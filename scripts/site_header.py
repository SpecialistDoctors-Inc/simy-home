#!/usr/bin/env python3
"""Apply the shared static header after generating site pages. Safe to rerun."""
from pathlib import Path
from html.parser import HTMLParser
import html
import re
import argparse

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
LOCALES = {"en": "English", "ja": "日本語", "hi": "हिन्दी", "es": "Español", "fr": "Français", "zh-Hans": "简体中文"}

JA_LABELS = {
    "Product": "プロダクト", "Solutions": "職業別", "Resources": "ガイド・情報",
    "Overview": "できること", "How it works": "仕組み", "Apps & integrations": "連携アプリ",
    "Download": "ダウンロード", "For your work": "職業から探す", "For engineers": "エンジニア",
    "For financial planners": "ファイナンシャルプランナー", "For sales": "営業", "Use cases": "活用例",
    "Guides": "ガイド", "Compare": "他サービスとの比較", "News": "お知らせ", "About SIMY": "SIMYについて",
    "Security": "セキュリティ", "Contact": "お問い合わせ", "Legal & service information": "規約・サービス情報",
    "Seller information": "特定商取引法に基づく表記", "Pricing": "料金", "Log in": "ログイン", "Sign up": "新規登録",
    "Android availability": "Android版の提供状況", "Navigation menu": "メニュー", "Primary navigation": "メインナビゲーション",
    "Download on the App Store": "App Storeでダウンロード",
    "Mobile apps": "モバイルアプリ", "SIMY home": "SIMYホーム", "Language": "言語",
}

def home(locale):
    return "/" if locale == "en" else f"/{locale}.html"

def header(locale, source, path):
    base = home(locale)
    suffix = "" if locale == "ja" else f"{locale.lower()}/"
    sales_visible = None if locale in ("ja", "en") else "For sales (English)"
    groups = {
        "Product": [("Overview", base + "#product"), ("How it works", base + "#how-it-works"), ("Apps & integrations", "/integrations.html"), ("Download", "/download.html" if locale == "ja" else f"/download/{locale.lower()}.html")],
        "Solutions": [("For your work", ("/for/" if locale == "ja" else "/for/en/")), ("For engineers", ("/for/engineers/" if locale == "ja" else f"/for/{locale.lower()}/engineers/")), ("For financial planners", ("/for/financial-planners/" if locale == "ja" else f"/for/{locale.lower()}/financial-planners/")), ("For sales", "/for/sales/" if locale == "ja" else "/for/en/sales/", sales_visible), ("Use cases", base + "#use-cases")],
        "Resources": [("Guides", f"/guides/{suffix}index.html"), ("Compare", "/compare.html"), ("News", "/press-release.html"), ("About SIMY", "/about.html"), ("Security", "/security.html"), ("Contact", "/contact.html"), ("Legal & service information", "/legal.html"), ("Seller information", "/seller-info.html")],
    }
    def label(text, visible_override=None):
        japanese = JA_LABELS.get(text, text)
        visible = visible_override if visible_override is not None else japanese if locale == "ja" else text
        return f'<span data-header-label data-label-en="{html.escape(text, quote=True)}" data-label-ja="{html.escape(japanese, quote=True).encode("ascii", "xmlcharrefreplace").decode("ascii")}">{html.escape(visible)}</span>'
    def accessible(text):
        japanese = JA_LABELS.get(text, text)
        visible = japanese if locale == "ja" else text
        return f'aria-label="{visible}" data-aria-en="{text}" data-aria-ja="{html.escape(japanese, quote=True).encode("ascii", "xmlcharrefreplace").decode("ascii")}"'
    def link(text, href, visible_override=None):
        if href.endswith(".html") and href in ["/integrations.html", "/compare.html", "/press-release.html", "/about.html", "/security.html", "/contact.html"]:
            href += "?lang=" + locale
        return f'<a href="{html.escape(href, quote=True)}">{label(text, visible_override)}</a>'
    download = "/download.html" if locale == "ja" else f"/download/{locale.lower()}.html"
    stores = f'''<div class="sh-stores" role="group" {accessible("Mobile apps")}>
      <a class="sh-store" href="https://apps.apple.com/app/id6745385262" {accessible("Download on the App Store")}><img src="/assets/store-badges/app-store.svg" width="120" height="40" alt=""></a>
      <a class="sh-store sh-google-play" href="{download}#android" {accessible("Android availability")}><img src="/assets/store-badges/google-play.png" width="155" height="60" alt="Google Play"><small>{label("Android availability")}</small></a>
    </div>'''
    menus = "".join(f'<details class="sh-dropdown"><summary>{label(name)}<span aria-hidden="true">⌄</span></summary><div class="sh-panel">' + "".join(link(*item) for item in items) + (stores if name == "Product" else "") + '</div></details>' for name, items in groups.items())
    # Prefer an existing translated counterpart; otherwise use the localized home.
    alternatives = dict(re.findall(r'<link[^>]*hreflang="([^" ]+)"[^>]*href="https://simy.one([^" ]*)"', source))
    if re.search(r'<script[^>]+src="(?:/|(?:\.\./)*)i18n\.js', source):
        page_url = "/" + str(path.relative_to(SITE))
        alternatives = {code: page_url + "?lang=" + code for code in LOCALES}
    options = "".join(f'<a href="{html.escape(alternatives.get(code, home(code)), quote=True)}" lang="{code}" hreflang="{code}" data-locale-option="{code}"' + (' aria-current="page"' if code == locale else '') + f'>{language_name}</a>' for code, language_name in LOCALES.items())
    region = {"en": "us", "ja": "jp", "hi": "in", "es": "es", "fr": "fr"}.get(locale)
    params = f"lang={locale}&amp;locale={locale}" + (f"&amp;region={region}" if region else "")
    code = "ZH" if locale == "zh-Hans" else locale.upper()
    return f'''<header class="simy-header" translate="no" data-simy-no-translate>
  <div class="sh-frame">
    <a class="sh-brand" href="{base}" {accessible("SIMY home")}><img src="/simy-icon-56.png" width="32" height="32" alt=""><span>SIMY</span></a>
    <details class="sh-menu"><summary class="sh-menu-toggle" {accessible("Navigation menu")}><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg></summary><div class="sh-menu-panel"><div class="sh-navigation" role="navigation" {accessible("Primary navigation")}>{menus}<a class="sh-pricing" href="{base}#pricing">{label("Pricing")}</a></div><a class="sh-login" data-existing-account-login href="https://app.simy.one/">{label("Log in")}</a></div></details>
    <div class="sh-account"><details class="sh-dropdown sh-language"><summary aria-label="{JA_LABELS["Language"] if locale == "ja" else "Language"}: {LOCALES[locale]}"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/></svg> {code}</summary><div class="sh-panel">{options}</div></details><a data-new-account-signup class="sh-signup" href="https://app.simy.one/signup?{params}">{label("Sign up")}</a></div>
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

def needs_header(source, path):
    # The authentication return page has a focused, security-sensitive purpose.
    # Redirect aliases and verification tokens never render site navigation.
    return (path.name != "auth-callback.html"
            and not re.search(r'http-equiv=["\']refresh', source, re.I)
            and "<body" in source.lower())


def apply(source, path):
    if not needs_header(source, path): return source
    locale_match = re.search(r'<html[^>]*lang="([^" ]+)"', source)
    locale = locale_match.group(1) if locale_match else "en"
    if locale not in LOCALES: locale = "en"
    parser = HeaderParser(source)
    parser.feed(source)
    markup = header(locale, source, path)
    if parser.end is not None: source = source[:parser.start] + markup + source[parser.end:]
    else: source = re.sub(r'(<body[^>]*>)', lambda m: m[1] + markup, source, count=1)
    source = re.sub(r'[ \t]*<nav class="legal-mobile-toolbar".*?</nav>', '', source, flags=re.S)
    assets = '<link rel="stylesheet" href="/site-header.css?v=20261006-ja-labels-1">\n<script src="/site-header.js?v=20261006-ja-labels-1" defer></script>\n'
    if '/site-header.css?' not in source:
        source = source.replace('</head>', assets + '</head>')
    source = re.sub(r'(/site-header\.(?:css|js)\?v=)[^"\s]+', r'\g<1>20261006-ja-labels-1', source)
    return source

if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--check", action="store_true", help="Fail when a rendered page differs from the shared header")
    args = cli.parse_args()
    changed = []
    for path in sorted(SITE.rglob("*.html")):
        source = path.read_text()
        output = apply(source, path)
        if source != output:
            changed.append(str(path.relative_to(SITE)))
            if not args.check:
                path.write_text(output)
    if args.check and changed:
        raise SystemExit("Shared header differs: " + ", ".join(changed))
    print(f"{'Checked' if args.check else 'Updated'} shared headers; {len(changed)} pages {'differ' if args.check else 'updated'}")
