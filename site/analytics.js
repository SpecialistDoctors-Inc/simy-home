/* SIMY site analytics: GA4 loaded only after cookie consent, plus funnel events.
   Shared by the home page, /guides/* and /download.html. Consent key matches the
   older static pages (localStorage "simy-cookies" = "1" | "0"). */
(function () {
  var GA_ID = 'G-SBLYYNMSJW';
  var KEY = 'simy-cookies';
  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = window.gtag || gtag;

  function store(get, value) {
    try { return get ? localStorage.getItem(KEY) : localStorage.setItem(KEY, value); } catch (e) { return null; }
  }
  function loadGA() {
    if (document.getElementById('ga-script')) return;
    var s = document.createElement('script');
    s.id = 'ga-script'; s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    document.head.appendChild(s);
    window.gtag('js', new Date());
    window.gtag('config', GA_ID);
  }
  window.loadGA = window.loadGA || loadGA;
  function track(name, params) {
    if (store(true) !== '1') return;
    window.gtag('event', name, params || {});
  }
  window.simyTrack = track;

  var TEXT = {
    ja: ['サイトの改善のために Cookie を使います。', 'プライバシーポリシー', '拒否する', '同意する'],
    en: ['We use cookies to improve this site. See our ', 'Privacy Policy', 'Decline', 'Accept'],
    es: ['Usamos cookies para mejorar este sitio. Consulta la ', 'Política de privacidad', 'Rechazar', 'Aceptar'],
    fr: ['Nous utilisons des cookies pour améliorer ce site. Voir la ', 'Politique de confidentialité', 'Refuser', 'Accepter'],
    hi: ['हम इस साइट को बेहतर बनाने के लिए कुकीज़ का उपयोग करते हैं। देखें ', 'गोपनीयता नीति', 'अस्वीकार करें', 'स्वीकार करें'],
    zh: ['我们使用 Cookie 来改进本网站。请参阅', '隐私政策', '拒绝', '同意']
  };
  function lang() {
    var l = (document.documentElement.lang || 'en').toLowerCase();
    var q = (location.search.match(/[?&]lang=([^&]+)/) || [])[1];
    if (q) l = decodeURIComponent(q).toLowerCase();
    if (l.indexOf('zh') === 0) return 'zh';
    return TEXT[l.slice(0, 2)] ? l.slice(0, 2) : 'en';
  }
  function banner() {
    if (store(true) !== null || document.getElementById('simy-consent')) return;
    var t = TEXT[lang()];
    var b = document.createElement('div');
    b.id = 'simy-consent';
    b.setAttribute('role', 'region');
    b.setAttribute('aria-label', 'Cookie');
    b.style.cssText = 'position:fixed;left:12px;right:12px;bottom:12px;z-index:9999;max-width:720px;margin:0 auto;display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;justify-content:space-between;padding:12px 16px;background:#fff;color:#111;border:1px solid #111;border-radius:12px;box-shadow:4px 4px 0 #111;font:14px/1.6 "Helvetica Neue",Arial,"Hiragino Sans",sans-serif';
    var p = document.createElement('p');
    p.style.cssText = 'margin:0;flex:1 1 260px';
    p.appendChild(document.createTextNode(t[0]));
    var a = document.createElement('a');
    a.href = '/privacy.html'; a.textContent = t[1]; a.style.color = '#235db8';
    p.appendChild(a);
    var row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:8px';
    function btn(label, ok) {
      var x = document.createElement('button');
      x.type = 'button'; x.textContent = label;
      x.style.cssText = ok
        ? 'min-height:40px;padding:0 16px;border-radius:8px;border:1px solid #111;background:#235db8;color:#fff;font:inherit;font-weight:700;cursor:pointer'
        : 'min-height:40px;padding:0 16px;border-radius:8px;border:1px solid #c9c7c4;background:#fff;color:#111;font:inherit;cursor:pointer';
      x.addEventListener('click', function () {
        store(false, ok ? '1' : '0');
        b.parentNode && b.parentNode.removeChild(b);
        if (ok) { loadGA(); track('consent_granted'); }
      });
      return x;
    }
    row.appendChild(btn(t[2], false));
    row.appendChild(btn(t[3], true));
    b.appendChild(p); b.appendChild(row);
    document.body.appendChild(b);
  }

  function page() { return location.pathname.replace(/\/$/, '/index') || '/'; }
  function onClick(e) {
    var el = e.target && e.target.closest ? e.target.closest('a,button') : null;
    if (!el) return;
    var href = el.getAttribute('href') || '';
    var label = (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60);
    var base = { page_path: page(), link_text: label };
    if (/app\.simy\.one\/signup/.test(href)) {
      var c = (href.match(/utm_content=([^&]+)/) || [])[1] || '';
      base.cta_position = c;
      track('sign_up_click', base);
    } else if (/app\.simy\.one\/(login|\?|$)/.test(href)) {
      track('login_click', base);
    } else if (el.hasAttribute('data-dl') || /\/downloads\/simy-cli\//.test(href)) {
      base.platform = el.getAttribute('data-dl') || (/windows/.test(href) ? 'win' : 'mac');
      track('file_download', base);
    } else if (/apps\.apple\.com/.test(href)) {
      track('app_store_click', base);
    } else if (/\/download\.html/.test(href)) {
      track('download_page_click', base);
    } else if (/\/guides\//.test(href)) {
      base.guide = (href.match(/\/guides\/([^.\/]+)/) || [])[1] || 'index';
      track('guide_click', base);
    } else if (/^mailto:/.test(href)) {
      track('contact_click', base);
    }
  }
  function onToggle(e) {
    var d = e.target;
    if (!d || d.tagName !== 'DETAILS' || !d.open) return;
    var s = d.querySelector('summary');
    track(d.closest('.faq') ? 'faq_open' : 'fold_open', { page_path: page(), item: s ? s.textContent.replace(/\s+/g, ' ').trim().slice(0, 80) : '' });
  }
  var marks = { 25: false, 50: false, 75: false, 90: false };
  var ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(function () {
      ticking = false;
      var h = document.documentElement.scrollHeight - window.innerHeight;
      if (h <= 0) return;
      var pct = Math.round((window.scrollY / h) * 100);
      Object.keys(marks).forEach(function (k) {
        if (!marks[k] && pct >= Number(k)) { marks[k] = true; track('scroll_depth', { page_path: page(), percent: Number(k) }); }
      });
    });
  }

  if (store(true) === '1') loadGA();
  document.addEventListener('click', onClick, true);
  document.addEventListener('toggle', onToggle, true);
  window.addEventListener('scroll', onScroll, { passive: true });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', banner);
  else banner();
})();
