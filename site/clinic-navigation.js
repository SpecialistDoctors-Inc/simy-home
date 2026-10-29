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
  // Styles, fonts and images can change layout after the browser first resolves a fragment.
  const initialHash = location.hash;
  let userMoved = false;
  const markMoved = () => { userMoved = true; };
  for (const name of ['wheel','touchstart','pointerdown','keydown']) window.addEventListener(name, markMoved, {once:true,passive:true});
  window.addEventListener('load', () => {
    measure();
    requestAnimationFrame(() => requestAnimationFrame(() => {
      if (!userMoved && initialHash && location.hash === initialHash) {
        let id; try { id = decodeURIComponent(initialHash.slice(1)); } catch { return; }
        document.getElementById(id)?.scrollIntoView({block:'start',behavior:'instant'});
      }
    }));
  }, {once:true});
  if ('ResizeObserver' in window) {
    const observer = new ResizeObserver(measure);
    if (header) observer.observe(header);
    observer.observe(nav);
  } else window.addEventListener('resize', measure, { passive: true });
})();
