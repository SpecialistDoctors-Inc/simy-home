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
      const illustrations={};for(const [key,path] of Object.entries({content:'/assets/website-check/clinic-content-journey.png',consultation:'/assets/website-check/clinic-provider-review-v2.png'})){const response=await fetch(path,{signal:AbortSignal.timeout(30000)});if(!response.ok)throw Error('レポート画像を読み込めませんでした');const bytes=new Uint8Array(await response.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));illustrations[key]='data:image/png;base64,'+btoa(binary);}
      return {font:btoa(binary),bold:btoa(boldBinary),logo:btoa(iconBinary),illustrations};
    })().catch(error => { dependencies = null; throw error; });
    return dependencies;
  }
  const text = value => String(value ?? '').replace(/\r/g, '');
  function model({report, registration, root}) {
    const versions = [...root.querySelectorAll('.evaluation-section .component-version-table tbody tr')].map(row => [...row.children].map(cell => {
      // Preserve line boundaries and full issue/incident details, including collapsed evidence.
      const clone = cell.cloneNode(true);
      clone.querySelectorAll('a').forEach(a => { if(a.href && a.closest('.component-disclosure')) a.append(' '+a.href); });
      clone.querySelectorAll('small,summary,p,li').forEach(n => n.prepend('\n'));
      return clone.textContent.trim();
    }));
    const connections = new Map();
    for (const x of report.integrations || []) { const key = x.kind + '|' + x.destination; const old = connections.get(key); if (old) old.pages.add(x.page); else connections.set(key, {...x, pages: new Set([x.page])}); }
    return {report, registration, versions, connections: [...connections.values()]};
  }
  function create({report, registration = {}, versions = []}, font, JsPDF, logo, bold, illustrations={}) {
    const doc = new JsPDF({unit:'mm', format:'a4', orientation:'portrait', compress:true, putOnlyUsedFonts:true});
    doc.addFileToVFS('ReportJP.ttf',font);doc.addFont('ReportJP.ttf','ReportJP','normal');doc.setFont('ReportJP','normal');
    if(bold){doc.addFileToVFS('ReportJP-Bold.ttf',bold);doc.addFont('ReportJP-Bold.ttf','ReportJP','bold');}
    doc.setProperties({title:'SIMY HP管理｜ホームページ診断レポート',author:'SIMY',subject:registration.clinicName||report.url});
    const C={ink:[24,36,47],muted:[100,116,123],blue:[48,127,174],mint:[255,255,255],paper:[255,255,255],pale:[255,255,255],line:[223,223,216],red:[177,72,61]};
    const left=17,width=176,bottom=268;let y=32,section='SUMMARY';
    const date=new Date(report.checkedAt).toLocaleDateString('ja-JP');
    const lines=(s,size,w)=>{doc.setFont('ReportJP',bold&&size>=11?'bold':'normal');doc.setFontSize(size);return doc.splitTextToSize(text(s),w);};
    const height=(s,size,w)=>lines(s,size,w).length*size*.52;
    function write(s,x,top,size=10,w=width,color=C.ink){doc.setFontSize(size);doc.setTextColor(...color);const list=lines(s,size,w);doc.text(list.length===1?list[0]:list,x,top,{lineHeightFactor:1.45});return list.length*size*.52;}
    function box(x,top,w,h,fill=C.paper){doc.setDrawColor(...C.line);doc.setFillColor(...fill);doc.roundedRect(x,top,w,h,3,3,'FD');}
    function page(label){if(doc.getNumberOfPages()>0&&y!==32)doc.addPage();section=label;y=32;doc.setFillColor(...C.paper);doc.rect?.(0,0,210,297,'F');if(logo)doc.addImage(logo,'PNG',left,16,7,7);write('SIMY',logo?27:left,21.5,12,32);write('HP MANAGEMENT',44,21,6,50,C.muted);write(section+' / '+date,132,21,6,61,C.muted);doc.setDrawColor(...C.line);doc.line(left,26,193,26);}
    function ensure(h){if(y+h>bottom){const label=section;page(label.replace(/ \/ CONTINUED$/,'')+' / CONTINUED');}}
    function paragraph(value,size=10,color=C.muted){const list=lines(value,size,width);if(list.length<=5)ensure(list.length*size*.52+4);for(const line of list){ensure(size*.52+2);write(line,left,y,size,width,color);y+=size*.52;}y+=4;}
    function heading(kicker,title,lede){
      const titleSize=kicker==='MONTHLY MANAGEMENT'?16:19;
      if(y>32)y+=12;
      ensure(8+height(title,titleSize,width)+(lede?height(lede,9,width)+9:0)+22);
      write(kicker,left,y,7,width,C.blue);y+=8;
      const h=height(title,titleSize,width);write(title,left,y,titleSize);y+=h+2;
      if(lede){y+=3;paragraph(lede,9);}y+=3;
    }
    function card(title,body,tag){
      const all=lines(body,9,width-12),limit=35;
      for(let start=0;start<all.length;start+=limit){const chunk=all.slice(start,start+limit).join('\n'),label=title+(start?'（続き）':'');const h=height(label,12,width-12)+height(chunk,9,width-12)+(tag?8:0)+14;ensure(h+5);box(left,y,width,h);let top=y+8;if(tag){write(tag,left+6,top,8,width-12,C.red);top+=8;}top+=write(label,left+6,top,12,width-12)+3;write(chunk,left+6,top,9,width-12,C.muted);y+=h+5;}
    }
    function grid(items,compact=false){for(let i=0;i<items.length;i+=2){const pair=items.slice(i,i+2),w=85,titleSize=compact?10:13,bodySize=compact?8:9;const h=Math.max(...pair.map(a=>height(a[0],titleSize,w-12)+height(a[1],bodySize,w-12)+(compact?11:17)+(a[2]?7:0)));ensure(h+5);pair.forEach((a,j)=>{const x=left+j*91;box(x,y,w,h,j===0?C.mint:C.paper);const used=write(a[0],x+6,y+9,titleSize,w-12,C.blue);write(a[1],x+6,y+12+used,bodySize,w-12,C.muted);if(a[2]&&/^https:\/\//.test(a[2])){write('公式発表を開く',x+6,y+h-4,7,w-12,C.blue);doc.link(x+6,y+h-7,w-12,5,{url:a[2]});}});y+=h+5;}}
    function table(title,head,body,widths){if(!body.length)return;ensure(30);paragraph(title,12,C.ink);const columnStyles={};widths.forEach((w,i)=>columnStyles[i]={cellWidth:w});doc.autoTable({startY:y,margin:{left,right:17,top:34,bottom:30},head:[head],body,styles:{font:'ReportJP',fontStyle:'normal',fontSize:8,cellPadding:2.5,overflow:'linebreak',lineWidth:.15,lineColor:C.line,textColor:C.ink},headStyles:{fillColor:C.pale,textColor:C.muted,fontStyle:'normal'},alternateRowStyles:{fillColor:[255,255,255]},columnStyles,rowPageBreak:'avoid',didDrawPage(data){if(data.pageNumber>1){const saved=y;y=33;pageHeaderOnly();y=saved;}}});y=doc.lastAutoTable.finalY+7;}
    function pageHeaderOnly(){if(logo)doc.addImage(logo,'PNG',left,16,7,7);write('SIMY',logo?27:left,21.5,12,32);write('HP MANAGEMENT',44,21,6,50,C.muted);doc.setDrawColor(...C.line);doc.line(left,26,193,26);}
    const security=global.SimyServiceSecurity?.assess(report);
    const externalServices=security?global.SimyServiceSecurity.visibleServices(security):[];
    const notices=[...new Map((security?global.SimyServiceSecurity.visibleServices(security).flatMap(s=>global.SimyServiceSecurity.findingsFor(s,security)):[]).map(n=>[n.id||n.url,n])).values()];
    const componentNotices=[...new Map((security?(global.SimyServiceSecurity.componentServices?.(security)||[]).flatMap(s=>global.SimyServiceSecurity.findingsFor(s,security)):[]).map(n=>[n.id||n.url,n])).values()];
    const providerNotices=global.SimyServiceSecurity?.providerNotices(report)||report.providers?.notices||[];
    const searchFindings=(report.findings||[]).filter(f=>/^(?:seo|sem|geo)-/.test(f.id));
    const findings=(report.findings||[]).filter(f=>f.state==='review'&&!/^(?:seo|sem|geo)-/.test(f.id));
    const flow=global.SimyInformationFlow?.model(report)||[];
    const sharing=(report.sharing?.items||[]).filter(x=>global.SimyInformationFlow?.sharingHasIssue(x));
    const components=versions.map(row=>({name:row[0],current:row[1],latest:row[2],assessment:row[3]}));
    const mail='mailto:sales@simy.one?subject='+encodeURIComponent('ホームページ診断の相談：'+(registration.clinicName||report.url))+'&body='+encodeURIComponent('SIMY ご担当者様\r\n\r\n医療機関名：'+(registration.clinicName||'')+'\r\nご担当者名：'+(registration.contactName||'')+'\r\nホームページURL：'+report.url+'\r\nご用件：診断結果について\r\n\r\nご相談内容：\r\n\r\n診断ID：'+(report.diagnosisId||''));
    function illustration(key,w=176){if(!illustrations[key])return;const h=w*2/3;ensure(h+8);doc.addImage(illustrations[key],'PNG',left+(width-w)/2,y,w,h);y+=h+8;}
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
    const countLabel=n=>n?String(n)+(report.completion==='partial'?'件以上':'件'):(!components.length||report.completion==='partial'?'未確認':'0件');
    grid([[countLabel(components.filter(c=>/サポート終了/.test(c.assessment)).length)+' / サポートが終了した部品',components.filter(c=>/サポート終了/.test(c.assessment)).map(c=>c.name.split('\n')[0]+' '+c.current.split('\n')[0]).join('、')||'今回の範囲では特定していません。'],[countLabel(components.filter(c=>/サポート終了|脆弱性|旧バージョン/.test(c.assessment)).length)+' / 脆弱性・更新リスク','公開情報から確認できた部品の版を、公式情報と比較しています。'],[''+new Set([...componentNotices,...notices,...providerNotices].map(n=>n.url)).size+'件 / 関連する公表情報','提供元・サービスの公表情報です。この医院の被害を示すものではありません。'],[''+findings.length+'件 / その他の改善点','公開ページで見直しが必要な設定などを確認しています。']]);
    paragraph('公開情報に基づく診断です。古い部品があるだけで攻撃可能とは限りません。侵入・情報漏えいの有無は判定できません。',8);paragraph('今回の確認は公開情報の範囲です。サーバー内部、データベース、ログイン後、電子カルテ・予約サービス内部、侵入や漏えいの有無は調査していません。',8);
    page('RISKS TO PATIENTS & CLINIC');heading('IF LEFT UNADDRESSED','ホームページの問題は、\n患者さんの受診にも関わります。','以下は起こり得るリスクの説明です。この診断で、被害や改ざんの発生を確認したという意味ではありません。');
    illustration('consultation',120);card('01 / 患者さんが偽の予約先へ誘導されるおそれ','予約リンクの改ざんで、患者さんが偽の画面に誘導されるおそれがあります。');
    card('02 / Googleが「危険なサイト」と警告','不正な内容が検出されると、検索結果やChromeに警告が表示され、閲覧や予約をためらう原因になります。');
    card('03 / 他システムに被害が広がるおそれ','同じ環境や認証情報を共有している場合、他システムに被害が広がる可能性があります。');
    paragraph('接続・権限の設定によって影響は異なります。公開URLだけでは院内への侵入の有無は分かりません。',8);
    page('SIMY SERVICE');heading('WHY SIMY / AFTER THE DIAGNOSIS','診断・修正・監視を、\nひとつのサービスに。','公開後も必要な対策を続けるために。修正情報の確認、更新、動作確認、バックアップ、稼働監視までSIMYが対応します。');
    grid([['24時間以内','セキュリティ修正が公開されたら、24時間以内に確認・対応を開始。AIが医院への影響を確認し、必要な更新を進めます。'],['24時間365日','ホームページの稼働状況を自動監視。異常を検知した場合は状況を確認します。'],['多層防御','WAF、海外アクセス制限、DDoS・Bot対策、攻撃ログの確認など。セキュリティ強化プランで対応します。'],['更新から復元まで','必要な修正を適用し、表示や主要機能を確認。バックアップで復元にも備えます。']]);
    heading('MONTHLY MANAGEMENT','保守プランは2種類です。');
    grid([['基本保守 / 月額19,800円','税込21,780円。修正対応・動作確認・バックアップ・稼働監視・サーバー管理。医院がご契約のChatGPT・Claude Codeへの接続を支援します。'],['セキュリティ強化 / 月額29,800円','税込32,780円。基本保守に加え、WAF・海外アクセス制限・DDoSやBot対策・攻撃ログ確認などに対応します。']]);
    paragraph('更新代行は両コース共通で月額49,800円（税別・税込54,780円）を追加。MEO（Googleマップ対策）＋GEO（AI検索対策）を含みます。地図・口コミ対応と、AIにも伝わる医院情報の整備を支援します。',9);
    paragraph('ドメインの新規取得費用・更新費用は別途です。',8);
    if(components.length||componentNotices.length){page('COMPONENTS');heading('01 / SOFTWARE COMPONENTS','使用部品の脆弱性・更新リスク','検出した版と公式情報を比較しています。使用箇所や修正の適用状況により、実際の影響は異なります。');
      for(const c of components){const name=c.name.split('\n'),a=c.current.split('\n'),b=c.latest.split('\n');const detailLines=lines(c.assessment,9,164),details=detailLines.slice(0,24).join('\n');const h=50+Math.max(height(c.current,10,66),height(c.latest,10,66))+height(details,9,164)+12;ensure(h+5);box(left,y,width,h);write(name[0],left+6,y+9,14,164);if(name[1])write(name.slice(1).join(' '),left+6,y+15,8,164,C.muted);const top=y+24;box(left+6,top,76,Math.max(height(c.current,10,66),height(c.latest,10,66))+14,C.pale);box(left+94,top,76,Math.max(height(c.current,10,66),height(c.latest,10,66))+14,C.pale);write('確認したバージョン',left+10,top+6,7,68,C.muted);write('確認時点の最新安定版',left+98,top+6,7,68,C.muted);write(c.current,left+10,top+13,10,66,/サポート終了|脆弱性|旧バージョン/.test(c.assessment)?C.red:C.ink);write(c.latest,left+98,top+13,10,66);const below=top+Math.max(height(c.current,10,66),height(c.latest,10,66))+20;write(details,left+6,below,9,164,C.muted);y=Math.max(y+h+5,below+height(details,9,164)+8);if(detailLines.length>24)card(name[0]+' / 公表情報の続き',detailLines.slice(24).join('\n'));}
    }
    const facts=global.SimyServiceSecurity?.providerFacts?.(report)||(report.providers?.facts||[]).filter(f=>f.role!=='現在の保守・契約担当');
    if(facts.length||providerNotices.length){page('INFRASTRUCTURE');heading('02 / DOMAIN & SERVER','ドメイン・サーバーについて','公開情報から確認・推定した管理先と、提供元が公表している事故・障害情報です。');paragraph('提供元の過去の公表です。この医院での被害や、同じ製品・契約であることを示すものではありません。',8);grid(providerNotices.map(n=>[(n.name?n.name+' / ':'')+n.title,'公表 '+n.published+'\n'+n.summary+'\n対象：'+(n.scope||'公表内容をご参照ください。')+'\n'+(n.resolution||''),n.url]),true);table('公開情報から確認した管理先',['項目','提供元','判定'],facts.map(f=>[f.role,f.name||'未特定',f.status||'未確認']),[40,108,28]);}
    if(externalServices.length||notices.length){page('PUBLIC ADVISORIES');heading('03 / PUBLIC ADVISORIES','外部サービス・接続先の一覧','検出した接続先を全件掲載しています。リンクの記載だけでサービスの利用契約や情報送信を確認したものではありません。');table('外部サービス・接続先',['サービス・接続先','事故・脆弱性の調査結果'],externalServices.map(s=>[s.name+'\n'+(s.category||''),global.SimyServiceSecurity.findingsFor(s,security).map(n=>n.type+'：'+n.title).join('\n')||global.SimyServiceSecurity.inventoryResearchStatus(s,security)]),[58,118]);grid(notices.map(n=>[n.name+' / '+n.title,'公表 '+n.published+'\n'+n.summary+'\n対象：'+(n.scope||'公表内容をご参照ください。')+'\n'+(n.resolution||''),n.url]),true);}
    paragraph(security?.research?.status==='completed'?'診断時に公式情報を検索しました。':security?.research?.status==='partial'?'診断時の検索・一次情報確認は一部のみ完了しました。':'診断時の検索は未実施または取得できませんでした。事前確認の公表事例を含みます。',8);
    const mainFlow=flow.filter(g=>!g.kinds.every(k=>k==='link')||/予約|問診|診療|決済|ログイン/.test(g.categories.join(' '))||g.sharing.length);
    if(mainFlow.length){page('EXTERNAL CONNECTIONS');heading('04 / EXTERNAL CONNECTION MAP','ホームページが利用する外部サービス','接続先の記載と、患者情報の送信は別です。外部サービス内部の保存先・保存期間は、この診断では分かりません。');card('医院のホームページ → 閲覧者のブラウザー → 外部サービス','公開ページの表示・外部プログラムの読込・予約などの接続関係を整理しています。');
      const grouped=new Map();for(const g of mainFlow){const key=g.category;const item=grouped.get(key)||{domains:[],reason:global.SimyInformationFlow.managementCopy(g).reason};item.domains.push(g.domain);grouped.set(key,item);}grid([...grouped].map(([category,g])=>[category,[...new Set(g.domains)].join('\n')+'\n'+g.reason]),true);const summary=global.SimyInformationFlow.noProblemSummary?.(report);if(summary)paragraph(summary,10);}
    if(findings.length||sharing.length){page('RECOMMENDATIONS');heading('05 / RECOMMENDATIONS','その他おすすめの改善点','診断で見つかった問題・見直しが必要な点だけを記載しています。');for(const f of findings)card(f.title,f.summary);table('共有資料の公開範囲',['資料','確認した内容'],sharing.map(x=>[global.SimyInformationFlow.sharingName(x),global.SimyInformationFlow.sharingCopy(x).reason]),[58,118]);}
    const growth=global.SimyClinicGrowth?.model(report);
    if(growth?.available){
      page('GROWTH REPORT');heading('GROWTH / CLINIC WEBSITE',growth.headline,growth.name+' / '+growth.intro);
      if(growth.discovery){const d=growth.discovery;
        grid([['AI回答への登場 '+d.ratio,'医院名を入力しない質問で確認'],['公式サイトへの誘導',d.verified?d.verified+'件の回答から公式サイトへの到達を確認。診療情報の正確性とは別に評価。':'公式URLへの到達・診療情報の一致は未検証']]);
        table('01 / AI検索の実測結果',['患者さんの質問','医院の紹介','同じ回答に登場した医院'],d.questions.map(q=>[q.theme,q.status!=='observed'?'取得できず':q.mentioned?'紹介あり':'紹介なし',q.peers.join('、')||'—']),[65,25,86]);
        if(d.different)card('公式サイトへの誘導は、要検証','取得した回答に、公式サイトと異なるドメインのリンクがありました。公式サイトへの到達と、診療情報の一致は未確認です。\n改善の方向：公式URLの表記を揃え、回答内リンクの到達先と診療情報を照合します。');
        paragraph(d.provider+' / '+d.measuredLabel+' / 各質問'+d.repetitions+'回。医院名は入力せず。回答は条件・日時で変わります。',8);paragraph('取得記録：'+d.sourceUrl,7);if(d.captureNote)paragraph(d.captureNote,8);
      }
      if(growth.audit){const a=growth.audit;page('PATIENT JOURNEY');heading('02 / PATIENT JOURNEY','正しい案内から、予約まで。',a.summary);
       for(const item of a.findings){card(item.priority+' / '+item.title,'確認したこと：'+item.observation+'\n保護者への影響：'+item.impact+'\n改善案：'+item.change);for(const source of item.sources)paragraph(source.label+'：'+source.url,7);}
       card('すでに案内できていること',a.confirmed.join('\n'));card('成長相談ページの掲載案',a.proposal.heading+'\n'+a.proposal.body+'\n'+a.proposal.button+'\n'+a.proposal.note);paragraph('別途確認日：'+a.checkedOn+'。'+a.scope,8);
      }
      if(growth.contentAvailable){
      if(growth.discovery||growth.audit){page('GROWTH / WEBSITE');heading((growth.audit?'03':'02')+' / WEBSITE','診断時に取得した本文のAI分析',growth.contentSummary);}else{paragraph('診断時に取得した本文のAI分析',12,C.ink);paragraph(growth.contentSummary,9);}
      table('本文から確認した数値',['項目','確認結果'],growth.metrics,[110,66]);
      for(const [i,item] of growth.priorities.entries())card(String(i+1).padStart(2,'0')+' / '+item.title,'現状：'+item.observation+'\n改善案：'+item.change);
      card('トップページの掲載案',growth.proposal.heading+'\n'+growth.proposal.description+'\n'+growth.proposal.button);
      table('初めての患者さんに必要な案内',['項目','公開本文で確認できたこと'],growth.questions.map(q=>[q.label,q.status+'\n'+q.answer]),[42,134]);
      paragraph(growth.scope+' 掲載案は医院で内容をご確認ください。',8);}
    }

    page('CONTENT & DISCOVERY');
heading('INTERVIEW TO CONTENT','セキュリティから、集患まで。SIMYに。','Googleマップでも、AI検索でも。医院を探す患者さんに、見つけてもらうために。');
paragraph('取材で伺った先生の説明や、患者さんからよく寄せられる質問を、AIが記事案に整えます。',10);
illustration('content');
paragraph('取材・素材の整理 / 個人を特定できる情報の除去 / AIが記事案を作成 / 先生が確認して公開',9,C.ink);
paragraph('氏名・連絡先・受診歴などは記事に含めず、匿名化後も個人を推測できる記述がないか確認します。公開頻度は医院と相談し、継続して内容を充実させます。',9);
contact();
page('MIGRATION');heading('DIAGNOSIS TO ACTION','今のホームページを、SIMYへ。','URLも、見慣れたデザインも。医院には情報の受け取りと内容の確認をお願いします。準備から公開までSIMYが進めます。');
    card('01 / 今の管理会社から、移管情報を受け取ります。','HTML・画像・管理情報を受け取ります。ドメイン登録会社の移管が必要なら「AuthCode（オースコード）」も依頼します。必要な依頼内容はSIMYがご案内します。');
    card('02 / 今の見た目を、最新の技術で作り直します。','既存データを引き継ぐか、同じ見た目・内容を最新技術で無料で再制作します。必要な権利・許諾と対象範囲を確認して着手し、公開前に先生に画面をご確認いただきます。');
    card('03 / 同じURLで公開し、ChatGPTへ接続します。','ドメイン設定・公開先を切り替えます。予約・フォーム・メールへの影響を確認し、医院のChatGPTを更新環境へ接続します。プレビューを確認して公開できます。');
    paragraph('無料再制作はHP管理をご契約いただく場合に、権利・許諾を確認できた事前合意の範囲で対応します。外部サービス内部・追加機能は別途確認。月額保守料、ドメイン移管実費、AIサービス契約・利用料等は別途です。',8);contact();
    page('RIGHTS & CONTACT');heading('BEFORE THE MIGRATION','権利の確認から、\nSIMYがお手伝いします。');
    card('医院が権利をお持ちの場合','契約上、利用できる範囲を確認して引き継ぎます。');card('制作会社などが権利を持つ場合','データ引き渡し・移設・作り替え・公開・今後の更新について、権利者の許可を得て進めます。確認事項や依頼文はSIMYがご案内します。');card('許可を得られない素材がある場合','そのデザイン・文章・写真などは使用せず、新しく制作・差し替えます。');
    paragraph('同じ見た目・内容での再制作は必要な権利・許諾を確認できた範囲で対応します。写真素材・フォント・テンプレートの利用条件も確認し、許諾の対象と範囲を書面やメールで残します。',8);
    contact();
    page('CYBER INSURANCE');
heading('MEDICAL INFORMATION / CYBER INSURANCE',"サイバー保険を検討する際に","サイバー保険は、情報漏えいやサイバー攻撃による費用負担に備える選択肢です。");
paragraph("情報漏えいやサイバー攻撃による、原因調査・復旧・損害賠償などの費用負担に備える商品があります。休業による利益損失などは、商品・プラン・特約によって異なります。",10);
table('ご検討いただける補償の例',['備えたいこと','費用・損害の例'],[["原因・被害範囲の調査", "事故の原因や影響を調べる費用。"], ["システム・データの復旧", "事故で損傷したシステムやデータを復旧する費用。"], ["損害賠償・法律相談", "法律上の損害賠償責任を負った場合の賠償金や、対応に必要な費用。"], ["休業中の損失への備え", "システム停止による利益損失や営業継続費用。商品・プラン・特約等の確認が必要です。"]],[44,132]);
paragraph("補償の範囲、支払限度額、自己負担額、保険金をお支払いできない場合は契約によって異なります。ご検討の際は、取扱代理店の説明と重要事項説明書・約款をご確認ください。",9);
paragraph("この診断は、対象の公開Webサイトを外部から確認した結果です。院内ネットワーク、電子カルテ、職員端末などの対策状況や、保険への加入可否・保険料を判定するものではありません。",9);
paragraph('SIMYの月額保守料には保険料を含みません。',8);
ensure(30);box(left,y,width,26);write("見積りの進め方をSIMYに相談する",left+6,y+10,11,width-12,C.blue);write('sales@simy.one',left+6,y+19,10,width-12,C.blue);
const insuranceMail="mailto:sales@simy.one?subject=%E3%82%B5%E3%82%A4%E3%83%90%E3%83%BC%E4%BF%9D%E9%99%BA%E3%81%AE%E8%A6%8B%E7%A9%8D%E3%82%8A%E3%81%AB%E9%96%A2%E3%81%99%E3%82%8B%E7%9B%B8%E8%AB%87&body=%E3%82%B5%E3%82%A4%E3%83%90%E3%83%BC%E4%BF%9D%E9%99%BA%E3%81%AE%E8%A6%8B%E7%A9%8D%E3%82%8A%E3%81%AE%E9%80%B2%E3%82%81%E6%96%B9%E3%82%92%E7%9B%B8%E8%AB%87%E3%81%97%E3%81%9F%E3%81%84%E3%81%A7%E3%81%99%E3%80%82%0A%0A%E3%82%AF%E3%83%AA%E3%83%8B%E3%83%83%E3%82%AF%E5%90%8D%EF%BC%9A%0A%E3%81%94%E6%8B%85%E5%BD%93%E8%80%85%E5%90%8D%EF%BC%9A%0A%E3%81%94%E9%80%A3%E7%B5%A1%E5%85%88%EF%BC%9A%0A%0A%E2%80%BB%E6%82%A3%E8%80%85%E3%81%95%E3%81%BE%E3%81%AE%E6%83%85%E5%A0%B1%E3%80%81%E8%A9%B3%E3%81%97%E3%81%84%E4%BA%8B%E6%95%85%E6%83%85%E5%A0%B1%E3%80%81%E8%A8%98%E5%85%A5%E6%B8%88%E3%81%BF%E3%81%AE%E5%91%8A%E7%9F%A5%E6%9B%B8%E3%81%AF%E6%B7%BB%E4%BB%98%E3%81%97%E3%81%AA%E3%81%84%E3%81%A7%E3%81%8F%E3%81%A0%E3%81%95%E3%81%84%E3%80%82";doc.link(left,y,width,26,{url:insuranceMail});y+=34;
paragraph("メール作成画面が開きます。診断結果・告知書は自動送信されません。",8);
paragraph("見積りには、売上や保険会社ごとの質問へのご回答が別途必要です。",8);
paragraph("初回のご相談には、患者さまの情報、詳しい事故情報、記入済みの告知書を添付しないでください。",8);
paragraph('補償内容の参考：保険会社の公式資料（2026年11月5日確認）。特定の商品・取扱先を推奨するものではありません。',7);
write("東京海上日動の公式資料",left,y,7,width,C.blue);doc.link(left,y-4,80,6,{url:"https://www.tokiomarine-nichido.co.jp/hojin/baiseki/cyber/"});y+=8;
write("三井住友海上の公式資料",left,y,7,width,C.blue);doc.link(left,y-4,80,6,{url:"https://www.ms-ins.com/business/indemnity/pd-protector/"});y+=8;
write("損保ジャパンの公式資料",left,y,7,width,C.blue);doc.link(left,y-4,80,6,{url:"https://www.sompo-japan.co.jp/hinsurance/cyberrisk/"});y+=8;
const count=doc.getNumberOfPages();for(let i=1;i<=count;i++){doc.setPage(i);doc.setDrawColor(...C.line);doc.line(left,280,193,280);write('SIMY HP管理 · 公開情報に基づく確認レポート',left,285,6,115,C.muted);write('sales@simy.one',left,290,7,110,C.blue);doc.link(left,286,75,6,{url:mail});write(i+' / '+count,178,286,7,15,C.muted);}
    return doc;
  }
  async function download(input) { const assets = await prepare(); const doc = create(model(input), assets.font, global.jspdf.jsPDF, assets.logo, assets.bold, assets.illustrations); doc.save('SIMY_ホームページ診断_' + new Date(input.report.checkedAt).toISOString().slice(0, 10) + '.pdf'); }
  global.SimyReportPdf = {download, create, model};
})(typeof window === 'undefined' ? globalThis : window);
