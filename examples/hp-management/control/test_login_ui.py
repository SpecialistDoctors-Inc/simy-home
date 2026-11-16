"""Page structure of the sign-in card and the site-type switch."""
import re
import types
import unittest

from clinic_onboarding import ClinicOnboarding
from email_login import choose_page

PURCHASE = {'plan': 'basic', 'email': 'buyer@example.test'}
VISIT = {'email': 'buyer@example.test'}


def onboarding(*, email=True, wordpress=True):
    # Only the attributes the page builders read.
    onboarding = object.__new__(ClinicOnboarding)
    onboarding.identity = types.SimpleNamespace(email_codes=object() if email else None)
    onboarding.wordpress = object() if wordpress else None
    onboarding.plugin_url = None
    return onboarding


def cards(html, cls):
    return re.findall(rf'<div class="card {cls}">(.*?)</div>(?=<div class="card|</main>)', html, re.S)


class LoginCardTest(unittest.TestCase):
    def assert_one_card_with_both(self, html, google, action):
        [card] = cards(html, 'login')
        self.assertLess(card.index(f'href="{google}'), card.index('または'))
        self.assertLess(card.index('または'), card.index(f'action="{action}"'))
        self.assertIn('name="email"', card)

    def test_plugin_page_offers_both_methods_in_one_card(self):
        self.assert_one_card_with_both(choose_page('st')['body'], '/oauth/login/google?state=st', '/oauth/login/email')

    def test_start_page_offers_both_methods_in_one_card(self):
        html = onboarding().sign_in_step(PURCHASE, 'sid')
        self.assert_one_card_with_both(html, '/start/google?session_id=sid', '/start/email')
        self.assertIn('name="session_id" value="sid"', cards(html, 'login')[0])

    def test_start_page_without_email_login_shows_google_only(self):
        [card] = cards(onboarding(email=False).sign_in_step(PURCHASE, 'sid'), 'login')
        self.assertIn('Googleでログイン', card)
        self.assertNotIn('または', card)
        self.assertNotIn('<form', card)


class SiteSwitchTest(unittest.TestCase):
    def test_wordpress_and_other_site_are_alternatives_in_one_card(self):
        html = onboarding().site_step(PURCHASE, VISIT, None, 'sid', None)
        [card] = cards(html, 'site-pick')
        self.assertIn('id="kind-wp" checked', card)
        self.assertIn('action="/start/wordpress"', card)
        self.assertIn('action="/start/site"', card)
        self.assertIn('<label for="kind-other">その他のホームページ</label>', card)

    def test_url_errors_reopen_the_other_site_form(self):
        for notice in ('invalid_url', 'invalid_auth_code'):
            html = onboarding().site_step(PURCHASE, VISIT, None, 'sid', notice)
            self.assertIn('id="kind-other" checked', html)
            self.assertNotIn('id="kind-wp" checked', html)

    def test_without_wordpress_only_the_site_form_remains(self):
        [card] = cards(onboarding(wordpress=False).site_step(PURCHASE, VISIT, None, 'sid', None), 'site-pick')
        self.assertNotIn('kind-wp', card)
        self.assertNotIn('/start/wordpress', card)
        self.assertIn('action="/start/site"', card)


if __name__ == '__main__':
    unittest.main()
