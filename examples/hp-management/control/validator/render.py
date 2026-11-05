"""Secretless static artifact renderer. Transfer capabilities never enter the page."""
from __future__ import annotations
import hashlib
import http.server
import io
import json
import os
from pathlib import Path
import re
import signal
import stat
import tempfile
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
import zipfile

MAX_FILE = 10 * 1024 * 1024
MAX_TOTAL = 50 * 1024 * 1024
MAX_TRANSPORT = 60 * 1024 * 1024
ALLOWED = {'.html','.css','.js','.json','.png','.jpg','.jpeg','.webp','.gif','.svg','.ico','.txt','.xml','.woff','.woff2','.ttf','.pdf','.webmanifest'}


class RenderError(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unpack(data, root, expected_sha, source_commit, package_operation_id=None):
    if not isinstance(data, bytes) or len(data) > MAX_TRANSPORT or digest(data) != expected_sha:
        raise RenderError('artifact_hash_mismatch')
    files, total, names = {}, 0, {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        if not 2 <= len(infos) <= 1001:
            raise RenderError('artifact_file_count')
        for info in infos:
            name = info.filename
            parts = name.split('/')
            if not name or len(name) > 1024 or unicodedata.normalize('NFC', name) != name or any(c in name for c in '\\:\0') or any(ord(c)<32 for c in name) or any(not p or p in ('.','..') or (p.startswith('.') and p != '.well-known') for p in parts) or Path(name).suffix.lower() not in ALLOWED:
                raise RenderError('artifact_path_rejected')
            prefix=[]
            for part in parts:
                prefix.append(part)
                key='/'.join(prefix)
                if key.casefold() in names and names[key.casefold()] != key:
                    raise RenderError('artifact_case_collision')
                names[key.casefold()] = key
            if name in files or info.is_dir() or info.flag_bits & 1 or stat.S_IFMT(info.external_attr >> 16) not in (0,stat.S_IFREG) or info.file_size > MAX_FILE:
                raise RenderError('artifact_entry_rejected')
            total += info.file_size
            if total > MAX_TOTAL + 1024 * 1024:
                raise RenderError('artifact_size_rejected')
            files[name] = archive.read(info)
    if 'index.html' not in files or 'version.json' not in files:
        raise RenderError('artifact_required_files_missing')
    metadata=json.loads(files['version.json'])
    source=[{'path': p,'sha256':digest(v),'size':len(v)} for p,v in sorted(files.items()) if p != 'version.json']
    source_hash=digest(json.dumps(source,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
    if not isinstance(metadata,dict) or set(metadata)!={'schema_version','source_commit','operation_id','source_sha256','version'} or type(metadata.get('schema_version')) is not int or metadata.get('schema_version') != 1 or metadata.get('source_commit') != source_commit or metadata.get('source_sha256') != source_hash or metadata.get('version') != source_hash or (package_operation_id is not None and metadata['operation_id']!=package_operation_id):
        raise RenderError('artifact_source_metadata_mismatch')
    if root is not None:
        for name,value in files.items():
            path=Path(root)/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(value)
    return metadata


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None


def transfer(method,url,data=None,limit=MAX_TRANSPORT,content_type=None):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.amazonaws.com') or parsed.username or parsed.password or parsed.port not in (None,443) or parsed.fragment:
        raise RenderError('transfer_target_rejected')
    headers={'x-amz-expected-bucket-owner':'209300895845'}
    if content_type:
        headers['Content-Type']=content_type
    if method=='PUT':
        headers['If-None-Match']='*'
    request=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.build_opener(NoRedirect()).open(request,timeout=20) as response:
        content=response.read(limit+1)
        if response.status not in (200,204) or len(content)>limit:
            raise RenderError('transfer_failed')
        return content


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):
        pass
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        # Browser networking is also denied at the Playwright routing boundary.
        self.send_header('Content-Security-Policy', "connect-src 'none'; object-src 'none'; frame-src 'none'; worker-src 'none'; form-action 'none'")
        super().end_headers()


def render(data,job,browser_type=None):
    """Render only localhost, at two fixed viewports; never run source processes."""
    from playwright.sync_api import sync_playwright
    deadline=job['deadline']
    if deadline <= time.time() or deadline > time.time()+900:
        raise RenderError('validation_deadline_invalid')
    with tempfile.TemporaryDirectory(prefix='hp-render-') as temporary:
        metadata=unpack(data,temporary,job['artifact_sha256'],job['source_commit'],job['package_operation_id'])
        handler=lambda *args,**kwargs: Handler(*args,directory=temporary,**kwargs)
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
        server.daemon_threads=True
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        origin='http://127.0.0.1:'+str(server.server_port)
        screenshots={}
        states=[]
        try:
            with sync_playwright() as runtime:
                # Fargate's nonprivileged runtime cannot supply Chromium's user
                # namespace sandbox. The reviewed secretless task is the outer
                # isolation boundary; report this limitation without ambiguity.
                browser=(browser_type or runtime.chromium).launch(headless=True,chromium_sandbox=False)
                try:
                    for name,width,height in [('desktop',1440,1000),('mobile',390,844)]:
                        if time.time()>=deadline:
                            raise RenderError('validation_deadline_exceeded')
                        context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1,service_workers='block',accept_downloads=False)
                        page=context.new_page()
                        errors=[]
                        blocked=[]
                        def route(request_route):
                            target=urllib.parse.urlsplit(request_route.request.url)
                            if target.scheme=='http' and target.hostname=='127.0.0.1' and target.port==server.server_port and not target.username and not target.password:
                                request_route.continue_()
                            else:
                                blocked.append(request_route.request.url[:200])
                                request_route.abort('blockedbyclient')
                        context.route('**/*',route)
                        context.route_web_socket(re.compile('.*'),lambda socket: socket.close())
                        page.on('pageerror',lambda error: errors.append(str(error)[:500]))
                        page.on('console',lambda message: errors.append(message.text[:500]) if message.type=='error' else None)
                        page.on('response',lambda response: errors.append('http_'+str(response.status)) if response.status>=400 else None)
                        response=page.goto(origin+'/index.html',wait_until='networkidle',timeout=min(30000,max(1,int((deadline-time.time())*1000))))
                        page.evaluate('document.fonts.ready')
                        page.wait_for_timeout(200)
                        metrics=page.evaluate('({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,height:document.body?.getBoundingClientRect().height||0,title:document.title,text:document.body?.innerText?.trim().length||0})')
                        screenshots[name]=page.screenshot(full_page=True,animations='disabled',timeout=10000)
                        ok=response is not None and response.status==200 and metrics['height']>0 and metrics['text']>0 and metrics['scrollWidth']<=width+1 and not errors and not blocked
                        states.append({'name':name,'width':width,'height':height,'ok':ok,'metrics':metrics,'errors':errors[:20],'blocked_request_count':len(blocked),'screenshot_sha256':digest(screenshots[name]),'screenshot_size':len(screenshots[name])})
                        context.close()
                finally:
                    browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
    report={'schema_version':1,'kind':'browser-validation','site_id':job['site_id'],'operation_id':job['operation_id'],
        'validation_id':job['validation_id'],'artifact_sha256':job['artifact_sha256'],'source_commit':job['source_commit'],
        'source_sha256':metadata['source_sha256'],'verified':all(state['ok'] for state in states),'viewports':states}
    report['chromium_os_sandbox']=False
    return report,screenshots


def main():
    job=json.loads(os.environ['HP_VALIDATION_JOB'])
    allowed={'site_id','operation_id','validation_id','artifact_sha256','source_commit','package_operation_id','artifact_get_url','output_put_urls','deadline'}
    if not isinstance(job,dict) or set(job)!=allowed or set(job['output_put_urls'])!={'desktop','mobile','report'}:
        raise RenderError('validation_job_invalid')
    remaining=int(job['deadline']-time.time())
    if not 0<remaining<=600:
        raise RenderError('validation_deadline_invalid')
    # A stuck browser or hostile page cannot outlive the sealed task deadline.
    # This exits only this worker process; no shared processes are signalled.
    signal.signal(signal.SIGALRM,lambda *_: os._exit(124))
    signal.alarm(remaining)
    data=transfer('GET',job['artifact_get_url'])
    report,screenshots=render(data,job)
    for name,content in screenshots.items():
        if len(content)>8*1024*1024:
            raise RenderError('screenshot_size_exceeded')
        transfer('PUT',job['output_put_urls'][name],content,0,'image/png')
    transfer('PUT',job['output_put_urls']['report'],json.dumps(report,sort_keys=True,separators=(',',':')).encode(),0,'application/json')


if __name__=='__main__':
    try:
        main()
    except Exception as error:
        # Do not log presigned capability URLs or the full job environment.
        print('browser_validation_failed:'+type(error).__name__,flush=True)
        raise SystemExit(1)
