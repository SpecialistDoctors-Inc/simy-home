/* An isolated, opt-in Turnstile demonstration. Never used to authorize scans or forms. */
(function () {
  'use strict';
  const section = document.querySelector('#cloudflare-experience');
  if (!section) return;
  const start = section.querySelector('[data-experience-start]');
  const mount = section.querySelector('[data-experience-widget]');
  const status = section.querySelector('[data-experience-status]');
  const result = section.querySelector('[data-experience-result]');
  let sdk, widget, generation = 0;
  function load() {
    if (window.turnstile) return Promise.resolve(window.turnstile);
    if (!sdk) sdk = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      const timer = setTimeout(() => fail(), 20000);
      function fail() { clearTimeout(timer); script.remove(); reject(Error('load')); }
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
      script.async = true;
      script.onload = () => { clearTimeout(timer); window.turnstile ? resolve(window.turnstile) : fail(); };
      script.onerror = fail;
      document.head.append(script);
    }).catch(error => { sdk = undefined; throw error; });
    return sdk;
  }
  start.addEventListener('click', async () => {
    const current = ++generation;
    start.disabled = true;
    result.hidden = true;
    status.textContent = 'Cloudflareの確認画面を読み込んでいます…';
    const message = value => { if (current === generation) { status.textContent = value; result.hidden = true; } };
    try {
      const turnstile = await load();
      if (current !== generation) return;
      if (widget !== undefined) turnstile.remove(widget);
      mount.hidden = false;
      status.textContent = '下のCloudflareの画面で、チェックをお試しください。';
      widget = turnstile.render(mount, {
        // Official forced-interaction test key. A demonstration, not real bot protection.
        sitekey: '3x00000000000000000000FF',
        theme: 'light', size: mount.clientWidth < 300 ? 'compact' : 'flexible', language: 'ja',
        action: 'simy_experience', 'response-field': false, retry: 'never',
        callback: () => {
          if (current !== generation) return;
          status.textContent = 'チェック後の画面を体験できました。';
          result.hidden = false;
        },
        'error-callback': () => { message('確認画面を表示できませんでした。「もう一度体験する」でお試しください。'); return true; },
        'expired-callback': () => message('体験の有効時間が過ぎました。もう一度お試しいただけます。'),
        'timeout-callback': () => message('確認の時間が過ぎました。もう一度お試しいただけます。')
      });
      start.textContent = 'もう一度体験する';
    } catch {
      status.textContent = 'Cloudflareに接続できませんでした。通信環境をご確認のうえ、もう一度お試しください。';
      start.textContent = 'もう一度体験する';
    } finally { if (current === generation) start.disabled = false; }
  });
})();
