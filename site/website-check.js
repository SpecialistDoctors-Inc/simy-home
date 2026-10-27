'use strict';
const form = document.querySelector('#consultation');
const urlInput = document.querySelector('#url');
const draft = document.querySelector('#draft');
const clearDraft = () => { draft.hidden = true; document.querySelector('#email-link').removeAttribute('href'); };
form.addEventListener('input', clearDraft);
urlInput.addEventListener('input', () => urlInput.setCustomValidity(''));
document.querySelectorAll('[data-plan]').forEach(link => link.addEventListener('click', () => {
  form.elements.plan.value = link.dataset.plan;
  clearDraft();
}));
form.addEventListener('submit', event => {
  event.preventDefault();
  const url = new URL(urlInput.value);
  if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) {
    urlInput.setCustomValidity('http:// または https:// で始まる、認証情報を含まないURLを入力してください。');
    urlInput.reportValidity();
    return;
  }
  const message = `SIMY ホームページ保守・セキュリティ管理の相談\n\n対象URL：${url.href}\n希望プラン：${form.elements.plan.value}\n気になっていること：${form.elements.concern.value.trim() || '相談しながら整理したい'}\n\n提供範囲・料金・開始時期について相談を希望します。`;
  document.querySelector('#draft-body').textContent = message;
  document.querySelector('#email-link').href = `mailto:sales@simy.one?subject=${encodeURIComponent('クリニックのホームページ保守についての相談')}&body=${encodeURIComponent(message)}`;
  draft.hidden = false;
  draft.scrollIntoView({block:'nearest'});
});

const diagnosisForm = document.querySelector('#diagnosis-form');
const diagnosisInput = document.querySelector('#diagnosis-url');
const diagnosisState = document.querySelector('#diagnosis-state');
const results = document.querySelector('#diagnosis-results');
const message = document.querySelector('#diagnosis-message');
const title = document.querySelector('#diagnosis-state-title');
let busy = false;
// Set only after the production diagnosis service is publicly available.
const diagnosisEndpoint = diagnosisForm.dataset.endpoint;
const element = (tag, text, className) => {
  const node = document.createElement(tag); node.textContent = text;
  if (className) node.className = className;
  return node;
};
function card(level, heading, risk, action, evidence) {
  const article = element('article', '', 'live-finding ' + level);
  article.append(element('span', level === 'urgent' ? '早めに対応' : level === 'review' ? '確認が必要' : '今回確認できたこと', 'live-label'), element('h3', heading), element('p', risk));
  if (action) article.append(element('p', '次にすること：' + action, 'live-action'));
  if (evidence) { const details = element('details', ''); details.append(element('summary', '制作会社に伝える根拠を見る'), element('pre', evidence)); article.append(details); }
  results.append(article);
}
function renderReport(report) {
  if (!Array.isArray(report.findings) || !Array.isArray(report.technologies) || !Array.isArray(report.scripts?.libraries)) throw Error('結果の形式を確認できませんでした。時間をおいて再度お試しください。');
  const technologies = report.technologies.filter(t => t.status === 'review');
  const libraries = report.scripts.libraries.filter(l => l.issues.length);
  const reviews = report.findings.filter(f => f.state === 'review');
  const patches = (report.scripts.comparisons || []).filter(c => ['legacy','mixed'].includes(c.patch?.state));
  title.textContent = technologies.length || libraries.length || patches.length ? '放置せず、制作会社へ確認してください。' : reviews.length ? '保護設定に、見直したい点があります。' : '今回の範囲で、状態を確認しました。';
  message.textContent = '確認日時：' + new Date(report.checkedAt).toLocaleString('ja-JP') + '。公開ページと関連するプログラムを調べた結果です。';
  for (const t of technologies.filter(t => !libraries.some(l => l.name.toLowerCase() === t.name.toLowerCase()))) card('urgent', t.name === 'PHP' ? 'ホームページの土台に、古いPHPの表記があります' : t.name + 'に更新の確認が必要です', t.name === 'PHP' ? '開発元のサポートが終了した系列です。新しい問題が見つかっても、開発元から修正が提供されません。表記だけでは実際の修正状況までは分かりません。' : '既知の問題に関係する版の手掛かりがあります。実際の導入版と修正状況を確認する必要があります。', t.fix, t.evidence.join('\n') + '\n' + t.assessment);
  for (const l of libraries) card('urgent', l.name + ' ' + l.version + '：既知の問題に関係する部品です', '画面の動きに使う部品です。使い方によっては不正な処理につながるおそれがあります。侵入や漏えいが起きたと判定したものではありません。', '制作会社に実際の版・個別修正を確認し、画面やフォームの動作を検証して修正版へ更新してください。', '検出方法：' + ({url:'URLの表記から推定',body:'公開ファイルの内容',hash:'ファイルの照合',sourcemap:'公開された元ソース情報'}[l.basis] || l.basis) + '\n取得元：' + l.resource + '\n' + l.issues.flatMap(i => i.ids).join('、'));
  for (const c of patches) card('urgent', '修正前のプログラムに似た特徴があります', '版の番号だけでなく、公開コードにも確認が必要な特徴があります。実際に攻撃できるかは調べていません。', '制作会社へコードの修正適用状況を確認してください。', JSON.stringify(c, null, 2));
  for (const f of reviews) card('review', f.title, f.summary, f.fix, f.evidence);
  const verified = report.findings.filter(f => f.state === 'observed');
  if (verified.length) { const d=element('details','','live-finding'); d.append(element('summary','今回確認できた設定を見る（' + verified.length + '項目）')); verified.forEach(f=>{d.append(element('h3',f.title),element('p',f.evidence));}); results.append(d); }
  const scope = element('aside', '', 'live-limits');
  scope.append(element('h3', '普段どおり表示されていても、侵入されていない証明にはなりません。'), element('p', 'この診断だけでは、侵入・情報漏えいの有無は分かりません。確認するには、管理者の協力のもと、アクセス記録やサーバー内のファイル、利用者の権限などを調べる必要があります。'), element('p', '今回調べていないこと：サーバー内部・データベース・ログイン後・電子カルテ・外部予約サービス内部。'), element('p', '追加読込の確認：' + report.scripts.dynamic.reason));
  for (const f of report.findings.filter(f=>f.state==='unknown')) scope.append(element('p', f.title + '：判定できません。' + f.evidence));
  if(report.truncated) scope.append(element('p','ページの容量上限により、HTMLの一部は未確認です。'));
  const unknownTech = report.technologies.filter(t => t.status === 'unknown').map(t => t.name);
  if(unknownTech.length) scope.append(element('p','使用の有無や版を確認できなかったもの：' + unknownTech.join('、') + '。検出されないことは、安全や未使用の証明ではありません。'));
  for(const limit of report.scripts.limitations || []) scope.append(element('p',limit));
  const coverage = element('details','','live-finding'); coverage.append(element('summary','取得・解析した範囲と部品の一覧を見る'));
  for(const t of report.technologies.filter(t=>t.status!=='unknown')) coverage.append(element('p',t.name + '：' + (t.versions.join(' / ') || '版は未確認') + '。' + t.assessment));
  for(const resource of report.scripts.resources || []) coverage.append(element('p',resource.url + '：' + resource.reason));
  for(const analysis of report.scripts.analysis || []) coverage.append(element('p','プログラム解析：' + analysis.url + ' / ' + analysis.reason));
  results.append(coverage,scope);
  const save=element('button','結果を保存して、制作会社に確認する','button button-primary');save.type='button';save.addEventListener('click',()=>{const blob=new Blob([title.textContent+'\n'+report.url+'\n'+message.textContent+'\n'+results.innerText+'\n\n詳細な取得根拠\n'+JSON.stringify(report,null,2)],{type:'text/plain;charset=utf-8'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='医院ホームページ診断.txt';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);});results.append(save);
}
diagnosisInput.addEventListener('input', () => { diagnosisInput.setCustomValidity(''); if(!busy) diagnosisState.hidden = true; });
diagnosisForm.addEventListener('submit', async event => {
  event.preventDefault(); if(busy) return;
  let target;
  try { const value=diagnosisInput.value.trim(); target=new URL(/^[a-z][a-z\d+.-]*:/i.test(value)?value:'https://'+value); if(!['https:','http:'].includes(target.protocol)||target.username||target.password||target.port||target.search||target.hash||!target.hostname.includes('.')||/\s/.test(value)) throw Error(); }
  catch { diagnosisInput.setCustomValidity('認証情報や「?」「#」以降を含まない公開URLを入力してください。');diagnosisInput.reportValidity();return; }
  results.replaceChildren(); diagnosisState.hidden=false; document.querySelector('#diagnosis-target').textContent=target.href;
  title.textContent='公開ホームページを確認しています'; message.textContent='最大約1分かかります。ページの保護設定・使用部品・公開プログラムを確認しています。';
  diagnosisState.focus({preventScroll:true}); diagnosisState.scrollIntoView({block:'start',behavior:'smooth'});
  urlInput.value=target.href; clearDraft();
  if(!diagnosisEndpoint){title.textContent='診断サービスは接続準備中です';message.textContent='まだ診断は実行していません。公開設定の確認後にご利用いただけます。';return;}
  busy=true;const button=diagnosisForm.querySelector('button');button.disabled=true;diagnosisInput.disabled=true;
  try { const response=await fetch(diagnosisEndpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:target.href,behavior:false}),signal:AbortSignal.timeout(80000)}); const data=await response.json(); if(!response.ok)throw Error(data.error||'診断結果を取得できませんでした。'); renderReport(data); }
  catch(error){results.replaceChildren();title.textContent='診断を完了できませんでした';message.textContent=error.name==='TimeoutError'?'時間内に応答がありませんでした。少し待って再度お試しください。':error.message==='Failed to fetch'?'診断サービスに接続できませんでした。少し待って再度お試しください。':error.message;}
  finally{busy=false;button.disabled=false;diagnosisInput.disabled=false;}
});
document.querySelector('.edit-url').addEventListener('click',()=>{if(!busy){diagnosisState.hidden=true;diagnosisInput.focus();}});
