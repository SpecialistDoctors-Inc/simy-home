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
 const all=model(report),links=all.filter(g=>g.kinds.every(k=>k==='link')&&!g.sharing.length&&!/予約|問診|診療|決済|ログイン/.test(g.categories.join(' '))),groups=all.filter(g=>!links.includes(g)),section=el('section','','information-flow');section.append(el('h3','04 / ホームページと外部サービスのつながり'),el('p','用途から考えられる管理の重要度を示しています。'));
 const diagram=el('div','','flow-diagram');diagram.setAttribute('aria-label','医院ホームページ、閲覧者のブラウザー、外部サービスの接続図');
 const site=el('div','','flow-node flow-site');site.append(el('span','診断対象のホームページ'),el('strong',new URL(report.url).hostname),el('p','ページ・画像などを配信'));
 const browser=el('div','','flow-node flow-browser');browser.append(el('span','⇄ ページの取得','flow-direction'),el('strong','閲覧者のブラウザー'),el('p','ホームページを表示'),el('small','診断では匿名のブラウザーを使用。患者情報は入力しません。'));
 const branches=el('div','','flow-branches');
 const categories=new Map();for(const g of groups){const key=g.category==='用途未確認'?'その他の外部リンク':g.category;const list=categories.get(key)||[];list.push(g);categories.set(key,list);}
 for(const [category,list] of categories){const observed=list.some(g=>g.observed),branch=el('details','','flow-branch'+(observed?' observed':''));const summary=el('summary','');const direction=list.every(g=>g.kinds.every(k=>k==='link'||k==='form'))?'→':'⇄';summary.append(el('span',direction,'flow-arrow'),el('strong',category+' · '+list.length+'サービス'),el('small',observed?'通常表示で通信を確認した接続先あり':'ページに接続先の記載あり'));
 branch.open=true;branch.append(summary);
 for(const g of list){const copy=managementCopy(g),entry=el('div','','flow-service');entry.append(el('strong',g.domain),el('p',copy.label),el('p',copy.reason));
 branch.append(entry);}
 branches.append(branch);}
 if(links.length)branches.append(el('p','案内・参考情報への外部リンク：'+links.length+'件。リンクの記載だけでは、サービス利用や情報送信は確認できません。'));
 if(!groups.length&&!links.length)branches.append(el('p','接続先を検出できませんでした。未使用の証明ではありません。'));
 diagram.append(site,browser,branches);section.append(diagram,el('p','管理の重要度は、安全・危険の判定ではありません。入力内容や実際の患者情報の送信、提供先内部の管理状況は未確認です。','small'));root.append(section);
 renderSharing(report,root,el);
}
function sharingName(item){
 const assessment=item.assessment;
 if(item.status==='preview-observed'&&['extracted','partial'].includes(item.content?.status)&&assessment?.status==='assessed'&&typeof assessment.topic==='string'&&assessment.topic.trim())return assessment.topic.trim().replace(/に関する資料$/, '')+'に関する資料';
 const title=typeof item.title==='string'?item.title.trim().replace(/\.(pdf|docx?|pptx?|xlsx?)$/i,''):'';
 if(title&&!/^(?:プレゼンテーション|presentation|資料|document|untitled|無題|ファイル|scan|スキャン|[0-9 _-]+)[0-9 _-]*$/i.test(title))return title+'に関する資料（名称から表示・内容未判定）';
 return item.kind==='folder'?'共有フォルダ（内容未判定）':'内容を特定できていない資料';
}
function sharingCopy(item){
 if(item.kind==='folder')return {label:'フォルダー内の資料',reason:item.folder?.discovered?'公開一覧から'+item.folder.discovered+'件を検出。資料ごとの結果を下に表示します。':'フォルダー内の資料は未確認です。',action:''};
 const copies={
  'preview-observed':{label:'本文は未確認',reason:'資料の内容を確認できませんでした。',action:''},
  'access-required':{label:'閲覧にはアクセス許可が必要です',reason:'今回の確認では、資料の閲覧にアクセス許可が必要でした。誰に共有されているかは未確認です。',action:''},
  unknown:{label:'見られるか判断できませんでした',reason:'今回の取得結果だけでは、閲覧できるか判断できませんでした。',action:''},
  'not-checked':{label:'今回は確認していません',reason:'確認件数や時間の上限に達したため、このリンクは未確認です。',action:''}
 };
 if(item.status!=='preview-observed')return copies[item.status]||copies.unknown;
 const content=item.content,a=item.assessment;
 if(!content||content.status==='unavailable')return copies['preview-observed'];
 if(!a||a.status==='not-run')return {label:'内容は未判定',reason:'資料の内容を確認できませんでした。',action:''};
 if(a.status==='withheld')return {label:'内容の確認が必要です',reason:'資料の内容を確認できませんでした。',action:''};
 if(a.status!=='assessed'||a.scope!=='extracted-text-only')return {label:'内容を判定できませんでした',reason:'資料の内容を確認できませんでした。',action:''};
 const partial=content.status==='partial'?'取得できた一部の文字では、':'取得できた文字では、';
 if(a.audience==='internal')return {label:'院内向け資料の可能性があります',reason:partial+'院内向けの資料と推定されます。公開の意図や情報漏えいの有無は断定できません。',action:''};
 if(a.audience==='patient'&&a.concern==='none'&&content.status==='extracted')return {label:'確認範囲で秘匿情報なし',reason:'確認した範囲では、秘匿情報は見つかりませんでした。',action:''};
 return {label:'内容の確認が必要です',reason:partial+'公開用の案内資料と判断できませんでした。',action:''};
}
function sharingHasIssue(item){
 const a=item.assessment;return item.status==='preview-observed'&&['extracted','partial'].includes(item.content?.status)&&a?.status==='assessed'&&a.scope==='extracted-text-only'&&(a.audience==='internal'||a.concern==='review');
}
function renderSharing(report,root,el){
 const section=el('section','','sharing-review');section.append(el('h3','Google Driveなどの公開範囲'));
 const items=(report.sharing?.items||[]).filter(sharingHasIssue);
 if(!items.length)return;
 if(items.length){
 const wrap=el('div','','evaluation-scroll');const table=el('table','','evaluation-table sharing-table');const head=el('thead',''),header=el('tr','');
 for(const label of ['資料','判定内容']){const cell=el('th',label);cell.scope='col';header.append(cell);}head.append(header);table.append(head);
 const body=el('tbody','');
 items.forEach((item,i)=>{const copy=sharingCopy(item),row=el('tr',''),name=el('th',sharingName(item));name.scope='row';
 if(/^https:\/\//.test(item.url||'')){const link=el('a','資料を見る ↗');link.href=item.url;link.target='_blank';link.rel='noopener';name.append(el('br',''),link);}
 const result=el('td',copy.reason);row.append(name,result);body.append(row);});
 table.append(body);wrap.append(table);section.append(wrap,el('p','用途の判定は取得できた文字に限ります。画像・手書き・編集権限は未確認です。公開されているだけで情報漏えいとは判定しません。','small'));
 }
 root.append(section);
}
global.SimyInformationFlow={model,render,renderPriority,sharingCopy,sharingName,sharingHasIssue,managementCopy};
})(typeof window==='undefined'?globalThis:window);
