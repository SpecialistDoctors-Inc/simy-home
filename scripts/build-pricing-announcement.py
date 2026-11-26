#!/usr/bin/env python3
"""Generate the advance pricing announcement; this never enables checkout."""
import argparse
import hashlib
import json
import re
from html import escape
from pathlib import Path
from site_header import apply as apply_header

REPO = Path(__file__).resolve().parents[1]
from pricing_2026_11_data import RECURRING, PENDING, USAGE, parse_prices, money
from service_pricing_2026_11 import monthly_card, SIMPLE


def purpose_cards():
    s = SIMPLE['ja']
    plans = [
        (['base'], '営業・MR・日々の仕事', [s['basic'], s['workflow']], '/for/sales/'),
        (['base', 'hearing_8h'], '同時ヒアリング（月8時間）', ['会議中の文字起こし・助言 月8時間'], '/for/sales/#new-pricing'),
        (['base', 'hearing_20h'], '同時ヒアリング（月20時間）', ['会議中の文字起こし・助言 月20時間'], '/for/sales/#new-pricing'),
        (['base', 'fp_quality'], 'FP募集品質・営業管理', [s['fp']], '/for/financial-planners/'),
        (['base', 'sqm_check'], '開発支援', [s['development']], '/for/engineers/'),
        (['base', 'land_valuation'], 'ロセンズ（路線価評価）', ['60件/月・同時利用1人', '超過は1件 ¥300（税別）'], '/for/rosenz/'),
        (['base', 'homepage'], 'ホームページ管理', [s['website']], '/hp-management/'),
        (['base', 'homepage_secure'], 'ホームページ管理 安心プラス', [s['website'], s['secure']], '/hp-management/'),
    ]
    cards = []
    for codes, title, features, href in plans:
        card = monthly_card(codes, 'ja', title, features)
        cards.append(card.replace('</article>', f'<p><a href="{href}">この用途の詳細を見る →</a></p></article>'))
    return ''.join(cards)


def price_cell(row, currency):
    monthly = money(row[currency], currency)
    annual = row.get(f"{currency}_annual")
    if annual is None:
        return monthly
    return f"{monthly}<small>年払い {money(annual, currency)} / 年（{money(annual // 12, currency)} / 月相当）</small>"


def table(rows, codes, label):
    body = []
    for code in codes:
        row = rows[code]
        name = escape(row["name"]).replace("20時間", '<span class="price-term">20時間</span>')
        if code == "land_valuation":
            name += '<br><small>路線価評価</small>'
        unit = escape(row["unit"]).replace("（同時利用1人）", '<span class="price-term">（同時利用1人）</span>')
        body.append(
            f'<tr role="row"><th scope="row" role="rowheader">{name}</th>'
            f'<td role="cell">{unit}</td>'
            f'<td class="amount rate-currency" role="cell"><span class="rate-mobile-label" aria-hidden="true">日本（JPY）</span>{price_cell(row, "jpy")}</td>'
            f'<td class="amount rate-currency" role="cell"><span class="rate-mobile-label" aria-hidden="true">日本以外（USD）</span>{price_cell(row, "usd")}</td>'
            f'<td role="cell">{escape(row["included"])}</td></tr>'
        )
    return f"""<div class="pricing-rate-table">
<table role="table" aria-label="{label}"><thead role="rowgroup"><tr role="row">
<th scope="col" role="columnheader">サービス</th><th scope="col" role="columnheader">単位</th>
<th scope="col" role="columnheader">日本（JPY）</th><th scope="col" role="columnheader">日本以外（USD）</th>
<th scope="col" role="columnheader">含まれる内容</th></tr></thead><tbody role="rowgroup">{''.join(body)}</tbody></table></div>"""


def clinic_examples(rows):
    examples = []
    for label, codes in (
        ("ホームページ管理", ("base", "homepage")),
        ("ホームページ管理 安心プラス", ("base", "homepage_secure")),
        ("安心プラス ＋ AI・HP運用サポート", ("base", "homepage_secure", "homepage_ops")),
    ):
        total = sum(rows[code]["jpy"] for code in codes)
        examples.append(f'<div><dt>{label}</dt><dd>{money(total, "jpy")} <small>/ 月</small></dd></div>')
    return "".join(examples)


def preview(rows):
    base = rows["base"]["jpy"]
    hearing_total = base + rows["hearing_8h"]["jpy"]
    css = (REPO / "site/site-theme.css").read_text(encoding="utf-8").split(".button {", 1)[0]
    shared_css = REPO / "site/pricing-rate-tables.css"
    shared_version = hashlib.sha256(shared_css.read_bytes()).hexdigest()[:12]
    return f"""<!doctype html>
<html lang="ja"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,follow"><title>SIMY 新料金のご案内</title>
<meta name="description" content="SIMYの新料金の事前案内です。適用日未定・新料金での申込受付前です。現在の申込には現行料金が適用されます。">
<link rel="canonical" href="https://simy.one/pricing-2026-11.html">
<link rel="stylesheet" href="/pricing-rate-tables.css?v={shared_version}">
<style>
{css}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--paper); color: var(--ink); font: 1rem/1.65 var(--body), sans-serif; }}
main {{ max-width: 72rem; margin-inline: auto; padding: 2.5rem var(--section-x) 4rem; }}
main > header {{ border-bottom: 1px solid var(--line); padding-bottom: 1.5rem; }}
h1 {{ font-size: clamp(2rem, 5vw, 3.5rem); margin: 0.3rem 0; }}
h2 {{ font-size: 1.5rem; margin: 0 0 0.6rem; }}
p {{ margin: 0.35rem 0 0; }}
section {{ margin-top: 2.5rem; }}
small {{ font-size: 0.82rem; font-weight: 400; }}
.state {{ color: var(--ink-soft); }}
.announcement-status {{ padding: 1rem; margin-top: 1rem; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper-light); }}
main > section {{ min-width: 0; }}
.amount, dd {{ font-variant-numeric: tabular-nums; font-weight: 700; }}
.price-term {{ white-space: nowrap; }}
dl {{ margin: 0.8rem 0 0; border-top: 1px solid var(--line); }}
dl div {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 1rem; align-items: baseline; padding: 0.7rem 0; border-bottom: 1px solid var(--line-soft); }}
dd {{ margin: 0; }}
a {{ color: var(--blue-deep); }}
</style></head><body data-pricing-announcement-only><main>
<header><a href="/ja.html">SIMY 公式ホームへ</a><h1>SIMY 新料金のご案内</h1>
<p>使いたい用途から、毎月の合計料金を確認できます。</p>
<p class="announcement-status"><strong>適用日未定・新料金での申込受付は開始していません。</strong></p>
<p>このページは新料金の事前案内です。現在の申込には現行料金が適用されます。新料金での申込開始時に、適用日と申込方法を改めてご案内します。</p>
<p class="state">掲載金額は税別です。日本の請求先は円、日本以外の請求先はドルでのお支払いになります。税額と税込総額は、申込開始後の確定前画面でご案内します。</p>
<p><a href="#clinic">クリニックのホームページ管理</a></p></header>
<section class="sp26" aria-labelledby="purpose-prices"><h2 id="purpose-prices">使いたい用途で選ぶ</h2>
<p>以下は無料期間終了後の月額合計です。すべてSIMY 基本1人分込み・税別。HP管理は1サイトを1人で更新する場合です。</p>
<div class="sp26-plan-grid">{purpose_cards()}</div>
<p>会議中の支援は8時間・20時間のどちらかを選びます。すでに基本を契約している同じ利用者の基本料金は重複しません。</p>
<p>{escape(SIMPLE["ja"]["baseValue"])}</p>
<p>{escape(SIMPLE["ja"]["ai"])}</p>
<p>HPのドメイン実費や超過利用は別途です。</p>
</section>
<details class="sp26-details"><summary>追加料金・年払い・海外料金などの詳細を見る</summary>
<section aria-labelledby="plans"><h2 id="plans">基本と業務ライセンス</h2>
<p>新料金の提供開始後は、SIMY 基本のみ1か月無料です。追加ライセンスは購入日から課金されます。</p>
<p>仕事の自動実行には、お客様自身のChatGPT接続が必要です。業務ライセンスはSIMY 基本への追加料金です。</p>
<p>録音ファイルの文字起こしは、従来案では1人につき月2時間です。利用枠と追加料金・仕上がり条件は見直し中です。同時ヒアリングの8時間・20時間とは別の枠で、会議時間全体が月2時間に制限される意味ではありません。以下は従来案の条件です。利用量は各利用者で個別管理します。込み量は年払いでも契約開始日に合わせて毎月更新し、翌月には繰り越しません。</p>
{table(rows, RECURRING, "基本と業務ライセンスの料金")}
<p>例：基本 ＋ 同時ヒアリング（8時間）は、国内で1人あたり {money(hearing_total, "jpy")} / 月。</p>
</section>
<section id="clinic" aria-labelledby="clinic-title"><h2 id="clinic-title">クリニックのホームページ管理</h2>
<p>ホームページ管理と運用サポートは1サイト単位です。更新する方ごとにSIMY 基本（月払い {money(base, "jpy")}）が必要です。</p>
<h3>1サイトを1人で更新する場合（国内・月払い）</h3><dl>{clinic_examples(rows)}</dl>
<p>ドメイン取得・更新などの実費や、込み量を超える利用には別途費用がかかります。</p>
<p>AI・HP運用サポートだけでは、ホームページを編集する権限は付きません。編集するサイトにはホームページ管理または安心プラスの契約が必要です。</p>
</section>
<section aria-labelledby="usage"><h2 id="usage">利用量に応じた料金</h2><p>録音ファイルの文字起こしパック・超過料金は見直し中の従来案です。</p>
<p>会議ボットの利用時間は同時ヒアリングの込み時間とは別に数えます。文字起こしパックは購入から3か月有効です。</p>
<p>従来案の仕上がり条件（見直し中）：録音の文字起こしは24時間以内を保証し、目標は1時間以内です。24時間を超えた録音の時間は利用量に数えません。</p>
{table(rows, USAGE, "従量料金と文字起こしパック")}
</section>
<section aria-labelledby="preparing"><h2 id="preparing">提供準備中の項目</h2>
<p>図面・見積の込み枚数と超過料金は仮の条件です。ストレージ追加を含め、提供開始と条件の確定後に改めてご案内します。</p>
{table(rows, tuple(PENDING), "提供準備中の料金と仮の条件")}
</section>
<section aria-labelledby="enterprise"><h2 id="enterprise">Enterprise</h2>
<p>20人からの年契約です。料金は1人あたりの利用料金の1.5倍から個別にお見積もりします。SSO、データの論理分離、導入支援を含みます。</p>
</section></details></main></body></html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rows = parse_prices(REPO / "docs/pricing/pricing-2026-11-spec.md")
    target = REPO / "site/pricing-2026-11.html"
    content = apply_header(preview(rows), target)
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != content:
            raise SystemExit("Pricing announcement is stale; run scripts/build-pricing-announcement.py")
    else:
        target.write_text(content, encoding="utf-8")
    print("PASS: 23 approved pricing rows; advance notice only; checkout not enabled")


if __name__ == "__main__":
    main()
