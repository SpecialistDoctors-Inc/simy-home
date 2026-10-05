#!/usr/bin/env python3
"""Normalize cross-language plumbing on every guide and download page.

For each page that exists in site/guides (Japanese source) and its translations:
- hreflang alternates for every language that has the page, plus x-default (English)
- the header language switcher pointing at the same page in each language
- one footer link list per language
- sitemap entries for every page

Run from the repository root: python3 scripts/finalize-guides.py
"""
import os
from shared_header import apply as shared_header
import re
import json

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")
LANGS = [("ja", "ja", "日本語"), ("en", "en", "English"), ("zh-hans", "zh-Hans", "中文"),
         ("es", "es", "Español"), ("fr", "fr", "Français"), ("hi", "hi", "हिन्दी")]
HOME_LANG = {"ja": "ja", "en": "en", "zh-hans": "zh-Hans", "es": "es", "fr": "fr", "hi": "hi"}

LABELS = {
    "ja": ["ホーム", "料金", "連携", "ダウンロード", "ガイド一覧", "AI議事録", "中国のAI比較", "Qwenを自社サーバーで", "セキュリティ", "プライバシーポリシー", "利用規約"],
    "en": ["Home", "Pricing", "Integrations", "Download", "All guides", "AI meeting notes", "Chinese AI compared", "Qwen on your own server", "Security", "Privacy Policy", "Terms of Use"],
    "zh-hans": ["首页", "价格", "集成", "下载", "全部指南", "AI 会议纪要", "中国 AI 对比", "在自有服务器上运行 Qwen", "安全", "隐私政策", "使用条款"],
    "es": ["Inicio", "Precios", "Integraciones", "Descargar", "Todas las guías", "Actas con IA", "IA china comparada", "Qwen en tu propio servidor", "Seguridad", "Política de privacidad", "Términos de uso"],
    "fr": ["Accueil", "Tarifs", "Intégrations", "Télécharger", "Tous les guides", "Comptes rendus IA", "IA chinoises comparées", "Qwen sur votre serveur", "Sécurité", "Politique de confidentialité", "Conditions d’utilisation"],
    "hi": ["होम", "मूल्य", "इंटीग्रेशन", "डाउनलोड", "सभी गाइड", "AI मीटिंग नोट्स", "चीनी AI की तुलना", "अपने सर्वर पर Qwen", "सुरक्षा", "गोपनीयता नीति", "उपयोग की शर्तें"],
}


def page_path(name, code):
    if name == "download":
        return "/download.html" if code == "ja" else f"/download/{code}.html"
    return f"/guides/{name}.html" if code == "ja" else f"/guides/{code}/{name}.html"


def exists(name, code):
    return os.path.exists(os.path.join(ROOT, page_path(name, code).lstrip("/")))


def footer(code, current):
    L = LABELS[code]
    hl = HOME_LANG[code]
    home = "/" if code == "en" else f"/{hl}.html"
    q = "" if code == "ja" else f"?lang={hl}"
    g = lambda n: page_path(n, code)
    items = [
        (home, L[0]), (f"{home}#pricing", L[1]), ("/integrations.html", L[2]), (g("download"), L[3]), (g("index"), L[4]),
        (g("claude"), "Claude"), (g("codex"), "Codex"), (g("cowork"), "Cowork"), (g("chatgpt"), "ChatGPT"), (g("plaud"), "PLAUD"), (g("notta"), "Notta"),
        (g("meeting-notes"), L[5]), (g("china-llm"), L[6]), (g("deepseek"), "DeepSeek"), (g("qwen"), "Qwen"), (g("qwen-local"), L[7]),
        ("/security.html", L[8]), (f"/privacy.html{q}", L[9]), (f"/terms.html{q}", L[10]),
    ]
    items = [(h, t) for h, t in items if not h.startswith(("/guides", "/download")) or os.path.exists(os.path.join(ROOT, h.lstrip("/")))]
    lis = "\n".join(f'      <li><a href="{h}"' + (' aria-current="page"' if h == current else "") + f">{t}</a></li>" for h, t in items)
    return '<ul class="footer-links">\n' + lis + "\n    </ul>"


def main():
    # New workflow guides own their complete HTML in build-content-pages.py.
    manifest = json.load(open(os.path.join(ROOT, '..', 'scripts', 'content-pages.json'), encoding='utf-8'))
    generated = {p['id'] for p in manifest['pages'] if p['kind'] == 'guide'}
    names = sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, "guides")) if f.endswith(".html")) + ["download"]
    touched = 0
    sitemap_urls = []
    for name in names:
        if name in generated:
            continue
        available = [(c, h, l) for c, h, l in LANGS if exists(name, c)]
        for code, hl, label in available:
            f = os.path.join(ROOT, page_path(name, code).lstrip("/"))
            s = open(f, encoding="utf-8").read()
            # hreflang
            s = re.sub(r'\n<link rel="alternate" hreflang="[^"]+" href="[^"]+">', "", s)
            alts = "".join(f'\n<link rel="alternate" hreflang="{h}" href="https://simy.one{page_path(name, c)}">' for c, h, _ in available)
            xdef = "en" if any(c == "en" for c, _, _ in available) else "ja"
            alts += f'\n<link rel="alternate" hreflang="x-default" href="https://simy.one{page_path(name, xdef)}">'
            s = re.sub(r'(<link rel="canonical" href="[^"]+">)', lambda m: m.group(1) + alts, s, count=1)
            # language switcher
            m = re.search(r'<details class="lang-switch">[\s\S]*?</details>', s)
            if m:
                items = "".join(
                    f'<li><a href="{page_path(name, c) if exists(name, c) else page_path("index", c)}" hreflang="{h}" lang="{h}"'
                    + (' aria-current="page"' if c == code else "") + f">{l}</a></li>"
                    for c, h, l in LANGS)
                sw = f'<details class="lang-switch"><summary aria-label="Language: {label}"><span aria-hidden="true">🌐</span> <span class="ls-label">{label}</span></summary><ul>{items}</ul></details>'
                s = s[:m.start()] + sw + s[m.end():]
            # compact language button on phones so the header stays on one line
            if ".lang-switch .ls-label" not in s:
                s = s.replace("</style>", "@media (max-width: 640px) { .lang-switch .ls-label { display: none; } .lang-switch > summary { padding: 0 10px; } }\n</style>", 1)
            # footer
            m = re.search(r'<ul class="footer-links">[\s\S]*?</ul>', s)
            if m:
                s = s[:m.start()] + footer(code, page_path(name, code)) + s[m.end():]
            open(f, "w", encoding="utf-8").write(shared_header(s, page_path(name, code).lstrip("/")))
            touched += 1
            sitemap_urls.append("https://simy.one" + page_path(name, code))
    # sitemap
    sp = os.path.join(ROOT, "sitemap.xml")
    sm = open(sp, encoding="utf-8").read()
    add = "".join(
        f"  <url>\n    <loc>{u}</loc>\n    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>\n"
        for u in sitemap_urls if f"<loc>{u}</loc>" not in sm)
    sm = sm.replace("</urlset>", add + "</urlset>")
    open(sp, "w", encoding="utf-8").write(sm)
    print(f"pages updated: {touched}, sitemap urls added: {add.count('<loc>')}")


if __name__ == "__main__":
    main()
