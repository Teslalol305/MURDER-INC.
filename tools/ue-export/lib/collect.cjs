'use strict';

// Page-side collectors for the Unreal data export. Every function here is serialised by Playwright and
// runs inside the booted game page (page.evaluate), so none of them can close over anything in this
// file: they share code through window.__ue.h, which `installHelpers` puts there first.
//
// Everything is returned in web space (metres, radians, +Y up, north = −Z) as plain JSON; the Node side
// (export.cjs) adds the Unreal-space twins, rounds and writes.

/** Shared helpers, stored on window.__ue.h. */
function installHelpers() {
  const rec = window.__ue;
  const G = window.__G;
  const T = G.THREE;

  /** JSON has no Infinity: non-finite numbers travel as strings. */
  const num = (n) => (Number.isFinite(n) ? n : n === Infinity ? 'Infinity' : n === -Infinity ? '-Infinity' : 'NaN');
  const v3 = (v) => ({ x: v.x, y: v.y, z: v.z });

  /**
   * Plain copy of tuning data: functions become {$fn, arity} (the Node side adds their source text and
   * samples), non-finite numbers become strings, scene objects are dropped.
   */
  function plain(value, depth = 0) {
    if (value === null || value === undefined) return null;
    const type = typeof value;
    if (type === 'number') return num(value);
    if (type === 'string' || type === 'boolean') return value;
    if (type === 'function') return { $fn: value.name || '', arity: value.length };
    if (type !== 'object' || depth > 20) return null;
    if (Array.isArray(value)) return value.map((v) => plain(v, depth + 1));
    if (ArrayBuffer.isView(value)) return Array.from(value, num);
    if (value.isVector3) return v3(value);
    if (value.isVector2) return { x: value.x, y: value.y };
    if (value.isColor) return value.getHex();
    if (value.isObject3D || value.isMaterial || value.isTexture || value.isBufferGeometry) return null;
    const out = {};
    for (const key of Object.keys(value)) {
      if (value[key] === undefined) continue;
      out[key] = plain(value[key], depth + 1);
    }
    return out;
  }

  /** The props the level placed, in placement order (everything built while the level was being made). */
  const placed = () => rec.builds.filter((b) => b.by === 'level');

  const scratch = new T.Color();
  /** sRGB hex of a linear colour triple (what a vertex-tinted paint carries). */
  const hexOfLinear = (r, g, b) => scratch.setRGB(r, g, b).getHex();

  /** Meshes of a prop that are part of the model (the level's shadow hulls are not). */
  function modelMeshes(object) {
    const out = [];
    object.traverse((m) => {
      if (m.isMesh && m.geometry && m.name !== 'shadow-hull') out.push(m);
    });
    return out;
  }

  /** Paint colour of a built prop (sRGB hex), or null when it has no paint slot. */
  function paintOf(prop) {
    let hex = null;
    prop.object.traverse((m) => {
      if (hex !== null || !m.isMesh || m.name !== '@paint') return;
      const color = m.geometry.getAttribute('color');
      if (color && m.material && m.material.vertexColors) hex = hexOfLinear(color.getX(0), color.getY(0), color.getZ(0));
      else if (m.material && m.material.color) hex = m.material.color.getHex();
    });
    return hex;
  }

  /** Is the dome light on (a parked car's lit glass)? null when the prop has no such glass. */
  function domeOf(prop) {
    let lit = null;
    prop.object.traverse((m) => {
      if (m.isMesh && m.name === '@glass' && m.material) lit = m.material.name === 'glass_car_lit';
    });
    return lit;
  }

  const inverse = new T.Matrix4();
  const relative = new T.Matrix4();
  const box = new T.Box3();
  const part = new T.Box3();

  /** Bounds of the model in the prop's own frame (overhangs included), whatever transform it carries. */
  function localBounds(prop) {
    const object = prop.object;
    object.updateMatrixWorld(true);
    inverse.copy(object.matrixWorld).invert();
    box.makeEmpty();
    for (const mesh of modelMeshes(object)) {
      if (!mesh.geometry.boundingBox) mesh.geometry.computeBoundingBox();
      relative.multiplyMatrices(inverse, mesh.matrixWorld);
      box.union(part.copy(mesh.geometry.boundingBox).applyMatrix4(relative));
    }
    return box.isEmpty() ? null : { min: v3(box.min), max: v3(box.max) };
  }

  /**
   * A short hash of a prop's geometry: mesh slots, vertex counts and bounds in its own frame. Two props
   * with the same hash look the same apart from paint and the small graphics drawn on them.
   */
  function shapeOf(prop) {
    const object = prop.object;
    object.updateMatrixWorld(true);
    inverse.copy(object.matrixWorld).invert();
    const parts = [];
    for (const mesh of modelMeshes(object)) {
      const geo = mesh.geometry;
      if (!geo.boundingBox) geo.computeBoundingBox();
      relative.multiplyMatrices(inverse, mesh.matrixWorld);
      part.copy(geo.boundingBox).applyMatrix4(relative);
      const r = (n) => Math.round(n * 1000);
      parts.push(`${mesh.name}:${geo.getAttribute('position').count}:${r(part.min.x)},${r(part.min.y)},${r(part.min.z)},${r(part.max.x)},${r(part.max.y)},${r(part.max.z)}`);
    }
    parts.sort();
    let hash = 0x811c9dc5;
    const text = parts.join('|');
    for (let i = 0; i < text.length; i++) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 0x01000193);
    }
    return (hash >>> 0).toString(16).padStart(8, '0');
  }

  /**
   * Which of the factory's cached shapes a prop was made from. The factory builds each shape once and
   * every instance shares its geometries (src/props.js protoFor), so the geometry objects themselves
   * say it; only the paint is copied per colour, so that slot is left out.
   */
  function protoOf(prop) {
    const ids = [];
    for (const mesh of modelMeshes(prop.object)) if (mesh.name !== '@paint') ids.push(`${mesh.name}=${mesh.geometry.uuid}`);
    ids.sort();
    return ids.length ? ids.join(',') : `shape=${shapeOf(prop)}`;
  }

  /** What a built prop says about its type: colliders, bounds, lamp hints, anchors, moving parts. */
  function describeProp(prop) {
    return {
      size: prop.size ? prop.size.slice() : null,
      surface: prop.surface || null,
      dynamic: !!prop.dynamic,
      fallback: !!prop.fallback,
      stateful: typeof prop.setState === 'function',
      animated: typeof prop.update === 'function',
      triangles: prop.object.userData.triangles ?? null,
      shape: shapeOf(prop),
      slots: [...new Set(modelMeshes(prop.object).map((m) => m.name))].sort(),
      bounds: localBounds(prop),
      colliders: (prop.colliders || []).map((c) => ({
        min: { x: c.min[0], y: c.min[1], z: c.min[2] },
        max: { x: c.max[0], y: c.max[1], z: c.max[2] },
        surface: c.surface || prop.surface || null,
        bulletOnly: !!c.bulletOnly,
        playerOnly: !!c.playerOnly,
        noNav: !!c.noNav,
      })),
      lights: (prop.lights || []).map((l) => ({
        pos: { x: l.pos[0], y: l.pos[1], z: l.pos[2] },
        dir: l.dir ? { x: l.dir[0], y: l.dir[1], z: l.dir[2] } : null,
        kind: l.kind || 'street',
        color: l.color ?? null,
        intensity: l.intensity ?? null,
        range: l.range ?? null,
      })),
      anchors: Object.fromEntries(
        Object.entries(prop.anchors || {}).map(([id, a]) => [id, { pos: { x: a.pos[0], y: a.pos[1], z: a.pos[2] }, dir: { x: a.dir[0], y: a.dir[1], z: a.dir[2] } }]),
      ),
      nodes: Object.keys(prop.nodes || {}),
      state: prop.state ?? null,
    };
  }

  /**
   * Splits a rectangle of the block into axis-aligned rectangles on which `valueAt(x, z)` is constant,
   * sampling cell centres on a `step` grid (greedy: widest run first, then as many rows as match).
   */
  function rectsOf(bounds, step, valueAt) {
    const cols = Math.round((bounds.maxX - bounds.minX) / step);
    const rows = Math.round((bounds.maxZ - bounds.minZ) / step);
    const values = [];
    const grid = new Int32Array(cols * rows);
    for (let j = 0; j < rows; j++) {
      for (let i = 0; i < cols; i++) {
        const value = valueAt(bounds.minX + (i + 0.5) * step, bounds.minZ + (j + 0.5) * step);
        let id = values.indexOf(value);
        if (id < 0) id = values.push(value) - 1;
        grid[j * cols + i] = id;
      }
    }
    const done = new Uint8Array(cols * rows);
    const out = [];
    for (let j = 0; j < rows; j++) {
      for (let i = 0; i < cols; i++) {
        if (done[j * cols + i]) continue;
        const id = grid[j * cols + i];
        let i1 = i;
        while (i1 + 1 < cols && !done[j * cols + i1 + 1] && grid[j * cols + i1 + 1] === id) i1++;
        let j1 = j;
        for (;;) {
          if (j1 + 1 >= rows) break;
          let same = true;
          for (let k = i; k <= i1 && same; k++) same = !done[(j1 + 1) * cols + k] && grid[(j1 + 1) * cols + k] === id;
          if (!same) break;
          j1++;
        }
        for (let b = j; b <= j1; b++) done.fill(1, b * cols + i, b * cols + i1 + 1);
        out.push({
          value: values[id],
          minX: bounds.minX + i * step,
          maxX: bounds.minX + (i1 + 1) * step,
          minZ: bounds.minZ + j * step,
          maxZ: bounds.minZ + (j1 + 1) * step,
        });
      }
    }
    return out;
  }

  const pa = new T.Vector3();
  const pb = new T.Vector3();
  const pc = new T.Vector3();
  const pd = new T.Vector3();
  const eu = new T.Vector3();
  const ev = new T.Vector3();
  const nn = new T.Vector3();

  /**
   * The flat four-cornered faces of a mesh, in world space. The level builds every sign, pane and wall
   * face as one plane and the static merge keeps planes whole (four vertices, two triangles), so the
   * merged meshes still say where each one is. A face comes back as
   *   {pos, right, up, normal, w, h, u0, u1, v0, v1}
   * `right` and `up` are the directions in which its texture coordinates u and v grow (so `right` is the
   * reading direction of a sign), `normal` = right × up is the side it shows.
   * `corner(u, v)` may be given to say which texture corner counts as bottom-left (a flipped atlas rect).
   */
  function quadsOf(mesh, visit) {
    const position = mesh.geometry.getAttribute('position');
    const uv = mesh.geometry.getAttribute('uv');
    const index = mesh.geometry.index;
    if (!position || !uv || !index) return;
    mesh.updateMatrixWorld(true);
    const tri = (t, k) => index.getX(t * 3 + k);
    const triangles = index.count / 3;
    for (let t = 0; t + 1 < triangles; ) {
      const ids = new Set([tri(t, 0), tri(t, 1), tri(t, 2), tri(t + 1, 0), tri(t + 1, 1), tri(t + 1, 2)]);
      if (ids.size !== 4) {
        t += 1;
        continue;
      }
      t += 2;
      const corner = [...ids];
      let u0 = Infinity;
      let u1 = -Infinity;
      let v0 = Infinity;
      let v1 = -Infinity;
      for (const id of corner) {
        u0 = Math.min(u0, uv.getX(id));
        u1 = Math.max(u1, uv.getX(id));
        v0 = Math.min(v0, uv.getY(id));
        v1 = Math.max(v1, uv.getY(id));
      }
      if (!(u1 - u0 > 1e-9) || !(v1 - v0 > 1e-9)) continue;
      const pick = (u, v) =>
        corner.reduce((best, id) => {
          const e = Math.abs(uv.getX(id) - u) / (u1 - u0) + Math.abs(uv.getY(id) - v) / (v1 - v0);
          return best === null || e < best.e ? { id, e } : best;
        }, null).id;
      pa.fromBufferAttribute(position, pick(u0, v0)).applyMatrix4(mesh.matrixWorld);
      pb.fromBufferAttribute(position, pick(u1, v0)).applyMatrix4(mesh.matrixWorld);
      pc.fromBufferAttribute(position, pick(u0, v1)).applyMatrix4(mesh.matrixWorld);
      pd.fromBufferAttribute(position, pick(u1, v1)).applyMatrix4(mesh.matrixWorld);
      eu.subVectors(pb, pa);
      ev.subVectors(pc, pa);
      const w = eu.length();
      const h = ev.length();
      if (!(w > 1e-6) || !(h > 1e-6)) continue;
      nn.crossVectors(eu, ev).normalize();
      visit({
        pos: { x: (pa.x + pb.x + pc.x + pd.x) / 4, y: (pa.y + pb.y + pc.y + pd.y) / 4, z: (pa.z + pb.z + pc.z + pd.z) / 4 },
        right: { x: eu.x / w, y: eu.y / w, z: eu.z / w },
        up: { x: ev.x / h, y: ev.y / h, z: ev.z / h },
        normal: v3(nn),
        w,
        h,
        u0,
        u1,
        v0,
        v1,
      });
    }
  }

  rec.h = { num, v3, plain, placed, paintOf, domeOf, localBounds, shapeOf, protoOf, describeProp, rectsOf, modelMeshes, quadsOf };
  return true;
}

// -------------------------------------------------------------------------------------------------
// The run itself, and tuning
// -------------------------------------------------------------------------------------------------

/** What was booted: seed, build, errors, the static strings of the page. */
function collectMeta() {
  const rec = window.__ue;
  const G = window.__G;
  const { plain } = rec.h;
  const text = (selector) => {
    const el = document.querySelector(selector);
    return el ? el.textContent.replace(/\s+/g, ' ').trim() : null;
  };
  const view = document.getElementById('view');
  const stats = window.__stats();
  return {
    seed: G.rng.seed,
    params: { ...G.params },
    build: plain(G.build),
    order: rec.order.slice(),
    state: G.game.state,
    mode: G.game.mode,
    difficulty: G.game.difficulty,
    time: G.atmos.time,
    quality: plain(G.quality),
    stubbed: stats.stubbed,
    errors: (window.__errors || []).slice(),
    fatal: window.__fatal || null,
    three: G.THREE.REVISION,
    page: {
      title: document.title,
      bootPresenter: [text('#boot .boot-kicker .ipx-mark'), text('#boot .boot-kicker span:last-child')],
      bootMark: text('#boot .boot-mark'),
      bootStar: text('#boot .boot-star'),
      bootNote: text('#boot .boot-note'),
      canvasLabel: view ? view.getAttribute('aria-label') : null,
    },
  };
}

/** G.config as the game holds it, the default settings, and the tables the modules derive from them. */
function collectConfig() {
  const rec = window.__ue;
  const G = window.__G;
  const { plain } = rec.h;

  // Explosive rules live in src/explosives.js; every placed item carries its row (`item.kind`).
  const kinds = {};
  for (const item of G.explosives.items) if (item.kind && !kinds[item.type]) kinds[item.type] = plain(item.kind);

  // Enemy tuning as the module resolves it for each difficulty (base values + that difficulty's overlay).
  const resolved = {};
  const debug = typeof G.enemies.debug === 'function' ? G.enemies.debug() : null;
  if (debug && debug.tune) {
    for (const name of Object.keys(G.config.enemies.difficulty)) {
      G.enemies.setDifficulty(G.config.enemies.difficulty[name]);
      resolved[name] = plain(G.enemies.debug().tune);
    }
    const current = G.config.enemies.difficulty[G.game.difficulty] || G.config.enemies.difficulty[G.config.flow.defaultDifficulty];
    G.enemies.setDifficulty(current);
  }

  return {
    config: plain(G.config),
    settings: plain(G.settings.all()),
    explosiveKinds: kinds,
    enemiesResolved: resolved,
  };
}

/**
 * Calls config functions in the page: [{path: ['flow', 'holdout', 'total'], calls: [[1], [2]]}] →
 * [[value, value]]. A call that throws answers {$error}; a path that is no function answers null.
 */
function callConfigFunctions(requests) {
  const G = window.__G;
  const { plain } = window.__ue.h;
  return requests.map(({ path, calls }) => {
    let fn = G.config;
    let self = null;
    for (const key of path) {
      self = fn;
      fn = fn == null ? undefined : fn[key];
    }
    if (typeof fn !== 'function') return null;
    return calls.map((args) => {
      try {
        return plain(fn.apply(self, args));
      } catch (err) {
        return { $error: String((err && err.message) || err) };
      }
    });
  });
}

// -------------------------------------------------------------------------------------------------
// The level
// -------------------------------------------------------------------------------------------------

function collectLevel() {
  const rec = window.__ue;
  const G = window.__G;
  const { plain, v3, placed, rectsOf } = rec.h;
  const L = G.level;
  const P = G.physics;
  const nav = P.nav;

  const placement = new Map(placed().map((b, i) => [b.prop, i]));
  const items = G.explosives.items;
  const itemIndex = new Map(items.map((item, i) => [item, i]));
  const orientedIndex = new Map(rec.oriented.map((o, i) => [o, i]));
  const boxIndex = new Map(P.boxes.map((b, i) => [b, i]));

  const colliders = P.boxes.map((b) => {
    const info = rec.boxes.get(b) || { by: null, oriented: null };
    return {
      min: v3(b.min),
      max: v3(b.max),
      surface: b.surface,
      tag: b.tag === undefined ? null : b.tag,
      noNav: !!b.noNav,
      bulletOnly: !!b.bulletOnly,
      playerOnly: !!b.playerOnly,
      prop: placement.has(b.owner) ? placement.get(b.owner) : null,
      explosive: itemIndex.has(b.owner) ? itemIndex.get(b.owner) : null,
      oriented: info.oriented ? orientedIndex.get(info.oriented) : null,
      by: info.by,
    };
  });

  const oriented = rec.oriented.map((o) => ({
    center: { x: o.center[0], y: o.center[1], z: o.center[2] },
    size: { x: o.size[0], y: o.size[1], z: o.size[2] },
    yaw: o.yaw,
    by: o.by,
    boxes: o.boxes.map((b) => (boxIndex.has(b) ? boxIndex.get(b) : null)),
  }));

  // The nav grid as the game built it: one string per row (z), one character per cell (x).
  const grid = nav.grid;
  const cols = nav.cols;
  const rows = nav.rows;
  const navRows = [];
  let free = 0;
  for (let j = 0; j < rows; j++) {
    let line = '';
    for (let i = 0; i < cols; i++) {
      const blocked = grid[j * cols + i] === 1;
      if (!blocked) free++;
      line += blocked ? '#' : '.';
    }
    navRows.push(line);
  }

  // The game keeps no facing for a spawn point (a new enemy gets a random yaw). For the port each point
  // gets one anyway: a ground point looks toward the walkable cells it can reach in a straight line (out
  // of its pocket), an air point toward the middle of the block.
  const centre = { x: (L.bounds.minX + L.bounds.maxX) / 2, z: (L.bounds.minZ + L.bounds.maxZ) / 2 };
  const origin = nav.origin;
  const cell = nav.cell;
  const from = new G.THREE.Vector3();
  const to = new G.THREE.Vector3();
  function opening(p, radius) {
    let sx = 0;
    let sz = 0;
    let n = 0;
    const i0 = Math.max(0, Math.floor((p.x - radius - origin.x) / cell));
    const i1 = Math.min(cols - 1, Math.ceil((p.x + radius - origin.x) / cell));
    const j0 = Math.max(0, Math.floor((p.z - radius - origin.z) / cell));
    const j1 = Math.min(rows - 1, Math.ceil((p.z + radius - origin.z) / cell));
    from.set(p.x, 0, p.z);
    for (let j = j0; j <= j1; j++) {
      for (let i = i0; i <= i1; i++) {
        if (grid[j * cols + i] === 1) continue;
        const x = origin.x + (i + 0.5) * cell;
        const z = origin.z + (j + 0.5) * cell;
        const d = Math.hypot(x - p.x, z - p.z);
        if (d > radius || d < 0.3) continue;
        if (!nav.clearLine(from, to.set(x, 0, z))) continue;
        sx += x - p.x;
        sz += z - p.z;
        n++;
      }
    }
    return n ? { x: sx / n, z: sz / n, cells: n } : { x: 0, z: 0, cells: 0 };
  }
  const SPAWN_REACH = 6;
  const spawns = L.enemySpawns.map((s) => {
    let dx = centre.x - s.pos.x;
    let dz = centre.z - s.pos.z;
    let source = 'centre';
    if (s.type !== 'air') {
      const open = opening(s.pos, SPAWN_REACH);
      if (Math.hypot(open.x, open.z) > 0.25) {
        dx = open.x;
        dz = open.z;
        source = 'opening';
      }
    }
    const length = Math.hypot(dx, dz) || 1;
    return {
      type: s.type,
      zone: s.zone,
      pos: v3(s.pos),
      place: L.zoneName(s.pos.x, s.pos.z),
      walkable: s.type === 'air' ? null : nav.isWalkable(s.pos.x, s.pos.z),
      interior: L.interiorAt(s.pos),
      facing: { x: dx / length, y: 0, z: dz / length },
      facingSource: source,
    };
  });

  const debug = typeof G.enemies.debug === 'function' ? G.enemies.debug() : null;

  // Regions of constant answer of the level's own queries, sampled on a 0.1 m grid (every edge of the
  // layout lies on it).
  const STEP = 0.1;
  const places = rectsOf(L.bounds, STEP, (x, z) => L.zoneName(x, z));
  const zoneRects = rectsOf(L.bounds, STEP, (x, z) => L.zoneAt(x, z));
  const surfaces = rectsOf(L.bounds, STEP, (x, z) => L.groundSurfaceAt(x, z));
  const floors = rectsOf(L.bounds, STEP, (x, z) => L.floorAt(x, z));

  // How far outside an interior box interiorAt() still answers: probe the live function. It falls
  // linearly from 1 at the wall to 0 at the fade distance.
  let interiorFade = null;
  if (L.interiorBoxes.length) {
    const b = L.interiorBoxes[0];
    const probe = new G.THREE.Vector3(b.max.x + 0.5, (b.min.y + b.max.y) / 2, (b.min.z + b.max.z) / 2);
    const at = L.interiorAt(probe);
    if (at > 0 && at < 1) interiorFade = 0.5 / (1 - at);
  }

  return {
    bounds: plain(L.bounds),
    physicsBounds: plain(P.bounds),
    playerStart: { pos: v3(L.playerStart.pos), yaw: L.playerStart.yaw },
    objectives: L.objectives.map((o) => ({
      id: o.id,
      code: o.code,
      label: o.label,
      zone: o.zone,
      place: L.zoneName(o.pos.x, o.pos.z),
      pos: v3(o.pos),
      yaw: o.prop && o.prop.object ? o.prop.object.rotation.y : 0,
      prop: placement.has(o.prop) ? placement.get(o.prop) : null,
      interior: L.interiorAt(o.pos),
    })),
    extraction: {
      pos: v3(L.extraction.pos),
      radius: L.extraction.radius,
      label: L.extraction.label,
      code: L.extraction.code,
      zone: L.zoneAt(L.extraction.pos.x, L.extraction.pos.z),
      place: L.zoneName(L.extraction.pos.x, L.extraction.pos.z),
      prop: placement.has(L.extraction.prop) ? placement.get(L.extraction.prop) : null,
      truck: L.extraction.prop && L.extraction.prop.object
        ? { pos: v3(L.extraction.prop.object.position), yaw: L.extraction.prop.object.rotation.y }
        : null,
    },
    zones: L.zones.map((z) => plain(z)),
    places,
    zoneRects,
    surfaces,
    floors,
    spawns,
    spawnReach: SPAWN_REACH,
    coverPoints: L.coverPoints.map((c) => ({
      zone: c.zone,
      place: L.zoneName(c.pos.x, c.pos.z),
      pos: v3(c.pos),
      walkable: nav.isWalkable(c.pos.x, c.pos.z),
      interior: L.interiorAt(c.pos),
    })),
    cinematicPath: L.cinematicPath.map((p) => ({ pos: v3(p.pos), look: v3(p.look) })),
    explosives: L.explosives.map((e, i) => {
      const item = items[i];
      const same = item && item.type === e.type && item.pos.distanceTo(e.pos) < 1e-6;
      return {
        type: e.type,
        pos: v3(e.pos),
        yaw: e.yaw || 0,
        zone: L.zoneAt(e.pos.x, e.pos.z),
        place: L.zoneName(e.pos.x, e.pos.z),
        interior: L.interiorAt(e.pos),
        item: same
          ? {
              hp: item.hp,
              state: item.state,
              yaw: item.yaw ?? null,
              prop: item.kind ? item.kind.prop : null,
              collider: item.box && boxIndex.has(item.box) ? boxIndex.get(item.box) : null,
            }
          : null,
      };
    }),
    explosiveItems: items.length,
    interiorBoxes: L.interiorBoxes.map((b) => ({ min: v3(b.min), max: v3(b.max) })),
    interiorFade,
    doorways: debug && debug.doorways ? plain(debug.doorways) : null,
    vantage: L.vantage ? { stairsFoot: v3(L.vantage.stairsFoot), deck: v3(L.vantage.deck) } : null,
    el: plain(L.el),
    steam: L.steam.map(v3),
    puddles: plain(L.puddles),
    stats: plain(L.stats),
    colliders,
    oriented,
    nav: {
      cell: nav.cell,
      cols,
      rows,
      origin: { x: origin.x, z: origin.z },
      free,
      blocked: cols * rows - free,
      grid: navRows,
    },
    propsStats: typeof G.props.stats === 'function' ? plain(G.props.stats()) : null,
  };
}

// -------------------------------------------------------------------------------------------------
// Props
// -------------------------------------------------------------------------------------------------

/** Every prop the level placed, with what the factory made of it. */
function collectProps() {
  const rec = window.__ue;
  const G = window.__G;
  const { plain, v3, placed, paintOf, domeOf, shapeOf, protoOf, describeProp } = rec.h;
  const L = G.level;
  const boxIndex = new Map(G.physics.boxes.map((b, i) => [b, i]));

  // Which level lamps came from a prop's own lamp hints (same arithmetic as the level's kit.place).
  const lampOwner = new Map();
  const list = placed();
  list.forEach((b, index) => {
    const o = b.prop.object;
    const sin = Math.sin(o.rotation.y);
    const cos = Math.cos(o.rotation.y);
    for (const hint of b.prop.lights || []) {
      const [hx, hy, hz] = hint.pos;
      const x = o.position.x + hx * cos + hz * sin;
      const y = o.position.y + hy;
      const z = o.position.z - hx * sin + hz * cos;
      L.lamps.forEach((lamp, i) => {
        if (!lampOwner.has(i) && Math.abs(lamp.pos.x - x) < 1e-6 && Math.abs(lamp.pos.y - y) < 1e-6 && Math.abs(lamp.pos.z - z) < 1e-6) lampOwner.set(i, index);
      });
    }
  });

  const described = {}; // name → proto id → description
  const describe = (b) => {
    const proto = protoOf(b.prop);
    if (!described[b.name]) described[b.name] = {};
    if (!described[b.name][proto]) described[b.name][proto] = describeProp(b.prop);
    return proto;
  };

  const instances = list.map((b, index) => {
    const o = b.prop.object;
    const proto = describe(b);
    return {
      name: b.name,
      opts: plain(b.opts),
      seed: b.seed,
      seedGiven: b.seedGiven,
      pos: v3(o.position),
      rotation: { x: o.rotation.x, y: o.rotation.y, z: o.rotation.z },
      scale: v3(o.scale),
      zone: L.zoneAt(o.position.x, o.position.z),
      place: L.zoneName(o.position.x, o.position.z),
      interior: L.interiorAt(o.position),
      dynamic: !!b.prop.dynamic,
      fallback: !!b.prop.fallback,
      paint: paintOf(b.prop),
      dome: domeOf(b.prop),
      shape: shapeOf(b.prop),
      proto,
      colliders: (b.prop.boxes || []).map((box) => (boxIndex.has(box) ? boxIndex.get(box) : null)),
      lamps: [...lampOwner.entries()].filter(([, owner]) => owner === index).map(([lamp]) => lamp),
      state: b.prop.state ?? null,
      inScene: (() => {
        // A static prop is merged into the level's meshes and its own object is emptied or detached.
        let top = o;
        while (top.parent) top = top.parent;
        return top === G.scene;
      })(),
    };
  });

  // What other modules built after the level (the explosives' two templates).
  const others = rec.builds.filter((b) => b.by !== 'level').map((b) => ({ name: b.name, opts: plain(b.opts), seed: b.seed, by: b.by, proto: describe(b), shape: shapeOf(b.prop), paint: paintOf(b.prop) }));

  return { instances, others, described, lampOwners: [...lampOwner.entries()] };
}

/**
 * Builds every catalogue prop a few times over to find out what the factory varies: how many shapes a
 * seed can pick, which paints it draws from, what each shape collides with. `requests` is
 * [{name, opts}] (the default build of every type plus every option set the level used); the answer is
 * one entry per request. Run this last: it builds props that are thrown away.
 */
function probeCatalog({ requests, seeds }) {
  const rec = window.__ue;
  const G = window.__G;
  const { paintOf, domeOf, shapeOf, protoOf, describeProp } = rec.h;
  return requests.map(({ name, opts }) => {
    const protos = []; // by seed
    const shapes = [];
    const paints = [];
    const domes = [];
    const described = {};
    let error = null;
    for (let seed = 0; seed < seeds; seed++) {
      try {
        const prop = G.props.build(name, { ...opts, seed });
        const proto = protoOf(prop);
        protos.push(proto);
        shapes.push(shapeOf(prop));
        paints.push(paintOf(prop));
        domes.push(domeOf(prop));
        if (!described[proto]) described[proto] = describeProp(prop);
      } catch (err) {
        error = String((err && err.message) || err);
        break;
      }
    }
    return { name, opts, protos, shapes, paints, domes, described, error };
  });
}

// -------------------------------------------------------------------------------------------------
// Signs, posters, graffiti and decals; glass; facades
// -------------------------------------------------------------------------------------------------

/**
 * Where every painting ended up. The level maps each one onto a single quad whose UVs are the
 * painting's rectangle on its atlas page (CONTRACT 11.2), so a quad of a page material whose UVs are
 * that rectangle is that painting.
 */
function collectSignage() {
  const rec = window.__ue;
  const G = window.__G;
  const { plain, quadsOf } = rec.h;
  const L = G.level;

  // Paintings by material: a painting asked for twice is one entry.
  const byMaterial = new Map();
  const seen = new Map();
  const paintings = [];
  for (const p of rec.paintings) {
    if (!p.out || !p.out.material) continue;
    const uv = p.out.uv ? p.out.uv.slice() : null;
    const key = `${p.out.material.uuid}|${uv ? uv.map((n) => Math.round(n * 1e6)).join(',') : 'tile'}|${p.kind}`;
    if (seen.has(key)) {
      const entry = seen.get(key);
      if (!entry.by.includes(p.by)) entry.by.push(p.by);
      continue;
    }
    const map = p.out.material.map;
    const entry = {
      kind: p.kind,
      args: plain(p.args),
      w: p.out.w,
      h: p.out.h,
      uv,
      tiles: !uv,
      material: p.out.material.name || null,
      by: [p.by],
      repeat: !uv && map ? { x: map.repeat.x, y: map.repeat.y } : null,
      placed: 0,
    };
    seen.set(key, entry);
    paintings.push(entry);
    if (!byMaterial.has(p.out.material)) byMaterial.set(p.out.material, []);
    byMaterial.get(p.out.material).push(entry);
  }

  const quads = [];
  let unmatched = 0;
  L.root.updateMatrixWorld(true);
  L.root.traverse((mesh) => {
    if (!mesh.isMesh || !byMaterial.has(mesh.material)) return;
    const candidates = byMaterial.get(mesh.material);
    quadsOf(mesh, (q) => {
      // Which painting: the one whose atlas rectangle these UVs are (tiling road paint has none).
      let match = null;
      for (const p of candidates) {
        if (!p.uv) {
          if (!match) match = p;
          continue;
        }
        const [a0, b0, a1, b1] = p.uv;
        if (Math.abs(q.u0 - Math.min(a0, a1)) < 2e-4 && Math.abs(q.u1 - Math.max(a0, a1)) < 2e-4 && Math.abs(q.v0 - Math.min(b0, b1)) < 2e-4 && Math.abs(q.v1 - Math.max(b0, b1)) < 2e-4) {
          match = p;
          break;
        }
      }
      if (!match) {
        unmatched++;
        return;
      }
      // An atlas rectangle given right-to-left or top-to-bottom turns the picture: follow it.
      const flipU = match.uv ? match.uv[2] < match.uv[0] : false;
      const flipV = match.uv ? match.uv[3] < match.uv[1] : false;
      const right = flipU ? { x: -q.right.x, y: -q.right.y, z: -q.right.z } : q.right;
      const up = flipV ? { x: -q.up.x, y: -q.up.y, z: -q.up.z } : q.up;
      const normal = flipU !== flipV ? { x: -q.normal.x, y: -q.normal.y, z: -q.normal.z } : q.normal;
      match.placed++;
      quads.push({
        painting: paintings.indexOf(match),
        pos: q.pos,
        normal,
        right,
        up,
        w: q.w,
        h: q.h,
        zone: L.zoneAt(q.pos.x, q.pos.z),
        place: L.zoneName(q.pos.x, q.pos.z),
        interior: L.interiorAt(q.pos),
        dynamic: !mesh.name.startsWith('merged:'),
      });
    });
  });

  return { paintings, quads, unmatched };
}

/**
 * Flat faces of the level's glass and of its window facades.
 *   panes    every four-cornered face drawn with one of the catalogue's glass materials
 *   facades  every wall face that carries a painted window grid (mats.facade): where it is and which
 *            part of the repeating grid it shows (u along the wall, v up, in metres)
 */
function collectGlass() {
  const rec = window.__ue;
  const G = window.__G;
  const { plain, quadsOf } = rec.h;
  const L = G.level;
  const GLASS = ['glass_dark', 'glass_store', 'glass_lit_warm', 'glass_lit_cool', 'glass_skylight', 'glass_car', 'glass_car_lit'];
  const panes = [];
  const faces = [];
  L.root.updateMatrixWorld(true);
  L.root.traverse((mesh) => {
    if (!mesh.isMesh || !mesh.material || Array.isArray(mesh.material)) return;
    const material = mesh.material;
    const grid = material.userData && material.userData.facade;
    if (grid) {
      quadsOf(mesh, (q) => {
        faces.push({
          material: material.name,
          pos: q.pos,
          normal: q.normal,
          right: q.right,
          up: q.up,
          w: q.w,
          h: q.h,
          u0: q.u0,
          v0: q.v0,
          zone: L.zoneAt(q.pos.x, q.pos.z),
          place: L.zoneName(q.pos.x, q.pos.z),
        });
      });
      return;
    }
    if (!GLASS.includes(material.name)) return;
    quadsOf(mesh, (q) => {
      panes.push({
        material: material.name,
        pos: q.pos,
        normal: q.normal,
        right: q.right,
        up: q.up,
        w: q.w,
        h: q.h,
        zone: L.zoneAt(q.pos.x, q.pos.z),
        place: L.zoneName(q.pos.x, q.pos.z),
        interior: L.interiorAt(q.pos),
        dynamic: !mesh.name.startsWith('merged:'),
      });
    });
  });

  // The facade grids the level asked for (one material per distinct spec).
  const grids = [];
  const seen = new Set();
  for (const f of rec.facades) {
    if (!f.material || seen.has(f.material)) continue;
    seen.add(f.material);
    const u = f.material.userData && f.material.userData.facade;
    grids.push({
      material: f.material.name,
      spec: plain(f.spec),
      grid: u ? { w: u.w, h: u.h, bays: u.bays, floors: u.floors, bayW: u.bayW, floorH: u.floorH } : null,
      asked: rec.facades.filter((g) => g.material === f.material).length,
    });
  }
  return { panes, faces, grids };
}

// -------------------------------------------------------------------------------------------------
// Light and sky
// -------------------------------------------------------------------------------------------------

/** Both lighting rigs as the running game sets them (atmos.setTime), and the lamp list. */
function collectAtmos() {
  const rec = window.__ue;
  const G = window.__G;
  const { plain, v3, placed } = rec.h;
  const T = G.THREE;
  const L = G.level;
  const A = G.atmos;
  const shown = A.time;

  const hemi = G.scene.getObjectByName('ambient');
  const spots = [];
  G.scene.traverse((o) => {
    if (o.isSpotLight && /^lamp-light-/.test(o.name)) spots.push(o);
  });

  const color = (c) => ({ hex: c.getHex(), linear: [c.r, c.g, c.b] });
  const direction = new T.Vector3();

  // -- The lamps, and how each one would shine as a real light (src/atmos/lights.js collectLamps and
  //    createLightRig assign): along its own `dir`; a flood without one at the nearest objective; a sign
  //    or lit window out from the wall behind it and down onto the sidewalk; anything else straight down.
  const avenueZ = L.el ? (L.el.minZ + L.el.maxZ) / 2 : (L.bounds.minZ + L.bounds.maxZ) / 2;
  const CARDINALS = [new T.Vector3(1, 0, 0), new T.Vector3(-1, 0, 0), new T.Vector3(0, 0, 1), new T.Vector3(0, 0, -1)];
  const DOWN = new T.Vector3(0, -1, 0);
  const hit = { dist: 0, point: new T.Vector3(), normal: new T.Vector3(), surface: null, box: null };
  const probe = new T.Vector3();
  const explosive = new Set(G.explosives.items.map((item) => item.box));
  const lamps = L.lamps.map((l) => {
    const pos = l.pos;
    let aim = null;
    let aimSource = 'down';
    let wall = null;
    if (l.dir) {
      aim = l.dir.clone().normalize();
      aimSource = 'dir';
    } else if (l.kind === 'flood') {
      let best = null;
      let bestD = 38;
      for (const o of L.objectives) {
        const d = Math.hypot(o.pos.x - pos.x, o.pos.z - pos.z);
        if (d < bestD) {
          bestD = d;
          best = o.pos;
        }
      }
      aim = best ? new T.Vector3(best.x - pos.x, 0.4 - pos.y, best.z - pos.z).normalize() : DOWN.clone();
      aimSource = best ? 'objective' : 'down';
    }
    if (l.kind === 'neon' || l.kind === 'window') {
      let bestD = 2.2;
      for (const c of CARDINALS) {
        const h = G.physics.raycast(pos, c, bestD, hit);
        // The explosives were not standing yet when the atmosphere looked for its walls.
        if (h && h.dist < bestD && !explosive.has(h.box)) {
          bestD = h.dist;
          wall = new T.Vector3(-c.x, 0, -c.z);
        }
      }
      if (!wall && Math.abs(pos.z - avenueZ) > 6) wall = new T.Vector3(0, 0, pos.z > avenueZ ? -1 : 1);
      if (!aim && wall) {
        aim = wall.clone().setY(-0.7).normalize();
        aimSource = 'wall';
      }
    }
    if (!aim) aim = DOWN.clone();
    let floor = 0;
    probe.set(pos.x, pos.y - 0.25, pos.z);
    const below = G.physics.raycast(probe, DOWN, pos.y + 1, hit);
    if (below && below.box && below.point.y > 0.6) {
      const b = below.box;
      if (b.max.x - b.min.x >= 2.5 && b.max.z - b.min.z >= 2.5) floor = below.point.y;
    }
    return {
      kind: l.kind,
      pos: v3(pos),
      color: l.color,
      intensity: l.intensity,
      range: l.range,
      priority: l.priority,
      dir: l.dir ? v3(l.dir) : null,
      aim: v3(aim),
      aimSource,
      wall: wall ? v3(wall) : null,
      floor,
      zone: L.zoneAt(pos.x, pos.z),
      place: L.zoneName(pos.x, pos.z),
      interior: L.interiorAt(pos),
    };
  });

  // -- Check that reading against the game's own lights: with the camera's point of interest on a lamp,
  //    the lamp usually holds one of the real lights, which then stands where it is and points how it
  //    shines. Night: every kind may hold one.
  const check = { held: 0, mismatched: [] };
  const cam = G.camera;
  const savedPos = cam.position.clone();
  const savedQuat = cam.quaternion.clone();
  A.setTime('night');
  if (typeof A.settleLights === 'function') {
    const seenHeld = new Set();
    for (let i = 0; i < lamps.length; i++) {
      const p = L.lamps[i].pos;
      cam.position.set(p.x, p.y, p.z + 6); // the rig looks 6 m ahead of the camera
      cam.lookAt(p.x, p.y, p.z);
      cam.updateMatrixWorld(true);
      A.settleLights();
      for (const s of spots) {
        if (!(s.intensity > 0)) continue;
        const j = L.lamps.findIndex((l) => l.pos.distanceTo(s.position) < 1e-6);
        if (j < 0 || seenHeld.has(j)) continue;
        seenHeld.add(j);
        direction.copy(s.target.position).sub(s.position).normalize();
        const a = lamps[j].aim;
        if (Math.hypot(a.x - direction.x, a.y - direction.y, a.z - direction.z) > 1e-4) check.mismatched.push({ lamp: j, game: v3(direction), export: a });
      }
    }
    check.held = seenHeld.size;
  }
  cam.position.copy(savedPos);
  cam.quaternion.copy(savedQuat);
  cam.updateMatrixWorld(true);

  // -- Both rigs.
  const times = {};
  for (const name of ['day', 'night']) {
    A.setTime(name);
    const sun = A.sun;
    direction.copy(sun.target.position).sub(sun.position).normalize();
    const fog = G.scene.fog;
    times[name] = {
      time: A.time,
      sun: {
        color: color(sun.color),
        intensity: sun.intensity,
        direction: v3(direction),
        castShadow: sun.castShadow,
        shadowRadius: sun.shadow.radius,
        shadowNormalBias: sun.shadow.normalBias,
      },
      ambient: hemi ? { sky: color(hemi.color), ground: color(hemi.groundColor), intensity: hemi.intensity } : null,
      fog: fog ? { type: fog.isFogExp2 ? 'FogExp2' : 'Fog', color: color(fog.color), density: fog.density } : null,
      look: plain(G.render.look),
      exposure: G.render.exposure,
      environmentSet: !!G.scene.environment,
    };
  }
  A.setTime(shown);
  if (typeof A.settleLights === 'function') A.settleLights();

  const stats = A.stats();
  const owners = new Map();
  placed().forEach((b, index) => {
    const o = b.prop.object;
    const sin = Math.sin(o.rotation.y);
    const cos = Math.cos(o.rotation.y);
    for (const hint of b.prop.lights || []) {
      const [hx, hy, hz] = hint.pos;
      const x = o.position.x + hx * cos + hz * sin;
      const y = o.position.y + hy;
      const z = o.position.z - hx * sin + hz * cos;
      L.lamps.forEach((lamp, i) => {
        if (!owners.has(i) && Math.abs(lamp.pos.x - x) < 1e-6 && Math.abs(lamp.pos.y - y) < 1e-6 && Math.abs(lamp.pos.z - z) < 1e-6) owners.set(i, index);
      });
    }
  });
  lamps.forEach((lamp, i) => {
    lamp.prop = owners.has(i) ? owners.get(i) : null;
  });

  return {
    shown,
    times,
    lamps,
    aimCheck: check,
    counts: { lamps: stats.lamps, levelLamps: stats.levelLamps, realLights: stats.realLights, buildings: stats.buildings },
    train: plain(A.train),
    nextTrain: stats.nextTrain,
    clock: stats.clock,
    hasAmbient: !!hemi,
    realLights: spots.length,
  };
}

/**
 * Listens for the El train. Call once; then let the simulation run and read `readTrainWatch`.
 * Every `train:pass` event is kept with the atmosphere's clock and the train's state at that moment.
 */
function startTrainWatch() {
  const rec = window.__ue;
  const G = window.__G;
  if (rec.train) return false;
  rec.train = { events: [], begun: [] };
  let wasActive = G.atmos.train.active;
  let passes = G.atmos.train.passes;
  G.events.on('train:pass', (e) => {
    const t = G.atmos.train;
    rec.train.events.push({ phase: e.phase, duration: e.duration, dir: e.dir, clock: G.atmos.stats().clock, x: t.x, lo: t.lo, hi: t.hi, y: t.y, z: t.z, pass: t.passes });
  });
  // The end of a pass has no event: watch the state once per step (level.update runs with atmos.update).
  const watch = () => {
    const t = G.atmos.train;
    if (t.passes !== passes) {
      passes = t.passes;
      rec.train.begun.push({ pass: t.passes, clock: G.atmos.stats().clock, dir: t.dir, z: t.z, x: t.x });
    }
    if (wasActive && !t.active) rec.train.events.push({ phase: 'ended', duration: 0, dir: t.dir, clock: G.atmos.stats().clock, x: t.x, lo: t.lo, hi: t.hi, y: t.y, z: t.z, pass: t.passes });
    wasActive = t.active;
  };
  const update = G.atmos.update;
  G.atmos.update = function watchedUpdate(dt) {
    const out = update.call(this, dt);
    watch();
    return out;
  };
  rec.train.restore = () => {
    G.atmos.update = update;
  };
  return true;
}

function readTrainWatch() {
  const rec = window.__ue;
  const G = window.__G;
  const { plain } = rec.h;
  const stats = G.atmos.stats();
  return { events: rec.train ? rec.train.events.slice() : [], begun: rec.train ? rec.train.begun.slice() : [], state: plain(G.atmos.train), clock: stats.clock, nextTrain: stats.nextTrain };
}

function stopTrainWatch() {
  const rec = window.__ue;
  if (rec.train && rec.train.restore) rec.train.restore();
  return true;
}

module.exports = {
  installHelpers,
  collectMeta,
  collectConfig,
  callConfigFunctions,
  collectLevel,
  collectProps,
  probeCatalog,
  collectSignage,
  collectGlass,
  collectAtmos,
  startTrainWatch,
  readTrainWatch,
  stopTrainWatch,
};
