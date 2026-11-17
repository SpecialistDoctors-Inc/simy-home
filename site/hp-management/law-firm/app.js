const examples = {
  notice: {
    request: '年末年始は12月29日から1月4日まで休業します。新規相談の受付は1月5日から、と載せてください。',
    category: 'NEWS / お知らせ',
    title: '年末年始の休業のお知らせ',
    body: '当事務所は、12月29日から1月4日まで休業いたします。新規のご相談は、1月5日より受付を再開いたします。ご不便をおかけしますが、何卒よろしくお願い申し上げます。'
  },
  profile: {
    request: '新しい弁護士の入所をお知らせしたいです。本人が確認した経歴と写真を、弁護士紹介ページに載せる案を用意してください。',
    category: 'PEOPLE / 弁護士紹介',
    title: '新たな弁護士が加わりました',
    body: '新たな弁護士が当事務所に加わりました。弁護士紹介ページで、本人が確認した経歴とメッセージをご紹介します。\n\n掲載前に、氏名・所属・登録情報と、写真の使用許諾をご確認ください。'
  },
  article: {
    request: '初めての法律相談を予約した方に、相談したいことをメモしておくとよい、とわかりやすく伝えたいです。',
    category: 'Q&A / 初めてのご相談',
    title: '初めてのご相談前に、準備しておくこと',
    body: '相談したいことや、これまでの出来事を簡単にメモしておくと、限られた時間で状況を伝えやすくなります。\n\nお持ちいただく資料は相談内容によって異なるため、ご予約時に事務所へご確認ください。'
  }
};
const titleInput = document.getElementById('draft-title');
const bodyInput = document.getElementById('draft-body');
const previewTitle = document.getElementById('preview-title');
const previewBody = document.getElementById('preview-body');
const approval = document.getElementById('approval-check');
const publishButton = document.getElementById('publish-preview-button');
const controls = document.getElementById('review-controls');
const feedback = document.getElementById('preview-feedback');
const preview = document.querySelector('.studio-preview');
const step = document.getElementById('preview-step');
const draftLabel = document.getElementById('draft-label');
const error = document.getElementById('draft-error');

function resetReview() {
  approval.checked = false;
  publishButton.disabled = true;
  controls.hidden = true;
  preview.dataset.stage = 'editing';
  step.textContent = 'STEP 1 / 原稿を編集';
  draftLabel.textContent = '確認前';
  feedback.textContent = '原稿を編集して「原稿を確認する」へ。';
  error.hidden = true;
}

function syncDraft() {
  previewTitle.textContent = titleInput.value;
  previewBody.textContent = bodyInput.value;
  resetReview();
}

document.querySelectorAll('[data-example]').forEach(button => {
  button.addEventListener('click', () => {
    const example = examples[button.dataset.example];
    document.querySelectorAll('[data-example]').forEach(item => {
      item.setAttribute('aria-pressed', String(item === button));
    });
    document.getElementById('request-text').textContent = example.request;
    document.getElementById('preview-category').textContent = example.category;
    titleInput.value = example.title;
    bodyInput.value = example.body;
    syncDraft();
  });
});

titleInput.addEventListener('input', syncDraft);
bodyInput.addEventListener('input', syncDraft);

document.getElementById('review-button').addEventListener('click', () => {
  if (!titleInput.value.trim() || !bodyInput.value.trim()) {
    error.hidden = false;
    (!titleInput.value.trim() ? titleInput : bodyInput).focus();
    return;
  }
  error.hidden = true;
  controls.hidden = false;
  preview.dataset.stage = 'review';
  step.textContent = 'STEP 2 / 掲載内容を確認';
  draftLabel.textContent = '確認用の原稿';
  feedback.textContent = 'タイトル・本文・日程・表現を確認して、チェックを入れてください。';
  approval.focus();
});

approval.addEventListener('change', () => {
  publishButton.disabled = !approval.checked;
});

publishButton.addEventListener('click', () => {
  if (!approval.checked) return;
  controls.hidden = true;
  preview.dataset.stage = 'published';
  step.textContent = 'STEP 3 / 公開イメージ';
  draftLabel.textContent = '表示イメージ';
  feedback.textContent = '確認した原稿の表示イメージです。実際のサイトには公開されていません。';
  feedback.tabIndex = -1;
  feedback.focus();
});
