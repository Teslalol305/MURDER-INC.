// The level's building kit: small helpers that put a mesh under the static root (merged per material at
// the end), register colliders with G.physics, place catalogue props and collect lamp hints for atmos.
//
// Conventions:
//   - Boxes are given as extents (x0, x1, y0, y1, z0, z1), never as centre + size.
//   - `box` is visual only, `solid` is a collider only, `block` is both.
//   - A material argument is a catalogue name, a [name, opts] pair for mats.get, or a Material.
//   - Geometry UVs are in metres (core/geo.js); overlays from mats (signs, posters, decals, graffiti)
//     are mapped once across their quad whatever repeat their texture carries.

import * as THREE from 'three';
import { boxGeo, cylGeo, planeGeo } from '../core/geo.js';
import { floorAt } from './layout.js';

/** Impact / footstep surface of the catalogue materials the level builds with. */
const SURFACE = {
  asphalt: 'asphalt',
  asphalt_wet: 'asphalt',
  sidewalk: 'concrete',
  curb: 'concrete',
  court: 'concrete',
  dirt: 'dirt',
  concrete: 'concrete',
  concrete_dark: 'concrete',
  cinder: 'concrete',
  brick_red: 'brick',
  brick_brown: 'brick',
  brick_tan: 'brick',
  brick_painted: 'brick',
  stucco: 'concrete',
  tile_white: 'concrete',
  metal_dark: 'metal',
  metal_galv: 'metal',
  steel_el: 'metal',
  steel_rust: 'metal',
  roll_gate: 'metal',
  corrugated: 'metal',
  chainlink: 'metal',
  chrome: 'metal',
  wood: 'wood',
  plywood: 'wood',
  cardboard: 'wood',
  fabric: 'cloth',
  fabric_awning: 'cloth',
  rubber: 'rubber',
  tire: 'rubber',
  glass_dark: 'glass',
  glass_store: 'glass',
  glass_lit_warm: 'glass',
  glass_lit_cool: 'glass',
};

/** How much a lamp of each kind deserves one of the few real lights (atmos sorts by this). */
const LAMP_PRIORITY = { work: 10, flood: 9, street: 6, el: 5, neon: 4, window: 2 };

/**
 * Vehicles share a small paint chart: the prop factory makes one material per body colour, so every
 * vehicle the level places is painted from these (asked colours snap to the nearest, unpainted ones
 * draw from it by seed).
 */
const VEHICLES = new Set(['sedan', 'suv', 'van', 'box_truck', 'pickup']);
const VEHICLE_PAINT = [0x14161a, 0x2a2d33, 0x8f959c, 0xd9d7d0, 0x6e1a1c, 0x1b2a4a, 0x16342a, 0xb9b4a6, 0xc9a23a];

function vehiclePaint(o, name) {
  if (o.color === undefined) {
    const seed = Math.imul(((o.seed ?? 0) + name.length * 7) | 0, 0x9e3779b1) >>> 0;
    return VEHICLE_PAINT[(seed >>> 8) % (VEHICLE_PAINT.length - 1)]; // the mustard stays for box trucks asked for it
  }
  const rgb = (c) => [(c >> 16) & 255, (c >> 8) & 255, c & 255];
  const [r, g, b] = rgb(o.color);
  let best = VEHICLE_PAINT[0];
  let bestD = Infinity;
  for (const c of VEHICLE_PAINT) {
    const [cr, cg, cb] = rgb(c);
    const d = (cr - r) ** 2 + (cg - g) ** 2 + (cb - b) ** 2;
    if (d < bestD) {
      bestD = d;
      best = c;
    }
  }
  return best;
}

const key = (n) => Math.round(n * 1000);
const X_AXIS = new THREE.Vector3(1, 0, 0);
const _dir = new THREE.Vector3();

export function createKit(G) {
  const { mats, props, physics } = G;

  const staticRoot = new THREE.Group(); // merged per material by finish()
  staticRoot.name = 'level-static-source';
  const dynamicRoot = new THREE.Group(); // stateful and animated things, kept as they are
  dynamicRoot.name = 'dynamic';
  const lamps = [];
  const animated = []; // everything with update(dt)
  const placed = []; // {name, x, y, z, yaw, prop}: what stands where (tests, debugging)
  const rng = G.rng.fork('level'); // layout variation that must not depend on what other modules drew
  const boxGeos = new Map();
  const planeGeos = new Map();

  // ---------------------------------------------------------------------------------------------
  // Materials and meshes
  // ---------------------------------------------------------------------------------------------

  const nameOf = (m) => (typeof m === 'string' ? m : Array.isArray(m) ? m[0] : m.isMaterial ? m.name : 'glow');

  // Colour variants ([name, {color}]) and lamp glows do not get a material each (CONTRACT 11.2): they
  // share one vertex-tinted material per catalogue name (mats.get tint 'vertex') or one level glow
  // material, and the colour rides on the geometry.
  const glowMaterial = new THREE.MeshBasicMaterial({ vertexColors: true });
  glowMaterial.name = 'level-glow';
  const tinted = new Map(); // geometry uuid | colour → coloured copy
  const _color = new THREE.Color();

  // Painted and timber surfaces the level also builds in other colours: their plain uses join the
  // tinted material too (catalogue colour on the vertices), so each is one material, not two. Ground
  // materials stay plain: the library gives those a separate day albedo.
  const catalog = G.config.catalog.MATERIALS;
  const ONE_TINT = new Set(['paint_yellow', 'paint_white', 'paint_black', 'paint_red', 'paint_green', 'paint_blue', 'wood', 'plywood', 'fabric', 'fabric_awning', 'court', 'corrugated', 'plastic_orange']);

  /** {material, color}: color (linear, may be HDR) is null when the material carries its own. */
  function resolve(m) {
    if (typeof m === 'string') {
      if (ONE_TINT.has(m) && catalog[m]) return resolve([m, { color: catalog[m].color }]);
      return { material: mats.get(m), color: null };
    }
    if (Array.isArray(m)) {
      const [name, opts] = m;
      if (!opts || opts.color === undefined || !mats.get(name, { tint: 'vertex' }).vertexColors) return { material: mats.get(name, opts), color: null };
      const { color, ...rest } = opts;
      return { material: mats.get(name, { ...rest, tint: 'vertex' }), color: _color.set(color).clone() };
    }
    if (m && m.glow) return { material: glowMaterial, color: _color.set(m.color).multiplyScalar(m.intensity).clone() };
    return { material: m, color: null };
  }

  function mat(m) {
    return resolve(m).material;
  }

  /** A copy of `geo` carrying a constant colour attribute (shared per geometry and colour). */
  function withColor(geo, color) {
    const id = `${geo.uuid}|${color.r.toFixed(4)},${color.g.toFixed(4)},${color.b.toFixed(4)}`;
    let out = tinted.get(id);
    if (!out) {
      out = geo.clone();
      const n = out.getAttribute('position').count;
      const arr = new Float32Array(n * 3);
      for (let i = 0; i < n; i++) {
        arr[i * 3] = color.r;
        arr[i * 3 + 1] = color.g;
        arr[i * 3 + 2] = color.b;
      }
      out.setAttribute('color', new THREE.BufferAttribute(arr, 3));
      tinted.set(id, out);
    }
    return out;
  }

  function mesh(geo, m, o = {}) {
    const { material, color } = resolve(m);
    const out = new THREE.Mesh(color ? withColor(geo, color) : geo, material);
    out.castShadow = o.cast !== false;
    out.receiveShadow = o.receive !== false;
    (o.parent || staticRoot).add(out);
    return out;
  }

  function cachedBox(w, h, d, o) {
    const id = `${key(w)}|${key(h)}|${key(d)}|${o.noTop ? 1 : 0}${o.noBottom ? 1 : 0}`;
    let geo = boxGeos.get(id);
    if (!geo) {
      geo = boxGeo(w, h, d, { noTop: o.noTop, noBottom: o.noBottom });
      boxGeos.set(id, geo);
    }
    return geo;
  }

  /** Visual box from (x0, y0, z0) to (x1, y1, z1). */
  function box(m, x0, x1, y0, y1, z0, z1, o = {}) {
    const out = mesh(cachedBox(x1 - x0, y1 - y0, z1 - z0, o), m, o);
    out.position.set((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
    return out;
  }

  /** Collider only. opts: surface, tag, noNav, bulletOnly, playerOnly. */
  function solid(x0, x1, y0, y1, z0, z1, o = {}) {
    return physics.addBox({
      min: [x0, y0, z0],
      max: [x1, y1, z1],
      surface: o.surface || 'concrete',
      tag: o.tag,
      noNav: o.noNav,
      bulletOnly: o.bulletOnly,
      playerOnly: o.playerOnly,
    });
  }

  /** Visual box with a matching collider. */
  function block(m, x0, x1, y0, y1, z0, z1, o = {}) {
    solid(x0, x1, y0, y1, z0, z1, { ...o, surface: o.surface || SURFACE[nameOf(m)] || 'concrete' });
    return box(m, x0, x1, y0, y1, z0, z1, o);
  }

  /** Box given by centre, size and yaw. `collide` adds its (sliced) collider. */
  function obox(m, cx, cy, cz, sx, sy, sz, yaw = 0, o = {}) {
    const out = mesh(cachedBox(sx, sy, sz, o), m, o);
    out.position.set(cx, cy, cz);
    out.rotation.y = yaw;
    if (o.collide) {
      physics.addOriented([cx, cy, cz], [sx, sy, sz], yaw, {
        surface: o.surface || SURFACE[nameOf(m)] || 'concrete',
        tag: o.tag,
        noNav: o.noNav,
        bulletOnly: o.bulletOnly,
        playerOnly: o.playerOnly,
      });
    }
    return out;
  }

  /** A bar of w (horizontal) × h (vertical) between two points: bracing, rails, diagonals. */
  function beam(m, a, b, w, h, o = {}) {
    _dir.set(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
    const length = _dir.length();
    const out = mesh(cachedBox(length, h, w, o), m, o);
    out.position.set((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2);
    out.quaternion.setFromUnitVectors(X_AXIS, _dir.divideScalar(length));
    return out;
  }

  /** Upright cylinder (or frustum with o.radiusTop) standing from y0 to y1. */
  function cyl(m, x, y0, y1, z, radius, segments = 10, o = {}) {
    const out = mesh(cylGeo(radius, y1 - y0, segments, { radiusTop: o.radiusTop, open: o.open }), m, o);
    out.position.set(x, (y0 + y1) / 2, z);
    return out;
  }

  /** Round bar between two points. */
  function pipe(m, a, b, radius, segments = 6, o = {}) {
    _dir.set(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
    const length = _dir.length();
    const out = mesh(cylGeo(radius, length, segments, { open: true }), m, o);
    out.position.set((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2);
    out.quaternion.setFromUnitVectors(THREE.Object3D.DEFAULT_UP, _dir.divideScalar(length));
    return out;
  }

  function cachedPlane(w, h, facing, su, sv, ou = 0, ov = 0) {
    const id = `${key(w)}|${key(h)}|${facing}|${key(su)}|${key(sv)}|${key(ou)}|${key(ov)}`;
    let geo = planeGeos.get(id);
    if (!geo) {
      geo = planeGeo(w, h, {
        facing,
        uvScale: su === 1 && sv === 1 ? undefined : [su, sv],
        uvOffset: ou || ov ? [ou, ov] : undefined,
      });
      planeGeos.set(id, geo);
    }
    return geo;
  }

  /** Horizontal quad at height y. o.down turns it to face the ground (ceilings, soffits). */
  function flat(m, x0, x1, z0, z1, y, o = {}) {
    const out = mesh(cachedPlane(x1 - x0, z1 - z0, o.down ? '-y' : '+y', 1, 1), m, { cast: false, ...o });
    out.position.set((x0 + x1) / 2, y, (z0 + z1) / 2);
    return out;
  }

  /**
   * Upright quad of w × h centred on (cx, cy, cz), facing '+x' | '-x' | '+z' | '-z'.
   * o.uvOffset shifts its metre UVs (a facade that starts some way up its texture).
   */
  function quad(m, facing, cx, cy, cz, w, h, o = {}) {
    const [su, sv] = o.uvScale || [1, 1];
    const [ou, ov] = o.uvOffset || [0, 0];
    const out = mesh(cachedPlane(w, h, facing, su, sv, ou, ov), m, o);
    out.position.set(cx, cy, cz);
    return out;
  }

  /** Flat strip of paint (or anything else) of the given width between two ground points. */
  function strip(m, ax, az, bx, bz, width, y, o = {}) {
    const length = Math.hypot(bx - ax, bz - az);
    const out = mesh(cachedPlane(length, width, '+y', 1, 1), m, { cast: false, ...o });
    out.position.set((ax + bx) / 2, y, (az + bz) / 2);
    out.rotation.y = -Math.atan2(bz - az, bx - ax);
    return out;
  }

  /** Flat circular arc of paint: centre, radius, from angle a0 to a1 (radians, 0 = +x, π/2 = +z). */
  function arc(m, cx, cz, radius, a0, a1, width, y, segments = 16, o = {}) {
    for (let i = 0; i < segments; i++) {
      const t0 = a0 + ((a1 - a0) * i) / segments;
      const t1 = a0 + ((a1 - a0) * (i + 1)) / segments;
      strip(m, cx + Math.cos(t0) * radius, cz + Math.sin(t0) * radius, cx + Math.cos(t1) * radius, cz + Math.sin(t1) * radius, width, y, o);
    }
  }

  /**
   * A sign, poster, decal or graffiti from mats ({material, w, h}) on a quad, mapped exactly once.
   * facing '+y' lays it on the ground (o.yaw turns it); o.w / o.h resize it.
   */
  function overlay(item, facing, cx, cy, cz, o = {}) {
    const w = o.w ?? item.w;
    const h = o.h ?? item.h;
    const map = item.material.map;
    let su;
    let sv;
    let ou = 0;
    let ov = 0;
    if (item.uv) {
      // An atlas painting (CONTRACT 11.2): the quad's 0…1 maps into its rectangle on the shared page.
      const [u0, v0, u1, v1] = item.uv;
      su = (u1 - u0) / w;
      sv = (v1 - v0) / h;
      ou = u0;
      ov = v0;
    } else {
      // A direction that repeats keeps its metre UVs (road paint, crossing bars); the other is fitted.
      su = map && map.wrapS === THREE.RepeatWrapping ? 1 : 1 / (w * (map ? map.repeat.x : 1));
      sv = map && map.wrapT === THREE.RepeatWrapping ? 1 : 1 / (h * (map ? map.repeat.y : 1));
    }
    const out = mesh(cachedPlane(w, h, facing, su, sv, ou, ov), item.material, { cast: false, receive: false, ...o });
    out.position.set(cx, cy, cz);
    if (o.yaw) out.rotation.y = o.yaw;
    return out;
  }

  /** Does this overlay's texture repeat along its width (so one quad of any length can carry it)? */
  const tiles = (item) => !!item.material.map && item.material.map.wrapS === THREE.RepeatWrapping;

  // Road paint: the library's worn, tiling paint decals when it has them, plain paint otherwise.
  let paints = null;
  function paintFor(color) {
    if (!paints) {
      const white = mats.decal('lane');
      const yellow = mats.decal('lane_yellow');
      paints = {
        white: tiles(white) ? white : null,
        yellow: tiles(yellow) && yellow.w < 0.5 ? yellow : null,
      };
    }
    return paints[color];
  }

  /** A painted line of the given width between two ground points. color: 'white' | 'yellow'. */
  function paint(color, ax, az, bx, bz, width, y) {
    const decal = paintFor(color);
    if (!decal) return strip(color === 'yellow' ? 'paint_yellow' : 'paint_white', ax, az, bx, bz, width, y);
    return overlay(decal, '+y', (ax + bx) / 2, y, (az + bz) / 2, { w: Math.hypot(bx - ax, bz - az), h: width, yaw: -Math.atan2(bz - az, bx - ax) });
  }

  /** Painted circular arc (see arc()). */
  function paintArc(color, cx, cz, radius, a0, a1, width, y, segments = 16) {
    for (let i = 0; i < segments; i++) {
      const t0 = a0 + ((a1 - a0) * i) / segments;
      const t1 = a0 + ((a1 - a0) * (i + 1)) / segments;
      paint(color, cx + Math.cos(t0) * radius, cz + Math.sin(t0) * radius, cx + Math.cos(t1) * radius, cz + Math.sin(t1) * radius, width, y);
    }
  }

  /**
   * Convex prism: the polygon `profile` ([[u, v], …]) swept from a0 to a1 along `axis`.
   * axis 'z': u is x and v is y;  axis 'x': u is z and v is y;  axis 'y': u is x and v is z.
   * Used for ramps, kerb flares, awnings, gables and sloped roofs. UVs are in metres.
   */
  function prism(m, profile, axis, a0, a1, o = {}) {
    const point = (u, v, a) => (axis === 'z' ? [u, v, a] : axis === 'x' ? [a, v, u] : [u, a, v]);
    const n = profile.length;
    let cu = 0;
    let cv = 0;
    for (const [u, v] of profile) {
      cu += u / n;
      cv += v / n;
    }
    const centre = point(cu, cv, (a0 + a1) / 2);
    const position = [];
    const normal = [];
    const uv = [];
    const index = [];

    /** One flat face from corner points (a fan), wound to face away from the prism's centre. */
    function face(points, uvs) {
      const [a, b, c] = points;
      const ux = b[0] - a[0];
      const uy = b[1] - a[1];
      const uz = b[2] - a[2];
      const vx = c[0] - a[0];
      const vy = c[1] - a[1];
      const vz = c[2] - a[2];
      let nx = uy * vz - uz * vy;
      let ny = uz * vx - ux * vz;
      let nz = ux * vy - uy * vx;
      const length = Math.hypot(nx, ny, nz) || 1;
      nx /= length;
      ny /= length;
      nz /= length;
      const outward = nx * (a[0] - centre[0]) + ny * (a[1] - centre[1]) + nz * (a[2] - centre[2]) >= 0;
      const base = position.length / 3;
      for (let i = 0; i < points.length; i++) {
        position.push(...points[i]);
        normal.push(outward ? nx : -nx, outward ? ny : -ny, outward ? nz : -nz);
        uv.push(...uvs[i]);
      }
      for (let i = 1; i < points.length - 1; i++) {
        if (outward) index.push(base, base + i, base + i + 1);
        else index.push(base, base + i + 1, base + i);
      }
    }

    const span = Math.abs(a1 - a0);
    for (let i = 0; i < n; i++) {
      const [u0, v0] = profile[i];
      const [u1, v1] = profile[(i + 1) % n];
      const edge = Math.hypot(u1 - u0, v1 - v0);
      face(
        [point(u0, v0, a0), point(u1, v1, a0), point(u1, v1, a1), point(u0, v0, a1)],
        [[0, 0], [edge, 0], [edge, span], [0, span]],
      );
    }
    if (!o.noCaps) {
      for (const a of [a0, a1]) face(profile.map(([u, v]) => point(u, v, a)), profile.map(([u, v]) => [u, v]));
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(position), 3));
    geo.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(normal), 3));
    geo.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(uv), 2));
    geo.setIndex(index);
    return mesh(geo, m, o);
  }

  /**
   * A straight flight of steps. `dir` is the way it climbs ('+x' | '-x' | '+z' | '-z'), from y0 to y1
   * over the footprint. Each step gets a tread and a solid collider down to y0, so the flight is a wall
   * from the sides and a walkable ramp of low ledges from the front. o.open leaves the risers out.
   */
  function stairs(m, x0, x1, z0, z1, y0, y1, risers, dir, o = {}) {
    const alongX = dir === '+x' || dir === '-x';
    const up = dir === '+x' || dir === '+z';
    const run = ((alongX ? x1 - x0 : z1 - z0) / risers) * (up ? 1 : -1);
    const rise = (y1 - y0) / risers;
    const start = alongX ? (up ? x0 : x1) : up ? z0 : z1;
    const surface = o.surface || SURFACE[nameOf(m)] || 'metal';
    for (let i = 0; i < risers; i++) {
      const a = start + run * i;
      const b = start + run * (i + 1);
      const lo = Math.min(a, b);
      const hi = Math.max(a, b);
      const top = y0 + rise * (i + 1);
      const sx0 = alongX ? lo : x0;
      const sx1 = alongX ? hi : x1;
      const sz0 = alongX ? z0 : lo;
      const sz1 = alongX ? z1 : hi;
      if (o.open) box(m, sx0, sx1, top - 0.05, top, sz0, sz1, o);
      else box(m, sx0, sx1, top - rise, top, sz0, sz1, o);
      if (o.collide !== false) solid(sx0, sx1, y0, top, sz0, sz1, { surface, tag: o.tag || 'stair', playerOnly: o.playerOnly });
    }
  }

  // ---------------------------------------------------------------------------------------------
  // Lamps
  // ---------------------------------------------------------------------------------------------

  /** A lamp hint for atmos. o: priority, dir (Vector3 the light points along). */
  function lamp(x, y, z, kind, color, intensity, range, o = {}) {
    const entry = {
      pos: new THREE.Vector3(x, y, z),
      color,
      intensity,
      range,
      kind,
      priority: o.priority ?? LAMP_PRIORITY[kind] ?? 3,
    };
    if (o.dir) entry.dir = o.dir.clone().normalize();
    lamps.push(entry);
    return entry;
  }

  // ---------------------------------------------------------------------------------------------
  // Props
  // ---------------------------------------------------------------------------------------------

  /**
   * Builds a catalogue prop at (x, z), turned by yaw about +Y, standing on the level's own floor there
   * (o.y overrides: decks, roofs, wall mounts). Its colliders are registered unless o.collide is false,
   * walk-over ones (flatter than 0.2 m, top under 0.3 m) are skipped, dynamic props stay out of the
   * merge and its lamp hints join level.lamps. Remaining opts go to props.build.
   */
  function place(name, x, z, yaw = 0, o = {}) {
    const y = o.y ?? floorAt(x, z);
    if (VEHICLES.has(name)) o = { ...o, color: vehiclePaint(o, name) };
    const prop = props.build(name, o);
    prop.object.position.set(x, y, z);
    prop.object.rotation.y = yaw;
    if (prop.dynamic) prop.object.userData.noMerge = true;
    (prop.dynamic ? dynamicRoot : staticRoot).add(prop.object);

    const sin = Math.sin(yaw);
    const cos = Math.cos(yaw);
    prop.boxes = [];
    if (o.collide !== false) {
      for (const c of prop.colliders || []) {
        const sy = c.max[1] - c.min[1];
        if (sy < 0.2 && c.max[1] < 0.3) continue; // flat things are walked over
        const lx = (c.min[0] + c.max[0]) / 2;
        const lz = (c.min[2] + c.max[2]) / 2;
        // rotation.y maps local +X to (cos, −sin) and local +Z to (sin, cos) in world XZ
        const centre = [x + lx * cos + lz * sin, y + (c.min[1] + c.max[1]) / 2, z - lx * sin + lz * cos];
        const size = [c.max[0] - c.min[0], sy, c.max[2] - c.min[2]];
        prop.boxes.push(
          ...physics.addOriented(centre, size, yaw, {
            surface: c.surface || prop.surface,
            bulletOnly: c.bulletOnly,
            playerOnly: c.playerOnly,
            noNav: c.noNav || o.noNav,
            tag: name,
            owner: prop,
          }),
        );
      }
    }

    if (o.lamps !== false) {
      for (const hint of prop.lights || []) {
        const [hx, hy, hz] = hint.pos;
        // A prop's own work light (a food cart, a floodlight stand) ranks below the shop's four.
        lamp(x + hx * cos + hz * sin, y + hy, z - hx * sin + hz * cos, hint.kind || 'street', hint.color, hint.intensity, hint.range, {
          priority: o.priority ?? (hint.kind === 'work' ? 6 : undefined),
          dir: hint.dir ? new THREE.Vector3(hint.dir[0] * cos + hint.dir[2] * sin, hint.dir[1], -hint.dir[0] * sin + hint.dir[2] * cos) : undefined,
        });
      }
    }
    if (typeof prop.update === 'function') animated.push(prop);
    /** World position of one of the prop's anchors (props.build `anchors`), or null. */
    prop.anchorAt = (id) => {
      const a = prop.anchors && prop.anchors[id];
      return a ? new THREE.Vector3(x + a.pos[0] * cos + a.pos[2] * sin, y + a.pos[1], z - a.pos[0] * sin + a.pos[2] * cos) : null;
    };
    placed.push({ name, x, y, z, yaw, prop });
    return prop;
  }

  return {
    G,
    mats,
    rng,
    surfaceOf: (m) => SURFACE[nameOf(m)] || 'concrete',
    staticRoot,
    dynamicRoot,
    lamps,
    animated,
    placed,
    mat,
    mesh,
    box,
    solid,
    block,
    obox,
    beam,
    cyl,
    pipe,
    flat,
    quad,
    strip,
    arc,
    overlay,
    tiles,
    paint,
    paintArc,
    prism,
    stairs,
    lamp,
    place,
    /** A lamp lens or tube that glows (HDR colour × intensity): one shared material for the block. */
    glow: (color, intensity = 2) => ({ glow: true, color, intensity }),
  };
}
