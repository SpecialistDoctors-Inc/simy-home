"""Durable registrar transfers. Registration, site import and publication are distinct.

AuthCodes and contacts stay encrypted. A transfer API timeout is an unknown
outcome, never permission to submit another chargeable transfer.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone

from store import Check, Conflict, Write
from stripe_billing import ACTIVE, valid_subscription_id

QUEUE = 'clinic-transfer-pending'
TERMINAL = {'complete', 'failed', 'cancelled'}


class TransferRejected(ValueError):
    """A documented provider rejection, with no accepted transfer."""


def key(subscription_id):
    if not valid_subscription_id(subscription_id):
        raise ValueError('invalid_subscription')
    return 'clinic-transfer:' + subscription_id


def enqueue_writes(store, intake):
    """Append to the same transaction as the authenticated intake write."""
    sub = intake['subscription_id']
    if not intake.get('auth_code') or intake.get('status') != 'received':
        return []
    current = store.get(key(sub))
    # A changed URL/code must not replace a transfer that could be in flight.
    identity = hashlib.sha256((intake['host'] + '\0' + intake['auth_code']).encode()).hexdigest()
    if current:
        if current['intake_identity'] == identity or current['status'] != 'awaiting_details':
            return []
        return [Write(key(sub), {**current, 'host': intake['host'], 'subject': intake['subject'],
                                'intake_identity': identity, 'required': [
                                    'registrant_contacts', 'dns_continuity', 'transfer_price_acceptance'],
                                'sealed_request': None, 'reason': None}, current['_version'])]
    return [Write(key(sub), {'subscription_id': sub, 'host': intake['host'],
                            'subject': intake['subject'], 'intake_identity': identity,
                            'status': 'awaiting_details', 'created_at': int(time.time()),
                            'required': ['registrant_contacts', 'dns_continuity', 'transfer_price_acceptance']}, None)]


def public_status(row):
    """No provider response bodies, contacts, codes, or operation IDs in the UI."""
    if not row:
        return None
    return {'stage': 'domain_transfer', **{name: row[name] for name in ('status', 'required', 'reason') if name in row}}


def prepare(store, subscription_id, request, cipher, now=None):
    """Called by the authenticated intake layer after contacts/DNS/price checks.

    request must be server-built: DNS continuity comes from a connected provider,
    not an unchecked client boolean. The provider's exact quote is displayed and
    accepted for this domain before this function is called.
    """
    now = int(time.time() if now is None else now)
    row = store.get(key(subscription_id))
    intake = store.get('clinic-intake:' + subscription_id)
    if not row or row['status'] != 'awaiting_details' or not intake:
        raise ValueError('transfer_not_editable')
    identity = hashlib.sha256((intake['host'] + '\0' + intake['auth_code']).encode()).hexdigest()
    if identity != row['intake_identity'] or intake['subject'] != row['subject']:
        raise ValueError('transfer_intake_changed')
    purchase = store.get('stripe-subscription:' + subscription_id)
    if not purchase or purchase.get('subject') != row['subject'] or purchase.get('status') not in ACTIVE:
        raise ValueError('active_purchase_required')
    validate_request(request, intake['host'], now)
    domain_key = 'domain-transfer-owner:' + request['domain']
    owner = store.get(domain_key)
    if owner and owner.get('subscription_id') != subscription_id:
        raise ValueError('domain_transfer_in_use')
    sealed = cipher.encrypt(json.dumps(request, sort_keys=True).encode()).decode()
    pending = store.get(QUEUE)
    jobs = list(pending.get('subscriptions', [])) if pending else []
    if subscription_id not in jobs:
        if len(jobs) >= 1000:
            raise ValueError('transfer_queue_full')
        jobs.append(subscription_id)
    writes = [Write(key(subscription_id), {**row, 'status': 'ready', 'required': [],
                        'domain': request['domain'], 'sealed_request': sealed, 'reason': None, 'retry_at': 0}, row['_version']),
              Check('clinic-intake:' + subscription_id, intake['_version']),
              Check('stripe-subscription:' + subscription_id, purchase['_version']),
              Write(QUEUE, {'subscriptions': jobs}, pending['_version'] if pending else None)]
    if not owner:
        writes.append(Write(domain_key, {'subscription_id': subscription_id}, None))
    store.transact(writes)


def validate_request(request, host, now):
    fields = {'domain', 'contacts', 'nameservers', 'dns_evidence', 'quote', 'accepted_at', 'auto_renew'}
    if not isinstance(request, dict) or set(request) != fields:
        raise ValueError('transfer_details_required')
    if type(request['auto_renew']) is not bool:
        raise ValueError('renewal_choice_required')
    domain = request['domain']
    if (not isinstance(domain, str) or len(domain) > 253 or '.' not in domain
            or not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
                       for label in domain.split('.'))
            or not (host == domain or host.endswith('.' + domain))):
        raise ValueError('invalid_transfer_domain')
    contacts = request['contacts']
    if not isinstance(contacts, dict) or set(contacts) != {'AdminContact', 'RegistrantContact', 'TechContact'}:
        raise ValueError('registrant_contacts_required')
    required = {'FirstName', 'LastName', 'ContactType', 'AddressLine1', 'City', 'CountryCode', 'PhoneNumber', 'Email'}
    for contact in contacts.values():
        if not isinstance(contact, dict) or not required <= set(contact) or any(
                not isinstance(contact.get(k), str) or not contact[k].strip() for k in required):
            raise ValueError('registrant_contacts_required')
    ns = request['nameservers']
    if (not isinstance(ns, list) or not 2 <= len(ns) <= 13 or
            any(not isinstance(n, dict) or set(n) != {'Name'} or not isinstance(n['Name'], str)
                or not re.fullmatch(r'[A-Za-z0-9.-]{1,253}', n['Name']) for n in ns)):
        raise ValueError('verified_nameservers_required')
    proof = request['dns_evidence']
    # The existing DNS provider may discontinue service after a registrar move.
    # Never infer a complete zone from public A/MX lookups or switch NS blindly.
    if (not isinstance(proof, dict) or set(proof) != {'domain', 'nameservers', 'continuity', 'checked_at'}
            or proof['domain'] != domain or proof['nameservers'] != ns
            or proof['continuity'] not in ('independent_dns_confirmed', 'full_zone_migrated_verified')
            or type(proof['checked_at']) is not int or not 0 <= now - proof['checked_at'] <= 3600):
        raise ValueError('dns_continuity_required')
    quote = request['quote']
    if (not isinstance(quote, dict) or set(quote) != {'currency', 'amount'}
            or not isinstance(quote['currency'], str) or not re.fullmatch('[A-Z]{3}', quote['currency'])
            or type(quote['amount']) not in (int, float) or not 0 <= quote['amount'] <= 100000
            or type(request['accepted_at']) is not int or not 0 <= now - request['accepted_at'] <= 3600):
        raise ValueError('transfer_price_acceptance_required')


class Route53Registrar:
    def __init__(self, client):
        self.client = client
        if 'Consent' not in client.meta.service_model.operation_model('TransferDomain').input_shape.members:
            raise ValueError('registrar_sdk_price_cap_unavailable')

    def check(self, domain, code):
        data = self.client.check_domain_transferability(DomainName=domain, AuthCode=code)
        status = data.get('Transferability', {}).get('Transferable')
        if status in ('DONT_KNOW', None):
            raise RuntimeError('registrar_check_pending')
        if status not in ('TRANSFERABLE', 'Transferable'):
            return {'transferable': False}
        price = data.get('Price', {})
        return {'transferable': True, 'quote': {'currency': price.get('Currency'), 'amount': price.get('Price')}}

    def submit(self, request, code):
        # Current API supports Consent: MaxPrice. Do not remove this cap if an
        # older deployed SDK rejects it; upgrade that SDK before enabling writes.
        try:
            return self.client.transfer_domain(DomainName=request['domain'], AuthCode=code,
                Nameservers=request['nameservers'], AutoRenew=request['auto_renew'], **request['contacts'],
                Consent={'MaxPrice': request['quote']['amount'], 'Currency': request['quote']['currency']})['OperationId']
        except Exception as error:
            response = getattr(error, 'response', {})
            if (response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 400
                    and response.get('Error', {}).get('Code') in (
                        'InvalidInput', 'UnsupportedTLD', 'TLDRulesViolation',
                        'DomainLimitExceeded', 'OperationLimitExceeded')):
                raise TransferRejected('registrar_details_rejected') from None
            # DuplicateRequest, transport errors and unknown responses require
            # reconciliation. Never turn them into permission to submit again.
            raise

    def detail(self, operation_id, domain):
        data = self.client.get_operation_detail(OperationId=operation_id)
        if data.get('DomainName') != domain or data.get('Type') != 'TRANSFER_IN_DOMAIN':
            raise ValueError('transfer_operation_mismatch')
        return data['Status']

    def reconcile(self, domain, submitted_at):
        marker, found = None, []
        # Bounded pagination: partial results cannot establish a unique match.
        for _ in range(20):
            args = {'SubmittedSince': datetime.fromtimestamp(submitted_at, timezone.utc),
                    'Type': ['TRANSFER_IN_DOMAIN'], 'MaxItems': 100}
            if marker:
                args['Marker'] = marker
            data = self.client.list_operations(**args)
            found += [r['OperationId'] for r in data.get('Operations', []) if r.get('DomainName') == domain]
            marker = data.get('NextPageMarker')
            if not marker:
                return found[0] if len(found) == 1 else None
        return None


def run_one(store, registrar, cipher, clock=time.time):
    pending = store.get(QUEUE)
    jobs = pending.get('subscriptions', []) if pending else []
    if not jobs:
        return None
    sub = jobs[0]
    # Rotate first: waiting for a customer's confirmation must not starve others.
    try:
        store.put(QUEUE, {'subscriptions': jobs[1:] + jobs[:1]}, pending['_version'])
    except Conflict:
        return sub
    row = store.get(key(sub))
    if not row or row['status'] in TERMINAL or row['status'] == 'awaiting_details':
        current = store.get(QUEUE)
        try:
            store.put(QUEUE, {'subscriptions': [s for s in current['subscriptions'] if s != sub]}, current['_version'])
        except Conflict:
            pass
        return sub
    purchase = store.get('stripe-subscription:' + sub)
    if not purchase or purchase.get('status') not in ACTIVE or purchase.get('subject') != row['subject']:
        return sub
    now = int(clock())
    if row.get('retry_at', 0) > now:
        return sub
    try:
        if row['status'] in ('submitting', 'submission_unknown'):
            operation_id = registrar.reconcile(row['domain'], row['submitted_at'])
            update = {'status': 'transferring', 'operation_id': operation_id} if operation_id else {
                'status': 'submission_unknown', 'reason': 'provider_result_pending', 'retry_at': now + 60}
        elif row['status'] == 'transferring':
            status = registrar.detail(row['operation_id'], row['domain'])
            if status == 'SUCCESSFUL':
                update = {'status': 'complete', 'reason': None, 'completed_at': now}
            elif status in ('FAILED', 'ERROR'):
                update = {'status': 'failed', 'reason': 'registrar_rejected'}
            else:
                update = {'retry_at': now + 60}
        elif row['status'] == 'ready':
            request = json.loads(cipher.decrypt(row['sealed_request'].encode()))
            intake = store.get('clinic-intake:' + sub)
            if not intake or intake['host'] != row['host'] or intake['subject'] != row['subject']:
                return sub
            identity = hashlib.sha256((intake['host'] + '\0' + intake['auth_code']).encode()).hexdigest()
            if identity != row['intake_identity']:
                update = {'status': 'failed', 'reason': 'intake_changed'}
            else:
                try:
                    validate_request(request, row['host'], now)
                except ValueError:
                    store.put(key(sub), {**row, 'status': 'awaiting_details',
                              'required': ['refresh_transfer_details'], 'reason': 'details_expired'}, row['_version'])
                    return sub
                code = cipher.decrypt(intake['auth_code'].encode()).decode()
                check = registrar.check(row['domain'], code)
                if not check.get('transferable'):
                    update = {'status': 'awaiting_details', 'required': ['registrar_unlock_or_supported_route'],
                              'reason': 'not_transferable'}
                elif check.get('quote') != request['quote']:
                    update = {'status': 'awaiting_details', 'required': ['transfer_price_acceptance'],
                              'reason': 'price_changed'}
                else:
                    # A durable write BEFORE the non-idempotent request. A crash
                    # or lost response only enters reconciliation, never resends.
                    store.transact([Write(key(sub), {**row, 'status': 'submitting', 'submitted_at': now}, row['_version']),
                                    Check('stripe-subscription:' + sub, purchase['_version']),
                                    Check('clinic-intake:' + sub, intake['_version'])])
                    row = store.get(key(sub))
                    try:
                        operation_id = registrar.submit(request, code)
                        if not isinstance(operation_id, str) or not operation_id:
                            raise ValueError('missing_provider_operation')
                        update = {'status': 'transferring', 'operation_id': operation_id}
                    except TransferRejected:
                        update = {'status': 'awaiting_details', 'required': ['registrar_details'],
                                  'reason': 'registrar_details_rejected'}
                    except Exception:
                        update = {'status': 'submission_unknown', 'reason': 'provider_result_pending', 'retry_at': now + 60}
        else:
            return sub
        store.put(key(sub), {**row, **update}, row['_version'])
    except Conflict:
        pass
    except Exception:
        # Provider errors often echo request values. Never persist or print them.
        try:
            store.put(key(sub), {**row, 'reason': 'transfer_check_unavailable', 'retry_at': now + 60}, row['_version'])
        except Conflict:
            pass
    return sub
