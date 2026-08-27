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

    "Your Digital Twin for work in motion": "動き続ける仕事のためのデジタルツイン",
    "You’re using AI.": "AIは使っている。",
    "But the workload hasn’t gone down.": "でも、仕事は\n減っていない。",
    "You’re using AI. But the workload hasn’t gone down.": "AIは使っている。でも、仕事は減っていない。",
    "Turn chats and conversations into workflows that get work done.": "チャットや会話を、仕事が進む仕組みに変える。",
    "Turn conversations into workflows that get work done.": "会話を、仕事が進む仕組みに変える。",
    "Bring the conversations you choose from Codex, Claude Code, and Cowork. SIMY turns the essential patterns into focused pipelines. When work arrives, it selects the right pipeline automatically and Autorun starts—without asking you to choose an agent.": "Codex、Claude Code、Coworkから、選んだ会話だけを取り込みます。SIMYは、そこで繰り返される大切な判断基準を、必要なものだけのパイプラインに変換。仕事が来ると、最適なパイプラインを自動で選び、エージェントを選ばせることなくAutorunを開始します。",
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

    "No agent or pipeline to choose": "エージェントもパイプラインも選ばない",
    "You ask. SIMY selects the pipeline. Autorun gets to work.": "あなたが頼む。SIMYが選ぶ。Autorunが動かす。",
    "SIMY builds focused pipelines from the checks and priorities in your work. For each new request, it recognizes the work, chooses the matching pipeline, and starts Autorun automatically.": "SIMYは、あなたが仕事で大切にしている確認や優先順位から、必要なものだけのパイプラインを作ります。新しい依頼が来るたびに仕事を見極め、合うパイプラインを選び、Autorunを自動で開始します。",
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
    "You ask for the work. SIMY chooses how it should run.": "あなたは仕事を頼むだけ。進め方はSIMYが選びます。",
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
    "You describe the work. SIMY selects the pipeline.": "あなたが仕事を伝える。SIMYがパイプラインを選ぶ。",
    "Autorun takes it from there.": "その先はAutorunが進めます。",

    "Codex, connected": "Codexと連携",
    "Connect your ChatGPT account. SIMY runs Codex through App Server.": "ChatGPTアカウントを接続。SIMYがApp Server経由でCodexを動かします。",
    "SIMY uses Codex App Server—OpenAI’s programmatic interface for rich clients—to start and continue Codex sessions with the ChatGPT account you connect. Usage follows that ChatGPT plan.": "SIMYは、リッチクライアント向けのOpenAI公式インターフェースであるCodex App Serverを使い、接続したChatGPTアカウントでCodexセッションを開始・継続します。利用量は、そのChatGPTプランに従います。",
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
    "SIMY identifies what’s missing, who needs to be involved, and what should happen next—then Autorun moves the work forward in the right order.": "SIMYは、足りないもの、関わるべき人、次にすべきことを見極めます。そのうえでAutorunが、正しい順番で仕事を前へ進めます。",
    "01 / MY AI": "01 / MY AI",
    "Ask for what you need.": "必要な仕事を頼む。",
    "SIMY understands the request and selects the right pipeline automatically—no agent catalog to browse.": "SIMYが依頼を理解し、最適なパイプラインを自動で選びます。エージェント一覧から選ぶ必要はありません。",
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
    "Let Autorun stay ahead.": "Autorunが先回りする。",
    "SIMY moves recurring and delegated work before it becomes another follow-up. My Actions shows what is running, complete, or needs attention.": "定例業務や任せた仕事を、確認作業が増える前にSIMYが進めます。My Actionsでは、実行中・完了・確認が必要な仕事だけを把握できます。",
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
    "Built once. Chosen automatically.": "一度作れば、あとは自動で選ばれる。",
    "Your focused pipelines stay reusable. SIMY picks the matching one whenever the work calls for it.": "必要なものだけで作ったパイプラインは、何度でも再利用できます。仕事が来るたびに、SIMYが合うものを選びます。",
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
    "Capture context as it happens.": "会話の最中に、文脈をつかむ。",
    "With consent, SIMY keeps the purpose attached to the conversation and turns decisions into follow-through.": "同意のもと、SIMYが会話の目的を保ち、決まったことを次の行動につなげます。",
    "● Listening": "● 聞き取り中",
    "Outcome to capture": "今回得たい成果",
    "Prepare the evidence for the next decision.": "次の判断に必要な根拠を準備する。",
    "05 / GROWTH": "05 / 成長",
    "Make progress visible.": "積み上がった力を見えるようにする。",
    "Completed work makes the skills and repeatable workflows you are strengthening easier to see.": "完了した仕事から、伸びているスキルや再現できる仕事の型が見えるようになります。",
    "Level": "レベル",
    "This week": "今週",
    "Workflow design": "ワークフロー設計",
    "Decision quality": "意思決定の質",
    "Follow-through": "実行力",

    "Connected apps": "連携アプリ",
    "The work is already in your tools. SIMY keeps it moving.": "仕事は、すでにいつものツールにある。SIMYがその先を動かします。",
    "Connect the apps where conversations, meetings, documents, code, and business signals already live. SIMY brings the right context into the selected Pipeline and returns the result where work continues.": "会話、会議、文書、コード、事業データがあるアプリを接続します。SIMYが必要な文脈を選ばれたパイプラインへ取り込み、仕事を続ける場所へ結果を返します。",
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
    "Evidence to date.": "これまでに得られた根拠。",
    "Targets for what’s next.": "次に検証する目標。",
    "Each case is labeled as an internal replay, workflow target, reference case, or pilot target—so proof and ambition stay distinct.": "各事例を、社内再現検証・業務目標・参考事例・パイロット目標に分け、実績と目標を混同しないように示しています。",
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
    "A general agent can do the task.": "汎用エージェントは、タスクをこなす。",
    "SIMY preserves how you want it done.": "SIMYは、あなたの仕事の進め方を残す。",
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
    "Selected conversations, not everything": "すべてではなく、選んだ会話だけ",
    "Bring in only the work that shows how you work.": "あなたらしい仕事の進め方が表れた会話だけを取り込む。",
    "Choose the conversations that reveal your quality bar. SIMY looks for repeated patterns, separates signal from one-off detail, and leaves the rest out.": "あなたの品質基準が表れた会話を選びます。SIMYは繰り返される型を見つけ、一度きりの情報と分け、不要なものを残しません。",
    "Bring in": "取り込むもの",
    "Codex chats": "Codexのチャット",
    "Claude Code chats": "Claude Codeのチャット",
    "Cowork chats": "Coworkのチャット",
    "SIMY keeps": "SIMYが残すもの",
    "Your priorities": "あなたの優先順位",
    "Essential checks": "欠かせない確認",
    "Non-negotiables": "譲れない基準",
    "You choose the source.": "取り込む会話は、あなたが選ぶ。",
    "Bring only the conversations you want SIMY to analyze.": "SIMYに分析させたい会話だけを取り込みます。",
    "You see what was kept.": "残した内容は、あなたが確認できる。",
    "Review the checks and priorities before they become a reusable pipeline.": "再利用できるパイプラインにする前に、確認項目と優先順位を見直せます。",
    "You set the boundaries once.": "境界は、最初に一度だけ決める。",
    "SIMY selects and runs the right pipeline within the limits you define.": "SIMYは、あなたが決めた範囲で最適なパイプラインを選び、実行します。",

    "Recommended · SIMY Quality": "おすすめ · SIMY Quality",
    "Swipe to compare plans →": "横にスワイプしてプランを比較 →",
    "Put a Quality Loop around every Autorun.": "すべてのAutorunに、Quality Loopを。",
    "SIMY Quality checks the work before it reaches you—while Autorun keeps it moving.": "SIMY Qualityが、あなたに届く前に仕事を検証。その間もAutorunが前へ進めます。",
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

    "No agent selection. No pipeline picker.": "エージェント選びも、パイプライン選びも不要。",
    "Tell SIMY what needs to move. It takes it from there.": "進めたい仕事をSIMYに伝える。その先はSIMYが動かす。",
    "SIMY recognizes the work, selects the matching pipeline, and starts Autorun automatically.": "SIMYが仕事を見極め、合うパイプラインを選び、Autorunを自動で開始します。",
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
      description: "Turn chats and conversations into workflows that get work done. When the conversation ends, SIMY selects the right pipeline and Autorun gets to work.",
      socialTitle: "You’re using AI. But the workload hasn’t gone down.",
      socialDescription: "When the conversation ends, SIMY selects the right pipeline and Autorun gets to work.",
      imageAlt: "You’re using AI. But the workload hasn’t gone down. Turn chats and conversations into workflows that get work done.",
      ogLocale: "en_US"
    },
    ja: {
      title: "SIMY — 会話を、仕事が進むワークフローに",
      description: "チャットや会話を、仕事が進む仕組みに変える。会話が終わると、SIMYが最適なパイプラインを選び、Autorunが仕事を動かします。",
      socialTitle: "AIは使っている。でも、仕事は減っていない。",
      socialDescription: "会話が終わると、SIMYが最適なパイプラインを選び、Autorunが仕事を動かします。",
      imageAlt: "AIは使っている。でも、仕事は減っていない。チャットや会話を、仕事が進む仕組みに変える。",
      ogLocale: "ja_JP"
    },
    hi: {
      title: "SIMY — बातचीत को काम पूरा करने वाले वर्कफ़्लो में बदलें",
      description: "चैट और बातचीत को काम पूरा करने वाले वर्कफ़्लो में बदलें। बातचीत खत्म होते ही SIMY सही पाइपलाइन चुनता है और Autorun काम आगे बढ़ाता है।",
      socialTitle: "आप AI का उपयोग कर रहे हैं। लेकिन काम का बोझ कम नहीं हुआ।",
      socialDescription: "बातचीत खत्म होते ही SIMY सही पाइपलाइन चुनता है और Autorun काम आगे बढ़ाता है।",
      imageAlt: "आप AI का उपयोग कर रहे हैं। लेकिन काम का बोझ कम नहीं हुआ। चैट और बातचीत को काम पूरा करने वाले वर्कफ़्लो में बदलें।",
      ogLocale: "hi_IN"
    },
    es: {
      title: "SIMY — Convierte conversaciones en flujos de trabajo que avanzan",
      description: "Convierte chats y conversaciones en flujos de trabajo que hacen avanzar el trabajo. Cuando termina la conversación, SIMY elige el pipeline adecuado y Autorun se pone en marcha.",
      socialTitle: "Usas IA. Pero la carga de trabajo no ha disminuido.",
      socialDescription: "Cuando termina la conversación, SIMY elige el pipeline adecuado y Autorun se pone en marcha.",
      imageAlt: "Usas IA. Pero la carga de trabajo no ha disminuido. Convierte chats y conversaciones en flujos de trabajo que hacen avanzar el trabajo.",
      ogLocale: "es_ES"
    },
    fr: {
      title: "SIMY — Transformez les conversations en workflows qui avancent",
      description: "Transformez les chats et les conversations en workflows qui font avancer le travail. À la fin de la conversation, SIMY choisit le bon pipeline et Autorun se met au travail.",
      socialTitle: "Vous utilisez l’IA. Mais la charge de travail n’a pas diminué.",
      socialDescription: "À la fin de la conversation, SIMY choisit le bon pipeline et Autorun se met au travail.",
      imageAlt: "Vous utilisez l’IA. Mais la charge de travail n’a pas diminué. Transformez les chats et les conversations en workflows qui font avancer le travail.",
      ogLocale: "fr_FR"
    },
    "zh-Hans": {
      title: "SIMY — 将对话变成真正推进工作的工作流",
      description: "将聊天和对话变成真正推进工作的工作流。对话结束后，SIMY 会选择合适的管线，由 Autorun 推动工作继续向前。",
      socialTitle: "你在使用 AI，但工作量并没有减少。",
      socialDescription: "对话结束后，SIMY 会选择合适的管线，由 Autorun 推动工作继续向前。",
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
