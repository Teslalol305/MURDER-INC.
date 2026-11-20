// Ammo on the ground: the crates a level is dressed with and the pouches Vultures drop
// (src/config/flow.js `pickups`; what one is worth to each gun is `pickup` in src/config/weapons.js).
//
// Walking over one takes it: every gun gets its share through weapon.resupply(). A full rack takes
// nothing and the crate stays for later. Crates breathe and turn under a green marker so they read as
// something to take; a pouch lies where its Vulture fell and is gone after a while.
// `list` is what the minimap draws. Three draw calls for all of them (instanced).

import * as THREE from 'three';
import { boxGeo, cylGeo, mergeGeos } from '../core/geo.js';

const CRATES = 10;
const GREEN = 0x3fe07a;

/** Does a kill leave a pouch? `roll` is uniform 0…1; `reserve` the gun in hand's reserve as a share of a full one. */
export function shouldDrop(type, roll, reserve, P) {
  if (reserve <= P.dropAlways) return true;
  const chance = P.dropChance[type];
  return typeof chance === 'number' && roll < chance;
}

/** The message for what a pickup added (`added` is what weapon.resupply returned; the weapon bar shows the counts). */
export function pickupLine(kind, added, T) {
  if (!added || added.length === 0) return T.full;
  return kind === 'crate' ? T.crate : T.pouch;
}

export function createPickups(G) {
  const P = G.config.flow.pickups;
  const T = G.config.text.story.pickup;
  const W = G.config.weapons;
  // What a dropped pouch feeds: every gun that takes bullets, not the launcher.
  const bulletGuns = W.common.order.filter((id) => W[id] && W[id].pickup && !W[id].projectile);
  const total = CRATES + P.maxDrops;

  /** Every slot, in use or not: {kind, pos, live, age, life, phase}. */
  const list = [];
  for (let i = 0; i < total; i++) {
    list.push({ kind: i < CRATES ? 'crate' : 'pouch', pos: new THREE.Vector3(), live: false, age: 0, life: Infinity, phase: i * 1.7 });
  }
  let crates = 0; // crate slots the current level uses
  let fullAt = -Infinity;
  let clock = 0;
  let warmed = false;

  // Models: an ammo box (olive, dark bands, a lit stripe), a lit ring on the ground, a lit marker above.
  let boxes = null;
  let rings = null;
  let marks = null;
  if (G.scene && G.mats) {
    try {
      const body = mergeGeos([
        boxGeo(0.5, 0.26, 0.3, { bottom: true }),
        boxGeo(0.52, 0.045, 0.32, { at: [0, 0.2, 0] }),
        boxGeo(0.06, 0.05, 0.2, { at: [0, 0.285, 0] }), // the handle
      ]);
      const ring = new THREE.RingGeometry(0.52, 0.6, 28).rotateX(-Math.PI / 2);
      const mark = mergeGeos([
        cylGeo(0.11, 0.2, 4, { radiusTop: 0.001, at: [0, 0.1, 0] }),
        cylGeo(0.001, 0.2, 4, { radiusTop: 0.11, at: [0, -0.1, 0] }),
      ]);
      const make = (geometry, material, name) => {
        const mesh = new THREE.InstancedMesh(geometry, material, total);
        mesh.name = name;
        mesh.frustumCulled = false;
        mesh.castShadow = false;
        mesh.count = 1; // one of each under the street until the first update: the shader warm-up sees them
        mesh.setMatrixAt(0, new THREE.Matrix4().makeTranslation(0, -200, 0));
        G.scene.add(mesh);
        return mesh;
      };
      boxes = make(body, G.mats.get('paint_green'), 'pickup-boxes');
      rings = make(ring, G.mats.emissive(GREEN, 1.6), 'pickup-rings');
      marks = make(mark, G.mats.emissive(GREEN, 2.4), 'pickup-marks');
    } catch (err) {
      console.warn('[game] ammo pickups have no model:', err);
      boxes = rings = marks = null;
    }
  }

  const matrix = new THREE.Matrix4();
  const position = new THREE.Vector3();
  const quaternion = new THREE.Quaternion();
  const scale = new THREE.Vector3();
  const UP = new THREE.Vector3(0, 1, 0);

  /** A point on the floor nearest to (x, z) that can be walked to, or null. */
  function onFloor(x, z, fromY = 3) {
    const nav = G.physics && G.physics.nav;
    let px = x;
    let pz = z;
    if (nav && typeof nav.nearestWalkable === 'function') {
      const near = nav.nearestWalkable(x, z, 3);
      if (!near) return null;
      px = near.x;
      pz = near.z;
    }
    return position.set(px, G.physics ? G.physics.groundHeight(px, pz, fromY) : 0, pz);
  }

  /** Dresses the level: crates at these [x, z] points. Whatever lay around before is gone. */
  function place(points) {
    clear();
    crates = 0;
    for (const point of points || []) {
      if (crates >= CRATES) break;
      const at = onFloor(point[0], point[1]);
      if (!at) continue;
      const slot = list[crates++];
      slot.pos.copy(at);
      slot.live = true;
      slot.age = 0;
      slot.life = Infinity;
    }
  }

  /** Every crate of the level stands there again (Hold the Block, between waves). */
  function refill() {
    for (let i = 0; i < crates; i++) {
      list[i].live = true;
      list[i].age = 0;
    }
  }

  /** A pouch where a Vulture fell. The oldest one goes when there is no slot left. */
  function drop(pos) {
    const at = onFloor(pos.x, pos.z, pos.y + 1.2);
    if (!at) return null;
    let slot = null;
    for (let i = CRATES; i < total; i++) {
      const s = list[i];
      if (!s.live) {
        slot = s;
        break;
      }
      if (!slot || s.age > slot.age) slot = s;
    }
    slot.pos.copy(at);
    slot.live = true;
    slot.age = 0;
    slot.life = P.dropLife;
    return slot;
  }

  function clear() {
    for (const slot of list) slot.live = false;
  }

  function take(slot) {
    const weapon = G.weapon;
    if (!weapon || typeof weapon.resupply !== 'function') return;
    const added = slot.kind === 'crate' ? weapon.resupply(P.crate) : weapon.resupply(P.drop, bulletGuns);
    if (added.length === 0) {
      // Nothing to add: it stays, and Rule is told why, now and then.
      if (clock - fullAt > P.fullEvery) {
        fullAt = clock;
        if (G.hud) G.hud.message(T.full, P.messageSecs);
      }
      return;
    }
    slot.live = false;
    if (G.hud) G.hud.message(pickupLine(slot.kind, added, T), P.messageSecs);
    if (G.audio) G.audio.play('pickup');
    if (G.events) G.events.emit('game:pickup', { kind: slot.kind, pos: slot.pos.clone(), added });
  }

  function draw() {
    if (!boxes) return;
    let n = 0;
    for (let i = 0; i < total; i++) {
      const slot = list[i];
      if (!slot.live) continue;
      const crate = slot.kind === 'crate';
      const t = clock * P.bob.rate + slot.phase;
      // A pouch about to go blinks.
      if (!crate && slot.life - slot.age < 5 && Math.sin(slot.age * 14) < 0) continue;
      const size = crate ? 1 : 0.62;
      quaternion.setFromAxisAngle(UP, crate ? clock * P.bob.spin + slot.phase : slot.phase);
      position.copy(slot.pos);
      position.y += crate ? 0.16 + Math.sin(t) * P.bob.lift : 0.02;
      matrix.compose(position, quaternion, scale.setScalar(size));
      boxes.setMatrixAt(n, matrix);
      position.copy(slot.pos);
      position.y += 0.03;
      matrix.compose(position, quaternion, scale.setScalar(crate ? 1 + 0.08 * Math.sin(t * 1.3) : 0.6));
      rings.setMatrixAt(n, matrix);
      position.copy(slot.pos);
      position.y += (crate ? 0.95 : 0.55) + Math.sin(t + 1) * P.bob.lift;
      matrix.compose(position, quaternion, scale.setScalar(crate ? 1 : 0.6));
      marks.setMatrixAt(n, matrix);
      n++;
    }
    for (const mesh of [boxes, rings, marks]) {
      mesh.count = n;
      mesh.instanceMatrix.needsUpdate = true;
    }
  }

  /** `active`: Rule can take things (a live run). Drawn either way, so a cutscene shows the crates. */
  function update(dt, active = true) {
    if (!warmed) warmed = true;
    clock += dt;
    const player = G.player;
    for (let i = 0; i < total; i++) {
      const slot = list[i];
      if (!slot.live) continue;
      slot.age += dt;
      if (slot.age >= slot.life) {
        slot.live = false;
        continue;
      }
      if (!active || !player || !player.pos || player.alive === false) continue;
      const dx = slot.pos.x - player.pos.x;
      const dz = slot.pos.z - player.pos.z;
      if (dx * dx + dz * dz > P.radius * P.radius || Math.abs(slot.pos.y - player.pos.y) > P.vertical) continue;
      take(slot);
    }
    draw();
  }

  return {
    list,
    place,
    refill,
    drop,
    clear,
    update,
    get crates() {
      let n = 0;
      for (let i = 0; i < crates; i++) if (list[i].live) n++;
      return n;
    },
  };
}
