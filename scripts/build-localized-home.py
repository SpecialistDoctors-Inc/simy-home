#!/usr/bin/env python3
"""Generate crawlable homepages using the existing copy. Python 3 + Node, no packages.

Run with --check in CI to reject stale artifacts. Edit index.html and its locale
sources, never the generated locale HTML files.
"""
import argparse
import json
import re
import subprocess
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
CONTENT = json.loads(subprocess.check_output(['node', str(ROOT / 'scripts/home-content.cjs')], text=True))
LOCALES = ['en', 'ja', 'hi', 'es', 'fr', 'zh-Hans']
LABELS = {'en': ('English', 'EN'), 'ja': ('日本語', 'JA'), 'hi': ('हिन्दी', 'HI'), 'es': ('Español', 'ES'), 'fr': ('Français', 'FR'), 'zh-Hans': ('简体中文', 'ZH')}
REGIONS = {'en': 'us', 'ja': 'jp', 'hi': 'in', 'es': 'es', 'fr': 'fr'}
BASE = 'https://simy.one'

def home_path(locale):
    return '/' if locale == 'en' else f'/{locale}.html'

class Localize(HTMLParser):
    def __init__(self, locale):
        super().__init__(convert_charrefs=True)
        self.locale = locale
        self.copy = CONTENT['copy'][locale]
        self.meta = CONTENT['meta'][locale]
        self.output = []
        self.stack = []
        self.raw_tag = None
        self.json_ld = False
        self.raw = ''

    def translate(self, value):
        core = value.strip()
        return value.replace(core, self.copy.get(core, core), 1) if core else value

    def handle_decl(self, decl):
        self.output.append(f'<!{decl}>')

    def handle_comment(self, data):
        self.output.append(f'<!--{data}-->')

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html':
            a.update(lang=self.locale, **{'data-rendered-locale': self.locale})
        if tag == 'link' and a.get('rel') == 'canonical':
            a['href'] = BASE + home_path(self.locale)
        if tag == 'meta':
            key = a.get('name', a.get('property'))
            values = {'description': self.meta['description'], 'og:url': BASE + home_path(self.locale),
                      'og:locale': self.meta['ogLocale'], 'og:title': self.meta['socialTitle'],
                      'og:description': self.meta['socialDescription'], 'og:image:alt': self.meta['imageAlt'],
                      'twitter:title': self.meta['socialTitle'], 'twitter:description': self.meta['socialDescription'],
                      'twitter:image:alt': self.meta['imageAlt']}
            if key in values:
                a['content'] = values[key]
        for attr in ('aria-label', 'title', 'placeholder', 'alt'):
            if a.get(attr):
                a[attr] = self.translate(a[attr])
        if 'data-language-trigger' in a:
            a['aria-label'] = self.translate('Language') + ': ' + LABELS[self.locale][0]
        if 'data-locale-option' in a:
            if a['data-locale-option'] == self.locale:
                a['aria-current'] = 'true'
            else:
                a.pop('aria-current', None)
        if tag == 'a' and 'href' in a:
            original = a['href']
            url = urlsplit(original)
            if url.netloc == 'app.simy.one' or url.path in ('privacy.html', 'terms.html', '/privacy.html', '/terms.html'):
                params = dict(parse_qsl(url.query))
                params['lang'] = self.locale
                if url.netloc == 'app.simy.one':
                    params['locale'] = self.locale
                    if self.locale in REGIONS:
                        params['region'] = REGIONS[self.locale]
                    else:
                        params.pop('region', None)
                a['href'] = urlunsplit(url._replace(query=urlencode(params)))
            # Match runtime guide/download navigation in the raw crawlable HTML.
            if not url.scheme and not url.netloc:
                code = {'en': 'en', 'hi': 'hi', 'es': 'es', 'fr': 'fr', 'zh-Hans': 'zh-hans'}.get(self.locale)
                guide = re.fullmatch(r'/guides/(?:en/)?([a-z-]+\.html)', url.path)
                if guide:
                    target = f'/guides/{code}/{guide[1]}' if code else f'/guides/{guide[1]}'
                    a['href'] = urlunsplit(url._replace(path=target))
                elif url.path in ('/for/', '/for/en/'):
                    target = '/for/' if self.locale == 'ja' else '/for/en/'
                    a['href'] = urlunsplit(url._replace(path=target))
                elif url.path in ('/for/engineers/', '/for/en/engineers/'):
                    target = '/for/engineers/' if self.locale == 'ja' else '/for/en/engineers/'
                    a['href'] = urlunsplit(url._replace(path=target))
                elif url.path in ('/download.html', '/download/en.html'):
                    target = f'/download/{code}.html' if code else '/download.html'
                    a['href'] = urlunsplit(url._replace(path=target))
            # Runtime localizes email subjects from the original English value.
            if original.startswith('mailto:'):
                a['data-original-href'] = original
        self.output.append('<' + tag + ''.join(' ' + k + ('' if v is None else '="' + escape(v, quote=True) + '"') for k, v in a.items()) + '>')
        if tag in ('script', 'style'):
            self.raw_tag = tag
            self.json_ld = a.get('type') == 'application/ld+json'
            self.raw = ''
        if tag not in ('meta', 'link', 'img', 'br', 'hr', 'input', 'source', 'wbr', 'area', 'base', 'embed', 'param', 'track', 'col'):
            self.stack.append((tag, a))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.stack and self.stack[-1][0] == tag:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self.raw_tag:
            self.raw += data
            return
        tag, attrs = self.stack[-1] if self.stack else ('', {})
        if tag == 'title':
            data = self.meta['title']
        elif 'data-locale-current' in attrs:
            data = LABELS[self.locale][0]
        elif 'data-locale-current-code' in attrs:
            data = LABELS[self.locale][1]
        elif not any('data-locale-option' in a for _, a in self.stack):
            data = self.translate(data)
        self.output.append(escape(data, quote=False))

    def handle_endtag(self, tag):
        if self.raw_tag == tag:
            if self.json_ld:
                payload = json.loads(self.raw)
                payload.update(description=self.meta['description'], url=BASE + home_path(self.locale), inLanguage=self.locale)
                self.raw = '\n' + json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
            self.output.append(self.raw)
            self.raw_tag = None
            self.json_ld = False
        self.output.append(f'</{tag}>')
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()


def generate():
    source = (SITE / 'index.html').read_text()
    outputs = {}
    for locale in LOCALES[1:]:
        parser = Localize(locale)
        parser.feed(source)
        outputs[SITE / f'{locale}.html'] = '<!-- Generated by scripts/build-localized-home.py; edit homepage sources. -->\n' + ''.join(parser.output)
    # Keep existing indexed subpages and their historical modification dates.
    namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    ET.register_namespace('', namespace)
    tree = ET.parse(SITE / 'sitemap.xml')
    urlset = tree.getroot()
    home_urls = {BASE + home_path(locale) for locale in LOCALES}
    for entry in list(urlset):
        if entry.findtext(f'{{{namespace}}}loc') in home_urls:
            urlset.remove(entry)
    for index, locale in enumerate(LOCALES):
        entry = ET.Element(f'{{{namespace}}}url')
        ET.SubElement(entry, f'{{{namespace}}}loc').text = BASE + home_path(locale)
        # Omit lastmod instead of publishing an invented date on every build.
        urlset.insert(index, entry)
    ET.indent(tree, space='  ')
    outputs[SITE / 'sitemap.xml'] = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(urlset, encoding='unicode') + '\n'
    return outputs

if __name__ == '__main__':
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--check', action='store_true')
    check = args.parse_args().check
    stale = []
    for target, content in generate().items():
        if check:
            if not target.exists() or target.read_text() != content:
                stale.append(str(target.relative_to(ROOT)))
        else:
            target.write_text(content)
    if stale:
        raise SystemExit('Stale localized pages; run python3 scripts/build-localized-home.py: ' + ', '.join(stale))
    print('Localized homepages and sitemap verified.' if check else 'Generated 5 localized homepages and sitemap.')
