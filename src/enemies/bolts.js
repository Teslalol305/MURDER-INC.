// Buzzard bolts: slow, visible, dodgeable projectiles. Each one is simulated: every step it is swept
// against the world (physics.raycast) and against the player's body capsule, and drawn as a red streak
// with a hot head through the shared glow batch. A fixed pool, no allocation in flight.

import * as THREE from 'three';
import { segmentHitsUpright } from './logic.js';

const STREAK = 2.4; // metres of trail behind the head
const HEAD_SIZE = 0.34;
const WIDTH = 0.11;
const GLOW = 9; // HDR multiplier on the tracer colour

export function createBolts(ctx) {
  const { G, cfg } = ctx;
  const capacity = cfg.pool.bolts;
  const target = cfg.buzzard.boltTarget;

  // Struct of arrays: position, unit direction, where it was fired from.
  const px = new Float64Array(capacity);
  const py = new Float64Array(capacity);
  const pz = new Float64Array(capacity);
  const dx = new Float64Array(capacity);
  const dy = new Float64Array(capacity);
  const dz = new Float64Array(capacity);
  const ox = new Float64Array(capacity);
  const oy = new Float64Array(capacity);
  const oz = new Float64Array(capacity);
  const life = new Float64Array(capacity); // seconds left; <= 0 = free
  const flown = new Float64Array(capacity);
  const damage = new Float64Array(capacity);
  const owner = new Array(capacity).fill(null);
  let next = 0;
  let live = 0;

  const origin = new THREE.Vector3();
  const dir = new THREE.Vector3();
  const hit = { dist: 0, point: new THREE.Vector3(), normal: new THREE.Vector3(), surface: null, box: null };
  const color = new THREE.Color((G.config.look && G.config.look.palette && G.config.look.palette.tracerEnemy) || 0xff3a22);

  function spawn(from, direction, amount, shooter) {
    // The oldest bolt makes room when all are in flight.
    let i = -1;
    for (let k = 0; k < capacity; k++) {
      const slot = (next + k) % capacity;
      if (life[slot] <= 0) {
        i = slot;
        break;
      }
    }
    if (i < 0) i = next;
    else live++;
    next = (i + 1) % capacity;
    px[i] = ox[i] = from.x;
    py[i] = oy[i] = from.y;
    pz[i] = oz[i] = from.z;
    dx[i] = direction.x;
    dy[i] = direction.y;
    dz[i] = direction.z;
    life[i] = ctx.tune.buzzard.boltLife;
    flown[i] = 0;
    damage[i] = amount;
    owner[i] = shooter;
  }

  function free(i) {
    life[i] = 0;
    owner[i] = null;
    live--;
  }

  /** The live explosive a world collider belongs to, or null (same rule as combat.js). */
  function explosiveBehind(box) {
    const items = G.explosives && G.explosives.items;
    if (!box || !items) return null;
    for (let k = 0; k < items.length; k++) {
      const item = items[k];
      if (item && item.state !== 'gone' && (item.box === box || box.owner === item)) return item;
    }
    return null;
  }

  function update(dt) {
    if (live === 0) return;
    const speed = ctx.tune.buzzard.boltSpeed;
    const player = G.player;
    const playerUp = player && player.pos && player.alive !== false;
    const step = speed * dt;
    for (let i = 0; i < capacity; i++) {
      if (life[i] <= 0) continue;
      origin.set(px[i], py[i], pz[i]);
      dir.set(dx[i], dy[i], dz[i]);
      const world = G.physics.raycast(origin, dir, step, hit);
      const reach = world ? world.dist : step;

      // The player's body: an upright capsule, shorter when he crouches.
      // (Only bolts that could reach him this step pay for the exact test.)
      const p = playerUp ? player.pos : null;
      if (p !== null && (p.x - px[i]) * (p.x - px[i]) + (p.z - pz[i]) * (p.z - pz[i]) < (reach + 1) * (reach + 1)) {
        const top = player.crouching ? target.crouchTop : target.top;
        const s = segmentHitsUpright(
          px[i], py[i], pz[i],
          px[i] + dx[i] * reach, py[i] + dy[i] * reach, pz[i] + dz[i] * reach,
          p.x, p.y + target.bottom, p.y + top, p.z, target.radius,
        );
        if (s >= 0) {
          player.damage(damage[i], new THREE.Vector3(ox[i], oy[i], oz[i]), 'bolt');
          free(i);
          continue;
        }
      }

      if (world) {
        const item = explosiveBehind(world.box);
        if (item && typeof G.explosives.damage === 'function') {
          const common = G.config.weapons && G.config.weapons.common;
          G.explosives.damage(item, (common && common.explosiveHitFromEnemy) || 9, owner[i]);
        }
        ctx.emit('impact', {
          point: world.point.clone(),
          normal: world.normal.clone(),
          surface: world.surface,
          dir: dir.clone(),
          from: 'enemy',
          enemy: null,
        });
        free(i);
        continue;
      }

      px[i] += dx[i] * step;
      py[i] += dy[i] * step;
      pz[i] += dz[i] * step;
      flown[i] += step;
      life[i] -= dt;
      if (life[i] <= 0) {
        life[i] = 0;
        owner[i] = null;
        live--;
      }
    }
  }

  /** Adds every bolt in flight to the glow batch. */
  function draw(glow) {
    if (live === 0) return;
    const r = color.r * GLOW;
    const g = color.g * GLOW;
    const b = color.b * GLOW;
    const a = glow.args; // through glow.args, not as arguments (glow.js: a double passed to a call is garbage)
    for (let i = 0; i < capacity; i++) {
      if (life[i] <= 0) continue;
      const tail = Math.min(STREAK, flown[i]);
      a[0] = px[i] - dx[i] * tail;
      a[1] = py[i] - dy[i] * tail;
      a[2] = pz[i] - dz[i] * tail;
      a[3] = px[i];
      a[4] = py[i];
      a[5] = pz[i];
      a[6] = WIDTH;
      a[7] = r * 0.6;
      a[8] = g * 0.6;
      a[9] = b * 0.6;
      glow.streakA();
      a[0] = px[i];
      a[1] = py[i];
      a[2] = pz[i];
      a[3] = HEAD_SIZE;
      a[4] = r;
      a[5] = g + 1.2;
      a[6] = b + 0.5;
      glow.flareA();
    }
  }

  function clear() {
    life.fill(0);
    owner.fill(null);
    live = 0;
  }

  return {
    spawn,
    update,
    draw,
    clear,
    get live() {
      return live;
    },
  };
}
