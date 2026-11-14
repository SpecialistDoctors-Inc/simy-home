"""Post-payment start page for clinics that bought HP management on simy.one.

The clinic page's Stripe Payment Links redirect to
``/start?session_id={CHECKOUT_SESSION_ID}``. This page:

1. asks Stripe whether that Checkout Session is paid (the URL alone is not proof),
2. signs the clinic in with Google and binds that account to the subscription once,
3. takes the homepage URL and, optionally, the domain's transfer AuthCode,
4. when the operator registered that domain with an owner email equal to the
   signed-in (verified) email, grants read/edit/publish under the subscription.

A clinic whose homepage runs on WordPress.com can instead connect it directly:
the clinic approves SIMY on WordPress.com and the connected site is licensed by
the same subscription (see wordpress_onboarding.py).

Otherwise the URL is kept as an intake: an unknown domain is queued for a copy of
its public homepage (see site_copy.py); a known domain with another owner email
waits for the operator. Once the operator registers the site, reopening this page
completes the claim. AuthCodes are encrypted at rest and never shown again.
"""
from __future__ import annotations

import re
import secrets
import time
from html import escape
from urllib.parse import urlencode

from cryptography.fernet import Fernet

from domain_verification import site_host
from identity import AuthError, sha
from licensing import LicenseUnavailable
from service import Rejected
from site_copy import enqueue as enqueue_copy
from store import Conflict
from stripe_billing import ACTIVE, BillingRejected, valid_session_id
from wordpress_provider import WordPressConnectionError

COOKIE = 'hp_start'
LOGIN_COOKIE = 'hp_start_login'
WORDPRESS_COOKIE = 'hp_start_wordpress'
WORDPRESS_CALLBACK = '/start/wordpress/callback'
SESSION_SECONDS = 3600
GOOGLE_AUTHORIZE = 'https://accounts.google.com/o/oauth2/v2/auth'
PLANS = {
    'basic': ('基本保守', '19,800'),
    'security': ('セキュリティ強化', '29,800'),
    'basic_manager': ('基本保守＋更新代行', '69,600'),
    'security_manager': ('セキュリティ強化＋更新代行', '79,600'),
}
WORDPRESS_NOTICES = {
    'wordpress_declined': 'WordPress.comでの許可が完了しませんでした。もう一度お試しください。',
    'wordpress_wrong_site': '許可したサイトが入力したURLと一致しないか、公開されていません。',
    'wordpress_publish_permission_required': 'このWordPress.comアカウントには、固定ページの編集・公開権限がありません。サイトの管理者アカウントで許可してください。',
    'wordpress_static_homepage_required': 'WordPress.comの設定で、ホームページに固定ページを表示する設定にしてください。',
    'wordpress_homepage_access_required': 'ホームページの固定ページを読み込めませんでした。公開中の固定ページか確認してください。',
    'wordpress_site_grant_required': '「このサイトだけ」を選んで許可してください。',
    'wordpress_site_unavailable': 'このサイトは別のお申し込みで接続済みです。SIMYまでご連絡ください。',
    'wordpress_failed': 'WordPress.comとの接続を完了できませんでした。少し時間をおいて、もう一度お試しください。',
}
CSP = ("default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; base-uri 'none'; "
       "form-action 'self'; frame-ancestors 'none'")


def valid_auth_code(value):
    # Registrar transfer codes are printable ASCII without spaces.
    return isinstance(value, str) and re.fullmatch(r'[\x21-\x7e]{6,64}', value) is not None


def cookie_value(raw, name=COOKIE):
    for part in (raw or '').split(';'):
        key, _, value = part.strip().partition('=')
        if key == name and re.fullmatch(r'[A-Za-z0-9_-]{43}', value):
            return value
    return None


class ClinicOnboarding:
    def __init__(self, store, billing, service, identity, intake_key, *, plugin_url=None, wordpress=None,
                 google_authorize=GOOGLE_AUTHORIZE, secure_cookie=True, clock=time.time):
        self.store, self.billing, self.service, self.identity = store, billing, service, identity
        # Factory for a WordPressOnboarding whose WordPress.com app returns to
        # WORDPRESS_CALLBACK on this origin; None hides the WordPress option.
        self.wordpress = wordpress
        self.cipher = Fernet(intake_key.encode() if isinstance(intake_key, str) else intake_key)
        self.plugin_url = plugin_url if isinstance(plugin_url, str) and plugin_url.startswith('https://') else None
        self.google_authorize, self.secure_cookie, self.clock = google_authorize, secure_cookie, clock
        self.origin = identity.issuer

    # -- HTTP entry points --------------------------------------------------

    def page(self, query, cookie):
        session_id = query.get('session_id')
        if not valid_session_id(session_id):
            return self.html(400, self.error('お申し込みを確認できませんでした', 'simy.one の決済完了画面から開いてください。'))
        try:
            purchase = self.billing.confirmed_session(session_id)
        except BillingRejected:
            return self.html(403, self.error('お支払いを確認できませんでした',
                                             '決済が完了していないか、このページの対象外のお申し込みです。'))
        except LicenseUnavailable:
            return self.html(503, self.error('ただいま確認できません', '少し時間をおいて、このページを再読み込みしてください。'))
        visit = self.visit(cookie, purchase)
        if visit is None:
            return self.html(200, self.sign_in_step(purchase, session_id))
        if purchase.get('status') not in ACTIVE:
            return self.html(200, self.error('契約が有効ではありません', 'お支払い状況をご確認のうえ、SIMYまでご連絡ください。'))
        intake = self.store.get('clinic-intake:' + purchase['subscription_id'])
        if intake and intake.get('status') in ('received', 'needs_review'):
            # The operator may have registered the site since; claim it now.
            intake = self.claim_if_registered(purchase, visit, intake)
        return self.html(200, self.site_step(purchase, visit, intake, session_id, query.get('notice')))

    def google_start(self, query):
        session_id = query.get('session_id')
        if not valid_session_id(session_id):
            raise Rejected('invalid_input')
        self.billing.confirmed_session(session_id)
        state, nonce, browser = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        # Bind the Google round trip to this browser so a callback URL completed
        # by someone else cannot sign this browser into their account (login CSRF).
        self.store.put('login:' + sha(state), {'onboarding_session': session_id, 'nonce': nonce,
                                               'browser': sha(browser), 'expires_at': int(self.clock()) + 600})
        response = self.redirect(self.google_authorize + '?' + urlencode({
            'client_id': self.identity.client_id, 'redirect_uri': self.origin + '/oauth/google/callback',
            'response_type': 'code', 'scope': 'openid email', 'state': state, 'nonce': nonce,
            'prompt': 'select_account'}))
        response['cookies'] = [f'{LOGIN_COOKIE}={browser}; Path=/oauth/google/callback; Max-Age=600; HttpOnly; '
                               'SameSite=Lax' + ('; Secure' if self.secure_cookie else '')]
        return response

    def owns_login(self, state):
        if not isinstance(state, str) or len(state) > 256:
            return False
        login = self.store.get('login:' + sha(state))
        return bool(login and 'onboarding_session' in login)

    def google_callback(self, state, code, cookie):
        key = 'login:' + sha(state)
        login = self.store.get(key)
        if not login or 'onboarding_session' not in login or login['expires_at'] <= self.clock():
            raise AuthError('expired_login')
        browser = cookie_value(cookie, LOGIN_COOKIE)
        if browser is None or not secrets.compare_digest(sha(browser), login.get('browser', '')):
            raise AuthError('expired_login')
        self.store.put(key, None, login['_version'])  # single use
        session_id = login['onboarding_session']
        profile = self.identity.exchange(code, self.origin + '/oauth/google/callback', login['nonce'])
        subject, email = profile.get('sub'), profile.get('email')
        if not isinstance(subject, str) or not profile.get('email_verified') or not isinstance(email, str):
            raise AuthError('invalid_google_identity')
        purchase = self.billing.confirmed_session(session_id)
        try:
            self.billing.bind_subject(purchase['subscription_id'], subject, email)
        except BillingRejected:
            return self.html(403, self.error('別のGoogleアカウントで登録済みです',
                                             'このお申し込みは、最初にログインしたGoogleアカウントで続けてください。'))
        token = secrets.token_urlsafe(32)
        self.store.put('start-session:' + sha(token), {
            'subscription_id': purchase['subscription_id'], 'session_id': session_id, 'subject': subject,
            'email': email, 'expires_at': int(self.clock()) + SESSION_SECONDS})
        response = self.redirect('/start?' + urlencode({'session_id': session_id}))
        flags = '; HttpOnly; SameSite=Lax' + ('; Secure' if self.secure_cookie else '')
        response['cookies'] = [f'{COOKIE}={token}; Path=/start; Max-Age={SESSION_SECONDS}' + flags,
                               f'{LOGIN_COOKIE}=; Path=/oauth/google/callback; Max-Age=0' + flags]
        return response

    def submit_site(self, form, cookie, origin):
        purchase, visit, session_id = self.authorized_post(form, cookie, origin)
        site_url, auth_code = form.get('site_url', '').strip(), form.get('auth_code', '').strip()
        try:
            host = site_host(site_url)
        except ValueError:
            return self.back(session_id, 'invalid_url')
        if auth_code and not valid_auth_code(auth_code):
            return self.back(session_id, 'invalid_auth_code')
        key = 'clinic-intake:' + purchase['subscription_id']
        existing = self.store.get(key)
        if existing and existing.get('status') == 'claimed':
            return self.back(session_id)
        if auth_code:
            sealed = self.cipher.encrypt(auth_code.encode()).decode()
        elif existing and existing.get('host') == host:
            sealed = existing.get('auth_code')  # keep a code already given for the same domain
        else:
            sealed = None
        intake = {'subscription_id': purchase['subscription_id'], 'subject': visit['subject'],
                  'email': visit['email'], 'plan': purchase['plan'], 'site_url': site_url, 'host': host,
                  'auth_code': sealed, 'updated_at': int(self.clock())}
        status = self.register(purchase, visit, site_url).get('status')
        if status == 'claimed':
            intake['status'] = 'claimed'
        elif status == 'site_not_registered':
            # Unknown to SIMY: keep the request and copy the public homepage for the operator.
            same = existing and existing.get('host') == host and existing.get('copy_state') in ('pending', 'done')
            generation = (existing or {}).get('copy_generation', 0)
            intake.update(status='received', **({k: existing.get(k) for k in (
                'copy_state', 'copy_key', 'copy_files', 'copy_truncated', 'copy_attempts', 'copy_generation')}
                if same else {'copy_state': 'pending', 'copy_attempts': 0, 'copy_generation': generation + 1}))
        else:
            # Known domain but a different owner email (or not claimable now): the operator checks.
            intake.update(status='needs_review', copy_generation=(existing or {}).get('copy_generation', 0))
        self.store.put(key, intake, existing['_version'] if existing else None)
        if intake.get('copy_state') == 'pending':
            enqueue_copy(self.store, purchase['subscription_id'], intake['copy_generation'])
        return self.back(session_id)

    def wordpress_start(self, form, cookie, origin):
        purchase, visit, session_id = self.authorized_post(form, cookie, origin)
        if self.wordpress is None:
            raise Rejected('request_rejected')
        intake = self.store.get('clinic-intake:' + purchase['subscription_id'])
        if intake and intake.get('status') == 'claimed':
            return self.back(session_id)
        site_url = form.get('wordpress_url', '').strip()
        try:
            site_host(site_url)
        except ValueError:
            return self.back(session_id, 'invalid_url')
        browser = secrets.token_urlsafe(32)
        # Bind the WordPress.com round trip to this browser and this purchase.
        started = self.wordpress().start_for(self.policy(purchase), visit['subject'], site_url, {
            'onboarding_session': session_id, 'browser': sha(browser)})
        response = self.redirect(started['url'], 303)
        response['cookies'] = [f'{WORDPRESS_COOKIE}={browser}; Path={WORDPRESS_CALLBACK}; Max-Age=600; HttpOnly; '
                               'SameSite=Lax' + ('; Secure' if self.secure_cookie else '')]
        return response

    def wordpress_callback(self, query, cookie):
        if self.wordpress is None:
            raise Rejected('request_rejected')
        state = query.get('state')
        wordpress = self.wordpress()
        try:
            attempt = wordpress.attempt(state)
        except WordPressConnectionError:
            attempt = None
        browser = cookie_value(cookie, WORDPRESS_COOKIE)
        if (attempt is None or 'onboarding_session' not in attempt or browser is None
                or not secrets.compare_digest(sha(browser), attempt.get('browser', ''))):
            raise AuthError('expired_login')
        session_id = attempt['onboarding_session']
        purchase = self.billing.confirmed_session(session_id)
        visit = self.visit(cookie, purchase)
        if visit is None or visit['subject'] != attempt['subject'] or purchase.get('status') not in ACTIVE:
            raise Rejected('authentication_required')
        clear = (f'{WORDPRESS_COOKIE}=; Path={WORDPRESS_CALLBACK}; Max-Age=0; HttpOnly; SameSite=Lax'
                 + ('; Secure' if self.secure_cookie else ''))
        if 'code' not in query:
            # Declined on WordPress.com (error=access_denied) or an incomplete return.
            response = self.back(session_id, 'wordpress_declined')
        else:
            try:
                connected = wordpress.finish_for(self.policy(purchase), visit['subject'], state, query['code'])
            except WordPressConnectionError as error:
                notice = str(error) if str(error) in WORDPRESS_NOTICES else 'wordpress_failed'
                response = self.back(session_id, notice)
            else:
                self.record_wordpress(purchase, visit, connected['origin'])
                response = self.back(session_id)
        response['cookies'] = [clear]
        return response

    def record_wordpress(self, purchase, visit, origin):
        key = 'clinic-intake:' + purchase['subscription_id']
        for _ in range(3):
            existing = self.store.get(key)
            intake = {**(existing or {}), 'subscription_id': purchase['subscription_id'], 'subject': visit['subject'],
                      'email': visit['email'], 'plan': purchase['plan'], 'site_url': origin,
                      'host': site_host(origin), 'provider': 'wordpress', 'status': 'claimed',
                      'auth_code': (existing or {}).get('auth_code') if (existing or {}).get('host') == site_host(origin) else None,
                      'updated_at': int(self.clock())}
            if intake.get('copy_state') == 'pending':
                intake['copy_state'] = None  # nothing to copy: the site is connected as it is
            intake.pop('_version', None)
            try:
                return self.store.put(key, intake, existing['_version'] if existing else None)
            except Conflict:
                continue
        raise Conflict('concurrent_change')

    def claim_if_registered(self, purchase, visit, intake):
        if self.register(purchase, visit, intake['site_url']).get('status') != 'claimed':
            return intake
        try:
            return self.store.put('clinic-intake:' + purchase['subscription_id'],
                                  {**intake, 'status': 'claimed', 'updated_at': int(self.clock())}, intake['_version'])
        except Conflict:
            return self.store.get('clinic-intake:' + purchase['subscription_id'])

    # -- internals ----------------------------------------------------------

    @staticmethod
    def policy(purchase):
        return {'mode': 'stripe', 'subscription_id': purchase['subscription_id']}

    def register(self, purchase, visit, site_url):
        try:
            # visit['email'] is the Google account's verified email (checked at sign-in).
            return self.service.register_by_owner_email(self.policy(purchase), visit['subject'], visit['email'], site_url)
        except (Rejected, LicenseUnavailable, Conflict):
            return {'status': 'registration_unavailable'}

    def visit(self, cookie, purchase):
        token = cookie_value(cookie)
        if token is None:
            return None
        row = self.store.get('start-session:' + sha(token))
        if (not row or row['expires_at'] <= self.clock() or row['subscription_id'] != purchase['subscription_id']
                or row['subject'] != purchase.get('subject')):
            return None
        return row

    def authorized_post(self, form, cookie, origin):
        # The session cookie is SameSite=Lax; also require our own Origin on POSTs.
        if origin != self.origin:
            raise Rejected('request_rejected')
        session_id = form.get('session_id')
        if not valid_session_id(session_id):
            raise Rejected('invalid_input')
        purchase = self.billing.confirmed_session(session_id)
        visit = self.visit(cookie, purchase)
        if visit is None or purchase.get('status') not in ACTIVE:
            raise Rejected('authentication_required')
        return purchase, visit, session_id

    def back(self, session_id, notice=None):
        params = {'session_id': session_id, **({'notice': notice} if notice else {})}
        return self.redirect('/start?' + urlencode(params), 303)

    @staticmethod
    def redirect(location, status=302):
        return {'statusCode': status, 'headers': {'location': location, 'cache-control': 'no-store',
                                                  'referrer-policy': 'same-origin'}, 'body': ''}

    @staticmethod
    def html(status, body):
        return {'statusCode': status, 'headers': {
            'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store',
            # same-origin, not no-referrer: browsers send "Origin: null" on POSTs
            # under no-referrer, and the form POSTs are checked against our origin.
            # Cross-origin requests still carry no referrer (the URL holds the session id).
            'x-content-type-options': 'nosniff', 'referrer-policy': 'same-origin',
            'x-frame-options': 'DENY', 'content-security-policy': CSP}, 'body': body}

    # -- views --------------------------------------------------------------

    @staticmethod
    def layout(title, inner, step=None):
        steps = ''
        if step is not None:
            names = ('お支払い', 'Googleでログイン', 'ホームページの登録', '編集を始める')
            steps = '<ol class="steps">' + ''.join(
                f'<li class="{"done" if i < step else "now" if i == step else ""}">{escape(n)}</li>'
                for i, n in enumerate(names)) + '</ol>'
        return ('<!doctype html><html lang="ja"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>{escape(title)} | SIMY HP管理</title><style>'
                ':root{--fg:#1d2433;--muted:#5b6577;--line:#e3e6eb;--bg:#f6f7f9;--primary:#0075de;--ok:#1a7f37;--warn:#b54708}'
                'body{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif;line-height:1.7}'
                'main{max-width:640px;margin:40px auto;padding:0 16px}.brand{font-weight:600;color:var(--muted);font-size:14px}'
                'h1{font-size:24px;font-weight:600;margin:6px 0 20px}.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:24px;margin-bottom:16px}'
                'h2{font-size:17px;font-weight:600;margin:0 0 10px}p{margin:0 0 12px}.muted{color:var(--muted);font-size:14px}'
                '.steps{display:flex;gap:6px;list-style:none;padding:0;margin:0 0 20px;font-size:12px;color:var(--muted)}'
                '.steps li{flex:1;border-top:3px solid var(--line);padding-top:6px}.steps li.done{border-color:var(--ok);color:var(--ok)}'
                '.steps li.now{border-color:var(--primary);color:var(--fg);font-weight:600}'
                'label{display:block;font-weight:600;font-size:14px;margin:14px 0 4px}input[type=text],input[type=url]{width:100%;box-sizing:border-box;font:inherit;padding:10px 12px;border:1px solid #c9ced6;border-radius:8px}'
                '.btn{display:inline-block;background:var(--primary);color:#fff;border:0;border-radius:8px;padding:11px 18px;font:inherit;font-weight:600;text-decoration:none;cursor:pointer}'
                '.btn.secondary{background:#fff;color:var(--fg);border:1px solid #c9ced6}'
                '.kv{display:grid;grid-template-columns:120px 1fr;gap:4px 12px;font-size:14px}.kv dt{color:var(--muted)}.kv dd{margin:0;word-break:break-all}'
                'code{background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:2px 6px;font-size:13px;word-break:break-all}'
                '.notice{border-left:3px solid var(--warn);padding:8px 12px;background:#fff8f1;margin-bottom:16px;font-size:14px}'
                '.ok{color:var(--ok);font-weight:600}ol.guide{padding-left:20px;margin:0}'
                '</style></head><body><main><div class="brand">SIMY HP管理</div>'
                f'<h1>{escape(title)}</h1>{steps}{inner}</main></body></html>')

    def error(self, title, message):
        return self.layout(title, f'<div class="card"><p>{escape(message)}</p></div>')

    @staticmethod
    def plan_summary(purchase):
        name, price = PLANS.get(purchase.get('plan'), (purchase.get('plan') or '', ''))
        rows = [('プラン', f'{name}（月額 {price}円・税別）' if price else name)]
        if purchase.get('email'):
            rows.append(('決済メール', purchase['email']))
        return '<dl class="kv">' + ''.join(f'<dt>{escape(k)}</dt><dd>{escape(v)}</dd>' for k, v in rows) + '</dl>'

    def sign_in_step(self, purchase, session_id):
        href = '/start/google?' + urlencode({'session_id': session_id})
        bound = purchase.get('subject_email')
        note = (f'<p class="muted">このお申し込みは {escape(bound)} で登録済みです。同じアカウントでログインしてください。</p>'
                if bound else '<p class="muted">ホームページを編集するときに使うGoogleアカウントでログインしてください。'
                              'このアカウントにホームページの編集権限を付与します。</p>')
        return self.layout('お支払いが完了しました', (
            f'<div class="card"><h2>お申し込み内容</h2>{self.plan_summary(purchase)}</div>'
            f'<div class="card"><h2>Googleアカウントでログイン</h2>{note}'
            f'<a class="btn" href="{escape(href, quote=True)}">Googleでログイン</a></div>'), step=1)

    def site_step(self, purchase, visit, intake, session_id, notice):
        sid = escape(session_id, quote=True)
        account = (f'<div class="card"><h2>お申し込み内容</h2>{self.plan_summary(purchase)}'
                   f'<dl class="kv"><dt>Googleアカウント</dt><dd>{escape(visit["email"])}</dd></dl></div>')
        notices = {
            'invalid_url': 'ホームページのURLを確認してください（例: https://www.example-clinic.jp）。',
            'invalid_auth_code': 'AuthCodeは半角英数字・記号6〜64文字で、空白を含めずに入力してください。',
            **WORDPRESS_NOTICES,
        }
        banner = f'<div class="notice">{escape(notices[notice])}</div>' if notice in notices else ''
        status = (intake or {}).get('status')
        if status == 'claimed':
            plugin = (f'<p><a class="btn" href="{escape(self.plugin_url, quote=True)}">HPプラグインをダウンロード</a></p>'
                      if self.plugin_url else '<p class="muted">HPプラグイン（ZIP）は担当者からお送りします。</p>')
            return self.layout('HP編集を始める', account + (
                f'<div class="card"><h2><span class="ok">登録が完了しました</span></h2>'
                f'<dl class="kv"><dt>ホームページ</dt><dd>{escape(intake["site_url"])}</dd>'
                f'<dt>AuthCode</dt><dd>{"受け付け済み（表示しません）" if intake.get("auth_code") else "なし"}</dd></dl></div>'
                '<div class="card"><h2>編集の始め方</h2><ol class="guide">'
                '<li>Codexを開き、ご自身のChatGPTアカウントでログインします。</li>'
                '<li>HPプラグインのZIPをCodexに渡し、「このプラグインを導入してください」と伝えます。</li>'
                f'<li>HPプラグインを選び、{escape(visit["email"])} で接続します。</li>'
                '<li>ホームページが表示されたら「HP編集を始めたい」と伝えます。</li></ol>'
                f'{plugin}</div>'), step=3)
        if status in ('received', 'needs_review'):
            auth = "受け付け済み（表示しません）" if intake.get("auth_code") else "未入力"
            if status == 'needs_review':
                head, body = ('登録情報を確認します',
                              'このドメインはSIMYに登録がありますが、ログイン中のメールアドレスと一致しませんでした。'
                              '担当者が確認し、')
            else:
                copy = {'pending': 'コピー中', 'done': 'コピー済み', 'failed': '担当者が確認します'}.get(intake.get('copy_state'), '')
                head, body = ('ホームページの準備を進めます',
                              'いま公開されているホームページをSIMYにコピーし、編集できる状態に準備します。準備ができましたら、')
            rows = f'<dt>ホームページ</dt><dd>{escape(intake["site_url"])}</dd><dt>AuthCode</dt><dd>{auth}</dd>'
            if status == 'received' and copy:
                rows += f'<dt>コピー</dt><dd>{escape(copy)}</dd>'
            return self.layout('お申し込みを受け付けました', account + banner + (
                f'<div class="card"><h2>{escape(head)}</h2><dl class="kv">{rows}</dl>'
                f'<p class="muted" style="margin-top:12px">{escape(body)}'
                f'{escape(visit["email"])} あてにご連絡します。このページを開き直すと、準備ができ次第そのまま編集を始められます。</p></div>'), step=2)
        wordpress = '' if self.wordpress is None else (
            '<div class="card"><h2>WordPress.comのサイトをお使いの場合</h2>'
            '<p class="muted">WordPress.comでSIMYを許可すると、そのまま編集を始められます。'
            'サイトの管理者アカウントで、このサイトだけを許可してください。</p>'
            f'<form method="post" action="/start/wordpress"><input type="hidden" name="session_id" value="{sid}">'
            '<label for="wordpress_url">WordPress.comサイトのURL</label>'
            '<input id="wordpress_url" name="wordpress_url" type="url" required placeholder="https://example-clinic.wordpress.com" autocomplete="url">'
            '<p style="margin-top:12px"><button class="btn secondary" type="submit">WordPress.comで接続する</button></p></form></div>')
        return self.layout('ホームページを登録します', account + banner + wordpress + (
            '<div class="card"><h2>ホームページの情報</h2>'
            f'<form method="post" action="/start/site"><input type="hidden" name="session_id" value="{sid}">'
            '<label for="site_url">ホームページのURL</label>'
            '<input id="site_url" name="site_url" type="url" required placeholder="https://www.example-clinic.jp" autocomplete="url">'
            '<label for="auth_code">ドメインのAuthCode（移管する場合）</label>'
            '<input id="auth_code" name="auth_code" type="text" autocomplete="off" spellcheck="false" placeholder="例: Ab3$xY9!kQ">'
            '<p class="muted">現在のドメイン管理会社が発行する移管用のコードです。ドメインをSIMYへ移す場合に入力してください。'
            '暗号化して保存し、移管手続き以外には使いません。後から担当者にお伝えいただくこともできます。</p>'
            '<p><button class="btn" type="submit">登録する</button></p></form></div>'), step=2)
