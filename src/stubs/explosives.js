// Stub explosives (CONTRACT 6.7): propane tanks and welding racks from level.explosives.
//
// Each one is a prop from G.props.build (a plain red shape when the factory cannot supply it) plus one
// solid collider. The first hit lights the fuse; hit points at zero cut it to an instant; another blast
// sets it off after a short random delay. When the fuse runs out the collider goes and G.combat.explode
// does the damage. No flames or smoke here: the real module adds those.

import * as THREE from 'three';

const KINDS = {
  propane: { prop: 'propane_tank', hp: 50, fuse: 1.6, radius: 6.5, damage: 170, size: [0.32, 0.6, 0.32] },
  rack: { prop: 'welding_rack', hp: 70, fuse: 1.1, radius: 7.5, damage: 210, size: [0.9, 1.6, 0.5] },
};
const POP_FUSE = 0.06; // once the hit points are gone
const CHAIN_FUSE = [0.14, 0.44]; // when set off by another blast
const PLAYER_SCALE = 0.5;
const AXES = ['x', 'y', 'z'];

export function createExplosives(G) {
  const rng = G.rng && typeof G.rng.fork === 'function' ? G.rng.fork('explosives') : null;
  const random = rng ? () => rng.next() : Math.random;
  const emit = (name, payload) => G.events && G.events.emit(name, payload);

  const root = new THREE.Group();
  root.name = 'explosives-stub';
  if (G.scene) G.scene.add(root);
  const items = [];
  let builtFrom = null; // the level list the current items were made from
  let fallbackMaterial = null;

  function fallbackObject(kind) {
    fallbackMaterial =
      fallbackMaterial || new THREE.MeshStandardMaterial({ color: 0xb3261e, roughness: 0.5, metalness: 0.3 });
    const [length, height, width] = kind.size;
    const geometry =
      kind === KINDS.propane
        ? new THREE.CylinderGeometry(length / 2, length / 2, height, 12)
        : new THREE.BoxGeometry(length, height, width);
    geometry.translate(0, height / 2, 0); // origin on the ground, like every prop
    const mesh = new THREE.Mesh(geometry, fallbackMaterial);
    mesh.castShadow = true;
    return mesh;
  }

  function buildItem(entry) {
    const kind = KINDS[entry.type] || KINDS.propane;
    let prop = null;
    try {
      prop = G.props && typeof G.props.build === 'function' ? G.props.build(kind.prop) : null;
    } catch (err) {
      console.error('[explosives] props.build failed:', err);
    }
    const object = (prop && prop.object) || fallbackObject(kind);
    const yaw = entry.yaw || 0;
    object.position.copy(entry.pos);
    object.rotation.y = yaw;
    root.add(object);
    const [length, height, width] = (prop && prop.size) || kind.size;
    const sin = Math.abs(Math.sin(yaw));
    const cos = Math.abs(Math.cos(yaw));
    return {
      type: KINDS[entry.type] ? entry.type : 'propane',
      pos: new THREE.Vector3().copy(entry.pos),
      hp: kind.hp,
      state: 'idle',
      box: null,
      kind,
      fuse: 0,
      object,
      prop,
      height,
      // Footprint of the rotated prop as an axis-aligned half extent.
      halfX: (cos * length + sin * width) / 2,
      halfZ: (sin * length + cos * width) / 2,
    };
  }

  function show(item, state) {
    if (item.prop && typeof item.prop.setState === 'function') item.prop.setState(state);
    else item.object.visible = state !== 'gone';
  }

  function arm(item) {
    item.hp = item.kind.hp;
    item.state = 'idle';
    item.fuse = 0;
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
        disarm(item);
        root.remove(item.object);
      }
      items.length = 0;
      for (const entry of list) {
        if (entry && entry.pos) items.push(buildItem(entry));
      }
      builtFrom = list;
    }
    for (const item of items) arm(item);
  }

  function damage(item, amount, from) {
    if (!item || item.state === 'gone' || !(amount > 0)) return;
    item.hp -= amount;
    if (item.state === 'idle') {
      item.state = 'lit';
      item.fuse = item.kind.fuse;
      show(item, 'lit');
      emit('explosive:lit', { item, pos: item.pos.clone() });
    }
    if (from === 'blast') {
      item.fuse = Math.min(item.fuse, CHAIN_FUSE[0] + random() * (CHAIN_FUSE[1] - CHAIN_FUSE[0]));
    } else if (item.hp <= 0) {
      item.fuse = Math.min(item.fuse, POP_FUSE);
    }
  }

  function blow(item) {
    item.state = 'gone';
    item.hp = 0;
    disarm(item); // before the blast, so the collider does not shield anything from it
    show(item, 'gone');
    const centre = item.pos.clone();
    centre.y += item.height / 2;
    emit('explosive:blast', { item, pos: centre.clone() });
    G.combat.explode({
      pos: centre,
      radius: item.kind.radius,
      damage: item.kind.damage,
      playerScale: PLAYER_SCALE,
      source: item,
    });
  }

  function update(dt) {
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.prop && typeof item.prop.update === 'function') item.prop.update(dt);
      if (item.state !== 'lit') continue;
      item.fuse -= dt;
      if (item.fuse <= 0) blow(item);
    }
  }

  /** Nearest live explosive along a unit ray (slab test against its collider). */
  function raycast(origin, dir, maxDist = 500) {
    let best = null;
    let bestDist = maxDist;
    let bestAxis = 'x';
    for (let i = 0; i < items.length; i++) {
      const box = items[i].box;
      if (!box) continue;
      let tIn = 0;
      let tOut = bestDist;
      let entry = null;
      for (const axis of AXES) {
        const o = origin[axis];
        const d = dir[axis];
        if (d === 0) {
          if (o < box.min[axis] || o > box.max[axis]) tOut = -1;
          continue;
        }
        const a = (box.min[axis] - o) / d;
        const b = (box.max[axis] - o) / d;
        const near = Math.min(a, b);
        if (near >= tIn) {
          tIn = near;
          entry = axis;
        }
        tOut = Math.min(tOut, Math.max(a, b));
      }
      if (entry === null || tIn > tOut || tIn >= bestDist) continue;
      best = items[i];
      bestDist = tIn;
      bestAxis = entry;
    }
    if (!best) return null;
    const normal = new THREE.Vector3();
    normal[bestAxis] = dir[bestAxis] > 0 ? -1 : 1;
    return { item: best, dist: bestDist, point: new THREE.Vector3().copy(origin).addScaledVector(dir, bestDist), normal };
  }

  reset();

  return { items, reset, raycast, damage, update };
}
