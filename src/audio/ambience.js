// The block as a sound: a day bed and a night bed crossfaded by G.atmos.time, wind in the El steel, neon
// buzz and steam hiss at the nearest emitters, far one-shots on their own clocks (a bus, kids, pigeons, a
// jackhammer, the chime by day; a siren, a dog, a horn by night), the El train, and the boombox at each
// live reel case, in time with the score.

const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);

// [name, min gap, max gap, first after, placement]
const SCHEDULE = {
  day: [
    ['horn_far', 14, 34, 6, 'far'],
    ['bus_pull', 32, 70, 18, 'street'],
    ['kids_far', 24, 52, 10, 'far'],
    ['pigeons', 15, 36, 4, 'roof'],
    ['jackhammer', 48, 100, 28, 'far'],
    ['chime_far', 90, 170, 40, 'far'],
    ['siren_far', 85, 160, 55, 'far'],
    ['dog_far', 100, 180, 70, 'far'],
  ],
  night: [
    ['siren_far', 55, 115, 16, 'far'],
    ['dog_far', 24, 55, 9, 'far'],
    ['horn_far', 40, 85, 25, 'far'],
  ],
};

const EMITTERS = { neon: { sound: 'neon_buzz', radius: 15, max: 3 }, steam: { sound: 'steam', radius: 24, max: 3 } };

export function createAmbience(A) {
  const { G } = A;
  const THREE = G.THREE;
  const tmp = new THREE.Vector3();
  let beds = null;
  let dayMix = 1;
  let gust = 0.6;
  let gustTarget = 0.6;
  let gustTimer = 4;
  let emitTimer = 0;
  let timers = null;
  let timersFor = '';
  const sources = { neon: null, steam: null }; // world positions, read from the level once
  const active = { neon: new Map(), steam: new Map() }; // index → loop handle
  const reels = new Map(); // objective id → boombox loop
  const train = { phase: null, t: 0, dur: 0, rumble: null, clack: null, squeal: -1, duck: 1 };

  const isDay = () => {
    const t = (G.atmos && G.atmos.time) || (G.settings && G.settings.get && G.settings.get('time')) || 'day';
    return t !== 'night';
  };

  function readSources() {
    const L = G.level;
    sources.neon = [];
    sources.steam = [];
    if (!L) return;
    const vec = (p) => (p && Number.isFinite(+p.x) && Number.isFinite(+p.z) ? new THREE.Vector3(+p.x, +p.y || 0, +p.z) : null);
    if (Array.isArray(L.lamps)) for (const l of L.lamps) if (l && l.kind === 'neon' && vec(l.pos)) sources.neon.push(vec(l.pos));
    if (Array.isArray(L.steam)) for (const p of L.steam) if (vec(p)) sources.steam.push(vec(p));
  }

  function resetTimers(which) {
    timersFor = which;
    timers = SCHEDULE[which].map(([name, a, b, first, where]) => ({ name, a, b, t: first * (0.7 + 0.6 * A.rnd()), where }));
  }

  /** Somewhere off the block in a random direction (pigeons: a ledge nearby; a bus: down the avenue). */
  function placeFar(where) {
    const L = A.listener;
    const ang = A.rnd() * Math.PI * 2;
    if (where === 'roof') {
      const d = 9 + A.rnd() * 18;
      return tmp.set(L.x + Math.cos(ang) * d, 7 + A.rnd() * 9, L.z + Math.sin(ang) * d);
    }
    if (where === 'street') {
      const d = 45 + A.rnd() * 60;
      return tmp.set(L.x + (A.rnd() < 0.5 ? -d : d), 1.5, L.z + (A.rnd() * 2 - 1) * 12);
    }
    const d = 60 + A.rnd() * 90;
    return tmp.set(L.x + Math.cos(ang) * d, 2 + A.rnd() * 14, L.z + Math.sin(ang) * d);
  }

  function updateTimers(dt) {
    const which = isDay() ? 'day' : 'night';
    if (which !== timersFor) resetTimers(which);
    for (const tm of timers) {
      tm.t -= dt;
      if (tm.t > 0) continue;
      tm.t = tm.a + A.rnd() * (tm.b - tm.a);
      const pos = placeFar(tm.where);
      A.play(tm.name, { pos, volume: 0.75 + A.rnd() * 0.25, pitch: tm.name === 'siren_far' && A.rnd() < 0.3 ? 0.92 : 1 });
    }
  }

  function updateEmitters() {
    if (!sources.neon) readSources();
    const L = A.listener;
    const day = dayMix;
    for (const kind of ['neon', 'steam']) {
      const spec = EMITTERS[kind];
      const list = sources[kind];
      const near = [];
      for (let i = 0; i < list.length; i++) {
        const d = list[i].distanceTo(L);
        if (d < spec.radius) near.push([d, i]);
      }
      near.sort((a, b) => a[0] - b[0]);
      const keep = new Set(near.slice(0, spec.max).map((e) => e[1]));
      for (const [i, h] of active[kind]) {
        if (!keep.has(i)) {
          h.stop(0.5);
          active[kind].delete(i);
        }
      }
      for (const i of keep) {
        if (!active[kind].has(i)) active[kind].set(i, A.loop(spec.sound, { pos: list[i], volume: 0 }));
        // Neon hums louder at night, when the street is quiet enough to hear it.
        active[kind].get(i).setVolume(kind === 'neon' ? 0.5 + 0.5 * (1 - day) : 1);
      }
    }
  }

  function updateWind(dt) {
    gustTimer -= dt;
    if (gustTimer <= 0) {
      gustTimer = 3 + A.rnd() * 6;
      gustTarget = 0.15 + A.rnd() * 0.85;
    }
    gust += (gustTarget - gust) * Math.min(1, dt * 0.5);
    // Louder close to the El's steel.
    let near = 0;
    const el = G.level && G.level.el;
    if (el && Number.isFinite(el.minX)) {
      const L = A.listener;
      const dx = Math.max(el.minX - L.x, 0, L.x - el.maxX);
      const dz = Math.max(el.minZ - L.z, 0, L.z - el.maxZ);
      near = clamp(1 - Math.hypot(dx, dz) / 25, 0, 1);
    }
    beds.wind.setVolume((0.35 + 0.25 * (1 - dayMix)) * (0.45 + 0.75 * near) * (0.3 + 0.7 * gust));
    beds.wind.setPitch(0.9 + 0.22 * gust);
  }

  // ---- the El train --------------------------------------------------------------------------------

  function trainPos() {
    const t = G.atmos && G.atmos.train;
    if (t && Number.isFinite(t.lo) && Number.isFinite(t.hi)) {
      return tmp.set(clamp(A.listener.x, Math.min(t.lo, t.hi), Math.max(t.lo, t.hi)), Number.isFinite(t.y) ? t.y : 7, Number.isFinite(t.z) ? t.z : 0);
    }
    const el = G.level && G.level.el;
    return tmp.set(A.listener.x, el && Number.isFinite(el.y) ? el.y : 7, el ? (el.minZ + el.maxZ) / 2 : 0);
  }

  function onTrain(p) {
    if (!A.unlocked || !p) return;
    const phase = p.phase;
    if (phase === 'approach' || (phase === 'over' && !train.rumble)) {
      if (!train.rumble) {
        const pos = trainPos();
        train.rumble = A.loop('train_rumble', { pos, volume: 0 });
        train.clack = A.loop('train_clack', { pos, volume: 0 });
      }
    }
    train.phase = phase;
    train.t = 0;
    train.dur = Math.max(0.5, +p.duration || 8);
    train.squeal = phase === 'over' && A.rnd() < 0.7 ? train.dur * (0.2 + A.rnd() * 0.4) : -1;
  }

  function updateTrain(dt) {
    if (!train.phase) {
      train.duck += (1 - train.duck) * Math.min(1, dt * 1.5);
      A.setTrainDuck(train.duck);
      return;
    }
    train.t += dt;
    const u = clamp(train.t / train.dur, 0, 1);
    let vol = 1;
    if (train.phase === 'approach') vol = 0.2 + 0.8 * u;
    else if (train.phase === 'gone') vol = 1 - u;
    const t = G.atmos && G.atmos.train;
    const rate = t && t.speed ? clamp(t.speed / 16.5, 0.5, 1.6) : 1;
    const pos = trainPos();
    if (train.rumble) {
      train.rumble.setPos(pos);
      train.rumble.setVolume(vol);
      train.clack.setPos(pos);
      train.clack.setVolume(vol * (train.phase === 'approach' ? u : 1));
      train.clack.setPitch(rate);
    }
    if (train.squeal >= 0 && train.t >= train.squeal) {
      train.squeal = -1;
      A.play('train_squeal', { pos, volume: 0.8 });
    }
    const want = train.phase === 'over' ? 0.72 : train.phase === 'approach' ? 1 - 0.2 * u : 0.8 + 0.2 * u;
    train.duck += (want - train.duck) * Math.min(1, dt * 1.5);
    A.setTrainDuck(train.duck);
    if (train.phase === 'gone' && (u >= 1 || (t && t.active === false && train.t > 1))) stopTrain();
  }

  function stopTrain() {
    if (train.rumble) {
      train.rumble.stop(1.2);
      train.clack.stop(0.8);
    }
    train.rumble = train.clack = null;
    train.phase = null;
  }

  // ---- reel boomboxes ------------------------------------------------------------------------------

  function startReels() {
    for (const h of reels.values()) h.stop(0.3);
    reels.clear();
    const objs = G.level && G.level.objectives;
    if (!Array.isArray(objs) || (G.game && G.game.mode === 'holdout')) return;
    for (const o of objs) {
      if (!o || !o.pos) continue;
      const pos = new THREE.Vector3().copy(o.pos);
      pos.y += 0.6;
      reels.set(o.id, A.loop('boombox', { pos, volume: 0.95, phaseLock: true }));
    }
  }

  function reelTaken(id) {
    const h = reels.get(id);
    if (!h) return;
    h.stop(0.25);
    reels.delete(id);
  }

  return {
    attach() {},
    unlock() {
      beds = {
        day: A.loop('bed_day', { volume: 0 }),
        night: A.loop('bed_night', { volume: 0 }),
        wind: A.loop('wind_el', { volume: 0 }),
      };
      dayMix = isDay() ? 1 : 0;
      resetTimers(dayMix ? 'day' : 'night');
      startReels();
    },
    update(dt) {
      if (!beds) return;
      dayMix += ((isDay() ? 1 : 0) - dayMix) * Math.min(1, dt * 0.5);
      beds.day.setVolume(dayMix);
      beds.night.setVolume(1 - dayMix);
      updateWind(dt);
      emitTimer -= dt;
      if (emitTimer <= 0) {
        emitTimer = 0.5;
        updateEmitters();
      }
      updateTrain(dt);
      const s = G.game && G.game.state;
      if (!A.paused && s !== 'dead' && s !== 'paused') updateTimers(dt);
    },
    onTrain,
    startReels,
    reelTaken,
    stopTrain,
    get reels() {
      return reels;
    },
  };
}
