(function(global){
'use strict';
const labels={link:'リンクで移動（未操作）',script:'外部プログラムを読込',embed:'ページ内に埋め込み',form:'フォーム送信先（未送信）'};
function urlKey(value){try{const u=new URL(value);return u.origin+u.pathname;}catch{return '';}}
function model(report){
 const observed=new Set((report.scripts?.browserEvidence?.connections||[]).map(x=>urlKey(x.destination)).filter(Boolean));
 const groups=new Map();
 for(const item of report.integrations||[]){let url;try{url=new URL(item.destination);}catch{continue;}if(!['http:','https:'].includes(url.protocol))continue;try{if(url.origin===new URL(report.url).origin)continue;}catch{}const key=url.hostname;let g=groups.get(key);if(!g){g={domain:key,category:/^(drive|docs)\.google\.com$/.test(key)?'資料共有':item.category,kinds:[],categories:[],pages:new Set(),observed:false,sharing:[]};groups.set(key,g);}if(!g.categories.includes(item.category))g.categories.push(item.category);if(!g.kinds.includes(item.kind))g.kinds.push(item.kind);g.pages.add(item.page);if(observed.has(urlKey(item.destination)))g.observed=true;
 }
 for(const item of report.sharing?.items||[]){try{groups.get(new URL(item.url).hostname)?.sharing.push(item);}catch{}}
 return [...groups.values()].map(g=>({...g,pages:[...g.pages],labels:g.kinds.map(k=>labels[k]||k)})).sort((a,b)=>(b.sharing.length>0)-(a.sharing.length>0)||a.domain.localeCompare(b.domain));
}
function managementCopy(g){
 const category=(g.categories||[g.category]).join(' ');
 if(/予約|問診|診療|決済|ログイン/.test(category))return {label:'患者情報の管理が重要',reason:'予約・問診などで、氏名や連絡先、症状などを入力する可能性があります。',action:'入力する情報・閲覧できる人・保存期間を確認してください。'};
 if(g.category==='資料共有'||g.sharing?.length)return {label:'資料の公開範囲が重要',reason:'患者さん向けの公開資料か、院内だけで使う資料かで、必要な管理が変わります。',action:'公開してよい内容か、共有相手が適切かを確認してください。'};
 if(g.kinds.includes('form'))return {label:'入力情報の管理が重要',reason:'フォームの入力内容を外部へ送る設定があります。入力内容は未確認です。',action:'送信する項目・受取先・保存期間を確認してください。'};
 if(g.kinds.some(k=>k==='script'||k==='embed'))return {label:'外部へ情報が送られる可能性',reason:'ページを開くだけで、アクセス情報などが外部に送られる場合があります。',action:'送る情報と外部プログラムの更新状況を確認してください。'};
 return {label:'案内だけのリンクなら、優先度は低め',reason:'リンクを置いているだけでは、患者情報が送られるとは限りません。移動先で情報を入力する場合は、管理の確認が必要です。',action:'案内を見るだけか、予約や個人情報の入力に使うかを確認してください。'};
}
function renderPriority(report,root,el){
 const groups=model(report).filter(g=>managementCopy(g).label==='患者情報の管理が重要');
 if(!groups.length)return;
 const box=el('section','','patient-information-priority');
 box.append(el('h3','患者情報の管理が重要'),el('p','予約・問診などの外部サービスでは、氏名・連絡先・症状などを扱う可能性があります。'));
 const list=el('ul','');for(const g of groups)list.append(el('li',g.domain+'（'+g.categories.join('・')+'）'));
 box.append(list,el('p','患者情報の送信や漏えいを確認したものではありません。','small'));root.append(box);
}
function render(report,root,el){
 const groups=model(report),section=el('section','','information-flow');section.append(el('h3','04 / ホームページと外部サービスのつながり'),el('p','用途から考えられる管理の重要度を示しています。'));
 const diagram=el('div','','flow-diagram');diagram.setAttribute('aria-label','医院ホームページ、閲覧者のブラウザー、外部サービスの接続図');
 const site=el('div','','flow-node flow-site');site.append(el('span','医院のホームページ'),el('strong',new URL(report.url).hostname),el('p','ページ・画像などを配信'));
 const browser=el('div','','flow-node flow-browser');browser.append(el('span','⇄ ページの取得','flow-direction'),el('strong','閲覧者のブラウザー'),el('p','医院のHPを表示'),el('small','診断では匿名のブラウザーを使用。患者情報は入力しません。'));
 const branches=el('div','','flow-branches');
 const categories=new Map();for(const g of groups){const key=g.category==='用途未確認'?'その他の外部リンク':g.category;const list=categories.get(key)||[];list.push(g);categories.set(key,list);}
 for(const [category,list] of categories){const observed=list.some(g=>g.observed),branch=el('details','','flow-branch'+(observed?' observed':''));const summary=el('summary','');const direction=list.every(g=>g.kinds.every(k=>k==='link'||k==='form'))?'→':'⇄';summary.append(el('span',direction,'flow-arrow'),el('strong',category+' · '+list.length+'サービス'),el('small',observed?'通常表示で通信を確認した接続先あり':'ページに接続先の記載あり'));
 branch.open=true;branch.append(summary);
 for(const g of list){const copy=managementCopy(g),entry=el('div','','flow-service');entry.append(el('strong',g.domain),el('p',copy.label),el('p',copy.reason));
 branch.append(entry);}
 branches.append(branch);}
 if(!groups.length)branches.append(el('p','接続先を検出できませんでした。未使用の証明ではありません。'));
 diagram.append(site,browser,branches);section.append(diagram,el('p','管理の重要度は、安全・危険の判定ではありません。入力内容や実際の患者情報の送信、提供先内部の管理状況は未確認です。','small'));root.append(section);
 renderSharing(report,root,el);
}
function sharingName(item){return typeof item.title==='string'&&item.title.trim()?item.title.trim():item.kind==='folder'?'共有フォルダ（名称未取得）':'資料名を取得できませんでした';}
function sharingCopy(item){
 const copies={
  'preview-observed':{label:'内容は未判定',reason:'公開用の案内資料なら問題ありません。資料の内容が患者さん向けか、院内限定かは未判定です。',action:'この資料が「誰に見られてもよい資料」か確認してください。院内限定の資料なら、公開範囲を見直してください。'},
  'access-required':{label:'閲覧にはアクセス許可が必要です',reason:'今回の確認では、ログインなしで資料を閲覧できませんでした。誰に共有されているかは未確認です。',action:'院内限定の資料なら、不要な外部の人に共有していないか確認してください。'},
  unknown:{label:'見られるか判断できませんでした',reason:'今回の取得結果だけでは、ログインなしで見られるか判断できませんでした。',action:'資料の持ち主と、共有先と公開範囲を確認してください。'},
  'not-checked':{label:'今回は確認していません',reason:'確認件数や時間の上限に達したため、このリンクは未確認です。',action:'資料の持ち主に公開範囲を確認してください。'}
 };
 return copies[item.status]||copies.unknown;
}
function renderSharing(report,root,el){
 const section=el('section','','sharing-review');section.append(el('h3','Google Driveなどの公開範囲'));
 const items=report.sharing?.items||[];
 if(!report.sharing){section.append(el('p','この診断結果には共有リンクの閲覧確認がありません。'));root.append(section);return;}
 if(!items.length)section.append(el('p','確認した公開ページでは、検査対象のGoogle Drive・Docs直接リンクは見つかりませんでした。リンクのない内部共有は未検査です。'));
 if(items.length){
 const wrap=el('div','','evaluation-scroll');const table=el('table','','evaluation-table sharing-table');const head=el('thead',''),header=el('tr','');
 for(const label of ['資料','判定内容']){const cell=el('th',label);cell.scope='col';header.append(cell);}head.append(header);table.append(head);
 const body=el('tbody','');
 items.forEach((item,i)=>{const copy=sharingCopy(item),row=el('tr',''),name=el('th',sharingName(item));name.scope='row';
 if(/^https:\/\//.test(item.url||'')){const link=el('a','資料を見る ↗');link.href=item.url;link.target='_blank';link.rel='noopener';name.append(el('br',''),link);}
 const result=el('td',copy.reason);row.append(name,result);body.append(row);});
 table.append(body);wrap.append(table);section.append(wrap,el('p','資料の内容が患者さん向けか、院内限定かは未判定です。編集権限も未確認です。公開されているだけで情報漏えいとは判定しません。','small'));
 }
 root.append(section);
}
global.SimyInformationFlow={model,render,renderPriority,sharingCopy,sharingName,managementCopy};
})(typeof window==='undefined'?globalThis:window);
