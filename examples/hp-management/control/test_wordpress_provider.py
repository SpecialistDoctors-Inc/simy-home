import unittest
from copy import deepcopy
from urllib.parse import parse_qs, urlsplit

from wordpress_provider import WordPressConnectionError, WordPressProvider, content_digest


class WordPressProviderTest(unittest.TestCase):
    def setUp(self):
        self.replies = {
            '/oauth2/token': {'access_token': 'fake-wordpress-token', 'token_type': 'bearer', 'blog_id': '123'},
            '/rest/v1.1/sites/123?fields=ID,URL,is_private': {
                'ID': 123, 'URL': 'https://clinic.wordpress.com', 'is_private': False,
            },
            '/wp/v2/sites/123/users/me?context=edit': {
                'capabilities': {'edit_pages': True, 'publish_pages': True},
            },
            '/wp/v2/sites/123/settings': {'show_on_front': 'page', 'page_on_front': 456},
            '/wp/v2/sites/123/pages/456?context=edit': {
                'id': 456, 'status': 'publish', 'link': 'https://clinic.wordpress.com/',
                'content': {'raw': '<h1>Clinic</h1>'},
            },
        }
        self.calls = []
        self.provider = WordPressProvider('app-id', 'secret', 'https://simy.example/return', self.request)

    def request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        page = '/wp/v2/sites/123/pages/456'
        if method == 'POST' and path == page + '/autosaves?context=edit':
            revision = {'id': 789, 'parent': 456, 'content': {'raw': kwargs['payload']['content']}}
            self.replies[page + '/autosaves/789?context=edit'] = revision
            return deepcopy(revision)
        if method == 'POST' and path == page:
            current = self.replies[page + '?context=edit']
            current['content']['raw'] = kwargs['payload']['content']
            return deepcopy(current)
        return deepcopy(self.replies[path])

    def test_oauth_is_for_only_the_requested_site(self):
        url = urlsplit(self.provider.authorization_url('https://clinic.wordpress.com/about', 'x' * 43))
        self.assertEqual((url.scheme, url.hostname, url.path), ('https', 'public-api.wordpress.com', '/oauth2/authorize'))
        self.assertEqual(parse_qs(url.query), {
            'client_id': ['app-id'], 'redirect_uri': ['https://simy.example/return'],
            'response_type': ['code'], 'blog': ['clinic.wordpress.com'], 'state': ['x' * 43],
        })
        self.assertEqual(self.calls, [])

    def test_connect_resolves_provider_owned_site_and_static_homepage(self):
        connection = self.provider.connect('authorization-code', 'clinic.wordpress.com')
        self.assertEqual((connection.site_id, connection.page_id, connection.origin),
                         (123, 456, 'https://clinic.wordpress.com'))
        self.assertEqual(connection.content, '<h1>Clinic</h1>')
        self.assertNotIn(connection.access_token, repr(connection))
        self.assertEqual(self.calls[0][0:2], ('POST', '/oauth2/token'))
        self.assertTrue(all(method == 'GET' and kwargs == {'token': connection.access_token}
                            for method, _, kwargs in self.calls[1:]))

    def test_refuses_mismatched_or_overbroad_grant_before_reading_homepage(self):
        self.replies['/oauth2/token']['scope'] = 'global'
        with self.assertRaisesRegex(WordPressConnectionError, 'wordpress_site_grant_required'):
            self.provider.connect('code', 'clinic.wordpress.com')
        self.assertEqual(len(self.calls), 1)
        del self.replies['/oauth2/token']['scope']
        with self.assertRaisesRegex(WordPressConnectionError, 'wordpress_wrong_site'):
            self.provider.connect('code', 'different.wordpress.com')
        self.assertEqual(len(self.calls), 3)

    def test_refuses_read_only_or_non_static_site(self):
        caps = self.replies['/wp/v2/sites/123/users/me?context=edit']['capabilities']
        caps['publish_pages'] = False
        with self.assertRaisesRegex(WordPressConnectionError, 'wordpress_publish_permission_required'):
            self.provider.connect('code', 'clinic.wordpress.com')
        self.assertEqual(len(self.calls), 3)
        caps['publish_pages'] = True
        self.replies['/wp/v2/sites/123/settings']['show_on_front'] = 'posts'
        with self.assertRaisesRegex(WordPressConnectionError, 'wordpress_static_homepage_required'):
            self.provider.connect('code', 'clinic.wordpress.com')

    def test_publishes_only_the_saved_and_approved_revision_and_verifies_readback(self):
        page = '/wp/v2/sites/123/pages/456'
        connection = self.provider.connect('code', 'clinic.wordpress.com')
        changed = '<h1>New clinic hours</h1>'
        draft = self.provider.save_draft(connection, changed)
        self.assertEqual(self.replies[page + '?context=edit']['content']['raw'], connection.content)
        with self.assertRaisesRegex(WordPressConnectionError, 'wordpress_approval_mismatch'):
            self.provider.publish_approved_draft(connection, draft, content_digest('wrong approval'))
        self.provider.publish_approved_draft(connection, draft, draft.content_sha256)
        self.provider.publish_approved_draft(connection, draft, draft.content_sha256)
        self.assertEqual(self.replies[page + '?context=edit']['content']['raw'], changed)
        self.assertEqual(sum((method, path) == ('POST', page) for method, path, _ in self.calls), 1)

    def test_rejects_a_changed_homepage_or_autosave_without_publishing(self):
        page = '/wp/v2/sites/123/pages/456'
        connection = self.provider.connect('code', 'clinic.wordpress.com')
        draft = self.provider.save_draft(connection, '<h1>Prepared</h1>')
        self.replies[page + '?context=edit']['content']['raw'] = 'Other editor changed this page'
        with self.assertRaisesRegex(WordPressConnectionError, 'wordpress_homepage_changed'):
            self.provider.publish_approved_draft(connection, draft, draft.content_sha256)
        self.replies[page + '/autosaves/789?context=edit']['content']['raw'] = 'Autosave was replaced'
        with self.assertRaisesRegex(WordPressConnectionError, 'wordpress_draft_changed'):
            self.provider.publish_approved_draft(connection, draft, draft.content_sha256)
        self.assertFalse(any((method, path) == ('POST', page) for method, path, _ in self.calls))
