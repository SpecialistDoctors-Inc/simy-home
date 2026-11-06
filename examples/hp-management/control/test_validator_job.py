"""Worker manifest boundary and diagnostic redaction, no network/browser calls."""
from contextlib import redirect_stdout
import io
import json
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from validator import render as worker


class WorkerJobTests(unittest.TestCase):
    def setUp(self):
        self.job={'site_id':'sample-site','operation_id':'23456789-1234-4234-8234-123456789abc',
            'package_operation_id':'34567890-1234-4234-8234-123456789abc','validation_id':'a'*64,
            'artifact_sha256':'b'*64,'source_commit':'c'*40,'deadline':int(time.time())+300,
            'artifact_get_url':'https://example.s3.ap-northeast-1.amazonaws.com/site.zip?signature=PRIVATE',
            'output_put_urls':{name:'https://example.s3.ap-northeast-1.amazonaws.com/'+name+'?signature=PRIVATE' for name in ('desktop','mobile','report')}}

    def envelope(self,body=None,**changes):
        body=body if body is not None else json.dumps(self.job,sort_keys=True,separators=(',',':')).encode()
        data={'schema_version':1,'kind':'browser-validation-job','job_get_url':'https://example.s3.ap-northeast-1.amazonaws.com/job.json?signature=PRIVATE',
            'job_sha256':worker.digest(body),'deadline':self.job['deadline']}
        data.update(changes)
        return json.dumps(data),body

    def test_exact_manifest_hash_deadline_shape_and_bounded_fetch(self):
        raw,body=self.envelope();calls=[]
        def fetch(method,url,limit):
            calls.append((method,limit));return body
        self.assertEqual(worker.load_job(raw,fetch),self.job)
        self.assertEqual(calls,[('GET',worker.MAX_JOB)])
        with self.assertRaises(worker.RenderError): worker.load_job(raw,lambda *a,**kw:body+b' ')
        with self.assertRaises(worker.RenderError): worker.load_job(raw,lambda *a,**kw:b'x'*(worker.MAX_JOB+1))
        for change in ({'deadline':self.job['deadline']-1},{'output_put_urls':{'unexpected':'https://example.amazonaws.com/'}},
                       {'artifact_get_url':'http://169.254.169.254/latest/meta-data/'},{'extra':'not permitted'}):
            changed={**self.job,**change}
            raw,body=self.envelope(json.dumps(changed).encode())
            with self.subTest(change=change),self.assertRaises((worker.RenderError,ValueError)):
                worker.load_job(raw,lambda *a,**kw:body)

    def test_expired_or_duplicate_manifest_is_rejected_before_artifact_io(self):
        raw,body=self.envelope(deadline=int(time.time())-1)
        fetch=lambda *a,**kw:self.fail('expired envelope fetched')
        with self.assertRaises(worker.RenderError):worker.load_job(raw,fetch)
        duplicate=b'{"site_id":"first","site_id":"second"}'
        raw,_=self.envelope(duplicate)
        with self.assertRaisesRegex(worker.RenderError,'duplicate'):
            worker.load_job(raw,lambda *a,**kw:duplicate)

    def test_main_logs_only_constant_stage_error_class_and_http_status(self):
        raw,_=self.envelope()
        private='PRIVATE-CAPABILITY-DO-NOT-LOG'
        error=HTTPError('https://example.amazonaws.com/?token='+private,400,'provider-body-'+private,{},io.BytesIO(private.encode()))
        output=io.StringIO()
        with patch.dict('os.environ',{'HP_VALIDATION_JOB':raw}),patch.object(worker,'transfer',side_effect=error), \
                patch.object(worker.signal,'signal'),patch.object(worker.signal,'alarm'),redirect_stdout(output):
            with self.assertRaises(SystemExit) as stopped:worker.main()
        self.assertEqual(stopped.exception.code,1)
        self.assertEqual(json.loads(output.getvalue()),{'event':'browser_validation_failed','stage':'job_manifest','error_class':'HTTPError','http_status':400})
        self.assertNotIn(private,output.getvalue());self.assertNotIn('https://',output.getvalue());self.assertNotIn('signature',output.getvalue())

    def test_main_fetches_verified_manifest_first_and_binds_report_to_job_hash(self):
        raw,body=self.envelope();transfers=[]
        def transfer(method,url,data=None,limit=worker.MAX_TRANSPORT,content_type=None):
            transfers.append((method,url,data,limit,content_type))
            return body if url.endswith('job.json?signature=PRIVATE') else b'artifact' if method=='GET' else b''
        with patch.dict('os.environ',{'HP_VALIDATION_JOB':raw}),patch.object(worker,'transfer',side_effect=transfer), \
                patch.object(worker,'render',return_value=({'verified':True},{'desktop':b'png','mobile':b'png'})), \
                patch.object(worker.signal,'signal'),patch.object(worker.signal,'alarm'):
            worker.main()
        self.assertEqual([call[0] for call in transfers],['GET','GET','PUT','PUT','PUT'])
        self.assertEqual(transfers[0][3],worker.MAX_JOB)
        self.assertEqual(json.loads(transfers[-1][2])['job_sha256'],worker.digest(body))
        self.assertEqual([call[4] for call in transfers[2:]],['image/png','image/png','application/json'])

    def test_worker_transfer_keeps_owner_if_none_match_content_type_and_no_redirect(self):
        recorded=[]
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,limit):return b''
        class Opener:
            def open(self,request,timeout):recorded.append(request);return Response()
        with patch.object(worker.urllib.request,'build_opener',return_value=Opener()) as build:
            worker.transfer('PUT',self.job['output_put_urls']['desktop'],b'png',0,'image/png')
        self.assertIsInstance(build.call_args.args[0],worker.NoRedirect)
        headers={name.lower():value for name,value in recorded[0].header_items()}
        self.assertEqual(headers['x-amz-expected-bucket-owner'],'209300895845')
        self.assertEqual(headers['if-none-match'],'*');self.assertEqual(headers['content-type'],'image/png')


if __name__=='__main__':unittest.main()
