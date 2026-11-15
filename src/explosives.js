// G.explosives (CONTRACT 6.7): propane tanks and welding racks, solid cover until they blow.
//
// Rules (reference numbers, DESIGN names):
//   propane tank   50 HP, fuse 1.6 s, blast radius 6.5 m, 170 damage (the player takes half)
//   welding rack   70 HP, fuse 1.1 s, blast radius 7.5 m, 210 damage
//   - the first hit lights the fuse: a jet of flame roars out of the hole and the gas hisses louder
//     until the fuse runs out; a hit that takes the hit points to zero pops it 0.06 s later
//   - a player round does the weapon's damage, an enemy round 9, whatever it would do to a person
//   - every explosion (a Buzzard coming down included) sets off the explosives within
//     2.2 + 1.6 × size metres after 0.14 + 0…0.3 + 0.03 × distance seconds: tanks go up in a ripple
//   - the collider goes with the blast and comes back with reset()
//
// The blast itself is G.combat.explode (damage, falloff, line of sight, the `explosion` event that fx
// and audio answer). This module adds the shake and the wide alert of a prop going up.

import * as THREE from 'three';
import { mergeGeos } from './core/geo.js';

export const KINDS = {
  propane: { prop: 'propane_tank', hp: 50, fuse: 1.6, radius: 6.5, damage: 170, size: 1.9, box: [0.32, 0.6, 0.32], jet: 0.9 },
  rack: { prop: 'welding_rack', hp: 70, fuse: 1.1, radius: 7.5, damage: 210, size: 2.3, box: [0.9, 1.6, 0.5], jet: 1.2 },
};

const POP_FUSE = 0.06; // once the hit points are gone
const PLAYER_SCALE = 0.5;
const ENEMY_ROUND = 9; // config/weapons.js common.explosiveHitFromEnemy when present
const SHAKE_REACH = 28; // metres: camera shake 0.15 + 0.9 g², g = 1 − distance / reach
const ALERT_RADIUS = 60; // a prop going up is heard further than an ordinary blast
const RATTLE = 0.035; // radians: how hard a lit tank shakes just before it goes
const HISS = { name: 'hiss', from: 0.25 }; // audio loop asked for while lit; its volume rises from here to 1

/** How far a blast of the given size sets off other explosives. */
export const chainRange = (size) => 2.2 + 1.6 * size;

/** Fuse of an explosive caught by a blast `dist` metres away; `roll` is uniform in [0, 1). */
export const chainFuse = (dist, roll) => 0.14 + roll * 0.3 + 0.03 * dist;

/** "Size" of a blast that did not come from one of our props, from its radius (a Buzzard's 3 m → 1.2). */
export const sizeFromRadius = (radius) => Math.min(2.6, Math.max(0.6, 0.47 + 0.244 * radius));

export function createExplosives(G) {
  const rng = G.rng && typeof G.rng.fork === 'function' ? G.rng.fork('explosives') : null;
  const random = rng ? () => rng.next() : Math.random;
  const emit = (name, payload) => G.events && G.events.emit(name, payload);

  const root = new THREE.Group();
  root.name = 'explosives';
  if (G.scene) G.scene.add(root);

  const items = [];
  let builtFrom = null; // the level list the current items were made from
  let fallbackMaterial = null;
  let clock = 0;

  // The last ray that found an explosive: tells damage() where the round went in.
  const struck = { item: null, frame: -1, point: new THREE.Vector3(), normal: new THREE.Vector3() };
  const jetPos = new THREE.Vector3();
  const jetDir = new THREE.Vector3();
  const centre = new THREE.Vector3();

  // ---------------------------------------------------------------------------------------------
  // Building: every item of a type is an instance of one batch (CONTRACT 11.2)
  // ---------------------------------------------------------------------------------------------

  /** A plain red shape of the right size, for when the prop factory has nothing to offer. */
  function fallbackObject(kind) {
    fallbackMaterial = fallbackMaterial || new THREE.MeshStandardMaterial({ color: 0xb3261e, roughness: 0.5, metalness: 0.3 });
    const [length, height, width] = kind.box;
    const geometry =
      kind === KINDS.propane ? new THREE.CylinderGeometry(length / 2, length / 2, height, 12) : new THREE.BoxGeometry(length, height, width);
    geometry.translate(0, height / 2, 0); // origin on the ground, like every prop
    const mesh = new THREE.Mesh(geometry, fallbackMaterial);
    mesh.castShadow = true;
    return mesh;
  }

  /** One prop of the type, built once: the model every item of that type is drawn from. */
  function buildTemplate(type) {
    const kind = KINDS[type];
    let prop = null;
    try {
      prop = G.props && typeof G.props.build === 'function' ? G.props.build(kind.prop, { seed: 1 }) : null;
    } catch (err) {
      console.error('[explosives] props.build failed:', err);
    }
    if (!prop || !prop.object) prop = { object: fallbackObject(kind), size: kind.box };
    return prop;
  }

  /**
   * The visible meshes of the template in one state, merged per material (and shadow flags) in the
   * prop's own space. Null when the model cannot be batched (a multi-material mesh).
   */
  function partsOf(prop, state) {
    if (typeof prop.setState === 'function') prop.setState(state);
    else prop.object.visible = state !== 'gone';
    const object = prop.object;
    object.position.set(0, 0, 0);
    object.rotation.set(0, 0, 0);
    object.updateMatrixWorld(true);
    const buckets = new Map();
    let ok = true;
    (function walk(obj) {
      if (!obj.visible) return;
      if (obj.isMesh && obj.geometry && obj.material) {
        if (Array.isArray(obj.material) || obj.isInstancedMesh || obj.isSkinnedMesh) ok = false;
        else {
          const key = `${obj.material.uuid}|${obj.castShadow ? 1 : 0}${obj.receiveShadow ? 1 : 0}|${obj.renderOrder}`;
          let bucket = buckets.get(key);
          if (!bucket) buckets.set(key, (bucket = { source: obj, list: [] }));
          bucket.list.push({ geo: obj.geometry, matrix: obj.matrixWorld.clone() });
        }
      }
      for (const child of obj.children) walk(child);
    })(object);
    if (!ok) return null;
    return [...buckets.values()].map(({ source, list }) => ({ source, geometry: mergeGeos(list) }));
  }

  // type -> {states: {idle, lit, gone}: InstancedMesh[], count}
  const batches = {};
  const ZERO = new THREE.Matrix4().makeScale(0, 0, 0);
  const hidden = new THREE.Matrix4();
  const STATES = ['idle', 'lit', 'gone'];

  function dropBatches() {
    for (const type of Object.keys(batches)) {
      for (const state of STATES) {
        for (const mesh of batches[type].states[state]) {
          root.remove(mesh);
          mesh.geometry.dispose();
          mesh.dispose();
        }
      }
      delete batches[type];
    }
  }

  /** Instanced meshes for `count` items of a type, or null (then each item gets its own model). */
  function makeBatch(type, count) {
    const prop = buildTemplate(type);
    const states = {};
    for (const state of STATES) {
      const parts = partsOf(prop, state);
      if (!parts) return null;
      states[state] = parts.map(({ source, geometry }) => {
        const mesh = new THREE.InstancedMesh(geometry, source.material, count);
        mesh.name = `explosives:${type}:${state}`;
        mesh.castShadow = source.castShadow;
        mesh.receiveShadow = source.receiveShadow;
        mesh.renderOrder = source.renderOrder;
        mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        for (let i = 0; i < count; i++) mesh.setMatrixAt(i, ZERO);
        mesh.visible = false;
        root.add(mesh);
        return mesh;
      });
    }
    return { states, size: prop.size || KINDS[type].box };
  }

  function buildItem(entry, slot, batch) {
    const type = KINDS[entry.type] ? entry.type : 'propane';
    const kind = KINDS[type];
    // Without a batch the item carries a model of its own (only when the prop cannot be instanced).
    const own = batch ? null : buildTemplate(type);
    const object = own ? own.object : new THREE.Object3D();
    const yaw = entry.yaw || 0;
    object.position.copy(entry.pos);
    object.rotation.set(0, yaw, 0);
    if (own) {
      object.userData.noMerge = true;
      root.add(object);
    }

    const [length, height, width] = (batch && batch.size) || (own && own.size) || kind.box;
    const sin = Math.abs(Math.sin(yaw));
    const cos = Math.abs(Math.cos(yaw));
    return {
      // contract
      type,
      pos: new THREE.Vector3().copy(entry.pos),
      hp: kind.hp,
      state: 'idle',
      box: null,
      // internal
      kind,
      fuse: 0, // seconds left while lit
      fuseTotal: 0, // the fuse it was lit with (for the build-up)
      yaw,
      object, // its transform (the drawn model itself when it is not instanced)
      prop: own,
      batch,
      slot, // its instance index in the batch
      shown: null, // the state it is drawn in
      height,
      // Footprint of the rotated prop as an axis-aligned half extent.
      halfX: (cos * length + sin * width) / 2,
      halfZ: (sin * length + cos * width) / 2,
      jet: null, // emitter handle while lit
      hiss: null, // audio loop handle while lit
      chainedBy: -1, // id of the last blast that caught it
    };
  }

  /** Writes the item's transform into the instances of the state it is drawn in. */
  function place(item) {
    if (!item.batch) return;
    item.object.updateMatrix();
    // Hidden instances shrink to nothing where the item stands, so they do not stretch the bounds.
    hidden.copy(ZERO).setPosition(item.pos);
    for (const state of STATES) {
      const matrix = state === item.shown ? item.object.matrix : hidden;
      for (const mesh of item.batch.states[state]) {
        mesh.setMatrixAt(item.slot, matrix);
        mesh.instanceMatrix.needsUpdate = true;
      }
    }
  }

  /** Shows only the batch meshes some item is drawn with, and refits their bounds. */
  function refreshBatches() {
    for (const type of Object.keys(batches)) {
      for (const state of STATES) {
        const used = items.some((item) => item.batch === batches[type] && item.shown === state);
        for (const mesh of batches[type].states[state]) {
          mesh.visible = used;
          mesh.computeBoundingSphere();
        }
      }
    }
  }

  function show(item, state) {
    item.shown = state;
    if (item.batch) {
      place(item);
      refreshBatches();
    } else if (item.prop && typeof item.prop.setState === 'function') item.prop.setState(state);
    else item.object.visible = state !== 'gone';
  }

  function quench(item) {
    if (item.jet) item.jet.stop();
    item.jet = null;
    if (item.hiss) item.hiss.stop();
    item.hiss = null;
  }

  /**
   * Escaping gas: a loop at the item that grows louder until it blows. Audio that has no such sound
   * simply returns nothing; `explosive:lit` carries the fuse for whoever else wants to mark it.
   */
  function startHiss(item) {
    const audio = G.audio;
    if (!audio || typeof audio.loop !== 'function') return;
    try {
      const handle = audio.loop(HISS.name, { pos: item.pos, volume: HISS.from });
      item.hiss = handle && typeof handle.stop === 'function' && typeof handle.setVolume === 'function' ? handle : null;
    } catch {
      item.hiss = null;
    }
  }

  function arm(item) {
    quench(item);
    item.hp = item.kind.hp;
    item.state = 'idle';
    item.fuse = item.fuseTotal = 0;
    item.chainedBy = -1;
    item.object.rotation.set(0, item.yaw, 0);
    if (!item.box) {
      const p = item.pos;
      item.box = G.physics.addBox({
        min: [p.x - item.halfX, p.y, p.z - item.halfZ],
        max: [p.x + item.halfX, p.y + item.height, p.z + item.halfZ],
        surface: 'metal',
        tag: 'explosive',
        owner: item,
      });
    }
    show(item, 'idle');
  }

  function disarm(item) {
    if (item.box) G.physics.removeBox(item.box);
    item.box = null;
  }

  /** Restores every explosive. The set is only rebuilt when the level's list has changed. */
  function reset() {
    const list = (G.level && G.level.explosives) || [];
    if (list !== builtFrom || list.length !== items.length) {
      for (const item of items) {
        quench(item);
        disarm(item);
        if (item.prop) root.remove(item.object);
      }
      items.length = 0;
      dropBatches();
      const entries = list.filter((entry) => entry && entry.pos);
      const counts = {};
      for (const entry of entries) {
        const type = KINDS[entry.type] ? entry.type : 'propane';
        counts[type] = (counts[type] || 0) + 1;
      }
      for (const type of Object.keys(counts)) {
        try {
          const batch = makeBatch(type, counts[type]);
          if (batch) batches[type] = batch;
        } catch (err) {
          console.error('[explosives] could not instance', type, err);
        }
      }
      const slots = {};
      for (const entry of entries) {
        const type = KINDS[entry.type] ? entry.type : 'propane';
        slots[type] = (slots[type] || 0) + 1;
        items.push(buildItem(entry, slots[type] - 1, batches[type] || null));
      }
      builtFrom = list;
    }
    for (const item of items) arm(item);
    struck.item = null;
  }

  // ---------------------------------------------------------------------------------------------
  // Fuse
  // ---------------------------------------------------------------------------------------------

  /** Where the flame comes out: the bullet hole when we know it, else the valve on top. */
  function startJet(item, fuse) {
    if (!G.fx || typeof G.fx.addEmitter !== 'function') return;
    const frame = G.time ? G.time.frame : 0;
    if (struck.item === item && struck.frame === frame) {
      // Out of the hole, and up: burning gas rises.
      jetPos.copy(struck.point).addScaledVector(struck.normal, 0.02);
      jetDir.copy(struck.normal);
      jetDir.y += 0.55;
    } else {
      const a = random() * Math.PI * 2;
      jetPos.set(item.pos.x, item.pos.y + item.height * 0.94, item.pos.z);
      jetDir.set(Math.cos(a) * 0.55, 0.85, Math.sin(a) * 0.55);
    }
    quench(item);
    item.jet = G.fx.addEmitter(jetPos, 'jet', { ttl: fuse + 0.15, scale: item.kind.jet, dir: jetDir.normalize() });
  }

  function ignite(item, fuse) {
    item.state = 'lit';
    item.fuse = item.fuseTotal = fuse;
    show(item, 'lit');
    startJet(item, fuse);
    startHiss(item);
    emit('explosive:lit', { item, pos: item.pos.clone(), fuse });
  }

  /**
   * Damage from a round (`from` is 'player' or the enemy that fired) or from a blast (`from` 'blast').
   * Rounds wear the hit points down and light the fuse; a blast in range sets a short fuse outright.
   */
  function damage(item, amount, from) {
    if (!item || item.state === 'gone' || !(amount > 0)) return;
    if (from === 'blast') {
      chain(item);
      return;
    }
    if (from && typeof from === 'object') {
      const common = G.config && G.config.weapons && G.config.weapons.common;
      amount = common && common.explosiveHitFromEnemy > 0 ? common.explosiveHitFromEnemy : ENEMY_ROUND;
    }
    item.hp = Math.max(0, item.hp - amount);
    if (item.state === 'idle') ignite(item, item.kind.fuse);
    if (item.hp <= 0) item.fuse = Math.min(item.fuse, POP_FUSE);
  }

  // The blast being resolved right now (set by the `explosion` event, which combat emits first).
  const blast = { id: 0, live: false, pos: new THREE.Vector3(), range: 0, source: null };

  /** Applies the chain rule of the current blast to one explosive. Once per blast and item. */
  function chain(item) {
    if (!blast.live || item === blast.source || item.state === 'gone' || item.chainedBy === blast.id) return;
    centre.set(item.pos.x, item.pos.y + item.height / 2, item.pos.z);
    const dist = centre.distanceTo(blast.pos);
    if (dist > blast.range) return;
    item.chainedBy = blast.id;
    const fuse = chainFuse(dist, random());
    if (item.state === 'idle') ignite(item, fuse);
    else item.fuse = Math.min(item.fuse, fuse);
  }

  if (G.events) {
    G.events.on('explosion', (e) => {
      if (!e || !e.pos) return;
      blast.id++;
      blast.live = true;
      blast.pos.copy(e.pos);
      blast.source = e.source || null;
      const own = e.source && e.source.kind && items.includes(e.source) ? e.source.kind.size : sizeFromRadius(e.radius || 0);
      blast.range = chainRange(own);
      // Everything in range goes, seen or not: the shock carries around corners.
      for (let i = 0; i < items.length; i++) chain(items[i]);
    });
  }

  function blow(item) {
    quench(item);
    item.state = 'gone';
    item.hp = 0;
    item.fuse = 0;
    disarm(item); // before the blast, so the collider does not shield anything from it
    item.object.rotation.set(0, item.yaw, 0);
    show(item, 'gone');
    centre.set(item.pos.x, item.pos.y + item.height / 2, item.pos.z);
    const pos = centre.clone();
    emit('explosive:blast', { item, pos: pos.clone() });
    G.combat.explode({ pos, radius: item.kind.radius, damage: item.kind.damage, playerScale: PLAYER_SCALE, source: item });

    const player = G.player;
    if (player && player.pos && typeof player.addShake === 'function') {
      const g = 1 - player.pos.distanceTo(pos) / SHAKE_REACH;
      if (g > 0) player.addShake(0.15 + 0.9 * g * g);
    }
    if (G.enemies && typeof G.enemies.alert === 'function') G.enemies.alert(pos, ALERT_RADIUS);
  }

  function update(dt) {
    clock += dt;
    blast.live = false; // a blast only chains while it is being resolved
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.prop && typeof item.prop.update === 'function') item.prop.update(dt);
      if (item.state !== 'lit') continue;
      item.fuse -= dt;
      if (item.fuse <= 0) {
        blow(item);
        continue;
      }
      // The tank shudders harder and hisses louder as the pressure builds.
      const build = 1 - item.fuse / Math.max(item.fuseTotal, 1e-3);
      if (item.hiss) item.hiss.setVolume(HISS.from + (1 - HISS.from) * build * build);
      const shake = RATTLE * (0.3 + 0.7 * build);
      item.object.rotation.x = Math.sin(clock * 71 + i) * shake;
      item.object.rotation.z = Math.sin(clock * 83 + i * 2.3) * shake;
      place(item);
    }
  }

  // ---------------------------------------------------------------------------------------------
  // Rays
  // ---------------------------------------------------------------------------------------------

  /** Nearest live explosive along a unit ray (slab test against its collider), or null. */
  function raycast(origin, dir, maxDist = 500) {
    let best = null;
    let bestDist = maxDist;
    let bestAxis = 0;
    for (let i = 0; i < items.length; i++) {
      const box = items[i].box;
      if (!box) continue;
      let tIn = 0;
      let tOut = bestDist;
      let axis = -1;
      for (let a = 0; a < 3; a++) {
        const o = a === 0 ? origin.x : a === 1 ? origin.y : origin.z;
        const d = a === 0 ? dir.x : a === 1 ? dir.y : dir.z;
        const lo = a === 0 ? box.min.x : a === 1 ? box.min.y : box.min.z;
        const hi = a === 0 ? box.max.x : a === 1 ? box.max.y : box.max.z;
        if (d === 0) {
          if (o < lo || o > hi) tOut = -1;
          continue;
        }
        const t0 = (lo - o) / d;
        const t1 = (hi - o) / d;
        const near = t0 < t1 ? t0 : t1;
        const far = t0 < t1 ? t1 : t0;
        if (near >= tIn) {
          tIn = near;
          axis = a;
        }
        if (far < tOut) tOut = far;
      }
      if (axis < 0 || tIn > tOut || tIn >= bestDist) continue;
      best = items[i];
      bestDist = tIn;
      bestAxis = axis;
    }
    if (!best) return null;

    const normal = new THREE.Vector3();
    const d = bestAxis === 0 ? dir.x : bestAxis === 1 ? dir.y : dir.z;
    normal.setComponent(bestAxis, d > 0 ? -1 : 1);
    const point = new THREE.Vector3().copy(origin).addScaledVector(dir, bestDist);
    struck.item = best;
    struck.frame = G.time ? G.time.frame : 0;
    struck.point.copy(point);
    struck.normal.copy(normal);
    return { item: best, dist: bestDist, point, normal };
  }

  reset();

  return { items, reset, raycast, damage, update };
}
