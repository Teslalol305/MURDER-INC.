// G.game — the flow controller (CONTRACT 6.13, rules from the reference notes 04 with DESIGN 2 and 3).
//
//   title → intro → playing ⇄ paused,  playing → dead | complete
//
// Story: a starting patrol that does not know Rule is there; hold Interact on a master reel to take it
// back; every reel queues a reinforcement wave that arrives alerted; after the third a finite pursuit
// runs while the player makes for the IPX truck. Hold the Block: growing waves with a breather and a
// resupply between them, a score and a local best.
//
// This file owns the state machine, the run reset, the interaction, the spawn queue and its pump, the
// radio queue, the music-intensity driver, the title camera and the screen fades. The rules that are
// pure arithmetic live in src/game/* (waves, spawn scoring, music, radio timing, card data) with unit
// tests in test/flow-*.test.js. Every number is in src/config/flow.js, every line in src/config/text.js.
//
// Beyond the contract (documented in CONTRACT 6.13 "as built"): game.flow and game.holdout are live
// read-only views for tests and tuning.

import * as THREE from 'three';
import { clamp01, damp, paramOn, smoothstep } from './core/util.js';
import { musicIntensity, waveIsOver } from './game/music.js';
import { introCopy } from './game/intro.js';
import { createRadio } from './game/radio.js';
import { compassSector, pickSpawn } from './game/spawn.js';
import { cardData } from './game/stats.js';
import { createTitleCamera } from './game/titlecam.js';
import { BUZZARD, holdoutWave, killScore, missionOrder, pursuitType } from './game/waves.js';

const TYPING = /^(BUTTON|A|INPUT|SELECT|TEXTAREA)$/;

export function createGame(G) {
  const { text, flow } = G.config;
  const rng = G.rng.fork('game');
  const camera = G.camera;
  const post = G.render.post;
  const quiet = paramOn(G.params, 'shot'); // screenshots: no look-mode toasts

  const run = { time: 0, reels: 0, total: 3, retries: 0, wave: 0, score: 0, kills: 0, shots: 0, hits: 0 };
  const queue = []; // pending arrivals: {type, at, pos, tries}
  const holdout = { active: false, breakLeft: 0, countdown: 0, cleared: 0, realertIn: 0 };
  // What the flow is doing right now, for tests and tuning. Read-only for everyone else.
  const view = { queue, clock: 0, maxAlive: 0, pursuitLeft: 0, pursuitTimer: 0, music: flow.music.calm, lastWave: null, grabbing: null, progress: 0 };

  const game = {
    state: 'title',
    mode: G.settings.get('mode'),
    difficulty: G.settings.get('difficulty'),
    run,
    flow: view,
    holdout,
    start,
    pause,
    resume,
    restart,
    retry,
    redeploy,
    toTitle,
    setDifficulty,
    debugGrab,
    update,
  };

  let stateTime = 0; // seconds in the current state
  let clock = 0; // seconds of this run with the simulation live (intro included); times every spawn and cooldown
  let diff = flow.difficulty[flow.defaultDifficulty];
  let maxAlive = diff.maxAlive;
  let introLength = 0;
  let fullIntro = false;
  let introCard = false;
  let introRadio = false;
  let cardShown = false;
  let everLocked = false;
  let startedFrame = -1; // two start requests in one frame (menu button + key) are one start
  let hintIn = 0; // seconds until the look-mode hint may show again
  let dragHinted = false;

  const secured = new Set(); // ids of the reels already back
  const lastUsed = new Map(); // spawn point → clock when it was last picked
  let grabTarget = null; // the reel whose progress bar is not empty
  let progress = 0;
  let promptOn = false;
  let refusedAt = -Infinity;
  let saidContact = false;
  let saidLow = false;
  let pursuitLeft = 0;
  let pursuitTimer = 0;
  let waveAge = Infinity; // seconds since a wave was queued
  let sinceAlert = Infinity;
  let sinceHit = Infinity;

  // Reused every frame: no garbage while the player stands at a reel or a wave pours in.
  const promptSpec = { text: '', glyph: '', code: '', progress: 0 };
  const progressEvent = { id: '', t: 0 };
  const musicState = { allDone: false, queued: 0, alive: 0, waveAge: Infinity, sinceAlert: Infinity, sinceHit: Infinity, nearest: Infinity };
  const eye = new THREE.Vector3();
  const probe = new THREE.Vector3();
  const sum = new THREE.Vector3();

  const titleCamera = createTitleCamera(G.level.cinematicPath, flow.titleCamera);

  const inRun = () => game.state === 'playing' || game.state === 'intro';
  const mission = () => game.mode === 'mission';
  const allSecured = () => mission() && run.total > 0 && run.reels >= run.total;

  /** Objective and truck props are optional talents of the level: a stub may not have them. */
  function setProp(thing, state, t) {
    const prop = thing && thing.prop;
    if (prop && typeof prop.setState === 'function') prop.setState(state, t);
  }

  // ---------------------------------------------------------------------------------------------
  // Radio: one speaker, lines in order (src/game/radio.js keeps the timing)
  // ---------------------------------------------------------------------------------------------

  const radio = createRadio({
    charsPerSec: flow.pacing.radioCharsPerSec,
    gap: flow.pacing.radioGap,
    onLine(words, secs) {
      G.hud.radio(text.radio.speaker, words, secs);
      G.events.emit('radio:line', { speaker: text.radio.speaker, text: words, secs });
    },
    onClear() {
      G.hud.clearRadio();
    },
  });

  function say(line, arg) {
    radio.say(typeof line.text === 'function' ? line.text(arg) : line.text, line.secs);
  }

  function hushRadio() {
    radio.clear();
    G.hud.clearRadio();
  }

  // ---------------------------------------------------------------------------------------------
  // State machine
  // ---------------------------------------------------------------------------------------------

  function setState(next, prev = game.state) {
    game.state = next;
    stateTime = 0;
    cardShown = false;
    const active = next === 'playing' || next === 'intro';
    G.input.setGameplay(active);
    G.hud.show(active);
    G.weapon.setVisible(active);
    // A dead player keeps simulating (the death camera); the title and the debrief own the camera.
    G.player.enabled = active || next === 'dead' || next === 'paused';
    G.audio.setPaused(next === 'paused');
    if (next === 'title' || next === 'paused') G.menus.show(next);
    else G.menus.show('none'); // the death and debrief cards come up later, from update()
    if (!active) showPrompt(null);
    G.events.emit('game:state', { state: next, prev });
  }

  /** How many may be alive at once: the difficulty's cap, plus the holdout wave's allowance. */
  function applyWaveScale() {
    if (game.mode === 'holdout' && run.wave > 0) {
      const w = holdoutWave(run.wave, flow.holdout);
      G.enemies.setScale(w.scale);
      maxAlive = diff.maxAlive + w.extraAlive;
    } else {
      G.enemies.setScale({ hp: 1, damage: 1, cooldown: 1 });
      maxAlive = diff.maxAlive;
    }
    view.maxAlive = maxAlive;
  }

  /**
   * Lays the chosen difficulty over the base tuning. Everything but hit points changes at once for
   * whoever is alive; wave sizes, the alive cap and the pursuit follow from the next spawn on.
   */
  function applyDifficulty() {
    if (!flow.difficulty[game.difficulty]) game.difficulty = flow.defaultDifficulty;
    diff = flow.difficulty[game.difficulty];
    G.enemies.setDifficulty(G.config.enemies.difficulty[game.difficulty]);
    applyWaveScale(); // holdout multipliers sit on top of the table, never compounding
    G.player.regen.delay = diff.regen.delay;
    G.player.regen.rate = diff.regen.rate;
  }

  function setDifficulty(name) {
    game.difficulty = flow.difficulty[name] ? name : flow.defaultDifficulty;
    applyDifficulty();
  }

  /** Day or night: the look, and the clock on the location card. */
  function applyTimeOfDay() {
    const time = G.settings.get('time') === 'night' ? 'night' : 'day';
    if (G.atmos && typeof G.atmos.setTime === 'function') G.atmos.setTime(time);
    text.location.place = text.location.byTime[time];
  }

  /** Puts every module back to the start of a run. `run.retries` is the caller's business. */
  function reset() {
    const story = mission();
    queue.length = 0;
    lastUsed.clear();
    secured.clear();
    clock = 0;
    grabTarget = null;
    progress = 0;
    refusedAt = -Infinity;
    saidContact = saidLow = false;
    pursuitLeft = 0;
    pursuitTimer = 0;
    waveAge = sinceAlert = sinceHit = Infinity;
    hintIn = 1.5; // the mouse capture gets a moment to arrive first
    holdout.active = false;
    holdout.breakLeft = flow.holdout.firstDelay;
    holdout.countdown = 0;
    holdout.cleared = 0;
    holdout.realertIn = 0;
    Object.assign(run, { time: 0, reels: 0, total: G.level.objectives.length, wave: 0, score: 0, kills: 0, shots: 0, hits: 0 });
    Object.assign(view, { clock: 0, pursuitLeft: 0, pursuitTimer: 0, lastWave: null, grabbing: null, progress: 0 });

    hushRadio();
    applyTimeOfDay();
    G.enemies.clear();
    applyDifficulty();
    G.fx.clear();
    G.combat.reset();
    G.weapon.reset();
    G.explosives.reset();
    G.player.reset(G.level.playerStart);
    G.hud.reset();
    promptOn = false;
    G.menus.locationCard(false);
    post.saturation = 1;
    post.flash = 0;

    for (const o of G.level.objectives) setProp(o, story ? 'live' : 'taken', 0);
    setProp(G.level.extraction, 'idle');

    if (story) {
      G.hud.setReels(0, run.total);
      spawnPatrol();
    } else {
      G.hud.setTally(text.objectives.tally.standby);
    }
    refreshObjective();
    G.events.emit('game:reset', { mode: game.mode });
  }

  function begin({ mode, skipIntro = false, quick = false } = {}) {
    if (flow.modes.includes(mode)) game.mode = mode;
    reset();
    G.input.requestLock();
    G.audio.setMusicIntensity(flow.music.calm);
    if (skipIntro) {
      post.fade = 0;
      setState('playing');
      return;
    }
    introLength = quick ? flow.timing.introQuick : flow.timing.intro;
    fullIntro = !quick;
    introCard = introRadio = false;
    post.fade = 1;
    setState('intro');
  }

  /** A fresh run: from the title button, Enter, the gamepad, or ?autostart. Without a mode, the saved one. */
  function start(opts = {}) {
    if (startedFrame === G.time.frame && inRun()) return;
    startedFrame = G.time.frame;
    run.retries = 0;
    begin({ ...opts, mode: flow.modes.includes(opts.mode) ? opts.mode : G.settings.get('mode') });
  }

  /** "Restart run" on the pause card: the same mode again, counted as a retry. */
  function restart() {
    run.retries++;
    begin({ quick: true });
  }

  /** "Run it back" on the death card. */
  function retry() {
    restart();
  }

  /** "Run it back" on the debrief: a new run with a clean sheet. */
  function redeploy() {
    run.retries = 0;
    begin({ quick: true });
  }

  function pause() {
    if (!inRun()) return;
    if (game.state === 'intro') finishIntro();
    setState('paused');
    G.input.exitLock();
  }

  function resume() {
    if (game.state !== 'paused') return;
    setState('playing');
    G.input.requestLock();
  }

  function toTitle() {
    queue.length = 0;
    // From the death card or a hurt debrief: alive and at full health again, so the low-health look
    // (desaturation, vignette, red rim) does not stay on the title.
    G.player.reset(G.level.playerStart);
    hushRadio();
    G.enemies.clear();
    G.fx.clear();
    G.menus.locationCard(false);
    applyTimeOfDay();
    for (const o of G.level.objectives) setProp(o, 'live', 0);
    setProp(G.level.extraction, 'idle');
    G.hud.setMarkers([]);
    post.saturation = 1;
    post.fade = 1;
    G.audio.setMusicIntensity(flow.music.calm);
    setState('title');
    G.input.exitLock(); // the title card needs the mouse
  }

  function finishIntro() {
    G.menus.locationCard(false);
    post.fade = 0;
    setState('playing');
  }

  // ---------------------------------------------------------------------------------------------
  // HUD lines
  // ---------------------------------------------------------------------------------------------

  function refreshObjective() {
    if (mission()) {
      G.hud.setObjective(text.objectives.mission[Math.min(run.reels, text.objectives.mission.length - 1)]);
      const markers = [];
      for (const o of G.level.objectives) {
        if (!secured.has(o.id)) markers.push({ id: o.id, code: o.code, label: o.label, pos: o.pos, kind: 'reel' });
      }
      if (allSecured()) {
        const ex = G.level.extraction;
        markers.push({ id: 'extraction', code: ex.code, label: ex.label, pos: ex.pos, kind: 'exit' });
      }
      G.hud.setMarkers(markers);
    } else {
      const h = text.objectives.holdout;
      G.hud.setObjective(holdout.active ? h.hold : run.wave === 0 ? h.inbound : h.breather);
      G.hud.setMarkers([]);
      refreshTally();
    }
  }

  function refreshTally() {
    const t = text.objectives.tally;
    G.hud.setTally(run.wave > 0 ? t.wave(run.wave, run.score) : t.standby);
  }

  /** The interaction prompt: null hides it. The HUD is only told when something changes or is showing. */
  function showPrompt(spec) {
    if (!spec && !promptOn) return;
    promptOn = !!spec;
    G.hud.prompt(spec);
  }

  /** Desktop without the mouse captured: say how looking works, now and then. */
  function updateLookHint(dt) {
    const input = G.input;
    if (quiet || input.touch || input.device !== 'kbm' || input.locked) {
      hintIn = Math.min(hintIn, 1);
      return;
    }
    hintIn -= dt;
    if (hintIn > 0) return;
    hintIn = flow.timing.lookHintEvery;
    if (input.mode === 'drag') {
      if (dragHinted) return; // the fallback explains itself once
      dragHinted = true;
    }
    const words = input.hint();
    if (words) G.hud.message(words, flow.timing.lookHintSecs);
  }

  // ---------------------------------------------------------------------------------------------
  // Spawning
  // ---------------------------------------------------------------------------------------------

  const spawnQuery = {
    x: 0,
    z: 0,
    minDistance: 0,
    strict: false,
    hidden(point) {
      probe.copy(point.pos);
      if (point.type === 'ground') probe.y += flow.spawn.probeHeight;
      return !G.physics.lineOfSight(eye, probe);
    },
    usedAgo(point) {
      const at = lastUsed.get(point);
      return at === undefined ? Infinity : clock - at;
    },
    random: () => rng.next(),
  };

  /**
   * Where one enemy of `type` should appear, written to `out`: the best authored point for the player's
   * position right now, nudged a little so two arrivals never stack. False when the level has nowhere.
   */
  function choosePosition(type, minDistance, strict, out) {
    const S = flow.spawn;
    const air = type === BUZZARD;
    const p = G.player.pos;
    eye.set(p.x, p.y + S.eyeHeight, p.z);
    spawnQuery.x = p.x;
    spawnQuery.z = p.z;
    spawnQuery.minDistance = minDistance;
    spawnQuery.strict = strict;
    const point = pickSpawn(G.level.enemySpawns, air ? 'air' : 'ground', spawnQuery, S.score);

    if (point) {
      lastUsed.set(point, clock);
      out.copy(point.pos);
    } else {
      // A level without authored points: somewhere on a ring around the player, inside the block.
      const a = rng.range(0, Math.PI * 2);
      const b = G.level.bounds;
      out.set(
        Math.min(b.maxX - 2, Math.max(b.minX + 2, p.x + Math.cos(a) * S.fallbackRing)),
        0,
        Math.min(b.maxZ - 2, Math.max(b.minZ + 2, p.z + Math.sin(a) * S.fallbackRing)),
      );
      if (!air) {
        const near = G.physics.nav.nearestWalkable(out.x, out.z);
        if (!near) return false;
        out.set(near.x, G.physics.groundHeight(near.x, near.z, 1), near.z);
      }
    }

    const jx = rng.range(-S.jitter, S.jitter);
    const jz = rng.range(-S.jitter, S.jitter);
    if (air) {
      out.x += jx;
      out.z += jz;
      if (out.y < S.airMinHeight) out.y = rng.range(S.airLift[0], S.airLift[1]);
    } else if (G.physics.nav.isWalkable(out.x + jx, out.z + jz)) {
      // Same floor as the authored point: a jitter must not climb onto a car or drop off a deck.
      const y = G.physics.groundHeight(out.x + jx, out.z + jz, out.y + 0.6);
      if (Math.abs(y - out.y) < 0.3) out.set(out.x + jx, y, out.z + jz);
    }
    return true;
  }

  /** The starting patrol: unaware, well away from the start, out of its sight where the block allows. */
  function spawnPatrol() {
    const at = new THREE.Vector3();
    for (const type of [BUZZARD, 'goon']) {
      for (let i = 0; i < diff.patrol[type]; i++) {
        if (choosePosition(type, flow.spawn.patrolMinDistance, true, at)) G.enemies.spawn(type, at, { alerted: false });
      }
    }
  }

  /**
   * Queues `order` (enemy types, first to arrive first), each with its own spawn point picked now.
   * @returns {string | null} the compass direction the wave comes from, as seen from the player
   */
  function queueWave(order, firstDelay, stagger) {
    const p = G.player.pos;
    sum.set(0, 0, 0);
    let queued = 0;
    for (let i = 0; i < order.length; i++) {
      const pos = new THREE.Vector3();
      if (!choosePosition(order[i], flow.spawn.far, false, pos)) continue;
      sum.x += pos.x - p.x;
      sum.z += pos.z - p.z;
      queue.push({ type: order[i], at: clock + firstDelay + i * stagger, pos, tries: 0 });
      queued++;
    }
    if (queued === 0) return null;
    waveAge = 0;
    const from = text.compass[compassSector(sum.x, sum.z)];
    view.lastWave = { order: order.slice(), from, at: clock };
    return from;
  }

  /**
   * At most one arrival per frame. A due arrival waits while the alive cap is reached, and is retried a
   * few times when the pool has no free body before it is given up.
   */
  function pumpQueue() {
    const S = flow.spawn;
    let index = -1;
    for (let i = 0; i < queue.length; i++) {
      if (queue[i].at <= clock) {
        index = i;
        break;
      }
    }
    if (index < 0) return;
    const next = queue[index];
    if (G.enemies.aliveCount() >= maxAlive) {
      next.at = clock + S.capRetry;
      return;
    }
    // The player has walked up to a ground point since it was picked: come in somewhere else.
    const p = G.player.pos;
    if (next.type !== BUZZARD && Math.hypot(next.pos.x - p.x, next.pos.z - p.z) < S.tooClose) {
      choosePosition(next.type, S.far, false, next.pos);
    }
    if (G.enemies.spawn(next.type, next.pos, { alerted: true, target: p })) {
      queue.splice(index, 1);
      G.enemies.alert(p, S.alertRadius);
    } else if (++next.tries >= S.poolTries) {
      queue.splice(index, 1);
    } else {
      next.at = clock + S.poolRetry;
    }
  }

  // ---------------------------------------------------------------------------------------------
  // Story mode
  // ---------------------------------------------------------------------------------------------

  /** The nearest reel still out there that the player can reach and is facing. */
  function reelInReach() {
    const I = flow.interact;
    const p = G.player;
    const fx = p.forward.x;
    const fz = p.forward.z;
    const flat = Math.hypot(fx, fz) || 1;
    let best = null;
    let bestD = Infinity;
    const list = G.level.objectives;
    for (let i = 0; i < list.length; i++) {
      const o = list[i];
      if (secured.has(o.id)) continue;
      const dx = o.pos.x - p.pos.x;
      const dz = o.pos.z - p.pos.z;
      const d = Math.hypot(dx, dz);
      if (d > I.range || d >= bestD || Math.abs(o.pos.y - p.pos.y) > I.vertical) continue;
      if (d > I.freeRange && (dx * fx + dz * fz) / (d * flat) < I.facingDot) continue;
      best = o;
      bestD = d;
    }
    return best;
  }

  function emitProgress(id, t) {
    progressEvent.id = id;
    progressEvent.t = t;
    G.events.emit('objective:progress', progressEvent);
  }

  /**
   * Hold Interact on a reel in reach to fill its bar. Letting go, looking away, stepping out or dying
   * drains it at `decay` per second: a short interruption costs little. The player is never held in place.
   */
  function updateInteraction(dt) {
    const I = flow.interact;
    const target = G.player.alive ? reelInReach() : null;
    const holding = !!target && G.input.down('interact');

    if (holding) {
      if (grabTarget !== target) {
        if (grabTarget) {
          setProp(grabTarget, 'live', 0);
          emitProgress(grabTarget.id, 0);
        }
        grabTarget = target;
        progress = 0;
      }
      progress = Math.min(1, progress + dt / I.hold);
      setProp(target, 'grabbing', progress);
      emitProgress(target.id, progress);
    } else if (grabTarget) {
      progress = Math.max(0, progress - I.decay * dt);
      setProp(grabTarget, 'live', progress);
      emitProgress(grabTarget.id, progress);
      if (progress === 0) grabTarget = null;
    }
    view.grabbing = grabTarget ? grabTarget.id : null;
    view.progress = progress;

    if (target) {
      const glyph = G.input.glyph('interact');
      if (promptSpec.glyph !== glyph || promptSpec.code !== target.code) {
        promptSpec.glyph = glyph;
        promptSpec.code = target.code;
        promptSpec.text = text.prompts.grab(glyph, target.code);
      }
      promptSpec.progress = target === grabTarget ? clamp01(progress) : 0;
      showPrompt(promptSpec);
    } else {
      showPrompt(null);
    }

    if (holding && progress >= 1) secure(target);
  }

  function secure(o) {
    secured.add(o.id);
    run.reels = secured.size;
    setProp(o, 'taken', 1);
    if (grabTarget === o) grabTarget = null;
    progress = 0;
    view.grabbing = null;
    view.progress = 0;
    showPrompt(null);
    G.hud.setReels(run.reels, run.total);
    G.player.addShake(flow.interact.shake);
    refreshObjective();
    G.events.emit('objective:done', { id: o.id, index: run.reels, total: run.total });

    const all = run.reels >= run.total;
    const wave = diff.waves[Math.min(run.reels, diff.waves.length) - 1];
    const from = queueWave(missionOrder(wave.buzzard, wave.goon), flow.spawn.firstDelay, flow.spawn.stagger);
    if (from) G.hud.warn(text.banners.contact(from), flow.spawn.bannerSecs);
    const lines = text.radio.reel;
    say(lines[all ? lines.length - 1 : Math.min(run.reels, lines.length - 1) - 1]);

    G.audio.sting(all ? 'all' : 'reel');
    if (all) {
      pursuitLeft = diff.pursuitBudget;
      pursuitTimer = flow.pursuit.firstDelay;
      G.events.emit('objective:all', {});
    }
  }

  function debugGrab() {
    if (!mission() || !inRun()) return;
    const next = G.level.objectives.find((o) => !secured.has(o.id));
    if (next) secure(next);
  }

  /** After the last reel: a finite trickle of extra Vultures, and everyone keeps being pointed at Rule. */
  function updatePursuit(dt) {
    const P = flow.pursuit;
    pursuitTimer -= dt;
    if (pursuitTimer <= 0) {
      if (pursuitLeft > 0 && queue.length === 0 && G.enemies.aliveCount() < P.minAlive) {
        pursuitLeft--;
        queueWave([pursuitType(rng.next(), P.buzzardShare)], P.spawnDelay, 0);
        pursuitTimer = diff.pursuitEvery;
      } else {
        pursuitTimer = P.realertEvery;
        G.enemies.alert(G.player.pos, P.realertRadius);
      }
    }
    view.pursuitLeft = pursuitLeft;
    view.pursuitTimer = pursuitTimer;
  }

  function updateExtraction() {
    const E = flow.extraction;
    const ex = G.level.extraction;
    const p = G.player.pos;
    if (Math.hypot(ex.pos.x - p.x, ex.pos.z - p.z) > ex.radius || Math.abs(ex.pos.y - p.y) > E.vertical) return;
    if (allSecured()) {
      if (G.player.alive) complete();
    } else if (clock - refusedAt > E.refuseEvery) {
      refusedAt = clock;
      G.hud.message(text.prompts.refuse, E.refuseSecs);
    }
  }

  function complete() {
    syncStats();
    G.player.invulnerable = true;
    setProp(G.level.extraction, 'open');
    G.events.emit('extraction:reached', {});
    G.audio.sting('complete');
    setState('complete'); // player disabled, HUD hidden
    hushRadio();
    say(text.radio.done);
    G.input.exitLock(); // the debrief card needs the mouse back
  }

  // ---------------------------------------------------------------------------------------------
  // Hold the Block
  // ---------------------------------------------------------------------------------------------

  function startWave() {
    const H = flow.holdout;
    const n = ++run.wave;
    holdout.active = true;
    holdout.realertIn = H.realertEvery;
    applyDifficulty(); // base table first, then this wave's multipliers and alive allowance
    const wave = holdoutWave(n, H);
    const from = queueWave(wave.order, H.firstSpawn, wave.stagger);
    if (from) G.hud.warn(text.banners.wave(n, from), H.bannerSecs);
    refreshObjective();
    G.events.emit('holdout:wave', { wave: n, count: wave.total });
  }

  function clearWave() {
    const H = flow.holdout;
    const n = run.wave;
    holdout.active = false;
    holdout.cleared = n;
    holdout.breakLeft = H.breather;
    holdout.countdown = H.countdownFrom;
    run.score += H.score.waveClear(n);
    G.weapon.addReserve(H.resupply.reserve, H.resupply.reserveCap);
    G.player.heal(H.resupply.heal);
    if (n % H.resupply.explosivesEvery === 0) G.explosives.reset();
    say(text.radio.waveClear, n);
    refreshObjective();
    G.events.emit('objective:done', { id: 'wave', index: n, total: n });
    G.audio.sting('reel');
  }

  function updateHoldout(dt) {
    const H = flow.holdout;
    if (holdout.active) {
      if (queue.length > 0) return;
      if (G.enemies.aliveCount() === 0) {
        clearWave();
        return;
      }
      // Everyone is out: whoever lost the trail is sent after the player again.
      holdout.realertIn -= dt;
      if (holdout.realertIn <= 0) {
        holdout.realertIn = H.realertEvery;
        G.enemies.alert(G.player.pos, H.realertRadius);
      }
      return;
    }
    holdout.breakLeft -= dt;
    // "Wave N in 3 … 2 … 1", one message a second, not before the first wave.
    if (run.wave > 0 && holdout.countdown > 0 && holdout.breakLeft <= holdout.countdown) {
      G.hud.message(text.banners.countdown(run.wave + 1, holdout.countdown), flow.pacing.countdownSecs);
      holdout.countdown--;
    }
    if (holdout.breakLeft <= 0) startWave();
  }

  // ---------------------------------------------------------------------------------------------
  // Cards
  // ---------------------------------------------------------------------------------------------

  function syncStats() {
    const stats = G.combat.stats;
    run.kills = stats.kills;
    run.shots = stats.shots;
    run.hits = stats.hits;
  }

  function showCard(screen) {
    syncStats();
    run.score = Math.round(run.score);
    const info = { mode: game.mode, difficulty: game.difficulty, wavesCleared: holdout.cleared, headshots: G.combat.stats.headshots, best: 0, newBest: false };
    if (game.mode === 'holdout') {
      info.newBest = G.settings.setBest(run.score);
      info.best = G.settings.best();
    }
    G.menus.show(screen, cardData(run, info, flow, text.ratings));
    G.audio.setMusicIntensity(flow.music.calm);
  }

  /** Eases the screen toward a [target, rate] pair from config/flow.js `post`. */
  function easePost(look, dt) {
    post.saturation = damp(post.saturation, look.saturation[0], look.saturation[1], dt);
    post.fade = damp(post.fade, look.fade[0], look.fade[1], dt);
  }

  // ---------------------------------------------------------------------------------------------
  // Music
  // ---------------------------------------------------------------------------------------------

  function updateMusic(dt) {
    const M = flow.music;
    waveAge += dt;
    sinceAlert += dt;
    sinceHit += dt;
    const s = musicState;
    s.allDone = allSecured();
    s.queued = queue.length;
    s.alive = G.enemies.aliveCount();
    s.waveAge = waveAge;
    s.sinceAlert = sinceAlert;
    s.sinceHit = sinceHit;
    s.nearest = G.enemies.nearestDistance();
    if (waveIsOver(s, M)) s.waveAge = waveAge = Infinity;
    const level = musicIntensity(s, M);
    view.music = level;
    G.audio.setMusicIntensity(level);
  }

  // ---------------------------------------------------------------------------------------------
  // Update
  // ---------------------------------------------------------------------------------------------

  function update(dt) {
    stateTime += dt;
    const { state } = game;

    if (state === 'title') {
      post.fade = titleCamera.apply(stateTime, camera);
      post.saturation = 1;
      G.audio.setMusicIntensity(flow.music.calm);
      // Gamepad Start begins a run, like the button (reading menuNav does not consume it).
      const nav = G.input.menuNav();
      if (nav && nav.start && !G.menus.panelOpen) titleStart();
      return false;
    }

    if (state === 'paused') {
      // The pause key closes an open panel first (the menus do that); otherwise it resumes.
      if (stateTime > flow.timing.pauseDebounce && G.input.pressed('pause') && !G.menus.panelOpen) resume();
      return false;
    }

    if (state === 'dead') {
      easePost(flow.post.dead, dt);
      if (!cardShown && stateTime >= flow.timing.deathCard) {
        cardShown = true;
        showCard('dead');
      }
      return true;
    }

    if (state === 'complete') {
      easePost(flow.post.complete, dt);
      radio.update(dt);
      if (!cardShown && stateTime >= flow.timing.debriefCard) {
        cardShown = true;
        showCard('complete');
      }
      return true;
    }

    // intro and playing: the player has control in both
    if (G.input.pressed('pause')) {
      pause();
      return false;
    }
    clock += dt;
    view.clock = clock;

    if (state === 'intro') {
      const T = flow.timing;
      post.fade = 1 - smoothstep(T.introFade[0], Math.min(introLength, T.introFade[1]), stateTime);
      if (fullIntro && !introCard && stateTime >= T.locationCardAt) {
        introCard = true;
        G.menus.locationCard(true, introCopy(mission(), text).card); // Hold the Block: no reels on its card
      }
      if (fullIntro && !introRadio && stateTime >= T.introRadioAt) {
        introRadio = true;
        const { line } = introCopy(mission(), text);
        if (line) say(line);
      }
      if (stateTime >= introLength) finishIntro();
    } else {
      run.time += dt;
    }

    syncStats();
    pumpQueue();
    if (mission()) {
      updateInteraction(dt);
      if (allSecured()) updatePursuit(dt);
      updateExtraction();
      if (game.state === 'complete') return true; // the truck: nothing more to drive this frame
    } else {
      updateHoldout(dt);
    }

    if (!saidLow && G.player.alive && G.player.health < G.config.player.health.lowWarning) {
      saidLow = true;
      say(text.radio.lowHealth);
    }

    radio.update(dt);
    updateMusic(dt);
    updateLookHint(dt);
    return true;
  }

  // ---------------------------------------------------------------------------------------------
  // Events
  // ---------------------------------------------------------------------------------------------

  G.events.on('player:dead', () => {
    if (!inRun() && game.state !== 'paused') return;
    syncStats();
    if (grabTarget) {
      setProp(grabTarget, 'live', 0);
      emitProgress(grabTarget.id, 0);
      grabTarget = null;
      progress = 0;
    }
    G.menus.locationCard(false);
    G.audio.sting('dead');
    setState('dead'); // input released, HUD hidden
    hushRadio();
    G.input.exitLock();
  });

  G.events.on('player:hit', () => {
    sinceHit = 0;
  });

  G.events.on('enemy:alert', () => {
    sinceAlert = 0;
    if (saidContact || game.state !== 'playing') return;
    saidContact = true;
    say(text.radio.contact);
  });

  G.events.on('enemy:killed', (e) => {
    if (game.mode !== 'holdout' || game.state !== 'playing') return;
    run.score += killScore(e.type, run.wave, flow.holdout.score);
    refreshTally();
  });

  G.events.on('settings:change', ({ key, value }) => {
    if (key === 'difficulty') setDifficulty(value);
    else if (key === 'mode' && game.state === 'title') game.mode = value;
    else if (key === 'time' && game.state === 'title') applyTimeOfDay(); // mid-run it waits for the next reset
  });

  // Losing the mouse or the tab mid-run pauses the game.
  G.events.on('input:lock', (e) => {
    if (e.locked) everLocked = true;
    else if (everLocked && e.mode === 'lock') pause();
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) pause();
  });
  // The window losing focus (a click on the chat beside the Artifact, another app) pauses too: in drag
  // mode and on touch no lock is ever lost to say so. pause() ignores anything but a live run.
  window.addEventListener('blur', () => pause());
  // A lost WebGL context leaves a black canvas: nobody plays blind. A restore leaves the pause card up.
  G.events.on('render:lost', () => pause());

  /** The title's primary action from a key or the gamepad: the same path as the menu button. */
  function titleStart() {
    G.audio.unlock();
    start({ mode: G.settings.get('mode') });
  }

  // Enter starts from the title even when focus has wandered off the button.
  document.addEventListener('keydown', (e) => {
    if (game.state !== 'title' || e.repeat || (e.code !== 'Enter' && e.code !== 'NumpadEnter')) return;
    if (G.menus.panelOpen) return;
    const focus = document.activeElement;
    if (focus && TYPING.test(focus.tagName || '')) return; // the browser clicks a focused button itself
    titleStart();
  });

  // ---------------------------------------------------------------------------------------------
  // Start on the title screen
  // ---------------------------------------------------------------------------------------------

  text.location.place = text.location.byTime[G.settings.get('time') === 'night' ? 'night' : 'day'];
  applyDifficulty();
  post.fade = 1;
  setState('title', null);

  return game;
}
