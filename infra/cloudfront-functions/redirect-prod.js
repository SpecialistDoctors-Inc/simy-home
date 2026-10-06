var BASIC_AUTH_ENABLED = false;
var EXPECTED_AUTH = 'Basic ';

function queryHas(request, key) {
  return request.querystring && request.querystring[key];
}

function queryToString(request, additions) {
  var querystring = request.querystring || {};
  var parts = [];
  for (var key in querystring) {
    if (!Object.prototype.hasOwnProperty.call(querystring, key)) continue;
    var item = querystring[key];
    if (item.multiValue) {
      for (var i = 0; i < item.multiValue.length; i++) {
        parts.push(encodeURIComponent(key) + '=' + encodeURIComponent(item.multiValue[i].value || ''));
      }
    } else if (item.value === '') {
      parts.push(encodeURIComponent(key));
    } else {
      parts.push(encodeURIComponent(key) + '=' + encodeURIComponent(item.value || ''));
    }
  }
  for (var addKey in additions) {
    if (!additions.hasOwnProperty(addKey)) continue;
    parts.push(encodeURIComponent(addKey) + '=' + encodeURIComponent(additions[addKey]));
  }
  return parts.length ? '?' + parts.join('&') : '';
}

function regionFromCountry(country) {
  var c = (country || '').toUpperCase();
  var map = {
    US: 'us',
    JP: 'jp',
    GB: 'gb',
    DE: 'de',
    FR: 'fr',
    CA: 'ca',
    IN: 'in',
    KR: 'kr',
    BR: 'br',
    MX: 'mx',
    ID: 'id',
    VN: 'vn',
    ES: 'es',
    IT: 'it',
    SA: 'sa',
    TW: 'tw',
    TH: 'th',
    MY: 'my',
    PH: 'ph'
  };
  return map[c] || '';
}

function regionFromAcceptLanguage(acceptLanguage) {
  var raw = (acceptLanguage || '').toLowerCase();
  if (!raw) return '';
  var first = raw.split(',')[0].split(';')[0].trim();
  if (first.indexOf('ja') === 0) return 'jp';
  if (first.indexOf('en-us') === 0 || first.indexOf('en') === 0) return 'us';
  if (first.indexOf('en-gb') === 0) return 'gb';
  if (first.indexOf('en-ca') === 0) return 'ca';
  if (first.indexOf('en-in') === 0) return 'in';
  if (first.indexOf('fr') === 0) return 'fr';
  if (first.indexOf('de') === 0) return 'de';
  if (first.indexOf('es-es') === 0) return 'es';
  if (first.indexOf('es') === 0) return 'mx';
  if (first.indexOf('it') === 0) return 'it';
  if (first.indexOf('ko') === 0) return 'kr';
  if (first.indexOf('pt') === 0) return 'br';
  if (first.indexOf('zh') === 0) return 'tw';
  if (first.indexOf('hi') === 0) return 'in';
  if (first.indexOf('ar') === 0) return 'sa';
  if (first.indexOf('vi') === 0) return 'vn';
  if (first.indexOf('th') === 0) return 'th';
  if (first.indexOf('id') === 0) return 'id';
  return '';
}

function maybeRedirectWithViewerRegion(request, host, uri) {
  if (queryHas(request, 'region') || queryHas(request, 'lang')) return null;
  if (!(uri === '/compare.html' || uri === '/press-release.html' || uri === '/privacy.html' || uri === '/terms.html')) return null;

  var countryHeader = request.headers['cloudfront-viewer-country'];
  var languageHeader = request.headers['accept-language'];
  var region = countryHeader ? regionFromCountry(countryHeader.value) : '';
  if (!region && languageHeader) region = regionFromAcceptLanguage(languageHeader.value);
  if (!region) return null;

  var normalizedUri = uri === '/index.html' ? '/' : uri;
  return {
    statusCode: 302,
    statusDescription: 'Found',
    headers: { location: { value: 'https://' + host + normalizedUri + queryToString(request, { region: region }) } }
  };
}

function homepageLanguageRedirect(request, host, uri) {
  var homepagePaths = { '/': true, '/index.html': true, '/ja.html': true, '/hi.html': true, '/es.html': true, '/fr.html': true, '/zh-Hans.html': true };
  if (!homepagePaths[uri]) return null;
  var item = request.querystring && request.querystring.lang;
  if (!item) return null;
  var language = (item.value || '').toLowerCase();
  var base = language.split('-')[0];
  var locale = ['en', 'ja', 'hi', 'es', 'fr'].indexOf(base) >= 0 ? base : '';
  if (['zh', 'zh-cn', 'zh-sg', 'zh-hans'].indexOf(language) >= 0) locale = 'zh-Hans';
  if (!locale) return null;
  var remaining = Object.create(null);
  for (var key in request.querystring) {
    if (Object.prototype.hasOwnProperty.call(request.querystring, key) && key !== 'lang') remaining[key] = request.querystring[key];
  }
  var path = locale === 'en' ? '/' : '/' + locale + '.html';
  return {
    statusCode: 301,
    statusDescription: 'Moved Permanently',
    headers: { location: { value: 'https://' + host + path + queryToString({ querystring: remaining }, {}) } }
  };
}

function handler(event) {
  var request = event.request;
  var uri = request.uri;

  if (BASIC_AUTH_ENABLED) {
    var headers = request.headers;
    if (!headers.authorization || headers.authorization.value !== EXPECTED_AUTH) {
      return {
        statusCode: 401,
        statusDescription: 'Unauthorized',
        headers: {
          'www-authenticate': { value: 'Basic realm="dev"' }
        }
      };
    }
  }

  var host = request.headers.host ? request.headers.host.value : '';
  var languageRedirect = homepageLanguageRedirect(request, host, uri);
  if (languageRedirect) return languageRedirect;

  var viewerRegionRedirect = maybeRedirectWithViewerRegion(request, host, uri);
  if (viewerRegionRedirect) return viewerRegionRedirect;

  // Keep the Universal Link callback URL stable for iOS while serving the
  // Safari fallback page when the app is not installed. This is an internal
  // rewrite, so its query string remains available to the user-initiated
  // custom-scheme link in the page.
  if (host.toLowerCase() === 'simy.one' &&
      (uri === '/app/auth/callback' || uri === '/app/auth/callback/' ||
      uri === '/dev-app/auth/callback' || uri === '/dev-app/auth/callback/' ||
      uri === '/stg-app/auth/callback' || uri === '/stg-app/auth/callback/')) {
    request.uri = '/auth-callback.html';
    return request;
  }

  if (uri === '/test' || uri === '/test/' || uri.startsWith('/test/')) {
    return {
      statusCode: 301,
      statusDescription: 'Moved Permanently',
      headers: { location: { value: 'https://' + host + '/' } }
    };
  }

  // /index.html -> / redirect
  if (uri === '/index.html') {
    return {
      statusCode: 301,
      statusDescription: 'Moved Permanently',
      headers: { location: { value: 'https://' + host + '/' + queryToString(request, {}) } }
    };
  }

  if (uri === '/old') {
    return {
      statusCode: 301,
      statusDescription: 'Moved Permanently',
      headers: { location: { value: 'https://' + host + '/old/' } }
    };
  }

  if (uri === '/old/') {
    request.uri = '/old/index.html';
    return request;
  }

  // The alternate homepage preview is now the production homepage.
  if (uri === '/newpage') {
    return {
      statusCode: 301,
      statusDescription: 'Moved Permanently',
      headers: { location: { value: 'https://' + host + '/' } }
    };
  }

  if (uri === '/newpage/' || uri === '/newpage/index.html') {
    return {
      statusCode: 301,
      statusDescription: 'Moved Permanently',
      headers: { location: { value: 'https://' + host + '/' } }
    };
  }

  // Occupation pages have stable directory URLs, independent of plan names.
  var occupationAliases = { '/engineers.html': '/for/engineers/', '/engineers-en.html': '/for/en/engineers/', '/for': '/for/', '/for/': '/for/', '/for.html': '/for/', '/for/index.html': '/for/' };
  var occupationPath = occupationAliases[uri];
  var occupation = uri.match(/^\/for\/(?:(?:en|es|fr|hi|zh-hans)\/)?[a-z][a-z0-9-]*(?:\/index\.html|\.html|\/)?$/);
  if (occupation && !occupationPath) occupationPath = uri.replace(/(?:\/index\.html|\.html|\/)$/, '') + '/';
  if (occupationPath) {
    if (uri !== occupationPath) {
      return {
        statusCode: 301,
        statusDescription: 'Moved Permanently',
        headers: { location: { value: 'https://' + host + occupationPath + queryToString(request, {}) } }
      };
    }
    request.uri = occupationPath + 'index.html';
    return request;
  }

  // Remove trailing slash (except root /)
  // e.g. /about/ -> /about.html
  if (uri !== '/' && uri.endsWith('/')) {
    var trimmed = uri.slice(0, -1);
    return {
      statusCode: 301,
      statusDescription: 'Moved Permanently',
      headers: { location: { value: 'https://' + host + trimmed + '.html' } }
    };
  }

  // /pricing, /compare, /about etc. -> redirect to .html
  if (uri !== '/' && !uri.includes('.')) {
    return {
      statusCode: 301,
      statusDescription: 'Moved Permanently',
      headers: { location: { value: 'https://' + host + uri + '.html' } }
    };
  }

  return request;
}
