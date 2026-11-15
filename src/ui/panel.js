// The settings / controls drawer (notes 05 §4.6): a right-edge modal dialog with two tabs.
//
// Settings apply at once through G.settings.set (each module listens to settings:change itself) and are
// read back on every open, so the drawer never disagrees with what is stored. Focus is trapped inside
// while it is open; Esc and the Close button shut it and focus returns to whatever opened it.

import * as copy from './copy.js';
import { el, setClass } from './dom.js';
import { closeGlyph } from './glyphs.js';

const SLIDERS = {
  sens: { min: 0.2, max: 3, step: 0.05, padStep: 0.1, show: (v) => `${Number(v).toFixed(2)}×` },
  volume: { min: 0, max: 100, step: 1, padStep: 5, show: (v) => `${Math.round(v)}%` },
  fov: { min: 60, max: 95, step: 1, padStep: 1, show: (v) => `${Math.round(v)}°` },
};

export function createPanel(G, hooks) {
  const text = G.config.text;
  const P = copy.panel;
  const groups = []; // {key, buttons: [{node, value}]}
  const sliders = []; // {key, input, output, spec}
  let opener = null;
  let open = false;
  let tab = 'settings';
  let uid = 0;
  const id = (name) => `mi-${name}-${++uid}`;

  const click = (fn) => (e) => {
    G.events.emit('ui:click', {});
    fn(e);
  };

  // ---- header -----------------------------------------------------------------------------------
  const tabs = {};
  const pages = {};
  const tablist = el('div', { class: 'panel-tabs', role: 'tablist', 'aria-label': P.label });
  for (const name of ['settings', 'controls']) {
    const tid = id('tab');
    const pid = id('page');
    tabs[name] = el('button', { class: 'panel-tab', type: 'button', role: 'tab', id: tid, 'aria-controls': pid, 'aria-selected': 'false' }, P.tabs[name]);
    pages[name] = el('div', { class: 'panel-page', role: 'tabpanel', id: pid, 'aria-labelledby': tid });
    tabs[name].addEventListener('click', click(() => setTab(name, true)));
    tablist.append(tabs[name]);
  }
  const closeBtn = el('button', { class: 'panel-close', type: 'button', 'aria-label': P.close }, closeGlyph(), el('span', null, P.close));
  closeBtn.addEventListener('click', click(() => close()));

  const titleId = id('title');
  const node = el(
    'div',
    { class: 'panel', role: 'dialog', 'aria-modal': 'true', 'aria-labelledby': titleId, tabindex: '-1', hidden: true },
    el('div', 'panel-head', el('h2', { class: 'panel-title', id: titleId }, P.label), tablist, closeBtn),
    el('div', 'panel-body', pages.settings, pages.controls),
  );
  const scrim = el('div', 'panel-scrim');
  scrim.addEventListener('click', () => close());

  // ---- settings page ----------------------------------------------------------------------------
  function row(label, control, extraClass = '') {
    return el('div', `panel-row${extraClass ? ` ${extraClass}` : ''}`, label, control);
  }

  function segmented(key, label, options) {
    const lid = id('lbl');
    const wrap = el('div', { class: `seg seg-${options.length}`, role: 'group', 'aria-labelledby': lid });
    const buttons = [];
    for (const [value, name] of options) {
      const b = el('button', { class: 'seg-btn', type: 'button', 'aria-pressed': 'false' }, name);
      b.addEventListener(
        'click',
        click(() => {
          G.settings.set(key, value);
          refresh();
        }),
      );
      wrap.append(b);
      buttons.push({ node: b, value });
    }
    groups.push({ key, buttons });
    return row(el('div', { class: 'panel-label', id: lid }, label), wrap);
  }

  function slider(key, label) {
    const spec = SLIDERS[key];
    const iid = id('in');
    const input = el('input', { type: 'range', id: iid, min: spec.min, max: spec.max, step: spec.step, class: 'slider' });
    const output = el('output', { class: 'slider-out num', for: iid });
    input.addEventListener('input', () => {
      const v = Number(input.value);
      G.settings.set(key, key === 'volume' ? v / 100 : v);
      output.textContent = spec.show(v);
      paintSlider(input, spec);
    });
    input.addEventListener('change', () => G.events.emit('ui:click', {}));
    sliders.push({ key, input, output, spec });
    return row(el('div', 'panel-label-row', el('label', { class: 'panel-label', for: iid }, label), output), input, 'is-slider');
  }

  function paintSlider(input, spec) {
    const k = (Number(input.value) - spec.min) / (spec.max - spec.min);
    input.style.setProperty('--k', `${Math.round(k * 1000) / 10}%`);
  }

  const invertBtn = el('button', { class: 'toggle', type: 'button', 'aria-pressed': 'false' }, el('span', 'toggle-knob'), el('span', 'toggle-text'));
  invertBtn.addEventListener(
    'click',
    click(() => {
      G.settings.set('invertY', !G.settings.get('invertY'));
      refresh();
    }),
  );
  const invertLabel = id('lbl');
  invertBtn.setAttribute('aria-labelledby', invertLabel);

  const fsBtn = el('button', { class: 'btn', type: 'button' }, P.fullscreenEnter);
  const fsTarget = document.documentElement;
  const fsAvailable = !!(document.fullscreenEnabled || document.webkitFullscreenEnabled) && !!(fsTarget.requestFullscreen || fsTarget.webkitRequestFullscreen);
  fsBtn.addEventListener(
    'click',
    click(() => {
      try {
        const inFs = document.fullscreenElement || document.webkitFullscreenElement;
        const p = inFs ? (document.exitFullscreen || document.webkitExitFullscreen).call(document) : (fsTarget.requestFullscreen || fsTarget.webkitRequestFullscreen).call(fsTarget);
        if (p && typeof p.catch === 'function') p.catch(() => (fsBtn.textContent = P.fullscreenFail));
      } catch {
        fsBtn.textContent = P.fullscreenFail;
      }
    }),
  );
  document.addEventListener('fullscreenchange', () => refresh());

  const qualityNote = el('p', 'panel-note');
  const diffs = G.config.flow.difficulties || ['hustler', 'boss', 'kingpin'];
  pages.settings.append(
    segmented('difficulty', P.difficulty, diffs.map((d) => [d, text.difficulties[d]])),
    segmented('view', P.view, [1, 2, 3].map((v) => [v, P.views[v]])),
    segmented('quality', P.quality, [['auto', P.auto], ...['low', 'medium', 'high', 'ultra'].map((q) => [q, P.qualities[q]])]),
    slider('sens', P.sens),
    row(el('div', { class: 'panel-label', id: invertLabel }, P.invertY), invertBtn, 'is-inline'),
    slider('volume', P.volume),
    slider('fov', P.fov),
    fsAvailable ? row(el('div', 'panel-label', P.display), fsBtn, 'is-inline') : '', // native append(): never null
    qualityNote,
    el('p', 'panel-note', (text.notes && text.notes.difficulty) || P.noteDifficulty),
  );

  // ---- controls page ----------------------------------------------------------------------------
  // A touch key is drawn with the on-screen button's own glyph (config/player.js touchGlyphs), the same
  // line art the thumbs see: the buttons carry no words.
  const touchGlyphs = (G.config.player && G.config.player.touchGlyphs) || {};
  function keycap(k) {
    if (!k || typeof k !== 'object') return el('kbd', 'cap', k);
    const art = el('span', { class: 'cap-glyph', 'aria-hidden': 'true' });
    art.innerHTML = `<svg viewBox="0 0 32 32" focusable="false">${touchGlyphs[k.glyph] || ''}</svg>`;
    return el('kbd', { class: 'cap is-glyph', 'aria-label': k.label || k.glyph }, art, k.label ? el('span', 'cap-text', k.label) : null);
  }
  function keycaps(keys) {
    return el('span', 'caps', ...keys.map(keycap));
  }
  const sections = {};
  for (const device of ['kbm', 'touch', 'pad']) {
    const table = copy.controls[device];
    const list = el('dl', 'ctl-list');
    for (const [action, keys, extra] of table.rows) {
      list.append(el('dt', null, action), el('dd', null, keycaps(keys), extra ? el('span', 'ctl-extra', extra) : null));
    }
    sections[device] = el('section', { class: 'ctl', 'aria-label': table.title }, el('h3', 'ctl-title', table.title), list, table.note ? el('p', 'panel-note', table.note) : null);
    pages.controls.append(sections[device]);
  }

  /** The device in use comes first on the Controls tab (on a phone the touch table, not the keyboard one). */
  function orderControls() {
    const device = (G.input && G.input.device) || 'kbm';
    const order = device === 'touch' ? ['touch', 'kbm', 'pad'] : device === 'pad' ? ['pad', 'kbm', 'touch'] : ['kbm', 'touch', 'pad'];
    if (pages.controls.firstChild === sections[order[0]]) return;
    pages.controls.append(...order.map((d) => sections[d]));
  }

  // ---- behaviour --------------------------------------------------------------------------------
  function setTab(name, focusTab = false) {
    tab = name;
    for (const n in tabs) {
      const on = n === name;
      tabs[n].setAttribute('aria-selected', on ? 'true' : 'false');
      tabs[n].tabIndex = on ? 0 : -1;
      pages[n].hidden = !on;
    }
    if (focusTab) tabs[name].focus({ preventScroll: true });
  }

  function refresh() {
    const s = G.settings;
    const activeTier = (G.quality && G.quality.name) || 'medium';
    for (const g of groups) {
      const value = s.get(g.key);
      for (const b of g.buttons) {
        let on = String(b.value) === String(value);
        // Auto quality: the tier it picked shows pressed as well, so the player sees what they got.
        if (g.key === 'quality' && value === 'auto' && b.value === activeTier) on = true;
        b.node.setAttribute('aria-pressed', on ? 'true' : 'false');
        setClass(b.node, 'is-implied', g.key === 'quality' && value === 'auto' && b.value === activeTier);
      }
    }
    for (const sl of sliders) {
      const raw = s.get(sl.key);
      const v = sl.key === 'volume' ? Math.round(raw * 100) : raw;
      sl.input.value = String(v);
      sl.output.textContent = sl.spec.show(v);
      paintSlider(sl.input, sl.spec);
    }
    const inv = !!s.get('invertY');
    invertBtn.setAttribute('aria-pressed', inv ? 'true' : 'false');
    invertBtn.lastChild.textContent = inv ? P.on : P.off;
    const inFs = !!(document.fullscreenElement || document.webkitFullscreenElement);
    if (fsBtn.textContent !== P.fullscreenFail) fsBtn.textContent = inFs ? P.fullscreenExit : P.fullscreenEnter;
    const tierName = P.qualities[activeTier] || activeTier;
    qualityNote.textContent = s.get('quality') === 'auto' ? P.noteAuto(tierName) : P.noteManual;
  }

  /** Buttons and inputs that can take focus right now, in order. */
  function focusables() {
    return [...node.querySelectorAll('button, input, [tabindex="0"]')].filter((n) => !n.disabled && n.offsetParent !== null && n.tabIndex >= 0);
  }

  function openPanel(name = 'settings', from = null) {
    opener = from || document.activeElement;
    open = true;
    refresh();
    orderControls();
    setTab(name === 'controls' ? 'controls' : 'settings');
    node.hidden = false;
    scrim.hidden = false;
    setClass(node, 'is-open', true);
    setClass(scrim, 'is-open', true);
    node.querySelector('.panel-body').scrollTop = 0;
    node.focus({ preventScroll: true });
    hooks.onChange(true);
  }

  function close() {
    if (!open) return;
    open = false;
    setClass(node, 'is-open', false);
    setClass(scrim, 'is-open', false);
    node.hidden = true;
    scrim.hidden = true;
    const back = opener && opener.isConnected && opener.offsetParent !== null ? opener : null;
    opener = null;
    hooks.onChange(false, back);
  }

  node.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      close();
      return;
    }
    if (e.key === 'Tab') {
      const list = focusables();
      if (!list.length) return;
      const i = list.indexOf(document.activeElement);
      if (e.shiftKey && (i <= 0 || document.activeElement === node)) {
        e.preventDefault();
        list[list.length - 1].focus();
      } else if (!e.shiftKey && i === list.length - 1) {
        e.preventDefault();
        list[0].focus();
      }
      return;
    }
    // Arrow keys move between the two tabs (the WAI tabs pattern).
    if ((e.key === 'ArrowLeft' || e.key === 'ArrowRight') && document.activeElement && document.activeElement.getAttribute('role') === 'tab') {
      e.preventDefault();
      setTab(tab === 'settings' ? 'controls' : 'settings', true);
    }
  });

  /** A gamepad left / right on a focused slider: one pad step. Returns true when it was a slider. */
  function nudge(target, dir) {
    const sl = sliders.find((s) => s.input === target);
    if (!sl) return false;
    const v = Math.min(sl.spec.max, Math.max(sl.spec.min, Number(sl.input.value) + Math.sign(dir) * sl.spec.padStep));
    sl.input.value = String(Math.round(v * 1000) / 1000);
    sl.input.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  }

  return {
    node,
    scrim,
    open: openPanel,
    close,
    refresh,
    focusables,
    nudge,
    setTab,
    get isOpen() {
      return open;
    },
    get tab() {
      return tab;
    },
  };
}
