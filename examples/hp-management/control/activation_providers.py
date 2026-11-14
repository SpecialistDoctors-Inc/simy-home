"""Real GitHub/CloudFormation adapters for automatic clinic environment creation."""
import datetime as dt
import hashlib
import json
import re

from github_app import AppConfig, GitHubApp, https_transport
from publisher import ACCOUNT, config_sha256
from site_activation import ActivationWaiting


def tenant_name(job):
    return 'hp-clinic-' + hashlib.sha256(job['subscription_id'].encode()).hexdigest()[:20]


class RepositoryBootstrap:
    def __init__(self, config, secrets, transport=https_transport):
        self.config, self.secrets, self.transport = config, secrets, transport
        for name in ('owner', 'template_owner', 'template_repository'):
            if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', config[name]):
                raise ValueError('invalid_repository_platform_config')
        if not re.fullmatch('[0-9a-f]{40}', config['template_tree']):
            raise ValueError('reviewed_template_tree_required')

    def request(self, method, path, body, guard, statuses=(200,)):
        guard()
        token = self.secrets(self.config['bootstrap_token_secret_ref'])
        if isinstance(token, str) and token.startswith('{'):
            token = json.loads(token).get('token')
        if not isinstance(token, str) or not token or any(c in token for c in '\r\n'):
            raise ActivationWaiting('bootstrap_credential_unavailable')
        headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                   'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'SIMY-HP'}
        status, result = self.transport(method, 'https://api.github.com' + path, headers, body)
        if status not in statuses or not isinstance(result, dict):
            raise ActivationWaiting('repository_provider_pending')
        return status, result

    def app(self, repository_id, name):
        def private_key(reference):
            raw = self.secrets(reference)
            value = json.loads(raw) if isinstance(raw, str) else raw
            if (not isinstance(value, dict) or value.get('app_id') != self.config['app_id']
                    or value.get('installation_id', value.get('install_id')) != self.config['installation_id']):
                raise ActivationWaiting('repository_app_identity_mismatch')
            return value['private_key']
        return GitHubApp(AppConfig(app_id=self.config['app_id'], installation_id=self.config['installation_id'],
            repository_id=repository_id, owner=self.config['owner'], repository=name,
            private_key_secret_ref=self.config['private_key_secret_ref']), private_key,
            transport=self.transport, permissions={'contents': 'write', 'actions': 'read'})

    def ensure(self, job, files, guard):
        name = tenant_name(job)
        prefix = '/repos/' + self.config['owner'] + '/' + name
        marker = 'SIMY clinic activation ' + job['job_id']
        status, repo = self.request('GET', prefix, None, guard, (200, 404))
        if status == 404:
            _, repo = self.request('POST', '/repos/' + self.config['template_owner'] + '/'
                + self.config['template_repository'] + '/generate', {'owner': self.config['owner'],
                'name': name, 'private': True, 'description': marker, 'include_all_branches': False}, guard, (201,))
        if (repo.get('full_name', '').casefold() != (self.config['owner'] + '/' + name).casefold()
                or repo.get('private') is not True or repo.get('description') != marker
                or repo.get('default_branch') != 'main' or type(repo.get('id')) is not int):
            raise ActivationWaiting('repository_identity_mismatch')
        app = self.app(repo['id'], name)
        base = app.head('main')
        _, expected = self.request('GET', '/repos/' + self.config['template_owner'] + '/'
            + self.config['template_repository'] + '/git/trees/' + self.config['template_tree'] + '?recursive=1', None, guard)
        _, current = self.request('GET', prefix + '/git/trees/' + base + '?recursive=1', None, guard)
        def metadata(tree):
            if tree.get('truncated') or not isinstance(tree.get('tree'), list):
                raise ActivationWaiting('repository_template_incomplete')
            return {r['path']: (r['mode'], r['sha']) for r in tree['tree']
                    if r.get('type') == 'blob' and not r['path'].startswith('site/')}
        if metadata(expected) != metadata(current):
            raise ActivationWaiting('repository_template_changed')
        # Only the site/ tree is populated. Trusted workflow/tools remain pinned.
        try:
            same = app.read_site_at(base).files == files
        except Exception:
            same = False
        guard()
        if not same:
            stamp = dt.datetime.fromtimestamp(job['created_at'], dt.timezone.utc).isoformat(timespec='seconds')
            base = app.commit_site('main', base, files, 'Import clinic homepage', job['job_id'], stamp).commit
        guard()
        ref = app._request('GET', app.prefix + '/git/ref/heads/dev', statuses=(200, 404))
        if ref.get('object', {}).get('sha') not in (None, base):
            raise ActivationWaiting('existing_draft_branch_changed')
        if ref.get('object', {}).get('sha') is None:
            app._request('POST', app.prefix + '/git/refs', {'ref': 'refs/heads/dev', 'sha': base}, statuses=(201,))
        guard()
        workflow = app._request('GET', app.prefix + '/actions/workflows/check-site.yml')
        if type(workflow.get('id')) is not int:
            raise ActivationWaiting('validation_workflow_pending')
        return {'github_app_id': self.config['app_id'], 'github_installation_id': self.config['installation_id'],
                'github_repository_id': repo['id'], 'github_owner': self.config['owner'], 'github_repository': name,
                'validation_workflow_id': workflow['id'], 'initial_main_commit': base}

    def verify(self, site, files, guard):
        guard()
        app = self.app(site['github_repository_id'], site['github_repository'])
        if app.read_site_at(site['initial_main_commit']).files != files or app.head('dev') != site['initial_main_commit']:
            raise ActivationWaiting('import_readback_mismatch')


class CloudEnvironments:
    def __init__(self, stacks, cloudfront, s3, route53, role_arn, template_builder):
        if not re.fullmatch('arn:aws:iam::' + ACCOUNT + r':role/[A-Za-z0-9+=,.@_/-]+', role_arn):
            raise ValueError('provisioner_role_account_mismatch')
        self.stacks, self.cloudfront, self.s3, self.route53 = stacks, cloudfront, s3, route53
        self.role_arn, self.template_builder = role_arn, template_builder

    def ensure(self, job, dns, guard):
        name = tenant_name(job)
        guard()
        try:
            rows = self.stacks.describe_stacks(StackName=name)['Stacks']
        except Exception as error:
            response = getattr(error, 'response', {})
            if response.get('Error', {}).get('Code') != 'ValidationError':
                raise
            guard()
            self.stacks.create_stack(StackName=name, TemplateBody=json.dumps(self.template_builder(name, job['host'], dns)),
                RoleARN=self.role_arn, ClientRequestToken='hp-' + job['job_id'],
                Capabilities=['CAPABILITY_NAMED_IAM'],
                EnableTerminationProtection=True, OnFailure='DO_NOTHING',
                Tags=[{'Key': 'hp_activation_job', 'Value': job['job_id']}])
            raise ActivationWaiting('hosting_creation_pending') from None
        if len(rows) != 1 or {t['Key']: t['Value'] for t in rows[0].get('Tags', [])}.get('hp_activation_job') != job['job_id']:
            raise ActivationWaiting('hosting_identity_mismatch')
        if rows[0].get('RoleARN') != self.role_arn:
            raise ActivationWaiting('hosting_identity_mismatch')
        if rows[0]['StackStatus'] in ('CREATE_FAILED', 'UPDATE_FAILED'):
            # Resume the owned stack in place. Never delete retained resources
            # or require an operator to recreate this customer's environment.
            stamp = str(rows[0].get('LastUpdatedTime', rows[0].get('CreationTime')))
            token = 'hp-retry-' + job['job_id'] + '-' + hashlib.sha256(stamp.encode()).hexdigest()[:12]
            guard()
            self.stacks.update_stack(StackName=name, TemplateBody=json.dumps(self.template_builder(name, job['host'], dns)),
                RoleARN=self.role_arn, ClientRequestToken=token, DisableRollback=True,
                Capabilities=['CAPABILITY_NAMED_IAM'])
            raise ActivationWaiting('hosting_creation_retrying', 300)
        if rows[0]['StackStatus'] not in ('CREATE_COMPLETE', 'UPDATE_COMPLETE'):
            raise ActivationWaiting('hosting_creation_pending')
        outputs = {r['OutputKey']: r['OutputValue'] for r in rows[0].get('Outputs', [])}
        deployment, dev_url, roles = {}, None, {}
        for env, prefix in [('dev', 'Dev'), ('prod', 'Prod')]:
            bucket, distribution_id = outputs[prefix + 'Bucket'], outputs[prefix + 'Distribution']
            if not bucket.startswith(name + '-'):
                raise ActivationWaiting('hosting_bucket_mismatch')
            guard()
            self.s3.head_bucket(Bucket=bucket, ExpectedBucketOwner=ACCOUNT)
            result = self.cloudfront.get_distribution(Id=distribution_id)['Distribution']
            config = result['DistributionConfig']
            origins = config.get('Origins', {}).get('Items', [])
            if (result.get('Status') != 'Deployed' or len(origins) != 1 or origins[0]['Id'] != 'site'
                    or not origins[0]['DomainName'].startswith(bucket + '.s3.')
                    or not result.get('ARN', '').startswith('arn:aws:cloudfront::' + ACCOUNT + ':distribution/')):
                raise ActivationWaiting('hosting_origin_unverified')
            if env == 'prod' and config.get('Aliases', {}).get('Items') != [job['host']]:
                raise ActivationWaiting('hosting_alias_mismatch')
            # Empty initial objects form a real inventory. No imported customer
            # content is published by provisioning, even on the CDN hostname.
            guard()
            try:
                self.s3.put_object(Bucket=bucket, Key='index.html', Body=b'', ContentType='text/html',
                    ExpectedBucketOwner=ACCOUNT, IfNoneMatch='*')
            except Exception as error:
                if getattr(error, 'response', {}).get('Error', {}).get('Code') not in ('PreconditionFailed', '412'):
                    raise
                existing = self.s3.get_object(Bucket=bucket, Key='index.html', ExpectedBucketOwner=ACCOUNT)
                try:
                    if existing['Body'].read(1) != b'':
                        raise ActivationWaiting('hosting_initial_inventory_changed')
                finally:
                    existing['Body'].close()
            deployment[env] = {'bucket': bucket, 'distribution_id': distribution_id, 'origin_id': 'site',
                               'expected_config_sha256': config_sha256(config, 'site'), 'initial_file_paths': ['index.html']}
            role = outputs[prefix + 'PublisherRole']
            if role != 'arn:aws:iam::' + ACCOUNT + ':role/' + name + '-publisher-' + env:
                raise ActivationWaiting('publisher_role_identity_mismatch')
            roles[env] = role
            if env == 'dev':
                dev_url = 'https://' + result['DomainName']
        return {'deployment': deployment, 'dev_url': dev_url, 'prod_url': 'https://' + job['host'], 'publisher_roles': roles}

    def verify(self, site, job, dns, guard):
        actual = self.ensure(job, dns, guard)
        roles = actual.pop('publisher_roles')
        if (roles != job['phases']['hosting']['publisher_roles'] or
                any(site.get(name) != value for name, value in actual.items())):
            raise ActivationWaiting('hosting_readback_mismatch')

    def cutover_plan(self, site, dns, guard):
        if dns.get('web_cutover_safe') is not True:
            raise ActivationWaiting('mail_and_application_connection_required')
        zone, host = dns['hosted_zone_id'], site['prod_url'].split('://', 1)[1].rstrip('/') + '.'
        if not re.fullmatch(r'Z[A-Z0-9]{5,32}', zone):
            raise ActivationWaiting('verified_dns_zone_required')
        guard()
        records = self.route53.list_resource_record_sets(HostedZoneId=zone, StartRecordName=host, MaxItems='100')
        same = [r for r in records['ResourceRecordSets'] if r['Name'].lower() == host.lower()]
        if records.get('IsTruncated') and records.get('NextRecordName', '').lower() == host.lower():
            raise ActivationWaiting('dns_inventory_incomplete')
        web = [r for r in same if r['Type'] in ('A', 'AAAA', 'CNAME')]
        if any('SetIdentifier' in r for r in web):
            raise ActivationWaiting('dns_routing_policy_connection_required')
        distribution = self.cloudfront.get_distribution(Id=site['deployment']['prod']['distribution_id'])['Distribution']
        return {'zone_id': zone, 'host': host, 'before': web,
                'target': distribution['DomainName'], 'site_id': site['site_id'],
                'distribution_id': site['deployment']['prod']['distribution_id'],
                'status': 'prepared', 'activation_job': dns['subscription_id']}
