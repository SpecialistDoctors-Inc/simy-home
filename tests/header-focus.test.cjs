'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const runtime = require('./helpers/header-runtime.cjs');
const source = fs.readFileSync(path.join(__dirname, '../site/site-header.js'), 'utf8');

test('desktop to mobile moves keyboard focus out of the menu before closing it', () => {
  const ui = runtime(source); ui.link.focus(); ui.change(true);
  assert.equal(ui.menu.open, false); assert.equal(ui.document.activeElement, ui.toggle);
});
test('mobile to desktop replaces focus on the hidden menu toggle with primary navigation', () => {
  const ui = runtime(source, true); ui.toggle.focus(); ui.change(false);
  assert.equal(ui.menu.open, true); assert.equal(ui.document.activeElement, ui.first);
});
test('resize never steals focus from the page or the persistent language control', () => {
  for (const name of ['body', 'language']) {
    const ui = runtime(source); ui[name].focus(); ui.change(true); ui.change(false);
    assert.equal(ui.document.activeElement, ui[name]);
  }
});
test('missed media-query notification still executes focus recovery through header resize', () => {
  const ui = runtime(source); ui.link.focus(); ui.media.matches = true; ui.header.clientWidth = 390; ui.resize();
  assert.equal(ui.menu.open, false); assert.equal(ui.document.activeElement, ui.toggle);
  assert.equal(ui.toggle.focuses, 1);
});
test('late/repeated notifications do not duplicate recovery or close user-reopened menu', () => {
  const ui = runtime(source); ui.link.focus(); ui.media.matches = true; ui.header.clientWidth = 390; ui.resize();
  ui.menu.open = true; ui.media.listeners.change(); ui.resize();
  assert.equal(ui.toggle.focuses, 1); assert.equal(ui.menu.open, true);
  ui.change(false); assert.equal(ui.document.activeElement, ui.first);
});

test('CSS zoom uses actual header width when viewport media query remains desktop', () => {
  const ui = runtime(source); ui.link.focus(); ui.header.clientWidth = 720; ui.resize();
  assert.equal(ui.media.matches, false); assert.equal(ui.menu.open, false);
  assert.equal(ui.document.activeElement, ui.toggle);
  ui.header.clientWidth = 1440; ui.resize();
  assert.equal(ui.menu.open, true); assert.equal(ui.document.activeElement, ui.first);
});

test('CSS layout signal stays authoritative under zoom-out and fractional widths', () => {
  const ui = runtime(source, true); ui.toggle.focus(); ui.header.clientWidth = 1000; ui.resize();
  assert.equal(ui.media.matches, true); assert.equal(ui.menu.open, true);
  assert.equal(ui.document.activeElement, ui.first);
  ui.header.clientWidth = 960.5; ui.resize(); assert.equal(ui.menu.open, true);
  ui.header.clientWidth = 960; ui.resize(); assert.equal(ui.menu.open, false);
  assert.equal(ui.document.activeElement, ui.toggle);
});
