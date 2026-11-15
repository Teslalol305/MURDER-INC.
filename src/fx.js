// G.fx (CONTRACT 6.8): tracers, muzzle flashes, impacts, explosions, brass, debris, decals and emitters.
//
//   fx/sim.js        particle simulation on typed arrays (pure)
//   fx/particles.js  the two billboard pools as instanced quads: lit (sorted, alpha) and additive
//   fx/atlas.js      procedural sprite and decal sheets
//   fx/tracers.js    pooled travelling streaks
//   fx/bits.js       instanced brass and debris with bounce physics
//   fx/decals.js     ring buffer of bullet holes and scorch marks
//   fx/emitters.js   steam, smolder, embers, fire, drip, jet
//   fx/recipes.js    what each effect is made of
//
// Six draw calls in the world (decals, lit, additive, tracers, shells, debris) and one on the viewmodel.
// Budgets follow G.quality.fx: it caps the pools and thins every recipe. Nothing here allocates per
// frame; `impact`, `explosion` and `player:land` events run their effects by themselves.

import * as THREE from 'three';
import { clamp } from './core/util.js';
import { LIT, additiveSheet, decalSheet, litSheet } from './fx/atlas.js';
import { createDebris, createShells } from './fx/bits.js';
import { createDecals } from './fx/decals.js';
import { createEmitters } from './fx/emitters.js';
import { createPoolMesh } from './fx/particles.js';
import { createRecipes } from './fx/recipes.js';
import { FX_LIGHTS, createCommonUniforms, createLightSampler, createRandom, readFog, sheetTexture } from './fx/shared.js';
import { createSpec, createStore, integrate, sortBackToFront, writeInstances } from './fx/sim.js';
import { createTracers } from './fx/tracers.js';

// Budgets at G.quality.fx = 1.
const LIT_PARTICLES = 1400;
const ADD_PARTICLES = 3040;
const VIEW_PARTICLES = 32; // first-person muzzle flash sprites
const TRACERS = 48;
const DEBRIS = 256;
const SHELLS = 60;
const DECALS = 256;
const EMITTERS = 24;
const MIN_QUALITY = 0.25;

const FAR = 55; // particle counts halve beyond this distance from the camera…
const NOTHING = 150; // …and nothing is spawned beyond this
const SHADOWED = 0.12; // share of the key light that reaches a spot the key cannot see
const TRACER_SKIP = 1.1; // metres of a tracer's path hidden at the muzzle (no fat streak in the face)
const TRACER_WIDTH = 0.035;
const TRACER_GLOW = 8; // HDR gain of the tracer colour
const TRAIL_EVERY = 0.07; // seconds between tracer smoke trails
const MINOR_LIGHT_EVERY = 0.07; // seconds between small impact light flashes
const LIGHT_RANGE = 75; // no pooled light is spent on something further than this from the camera
const SAMPLE_EVERY = 0.5; // seconds between readings of the scene lights
const WIND = [0.5, 0.2]; // m/s toward +X (east) and +Z; gusts ride on top
const HARD_LANDING = 5; // m/s: a landing faster than this raises a full dust ring
const VIEWMODEL_FLASH = 'muzzle-flash'; // name of the weapon module's own first-person flash, when it has one

export function createFx(G) {
  const scene = G.scene;
  const camera = G.camera;
  const random = createRandom(0x51a9e37);
  const common = createCommonUniforms();
  const sampler = createLightSampler(common, scene, () => (G.atmos && G.atmos.sun) || null);

  // ---------------------------------------------------------------------------------------------
  // Pools
  // ---------------------------------------------------------------------------------------------

  const litTexture = sheetTexture(litSheet(), 'fx-lit');
  const addTexture = sheetTexture(additiveSheet(), 'fx-additive');
  const decalTexture = sheetTexture(decalSheet(), 'fx-decals');

  const lit = createStore(LIT_PARTICLES);
  const add = createStore(ADD_PARTICLES);
  const view = createStore(VIEW_PARTICLES);
  const order = new Uint16Array(LIT_PARTICLES);
  const keys = new Float32Array(LIT_PARTICLES);

  const root = new THREE.Group();
  root.name = 'fx';
  root.matrixAutoUpdate = false;
  scene.add(root);

  const decals = createDecals({ capacity: DECALS, texture: decalTexture, common, renderOrder: 5 });
  const litMesh = createPoolMesh({ kind: 'lit', capacity: LIT_PARTICLES, texture: litTexture, common, name: 'fx-lit', renderOrder: 20 });
  const addMesh = createPoolMesh({ kind: 'additive', capacity: ADD_PARTICLES, texture: addTexture, common, name: 'fx-additive', renderOrder: 21 });
  const tracers = createTracers({ capacity: TRACERS, common, renderOrder: 22 });
  const viewMesh = createPoolMesh({
    kind: 'additive',
    capacity: VIEW_PARTICLES,
    texture: addTexture,
    common,
    name: 'fx-viewmodel-flash',
    renderOrder: 50,
    space: 'view',
  });

  // ---------------------------------------------------------------------------------------------
  // World queries
  // ---------------------------------------------------------------------------------------------

  const rayFrom = new THREE.Vector3();
  const rayDir = new THREE.Vector3();
  const rayHit = { dist: 0, point: new THREE.Vector3(), normal: new THREE.Vector3(), surface: null, box: null };
  const DOWN = new THREE.Vector3(0, -1, 0);

  const floorAt = (x, z, maxY) => G.physics.groundHeight(x, z, maxY);

  /** How much of the key light reaches a point: 1 in the open, SHADOWED under a roof or behind a wall. */
  function shadeAt(x, y, z) {
    rayFrom.set(x, y, z);
    return G.physics.raycast(rayFrom, common.uKeyDir.value, 60, rayHit) ? SHADOWED : 1;
  }

  /** First wall within `reach` metres along the horizontal direction (dx, dz); writes out.dist. */
  function wallAhead(x, y, z, dx, dz, reach, out) {
    rayFrom.set(x, y, z);
    rayDir.set(dx, 0, dz);
    const hit = G.physics.raycast(rayFrom, rayDir, reach, rayHit);
    if (!hit) return false;
    out.dist = hit.dist;
    return true;
  }

  function surfaceAt(x, y, z) {
    rayFrom.set(x, y + 0.3, z);
    const hit = G.physics.raycast(rayFrom, DOWN, 0.8, rayHit);
    return (hit && hit.surface) || 'asphalt';
  }

  const world = { floorAt, wallAhead };

  // ---------------------------------------------------------------------------------------------
  // Quality and distance
  // ---------------------------------------------------------------------------------------------

  // Numbers that change every frame live in one object: its fields are updated in place, where a
  // closure variable would put a fresh boxed number on the heap at every write.
  const state = {
    quality: 1, // G.quality.fx, clamped
    clock: 0, // seconds of effects time (stops while paused)
    sinceSample: SAMPLE_EVERY,
    sinceTrail: 1,
    sinceMinorLight: 1,
    flash: 0, // our share of render.post.flash …
    flashWritten: -1, // … and the value last written there
    ms: 0, // cost of the last update
  };

  function applyQuality() {
    state.quality = clamp(G.quality && G.quality.fx > 0 ? G.quality.fx : 1, MIN_QUALITY, 1);
    lit.budget = Math.round(LIT_PARTICLES * state.quality);
    add.budget = Math.round(ADD_PARTICLES * state.quality);
    debris.budget = DEBRIS * state.quality;
  }

  function cameraDistanceSq(x, y, z) {
    const p = camera.position;
    const dx = x - p.x;
    const dy = y - p.y;
    const dz = z - p.z;
    return dx * dx + dy * dy + dz * dz;
  }

  /** Particle multiplier for an effect at a point: the quality factor, halved far away, zero out of sight. */
  function density(x, y, z) {
    const d2 = cameraDistanceSq(x, y, z);
    if (d2 > NOTHING * NOTHING) return 0;
    return d2 > FAR * FAR ? state.quality * 0.5 : state.quality;
  }

  // ---------------------------------------------------------------------------------------------
  // Lights: pooled flashes for the world, and the few that also shine on the smoke
  // ---------------------------------------------------------------------------------------------

  const lightPos = new THREE.Vector3();
  const lightColor = new THREE.Color();

  // Blast flashes that light the lit pool: x y z, r g b, intensity, range, ttl, life.
  const FLASH = 10;
  const flashes = new Float32Array(FX_LIGHTS * FLASH);
  // The strongest lights this frame (flashes and burning emitters), written to the shared uniforms.
  const strongest = new Float32Array(FX_LIGHTS * 8); // x y z, r g b, intensity, range
  let strongestCount = 0;

  /** Offers one light for the lit pool; the FX_LIGHTS brightest of a frame win. */
  function smokeLight(x, y, z, r, g, b, intensity, range) {
    if (intensity <= 0) return;
    let at = strongestCount;
    if (at >= FX_LIGHTS) {
      at = 0;
      for (let i = 1; i < FX_LIGHTS; i++) if (strongest[i * 8 + 6] < strongest[at * 8 + 6]) at = i;
      if (strongest[at * 8 + 6] >= intensity) return;
    } else {
      strongestCount++;
    }
    const o = at * 8;
    strongest[o] = x;
    strongest[o + 1] = y;
    strongest[o + 2] = z;
    strongest[o + 3] = r;
    strongest[o + 4] = g;
    strongest[o + 5] = b;
    strongest[o + 6] = intensity;
    strongest[o + 7] = range;
  }

  /**
   * A pooled light flash. Small ones (impacts) are rationed so that a burst of fire on sheet metal
   * cannot take the whole pool; `smoke` flashes (blasts) also light the lit particles while they fade.
   */
  function light(x, y, z, hex, intensity, range, ttl, smoke) {
    if (cameraDistanceSq(x, y, z) > LIGHT_RANGE * LIGHT_RANGE) return;
    if (!smoke && intensity < 20) {
      if (state.sinceMinorLight < MINOR_LIGHT_EVERY) return;
      state.sinceMinorLight = 0;
    }
    lightPos.set(x, y, z);
    G.render.lights.flash(lightPos, hex, intensity, range, ttl);
    if (!smoke) return;
    // Takes the slot of the flash that is nearest its end.
    let at = 0;
    for (let i = 1; i < FX_LIGHTS; i++) if (flashes[i * FLASH + 8] < flashes[at * FLASH + 8]) at = i;
    const o = at * FLASH;
    lightColor.set(hex);
    flashes[o] = x;
    flashes[o + 1] = y;
    flashes[o + 2] = z;
    flashes[o + 3] = lightColor.r;
    flashes[o + 4] = lightColor.g;
    flashes[o + 5] = lightColor.b;
    flashes[o + 6] = intensity;
    flashes[o + 7] = range;
    flashes[o + 8] = flashes[o + 9] = ttl * 1.6; // smoke holds the glow a little longer than the walls do
  }

  function updateSmokeLights(dt) {
    for (let i = 0; i < FX_LIGHTS; i++) {
      const o = i * FLASH;
      if (flashes[o + 8] <= 0) continue;
      flashes[o + 8] -= dt;
      if (flashes[o + 8] <= 0) continue;
      const k = flashes[o + 8] / flashes[o + 9];
      smokeLight(flashes[o], flashes[o + 1], flashes[o + 2], flashes[o + 3], flashes[o + 4], flashes[o + 5], flashes[o + 6] * k, flashes[o + 7]);
    }
    const positions = common.uLightPos.value;
    const colors = common.uLightCol.value;
    for (let i = 0; i < FX_LIGHTS; i++) {
      const o = i * 8;
      if (i < strongestCount) {
        positions[i].set(strongest[o], strongest[o + 1], strongest[o + 2], strongest[o + 7]);
        colors[i].set(strongest[o + 3], strongest[o + 4], strongest[o + 5]).multiplyScalar(strongest[o + 6]);
      } else {
        positions[i].set(0, -1000, 0, 1);
        colors[i].set(0, 0, 0);
      }
    }
    strongestCount = 0;
  }

  // ---------------------------------------------------------------------------------------------
  // Recipes, bits, emitters
  // ---------------------------------------------------------------------------------------------

  const viewPoint = new THREE.Vector3();
  const viewQuat = new THREE.Quaternion();

  const ctx = {
    lit,
    add,
    view,
    spec: createSpec(),
    random,
    density,
    floorAt,
    shadeAt,
    light,
    smokeLight,
    decals,
    debris: null, // set below
    acquireLight: () => G.render.lights.acquire(),
    cameraDistance: (x, y, z) => Math.sqrt(cameraDistanceSq(x, y, z)),
  };

  const debris = createDebris({ capacity: DEBRIS, world });
  ctx.debris = debris;
  applyQuality();
  const bounce = new THREE.Vector3();
  const shells = createShells({
    capacity: SHELLS,
    world,
    onBounce(x, y, z) {
      G.events.emit('shell:bounce', { pos: bounce.set(x, y, z).clone(), surface: surfaceAt(x, y, z) });
    },
  });
  const recipes = createRecipes(ctx);
  const emitters = createEmitters(ctx, EMITTERS);

  root.add(decals.mesh, shells.mesh, debris.mesh, litMesh.mesh, addMesh.mesh, tracers.mesh);
  G.vmCamera.add(viewMesh.mesh);

  // ---------------------------------------------------------------------------------------------
  // Public effects
  // ---------------------------------------------------------------------------------------------

  const unit = new THREE.Vector3();
  const tint = [0, 0, 0];
  const color = new THREE.Color();

  /** `v` as a unit vector in `unit`, or `fallback` (x, y, z) when it is missing or has no length. */
  function unitOf(v, fx, fy, fz) {
    if (v) unit.set(v.x, v.y, v.z);
    if (!v || unit.lengthSq() < 1e-10) unit.set(fx, fy, fz);
    return unit.normalize();
  }

  // The weapon module may bring its own first-person flash (an object named 'muzzle-flash' in the
  // viewmodel scene). Looked up once, on the first shot: the weapon is created after fx.
  let ownsViewFlash = null;

  /**
   * Flash at a muzzle. `pos` and `dir` are world space in both modes. No light is flashed here: the
   * shooter (weapon, enemies) flashes its own, at its own strength and rhythm.
   */
  function muzzleFlash(pos, dir, scale = 1, inWorld = true) {
    if (!pos) return;
    const d = unitOf(dir, 0, 0, -1);
    if (inWorld) {
      recipes.muzzleFlash(pos.x, pos.y, pos.z, d.x, d.y, d.z, scale);
      return;
    }
    // First person: a few sparks spat into the world …
    recipes.muzzleSparks(pos.x + d.x * 0.3, pos.y + d.y * 0.3, pos.z + d.z * 0.3, d.x, d.y, d.z, 2);
    // … and the flash itself, unless the viewmodel draws one.
    if (ownsViewFlash === null) ownsViewFlash = !G.vmScene.getObjectByName(VIEWMODEL_FLASH);
    if (!ownsViewFlash) return;
    // The same point as the viewmodel camera sees it: both cameras share a transform but not a field
    // of view, so the camera-space offset is rescaled to land on the same pixel.
    const ratio = Math.tan((G.vmCamera.fov * Math.PI) / 360) / Math.tan((camera.fov * Math.PI) / 360);
    viewQuat.copy(camera.quaternion).invert();
    viewPoint.set(pos.x, pos.y, pos.z).sub(camera.position).applyQuaternion(viewQuat);
    const vx = viewPoint.x * ratio;
    const vy = viewPoint.y * ratio;
    const vz = viewPoint.z;
    viewPoint.copy(d).applyQuaternion(viewQuat);
    recipes.viewFlash(vx, vy, vz, viewPoint.x, viewPoint.y, viewPoint.z, scale);
  }

  function tracer(from, to, hex = 0xffe2a8, speed = 260) {
    if (!from || !to) return;
    let dx = to.x - from.x;
    let dy = to.y - from.y;
    let dz = to.z - from.z;
    const length = Math.hypot(dx, dy, dz);
    if (length < 0.5) return;
    dx /= length;
    dy /= length;
    dz /= length;
    // Leave the first stretch out when there is room, so the streak does not start in the viewer's face.
    const skip = length > TRACER_SKIP * 3 ? TRACER_SKIP : 0;
    color.set(hex);
    tracers.sim.add(
      from.x + dx * skip,
      from.y + dy * skip,
      from.z + dz * skip,
      dx,
      dy,
      dz,
      length - skip,
      speed > 1 ? speed : 260,
      color.r * TRACER_GLOW,
      color.g * TRACER_GLOW,
      color.b * TRACER_GLOW,
      TRACER_WIDTH,
    );

    // Now and then a faint thread of smoke along the first metres of the path.
    if (state.sinceTrail < TRAIL_EVERY || length < 4) return;
    state.sinceTrail = 0;
    const reach = Math.min(length, 7);
    const k = density(from.x, from.y, from.z);
    for (let i = 0; i < 5 && k > 0; i++) {
      const at = 0.8 + ((reach - 0.8) * (i + random())) / 5;
      const idx = recipes.litPuff(
        from.x + dx * at,
        from.y + dy * at,
        from.z + dz * at,
        dx * 0.6 + random.signed() * 0.1,
        dy * 0.6 + 0.12,
        dz * 0.6 + random.signed() * 0.1,
        recipes.dustTint('concrete'),
        0.05,
        random.range(0.16, 0.26),
        random.range(0.5, 0.9),
        0.09,
        LIT.wisp,
        1,
        -1000,
        true,
      );
      if (idx < 0) break;
    }
  }

  function impactAt(point, normal, surface, dir, enemy) {
    if (!point) return;
    const n = unitOf(normal, 0, 1, 0);
    const nx = n.x;
    const ny = n.y;
    const nz = n.z;
    const d = unitOf(dir, -nx, -ny, -nz);
    recipes.impact(point.x, point.y, point.z, nx, ny, nz, surface || 'concrete', d.x, d.y, d.z, !!enemy || surface === 'flesh' || surface === 'drone');
  }

  function sparks(pos, dir, n = 8) {
    if (!pos) return;
    if (dir) recipes.sparks(pos.x, pos.y, pos.z, dir.x, dir.y, dir.z, n);
    else recipes.sparks(pos.x, pos.y, pos.z, 0, 0, 0, n);
  }

  function smoke(pos, scale = 1) {
    if (pos) recipes.smoke(pos.x, pos.y, pos.z, scale);
  }

  function dust(pos, scale = 1) {
    if (pos) recipes.dust(pos.x, pos.y, pos.z, scale);
  }

  function puff(pos, hex = 0xb9b6ae, scale = 1) {
    if (!pos) return;
    color.set(hex);
    tint[0] = color.r;
    tint[1] = color.g;
    tint[2] = color.b;
    recipes.puff(pos.x, pos.y, pos.z, tint, scale);
  }

  const sitePos = new THREE.Vector3();

  function explosionAt(pos, scale, flavour) {
    if (!pos) return;
    const size = clamp(scale > 0 ? scale : 1, 0.25, 2.5);
    recipes.explosion(pos.x, pos.y, pos.z, size, flavour);

    // A blast on the ground leaves something burning for a while.
    const floor = floorAt(pos.x, pos.z, pos.y + 0.3);
    if (pos.y - floor < 3) {
      sitePos.set(pos.x, floor + 0.1, pos.z);
      emitters.add(sitePos, 'smolder', { ttl: 5 + 2 * size, scale: 0.9 * size });
      emitters.add(sitePos, 'embers', { ttl: 1.6 + size, scale: size });
    }

    const dist = Math.sqrt(cameraDistanceSq(pos.x, pos.y, pos.z));
    const near = clamp(1 - dist / (16 + 8 * size), 0, 1);
    // The screen flash of a close blast (fx owns render.post.flash only while its own value is the one there).
    state.flash = Math.max(state.flash, near * near * 0.6 * Math.min(1.2, size));
  }

  function explosion(pos, scale = 1) {
    explosionAt(pos, scale, 'fuel');
  }

  function shell(pos, vel, kind = 'rifle') {
    if (!pos) return;
    shells.add(pos.x, pos.y, pos.z, vel ? vel.x : 0, vel ? vel.y : 0, vel ? vel.z : 0, kind, random);
  }

  function debrisBurst(pos, n = 6, hex = 0x3a3a3c, speed = 5) {
    if (!pos) return;
    const k = density(pos.x, pos.y, pos.z);
    if (k <= 0) return;
    color.set(hex);
    const count = Math.round(n * k);
    for (let i = 0; i < count; i++) {
      const a = random() * Math.PI * 2;
      const out = random.range(0.3, 1) * speed;
      const size = random.range(0.03, 0.09);
      const shade = random.range(0.7, 1.15);
      debris.add(
        pos.x,
        pos.y,
        pos.z,
        Math.cos(a) * out,
        random.range(0.4, 1.1) * speed,
        Math.sin(a) * out,
        size * random.range(1, 2),
        size * 0.6,
        size,
        color.r * shade,
        color.g * shade,
        color.b * shade,
        random.range(1.8, 3.4),
        random,
      );
    }
  }

  function decal(point, normal, kind = 'bullet', size) {
    if (!point) return;
    const entry = recipes.decalEntry(kind);
    if (!entry) return;
    const n = unitOf(normal, 0, 1, 0);
    const s = size > 0 ? size : random.range(entry[1], entry[2]);
    const shade = shadeAt(point.x + n.x * 0.2, point.y + n.y * 0.2, point.z + n.z * 0.2);
    decals.add(point.x, point.y, point.z, n.x, n.y, n.z, s, random() * Math.PI * 2, entry[0], entry[3], shade);
  }

  function clear() {
    lit.count = add.count = view.count = 0;
    litMesh.commit(0);
    addMesh.commit(0);
    viewMesh.commit(0);
    tracers.clear();
    shells.clear();
    debris.clear();
    decals.clear();
    emitters.clear();
    flashes.fill(0);
    if (G.render.post.flash === state.flashWritten) G.render.post.flash = 0;
    state.flash = 0;
    state.flashWritten = -1;
  }

  // ---------------------------------------------------------------------------------------------
  // Update
  // ---------------------------------------------------------------------------------------------

  const forward = new THREE.Vector3();
  const env = new Float64Array(4); // dt, clock, wind x, wind z
  const still = new Float64Array(4); // the same without wind
  const viewer = new Float64Array(6); // eye, view direction

  function update(dt) {
    const t0 = performance.now();
    state.clock += dt;
    state.sinceTrail += dt;
    state.sinceMinorLight += dt;
    const clock = state.clock;

    applyQuality();
    state.sinceSample += dt;
    if (state.sinceSample >= SAMPLE_EVERY) {
      state.sinceSample = 0;
      sampler.sample();
      readFog(common, scene);
    }
    // Thinnest drawable streak: a pixel and a quarter at the internal resolution.
    const pixels = Math.max(240, G.renderer.domElement.height * (G.quality.scale || 1));
    common.uPixel.value = (2 * Math.tan((camera.fov * Math.PI) / 360) * 1.25) / pixels;

    // A light breeze down the avenue with slow gusts; the viewmodel flash feels none of it.
    env[0] = still[0] = dt;
    env[1] = still[1] = clock;
    env[2] = WIND[0] + 0.3 * Math.sin(clock * 0.31) + 0.12 * Math.sin(clock * 1.7);
    env[3] = WIND[1] + 0.22 * Math.sin(clock * 0.23 + 1);
    integrate(lit, env);
    integrate(add, env);
    integrate(view, still);
    // Emitters run after the step, so what they make this frame is drawn where it was born: a jet
    // stays attached to its valve instead of starting a frame's travel away from it.
    emitters.update(dt);

    camera.getWorldDirection(forward);
    viewer[0] = camera.position.x;
    viewer[1] = camera.position.y;
    viewer[2] = camera.position.z;
    viewer[3] = forward.x;
    viewer[4] = forward.y;
    viewer[5] = forward.z;
    sortBackToFront(lit, order, keys, viewer);
    litMesh.commit(writeInstances(lit, litMesh.array, order));
    addMesh.commit(writeInstances(add, addMesh.array, null));
    viewMesh.commit(writeInstances(view, viewMesh.array, null));

    tracers.update(dt);
    shells.update(dt);
    debris.update(dt);
    updateSmokeLights(dt);

    // Screen flash: written only while nobody else has changed the value since our last write.
    if (state.flash > 0) {
      const post = G.render.post;
      if (post.flash === state.flashWritten || state.flash > post.flash) {
        post.flash = state.flashWritten = state.flash;
      }
      state.flash = state.flash > 0.004 ? state.flash * Math.exp(-7 * dt) : 0;
      if (state.flash === 0 && post.flash === state.flashWritten) post.flash = 0;
    }
    state.ms = performance.now() - t0;
  }

  // ---------------------------------------------------------------------------------------------
  // Automatic effects
  // ---------------------------------------------------------------------------------------------

  G.events.on('impact', (e) => {
    if (e) impactAt(e.point, e.normal, e.surface, e.dir, e.enemy);
  });

  G.events.on('explosion', (e) => {
    if (!e || !e.pos) return;
    // Size from the blast radius: a propane tank (6.5 m) is 1, a Buzzard's burst about half.
    const scale = e.radius > 0 ? clamp(e.radius / 6.5, 0.4, 1.6) : e.size === 'big' ? 1 : 0.5;
    explosionAt(e.pos, scale, e.source && e.source.type === 'buzzard' ? 'drone' : 'fuel');
  });

  // Whatever stood there is gone: marks on it would be left hanging in the air.
  G.events.on('explosive:blast', (e) => {
    if (e && e.pos) decals.removeNear(e.pos.x, e.pos.y, e.pos.z, 1.3);
  });

  G.events.on('player:land', (e) => {
    const p = G.player && G.player.pos;
    if (!e || !p || !(e.speed > 2.5)) return;
    recipes.landing(p.x, p.y, p.z, e.speed > HARD_LANDING ? clamp((e.speed - HARD_LANDING) / 6 + 0.4, 0.4, 1) : 0.1, e.surface);
  });

  sampler.scan();
  sampler.sample();
  readFog(common, scene);
  // Lights may have been added by modules created after this one.
  G.events.on('boot:done', () => {
    sampler.scan();
    sampler.sample();
    readFog(common, scene);
  });

  function stats() {
    return {
      lit: lit.count,
      additive: add.count,
      tracers: tracers.sim.count,
      debris: debris.count,
      shells: shells.count,
      decals: decals.count,
      emitters: emitters.count,
      budget: { lit: lit.budget, additive: add.budget, tracers: TRACERS, debris: debris.budget, shells: SHELLS, decals: DECALS, emitters: EMITTERS },
      spawned: lit.spawned + add.spawned,
      recycled: lit.stolen + add.stolen,
      refused: lit.dropped + add.dropped,
      decalsPlaced: decals.total,
      quality: state.quality,
      ms: state.ms,
    };
  }

  return {
    muzzleFlash,
    tracer,
    impact: (point, normal, surface, dir) => impactAt(point, normal, surface, dir, null),
    sparks,
    smoke,
    dust,
    puff,
    explosion,
    shell,
    debris: debrisBurst,
    decal,
    addEmitter: (pos, kind, opts) => emitters.add(pos, kind, opts),
    clear,
    stats,
    update,
  };
}
