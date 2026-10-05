/* Native details keep navigation available even without JavaScript. */
(() => {
  const header = document.querySelector('.simy-header');
  if (!header) return;
  const labels = {en: 'English', ja: '日本語', hi: 'हिन्दी', es: 'Español', fr: 'Français', 'zh-Hans': '简体中文'};
  const syncLocale = () => {
    const locale = document.documentElement.lang;
    if (!labels[locale]) return;
    const summary = header.querySelector('.sh-language summary');
    summary.setAttribute('aria-label', `Language: ${labels[locale]}`);
    summary.lastChild.textContent = ` ${locale === 'zh-Hans' ? 'ZH' : locale.toUpperCase()}`;
    header.querySelectorAll('.sh-language a').forEach(link => {
      if (link.lang === locale) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    const home = locale === 'en' ? '/' : `/${locale}.html`;
    header.querySelector('.sh-brand').href = home;
    header.querySelector('.sh-pricing').href = home + '#pricing';
    header.querySelectorAll('.sh-navigation a').forEach(link => {
      const url = new URL(link.href);
      if (url.hash) url.pathname = home;
      else if (url.pathname.startsWith('/for/')) url.pathname = (locale === 'ja' ? '/for/' : '/for/en/') + (url.pathname.includes('engineers') ? 'engineers/' : '');
      else if (url.pathname.startsWith('/guides/')) url.pathname = locale === 'ja' ? '/guides/' : `/guides/${locale.toLowerCase()}/`;
      else if (url.pathname.startsWith('/download')) url.pathname = locale === 'ja' ? '/download.html' : `/download/${locale.toLowerCase()}.html`;
      if (url.searchParams.has('lang')) url.searchParams.set('lang', locale);
      link.href = url.pathname + url.search + url.hash;
    });
  };
  syncLocale();
  new MutationObserver(syncLocale).observe(document.documentElement, {attributes: true, attributeFilter: ['lang']});
  const menus = [...header.querySelectorAll('details')];
  const closeOthers = (except) => menus.forEach(menu => {
    if (menu !== except) menu.open = false;
  });
  menus.forEach(menu => {
    menu.addEventListener('toggle', () => {
      if (menu.open) closeOthers(menu);
    });
    menu.addEventListener('keydown', event => {
      if (event.key === 'Escape' && menu.open) {
        menu.open = false;
        menu.querySelector('summary').focus();
        event.stopPropagation();
      }
    });
    menu.addEventListener('focusout', () => {
      setTimeout(() => {
        if (!menu.contains(document.activeElement)) menu.open = false;
      });
    });
  });
  document.addEventListener('pointerdown', event => {
    if (!header.contains(event.target)) closeOthers();
  });
  header.addEventListener('click', event => {
    if (event.target.closest('a')) closeOthers();
  });
})();
