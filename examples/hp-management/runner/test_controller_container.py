"""Linux-only controller/UID boundary smoke; no providers or network."""
import json, os, subprocess, tempfile, time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from agent import Agent
from agent_store import AgentStore
import test_ledger

SHA='a'*40
REQUEST={'site_id':'site','request_id':'11111111-1111-4111-8111-111111111111','revision':'1','outcome':'ok'}
BASE={'sha':SHA,'blob_sha':'b'*40,'content':{'notices':[{'id':'notice','title':'t','body':'old'}]}}

class Sheets:
 def snapshot(self): return {'requests':[REQUEST],'events':[]}
class GitHub: pass

def script(path, body):
 path.write_text('#!/bin/sh\n'+body); path.chmod(0o755)

def main():
 if os.getuid()!=0 or sys.platform!='linux': raise SystemExit('requires linux root controller')
 tmp=tempfile.mkdtemp(dir='/work')
 if True:
  root=Path(tmp); os.chmod(root,0o711); bind=root/'bin'; bind.mkdir(); os.chmod(bind,0o755)
  # Fake git creates a read-only clone, never contacts a remote.
  script(bind/'git', '''if [ "$1" = "rev-parse" ]; then echo '''+SHA+'''; exit 0; fi
for dest; do :; done; mkdir -p "$dest/examples/sample-clinic/content" "$dest/examples/sample-clinic/tests"
cat > "$dest/examples/sample-clinic/content/clinic.json" <<'EOF'
{"notices":[{"id":"notice","title":"t","body":"old"}]}
EOF
touch "$dest/examples/sample-clinic/build.mjs" "$dest/examples/sample-clinic/tests/x.test.mjs"''')
  script(bind/'node','exit 0')
  script(bind/'fake-codex', '''if echo "$*" | grep -q output-schema; then echo '{"type":"item.completed","item":{"type":"agent_message","text":"{\\"approved\\":true,\\"findings\\":[]}"}}'; exit 0; fi
python3 - <<'PY'
import json
p='examples/sample-clinic/content/clinic.json'; v=json.load(open(p)); v['notices'][0]['body']='new'; v['changeRequest']={'id':'11111111-1111-4111-8111-111111111111','revision':1}; open(p,'w').write(json.dumps(v))
PY''')
  os.environ['PATH']=str(bind)+':'+os.environ['PATH']
  config={'site':test_ledger.LedgerTestCase().config(),'intake_start_at':'2026-11-02T00:00:00Z','notice_id':'notice','work_directory':str(root/'work'),'worker_uid':1000,'worker_home':'/home/node','codex_binary':str(bind/'fake-codex')}
  store=AgentStore(root/'state.sqlite3'); agent=Agent(config,store,Sheets(),GitHub())
  job=root/'work'/'job'; job.mkdir(mode=0o711)
  try: record=agent.start_worker(('site',REQUEST['request_id'],1),REQUEST,BASE,job)
  except Exception:
   print((job/'clone.log').read_text()); raise
  for _ in range(50):
   if (job/'child/result.json').exists(): break
   time.sleep(.1)
  try: candidate=agent.worker_result(job)
  except Exception:
   print((job/'child/result.json').read_text())
   print((job/'control/private/worker.log').read_text()); raise
  assert candidate['notices'][0]['body']=='new'
  # The controller has no DAC override: worker-owned process records must be
  # readable through the inherited controller group for safe recovery.
  process_record=job/'child'/'codex-process.json'
  assert process_record.stat().st_uid==1000 and process_record.stat().st_gid==0
  assert process_record.stat().st_mode & 0o777 == 0o640
  assert json.loads(process_record.read_text())['identity']
  proof=agent.verify_candidate(('site',REQUEST['request_id'],1),BASE,candidate,job); assert proof['root_pristine_tests']
  review=agent.review_candidate(('site',REQUEST['request_id'],1),BASE,candidate,REQUEST,job); assert review=={'approved':True,'findings':[]}
  # Restart reconciliation: same receipts must not launch fake Codex again.
  assert agent.verify_candidate(('site',REQUEST['request_id'],1),BASE,candidate,job)==proof
  assert agent.review_candidate(('site',REQUEST['request_id'],1),BASE,candidate,REQUEST,job)==review
  print(json.dumps({'ok':True,'pid':record['pid'],'identity':bool(record['identity'])}))
  store.close()

if __name__=='__main__': main()
