'use strict';
const form = document.querySelector('#consultation');
const urlInput = document.querySelector('#url');
const draft = document.querySelector('#draft');
const clearDraft = () => { if (!draft) return; draft.hidden = true; document.querySelector('#email-link').removeAttribute('href'); };
if (form) {
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

}

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
// Official releases checked on 2026-10-27. These are dated references, not live latest-version guarantees.
const releaseReferences = {
  php: { version: '8.5系', url: 'https://www.php.net/supported-versions.php' },
  jquery: { version: '4.0.0', url: 'https://blog.jquery.com/2026/01/17/jquery-4-0-0/' },
  swiper: { version: '14.3.0', url: 'https://github.com/nolimits4web/swiper/releases/tag/v14.3.0' }
};
function renderEvaluationTable(report) {
  const rows = new Map();
  const add = (name, version, issues, assessment, fix) => {
    const key = name.toLowerCase() + ':' + (version || '');
    const previous = rows.get(key);
    rows.set(key, {name: previous?.name || ({jquery: 'jQuery', swiper: 'Swiper'}[name.toLowerCase()] || name), version, issues: [...(previous?.issues || []), ...(issues || [])], assessment: assessment || previous?.assessment || '', fix: fix || previous?.fix || ''});
  };
  for (const t of report.technologies.filter(t => t.status !== 'unknown')) {
    for (const version of t.versions?.length ? t.versions : ['']) add(t.name, version, t.issues, t.assessment, t.fix);
  }
  for (const l of report.scripts.libraries) add(l.name, l.version, l.issues);
  const section = element('section', '', 'evaluation-section');
  section.append(element('h3', '入力したホームページの評価'), element('p', '公開情報から検出した部品と、更新・確認が必要な点です。'));
  if (!rows.size) {
    section.append(element('p', '公開情報から部品の版を特定できませんでした。安全という判定ではありません。制作会社に構成と更新状況の確認が必要です。'));
    results.append(section); return;
  }
  const wrap = element('div', '', 'evaluation-scroll'); wrap.tabIndex = 0; wrap.setAttribute('role','region'); wrap.setAttribute('aria-label','使用部品の評価表。画面が狭い場合は横にスクロールできます');
  const table = element('table', '', 'evaluation-table');
  table.append(element('caption', '使用部品・検出した版・公式情報・評価・対応'));
  const head = element('thead',''); const tr = element('tr','');
  for (const label of ['見つかった部品','検出した版','公式の公開版（参考）','評価','必要な対応']) {const th=element('th',label);th.scope='col';tr.append(th);}head.append(tr);table.append(head);
  const body = element('tbody','');
  for (const row of rows.values()) {
    const ref = releaseReferences[row.name.toLowerCase()];
    const ended = /サポート終了/.test(row.assessment);
    const issue = row.issues.length > 0;
    const state = ended ? 'サポート終了の系列' : issue ? '既知の問題に関係する版' : !row.version ? '版を特定できず' : ref && row.version !== ref.version && row.name.toLowerCase() !== 'php' ? '更新状況の確認が必要' : '安全性は未判定';
    const line = element('tr','');const name=element('th',row.name);name.scope='row';line.append(name,element('td',row.version || '不明'));
    const official=element('td','');
    if(ref){const a=element('a',ref.version);a.href=ref.url;a.target='_blank';a.rel='noopener';official.append(a,element('small','2026年10月27日確認'));}
    else official.append(element('span','公式情報を別途確認'));
    const status=element('td','');status.append(element('span',state,ended||issue?'evaluation-badge urgent':'evaluation-badge'));
    const action=ended?'制作会社・サーバー会社に延長保守や個別修正の有無を確認し、保守対象の系列へ移行。':issue?'実際の導入版と修正状況を確認し、画面・フォームの動作を検証して更新。':!row.version?'制作会社に使用部品と導入版を確認。':'公式の修正情報と実際の構成を照合。互換性を確認して更新を判断。';
    line.append(official,status,element('td',action));body.append(line);
  }
  table.append(body);wrap.append(table);section.append(wrap,element('p','公式の公開版は上記確認日時点の参考情報です。最新の修正版はリンク先で確認してください。新しい版との差だけで脆弱性や侵入を断定しません。検出した版は公開情報の手掛かりであり、実際の導入版・個別修正は制作会社への確認が必要です。','evaluation-note'));
  results.append(section);
}

function renderReport(report) {
  if (!Array.isArray(report.findings) || !Array.isArray(report.technologies) || !Array.isArray(report.scripts?.libraries)) throw Error('結果の形式を確認できませんでした。時間をおいて再度お試しください。');
  const technologies = report.technologies.filter(t => t.status === 'review');
  const libraries = report.scripts.libraries.filter(l => l.issues.length);
  const reviews = report.findings.filter(f => f.state === 'review');
  const patches = (report.scripts.comparisons || []).filter(c => ['legacy','mixed'].includes(c.patch?.state));
  title.textContent = technologies.length || libraries.length || patches.length ? '放置せず、制作会社へ確認してください。' : reviews.length ? '保護設定に、見直したい点があります。' : '今回の範囲で、状態を確認しました。';
  message.textContent = '確認日時：' + new Date(report.checkedAt).toLocaleString('ja-JP') + '。公開ページと関連するプログラムを調べた結果です。';
  renderEvaluationTable(report);
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
  results.replaceChildren(); diagnosisState.hidden=false; document.querySelector('#diagnosis-target').textContent='医院ホームページの診断結果';
  title.textContent='公開ホームページを確認しています'; message.textContent='最大約1分かかります。ページの保護設定・使用部品・公開プログラムを確認しています。';
  const progress = document.querySelector('#scan-progress');
  if(progress){progress.hidden=false;progress.textContent='診断中です。公開ページと使用部品を確認しています（最大約1分）。';}
  if(urlInput) urlInput.value=target.href; clearDraft();
  if(!diagnosisEndpoint){title.textContent='診断サービスは接続準備中です';message.textContent='まだ診断は実行していません。公開設定の確認後にご利用いただけます。';return;}
  busy=true;const button=diagnosisForm.querySelector('button');const label=button.querySelector('.button-label');const originalLabel=label?.textContent;if(label)label.textContent='診断中…';button.disabled=true;diagnosisInput.disabled=true;diagnosisForm.setAttribute('aria-busy','true');
  try { const response=await fetch(diagnosisEndpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:target.href,behavior:false}),signal:AbortSignal.timeout(80000)}); const data=await response.json(); if(!response.ok)throw Error(data.error||'診断結果を取得できませんでした。'); renderReport(data); if(progress)progress.textContent='診断が完了しました。結果をご確認ください。'; diagnosisState.focus({preventScroll:true});diagnosisState.scrollIntoView({block:'start',behavior:'smooth'}); }
  catch(error){results.replaceChildren();title.textContent='診断を完了できませんでした';message.textContent=error.name==='TimeoutError'?'時間内に応答がありませんでした。少し待って再度お試しください。':error.message==='Failed to fetch'?'診断サービスに接続できませんでした。少し待って再度お試しください。':error.message;}
  finally{busy=false;button.disabled=false;diagnosisInput.disabled=false;diagnosisForm.removeAttribute('aria-busy');if(label)label.textContent=originalLabel;if(title.textContent==='診断を完了できませんでした' && progress)progress.textContent=message.textContent;}
});
document.querySelector('.edit-url').addEventListener('click',()=>{if(!busy){diagnosisState.hidden=true;diagnosisInput.focus();}});
