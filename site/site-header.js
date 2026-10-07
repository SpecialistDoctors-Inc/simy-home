/* Native details keep navigation available even without JavaScript. */
(() => {
  const header = document.querySelector('.simy-header');
  if (!header) return;
  const menu = header.querySelector('.sh-menu');
  const mobile = window.matchMedia('(max-width: 960px)');
  // Read the rendered CSS layout, including zoom and fractional container widths.
  const isMobile = () => getComputedStyle(menu.querySelector('.sh-menu-toggle')).display !== 'none';
  let lastMobile = null;
  const syncMenu = () => {
    const compact = isMobile();
    if (lastMobile === compact) return;
    const toggle = menu.querySelector('.sh-menu-toggle');
    const focused = document.activeElement;
    // Move focus before closing/hiding its control; never steal focus from the page.
    if (compact && menu.contains(focused) && focused !== toggle) toggle.focus();
    menu.open = !compact;
    if (!compact && focused === toggle) {
      header.querySelector('.sh-navigation summary, .sh-navigation a')?.focus();
    }
    lastMobile = compact;
  };
  header.dataset.enhanced = '';
  syncMenu();
  mobile.addEventListener('change', syncMenu);
  const labels = {en: 'English', ja: '日本語', hi: 'हिन्दी', es: 'Español', fr: 'Français', 'zh-Hans': '简体中文'};
  const syncLocale = () => {
    const locale = document.documentElement.lang;
    if (!labels[locale]) return;
    header.querySelectorAll('[data-header-label]').forEach(label => {
      label.textContent = locale === 'ja' ? label.dataset.labelJa : label.dataset.labelEn;
    });
    header.querySelectorAll('[data-aria-en]').forEach(control => {
      control.setAttribute('aria-label', locale === 'ja' ? control.dataset.ariaJa : control.dataset.ariaEn);
    });
    const summary = header.querySelector('.sh-language summary');
    summary.setAttribute('aria-label', `${locale === 'ja' ? '言語' : 'Language'}: ${labels[locale]}`);
    summary.lastChild.textContent = ` ${locale === 'zh-Hans' ? 'ZH' : locale.toUpperCase()}`;
    header.querySelectorAll('.sh-language a').forEach(link => {
      if (link.lang === locale) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    header.querySelector('.sh-google-play').href = (locale === 'ja' ? '/download.html' : `/download/${locale.toLowerCase()}.html`) + '#android';
    const home = locale === 'en' ? '/' : `/${locale}.html`;
    header.querySelector('.sh-brand').href = home;
    header.querySelector('.sh-pricing').href = home + '#pricing';
    header.querySelectorAll('.sh-navigation a:not(.sh-store)').forEach(link => {
      const url = new URL(link.href);
      if (url.origin !== location.origin) return;
      if (url.pathname.startsWith('/download')) url.pathname = locale === 'ja' ? '/download.html' : `/download/${locale.toLowerCase()}.html`;
      else if (url.hash) url.pathname = home;
      else if (url.pathname.includes('/financial-planners/')) url.pathname = locale === 'ja' ? '/for/financial-planners/' : `/for/${locale.toLowerCase()}/financial-planners/`;
      else if (url.pathname.includes('/sales/')) {
        url.pathname = locale === 'ja' ? '/for/sales/' : '/for/en/sales/';
        const label = link.querySelector('[data-header-label]');
        label.textContent = locale === 'ja' ? '営業' : (locale === 'en' ? 'For sales' : 'For sales (English)');
      }
      else if (url.pathname.startsWith('/for/')) url.pathname = url.pathname.includes('engineers') ? (locale === 'ja' ? '/for/engineers/' : `/for/${locale.toLowerCase()}/engineers/`) : (locale === 'ja' ? '/for/' : '/for/en/');
      else if (url.pathname.startsWith('/guides/')) url.pathname = locale === 'ja' ? '/guides/index.html' : `/guides/${locale.toLowerCase()}/index.html`;
      if (url.searchParams.has('lang')) url.searchParams.set('lang', locale);
      link.href = url.pathname + url.search + url.hash;
    });
  };
  // Sticky headers wrap as the viewport or text size changes.
  const updateOffset = () => document.documentElement.style.setProperty('--simy-header-offset', `${Math.ceil(header.getBoundingClientRect().height) + 16}px`);
  updateOffset();
  new ResizeObserver(() => {
    updateOffset();
    // A missed media-query notification must not leave keyboard focus hidden.
    if (lastMobile !== isMobile()) syncMenu();
  }).observe(header);
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
    if (!header.contains(event.target)) { closeOthers(); if (isMobile()) menu.open = false; }
  });
  menu.addEventListener('toggle', () => { if (isMobile()) closeOthers(); });
  // Keep navigation reachable and close the innermost menu with Escape.
  document.addEventListener('keydown', event => {
    // Safari can skip nested native summaries when tabbing from the outer one.
    if (event.key === 'Tab' && !event.shiftKey && isMobile() && menu.open
        && event.target === menu.querySelector('.sh-menu-toggle')) {
      const first = header.querySelector('.sh-navigation summary, .sh-navigation a');
      if (first) { first.focus(); event.preventDefault(); }
      return;
    }
    if (event.key !== 'Escape') return;
    const opened = header.querySelector('.sh-dropdown[open]');
    if (opened) {
      opened.open = false;
      opened.querySelector('summary').focus();
    } else if (isMobile() && menu.open) {
      menu.open = false;
      menu.querySelector('.sh-menu-toggle').focus();
    } else return;
    event.preventDefault();
    event.stopPropagation();
  }, true);
  menu.addEventListener('focusout', () => {
    setTimeout(() => { if (isMobile() && !menu.contains(document.activeElement)) menu.open = false; });
  });
  header.addEventListener('click', event => {
    if (event.target.closest('a')) { closeOthers(); if (isMobile()) menu.open = false; }
  });
})();
