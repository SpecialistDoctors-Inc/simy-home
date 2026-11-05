const {test}=require('node:test');
const assert=require('node:assert/strict');
const {normalize,buildText,buildMail}=require('../site/clinic-insurance-preparation.js');
const sample=()=>({clinicName:'テスト医院',contactName:'担当者',email:'test@example.com',url:'https://clinic.example/',mfa:'yes',backup:'no',training:'unknown',response:'unknown'});
test('consultation preparation preserves only known fields and marks unknown answers',()=>{
 const data=normalize({...sample(),patientName:'NEVER INCLUDE',revenue:'SECRET',accident:'SECRET'});
 assert.equal(data.mfa,'yes');assert(!('patientName' in data));assert(!('revenue' in data));assert(!('accident' in data));
 const text=buildText(data);assert(text.includes('分からない・未確認'));assert(!text.includes('SECRET'));assert(!text.includes('NEVER INCLUDE'));
 assert(text.includes('正式な告知書ではありません'));assert(text.includes('提供先と内容を別途確認'));
});
test('mail draft targets SIMY and keeps content encoded in the body only',()=>{
 const link=buildMail({...sample(),clinicName:'医院 &name=example?'});
 const mail=new URL(link);assert.equal(mail.protocol,'mailto:');assert.equal(mail.pathname,'sales@simy.one');
 assert.equal(mail.searchParams.get('subject'),'サイバー保険の見積りに関する相談');
 assert(mail.searchParams.get('body').includes('医院 &name=example?'));assert.equal([...mail.searchParams].length,2);
});
test('URL cannot carry credentials, query data, or an executable scheme',()=>{
 for(const url of ['javascript:alert(1)','https://user:pass@example.org','https://clinic.example/?patient=secret','https://clinic.example/#patient','not a URL'])assert.throws(()=>normalize({...sample(),url}));
 assert.equal(normalize({...sample(),url:''}).url,'');
});
test('required contact fields and bounded self-declarations are validated',()=>{
 for(const patch of [{clinicName:''},{email:'bad'},{email:'test@example.com\nBcc:someone'},{contactName:'x'.repeat(81)},{mfa:'guaranteed'},{backup:'__proto__'}])assert.throws(()=>normalize({...sample(),...patch}));
 const data=normalize({clinicName:'医院',contactName:'担当者',email:'test@example.com'});assert.equal(data.backup,'unknown');
});
