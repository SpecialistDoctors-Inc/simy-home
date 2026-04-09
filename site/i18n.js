/**
 * SIMY i18n — Lightweight client-side internationalisation
 * Supports: en, ja, es, fr, zh, ar (RTL)
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

  var SUPPORTED = ['en', 'ja', 'es', 'fr', 'zh', 'ar'];
  var DEFAULT = 'en';
  var CACHE = {};

  /* ── Detect preferred language ─────────────────────────────── */
  function detect() {
    // 1. Query param  ?lang=ja
    var params = new URLSearchParams(location.search);
    var qLang = params.get('lang');
    if (qLang && SUPPORTED.indexOf(qLang) !== -1) return qLang;

    // 2. Saved preference
    var saved = localStorage.getItem('simy-lang');
    if (saved && SUPPORTED.indexOf(saved) !== -1) return saved;

    // 3. Browser / OS language
    var langs = navigator.languages || [navigator.language || navigator.userLanguage || ''];
    for (var i = 0; i < langs.length; i++) {
      var code = langs[i].toLowerCase().split('-')[0];
      if (SUPPORTED.indexOf(code) !== -1) return code;
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

  /* ── Apply translations to DOM ─────────────────────────────── */
  function apply(dict) {
    var meta = dict._meta || {};

    // Set html lang & dir
    document.documentElement.lang = meta.code || DEFAULT;
    document.documentElement.dir = meta.dir || 'ltr';

    // Text-only replacements
    var els = document.querySelectorAll('[data-i18n]');
    for (var i = 0; i < els.length; i++) {
      var key = els[i].getAttribute('data-i18n');
      if (dict[key] !== undefined) {
        els[i].textContent = dict[key];
      }
    }

    // HTML replacements (e.g. <br> tags)
    var htmlEls = document.querySelectorAll('[data-i18n-html]');
    for (var j = 0; j < htmlEls.length; j++) {
      var hkey = htmlEls[j].getAttribute('data-i18n-html');
      if (dict[hkey] !== undefined) {
        htmlEls[j].innerHTML = dict[hkey];
      }
    }

    // Placeholder / aria-label
    var attrEls = document.querySelectorAll('[data-i18n-placeholder]');
    for (var k = 0; k < attrEls.length; k++) {
      var pkey = attrEls[k].getAttribute('data-i18n-placeholder');
      if (dict[pkey] !== undefined) {
        attrEls[k].setAttribute('placeholder', dict[pkey]);
      }
    }

    // Update active selector display
    var display = document.getElementById('langDisplay');
    if (display && meta.name) {
      display.textContent = meta.name;
    }
  }

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
    var names = { en: 'English', ja: '\u65e5\u672c\u8a9e', es: 'Espa\u00f1ol', fr: 'Fran\u00e7ais', zh: '\u4e2d\u6587', ar: '\u0627\u0644\u0639\u0631\u0628\u064a\u0629' };

    SUPPORTED.forEach(function (code) {
      var opt = document.createElement('button');
      opt.className = 'lang-option';
      opt.textContent = names[code];
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
    localStorage.setItem('simy-lang', lang);
    load(lang, apply);
  }

  /* ── Inject minimal CSS for switcher ────────────────────────── */
  function injectCSS() {
    var style = document.createElement('style');
    style.textContent =
      '.lang-switcher{position:relative;margin-left:8px}' +
      '.lang-btn{display:flex;align-items:center;gap:6px;background:none;border:none;color:#5a5a56;cursor:pointer;font-family:inherit;font-size:0.75rem;font-weight:400;padding:4px 8px;border-radius:6px;transition:background 0.15s}' +
      '.lang-btn:hover{background:rgba(0,0,0,0.04)}' +
      '.lang-btn svg{opacity:0.6}' +
      '.lang-dropdown{display:none;position:absolute;top:100%;right:0;margin-top:8px;background:#fff;border:1px solid #e0e0dc;border-radius:10px;box-shadow:0 8px 32px rgba(0,0,0,0.08);padding:6px;min-width:140px;z-index:100}' +
      '.lang-dropdown.open{display:block}' +
      '.lang-option{display:block;width:100%;text-align:left;background:none;border:none;padding:8px 14px;font-size:0.8rem;color:#333;cursor:pointer;border-radius:6px;font-family:inherit;transition:background 0.12s}' +
      '.lang-option:hover{background:#f5f5f3}' +
      '[dir="rtl"] .lang-dropdown{right:auto;left:0}' +
      '[dir="rtl"] .lang-option{text-align:right}';
    document.head.appendChild(style);
  }

  /* ── Init ───────────────────────────────────────────────────── */
  function init() {
    injectCSS();
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
    if (lang !== DEFAULT) {
      load(lang, apply);
    } else {
      // Still apply to set display name
      load(DEFAULT, function (dict) {
        var display = document.getElementById('langDisplay');
        if (display) display.textContent = (dict._meta || {}).name || 'English';
      });
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
