"""AWS entrypoints. State, authentication and external providers are separate."""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
from cloud_auth import Secrets, Tokens, GoogleExchange
from identity import Identity
from licensing import EntitlementResolver
from service import Service
from store import DynamoStore, Conflict
from mcp_adapter import App
from wordpress_onboarding import WordPressOnboarding
from wordpress_editor import WordPressEditor, WordPressTransfers

_app = None


def entitlement_resolver(secret):
    endpoint = os.environ.get('HP_CONTROL_ENTITLEMENT_ENDPOINT', '')
    token_arn = os.environ.get('HP_CONTROL_ENTITLEMENT_SECRET_ARN', '')
    return EntitlementResolver(endpoint, lambda: secret(token_arn)) if endpoint and token_arn else None


def application():
    global _app
    if _app is not None:
        return _app
    secret = Secrets()
    issuer = os.environ['HP_PUBLIC_BASE_URL'].rstrip('/')
    tokens = Tokens(secret(os.environ['HP_SIGNING_SECRET_ARN']), issuer)
    client = json.loads(secret(os.environ['HP_GOOGLE_SECRET_ARN']))
    store = DynamoStore(os.environ['HP_TABLE_NAME'])
    identity = Identity(store, issuer, client['client_id'], tokens.sign, GoogleExchange(client))
    wordpress_arn = os.environ.get('HP_WORDPRESS_SECRET_ARN', '')
    wordpress_origin = os.environ.get('HP_WORDPRESS_TEST_ORIGIN') if wordpress_arn else None
    service = Service(store, publication_enabled=os.environ.get('HP_PUBLICATION_ENABLED') == 'true',
        license_resolver=entitlement_resolver(secret),
        claim_targets=json.loads(os.environ.get('HP_SITE_CLAIM_TARGETS', '{}')), wordpress_test_origin=wordpress_origin)
    html = (Path(__file__).parent / 'ui' / 'dist' / 'publish.html').read_text()
    from transfers import Transfers
    preflight_arn = os.environ.get('HP_CONTROL_PREFLIGHT_SECRET_ARN', '')
    bucket = os.environ['HP_ARTIFACT_BUCKET']
    s3 = regional_s3_client(os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION'))
    onboarding, stripe_webhook = clinic_billing(store, service, identity, secret)
    _app = App(identity, service, tokens.verify, {'keys': [tokens.jwk]}, html,
        preflight_token=(lambda: secret(preflight_arn)) if preflight_arn else None,
        wordpress=(lambda: WordPressOnboarding(store, json.loads(secret(wordpress_arn)))) if wordpress_arn else None,
        wordpress_transfers=WordPressTransfers(store, s3, bucket) if service.wordpress_test_origin else None,
        transfers=Transfers(service, bucket, s3), onboarding=onboarding, stripe_webhook=stripe_webhook)
    return _app


def clinic_billing(store, service, identity, secret):
    """Wire simy.one Payment Link purchases when the billing secret is configured.

    The secret holds JSON: secret_key (restricted, read Checkout Sessions),
    webhook_secret, payment_links {plink_id: plan}, intake_key (Fernet) and an
    optional https plugin_url.
    """
    arn = os.environ.get('HP_CLINIC_BILLING_SECRET_ARN', '')
    if not arn:
        return None, None
    from clinic_onboarding import ClinicOnboarding
    from stripe_billing import StripeApi, StripeBilling
    config = lambda: json.loads(secret(arn))
    billing = StripeBilling(store, StripeApi(lambda: config()['secret_key']), config()['payment_links'])
    onboarding = ClinicOnboarding(store, billing, service, identity, config()['intake_key'],
                                  plugin_url=config().get('plugin_url'))
    return onboarding, lambda payload, signature: billing.webhook(payload, signature, config()['webhook_secret'])


def handler(event, context):
    try:
        if event.get('rawPath') == '/.well-known/openai-apps-challenge':
            return domain_verification(event, DynamoStore(os.environ['HP_TABLE_NAME']),
                os.environ['HP_PUBLIC_BASE_URL'])
        if event.get('rawPath') == '/github/webhook':
            from github_events import handle
            if event.get('requestContext', {}).get('http', {}).get('method') != 'POST':
                return {'statusCode': 405, 'body': ''}
            status = handle(event, DynamoStore(os.environ['HP_TABLE_NAME']), Secrets()(os.environ['HP_GITHUB_WEBHOOK_SECRET_ARN']))
            return {'statusCode': status, 'headers': {'Cache-Control': 'no-store'}, 'body': ''}
        result = application()(event, context)
        # The minute dispatcher is recovery, not a throughput ceiling. A command
        # is already durable before this best-effort queue hint is attempted.
        if event.get('rawPath') == '/mcp' and result.get('statusCode') == 200:
            try:
                data = json.loads(result['body']).get('result', {}).get('structuredContent', {})
                operation_id = data.get('operation_id')
                if isinstance(operation_id, str):
                    import boto3, time
                    enqueue_one(DynamoStore(os.environ['HP_TABLE_NAME']), boto3.client('sqs'),
                        'operation:' + operation_id, time.time())
            except Exception:
                print('{"event":"hp_enqueue_deferred"}')
        return result
    except Exception:
        return {'statusCode': 503, 'headers': {'Content-Type': 'application/json', 'Cache-Control': 'no-store'},
                'body': '{"error":"service_not_configured"}'}


def domain_verification(event, store, issuer):
    """Serve only the operator-provisioned public ownership proof for this host."""
    headers = {'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store',
               'X-Content-Type-Options': 'nosniff'}
    if event.get('requestContext', {}).get('http', {}).get('method') != 'GET':
        return {'statusCode': 405, 'headers': headers, 'body': ''}
    record = store.get('domain-verification:openai') or {}
    value = record.get('token')
    if (record.get('issuer') != issuer.rstrip('/') or
            not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9._=\-]{16,1024}', value)):
        return {'statusCode': 404, 'headers': headers, 'body': ''}
    # The token is public by design. No other row fields or credentials are returned.
    return {'statusCode': 200, 'headers': headers, 'body': value}


def enqueue_one(store, sqs, key, now):
    row = store.get(key)
    reporting = bool(row and row.get('reporting_required') and row.get('reporting_state') not in ('complete', 'suppressed', 'needs_attention'))
    if not row or row.get('queue_state') != 'pending' or (row.get('status') not in ('queued', 'retry_wait', 'reconciling') and not reporting) or row.get('retry_at', 0) > now:
        return False
    generation = row.get('retry_generation', 0)
    sqs.send_message(QueueUrl=os.environ['HP_COMMAND_QUEUE_URL'],
        MessageBody=json.dumps({'operation_id': row['operation_id']}),
        MessageGroupId=row['site_id'], MessageDeduplicationId=row['operation_id'] + ':' + str(generation))
    try:
        store.put(key, {**row, 'queue_state': 'sent'}, row['_version'])
    except Conflict:
        pass
    return True


def dispatch_pending(event, context, *, store=None, sqs=None, clock=None):
    import time
    import boto3
    store = store or DynamoStore(os.environ['HP_TABLE_NAME'])
    sqs = sqs or boto3.client('sqs')
    now = (clock or time.time)()
    sent = 0
    for key, observed in store.pending(25, now=now):
        sent += int(enqueue_one(store, sqs, key, now))
    print(json.dumps({'event': 'hp_dispatch_completed', 'enqueued': sent,
        'has_attention': getattr(store, 'has_attention', lambda: False)()}))
    return {'enqueued': sent}


def regional_s3_client(region):
    """Construct a regional SigV4 client from trusted deployment configuration.

    An implicit S3 client may presign GET with SigV2, which hoists the expected
    owner into query parameters while the renderer sends the required header.
    Keep the owner header and sign it once with SigV4 instead.
    """
    import re
    import boto3
    from botocore.config import Config
    if not isinstance(region, str) or not re.fullmatch(r'[a-z]{2}(?:-[a-z]+)+-[0-9]', region):
        raise ValueError('regional_s3_region_required')
    endpoint = 'https://s3.' + region + '.amazonaws.com'
    client = boto3.client('s3', region_name=region, endpoint_url=endpoint,
        config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'}))
    if client.meta.region_name != region or client.meta.endpoint_url != endpoint or client.meta.config.signature_version != 's3v4':
        raise ValueError('regional_s3_client_binding_failed')
    return client


def consumer():
    import boto3
    from executor import Executor
    from cloud_providers import GoogleDrive, S3Artifacts, github_factory
    from github_workflow import GitHubWorkflow
    from publisher import SitePublisher
    from browser_validation import BrowserValidation
    store = DynamoStore(os.environ['HP_TABLE_NAME']); secret = Secrets()
    drive = GoogleDrive(os.environ['HP_GOOGLE_OPERATOR_SECRET_ARN'], secret)
    validator_config = json.loads(os.environ.get('HP_VALIDATOR_CONFIG', '{}'))
    region = validator_config.get('region') or os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION')
    s3 = regional_s3_client(region)
    artifacts = S3Artifacts(os.environ['HP_ARTIFACT_BUCKET'], s3)
    github = github_factory(os.environ['HP_GITHUB_SECRET_ARN'], secret)
    roles = json.loads(os.environ.get('HP_PUBLISHER_ROLES', '{}'))
    preview_publisher = SitePublisher('dev', roles.get('dev'), store)
    publisher = SitePublisher('prod', roles.get('prod'), store)
    workflow = GitHubWorkflow(github, preview_readback=preview_publisher.readback)
    browser = BrowserValidation(store, boto3.client('ecs', region_name=region), s3, validator_config)
    wordpress_arn = os.environ.get('HP_WORDPRESS_SECRET_ARN', '')
    wordpress_origin = os.environ.get('HP_WORDPRESS_TEST_ORIGIN') if wordpress_arn else None
    wordpress = None
    if wordpress_origin:
        onboarding = WordPressOnboarding(store, json.loads(secret(wordpress_arn)))
        transfers = WordPressTransfers(store, s3, os.environ['HP_ARTIFACT_BUCKET'])
        wordpress = WordPressEditor(onboarding, transfers, os.environ['HP_PUBLIC_BASE_URL'].rstrip('/') + '/mcp')
    return Executor(store, github, drive, artifacts, workflow, publisher,
        publication_enabled=os.environ.get('HP_PUBLICATION_ENABLED') == 'true', preview_publisher=preview_publisher,
        lease_seconds=960, browser_validator=browser, license_resolver=entitlement_resolver(secret),
        wordpress=wordpress, wordpress_test_origin=wordpress_origin)


def defer_admission_conflict(executor, row):
    """Persist a wake-up before acknowledging a delivery that lost admission.

    Sending a FIFO message and marking its outbox row sent are separate writes.
    A fast consumer can lose its lease transaction to that final outbox write.
    Preserve the sealed work and fence; only reschedule a non-running operation.
    """
    from store import Write
    if not row or row.get('status') not in ('queued', 'retry_wait', 'reconciling') or row.get('queue_state') not in ('pending', 'sent'):
        return False
    import time
    now = getattr(executor, 'clock', time.time)()
    if row.get('queue_state') == 'pending' and row.get('retry_at', 0) > now:
        # execute() already persisted this delivery's retry. The dispatcher
        # cannot have sent this future version, so its older sent write is stale.
        return True
    lease_key = 'lease:site:' + row['site_id']
    lease = executor.store.get(lease_key)
    attempts = row.get('retry_attempts', 0) + 1
    exhausted = attempts >= getattr(executor, 'max_retry_attempts', 8)
    updated = {**row, 'retry_attempts': attempts,
        'retry_generation': row.get('retry_generation', 0) + 1,
        'retry_at': max(row.get('retry_at', 0), now + min(5 * 2 ** min(attempts - 1, 6), 300),
                        (lease or {}).get('until', 0) + 1),
        'error': 'retry_budget_exhausted' if exhausted else 'consumer_admission_conflict'}
    if exhausted:
        updated['status'] = 'needs_attention'
        updated.pop('queue_state', None)
    else:
        updated['queue_state'] = 'pending'
    # Also change a still-pending row: a delayed dispatcher must not mark the
    # acknowledged delivery sent. Admission changes the operation version, so
    # this CAS protects an active owner without fencing unrelated lease updates.
    executor.store.transact([Write('operation:' + row['operation_id'], updated, row['_version'])])
    return True


def consume_commands(event, context, *, executor=None, reporter=None):
    executor = executor or consumer()
    failures = []
    for record in event.get('Records', []):
        operation_id = None
        try:
            body = json.loads(record['body'])
            if set(body) != {'operation_id'}:
                raise ValueError('invalid_command')
            operation_id = body['operation_id']
            operation = executor.execute(operation_id)
            if operation.get('status') == 'completed' and operation.get('reporting_required'):
                if reporter is None:
                    from reporting import Reporter
                    from cloud_reporting import factories
                    sheets, mail = factories(os.environ['HP_GOOGLE_OPERATOR_SECRET_ARN'], Secrets())
                    reporter = Reporter(executor.store, sheets, mail, license_resolver=executor.license_resolver)
                reporter.report(operation_id)
        except Exception as error:
            # Expected waits/reconciliation already have a durable outbox. Keeping
            # the old FIFO delivery invisible would delay that site's retry by the
            # full visibility timeout. Only ack after observing persisted recovery.
            saved = executor.store.get('operation:' + operation_id) if isinstance(operation_id, str) else None
            from executor import Busy
            if isinstance(error, (Busy, Conflict)):
                try:
                    if defer_admission_conflict(executor, saved):
                        continue
                except Conflict:
                    # A concurrent owner won. Never overwrite its work or ack
                    # solely because this delivery tried to reserve a retry.
                    pass
                saved = executor.store.get('operation:' + operation_id) if isinstance(operation_id, str) else None
            if saved and saved.get('status') == 'completed' and saved.get('reporting_required') and saved.get('reporting_state') != 'needs_attention':
                if saved.get('queue_state') != 'pending':
                    import time
                    attempts = saved.get('reporting_retry_attempts', 0) + 1
                    changes = {**saved, 'reporting_retry_attempts': attempts,
                        'retry_generation': saved.get('retry_generation', 0) + 1,
                        'retry_at': int(time.time()) + min(30 * 2 ** min(attempts - 1, 5), 900),
                        'queue_state': 'pending', 'error': 'reporting_retry_required'}
                    if attempts > 8:
                        changes['reporting_state'] = 'needs_attention'
                        changes.pop('queue_state', None)
                    try:
                        executor.store.put('operation:' + operation_id, changes, saved['_version'])
                    except Conflict:
                        pass
                    saved = executor.store.get('operation:' + operation_id)
            settled_reporting = saved and (not saved.get('reporting_required') or saved.get('queue_state') == 'pending' or saved.get('reporting_state') == 'needs_attention')
            if saved and (saved.get('status') in ('failed', 'cancelled', 'needs_attention', 'published_after_cancel_or_revocation')
                    or (saved.get('status') == 'completed' and settled_reporting)
                    or (saved.get('status') in ('retry_wait', 'reconciling', 'queued') and saved.get('queue_state') == 'pending')):
                continue
            failures.append({'itemIdentifier': record['messageId']})
    return {'batchItemFailures': failures}
