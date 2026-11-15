// Stub enemies (CONTRACT 6.6): dummy targets with the full API, so everything that shoots at, counts,
// spawns or gets shot by enemies can be built and tested before the real AI exists.
//
//   goon     an upright capsule (radius 0.35, 1.8 m tall) with a head sphere; pos = feet
//   buzzard  a hovering sphere; pos = centre
//
// They never move. They turn to face the player, notice him after a moment in view (or when alerted,
// hurt, or within earshot of gunfire) and then, with line of sight, fire one weak telegraphed hitscan
// shot every few seconds through G.combat.hitscan. A dead buzzard falls and bursts through
// G.combat.explode. Whoever runs the game decides where they stand: enemies.spawn(type, pos, opts).

import * as THREE from 'three';
import { angleDelta, moveToward } from '../core/util.js';

const POOL = { goon: 12, buzzard: 8 };
const SHAPE = {
  goon: { radius: 0.35, height: 1.8, bodyLow: 0.35, bodyHigh: 1.15, headY: 1.63, headRadius: 0.17, eyeY: 1.6, gunY: 1.35 },
  buzzard: { radius: 0.45, height: 0.45 },
};
// Boss-level numbers, used until setDifficulty() supplies a table.
const BASE = {
  goon: { hp: 110, damage: 6 },
  buzzard: { hp: 55, damage: 10 },
};
const SIGHT_RANGE = 45;
const NOTICE_TIME = 0.55; // seconds in view before an unaware dummy engages
const SENSE_EVERY = 0.15;
const TURN_RATE = 2.5;
const TELEGRAPH = 0.5;
const COOLDOWN = [2.5, 4];
const AIM_SPREAD = 0.05; // radians, per axis
const GUNFIRE_RADIUS = 45;
const GUNFIRE_EVERY = 0.3;
const BLAST_RADIUS = 30;
const BODY_TIME = 2.5; // a dead goon lies this long before its slot frees up
const BUZZARD_BURST = { radius: 3, damage: 30, playerScale: 0.5 };
const TRACER_COLOR = 0xff3b30;

const KILLED = Object.freeze({ killed: true });
const SURVIVED = Object.freeze({ killed: false });

export function createEnemies(G) {
  const rng = G.rng && typeof G.rng.fork === 'function' ? G.rng.fork('enemies') : null;
  const random = rng ? () => rng.next() : Math.random;
  const emit = (name, payload) => G.events && G.events.emit(name, payload);

  const root = new THREE.Group();
  root.name = 'enemies-stub';
  if (G.scene) G.scene.add(root);

  // Shared geometry and materials; one small group per pooled dummy.
  const dark = new THREE.MeshStandardMaterial({ color: 0x17171c, roughness: 0.85 });
  const oxblood = new THREE.MeshStandardMaterial({ color: 0x5a1016, roughness: 0.8 });
  const mask = new THREE.MeshStandardMaterial({ color: 0xd8d2c4, roughness: 0.7 });
  const glow = new THREE.MeshBasicMaterial({ color: new THREE.Color(3, 0.25, 0.15) });
  const geo = {
    body: new THREE.CapsuleGeometry(SHAPE.goon.radius, SHAPE.goon.bodyHigh - SHAPE.goon.bodyLow, 4, 12),
    head: new THREE.SphereGeometry(SHAPE.goon.headRadius, 12, 8),
    band: new THREE.BoxGeometry(0.24, 0.05, 0.08),
    hull: new THREE.SphereGeometry(SHAPE.buzzard.radius, 14, 10),
    eye: new THREE.SphereGeometry(0.09, 8, 6),
  };

  function part(geometry, material, x, y, z, parent) {
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(x, y, z);
    mesh.castShadow = true;
    parent.add(mesh);
    return mesh;
  }

  function buildObject(type) {
    const group = new THREE.Group();
    group.visible = false;
    group.rotation.order = 'YXZ'; // yaw first, so tipping over is relative to the facing
    if (type === 'goon') {
      const s = SHAPE.goon;
      part(geo.body, oxblood, 0, (s.bodyLow + s.bodyHigh) / 2, 0, group);
      part(geo.head, mask, 0, s.headY, 0, group);
      part(geo.band, glow, 0, s.headY + 0.02, -s.headRadius, group); // marks the front (local −Z)
    } else {
      part(geo.hull, dark, 0, 0, 0, group);
      part(geo.eye, glow, 0, -0.08, -SHAPE.buzzard.radius + 0.02, group);
    }
    root.add(group);
    return group;
  }

  const makeEnemy = (type) => ({
    id: 0,
    type,
    pos: new THREE.Vector3(),
    alive: false,
    hp: 0,
    maxHp: 0,
    radius: SHAPE[type].radius,
    height: SHAPE[type].height,
    state: 'idle', // 'patrol' (unaware) | 'engage' | 'dying' while active
    object: buildObject(type),
    yaw: 0,
    active: false,
    seen: 0,
    sees: false,
    senseIn: 0,
    cooldown: 0,
    telegraph: 0,
    deadTime: 0,
    fallSpeed: 0,
    hover: 0,
    baseY: 0,
  });

  const pool = {
    goon: Array.from({ length: POOL.goon }, () => makeEnemy('goon')),
    buzzard: Array.from({ length: POOL.buzzard }, () => makeEnemy('buzzard')),
  };
  const list = []; // active dummies: living and dying

  let nextId = 1;
  let difficulty = null;
  const scale = { hp: 1, damage: 1, cooldown: 1 };
  let sinceGunfire = Infinity;

  // Scratch vectors and the result of trace().
  const sensor = new THREE.Vector3();
  const aim = new THREE.Vector3();
  const muzzle = new THREE.Vector3();
  const shotDir = new THREE.Vector3();
  const probe = new THREE.Vector3();
  let traceEnemy = null;
  let traceDist = 0;
  let tracePart = 'body';
  let traceCentreY = 0; // height of the sphere centre / capsule axis point the hit normal points away from
  let capsuleY = 0; // the same, for the last rayCapsule() call

  const tuned = (type, key, fallback) => {
    const table = difficulty && difficulty[type];
    return table && Number.isFinite(table[key]) ? table[key] : fallback;
  };

  function spawn(type, pos, opts = {}) {
    const slots = pool[type];
    if (!slots) return null;
    // A free slot, else the slot of a dummy that is only lying there dead; null when all are alive.
    let enemy = slots.find((e) => !e.active);
    if (!enemy) {
      enemy = slots.find((e) => !e.alive);
      if (!enemy) return null;
      retire(enemy);
    }
    enemy.id = nextId++;
    enemy.active = true;
    enemy.alive = true;
    enemy.maxHp = enemy.hp = tuned(type, 'hp', BASE[type].hp) * scale.hp;
    enemy.pos.copy(pos);
    if (type === 'buzzard' && enemy.pos.y < 3) enemy.pos.y = 5; // asked for at ground level: hover under the El
    enemy.baseY = enemy.pos.y;
    enemy.hover = random() * Math.PI * 2;
    enemy.yaw = random() * Math.PI * 2;
    enemy.state = opts.alerted ? 'engage' : 'patrol';
    enemy.seen = 0;
    enemy.sees = false;
    enemy.senseIn = random() * SENSE_EVERY;
    enemy.cooldown = 1 + random() * 1.5;
    enemy.telegraph = 0;
    enemy.deadTime = 0;
    enemy.fallSpeed = 0;
    enemy.object.visible = true;
    enemy.object.scale.setScalar(1);
    enemy.object.rotation.set(0, enemy.yaw, 0);
    enemy.object.position.copy(enemy.pos);
    list.push(enemy);
    emit('enemy:spawn', { enemy });
    return enemy;
  }

  function retire(enemy) {
    enemy.active = false;
    enemy.alive = false;
    enemy.state = 'idle';
    enemy.object.visible = false;
    const i = list.indexOf(enemy);
    if (i >= 0) list.splice(i, 1);
  }

  function clear() {
    for (let i = list.length - 1; i >= 0; i--) retire(list[i]);
  }

  function engage(enemy, at) {
    if (!enemy.alive || enemy.state === 'engage') return;
    enemy.state = 'engage';
    emit('enemy:alert', { enemy, pos: (at || enemy.pos).clone() });
  }

  /** Everyone within radius of pos who is not engaged yet turns hostile. */
  function alert(pos, radius = 40) {
    for (let i = 0; i < list.length; i++) {
      const enemy = list[i];
      if (enemy.alive && enemy.state !== 'engage' && enemy.pos.distanceTo(pos) <= radius) engage(enemy, pos);
    }
  }

  /** Ray against a sphere; returns the entry distance or Infinity (rays starting inside miss). */
  function raySphere(origin, dir, cx, cy, cz, radius) {
    const ox = origin.x - cx;
    const oy = origin.y - cy;
    const oz = origin.z - cz;
    const b = ox * dir.x + oy * dir.y + oz * dir.z;
    const c = ox * ox + oy * oy + oz * oz - radius * radius;
    if (c <= 0) return Infinity;
    const disc = b * b - c;
    if (disc < 0) return Infinity;
    const t = -b - Math.sqrt(disc);
    return t >= 0 ? t : Infinity;
  }

  /** Ray against an upright capsule (axis from y0 to y1). Writes capsuleY for the hit normal. */
  function rayCapsule(origin, dir, cx, cz, y0, y1, radius) {
    const ox = origin.x - cx;
    const oz = origin.z - cz;
    const a = dir.x * dir.x + dir.z * dir.z;
    if (a > 1e-12) {
      const b = ox * dir.x + oz * dir.z;
      const c = ox * ox + oz * oz - radius * radius;
      const disc = b * b - a * c;
      if (disc < 0) return Infinity;
      const t = (-b - Math.sqrt(disc)) / a;
      const y = origin.y + dir.y * t;
      if (t >= 0 && c > 0 && y >= y0 && y <= y1) {
        capsuleY = y;
        return t;
      }
    }
    const low = raySphere(origin, dir, cx, y0, cz, radius);
    const high = raySphere(origin, dir, cx, y1, cz, radius);
    capsuleY = low <= high ? y0 : y1;
    return Math.min(low, high);
  }

  /** Nearest living dummy along a unit ray. Fills traceEnemy / traceDist / tracePart, no allocation. */
  function trace(origin, dir, maxDist) {
    traceEnemy = null;
    traceDist = maxDist;
    for (let i = 0; i < list.length; i++) {
      const enemy = list[i];
      if (!enemy.alive) continue;
      const p = enemy.pos;
      if (enemy.type === 'buzzard') {
        const t = raySphere(origin, dir, p.x, p.y, p.z, enemy.radius);
        if (t < traceDist) {
          traceDist = t;
          traceEnemy = enemy;
          tracePart = 'body';
          traceCentreY = p.y;
        }
        continue;
      }
      const s = SHAPE.goon;
      const head = raySphere(origin, dir, p.x, p.y + s.headY, p.z, s.headRadius);
      if (head < traceDist) {
        traceDist = head;
        traceEnemy = enemy;
        tracePart = 'head';
        traceCentreY = p.y + s.headY;
      }
      const torso = rayCapsule(origin, dir, p.x, p.z, p.y + s.bodyLow, p.y + s.bodyHigh, s.radius);
      if (torso < traceDist) {
        traceDist = torso;
        traceEnemy = enemy;
        tracePart = 'body';
        traceCentreY = capsuleY;
      }
    }
    return traceEnemy !== null;
  }

  function raycast(origin, dir, maxDist = 500) {
    if (!trace(origin, dir, maxDist)) return null;
    const enemy = traceEnemy;
    const point = new THREE.Vector3().copy(origin).addScaledVector(dir, traceDist);
    const normal = new THREE.Vector3(point.x - enemy.pos.x, point.y - traceCentreY, point.z - enemy.pos.z).normalize();
    return { enemy, dist: traceDist, point, normal, part: tracePart };
  }

  function aimTarget(origin, dir, maxDist = 60) {
    if (!trace(origin, dir, maxDist)) return false;
    probe.copy(origin).addScaledVector(dir, traceDist);
    return G.physics.lineOfSight(origin, probe);
  }

  function damage(enemy, amount, info = {}) {
    if (!enemy || !enemy.alive) return SURVIVED;
    enemy.hp -= amount;
    const partHit = info.part || 'body';
    emit('enemy:hit', { enemy, part: partHit, damage: amount, point: (info.point || enemy.pos).clone() });
    if (enemy.hp > 0) {
      engage(enemy); // being hurt gives the shooter away
      return SURVIVED;
    }
    enemy.hp = 0;
    enemy.alive = false;
    enemy.state = 'dying';
    enemy.deadTime = 0;
    enemy.fallSpeed = 0;
    emit('enemy:killed', {
      enemy,
      type: enemy.type,
      pos: enemy.pos.clone(),
      part: partHit,
      byPlayer: info.from === 'player' || info.from === 'blast',
      weapon: info.weapon || null,
    });
    return KILLED;
  }

  function fire(enemy, player) {
    const goon = enemy.type === 'goon';
    const p = enemy.pos;
    // A goon's gun is held out in front of the chest, a buzzard's hangs underneath.
    if (goon) muzzle.set(p.x - Math.sin(enemy.yaw) * 0.45, p.y + SHAPE.goon.gunY, p.z - Math.cos(enemy.yaw) * 0.45);
    else muzzle.set(p.x, p.y - enemy.radius - 0.05, p.z);
    aim.copy(player.pos);
    aim.y += player.crouching ? 0.6 : 1.0;
    shotDir.subVectors(aim, muzzle).normalize();
    shotDir.x += (random() * 2 - 1) * AIM_SPREAD;
    shotDir.y += (random() * 2 - 1) * AIM_SPREAD;
    shotDir.z += (random() * 2 - 1) * AIM_SPREAD;
    shotDir.normalize();
    const base = goon ? tuned('goon', 'shotDamage', BASE.goon.damage) : tuned('buzzard', 'boltDamage', BASE.buzzard.damage);
    const hit = G.combat.hitscan({
      origin: muzzle,
      dir: shotDir,
      range: 200,
      damage: base * scale.damage,
      from: enemy,
      weapon: enemy.type,
    });
    if (G.fx && typeof G.fx.tracer === 'function') G.fx.tracer(muzzle, hit.point, TRACER_COLOR);
    emit('enemy:fire', { enemy, type: enemy.type, pos: muzzle.clone(), dir: shotDir.clone() });
  }

  function updateDying(enemy, dt) {
    enemy.deadTime += dt;
    if (enemy.type === 'goon') {
      // Tip over backwards, lie there, then sink away.
      enemy.object.rotation.x = Math.min(1, enemy.deadTime / 0.45) * (Math.PI / 2);
      if (enemy.deadTime > BODY_TIME - 0.5) enemy.object.scale.setScalar(Math.max(0.01, (BODY_TIME - enemy.deadTime) / 0.5));
      if (enemy.deadTime >= BODY_TIME) retire(enemy);
      return;
    }
    // Buzzard: spin down and burst where it lands.
    enemy.fallSpeed += 9.5 * dt;
    enemy.pos.y -= enemy.fallSpeed * dt;
    enemy.object.rotation.y += (4 + enemy.deadTime * 14) * dt;
    enemy.object.position.copy(enemy.pos);
    const floor = G.physics.groundHeight(enemy.pos.x, enemy.pos.z, enemy.pos.y + 0.5) + enemy.radius;
    if (enemy.pos.y <= floor || enemy.deadTime > 5) {
      enemy.pos.y = Math.max(enemy.pos.y, floor);
      retire(enemy);
      G.combat.explode({ pos: enemy.pos, source: enemy, ...BUZZARD_BURST });
    }
  }

  function updateLiving(enemy, dt, player) {
    if (enemy.type === 'buzzard') {
      enemy.hover += dt * 1.7;
      enemy.pos.y = enemy.baseY + Math.sin(enemy.hover) * 0.15;
    }
    const target = player && player.alive !== false && player.pos ? player : null;
    if (target) {
      const facing = Math.atan2(-(target.pos.x - enemy.pos.x), -(target.pos.z - enemy.pos.z));
      enemy.yaw += moveToward(0, angleDelta(enemy.yaw, facing), TURN_RATE * dt);

      enemy.senseIn -= dt;
      if (enemy.senseIn <= 0) {
        enemy.senseIn += SENSE_EVERY;
        sensor.copy(enemy.pos);
        if (enemy.type === 'goon') sensor.y += SHAPE.goon.eyeY;
        const eye = target.eye || target.pos;
        enemy.sees = sensor.distanceTo(eye) < SIGHT_RANGE && G.physics.lineOfSight(sensor, eye);
        enemy.seen = enemy.sees ? enemy.seen + SENSE_EVERY : Math.max(0, enemy.seen - SENSE_EVERY * 0.6);
        if (enemy.state !== 'engage' && enemy.seen >= NOTICE_TIME) engage(enemy);
      }

      if (enemy.state === 'engage') {
        if (enemy.telegraph > 0) {
          enemy.telegraph -= dt;
          if (enemy.telegraph <= 0) {
            fire(enemy, target);
            enemy.cooldown = (COOLDOWN[0] + random() * (COOLDOWN[1] - COOLDOWN[0])) * scale.cooldown;
          }
        } else if (enemy.sees) {
          enemy.cooldown -= dt;
          if (enemy.cooldown <= 0) {
            enemy.telegraph = TELEGRAPH;
            emit('enemy:telegraph', { enemy, type: enemy.type, duration: TELEGRAPH, pos: enemy.pos.clone() });
          }
        }
      }
    }
    enemy.object.position.copy(enemy.pos);
    enemy.object.rotation.y = enemy.yaw;
  }

  function update(dt) {
    const player = G.player;
    sinceGunfire += dt;
    for (let i = list.length - 1; i >= 0; i--) {
      const enemy = list[i];
      if (enemy.alive) updateLiving(enemy, dt, player);
      else updateDying(enemy, dt);
    }
  }

  if (G.events) {
    G.events.on('weapon:fire', (e) => {
      if (sinceGunfire < GUNFIRE_EVERY || !e || !e.pos) return;
      sinceGunfire = 0;
      alert(e.pos, GUNFIRE_RADIUS);
    });
    G.events.on('explosion', (e) => {
      if (e && e.pos) alert(e.pos, BLAST_RADIUS);
    });
  }

  return {
    list,
    aliveCount() {
      let n = 0;
      for (let i = 0; i < list.length; i++) if (list[i].alive) n++;
      return n;
    },
    countByType(type) {
      let n = 0;
      for (let i = 0; i < list.length; i++) if (list[i].alive && list[i].type === type) n++;
      return n;
    },
    spawn,
    clear,
    raycast,
    damage,
    alert,
    hear: alert, // the dummies make no difference between hearing and being told
    setDifficulty(table) {
      difficulty = table || null;
    },
    setScale(s = {}) {
      scale.hp = s.hp > 0 ? s.hp : 1;
      scale.damage = s.damage > 0 ? s.damage : 1;
      scale.cooldown = s.cooldown > 0 ? s.cooldown : 1;
    },
    nearestDistance() {
      const player = G.player;
      let best = Infinity;
      if (!player || !player.pos) return best;
      for (let i = 0; i < list.length; i++) {
        if (list[i].alive) best = Math.min(best, list[i].pos.distanceTo(player.pos));
      }
      return best;
    },
    aimTarget,
    update,
  };
}
