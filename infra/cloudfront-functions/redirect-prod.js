var BASIC_AUTH_ENABLED = false;
var EXPECTED_AUTH = 'Basic ';

function queryHas(request, key) {
  return request.querystring && request.querystring[key];
}

function queryToString(request, additions) {
  var querystring = request.querystring || {};
  var parts = [];
  for (var key in querystring) {
    if (!querystring.hasOwnProperty(key)) continue;
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

function maybeRedirectWithViewerRegion(request, host, uri) {
  if (queryHas(request, 'region') || queryHas(request, 'lang')) return null;
  if (!(uri === '/' || uri === '/index.html' || uri === '/compare.html' || uri === '/press-release.html' || uri === '/privacy.html' || uri === '/terms.html')) return null;

  var countryHeader = request.headers['cloudfront-viewer-country'];
  var region = countryHeader ? regionFromCountry(countryHeader.value) : '';
  if (!region) return null;

  var normalizedUri = uri === '/index.html' ? '/' : uri;
  return {
    statusCode: 302,
    statusDescription: 'Found',
    headers: { location: { value: 'https://' + host + normalizedUri + queryToString(request, { region: region }) } }
  };
}

function handler(event) {
  var request = event.request;

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

  var uri = request.uri;
  var host = request.headers.host ? request.headers.host.value : '';
  var viewerRegionRedirect = maybeRedirectWithViewerRegion(request, host, uri);
  if (viewerRegionRedirect) return viewerRegionRedirect;

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
      headers: { location: { value: 'https://' + host + '/' } }
    };
  }

  // Keep the alternate homepage preview under /newpage/.
  if (uri === '/newpage') {
    return {
      statusCode: 301,
      statusDescription: 'Moved Permanently',
      headers: { location: { value: 'https://' + host + '/newpage/' } }
    };
  }

  if (uri === '/newpage/index.html') {
    return {
      statusCode: 301,
      statusDescription: 'Moved Permanently',
      headers: { location: { value: 'https://' + host + '/newpage/' } }
    };
  }

  if (uri === '/newpage/') {
    request.uri = '/newpage/index.html';
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
