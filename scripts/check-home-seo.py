#!/usr/bin/env python3
"""Check raw HTML (without executing JS), language navigation and local resources."""
import importlib.util
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True

spec = importlib.util.spec_from_file_location('localized_home', Path(__file__).with_name('build-localized-home.py'))
home = importlib.util.module_from_spec(spec)
spec.loader.exec_module(home)

class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.headings = []
        self.ids = []
        self.title = ''
        self.json_ld = ''
        self.in_title = False
        self.in_ld = False
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs))
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'h1':
            self.headings.append(attrs)
        if tag == 'title':
            self.in_title = True
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.in_ld = True

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.in_ld:
            self.json_ld += data

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        if tag == 'script':
            self.in_ld = False

    def attrs(self, tag, **match):
        return [a for t, a in self.elements if t == tag and all(a.get(k) == v for k, v in match.items())]

for locale in home.LOCALES:
    filename = 'index.html' if locale == 'en' else locale + '.html'
    source = (home.SITE / filename).read_text()
    page = Page(source)
    expected_url = home.BASE + home.home_path(locale)
    assert page.attrs('html', lang=locale), filename
    assert page.title == home.CONTENT['meta'][locale]['title'], filename
    assert len(page.headings) == 1, filename
    assert len(page.ids) == len(set(page.ids)), f'Duplicate IDs: {filename}'
    assert page.attrs('link', rel='canonical') == [{'rel':'canonical','href':expected_url}], filename
    assert page.attrs('meta', property='og:url')[0]['content'] == expected_url, filename
    desc = page.attrs('meta', name='description')[0]['content']
    assert desc == home.CONTENT['meta'][locale]['description'], filename
    assert 'noindex' not in page.attrs('meta', name='robots')[0]['content'], filename
    schema = json.loads(page.json_ld)
    assert schema['url'] == expected_url and schema['description'] == desc, filename
    alternates = {a['hreflang']:a['href'] for a in page.attrs('link', rel='alternate')}
    assert alternates == {**{lang:home.BASE+home.home_path(lang) for lang in home.LOCALES},'x-default':home.BASE+'/'}, filename
    options = {a['data-locale-option']:a for _,a in page.elements if 'data-locale-option' in a}
    assert set(options) == set(home.LOCALES), filename
    for lang,a in options.items():
        assert a['href'] == home.home_path(lang), filename
        assert ('aria-current' in a) == (lang == locale), filename
    # Search crawlers must reach the matching language without a JS rewrite.
    code = {'en':'en', 'hi':'hi', 'es':'es', 'fr':'fr', 'zh-Hans':'zh-hans'}.get(locale)
    guide_prefix = f'/guides/{code}/' if code else '/guides/'
    download_path = f'/download/{code}.html' if code else '/download.html'
    guide_links = [a['href'] for a in page.attrs('a') if a.get('href', '').startswith('/guides/')]
    download_links = [a['href'] for a in page.attrs('a') if a.get('href', '').startswith('/download')]
    assert guide_links and all(h.startswith(guide_prefix) and '/' not in h[len(guide_prefix):] for h in guide_links), filename
    assert download_links and all(h.split("#", 1)[0] == download_path for h in download_links), filename
    # Real localized answers must exist in raw HTML, not just in a JS dictionary.
    for key in ['AI workflow automation, explained','How does SIMY use AI agents to automate workflows?',
                'What happens after a meeting or customer conversation?','How do I stay in control of automated work?']:
        expected = home.CONTENT['copy'][locale].get(key, key)
        assert expected in source, (filename, expected)
    for tag,attrs in page.elements:
        for attr in ('src','href'):
            url = urlsplit(attrs.get(attr, ''))
            if url.scheme or url.netloc or not attrs.get(attr):
                continue
            if url.path:
                target = home.SITE / unquote(url.path).lstrip('/')
                if url.path == '/':
                    target = home.SITE / 'index.html'
                assert target.exists(), f'{filename}: missing {attrs[attr]}'
            elif url.fragment:
                assert url.fragment in page.ids, f'{filename}: missing anchor {url.fragment}'
ns = {'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
urls = [e.text for e in ET.parse(home.SITE/'sitemap.xml').findall('s:url/s:loc', ns)]
assert len(urls) == len(set(urls)), 'Duplicate sitemap entries'
for locale in home.LOCALES:
    assert home.BASE + home.home_path(locale) in urls
for url in urls:
    target = home.SITE / (urlsplit(url).path.lstrip('/') or 'index.html')
    assert target.exists(), url
print('SEO checks passed: 6 raw-HTML locales, metadata, hreflang, schema, FAQ, navigation, local assets and sitemap.')
