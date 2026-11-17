/* Shared homepage entry policy. Country hints are optional; timezone is an OS
   signal, not an IP-location claim. Explicit language URLs remain crawlable. */
(() => {
  'use strict';
  const languages = new Set(['en', 'ja', 'es', 'fr', 'hi', 'zh-Hans']);
  const normalize = value => {
    const text = String(value || '').trim().toLowerCase();
    if (text === 'zh' || /^zh-(?:cn|sg|hans)(?:-|$)/.test(text)) return 'zh-Hans';
    const base = text.split('-')[0];
    return languages.has(base) ? base : null;
  };
  const countryLanguage = country => ({JP:'ja',FR:'fr',ES:'es',MX:'es',AR:'es',CO:'es',CL:'es',PE:'es',IN:'hi',CN:'zh-Hans',US:'en',GB:'en',AU:'en',NZ:'en'})[String(country || '').toUpperCase()] || null;
  const timezoneCountry = zone => ({'Asia/Tokyo':'JP','Europe/Paris':'FR','Europe/Madrid':'ES','Atlantic/Canary':'ES','America/Mexico_City':'MX','America/Bogota':'CO','America/Lima':'PE','America/Santiago':'CL','Asia/Kolkata':'IN','Asia/Calcutta':'IN','Asia/Shanghai':'CN','Asia/Chongqing':'CN','Europe/London':'GB','America/New_York':'US','America/Chicago':'US','America/Denver':'US','America/Los_Angeles':'US','Australia/Sydney':'AU','Pacific/Auckland':'NZ'})[zone] || null;
  const home = locale => locale === 'en' ? '/?locale=en' : '/' + locale + '.html';
  const savedLanguage = storage => {
    try {
      const legacy = normalize(storage.getItem('simy-home-locale'));
      if (legacy) return legacy;
      for (const key of ['simy-lang', 'simy-language']) {
        if (storage.getItem(key + '-source') === 'manual') {
          const value = normalize(storage.getItem(key));
          if (value) return value;
        }
      }
      if (storage.getItem('simy-region-source') === 'manual') return countryLanguage(storage.getItem('simy-region'));
    } catch (_) { /* A blocked store must not block navigation. */ }
    return null;
  };
  const resolve = ({url, storage, country, timezone, browserLanguages = []}) => {
    const explicit = normalize(url.searchParams.get('lang')) || normalize(url.searchParams.get('locale'));
    if (explicit) return explicit;
    const path = /^\/(ja|es|fr|hi|zh-Hans)\.html$/.exec(url.pathname);
    if (path) return path[1];
    const saved = savedLanguage(storage);
    if (saved) return saved;
    const region = countryLanguage(url.searchParams.get('region'));
    if (region) return region;
    const geographic = countryLanguage(country) || countryLanguage(timezoneCountry(timezone));
    if (geographic) return geographic;
    for (const value of browserLanguages) {
      const match = normalize(value);
      if (match) return match;
    }
    return 'en';
  };
  const persist = locale => {
    try {
      for (const key of ['simy-home-locale', 'simy-lang', 'simy-language']) window.localStorage.setItem(key, locale);
      window.localStorage.setItem('simy-lang-source', 'manual');
      window.localStorage.setItem('simy-language-source', 'manual');
    } catch (_) { /* Explicit hrefs also work without storage. */ }
  };
  window.SIMY_LOCALE_NAVIGATION = Object.freeze({normalize, home, resolve});
  const url = new URL(window.location.href);
  if (url.pathname === '/' || url.pathname === '/index.html') {
    let storage, timezone;
    try { storage = window.localStorage; } catch (_) { storage = null; }
    try { timezone = Intl.DateTimeFormat().resolvedOptions().timeZone; } catch (_) { timezone = ''; }
    const locale = resolve({url, storage, timezone, country:document.documentElement.dataset.viewerCountry,
      browserLanguages:navigator.languages || [navigator.language]});
    if (locale !== 'en') {
      const target = new URL(url);
      target.pathname = '/' + locale + '.html';
      target.searchParams.delete('lang');
      window.location.replace(target.href);
    }
  }
  const bindChoices = () => {
    // Same-site home links on an explicitly English page must also retain the
    // choice when storage is blocked. Hash-only links already retain the URL.
    if (document.documentElement.lang === 'en') {
      for (const link of document.querySelectorAll('a[href]')) {
        const destination = new URL(link.href, window.location.href);
        if (destination.origin === window.location.origin && ['/', '/index.html'].includes(destination.pathname)) {
          destination.pathname = '/';
          destination.searchParams.set('locale', 'en');
          link.href = destination.pathname + destination.search + destination.hash;
        }
      }
    }
    for (const link of document.querySelectorAll('[data-locale-option]')) {
      const locale = normalize(link.dataset.localeOption);
      if (!locale) continue;
      const destination = new URL(link.href, window.location.href);
      if (locale === 'en' && destination.origin === window.location.origin && ['/', '/index.html'].includes(destination.pathname)) {
        destination.pathname = '/';
        destination.searchParams.delete('lang');
        destination.searchParams.set('locale', 'en');
        link.href = destination.pathname + destination.search + destination.hash;
      }
      link.addEventListener('click', () => persist(locale));
    }
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bindChoices, {once:true});
  else bindChoices();
})();
