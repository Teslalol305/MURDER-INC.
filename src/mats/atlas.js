// Atlas pages (CONTRACT 11.2): every sign, poster, graffiti and decal is painted on its own canvas and
// then copied into a shared page, so a whole class of quads draws with one material and a couple of
// textures instead of one of each per quad.
//
// - createPacker(): where things go. An online shelf packer: a rectangle is placed once and never
//   moves, so a result handed out at boot stays valid whatever is asked for later. Pure data, no DOM
//   (test/mats-atlas.test.js).
// - createAtlas(): the pages themselves. A page is an albedo canvas, optionally an emissive canvas at
//   half size, and a small roughness / metalness canvas, all laid out alike so one uv rect addresses
//   the three of them.

import { canvas2d } from './canvas.js';

/** Shelf heights are rounded up to this, so that similar heights share a shelf. */
const SHELF_STEP = 8;

/**
 * @param {number} width   page width in pixels
 * @param {number} height  page height in pixels
 * @param {number} pad     clear pixels kept around every rectangle
 * @param {number} align   the padded box of every rectangle starts and ends on a multiple of this
 *                         (so a layer stored at 1 / align of the size has whole texels per box)
 */
export function createPacker(width, height, pad = 2, align = 1) {
  const pages = []; // {shelves: [{y, h, x}], y: next free row}

  function openPage() {
    const page = { shelves: [], y: 0 };
    pages.push(page);
    return page;
  }

  /**
   * Places a w × h rectangle (pixels). Returns {page, x, y, w, h}: the rectangle itself, inside its
   * padding. A rectangle larger than a page is refused (null): scale it down first (see fit()).
   */
  function place(w, h) {
    const bw = Math.ceil((w + pad * 2) / align) * align;
    const bh = Math.ceil((h + pad * 2) / align) * align;
    if (!(w > 0 && h > 0) || bw > width || bh > height) return null;

    // Best existing shelf: the lowest one that wastes the least height, within reason.
    let best = null;
    let bestPage = 0;
    let bestWaste = Infinity;
    for (let p = 0; p < pages.length; p++) {
      for (const shelf of pages[p].shelves) {
        const waste = shelf.h - bh;
        if (waste < 0 || shelf.x + bw > width) continue;
        if (waste > Math.max(SHELF_STEP, bh * 0.25)) continue;
        if (waste < bestWaste) {
          best = shelf;
          bestPage = p;
          bestWaste = waste;
        }
      }
    }
    if (!best) {
      const step = Math.ceil(SHELF_STEP / align) * align;
      const shelfH = Math.min(height, Math.ceil(bh / step) * step);
      for (let p = 0; p < pages.length && !best; p++) {
        // The last rows of a page may hold a shelf that is not rounded up.
        const room = height - pages[p].y;
        if (room >= bh) {
          best = { y: pages[p].y, h: Math.min(shelfH, room), x: 0 };
          bestPage = p;
        }
      }
      // A page whose rows are all taken may still have room at the end of a taller shelf: better a
      // little waste there than a whole new page (every page is two or three more textures).
      for (let p = 0; p < pages.length && !best; p++) {
        let loose = null;
        for (const shelf of pages[p].shelves) {
          if (shelf.h >= bh && shelf.x + bw <= width && (!loose || shelf.h < loose.h)) loose = shelf;
        }
        if (loose) {
          const rect = { page: p, x: loose.x + pad, y: loose.y + pad, w, h };
          loose.x += bw;
          return rect;
        }
      }
      if (!best) {
        bestPage = pages.length;
        openPage();
        best = { y: 0, h: shelfH, x: 0 };
      }
      pages[bestPage].shelves.push(best);
      pages[bestPage].y = best.y + best.h;
    }
    const rect = { page: bestPage, x: best.x + pad, y: best.y + pad, w, h };
    best.x += bw;
    return rect;
  }

  /** Largest size no bigger than w × h that a page can hold: [w, h] in whole pixels. */
  function fit(w, h) {
    const k = Math.min(1, (width - pad * 2 - align) / w, (height - pad * 2 - align) / h);
    return [Math.max(1, Math.floor(w * k)), Math.max(1, Math.floor(h * k))];
  }

  /** Fraction of the opened pages that is covered by shelves (how full the atlas is). */
  function fill() {
    if (!pages.length) return 0;
    let used = 0;
    for (const page of pages) for (const shelf of page.shelves) used += shelf.x * shelf.h;
    return used / (pages.length * width * height);
  }

  return { width, height, pad, place, fit, fill, pageCount: () => pages.length };
}

/** UV rectangle [u0, v0, u1, v1] of a placed rectangle (v up, as three.js flips canvases). */
export function rectUv(rect, width, height) {
  return [rect.x / width, 1 - (rect.y + rect.h) / height, (rect.x + rect.w) / width, 1 - rect.y / height];
}

/** sRGB grey level (0 … 255) that multiplies a colour by `k` in linear light. */
const linearGain = (k) => Math.round(255 * Math.pow(Math.min(1, Math.max(0, k)), 1 / 2.2));

/**
 * @param {object} o
 *   width, height  page size in pixels
 *   pad            gutter around every picture
 *   opaque         true: the gutter repeats the picture's edge (no dark seams when minified);
 *                  false: the gutter stays clear (soft-edged decals, paper)
 *   emissive       true: pages carry an emissive layer at half size
 *   onPage(page)   called once for every new page: {index, albedo, emissive, orm} canvases
 */
export function createAtlas({ width, height, pad = 4, opaque = false, emissive = false, onPage }) {
  // The roughness layer is a quarter of the size: boxes aligned to 4 pixels own whole texels of it.
  const ORM_SCALE = 1 / 4;
  const packer = createPacker(width, height, pad, 1 / ORM_SCALE);
  const pages = [];

  function page(index) {
    while (pages.length <= index) {
      const albedo = canvas2d(width, height);
      const glow = emissive ? canvas2d(width / 2, height / 2) : null;
      if (glow) {
        glow.fillStyle = '#000';
        glow.fillRect(0, 0, width / 2, height / 2);
      }
      const orm = canvas2d(width * ORM_SCALE, height * ORM_SCALE);
      orm.fillStyle = 'rgb(255,204,0)';
      orm.fillRect(0, 0, orm.canvas.width, orm.canvas.height);
      const made = { index: pages.length, albedo, emissive: glow, orm, user: null };
      pages.push(made);
      made.user = onPage ? onPage(made) : null;
    }
    return pages[index];
  }

  /**
   * Copies a painting into the atlas.
   * @param {HTMLCanvasElement} picture   the albedo (with alpha for the clear classes)
   * @param {object} look  {emissive: canvas | null, glow: 0 … 1 gain on the emissive, roughness, metalness}
   * @returns {{page: object, uv: number[], rect: object}}
   */
  function add(picture, look = {}) {
    const [w, h] = packer.fit(picture.width, picture.height);
    const rect = packer.place(w, h);
    const target = page(rect.page);
    const A = target.albedo;
    if (opaque) {
      // Edge colours under the gutter, then the picture itself on top.
      A.drawImage(picture, rect.x - pad, rect.y - pad, w + pad * 2, h + pad * 2);
    }
    A.drawImage(picture, rect.x, rect.y, w, h);

    if (target.emissive && look.emissive) {
      const E = target.emissive;
      E.save();
      E.beginPath();
      E.rect((rect.x - pad) / 2, (rect.y - pad) / 2, (w + pad * 2) / 2, (h + pad * 2) / 2);
      E.clip();
      E.drawImage(look.emissive, (rect.x - pad) / 2, (rect.y - pad) / 2, (w + pad * 2) / 2, (h + pad * 2) / 2);
      E.drawImage(look.emissive, rect.x / 2, rect.y / 2, w / 2, h / 2);
      const gain = linearGain(look.glow ?? 1);
      if (gain < 255) {
        E.globalCompositeOperation = 'multiply';
        E.fillStyle = `rgb(${gain},${gain},${gain})`;
        E.fillRect((rect.x - pad) / 2, (rect.y - pad) / 2, (w + pad * 2) / 2, (h + pad * 2) / 2);
      }
      E.restore();
    }

    const O = target.orm;
    const r = Math.round(255 * Math.min(1, Math.max(0.04, look.roughness ?? 0.8)));
    const m = Math.round(255 * Math.min(1, Math.max(0, look.metalness ?? 0)));
    O.fillStyle = `rgb(255,${r},${m})`;
    // The padded box starts on a multiple of four pixels: whole texels of the small layer.
    const x0 = Math.floor((rect.x - pad) * ORM_SCALE);
    const y0 = Math.floor((rect.y - pad) * ORM_SCALE);
    O.fillRect(x0, y0, Math.ceil((rect.x + w + pad) * ORM_SCALE) - x0, Math.ceil((rect.y + h + pad) * ORM_SCALE) - y0);

    return { page: target, rect, uv: rectUv(rect, width, height) };
  }

  return { add, pages, fill: packer.fill, width, height };
}

/**
 * Facade pages: each facade's window layer (RGBA overlay, full size) and its glow layer (RGBA, half
 * size) packed alike into shared pages. A facade repeats along its wall, so the gutter left and right
 * of every picture holds the picture's other end (the shader wraps inside the rect, see shader.js)
 * and the gutter below repeats its foot; above the top floor it stays clear (bare wall).
 *
 * add(overlay, emissive) → {page, rect: [u0, v0, du, dv]}  (v up, as three.js flips canvases)
 */
export function createWrapAtlas({ width, height, pad = 8, onPage }) {
  const packer = createPacker(width, height, pad, 2);
  const pages = [];

  function page(index) {
    while (pages.length <= index) {
      const made = { index: pages.length, overlay: canvas2d(width, height), emissive: canvas2d(width / 2, height / 2), user: null };
      pages.push(made);
      made.user = onPage ? onPage(made) : null;
    }
    return pages[index];
  }

  function blit(ctx, picture, x, y, w, h, p) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(x - p, y - p, w + p * 2, h + p * 2);
    ctx.clip();
    for (const dx of [-w, 0, w]) {
      ctx.drawImage(picture, x + dx, y, w, h);
      ctx.drawImage(picture, 0, picture.height - 1, picture.width, 1, x + dx, y + h, w, p);
    }
    ctx.restore();
  }

  function add(overlay, emissive) {
    const [w, h] = packer.fit(overlay.width, overlay.height);
    const rect = packer.place(w, h);
    const target = page(rect.page);
    blit(target.overlay, overlay, rect.x, rect.y, w, h, pad);
    blit(target.emissive, emissive, rect.x / 2, rect.y / 2, w / 2, h / 2, pad / 2);
    return { page: target, rect: [rect.x / width, 1 - (rect.y + h) / height, w / width, h / height] };
  }

  return { add, pages, fill: packer.fill, width, height };
}
