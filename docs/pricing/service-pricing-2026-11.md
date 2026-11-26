# サービス別の新料金表示

事前案内の実装・レビュー用記録。公開操作、新料金の申込開始、Stripe live の変更は含まない。

料金は公開済みの仕様 `docs/pricing/pricing-2026-11-spec.md` と同じデータから生成する。業種名だけで有料機能を割り当てず、現在のサービス本文の機能に対応させる。

| ページ | 言語 | canonical metadata | 基本・サービス SKU | 任意追加 SKU | 元データ / 生成処理 | 根拠 |
|---|---|---|---|---|---|---|
| /for/engineers/index.html | ja | https://simy.one/for/engineers/ | base, sqm_check | なし | scripts/engineering-cli-{locale}.html (ja/en); scripts/engineering-copy.json (all locales) / scripts/build-engineering-pages.py | Delivery Loop / SQM implementation and quality checks |
| /for/en/engineers/index.html | en | https://simy.one/for/en/engineers/ | base, sqm_check | なし | scripts/engineering-cli-{locale}.html (ja/en); scripts/engineering-copy.json (all locales) / scripts/build-engineering-pages.py | Delivery Loop / SQM implementation and quality checks |
| /for/es/engineers/index.html | es | https://simy.one/for/es/engineers/ | base, sqm_check | なし | scripts/engineering-cli-{locale}.html (ja/en); scripts/engineering-copy.json (all locales) / scripts/build-engineering-pages.py | Delivery Loop / SQM implementation and quality checks |
| /for/fr/engineers/index.html | fr | https://simy.one/for/fr/engineers/ | base, sqm_check | なし | scripts/engineering-cli-{locale}.html (ja/en); scripts/engineering-copy.json (all locales) / scripts/build-engineering-pages.py | Delivery Loop / SQM implementation and quality checks |
| /for/hi/engineers/index.html | hi | https://simy.one/for/hi/engineers/ | base, sqm_check | なし | scripts/engineering-cli-{locale}.html (ja/en); scripts/engineering-copy.json (all locales) / scripts/build-engineering-pages.py | Delivery Loop / SQM implementation and quality checks |
| /for/zh-hans/engineers/index.html | zh-Hans | https://simy.one/for/zh-hans/engineers/ | base, sqm_check | なし | scripts/engineering-cli-{locale}.html (ja/en); scripts/engineering-copy.json (all locales) / scripts/build-engineering-pages.py | Delivery Loop / SQM implementation and quality checks |
| /for/financial-planners/index.html | ja | https://simy.one/for/financial-planners/ | base, fp_quality | hearing_8h, hearing_20h | scripts/build-financial-planner-pages.py + scripts/financial-planner-locales.json / scripts/build-financial-planner-pages.py | FP recorded consultation preparation and sales-quality review |
| /for/en/financial-planners/index.html | en | https://simy.one/for/en/financial-planners/ | base, fp_quality | hearing_8h, hearing_20h | scripts/build-financial-planner-pages.py + scripts/financial-planner-locales.json / scripts/build-financial-planner-pages.py | FP recorded consultation preparation and sales-quality review |
| /for/es/financial-planners/index.html | es | https://simy.one/for/es/financial-planners/ | base, fp_quality | hearing_8h, hearing_20h | scripts/build-financial-planner-pages.py + scripts/financial-planner-locales.json / scripts/build-financial-planner-pages.py | FP recorded consultation preparation and sales-quality review |
| /for/fr/financial-planners/index.html | fr | https://simy.one/for/fr/financial-planners/ | base, fp_quality | hearing_8h, hearing_20h | scripts/build-financial-planner-pages.py + scripts/financial-planner-locales.json / scripts/build-financial-planner-pages.py | FP recorded consultation preparation and sales-quality review |
| /for/hi/financial-planners/index.html | hi | https://simy.one/for/hi/financial-planners/ | base, fp_quality | hearing_8h, hearing_20h | scripts/build-financial-planner-pages.py + scripts/financial-planner-locales.json / scripts/build-financial-planner-pages.py | FP recorded consultation preparation and sales-quality review |
| /for/zh-hans/financial-planners/index.html | zh-Hans | https://simy.one/for/zh-hans/financial-planners/ | base, fp_quality | hearing_8h, hearing_20h | scripts/build-financial-planner-pages.py + scripts/financial-planner-locales.json / scripts/build-financial-planner-pages.py | FP recorded consultation preparation and sales-quality review |
| /for/pharmaceutical-companies/index.html | ja | https://simy.one/for/pharmaceutical-companies/ | base | hearing_8h, hearing_20h | scripts/pharmaceutical-ja.html + scripts/pharmaceutical-locales.json / scripts/build-pharmaceutical-pages.py | MR doctor-specific voice role-play and preparation; live Hearing is optional, not implied by profession |
| /for/en/pharmaceutical-companies/index.html | en | https://simy.one/for/en/pharmaceutical-companies/ | base | hearing_8h, hearing_20h | scripts/pharmaceutical-ja.html + scripts/pharmaceutical-locales.json / scripts/build-pharmaceutical-pages.py | MR doctor-specific voice role-play and preparation; live Hearing is optional, not implied by profession |
| /for/es/pharmaceutical-companies/index.html | es | https://simy.one/for/es/pharmaceutical-companies/ | base | hearing_8h, hearing_20h | scripts/pharmaceutical-ja.html + scripts/pharmaceutical-locales.json / scripts/build-pharmaceutical-pages.py | MR doctor-specific voice role-play and preparation; live Hearing is optional, not implied by profession |
| /for/fr/pharmaceutical-companies/index.html | fr | https://simy.one/for/fr/pharmaceutical-companies/ | base | hearing_8h, hearing_20h | scripts/pharmaceutical-ja.html + scripts/pharmaceutical-locales.json / scripts/build-pharmaceutical-pages.py | MR doctor-specific voice role-play and preparation; live Hearing is optional, not implied by profession |
| /for/hi/pharmaceutical-companies/index.html | hi | https://simy.one/for/hi/pharmaceutical-companies/ | base | hearing_8h, hearing_20h | scripts/pharmaceutical-ja.html + scripts/pharmaceutical-locales.json / scripts/build-pharmaceutical-pages.py | MR doctor-specific voice role-play and preparation; live Hearing is optional, not implied by profession |
| /for/zh-hans/pharmaceutical-companies/index.html | zh-Hans | https://simy.one/for/zh-hans/pharmaceutical-companies/ | base | hearing_8h, hearing_20h | scripts/pharmaceutical-ja.html + scripts/pharmaceutical-locales.json / scripts/build-pharmaceutical-pages.py | MR doctor-specific voice role-play and preparation; live Hearing is optional, not implied by profession |
| /for/sales/index.html | ja | https://simy.one/for/sales/ | base | hearing_8h, hearing_20h | scripts/content-pages.json / scripts/build-content-pages.py | Existing sales page uses an existing meeting memo to draft follow-up; basic workflow needs base; Hearing applies only to live transcription/advice |
| /for/en/sales/index.html | en | https://simy.one/for/en/sales/ | base | hearing_8h, hearing_20h | scripts/content-pages.json / scripts/build-content-pages.py | Existing sales page uses an existing meeting memo to draft follow-up; basic workflow needs base; Hearing applies only to live transcription/advice |
| /for/rosenz/index.html | ja | https://simy.one/for/rosenz/ | base, land_valuation | なし | site/for/rosenz/index.html / scripts/site_header.py | Existing 導入予定料金 explicitly identifies base2280 + land14800, 60 cases/month, one concurrent user |
| /hp-management/index.html | ja | https://simy.one/hp-management.html | base, homepage, homepage_secure | homepage_ops | scripts/hp-management-industries.json / scripts/build-hp-management-industries.py | Industry selector for published clinic and law-firm HP management |
| /hp-management/clinic/index.html | ja | https://simy.one/hp-management/clinic.html | base, homepage, homepage_secure | homepage_ops | site/hp-management/clinic/index.html / scripts/site_header.py | Website editing, hosting/security and HP operations; recorded explanation-to-article is separate, not a live Hearing service |
| /hp-management/law-firm.html | ja | https://simy.one/hp-management/law-firm.html | base, homepage, homepage_secure | homepage_ops | site/hp-management/law-firm.html / scripts/site_header.py | Law firm website editing, security and operational support |

## 既存 URL と制御範囲

| 旧 URL / 別名 | 遷移先 | 処理 |
|---|---|---|
| /for/{locale/}engineers.html | /for/{locale/}engineers/ | generated redirect; no duplicate price content |
| /for/{locale/}financial-planners.html | /for/{locale/}financial-planners/ | legacy alias; no duplicate price content |
| /for/clinic[/|.html|/index.html] | /hp-management/clinic/ | CloudFront/HTML legacy HP redirect; not a Hearing product route |
| /hp-management[.html|/index.html] | /hp-management/ | canonical metadata .html; CloudFront normalizes to slash |
| /hp-management/clinic[.html|/index.html] | /hp-management/clinic/ | metadata .html; published alias uses clinic/index.html |
| /hp-management/clinic-service[|-v2].html | /hp-management/clinic.html | HTML refresh legacy alias |

- 24ページにのみ事前案内を追加。既存の料金・申込・ログイン・相談リンクは保持する。ロセンズは既存の「導入予定料金」を更新し、導入相談メールを保持する。
- 営業・MR向けの既存録音整理、面談準備、ChatGPT音声ロールプレイに、同時ヒアリング料金を自動的に課さない。リアルタイム文字起こし・助言を使う場合のみ8時間/20時間を任意追加する。
- 医療機関の旧業種URLはHP管理に遷移する。独立した医療向け同時ヒアリングの販売ページは新設しない。
- HPは編集者ごとの基本とサイトごとのHP / 安心プラスを組み合わせる。運用サポートのみでは編集できない。
- 図面見積と追加ストレージは対象サービス未確定のため、サービス別の申込商品にしない。
- 月払い・実際の年額・月相当額を分ける。年払いのない追加商品は基本の年額と追加商品の月額を別々に示す。
- 込み量は個人別、契約開始日の月応当日更新。年払いでも毎月更新する。
- 適用日未定・新料金の申込受付前。既存顧客の自動移行は行わない。税額・税込総額の確定前画面照合とiOS実購入/復元の検証は別途必要。
- 弁護士HPの独立配信パッケージには同一CSSを同梱し、既存の所有パス・manifest検証を維持する。

- 各用途の月払い合計を先頭に表示。営業・MRは基本のみ、FP・開発支援・HPは必要な基本を含める。会議中の支援、超過、年払い・海外料金は折りたたむ。
- 開発支援・HP・ロセンズには無関係な文字起こし追加商品の料金表を出さない。
- 6言語のトップページは現行カタログの月払い合計を先頭に表示。新料金の事前案内から申込を開始しない。
