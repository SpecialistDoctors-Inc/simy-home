"""Authenticated signup-to-transfer bridge. No client-supplied DNS proof or price."""
import hashlib
import json
import secrets
import time
import re
import phonenumbers
from html import escape
from urllib.parse import urlencode

from domain_transfer import key, prepare, validate_request
from store import Check, Write

CONTACT_FIELDS = {
    'LastName': '姓（ローマ字）', 'FirstName': '名（ローマ字）',
    'OrganizationName': '法人名・医院名', 'ZipCode': '郵便番号', 'State': '都道府県',
    'City': '市区町村', 'AddressLine1': '番地・建物名',
    'CountryCode': '国・地域（日本：JP）', 'PhoneNumber': '電話番号', 'Email': '連絡先メールアドレス',
}


class TransferInput(ValueError):
    pass


class TransferIntake:
    def __init__(self, store, registrar, cipher, clock=time.time, connection_start=None):
        self.store, self.registrar, self.cipher, self.clock = store, registrar, cipher, clock
        # Internal path to a configured provider connection flow. It must bind
        # its OAuth state to the same subject/purchase before recording proof.
        if connection_start is not None and not (
                isinstance(connection_start, str) and connection_start.startswith('/start/connect/')
                and '?' not in connection_start and '#' not in connection_start):
            raise ValueError('invalid_connection_start')
        self.connection_start = connection_start

    def intake(self, purchase, visit):
        sub = purchase['subscription_id']
        intake = self.store.get('clinic-intake:' + sub)
        if (not intake or intake.get('subject') != visit['subject'] or not intake.get('auth_code')
                or intake.get('status') != 'received'):
            raise TransferInput('transfer_unavailable')
        return intake

    def dns(self, purchase, visit, intake):
        # Written only by a server-side DNS connector after provider-account,
        # full-zone continuity and delegation verification. Never a browser POST.
        proof = self.store.get('dns-connection:' + purchase['subscription_id'])
        if (not proof or proof.get('subject') != visit['subject'] or proof.get('host') != intake['host']
                or proof.get('status') != 'verified' or type(proof.get('checked_at')) is not int
                or not 0 <= self.clock() - proof['checked_at'] <= 3600):
            raise TransferInput('dns_connection_required')
        return proof

    def quote(self, purchase, visit):
        intake = self.intake(purchase, visit)
        dns = self.dns(purchase, visit, intake)
        try:
            result = self.registrar.check(dns['domain'], self.cipher.decrypt(intake['auth_code'].encode()).decode())
        except Exception:
            raise TransferInput('quote_unavailable') from None
        price = result.get('quote')
        if not result.get('transferable') or not isinstance(price, dict):
            raise TransferInput('transfer_not_available')
        # Validate the quote before allowing it into the rendered page.
        if (set(price) != {'currency', 'amount'} or not isinstance(price['currency'], str)
                or len(price['currency']) != 3 or not price['currency'].isupper()
                or type(price['amount']) not in (int, float) or not 0 <= price['amount'] <= 100000):
            raise TransferInput('quote_unavailable')
        identifier = secrets.token_urlsafe(32)
        row = {'subject': visit['subject'], 'subscription_id': purchase['subscription_id'],
               'domain': dns['domain'], 'host': intake['host'], 'quote': price,
               'intake_hash': hashlib.sha256(intake['auth_code'].encode()).hexdigest(),
               'dns_version': dns['_version'], 'expires_at': int(self.clock()) + 600}
        self.store.put('transfer-quote:' + identifier, row)
        return {'quote_id': identifier, **price}

    def accept(self, purchase, visit, form):
        intake = self.intake(purchase, visit)
        dns = self.dns(purchase, visit, intake)
        quote_id = form.get('quote_id', '')
        if not isinstance(quote_id, str) or len(quote_id) != 43:
            raise TransferInput('quote_expired')
        quote = self.store.get('transfer-quote:' + quote_id)
        if (not quote or quote.get('subject') != visit['subject']
                or quote.get('subscription_id') != purchase['subscription_id']
                or quote.get('domain') != dns['domain'] or quote.get('host') != intake['host']
                or quote.get('dns_version') != dns['_version'] or quote['expires_at'] <= self.clock()
                or quote.get('intake_hash') != hashlib.sha256(intake['auth_code'].encode()).hexdigest()):
            raise TransferInput('quote_expired')
        if form.get('accept_transfer') != 'yes':
            raise TransferInput('transfer_acceptance_required')
        contact = {name: form.get(name, '') for name in CONTACT_FIELDS}
        if any(not isinstance(value, str) or len(value) > 256 for value in contact.values()):
            raise TransferInput('invalid_contacts')
        contact = {name: value.strip() for name, value in contact.items()}
        contact['ContactType'] = form.get('ContactType', '')
        if contact['ContactType'] not in ('PERSON', 'COMPANY'):
            raise TransferInput('invalid_contacts')
        if contact['ContactType'] == 'COMPANY' and not contact['OrganizationName']:
            raise TransferInput('invalid_contacts')
        if (not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', contact['Email'])
                or not re.fullmatch(r'[A-Z]{2}', contact['CountryCode'])):
            raise TransferInput('invalid_contacts')
        try:
            phone = phonenumbers.parse(contact['PhoneNumber'], contact['CountryCode'])
            if not phonenumbers.is_valid_number(phone) or phone.extension:
                raise ValueError()
            contact['PhoneNumber'] = '+' + str(phone.country_code) + '.' + phonenumbers.national_significant_number(phone)
        except (ValueError, phonenumbers.NumberParseException):
            raise TransferInput('invalid_contacts') from None
        request = {'domain': dns['domain'], 'nameservers': dns['nameservers'],
                   'contacts': {name: dict(contact) for name in ('AdminContact', 'RegistrantContact', 'TechContact')},
                   'dns_evidence': {name: dns[name] for name in ('domain', 'nameservers', 'continuity', 'checked_at')},
                   'quote': quote['quote'], 'accepted_at': int(self.clock()),
                   'auto_renew': form.get('auto_renew') == 'yes'}
        try:
            validate_request(request, intake['host'], int(self.clock()))
        except ValueError:
            raise TransferInput('invalid_contacts') from None
        # Prepare and quote consumption share one transaction. A lost browser
        # response cannot reuse the same quote for a later transfer request.
        prepare(self.store, purchase['subscription_id'], request, self.cipher, self.clock(),
                extra_checks=[Check('dns-connection:' + purchase['subscription_id'], dns['_version'])],
                extra_writes=[Write('transfer-quote:' + quote_id, None, quote['_version'])])

    def render(self, purchase, visit, session_id, notice=None):
        try:
            intake = self.intake(purchase, visit)
        except TransferInput:
            return None
        row = self.store.get(key(purchase['subscription_id']))
        if not row:
            return None
        if row['status'] == 'complete':
            activation = self.store.get('clinic-activation:' + purchase['subscription_id'])
            if activation and activation.get('status') == 'failed':
                return ('<div class="card"><h2>ホームページの取り込みに接続が必要です</h2>'
                        '<p>公開ページだけでは取り込めない内容があるため、現在のHP管理サービスとの接続を確認します。</p></div>')
            if activation and activation.get('status') in ('preparing_hosting', 'verifying_connection', 'waiting_copy'):
                return ('<div class="card"><h2>ホームページの編集環境を準備しています</h2>'
                        '<ol class="guide"><li>ホームページを取り込む</li><li>編集用・確認用の環境を作る</li>'
                        '<li>公開先への接続を確認する</li></ol><p class="muted">このページを開き直すと、準備状況を確認できます。公開中のHPはまだ切り替わりません。</p></div>')
        if row['status'] != 'awaiting_details':
            labels = {'ready': '移管の申請を準備しています', 'submitting': '移管を申請しています',
                      'submission_unknown': '移管先で受付状況を確認しています', 'transferring': '移管先で手続き中です',
                      'complete': 'ドメインの移管が完了しました', 'failed': '移管先の確認が必要です'}
            return '<div class="card"><h2>' + labels.get(row['status'], '状況を確認しています') + (
                '</h2><p>ホームページの編集準備と公開先の接続は、この後に確認します。</p>'
                '<p class="muted">移管先から確認メールが届いた場合は、メール内の案内に従ってください。このページで続きの状況を確認できます。</p></div>')
        try:
            dns = self.dns(purchase, visit, intake)
        except TransferInput:
            link = ('<a class="btn" href="' + escape(self.connection_start + '?' + urlencode({'session_id': session_id}), quote=True)
                    + '">現在の管理サービスに接続する →</a>') if self.connection_start else ''
            return ('<div class="card"><h2>現在の管理サービスを確認します</h2>'
                    '<p>ホームページやメールの設定を引き継ぐため、現在の管理サービスへの接続が必要です。</p>'
                    + link + '</div>')
        cached = self.store.get('transfer-form:' + purchase['subscription_id'])
        quote = self.store.get('transfer-quote:' + cached['quote_id']) if cached else None
        if (not quote or quote.get('expires_at', 0) <= self.clock() or quote.get('subject') != visit['subject']
                or quote.get('intake_hash') != hashlib.sha256(intake['auth_code'].encode()).hexdigest()):
            return ('<div class="card"><h2>移管に必要な情報を確認します</h2>'
                    '<form method="post" action="/start/transfer/quote">'
                    f'<input type="hidden" name="session_id" value="{escape(session_id, quote=True)}">'
                    '<button class="btn" type="submit">移管費用を確認する →</button></form></div>')
        messages = {'invalid_contacts': '登録者の情報をご確認ください。', 'quote_expired': '最新の移管費用をもう一度ご確認ください。',
                    'transfer_acceptance_required': '移管内容と費用をご確認ください。'}
        error = ('<p role="alert">' + messages[notice] + '</p>') if notice in messages else ''
        known = dns.get('registrant_contact') if isinstance(dns.get('registrant_contact'), dict) else {}
        defaults = {k: known[k] if isinstance(known.get(k), str) else visit['email'] if k == 'Email' else ''
                    for k in CONTACT_FIELDS}
        country = known.get('CountryCode') if isinstance(known.get('CountryCode'), str) else 'JP'
        fields = ''.join(f'<label for="transfer-{k}">{v}</label><input type="text" id="transfer-{k}" name="{k}" '
                         f'value="{escape(defaults[k], quote=True)}" '
                         f'{"" if k == "OrganizationName" else "required"} maxlength="256">' for k, v in CONTACT_FIELDS.items() if k != 'CountryCode')
        fields += ('<details' + (' open' if country != 'JP' else '') +
                   '><summary>日本以外の住所で登録する場合</summary><label for="transfer-CountryCode">国・地域のコード</label>'
                   f'<input type="text" id="transfer-CountryCode" name="CountryCode" value="{escape(country, quote=True)}" maxlength="2" required></details>')
        return ('<div class="card"><h2>移管に必要な情報を確認します</h2>' + error +
                '<p>' + escape(quote['domain']) + '</p>' +
                '<p>ドメインの登録者情報をご確認ください。取得できた情報は反映しています。足りない項目や変更箇所だけ入力してください。</p>'
                '<form method="post" action="/start/transfer">'
                f'<input type="hidden" name="session_id" value="{escape(session_id, quote=True)}">'
                f'<input type="hidden" name="quote_id" value="{escape(cached["quote_id"], quote=True)}">'
                '<label for="transfer-type">登録者</label><select id="transfer-type" name="ContactType">'
                '<option value="COMPANY"' + (' selected' if known.get('ContactType') != 'PERSON' else '') + '>医院・法人</option>'
                '<option value="PERSON"' + (' selected' if known.get('ContactType') == 'PERSON' else '') + '>個人</option></select>' + fields +
                f'<p><strong>今回の移管費用：{quote["quote"]["amount"]:,.2f} {escape(quote["quote"]["currency"])}</strong></p>'
                '<p class="muted">HP管理の月額料金とは別に発生します。</p>'
                '<label><input style="width:auto" type="checkbox" name="auto_renew" value="yes">ドメインの自動更新を有効にする</label>'
                '<label><input style="width:auto" type="checkbox" name="accept_transfer" value="yes" required>登録者情報と今回の移管費用を確認し、移管を申し込みます</label>'
                '<p><button class="btn" type="submit">移管と利用準備を開始する →</button></p></form></div>')
