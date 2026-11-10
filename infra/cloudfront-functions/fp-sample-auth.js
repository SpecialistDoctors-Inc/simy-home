// BEGIN FP SAMPLE AUTH: protect HTML, bundles and every sample object before cache lookup.
var SAMPLE_AUTH_SHA256 = '7f11803dcd14ed10e97d3365e49e7f4288fab15f7d3bd3fd17435a50b7b55907';
function protectFpSample(request) {
  var decoded;
  try { decoded = decodeURIComponent(request.uri); } catch (_) { return {statusCode:400,statusDescription:'Bad Request'}; }
  var segments = [];
  decoded.split('/').forEach(function(part) { if (part === '..') segments.pop(); else if (part && part !== '.') segments.push(part); });
  var path = '/' + segments.join('/');
  if (path !== '/samples' && path.indexOf('/samples/') !== 0) return null;
  var auth = request.headers.authorization;
  var crypto = require('crypto');
  if (!auth || crypto.createHash('sha256').update(auth.value).digest('hex') !== SAMPLE_AUTH_SHA256) {
    return {statusCode:401,statusDescription:'Unauthorized',headers:{
      'www-authenticate':{value:'Basic realm="SIMY sample", charset="UTF-8"'},
      'cache-control':{value:'no-store'},
      'x-robots-tag':{value:'noindex, nofollow, noarchive'}
    }};
  }
  if (path === '/samples/fp-management') request.uri = '/samples/fp-management/index.html';
  else if (path === '/samples/fp-management/index.html' || path === '/samples/fp-management/app.js' || path === '/samples/fp-management/app.css') request.uri = path;
  else return {statusCode:404,statusDescription:'Not Found'};
  return request;
}
// END FP SAMPLE AUTH
