"""Build/check one immutable source-derived locale-navigation release snapshot."""
import argparse
import hashlib
import json
import os
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from hp_industry_release import LEGACY_HTML_DIRECTORIES, source_path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_RELATIVE = 'docs/seo/locale-navigation-release.json'
MARKER = '<!-- SIMY locale navigation -->'
SUPPORT = ('site-header.js', 'i18n.js', 'hp-management/law-firm/release-manifest.json')
# These Japanese-only service pages keep their own header/runtime and receive
# only the reviewed static logo-link correction. No law package alias is owned.
EXPLICIT_PAGES = ('hp-management/clinic/index.html', 'hp-management/law-firm.html')
INDEX_ALIASES = {
    'hp-management/index.html': ('hp-management/', 'hp-management.html', 'hp-management'),
    'hp-management/clinic/index.html': ('hp-management/clinic/', 'hp-management/clinic.html'),
}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def plan(root=ROOT):
    site = root / 'site'
    pages = []
    for path in sorted(site.rglob('*.html')):
        relative = path.relative_to(site).as_posix()
        text = source_path(site, relative).read_text(encoding='utf-8')
        if MARKER in text or relative in EXPLICIT_PAGES:
            pages.append((relative, text))
    if not any(MARKER in text for _, text in pages):
        raise ValueError('No locale navigation sources; generate pages first')
    if not set(EXPLICIT_PAGES) <= {relative for relative, _ in pages}:
        raise ValueError('Missing explicit clinic/law locale release source')
    objects = []
    keys = set()

    def add(relative, key, phase):
        if not key or key.startswith('/') or any(c in key for c in '*?\\') or key in keys:
            raise ValueError('Unsafe or duplicate locale publication key: ' + key)
        keys.add(key)
        body = source_path(site, relative).read_bytes()
        objects.append({'source': relative, 'key': key, 'phase': phase,
                        'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()})

    for relative in SUPPORT:
        add(relative, relative, 'support')
    for relative, _ in pages:
        add(relative, relative, 'page')
        if relative in INDEX_ALIASES:
            for key in INDEX_ALIASES[relative]:
                add(relative, key, 'page')
        elif relative.endswith('/index.html'):
            directory = relative[:-len('index.html')]
            add(relative, directory, 'page')
            if directory in LEGACY_HTML_DIRECTORIES:
                add(relative, directory.rstrip('/') + '.html', 'page')
    paths = {'/' + key for key in keys}

    class Canonical(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag != 'link' or attrs.get('rel') != 'canonical':
                return
            url = urlsplit(attrs.get('href', ''))
            if (url.scheme, url.netloc) != ('https', 'simy.one'):
                return
            if not url.path.startswith('/') or any(c in url.path for c in '*?\\') or url.query or url.fragment:
                raise ValueError('Unsafe canonical invalidation path')
            paths.add(url.path)
    for relative, text in pages:
        Canonical().feed(text)
        if relative == 'index.html':
            paths.add('/')
    return {'version': 1, 'purpose': 'locale-navigation', 'objects': objects,
            'invalidation_paths': sorted(paths)}


def check(root=ROOT, expected=None):
    body = (root / MANIFEST_RELATIVE).read_bytes()
    digest = hashlib.sha256(body).hexdigest()
    if expected is not None and (not re.fullmatch('[a-f0-9]{64}', expected) or digest != expected):
        raise ValueError('Unexpected reviewed locale release digest')
    if body != encoded(plan(root)):
        raise ValueError('Locale release differs from source-derived plan; rebuild and review')
    return json.loads(body), digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--build', action='store_true')
    modes.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.build:
        path = ROOT / MANIFEST_RELATIVE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded(plan()))
    data, digest = check(expected=os.environ.get('EXPECTED_RELEASE_SHA256'))
    print(json.dumps({'status': 'passed', 'objects': len(data['objects']),
                      'source_files': len({o['source'] for o in data['objects']}),
                      'manifest_sha256': digest}))


if __name__ == '__main__':
    main()
