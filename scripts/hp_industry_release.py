"""Deterministic, source-derived scope for the shared HP industry release."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
from html.parser import HTMLParser
from urllib.parse import urlsplit
from hp_management_industries import HUB_URL, HUB_SOURCE

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'docs/seo/hp-industry-navigation-release.json'
HUB = HUB_SOURCE
URL = 'https://simy.one' + HUB_URL
LEGACY_URL = 'https://simy.one/hp-management/'
ASSETS = ('hp-industry-navigation.css', 'hp-management-industries.css',
          'assets/social/cards/hp-management-industries-v1.png',
          'hp-management/law-firm/release-manifest.json')
HUB_KEYS = (HUB, 'hp-management/', 'hp-management.html', 'hp-management')
# Existing occupation aliases plus the verified live guides/ -> guides.html
# edge redirect. Only
# folder-index sources own these keys; canonical metadata never assigns writes.
LEGACY_HTML_DIRECTORIES = {'for/clinic/', 'for/pharmaceutical-companies/', 'guides/'} | {
    f'for/{locale}/{industry}/'
    for locale in ('en', 'es', 'fr', 'hi', 'zh-hans')
    for industry in ('pharmaceutical-companies', 'engineers', 'financial-planners')
    if locale != 'en' or industry == 'pharmaceutical-companies'
}



def source_path(site, relative):
    if (not isinstance(relative, str) or not relative or '\\' in relative
            or PurePosixPath(relative).is_absolute()
            or any(part in ('', '.', '..') for part in relative.split('/'))):
        raise ValueError('Unsafe source path: ' + str(relative))
    path = site / relative
    if not path.resolve().is_relative_to(site.resolve()) or not path.is_file():
        raise ValueError('Missing or escaping site source: ' + relative)
    return path


def plan(root=ROOT):
    site = root / 'site'
    menu_pages = []
    for path in sorted(site.rglob('*.html')):
        relative = path.relative_to(site).as_posix()
        checked = source_path(site, relative)
        if re.search(r'class=[\"\'][^\"\']*\bsh-solutions-panel\b', checked.read_text()):
            menu_pages.append(relative)
    if HUB not in menu_pages:
        raise ValueError('Generated hub must include the shared industry navigation')
    objects = []
    keys = set()

    def add(source, key, phase):
        if key in keys:
            raise ValueError('Duplicate object key: ' + key)
        keys.add(key)
        blob = source_path(site, source).read_bytes()
        objects.append({'source': source, 'key': key, 'phase': phase,
                        'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()})

    for source in ASSETS:
        add(source, source, 'support')
    for key in HUB_KEYS:
        add(HUB, key, 'hub')
    for source in menu_pages:
        if source != HUB:
            add(source, source, 'menu')
            if source.endswith('/index.html'):
                directory = source[:-len('index.html')]
                add(source, directory, 'menu')
                if directory in LEGACY_HTML_DIRECTORIES:
                    add(source, directory.rstrip('/') + '.html', 'menu')
    invalidation_paths = {'/' + key for key in keys}
    class Canonical(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'link' and attrs.get('rel') == 'canonical':
                url = urlsplit(attrs.get('href', ''))
                if (url.scheme, url.netloc) == ('https', 'simy.one'):
                    if not url.path.startswith('/') or any(c in url.path for c in '*?\\') or url.query or url.fragment:
                        raise ValueError('Unsafe canonical invalidation path')
                    invalidation_paths.add(url.path)
    for source in menu_pages:
        Canonical().feed(source_path(site, source).read_text())
        if source == 'index.html':
            invalidation_paths.add('/')
        elif source.endswith('/index.html'):
            invalidation_paths.add('/' + source[:-len('index.html')])
    return {'version': 1, 'url': URL, 'invalidation_paths': sorted(invalidation_paths), 'sitemap': {'key': 'sitemap.xml', 'mode': 'live-hub-canonical-only', 'url': URL},
            'objects': objects}


def encoded(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def check(root=ROOT, expected=None):
    path = root / MANIFEST.relative_to(ROOT)
    blob = path.read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    if expected is not None and (not re.fullmatch('[a-f0-9]{64}', expected) or digest != expected):
        raise ValueError('Unexpected reviewed industry release digest')
    # Equality with canonical bytes rejects injected keys, reordered uploads, extra
    # fields, stale hashes and unreviewed source changes before contacting AWS.
    if blob != encoded(plan(root)):
        raise ValueError('Industry release manifest differs from source-derived plan; rebuild and review')
    return json.loads(blob), digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--build', action='store_true', help='Write deterministic review manifest')
    modes.add_argument('--check', action='store_true', help='Check the reviewed manifest (default)')
    args = parser.parse_args()
    if args.build:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_bytes(encoded(plan()))
    data, digest = check(expected=os.environ.get('EXPECTED_RELEASE_SHA256'))
    print(json.dumps({'status': 'passed', 'objects': len(data['objects']),
                      'source_files': len({o['source'] for o in data['objects']}),
                      'manifest_sha256': digest}))


if __name__ == '__main__':
    main()
