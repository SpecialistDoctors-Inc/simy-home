"""Mail the owner of a self-service site when a preview is ready or a publication finished.

Operator-managed sites report through their request sheet and Gmail
(``reporting_enabled``). A clinic that connected its own WordPress.com site from
the purchase page has no such binding, so without this it would never hear that
its preview is ready or that its change went live.

Delivery is at most once per operation: the operation is moved from
``pending`` to ``sending`` with a compare-and-set before SES is called, and a
crash after that point never resends. A missed notice is preferable to a
duplicate one; the Codex conversation still shows the result either way.
"""
from __future__ import annotations

import json

from email_login import normalize_email
from store import Conflict

KINDS = ('preview', 'published')
FOOTER = ('\nこのメールは送信専用です。ご不明な点は、SIMYの担当者までお問い合わせください。\n'
          'お心当たりのない場合は、このメールを破棄してください。\n')


def wanted(site, result):
    """True when a completed operation on this site should mail its owner."""
    return (site.get('reporting_enabled') is not True and isinstance(site.get('owner_subject'), str)
            and bool(site['owner_subject']) and isinstance(result, dict) and result.get('kind') in KINDS)


def message(site, result):
    name = site.get('name') or site.get('site_id')
    if result['kind'] == 'preview':
        subject = f'SIMY HP管理 確認用の内容ができました（{name}）'
        body = (f'{name} の変更を確認用に反映しました。\n\n'
                'Codexの編集画面で「確認用サイトを開く」を押し、文章・リンク・画像とスマートフォンでの見え方をご確認ください。\n'
                '内容がよければ「公開する」から公開できます。公開するまで、一般の方が見るホームページは変わりません。\n')
    else:
        url = ((result.get('receipt') or {}).get('url') or site.get('prod_url') or '')
        subject = f'SIMY HP管理 ホームページを公開しました（{name}）'
        body = (f'{name} に変更を公開しました。\n\n'
                + (f'公開中のホームページ: {url}\n' if url else '')
                + '表示が変わらない場合は、少し時間をおいてから再読み込みしてください。\n')
    return subject, body + FOOTER


def recipient(store, site):
    """The owner's verified address, or None.

    A self-service owner is created by the purchase page, which records the
    address it verified at sign-in on the subscription (``subject_email``) bound
    to the same subject; the principal itself carries no email. Operator-invited
    principals do carry one, so it is the fallback.
    """
    owner = site.get('owner_subject')
    if not isinstance(owner, str) or not owner:
        return None
    policy = site.get('license_policy') or {}
    subscription_id = policy.get('subscription_id') if policy.get('mode') == 'stripe' else None
    if isinstance(subscription_id, str) and subscription_id:
        from stripe_billing import BillingRejected, subscription_key
        try:
            purchase = store.get(subscription_key(subscription_id)) or {}
        except BillingRejected:
            purchase = {}
        if purchase.get('subject') == owner:
            address = normalize_email(purchase.get('subject_email'))
            if address:
                return address
    return normalize_email((store.get('principal:' + owner) or {}).get('email'))


class OwnerNotifier:
    def __init__(self, store, send):
        self.store, self.send = store, send

    def notify(self, operation_id):
        key = 'operation:' + operation_id
        op = self.store.get(key)
        if not op or op.get('status') != 'completed' or op.get('owner_notice') != 'pending':
            return None
        try:
            self.store.put(key, {**op, 'owner_notice': 'sending'}, op['_version'])
        except Conflict:
            return None  # another delivery reserved it
        site = self.store.get('site:' + op['site_id']) or {}
        to = recipient(self.store, site)
        state = 'skipped'
        if to and wanted(site, op.get('result')):
            subject, body = message(site, op['result'])
            try:
                self.send(to, subject, body)
                state = 'sent'
            except Exception:
                state = 'failed'
        print(json.dumps({'event': 'hp_owner_notice', 'operation_id': operation_id, 'state': state}))
        for _ in range(3):
            current = self.store.get(key)
            if not current or current.get('owner_notice') != 'sending':
                break
            try:
                self.store.put(key, {**current, 'owner_notice': state}, current['_version'])
                break
            except Conflict:
                continue
        return state
