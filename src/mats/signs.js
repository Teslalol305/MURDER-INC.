// Shop signs and the IPX wordmark, painted on canvases: mats.sign(spec) and mats.drawIPX().
//
// A sign is an albedo canvas plus, when it is lit, an emissive canvas (what glows, and how hard).
// Styles: neon, box, painted, awning, street, stencil, plate. Text is whatever the caller passes; a
// text that is exactly the IPX wordmark is drawn with drawIPX() so the real logo can replace it later
// in one place.

import { canvas2d, css, erase, fillTiled, luma, mixHex, shade, stain, toHex } from './canvas.js';
import { prng } from './noise.js';

const TAU = Math.PI * 2;

/** Pixels per metre for signs at each texture tier, before clamping. */
const SIGN_PPM = { 256: 100, 512: 170, 1024: 256 };

const PAINTED_BOARDS = [0x6e1a1f, 0x1b4a36, 0x1b3565, 0x1a1b1f, 0xb8891a, 0x4a2a5e];

function roundRect(ctx, x, y, w, h, r) {
  r = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.arc(x + w - r, y + r, r, -Math.PI / 2, 0);
  ctx.lineTo(x + w, y + h - r);
  ctx.arc(x + w - r, y + h - r, r, 0, Math.PI / 2);
  ctx.lineTo(x + r, y + h);
  ctx.arc(x + r, y + h - r, r, Math.PI / 2, Math.PI);
  ctx.lineTo(x, y + r);
  ctx.arc(x + r, y + r, r, Math.PI, Math.PI * 1.5);
  ctx.closePath();
}

function hashText(text) {
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 16777619);
  return h >>> 0;
}

/**
 * @param {object} env  { size, type, bank, brand, palette, aniso }
 */
export function createSignPainter(env) {
  const { size, type, bank, brand, palette } = env;
  const WORDMARK = brand.ipx.wordmark;

  /**
   * The IPX wordmark: "IPX" in a heavy italic grotesque inside a thin lozenge.
   * (x, y) is the centre, h the height in pixels; returns the width drawn.
   */
  function drawIPX(ctx, x, y, h, color = brand.colors.ink) {
    const paint = typeof color === 'number' || (color && color.isColor) ? css(toHex(color)) : color;
    const fitted = type.at(ctx, WORDMARK, 'italic', h * 0.58, 0.05);
    const line = Math.max(1, h * 0.065);
    const w = fitted.width + h * 0.86;
    const r = h / 2 - line / 2;
    ctx.save();
    ctx.strokeStyle = paint;
    ctx.lineWidth = line;
    ctx.beginPath(); // the lozenge: two half circles joined by straight edges
    ctx.arc(x - w / 2 + h / 2, y, r, Math.PI / 2, Math.PI * 1.5);
    ctx.arc(x + w / 2 - h / 2, y, r, -Math.PI / 2, Math.PI / 2);
    ctx.closePath();
    ctx.stroke();
    type.draw(ctx, WORDMARK, x - h * 0.02, y, fitted, { fill: paint });
    ctx.restore();
    return w;
  }

  /** Width the wordmark takes at height h. */
  const ipxWidth = (ctx, h) => type.at(ctx, WORDMARK, 'italic', h * 0.58, 0.05).width + h * 0.86;

  /** Canvas size for a sign of w × h metres: [pixels wide, pixels high]. */
  function pixels(w, h) {
    const cap = size * 2;
    const long = Math.max(w, h);
    let ppm = Math.min(SIGN_PPM[size] || 256, cap / long);
    // Small signs get more pixels per metre so their lettering stays crisp.
    ppm = Math.max(ppm, Math.min(Math.max(48, size / 8) / Math.min(w, h), cap / long));
    return [Math.max(16, Math.round(w * ppm)), Math.max(16, Math.round(h * ppm))];
  }

  /**
   * The headline of a sign: the fitted text, or the wordmark when the text is "IPX".
   * Returns a function that draws it centred on (cx, cy) in any context and style.
   */
  function headline(ctx, text, face, maxW, inkH, spacing = 0) {
    if (text === WORDMARK) {
      let h = inkH * 1.4;
      const wide = ipxWidth(ctx, h);
      if (wide > maxW) h *= maxW / wide;
      return { width: ipxWidth(ctx, h), ink: h, draw: (c, cx, cy, o) => drawIPX(c, cx, cy, h, o.fill || o.stroke) };
    }
    const fitted = type.fit(ctx, text, face, maxW, inkH, spacing);
    return { width: fitted.width, ink: fitted.ascent + fitted.descent, fitted, draw: (c, cx, cy, o) => type.draw(c, text, cx, cy, fitted, o) };
  }

  /** Dirt and sun on a painted or printed face. */
  function weather(A, amount, seedOffset = 0) {
    // One repeat of a noise layer per sign height, so runs stay vertical on a long board.
    const across = Math.max(1, A.canvas.width / A.canvas.height);
    stain(A, bank.mask('streaks', 0.5, 0.92), 'rgb(28,26,22)', { alpha: 0.32 * amount, tilesX: across, tilesY: 1, ox: seedOffset });
    stain(A, bank.mask('clouds', 0.58, 0.9), 'rgb(210,205,190)', { alpha: 0.14 * amount, tilesX: across / 2, tilesY: 0.5, ox: seedOffset * 0.7, oy: 0.3 });
    fillTiled(A, bank.grain(64, 64), A.canvas.width / 64, A.canvas.height / 64, { mode: 'overlay', alpha: 0.12 });
  }

  // ---------------------------------------------------------------------------------------------
  // Styles. Each paints the albedo `A` and, when the sign is lit, the emissive `E`.
  // ---------------------------------------------------------------------------------------------

  /** Glass tube lettering on a dark backing board: outlined capitals, a border tube, a soft halo. */
  function neon(A, E, o) {
    const { cw, ch } = o;
    const pad = ch * 0.09;
    const tube = Math.max(2, Math.min(ch * 0.045, cw * 0.012));
    A.fillStyle = css(o.bg);
    A.fillRect(0, 0, cw, ch);
    A.strokeStyle = css(shade(o.bg, 2.4) || 0x1c1c20);
    A.lineWidth = Math.max(1, ch * 0.02);
    A.strokeRect(A.lineWidth / 2, A.lineWidth / 2, cw - A.lineWidth, ch - A.lineWidth);

    const hasSub = !!o.sub;
    const inner = cw - pad * 4 - tube * 2;
    const main = headline(A, o.text, 'tube', inner, ch * (hasSub ? 0.36 : 0.46), 0.07);
    const yMain = ch * (hasSub ? 0.4 : 0.5);
    const sub = hasSub ? type.fit(A, o.sub, 'ui', inner * 0.9, ch * 0.13, 0.1) : null;
    const ySub = ch * 0.76;

    /** Everything that is tube, stroked `width` wide in the two colours. */
    function tubes(ctx, first, second, width, blur = 0) {
      ctx.save();
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      ctx.lineWidth = width;
      ctx.shadowBlur = blur;
      ctx.shadowColor = second;
      ctx.strokeStyle = second;
      roundRect(ctx, pad, pad, cw - pad * 2, ch - pad * 2, ch * 0.14);
      ctx.stroke();
      if (sub) type.draw(ctx, o.sub, cw / 2, ySub, sub, { fill: second, stroke: second, lineWidth: width * 0.35 });
      ctx.shadowColor = first;
      if (o.text === WORDMARK) main.draw(ctx, cw / 2, yMain, { fill: first });
      else main.draw(ctx, cw / 2, yMain, { stroke: first, lineWidth: width });
      ctx.restore();
    }

    // Unlit glass on the board, with the clips that hold it.
    tubes(A, css(mixHex(o.fg, 0x9a9aa2, 0.55), 0.6), css(mixHex(o.glow, 0x9a9aa2, 0.55), 0.6), tube);
    if (!E) return;

    E.fillStyle = '#000';
    E.fillRect(0, 0, cw, ch);
    // Wide halo: the tubes drawn small and stretched back up.
    const k = 8;
    const small = canvas2d(Math.ceil(cw / k), Math.ceil(ch / k));
    small.scale(1 / k, 1 / k);
    tubes(small, css(o.fg), css(o.glow), tube * 3);
    E.save();
    E.globalAlpha = 0.42;
    E.imageSmoothingEnabled = true;
    E.drawImage(small.canvas, 0, 0, cw, ch);
    E.restore();
    // The tube with a tight glow, then its white-hot core.
    tubes(E, css(o.fg), css(o.glow), tube, tube * 2.2);
    tubes(E, css(mixHex(o.fg, 0xffffff, 0.72)), css(mixHex(o.glow, 0xffffff, 0.72)), Math.max(1, tube * 0.42));
  }

  /** Back-lit plastic box sign in an aluminium frame. */
  function box(A, E, o) {
    const { cw, ch, ppm } = o;
    const frame = Math.max(2, ch * 0.045);
    A.fillStyle = css(o.bg);
    A.fillRect(0, 0, cw, ch);
    const hasSub = !!o.sub;
    const main = headline(A, o.text, 'display', cw * 0.9 - frame * 4, ch * (hasSub ? 0.4 : 0.54));
    main.draw(A, cw / 2, ch * (hasSub ? 0.4 : 0.5), { fill: css(o.fg) });
    if (hasSub) {
      const sub = type.fit(A, o.sub, 'ui', cw * 0.84, ch * 0.14, 0.08);
      type.draw(A, o.sub, cw / 2, ch * 0.78, sub, { fill: css(o.glow) });
    }
    A.strokeStyle = css(o.fg, 0.85);
    A.lineWidth = Math.max(1, ch * 0.014);
    A.strokeRect(frame * 2.2, frame * 2.2, cw - frame * 4.4, ch - frame * 4.4);
    // Seams between the plastic panels.
    for (let x = 1.22 * ppm; x < cw - 0.3 * ppm; x += 1.22 * ppm) {
      A.fillStyle = 'rgba(0,0,0,0.28)';
      A.fillRect(x, 0, Math.max(1, ch * 0.008), ch);
    }

    if (E) {
      E.drawImage(A.canvas, 0, 0);
      // Fluorescent tubes behind the face: two bright bands, dimmer toward the ends.
      E.globalCompositeOperation = 'multiply';
      const v = E.createLinearGradient(0, 0, 0, ch);
      for (const [stop, level] of [[0, 0.62], [0.28, 1], [0.5, 0.86], [0.72, 1], [1, 0.62]]) v.addColorStop(stop, `rgb(${level * 255},${level * 255},${level * 255})`);
      E.fillStyle = v;
      E.fillRect(0, 0, cw, ch);
      const u = E.createLinearGradient(0, 0, cw, 0);
      for (const [stop, level] of [[0, 0.7], [Math.min(0.2, ch / cw), 1], [1 - Math.min(0.2, ch / cw), 1], [1, 0.7]]) u.addColorStop(stop, `rgb(${level * 255},${level * 255},${level * 255})`);
      E.fillStyle = u;
      E.fillRect(0, 0, cw, ch);
      E.globalCompositeOperation = 'source-over';
    }
    // Grime that has run down the face, then the frame on top.
    stain(A, bank.mask('streaks', 0.55, 0.95), 'rgb(30,28,24)', { alpha: 0.22, tilesX: Math.max(1, cw / ch), tilesY: 1 });
    for (const [ctx, style] of [[A, css(0x1b1c20)], [E, '#000']]) {
      if (!ctx) continue;
      ctx.strokeStyle = style;
      ctx.lineWidth = frame;
      ctx.strokeRect(frame / 2, frame / 2, cw - frame, ch - frame);
    }
    A.strokeStyle = 'rgba(255,255,255,0.14)';
    A.lineWidth = 1;
    A.strokeRect(frame, frame, cw - frame * 2, ch - frame * 2);
  }

  /** Hand-painted fascia board: block capitals with a drop shadow and a pinstripe, weathered. */
  function painted(A, E, o) {
    const { cw, ch, ppm } = o;
    A.fillStyle = css(o.bg);
    A.fillRect(0, 0, cw, ch);
    // Brush marks along the board and the joints between its sheets.
    stain(A, bank.mask('fine', 0.3, 0.9), css(shade(o.bg, 1.25)), { alpha: 0.25, tilesX: cw / ch, tilesY: 6 });
    for (let x = 2.44 * ppm; x < cw - 0.3 * ppm; x += 2.44 * ppm) {
      A.fillStyle = 'rgba(0,0,0,0.45)';
      A.fillRect(x, 0, Math.max(1, ch * 0.01), ch);
    }
    const inset = ch * 0.08;
    A.strokeStyle = css(o.fg, 0.9);
    A.lineWidth = Math.max(1, ch * 0.018);
    A.strokeRect(inset, inset, cw - inset * 2, ch - inset * 2);

    const hasSub = !!o.sub;
    const main = headline(A, o.text, 'display', cw - inset * 5, ch * (hasSub ? 0.4 : 0.52));
    const yMain = ch * (hasSub ? 0.4 : 0.5);
    const drop = Math.max(1, main.ink * 0.07);
    main.draw(A, cw / 2 + drop, yMain + drop, { fill: css(shade(o.bg, 0.35)) });
    main.draw(A, cw / 2, yMain, { fill: css(o.fg) });
    if (hasSub) {
      const sub = type.fit(A, o.sub, 'medium', cw - inset * 6, ch * 0.13, 0.14);
      type.draw(A, o.sub, cw / 2, ch * 0.78, sub, { fill: css(o.glow) });
    }
    weather(A, 1, (hashText(o.text) % 97) / 97);
    // Paint that has flaked off to the primer.
    const rand = prng(hashText(o.text));
    for (let i = 0; i < Math.round((cw * ch) / 5000); i++) {
      A.fillStyle = `rgba(${150 + rand() * 60},${140 + rand() * 50},${120 + rand() * 40},${0.25 + rand() * 0.4})`;
      A.beginPath();
      A.ellipse(rand() * cw, rand() * ch, 1 + rand() * ch * 0.02, 1 + rand() * ch * 0.012, rand() * 3, 0, TAU);
      A.fill();
    }
    if (E) {
      // Gooseneck lamps above the board: pools of light that fade toward its foot.
      E.fillStyle = '#000';
      E.fillRect(0, 0, cw, ch);
      E.globalCompositeOperation = 'lighter';
      const lamps = Math.max(1, Math.round(cw / (1.8 * ppm)));
      for (let i = 0; i < lamps; i++) {
        const x = ((i + 0.5) * cw) / lamps;
        const g = E.createRadialGradient(x, -ch * 0.25, 0, x, -ch * 0.25, ch * 1.9);
        g.addColorStop(0, 'rgba(255,226,170,1)');
        g.addColorStop(0.45, 'rgba(255,226,170,0.55)');
        g.addColorStop(1, 'rgba(255,226,170,0)');
        E.fillStyle = g;
        E.fillRect(0, 0, cw, ch);
      }
      E.globalCompositeOperation = 'multiply';
      E.drawImage(A.canvas, 0, 0);
      E.globalCompositeOperation = 'source-over';
    }
  }

  /** Lettering on a fabric awning valance, lit from inside. */
  function awning(A, E, o) {
    const { cw, ch, ppm } = o;
    A.fillStyle = css(o.bg);
    A.fillRect(0, 0, cw, ch);
    const hasSub = !!o.sub;
    const main = headline(A, o.text, 'display', cw * 0.9, ch * (hasSub ? 0.38 : 0.5));
    main.draw(A, cw / 2, ch * (hasSub ? 0.38 : 0.46), { fill: css(o.fg) });
    if (hasSub) {
      const sub = type.fit(A, o.sub, 'ui', cw * 0.84, ch * 0.13, 0.1);
      type.draw(A, o.sub, cw / 2, ch * 0.72, sub, { fill: css(o.glow) });
    }
    // Bound edge with a line of stitching.
    const trim = Math.max(2, ch * 0.07);
    A.fillStyle = css(o.fg, 0.9);
    A.fillRect(0, ch - trim, cw, trim * 0.45);
    A.fillStyle = css(shade(o.bg, 0.6));
    A.fillRect(0, ch - trim * 0.55, cw, trim * 0.55);
    A.setLineDash([Math.max(2, ch * 0.03), Math.max(2, ch * 0.03)]);
    A.strokeStyle = 'rgba(255,255,255,0.25)';
    A.lineWidth = 1;
    A.beginPath();
    A.moveTo(0, ch * 0.05);
    A.lineTo(cw, ch * 0.05);
    A.stroke();
    A.setLineDash([]);
    // The cloth hangs in soft folds between its frame ribs.
    const rand = prng(hashText(o.text) + 5);
    const rib = 0.6 * ppm;
    for (let x = -rand() * rib; x < cw; x += rib * (0.8 + rand() * 0.4)) {
      const g = A.createLinearGradient(x, 0, x + rib, 0);
      g.addColorStop(0, 'rgba(0,0,0,0.2)');
      g.addColorStop(0.5, 'rgba(255,255,255,0.07)');
      g.addColorStop(1, 'rgba(0,0,0,0.2)');
      A.fillStyle = g;
      A.fillRect(x, 0, rib, ch);
    }
    weather(A, 0.8, (hashText(o.text) % 89) / 89);
    if (E) {
      E.drawImage(A.canvas, 0, 0);
      E.globalCompositeOperation = 'multiply';
      const v = E.createLinearGradient(0, 0, 0, ch);
      v.addColorStop(0, 'rgb(150,150,150)');
      v.addColorStop(0.45, 'rgb(255,255,255)');
      v.addColorStop(1, 'rgb(170,170,170)');
      E.fillStyle = v;
      E.fillRect(0, 0, cw, ch);
      E.globalCompositeOperation = 'source-over';
    }
  }

  /** Street-name blade: white on green inside a white keyline, the suffix set small and high. */
  function street(A, E, o) {
    const { cw, ch } = o;
    A.fillStyle = css(o.bg);
    A.fillRect(0, 0, cw, ch);
    const line = Math.max(1, ch * 0.035);
    A.strokeStyle = css(o.fg);
    A.lineWidth = line;
    roundRect(A, line * 1.6, line * 1.6, cw - line * 3.2, ch - line * 3.2, ch * 0.1);
    A.stroke();
    const hasSub = !!o.sub;
    const room = cw - ch * 0.5;
    let main = type.fit(A, o.text, 'ui', room, ch * 0.46);
    let sub = hasSub ? type.fit(A, o.sub, 'ui', room * 0.3, (main.ascent + main.descent) * 0.52) : null;
    let gap = hasSub ? main.px * 0.22 : 0;
    const total = main.width + gap + (sub ? sub.width : 0);
    if (total > room) {
      // Name and suffix together are too long: shrink both.
      const k = room / total;
      main = type.at(A, o.text, 'ui', main.px * k);
      sub = sub && type.at(A, o.sub, 'ui', sub.px * k);
      gap *= k;
    }
    const left = (cw - (main.width + gap + (sub ? sub.width : 0))) / 2;
    type.draw(A, o.text, left, ch / 2, main, { fill: css(o.fg), align: 'left' });
    if (sub) {
      const top = ch / 2 - (main.ascent + main.descent) / 2;
      type.draw(A, o.sub, left + main.width + gap, top + (sub.ascent + sub.descent) / 2, sub, { fill: css(o.fg), align: 'left' });
    }
    weather(A, 0.45, 0.4);
    if (E) E.drawImage(A.canvas, 0, 0);
  }

  /** Sprayed stencil lettering straight on the wall or the road: bridges, overspray, wear. */
  function stencil(A, E, o) {
    const { cw, ch } = o;
    const hasSub = !!o.sub;
    const lines = [[o.text, 'display', ch * (hasSub ? 0.36 : 0.5), ch * (hasSub ? 0.56 : 0.72)]];
    if (hasSub) lines.push([o.sub, 'ui', ch * 0.82, ch * 0.2]);
    for (const [text, face, y, inkH] of lines) {
      const yy = lines.length > 1 ? y : ch / 2;
      if (text === WORDMARK) {
        headline(A, text, face, cw * 0.9, inkH).draw(A, cw / 2, yy, { fill: css(o.fg) });
        continue;
      }
      const fitted = type.fit(A, text, face, cw * 0.92, inkH, 0.04);
      type.draw(A, text, cw / 2, yy, fitted, { fill: css(o.fg) });
      // Stencil bridges: a thin gap through the middle of every letter that has a counter.
      A.save();
      A.globalCompositeOperation = 'destination-out';
      let cursor = cw / 2 - fitted.width / 2;
      for (const ch1 of text) {
        const glyph = type.at(A, ch1, face, fitted.px).width;
        if (/[A-HJ-Z02-9&@#$%]/i.test(ch1)) A.fillRect(cursor + glyph * 0.5 - fitted.px * 0.022, yy - inkH, fitted.px * 0.044, inkH * 2);
        cursor += glyph + fitted.spacing * fitted.px * type.faces[face].squeeze;
      }
      A.restore();
    }
    // Paint that never reached the surface, and paint that has worn away since.
    erase(A, bank.mask('fine', 0.56, 0.8), Math.max(1, cw / 256), Math.max(1, ch / 256), { alpha: 0.85 });
    erase(A, bank.mask('clouds', 0.6, 0.85), Math.max(1, cw / 700), Math.max(1, ch / 700), { alpha: 0.6 });
    // Overspray: a faint ghost of the letters behind them.
    const ghost = canvas2d(Math.ceil(cw / 4), Math.ceil(ch / 4));
    ghost.drawImage(A.canvas, 0, 0, ghost.canvas.width, ghost.canvas.height);
    A.save();
    A.globalCompositeOperation = 'destination-over';
    A.globalAlpha = 0.35;
    A.drawImage(ghost.canvas, -2, -2, cw + 4, ch + 4);
    A.restore();
  }

  /** Transit plate: black enamel, a thin white rule above white grotesque type, an optional bullet. */
  function plate(A, E, o) {
    const { cw, ch } = o;
    A.fillStyle = css(o.bg);
    A.fillRect(0, 0, cw, ch);
    const m = ch * 0.13;
    const hasSub = !!o.sub;
    A.fillStyle = css(o.fg);
    A.fillRect(m, ch * 0.15, cw - m * 2, Math.max(1, ch * 0.028));

    if (o.text === WORDMARK) {
      // The mark alone, centred under the rule, its address beneath.
      const mark = headline(A, o.text, 'italic', cw - m * 3, ch * (hasSub ? 0.21 : 0.27));
      mark.draw(A, cw / 2, ch * (hasSub ? 0.47 : 0.58), { fill: css(o.fg) });
      if (hasSub) {
        const sub = type.fit(A, o.sub, 'ui', cw - m * 3, ch * 0.1, 0.16);
        type.draw(A, o.sub, cw / 2, ch * 0.82, sub, { fill: css(o.fg) });
      }
    } else {
      let x = m;
      const yText = ch * (hasSub ? 0.5 : 0.6);
      if (o.bullet) {
        const d = ch * 0.5;
        A.fillStyle = css(o.bulletColor);
        A.beginPath();
        A.arc(x + d / 2, ch * 0.6, d / 2, 0, TAU);
        A.fill();
        const ink = luma(o.bulletColor) > 0.55 ? 0x0d0e11 : 0xffffff;
        const glyph = type.fit(A, o.bullet, 'ui', d * 0.72, d * 0.5);
        type.draw(A, o.bullet, x + d / 2, ch * 0.6, glyph, { fill: css(ink) });
        x += d + m * 0.8;
      }
      const main = type.fit(A, o.text, 'ui', cw - x - m, ch * (hasSub ? 0.25 : 0.33));
      type.draw(A, o.text, x, yText, main, { fill: css(o.fg), align: 'left' });
      if (hasSub) {
        const sub = type.fit(A, o.sub, 'medium', cw - x - m, ch * 0.15);
        type.draw(A, o.sub, x, ch * 0.81, sub, { fill: css(mixHex(o.fg, o.bg, 0.3)), align: 'left' });
      }
    }
    // Fixing holes and a little street dirt on the enamel.
    for (const [hx, hy] of [[m * 0.45, m * 0.45], [cw - m * 0.45, m * 0.45], [m * 0.45, ch - m * 0.45], [cw - m * 0.45, ch - m * 0.45]]) {
      A.fillStyle = 'rgba(150,150,150,0.8)';
      A.beginPath();
      A.arc(hx, hy, Math.max(1, ch * 0.016), 0, TAU);
      A.fill();
    }
    weather(A, 0.35, 0.2);
    if (E) E.drawImage(A.canvas, 0, 0);
  }

  /**
   * style → {paint, emissive intensity when lit, roughness, lit by default, default colours}
   */
  const STYLES = {
    neon: { paint: neon, glow: 2.6, roughness: 0.45, lit: true, fg: palette.neonPink, bg: 0x0b0b0e },
    box: { paint: box, glow: 1.5, roughness: 0.35, lit: true, fg: 0xb3261e, bg: 0xf1ede2 },
    painted: { paint: painted, glow: 0.85, roughness: 0.8, lit: false, fg: 0xf1e6c8, bg: null },
    awning: { paint: awning, glow: 0.8, roughness: 0.9, lit: true, fg: 0xf4f2ec, bg: 0x7a1f24 },
    street: { paint: street, glow: 0.45, roughness: 0.4, lit: true, fg: 0xffffff, bg: 0x0f5c3f },
    stencil: { paint: stencil, glow: 0, roughness: 0.85, lit: false, fg: 0xe9e4d4, bg: null, overlay: true },
    plate: { paint: plate, glow: 0.45, roughness: 0.25, lit: true, fg: 0xf4f2ec, bg: 0x0d0e11 },
  };

  /**
   * Resolves a sign spec to everything the painter needs. The returned `key` identifies the
   * finished look (two equal keys can share one material).
   */
  function resolve(spec = {}) {
    const style = STYLES[spec.style] ? spec.style : 'box';
    const def = STYLES[style];
    const text = String(spec.text ?? '');
    const sub = spec.sub ? String(spec.sub) : '';
    const w = spec.w > 0 ? +spec.w : 2;
    const h = spec.h > 0 ? +spec.h : 0.6;
    const fg = toHex(spec.fg, def.fg);
    let bg = toHex(spec.bg, def.bg ?? PAINTED_BOARDS[hashText(text) % PAINTED_BOARDS.length]);
    if (style === 'stencil') bg = 0;
    const glow = toHex(spec.glow, style === 'neon' ? (spec.glow === undefined && sub ? palette.neonCyan : fg) : fg);
    // Painted boards and stencils are only lit when asked; everything else is lit unless told not to be.
    const lit = def.glow > 0 && (def.lit ? spec.lit !== false : spec.lit === true);
    const bullet = style === 'plate' && spec.bullet !== undefined && spec.bullet !== null ? String(spec.bullet) : '';
    const bulletColor = toHex(spec.bulletColor, spec.glow !== undefined ? toHex(spec.glow) : toHex(brand.colors.gold));
    const key = ['sign', style, text, sub, w, h, fg, bg, glow, lit ? 1 : 0, bullet, bullet ? bulletColor : 0].join('|');
    return { key, style, def, text, sub, w, h, fg, bg, glow, lit, bullet, bulletColor };
  }

  /** Paints a resolved sign: {albedo, emissive (or null)} canvases. */
  function paint(o) {
    const [cw, ch] = pixels(o.w, o.h);
    const A = canvas2d(cw, ch);
    const E = o.lit ? canvas2d(cw, ch) : null;
    o.def.paint(A, E, { ...o, cw, ch, ppm: cw / o.w });
    return { albedo: A.canvas, emissive: E ? E.canvas : null };
  }

  return { drawIPX, ipxWidth, resolve, paint, pixels, headline, roundRect };
}
