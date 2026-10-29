(() => {
  'use strict';
  const header = document.querySelector('.simy-header');
  const nav = document.querySelector('#main .care-nav');
  if (!nav) return;
  const measure = () => {
    document.documentElement.style.setProperty('--clinic-header-height', `${header?.getBoundingClientRect().height || 0}px`);
    document.documentElement.style.setProperty('--clinic-nav-height', `${nav.getBoundingClientRect().height}px`);
  };
  measure();
  if ('ResizeObserver' in window) {
    const observer = new ResizeObserver(measure);
    if (header) observer.observe(header);
    observer.observe(nav);
  } else window.addEventListener('resize', measure, { passive: true });
})();
