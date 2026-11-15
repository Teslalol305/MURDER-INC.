// Atmosphere (`G.atmos`, CONTRACT 6.11): sky, light and life. Night, sodium and neon.
//
//   src/atmos/fog.js        the haze: scene.fog, thicker past the bounds, tinted by where you look
//   src/atmos/sky.js        the sky dome and the PMREM environment captured from it
//   src/atmos/lights.js     the shadow-casting key, the ambient, real lights for the top-priority lamps
//   src/atmos/lampfield.js  light pools, cones and glows for every lamp (three draw calls)
//   src/atmos/farcity.js    the next blocks, the skyline rings, the El and the street beyond the bounds
//   src/atmos/train.js      the El train (emits `train:pass`)
//   src/atmos/life.js       steam, moths and dust, loose paper, the hydrant's spray
//   src/atmos/plan.js       the logic behind all of it that needs no renderer (unit-tested)
//
// Everything is built once at boot, including what the current quality preset does not show: presets
// only switch layers on and off (config/look.js `detail`), and the number of real lights is fixed at boot
// (`quality.lights`), so no shader is ever recompiled while the game runs.
//
// Tuning lives in src/config/look.js.

import * as THREE from 'three';
import { clamp, clamp01, damp, lerp } from './core/util.js';
import { createFarCity } from './atmos/farcity.js';
import { createFog } from './atmos/fog.js';
import { createLampField } from './atmos/lampfield.js';
import { createLife } from './atmos/life.js';
import { collectLamps, createKeyLight, createLightRig } from './atmos/lights.js';
import { continueRow, interiorTarget, rowStep } from './atmos/plan.js';
import { createEnvironment, createSky } from './atmos/sky.js';
import { createTrain } from './atmos/train.js';

const FALLBACK_BOUNDS = { minX: -46, maxX: 46, minZ: -34, maxZ: 34 };
const TIME_WRAP = 7200; // shader time wraps every two hours to keep its float precision
const ROAD_HALF = 7; // kerb to kerb is 14 m (DESIGN section 4)
const WALK_OUTER = 11.5;

/**
 * How far along the street the level's own geometry fills the space of the El's deck. Levels may carry
 * the line on past their bounds as decor; the atmosphere continues it from wherever it stops.
 */
function deckExtent(root, el) {
  const extent = { minX: el.minX, maxX: el.maxX };
  if (!root) return extent;
  const box = new THREE.Box3();
  const v = new THREE.Vector3();
  const y0 = el.y - 1;
  const y1 = el.y + 0.5;
  root.updateMatrixWorld(true);
  root.traverse((obj) => {
    const position = obj.isMesh && obj.geometry ? obj.geometry.getAttribute('position') : null;
    if (!position) return;
    if (!obj.geometry.boundingBox) obj.geometry.computeBoundingBox();
    box.copy(obj.geometry.boundingBox).applyMatrix4(obj.matrixWorld);
    if ((box.min.x >= extent.minX && box.max.x <= extent.maxX) || box.max.y < y0 || box.min.y > y1) return;
    for (let i = 0; i < position.count; i++) {
      v.fromBufferAttribute(position, i).applyMatrix4(obj.matrixWorld);
      if (v.y < y0 || v.y > y1 || v.z < el.minZ || v.z > el.maxZ) continue;
      if (v.x < extent.minX) extent.minX = v.x;
      if (v.x > extent.maxX) extent.maxX = v.x;
    }
  });
  return extent;
}

export function createAtmos(G) {
  const look = G.config.look;
  const level = G.level || {};
  const bounds = { ...(level.bounds || FALLBACK_BOUNDS) };
  const el = level.el && Number.isFinite(level.el.y) ? level.el : null;
  const avenueZ = el ? (el.minZ + el.maxZ) / 2 : (bounds.minZ + bounds.maxZ) / 2;
  const rng = G.rng.fork('atmos');

  const root = new THREE.Group();
  root.name = 'atmos';
  G.scene.add(root);

  // The haze comes first: it rewrites the fog shader, which must happen before any material is compiled.
  const haze = createFog(G, bounds);
  /** Uniform objects shared by every atmosphere shader: one write per frame reaches them all. */
  const shared = {
    haze,
    uTime: { value: 0 },
    uTrain: { value: new THREE.Vector3() },
    uWind: { value: new THREE.Vector2().fromArray(look.life.paper.wind) },
  };

  const sky = createSky(G, haze, shared.uTime);
  root.add(sky.dome);

  // ---------------------------------------------------------------------------------------------
  // Key light and ambient
  // ---------------------------------------------------------------------------------------------

  const key = createKeyLight(G, bounds, root);
  {
    // Tallest thing in the level that may cast a shadow (the train on its deck included).
    let top = el ? el.y + look.train.railOffset + look.train.carHeight : 12;
    if (level.root) {
      const box = new THREE.Box3().setFromObject(level.root);
      if (Number.isFinite(box.max.y)) top = Math.max(top, box.max.y);
    }
    key.fit(-0.5, clamp(top + 1, 12, look.sun.shadowHeight));
  }

  // ---------------------------------------------------------------------------------------------
  // Lamps
  // ---------------------------------------------------------------------------------------------

  const lamps = collectLamps(G, avenueZ);
  const elRow = { step: 10, anchor: bounds.minX + 5 }; // rhythm of the lamps under the El (columns stand between them)

  // The avenue runs on past the bounds: carry the lamps under the El and along the kerbs out into the haze.
  {
    const cfg = look.lamps.beyond;
    const sodium = new THREE.Color(look.palette.sodium);
    const virtual = (pos, kind, intensity, range, color) => {
      lamps.push({
        index: lamps.length, pos, color, intensity, range, kind, style: look.lamps.kinds[kind],
        priority: -1, dir: null, wall: null, floor: 0, real: false, virtual: true,
      });
    };
    if (el) {
      // The lamps hung under the deck (not the station's tubes above it), in order along the street.
      const own = lamps.filter((l) => l.kind === 'el' && l.pos.y < el.y).sort((a, b) => a.pos.x - b.pos.x);
      const first = own[0];
      const second = first ? own.find((l) => Math.abs(l.pos.z - first.pos.z) > 0.3) : null; // a staggered row has two sides
      const step = rowStep(own.map((l) => l.pos.x), 10);
      elRow.step = step;
      elRow.anchor = first ? first.pos.x : bounds.minX + step / 2;
      for (const x of continueRow(own.map((l) => l.pos.x), bounds.minX, bounds.maxX, cfg.reach, 10)) {
        const odd = Math.abs(Math.round((x - elRow.anchor) / step)) % 2 === 1;
        const z = first ? (odd && second ? second.pos.z : first.pos.z) : avenueZ;
        virtual(new THREE.Vector3(x, first ? first.pos.y : el.y - 0.4, z), 'el', first ? first.intensity : cfg.elIntensity, first ? first.range : cfg.elRange, first ? first.color : sodium);
      }
    }
    let side = 1;
    for (let d = 15; d < cfg.reach; d += cfg.streetEvery) {
      for (const x of [bounds.maxX + d, bounds.minX - d]) {
        virtual(new THREE.Vector3(x, cfg.streetHeight, avenueZ + side * (ROAD_HALF + 0.5)), 'street', cfg.streetIntensity, cfg.streetRange, sodium);
        side = -side;
      }
    }
  }

  // A couple of tired lamps that buzz and drop out (they never get a real light: it would have to flicker).
  {
    const cfg = look.lamps.flicker;
    const candidates = lamps.filter((l) => !l.virtual && cfg.kinds.includes(l.kind) && l.priority < cfg.belowPriority);
    for (let i = 0; i < cfg.count && candidates.length; i++) {
      candidates.splice(rng.int(0, candidates.length - 1), 1)[0].tired = true;
    }
  }

  // Real lights for the lamps that matter most from wherever the camera is (see createLightRig).
  const rig = createLightRig(G, lamps, G.quality.lights, root);

  /** Height a pool of light lies on: the physics world inside the bounds, our own street outside. */
  function groundAt(x, z) {
    const inside = x > bounds.minX && x < bounds.maxX && z > bounds.minZ && z < bounds.maxZ;
    if (inside) return G.physics.groundHeight(x, z, 0.6);
    const off = Math.abs(z - avenueZ);
    return off > ROAD_HALF && off < WALK_OUTER ? 0.15 : 0;
  }

  const detailName = () => (look.detail[G.quality.name] ? G.quality.name : 'medium');
  const bootDetail = look.detail[detailName()];
  const field = createLampField(G, lamps, shared, root, { poolCells: bootDetail.cones ? 5 : 3, groundAt, bounds });

  // ---------------------------------------------------------------------------------------------
  // The city, the train, the small things
  // ---------------------------------------------------------------------------------------------

  const city = createFarCity(G, { bounds, el, elRow, deck: el ? deckExtent(level.root, el) : null, avenueZ, haze, shared, glowBatch: field.glowBatch, parent: root });
  field.finish(); // the glow mesh, now that the city has added its lights

  const train = el ? createTrain(G, { bounds, el, haze, shared, glowMaterial: field.glowMaterial, parent: root }) : null;
  const life = createLife(G, { bounds, el, avenueZ, lamps, haze, shared, parent: root });

  // ---------------------------------------------------------------------------------------------
  // Image-based light
  // ---------------------------------------------------------------------------------------------

  let envTarget = null;
  {
    const cfg = look.env;
    const probe = new THREE.Vector3((bounds.minX + bounds.maxX) / 2, 1.4, avenueZ);
    const blobs = [];
    for (const lamp of lamps) {
      const to = lamp.pos.clone().sub(probe);
      const dist = Math.max(to.length(), 3);
      if (to.y < -0.5) continue;
      const weight = (lamp.intensity * (lamp.style.env ?? 1)) / (dist * dist);
      blobs.push({
        weight,
        dir: to.normalize(),
        // Near lamps are bigger in the sky; far ones keep a minimum so they survive the blur. (The discs
        // fade out toward their rim: about half of this radius is visibly bright.)
        size: clamp((lamp.kind === 'neon' ? 2.4 : 1.3) / dist, 0.04, 0.2),
        color: lamp.color.clone().multiplyScalar(cfg.lampGain * (lamp.style.env ?? 1) * clamp(lamp.intensity / 60, 0.35, 1.8)),
      });
    }
    blobs.sort((a, b) => b.weight - a.weight);
    envTarget = createEnvironment(G, sky, blobs.slice(0, cfg.maxLamps));
    G.render.setEnvironment(envTarget.texture);
  }

  // ---------------------------------------------------------------------------------------------
  // Quality
  // ---------------------------------------------------------------------------------------------

  let shownDetail = null;
  function applyDetail() {
    const name = detailName();
    if (name === shownDetail) return;
    shownDetail = name;
    const detail = look.detail[name];
    if (field.cones) field.cones.visible = detail.cones;
    city.setDetail(detail);
    life.setDetail(detail);
    if (train) train.setDetail(detail);
  }
  applyDetail();

  // ---------------------------------------------------------------------------------------------
  // Interior
  // ---------------------------------------------------------------------------------------------

  const interiorCfg = look.interior;
  const ambientOut = { sky: key.hemi.color.clone(), ground: key.hemi.groundColor.clone(), intensity: key.hemi.intensity };
  const ambientIn = new THREE.Color(interiorCfg.ambientSky);
  let interior = 0; // 0 on the street … 1 inside the shop (smoothed)
  let explicit = null; // last value handed to setInterior()
  let explicitAge = Infinity;
  let appliedExposure = 1; // the factor currently folded into render.look.exposure

  function applyInterior(f) {
    // Exposure is shared with whoever else tunes render.look: only our own factor is swapped out.
    const exposure = lerp(1, interiorCfg.exposure, f);
    G.render.look.exposure *= exposure / appliedExposure;
    appliedExposure = exposure;
    key.hemi.intensity = ambientOut.intensity * lerp(1, interiorCfg.ambient, f);
    key.hemi.color.copy(ambientOut.sky).lerp(ambientIn, f);
    haze.setDensityScale(lerp(1, interiorCfg.fog, f));
  }

  function setInterior(amount) {
    explicit = clamp01(Number(amount) || 0);
    explicitAge = 0;
  }

  // ---------------------------------------------------------------------------------------------
  // Hooks into modules created after this one
  // ---------------------------------------------------------------------------------------------

  G.events.on('boot:done', () => {
    life.hookEmitters();
    // Upload what the first frames do not show, so the first train does not hitch.
    const textures = [...(train ? train.textures : []), ...city.textures, life.paper.texture];
    for (const texture of textures) {
      try {
        G.renderer.initTexture(texture);
      } catch {
        // uploaded on first use instead
      }
    }
  });
  // A new run clears the fx module: ask for the steam again.
  G.events.on('game:reset', () => life.hookEmitters());

  // ---------------------------------------------------------------------------------------------
  // Update
  // ---------------------------------------------------------------------------------------------

  let clock = 0; // seconds of un-paused time since boot

  function update(dt) {
    clock += dt;
    shared.uTime.value = clock % TIME_WRAP;

    explicitAge += dt;
    const polled = typeof level.interiorAt === 'function' ? level.interiorAt(G.camera.position) : 0;
    const target = interiorTarget(explicit, explicitAge, polled, interiorCfg.holdExplicit);
    if (Math.abs(target - interior) > 1e-4) {
      interior = damp(interior, target, interiorCfg.rate, dt);
      if (Math.abs(target - interior) < 0.002) interior = target;
      applyInterior(interior);
    }

    rig.update(dt, G.camera);
    if (train) train.update(dt, clock);
    life.update(dt, train ? train.state : null);

    key.refit(); // the renderer may have resized the shadow map
    if (G.quality.name !== shownDetail) applyDetail();
  }

  return {
    sun: key.sun,
    setInterior,
    update,
    /** Live state of the El train: {active, phase, dir, x, lo, hi, y, z, speed, length, passes}. */
    train: train ? train.state : { active: false, phase: null, dir: 1, x: 0, lo: 0, hi: 0, y: 0, z: 0, speed: 0, length: 0, passes: 0 },
    /** Sends a train now (debug, tests): dir +1 east / −1 west, `lead` seconds before it reaches the block. */
    passTrain(dir = 1, lead = null) {
      if (train) train.pass(dir, lead);
    },
    /** Completes every pending hand-over of the lamp lights at once (screenshots, tests). */
    settleLights() {
      rig.settle(G.camera);
    },
    /** 0 on the street … 1 inside the shop, as currently applied. */
    get interior() {
      return interior;
    },
    /** Numbers for the harness and the curious. */
    stats() {
      return {
        clock,
        lamps: lamps.length,
        levelLamps: lamps.filter((l) => !l.virtual).length,
        realLights: rig.count,
        realKinds: rig.kinds(),
        glows: field.glowBatch.count,
        buildings: city.stats.buildings,
        cityTriangles: city.stats.triangles,
        detail: shownDetail,
        hydrant: !!life.hydrant,
        nextTrain: train ? train.schedule.nextAt : null,
        shadow: key.fitted ? { width: key.fitted.width, height: key.fitted.height, near: key.fitted.near, far: key.fitted.far, texel: key.fitted.texel } : null,
      };
    },
  };
}
