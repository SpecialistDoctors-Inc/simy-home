/**
 * SIMY i18n — Lightweight client-side internationalisation
 * Supports 18 languages including RTL (Arabic)
 *
 * Usage: Add data-i18n="key" to any element.
 *        For innerHTML (HTML allowed), use data-i18n-html="key".
 *        The script auto-detects language from:
 *          1. ?lang= query parameter
 *          2. localStorage('simy-lang')
 *          3. navigator.language / navigator.languages
 *        Falls back to English.
 */
(function () {
  'use strict';

  var SUPPORTED = [
    'en', 'ja', 'zh-Hans', 'zh-Hant', 'fr', 'de', 'es', 'ar',
    'it', 'hi', 'te', 'kn', 'ko', 'vi', 'th', 'id', 'ru', 'pt-BR'
  ];
  var DEFAULT = 'en';
  var CACHE = {};
  var CURRENT_LANG = DEFAULT;

  /* ── Home (/) React SPA translation bridge ──
     The home page (/) is served by a compiled React bundle whose source is
     no longer available, so we can't add t() calls or rebuild it. Instead,
     we walk the #root DOM after React mounts, capture each text node's
     original (English) content, and replace it with the target language
     from /lang/home-dom.json. A MutationObserver re-applies translations
     on every React re-render so the translation always wins. On all other
     pages #root is absent, so this bridge is a no-op. */
  var HOME_DOM_CACHE = {};     // { [lang]: { [enSource]: translated } }
  var ROOT_NODE_MAP = null;    // WeakMap<Text, string> — trimmed English source per text node
  var ROOT_OBSERVER = null;
  var ROOT_DEBOUNCE = null;
  var ROOT_APPLYING = false;   // guard against observer self-triggering

  /* ── Map browser locale to our supported codes ────────────── */
  var LOCALE_MAP = {
    'en': 'en',
    'ja': 'ja',
    'zh': 'zh-Hans',
    'zh-cn': 'zh-Hans',
    'zh-hans': 'zh-Hans',
    'zh-sg': 'zh-Hans',
    'zh-tw': 'zh-Hant',
    'zh-hant': 'zh-Hant',
    'zh-hk': 'zh-Hant',
    'zh-mo': 'zh-Hant',
    'fr': 'fr',
    'de': 'de',
    'es': 'es',
    'ar': 'ar',
    'it': 'it',
    'hi': 'hi',
    'te': 'te',
    'kn': 'kn',
    'ko': 'ko',
    'vi': 'vi',
    'th': 'th',
    'id': 'id',
    'ru': 'ru',
    'pt': 'pt-BR',
    'pt-br': 'pt-BR'
  };

  /* ── Resolve a browser locale string to supported code ────── */
  function resolve(locale) {
    var lc = locale.toLowerCase();
    // Exact match first (e.g. zh-tw, pt-br)
    if (LOCALE_MAP[lc]) return LOCALE_MAP[lc];
    // Try base language (e.g. "de-AT" → "de")
    var base = lc.split('-')[0];
    if (LOCALE_MAP[base]) return LOCALE_MAP[base];
    return null;
  }

  /* ── Detect preferred language ─────────────────────────────── */
  function detect() {
    // 1. Query param  ?lang=ja
    var params = new URLSearchParams(location.search);
    var qLang = params.get('lang');
    if (qLang) {
      var resolved = resolve(qLang);
      if (!resolved && SUPPORTED.indexOf(qLang) !== -1) resolved = qLang;
      if (resolved) return resolved;
    }

    // 2. Saved preference — check BOTH keys. The React bundle on /
    //    uses 'simy-language' for its internal LanguageContext, while
    //    the static pages use 'simy-lang'. Either key is authoritative.
    var saved = localStorage.getItem('simy-lang');
    if (saved && SUPPORTED.indexOf(saved) !== -1) return saved;
    var savedReact = localStorage.getItem('simy-language');
    if (savedReact && SUPPORTED.indexOf(savedReact) !== -1) return savedReact;

    // 3. Browser / OS language
    var langs = navigator.languages || [navigator.language || navigator.userLanguage || ''];
    for (var i = 0; i < langs.length; i++) {
      var match = resolve(langs[i]);
      if (match) return match;
    }

    return DEFAULT;
  }

  /* ── Fetch translation JSON ────────────────────────────────── */
  function load(lang, cb) {
    if (CACHE[lang]) return cb(CACHE[lang]);

    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/lang/' + lang + '.json', true);
    xhr.onreadystatechange = function () {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          try {
            CACHE[lang] = JSON.parse(xhr.responseText);
          } catch (e) {
            CACHE[lang] = {};
          }
        } else {
          CACHE[lang] = {};
        }
        cb(CACHE[lang]);
      }
    };
    xhr.send();
  }

  /* ── SEO data: keywords + per-page title/description per locale ── */
  var SEO = {
    "en": {
      kw: "AI code generation, AI coding agent, problem-solving AI agent, AI that fixes bugs, AI agent for engineers, autonomous AI engineer, AI software engineer, meeting to code, voice to code, speech to code, AI pull request generator, AI pair programmer, meeting to PR, spec to code AI, sprint planning to code, GitHub Copilot alternative, Cursor alternative, Devin alternative, Claude Code alternative, Replit Agent alternative, AI SDLC automation",
      p: {
        "index": { t: "SIMY — AI Code Generation from Meetings | Copilot Alternative", d: "Autonomous AI coding agent that turns meetings into shipped GitHub pull requests. A Copilot, Cursor, Devin, and Claude Code alternative." },
        "pricing": { t: "Pricing — SIMY | AI Code Generation Plans from $20/mo", d: "SIMY pricing for AI code generation from meetings. Starter $20, Pro $40, Scale $100/mo. A cheaper GitHub Copilot alternative." },
        "compare": { t: "Compare SIMY vs Copilot, Cursor, Devin & Claude Code", d: "SIMY vs GitHub Copilot, Cursor, Devin, and Claude Code. Autonomous AI that generates code from meetings — no prompting required." },
        "how-it-works": { t: "How SIMY Works — AI Code Generation from Meetings in 4 Steps", d: "See how SIMY turns meetings into shipped GitHub pull requests in 4 steps: record, AI processes, code generates, PR ships." },
        "contact": { t: "Request a Demo — SIMY | AI Code Generation Platform", d: "Request a SIMY demo. AI code generation from meetings — book a demo, start a free trial, or ask about Enterprise plans." },
        "integrations": { t: "Integrations — SIMY | GitHub, Slack, Zoom, Google Workspace", d: "Connect SIMY with GitHub, Slack, Zoom, and Google Workspace. Ship code from meetings — no IDE extension required." },
        "security": { t: "Security — SIMY | Enterprise AI Coding, HIPAA & SOC2", d: "Enterprise-grade AI code generation with HIPAA and SOC2 roadmap. Trusted by medical SaaS and fintech teams." },
        "about": { t: "About AwakApp Inc. — Makers of SIMY AI Coding Agent", d: "AwakApp Inc., the company behind SIMY — the AI coding agent that generates code from meetings." }
      }
    },
    "ja": {
      kw: "AIコード生成, AIコーディングエージェント, 問題解決 AI エージェント, 課題解決 AI, バグ修正 AI, 自律型AIエンジニア, AIソフトウェアエンジニア, 会議からコード生成, 議事録からコード, 音声からコード, ミーティング コード化, AIプルリクエスト自動生成, AI PR 自動作成, 仕様書からコード AI, スプリント AI 開発, 会議 自動化 開発, AI ペアプログラミング, GitHub Copilot 代替, Cursor 代替, Devin 代替, Claude Code 代替, 開発自動化 AI, 開発効率化 AI",
      p: {
        "index": { t: "SIMY — 会議からコードを生成するAIエンジニア", d: "ミーティングの議論をGitHubプルリクエストに自動変換する自律型AIコーディングエージェント。GitHub Copilot・Cursor・Devin・Claude Codeの代替。" },
        "pricing": { t: "料金 — SIMY | AIコード生成プラン 月額20ドルから", d: "会議からコードを生成するSIMYの料金。Starter月額$20、Pro$40、Scale$100。GitHub Copilot・Cursorより安価なプラン。" },
        "compare": { t: "SIMY vs Copilot・Cursor・Devin・Claude Code 比較", d: "SIMYとGitHub Copilot、Cursor、Devin、Claude Codeを比較。会議から自動でコードを生成する自律型AIエンジニア。" },
        "how-it-works": { t: "使い方 — SIMY | 会議からコード生成 4ステップ", d: "SIMYが会議をGitHubプルリクエストに変える4ステップ：録画、AI処理、コード生成、PR作成。プロンプト不要。" },
        "contact": { t: "デモ申込 — SIMY | AIコード生成プラットフォーム", d: "SIMYのデモをリクエスト。会議からコードを生成するAI — デモ予約、無料トライアル、エンタープライズ相談。" },
        "integrations": { t: "連携サービス — SIMY | GitHub・Slack・Zoom・Google Workspace", d: "GitHub、Slack、Zoom、Google WorkspaceとSIMYを連携。IDE拡張不要で会議からコードを出荷。" },
        "security": { t: "セキュリティ — SIMY | エンタープライズ・HIPAA・SOC2対応", d: "HIPAA・SOC2ロードマップ付きエンタープライズ級AIコード生成。医療SaaS・フィンテックで採用。" },
        "about": { t: "会社概要 — AwakApp株式会社 (SIMY運営元)", d: "SIMYを開発するAwakApp株式会社。会議からコードを生成するAIコーディングエージェントの開発元。" }
      }
    },
    "zh-Hans": {
      kw: "AI代码生成, AI编程代理, 问题解决AI代理, 修复bug的AI, 自主AI工程师, AI软件工程师, 会议转代码, 语音转代码, AI拉取请求生成, AI结对编程, GitHub Copilot替代, Cursor替代, Devin替代, Claude Code替代, AI开发自动化, AI编码助手",
      p: {
        "index": { t: "SIMY — 从会议生成代码的AI编程代理", d: "自主AI编程代理，将会议讨论转化为GitHub拉取请求。GitHub Copilot、Cursor、Devin、Claude Code的替代方案。" },
        "pricing": { t: "价格 — SIMY | AI代码生成套餐 每月20美元起", d: "SIMY从会议生成代码的定价。Starter每月$20，Pro$40，Scale$100。比GitHub Copilot更便宜。" },
        "compare": { t: "SIMY vs Copilot、Cursor、Devin、Claude Code 对比", d: "SIMY对比GitHub Copilot、Cursor、Devin、Claude Code。从会议自动生成代码的自主AI工程师。" },
        "how-it-works": { t: "工作原理 — SIMY | 4步从会议生成代码", d: "了解SIMY如何通过4步将会议转化为GitHub拉取请求：录制、AI处理、代码生成、PR发布。" },
        "contact": { t: "申请演示 — SIMY | AI代码生成平台", d: "申请SIMY演示。从会议生成代码的AI — 预约演示、免费试用或咨询企业版。" },
        "integrations": { t: "集成 — SIMY | GitHub、Slack、Zoom、Google Workspace", d: "将SIMY与GitHub、Slack、Zoom和Google Workspace集成。无需IDE扩展即可从会议发布代码。" },
        "security": { t: "安全 — SIMY | 企业级AI编程、HIPAA与SOC2", d: "SIMY企业级AI代码生成，配备HIPAA和SOC2合规路线图。受医疗SaaS和金融科技团队信赖。" },
        "about": { t: "关于 AwakApp Inc. — SIMY AI编程代理的制造商", d: "AwakApp Inc.，SIMY背后的公司——从会议生成代码的AI编程代理。" }
      }
    },
    "zh-Hant": {
      kw: "AI程式碼生成, AI編程代理, 問題解決AI代理, 修復bug的AI, 自主AI工程師, AI軟體工程師, 會議轉程式碼, 語音轉程式碼, AI拉取請求生成, AI結對編程, GitHub Copilot替代, Cursor替代, Devin替代, Claude Code替代",
      p: {
        "index": { t: "SIMY — 從會議生成程式碼的AI編程代理", d: "自主AI編程代理，將會議討論轉化為GitHub拉取請求。GitHub Copilot、Cursor、Devin、Claude Code的替代方案。" },
        "pricing": { t: "價格 — SIMY | AI程式碼生成方案 每月20美元起", d: "SIMY從會議生成程式碼的定價。Starter每月$20，Pro$40，Scale$100。比GitHub Copilot更便宜。" },
        "compare": { t: "SIMY vs Copilot、Cursor、Devin、Claude Code 比較", d: "SIMY對比GitHub Copilot、Cursor、Devin、Claude Code。從會議自動生成程式碼的自主AI工程師。" },
        "how-it-works": { t: "使用方式 — SIMY | 4步從會議生成程式碼", d: "了解SIMY如何透過4步將會議轉化為GitHub拉取請求：錄製、AI處理、程式碼生成、PR發布。" },
        "contact": { t: "申請示範 — SIMY | AI程式碼生成平台", d: "申請SIMY示範。從會議生成程式碼的AI — 預約示範、免費試用或諮詢企業版。" },
        "integrations": { t: "整合 — SIMY | GitHub、Slack、Zoom、Google Workspace", d: "將SIMY與GitHub、Slack、Zoom和Google Workspace整合。" },
        "security": { t: "安全 — SIMY | 企業級AI編程、HIPAA與SOC2", d: "SIMY企業級AI程式碼生成，配備HIPAA和SOC2合規路線圖。" },
        "about": { t: "關於 AwakApp Inc. — SIMY AI編程代理的製造商", d: "AwakApp Inc.，SIMY背後的公司——從會議生成程式碼的AI編程代理。" }
      }
    },
    "fr": {
      kw: "génération de code IA, agent de codage IA, agent IA résolution de problèmes, IA qui corrige les bugs, ingénieur IA autonome, ingénieur logiciel IA, réunion vers code, voix vers code, alternative GitHub Copilot, alternative Cursor, alternative Devin, alternative Claude Code",
      p: {
        "index": { t: "SIMY — IA qui génère du code depuis vos réunions", d: "Agent de codage IA autonome qui transforme les réunions en pull requests GitHub. Alternative à Copilot, Cursor, Devin et Claude Code." },
        "pricing": { t: "Tarifs — SIMY | Génération de code IA dès 20 $/mois", d: "Tarifs SIMY pour la génération de code depuis les réunions. Starter 20$, Pro 40$, Scale 100$/mois." },
        "compare": { t: "SIMY vs Copilot, Cursor, Devin et Claude Code", d: "SIMY vs GitHub Copilot, Cursor, Devin et Claude Code. IA autonome qui génère du code depuis les réunions." },
        "how-it-works": { t: "Fonctionnement — SIMY | De la réunion au code en 4 étapes", d: "Découvrez comment SIMY transforme les réunions en pull requests GitHub en 4 étapes." },
        "contact": { t: "Demander une démo — SIMY | IA génération de code", d: "Demandez une démo SIMY. Génération de code IA depuis les réunions." },
        "integrations": { t: "Intégrations — SIMY | GitHub, Slack, Zoom, Google Workspace", d: "Connectez SIMY à GitHub, Slack, Zoom et Google Workspace." },
        "security": { t: "Sécurité — SIMY | Codage IA Entreprise, HIPAA & SOC2", d: "Génération de code IA avec feuille de route HIPAA et SOC2." },
        "about": { t: "À propos d'AwakApp Inc. — Créateurs de SIMY", d: "AwakApp Inc., l'entreprise derrière SIMY." }
      }
    },
    "de": {
      kw: "KI-Codegenerierung, KI-Coding-Agent, KI-Agent zur Problemlösung, KI die Bugs behebt, autonomer KI-Ingenieur, KI-Softwareentwickler, Meeting zu Code, Sprache zu Code, GitHub Copilot Alternative, Cursor Alternative, Devin Alternative, Claude Code Alternative",
      p: {
        "index": { t: "SIMY — KI generiert Code aus Ihren Meetings", d: "Autonomer KI-Coding-Agent, der Meetings in GitHub Pull Requests verwandelt. Alternative zu Copilot, Cursor, Devin und Claude Code." },
        "pricing": { t: "Preise — SIMY | KI-Codegenerierung ab 20 $/Monat", d: "SIMY-Preise für KI-Codegenerierung aus Meetings. Starter 20$, Pro 40$, Scale 100$/Monat." },
        "compare": { t: "SIMY vs Copilot, Cursor, Devin & Claude Code", d: "SIMY vs GitHub Copilot, Cursor, Devin und Claude Code. Autonome KI, die Code aus Meetings generiert." },
        "how-it-works": { t: "Funktionsweise — SIMY | Vom Meeting zum Code in 4 Schritten", d: "So verwandelt SIMY Meetings in 4 Schritten in GitHub Pull Requests." },
        "contact": { t: "Demo anfordern — SIMY | KI-Codegenerierung", d: "Fordern Sie eine SIMY-Demo an. KI-Codegenerierung aus Meetings." },
        "integrations": { t: "Integrationen — SIMY | GitHub, Slack, Zoom, Google Workspace", d: "Verbinden Sie SIMY mit GitHub, Slack, Zoom und Google Workspace." },
        "security": { t: "Sicherheit — SIMY | Enterprise-KI-Codegenerierung, HIPAA & SOC2", d: "Enterprise-KI-Codegenerierung mit HIPAA- und SOC2-Roadmap." },
        "about": { t: "Über AwakApp Inc. — Hersteller von SIMY", d: "AwakApp Inc., das Unternehmen hinter SIMY." }
      }
    },
    "es": {
      kw: "generación de código con IA, agente de codificación IA, agente IA resolución de problemas, IA que arregla bugs, ingeniero IA autónomo, ingeniero de software IA, de reunión a código, de voz a código, alternativa GitHub Copilot, alternativa Cursor, alternativa Devin, alternativa Claude Code",
      p: {
        "index": { t: "SIMY — IA que genera código desde tus reuniones", d: "Agente de codificación IA autónomo que convierte reuniones en pull requests de GitHub. Alternativa a Copilot, Cursor, Devin y Claude Code." },
        "pricing": { t: "Precios — SIMY | Generación de código IA desde 20 $/mes", d: "Precios de SIMY para generación de código desde reuniones. Starter 20$, Pro 40$, Scale 100$/mes." },
        "compare": { t: "SIMY vs Copilot, Cursor, Devin y Claude Code", d: "SIMY vs GitHub Copilot, Cursor, Devin y Claude Code. IA autónoma que genera código desde reuniones." },
        "how-it-works": { t: "Cómo funciona — SIMY | De la reunión al código en 4 pasos", d: "Descubre cómo SIMY convierte reuniones en pull requests de GitHub en 4 pasos." },
        "contact": { t: "Solicitar demo — SIMY | IA generación de código", d: "Solicita una demo de SIMY. Generación de código IA desde reuniones." },
        "integrations": { t: "Integraciones — SIMY | GitHub, Slack, Zoom, Google Workspace", d: "Conecta SIMY con GitHub, Slack, Zoom y Google Workspace." },
        "security": { t: "Seguridad — SIMY | Codificación IA Enterprise, HIPAA y SOC2", d: "Generación de código IA de nivel empresarial con HIPAA y SOC2." },
        "about": { t: "Acerca de AwakApp Inc. — Creadores de SIMY", d: "AwakApp Inc., la empresa detrás de SIMY." }
      }
    },
    "ar": {
      kw: "توليد الكود بالذكاء الاصطناعي, وكيل برمجة بالذكاء الاصطناعي, وكيل ذكاء اصطناعي لحل المشكلات, مهندس ذكاء اصطناعي ذاتي, مهندس برمجيات بالذكاء الاصطناعي, من الاجتماع إلى الكود, من الصوت إلى الكود, بديل GitHub Copilot, بديل Cursor, بديل Devin, بديل Claude Code",
      p: {
        "index": { t: "SIMY — ذكاء اصطناعي يولد الكود من اجتماعاتك", d: "وكيل برمجة بالذكاء الاصطناعي يحول الاجتماعات إلى طلبات سحب على GitHub. بديل لـ Copilot و Cursor و Devin و Claude Code." },
        "pricing": { t: "الأسعار — SIMY | توليد الكود من 20$ شهريًا", d: "أسعار SIMY لتوليد الكود من الاجتماعات." },
        "compare": { t: "مقارنة SIMY مع Copilot و Cursor و Devin و Claude Code", d: "SIMY مقابل GitHub Copilot و Cursor و Devin و Claude Code." },
        "how-it-works": { t: "كيف يعمل SIMY — من الاجتماع إلى الكود في 4 خطوات", d: "شاهد كيف يحول SIMY الاجتماعات إلى طلبات سحب GitHub في 4 خطوات." },
        "contact": { t: "اطلب عرضًا — SIMY | منصة توليد الكود", d: "اطلب عرض SIMY." },
        "integrations": { t: "التكاملات — SIMY | GitHub و Slack و Zoom و Google Workspace", d: "اربط SIMY بـ GitHub و Slack و Zoom و Google Workspace." },
        "security": { t: "الأمان — SIMY | HIPAA و SOC2 للمؤسسات", d: "توليد كود بالذكاء الاصطناعي بمستوى المؤسسات." },
        "about": { t: "حول AwakApp Inc. — صانعو SIMY", d: "AwakApp Inc.، الشركة وراء SIMY." }
      }
    },
    "it": {
      kw: "generazione di codice IA, agente di codifica IA, agente IA risoluzione problemi, IA che corregge bug, ingegnere IA autonomo, ingegnere software IA, da riunione a codice, da voce a codice, alternativa GitHub Copilot, alternativa Cursor, alternativa Devin, alternativa Claude Code",
      p: {
        "index": { t: "SIMY — IA che genera codice dalle tue riunioni", d: "Agente di codifica IA autonomo che trasforma le riunioni in pull request GitHub. Alternativa a Copilot, Cursor, Devin e Claude Code." },
        "pricing": { t: "Prezzi — SIMY | Generazione codice IA da 20 $/mese", d: "Prezzi SIMY per la generazione di codice dalle riunioni." },
        "compare": { t: "SIMY vs Copilot, Cursor, Devin e Claude Code", d: "SIMY vs GitHub Copilot, Cursor, Devin e Claude Code." },
        "how-it-works": { t: "Come funziona — SIMY | Dalla riunione al codice in 4 passaggi", d: "Scopri come SIMY trasforma le riunioni in pull request GitHub in 4 passaggi." },
        "contact": { t: "Richiedi una demo — SIMY | IA generazione codice", d: "Richiedi una demo SIMY." },
        "integrations": { t: "Integrazioni — SIMY | GitHub, Slack, Zoom, Google Workspace", d: "Collega SIMY a GitHub, Slack, Zoom e Google Workspace." },
        "security": { t: "Sicurezza — SIMY | Codifica IA Enterprise, HIPAA e SOC2", d: "Generazione di codice IA enterprise con roadmap HIPAA e SOC2." },
        "about": { t: "Chi siamo: AwakApp Inc. — Creatori di SIMY", d: "AwakApp Inc., l'azienda dietro SIMY." }
      }
    },
    "hi": {
      kw: "AI कोड जनरेशन, AI कोडिंग एजेंट, समस्या समाधान AI एजेंट, बग ठीक करने वाला AI, स्वायत्त AI इंजीनियर, AI सॉफ्टवेयर इंजीनियर, मीटिंग से कोड, आवाज से कोड, GitHub Copilot विकल्प, Cursor विकल्प, Devin विकल्प, Claude Code विकल्प",
      p: {
        "index": { t: "SIMY — मीटिंग से कोड जनरेट करने वाला AI", d: "स्वायत्त AI कोडिंग एजेंट जो मीटिंग को GitHub पुल रिक्वेस्ट में बदलता है। Copilot, Cursor, Devin और Claude Code का विकल्प।" },
        "pricing": { t: "मूल्य — SIMY | AI कोड जनरेशन $20/माह से", d: "मीटिंग से कोड जनरेट करने के लिए SIMY की कीमत।" },
        "compare": { t: "SIMY vs Copilot, Cursor, Devin, Claude Code तुलना", d: "SIMY बनाम GitHub Copilot, Cursor, Devin और Claude Code।" },
        "how-it-works": { t: "यह कैसे काम करता है — SIMY | 4 चरणों में मीटिंग से कोड", d: "देखें कि SIMY 4 चरणों में मीटिंग को GitHub पुल रिक्वेस्ट में कैसे बदलता है।" },
        "contact": { t: "डेमो अनुरोध — SIMY | AI कोड जनरेशन", d: "SIMY डेमो का अनुरोध करें।" },
        "integrations": { t: "एकीकरण — SIMY | GitHub, Slack, Zoom, Google Workspace", d: "SIMY को GitHub, Slack, Zoom और Google Workspace से कनेक्ट करें।" },
        "security": { t: "सुरक्षा — SIMY | एंटरप्राइज AI कोडिंग, HIPAA और SOC2", d: "HIPAA और SOC2 के साथ एंटरप्राइज-ग्रेड AI कोड जनरेशन।" },
        "about": { t: "AwakApp Inc. के बारे में — SIMY निर्माता", d: "AwakApp Inc., SIMY के पीछे की कंपनी।" }
      }
    },
    "te": {
      kw: "AI కోడ్ జనరేషన్, AI కోడింగ్ ఏజెంట్, సమస్య పరిష్కార AI ఏజెంట్, స్వయంప్రతిపత్తి AI ఇంజనీర్, AI సాఫ్ట్‌వేర్ ఇంజనీర్, మీటింగ్ నుండి కోడ్, వాయిస్ నుండి కోడ్, GitHub Copilot ప్రత్యామ్నాయం, Cursor ప్రత్యామ్నాయం, Devin ప్రత్యామ్నాయం, Claude Code ప్రత్యామ్నాయం",
      p: {
        "index": { t: "SIMY — మీటింగ్‌ల నుండి కోడ్ ఉత్పత్తి చేసే AI", d: "మీటింగ్‌లను GitHub పుల్ రిక్వెస్ట్‌లుగా మార్చే స్వయంప్రతిపత్తి AI కోడింగ్ ఏజెంట్." },
        "pricing": { t: "ధర — SIMY | AI కోడ్ జనరేషన్ $20/నెలకు", d: "మీటింగ్‌ల నుండి కోడ్ కోసం SIMY ధర." },
        "compare": { t: "SIMY vs Copilot, Cursor, Devin, Claude Code పోలిక", d: "SIMY vs GitHub Copilot, Cursor, Devin, Claude Code." },
        "how-it-works": { t: "ఎలా పనిచేస్తుంది — SIMY | 4 దశల్లో", d: "SIMY మీటింగ్‌లను 4 దశల్లో GitHub పుల్ రిక్వెస్ట్‌లుగా మారుస్తుంది." },
        "contact": { t: "డెమో అభ్యర్థన — SIMY", d: "SIMY డెమో అభ్యర్థించండి." },
        "integrations": { t: "ఇంటిగ్రేషన్‌లు — SIMY | GitHub, Slack, Zoom", d: "SIMYను GitHub, Slack, Zoom, Google Workspaceతో కనెక్ట్ చేయండి." },
        "security": { t: "భద్రత — SIMY | HIPAA & SOC2", d: "HIPAA మరియు SOC2తో ఎంటర్‌ప్రైజ్ AI." },
        "about": { t: "AwakApp Inc. గురించి", d: "AwakApp Inc., SIMY వెనుక ఉన్న సంస్థ." }
      }
    },
    "kn": {
      kw: "AI ಕೋಡ್ ಜನರೇಶನ್, AI ಕೋಡಿಂಗ್ ಏಜೆಂಟ್, ಸಮಸ್ಯೆ ಪರಿಹಾರ AI ಏಜೆಂಟ್, ಸ್ವಾಯತ್ತ AI ಇಂಜಿನಿಯರ್, AI ಸಾಫ್ಟ್‌ವೇರ್ ಎಂಜಿನಿಯರ್, ಮೀಟಿಂಗ್‌ನಿಂದ ಕೋಡ್, ಧ್ವನಿಯಿಂದ ಕೋಡ್, GitHub Copilot ಪರ್ಯಾಯ, Cursor ಪರ್ಯಾಯ, Devin ಪರ್ಯಾಯ, Claude Code ಪರ್ಯಾಯ",
      p: {
        "index": { t: "SIMY — ಮೀಟಿಂಗ್‌ಗಳಿಂದ ಕೋಡ್ ರಚಿಸುವ AI", d: "ಮೀಟಿಂಗ್‌ಗಳನ್ನು GitHub ಪುಲ್ ರಿಕ್ವೆಸ್ಟ್‌ಗಳಾಗಿ ಪರಿವರ್ತಿಸುವ ಸ್ವಾಯತ್ತ AI ಕೋಡಿಂಗ್ ಏಜೆಂಟ್." },
        "pricing": { t: "ಬೆಲೆ — SIMY | AI ಕೋಡ್ ರಚನೆ $20/ತಿಂಗಳಿಂದ", d: "ಮೀಟಿಂಗ್‌ಗಳಿಂದ ಕೋಡ್ ರಚನೆಗೆ SIMY ಬೆಲೆ." },
        "compare": { t: "SIMY vs Copilot, Cursor, Devin, Claude Code", d: "SIMY vs GitHub Copilot, Cursor, Devin, Claude Code." },
        "how-it-works": { t: "ಹೇಗೆ ಕಾರ್ಯನಿರ್ವಹಿಸುತ್ತದೆ — SIMY", d: "SIMY ಮೀಟಿಂಗ್‌ಗಳನ್ನು 4 ಹಂತಗಳಲ್ಲಿ GitHub ಪುಲ್ ರಿಕ್ವೆಸ್ಟ್‌ಗಳಾಗಿ ಮಾರ್ಪಡಿಸುತ್ತದೆ." },
        "contact": { t: "ಡೆಮೊ ವಿನಂತಿ — SIMY", d: "SIMY ಡೆಮೊಗೆ ವಿನಂತಿಸಿ." },
        "integrations": { t: "ಸಂಯೋಜನೆ — SIMY | GitHub, Slack, Zoom", d: "SIMY ಅನ್ನು GitHub, Slack, Zoom, Google Workspace ಗೆ ಸಂಪರ್ಕಿಸಿ." },
        "security": { t: "ಭದ್ರತೆ — SIMY | HIPAA & SOC2", d: "HIPAA ಮತ್ತು SOC2ನೊಂದಿಗೆ ಎಂಟರ್‌ಪ್ರೈಸ್ AI." },
        "about": { t: "AwakApp Inc. ಬಗ್ಗೆ", d: "AwakApp Inc., SIMY ಹಿಂದಿನ ಕಂಪನಿ." }
      }
    },
    "ko": {
      kw: "AI 코드 생성, AI 코딩 에이전트, 문제 해결 AI 에이전트, 버그 수정 AI, 자율 AI 엔지니어, AI 소프트웨어 엔지니어, 회의에서 코드로, 음성에서 코드로, GitHub Copilot 대안, Cursor 대안, Devin 대안, Claude Code 대안",
      p: {
        "index": { t: "SIMY — 회의에서 코드를 생성하는 AI 엔지니어", d: "회의를 GitHub 풀 리퀘스트로 변환하는 자율 AI 코딩 에이전트. Copilot, Cursor, Devin, Claude Code의 대안." },
        "pricing": { t: "요금 — SIMY | AI 코드 생성 플랜 월 $20부터", d: "회의에서 코드를 생성하는 SIMY 요금." },
        "compare": { t: "SIMY vs Copilot, Cursor, Devin, Claude Code 비교", d: "SIMY와 GitHub Copilot, Cursor, Devin, Claude Code 비교." },
        "how-it-works": { t: "사용 방법 — SIMY | 4단계로 회의에서 코드", d: "SIMY가 4단계로 회의를 GitHub 풀 리퀘스트로 변환합니다." },
        "contact": { t: "데모 요청 — SIMY | AI 코드 생성", d: "SIMY 데모를 요청하세요." },
        "integrations": { t: "통합 — SIMY | GitHub, Slack, Zoom, Google Workspace", d: "SIMY를 GitHub, Slack, Zoom, Google Workspace와 연결하세요." },
        "security": { t: "보안 — SIMY | HIPAA & SOC2", d: "HIPAA 및 SOC2 로드맵을 갖춘 엔터프라이즈급 AI." },
        "about": { t: "AwakApp Inc. 소개", d: "SIMY의 개발사 AwakApp Inc." }
      }
    },
    "vi": {
      kw: "tạo mã AI, tác nhân lập trình AI, tác nhân AI giải quyết vấn đề, kỹ sư AI tự động, kỹ sư phần mềm AI, từ cuộc họp sang mã, từ giọng nói sang mã, thay thế GitHub Copilot, thay thế Cursor, thay thế Devin, thay thế Claude Code",
      p: {
        "index": { t: "SIMY — AI tạo mã từ các cuộc họp của bạn", d: "Tác nhân lập trình AI tự động biến cuộc họp thành pull request GitHub. Thay thế cho Copilot, Cursor, Devin và Claude Code." },
        "pricing": { t: "Giá — SIMY | Gói tạo mã AI từ 20$/tháng", d: "Giá SIMY để tạo mã từ cuộc họp." },
        "compare": { t: "So sánh SIMY vs Copilot, Cursor, Devin, Claude Code", d: "SIMY so với GitHub Copilot, Cursor, Devin, Claude Code." },
        "how-it-works": { t: "Cách hoạt động — SIMY | Từ cuộc họp đến mã trong 4 bước", d: "Xem SIMY biến cuộc họp thành pull request GitHub trong 4 bước." },
        "contact": { t: "Yêu cầu demo — SIMY | Nền tảng tạo mã AI", d: "Yêu cầu demo SIMY." },
        "integrations": { t: "Tích hợp — SIMY | GitHub, Slack, Zoom", d: "Kết nối SIMY với GitHub, Slack, Zoom và Google Workspace." },
        "security": { t: "Bảo mật — SIMY | HIPAA & SOC2", d: "Tạo mã AI cấp doanh nghiệp với lộ trình HIPAA và SOC2." },
        "about": { t: "Về AwakApp Inc.", d: "AwakApp Inc., công ty đứng sau SIMY." }
      }
    },
    "th": {
      kw: "การสร้างโค้ด AI, เอเจนต์เขียนโค้ด AI, เอเจนต์ AI แก้ปัญหา, วิศวกร AI อัตโนมัติ, วิศวกรซอฟต์แวร์ AI, จากการประชุมเป็นโค้ด, จากเสียงเป็นโค้ด, ทางเลือก GitHub Copilot, ทางเลือก Cursor, ทางเลือก Devin, ทางเลือก Claude Code",
      p: {
        "index": { t: "SIMY — AI ที่สร้างโค้ดจากการประชุมของคุณ", d: "เอเจนต์เขียนโค้ด AI อัตโนมัติที่เปลี่ยนการประชุมเป็น pull request บน GitHub ทางเลือกแทน Copilot, Cursor, Devin, Claude Code" },
        "pricing": { t: "ราคา — SIMY | แผนสร้างโค้ด AI เริ่มต้น $20/เดือน", d: "ราคา SIMY สำหรับการสร้างโค้ดจากการประชุม" },
        "compare": { t: "เปรียบเทียบ SIMY vs Copilot, Cursor, Devin, Claude Code", d: "SIMY เทียบกับ GitHub Copilot, Cursor, Devin, Claude Code" },
        "how-it-works": { t: "วิธีการทำงาน — SIMY | 4 ขั้นตอน", d: "ดูว่า SIMY เปลี่ยนการประชุมเป็น pull request GitHub ใน 4 ขั้นตอนอย่างไร" },
        "contact": { t: "ขอเดโม — SIMY", d: "ขอเดโม SIMY" },
        "integrations": { t: "การผสานการทำงาน — SIMY | GitHub, Slack, Zoom", d: "เชื่อมต่อ SIMY กับ GitHub, Slack, Zoom และ Google Workspace" },
        "security": { t: "ความปลอดภัย — SIMY | HIPAA & SOC2", d: "การสร้างโค้ด AI ระดับองค์กรพร้อม HIPAA และ SOC2 roadmap" },
        "about": { t: "เกี่ยวกับ AwakApp Inc.", d: "AwakApp Inc. บริษัทผู้สร้าง SIMY" }
      }
    },
    "id": {
      kw: "pembuatan kode AI, agen coding AI, agen AI pemecah masalah, insinyur AI otonom, insinyur perangkat lunak AI, dari rapat ke kode, dari suara ke kode, alternatif GitHub Copilot, alternatif Cursor, alternatif Devin, alternatif Claude Code",
      p: {
        "index": { t: "SIMY — AI yang membuat kode dari rapat Anda", d: "Agen coding AI otonom yang mengubah rapat menjadi pull request GitHub. Alternatif untuk Copilot, Cursor, Devin, Claude Code." },
        "pricing": { t: "Harga — SIMY | Paket pembuatan kode AI mulai $20/bulan", d: "Harga SIMY untuk pembuatan kode dari rapat." },
        "compare": { t: "Perbandingan SIMY vs Copilot, Cursor, Devin, Claude Code", d: "SIMY vs GitHub Copilot, Cursor, Devin, Claude Code." },
        "how-it-works": { t: "Cara kerja — SIMY | Dari rapat ke kode dalam 4 langkah", d: "Lihat bagaimana SIMY mengubah rapat menjadi pull request GitHub dalam 4 langkah." },
        "contact": { t: "Minta demo — SIMY | Platform pembuatan kode AI", d: "Minta demo SIMY." },
        "integrations": { t: "Integrasi — SIMY | GitHub, Slack, Zoom, Google Workspace", d: "Hubungkan SIMY dengan GitHub, Slack, Zoom, dan Google Workspace." },
        "security": { t: "Keamanan — SIMY | HIPAA & SOC2", d: "Pembuatan kode AI dengan roadmap HIPAA dan SOC2." },
        "about": { t: "Tentang AwakApp Inc.", d: "AwakApp Inc., perusahaan di balik SIMY." }
      }
    },
    "ru": {
      kw: "ИИ генерация кода, ИИ агент программирования, ИИ агент решения задач, автономный ИИ инженер, ИИ инженер-программист, от встречи к коду, от голоса к коду, альтернатива GitHub Copilot, альтернатива Cursor, альтернатива Devin, альтернатива Claude Code",
      p: {
        "index": { t: "SIMY — ИИ генерирует код из ваших встреч", d: "Автономный ИИ-агент программирования, превращающий встречи в GitHub pull request. Альтернатива Copilot, Cursor, Devin, Claude Code." },
        "pricing": { t: "Цены — SIMY | Планы генерации кода ИИ от $20/мес", d: "Цены SIMY на генерацию кода из встреч." },
        "compare": { t: "SIMY vs Copilot, Cursor, Devin, Claude Code сравнение", d: "SIMY против GitHub Copilot, Cursor, Devin, Claude Code." },
        "how-it-works": { t: "Как работает SIMY — от встречи к коду за 4 шага", d: "Узнайте, как SIMY превращает встречи в GitHub pull request за 4 шага." },
        "contact": { t: "Запросить демо — SIMY | Платформа генерации кода", d: "Запросите демо SIMY." },
        "integrations": { t: "Интеграции — SIMY | GitHub, Slack, Zoom, Google Workspace", d: "Подключите SIMY к GitHub, Slack, Zoom и Google Workspace." },
        "security": { t: "Безопасность — SIMY | HIPAA & SOC2", d: "Корпоративная генерация кода ИИ с HIPAA и SOC2." },
        "about": { t: "О AwakApp Inc.", d: "AwakApp Inc., компания, стоящая за SIMY." }
      }
    },
    "pt-BR": {
      kw: "geração de código com IA, agente de codificação IA, agente IA de resolução de problemas, engenheiro IA autônomo, engenheiro de software IA, de reunião para código, de voz para código, alternativa ao GitHub Copilot, alternativa ao Cursor, alternativa ao Devin, alternativa ao Claude Code",
      p: {
        "index": { t: "SIMY — IA que gera código a partir de reuniões", d: "Agente de codificação IA autônomo que transforma reuniões em pull requests do GitHub. Alternativa ao Copilot, Cursor, Devin e Claude Code." },
        "pricing": { t: "Preços — SIMY | Geração de código IA a partir de $20/mês", d: "Preços SIMY para geração de código de reuniões." },
        "compare": { t: "Compare SIMY vs Copilot, Cursor, Devin e Claude Code", d: "SIMY vs GitHub Copilot, Cursor, Devin e Claude Code." },
        "how-it-works": { t: "Como funciona — SIMY | Da reunião ao código em 4 passos", d: "Veja como o SIMY transforma reuniões em pull requests do GitHub em 4 passos." },
        "contact": { t: "Solicitar demo — SIMY", d: "Solicite uma demo SIMY." },
        "integrations": { t: "Integrações — SIMY | GitHub, Slack, Zoom, Google Workspace", d: "Conecte o SIMY ao GitHub, Slack, Zoom e Google Workspace." },
        "security": { t: "Segurança — SIMY | HIPAA & SOC2", d: "Geração de código IA empresarial com roadmap HIPAA e SOC2." },
        "about": { t: "Sobre a AwakApp Inc.", d: "AwakApp Inc., a empresa por trás do SIMY." }
      }
    }
  };

  function pageKey() {
    var p = location.pathname;
    if (p === '/' || p === '') return 'index';
    var m = p.match(/\/([^/]+?)(?:\.html)?$/);
    return m ? m[1] : 'index';
  }

  function setMetaTag(name, content, attr) {
    if (!content) return;
    attr = attr || 'name';
    var sel = 'meta[' + attr + '="' + name + '"]';
    var el = document.querySelector(sel);
    if (!el) {
      el = document.createElement('meta');
      el.setAttribute(attr, name);
      document.head.appendChild(el);
    }
    el.setAttribute('content', content);
  }

  function applySEO(lang) {
    var data = SEO[lang];
    if (!data) return;
    var key = pageKey();
    var page = data.p && data.p[key];
    if (page) {
      if (page.t) {
        document.title = page.t;
        setMetaTag('og:title', page.t, 'property');
        setMetaTag('twitter:title', page.t);
      }
      if (page.d) {
        setMetaTag('description', page.d);
        setMetaTag('og:description', page.d, 'property');
        setMetaTag('twitter:description', page.d);
      }
    }
    if (data.kw) setMetaTag('keywords', data.kw);
  }

  /* ── Capture original (English) DOM content on first apply ──
     Used as a fallback when the target language dict is missing a key
     (e.g. because the browser has a stale cached JSON from before a
     translation update, or because the key genuinely isn't translated
     yet). Without this, missing keys leave whatever text the cell
     previously held — causing "sticky" Japanese ghosts when switching
     from ja to another language. */
  var ORIG_CAPTURED = false;
  function captureOriginals() {
    if (ORIG_CAPTURED) return;
    ORIG_CAPTURED = true;
    var els = document.querySelectorAll('[data-i18n]');
    for (var i = 0; i < els.length; i++) {
      els[i].setAttribute('data-i18n-orig', els[i].textContent);
    }
    var htmlEls = document.querySelectorAll('[data-i18n-html]');
    for (var j = 0; j < htmlEls.length; j++) {
      htmlEls[j].setAttribute('data-i18n-orig-html', htmlEls[j].innerHTML);
    }
    var phEls = document.querySelectorAll('[data-i18n-placeholder]');
    for (var k = 0; k < phEls.length; k++) {
      phEls[k].setAttribute('data-i18n-orig-placeholder', phEls[k].getAttribute('placeholder') || '');
    }
  }

  /* ── Home #root bridge: load per-language dictionary ─────────── */
  function loadHomeDom(lang, cb) {
    if (HOME_DOM_CACHE[lang]) return cb(HOME_DOM_CACHE[lang]);
    // English is identity — nothing to load
    if (lang === DEFAULT) {
      HOME_DOM_CACHE[lang] = {};
      return cb(HOME_DOM_CACHE[lang]);
    }
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/lang/home-dom/' + lang + '.json', true);
    xhr.onreadystatechange = function () {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          try { HOME_DOM_CACHE[lang] = JSON.parse(xhr.responseText); }
          catch (e) { HOME_DOM_CACHE[lang] = {}; }
        } else { HOME_DOM_CACHE[lang] = {}; }
        cb(HOME_DOM_CACHE[lang]);
      }
    };
    xhr.send();
  }

  /* ── Home #root bridge: walk text nodes, capture originals ─── */
  function captureRootOriginals(root) {
    if (!ROOT_NODE_MAP) ROOT_NODE_MAP = new WeakMap();
    // Track captured nodes so subsequent walks only pick up newly-added ones.
    // WeakMap has no size, so we also keep a parallel Set of nodes for iteration.
    if (!ROOT_NODE_MAP._list) ROOT_NODE_MAP._list = [];
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var n;
    while ((n = walker.nextNode())) {
      if (ROOT_NODE_MAP.has(n)) continue;
      var raw = n.nodeValue;
      if (!raw) continue;
      var trimmed = raw.replace(/\s+/g, ' ').trim();
      if (!trimmed) continue;
      // Skip pure numeric / symbolic content — never worth translating
      if (/^[\s\d.,:%×·$/()\-+]*$/.test(trimmed)) continue;
      // Skip nodes inside any element marked data-simy-no-translate —
      // e.g. the Screen Studio block, which owns its own text updates.
      var p = n.parentNode;
      var skip = false;
      while (p && p !== root) {
        if (p.nodeType === 1 && p.hasAttribute && p.hasAttribute('data-simy-no-translate')) {
          skip = true;
          break;
        }
        p = p.parentNode;
      }
      if (skip) continue;
      ROOT_NODE_MAP.set(n, trimmed);
      ROOT_NODE_MAP._list.push(n);
    }
  }

  /* ── Home #root bridge: apply current language to all text nodes ── */
  function applyRoot(langCode) {
    var root = document.getElementById('root');
    if (!root) return;
    captureRootOriginals(root);
    if (!ROOT_NODE_MAP || !ROOT_NODE_MAP._list) return;
    // Ensure the language dict is loaded — lazy-load on demand if not.
    if (!HOME_DOM_CACHE[langCode] && langCode !== DEFAULT) {
      loadHomeDom(langCode, function () { applyRoot(langCode); });
      return;
    }
    var dict = HOME_DOM_CACHE[langCode] || {};
    ROOT_APPLYING = true;
    try {
      var list = ROOT_NODE_MAP._list;
      // Compact dead nodes occasionally
      var alive = [];
      for (var i = 0; i < list.length; i++) {
        var node = list[i];
        if (!node || !node.isConnected) continue;
        alive.push(node);
        var orig = ROOT_NODE_MAP.get(node);
        if (!orig) continue;
        var translated = dict[orig];
        var target = (translated !== undefined && translated !== null && translated !== '')
          ? translated
          : orig; // EN or missing key → restore original
        var raw = node.nodeValue || '';
        var mLead = raw.match(/^\s*/);
        var mTail = raw.match(/\s*$/);
        var next = (mLead ? mLead[0] : '') + target + (mTail ? mTail[0] : '');
        if (node.nodeValue !== next) node.nodeValue = next;
      }
      ROOT_NODE_MAP._list = alive;
      // Inject the Screen Studio animated demo above the "What is SIMY" section.
      // Idempotent and guarded by ROOT_APPLYING so the observer ignores it.
      injectScreenStudio(root);
    } finally {
      ROOT_APPLYING = false;
    }
  }

  /* ── Home #root bridge: inject the Screen Studio animated demo
        above the "03 / What is SIMY" section. Idempotent — safe to
        call on every applyRoot() pass. Auto-removes the older static
        dashboard <figure> from PR #27 if it is still present. ───── */
  function injectScreenStudio(root) {
    if (!root) return;
    if (document.getElementById('simy-screen-studio')) return;
    if (!ROOT_NODE_MAP || !ROOT_NODE_MAP._list) return;

    var anchor = null;
    var list = ROOT_NODE_MAP._list;
    for (var i = 0; i < list.length; i++) {
      var node = list[i];
      if (!node || !node.isConnected) continue;
      var orig = ROOT_NODE_MAP.get(node);
      if (orig && orig.indexOf('03 / What is SIMY') === 0) {
        anchor = node;
        break;
      }
    }
    if (!anchor) return;

    // Walk up to the nearest <section> ancestor — that's the What is SIMY block.
    var section = anchor.parentNode;
    while (section && section !== root && section.tagName !== 'SECTION') {
      section = section.parentNode;
    }
    if (!section || section === root || !section.parentNode) return;

    // If a previous static figure exists from the earlier iteration, remove it.
    var oldFig = document.getElementById('simy-dashboard-visual');
    if (oldFig && oldFig.parentNode) oldFig.parentNode.removeChild(oldFig);

    var wrap = document.createElement('section');
    wrap.id = 'simy-screen-studio';
    wrap.className = 'simy-ss-section';
    // Tell captureRootOriginals to skip all text nodes inside the demo so
    // the MutationObserver/bridge can't clobber our caption/tick/button text.
    wrap.setAttribute('data-simy-no-translate', '1');
    wrap.innerHTML = [
      '<div class="simy-ss-container">',
        '<div class="simy-ss-eyebrow">',
          '<span class="simy-ss-eyebrow-dot"></span>',
          'WATCH SIMY IN 12 SECONDS',
        '</div>',
        '<h2 class="simy-ss-title">From meeting to shipped PR.</h2>',
        '<p class="simy-ss-kicker">Four scenes, one unbroken take through the real SIMY desktop app.</p>',
        '<div class="simy-ss-wrap">',
          '<div class="simy-ss-browser">',
            '<div class="simy-ss-chrome">',
              '<div class="simy-ss-dots">',
                '<span class="simy-ss-dot" style="background:#ff5f57"></span>',
                '<span class="simy-ss-dot" style="background:#febc2e"></span>',
                '<span class="simy-ss-dot" style="background:#28c840"></span>',
              '</div>',
              '<div class="simy-ss-addr">',
                '<span class="simy-ss-addr-inner">',
                  '<span>\u{1F512}</span>',
                  '<span>app.simy.one / home</span>',
                '</span>',
              '</div>',
              '<span class="simy-ss-rec">',
                '<span class="simy-ss-rec-dot"></span>',
                'REC \u00b7 LIVE',
              '</span>',
            '</div>',
            '<div class="simy-ss-viewport">',
              '<video class="simy-ss-video" data-simy-video ',
                'src="/assets/demo.mp4" ',
                'poster="/assets/demo-shots/01-twin.png" ',
                'autoplay muted loop playsinline preload="metadata" ',
                'aria-label="SIMY click-through demo"></video>',
            '</div>',
          '</div>',
          '<div class="simy-ss-rail"><div class="simy-ss-rail-fill" data-simy-rail></div></div>',
          '<div class="simy-ss-ticks" data-simy-ticks>',
            '<button class="simy-ss-tick" data-simy-idx="0" type="button">01 \u00b7 Twin</button>',
            '<button class="simy-ss-tick" data-simy-idx="1" type="button">02 \u00b7 Meeting</button>',
            '<button class="simy-ss-tick" data-simy-idx="2" type="button">03 \u00b7 Actions</button>',
            '<button class="simy-ss-tick" data-simy-idx="3" type="button">04 \u00b7 Dashboard</button>',
          '</div>',
          '<div class="simy-ss-caption">',
            '<div class="simy-ss-caption-main" data-simy-cap-main></div>',
            '<div class="simy-ss-caption-sub" data-simy-cap-sub></div>',
          '</div>',
          '<div class="simy-ss-controls">',
            '<button type="button" class="simy-ss-btn" data-simy-pause>Pause</button>',
            '<button type="button" class="simy-ss-btn" data-simy-replay>Replay</button>',
          '</div>',
        '</div>',
      '</div>'
    ].join('');

    section.parentNode.insertBefore(wrap, section);
    initScreenStudioAnimation(wrap);
  }

  /* ── Screen Studio driver: a single recorded <video> that walks through
        Twin → Meetings → Actions → Dashboard as Alex clicks each sidebar
        item. The caption, tick highlight, and progress rail are all driven
        from the video's currentTime so they stay in lockstep even if the
        user scrubs or the video loops. ─────────────────────────────── */
  function initScreenStudioAnimation(wrap) {
    // Scene start offsets in the trimmed demo.mp4 (milliseconds). Must
    // match the output of /tmp/simy-capture/record.mjs after ffmpeg trim.
    var SCENES = [
      { at: 0,     main: 'Alex opens the Twin before the planning session.',
        sub:  'Product Manager at a 150-person tech company. The Twin already knows what needs decisions today.' },
      { at: 4475,  main: 'Planning session ends \u2014 every decision captured.',
        sub:  'SIMY generates a structured roadmap, assigns owners, and sends summaries automatically.' },
      { at: 8647,  main: 'Roadmap items become assigned, ready-to-review tickets.',
        sub:  'Hours of turning discussion into a roadmap \u2014 gone.' },
      { at: 12813, main: 'Growth Dashboard: North Star 1,247 (+12.4%) \u00b7 Retention 71%.',
        sub:  'Roadmap ready before the next standup.' }
    ];

    var video    = wrap.querySelector('[data-simy-video]');
    var rail     = wrap.querySelector('[data-simy-rail]');
    var capMain  = wrap.querySelector('[data-simy-cap-main]');
    var capSub   = wrap.querySelector('[data-simy-cap-sub]');
    var ticks    = wrap.querySelectorAll('[data-simy-ticks] .simy-ss-tick');
    var pauseBtn = wrap.querySelector('[data-simy-pause]');
    var replayBtn= wrap.querySelector('[data-simy-replay]');
    if (!video) return;

    var currentIndex = -1;
    var reduced = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

    function sceneIndexForMs(ms) {
      var i = 0;
      for (var k = 0; k < SCENES.length; k++) {
        if (ms + 40 >= SCENES[k].at) i = k;
      }
      return i;
    }

    function renderScene(i) {
      if (i === currentIndex) return;
      currentIndex = i;
      var s = SCENES[i];
      capMain.textContent = s.main;
      capSub.textContent  = s.sub;
      for (var t = 0; t < ticks.length; t++) {
        ticks[t].setAttribute('data-active', t === i ? 'true' : 'false');
      }
    }

    function onTimeUpdate() {
      if (!wrap.isConnected) return;
      var ms  = (video.currentTime || 0) * 1000;
      var dur = (video.duration && isFinite(video.duration)) ? video.duration : 16.4;
      var idx = sceneIndexForMs(ms);
      if (idx !== currentIndex) renderScene(idx);
      rail.style.transform = 'scaleX(' + Math.min(1, (video.currentTime || 0) / dur) + ')';
    }

    function seekToScene(i) {
      i = ((i % SCENES.length) + SCENES.length) % SCENES.length;
      try { video.currentTime = (SCENES[i].at + 50) / 1000; } catch (e) {}
      renderScene(i);
      if (video.paused) {
        video.play().catch(function () {});
      }
    }

    // Wire up ticks (click to jump scene)
    for (var k = 0; k < ticks.length; k++) {
      (function (btn, idx) {
        btn.addEventListener('click', function () { seekToScene(idx); });
      })(ticks[k], k);
    }

    pauseBtn.addEventListener('click', function () {
      if (video.paused) {
        video.play().catch(function () {});
        pauseBtn.textContent = 'Pause';
      } else {
        video.pause();
        pauseBtn.textContent = 'Play';
      }
    });
    replayBtn.addEventListener('click', function () { seekToScene(0); });

    video.addEventListener('timeupdate', onTimeUpdate);
    video.addEventListener('loadedmetadata', onTimeUpdate);
    video.addEventListener('seeked', onTimeUpdate);

    // Respect prefers-reduced-motion: hold on the first scene.
    if (reduced) {
      try { video.pause(); } catch (e) {}
      pauseBtn.textContent = 'Play';
    }

    // Initial state — prime caption + tick without waiting for timeupdate.
    renderScene(0);
    rail.style.transform = 'scaleX(0)';
  }

  /* ── Screen Studio: inject its scoped CSS once at bridge init. ── */
  function injectScreenStudioStyles() {
    if (document.getElementById('simy-screen-studio-styles')) return;
    var style = document.createElement('style');
    style.id = 'simy-screen-studio-styles';
    style.textContent = [
      '.simy-ss-section{margin:64px auto 80px;padding:0 24px;}',
      '.simy-ss-container{max-width:1180px;margin:0 auto;}',
      '.simy-ss-eyebrow{display:inline-flex;align-items:center;gap:8px;font-family:"Geist Mono",ui-monospace,monospace;font-size:11px;text-transform:uppercase;letter-spacing:.18em;color:#6b6b68;margin-bottom:12px;}',
      '.simy-ss-eyebrow-dot{width:6px;height:6px;border-radius:999px;background:#1d4ed8;display:inline-block;}',
      '.simy-ss-title{font-size:clamp(28px,4vw,48px);font-weight:600;letter-spacing:-.02em;margin:0 0 10px;line-height:1.1;}',
      '.simy-ss-kicker{font-size:16px;color:#6b6b68;max-width:560px;margin:0 0 28px;line-height:1.5;}',
      '.simy-ss-wrap{background:radial-gradient(ellipse at top,rgba(210,220,255,.55) 0%,transparent 60%),linear-gradient(180deg,#f2f3ff 0%,#f9f9f6 100%);border-radius:28px;padding:28px;box-shadow:inset 0 1px 0 rgba(0,0,0,.04),0 40px 80px -40px rgba(20,20,40,.25);}',
      '.simy-ss-browser{background:#111113;border-radius:18px;overflow:hidden;box-shadow:0 30px 80px -30px rgba(0,0,0,.55);border:1px solid rgba(255,255,255,.06);}',
      '.simy-ss-chrome{display:flex;align-items:center;gap:12px;padding:10px 14px;background:linear-gradient(180deg,#1a1a1d 0%,#111113 100%);border-bottom:1px solid rgba(255,255,255,.05);}',
      '.simy-ss-dots{display:flex;gap:6px;}',
      '.simy-ss-dot{width:11px;height:11px;border-radius:999px;display:inline-block;}',
      '.simy-ss-addr{flex:1;display:flex;align-items:center;justify-content:center;}',
      '.simy-ss-addr-inner{background:rgba(255,255,255,.07);color:rgba(255,255,255,.72);font-size:12px;padding:5px 12px;border-radius:999px;font-family:"Geist Mono",ui-monospace,monospace;display:inline-flex;align-items:center;gap:6px;}',
      '.simy-ss-rec{display:inline-flex;align-items:center;gap:6px;font-size:11px;color:#ff4d4d;font-family:"Geist Mono",ui-monospace,monospace;letter-spacing:.04em;}',
      '.simy-ss-rec-dot{width:8px;height:8px;border-radius:999px;background:#ff4d4d;animation:simy-ss-pulse 1.6s ease-out infinite;}',
      '@keyframes simy-ss-pulse{0%{box-shadow:0 0 0 0 rgba(255,77,77,.6);}70%{box-shadow:0 0 0 10px rgba(255,77,77,0);}100%{box-shadow:0 0 0 0 rgba(255,77,77,0);}}',
      '.simy-ss-viewport{position:relative;aspect-ratio:16/10;background:#0a0a0c;overflow:hidden;}',
      '.simy-ss-video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center top;background:#0a0a0c;display:block;}',
      '.simy-ss-rail{margin-top:18px;height:4px;background:rgba(0,0,0,.08);border-radius:999px;overflow:hidden;}',
      '.simy-ss-rail-fill{height:100%;width:100%;background:linear-gradient(90deg,#1d4ed8 0%,#7c3aed 100%);transform:scaleX(0);transform-origin:left center;transition:transform .05s linear;}',
      '.simy-ss-ticks{margin-top:14px;display:grid;grid-template-columns:repeat(4,1fr);gap:10px;}',
      '.simy-ss-tick{text-align:left;font-family:"Geist Mono",ui-monospace,monospace;font-size:11px;color:#6b6b68;padding:8px 12px;border-radius:10px;border:1px solid rgba(0,0,0,.06);background:rgba(255,255,255,.6);transition:all .25s ease;cursor:pointer;}',
      '.simy-ss-tick[data-active="true"]{color:#0a0a0a;background:#fff;border-color:#1d4ed8;box-shadow:0 0 0 3px rgba(29,78,216,.25);}',
      '.simy-ss-caption{margin-top:18px;padding:16px 20px;background:#0a0a0c;color:#f9f9f6;border-radius:14px;min-height:64px;}',
      '.simy-ss-caption-main{font-size:16px;font-weight:600;line-height:1.4;}',
      '.simy-ss-caption-sub{font-size:13px;color:rgba(255,255,255,.6);line-height:1.5;margin-top:4px;}',
      '.simy-ss-controls{margin-top:14px;display:flex;gap:10px;justify-content:flex-end;}',
      '.simy-ss-btn{font-family:"Geist Mono",ui-monospace,monospace;font-size:11px;padding:6px 12px;border-radius:999px;border:1px solid rgba(0,0,0,.1);background:#fff;color:#0a0a0a;cursor:pointer;transition:all .15s ease;}',
      '.simy-ss-btn:hover{border-color:#1d4ed8;color:#1d4ed8;}',
      '@media (max-width:768px){',
        '.simy-ss-section{padding:0 16px;margin:40px auto 56px;}',
        '.simy-ss-wrap{padding:16px;border-radius:20px;}',
        '.simy-ss-ticks{grid-template-columns:repeat(2,1fr);}',
        '.simy-ss-title{font-size:28px;}',
      '}'
    ].join('');
    document.head.appendChild(style);
  }

  /* ── Home #root bridge: MutationObserver re-applies on React renders ── */
  function setupRootObserver() {
    if (ROOT_OBSERVER) return;
    var root = document.getElementById('root');
    if (!root) return;
    ROOT_OBSERVER = new MutationObserver(function (mutations) {
      if (ROOT_APPLYING) return;
      // If every mutation is just a characterData change caused by us, skip
      if (ROOT_DEBOUNCE) clearTimeout(ROOT_DEBOUNCE);
      ROOT_DEBOUNCE = setTimeout(function () {
        applyRoot(CURRENT_LANG);
      }, 30);
    });
    ROOT_OBSERVER.observe(root, {
      childList: true,
      subtree: true,
      characterData: true
    });
  }

  /* ── Home #root bridge: one-time kickoff from init ──────────── */
  function initHomeDomBridge() {
    // Only run on pages that have a React SPA root (#root)
    if (!document.getElementById('root')) return;
    injectScreenStudioStyles();
    loadHomeDom(CURRENT_LANG, function () {
      applyRoot(CURRENT_LANG);
      setupRootObserver();
      // React may still be mounting. Poll for ~6s to catch late renders.
      var tries = 0;
      var poll = setInterval(function () {
        tries++;
        var r = document.getElementById('root');
        if (r && r.childNodes && r.childNodes.length > 0) {
          applyRoot(CURRENT_LANG);
          setupRootObserver();
        }
        if (tries > 60) clearInterval(poll); // stop after ~6s
      }, 100);
    });
  }

  /* ── Apply translations to DOM ─────────────────────────────── */
  function apply(dict) {
    var meta = dict._meta || {};

    // Capture baseline English text from the static HTML on first run,
    // BEFORE any translation has been applied. Subsequent apply() calls
    // use these as a fallback for missing keys.
    captureOriginals();

    // Track the current language so the Home #root bridge and its
    // MutationObserver know what language to (re-)apply on React renders.
    CURRENT_LANG = meta.code || DEFAULT;

    // Set html lang & dir
    document.documentElement.lang = meta.code || DEFAULT;
    document.documentElement.dir = meta.dir || 'ltr';

    // Inject localized SEO (title, description, keywords, OG, Twitter)
    applySEO(meta.code || DEFAULT);

    // Text-only replacements — fall back to captured original if dict
    // lacks the key so we never leave a stale translation behind.
    var els = document.querySelectorAll('[data-i18n]');
    for (var i = 0; i < els.length; i++) {
      var key = els[i].getAttribute('data-i18n');
      var val = dict[key];
      if (val === undefined) val = els[i].getAttribute('data-i18n-orig');
      if (val !== undefined && val !== null) {
        els[i].textContent = val;
      }
    }

    // HTML replacements (e.g. <br> tags)
    var htmlEls = document.querySelectorAll('[data-i18n-html]');
    for (var j = 0; j < htmlEls.length; j++) {
      var hkey = htmlEls[j].getAttribute('data-i18n-html');
      var hval = dict[hkey];
      if (hval === undefined) hval = htmlEls[j].getAttribute('data-i18n-orig-html');
      if (hval !== undefined && hval !== null) {
        htmlEls[j].innerHTML = hval;
      }
    }

    // Placeholder / aria-label
    var attrEls = document.querySelectorAll('[data-i18n-placeholder]');
    for (var k = 0; k < attrEls.length; k++) {
      var pkey = attrEls[k].getAttribute('data-i18n-placeholder');
      var pval = dict[pkey];
      if (pval === undefined) pval = attrEls[k].getAttribute('data-i18n-orig-placeholder');
      if (pval !== undefined && pval !== null) {
        attrEls[k].setAttribute('placeholder', pval);
      }
    }

    // Update active selector display
    var display = document.getElementById('langDisplay');
    if (display && meta.name) {
      display.textContent = meta.name;
    }

    // Press release: swap to the polished hand-written JA article when lang=ja,
    // otherwise show the canonical EN article (which /i18n.js translates via data-i18n
    // for all other supported languages).
    var prEn = document.getElementById('prEn');
    var prJa = document.getElementById('prJa');
    if (prEn && prJa) {
      var isJa = meta.code === 'ja';
      prEn.style.display = isJa ? 'none' : 'block';
      prJa.style.display = isJa ? 'block' : 'none';
    }

    // Apple App Store: use the JP storefront for Japanese, US storefront otherwise.
    var appStoreUrl = meta.code === 'ja'
      ? 'https://apps.apple.com/jp/app/simy-meetings-end-code-ships/id6745385262'
      : 'https://apps.apple.com/us/app/simy-meetings-end-code-ships/id6745385262';
    var appLinks = document.querySelectorAll('a[href*="apps.apple.com"]');
    for (var m = 0; m < appLinks.length; m++) { appLinks[m].href = appStoreUrl; }

    // Home (/) React SPA: re-apply #root translations on every apply() —
    // this handles both initial load and user-initiated language switches.
    if (document.getElementById('root')) {
      applyRoot(CURRENT_LANG);
    }
  }

  /* ── Language names for switcher ───────────────────────────── */
  var LANG_NAMES = {
    'en':      'English',
    'ja':      '日本語',
    'zh-Hans': '简体中文',
    'zh-Hant': '繁體中文',
    'fr':      'Français',
    'de':      'Deutsch',
    'es':      'Español',
    'ar':      'العربية',
    'it':      'Italiano',
    'hi':      'हिन्दी',
    'te':      'తెలుగు',
    'kn':      'ಕನ್ನಡ',
    'ko':      '한국어',
    'vi':      'Tiếng Việt',
    'th':      'ไทย',
    'id':      'Indonesia',
    'ru':      'Русский',
    'pt-BR':   'Português'
  };

  /* ── Language switcher ─────────────────────────────────────── */
  function buildSwitcher() {
    // Already injected (e.g. React re-render) — skip
    if (document.getElementById('langBtn')) return;

    // Find nav container: static pages use .nav-inner, React SPA uses nav > .container
    var navInner = document.querySelector('.nav-inner') || document.querySelector('nav > .container');
    if (!navInner) return;

    var wrapper = document.createElement('div');
    wrapper.className = 'lang-switcher';
    wrapper.innerHTML =
      '<button class="lang-btn" id="langBtn" aria-label="Change language">' +
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
          '<circle cx="12" cy="12" r="10"/>' +
          '<path d="M2 12h20"/>' +
          '<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>' +
        '</svg>' +
        '<span id="langDisplay">English</span>' +
      '</button>' +
      '<div class="lang-dropdown" id="langDropdown"></div>';

    // Insert before mobile menu button or at end
    var mobileBtn = navInner.querySelector('.mobile-menu-btn') || navInner.querySelector('button[aria-label="Menu"]');
    if (mobileBtn) {
      navInner.insertBefore(wrapper, mobileBtn);
    } else {
      navInner.appendChild(wrapper);
    }

    var dropdown = document.getElementById('langDropdown');

    SUPPORTED.forEach(function (code) {
      var opt = document.createElement('button');
      opt.className = 'lang-option';
      opt.textContent = LANG_NAMES[code] || code;
      opt.setAttribute('data-lang', code);
      opt.onclick = function () {
        setLang(code);
        dropdown.classList.remove('open');
      };
      dropdown.appendChild(opt);
    });

    document.getElementById('langBtn').onclick = function (e) {
      e.stopPropagation();
      dropdown.classList.toggle('open');
    };

    document.addEventListener('click', function () {
      dropdown.classList.remove('open');
    });
  }

  /* ── Public: switch language ────────────────────────────────── */
  function setLang(lang) {
    if (SUPPORTED.indexOf(lang) === -1) lang = DEFAULT;
    // Mirror to BOTH keys so the React bundle's LanguageContext and
    // i18n.js stay in lockstep — whichever side reads localStorage
    // on next mount/reload gets the same answer.
    localStorage.setItem('simy-lang', lang);
    try { localStorage.setItem('simy-language', lang); } catch (e) {}
    load(lang, apply);
  }

  /* ── Cross-component sync: watch for external writes to either
     language key (e.g. the React bundle's own setter) and re-apply
     the bridge whenever they diverge from CURRENT_LANG. Covers:
       (a) cross-tab storage events  (b) same-tab setItem via polling */
  function installLangKeySync() {
    function handleKey(newVal) {
      if (!newVal || SUPPORTED.indexOf(newVal) === -1) return;
      if (newVal === CURRENT_LANG) return;
      setLang(newVal);
    }
    window.addEventListener('storage', function (ev) {
      if (!ev) return;
      if (ev.key === 'simy-lang' || ev.key === 'simy-language') {
        handleKey(ev.newValue);
      }
    });
    // Same-tab writes don't fire `storage`. Poll at 400ms and detect
    // a change in EITHER key against the previously-seen values — this
    // way we notice simy-language being updated independently of
    // simy-lang (e.g. by the React bundle's own setter).
    var prevA = localStorage.getItem('simy-lang');
    var prevB = localStorage.getItem('simy-language');
    setInterval(function () {
      var a = localStorage.getItem('simy-lang');
      var b = localStorage.getItem('simy-language');
      var changed = null;
      if (a !== prevA && a && SUPPORTED.indexOf(a) !== -1) changed = a;
      else if (b !== prevB && b && SUPPORTED.indexOf(b) !== -1) changed = b;
      prevA = a;
      prevB = b;
      if (changed) { handleKey(changed); return; }
      // Also mirror on steady state: if one key is set and the other
      // isn't, copy across so the React bundle's next read agrees.
      if (a && !b && SUPPORTED.indexOf(a) !== -1) {
        try { localStorage.setItem('simy-language', a); prevB = a; } catch (e) {}
      } else if (b && !a && SUPPORTED.indexOf(b) !== -1) {
        try { localStorage.setItem('simy-lang', b); prevA = b; } catch (e) {}
      }
    }, 400);
  }

  /* ── Inject minimal CSS for switcher ────────────────────────── */
  function injectCSS() {
    var style = document.createElement('style');
    style.textContent =
      '.lang-switcher{position:relative;margin-left:8px}' +
      '.lang-btn{display:flex;align-items:center;gap:6px;background:none;border:none;color:#5a5a56;cursor:pointer;font-family:inherit;font-size:0.75rem;font-weight:400;padding:4px 8px;border-radius:6px;transition:background 0.15s}' +
      '.lang-btn:hover{background:rgba(0,0,0,0.04)}' +
      '.lang-btn svg{opacity:0.6}' +
      '.lang-dropdown{display:none;position:absolute;top:100%;right:0;margin-top:8px;background:#fff;border:1px solid #e0e0dc;border-radius:10px;box-shadow:0 8px 32px rgba(0,0,0,0.08);padding:6px;min-width:160px;z-index:100;max-height:400px;overflow-y:auto}' +
      '.lang-dropdown.open{display:grid;grid-template-columns:1fr 1fr;gap:2px}' +
      '.lang-option{display:block;width:100%;text-align:left;background:none;border:none;padding:8px 12px;font-size:0.78rem;color:#333;cursor:pointer;border-radius:6px;font-family:inherit;transition:background 0.12s;white-space:nowrap}' +
      '.lang-option:hover{background:#f5f5f3}' +
      '[dir="rtl"] .lang-switcher{margin-left:0;margin-right:8px}' +
      '[dir="rtl"] .lang-dropdown{right:auto;left:0}' +
      '[dir="rtl"] .lang-option{text-align:right}';
    document.head.appendChild(style);
  }

  /* ── Inject hreflang links for SEO ───────────────────────────── */
  function injectHreflang() {
    // Map our codes to BCP-47 hreflang values
    var hreflangMap = {
      'en': 'en', 'ja': 'ja', 'zh-Hans': 'zh-Hans', 'zh-Hant': 'zh-Hant',
      'fr': 'fr', 'de': 'de', 'es': 'es', 'ar': 'ar', 'it': 'it',
      'hi': 'hi', 'te': 'te', 'kn': 'kn', 'ko': 'ko', 'vi': 'vi',
      'th': 'th', 'id': 'id', 'ru': 'ru', 'pt-BR': 'pt-BR'
    };
    var base = location.origin + location.pathname;
    // x-default (no lang param)
    var xdef = document.createElement('link');
    xdef.rel = 'alternate';
    xdef.hreflang = 'x-default';
    xdef.href = base;
    document.head.appendChild(xdef);
    // Each language
    SUPPORTED.forEach(function (code) {
      var link = document.createElement('link');
      link.rel = 'alternate';
      link.hreflang = hreflangMap[code] || code;
      link.href = base + '?lang=' + code;
      document.head.appendChild(link);
    });
  }

  /* ── Init ───────────────────────────────────────────────────── */
  function init() {
    injectCSS();
    injectHreflang();
    buildSwitcher();

    // For React SPA: nav may not exist yet. Watch for it.
    if (!document.getElementById('langBtn')) {
      var observer = new MutationObserver(function () {
        if (document.querySelector('nav > .container') && !document.getElementById('langBtn')) {
          buildSwitcher();
          // Set display name from cached/loaded dict
          var lang = detect();
          load(lang, function (dict) {
            var display = document.getElementById('langDisplay');
            if (display) display.textContent = (dict._meta || {}).name || 'English';
          });
        }
      });
      observer.observe(document.body || document.documentElement, { childList: true, subtree: true });
      // Stop observing after 10s to avoid leaks
      setTimeout(function () { observer.disconnect(); }, 10000);
    }

    var lang = detect();
    CURRENT_LANG = lang;
    if (lang !== DEFAULT) {
      load(lang, apply);
    } else {
      // Still apply to set display name
      load(DEFAULT, function (dict) {
        var display = document.getElementById('langDisplay');
        if (display) display.textContent = (dict._meta || {}).name || 'English';
      });
    }

    // Kick off the Home (/) React SPA translation bridge — no-op on pages
    // that don't have a #root (all static pages). Loads the home-dom
    // dictionary and installs a MutationObserver that re-applies the
    // current language on every React render.
    initHomeDomBridge();

    // Keep simy-lang / simy-language in sync across i18n.js and the
    // React bundle. Without this, changing language via one side can
    // leave the other stuck on the old value after a reload.
    installLangKeySync();

    // Mirror the detected language to 'simy-language' on first load
    // so the React bundle's useState(() => localStorage.getItem(...))
    // picks it up on a subsequent reload.
    if (lang && SUPPORTED.indexOf(lang) !== -1) {
      try {
        if (localStorage.getItem('simy-language') !== lang) {
          localStorage.setItem('simy-language', lang);
        }
        if (localStorage.getItem('simy-lang') !== lang) {
          localStorage.setItem('simy-lang', lang);
        }
      } catch (e) {}
    }
  }

  // Run on DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose global
  window.simyI18n = { setLang: setLang, detect: detect };
})();
