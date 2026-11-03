(function(){
"use strict";
// Navigation and inquiry UI for the alternate service page.
const menuButton=document.getElementById('menu-toggle'),mainNav=document.getElementById('main-nav');
menuButton.addEventListener('click',()=>{const isOpen=mainNav.classList.toggle('open');menuButton.setAttribute('aria-expanded',String(isOpen));});
mainNav.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{mainNav.classList.remove('open');menuButton.setAttribute('aria-expanded','false');}));
const floatingCta=document.querySelector('.floating-cta');
const updateFloatingCta=()=>{
 const interacting=['diagnosis','rebuild','contact'].some(id=>{const r=document.getElementById(id).getBoundingClientRect();return r.top<innerHeight && r.bottom>0;});
 floatingCta.classList.toggle('is-visible',window.scrollY>750 && !interacting && !document.querySelector('dialog[open]'));
};
window.addEventListener('scroll',updateFloatingCta,{passive:true});
updateFloatingCta();
document.querySelectorAll('[data-select-plan]').forEach(btn=>btn.addEventListener('click',()=>{document.getElementById('contact-plan').value=btn.dataset.selectPlan;document.getElementById('contact').scrollIntoView({behavior:'smooth'});setTimeout(()=>document.getElementById('contact-clinic').focus({preventScroll:true}),320); }));
document.getElementById('inquiry-form').addEventListener('submit',e=>{
 e.preventDefault();const plan=document.getElementById('contact-plan').value,clinic=document.getElementById('contact-clinic').value.trim(),person=document.getElementById('contact-person').value.trim(),email=document.getElementById('contact-email').value.trim(),opt=document.getElementById('contact-option').checked;
 if(!clinic || !person || !email)return;
 const subject='【SIMY HP管理】導入相談：'+clinic;
 const body=`SIMY HP管理 担当者様\n\n導入について相談したく、ご連絡いたしました。\n\n希望プラン：${plan}（SIMYライセンス込み）\n運用・集患サポート：${opt?'相談希望':'希望なし／未定'}\n医療機関名：${clinic}\nご担当者名：${person}\nメールアドレス：${email}\nホームページ：${document.getElementById("contact-url").value.trim()}\nご用件：${document.getElementById("contact-message").value.trim()}\n\nよろしくお願いいたします。`;
 window.location.href='mailto:sales@simy.one?subject='+encodeURIComponent(subject)+'&body='+encodeURIComponent(body);
});


})();
