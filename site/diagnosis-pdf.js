/* Local-only PDF generation. No registration data is sent to another service. */
(function (global) {
  'use strict';
  let dependencies;
  function script(src) { return new Promise((resolve, reject) => { const el = document.createElement('script'); el.src = src; el.onload = resolve; el.onerror = () => { el.remove(); reject(Error('PDFの読込に失敗しました')); }; document.head.append(el); }); }
  async function prepare() {
    if (!dependencies) dependencies = (async () => {
      if (!global.jspdf) await script('/vendor/report-pdf/jspdf-4.2.1.min.js');
      if (!global.jspdf.jsPDF.API.autoTable) await script('/vendor/report-pdf/autotable-5.0.9.min.js');
      const response = await fetch('/vendor/report-pdf/NotoSansJP-Regular.ttf', {signal: AbortSignal.timeout(60000)});
      if (!response.ok) throw Error('日本語フォントを読み込めませんでした');
      const bytes = new Uint8Array(await response.arrayBuffer());
      let binary = ''; for (let i = 0; i < bytes.length; i += 32768) binary += String.fromCharCode(...bytes.subarray(i, i + 32768));
      const icon=await fetch('/simy-icon-56.png');if(!icon.ok)throw Error('SIMYアイコンを読み込めませんでした');
      const iconBytes=new Uint8Array(await icon.arrayBuffer());let iconBinary='';for(const value of iconBytes)iconBinary+=String.fromCharCode(value);
      const boldResponse=await fetch('/vendor/report-pdf/NotoSansJP-Bold.ttf',{signal:AbortSignal.timeout(60000)});
      if(!boldResponse.ok)throw Error('見出しフォントを読み込めませんでした');
      const boldBytes=new Uint8Array(await boldResponse.arrayBuffer());let boldBinary='';for(let i=0;i<boldBytes.length;i+=32768)boldBinary+=String.fromCharCode(...boldBytes.subarray(i,i+32768));
      return {font:btoa(binary),bold:btoa(boldBinary),logo:btoa(iconBinary)};
    })().catch(error => { dependencies = null; throw error; });
    return dependencies;
  }
  const text = value => String(value ?? '').replace(/\r/g, '');
  function model({report, registration, root}) {
    const versions = [...root.querySelectorAll('.evaluation-section .component-version-table tbody tr')].map(row => [...row.children].map(cell => {
      // Preserve line boundaries and full issue/incident details, including collapsed evidence.
      const clone = cell.cloneNode(true);
      clone.querySelectorAll('small,summary,p,li').forEach(n => n.prepend('\n'));
      return clone.textContent.trim();
    }));
    const connections = new Map();
    for (const x of report.integrations || []) { const key = x.kind + '|' + x.destination; const old = connections.get(key); if (old) old.pages.add(x.page); else connections.set(key, {...x, pages: new Set([x.page])}); }
    return {report, registration, versions, connections: [...connections.values()]};
  }
  function create({report, registration = {}, versions = []}, font, JsPDF, logo, bold) {
    const doc = new JsPDF({unit:'mm', format:'a4', orientation:'portrait', compress:true, putOnlyUsedFonts:true});
    doc.addFileToVFS('ReportJP.ttf',font);doc.addFont('ReportJP.ttf','ReportJP','normal');doc.setFont('ReportJP','normal');
    if(bold){doc.addFileToVFS('ReportJP-Bold.ttf',bold);doc.addFont('ReportJP-Bold.ttf','ReportJP','bold');}
    doc.setProperties({title:'SIMY HP管理｜ホームページ診断レポート',author:'SIMY',subject:registration.clinicName||report.url});
    const C={ink:[24,36,47],muted:[100,116,123],blue:[48,127,174],mint:[235,246,244],paper:[255,253,250],pale:[247,246,241],line:[223,223,216],red:[177,72,61]};
    const left=17,width=176,bottom=268;let y=32,section='SUMMARY';
    const date=new Date(report.checkedAt).toLocaleDateString('ja-JP');
    const lines=(s,size,w)=>{doc.setFont('ReportJP',bold&&size>=11?'bold':'normal');doc.setFontSize(size);return doc.splitTextToSize(text(s),w);};
    const height=(s,size,w)=>lines(s,size,w).length*size*.48;
    function write(s,x,top,size=10,w=width,color=C.ink){doc.setFontSize(size);doc.setTextColor(...color);const list=lines(s,size,w);doc.text(list.length===1?list[0]:list,x,top,{lineHeightFactor:1.36});return list.length*size*.48;}
    function box(x,top,w,h,fill=C.paper){doc.setDrawColor(...C.line);doc.setFillColor(...fill);doc.roundedRect(x,top,w,h,3,3,'FD');}
    function page(label){if(doc.getNumberOfPages()>0&&y!==32)doc.addPage();section=label;y=32;doc.setFillColor(...C.paper);doc.rect?.(0,0,210,297,'F');if(logo)doc.addImage(logo,'PNG',left,16,7,7);write('SIMY',logo?27:left,21.5,12,32);write('HP MANAGEMENT',44,21,6,50,C.muted);write(section+' / '+date,132,21,6,61,C.muted);doc.setDrawColor(...C.line);doc.line(left,26,193,26);}
    function ensure(h){if(y+h>bottom){const label=section;page(label.replace(/ \/ CONTINUED$/,'')+' / CONTINUED');}}
    function paragraph(value,size=10,color=C.muted){const list=lines(value,size,width);for(const line of list){ensure(size*.48+2);write(line,left,y,size,width,color);y+=size*.48;}y+=4;}
    function heading(kicker,title,lede){write(kicker,left,y,7,width,C.blue);y+=7;const h=height(title,19,width);write(title,left,y,19);y+=h+4;if(lede)paragraph(lede,9);y+=3;}
    function card(title,body,tag){
      const all=lines(body,9,width-12),limit=35;
      for(let start=0;start<all.length;start+=limit){const chunk=all.slice(start,start+limit).join('\n'),label=title+(start?'（続き）':'');const h=height(label,12,width-12)+height(chunk,9,width-12)+(tag?8:0)+14;ensure(h+5);box(left,y,width,h);let top=y+8;if(tag){write(tag,left+6,top,8,width-12,C.red);top+=8;}top+=write(label,left+6,top,12,width-12)+3;write(chunk,left+6,top,9,width-12,C.muted);y+=h+5;}
    }
    function grid(items,compact=false){for(let i=0;i<items.length;i+=2){const pair=items.slice(i,i+2),w=85,titleSize=compact?11:13,bodySize=compact?8:9;const h=Math.max(...pair.map(a=>height(a[0],titleSize,w-12)+height(a[1],bodySize,w-12)+17+(a[2]?7:0)));ensure(h+5);pair.forEach((a,j)=>{const x=left+j*91;box(x,y,w,h,j===0?C.mint:C.paper);const used=write(a[0],x+6,y+9,titleSize,w-12,C.blue);write(a[1],x+6,y+12+used,bodySize,w-12,C.muted);if(a[2]&&/^https:\/\//.test(a[2])){write('公式発表を開く',x+6,y+h-4,7,w-12,C.blue);doc.link(x+6,y+h-7,w-12,5,{url:a[2]});}});y+=h+5;}}
    function table(title,head,body,widths){if(!body.length)return;ensure(30);paragraph(title,12,C.ink);const columnStyles={};widths.forEach((w,i)=>columnStyles[i]={cellWidth:w});doc.autoTable({startY:y,margin:{left,right:17,top:34,bottom:30},head:[head],body,styles:{font:'ReportJP',fontStyle:'normal',fontSize:8,cellPadding:3,overflow:'linebreak',lineWidth:.15,lineColor:C.line,textColor:C.ink},headStyles:{fillColor:C.pale,textColor:C.muted,fontStyle:'normal'},alternateRowStyles:{fillColor:[250,250,247]},columnStyles,rowPageBreak:'avoid',didDrawPage(data){if(data.pageNumber>1){const saved=y;y=33;pageHeaderOnly();y=saved;}}});y=doc.lastAutoTable.finalY+7;}
    function pageHeaderOnly(){if(logo)doc.addImage(logo,'PNG',left,16,7,7);write('SIMY',logo?27:left,21.5,12,32);write('HP MANAGEMENT',44,21,6,50,C.muted);doc.setDrawColor(...C.line);doc.line(left,26,193,26);}
    const security=global.SimyServiceSecurity?.assess(report);
    const externalServices=security?global.SimyServiceSecurity.visibleServices(security):[];
    const notices=[...new Map((security?global.SimyServiceSecurity.visibleServices(security).flatMap(s=>global.SimyServiceSecurity.findingsFor(s,security)):[]).map(n=>[n.id||n.url,n])).values()];
    const componentNotices=[...new Map((security?(global.SimyServiceSecurity.componentServices?.(security)||[]).flatMap(s=>global.SimyServiceSecurity.findingsFor(s,security)):[]).map(n=>[n.id||n.url,n])).values()];
    const providerNotices=global.SimyServiceSecurity?.providerNotices(report)||report.providers?.notices||[];
    const findings=(report.findings||[]).filter(f=>f.state==='review');
    const flow=global.SimyInformationFlow?.model(report)||[];
    const sharing=(report.sharing?.items||[]).filter(x=>global.SimyInformationFlow?.sharingHasIssue(x));
    const components=versions.map(row=>({name:row[0],current:row[1],latest:row[2],assessment:row[3]}));
    const mail='mailto:sales@simy.one?subject='+encodeURIComponent('ホームページ診断の相談：'+(registration.clinicName||report.url))+'&body='+encodeURIComponent('SIMY ご担当者様\r\n\r\n医療機関名：'+(registration.clinicName||'')+'\r\nご担当者名：'+(registration.contactName||'')+'\r\nホームページURL：'+report.url+'\r\nご用件：診断結果について\r\n\r\nご相談内容：\r\n\r\n診断ID：'+(report.diagnosisId||''));
    function contact(){ensure(28);box(left,y,width,24,C.mint);write('この診断結果を、SIMYに相談する',left+6,y+9,12,width-12);write('お問い合わせ：sales@simy.one',left+6,y+17,10,width-12,C.blue);doc.link(left,y,width,24,{url:mail});y+=30;}
    page('SUMMARY');
    const clinic=registration.clinicName||new URL(report.url).hostname;
    const heroTitle=clinic+'\nホームページ診断レポート';
    const heroHeight=height(heroTitle,21,width-16)+40;box(left,y,width,heroHeight,C.pale);
    write('SECURITY, EVERY DAY',left+8,y+10,8,width-16,C.blue);
    const heroText=write(heroTitle,left+8,y+23,21,width-16);
    write('先生のホームページは、SIMYが見守ります。',left+8,y+29+heroText,11,width-16,C.blue);y+=heroHeight+7;
    paragraph('診断対象：'+report.url,8);paragraph('確認日時：'+new Date(report.checkedAt).toLocaleString('ja-JP')+'\n診断ID：'+(report.diagnosisId||'未取得'),7);
    if(report.completion==='partial')paragraph('一部完了：'+report.completionReason,9,C.red);
    heading('AT A GLANCE','主な確認結果');
    grid([[''+components.filter(c=>/サポート終了/.test(c.assessment)).length+'件 / サポートが終了した部品',components.filter(c=>/サポート終了/.test(c.assessment)).map(c=>c.name.split('\n')[0]+' '+c.current.split('\n')[0]).join('、')||'今回の範囲では特定していません。'],[''+components.filter(c=>/サポート終了|脆弱性|旧バージョン/.test(c.assessment)).length+'件 / 脆弱性・更新リスク','公開情報から確認できた部品の版を、公式情報と比較しています。'],[''+new Set([...componentNotices,...notices,...providerNotices].map(n=>n.url)).size+'件 / 関連する公表情報','関連する提供元・サービスの事故や脆弱性の公表です。この医院の被害を示すものではありません。'],[''+findings.length+'件 / その他の改善点','公開ページで見直しが必要な設定などを確認しています。']]);
    paragraph('公開情報に基づく診断です。古い部品があるだけで攻撃可能とは限りません。侵入・情報漏えいの有無は判定できません。',8);
    page('RISKS TO PATIENTS & CLINIC');heading('IF LEFT UNADDRESSED','放置した場合の影響は、\n患者さんと診療にも及びます。','以下は起こり得るリスクの説明です。この診断で、被害や改ざんの発生を確認したという意味ではありません。');
    card('01 / 患者さんが偽の予約先へ誘導されるおそれ','改ざんによって予約リンクがすり替えられたり、悪意のあるプログラムが埋め込まれたりすることがあります。患者さんが偽の予約画面に個人情報を入力し、詐欺やマルウェアの被害を受けるおそれがあります。');
    card('02 / Googleが「危険なサイト」と警告','不正な内容やマルウェアが検出されると、Googleの検索結果やChromeに「危険なサイト」などの警告が表示される場合があります。患者さんがアクセスや予約をためらい、来院機会や医院への信頼を失うおそれがあります。');
    card('03 / 他システムに被害が広がるおそれ','同じサーバー環境や認証情報を他システムと共有している場合、侵入の足掛かりにされ、被害が広がる可能性があります。予約停止や情報漏えいの調査・復旧に追われ、受付や診療の継続にも負担がかかります。');
    paragraph('被害の広がり方は、接続関係・認証情報の共有・権限の設定によって異なります。公開URLの診断だけでは、院内ネットワークとの接続や侵入の有無は分かりません。',8);
    contact();
    page('SIMY SERVICE');heading('WHY SIMY / AFTER THE DIAGNOSIS','診断・修正・監視を、\nひとつのサービスに。','公開後も必要な対策を続けるために。修正情報の確認、更新、動作確認、バックアップ、稼働監視までSIMYが対応します。');
    grid([['24時間以内','セキュリティ修正が公開されたら、24時間以内に確認・対応を開始。AIが医院への影響を確認し、必要な更新を進めます。'],['24時間365日','ホームページの稼働状況を自動監視。異常を検知した場合は状況を確認します。'],['多層防御','WAF、海外アクセス制限、DDoS・Bot対策、攻撃ログの確認など。セキュリティ強化プランで対応します。'],['更新から復元まで','必要な修正を適用し、表示や主要機能を確認。バックアップで復元にも備えます。']]);
    heading('MONTHLY MANAGEMENT','保守プランは2種類です。');
    grid([['基本保守 / 月額14,800円','税込16,280円。修正対応・動作確認・バックアップ・稼働監視・サーバー管理。医院がご契約のChatGPT・Claude Codeへの接続を支援します。'],['セキュリティ強化 / 月額29,800円','税込32,780円。基本保守に加え、WAF・海外アクセス制限・DDoSやBot対策・攻撃ログ確認などに対応します。']]);
    paragraph('更新代行は月額35,000円（税別）を追加。MEO（Googleマップ対策）＋GEO（AI検索対策）を含みます。地図・口コミ対応と、AIにも伝わる医院情報の整備を支援します。',9);
    paragraph('ドメインの新規取得費用・更新費用は別途です。',8);contact();
    if(components.length||componentNotices.length){page('COMPONENTS');heading('01 / SOFTWARE COMPONENTS','使用部品の脆弱性・更新リスク','検出した版と公式情報を比較しています。使用箇所や修正の適用状況により、実際の影響は異なります。');
      for(const c of components){const name=c.name.split('\n'),a=c.current.split('\n'),b=c.latest.split('\n');const detailLines=lines(c.assessment,9,164),details=detailLines.slice(0,24).join('\n');const h=50+Math.max(height(c.current,10,66),height(c.latest,10,66))+height(details,9,164)+12;ensure(h+5);box(left,y,width,h);write(name[0],left+6,y+9,14,164);if(name[1])write(name.slice(1).join(' '),left+6,y+15,8,164,C.muted);const top=y+24;box(left+6,top,76,Math.max(height(c.current,10,66),height(c.latest,10,66))+14,C.pale);box(left+94,top,76,Math.max(height(c.current,10,66),height(c.latest,10,66))+14,C.pale);write('確認したバージョン',left+10,top+6,7,68,C.muted);write('確認時点の最新安定版',left+98,top+6,7,68,C.muted);write(c.current,left+10,top+13,10,66,/サポート終了|脆弱性|旧バージョン/.test(c.assessment)?C.red:C.ink);write(c.latest,left+98,top+13,10,66);const below=top+Math.max(height(c.current,10,66),height(c.latest,10,66))+20;write(details,left+6,below,9,164,C.muted);y=Math.max(y+h+5,below+height(details,9,164)+8);if(detailLines.length>24)card(name[0]+' / 公表情報の続き',detailLines.slice(24).join('\n'));}
    }
    if(componentNotices.length){heading('COMPONENT DISCLOSURES','検出した部品に関する公表情報','過去の公表事例です。検出した版への該当性や、このサイトの被害を示すものではありません。');grid(componentNotices.map(n=>[n.name+' / '+n.title,n.type+' / 公表 '+n.published+'\n'+n.summary+'\n'+(n.affectedVersions?'公表された影響版：'+n.affectedVersions+'\n':'')+n.scope,n.url]),true);}
    const facts=global.SimyServiceSecurity?.providerFacts?.(report)||(report.providers?.facts||[]).filter(f=>f.role!=='現在の保守・契約担当');
    if(facts.length||providerNotices.length){page('INFRASTRUCTURE');heading('02 / DOMAIN & SERVER','ドメイン・サーバーについて','公開情報から確認・推定した管理先と、提供元が公表している事故・障害情報です。');grid(providerNotices.map(n=>[(n.name?n.name+' / ':'')+n.title,'公表 '+n.published+'\n'+n.summary+'\n対象：'+(n.scope||'公表内容をご参照ください。')+'\n'+(n.resolution||''),n.url]),true);table('公開情報から確認した管理先',['項目','提供元','判定'],facts.map(f=>[f.role,f.name||'未特定',f.status||'未確認']),[40,108,28]);paragraph('提供元の過去の公表です。この医院での被害や、同じ製品・契約であることを示すものではありません。',8);}
    if(externalServices.length||notices.length){page('PUBLIC ADVISORIES');heading('03 / PUBLIC ADVISORIES','外部サービス・接続先の一覧','検出した接続先を全件掲載しています。リンクの記載だけでサービスの利用契約や情報送信を確認したものではありません。');table('外部サービス・接続先',['サービス・接続先','事故・脆弱性の調査結果'],externalServices.map(s=>[s.name+'\n'+(s.category||''),global.SimyServiceSecurity.findingsFor(s,security).map(n=>n.type+'：'+n.title).join('\n')||global.SimyServiceSecurity.inventoryResearchStatus(s,security)]),[58,118]);grid(notices.map(n=>[n.name+' / '+n.title,'公表 '+n.published+'\n'+n.summary+'\n対象：'+(n.scope||'公表内容をご参照ください。')+'\n'+(n.resolution||''),n.url]),true);}
    paragraph(security?.research?.status==='completed'?'診断時に公式情報を検索しました。':security?.research?.status==='partial'?'診断時の検索・一次情報確認は一部のみ完了しました。':'診断時の検索は未実施または取得できませんでした。事前確認の公表事例を含みます。',8);
    const mainFlow=flow.filter(g=>!g.kinds.every(k=>k==='link')||/予約|問診|診療|決済|ログイン/.test(g.categories.join(' '))||g.sharing.length);
    if(mainFlow.length){page('EXTERNAL CONNECTIONS');heading('04 / EXTERNAL CONNECTION MAP','ホームページが利用する外部サービス','接続先の記載と、患者情報の送信は別です。外部サービス内部の保存先・保存期間は、この診断では分かりません。');card('医院のホームページ → 閲覧者のブラウザー → 外部サービス','公開ページの表示・外部プログラムの読込・予約などの接続関係を整理しています。');
      const grouped=new Map();for(const g of mainFlow){const key=g.category;const item=grouped.get(key)||{domains:[],reason:global.SimyInformationFlow.managementCopy(g).reason};item.domains.push(g.domain);grouped.set(key,item);}grid([...grouped].map(([category,g])=>[category,[...new Set(g.domains)].join('\n')+'\n'+g.reason]),true);}
    if(findings.length||sharing.length){page('RECOMMENDATIONS');heading('05 / RECOMMENDATIONS','その他おすすめの改善点','診断で見つかった問題・見直しが必要な点だけを記載しています。');for(const f of findings)card(f.title,f.summary);table('共有資料の公開範囲',['資料','確認した内容'],sharing.map(x=>[global.SimyInformationFlow.sharingName(x),global.SimyInformationFlow.sharingCopy(x).reason]),[58,118]);}
    paragraph('今回の確認は公開情報の範囲です。サーバー内部、データベース、ログイン後、電子カルテ・予約サービス内部、侵入や漏えいの有無は調査していません。',8);contact();
    page('MIGRATION');heading('DIAGNOSIS TO ACTION','今のホームページを、SIMYへ。','URLも、見慣れたデザインも。医院には情報の受け取りと内容の確認をお願いします。準備から公開までSIMYが進めます。');
    card('01 / 今の管理会社から、移管情報を受け取ります。','HTML・画像・管理情報を受け取ります。ドメイン登録会社の移管が必要なら「AuthCode（オースコード）」も依頼します。必要な依頼内容はSIMYがご案内します。');
    card('02 / 今の見た目を、最新の技術で作り直します。','既存データを引き継ぐか、同じ見た目・内容を最新技術で無料で再制作します。必要な権利・許諾と対象範囲を確認して着手し、公開前に先生に画面をご確認いただきます。');
    card('03 / 同じURLで公開し、ChatGPTへ接続します。','ドメイン設定・公開先を切り替えます。予約・フォーム・メールへの影響を確認し、医院のChatGPTを更新環境へ接続します。プレビューを確認して公開できます。');
    paragraph('無料再制作はHP管理をご契約いただく場合に、権利・許諾を確認できた事前合意の範囲で対応します。外部サービス内部・追加機能は別途確認。月額保守料、ドメイン移管実費、AIサービス契約・利用料等は別途です。',8);contact();
    page('RIGHTS & CONTACT');heading('BEFORE THE MIGRATION','権利の確認から、\nSIMYがお手伝いします。');
    card('医院が権利をお持ちの場合','契約上、利用できる範囲を確認して引き継ぎます。');card('制作会社などが権利を持つ場合','データ引き渡し・移設・作り替え・公開・今後の更新について、権利者の許可を得て進めます。確認事項や依頼文はSIMYがご案内します。');card('許可を得られない素材がある場合','そのデザイン・文章・写真などは使用せず、新しく制作・差し替えます。');
    paragraph('同じ見た目・内容での再制作は必要な権利・許諾を確認できた範囲で対応します。写真素材・フォント・テンプレートの利用条件も確認し、許諾の対象と範囲を書面やメールで残します。',8);
    contact();
    const count=doc.getNumberOfPages();for(let i=1;i<=count;i++){doc.setPage(i);doc.setDrawColor(...C.line);doc.line(left,280,193,280);write('SIMY HP管理 · 公開情報に基づく確認レポート',left,285,6,115,C.muted);write('sales@simy.one',left,290,7,110,C.blue);doc.link(left,286,75,6,{url:mail});write(i+' / '+count,178,286,7,15,C.muted);}
    return doc;
  }
  async function download(input) { const assets = await prepare(); const doc = create(model(input), assets.font, global.jspdf.jsPDF, assets.logo, assets.bold); doc.save('SIMY_ホームページ診断_' + new Date(input.report.checkedAt).toISOString().slice(0, 10) + '.pdf'); }
  global.SimyReportPdf = {download, create, model};
})(typeof window === 'undefined' ? globalThis : window);
