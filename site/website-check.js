'use strict';
const form = document.querySelector('#consultation');
const urlInput = document.querySelector('#url');
const draft = document.querySelector('#draft');
const clearDraft = () => { if (!draft) return; draft.hidden = true; document.querySelector('#email-link').removeAttribute('href'); };
if (form) {
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

}

const diagnosisForm = document.querySelector('#diagnosis-form');
const diagnosisInput = document.querySelector('#diagnosis-url');
const diagnosisState = document.querySelector('#diagnosis-state');
const results = document.querySelector('#diagnosis-results');
const message = document.querySelector('#diagnosis-message');
const title = document.querySelector('#diagnosis-state-title');
let busy = false;
// Set only after the production diagnosis service is publicly available.
const diagnosisEndpoint = diagnosisForm.dataset.endpoint;
const element = (tag, text, className) => {
  const node = document.createElement(tag); node.textContent = text;
  if (className) node.className = className;
  return node;
};
function simyAction(action) {
  return String(action || '').replace(/制作会社(?:・管理者)?/g, 'SIMY').replace(/管理者([へに])/g, 'SIMY$1');
}
let reportDetails;
function card(level, heading, risk, action, evidence) {
  const article = element('article', '', 'live-finding ' + level);
  article.append(element('span', level === 'urgent' ? '早めに対応' : level === 'review' ? '確認が必要' : '今回確認できたこと', 'live-label'), element('h3', heading), element('p', risk));
  if (action) article.append(element('p', '次にすること：' + simyAction(action), 'live-action'));
  if (evidence) { const details = element('details', ''); details.append(element('summary', 'SIMYに伝える根拠を見る'), element('pre', evidence)); article.append(details); }
  (reportDetails || results).append(article);
}
// Official releases checked on 2026-10-27. These are dated references, not live latest-version guarantees.
const releaseReferences = {
  "vue": {"version":"3.5.44","url":"https://www.npmjs.com/package/vue?activeTab=versions","checkedAt":"2026-10-28","dates":{"0.0.0":"2013-12-07","0.6.0":"2013-12-08","0.7.0":"2013-12-24","0.7.1":"2013-12-24","0.7.3":"2014-01-06","0.7.4":"2014-01-10","0.7.5":"2014-01-13","0.7.6":"2014-01-19","0.8.0":"2014-01-27","0.8.1":"2014-02-02","0.8.2":"2014-02-03","0.8.3":"2014-02-06","0.8.4":"2014-02-09","0.8.5":"2014-02-10","0.8.6":"2014-02-14","0.8.7":"2014-02-20","0.8.8":"2014-02-20","0.9.0":"2014-02-25","0.9.1":"2014-02-25","0.9.2":"2014-02-25","0.9.3":"2014-03-02","0.10.0":"2014-03-23","0.10.1":"2014-03-24","0.10.2":"2014-03-25","0.10.3":"2014-03-26","0.10.4":"2014-04-25","0.10.5":"2014-06-06","0.10.6":"2014-07-29","0.11.0":"2014-11-07","0.11.1":"2014-12-01","0.11.2":"2014-12-02","0.11.3":"2014-12-02","0.11.4":"2014-12-07","0.11.5":"2015-02-05","0.11.6":"2015-04-18","0.11.7":"2015-04-21","0.11.8":"2015-04-21","0.11.9":"2015-05-06","0.11.10":"2015-05-07","0.12.0":"2015-06-12","0.12.1":"2015-06-14","0.12.2":"2015-06-25","0.12.3":"2015-06-25","0.12.4":"2015-06-25","0.12.5":"2015-07-02","0.12.6":"2015-07-05","0.12.7":"2015-07-07","0.12.8":"2015-07-23","0.12.9":"2015-07-31","0.12.10":"2015-08-10","0.12.11":"2015-08-25","0.12.12":"2015-08-26","0.12.13":"2015-09-07","0.12.14":"2015-09-11","0.12.15":"2015-09-19","0.12.16":"2015-09-25","1.0.0":"2015-10-27","1.0.1":"2015-10-27","1.0.2":"2015-10-29","1.0.3":"2015-10-29","1.0.4":"2015-10-31","1.0.5":"2015-11-05","1.0.6":"2015-11-05","1.0.7":"2015-11-06","1.0.8":"2015-11-12","1.0.9":"2015-11-23","1.0.10":"2015-11-23","1.0.11":"2015-12-10","1.0.12":"2015-12-17","1.0.13":"2015-12-24","1.0.14":"2016-01-11","1.0.15":"2016-01-18","1.0.16":"2016-01-30","1.0.17":"2016-02-29","1.0.18":"2016-03-18","1.0.19":"2016-03-25","1.0.20":"2016-03-26","1.0.21":"2016-04-07","1.0.22":"2016-05-07","1.0.23":"2016-05-11","1.0.24":"2016-05-11","1.0.25":"2016-06-16","1.0.26":"2016-06-28","1.0.27":"2016-09-23","1.0.28":"2016-09-27","2.0.0":"2016-09-30","2.0.1":"2016-09-30","2.0.2":"2016-10-12","2.0.3":"2016-10-13","2.0.4":"2016-11-04","2.0.5":"2016-11-05","2.0.6":"2016-11-15","2.0.7":"2016-11-16","2.0.8":"2016-11-20","2.1.0":"2016-11-22","2.1.1":"2016-11-23","2.1.2":"2016-11-23","2.1.3":"2016-11-24","2.1.4":"2016-12-02","2.1.5":"2016-12-13","2.1.6":"2016-12-13","2.1.7":"2016-12-24","2.1.8":"2016-12-28","2.1.9":"2017-01-16","2.1.10":"2017-01-17","2.2.0":"2017-02-26","2.2.1":"2017-02-26","2.2.2":"2017-03-09","2.2.3":"2017-03-13","2.2.4":"2017-03-13","2.2.5":"2017-03-24","2.2.6":"2017-03-27","2.3.0":"2017-04-27","2.3.1":"2017-05-02","2.3.2":"2017-05-02","2.3.3":"2017-05-09","2.3.4":"2017-06-08","2.4.0":"2017-07-13","2.4.1":"2017-07-13","2.4.2":"2017-07-21","2.4.3":"2017-09-13","2.4.4":"2017-09-14","2.5.0":"2017-10-13","2.5.1":"2017-10-13","2.5.2":"2017-10-13","2.5.3":"2017-11-03","2.5.4":"2017-11-16","2.5.5":"2017-11-17","2.5.6":"2017-11-18","2.5.7":"2017-11-20","2.5.8":"2017-11-21","2.5.9":"2017-11-27","2.5.10":"2017-12-12","2.5.11":"2017-12-14","2.5.12":"2017-12-19","2.5.13":"2017-12-19","2.5.14":"2018-03-09","2.5.15":"2018-03-10","2.5.16":"2018-03-13","2.5.17":"2018-08-01","2.5.18":"2018-12-07","2.5.19":"2018-12-09","2.5.20":"2018-12-10","2.5.21":"2018-12-11","2.5.22":"2019-01-11","2.6.0":"2019-02-04","2.6.1":"2019-02-04","2.6.2":"2019-02-05","2.6.3":"2019-02-06","2.6.4":"2019-02-08","2.6.5":"2019-02-11","2.6.6":"2019-02-12","2.6.7":"2019-02-21","2.6.8":"2019-03-01","2.6.9":"2019-03-14","2.6.10":"2019-03-20","2.6.11":"2019-12-13","2.6.12":"2020-08-20","3.0.0":"2020-09-18","3.0.1":"2020-10-15","3.0.2":"2020-10-20","3.0.3":"2020-11-25","3.0.4":"2020-12-02","3.0.5":"2020-12-30","3.0.6":"2021-02-24","3.0.7":"2021-03-01","3.0.8":"2021-03-26","3.0.9":"2021-03-27","3.0.10":"2021-03-31","3.0.11":"2021-04-01","2.6.13":"2021-06-01","2.6.14":"2021-06-07","3.1.0":"2021-06-07","3.1.1":"2021-06-07","3.1.2":"2021-06-22","3.1.3":"2021-07-01","3.1.4":"2021-07-02","3.1.5":"2021-07-16","3.2.0":"2021-08-09","3.2.1":"2021-08-09","3.2.2":"2021-08-11","3.2.3":"2021-08-16","3.2.4":"2021-08-17","3.2.5":"2021-08-24","3.2.6":"2021-08-24","3.2.7":"2021-09-01","3.2.8":"2021-09-02","3.2.9":"2021-09-05","3.2.10":"2021-09-07","3.2.11":"2021-09-08","3.2.12":"2021-09-17","3.2.13":"2021-09-21","3.2.14":"2021-09-22","3.2.15":"2021-09-23","3.2.16":"2021-09-23","3.2.17":"2021-09-24","3.2.18":"2021-09-24","3.2.19":"2021-09-25","3.2.20":"2021-10-08","3.2.21":"2021-11-02","3.2.22":"2021-11-15","3.2.23":"2021-11-26","3.2.24":"2021-12-06","3.2.25":"2021-12-12","3.2.26":"2021-12-12","3.2.27":"2022-01-16","3.2.28":"2022-01-21","3.2.29":"2022-01-23","3.2.30":"2022-02-07","3.2.31":"2022-02-12","3.2.32":"2022-04-12","3.2.33":"2022-04-14","3.2.34":"2022-05-19","3.2.35":"2022-05-20","3.2.36":"2022-05-23","3.2.37":"2022-06-06","2.7.0":"2022-07-01","2.7.1":"2022-07-04","2.7.2":"2022-07-05","2.7.3":"2022-07-06","2.7.4":"2022-07-08","2.7.5":"2022-07-13","2.7.6":"2022-07-15","2.7.7":"2022-07-16","2.7.8":"2022-07-22","2.7.9":"2022-08-19","2.7.10":"2022-08-23","3.2.38":"2022-08-30","3.2.39":"2022-09-08","3.2.40":"2022-09-28","2.7.11":"2022-10-11","2.7.12":"2022-10-12","2.7.13":"2022-10-14","3.2.41":"2022-10-14","3.2.42":"2022-11-09","2.7.14":"2022-11-09","3.2.43":"2022-11-09","3.2.44":"2022-11-09","3.2.45":"2022-11-11","3.2.46":"2023-02-02","3.2.47":"2023-02-02","3.3.0":"2023-05-11","3.3.1":"2023-05-11","3.3.2":"2023-05-12","3.3.3":"2023-05-18","3.3.4":"2023-05-18","3.3.5":"2023-10-20","3.3.6":"2023-10-20","2.7.15":"2023-10-23","3.3.7":"2023-10-24","3.3.8":"2023-11-06","3.3.9":"2023-11-25","3.3.10":"2023-12-04","3.3.11":"2023-12-08","3.3.12":"2023-12-16","3.3.13":"2023-12-19","2.7.16":"2023-12-24","3.4.0":"2023-12-29","3.4.1":"2023-12-30","3.4.2":"2023-12-30","3.4.3":"2023-12-30","3.4.4":"2024-01-03","3.4.5":"2024-01-04","3.4.6":"2024-01-08","3.4.7":"2024-01-09","3.4.8":"2024-01-10","3.4.9":"2024-01-11","3.4.10":"2024-01-11","3.4.11":"2024-01-12","3.4.12":"2024-01-13","3.4.13":"2024-01-13","3.4.14":"2024-01-15","3.4.15":"2024-01-18","3.4.16":"2024-02-08","3.4.17":"2024-02-09","3.4.18":"2024-02-09","3.4.19":"2024-02-13","3.4.20":"2024-02-26","3.4.21":"2024-02-28","3.4.22":"2024-04-15","3.4.23":"2024-04-16","3.4.24":"2024-04-22","3.4.25":"2024-04-24","3.4.26":"2024-04-29","3.4.27":"2024-05-07","3.4.28":"2024-06-14","3.4.29":"2024-06-14","3.4.30":"2024-06-22","3.4.31":"2024-06-28","3.4.32":"2024-07-17","3.4.33":"2024-07-19","3.4.34":"2024-07-24","3.4.35":"2024-07-31","3.4.36":"2024-08-06","3.4.37":"2024-08-08","3.4.38":"2024-08-15","3.5.0":"2024-09-03","3.5.1":"2024-09-04","3.5.2":"2024-09-05","3.5.3":"2024-09-06","3.5.4":"2024-09-10","3.5.5":"2024-09-13","3.5.6":"2024-09-16","3.5.7":"2024-09-20","3.5.8":"2024-09-22","3.5.9":"2024-09-26","3.5.10":"2024-09-27","3.5.11":"2024-10-03","3.5.12":"2024-10-11","3.5.13":"2024-11-15","3.5.14":"2025-05-15","3.5.15":"2025-05-26","3.5.16":"2025-05-29","3.5.17":"2025-06-18","3.5.18":"2025-07-23","3.5.19":"2025-08-21","3.5.20":"2025-08-25","3.5.21":"2025-09-02","3.5.22":"2025-09-25","3.5.23":"2025-11-06","3.5.24":"2025-11-07","3.5.25":"2025-11-24","3.5.26":"2025-12-18","3.5.27":"2026-01-19","3.5.28":"2026-02-09","3.5.29":"2026-02-24","3.5.30":"2026-03-09","3.5.31":"2026-03-25","3.5.32":"2026-04-03","3.5.33":"2026-04-22","3.5.34":"2026-05-06","3.5.35":"2026-05-27","3.5.36":"2026-06-11","3.5.37":"2026-06-11","3.5.38":"2026-06-11","3.5.39":"2026-06-25","3.5.40":"2026-07-16","3.5.41":"2026-08-05","3.5.42":"2026-08-27","3.5.43":"2026-09-17","3.5.44":"2026-10-13"}},
  "handlebars": {"version":"4.7.10","url":"https://www.npmjs.com/package/handlebars?activeTab=versions","checkedAt":"2026-10-28","dates":{"1.0.6":"2012-07-23","1.0.7":"2012-09-18","1.0.8":"2013-01-19","1.0.9":"2013-02-16","1.0.10":"2013-02-27","1.0.11":"2013-05-14","1.0.12":"2013-05-31","1.1.0":"2013-11-04","1.1.1":"2013-11-04","1.1.2":"2013-11-06","1.2.0":"2013-12-24","1.2.1":"2013-12-26","1.3.0":"2014-01-02","2.0.0":"2014-09-02","3.0.0":"2015-02-10","3.0.1":"2015-03-24","3.0.2":"2015-04-20","3.0.3":"2015-04-28","4.0.0":"2015-09-01","4.0.1":"2015-09-03","4.0.2":"2015-09-04","4.0.3":"2015-09-24","4.0.4":"2015-10-29","4.0.5":"2015-11-20","4.0.6":"2016-11-13","4.0.7":"2017-04-29","4.0.8":"2017-05-02","4.0.9":"2017-05-21","4.0.10":"2017-05-21","4.0.11":"2017-10-17","4.0.12":"2018-09-04","3.0.4":"2018-12-15","3.0.5":"2018-12-15","3.0.6":"2019-01-02","4.1.0":"2019-02-07","4.0.13":"2019-02-07","4.1.1":"2019-03-16","4.1.2":"2019-04-13","4.0.14":"2019-04-13","3.0.7":"2019-06-30","4.2.0":"2019-09-03","4.2.1":"2019-09-20","4.3.0":"2019-09-24","4.3.1":"2019-09-24","4.3.2":"2019-09-26","4.3.3":"2019-09-27","4.3.4":"2019-09-28","4.4.0":"2019-09-29","4.4.1":"2019-10-02","4.3.5":"2019-10-02","4.2.2":"2019-10-02","4.4.2":"2019-10-02","4.4.3":"2019-10-08","4.4.4":"2019-10-20","4.4.5":"2019-10-20","4.5.0":"2019-10-28","4.5.1":"2019-10-29","4.5.2":"2019-11-13","4.5.3":"2019-11-18","4.6.0":"2020-01-08","4.7.0":"2020-01-10","4.7.1":"2020-01-12","4.7.2":"2020-01-13","4.7.3":"2020-02-05","3.0.8":"2020-02-23","4.7.4":"2020-04-01","4.7.5":"2020-04-02","4.7.6":"2020-04-03","4.7.7":"2021-02-15","4.7.8":"2023-08-01","4.7.9":"2026-03-26","4.7.10":"2026-10-05"}},
  "axios": {"version":"1.21.0","url":"https://www.npmjs.com/package/axios?activeTab=versions","checkedAt":"2026-10-28","dates":{"0.1.0":"2014-08-29","0.2.0":"2014-09-12","0.2.1":"2014-09-12","0.2.2":"2014-09-15","0.3.0":"2014-09-16","0.3.1":"2014-09-17","0.4.0":"2014-10-05","0.4.1":"2014-10-15","0.4.2":"2014-12-11","0.5.0":"2015-01-23","0.5.1":"2015-03-10","0.5.2":"2015-03-13","0.5.3":"2015-04-08","0.5.4":"2015-04-08","0.6.0":"2015-09-21","0.7.0":"2015-09-29","0.8.0":"2015-12-11","0.8.1":"2015-12-15","0.9.0":"2016-01-18","0.9.1":"2016-01-24","0.10.0":"2016-04-21","0.11.0":"2016-04-27","0.11.1":"2016-05-17","0.12.0":"2016-06-01","0.13.0":"2016-07-13","0.13.1":"2016-07-16","0.14.0":"2016-08-27","0.15.0":"2016-10-11","0.15.1":"2016-10-15","0.15.2":"2016-10-18","0.15.3":"2016-11-27","0.16.0":"2017-04-01","0.16.1":"2017-04-08","0.16.2":"2017-06-03","0.17.0":"2017-10-21","0.17.1":"2017-11-11","0.18.0":"2018-02-19","0.19.0":"2019-05-30","0.18.1":"2019-06-01","0.19.1":"2020-01-07","0.19.2":"2020-01-22","0.20.0":"2020-08-21","0.21.0":"2020-10-23","0.21.1":"2020-12-22","0.21.2":"2021-09-04","0.21.3":"2021-09-04","0.21.4":"2021-09-06","0.22.0":"2021-10-01","0.23.0":"2021-10-12","0.24.0":"2021-10-25","0.25.0":"2022-01-18","0.26.0":"2022-02-13","0.26.1":"2022-03-09","0.27.0":"2022-04-25","0.27.1":"2022-04-26","0.27.2":"2022-04-27","1.0.0":"2022-10-04","1.1.0":"2022-10-06","1.1.1":"2022-10-07","1.1.2":"2022-10-07","1.1.3":"2022-10-15","1.2.0":"2022-11-22","1.2.1":"2022-12-05","1.2.2":"2022-12-29","1.2.3":"2023-01-17","1.2.4":"2023-01-24","1.2.5":"2023-01-26","1.2.6":"2023-01-28","1.3.0":"2023-01-31","1.3.1":"2023-02-01","1.3.2":"2023-02-03","1.3.3":"2023-02-13","1.3.4":"2023-02-22","1.3.5":"2023-04-05","1.3.6":"2023-04-19","1.4.0":"2023-04-27","1.5.0":"2023-08-26","1.5.1":"2023-09-26","1.6.0":"2023-10-26","1.6.1":"2023-11-08","1.6.2":"2023-11-14","1.6.3":"2023-12-26","1.6.4":"2024-01-03","1.6.5":"2024-01-05","1.6.6":"2024-01-24","1.6.7":"2024-01-25","0.28.0":"2024-02-12","1.6.8":"2024-03-15","0.28.1":"2024-03-28","1.7.0":"2024-05-19","1.7.1":"2024-05-20","1.7.2":"2024-05-21","1.7.3":"2024-08-01","1.7.4":"2024-08-13","1.7.5":"2024-08-23","1.7.6":"2024-08-30","1.7.7":"2024-08-31","0.29.0":"2024-11-21","1.7.8":"2024-11-25","1.7.9":"2024-12-04","1.8.0":"2025-02-26","1.8.1":"2025-02-26","1.8.2":"2025-03-07","1.8.3":"2025-03-12","1.8.4":"2025-03-19","0.30.0":"2025-03-26","1.9.0":"2025-04-24","1.10.0":"2025-06-14","1.11.0":"2025-07-23","0.30.1":"2025-08-04","1.12.0":"2025-09-11","1.12.1":"2025-09-12","1.12.2":"2025-09-14","0.30.2":"2025-09-27","1.13.0":"2025-10-27","1.13.1":"2025-10-28","1.13.2":"2025-11-04","1.13.3":"2026-01-25","1.13.4":"2026-01-27","1.13.5":"2026-02-08","0.30.3":"2026-02-18","1.13.6":"2026-02-27","1.14.0":"2026-03-27","1.14.1":"2026-03-31","0.30.4":"2026-03-31","1.15.0":"2026-04-08","0.31.0":"2026-04-12","1.15.1":"2026-04-19","0.31.1":"2026-04-19","1.15.2":"2026-04-21","1.16.0":"2026-05-02","0.32.0":"2026-05-04","1.16.1":"2026-05-13","1.17.0":"2026-06-03","0.33.0":"2026-06-14","1.18.0":"2026-06-14","1.18.1":"2026-06-22","1.19.0":"2026-07-29","1.20.0":"2026-08-26","0.34.0":"2026-09-16","1.21.0":"2026-10-27"}},
  'jquery-ui': { version: '1.14.2', url: 'https://jqueryui.com/download/all/' },
  wordpress: { version: '7.1.3', url: 'https://wordpress.org/download/releases/' },
  php: { version: '8.5.12', url: 'https://www.php.net/downloads.php' },
  jquery: { version: '4.0.0', url: 'https://blog.jquery.com/2026/01/17/jquery-4-0-0/' },
  swiper: { version: '14.3.0', url: 'https://github.com/nolimits4web/swiper/releases/tag/v14.3.0' }
};
// Compare only complete numeric release versions; do not guess prerelease or partial versions.
function compareReleaseVersions(current, latest) {
  const parse=value=>typeof value==='string' && /^v?\d+\.\d+\.\d+(?:\.\d+)?$/.test(value) ? value.replace(/^v/,'').split('.').map(Number) : null;
  const a=parse(current),b=parse(latest);if(!a||!b)return null;
  for(let i=0;i<Math.max(a.length,b.length);i++){if((a[i]||0)<(b[i]||0))return -1;if((a[i]||0)>(b[i]||0))return 1;}return 0;
}
function renderEvaluationTable(report) {
  const rows = new Map();
  const add = (name, version, issues, assessment, fix) => {
    name = ({nextjs:'Next.js',next:'Next.js',rails:'Ruby on Rails',moment:'moment.js'}[name.toLowerCase()] || name);
    const key = name.toLowerCase() + ':' + (version || '');
    const previous = rows.get(key);
    rows.set(key, {name: previous?.name || ({jquery: 'jQuery', swiper: 'Swiper'}[name.toLowerCase()] || name), version, issues: [...(previous?.issues || []), ...(issues || [])], assessment: assessment || previous?.assessment || '', fix: fix || previous?.fix || ''});
  };
  for (const t of report.technologies.filter(t => t.status !== 'unknown')) {
    for (const version of t.versions?.length ? t.versions : ['']) add(t.name, version, t.versions?.length === 1 ? t.issues : report.scripts.libraries.filter(l=>l.name.toLowerCase()===t.name.toLowerCase() && l.version===version).flatMap(l=>l.issues || []), t.assessment, t.fix);
  }
  for (const l of report.scripts.libraries) add(l.name, l.version, l.issues);
  const section = element('section', '', 'evaluation-section');
  section.append(element('h3', '言語・システム・ライブラリのバージョン比較'));
  if (!rows.size) {
    section.append(element('p', '公開情報から部品の版を特定できませんでした。安全という判定ではありません。SIMYに構成と更新状況の確認をご相談ください。'));
    const missed=[...new Map((report.scripts.resources||[]).filter(r=>r.status==='failed'||r.status==='skipped').map(r=>[r.url,r])).values()];
    if(missed.length){const reasons=[...new Set(missed.map(r=>r.reason))];section.append(element('p','版を特定できなかった理由：'+reasons.join('／'),'evaluation-note'));}
    section.append(element('p','次にすること：SIMYに、使われている部品とバージョンの調査をご相談ください。'));
    results.append(section); return;
  }
  const wrap = element('div', '', 'evaluation-scroll'); wrap.tabIndex = 0; wrap.setAttribute('role','region'); wrap.setAttribute('aria-label','使用部品の評価表。画面が狭い場合は横にスクロールできます');
  const table = element('table', '', 'evaluation-table');
  table.append(element('caption', '使用部品・検出した版・公式情報・評価・対応'));
  const head = element('thead',''); const tr = element('tr','');
  for (const label of ['言語・部品','現在のバージョン','最新バージョン','必要な対応']) {const th=element('th',label);th.scope='col';tr.append(th);}head.append(tr);table.append(head);
  const body = element('tbody','');
  for (const row of rows.values()) {
    const fallback=releaseReferences[row.name.toLowerCase()];const reported=report.releaseInfo?.[row.name.toLowerCase()];
    const ref=reported ? {...fallback,...reported,dates:{...fallback?.dates,...reported.dates}} : fallback;
    const ended = /サポート終了/.test(row.assessment);
    const issue = row.issues.length > 0;
    const comparison = ref ? compareReleaseVersions(row.version,ref.version) : null;
    const outdated = comparison === -1;
    const state = ended ? 'SIMYに対応版への更新を相談' : issue ? 'SIMYに修正版への更新を相談' : !row.version ? 'SIMYに使用中の版を確認' : outdated ? 'SIMYに更新を相談' : comparison === 0 ? '更新不要・定期確認を継続' : 'SIMYに最新の公式情報と照合を依頼';
    const line = element('tr','');const name=element('th',row.name);name.scope='row';const purpose={php:'サーバーの動作基盤',jquery:'画面の動きを作る部品',swiper:'写真を切り替える部品',wordpress:'ページを管理する仕組み'}[row.name.toLowerCase()];if(purpose)name.append(element('small',purpose));const current=element('td','');current.append(element('strong',row.version || 'バージョン未確認',outdated?'version-outdated':''));if(outdated)current.append(element('small','旧バージョン','version-outdated-label'));const released=ref?.dates?.[row.version];current.append(element('small',released?'公開日 '+released.replace(/-/g,'/'):'公開日未確認'));if(!row.version&&/Ruby|Rails/.test(row.name))name.append(element('small','利用の手掛かりあり（推定）'));line.append(name,current);
    const official=element('td','');
    if(ref){const a=element('a',ref.version);a.href=ref.url;a.target='_blank';a.rel='noopener';official.append(a,element('small',(ref.checkedAt || '2026-10-27').replace(/-/g,'/')+'確認'));}
    else official.append(element('span','公式情報を別途確認'));
    const status=element('td','');status.append(element('span',state,ended||issue||outdated?'evaluation-badge urgent':'evaluation-badge'));
    if(ended||issue)status.append(element('small',ended?'開発元のサポート終了':'既知の問題に関係する版'));else if(outdated)status.append(element('small','動作確認のうえ更新。旧版だけで危険とは判定しません。'));else if(comparison===0)status.append(element('small','確認日の公式版と一致。安全性全体の保証ではありません。'));line.append(official,status);body.append(line);
  }
  table.append(body);wrap.append(table);section.append(wrap,element('p','公開日は検出した版の配布元の記録です。版や日付が不明なものは未確認と表示します。最新の版は記載日の確認情報です。旧版だけで脆弱性があるとは限りません。実際の版・修正状況はSIMYへご相談ください。','evaluation-note'));
  results.append(section);
}

function renderReport(report) {
  if (!Array.isArray(report.findings) || !Array.isArray(report.technologies) || !Array.isArray(report.scripts?.libraries)) throw Error('結果の形式を確認できませんでした。時間をおいて再度お試しください。');
  const technologies = report.technologies.filter(t => t.status === 'review');
  const libraries = report.scripts.libraries.filter(l => l.issues.length);
  const reviews = report.findings.filter(f => f.state === 'review');
  const patches = (report.scripts.comparisons || []).filter(c => ['legacy','mixed'].includes(c.patch?.state));
  title.textContent = technologies.length || libraries.length || patches.length ? '放置せず、SIMYへ確認してください。' : reviews.length ? '保護設定に、見直したい点があります。' : '今回の範囲で、状態を確認しました。';
  message.textContent = '確認日時：' + new Date(report.checkedAt).toLocaleString('ja-JP') + '。公開ページと関連するプログラムを調べた結果です。';
  title.textContent = technologies.length || libraries.length || patches.length ? '更新・修正の確認が必要です' : reviews.length ? '設定の確認が必要です' : '今回の範囲では、問題を特定できませんでした';
  renderEvaluationTable(report);
  if(report.crawl){
    const c=report.crawl;const scope=element('div','','crawl-summary');
    scope.append(element('strong','同じサイト内の '+c.checked+' ページを確認（上限 '+c.maxPages+' ページ）'));
    if(c.limited||c.pages.some(p=>p.status!=='checked'||p.truncated)||c.scriptLimitReached)scope.append(element('p','上限・接続状況などにより、一部は未確認です。'));
    const details=element('details','');details.append(element('summary','調べたページを見る'));
    for(const page of c.pages)details.append(element('p',(page.status==='checked'?'確認':'未確認')+'：'+page.url+' — '+page.reason));
    scope.append(details);results.append(scope);
  }
  const next=element('div','','report-next');
  next.append(element('strong',document.querySelector('#diagnosis-form')?.dataset.nextLabel || '院長先生が次にすること'),element('p',technologies.length || libraries.length || patches.length || reviews.length ? 'この結果をSIMYへ送り、対応が必要か確認してください。' : '今の管理体制を継続し、定期的に更新状況を確認してください。'));
  const contact=element('a','SIMYに診断結果を相談する ↗','button button-primary');
  contact.href='mailto:sales@simy.one?subject='+encodeURIComponent('ホームページの診断結果について相談')+'&body='+encodeURIComponent('診断したURL：'+report.url+'\n'+message.textContent+'\n\nこの診断結果について、必要な対応を相談したいです。\n診断結果は「結果を保存」から保存して添付できます。');
  next.append(contact);
  results.append(next);
  reportDetails=element('details','','report-technical');reportDetails.append(element('summary','SIMY向けの詳細・確認範囲を見る'));

  for (const t of technologies.filter(t => !libraries.some(l => l.name.toLowerCase() === t.name.toLowerCase()))) card('urgent', t.name === 'PHP' ? 'ホームページの土台に、古いPHPの表記があります' : t.name + 'に更新の確認が必要です', t.name === 'PHP' ? '開発元のサポートが終了した系列です。新しい問題が見つかっても、開発元から修正が提供されません。表記だけでは実際の修正状況までは分かりません。' : '既知の問題に関係する版の手掛かりがあります。実際の導入版と修正状況を確認する必要があります。', t.fix, t.evidence.join('\n') + '\n' + t.assessment);
  for (const l of libraries) card('urgent', l.name + ' ' + l.version + '：既知の問題に関係する部品です', '画面の動きに使う部品です。使い方によっては不正な処理につながるおそれがあります。侵入や漏えいが起きたと判定したものではありません。', 'SIMYに、使用中の版の確認と修正版への更新をご相談ください。', '検出方法：' + ({url:'URLの表記から推定',body:'公開ファイルの内容',hash:'ファイルの照合',sourcemap:'公開された元ソース情報'}[l.basis] || l.basis) + '\n取得元：' + l.resource + '\n' + l.issues.flatMap(i => i.ids).join('、'));
  for (const c of patches) card('urgent', '修正前のプログラムに似た特徴があります', '版の番号だけでなく、公開コードにも確認が必要な特徴があります。実際に攻撃できるかは調べていません。', 'SIMYへコードの修正適用状況を確認してください。', JSON.stringify(c, null, 2));
  const technical=reportDetails;
  reportDetails=element('section','','report-other-issues');
  reportDetails.append(element('h3','その他の確認・改善点（'+reviews.length+'件）'));
  if(!reviews.length)reportDetails.append(element('p','今回の確認範囲では、追加の改善点は特定できませんでした。'));
  for (const f of reviews) card('review', f.title, f.summary, f.fix, f.evidence);
  results.append(reportDetails);reportDetails=technical;
  const verified = report.findings.filter(f => f.state === 'observed');
  if (verified.length) { const d=element('details','','live-finding'); d.append(element('summary','今回確認できた設定を見る（' + verified.length + '項目）')); verified.forEach(f=>{d.append(element('h3',f.title),element('p',f.evidence));}); reportDetails.append(d); }
  const scope = element('aside', '', 'live-limits');
  scope.append(element('h3', '普段どおり表示されていても、侵入されていない証明にはなりません。'), element('p', 'この診断だけでは、侵入・情報漏えいの有無は分かりません。確認するには、管理者の協力のもと、アクセス記録やサーバー内のファイル、利用者の権限などを調べる必要があります。'), element('p', '今回調べていないこと：サーバー内部・データベース・ログイン後・電子カルテ・外部予約サービス内部。'), element('p', '追加読込の確認：' + report.scripts.dynamic.reason));
  for (const f of report.findings.filter(f=>f.state==='unknown')) scope.append(element('p', f.title + '：判定できません。' + f.evidence));
  if(report.truncated) scope.append(element('p','ページの容量上限により、HTMLの一部は未確認です。'));
  const unknownTech = report.technologies.filter(t => t.status === 'unknown').map(t => t.name);
  if(unknownTech.length) scope.append(element('p','使用の有無や版を確認できなかったもの：' + unknownTech.join('、') + '。検出されないことは、安全や未使用の証明ではありません。'));
  for(const limit of report.scripts.limitations || []) scope.append(element('p',limit));
  const coverage = element('details','','live-finding'); coverage.append(element('summary','取得・解析した範囲と部品の一覧を見る'));
  for(const t of report.technologies.filter(t=>t.status!=='unknown')) coverage.append(element('p',t.name + '：' + (t.versions.join(' / ') || '版は未確認') + '。' + t.assessment));
  for(const resource of report.scripts.resources || []) coverage.append(element('p',resource.url + '：' + resource.reason));
  for(const analysis of report.scripts.analysis || []) coverage.append(element('p','プログラム解析：' + analysis.url + ' / ' + analysis.reason));
  reportDetails.append(coverage,scope);
  results.append(element('p','侵入・漏えいの有無は、この診断では分かりません。','report-boundary'),reportDetails);
  reportDetails=null;
  const save=element('button','結果を保存','button button-primary');save.type='button';save.addEventListener('click',()=>{const blob=new Blob([title.textContent+'\n'+report.url+'\n'+message.textContent+'\n'+results.textContent+'\n\n詳細な取得根拠\n'+JSON.stringify(report,null,2)],{type:'text/plain;charset=utf-8'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=(document.querySelector('#diagnosis-form')?.dataset.reportLabel || '医院ホームページ')+'診断.txt';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);});results.append(save);
}
let scanClock;
function scanProgress(stage, detail) {
  const panel=document.querySelector('#scan-progress'); if(!panel)return;
  panel.hidden=false;
  if(stage==='start'){
    clearInterval(scanClock); panel.replaceChildren();panel.className='scan-live';panel.dataset.state='running';
    const header=element('div','','scan-live-heading');const spinner=element('span','','scan-spinner');spinner.setAttribute('aria-hidden','true');
    header.append(spinner,element('strong','ホームページを診断中'),element('span','0秒','scan-elapsed'));header.lastChild.setAttribute('aria-hidden','true');
    const status=element('p','診断サービスに接続しています','scan-live-detail');status.setAttribute('role','status');
    const track=element('div','','scan-track');track.setAttribute('aria-hidden','true');track.append(element('span',''));
    const list=element('ol','','scan-steps');
    for(const [id,label] of [['page','ページ取得'],['scripts','部品の照合'],['browser','追加読込の確認'],['crawl','配下ページの確認'],['report','結果の整理']]){const li=element('li',label);li.dataset.stage=id;list.append(li);}
    panel.append(header,status,track,list);const started=Date.now();scanClock=setInterval(()=>{const elapsed=panel.querySelector('.scan-elapsed');if(elapsed)elapsed.textContent=Math.floor((Date.now()-started)/1000)+'秒';},1000);return;
  }
  const text=panel.querySelector('.scan-live-detail');if(text)text.textContent=detail;
  if(['done','error'].includes(stage)){
    clearInterval(scanClock);panel.dataset.state=stage;
    const heading=panel.querySelector('strong');if(heading)heading.textContent=stage==='done'?'診断が完了しました':'診断を完了できませんでした';
    panel.querySelectorAll('.scan-steps li').forEach(li=>{li.removeAttribute('aria-current');li.classList.remove('active');});return;
  }
  const ids=['page','scripts','browser','crawl','report'];const current=ids.indexOf(stage);
  panel.querySelectorAll('.scan-steps li').forEach((li,i)=>{li.classList.toggle('active',i===current);li.classList.toggle('processed',i<current);if(i===current)li.setAttribute('aria-current','step');else li.removeAttribute('aria-current');});
}
async function readScanResponse(response){
  if(!response.ok){const data=await response.json();throw Error(data.error||'診断結果を取得できませんでした。');}
  if(!response.headers.get('content-type')?.includes('application/x-ndjson'))return response.json();
  const reader=response.body.getReader();const decoder=new TextDecoder();let pending='';let report;
  const consume=line=>{if(!line.trim())return;const event=JSON.parse(line);if(event.type==='progress')scanProgress(event.stage,event.detail);else if(event.type==='result')report=event.report;else if(event.type==='error')throw Error(event.error);};
  try{while(true){const {done,value}=await reader.read();pending+=decoder.decode(value,{stream:!done});let at;while((at=pending.indexOf('\n'))>=0){consume(pending.slice(0,at));pending=pending.slice(at+1);}if(done){consume(pending);break;}}}
  finally{await reader.cancel().catch(()=>{});reader.releaseLock();}
  if(!report)throw Error('診断結果の受信が途中で止まりました。もう一度お試しください。');return report;
}

// Advertising identifiers do not select a page. Remove only known tracking keys;
// preserve page-selecting queries by rejecting them rather than diagnosing another page.
function normalizeDiagnosisUrl(input) {
  const value=input.trim();let url;
  try{url=new URL(/^[a-z][a-z\d+.-]*:/i.test(value)?value:'https://'+value);}catch{throw Error('ホームページのURLを入力してください。');}
  if(!['https:','http:'].includes(url.protocol)||url.username||url.password||url.port||!url.hostname.includes('.')||/\s/.test(value))throw Error('認証情報を含まない、http:// または https:// の公開URLを入力してください。');
  const tracking=/^(?:utm_.+|gclid|dclid|gbraid|wbraid|gad_source|gad_campaignid|gclsrc|fbclid|msclkid|yclid|twclid|ttclid|srsltid|mc_cid|mc_eid|campaignid|adgroupid|creative|matchtype|network|device|keyword)$/i;
  for(const key of [...url.searchParams.keys()])if(tracking.test(key))url.searchParams.delete(key);
  url.hash='';
  if(url.search)throw Error('広告用の追跡情報は自動で除けます。このURLにはページ指定などの情報もあるため、サイトのトップページURLを入力してください。');
  return url;
}

diagnosisInput.addEventListener('input', () => { diagnosisInput.setCustomValidity(''); if(!busy) diagnosisState.hidden = true; });
diagnosisForm.addEventListener('submit', async event => {
  event.preventDefault(); if(busy) return;
  let target;
  try { target=normalizeDiagnosisUrl(diagnosisInput.value); }
  catch(error) { diagnosisInput.setCustomValidity(error.message);diagnosisInput.reportValidity();return; }
  const cleaned=target.href!==diagnosisInput.value.trim();
  diagnosisInput.value=target.href;
  let notice=document.querySelector('#diagnosis-url-normalized');
  if(!notice){notice=element('p','','availability');notice.id='diagnosis-url-normalized';notice.setAttribute('role','status');diagnosisForm.querySelector('.url-entry').after(notice);}
  notice.textContent=cleaned?'診断するURL：'+target.href:'';notice.hidden=!cleaned;
  results.replaceChildren(); diagnosisState.hidden=false; document.querySelector('#diagnosis-target').textContent=(document.querySelector('#diagnosis-form').dataset.reportLabel || '医院ホームページ')+'の診断結果';
  title.textContent='公開ホームページを確認しています'; message.textContent='最大約3分かかります。ページの保護設定・使用部品・公開プログラムを確認しています。';
  scanProgress('start');
  if(urlInput) urlInput.value=target.href; clearDraft();
  if(!diagnosisEndpoint){title.textContent='診断サービスは接続準備中です';message.textContent='まだ診断は実行していません。公開設定の確認後にご利用いただけます。';return;}
  busy=true;const button=diagnosisForm.querySelector('button');const label=button.querySelector('.button-label');const originalLabel=label?.textContent;if(label)label.textContent='診断中…';button.disabled=true;diagnosisInput.disabled=true;diagnosisForm.setAttribute('aria-busy','true');
  try { const response=await fetch(diagnosisEndpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:target.href,behavior:false,stream:true}),signal:AbortSignal.timeout(185000)}); const data=await readScanResponse(response); renderReport(data); scanProgress('done','下に結果を表示しました。'); diagnosisState.focus({preventScroll:true});diagnosisState.scrollIntoView({block:'start',behavior:'smooth'}); }
  catch(error){results.replaceChildren();title.textContent='診断を完了できませんでした';message.textContent=error.name==='TimeoutError'?'時間内に応答がありませんでした。少し待って再度お試しください。':error.message==='Failed to fetch'?'診断サービスに接続できませんでした。少し待って再度お試しください。':error.message;}
  finally{busy=false;button.disabled=false;diagnosisInput.disabled=false;diagnosisForm.removeAttribute('aria-busy');if(label)label.textContent=originalLabel;if(title.textContent==='診断を完了できませんでした')scanProgress('error',message.textContent);}
});
document.querySelector('.edit-url').addEventListener('click',()=>{if(!busy){diagnosisState.hidden=true;diagnosisInput.focus();}});
