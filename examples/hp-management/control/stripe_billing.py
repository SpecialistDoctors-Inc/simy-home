"""Clinic HP subscriptions bought through Stripe Payment Links.

The clinic page sells HP management with public Payment Links. A completed
Checkout Session from one of the configured links becomes a subscription record
here; its status, kept current by signed Stripe webhooks, is the only license a
clinic site needs. No SIMY organization is involved.

Records:
  stripe-subscription:<sub_id>  plan, customer email, status, bound Google subject
  stripe-event:<evt_id>         processed webhook ids (replay guard)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from urllib.parse import quote
from urllib.error import HTTPError
from urllib.request import Request, build_opener

from licensing import LicenseUnavailable, NoRedirect, valid_google_subject, valid_subscription_id
from store import Conflict, Write

ACTIVE = frozenset({'active', 'trialing'})
# Stripe never reactivates these; once seen, access stays off for that subscription.
TERMINAL = frozenset({'canceled', 'incomplete_expired'})
PENDING_RETENTION = 30 * 86400
KNOWN_STATUSES = frozenset({'active', 'trialing', 'past_due', 'unpaid', 'canceled', 'incomplete',
                            'incomplete_expired', 'paused'})
SIGNATURE_TOLERANCE = 300
EVENT_RETENTION = 30 * 86400


class BillingRejected(ValueError):
    """The request is well-formed but does not describe a usable clinic purchase."""


def valid_session_id(value):
    return isinstance(value, str) and re.fullmatch(r'cs_(?:test|live)_[A-Za-z0-9]{10,200}', value) is not None


def valid_payment_link(value):
    return isinstance(value, str) and re.fullmatch(r'plink_[A-Za-z0-9]{8,64}', value) is not None


def subscription_key(subscription_id):
    if not valid_subscription_id(subscription_id):
        raise BillingRejected('invalid_subscription')
    return 'stripe-subscription:' + subscription_id


class StripeLicenses:
    """License check for sites whose policy names a Stripe subscription."""

    def __init__(self, store):
        self.store = store

    def allowed(self, subscription_id, google_subject):
        if not valid_subscription_id(subscription_id) or not valid_google_subject(google_subject):
            raise LicenseUnavailable('hp_license_unavailable')
        row = self.store.get('stripe-subscription:' + subscription_id)
        return bool(row and not row.get('pending') and row.get('subject') == google_subject
                    and row.get('status') in ACTIVE)


def verify_signature(payload, header, secret, now, tolerance=SIGNATURE_TOLERANCE):
    """Check a Stripe-Signature header (v1 HMAC-SHA256 over "t.payload")."""
    if not isinstance(header, str) or not isinstance(secret, str) or not secret.startswith('whsec_'):
        return False
    timestamp, signatures = None, []
    for part in header.split(','):
        key, _, value = part.strip().partition('=')
        if key == 't' and value.isdigit():
            timestamp = int(value)
        elif key == 'v1' and re.fullmatch(r'[0-9a-f]{64}', value):
            signatures.append(value)
    if timestamp is None or not signatures or abs(now - timestamp) > tolerance:
        return False
    expected = hmac.new(secret.encode(), str(timestamp).encode() + b'.' + payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, candidate) for candidate in signatures)


class StripeApi:
    """Read-only Stripe API calls. The secret key never leaves this object."""

    def __init__(self, secret_key, opener=None):
        self.secret_key = secret_key
        self.opener = opener or build_opener(NoRedirect())

    def checkout_session(self, session_id):
        if not valid_session_id(session_id):
            raise BillingRejected('invalid_session')
        return self.get('/v1/checkout/sessions/' + quote(session_id) + '?expand[]=subscription')

    def subscription(self, subscription_id):
        if not valid_subscription_id(subscription_id):
            raise BillingRejected('invalid_subscription')
        return self.get('/v1/subscriptions/' + quote(subscription_id))

    def get(self, path):
        key = self.secret_key()
        if not isinstance(key, str) or not re.fullmatch(r'(?:sk|rk)_(?:test|live)_[A-Za-z0-9]{10,255}', key):
            raise LicenseUnavailable('hp_license_unavailable')
        request = Request('https://api.stripe.com' + path, headers={'Authorization': 'Bearer ' + key})
        try:
            with self.opener.open(request, timeout=10) as response:
                if response.status != 200:
                    raise ValueError()
                data = response.read(262145)
            if len(data) > 262144:
                raise ValueError()
            return json.loads(data)
        except HTTPError as error:
            if error.code == 404:
                # Stripe does not know this object: not a purchase, not an outage.
                raise BillingRejected('payment_not_confirmed') from None
            raise LicenseUnavailable('hp_license_unavailable') from None
        except Exception:
            raise LicenseUnavailable('hp_license_unavailable') from None


class StripeBilling:
    def __init__(self, store, api, payment_links, clock=time.time):
        if not isinstance(payment_links, dict) or not payment_links or not all(
                valid_payment_link(link) and isinstance(plan, str) and re.fullmatch(r'[a-z_]{1,40}', plan)
                for link, plan in payment_links.items()):
            raise ValueError('payment_links_required')
        self.store, self.api, self.payment_links, self.clock = store, api, dict(payment_links), clock

    def confirmed_session(self, session_id):
        """Ask Stripe for the session; the redirect URL alone never proves payment."""
        return self.record_session(self.api.checkout_session(session_id))

    def record_session(self, session):
        if (not isinstance(session, dict) or session.get('object') != 'checkout.session'
                or session.get('mode') != 'subscription' or session.get('status') != 'complete'
                or session.get('payment_status') not in ('paid', 'no_payment_required')):
            raise BillingRejected('payment_not_confirmed')
        plan = self.payment_links.get(session.get('payment_link'))
        if plan is None:
            raise BillingRejected('unknown_payment_link')
        subscription = session.get('subscription')
        expanded = subscription if isinstance(subscription, dict) else None
        subscription = expanded.get('id') if expanded else subscription
        key = subscription_key(subscription)
        details = session.get('customer_details') if isinstance(session.get('customer_details'), dict) else {}
        email = details.get('email') if isinstance(details.get('email'), str) else None
        for _ in range(3):
            existing = self.store.get(key)
            if existing and not existing.get('pending'):
                if existing.get('session_id') != session.get('id'):
                    raise BillingRejected('subscription_session_mismatch')
                return existing
            if existing and existing.get('status') in TERMINAL:
                status = existing['status']
            else:
                # A pending row means a subscription event raced this purchase; the
                # session's expanded snapshot may predate it, so ask Stripe again.
                status = self.current_status(subscription, None if existing else expanded)
            record = {'subscription_id': subscription, 'session_id': session.get('id'), 'plan': plan,
                      'customer': session.get('customer') if isinstance(session.get('customer'), str) else None,
                      'email': email, 'status': status, 'status_at': int(self.clock()),
                      'subject': None, 'subject_email': None, 'created_at': int(self.clock())}
            try:
                return self.store.put(key, record, existing['_version'] if existing else None)
            except Conflict:
                continue  # re-read: another event or request wrote this subscription meanwhile
        raise Conflict('concurrent_change')

    def current_status(self, subscription_id, expanded=None):
        current = expanded if isinstance(expanded, dict) and 'status' in expanded else self.api.subscription(subscription_id)
        if not isinstance(current, dict) or current.get('id') != subscription_id:
            raise LicenseUnavailable('hp_license_unavailable')
        status = current.get('status')
        return status if status in KNOWN_STATUSES else 'incomplete'

    def bind_subject(self, subscription_id, subject, email):
        """Attach the clinic's Google account to the purchase, once."""
        key = subscription_key(subscription_id)
        row = self.store.get(key)
        if not row or not valid_google_subject(subject):
            raise BillingRejected('subscription_unavailable')
        if row.get('subject') == subject:
            return row
        if row.get('subject') is not None:
            raise BillingRejected('subscription_already_bound')
        return self.store.put(key, {**row, 'subject': subject, 'subject_email': email}, row['_version'])

    def webhook(self, payload, signature, secret):
        """Apply one signed Stripe event. Returns an HTTP status code."""
        if not isinstance(payload, bytes) or not verify_signature(payload, signature, secret, int(self.clock())):
            return 400
        try:
            event = json.loads(payload)
        except ValueError:
            return 400
        if not isinstance(event, dict) or not isinstance(event.get('id'), str) or not isinstance(event.get('data'), dict):
            return 400
        event_key = 'stripe-event:' + hashlib.sha256(event['id'].encode()).hexdigest()
        if self.store.get(event_key):
            return 200
        kind, obj = event.get('type'), event['data'].get('object')
        if not isinstance(obj, dict):
            return 400
        try:
            if kind == 'checkout.session.completed':
                if obj.get('payment_link') in self.payment_links:
                    self.record_session(obj)
            elif kind in ('customer.subscription.created', 'customer.subscription.updated',
                          'customer.subscription.deleted'):
                self.apply_status(obj, int(event.get('created') or 0), deleted=kind.endswith('.deleted'))
        except BillingRejected:
            # Unrelated or not-yet-paid sessions are acknowledged and ignored.
            pass
        except (Conflict, LicenseUnavailable):
            # Not marked processed: Stripe retries the same event.
            return 503
        try:
            self.store.put(event_key, {'type': kind, 'expires_at': int(self.clock()) + EVENT_RETENTION})
        except Conflict:
            pass
        return 200

    def apply_status(self, subscription, created, *, deleted=False):
        sub_id = subscription.get('id')
        if not valid_subscription_id(sub_id):
            raise BillingRejected('invalid_subscription')
        key = subscription_key(sub_id)
        row = self.store.get(key)
        if row and row.get('status') in TERMINAL:
            return
        # Ask Stripe for the current state so delivery order and same-second
        # events cannot resurrect a canceled subscription.
        status = 'canceled' if deleted else self.current_status(sub_id)
        if row is None:
            # The purchase may not be recorded yet. Keep the status (no access)
            # so a later checkout.session.completed cannot start from "active".
            self.store.put(key, {'pending': True, 'subscription_id': sub_id, 'status': status, 'status_at': created,
                                 'expires_at': int(self.clock()) + PENDING_RETENTION})
            return
        self.store.transact([Write(key, {**row, 'status': status, 'status_at': max(created, row.get('status_at', 0))},
                                   row['_version'])])
