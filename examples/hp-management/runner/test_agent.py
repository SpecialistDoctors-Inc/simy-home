import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).parent))
from agent import Agent
from agent_store import AgentStore
from codex_worker import atomic_json,validate_candidate
import test_ledger


class Sheets:
    def __init__(self,row,event):self.rows=[row];self.events=[event];self.writes=0;self.uncertain=False
    def snapshot(self):return copy.deepcopy({'requests':self.rows,'events':self.events})
    def find_event(self,key):
        matches=[e for e in self.events if e['event_idempotency_key']==key]
        if len(matches)>1:raise ValueError('duplicate_event')
        return matches[0] if matches else None
    def append_event(self,event):
        assert self.find_event(event['event_idempotency_key']) is None
        self.events.append(copy.deepcopy(event));self.writes+=1
        if self.uncertain:self.uncertain=False;raise RuntimeError('response_lost')
        return {'event':event,'readback_verified':True}


class GitHub:
    def __init__(self):self.candidates=0;self.merges=0;self.proof=None;self.uncertain=False;self.merge_uncertain=False
    def base(self):return {'sha':'a'*40,'blob_sha':'b'*40,'content':{'name':'clinic','notices':[{'id':'notice','title':'Title','body':'original'}]}}
    def ensure_candidate(self,*args):
        self.candidates+=1
        self.proof={'pr_number':1,'head_sha':'c'*40,'pr_url':'https://github.com/owner/repo/pull/1'}
        if self.uncertain:raise RuntimeError('response_lost')
        return self.proof
    def reconcile_candidate(self,*args):return self.proof
    def readiness(self,*args):return {'head_sha':'c'*40}
    def merge_dev(self,*args):
        self.merges+=1
        if self.merge_uncertain:raise RuntimeError('response_lost')
        return {'merge_sha':'d'*40}
    def reconcile_merge(self,*args):return {'merge_sha':'d'*40} if self.merges else None
    def read_deployment(self,sha,request,revision,directory):
        return {'source_sha':sha,'artifact_id':'1','artifact_hash':'e'*64,'run_id':42,'run_attempt':1,
                'url':'https://dev.example','tests_passed':True,'files':{'index.html':'f'*64}}


class Mail:
    def __init__(self): self.sent=[]
    def send_notice(self,envelope,key):
        self.sent.append((copy.deepcopy(envelope),key))
        return {'provider_message_id':'mail-1','readback_verified':True}
    def find_notice(self,envelope,key):
        return {'provider_message_id':'mail-1','readback_verified':True} if self.sent else None


class AgentTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)
        self.now=[1000.0];self.store=AgentStore(self.path/'state.sqlite3',clock=lambda:self.now[0])
        fixture=test_ledger.LedgerTestCase()
        self.config={'site':fixture.config(),'intake_start_at':'2026-11-02T00:00:00Z','notice_id':'notice',
                     'work_directory':str(self.path/'work'),'auto_merge_dev':True}
        self.row=fixture.request()
        self.event={'event_id':str(uuid4()),'request_id':self.row['request_id'],'revision':'1','occurred_at':'2026-11-02T01:00:00Z',
                    'actor':'customer','kind':'ready_for_dev','body':'ready','reply_to_event_id':'','event_idempotency_key':'ready-1'}
        self.sheets=Sheets(self.row,self.event);self.github=GitHub();self.workers=0
        self.agent=Agent(self.config,self.store,self.sheets,self.github,worker=self.worker,verifier=self.verifier,reviewer=self.reviewer)
        self.key=(self.row['site_id'],self.row['request_id'],1)
    def worker(self,key,request,base,directory):
        self.workers+=1
        after=copy.deepcopy(base['content']);after['notices'][0]['body']='changed'
        after['changeRequest']={'id':request['request_id'],'revision':int(request['revision'])}
        child=directory/'child';child.mkdir(exist_ok=True)
        atomic_json(child/'result.json',{'state':'success','content':after,'tests_passed':False,
                    'independent_review':{'approved':False,'findings':['untrusted']}})
        return {'pid':123,'identity':'fake'}
    def verifier(self,key,base,candidate,directory):
        self.assertEqual('changed',candidate['notices'][0]['body'])
        return {'root_pristine_tests':True}
    def reviewer(self,key,base,candidate,request,directory): return {'approved':True,'findings':[]}
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def restart(self):
        self.store.close();self.store=AgentStore(self.path/'state.sqlite3',clock=lambda:self.now[0])
        self.agent=Agent(self.config,self.store,self.sheets,self.github,worker=self.worker,verifier=self.verifier,reviewer=self.reviewer)
    def until(self,stage):
        for _ in range(15):
            result=self.agent.tick()
            if result.get('error'):self.fail(str(result))
            if result['stage']==stage:return
        self.fail('stage not reached: '+stage)
    def test_full_pipeline_returns_exact_preview_and_replay_has_no_effect(self):
        self.until('awaiting_approval')
        for _ in range(3):self.assertEqual(self.agent.tick()['stage'],'idle')
        self.assertEqual((self.workers,self.github.candidates,self.github.merges,self.sheets.writes),(1,1,1,2))
        self.assertEqual(self.store.execute('status',self.row)['state'],'preview_ready')
        self.assertEqual(self.store.row('SELECT count(*) AS n FROM leases')['n'],0)
        self.assertEqual(json.loads(self.sheets.events[-1]['body'])['source_sha'],'d'*40)
    def test_resume_after_codex_result_does_not_run_codex_again(self):
        self.until('candidate');self.restart();self.until('awaiting_approval')
        self.assertEqual(self.workers,1)
    def test_worker_claims_are_not_accepted_as_test_or_review_evidence(self):
        # The fake child explicitly reports failed tests/review; only the
        # injected controller-side pristine verifier is authoritative.
        self.until('candidate')
        self.assertEqual(self.store.job(self.key)['data']['local_proof'],{'root_pristine_tests':True})
    def test_reviewer_rejection_moves_only_job_to_needs_input(self):
        self.agent.reviewer=lambda *args: (_ for _ in ()).throw(ValueError('independent_review_rejected'))
        self.until('coding')
        self.assertEqual(self.agent.tick()['stage'],'needs_input')
        self.assertEqual(self.store.job(self.key)['stage'],'needs_input')
    def test_failed_verification_is_not_replayed_and_does_not_block_queue(self):
        calls=[]
        def fail_once(*args):
            calls.append(1)
            raise RuntimeError('owned_process_failed')
        self.agent.verifier=fail_once
        self.until('coding')
        self.assertEqual(self.agent.tick()['stage'],'needs_input')
        self.assertEqual(self.agent.tick()['stage'],'idle')
        self.assertEqual(calls,[1])
        self.assertEqual(self.github.candidates,0)
        self.agent.verifier=self.verifier
        sibling={**self.row,'request_id':str(uuid4())}
        self.sheets.rows.append(sibling)
        self.sheets.events.append({**self.event,'event_id':str(uuid4()),'request_id':sibling['request_id'],'event_idempotency_key':'ready-2'})
        self.until('awaiting_approval')
        self.assertEqual(self.workers,2)
        self.assertEqual(self.github.candidates,1)
    def test_optional_mail_uses_ledger_admission_and_replay_does_not_resend(self):
        mail=Mail();self.config['mail_enabled']=True
        self.agent=Agent(self.config,self.store,self.sheets,self.github,worker=self.worker,verifier=self.verifier,reviewer=self.reviewer,mail=mail)
        self.until('awaiting_approval')
        for _ in range(2): self.assertEqual(self.agent.tick()['stage'],'idle')
        self.assertEqual(len(mail.sent),1)
    def test_missing_launch_record_is_observable_and_never_relaunches(self):
        self.until('coding')
        job=self.store.job(self.key)
        (self.path/'work'/(self.key[1]+'-r1')/'child'/'result.json').unlink()
        job['data'].pop('worker',None)
        self.store.save(self.key,'worker_starting',job['data'],job['token'])
        self.assertEqual(self.agent.tick()['stage'],'worker_interrupted')
        self.assertEqual(self.workers,1)
        self.assertEqual(self.store.job(self.key)['data']['worker_recovery']['state'],'launch_record_missing')
    def test_identity_unavailable_blocks_even_when_child_writes_a_result(self):
        self.until('coding')
        job=self.store.job(self.key);job['data']['worker']['identity']=None
        self.store.save(self.key,'coding',job['data'],job['token'])
        self.assertEqual(self.agent.tick()['stage'],'worker_interrupted')
        self.assertEqual(self.store.job(self.key)['data']['worker_recovery']['state'],'launch_identity_unavailable')
    def test_preexisting_job_symlink_is_rejected_before_controller_writes(self):
        path=self.path/'work'/(self.key[1]+'-r1')
        path.symlink_to(self.path)
        result=self.agent.tick()
        self.assertEqual(result['error'],'unsafe_job_directory')
    def test_worker_entrypoint_smoke_with_fake_codex_and_node(self):
        root=self.path/'smoke'; source=root/'source'; child=root/'child'; fake=root/'bin'
        (source/'examples/sample-clinic/content').mkdir(parents=True); (source/'examples/sample-clinic/tests').mkdir(parents=True); child.mkdir(parents=True); fake.mkdir(parents=True)
        base=self.github.base();(source/'examples/sample-clinic/content/clinic.json').write_text(json.dumps(base['content']))
        (source/'examples/sample-clinic/build.mjs').write_text('')
        (source/'examples/sample-clinic/tests/x.test.mjs').write_text('')
        codex=fake/'codex';codex.write_text('#!/usr/bin/env python3\nimport json,pathlib\np=pathlib.Path("examples/sample-clinic/content/clinic.json");v=json.loads(p.read_text());v["notices"][0]["body"]="changed";v["changeRequest"]={"id":"'+self.row['request_id']+'","revision":1};p.write_text(json.dumps(v))\n')
        node=fake/'node';node.write_text('#!/bin/sh\nexit 0\n');os.chmod(codex,0o755);os.chmod(node,0o755)
        input_path=root/'input.json';atomic_json(input_path,{'request':self.row,'base':base,'notice_id':'notice','codex_binary':str(codex)})
        env={**os.environ,'PATH':str(fake)+os.pathsep+os.environ['PATH']}
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('codex_worker.py')),'--input',str(input_path),'--source',str(source),'--workspace',str(child/'workspace'),'--result',str(child/'result.json')],env=env,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads((child/'result.json').read_text())['state'],'success')
    def test_uncertain_candidate_reconciles_after_restart_and_expired_lease(self):
        self.github.uncertain=True;self.until('candidate')
        self.assertIn('error',self.agent.tick())
        self.now[0]+=4000;self.restart();self.until('awaiting_approval')
        self.assertEqual(self.github.candidates,1)
    def test_uncertain_merge_reconciles_without_remerge(self):
        self.github.merge_uncertain=True;self.until('merge');self.assertIn('error',self.agent.tick())
        self.restart();self.until('awaiting_approval');self.assertEqual(self.github.merges,1)
    def test_sheet_append_response_loss_is_reconciled_without_duplicate(self):
        self.until('results');self.sheets.uncertain=True;self.assertIn('error',self.agent.tick())
        self.restart();self.until('awaiting_approval');self.assertEqual(self.sheets.writes,2)
    def test_partial_candidate_is_observable_and_not_retried(self):
        self.until('candidate');self.github.uncertain=True
        self.agent.tick();self.github.proof=None
        self.assertEqual(self.agent.tick()['stage'],'provider_reconciliation_required')
        self.assertEqual(self.store.job(self.key)['data']['provider_recovery'],{'effect':'candidate','state':'remote_partial_or_absent'})
        for _ in range(2):self.assertEqual(self.agent.tick()['stage'],'provider_reconciliation_required')
        self.assertEqual(self.github.candidates,1)
    def test_new_revision_and_cancel_stop_old_work_before_github(self):
        self.until('candidate')
        self.sheets.events.append({**self.event,'event_id':str(uuid4()),'kind':'request_cancelled','event_idempotency_key':'cancel'})
        self.assertEqual(self.agent.tick()['stage'],'stopped')
        self.assertEqual(self.github.candidates,0)
    def test_changed_row_same_revision_fails_closed(self):
        self.until('candidate');self.sheets.rows[0]['outcome']='changed after acceptance'
        self.assertEqual(self.agent.tick()['stage'],'idle')
        self.assertEqual(self.store.job(self.key)['stage'],'needs_input')
        self.assertEqual(self.github.candidates,0)
    def test_history_before_start_is_not_reimplemented(self):
        self.sheets.events[0]['occurred_at']='2026-10-31T00:00:00Z'
        self.assertEqual(self.agent.tick()['stage'],'idle');self.assertEqual(self.workers,0)
    def test_malformed_unrelated_revision_does_not_block_target(self):
        self.sheets.rows.append({'site_id':'other','request_id':'other','revision':'not-an-int'})
        self.assertEqual(self.agent.tick()['stage'],'coding')
    def test_concurrent_instance_lock_denies_work(self):
        other=AgentStore(self.path/'state.sqlite3')
        try:
            with self.store.exclusive():
                with self.assertRaisesRegex(ValueError,'agent_instance_busy'):
                    with other.exclusive():pass
        finally:other.close()
    def test_unexpected_candidate_fields_are_rejected(self):
        before=self.github.base()['content'];after=copy.deepcopy(before)
        after['name']='attacker';after['notices'][0]['body']='changed';after['changeRequest']={'id':self.row['request_id'],'revision':1}
        with self.assertRaisesRegex(ValueError,'candidate_scope_exceeded'):validate_candidate(before,after,self.row,'notice')
    def test_admission_blocks_revision_and_cancel_until_reconciliation(self):
        self.until('candidate');self.github.uncertain=True;self.agent.tick()
        with self.assertRaisesRegex(ValueError,'effect_reconciliation_required'):
            self.store.execute('cancel',{**self.row,'reason':'stop'})
        self.until('awaiting_approval')
        self.assertEqual(self.store.execute('cancel',{**self.row,'reason':'stop'})['state'],'cancelled')


if __name__=='__main__':unittest.main()
