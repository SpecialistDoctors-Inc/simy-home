"""Editorial CLI story and proposed pricing, reusing artwork and the SIMY catalog."""
from html import escape
from decimal import Decimal
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
STORY = json.loads((ROOT / 'scripts/engineering-cli-story.json').read_text())
# Four equal panels in a lettering-free 1536 x 1024 sheet.

def story_panels(lang='ja'):
    result = []
    for i, panel in enumerate(STORY[lang]):
        w, h = 768, 512
        x, y = (i % 2) * w, (i // 2) * h
        style = f'aspect-ratio:{w}/{h};--image-width:{1536/w*100:.6f}%;--image-left:{-x/w*100:.6f}%;--image-top:{-y/h*100:.6f}%'
        speech = ''.join(f'<div class="cli-speech"><span class="cli-speaker">{escape(d["speaker"])}</span><p>{escape(d["text"])}</p></div>' for d in panel['dialogue'])
        result.append(f'''<li><p class="cli-comic-label"><span>{i+1:02}</span> {escape(panel['title'])}</p><figure class="cli-comic-frame"><div class="cli-dialogue">{speech}</div><div class="cli-comic-visual" style="{style}"><img src="/assets/cli-ui/booking-story-art-v2.png" width="1536" height="1024" alt="{escape(panel['caption'])}" loading="lazy" decoding="async"></div></figure><p class="cli-comic-caption">{escape(panel['caption'])}</p></li>''')
    return '\n'.join(result)


def proposed_plans(lang='ja'):
    """Present existing HOME contracts; CLI has no separate purchase flow."""
    catalog = json.loads(subprocess.check_output([
        'node', '-e', "const p=require('./site/pricing-catalog.js');process.stdout.write(JSON.stringify({monthly:p.presentation('jp','ja','monthly'),annual:p.presentation('jp','ja','annual')}))"
    ], cwd=ROOT, text=True))
    en = lang == 'en'
    result = []
    for key, name, storage in [('quality', 'SIMY by Industry', '50 GB'), ('starter', 'Starter', '10 GB')]:
        monthly, annual = catalog['monthly'], catalog['annual']
        annual_net = f"${Decimal(annual['baseAmounts'][key].replace('$', '').replace(',', '')) * 12:,.2f}"
        def signup(cycle):
            return 'https://app.simy.one/signup/?' + '&amp;'.join([f'plan={key}', f'interval={cycle}', f'lang={lang}', f'locale={lang}', 'region=' + ('us' if en else 'jp'), 'industry_package_code=' + ('it_engineer' if key == 'quality' else 'general'), 'storage_30gb=0'])
        if en:
            actions = (f'<a class="cli-textlink" href="/#pricing">For SIMY Web: view Starter ↗</a>' if key == 'starter' else f'<a class="button button-primary" href="{signup("monthly")}">Start CLI with monthly billing ↗</a><a class="cli-textlink" href="{signup("annual")}">Choose annual billing ↗</a>')
            lead = 'SIMY Web plan. Not eligible for SIMY CLI.' if key == 'starter' else 'SIMY CLI with the IT Engineer package.'
            items = (['SIMY CLI is not included', 'For SIMY Web use', '1 user', storage + ' of SIMY storage'] if key == 'starter' else ['SIMY CLI: $0 additional fee', 'IT Engineer package selected at signup', 'Delivery Loop and SQM access, subject to organization permissions', '1 user · ' + storage + ' of SIMY storage'])
            result.append(f'''<article class="cli-plan" data-cli-plan="{key}"><p class="cli-eyebrow">SIMY PLAN</p><h3>{name}</h3><p>{lead}</p><p class="cli-plan-price">{monthly['baseAmounts'][key]}<span> / month, before tax</span></p><p class="cli-plan-tax">Monthly billing · {monthly['taxInclusiveAmounts'][key]} with illustrative 10% Japan tax</p><div class="cli-plan-annual"><strong>Annual billing: {annual['baseAmounts'][key]} / month equivalent, before tax</strong><p>One annual payment of {annual_net} before tax ({annual['annualTotals'][key]} with illustrative Japan tax).</p></div><p class="cli-plan-feature-label">Included in this SIMY plan</p><ul>{''.join(f'<li>{escape(item)}</li>' for item in items)}</ul><div class="cli-plan-actions">{actions}</div><p class="cli-plan-draft">Base plan: 1 calendar month free, then automatic renewal. Cancel before the trial ends to avoid the plan charge. Checkout shows applicable taxes and the final terms.</p></article>''')
        else:
            actions = (f'<a class="cli-textlink" href="/ja.html#pricing">Web用Starterの料金を見る ↗</a>' if key == 'starter' else f'<a class="button button-primary" href="{signup("monthly")}">月払いでCLIを始める ↗</a><a class="cli-textlink" href="{signup("annual")}">年払いを選ぶ ↗</a>')
            lead = 'SIMY Web向け。CLIは対象外です。' if key == 'starter' else 'CLIを使う方へ。IT Engineer付き。'
            items = (['SIMY CLIは対象外', 'SIMY Webの利用向け', '1ユーザー', 'SIMYストレージ ' + storage] if key == 'starter' else ['SIMY CLIの追加利用料：$0', '申し込み時にIT Engineerを選択済み', 'Delivery Loop・SQM（組織の利用権限が必要）', '1ユーザー・SIMYストレージ ' + storage])
            result.append(f'''<article class="cli-plan" data-cli-plan="{key}"><p class="cli-eyebrow">SIMY PLAN</p><h3>{name}</h3><p>{lead}</p><p class="cli-plan-price">{monthly['baseAmounts'][key]}<span> / 月・税別</span></p><p class="cli-plan-tax">毎月払い・税込参考 {monthly['taxInclusiveAmounts'][key]} / 月</p><div class="cli-plan-annual"><strong>年払い：{annual['baseAmounts'][key]} / 月相当・税別</strong><p>年額 {annual_net}（税込参考 {annual['annualTotals'][key]}）を一括でお支払い。</p></div><p class="cli-plan-feature-label">SIMYプランに含まれるもの</p><ul>{''.join(f'<li>{escape(item)}</li>' for item in items)}</ul><div class="cli-plan-actions">{actions}</div><p class="cli-plan-draft">基本プランは1か月無料。その後は選択した周期で自動更新されます。無料期間終了前にキャンセルできます。税額と最終条件は購入画面でご確認ください。</p></article>''')
    return '\n'.join(result)
