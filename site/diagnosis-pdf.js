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
        didParseCell(data) { if (head.length === 5 && data.section === 'body' && /旧バージョン/.test(text(data.row.raw[1])) && [1, 4].includes(data.column.index)) data.cell.styles.textColor = [174, 41, 34]; }
      });
      y = doc.lastAutoTable.finalY + 9;
    }
    paragraph(registration.clinicName + '　診断結果一覧', 17);
    if(registration.contactName) paragraph('お名前：' + registration.contactName + ' 様');
    paragraph('対象：' + report.url + '\n確認日時：' + new Date(report.checkedAt).toLocaleString('ja-JP') + '\n診断ID：' + (report.diagnosisId || '未取得'), 9);
    paragraph('公開情報による確認です。旧版だけで脆弱性があるとは限りません。侵入・情報漏えいの有無は判定できません。', 9);
    table('言語・システム・ライブラリの比較', ['言語・部品', '現在のバージョン', 'その版の公開日', '最新安定版', '必要な対応・根拠'], versions, [36, 37, 33, 36, 123]);
    if (!versions.length) paragraph('公開情報から使用部品の版は特定できませんでした。安全という判定ではありません。');
    const action = value => text(value).replace(/制作会社(?:・管理者)?/g, 'SIMY').replace(/管理者([へに])/g, 'SIMY$1');
    const security=global.SimyServiceSecurity?.assess(report);
    table('外部サービスの事故・脆弱性情報', ['サービス・公表日', '公表された内容・対象', '必要な対応・公式発表'], (security?.notices||[]).map(n=>[n.name+'\n公表 '+n.published+' / 確認 '+n.checkedAt,n.title+'\n'+n.summary+'\n'+n.scope,n.action+'\n'+n.impact+'\n'+n.url]), [55,110,100]);
    paragraph('外部サービス：'+(security?.notices.length?'上記の公表事例に関連する記載あり。':'今回の照合で関連事例を特定できず。事故なしの判定ではありません。')+' 選定した公式発表との照合で、全件収集・リアルタイム更新ではありません。情報確認 '+(security?.checkedAt||'未確認'),9);
    table('その他の確認・改善点', ['項目', '確認結果・医院への影響', '必要な対応'], (report.findings || []).filter(f => f.state === 'review').map(f => [f.title, f.summary, action(f.fix)]), [48, 105, 112]);
    table('外部サービスとの接続先', ['用途・接続先', '設置方法', '設置ページ数・公開された接続先'], connections.map(x => [x.category + '\n' + x.domain, ({link: 'リンク', embed: '埋め込み', script: 'プログラム読込', form: 'フォーム送信先'}[x.kind] || x.kind), x.pages.size + 'ページに記載\n' + x.destination]), [60, 35, 170]);
    paragraph('リンク・コードの記載と、実際の通信は別です。患者情報は入力・送信していません。外部サービス内部の保存・削除・権限は未確認です。', 9);
    table('通常表示で観測した通信', ['種類', '接続先'], (report.scripts?.browserEvidence?.connections || []).map(x => [x.type, x.destination]), [40, 225]);
    table('確認済み・外からは確認できない項目', ['項目', '判定', '確認範囲・根拠'], (report.findings || []).filter(f => f.state !== 'review').map(f => [f.title, f.state === 'observed' ? '確認できた設定' : '未確認', f.summary || '詳細な根拠は診断画面でご確認ください。']), [48, 35, 182]);
    table('調べたページ', ['対象ページ', '取得状況'], (report.crawl?.pages || []).map(p => [p.url, p.status === 'checked' ? '確認' : '未確認：' + (p.reason || p.status)]), [205, 60]);
    paragraph('診断の範囲・制限', 13);
    if (report.crawl) paragraph('確認ページ数：' + report.crawl.pages.filter(p => p.status === 'checked').length + '（上限30ページ）。サイト全体の安全性を保証するものではありません。', 9);
    for (const limit of [...(report.sourceWarnings || []), ...(report.scripts?.limitations || [])]) paragraph(limit, 9);
    paragraph('サーバー内部・データベース・ログイン後・電子カルテ・外部サービス内部は対象外です。対応の確認・ご相談：SIMY（sales@simy.one）', 9);
    const count = doc.getNumberOfPages();
    for (let i = 1; i <= count; i++) { doc.setPage(i); doc.setFont('ReportJP', 'normal'); doc.setTextColor(19, 43, 76); doc.setFontSize(10); doc.text('SIMY HP管理', 16, 14); doc.setFontSize(9); doc.text('お問い合わせ：sales@simy.one', 281, 14, {align: 'right'}); doc.link(226, 9, 55, 6, {url: 'mailto:sales@simy.one'}); doc.setDrawColor(215, 224, 235); doc.line(16, 18, 281, 18); doc.setFontSize(8); doc.text('サービス詳細：https://simy.one/hp-management.html', 16, 201); doc.link(16, 197, 90, 6, {url: 'https://simy.one/hp-management.html'}); doc.text('公開情報の診断記録・確認日時点', 158, 201); doc.text(i + ' / ' + count, 281, 201, {align: 'right'}); }
    return doc;
  }
  async function download(input) { const font = await prepare(); const doc = create(model(input), font, global.jspdf.jsPDF); doc.save('SIMY_ホームページ診断_' + new Date(input.report.checkedAt).toISOString().slice(0, 10) + '.pdf'); }
  global.SimyReportPdf = {download, create, model};
})(typeof window === 'undefined' ? globalThis : window);
