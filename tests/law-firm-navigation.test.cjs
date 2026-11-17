const test=require('node:test');
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');

test('law-firm landing retains service navigation while ordinary pages use the shared header',()=>{
 const result=execFileSync('python3',['-c',`
import sys
sys.path.insert(0,'scripts')
from site_header import SITE,apply,needs_header
page=SITE/'hp-management/law-firm.html'
source=page.read_text()
assert not needs_header(source,page)
assert apply(source,page)==source
assert needs_header('<html><body><header>Navigation</header></body></html>',SITE/'ordinary.html')
print('passed')
`],{encoding:'utf8'});
 assert.equal(result.trim(),'passed');
});
