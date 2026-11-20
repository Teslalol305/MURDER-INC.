// Stub game flow (CONTRACT 6.13): a small but real run, so a stubbed build is a playable vertical slice.
//
//   title → intro → playing ⇄ paused,  playing → dead | complete
//
// Story: a starting patrol, hold Interact on a master reel to grab it, each reel brings a reinforcement
// wave, after the third a short pursuit while the player runs for the IPX truck. Hold the Block: growing
// waves with a breather and a resupply between them, score and local best.
// Deliberately simple next to the real flow: one run with no levels and no cutscenes (the three reels
// in any order, then the truck), no radio queue (a new line replaces the old one), a plain camera glide
// behind the title, and progress on a reel is lost as soon as the player steps away.
//
// Conventions for whoever replaces this:
//   - objective:done carries index = how many reels are now secured (1 … total); for a cleared holdout
//     wave it is {id: 'wave', index: wave, total: wave}.
//   - card data handed to menus.show(): see src/stubs/menus.js.

import * as THREE from 'three';
import { clamp01, damp, lerp, smoothstep } from '../core/util.js';

export function createGame(G) {
  const { text, flow } = G.config;
  const rng = G.rng.fork('game');
  const camera = G.camera;
  const post = G.render.post;

  const run = { time: 0, reels: 0, total: 3, retries: 0, wave: 0, score: 0, kills: 0, shots: 0, hits: 0, level: 0, levels: 1 };
  // The flow table is written for the story's levels: the stub takes its patrol from the first and a
  // wave from each one that has one.
  const patrolOf = (d) => (d.levels && d.levels[0] && d.levels[0].patrol) || d.patrol || { buzzard: 1, goon: 2 };
  const wavesOf = (d) => (d.levels ? d.levels.map((l) => l.wave).filter(Boolean) : d.waves || [{ buzzard: 1, goon: 2 }]);
  const game = {
    state: 'title',
    mode: G.settings.get('mode'),
    difficulty: G.settings.get('difficulty'),
    run,
    start,
    pause,
    resume,
    restart,
    retry,
    redeploy,
    toTitle,
    skipCutscene() {}, // the stub has no cutscenes
    setDifficulty,
    debugGrab,
    update,
  };

  let stateTime = 0; // seconds in the current state
  let clock = 0; // seconds since the run began (intro included); times spawns and cooldowns
  let diff = flow.difficulty[flow.defaultDifficulty];
  let maxAlive = diff.maxAlive;
  let introLength = 0;
  let fullIntro = false;
  let introCard = false;
  let introRadio = false;
  let cardShown = false;
  let everLocked = false;

  const secured = new Set(); // ids of the reels already grabbed
  const queue = []; // pending spawns, soonest first: {type, at, pos}
  const lastUsed = new Map(); // spawn point → clock when it was last picked
  let current = null; // the reel in reach
  let progress = 0;
  let refusedAt = -Infinity;
  let saidContact = false;
  let saidLow = false;
  let pursuitLeft = 0;
  let pursuitTimer = 0;
  const holdout = { active: false, breakLeft: 0, countdown: 0 };

  // Reused per frame: no garbage while the player stands at a reel.
  const promptSpec = { text: '', glyph: '', progress: 0 };
  const progressEvent = { id: '', t: 0 };
  const eye = new THREE.Vector3();
  const lookAt = new THREE.Vector3();
  const sum = new THREE.Vector3();
  let titleLoop = 26;

  const inRun = () => game.state === 'playing' || game.state === 'intro';

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
    else if (active) G.menus.show('none');
    G.events.emit('game:state', { state: next, prev });
  }

  function applyDifficulty() {
    if (!flow.difficulty[game.difficulty]) game.difficulty = flow.defaultDifficulty;
    diff = flow.difficulty[game.difficulty];
    maxAlive = diff.maxAlive;
    G.enemies.setDifficulty(G.config.enemies.difficulty[game.difficulty]);
    G.enemies.setScale({ hp: 1, damage: 1, cooldown: 1 });
    G.player.regen.delay = diff.regen.delay;
    G.player.regen.rate = diff.regen.rate;
  }

  function setDifficulty(name) {
    if (!flow.difficulty[name]) return;
    game.difficulty = name;
    applyDifficulty();
  }

  /** Puts every module back to the start of a run. `run.retries` is the caller's business. */
  function reset() {
    const mission = game.mode === 'mission';
    queue.length = 0;
    lastUsed.clear();
    secured.clear();
    clock = 0;
    current = null;
    progress = 0;
    refusedAt = -Infinity;
    saidContact = saidLow = false;
    pursuitLeft = 0;
    holdout.active = false;
    holdout.breakLeft = flow.holdout.firstDelay;
    holdout.countdown = 0;
    Object.assign(run, { time: 0, reels: 0, total: G.level.objectives.length, wave: 0, score: 0, kills: 0, shots: 0, hits: 0 });

    G.enemies.clear();
    applyDifficulty();
    G.fx.clear();
    G.combat.reset();
    G.weapon.reset();
    G.explosives.reset();
    G.player.reset(G.level.playerStart);
    G.hud.reset();
    G.menus.locationCard(false);
    post.saturation = 1;
    post.flash = 0;

    for (const o of G.level.objectives) if (o.prop.setState) o.prop.setState(mission ? 'live' : 'taken', 0);
    if (G.level.extraction.prop.setState) G.level.extraction.prop.setState('idle');

    if (mission) {
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

  function start(opts) {
    run.retries = 0;
    begin(opts);
  }

  function restart() {
    run.retries++;
    begin({ quick: true });
  }

  function retry() {
    restart();
  }

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
    G.enemies.clear();
    G.hud.clearRadio();
    G.menus.locationCard(false);
    setState('title');
    G.input.exitLock(); // the title card needs the mouse
  }

  function finishIntro() {
    G.menus.locationCard(false);
    post.fade = 0;
    setState('playing');
  }

  // ---------------------------------------------------------------------------------------------
  // Text
  // ---------------------------------------------------------------------------------------------

  function radio(line, arg) {
    const words = typeof line.text === 'function' ? line.text(arg) : line.text;
    G.hud.radio(text.radio.speaker, words, line.secs);
    G.events.emit('radio:line', { speaker: text.radio.speaker, text: words, secs: line.secs });
  }

  function refreshObjective() {
    if (game.mode === 'mission') {
      G.hud.setObjective(text.objectives.mission[run.reels]);
      const markers = G.level.objectives
        .filter((o) => !secured.has(o.id))
        .map((o) => ({ id: o.id, code: o.code, label: o.label, pos: o.pos, kind: 'reel' }));
      if (run.reels >= run.total) {
        const ex = G.level.extraction;
        markers.push({ id: 'extraction', code: ex.code, label: ex.label, pos: ex.pos, kind: 'exit' });
      }
      G.hud.setMarkers(markers);
    } else {
      const h = text.objectives.holdout;
      G.hud.setObjective(holdout.active ? h.hold : run.wave === 0 ? h.inbound : h.breather);
      G.hud.setMarkers([]);
      if (run.wave > 0) G.hud.setTally(text.objectives.tally.wave(run.wave, run.score));
    }
  }

  /** 8-way compass name of the direction (dx, dz) as seen from above; north is −Z. */
  function compass(dx, dz) {
    const sector = Math.round(Math.atan2(dx, -dz) / (Math.PI / 4));
    return text.compass[(sector + 8) % 8];
  }

  // ---------------------------------------------------------------------------------------------
  // Spawning
  // ---------------------------------------------------------------------------------------------

  /** Best authored point for one spawn: far from the player, out of sight, not just used. */
  function pickSpawn(type, minDistance) {
    const S = flow.spawn.score;
    const wanted = type === 'buzzard' ? 'air' : 'ground';
    const p = G.player.pos;
    eye.set(p.x, p.y + 1.6, p.z);
    let best = null;
    let bestScore = -Infinity;
    for (const point of G.level.enemySpawns) {
      if (point.type !== wanted) continue;
      const d = Math.hypot(point.pos.x - p.x, point.pos.z - p.z);
      let score = rng.range(0, S.random);
      score += d >= minDistance ? S.far + S.farExtra * clamp01((d - minDistance) / S.farExtraOver) : -(minDistance - d) / S.nearDivisor;
      lookAt.copy(point.pos);
      if (wanted === 'ground') lookAt.y += 1;
      if (!G.physics.lineOfSight(eye, lookAt)) score += S.hidden;
      if (clock - (lastUsed.get(point) ?? -Infinity) < S.recentSecs) score += S.recent;
      if (score > bestScore) {
        bestScore = score;
        best = point;
      }
    }
    if (best) lastUsed.set(best, clock);
    return best;
  }

  function spawnPatrol() {
    for (const type of ['buzzard', 'goon']) {
      for (let i = 0; i < patrolOf(diff)[type]; i++) {
        const point = pickSpawn(type, flow.spawn.patrolMinDistance);
        if (point) G.enemies.spawn(type, point.pos, { alerted: false });
      }
    }
  }

  /** Queues `list` (enemy types in arrival order) and returns the compass direction they come from. */
  function queueWave(list, firstDelay, stagger) {
    const p = G.player.pos;
    sum.set(0, 0, 0);
    list.forEach((type, i) => {
      const point = pickSpawn(type, flow.spawn.far);
      if (!point) return;
      sum.x += point.pos.x - p.x;
      sum.z += point.pos.z - p.z;
      queue.push({ type, at: clock + firstDelay + i * stagger, pos: point.pos });
    });
    return compass(sum.x, sum.z);
  }

  /** `goons` on foot with `buzzards` slotted in at every other position. */
  function mixedWave(buzzards, goons) {
    const list = [];
    while (buzzards > 0 || goons > 0) {
      if (goons > 0) {
        list.push('goon');
        goons--;
      }
      if (buzzards > 0) {
        list.push('buzzard');
        buzzards--;
      }
    }
    return list;
  }

  /** At most one arrival per frame, held back while the alive cap is reached. */
  function pumpQueue() {
    const next = queue[0];
    if (!next || next.at > clock) return;
    if (G.enemies.aliveCount() >= maxAlive) {
      next.at = clock + flow.spawn.capRetry;
      return;
    }
    queue.shift();
    if (G.enemies.spawn(next.type, next.pos, { alerted: true, target: G.player.pos })) {
      G.enemies.alert(G.player.pos, flow.spawn.alertRadius);
    }
  }

  // ---------------------------------------------------------------------------------------------
  // Story mode
  // ---------------------------------------------------------------------------------------------

  /** The nearest reel still out there that the player can reach and is facing. */
  function reelInReach() {
    const I = flow.interact;
    const p = G.player;
    const flat = Math.hypot(p.forward.x, p.forward.z) || 1;
    let best = null;
    let bestD = Infinity;
    for (const o of G.level.objectives) {
      if (secured.has(o.id)) continue;
      const dx = o.pos.x - p.pos.x;
      const dz = o.pos.z - p.pos.z;
      const d = Math.hypot(dx, dz);
      if (d > I.range || d >= bestD || Math.abs(o.pos.y - p.pos.y) > I.vertical) continue;
      if (d > I.freeRange && (dx * p.forward.x + dz * p.forward.z) / (d * flat) < I.facingDot) continue;
      best = o;
      bestD = d;
    }
    return best;
  }

  function updateInteraction(dt) {
    const I = flow.interact;
    const target = G.player.alive ? reelInReach() : null;
    if (target !== current) {
      if (current && current.prop.setState) current.prop.setState('live', 0);
      current = target;
      progress = 0;
      if (target) promptSpec.text = '';
    }
    if (!target) {
      G.hud.prompt(null);
      return;
    }
    const holding = G.input.down('interact');
    progress = holding ? Math.min(1, progress + dt / I.hold) : Math.max(0, progress - I.decay * dt);
    if (target.prop.setState) target.prop.setState(holding ? 'grabbing' : 'live', progress);

    const glyph = G.input.glyph('interact');
    if (promptSpec.glyph !== glyph || !promptSpec.text) {
      promptSpec.glyph = glyph;
      promptSpec.text = text.prompts.grab(glyph, target.code);
    }
    promptSpec.progress = progress;
    G.hud.prompt(promptSpec);
    if (holding) {
      progressEvent.id = target.id;
      progressEvent.t = progress;
      G.events.emit('objective:progress', progressEvent);
    }
    if (progress >= 1) secure(target);
  }

  function secure(o) {
    secured.add(o.id);
    run.reels = secured.size;
    if (o.prop.setState) o.prop.setState('taken', 1);
    current = null;
    progress = 0;
    G.hud.prompt(null);
    G.hud.setReels(run.reels, run.total);
    G.player.addShake(flow.interact.shake);
    refreshObjective();
    G.events.emit('objective:done', { id: o.id, index: run.reels, total: run.total });

    const waves = wavesOf(diff);
    const wave = waves[Math.min(run.reels, waves.length) - 1];
    const from = queueWave(mixedWave(wave.buzzard, wave.goon), flow.spawn.firstDelay, flow.spawn.stagger);
    G.hud.warn(text.banners.contact(from), flow.spawn.bannerSecs);
    radio(text.radio.reel[Math.min(run.reels, text.radio.reel.length) - 1]);

    const all = run.reels >= run.total;
    G.audio.sting(all ? 'all' : 'reel');
    if (all) {
      pursuitLeft = diff.pursuitBudget;
      pursuitTimer = flow.pursuit.firstDelay;
      G.events.emit('objective:all', {});
    }
  }

  function debugGrab() {
    if (game.mode !== 'mission' || !inRun()) return;
    const next = G.level.objectives.find((o) => !secured.has(o.id));
    if (next) secure(next);
  }

  /** After the last reel: a finite trickle of extra Vultures, and everyone keeps being pointed at Rule. */
  function updatePursuit(dt) {
    const P = flow.pursuit;
    pursuitTimer -= dt;
    if (pursuitTimer > 0) return;
    if (pursuitLeft > 0 && queue.length === 0 && G.enemies.aliveCount() < P.minAlive) {
      pursuitLeft--;
      queueWave([rng.chance(P.buzzardShare) ? 'buzzard' : 'goon'], P.spawnDelay, 0);
      pursuitTimer = diff.pursuitEvery;
    } else {
      pursuitTimer = P.realertEvery;
      G.enemies.alert(G.player.pos, P.realertRadius);
    }
  }

  function updateExtraction() {
    const E = flow.extraction;
    const ex = G.level.extraction;
    const p = G.player.pos;
    if (Math.hypot(ex.pos.x - p.x, ex.pos.z - p.z) > ex.radius || Math.abs(ex.pos.y - p.y) > E.vertical) return;
    if (run.reels >= run.total) {
      G.player.invulnerable = true;
      if (ex.prop.setState) ex.prop.setState('open');
      radio(text.radio.done);
      G.events.emit('extraction:reached', {});
      G.audio.sting('complete');
      setState('complete');
      G.input.exitLock(); // the debrief card needs the mouse back
    } else if (clock - refusedAt > E.refuseEvery) {
      refusedAt = clock;
      G.hud.message(text.prompts.refuse, E.refuseSecs);
    }
  }

  // ---------------------------------------------------------------------------------------------
  // Hold the Block
  // ---------------------------------------------------------------------------------------------

  function startWave() {
    const H = flow.holdout;
    const n = ++run.wave;
    holdout.active = true;
    applyDifficulty(); // scales are relative to the base table, never compounding
    G.enemies.setScale({ hp: H.hpScale(n), damage: H.damageScale(n), cooldown: H.cooldownScale(n) });
    maxAlive = diff.maxAlive + H.extraAlive(n);
    const total = H.total(n);
    const buzzards = Math.round(total * H.buzzardShare(n));
    const from = queueWave(mixedWave(buzzards, total - buzzards), H.firstSpawn, H.stagger(n));
    G.hud.warn(text.banners.wave(n, from), H.bannerSecs);
    refreshObjective();
    G.events.emit('holdout:wave', { wave: n, count: total });
  }

  function clearWave() {
    const H = flow.holdout;
    const n = run.wave;
    holdout.active = false;
    holdout.breakLeft = H.breather;
    holdout.countdown = H.countdownFrom;
    run.score += H.score.waveClear(n);
    if (typeof G.weapon.resupply === 'function') G.weapon.resupply(H.resupply.share);
    G.player.heal(H.resupply.heal);
    if (n % H.resupply.explosivesEvery === 0) G.explosives.reset();
    radio(text.radio.waveClear, n);
    refreshObjective();
    G.events.emit('objective:done', { id: 'wave', index: n, total: n });
    G.audio.sting('reel');
  }

  function updateHoldout(dt) {
    if (holdout.active) {
      if (queue.length === 0 && G.enemies.aliveCount() === 0) clearWave();
      return;
    }
    holdout.breakLeft -= dt;
    // "Wave N in 3 … 2 … 1", one message per second, not before the first wave.
    if (run.wave > 0 && holdout.countdown > 0 && holdout.breakLeft <= holdout.countdown) {
      G.hud.message(text.banners.countdown(run.wave + 1, holdout.countdown), flow.pacing.countdownSecs);
      holdout.countdown--;
    }
    if (holdout.breakLeft <= 0) startWave();
  }

  // ---------------------------------------------------------------------------------------------
  // Cards
  // ---------------------------------------------------------------------------------------------

  function deathCard() {
    const data = {
      mode: game.mode,
      time: run.time,
      reels: run.reels,
      total: run.total,
      wave: Math.max(0, run.wave - (holdout.active ? 1 : 0)), // waves fully cleared
      kills: run.kills,
      score: Math.round(run.score),
      best: 0,
      newBest: false,
    };
    if (game.mode === 'holdout') {
      data.newBest = G.settings.setBest(data.score);
      data.best = G.settings.best();
    }
    G.menus.show('dead', data);
  }

  function debriefCard() {
    G.menus.show('complete', {
      mode: game.mode,
      time: run.time,
      accuracy: run.shots > 0 ? run.hits / run.shots : null,
      kills: run.kills,
      retries: run.retries,
      rating: flow.ratingPoints(run),
    });
  }

  /** Eases the screen toward a [target, rate] pair from config/flow.js `post`. */
  function easePost(look, dt) {
    post.saturation = damp(post.saturation, look.saturation[0], look.saturation[1], dt);
    post.fade = damp(post.fade, look.fade[0], look.fade[1], dt);
  }

  // ---------------------------------------------------------------------------------------------
  // Title camera
  // ---------------------------------------------------------------------------------------------

  function updateTitleCamera() {
    const path = G.level.cinematicPath;
    if (!path || path.length < 2) return;
    const T = flow.titleCamera;
    const t = stateTime % titleLoop;
    const u = (t / titleLoop) * (path.length - 1);
    const i = Math.min(path.length - 2, Math.floor(u));
    const k = smoothstep(0, 1, u - i);
    camera.position.lerpVectors(path[i].pos, path[i + 1].pos, k);
    lookAt.lerpVectors(path[i].look, path[i + 1].look, k);
    camera.lookAt(lookAt);
    camera.fov = T.fov;
    post.fade = lerp(1, 0, smoothstep(0, T.fadeIn, t)) + smoothstep(titleLoop - T.fadeOut, titleLoop, t);
    post.saturation = 1;
  }

  // ---------------------------------------------------------------------------------------------
  // Update
  // ---------------------------------------------------------------------------------------------

  function update(dt) {
    stateTime += dt;
    const { state } = game;

    if (state === 'title') {
      updateTitleCamera();
      G.audio.setMusicIntensity(flow.music.calm);
      return false;
    }

    if (state === 'paused') {
      if (stateTime > flow.timing.pauseDebounce && G.input.pressed('pause')) resume();
      return false;
    }

    if (state === 'dead') {
      easePost(flow.post.dead, dt);
      if (!cardShown && stateTime >= flow.timing.deathCard) {
        cardShown = true;
        deathCard();
      }
      return true;
    }

    if (state === 'complete') {
      easePost(flow.post.complete, dt);
      if (!cardShown && stateTime >= flow.timing.debriefCard) {
        cardShown = true;
        debriefCard();
      }
      return true;
    }

    // intro and playing: the player has control in both
    clock += dt;
    if (G.input.pressed('pause')) {
      pause();
      return false;
    }

    if (state === 'intro') {
      const [from, to] = flow.timing.introFade;
      post.fade = 1 - smoothstep(from, Math.min(introLength, to), stateTime);
      if (fullIntro && !introCard && stateTime >= flow.timing.locationCardAt) {
        introCard = true;
        G.menus.locationCard(true);
      }
      if (fullIntro && !introRadio && stateTime >= flow.timing.introRadioAt) {
        introRadio = true;
        radio(text.radio.intro);
      }
      if (stateTime >= introLength) finishIntro();
    } else {
      run.time += dt;
    }

    const stats = G.combat.stats;
    run.kills = stats.kills;
    run.shots = stats.shots;
    run.hits = stats.hits;

    pumpQueue();
    if (game.mode === 'mission') {
      updateInteraction(dt);
      if (run.reels >= run.total) updatePursuit(dt);
      updateExtraction();
    } else {
      updateHoldout(dt);
    }

    if (!saidLow && G.player.alive && G.player.health < G.config.player.health.lowWarning) {
      saidLow = true;
      radio(text.radio.lowHealth);
    }

    const M = flow.music;
    const hot = queue.length > 0 || holdout.active || (game.mode === 'mission' && run.reels >= run.total);
    G.audio.setMusicIntensity(hot ? M.hot : G.enemies.nearestDistance() < M.nearDistance ? M.alert : M.calm);
    return true;
  }

  // ---------------------------------------------------------------------------------------------
  // Events
  // ---------------------------------------------------------------------------------------------

  G.events.on('player:dead', () => {
    if (game.state !== 'playing' && game.state !== 'intro' && game.state !== 'paused') return;
    G.hud.clearRadio();
    G.menus.locationCard(false);
    G.audio.sting('dead');
    setState('dead');
    G.input.exitLock();
  });

  G.events.on('enemy:alert', () => {
    if (saidContact || game.state !== 'playing') return;
    saidContact = true;
    radio(text.radio.contact);
  });

  G.events.on('enemy:killed', (e) => {
    if (game.mode !== 'holdout' || game.state !== 'playing') return;
    const H = flow.holdout.score;
    run.score += (H[e.type] || H.buzzard) * H.killScale(run.wave);
    refreshObjective();
  });

  G.events.on('settings:change', ({ key, value }) => {
    if (key === 'difficulty') setDifficulty(value);
    if (key === 'mode' && game.state === 'title') game.mode = value;
  });

  // Losing the mouse or the tab mid-run pauses the game.
  G.events.on('input:lock', (e) => {
    if (e.locked) everLocked = true;
    else if (everLocked && e.mode === 'lock') pause();
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) pause();
  });

  // ---------------------------------------------------------------------------------------------
  // Start on the title screen
  // ---------------------------------------------------------------------------------------------

  {
    const path = G.level.cinematicPath || [];
    let length = 0;
    for (let i = 1; i < path.length; i++) length += path[i].pos.distanceTo(path[i - 1].pos);
    titleLoop = Math.max(flow.titleCamera.minLoop, length / flow.titleCamera.speed);
  }
  applyDifficulty();
  post.fade = 1;
  setState('title', null);

  return game;
}
