'use strict';
const form = document.querySelector('#consultation');
const urlInput = document.querySelector('#url');
const draft = document.querySelector('#draft');
const clearDraft = () => { draft.hidden = true; document.querySelector('#email-link').removeAttribute('href'); };
form.addEventListener('input', clearDraft);
urlInput.addEventListener('input', () => urlInput.setCustomValidity(''));
document.querySelectorAll('[data-plan]').forEach(link => link.addEventListener('click', () => {
  form.elements.plan.value = link.dataset.plan;
  clearDraft();
}));
form.addEventListener('submit', event => {
  event.preventDefault();
  const url = new URL(urlInput.value);
  if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) {
    urlInput.setCustomValidity('http:// または https:// で始まる、認証情報を含まないURLを入力してください。');
    urlInput.reportValidity();
    return;
  }
  const message = `SIMY ホームページ保守・セキュリティ管理の相談\n\n対象URL：${url.href}\n希望プラン：${form.elements.plan.value}\n気になっていること：${form.elements.concern.value.trim() || '相談しながら整理したい'}\n\n提供範囲・料金・開始時期について相談を希望します。`;
  document.querySelector('#draft-body').textContent = message;
  document.querySelector('#email-link').href = `mailto:sales@simy.one?subject=${encodeURIComponent('クリニックのホームページ保守についての相談')}&body=${encodeURIComponent(message)}`;
  draft.hidden = false;
  draft.scrollIntoView({block:'nearest'});
});

const diagnosisForm = document.querySelector('#diagnosis-form');
const diagnosisInput = document.querySelector('#diagnosis-url');
const diagnosisState = document.querySelector('#diagnosis-state');
diagnosisInput.addEventListener('input', () => {
  diagnosisInput.setCustomValidity('');
  diagnosisState.hidden = true;
  document.querySelector('#diagnosis-target').textContent = '';
});
diagnosisForm.addEventListener('submit', event => {
  event.preventDefault();
  let target;
  try {
    const value = diagnosisInput.value.trim();
    const candidate = /^[a-z][a-z\d+.-]*:/i.test(value) ? value : `https://${value}`;
    target = new URL(candidate);
    if (!['https:', 'http:'].includes(target.protocol) || target.username || target.password || !target.hostname.includes('.') || /\s/.test(value)) throw new Error('invalid');
  } catch {
    diagnosisInput.setCustomValidity('医院の公開URLを入力してください。例：https://example-clinic.jp');
    diagnosisInput.reportValidity();
    return;
  }
  document.querySelector('#diagnosis-target').textContent = `入力したURL：${target.href}`;
  diagnosisState.hidden = false;
  // Preserve the URL for an optional care enquiry without claiming a scan took place.
  urlInput.value = target.href;
  urlInput.setCustomValidity('');
  clearDraft();
  diagnosisState.focus({preventScroll:true});
  diagnosisState.scrollIntoView({block:'center'});
});
document.querySelector('.edit-url').addEventListener('click', () => {
  diagnosisState.hidden = true;
  diagnosisInput.focus();
});
