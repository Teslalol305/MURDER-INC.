// Stub materials (CONTRACT 6.1): every catalogue material as a flat-colour MeshStandardMaterial, and
// plain canvas text for signs, posters, graffiti and decals. Same API as the real library, no textures.
//
// Conventions the real module should keep:
//   - get() caches by name + options and always returns a MeshStandardMaterial.
//   - sign / poster / graffiti / decal return {material, w, h} with w and h in metres.
//   - drawIPX(ctx, x, y, h, color): (x, y) is the CENTRE of the mark, h its height in pixels;
//     it returns the width it drew.

import * as THREE from 'three';
import { colors, fonts, ipx } from '../config/brand.js';
import { MATERIALS } from '../config/catalog.js';

const UNKNOWN = { color: 0x808080, roughness: 0.8, metalness: 0 };
const PIXELS_PER_METRE = 128;

// kind → [width, height] in metres
const POSTER_SIZE = { ipx: [0.6, 0.9], show: [0.6, 0.9], wanted: [0.45, 0.6], ad: [1.2, 1.8], torn: [0.5, 0.7] };
const DECAL_SIZE = {
  oil: [1.6, 1.2],
  crack: [2, 0.6],
  manhole: [0.9, 0.9],
  grime: [2, 2],
  scorch: [3, 3],
  bullet: [0.12, 0.12],
  crosswalk: [4, 3],
  arrow: [1.2, 3],
  lane: [0.15, 3],
};

const css = (color, fallback) => (color === undefined || color === null ? fallback : `#${new THREE.Color(color).getHexString()}`);

export function createMats() {
  const cache = new Map();
  const warned = new Set();

  function optionKey(opts) {
    return Object.keys(opts)
      .sort()
      .map((k) => `${k}=${opts[k] && opts[k].isColor ? opts[k].getHex() : opts[k]}`)
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
    const o = { ...def, ...opts };
    material = new THREE.MeshStandardMaterial({
      color: o.color,
      roughness: o.roughness ?? 0.8,
      metalness: o.metalness ?? 0,
      side: o.doubleSide ? THREE.DoubleSide : THREE.FrontSide,
      transparent: !!o.transparent,
      opacity: o.opacity ?? 1,
    });
    if (o.emissive !== undefined) {
      material.emissive.set(o.emissive);
      material.emissiveIntensity = o.emissiveIntensity ?? 1;
    }
    // three.js draws a transparent double-sided material twice (back faces, then front faces) and rebuilds
    // its program parameters for each pass, every frame. One pass is plenty for fences and glass.
    if (o.transparent && o.doubleSide) material.forceSinglePass = true;
    material.name = name;
    cache.set(key, material);
    return material;
  }

  /** Unlit and HDR-bright: anything above 1 after the multiply blooms. */
  function emissive(color, intensity = 2) {
    const key = `emissive|${new THREE.Color(color).getHex()}|${intensity}`;
    let material = cache.get(key);
    if (!material) {
      material = new THREE.MeshBasicMaterial({ color });
      material.color.multiplyScalar(intensity);
      material.name = 'emissive';
      cache.set(key, material);
    }
    return material;
  }

  function canvasTexture(w, h, draw, opts = {}) {
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(2, Math.round(w));
    canvas.height = Math.max(2, Math.round(h));
    draw(canvas.getContext('2d'), canvas.width, canvas.height);
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = opts.srgb === false ? THREE.NoColorSpace : THREE.SRGBColorSpace;
    if (opts.repeat) {
      texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
      texture.repeat.set(opts.repeat[0], opts.repeat[1]);
    }
    texture.anisotropy = opts.aniso ?? 4;
    return texture;
  }

  /** Canvas of w × h metres at a fixed pixel density (clamped so no stub texture gets large). */
  function metreCanvas(w, h, draw) {
    const scale = Math.min(PIXELS_PER_METRE, 1024 / Math.max(w, h));
    return canvasTexture(Math.max(32, w * scale), Math.max(32, h * scale), draw);
  }

  /** Largest bold text of `family` that fits the box, centred on (cx, cy). */
  function fitText(ctx, text, cx, cy, maxW, maxH, family, style = '700') {
    let size = maxH;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    do {
      ctx.font = `${style} ${size}px ${family}`;
      size *= 0.92;
    } while (ctx.measureText(text).width > maxW && size > 6);
    ctx.fillText(text, cx, cy);
  }

  function drawIPX(ctx, x, y, h, color = colors.ink) {
    ctx.save();
    ctx.font = `italic 800 ${h * 0.62}px ${fonts.ui}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const w = ctx.measureText(ipx.wordmark).width + h * 0.9;
    ctx.strokeStyle = ctx.fillStyle = color;
    ctx.lineWidth = Math.max(1, h * 0.06);
    const r = h / 2 - ctx.lineWidth;
    ctx.beginPath(); // the lozenge: two half circles joined by straight edges
    ctx.arc(x - w / 2 + h / 2, y, r, Math.PI / 2, Math.PI * 1.5);
    ctx.arc(x + w / 2 - h / 2, y, r, -Math.PI / 2, Math.PI / 2);
    ctx.closePath();
    ctx.stroke();
    ctx.fillText(ipx.wordmark, x, y + h * 0.03);
    ctx.restore();
    return w;
  }

  /** A quad material that sits on a wall or the ground without z-fighting. */
  function overlay(texture, lit) {
    const common = {
      map: texture,
      transparent: true,
      depthWrite: false,
      polygonOffset: true,
      polygonOffsetFactor: -2,
      polygonOffsetUnits: -2,
    };
    if (!lit) return new THREE.MeshStandardMaterial({ ...common, roughness: 0.9, metalness: 0 });
    const material = new THREE.MeshBasicMaterial(common);
    material.color.multiplyScalar(2.2); // lit signs glow and bloom
    return material;
  }

  function sign(spec = {}) {
    const { text = '', sub = '', w = 2, h = 0.6, style = 'box', lit = true } = spec;
    const neon = style === 'neon';
    const fg = css(spec.fg, neon ? '#ff4fa3' : style === 'street' ? '#ffffff' : colors.ink);
    const bg = neon || style === 'stencil' ? null : css(spec.bg, style === 'street' ? '#1f5a3a' : colors.plate);
    const texture = metreCanvas(w, h, (ctx, cw, ch) => {
      if (bg) {
        ctx.fillStyle = bg;
        ctx.fillRect(0, 0, cw, ch);
      }
      ctx.fillStyle = fg;
      const mainH = sub ? ch * 0.52 : ch * 0.7;
      fitText(ctx, text, cw / 2, sub ? ch * 0.38 : ch / 2, cw * 0.9, mainH, fonts.ui);
      if (sub) fitText(ctx, sub, cw / 2, ch * 0.78, cw * 0.9, ch * 0.24, fonts.ui, '500');
    });
    return { material: overlay(texture, lit && style !== 'stencil' && style !== 'painted'), w, h };
  }

  function facade(spec = {}) {
    return get(spec.base || 'brick_red');
  }

  function poster(kind = 'ad', seed = 0) {
    const [w, h] = POSTER_SIZE[kind] || POSTER_SIZE.ad;
    const key = `poster|${kind}|${seed % 4}`;
    let material = cache.get(key);
    if (!material) {
      const paper = ['#d8d2c0', '#c9b037', '#b8483a', '#3d6a8a'][Math.abs(seed) % 4];
      const texture = metreCanvas(w, h, (ctx, cw, ch) => {
        ctx.fillStyle = paper;
        ctx.fillRect(0, 0, cw, ch);
        ctx.fillStyle = '#111';
        if (kind === 'ipx') drawIPX(ctx, cw / 2, ch / 2, ch * 0.22, '#111');
        else fitText(ctx, kind.toUpperCase(), cw / 2, ch / 2, cw * 0.85, ch * 0.2, fonts.ui);
      });
      material = overlay(texture, false);
      cache.set(key, material);
    }
    return { material, w, h };
  }

  function graffiti(text = 'RULE', seed = 0, color) {
    const w = Math.max(1, text.length * 0.42);
    const h = 0.9;
    const ink = css(color, ['#e2222b', '#f6c21a', '#39d0e0', '#f4f2ec'][Math.abs(seed) % 4]);
    const texture = metreCanvas(w, h, (ctx, cw, ch) => {
      ctx.fillStyle = ink;
      fitText(ctx, text, cw / 2, ch / 2, cw * 0.95, ch * 0.8, fonts.display, 'italic 400');
    });
    return { material: overlay(texture, false), w, h };
  }

  function decal(kind = 'grime') {
    const [w, h] = DECAL_SIZE[kind] || DECAL_SIZE.grime;
    const key = `decal|${kind}`;
    let material = cache.get(key);
    if (!material) {
      const paint = kind === 'crosswalk' || kind === 'arrow' || kind === 'lane';
      const texture = metreCanvas(w, h, (ctx, cw, ch) => {
        ctx.fillStyle = paint ? 'rgba(225,225,215,0.85)' : 'rgba(8,8,10,0.6)';
        if (kind === 'crosswalk') {
          for (let i = 0; i < 6; i++) ctx.fillRect((i + 0.2) * (cw / 6), 0, (cw / 6) * 0.6, ch);
        } else if (kind === 'arrow') {
          ctx.beginPath();
          ctx.moveTo(cw / 2, 0);
          ctx.lineTo(cw, ch * 0.4);
          ctx.lineTo(cw * 0.65, ch * 0.4);
          ctx.lineTo(cw * 0.65, ch);
          ctx.lineTo(cw * 0.35, ch);
          ctx.lineTo(cw * 0.35, ch * 0.4);
          ctx.lineTo(0, ch * 0.4);
          ctx.fill();
        } else if (kind === 'lane' || kind === 'crack') {
          ctx.fillRect(0, kind === 'crack' ? ch * 0.4 : 0, cw, kind === 'crack' ? ch * 0.2 : ch);
        } else {
          ctx.beginPath();
          ctx.ellipse(cw / 2, ch / 2, cw * 0.48, ch * 0.48, 0, 0, Math.PI * 2);
          ctx.fill();
        }
      });
      material = overlay(texture, false);
      cache.set(key, material);
    }
    return { material, w, h };
  }

  return {
    get,
    emissive,
    sign,
    facade,
    poster,
    graffiti,
    decal,
    drawIPX,
    canvasTexture,
    names: () => Object.keys(MATERIALS),
    update() {},
  };
}
