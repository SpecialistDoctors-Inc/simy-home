"""Put current monthly totals before the existing homepage plan comparison."""
import re
from html import escape
from urllib.parse import urlencode
from service_pricing_2026_11 import COPY, SIMPLE
from pricing_2026_11_data import money


def apply(source, locale, monthly_prices):
    c, s = COPY[locale], SIMPLE[locale]
    cards = []
    for code, name, description in [('starter', 'Starter', 'starter'), ('quality', 'SIMY by Industry', 'quality')]:
        params = {'plan': code, 'interval': 'monthly', 'lang': locale, 'locale': locale}
        region = {'ja': 'jp', 'en': 'us', 'es': 'es', 'fr': 'fr', 'hi': 'in'}.get(locale)
        if region:
            params['region'] = region
        cards.append(f'''<article class="current-price-card" data-current-monthly="{code}">
<h3>{name}</h3><p>{escape(s[description])}</p>
<p class="current-price-total"><strong>{money(monthly_prices[code], 'usd')}</strong> <span>{escape(s['period'])}</span></p>
<p>{escape(c['beforeTax'])} · USD</p>
<a href="https://app.simy.one/signup/?{escape(urlencode(params), quote=True)}">{escape(s['choose'])} ↗</a></article>''')

    def replace(match):
        content = match[2]
        start = content.index('<div class="pricing-billing-bar">')
        summary = (f'<div class="current-price-heading">{escape(s["current"])}</div>'
                   f'<div class="current-price-grid">{"".join(cards)}</div>'
                   f'<p>{escape(s["ai"])}</p>')
        details = f'<details class="current-price-details"><summary>{escape(s["currentDetails"])}</summary>{content[start:]}</details>'
        intro = re.sub(r'<p class="pricing-billing-disclosure">[\s\S]*?</p>', '', content[:start], count=1)
        return match[1] + intro + summary + details + match[3]

    return re.sub(r'(<section\b[^>]*\bid="pricing"[^>]*>)([\s\S]*?)(</section>)', replace, source, count=1)
