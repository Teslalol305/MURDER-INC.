// The city beyond the bounds. The level stops at its player-only walls; this is everything past them:
//
//   - the next blocks: rows of walk-ups as low boxes with one shared facade sheet (lit and dark windows,
//     gates and shop fronts), water towers and stair bulkheads on their roofs;
//   - the ground they stand on, the avenue's sidewalks, and the El running on east and west into the haze;
//   - two far rings of skyline cards, the nearer one all the way round, the farther one with a cluster of
//     towers in the west where the glow is;
//   - a few windows that switch on and off, blinking red aviation lights, far headlights crossing the
//     avenue, a plane on approach.
//
// Unlit materials throughout (it is night and far away), fogged by the scene haze, so none of it costs a
// light loop. Lights go into the shared glow batch.

import * as THREE from 'three';
import { boxGeo, mergeGeos, planeGeo } from '../core/geo.js';
import { planCity } from './plan.js';
import { SHEET, facadeSheet, skylineStrip, textureSize } from './textures.js';

const FLOOR_H = 3.1;
const GROUND_H = 4.1;
const BAY_W = 3.2;
const ROW = 1 / SHEET.rows;
const INSET = 0.004; // keeps a band's UVs off the neighbouring row of the sheet

// Brick tints (multiply the sheet), bottom to top the wall cools and darkens.
const TONES = [
  [1.0, 0.74, 0.64],
  [0.92, 0.84, 0.72],
  [0.74, 0.74, 0.78],
  [0.84, 0.66, 0.6],
];

// By day the sheet itself carries the brick colour: the tones only nudge it.
const DAY_TONES = TONES.map((t) => {
  const avg = (t[0] + t[1] + t[2]) / 3;
  return t.map((c) => (c * 0.45 + avg * 0.55) / avg);
});

/**
 * Gathers quads with uv and vertex colour into one geometry. Every quad also gets a day colour: its
 * `dayBase` lit by the sun (`toSun`, a unit vector) by its facing, so the far blocks are modelled by the
 * sun with an unlit material. `dayColors` / `nightColors` hold both sets for the colour attribute.
 */
function quadMesh(toSun, light) {
  const position = [];
  const uv = [];
  const color = [];
  const dayColor = [];
  const index = [];
  const e1 = new THREE.Vector3();
  const e2 = new THREE.Vector3();
  return {
    /** Corners a, b (bottom, left to right seen from outside), c, d (top, right to left). */
    quad(a, b, c, d, u0, v0, u1, v1, bottom, top, dayBase = bottom) {
      const base = position.length / 3;
      position.push(...a, ...b, ...c, ...d);
      uv.push(u0, v0, u1, v0, u1, v1, u0, v1);
      color.push(...bottom, ...bottom, ...top, ...top);
      e1.set(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
      e2.set(d[0] - a[0], d[1] - a[1], d[2] - a[2]);
      const n = e1.cross(e2).normalize(); // outward
      const k = light.ambient + light.sky * Math.max(0, n.y) + light.sun * Math.max(0, n.dot(toSun));
      const foot = k * light.foot; // a little darker at street level
      for (const f of [foot, foot, k, k]) dayColor.push(dayBase[0] * f, dayBase[1] * f, dayBase[2] * f);
      index.push(base, base + 1, base + 2, base, base + 2, base + 3);
    },
    get triangles() {
      return index.length / 3;
    },
    get nightColors() {
      return new Float32Array(color);
    },
    get dayColors() {
      return new Float32Array(dayColor);
    },
    geometry() {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.Float32BufferAttribute(position, 3));
      geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
      geo.setAttribute('color', new THREE.Float32BufferAttribute(color, 3));
      geo.setIndex(index);
      geo.computeBoundingSphere();
      return geo;
    },
  };
}

/**
 * @param {object} o
 * @param {object} o.el      level.el, or null
 * @param {object} o.elRow   {step, anchor}: rhythm of the lamps under the El (its columns stand between them)
 * @param {object} o.deck    {minX, maxX}: how far the level's own El reaches along the street
 */
export function createFarCity(G, { bounds, el, elRow, deck, avenueZ, haze, shared, glowBatch, parent }) {
  const cfg = G.config.look.city;
  const rng = G.rng.fork('atmos-city');
  const centre = new THREE.Vector3((bounds.minX + bounds.maxX) / 2, 0, (bounds.minZ + bounds.maxZ) / 2);
  const group = new THREE.Group();
  group.name = 'atmos-city';
  parent.add(group);

  // ---------------------------------------------------------------------------------------------
  // The next blocks
  // ---------------------------------------------------------------------------------------------

  const sheet = facadeSheet(textureSize(G), rng.fork('sheet'), cfg.litWindows);
  const sheetDay = facadeSheet(textureSize(G), rng.fork('sheet'), cfg.litWindows, true); // same layout, in sunlight
  const times = G.config.look.times;
  const toSun = new THREE.Vector3().fromArray(times.day.sun.direction).normalize().negate();
  const dayLight = { ambient: 0.5, sky: 0.12, sun: 0.62, foot: 0.86 };
  const buildings = planCity(rng.fork('plan'), bounds, { avenueZ });
  const switchSpots = []; // dark windows on facades that look at the block: {p0, right, up, w, h}

  const wallColor = (tone, y, height) => {
    const k = 1.22 - 0.5 * Math.min(1, y / Math.max(height, 12)); // street light at the bottom, night at the top
    const t = TONES[tone % TONES.length];
    return [t[0] * k, t[1] * k * (0.96 + 0.04 * (y / height)), t[2] * k * (0.9 + 0.14 * Math.min(1, y / height))];
  };

  /**
   * One wall as stacked bands. `a` and `b` are the foot of the wall, left to right seen from outside.
   * kind: 'shop' (shop fronts, then windows), 'windows', 'blank'.
   */
  function wall(mesh, a, b, height, floors, tone, kind, facesBlock) {
    const width = Math.hypot(b[0] - a[0], b[2] - a[2]);
    const bays = Math.max(1, Math.round(width / BAY_W));
    const u0 = rng.int(0, SHEET.bays - 1) / SHEET.bays;
    const u1 = u0 + bays / SHEET.bays;
    const at = (p, y) => [p[0], y, p[2]];
    const band = (y0, y1, v0, v1, ua = u0, ub = u1) =>
      mesh.quad(at(a, y0), at(b, y0), at(b, y1), at(a, y1), ua, v0 + INSET, ub, v1 - INSET, wallColor(tone, y0, height), wallColor(tone, y1, height), DAY_TONES[tone % DAY_TONES.length]);

    let y = 0;
    if (kind === 'blank') {
      const tile = width / (BAY_W * SHEET.bays);
      for (; y < height - 0.01; y += FLOOR_H) band(y, Math.min(height, y + FLOOR_H), 1 - ROW, 1, u0, u0 + tile);
      return;
    }
    let rows = floors;
    if (kind === 'shop') {
      band(0, GROUND_H, 0, ROW);
      y = GROUND_H;
      rows--;
    }
    while (rows > 0) {
      const n = Math.min(rows, SHEET.windowRows);
      const first = rng.int(0, SHEET.windowRows - n);
      band(y, y + n * FLOOR_H, ROW * (1 + first), ROW * (1 + first + n));
      if (facesBlock) {
        // Remember the dark windows of this band: some of them will come on later.
        const firstBay = Math.round(u0 * SHEET.bays);
        for (let r = 0; r < n; r++) {
          for (let k = 0; k < bays; k++) {
            if (sheet.lit[first + r][(firstBay + k) % SHEET.bays]) continue;
            switchSpots.push({ a, b, bays, bay: k, y: y + r * FLOOR_H, tone });
          }
        }
      }
      y += n * FLOOR_H;
      rows -= n;
    }
    if (y < height) band(y, height, 1 - ROW, 1, u0, u0 + width / (BAY_W * SHEET.bays)); // parapet
  }

  /** Dark roof furniture: UVs pinned to a patch of bare brick, colour does the rest. */
  function roofBox(mesh, x, y, z, w, h, d, tint) {
    const u = 0.03;
    const v0 = 1 - ROW + INSET * 2;
    const v1 = 1 - INSET * 2;
    const x0 = x - w / 2;
    const x1 = x + w / 2;
    const z0 = z - d / 2;
    const z1 = z + d / 2;
    const q = (a, b) => mesh.quad([a[0], y, a[1]], [b[0], y, b[1]], [b[0], y + h, b[1]], [a[0], y + h, a[1]], u, v0, u + 0.02, v1, tint, tint);
    q([x0, z1], [x1, z1]);
    q([x1, z0], [x0, z0]);
    q([x1, z1], [x1, z0]);
    q([x0, z0], [x0, z1]);
  }

  /** A rooftop water tower: legs, a staved tank, a cone. Eight-sided, dark against the glow. */
  function waterTower(mesh, x, y, z, scale) {
    const tint = [0.5, 0.4, 0.33];
    const u = 0.05;
    const v0 = 1 - ROW + INSET * 2;
    const v1 = 1 - INSET * 2;
    const r = 1.55 * scale;
    const legH = 2.4 * scale;
    const tankH = 3.1 * scale;
    for (const [lx, lz] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) roofBox(mesh, x + lx * r * 0.62, y, z + lz * r * 0.62, 0.16, legH, 0.16, [0.3, 0.28, 0.27]);
    const N = 8;
    const y0 = y + legH;
    const y1 = y0 + tankH;
    for (let i = 0; i < N; i++) {
      const a0 = (i / N) * Math.PI * 2;
      const a1 = ((i + 1) / N) * Math.PI * 2;
      const p0 = [x + Math.cos(a0) * r, z - Math.sin(a0) * r];
      const p1 = [x + Math.cos(a1) * r, z - Math.sin(a1) * r];
      const shade = 0.8 + 0.2 * Math.cos(a0 + 0.6);
      const c = tint.map((t) => t * shade);
      mesh.quad([p0[0], y0, p0[1]], [p1[0], y0, p1[1]], [p1[0], y1, p1[1]], [p0[0], y1, p0[1]], u, v0, u + 0.02, v1, c, c);
      // Roof: a slice of the cone (degenerate quad).
      const apex = [x, y1 + 1.1 * scale, z];
      mesh.quad([p0[0], y1, p0[1]], [p1[0], y1, p1[1]], apex, apex, u, v0, u + 0.02, v1, c.map((t) => t * 0.8), c.map((t) => t * 0.8));
    }
  }

  const core = quadMesh(toSun, dayLight);
  const extra = quadMesh(toSun, dayLight);
  const roofs = []; // tallest roofs get the aviation lights

  for (const b of buildings) {
    const mesh = b.core ? core : extra;
    const sw = [b.x0, 0, b.z1];
    const se = [b.x1, 0, b.z1];
    const ne = [b.x1, 0, b.z0];
    const nw = [b.x0, 0, b.z0];
    const sides = { '+z': [sw, se], '-z': [ne, nw], '+x': [se, ne], '-x': [nw, sw] };
    const opposite = { '+z': '-z', '-z': '+z', '+x': '-x', '-x': '+x' };
    // The front has the shops when it stands on the avenue or a cross street; the back has plain windows; the
    // party walls are blank brick.
    const alongAvenue = Math.abs((b.face === '+z' ? b.z1 : b.z0) - avenueZ) < 13 && (b.face === '+z' || b.face === '-z');
    const frontKind = alongAvenue || b.face === '+x' || b.face === '-x' ? 'shop' : 'windows';
    for (const side of Object.keys(sides)) {
      const [p, q] = sides[side];
      const kind = side === b.face ? frontKind : side === opposite[b.face] ? 'windows' : 'blank';
      wall(mesh, p, q, b.h, b.floors, b.tone, kind, side === b.face);
    }
    // Roof clutter, kept back from the parapet.
    const cx = (b.x0 + b.x1) / 2;
    const cz = (b.z0 + b.z1) / 2;
    const roofY = b.h - 0.9;
    const tar = [0.36, 0.34, 0.36];
    mesh.quad([b.x0, roofY, b.z1], [b.x1, roofY, b.z1], [b.x1, roofY, b.z0], [b.x0, roofY, b.z0], 0.03, 1 - ROW + INSET * 2, 0.05, 1 - INSET * 2, tar, tar);
    if (b.tower) waterTower(mesh, cx + rng.range(-1.5, 1.5), roofY, cz + rng.range(-2, 2), rng.range(0.85, 1.15));
    if (rng.chance(0.6)) roofBox(mesh, cx + rng.range(-3, 3), roofY, cz + rng.range(-3, 3), 3, rng.range(2.3, 3), 4, [0.55, 0.5, 0.48]);
    if (rng.chance(0.4)) roofBox(mesh, cx + rng.range(-4, 4), roofY, cz + rng.range(-4, 4), 0.7, rng.range(1.5, 3), 0.7, [0.4, 0.34, 0.32]);
    roofs.push({ x: cx, y: b.h, z: cz });
  }

  const facadeMaterial = new THREE.MeshBasicMaterial({ map: sheet.texture, vertexColors: true, fog: true });
  facadeMaterial.name = 'atmos-facade';
  facadeMaterial.color.setRGB(cfg.wall[0] * cfg.windowGain, cfg.wall[1] * cfg.windowGain, cfg.wall[2] * cfg.windowGain);

  const blocks = new THREE.Mesh(core.geometry(), facadeMaterial);
  blocks.name = 'atmos-blocks';
  blocks.matrixAutoUpdate = false;
  group.add(blocks);
  const blocksFar = new THREE.Mesh(extra.geometry(), facadeMaterial);
  blocksFar.name = 'atmos-blocks-far';
  blocksFar.matrixAutoUpdate = false;
  group.add(blocksFar);

  // ---------------------------------------------------------------------------------------------
  // Ground, sidewalks and the El beyond the bounds
  // ---------------------------------------------------------------------------------------------

  {
    // A frame of asphalt around the block, a hand below the level's own ground.
    const far = 460;
    const lap = 1.5; // reaches a little way under the level
    const b = bounds;
    const rects = [
      [-far, b.minX + lap, -far, far],
      [b.maxX - lap, far, -far, far],
      [b.minX + lap, b.maxX - lap, -far, b.minZ + lap],
      [b.minX + lap, b.maxX - lap, b.maxZ - lap, far],
    ];
    const parts = rects.map(([x0, x1, z0, z1]) => planeGeo(x1 - x0, z1 - z0, { at: [(x0 + x1) / 2, -0.06, (z0 + z1) / 2] }));
    const ground = new THREE.Mesh(mergeGeos(parts), G.mats.get('asphalt'));
    ground.name = 'atmos-ground';
    ground.receiveShadow = true; // same program as the level's ground; nothing out here is in the shadow map
    ground.matrixAutoUpdate = false;
    group.add(ground);

    // Sidewalks along the avenue, both sides, both directions.
    const reach = G.config.look.lamps.beyond.reach;
    const walks = [];
    for (const [x0, x1] of [[b.maxX + 0.6, b.maxX + reach], [b.minX - reach, b.minX - 0.6]]) {
      // A hair lower than the level's kerb, so a level that paves out here itself simply covers these.
      for (const z of [avenueZ - 9.25, avenueZ + 9.25]) walks.push(boxGeo(x1 - x0, 0.205, 4.5, { at: [(x0 + x1) / 2, 0.0425, z], noBottom: true }));
    }
    const sidewalk = new THREE.Mesh(mergeGeos(walks), G.mats.get('sidewalk'));
    sidewalk.name = 'atmos-sidewalk';
    sidewalk.receiveShadow = true;
    sidewalk.matrixAutoUpdate = false;
    group.add(sidewalk);

    // The El, from where the level's own steel stops: deck, girders, rails, and a pair of columns between
    // every two lamps, the way the level spaces them.
    if (el) {
      const half = (el.maxZ - el.minZ) / 2;
      const mid = (el.minZ + el.maxZ) / 2;
      const rowZ = Math.max(1, half - 0.8);
      const tracks = Array.isArray(el.tracks) && el.tracks.length ? el.tracks : [mid - half * 0.4, mid + half * 0.4];
      const railY = (Number.isFinite(el.deckTop) ? el.deckTop : el.y + 0.33) - 0.08;
      const parts2 = [];
      for (const dir of [1, -1]) {
        const from = dir > 0 ? deck.maxX : deck.minX;
        const to = dir > 0 ? bounds.maxX + reach : bounds.minX - reach;
        const length = Math.abs(to - from);
        if (length < 2) continue;
        const cx = (from + to) / 2;
        parts2.push(boxGeo(length, 0.2, half * 2, { at: [cx, el.y + 0.1, mid] }));
        for (const z of [mid - rowZ, mid + rowZ]) parts2.push(boxGeo(length, 1, 0.36, { at: [cx, el.y - 0.5, z] }));
        for (const t of tracks) {
          for (const side of [-0.72, 0.72]) parts2.push(boxGeo(length, 0.16, 0.08, { at: [cx, railY, t + side] }));
        }
        const first = Math.ceil((Math.min(from, to) - elRow.anchor) / elRow.step - 0.5);
        const last = Math.floor((Math.max(from, to) - elRow.anchor) / elRow.step - 0.5);
        for (let k = first; k <= last; k++) {
          const x = elRow.anchor + (k + 0.5) * elRow.step;
          if (Math.abs(x - from) < 1.5) continue; // the level's last bent stands here
          for (const z of [mid - rowZ, mid + rowZ]) parts2.push(boxGeo(0.56, el.y - 1, 0.56, { at: [x, (el.y - 1) / 2, z] }));
          parts2.push(boxGeo(0.44, 1.1, rowZ * 2, { at: [x, el.y - 0.55, mid] })); // cross girder
        }
      }
      if (parts2.length) {
        const elMore = new THREE.Mesh(mergeGeos(parts2), G.mats.get('steel_el'));
        elMore.name = 'atmos-el';
        elMore.receiveShadow = true;
        elMore.matrixAutoUpdate = false;
        group.add(elMore);
      }
    }
  }

  // ---------------------------------------------------------------------------------------------
  // Skyline rings
  // ---------------------------------------------------------------------------------------------

  const skylineMaterials = [];

  function ring(index, { radius, height, repeats, strip, stripDay, haze: sunk }) {
    const SEG = 72;
    const position = [];
    const uv = [];
    const idx = [];
    for (let i = 0; i <= SEG; i++) {
      const t = i / SEG;
      const a = t * Math.PI * 2;
      const x = centre.x + Math.cos(a) * radius;
      const z = centre.z + Math.sin(a) * radius;
      position.push(x, -3, z, x, height - 3, z);
      uv.push(t * repeats, 0, t * repeats, 1);
      if (i < SEG) idx.push(i * 2, i * 2 + 2, i * 2 + 1, i * 2 + 1, i * 2 + 2, i * 2 + 3);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(position, 3));
    geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    geo.setIndex(idx);
    geo.computeBoundingSphere();

    const material = new THREE.ShaderMaterial({
      name: `atmos-skyline-${index}`,
      uniforms: {
        ...haze.uniforms,
        uMap: { value: strip.texture },
        uSunk: { value: sunk },
        uWindowGain: { value: cfg.windowGain * 0.75 },
      },
      vertexShader: /* glsl */ `
varying vec2 vUv;
varying vec2 vWorldXZ;
void main() {
	vUv = uv;
	vWorldXZ = position.xz;
	gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
}`,
      fragmentShader: /* glsl */ `
uniform sampler2D uMap;
uniform float uSunk;
uniform float uWindowGain;
varying vec2 vUv;
varying vec2 vWorldXZ;
${haze.glsl}
void main() {
	vec4 tex = texture2D( uMap, vUv );
	if ( tex.a < 0.5 ) discard;
	float bright = max( tex.r, max( tex.g, tex.b ) );
	vec3 col = tex.rgb * ( 1.0 + uWindowGain * smoothstep( 0.12, 0.5, bright ) );
	// Aerial perspective: the far city sits in the haze, deepest at street level.
	float sunk = clamp( uSunk + 0.3 * ( 1.0 - vUv.y ) * ( 1.0 - uSunk ), 0.0, 1.0 );
	col = mix( col, hazeColor( vWorldXZ ), sunk );
	gl_FragColor = vec4( col, 1.0 );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,
      side: THREE.DoubleSide,
      fog: false,
    });
    material.userData.maps = { night: strip.texture, day: stripDay.texture };
    skylineMaterials.push(material);
    const mesh = new THREE.Mesh(geo, material);
    mesh.name = `atmos-skyline-${index}`;
    mesh.matrixAutoUpdate = false;
    mesh.renderOrder = 900; // behind everything but the sky
    group.add(mesh);

    // Aviation lights on the tallest tops of this ring.
    const tops = strip.towers.slice().sort((p, q) => q.top - p.top).slice(0, Math.ceil(cfg.aviation / 2));
    for (const t of tops) {
      const copy = rng.int(0, repeats - 1);
      const a = ((t.at + copy) / repeats) * Math.PI * 2;
      glowBatch.add({
        pos: { x: centre.x + Math.cos(a) * (radius - 3), y: t.top * height - 3 + 2.5, z: centre.z + Math.sin(a) * (radius - 3) },
        color: new THREE.Color().setRGB(1, 0.05, 0.03),
        size: 2.4,
        core: 3.2,
        halo: 0.5,
        minAngle: 0.0052,
        blink: rng.chance(0.3) ? null : [rng.range(1.6, 2.6), 0.5, rng.next()],
      });
    }
    return mesh;
  }

  const stripW = textureSize(G, 2048);
  const near = ring(0, {
    radius: cfg.skylineRadius[0],
    height: cfg.skylineHeight[0],
    repeats: 3,
    haze: cfg.skylineHaze[0],
    strip: skylineStrip(stripW / 2, stripW / 8, rng.fork('skyline-near'), { body: [15, 16, 22], lit: 0.2, base: 0.2, variance: 0.42 }),
    stripDay: skylineStrip(stripW / 2, stripW / 8, rng.fork('skyline-near'), { body: [124, 104, 96], lit: 0.2, base: 0.2, variance: 0.42, day: true }),
  });
  // The far ring wraps once and starts in the east, so its tall cluster (mid-strip) stands in the west.
  const far = ring(1, {
    radius: cfg.skylineRadius[1],
    height: cfg.skylineHeight[1],
    repeats: 1,
    haze: cfg.skylineHaze[1],
    strip: skylineStrip(stripW, stripW / 8, rng.fork('skyline-far'), { body: [19, 20, 28], lit: 0.26, base: 0.16, variance: 0.3, tall: 0.75 }),
    stripDay: skylineStrip(stripW, stripW / 8, rng.fork('skyline-far'), { body: [112, 120, 136], lit: 0.26, base: 0.16, variance: 0.3, tall: 0.75, day: true }),
  });

  // ---------------------------------------------------------------------------------------------
  // Lights: roofs, traffic, the plane
  // ---------------------------------------------------------------------------------------------

  roofs.sort((p, q) => q.y - p.y);
  for (const r of roofs.slice(0, Math.floor(cfg.aviation / 2))) {
    glowBatch.add({
      pos: { x: r.x, y: r.y + 3.5, z: r.z },
      color: new THREE.Color().setRGB(1, 0.05, 0.03),
      size: 1.1,
      core: 3,
      halo: 0.45,
      minAngle: 0.0045,
      blink: [rng.range(1.8, 2.8), 0.45, rng.next()],
    });
  }

  // Headlights and tail lights on the cross streets, a pair of glows per car.
  {
    const streets = [bounds.maxX + 10, bounds.minX - 10, bounds.maxX + 88, bounds.minX - 88];
    const white = new THREE.Color().setRGB(1, 0.92, 0.74);
    const red = new THREE.Color().setRGB(1, 0.06, 0.04);
    for (let i = 0; i < cfg.traffic; i++) {
      const x = streets[i % streets.length] + rng.range(-2, 2);
      const south = rng.chance(0.5);
      const speed = rng.range(7, 12) * (south ? 1 : -1);
      const span = 240; // the stretch of street around the block worth driving
      const loop = rng.range(26, 60); // one car per street every so often
      const z0 = centre.z - (span / 2) * Math.sign(speed);
      const offset = rng.range(0, loop);
      // Seen from the block a car is either coming (white) or going (red); pick by which side of us it starts.
      const color = rng.chance(0.5) ? white : red;
      for (const dx of [-0.75, 0.75]) {
        glowBatch.add({
          pos: { x: x + dx, y: 0.75, z: z0 },
          color,
          size: 0.55,
          core: color === white ? 5 : 3,
          halo: 0.5,
          minAngle: 0.003,
          motion: [0, 0, speed, loop, offset],
        });
      }
    }
  }

  // A plane on approach: a white strobe, a red beacon and a steady light, crossing every so often.
  {
    const p = cfg.plane;
    const heading = new THREE.Vector3(0.55, -0.035, 0.83).normalize(); // north-west to south-east, descending
    const span = 1100; // metres of flight path; its middle is the closest point, west of the block
    const start = new THREE.Vector3(centre.x - p.distance * 0.8, p.height + 20, centre.z + p.distance * 0.2).addScaledVector(heading, -span / 2);
    const motion = [heading.x * p.speed, heading.y * p.speed, heading.z * p.speed, Math.max(p.every, span / p.speed), p.every * 0.55];
    glowBatch.add({ pos: start, color: new THREE.Color().setRGB(1, 1, 1), size: 3, core: 6, halo: 0.6, minAngle: 0.004, blink: [1.3, 0.07, 0], motion });
    glowBatch.add({ pos: start, color: new THREE.Color().setRGB(1, 0.08, 0.05), size: 2.4, core: 3.5, halo: 0.5, minAngle: 0.0036, blink: [1.3, 0.12, 0.5], motion });
    glowBatch.add({ pos: start, color: new THREE.Color().setRGB(0.9, 0.95, 1), size: 2, core: 1.6, halo: 0.3, minAngle: 0.003, motion });
  }

  // ---------------------------------------------------------------------------------------------
  // Windows that switch
  // ---------------------------------------------------------------------------------------------

  let switchers = null;
  if (switchSpots.length) {
    const position = [];
    const aUv = [];
    const aSwitch = [];
    const index = [];
    const count = Math.min(cfg.switchers, switchSpots.length);
    const w = SHEET.window;
    for (let n = 0; n < count; n++) {
      const spot = switchSpots.splice(rng.int(0, switchSpots.length - 1), 1)[0];
      const { a, b } = spot;
      const len = Math.hypot(b[0] - a[0], b[2] - a[2]);
      const dx = (b[0] - a[0]) / len;
      const dz = (b[2] - a[2]) / len;
      const nx = -dz; // outward normal of a wall whose foot runs a → b (left to right seen from outside)
      const nz = dx;
      const bayW = len / spot.bays;
      const s0 = (spot.bay + w.u0) * bayW;
      const s1 = (spot.bay + w.u1) * bayW;
      const y0 = spot.y + w.v0 * FLOOR_H;
      const y1 = spot.y + w.v1 * FLOOR_H;
      const base = position.length / 3;
      const lift = 0.08;
      const corner = (s, y) => position.push(a[0] + dx * s + nx * lift, y, a[2] + dz * s + nz * lift);
      corner(s0, y0);
      corner(s1, y0);
      corner(s1, y1);
      corner(s0, y1);
      aUv.push(0, 0, 1, 0, 1, 1, 0, 1);
      const period = rng.range(7, 26);
      const phase = rng.range(0, 40);
      const warm = rng.chance(0.75) ? 0 : 1;
      for (let k = 0; k < 4; k++) aSwitch.push(period, phase, warm);
      index.push(base, base + 1, base + 2, base, base + 2, base + 3);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(position, 3));
    geo.setAttribute('aUv', new THREE.Float32BufferAttribute(aUv, 2));
    geo.setAttribute('aSwitch', new THREE.Float32BufferAttribute(aSwitch, 3));
    geo.setIndex(index);
    geo.computeBoundingSphere();
    const material = new THREE.ShaderMaterial({
      name: 'atmos-switchers',
      uniforms: { ...haze.uniforms, uTime: shared.uTime, uGain: { value: cfg.wall[0] * cfg.windowGain * 0.62 } },
      vertexShader: /* glsl */ `
attribute vec2 aUv;
attribute vec3 aSwitch;   // period (s), phase, 0 = tungsten / 1 = television
uniform float uTime;
uniform float uGain;
varying vec2 vUv;
varying vec3 vColor;
${haze.glsl}
float slotOn( float slot, float seed ) {
	return step( 0.55, fract( sin( slot * 12.9898 + seed * 78.233 ) * 43758.5453 ) );
}
void main() {
	vec4 mv = modelViewMatrix * vec4( position, 1.0 );
	float s = uTime / aSwitch.x + aSwitch.y;
	float on = mix( slotOn( floor( s ), aSwitch.y ), slotOn( floor( s ) + 1.0, aSwitch.y ), smoothstep( 0.985, 1.0, fract( s ) ) );
	vec3 warm = vec3( 1.0, 0.66, 0.3 );
	// A television: cold, and never quite steady.
	vec3 tv = vec3( 0.3, 0.45, 1.0 ) * ( 0.55 + 0.45 * sin( uTime * 7.0 + aSwitch.y * 9.0 ) * sin( uTime * 2.3 + aSwitch.y ) );
	vColor = mix( warm, tv, aSwitch.z ) * on * uGain * hazeT( - mv.z, position.xz );
	vUv = aUv;
	gl_Position = projectionMatrix * mv;
}`,
      fragmentShader: /* glsl */ `
varying vec2 vUv;
varying vec3 vColor;
void main() {
	// Brighter at the top of the pane, and a sash bar across the middle.
	float shade = ( 0.7 + 0.3 * vUv.y ) * ( 1.0 - 0.8 * step( abs( vUv.y - 0.5 ), 0.03 ) ) * ( 1.0 - 0.8 * step( abs( vUv.x - 0.5 ), 0.025 ) );
	gl_FragColor = vec4( vColor * shade, 1.0 );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,
      transparent: true,
      blending: THREE.AdditiveBlending,
      premultipliedAlpha: true,
      depthWrite: false,
      fog: false,
      polygonOffset: true,
      polygonOffsetFactor: -2,
      polygonOffsetUnits: -2,
    });
    switchers = new THREE.Mesh(geo, material);
    switchers.name = 'atmos-switchers';
    switchers.matrixAutoUpdate = false;
    switchers.renderOrder = -15;
    group.add(switchers);
  }

  const coreColors = { day: core.dayColors, night: core.nightColors };
  const extraColors = { day: extra.dayColors, night: extra.nightColors };
  let timeCfg = times.night.city;
  let shownDetail = null;

  return {
    group,
    blocks,
    blocksFar,
    near,
    far,
    switchers,
    textures: [sheet.texture, sheetDay.texture, ...skylineMaterials.flatMap((m) => [m.userData.maps.night, m.userData.maps.day])],
    stats: { buildings: buildings.length, triangles: core.triangles + extra.triangles },
    /** Shows or hides the optional layers for a quality preset (config/look.js `detail`). */
    setDetail(detail) {
      shownDetail = detail;
      blocksFar.visible = detail.cityFull;
      far.visible = detail.farRing;
      if (switchers) switchers.visible = detail.switchers && timeCfg.lights;
    },
    /** Day or night: the facade sheet and its colours, the skyline strips, the switching windows. */
    setTime(name) {
      const t = times[name] || times.day;
      timeCfg = t.city;
      const day = name === 'day';
      facadeMaterial.map = day ? sheetDay.texture : sheet.texture;
      facadeMaterial.color.setRGB(timeCfg.sheet[0], timeCfg.sheet[1], timeCfg.sheet[2]);
      for (const [mesh, colors] of [[blocks, coreColors], [blocksFar, extraColors]]) {
        const attr = mesh.geometry.getAttribute('color');
        attr.array.set(day ? colors.day : colors.night);
        attr.needsUpdate = true;
      }
      skylineMaterials.forEach((m, i) => {
        m.uniforms.uMap.value = day ? m.userData.maps.day : m.userData.maps.night;
        m.uniforms.uWindowGain.value = timeCfg.windowGain;
        m.uniforms.uSunk.value = timeCfg.skylineSunk[i];
      });
      if (switchers) switchers.visible = !!(shownDetail && shownDetail.switchers) && timeCfg.lights;
    },
  };
}
