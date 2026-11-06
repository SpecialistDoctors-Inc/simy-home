"""Durable, append-only result reporting for the local editor (no default adapters).

Factories receive (frozen_site, guard). Every provider request must call guard()
for reads or guard(True) immediately before writes. Providers must verify the
configured operator identity and exact Sheet/recipient. Sheets exposes
spreadsheet_id, authorized_user(), find_request(id,revision), append_request(row),
find_event(key), append_event(event); Gmail
exposes recipient, authorized_user(), find_notice(envelope,key), send_notice(...).
Existing runner providers can be wrapped with a guarded transport and their
set_event_admission/set_notice_admission context hooks; their row-4 header checks
are retained. V2 Requests and Events use the operation UUID/revision 1, not a
legacy intake request. Requests rows are immutable local_draft/local_preview/
local_publication projections. Nothing emits ready_for_dev or grants old-runner
authority. Workspace opening has an Event but no Requests row.

An admitted effect is never resent, even if subsequent readback finds nothing.
The shared site lease stays blocked until the exact prior effect is observed or
an operator resolves it outside this API. Provider acceptance/readback is not
recipient inbox delivery. Cancellation/revocation permit only prior-effect reads.
"""
from __future__ import annotations
from contextlib import contextmanager
import datetime as dt
import json
import re
import time
from urllib.parse import urlsplit
from uuid import uuid4, uuid5, NAMESPACE_URL

from executor import Busy, IntegrationUnavailable, ReconciliationRequired
from service import Rejected, fingerprint, uuid
from store import Check, Write

KINDS = {'open_workspace': ('workspace', 'workspace_ready'), 'save_draft': ('saved', 'draft_saved'),
         'submit_preview': ('preview', 'dev_preview_ready'), 'publish': ('published', 'published')}
SAFE_REASONS = set('operation_cancelled access_revoked site_configuration_changed reporting_binding_changed reporting_binding_invalid reporting_wrong_site reporting_result_invalid reporting_workspace_mismatch reporting_saved_mismatch reporting_artifact_mismatch reporting_preview_stale reporting_artifact_unverified reporting_url_invalid reporting_url_mismatch reporting_publication_stale reporting_operator_mismatch reporting_wrong_sheet reporting_wrong_recipient reporting_admission_mismatch reporting_event_mismatch reporting_notice_unverified reporting_outbox_tampered reporting_result_changed reporting_request_mismatch'.split())
BINDING_FIELDS = ('site_id', 'config_version', 'sheet_id', 'recipient', 'operator_subject', 'operator_email', 'mail_enabled', 'notification_recipient_ref')


def require(condition, code):
    if not condition:
        raise Rejected(code)


def email(value):
    return isinstance(value, str) and re.fullmatch(r'[^\s@<>,;:]+@[^\s@<>,;:]+\.[^\s@<>,;:]+', value) is not None


def https(value):
    require(isinstance(value, str) and not any(ord(c) < 32 or ord(c) == 127 for c in value), 'reporting_url_invalid')
    parsed = urlsplit(value)
    require(parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username and '@' not in parsed.netloc, 'reporting_url_invalid')
    return value


def hash_value(value, length):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is not None


def binding(site, site_id):
    result = {key: site.get(key) for key in BINDING_FIELDS}
    result['site_id'] = site_id
    return result


class Reporter:
    def __init__(self, store, sheets_factory, mail_factory, clock=time.time):
        self.store, self.sheets_factory, self.mail_factory, self.clock = store, sheets_factory, mail_factory, clock
        self.lease_seconds = 300

    def report(self, operation_id):
        uuid(operation_id)
        key = 'operation:' + operation_id
        operation = self.store.get(key)
        require(operation is not None, 'operation_missing')
        existing = self.store.get('reporting:' + operation_id)
        if existing and existing.get('state') in ('complete', 'suppressed', 'needs_attention'):
            return _Report.receipt(existing)
        require(operation.get('status') == 'completed' and operation.get('reporting_required') is True, 'reporting_not_ready')
        require(operation.get('kind') in KINDS, 'reporting_kind_invalid')
        lock_key = 'lease:site:' + operation['site_id']
        lock = self.store.get(lock_key)
        if lock and (lock.get('until', 0) > self.clock() or lock.get('blocked_operation') not in (None, operation_id)):
            raise Busy('site_busy')
        owner, epoch = str(uuid4()), (lock or {}).get('epoch', 0) + 1
        self.store.transact([Write(lock_key, {'owner': owner, 'operation_id': operation_id, 'epoch': epoch,
            'until': self.clock() + self.lease_seconds, 'blocked_operation': operation_id if existing and 'admitted' in existing.get('phases', {}).values() else None}, (lock or {}).get('_version')),
            Write(key, {**operation, 'reporting_lease_owner': owner, 'reporting_lease_epoch': epoch}, operation['_version'])])
        run = _Report(self, key, lock_key, owner, epoch)
        try:
            run.run()
        except Rejected as error:
            # Never let revoked authority skip reconciliation of an admitted write.
            run.refresh()
            reason = str(error) if str(error) in SAFE_REASONS else 'reporting_rejected'
            if run.record and 'admitted' in run.record['phases'].values():
                run.finish('reconciling' if reason in ('operation_cancelled', 'access_revoked') else 'needs_attention', reason)
            else:
                run.finish('suppressed' if reason in ('operation_cancelled', 'access_revoked') else 'needs_attention', reason)
        except Exception:
            run.refresh()
            # Provider exception details may contain credentials; retain fixed codes.
            blocked = bool(run.record and 'admitted' in run.record['phases'].values())
            run.finish('reconciling' if blocked else 'pending', 'provider_readback_required' if blocked else 'reporting_adapter_unavailable')
        return run.public_receipt()


class _Report:
    def __init__(self, reporter, key, lock_key, owner, epoch):
        self.reporter, self.store = reporter, reporter.store
        self.key, self.lock_key, self.owner, self.epoch = key, lock_key, owner, epoch
        self.report_key = 'reporting:' + key.removeprefix('operation:')
        self.refresh()

    def refresh(self):
        self.op = self.store.get(self.key)
        self.lock = self.store.get(self.lock_key)
        self.record = self.store.get(self.report_key)

    def fence(self):
        self.refresh()
        if not self.lock or self.lock.get('owner') != self.owner or self.lock.get('epoch') != self.epoch or self.lock.get('until', 0) <= self.reporter.clock() or self.op.get('reporting_lease_owner') != self.owner or self.op.get('reporting_lease_epoch') != self.epoch:
            raise Busy('reporting_lease_lost')

    def guard(self, new_effect=False):
        self.fence()
        if not new_effect:
            return
        require(not self.op.get('cancel_requested'), 'operation_cancelled')
        self.member = self.store.get('principal:' + self.op['subject'])
        self.site = self.store.get('site:' + self.op['site_id'])
        role = 'publish' if self.op['kind'] == 'publish' else 'edit'
        require(self.member is not None and not self.member.get('disabled') and self.member['_version'] == self.op['member_version'] and role in self.member.get('sites', {}).get(self.op['site_id'], []), 'access_revoked')
        require(self.site is not None and not self.site.get('disabled') and self.site.get('config_version') == self.op['site_config_version'], 'site_configuration_changed')
        frozen = self.record['provider_site'] if self.record else self.op.get('execution_site')
        require(isinstance(frozen, dict) and binding(self.site, self.op['site_id']) == binding(frozen, self.op['site_id']), 'reporting_binding_changed')
        require(not self.site.get('site_id') or self.site['site_id'] == self.op['site_id'], 'reporting_wrong_site')
        require(isinstance(self.site.get('sheet_id'), str) and bool(self.site['sheet_id']) and email(self.site.get('recipient')) and email(self.site.get('operator_email')) and isinstance(self.site.get('operator_subject'), str) and bool(self.site['operator_subject']), 'reporting_binding_invalid')
        evidence = self.evidence(self.site)
        if self.record:
            require(json.loads(self.record['event']['body']) == evidence and self.event_kind == self.record['event_kind'], 'reporting_result_changed')

    def evidence(self, site):
        result = self.op.get('result')
        expected_kind, self.event_kind = KINDS[self.op['kind']]
        require(isinstance(result, dict) and result.get('kind') == expected_kind, 'reporting_result_invalid')
        require(result.get('site_id', self.op['site_id']) == self.op['site_id'], 'reporting_wrong_site')
        data = {'operation_id': self.op['operation_id'], 'site_id': self.op['site_id']}
        if expected_kind == 'workspace':
            workspace = self.store.get('workspace:' + result.get('workspace_id', ''))
            require(workspace is not None and workspace.get('subject') == self.op['subject'] and workspace.get('site_id') == self.op['site_id'] and result.get('workspace_id') == self.op.get('workspace_id') and workspace.get('snapshot_file_id') == result.get('snapshot_file_id') and workspace.get('snapshot_sha256') == result.get('snapshot_sha256') and hash_value(result.get('snapshot_sha256'), 64) and hash_value(result.get('base_commit'), 40), 'reporting_workspace_mismatch')
            data.update(workspace_id=result['workspace_id'], base_commit=result['base_commit'], snapshot_sha256=result['snapshot_sha256'])
        elif expected_kind == 'saved':
            body = self.op['input']
            require(all(result.get(k) == body.get(k) for k in ('workspace_id', 'base_commit', 'bundle_sha256')) and result.get('operation_id') == self.op['operation_id'] and hash_value(result.get('saved_commit'), 40), 'reporting_saved_mismatch')
            data.update(workspace_id=result['workspace_id'], source_commit=result['saved_commit'], bundle_sha256=result['bundle_sha256'])
        else:
            preview = self.store.get('preview:' + result.get('preview_id', ''))
            require(preview is not None and preview.get('site_id') == self.op['site_id'] and preview.get('status') == 'verified' and all(preview.get(k) == result.get(k) and hash_value(result.get(k), size) for k, size in (('source_commit', 40), ('artifact_sha256', 64))), 'reporting_artifact_mismatch')
            if expected_kind == 'preview':
                require(site.get('current_preview') == result['preview_id'] and preview.get('operation_id') == self.op['operation_id'], 'reporting_preview_stale')
                proof = preview.get('validation', {})
                require(proof.get('conclusion') == 'success' and all(proof.get(k) == result.get(k) for k in ('source_commit', 'artifact_sha256')), 'reporting_artifact_unverified')
                data['preview_url'] = https(site.get('dev_url'))
                require(result.get('preview_url') == data['preview_url'] and preview.get('url') == data['preview_url'], 'reporting_url_mismatch')
            else:
                publication = site.get('current_publication')
                require(isinstance(publication, dict) and publication.get('operation_id') == self.op['operation_id'] and result.get('operation_id') == self.op['operation_id'] and all(publication.get(k) == result.get(k) for k in ('preview_id','source_commit','artifact_sha256','main_commit')), 'reporting_publication_stale')
                proof = publication.get('receipt', {})
                require(proof.get('verified') is True and proof.get('artifact_sha256') == result['artifact_sha256'], 'reporting_artifact_unverified')
                data['production_url'] = https(site.get('prod_url'))
            data['preview_url'] = https(site.get('dev_url'))
            data['production_url'] = https(site.get('prod_url'))
            data.update(preview_id=result['preview_id'], source_commit=result['source_commit'], artifact_sha256=result['artifact_sha256'])
        return data

    def request_row(self, data):
        if self.op['kind'] == 'open_workspace':
            return None
        kind = self.op['kind']
        labels = {'save_draft': 'ホームページの変更を下書き保存', 'submit_preview': 'ホームページの確認ページを準備', 'publish': '確認済みホームページを本番公開'}
        summary = self.op.get('summary')
        outcome = ' '.join(summary.split())[:200] if isinstance(summary, str) and summary.strip() else labels[kind]
        target = https(self.site['prod_url'] if kind == 'publish' else self.site['dev_url'])
        if kind == 'save_draft':
            acceptance = '保存済み受領結果と提出ZIPのハッシュ・基準コミットを照合。保存コミット: ' + data['source_commit'] + '、ZIP SHA256: ' + data['bundle_sha256'] + '。公開は別操作。'
        else:
            acceptance = ('公開先の読み戻し' if kind == 'publish' else '検証済みプレビュー') + 'がソースコミット ' + data['source_commit'] + '、成果物SHA256 ' + data['artifact_sha256'] + '、対象URL ' + target + ' と一致すること。'
        return {'request_id': self.op['operation_id'], 'revision': '1', 'site_id': self.op['site_id'],
            'outcome': outcome, 'target': target, 'effective_at': '確認・公開操作に従う', 'expires_at': 'なし',
            'timezone': 'Asia/Tokyo', 'assets_rights': 'この操作の提出ファイルを参照',
            'dependencies': 'この操作の提出ファイルを参照', 'acceptance': acceptance,
            'requester_ref': 'google-sub:' + self.op['subject'],
            'notification_recipient_ref': self.site.get('notification_recipient_ref') or 'site:' + self.op['site_id'] + ':notification',
            'proposal_state': {'save_draft': 'local_draft', 'submit_preview': 'local_preview', 'publish': 'local_publication'}[kind]}

    def create(self):
        self.guard(True)
        data = self.evidence(self.site)
        key = 'hp-control:' + self.op['operation_id'] + ':' + self.event_kind
        event = {'event_id': str(uuid5(NAMESPACE_URL, key)), 'request_id': self.op['operation_id'], 'revision': '1',
            'occurred_at': dt.datetime.fromtimestamp(self.op.get('completed_at', self.op['created_at']), dt.timezone.utc).isoformat(timespec='seconds'),
            'actor': 'hp-control:' + self.op['subject'], 'kind': self.event_kind,
            'body': json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')),
            'reply_to_event_id': '', 'event_idempotency_key': key}
        labels = {'workspace_ready': ('編集用ファイルの準備ができました', 'Codexでホームページの編集を続けられます。'),
            'draft_saved': ('ホームページの変更を保存しました', '変更を下書きとして保存しました。まだ公開はしていません。'),
            'dev_preview_ready': ('ホームページの確認ページができました', '確認ページをご覧いただき、内容をご確認ください。\n' + data.get('preview_url', '')),
            'published': ('ホームページの公開が完了しました', '公開先の表示をご確認ください。\n' + data.get('production_url', ''))}
        subject, body = labels[self.event_kind]
        notice_key = fingerprint({'event_key': key})
        envelope = {'to': self.site['recipient'], 'subject': subject, 'body': body + '\n\n操作ID: ' + self.op['operation_id'] + '\nHP-NOTICE-' + notice_key}
        record = {'operation_id': self.op['operation_id'], 'event_kind': self.event_kind, 'event_key': key,
            'schema_version': 2, 'request': self.request_row(data), 'event': event, 'notice_key': notice_key,
            'envelope': envelope, 'provider_site': {**self.site, 'site_id': self.op['site_id']},
            'phases': {'request': 'not_required' if self.op['kind'] == 'open_workspace' else 'ready', 'sheet': 'ready', 'mail': ('not_required' if self.event_kind not in ('dev_preview_ready', 'published') else 'ready' if self.site.get('mail_enabled') is True else 'disabled')},
            'receipts': {}, 'state': 'pending'}
        record['payload_sha256'] = fingerprint({k:record[k] for k in ('request','event','notice_key','envelope','provider_site')})
        self.store.transact([Write(self.report_key, record, None), Check(self.key, self.op['_version']),
            Check(self.lock_key, self.lock['_version']), Check('principal:' + self.op['subject'], self.member['_version']),
            Check('site:' + self.op['site_id'], self.site['_version'])])
        self.refresh()

    def run(self):
        if not self.record:
            self.create()
        require(self.record['payload_sha256'] == fingerprint({k:self.record[k] for k in ('request','event','notice_key','envelope','provider_site')}), 'reporting_outbox_tampered')
        for phase in ('request', 'sheet', 'mail'):
            self.fence()
            state = self.record['phases'][phase]
            if state in ('done', 'disabled', 'not_required', 'suppressed'):
                continue
            if state == 'ready':
                self.guard(True)
            provider = self.provider(phase)
            found = self.observe(phase, provider)
            if found is not None:
                self.mark(phase, 'done', found)
                continue
            if state == 'admitted':
                raise ReconciliationRequired('reporting_readback_missing')
            self.admit(phase)
            self.guard(True)
            if phase == 'request':
                provider.append_request(self.record['request'])
            elif phase == 'sheet':
                provider.append_event(self.record['event'])
            else:
                provider.send_notice(self.record['envelope'], self.record['notice_key'])
            self.fence()
            found = self.observe(phase, provider)
            if found is None:
                raise ReconciliationRequired('reporting_readback_missing')
            self.mark(phase, 'done', found)
        self.finish('complete')

    def provider(self, phase):
        factory = self.reporter.sheets_factory if phase in ('request', 'sheet') else self.reporter.mail_factory
        if factory is None:
            raise IntegrationUnavailable('reporting_provider_not_configured')
        self.fence()
        site = self.record['provider_site']
        provider = factory(site, self.guard)
        identity = provider.authorized_user()
        require(identity.get('sub') == site['operator_subject'] and isinstance(identity.get('email'), str) and identity['email'].casefold() == site['operator_email'].casefold(), 'reporting_operator_mismatch')
        if phase in ('request', 'sheet'):
            require(provider.spreadsheet_id == site['sheet_id'], 'reporting_wrong_sheet')
            if hasattr(provider, 'set_request_admission'):
                provider.set_request_admission(self.request_admission)
            if hasattr(provider, 'set_event_admission'):
                provider.set_event_admission(self.event_admission)
        else:
            require(isinstance(provider.recipient, str) and provider.recipient.casefold() == site['recipient'].casefold(), 'reporting_wrong_recipient')
            if hasattr(provider, 'set_notice_admission'):
                provider.set_notice_admission(self.notice_admission)
        return provider

    @contextmanager
    def request_admission(self, sheet_id, request_id, revision):
        self.guard(True)
        require(sheet_id == self.record['provider_site']['sheet_id'] and
            request_id == self.op['operation_id'] and revision == '1' and
            self.record['phases']['request'] == 'admitted', 'reporting_admission_mismatch')
        yield
        self.fence()

    @contextmanager
    def event_admission(self, sheet_id, key):
        self.guard(True)
        require(sheet_id == self.record['provider_site']['sheet_id'] and key == self.record['event_key'] and self.record['phases']['sheet'] == 'admitted', 'reporting_admission_mismatch')
        yield
        self.fence()

    @contextmanager
    def notice_admission(self, key):
        self.guard(True)
        require(key == self.record['notice_key'] and self.record['phases']['mail'] == 'admitted' and self.record['provider_site'].get('mail_enabled') is True, 'reporting_admission_mismatch')
        yield
        self.fence()

    def observe(self, phase, provider):
        self.fence()
        if phase == 'request':
            found = provider.find_request(self.op['operation_id'], '1')
            if found is None:
                return None
            require(found == self.record['request'], 'reporting_request_mismatch')
            return {'request_id': found['request_id'], 'revision': '1', 'readback_verified': True}
        if phase == 'sheet':
            found = provider.find_event(self.record['event_key'])
            if found is None:
                return None
            require(found == self.record['event'], 'reporting_event_mismatch')
            return {'event_id': found['event_id'], 'event_key': self.record['event_key'], 'readback_verified': True}
        found = provider.find_notice(self.record['envelope'], self.record['notice_key'])
        if found is None:
            return None
        require(isinstance(found, dict) and found.get('readback_verified') is True and isinstance(found.get('provider_message_id'), str) and bool(found['provider_message_id']), 'reporting_notice_unverified')
        return {'provider_message_id': found['provider_message_id'], 'provider_accepted': True, 'readback_verified': True, 'inbox_delivery': 'unknown'}

    def admit(self, phase):
        self.guard(True)
        record = {**self.record, 'phases': {**self.record['phases'], phase: 'admitted'}, 'state': 'reporting'}
        # This record is also the durable outbox: exact key/envelope precede send.
        self.store.transact([Write(self.report_key, record, self.record['_version']),
            Write(self.lock_key, {**self.lock, 'blocked_operation': self.op['operation_id']}, self.lock['_version']),
            Check(self.key, self.op['_version']), Check('principal:' + self.op['subject'], self.member['_version']),
            Check('site:' + self.op['site_id'], self.site['_version'])])
        self.refresh()

    def mark(self, phase, state, receipt):
        self.fence()
        self.store.transact([Write(self.report_key, {**self.record,
            'phases': {**self.record['phases'], phase: state},
            'receipts': {**self.record['receipts'], phase: receipt}}, self.record['_version']),
            Check(self.key, self.op['_version']), Check(self.lock_key, self.lock['_version'])])
        self.refresh()

    def finish(self, state, reason=None):
        self.fence()
        terminal = state in ('complete', 'suppressed')
        stop_queue = terminal or state == 'needs_attention'
        record = self.record
        if record:
            record = {**record, 'state': state, 'reason': reason}
            if state == 'suppressed':
                record['phases'] = {phase: 'suppressed' if value == 'ready' else value for phase, value in record['phases'].items()}
        else:
            record = {'operation_id': self.op['operation_id'], 'state': state, 'reason': reason, 'phases': {}, 'receipts': {}}
        operation = {**self.op, 'reporting_required': not terminal, 'reporting_state': state,
            'reporting_receipt': self.receipt(record)}
        if stop_queue:
            operation.pop('queue_state', None)
        else:
            attempts = operation.get('reporting_retry_attempts', 0) + 1
            operation.update(queue_state='pending', reporting_retry_attempts=attempts,
                retry_generation=operation.get('retry_generation', 0) + 1,
                retry_at=max(operation.get('retry_at', 0), self.reporter.clock() + min(300, 5 * 2 ** min(attempts - 1, 10))))
        self.store.transact([Write(self.report_key, record, (self.record or {}).get('_version')),
            Write(self.key, operation, self.op['_version']),
            Write(self.lock_key, {**self.lock, 'until': 0, 'blocked_operation': self.op['operation_id'] if state == 'reconciling' or 'admitted' in record.get('phases', {}).values() else None}, self.lock['_version'])])
        self.refresh()

    @staticmethod
    def receipt(record):
        return {'operation_id': record['operation_id'], 'state': record['state'], 'event_kind': record.get('event_kind'),
            'phases': record.get('phases', {}), 'receipts': record.get('receipts', {}), 'reason': record.get('reason')}

    def public_receipt(self):
        return self.receipt(self.record)
