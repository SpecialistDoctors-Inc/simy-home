import hashlib
import hmac
import json
import unittest

from licensing import LicenseUnavailable, site_license_allowed
from store import MemoryStore
from stripe_billing import BillingRejected, StripeBilling, StripeLicenses, verify_signature

SECRET = 'whsec_' + 'k' * 32
LINK = 'plink_' + 'A' * 24
SUB = 'sub_' + 'B' * 24
SESSION = 'cs_test_' + 'C' * 40


def session(**changes):
    value = {'object': 'checkout.session', 'id': SESSION, 'mode': 'subscription', 'status': 'complete',
             'payment_status': 'paid', 'payment_link': LINK, 'subscription': SUB, 'customer': 'cus_1',
             'customer_details': {'email': 'clinic@example.test'}, 'created': 1000}
    value.update(changes)
    return value


def signed(event, now=2000, secret=SECRET):
    payload = json.dumps(event).encode()
    digest = hmac.new(secret.encode(), f'{now}.'.encode() + payload, hashlib.sha256).hexdigest()
    return payload, f't={now},v1={digest}'


class FakeSubscriptions:
    """Stripe's current subscription state, as GET /v1/subscriptions/{id} returns it."""
    def __init__(self):
        self.status, self.available = {}, True

    def subscription(self, subscription_id):
        if not self.available:
            raise LicenseUnavailable('hp_license_unavailable')
        return {'id': subscription_id, 'status': self.status.get(subscription_id, 'active')}


class StripeBillingTest(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.api = FakeSubscriptions()
        self.billing = StripeBilling(self.store, self.api, {LINK: 'basic'}, clock=lambda: 2000)

    def test_signature_requires_the_secret_and_a_fresh_timestamp(self):
        payload, header = signed({'id': 'evt_1'})
        self.assertTrue(verify_signature(payload, header, SECRET, 2000))
        self.assertFalse(verify_signature(payload + b' ', header, SECRET, 2000))
        self.assertFalse(verify_signature(payload, header, 'whsec_other', 2000))
        self.assertFalse(verify_signature(payload, header, SECRET, 2000 + 301))
        self.assertFalse(verify_signature(payload, 'v1=' + 'a' * 64, SECRET, 2000))

    def test_only_paid_sessions_from_configured_links_are_recorded(self):
        for change in ({'payment_status': 'unpaid'}, {'status': 'open'}, {'mode': 'payment'},
                       {'payment_link': 'plink_' + 'Z' * 24}, {'subscription': None}):
            with self.subTest(change=change), self.assertRaises(BillingRejected):
                self.billing.record_session(session(**change))
        self.assertEqual(self.store.rows, {})
        row = self.billing.record_session(session(subscription={'id': SUB, 'status': 'active'}))
        self.assertEqual((row['plan'], row['status'], row['email'], row['subject']),
                         ('basic', 'active', 'clinic@example.test', None))
        self.assertEqual(self.billing.record_session(session())['_version'], 1)
        with self.assertRaises(BillingRejected):
            self.billing.record_session(session(id='cs_test_' + 'D' * 40))

    def test_subject_binds_once_and_license_follows_subscription_status(self):
        self.billing.record_session(session())
        licenses = StripeLicenses(self.store)
        self.assertFalse(licenses.allowed(SUB, 'google-subject'))
        self.billing.bind_subject(SUB, 'google-subject', 'owner@example.test')
        self.billing.bind_subject(SUB, 'google-subject', 'owner@example.test')
        with self.assertRaises(BillingRejected):
            self.billing.bind_subject(SUB, 'other-subject', 'other@example.test')
        site = {'license_policy': {'mode': 'stripe', 'subscription_id': SUB}}
        self.assertTrue(site_license_allowed(site, 'google-subject', None, licenses))
        self.assertFalse(site_license_allowed(site, 'other-subject', None, licenses))
        with self.assertRaises(LicenseUnavailable):
            site_license_allowed(site, 'google-subject', None)

        self.api.status[SUB] = 'past_due'
        updated = {'id': 'evt_due', 'type': 'customer.subscription.updated', 'created': 2500,
                   'data': {'object': {'id': SUB, 'status': 'active'}}}
        self.assertEqual(self.billing.webhook(*signed(updated), SECRET), 200)
        # The payload said active; Stripe's current state wins.
        self.assertFalse(site_license_allowed(site, 'google-subject', None, licenses))
        self.api.status[SUB] = 'canceled'
        cancel = {'id': 'evt_cancel', 'type': 'customer.subscription.deleted', 'created': 3000,
                  'data': {'object': {'id': SUB, 'status': 'canceled'}}}
        self.assertEqual(self.billing.webhook(*signed(cancel), SECRET), 200)
        # A same-second or older "active" event delivered afterwards cannot restore access.
        self.api.status[SUB] = 'active'
        for event_id, created in (('evt_same', 3000), ('evt_stale', 2500)):
            late = {'id': event_id, 'type': 'customer.subscription.updated', 'created': created,
                    'data': {'object': {'id': SUB, 'status': 'active'}}}
            self.assertEqual(self.billing.webhook(*signed(late), SECRET), 200)
        self.assertEqual(self.store.get('stripe-subscription:' + SUB)['status'], 'canceled')
        self.assertFalse(site_license_allowed(site, 'google-subject', None, licenses))

    def test_cancellation_before_checkout_completion_is_kept(self):
        cancel = {'id': 'evt_cancel', 'type': 'customer.subscription.deleted', 'created': 1500,
                  'data': {'object': {'id': SUB, 'status': 'canceled'}}}
        self.assertEqual(self.billing.webhook(*signed(cancel), SECRET), 200)
        pending = self.store.get('stripe-subscription:' + SUB)
        self.assertEqual((pending['pending'], pending['status']), (True, 'canceled'))
        self.assertFalse(StripeLicenses(self.store).allowed(SUB, 'google-subject'))
        row = self.billing.record_session(session(subscription={'id': SUB, 'status': 'active'}))
        self.assertEqual(row['status'], 'canceled')
        self.assertNotIn('pending', row)
        self.assertNotIn('expires_at', row)

    def test_pending_status_is_refreshed_instead_of_trusting_the_session_snapshot(self):
        # The Checkout snapshot says active, but a newer event already stored
        # past_due; converting the pending row must ask Stripe again.
        self.api.status[SUB] = 'past_due'
        event = {'id': 'evt_due', 'type': 'customer.subscription.updated', 'created': 1500,
                 'data': {'object': {'id': SUB, 'status': 'past_due'}}}
        self.assertEqual(self.billing.webhook(*signed(event), SECRET), 200)
        row = self.billing.record_session(session(subscription={'id': SUB, 'status': 'active'}))
        self.assertEqual(row['status'], 'past_due')
        self.billing.bind_subject(SUB, 'google-subject', 'owner@example.test')
        self.assertFalse(StripeLicenses(self.store).allowed(SUB, 'google-subject'))

    def test_events_are_retried_when_stripe_cannot_be_asked(self):
        self.billing.record_session(session())
        self.api.available = False
        event = {'id': 'evt_retry', 'type': 'customer.subscription.updated', 'created': 3000,
                 'data': {'object': {'id': SUB, 'status': 'canceled'}}}
        self.assertEqual(self.billing.webhook(*signed(event), SECRET), 503)
        self.api.available = True
        self.api.status[SUB] = 'canceled'
        self.assertEqual(self.billing.webhook(*signed(event), SECRET), 200)
        self.assertEqual(self.store.get('stripe-subscription:' + SUB)['status'], 'canceled')

    def test_webhook_records_checkout_ignores_others_and_rejects_bad_signatures(self):
        completed = {'id': 'evt_done', 'type': 'checkout.session.completed', 'created': 1000,
                     'data': {'object': session()}}
        payload, header = signed(completed)
        self.assertEqual(self.billing.webhook(payload, header.replace('v1=', 'v1=0'), SECRET), 400)
        self.assertEqual(self.store.rows, {})
        self.assertEqual(self.billing.webhook(payload, header, SECRET), 200)
        self.assertEqual(self.store.get('stripe-subscription:' + SUB)['status'], 'active')
        other = {'id': 'evt_other', 'type': 'checkout.session.completed', 'created': 1000,
                 'data': {'object': session(payment_link=None, subscription='sub_' + 'E' * 24)}}
        self.assertEqual(self.billing.webhook(*signed(other), SECRET), 200)
        self.assertIsNone(self.store.get('stripe-subscription:sub_' + 'E' * 24))
        unknown = {'id': 'evt_unknown', 'type': 'customer.subscription.updated', 'created': 5000,
                   'data': {'object': {'id': 'sub_' + 'F' * 24, 'status': 'active'}}}
        self.assertEqual(self.billing.webhook(*signed(unknown), SECRET), 200)
        # Unknown subscriptions keep only an expiring, access-free status row.
        pending = self.store.get('stripe-subscription:sub_' + 'F' * 24)
        self.assertTrue(pending['pending'])
        self.assertFalse(StripeLicenses(self.store).allowed('sub_' + 'F' * 24, 'google-subject'))


if __name__ == '__main__':
    unittest.main()
