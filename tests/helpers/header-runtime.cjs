'use strict';
const vm = require('node:vm');
module.exports = function headerRuntime(source, initialMobile = false) {
  const media = { matches: initialMobile, listeners: {}, addEventListener(name, fn) { this.listeners[name] = fn; } };
  const document = { activeElement: null, documentElement: { lang: 'fixture', style: { setProperty() {} } }, listeners: {}, addEventListener(name, fn) { this.listeners[name] = fn; } };
  function control(name) { return { name, focuses: 0, focus() { if (([first, link].includes(this) && !menu.open) || (this === toggle && header.clientWidth > 960)) return; this.focuses++; document.activeElement = this; } }; }
  const body = control('body'), toggle = control('menu toggle'), first = control('first navigation summary'), link = control('menu link'), language = control('language');
  document.activeElement = body;
  const navigationDropdown = { open: false, addEventListener() {} };
  const languageDropdown = { open: false, addEventListener() {} };
  const menu = { open: false, listeners: {}, contains(element) { return [toggle, first, link, navigationDropdown].includes(element); }, querySelector() { return toggle; }, addEventListener(name, fn) { this.listeners[name] = fn; } };
  const header = { clientWidth: initialMobile ? 390 : 1440, dataset: {}, querySelector(selector) { return selector === '.sh-menu' ? menu : first; }, querySelectorAll(selector) { return selector === '.sh-dropdown' ? [navigationDropdown, languageDropdown] : []; }, addEventListener() {}, getBoundingClientRect() { return { height: 76 }; } };
  document.querySelector = () => header;
  let resize;
  vm.runInNewContext(source, { document, getComputedStyle: () => ({ display: header.clientWidth > 960 ? 'none' : 'flex' }), window: { matchMedia: () => media, addEventListener() {} },
    ResizeObserver: class { constructor(callback) { resize = callback; } observe() {} },
    MutationObserver: class { observe() {} }, setTimeout });
  return { header, media, document, menu, toggle, first, link, language, navigationDropdown, languageDropdown, body, resize: () => resize(), change: value => { media.matches = value; header.clientWidth = value ? 390 : 1440; media.listeners.change(); } };
};
