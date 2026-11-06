"""Loopback-only fixed-route fake-host preview. Never serves arbitrary paths."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
ROUTES = {'/': (ROOT / 'output/playwright/host.html', 'text/html; charset=utf-8'), '/publish.html': (ROOT / 'dist/publish.html', 'text/html; charset=utf-8'), '/harness.js': (ROOT / 'output/playwright/harness.js', 'text/javascript; charset=utf-8')}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        target = ROUTES.get(urlsplit(self.path).path)
        if not target:
            self.send_error(404)
            return
        data = target[0].read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', target[1])
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, *args):
        pass

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 0), Handler)
    print('http://127.0.0.1:' + str(server.server_port), flush=True)
    server.serve_forever()
