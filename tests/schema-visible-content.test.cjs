const test=require('node:test');
const {execFileSync}=require('node:child_process');
const path=require('node:path');
test('every declared FAQ pair agrees with its own visible question and answer',()=>{
 execFileSync('python3',['scripts/check-schema-visible-content.py','--check'],{cwd:path.resolve(__dirname,'..'),stdio:'pipe'});
});
