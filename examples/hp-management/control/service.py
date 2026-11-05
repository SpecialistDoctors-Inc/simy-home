"""Server-authoritative HP command admission and exact-artifact approval.

MCP clients may supply site/workspace identifiers, never repository/recipient/IAM
configuration. Mutable Sheets and Drive are transport/audit surfaces only.
"""
from __future__ import annotations
import hashlib
import json
import re
import secrets
import time
from uuid import UUID, uuid4
from store import Write, Check, Conflict


class Rejected(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def uuid(value):
    try:
        result = str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise Rejected('invalid_id') from None
    if result != value:
        raise Rejected('invalid_id')
    return result


def exact(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise Rejected('invalid_input')


def digest(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise Rejected('invalid_digest')
    return value


def main_commit(site):
    publication = site.get('current_publication')
    publication = publication if isinstance(publication, dict) else {}
    receipt = publication.get('receipt') or {}
    value = site.get('current_main_commit') or publication.get('main_commit') or receipt.get('main_commit') or site.get('initial_main_commit')
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value):
        raise Rejected('publication_source_not_configured')
    return value


class Service:
    def __init__(self, store, clock=time.time, publication_enabled=False):
        self.store, self.clock, self.publication_enabled = store, clock, publication_enabled

    def principal(self, claims):
        if not isinstance(claims, dict) or not isinstance(claims.get('sub'), str):
            raise Rejected('authentication_required')
        row = self.store.get('principal:' + claims['sub'])
        if not row or row.get('disabled') or not row.get('sites'):
            raise Rejected('access_revoked')
        return row

    def authorized(self, claims, site_id, role='read'):
        member = self.principal(claims)
        if not isinstance(site_id, str) or not re.fullmatch('[a-z][a-z0-9-]{1,62}', site_id):
            raise Rejected('invalid_site')
        scopes = set(claims.get('scope', '').split())
        if ('hp:read' if role == 'read' else 'hp:write') not in scopes:
            raise Rejected('insufficient_scope')
        if role not in member['sites'].get(site_id, []):
            raise Rejected('site_access_denied')
        site = self.store.get('site:' + site_id)
        if not site or site.get('disabled'):
            raise Rejected('site_unavailable')
        return member, site

    def profile(self, claims):
        member = self.principal(claims)
        if 'hp:read' not in claims.get('scope', '').split():
            raise Rejected('insufficient_scope')
        return {'subject': claims['sub'], 'email': claims.get('email'), 'sites': sorted(member['sites'])}

    def list_sites(self, claims):
        member = self.principal(claims)
        result = []
        for site_id in sorted(member['sites']):
            try:
                _, site = self.authorized(claims, site_id)
            except Rejected:
                continue
            result.append({'site_id': site_id, 'name': site['name'], 'roles': member['sites'][site_id],
                'preview_url': site['dev_url'], 'production_url': site['prod_url']})
        return result

    def workspace(self, claims, site_id, workspace_id):
        self.authorized(claims, site_id, 'edit')
        row = self.store.get('workspace:' + uuid(workspace_id))
        if not row or row['site_id'] != site_id or row['subject'] != claims['sub'] or row.get('closed'):
            raise Rejected('workspace_access_denied')
        return row

    def admit(self, claims, kind, body):
        fields = {'open_workspace': {'operation_id','site_id'},
            'save_draft': {'operation_id','site_id','workspace_id','base_commit','bundle_file_id','bundle_sha256'},
            'submit_preview': {'operation_id','site_id','workspace_id','saved_commit'}}
        if kind not in fields:
            raise Rejected('unsupported_operation')
        exact(body, fields[kind]); op_id = uuid(body['operation_id'])
        member, site = self.authorized(claims, body['site_id'], 'edit')
        key = 'operation:' + op_id
        op_fingerprint = fingerprint({'kind': kind, 'subject': claims['sub'], 'input': body})
        old = self.store.get(key)
        if old:
            if old['fingerprint'] != op_fingerprint:
                raise Rejected('operation_id_conflict')
            return self.public_operation(old)
        if kind != 'open_workspace':
            workspace = self.workspace(claims, body['site_id'], body['workspace_id'])
            commit = body.get('base_commit', body.get('saved_commit'))
            if not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit):
                raise Rejected('invalid_commit')
            if workspace.get('head_commit') != commit:
                raise Rejected('workspace_changed')
        if kind == 'save_draft':
            digest(body['bundle_sha256'])
            if not isinstance(body['bundle_file_id'], str) or not re.fullmatch('[A-Za-z0-9_-]{10,256}', body['bundle_file_id']):
                raise Rejected('invalid_drive_file')
        now = int(self.clock())
        operation = {'operation_id': op_id, 'site_id': body['site_id'], 'subject': claims['sub'], 'kind': kind,
            'input': body, 'fingerprint': op_fingerprint, 'created_at': now, 'status': 'queued',
            'queue_state': 'pending', 'member_version': member['_version'], 'site_config_version': site['config_version'],
            'stage': 'accepted', 'result': None, 'error': None, 'lease_epoch': 0}
        writes = [Write(key, operation, None), Check('principal:' + claims['sub'], member['_version']),
                  Check('site:' + body['site_id'], site['_version'])]
        if kind != 'open_workspace':
            writes.append(Check('workspace:' + body['workspace_id'], workspace['_version']))
        if kind == 'open_workspace':
            workspace_id = str(uuid4()); operation['workspace_id'] = workspace_id
            writes.append(Write('workspace:' + workspace_id, {'workspace_id': workspace_id,
                'site_id': body['site_id'], 'subject': claims['sub'], 'status': 'preparing', 'created_at': now}, None))
        self.store.transact(writes)
        return self.public_operation(operation)

    @staticmethod
    def public_operation(op):
        result = {k: op.get(k) for k in ('operation_id','site_id','workspace_id','kind','status','stage','result','error')}
        if op.get('reporting_required') and op.get('status') == 'completed':
            result['status'] = 'needs_attention' if op.get('reporting_state') == 'needs_attention' else 'reporting'
        if op.get('reporting_state'):
            result['reporting_state'] = op['reporting_state']
            result['reporting_receipt'] = op.get('reporting_receipt')
        return result

    def operation(self, claims, operation_id):
        row = self.store.get('operation:' + uuid(operation_id))
        if not row or row['subject'] != claims['sub']:
            raise Rejected('operation_access_denied')
        self.authorized(claims, row['site_id'])
        return self.public_operation(row)

    def cancel(self, claims, operation_id):
        key = 'operation:' + uuid(operation_id); row = self.store.get(key)
        if not row or row['subject'] != claims['sub']:
            raise Rejected('operation_access_denied')
        self.authorized(claims, row['site_id'], 'publish' if row['kind'] == 'publish' else 'edit')
        if row['status'] in {'completed', 'cancelled', 'failed', 'published_after_cancel_or_revocation'}:
            return self.public_operation(row)
        row['cancel_requested'] = True
        if row['status'] == 'queued' and not row.get('effects'):
            row['status'] = 'cancelled'; row.pop('queue_state', None)
        self.store.put(key, row, row['_version'])
        return self.public_operation(row)

    def resume(self, claims, operation_id, recovery_id):
        """Audit an explicit same-operation retry; never replace its sealed work."""
        operation_id, recovery_id = uuid(operation_id), uuid(recovery_id)
        self.principal(claims)
        key = 'operation:' + operation_id
        row = self.store.get(key)
        if not row or row.get('subject') != claims['sub']:
            raise Rejected('operation_access_denied')
        member, site = self.authorized(claims, row['site_id'], 'publish' if row['kind'] == 'publish' else 'edit')
        if member['_version'] != row.get('member_version') or site.get('config_version') != row.get('site_config_version'):
            raise Rejected('resumption_stale')
        audit_key = 'resumption:' + recovery_id
        existing = self.store.get(audit_key)
        if existing:
            if existing.get('operation_id') != operation_id or existing.get('subject') != claims['sub'] or existing.get('original_fingerprint') != row.get('fingerprint'):
                raise Rejected('resumption_id_conflict')
            # Replay observes current state even after the worker starts/finishes;
            # it never clears cancellation, resets retries, or requeues again.
            return self.public_operation(row)
        if row.get('cancel_requested'):
            raise Rejected('resumption_cancel_requested')
        if row.get('status') != 'needs_attention' or row.get('kind') not in ('open_workspace', 'save_draft', 'submit_preview', 'publish'):
            raise Rejected('resumption_not_allowed')
        approval = None
        approval_key = None
        if row['kind'] == 'publish':
            if not self.publication_enabled:
                raise Rejected('publication_not_enabled')
            approval_id = row.get('input', {}).get('approval_id')
            try:
                approval_key = 'approval:' + uuid(approval_id)
            except Rejected:
                raise Rejected('resumption_approval_invalid') from None
            approval = self.store.get(approval_key)
            if not approval or approval.get('state') != 'accepted' or approval.get('operation_id') != operation_id or approval.get('subject') != claims['sub'] or approval.get('site_id') != row['site_id'] or approval.get('member_version') != row['member_version'] or approval.get('site_config_version') != row['site_config_version']:
                raise Rejected('resumption_approval_invalid')
        observed_now = self.clock()
        now = int(observed_now)
        lease_key = 'lease:site:' + row['site_id']
        lease = self.store.get(lease_key)
        if lease and (lease.get('until', 0) > observed_now or lease.get('blocked_operation') not in (None, operation_id)):
            raise Rejected('resumption_site_busy')
        prior_error = row.get('error')
        # Keep known stop codes verbatim; unexpected error data is fingerprinted,
        # never copied into another record where it could contain provider data.
        safe_error = prior_error if prior_error in (None, 'retry_budget_exhausted', 'wait_deadline_exceeded') else 'unclassified_error'
        audit = {'schema_version': 1, 'kind': 'operation_resumption', 'recovery_id': recovery_id,
            'operation_id': operation_id, 'subject': claims['sub'], 'original_fingerprint': row['fingerprint'],
            'prior_status': row['status'], 'prior_error': safe_error,
            'prior_retry_attempts': row.get('retry_attempts', 0), 'prior_retry_at': row.get('retry_at'),
            'prior_retry_generation': row.get('retry_generation', 0), 'resumed_at': now}
        if safe_error == 'unclassified_error':
            audit['prior_error_sha256'] = fingerprint(prior_error)
        resumed = {**row, 'status': 'reconciling' if row.get('pending_effect') or row.get('reconciliation_required') else 'retry_wait',
            'queue_state': 'pending', 'retry_at': now, 'retry_attempts': 0,
            'retry_generation': row.get('retry_generation', 0) + 1, 'error': None}
        writes = [Write(key, resumed, row['_version']), Write(audit_key, audit, None),
            Check('principal:' + claims['sub'], member['_version']), Check('site:' + row['site_id'], site['_version']),
            Check(lease_key, lease['_version'] if lease else None)]
        if approval:
            writes.append(Check(approval_key, approval['_version']))
        # The old lease, pending-effect fence and external deadlines stay intact.
        self.store.transact(writes)
        return self.public_operation(resumed)

    def prepare_publish(self, claims, site_id, preview_id):
        member, site = self.authorized(claims, site_id, 'publish')
        preview = self.store.get('preview:' + uuid(preview_id))
        if not preview or preview['site_id'] != site_id or preview.get('status') != 'verified' or site.get('current_preview') != preview_id:
            raise Rejected('preview_not_current')
        mode = 'publish' if self.publication_enabled else 'connection_test'
        approval_id, nonce = str(uuid4()), secrets.token_urlsafe(32)
        record = {'approval_id': approval_id, 'mode': mode, 'subject': claims['sub'], 'site_id': site_id,
            'preview_id': preview_id, 'source_commit': preview['source_commit'], 'artifact_sha256': preview['artifact_sha256'],
            'member_version': member['_version'], 'site_config_version': site['config_version'],
            'expected_publication': site.get('current_publication'), 'nonce_hash': fingerprint(nonce),
            'expected_main_commit': main_commit(site),
            'created_at': int(self.clock()), 'expires_at': int(self.clock()) + 600, 'state': 'prepared'}
        self.store.put('approval:' + approval_id, record)
        # The host sends _meta to the app only. It is not permission by itself;
        # confirm checks the authenticated subject, live ACL and immutable proof.
        message = ('接続テストです。公開は行いません。確認カードの接続確認ボタンを押してください。'
            if mode == 'connection_test' else '確認した内容を公開する場合は、確認カードの公開ボタンを押してください。')
        return {'structuredContent': {'approval_id': approval_id, 'mode': mode, 'site_id': site_id, 'site_name': site['name'],
            'preview_id': preview_id, 'preview_url': preview['url'], 'production_url': site['prod_url'],
            'source_commit': record['source_commit'], 'artifact_sha256': record['artifact_sha256'],
            'summary': preview['summary'], 'expires_at': record['expires_at']},
            '_meta': {'confirmation_nonce': nonce}, 'content': [{'type': 'text', 'text': message}]}

    def confirmation(self, claims, approval_id):
        approval = self.store.get('approval:' + uuid(approval_id))
        if not approval or approval['subject'] != claims.get('sub'):
            raise Rejected('confirmation_invalid')
        self.authorized(claims, approval['site_id'])
        result = {key: approval[key] for key in ('approval_id', 'site_id', 'preview_id',
            'source_commit', 'artifact_sha256', 'state', 'expires_at')}
        result['mode'] = approval.get('mode', 'publish')
        if approval['state'] == 'accepted':
            result['operation'] = self.operation(claims, approval['operation_id'])
        elif approval['state'] == 'connection_tested':
            result['result'] = {key: approval['result'][key] for key in
                ('kind', 'status', 'approval_id', 'preview_id', 'completed_at')}
        elif approval['state'] == 'prepared':
            # Another confirmation surface may already have requested these same
            # bytes. Read that factual operation without accepting this card.
            target = self.store.get('publication-target:' + approval['site_id'] + ':' + approval['preview_id']) if result['mode'] == 'publish' else None
            if target and target.get('subject') == claims['sub'] and target.get('artifact_sha256') == approval['artifact_sha256']:
                result['state'] = 'already_requested'
                result['operation'] = self.operation(claims, target['operation_id'])
            elif approval['expires_at'] <= self.clock():
                result['state'] = 'expired'
        # A prepared read is not proof that an in-flight confirmation cannot
        # still commit. Clients preserve uncertainty and never resend from it.
        return result

    def confirm_publish(self, claims, approval_id, nonce):
        key = 'approval:' + uuid(approval_id); approval = self.store.get(key)
        if not approval or approval['subject'] != claims['sub'] or not isinstance(nonce, str) or not secrets.compare_digest(approval['nonce_hash'], fingerprint(nonce)):
            raise Rejected('confirmation_invalid')
        member, site = self.authorized(claims, approval['site_id'], 'publish')
        mode = approval.get('mode', 'publish')  # Existing publication approvals remain publication-only.
        if mode not in ('publish', 'connection_test'):
            raise Rejected('confirmation_invalid')
        if mode == 'publish':
            if not self.publication_enabled:
                raise Rejected('publication_not_enabled')
            if approval['state'] == 'accepted':
                return self.operation(claims, approval['operation_id'])
        valid_states = ('prepared', 'connection_tested') if mode == 'connection_test' else ('prepared',)
        if approval['state'] not in valid_states or approval['expires_at'] <= self.clock():
            raise Rejected('confirmation_expired')
        if member['_version'] != approval['member_version'] or site['config_version'] != approval['site_config_version'] or site.get('current_preview') != approval['preview_id'] or site.get('current_publication') != approval['expected_publication'] or main_commit(site) != approval['expected_main_commit']:
            raise Rejected('confirmation_stale')
        preview = self.store.get('preview:' + approval['preview_id'])
        if not preview or preview['status'] != 'verified' or preview['artifact_sha256'] != approval['artifact_sha256'] or preview['source_commit'] != approval['source_commit']:
            raise Rejected('confirmation_stale')
        if mode == 'connection_test':
            # A test card can never become publication authority after a gate change.
            # The approval row is the durable audit; there is no operation or queue entry.
            if approval['state'] == 'connection_tested':
                return approval['result']
            result = {'kind': 'connection_test', 'status': 'completed', 'approval_id': approval_id,
                'preview_id': approval['preview_id'], 'completed_at': int(self.clock())}
            self.store.transact([Write(key, {**approval, 'state': 'connection_tested', 'result': result}, approval['_version']),
                Check('principal:' + claims['sub'], member['_version']),
                Check('site:' + approval['site_id'], site['_version']),
                Check('preview:' + approval['preview_id'], preview['_version'])])
            return result
        target_key = 'publication-target:' + approval['site_id'] + ':' + approval['preview_id']
        target = self.store.get(target_key)
        replacement_checks = []
        if target:
            previous = self.store.get('operation:' + target['operation_id'])
            lease_key = 'lease:site:' + approval['site_id']
            lease = self.store.get(lease_key)
            phases = previous.get('phases', {}) if previous else {}
            known_main = phases.get('main_commit', {}).get('commit')
            replaceable = (previous and previous['status'] in ('failed', 'cancelled')
                and not previous.get('pending_effect') and not previous.get('reconciliation_required')
                and 'publish' not in phases and not (lease or {}).get('blocked_operation')
                and (not known_main or known_main == main_commit(site)))
            if not replaceable:
                if target['subject'] != claims['sub']:
                    raise Rejected('publication_already_requested')
                return self.operation(claims, target['operation_id'])
            replacement_checks.append(Check('operation:' + target['operation_id'], previous['_version']))
            if lease:
                replacement_checks.append(Check(lease_key, lease['_version']))
        op_id = str(uuid4()); operation = {'operation_id': op_id, 'site_id': approval['site_id'],
            'subject': claims['sub'], 'kind': 'publish', 'input': {'approval_id': approval_id},
            'created_at': int(self.clock()), 'status': 'queued', 'queue_state': 'pending', 'stage': 'accepted',
            'fingerprint': fingerprint({'approval_id': approval_id, 'artifact_sha256': approval['artifact_sha256']}),
            'member_version': member['_version'], 'site_config_version': site['config_version'],
            'result': None, 'error': None, 'lease_epoch': 0}
        self.store.transact([Write(key, {**approval, 'state': 'accepted', 'operation_id': op_id}, approval['_version']),
            Write('operation:' + op_id, operation, None),
            Write(target_key, {'operation_id': op_id, 'subject': claims['sub'], 'artifact_sha256': approval['artifact_sha256']}, (target or {}).get('_version')),
            Check('principal:' + claims['sub'], member['_version']),
            Check('site:' + approval['site_id'], site['_version']),
            Check('preview:' + approval['preview_id'], preview['_version']), *replacement_checks])
        stored = self.store.get('operation:' + op_id)
        return self.public_operation(stored)
