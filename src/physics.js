// World collision and navigation (`G.physics`), CONTRACT 5.1.
//
// The static world is a flat list of axis-aligned boxes; the ground is the implicit plane y = 0.
// Nothing here knows about meshes: the level registers colliders and everything else queries them.
// Boxes are immutable once added (remove and re-add to move one), because their coordinates are
// mirrored into typed arrays that every query loops over.
//
// Flags:  bulletOnly  hit by rays, ignored by movement and nav
//         playerOnly  blocks capsule movement, ignored by rays and nav
//         noNav       not stamped into the nav grid
//
// Extras beyond the contract: `physics.bounds`, `physics.overlapsCylinder()`, an optional reusable
// result object as the last argument of `raycast` / `moveCapsule` / `nav.findPath`, and a few read-only
// nav fields for debug overlays and tests (`nav.cols`, `rows`, `origin`, `grid`, `lastExpansions`, `rebuilds`).

import * as THREE from 'three';

/* ---------------------------------------------------------------------------------------- tuning */

const STEP_HEIGHT = 0.42; // tallest ledge a grounded body walks up, and the furthest it snaps down
const AIR_STEP = 0.08; // ledge tolerance while airborne (a jump that just reaches a top still lands on it)
const SUBSTEP = 0.6; // longest horizontal sub-step, in body radii
const PUSH_ITERATIONS = 3;
const FOOTPRINT = 0.7; // half-size of the square under a body that finds its floor, in body radii
const LOS_SLACK = 0.05; // lineOfSight stops this short of the far point
const GROUND_SURFACE = 'asphalt'; // ground plane surface when the level has no opinion

const SLICE_THRESHOLD = 0.2; // |sin 2·yaw| above which an oriented box is sliced
const SLICE_MAX = 10;
const SLICE_SHRINK = 0.86; // a slice's AABB is shrunk 7 % per side

const NAV_CELL = 0.5;
const NAV_INFLATE = 0.5; // obstacle growth: body radius plus some clearance
const NAV_BAND_MIN = 0.47; // lower boxes are stepped over
const NAV_BAND_MAX = 1.5; // boxes that start higher are walked under
const NAV_SNAP_RINGS = 12; // how far (cells) a blocked start or goal looks for a free cell
const NAV_MIN_EXPANSIONS = 9000; // search budget; larger grids get half their cell count instead
const NAV_RANDOM_TRIES = 24;
const NAV_H_SCALE = 1.001; // octile heuristic nudged up so ties resolve toward the goal

const BULLET_ONLY = 1;
const PLAYER_ONLY = 2;
const GROUND = -2; // pseudo box index for the ground plane

const SQRT2 = Math.SQRT2;
// 8 neighbours: the four straight ones first, then the diagonals.
const DIR_X = [1, -1, 0, 0, 1, 1, -1, -1];
const DIR_Z = [0, 0, 1, -1, 1, -1, 1, -1];

const clampInt = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);

/** Reads [x, y, z] or anything with x / y / z into a new Vector3. */
function toVector(v) {
  return Array.isArray(v) ? new THREE.Vector3(v[0], v[1], v[2]) : new THREE.Vector3(v.x, v.y, v.z);
}

export function createPhysics(G) {
  /* ---------------------------------------------------------------------------------- box list */

  const boxes = [];
  const bounds = { minX: -46, maxX: 46, minZ: -34, maxZ: 34 };

  // Packed mirror of `boxes` for the query loops: 6 doubles per box (min xyz, max xyz) plus a flag byte.
  let packed = new Float64Array(6 * 256);
  let flags = new Uint8Array(256);
  let count = 0;
  let packDirty = false;
  let navDirty = true;

  function repack() {
    packDirty = false;
    count = boxes.length;
    if (count > flags.length) {
      const capacity = Math.max(count, flags.length * 2);
      packed = new Float64Array(6 * capacity);
      flags = new Uint8Array(capacity);
    }
    for (let i = 0, o = 0; i < count; i++, o += 6) {
      const b = boxes[i];
      packed[o] = b.min.x;
      packed[o + 1] = b.min.y;
      packed[o + 2] = b.min.z;
      packed[o + 3] = b.max.x;
      packed[o + 4] = b.max.y;
      packed[o + 5] = b.max.z;
      flags[i] = (b.bulletOnly ? BULLET_ONLY : 0) | (b.playerOnly ? PLAYER_ONLY : 0);
    }
  }

  const blocksNav = (b) =>
    !b.noNav && !b.bulletOnly && !b.playerOnly && b.max.y >= NAV_BAND_MIN && b.min.y <= NAV_BAND_MAX;

  function addBox(spec) {
    const min = toVector(spec.min);
    const max = toVector(spec.max);
    const box = {
      min: min.clone().min(max),
      max: max.max(min),
      surface: spec.surface || 'concrete',
      tag: spec.tag,
      noNav: !!spec.noNav,
      bulletOnly: !!spec.bulletOnly,
      playerOnly: !!spec.playerOnly,
      owner: spec.owner,
    };
    boxes.push(box);
    packDirty = true;
    if (blocksNav(box)) navDirty = true;
    return box;
  }

  /**
   * Adds a box rotated by `yaw` about +Y (same sense as Object3D.rotation.y). Near-axis yaws become one
   * box; anything else is sliced along its long side into up to 10 pieces whose world AABBs, shrunk a
   * little, stand in for the oriented shape. `center` is the middle of the box on all three axes.
   */
  function addOriented(center, size, yaw = 0, opts = {}) {
    const c = toVector(center);
    const [sx, sy, sz] = Array.isArray(size) ? size : [size.x, size.y, size.z];
    const sin = Math.sin(yaw);
    const cos = Math.cos(yaw);
    const y0 = c.y - sy / 2;
    const y1 = c.y + sy / 2;
    const add = (px, pz, hx, hz) =>
      addBox({ ...opts, min: [px - hx, y0, pz - hz], max: [px + hx, y1, pz + hz] });

    if (Math.abs(Math.sin(2 * yaw)) <= SLICE_THRESHOLD) {
      // Snap to the nearest right angle; a quarter turn swaps the footprint.
      const quarter = Math.abs(sin) > Math.abs(cos);
      return [add(c.x, c.z, (quarter ? sz : sx) / 2, (quarter ? sx : sz) / 2)];
    }

    const alongX = sx >= sz;
    const long = alongX ? sx : sz;
    const short = Math.max(alongX ? sz : sx, 1e-3);
    const n = clampInt(Math.ceil(long / short), 1, SLICE_MAX);
    const piece = long / n;
    // Local +X maps to (cos, −sin) in world XZ, local +Z to (sin, cos).
    const ax = alongX ? cos : sin;
    const az = alongX ? -sin : cos;
    const hlx = (alongX ? piece : sx) / 2;
    const hlz = (alongX ? sz : piece) / 2;
    // Shrunk AABB half extents of one rotated piece, but never so small that neighbours stop overlapping.
    const gap = n > 1 ? 0.01 : 0;
    const hx = Math.max((Math.abs(cos) * hlx + Math.abs(sin) * hlz) * SLICE_SHRINK, Math.abs(ax) * piece * 0.5 + gap);
    const hz = Math.max((Math.abs(sin) * hlx + Math.abs(cos) * hlz) * SLICE_SHRINK, Math.abs(az) * piece * 0.5 + gap);
    const out = [];
    for (let k = 0; k < n; k++) {
      const t = (k + 0.5) * piece - long / 2;
      out.push(add(c.x + ax * t, c.z + az * t, hx, hz));
    }
    return out;
  }

  function removeBox(box) {
    const i = boxes.indexOf(box);
    if (i < 0) return;
    boxes.splice(i, 1);
    packDirty = true;
    if (blocksNav(box)) navDirty = true;
  }

  function removeBoxes(list) {
    if (!list || !list.length) return;
    const gone = new Set(list);
    let kept = 0;
    for (let i = 0; i < boxes.length; i++) {
      const b = boxes[i];
      if (gone.has(b)) {
        if (blocksNav(b)) navDirty = true;
      } else {
        boxes[kept++] = b;
      }
    }
    if (kept !== boxes.length) {
      boxes.length = kept;
      packDirty = true;
    }
  }

  function setBounds(b) {
    bounds.minX = Math.min(b.minX, b.maxX);
    bounds.maxX = Math.max(b.minX, b.maxX);
    bounds.minZ = Math.min(b.minZ, b.maxZ);
    bounds.maxZ = Math.max(b.minZ, b.maxZ);
    navDirty = true;
  }

  function groundSurface(x, z) {
    const level = G.level;
    return (level && typeof level.groundSurfaceAt === 'function' && level.groundSurfaceAt(x, z)) || GROUND_SURFACE;
  }

  /* -------------------------------------------------------------------------------------- rays */

  // The ray being cast. Doubles handed to a function as arguments (or handed back as its result) are
  // boxed on the heap by V8, one small object each, and this is the most called code in the game: so
  // the ray travels in a typed array instead, and a query allocates nothing.
  //   in:  [0..2] origin, [3..5] unit direction, [6] reach      out: [7] distance of the hit
  const ray = new Float64Array(8);
  let hitIndex = -1; // box index of the last cast, GROUND, or -1
  let hitAxis = 0; // 0 x, 1 y, 2 z: the face the ray entered through

  /**
   * Slab test of the ray in `ray` against every ray-solid box and the ground plane.
   * Returns whether anything was hit within reach; the distance of the nearest entry goes to ray[7] and
   * hitIndex / hitAxis say what and where.
   * A box that contains the origin is ignored (rays only hit faces they enter through).
   * With `any` the first hit found ends the search (occlusion queries).
   * The three axes are written out one after the other on purpose: this is the hottest loop in the game.
   */
  function cast(any) {
    if (packDirty) repack();
    const ox = ray[0];
    const oy = ray[1];
    const oz = ray[2];
    const dx = ray[3];
    const dy = ray[4];
    const dz = ray[5];
    const ix = dx !== 0 ? 1 / dx : 0;
    const iy = dy !== 0 ? 1 / dy : 0;
    const iz = dz !== 0 ? 1 / dz : 0;
    let best = ray[6];
    let index = -1;
    let face = 0;
    for (let i = 0, o = 0; i < count; i++, o += 6) {
      if (flags[i] & PLAYER_ONLY) continue;
      let tmin = 0;
      let tmax = best;
      let axis = -1;
      let t1;
      let t2;
      if (dx !== 0) {
        t1 = (packed[o] - ox) * ix;
        t2 = (packed[o + 3] - ox) * ix;
        if (t1 > t2) {
          const s = t1;
          t1 = t2;
          t2 = s;
        }
        if (t1 >= tmin) {
          tmin = t1;
          axis = 0;
        }
        if (t2 < tmax) tmax = t2;
        if (tmin > tmax) continue;
      } else if (ox < packed[o] || ox > packed[o + 3]) continue;
      if (dy !== 0) {
        t1 = (packed[o + 1] - oy) * iy;
        t2 = (packed[o + 4] - oy) * iy;
        if (t1 > t2) {
          const s = t1;
          t1 = t2;
          t2 = s;
        }
        if (t1 >= tmin) {
          tmin = t1;
          axis = 1;
        }
        if (t2 < tmax) tmax = t2;
        if (tmin > tmax) continue;
      } else if (oy < packed[o + 1] || oy > packed[o + 4]) continue;
      if (dz !== 0) {
        t1 = (packed[o + 2] - oz) * iz;
        t2 = (packed[o + 5] - oz) * iz;
        if (t1 > t2) {
          const s = t1;
          t1 = t2;
          t2 = s;
        }
        if (t1 >= tmin) {
          tmin = t1;
          axis = 2;
        }
        if (t2 < tmax) tmax = t2;
        if (tmin > tmax) continue;
      } else if (oz < packed[o + 2] || oz > packed[o + 5]) continue;
      if (axis < 0 || tmin >= best) continue;
      best = tmin;
      index = i;
      face = axis;
      if (any) break;
    }
    if (dy < 0 && oy >= 0 && !(any && index !== -1)) {
      const t = -oy / dy;
      if (t < best) {
        best = t;
        index = GROUND;
        face = 1;
      }
    }
    hitIndex = index;
    hitAxis = face;
    ray[7] = best;
    return index !== -1;
  }

  /**
   * Nearest hit along a ray, or null. `dir` need not be normalised; `dist` is always in metres.
   * Pass `out` (an object with `point` and `normal` Vector3s, e.g. a previous result) to avoid allocating.
   */
  function raycast(origin, dir, maxDist = 500, out) {
    let dx = dir.x;
    let dy = dir.y;
    let dz = dir.z;
    const lenSq = dx * dx + dy * dy + dz * dz;
    if (lenSq === 0) return null;
    if (Math.abs(lenSq - 1) > 1e-6) {
      const inv = 1 / Math.sqrt(lenSq);
      dx *= inv;
      dy *= inv;
      dz *= inv;
    }
    ray[0] = origin.x;
    ray[1] = origin.y;
    ray[2] = origin.z;
    ray[3] = dx;
    ray[4] = dy;
    ray[5] = dz;
    ray[6] = maxDist;
    if (!cast(false)) return null;
    const dist = ray[7];
    const hit = out || { dist: 0, point: new THREE.Vector3(), normal: new THREE.Vector3(), surface: null, box: null };
    hit.dist = dist;
    hit.point.set(origin.x + dx * dist, origin.y + dy * dist, origin.z + dz * dist);
    const d = hitAxis === 0 ? dx : hitAxis === 1 ? dy : dz;
    hit.normal.set(0, 0, 0).setComponent(hitAxis, d > 0 ? -1 : 1);
    if (hitIndex === GROUND) {
      hit.box = null;
      hit.surface = groundSurface(hit.point.x, hit.point.z);
    } else {
      hit.box = boxes[hitIndex];
      hit.surface = hit.box.surface;
    }
    return hit;
  }

  /** True when nothing ray-solid lies between the two points (allocation free). */
  function lineOfSight(a, b) {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const dz = b.z - a.z;
    const len = Math.sqrt(dx * dx + dy * dy + dz * dz);
    if (len <= LOS_SLACK) return true;
    const inv = 1 / len;
    ray[0] = a.x;
    ray[1] = a.y;
    ray[2] = a.z;
    ray[3] = dx * inv;
    ray[4] = dy * inv;
    ray[5] = dz * inv;
    ray[6] = len - LOS_SLACK;
    return !cast(true);
  }

  /** Highest walkable top at (x, z) that is not above maxY; 0 (the ground) when there is none. */
  function groundHeight(x, z, maxY = 50) {
    if (packDirty) repack();
    let h = 0;
    for (let i = 0, o = 0; i < count; i++, o += 6) {
      if (flags[i]) continue; // real geometry only: neither bullet-only nor player-only
      const top = packed[o + 4];
      if (top <= h || top > maxY) continue;
      if (x < packed[o] || x > packed[o + 3] || z < packed[o + 2] || z > packed[o + 5]) continue;
      h = top;
    }
    return h;
  }

  /** Does an upright cylinder (y0..y1) overlap any box that blocks movement? (headroom, spawn checks) */
  function overlapsCylinder(x, z, radius, y0, y1) {
    if (packDirty) repack();
    const r2 = radius * radius;
    for (let i = 0, o = 0; i < count; i++, o += 6) {
      if (flags[i] & BULLET_ONLY) continue;
      if (packed[o + 4] <= y0 || packed[o + 1] >= y1) continue;
      const cx = x < packed[o] ? packed[o] : x > packed[o + 3] ? packed[o + 3] : x;
      const cz = z < packed[o + 2] ? packed[o + 2] : z > packed[o + 5] ? packed[o + 5] : z;
      if ((x - cx) * (x - cx) + (z - cz) * (z - cz) < r2) return true;
    }
    return false;
  }

  /* ---------------------------------------------------------------------------------- movement */

  // What moveCapsule() shares with its helpers, in a typed array for the same reason as `ray` (a double
  // passed to a function or written to a closure variable is boxed on the heap every time):
  //   set by moveCapsule:  [0] x, [1] z of the spot to scan, [2] body radius, [3] step top, [4] head height
  //   set by scanColumn:   [5] floor height, [6] ceiling height (and floorIndex, the floor's box)
  const body = new Float64Array(7);
  const FLOOR = 5;
  const CEILING = 6;
  let floorIndex = GROUND;

  /**
   * What is under and over the body described in `body`. The floor is the highest top not above the step
   * top under a square footprint smaller than the body, so the body can lean over an edge without standing
   * on thin air or on a wall it merely touches. The ceiling is the lowest bottom at or above the head
   * over the whole cylinder, the same extent the wall test uses, so a body can never rise into a box
   * beside it. Boxes between the two heights are walls, not floors or ceilings.
   */
  function scanColumn() {
    const x = body[0];
    const z = body[1];
    const radius = body[2];
    const stepTop = body[3];
    const head = body[4];
    const foot = FOOTPRINT * radius;
    const r2 = radius * radius;
    let floorY = 0;
    let ceilingY = Infinity;
    floorIndex = GROUND;
    for (let i = 0, o = 0; i < count; i++, o += 6) {
      if (flags[i] & BULLET_ONLY) continue;
      const x0 = packed[o];
      const x1 = packed[o + 3];
      const z0 = packed[o + 2];
      const z1 = packed[o + 5];
      const top = packed[o + 4];
      if (top <= stepTop) {
        if (top > floorY && x + foot > x0 && x - foot < x1 && z + foot > z0 && z - foot < z1) {
          floorY = top;
          floorIndex = i;
        }
      } else if (packed[o + 1] >= head - 1e-4 && packed[o + 1] < ceilingY) {
        const dx = x - (x < x0 ? x0 : x > x1 ? x1 : x);
        const dz = z - (z < z0 ? z0 : z > z1 ? z1 : z);
        if (dx * dx + dz * dz < r2) ceilingY = packed[o + 1];
      }
    }
    body[FLOOR] = floorY;
    body[CEILING] = ceilingY;
  }

  /** Treats the play bounds as walls for the body in `body`; true when it had to be moved. */
  function keepInside(pos, vel) {
    const radius = body[2];
    let moved = false;
    if (pos.x < bounds.minX + radius) {
      pos.x = bounds.minX + radius;
      if (vel.x < 0) vel.x = 0;
      moved = true;
    } else if (pos.x > bounds.maxX - radius) {
      pos.x = bounds.maxX - radius;
      if (vel.x > 0) vel.x = 0;
      moved = true;
    }
    if (pos.z < bounds.minZ + radius) {
      pos.z = bounds.minZ + radius;
      if (vel.z < 0) vel.z = 0;
      moved = true;
    } else if (pos.z > bounds.maxZ - radius) {
      pos.z = bounds.maxZ - radius;
      if (vel.z > 0) vel.z = 0;
      moved = true;
    }
    return moved;
  }

  /**
   * Moves an upright cylinder (origin at the feet) by vel·dt, mutating pos and vel.
   *
   * `allowStep` should be the body's grounded state from the previous frame: grounded bodies walk up
   * ledges of up to 0.42 m and stay glued to the floor going down them; airborne ones (false) only get
   * a 0.08 m tolerance and never snap. A ledge with too little headroom above it counts as a wall, and
   * so do the play bounds.
   * Returns {onGround, hitWall, hitCeil, surface}; `surface` is what lies under the feet. Pass `out` to
   * reuse a result object.
   */
  function moveCapsule(pos, vel, dt, radius = 0.32, height = 1.8, allowStep = true, out) {
    if (packDirty) repack();
    const startX = pos.x;
    const startZ = pos.z;
    const feet = pos.y;
    const head = feet + height;
    const stepTop = feet + (allowStep ? STEP_HEIGHT : AIR_STEP);
    const r2 = radius * radius;
    let hitWall = false;
    body[2] = radius;
    body[3] = stepTop;
    body[4] = head;

    // Horizontal: short sub-steps, each followed by push-out passes that also strip the velocity
    // component pointing into the obstacle, which is what makes the body slide along walls.
    const travel = Math.sqrt(vel.x * vel.x + vel.z * vel.z) * dt;
    const steps = Math.max(1, Math.ceil(travel / (SUBSTEP * radius)));
    const h = dt / steps;
    for (let s = 0; s < steps; s++) {
      pos.x += vel.x * h;
      pos.z += vel.z * h;
      for (let iter = 0; iter < PUSH_ITERATIONS; iter++) {
        // The bounds first, so that boxes are always tested from a spot inside the world.
        let pushed = keepInside(pos, vel);
        for (let i = 0, o = 0; i < count; i++, o += 6) {
          if (flags[i] & BULLET_ONLY) continue;
          // Low enough to step onto, or entirely above the head: not a wall.
          if (packed[o + 4] <= stepTop || packed[o + 1] >= head) continue;
          const x0 = packed[o];
          const x1 = packed[o + 3];
          const z0 = packed[o + 2];
          const z1 = packed[o + 5];
          const px = pos.x;
          const pz = pos.z;
          let nx = px - (px < x0 ? x0 : px > x1 ? x1 : px);
          let nz = pz - (pz < z0 ? z0 : pz > z1 ? z1 : pz);
          const d2 = nx * nx + nz * nz;
          if (d2 >= r2) continue;
          let push;
          if (d2 > 1e-12) {
            const d = Math.sqrt(d2);
            nx /= d;
            nz /= d;
            push = radius - d;
          } else {
            // Centre inside the box: leave through the nearest face.
            const left = px - x0;
            const right = x1 - px;
            const back = pz - z0;
            const front = z1 - pz;
            const m = Math.min(left, right, back, front);
            nx = m === left ? -1 : m === right ? 1 : 0;
            nz = nx !== 0 ? 0 : m === back ? -1 : 1;
            push = m + radius;
          }
          pos.x += nx * push;
          pos.z += nz * push;
          const vn = vel.x * nx + vel.z * nz;
          if (vn < 0) {
            vel.x -= vn * nx;
            vel.z -= vn * nz;
          }
          pushed = true;
        }
        if (!pushed) break;
        hitWall = true;
      }
    }
    // The bounds have the last word: nothing leaves the world, whatever the level leaves open.
    if (keepInside(pos, vel)) hitWall = true;

    // Vertical, at the new spot.
    body[0] = pos.x;
    body[1] = pos.z;
    scanColumn();
    if (body[FLOOR] > feet && body[FLOOR] + height > body[CEILING] + 1e-4) {
      // A step up with no headroom above it is a wall after all: stay where the frame began…
      pos.x = startX;
      pos.z = startZ;
      vel.x = 0;
      vel.z = 0;
      hitWall = true;
      body[0] = startX;
      body[1] = startZ;
      scanColumn();
      // …and should that spot be no better (wedged in a gap beside the step), at least do not rise.
      if (body[FLOOR] > feet && body[FLOOR] + height > body[CEILING] + 1e-4) body[FLOOR] = feet;
    }
    const floor = body[FLOOR];
    const ceiling = body[CEILING];

    let y = feet + vel.y * dt;
    let onGround = false;
    let hitCeil = false;
    if (vel.y > 0 && y + height > ceiling) {
      y = ceiling - height;
      vel.y = 0;
      hitCeil = true;
    }
    if (y <= floor) {
      // Landed, or stepped up onto a ledge.
      y = floor;
      if (vel.y < 0) vel.y = 0;
      onGround = true;
    } else if (allowStep && vel.y <= 0 && y - floor <= STEP_HEIGHT) {
      // Walking down a step or kerb: stay on the floor instead of going airborne.
      y = floor;
      vel.y = 0;
      onGround = true;
    }
    pos.y = y;

    const res = out || { onGround: false, hitWall: false, hitCeil: false, surface: GROUND_SURFACE };
    res.onGround = onGround;
    res.hitWall = hitWall;
    res.hitCeil = hitCeil;
    res.surface = floorIndex === GROUND ? groundSurface(pos.x, pos.z) : boxes[floorIndex].surface;
    return res;
  }

  /* --------------------------------------------------------------------------------------- nav */

  // Occupancy grid over the play bounds, rebuilt lazily after the box list or the bounds change.
  let cols = 0;
  let rows = 0;
  let originX = 0;
  let originZ = 0;
  let blocked = new Uint8Array(0); // 1 = not walkable
  let region = new Int32Array(0); // connected area id of a free cell (0 for blocked cells)
  // A* working set, sized to the grid. `seen` / `closed` hold the id of the search that touched the cell.
  let gCost = new Float64Array(0);
  let fCost = new Float64Array(0);
  let parent = new Int32Array(0);
  let seen = new Uint32Array(0);
  let closed = new Uint32Array(0);
  let heap = new Int32Array(0); // binary min-heap of cell indices ordered by fCost
  let heapPos = new Int32Array(0);
  let pathBuf = new Int32Array(0);
  let heapSize = 0;
  let searchId = 0;
  let lastExpansions = 0;
  let rebuilds = 0; // how often the grid has been rebuilt (a number that keeps climbing means a collider is being moved every frame)
  let expansionCap = NAV_MIN_EXPANSIONS;
  const offsets = new Int32Array(8); // index offset of each neighbour direction
  const segment = new Float64Array(4); // the line lineFree() tests: x0, z0, x1, z1 (see `ray` for why)
  const rng = G.rng && typeof G.rng.fork === 'function' ? G.rng.fork('nav') : null;
  const random = rng ? () => rng.next() : Math.random;

  function rebuild() {
    navDirty = false;
    rebuilds++;
    originX = bounds.minX;
    originZ = bounds.minZ;
    cols = Math.max(3, Math.ceil((bounds.maxX - bounds.minX) / NAV_CELL - 1e-9));
    rows = Math.max(3, Math.ceil((bounds.maxZ - bounds.minZ) / NAV_CELL - 1e-9));
    const n = cols * rows;
    if (blocked.length !== n) {
      blocked = new Uint8Array(n);
      region = new Int32Array(n);
      gCost = new Float64Array(n);
      fCost = new Float64Array(n);
      parent = new Int32Array(n);
      seen = new Uint32Array(n);
      closed = new Uint32Array(n);
      heap = new Int32Array(n);
      heapPos = new Int32Array(n);
      pathBuf = new Int32Array(n);
      searchId = 0;
    } else {
      blocked.fill(0);
    }
    for (let d = 0; d < 8; d++) offsets[d] = DIR_Z[d] * cols + DIR_X[d];
    // Unreachable goals never get as far as a search (see the area labels below), so the cap only has
    // to stop pathological cases; half the grid is more than a search across a real level expands.
    expansionCap = Math.max(NAV_MIN_EXPANSIONS, n >> 1);

    // The outer ring is never walkable, which also lets the search skip range checks.
    for (let i = 0; i < cols; i++) blocked[i] = blocked[n - cols + i] = 1;
    for (let j = 0; j < rows; j++) blocked[j * cols] = blocked[j * cols + cols - 1] = 1;

    // A cell is blocked when its centre lies inside an obstacle grown by NAV_INFLATE.
    for (let b = 0; b < boxes.length; b++) {
      const box = boxes[b];
      if (!blocksNav(box)) continue;
      const i0 = Math.max(0, Math.ceil((box.min.x - NAV_INFLATE - originX) / NAV_CELL - 0.5 - 1e-9));
      const i1 = Math.min(cols - 1, Math.floor((box.max.x + NAV_INFLATE - originX) / NAV_CELL - 0.5 + 1e-9));
      const j0 = Math.max(0, Math.ceil((box.min.z - NAV_INFLATE - originZ) / NAV_CELL - 0.5 - 1e-9));
      const j1 = Math.min(rows - 1, Math.floor((box.max.z + NAV_INFLATE - originZ) / NAV_CELL - 0.5 + 1e-9));
      for (let j = j0; j <= j1; j++) blocked.fill(1, j * cols + i0, j * cols + i1 + 1);
    }

    // Label connected areas (4-connectivity: a legal diagonal move never joins two of them), so an
    // unreachable goal is rejected without running a search.
    region.fill(0);
    let id = 0;
    for (let c = 0; c < n; c++) {
      if (blocked[c] || region[c]) continue;
      id++;
      let top = 0;
      pathBuf[top++] = c;
      region[c] = id;
      while (top > 0) {
        const cur = pathBuf[--top];
        for (let d = 0; d < 4; d++) {
          const nb = cur + offsets[d];
          if (blocked[nb] || region[nb]) continue;
          region[nb] = id;
          pathBuf[top++] = nb;
        }
      }
    }
  }

  const ensureNav = () => {
    if (navDirty) rebuild();
  };

  const cellBlocked = (i, j) => i < 0 || j < 0 || i >= cols || j >= rows || blocked[j * cols + i] === 1;
  const centreX = (cell) => originX + ((cell % cols) + 0.5) * NAV_CELL;
  const centreZ = (cell) => originZ + (((cell / cols) | 0) + 0.5) * NAV_CELL;

  /** Cell index under a world point, or -1 outside the grid. */
  function cellAt(x, z) {
    const i = Math.floor((x - originX) / NAV_CELL);
    const j = Math.floor((z - originZ) / NAV_CELL);
    return i < 0 || j < 0 || i >= cols || j >= rows ? -1 : j * cols + i;
  }

  /**
   * Free cell nearest to a world point, searching outward ring by ring; -1 if there is none within
   * maxRings cells (so a point far outside the grid finds nothing).
   * With `inRegion` only cells of that connected area qualify.
   */
  function nearestFree(x, z, maxRings, inRegion) {
    const fx = (x - originX) / NAV_CELL;
    const fz = (z - originZ) / NAV_CELL;
    const ci = clampInt(Math.floor(fx), 0, cols - 1);
    const cj = clampInt(Math.floor(fz), 0, rows - 1);
    const c = cj * cols + ci;
    if (!blocked[c] && (!inRegion || region[c] === inRegion)) return c;
    let best = -1;
    let bestD = Infinity;
    for (let r = 1; r <= maxRings; r++) {
      // No cell of ring r can be closer than r − 0.5 cells.
      if ((r - 0.5) * (r - 0.5) >= bestD) break;
      for (let j = cj - r; j <= cj + r; j++) {
        if (j < 0 || j >= rows) continue;
        const stride = j === cj - r || j === cj + r ? 1 : 2 * r;
        for (let i = ci - r; i <= ci + r; i += stride) {
          if (i < 0 || i >= cols) continue;
          const k = j * cols + i;
          if (blocked[k] || (inRegion && region[k] !== inRegion)) continue;
          const d = (i + 0.5 - fx) * (i + 0.5 - fx) + (j + 0.5 - fz) * (j + 0.5 - fz);
          if (d < bestD) {
            bestD = d;
            best = k;
          }
        }
      }
    }
    return bestD <= (maxRings + 1) * (maxRings + 1) ? best : -1;
  }

  /**
   * Supercover walk: is every cell touched by the segment in `segment` free? A segment through a cell
   * corner needs both cells beside the corner free, matching the search's no-corner-cutting rule.
   */
  function lineFree() {
    const gx = (segment[0] - originX) / NAV_CELL;
    const gz = (segment[1] - originZ) / NAV_CELL;
    const ex = (segment[2] - originX) / NAV_CELL;
    const ez = (segment[3] - originZ) / NAV_CELL;
    let i = Math.floor(gx);
    let j = Math.floor(gz);
    const iEnd = Math.floor(ex);
    const jEnd = Math.floor(ez);
    const dx = ex - gx;
    const dz = ez - gz;
    const si = dx > 0 ? 1 : -1;
    const sj = dz > 0 ? 1 : -1;
    const stepX = dx !== 0 ? Math.abs(1 / dx) : Infinity;
    const stepZ = dz !== 0 ? Math.abs(1 / dz) : Infinity;
    // Segment parameter (0..1) at which the walk next crosses a vertical / horizontal grid line.
    let tx = dx !== 0 ? (dx > 0 ? i + 1 - gx : gx - i) * stepX : Infinity;
    let tz = dz !== 0 ? (dz > 0 ? j + 1 - gz : gz - j) * stepZ : Infinity;
    for (let guard = cols + rows + 4; guard > 0; guard--) {
      if (cellBlocked(i, j)) return false;
      if ((i === iEnd && j === jEnd) || (tx > 1 && tz > 1)) return true;
      if (Math.abs(tx - tz) < 1e-9) {
        if (cellBlocked(i + si, j) || cellBlocked(i, j + sj)) return false;
        i += si;
        j += sj;
        tx += stepX;
        tz += stepZ;
      } else if (tx < tz) {
        i += si;
        tx += stepX;
      } else {
        j += sj;
        tz += stepZ;
      }
    }
    return false;
  }

  /* Indexed binary heap keyed on fCost; equal costs prefer the cell further along (larger gCost). */

  const before = (a, b) => fCost[a] < fCost[b] || (fCost[a] === fCost[b] && gCost[a] > gCost[b]);

  function siftUp(i) {
    const cell = heap[i];
    while (i > 0) {
      const p = (i - 1) >> 1;
      const up = heap[p];
      if (!before(cell, up)) break;
      heap[i] = up;
      heapPos[up] = i;
      i = p;
    }
    heap[i] = cell;
    heapPos[cell] = i;
  }

  function siftDown(i) {
    const cell = heap[i];
    for (;;) {
      let child = 2 * i + 1;
      if (child >= heapSize) break;
      if (child + 1 < heapSize && before(heap[child + 1], heap[child])) child++;
      const down = heap[child];
      if (!before(down, cell)) break;
      heap[i] = down;
      heapPos[down] = i;
      i = child;
    }
    heap[i] = cell;
    heapPos[cell] = i;
  }

  function heapPop() {
    const top = heap[0];
    const last = heap[--heapSize];
    if (heapSize > 0) {
      heap[0] = last;
      siftDown(0);
    }
    return top;
  }

  /**
   * A* between two free cells: 8-connected, no diagonal corner cutting, octile heuristic.
   * Writes the cell path (start first) into pathBuf and returns its length; 0 when the expansion cap
   * is reached or the cells are not connected.
   */
  function search(start, goal) {
    if (++searchId === 0xffffffff) {
      seen.fill(0);
      closed.fill(0);
      searchId = 1;
    }
    const goalX = goal % cols;
    const goalZ = (goal / cols) | 0;
    heapSize = 0;
    gCost[start] = 0;
    fCost[start] = 0;
    parent[start] = -1;
    seen[start] = searchId;
    heap[heapSize++] = start;
    heapPos[start] = 0;
    lastExpansions = 0;

    while (heapSize > 0) {
      const cur = heapPop();
      if (cur === goal) {
        let n = 0;
        for (let c = goal; c !== -1; c = parent[c]) pathBuf[n++] = c;
        for (let i = 0, j = n - 1; i < j; i++, j--) {
          const t = pathBuf[i];
          pathBuf[i] = pathBuf[j];
          pathBuf[j] = t;
        }
        return n;
      }
      closed[cur] = searchId;
      if (++lastExpansions > expansionCap) return 0;
      const cx = cur % cols;
      const cz = (cur / cols) | 0;
      const g = gCost[cur];
      for (let d = 0; d < 8; d++) {
        const nb = cur + offsets[d];
        if (blocked[nb] || closed[nb] === searchId) continue;
        // A diagonal needs both cells it squeezes between to be free.
        if (d >= 4 && (blocked[cur + DIR_X[d]] || blocked[cur + DIR_Z[d] * cols])) continue;
        const ng = g + (d < 4 ? 1 : SQRT2);
        if (seen[nb] === searchId) {
          if (ng >= gCost[nb]) continue;
          fCost[nb] += ng - gCost[nb];
          gCost[nb] = ng;
          parent[nb] = cur;
          siftUp(heapPos[nb]);
        } else {
          const ax = Math.abs(cx + DIR_X[d] - goalX);
          const az = Math.abs(cz + DIR_Z[d] - goalZ);
          seen[nb] = searchId;
          gCost[nb] = ng;
          fCost[nb] = ng + (ax > az ? ax + (SQRT2 - 1) * az : az + (SQRT2 - 1) * ax) * NAV_H_SCALE;
          parent[nb] = cur;
          heap[heapSize] = nb;
          siftUp(heapSize++);
        }
      }
    }
    return 0;
  }

  /** Stores the end point of `segment` as waypoint n of `out`, reusing the vector that is already there. */
  function keepPoint(out, n) {
    const v = out[n] || (out[n] = new THREE.Vector3());
    v.x = segment[2];
    v.y = 0;
    v.z = segment[3];
    return n + 1;
  }

  /**
   * Walkable route from a to b as waypoints (y = 0), or null. The first point is the start, the last
   * the goal; a blocked start or goal is replaced by the nearest free cell (the goal by the nearest one
   * that can actually be reached). Pass `out` to refill an existing array instead of allocating.
   */
  function findPath(a, b, out = []) {
    ensureNav();
    const start = nearestFree(a.x, a.z, NAV_SNAP_RINGS, 0);
    if (start < 0) return null;
    const goal = nearestFree(b.x, b.z, NAV_SNAP_RINGS, region[start]);
    if (goal < 0) return null;
    let len = 1;
    pathBuf[0] = start;
    if (goal !== start) {
      len = search(start, goal);
      if (len === 0) return null;
    }
    const last = len - 1;
    const exactStart = cellAt(a.x, a.z) === start;
    const exactGoal = cellAt(b.x, b.z) === goal;
    const goalX = exactGoal ? b.x : centreX(goal);
    const goalZ = exactGoal ? b.z : centreZ(goal);

    // String pulling: from each kept point jump to the farthest later cell in straight walkable view.
    // The candidate leg lives in `segment` ([0..1] from, [2..3] to), where lineFree() reads it.
    segment[2] = exactStart ? a.x : centreX(start);
    segment[3] = exactStart ? a.z : centreZ(start);
    let n = keepPoint(out, 0);
    let i = 0;
    while (i < last) {
      let j = last;
      segment[0] = segment[2];
      segment[1] = segment[3];
      segment[2] = goalX;
      segment[3] = goalZ;
      while (j > i + 1 && !lineFree()) {
        j--;
        const cell = pathBuf[j];
        segment[2] = originX + ((cell % cols) + 0.5) * NAV_CELL;
        segment[3] = originZ + (((cell / cols) | 0) + 0.5) * NAV_CELL;
      }
      n = keepPoint(out, n);
      i = j;
    }
    if (last === 0) {
      segment[2] = goalX;
      segment[3] = goalZ;
      n = keepPoint(out, n);
    }
    out.length = n;
    return out;
  }

  function isWalkable(x, z) {
    ensureNav();
    const c = cellAt(x, z);
    return c >= 0 && blocked[c] === 0;
  }

  function clearLine(a, b) {
    ensureNav();
    segment[0] = a.x;
    segment[1] = a.z;
    segment[2] = b.x;
    segment[3] = b.z;
    return lineFree();
  }

  /** Random walkable point within `radius` of `center`, in the same connected area; null if unlucky. */
  function randomPoint(center, radius) {
    ensureNav();
    const home = nearestFree(center.x, center.z, NAV_SNAP_RINGS, 0);
    if (home < 0) return null;
    for (let k = 0; k < NAV_RANDOM_TRIES; k++) {
      const angle = random() * Math.PI * 2;
      const r = radius * Math.sqrt(random());
      const x = center.x + Math.cos(angle) * r;
      const z = center.z + Math.sin(angle) * r;
      const c = cellAt(x, z);
      if (c >= 0 && !blocked[c] && region[c] === region[home]) return new THREE.Vector3(x, 0, z);
    }
    return null;
  }

  /** The point itself when walkable, else the centre of the nearest free cell within maxR metres. */
  function nearestWalkable(x, z, maxR = 6) {
    ensureNav();
    const c = cellAt(x, z);
    if (c >= 0 && !blocked[c]) return new THREE.Vector3(x, 0, z);
    const k = nearestFree(x, z, Math.ceil(maxR / NAV_CELL) + 1, 0);
    if (k < 0) return null;
    const px = centreX(k);
    const pz = centreZ(k);
    return (px - x) * (px - x) + (pz - z) * (pz - z) <= maxR * maxR ? new THREE.Vector3(px, 0, pz) : null;
  }

  const nav = {
    cell: NAV_CELL,
    rebuild,
    isWalkable,
    findPath,
    clearLine,
    randomPoint,
    nearestWalkable,
    // Read-only views for debug overlays and tests (they trigger the lazy rebuild).
    get cols() {
      ensureNav();
      return cols;
    },
    get rows() {
      ensureNav();
      return rows;
    },
    get origin() {
      ensureNav();
      return { x: originX, z: originZ };
    },
    get grid() {
      ensureNav();
      return blocked;
    },
    get lastExpansions() {
      return lastExpansions;
    },
    get rebuilds() {
      return rebuilds;
    },
  };

  return {
    boxes,
    bounds,
    addBox,
    addOriented,
    removeBox,
    removeBoxes,
    setBounds,
    raycast,
    lineOfSight,
    moveCapsule,
    groundHeight,
    overlapsCylinder,
    nav,
  };
}
