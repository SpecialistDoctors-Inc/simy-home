"""Claim an operator-prepared clinic site and tell the clinic it is ready.

A clinic that paid through a Payment Link and gave a homepage SIMY had not
prepared yet keeps an intake in ``received`` (or ``needs_review``), and /start
promises to email it once the homepage is ready. After the operator has built
the site, registered ``registration-site:<host>`` for the clinic's mailbox
(``provision_site.py --enable-domain-registration --owner-email``) and deployed
its claim targets, ``notify_clinic_ready.py`` invokes the API Lambda directly
(never over HTTP) to run ``ClinicReady.notify``:

1. claim the site exactly as reopening /start would, with the Google subject and
   verified sign-in email the intake recorded,
2. mark the intake claimed, and
3. email that mailbox, with the clinic's own /start link, recording the send so
   reruns do not repeat it.

Every step is idempotent, so the operator can rerun the command after fixing
whatever it reported.
"""
from __future__ import annotations

import time
from urllib.parse import urlencode

from licensing import LicenseUnavailable
from service import Rejected
from store import Conflict
from stripe_billing import ACTIVE, BillingRejected, subscription_key

OPEN_INTAKE = ('received', 'needs_review')
# Well past the API Lambda's 29 s timeout: an older 'sending' mark was interrupted.
STALE_SENDING_SECONDS = 300


class ClinicReady:
    def __init__(self, store, service, send, base_url, clock=time.time):
        # send(to, subject, body) delivers one plain-text mail; None skips mail.
        self.store, self.service, self.send = store, service, send
        self.base_url, self.clock = base_url.rstrip('/'), clock

    def notify(self, subscription_id):
        try:
            purchase = self.store.get(subscription_key(subscription_id))
        except BillingRejected:
            return {'status': 'invalid_subscription'}
        if not purchase or purchase.get('pending') or not purchase.get('session_id'):
            return {'status': 'subscription_not_found'}
        if purchase.get('status') not in ACTIVE:
            return {'status': 'subscription_inactive'}
        key = 'clinic-intake:' + subscription_id
        intake = self.store.get(key)
        if not intake:
            return {'status': 'intake_not_found'}
        if intake.get('provider') == 'wordpress':
            return {'status': 'not_applicable'}  # WordPress.com sites are claimed during onboarding
        if intake.get('subject') != purchase.get('subject'):
            return {'status': 'subject_mismatch'}
        if intake.get('status') in OPEN_INTAKE:
            claimed = self.claim(purchase, intake)
            if claimed.get('status') != 'claimed':
                return claimed
            intake = claimed['intake']
        elif intake.get('status') != 'claimed':
            return {'status': 'intake_not_ready'}
        site = {'site_url': intake['site_url'], 'host': intake['host']}
        mail = intake.get('ready_mail')
        if mail == 'sent':
            return {'status': 'already_notified', **site}
        if self.send is None:
            return {'status': 'claimed', 'mail': 'not_configured', **site}
        now = int(self.clock())
        if mail == 'sending' and intake.get('ready_mail_at', 0) > now - STALE_SENDING_SECONDS:
            return {'status': 'mail_in_progress', **site}
        # Mark the send before delivering so concurrent reruns do not both mail.
        # A send interrupted before it is recorded (e.g. a Lambda timeout) goes
        # stale and is retried: at worst the clinic gets the same mail twice.
        try:
            self.store.put(key, {**intake, 'ready_mail': 'sending', 'ready_mail_at': now}, intake['_version'])
        except Conflict:
            return {'status': 'retry'}
        try:
            self.send(intake['email'], *self.message(purchase, intake))
        except Exception:
            self.record(key, {'ready_mail': 'failed'})
            return {'status': 'mail_failed', **site}
        if not self.record(key, {'ready_mail': 'sent', 'ready_notified_at': int(self.clock())}):
            return {'status': 'notified_unrecorded', **site}
        return {'status': 'notified', **site}

    def record(self, key, fields):
        """Merge mail state into the intake, surviving unrelated concurrent updates."""
        for _ in range(5):
            current = self.store.get(key)
            if not current:
                return False
            try:
                self.store.put(key, {**current, **fields}, current['_version'])
                return True
            except Conflict:
                continue
        return False

    def claim(self, purchase, intake):
        policy = {'mode': 'stripe', 'subscription_id': purchase['subscription_id']}
        try:
            # intake['email'] is the identity provider's verified email recorded at sign-in.
            result = self.service.register_by_owner_email(policy, intake['subject'], intake['email'],
                                                          intake['site_url'])
        except LicenseUnavailable:
            # Most often: this site's claim targets are not deployed yet.
            return {'status': 'site_unavailable'}
        except (Rejected, Conflict) as error:
            return {'status': str(error) or 'registration_unavailable'}
        if result.get('status') != 'claimed':
            return {'status': result.get('status', 'registration_unavailable')}
        key = 'clinic-intake:' + purchase['subscription_id']
        for _ in range(3):
            current = self.store.get(key)
            # The clinic may have submitted another URL meanwhile. Never mark that
            # one claimed with this result; a rerun evaluates the new URL.
            if not current or current.get('site_url') != intake['site_url']:
                return {'status': 'intake_changed'}
            if current.get('status') == 'claimed':
                return {'status': 'claimed', 'intake': current}
            try:
                return {'status': 'claimed', 'intake': self.store.put(
                    key, {**current, 'status': 'claimed', 'updated_at': int(self.clock())}, current['_version'])}
            except Conflict:
                continue
        return {'status': 'retry'}

    def message(self, purchase, intake):
        start = self.base_url + '/start?' + urlencode({'session_id': purchase['session_id']})
        subject = '【SIMY】ホームページの編集の準備ができました'
        body = (
            'SIMY HP管理をお申し込みいただき、ありがとうございます。\n\n'
            f'ご登録のホームページ（{intake["site_url"]}）を編集できる準備ができました。\n\n'
            '次のページを開き、お申し込み時と同じアカウント'
            f'（{intake["email"]}）でログインすると、HPプラグインのダウンロードと編集の始め方をご確認いただけます。\n'
            f'{start}\n\n'
            'ご不明な点は、このメールへの返信ではなく、SIMYの担当者までお問い合わせください。\n'
            'お心当たりのない場合は、このメールを破棄してください。\n')
        return subject, body


class SesMail:
    """Send one plain-text mail from the SES-verified sign-in sender."""

    def __init__(self, from_address, client=None):
        if client is None:
            import boto3
            client = boto3.client('sesv2')
        self.from_address, self.client = from_address, client

    def __call__(self, to, subject, body):
        self.client.send_email(
            FromEmailAddress=self.from_address, Destination={'ToAddresses': [to]},
            Content={'Simple': {'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                                'Body': {'Text': {'Data': body, 'Charset': 'UTF-8'}}}})


def readiness(store, subscription_id, claim_targets):
    """Read-only operator check of what notify() would find. Sends and writes nothing."""
    from domain_verification import site_host
    try:
        purchase = store.get(subscription_key(subscription_id))
    except BillingRejected:
        return {'subscription': 'invalid'}
    intake = store.get('clinic-intake:' + subscription_id) or {}
    report = {'subscription': (purchase or {}).get('status', 'not_found'),
              'intake': intake.get('status', 'not_found'),
              'site_url': intake.get('site_url'),
              'ready_mail': intake.get('ready_mail')}
    try:
        host = site_host(intake.get('site_url') or '')
    except ValueError:
        return report
    binding = store.get('registration-site:' + host)
    if not binding:
        return {**report, 'registration': 'missing'}
    owner = binding.get('owner_email')
    site = binding['site']
    targets = claim_targets.get(site['site_id'], {})
    deployed = set(targets) == {'dev', 'prod'} and all(
        site['deployment'][env]['bucket'] == target['bucket']
        and site['deployment'][env]['distribution_id'] == target['distribution']
        for env, target in targets.items())
    return {**report, 'registration': 'present', 'site_id': site['site_id'],
            'owner_matches': isinstance(owner, str) and owner.casefold() == str(intake.get('email', '')).casefold(),
            'claim_targets': 'deployed' if deployed else 'missing'}
