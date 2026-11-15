// Effect recipes: what a bullet strike, a muzzle flash or a blast is made of.
//
// A recipe fills the shared spawn description and hands it to the particle stores, throws debris and
// lays decals. Counts are "at full quality, up close": every recipe scales them by ctx.density(x, y, z)
// (the quality preset's fx factor, halved far from the camera) and rounds without bias.
//
// Brightness convention for the additive pool: colours are HDR, scene-referred. The bloom picks up
// anything above 1, so a single spark sits around 3–6, while large overlapping sprites (fireballs)
// stay well below 1 each and only their sum goes hot.

import { ADD, DECAL, LIT } from './atlas.js';
import { BOUNCE, DIE, resetSpec, spawn, stochasticRound } from './sim.js';
import { rgb } from './shared.js';

const TAU = Math.PI * 2;

// Dust thrown up by a hit, by surface (linear albedo).
const DUST = {
  asphalt: rgb(0x8a857e),
  concrete: rgb(0xb5b0a8),
  brick: rgb(0xa8674f),
  wood: rgb(0xb09468),
  dirt: rgb(0x8a6f4f),
  metal: rgb(0x8c8f96),
  car: rgb(0x8c8f96),
  rubber: rgb(0x38383a),
  glass: rgb(0xd8e2e6),
  cloth: rgb(0xb9b6ae),
  flesh: rgb(0x9a6a64), // dusty, a faint dark red: cloth and grit, nothing wet
  drone: rgb(0x4a4c52),
};

// Chips knocked out of a surface (linear albedo of the debris chunks).
const CHIP = {
  asphalt: rgb(0x3a3a3c),
  concrete: rgb(0x8c8a84),
  brick: rgb(0x7a3a2a),
  wood: rgb(0x9a7a4c),
  dirt: rgb(0x4a3a28),
  metal: rgb(0x50545a),
  car: rgb(0x44484e),
  rubber: rgb(0x121213),
  glass: rgb(0xa8c0c8),
  cloth: rgb(0x55524c),
  drone: rgb(0x2a2c30),
};

// Bullet-hole decal by surface: [atlas cell, smallest size, largest size (m), opacity].
const HOLE = {
  asphalt: [DECAL.stone, 0.24, 0.34, 0.95],
  concrete: [DECAL.stone, 0.25, 0.36, 1],
  brick: [DECAL.brick, 0.25, 0.36, 1],
  metal: [DECAL.metal, 0.12, 0.17, 1],
  car: [DECAL.metal, 0.12, 0.18, 1],
  glass: [DECAL.glass, 0.3, 0.46, 0.9],
  wood: [DECAL.wood, 0.15, 0.22, 1],
  rubber: [DECAL.soot, 0.08, 0.12, 0.9],
  dirt: [DECAL.soot, 0.2, 0.3, 0.8],
  cloth: [DECAL.soot, 0.07, 0.1, 0.85],
};

// Names accepted by fx.decal() besides the surface names above.
const DECAL_KIND = {
  bullet: HOLE.concrete,
  hole: HOLE.concrete,
  dent: HOLE.metal,
  crack: HOLE.glass,
  soot: [DECAL.soot, 0.3, 0.3, 0.8],
  scorch: [DECAL.scorchA, 3, 3, 0.92],
};

const SPARK_HOT = [1.0, 0.78, 0.42, 1.0, 0.33, 0.07]; // start rgb, end rgb
const SPARK_ELECTRIC = [0.62, 0.84, 1.0, 0.28, 0.45, 1.0];
const SMOKE_DARK = [0.13, 0.125, 0.12];
const SMOKE_PALE = [0.5, 0.5, 0.52];
const WISP_BELOW = 0.35; // fx.smoke scales under this are pale wisps, not rolling smoke

const FAR = 55; // beyond this, half the particles
const NOTHING = 150; // beyond this, no particles at all

/**
 * @param {object} ctx
 *   lit, add, view     particle stores (view: camera-space additive store for viewmodel flashes)
 *   spec               scratch spawn description
 *   random             PRNG with .range(a, b) and .signed()
 *   density(x, y, z)   particle multiplier at a point (quality × distance), 0 = too far to bother
 *   debris.add(…), decals.add(…)
 *   light(x, y, z, hex, intensity, range, ttl, smoke)   pooled light flash; `smoke` also lights the lit pool
 *   floorAt(x, z, maxY), shadeAt(x, y, z)                world queries (shade: 1 lit by the key … 0 shadowed)
 */
export function createRecipes(ctx) {
  const { lit, add, view, spec: s, random } = ctx;

  // Scratch for directions, in a typed array: neither vector objects nor boxed numbers in the hot path.
  //   [0..2] t and [3..5] b: the two axes perpendicular to a normal; [6..8] o: the direction just drawn.
  const v = new Float64Array(9);

  /** Sets (t, b): two unit vectors perpendicular to the unit vector n and to each other. */
  function basis(nx, ny, nz) {
    if (Math.abs(ny) > 0.99) {
      v[0] = 1;
      v[1] = 0;
      v[2] = 0;
    } else {
      const len = Math.hypot(nz, nx);
      v[0] = nz / len;
      v[1] = 0;
      v[2] = -nx / len;
    }
    v[3] = ny * v[2] - nz * v[1];
    v[4] = nz * v[0] - nx * v[2];
    v[5] = nx * v[1] - ny * v[0];
  }

  /** Sets o: a random unit vector within `spread` radians of n. Call basis(n) first. */
  function cone(nx, ny, nz, spread) {
    const cos = 1 - random() * (1 - Math.cos(spread));
    const sin = Math.sqrt(Math.max(0, 1 - cos * cos));
    const phi = random() * TAU;
    const c = Math.cos(phi) * sin;
    const d = Math.sin(phi) * sin;
    v[6] = nx * cos + v[0] * c + v[3] * d;
    v[7] = ny * cos + v[1] * c + v[4] * d;
    v[8] = nz * cos + v[2] * c + v[5] * d;
  }

  const howMany = (n, k) => stochasticRound(n * k, random());

  // Free distance around a blast in eight directions: smoke and flame that would fly into a wall are
  // turned back or held short, so a tank against a building does not lose half its cloud inside it.
  const room = new Float64Array(8);
  function measureRoom(x, y, z, max) {
    for (let j = 0; j < 8; j++) {
      const a = (j / 8) * TAU;
      room[j] = ctx.wallDistance ? ctx.wallDistance(x, y, z, Math.cos(a), Math.sin(a), max) : max;
    }
  }
  /** Room toward angle a (radians). */
  const roomAt = (a) => room[Math.round((a / TAU) * 8) & 7];
  /** An outward direction with room to spare: `a`, or its opposite when a wall is close that way. */
  const awayFromWalls = (a) => (roomAt(a) < 1.4 && roomAt(a + Math.PI) > roomAt(a) ? a + Math.PI : a);
  /** Speed that travels no further than the room allows under exponential drag (distance ≈ v / drag). */
  const held = (speed, a, drag) => Math.min(speed, Math.max(0.25, roomAt(a) - 0.4) * drag);

  // ---------------------------------------------------------------------------------------------
  // Building blocks
  // ---------------------------------------------------------------------------------------------

  /**
   * Sparks: `n` hot streaks in a cone around (nx, ny, nz) that fall, bounce and die.
   * `tint` is [r, g, b, r1, g1, b1]; `gain` scales the brightness.
   */
  function sparkBurst(x, y, z, nx, ny, nz, n, spread, speedMin, speedMax, tint, gain, lifeMin, lifeMax, floor) {
    if (n <= 0) return;
    basis(nx, ny, nz);
    for (let i = 0; i < n; i++) {
      cone(nx, ny, nz, spread);
      const speed = random.range(speedMin, speedMax);
      resetSpec(s);
      s.x = x;
      s.y = y;
      s.z = z;
      s.vx = v[6] * speed;
      s.vy = v[7] * speed;
      s.vz = v[8] * speed;
      s.life = random.range(lifeMin, lifeMax);
      s.size = random.range(0.016, 0.03);
      s.size1 = s.size * 0.5;
      s.r = tint[0] * gain;
      s.g = tint[1] * gain;
      s.b = tint[2] * gain;
      s.r1 = tint[3] * gain * 0.4;
      s.g1 = tint[4] * gain * 0.4;
      s.b1 = tint[5] * gain * 0.4;
      s.ramp = 0.7;
      s.fadeIn = 0;
      s.fadeOut = 0.55;
      s.drag = 1.3;
      s.gravity = 1;
      s.stretch = random.range(0.03, 0.05);
      s.frame = ADD.streak;
      s.flags = BOUNCE;
      s.floor = floor;
      s.seed = random();
      spawn(add, s);
    }
  }

  /** A soft additive ball of light for a frame or three: the flash at the heart of a hit. */
  function glow(store, x, y, z, size, life, r, g, b, frame = ADD.glow) {
    resetSpec(s);
    s.x = x;
    s.y = y;
    s.z = z;
    s.life = life;
    s.size = size;
    s.size1 = size * 1.5;
    s.r = r;
    s.g = g;
    s.b = b;
    s.fadeIn = 0;
    s.fadeOut = 0.2;
    s.frame = frame;
    s.rot = random() * TAU;
    s.floor = -1000;
    spawn(store, s);
  }

  /**
   * One lit puff: where, how fast, which albedo (`tint`), how big it starts and ends, how long it
   * lives. Returns the particle index, or -1 when the pool turned it away.
   */
  function litPuff(x, y, z, vx, vy, vz, tint, size0, size1, life, alpha, frame, shade, floor, soft, drag = 3.2, gravity = -0.015) {
    resetSpec(s);
    s.x = x;
    s.y = y;
    s.z = z;
    s.vx = vx;
    s.vy = vy;
    s.vz = vz;
    s.life = life;
    s.size = size0;
    s.size1 = size1;
    s.curve = 0.55; // swells fast, then lingers
    s.rot = random() * TAU;
    s.spin = random.signed() * 0.9;
    s.r = tint[0];
    s.g = tint[1];
    s.b = tint[2];
    s.alpha = alpha;
    s.fadeIn = 0.06;
    s.fadeOut = 0.25;
    s.drag = drag;
    s.gravity = gravity;
    s.wind = 0.7;
    s.turb = 0.5;
    s.frame = frame;
    s.shade = shade;
    s.floor = floor;
    s.seed = random();
    return spawn(lit, s, soft);
  }

  /**
   * Dust knocked off a surface: a quick jet along the normal and a slower cloud that hangs. Always
   * both, whatever the quality: without them a hit on masonry does not read at night.
   */
  function dustPuff(x, y, z, nx, ny, nz, tint, scale, k, shade, floor) {
    const n = 2 + (random() < k - 0.5 ? 1 : 0);
    for (let i = 0; i < n; i++) {
      const fast = i === 0;
      const speed = (fast ? random.range(3.5, 6) : random.range(0.8, 1.9)) * Math.sqrt(scale);
      litPuff(
        x + nx * 0.04,
        y + ny * 0.04,
        z + nz * 0.04,
        nx * speed + random.signed() * 0.5,
        ny * speed + random.signed() * 0.5 + 0.25,
        nz * speed + random.signed() * 0.5,
        tint,
        (fast ? 0.1 : 0.16) * scale,
        (fast ? 0.6 : 0.95) * scale * random.range(0.85, 1.2),
        fast ? random.range(0.3, 0.45) : random.range(0.65, 1.05),
        fast ? 0.7 : 0.5,
        fast ? LIT.dust : i % 2 ? LIT.smokeB : LIT.dust,
        shade,
        floor,
        false,
        fast ? 6 : 3.2,
      );
    }
  }

  /** Small solid chips thrown off a surface, in a cone around (nx, ny, nz). */
  function chips(x, y, z, nx, ny, nz, n, tint, speedMin, speedMax, sizeMin, sizeMax, long) {
    if (n <= 0) return;
    basis(nx, ny, nz);
    for (let i = 0; i < n; i++) {
      cone(nx, ny, nz, 0.95);
      const speed = random.range(speedMin, speedMax);
      const size = random.range(sizeMin, sizeMax);
      const shade = random.range(0.7, 1.15);
      ctx.debris.add(
        x + nx * 0.03,
        y + ny * 0.03,
        z + nz * 0.03,
        v[6] * speed,
        v[7] * speed + 0.6,
        v[8] * speed,
        long ? size * random.range(3.5, 6) : size * random.range(0.8, 1.4),
        size * random.range(0.5, 0.9),
        size,
        tint[0] * shade,
        tint[1] * shade,
        tint[2] * shade,
        random.range(1.6, 2.8),
        random,
      );
    }
  }

  /** Fast grit: tiny dark specks that arc away and are gone. */
  function grit(x, y, z, nx, ny, nz, n, tint, floor) {
    if (n <= 0) return;
    basis(nx, ny, nz);
    for (let i = 0; i < n; i++) {
      cone(nx, ny, nz, 1.0);
      const speed = random.range(3, 7.5);
      resetSpec(s);
      s.x = x;
      s.y = y;
      s.z = z;
      s.vx = v[6] * speed;
      s.vy = v[7] * speed;
      s.vz = v[8] * speed;
      s.life = random.range(0.3, 0.55);
      s.size = random.range(0.035, 0.06);
      s.r = tint[0] * 0.6;
      s.g = tint[1] * 0.6;
      s.b = tint[2] * 0.6;
      s.alpha = 0.9;
      s.fadeIn = 0;
      s.fadeOut = 0.7;
      s.drag = 0.8;
      s.gravity = 1;
      s.frame = LIT.dust;
      s.flags = DIE;
      s.floor = floor;
      s.seed = random();
      spawn(lit, s, true);
    }
  }

  function hole(x, y, z, nx, ny, nz, entry, shade, scale = 1) {
    const size = random.range(entry[1], entry[2]) * scale;
    ctx.decals.add(x, y, z, nx, ny, nz, size, entry[0] === DECAL.wood ? random.signed() * 0.2 : random() * TAU, entry[0], entry[3], shade);
  }

  // ---------------------------------------------------------------------------------------------
  // Public building blocks
  // ---------------------------------------------------------------------------------------------

  /** fx.sparks: `n` sparks around a direction (straight up when there is none). */
  function sparks(x, y, z, dx, dy, dz, n) {
    const k = ctx.density(x, y, z);
    if (k <= 0) return;
    const len = Math.hypot(dx, dy, dz);
    const omni = len < 1e-6;
    const floor = ctx.floorAt(x, z, y + 0.05);
    if (omni) sparkBurst(x, y, z, 0, 1, 0, howMany(n, k), 1.9, 4, 15, SPARK_HOT, 4.2, 0.25, 0.7, floor);
    else sparkBurst(x, y, z, dx / len, dy / len, dz / len, howMany(n, k), 0.6, 4, 15, SPARK_HOT, 4.2, 0.25, 0.7, floor);
    glow(add, x, y, z, 0.22, 0.05, 2.6, 1.9, 1.0);
  }

  /**
   * fx.smoke: dark smoke that rolls upward (a burning Buzzard, wreckage). Small scales are something
   * else: the thin pale wisp off a hot barrel or a scorched wire.
   */
  function smoke(x, y, z, scale) {
    const k = ctx.density(x, y, z);
    if (k <= 0) return;
    if (scale < WISP_BELOW) {
      const shade = ctx.shadeAt(x, y + 0.5, z);
      const size = random.range(1.1, 1.6) * scale;
      const life = random.range(0.7, 1.2);
      litPuff(x, y, z, random.signed() * 0.12, random.range(0.25, 0.5), random.signed() * 0.12, SMOKE_PALE, 0.25 * scale, size, life, 0.2, LIT.wisp, shade, -1000, true, 1.2, -0.02);
      return;
    }
    const shade = ctx.shadeAt(x, y + 0.5, z);
    const n = Math.max(1, howMany(3, k));
    for (let i = 0; i < n; i++) {
      const idx = litPuff(
        x + random.signed() * 0.12 * scale,
        y + random.signed() * 0.08 * scale,
        z + random.signed() * 0.12 * scale,
        random.signed() * 0.35,
        random.range(0.5, 1.2),
        random.signed() * 0.35,
        SMOKE_DARK,
        0.3 * scale,
        random.range(1.0, 1.5) * scale,
        random.range(1.3, 2.3) * Math.sqrt(scale),
        0.55,
        i % 3 === 0 ? LIT.smokeA : i % 3 === 1 ? LIT.smokeB : LIT.smokeC,
        shade,
        -1000,
        false,
        1.4,
        -0.04,
      );
      if (idx < 0) break;
    }
  }

  /** fx.dust: a pale cloud kicked off the ground. */
  function dust(x, y, z, scale, tint = DUST.concrete) {
    const k = ctx.density(x, y, z);
    if (k <= 0) return;
    const shade = ctx.shadeAt(x, y + 0.4, z);
    const floor = ctx.floorAt(x, z, y + 0.3);
    const n = howMany(3, k);
    for (let i = 0; i < n; i++) {
      litPuff(
        x + random.signed() * 0.15 * scale,
        Math.max(y, floor + 0.08),
        z + random.signed() * 0.15 * scale,
        random.signed() * 0.9,
        random.range(0.2, 0.7),
        random.signed() * 0.9,
        tint,
        0.25 * scale,
        random.range(0.8, 1.2) * scale,
        random.range(0.8, 1.3),
        0.32,
        i % 2 ? LIT.dust : LIT.roll,
        shade,
        floor,
        false,
      );
    }
  }

  /** fx.puff: a small tinted burst (cloth, a body hit) thrown along n. `tint` is linear [r, g, b]. */
  function puff(x, y, z, tint, scale, nx = 0, ny = 1, nz = 0) {
    const k = ctx.density(x, y, z);
    if (k <= 0) return;
    const shade = ctx.shadeAt(x, y, z);
    const jx = random.signed() * 0.4;
    const jz = random.signed() * 0.4;
    litPuff(x, y, z, nx * 1.6 + jx, ny * 1.6 + 0.3, nz * 1.6 + jz, tint, 0.08 * scale, 0.42 * scale, random.range(0.35, 0.55), 0.5, LIT.dust, shade, -1000, false);
    // Lint and grit flying off, and falling.
    litPuff(x, y, z, nx * 2.6 + jx * 2, ny * 2.6 + 0.6, nz * 2.6 + jz * 2, tint, 0.12 * scale, 0.5 * scale, random.range(0.3, 0.5), 0.85, LIT.lint, shade, -1000, false, 2.4, 0.25);
  }

  // ---------------------------------------------------------------------------------------------
  // Impacts
  // ---------------------------------------------------------------------------------------------

  /**
   * A bullet strike on `surface` at (x, y, z) with unit normal n, shot travelling along unit d.
   * `body` is true when a Goon or Buzzard was hit (no decal: it would hang in the air).
   */
  function impact(x, y, z, nx, ny, nz, surface, dx, dy, dz, body) {
    const k = ctx.density(x, y, z);
    // The reflected shot direction: where the energy goes.
    const dn = dx * nx + dy * ny + dz * nz;
    let rx = dx - 2 * dn * nx;
    let ry = dy - 2 * dn * ny;
    let rz = dz - 2 * dn * nz;
    // Debris leaves between the normal and the reflection.
    let mx = nx * 0.6 + rx * 0.4;
    let my = ny * 0.6 + ry * 0.4;
    let mz = nz * 0.6 + rz * 0.4;
    const ml = Math.hypot(mx, my, mz) || 1;
    mx /= ml;
    my /= ml;
    mz /= ml;
    const rl = Math.hypot(rx, ry, rz) || 1;
    rx /= rl;
    ry /= rl;
    rz /= rl;

    const shade = ctx.shadeAt(x + nx * 0.2, y + ny * 0.2, z + nz * 0.2);
    const entry = HOLE[surface];
    if (entry && !body) hole(x, y, z, nx, ny, nz, entry, shade);
    if (k <= 0) return;

    const floor = ny > 0.7 ? y : ctx.floorAt(x + nx * 0.3, z + nz * 0.3, y + 0.05);
    const px = x + nx * 0.02;
    const py = y + ny * 0.02;
    const pz = z + nz * 0.02;
    const tint = DUST[surface] || DUST.concrete;
    const chip = CHIP[surface] || CHIP.concrete;

    switch (surface) {
      case 'metal':
      case 'car': {
        sparkBurst(px, py, pz, mx, my, mz, howMany(14, k), 0.85, 5, 18, SPARK_HOT, 4.5, 0.2, 0.6, floor);
        // The ricochet: a few long streaks along the reflection.
        sparkBurst(px, py, pz, rx, ry, rz, howMany(2.5, k), 0.2, 22, 34, SPARK_HOT, 6, 0.16, 0.3, floor);
        glow(add, px, py, pz, 0.3, 0.05, 3.2, 2.4, 1.3);
        glow(add, px, py, pz, 0.42, 0.045, 1.8, 1.3, 0.7, ADD.star);
        litPuff(px, py, pz, mx * 1.4, my * 1.4 + 0.3, mz * 1.4, tint, 0.06, 0.4, random.range(0.35, 0.55), 0.3, LIT.dust, shade, floor, true);
        if (surface === 'car') chips(px, py, pz, mx, my, mz, howMany(1.2, k), chip, 2, 5, 0.012, 0.025, false);
        ctx.light(px + nx * 0.7, py + ny * 0.7, pz + nz * 0.7, 0xffc070, 6, 5, 0.06, false);
        break;
      }
      case 'glass': {
        // Shards: glints that tumble down and wink out.
        basis(mx, my, mz);
        const n = howMany(12, k);
        for (let i = 0; i < n; i++) {
          cone(mx, my, mz, 1.1);
          const speed = random.range(1.5, 6);
          resetSpec(s);
          s.x = px;
          s.y = py;
          s.z = pz;
          s.vx = v[6] * speed;
          s.vy = v[7] * speed + 0.8;
          s.vz = v[8] * speed;
          s.life = random.range(0.45, 0.95);
          s.size = random.range(0.035, 0.09);
          s.rot = random() * TAU;
          s.spin = random.signed() * 14;
          s.r = 0.7 * 2.2;
          s.g = 0.9 * 2.2;
          s.b = 1.0 * 2.2;
          s.fadeIn = 0;
          s.fadeOut = 0.6;
          s.drag = 0.6;
          s.gravity = 1;
          s.frame = ADD.glint;
          s.flags = DIE;
          s.floor = floor;
          s.seed = random();
          spawn(add, s);
        }
        dustPuff(px, py, pz, mx, my, mz, tint, 0.7, k, shade, floor);
        chips(px, py, pz, mx, my, mz, howMany(2, k), chip, 2, 5, 0.012, 0.03, false);
        break;
      }
      case 'wood': {
        chips(px, py, pz, mx, my, mz, howMany(5, k), chip, 2.5, 7, 0.008, 0.016, true);
        dustPuff(px, py, pz, mx, my, mz, tint, 0.85, k, shade, floor);
        break;
      }
      case 'rubber': {
        litPuff(px, py, pz, mx * 1.5, my * 1.5 + 0.3, mz * 1.5, tint, 0.08, 0.45, random.range(0.4, 0.6), 0.5, LIT.dust, shade, floor, false);
        chips(px, py, pz, mx, my, mz, howMany(2.5, k), chip, 2, 5, 0.012, 0.03, false);
        break;
      }
      case 'dirt': {
        chips(px, py, pz, mx, my, mz, howMany(5, k), chip, 2, 5.5, 0.02, 0.05, false);
        dustPuff(px, py, pz, mx, my, mz, tint, 1.25, k, shade, floor);
        break;
      }
      case 'cloth': {
        puff(px, py, pz, tint, 1, mx, my, mz);
        break;
      }
      case 'flesh': {
        // A Goon: cloth dust and lint, a faint dark-red tint. Nothing wet, nothing left behind.
        puff(px, py, pz, tint, 0.9, -dx * 0.6 + nx * 0.4, 0.2, -dz * 0.6 + nz * 0.4);
        break;
      }
      case 'drone': {
        // A Buzzard: electric sparks, a wink of light, a wisp of dark smoke, now and then hot fragments.
        sparkBurst(px, py, pz, mx, my, mz, howMany(13, k), 1.0, 4, 14, SPARK_ELECTRIC, 5, 0.15, 0.45, floor);
        sparkBurst(px, py, pz, rx, ry, rz, howMany(2, k), 0.3, 16, 26, SPARK_ELECTRIC, 6, 0.15, 0.28, floor);
        glow(add, px, py, pz, 0.34, 0.05, 1.6, 2.4, 3.4);
        litPuff(px, py, pz, mx * 0.8, my * 0.8 + 0.5, mz * 0.8, SMOKE_DARK, 0.1, 0.6, random.range(0.6, 0.9), 0.5, LIT.wisp, shade, -1000, true);
        chips(px, py, pz, mx, my, mz, howMany(1.5, k), chip, 2, 6, 0.015, 0.035, false);
        if (random() < 0.35) sparkBurst(px, py, pz, mx, my, mz, howMany(3, k), 0.9, 2, 6, SPARK_HOT, 3.5, 0.5, 1.0, floor);
        ctx.light(px + nx * 0.5, py + ny * 0.5, pz + nz * 0.5, 0x9cc8ff, 7, 5, 0.06, false);
        break;
      }
      default: {
        // Asphalt, concrete, brick and anything unknown: dust, chips, grit, a spark or two.
        dustPuff(px, py, pz, mx, my, mz, tint, 1, k, shade, floor);
        chips(px, py, pz, mx, my, mz, howMany(2.6, k), chip, 2, 6, 0.014, 0.035, false);
        grit(px, py, pz, mx, my, mz, howMany(3, k), chip, floor);
        if (random() < 0.45) sparkBurst(px, py, pz, rx, ry, rz, 1 + (random() < 0.4 ? 1 : 0), 0.5, 7, 18, SPARK_HOT, 4, 0.12, 0.3, floor);
      }
    }
  }

  // ---------------------------------------------------------------------------------------------
  // Muzzle flash
  // ---------------------------------------------------------------------------------------------

  /**
   * World-space flash at a muzzle firing along unit d: hot core, star, a jet of flame out of the
   * barrel, three sparks and a puff of smoke.
   */
  function muzzleFlash(x, y, z, dx, dy, dz, scale) {
    const k = ctx.density(x, y, z);
    if (k <= 0) return;
    const life = random.range(0.036, 0.056);
    glow(add, x + dx * 0.05, y + dy * 0.05, z + dz * 0.05, 0.3 * scale, life, 3.6, 2.7, 1.5);
    glow(add, x + dx * 0.08, y + dy * 0.08, z + dz * 0.08, 0.5 * scale * random.range(0.8, 1.3), life, 2.2, 1.5, 0.75, ADD.star);
    // The jet: two tongues stretched along the bore.
    for (let i = 0; i < 2; i++) {
      resetSpec(s);
      const reach = (0.16 + i * 0.16) * scale;
      s.x = x + dx * reach;
      s.y = y + dy * reach;
      s.z = z + dz * reach;
      s.vx = dx * 7;
      s.vy = dy * 7;
      s.vz = dz * 7;
      s.stretch = 0.045 * scale;
      s.life = life;
      s.size = (0.2 - i * 0.07) * scale;
      s.r = 2.4;
      s.g = 1.5;
      s.b = 0.6;
      s.fadeIn = 0;
      s.fadeOut = 0.3;
      s.frame = ADD.streak;
      s.floor = -1000;
      spawn(add, s);
    }
    muzzleSparks(x, y, z, dx, dy, dz, 3);
    const life2 = random.range(0.45, 0.75);
    litPuff(x + dx * 0.2, y + dy * 0.2, z + dz * 0.2, dx * 1.1, dy * 1.1 + 0.35, dz * 1.1, DUST.concrete, 0.1 * scale, 0.5 * scale, life2, 0.14, LIT.steam, 1, -1000, true);
  }

  /** The few sparks a shot spits out of the barrel. */
  function muzzleSparks(x, y, z, dx, dy, dz, n) {
    const k = ctx.density(x, y, z);
    if (k <= 0) return;
    sparkBurst(x, y, z, dx, dy, dz, howMany(n, k), 0.3, 8, 17, SPARK_HOT, 3.5, 0.1, 0.22, ctx.floorAt(x, z, y + 0.05));
  }

  /** The same flash in camera space for the first-person weapon (drawn in the viewmodel scene). */
  function viewFlash(x, y, z, dx, dy, dz, scale) {
    const life = random.range(0.036, 0.056);
    glow(view, x, y, z, 0.05 * scale, life, 3.4, 2.6, 1.5);
    glow(view, x + dx * 0.02, y + dy * 0.02, z + dz * 0.02, 0.1 * scale * random.range(0.8, 1.3), life, 2.1, 1.45, 0.7, ADD.star);
    for (let i = 0; i < 2; i++) {
      resetSpec(s);
      const reach = (0.03 + i * 0.04) * scale;
      s.x = x + dx * reach;
      s.y = y + dy * reach;
      s.z = z + dz * reach;
      s.vx = dx * 3;
      s.vy = dy * 3;
      s.vz = dz * 3;
      s.stretch = 0.03 * scale;
      s.life = life;
      s.size = (0.04 - i * 0.012) * scale;
      s.r = 2.3;
      s.g = 1.45;
      s.b = 0.6;
      s.fadeIn = 0;
      s.fadeOut = 0.3;
      s.frame = ADD.streak;
      spawn(view, s);
    }
  }

  // ---------------------------------------------------------------------------------------------
  // Explosion
  // ---------------------------------------------------------------------------------------------

  /**
   * A blast of size `scale` (1 = a propane tank) centred at (x, y, z).
   * `flavour`: 'fuel' (default) or 'drone' (a Buzzard: more electric sparks, less fire).
   */
  function explosion(x, y, z, scale, flavour = 'fuel', ground = -1000) {
    const k = ctx.density(x, y, z);
    // `ground`: where the thing that blew up stood, when known (a kerb the collision world leaves out).
    const floor = Math.max(ctx.floorAt(x, z, y + 0.3), ground <= y ? ground : -1000);
    const grounded = y - floor < 2.2 * scale + 0.6;
    const shade = ctx.shadeAt(x, y + 1.5, z);
    const drone = flavour === 'drone';

    // Light first: it also colours the smoke about to appear.
    ctx.light(x, y + 0.5 * scale, z, 0xffa040, 120 * scale * Math.sqrt(scale), 10 + 8 * scale, 0.36, true);
    if (grounded) {
      ctx.decals.add(x, floor, z, 0, 1, 0, random.range(3.4, 4.3) * scale, random() * TAU, random() < 0.5 ? DECAL.scorchA : DECAL.scorchB, 0.92, shade);
    }
    if (k <= 0) return;
    const cy = Math.max(y, floor + 0.35 * scale);

    // The flash: one white-hot frame, a wide warm bloom behind it and a faint shock ring.
    glow(add, x, cy, z, 2.2 * scale, 0.07, 4.2, 3.4, 2.2);
    glow(add, x, cy, z, 6.5 * scale, 0.14, 0.7, 0.36, 0.14);
    resetSpec(s);
    s.x = x;
    s.y = cy;
    s.z = z;
    s.life = 0.2;
    s.size = 1.5 * scale;
    s.size1 = 9 * scale;
    s.curve = 0.6;
    s.r = 0.9;
    s.g = 0.6;
    s.b = 0.35;
    s.alpha = 0.22;
    s.fadeIn = 0;
    s.fadeOut = 0.1;
    s.frame = ADD.ring;
    s.rot = random() * TAU;
    s.floor = -1000;
    spawn(add, s);

    // Fireball: tongues of flame thrown outward that swell, redden and burn out. Each sprite is dim on
    // its own; only where many overlap, in the first frames, does the sum go white.
    measureRoom(x, cy + 0.4, z, 6 * scale);
    const flames = howMany((drone ? 9 : 18) * Math.sqrt(scale), k);
    const flameGain = 0.42 / Math.max(k, 0.3); // fewer sprites at low quality, each brighter: same fire
    for (let i = 0; i < flames; i++) {
      const a = awayFromWalls(random() * TAU);
      const up = random.range(-0.25, 1);
      const flat = Math.sqrt(Math.max(0, 1 - up * up * 0.8));
      const speed = held(random.range(3.5, 12) * scale, a, 3.2);
      resetSpec(s);
      s.x = x + Math.cos(a) * flat * 0.35 * scale;
      s.y = cy + up * 0.3 * scale;
      s.z = z + Math.sin(a) * flat * 0.35 * scale;
      s.vx = Math.cos(a) * flat * speed;
      s.vy = up * speed * 0.8 + 1.8 * scale;
      s.vz = Math.sin(a) * flat * speed;
      s.life = random.range(0.32, 0.68);
      s.size = random.range(0.8, 1.2) * scale;
      s.size1 = random.range(2.3, 3.4) * scale;
      s.curve = 0.5;
      s.rot = random() * TAU;
      s.spin = random.signed() * 1.6;
      s.r = 0.85;
      s.g = 0.42;
      s.b = 0.12;
      s.r1 = 0.3;
      s.g1 = 0.03;
      s.b1 = 0.004;
      s.ramp = 0.45;
      s.alpha = flameGain;
      s.fadeIn = 0.03;
      s.fadeOut = 0.35;
      s.drag = 3.2;
      s.gravity = -0.3;
      s.turb = 2;
      s.frame = i % 2 ? ADD.flameA : ADD.flameB;
      s.floor = floor;
      s.seed = random();
      spawn(add, s);
    }

    // The heart of the fireball: a few big, slow tongues that hold the centre while the rest flies out,
    // so the blast reads as one ball of fire and not as a spray.
    const core = howMany((drone ? 2 : 4) * Math.sqrt(scale), Math.max(k, 0.75));
    for (let i = 0; i < core; i++) {
      resetSpec(s);
      s.x = x + random.signed() * 0.3 * scale;
      s.y = cy + random.range(0.1, 0.6) * scale;
      s.z = z + random.signed() * 0.3 * scale;
      s.vx = random.signed() * 1.2 * scale;
      s.vy = random.range(1.5, 3.2) * scale;
      s.vz = random.signed() * 1.2 * scale;
      s.life = random.range(0.55, 0.85);
      s.size = random.range(1.6, 2.1) * scale;
      s.size1 = random.range(3.4, 4.4) * scale;
      s.curve = 0.45;
      s.rot = random() * TAU;
      s.spin = random.signed() * 1.1;
      s.r = 0.9;
      s.g = 0.5;
      s.b = 0.16;
      s.r1 = 0.32;
      s.g1 = 0.05;
      s.b1 = 0.006;
      s.ramp = 0.4;
      s.alpha = 0.5;
      s.fadeIn = 0.02;
      s.fadeOut = 0.45;
      s.drag = 2.4;
      s.gravity = -0.35;
      s.turb = 1.4;
      s.frame = i % 2 ? ADD.flameB : ADD.flameA;
      s.floor = floor;
      s.seed = random();
      spawn(add, s);
    }

    // By day the column must stand out against a bright sky: the soot is darker, there is more of it.
    const day = ctx.day ? ctx.day() : 0;
    const soot = 1 - 0.45 * day;

    // Smoke: a column that rolls up out of the fire, lit from inside while it is young.
    const puffs = howMany((drone ? 12 : 26) * Math.sqrt(scale), k);
    for (let i = 0; i < puffs; i++) {
      const a = awayFromWalls(random() * TAU);
      const out = held(random.range(0.3, 3.4) * scale, a, 1.5);
      const rise = random.range(1.2, 5.6) * Math.sqrt(scale);
      const girth = random.range(0.6, 1.25);
      resetSpec(s);
      s.x = x + Math.cos(a) * 0.5 * scale;
      s.y = cy + random.range(0, 0.7) * scale;
      s.z = z + Math.sin(a) * 0.5 * scale;
      s.vx = Math.cos(a) * out;
      s.vy = rise;
      s.vz = Math.sin(a) * out;
      s.life = random.range(2.6, 4.8) * (0.6 + 0.4 * scale);
      s.size = 0.9 * girth * scale;
      s.size1 = random.range(2.8, 4.0) * girth * scale;
      s.curve = 0.5;
      s.rot = random() * TAU;
      s.spin = random.signed() * 0.5;
      const tone = random.range(0.07, 0.15) * soot;
      s.r = tone * 1.06;
      s.g = tone;
      s.b = tone * 0.95;
      s.r1 = 0.16 * soot;
      s.g1 = 0.16 * soot;
      s.b1 = 0.165 * soot;
      s.alpha = random.range(0.72, 0.92);
      s.fadeIn = 0.05;
      s.fadeOut = 0.4;
      s.drag = 1.5;
      s.gravity = -0.11;
      s.wind = 0.8;
      s.turb = 1.3;
      s.frame = i % 3 === 0 ? LIT.smokeA : i % 3 === 1 ? LIT.smokeB : LIT.smokeC;
      s.heat = random.range(0.4, 1.0);
      s.shade = shade;
      s.floor = floor;
      s.seed = random();
      spawn(lit, s);
    }

    // The column: puffs shot straight up out of the fire that keep climbing and spread at the top.
    const column = drone ? 0 : howMany((6 + 6 * day) * Math.sqrt(scale), Math.max(k, 0.6));
    for (let i = 0; i < column; i++) {
      const lift = (i + random()) / Math.max(column, 1);
      resetSpec(s);
      s.x = x + random.signed() * 0.4 * scale;
      s.y = cy + 0.4 * scale;
      s.z = z + random.signed() * 0.4 * scale;
      s.vx = random.signed() * 0.6;
      s.vy = (3 + 4.5 * lift) * Math.sqrt(scale);
      s.vz = random.signed() * 0.6;
      s.life = random.range(4.5, 6.5) * (0.7 + 0.3 * scale);
      s.size = 0.8 * scale;
      s.size1 = (2.8 + 2.8 * lift) * scale;
      s.curve = 0.6;
      s.rot = random() * TAU;
      s.spin = random.signed() * 0.4;
      const tone = random.range(0.05, 0.1) * soot;
      s.r = tone * 1.05;
      s.g = tone;
      s.b = tone * 0.96;
      s.r1 = 0.2 * soot;
      s.g1 = 0.2 * soot;
      s.b1 = 0.21 * soot;
      s.alpha = random.range(0.7, 0.88);
      s.fadeIn = 0.08;
      s.fadeOut = 0.5;
      s.drag = 0.9;
      s.gravity = -0.05;
      s.wind = 1;
      s.turb = 1;
      s.frame = i % 2 ? LIT.smokeA : LIT.smokeC;
      s.heat = random.range(0.3, 0.7);
      s.shade = shade;
      s.floor = floor;
      s.seed = random();
      spawn(lit, s);
    }

    // Sparks and embers.
    sparkBurst(x, cy, z, 0, 1, 0, howMany((drone ? 18 : 34) * scale, k), 1.75, 8 * scale, 26 * scale, SPARK_HOT, 4.5, 0.45, 1.3, floor);
    if (drone) sparkBurst(x, cy, z, 0, 1, 0, howMany(16, k), 1.9, 5, 16, SPARK_ELECTRIC, 5.5, 0.2, 0.6, floor);
    const embers = howMany(14 * scale, k);
    for (let i = 0; i < embers; i++) {
      const a = random() * TAU;
      const speed = random.range(1, 5) * scale;
      resetSpec(s);
      s.x = x;
      s.y = cy;
      s.z = z;
      s.vx = Math.cos(a) * speed;
      s.vy = random.range(2, 7) * Math.sqrt(scale);
      s.vz = Math.sin(a) * speed;
      s.life = random.range(1.2, 2.8);
      s.size = random.range(0.035, 0.065);
      s.r = 3.2;
      s.g = 1.5;
      s.b = 0.4;
      s.r1 = 1.2;
      s.g1 = 0.2;
      s.b1 = 0.03;
      s.fadeIn = 0;
      s.fadeOut = 0.5;
      s.drag = 1.3;
      s.gravity = 0.22;
      s.wind = 1;
      s.turb = 3.2;
      s.frame = ADD.ember;
      s.flags = DIE;
      s.floor = floor;
      s.seed = random();
      spawn(add, s, true);
    }

    // Fragments.
    const fragments = howMany((drone ? 7 : 13) * scale, k);
    for (let i = 0; i < fragments; i++) {
      const a = random() * TAU;
      const speed = random.range(3, 11) * Math.sqrt(scale);
      const size = random.range(0.04, 0.11) * Math.sqrt(scale);
      const tone = random.range(0.02, 0.09);
      const up = random.range(3, 10) * Math.sqrt(scale);
      const long = size * random.range(1, 2.4);
      ctx.debris.add(x, cy + 0.1, z, Math.cos(a) * speed, up, Math.sin(a) * speed, long, size * 0.6, size, tone, tone * 0.95, tone * 0.9, random.range(2.2, 4), random);
    }

    // Dust kicked out along the ground.
    if (grounded) {
      const tint = DUST.asphalt;
      const ringN = howMany(14 * Math.sqrt(scale), k);
      const start = random() * TAU;
      for (let i = 0; i < ringN; i++) {
        const a = start + (i / ringN) * TAU + random.signed() * 0.2;
        const speed = held(random.range(7, 11.5) * scale, a, 3.1);
        resetSpec(s);
        s.x = x + Math.cos(a) * 0.5 * scale;
        s.y = floor + 0.3 * scale;
        s.z = z + Math.sin(a) * 0.5 * scale;
        s.vx = Math.cos(a) * speed;
        s.vy = random.range(0.1, 0.7);
        s.vz = Math.sin(a) * speed;
        s.life = random.range(0.9, 1.6);
        s.size = 0.7 * scale;
        s.size1 = random.range(1.9, 2.7) * scale;
        s.curve = 0.5;
        s.rot = random.signed() * 0.3;
        s.spin = random.signed() * 0.2;
        s.r = tint[0];
        s.g = tint[1];
        s.b = tint[2];
        s.alpha = random.range(0.3, 0.42);
        s.fadeIn = 0.08;
        s.fadeOut = 0.3;
        s.drag = 3.1;
        s.gravity = -0.01;
        s.wind = 0.6;
        s.turb = 0.4;
        s.frame = LIT.roll;
        s.heat = 0.12;
        s.shade = shade;
        s.floor = floor;
        s.seed = random();
        spawn(lit, s);
      }
    }
  }

  /** Dust ring under a body that landed hard at (x, y, z). `strength` 0…1. */
  function landing(x, y, z, strength, surface) {
    const k = ctx.density(x, y, z);
    if (k <= 0) return;
    const tint = DUST[surface] || DUST.asphalt;
    const shade = ctx.shadeAt(x, y + 0.5, z);
    const n = howMany(3 + 4 * strength, k);
    const start = random() * TAU;
    for (let i = 0; i < n; i++) {
      const a = start + (i / n) * TAU + random.signed() * 0.3;
      const speed = random.range(1.2, 2.4) * (0.6 + strength);
      const idx = litPuff(
        x + Math.cos(a) * 0.25,
        y + 0.1,
        z + Math.sin(a) * 0.25,
        Math.cos(a) * speed,
        random.range(0.1, 0.4),
        Math.sin(a) * speed,
        tint,
        0.2,
        random.range(0.6, 0.95) * (0.7 + 0.5 * strength),
        random.range(0.55, 0.9),
        0.16 + 0.14 * strength,
        LIT.roll,
        shade,
        y,
        true,
      );
      if (idx < 0) break;
    }
  }

  return {
    sparks,
    smoke,
    dust,
    puff,
    impact,
    muzzleFlash,
    muzzleSparks,
    viewFlash,
    explosion,
    landing,
    litPuff,
    glow,
    sparkBurst,
    decalEntry: (kind) => DECAL_KIND[kind] || HOLE[kind] || null,
    dustTint: (surface) => DUST[surface] || DUST.concrete,
  };
}

export { DUST, SPARK_HOT, SPARK_ELECTRIC, SMOKE_DARK };
