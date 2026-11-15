// Material slots → materials. Surfaces come from the shared library (G.mats.get by catalogue name), so the
// props pick up whatever textures the real library gives those names and merge with the level's own
// meshes. The props add only what the library cannot know about:
//
//   '@decal' / '@lit'   quads cut from the prop atlas (src/props/atlas.js), scene-lit or glowing
//   '@glow'             every unlit lamp lens, tail light and LED: one vertex-coloured HDR material
//   '@grid'             a cut-out lattice (milk crates, wire baskets, gratings, chain nets); builders
//                       ask for '@grid:rrggbb' and the colour is baked into the geometry
//   '@vc'               vertex-coloured paint for small props that must stay one draw call each
//                       ('@vchot' is the same paint glowing with heat)

import {
  AdditiveBlending,
  CanvasTexture,
  Color,
  DoubleSide,
  LinearFilter,
  LinearMipmapLinearFilter,
  MeshBasicMaterial,
  MeshStandardMaterial,
  RepeatWrapping,
  SRGBColorSpace,
  Texture,
} from 'three';
import { ATLAS_H, ATLAS_W, drawAtlas, layoutAtlas } from './atlas.js';
import { RIGGED } from './kit.js';

const LIT_GAIN = 1.7; // lit atlas pictures: bright enough to bloom a little
const GRID_LEVELS = 7; // 64 px down to 1 px

const hasDom = typeof document !== 'undefined';

export function createPropMaterials(G) {
  const mats = G.mats;
  const brand = G.config.brand;
  const cache = new Map();
  const rects = layoutAtlas();
  const small = G.quality && (G.quality.name === 'test' || G.quality.name === 'low');
  const atlasScale = small ? 0.5 : 1;
  let atlasTexture = null;
  let gridTexture = null;

  const tools = {
    drawIPX: (ctx, x, y, h, color) => mats.drawIPX(ctx, x, y, h, color),
    fonts: brand.fonts,
    brand,
  };

  /** The atlas is drawn on first use: by then the level is being built and the fonts have had their chance to load. */
  function atlas() {
    if (!atlasTexture) {
      atlasTexture = mats.canvasTexture(
        ATLAS_W * atlasScale,
        ATLAS_H * atlasScale,
        (ctx) => drawAtlas(ctx, atlasScale, rects, tools),
        { srgb: true, aniso: 8 },
      );
    }
    return atlasTexture;
  }

  /**
   * White lattice on nothing, with hand-made mip levels: the bars never get thinner than a texel, and the
   * smallest levels turn solid, so a wire basket neither sparkles nor vanishes with distance.
   */
  function grid() {
    if (gridTexture) return gridTexture;
    if (!hasDom) return (gridTexture = new Texture());
    const levels = [];
    for (let i = 0, size = 1 << (GRID_LEVELS - 1); i < GRID_LEVELS; i++, size >>= 1) {
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = size;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#fff';
      if (size >= 8) {
        const bar = Math.max(1, Math.round(size * 0.12));
        ctx.fillRect(0, 0, size, bar);
        ctx.fillRect(0, 0, bar, size);
      } else {
        ctx.globalAlpha = 0.66;
        ctx.fillRect(0, 0, size, size);
      }
      levels.push(canvas);
    }
    gridTexture = new CanvasTexture(levels[0]);
    gridTexture.mipmaps = levels;
    gridTexture.generateMipmaps = false;
    gridTexture.minFilter = LinearMipmapLinearFilter;
    gridTexture.magFilter = LinearFilter;
    gridTexture.wrapS = gridTexture.wrapT = RepeatWrapping;
    gridTexture.colorSpace = SRGBColorSpace;
    gridTexture.anisotropy = 4;
    return gridTexture;
  }

  function overlay(material) {
    material.transparent = true;
    material.depthWrite = false;
    material.polygonOffset = true;
    material.polygonOffsetFactor = -2;
    material.polygonOffsetUnits = -2;
    return material;
  }

  function create(slot) {
    if (slot === '@decal') {
      const m = overlay(new MeshStandardMaterial({ map: atlas(), roughness: 0.7, metalness: 0 }));
      m.name = 'props_decal';
      return m;
    }
    if (slot === '@lit') {
      const m = overlay(new MeshBasicMaterial({ map: atlas() }));
      m.color.multiplyScalar(LIT_GAIN);
      m.name = 'props_lit';
      return m;
    }
    if (slot === '@glow') {
      const m = new MeshBasicMaterial({ vertexColors: true });
      m.name = 'props_glow';
      return m;
    }
    if (slot === '@vc' || slot === '@vchot') {
      const m = new MeshStandardMaterial({ vertexColors: true, roughness: 0.6, metalness: 0.15 });
      // The same paint with the heat of a gas fire in it: what a lit explosive wears.
      if (slot === '@vchot') {
        m.emissive.set(0xb8400f);
        m.emissiveIntensity = 0.6;
      }
      m.name = slot === '@vc' ? 'props_vc' : 'props_vc_hot';
      return m;
    }
    if (slot === '@grid') {
      const m = new MeshStandardMaterial({
        map: grid(),
        vertexColors: true, // every lattice colour shares this material (Builder.tintSlot)
        alphaTest: 0.5,
        side: DoubleSide,
        roughness: 0.55,
        metalness: 0.35,
      });
      m.name = 'props_grid';
      return m;
    }
    if (slot === RIGGED) {
      // Stand-in until the prop's rig installs its own material.
      const m = new MeshBasicMaterial({ color: 0x808080 });
      m.name = 'props_rigged';
      return m;
    }
    const bar = slot.indexOf('|');
    return bar < 0 ? mats.get(slot) : mats.get(slot.slice(0, bar), JSON.parse(slot.slice(bar + 1)));
  }

  /**
   * @param {string} slot
   * @param {{paint: string, color?: number, lit?: boolean}} [inst]  what this particular prop asked for
   *        (only the '@paint' and '@glass' slots depend on it)
   */
  // Does the library offer one shared vertex-tinted material per name (CONTRACT 11.2)? The stub does not:
  // then every paint colour is a material of its own, as before.
  let tintable = null;
  function canTint() {
    if (tintable === null) {
      try {
        tintable = !!mats.get('car_paint', { tint: 'vertex' }).vertexColors;
      } catch {
        tintable = false;
      }
    }
    return tintable;
  }

  function resolve(slot, inst = {}) {
    if (slot === '@paint') {
      if (canTint()) return mats.get(inst.paint, { tint: 'vertex' });
      return mats.get(inst.paint, inst.color === undefined ? undefined : { color: inst.color });
    }
    // A parked car with its interior light on: its own catalogue glass, which the library dims by day.
    if (slot === '@glass') return mats.get(inst.lit ? 'glass_car_lit' : 'glass_car');
    let material = cache.get(slot);
    if (!material) cache.set(slot, (material = create(slot)));
    return material;
  }

  /** The IPX billboard face: its own sheet, painted as if lit from the catwalk below. */
  function billboardFace() {
    let material = cache.get('#billboard');
    if (material) return material;
    const w = small ? 512 : 1024;
    const texture = mats.canvasTexture(w, w / 2, (ctx, cw) => {
      const s = cw / 1024;
      ctx.scale(s, s);
      ctx.fillStyle = '#0d0e11';
      ctx.fillRect(0, 0, 1024, 512);
      const markW = mats.drawIPX(ctx, 512, 214, 270, '#f4f2ec');
      ctx.fillStyle = '#f6c21a';
      ctx.fillRect(512 - markW / 2, 388, markW, 6);
      ctx.font = `700 46px ${brand.fonts.ui}`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      if ('letterSpacing' in ctx) ctx.letterSpacing = '14px';
      ctx.fillStyle = '#f4f2ec';
      ctx.fillText(brand.ipx.url, 512 + 7, 440);
      // The lamps sit under the face: bright along the bottom edge, falling off toward the top.
      const shade = ctx.createLinearGradient(0, 0, 0, 512);
      shade.addColorStop(0, 'rgba(0,0,0,0.62)');
      shade.addColorStop(0.55, 'rgba(0,0,0,0.18)');
      shade.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = shade;
      ctx.fillRect(0, 0, 1024, 512);
      const wash = ctx.createLinearGradient(0, 300, 0, 512);
      wash.addColorStop(0, 'rgba(255,214,150,0)');
      wash.addColorStop(1, 'rgba(255,214,150,0.16)');
      ctx.fillStyle = wash;
      ctx.fillRect(0, 300, 1024, 212);
    }, { srgb: true, aniso: 8 });
    material = new MeshBasicMaterial({ map: texture });
    material.color.multiplyScalar(1.5);
    material.name = 'props_billboard';
    cache.set('#billboard', material);
    return material;
  }

  /** A sign from the material library, made once per distinct spec (the library builds a texture per call). */
  function sign(spec) {
    const key = `#sign|${JSON.stringify(spec)}`;
    let result = cache.get(key);
    if (!result) cache.set(key, (result = mats.sign(spec)));
    return result;
  }

  /**
   * Additive, vertex-coloured, unlit: light shafts, flames and glows that the props animate themselves.
   * Every caller gets its own instance so it can fade it without touching anyone else's.
   */
  function additive(color = 0xffffff, opacity = 1) {
    const m = new MeshBasicMaterial({
      color,
      vertexColors: true,
      transparent: true,
      opacity,
      blending: AdditiveBlending,
      depthWrite: false,
      side: DoubleSide,
      fog: false,
    });
    m.forceSinglePass = true;
    m.name = 'props_additive';
    return m;
  }

  /** Own unlit material in one colour, for lamps a prop switches or pulses by itself. */
  function lamp(color, intensity = 2) {
    const m = new MeshBasicMaterial({ color });
    m.color.multiplyScalar(intensity);
    m.userData.base = new Color(color);
    m.name = 'props_lamp';
    return m;
  }

  return {
    resolve,
    canTint,
    rect: (name) => {
      const r = rects.get(name);
      if (!r) throw new Error(`no atlas region '${name}'`);
      return r.uv;
    },
    billboardFace,
    sign,
    additive,
    lamp,
  };
}
