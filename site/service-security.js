/* Reviewed official disclosures. This is a dated catalog, not a live news feed. */
(function(global){
'use strict';
const checkedAt='2026-10-28';
const catalog=[
 {id:'drive-shared-20140628',domains:['drive.google.com'],name:'Google Drive',published:'2014-06-28',checkedAt,type:'過去の脆弱性（修正済み）',title:'一部のファイル形式の共有リンク保護を修正',summary:'Googleが一部のファイル形式に関するセキュリティ問題の報告を受け、修正したと公表。',scope:'2014年の修正済み事例です。現在の共有資料にこの問題が残っているという判定ではありません。',url:'https://workspaceupdates.googleblog.com/2014/06/google-drive-update-to-protect-shared.html'},
 {id:'onamae-desktop-20261023',domains:['onamae.com'],provider:'onamae',providerWide:true,name:'お名前.com デスクトップクラウド',published:'2026-10-23',occurred:'2026-10-20（不正プログラム確認）',checkedAt,type:'同じ提供会社の別サービスの事故',title:'サーバーに不正プログラム。保存されたログイン情報が取得された可能性',summary:'デスクトップクラウドで不正アクセスを確認。保存された取引口座のログイン情報等が取得・不正利用された可能性を公表。',scope:'対象はデスクトップクラウド。DNS・ドメイン登録の事故を示す発表ではありません。',url:'https://www.onamae.com/news/article/11595'},
 {id:'nomoca-online-20231020',domains:['nomoca-ai.com'],name:'GENOVA / NOMOCaオンライン診療',published:'2023-10-20',occurred:'2023-10-16（発覚）',checkedAt,type:'同じ提供会社の別サービスの過去事例',title:'クラウドの不正操作でスパム送信・オンライン診療が停止',summary:'外注先のアカウントを使った不正なアカウント作成と大量のスパム送信が発生。提供元は患者情報へのアクセス・流出はないと公表。',scope:'対象はNOMOCaオンライン診療。NOMOCa-AI chatの事故を示すものではありません。',url:'https://genova.co.jp/news/12660'},
 {id:'clara-plesk-20260925',domains:[],provider:'clara',name:'クララ / Pleskの注意喚起',published:'2026-09-25',checkedAt,type:'脆弱性の注意喚起（事故報告ではありません）',title:'サーバー管理ソフトPleskで、強い権限によるファイル書込みのおそれ',summary:'バックアップ機能の脆弱性CVE-2026-68487について注意喚起。ログイン済みの利用者が管理者権限で任意のファイルを書き込めるおそれ。',scope:'Pleskの該当版が対象。このサイトでのPleskの使用・版・被害は未確認。',url:'https://spt.clara.jp/news/info/'},
 {id:'blastmail-20261021',domains:['blastmail.jp'],provider:'blastmail',name:'ブラストメール',published:'2026-10-21',checkedAt,type:'情報漏えい',title:'不正アクセスで契約者情報・一部の配信先情報が流出',summary:'API用サーバーへの侵入からデータが持ち出されたと公表。侵入経路の詳細は調査中で、古いPHPが原因とは断定できません。',scope:'販売管理システムの全契約者の情報と、一部顧客のメール配信情報。',action:'提供元の個別通知・対象データ・連携継続の可否を確認。',url:'https://www.rakus.co.jp/news/2026/1021-3.html'},
 {id:'xserver-20261023',domains:[],provider:'xserver',name:'エックスサーバー（委託先）',published:'2026-10-23',checkedAt,type:'委託先で情報漏えい',title:'メール配信委託先で顧客のメールアドレスが流出',summary:'ブラストメールに登録された配信先が対象。エックスサーバーのサーバー・管理画面への侵入ではありません。',scope:'ニュース等の配信を希望し、委託先に登録されていた顧客。全利用者ではありません。',action:'契約先からの対象者通知・不審メールへの対応を確認。',url:'https://www.xserver.co.jp/news/152'}
];
const services=[['digikar-smart.jp','デジスマ診療'],['nomoca-ai.com','NOMOCA AI'],['doctorsfile.jp','ドクターズ・ファイル'],['googletagmanager.com','Googleタグ'],['google-analytics.com','Google Analytics'],['ajax.googleapis.com','Google Hosted Libraries'],['line.me','LINE'],['stripe.com','Stripe'],['blastmail.jp','ブラストメール']];
function matches(host,domain){return host===domain||host.endsWith('.'+domain);}
function assess(report,now=Date.now()){
 const linked=new Map();
 for(const x of report.integrations||[]){let host;try{host=new URL(x.destination).hostname.toLowerCase();}catch{continue;}const known=services.find(([domain])=>matches(host,domain));const key=known?.[0]||host;const prior=linked.get(key);if(!prior)linked.set(key,{host,name:known?.[1]||host,kind:x.kind,category:x.category});else if(prior.kind==='link'&&x.kind!=='link')prior.kind=x.kind;}
 for(const fact of report.providers?.facts||[]){
  if(!['DNS提供元','ドメイン登録会社','サーバー・ネットワーク'].includes(fact.role)||fact.status==='未確認')continue;
  const key='provider:'+fact.role+':'+(fact.provider||fact.name);
  if(!linked.has(key))linked.set(key,{host:'',name:/d\/b\/a Onamae\.com$/i.test(fact.name)?'お名前.com（GMO Internet Group）':fact.name,kind:'provider',category:fact.role,provider:fact.provider||(/Onamae\.com/i.test(fact.name||'')?'onamae':undefined),status:fact.status,evidence:fact.evidence,source:fact.source});
 }
 const notices=[];
 for(const n of catalog){const connection=[...linked.values()].find(x=>(x.provider&&x.provider===n.provider&&(n.providerWide||x.category==='サーバー・ネットワーク'))||n.domains.some(d=>matches(x.host,d)));const fact=(report.providers?.facts||[]).find(f=>f.provider===n.provider&&f.role==='サーバー・ネットワーク');if(!connection&&!fact)continue;
  const age=(now-Date.parse(n.published))/86400000;
  notices.push({...n,recent:age>=0&&age<=180,stale:now-Date.parse(n.checkedAt)>7*86400000,connection:connection&&connection.kind!=='provider'?(connection.kind==='link'?'リンクを確認（利用契約は未確認）':'埋め込み・読込等の記載を確認'):'サーバー提供元の候補（推定）',impact:'このサイトへの影響は未確認'});
 }
 return {checkedAt,notices,services:[...linked.values()],unmatched:[...linked.values()].filter(x=>!notices.some(n=>(x.provider&&x.provider===n.provider&&(n.providerWide||x.category==='サーバー・ネットワーク'))||n.domains.some(d=>matches(x.host,d))))};
}
// Dated manual research; never represent this as a search performed by each scan.
const researchedDomains=['digikar-smart.jp','nomoca-ai.com','doctorsfile.jp','googletagmanager.com','google-analytics.com','ajax.googleapis.com','drive.google.com','instagram.com','caloo.jp','tokyo-doctors.com','kireireport.com'];
function findingsFor(service,info){return info.notices.filter(n=>(service.provider&&service.provider===n.provider&&(n.providerWide||service.category==='サーバー・ネットワーク'))||n.domains.some(d=>matches(service.host,d)));}
function researchStatus(service){return researchedDomains.some(d=>matches(service.host,d))?'今回のネット調査では、このサービスの事故・脆弱性の公表を特定できませんでした。':'このサービスのネット調査は未実施です。';}
global.SimyServiceSecurity={assess,catalog,findingsFor,researchStatus};
})(typeof window==='undefined'?globalThis:window);
