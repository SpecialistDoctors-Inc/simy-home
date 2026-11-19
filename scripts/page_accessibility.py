"""Preserve page layouts while providing keyboard access to public page content."""
from html.parser import HTMLParser
import hashlib
import html
import re

SKIP_LABELS = {
    'en': 'Skip to content', 'ja': '本文へ移動', 'es': 'Saltar al contenido',
    'fr': 'Aller au contenu', 'hi': 'मुख्य सामग्री पर जाएँ', 'zh-Hans': '跳到正文',
}
# This legacy application creates its main landmark in the client bundle. Do not
# wrap its root in another main; its runtime landmark is audited separately.
LEGACY_APPLICATIONS = {'old/contact.html'}


def classification(source, relative_path):
    if relative_path == 'auth-callback.html':
        return 'authentication-return'
    if relative_path.startswith('google-site-verification-'):
        return 'verification'
    if re.search(r'http-equiv=["\']refresh', source, re.I):
        return 'redirect'
    if not re.search(r'<body\b', source, re.I):
        return 'non-document'
    if relative_path in LEGACY_APPLICATIONS:
        return 'legacy-application'
    return 'public-document'


class Elements(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.lines = [0] + [m.end() for m in re.finditer('\n', source)]
        self.tags = []

    def handle_starttag(self, tag, attrs):
        line, col = self.getpos()
        start = self.lines[line - 1] + col
        self.tags.append((tag, dict(attrs), start, start + len(self.get_starttag_text())))


def apply(source, path, site):
    if classification(source, path.relative_to(site).as_posix()) != 'public-document':
        return source
    parser = Elements(source)
    parser.feed(source)
    mains = [t for t in parser.tags if t[0] == 'main' or t[1].get('role') == 'main']
    if len(mains) > 1:
        raise ValueError(f'{path}: multiple main landmarks require an explicit repair')
    if not mains:
        header = re.search(r'<header\b[^>]*class="simy-header"[\s\S]*?</header>', source)
        if not header:
            raise ValueError(f'{path}: missing main without a known page boundary')
        footer = next((t for t in parser.tags if t[0] == 'footer' and t[2] > header.end()), None)
        end = footer[2] if footer else source.lower().rfind('</body>')
        source = (source[:header.end()] + '\n<main id="simy-main" tabindex="-1">'
                  + source[header.end():end].rstrip() + '\n</main>\n' + source[end:])
        return apply(source, path, site)
    skips = [t for t in parser.tags if t[0] == 'a' and any('skip' in c for c in t[1].get('class', '').split())]
    main = mains[0]
    attrs = main[1]
    main_id = attrs.get('id')
    additions = ''
    if not main_id:
        ids = {t[1].get('id') for t in parser.tags}
        existing_target = next((t[1].get('href', '')[1:] for t in skips if t[1].get('href', '').startswith('#') and t[1]['href'][1:] not in ids), None)
        main_id = existing_target or 'simy-main'
        while main_id in ids:
            main_id += '-content'
        additions += f' id="{main_id}"'
    if 'tabindex' not in attrs:
        additions += ' tabindex="-1"'
    if additions:
        source = source[:main[3] - 1] + additions + source[main[3] - 1:]
    # Keep existing links and their text, classes and destinations intact.
    skips = [t for t in parser.tags if t[0] == 'a' and any('skip' in c for c in t[1].get('class', '').split())]
    if not skips:
        locale = re.search(r'<html[^>]*lang="([^" ]+)"', source)
        label = SKIP_LABELS.get(locale[1] if locale else 'en', SKIP_LABELS['en'])
        link = f'\n<a class="simy-skip-link" href="#{html.escape(main_id, quote=True)}">{label}</a>'
        source = re.sub(r'(<body\b[^>]*>)', lambda m: m[1] + link, source, count=1)
    version = hashlib.sha256((site / 'page-accessibility.css').read_bytes()).hexdigest()[:12]
    css_url = '/hp-management/law-firm/page-accessibility.css' if path.relative_to(site).as_posix() == 'hp-management/law-firm.html' else '/page-accessibility.css'
    asset = f'<link rel="stylesheet" href="{css_url}?v={version}">'
    source = re.sub(r'<link\b[^>]*href="/(?:hp-management/law-firm/)?page-accessibility\.css[^" ]*"[^>]*>\n?', '', source)
    source = re.sub(r'[ \t]+\n(?=</main>)', '\n', source)
    return source.replace('</head>', asset + '\n</head>', 1)
