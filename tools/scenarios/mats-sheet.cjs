#!/usr/bin/env node
// Contact sheets of the generated textures, straight from the canvases: no WebGL, so it runs in a few
// seconds on any machine. A standalone script, not a shot.cjs scenario.
//
//   node tools/scenarios/mats-sheet.cjs                     every sheet at 512 px
//   node tools/scenarios/mats-sheet.cjs signs posters       some sheets
//   node tools/scenarios/mats-sheet.cjs surfaces --tex 1024 --only brick_red,asphalt
//
// Sheets: surfaces (albedo, tiled albedo, normal, roughness per material), signs (albedo + glow),
// posters, graffiti, decals, facades (wall, window layer and glow composited), ipx (the wordmark).
// Output: shots/mats/sheet-<name>.png

'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { build } = require('esbuild');

const ROOT = path.resolve(__dirname, '..', '..');
const OUT = path.join(ROOT, 'shots', 'mats');
const ALL = ['surfaces', 'signs', 'posters', 'graffiti', 'decals', 'facades', 'ipx'];

// Runs in the page: a stand-in for G with everything the mats module reads, then the sheet painters.
const ENTRY = `
import * as THREE from 'three';
import * as brand from './src/config/brand.js';
import * as catalog from './src/config/catalog.js';
import * as look from './src/config/look.js';
import * as text from './src/config/text.js';
import { createMats } from './src/mats.js';

window.makeMats = async (size) => {
  const G = {
    THREE,
    params: { tex: String(size) },
    events: { on() {} },
    time: { t: 0 },
    quality: { name: 'high' },
    config: { brand, catalog, look, text },
    renderer: { capabilities: { getMaxAnisotropy: () => 8 } },
  };
  window.G = G;
  window.mats = await createMats(G);
  window.THREE = THREE;
  return window.mats.stats();
};
`;

/** Runs in the page: lays out labelled cells on one canvas and returns it as a PNG data URL. */
function pageSheet(kind, opts) {
  const { mats, G } = window;
  const cells = []; // {label, w, h, draw(ctx, x, y, w, h)}
  const image = (texture) => (texture && texture.image && texture.image.width > 1 ? texture.image : null);

  /** A canvas for any texture image: DataTexture bytes are copied to one first. */
  function drawable(img) {
    if (img instanceof HTMLCanvasElement) return img;
    const canvas = document.createElement('canvas');
    canvas.width = img.width;
    canvas.height = img.height;
    const c = canvas.getContext('2d');
    const data = c.createImageData(img.width, img.height);
    data.data.set(img.data);
    c.putImageData(data, 0, 0);
    return canvas;
  }

  /** Draws a texture's image (canvas or raw RGBA data) into a rect. */
  function put(ctx, texture, x, y, w, h, tiles = 1) {
    const img = image(texture);
    if (!img) {
      ctx.fillStyle = '#222';
      ctx.fillRect(x, y, w, h);
      return;
    }
    const source = drawable(img);
    for (let j = 0; j < tiles; j++) for (let i = 0; i < tiles; i++) ctx.drawImage(source, x + (i * w) / tiles, y + (j * h) / tiles, w / tiles, h / tiles);
  }
  /** The top-left w × h pixels of a texture, unscaled. */
  const crop = (ctx, texture, x, y, w, h) => {
    const img = image(texture);
    const cw = Math.min(w, img.width);
    const ch = Math.min(h, img.height);
    ctx.drawImage(drawable(img), 0, 0, cw, ch, x, y, cw, ch);
  };
  const checker = (ctx, x, y, w, h, a = '#5b4a44', b = '#6b5850') => {
    for (let j = 0; j * 16 < h; j++) {
      for (let i = 0; i * 16 < w; i++) {
        ctx.fillStyle = (i + j) % 2 ? a : b;
        ctx.fillRect(x + i * 16, y + j * 16, Math.min(16, w - i * 16), Math.min(16, h - j * 16));
      }
    }
  };

  if (kind === 'surfaces') {
    const names = opts.only && opts.only.length ? opts.only : mats.names();
    const S = opts.cell || 200;
    for (const name of names) {
      const m = mats.get(name);
      const aspect = image(m.map) ? m.map.image.height / m.map.image.width : 1;
      const w = aspect > 1 ? S / aspect : S;
      const h = aspect > 1 ? S : S * aspect;
      const tintCss = '#' + m.color.clone().convertLinearToSRGB().getHexString();
      cells.push({
        label: `${name}  ${image(m.map) ? m.map.image.width + '×' + m.map.image.height : 'flat'}  tile ${(1 / m.map.repeat.x).toFixed(2)} m  r×${m.roughness.toFixed(2)}`,
        w: w * 4 + 12,
        h,
        draw(ctx, x, y) {
          put(ctx, m.map, x, y, w, h);
          // The material colour multiplies the albedo: show the tinted result, tiled 2 × 2
          // (or, with --crop, a piece of it and of the normal map pixel for pixel).
          if (opts.crop && image(m.map)) crop(ctx, m.map, x + w + 4, y, w, h);
          else put(ctx, m.map, x + w + 4, y, w, h, 2);
          ctx.globalCompositeOperation = 'multiply';
          ctx.fillStyle = tintCss;
          ctx.fillRect(x + w + 4, y, w, h);
          ctx.globalCompositeOperation = 'source-over';
          if (opts.crop && image(m.normalMap)) crop(ctx, m.normalMap, x + (w + 4) * 2, y, w, h);
          else put(ctx, m.normalMap, x + (w + 4) * 2, y, w, h);
          put(ctx, m.roughnessMap, x + (w + 4) * 3, y, w, h);
        },
      });
    }
  } else if (kind === 'signs') {
    const s = G.config.text.world.storefronts;
    const specs = opts.specs || [
      { text: s[0], w: 7.6, h: 0.9, style: 'neon', fg: 0x35e0ff },
      { text: 'OPEN', sub: '24 HRS', w: 1.6, h: 0.9, style: 'neon', fg: 0xff3030, glow: 0x55ff8a },
      { text: s[9], w: 3.6, h: 0.7, style: 'neon', fg: 0xff3d9a },
      { text: 'IPX', w: 1.6, h: 0.7, style: 'neon', fg: 0xf6c21a },
      { text: G.config.text.world.shop, w: 7.6, h: 1.1, style: 'box', bg: 0x101113, fg: 0xf6c21a },
      { text: s[5], sub: 'COLD BEER · LOTTO', w: 5.6, h: 1.0, style: 'box' },
      { text: 'IPX', w: 1.8, h: 0.6, style: 'box', bg: 0xf6c21a, fg: 0x0d0e11 },
      { text: s[2], sub: 'WE BUY · WE LOAN', w: 5.6, h: 0.9, style: 'painted' },
      { text: s[1], w: 5.6, h: 0.8, style: 'painted', bg: 0x1b3565, fg: 0xf2c21a, lit: true },
      { text: s[3], w: 5.6, h: 0.8, style: 'painted' },
      { text: s[4], w: 3.8, h: 0.6, style: 'awning' },
      { text: s[6], sub: 'WALK-INS WELCOME', w: 3.8, h: 0.7, style: 'awning', bg: 0x1f6b6b },
      { text: s[7], w: 4, h: 0.9, style: 'awning', bg: 0x1f4f9a, lit: false },
      { text: 'Jamaica', sub: 'Av', w: 1.1, h: 0.24, style: 'street' },
      { text: '205', sub: 'St', w: 0.8, h: 0.24, style: 'street' },
      { text: 'Hollis', sub: 'Av', w: 1.0, h: 0.24, style: 'street' },
      { text: 'NO PARKING', sub: 'LOADING ZONE', w: 2.4, h: 0.9, style: 'stencil', fg: 0xf2c21a },
      { text: 'KEEP CLEAR', w: 2.4, h: 0.5, style: 'stencil' },
      { text: 'IPX', w: 1.6, h: 0.7, style: 'stencil', fg: 0xf4f2ec },
      { text: 'Jamaica Av', sub: 'Hollis · Queens', w: 2.6, h: 0.6, style: 'plate', bullet: '1', bulletColor: 0xe2222b },
      { text: 'Downtown & Brooklyn', w: 3.2, h: 0.5, style: 'plate', bullet: 'J', bulletColor: 0x9a6a2a },
      { text: 'Exit', w: 1.2, h: 0.5, style: 'plate' },
      { text: 'IPX', sub: 'IPX.EXCHANGE', w: 2.6, h: 1.0, style: 'plate', lit: false },
      { text: s[8], w: 3, h: 0.6, style: 'box', bg: 0x1f5a3a, fg: 0xf2c21a },
    ];
    const ppm = opts.ppm || 90;
    for (const spec of specs) {
      const sign = mats.sign(spec);
      const m = sign.material;
      const w = sign.w * ppm;
      const h = sign.h * ppm;
      const lit = image(m.emissiveMap);
      cells.push({
        label: `${spec.style}${spec.lit === false ? ' unlit' : ''}  ${image(m.map).width}×${image(m.map).height}  glow ${lit ? m.emissiveIntensity : 0}`,
        w: w * 2 + 8,
        h,
        draw(ctx, x, y) {
          checker(ctx, x, y, w, h);
          put(ctx, m.map, x, y, w, h);
          ctx.fillStyle = '#000';
          ctx.fillRect(x + w + 8, y, w, h);
          if (lit) put(ctx, m.emissiveMap, x + w + 8, y, w, h);
        },
      });
    }
  } else if (kind === 'posters') {
    const ppm = opts.ppm || 300;
    for (const k of ['ipx', 'show', 'wanted', 'ad', 'torn']) {
      for (let v = 0; v < 4; v++) {
        if ((k === 'wanted' || k === 'torn') && v > 2) continue;
        const p = mats.poster(k, v);
        const scale = k === 'ad' ? 0.5 : 1;
        cells.push({
          label: `${k} ${v}  ${p.w}×${p.h} m`,
          w: p.w * ppm * scale,
          h: p.h * ppm * scale,
          draw(ctx, x, y, w, h) {
            checker(ctx, x, y, w, h);
            put(ctx, p.material.map, x, y, w, h);
          },
        });
      }
    }
  } else if (kind === 'graffiti') {
    const ppm = opts.ppm || 150;
    const tags = opts.tags || [['RULE', 2], ['RULE', 0], ['RULE', 1], ['VULTURES', 0, 0xe2222b], ['HOLLIS', 1], ['IPX', 1, 0xf6c21a], ['QNS', 2, 0x39d0e0], ['205', 0], ['JA', 1, 0xf4f2ec], ['KINGS', 2, 0xff3d9a], ['INC', 0, 0x55ff8a], ['MURDER INC', 2, 0xe2222b], ['VULTURES', 1], ['Rule', 3]];
    for (const [t, seed, color] of tags) {
      const g = mats.graffiti(t, seed, color);
      cells.push({
        label: `${t} seed ${seed}  ${g.w.toFixed(2)}×${g.h} m`,
        w: g.w * ppm,
        h: g.h * ppm,
        draw(ctx, x, y, w, h) {
          checker(ctx, x, y, w, h);
          put(ctx, g.material.map, x, y, w, h);
        },
      });
    }
  } else if (kind === 'decals') {
    const kinds = ['oil', 'crack', 'manhole', 'grime', 'scorch', 'bullet', 'crosswalk', 'arrow', 'lane', 'lane_yellow', 'puddle'];
    for (const k of kinds) {
      for (let v = 0; v < 3; v++) {
        const d = mats.decal(k, v);
        if (v > 0 && d.material === mats.decal(k, 0).material) continue;
        const img = image(d.material.map);
        const scale = Math.min(1, 240 / Math.max(img.width, img.height));
        cells.push({
          label: `${k} ${v}  ${d.w}×${d.h} m  ${img.width}×${img.height}`,
          w: Math.max(60, img.width * scale),
          h: Math.max(60, img.height * scale),
          draw(ctx, x, y, w, h) {
            checker(ctx, x, y, w, h, '#26272a', '#2e2f33');
            put(ctx, d.material.map, x, y, w, h);
          },
        });
      }
    }
  } else if (kind === 'facades') {
    const specs = opts.specs || [
      { base: 'brick_red', floors: 4, bays: 6, floorH: 3.2, lit: 0.35, seed: 3, shopfront: true },
      { base: 'brick_tan', floors: 5, bays: 5, floorH: 3, lit: 0.2, seed: 8, w: 16 },
      { base: 'brick_brown', floors: 3, bays: 5, floorH: 3.4, lit: 0.5, seed: 21, shopfront: true },
      { base: 'brick_painted', floors: 2, bays: 3, floorH: 3.2, lit: 0.34, seed: 5 },
      { base: 'stucco', floors: 3, bays: 4, floorH: 3.2, lit: 0.25, seed: 11, shopfront: true },
      { base: 'cinder', floors: 2, bays: 4, floorH: 3.6, lit: 0.1, seed: 2 },
    ];
    const ppm = opts.ppm || 36;
    for (const spec of specs) {
      const m = mats.facade(spec);
      const f = m.userData.facade;
      const tintCss = '#' + m.color.clone().convertLinearToSRGB().getHexString();
      cells.push({
        label: `${spec.base} ${f.floors}×${f.bays} seed ${spec.seed}${spec.shopfront ? ' shop' : ''}  ${f.w}×${f.h} m  overlay ${f.overlay.image.width}×${f.overlay.image.height}`,
        w: f.w * ppm,
        h: (f.h + 1) * ppm,
        draw(ctx, x, y, w, h) {
          // The tiling wall at its real scale, then the window layer, then the glow added on top.
          const tile = (1 / m.map.repeat.x) * ppm;
          ctx.save();
          ctx.beginPath();
          ctx.rect(x, y, w, h);
          ctx.clip();
          for (let ty = y + h - tile; ty > y - tile; ty -= tile) for (let tx = x; tx < x + w; tx += tile) ctx.drawImage(m.map.image, tx, ty, tile, tile);
          ctx.globalCompositeOperation = 'multiply';
          ctx.fillStyle = tintCss;
          ctx.fillRect(x, y, w, h);
          ctx.fillStyle = '#5a5e70'; // night: everything that is not lit sits in cool half-light
          ctx.fillRect(x, y, w, h);
          ctx.globalCompositeOperation = 'source-over';
          const top = y + ppm;
          ctx.globalAlpha = 0.55;
          ctx.drawImage(f.overlay.image, x, top, w, h - ppm);
          ctx.globalAlpha = 1;
          ctx.globalCompositeOperation = 'lighter';
          ctx.drawImage(m.emissiveMap.image, x, top, w, h - ppm);
          ctx.restore();
        },
      });
      cells.push({
        label: 'window layer alone',
        w: f.w * ppm * 0.6,
        h: f.h * ppm * 0.6,
        draw(ctx, x, y, w, h) {
          checker(ctx, x, y, w, h);
          ctx.drawImage(f.overlay.image, x, y, w, h);
        },
      });
    }
  } else if (kind === 'ipx') {
    for (const [h, fg, bg] of [[12, '#f4f2ec', '#0f1114'], [20, '#f4f2ec', '#0f1114'], [40, '#f6c21a', '#0f1114'], [80, '#0f1114', '#f6c21a'], [160, '#f4f2ec', '#6b1218']]) {
      cells.push({
        label: `drawIPX h=${h}`,
        w: h * 3.4,
        h: h * 1.5,
        draw(ctx, x, y, w, hh) {
          ctx.fillStyle = bg;
          ctx.fillRect(x, y, w, hh);
          const drawn = mats.drawIPX(ctx, x + w / 2, y + hh / 2, h, fg);
          ctx.fillStyle = '#888';
          ctx.fillRect(x + w / 2 - drawn / 2, y + hh - 2, drawn, 1); // the width it reports
        },
      });
    }
  }

  // Shelf-pack the cells left to right, top to bottom.
  const W = opts.width || 1500;
  const PAD = 10;
  const LABEL = 14;
  let x = PAD;
  let y = PAD;
  let rowH = 0;
  for (const c of cells) {
    if (x + c.w + PAD > W && x > PAD) {
      x = PAD;
      y += rowH + LABEL + PAD;
      rowH = 0;
    }
    c.x = x;
    c.y = y;
    x += c.w + PAD;
    rowH = Math.max(rowH, c.h);
  }
  const sheet = document.createElement('canvas');
  sheet.width = W;
  sheet.height = y + rowH + LABEL + PAD;
  const ctx = sheet.getContext('2d');
  ctx.fillStyle = '#16171a';
  ctx.fillRect(0, 0, sheet.width, sheet.height);
  ctx.font = '11px monospace';
  ctx.textBaseline = 'top';
  for (const c of cells) {
    ctx.save();
    c.draw(ctx, c.x, c.y, c.w, c.h);
    ctx.restore();
    ctx.fillStyle = '#c8c6c0';
    ctx.fillText(c.label, c.x, c.y + c.h + 2, c.w);
  }
  return sheet.toDataURL('image/png');
}

async function main() {
  const args = process.argv.slice(2);
  const opts = { tex: 512, only: [], sheets: [] };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--tex') opts.tex = Number(args[++i]);
    else if (args[i] === '--only') opts.only = args[++i].split(',').filter(Boolean);
    else if (args[i] === '--cell') opts.cell = Number(args[++i]);
    else if (args[i] === '--width') opts.width = Number(args[++i]);
    else if (args[i] === '--ppm') opts.ppm = Number(args[++i]);
    else if (args[i] === '--crop') opts.crop = true;
    else opts.sheets.push(args[i]);
  }
  const sheets = opts.sheets.length ? opts.sheets : ALL;

  const bundle = await build({
    stdin: { contents: ENTRY, resolveDir: ROOT, loader: 'js' },
    bundle: true,
    format: 'iife',
    write: false,
    logLevel: 'warning',
  });

  const { chromium } = require('playwright');
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
    page.on('console', (msg) => {
      if (msg.type() === 'error' || msg.type() === 'warning') console.error(`[page ${msg.type()}] ${msg.text()}`);
    });
    page.on('pageerror', (err) => console.error(`[page error] ${err.message}`));
    await page.setContent('<!doctype html><html><body></body></html>');
    await page.addScriptTag({ content: bundle.outputFiles[0].text });
    const t0 = Date.now();
    const stats = await page.evaluate((size) => window.makeMats(size), opts.tex);
    fs.mkdirSync(OUT, { recursive: true });
    for (const kind of sheets) {
      const url = await page.evaluate(([fn, k, o]) => (0, eval)(`(${fn})`)(k, o), [pageSheet.toString(), kind, opts]);
      const file = path.join(OUT, `sheet-${kind}.png`);
      fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
      console.log(`${path.relative(ROOT, file)}`);
    }
    console.log(`painted in ${Date.now() - t0} ms: ${JSON.stringify(await page.evaluate(() => window.mats.stats()))} (first stats ${JSON.stringify(stats)})`);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(`mats-sheet: ${err.stack || err.message}`);
  process.exitCode = 1;
});
