// Preserve the explicit test choice from the live marketing pages through their
// signup and HP links, including the locale and billing-cycle selections.
(() => {
  const modes = new URL(location.href).searchParams.getAll("checkout_mode");
  const mode = modes.length === 1 && modes[0] === "sandbox" ? "sandbox" : "invalid";

  function preserveMode(link) {
    const target = new URL(link.href);
    const webSignup = target.origin === "https://app.simy.one" && /^\/signup\/?$/.test(target.pathname);
    const homeSignup = target.origin === location.origin &&
      (target.pathname.endsWith("/") || target.pathname.endsWith(".html")) &&
      !/^\/(?:api|auth|assets)\/|^\/auth-callback\.html$/.test(target.pathname);
    if (!webSignup && !homeSignup) return;
    target.searchParams.set("checkout_mode", mode);
    link.href = target.href;
  }

  const preserveLinks = () => {
    if (modes.length) document.querySelectorAll("a[href]").forEach(preserveMode);
  };
  if (modes.length) {
    preserveLinks();
    document.addEventListener("DOMContentLoaded", preserveLinks, { once: true });
    for (const type of ["click", "auxclick", "contextmenu"]) {
      document.addEventListener(type, (event) => {
        const link = event.target.closest?.("a[href]");
        if (link) preserveMode(link);
      }, true);
    }
  }

  // Native details keep navigation available even without JavaScript.

  const header = document.querySelector('.simy-header');
  if (!header) return;
  const menu = header.querySelector('.sh-menu');
  const mobile = window.matchMedia('(max-width: 960px)');
  const syncMenu = () => { menu.open = !mobile.matches; };
  header.dataset.enhanced = '';
  syncMenu();
  mobile.addEventListener('change', syncMenu);
  const labels = {en: 'English', ja: '日本語', hi: 'हिन्दी', es: 'Español', fr: 'Français', 'zh-Hans': '简体中文'};
  const languageLabels = {en: 'Language', ja: '言語', es: 'Idioma', fr: 'Langue', hi: 'भाषा', 'zh-Hans': '语言'};
  const accountLabels = {
    en: ['Sign up', 'Log in'], ja: ['新規登録', 'ログイン'],
    es: ['Registrarse', 'Iniciar sesión'], fr: ["S’inscrire", 'Se connecter'],
    hi: ['साइन अप', 'लॉग इन'], 'zh-Hans': ['注册', '登录']
  };
  const syncLocale = () => {
    const locale = document.documentElement.lang;
    if (!labels[locale]) return;
    const signup = header.querySelector('[data-new-account-signup]');
    if (signup) {
      signup.textContent = accountLabels[locale][0];
      const url = new URL(signup.href);
      url.searchParams.set('lang', locale);
      url.searchParams.set('locale', locale);
      signup.href = url.href;
    }
    const login = header.querySelector('.sh-login');
    if (login && Object.values(accountLabels).some(copy => copy[1] === login.textContent.trim())) {
      login.textContent = accountLabels[locale][1];
    }
    const summary = header.querySelector('.sh-language summary');
    const code = locale === 'zh-Hans' ? 'ZH' : locale.toUpperCase();
    summary.setAttribute('aria-label', `${code}: ${labels[locale]} (${languageLabels[locale]})`);
    summary.lastChild.textContent = ` ${locale === 'zh-Hans' ? 'ZH' : locale.toUpperCase()}`;
    header.querySelectorAll('.sh-language a').forEach(link => {
      if (link.lang === locale) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    header.querySelector('.sh-google-play').href = (locale === 'ja' ? '/download.html' : `/download/${locale.toLowerCase()}.html`) + '#android';
    const home = locale === 'en' ? '/' : `/${locale}.html`;
    const homeHref = locale === 'en' ? '/?locale=en' : home;
    header.querySelector('.sh-brand').href = homeHref;
    if (!header.querySelector('.sh-pricing').hasAttribute('data-service-pricing')) header.querySelector('.sh-pricing').href = homeHref + '#pricing';
    header.querySelectorAll('.sh-navigation a:not(.sh-store)').forEach(link => {
      const url = new URL(link.href);
      if (url.origin !== location.origin) return;
      if (url.pathname.startsWith('/download')) url.pathname = locale === 'ja' ? '/download.html' : `/download/${locale.toLowerCase()}.html`;
      else if (url.hash && !link.hasAttribute('data-service-pricing')) {
        url.pathname = home;
        if (locale === 'en') url.searchParams.set('locale', 'en');
      }
      else if (url.pathname.includes('/pharmaceutical-companies/')) url.pathname = locale === 'ja' ? '/for/pharmaceutical-companies/' : `/for/${locale.toLowerCase()}/pharmaceutical-companies/`;
      else if (url.pathname.includes('/financial-planners/')) url.pathname = locale === 'ja' ? '/for/financial-planners/' : `/for/${locale.toLowerCase()}/financial-planners/`;
      else if (url.pathname.startsWith('/for/') && url.pathname.includes('engineers')) url.pathname = locale === 'ja' ? '/for/engineers/' : `/for/${locale.toLowerCase()}/engineers/`;
      else if (['/for/', '/for/en/'].includes(url.pathname)) url.pathname = locale === 'ja' ? '/for/' : '/for/en/';
      else if (url.pathname.startsWith('/guides/')) url.pathname = locale === 'ja' ? '/guides/index.html' : `/guides/${locale.toLowerCase()}/index.html`;
      if (url.searchParams.has('lang')) url.searchParams.set('lang', locale);
      link.href = url.pathname + url.search + url.hash;
    });
    preserveLinks();
  };
  // Sticky headers wrap as the viewport or text size changes.
  const updateOffset = () => document.documentElement.style.setProperty('--simy-header-offset', `${Math.ceil(header.getBoundingClientRect().height) + 16}px`);
  updateOffset();
  new ResizeObserver(updateOffset).observe(header);
  window.addEventListener('load', () => {
    updateOffset();
    if (location.hash) {
      let id;
      try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
      document.getElementById(id)?.scrollIntoView();
    }
  }, {once: true});
  syncLocale();
  new MutationObserver(syncLocale).observe(document.documentElement, {attributes: true, attributeFilter: ['lang']});
  const menus = [...header.querySelectorAll('.sh-dropdown')];
  const closeOthers = (except) => menus.forEach(menu => {
    if (menu !== except) menu.open = false;
  });
  menus.forEach(menu => {
    menu.addEventListener('toggle', () => {
      if (menu.open) closeOthers(menu);
    });
    menu.addEventListener('focusout', () => {
      setTimeout(() => {
        if (!menu.contains(document.activeElement)) menu.open = false;
      });
    });
  });
  document.addEventListener('pointerdown', event => {
    if (!header.contains(event.target)) { closeOthers(); if (mobile.matches) menu.open = false; }
  });
  menu.addEventListener('toggle', () => { if (mobile.matches) closeOthers(); });
  // Escape closes the innermost header menu regardless of where focus moved.
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const opened = header.querySelector('.sh-dropdown[open]');
    if (opened) {
      opened.open = false;
      opened.querySelector('summary').focus();
    } else if (mobile.matches && menu.open) {
      menu.open = false;
      menu.querySelector('.sh-menu-toggle').focus();
    } else return;
    event.preventDefault();
    event.stopPropagation();
  }, true);
  menu.addEventListener('focusout', () => {
    setTimeout(() => { if (mobile.matches && !menu.contains(document.activeElement)) menu.open = false; });
  });
  header.addEventListener('click', event => {
    if (event.target.closest('a')) { closeOthers(); if (mobile.matches) menu.open = false; }
  });
})();
