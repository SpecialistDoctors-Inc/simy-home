/* A failed latest lookup retains the dated, visible static download. */
(function () {
  'use strict';
  // Bound both headers and body reads. Late replies cannot overwrite a retry.
  function request(path, attempt) {
    var controller = window.AbortController ? new window.AbortController() : null;
    var timer;
    var expired = new Promise(function (_, reject) {
      timer = setTimeout(function () {
        var error = new Error('Manifest timed out');
        error.retryable = true;
        reject(error);
        if (controller) controller.abort();
      }, 5000);
    });
    var read = Promise.resolve().then(function () {
      return fetch(path, { cache: 'no-store', signal: controller ? controller.signal : undefined });
    }).catch(function (error) {
      error.retryable = true;
      throw error;
    }).then(function (r) {
      if (!r.ok) {
        var error = new Error('Manifest unavailable');
        // A server-directed delay is left to the visible reload recovery path.
        error.retryable = r.status >= 500 && r.status <= 599 &&
          !(r.headers && r.headers.get('Retry-After'));
        throw error;
      }
      return r.json().catch(function (error) {
        // Body transport/decoding failures are transient; invalid JSON is not.
        if (error && error.name === 'TypeError') error.retryable = true;
        throw error;
      });
    });
    return Promise.race([read, expired]).then(function (manifest) {
      clearTimeout(timer);
      return manifest;
    }, function (error) {
      clearTimeout(timer);
      if (attempt === 0 && error.retryable) {
        return new Promise(function (resolve) { setTimeout(resolve, 250); }).then(function () {
          return request(path, 1);
        });
      }
      throw error;
    });
  }
  function load(key, path, platform, arch, ext) {
    var link = document.querySelector('[data-dl="' + key + '"]');
    var meta = document.querySelector('[data-meta="' + key + '"]');
    var notice = document.querySelector('[data-release-status="' + key + '"]');
    if (!link || !meta || !notice || !window.fetch) return;
    request(path, 0).then(function (manifest) {
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
