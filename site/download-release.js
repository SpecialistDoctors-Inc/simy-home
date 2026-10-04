/* A failed latest lookup retains the dated, visible static download. */
(function () {
  'use strict';
  function load(key, path, platform, arch, ext) {
    var link = document.querySelector('[data-dl="' + key + '"]');
    var meta = document.querySelector('[data-meta="' + key + '"]');
    var notice = document.querySelector('[data-release-status="' + key + '"]');
    if (!link || !meta || !notice || !window.fetch) return;
    fetch(path, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('Manifest unavailable');
      return r.json();
    }).then(function (manifest) {
      if (!manifest || !/^\d+\.\d+\.\d+$/.test(manifest.version) || !Array.isArray(manifest.artifacts)) return;
      var artifact = manifest.artifacts.find(function (a) {
        return a && a.platform === platform && a.arch === arch;
      });
      if (!artifact || typeof artifact.url !== 'string') return;
      var url = new URL(artifact.url);
      var prefix = '/downloads/simy-cli/' + (key === 'win' ? 'windows/' : '') + manifest.version + '/';
      if (url.origin !== 'https://simy.one' || !url.pathname.startsWith(prefix) || !url.pathname.endsWith(ext) || url.search || url.hash || url.username || url.password) return;
      link.href = url.href;
      meta.textContent = 'v' + manifest.version + ' · ' + ext;
      notice.textContent = notice.getAttribute('data-release-current');
    }).catch(function () { /* The visible fallback explains how to retry. */ });
  }
  load('mac', '/downloads/simy-cli/latest.json', 'darwin', 'arm64', '.dmg');
  load('win', '/downloads/simy-cli/windows/latest.json', 'win32', 'x64', '.exe');
})();
