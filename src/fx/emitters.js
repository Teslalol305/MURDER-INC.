// Emitters: things that keep making particles until they are stopped or their time is up.
//
//   steam    a soft white column drifting on the wind (manholes, vents)
//   smolder  dark wisps that thin out over the emitter's life (wreckage, a blast site)
//   embers   glowing motes carried upward
//   fire     flames, smoke and embers, with a pooled light that flickers while the camera is near
//   drip     a drop every so often, with a small splash where it lands
//   jet      the roaring tongue of flame from a lit propane valve (aimed with `dir`)
//
// A fixed number of slots; a handle is {stop(), setPos(v), setDir(v)}. Rates are "per second at full
// quality, up close" and scale like every other effect.

import { ADD, LIT } from './atlas.js';
import { DIE, BOUNCE, GRAVITY, resetSpec, spawn } from './sim.js';
import { rgb } from './shared.js';

const TAU = Math.PI * 2;
const MAX_PER_FRAME = 10; // particles one stream may emit in a single frame (long frames do not flood)
const LIGHT_NEAR = 42; // a fire takes a pooled light when the camera comes this close…
const LIGHT_FAR = 52; // …and gives it back beyond this
const LIGHT_CHECK = 0.3; // seconds between those checks
const WHOLE_MIN_DENSITY = 0.7; // jets and fires are single bodies of flame: never thinned below this

const STEAM = rgb(0xd9dde0);
const SMOLDER = [0.11, 0.105, 0.1];
const FIRE_SMOKE = [0.1, 0.095, 0.09];

const NOOP_HANDLE = Object.freeze({ stop() {}, setPos() {}, setDir() {} });

export const EMITTER_KINDS = ['steam', 'smolder', 'embers', 'fire', 'drip', 'jet'];

/**
 * @param {object} ctx  the recipe context (stores, spec, random, density, floorAt, shadeAt) plus
 *   acquireLight() → {light, release()} | null, cameraDistance(x, y, z),
 *   smokeLight(x, y, z, r, g, b, intensity, range)   reports a burning emitter's light for the lit pool
 */
export function createEmitters(ctx, capacity = 24) {
  const { lit, add, spec: s, random } = ctx;

  const slots = [];
  for (let i = 0; i < capacity; i++) {
    slots.push({
      active: false,
      gen: 0,
      kind: '',
      x: 0,
      y: 0,
      z: 0,
      dx: 0,
      dy: 1,
      dz: 0,
      ttl: Infinity,
      age: 0,
      scale: 1,
      a: 0, // emission accumulators, one per stream
      b: 0,
      c: 0,
      d: 0,
      floor: 0,
      shade: 1,
      placedX: 0, // where floor and shade were last asked for
      placedY: 0,
      placedZ: 0,
      light: null,
      lightIn: 0,
      flicker: 0,
      drops: new Float32Array(4), // drip: seconds until each falling drop lands (0 = none)
    });
  }
  let active = 0;

  function release(slot) {
    if (slot.light) {
      slot.light.light.intensity = 0;
      slot.light.release();
      slot.light = null;
    }
  }

  function stop(slot) {
    if (!slot.active) return;
    release(slot);
    slot.active = false;
    slot.gen++;
    active--;
  }

  /** How many whole particles a stream emits this frame. */
  function due(slot, key, rate, dt, k) {
    const total = slot[key] + rate * dt * k;
    const n = total < MAX_PER_FRAME ? Math.floor(total) : MAX_PER_FRAME;
    slot[key] = total - n < 1 ? total - n : 0; // a long frame's surplus is dropped, not owed
    return n;
  }

  // ---- one stream each ---------------------------------------------------------------------

  function steam(e, dt, k) {
    const n = due(e, 'a', 13, dt, k);
    for (let i = 0; i < n; i++) {
      resetSpec(s);
      const r = 0.16 * e.scale;
      s.x = e.x + random.signed() * r;
      s.y = e.y + 0.05;
      s.z = e.z + random.signed() * r;
      s.vx = random.signed() * 0.18;
      s.vy = random.range(0.9, 1.6) * Math.sqrt(e.scale);
      s.vz = random.signed() * 0.18;
      s.life = random.range(2.4, 3.8);
      s.size = 0.32 * e.scale;
      s.size1 = random.range(1.3, 1.9) * e.scale;
      s.curve = 0.7;
      s.rot = random() * TAU;
      s.spin = random.signed() * 0.35;
      s.r = STEAM[0];
      s.g = STEAM[1];
      s.b = STEAM[2];
      s.alpha = random.range(0.13, 0.2);
      s.fadeIn = 0.14;
      s.fadeOut = 0.35;
      s.drag = 0.55;
      s.gravity = -0.012;
      s.wind = 1;
      s.turb = 0.55;
      s.frame = LIT.steam;
      s.shade = e.shade;
      s.floor = e.floor;
      s.seed = random();
      spawn(lit, s, true);
    }
  }

  function smolder(e, dt, k) {
    // Tapers to nothing over the emitter's life.
    const left = e.ttl < Infinity ? Math.max(0, 1 - e.age / e.ttl) : 1;
    const n = due(e, 'a', 9 * left, dt, k);
    for (let i = 0; i < n; i++) {
      resetSpec(s);
      s.x = e.x + random.signed() * 0.12 * e.scale;
      s.y = e.y + 0.05;
      s.z = e.z + random.signed() * 0.12 * e.scale;
      s.vx = random.signed() * 0.2;
      s.vy = random.range(0.6, 1.2);
      s.vz = random.signed() * 0.2;
      s.life = random.range(1.8, 3.1);
      s.size = 0.22 * e.scale;
      s.size1 = random.range(0.9, 1.4) * e.scale;
      s.curve = 0.65;
      s.rot = random() * TAU;
      s.spin = random.signed() * 0.5;
      s.r = SMOLDER[0];
      s.g = SMOLDER[1];
      s.b = SMOLDER[2];
      s.alpha = random.range(0.26, 0.4) * (0.4 + 0.6 * left);
      s.fadeIn = 0.12;
      s.fadeOut = 0.4;
      s.drag = 0.7;
      s.gravity = -0.03;
      s.wind = 1;
      s.turb = 0.8;
      s.frame = i % 2 ? LIT.wisp : LIT.smokeB;
      s.shade = e.shade;
      s.floor = -1000;
      s.seed = random();
      spawn(lit, s, true);
    }
  }

  function ember(e, spread, soft) {
    resetSpec(s);
    s.x = e.x + random.signed() * spread;
    s.y = e.y + random.range(0, 0.25) * e.scale;
    s.z = e.z + random.signed() * spread;
    s.vx = random.signed() * 0.5;
    s.vy = random.range(0.9, 2.3);
    s.vz = random.signed() * 0.5;
    s.life = random.range(1.2, 2.5);
    s.size = random.range(0.028, 0.05);
    s.r = 3.0;
    s.g = 1.4;
    s.b = 0.35;
    s.r1 = 1.1;
    s.g1 = 0.18;
    s.b1 = 0.02;
    s.fadeIn = 0.05;
    s.fadeOut = 0.5;
    s.drag = 0.9;
    s.gravity = -0.04;
    s.wind = 1;
    s.turb = 3.4;
    s.frame = ADD.ember;
    s.floor = -1000;
    s.seed = random();
    spawn(add, s, soft);
  }

  function embers(e, dt, k) {
    const n = due(e, 'a', 8, dt, k);
    for (let i = 0; i < n; i++) ember(e, 0.25 * e.scale, true);
  }

  function fire(e, dt, k) {
    // Like a jet, a fire is one body of flame: thinning it too far leaves loose blobs.
    const body = k > 0 && k < WHOLE_MIN_DENSITY ? WHOLE_MIN_DENSITY : k;
    const flames = due(e, 'a', 38, dt, body);
    for (let i = 0; i < flames; i++) {
      resetSpec(s);
      const r = 0.2 * e.scale;
      const rise = random.range(1.5, 2.9) * Math.sqrt(e.scale);
      s.x = e.x + random.signed() * r;
      s.y = e.y + random.range(0.1, 0.3) * e.scale;
      s.z = e.z + random.signed() * r;
      s.vx = random.signed() * 0.35;
      s.vy = rise;
      s.vz = random.signed() * 0.35;
      s.life = random.range(0.45, 0.85);
      s.size = random.range(0.42, 0.6) * e.scale;
      s.size1 = 0.14 * e.scale;
      s.rot = random() * TAU;
      s.spin = random.signed() * 2.2;
      s.r = 1.35;
      s.g = 0.8;
      s.b = 0.28;
      s.r1 = 0.75;
      s.g1 = 0.11;
      s.b1 = 0.012;
      s.ramp = 0.8;
      s.alpha = 0.5;
      s.fadeIn = 0.15;
      s.fadeOut = 0.5;
      s.drag = 0.9;
      s.wind = 0.5;
      s.turb = 1.8;
      s.stretch = 0.11; // tongues, not balls
      s.frame = i % 2 ? ADD.flameA : ADD.flameB;
      s.floor = e.floor;
      s.seed = random();
      spawn(add, s);
    }
    // The bed of the fire: a low steady glow that ties the tongues together.
    if (due(e, 'd', 7, dt, body) > 0) {
      resetSpec(s);
      s.x = e.x;
      s.y = e.y + 0.3 * e.scale;
      s.z = e.z;
      s.life = 0.32;
      s.size = 1.0 * e.scale;
      s.size1 = 1.15 * e.scale;
      s.r = 0.95;
      s.g = 0.42;
      s.b = 0.1;
      s.alpha = 0.45;
      s.fadeIn = 0.4;
      s.fadeOut = 0.5;
      s.frame = ADD.glow;
      s.floor = e.floor;
      spawn(add, s);
    }
    const puffs = due(e, 'b', 4, dt, k);
    for (let i = 0; i < puffs; i++) {
      resetSpec(s);
      s.x = e.x + random.signed() * 0.15 * e.scale;
      s.y = e.y + random.range(0.5, 0.9) * e.scale;
      s.z = e.z + random.signed() * 0.15 * e.scale;
      s.vx = random.signed() * 0.25;
      s.vy = random.range(1.2, 2.0);
      s.vz = random.signed() * 0.25;
      s.life = random.range(2.0, 3.4);
      s.size = 0.4 * e.scale;
      s.size1 = random.range(1.4, 2.0) * e.scale;
      s.curve = 0.6;
      s.rot = random() * TAU;
      s.spin = random.signed() * 0.4;
      s.r = FIRE_SMOKE[0];
      s.g = FIRE_SMOKE[1];
      s.b = FIRE_SMOKE[2];
      s.alpha = random.range(0.4, 0.55);
      s.fadeIn = 0.15;
      s.fadeOut = 0.4;
      s.drag = 0.6;
      s.gravity = -0.03;
      s.wind = 1;
      s.turb = 0.8;
      s.frame = i % 2 ? LIT.smokeA : LIT.smokeC;
      s.heat = 0.35;
      s.shade = e.shade;
      s.floor = -1000;
      s.seed = random();
      spawn(lit, s, true);
    }
    const motes = due(e, 'c', 3, dt, k);
    for (let i = 0; i < motes; i++) ember(e, 0.2 * e.scale, true);
  }

  function drip(e, dt, k) {
    // Drops already falling: splash when their time is up.
    for (let i = 0; i < e.drops.length; i++) {
      if (e.drops[i] <= 0) continue;
      e.drops[i] -= dt;
      if (e.drops[i] > 0) continue;
      e.drops[i] = 0;
      const n = k > 0 ? 3 : 0;
      for (let j = 0; j < n; j++) {
        resetSpec(s);
        const a = random() * TAU;
        const speed = random.range(0.5, 1.3);
        s.x = e.x;
        s.y = e.floor + 0.02;
        s.z = e.z;
        s.vx = Math.cos(a) * speed;
        s.vy = random.range(0.9, 1.9);
        s.vz = Math.sin(a) * speed;
        s.life = random.range(0.25, 0.4);
        s.size = random.range(0.018, 0.03);
        s.r = 0.5;
        s.g = 0.62;
        s.b = 0.75;
        s.fadeIn = 0;
        s.fadeOut = 0.5;
        s.gravity = 1;
        s.stretch = 0.02;
        s.frame = ADD.streak;
        s.flags = DIE;
        s.floor = e.floor;
        s.seed = random();
        spawn(add, s, true);
      }
    }
    if (due(e, 'a', 1.6, dt, k > 0 ? 1 : 0) < 1) return;
    const height = e.y - e.floor;
    if (height <= 0.05) return;
    const fall = Math.sqrt((2 * height) / GRAVITY);
    resetSpec(s);
    s.x = e.x;
    s.y = e.y;
    s.z = e.z;
    s.life = fall + 0.05;
    s.size = 0.022;
    s.r = 0.55;
    s.g = 0.68;
    s.b = 0.82;
    s.fadeIn = 0;
    s.fadeOut = 0.95;
    s.gravity = 1;
    s.stretch = 0.03;
    s.frame = ADD.streak;
    s.flags = DIE;
    s.floor = e.floor;
    spawn(add, s, true);
    for (let i = 0; i < e.drops.length; i++) {
      if (e.drops[i] <= 0) {
        e.drops[i] = fall;
        break;
      }
    }
  }

  function jet(e, dt, k) {
    // A jet is one thin flame that has to stay whole: it is thinned less than other effects.
    if (k > 0 && k < WHOLE_MIN_DENSITY) k = WHOLE_MIN_DENSITY;
    // Pressure builds: the jet lengthens over the emitter's life.
    const build = e.ttl < Infinity ? 0.75 + 0.5 * Math.min(1, e.age / e.ttl) : 1;
    const reach = e.scale * build;
    // Blue-white cone at the valve: fast, short-lived, drawn out along the jet.
    const core = due(e, 'a', 95, dt, k);
    for (let i = 0; i < core; i++) {
      resetSpec(s);
      const speed = random.range(9, 13) * reach;
      const lead = random() * dt * speed; // spread the frame's batch along the jet: no beads
      s.x = e.x + e.dx * (0.03 + lead);
      s.y = e.y + e.dy * (0.03 + lead);
      s.z = e.z + e.dz * (0.03 + lead);
      s.vx = e.dx * speed + random.signed() * 0.5;
      s.vy = e.dy * speed + random.signed() * 0.5;
      s.vz = e.dz * speed + random.signed() * 0.5;
      s.life = random.range(0.06, 0.095);
      s.size = 0.075 * e.scale;
      s.size1 = 0.2 * e.scale;
      s.r = 0.55;
      s.g = 0.85;
      s.b = 1.7;
      s.r1 = 1.5;
      s.g1 = 0.85;
      s.b1 = 0.35;
      s.ramp = 0.7;
      s.alpha = 0.8;
      s.fadeIn = 0;
      s.fadeOut = 0.45;
      s.stretch = 0.022;
      s.frame = ADD.glow;
      s.floor = -1000;
      spawn(add, s);
    }
    // Orange tongue further out: slows, swells, curls upward and breaks up.
    const tongue = due(e, 'b', 150, dt, k);
    for (let i = 0; i < tongue; i++) {
      resetSpec(s);
      const speed = random.range(8, 12.5) * reach;
      const start = 0.1 * reach + random() * dt * speed;
      s.x = e.x + e.dx * start;
      s.y = e.y + e.dy * start;
      s.z = e.z + e.dz * start;
      s.vx = e.dx * speed + random.signed() * 0.9;
      s.vy = e.dy * speed + random.signed() * 0.9;
      s.vz = e.dz * speed + random.signed() * 0.9;
      s.life = random.range(0.13, 0.24);
      s.size = 0.11 * e.scale;
      s.size1 = random.range(0.36, 0.52) * e.scale;
      s.curve = 0.7;
      s.rot = random() * TAU;
      s.spin = random.signed() * 5;
      s.r = 1.15;
      s.g = 0.62;
      s.b = 0.18;
      s.r1 = 0.6;
      s.g1 = 0.08;
      s.b1 = 0.01;
      s.alpha = 0.5;
      s.fadeIn = 0.08;
      s.fadeOut = 0.4;
      s.drag = 2.6;
      s.gravity = -0.45;
      s.turb = 4;
      s.stretch = 0.028; // drawn out along the jet while it is fast, round once it has slowed
      s.frame = i % 2 ? ADD.flameA : ADD.flameB;
      s.floor = -1000;
      s.seed = random();
      spawn(add, s);
    }
    // Sparks spat out with it.
    const sparks = due(e, 'c', 18, dt, k);
    for (let i = 0; i < sparks; i++) {
      resetSpec(s);
      const speed = random.range(6, 13) * reach;
      s.x = e.x;
      s.y = e.y;
      s.z = e.z;
      s.vx = e.dx * speed + random.signed() * 2.4;
      s.vy = e.dy * speed + random.signed() * 2.4;
      s.vz = e.dz * speed + random.signed() * 2.4;
      s.life = random.range(0.25, 0.6);
      s.size = random.range(0.014, 0.024);
      s.r = 4.2;
      s.g = 3.0;
      s.b = 1.5;
      s.r1 = 1.6;
      s.g1 = 0.5;
      s.b1 = 0.1;
      s.fadeIn = 0;
      s.fadeOut = 0.5;
      s.drag = 1.2;
      s.gravity = 1;
      s.stretch = 0.035;
      s.frame = ADD.streak;
      s.flags = BOUNCE;
      s.floor = e.floor;
      s.seed = random();
      spawn(add, s, true);
    }
  }

  const STREAMS = { steam, smolder, embers, fire, drip, jet };
  // Pooled light per kind: [hex, base intensity, flicker depth, range, offset along dir].
  const LIGHTS = {
    fire: [0xff8a3a, 14, 10, 9, 0.5],
    jet: [0xffa050, 9, 5, 7.5, 1.0],
  };
  const lightTint = { fire: rgb(0xff8a3a), jet: rgb(0xffa050) };

  function updateLight(e, dt) {
    const def = LIGHTS[e.kind];
    if (!def) return;
    e.lightIn -= dt;
    if (e.lightIn <= 0) {
      e.lightIn = LIGHT_CHECK;
      const dist = ctx.cameraDistance(e.x, e.y, e.z);
      if (!e.light && dist < LIGHT_NEAR) {
        e.light = ctx.acquireLight();
        if (e.light) {
          e.light.light.color.set(def[0]);
          e.light.light.distance = def[3] * Math.sqrt(e.scale);
        }
      } else if (e.light && dist > LIGHT_FAR) {
        release(e);
      }
    }
    // Two beating sines and a little noise: a flame, not a strobe.
    e.flicker += dt;
    const t = e.flicker;
    const wobble = 0.5 * Math.sin(t * 17.3 + e.gen) * Math.sin(t * 6.1) + 0.3 * Math.sin(t * 31.7) + 0.2 * random.signed();
    const intensity = Math.max(0, def[1] + def[2] * wobble) * e.scale;
    const lx = e.x + e.dx * def[4] * e.scale;
    const ly = e.y + e.dy * def[4] * e.scale + (e.kind === 'fire' ? 0.2 : 0);
    const lz = e.z + e.dz * def[4] * e.scale;
    if (e.light) {
      e.light.light.position.set(lx, ly, lz);
      e.light.light.intensity = intensity;
    }
    const tint = lightTint[e.kind];
    ctx.smokeLight(lx, ly, lz, tint[0], tint[1], tint[2], intensity, def[3] * Math.sqrt(e.scale));
  }

  // ---- public ------------------------------------------------------------------------------

  /** A free slot, else the finite emitter nearest its end, else null (all slots hold endless emitters). */
  function findSlot() {
    let best = null;
    for (let i = 0; i < slots.length; i++) {
      const e = slots[i];
      if (!e.active) return e;
      if (e.ttl === Infinity) continue;
      if (!best || e.ttl - e.age < best.ttl - best.age) best = e;
    }
    return best;
  }

  function addEmitter(pos, kind, opts) {
    if (!pos || !STREAMS[kind]) return NOOP_HANDLE;
    const e = findSlot();
    if (!e) return NOOP_HANDLE;
    stop(e);
    const ttl = opts && opts.ttl > 0 ? opts.ttl : Infinity;
    const scale = opts && opts.scale > 0 ? opts.scale : 1;
    e.active = true;
    active++;
    e.kind = kind;
    e.x = pos.x;
    e.y = pos.y;
    e.z = pos.z;
    e.dx = 0;
    e.dy = 1;
    e.dz = 0;
    e.ttl = ttl;
    e.age = 0;
    e.scale = scale;
    e.a = e.b = e.c = e.d = random();
    e.lightIn = 0;
    e.flicker = random() * 10;
    e.drops.fill(0);
    const place = () => {
      e.placedX = e.x;
      e.placedY = e.y;
      e.placedZ = e.z;
      e.floor = ctx.floorAt(e.x, e.z, e.y + 0.3);
      e.shade = ctx.shadeAt(e.x, e.y + 1.2, e.z);
    };
    const aim = (d) => {
      const len = d ? Math.hypot(d.x, d.y, d.z) : 0;
      if (len < 1e-6) return;
      e.dx = d.x / len;
      e.dy = d.y / len;
      e.dz = d.z / len;
    };
    place();
    aim(opts && opts.dir);

    const gen = e.gen;
    return {
      stop() {
        if (e.gen === gen) stop(e);
      },
      setPos(v) {
        if (e.gen !== gen || !v) return;
        e.x = v.x;
        e.y = v.y;
        e.z = v.z;
        // The floor and the shade are asked again only when the emitter has really moved.
        if (Math.abs(e.x - e.placedX) + Math.abs(e.z - e.placedZ) > 0.75 || Math.abs(e.y - e.placedY) > 1.5) place();
      },
      setDir(v) {
        if (e.gen === gen) aim(v);
      },
    };
  }

  function update(dt) {
    if (active === 0) return;
    for (let i = 0; i < slots.length; i++) {
      const e = slots[i];
      if (!e.active) continue;
      e.age += dt;
      if (e.age >= e.ttl) {
        stop(e);
        continue;
      }
      STREAMS[e.kind](e, dt, ctx.density(e.x, e.y, e.z));
      updateLight(e, dt);
    }
  }

  /** Stops everything with a finite life; endless emitters (the block's steam) carry on. */
  function clear() {
    for (let i = 0; i < slots.length; i++) {
      if (slots[i].active && slots[i].ttl !== Infinity) stop(slots[i]);
    }
  }

  return {
    add: addEmitter,
    update,
    clear,
    capacity,
    get count() {
      return active;
    },
  };
}
