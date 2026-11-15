// The music player. Every stem is an eight-bar loop started on one shared clock (t0); a stem whose buffer
// arrives late joins at the right offset, so the layers stay phase-locked whatever the render order.
// A lookahead clock places everything else on the grid: stings on the next beat, the riser so that it
// peaks on a bar line, the impact on that downbeat. Works on any BaseAudioContext, so the same code can be
// rendered offline (audio.debug.renderMusic) to check levels and timing.

import { BAR, BEAT, LOOP, RISER_SECS, STEMS } from './music.js';

export const STEM_NAMES = Object.keys(STEMS);

const smooth = (a, b, x) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

/**
 * Stem gains for an intensity 0..1 and a mode ('title' | 'play' | 'dead' | 'complete'). `gate` (0..1)
 * holds the top layers back until a riser's impact lands. drumCut = drum low-pass in Hz.
 *   0.15  filtered drums, a sketch of the bass, crackle
 *   0.6   full drums and hats, bass, keys
 *   1.0   everything: string stabs and the bell hook on top
 */
export function layerGains(I, mode = 'play', gate = 1, out = {}) {
  if (mode === 'dead') {
    for (const n of STEM_NAMES) out[n] = 0;
    out.crackle = 0.55;
    out.keys = 0.16;
    out.drumCut = 400;
    return out;
  }
  const o = smooth(0.25, 0.55, I);
  const k = smooth(0.35, 0.6, I);
  const r = smooth(0.75, 0.95, I) * gate;
  out.drums = 0.78 + 0.22 * o;
  out.hats = 0.1 + 0.9 * o;
  out.bass = 0.5 + 0.5 * o;
  out.keys = mode === 'title' ? Math.max(k, 0.55) : k * (1 - 0.1 * r);
  out.strings = r;
  out.bell = r * 0.9;
  out.crackle = 0.6 - 0.3 * o;
  out.drumCut = 700 * Math.pow(26, o);
  return out;
}

/** Tier with hysteresis: 2 at I ≥ 0.8 (held down to 0.68), 1 at I ≥ 0.4 (held to 0.32), else 0. */
export function nextTier(tier, I) {
  if (I >= 0.8 || (tier === 2 && I >= 0.68)) return 2;
  if (I >= 0.4 || (tier >= 1 && I >= 0.32)) return 1;
  return 0;
}

/** The first grid time (step = BAR or BEAT) at or after `t + ahead`, on a clock that started at t0. */
export function nextGrid(t0, t, ahead, step) {
  return t0 + Math.ceil((t + ahead - t0) / step - 1e-9) * step;
}

export function createConductor(ctx, dest, getBuffer, opts = {}) {
  const rnd = opts.rnd || Math.random;
  const trim = opts.trim ?? 0.9;

  const master = ctx.createGain(); // everything the score makes
  master.gain.value = trim;
  master.connect(dest);
  const stemBus = ctx.createGain(); // ducks under stings and before an impact
  stemBus.connect(master);
  const drumLp = ctx.createBiquadFilter();
  drumLp.type = 'lowpass';
  drumLp.Q.value = 0.8;
  drumLp.frequency.value = 700;
  drumLp.connect(stemBus);
  const oneShots = ctx.createGain();
  oneShots.connect(master);

  const stems = {};
  for (const name of STEM_NAMES) {
    const gain = ctx.createGain();
    gain.gain.value = 0;
    let head = gain;
    if (STEMS[name].pan && ctx.createStereoPanner) {
      const p = ctx.createStereoPanner();
      p.pan.value = STEMS[name].pan;
      gain.connect(p);
      head = p;
    }
    head.connect(name === 'drums' || name === 'hats' ? drumLp : stemBus);
    stems[name] = { gain, src: null, last: -1 };
  }

  const st = {
    t0: null,
    mode: 'title',
    target: 0.15, // what the game asks for
    meter: 0.15, // the engine's own combat meter
    I: 0.15, // smoothed value in use
    tier: 0,
    gate: 1,
    impactAt: 0, // a riser in flight lands here (0 = none)
    riserSrc: null,
    impactSrc: null,
    lastRiser: -1e9,
    lastSting: -1e9,
    final: false,
    forceRiser: false,
    duckUntil: 0,
  };
  const g = {};

  function startStems(now) {
    if (st.t0 === null) return;
    for (const name of STEM_NAMES) {
      const s = stems[name];
      if (s.src) continue;
      const buf = getBuffer(`stem_${name}`);
      if (!buf) continue;
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.loop = true;
      src.connect(s.gain);
      const at = st.t0 >= now ? st.t0 : now + 0.02;
      const offset = (((at - st.t0) % LOOP) + LOOP) % LOOP;
      src.start(at, Math.min(offset, buf.duration - 1e-4));
      s.src = src;
    }
  }

  function oneShot(name, at, gain = 1, offset = 0) {
    const buf = getBuffer(name);
    if (!buf) return null;
    const src = ctx.createBufferSource();
    src.buffer = buf;
    const g1 = ctx.createGain();
    g1.gain.value = gain;
    src.connect(g1).connect(oneShots);
    src.start(Math.max(at, ctx.currentTime), Math.max(0, offset));
    src.onended = () => g1.disconnect();
    return src;
  }

  function setParam(param, value, now, tau, last) {
    if (Math.abs(value - last) < 0.004) return last;
    param.setTargetAtTime(value, now, tau);
    return value;
  }

  /** Ducks the stems (not the stings) to `depth` from `at` for `secs`. */
  function duckStems(now, at, depth, secs) {
    const p = stemBus.gain;
    p.cancelScheduledValues(now);
    p.setTargetAtTime(depth, at, 0.06);
    p.setTargetAtTime(1, at + secs, 0.5);
    st.duckUntil = at + secs;
  }

  function cancelRiser(now) {
    for (const src of [st.riserSrc, st.impactSrc]) {
      if (!src) continue;
      try {
        src.stop(now + 0.05);
      } catch (err) {
        /* already stopped */
      }
    }
    st.riserSrc = st.impactSrc = null;
    st.impactAt = 0;
    st.gate = 1;
    for (const n of ['strings', 'bell']) stems[n].last = -1;
  }

  /** Entering the top tier: a riser that lands on a bar line, the impact, the top layers snapping in. */
  function launchRiser(now) {
    const impactAt = nextGrid(st.t0, now, now - st.lastSting < 1.5 ? 2.6 : 1.4, BAR);
    const riserStart = impactAt - RISER_SECS;
    const at = Math.max(now + 0.02, riserStart);
    st.riserSrc = oneShot('m_riser', at, 0.85, at - riserStart);
    st.impactSrc = oneShot('m_impact', impactAt, 0.8);
    st.impactAt = impactAt;
    st.gate = 0;
    st.lastRiser = now;
    // The layers dip half a second before the downbeat, then everything comes in on it.
    const p = stemBus.gain;
    p.cancelScheduledValues(now);
    p.setTargetAtTime(1, now, 0.1);
    p.setTargetAtTime(0.5, impactAt - 0.5, 0.12);
    p.setValueAtTime(1, impactAt);
    layerGains(st.I, st.mode, 1, g);
    for (const n of ['strings', 'bell']) {
      const gp = stems[n].gain.gain;
      gp.cancelScheduledValues(now);
      gp.setTargetAtTime(0, now, 0.15);
      gp.setValueAtTime(g[n], impactAt);
      stems[n].last = g[n];
    }
  }

  function update(now, dt) {
    if (st.t0 === null) return;
    startStems(now);
    // Intensity: the game's floor or the meter, whichever is higher, eased.
    st.meter = Math.max(0.15, st.meter - dt * 0.06);
    const want = st.mode === 'play' ? Math.max(st.target, st.meter) : st.mode === 'title' ? 0.15 : st.target;
    st.I += (want - st.I) * Math.min(1, dt * 2);
    if (st.mode === 'dead' || st.mode === 'complete') st.I = Math.min(st.I, 0.2);

    const tier = nextTier(st.tier, st.I);
    if (st.mode === 'play' && tier === 2 && (st.tier < 2 || st.forceRiser) && !st.impactAt) {
      if (now - st.lastRiser > 25 || st.forceRiser) launchRiser(now);
      st.forceRiser = false;
    }
    st.tier = tier;
    if (st.impactAt) {
      if (now >= st.impactAt) {
        st.impactAt = 0;
        st.gate = 1;
        st.riserSrc = st.impactSrc = null;
      } else if (st.I < 0.68 && st.impactAt - now > 0.6) {
        cancelRiser(now);
      }
    }

    layerGains(st.I, st.mode, st.gate, g);
    const tau = st.mode === 'dead' ? 0.22 : 0.5;
    for (const name of STEM_NAMES) {
      if (st.impactAt && (name === 'strings' || name === 'bell')) continue; // already scheduled
      const s = stems[name];
      s.last = setParam(s.gain.gain, g[name], now, tau, s.last);
    }
    drumLp.frequency.setTargetAtTime(Math.min(g.drumCut, ctx.sampleRate * 0.45), now, 0.35);
  }

  return {
    stems,
    state: st,
    /** Starts the clock (once). Stems join as their buffers arrive. */
    start(at = ctx.currentTime + 0.1) {
      if (st.t0 !== null) return;
      st.t0 = at;
      startStems(ctx.currentTime);
    },
    get t0() {
      return st.t0;
    },
    /** Where the loop is at time t, in seconds (boombox loops use it to start in phase). */
    phase(t) {
      return st.t0 === null ? 0 : (((t - st.t0) % LOOP) + LOOP) % LOOP;
    },
    setIntensity(x, instant = false) {
      st.target = Math.min(1, Math.max(0, +x || 0));
      if (instant) st.I = st.meter = st.target;
    },
    bump(level) {
      st.meter = Math.min(1, Math.max(st.meter, level));
    },
    add(amount) {
      st.meter = Math.min(1, st.meter + amount);
    },
    setMode(mode, now = ctx.currentTime) {
      if (mode === st.mode) return;
      if (mode === 'title' || (mode === 'play' && st.mode !== 'play')) {
        st.final = false;
        if (st.impactAt) cancelRiser(now);
      }
      if (mode === 'dead' && st.impactAt) cancelRiser(now);
      st.mode = mode;
    },
    sting(name, now = ctx.currentTime) {
      if (st.t0 === null) return null;
      if (name === 'dead') {
        st.mode = 'dead';
        cancelRiser(now);
        st.lastSting = now;
        return oneShot('sting_dead', now + 0.01, 1);
      }
      if (name === 'complete' && now - st.lastSting < 6) return null;
      const at = nextGrid(st.t0, now, 0.04, BEAT);
      const src = oneShot(`sting_${name}`, at, 1);
      if (!src) return null;
      st.lastSting = now;
      if (name === 'complete') {
        st.mode = 'complete';
        duckStems(now, at, 0.12, 7);
      } else {
        duckStems(now, at, 0.4, 3.4);
      }
      if (name === 'all') {
        st.final = true;
        st.forceRiser = true;
        st.lastRiser = -1e9;
      }
      return src;
    },
    update,
    layer: g,
    disconnect() {
      master.disconnect();
    },
  };
}
