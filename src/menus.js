// G.menus (CONTRACT 6.12): the title screen, the pause / death / debrief cards, the intro location card
// and the settings / controls drawer (src/ui/panel.js).
//
// Screens: 'none' | 'title' | 'paused' | 'dead' | 'complete'. Showing a screen fades in its veil, closes
// the drawer and focuses the primary button after 30 ms. Menus talk to the game only through G.game and to
// the settings through G.settings.set. The click that starts a run also unlocks audio and asks for
// pointer lock (browsers only allow both from a user gesture).
//
// Navigation: mouse / touch clicks, the keyboard's own focus order (Tab, Enter, Space, arrows on sliders),
// and the gamepad through input.menuNav() (D-pad / stick moves focus, left / right nudges sliders, A
// accepts, B backs out, Start = the screen's primary action). Every press emits ui:click, every pointer
// entering a button or gamepad move emits ui:hover.
//
// Beyond the contract: menus.openPanel(tab) (the HUD's settings button opens the drawer over the pause card).

import * as copy from './ui/copy.js';
import { applyBrand, el, ipxMark, reducedMotion, setClass } from './ui/dom.js';
import { arrowGlyph, recordGlyph } from './ui/glyphs.js';
import { deathStats, debriefStats, nextFocus, ratingName } from './ui/logic.js';
import { createPanel } from './ui/panel.js';

const FOCUS_DELAY_MS = 30;
const LOCATION_WIPE_SECS = 1.1;
const LOCATION_STEPS = 28;

export function createMenus(G) {
  const brand = G.config.brand;
  const text = G.config.text;
  applyBrand(brand);
  const ui = document.getElementById('ui');
  const rootEl = document.documentElement;
  const reduce = reducedMotion();

  const menus = {
    screen: 'none',
    panelOpen: false,
    show,
    locationCard,
    openPanel,
    update,
  };

  let primary = null; // the current screen's main button
  let focusTimer = 0;
  let panelClosing = false; // panelOpen stays true until the end of the frame the drawer closed in
  let locT = -1;

  // ------------------------------------------------------------------------------------------------
  // Building blocks
  // ------------------------------------------------------------------------------------------------

  function button(label, onClick, kind = '') {
    const b = el('button', { class: `btn${kind ? ` btn-${kind}` : ''}`, type: 'button' }, el('span', 'btn-label', label), kind === 'primary' ? arrowGlyph() : null);
    b.addEventListener('click', (e) => {
      G.audio.unlock();
      G.events.emit('ui:click', {});
      onClick(e, b);
    });
    return b;
  }

  // Hover sound for anything clickable in the menu layer (delegated: cards are rebuilt).
  function hoverable(root) {
    root.addEventListener('pointerover', (e) => {
      const target = e.target && e.target.closest ? e.target.closest('button') : null;
      if (!target || target.disabled || target === hoverable.last) return;
      hoverable.last = target;
      if (e.pointerType !== 'touch') G.events.emit('ui:hover', {});
    });
    root.addEventListener('pointerout', (e) => {
      if (e.target && e.target.closest && e.target.closest('button') === hoverable.last) hoverable.last = null;
    });
  }

  function picker(key, label, options, onPick) {
    const lid = `mi-pick-${key}`;
    const wrap = el('div', { class: 'seg', role: 'group', 'aria-labelledby': lid });
    const buttons = options.map(([value, name]) => {
      const b = el('button', { class: 'seg-btn', type: 'button', 'aria-pressed': 'false', 'data-value': value }, name);
      b.addEventListener('click', () => {
        G.events.emit('ui:click', {});
        G.settings.set(key, value);
        if (onPick) onPick(value);
        refreshTitle();
      });
      wrap.append(b);
      return b;
    });
    return { node: el('div', 'pick', el('div', { class: 'pick-label', id: lid }, label), wrap), buttons, key };
  }

  function startRun() {
    G.audio.unlock();
    G.input.requestLock();
    G.game.start({ mode: G.settings.get('mode') });
  }

  // ------------------------------------------------------------------------------------------------
  // DOM: layer, veil, letterbox, title, card, location card, drawer
  // ------------------------------------------------------------------------------------------------

  const veil = el('div', 'menu-veil');
  const bars = el('div', 'menu-bars', el('i', 'is-top'), el('i', 'is-bottom'));

  // Title
  const modeNote = el('p', 'title-note-mode');
  const pickMode = picker('mode', copy.title.modeLabel, (G.config.flow.modes || ['mission', 'holdout']).map((m) => [m, text.modes[m].name]));
  const pickDiff = picker('difficulty', copy.title.difficultyLabel, (G.config.flow.difficulties || ['hustler', 'boss', 'kingpin']).map((d) => [d, text.difficulties[d]]));
  const pickTime = picker('time', copy.title.timeLabel, [
    ['day', copy.title.times.day],
    ['night', copy.title.times.night],
  ]);
  const pickers = [pickMode, pickDiff, pickTime];
  const startBtn = button(text.title.start, () => startRun(), 'primary');
  const settingsBtn = button(text.title.settings, (e, b) => openPanel('settings', b));
  const controlsBtn = button(text.title.controls, (e, b) => openPanel('controls', b));
  const eyebrowRest = String(text.title.eyebrow).replace(/^IPX\s+/i, '');

  const glance = el(
    'aside',
    { class: 'glance', 'aria-label': copy.title.glance },
    el('div', 'glance-title', copy.title.glance),
    el('dl', 'glance-keys', ...copy.glance.flatMap(([verb, keys]) => [el('dt', null, el('span', 'caps', ...keys.map((k) => el('kbd', 'cap', k)))), el('dd', null, verb)])),
    el('dl', 'glance-other', ...copy.glanceOther.flatMap(([dev, line]) => [el('dt', null, dev), el('dd', null, line)])),
  );

  const title = el(
    'section',
    { class: 'scr scr-title', 'aria-label': brand.titlePlain, hidden: true },
    el(
      'div',
      'title-block',
      el('div', 'title-eyebrow', ipxMark(brand), el('span', null, eyebrowRest)),
      el('h1', 'title-mark', text.title.wordmark),
      el('div', 'title-star', text.title.star),
      el('p', 'title-premise', text.title.premise),
      el('div', 'title-picks', pickMode.node, pickDiff.node, pickTime.node),
      modeNote,
      el('div', 'title-actions', startBtn, settingsBtn, controlsBtn),
      el('p', 'title-foot', text.title.note),
    ),
    glance,
  );

  // Cards (pause, dead, complete): rebuilt on every show, they are rare.
  const cardBox = el('div', 'card');
  const card = el('section', { class: 'scr scr-card', role: 'dialog', 'aria-modal': 'false', hidden: true }, cardBox);

  // Intro location card
  const locPlace = el('div', 'loc-place');
  const locTag = el('div', 'loc-tag');
  const loc = el('div', { class: 'loc', 'aria-hidden': 'true', hidden: true }, el('div', 'loc-inner', locPlace, locTag));

  const panel = createPanel(G, {
    onChange(isOpen, back) {
      if (isOpen) {
        menus.panelOpen = true;
        panelClosing = false;
      } else {
        panelClosing = true; // cleared in update(), after the game has read this frame's keys
        const target = back || primary;
        if (target) target.focus({ preventScroll: true });
      }
      setClass(layer, 'has-panel', isOpen);
    },
  });

  const layer = el('div', 'menus', veil, bars, title, card, loc, panel.scrim, panel.node);
  panel.scrim.hidden = true;
  hoverable(layer);
  ui.append(layer);

  // ------------------------------------------------------------------------------------------------
  // Title
  // ------------------------------------------------------------------------------------------------

  function refreshTitle() {
    for (const p of pickers) {
      const value = String(G.settings.get(p.key));
      for (const b of p.buttons) b.setAttribute('aria-pressed', b.dataset.value === value ? 'true' : 'false');
    }
    const mode = G.settings.get('mode');
    modeNote.textContent = `${text.modes[mode] ? text.modes[mode].note : ''}`;
  }
  G.events.on('settings:change', () => {
    if (menus.screen === 'title') refreshTitle();
    if (panel.isOpen) panel.refresh();
  });

  // ------------------------------------------------------------------------------------------------
  // Cards
  // ------------------------------------------------------------------------------------------------

  function cardHead(kicker, heading, mark = false) {
    return el('header', 'card-head', mark ? ipxMark(brand, 'ipx-sm') : null, el('div', 'card-kicker', kicker), el('h2', { class: 'card-title', id: 'mi-card-title' }, heading));
  }

  function statList(rows) {
    return el(
      'dl',
      'card-stats',
      ...rows.flatMap(([label, value, flag]) => [el('dt', null, label), el('dd', 'num', value, flag ? el('span', 'stat-flag', copy.cards.newBest) : null)]),
    );
  }

  const CARDS = {
    paused() {
      const t = text.cards.pause;
      const resume = button(t.resume, () => G.game.resume(), 'primary');
      const hint = G.input && typeof G.input.hint === 'function' ? G.input.hint() : '';
      cardBox.append(
        cardHead(t.kicker, t.title, true),
        hint ? el('p', 'card-hint', hint) : '', // native append() would print a null as "null"
        el(
          'div',
          'card-actions',
          resume,
          button(t.settings, (e, b) => openPanel('settings', b)),
          button(t.controls, (e, b) => openPanel('controls', b)),
          button(t.restart, () => G.game.restart(), 'quiet'),
        ),
      );
      return resume;
    },
    dead(data) {
      const t = text.cards.dead;
      const again = button(t.retry, () => {
        G.input.requestLock();
        G.game.retry();
      }, 'primary');
      cardBox.append(
        cardHead(t.kicker, t.title),
        statList(deathStats(data, t.stats)),
        el('div', 'card-actions', again, button(copy.cards.toTitle, () => G.game.toTitle(), 'quiet')),
      );
      return again;
    },
    complete(data) {
      const t = text.cards.debrief;
      const again = button(t.again, () => {
        G.input.requestLock();
        G.game.redeploy();
      }, 'primary');
      const name = data.ratingName || ratingName(data.rating, text.ratings);
      cardBox.append(
        cardHead(t.kicker, t.title, true),
        el(
          'div',
          'card-rating',
          el('span', 'card-disc', recordGlyph()),
          el('div', null, el('div', 'card-rating-label', t.stats.rating), el('div', 'card-rating-name', name)),
        ),
        statList(debriefStats(data, t.stats)),
        el('div', 'card-actions', again, button(copy.cards.toTitle, () => G.game.toTitle(), 'quiet')),
        el('p', 'card-foot', copy.cards.ipxLine),
      );
      return again;
    },
  };

  // ------------------------------------------------------------------------------------------------
  // Screens
  // ------------------------------------------------------------------------------------------------

  function show(screen, data = {}) {
    const next = screen === 'title' || CARDS[screen] ? screen : 'none';
    menus.screen = next;
    panel.close();
    clearTimeout(focusTimer);
    layer.dataset.screen = next;
    setClass(layer, 'is-on', next !== 'none');
    setClass(rootEl, 'menu-open', next !== 'none');

    title.hidden = next !== 'title';
    card.hidden = !CARDS[next];
    cardBox.replaceChildren();
    card.className = `scr scr-card is-${next}`;
    primary = null;
    if (next === 'title') {
      refreshTitle();
      primary = startBtn;
    } else if (CARDS[next]) {
      primary = CARDS[next](data || {});
      card.setAttribute('aria-labelledby', 'mi-card-title');
    }
    if (next === 'none') {
      const focus = document.activeElement;
      if (focus && layer.contains(focus)) focus.blur();
      return;
    }
    if (next !== 'title') locationCard(false);
    focusTimer = setTimeout(() => {
      if (primary && primary.isConnected && !panel.isOpen) primary.focus({ preventScroll: true });
    }, FOCUS_DELAY_MS);
  }

  function openPanel(tab = 'settings', from = null) {
    if (menus.screen === 'none') return; // the HUD's gear pauses first; nothing to open over gameplay
    panel.open(tab, from);
  }

  function locationCard(on, data) {
    if (!on) {
      loc.hidden = true;
      locT = -1;
      return;
    }
    const src = data || text.location;
    const time = G.settings.get('time') === 'night' ? 'night' : 'day';
    const place = (src.byTime && src.byTime[time]) || copy.location[time] || src.place;
    locPlace.textContent = String(place).replace(/ (AM|PM)\b/, '\u00a0$1'); // the time never splits from its AM / PM
    locTag.textContent = src.tagline || text.location.tagline;
    loc.hidden = false;
    locT = reduce ? LOCATION_WIPE_SECS : 0;
    locPlace.style.setProperty('--wipe', reduce ? '100%' : '0%');
  }

  // ------------------------------------------------------------------------------------------------
  // Gamepad navigation
  // ------------------------------------------------------------------------------------------------

  function scope() {
    if (panel.isOpen) return panel.focusables();
    const root = menus.screen === 'title' ? title : card;
    return [...root.querySelectorAll('button, input')].filter((n) => !n.disabled && n.offsetParent !== null);
  }

  function padNav(on) {
    setClass(rootEl, 'pad-nav', on);
  }
  window.addEventListener('mousemove', () => padNav(false), { passive: true });

  function moveFocus(dir) {
    const list = scope();
    if (!list.length) return;
    const i = nextFocus(list.length, list.indexOf(document.activeElement), dir);
    const target = list[i];
    target.focus({ preventScroll: true });
    if (typeof target.scrollIntoView === 'function') target.scrollIntoView({ block: 'nearest' });
    padNav(true);
    G.events.emit('ui:hover', {});
  }

  function updateNav() {
    const input = G.input;
    if (!input || typeof input.menuNav !== 'function') return;
    const nav = input.menuNav();
    if (!nav) return;
    const focus = document.activeElement;
    if (nav.y) moveFocus(nav.y);
    if (nav.x) {
      if (panel.isOpen && focus && focus.getAttribute && focus.getAttribute('role') === 'tab') {
        // The unselected tab is out of the focus order (the WAI tabs pattern): left / right switches tabs.
        panel.setTab(panel.tab === 'settings' ? 'controls' : 'settings', true);
        padNav(true);
        G.events.emit('ui:hover', {});
      } else if (!(panel.isOpen && focus && panel.nudge(focus, nav.x))) {
        // Inside a picker row left / right steps across its options; anywhere else it moves like up / down.
        const seg = focus && focus.closest ? focus.closest('.seg') : null;
        if (seg) {
          const opts = [...seg.querySelectorAll('button')];
          const i = opts.indexOf(focus);
          const target = opts[Math.max(0, Math.min(opts.length - 1, i + nav.x))];
          if (target && target !== focus) {
            target.focus({ preventScroll: true });
            padNav(true);
            G.events.emit('ui:hover', {});
          }
        } else moveFocus(nav.x);
      }
    }
    if (nav.accept) {
      padNav(true);
      const target = focus && layer.contains(focus) && focus.tagName === 'BUTTON' ? focus : panel.isOpen ? null : primary;
      if (target) target.click();
    }
    if (nav.back) {
      if (panel.isOpen) panel.close();
      else if (menus.screen === 'paused') G.game.resume();
    }
    // Start on the title is the game's own (it reads menuNav too); paused: the pause action resumes.
    if (nav.start && !panel.isOpen && (menus.screen === 'dead' || menus.screen === 'complete') && primary) primary.click();
  }

  // Esc / P while the drawer is open closes the drawer and does not unpause (the panel stops Esc itself,
  // this covers P and focus that left the drawer).
  window.addEventListener('keydown', (e) => {
    if (!panel.isOpen) return;
    if (e.code === 'Escape' || e.code === 'KeyP') {
      e.preventDefault();
      panel.close();
    }
  });

  // ------------------------------------------------------------------------------------------------
  // Frame
  // ------------------------------------------------------------------------------------------------

  function update(dt) {
    if (panelClosing) {
      panelClosing = false;
      menus.panelOpen = false;
    }
    if (menus.screen !== 'none') updateNav();
    if (locT >= 0 && locT < LOCATION_WIPE_SECS) {
      locT += dt;
      const steps = Math.min(LOCATION_STEPS, Math.floor((locT / LOCATION_WIPE_SECS) * LOCATION_STEPS));
      locPlace.style.setProperty('--wipe', `${Math.round((steps / LOCATION_STEPS) * 1000) / 10}%`);
    }
  }

  return menus;
}
