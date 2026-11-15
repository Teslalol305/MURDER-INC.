// Small rigid things with real (if simple) physics, each kind one InstancedMesh:
//   shells   ejected brass: tumbles, bounces a few times, comes to rest on its side and stays there
//            until the ring buffer needs its slot
//   debris   chips, splinters and blast fragments: bounce, settle, shrink away
//
// Bodies fall under gravity onto "the floor under them" (asked from the world every few frames while
// they fly, so brass lands on a car bonnet or a scaffold deck rather than sinking through it) and
// bounce off the first wall in their way.

import * as THREE from 'three';

const GRAVITY = 9.81;
const FLOOR_EVERY = 4; // frames between floor queries for a flying body
const SHELL_MAX_BOUNCES = 4;

// ------------------------------------------------------------------------------------------------
// Pure body step (exported for tests)
// ------------------------------------------------------------------------------------------------

export const BODY = 16; // floats per body
// x y z, vx vy vz, yaw pitch roll, yaw-rate pitch-rate roll-rate, floor, bounces, radius, state
export const FLYING = 1;
export const RESTING = 2;

/**
 * Advances one body in `d` at offset `o`. Returns 1 when it touched the floor this step, else 0.
 * `restitution` is the share of vertical speed kept, `grip` the share of horizontal speed kept.
 */
export function stepBody(d, o, dt, restitution, grip, maxBounces) {
  if (d[o + 15] !== FLYING) return 0;
  d[o + 4] -= GRAVITY * dt;
  d[o] += d[o + 3] * dt;
  d[o + 1] += d[o + 4] * dt;
  d[o + 2] += d[o + 5] * dt;
  d[o + 6] += d[o + 9] * dt;
  d[o + 7] += d[o + 10] * dt;
  d[o + 8] += d[o + 11] * dt;
  const rest = d[o + 12] + d[o + 14];
  if (d[o + 1] > rest || d[o + 4] >= 0) return 0;

  d[o + 1] = rest;
  d[o + 13]++;
  const vy = -d[o + 4] * restitution;
  d[o + 3] *= grip;
  d[o + 5] *= grip;
  if (d[o + 13] >= maxBounces || vy < 0.55) {
    // Done bouncing: lie flat, stop.
    d[o + 3] = d[o + 4] = d[o + 5] = 0;
    d[o + 7] = 0;
    d[o + 9] = d[o + 10] = d[o + 11] = 0;
    d[o + 15] = RESTING;
  } else {
    d[o + 4] = vy;
    // A bounce scrambles the tumble.
    d[o + 9] *= -0.6;
    d[o + 10] *= 0.5;
    d[o + 11] *= 0.7;
  }
  return 1;
}

/** Writes the 4 × 4 matrix T · Ry(yaw) · Rz(pitch) · Rx(roll) · S(sx, sy, sz) of a body into `m` at `at`. */
function writeMatrix(m, at, d, o, sx, sy, sz) {
  const cy = Math.cos(d[o + 6]);
  const sy_ = Math.sin(d[o + 6]);
  const cp = Math.cos(d[o + 7]);
  const sp = Math.sin(d[o + 7]);
  const cr = Math.cos(d[o + 8]);
  const sr = Math.sin(d[o + 8]);
  // Columns of Ry · Rz · Rx.
  m[at] = cy * cp * sx;
  m[at + 1] = sp * sx;
  m[at + 2] = -sy_ * cp * sx;
  m[at + 3] = 0;
  m[at + 4] = (-cy * sp * cr + sy_ * sr) * sy;
  m[at + 5] = cp * cr * sy;
  m[at + 6] = (sy_ * sp * cr + cy * sr) * sy;
  m[at + 7] = 0;
  m[at + 8] = (cy * sp * sr + sy_ * cr) * sz;
  m[at + 9] = -cp * sr * sz;
  m[at + 10] = (-sy_ * sp * sr + cy * cr) * sz;
  m[at + 11] = 0;
  m[at + 12] = d[o];
  m[at + 13] = d[o + 1];
  m[at + 14] = d[o + 2];
  m[at + 15] = 1;
}

function hideMatrix(m, at) {
  for (let i = 0; i < 16; i++) m[at + i] = 0;
  m[at + 15] = 1;
}

/** Bounces a body off the wall recorded for it (walls are found once, when the body is thrown). */
function hitWall(d, o, wall, w, radius) {
  const dist = wall[w];
  if (!(dist < Infinity)) return;
  // Signed distance travelled toward the wall plane since the throw.
  const travelled = (d[o] - wall[w + 3]) * wall[w + 1] + (d[o + 2] - wall[w + 4]) * wall[w + 2];
  if (travelled < dist - radius) return;
  // Reflect about the wall normal (stored as the direction of travel that led to it).
  const vn = d[o + 3] * wall[w + 1] + d[o + 5] * wall[w + 2];
  if (vn > 0) {
    d[o + 3] -= 1.35 * vn * wall[w + 1];
    d[o + 5] -= 1.35 * vn * wall[w + 2];
    d[o + 3] *= 0.6;
    d[o + 5] *= 0.6;
  }
  wall[w] = Infinity;
}

// ------------------------------------------------------------------------------------------------
// Shells
// ------------------------------------------------------------------------------------------------

// Case sizes, a third larger than life so brass still reads on the ground: [length, radius].
const SHELL_SIZE = { rifle: [0.058, 0.0085], pistol: [0.027, 0.0085] };
const SHELL_KIND = { rifle: 'rifle', chopper: 'rifle', pistol: 'pistol', nine: 'pistol' };

/**
 * @param {object} world {floorAt(x, z, maxY), wallAhead(x, y, z, dx, dz, reach, out), surfaceAt(x, y, z)}
 * @param {function} onBounce (x, y, z, kind) → void, called on a shell's first touch of the floor
 */
export function createShells({ capacity, world, onBounce }) {
  const data = new Float32Array(capacity * BODY);
  const wall = new Float32Array(capacity * 5).fill(Infinity); // distance, dir x, dir z, start x, start z
  const size = new Float32Array(capacity * 2);
  const kindOf = new Uint8Array(capacity); // 0 rifle, 1 pistol
  const sinceFloor = new Uint8Array(capacity);

  const geometry = new THREE.CylinderGeometry(1, 1, 1, 7, 1);
  geometry.rotateZ(Math.PI / 2); // the case's axis is local X
  const material = new THREE.MeshStandardMaterial({ name: 'fx-brass', color: 0xc9a24a, metalness: 0.9, roughness: 0.32 });
  const mesh = new THREE.InstancedMesh(geometry, material, capacity);
  mesh.name = 'fx-shells';
  mesh.frustumCulled = false;
  mesh.castShadow = false;
  mesh.receiveShadow = false;
  mesh.matrixAutoUpdate = false;
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  const matrices = mesh.instanceMatrix.array;
  for (let i = 0; i < capacity; i++) hideMatrix(matrices, i * 16);
  mesh.visible = false;

  const probe = { dist: 0, nx: 0, nz: 0 };
  let next = 0;
  let flying = 0;
  let resting = 0;

  function add(x, y, z, vx, vy, vz, kind, random) {
    const i = next;
    next = (next + 1) % capacity;
    const o = i * BODY;
    if (data[o + 15] === FLYING) flying--;
    else if (data[o + 15] === RESTING) resting--;
    const which = SHELL_KIND[kind] || 'rifle';
    const [length, radius] = SHELL_SIZE[which];
    size[i * 2] = length;
    size[i * 2 + 1] = radius;
    kindOf[i] = which === 'pistol' ? 1 : 0;
    data[o] = x;
    data[o + 1] = y;
    data[o + 2] = z;
    data[o + 3] = vx;
    data[o + 4] = vy;
    data[o + 5] = vz;
    data[o + 6] = random() * 6.283;
    data[o + 7] = random.signed() * 0.8;
    data[o + 8] = random() * 6.283;
    data[o + 9] = random.signed() * 9;
    data[o + 10] = random.signed() * 22;
    data[o + 11] = random.signed() * 16;
    data[o + 12] = world.floorAt(x, z, y + 0.05);
    data[o + 13] = 0;
    data[o + 14] = radius;
    data[o + 15] = FLYING;
    sinceFloor[i] = 0;
    flying++;

    // The first wall in the way of the throw, if any.
    const w = i * 5;
    wall[w] = Infinity;
    const speed = Math.hypot(vx, vz);
    if (speed > 0.3 && world.wallAhead(x, y, z, vx / speed, vz / speed, speed * 1.4 + 0.3, probe)) {
      wall[w] = probe.dist;
      wall[w + 1] = vx / speed;
      wall[w + 2] = vz / speed;
      wall[w + 3] = x;
      wall[w + 4] = z;
    }
    mesh.visible = true;
  }

  function update(dt) {
    if (flying === 0) return;
    for (let i = 0; i < capacity; i++) {
      const o = i * BODY;
      if (data[o + 15] !== FLYING) continue;
      if (++sinceFloor[i] >= FLOOR_EVERY) {
        sinceFloor[i] = 0;
        data[o + 12] = world.floorAt(data[o], data[o + 2], data[o + 1] + 0.05);
      }
      hitWall(data, o, wall, i * 5, 0.03);
      // Restitution 0.32–0.48, different on every bounce.
      const restitution = 0.32 + 0.16 * ((i * 0.618 + data[o + 13] * 0.37) % 1);
      const touched = stepBody(data, o, dt, restitution, 0.6, SHELL_MAX_BOUNCES);
      if (touched && data[o + 13] === 1) onBounce(data[o], data[o + 1], data[o + 2], kindOf[i]);
      if (data[o + 15] === RESTING) {
        flying--;
        resting++;
      }
      writeMatrix(matrices, i * 16, data, o, size[i * 2], size[i * 2 + 1], size[i * 2 + 1]);
    }
    mesh.instanceMatrix.needsUpdate = true;
  }

  function clear() {
    for (let i = 0; i < capacity; i++) {
      data[i * BODY + 15] = 0;
      hideMatrix(matrices, i * 16);
    }
    flying = resting = 0;
    next = 0;
    mesh.instanceMatrix.needsUpdate = true;
    mesh.visible = false;
  }

  return {
    mesh,
    capacity,
    add,
    update,
    clear,
    get count() {
      return flying + resting;
    },
    get flying() {
      return flying;
    },
  };
}

// ------------------------------------------------------------------------------------------------
// Debris
// ------------------------------------------------------------------------------------------------

const DEBRIS_FADE = 0.45; // seconds a chunk takes to shrink away at the end of its life

/** A chipped lump: a low-poly ball with its corners pulled about. */
function chunkGeometry() {
  const geometry = new THREE.IcosahedronGeometry(0.5, 0);
  const p = geometry.attributes.position;
  for (let i = 0; i < p.count; i++) {
    // Keyed on the corner's position, so the faces that share it stay joined.
    const wave = Math.sin(p.getX(i) * 12.9898 + p.getY(i) * 78.233 + p.getZ(i) * 37.719) * 43758.5453;
    const k = 0.7 + 0.55 * (wave - Math.floor(wave));
    p.setXYZ(i, p.getX(i) * k, p.getY(i) * k * 0.8, p.getZ(i) * k);
  }
  geometry.computeVertexNormals();
  return geometry;
}

export function createDebris({ capacity, world }) {
  const data = new Float32Array(capacity * BODY);
  const extra = new Float32Array(capacity * 5); // sx, sy, sz, age, life
  const wall = new Float32Array(capacity * 5).fill(Infinity);
  const sinceFloor = new Uint8Array(capacity);

  const material = new THREE.MeshLambertMaterial({ name: 'fx-debris', color: 0xffffff });
  const mesh = new THREE.InstancedMesh(chunkGeometry(), material, capacity);
  mesh.name = 'fx-debris';
  mesh.frustumCulled = false;
  mesh.castShadow = false;
  mesh.receiveShadow = false;
  mesh.matrixAutoUpdate = false;
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  // Created up front: adding instance colours later would recompile the shader mid-game.
  mesh.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(capacity * 3).fill(1), 3);
  mesh.instanceColor.setUsage(THREE.DynamicDrawUsage);
  mesh.count = 0;
  mesh.visible = false;

  const matrices = mesh.instanceMatrix.array;
  const colors = mesh.instanceColor.array;
  const probe = { dist: 0, nx: 0, nz: 0 };
  let count = 0;
  let budget = capacity; // soft cap, lowered by the quality preset

  /**
   * One chunk. (sx, sy, sz) is its size in metres along its own axes; (r, g, b) linear colour.
   * A full pool recycles the chunk that is nearest its end.
   */
  function add(x, y, z, vx, vy, vz, sx, sy, sz, r, g, b, life, random) {
    let i = count;
    if (i >= budget) {
      let best = 0;
      for (let k = 1; k < count; k++) {
        if (extra[k * 5 + 3] / extra[k * 5 + 4] > extra[best * 5 + 3] / extra[best * 5 + 4]) best = k;
      }
      i = best;
    } else {
      count = i + 1;
    }
    const o = i * BODY;
    data[o] = x;
    data[o + 1] = y;
    data[o + 2] = z;
    data[o + 3] = vx;
    data[o + 4] = vy;
    data[o + 5] = vz;
    data[o + 6] = random() * 6.283;
    data[o + 7] = random() * 6.283;
    data[o + 8] = random() * 6.283;
    data[o + 9] = random.signed() * 14;
    data[o + 10] = random.signed() * 14;
    data[o + 11] = random.signed() * 14;
    data[o + 12] = world.floorAt(x, z, y + 0.05);
    data[o + 13] = 0;
    data[o + 14] = Math.min(sx, sy, sz) * 0.5;
    data[o + 15] = FLYING;
    const e = i * 5;
    extra[e] = sx;
    extra[e + 1] = sy;
    extra[e + 2] = sz;
    extra[e + 3] = 0;
    extra[e + 4] = life;
    colors[i * 3] = r;
    colors[i * 3 + 1] = g;
    colors[i * 3 + 2] = b;
    mesh.instanceColor.needsUpdate = true;
    sinceFloor[i] = (i * 3) % FLOOR_EVERY;

    const w = i * 5;
    wall[w] = Infinity;
    const speed = Math.hypot(vx, vz);
    if (speed > 1 && world.wallAhead(x, y, z, vx / speed, vz / speed, speed * 0.9 + 0.3, probe)) {
      wall[w] = probe.dist;
      wall[w + 1] = vx / speed;
      wall[w + 2] = vz / speed;
      wall[w + 3] = x;
      wall[w + 4] = z;
    }
  }

  function update(dt) {
    if (count === 0) {
      mesh.visible = false;
      return;
    }
    let i = 0;
    while (i < count) {
      const o = i * BODY;
      const e = i * 5;
      extra[e + 3] += dt;
      if (extra[e + 3] >= extra[e + 4]) {
        // Dead: the last chunk takes its slot.
        count--;
        if (i !== count) {
          data.copyWithin(o, count * BODY, count * BODY + BODY);
          extra.copyWithin(e, count * 5, count * 5 + 5);
          wall.copyWithin(i * 5, count * 5, count * 5 + 5);
          colors.copyWithin(i * 3, count * 3, count * 3 + 3);
          sinceFloor[i] = sinceFloor[count];
          mesh.instanceColor.needsUpdate = true;
        }
        continue;
      }
      if (data[o + 15] === FLYING) {
        if (++sinceFloor[i] >= FLOOR_EVERY) {
          sinceFloor[i] = 0;
          data[o + 12] = world.floorAt(data[o], data[o + 2], data[o + 1] + 0.05);
        }
        hitWall(data, o, wall, i * 5, 0.05);
        stepBody(data, o, dt, 0.3 + 0.15 * ((i * 0.618) % 1), 0.55, 3);
      }
      const left = extra[e + 4] - extra[e + 3];
      const k = left < DEBRIS_FADE ? left / DEBRIS_FADE : 1;
      writeMatrix(matrices, i * 16, data, o, extra[e] * k, extra[e + 1] * k, extra[e + 2] * k);
      i++;
    }
    mesh.count = count;
    mesh.visible = count > 0;
    mesh.instanceMatrix.needsUpdate = true;
  }

  function clear() {
    count = 0;
    mesh.count = 0;
    mesh.visible = false;
  }

  return {
    mesh,
    capacity,
    add,
    update,
    clear,
    get count() {
      return count;
    },
    get budget() {
      return budget;
    },
    set budget(n) {
      budget = Math.max(1, Math.min(capacity, Math.round(n)));
    },
  };
}
