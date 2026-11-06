/* These controls switch static examples. No microphone, recording or AI request. */
(() => {
  document.querySelectorAll('[data-demo]').forEach((demo) => {
    const panels = [...demo.querySelectorAll('[data-panel]')];
    const buttons = [...demo.querySelectorAll('[data-step]')];
    const select = (index) => {
      panels.forEach((panel, i) => { panel.hidden = i !== index; });
      buttons.forEach((button, i) => button.setAttribute('aria-pressed', String(i === index)));
    };
    buttons.forEach((button, index) => {
      const panelId = `fp-${demo.dataset.demo}-${index}`;
      panels[index].id = panelId;
      button.setAttribute('aria-controls', panelId);
      button.addEventListener('click', () => select(index));
    });
    select(0);
    demo.classList.add('is-enhanced');
    demo.querySelector('[data-controls]').hidden = false;
  });
})();
