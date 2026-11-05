"""Local container smoke: render, JS error, overflow, and rejected external I/O."""
import io,json,os,signal,time,zipfile
from pathlib import Path
from render import digest,render

signal.signal(signal.SIGALRM,lambda *_: os._exit(124))
signal.alarm(120)
package='34567890-1234-4234-8234-123456789abc'
output=Path('/output')
results=[]
for scenario,body,expected in [
    ('valid','<h1>Isolated preview</h1><p>Local static content</p>',True),
    ('page-error','<h1>JS error</h1><script>throw new Error("expected-render-error")</script>',False),
    ('overflow','<h1>Overflow</h1><div style="width:2000px">Too wide</div>',False),
    ('external-blocked','<h1>Blocked resource</h1><img src="http://169.254.169.254/latest/meta-data/"><script src="https://example.invalid/blocked.js"></script>',False),
]:
    html='<!doctype html><html><head><title>Isolated preview</title><meta name="viewport" content="width=device-width"></head><body>'+body+'</body></html>'
    source={'index.html':html.encode()}
    records=[{'path':p,'sha256':digest(v),'size':len(v)} for p,v in sorted(source.items())]
    source_hash=digest(json.dumps(records,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
    metadata={'schema_version':1,'source_commit':'a'*40,'operation_id':package,'source_sha256':source_hash,'version':source_hash}
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as archive:
        for path,data in source.items(): archive.writestr(path,data)
        archive.writestr('version.json',json.dumps(metadata))
    data=stream.getvalue()
    job={'site_id':'smoke','operation_id':'23456789-1234-4234-8234-123456789abc','validation_id':'c'*64,'artifact_sha256':digest(data),'source_commit':'a'*40,'package_operation_id':package,'deadline':time.time()+25}
    report,screenshots=render(data,job)
    directory=output if scenario=='valid' else output/scenario
    directory.mkdir(parents=True,exist_ok=True)
    (directory/'report.json').write_text(json.dumps(report,indent=2))
    for name,value in screenshots.items(): (directory/(name+'.png')).write_bytes(value)
    if report['verified'] is not expected: raise AssertionError('unexpected_'+scenario+'_result')
    if scenario=='external-blocked' and not all(state['blocked_request_count']>=2 for state in report['viewports']):
        raise AssertionError('external_request_was_not_rejected')
    results.append({'scenario':scenario,'verified':report['verified'],'expected':expected,'viewports':[{'name':s['name'],'ok':s['ok'],'errors':s['errors'],'blocked_request_count':s['blocked_request_count']} for s in report['viewports']]})
(output/'smoke-results.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results))
