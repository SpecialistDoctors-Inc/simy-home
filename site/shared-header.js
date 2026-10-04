/* Progressive enhancement only: all destinations and disclosures exist in raw HTML. */
(() => {
  const header = document.querySelector('.simy-header');
  if (!header) return;
  const disclosures = [...header.querySelectorAll('details')];
  const close = (details, restore = false) => {
    details.open = false;
    details.querySelector('summary').setAttribute('aria-expanded', 'false');
    if (restore) details.querySelector('summary').focus();
  };
  for (const details of disclosures) {
    const summary = details.querySelector('summary');
    summary.setAttribute('aria-expanded', String(details.open));
    details.addEventListener('toggle', () => {
      summary.setAttribute('aria-expanded', String(details.open));
      if (details.open) {
        for (const other of disclosures) {
          if (other !== details && !other.contains(details) && !details.contains(other)) close(other);
        }
      }
    });
    details.addEventListener('keydown', event => {
      if (event.key === 'Escape' && details.open) {
        event.stopPropagation(); event.preventDefault(); close(details, true);
      }
    });
    details.addEventListener('focusout', () => {
      requestAnimationFrame(() => { if (!details.contains(document.activeElement)) close(details); });
    });
  }
  document.addEventListener('pointerdown', event => {
    for (const details of disclosures) if (!details.contains(event.target)) close(details);
  });
  header.addEventListener('click', event => {
    const link = event.target.closest('a');
    if (link) for (const details of disclosures) close(details);
  });
  matchMedia('(min-width: 1400px)').addEventListener('change', () => disclosures.forEach(d => close(d)));

  // Only legacy query-translated pages need runtime labels. Static locale pages
  // keep their authored language regardless of browser/storage preferences.
  const configurations = JSON.parse(header.querySelector('[data-sh-config]').textContent);
  const update = () => {
    const lang = document.documentElement.lang;
    const config = configurations[lang];
    if (!config) return;
    header.dataset.shLocale = lang;
    for (const el of header.querySelectorAll('[data-sh-label]')) el.textContent = config.labels[el.dataset.shLabel];
    for (const el of header.querySelectorAll('[data-sh-link]')) {
      const key = el.dataset.shLink;
      const url = new URL(config.urls[key], location.origin);
      // Explicit region remains the user's account context; do not infer a plan.
      const region = new URLSearchParams(location.search).get('region');
      if (url.hostname === 'app.simy.one' && region && /^[a-z]{2}$/i.test(region)) url.searchParams.set('region', region.toLowerCase());
      el.setAttribute('href', url.origin === location.origin ? url.pathname + url.search + url.hash : url.href);
      if (key.startsWith('locale-')) {
        if (key === `locale-${lang}`) el.setAttribute('aria-current', 'true');
        else el.removeAttribute('aria-current');
      }
    }
    for (const nav of header.querySelectorAll('[role="navigation"]')) nav.setAttribute('aria-label', config.labels.navigation);
    header.querySelector('.sh-mobile > summary').setAttribute('aria-label', config.labels.menu);
    header.querySelector('.sh-language > summary').setAttribute('aria-label', `${config.labels.language}: ${config.labels.current}`);
  };
  if (Object.keys(configurations).length) {
    update();
    new MutationObserver(update).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
  }
})();
