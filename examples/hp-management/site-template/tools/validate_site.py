#!/usr/bin/env python3
"""Validate inert static source. Never load dependencies or run supplied scripts."""
from __future__ import annotations

import argparse
import os
import re
import stat
import subprocess
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

MAX_FILES = 1000
MAX_FILE = 10 * 1024 * 1024
MAX_TOTAL = 50 * 1024 * 1024
SUFFIXES = {'.html', '.css', '.js', '.json', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.ico', '.txt', '.xml', '.woff', '.woff2', '.ttf', '.pdf', '.webmanifest'}
DENIED = {'node_modules', 'package.json', 'package-lock.json', 'pnpm-lock.yaml', 'yarn.lock', 'credentials.json', 'service-account.json', 'config.json', 'tsconfig.json', 'jsconfig.json', 'vercel.json', 'server.js', 'build.js', 'deploy.js', 'gulpfile.js', 'gruntfile.js', 'version.json'}


class ValidationError(ValueError):
    pass


def safe_path(path):
    if not path or len(path) > 1024 or any(c in path for c in '\\:\0') or unicodedata.normalize('NFC', path) != path or any(ord(c) < 32 or ord(c) == 127 for c in path):
        raise ValidationError('unsafe static path: ' + repr(path))
    parts = path.split('/')
    if any(not p or p in ('.', '..') or (p.startswith('.') and p != '.well-known') or p.casefold() in DENIED for p in parts):
        raise ValidationError('forbidden static path: ' + path)
    leaf = parts[-1].casefold()
    if Path(leaf).suffix not in SUFFIXES or '.config.' in leaf or leaf.startswith(('credentials.', 'service-account.', 'service_account.')):
        raise ValidationError('unsupported static file: ' + path)


def read_source(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValidationError('site must be an ordinary directory')
    files, folded, total = {}, {}, 0
    for directory, directories, names in os.walk(root, followlinks=False):
        for name in directories + names:
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            canonical = relative.casefold()
            if canonical in folded and folded[canonical] != relative:
                raise ValidationError('case-folding path collision: ' + relative)
            folded[canonical] = relative
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise ValidationError('special source entry: ' + relative)
            safe_path(relative + '/placeholder.txt' if stat.S_ISDIR(mode) else relative)
            if stat.S_ISREG(mode):
                if path.stat().st_size > MAX_FILE:
                    raise ValidationError('static file exceeds 10 MiB: ' + relative)
                data = path.read_bytes()
                if len(data) > MAX_FILE:
                    raise ValidationError('static file grew beyond limit')
                files[relative] = data
                total += len(data)
                if len(files) > MAX_FILES or total > MAX_TOTAL:
                    raise ValidationError('site exceeds file count or 50 MiB limit')
    if 'index.html' not in files:
        raise ValidationError('site/index.html is required')
    return files


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = self.doctype = self.charset = self.viewport = self.description = False
        self.title = ''
        self.in_title = False
        self.references, self.ids, self.inline_scripts = [], set(), []
        self.in_script = None
        self.script_text = ''

    def handle_decl(self, declaration):
        self.doctype = declaration.lower() == 'doctype html'

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get('id'):
            if attrs['id'] in self.ids:
                raise ValidationError('duplicate HTML id: ' + attrs['id'])
            self.ids.add(attrs['id'])
        if tag == 'html':
            self.lang = bool(attrs.get('lang', '').strip())
        if tag == 'title':
            self.in_title = True
        if tag == 'base':
            raise ValidationError('base href is unsupported; use root-relative links')
        if tag == 'meta':
            self.charset |= attrs.get('charset', '').lower().replace('-', '') == 'utf8'
            if attrs.get('name', '').lower() == 'viewport':
                self.viewport = 'width=device-width' in attrs.get('content', '').replace(' ', '')
            if attrs.get('name', '').lower() == 'description':
                self.description = bool(attrs.get('content', '').strip())
        for attribute in ('href', 'src', 'poster', 'action'):
            if attrs.get(attribute):
                self.references.append(attrs[attribute])
        # Data URLs contain commas; they are self-contained and need no disk lookup.
        if attrs.get('srcset') and not attrs['srcset'].lstrip().startswith('data:'):
            self.references.extend(part.strip().split()[0] for part in attrs['srcset'].split(',') if part.strip())
        if tag == 'script' and not attrs.get('src'):
            script_type = attrs.get('type', '').strip().lower()
            if script_type in ('', 'text/javascript', 'application/javascript', 'module'):
                self.in_script = 'module' if script_type == 'module' else 'commonjs'
                self.script_text = ''
        if attrs.get('style'):
            self.references.extend(css_references(attrs['style']))
        if tag == 'style':
            self.in_style = True

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        if tag == 'script' and self.in_script:
            self.inline_scripts.append((self.in_script, self.script_text))
            self.in_script = None
        if tag == 'style':
            self.in_style = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.in_script:
            self.script_text += data
        if getattr(self, 'in_style', False):
            self.references.extend(css_references(data))


def css_references(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    urls = [match[1] for match in re.findall(r'url\(\s*([\'"]?)(.*?)\1\s*\)', text, flags=re.I)]
    urls += re.findall(r'@import\s+[\'"]([^\'"]+)[\'"]', text, flags=re.I)
    return urls


def target_path(source, reference, files):
    if any(ord(c) < 32 for c in reference):
        raise ValidationError('control character in URL')
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme.lower() not in ('', 'https', 'http', 'mailto', 'tel', 'data'):
            raise ValidationError('unsupported URL scheme: ' + reference)
        return None
    path = unquote(parsed.path, errors='strict')
    if '\\' in path or '\0' in path:
        raise ValidationError('unsafe internal URL: ' + reference)
    parts = [] if path.startswith('/') else source.split('/')[:-1]
    for part in path.split('/'):
        if part in ('', '.'):
            continue
        if part == '..':
            if not parts:
                raise ValidationError('internal URL leaves site: ' + reference)
            parts.pop()
        else:
            parts.append(part)
    target = '/'.join(parts) if path else source
    if target not in files:
        target = (target.rstrip('/') + '/index.html').lstrip('/')
    if target not in files:
        raise ValidationError(source + ': missing internal target: ' + reference)
    return target, unquote(parsed.fragment)


def check_javascript(text, mode, label, node='node'):
    environment = {key: value for key, value in os.environ.items() if key not in ('NODE_OPTIONS', 'NODE_PATH')}
    try:
        result = subprocess.run([node, '--check', '--input-type=' + mode], input=text, text=True, capture_output=True, env=environment, check=False)
    except OSError as error:
        raise ValidationError('Node syntax check unavailable for ' + label) from error
    if result.returncode:
        raise ValidationError(label + ': JavaScript syntax check failed: ' + result.stderr[:1000])


def validate(root, node='node'):
    files = read_source(root)
    pages = {}
    references = []
    for path, data in sorted(files.items()):
        suffix = Path(path).suffix.lower()
        if suffix in ('.html', '.css', '.js', '.json', '.webmanifest', '.svg', '.xml', '.txt'):
            try:
                text = data.decode('utf-8')
            except UnicodeError as error:
                raise ValidationError(path + ': text must be UTF-8') from error
        if suffix == '.html':
            page = Page()
            try:
                page.feed(text)
                page.close()
            except Exception as error:
                raise ValidationError(path + ': invalid HTML: ' + str(error)) from error
            if not all((page.lang, page.doctype, page.charset, page.title.strip())):
                raise ValidationError(path + ': requires HTML doctype, lang, UTF-8 charset and title')
            # The existing public fallback is intentionally a minimal noindex
            # document; SEO and responsive-page metadata do not gate that file.
            if path != 'error.html' and not all((page.viewport, page.description)):
                raise ValidationError(path + ': requires viewport and description')
            pages[path] = page
            references.extend((path, ref) for ref in page.references)
            for index, (mode, script) in enumerate(page.inline_scripts):
                check_javascript(script, mode, path + ':inline-script-' + str(index), node)
        elif suffix == '.css':
            references.extend((path, ref) for ref in css_references(text))
        elif suffix == '.js':
            # Modules are valid in both standalone scripts and type=module usage;
            # syntax checking does not import, resolve, or execute anything.
            check_javascript(text, 'module', path, node)
        elif suffix in ('.json', '.webmanifest'):
            import json
            try:
                json.loads(text)
            except ValueError as error:
                raise ValidationError(path + ': invalid JSON') from error
    for source, reference in references:
        target = target_path(source, reference, files)
        if target and target[1] and target[0] in pages and target[1] not in pages[target[0]].ids:
            raise ValidationError(source + ': missing HTML anchor: ' + reference)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('site', nargs='?', default='site')
    args = parser.parse_args()
    try:
        files = validate(args.site)
    except (ValidationError, UnicodeError, ValueError) as error:
        parser.exit(1, str(error) + '\n')
    print('Validated ' + str(len(files)) + ' static files; no customer code executed.')


if __name__ == '__main__':
    main()
