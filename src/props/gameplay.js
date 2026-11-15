// Props the game talks to (CONTRACT 6.2):
//
//   master_case    setState('live' | 'grabbing' | 'taken', t), update(dt)
//                  live      lid off, the gold reel on show, beacon and light shaft pulsing, boombox lit
//                  grabbing  the same, faster, with a gold bar filling up on the lid as t goes 0 → 1
//                  taken     reel gone, lid back on, every light out
//   propane_tank, welding_rack   setState('idle' | 'lit' | 'gone'), optional update(dt)
//                  lit       the shell glows with heat; when fx is stubbed there is also a flame at the
//                            valve (it flickers if update is called)
//                  gone      only a scorched foot is left
//
// The two explosives are a single vertex-coloured mesh each (plus one decal quad): there are twenty of
// them on the block and none of them can be merged.

import { BufferAttribute, Quaternion, Vector3 } from 'three';
import { clamp01 } from '../core/util.js';
import { boombox } from './clutter.js';
import { RIGGED, Soup, glow, latheGeo, xf } from './kit.js';

const TAU = Math.PI * 2;

// ---- master case ---------------------------------------------------------------------------------

const CASE = {
  x: -0.19, // centre of the case
  z: 0,
  w: 0.42,
  d: 0.32,
  base: 0.03, // the toe plate it stands on
  body: 0.5,
  lid: 0.12,
  open: 1.66, // radians the lid stands open while the reel is there
  lidTime: 0.3, // seconds for it to drop shut
  shaft: 6, // metres of light above the beacon
  pulse: 2.2, // rad/s while waiting; faster while being grabbed
  pulseGrab: 9,
  boombox: [0.16, 0, -0.04, 1.15], // x, y, z, yaw
};

/** Per-vertex greys for an additive mesh: fn(x, y, z) → brightness. */
function fadeBy(geo, fn) {
  const pos = geo.getAttribute('position');
  const col = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) col.fill(fn(pos.getX(i), pos.getY(i), pos.getZ(i)), i * 3, i * 3 + 3);
  geo.setAttribute('color', new BufferAttribute(col, 3));
  return geo;
}

/** A road-case shell: black panels, aluminium edging, ball corners. Centre (x, y, z), size (w, h, d). */
function caseShell(b, x, y, z, w, h, d) {
  b.box('plastic_dark', [w, h, d], [x, y, z]);
  const e = 0.016;
  const edge = 'metal_galv';
  for (const sy of [1, -1]) {
    for (const sz of [1, -1]) b.box(edge, [w + 0.004, e, e], [x, y + sy * (h / 2 - e / 2 + 0.002), z + sz * (d / 2 - e / 2 + 0.002)]);
    for (const sx of [1, -1]) b.box(edge, [e, e, d + 0.004], [x + sx * (w / 2 - e / 2 + 0.002), y + sy * (h / 2 - e / 2 + 0.002), z]);
  }
  for (const sx of [1, -1]) {
    for (const sz of [1, -1]) {
      b.box(edge, [e, h + 0.004, e], [x + sx * (w / 2 - e / 2 + 0.002), y, z + sz * (d / 2 - e / 2 + 0.002)]);
      for (const sy of [1, -1]) b.box('chrome', [0.03, 0.03, 0.03], [x + sx * (w / 2 - 0.008), y + sy * (h / 2 - 0.008), z + sz * (d / 2 - 0.008)]);
    }
  }
}

function buildMasterCase(b) {
  const C = CASE;
  const front = C.z + C.d / 2;
  const back = C.z - C.d / 2;
  const left = C.x - C.w / 2;
  const bodyTop = C.base + C.body;
  const steel = 'metal_galv';
  const boom = xf(C.boombox[0], C.boombox[1], C.boombox[2], 0, C.boombox[3], 0);

  // ---- hand truck, loaded from the left: toe plate, two rails bent into a handle, axle and wheels ----
  const hx = left - 0.022;
  b.box(steel, [0.3, 0.012, 0.3], [left + 0.13, 0.024, C.z]);
  for (const s of [1, -1]) {
    b.pipe(steel, [[hx, 0.03, s * 0.12], [hx - 0.006, 0.86, s * 0.12], [hx, 0.96, s * 0.08]], 0.013, { seg: 6 });
    const m = xf(hx + 0.07, 0.09, s * 0.195, (s * Math.PI) / 2, 0, 0);
    b.add('tire', latheGeo([[0, -0.02], [0.09, -0.02], [0.09, 0.02], [0.045, 0.02]], 10), m);
    b.add(steel, latheGeo([[0.045, 0.02], [0, 0.026]], 8), m);
  }
  b.stick(steel, [hx, 0.96, -0.08], [hx, 0.96, 0.08], 0.013, { seg: 6 });
  for (const y of [0.3, 0.62]) b.box(steel, [0.012, 0.03, 0.24], [hx, y, C.z]);
  b.cyl(steel, 0.012, 0.4, [hx + 0.07, 0.09, C.z], { axis: 'z', seg: 5 });

  // ---- the case: body, foam, latches, a handle, the tracker clipped to its front ----
  caseShell(b, C.x, C.base + C.body / 2, C.z, C.w, C.body, C.d);
  b.box('rubber', [C.w - 0.05, 0.02, C.d - 0.05], [C.x, bodyTop + 0.002, C.z]); // foam, seen while the lid is up
  for (const dx of [-0.12, 0.12]) b.box('chrome', [0.05, 0.07, 0.012], [C.x + dx, bodyTop - 0.05, front + 0.006]);
  b.box('rubber', [0.012, 0.07, 0.14], [C.x + C.w / 2 + 0.002, 0.34, C.z]);
  b.box('chrome', [0.014, 0.012, 0.12], [C.x + C.w / 2 + 0.006, 0.345, C.z]);
  b.decal('ipx_tag', [C.x + 0.08, 0.2, front], 0.2, 0.1, '+z', { lift: 0.004 });
  const tx = C.x - 0.1;
  const ty = 0.32;
  b.box('plastic_dark', [0.11, 0.065, 0.03], [tx, ty, front + 0.016]);
  b.decal('tracker_lcd', [tx, ty, front + 0.031], 0.084, 0.035, '+z', { lit: true, lift: 0.002 });
  b.stick('plastic_dark', [tx + 0.045, ty + 0.03, front + 0.016], [tx + 0.065, ty + 0.2, front + 0.024], 0.004, { seg: 4 });

  // ---- the boombox beside it ----
  boombox(b, boom);

  // ---- lid: authored shut, hinged along the back of the case ----
  const lidY = bodyTop + C.lid / 2;
  b.node('lid', [C.x, bodyTop, back]);
  caseShell(b, C.x, lidY, C.z, C.w, C.lid, C.d);
  b.decal('ipx_mark', [C.x, bodyTop + C.lid, C.z], 0.3, 0.125, '+y', { lift: 0.004 });
  // Inside the lid: foam, the mark again, and the track the progress bar runs in.
  b.box('rubber', [C.w - 0.05, 0.012, C.d - 0.05], [C.x, bodyTop + 0.004, C.z]);
  b.decal('ipx_mark', [C.x, bodyTop - 0.002, C.z - 0.03], 0.26, 0.108, { right: [1, 0, 0], up: [0, 0, 1] }, { lift: 0.002 });
  b.box('plastic_dark', [0.36, 0.008, 0.045], [C.x, bodyTop - 0.004, front - 0.07]);

  // The progress bar: grows from its left end along the track.
  b.node('bar', [C.x - 0.17, bodyTop - 0.009, front - 0.07]);
  b.box(glow(0xf6c21a, 3.2), [0.34, 0.006, 0.03], [C.x, bodyTop - 0.009, front - 0.07]);

  // ---- the reel: gold flanges on show in the open case, propped on its tape box ----
  b.node('reel', [C.x, bodyTop, C.z]);
  b.box('cardboard', [0.29, 0.04, 0.29], [C.x + 0.03, bodyTop + 0.033, C.z - 0.005], { rot: [0, 0.12, 0] });
  b.decal('reel_label', [C.x + 0.03, bodyTop + 0.053, C.z - 0.005], 0.26, 0.26, { right: [0.993, 0, -0.12], up: [-0.12, 0, -0.993] }, { lift: 0.002 });
  const tilt = xf(C.x - 0.05, bodyTop + 0.125, C.z + 0.035, 0.7, 0, 0.1);
  b.add('gold', latheGeo([[0, 0], [0.135, 0], [0.135, 0.008], [0.03, 0.008], [0.03, 0.03], [0.135, 0.03], [0.135, 0.038], [0, 0.038]], 14), tilt);
  b.add('wood', latheGeo([[0.118, 0.008], [0.118, 0.03]], 14), tilt);
  b.push(tilt);
  b.decal('reel_top', [0, 0.038, 0], 0.27, 0.27, '+y', { lift: 0.002 });
  b.pop();

  // ---- beacon on a short mast clamped to the handle (it clears waist-high cover), its shaft of light,
  //      the pool on the ground. By day the beacon and the mast's silhouette have to do the work.
  const by = 1.22;
  b.stick('plastic_dark', [hx, 0.9, C.z], [hx, by, C.z], 0.011, { seg: 6 });
  b.box('metal_galv', [0.03, 0.05, 0.05], [hx, 0.93, C.z]); // clamp
  b.cyl('plastic_dark', 0.062, 0.03, [hx, by + 0.015, C.z], { seg: 10 });
  b.node('beacon', [hx, by, C.z]);
  b.add(RIGGED, latheGeo([[0.052, 0.03], [0.052, 0.075], [0.04, 0.11], [0.018, 0.124], [0, 0.126]], 10), xf(hx, by, C.z));
  b.node('shaft', [hx, by + 0.12, C.z]);
  const shaft = new Soup();
  for (let i = 0; i < 6; i++) {
    const p = (k, r, y) => {
      const a = (k / 6) * TAU;
      return [hx + Math.cos(a) * r, by + 0.12 + y, C.z + Math.sin(a) * r];
    };
    shaft.quad(p(i, 0.05, 0), p(i + 1, 0.05, 0), p(i + 1, 0.14, C.shaft), p(i, 0.14, C.shaft));
  }
  b.add(RIGGED, fadeBy(shaft.build(60), (x, y) => (1 - clamp01((y - by) / C.shaft)) ** 1.6));
  b.node('pool', [0, 0.02, 0]);
  const pool = new Soup();
  const rings = [0, 0.45, 1.0];
  for (let k = 0; k < rings.length - 1; k++) {
    for (let i = 0; i < 12; i++) {
      const p = (j, r) => {
        const a = (j / 12) * TAU;
        return [Math.cos(a) * r - 0.05, 0.02, -Math.sin(a) * r];
      };
      if (rings[k] === 0) pool.tri(p(i, 0), p(i, rings[k + 1]), p(i + 1, rings[k + 1]));
      else pool.quad(p(i, rings[k]), p(i, rings[k + 1]), p(i + 1, rings[k + 1]), p(i + 1, rings[k]));
    }
  }
  b.add(RIGGED, fadeBy(pool.build(60), (x, y, z) => {
    const r = Math.hypot(x + 0.05, z);
    return r < 0.45 ? 0.5 - (r / 0.45) * 0.18 : 0.32 * (1 - clamp01((r - 0.45) / 0.55));
  }));

  // ---- small lights: tracker LED, the boombox's level meter ----
  b.node('leds');
  b.box(glow(0x3dff7a, 3), [0.012, 0.012, 0.006], [tx - 0.04, ty + 0.02, front + 0.032]);
  b.push(boom);
  for (let i = 0; i < 5; i++) b.box(glow(i > 2 ? 0xff5a2a : 0x3dff7a, 2.4), [0.016, 0.008, 0.004], [-0.04 + i * 0.022, 0.262, 0.194]);
  b.pop();
  b.root();

  b.collide([-0.45, 0, -0.3], [C.x + C.w / 2 + 0.01, 0.66, 0.3], { surface: 'metal' });
  b.collide([C.x + C.w / 2 + 0.01, 0, -0.3], [0.45, 0.35, 0.3], { surface: 'rubber', bulletOnly: true });
  b.collide([C.x + C.w / 2 + 0.01, 0, -0.3], [0.45, 0.66, 0.3], { playerOnly: true });
  b.anchor('boombox', [C.boombox[0] + 0.08, 0.16, C.boombox[2]], [0, 0, 1]);
  b.anchor('beacon', [hx, by + 0.08, C.z], [0, 1, 0]);
  b.anchor('reel', [C.x, bodyTop + 0.1, C.z], [0, 1, 0]);
}

function rigMasterCase(prop, o, env) {
  const { G, materials, palette } = env;
  const C = CASE;
  const { lid, bar, reel, beacon, shaft, pool, leds } = prop.nodes;
  const lamp = materials.lamp(palette.beacon, 3);
  const shaftMat = materials.additive(palette.beacon, 0.5);
  const poolMat = materials.additive(palette.beacon, 0.5);
  beacon.children[0].material = lamp;
  shaft.children[0].material = shaftMat;
  pool.children[0].material = poolMat;
  for (const node of [shaft, pool]) {
    node.children[0].castShadow = false;
    node.children[0].receiveShadow = false;
    node.children[0].renderOrder = 2;
  }
  lid.attach(bar); // the bar rides inside the lid

  let state = 'live';
  let progress = 0;
  let shut = 0; // 0 lid up … 1 lid down
  let clock = (o.seed % 7) * 0.9; // the three reels should not pulse in step
  let ticking = false; // true once somebody calls update(): only then can the lid be seen to drop
  const worldPos = new Vector3();

  function poseLid() {
    lid.rotation.x = -C.open * (1 - shut * shut); // falls faster as it goes
  }

  function light() {
    const live = state !== 'taken';
    const grabbing = state === 'grabbing';
    reel.visible = live;
    beacon.visible = shaft.visible = pool.visible = leds.visible = live;
    bar.visible = grabbing && progress > 0.005;
    bar.scale.x = Math.max(0.001, progress);
    if (!live) return;
    const rate = grabbing ? C.pulse + (C.pulseGrab - C.pulse) * progress : C.pulse;
    const wave = 0.5 + 0.5 * Math.sin(clock * rate);
    const k = grabbing ? 0.75 + 0.25 * wave + progress : 0.45 + 0.55 * wave;
    lamp.color.copy(lamp.userData.base).multiplyScalar(1.2 + 3.2 * k);
    shaftMat.opacity = 0.16 + 0.3 * k;
    poolMat.opacity = 0.2 + 0.3 * k;
    // The shaft widens with distance so it reads from across the block without flaring up close.
    const far = G.camera ? G.camera.position.distanceTo(prop.object.getWorldPosition(worldPos)) : 10;
    const wide = Math.min(3.2, Math.max(0.6, far / 9)) * (grabbing ? 1 - 0.45 * progress : 1);
    shaft.scale.set(wide, 1, wide);
    leds.visible = Math.sin(clock * 9.2) > -0.3; // the meters dance to a beat nobody else hears
  }

  prop.state = state;
  prop.setState = (next, t = 0) => {
    state = next === 'grabbing' || next === 'taken' ? next : 'live';
    prop.state = state;
    progress = state === 'grabbing' ? clamp01(t) : 0;
    if (state !== 'taken') shut = 0;
    else if (!ticking) shut = 1;
    poseLid();
    light();
  };
  prop.update = (dt) => {
    ticking = true;
    clock += dt;
    if (state === 'taken' && shut < 1) {
      shut = Math.min(1, shut + dt / C.lidTime);
      poseLid();
    }
    light();
  };
  poseLid();
  light();
}

// ---- explosives ------------------------------------------------------------------------------------

const WHITE = 0xe6e4dc;
const RED = 0xb3261e;
const BRASS = 0xb58a3a;
const STEEL = 0x2a2d31;
const SOOT = 0x0c0b0a;
const OXYGEN = 0x2f6b4f;
const ACETYLENE = 0x7a1a1a;

/** A teardrop of flame along +Y from the origin, white-hot at the root and gone at the tip. */
function flameGeo(length, girth) {
  const geo = latheGeo([[0, 0], [girth, length * 0.14], [girth * 0.7, length * 0.6], [0, length]], 6, { crease: 60 });
  return fadeBy(geo, (x, y) => 1 - clamp01(y / length) ** 0.8);
}

/**
 * setState('idle' | 'lit' | 'gone') for a prop built with 'body', 'flame' and 'wreck' nodes.
 * Lit, the body glows with heat. The flame at the valve is only shown when fx is a stub: the real
 * explosives module puts an fx jet at the bullet hole, and one fire per tank is enough.
 */
function rigExplosive(prop, o, env) {
  const { G, materials } = env;
  const { body, flame, wreck } = prop.nodes;
  const shell = body.children.find((mesh) => mesh.name === '@vc');
  const cold = shell.material;
  const hot = materials.resolve('@vchot');
  const fire = materials.additive(0xffa040, 0.9);
  const mesh = flame.children[0];
  mesh.material = fire;
  mesh.castShadow = false;
  mesh.receiveShadow = false;
  const rest = flame.quaternion.clone();
  const spin = new Quaternion();
  const axis = new Vector3(0, 1, 0);
  let state = 'idle';
  let clock = o.seed % 10;

  function apply() {
    const fxIsStub = !G.build || !Array.isArray(G.build.stubbed) || G.build.stubbed.includes('fx');
    body.visible = state !== 'gone';
    shell.material = state === 'lit' ? hot : cold;
    flame.visible = state === 'lit' && fxIsStub;
    wreck.visible = state === 'gone';
  }
  prop.state = state;
  prop.setState = (next) => {
    state = next === 'lit' || next === 'gone' ? next : 'idle';
    prop.state = state;
    apply();
  };
  prop.update = (dt) => {
    if (!flame.visible) return;
    clock += dt;
    // A gas jet: it roars, stretches and never holds still.
    const stretch = 1 + 0.28 * Math.sin(clock * 41) + 0.18 * Math.sin(clock * 67 + 1.3);
    flame.scale.set(1 + 0.2 * Math.sin(clock * 53), stretch, 1 + 0.2 * Math.sin(clock * 47 + 2));
    flame.quaternion.copy(rest).multiply(spin.setFromAxisAngle(axis, clock * 9));
    fire.opacity = 0.75 + 0.25 * Math.sin(clock * 59);
  };
  apply();
}

/** A gas cylinder standing at (x, z): shoulder, neck ring, brass valve. */
function cylinder(b, x, z, r, h, color) {
  b.lathe('@vc', [[0, 0], [r - 0.01, 0], [r, 0.012], [r, h - r * 0.9], [r * 0.72, h - r * 0.32], [0.035, h - 0.04], [0.035, h]], [x, 0, z], { seg: 10, color });
  b.cyl('@vc', 0.022, 0.07, [x, h + 0.035, z], { seg: 6, color: BRASS });
  b.cyl('@vc', 0.04, 0.014, [x, h + 0.075, z], { seg: 6, color: STEEL });
}

export function registerGameplay(R) {
  R.add('master_case', {
    // Three of these on the block, never merged: one paint for the case, truck and boombox, real gold for the reel.
    flatten: { keep: ['gold'] },
    build: buildMasterCase,
    rig: rigMasterCase,
  });

  R.add('propane_tank', {
    build(b) {
      b.node('body');
      const r = 0.152;
      b.lathe('@vc', [[0.105, 0], [0.125, 0], [0.125, 0.045], [0.105, 0.045]], [0, 0, 0], { seg: 10, color: STEEL });
      b.lathe('@vc', [[0, 0.03], [0.1, 0.03], [r - 0.006, 0.075], [r, 0.11], [r, 0.33]], [0, 0, 0], { seg: 10, color: WHITE });
      b.lathe('@vc', [[r, 0.33], [r - 0.01, 0.39], [0.105, 0.445], [0.045, 0.47], [0, 0.47]], [0, 0, 0], { seg: 10, color: RED });
      // Collar with its two hand holes left open at the sides, valve and handwheel inside it.
      for (const a of [0, Math.PI]) {
        b.lathe('@vc', [[0.1, 0.45], [0.1, 0.585], [0.092, 0.585], [0.092, 0.45]], [0, 0, 0], { seg: 5, arc: Math.PI * 0.72, rot: [0, a + Math.PI * 0.14, 0], color: WHITE });
      }
      b.cyl('@vc', 0.02, 0.07, [0, 0.5, 0], { seg: 6, color: BRASS });
      b.cyl('@vc', 0.016, 0.06, [0, 0.515, 0.04], { axis: 'z', seg: 5, color: BRASS });
      b.cyl('@vc', 0.04, 0.012, [0, 0.55, 0], { seg: 6, color: RED });
      b.decal('flame', [0, 0.215, r], 0.13, 0.13, '+z', { lift: 0.014 });
      b.decal('flame', [0, 0.215, -r], 0.13, 0.13, '-z', { lift: 0.014 });

      b.node('flame', [0, 0.52, 0.07]);
      b.add(RIGGED, flameGeo(0.75, 0.07), xf(0, 0.52, 0.07, 0.95, 0, 0));

      b.node('wreck');
      b.lathe('@vc', [[0.09, 0], [0.13, 0], [0.125, 0.05], [0.1, 0.035], [0.09, 0.06]], [0, 0, 0], { seg: 7, color: SOOT, rot: [0.08, 0.3, 0.05] });
      b.box('@vc', [0.16, 0.012, 0.11], [0.05, 0.02, -0.04], { rot: [0.2, 0.6, -0.25], color: SOOT });
      b.root();

      b.collide([-0.16, 0, -0.16], [0.16, 0.6, 0.16], { surface: 'metal' });
      b.anchor('jet', [0, 0.52, 0.07], [0, 0.58, 0.81]);
    },
    rig: rigExplosive,
  });

  R.add('welding_rack', {
    build(b) {
      b.node('body');
      // A bottle cart: base plate, a back frame with a chain, three cylinders, regulators and hoses.
      b.box('@vc', [0.9, 0.04, 0.5], [0, 0.02, 0], { color: STEEL });
      for (const x of [-0.42, 0.42]) b.box('@vc', [0.04, 1.3, 0.04], [x, 0.69, -0.22], { color: STEEL });
      for (const y of [0.5, 1.0, 1.32]) b.box('@vc', [0.88, 0.04, 0.03], [0, y, -0.225], { color: STEEL });
      b.box('@vc', [0.9, 0.02, 0.012], [0, 0.82, 0.215], { color: STEEL }); // chain
      cylinder(b, -0.28, 0, 0.115, 1.42, OXYGEN);
      cylinder(b, 0, 0, 0.115, 1.42, OXYGEN);
      cylinder(b, 0.28, 0, 0.14, 1.12, ACETYLENE);
      // Regulators with two gauges each, and the twin hose looped over the frame.
      for (const [x, h] of [[0, 1.42], [0.28, 1.12]]) {
        b.box('@vc', [0.07, 0.05, 0.05], [x + 0.06, h + 0.04, 0.02], { color: BRASS });
        for (const dz of [-0.03, 0.05]) {
          b.cyl('@vc', 0.028, 0.02, [x + 0.1, h + 0.07, dz], { axis: 'x', seg: 8, color: WHITE });
        }
      }
      const loop = (dx, color) => b.tube('@vc', [
        [0.34 + dx, 1.2, 0.05], [0.4 + dx, 1.37, -0.1], [0.38 + dx, 1.33, -0.24], [0.34 + dx, 1.05, -0.262],
        [0.385 + dx, 0.82, -0.262], [0.43 + dx, 1.05, -0.262], [0.415 + dx, 1.3, -0.262],
      ], 0.011, { radial: 4, segments: 16, color });
      loop(0, RED);
      loop(-0.024, OXYGEN);
      b.box('@vc', [0.03, 0.2, 0.03], [0.42, 1.38, -0.262], { rot: [0, 0, 0.2], color: BRASS }); // the torch
      b.decal('gas_placard', [-0.14, 0.5, 0.12], 0.36, 0.25, '+z', { lift: 0.004 });
      b.box('@vc', [0.38, 0.27, 0.01], [-0.14, 0.5, 0.118], { color: WHITE });

      b.node('flame', [0.28, 1.2, 0.03]);
      b.add(RIGGED, flameGeo(0.9, 0.08), xf(0.28, 1.2, 0.03, 0.8, 0, -0.25));

      b.node('wreck');
      b.box('@vc', [0.86, 0.035, 0.46], [0, 0.03, 0], { rot: [0.03, 0.1, 0.04], color: SOOT });
      b.box('@vc', [0.04, 0.7, 0.04], [-0.4, 0.3, -0.2], { rot: [0.5, 0, 0.6], color: SOOT });
      b.box('@vc', [0.04, 0.5, 0.04], [0.36, 0.2, -0.16], { rot: [-0.3, 0, -0.9], color: SOOT });
      b.root();

      b.collide([-0.45, 0, -0.25], [0.45, 1.5, 0.25], { surface: 'metal' });
      b.anchor('jet', [0.28, 1.2, 0.03], [-0.18, 0.68, 0.71]);
    },
    rig: rigExplosive,
  });
}
