"""Editorial CLI story and proposed pricing, reusing artwork and the SIMY catalog."""
from html import escape
from decimal import Decimal
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
STORY = json.loads((ROOT / 'scripts/engineering-cli-story.json').read_text())
# Bounds of the new lettering-free illustration sheet, 1055 x 1491.
ROWS = [(0, 394), (396, 347), (745, 357), (1104, 387)]

def story_panels(lang='ja'):
    result = []
    for i, panel in enumerate(STORY[lang]):
        x, w = (0, 527) if i % 2 == 0 else (529, 526)
        y, h = ROWS[i // 2]
        style = f'aspect-ratio:{w}/{h};--image-width:{1055/w*100:.6f}%;--image-left:{-x/w*100:.6f}%;--image-top:{-y/h*100:.6f}%'
        speech = ''.join(f'<div class="cli-speech"><span class="cli-speaker">{escape(d["speaker"])}</span><p>{escape(d["text"])}</p></div>' for d in panel['dialogue'])
        result.append(f'''<li><p class="cli-comic-label"><span>{i+1:02}</span> {escape(panel['title'])}</p><figure class="cli-comic-frame"><div class="cli-dialogue">{speech}</div><div class="cli-comic-visual" style="{style}"><img src="/assets/cli-ui/comic-art.png" width="1055" height="1491" alt="{escape(panel['caption'])}" loading="lazy" decoding="async"></div></figure><p class="cli-comic-caption">{escape(panel['caption'])}</p></li>''')
    return '\n'.join(result)


def proposed_plans(lang='ja'):
    # Resolve the established catalog at build time; no exchange-rate estimate or
    # separate copied price table. Japan's displayed reference tax follows SIMY.
    catalog = json.loads(subprocess.check_output([
        'node', '-e', "const p=require('./site/pricing-catalog.js'); process.stdout.write(JSON.stringify({monthly:p.presentation('jp','ja','monthly'),annual:p.presentation('jp','ja','annual')}))"
    ], cwd=ROOT, text=True))
    plans = [
        ('starter', 'Starter', '個人の開発を、完了まで。', ['Delivery Loopで作業の続きを促す', 'アプリで進行・質問・利用状況を確認', 'Codex・Claude Codeとの接続']),
        ('quality', 'Quality', '品質確認を、仕事の流れに。', ['Starterの想定内容', 'SQMによる適用ルールのチェック', '品質の確認結果・指摘をたどる']),
    ]
    result = []
    for key, name, lead, features in plans:
        monthly, annual = catalog['monthly'], catalog['annual']
        # All displayed annual figures derive from the same cents as the catalog.
        annual_net = f"${Decimal(annual['baseAmounts'][key].replace('$', '').replace(',', '')) * 12:,.2f}"
        if lang == 'en':
            lead = 'Bring personal development to completion.' if key == 'starter' else 'Make quality checks part of the work.'
            features = ['Prompt unfinished work with Delivery Loop', 'See progress, questions and usage in the app', 'Connect Codex or Claude Code'] if key == 'starter' else ['The proposed Starter features', 'Check applicable rules with SQM', 'Review quality findings and follow-up']
            result.append(f'''<article class="cli-plan" data-cli-plan="{key}"><p class="cli-eyebrow">CLI PLAN PROPOSAL</p><h3>{name}</h3><p>{lead}</p><p class="cli-plan-price">{monthly['baseAmounts'][key]}<span> / month, before tax</span></p><p class="cli-plan-tax">Monthly billing · {monthly['taxInclusiveAmounts'][key]} including illustrative 10% Japan tax</p><div class="cli-plan-annual"><strong>Annual billing: {annual['baseAmounts'][key]} / month equivalent, before tax</strong><p>One annual payment of {annual_net} before tax ({annual['annualTotals'][key]} with illustrative Japan tax).</p></div><p class="cli-plan-feature-label">Proposed features</p><ul>{''.join(f'<li>{escape(feature)}</li>' for feature in features)}</ul><a class="cli-textlink" href="mailto:sales@simy.one?subject=SIMY%20CLI%20pricing%20enquiry">Ask about this proposal ↗</a><p class="cli-plan-draft">Draft pricing · Not open for purchase</p></article>''')
            continue
        result.append(f'''<article class="cli-plan" data-cli-plan="{key}"><p class="cli-eyebrow">CLI PLAN PROPOSAL</p><h3>{name}</h3><p>{lead}</p><p class="cli-plan-price">{monthly['baseAmounts'][key]}<span> / 月・税別</span></p><p class="cli-plan-tax">毎月払い・税込 {monthly['taxInclusiveAmounts'][key]} / 月</p><div class="cli-plan-annual"><strong>年払いなら {annual['baseAmounts'][key]} / 月あたり・税別</strong><p>年額 {annual_net}（税込 {annual['annualTotals'][key]}）を一括払いする案です。</p></div><p class="cli-plan-feature-label">想定する内容</p><ul>{''.join(f'<li>{escape(feature)}</li>' for feature in features)}</ul><a class="cli-textlink" href="mailto:sales@simy.one?subject=SIMY%20CLI%20%E6%96%99%E9%87%91%E6%A1%88%E3%81%AE%E7%9B%B8%E8%AB%87">このプランについて相談する ↗</a><p class="cli-plan-draft">仮料金・受付未開始</p></article>''')
    return '\n'.join(result)
