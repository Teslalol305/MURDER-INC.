// Materials and generated textures (`G.mats`), CONTRACT 6.1.
//
// Everything here is painted in code when it is first asked for:
//
//   get(name, opts)          a catalogue material (src/config/catalog.js MATERIALS) with canvas-painted
//                            albedo / normal / roughness at real-world scale
//   emissive(color, i)       unlit HDR-bright material for lamps, LEDs, tubes
//   sign(spec)               shop signs: neon, box, painted, awning, street, stencil, plate
//   facade(spec)             a wall with windows, some of them lit, deterministic by seed
//   poster / graffiti / decal   transparent quads for walls and the street
//   drawIPX(ctx, x, y, h, c) the IPX wordmark on any 2D canvas
//
// Conventions
// - Geometry UVs are in metres (core/geo.js) and tiling materials repeat at their own real size.
// - sign / poster / graffiti / decal return {material, w, h, uv}: a painting for a quad of w × h metres
//   that lives on a shared atlas page (src/mats/atlas.js). `uv` = [u0, v0, u1, v1] is its rectangle on
//   the page: map the quad's corners into it. `material` is shared by everything of the same class on
//   the same page (lit signs, neon, clear overlays), so the block merges into a handful of meshes.
//   Road paint is the exception: `lane`, `lane_yellow` and `crosswalk` keep a material of their own
//   whose texture repeats (`map.wrapS / wrapT` is RepeatWrapping) and come back without `uv`: the
//   repeating direction takes metre UVs, so one quad can be any length.
// - Every material built here carries the same five texture slots (albedo, normal, roughness/metalness,
//   emissive), filled with 1 × 1 stand-ins where a look does not need them. That keeps the whole block
//   on a handful of shader programs instead of one per combination.
// - Ground and masonry get a small shader patch (src/mats/shader.js): world-space tone variation, the
//   wet street, grime at the foot of walls. `?matfx=0` switches the patches off.
// - Texture size follows the quality tier at boot: test 256, low 512, otherwise 1024 (`?tex=` overrides).

import * as THREE from 'three';
import { createAtlas, createWrapAtlas } from './mats/atlas.js';
import { canvas2d, createBank, dropScratch, makeTexture, pixelTexture, toHex } from './mats/canvas.js';
import { DECALS, createDecalPainter } from './mats/decals.js';
import { paintFacade } from './mats/facade.js';
import { facadeKey, facadeLayout, facadeSpec } from './mats/layout.js';
import { prng } from './mats/noise.js';
import { POSTER_SIZE, POSTER_VARIANTS, createPaperPainter } from './mats/paper.js';
import { MACRO_TILE, macroTexture, patchCutout, patchPacked, patchWorld } from './mats/shader.js';
import { createSignPainter } from './mats/signs.js';
import { SETS, chainlinkPixels, paintSet } from './mats/surfaces.js';
import { createType, loadFonts } from './mats/type.js';

const UNKNOWN = { color: 0x808080, roughness: 0.8, metalness: 0 };
const NO_OPTS = Object.freeze({});
const FENCE_TILE = 0.6; // metres per repeat of the chain-link mesh (8 diamonds)

/**
 * How each catalogue material is dressed.
 *   set     surface set that supplies albedo, normal and roughness (src/mats/surfaces.js)
 *   skin    which albedo of the set ('base' unless named)
 *   relief  take the normal map from this set instead
 *   gloss   take the roughness map from this set instead
 *   world   [tone variation, wetness, wall grime]: gets the world shader patch (static scenery only)
 *   normal  normal-map strength (default 1)
 *   day     albedo by day (sRGB hex) where the catalogue colour is tuned for the night street: the
 *           untinted material switches between the two with atmos.time
 *   dayGlow  multiplier on the catalogue glow by day: lit windows are glass in the sun, not lamps
 */
export const LOOKS = {
  // ground
  asphalt: { set: 'asphalt', world: [0.2, 1, 0], day: 0x56575a },
  asphalt_wet: { set: 'asphalt', normal: 0.45 },
  sidewalk: { set: 'sidewalk', world: [0.16, 0.5, 0], day: 0x9a968e },
  curb: { set: 'concrete', world: [0.12, 0.3, 0], day: 0xa4a097 },
  court: { set: 'asphalt', skin: 'coat', normal: 0.5, world: [0.14, 0.5, 0] },
  dirt: { set: 'dirt', world: [0.2, 0.7, 0], day: 0x625646 },
  // masonry
  concrete: { set: 'concrete', world: [0.18, 0, 0.5], day: 0x8e8c87 },
  concrete_dark: { set: 'concrete', world: [0.18, 0, 0.4], day: 0x5e5e62 },
  cinder: { set: 'cinder', world: [0.16, 0, 0.6] },
  brick_red: { set: 'brick', skin: 'red', world: [0.18, 0, 0.7] },
  brick_brown: { set: 'brick', skin: 'brown', world: [0.18, 0, 0.7] },
  brick_tan: { set: 'brick', skin: 'tan', world: [0.18, 0, 0.7] },
  brick_painted: { set: 'brick', skin: 'painted', world: [0.16, 0, 0.8] },
  stucco: { set: 'stucco', world: [0.16, 0, 0.8] },
  tile_white: { set: 'tile' },
  // metal
  metal_dark: { set: 'metal' },
  metal_galv: { set: 'metal', skin: 'galv' },
  steel_el: { set: 'steel_el' },
  steel_rust: { set: 'rust' },
  roll_gate: { set: 'roll_gate' },
  corrugated: { set: 'corrugated' },
  chainlink: { cutout: true },
  chrome: {},
  gold: {},
  // paint and plastics
  car_paint: { gloss: 'smudge' },
  paint_yellow: { set: 'paint' },
  paint_white: { set: 'paint' },
  paint_red: { set: 'paint' },
  paint_blue: { set: 'paint' },
  paint_green: { set: 'paint' },
  paint_black: { set: 'paint' },
  plastic_dark: { relief: 'pebble' },
  plastic_orange: { relief: 'pebble' },
  rubber: { relief: 'pebble' },
  tire: { set: 'tire' },
  trash_bag: { set: 'wrinkle' },
  // organic and soft
  wood: { set: 'wood' },
  plywood: { set: 'plywood' },
  cardboard: { set: 'cardboard' },
  fabric_awning: { set: 'fabric' },
  fabric: { set: 'fabric' },
  leaves: { set: 'leaves', doubleSide: true },
  skin: {},
  // glass
  glass_dark: { gloss: 'smudge' },
  glass_store: { gloss: 'smudge', dayGlow: 0.3 },
  glass_lit_warm: { gloss: 'smudge', dayGlow: 0.06 },
  glass_lit_cool: { gloss: 'smudge', dayGlow: 0.06 },
  glass_car: { gloss: 'smudge' },
};
const PLAIN = {};
/** Sets that dress world-patched looks: they keep a separate ORM map (its red channel is the water level). */
const WORLD_SETS = new Set(Object.values(LOOKS).filter((l) => l.world).map((l) => l.set));

const WHITE = [1, 1, 1];
const mod = (n, m) => ((Math.floor(n) % m) + m) % m;

export async function createMats(G) {
  const MATERIALS = G.config.catalog.MATERIALS;
  const brand = G.config.brand;
  const palette = G.config.look.palette;

  // Lettering needs the page fonts; wait for them, briefly.
  await loadFonts();
  const type = createType(brand.fonts);

  const tier = { test: 256, low: 512 }[G.quality.name] ?? 1024;
  const size = [256, 512, 1024].includes(+G.params.tex) ? +G.params.tex : tier;
  const worldFx = G.params.matfx !== '0';
  const maxAniso = G.renderer.capabilities.getMaxAnisotropy();
  const ANISO = { ground: 8, wall: 4, prop: 2 };
  const aniso = (kind) => Math.max(1, Math.min(maxAniso, (ANISO[kind] || 2) * (size === 256 ? 0.5 : 1)));

  const bank = createBank(256, size >= 1024 ? 512 : 256);
  const cache = new Map(); // key → material, or {material, w, h}
  const warned = new Set();
  const stats = { sets: 0, textures: 0, materials: 0, signs: 0, facades: 0 };

  // Glow and wetness by time of day (applyTime below): multipliers on each kind's night glow.
  const NIGHT = { sign: 1, neon: 1, facade: 1, dry: 0 };
  const DAY = { sign: 0.3, neon: 0.55, facade: 0, dry: 1 };
  const FACADE_GLOW = 1.6;
  const glowScale = { ...(timeOfDay() === 'night' ? NIGHT : DAY) };
  const facades = []; // facade materials, their window glow follows the time of day
  const retint = []; // {material, night, day, mean}: ground and masonry with a day albedo (LOOKS.day)
  const windows = []; // {material, base, day}: catalogue glass that glows at night (LOOKS.dayGlow)

  // 1 × 1 stand-ins for the slots a look leaves empty.
  const white = pixelTexture(255, 255, 255, true);
  const flat = pixelTexture(128, 128, 255, false);
  const plainOrm = pixelTexture(255, 255, 255, false);
  white.name = 'mats:white';
  flat.name = 'mats:flat';
  plainOrm.name = 'mats:plainOrm';

  /** Every texture the library makes goes through here: counted, and named for census tools. */
  const texture = (canvas, opts, label = '') => {
    stats.textures++;
    const t = makeTexture(canvas, opts);
    t.name = `mats:${label}`;
    return t;
  };

  // ---------------------------------------------------------------------------------------------
  // Surface sets as textures
  // ---------------------------------------------------------------------------------------------

  const _c = new THREE.Color();

  /** Average colour of a canvas in linear RGB: what a tint has to be divided by. */
  function meanColor(canvas) {
    const ctx = canvas2d(16, 16, true);
    ctx.drawImage(canvas, 0, 0, 16, 16);
    const data = ctx.getImageData(0, 0, 16, 16).data;
    const sum = [0, 0, 0];
    for (let i = 0; i < data.length; i += 4) {
      _c.setRGB(data[i] / 255, data[i + 1] / 255, data[i + 2] / 255, THREE.SRGBColorSpace);
      sum[0] += _c.r;
      sum[1] += _c.g;
      sum[2] += _c.b;
    }
    return sum.map((v) => v / (data.length / 4));
  }

  const surfaces = new Map();

  /**
   * One RGBA texture from a set's normal and ORM canvases: R, G normal x, y; B metalness (or, `blue` = 0,
   * the ORM's red channel: the water level of a ground set); A roughness.
   * Built from the raw pixels (a canvas would premultiply the alpha and lose the normal's precision).
   */
  function packTexture(normalCanvas, ormCanvas, opts, label, blue) {
    const w = normalCanvas.width;
    const h = normalCanvas.height;
    const n = normalCanvas.getContext('2d').getImageData(0, 0, w, h).data;
    const m = ormCanvas.getContext('2d').getImageData(0, 0, w, h).data;
    const data = new Uint8Array(w * h * 4);
    // Rows flipped here (canvas row 0 is the top; three.js flips canvases, not data, on upload).
    for (let y = 0; y < h; y++) {
      for (let x = 0, i = y * w * 4, o = (h - 1 - y) * w * 4; x < w; x++, i += 4, o += 4) {
        data[o] = n[i];
        data[o + 1] = n[i + 1];
        data[o + 2] = m[i + blue];
        data[o + 3] = m[i + 1];
      }
    }
    const t = new THREE.DataTexture(data, w, h, THREE.RGBAFormat, THREE.UnsignedByteType);
    t.colorSpace = THREE.NoColorSpace;
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(opts.repeat[0], opts.repeat[1]);
    t.magFilter = THREE.LinearFilter;
    t.minFilter = THREE.LinearMipmapLinearFilter;
    t.generateMipmaps = true;
    t.anisotropy = opts.aniso;
    t.needsUpdate = true;
    t.name = `mats:${label}`;
    stats.textures++;
    return t;
  }

  /** The textures of a surface set, painted on first use. */
  function surface(name) {
    let s = surfaces.get(name);
    if (s) return s;
    const spec = SETS[name];
    const painted = paintSet(name, size, bank);
    const opts = { repeat: [1 / spec.tile[0], 1 / spec.tile[1]], aniso: aniso(spec.aniso) };
    const skins = new Map();
    let normal;
    let orm;
    let packed;
    s = {
      spec,
      /** Normal + roughness / metalness in one texture (shader.js patchPacked) when both exist. */
      packable: !!(painted.normal && painted.orm),
      /** Dresses world-patched looks: blue holds the water level, metalness stays a plain value. */
      world: WORLD_SETS.has(name),
      get normal() {
        if (normal === undefined) normal = painted.normal ? texture(painted.normal, { ...opts, srgb: false }, `${name}:normal`) : null;
        return normal;
      },
      get orm() {
        if (orm === undefined) orm = painted.orm ? texture(painted.orm, { ...opts, srgb: false }, `${name}:orm`) : null;
        return orm;
      },
      get packed() {
        if (packed === undefined) packed = s.packable ? packTexture(painted.normal, painted.orm, opts, `${name}:packed`, s.world ? 0 : 2) : null;
        return packed;
      },
      /** {map, mean} of one albedo, or null when the set has no colour of its own. */
      skin(key) {
        if (!painted.albedo) return null;
        if (!skins.has(key)) {
          const source = painted.albedo[key] ?? painted.albedo.base;
          const canvas = typeof source === 'function' ? source() : source;
          skins.set(key, { map: texture(canvas, opts, `${name}:${key}`), mean: meanColor(canvas) });
        }
        return skins.get(key);
      },
    };
    surfaces.set(name, s);
    stats.sets++;
    return s;
  }

  // ---------------------------------------------------------------------------------------------
  // Materials
  // ---------------------------------------------------------------------------------------------

  /** A MeshStandardMaterial with all five texture slots filled. */
  function standard({ map, normalMap, orm, metalMap = orm, emissiveMap, roughness = 0.8, metalness = 0 } = {}) {
    const material = new THREE.MeshStandardMaterial({
      map: map || white,
      normalMap: normalMap || flat,
      roughnessMap: orm || plainOrm,
      metalnessMap: metalMap || plainOrm,
      emissiveMap: emissiveMap || white,
      roughness,
      metalness,
    });
    stats.materials++;
    return material;
  }

  /** Sets `target` so that a texture averaging `mean` (linear RGB) comes out as `hex` on average. */
  function tint(target, hex, mean) {
    _c.setHex(hex);
    target.setRGB(Math.min(8, _c.r / Math.max(mean[0], 0.004)), Math.min(8, _c.g / Math.max(mean[1], 0.004)), Math.min(8, _c.b / Math.max(mean[2], 0.004)));
  }

  /** Options every material understands (the contract's, plus a few pass-throughs). */
  function applyOptions(material, o, def) {
    const glow = o.emissive ?? def.emissive;
    if (glow !== undefined) {
      material.emissive.setHex(toHex(glow));
      material.emissiveIntensity = o.emissiveIntensity ?? def.emissiveIntensity ?? 1;
    }
    if (o.doubleSide) material.side = THREE.DoubleSide;
    if (o.transparent) {
      material.transparent = true;
      // three.js draws a transparent double-sided material twice and rebuilds its program
      // parameters for each pass, every frame. One pass is plenty for fences and glass.
      if (material.side === THREE.DoubleSide) material.forceSinglePass = true;
    }
    if (o.opacity !== undefined) material.opacity = o.opacity;
    if (o.vertexColors) material.vertexColors = true;
    if (o.flatShading) material.flatShading = true;
    if (o.alphaTest) material.alphaTest = o.alphaTest;
    if (o.depthWrite !== undefined) material.depthWrite = !!o.depthWrite;
    if (o.envMapIntensity !== undefined) material.envMapIntensity = o.envMapIntensity;
  }

  const macro = { value: null }; // shared by every world material
  const dry = { value: glowScale.dry }; // 0 at night (the soaked street), 1 by day; follows atmos.time in update()
  const lookUniforms = new Map();

  function worldUniforms(world) {
    if (!macro.value) {
      macro.value = macroTexture(256);
      macro.value.name = 'mats:macro';
      stats.textures++;
    }
    const key = world.join(',');
    let look = lookUniforms.get(key);
    if (!look) {
      look = { value: new THREE.Vector4(world[0], world[1], world[2], 1 / MACRO_TILE) };
      lookUniforms.set(key, look);
    }
    return { miMacro: macro, miLook: look, miDry: dry };
  }

  function textured(def, look, o, extra) {
    const set = look.set ? surface(look.set) : null;
    const skin = set ? set.skin(look.skin || 'base') : null;
    const relief = look.relief ? surface(look.relief) : set;
    const gloss = look.gloss ? surface(look.gloss) : set;
    // A set that supplies both the relief and the gloss of a material without the world patch sends
    // them as one packed texture.
    const packed = set && relief === set && gloss === set && set.packable ? set.packed : null;
    const orm = packed || (gloss ? gloss.orm : null);
    const material = standard({
      map: skin && skin.map,
      normalMap: packed || (relief && relief.normal),
      orm,
      metalMap: packed && set.world ? plainOrm : orm,
      emissiveMap: extra && extra.emissiveMap,
    });
    const patched = worldFx && look.world && o.local !== true;
    if (packed && !patched) patchPacked(material);
    if (o.tint === 'vertex') {
      // The colour comes from the geometry: the material only cancels the painting's own average,
      // so a vertex colour is the colour the surface ends up with.
      const mean = skin ? skin.mean : WHITE;
      material.color.setRGB(Math.min(8, 1 / Math.max(mean[0], 0.004)), Math.min(8, 1 / Math.max(mean[1], 0.004)), Math.min(8, 1 / Math.max(mean[2], 0.004)));
      material.vertexColors = true;
    } else {
      tint(material.color, o.color !== undefined ? toHex(o.color, def.color) : def.color, skin ? skin.mean : WHITE);
      if (look.day !== undefined && o.color === undefined) {
        const entry = { material, night: def.color, day: look.day, mean: skin ? skin.mean : WHITE };
        retint.push(entry);
        if (glowScale.dry) tint(material.color, look.day, entry.mean);
      }
    }
    // A painted roughness map holds absolute values around the set's own level: scale, do not replace.
    material.roughness = (o.roughness ?? def.roughness ?? 0.8) / (orm ? gloss.spec.rough : 1);
    material.metalness = o.metalness ?? def.metalness ?? 0;
    if (look.normal !== undefined) material.normalScale.setScalar(look.normal);
    if (look.doubleSide) material.side = THREE.DoubleSide;
    applyOptions(material, o, def);
    if (patched) {
      patchWorld(material, extra && extra.facade ? { ...worldUniforms(look.world), ...extra.facade } : worldUniforms(look.world), !!packed);
    }
    return material;
  }

  let fence = null;

  /** Chain-link: an alpha-tested weave. `transparent` / `opacity` are ignored, the mesh is the alpha. */
  function cutout(def, o) {
    if (!fence) {
      const px = chainlinkPixels(Math.max(128, size / 2));
      const map = new THREE.DataTexture(px.data, px.size, px.size, THREE.RGBAFormat, THREE.UnsignedByteType);
      map.colorSpace = THREE.SRGBColorSpace;
      map.wrapS = map.wrapT = THREE.RepeatWrapping;
      map.repeat.set(1 / FENCE_TILE, 1 / FENCE_TILE);
      map.magFilter = THREE.LinearFilter;
      map.minFilter = THREE.LinearMipmapLinearFilter;
      map.generateMipmaps = true;
      map.anisotropy = aniso('wall');
      map.needsUpdate = true;
      map.name = 'mats:chainlink';
      stats.textures++;
      // Wire width in texels (see chainlinkPixels: 8.5 % of the diagonal period).
      fence = { map, uniforms: { miWire: { value: new THREE.Vector3(px.size, (px.size / 8) * 0.085, 1.15) } } };
    }
    const material = standard({ map: fence.map });
    if (o.tint === 'vertex') {
      material.color.setRGB(1 / 0.55, 1 / 0.57, 1 / 0.6);
      material.vertexColors = true;
    } else {
      tint(material.color, o.color !== undefined ? toHex(o.color, def.color) : def.color, [0.55, 0.57, 0.6]);
    }
    material.roughness = o.roughness ?? def.roughness ?? 0.6;
    // Thin wire has little to mirror at night: half metal, so lamps still light it.
    material.metalness = o.metalness ?? Math.min(def.metalness ?? 0.8, 0.5);
    material.alphaTest = 0.5;
    material.side = THREE.DoubleSide;
    const { emissive, emissiveIntensity, vertexColors, envMapIntensity } = o;
    applyOptions(material, { emissive, emissiveIntensity, vertexColors, envMapIntensity }, def);
    if (worldFx) patchCutout(material, fence.uniforms);
    return material;
  }

  function optionKey(opts) {
    return Object.keys(opts)
      .sort()
      .map((k) => {
        const v = opts[k];
        return `${k}=${k === 'color' || k === 'emissive' ? toHex(v) : v}`;
      })
      .join(',');
  }

  function get(name, opts) {
    const key = opts ? `${name}|${optionKey(opts)}` : name;
    let material = cache.get(key);
    if (material) return material;

    let def = MATERIALS[name];
    if (!def) {
      if (!warned.has(name)) {
        warned.add(name);
        console.warn(`[mats] unknown material '${name}': add it to src/config/catalog.js`);
      }
      def = UNKNOWN;
    }
    const look = LOOKS[name] || PLAIN;
    const o = opts || NO_OPTS;
    material = look.cutout ? cutout(def, o) : textured(def, look, o);
    material.name = name;
    if (look.dayGlow !== undefined && o.emissive === undefined && def.emissive !== undefined) {
      const entry = { material, base: material.emissiveIntensity, day: look.dayGlow };
      windows.push(entry);
      if (glowScale.dry) material.emissiveIntensity = entry.base * entry.day;
    }
    cache.set(key, material);
    return material;
  }

  /** Unlit and HDR-bright: anything above 1 after the multiply blooms. */
  function emissive(color, intensity = 2) {
    const hex = toHex(color, 0xffffff);
    const key = `emissive|${hex}|${intensity}`;
    let material = cache.get(key);
    if (!material) {
      material = new THREE.MeshBasicMaterial({ color: hex });
      material.color.multiplyScalar(intensity);
      material.name = 'emissive';
      cache.set(key, material);
    }
    return material;
  }

  function canvasTexture(w, h, draw, opts = {}) {
    const ctx = canvas2d(Math.max(2, w), Math.max(2, h));
    draw(ctx, ctx.canvas.width, ctx.canvas.height);
    return texture(ctx.canvas, { aniso: 4, ...opts }, 'canvasTexture');
  }

  /** Turns a material into a quad that sits on a wall or the ground without z-fighting. */
  function asOverlay(material) {
    material.transparent = true;
    material.depthWrite = false;
    material.polygonOffset = true;
    material.polygonOffsetFactor = -2;
    material.polygonOffsetUnits = -2;
    return material;
  }

  // ---------------------------------------------------------------------------------------------
  // Signs
  // ---------------------------------------------------------------------------------------------

  const env = { size, type, bank, brand, palette };
  const signs = createSignPainter(env);
  const paper = createPaperPainter({ ...env, drawIPX: signs.drawIPX, ipxWidth: signs.ipxWidth });
  const decals = createDecalPainter(env);

  const flicker = []; // neon tube materials: {material, base, rate, phase, faulty, wait, burst}
  const chance = prng(4242); // cosmetic, but seeded: screenshots repeat

  // Atlas pages (CONTRACT 11.2). Two classes:
  //   sign   opaque boards with an emissive layer: box, painted, awning, street, plate, neon
  //   clear  alpha overlays without glow: posters, graffiti, decals, stencilled signs
  // Every page has one material per class (plus NEON_RINGS flicker twins on sign pages that share
  // the page textures), so a page costs two or three textures whatever it holds.
  const PAGE = size >= 512 ? 2048 : 1024;
  const SIGN_GLOW = 2.6; // page emissiveIntensity: the brightest style's glow, the others are baked lower
  const NEON_RINGS = 3; // neon flicker groups (the second one is the tired tube that stutters)
  const pageTextureOpts = { wrap: 'clamp', aniso: aniso('wall') };
  const signPages = [];

  function pageTextures(page) {
    return {
      map: texture(page.albedo.canvas, pageTextureOpts, 'page:albedo'),
      emissiveMap: page.emissive ? texture(page.emissive.canvas, pageTextureOpts, 'page:emissive') : null,
      orm: texture(page.orm.canvas, { ...pageTextureOpts, srgb: false, aniso: 1 }, 'page:orm'),
    };
  }

  const atlases = {
    sign: createAtlas({
      width: PAGE,
      height: PAGE,
      pad: 4,
      opaque: true,
      emissive: true,
      onPage(page) {
        const t = pageTextures(page);
        const material = standard({ map: t.map, normalMap: null, orm: t.orm, emissiveMap: t.emissiveMap, roughness: 1, metalness: 1 });
        material.emissive.setHex(0xffffff);
        material.emissiveIntensity = SIGN_GLOW * glowScale.sign;
        // Signs hang a hair in front of a wall: keep them in front at any distance.
        material.polygonOffset = true;
        material.polygonOffsetFactor = -1;
        material.polygonOffsetUnits = -1;
        material.name = `atlas:sign:${page.index}`;
        const neon = [];
        for (let i = 0; i < NEON_RINGS; i++) {
          const twin = material.clone();
          twin.name = `atlas:neon:${page.index}:${i}`;
          stats.materials++;
          neon.push(twin);
          flicker.push({ material: twin, base: SIGN_GLOW * glowScale.neon, rate: 9 + chance() * 6, phase: chance() * 6.28, faulty: i === 1, wait: 2 + chance() * 6, burst: 0 });
        }
        const user = { ...t, material, neon, used: 0 };
        signPages.push(user);
        return user;
      },
    }),
    clear: createAtlas({
      width: PAGE,
      height: PAGE,
      pad: 4,
      opaque: false,
      emissive: false,
      onPage(page) {
        const t = pageTextures(page);
        const material = asOverlay(standard({ map: t.map, orm: t.orm, roughness: 1, metalness: 1 }));
        material.name = `atlas:clear:${page.index}`;
        return { ...t, material, used: 0 };
      },
    }),
  };

  /** Copies a painting into a page of `cls` and flags the page for upload. */
  function toAtlas(cls, picture, look) {
    const placed = atlases[cls].add(picture, look);
    const user = placed.page.user;
    user.map.needsUpdate = true;
    user.orm.needsUpdate = true;
    if (user.emissiveMap && look.emissive) user.emissiveMap.needsUpdate = true;
    user.used++;
    return { user, uv: placed.uv };
  }

  function sign(spec) {
    const o = signs.resolve(spec);
    let entry = cache.get(o.key);
    if (!entry) {
      const painted = signs.paint(o);
      const cls = o.def.overlay ? 'clear' : 'sign';
      const { user, uv } = toAtlas(cls, painted.albedo, {
        emissive: painted.emissive,
        glow: o.def.glow / SIGN_GLOW,
        roughness: o.def.roughness,
        metalness: 0,
      });
      let material = user.material;
      if (o.style === 'neon' && painted.emissive) material = user.neon[stats.signs % NEON_RINGS];
      entry = { material, w: o.w, h: o.h, uv };
      cache.set(o.key, entry);
      stats.signs++;
    }
    return { material: entry.material, w: entry.w, h: entry.h, uv: entry.uv.slice() };
  }

  // ---------------------------------------------------------------------------------------------
  // Facades
  // ---------------------------------------------------------------------------------------------

  // Facade window layers share pages (two textures a page instead of two a facade).
  const facadePages = createWrapAtlas({
    width: PAGE,
    height: PAGE,
    pad: 8,
    onPage(page) {
      const opts = { wrap: 'clamp', aniso: aniso('wall') };
      return { overlay: texture(page.overlay.canvas, opts, 'facade:overlay'), emissive: texture(page.emissive.canvas, opts, 'facade:emissive') };
    },
  });

  function facade(spec) {
    const s = facadeSpec(spec);
    let base = s.base;
    if (!MATERIALS[base] || !LOOKS[base] || !LOOKS[base].world) {
      if (!warned.has(`facade:${base}`)) {
        warned.add(`facade:${base}`);
        console.warn(`[mats] facade base '${base}' is not a wall material: brick_red is used`);
      }
      base = s.base = 'brick_red';
    }
    const key = facadeKey(s);
    let material = cache.get(key);
    if (material) return material;
    if (!worldFx) return get(base); // the window layer needs the shader patch

    const painted = paintFacade(s, facadeLayout(s), size);
    const placed = facadePages.add(painted.overlay, painted.emissive);
    const pageUser = placed.page.user;
    pageUser.overlay.needsUpdate = true;
    pageUser.emissive.needsUpdate = true;
    const overlay = pageUser.overlay;
    material = textured(MATERIALS[base], LOOKS[base], NO_OPTS, {
      emissiveMap: pageUser.emissive,
      facade: {
        miFacade: { value: overlay },
        miFacadeRect: { value: new THREE.Vector4().fromArray(placed.rect) },
        miFacadeScale: { value: new THREE.Vector2(1 / s.w, 1 / s.h) },
      },
    });
    material.emissive.setHex(0xffffff);
    material.emissiveIntensity = FACADE_GLOW * glowScale.facade;
    material.name = `facade:${base}`;
    facades.push(material);
    // For the level: the size one repeat covers and the grid it holds (plus the window layer itself).
    material.userData.facade = { w: s.w, h: s.h, bays: s.bays, floors: s.floors, bayW: s.bayW, floorH: s.floorH, overlay };
    cache.set(key, material);
    stats.facades++;
    return material;
  }

  // ---------------------------------------------------------------------------------------------
  // Posters, graffiti, decals
  // ---------------------------------------------------------------------------------------------

  /**
   * A painting for a clear quad, cached by key: on a clear atlas page, or (painted.wrap) on a
   * repeating texture of its own, which comes back without `uv`.
   */
  function quad(key, roughness, metalness, make) {
    let entry = cache.get(key);
    if (!entry) {
      const painted = make();
      if (painted.wrap) {
        const material = asOverlay(
          standard({
            map: texture(painted.canvas, { repeat: painted.repeat, wrap: painted.wrap, aniso: aniso('ground') }, key),
            roughness,
            metalness,
          }),
        );
        material.name = key.replace(/\|/g, ':');
        entry = { material, w: painted.w, h: painted.h, uv: null };
      } else {
        const { user, uv } = toAtlas('clear', painted.canvas, { roughness, metalness });
        entry = { material: user.material, w: painted.w, h: painted.h, uv };
      }
      cache.set(key, entry);
    }
    return entry.uv ? { material: entry.material, w: entry.w, h: entry.h, uv: entry.uv.slice() } : { material: entry.material, w: entry.w, h: entry.h };
  }

  function poster(kind = 'ad', seed = 0) {
    const k = POSTER_SIZE[kind] ? kind : 'ad';
    const v = mod(+seed || 0, POSTER_VARIANTS[k]);
    return quad(`poster|${k}|${v}`, 0.88, 0, () => paper.poster(k, v));
  }

  function graffiti(text = 'RULE', seed = 0, color) {
    const str = String(text);
    const n = Math.floor(+seed || 0);
    return quad(`graffiti|${str}|${n}|${color === undefined || color === null ? '' : toHex(color)}`, 0.7, 0, () => paper.graffiti(str, n, color));
  }

  function decal(kind = 'grime', variant = 0) {
    const k = DECALS[kind] ? kind : 'grime';
    const def = DECALS[k];
    const v = mod(+variant || 0, def.variants);
    return quad(`decal|${k}|${v}`, def.roughness, def.metalness || 0, () => {
      const painted = decals.decal(k, v);
      // Road paint tiles in metres both ways, so one material serves a line of any length; a
      // crossing repeats along its width only (one painting holds w metres of bars).
      if (def.tile) return { ...painted, repeat: [1 / def.tile, 1 / def.tile], wrap: 'repeat' };
      if (def.wrap) return { ...painted, repeat: [def.wrap[0] === 'repeat' ? 1 / painted.w : 1, def.wrap[1] === 'repeat' ? 1 / painted.h : 1], wrap: def.wrap };
      return painted;
    });
  }

  // ---------------------------------------------------------------------------------------------
  // Per frame
  // ---------------------------------------------------------------------------------------------

  /** 'day' | 'night': what atmos shows, else the user setting. */
  function timeOfDay() {
    const t = (G.atmos && G.atmos.time) || (G.settings && typeof G.settings.get === 'function' && G.settings.get('time'));
    return t === 'night' ? 'night' : 'day';
  }

  /**
   * Day and night (CONTRACT 11.1). By day signs are lit signage, not lamps: their glow drops so the
   * painted face carries them; windows are glass, not light; the street dries to a few damp patches.
   * Only uniform values change (no defines, no new programs).
   */
  let shownTime = null;
  function applyTime(name) {
    shownTime = name;
    const k = name === 'night' ? NIGHT : DAY;
    Object.assign(glowScale, k);
    dry.value = k.dry;
    for (const page of signPages) page.material.emissiveIntensity = SIGN_GLOW * k.sign;
    for (const f of flicker) f.base = SIGN_GLOW * k.neon;
    for (const m of facades) m.emissiveIntensity = FACADE_GLOW * k.facade;
    for (const r of retint) tint(r.material.color, k.dry ? r.day : r.night, r.mean);
    for (const w of windows) w.material.emissiveIntensity = w.base * (k.dry ? w.day : 1);
  }

  /** Neon hum: a small ripple on every tube, and now and then a tired one stutters. */
  function update(dt) {
    const now = timeOfDay();
    if (now !== shownTime) applyTime(now);
    const t = G.time.t;
    for (let i = 0; i < flicker.length; i++) {
      const f = flicker[i];
      let k = 1 + 0.03 * Math.sin(t * f.rate + f.phase) + 0.02 * Math.sin(t * f.rate * 2.63 + f.phase * 1.7);
      if (f.faulty) {
        if (f.burst > 0) {
          f.burst -= dt;
          if (Math.sin(t * 47 + f.phase) * Math.sin(t * 13.1) > 0.12) k *= 0.3;
        } else {
          f.wait -= dt;
          if (f.wait <= 0) {
            f.burst = 0.25 + chance() * 0.6;
            f.wait = 3 + chance() * 8;
          }
        }
      }
      f.material.emissiveIntensity = f.base * k;
    }
  }

  // Once the block stands, the painting scratch space can go.
  G.events.on('boot:done', () => {
    dropScratch();
    bank.trim();
  });

  return {
    get,
    emissive,
    sign,
    facade,
    poster,
    graffiti,
    decal,
    drawIPX: signs.drawIPX,
    canvasTexture,
    names: () => Object.keys(MATERIALS),
    update,
    /** Texture tier in pixels (256 | 512 | 1024) and what has been built so far. */
    textureSize: size,
    stats: () => ({
      ...stats,
      size,
      time: shownTime,
      atlas: { page: PAGE, sign: atlases.sign.pages.length, clear: atlases.clear.pages.length, facade: facadePages.pages.length, fill: [atlases.sign.fill(), atlases.clear.fill(), facadePages.fill()].map((f) => +f.toFixed(2)) },
      fonts: { condensed: type.hasCondensed, hand: type.hasHand },
    }),
  };
}
