// The guide line (the `guide` setting, on by default): gold chevrons on the ground along the walkable
// route from Rule to whatever the level wants next, running toward it. Red when it leads to a Vulture.
//
// The route is physics.nav.findPath, asked for a couple of times a second and at once when the target
// changes or Rule leaves it; between searches the chevrons simply flow along the last one. `route` is
// what the minimap draws. Numbers: src/config/flow.js `guide`.

import * as THREE from 'three';

const MAX = 34; // chevrons on screen at once
const STEP = 0.5; // metres between two height samples along the route

/** A chevron lying flat, pointing down −Z: two arms of a V, `w` wide and `l` long. */
function chevronGeometry(w, l) {
  const hw = w / 2;
  const t = l * 0.45; // thickness of an arm along the route
  // Outline, clockwise from the tip: tip, right wing (outer, inner), notch, left wing (inner, outer).
  const p = [
    [0, -l / 2],
    [hw, l / 2 - t],
    [hw, l / 2],
    [0, -l / 2 + t],
    [-hw, l / 2],
    [-hw, l / 2 - t],
  ];
  const index = [0, 3, 1, 1, 3, 2, 0, 5, 3, 5, 4, 3];
  const position = new Float32Array(index.length * 3);
  const normal = new Float32Array(index.length * 3);
  index.forEach((i, n) => {
    position[n * 3] = p[i][0];
    position[n * 3 + 2] = p[i][1];
    normal[n * 3 + 1] = 1;
  });
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(position, 3));
  geometry.setAttribute('normal', new THREE.BufferAttribute(normal, 3));
  return geometry;
}

/**
 * Resamples a polyline (points with x and z) every `step` metres: returns how many samples were written
 * to `out` ([x, z, distance along the route] triples). Pure; exported for the unit test.
 */
export function resample(points, step, limit, out) {
  let n = 0;
  if (!points || points.length === 0) return 0;
  let travelled = 0;
  let carry = 0; // distance into the current leg of the next sample
  out[0] = points[0].x;
  out[1] = points[0].z;
  out[2] = 0;
  n = 1;
  for (let i = 1; i < points.length; i++) {
    const ax = points[i - 1].x;
    const az = points[i - 1].z;
    const dx = points[i].x - ax;
    const dz = points[i].z - az;
    const leg = Math.hypot(dx, dz);
    if (leg < 1e-6) continue;
    let at = step - carry;
    while (at <= leg) {
      if (travelled + at > limit || (n + 1) * 3 > out.length) return n;
      out[n * 3] = ax + (dx * at) / leg;
      out[n * 3 + 1] = az + (dz * at) / leg;
      out[n * 3 + 2] = travelled + at;
      n++;
      at += step;
    }
    carry = leg - (at - step);
    travelled += leg;
  }
  return n;
}

/** Distance from (x, z) to the nearest point of a resampled route (`samples`: [x, z, d] triples). */
export function offRoute(samples, count, x, z) {
  let best = Infinity;
  for (let i = 0; i < count; i++) {
    const d = Math.hypot(samples[i * 3] - x, samples[i * 3 + 1] - z);
    if (d < best) best = d;
  }
  return best;
}

export function createGuide(G) {
  const T = G.config.flow.guide;
  const brand = G.config.brand || {};
  const colors = brand.colors || {};
  const GOLD = new THREE.Color(colors.gold || '#ffd21f');
  const RED = new THREE.Color(colors.red || '#ff3b30');

  /** The route as the minimap draws it: way-points from Rule to the target (empty: nothing to show). */
  const route = [];
  const found = []; // what findPath fills
  const samples = new Float32Array(Math.ceil((T.reach + 8) / STEP) * 3); // [x, z, distance]
  const heights = new Float32Array(samples.length / 3);
  let count = 0; // samples in use
  let length = 0; // metres of route sampled

  const target = new THREE.Vector3();
  let has = false;
  let hunt = false; // the target is a Vulture: the line is red
  let searchIn = 0;
  let flow = 0; // metres the chevrons have run
  let shown = 0;
  let warmed = false;

  // One instanced mesh for the whole line. Unlit and opaque, so it reads the same by day and by night.
  let mesh = null;
  if (G.scene) {
    const material = new THREE.MeshBasicMaterial({ color: GOLD.clone().multiplyScalar(1.25), fog: false });
    material.polygonOffset = true;
    material.polygonOffsetFactor = -2;
    material.polygonOffsetUnits = -2;
    material.name = 'guide-line';
    mesh = new THREE.InstancedMesh(chevronGeometry(T.size[0], T.size[1]), material, MAX);
    mesh.name = 'guide-line';
    mesh.frustumCulled = false;
    mesh.castShadow = false;
    mesh.receiveShadow = false;
    mesh.renderOrder = 1;
    // One chevron far under the street until the first update: the boot's shader warm-up sees it.
    mesh.count = 1;
    mesh.setMatrixAt(0, new THREE.Matrix4().makeTranslation(0, -200, 0));
    G.scene.add(mesh);
  }

  const matrix = new THREE.Matrix4();
  const position = new THREE.Vector3();
  const quaternion = new THREE.Quaternion();
  const scale = new THREE.Vector3();
  const UP = new THREE.Vector3(0, 1, 0);
  const from = new THREE.Vector3();

  const enabled = () => !G.settings || G.settings.get('guide') !== false;

  function hide() {
    if (mesh && shown !== 0) {
      mesh.count = 0;
      shown = 0;
    }
  }

  /** Where the line leads: a point, or null for none. `asHunt` paints it red. */
  function setTarget(point, asHunt = false) {
    if (!point) {
      if (has) {
        has = false;
        route.length = 0;
        count = 0;
        hide();
      }
      return;
    }
    const moved = !has || Math.hypot(point.x - target.x, point.z - target.z) > 1.5;
    target.copy(point);
    if (hunt !== asHunt) {
      hunt = asHunt;
      if (mesh) mesh.material.color.copy(hunt ? RED : GOLD).multiplyScalar(1.25);
    }
    has = true;
    if (moved) searchIn = 0;
  }

  function search(player) {
    const nav = G.physics && G.physics.nav;
    count = 0;
    route.length = 0;
    if (!nav || typeof nav.findPath !== 'function') return;
    from.set(player.pos.x, 0, player.pos.z);
    const path = nav.findPath(from, target, found);
    if (!path || path.length < 2) return;
    for (let i = 0; i < path.length; i++) route.push(path[i]);
    count = resample(path, STEP, T.reach + 6, samples);
    length = count > 0 ? samples[(count - 1) * 3 + 2] : 0;
    // The floor under every sample, followed from Rule's own floor so a deck overhead is never picked.
    let y = player.pos.y;
    for (let i = 0; i < count; i++) {
      y = G.physics.groundHeight(samples[i * 3], samples[i * 3 + 1], y + 0.9);
      heights[i] = y;
    }
  }

  /** Places the chevrons along the sampled route. */
  function place() {
    if (!mesh) return;
    let n = 0;
    // Total route length left (to the target), so the line stops short of it.
    const end = Math.min(T.reach, length - T.stop);
    let d = T.first + (flow % T.spacing);
    for (; d < end && n < MAX; d += T.spacing) {
      const f = d / STEP;
      const i = Math.min(count - 2, Math.floor(f));
      if (i < 0) break;
      const k = f - i;
      const ax = samples[i * 3];
      const az = samples[i * 3 + 1];
      const bx = samples[(i + 1) * 3];
      const bz = samples[(i + 1) * 3 + 1];
      const dx = bx - ax;
      const dz = bz - az;
      if (dx * dx + dz * dz < 1e-8) continue;
      position.set(ax + dx * k, heights[i] + (heights[i + 1] - heights[i]) * k + T.lift, az + dz * k);
      // The chevron's −Z turned to the way the route runs.
      quaternion.setFromAxisAngle(UP, Math.atan2(-dx, -dz));
      // Grows in at the near end, shrinks away over the last metres.
      const size = Math.min(1, (d - T.first + 0.6) / 1.4, (end - d) / T.fade + 0.25);
      scale.setScalar(Math.max(0.05, size));
      matrix.compose(position, quaternion, scale);
      mesh.setMatrixAt(n++, matrix);
    }
    mesh.count = n;
    shown = n;
    mesh.instanceMatrix.needsUpdate = true;
  }

  /** `show` is false whenever the line has no business on screen (cutscene, death card, the title). */
  function update(dt, show = true) {
    if (!warmed) {
      warmed = true;
      hide();
    }
    const player = G.player;
    if (!show || !has || !enabled() || !player || !player.pos || player.alive === false) {
      route.length = 0;
      hide();
      searchIn = 0;
      return;
    }
    flow += T.speed * dt;
    searchIn -= dt;
    if (searchIn <= 0 || (count > 0 && offRoute(samples, Math.min(count, 12), player.pos.x, player.pos.z) > T.offRoute)) {
      searchIn = T.every;
      search(player);
    }
    if (count < 2) {
      hide();
      return;
    }
    place();
  }

  return {
    route,
    setTarget,
    update,
    get target() {
      return has ? target : null;
    },
    get hunting() {
      return hunt;
    },
    get shown() {
      return shown;
    },
  };
}
