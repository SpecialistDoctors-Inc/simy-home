# SIMY 紹介プログラム

2026年11月17日。現行HOME契約に整合した実装。共有DBへの適用とStripeテストモードの統合受入、実送金は未実施。公開ページは開始準備中と案内する。

## 制度と対象

[PLAUD日本公式](https://jp.plaud.ai/pages/affiliate-program)の10%、14日、50日、申請月翌月末までの支払いを参考にしたSIMY独自制度。SIMYの契約通貨USDに合わせ、最低額は$100とする。PLAUDの最低額やグローバル版の条件とは区別する。

- 対象プランの割引後・税抜の現金決済額に対し10%。新規契約の最初の対象有料請求だけ。無料トライアル後も対象、更新の継続報酬なし。
- リンクから14日以内に認証済みチェックアウトで紹介元を固定。その後の再試行やトライアル期間でも紹介元を保持。
- 決済から50日間の確認。部分返金でも該当請求の報酬全額を取り消す。争議は保留、解決結果を反映。
- 確定したUSD残高$100以上で申請。日本時間の月末締め・翌月末までにUSDで支払い。自動為替換算なし。
- 対象は現行HOMEのStarter／SIMY by Industry、月払い／年払いの4契約。4つのPrice IDを環境から明示指定し、実際の商品・通貨・価格の確認後に運用する。Starterの紹介はWeb利用向けであり、CLI利用対象はIT Engineer付きIndustryまたは対象の既存Pro契約。
- 下書きは常にdisabled。DBに有効プログラムは自動作成しない。

## ファイルと動作

HP: `site/affiliate.html`。CLIページから接続。CLI掲載のネイティブ画面の根拠は `../cli-home-refresh/verification.md`。

Web: `/Users/t.shiwaku/.codex/worktrees/simy-web-cli-launch-20261117`。
`/r/[code]`で固定のCLIページへ遷移し、署名HttpOnly cookieを保存。オープンリダイレクトなし。
`/affiliate`は認証済み所有者だけにリンク、広告表示付きブログHTML、報酬、支払申請・履歴を表示。
`/e2e/affiliate`は開発専用の表示サンプルで、リンクコピー・申請は無効。実認証・本番DBの受入試験ではない。

Checkoutではサーバーが紹介元を確認し、組織・ユーザー・Stripe customer・subscriptionを固定。
Stripe webhookは既存署名検証を通過後、固定APIバージョン2024-06-20の正規invoice/charge/subscriptionを読み直す。
対象の最初の有料請求は全ページを探索。更新イベントが先着しても最初を照合し、不完全な取得は再試行する。
整数金額と請求IDによる冪等処理。自己紹介・同一組織・既存顧客・ブラウザーからの金額や紹介者IDの偽装を拒否。

Backend: `/Users/t.shiwaku/.codex/worktrees/simy-backend-cli-launch-20261117`。
`supabase/migrations/20261116235324_affiliate_program.sql`にスキーマ、RLS、service-only RPC。
紹介時点の不変な条件版を保存。新規紹介を停止しても既存の返金・精算を継続。

## 管理操作

`/api/admin/affiliate`は既存のplatform管理者allowlist認証。POSTは同一Origin必須。

| action | 用途 |
| --- | --- |
| proposal_draft | 環境の対象Price IDから無効な制度案を作成 |
| create_program | 条件を指定して無効な版を作成 |
| program_status | 指定版の有効・無効切替（正式開始時のみ） |
| partner_status | pending / approved / suspended（認証管理者と日時を記録） |
| partner_dashboard | 指定所有者の報酬情報を確認 |
| verify_payee | 本人・口座所有確認済みの振込先参照を版管理 |
| prepare_settlement | 申請済みの確定残高を支払batchへ固定。送金は行わない |
| confirm_settlement | 外部で振込済みと確認後、固有の振込参照番号で記録 |
| cancel_settlement | 未送金と確認したbatchを取消 |

支払申請は `/api/affiliate` POSTの `action=request_payout,currency=usd`。
ユーザーID・金額はサーバーと台帳が決定。最低額・二重申請・二重割当をDBロックで制御。
支払予定の固定と振込済み確認を分け、振込中に返金が来ても、実振込記録と次回のマイナス調整を両方保持する。

銀行やStripe Connectによる自動送金、口座登録、税務帳票は未接続。現在は管理者の外部手動振込を監査記録する方式。
管理操作は保護されたAPIまでで、管理者専用UIは追加していない。

## 有効化前の確認

1. 正式条件・対象商品を確認し、既存の全migrationと統合した専用dev環境へ適用する。今回のPG試験はidentity/billing scaffoldと新migrationの検証であり、既存全migrationの受入ではない。
2. 実際のStripe Price ID・通貨・商品を確認。新しいWebhookイベント（invoice.paid、charge.refunded、charge.dispute.created/updated/closed）を購読する。
3. `SIMY_AFFILIATE_LEDGER_READY=1`はmigration適用後だけ。`SIMY_AFFILIATE_SIGNING_KEYS`は32文字以上の秘密鍵（先頭が署名用、後続は更新時の検証用）。`SIMY_AFFILIATE_NEW_REFERRALS=1`は新規受付の明示開始時だけ。
4. Stripe test modeで紹介→認証→checkout→trial→決済→返金→申請→精算を受入確認する。既存の本番決済キーや共有DBへは今回アクセスしていない。
5. 振込先の確認方法・月次作業担当・運用監視を用意し、実際の送金開始を別途判断する。

## 検証

- Web関連234テスト成功（署名、owner、自己承認拒否、CSRF、価格、通貨、trial後初回・全ページ探索・再試行、返金、コピー失敗、JPY/USD/KWD、課金既存ルート等）。型検査・対象ESLint成功。
- `python3 scripts/test-affiliate-local.py`: 独立したsocket-only PostgreSQL17でmigration、整数台帳、返金、申請最低額、JST月末・閏年、振込中の返金、冪等、RLSを確認。終了後cluster削除。共有DBには接続しない。
- HP全1632テスト成功。生成整合・SEO・共有header check成功。関連17件成功。
- Browserで360/390/720/768/1024/1440幅のHP・画面を検査。横はみ出し0。`responsive.json`。審査中・受付停止・取得失敗・英語表示も確認。
- `screenshots/landing-desktop.jpg`, `screenshots/dashboard-mobile.jpg`は実ブラウザー。サンプルの数字は実報酬の証明ではない。

ログは `/tmp/simy-affiliate-{web-tests,db-tests,typecheck,lint,copy-style,copy-i18n,vocabulary}.log`。

## 2026-11-17 現行HOME契約への整合

以前のJPY・旧Starter/Pro/Team対象の下書きを、現行HOME4契約（月／年、Starter／SIMY by Industry）とUSDへ修正。最低額は10000セント=$100。10％・14日・50日・初回のみ・返金全取消を維持。日英のHTML・バナー・紹介遷移先とログイン後の戻り先を修正した。

現在の作業ツリーは `/Users/t.shiwaku/.codex/worktrees/simy-web-cli-launch-20261117` と `/Users/t.shiwaku/.codex/worktrees/simy-backend-cli-launch-20261117`。元の下書きは保持。

振込先確認を版管理する追加migrationを作成。`verify_payee`では本人・口座所有確認済みの明示と、保護された振込サービスの受取人参照・確認記録参照を必須とする。生の口座情報は受け取らない。`prepare_settlement`が受取人版を固定し、準備中は振込先の差替え・本人確認の取消を禁止。未送金の精算バッチ自体は取消可能。`confirm_settlement`は送金済みの明示に加え、受取人版・通貨・金額・固有送金参照を照合する。API自体は送金しない。

管理されたdev環境とStripeテストモードによる一連の受入は未実施。共有DBへ直接アクセスしていない。具体的な受入と開始条件は `../cli-home-refresh/commercial-launch/release-acceptance.md`。受付フラグはdisabledのままとし、実課金・送金を開始しない。


## 2026-11-18 dev限定適用と反映待ち

ユーザーの限定許可後、Backend PR1669の2つのmigrationはrun44101478894でdevへ適用し、9RLSテーブル・16関数・有効プログラム0件を確認。Web PR3017は必須CI成功後もブランチ保護でマージ権限がなく、管理者のdevマージ待ち。実決済・返金・模擬精算の一連の受入は未実施。Stripe管理画面で正しいテスト料金とdevWebhookを照合し、Ops Draft PR3023に再開手順を用意した。全体の状態と証拠は `../cli-home-refresh/commercial-launch/dev-acceptance-status.md` を参照。初期のローカル実装時点の説明より、この最新状態を優先する。
