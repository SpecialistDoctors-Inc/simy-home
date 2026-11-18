import json
import unittest

from hp_control import consume_commands
from owner_notice import OwnerNotifier, wanted
from store import MemoryStore

SITE = {'site_id': 'wordpress-1', 'name': 'clinic.wordpress.com', 'owner_subject': 'email-abc',
        'prod_url': 'https://clinic.wordpress.com'}


def seeded(result=None, notice='pending', email='owner@clinic.example'):
    store = MemoryStore()
    store.put('site:wordpress-1', SITE)
    store.put('principal:email-abc', {'email': email, 'sites': {}, 'disabled': False})
    store.put('operation:op-1', {'operation_id': 'op-1', 'site_id': 'wordpress-1', 'status': 'completed',
                                 'result': result or {'kind': 'published', 'receipt': {'url': SITE['prod_url']}},
                                 'owner_notice': notice})
    return store


class OwnerNoticeTest(unittest.TestCase):
    def test_only_self_service_preview_and_publication_results_are_wanted(self):
        self.assertTrue(wanted(SITE, {'kind': 'preview'}))
        self.assertTrue(wanted(SITE, {'kind': 'published'}))
        for kind in ('saved', 'workspace', 'conflicts', 'no_changes'):
            self.assertFalse(wanted(SITE, {'kind': kind}))
        self.assertFalse(wanted({**SITE, 'reporting_enabled': True}, {'kind': 'published'}))
        self.assertFalse(wanted({k: v for k, v in SITE.items() if k != 'owner_subject'}, {'kind': 'published'}))

    def test_send_failure_is_recorded_and_never_retried(self):
        store = seeded()

        def broken(*_):
            raise RuntimeError('ses down')
        self.assertEqual(OwnerNotifier(store, broken).notify('op-1'), 'failed')
        self.assertEqual(store.get('operation:op-1')['owner_notice'], 'failed')
        self.assertIsNone(OwnerNotifier(store, broken).notify('op-1'))

    def test_recipient_is_the_subscription_address_bound_to_the_owner(self):
        from owner_notice import recipient
        store = seeded(email=None)
        site = {**SITE, 'license_policy': {'mode': 'stripe', 'subscription_id': 'sub_' + 'A' * 24}}
        store.put('stripe-subscription:sub_' + 'A' * 24, {'subject': 'email-abc', 'subject_email': 'Bought@Clinic.example'})
        self.assertEqual(recipient(store, site), 'bought@clinic.example')
        # A subscription bound to someone else is never used.
        store.put('stripe-subscription:sub_' + 'B' * 24, {'subject': 'other', 'subject_email': 'other@clinic.example'})
        self.assertIsNone(recipient(store, {**site, 'license_policy': {'mode': 'stripe', 'subscription_id': 'sub_' + 'B' * 24}}))

    def test_owner_without_a_valid_mailbox_is_skipped(self):
        store = seeded(email='not an address')
        sent = []
        self.assertEqual(OwnerNotifier(store, lambda *a: sent.append(a)).notify('op-1'), 'skipped')
        self.assertEqual(sent, [])

    def test_consumer_mails_after_execution_without_changing_the_delivery_outcome(self):
        store = seeded()
        sent = []

        class Done:
            owner_notices = True

            def __init__(self):
                self.store = store

            def execute(self, operation_id):
                return store.get('operation:' + operation_id)

        event = {'Records': [{'messageId': 'm1', 'body': json.dumps({'operation_id': 'op-1'})}]}
        notifier = OwnerNotifier(store, lambda *a: sent.append(a))
        self.assertEqual(consume_commands(event, None, executor=Done(), notifier=notifier), {'batchItemFailures': []})
        self.assertEqual(len(sent), 1)
        # A redelivery of the same command does not mail again.
        self.assertEqual(consume_commands(event, None, executor=Done(), notifier=notifier), {'batchItemFailures': []})
        self.assertEqual(len(sent), 1)

        # A notifier crash is logged and still leaves the delivery acknowledged.
        store2 = seeded()

        class Exploding:
            def notify(self, _):
                raise RuntimeError('unexpected')
        executor = Done()
        executor.store = store2
        self.assertEqual(consume_commands(event, None, executor=executor, notifier=Exploding()), {'batchItemFailures': []})


if __name__ == '__main__':
    unittest.main()
