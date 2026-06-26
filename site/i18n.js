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
  var HOME_LOCALES = ['en', 'ja'];
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

  function isIndexPage() {
    return location.pathname === '/' || location.pathname === '' || location.pathname === '/index.html';
  }

  function safeLangForPage(lang) {
    if (isIndexPage() && HOME_LOCALES.indexOf(lang) === -1) return DEFAULT;
    return lang;
  }

  /* ── Detect preferred language ─────────────────────────────── */
  function detect() {
    // 1. Query param  ?lang=ja
    var params = new URLSearchParams(location.search);
    var qLang = params.get('lang');
    if (qLang) {
      var resolved = resolve(qLang);
      if (!resolved && SUPPORTED.indexOf(qLang) !== -1) resolved = qLang;
      if (resolved) return safeLangForPage(resolved);
    }

    // 2. Saved preference — check BOTH keys. The React bundle on /
    //    uses 'simy-language' for its internal LanguageContext, while
    //    the static pages use 'simy-lang'. Either key is authoritative.
    var saved = localStorage.getItem('simy-lang');
    if (saved && SUPPORTED.indexOf(saved) !== -1) return safeLangForPage(saved);
    var savedReact = localStorage.getItem('simy-language');
    if (savedReact && SUPPORTED.indexOf(savedReact) !== -1) return safeLangForPage(savedReact);

    // 3. Browser / OS language
    var langs = navigator.languages || [navigator.language || navigator.userLanguage || ''];
    for (var i = 0; i < langs.length; i++) {
      var match = resolve(langs[i]);
      if (match) return safeLangForPage(match);
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
      kw: "Digital Twin, AI work assistant, AI agents, meeting follow-up automation, proposal deck automation, sales follow-up AI, AI research assistant, AI email drafting, PC task automation, knowledge work automation",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "Meeting ends. Your Twin starts working. SIMY moves follow-ups, decks, research, analysis, updates, and next actions forward while you step into the next conversation, customer, team, or idea." },
        "pricing": { t: "Pricing - SIMY | Create your Twin", d: "SIMY pricing for the work after meetings. Choose the Twin capacity your team needs for follow-ups, decks, research, analysis, updates, and next actions." },
        "compare": { t: "Compare SIMY - Agents do tasks. Your Twin carries the thread.", d: "Compare SIMY with agents, meeting recorders, search, and PC automation. SIMY starts when the meeting ends and carries the work forward." },
        "how-it-works": { t: "How SIMY Works - Your Twin after meetings", d: "See how SIMY turns meeting context into follow-ups, decks, research, analysis, updates, and next actions." },
        "contact": { t: "Contact - SIMY | Create your Twin", d: "Talk to SIMY about creating a Twin for post-meeting work, team follow-up, decks, research, and analysis." },
        "integrations": { t: "Integrations - SIMY | Work after meetings", d: "Connect SIMY with the channels that hold your meeting context and follow-up work." },
        "security": { t: "Security - SIMY | AI Twin for teams", d: "Security and privacy for teams using SIMY to move work after meetings." },
        "about": { t: "About SIMY - Meeting ends. Your Twin starts working.", d: "SIMY moves the work after meetings so drafts, briefs, updates, and next actions are ready when you return." }
      }
    },
    "ja": {
      kw: "Digital Twin, デジタルツイン, AI秘書, AIエージェント, パーソナルAI, 会議フォロー自動化, 営業フォローAI, 提案資料作成AI, パワーポイント自動作成, メール下書きAI, 調査AI, 戦略分析AI, PC作業自動化, ナレッジワーク自動化",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "会議が終わった瞬間、Twinがフォロー、資料、調査、分析、共有、次アクションを進めます。次の会話、顧客、チーム、アイデアへ向かう時間をつくるAI Twinです。" },
        "pricing": { t: "料金 - SIMY | Twinを作成", d: "会議後の仕事を進めるSIMYの料金。フォロー、資料、調査、分析、共有、次アクションを進めるTwinの容量を選べます。" },
        "compare": { t: "SIMY比較 - エージェントはタスクをこなす。Twinは文脈を運ぶ。", d: "SIMYをエージェント、議事録ツール、検索、PC自動化と比較。会議が終わった瞬間にTwinが仕事を前へ進めます。" },
        "how-it-works": { t: "SIMYの仕組み - 会議後に動くTwin", d: "SIMYが会議の文脈をフォロー、資料、調査、分析、共有、次アクションへ変える流れを紹介します。" },
        "contact": { t: "お問い合わせ - SIMY | Twinを作成", d: "会議後の仕事を進めるTwin、チーム導入、営業フォロー、資料作成、調査、分析についてSIMYにご相談ください。" },
        "integrations": { t: "連携 - SIMY | 会議後の仕事を前へ", d: "会議の文脈とフォローアップが集まるチャンネルにSIMYをつなぎ、次の仕事を前へ進めます。" },
        "security": { t: "セキュリティ - SIMY | チームのAI Twin", d: "会議後の仕事をSIMYで進めるチームのためのセキュリティとプライバシー。" },
        "about": { t: "SIMYについて - Meeting ends. Your Twin starts working.", d: "SIMYは、会議後の仕事を進め、下書き、ブリーフ、共有、次アクションとして返すAI Twinです。" }
      }
    },
    "zh-Hans": {
      kw: "Digital Twin, AI work assistant, AI agents, meeting follow-up automation, proposal deck automation, sales follow-up AI, AI research assistant, AI email drafting, PC task automation, knowledge work automation",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "Meeting ends. Your Twin starts working. SIMY moves follow-ups, decks, research, analysis, updates, and next actions forward while you step into the next conversation, customer, team, or idea." },
        "pricing": { t: "Pricing - SIMY | Create your Twin", d: "SIMY pricing for the work after meetings. Choose the Twin capacity your team needs for follow-ups, decks, research, analysis, updates, and next actions." },
        "compare": { t: "Compare SIMY - Agents do tasks. Your Twin carries the thread.", d: "Compare SIMY with agents, meeting recorders, search, and PC automation. SIMY starts when the meeting ends and carries the work forward." },
        "how-it-works": { t: "How SIMY Works - Your Twin after meetings", d: "See how SIMY turns meeting context into follow-ups, decks, research, analysis, updates, and next actions." },
        "contact": { t: "Contact - SIMY | Create your Twin", d: "Talk to SIMY about creating a Twin for post-meeting work, team follow-up, decks, research, and analysis." },
        "integrations": { t: "Integrations - SIMY | Work after meetings", d: "Connect SIMY with the channels that hold your meeting context and follow-up work." },
        "security": { t: "Security - SIMY | AI Twin for teams", d: "Security and privacy for teams using SIMY to move work after meetings." },
        "about": { t: "About SIMY - Meeting ends. Your Twin starts working.", d: "SIMY moves the work after meetings so drafts, briefs, updates, and next actions are ready when you return." }
      }
    },
    "zh-Hant": {
      kw: "Digital Twin, AI work assistant, AI agents, meeting follow-up automation, proposal deck automation, sales follow-up AI, AI research assistant, AI email drafting, PC task automation, knowledge work automation",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "Meeting ends. Your Twin starts working. SIMY moves follow-ups, decks, research, analysis, updates, and next actions forward while you step into the next conversation, customer, team, or idea." },
        "pricing": { t: "Pricing - SIMY | Create your Twin", d: "SIMY pricing for the work after meetings. Choose the Twin capacity your team needs for follow-ups, decks, research, analysis, updates, and next actions." },
        "compare": { t: "Compare SIMY - Agents do tasks. Your Twin carries the thread.", d: "Compare SIMY with agents, meeting recorders, search, and PC automation. SIMY starts when the meeting ends and carries the work forward." },
        "how-it-works": { t: "How SIMY Works - Your Twin after meetings", d: "See how SIMY turns meeting context into follow-ups, decks, research, analysis, updates, and next actions." },
        "contact": { t: "Contact - SIMY | Create your Twin", d: "Talk to SIMY about creating a Twin for post-meeting work, team follow-up, decks, research, and analysis." },
        "integrations": { t: "Integrations - SIMY | Work after meetings", d: "Connect SIMY with the channels that hold your meeting context and follow-up work." },
        "security": { t: "Security - SIMY | AI Twin for teams", d: "Security and privacy for teams using SIMY to move work after meetings." },
        "about": { t: "About SIMY - Meeting ends. Your Twin starts working.", d: "SIMY moves the work after meetings so drafts, briefs, updates, and next actions are ready when you return." }
      }
    },
    "fr": {
      kw: "Digital Twin, AI work assistant, AI agents, meeting follow-up automation, proposal deck automation, sales follow-up AI, AI research assistant, AI email drafting, PC task automation, knowledge work automation",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "Meeting ends. Your Twin starts working. SIMY moves follow-ups, decks, research, analysis, updates, and next actions forward while you step into the next conversation, customer, team, or idea." },
        "pricing": { t: "Pricing - SIMY | Create your Twin", d: "SIMY pricing for the work after meetings. Choose the Twin capacity your team needs for follow-ups, decks, research, analysis, updates, and next actions." },
        "compare": { t: "Compare SIMY - Agents do tasks. Your Twin carries the thread.", d: "Compare SIMY with agents, meeting recorders, search, and PC automation. SIMY starts when the meeting ends and carries the work forward." },
        "how-it-works": { t: "How SIMY Works - Your Twin after meetings", d: "See how SIMY turns meeting context into follow-ups, decks, research, analysis, updates, and next actions." },
        "contact": { t: "Contact - SIMY | Create your Twin", d: "Talk to SIMY about creating a Twin for post-meeting work, team follow-up, decks, research, and analysis." },
        "integrations": { t: "Integrations - SIMY | Work after meetings", d: "Connect SIMY with the channels that hold your meeting context and follow-up work." },
        "security": { t: "Security - SIMY | AI Twin for teams", d: "Security and privacy for teams using SIMY to move work after meetings." },
        "about": { t: "About SIMY - Meeting ends. Your Twin starts working.", d: "SIMY moves the work after meetings so drafts, briefs, updates, and next actions are ready when you return." }
      }
    },
    "de": {
      kw: "Digital Twin, AI work assistant, AI agents, meeting follow-up automation, proposal deck automation, sales follow-up AI, AI research assistant, AI email drafting, PC task automation, knowledge work automation",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "Meeting ends. Your Twin starts working. SIMY moves follow-ups, decks, research, analysis, updates, and next actions forward while you step into the next conversation, customer, team, or idea." },
        "pricing": { t: "Pricing - SIMY | Create your Twin", d: "SIMY pricing for the work after meetings. Choose the Twin capacity your team needs for follow-ups, decks, research, analysis, updates, and next actions." },
        "compare": { t: "Compare SIMY - Agents do tasks. Your Twin carries the thread.", d: "Compare SIMY with agents, meeting recorders, search, and PC automation. SIMY starts when the meeting ends and carries the work forward." },
        "how-it-works": { t: "How SIMY Works - Your Twin after meetings", d: "See how SIMY turns meeting context into follow-ups, decks, research, analysis, updates, and next actions." },
        "contact": { t: "Contact - SIMY | Create your Twin", d: "Talk to SIMY about creating a Twin for post-meeting work, team follow-up, decks, research, and analysis." },
        "integrations": { t: "Integrations - SIMY | Work after meetings", d: "Connect SIMY with the channels that hold your meeting context and follow-up work." },
        "security": { t: "Security - SIMY | AI Twin for teams", d: "Security and privacy for teams using SIMY to move work after meetings." },
        "about": { t: "About SIMY - Meeting ends. Your Twin starts working.", d: "SIMY moves the work after meetings so drafts, briefs, updates, and next actions are ready when you return." }
      }
    },
    "es": {
      kw: "Digital Twin, AI work assistant, AI agents, meeting follow-up automation, proposal deck automation, sales follow-up AI, AI research assistant, AI email drafting, PC task automation, knowledge work automation",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "Meeting ends. Your Twin starts working. SIMY moves follow-ups, decks, research, analysis, updates, and next actions forward while you step into the next conversation, customer, team, or idea." },
        "pricing": { t: "Pricing - SIMY | Create your Twin", d: "SIMY pricing for the work after meetings. Choose the Twin capacity your team needs for follow-ups, decks, research, analysis, updates, and next actions." },
        "compare": { t: "Compare SIMY - Agents do tasks. Your Twin carries the thread.", d: "Compare SIMY with agents, meeting recorders, search, and PC automation. SIMY starts when the meeting ends and carries the work forward." },
        "how-it-works": { t: "How SIMY Works - Your Twin after meetings", d: "See how SIMY turns meeting context into follow-ups, decks, research, analysis, updates, and next actions." },
        "contact": { t: "Contact - SIMY | Create your Twin", d: "Talk to SIMY about creating a Twin for post-meeting work, team follow-up, decks, research, and analysis." },
        "integrations": { t: "Integrations - SIMY | Work after meetings", d: "Connect SIMY with the channels that hold your meeting context and follow-up work." },
        "security": { t: "Security - SIMY | AI Twin for teams", d: "Security and privacy for teams using SIMY to move work after meetings." },
        "about": { t: "About SIMY - Meeting ends. Your Twin starts working.", d: "SIMY moves the work after meetings so drafts, briefs, updates, and next actions are ready when you return." }
      }
    },
    "ar": {
      kw: "Digital Twin, AI work assistant, AI agents, meeting follow-up automation, proposal deck automation, sales follow-up AI, AI research assistant, AI email drafting, PC task automation, knowledge work automation",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "Meeting ends. Your Twin starts working. SIMY moves follow-ups, decks, research, analysis, updates, and next actions forward while you step into the next conversation, customer, team, or idea." },
        "pricing": { t: "Pricing - SIMY | Create your Twin", d: "SIMY pricing for the work after meetings. Choose the Twin capacity your team needs for follow-ups, decks, research, analysis, updates, and next actions." },
        "compare": { t: "Compare SIMY - Agents do tasks. Your Twin carries the thread.", d: "Compare SIMY with agents, meeting recorders, search, and PC automation. SIMY starts when the meeting ends and carries the work forward." },
        "how-it-works": { t: "How SIMY Works - Your Twin after meetings", d: "See how SIMY turns meeting context into follow-ups, decks, research, analysis, updates, and next actions." },
        "contact": { t: "Contact - SIMY | Create your Twin", d: "Talk to SIMY about creating a Twin for post-meeting work, team follow-up, decks, research, and analysis." },
        "integrations": { t: "Integrations - SIMY | Work after meetings", d: "Connect SIMY with the channels that hold your meeting context and follow-up work." },
        "security": { t: "Security - SIMY | AI Twin for teams", d: "Security and privacy for teams using SIMY to move work after meetings." },
        "about": { t: "About SIMY - Meeting ends. Your Twin starts working.", d: "SIMY moves the work after meetings so drafts, briefs, updates, and next actions are ready when you return." }
      }
    },
    "it": {
      kw: "Digital Twin, AI work assistant, AI agents, meeting follow-up automation, proposal deck automation, sales follow-up AI, AI research assistant, AI email drafting, PC task automation, knowledge work automation",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "Meeting ends. Your Twin starts working. SIMY moves follow-ups, decks, research, analysis, updates, and next actions forward while you step into the next conversation, customer, team, or idea." },
        "pricing": { t: "Pricing - SIMY | Create your Twin", d: "SIMY pricing for the work after meetings. Choose the Twin capacity your team needs for follow-ups, decks, research, analysis, updates, and next actions." },
        "compare": { t: "Compare SIMY - Agents do tasks. Your Twin carries the thread.", d: "Compare SIMY with agents, meeting recorders, search, and PC automation. SIMY starts when the meeting ends and carries the work forward." },
        "how-it-works": { t: "How SIMY Works - Your Twin after meetings", d: "See how SIMY turns meeting context into follow-ups, decks, research, analysis, updates, and next actions." },
        "contact": { t: "Contact - SIMY | Create your Twin", d: "Talk to SIMY about creating a Twin for post-meeting work, team follow-up, decks, research, and analysis." },
        "integrations": { t: "Integrations - SIMY | Work after meetings", d: "Connect SIMY with the channels that hold your meeting context and follow-up work." },
        "security": { t: "Security - SIMY | AI Twin for teams", d: "Security and privacy for teams using SIMY to move work after meetings." },
        "about": { t: "About SIMY - Meeting ends. Your Twin starts working.", d: "SIMY moves the work after meetings so drafts, briefs, updates, and next actions are ready when you return." }
      }
    },
    "hi": {
      kw: "Digital Twin, AI work assistant, AI agents, meeting follow-up automation, proposal deck automation, sales follow-up AI, AI research assistant, AI email drafting, PC task automation, knowledge work automation",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "Meeting ends. Your Twin starts working. SIMY moves follow-ups, decks, research, analysis, updates, and next actions forward while you step into the next conversation, customer, team, or idea." },
        "pricing": { t: "Pricing - SIMY | Create your Twin", d: "SIMY pricing for the work after meetings. Choose the Twin capacity your team needs for follow-ups, decks, research, analysis, updates, and next actions." },
        "compare": { t: "Compare SIMY - Agents do tasks. Your Twin carries the thread.", d: "Compare SIMY with agents, meeting recorders, search, and PC automation. SIMY starts when the meeting ends and carries the work forward." },
        "how-it-works": { t: "How SIMY Works - Your Twin after meetings", d: "See how SIMY turns meeting context into follow-ups, decks, research, analysis, updates, and next actions." },
        "contact": { t: "Contact - SIMY | Create your Twin", d: "Talk to SIMY about creating a Twin for post-meeting work, team follow-up, decks, research, and analysis." },
        "integrations": { t: "Integrations - SIMY | Work after meetings", d: "Connect SIMY with the channels that hold your meeting context and follow-up work." },
        "security": { t: "Security - SIMY | AI Twin for teams", d: "Security and privacy for teams using SIMY to move work after meetings." },
        "about": { t: "About SIMY - Meeting ends. Your Twin starts working.", d: "SIMY moves the work after meetings so drafts, briefs, updates, and next actions are ready when you return." }
      }
    },
    "te": {
      kw: "Digital Twin, AI work assistant, AI agents, meeting follow-up automation, proposal deck automation, sales follow-up AI, AI research assistant, AI email drafting, PC task automation, knowledge work automation",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "Meeting ends. Your Twin starts working. SIMY moves follow-ups, decks, research, analysis, updates, and next actions forward while you step into the next conversation, customer, team, or idea." },
        "pricing": { t: "Pricing - SIMY | Create your Twin", d: "SIMY pricing for the work after meetings. Choose the Twin capacity your team needs for follow-ups, decks, research, analysis, updates, and next actions." },
        "compare": { t: "Compare SIMY - Agents do tasks. Your Twin carries the thread.", d: "Compare SIMY with agents, meeting recorders, search, and PC automation. SIMY starts when the meeting ends and carries the work forward." },
        "how-it-works": { t: "How SIMY Works - Your Twin after meetings", d: "See how SIMY turns meeting context into follow-ups, decks, research, analysis, updates, and next actions." },
        "contact": { t: "Contact - SIMY | Create your Twin", d: "Talk to SIMY about creating a Twin for post-meeting work, team follow-up, decks, research, and analysis." },
        "integrations": { t: "Integrations - SIMY | Work after meetings", d: "Connect SIMY with the channels that hold your meeting context and follow-up work." },
        "security": { t: "Security - SIMY | AI Twin for teams", d: "Security and privacy for teams using SIMY to move work after meetings." },
        "about": { t: "About SIMY - Meeting ends. Your Twin starts working.", d: "SIMY moves the work after meetings so drafts, briefs, updates, and next actions are ready when you return." }
      }
    },
    "kn": {
      kw: "Digital Twin, AI work assistant, AI agents, meeting follow-up automation, proposal deck automation, sales follow-up AI, AI research assistant, AI email drafting, PC task automation, knowledge work automation",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "Meeting ends. Your Twin starts working. SIMY moves follow-ups, decks, research, analysis, updates, and next actions forward while you step into the next conversation, customer, team, or idea." },
        "pricing": { t: "Pricing - SIMY | Create your Twin", d: "SIMY pricing for the work after meetings. Choose the Twin capacity your team needs for follow-ups, decks, research, analysis, updates, and next actions." },
        "compare": { t: "Compare SIMY - Agents do tasks. Your Twin carries the thread.", d: "Compare SIMY with agents, meeting recorders, search, and PC automation. SIMY starts when the meeting ends and carries the work forward." },
        "how-it-works": { t: "How SIMY Works - Your Twin after meetings", d: "See how SIMY turns meeting context into follow-ups, decks, research, analysis, updates, and next actions." },
        "contact": { t: "Contact - SIMY | Create your Twin", d: "Talk to SIMY about creating a Twin for post-meeting work, team follow-up, decks, research, and analysis." },
        "integrations": { t: "Integrations - SIMY | Work after meetings", d: "Connect SIMY with the channels that hold your meeting context and follow-up work." },
        "security": { t: "Security - SIMY | AI Twin for teams", d: "Security and privacy for teams using SIMY to move work after meetings." },
        "about": { t: "About SIMY - Meeting ends. Your Twin starts working.", d: "SIMY moves the work after meetings so drafts, briefs, updates, and next actions are ready when you return." }
      }
    },
    "ko": {
      kw: "Digital Twin, AI work assistant, AI agents, meeting follow-up automation, proposal deck automation, sales follow-up AI, AI research assistant, AI email drafting, PC task automation, knowledge work automation",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "Meeting ends. Your Twin starts working. SIMY moves follow-ups, decks, research, analysis, updates, and next actions forward while you step into the next conversation, customer, team, or idea." },
        "pricing": { t: "Pricing - SIMY | Create your Twin", d: "SIMY pricing for the work after meetings. Choose the Twin capacity your team needs for follow-ups, decks, research, analysis, updates, and next actions." },
        "compare": { t: "Compare SIMY - Agents do tasks. Your Twin carries the thread.", d: "Compare SIMY with agents, meeting recorders, search, and PC automation. SIMY starts when the meeting ends and carries the work forward." },
        "how-it-works": { t: "How SIMY Works - Your Twin after meetings", d: "See how SIMY turns meeting context into follow-ups, decks, research, analysis, updates, and next actions." },
        "contact": { t: "Contact - SIMY | Create your Twin", d: "Talk to SIMY about creating a Twin for post-meeting work, team follow-up, decks, research, and analysis." },
        "integrations": { t: "Integrations - SIMY | Work after meetings", d: "Connect SIMY with the channels that hold your meeting context and follow-up work." },
        "security": { t: "Security - SIMY | AI Twin for teams", d: "Security and privacy for teams using SIMY to move work after meetings." },
        "about": { t: "About SIMY - Meeting ends. Your Twin starts working.", d: "SIMY moves the work after meetings so drafts, briefs, updates, and next actions are ready when you return." }
      }
    },
    "vi": {
      kw: "Digital Twin, AI work assistant, AI agents, meeting follow-up automation, proposal deck automation, sales follow-up AI, AI research assistant, AI email drafting, PC task automation, knowledge work automation",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "Meeting ends. Your Twin starts working. SIMY moves follow-ups, decks, research, analysis, updates, and next actions forward while you step into the next conversation, customer, team, or idea." },
        "pricing": { t: "Pricing - SIMY | Create your Twin", d: "SIMY pricing for the work after meetings. Choose the Twin capacity your team needs for follow-ups, decks, research, analysis, updates, and next actions." },
        "compare": { t: "Compare SIMY - Agents do tasks. Your Twin carries the thread.", d: "Compare SIMY with agents, meeting recorders, search, and PC automation. SIMY starts when the meeting ends and carries the work forward." },
        "how-it-works": { t: "How SIMY Works - Your Twin after meetings", d: "See how SIMY turns meeting context into follow-ups, decks, research, analysis, updates, and next actions." },
        "contact": { t: "Contact - SIMY | Create your Twin", d: "Talk to SIMY about creating a Twin for post-meeting work, team follow-up, decks, research, and analysis." },
        "integrations": { t: "Integrations - SIMY | Work after meetings", d: "Connect SIMY with the channels that hold your meeting context and follow-up work." },
        "security": { t: "Security - SIMY | AI Twin for teams", d: "Security and privacy for teams using SIMY to move work after meetings." },
        "about": { t: "About SIMY - Meeting ends. Your Twin starts working.", d: "SIMY moves the work after meetings so drafts, briefs, updates, and next actions are ready when you return." }
      }
    },
    "th": {
      kw: "Digital Twin, AI work assistant, AI agents, meeting follow-up automation, proposal deck automation, sales follow-up AI, AI research assistant, AI email drafting, PC task automation, knowledge work automation",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "Meeting ends. Your Twin starts working. SIMY moves follow-ups, decks, research, analysis, updates, and next actions forward while you step into the next conversation, customer, team, or idea." },
        "pricing": { t: "Pricing - SIMY | Create your Twin", d: "SIMY pricing for the work after meetings. Choose the Twin capacity your team needs for follow-ups, decks, research, analysis, updates, and next actions." },
        "compare": { t: "Compare SIMY - Agents do tasks. Your Twin carries the thread.", d: "Compare SIMY with agents, meeting recorders, search, and PC automation. SIMY starts when the meeting ends and carries the work forward." },
        "how-it-works": { t: "How SIMY Works - Your Twin after meetings", d: "See how SIMY turns meeting context into follow-ups, decks, research, analysis, updates, and next actions." },
        "contact": { t: "Contact - SIMY | Create your Twin", d: "Talk to SIMY about creating a Twin for post-meeting work, team follow-up, decks, research, and analysis." },
        "integrations": { t: "Integrations - SIMY | Work after meetings", d: "Connect SIMY with the channels that hold your meeting context and follow-up work." },
        "security": { t: "Security - SIMY | AI Twin for teams", d: "Security and privacy for teams using SIMY to move work after meetings." },
        "about": { t: "About SIMY - Meeting ends. Your Twin starts working.", d: "SIMY moves the work after meetings so drafts, briefs, updates, and next actions are ready when you return." }
      }
    },
    "id": {
      kw: "Digital Twin, AI work assistant, AI agents, meeting follow-up automation, proposal deck automation, sales follow-up AI, AI research assistant, AI email drafting, PC task automation, knowledge work automation",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "Meeting ends. Your Twin starts working. SIMY moves follow-ups, decks, research, analysis, updates, and next actions forward while you step into the next conversation, customer, team, or idea." },
        "pricing": { t: "Pricing - SIMY | Create your Twin", d: "SIMY pricing for the work after meetings. Choose the Twin capacity your team needs for follow-ups, decks, research, analysis, updates, and next actions." },
        "compare": { t: "Compare SIMY - Agents do tasks. Your Twin carries the thread.", d: "Compare SIMY with agents, meeting recorders, search, and PC automation. SIMY starts when the meeting ends and carries the work forward." },
        "how-it-works": { t: "How SIMY Works - Your Twin after meetings", d: "See how SIMY turns meeting context into follow-ups, decks, research, analysis, updates, and next actions." },
        "contact": { t: "Contact - SIMY | Create your Twin", d: "Talk to SIMY about creating a Twin for post-meeting work, team follow-up, decks, research, and analysis." },
        "integrations": { t: "Integrations - SIMY | Work after meetings", d: "Connect SIMY with the channels that hold your meeting context and follow-up work." },
        "security": { t: "Security - SIMY | AI Twin for teams", d: "Security and privacy for teams using SIMY to move work after meetings." },
        "about": { t: "About SIMY - Meeting ends. Your Twin starts working.", d: "SIMY moves the work after meetings so drafts, briefs, updates, and next actions are ready when you return." }
      }
    },
    "ru": {
      kw: "Digital Twin, AI work assistant, AI agents, meeting follow-up automation, proposal deck automation, sales follow-up AI, AI research assistant, AI email drafting, PC task automation, knowledge work automation",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "Meeting ends. Your Twin starts working. SIMY moves follow-ups, decks, research, analysis, updates, and next actions forward while you step into the next conversation, customer, team, or idea." },
        "pricing": { t: "Pricing - SIMY | Create your Twin", d: "SIMY pricing for the work after meetings. Choose the Twin capacity your team needs for follow-ups, decks, research, analysis, updates, and next actions." },
        "compare": { t: "Compare SIMY - Agents do tasks. Your Twin carries the thread.", d: "Compare SIMY with agents, meeting recorders, search, and PC automation. SIMY starts when the meeting ends and carries the work forward." },
        "how-it-works": { t: "How SIMY Works - Your Twin after meetings", d: "See how SIMY turns meeting context into follow-ups, decks, research, analysis, updates, and next actions." },
        "contact": { t: "Contact - SIMY | Create your Twin", d: "Talk to SIMY about creating a Twin for post-meeting work, team follow-up, decks, research, and analysis." },
        "integrations": { t: "Integrations - SIMY | Work after meetings", d: "Connect SIMY with the channels that hold your meeting context and follow-up work." },
        "security": { t: "Security - SIMY | AI Twin for teams", d: "Security and privacy for teams using SIMY to move work after meetings." },
        "about": { t: "About SIMY - Meeting ends. Your Twin starts working.", d: "SIMY moves the work after meetings so drafts, briefs, updates, and next actions are ready when you return." }
      }
    },
    "pt-BR": {
      kw: "Digital Twin, AI work assistant, AI agents, meeting follow-up automation, proposal deck automation, sales follow-up AI, AI research assistant, AI email drafting, PC task automation, knowledge work automation",
      p: {
        "index": { t: "SIMY - Meeting Ends. Your Twin Starts Working.", d: "Meeting ends. Your Twin starts working. SIMY moves follow-ups, decks, research, analysis, updates, and next actions forward while you step into the next conversation, customer, team, or idea." },
        "pricing": { t: "Pricing - SIMY | Create your Twin", d: "SIMY pricing for the work after meetings. Choose the Twin capacity your team needs for follow-ups, decks, research, analysis, updates, and next actions." },
        "compare": { t: "Compare SIMY - Agents do tasks. Your Twin carries the thread.", d: "Compare SIMY with agents, meeting recorders, search, and PC automation. SIMY starts when the meeting ends and carries the work forward." },
        "how-it-works": { t: "How SIMY Works - Your Twin after meetings", d: "See how SIMY turns meeting context into follow-ups, decks, research, analysis, updates, and next actions." },
        "contact": { t: "Contact - SIMY | Create your Twin", d: "Talk to SIMY about creating a Twin for post-meeting work, team follow-up, decks, research, and analysis." },
        "integrations": { t: "Integrations - SIMY | Work after meetings", d: "Connect SIMY with the channels that hold your meeting context and follow-up work." },
        "security": { t: "Security - SIMY | AI Twin for teams", d: "Security and privacy for teams using SIMY to move work after meetings." },
        "about": { t: "About SIMY - Meeting ends. Your Twin starts working.", d: "SIMY moves the work after meetings so drafts, briefs, updates, and next actions are ready when you return." }
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
    if (key === 'index' && lang !== 'en' && lang !== 'ja') {
      page = SEO.en && SEO.en.p && SEO.en.p.index;
    }
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
    var keywords = (key === 'index' && lang !== 'en' && lang !== 'ja' && SEO.en)
      ? SEO.en.kw
      : data.kw;
    if (keywords) setMetaTag('keywords', keywords);
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
        '<h2 class="simy-ss-title">From meeting to shipped AI executions.</h2>',
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
              '<div class="simy-ss-subtitle" data-simy-subtitle></div>',
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
    // Scene timeline for captions + progress rail only. The cursor
    // animation is baked into demo.mp4 (painted by the Playwright
    // recorder), so we do not apply any CSS zoom or transform-origin
    // tracking here — the viewer just watches the raw video.
    var SCENES = [
      { at: 0,
        main: 'Alex opens the Twin before the planning session.',
        sub:  'Product Manager at a 150-person tech company. The Twin already knows what needs decisions today.' },
      { at: 4384,
        main: 'Planning session ends \u2014 every decision captured.',
        sub:  'SIMY generates a structured roadmap, assigns owners, and sends summaries automatically.' },
      { at: 8559,
        main: 'Roadmap items become assigned, ready-to-review tickets.',
        sub:  'Hours of turning discussion into a roadmap \u2014 gone.' },
      { at: 12728,
        main: 'Growth Dashboard: North Star 1,247 (+12.4%) \u00b7 Retention 71%.',
        sub:  'Roadmap ready before the next standup.' }
    ];

    var video    = wrap.querySelector('[data-simy-video]');
    var subtitle = wrap.querySelector('[data-simy-subtitle]');
    var rail     = wrap.querySelector('[data-simy-rail]');
    var capMain  = wrap.querySelector('[data-simy-cap-main]');
    var capSub   = wrap.querySelector('[data-simy-cap-sub]');
    var ticks    = wrap.querySelectorAll('[data-simy-ticks] .simy-ss-tick');
    var pauseBtn = wrap.querySelector('[data-simy-pause]');
    var replayBtn= wrap.querySelector('[data-simy-replay]');
    if (!video) return;

    var currentIndex = -1;
    var reduced = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    var rafId = 0;

    function sceneIndexForMs(ms) {
      var i = 0;
      for (var k = 0; k < SCENES.length; k++) {
        if (ms + 40 >= SCENES[k].at) i = k;
      }
      return i;
    }

    // Drop any stale inline transforms left over from older builds.
    video.style.transform = '';
    video.style.transformOrigin = '';

    function rafLoop() {
      // Keep the scene/caption state and the progress rail in sync with
      // video.currentTime. Cheaper than relying on 'timeupdate' which
      // only fires ~4x/s.
      var t   = (video.currentTime || 0) * 1000;
      var idx = sceneIndexForMs(t);
      if (idx !== currentIndex) renderScene(idx);
      var durMs = ((video.duration && isFinite(video.duration)) ? video.duration : 13.778) * 1000;
      rail.style.transform = 'scaleX(' + Math.min(1, t / durMs) + ')';
      rafId = requestAnimationFrame(rafLoop);
    }

    function renderScene(i) {
      if (i === currentIndex) return;
      currentIndex = i;
      var s = SCENES[i];
      capMain.textContent = s.main;
      capSub.textContent  = s.sub;
      if (subtitle) {
        subtitle.textContent = s.main;
        // Fade the subtitle out briefly, swap text, fade back in.
        subtitle.classList.remove('is-visible');
        // eslint-disable-next-line no-void
        void subtitle.offsetWidth;
        subtitle.classList.add('is-visible');
      }
      for (var t = 0; t < ticks.length; t++) {
        ticks[t].setAttribute('data-active', t === i ? 'true' : 'false');
      }
    }

    function onTimeUpdate() {
      if (!wrap.isConnected) return;
      var ms  = (video.currentTime || 0) * 1000;
      var dur = (video.duration && isFinite(video.duration)) ? video.duration : 13.778;
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
    } else {
      // Start the rAF loop. Reads video.currentTime every frame to keep
      // the scene/caption and progress rail in sync with playback,
      // pause/seek/loop all handled for free.
      rafId = requestAnimationFrame(rafLoop);
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
      '.simy-ss-subtitle{position:absolute;left:50%;bottom:6%;transform:translateX(-50%);max-width:82%;padding:10px 18px;background:rgba(10,10,12,.78);color:#f9f9f6;font-family:"Geist",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:15px;font-weight:600;line-height:1.45;text-align:center;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.45),inset 0 1px 0 rgba(255,255,255,.08);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);pointer-events:none;z-index:4;opacity:0;transition:opacity .35s ease;text-wrap:balance;text-shadow:0 1px 2px rgba(0,0,0,.35);}',
      '.simy-ss-subtitle.is-visible{opacity:1;}',
      '@media (max-width:768px){.simy-ss-subtitle{font-size:12px;padding:7px 12px;bottom:5%;max-width:88%;}}',
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
    if (isIndexPage() && meta.code && HOME_LOCALES.indexOf(meta.code) === -1) {
      load(DEFAULT, apply);
      return;
    }

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

    var switcherLocales = isIndexPage() ? HOME_LOCALES : SUPPORTED;
    switcherLocales.forEach(function (code) {
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
    lang = safeLangForPage(lang);
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
    // Each language. The redesigned top page currently has polished copy for
    // English and Japanese; other pages can still expose the wider locale set.
    var hreflangLocales = isIndexPage() ? HOME_LOCALES : SUPPORTED;
    hreflangLocales.forEach(function (code) {
      var link = document.createElement('link');
      link.rel = 'alternate';
      link.hreflang = hreflangMap[code] || code;
      link.href = base + '?lang=' + code;
      document.head.appendChild(link);
    });
  }

  /* ── Static mobile nav: keep signup reachable when .nav-right is hidden ── */
  function enhanceStaticMobileNav() {
    var navLinks = document.getElementById('navLinks');
    var menuButton = document.querySelector('.mobile-menu-btn');
    if (!navLinks || !menuButton || navLinks.querySelector('[data-mobile-signup-link]')) return;

    var signin = document.querySelector('.nav-right .nav-signin');
    var signup = document.querySelector('.nav-right .btn-primary');
    if (signin) {
      var signinLink = signin.cloneNode(true);
      signinLink.className = 'mobile-only-nav-action mobile-signin';
      signinLink.setAttribute('data-mobile-signin-link', 'true');
      navLinks.appendChild(signinLink);
    }
    if (signup) {
      var signupLink = signup.cloneNode(true);
      signupLink.className = 'mobile-only-nav-action mobile-signup';
      signupLink.setAttribute('data-mobile-signup-link', 'true');
      navLinks.appendChild(signupLink);
    }

    menuButton.removeAttribute('onclick');
    menuButton.setAttribute('aria-controls', 'navLinks');
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.addEventListener('click', function () {
      var isOpen = navLinks.classList.toggle('active');
      menuButton.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
  }

  /* ── Init ───────────────────────────────────────────────────── */
  function init() {
    injectCSS();
    injectHreflang();
    buildSwitcher();
    enhanceStaticMobileNav();

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
