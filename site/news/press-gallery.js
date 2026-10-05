(() => {
  'use strict';
  const figures = [...document.querySelectorAll('#report figure')];
  if (!figures.length || typeof HTMLDialogElement === 'undefined') return;
  const en = document.documentElement.lang === 'en';
  const dialog = document.createElement('dialog');
  dialog.className = 'slide-viewer';
  dialog.setAttribute('aria-label', en ? 'Report slide viewer' : '成果報告スライドの拡大表示');
  dialog.innerHTML = `<div class="viewer-toolbar"><p class="viewer-count" aria-live="polite"></p><button class="viewer-close" type="button" aria-label="${en ? 'Close' : '閉じる'}">×</button></div><div class="viewer-stage"><button class="viewer-prev" type="button" aria-label="${en ? 'Previous slide' : '前のスライド'}"><span aria-hidden="true">❮</span></button><img class="viewer-image" alt=""><button class="viewer-next" type="button" aria-label="${en ? 'Next slide' : '次のスライド'}"><span aria-hidden="true">❯</span></button></div><p class="viewer-caption"></p>`;
  document.body.append(dialog);
  const image = dialog.querySelector('img');
  const count = dialog.querySelector('.viewer-count');
  const caption = dialog.querySelector('.viewer-caption');
  let index = 0;
  let opener;
  function show(next) {
    index = (next + figures.length) % figures.length;
    const source = figures[index].querySelector('img');
    image.src = source.getAttribute('src');
    image.alt = source.alt;
    count.textContent = `${index + 1} / ${figures.length}`;
    caption.textContent = figures[index].querySelector('h3').textContent;
  }
  figures.forEach((figure, i) => {
    figure.querySelectorAll('a[href$=".webp"]').forEach(link => {
      link.removeAttribute('target');
      if (!link.hasAttribute('aria-hidden')) link.setAttribute('aria-label', en ? `Enlarge slide ${i + 1}` : `スライド${i + 1}を拡大`);
      link.addEventListener('click', event => {
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        opener = figure.querySelector('figcaption a');
        show(i);
        dialog.showModal();
        document.body.classList.add('viewer-open');
        dialog.querySelector('.viewer-close').focus();
      });
    });
  });
  dialog.querySelector('.viewer-prev').addEventListener('click', () => show(index - 1));
  dialog.querySelector('.viewer-next').addEventListener('click', () => show(index + 1));
  dialog.querySelector('.viewer-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault();
      show(index + (event.key === 'ArrowLeft' ? -1 : 1));
    }
  });
  dialog.addEventListener('close', () => {
    document.body.classList.remove('viewer-open');
    opener?.focus({ preventScroll: true });
  });
})();
