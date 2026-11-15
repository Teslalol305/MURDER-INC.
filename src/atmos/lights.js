// Real lights: the shadow-casting key, the hemisphere ambient, and a small rig of spot lights shared out
// among the lamps of the level. Everything is created once here and never added to or removed from the
// scene afterwards (that would recompile every material).
//
// Also home of `collectLamps`: the level's lamp list turned into the records the rest of the atmosphere
// draws from (pools, cones, glows, the environment, moths).

import * as THREE from 'three';
import { fitShadowFrustum, lampClaim, pickRealLights } from './plan.js';

const DOWN = new THREE.Vector3(0, -1, 0);
const CARDINALS = [new THREE.Vector3(1, 0, 0), new THREE.Vector3(-1, 0, 0), new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, 0, -1)];
const FLOOR_SPAN = 2.5; // a box at least this wide both ways under a lamp is a floor, not furniture

/**
 * Normalises `level.lamps` into records:
 *   {pos, color (linear, unit brightness), intensity, range, kind, style, priority, dir | null, wall | null,
 *    floor, real: false, virtual: false, index}
 * `wall` is the outward normal of the wall a neon sign or lit window hangs on (their pools lie in
 * front of it); `floor` is the height of the deck a lamp hangs over (0 = the street). Entries without a
 * usable position are dropped.
 */
export function collectLamps(G, avenueZ) {
  const cfg = G.config.look.lamps;
  const list = (G.level && Array.isArray(G.level.lamps) ? G.level.lamps : []).filter((l) => l && l.pos && Number.isFinite(l.pos.x));
  const objectives = (G.level && G.level.objectives) || [];
  const out = [];
  const hit = { point: new THREE.Vector3(), normal: new THREE.Vector3() };
  const probe = new THREE.Vector3();

  for (let i = 0; i < list.length; i++) {
    const src = list[i];
    const kind = cfg.kinds[src.kind] ? src.kind : cfg.fallbackKind;
    const pos = new THREE.Vector3(src.pos.x, src.pos.y, src.pos.z);
    const lamp = {
      index: i,
      pos,
      color: new THREE.Color(src.color ?? 0xffb45e),
      intensity: Number.isFinite(src.intensity) ? Math.max(0, src.intensity) : 30,
      range: Number.isFinite(src.range) && src.range > 0 ? src.range : 12,
      kind,
      style: cfg.kinds[kind],
      priority: Number(src.priority) || 0,
      dir: null,
      wall: null,
      floor: 0,
      real: false,
      virtual: false,
    };

    const d = src.dir;
    if (d && Number.isFinite(d.x) && Number.isFinite(d.y) && Number.isFinite(d.z) && d.x * d.x + d.y * d.y + d.z * d.z > 1e-6) {
      lamp.dir = new THREE.Vector3(d.x, d.y, d.z).normalize();
    } else if (kind === 'flood') {
      // A flood without an aim lights the nearest objective (the court), or the ground ahead of its mast.
      let best = null;
      let bestD = 38;
      for (const o of objectives) {
        const d = o.pos ? Math.hypot(o.pos.x - pos.x, o.pos.z - pos.z) : Infinity;
        if (d < bestD) {
          bestD = d;
          best = o.pos;
        }
      }
      lamp.dir = best
        ? new THREE.Vector3(best.x - pos.x, 0.4 - pos.y, best.z - pos.z).normalize()
        : new THREE.Vector3(0, -1, 0);
    }

    if (kind === 'neon' || kind === 'window') {
      // Which way does the wall behind the sign face? Nearest wall within reach, else "toward the avenue".
      let bestD = 2.2;
      for (const c of CARDINALS) {
        const h = G.physics.raycast(pos, c, bestD, hit);
        if (h && h.dist < bestD) {
          bestD = h.dist;
          lamp.wall = new THREE.Vector3(-c.x, 0, -c.z);
        }
      }
      if (!lamp.wall && Math.abs(pos.z - avenueZ) > 6) lamp.wall = new THREE.Vector3(0, 0, pos.z > avenueZ ? -1 : 1);
    }
    // What it hangs over: the street, or a floor of the level (a platform, a mezzanine, the shed deck).
    // Cars, shelters and other furniture under a lamp do not count: its light goes down around them.
    probe.set(pos.x, pos.y - 0.25, pos.z);
    const below = G.physics.raycast(probe, DOWN, pos.y + 1, hit);
    if (below && below.box && below.point.y > 0.6) {
      const b = below.box;
      if (b.max.x - b.min.x >= FLOOR_SPAN && b.max.z - b.min.z >= FLOOR_SPAN) lamp.floor = below.point.y;
    }
    out.push(lamp);
  }
  return out;
}

/**
 * The real lamp lights: `budget` spot lights, created once, that serve whichever lamps matter most from
 * where the camera is. A lamp's claim is its priority (the level's call) weighed against its distance
 * from the point the camera looks at, so the shop's work lights are real while you are in the shop and
 * the lamps under the El are real while you fight on the avenue. A light changes lamp by fading out,
 * moving, and fading back in; nothing is ever added to or removed from the scene.
 *
 * Every lamp is a spot: shaded fixtures throw their light down (and do not burn a hot spot into the
 * ceiling they hang from), signs and windows throw it out from their wall, floods along their aim.
 */
export function createLightRig(G, lamps, budget, parent) {
  const cfg = G.config.look.lamps;
  const rig = cfg.rig;
  const candidates = lamps.filter((l) => !l.virtual && !l.tired && l.intensity > 0);
  const count = Math.max(0, Math.min(Math.floor(budget) || 0, candidates.length));
  const slots = [];
  const aimDir = new THREE.Vector3();
  const focus = new THREE.Vector3();
  const forward = new THREE.Vector3();

  for (let i = 0; i < count; i++) {
    const light = new THREE.SpotLight(0xffffff, 0, 10, 1, 0.5, 2);
    light.name = `lamp-light-${i}`;
    light.castShadow = false;
    parent.add(light, light.target);
    slots.push({ light, lamp: null, next: null, level: 0, base: 0 });
  }

  /** Points a slot's light at the world the way `lamp` shines. */
  function assign(slot, lamp) {
    const style = lamp.style;
    const spot = style.spot || rig.spot;
    if (lamp.dir) aimDir.copy(lamp.dir);
    else if (lamp.wall) aimDir.copy(lamp.wall).setY(-0.7).normalize(); // out from the wall and down onto the sidewalk
    else aimDir.copy(DOWN);
    const { light } = slot;
    light.position.copy(lamp.pos);
    light.target.position.copy(lamp.pos).add(aimDir);
    light.color.copy(lamp.color);
    light.distance = lamp.range * rig.rangeScale;
    light.angle = THREE.MathUtils.degToRad(spot.angle);
    light.penumbra = spot.penumbra;
    slot.base = lamp.intensity * cfg.realGain * (style.realGain ?? 1);
    slot.lamp = lamp;
    lamp.real = true;
  }

  const byClaim = (a, b) => b.claimNow - a.claimNow || a.index - b.index;

  /** Decides which lamps should hold a light and starts the hand-overs. */
  function evaluate(camera) {
    camera.getWorldDirection(forward);
    focus.copy(camera.position).addScaledVector(forward, rig.lookAhead);
    for (let i = 0; i < candidates.length; i++) {
      const lamp = candidates[i];
      lamp.claimNow = lampClaim(lamp.priority, lamp.pos.distanceTo(focus), rig.reach) * (lamp.real ? rig.keep : 1); // holders are harder to dislodge
      lamp.wanted = false;
    }
    candidates.sort(byClaim);
    for (let i = 0; i < count; i++) candidates[i].wanted = true;
    for (let i = 0; i < slots.length; i++) if (slots[i].next) slots[i].next.wanted = false; // already on its way
    let search = 0;
    for (let i = 0; i < slots.length; i++) {
      const slot = slots[i];
      if (slot.next || (slot.lamp && slot.lamp.wanted)) continue;
      // This light is free (or its lamp lost its claim): give it the best lamp still waiting for one.
      while (search < count && (candidates[search].real || !candidates[search].wanted)) search++;
      if (search >= count) break;
      slot.next = candidates[search];
      slot.next.wanted = false;
    }
  }

  let timer = 0;

  function update(dt, camera) {
    if (!count) return;
    timer -= dt;
    if (timer <= 0) {
      timer = rig.interval;
      evaluate(camera);
    }
    for (let i = 0; i < slots.length; i++) {
      const slot = slots[i];
      if (slot.next) {
        slot.level -= dt / rig.fadeOut;
        if (slot.level <= 0) {
          slot.level = 0;
          if (slot.lamp) slot.lamp.real = false;
          assign(slot, slot.next);
          slot.next = null;
        }
      } else if (slot.level < 1) {
        slot.level = Math.min(1, slot.level + dt / rig.fadeIn);
      }
      slot.light.intensity = slot.base * slot.level;
    }
  }

  // Before the first frame: the highest priorities, fully on.
  const first = pickRealLights(candidates, count);
  for (let i = 0; i < count; i++) {
    assign(slots[i], candidates[first[i]]);
    slots[i].level = 1;
    slots[i].light.intensity = slots[i].base;
    slots[i].light.updateMatrixWorld();
    slots[i].light.target.updateMatrixWorld();
  }

  return {
    count,
    update,
    /** Kinds of the lamps that hold a light right now. */
    kinds: () => slots.map((slot) => (slot.lamp ? slot.lamp.kind : null)),
    /** Forces an evaluation and completes every hand-over at once (screenshots, tests). */
    settle(camera) {
      for (let pass = 0; pass < 3; pass++) {
        evaluate(camera);
        for (const slot of slots) {
          if (!slot.next) continue;
          if (slot.lamp) slot.lamp.real = false;
          assign(slot, slot.next);
          slot.next = null;
        }
      }
      for (const slot of slots) {
        slot.level = 1;
        slot.light.intensity = slot.base;
      }
      timer = rig.interval;
    },
  };
}

/**
 * The key (CONTRACT 6.11 `atmos.sun`) and the ambient.
 * `fit(minY, maxY)` wraps the shadow frustum around the bounds; call it again when the map size changes.
 */
export function createKeyLight(G, bounds, parent) {
  const look = G.config.look;
  const sun = new THREE.DirectionalLight(look.sun.color, look.sun.intensity);
  sun.name = 'key';
  sun.castShadow = true;
  sun.shadow.normalBias = look.sun.shadowNormalBias;
  sun.shadow.radius = look.sun.shadowRadius;
  if (G.quality.shadow > 0) sun.shadow.mapSize.set(G.quality.shadow, G.quality.shadow);
  parent.add(sun, sun.target);

  const hemi = new THREE.HemisphereLight(look.ambient.sky, look.ambient.ground, look.ambient.intensity);
  hemi.name = 'ambient';
  parent.add(hemi);

  let fitted = null;
  let fittedSize = 0;
  let span = [0, look.sun.shadowHeight];

  function fit(minY = span[0], maxY = span[1]) {
    span = [minY, maxY];
    fittedSize = sun.shadow.mapSize.x;
    fitted = fitShadowFrustum({
      bounds,
      minY,
      maxY,
      dir: look.sun.direction,
      mapSize: fittedSize,
      margin: look.sun.shadowMargin,
    });
    sun.position.fromArray(fitted.position);
    sun.target.position.fromArray(fitted.target);
    sun.updateMatrixWorld();
    sun.target.updateMatrixWorld();
    const cam = sun.shadow.camera;
    cam.left = fitted.left;
    cam.right = fitted.right;
    cam.top = fitted.top;
    cam.bottom = fitted.bottom;
    cam.near = fitted.near;
    cam.far = fitted.far;
    cam.updateProjectionMatrix();
    // The bias is a fraction of the depth range: keep it a fixed few centimetres in the world.
    sun.shadow.bias = -look.sun.shadowBiasMetres / (fitted.far - fitted.near);
    sun.shadow.needsUpdate = true;
    return fitted;
  }

  return {
    sun,
    hemi,
    fit,
    /** Re-fits when the renderer has resized the shadow map (quality change). */
    refit() {
      if (sun.shadow.mapSize.x !== fittedSize) fit();
    },
    get fitted() {
      return fitted;
    },
  };
}
