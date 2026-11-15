// Shared helpers for the flow scenarios (tools/scenarios/flow-*.cjs). Not a scenario itself.
//
// install() runs in the page: it records every flow event in order (with a compact payload), every line
// the game hands the HUD (warn / message / radio / objective / tally / reels / prompt), every card the
// menus are asked to show (with its data) and a few module calls the checks need (explosives.reset,
// enemies.setDifficulty / setScale, atmos.setTime, weapon.addReserve, player.heal).
//
// The scenarios act as a director: they move the player with player.reset, hold real keys for Interact
// and Pause, and kill enemies through enemies.damage. They work against the stubs and the full build.

'use strict';

const FLOW_EVENTS = [
  'game:state', 'game:reset', 'objective:progress', 'objective:done', 'objective:all', 'extraction:reached',
  'holdout:wave', 'radio:line', 'enemy:spawn', 'enemy:killed', 'player:dead', 'input:lock',
];

function install(names) {
  const G = window.__G;
  const want = new Set(names);
  const rec = (window.__flow = {
    events: [], // [name, payload] in order (objective:progress is folded: only its count and last value)
    progress: { count: 0, last: null, max: 0 },
    hud: { warn: [], message: [], radio: [], objective: [], tally: [], reels: [], prompt: null, prompts: 0 },
    cards: [],
    calls: { explosivesReset: 0, setDifficulty: [], setScale: [], setTime: [], addReserve: [], heal: [], locationCard: [] },
  });
  const brief = (v) => {
    if (v && v.isVector3) return [Math.round(v.x * 100) / 100, Math.round(v.y * 100) / 100, Math.round(v.z * 100) / 100];
    if (v && typeof v === 'object') return v.type || '[object]';
    return v;
  };
  const emit = G.events.emit;
  G.events.emit = (name, payload) => {
    if (name === 'objective:progress') {
      rec.progress.count++;
      rec.progress.last = { id: payload.id, t: payload.t };
      rec.progress.max = Math.max(rec.progress.max, payload.t);
    } else if (want.has(name)) {
      const flat = {};
      for (const key in payload || {}) flat[key] = brief(payload[key]);
      rec.events.push([name, flat, Math.round(G.time.t * 1000) / 1000]);
    }
    return emit(name, payload);
  };
  const wrap = (obj, key, fn) => {
    if (!obj || typeof obj[key] !== 'function') return;
    const orig = obj[key];
    obj[key] = function (...args) {
      fn(...args);
      return orig.apply(this, args);
    };
  };
  const hud = rec.hud;
  wrap(G.hud, 'warn', (t, s) => hud.warn.push([t, s]));
  wrap(G.hud, 'message', (t, s) => hud.message.push([t, s]));
  wrap(G.hud, 'radio', (sp, t, s) => hud.radio.push([sp, t, s]));
  wrap(G.hud, 'setObjective', (t) => hud.objective.push(t));
  wrap(G.hud, 'setTally', (t) => hud.tally.push(t));
  wrap(G.hud, 'setReels', (d, t) => hud.reels.push(`${d}/${t}`));
  wrap(G.hud, 'prompt', (spec) => {
    hud.prompt = spec ? { text: spec.text, glyph: spec.glyph, progress: spec.progress } : null;
    if (spec) hud.prompts++;
  });
  wrap(G.menus, 'show', (screen, data) => rec.cards.push([screen, data ? JSON.parse(JSON.stringify(data)) : null]));
  wrap(G.menus, 'locationCard', (on, data) => rec.calls.locationCard.push([on, data ? data.place : null]));
  wrap(G.explosives, 'reset', () => rec.calls.explosivesReset++);
  wrap(G.enemies, 'setDifficulty', (t) => {
    const table = G.config.enemies.difficulty || {};
    rec.calls.setDifficulty.push(Object.keys(table).find((k) => table[k] === t) || '?');
  });
  wrap(G.enemies, 'setScale', (s) => rec.calls.setScale.push({ ...s }));
  wrap(G.atmos, 'setTime', (t) => rec.calls.setTime.push(t));
  wrap(G.weapon, 'addReserve', (n, cap) => rec.calls.addReserve.push([n, cap]));
  wrap(G.player, 'heal', (n) => rec.calls.heal.push(n));
  Object.assign(rec.calls, { paused: [], music: null, requestLock: 0, exitLock: 0, clearRadio: 0, markers: null, hudShown: null, stings: [] });
  wrap(G.audio, 'setPaused', (on) => rec.calls.paused.push(!!on));
  wrap(G.audio, 'setMusicIntensity', (x) => (rec.calls.music = x));
  wrap(G.audio, 'sting', (name) => rec.calls.stings.push(name));
  wrap(G.input, 'requestLock', () => rec.calls.requestLock++);
  wrap(G.input, 'exitLock', () => rec.calls.exitLock++);
  wrap(G.hud, 'clearRadio', () => rec.calls.clearRadio++);
  wrap(G.hud, 'show', (on) => (rec.calls.hudShown = !!on));
  wrap(G.hud, 'setMarkers', (list) => (rec.calls.markers = list.map((m) => `${m.kind}:${m.code}`)));
  // The last state each reel case and the truck were put in.
  rec.props = {};
  for (const o of G.level.objectives) wrap(o.prop, 'setState', (s) => (rec.props[o.id] = s));
  wrap(G.level.extraction && G.level.extraction.prop, 'setState', (s) => (rec.props.truck = s));

  window.__fx = {
    snap() {
      const g = G.game;
      return {
        state: g.state,
        mode: g.mode,
        difficulty: g.difficulty,
        run: { ...g.run },
        flow: { ...g.flow, queue: g.flow.queue.length, lastWave: g.flow.lastWave },
        holdout: { ...g.holdout },
        alive: G.enemies.aliveCount(),
        goons: G.enemies.countByType('goon'),
        buzzards: G.enemies.countByType('buzzard'),
        player: {
          x: G.player.pos.x, z: G.player.pos.z, health: G.player.health, alive: G.player.alive,
          enabled: G.player.enabled, invulnerable: G.player.invulnerable, regen: { ...G.player.regen },
        },
        reserve: G.weapon.reserve,
        post: { fade: G.render.post.fade, saturation: G.render.post.saturation },
        screen: G.menus.screen,
        fov: G.camera.fov,
        cam: G.camera.position.toArray().map((v) => Math.round(v * 100) / 100),
        props: { ...rec.props },
        errors: window.__errors.length,
      };
    },
    /** Puts the player `dist` metres from point (x, z), on side `angle`, facing it (or facing away). */
    standAt(x, z, dist = 1.5, angle = 0, away = false) {
      const px = x + Math.sin(angle) * dist;
      const pz = z + Math.cos(angle) * dist;
      const dx = x - px;
      const dz = z - pz;
      let yaw = Math.atan2(-dx, -dz);
      if (away) yaw += Math.PI;
      G.player.reset({ pos: new G.THREE.Vector3(px, G.physics.groundHeight(px, pz, 1.5), pz), yaw });
      G.player.invulnerable = !!window.__god;
    },
    /** Kills every living enemy through enemies.damage, as the player's gun would. */
    killAll() {
      let n = 0;
      for (const e of G.enemies.list) {
        if (!e.alive) continue;
        G.enemies.damage(e, 10000, { point: e.pos.clone(), dir: new G.THREE.Vector3(0, 0, -1), part: 'body', from: 'player', weapon: 'chopper' });
        n++;
      }
      return n;
    },
    since(i) {
      return rec.events.slice(i);
    },
  };
}

/** Wires a scenario: the recorder, a check() that prints and counts, and small helpers. */
async function setup(page, h) {
  await h.eval(install, FLOW_EVENTS);
  let failed = 0;
  let checks = 0;
  const check = (name, ok, detail = '') => {
    checks++;
    if (!ok) failed++;
    const d = typeof detail === 'string' ? detail : JSON.stringify(detail);
    console.log(`${ok ? 'ok  ' : 'FAIL'}  ${name}${d ? `  (${d.slice(0, 300)})` : ''}`);
    return ok;
  };
  const snap = () => h.eval(() => window.__fx.snap());
  const rec = () => h.eval(() => window.__flow);
  const tap = async (code) => {
    await h.key(code, true);
    await h.skip(1);
    await h.key(code, false);
    await h.skip(1);
  };
  /** Undrawn steps until `pred(snap)` holds or `max` steps pass; returns the last snap. */
  const until = async (pred, max, step = 5) => {
    let s = await snap();
    for (let i = 0; i < max && !pred(s); i += step) {
      await h.skip(step);
      s = await snap();
    }
    return s;
  };
  const finish = async () => {
    const errs = await h.errors();
    check('nothing was logged as an error', errs.length === 0, errs.slice(0, 3).join(' | '));
    console.log(`${checks - failed}/${checks} checks passed`);
    if (failed) throw new Error(`${failed} flow check(s) failed`);
  };
  return { check, snap, rec, tap, until, finish };
}

module.exports = { setup, FLOW_EVENTS };
