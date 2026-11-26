#!/usr/bin/env python3
"""Build or verify service notices and the route/SKU review record; never publish."""
import argparse, hashlib, json, re
from html.parser import HTMLParser
from pathlib import Path
from service_pricing_2026_11 import ROOT, SITE, MAP, apply

class Canonical(HTMLParser):
    def __init__(self, source):
        super().__init__();self.url='';self.feed(source)
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='link' and a.get('rel')=='canonical':self.url=a['href']

def outputs():
    result={}
    lines=['# サービス別の新料金表示', '', '事前案内の実装・レビュー用記録。公開操作、新料金の申込開始、Stripe live の変更は含まない。', '', '料金は公開済みの仕様 `docs/pricing/pricing-2026-11-spec.md` と同じデータから生成する。業種名だけで有料機能を割り当てず、現在のサービス本文の機能に対応させる。', '', '| ページ | 言語 | canonical metadata | 基本・サービス SKU | 任意追加 SKU | 元データ / 生成処理 | 根拠 |', '|---|---|---|---|---|---|---|']
    for route in MAP['routes']:
        p=SITE/route['path'];source=p.read_text();result[p]=apply(source,p)
        profile=MAP['profiles'][route['profile']]
        lines.append('| /'+route['path']+' | '+route['locale']+' | '+Canonical(source).url+' | '+', '.join(profile['primary'])+' | '+(', '.join(profile['optional']) or 'なし')+' | '+route['source']+' / '+route['generator']+' | '+route['evidence']+' |')
    lines += ['', '## 既存 URL と制御範囲', '', '| 旧 URL / 別名 | 遷移先 | 処理 |', '|---|---|---|']
    lines += ['| '+a['pattern']+' | '+a['target']+' | '+a['type']+' |' for a in MAP['aliases']]
    lines += ['', '- 24ページにのみ事前案内を追加。既存の料金・申込・ログイン・相談リンクは保持する。ロセンズは既存の「導入予定料金」を更新し、導入相談メールを保持する。', '- 営業・MR向けの既存録音整理、面談準備、ChatGPT音声ロールプレイに、同時ヒアリング料金を自動的に課さない。リアルタイム文字起こし・助言を使う場合のみ8時間/20時間を任意追加する。', '- 医療機関の旧業種URLはHP管理に遷移する。独立した医療向け同時ヒアリングの販売ページは新設しない。', '- HPは編集者ごとの基本とサイトごとのHP / 安心プラスを組み合わせる。運用サポートのみでは編集できない。', '- 図面見積と追加ストレージは対象サービス未確定のため、サービス別の申込商品にしない。', '- 月払い・実際の年額・月相当額を分ける。年払いのない追加商品は基本の年額と追加商品の月額を別々に示す。', '- 込み量は個人別、契約開始日の月応当日更新。年払いでも毎月更新する。', '- 適用日未定・新料金の申込受付前。既存顧客の自動移行は行わない。税額・税込総額の確定前画面照合とiOS実購入/復元の検証は別途必要。', '- 弁護士HPの独立配信パッケージには同一CSSを同梱し、既存の所有パス・manifest検証を維持する。', '']
    lines += ['- 各用途の月払い合計を先頭に表示。営業・MRは基本のみ、FP・開発支援・HPは必要な基本を含める。会議中の支援、超過、年払い・海外料金は折りたたむ。', '- 開発支援・HP・ロセンズには無関係な文字起こし追加商品の料金表を出さない。', '- 6言語のトップページは現行カタログの月払い合計を先頭に表示。新料金の事前案内から申込を開始しない。', '']
    result[ROOT/'docs/pricing/service-pricing-2026-11.md']='\n'.join(lines)
    css=SITE/'hp-management/law-firm/pricing-rate-tables.css'
    result[css]=(SITE/'pricing-rate-tables.css').read_text()
    accessibility_css=SITE/'hp-management/law-firm/page-accessibility.css'
    result[accessibility_css]=(SITE/'page-accessibility.css').read_text()
    manifest_path=SITE/'hp-management/law-firm/release-manifest.json'
    manifest=json.loads(manifest_path.read_text())
    paths=sorted({x['path'] for x in manifest['files']}|{css.relative_to(SITE).as_posix(),accessibility_css.relative_to(SITE).as_posix()})
    manifest['files']=[]
    for key in paths:
        p=SITE/key;blob=result[p].encode() if p in result else p.read_bytes()
        manifest['files'].append({'path':key,'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()})
    result[manifest_path]=json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    stale=[]
    for path,expected in outputs().items():
        if not path.exists() or path.read_text()!=expected:
            stale.append(path.relative_to(ROOT).as_posix())
            if not args.check:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(expected)
    if args.check and stale:raise SystemExit('Stale service pricing outputs: '+', '.join(stale))
    print(('Verified' if args.check else 'Built')+' service pricing: '+str(len(MAP['routes']))+' routes')
