(function(global){
'use strict';
function discovery(report){
 let origin;try{origin=new URL(report.url).origin;}catch{return null;}
 const candidate=report.aiDiscovery||global.SimyClinicAiObservations?.find(x=>x.origin===origin);
 if(!candidate||candidate.origin!==origin||candidate.brandInQuery!==false||!candidate.sourceUrl?.startsWith('https://agent.tinyfish.ai/runs/')||!Array.isArray(candidate.questions)||!Number.isFinite(Date.parse(candidate.finishedAt)))return null;
 if(!candidate.questions.length||candidate.questions.length>20||candidate.questions.some(q=>!q||typeof q.theme!=='string'||typeof q.query!=='string'||!Array.isArray(q.peers)||q.peers.some(p=>typeof p!=='string')||(q.status==='observed'&&typeof q.mentioned!=='boolean')||!['observed','failed','unavailable'].includes(q.status)))return null;
 const rows=candidate.questions,observed=rows.filter(x=>x.status==='observed'),mentioned=observed.filter(x=>x.mentioned===true),different=observed.filter(x=>x.differentDomainLinks?.length);
 return {...candidate,observed:observed.length,total:rows.length,mentioned:mentioned.length,different:different.length,verified:mentioned.filter(q=>q.officialCitation==='verified'&&q.verifiedDestination&&(()=>{try{return new URL(q.verifiedDestination).origin===origin;}catch{return false;}})()).length,measuredLabel:candidate.datePrecision==='day'?new Date(candidate.finishedAt).toLocaleDateString('ja-JP',{timeZone:'Asia/Tokyo'})+'（取得日）':new Date(candidate.finishedAt).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo',year:'numeric',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'})+' JST',ratio:observed.length?mentioned.length+' / '+observed.length:'未取得'};
}
function journeyAudit(d){
 const a=d?.journeyAudit;if(!a||typeof a.headline!=='string'||typeof a.summary!=='string'||typeof a.scope!=='string'||!Array.isArray(a.confirmed)||a.confirmed.some(x=>typeof x!=='string')||!a.proposal||!['heading','body','button','note'].every(k=>typeof a.proposal[k]==='string')||a.version!==1||!/^\d{4}-\d{2}-\d{2}$/.test(a.checkedOn)||!Array.isArray(a.findings)||a.findings.length>8)return null;
 const safe=u=>{try{return new URL(u).protocol==='https:';}catch{return false;}};
 if(!a.findings.every(x=>['title','observation','impact','change'].every(k=>typeof x[k]==='string'&&x[k].length<500)&&Array.isArray(x.sources)&&x.sources.every(y=>safe(y.url)&&typeof y.label==='string')))return null;
 if(a.confirmedSources&&(!Array.isArray(a.confirmedSources)||!a.confirmedSources.every(s=>safe(s.url)&&typeof s.label==='string')))return null;
 return a;
}
function attach(report){const d=discovery(report);if(d&&!report.aiDiscovery)report.aiDiscovery=JSON.parse(JSON.stringify(global.SimyClinicAiObservations.find(x=>x.origin===d.origin)));return report;}
function model(report){
 const d=discovery(report),audit=journeyAudit(d);
 const g=report.growth, a=g?.status==='assessed'?g.analysis:null;
 const pages=Array.isArray(g?.sources)?g.sources:[];
 const name=a?.clinicName||d?.clinicName||new URL(report.url).hostname;
 if(!a)return {discovery:d,audit,name,available:!!d,contentAvailable:false,headline:audit?.headline||'AI検索での紹介状況',intro:audit?.summary||'別途取得したAI検索の実測記録です。本文の分析は今回完了していません。',scope:'集客分析を完了できませんでした。セキュリティの結果は上に表示しています。',metrics:[],questions:[],priorities:[],strengths:[]};
 const questions=a.questions.map(q=>({...q,status:q.status==='found'?'案内あり':'今回の範囲では見つからず'}));
 const priorities=[...a.priorities];

 return {discovery:d,audit,name,available:true,contentAvailable:true,headline:audit?.headline||(d?.mentioned? 'AI検索で紹介を確認。次は、正しい案内へ。':a.headline),intro:audit?.summary||(d?.mentioned?'医院名を入れない'+d.observed+'つの質問で紹介を確認。公式サイトへの誘導と、受診前の案内を分けて評価しました。':a.summary),contentSummary:a.summary,scope:pages.length+'ページの公開本文を分析。AI検索の実測は、記載した日時・条件での取得結果です。',sources:pages,metrics:[['本文を読んだページ',pages.length+'ページ'],['受診前の疑問への案内',a.questions.filter(q=>q.status==='found').length+' / 5'],['優先して変えたいこと',priorities.length+'件']],strengths:a.strengths,questions,priorities,proposal:{heading:a.proposal.heading,description:a.proposal.body,button:a.proposal.button},checkedAt:report.checkedAt};
}
global.SimyClinicGrowth={model,discovery,attach};
})(typeof window==='undefined'?globalThis:window);
