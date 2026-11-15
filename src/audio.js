// G.audio (CONTRACT 6.9): every sound and the music, procedural WebAudio.
//
//   src/audio/dsp.js          sample-level synthesis toolkit (pure)
//   src/audio/sfx-*.js        sound definitions: weapons, player, world, enemies, ambience
//   src/audio/music.js        the score: stems, riser, boombox mix, stings (pure)
//   src/audio/library.js      name → definition, render one variant, render order
//   src/audio/queue.js        background render queue (time-sliced generators)
//   src/audio/conductor.js    music player: phase-locked stems, intensity layers, grid-quantised stings
//   src/audio/ambience.js     the block: day / night beds, wind, neon, steam, far one-shots, the train
//   src/audio/react.js        game events → sounds
//
// Graph: world / near / gun / tail → muffle low-pass → pause gain → master; ambience → duck → its own
// low-pass (interior) → muffle; music → dip → duck → pause thinning → master; dry (UI, hurt) → master.
// Sends from world / near / gun into an outdoor and a shop convolver, split by the interior factor.
// Master: compressor → make-up → soft clip → volume. Every sound is rendered into AudioBuffers at load by
// the background queue (the guns first); nothing synthesises at play time.

import { SOUNDS, renderOrder, renderPriority, renderVariant, variantsOf } from './audio/library.js';
import { createQueue } from './audio/queue.js';
import { createConductor, layerGains, STEM_NAMES } from './audio/conductor.js';
import { createAmbience } from './audio/ambience.js';
import { wireEvents } from './audio/react.js';
import { impulse, seeded, measure } from './audio/dsp.js';
import { BAR, LOOP } from './audio/music.js';
import { createAudio as createSilentAudio } from './stubs/audio.js';

const BUS_GAIN = { world: 1.05, near: 0.95, gun: 1, tail: 0.85, amb: 0.7, dry: 0.95, music: 0.5 };
// Channels per bus: [flat, spatial]. Each channel is a persistent chain; sources are made per play.
const POOLS = { world: [0, 26], near: [12, 0], gun: [6, 0], tail: [8, 0], amb: [2, 6], dry: [10, 0], music: [4, 0] };
const SEND = { world: 0.5, near: 0.14, gun: 0.1, amb: 0 };
const DEFAULT_JITTER = 0.035;
const CULL = 160; // metres: a positional one-shot further away than this is not played

const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);

export function createAudio(G) {
  const AC = typeof window !== 'undefined' && (window.AudioContext || window.webkitAudioContext);
  if (!AC || typeof AudioBuffer === 'undefined') return createSilentAudio(G);
  const THREE = G.THREE;
  const rnd = seeded(0x5eed);

  // ---- buffers -------------------------------------------------------------------------------------

  const buffers = new Map(); // name → AudioBuffer[] (variants as they finish)
  const pendingRaw = []; // rendered before AudioBuffer could be made (old Safari): wrapped at unlock
  let bytes = 0;
  const canConstruct = (() => {
    try {
      new AudioBuffer({ length: 1, sampleRate: 22050, numberOfChannels: 1 });
      return true;
    } catch (err) {
      return false;
    }
  })();

  function toBuffer(r, context) {
    const len = r.channels[0].length;
    const buf = context
      ? context.createBuffer(r.channels.length, len, r.sr)
      : new AudioBuffer({ length: len, sampleRate: r.sr, numberOfChannels: r.channels.length });
    r.channels.forEach((ch, i) => buf.copyToChannel(ch, i));
    return buf;
  }

  function store(r) {
    bytes += r.channels.length * r.channels[0].length * 4;
    if (!canConstruct && !ctx) {
      pendingRaw.push(r);
      return;
    }
    let list = buffers.get(r.name);
    if (!list) buffers.set(r.name, (list = []));
    list[r.variant] = toBuffer(r, canConstruct ? null : ctx);
  }

  // With --expose-gc (the harness launches Chromium that way) V8 lets dead typed arrays pile up into
  // gigabytes while the queue renders: collect by hand every few sounds when window.gc exists.
  let sinceGc = 0;
  const collect = typeof window !== 'undefined' && typeof window.gc === 'function' ? window.gc : null;

  function* renderAll(name) {
    for (let v = 0; v < variantsOf(name); v++) {
      const r = yield* renderVariant(name, v);
      store(r);
      sinceGc += r.channels.length * r.channels[0].length * 4;
      if (collect && sinceGc > 1.5e6) {
        sinceGc = 0;
        collect();
      }
      yield;
    }
  }

  const queue = createQueue({ slice: 6, interval: 12 });
  for (const name of renderOrder()) queue.add(name, renderPriority(name), renderAll(name), () => {});

  /** Variants ready for `name`; renders a short sound on the spot if the queue has not reached it yet. */
  function ready(name, urgent = true) {
    const list = buffers.get(name);
    if (list && list.length) return list;
    if (!queue.has(name)) return null;
    const def = SOUNDS[name];
    if (urgent && !def.loop && def.bus !== 'music' && def.bus !== 'amb') {
      queue.finish(name);
      return buffers.get(name) || null;
    }
    queue.promote(name);
    return null;
  }

  const firstBuffer = (name) => {
    const list = ready(name, false);
    return list ? list[0] : null;
  };

  // ---- context and graph (built on unlock) ---------------------------------------------------------

  let ctx = null;
  let unlocked = false;
  const bus = {};
  const pools = {};
  const N = {}; // named nodes
  let conductor = null;
  let ambience = null;
  let impulses = false;

  function softClipCurve() {
    const n = 2048;
    const curve = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const x = (i / (n - 1)) * 2 - 1;
      const a = Math.abs(x);
      curve[i] = a < 0.6 ? x : Math.sign(x) * (0.6 + 0.4 * Math.tanh((a - 0.6) / 0.4));
    }
    return curve;
  }

  /** Filter frequencies stay under Nyquist whatever rate the device runs at. */
  const nyq = (f) => Math.min(f, ctx.sampleRate * 0.45);

  function lowpass(f, q = 0.5) {
    const n = ctx.createBiquadFilter();
    n.type = 'lowpass';
    n.frequency.value = nyq(f);
    n.Q.value = q;
    return n;
  }

  function gainNode(v = 1) {
    const n = ctx.createGain();
    n.gain.value = v;
    return n;
  }

  function buildGraph() {
    // Master chain.
    N.sum = gainNode(1);
    N.comp = ctx.createDynamicsCompressor();
    N.comp.threshold.value = -6;
    N.comp.knee.value = 8;
    N.comp.ratio.value = 2.5;
    N.comp.attack.value = 0.006;
    N.comp.release.value = 0.14;
    N.makeup = gainNode(1.15);
    N.clip = ctx.createWaveShaper();
    N.clip.curve = softClipCurve();
    N.clip.oversample = '2x';
    N.volume = gainNode(volume);
    N.sum.connect(N.comp).connect(N.makeup).connect(N.clip).connect(N.volume).connect(ctx.destination);

    // SFX: muffle → pause.
    N.pause = gainNode(1);
    N.pause.connect(N.sum);
    N.muffle = lowpass(20000, 0.6);
    N.muffle.connect(N.pause);
    for (const b of ['world', 'near', 'gun', 'tail']) {
      bus[b] = gainNode(BUS_GAIN[b]);
      bus[b].connect(N.muffle);
    }
    // Ambience: its own duck, pause, interior low-pass, state level.
    bus.amb = gainNode(BUS_GAIN.amb);
    N.ambDuck = gainNode(1);
    N.ambPause = gainNode(1);
    N.ambLevel = gainNode(1);
    N.ambLp = lowpass(20000, 0.5);
    bus.amb.connect(N.ambDuck).connect(N.ambLevel).connect(N.ambLp).connect(N.ambPause).connect(N.muffle);
    // Dry: straight to the master.
    bus.dry = gainNode(BUS_GAIN.dry);
    bus.dry.connect(N.sum);
    // Music: dip (explosions) → duck (guns) → pause thinning.
    bus.music = gainNode(BUS_GAIN.music);
    N.musicDip = gainNode(1);
    N.musicDuck = gainNode(1);
    N.musicPause = gainNode(1);
    N.musicLp = lowpass(20000, 0.6);
    bus.music.connect(N.musicDip).connect(N.musicDuck).connect(N.musicLp).connect(N.musicPause).connect(N.sum);

    // Reverb sends: an outdoor and a shop convolver, buffers made right after unlock.
    N.send = gainNode(1);
    N.verbOut = ctx.createConvolver();
    N.verbIn = ctx.createConvolver();
    N.verbOutGain = gainNode(0.8);
    N.verbInGain = gainNode(0);
    N.send.connect(N.verbOut).connect(N.verbOutGain).connect(N.muffle);
    N.send.connect(N.verbIn).connect(N.verbInGain).connect(N.muffle);
    for (const [b, amount] of Object.entries(SEND)) {
      if (!amount) continue;
      const s = gainNode(amount);
      bus[b].connect(s).connect(N.send);
    }

    // Voice channels.
    for (const [b, [flat, spatial]] of Object.entries(POOLS)) {
      pools[b] = { flat: [], spatial: [] };
      for (let i = 0; i < flat; i++) pools[b].flat.push({ bus: b, spatial: false, out: bus[b], name: '', prio: 0, end: 0, start: 0, src: null, g: null });
      for (let i = 0; i < spatial; i++) {
        const filter = lowpass(20000, 0.5);
        const panner = makePanner();
        filter.connect(panner).connect(bus[b]);
        pools[b].spatial.push({ bus: b, spatial: true, out: filter, filter, panner, name: '', prio: 0, end: 0, start: 0, src: null, g: null });
      }
    }

    conductor = createConductor(ctx, bus.music, firstBuffer, { rnd });
    ambience.attach();
  }

  function makePanner() {
    const p = ctx.createPanner();
    p.panningModel = 'equalpower';
    p.distanceModel = 'inverse';
    p.refDistance = 3;
    p.rolloffFactor = 1;
    p.maxDistance = 10000;
    return p;
  }

  function buildImpulses() {
    if (impulses || !ctx) return;
    impulses = true;
    const sr = ctx.sampleRate;
    const make = (secs, seed, o) => {
      const buf = ctx.createBuffer(2, Math.round(secs * sr), sr);
      for (let ch = 0; ch < 2; ch++) buf.copyToChannel(impulse(sr, secs, seeded(seed + ch * 31), o), ch);
      return buf;
    };
    // The street: early slaps off the facades and the El, a long dark tail. The shop: dense, short, bright.
    N.verbOut.buffer = make(1.4, 11, { bright: 5200, dark: 700, early: [[0.021, 0.5], [0.047, 0.35], [0.083, 0.3], [0.131, 0.22], [0.19, 0.15]], density: 0.8 });
    N.verbIn.buffer = make(0.8, 23, { bright: 7000, dark: 1600, early: [[0.007, 0.6], [0.013, 0.5], [0.019, 0.45], [0.026, 0.35]] });
  }

  // ---- voices --------------------------------------------------------------------------------------

  const lastPlay = new Map(); // name → ctx time of the last start
  const cursor = new Map(); // name → last variant used
  let lastImpact = -1;
  const tmpV = new THREE.Vector3();

  function countPlaying(pool, name, now) {
    let n = 0;
    for (const ch of pool) if (ch.name === name && ch.end > now) n++;
    return n;
  }

  function pickChannel(pool, name, prio, max, now) {
    let oldestSame = null;
    let free = null;
    let victim = null;
    let same = 0;
    for (const ch of pool) {
      const busy = ch.end > now;
      if (busy && ch.name === name) {
        same++;
        if (!oldestSame || ch.start < oldestSame.start) oldestSame = ch;
      }
      if (!busy) {
        if (!free) free = ch;
      } else if (ch.prio <= prio && (!victim || ch.prio < victim.prio || (ch.prio === victim.prio && ch.start < victim.start))) {
        victim = ch;
      }
    }
    if (max && same >= max) return oldestSame;
    return free || victim;
  }

  function release(ch, now, tau = 0.004) {
    if (!ch.src) return;
    try {
      ch.g.gain.setTargetAtTime(0, now, tau);
      ch.src.stop(now + tau * 8);
    } catch (err) {
      /* it had already stopped */
    }
    ch.src = null;
    ch.end = 0;
  }

  function nextVariant(name, n) {
    let v = ((cursor.get(name) ?? -1) + 1) % n;
    if (n > 2 && rnd() < 0.3) v = (v + 1) % n;
    cursor.set(name, v);
    return v;
  }

  /** Air absorption: far sounds lose their top. */
  const airCutoff = (d) => clamp(20000 * Math.exp(-d / 48), 1600, 20000);

  class PlayHandle {
    constructor(ch, src, g) {
      this.ch = ch;
      this.src = src;
      this.g = g;
    }
    get playing() {
      return this.ch.src === this.src && this.ch.end > clock();
    }
    stop(fade = 0.03) {
      if (this.ch.src === this.src) release(this.ch, ctx.currentTime, Math.max(0.002, fade / 4));
    }
    setVolume(v) {
      if (this.ch.src === this.src) this.g.gain.setTargetAtTime(Math.max(0, v), ctx.currentTime, 0.02);
    }
    setPitch(r) {
      if (this.ch.src === this.src) this.src.playbackRate.setTargetAtTime(clamp(r, 0.25, 4), ctx.currentTime, 0.02);
    }
    setPos(v) {
      if (this.ch.src === this.src && this.ch.spatial) placePanner(this.ch.panner, v);
    }
  }

  function placePanner(p, v) {
    if (p.positionX) {
      p.positionX.value = v.x;
      p.positionY.value = v.y;
      p.positionZ.value = v.z;
    } else p.setPosition(v.x, v.y, v.z);
  }

  /**
   * One-shot. opts: {pos, volume, pitch, delay (s), bus (override), ref, roll, prio}. Returns a handle or
   * null (not unlocked, not rendered yet, rate-limited, culled, or no voice free for its priority).
   */
  const counts = { played: {}, refused: {} }; // debug: what the game asked for

  function play(name, o = {}) {
    const h = playNow(name, o);
    const k = h ? counts.played : counts.refused;
    k[name] = (k[name] || 0) + 1;
    return h;
  }

  function playNow(name, o) {
    if (!unlocked || !ctx) return null;
    const def = SOUNDS[name];
    if (!def) return null;
    const busName = o.bus || def.bus;
    if (paused && busName !== 'dry' && busName !== 'music') return null;
    const now = clock();
    if (def.gap && now - (lastPlay.get(name) ?? -1e9) < def.gap) return null;
    if (name.startsWith('imp_')) {
      if (now - lastImpact < 0.022) return null;
      lastImpact = now;
    }
    let dist = 0;
    const spatial = !!o.pos && POOLS[busName] && POOLS[busName][1] > 0;
    if (o.pos) {
      dist = tmpV.copy(o.pos).distanceTo(listenerPos);
      if (dist > (def.cull || CULL)) return null;
    }
    const list = ready(name);
    if (!list) return null;
    const pool = pools[busName] && (spatial ? pools[busName].spatial : pools[busName].flat);
    if (!pool || !pool.length) return null;
    const prio = o.prio ?? def.prio ?? 5;
    const ch = pickChannel(pool, name, prio, def.max || 0, now);
    if (!ch) return null;
    const stolen = ch.end > now;
    if (stolen) release(ch, ctx.currentTime);

    const buf = list[nextVariant(name, list.length)] || list[0];
    const jitter = def.jitter ?? DEFAULT_JITTER;
    const rate = clamp((o.pitch || 1) * (1 + (rnd() * 2 - 1) * jitter), 0.25, 4);
    const vol = (def.vol ?? 1) * (o.volume ?? 1) * (1 - rnd() * 0.08);
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.playbackRate.value = rate;
    const g = ctx.createGain();
    g.gain.value = vol;
    src.connect(g).connect(ch.out);
    if (ch.spatial) {
      ch.panner.refDistance = o.ref ?? def.ref ?? 3;
      ch.panner.rolloffFactor = o.roll ?? def.roll ?? 1;
      placePanner(ch.panner, o.pos);
      ch.filter.frequency.value = nyq(airCutoff(dist));
    }
    const lead = (o.delay || 0) + (stolen ? 0.006 : 0);
    src.start(ctx.currentTime + lead);
    src.onended = () => {
      if (ch.src === src) {
        ch.src = null;
        ch.end = 0;
      }
      g.disconnect();
    };
    ch.src = src;
    ch.g = g;
    ch.name = name;
    ch.prio = prio;
    ch.start = now + lead;
    ch.end = now + lead + buf.duration / rate;
    lastPlay.set(name, now);
    return new PlayHandle(ch, src, g);
  }

  // ---- loops ---------------------------------------------------------------------------------------

  const loops = new Set();

  class LoopHandle {
    constructor(name, o) {
      this.name = name;
      this.pos = o.pos ? new THREE.Vector3().copy(o.pos) : null;
      this.vol = o.volume ?? 1;
      this.rate = o.pitch ?? 1;
      this.phaseLock = !!o.phaseLock;
      this.busName = o.bus || (SOUNDS[name] && SOUNDS[name].bus) || 'world';
      this.src = null;
      this.g = null;
      this.panner = null;
      this.filter = null;
      this.stopped = false;
      this.cut = 0;
    }
    setPos(v) {
      if (!v) return;
      if (!this.pos) this.pos = new THREE.Vector3();
      this.pos.copy(v);
      if (this.panner) placePanner(this.panner, this.pos);
    }
    setVolume(x) {
      const v = Math.max(0, +x || 0);
      if (Math.abs(v - this.vol) < 0.002) return;
      this.vol = v;
      if (this.g) this.g.gain.setTargetAtTime(v * (SOUNDS[this.name].vol ?? 1), ctx.currentTime, 0.06);
    }
    setPitch(r) {
      const v = clamp(+r || 1, 0.25, 4);
      if (Math.abs(v - this.rate) < 0.002) return;
      this.rate = v;
      if (this.src) this.src.playbackRate.setTargetAtTime(v, ctx.currentTime, 0.05);
    }
    stop(fade = 0.12) {
      if (this.stopped) return;
      this.stopped = true;
      loops.delete(this);
      if (!this.src) return;
      const now = ctx.currentTime;
      const src = this.src;
      const nodes = [this.g, this.filter, this.panner];
      this.g.gain.setTargetAtTime(0, now, Math.max(0.005, fade / 3));
      src.stop(now + fade + 0.05);
      src.onended = () => nodes.forEach((n) => n && n.disconnect());
      this.src = null;
    }
    get playing() {
      return !!this.src;
    }
    /** Starts once the context and the buffer exist (called from update). */
    tryStart() {
      if (this.src || this.stopped || !unlocked) return;
      const list = ready(this.name, false);
      if (!list) return;
      const def = SOUNDS[this.name];
      const buf = list[nextVariant(this.name, list.length)] || list[0];
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.loop = true;
      src.playbackRate.value = this.rate;
      const g = ctx.createGain();
      g.gain.value = 0;
      src.connect(g);
      const out = bus[this.busName] || bus.world;
      if (this.pos && this.busName !== 'dry' && this.busName !== 'music') {
        this.filter = lowpass(20000, 0.5);
        this.panner = makePanner();
        this.panner.refDistance = def.ref ?? 3;
        this.panner.rolloffFactor = def.roll ?? 1;
        placePanner(this.panner, this.pos);
        g.connect(this.filter).connect(this.panner).connect(out);
      } else g.connect(out);
      const now = ctx.currentTime;
      const at = now + 0.02;
      let offset = rnd() * buf.duration * 0.9;
      if (this.phaseLock && conductor && conductor.t0 !== null) offset = conductor.phase(at) % buf.duration;
      src.start(at, offset);
      g.gain.setTargetAtTime(this.vol * (def.vol ?? 1), at, 0.08);
      this.src = src;
      this.g = g;
    }
    /** Air absorption for far loops, refreshed by update. */
    air() {
      if (!this.filter || !this.pos) return;
      const c = airCutoff(this.pos.distanceTo(listenerPos));
      if (Math.abs(c - this.cut) > 200) {
        this.cut = c;
        this.filter.frequency.setTargetAtTime(nyq(c), ctx.currentTime, 0.1);
      }
    }
  }

  function loop(name, o = {}) {
    const h = new LoopHandle(name, o);
    if (!SOUNDS[name]) {
      h.stopped = true;
      return h;
    }
    loops.add(h);
    h.tryStart();
    return h;
  }

  // ---- mix state -----------------------------------------------------------------------------------

  let volume = clamp(Number(G.settings && G.settings.get ? G.settings.get('volume') : 0.8) || 0, 0, 1);
  let paused = false;
  let interior = 0;
  let interiorOverride = -1;
  let interiorUntil = -1;
  let muffle = 0;
  let muffleHold = 0; // the floor the muffle settles to (0.85 while dead)
  let ambState = 1; // title 0.6, dead 0.7, else 1
  const ducks = []; // {depth, until, release, music}
  let musicDip = 1;
  let trainDuck = 1;
  const listenerPos = new THREE.Vector3(0, 1.7, 0);
  const fwd = new THREE.Vector3();
  const up = new THREE.Vector3();
  const last = { muffle: -1, pause: -1, amb: -1, music: -1, ambLevel: -1, ambLp: -1, verb: -1, musicLp: -1, musicDip: -1 };

  /** Gunfire and blasts duck the ambience and the music: depth 0..1, held `hold` s, released with τ `rel`. */
  function duck(depth, hold, rel, musicToo = true) {
    if (!ctx) return;
    ducks.push({ depth, until: clock() + hold, rel, music: musicToo });
    if (ducks.length > 16) ducks.shift();
  }

  /** Moves a mix parameter: time constant `down` when it falls, `up` when it rises. */
  function setP(key, param, value, down, up = down) {
    if (Math.abs(value - last[key]) < 0.002) return;
    param.setTargetAtTime(value, ctx.currentTime, value < last[key] ? down : up);
    last[key] = value;
  }

  function updateMix(dt) {
    const now = clock();
    // Interior: the level's boxes around the camera, or setInterior() while it is being called.
    let want = 0;
    if (G.time.real < interiorUntil && interiorOverride >= 0) want = interiorOverride;
    else if (G.level && typeof G.level.interiorAt === 'function') want = clamp(+G.level.interiorAt(listenerPos) || 0, 0, 1);
    interior += (want - interior) * Math.min(1, dt * 3);

    // Ducks.
    let ambD = 1;
    let musD = 1;
    let rel = 0.1;
    for (let i = ducks.length - 1; i >= 0; i--) {
      const d = ducks[i];
      if (now > d.until + d.rel * 4) {
        ducks.splice(i, 1);
        continue;
      }
      if (now <= d.until) {
        ambD = Math.min(ambD, d.depth);
        if (d.music) musD = Math.min(musD, d.depth);
      }
      rel = Math.max(rel, d.rel);
    }
    musicDip += (1 - musicDip) * Math.min(1, dt * 3.5);

    // Muffle: damage, blasts, death.
    muffle += (muffleHold - muffle) * Math.min(1, dt * (muffleHold > 0 ? 3 : 0.9));

    setP('muffle', N.muffle.frequency, nyq(20000 * Math.pow(0.03, muffle)), 0.02, 0.08);
    setP('pause', N.pause.gain, paused ? 0 : 1, 0.08);
    setP('amb', N.ambDuck.gain, ambD * trainDuck, 0.012, rel);
    setP('music', N.musicDuck.gain, musD * (0.6 + 0.4 * trainDuck) * (paused ? 0.45 : 1), 0.012, rel);
    setP('musicDip', N.musicDip.gain, musicDip, 0.03, 0.15);
    setP('musicLp', N.musicLp.frequency, nyq(paused ? 1300 : 20000), 0.2);
    setP('ambLevel', N.ambLevel.gain, ambState * (paused ? 0 : 1) * (1 - 0.55 * interior), 0.6, 0.4);
    setP('ambLp', N.ambLp.frequency, nyq(20000 * Math.pow(0.08, interior)), 0.2);
    if (Math.abs(interior - last.verb) > 0.01) {
      last.verb = interior;
      N.verbOutGain.gain.setTargetAtTime(0.8 * (1 - 0.9 * interior), now, 0.1);
      N.verbInGain.gain.setTargetAtTime(0.9 * interior, now, 0.1);
    }
  }

  function updateListener() {
    const cam = G.camera;
    if (!cam) return;
    cam.getWorldPosition(listenerPos);
    cam.getWorldDirection(fwd);
    up.set(0, 1, 0).applyQuaternion(cam.quaternion);
    const L = ctx.listener;
    if (L.positionX) {
      L.positionX.value = listenerPos.x;
      L.positionY.value = listenerPos.y;
      L.positionZ.value = listenerPos.z;
      L.forwardX.value = fwd.x;
      L.forwardY.value = fwd.y;
      L.forwardZ.value = fwd.z;
      L.upX.value = up.x;
      L.upY.value = up.y;
      L.upZ.value = up.z;
    } else {
      L.setPosition(listenerPos.x, listenerPos.y, listenerPos.z);
      L.setOrientation(fwd.x, fwd.y, fwd.z, up.x, up.y, up.z);
    }
  }

  // ---- unlock --------------------------------------------------------------------------------------

  const frozen = G.params && G.params.step === '1' && G.params.audiort !== '1';
  /** Voice bookkeeping clock: the context's, or the simulation's while the context is held (harness). */
  const clock = () => (frozen ? G.time.t : ctx.currentTime);

  function unlock() {
    try {
      if (!ctx) {
        ctx = new AC({ latencyHint: 'interactive' });
        if (!canConstruct) {
          for (const r of pendingRaw.splice(0)) store(r);
        }
        buildGraph();
        buildImpulses();
        ambience.unlock();
      }
      // Under the harness (?step=1) simulated time has nothing to do with the clock, and a real-time
      // graph only burns the shared CPU: the context is built and kept suspended (?audiort=1 overrides).
      if (frozen) ctx.suspend().catch(() => {});
      else if (ctx.state === 'suspended') ctx.resume().catch(() => {});
      if (!unlocked) {
        unlocked = true;
        queue.start();
        conductor.start(ctx.currentTime + 0.15);
        for (const h of loops) h.tryStart();
      }
    } catch (err) {
      console.warn('[audio] could not start WebAudio:', err);
    }
  }

  // The first gesture anywhere starts the sound (menus also call unlock()).
  // It stays on: a phone can suspend the context later (a call, the lock screen) and only a gesture resumes it.
  const gesture = () => {
    if (!ctx || (ctx.state !== 'running' && !frozen)) unlock();
  };
  for (const e of ['pointerdown', 'keydown', 'touchend']) window.addEventListener(e, gesture, true);
  document.addEventListener('visibilitychange', () => {
    if (!ctx) return;
    if (document.hidden) ctx.suspend().catch(() => {});
    else if (unlocked && !frozen) ctx.resume().catch(() => {});
  });

  // ---- shared internals for ambience / react -----------------------------------------------------

  const A = {
    G,
    get ctx() {
      return ctx;
    },
    get unlocked() {
      return unlocked;
    },
    get paused() {
      return paused;
    },
    get interior() {
      return interior;
    },
    get conductor() {
      return conductor;
    },
    listener: listenerPos,
    now: () => clock(),
    forward: fwd,
    play,
    loop,
    duck,
    rnd,
    muffleTo(m, hold = muffleHold) {
      muffle = Math.max(muffle, clamp(m, 0, 1));
      muffleHold = hold;
    },
    dipMusic(v) {
      musicDip = Math.min(musicDip, v);
    },
    setTrainDuck(v) {
      trainDuck = v;
    },
    setAmbState(v) {
      ambState = v;
    },
    music(mode) {
      if (conductor) conductor.setMode(mode);
      else A.pendingMode = mode;
    },
    meter(level, add = 0) {
      if (!conductor) return;
      if (level) conductor.bump(level);
      if (add) conductor.add(add);
    },
  };
  ambience = createAmbience(A);
  A.ambience = ambience;
  const reactor = wireEvents(A);

  // ---- API -----------------------------------------------------------------------------------------

  let intensity = 0.15;

  const api = {
    unlock,
    setVolume(v) {
      volume = clamp(+v || 0, 0, 1);
      if (N.volume) N.volume.gain.setTargetAtTime(volume, ctx.currentTime, 0.03);
    },
    setPaused(on) {
      paused = !!on;
      if (paused) reactor.pause();
    },
    setInterior(f) {
      interiorOverride = clamp(+f || 0, 0, 1);
      interiorUntil = G.time.real + 0.25;
    },
    setMusicIntensity(x) {
      intensity = clamp(+x || 0, 0, 1);
      if (conductor) conductor.setIntensity(intensity);
    },
    play,
    loop,
    sting(name) {
      if (!conductor || !unlocked) return;
      conductor.sting(name, ctx.currentTime);
      if (name === 'dead') A.muffleTo(1, 0.85);
    },
    update(dt) {
      if (!ctx || !unlocked) return;
      const step = Math.min(0.1, dt || 0);
      updateListener();
      updateMix(step);
      if (A.pendingMode) {
        conductor.setMode(A.pendingMode);
        A.pendingMode = null;
      }
      conductor.setIntensity(intensity);
      conductor.update(ctx.currentTime, step);
      for (const h of loops) {
        if (!h.src) h.tryStart();
        else h.air();
      }
      ambience.update(step);
      reactor.update(step);
    },
    /** Debug and verification helpers (not part of the contract). */
    debug: {
      get ctx() {
        return ctx;
      },
      get conductor() {
        return conductor;
      },
      get queued() {
        return queue.size;
      },
      get bytes() {
        return bytes;
      },
      get interior() {
        return interior;
      },
      get muffle() {
        return muffle;
      },
      counts: () => counts,
      loops: () => [...loops].map((h) => ({ name: h.name, playing: !!h.src, vol: h.vol })),
      ready: (name) => !!(buffers.get(name) && buffers.get(name).length),
      names: () => Object.keys(SOUNDS),
      /** Renders everything still queued, now (tests). */
      flush() {
        while (queue.run(250) > 0) if (collect) collect();
      },
      voices() {
        const now = ctx ? clock() : 0;
        const out = {};
        for (const [b, p] of Object.entries(pools)) out[b] = [...p.flat, ...p.spatial].filter((c) => c.end > now).length;
        return out;
      },
      /** Peak / RMS of every rendered variant 0, as played at default volume (bus gain × vol). */
      measureAll() {
        const rows = [];
        for (const [name, list] of buffers) {
          const buf = list[0];
          if (!buf) continue;
          const m = measure(buf.getChannelData(0));
          const def = SOUNDS[name];
          const k = (BUS_GAIN[def.bus] ?? 1) * (def.vol ?? 1);
          const n = Math.min(buf.length, Math.round(buf.sampleRate * 0.1));
          const head = measure(buf.getChannelData(0).subarray(0, n));
          rows.push({ name, bus: def.bus, secs: +buf.duration.toFixed(2), peak: +(m.peak * k).toFixed(3), rms: +(m.rms * k).toFixed(4), punch: +(head.rms * k).toFixed(4) });
        }
        return rows;
      },
      /**
       * Renders `bars` of the score offline at a fixed intensity. opts: {mode, solo (one stem alone),
       * late (stems held back and joined off the grid at bar 1.37), keep (return the samples)}.
       */
      async renderMusic(I, bars = 8, opts = {}) {
        const sr = 22050;
        const off = new OfflineAudioContext(2, Math.round(bars * BAR * sr) + 256, sr);
        const getBuf = (name) => {
          const list = buffers.get(name);
          return list ? list[0] : null;
        };
        const busGain = off.createGain(); // as the music bus has it in the game
        busGain.gain.value = BUS_GAIN.music;
        busGain.connect(off.destination);
        const c = createConductor(off, busGain, getBuf, { rnd: seeded(5) });
        c.setMode(opts.mode || 'play');
        c.setIntensity(I, true);
        const late = opts.late || [];
        for (const n of late) c.stems[n].src = 'held';
        c.start(0);
        c.update(0, 0.016);
        if (opts.solo) {
          for (const n of STEM_NAMES) {
            const p = c.stems[n].gain.gain;
            p.cancelScheduledValues(0);
            p.value = n === opts.solo ? 1 : 0;
            c.stems[n].last = p.value;
          }
        }
        if (late.length) {
          const t = (Math.round((BAR * 1.37 * sr) / 128) * 128) / sr;
          off.suspend(t).then(() => {
            for (const n of late) c.stems[n].src = null;
            c.update(t, 0.016);
            off.resume();
          });
        }
        const out = await off.startRendering();
        const L = out.getChannelData(0);
        const R = out.getChannelData(1);
        const mono = new Float32Array(L.length);
        for (let i = 0; i < L.length; i++) mono[i] = 0.5 * (L[i] + R[i]);
        return { peak: Math.max(measure(L).peak, measure(R).peak), rms: measure(mono).rms, sr, data: opts.keep ? mono : null };
      },
      layerGains,
      stems: STEM_NAMES,
      LOOP,
      BAR,
    },
  };
  if (G.events) {
    G.events.on('settings:change', (p) => {
      if (p && p.key === 'volume') api.setVolume(p.value);
    });
  }

  // Synthesis starts once the boot is over (it would only slow it down), or at the first unlock. Under the
  // harness (?step=1) it waits for an unlock: most runs never make a sound and the CPU is shared.
  if (!frozen) {
    if (G.events) G.events.on('boot:done', () => queue.start());
    setTimeout(() => queue.start(), 8000);
  }
  return api;
}
