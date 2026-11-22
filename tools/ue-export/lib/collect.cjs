'use strict';

// Page-side collectors for the Unreal data export. Every function here is serialised by Playwright and
// runs inside the booted game page (page.evaluate), so none of them can close over anything in this
// file: they share code through window.__ue.h, which `installHelpers` puts there first.
//
// Everything is returned in web space (metres, +Y up, north = −Z) as plain JSON; the Node side
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
  const placed = () => rec.builds.filter((b) => b.after === 'input');

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
      if (m.isMesh && m.name === '@glass' && m.material) lit = m.material.name === 'glass_car_lit' || m.material === G.mats.get('glass_car_lit');
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

  /** A short hash of a prop's shape: two props built from the same shape variant share it. */
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

  rec.h = { num, v3, plain, placed, paintOf, domeOf, localBounds, shapeOf, describeProp, rectsOf, modelMeshes };
  return true;
}

// -------------------------------------------------------------------------------------------------
// Tuning
// -------------------------------------------------------------------------------------------------

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
    difficulty: G.game.difficulty,
    mode: G.game.mode,
    seed: G.rng.seed,
    build: plain(G.build),
    order: rec.order.slice(),
    explosiveKinds: kinds,
    enemiesResolved: resolved,
    quality: plain(G.quality),
    errors: (window.__errors || []).slice(),
    fatal: window.__fatal || null,
    stats: window.__stats(),
    page: {
      title: document.title,
      boot: Object.fromEntries(
        [['kicker', '.boot-kicker'], ['mark', '.boot-mark'], ['star', '.boot-star'], ['note', '.boot-note']]
          .map(([key, selector]) => [key, (document.querySelector(`#boot ${selector}`) || {}).textContent || null])
          .map(([key, text]) => [key, text ? text.replace(/\s+/g, ' ').trim() : null]),
      ),
      canvasLabel: (document.getElementById('view') || { getAttribute: () => null }).getAttribute('aria-label'),
    },
  };
}

/**
 * Calls config functions in the page: [{path: ['flow', 'holdout', 'total'], calls: [[1], [2]]}] →
 * [[value, value]]. A call that throws answers {$error}.
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
    const info = rec.boxes.get(b) || { via: null, after: null, oriented: null, slice: 0 };
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
      slice: info.oriented ? info.slice : null,
      addedBy: info.after === 'input' ? 'level' : info.after === 'combat' ? 'explosives' : info.after,
    };
  });

  const oriented = rec.oriented.map((o) => ({
    center: { x: o.center[0], y: o.center[1], z: o.center[2] },
    size: { x: o.size[0], y: o.size[1], z: o.size[2] },
    yaw: o.yaw,
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

  // Which way a ground spawn point opens: toward the walkable cells it can reach in a straight line.
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
    let cells = 0;
    if (s.type !== 'air') {
      const open = opening(s.pos, SPAWN_REACH);
      cells = open.cells;
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
      facing: { x: dx / length, y: 0, z: dz / length },
      facingSource: source,
      facingCells: cells,
    };
  });

  const debug = typeof G.enemies.debug === 'function' ? G.enemies.debug() : null;

  // Regions of constant answer of the level's own queries, sampled on a 0.1 m grid.
  const STEP = 0.1;
  const places = rectsOf(L.bounds, STEP, (x, z) => L.zoneName(x, z));
  const zoneRects = rectsOf(L.bounds, STEP, (x, z) => L.zoneAt(x, z));
  const surfaces = rectsOf(L.bounds, STEP, (x, z) => L.groundSurfaceAt(x, z));
  const floors = rectsOf(L.bounds, STEP, (x, z) => L.floorAt(x, z));

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
              height: item.height,
              halfX: item.halfX,
              halfZ: item.halfZ,
              collider: item.box && boxIndex.has(item.box) ? boxIndex.get(item.box) : null,
              instanced: !!item.batch,
            }
          : null,
      };
    }),
    explosiveItems: items.length,
    interiorBoxes: L.interiorBoxes.map((b) => ({ min: v3(b.min), max: v3(b.max) })),
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
      rebuilds: nav.rebuilds,
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
  const { plain, v3, placed, paintOf, domeOf, shapeOf, describeProp } = rec.h;
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

  const describedTypes = {};
  const instances = list.map((b, index) => {
    const o = b.prop.object;
    const shape = shapeOf(b.prop);
    if (!describedTypes[b.name]) describedTypes[b.name] = {};
    if (!describedTypes[b.name][shape]) describedTypes[b.name][shape] = describeProp(b.prop);
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
      shape,
      colliders: (b.prop.boxes || []).map((box) => (boxIndex.has(box) ? boxIndex.get(box) : null)),
      lamps: [...lampOwner.entries()].filter(([, owner]) => owner === index).map(([lamp]) => lamp),
      state: b.prop.state ?? null,
    };
  });

  // The explosives module builds one template per type (after the level): describe those too.
  for (const b of rec.builds) {
    if (b.after === 'input') continue;
    const shape = shapeOf(b.prop);
    if (!describedTypes[b.name]) describedTypes[b.name] = {};
    if (!describedTypes[b.name][shape]) describedTypes[b.name][shape] = describeProp(b.prop);
  }

  return { instances, describedTypes, lampOwners: [...lampOwner.entries()] };
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
  const { paintOf, domeOf, shapeOf, describeProp } = rec.h;
  return requests.map(({ name, opts }) => {
    const shapes = []; // by seed
    const paints = [];
    const domes = [];
    const described = {};
    let error = null;
    for (let seed = 0; seed < seeds; seed++) {
      try {
        const prop = G.props.build(name, { ...opts, seed });
        const shape = shapeOf(prop);
        shapes.push(shape);
        paints.push(paintOf(prop));
        domes.push(domeOf(prop));
        if (!described[shape]) described[shape] = describeProp(prop);
      } catch (err) {
        error = String((err && err.message) || err);
        break;
      }
    }
    return { name, opts, shapes, paints, domes, described, error };
  });
}

// -------------------------------------------------------------------------------------------------
// Light and sky
// -------------------------------------------------------------------------------------------------

/** Both lighting rigs as the running game sets them (atmos.setTime), and the lamp list. */
function collectAtmos() {
  const rec = window.__ue;
  const G = window.__G;
  const { plain, v3 } = rec.h;
  const L = G.level;
  const A = G.atmos;
  const shown = A.time;

  let hemi = null;
  const spots = [];
  G.scene.traverse((o) => {
    if (o.isHemisphereLight && !hemi) hemi = o;
    if (o.isSpotLight) spots.push(o);
  });

  const color = (c) => ({ hex: c.getHex(), linear: [c.r, c.g, c.b] });
  const direction = new G.THREE.Vector3();

  const times = {};
  for (const name of ['day', 'night']) {
    A.setTime(name);
    if (typeof A.settleLights === 'function') A.settleLights();
    const sun = A.sun;
    direction.copy(sun.target.position).sub(sun.position).normalize();
    const cam = sun.shadow.camera;
    const fog = G.scene.fog;
    times[name] = {
      time: A.time,
      sun: {
        color: color(sun.color),
        intensity: sun.intensity,
        position: v3(sun.position),
        target: v3(sun.target.position),
        direction: v3(direction),
        castShadow: sun.castShadow,
        shadow: {
          mapSize: sun.shadow.mapSize.x,
          bias: sun.shadow.bias,
          normalBias: sun.shadow.normalBias,
          radius: sun.shadow.radius,
          left: cam.left,
          right: cam.right,
          top: cam.top,
          bottom: cam.bottom,
          near: cam.near,
          far: cam.far,
        },
      },
      ambient: hemi ? { sky: color(hemi.color), ground: color(hemi.groundColor), intensity: hemi.intensity } : null,
      fog: fog ? { type: fog.isFogExp2 ? 'FogExp2' : 'Fog', color: color(fog.color), density: fog.density } : null,
      look: plain(G.render.look),
      exposure: G.render.exposure,
      realLights: spots.map((s) => ({
        pos: v3(s.position),
        target: v3(s.target.position),
        color: color(s.color),
        intensity: s.intensity,
        distance: s.distance,
        angle: s.angle,
        penumbra: s.penumbra,
        decay: s.decay,
      })),
      stats: plain(A.stats()),
    };
  }
  A.setTime(shown);
  if (typeof A.settleLights === 'function') A.settleLights();

  return {
    shown,
    times,
    lamps: L.lamps.map((l) => ({
      kind: l.kind,
      pos: v3(l.pos),
      color: l.color,
      intensity: l.intensity,
      range: l.range,
      priority: l.priority,
      dir: l.dir ? v3(l.dir) : null,
      zone: L.zoneAt(l.pos.x, l.pos.z),
      place: L.zoneName(l.pos.x, l.pos.z),
      interior: L.interiorAt(l.pos),
    })),
    train: plain(A.train),
    stats: plain(A.stats()),
    quality: plain(G.quality),
    toneMappingExposure: G.renderer.toneMappingExposure,
    facades: rec.facades.map((f) => ({
      spec: plain(f.spec),
      facade: f.material && f.material.userData && f.material.userData.facade
        ? { w: f.material.userData.facade.w, h: f.material.userData.facade.h, bays: f.material.userData.facade.bays, floors: f.material.userData.facade.floors, bayW: f.material.userData.facade.bayW, floorH: f.material.userData.facade.floorH }
        : null,
      material: f.material ? f.material.name : null,
    })),
  };
}

/**
 * Sends a train across (atmos.passTrain) and records what the game announces: called once to start a
 * pass, then polled while the harness steps the simulation. `dir` +1 east, −1 west.
 */
function startTrainWatch(dir) {
  const rec = window.__ue;
  const G = window.__G;
  if (!rec.train) {
    rec.train = { events: [], samples: [] };
    G.events.on('train:pass', (e) => {
      rec.train.events.push({ phase: e.phase, duration: e.duration, dir: e.dir, clock: G.atmos.stats().clock, x: G.atmos.train.x, z: G.atmos.train.z, y: G.atmos.train.y });
    });
  }
  rec.train.events.length = 0;
  G.atmos.passTrain(dir, null);
  return true;
}

function readTrainWatch() {
  const rec = window.__ue;
  const G = window.__G;
  const { plain } = rec.h;
  return { events: rec.train ? rec.train.events.slice() : [], state: plain(G.atmos.train), clock: G.atmos.stats().clock };
}

// -------------------------------------------------------------------------------------------------
// Signs, posters, graffiti and decals
// -------------------------------------------------------------------------------------------------

/**
 * Where every painting ended up. The level maps each one onto a single quad whose UVs are the
 * painting's rectangle on its atlas page (CONTRACT 11.2), and the static merge keeps quads whole, so
 * the merged meshes still say where each one hangs: its centre, its size and which way it faces.
 */
function collectSignage() {
  const rec = window.__ue;
  const G = window.__G;
  const { plain, v3 } = rec.h;
  const L = G.level;
  const T = G.THREE;

  // Paintings by material: [{kind, args, w, h, uv}] (a painting asked for twice is one entry).
  const byMaterial = new Map();
  const seen = new Set();
  const paintings = [];
  for (const p of rec.paintings) {
    if (p.after !== 'input' || !p.out || !p.out.material) continue;
    const uv = p.out.uv ? p.out.uv.map((n) => Math.round(n * 1e6) / 1e6) : null;
    const key = `${p.out.material.uuid}|${uv ? uv.join(',') : 'tile'}|${p.kind}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const entry = { kind: p.kind, args: plain(p.args), w: p.out.w, h: p.out.h, uv, material: p.out.material.name || null, placed: 0 };
    paintings.push(entry);
    if (!byMaterial.has(p.out.material)) byMaterial.set(p.out.material, []);
    byMaterial.get(p.out.material).push(entry);
  }

  const a = new T.Vector3();
  const b = new T.Vector3();
  const c = new T.Vector3();
  const d = new T.Vector3();
  const eu = new T.Vector3();
  const ev = new T.Vector3();
  const normal = new T.Vector3();
  const quads = [];
  let unmatched = 0;

  L.root.updateMatrixWorld(true);
  L.root.traverse((mesh) => {
    if (!mesh.isMesh || !byMaterial.has(mesh.material)) return;
    const candidates = byMaterial.get(mesh.material);
    const position = mesh.geometry.getAttribute('position');
    const uvAttr = mesh.geometry.getAttribute('uv');
    const index = mesh.geometry.index;
    if (!position || !uvAttr || !index) return;
    // Every source was one plane: four corners, two triangles, in order.
    for (let t = 0; t + 5 < index.count; t += 6) {
      const ids = new Set();
      for (let k = 0; k < 6; k++) ids.add(index.getX(t + k));
      if (ids.size !== 4) continue;
      const corner = [...ids];
      let u0 = Infinity;
      let u1 = -Infinity;
      let v0 = Infinity;
      let v1 = -Infinity;
      for (const id of corner) {
        u0 = Math.min(u0, uvAttr.getX(id));
        u1 = Math.max(u1, uvAttr.getX(id));
        v0 = Math.min(v0, uvAttr.getY(id));
        v1 = Math.max(v1, uvAttr.getY(id));
      }
      // The corners at (u0, v0), (u1, v0) and (u0, v1) give the quad's two edges.
      const pick = (u, v) => corner.reduce((best, id) => {
        const e = Math.abs(uvAttr.getX(id) - u) + Math.abs(uvAttr.getY(id) - v);
        return best === null || e < best.e ? { id, e } : best;
      }, null).id;
      a.fromBufferAttribute(position, pick(u0, v0)).applyMatrix4(mesh.matrixWorld);
      b.fromBufferAttribute(position, pick(u1, v0)).applyMatrix4(mesh.matrixWorld);
      c.fromBufferAttribute(position, pick(u0, v1)).applyMatrix4(mesh.matrixWorld);
      d.fromBufferAttribute(position, pick(u1, v1)).applyMatrix4(mesh.matrixWorld);
      eu.subVectors(b, a);
      ev.subVectors(c, a);
      normal.crossVectors(eu, ev).normalize();
      const w = eu.length();
      const h = ev.length();
      const centre = { x: (a.x + b.x + c.x + d.x) / 4, y: (a.y + b.y + c.y + d.y) / 4, z: (a.z + b.z + c.z + d.z) / 4 };

      // Which painting: the one whose atlas rectangle these UVs are (tiling road paint has none).
      let match = null;
      for (const p of candidates) {
        if (!p.uv) {
          if (!match) match = p;
          continue;
        }
        const [pu0, pv0, pu1, pv1] = p.uv;
        const lo = Math.min(pv0, pv1);
        const hi = Math.max(pv0, pv1);
        if (Math.abs(u0 - Math.min(pu0, pu1)) < 2e-4 && Math.abs(u1 - Math.max(pu0, pu1)) < 2e-4 && Math.abs(v0 - lo) < 2e-4 && Math.abs(v1 - hi) < 2e-4) {
          match = p;
          break;
        }
      }
      if (!match) {
        unmatched++;
        continue;
      }
      match.placed++;
      quads.push({
        painting: paintings.indexOf(match),
        pos: centre,
        normal: v3(normal),
        right: { x: eu.x / (w || 1), y: eu.y / (w || 1), z: eu.z / (w || 1) },
        up: { x: ev.x / (h || 1), y: ev.y / (h || 1), z: ev.z / (h || 1) },
        w,
        h,
        zone: L.zoneAt(centre.x, centre.z),
        place: L.zoneName(centre.x, centre.z),
        castShadow: mesh.castShadow,
      });
    }
  });

  return { paintings, quads, unmatched };
}

module.exports = {
  installHelpers,
  collectConfig,
  callConfigFunctions,
  collectLevel,
  collectProps,
  probeCatalog,
  collectAtmos,
  startTrainWatch,
  readTrainWatch,
  collectSignage,
};
