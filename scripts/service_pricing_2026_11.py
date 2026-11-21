"""Service-specific advance prices from the same public specification as the homepage notice.

The route registry is explicit. It neither enables checkout nor changes a current CTA.
"""
import hashlib
import json
import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from pricing_2026_11_data import parse_prices, money

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
MAP = json.loads((ROOT/'scripts/service-pricing-2026-11-map.json').read_text())
COPY = json.loads((ROOT/'scripts/service-pricing-2026-11-copy.json').read_text())
ROWS = parse_prices(ROOT/MAP['source'])
ROUTES = {r['path']: r for r in MAP['routes']}
START = '<!-- service-pricing-2026-11:start -->'
END = '<!-- service-pricing-2026-11:end -->'
NOTICE_START = '<!-- service-pricing-2026-11:notice -->'
NOTICE_END = '<!-- /service-pricing-2026-11:notice -->'

def e(value): return escape(str(value), quote=True)

def unit(code, c):
    if code in ['base','hearing_8h','hearing_20h','fp_quality','sqm_check']: return c['perPerson']
    if code == 'land_valuation': return c['perContract']
    if code in ['homepage','homepage_secure','homepage_ops']: return c['perSite']
    if code in ['hearing_bot','hearing_overage','transcription_overage','homepage_ops_overage']: return c['hour']
    if code == 'land_valuation_overage': return c['case']
    if code == 'homepage_transfer_overage': return c['gb']
    if code in ['homepage_request_overage','homepage_secure_request_overage']: return c['million']
    if code == 'transcription_20h': return c['pack']
    raise ValueError('Unmapped public billing unit: '+code)

def included(code, c):
    if code == 'base': return c['baseIncluded']
    if code in ['hearing_8h','hearing_20h']: return c['hearingIncluded'].format(hours=8 if code=='hearing_8h' else 20)
    if code == 'sqm_check': return 'Delivery Loop · SQM · '+c['unlimited']
    return c[{'fp_quality':'unlimited','land_valuation':'landIncluded','homepage':'hpIncluded','homepage_secure':'secureIncluded','homepage_ops':'opsIncluded'}[code]]

def price_cell(code, currency, annual, c):
    row=ROWS[code]
    if annual:
        total=row.get(currency+'_annual')
        if total is None:return e(c['noAnnual'])
        return f'<strong class="sp26-number">{money(total,currency)}</strong><small>{e(c["yearBill"])}</small><small>{money(total//12,currency)} · {e(c["monthEquivalent"])}</small>'
    return f'<strong class="sp26-number">{money(row[currency],currency)}</strong>'

def price_table(codes, c, heading_id, usage=False):
    currencies = ['JPY', 'USD']
    if usage:
        currencies = [f"{currency} · {c['beforeTax']}" for currency in currencies]
    labels = [c['service'], c['unit'], *currencies]
    if not usage:
        labels.append(c['included'])
    rows = []
    for code in codes:
        amounts = []
        for currency, label in zip(['jpy', 'usd'], currencies):
            value = price_cell(code, currency, False, c)
            if not usage:
                annual = price_cell(code, currency, True, c)
                value = (
                    f'<span class="rate-period">{e(c["monthly"])}</span>{value}'
                    f'<div class="rate-annual"><span class="rate-period">{e(c["annual"])}</span>{annual}</div>'
                )
            amounts.append(
                f'<td class="rate-currency" role="cell">'
                f'<span class="rate-mobile-label" aria-hidden="true">{e(label)}</span>{value}</td>'
            )
        name = e(c['names'][code])
        if code == 'land_valuation':
            name += '<small>路線価評価</small>'
        if code == 'transcription_20h':
            name += '<small>' + e(c['packIncluded']) + '</small>'
        if code == 'hearing_bot':
            name += '<small>' + e(c['botIncluded']) + '</small>'
        scope = '' if usage else f'<td role="cell">{e(included(code, c))}</td>'
        rows.append(
            f'<tr role="row" data-sku="{code}"><th scope="row" role="rowheader">{name}</th>'
            f'<td role="cell">{e(unit(code, c))}</td>{"".join(amounts)}{scope}</tr>'
        )
    heading = ''.join(f'<th scope="col" role="columnheader">{e(label)}</th>' for label in labels)
    table_class = 'sp26-table sp26-usage' if usage else 'sp26-table'
    return (
        f'<div class="pricing-rate-table"><table class="{table_class}" role="table" '
        f'aria-labelledby="{heading_id}" aria-describedby="{heading_id}-caption">'
        f'<caption id="{heading_id}-caption">{e(c["usage"] if usage else c["beforeTax"])}</caption>'
        f'<thead role="rowgroup"><tr role="row">{heading}</tr></thead>'
        f'<tbody role="rowgroup">{"".join(rows)}</tbody></table></div>'
    )

def examples(profile,c):
    result=[]
    for additions in profile['examples']:
        codes=['base']+additions
        label=' + '.join(c['names'][code] for code in codes)
        suffix=c['oneSite'] if any(x.startswith('homepage') for x in additions) else c['onePerson']
        monthly={cur:sum(ROWS[code][cur] for code in codes) for cur in ['jpy','usd']}
        annual_parts={}
        for cur in ['jpy','usd']:
            yearly=sum(ROWS[x][cur+'_annual'] for x in codes if cur+'_annual' in ROWS[x])
            month=sum(ROWS[x][cur] for x in codes if cur+'_annual' not in ROWS[x])
            annual_parts[cur]=money(yearly,cur)+' · '+c['annual']+((' + '+money(month,cur)+' · '+c['monthly']) if month else '')
        values=''.join(f'<div><dt>{cur.upper()} · {e(c["monthly"])}</dt><dd class="sp26-number">{money(monthly[cur],cur)}</dd></div>' for cur in ['jpy','usd'])
        annual=''.join('<p class="sp26-number">'+e(annual_parts[cur])+'</p>' for cur in ['jpy','usd'])
        result.append('<article class="sp26-example" data-example="'+','.join(codes)+'"><h4>'+e(label)+'</h4><p>'+e(suffix)+' · '+e(c['beforeTax'])+'</p><dl>'+values+'</dl><p class="sp26-subtitle">'+e(c['baseAnnual'])+'</p>'+annual+'</article>')
    return '<div class="sp26-examples">'+''.join(result)+'</div>'

def enabled_checkout(route):
    checkout = route.get('checkout')
    return checkout if checkout and checkout['enabled'] else None


def render(route):
    c=COPY[route['locale']];profile=MAP['profiles'][route['profile']]
    optional=''
    if profile['optional']:
        note=c['hpRule'] if route['profile']=='homepage' else c['optionalNote']
        optional = (f'<h3 id="sp26-optional-rates">{e(c["optional"])}</h3><p>{e(note)}</p>'
                    + price_table(profile['optional'], c, 'sp26-optional-rates'))
    checkout = enabled_checkout(route)
    title = checkout['title'] if checkout else c['title']
    if checkout:
        intro = (f'<p>{e(checkout["intro"])}</p>'
                 f'<p><a class="button button-primary" href="{e(checkout["href"])}">{e(checkout["label"])}</a></p>')
    else:
        intro = (f'<p class="sp26-status"><strong>{e(c["status"])}</strong></p>\n'
                 f'<p>{e(c["separation"])}</p>')
    rules=[c['allowance'],c['transcriptionSla'],checkout['taxNote'] if checkout else c['taxNote']]
    if route['profile'] in ['development','fp']:rules.append(c['byo'])
    if route['profile']=='homepage':rules.append(c['hpRule'])
    if route['profile'] in ['hearing','fp']:rules.append(c['hearingRule'])
    contact=route.get('existingContact')
    contact_note = '' if checkout else '（新料金での申込受付前）'
    existing_contact = (
        f'<p><a href="{e(contact["href"])}">{e(contact["label"])}</a>{contact_note}</p>'
        if contact else ''
    )
    legacy_anchor='<span id="pricing"></span>' if route.get('placement')=='replace-pricing' else ''
    rate_breakdown = (f'<h3 id="sp26-primary-rates">{e(c["primary"])}</h3>'
                      + price_table(profile['primary'], c, 'sp26-primary-rates') + optional)
    total_examples = f'<h3>{e(c["examples"])}</h3><p>{e(c["exampleNote"])}</p>{examples(profile, c)}'
    sections = [rate_breakdown, total_examples]
    if route['profile'] == 'rosenz':
        sections.reverse()
    return START+f'''\n<section class="sp26" id="new-pricing" data-service-pricing-202611="{route['profile']}" aria-labelledby="sp26-title"><div class="sp26-frame">{legacy_anchor}
<h2 id="sp26-title">{e(title)}</h2>{intro}<p>{e(c['country'])} {e(c['beforeTax'])}</p><p>{e(c['trial'])}</p>
{''.join(sections)}
<h3 id="sp26-usage-rates">{e(c['usage'])}</h3>{price_table(profile['usage'], c, 'sp26-usage-rates', usage=True)}
<ul class="sp26-notes">{''.join('<li>'+e(x)+'</li>' for x in rules)}</ul>
{existing_contact}<p><a href="/pricing-2026-11.html">{e(c['overview'])} ↗</a></p>
</div></section>\n'''+END

class SectionRanges(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False);self.source=source;self.lines=[0]
        self.lines += [m.end() for m in re.finditer('\n',source)];self.stack=[];self.target=None
        self.feed(source)
    def char_offset(self):
        line,col=self.getpos();return self.lines[line-1]+col
    def handle_starttag(self,tag,attrs):
        if tag=='section':self.stack.append((self.char_offset(),dict(attrs).get('id')))
    def handle_endtag(self,tag):
        if tag=='section' and self.stack:
            start,identifier=self.stack.pop()
            if identifier=='pricing':self.target=(start,self.char_offset()+len('</section>'))

def apply(source,path):
    key=Path(path).relative_to(SITE).as_posix()
    route=ROUTES.get(key)
    if route is None:return source
    c=COPY[route['locale']]
    block=render(route)
    if START in source:
        if source.count(START)!=1 or source.count(END)!=1:raise ValueError('Duplicate service price block: '+key)
        source=re.sub(re.escape(START)+r'[\s\S]*?'+re.escape(END),lambda _:block,source,count=1)
    elif route.get('placement')=='replace-pricing':
        ranges=SectionRanges(source)
        if not ranges.target:raise ValueError('Expected existing future price section: '+key)
        a,b=ranges.target;source=source[:a]+block+source[b:]
    else:
        if source.count('</main>')!=1:raise ValueError('Expected one service main: '+key)
        source=source.replace('</main>',block+'\n</main>',1)
    checkout = enabled_checkout(route)
    notice_copy = checkout['intro'] if checkout else c['currentNotice']
    notice_label = checkout['title'] if checkout else c['title']
    notice=NOTICE_START+'<aside class="sp26-notice"><p>'+e(notice_copy)+'</p><a href="#new-pricing">'+e(notice_label)+' ↓</a></aside>'+NOTICE_END
    if NOTICE_START in source:source=re.sub(re.escape(NOTICE_START)+r'[\s\S]*?'+re.escape(NOTICE_END),lambda _:notice,source,count=1)
    else:
        source,count=re.subn(r'(<main\b[^>]*>)',lambda m:m[0]+notice,source,count=1)
        if count!=1:raise ValueError('Service main missing: '+key)
    css=SITE/'pricing-rate-tables.css'
    css_url='/hp-management/law-firm/pricing-rate-tables.css' if key=='hp-management/law-firm.html' else '/pricing-rate-tables.css'
    asset='<link rel="stylesheet" data-service-pricing-style href="'+css_url+'?v='+hashlib.sha256(css.read_bytes()).hexdigest()[:12]+'">'
    source=re.sub(r'<link\b[^>]*data-service-pricing-style[^>]*>','',source)
    # Accessibility is the final shared head asset. Preserve that order when
    # this publisher is run independently after full-page generation.
    accessibility = re.search(r'<link\b[^>]*href="/(?:hp-management/law-firm/)?page-accessibility\.css[^" ]*"[^>]*>', source)
    if accessibility:
        return source[:accessibility.start()] + asset + source[accessibility.start():]
    return source.replace('</head>',asset+'</head>',1)
