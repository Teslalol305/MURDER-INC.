// G.game — the flow controller (CONTRACT 6.13, rules from the reference notes 04 with DESIGN 2 and 3).
//
//   title → (cutscene →) intro → playing ⇄ paused,  playing → dead | cutscene | complete
//
// Story: four levels on the one block (src/config/story.js), a cutscene before each and one after the
// last. A level has one thing to do, and the HUD always says which: get to the level's master reel
// (the gold guide line on the ground leads there), hold Interact to take it back, clear out the wave
// that comes for it; the last level is the run to the IPX truck with a finite pursuit behind. Every
// level is a checkpoint: Rule goes down, he goes again from its start with what he had when it began.
// Hold the Block: growing waves with a breather and a resupply between them, a score and a local best.
//
// This file owns the state machine, the run and level set-up, the interaction, the spawn queue and its
// pump, the radio queue, the cutscene on screen, the music-intensity driver, the title camera and the
// screen fades. The rules that are pure arithmetic live in src/game/* (waves, spawn scoring, music,
// radio timing, card data, the story's bookkeeping, the cutscene director) with unit tests in
// test/flow-*.test.js and test/story.test.js; the guide line and the ammo pickups are src/game/guide.js
// and src/game/pickups.js. Every number is in src/config/flow.js, every line in src/config/text.js.
//
// Beyond the contract (documented in CONTRACT 6.13 "as built"): game.flow and game.holdout are live
// read-only views for tests and tuning; game.guide and game.pickups are what the minimap draws from.

import * as THREE from 'three';
import * as STORY from './config/story.js';
import { clamp01, damp, paramOn, smoothstep } from './core/util.js';
import { createCutscene } from './game/cutscene.js';
import { createGuide } from './game/guide.js';
import { musicIntensity, waveIsOver } from './game/music.js';
import { introCopy } from './game/intro.js';
import { createPickups, shouldDrop } from './game/pickups.js';
import { createRadio } from './game/radio.js';
import { compassSector, pickSpawn } from './game/spawn.js';
import { cardData } from './game/stats.js';
import { facing, levelCard, objectiveLine, patrolOf, stageOf, timeOf } from './game/story.js';
import { createTitleCamera } from './game/titlecam.js';
import { BUZZARD, holdoutWave, killScore, missionOrder, pursuitType } from './game/waves.js';

const TYPING = /^(BUTTON|A|INPUT|SELECT|TEXTAREA)$/;
const SKIP_KEYS = ['Enter', 'NumpadEnter', 'Space'];
const HUNT_EVERY = 0.5; // seconds between looks for the nearest Vulture while a level is being cleared
const HUNT_BEYOND = 13; // …the guide line only leads to one that is further off than this

export function createGame(G) {
  const { text, flow } = G.config;
  const story = G.config.story || STORY;
  const levels = story.levels;
  const S = flow.story;
  const words = text.story;
  const rng = G.rng.fork('game');
  const camera = G.camera;
  const post = G.render.post;
  const quiet = paramOn(G.params, 'shot'); // screenshots: no look-mode toasts
  // Cutscenes play unless the page was told to start in the fight (the harness' ?autostart, ?shot);
  // ?scenes=1 / ?scenes=0 says otherwise either way.
  const scenesOn = G.params.scenes !== undefined ? paramOn(G.params, 'scenes') : !(paramOn(G.params, 'autostart') || quiet);

  const run = { time: 0, reels: 0, total: 3, retries: 0, wave: 0, score: 0, kills: 0, shots: 0, hits: 0, level: 0, levels: levels.length };
  const queue = []; // pending arrivals: {type, at, pos, tries}
  const holdout = { active: false, breakLeft: 0, countdown: 0, cleared: 0, realertIn: 0 };
  // What the flow is doing right now, for tests and tuning. Read-only for everyone else.
  const view = {
    queue,
    clock: 0,
    maxAlive: 0,
    pursuitLeft: 0,
    pursuitTimer: 0,
    music: flow.music.calm,
    lastWave: null,
    grabbing: null,
    progress: 0,
    level: 0, // 1-based; 0 outside the story
    phase: '', // 'reach' | 'clear' | 'truck' | 'done'
    left: 0, // Vultures still to put down in a level being cleared
    scene: null, // the name of the cutscene on screen
    sceneTime: 0,
  };

  const guide = createGuide(G);
  const pickups = createPickups(G);

  const game = {
    state: 'title',
    mode: G.settings.get('mode'),
    difficulty: G.settings.get('difficulty'),
    run,
    flow: view,
    holdout,
    guide,
    pickups,
    start,
    pause,
    resume,
    restart,
    retry,
    redeploy,
    toTitle,
    skipCutscene,
    setDifficulty,
    debugGrab,
    debugLevel,
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
  let resumeTo = 'playing'; // what a pause goes back to

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

  // The story.
  let levelIndex = -1; // which level is set up (−1: none)
  let phase = ''; // what that level wants right now
  let scene = null; // the cutscene on screen: {name, play, then, lines, card, place}
  let endingPlayed = false;
  let checkpoint = null; // weapon.loadout() at the start of the level
  let clearIn = 0; // > 0: the level is done and the next one comes up when this runs out
  let realertIn = 0;
  let huntIn = 0;
  let leftShown = -1; // the count the objective line was last written with
  let markedFoes = -1; // how many Vultures carry a HUD marker
  let levelClock = 0; // seconds played in this level
  let hinted = 0; // how many of the first level's how-to lines have been shown
  let levelRetry = false; // this level was restarted from its checkpoint

  // Reused every frame: no garbage while the player stands at a reel or a wave pours in.
  const promptSpec = { text: '', glyph: '', code: '', progress: 0 };
  const progressEvent = { id: '', t: 0 };
  const musicState = { allDone: false, queued: 0, alive: 0, waveAge: Infinity, sinceAlert: Infinity, sinceHit: Infinity, nearest: Infinity };
  const eye = new THREE.Vector3();
  const probe = new THREE.Vector3();
  const sum = new THREE.Vector3();
  const huntAt = new THREE.Vector3();

  const titleCamera = createTitleCamera(G.level.cinematicPath, flow.titleCamera);

  const inRun = () => game.state === 'playing' || game.state === 'intro';
  const mission = () => game.mode === 'mission';
  const allSecured = () => mission() && run.total > 0 && run.reels >= run.total;
  const guided = () => G.settings.get('guide') !== false;
  const has = (obj, method) => !!obj && typeof obj[method] === 'function';
  const level = () => levels[Math.max(0, levelIndex)];

  /** Objective and truck props are optional talents of the level: a stub may not have them. */
  function setProp(thing, state, t) {
    const prop = thing && thing.prop;
    if (prop && typeof prop.setState === 'function') prop.setState(state, t);
  }

  // ---------------------------------------------------------------------------------------------
  // Radio: the Vault, lines in order (src/game/radio.js keeps the timing)
  // ---------------------------------------------------------------------------------------------

  const radio = createRadio({
    charsPerSec: flow.pacing.radioCharsPerSec,
    gap: flow.pacing.radioGap,
    onLine(line, secs) {
      G.hud.radio(text.radio.speaker, line, secs);
      G.events.emit('radio:line', { speaker: text.radio.speaker, text: line, secs });
    },
    onClear() {
      G.hud.clearRadio();
    },
  });

  function say(line, arg) {
    if (!line) return;
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
    if (next !== 'paused') resumeTo = 'playing'; // only a pause remembers where it came from
    const active = next === 'playing' || next === 'intro';
    G.input.setGameplay(active);
    G.hud.show(active);
    G.weapon.setVisible(active);
    // A dead player keeps simulating (the death camera); the title, a cutscene and the debrief own the camera.
    G.player.enabled = active || next === 'dead' || (next === 'paused' && resumeTo !== 'cutscene');
    G.audio.setPaused(next === 'paused');
    // While the camera is elsewhere nobody finds Rule: the Vultures of the level keep to their posts.
    if (has(G.enemies, 'setBlind')) G.enemies.setBlind(next === 'cutscene' || (next === 'paused' && resumeTo === 'cutscene'));
    if (next === 'title' || next === 'paused') G.menus.show(next);
    else G.menus.show('none'); // the death and debrief cards come up later, from update()
    dressScene(next === 'cutscene');
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

  /**
   * Day or night: the look, and the clock on the location card. The story's later levels play after
   * dark whatever the setting says (src/config/story.js `time`); everything else follows the setting.
   */
  function applyTimeOfDay(index = -1) {
    const time = index >= 0 ? timeOf(index, levels, G.settings.get('time')) : G.settings.get('time') === 'night' ? 'night' : 'day';
    if (G.atmos && typeof G.atmos.setTime === 'function' && G.atmos.time !== time) G.atmos.setTime(time);
    text.location.place = text.location.byTime[time];
  }

  /** Puts every module back to the start of a run. `run.retries` is the caller's business. */
  function reset() {
    const isStory = mission();
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
    levelIndex = -1;
    phase = '';
    scene = null;
    endingPlayed = false;
    checkpoint = null;
    clearIn = 0;
    hinted = 0;
    Object.assign(run, { time: 0, reels: 0, total: G.level.objectives.length, wave: 0, score: 0, kills: 0, shots: 0, hits: 0, level: 0, levels: levels.length });
    Object.assign(view, { clock: 0, pursuitLeft: 0, pursuitTimer: 0, lastWave: null, grabbing: null, progress: 0, level: 0, phase: '', left: 0, scene: null, sceneTime: 0 });

    hushRadio();
    G.combat.reset();
    G.weapon.reset();
    guide.setTarget(null);
    pickups.clear();
    G.hud.setStage('');
    post.saturation = 1;
    post.flash = 0;

    if (isStory) {
      setupLevel(0);
    } else {
      applyTimeOfDay();
      G.enemies.clear();
      applyDifficulty();
      G.fx.clear();
      G.explosives.reset();
      G.player.reset(G.level.playerStart);
      G.hud.reset();
      promptOn = false;
      G.menus.locationCard(false);
      for (const o of G.level.objectives) setProp(o, 'taken', 0);
      setProp(G.level.extraction, 'idle');
      pickups.place((story.holdoutCrates || []).slice(0, flow.pickups.holdoutCrates));
      G.hud.setTally(text.objectives.tally.standby);
      refreshObjective();
    }
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
    if (mission()) {
      playScene(level().scene, enterLevel);
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
    if (startedFrame === G.time.frame && (inRun() || game.state === 'cutscene')) return;
    startedFrame = G.time.frame;
    run.retries = 0;
    begin({ ...opts, mode: flow.modes.includes(opts.mode) ? opts.mode : G.settings.get('mode') });
  }

  /**
   * The pause card's restart, counted as a retry: the story goes back to the start of the level it is
   * in, Hold the Block starts its run again.
   */
  function restart() {
    run.retries++;
    if (mission() && levelIndex >= 0) retryLevel();
    else begin({ quick: true });
  }

  /** The death card's button: the same. */
  function retry() {
    restart();
  }

  /** "Run it back" on the debrief: a new run with a clean sheet. */
  function redeploy() {
    run.retries = 0;
    begin({ quick: true });
  }

  function pause() {
    if (game.state === 'cutscene') {
      resumeTo = 'cutscene';
      setState('paused');
      G.input.exitLock();
      return;
    }
    if (!inRun()) return;
    if (game.state === 'intro') finishIntro();
    resumeTo = 'playing';
    setState('paused');
    G.input.exitLock();
  }

  function resume() {
    if (game.state !== 'paused') return;
    const to = resumeTo === 'cutscene' && scene ? 'cutscene' : 'playing';
    resumeTo = 'playing';
    setState(to);
    G.input.requestLock();
  }

  function toTitle() {
    queue.length = 0;
    scene = null;
    levelIndex = -1;
    phase = '';
    clearIn = 0;
    view.level = 0;
    view.phase = '';
    view.scene = null;
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
    G.hud.setStage('');
    guide.setTarget(null);
    pickups.clear();
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
  // The story: levels
  // ---------------------------------------------------------------------------------------------

  /** The reel a level is after (null for the run to the truck). */
  const reelOf = (L) => (L && L.reel ? G.level.objectives.find((o) => o.id === L.reel) || null : null);

  /** Where a level leads: its reel, or the truck. */
  function goalOf(L) {
    const reel = reelOf(L);
    return reel ? reel.pos : G.level.extraction.pos;
  }

  /** A walkable spot on the street nearest to (x, z), written to `out`. False when there is none. */
  function onStreet(x, z, out) {
    const near = G.physics.nav.nearestWalkable(x, z, 3);
    if (!near) return false;
    out.set(near.x, G.physics.groundHeight(near.x, near.z, 3), near.z);
    return true;
  }

  /** Where Rule stands when a level begins, facing down the route to what it wants. */
  function startOf(L) {
    const base = G.level.playerStart;
    const pos = base.pos.clone();
    if (L.start) onStreet(L.start.x, L.start.z, pos);
    const route = G.physics.nav.findPath(pos, goalOf(L), []);
    return { pos, yaw: facing(route, base.yaw) };
  }

  /** The level's Vultures, standing at their posts and not yet looking for anyone. */
  function spawnPosts(L, counts) {
    const at = new THREE.Vector3();
    for (const { type, point } of patrolOf(L, counts)) {
      if (type === BUZZARD) at.set(point[0], point[1], point[2]);
      else if (!onStreet(point[0], point[1], at)) continue;
      G.enemies.spawn(type, at, { alerted: false });
    }
  }

  /**
   * Sets the block up for level `index`: Rule at its start, its Vultures at their posts, its crates
   * out, the reels of the levels before it back in his hands. `retry`: the level is being gone at
   * again, so the guns are what they were when it first began.
   */
  function setupLevel(index, { retry: again = false } = {}) {
    const L = levels[index];
    const stage = stageOf(index, levels);
    levelIndex = index;
    levelRetry = again;
    run.level = stage.n;
    view.level = stage.n;
    queue.length = 0;
    lastUsed.clear();
    grabTarget = null;
    progress = 0;
    refusedAt = -Infinity;
    saidContact = saidLow = false;
    pursuitLeft = 0;
    pursuitTimer = 0;
    waveAge = sinceAlert = sinceHit = Infinity;
    clearIn = 0;
    realertIn = S.clearRealertEvery;
    huntIn = 0;
    leftShown = -1;
    markedFoes = -1;
    levelClock = 0;
    view.lastWave = null;
    view.grabbing = null;
    view.progress = 0;
    view.left = 0;
    // A level gone at again gives its reel back to the Vultures.
    if (L.reel) secured.delete(L.reel);
    run.reels = secured.size;
    phase = L.goal === 'truck' ? 'truck' : 'reach';

    hushRadio();
    applyTimeOfDay(index);
    G.enemies.clear();
    applyDifficulty();
    G.fx.clear();
    G.explosives.reset();
    G.player.reset(startOf(L));
    // The guns: a fresh story has a fresh rack (reset() saw to that); a level reached is a breather;
    // a level gone at again starts with what it started with.
    if (again && checkpoint && has(G.weapon, 'restore')) G.weapon.restore(checkpoint);
    else if (!again && index > 0 && has(G.weapon, 'rearm')) G.weapon.rearm(S.checkpointShare);
    if (!again || !checkpoint) checkpoint = has(G.weapon, 'loadout') ? G.weapon.loadout() : null;

    G.hud.reset();
    promptOn = false;
    G.menus.locationCard(false);
    post.saturation = 1;
    post.flash = 0;
    for (const o of G.level.objectives) setProp(o, secured.has(o.id) ? 'taken' : 'live', secured.has(o.id) ? 1 : 0);
    setProp(G.level.extraction, 'idle');

    spawnPosts(L, diff.levels[Math.min(index, diff.levels.length - 1)].patrol);
    if (L.goal === 'truck') {
      pursuitLeft = diff.pursuitBudget;
      pursuitTimer = flow.pursuit.firstDelay;
    }
    view.pursuitLeft = pursuitLeft;
    view.pursuitTimer = pursuitTimer;
    pickups.place(L.crates);

    showReels();
    G.hud.setStage(words.stage(stage.n, words.levels[L.id].title));
    refreshObjective();
    G.events.emit('game:level', { level: stage.n, total: stage.total, id: L.id, retry: again });
  }

  /** The level begins to play: a short fade in from black, its name on the location card, the Vault's first word. */
  function enterLevel() {
    G.player.invulnerable = false;
    introLength = flow.timing.intro;
    fullIntro = true;
    introCard = introRadio = false;
    post.fade = 1;
    setState('intro');
    G.input.requestLock();
  }

  /** Back to the start of the level Rule went down in (or asked to restart). */
  function retryLevel() {
    scene = null;
    setupLevel(levelIndex, { retry: true });
    G.audio.setMusicIntensity(flow.music.calm);
    introLength = flow.timing.introQuick;
    fullIntro = false;
    introCard = introRadio = true;
    post.fade = 1;
    setState('intro');
    G.input.requestLock();
  }

  /** The last Vulture of the level is down. */
  function levelCleared() {
    const L = level();
    phase = 'done';
    clearIn = S.levelClear;
    G.player.invulnerable = true; // nothing stray takes this away now
    G.hud.warn(words.banners.clear, S.levelClear);
    G.audio.sting('all');
    hushRadio(); // whatever the Vault was still saying about the fight is over with it
    say(words.levels[L.id].clear);
    refreshObjective();
    G.events.emit('game:level', { level: levelIndex + 1, total: levels.length, id: L.id, cleared: true });
  }

  /** The next level is set up behind a black screen, then its cutscene plays over it. */
  function nextLevel() {
    setupLevel(levelIndex + 1);
    playScene(level().scene, enterLevel);
  }

  /** Test and tool hook: sets level `index` (0-based) up and starts it, with no cutscene. */
  function debugLevel(index) {
    if (!mission()) return;
    const i = Math.min(levels.length - 1, Math.max(0, index | 0));
    scene = null;
    for (let k = 0; k < levels.length; k++) {
      const reel = levels[k].reel;
      if (!reel) continue;
      if (k < i) secured.add(reel);
      else secured.delete(reel);
    }
    setupLevel(i);
    post.fade = 0;
    setState('playing');
  }

  // ---------------------------------------------------------------------------------------------
  // The story: cutscenes
  // ---------------------------------------------------------------------------------------------

  /** What the menus dress the scene with: the place line, the title card, the key that skips. */
  function dressScene(on) {
    if (!has(G.menus, 'cutscene')) return;
    if (!on || !scene) {
      G.menus.cutscene(null);
      return;
    }
    const device = G.input.device || 'kbm';
    G.menus.cutscene({ place: scene.place, card: scene.card, key: device === 'touch' || G.input.touch ? '' : device === 'pad' ? 'A' : 'ENTER' });
  }

  function onCue(cue) {
    if (!scene) return;
    if (cue.say !== undefined) {
      const line = scene.lines[cue.say];
      if (line) {
        const who = words.speakers[line.who] || text.radio.speaker;
        G.hud.clearRadio();
        G.hud.radio(who, line.text, line.secs);
        // Only the Vault comes over the radio (the squelch): Rule is standing right there.
        if (line.who === 'vault') G.events.emit('radio:line', { speaker: who, text: line.text, secs: line.secs });
      }
    }
    if (cue.place) scene.place = text.location.place;
    if (cue.card) {
      scene.card = cue.card === 'end' ? words.end : levelCard(stageOf(levelIndex, levels), words);
      if (cue.card !== 'end') G.audio.sting('reel');
    }
    if (cue.train && G.atmos && typeof G.atmos.passTrain === 'function') G.atmos.passTrain(cue.train, 2.6);
    if (cue.place || cue.card) dressScene(true);
  }

  /** Plays cutscene `name`, then calls `then`. With cutscenes off (or no such scene) `then` runs at once. */
  function playScene(name, then) {
    const script = name ? story.scenes[name] : null;
    if (!scenesOn || !script) {
      then();
      return;
    }
    hushRadio();
    scene = { name, then, lines: words.scenes[name] || [], card: null, place: '', play: null };
    scene.play = createCutscene(script, S.cutscene, onCue);
    G.player.invulnerable = true;
    post.fade = 1;
    post.saturation = 1;
    G.audio.setMusicIntensity(flow.music.calm);
    view.scene = name;
    view.sceneTime = 0;
    setState('cutscene');
  }

  function endScene() {
    const done = scene;
    scene = null;
    view.scene = null;
    G.hud.clearRadio();
    post.fade = 1;
    if (done) done.then();
  }

  /** The Skip control, Enter / Space, or the gamepad's A / Start. A press in the first moment is ignored. */
  function skipCutscene() {
    if (game.state !== 'cutscene' || !scene || scene.play.time < S.cutscene.skipAfter) return;
    scene.play.skip();
    endScene();
  }

  // ---------------------------------------------------------------------------------------------
  // HUD lines
  // ---------------------------------------------------------------------------------------------

  /** The reel bullets: which ones are back. */
  function showReels() {
    const codes = [];
    for (const o of G.level.objectives) if (secured.has(o.id)) codes.push(o.code);
    G.hud.setReels(run.reels, run.total, codes);
  }

  /** How many are still to be put down: on the block and on their way. */
  const vulturesLeft = () => queue.length + G.enemies.aliveCount();

  function refreshObjective() {
    if (!mission()) {
      const h = text.objectives.holdout;
      G.hud.setObjective(holdout.active ? h.hold : run.wave === 0 ? h.inbound : h.breather);
      G.hud.setMarkers([]);
      guide.setTarget(null);
      refreshTally();
      return;
    }
    const L = level();
    const markers = [];
    view.phase = phase;
    if (phase === 'reach') {
      const o = reelOf(L);
      G.hud.setObjective(objectiveLine('reach', { code: o.code, guided: guided() }, words.objectives));
      markers.push({ id: o.id, code: o.code, label: o.label, pos: o.pos, kind: 'reel' });
      guide.setTarget(o.pos);
    } else if (phase === 'clear') {
      const left = vulturesLeft();
      leftShown = left;
      view.left = left;
      G.hud.setObjective(objectiveLine('clear', { left }, words.objectives));
      // The last few get a marker each, so the level never ends in a search.
      markedFoes = 0;
      if (queue.length === 0 && left <= S.leftover) {
        for (const e of G.enemies.list) {
          if (!e.alive) continue;
          markers.push({ id: `foe${e.id}`, code: '!', label: text.enemies[e.type] ? text.enemies[e.type].name : '', pos: e.pos, kind: 'foe', enemy: e });
          markedFoes++;
        }
      }
    } else if (phase === 'truck') {
      const ex = G.level.extraction;
      G.hud.setObjective(objectiveLine('truck', { guided: guided() }, words.objectives));
      markers.push({ id: 'extraction', code: ex.code, label: ex.label, pos: ex.pos, kind: 'exit' });
      guide.setTarget(ex.pos);
    } else {
      G.hud.setObjective(objectiveLine('done', {}, words.objectives));
      guide.setTarget(null);
    }
    G.hud.setMarkers(markers);
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
    const line = input.hint();
    if (line) G.hud.message(line, flow.timing.lookHintSecs);
  }

  /** The first level says how the game is played, one line at a time (not on a retry: Rule knows by then). */
  function updateHowTo() {
    if (quiet || levelIndex !== 0 || levelRetry || run.retries > 0 || hinted >= 3 || promptOn) return;
    const H = words.hints;
    const device = G.input.device || 'kbm';
    const touch = device === 'touch' || !!G.input.touch;
    const at = [S.hints.aim, S.hints.weapons, S.hints.path];
    if (levelClock < at[hinted]) return;
    const line =
      hinted === 0
        ? touch ? H.aimTouch : H.aim(G.input.glyph('ads'))
        : hinted === 1
          ? touch ? H.weaponsTouch : device === 'pad' ? H.weaponsPad : H.weapons
          : H.crates;
    hinted++;
    G.hud.message(line, S.hintSecs);
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
    const P = flow.spawn;
    const air = type === BUZZARD;
    const p = G.player.pos;
    eye.set(p.x, p.y + P.eyeHeight, p.z);
    spawnQuery.x = p.x;
    spawnQuery.z = p.z;
    spawnQuery.minDistance = minDistance;
    spawnQuery.strict = strict;
    const point = pickSpawn(G.level.enemySpawns, air ? 'air' : 'ground', spawnQuery, P.score);

    if (point) {
      lastUsed.set(point, clock);
      out.copy(point.pos);
    } else {
      // A level without authored points: somewhere on a ring around the player, inside the block.
      const a = rng.range(0, Math.PI * 2);
      const b = G.level.bounds;
      out.set(
        Math.min(b.maxX - 2, Math.max(b.minX + 2, p.x + Math.cos(a) * P.fallbackRing)),
        0,
        Math.min(b.maxZ - 2, Math.max(b.minZ + 2, p.z + Math.sin(a) * P.fallbackRing)),
      );
      if (!air) {
        const near = G.physics.nav.nearestWalkable(out.x, out.z);
        if (!near) return false;
        out.set(near.x, G.physics.groundHeight(near.x, near.z, 1), near.z);
      }
    }

    const jx = rng.range(-P.jitter, P.jitter);
    const jz = rng.range(-P.jitter, P.jitter);
    if (air) {
      out.x += jx;
      out.z += jz;
      if (out.y < P.airMinHeight) out.y = rng.range(P.airLift[0], P.airLift[1]);
    } else if (G.physics.nav.isWalkable(out.x + jx, out.z + jz)) {
      // Same floor as the authored point: a jitter must not climb onto a car or drop off a deck.
      const y = G.physics.groundHeight(out.x + jx, out.z + jz, out.y + 0.6);
      if (Math.abs(y - out.y) < 0.3) out.set(out.x + jx, y, out.z + jz);
    }
    return true;
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
    const P = flow.spawn;
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
      next.at = clock + P.capRetry;
      return;
    }
    // The player has walked up to a ground point since it was picked: come in somewhere else.
    const p = G.player.pos;
    if (next.type !== BUZZARD && Math.hypot(next.pos.x - p.x, next.pos.z - p.z) < P.tooClose) {
      choosePosition(next.type, P.far, false, next.pos);
    }
    if (G.enemies.spawn(next.type, next.pos, { alerted: true, target: p })) {
      queue.splice(index, 1);
      G.enemies.alert(p, P.alertRadius);
    } else if (++next.tries >= P.poolTries) {
      queue.splice(index, 1);
    } else {
      next.at = clock + P.poolRetry;
    }
  }

  // ---------------------------------------------------------------------------------------------
  // Story mode: the reel, the fight for it, the truck
  // ---------------------------------------------------------------------------------------------

  /** The level's reel, when the player can reach it and is facing it. */
  function reelInReach() {
    if (phase !== 'reach') return null;
    const o = reelOf(level());
    if (!o || secured.has(o.id)) return null;
    const I = flow.interact;
    const p = G.player;
    const dx = o.pos.x - p.pos.x;
    const dz = o.pos.z - p.pos.z;
    const d = Math.hypot(dx, dz);
    if (d > I.range || Math.abs(o.pos.y - p.pos.y) > I.vertical) return null;
    const fx = p.forward.x;
    const fz = p.forward.z;
    const flat = Math.hypot(fx, fz) || 1;
    if (d > I.freeRange && (dx * fx + dz * fz) / (d * flat) < I.facingDot) return null;
    return o;
  }

  function emitProgress(id, t) {
    progressEvent.id = id;
    progressEvent.t = t;
    G.events.emit('objective:progress', progressEvent);
  }

  /**
   * Hold Interact on the reel in reach to fill its bar. Letting go, looking away, stepping out or dying
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

  /** The reel is Rule's again: the Vultures come for it, and the level turns into clearing them out. */
  function secure(o) {
    secured.add(o.id);
    run.reels = secured.size;
    setProp(o, 'taken', 1);
    if (grabTarget === o) grabTarget = null;
    progress = 0;
    view.grabbing = null;
    view.progress = 0;
    showPrompt(null);
    showReels();
    G.player.addShake(flow.interact.shake);
    G.events.emit('objective:done', { id: o.id, index: run.reels, total: run.total });

    const all = run.reels >= run.total;
    const wave = diff.levels[Math.min(levelIndex, diff.levels.length - 1)].wave;
    const from = wave ? queueWave(missionOrder(wave.buzzard, wave.goon), flow.spawn.firstDelay, flow.spawn.stagger) : null;
    if (from) G.hud.warn(words.banners.ambush(from), flow.spawn.bannerSecs);
    const lines = text.radio.reel;
    hushRadio(); // this is the news now
    say(lines[Math.min(run.reels, lines.length) - 1]);
    G.audio.sting('reel');
    if (all) G.events.emit('objective:all', {});

    phase = 'clear';
    realertIn = S.clearRealertEvery;
    huntIn = 0;
    refreshObjective();
    // Whoever was still at a post hears it too.
    G.enemies.alert(G.player.pos, S.clearRealertRadius);
  }

  /** Test hook (CONTRACT): takes the level's reel at once. */
  function debugGrab() {
    if (!mission() || !inRun() || phase !== 'reach') return;
    const o = reelOf(level());
    if (o) secure(o);
  }

  /** The level's reel is back and the fight is on: count it down, keep it coming, end it. */
  function updateClear(dt) {
    const left = vulturesLeft();
    if (left === 0) {
      levelCleared();
      return;
    }
    const few = queue.length === 0 && left <= S.leftover;
    if (left !== leftShown || (few ? left : 0) !== markedFoes) refreshObjective();

    // Nobody sits a level out: whoever is left keeps being pointed at Rule.
    realertIn -= dt;
    if (realertIn <= 0) {
      realertIn = S.clearRealertEvery;
      G.enemies.alert(G.player.pos, S.clearRealertRadius);
    }

    // And when none of them is near, the guide line leads to the nearest one.
    huntIn -= dt;
    if (huntIn <= 0) {
      huntIn = HUNT_EVERY;
      const p = G.player.pos;
      let best = null;
      let bestD = Infinity;
      for (const e of G.enemies.list) {
        if (!e.alive) continue;
        const d = Math.hypot(e.pos.x - p.x, e.pos.z - p.z);
        if (d < bestD) {
          bestD = d;
          best = e;
        }
      }
      if (best && bestD > HUNT_BEYOND) guide.setTarget(huntAt.set(best.pos.x, 0, best.pos.z), true);
      else guide.setTarget(null);
    }
  }

  /** The last level: a finite trickle of extra Vultures, and everyone keeps being pointed at Rule. */
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
    if (phase === 'truck' && allSecured()) {
      if (G.player.alive) complete();
    } else if (phase !== 'done' && clock - refusedAt > E.refuseEvery) {
      refusedAt = clock;
      G.hud.message(text.prompts.refuse, E.refuseSecs);
    }
  }

  /** At the truck with all three: the closing scene, then the debrief. */
  function complete() {
    syncStats();
    phase = 'done';
    view.phase = phase;
    G.player.invulnerable = true;
    setProp(G.level.extraction, 'open');
    G.events.emit('extraction:reached', {});
    G.audio.sting('complete');
    hushRadio();
    queue.length = 0;
    guide.setTarget(null);
    showPrompt(null);
    endingPlayed = scenesOn && !!story.scenes[story.endScene];
    if (endingPlayed) {
      // The block goes quiet for the last pictures.
      G.enemies.clear();
      pickups.clear();
    }
    playScene(story.endScene, debrief);
  }

  function debrief() {
    setState('complete'); // player disabled, HUD hidden
    if (!endingPlayed) say(text.radio.done); // the closing scene has said it already
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
    if (has(G.weapon, 'resupply')) G.weapon.resupply(H.resupply.share);
    pickups.refill();
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
    const info = { mode: game.mode, difficulty: game.difficulty, wavesCleared: holdout.cleared, headshots: G.combat.stats.headshots, best: 0, newBest: false, levelTitle: '' };
    if (game.mode === 'holdout') {
      info.newBest = G.settings.setBest(run.score);
      info.best = G.settings.best();
    } else if (levelIndex >= 0) {
      info.levelTitle = words.levels[level().id].title;
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
    s.allDone = allSecured() && phase === 'truck';
    s.queued = queue.length;
    s.alive = G.enemies.aliveCount();
    s.waveAge = waveAge;
    s.sinceAlert = sinceAlert;
    s.sinceHit = sinceHit;
    s.nearest = G.enemies.nearestDistance();
    if (waveIsOver(s, M)) s.waveAge = waveAge = Infinity;
    const intensity = phase === 'done' ? M.calm : musicIntensity(s, M);
    view.music = intensity;
    G.audio.setMusicIntensity(intensity);
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
      guide.update(dt, false);
      pickups.update(dt, false);
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

    if (state === 'cutscene') {
      if (G.input.pressed('pause')) {
        pause();
        return false;
      }
      const nav = G.input.menuNav();
      if (nav && (nav.accept || nav.start)) skipCutscene();
      if (game.state !== 'cutscene' || !scene) return game.state !== 'title' && game.state !== 'paused';
      const over = scene.play.update(dt);
      post.fade = scene.play.apply(camera);
      post.saturation = 1;
      view.sceneTime = scene.play.time;
      guide.update(dt, false);
      pickups.update(dt, false);
      if (over) endScene();
      // The block lives on behind the pictures: Vultures at their posts, the train, the steam.
      return true;
    }

    if (state === 'dead') {
      easePost(flow.post.dead, dt);
      guide.update(dt, false);
      pickups.update(dt, false);
      if (!cardShown && stateTime >= flow.timing.deathCard) {
        cardShown = true;
        showCard('dead');
      }
      return true;
    }

    if (state === 'complete') {
      easePost(flow.post.complete, dt);
      radio.update(dt);
      guide.update(dt, false);
      pickups.update(dt, false);
      if (!cardShown && stateTime >= (endingPlayed ? flow.timing.debriefAfterScene : flow.timing.debriefCard)) {
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
        if (mission()) {
          // The level's name, and what it asks for.
          const stage = stageOf(levelIndex, levels);
          const card = levelCard(stage, words);
          G.menus.locationCard(true, { place: words.stage(stage.n, card.title), tagline: card.sub });
        } else {
          G.menus.locationCard(true, introCopy(false, text).card); // Hold the Block: no reels on its card
        }
      }
      if (fullIntro && !introRadio && stateTime >= T.introRadioAt) {
        introRadio = true;
        say(mission() ? words.levels[level().id].go : introCopy(false, text).line);
      }
      if (stateTime >= introLength) finishIntro();
    } else {
      run.time += dt;
      levelClock += dt;
    }

    syncStats();
    pumpQueue();
    if (mission()) {
      if (phase === 'reach') updateInteraction(dt);
      else if (phase === 'clear') updateClear(dt);
      else if (phase === 'truck') updatePursuit(dt);
      updateExtraction();
      if (game.state !== 'playing' && game.state !== 'intro') return game.state !== 'paused'; // the truck: nothing more to drive this frame
      if (clearIn > 0) {
        // Level clear: a beat to take it in, then the picture goes to black for the next level.
        clearIn -= dt;
        post.fade = 1 - smoothstep(0, 0.6, clearIn);
        if (clearIn <= 0) {
          if (levelIndex + 1 < levels.length) nextLevel();
          else complete();
          return game.state !== 'paused';
        }
      }
      updateHowTo();
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
    guide.update(dt, true);
    pickups.update(dt, G.player.alive && phase !== 'done');
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
    if (game.state !== 'playing' || !e) return;
    // What a Vulture leaves behind: a pouch of ammo, more often when the gun in hand is running low.
    if (e.byPlayer && e.pos) {
      const w = G.weapon;
      const full = w && w.def ? w.def.reserve : 0;
      const share = w && Number.isFinite(w.reserve) && full > 0 ? w.reserve / full : 1;
      if (shouldDrop(e.type, rng.next(), share, flow.pickups)) pickups.drop(e.pos);
    }
    if (game.mode !== 'holdout') return;
    run.score += killScore(e.type, run.wave, flow.holdout.score);
    refreshTally();
  });

  G.events.on('settings:change', ({ key, value }) => {
    if (key === 'difficulty') setDifficulty(value);
    else if (key === 'mode' && game.state === 'title') game.mode = value;
    else if (key === 'time' && game.state === 'title') applyTimeOfDay(); // mid-run it waits for the next reset
    else if (key === 'guide' && game.state !== 'title') refreshObjective(); // the objective line names the gold line or not
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

  document.addEventListener('keydown', (e) => {
    if (e.repeat) return;
    // A cutscene is skipped with Enter or Space (the Skip control is for a finger or a free mouse).
    if (game.state === 'cutscene') {
      if (!SKIP_KEYS.includes(e.code) || G.menus.panelOpen) return;
      // The key ends here: the level may begin on this very press, and Enter is also Fire, Space also Jump.
      e.preventDefault();
      e.stopPropagation();
      skipCutscene();
      return;
    }
    // Enter starts from the title even when focus has wandered off the button.
    if (game.state !== 'title' || (e.code !== 'Enter' && e.code !== 'NumpadEnter')) return;
    if (G.menus.panelOpen) return;
    const focus = document.activeElement;
    if (focus && TYPING.test(focus.tagName || '')) return; // the browser clicks a focused button itself
    e.stopPropagation(); // Enter is also Fire: this press starts the run, it does not shoot in it
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
