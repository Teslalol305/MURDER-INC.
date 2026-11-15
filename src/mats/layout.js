// Facade layout: where the windows, doors and shop units of a building wall go, and which windows
// are lit. Pure data from a spec and a seed (no DOM): the painter in facade.js draws exactly this, and
// test/mats-layout.test.js checks it.
//
// All positions are in metres on the wall: x from its left edge, y up from the ground.

import { prng } from './noise.js';

const clamp = (x, min, max) => (x < min ? min : x > max ? max : x);

const FRAMES = [0xe6e2d6, 0x3a2a20, 0x1f3a2c, 0x23262a, 0x8a8478];
const STONES = [0xb6ae9e, 0x8f8a80, 0x6e4e3e];
const FASCIAS = [0x1a2f26, 0x4a1418, 0x15171b, 0x1a2640, 0x5c5446];

/** Fisher–Yates with our own generator. */
function shuffle(list, rand) {
  for (let i = list.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    const t = list[i];
    list[i] = list[j];
    list[j] = t;
  }
  return list;
}

/**
 * Normalises a facade spec: every field present, in range, with the derived sizes.
 * spec: {base, floors, bays, floorH, lit, seed, shopfront, bayW, w}
 *   w     total wall width in metres: the bays divide it exactly (takes precedence over bayW)
 *   bayW  width of one bay (default 3 m)
 */
export function facadeSpec(spec = {}) {
  const floors = clamp(Math.round(spec.floors ?? 3), 1, 12);
  const bays = clamp(Math.round(spec.bays ?? 4), 1, 24);
  const floorH = clamp(+spec.floorH || 3.2, 2.2, 6);
  const bayW = clamp(spec.w > 0 ? spec.w / bays : +spec.bayW || 3, 1.4, 9);
  return {
    base: typeof spec.base === 'string' ? spec.base : 'brick_red',
    floors,
    bays,
    floorH,
    bayW,
    lit: clamp(spec.lit ?? 0.25, 0, 1),
    seed: Math.floor(+spec.seed || 0),
    shopfront: !!spec.shopfront,
    w: bays * bayW,
    h: floors * floorH,
  };
}

/** Cache / identity key of a normalised spec. */
export const facadeKey = (s) => `facade|${s.base}|${s.floors}|${s.bays}|${s.floorH}|${s.bayW}|${s.lit}|${s.seed}|${s.shopfront ? 1 : 0}`;

/**
 * @param {object} s  a normalised spec (facadeSpec)
 * @returns {{
 *   style: {frame: number, stone: number, fascia: number, lintel: 'stone'|'brick'|'steel', paired: boolean, cornice: boolean},
 *   windows: {floor, bay, x, y, w, h, state: 'dark'|'warm'|'tv', blind, curtain, ac, bars}[],
 *   doors: {bay, x, y, w, h}[],
 *   units: {bay, x, w, kind: 'gate'|'glass'|'lit'}[],      shop units of the ground floor
 * }}
 */
export function facadeLayout(s) {
  const rand = prng(0x5eed ^ Math.imul(s.seed + 1, 2654435761));
  const style = {
    frame: FRAMES[Math.floor(rand() * FRAMES.length)],
    stone: STONES[Math.floor(rand() * STONES.length)],
    fascia: FASCIAS[Math.floor(rand() * FASCIAS.length)],
    lintel: ['stone', 'stone', 'brick', 'steel'][Math.floor(rand() * 4)],
    paired: s.bayW >= 3.4 && rand() < 0.4,
    cornice: true,
  };

  // One window opening per bay (or a pair of narrow ones), the same on every upper floor.
  const winH = Math.min(s.floorH * 0.56, 1.95);
  const sill = (s.floorH - winH) * 0.44;
  const winW = style.paired ? Math.min(s.bayW * 0.24, 0.85) : Math.min(s.bayW * 0.4, 1.25);
  const offsets = style.paired ? [-(winW / 2 + 0.22), winW / 2 + 0.22] : [0];

  const windows = [];
  const doors = [];
  const units = [];
  const doorBay = Math.floor(rand() * s.bays);

  for (let floor = 0; floor < s.floors; floor++) {
    const ground = floor === 0;
    if (ground && s.shopfront) continue;
    for (let bay = 0; bay < s.bays; bay++) {
      const centre = (bay + 0.5) * s.bayW;
      if (ground && bay === doorBay) {
        const w = Math.min(1.1, s.bayW * 0.5);
        doors.push({ bay, x: centre - w / 2, y: 0, w, h: Math.min(2.3, s.floorH - 0.5) });
        continue;
      }
      for (const dx of offsets) {
        windows.push({
          floor,
          bay,
          x: centre + dx - winW / 2,
          y: floor * s.floorH + sill,
          w: winW,
          h: winH,
          state: 'dark',
          blind: rand() < 0.45 ? 0.15 + rand() * 0.7 : 0,
          curtain: rand() < 0.3,
          ac: !ground && rand() < 0.16,
          bars: ground,
        });
      }
    }
  }

  // Exactly round(lit × n) windows are lit, most of them warm, a few by a television.
  const order = shuffle(windows.map((_, i) => i), rand);
  const litCount = Math.round(s.lit * windows.length);
  for (let i = 0; i < litCount; i++) windows[order[i]].state = rand() < 0.22 ? 'tv' : 'warm';

  if (s.shopfront) {
    // Ground floor: shop units between piers, most of them shuttered at this hour, and the street
    // door to the flats above squeezed in beside one of them.
    const pier = 0.32;
    for (let bay = 0; bay < s.bays; bay++) {
      let x = bay * s.bayW + pier / 2;
      let w = s.bayW - pier;
      if (bay === doorBay && w > 2.4) {
        doors.push({ bay, x, y: 0, w: 1.0, h: Math.min(2.25, s.floorH - 1.1) });
        x += 1.0 + pier * 0.6;
        w -= 1.0 + pier * 0.6;
      }
      const roll = rand();
      const kind = roll < 0.58 ? 'gate' : roll < 0.58 + 0.42 * Math.min(1, s.lit * 1.6) ? 'lit' : 'glass';
      units.push({ bay, x, w, kind });
    }
  }

  return { style, windows, doors, units, shop: s.shopfront ? { base: 0.45, top: s.floorH - 0.95, fascia: [s.floorH - 0.88, s.floorH - 0.2] } : null };
}
