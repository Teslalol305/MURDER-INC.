// Posters and graffiti: transparent quads that go on walls. All content is invented for this block;
// the only brand is the IPX wordmark over its address.
//
//   posters   'ipx' | 'show' | 'wanted' | 'ad' | 'torn', a handful of variants each (by seed)
//   graffiti  any text as a marker tag, a spray tag or a bubble-letter throw-up (by seed)

import { canvas2d, css, erase, fillTiled, luma, mixHex, shade, stain, toHex } from './canvas.js';
import { prng } from './noise.js';

const TAU = Math.PI * 2;

/** kind → [width, height] in metres. */
export const POSTER_SIZE = { ipx: [0.6, 0.9], show: [0.6, 0.9], wanted: [0.45, 0.6], ad: [1.2, 1.8], torn: [0.5, 0.7] };
/** Distinct paintings per kind; seeds wrap around. */
export const POSTER_VARIANTS = { ipx: 4, show: 4, wanted: 3, ad: 4, torn: 3 };

const POSTER_PPM = { 256: 150, 512: 200, 1024: 360 };
const GRAFFITI_PPM = { 256: 90, 512: 128, 1024: 220 };
const SPRAY = [0xe2222b, 0xf6c21a, 0x39d0e0, 0xf4f2ec, 0xff3d9a, 0x55ff8a, 0x9a5cff, 0xff7a1a];

const INK = 0x0d0e11;
const PAPER = 0xf1ede2;

export function createPaperPainter(env) {
  const { size, type, bank, brand, drawIPX, ipxWidth } = env;
  const GOLD = toHex(brand.colors.gold);
  const RED = toHex(brand.colors.red);
  const OXBLOOD = toHex(brand.colors.oxblood);

  /** One centred line of type; `ink` is its height as a fraction of the canvas height. */
  function line(A, cw, ch, text, y, ink, color, face = 'display', spacing = 0, maxW = 0.84) {
    const fitted = type.fit(A, text, face, cw * maxW, ch * ink, spacing);
    type.draw(A, text, cw / 2, ch * y, fitted, { fill: css(color) });
    return fitted;
  }

  function rule(A, cw, ch, y, color, thickness = 0.006) {
    A.fillStyle = css(color);
    A.fillRect(cw * 0.08, ch * y, cw * 0.84, Math.max(1, ch * thickness));
  }

  function star(A, x, y, r, points, inner, color) {
    A.fillStyle = css(color);
    A.beginPath();
    for (let i = 0; i < points * 2; i++) {
      const a = (i / (points * 2)) * TAU - Math.PI / 2;
      const rr = i % 2 ? r * inner : r;
      A.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr);
    }
    A.closePath();
    A.fill();
  }

  /** Paste, weather and rough handling: makes a fresh print belong on the wall. */
  function age(A, cw, ch, rand, amount = 1) {
    fillTiled(A, bank.grey('ridges'), 1.3, 1.3 * (ch / cw), { mode: 'soft-light', alpha: 0.55 * amount, ox: rand(), oy: rand() });
    fillTiled(A, bank.grey('clouds'), 1, ch / cw, { mode: 'multiply', alpha: 0.3 * amount, ox: rand(), oy: rand() });
    stain(A, bank.mask('streaks', 0.55, 0.95), 'rgb(40,34,26)', { alpha: 0.3 * amount, ox: rand() });
    // Torn and nibbled edges.
    A.save();
    A.globalCompositeOperation = 'destination-out';
    const bite = Math.max(2, cw * 0.02);
    const count = Math.round(28 * amount);
    for (let i = 0; i < count; i++) {
      const side = Math.floor(rand() * 4);
      const t = rand();
      const x = side === 0 ? 0 : side === 1 ? cw : t * cw;
      const y = side === 2 ? 0 : side === 3 ? ch : t * ch;
      A.beginPath();
      A.ellipse(x, y, bite * (0.4 + rand() * 1.6), bite * (0.4 + rand() * 1.6), rand() * 3, 0, TAU);
      A.fill();
    }
    // One corner has lifted and gone.
    if (rand() < 0.6 * amount) {
      const c = cw * (0.08 + rand() * 0.14);
      const right = rand() < 0.5;
      A.beginPath();
      A.moveTo(right ? cw : 0, 0);
      A.lineTo(right ? cw - c : c, 0);
      A.lineTo(right ? cw : 0, c * (0.7 + rand() * 0.8));
      A.fill();
    }
    A.restore();
  }

  // ---------------------------------------------------------------------------------------------
  // Posters
  // ---------------------------------------------------------------------------------------------

  /** The IPX wordmark over IPX.EXCHANGE, nothing else. */
  function ipxPoster(A, cw, ch, v) {
    const [paper, ink] = [[INK, GOLD], [GOLD, INK], [PAPER, INK], [OXBLOOD, PAPER]][v];
    A.fillStyle = css(paper);
    A.fillRect(0, 0, cw, ch);
    rule(A, cw, ch, 0.07, ink);
    const h = Math.min(ch * 0.3, (cw * 0.8 * 100) / ipxWidth(A, 100));
    drawIPX(A, cw / 2, ch * 0.42, h, css(ink));
    line(A, cw, ch, brand.ipx.url, 0.68, 0.034, ink, 'ui', 0.2, 0.74);
    rule(A, cw, ch, 0.92, ink);
  }

  /** Gig and street-event bills: invented nights on the block. */
  function showPoster(A, cw, ch, v) {
    if (v === 0) {
      A.fillStyle = css(INK);
      A.fillRect(0, 0, cw, ch);
      A.fillStyle = css(GOLD);
      A.fillRect(0, ch * 0.3, cw, ch * 0.34);
      line(A, cw, ch, 'ONE NIGHT ONLY', 0.15, 0.05, PAPER, 'ui', 0.16);
      rule(A, cw, ch, 0.225, PAPER);
      line(A, cw, ch, 'RULE', 0.47, 0.27, INK, 'display', 0.02, 0.86);
      line(A, cw, ch, 'HOLLIS · QUEENS', 0.73, 0.05, GOLD, 'display', 0.06);
      drawIPX(A, cw / 2, ch * 0.86, ch * 0.055, css(PAPER));
      line(A, cw, ch, brand.ipx.url, 0.935, 0.018, PAPER, 'ui', 0.2, 0.5);
    } else if (v === 1) {
      A.fillStyle = css(0xc9281e);
      A.fillRect(0, 0, cw, ch);
      // Sunburst behind the title.
      A.save();
      A.translate(cw / 2, ch * 0.4);
      for (let i = 0; i < 24; i++) {
        A.rotate(TAU / 24);
        A.fillStyle = i % 2 ? 'rgba(241,230,200,0.16)' : 'rgba(0,0,0,0.12)';
        A.beginPath();
        A.moveTo(0, 0);
        A.lineTo(cw, -cw * 0.13);
        A.lineTo(cw, cw * 0.13);
        A.fill();
      }
      A.restore();
      line(A, cw, ch, 'BLOCK', 0.29, 0.17, 0xf1e6c8);
      line(A, cw, ch, 'PARTY', 0.5, 0.17, 0xf1e6c8);
      A.fillStyle = css(INK);
      A.fillRect(0, ch * 0.66, cw, ch * 0.12);
      line(A, cw, ch, 'SATURDAY · SUNDOWN', 0.72, 0.045, 0xf6c21a, 'display', 0.05);
      line(A, cw, ch, 'DJs · OPEN MIC · ALL AGES', 0.86, 0.026, 0xf1e6c8, 'ui', 0.1);
    } else if (v === 2) {
      A.fillStyle = css(0x1c3a6e);
      A.fillRect(0, 0, cw, ch);
      // A cassette, drawn large.
      const x = cw * 0.16;
      const y = ch * 0.12;
      const w = cw * 0.68;
      const h = w * 0.62;
      A.fillStyle = css(PAPER);
      A.fillRect(x, y, w, h);
      A.fillStyle = css(0x1c3a6e);
      A.fillRect(x + w * 0.1, y + h * 0.2, w * 0.8, h * 0.42);
      for (const cx of [0.32, 0.68]) {
        A.fillStyle = css(PAPER);
        A.beginPath();
        A.arc(x + w * cx, y + h * 0.41, h * 0.13, 0, TAU);
        A.fill();
        A.fillStyle = css(INK);
        A.beginPath();
        A.arc(x + w * cx, y + h * 0.41, h * 0.05, 0, TAU);
        A.fill();
      }
      line(A, cw, ch, 'THE HOLLIS', 0.62, 0.085, PAPER);
      line(A, cw, ch, 'SESSIONS', 0.74, 0.1, 0xf6c21a);
      rule(A, cw, ch, 0.82, PAPER);
      line(A, cw, ch, 'LIVE ON TAPE · VOL. 3', 0.88, 0.028, PAPER, 'ui', 0.12);
    } else {
      A.fillStyle = css(0xf2c21a);
      A.fillRect(0, 0, cw, ch);
      // A record in its sleeve.
      for (const [r, c] of [[0.36, INK], [0.3, 0x1c1c20], [0.24, INK], [0.11, 0xc9281e], [0.016, 0xf2c21a]]) {
        A.fillStyle = css(c);
        A.beginPath();
        A.arc(cw / 2, ch * 0.34, cw * r, 0, TAU);
        A.fill();
      }
      line(A, cw, ch, 'TAPE SWAP', 0.68, 0.12, INK);
      A.fillStyle = css(INK);
      A.fillRect(0, ch * 0.79, cw, ch * 0.09);
      line(A, cw, ch, 'RECORDS · TAPES · CDs', 0.835, 0.036, 0xf2c21a, 'display', 0.05);
      line(A, cw, ch, 'EVERY SUNDAY', 0.93, 0.03, INK, 'ui', 0.14);
    }
  }

  /** A hooded, masked head and shoulders: the Vultures never show a face. */
  function maskedFigure(A, cx, cy, s) {
    A.fillStyle = css(0x17181b);
    A.beginPath(); // shoulders
    A.moveTo(cx - s * 0.95, cy + s * 1.05);
    A.quadraticCurveTo(cx - s * 0.9, cy + s * 0.35, cx - s * 0.3, cy + s * 0.25);
    A.lineTo(cx + s * 0.3, cy + s * 0.25);
    A.quadraticCurveTo(cx + s * 0.9, cy + s * 0.35, cx + s * 0.95, cy + s * 1.05);
    A.fill();
    A.beginPath(); // hood
    A.ellipse(cx, cy - s * 0.1, s * 0.52, s * 0.64, 0, 0, TAU);
    A.fill();
    A.fillStyle = css(0xd9d4c6); // the pale mask
    A.beginPath();
    A.ellipse(cx, cy - s * 0.02, s * 0.33, s * 0.42, 0, 0, TAU);
    A.fill();
    A.fillStyle = css(0x17181b); // eye slit
    A.fillRect(cx - s * 0.26, cy - s * 0.12, s * 0.52, s * 0.1);
    A.fillStyle = css(OXBLOOD); // crew colour across the chest
    A.fillRect(cx - s * 0.7, cy + s * 0.72, s * 1.4, s * 0.12);
  }

  function wantedPoster(A, cw, ch, v) {
    const paper = [0xe9e0c6, 0xf1ede2, 0xe6d9a8][v];
    A.fillStyle = css(paper);
    A.fillRect(0, 0, cw, ch);
    A.strokeStyle = css(INK);
    A.lineWidth = Math.max(1, cw * 0.012);
    A.strokeRect(cw * 0.05, cw * 0.05, cw * 0.9, ch - cw * 0.1);
    if (v === 0) {
      line(A, cw, ch, 'WANTED', 0.16, 0.13, INK);
      A.fillStyle = css(0xbdb49a);
      A.fillRect(cw * 0.2, ch * 0.27, cw * 0.6, ch * 0.38);
      A.save();
      A.beginPath();
      A.rect(cw * 0.2, ch * 0.27, cw * 0.6, ch * 0.38);
      A.clip();
      maskedFigure(A, cw / 2, ch * 0.45, cw * 0.24);
      A.restore();
      line(A, cw, ch, 'THE VULTURES', 0.74, 0.06, INK);
      line(A, cw, ch, 'BOOTLEG CREW · REWARD', 0.85, 0.028, RED, 'ui', 0.1);
    } else if (v === 1) {
      line(A, cw, ch, 'MISSING', 0.15, 0.12, RED);
      // Three tape reels.
      for (let i = 0; i < 3; i++) {
        const x = cw * (0.25 + i * 0.25);
        const y = ch * 0.42;
        const r = cw * 0.105;
        A.fillStyle = css(INK);
        A.beginPath();
        A.arc(x, y, r, 0, TAU);
        A.fill();
        A.fillStyle = css(paper);
        for (let k = 0; k < 3; k++) {
          const a = (k / 3) * TAU + i;
          A.beginPath();
          A.arc(x + Math.cos(a) * r * 0.52, y + Math.sin(a) * r * 0.52, r * 0.22, 0, TAU);
          A.fill();
        }
        A.beginPath();
        A.arc(x, y, r * 0.12, 0, TAU);
        A.fill();
      }
      line(A, cw, ch, '3 MASTER REELS', 0.66, 0.07, INK);
      line(A, cw, ch, 'LAST SEEN ON THE AVENUE', 0.77, 0.028, INK, 'ui', 0.08);
      line(A, cw, ch, 'NO QUESTIONS ASKED', 0.87, 0.03, RED, 'ui', 0.1);
    } else {
      // A struck-through cassette: no bootlegs on this block.
      const r = cw * 0.27;
      const cy = ch * 0.36;
      A.fillStyle = css(INK);
      A.fillRect(cw / 2 - r * 0.7, cy - r * 0.42, r * 1.4, r * 0.84);
      A.fillStyle = css(paper);
      A.fillRect(cw / 2 - r * 0.5, cy - r * 0.22, r, r * 0.34);
      A.strokeStyle = css(RED);
      A.lineWidth = r * 0.16;
      A.beginPath();
      A.arc(cw / 2, cy, r, 0, TAU);
      A.moveTo(cw / 2 - r * 0.7, cy - r * 0.7);
      A.lineTo(cw / 2 + r * 0.7, cy + r * 0.7);
      A.stroke();
      line(A, cw, ch, 'NO BOOTLEGS', 0.7, 0.085, INK);
      line(A, cw, ch, 'BUY IT FROM THE SOURCE', 0.82, 0.028, INK, 'ui', 0.08);
    }
  }

  /** Big printed ads for the invented shops of the block. */
  function adPoster(A, cw, ch, v) {
    if (v === 0) {
      A.fillStyle = css(0xf2c21a);
      A.fillRect(0, 0, cw, ch);
      A.fillStyle = css(0xc9281e);
      A.fillRect(0, 0, cw, ch * 0.3);
      line(A, cw, ch, 'GOLDEN BIRD', 0.1, 0.085, 0xf2c21a);
      line(A, cw, ch, 'CHICKEN', 0.22, 0.085, PAPER);
      star(A, cw / 2, ch * 0.56, cw * 0.4, 14, 0.82, 0xc9281e);
      line(A, cw, ch, '2 PC', 0.5, 0.075, PAPER, 'display', 0, 0.5);
      line(A, cw, ch, '$1.99', 0.61, 0.1, 0xf2c21a, 'display', 0, 0.56);
      line(A, cw, ch, 'OPEN LATE · JAMAICA AVE', 0.9, 0.028, INK, 'ui', 0.1);
    } else if (v === 1) {
      A.fillStyle = css(PAPER);
      A.fillRect(0, 0, cw, ch);
      A.fillStyle = css(0x1f6b3a);
      A.fillRect(0, 0, cw, ch * 0.06);
      A.fillStyle = css(0xc9281e);
      A.fillRect(0, ch * 0.94, cw, ch * 0.06);
      line(A, cw, ch, '99¢', 0.2, 0.19, 0xc9281e, 'display', 0, 0.8);
      line(A, cw, ch, 'PIZZA', 0.4, 0.13, 0x1f6b3a);
      // One slice.
      const x = cw / 2;
      const y = ch * 0.52;
      const s = cw * 0.3;
      A.fillStyle = css(0xd9a23a);
      A.beginPath();
      A.moveTo(x - s, y);
      A.lineTo(x + s, y);
      A.lineTo(x, y + s * 1.9);
      A.fill();
      A.fillStyle = css(0xe9c45a);
      A.beginPath();
      A.moveTo(x - s * 0.84, y + s * 0.2);
      A.lineTo(x + s * 0.84, y + s * 0.2);
      A.lineTo(x, y + s * 1.78);
      A.fill();
      A.fillStyle = css(0xb3261e);
      for (const [px, py] of [[-0.35, 0.45], [0.3, 0.5], [0, 0.95], [-0.08, 0.4], [0.1, 1.35]]) {
        A.beginPath();
        A.arc(x + s * px, y + s * py, s * 0.13, 0, TAU);
        A.fill();
      }
      line(A, cw, ch, 'OPEN LATE', 0.9, 0.035, INK, 'ui', 0.16);
    } else if (v === 2) {
      A.fillStyle = css(0xf2a6c0);
      A.fillRect(0, 0, cw, ch);
      A.fillStyle = css(0x1f8a8a);
      A.fillRect(0, ch * 0.62, cw, ch * 0.38);
      const rand = prng(77);
      for (let i = 0; i < 16; i++) star(A, rand() * cw, rand() * ch * 0.58, cw * (0.02 + rand() * 0.05), 4, 0.28, i % 3 ? PAPER : 0xf6c21a);
      line(A, cw, ch, 'LUCKY', 0.26, 0.12, 0x1f8a8a);
      line(A, cw, ch, 'NAILS', 0.44, 0.14, 0xc9281e);
      line(A, cw, ch, 'MANICURE · PEDICURE', 0.72, 0.036, PAPER, 'display', 0.05);
      line(A, cw, ch, 'WALK-INS WELCOME', 0.84, 0.028, PAPER, 'ui', 0.14);
    } else {
      A.fillStyle = css(0x1f4f9a);
      A.fillRect(0, 0, cw, ch);
      const rand = prng(31);
      for (let i = 0; i < 22; i++) {
        A.strokeStyle = 'rgba(255,255,255,0.5)';
        A.lineWidth = Math.max(1, cw * 0.006);
        A.beginPath();
        A.arc(rand() * cw, ch * (0.45 + rand() * 0.5), cw * (0.02 + rand() * 0.08), 0, TAU);
        A.stroke();
      }
      line(A, cw, ch, '24 HR', 0.16, 0.13, 0xf6c21a);
      line(A, cw, ch, 'LAUNDROMAT', 0.33, 0.085, PAPER);
      rule(A, cw, ch, 0.42, PAPER, 0.004);
      line(A, cw, ch, 'WASH · DRY · FOLD', 0.5, 0.04, PAPER, 'display', 0.06);
      line(A, cw, ch, 'DROP OFF BY 9', 0.9, 0.028, PAPER, 'ui', 0.16);
    }
  }

  /** What is left of several posters: strips, a few readable letters, bare patches. */
  function tornPoster(A, cw, ch, v, rand) {
    const papers = [[0xc9281e, PAPER, 'LIVE'], [0xf2c21a, INK, 'SALE'], [0x1c3a6e, PAPER, 'TONITE']][v];
    A.fillStyle = css(mixHex(papers[0], 0x8a8478, 0.25));
    A.fillRect(0, 0, cw, ch);
    A.save();
    A.translate(cw / 2, ch * 0.4);
    A.rotate(-0.08);
    const fitted = type.fit(A, papers[2], 'display', cw * 1.1, ch * 0.3);
    type.draw(A, papers[2], 0, 0, fitted, { fill: css(papers[1]) });
    A.restore();
    A.fillStyle = css(shade(papers[0], 0.6));
    A.fillRect(0, ch * 0.72, cw, ch * 0.1);
    age(A, cw, ch, rand, 1.4);
    // Pieces ripped away from the edges inward: ragged outlines, a white fibre rim, then bare wall.
    const tears = 3 + Math.floor(rand() * 3);
    for (let i = 0; i < tears; i++) {
      // Each tear starts on an edge and bites toward the middle.
      const side = Math.floor(rand() * 4);
      const along = rand();
      const ex = side === 0 ? 0 : side === 1 ? cw : along * cw;
      const ey = side === 2 ? 0 : side === 3 ? ch : along * ch;
      const reach = Math.min(cw, ch) * (0.22 + rand() * 0.3);
      const pts = [];
      const n = 14;
      for (let k = 0; k < n; k++) {
        const a = (k / n) * TAU;
        const r = reach * (0.55 + rand() * 0.6);
        pts.push([ex + Math.cos(a) * r, ey + Math.sin(a) * r * (0.7 + rand() * 0.6)]);
      }
      const path = () => {
        A.beginPath();
        for (const [px, py] of pts) A.lineTo(px, py);
        A.closePath();
      };
      A.strokeStyle = 'rgba(236,232,220,0.85)';
      A.lineWidth = Math.max(2, cw * (0.012 + rand() * 0.014));
      A.lineJoin = 'bevel';
      A.save();
      A.globalCompositeOperation = 'source-atop';
      path();
      A.stroke();
      A.restore();
      A.save();
      A.globalCompositeOperation = 'destination-out';
      path();
      A.fill();
      A.restore();
    }
  }

  const POSTERS = { ipx: ipxPoster, show: showPoster, wanted: wantedPoster, ad: adPoster, torn: tornPoster };

  /** Paints poster `kind`, variant `v`: {canvas, w, h}. */
  function poster(kind, v) {
    const [w, h] = POSTER_SIZE[kind];
    const ppm = Math.min(POSTER_PPM[size] || 360, (size * 1.5) / Math.max(w, h));
    const cw = Math.round(w * ppm);
    const ch = Math.round(h * ppm);
    const A = canvas2d(cw, ch);
    const rand = prng(9001 + v * 131 + kind.length * 17);
    POSTERS[kind](A, cw, ch, v, rand);
    if (kind !== 'torn') age(A, cw, ch, rand, kind === 'ipx' ? 0.6 : 1);
    return { canvas: A.canvas, w, h };
  }

  // ---------------------------------------------------------------------------------------------
  // Graffiti
  // ---------------------------------------------------------------------------------------------

  /** Paint that ran: a thin line with a bead at its end. */
  function drip(A, x, y, len, wide, color) {
    A.strokeStyle = color;
    A.fillStyle = color;
    A.lineWidth = wide;
    A.lineCap = 'round';
    A.beginPath();
    A.moveTo(x, y);
    A.lineTo(x, y + len);
    A.stroke();
    A.beginPath();
    A.arc(x, y + len, wide * 0.9, 0, TAU);
    A.fill();
  }

  /** Letters set one by one, each a little off true: returns their boxes. */
  function letters(A, text, face, px, x0, baseY, advance, wobble, rand, each) {
    const boxes = [];
    let x = x0;
    for (const ch1 of text) {
      const fitted = type.at(A, ch1 === ' ' ? 'n' : ch1, face, px);
      if (ch1 !== ' ') {
        const box = { ch: ch1, x: x + fitted.width / 2, y: baseY + (rand() - 0.5) * px * wobble, rot: (rand() - 0.5) * wobble * 1.2, fitted };
        boxes.push(box);
        if (each) each(box);
      }
      x += fitted.width * advance;
    }
    return boxes;
  }

  function place(A, box, fn) {
    A.save();
    A.translate(box.x, box.y);
    A.rotate(box.rot);
    fn();
    A.restore();
  }

  /** Width of a run of letters at 100 px, to size it to the canvas. */
  function runWidth(A, text, face, advance) {
    let wsum = 0;
    for (const ch1 of text) wsum += type.at(A, ch1 === ' ' ? 'n' : ch1, face, 100).width * advance;
    return Math.max(1, wsum);
  }

  /** Fat-cap marker tag: quick, slanted, underlined. */
  function markerTag(A, cw, ch, text, color, rand) {
    const paint = css(color);
    const px = Math.min(ch * 0.62, (cw * 0.84 * 100) / runWidth(A, text, 'hand', 0.92));
    const total = (runWidth(A, text, 'hand', 0.92) * px) / 100;
    const x0 = (cw - total) / 2;
    const base = ch * 0.5;
    const boxes = letters(A, text, 'hand', px, x0, base, 0.92, 0.1, rand, (b) => {
      place(A, b, () => type.draw(A, b.ch, 0, 0, b.fitted, { fill: paint, stroke: paint, lineWidth: px * 0.035 }));
    });
    // The underline, struck in one move and finished with an arrowhead.
    A.strokeStyle = paint;
    A.lineWidth = Math.max(2, px * 0.07);
    A.lineCap = 'round';
    A.lineJoin = 'round';
    const y = base + px * 0.52;
    A.beginPath();
    A.moveTo(x0 - px * 0.1, y + px * 0.06);
    A.quadraticCurveTo(cw / 2, y - px * 0.12, x0 + total + px * 0.12, y + px * 0.02);
    A.lineTo(x0 + total - px * 0.08, y - px * 0.12);
    A.moveTo(x0 + total + px * 0.12, y + px * 0.02);
    A.lineTo(x0 + total - px * 0.06, y + px * 0.16);
    A.stroke();
    // Tick marks over the last letter.
    const last = boxes[boxes.length - 1];
    if (last) {
      for (let i = 0; i < 3; i++) {
        A.beginPath();
        A.moveTo(last.x + px * (0.1 + i * 0.14), last.y - px * 0.48);
        A.lineTo(last.x + px * (0.16 + i * 0.14), last.y - px * 0.62);
        A.stroke();
      }
    }
    for (const b of boxes) if (rand() < 0.3) drip(A, b.x + (rand() - 0.5) * px * 0.2, b.y + px * 0.2, px * (0.15 + rand() * 0.4), Math.max(1.5, px * 0.022), paint);
  }

  /** Spray tag: soft edges, a haze of overspray, long drips. */
  function sprayTag(A, cw, ch, text, color, rand) {
    const paint = css(color);
    const px = Math.min(ch * 0.66, (cw * 0.82 * 100) / runWidth(A, text, 'hand', 0.88));
    const total = (runWidth(A, text, 'hand', 0.88) * px) / 100;
    const x0 = (cw - total) / 2;
    const base = ch * 0.48;
    const fat = px * 0.05;
    // Overspray first: the same letters, wide and faint.
    A.save();
    A.globalAlpha = 0.2;
    A.shadowColor = paint;
    A.shadowBlur = px * 0.14;
    const boxes = letters(A, text, 'hand', px, x0, base, 0.88, 0.14, rand, (b) => {
      place(A, b, () => type.draw(A, b.ch, 0, 0, b.fitted, { fill: paint, stroke: paint, lineWidth: fat * 1.1 }));
    });
    A.restore();
    A.save();
    A.shadowColor = paint;
    A.shadowBlur = px * 0.03;
    for (const b of boxes) place(A, b, () => type.draw(A, b.ch, 0, 0, b.fitted, { fill: paint, stroke: paint, lineWidth: fat }));
    A.restore();
    // A halo ring thrown round the tag, and flecks from a tired cap.
    A.strokeStyle = paint;
    A.lineWidth = fat * 0.8;
    A.globalAlpha = 0.8;
    A.beginPath();
    A.ellipse(cw / 2, base, total * 0.56, px * 0.62, -0.04, Math.PI * 0.9, Math.PI * 2.75);
    A.stroke();
    A.globalAlpha = 1;
    for (let i = 0; i < 160; i++) {
      A.fillStyle = css(color, 0.15 + rand() * 0.35);
      A.beginPath();
      A.arc(cw / 2 + (rand() - 0.5) * total * 1.25, base + (rand() - 0.5) * px * 1.5, Math.max(0.6, rand() * px * 0.014), 0, TAU);
      A.fill();
    }
    for (const b of boxes) if (rand() < 0.45) drip(A, b.x + (rand() - 0.5) * px * 0.2, b.y + px * 0.18, px * (0.25 + rand() * 0.6), Math.max(1.5, px * 0.02), paint);
  }

  /** Throw-up: bubble letters, one colour inside a heavy outline, with a hard shadow and a shine. */
  function throwUp(A, cw, ch, text, color, rand) {
    const fill = css(color);
    const edge = luma(color) < 0.25 ? 0xf4f2ec : 0x0b0b0d;
    const outline = css(edge);
    const cloud = SPRAY[(SPRAY.indexOf(color) + 3 + Math.floor(rand() * 2)) % SPRAY.length];
    // A wide heavy face: bubbles need open counters to stay readable once they are inflated.
    const px = Math.min(ch * 0.56, (cw * 0.78 * 100) / runWidth(A, text, 'heavy', 0.94));
    const total = (runWidth(A, text, 'heavy', 0.94) * px) / 100;
    const x0 = (cw - total) / 2;
    const base = ch * 0.5;
    const fat = px * 0.13;

    // A cloud of second colour behind the piece.
    A.save();
    A.globalAlpha = 0.5;
    A.shadowColor = css(cloud);
    A.shadowBlur = px * 0.2;
    A.fillStyle = css(cloud);
    for (let i = 0; i < 7; i++) {
      A.beginPath();
      A.ellipse(x0 + total * (i / 6), base + (rand() - 0.5) * px * 0.3, px * (0.42 + rand() * 0.2), px * (0.5 + rand() * 0.22), 0, 0, TAU);
      A.fill();
    }
    A.restore();

    const boxes = letters(A, text, 'heavy', px, x0, base, 0.94, 0.09, rand);
    const shift = px * 0.08;
    for (const b of boxes) {
      place(A, b, () => type.draw(A, b.ch, shift, shift, b.fitted, { fill: outline, stroke: outline, lineWidth: fat }));
    }
    for (const b of boxes) {
      place(A, b, () => {
        type.draw(A, b.ch, 0, 0, b.fitted, { fill: outline, stroke: outline, lineWidth: fat });
        type.draw(A, b.ch, 0, 0, b.fitted, { fill, stroke: fill, lineWidth: fat * 0.22 });
        // The shine: a short white stroke high on the letter.
        A.strokeStyle = 'rgba(255,255,255,0.85)';
        A.lineWidth = Math.max(1.5, px * 0.035);
        A.lineCap = 'round';
        A.beginPath();
        A.moveTo(-b.fitted.width * 0.22, -px * 0.2);
        A.quadraticCurveTo(-b.fitted.width * 0.18, -px * 0.32, -b.fitted.width * 0.02, -px * 0.36);
        A.stroke();
      });
    }
    star(A, x0 + total + px * 0.12, base - px * 0.42, px * 0.16, 4, 0.3, 0xffffff);
    star(A, x0 - px * 0.1, base + px * 0.3, px * 0.1, 4, 0.3, 0xffffff);
    for (const b of boxes) if (rand() < 0.3) drip(A, b.x, b.y + px * 0.45, px * (0.12 + rand() * 0.3), Math.max(2, px * 0.03), outline);
  }

  /** The IPX mark sprayed through a stencil. */
  function sprayMark(A, cw, ch, color) {
    const paint = css(color);
    const h = Math.min(ch * 0.6, (cw * 0.8 * 100) / ipxWidth(A, 100));
    A.save();
    A.globalAlpha = 0.3;
    A.shadowColor = paint;
    A.shadowBlur = h * 0.2;
    drawIPX(A, cw / 2, ch / 2, h, paint);
    A.restore();
    drawIPX(A, cw / 2, ch / 2, h, paint);
  }

  /**
   * Paints `text` as graffiti: {canvas, w, h} in metres. The seed picks hand and colour.
   */
  function graffiti(text, seed, color) {
    const style = ((seed % 3) + 3) % 3;
    const big = style === 2;
    const n = Math.max(1, text.length);
    const w = big ? Math.max(1.6, n * 0.62 + 0.5) : Math.max(1, n * 0.42);
    const h = big ? 1.4 : 0.9;
    const ppm = Math.min(GRAFFITI_PPM[size] || 220, (size * 2) / w);
    const cw = Math.round(w * ppm);
    const ch = Math.round(h * ppm);
    const A = canvas2d(cw, ch);
    const rand = prng(1300 + seed * 977 + n);
    const paint = color === undefined || color === null ? SPRAY[(((seed * 5 + n) % SPRAY.length) + SPRAY.length) % SPRAY.length] : toHex(color);
    if (text === brand.ipx.wordmark) sprayMark(A, cw, ch, paint);
    else [markerTag, sprayTag, throwUp][style](A, cw, ch, text, paint, rand);
    // The wall shows through where the paint missed the pits and the joints.
    erase(A, bank.mask('fine', 0.6, 0.85), Math.max(1, cw / 300), Math.max(1, ch / 300), { alpha: 0.55 });
    return { canvas: A.canvas, w, h };
  }

  return { poster, graffiti };
}
