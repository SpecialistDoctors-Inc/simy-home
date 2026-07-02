var BASIC_AUTH_ENABLED = false;
var EXPECTED_AUTH = 'Basic ';

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
