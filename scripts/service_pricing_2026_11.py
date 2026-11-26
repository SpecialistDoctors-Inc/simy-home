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
SIMPLE = json.loads((ROOT/'scripts/simple-pricing-copy.json').read_text())
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

def render_rosenz(route, c):
    total = {cur: sum(ROWS[code][cur] for code in ['base', 'land_valuation'])
             for cur in ['jpy', 'usd']}
    base, land, overage = (ROWS[code] for code in ['base', 'land_valuation', 'land_valuation_overage'])
    contact = route['existingContact']
    return START + f'''
<section class="sp26" id="new-pricing" data-service-pricing-202611="rosenz" aria-labelledby="sp26-title"><div class="sp26-frame"><span id="pricing"></span>
<h2 id="sp26-title">ロセンズの料金</h2>
<p class="rosenz-pricing-status">{e(c['status'])}</p>
<article class="rosenz-price-card" aria-label="ロセンズの月払い料金">
  <p class="rosenz-price-label">ロセンズを1人で使うなら</p>
  <p class="rosenz-price-total"><span>月額</span> <strong class="sp26-number">{money(total['jpy'], 'jpy')}</strong><span>（税別）</span></p>
  <p>SIMY 基本を含む、月払いの合計です。</p>
  <dl class="rosenz-price-facts">
    <div><dt>月額に含まれる評価件数</dt><dd>月60件まで</dd></div>
    <div><dt>同時に使える人数</dt><dd>1人</dd></div>
    <div data-sku="land_valuation_overage"><dt>月60件を超えた分</dt><dd>1件 {money(overage['jpy'], 'jpy')}（税別）</dd></div>
  </dl>
  <p class="rosenz-price-example">例：月70件なら {money(total['jpy'] + 10 * overage['jpy'], 'jpy')}（税別）</p>
  <p class="rosenz-price-breakdown">月額の内訳：<span data-sku="base">SIMY 基本 {money(base['jpy'], 'jpy')}</span> ＋ <span data-sku="land_valuation">ロセンズ {money(land['jpy'], 'jpy')}</span></p>
</article>
<p class="rosenz-price-trial">{e(c['trial'])}</p>
<p class="rosenz-price-contact"><a href="{e(contact['href'])}">{e(contact['label'])} →</a></p>
<details class="rosenz-price-details"><summary>すでにSIMYを利用中の方・年払い・海外の料金</summary>
  <h3>すでにSIMY 基本を契約している方</h3>
  <p>契約済みの基本を使う場合、ロセンズの追加は月額 {money(land['jpy'], 'jpy')}（税別）です。</p>
  <h3>SIMY 基本を年払いにする場合</h3>
  <p>基本は年額 {money(base['jpy_annual'], 'jpy')}、ロセンズは月額 {money(land['jpy'], 'jpy')}。別々に請求されます（税別）。ロセンズ自体に年払いはありません。</p>
  <h3>日本以外の請求先</h3>
  <p>月払いの合計は {money(total['usd'], 'usd')}（基本 {money(base['usd'], 'usd')} ＋ ロセンズ {money(land['usd'], 'usd')}）。月60件・同時利用1人、超過は1件 {money(overage['usd'], 'usd')} です（税別）。</p>
  <p>基本を年払いにする場合は年額 {money(base['usd_annual'], 'usd')} ＋ ロセンズ月額 {money(land['usd'], 'usd')} です（税別・別々に請求）。</p>
  <p>{e(c['separation'])}</p><p>{e(c['taxNote'])}</p>
  <p><a href="/pricing-2026-11.html">{e(c['overview'])} ↗</a></p>
</details>
</div></section>
''' + END

def monthly_card(codes, locale, label, features):
    c, s = COPY[locale], SIMPLE[locale]
    currency = 'jpy' if locale == 'ja' else 'usd'
    total = sum(ROWS[code][currency] for code in codes)
    scope = c['oneSite'] if any(code.startswith('homepage') for code in codes) else c['onePerson']
    return f'''<article class="sp26-plan" data-plan-codes="{','.join(codes)}" data-total-currency="{currency}" data-total-amount="{total}">
<h3>{e(label)}</h3><p class="sp26-plan-scope">{e(scope)} · {e(s['afterTrial'])}</p>
<p class="sp26-plan-price"><strong class="sp26-number">{money(total, currency)}</strong> <span>{e(s['period'])}</span></p>
<p class="sp26-plan-total">{e(s['total'])}</p>
<ul>{''.join('<li>'+e(feature)+'</li>' for feature in features)}</ul></article>'''

def usage_list(codes, locale):
    c = COPY[locale]
    currency = 'jpy' if locale == 'ja' else 'usd'
    entries = []
    for code in codes:
        note = c['packIncluded'] if code == 'transcription_20h' else c['botIncluded'] if code == 'hearing_bot' else ''
        entries.append(f'<div><dt>{e(c["names"][code])}{("<small>"+e(note)+"</small>") if note else ""}</dt>'
                       f'<dd>{money(ROWS[code][currency], currency)} / {e(unit(code, c))}</dd></div>')
    return '<dl class="sp26-usage-list">' + ''.join(entries) + '</dl>'

def render(route):
    c=COPY[route['locale']];profile=MAP['profiles'][route['profile']]
    if route['profile'] == 'rosenz':
        return render_rosenz(route, c)
    locale, kind = route['locale'], route['profile']
    s = SIMPLE[locale]
    legacy_anchor = '<span id="pricing"></span>' if route.get('placement') == 'replace-pricing' else ''
    if kind == 'homepage':
        cards = monthly_card(['base', 'homepage'], locale, c['names']['homepage'], [s['website']])
        cards += monthly_card(['base', 'homepage_secure'], locale, c['names']['homepage_secure'], [s['website'], s['secure']])
    else:
        codes = profile['primary']
        feature = {'development': 'development', 'fp': 'fp', 'hearing': 'basic'}[kind]
        label = c['names'][codes[-1]] if kind != 'hearing' else c['names']['base']
        features = [s[feature]]
        if kind in ['hearing', 'fp']:
            features.append(s['workflow'])
        cards = monthly_card(codes, locale, label, features)
    optional = ''
    if kind in ['hearing', 'fp']:
        additions = ''.join(monthly_card(profile['primary'] + [code], locale, c['names'][code],
                                        [c['hearingIncluded'].format(hours=hours)])
                            for code, hours in [('hearing_8h', 8), ('hearing_20h', 20)])
        optional = f'''<details class="sp26-details"><summary>{e(s['hearing'])}</summary>
<p>{e(s['hearingNote'])}</p><div class="sp26-plan-grid">{additions}</div>
<h3>{e(s['optionalUsage'])} · {e(c['beforeTax'])}</h3>{usage_list(['hearing_bot', 'hearing_overage'], locale)}
<p>{e(c['hearingRule'])}</p></details>'''
    elif kind == 'homepage':
        additions = ''.join(monthly_card(['base', code, 'homepage_ops'], locale,
                                        c['names'][code] + ' + ' + c['names']['homepage_ops'], [c['opsIncluded']])
                            for code in ['homepage', 'homepage_secure'])
        optional = f'''<details class="sp26-details"><summary>{e(s['support'])}</summary>
<p>{e(s['supportNote'])}</p><div class="sp26-plan-grid">{additions}</div>
</details>'''
    usage = ''
    usage_codes = [code for code in profile['usage'] if code not in ['hearing_bot', 'hearing_overage']]
    if usage_codes:
        recording = kind in ['hearing', 'fp']
        notes = ''.join(f'<p>{e(text)}</p>' for text in [s['recording'], c['allowance'], c['transcriptionSla']]) if recording else ''
        usage = f'''<details class="sp26-details"><summary>{e(s['recordingDetails'] if recording else s['usage'])}</summary>
<p>{e(c['beforeTax'])}</p>{usage_list(usage_codes, locale)}
{notes}</details>'''
    requirement = (f'<p class="sp26-small">{e(s["baseValue"])}</p>'
                   f'<p class="sp26-requirement">{e(s["ai"])}</p>') if kind in ['development', 'fp', 'hearing'] else ''
    if kind == 'homepage':
        requirement = f'<p class="sp26-requirement">{e(c["hpRule"])}</p>'
    detailed_options = (f'<h3 id="sp26-optional-rates">{e(c["optional"])}</h3>'
                        + price_table(profile['optional'], c, 'sp26-optional-rates')) if profile['optional'] else ''
    detailed_usage = (f'<h3 id="sp26-usage-rates">{e(c["usage"])}</h3>'
                      + price_table(profile['usage'], c, 'sp26-usage-rates', usage=True)) if profile['usage'] else ''
    return START+f'''\n<section class="sp26" id="new-pricing" data-service-pricing-202611="{route['profile']}" aria-labelledby="sp26-title"><div class="sp26-frame">{legacy_anchor}
<h2 id="sp26-title">{e(s['title'])}</h2><p class="sp26-status-line">{e(c['status'])}</p>
<div class="sp26-plan-grid">{cards}</div>
{requirement}<p class="sp26-small">{e(c['trial'])}</p>
{optional}{usage}
<details class="sp26-details"><summary>{e(s['details'])}</summary>
<p>{e(c['country'])}</p><p>{e(s['existing'])}</p>
<h3 id="sp26-primary-rates">{e(c['primary'])}</h3>{price_table(profile['primary'], c, 'sp26-primary-rates')}
{detailed_options}{detailed_usage}
<h3>{e(c['baseAnnual'])}</h3>{examples(profile, c)}
<p>{e(c['separation'])}</p><p>{e(c['taxNote'])}</p>
<p><a href="/pricing-2026-11.html">{e(c['overview'])} ↗</a></p></details>
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
    # Existing prices may coexist with the advance announcement.
    source = re.sub(r'<p class="sp26-current-label">[\s\S]*?</p>', '', source)
    source = re.sub(r'(<section\b[^>]*\bid="pricing"[^>]*>)',
                    lambda m: m[0] + '<p class="sp26-current-label">' + e(SIMPLE[route['locale']]['currentSection']) + '</p>',
                    source, count=1)
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
    notice=NOTICE_START+'<aside class="sp26-notice"><p>'+e(c['currentNotice'])+'</p><a href="#new-pricing">'+e(c['title'])+' ↓</a></aside>'+NOTICE_END
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
