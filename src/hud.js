// G.hud (CONTRACT 6.12, DESIGN 8.2): the in-game heads-up display, DOM over the canvas.
//
// Layout (the genre's standard one, in transit-sign plates):
//   top-left      mission badge: IPX lozenge, reel bullets 1 · 2 · 3 (or the holdout tally), objective line
//   top-right     minimap with the zone band, pause and settings buttons beside it
//   top-centre    banner (hud.warn) with the centre message under it
//   left-middle   kill feed
//   centre        crosshair (gap from weapon.spread), hit marker, damage arcs, interaction prompt
//   bottom-centre ammo cue, weapon bar (CHOPPER · NINE · melee), HP bar under it; radio subtitles above
//   world         objective markers, clamped to the screen edge
//
// Every per-frame write is change-detected (src/ui/dom.js setText / setStyle / setClass) and anything that
// moves does so with transforms. Pure rules and timings live in src/ui/logic.js.

import * as copy from './ui/copy.js';
import { applyBrand, bullet, el, ipxMark, reducedMotion, setClass, setStyle, setText } from './ui/dom.js';
import { chopperGlyph, damageArc, fistGlyph, gearGlyph, nineGlyph, pauseGlyph, promptRing } from './ui/glyphs.js';
import {
  HIT_TIERS,
  arcOpacity,
  bannerPose,
  clampMarker,
  createFeed,
  createRadioQueue,
  crosshairGap,
  cueLine,
  healthView,
  hitMarkerPose,
  hitTier,
  lowAmmo,
  markerOverAim,
  metres,
  reserveText,
  screenBearing,
  typedCount,
  zoneLabel,
} from './ui/logic.js';
import { createMinimap } from './ui/minimap.js';

const OBJECTIVE_CPS = 46; // objective line typewriter
const RADIO_CPS = 58; // radio subtitles typewriter
const ARC_LIFE = 1.5; // seconds a damage arc stays
const ARC_POOL = 4;
const MARKER_POOL = 5;
const BANNER_SECS = 3.4;
const GHOST_HOLD = 0.45; // the lost-health ghost waits this long before it drains
const MAX_PIPS = 60;

export function createHud(G) {
  const brand = G.config.brand;
  const text = G.config.text;
  const THREE = G.THREE;
  applyBrand(brand);
  const ui = document.getElementById('ui');
  const rootEl = document.documentElement;
  rootEl.dataset.hudPause = ''; // the touch layer's own pause button steps aside for ours

  // ------------------------------------------------------------------------------------------------
  // DOM
  // ------------------------------------------------------------------------------------------------

  const hud = el('div', { class: 'hud', 'aria-hidden': 'true' });

  // Mission badge (top-left)
  const badgeBullets = el('div', 'hud-badge-bullets');
  const badgeCount = el('span', 'hud-badge-count num');
  const badgeTally = el('span', 'hud-badge-tally num');
  const objLabel = el('div', 'hud-obj-label', copy.hud.objective);
  const objText = el('div', 'hud-obj-text');
  const objRule = el('div', 'hud-obj-rule');
  const badge = el(
    'div',
    'hud-badge plate',
    el('div', 'hud-badge-top', ipxMark(brand, 'ipx-sm'), badgeBullets, badgeCount, badgeTally),
    objRule,
    objLabel,
    objText,
  );

  // Minimap (top-right)
  const mapCanvas = el('canvas', { class: 'hud-map-canvas', width: 150, height: 150 });
  const zoneBand = el('div', 'hud-zone');
  const pauseBtn = el('button', { class: 'hud-btn', type: 'button', 'aria-label': copy.hud.pause, 'data-action': 'pause' }, pauseGlyph());
  const gearBtn = el('button', { class: 'hud-btn', type: 'button', 'aria-label': copy.hud.settings, 'data-action': 'settings' }, gearGlyph());
  const mapBox = el(
    'div',
    'hud-map',
    el('div', 'hud-btns', pauseBtn, gearBtn),
    el('div', 'hud-map-plate', el('div', 'hud-map-frame', mapCanvas, el('div', 'hud-map-north', 'N')), zoneBand),
  );

  // Banner and centre message (top-centre)
  const bannerText = el('span', 'hud-banner-text');
  const banner = el('div', 'hud-banner', bannerText);
  const messageText = el('span', 'hud-msg-text');
  const message = el('div', 'hud-msg', messageText);

  // Kill feed (left-middle)
  const feedEl = el('div', 'hud-feed');

  // Centre: crosshair, hit marker, damage arcs, prompt
  const ticks = ['up', 'down', 'left', 'right'].map((d) => el('i', `hud-xh-tick is-${d}`));
  const crosshair = el('div', 'hud-xh', ...ticks, el('i', 'hud-xh-dot'));
  const hit = el('div', 'hud-hit', el('i'), el('i'), el('i'), el('i'));
  const arcLayer = el('div', 'hud-arcs');
  const arcs = [];
  for (let i = 0; i < ARC_POOL; i++) {
    const node = damageArc();
    arcLayer.append(node);
    arcs.push({ node, life: 0, x: 0, z: 0, rot: '', op: -1 });
  }
  const ring = promptRing();
  const promptGlyph = el('span', 'hud-prompt-glyph');
  const promptText = el('span', 'hud-prompt-text');
  const prompt = el('div', 'hud-prompt', el('div', 'hud-prompt-key', ring.node, promptGlyph), el('div', 'hud-prompt-plate', promptText));

  // World markers
  const markerLayer = el('div', 'hud-markers');
  const markerEls = [];
  for (let i = 0; i < MARKER_POOL; i++) {
    const code = el('span', 'rb');
    const dist = el('span', 'hud-mk-dist num');
    const node = el('div', 'hud-mk', el('span', 'hud-mk-pin', code), dist);
    node.hidden = true;
    markerLayer.append(node);
    markerEls.push({ node, code, dist, codeText: '' });
  }

  // Weapon bar + HP (bottom-centre)
  const cue = el('div', 'hud-cue');
  function slot(id, glyph, key) {
    const name = el('span', 'hud-slot-name');
    const count = el('span', 'hud-slot-count num');
    const keycap = el('span', 'hud-slot-key');
    const pips = el('span', 'hud-pips');
    const node = el(
      'button',
      { class: `hud-slot is-${id}`, type: 'button', tabindex: '-1', 'data-slot': id },
      el('span', 'hud-slot-art', glyph),
      el('span', 'hud-slot-info', name, count),
      keycap,
      pips,
    );
    return { id, key, node, name, count, keycap, pips, pipEls: [], pipCount: -1, spent: -1 };
  }
  const slots = {
    chopper: slot('chopper', chopperGlyph(), 'weapon1'),
    nine: slot('nine', nineGlyph(), 'weapon2'),
    melee: slot('melee', fistGlyph(), 'melee'),
  };
  setText(slots.chopper.name, text.weapons.chopper.name);
  setText(slots.nine.name, text.weapons.nine.name);
  setText(slots.melee.name, copy.hud.melee);
  const hpNum = el('span', 'hud-hp-num num');
  const hpFill = el('i', 'hud-hp-fill');
  const hpGhost = el('i', 'hud-hp-ghost');
  const hpBar = el('div', 'hud-hp-bar', hpGhost, hpFill);
  const hp = el('div', 'hud-hp', el('span', 'hud-hp-label', copy.hud.hp), hpBar, hpNum);
  const wbar = el('div', 'hud-wbar', cue, el('div', 'hud-slots', slots.chopper.node, slots.nine.node, slots.melee.node), hp);

  hud.append(arcLayer, markerLayer, badge, mapBox, banner, message, feedEl, crosshair, hit, prompt, wbar);

  // Radio strip: outside the aria-hidden HUD, a polite live region; it also plays over the debrief.
  const radioSpeaker = el('div', 'radio-speaker');
  const radioLine = el('div', 'radio-line');
  const radioEl = el('div', { class: 'radio', role: 'status', 'aria-live': 'polite' }, radioSpeaker, el('div', 'radio-plate', radioLine));
  ui.append(hud, radioEl);

  // ------------------------------------------------------------------------------------------------
  // State
  // ------------------------------------------------------------------------------------------------

  const minimap = createMinimap(G, mapCanvas);
  const feed = createFeed(4, 4.2, 0.6);
  const radio = createRadioQueue(RADIO_CPS);
  const reduce = reducedMotion();

  let shown = false;
  let objective = '';
  let objT = 0;
  let reelsDone = 0;
  let reelsTotal = 0;
  let tally = '';
  let holdout = false;
  let markers = [];
  let bannerLeft = 0;
  let bannerSecs = BANNER_SECS;
  let messageLeft = 0;
  let promptSpec = null;
  let promptOn = false;
  let promptProg = -1;
  let hitT = 1;
  let hitScale = 1;
  let hitSecs = 0.24;
  let feedVersion = -1;
  let radioKey = null;
  let radioShown = -1;
  let ghost = 1;
  let ghostHold = 0;
  let lastHealth = -1;
  let width = window.innerWidth || 960;
  let height = window.innerHeight || 540;
  let gap = -1;
  let zoneKey = '';
  let mapDrawn = -1;

  const hv = { value: 0, fill: 0, critical: false };
  const scratch = new THREE.Vector3();
  const clamped = { x: 0, y: 0, off: false };

  let limDown = 0.6; // NDC: how far down a pinned marker may go (above the weapon bar)
  function measure() {
    width = window.innerWidth || width;
    height = window.innerHeight || height;
    const top = wbar.getBoundingClientRect().top;
    const floor = top > 0 ? top - 34 : height * 0.8; // the pin, its distance tag, a little air
    limDown = Math.max(0.2, Math.min(0.9, (2 * floor) / height - 1));
  }
  window.addEventListener('resize', () => {
    measured = false;
  });
  let measured = false;

  // ------------------------------------------------------------------------------------------------
  // Pointer: the HUD's own buttons (minimap side, weapon slots)
  // ------------------------------------------------------------------------------------------------

  /** Keeps a press on a HUD control from also reaching the game (fire, look, pointer lock). */
  const swallow = (e) => e.stopPropagation();
  for (const node of [pauseBtn, gearBtn, slots.chopper.node, slots.nine.node, slots.melee.node]) {
    node.addEventListener('pointerdown', swallow);
    node.addEventListener('mousedown', swallow);
    node.addEventListener('touchstart', swallow, { passive: true });
  }
  pauseBtn.addEventListener('click', () => {
    G.events.emit('ui:click', {});
    G.game.pause();
  });
  gearBtn.addEventListener('click', () => {
    G.events.emit('ui:click', {});
    G.game.pause();
    if (typeof G.menus.openPanel === 'function') G.menus.openPanel('settings');
  });
  for (const id in slots) {
    const s = slots[id];
    s.node.addEventListener('click', () => {
      const input = G.input;
      if (typeof input.tap !== 'function') return;
      const w = G.weapon;
      if (id === 'melee') input.tap('melee');
      else if (w && w.current !== id) input.tap(s.key);
      G.events.emit('ui:click', {});
    });
  }

  // ------------------------------------------------------------------------------------------------
  // Events the HUD listens to itself
  // ------------------------------------------------------------------------------------------------

  G.events.on('player:hitEnemy', (e) => {
    const tier = hitTier(e);
    const t = HIT_TIERS[tier];
    hit.dataset.tier = tier;
    hitScale = t.scale;
    hitSecs = t.secs;
    hitT = 0;
  });

  G.events.on('enemy:killed', (e) => {
    const names = text.enemies;
    const name = (names[e.type] || names.goon).down;
    feed.push(name, e.part === 'head' ? names.headshot : '', e.weapon || '');
  });

  G.events.on('player:hit', (e) => {
    if (!e || !e.from || !Number.isFinite(e.from.x)) return;
    let arc = arcs[0];
    for (const a of arcs) {
      if (a.life <= 0) {
        arc = a;
        break;
      }
      if (a.life < arc.life) arc = a;
    }
    arc.life = ARC_LIFE;
    arc.x = e.from.x;
    arc.z = e.from.z;
  });

  // ------------------------------------------------------------------------------------------------
  // Per-frame parts
  // ------------------------------------------------------------------------------------------------

  function updateBadge(dt) {
    if (objT >= 0) {
      objT += dt;
      const n = typedCount(objective.length, objT, OBJECTIVE_CPS);
      setText(objText, objective.slice(0, n));
      if (n >= objective.length) objT = -1;
    }
  }

  function renderBullets() {
    badgeBullets.replaceChildren();
    if (holdout || reelsTotal <= 0) return;
    const out = new Set();
    let anyReel = false;
    for (const m of markers) {
      if (m.kind === 'reel') {
        out.add(String(m.code));
        anyReel = true;
      }
    }
    const allIn = markers.some((m) => m.kind === 'exit');
    for (let i = 1; i <= reelsTotal; i++) {
      const code = String(i);
      const done = allIn || (anyReel ? !out.has(code) : i <= reelsDone);
      badgeBullets.append(bullet(code, done ? 'is-done' : ''));
    }
    setText(badgeCount, `${reelsDone}/${reelsTotal}`);
  }

  function updateCrosshair() {
    const player = G.player;
    const weapon = G.weapon;
    const hidden = !player.alive || (player.ads || 0) > 0.6 || (weapon && weapon.state === 'lowered');
    setClass(crosshair, 'is-off', hidden);
    if (hidden) return;
    const fov = (G.camera && G.camera.fov) || G.settings.get('fov') || 74;
    const g = crosshairGap(weapon ? weapon.spread : undefined, fov, height, !!player.sprinting);
    if (g === gap) return;
    gap = g;
    setStyle(crosshair, '--gap', `${g}px`);
  }

  function updateHit(dt) {
    if (hitT >= 1) return;
    hitT = Math.min(1, hitT + dt / hitSecs);
    const pose = hitMarkerPose(hitT, reduce ? 1 : hitScale);
    hit.style.opacity = pose.opacity.toFixed(2);
    hit.style.transform = `translate(-50%, -50%) rotate(45deg) scale(${pose.scale.toFixed(3)})`;
  }

  function updateArcs(dt) {
    const p = G.player;
    for (const a of arcs) {
      if (a.life <= 0) {
        if (a.op !== 0) {
          a.op = 0;
          a.node.style.opacity = '0';
        }
        continue;
      }
      a.life -= dt;
      const op = arcOpacity(a.life);
      if (op !== a.op) {
        a.op = op;
        a.node.style.opacity = String(op);
      }
      const deg = ((screenBearing(a.x, a.z, p.pos.x, p.pos.z, p.yaw) * 180) / Math.PI).toFixed(1);
      if (deg !== a.rot) {
        a.rot = deg;
        a.node.style.transform = `translate(-50%, -50%) rotate(${deg}deg)`;
      }
    }
  }

  function updateMarkers() {
    const cam = G.camera;
    const p = G.player;
    const ads = (p.ads || 0) >= 0.5;
    setClass(markerLayer, 'is-off', ads);
    if (!cam || ads) return;
    if (!measured) {
      measured = true;
      measure();
    }
    cam.updateMatrixWorld();
    for (let i = 0; i < markerEls.length; i++) {
      const m = markers[i];
      const view = markerEls[i];
      const node = view.node;
      if (!m || !m.pos) {
        if (!node.hidden) node.hidden = true;
        continue;
      }
      const dx = m.pos.x - p.pos.x;
      const dz = m.pos.z - p.pos.z;
      const d = Math.hypot(dx, dz);
      if (d < 3) {
        if (!node.hidden) node.hidden = true;
        continue;
      }
      if (node.hidden) node.hidden = false;
      const code = String(m.code);
      if (view.codeText !== code) {
        view.codeText = code;
        view.code.textContent = code;
        view.code.dataset.line = code.toLowerCase();
        setClass(view.code, 'rb-wide', code.length > 1);
      }
      scratch.set(m.pos.x, m.pos.y + (m.kind === 'exit' ? 1.2 : 1.9), m.pos.z);
      scratch.applyMatrix4(cam.matrixWorldInverse);
      const behind = scratch.z > 0;
      scratch.applyMatrix4(cam.projectionMatrix);
      clampMarker(scratch.x, scratch.y, behind, 0.9, 0.78, clamped, limDown);
      const x = Math.round((clamped.x * 0.5 + 0.5) * width);
      const y = Math.round((-clamped.y * 0.5 + 0.5) * height);
      setStyle(node, 'transform', `translate(${x}px, ${y}px)`);
      setClass(node, 'is-edge', clamped.off);
      setClass(node, 'is-dim', !clamped.off && markerOverAim(clamped.x, clamped.y));
      setText(view.dist, metres(d));
    }
  }

  function slotAmmo(s, mag, reserve, magSize, active) {
    setText(s.count, `${mag} / ${reserveText(reserve)}`);
    setClass(s.node, 'is-low', active && mag > 0 && lowAmmo(mag, magSize));
    setClass(s.node, 'is-empty', active && mag <= 0);
    // The pip row: one per round of the magazine, spent ones dimmed. Built once per magazine size.
    const n = Math.max(1, Math.min(MAX_PIPS, magSize | 0));
    if (s.pipCount !== n) {
      s.pipCount = n;
      s.spent = -1;
      s.pips.replaceChildren();
      s.pipEls = [];
      for (let i = 0; i < n; i++) {
        const pip = el('i');
        s.pips.append(pip);
        s.pipEls.push(pip);
      }
    }
    const spent = Math.max(0, n - Math.min(n, mag));
    if (spent !== s.spent) {
      s.spent = spent;
      for (let i = 0; i < n; i++) setClass(s.pipEls[i], 'is-spent', i >= n - spent);
    }
  }

  function updateWeapon() {
    const w = G.weapon;
    const input = G.input;
    const device = input.device || 'kbm';
    if (!w || !w.def) return;
    const current = w.current;
    for (const id of ['chopper', 'nine']) {
      const s = slots[id];
      const active = current === id;
      setClass(s.node, 'is-active', active && w.state !== 'melee');
      if (active) slotAmmo(s, w.mag, w.reserve, w.magSize, true);
      else if (w.other && w.other.id === id) {
        const size = (G.config.weapons[id] && G.config.weapons[id].magSize) || 30;
        slotAmmo(s, w.other.mag, w.other.reserve, size, false);
      }
      setText(s.keycap, device === 'touch' ? '' : input.glyph(s.key));
    }
    setClass(slots.melee.node, 'is-active', w.state === 'melee');
    setText(slots.melee.keycap, device === 'touch' ? '' : input.glyph('melee'));

    const line = cueLine(w.cue, { reload: input.glyph('reload'), swap: input.glyph('swap') }, device, copy.hud.cue);
    setText(cue, line.text);
    setClass(cue, 'is-alarm', line.alarm);
    setClass(cue, 'is-on', !!line.text);
  }

  function updateHealth(dt) {
    const p = G.player;
    healthView(p.health, p.maxHealth, hv);
    if (hv.fill !== lastHealth) {
      if (hv.fill < lastHealth) ghostHold = GHOST_HOLD;
      else if (hv.fill > ghost) ghost = hv.fill;
      lastHealth = hv.fill;
      setStyle(hpFill, 'transform', `scaleX(${hv.fill})`);
      setText(hpNum, String(hv.value));
      setClass(hp, 'is-critical', hv.critical);
    }
    if (ghost > hv.fill) {
      if (ghostHold > 0) ghostHold -= dt;
      else ghost = Math.max(hv.fill, ghost - dt * 0.9);
    }
    setStyle(hpGhost, 'transform', `scaleX(${(Math.round(ghost * 200) / 200).toFixed(3)})`);
  }

  function updateFeed(dt) {
    feed.update(dt);
    if (feed.version() !== feedVersion) {
      feedVersion = feed.version();
      feedEl.replaceChildren();
      for (const line of feed.lines) {
        const glyph = line.weapon === 'chopper' ? chopperGlyph() : line.weapon === 'nine' ? nineGlyph() : line.weapon === 'melee' ? fistGlyph() : null;
        const node = el('div', 'hud-feed-line', glyph ? el('span', 'hud-feed-gl', glyph) : null, el('span', 'hud-feed-text', line.text), line.tag ? el('span', 'hud-feed-tag', line.tag) : null);
        line.node = node;
        line.op = 1;
        feedEl.append(node);
      }
    }
    for (const line of feed.lines) {
      const op = feed.opacity(line);
      if (line.node && op !== line.op) {
        line.op = op;
        line.node.style.opacity = String(op);
      }
    }
  }

  function updateBanner(dt) {
    if (bannerLeft <= 0) return;
    bannerLeft -= dt;
    const k = 1 - Math.max(0, bannerLeft) / bannerSecs;
    const pose = reduce ? { opacity: k < 0.9 ? 1 : 0, spread: 0 } : bannerPose(k);
    banner.style.opacity = pose.opacity.toFixed(2);
    bannerText.style.transform = `scaleX(${(1 + 0.22 * pose.spread).toFixed(3)})`;
    if (bannerLeft <= 0) banner.style.opacity = '0';
  }

  function updateMessage(dt) {
    if (messageLeft <= 0) return;
    messageLeft -= dt;
    if (messageLeft <= 0) setClass(message, 'is-on', false);
  }

  function updateRadio(dt) {
    radio.update(dt);
    const line = radio.current();
    const state = G.game.state;
    setClass(radioEl, 'is-on', !!line && state !== 'paused' && state !== 'title');
    if (line !== radioKey) {
      radioKey = line;
      radioShown = -1;
      if (line) {
        setText(radioSpeaker, line.speaker);
        radioEl.setAttribute('aria-label', `${line.speaker}: ${line.text}`);
      }
    }
    if (!line) return;
    const n = radio.shown();
    if (n !== radioShown) {
      radioShown = n;
      setText(radioLine, line.text.slice(0, n));
    }
  }

  function updateZone() {
    const level = G.level;
    const p = G.player.pos;
    if (!level || typeof level.zoneAt !== 'function') return;
    let id = 'avenue';
    try {
      id = level.zoneAt(p.x, p.z) || 'avenue';
    } catch {
      /* a level without zones */
    }
    const name = typeof text.zoneName === 'function' ? text.zoneName(id, p.z) : zoneLabel(id, p.z, copy.hud.zones);
    if (name !== zoneKey) {
      zoneKey = name;
      setText(zoneBand, name);
    }
  }

  function updatePrompt() {
    if (!promptSpec) return;
    const k = Math.round(Math.min(1, Math.max(0, promptSpec.progress || 0)) * 200) / 200;
    if (k === promptProg) return;
    promptProg = k;
    ring.fill.setAttribute('stroke-dashoffset', (ring.circumference * (1 - k)).toFixed(2));
    setClass(prompt, 'is-holding', k > 0);
  }

  // ------------------------------------------------------------------------------------------------
  // API
  // ------------------------------------------------------------------------------------------------

  const api = {
    show(on) {
      shown = !!on;
      setClass(hud, 'is-on', shown);
      if (shown) minimap.invalidate(); // the block may have changed under it since the last run
    },
    reset() {
      objective = '';
      objT = -1;
      setText(objText, '');
      setClass(badge, 'is-empty', true);
      reelsDone = reelsTotal = 0;
      tally = '';
      holdout = false;
      markers = [];
      minimap.setMarkers(markers);
      renderBullets();
      setText(badgeTally, '');
      setClass(badge, 'is-holdout', false);
      feed.clear();
      radio.clear();
      bannerLeft = messageLeft = 0;
      banner.style.opacity = '0';
      setClass(message, 'is-on', false);
      for (const a of arcs) a.life = 0;
      hitT = 1;
      hit.style.opacity = '0';
      api.prompt(null);
      ghost = 1;
      lastHealth = -1;
    },
    setObjective(value) {
      const next = String(value || '');
      if (next === objective) return;
      objective = next;
      objT = 0;
      setText(objText, '');
      setClass(badge, 'is-empty', !next);
      if (next && !reduce && typeof objRule.animate === 'function') {
        objRule.animate([{ backgroundColor: brand.colors.ink, transform: 'scaleX(1.0)' }, { backgroundColor: brand.colors.gold }], {
          duration: 900,
          easing: 'ease-out',
        });
        badge.animate([{ boxShadow: `inset 3px 0 0 ${brand.colors.ink}` }, { boxShadow: `inset 3px 0 0 ${brand.colors.gold}` }], { duration: 900 });
      }
    },
    setReels(done, total) {
      holdout = false;
      reelsDone = Math.max(0, done | 0);
      reelsTotal = Math.max(0, total | 0);
      setClass(badge, 'is-holdout', false);
      setText(badgeTally, '');
      renderBullets();
    },
    setTally(value) {
      holdout = true;
      tally = String(value || '');
      setClass(badge, 'is-holdout', true);
      badgeBullets.replaceChildren();
      setText(badgeCount, '');
      setText(badgeTally, tally);
    },
    setMarkers(list) {
      markers = Array.isArray(list) ? list.slice(0, MARKER_POOL) : [];
      minimap.setMarkers(markers);
      if (!holdout) renderBullets();
    },
    prompt(spec) {
      promptSpec = spec || null;
      const on = !!spec;
      if (on !== promptOn) {
        promptOn = on;
        setClass(prompt, 'is-on', on);
      }
      if (!spec) {
        promptProg = -1;
        return;
      }
      const glyph = String(spec.glyph || (G.input.glyph ? G.input.glyph('interact') : 'E'));
      setText(promptGlyph, glyph);
      setClass(promptGlyph, 'is-long', glyph.length > 1);
      setText(promptText, String(spec.text || ''));
      updatePrompt();
    },
    warn(value, secs) {
      if (!value) return;
      setText(bannerText, String(value));
      bannerSecs = Math.max(BANNER_SECS, Number(secs) || 0);
      bannerLeft = bannerSecs;
      updateBanner(0);
    },
    message(value, secs) {
      if (!value) {
        messageLeft = 0;
        setClass(message, 'is-on', false);
        return;
      }
      setText(messageText, String(value));
      messageLeft = Number(secs) > 0 ? Number(secs) : 3;
      setClass(message, 'is-on', true);
    },
    radio(speaker, value, secs) {
      radio.push(speaker || text.radio.speaker, value, secs);
    },
    clearRadio() {
      radio.clear();
    },
    update(dt) {
      updateRadio(dt);
      updateFeed(dt);
      if (!shown) return;
      updateBadge(dt);
      updateBanner(dt);
      updateMessage(dt);
      updateHit(dt);
      if (!G.player || !G.player.pos) return;
      updateCrosshair();
      updateArcs(dt);
      updateMarkers();
      updateWeapon();
      updateHealth(dt);
      updatePrompt();
      updateZone();
      // The map turns smoothly at 30 fps; more is wasted, and fast-forwarded steps need none.
      if (G.time.real - mapDrawn >= 1 / 32 || G.time.real < mapDrawn) {
        mapDrawn = G.time.real;
        minimap.draw();
      }
    },
  };

  api.reset();
  return api;
}
