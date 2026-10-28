# HP管理・ドメインの一括請求

## 顧客向け
- サーバー代とドメインの管理作業はHP管理料に含む。
- ドメインの移管・更新費用は、見積もりで確定する別料金。
- 医院はGoDaddyへのアカウント作成や直接支払いをしない。SIMYが管理窓口を担当する。
- 初回は月額HP管理料と、その年のドメイン費用をStripe Checkoutでまとめて支払う。
- 月額HP管理料だけが毎月継続する。ドメイン料を毎月重複請求しない。
- 次回ドメイン更新料は、事前承認後、同じHP管理契約の次回請求書に追加する。

## 実装と境界
`node scripts/hp-billing/cli.mjs` はSIMY運用担当者専用。公開サイトで実行しない。既存SaaS契約のWebhookや権限付与には接続していない。
顧客別の承認済み見積書から決済リンクを発行する。一般公開のフォームから金額を受け取らない。

Stripe APIで顧客と税率を検証し、顧客・契約・ドメイン一致を確認する。Checkoutの戻りURLは入金証明にしない。Stripe APIでpaidを確認してから移管・更新を実施する。

## 必要設定
- `STRIPE_SECRET_KEY`: サーバー/運用端末の秘密環境変数。サイトやGitへ入れない。
- `HP_BILLING_LEDGER`: 永続的に保存・バックアップする運用台帳ディレクトリ。既定は `~/.simy-hp-billing`。全実行者が同じ台帳とロックを使用すること。
- 本番作成時のみ `HP_BILLING_ALLOW_LIVE=1`。本番のカード課金・ドメイン購入はテストでは行わない。
- Stripe側に顧客（cus_）と外税10%の税率（txr_）が必要。税率の適用対象は販売条件に合わせて確認する。

見積書JSON（実データはGit外に保存）:
```json
{
  "id": "quote_clinic_20261028",
  "customer": "cus_REPLACE",
  "plan": "basic",
  "domain": "clinic.example",
  "domainYen": 5000,
  "periodStart": "2026-11-01",
  "periodEnd": "2027-11-01",
  "expiresAt": "2026-10-31T14:59:59Z",
  "approvalReference": "顧客が承認した見積書の管理番号",
  "taxRate": "txr_REPLACE"
}
```
`domainYen`は税別円。上記金額は例。GoDaddyの実際の更新料・為替等からSIMYが見積もり、顧客承認を保存する。プランは `basic`, `security`, `basic_manager`, `security_manager`。

```sh
node scripts/hp-billing/cli.mjs preview /secure/quote.json
node scripts/hp-billing/cli.mjs checkout /secure/quote.json
node scripts/hp-billing/cli.mjs verify /secure/quote.json cs_test_REPLACE
node scripts/hp-billing/cli.mjs renewal /secure/renewal-quote.json sub_REPLACE
```
CheckoutのURLは顧客専用の支払いリンク。自動メール送信はしない。更新料の追加は即時の支払い確認ではなく、次回の請求待ち。次回請求日をドメイン期限より十分前に設定し、Stripeの請求書入金とGoDaddyの更新完了を別々に確認する。

## 再実行と障害
- 台帳は見積ID（更新は顧客・ドメイン・対象期間）ごとに保存。同じ完了処理はStripeに再送しない。
- 書き込みがタイムアウトした場合はpendingのまま保持し、無条件再試行しない。Stripe側を照会し、結果を突き合わせて復旧する。Stripeの冪等性キーだけでは長期間の重複防止を保証しない。
- ロックを残したクラッシュは、実行中プロセスがないこととStripe結果を確認して復旧する。
- 台帳と監査ログを消さない。決済リンクを公開リポジトリに記録しない。

## 未接続
Stripeテスト/本番APIキーが未設定のため、実APIによる決済・入金・請求書の検証は未実施。GoDaddyへの購入/移管API、自動更新実行、更新期日スケジューラー、顧客向け管理画面はこのCLIに含まれない。現段階で顧客がセルフサービスで契約開始できる状態ではない。
