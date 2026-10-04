#!/usr/bin/env python3
"""Validate every HTML page's index policy, metadata and crawlable navigation.

Uses only Python's standard library so the same audit runs locally and in CI.
The inventory is intentional: a new page must declare its index policy.
"""
import json
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
BASE = 'https://simy.one'

class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.title = ''
        self.in_title = False
        self.ld = None
        self.schemas = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == 'title':
            self.in_title = True
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.ld = ''

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.ld is not None:
            self.ld += data

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        if tag == 'script' and self.ld is not None:
            self.schemas.append(json.loads(self.ld))
            self.ld = None

    def attrs(self, tag, **match):
        return [a for t, a in self.tags if t == tag and all(a.get(k) == v for k, v in match.items())]

    def meta(self, name, attr='name'):
        return [a.get('content', '') for a in self.attrs('meta', **{attr: name})]

    @property
    def canonical(self):
        return [a.get('href') for a in self.attrs('link', rel='canonical')]

    @property
    def alternates(self):
        return {a['hreflang']: a['href'] for a in self.attrs('link', rel='alternate') if 'hreflang' in a}


def canonical_url(name):
    if name.startswith('for/') and name.endswith('/index.html'):
        return BASE + '/' + name[:-len('index.html')]
    return BASE + ('/' if name == 'index.html' else '/' + name)


def main():
    inventory = json.loads((ROOT / 'docs/seo/sitewide-page-inventory.json').read_text())
    files = {str(p.relative_to(SITE)): p for p in SITE.rglob('*.html')}
    errors = []
    def check(ok, message):
        if not ok:
            errors.append(message)
    check(set(files) == set(inventory), f'Inventory mismatch: {set(files) ^ set(inventory)}')
    pages = {}
    for name, path in files.items():
        try:
            pages[name] = Page(path.read_text())
        except (ValueError, KeyError) as exc:
            errors.append(f'{name}: invalid structured data: {exc}')
    public = {name for name, data in inventory.items() if data['policy'] == 'index'}
    titles = Counter(pages[n].title for n in public if n in pages)
    descriptions = Counter(d for n in public if n in pages for d in pages[n].meta('description'))
    for name, page in pages.items():
        if name not in inventory:
            continue
        robots = ','.join(page.meta('robots')).lower()
        if name not in public:
            check('noindex' in robots, f'{name}: non-public page needs noindex')
            continue
        check('noindex' not in robots, f'{name}: indexable page has noindex')
        check(page.canonical == [canonical_url(name)], f'{name}: incorrect self canonical {page.canonical}')
        check(bool(page.title.strip()) and len(page.attrs('title')) == 1, f'{name}: missing/duplicate title')
        check(titles[page.title] == 1, f'{name}: duplicate title')
        desc = page.meta('description')
        check(len(desc) == 1 and bool(desc[0].strip()), f'{name}: missing/duplicate description')
        check(not desc or descriptions[desc[0]] == 1, f'{name}: duplicate description')
        check(len(page.attrs('h1')) == 1, f'{name}: expected one raw HTML h1')
        check(bool(page.schemas), f'{name}: missing structured data')
        # Social cards intentionally use shorter copy than search snippets.
        for key, attr in [('og:title','property'), ('twitter:title','name'),
                          ('og:description','property'), ('twitter:description','name')]:
            values = page.meta(key, attr)
            check(len(values) == 1 and bool(values[0].strip()), f'{name}: missing/duplicate {key}')
        check(page.meta('og:url', 'property') == page.canonical, f'{name}: og:url mismatch')
        lang = page.attrs('html')[0].get('lang')
        check(lang == inventory[name]['language'], f'{name}: inventory language mismatch')
        alts = page.alternates
        if name.startswith(('guides/', 'download/')) or name in ['index.html','ja.html','hi.html','fr.html','es.html','zh-Hans.html','download.html']:
            check(set(alts) == {'en','ja','hi','es','fr','zh-Hans','x-default'}, f'{name}: incomplete alternates')
        if alts:
            check(alts.get(lang) == canonical_url(name), f'{name}: missing self alternate')
        for code, href in alts.items():
            target_name = urlsplit(href).path.lstrip('/') or 'index.html'
            if target_name.endswith('/'):
                target_name += 'index.html'
            target = pages.get(target_name)
            check(target_name in public, f'{name}: alternate not indexable: {href}')
            if target:
                check(target.alternates == alts, f'{name}: non-reciprocal alternates: {href}')
                if code != 'x-default':
                    check(target.attrs('html')[0].get('lang') == code, f'{name}: alternate language mismatch')
        for tag, attrs in page.tags:
            if tag != 'a' or not attrs.get('href'):
                continue
            href = attrs['href']
            url = urlsplit(urljoin(canonical_url(name), href))
            if url.scheme not in ('http','https') or url.netloc not in ('simy.one','www.simy.one'):
                continue
            path = unquote(url.path).lstrip('/') or 'index.html'
            if path.startswith('downloads/'):
                continue  # Installers are published by a separate release workflow.
            target_file = SITE / path
            if target_file.is_dir():
                path = path.rstrip('/') + '/index.html'
                target_file = SITE / path
            check(target_file.exists(), f'{name}: broken internal URL {href}')
            target = pages.get(path)
            if target and url.fragment:
                ids = {a['id'] for _, a in target.tags if 'id' in a}
                check(unquote(url.fragment) in ids, f'{name}: missing fragment {href}')
    sitemap = ET.parse(SITE / 'sitemap.xml')
    urls = [e.text for e in sitemap.findall('.//{*}loc')]
    expected = {canonical_url(n) for n in public}
    check(len(urls) == len(set(urls)), 'Duplicate sitemap URLs')
    check(set(urls) == expected, f'Sitemap mismatch: {set(urls) ^ expected}')
    robots = (SITE / 'robots.txt').read_text()
    check('Disallow: /old/' not in robots and 'Disallow: /compare/' not in robots,
          'Archived HTML must be crawlable for noindex to be discovered')
    if errors:
        print('\n'.join(errors))
        print(f'FAIL: {len(errors)} issues across {len(files)} HTML files')
        return 1
    print(f'PASS: {len(files)} HTML pages; {len(public)} indexable URLs; {len(files)-len(public)} noindex pages; metadata, reciprocal hreflang, sitemap and internal links valid')
    return 0

if __name__ == '__main__':
    sys.exit(main())
