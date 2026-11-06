(function (global) {
  'use strict';
  const questions = [
    ['mfa', '重要なシステムで多要素認証を利用していますか。'],
    ['backup', 'データのバックアップと復元方法を確認していますか。'],
    ['training', '職員に情報セキュリティの注意点を伝えていますか。'],
    ['response', '事故時の連絡先や初動対応を決めていますか。']
  ];
  const needsQuestions = [
    ['recoveryCosts', '予約システムやホームページが止まったときの、調査・復旧費用に備えたいですか。'],
    ['dataIncidentCosts', '患者情報の漏えいが疑われたときの、調査・通知・相談費用に備えたいですか。'],
    ['interruptionCosts', 'サイバー事故で診療や受付が止まったときの、休業中の損失に備えたいですか。']
  ];
  const allQuestions = [...needsQuestions, ...questions];
  const labels = {yes: 'はい', no: 'いいえ', unknown: '分からない・未確認'};
  function text(value, max) {
    const result = String(value || '').trim();
    if (result.length > max || /[\r\n\u0000-\u001f\u007f]/.test(result)) throw Error('入力内容をご確認ください。');
    return result;
  }
  function normalize(value) {
    const data = {};
    data.clinicName = text(value.clinicName, 100);
    data.contactName = text(value.contactName, 80);
    data.email = text(value.email, 254);
    if (!data.clinicName || !data.contactName || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) throw Error('医院名・ご担当者名・メールアドレスをご確認ください。');
    data.url = text(value.url, 2048);
    if (data.url) {
      let url;
      try { url = new URL(data.url); } catch { throw Error('ホームページURLをご確認ください。'); }
      if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) throw Error('ホームページURLは、個人情報などを含まないトップページのURLをご入力ください。');
      data.url = url.href;
    }
    for (const [key] of allQuestions) {
      const answer = value[key] || 'unknown';
      if (!Object.hasOwn(labels, answer)) throw Error('回答をご確認ください。');
      data[key] = answer;
    }
    return data;
  }
  function buildText(value) {
    const data = normalize(value);
    return [
      'SIMY ご担当者様', '', 'サイバー保険の見積りの進め方について相談したいです。', '',
      '医院名：' + data.clinicName, 'ご担当者名：' + data.contactName, 'メールアドレス：' + data.email,
      'ホームページURL：' + (data.url || '未入力'), '', '相談のための事前整理（本人の自己申告）',
      '相談したい備え', ...needsQuestions.map(([key, label]) => label + '\n' + labels[data[key]]), '', '現在の備え',
      ...questions.map(([key, label]) => label + '\n' + labels[data[key]]), '',
      'この回答は保険会社の正式な告知書ではありません。加入可否・保険料を判定するものではありません。',
      '保険会社・代理店への情報提供が必要な場合は、提供先と内容を別途確認したうえで進めたいです。',
      '※患者情報、売上、詳しい事故情報、記入済み告知書は含めていません。'
    ].join('\r\n');
  }
  function buildMail(value) {
    return 'mailto:sales@simy.one?subject=' + encodeURIComponent('サイバー保険の見積りに関する相談') + '&body=' + encodeURIComponent(buildText(value));
  }
  let dialog, opener, form, inputPane, reviewPane, review, error, draft, downloadUrl;
  function make(tag, content, className) {
    const node = global.document.createElement(tag);
    if (content) node.textContent = content;
    if (className) node.className = className;
    return node;
  }
  function values() { return Object.fromEntries(new global.FormData(form)); }
  function clearDownload() { if (downloadUrl) { global.URL.revokeObjectURL(downloadUrl); downloadUrl = null; } }
  function createDialog() {
    const document = global.document;
    dialog = make('dialog', '', 'insurance-preparation');
    dialog.id = 'insurance-preparation';
    dialog.setAttribute('aria-labelledby', 'insurance-preparation-title');
    dialog.setAttribute('aria-describedby', 'insurance-preparation-intro');
    const content = make('div', '', 'insurance-preparation-body');
    const close = make('button', '閉じる', 'insurance-preparation-close');
    close.type = 'button';close.setAttribute('aria-label', '保険相談の準備を閉じる');
    close.addEventListener('click', () => dialog.close());
    const title = make('h2', '保険相談の準備');title.id = 'insurance-preparation-title';
    const intro = make('p', '医院の状況を整理し、SIMYへの相談メールを作成できます。入力内容はこの画面で扱い、サーバーには保存しません。');intro.id = 'insurance-preparation-intro';
    const note = make('p', '保険会社の正式な告知書ではありません。加入可否・保険料の判定は行いません。患者情報、売上、詳しい事故情報は入力しないでください。', 'insurance-preparation-note');
    inputPane = make('div');inputPane.id = 'insurance-preparation-input';
    form = make('form');form.id = 'insurance-preparation-form';
    const fields = make('div', '', 'insurance-preparation-fields');
    for (const [key, label, type, max, required] of [
      ['clinicName', '医院名', 'text', 100, true], ['contactName', 'ご担当者名', 'text', 80, true],
      ['email', 'メールアドレス', 'email', 254, true], ['url', 'ホームページURL（任意）', 'url', 2048, false]
    ]) {
      const wrap = make('label', '', 'insurance-preparation-field');
      wrap.append(make('span', label + (required ? '（必須）' : '')));
      const input = make('input');input.name = key;input.type = type;input.maxLength = max;input.required = required;
      input.autocomplete = ({clinicName: 'organization', contactName: 'name', email: 'email', url: 'url'})[key];
      if (key === 'url') input.placeholder = 'https://example.jp/';
      wrap.append(input);fields.append(wrap);
    }
    form.append(fields);
    for (const [legend, items] of [['相談したい備え（任意）', needsQuestions], ['現在の備え（任意）', questions]]) {
      const fieldset = make('fieldset');
      fieldset.append(make('legend', legend));
      fieldset.append(make('p', '分からない項目は、そのままで構いません。', 'insurance-preparation-note'));
      for (const [key, label] of items) {
        const wrap = make('label', '', 'insurance-preparation-question');
        wrap.append(make('span', label));
        const select = make('select');select.name = key;
        for (const answer of ['unknown', 'yes', 'no']) {
          const option = make('option', labels[answer]);option.value = answer;select.append(option);
        }
        wrap.append(select);fieldset.append(wrap);
      }
      form.append(fieldset);
    }
    error = make('p', '', 'insurance-preparation-error');error.setAttribute('role', 'alert');error.hidden = true;form.append(error);
    const next = make('button', '内容を確認する', 'insurance-preparation-primary');next.type = 'submit';form.append(next);
    form.addEventListener('submit', event => {
      event.preventDefault();error.hidden = true;
      if (!form.reportValidity()) return;
      try {
        const data = normalize(values());draft = data;review.replaceChildren();
        for (const [label, value] of [['医院名', data.clinicName], ['ご担当者名', data.contactName], ['メールアドレス', data.email], ['ホームページURL', data.url || '未入力'], ...allQuestions.map(([key, label]) => [label, labels[data[key]]])]) review.append(make('dt', label), make('dd', value));
        reviewPane.querySelector('[data-insurance-mail]').href = buildMail(data);
        inputPane.hidden = true;reviewPane.hidden = false;reviewPane.querySelector('h3').focus();
      } catch (reason) { error.textContent = reason.message;error.hidden = false; }
    });
    inputPane.append(form);
    reviewPane = make('div');reviewPane.id = 'insurance-preparation-review';reviewPane.hidden = true;
    const reviewTitle = make('h3', '相談内容の確認');reviewTitle.tabIndex = -1;reviewPane.append(reviewTitle);
    review = make('dl');reviewPane.append(review);
    reviewPane.append(make('p', '「メールを作成」でSIMY宛てのメール作成画面が開きます。ご自身で内容を確認して送信してください。保険会社・代理店へ自動で提供することはありません。', 'insurance-preparation-note'));
    const actions = make('div', '', 'insurance-preparation-actions');
    const back = make('button', '入力に戻る');back.type = 'button';back.addEventListener('click', () => { reviewPane.hidden = true;inputPane.hidden = false;form.querySelector('input').focus(); });
    const mail = make('a', 'メールを作成', 'insurance-preparation-primary');mail.dataset.insuranceMail = '';
    const download = make('button', '内容を保存');download.type = 'button';
    download.addEventListener('click', () => {
      if (!draft) return;
      clearDownload();downloadUrl = global.URL.createObjectURL(new global.Blob([buildText(draft)], {type: 'text/plain;charset=utf-8'}));
      const link = make('a');link.href = downloadUrl;link.download = 'サイバー保険_相談準備.txt';document.body.append(link);link.click();link.remove();
    });
    actions.append(back, mail, download);reviewPane.append(actions);
    content.append(close, title, intro, note, inputPane, reviewPane, make('p', '閉じると、この画面の入力内容は消去されます。保存したファイルや作成したメールは、お手元で管理してください。', 'insurance-preparation-note'));
    dialog.append(content);document.body.append(dialog);
    dialog.addEventListener('close', () => {
      form.reset();review.replaceChildren();reviewPane.querySelector('[data-insurance-mail]').removeAttribute('href');
      draft = null;error.textContent = '';error.hidden = true;inputPane.hidden = false;reviewPane.hidden = true;clearDownload();
      if (opener && opener.isConnected) opener.focus();opener = null;
    });
    return dialog;
  }
  function open({url} = {}) {
    if (!global.document) return;
    if (dialog?.open) return;
    opener = global.document.activeElement;
    (dialog || createDialog()).showModal();
    if (url) {
      try {
        const site = new URL(url);
        if (['http:', 'https:'].includes(site.protocol)) form.elements.namedItem('url').value = site.origin + '/';
      } catch {}
    }
    form.querySelector('input').focus();
  }
  const api = {open, normalize, buildText, buildMail, needsQuestions};
  if (typeof module === 'object' && module.exports) module.exports = api;
  global.SimyInsurancePreparation = api;
})(typeof window === 'object' ? window : globalThis);
