import unittest

from import_normalization import normalize, SourceConnectionRequired


class ImportNormalizationTest(unittest.TestCase):
    def convert(self, sources):
        records = [{'url': url, 'path': 'site/' + str(i), 'content_type': mime}
                   for i, (url, mime, body) in enumerate(sources)]
        files = {str(i): body for i, (url, mime, body) in enumerate(sources)}
        return normalize(records, files, 'clinic.example.jp')

    def test_query_assets_keep_valid_suffix_and_html_css_references_match(self):
        output = self.convert([
            ('https://clinic.example.jp/', 'text/html', b'<link href="/style.css?v=2"><img src="/image.png?v=1">'),
            ('https://clinic.example.jp/style.css?v=2', 'text/css', b'body{background:url("/image.png?v=1")}'),
            ('https://clinic.example.jp/image.png?v=1', 'image/png', b'image')])
        css = next(p for p in output if p.endswith('.css'))
        image = next(p for p in output if p.endswith('.png'))
        self.assertIn(('/' + css).encode(), output['index.html'])
        self.assertIn(('/' + image).encode(), output['index.html'])
        self.assertIn(('/' + image).encode(), output[css])

    def test_legacy_japanese_text_is_converted_with_correct_meta_charset(self):
        output = self.convert([('https://clinic.example.jp/home.php', 'text/html; charset=Shift_JIS',
            '<meta charset="Shift_JIS"><h1>医院のご案内</h1>'.encode('shift_jis'))])
        text = output['index.html'].decode('utf-8')
        self.assertIn('charset="utf-8"', text)
        self.assertIn('医院のご案内', text)

    def test_internal_forms_and_module_apps_require_a_real_source_connection(self):
        for html in (b'<form method="POST" action="/send.php"></form>', b'<script type="module" src="/app.js"></script>'):
            with self.subTest(html=html), self.assertRaises(SourceConnectionRequired):
                self.convert([('https://clinic.example.jp/', 'text/html', html)])

    def test_existing_external_booking_and_phone_links_are_preserved(self):
        body = b'<a href="https://booking.example.test/clinic">Book</a><a href="tel:0312345678">Call</a>'
        output = self.convert([('https://clinic.example.jp/', 'text/html', body)])
        self.assertIn(b'https://booking.example.test/clinic', output['index.html'])
        self.assertIn(b'tel:0312345678', output['index.html'])


if __name__ == '__main__': unittest.main()
