(function(global){
'use strict';
const labels={link:'リンクで移動（未操作）',script:'外部プログラムを読込',embed:'ページ内に埋め込み',form:'フォーム送信先（未送信）'};
function urlKey(value){try{const u=new URL(value);return u.origin+u.pathname;}catch{return '';}}
function model(report){
 const observed=new Set((report.scripts?.browserEvidence?.connections||[]).map(x=>urlKey(x.destination)).filter(Boolean));
 const groups=new Map();
 for(const item of report.integrations||[]){let url;try{url=new URL(item.destination);}catch{continue;}if(!['http:','https:'].includes(url.protocol))continue;const key=url.hostname;let g=groups.get(key);if(!g){g={domain:key,category:/^(drive|docs)\.google\.com$/.test(key)?'資料共有':item.category,kinds:[],pages:new Set(),observed:false,sharing:[]};groups.set(key,g);}if(!g.kinds.includes(item.kind))g.kinds.push(item.kind);g.pages.add(item.page);if(observed.has(urlKey(item.destination)))g.observed=true;
 }
 for(const item of report.sharing?.items||[]){try{groups.get(new URL(item.url).hostname)?.sharing.push(item);}catch{}}
 return [...groups.values()].map(g=>({...g,pages:[...g.pages],labels:g.kinds.map(k=>labels[k]||k)})).sort((a,b)=>(b.sharing.length>0)-(a.sharing.length>0)||a.domain.localeCompare(b.domain));
}
function render(report,root,el){
 const groups=model(report),section=el('section','','information-flow');section.append(el('h3','03 / ホームページと外部サービスのつながり'),el('p','誰が、どこにつながるのか。実際に観測した通信と、ページ上の設定を分けて表示します。'));
 const diagram=el('div','','flow-diagram');diagram.setAttribute('aria-label','医院ホームページ、閲覧者のブラウザー、外部サービスの接続図');
 const site=el('div','','flow-node flow-site');site.append(el('span','医院のホームページ'),el('strong',new URL(report.url).hostname),el('p','ページ・画像などを配信'));
 const browser=el('div','','flow-node flow-browser');browser.append(el('span','⇄ ページの取得','flow-direction'),el('strong','閲覧者のブラウザー'),el('p','医院のHPを表示'),el('small','診断では匿名のブラウザーを使用。患者情報は入力しません。'));
 const branches=el('div','','flow-branches');
 const categories=new Map();for(const g of groups){const key=g.category==='用途未確認'?'その他の外部リンク':g.category;const list=categories.get(key)||[];list.push(g);categories.set(key,list);}
 for(const [category,list] of categories){const observed=list.some(g=>g.observed),branch=el('details','','flow-branch'+(observed?' observed':''));const summary=el('summary','');const direction=list.every(g=>g.kinds.every(k=>k==='link'||k==='form'))?'→':'⇄';summary.append(el('span',direction,'flow-arrow'),el('strong',category+' · '+list.length+'サービス'),el('small',observed?'通常表示で通信を確認した接続先あり':'ページに接続先の記載あり'));
 if(list.some(g=>g.sharing.some(x=>x.status==='preview-observed')))summary.append(el('b','匿名の閲覧画面あり · 公開意図を確認','flow-sharing-alert'));
 branch.append(summary);
 for(const g of list){const entry=el('div','','flow-service');entry.append(el('strong',g.domain),el('p',g.labels.join(' / ')),el('p',(g.observed?'通常表示で通信を確認':'設定・リンクのみ確認')+' · 記載 '+g.pages.length+'ページ'));
 const possibilities=g.kinds.includes('form')?'フォームの入力内容が送信される設計です。入力・送信は検査していません。':g.kinds.includes('script')||g.kinds.includes('embed')?'アクセス時の通信情報を提供先が受け取る場合があります。患者情報の送信や保存の有無は未確認です。':'クリックすると外部ページへ移動するリンクです。リンクだけでは契約や情報送信を確認できません。';entry.append(el('p',possibilities));branch.append(entry);}
 branch.append(el('p','提供先の内部保存・再共有・削除は管理者と確認します。','small'));branches.append(branch);}
 if(!groups.length)branches.append(el('p','接続先を検出できませんでした。未使用の証明ではありません。'));
 diagram.append(site,browser,branches);section.append(diagram,el('p','矢印は接続関係です。患者情報が実際に流れたことや、サーバー間の連携を示すものではありません。','small'));root.append(section);
 renderSharing(report,root,el);
}
function renderSharing(report,root,el){
 const section=el('section','','sharing-review');section.append(el('h3','Google Driveなどの公開範囲'));
 const items=report.sharing?.items||[];
 if(!report.sharing){section.append(el('p','この診断結果には共有リンクの閲覧確認がありません。再診断して確認してください。'));root.append(section);return;}
 if(!items.length)section.append(el('p','確認した公開ページでは、検査対象のGoogle Drive・Docs直接リンクは見つかりませんでした。リンクのない内部共有は未検査です。'));
 const open=items.filter(x=>x.status==='preview-observed').length;
 if(items.length){section.append(el('strong','匿名の閲覧画面を確認：'+open+'件 / 対象リンク '+items.length+'件'),el('p','公開用の資料か、SIMYと確認してください。内部資料なら「制限付き」へ変更し、個別の外部共有・編集権限・親フォルダの共有も見直します。'));}
 items.forEach((item,i)=>{const article=el('details','','sharing-item '+(item.status==='preview-observed'?'review':''));const summary=el('summary','');summary.append(el('strong',item.service+' · '+(item.kind==='folder'?'フォルダ':'共有資料')+' '+(i+1)),el('span',({'preview-observed':'匿名の閲覧画面あり','access-required':'匿名では閲覧不可',unknown:'閲覧可否は未確認','not-checked':'上限等により未検査'})[item.status]||'未確認'));article.append(summary,el('p',item.reason),el('p','すること：'+item.action),el('p',item.url),el('p','記載ページ：'+item.pages.join(' / ')),el('p','確認：'+(item.checkedAt?new Date(item.checkedAt).toLocaleString('ja-JP'):'未実施')));section.append(article);});
 const scope=el('details','');scope.append(el('summary','確認範囲と、管理者に確認する設定'));for(const t of report.sharing.limitations||[])scope.append(el('p',t));section.append(scope);root.append(section);
}
global.SimyInformationFlow={model,render};
})(typeof window==='undefined'?globalThis:window);
