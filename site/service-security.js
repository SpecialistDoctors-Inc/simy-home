/* Reviewed official disclosures. This is a dated catalog, not a live news feed. */
(function(global){
'use strict';
const checkedAt='2026-10-28';
const catalog=[
 {id:'blastmail-20261021',domains:['blastmail.jp'],provider:'blastmail',name:'ブラストメール',published:'2026-10-21',checkedAt,type:'情報漏えい',title:'不正アクセスで契約者情報・一部の配信先情報が流出',summary:'API用サーバーへの侵入からデータが持ち出されたと公表。侵入経路の詳細は調査中で、古いPHPが原因とは断定できません。',scope:'販売管理システムの全契約者の情報と、一部顧客のメール配信情報。',action:'SIMYと、提供元の個別通知・対象データ・連携継続の可否を確認。',url:'https://www.rakus.co.jp/news/2026/1021-3.html'},
 {id:'xserver-20261023',domains:[],provider:'xserver',name:'エックスサーバー（委託先）',published:'2026-10-23',checkedAt,type:'委託先で情報漏えい',title:'メール配信委託先で顧客のメールアドレスが流出',summary:'ブラストメールに登録された配信先が対象。エックスサーバーのサーバー・管理画面への侵入ではありません。',scope:'ニュース等の配信を希望し、委託先に登録されていた顧客。全利用者ではありません。',action:'SIMYと、契約先からの対象者通知・不審メールへの対応を確認。',url:'https://www.xserver.co.jp/news/152'}
];
const services=[['digikar-smart.jp','デジスマ診療'],['nomoca-ai.com','NOMOCA AI'],['doctorsfile.jp','ドクターズ・ファイル'],['googletagmanager.com','Googleタグ'],['google-analytics.com','Google Analytics'],['ajax.googleapis.com','Google Hosted Libraries'],['line.me','LINE'],['stripe.com','Stripe'],['blastmail.jp','ブラストメール']];
function matches(host,domain){return host===domain||host.endsWith('.'+domain);}
function assess(report,now=Date.now()){
 const linked=new Map();
 for(const x of report.integrations||[]){let host;try{host=new URL(x.destination).hostname.toLowerCase();}catch{continue;}const known=services.find(([domain])=>matches(host,domain));const key=known?.[0]||host;const prior=linked.get(key);if(!prior)linked.set(key,{host,name:known?.[1]||host,kind:x.kind,category:x.category});else if(prior.kind==='link'&&x.kind!=='link')prior.kind=x.kind;}
 for(const fact of report.providers?.facts||[]){
  if(!['DNS提供元','ドメイン登録会社','サーバー・ネットワーク'].includes(fact.role)||fact.status==='未確認')continue;
  const key='provider:'+fact.role+':'+(fact.provider||fact.name);
  if(!linked.has(key))linked.set(key,{host:'',name:/d\/b\/a Onamae\.com$/i.test(fact.name)?'お名前.com（GMO Internet Group）':fact.name,kind:'provider',category:fact.role,provider:fact.provider,status:fact.status,evidence:fact.evidence,source:fact.source});
 }
 const notices=[];
 for(const n of catalog){const connection=[...linked.values()].find(x=>(x.provider&&x.provider===n.provider&&x.category==='サーバー・ネットワーク')||n.domains.some(d=>matches(x.host,d)));const fact=(report.providers?.facts||[]).find(f=>f.provider===n.provider&&f.role==='サーバー・ネットワーク');if(!connection&&!fact)continue;
  const age=(now-Date.parse(n.published))/86400000;
  notices.push({...n,recent:age>=0&&age<=180,stale:now-Date.parse(n.checkedAt)>7*86400000,connection:connection&&connection.kind!=='provider'?(connection.kind==='link'?'リンクを確認（利用契約は未確認）':'埋め込み・読込等の記載を確認'):'サーバー提供元の候補（推定）',impact:'このサイトへの影響は未確認'});
 }
 for(const n of report.providers?.notices||[]){
  if(notices.some(x=>x.url===n.url))continue;
  const age=(now-Date.parse(n.published))/86400000;
  notices.push({...n,name:n.publisher,type:'提供元の公式発表',recent:age>=0&&age<=180,stale:now-Date.parse(n.checkedAt)>7*86400000,domains:[],connection:'公開情報で確認した提供元に関連',impact:'このサイトへの影響は未確認'});
 }
 return {checkedAt,notices,services:[...linked.values()],unmatched:[...linked.values()].filter(x=>!notices.some(n=>(x.provider&&x.provider===n.provider&&x.category==='サーバー・ネットワーク')||n.domains.some(d=>matches(x.host,d))))};
}
global.SimyServiceSecurity={assess,catalog};
})(typeof window==='undefined'?globalThis:window);
