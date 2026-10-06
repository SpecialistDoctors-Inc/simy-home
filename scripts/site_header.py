#!/usr/bin/env python3
"""Apply the shared static header after generating site pages. Safe to rerun."""
from pathlib import Path
from html.parser import HTMLParser
import html
import re

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
LOCALES = {"en": "English", "ja": "日本語", "hi": "हिन्दी", "es": "Español", "fr": "Français", "zh-Hans": "简体中文"}

def home(locale):
    return "/" if locale == "en" else f"/{locale}.html"

def header(locale, source, path):
    base = home(locale)
    suffix = "" if locale == "ja" else f"{locale.lower()}/"
    groups = {
        "Product": [("Overview", base + "#product"), ("How it works", base + "#how-it-works"), ("Apps & integrations", "/integrations.html"), ("Download", "/download.html" if locale == "ja" else f"/download/{locale.lower()}.html")],
        "Solutions": [("For your work", ("/for/" if locale == "ja" else "/for/en/")), ("For engineers", ("/for/engineers/" if locale == "ja" else f"/for/{locale.lower()}/engineers/")), ("Use cases", base + "#use-cases")],
        "Resources": [("Guides", f"/guides/{suffix}index.html"), ("Compare", "/compare.html"), ("News", "/press-release.html"), ("About SIMY", "/about.html"), ("Security", "/security.html"), ("Contact", "/contact.html"), ("Legal & service information", "/legal.html"), ("Seller information", "/seller-info.html")],
    }
    def link(label, href):
        if href.endswith(".html") and href in ["/integrations.html", "/compare.html", "/press-release.html", "/about.html", "/security.html", "/contact.html"]:
            href += "?lang=" + locale
        return f'<a href="{html.escape(href, quote=True)}">{label}</a>'
    menus = "".join(f'<details class="sh-dropdown"><summary>{name}<span aria-hidden="true">⌄</span></summary><div class="sh-panel">' + "".join(link(label, href) for label, href in items) + '</div></details>' for name, items in groups.items())
    # Prefer an existing translated counterpart; otherwise use the localized home.
    alternatives = dict(re.findall(r'<link[^>]*hreflang="([^" ]+)"[^>]*href="https://simy.one([^" ]*)"', source))
    if re.search(r'<script[^>]+src="(?:\.\./|/)?i18n\.js', source):
        page_url = "/" + str(path.relative_to(SITE))
        alternatives = {code: page_url + "?lang=" + code for code in LOCALES}
    options = "".join(f'<a href="{html.escape(alternatives.get(code, home(code)), quote=True)}" lang="{code}" hreflang="{code}" data-locale-option="{code}"' + (' aria-current="page"' if code == locale else '') + f'>{label}</a>' for code, label in LOCALES.items())
    region = {"en": "us", "ja": "jp", "hi": "in", "es": "es", "fr": "fr"}.get(locale)
    params = f"lang={locale}&amp;locale={locale}" + (f"&amp;region={region}" if region else "")
    code = "ZH" if locale == "zh-Hans" else locale.upper()
    return f'''<header class="simy-header" translate="no" data-simy-no-translate>
  <div class="sh-frame">
    <a class="sh-brand" href="{base}" aria-label="SIMY home">SIMY</a>
    <div class="sh-navigation" role="navigation" aria-label="Primary navigation">{menus}<a class="sh-pricing" href="{base}#pricing">Pricing</a></div>
    <div class="sh-account"><details class="sh-dropdown sh-language"><summary aria-label="Language: {LOCALES[locale]}"><span aria-hidden="true">🌐</span> {code}</summary><div class="sh-panel">{options}</div></details><a data-existing-account-login href="https://app.simy.one/">Log in</a><a data-new-account-signup class="sh-signup" href="https://app.simy.one/signup?{params}">Sign up</a></div>
    <div class="sh-stores" role="group" aria-label="Mobile apps">
      <a class="sh-store" href="https://apps.apple.com/app/id6745385262"><img src="/assets/store-badges/app-store.svg" width="120" height="40" alt="Download on the App Store"></a>
      <a class="sh-store sh-google-play" href="{("/download.html" if locale == "ja" else f"/download/{locale.lower()}.html")}#android" aria-label="Android availability"><img src="/assets/store-badges/google-play.png" width="155" height="60" alt="Google Play"><small>Android availability</small></a>
    </div>
  </div>
</header>'''

class HeaderParser(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.source = source
        self.lines = [0]
        for m in re.finditer("\n", source): self.lines.append(m.end())
        self.start = self.end = None
        self.tag = None
        self.depth = 0
        self.in_body = False
        self.stopped = False
    def position(self):
        line, col = self.getpos()
        return self.lines[line - 1] + col
    def handle_starttag(self, tag, attrs):
        if tag == "body": self.in_body = True
        if tag == "main" and self.start is None: self.stopped = True
        if not self.in_body or self.stopped or self.end is not None: return
        if self.start is None and tag in ("header", "nav"):
            self.start, self.tag = self.position(), tag
        if self.start is not None and tag == self.tag: self.depth += 1
    def handle_endtag(self, tag):
        if self.start is not None and self.end is None and tag == self.tag:
            self.depth -= 1
            if self.depth == 0: self.end = self.source.index(">", self.position()) + 1

def apply(source, path):
    if re.search(r'http-equiv=["\']refresh', source, re.I) or "<body" not in source.lower(): return source
    locale_match = re.search(r'<html[^>]*lang="([^" ]+)"', source)
    locale = locale_match.group(1) if locale_match else "en"
    if locale not in LOCALES: locale = "en"
    parser = HeaderParser(source)
    parser.feed(source)
    markup = header(locale, source, path)
    if parser.end is not None: source = source[:parser.start] + markup + source[parser.end:]
    else: source = re.sub(r'(<body[^>]*>)', lambda m: m[1] + markup, source, count=1)
    source = re.sub(r'[ \t]*<nav class="legal-mobile-toolbar".*?</nav>', '', source, flags=re.S)
    if '/site-header.css?' not in source:
        source = source.replace('</head>', '<link rel="stylesheet" href="/site-header.css?v=20261005-2">\n<script src="/site-header.js?v=20261006-locales-1" defer></script>\n</head>')
    source = source.replace("/site-header.css?v=20261005-1", "/site-header.css?v=20261005-2").replace("/site-header.js?v=20261005-1", "/site-header.js?v=20261006-locales-1")
    source = source.replace("/site-header.js?v=20261005-2", "/site-header.js?v=20261006-locales-1")
    return source

if __name__ == "__main__":
    count = 0
    for path in SITE.rglob("*.html"):
        if "old" in path.relative_to(SITE).parts or path.name == "old.html": continue
        source = path.read_text()
        output = apply(source, path)
        if source != output:
            path.write_text(output)
            count += 1
    print(f"Updated {count} pages")
