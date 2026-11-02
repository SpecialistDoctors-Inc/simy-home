#!/usr/bin/env python3
"""Independent, single-replica HP intake and delivery service.

No Codex desktop/thread wakeups. Only trusted private configuration decides
providers, repository, notice scope and recipients. Production is deliberately
left at the existing exact-artifact, protected human approval boundary.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL
from agent_store import AgentStore
from codex_worker import atomic_json, process_identity, validate_candidate, run_owned
try:
    from provider_errors import EffectNotStarted
except ImportError:  # root owns the shared provider error module during integration
    class EffectNotStarted(RuntimeError): pass
from ledger import canon, digest, require


def timestamp(value):
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    require(parsed.tzinfo is not None,'timezone_required')
    return parsed


def request_key(row):return row['site_id'],row['request_id'],int(row['revision'])


class Agent:
    def __init__(self, config, store, sheets, github, worker=None, verifier=None, reviewer=None, clock=time.time, mail=None):
        self.config,self.store,self.sheets,self.github=config,store,sheets,github
        self.clock=clock
        self.mail=mail
        self.active_notice=None
        self.site=config['site']
        self.start_at=timestamp(config['intake_start_at'])
        self.work=Path(config['work_directory']).resolve()
        self.work.mkdir(parents=True,exist_ok=True,mode=0o711)
        require(not self.work.is_symlink() and self.work.stat().st_uid==os.getuid(),'unsafe_work_directory')
        os.chmod(self.work,0o711)
        self.worker=worker or self.start_worker
        self.verifier=verifier or self.verify_candidate
        self.reviewer=reviewer or self.review_candidate
        self.boot_id=str(uuid4())
        self.store.execute('config',{'config':self.site})
        self.store.connection.execute('INSERT INTO agent_boots VALUES(?,?,?,?,?)',(
            self.boot_id,datetime.now(timezone.utc).isoformat(),os.getpid(),os.getppid(),canon(sys.argv)))
        self.active_admission=None

    @contextmanager
    def sheet_admission(self, sheet_id, key):
        require(self.active_admission==(sheet_id,key),'sheet_effect_not_admitted')
        yield

    @contextmanager
    def notice_admission(self, key):
        require(self.active_notice==key,'notice_effect_not_admitted')
        yield

    def reconcile_notice(self, claim):
        notices=self.store.execute('outbox-query',claim)['notifications']
        for notice in notices:
            if notice['state'] not in {'sending','ambiguous'}:continue
            require(self.mail is not None,'mail_connection_required')
            receipt=self.mail.find_notice(notice['envelope'],notice['key'])
            require(receipt is not None,'notice_requires_reconciliation')
            self.store.execute('outbox-record',{'key':notice['key'],'token':claim['token'],
                'state':'provider_accepted',**receipt})

    def locate(self, snapshot, key):
        # Do not parse malformed revisions belonging to unrelated requests.
        rows=[r for r in snapshot['requests'] if r.get('site_id')==key[0] and r.get('request_id')==key[1] and int(r['revision'])==key[2]]
        require(len(rows)==1,'request_row_missing_or_duplicate')
        row=rows[0]
        latest=max(int(r['revision']) for r in snapshot['requests'] if r.get('request_id')==key[1] and r.get('site_id')==key[0])
        require(latest==key[2],'request_superseded_on_sheet')
        events=[e for e in snapshot['events'] if e['request_id']==key[1] and int(e['revision'])==key[2]]
        require(not any(e['kind']=='request_cancelled' for e in events),'request_cancelled_on_sheet')
        return row

    def discover(self,snapshot):
        seen={}
        for event in snapshot['events']:
            key=None
            try:
                eid=str(UUID(event['event_id']))
                require(eid not in seen,'duplicate_sheet_event'); seen[eid]=True
                if event['kind']!='ready_for_dev' or timestamp(event['occurred_at'])<self.start_at:continue
                key=(self.site['site_id'],event['request_id'],int(event['revision']))
                existing=self.store.job(key)
                if existing and existing['stage'] in {'awaiting_approval','stopped','needs_input','worker_interrupted','provider_reconciliation_required'}: continue
                self.store.observe(event)
                row=self.locate(snapshot,key)
                result=self.store.execute('ingest',{'request':row})
                if result['state'] in {'queued','working','preview_ready'}: self.store.add_job(row)
            except (KeyError,TypeError,ValueError) as exc:
                if isinstance(exc,ValueError) and str(exc) in {'request_conflict','sheet_event_mutated'}:
                    # Quarantine only this request; a malformed/conflicting
                    # sibling must not freeze unrelated in-flight work.
                    if key is not None and self.store.job(key):
                        job=self.store.job(key)
                        self.store.save(key,'needs_input',{**job['data'],'sheet_recovery':str(exc)},None)
                self.store.reject_event(event if isinstance(event,dict) else {'raw':str(event)},str(exc) if isinstance(exc,ValueError) else 'invalid_sheet_event')
                continue

    def lease(self,key,token):
        data={'site_id':key[0],'request_id':key[1],'revision':key[2]}
        if token:
            try:
                self.store.execute('renew',{**data,'token':token,'ttl':3600})
                return {**data,'token':token}
            except ValueError as exc:
                if str(exc)!='lease_unavailable':raise
        claim=self.store.execute('claim',{**data,'owner':'hp-independent-agent','ttl':3600})
        return {**data,'token':claim['token']}

    def live_input(self,key,claim):
        snapshot=self.sheets.snapshot()
        request=self.locate(snapshot,key)
        status=self.store.execute('status',claim)
        require(digest({**request,'revision':str(key[2])})==status['digest'],'request_changed_on_sheet')
        with self.store.transaction(): self.store.leased(claim)
        return request

    def perform(self,claim,name,payload,call,reconcile):
        effect=self.store.effect(claim,name,payload)
        if effect['state']=='observed':return effect['receipt']
        if effect['state']=='new':
            try: receipt=call()
            except EffectNotStarted:
                self.store.abandon_not_started(effect['key'])
                raise
        else:
            receipt=reconcile()
            require(receipt is not None,'effect_requires_reconciliation')
        self.store.record_effect(effect['key'],receipt)
        return receipt

    def start_worker(self,key,request,base,job_dir):
        require(sys.platform=='linux' and os.getuid()==0,'isolated_linux_controller_required')
        uid=self.config['worker_uid']
        require(type(uid) is int and uid>0,'nonroot_worker_required')
        # The job root and control tree are controller-owned.  The worker is
        # given one writable child tree only; it cannot replace state, process
        # identity, logs, provider configuration, or controller inputs.
        os.chmod(job_dir, 0o711)
        control=job_dir/'control'; control.mkdir(mode=0o711, exist_ok=False); os.chmod(control,0o711)
        private=control/'private'; private.mkdir(mode=0o700)
        child=job_dir/'child'; child.mkdir(mode=0o2750, exist_ok=False); os.chmod(child,0o2750)
        os.chown(child,uid,0)
        source=job_dir/'source'
        run_owned(['git','-c','credential.helper=','clone','--quiet','--depth','1','--branch','dev',
            'https://github.com/'+self.site['repo']+'.git',str(source)],job_dir,job_dir/'clone.log',job_dir/'clone-process.json',timeout=120)
        sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
        require(sha==base['sha'],'base_moved_before_worker')
        for path in [source,*source.rglob('*')]:
            if path.is_symlink(): raise ValueError('source_symlink_rejected')
            os.chmod(path,0o755 if path.is_dir() else 0o644)
        input_path=control/'worker-input.json'
        atomic_json(input_path,{'request':request,'base':base,'notice_id':self.config['notice_id'],
            'codex_binary':self.config.get('codex_binary','codex')})
        os.chmod(input_path,0o444)
        # Provider secrets and state remain root-only.  Codex auth is the sole
        # read-only user mount the worker receives through its own home.
        worker_home=self.config.get('worker_home','/home/node')
        require(isinstance(worker_home,str) and worker_home.startswith('/'),'invalid_worker_home')
        env={k:v for k,v in os.environ.items() if k in {'PATH','LANG','LC_ALL'}}
        env.update({'HOME':worker_home,'CODEX_HOME':worker_home+'/.codex'})
        log=(private/'worker.log').open('w')
        process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('codex_worker.py')),
            '--input',str(input_path),'--source',str(source),'--workspace',str(child/'workspace'),
            '--result',str(child/'result.json')], cwd=child,stdout=log,stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,user=uid,group=uid,extra_groups=[],env=env)
        log.close()
        result={'pid':process.pid,'ppid':os.getpid(),'command':[sys.executable,'codex_worker.py','--input',str(input_path)],
                'started_at':datetime.now(timezone.utc).isoformat(),'identity':None}
        atomic_json(private/'worker-process.json',result)
        try: result['identity']=process_identity(process.pid)
        except subprocess.CalledProcessError: result['identity_state']='unavailable'
        else: result['identity_state']='recorded'
        atomic_json(private/'worker-process.json',result)
        return result

    def worker_result(self, job_dir):
        """Read only a bounded regular child receipt; all metadata is untrusted."""
        path=job_dir/'child'/'result.json'
        flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0)
        try: descriptor=os.open(path,flags)
        except FileNotFoundError:return None
        except OSError as exc: raise ValueError('worker_result_unsafe') from exc
        try:
            info=os.fstat(descriptor)
            require(stat.S_ISREG(info.st_mode),'worker_result_unsafe')
            require(info.st_size<=1_000_000,'worker_result_unsafe')
            raw=os.read(descriptor,1_000_001)
        finally: os.close(descriptor)
        try: result=json.loads(raw)
        except (UnicodeDecodeError,json.JSONDecodeError) as exc: raise ValueError('worker_result_invalid') from exc
        require(isinstance(result,dict) and result.get('state')=='success' and isinstance(result.get('content'),dict),'worker_result_invalid')
        return result['content']

    def worker_interruption(self,key,job,data,job_dir):
        worker=data.get('worker')
        if not isinstance(worker,dict):
            data['worker_recovery']={'state':'launch_record_missing'}
            self.store.save(key,'worker_interrupted',data,job['token']); return 'worker_interrupted'
        try: current=process_identity(worker['pid'])
        except (subprocess.CalledProcessError,ValueError): current=''
        if current and current==worker.get('identity'): return 'coding'
        data['worker_recovery']={'state':'process_not_running' if not current else 'identity_changed'}
        self.store.save(key,'worker_interrupted',data,job['token'])
        return 'worker_interrupted'

    def prepare_job_dir(self, job_dir):
        if job_dir.exists():
            info=job_dir.lstat()
            require(stat.S_ISDIR(info.st_mode) and not job_dir.is_symlink() and info.st_uid==os.getuid(),'unsafe_job_directory')
            return job_dir
        job_dir.mkdir(mode=0o711)
        info=job_dir.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid==os.getuid(),'unsafe_job_directory')
        return job_dir

    def verify_candidate(self,key,base,candidate,job_dir):
        """Rebuild and test a root-owned pristine copy; worker claims are ignored."""
        control=job_dir/'control'; private=control/'private'; source=job_dir/'source'; verify=private/'verification'
        receipt=private/'verification-receipt.json'
        fingerprint=hashlib.sha256(canon({'base':base['sha'],'candidate':candidate}).encode()).hexdigest()
        if receipt.exists():
            require(not receipt.is_symlink(),'verification_receipt_unsafe')
            saved=json.loads(receipt.read_text())
            require(saved=={'fingerprint':fingerprint,'root_pristine_tests':True},'verification_reconciliation_required')
            return saved
        require(source.is_dir() and not source.is_symlink() and not verify.exists(),'verification_source_invalid')
        shutil.copytree(source/'examples/sample-clinic',verify/'examples/sample-clinic',ignore=shutil.ignore_patterns('dist','node_modules'))
        content=verify/'examples/sample-clinic/content/clinic.json'
        atomic_json(content,candidate)
        env={k:v for k,v in os.environ.items() if k in {'PATH','LANG','LC_ALL','TMPDIR'}}
        run_owned(['node','examples/sample-clinic/build.mjs'],verify,private/'verify-build.log',private/'verify-build-process.json',env=env,timeout=120)
        tests=sorted(str(p.relative_to(verify)) for p in (verify/'examples/sample-clinic/tests').glob('*.test.mjs'))
        require(tests,'verification_tests_missing')
        run_owned(['node','--test',*tests],verify,private/'verify-tests.log',private/'verify-tests-process.json',env=env,timeout=120)
        proof={'fingerprint':fingerprint,'root_pristine_tests':True}
        atomic_json(receipt,proof)
        return proof

    def review_candidate(self,key,base,candidate,request,job_dir):
        """A second controller-launched, read-only Codex execution is required."""
        control=job_dir/'control'; private=control/'private'; review=control/'review'; receipt=private/'review-receipt.json'
        fingerprint=hashlib.sha256(canon({'base':base['sha'],'candidate':candidate,'request':request}).encode()).hexdigest()
        if receipt.exists():
            saved=json.loads(receipt.read_text())
            require(saved=={'fingerprint':fingerprint,'approved':True,'findings':[]},'review_reconciliation_required')
            return {'approved':True,'findings':[]}
        require(not review.exists(),'review_reconciliation_required')
        review.mkdir(mode=0o755); os.chmod(review,0o755)
        schema={'type':'object','properties':{'approved':{'type':'boolean'},'findings':{'type':'array','items':{'type':'string'}}},'required':['approved','findings'],'additionalProperties':False}
        atomic_json(review/'before.json',base['content']); atomic_json(review/'after.json',candidate)
        atomic_json(review/'request.json',request); atomic_json(review/'schema.json',schema)
        for path in review.iterdir(): os.chmod(path,0o644)
        uid=self.config['worker_uid']; home=self.config.get('worker_home','/home/node')
        env={k:v for k,v in os.environ.items() if k in {'PATH','LANG','LC_ALL'}}; env.update({'HOME':home,'CODEX_HOME':home+'/.codex'})
        prompt='Independently review before.json, after.json, and request.json. Only the configured notice body and changeRequest may change. Return the schema JSON; do not edit or use network.'
        run_owned([self.config.get('codex_binary','codex'),'exec','--ignore-user-config','--ephemeral','--skip-git-repo-check','--sandbox','read-only','-c','sandbox_workspace_write.network_access=false','-c','web_search="disabled"','-c','features.apps=false','--json','--output-schema',str(review/'schema.json'),'-'],review,private/'review.jsonl',private/'review-process.json',stdin=prompt,env=env,user=uid,group=uid,extra_groups=[],timeout=900)
        candidates=[]
        for line in (private/'review.jsonl').read_text().splitlines():
            try: value=json.loads(line)
            except json.JSONDecodeError: continue
            # `codex exec --json` returns the reviewer message in a completed
            # item event, not as a top-level review object.
            if isinstance(value,dict) and value.get('type')=='item.completed':
                item=value.get('item',{})
                text=item.get('text') if isinstance(item,dict) and item.get('type')=='agent_message' else None
                if isinstance(text,str):
                    try: value=json.loads(text)
                    except json.JSONDecodeError: continue
            if isinstance(value,dict) and set(value)=={'approved','findings'}: candidates.append(value)
        require(len(candidates)==1 and candidates[0]=={'approved':True,'findings':[]},'independent_review_rejected')
        atomic_json(receipt,{'fingerprint':fingerprint,'approved':True,'findings':[]})
        return candidates[0]

    def event(self,key,kind,proof):
        stable=f'hp-agent:{key[0]}:{key[1]}:{key[2]}:{kind}'
        return {'event_id':str(uuid5(NAMESPACE_URL,stable)),'request_id':key[1],'revision':str(key[2]),
            'occurred_at':datetime.now(timezone.utc).isoformat(),'actor':'developer:hp-independent-agent',
            'kind':kind,'body':canon(proof),'reply_to_event_id':'','event_idempotency_key':stable}

    def append(self,key,claim,event):
        stable=event['event_idempotency_key']
        def write():
            self.active_admission=(self.site['sheet_id'],stable)
            try:return self.sheets.append_event(event)
            finally:self.active_admission=None
        def reconcile():
            observed=self.sheets.find_event(stable)
            if observed is None:return None
            require(observed==event,'sheet_result_conflict')
            return {'event':observed,'reconciled':True}
        return self.perform(claim,'sheet:'+event['kind'],event,write,reconcile)

    def advance(self,job):
        key=request_key(job);data=job['data'];stage=job['stage']
        job_dir=self.prepare_job_dir(self.work/(key[1]+'-r'+str(key[2])))
        claim={'site_id':key[0],'request_id':key[1],'revision':key[2],'token':job['token']}
        # Admitted external effects may have completed before a crash. Reconcile
        # them before acquiring a replacement lease or accepting new revisions.
        if stage=='candidate' and self.store.row("SELECT key FROM agent_effects WHERE site_id=? AND state='admitted'",(key[0],)):
            args=(key[1],key[2],data['base']['sha'],data['base']['blob_sha'],data['candidate'])
            try:data['remote']=self.perform(claim,'candidate',data['candidate'],lambda:None,lambda:self.github.reconcile_candidate(*args))
            except ValueError as exc:
                if str(exc)!='effect_requires_reconciliation':raise
                data['provider_recovery']={'effect':'candidate','state':'remote_partial_or_absent'}
                self.store.save(key,'provider_reconciliation_required',data,job['token'])
                return 'provider_reconciliation_required'
            stage='ci'
            self.store.save(key,stage,data,job['token'])
        elif stage=='merge' and self.store.row("SELECT key FROM agent_effects WHERE site_id=? AND state='admitted'",(key[0],)):
            remote=data['remote']
            try:data['merge']=self.perform(claim,'merge',remote,lambda:None,lambda:self.github.reconcile_merge(remote['pr_number'],remote['head_sha']))
            except ValueError as exc:
                if str(exc)!='effect_requires_reconciliation':raise
                data['provider_recovery']={'effect':'merge','state':'remote_partial_or_absent'}
                self.store.save(key,'provider_reconciliation_required',data,job['token'])
                return 'provider_reconciliation_required'
            stage='deploy'
            self.store.save(key,stage,data,job['token'])
        elif stage=='results' and self.store.row("SELECT key FROM agent_effects WHERE site_id=? AND state='admitted'",(key[0],)):
            for event in data['events']:
                effect=self.store.row('SELECT state FROM agent_effects WHERE key=?',(digest({'request':key,'stage':'sheet:'+event['kind']}),))
                if effect and effect['state']=='admitted':self.append(key,claim,event)
        if stage=='notification':self.reconcile_notice(claim)
        claim=self.lease(key,job['token'])
        self.store.save(key,stage,data,claim['token'])
        request=self.live_input(key,claim)
        if stage=='queued':
            base=self.github.base()
            data['base']=base
            # Persist intent before starting. A crash before process recording
            # is fail-closed, not permission to launch another coding session.
            self.store.save(key,'worker_starting',data,claim['token'])
            data['worker']=self.worker(key,request,base,job_dir)
            self.store.save(key,'coding',data,claim['token'])
            return 'coding'
        if stage in {'worker_starting','coding'}:
            worker=data.get('worker')
            if not isinstance(worker,dict):
                return self.worker_interruption(key,job,data,job_dir)
            if not isinstance(worker.get('identity'),str) or not worker['identity']:
                data['worker_recovery']={'state':'launch_identity_unavailable'}
                self.store.save(key,'worker_interrupted',data,job['token'])
                return 'worker_interrupted'
            try:
                candidate=self.worker_result(job_dir)
                if candidate is None:return self.worker_interruption(key,job,data,job_dir)
                validate_candidate(data['base']['content'],candidate,request,self.config['notice_id'])
                data['candidate']=candidate
                data['local_proof']=self.verifier(key,data['base'],candidate,job_dir)
            except (ValueError,RuntimeError,OSError) as exc:
                # A failed/interrupted local verification is not safe to replay.
                # Park this request so independent requests can still advance.
                code=str(exc) if isinstance(exc,ValueError) and str(exc).replace('_','').isalnum() else type(exc).__name__
                data['verification_recovery']={'state':'failed_or_interrupted','code':code}
                self.store.save(key,'needs_input',data,None)
                return 'needs_input'
            # Worker-supplied test/review fields are intentionally ignored. The
            # accepted authority is the confined candidate shape only.
            try: data['independent_review']=self.reviewer(key,data['base'],candidate,request,job_dir)
            except (ValueError,RuntimeError) as exc:
                data['review_recovery']={'state':'rejected_or_interrupted','code':str(exc) or type(exc).__name__}
                self.store.save(key,'needs_input',data,None)
                return 'needs_input'
            self.store.save(key,'candidate',data,claim['token'])
            return 'candidate'
        if stage=='candidate':
            args=(key[1],key[2],data['base']['sha'],data['base']['blob_sha'],data['candidate'])
            data['remote']=self.perform(claim,'candidate',data['candidate'],lambda:self.github.ensure_candidate(*args),lambda:self.github.reconcile_candidate(*args))
            self.store.save(key,'ci',data,claim['token'])
            return 'ci'
        if stage=='ci':
            remote=data['remote']
            if self.github.readiness(remote['pr_number'],remote['head_sha']) is None:return 'ci'
            require(self.config.get('auto_merge_dev') is True,'dev_merge_not_enabled')
            self.store.save(key,'merge',data,claim['token'])
            return 'merge'
        if stage=='merge':
            remote=data['remote']
            data['merge']=self.perform(claim,'merge',remote,
                lambda:self.github.merge_dev(remote['pr_number'],remote['head_sha'],data['base']['sha']),
                lambda:self.github.reconcile_merge(remote['pr_number'],remote['head_sha']))
            self.store.save(key,'deploy',data,claim['token'])
            return 'deploy'
        if stage=='deploy':
            proof=self.github.read_deployment(data['merge']['merge_sha'],key[1],key[2],job_dir/'artifact')
            if proof is None:return 'deploy'
            self.live_input(key,claim)
            self.store.execute('preview',{**claim,**proof})
            data['preview']=proof
            data['events']=[self.event(key,'test_result',{'tests_passed':True,'reviewer':'Codex','source_sha':proof['source_sha'],'pr_url':data['remote']['pr_url']}),
                            self.event(key,'dev_preview_ready',proof)]
            self.store.save(key,'results',data,claim['token'])
            return 'results'
        if stage=='results':
            for event in data['events']:
                self.live_input(key,claim)
                self.append(key,claim,event)
            if self.config.get('mail_enabled') is True:
                self.store.save(key,'notification',data,claim['token'])
                return 'notification'
            data['notification_status']='disabled'
            self.store.execute('release',claim)
            self.store.save(key,'awaiting_approval',data,None)
            return 'awaiting_approval'
        if stage=='notification':
            require(self.mail is not None,'mail_connection_required')
            reserved=self.store.execute('outbox-reserve',{**claim,'kind':'preview_ready'})
            if reserved['state']=='reserved':
                self.live_input(key,claim)
                require(self.github.read_deployment(data['merge']['merge_sha'],key[1],key[2],job_dir/'artifact') is not None,
                    'notification_artifact_not_verified')
                admitted=self.store.execute('outbox-admit',{**claim,'kind':'preview_ready','key':reserved['key']})
                require(admitted['may_send'] is True,'notice_not_admitted')
                self.active_notice=reserved['key']
                try: receipt=self.mail.send_notice(admitted['envelope'],reserved['key'])
                except EffectNotStarted:
                    self.store.notification_not_started(reserved['key'],claim['token'])
                    raise
                finally:self.active_notice=None
                self.store.execute('outbox-record',{'key':reserved['key'],'token':claim['token'],'state':'provider_accepted',**receipt})
            data['notification_status']='provider_accepted'
            self.store.execute('release',claim)
            self.store.save(key,'awaiting_approval',data,None)
            return 'awaiting_approval'
        return stage

    def tick(self):
        with self.store.exclusive():
            # Reconcile in-progress effects before discovery can supersede them.
            rows=list(self.store.connection.execute("SELECT * FROM agent_jobs WHERE stage NOT IN ('awaiting_approval','stopped','needs_input') ORDER BY rowid"))
            active=[self.store.job(request_key(row)) for row in rows]
            if not self.store.row("SELECT key FROM agent_effects WHERE state='admitted' UNION ALL SELECT key FROM notifications WHERE state IN ('sending','ambiguous') LIMIT 1"):
                self.discover(self.sheets.snapshot())
                active=[self.store.job(request_key(row)) for row in self.store.connection.execute("SELECT * FROM agent_jobs WHERE stage NOT IN ('awaiting_approval','stopped','needs_input') ORDER BY rowid")]
            for job in active[:1]:
                try:return {'request_id':job['request_id'],'stage':self.advance(job)}
                except Exception as exc:
                    if isinstance(exc,EffectNotStarted):
                        self.store.save(request_key(job),'needs_input',{**job['data'],'provider_recovery':{'state':'not_started','code':str(exc) or 'effect_not_started'}},None)
                        return {'request_id':job['request_id'],'stage':'needs_input','error':str(exc) or 'effect_not_started'}
                    if isinstance(exc,ValueError) and str(exc) in {'request_superseded_on_sheet','request_cancelled_on_sheet','request_superseded','request_inactive'}:
                        self.store.save(request_key(job),'stopped',job['data'],None)
                        return {'request_id':job['request_id'],'stage':'stopped'}
                    code=str(exc) if isinstance(exc,ValueError) and str(exc).replace('_','').isalnum() else type(exc).__name__
                    self.store.set_error(request_key(job),code)
                    return {'request_id':job['request_id'],'stage':job['stage'],'error':code}
            return {'stage':'idle'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--db',type=Path,required=True)
    p.add_argument('--once',action='store_true')
    p.add_argument('--max-ticks',type=int)
    p.add_argument('--stop-after-stage')
    args=p.parse_args()
    os.umask(0o077)
    config=json.loads(args.config.read_text())
    interval=config.get('poll_seconds',60)
    require(type(interval) is int and 5<=interval<=3600,'invalid_poll_interval')
    from google_provider import GoogleSheets
    from github_provider import GitHub
    store=AgentStore(args.db)
    sheets=GoogleSheets(config['site'],config['google_credentials_file'],config['google_subject'],config['google_email'])
    token=Path(config['github_token_file']).read_text().strip()
    github=GitHub(token,config['site']['repo'],config['site']['content_path'],config['site']['dev_url'])
    mail=None
    if config.get('mail_enabled') is True:
        from gmail_provider import Gmail
        mail=Gmail(config['site'],config['google_credentials_file'],config['google_subject'],config['google_email'])
    agent=Agent(config,store,sheets,github,mail=mail)
    sheets.set_event_admission(agent.sheet_admission)
    if mail:mail.set_notice_admission(agent.notice_admission)
    print(canon({'event':'agent_started','boot_id':agent.boot_id,'at':datetime.now(timezone.utc).isoformat()}),flush=True)
    count=0
    try:
        while True:
            try:result=agent.tick()
            except Exception as exc:result={'stage':'intake_blocked','error':type(exc).__name__}
            print(canon({'event':'poll_completed','boot_id':agent.boot_id,**result}),flush=True)
            count+=1
            if args.once or (args.max_ticks and count>=args.max_ticks) or result.get('stage')==args.stop_after_stage:break
            time.sleep(interval)
    finally:store.close()
    return 0


if __name__=='__main__':raise SystemExit(main())
