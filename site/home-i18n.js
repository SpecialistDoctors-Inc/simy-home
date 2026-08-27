(() => {
  const STORAGE_KEY = "simy-home-locale";
  const SUPPORTED_LOCALES = new Set(["en", "ja", "hi", "es", "fr", "zh-Hans"]);

  const JA_COPY = Object.freeze({
    "Skip to content": "本文へ移動",
    "Your Digital Twin": "あなたのデジタルツイン",
    "Product": "プロダクト",
    "Use cases": "ユースケース",
    "How it works": "仕組み",
    "Apps": "連携アプリ",
    "Why SIMY": "SIMYの違い",
    "Pricing": "料金",
    "Log in": "ログイン",
    "Log in to SIMY": "SIMYにログイン",
    "Map my workflow": "最初のワークフローを相談",
    "Map my first workflow": "最初のワークフローを相談",
    "Open navigation": "ナビゲーションを開く",
    "Close navigation": "ナビゲーションを閉じる",
    "Language": "言語",

    "Your Digital Twin for work that keeps moving": "動き続ける仕事のための、あなたのデジタルツイン",
    "You’re using AI.": "AIは使っている。",
    "But the workload hasn’t gone down.": "でも、仕事は\n減っていない。",
    "You’re using AI. But the workload hasn’t gone down.": "AIは使っている。でも、仕事は減っていない。",
    "Turn chats and conversations into workflows that get work done.": "チャットや会話を、仕事が進む仕組みに変える。",
    "Turn conversations into workflows that get work done.": "会話を、仕事が進む仕組みに変える。",
    "Bring in the conversations that matter. SIMY learns the checks, priorities, and non-negotiables behind your best work, turns them into focused Pipelines, and selects the right one automatically. Autorun takes it from there.": "必要な会話だけをSIMYへ。あなたが良い仕事で欠かさない確認、優先順位、譲れない基準を学び、必要なものだけのパイプラインに変えます。新しい仕事が来れば最適なものを自動で選び、その先はAutorunが進めます。",
    "See SIMY at work": "SIMYの動きを見る",
    "Talk to us": "相談する",
    "No agent to choose": "エージェント選びは不要",
    "No pipeline to manage": "パイプライン管理は不要",
    "Runs Codex through App Server": "App Server経由でCodexを実行",
    "Work pattern detected": "仕事の型を検出",
    "Across selected work chats": "選択した仕事の会話から",
    "“Check the user impact. Verify the evidence. Make the result easy to review.”": "「ユーザーへの影響を確認する。根拠を検証する。レビューしやすい形にする。」",
    "AI-selected pipeline": "AIが選んだパイプライン",
    "AI-SELECTED PIPELINE": "AIが選んだパイプライン",
    "Release quality": "リリース品質",
    "Running": "実行中",
    "Protect user impact": "ユーザーへの影響を守る",
    "Kept": "採用",
    "Verify the evidence": "根拠を検証する",
    "Make review effortless": "レビューしやすくする",
    "Run with Autorun": "Autorunで実行",
    "Working": "処理中",
    "Selected automatically": "自動で選択済み",
    "Autorun is already working.": "Autorunは、もう動いています。",
    "When the conversation ends,": "会話が終わると、",
    "Context captured": "文脈を引き継ぐ",
    "SIMY gets to work.": "SIMYが動き出す。",
    "The right pipeline, selected automatically": "最適なパイプラインを自動選択",
    "Moving the work forward": "仕事を前へ進める",

    "No agent menu. No pipeline picker.": "エージェント一覧も、パイプライン選びも不要。",
    "Your conversations become the way work gets done.": "会話が、仕事の進め方になる。",
    "SIMY finds the patterns behind how you work best, turns them into focused Pipelines, and automatically selects the right one whenever new work arrives.": "SIMYは、あなたが良い仕事で繰り返している判断と確認を見つけ、必要なものだけのパイプラインにします。新しい仕事が来れば、合うものを自動で選びます。",
    "Conversation source": "会話の取り込み元",
    "Request in Codex": "Codexでの依頼",
    "Request in Claude Code": "Claude Codeでの依頼",
    "Request in Cowork": "Coworkでの依頼",
    "New work": "新しい仕事",
    "You": "あなた",
    "Review this release before it ships. Check the user impact, evidence, and review quality.": "このリリースを公開前にレビューして。ユーザーへの影響、根拠、レビュー品質を確認して。",
    "I matched this work to your release-quality pipeline. Autorun is starting the essential checks now.": "この仕事に、あなたのリリース品質パイプラインを適用しました。Autorunが必要な確認を開始します。",
    "Investigate this regression. Trace the cause before changing code and leave evidence another engineer can review.": "このリグレッションを調査して。コードを変える前に原因を追い、別のエンジニアがレビューできる根拠を残して。",
    "I matched this to your investigation pipeline. Autorun is tracing the cause and preserving the review evidence now.": "この仕事に、あなたの調査パイプラインを適用しました。Autorunが原因を追い、レビュー用の根拠を残します。",
    "Turn these updates into a concise decision brief. Surface only material changes and trace every claim to evidence.": "この更新を簡潔な意思決定資料にして。重要な変更だけを示し、すべての主張を根拠までたどれるようにして。",
    "I matched this to your decision-brief pipeline. Autorun is applying your materiality and evidence checks now.": "この仕事に、あなたの意思決定資料パイプラインを適用しました。Autorunが重要性と根拠の確認を進めます。",
    "You bring the request. SIMY brings the right way of working.": "あなたは仕事を頼む。SIMYが、あなたらしい進め方を選ぶ。",
    "Your release-quality pipeline": "あなたのリリース品質パイプライン",
    "Your investigation pipeline": "あなたの調査パイプライン",
    "Your decision-brief pipeline": "あなたの意思決定資料パイプライン",
    "Recognize the work": "仕事を見極める",
    "Recognize the investigation": "調査内容を見極める",
    "Recognize the briefing task": "資料作成の目的を見極める",
    "Done": "完了",
    "Select the matching pipeline": "合うパイプラインを選ぶ",
    "Run the essential checks": "必要な確認を実行する",
    "Trace cause and evidence": "原因と根拠を追う",
    "Apply the briefing checks": "資料の確認項目を実行する",
    "Update My Actions": "My Actionsを更新する",
    "Next": "次",
    "What you did not have to do": "あなたがしなくてよかったこと",
    "No agent chosen · pipeline selected · Autorun running": "エージェント選びなし・パイプライン選択済み・Autorun実行中",
    "No agent chosen · investigation pipeline selected · Autorun running": "エージェント選びなし・調査パイプライン選択済み・Autorun実行中",
    "No agent chosen · briefing pipeline selected · Autorun running": "エージェント選びなし・資料作成パイプライン選択済み・Autorun実行中",
    "Describe the outcome. SIMY selects the Pipeline.": "成果を伝える。SIMYがパイプラインを選ぶ。",
    "Autorun moves it forward.": "その先は、Autorunが進める。",

    "Codex, connected": "Codexと連携",
    "Keep working in Codex. Let SIMY carry the work forward.": "Codexで頼む。その先の仕事はSIMYが動かす。",
    "Connect the ChatGPT account you already use. Through Codex App Server, SIMY starts and continues Codex sessions for you; usage stays with your ChatGPT plan.": "いつものChatGPTアカウントを接続するだけ。SIMYはCodex App Server経由でCodexセッションを開始・継続し、利用量は現在のChatGPTプランに従います。",
    "01 / CONNECT": "01 / 接続",
    "Your ChatGPT account": "あなたのChatGPTアカウント",
    "Connect the account and ChatGPT plan you already use.": "いつも使っているアカウントとChatGPTプランを接続します。",
    "Connected": "接続済み",
    "02 / RUN": "02 / 実行",
    "SIMY uses the app-server protocol to start and continue Codex sessions.": "SIMYがApp ServerプロトコルでCodexセッションを開始・継続します。",
    "OpenAI documentation": "OpenAI公式ドキュメント",
    "03 / MOVE": "03 / 前進",
    "SIMY selects how the work should run and moves it forward.": "SIMYが仕事の進め方を選び、前へ動かします。",
    "Autorun working": "Autorun実行中",
    "Codex and ChatGPT are products of OpenAI. SIMY is an independent product.": "CodexとChatGPTはOpenAIの製品です。SIMYは独立した製品です。",

    "The SIMY loop": "SIMYの仕事の進め方",
    "Stop managing the AI. Start moving the work.": "AIを管理するのをやめて、仕事を動かそう。",
    "SIMY finds the missing inputs, the right people, and the next move. Autorun handles the sequence, so the work keeps moving until your attention is actually needed.": "SIMYが、足りない情報、関わるべき人、次の一手を見極めます。Autorunが順番どおりに進め、あなたの確認が本当に必要なところまで仕事を止めません。",
    "01 / MY AI": "01 / MY AI",
    "Ask once. Get a way of working that lasts.": "一度頼めば、次からはあなたのやり方で進む。",
    "SIMY understands the outcome and selects the right Pipeline automatically—no agent catalog, no setup maze.": "SIMYが目的を理解し、合うパイプラインを自動で選びます。エージェント一覧も、複雑な設定もありません。",
    "My AI": "My AI",
    "◇ Network": "◇ ネットワーク",
    "New session": "新しいセッション",
    "Prepare the renewal brief": "更新提案資料を準備",
    "Ready": "準備完了",
    "Review customer risks": "顧客リスクを確認",
    "Draft the Q3 plan": "第3四半期計画を下書き",
    "Needs input": "入力が必要",
    "Chat": "チャット",
    "Review scope confirmed": "レビュー範囲を確認済み",
    "Complete": "完了",
    "Results are ready for review.": "成果物をレビューできます。",
    "Prepared for you": "準備したもの",
    "Ask SIMY to continue or revise…": "続行や修正をSIMYに頼む…",
    "02 / AUTORUN + MY ACTIONS": "02 / AUTORUN + MY ACTIONS",
    "Let Autorun get there before the follow-up.": "催促が必要になる前に、Autorunが動く。",
    "SIMY advances recurring and delegated work before it turns into another reminder. My Actions shows only what is moving, finished, or waiting on you.": "定例業務や任せた仕事を、確認や催促が増える前にSIMYが進めます。My Actionsに残るのは、進行中、完了、あなたを待っている仕事だけです。",
    "My Actions": "My Actions",
    "4 active": "4件実行中",
    "Active": "実行中",
    "Backlog": "バックログ",
    "SIMY Autorun": "SIMY Autorun",
    "Renewal brief": "更新提案資料",
    "Autorun running": "Autorun実行中",
    "Weekly status update": "週次進捗レポート",
    "My actions": "自分の対応",
    "Do now": "今やる",
    "Approve the customer response": "顧客への返信を承認",
    "Waiting for you": "あなたの確認待ち",
    "Today": "今日",
    "Confirm the rollout date": "展開日を確認",
    "Owner: you": "担当：あなた",
    "03 / TEMPLATES": "03 / テンプレート",
    "Build the Pipeline once. Use it without thinking twice.": "一度つくる。次からは、意識せず使える。",
    "Your focused Pipelines stay ready. Whenever similar work returns, SIMY selects the right one automatically.": "必要なものだけで作ったパイプラインは、いつでも使える状態に。似た仕事が来るたび、SIMYが自動で選びます。",
    "Search by outcome or template": "成果やテンプレートを検索",
    "Operations": "業務運営",
    "Decisions": "意思決定",
    "Meetings": "会議",
    "Customer follow-up": "顧客フォロー",
    "OPERATIONS": "業務運営",
    "Daily leadership brief": "毎日の経営ブリーフ",
    "Turn updates into decisions, risks, and owners.": "更新情報を、判断・リスク・担当へ整理します。",
    "Use template": "このテンプレートを使う",
    "CUSTOMER WORK": "顧客対応",
    "Important changes only": "重要な変化だけを知らせる",
    "Surface the shifts that need a human decision.": "人の判断が必要な変化だけを知らせます。",
    "04 / MEETINGS": "04 / 会議",
    "Turn meetings into momentum.": "会議を、次の動きに変える。",
    "With consent, SIMY keeps purpose and context together, then turns decisions into the next steps while they are still fresh.": "同意のもと、SIMYが目的と文脈を会話につなぎとめ、決定が新しいうちに次の行動へ変えます。",
    "● Listening": "● 聞き取り中",
    "Outcome to capture": "今回得たい成果",
    "Prepare the evidence for the next decision.": "次の判断に必要な根拠を準備する。",
    "05 / GROWTH": "05 / 成長",
    "See what gets stronger with every run.": "実行するほど、強くなるものが見える。",
    "Completed work reveals the skills, judgment, and repeatable ways of working your team is building.": "完了した仕事から、チームに積み上がるスキル、判断力、再現できる仕事の型が見えてきます。",
    "Level": "レベル",
    "This week": "今週",
    "Workflow design": "ワークフロー設計",
    "Decision quality": "意思決定の質",
    "Follow-through": "実行力",

    "Connected apps": "連携アプリ",
    "Your work stays in the tools your team already uses.": "いつものツールの中で、仕事はそのまま進む。",
    "Connect the apps that hold your conversations, meetings, documents, code, and business signals. SIMY brings in the right context, runs the selected Pipeline, and returns the result where the next step happens.": "会話、会議、文書、コード、事業データがあるアプリを接続。SIMYが必要な文脈を取り込み、選んだパイプラインを実行し、次の仕事が始まる場所へ結果を返します。",
    "AI coding tools": "AI開発ツール",
    "AI coding tools that connect with SIMY": "SIMYと連携できるAI開発ツール",
    "Work apps": "業務アプリ",
    "Sessions · Development work": "セッション・開発作業",
    "Chats · Development context": "チャット・開発コンテキスト",
    "Chats · Code suggestions": "チャット・コード提案",
    "Google Workspace": "Google Workspace",
    "Gmail · Drive · Calendar": "Gmail・Drive・カレンダー",
    "GA4 · Search Console": "GA4・Search Console",
    "Account connection": "アカウント接続",
    "Messages · Channels": "メッセージ・チャンネル",
    "Repositories · Pull requests": "リポジトリ・Pull Request",
    "Recordings · Transcripts": "録画・文字起こし",
    "Pages · Databases": "ページ・データベース",
    "Company documents": "社内文書",
    "Context in": "文脈を取り込む",
    "Messages · meetings · files · metrics": "メッセージ・会議・ファイル・指標",
    "Pipeline selected": "パイプラインを選択",
    "Work out": "仕事へ戻す",
    "Actions · drafts · decisions · updates": "アクション・下書き・判断・更新",
    "Available access and actions depend on the accounts and permissions you connect.": "参照・実行できる範囲は、接続したアカウントと権限によって異なります。",

    "Measured results · Pilot goals": "実測結果・パイロット目標",
    "Proof where we have it.": "実績は、根拠とともに。",
    "Clear targets where we are still learning.": "検証中の目標は、明確に。",
    "Every result is labeled as measured, replayed, referenced, or targeted—so evidence never gets mistaken for a promise.": "数字は、実測・再現検証・参考事例・目標のどれかを明記。根拠と約束を混同させません。",
    "01 / SOFTWARE ENGINEERING": "01 / ソフトウェア開発",
    "INTERNAL AUDIT REPLAY": "社内再現検証",
    "Detection improved from one of five cases to five of five cases in the same audit replay.": "同じ監査再現テストで、不具合の検出は5件中1件から5件中5件へ改善しました。",
    "audit replay detection": "監査再現テストでの検出",
    "Catch the bug before the PR leaves the loop.": "PRを出す前に、不具合を捕まえる。",
    "A knowledge base of 387 historical defects informed the replay checks. Detection improved from one of five cases to five of five.": "過去387件の不具合ナレッジを再現テストに反映。検出は5件中1件から5件中5件へ改善しました。",
    "Requirement": "要件",
    "Independent audit": "独立監査",
    "Five-case cross-repository audit replay · August 2026": "複数リポジトリを横断した5件の監査再現テスト・2026年8月",
    "02 / FINANCIAL PLANNING": "02 / ファイナンシャルプランニング",
    "WORKFLOW TARGET": "業務目標",
    "Current preparation and follow-up work is about sixty minutes. The workflow target is ten to fifteen minutes of review.": "現在約60分かかる面談準備とフォローを、10〜15分の確認時間にすることが目標です。",
    "60m": "60分",
    "10–15m": "10〜15分",
    "current manual work → review-time target": "現在の手作業 → 確認時間の目標",
    "Walk in prepared. Leave with the follow-up underway.": "準備して面談へ。終わる頃にはフォローも進んでいる。",
    "SIMY drafts the client record, planning inputs, next agenda, and follow-up—then surfaces the next line during the meeting.": "SIMYが顧客記録、プランニング情報、次回の議題、フォローを下書きし、面談中は次に伝えるべき内容を表示します。",
    "PILOT CONVERSION GOAL": "パイロット成約率目標",
    "FP interviews and an eight-case product-comparison study · July–August 2026": "FPへのインタビューと8件の製品比較検証・2026年7〜8月",
    "03 / ELECTIVE DENTAL CARE": "03 / 歯科の自由診療",
    "REFERENCE CASE": "参考事例",
    "A comparable script-improvement case grew monthly revenue to one point four times its starting level.": "同様のスクリプト改善事例では、月間売上が開始時の1.4倍になりました。",
    "starting point → monthly revenue index": "開始時 → 月間売上指数",
    "Coach the next line while the consultation is happening.": "説明の最中に、次の一言を支援する。",
    "SIMY listens for missing explanations and surfaces the next line in real time, so each consultation can improve the script that follows.": "SIMYが説明の抜けを聞き取り、次に伝える内容をリアルタイムで表示。面談のたびに、次の説明スクリプトを改善できます。",
    "Live consultation": "相談中",
    "Clarify the treatment difference before discussing price.": "価格の前に、治療の違いを明確に説明する。",
    "Comparable clinic result; two dental use cases reviewed; SIMY deployment pending": "類似医院の結果・歯科2事例を確認・SIMY導入は未実施",
    "04 / SME SALES": "04 / 中小企業の営業",
    "PILOT TARGET": "パイロット目標",
    "Current field survey and drawing work takes three and a half to four days. The pilot target is a draft quote within twenty-four hours of the customer request.": "現在3.5〜4日かかる現地調査と図面作業を、顧客からの依頼後24時間以内の見積もり下書きへ短縮することが目標です。",
    "3.5–4d": "3.5〜4日",
    "<24h": "24時間以内",
    "pilot target · request → draft quote": "パイロット目標・依頼 → 見積もり下書き",
    "Turn the customer ask into a quote before the window closes.": "顧客の要望を、機会を逃す前に見積もりへ。",
    "SIMY converts requirements, field notes, and drawings into the next workflow, drafts the quote, and keeps every handoff moving.": "SIMYが要件、現地メモ、図面を次のワークフローへつなぎ、見積もりを下書きして、引き継ぎを止めずに進めます。",
    "WIN-RATE GOAL": "受注率目標",
    "Current workflow measured in an August 2026 field visit; target to validate in pilot": "2026年8月の現場訪問で現行業務を計測・目標はパイロットで検証予定",
    "Results describe the cited internal or reference case. Targets are pilot goals, not guarantees.": "結果は、記載した社内検証または参考事例に基づきます。目標はパイロットでの検証値であり、保証ではありません。",

    "Not another general-purpose agent": "汎用エージェントとは違う",
    "General agents complete tasks.": "汎用AIは、タスクを終える。",
    "SIMY preserves your way of working.": "SIMYは、あなたの仕事の型を残す。",
    "The difference": "違い",
    "General-purpose agent": "汎用エージェント",
    "What it learns from": "何から学ぶか",
    "The current prompt and general instructions": "今のプロンプトと一般的な指示",
    "Patterns across the work conversations you choose": "あなたが選んだ仕事の会話に繰り返し現れる型",
    "What it keeps": "何を残すか",
    "What is useful for the task in front of it": "目の前のタスクに役立つ情報",
    "Your repeated checks, priorities, and non-negotiables": "繰り返し大切にする確認、優先順位、譲れない基準",
    "What you choose": "あなたが選ぶもの",
    "The agent, prompt, and next step": "エージェント、プロンプト、次の手順",
    "Nothing—SIMY selects the matching pipeline": "何も選ばない。SIMYが合うパイプラインを選ぶ",
    "What happens next": "その後どう進むか",
    "You prompt the next step": "次の手順を人が指示する",
    "Autorun starts the selected pipeline automatically": "Autorunが選ばれたパイプラインを自動で開始する",
    "Only the conversations that matter": "必要な会話だけ",
    "Teach SIMY what good work looks like—without giving it everything.": "すべてを渡さず、良い仕事の基準だけをSIMYへ。",
    "Choose the conversations that reveal your checks, priorities, and non-negotiables. SIMY extracts the patterns that repeat, separates them from one-off detail, and ignores the rest.": "あなたが大切にする確認、優先順位、譲れない基準が表れた会話を選びます。SIMYは繰り返す型を抽出し、一度きりの情報と分け、それ以外は残しません。",
    "Bring in": "取り込むもの",
    "Codex chats": "Codexのチャット",
    "Claude Code chats": "Claude Codeのチャット",
    "Cowork chats": "Coworkのチャット",
    "SIMY keeps": "SIMYが残すもの",
    "Your priorities": "あなたの優先順位",
    "Essential checks": "欠かせない確認",
    "Non-negotiables": "譲れない基準",
    "Choose what SIMY can learn from.": "SIMYに学ばせる会話は、あなたが選ぶ。",
    "Share only the conversations you want SIMY to learn from.": "学ばせたい会話だけを共有します。",
    "See exactly what SIMY kept.": "残した内容を、すべて確認できる。",
    "Review the checks, priorities, and non-negotiables before they become a reusable Pipeline.": "パイプラインにする前に、確認項目、優先順位、譲れない基準を見直せます。",
    "Set the guardrails once.": "境界は、一度だけ決める。",
    "SIMY selects and runs the right Pipeline within the limits you define.": "SIMYは、あなたが決めた範囲で合うパイプラインを選び、実行します。",

    "Recommended · SIMY Quality": "おすすめ · SIMY Quality",
    "Swipe to compare plans →": "横にスワイプしてプランを比較 →",
    "Make every Autorun earn your confidence.": "すべてのAutorunに、任せられる品質を。",
    "SIMY Quality checks the work before it reaches you—without slowing down what comes next.": "SIMY Qualityが、仕事があなたに届く前に検証します。次の流れは止めません。",
    "Starter, SIMY Quality, and Team monthly pricing and features": "Starter、SIMY Quality、Teamの月額料金と機能比較",
    "Monthly · USD": "月額・米ドル",
    "per month · before tax": "月額・税別",
    "Recommended": "おすすめ",
    "Pro plan at checkout": "申込画面ではProプラン",
    "Autorun allowance": "自動実行",
    "100 runs": "100回",
    "Unlimited": "無制限",
    "Storage": "ストレージ",
    "Users": "ユーザー数",
    "Up to 1 user": "最大1ユーザー",
    "Up to 3 users": "最大3ユーザー",
    "Codex account connection": "Codexアカウント連携",
    "Included": "含まれます",
    "Meeting Autorun": "Meeting Autorun",
    "Save and reuse Pipelines": "パイプラインの保存・再利用",
    "Use your connected ChatGPT plan": "接続したChatGPTプランを利用",
    "Quality Loop": "Quality Loop",
    "Not included": "含まれません",
    "Target error rate ≤3%": "目標エラー率 ≤3%",
    "Hearing Mode": "Hearing Mode",
    "Real-time suggestions": "リアルタイム提案",
    "Hearing minutes": "Hearing利用時間",
    "600 min included": "600分込み",
    "each month": "毎月",
    "Additional Hearing usage": "Hearing追加利用",
    "$2 / 60 min": "$2 / 60分",
    "usage-based": "従量制",
    "The ≤3% error rate is a target when SIMY’s defined testing and verification criteria are met. It is not a guaranteed result.": "≤3%のエラー率は、SIMYが定めるテスト・検証基準を満たした場合の目標値であり、結果を保証するものではありません。",
    "The purchase page shows the plans currently available for checkout and the final price before payment. Stripe securely processes payment.": "購入画面で、現在申し込めるプランと最終価格を決済前に確認できます。決済はStripeで安全に処理されます。",
    "Choose a plan": "プランを選ぶ",
    "Choose a SIMY plan and continue to secure Stripe Checkout": "SIMYのプランを選び、安全なStripe Checkoutへ進む",

    "Tell SIMY what needs to move.": "進めたい仕事をSIMYへ。",
    "Autorun takes it from there.": "あとはAutorun。",
    "SIMY recognizes the work, selects the right Pipeline, and moves it forward automatically.": "SIMYが仕事を見極め、合うパイプラインを選び、自動で前へ進めます。",
    "YOUR": "あなたの",
    "WAY": "やり方",
    "CHATS": "会話",
    "ESSENTIALS": "大切なこと",
    "PIPELINE": "パイプライン",
    "Codex connection": "Codex連携",
    "Get started": "はじめる",
    "Contact sales": "営業に相談",
    "Legal": "法務情報",
    "Privacy": "プライバシー",
    "Terms": "利用規約",
    "Oakland, California · Built for work that should keep moving.": "米国カリフォルニア州オークランド・止めたくない仕事のために。",

    "SIMY home": "SIMYホーム",
    "Primary navigation": "メインナビゲーション",
    "Mobile navigation": "モバイルナビゲーション",
    "Product principles": "プロダクトの原則",
    "A conversation becoming a working workflow": "会話が実行されるワークフローへ変わる様子",
    "When the conversation ends, SIMY gets to work": "会話が終わるとSIMYが仕事を始める流れ",
    "ChatGPT account connects to Codex App Server, which powers SIMY pipelines and Autorun": "ChatGPTアカウントをCodex App Serverへ接続し、SIMYのパイプラインとAutorunを動かす流れ",
    "SIMY monthly plan comparison": "SIMY月額プラン比較",
    "Apps that connect with SIMY": "SIMYと連携できるアプリ",
    "Connected app context flows into SIMY, which selects a pipeline, runs Autorun, and returns completed work": "連携アプリの文脈をSIMYへ取り込み、パイプラインを選び、Autorunを実行して、完了した仕事を戻す流れ",
    "Requirement, implementation, independent audit, pull request": "要件、実装、独立監査、Pull Requestの流れ",
    "Live consultation guidance": "相談中のリアルタイム提案",
    "General-purpose agents compared with SIMY": "汎用エージェントとSIMYの比較"
  });

  const PAGE_META = {
    en: {
      title: "SIMY — Turn conversations into workflows that get work done",
      description: "Turn chats and conversations into workflows that get work done. SIMY learns how you work, selects the right Pipeline, and Autorun moves it forward.",
      socialTitle: "You’re using AI. But the workload hasn’t gone down.",
      socialDescription: "SIMY learns your way of working, selects the right Pipeline, and Autorun moves it forward.",
      imageAlt: "You’re using AI. But the workload hasn’t gone down. Turn chats and conversations into workflows that get work done.",
      ogLocale: "en_US"
    },
    ja: {
      title: "SIMY — 会話を、仕事が進むワークフローに",
      description: "チャットや会話を、仕事が進む仕組みに変える。SIMYがあなたの仕事の基準を学び、合うパイプラインを選び、Autorunがその先を進めます。",
      socialTitle: "AIは使っている。でも、仕事は減っていない。",
      socialDescription: "SIMYがあなたの仕事の基準を学び、合うパイプラインを選び、Autorunがその先を進めます。",
      imageAlt: "AIは使っている。でも、仕事は減っていない。チャットや会話を、仕事が進む仕組みに変える。",
      ogLocale: "ja_JP"
    },
    hi: {
      title: "SIMY — बातचीत को काम पूरा करने वाले वर्कफ़्लो में बदलें",
      description: "चैट और बातचीत को काम आगे बढ़ाने वाले वर्कफ़्लो में बदलें। SIMY आपके काम करने का तरीका सीखता है, सही Pipeline चुनता है और Autorun उसे आगे बढ़ाता है।",
      socialTitle: "आप AI का उपयोग कर रहे हैं। लेकिन काम का बोझ कम नहीं हुआ।",
      socialDescription: "SIMY आपके काम करने का तरीका सीखता है, सही Pipeline चुनता है और Autorun उसे आगे बढ़ाता है।",
      imageAlt: "आप AI का उपयोग कर रहे हैं। लेकिन काम का बोझ कम नहीं हुआ। चैट और बातचीत को काम पूरा करने वाले वर्कफ़्लो में बदलें।",
      ogLocale: "hi_IN"
    },
    es: {
      title: "SIMY — Convierte conversaciones en flujos de trabajo que avanzan",
      description: "Convierte chats y conversaciones en flujos que hacen avanzar el trabajo. SIMY aprende cómo trabajas, elige el Pipeline adecuado y Autorun se ocupa del resto.",
      socialTitle: "Usas IA. Pero la carga de trabajo no ha disminuido.",
      socialDescription: "SIMY aprende cómo trabajas, elige el Pipeline adecuado y Autorun se ocupa del resto.",
      imageAlt: "Usas IA. Pero la carga de trabajo no ha disminuido. Convierte chats y conversaciones en flujos de trabajo que hacen avanzar el trabajo.",
      ogLocale: "es_ES"
    },
    fr: {
      title: "SIMY — Transformez les conversations en workflows qui avancent",
      description: "Transformez les échanges en workflows qui font réellement avancer le travail. SIMY apprend votre manière de travailler, choisit le bon Pipeline et Autorun prend le relais.",
      socialTitle: "Vous utilisez l’IA. Mais la charge de travail n’a pas diminué.",
      socialDescription: "SIMY apprend votre manière de travailler, choisit le bon Pipeline et Autorun prend le relais.",
      imageAlt: "Vous utilisez l’IA. Mais la charge de travail n’a pas diminué. Transformez les chats et les conversations en workflows qui font avancer le travail.",
      ogLocale: "fr_FR"
    },
    "zh-Hans": {
      title: "SIMY — 将对话变成真正推进工作的工作流",
      description: "把聊天和对话变成真正推进工作的工作流。SIMY 学习你的工作方式，选择合适的管线，再由 Autorun 持续推进。",
      socialTitle: "你在使用 AI，但工作量并没有减少。",
      socialDescription: "SIMY 学习你的工作方式，选择合适的管线，再由 Autorun 持续推进。",
      imageAlt: "你在使用 AI，但工作量并没有减少。将聊天和对话变成真正推进工作的工作流。",
      ogLocale: "zh_CN"
    }
  };

  let currentLocale = "en";
  const textRecords = [];
  const attributeRecords = [];

  function normalizeLocale(value) {
    const locale = String(value || "").trim().toLowerCase();
    if (["zh", "zh-cn", "zh-sg", "zh-hans"].includes(locale)) return "zh-Hans";
    const baseLocale = locale.split("-")[0];
    return SUPPORTED_LOCALES.has(baseLocale) ? baseLocale : null;
  }

  function resolveInitialLocale() {
    const queryLocale = normalizeLocale(new URL(window.location.href).searchParams.get("lang"));
    if (queryLocale) return queryLocale;
    try {
      const savedLocale = normalizeLocale(window.localStorage.getItem(STORAGE_KEY))
        || normalizeLocale(window.localStorage.getItem("simy-lang"))
        || normalizeLocale(window.localStorage.getItem("simy-language"));
      if (savedLocale) return savedLocale;
    } catch {
      // The selector still works when storage is unavailable.
    }
    return "en";
  }

  function translate(value, locale = currentLocale) {
    if (locale === "en") return value;
    const copy = locale === "ja" ? JA_COPY : window.SIMY_HOME_LOCALES?.[locale];
    return copy?.[value] || value;
  }

  function collectOriginalContent() {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node = walker.nextNode();
    while (node) {
      if (!node.parentElement?.hasAttribute("data-current-year")) {
        const value = node.nodeValue || "";
        const core = value.trim();
        if (core) {
          textRecords.push({
            node,
            core,
            leading: value.match(/^\s*/)?.[0] || "",
            trailing: value.match(/\s*$/)?.[0] || ""
          });
        }
      }
      node = walker.nextNode();
    }

    for (const element of document.querySelectorAll("[aria-label], [title], [placeholder], [alt]")) {
      for (const name of ["aria-label", "title", "placeholder", "alt"]) {
        if (!element.hasAttribute(name)) continue;
        attributeRecords.push({ element, name, value: element.getAttribute(name) || "" });
      }
    }

    for (const link of document.querySelectorAll("a[href]")) {
      link.dataset.originalHref = link.getAttribute("href") || "";
    }
  }

  function updateMeta(locale) {
    const meta = PAGE_META[locale];
    document.title = meta.title;
    const values = {
      'meta[name="description"]': meta.description,
      'meta[property="og:title"]': meta.socialTitle,
      'meta[property="og:description"]': meta.socialDescription,
      'meta[property="og:image:alt"]': meta.imageAlt,
      'meta[property="og:locale"]': meta.ogLocale,
      'meta[name="twitter:title"]': meta.socialTitle,
      'meta[name="twitter:description"]': meta.socialDescription,
      'meta[name="twitter:image:alt"]': meta.imageAlt
    };
    for (const [selector, content] of Object.entries(values)) {
      document.querySelector(selector)?.setAttribute("content", content);
    }

    const structuredData = document.querySelector('script[type="application/ld+json"]');
    if (structuredData) {
      try {
        const payload = JSON.parse(structuredData.textContent || "{}");
        payload.description = meta.description;
        structuredData.textContent = JSON.stringify(payload);
      } catch {
        // Leave valid static metadata untouched if a future schema shape changes.
      }
    }
  }

  function updateLinks(locale) {
    const localeParams = {
      en: { lang: "en", locale: "en", region: "us" },
      ja: { lang: "ja", locale: "ja", region: "jp" },
      hi: { lang: "hi", locale: "hi", region: "in" },
      es: { lang: "es", locale: "es", region: "es" },
      fr: { lang: "fr", locale: "fr", region: "fr" },
      "zh-Hans": { lang: "zh-Hans", locale: "zh-Hans", region: null }
    }[locale];

    for (const link of document.querySelectorAll("a[href]")) {
      const originalHref = link.dataset.originalHref || link.getAttribute("href") || "";
      if (originalHref.startsWith("https://app.simy.one/")) {
        const url = new URL(originalHref);
        for (const [name, value] of Object.entries(localeParams)) {
          if (value === null) url.searchParams.delete(name);
          else url.searchParams.set(name, value);
        }
        link.setAttribute("href", url.toString());
        continue;
      }

      const localUrl = new URL(originalHref, window.location.href);
      if (
        localUrl.origin === window.location.origin
        && ["/privacy.html", "/terms.html"].includes(localUrl.pathname)
      ) {
        localUrl.searchParams.set("lang", locale);
        link.setAttribute("href", `${localUrl.pathname}${localUrl.search}${localUrl.hash}`);
        continue;
      }

      if (originalHref.startsWith("mailto:") && originalHref.includes("?subject=")) {
        const address = originalHref.slice(0, originalHref.indexOf("?subject="));
        const originalSubject = decodeURIComponent(originalHref.slice(originalHref.indexOf("?subject=") + 9));
        const localizedSubjects = {
          ja: ["SIMYについて相談したい", "SIMYで最初のワークフローを設計したい"],
          hi: ["SIMY के बारे में परामर्श", "SIMY के साथ मेरा पहला वर्कफ़्लो डिज़ाइन करें"],
          es: ["Consulta sobre SIMY", "Diseñar mi primer flujo de trabajo con SIMY"],
          fr: ["Demande d’information sur SIMY", "Concevoir mon premier workflow avec SIMY"],
          "zh-Hans": ["咨询 SIMY", "设计我的第一个 SIMY 工作流"]
        };
        const subjectPair = localizedSubjects[locale];
        const subject = subjectPair
          ? subjectPair[originalSubject === "SIMY English site inquiry" ? 0 : 1]
          : originalSubject;
        link.setAttribute("href", `${address}?subject=${encodeURIComponent(subject)}`);
      }
    }
  }

  function updateUrl(locale) {
    const url = new URL(window.location.href);
    url.searchParams.set("lang", locale);
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
  }

  function applyLocale(locale, { persist = false, updateHistory = false } = {}) {
    currentLocale = normalizeLocale(locale) || "en";
    document.documentElement.lang = currentLocale;
    document.documentElement.dir = "ltr";

    for (const record of textRecords) {
      record.node.nodeValue = `${record.leading}${translate(record.core)}${record.trailing}`;
    }
    for (const record of attributeRecords) {
      record.element.setAttribute(record.name, translate(record.value));
    }

    for (const select of document.querySelectorAll("[data-locale-select]")) {
      select.value = currentLocale;
    }

    updateMeta(currentLocale);
    updateLinks(currentLocale);
    if (updateHistory) updateUrl(currentLocale);
    if (persist) {
      try {
        window.localStorage.setItem(STORAGE_KEY, currentLocale);
        window.localStorage.setItem("simy-lang", currentLocale);
        window.localStorage.setItem("simy-language", currentLocale);
        window.localStorage.setItem("simy-lang-source", "manual");
        window.localStorage.setItem("simy-language-source", "manual");
      } catch {
        // The selector still works when storage is unavailable.
      }
    }
    window.dispatchEvent(new CustomEvent("simy:locale-change", { detail: { locale: currentLocale } }));
  }

  window.SIMY_HOME_I18N = {
    get locale() {
      return currentLocale;
    },
    translate
  };

  collectOriginalContent();
  const initialLocale = resolveInitialLocale();
  const localeInUrl = normalizeLocale(new URL(window.location.href).searchParams.get("lang"));
  applyLocale(initialLocale, { updateHistory: !localeInUrl && initialLocale !== "en" });

  for (const select of document.querySelectorAll("[data-locale-select]")) {
    select.addEventListener("change", () => {
      applyLocale(select.value, { persist: true, updateHistory: true });
    });
  }
})();
