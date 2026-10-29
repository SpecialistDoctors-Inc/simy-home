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
      return btoa(binary);
    })().catch(error => { dependencies = null; throw error; });
    return dependencies;
  }
  const text = value => String(value ?? '').replace(/\r/g, '');
  function model({report, registration, root}) {
    const versions = [...root.querySelectorAll('.evaluation-section tbody tr')].map(row => [...row.children].map(cell => {
      // Preserve line boundaries and full issue/incident details, including collapsed evidence.
      const clone = cell.cloneNode(true);
      clone.querySelectorAll('small,summary,p,li').forEach(n => n.prepend('\n'));
      return clone.textContent.trim();
    }));
    const connections = new Map();
    for (const x of report.integrations || []) { const key = x.kind + '|' + x.destination; const old = connections.get(key); if (old) old.pages.add(x.page); else connections.set(key, {...x, pages: new Set([x.page])}); }
    return {report, registration, versions, connections: [...connections.values()]};
  }
  function create({report, registration, versions, connections}, font, JsPDF) {
    const doc = new JsPDF({unit: 'mm', format: 'a4', orientation: 'landscape', compress: true, putOnlyUsedFonts: true});
    doc.addFileToVFS('ReportJP.ttf', font); doc.addFont('ReportJP.ttf', 'ReportJP', 'normal'); doc.setFont('ReportJP', 'normal');
    doc.setProperties({title: 'SIMY HP管理｜ホームページ診断結果', author: 'SIMY', subject: registration.clinicName});
    let y = 27;
    function paragraph(value, size = 10) {
      doc.setFontSize(size); doc.setTextColor(30, 48, 65);
      const lines = doc.splitTextToSize(text(value), 265);
      for (const line of lines) { if (y > 187) { doc.addPage(); y = 27; } doc.text(line, 16, y); y += size * 0.48; }
      y += 3;
    }
    function table(title, head, body, widths) {
      if (!body.length) return;
      if (y > 165) { doc.addPage(); y = 27; }
      paragraph(title, 13);
      const columnStyles = {}; widths?.forEach((width, i) => columnStyles[i] = {cellWidth: width});
      doc.autoTable({startY: y, margin: {left: 16, right: 16, top: 26, bottom: 20}, head: [head], body,
        styles: {font: 'ReportJP', fontStyle: 'normal', fontSize: 9, cellPadding: 3, overflow: 'linebreak', lineColor: [215, 224, 235], lineWidth: 0.15},
        headStyles: {fillColor: [19, 43, 76], textColor: 255, fontStyle: 'normal'},
        alternateRowStyles: {fillColor: [242, 246, 251]}, columnStyles, rowPageBreak: 'avoid',
        didParseCell(data) { if (head.length === 4 && data.section === 'body' && /旧バージョン/.test(text(data.row.raw[1])) && [1, 3].includes(data.column.index)) data.cell.styles.textColor = [174, 41, 34]; }
      });
      y = doc.lastAutoTable.finalY + 9;
    }
    paragraph(registration.clinicName + '　診断結果一覧', 17);
    if(registration.contactName) paragraph('お名前：' + registration.contactName + ' 様');
    paragraph('対象：' + report.url + '\n確認日時：' + new Date(report.checkedAt).toLocaleString('ja-JP') + '\n診断ID：' + (report.diagnosisId || '未取得'), 9);
    if(report.completion==='partial') paragraph('一部完了：'+report.completionReason, 11);
    paragraph('公開情報による確認です。旧版だけで脆弱性があるとは限りません。侵入・情報漏えいの有無は判定できません。', 9);
    table('01 / 使用部品の脆弱性・セキュリティリスク', ['言語・部品', '現在のバージョン', '最新安定版', '判定'], versions, [36, 53, 53, 123]);

    const action = value => text(value).replace(/SIMY|制作会社(?:・管理者)?/g, '管理担当者');
    table('02 / ドメイン・サーバー・制作元の詳細', ['項目','提供元','判定'], (report.providers?.facts||[]).filter(f=>f.role!=='現在の保守・契約担当'&&!/未特定|未確認|不明/.test(f.name+' '+f.status)).map(f=>[f.role,f.name,f.status]), [65,150,50]);
    table('提供元が公表した事故・障害', ['公表日','公表内容','対象・状況'], (global.SimyServiceSecurity?.providerNotices(report)||report.providers?.notices||[]).map(n=>[n.published,(n.name?n.name+'：':'')+n.title+'\n'+n.summary,n.scope+'\n'+n.resolution]), [35,140,90]);
    const security=global.SimyServiceSecurity?.assess(report);
    table('03 / 外部サービスの事故・脆弱性情報', ['サービス・公表日', '公表された内容・対象', '公式発表'], [...new Map((security?global.SimyServiceSecurity.visibleServices(security).flatMap(service=>global.SimyServiceSecurity.findingsFor(service,security)):[]).map(n=>[n.id,n])).values()].map(n=>[n.name+'\n公表 '+n.published+' / 確認 '+n.checkedAt,n.title+'\n'+n.summary+'\n'+n.scope,n.url]), [55,110,100]);
    paragraph(security?.research?.status==='completed'?'診断時に公式情報を検索しました。':security?.research?.status==='partial'?'診断時の検索・一次情報確認は一部のみ完了しました。':'診断時の検索は未実施または取得できませんでした。事前確認の公表事例を含みます。',9);
    paragraph('外部サービス：'+(security?.notices.length?'上記の公表事例に関連する記載あり。':'今回の照合で関連事例を特定できず。事故なしの判定ではありません。')+' 選定した公式発表との照合で、全件収集・リアルタイム更新ではありません。情報確認 '+(security?.checkedAt||'未確認'),9);
    table('その他おすすめの改善点', ['項目', '確認結果・医院への影響'], (report.findings || []).filter(f => f.state === 'review').map(f => [f.title, f.summary]), [65, 200]);
    const flow=global.SimyInformationFlow?.model(report)||[];
    table('04 / ホームページと外部サービスのつながり', ['接続の起点', '外部サービス', '管理の重要度'], flow.filter(g=>!g.kinds.every(k=>k==='link')||/予約|問診|診療|決済|ログイン/.test(g.categories.join(' '))||g.sharing.length).map(g=>['閲覧者のブラウザー（医院HPを表示）',g.category+' / '+g.domain,global.SimyInformationFlow.managementCopy(g).label+'\n'+global.SimyInformationFlow.managementCopy(g).reason]), [65,90,110]);
    paragraph('矢印・経路は接続関係です。患者情報の送信や提供先内部の保存を確認したものではありません。',9);
    table('Google Drive等の共有範囲', ['資料', '本文・公開範囲の確認'], (report.sharing?.items||[]).filter(x=>global.SimyInformationFlow?.sharingHasIssue(x)).map((x,i)=>[(global.SimyInformationFlow?.sharingName(x)||x.title||'資料名を取得できませんでした')+'\n'+x.url,(global.SimyInformationFlow?.sharingCopy(x).reason||x.reason)+'\n確認日時：'+(x.checkedAt||'未実施')]), [85,180]);
    paragraph('診断の範囲・制限', 13);
    paragraph('今回確認したこと：公開ページから、古い部品や見直しが必要な設定を確認しました。', 9);
    paragraph('まだ分からないこと：侵入・情報漏えいの有無、サーバー内部、電子カルテ・予約サービスの内部は確認していません。', 9);
    const count = doc.getNumberOfPages();
    for (let i = 1; i <= count; i++) { doc.setPage(i); doc.setFont('ReportJP', 'normal'); doc.setTextColor(19, 43, 76); doc.setFontSize(10); doc.text('SIMY HP管理', 16, 14); doc.setFontSize(9); doc.text('お問い合わせ：sales@simy.one', 281, 14, {align: 'right'}); doc.link(226, 9, 55, 6, {url: 'mailto:sales@simy.one'}); doc.setDrawColor(215, 224, 235); doc.line(16, 18, 281, 18); doc.setFontSize(8); doc.text('サービス詳細：https://simy.one/hp-management.html', 16, 201); doc.link(16, 197, 90, 6, {url: 'https://simy.one/hp-management.html'}); doc.text('公開情報の診断記録・確認日時点', 158, 201); doc.text(i + ' / ' + count, 281, 201, {align: 'right'}); }
    return doc;
  }
  async function download(input) { const font = await prepare(); const doc = create(model(input), font, global.jspdf.jsPDF); doc.save('SIMY_ホームページ診断_' + new Date(input.report.checkedAt).toISOString().slice(0, 10) + '.pdf'); }
  global.SimyReportPdf = {download, create, model};
})(typeof window === 'undefined' ? globalThis : window);
