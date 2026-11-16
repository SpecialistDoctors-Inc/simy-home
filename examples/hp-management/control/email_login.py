"""One-time email codes: sign in with a mailbox instead of a Google account.

A clinic without a Google account receives a six-digit code at the address it
was invited (or purchased) with. Proving control of that mailbox yields the
principal ``email-<sha256(address)>``; the same address always maps to the same
principal, so a later sign-in on another computer finds the same site grants.
Google principals keep Google's own subject and are never merged with these.

Codes are stored only as a hash bound to the challenge that requested them, are
valid for ten minutes and allow five attempts. Sends are limited per challenge,
per address and per source IP so the form cannot be used to flood a mailbox or
to guess codes across many challenges.
"""
from __future__ import annotations

import re
import secrets
import time

from identity import AuthError, sha
from store import Conflict, Write

EMAIL = re.compile(r'[^\s@<>,;:"()\[\]\\]+@[^\s@<>,;:"()\[\]\\]+\.[^\s@<>,;:"()\[\]\\]+')
CODE_SECONDS = 600
MAX_ATTEMPTS = 5
MAX_SENDS_PER_CHALLENGE = 3
MAX_SENDS_PER_EMAIL_HOUR = 5
MAX_SENDS_PER_IP_HOUR = 20


def normalize_email(value):
    """Return the canonical (casefolded) address, or None when it is not one."""
    if not isinstance(value, str):
        return None
    value = value.strip().casefold()
    if not 6 <= len(value) <= 254 or not EMAIL.fullmatch(value) or any(ord(c) < 33 or ord(c) == 127 for c in value):
        return None
    return value


def email_subject(email):
    """Stable principal for a verified mailbox; distinct from Google's numeric subjects."""
    return 'email-' + sha(email)


def valid_code(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9]{6}', value) is not None


class EmailCodes:
    def __init__(self, store, send, clock=time.time):
        # send(to, code) delivers the message; it must raise on failure.
        self.store, self.send, self.clock = store, send, clock

    def _hash(self, challenge, code):
        return sha('email-code:' + challenge + ':' + code)

    def _count(self, key, limit, now):
        """Consume one unit of an hourly allowance; False once it is spent."""
        row = self.store.get(key)
        if row and row.get('expires_at', 0) > now:
            if row['count'] >= limit:
                return False
            value, expected = {**row, 'count': row['count'] + 1}, row['_version']
        else:
            value, expected = {'count': 1, 'expires_at': now + 3600}, row['_version'] if row else None
        value.pop('_version', None)
        try:
            self.store.transact([Write(key, value, expected)])
        except Conflict:
            return False
        return True

    def issue(self, challenge, email, *, source_ip=None, context=None, deliver=True):
        """Send a fresh code for ``challenge``. Returns False when a limit applies.

        ``context`` is opaque caller data returned unchanged by ``verify``.
        With ``deliver=False`` (an address that may not sign in) the same limits
        and an identical, never-redeemable record are kept, but nothing is
        sent, so answers do not reveal which addresses are registered.
        """
        if not isinstance(challenge, str) or not 16 <= len(challenge) <= 256:
            raise AuthError('expired_login')
        email = normalize_email(email)
        if email is None:
            raise AuthError('invalid_email')
        now = int(self.clock())
        key = 'email-code:' + sha(challenge)
        row = self.store.get(key)
        sends = row['sends'] if row and row.get('expires_at', 0) > now and row.get('email') == email else 0
        if sends >= MAX_SENDS_PER_CHALLENGE:
            return False
        hour = now // 3600
        if not self._count(f'email-rate:{sha(email)}:{hour}', MAX_SENDS_PER_EMAIL_HOUR, now):
            return False
        if isinstance(source_ip, str) and source_ip and not self._count(
                f'email-rate-ip:{sha(source_ip)}:{hour}', MAX_SENDS_PER_IP_HOUR, now):
            return False
        code = f'{secrets.randbelow(1_000_000):06d}'
        value = {'email': email, 'code': self._hash(challenge, code) if deliver else None, 'attempts': 0,
                 'sends': sends + 1, 'context': context or {}, 'expires_at': now + CODE_SECONDS}
        # Rows are overwritten, never deleted, so their version only grows and a
        # stale conditional write can never resurrect an earlier code.
        self.store.transact([Write(key, value, row['_version'] if row else None)])
        if not deliver:
            return True
        # The record precedes delivery: a lost send leaves a code nobody knows,
        # never a delivered code without a record.
        self.send(email, code)
        return True

    def verify(self, challenge, code):
        """Consume a correct code once and return (email, context)."""
        if not isinstance(challenge, str) or not 16 <= len(challenge) <= 256:
            raise AuthError('expired_login')
        key = 'email-code:' + sha(challenge)
        row = self.store.get(key)
        if not row or row.get('expires_at', 0) <= self.clock() or row.get('attempts', 0) >= MAX_ATTEMPTS:
            raise AuthError('expired_email_code')
        code = code.strip() if isinstance(code, str) else code
        if (not valid_code(code) or not isinstance(row.get('code'), str)
                or not secrets.compare_digest(row['code'], self._hash(challenge, code))):
            attempts = row.get('attempts', 0) + 1
            value = {key_: v for key_, v in row.items() if key_ != '_version'}
            # Spend the attempt before answering so parallel guesses cannot share it.
            self.store.transact([Write(key, {**value, 'attempts': attempts}, row['_version'])])
            raise AuthError('invalid_email_code' if attempts < MAX_ATTEMPTS else 'expired_email_code')
        # Consume by replacing the code with a tombstone (not deleting the row):
        # a concurrent wrong guess holding the old version then fails.
        value = {key_: v for key_, v in row.items() if key_ != '_version'}
        self.store.transact([Write(key, {**value, 'code': None, 'context': {}}, row['_version'])])
        return row['email'], row.get('context') or {}


class SesSender:
    """Deliver the code with Amazon SES from one verified sender address."""

    def __init__(self, from_address, client=None):
        if normalize_email(from_address) is None:
            raise ValueError('email_sender_not_configured')
        if client is None:
            import boto3
            client = boto3.client('sesv2')
        self.from_address, self.client = from_address, client

    def __call__(self, to, code):
        body = (f'SIMY HP管理のログイン確認コードは {code} です。\n\n'
                'このコードは10分間有効です。ログイン画面に入力してください。\n'
                'SIMYの担当者がこのコードをお尋ねすることはありません。他の人に伝えないでください。\n'
                'お心当たりのない場合は、このメールを破棄してください。\n')
        self.client.send_email(
            FromEmailAddress=self.from_address, Destination={'ToAddresses': [to]},
            Content={'Simple': {'Subject': {'Data': f'SIMY HP管理 ログイン確認コード {code}', 'Charset': 'UTF-8'},
                                'Body': {'Text': {'Data': body, 'Charset': 'UTF-8'}}}})


# -- sign-in pages for the plugin connection ---------------------------------

PAGE_CSP = ("default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; "
            "form-action 'self'; frame-ancestors 'none'")


def page(status, title, inner, *, refresh=None):
    from html import escape
    head = (f'<meta http-equiv="refresh" content="0;url={escape(refresh, quote=True)}">' if refresh else '')
    body = ('<!doctype html><html lang="ja"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">' + head +
            f'<title>{escape(title)} | SIMY HP管理</title><style>'
            'body{margin:0;background:#f6f7f9;color:#1d2433;font-family:-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif;line-height:1.7}'
            'main{max-width:480px;margin:40px auto;padding:0 16px}.brand{font-weight:600;color:#5b6577;font-size:14px}'
            'h1{font-size:22px;font-weight:600;margin:6px 0 20px}.card{background:#fff;border:1px solid #e3e6eb;border-radius:12px;padding:24px;margin-bottom:16px}'
            'h2{font-size:17px;font-weight:600;margin:0 0 10px}p{margin:0 0 12px}.muted{color:#5b6577;font-size:14px}'
            'label{display:block;font-weight:600;font-size:14px;margin:0 0 4px}'
            'input{width:100%;box-sizing:border-box;font:inherit;padding:10px 12px;border:1px solid #c9ced6;border-radius:8px;margin-bottom:12px}'
            'input.code{font-size:22px;letter-spacing:.3em;text-align:center}'
            '.btn{display:inline-block;background:#0075de;color:#fff;border:0;border-radius:8px;padding:11px 18px;font:inherit;font-weight:600;text-decoration:none;cursor:pointer}'
            '.btn.secondary{background:#fff;color:#1d2433;border:1px solid #c9ced6}'
            '.notice{border-left:3px solid #b54708;padding:8px 12px;background:#fff8f1;margin-bottom:16px;font-size:14px}'
            '</style></head><body><main><div class="brand">SIMY HP管理</div>'
            f'<h1>{escape(title)}</h1>{inner}</main></body></html>')
    return {'statusCode': status, 'headers': {
        'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-content-type-options': 'nosniff',
        # same-origin keeps a real Origin header on our form POSTs.
        'referrer-policy': 'same-origin', 'x-frame-options': 'DENY', 'content-security-policy': PAGE_CSP}, 'body': body}


def choose_page(state, notice=None):
    from html import escape
    from urllib.parse import urlencode
    s = escape(state, quote=True)
    google = '/oauth/login/google?' + urlencode({'state': state})
    banner = f'<div class="notice">{escape(notice)}</div>' if notice else ''
    return page(200, 'HP編集に接続します', banner + (
        '<div class="card"><h2>メールアドレスでログイン</h2>'
        '<p class="muted">登録したメールアドレスに、6桁の確認コードをお送りします。Googleアカウントは不要です。</p>'
        '<form method="post" action="/oauth/login/email">'
        f'<input type="hidden" name="state" value="{s}">'
        '<label for="email">メールアドレス</label>'
        '<input id="email" name="email" type="email" required autocomplete="email" inputmode="email">'
        '<button class="btn" type="submit">確認コードを送る</button></form></div>'
        '<div class="card"><h2>Googleアカウントでログイン</h2>'
        '<p class="muted">Googleアカウントで登録している場合はこちら。</p>'
        f'<a class="btn secondary" href="{escape(google, quote=True)}">Googleでログイン</a></div>'))


def code_page(state, email, notice=None, *, action='/oauth/login/email/verify', resend='/oauth/login/email',
              hidden=None, registered_only=True):
    from html import escape
    fields = ''.join(f'<input type="hidden" name="{escape(k, quote=True)}" value="{escape(v, quote=True)}">'
                     for k, v in (hidden or {'state': state}).items())
    banner = f'<div class="notice">{escape(notice)}</div>' if notice else ''
    # The plugin page must not reveal whether the address may sign in.
    sent = f'{escape(email)} が登録済みの場合、確認コードを送信しました。' if registered_only \
        else f'{escape(email)} に確認コードを送信しました。'
    return page(200, '確認コードを入力', banner + (
        f'<div class="card"><p>{sent}メールに記載の6桁のコードを入力してください。</p>'
        '<p class="muted">コードは10分間有効です。届かない場合は、迷惑メールフォルダーもご確認ください。</p>'
        f'<form method="post" action="{escape(action, quote=True)}">{fields}'
        f'<input type="hidden" name="email" value="{escape(email, quote=True)}">'
        '<label for="code">確認コード</label>'
        '<input id="code" class="code" name="code" required inputmode="numeric" autocomplete="one-time-code" '
        'pattern="[0-9]{6}" maxlength="6">'
        '<button class="btn" type="submit">ログイン</button></form></div>'
        f'<div class="card"><form method="post" action="{escape(resend, quote=True)}">{fields}'
        f'<input type="hidden" name="email" value="{escape(email, quote=True)}">'
        '<button class="btn secondary" type="submit">コードを再送する</button></form></div>'))


def done_page(redirect):
    from html import escape
    return page(200, 'ログインしました', (
        '<div class="card"><p>確認できました。接続を完了しています…</p>'
        f'<p class="muted">画面が切り替わらない場合は <a href="{escape(redirect, quote=True)}" rel="noreferrer">こちら</a> を開いてください。</p></div>'),
        refresh=redirect)


def error_page(title, message, status=400):
    from html import escape
    return page(status, title, f'<div class="card"><p>{escape(message)}</p></div>')


NOTICES = {
    'invalid_email': 'メールアドレスを確認してください。',
    # One message for both: a distinct "expired" answer would reveal which
    # addresses were actually sent a code.
    'invalid_email_code': '確認コードが正しくないか、有効期限が切れています。入力し直すか、コードを再送してください。',
    'expired_email_code': '確認コードが正しくないか、有効期限が切れています。入力し直すか、コードを再送してください。',
    'send_failed': '確認コードのメールを送信できませんでした。少し時間をおいて、もう一度お試しください。',
    'rate_limited': '確認コードの送信回数が上限に達しました。しばらく時間をおいてからお試しください。',
}
