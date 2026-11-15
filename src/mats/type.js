// Lettering for signs, posters and stencils.
//
// The page links Anton (tall condensed display) and Archivo (grotesque) from Google Fonts, but they may
// be blocked, and the canvas has to be painted either way. `createType()` works out once which faces
// really exist and gives every painter the same small API:
//
//   const fit = type.fit(ctx, 'WINES & LIQUORS', 'display', maxWidth, inkHeight)
//   type.draw(ctx, 'WINES & LIQUORS', cx, cy, fit, { fill: '#fff' })
//
// When no condensed face is installed the display face becomes the bold grotesque squeezed
// horizontally, so layouts keep their proportions on any machine.

import { canvas2d } from './canvas.js';

const FONT_WAIT_MS = 1500;
const WEB_FONTS = ['400 32px Anton', '700 32px Archivo', '500 32px Archivo', 'italic 800 32px Archivo'];

/** Asks the browser for the page's web fonts and waits for them, 1.5 s at most. */
export async function loadFonts() {
  if (typeof document === 'undefined' || !document.fonts || typeof document.fonts.load !== 'function') return;
  const all = Promise.all(WEB_FONTS.map((font) => document.fonts.load(font).catch(() => [])));
  await Promise.race([all, new Promise((resolve) => setTimeout(resolve, FONT_WAIT_MS))]);
}

/**
 * @param {{display: string, ui: string}} fonts  the brand font stacks (config/brand.js)
 */
export function createType(fonts) {
  const probe = canvas2d(4, 4);
  const SAMPLE = 'MURDER Inc. 0123 mwli';

  const width = (font) => {
    probe.font = font;
    return probe.measureText(SAMPLE).width;
  };

  /** True when `family` resolves to a real face: then the generic fallback behind it never shows. */
  function available(family, style = '400') {
    return Math.abs(width(`${style} 64px ${family}, monospace`) - width(`${style} 64px ${family}, serif`)) < 0.01;
  }

  const firstOf = (families, style) => families.find((family) => available(family, style)) || null;

  const condensed = firstOf(["'Anton'", "'Haettenschweiler'", 'Impact', "'Arial Narrow'"], '400');
  const hand = firstOf(["'Marker Felt'", "'Segoe Print'", "'Bradley Hand'", "'Ink Free'", "'Chalkboard SE'", "'Comic Sans MS'"], '700');

  /** face → {family, style (CSS font-style + weight), squeeze (horizontal scale), skew} */
  const faces = {
    display: condensed
      ? { family: `${condensed}, ${fonts.ui}`, style: condensed === "'Arial Narrow'" ? '700' : '400', squeeze: 1 }
      : { family: fonts.ui, style: '800', squeeze: 0.6 },
    // Outlined neon letters: a stroke is only even when the face is not squeezed much.
    tube: condensed ? { family: `${condensed}, ${fonts.ui}`, style: condensed === "'Arial Narrow'" ? '700' : '400', squeeze: 1 } : { family: fonts.ui, style: '800', squeeze: 0.82 },
    ui: { family: fonts.ui, style: '700', squeeze: 1 },
    medium: { family: fonts.ui, style: '500', squeeze: 1 },
    heavy: { family: fonts.ui, style: '800', squeeze: 1 },
    italic: { family: fonts.ui, style: 'italic 800', squeeze: 1 },
    // Handstyle for tags; without a marker face, a leaning grotesque stands in.
    hand: hand ? { family: `${hand}, ${fonts.ui}`, style: '700', squeeze: 0.9, skew: -0.18 } : { family: fonts.ui, style: 'italic 700', squeeze: 0.82, skew: -0.14 },
  };

  const face = (name) => faces[name] || faces.ui;
  const fontString = (f, px) => `${f.style} ${px}px ${f.family}`;

  /**
   * Size of `text` set in `faceName` at `px`: {width, ascent, descent} of the ink, squeeze and
   * letter-spacing (in em) included.
   */
  function measure(ctx, text, faceName, px, spacing = 0) {
    const f = face(faceName);
    // The caller's context may be in any state (drawIPX is public): measure in ours, leave theirs alone.
    ctx.save();
    ctx.font = fontString(f, px);
    ctx.textBaseline = 'alphabetic';
    const m = ctx.measureText(text);
    ctx.restore();
    const gaps = Math.max(0, text.length - 1) * spacing * px;
    return {
      width: (m.width + gaps) * f.squeeze,
      ascent: m.actualBoundingBoxAscent ?? px * 0.72,
      descent: m.actualBoundingBoxDescent ?? 0,
    };
  }

  /**
   * Largest size at which the ink of `text` is at most `inkHeight` tall and `maxWidth` wide.
   * Returns everything draw() needs.
   */
  function fit(ctx, text, faceName, maxWidth, inkHeight, spacing = 0) {
    const ref = measure(ctx, text || 'X', faceName, 100, spacing);
    const ink = Math.max(1, ref.ascent + ref.descent);
    let px = (100 * inkHeight) / ink;
    if (ref.width * (px / 100) > maxWidth) px = (100 * maxWidth) / ref.width;
    px = Math.max(4, px);
    const k = px / 100;
    return { face: faceName, px, spacing, width: ref.width * k, ascent: ref.ascent * k, descent: ref.descent * k };
  }

  /** Same, for a fixed size. */
  function at(ctx, text, faceName, px, spacing = 0) {
    const m = measure(ctx, text, faceName, px, spacing);
    return { face: faceName, px, spacing, width: m.width, ascent: m.ascent, descent: m.descent };
  }

  /**
   * Draws `text` with its ink centred vertically on y. `align` places x at the left edge, centre or
   * right edge of the line. opts: {fill, stroke, lineWidth, align = 'center', lineJoin = 'round'}.
   */
  function draw(ctx, text, x, y, fitted, opts = {}) {
    const f = face(fitted.face);
    const align = opts.align || 'center';
    const left = align === 'center' ? x - fitted.width / 2 : align === 'right' ? x - fitted.width : x;
    const baseline = y + (fitted.ascent - fitted.descent) / 2;
    ctx.save();
    ctx.translate(left, baseline);
    ctx.transform(f.squeeze, 0, f.skew && opts.skew !== false ? f.skew * f.squeeze : 0, 1, 0, 0);
    ctx.font = fontString(f, fitted.px);
    ctx.textAlign = 'left';
    ctx.textBaseline = 'alphabetic';
    ctx.lineJoin = opts.lineJoin || 'round';
    ctx.lineCap = 'round';
    if (opts.lineWidth) ctx.lineWidth = opts.lineWidth / f.squeeze;
    if (opts.fill) ctx.fillStyle = opts.fill;
    if (opts.stroke) ctx.strokeStyle = opts.stroke;
    const put = (str, at0) => {
      if (opts.stroke) ctx.strokeText(str, at0, 0);
      if (opts.fill) ctx.fillText(str, at0, 0);
    };
    if (!fitted.spacing) {
      put(text, 0);
    } else {
      // Tracked text: glyph by glyph (kerning is lost, which tracked capitals do not miss).
      let cursor = 0;
      for (const ch of text) {
        put(ch, cursor);
        cursor += ctx.measureText(ch).width + fitted.spacing * fitted.px;
      }
    }
    ctx.restore();
  }

  return { faces, available, measure, fit, at, draw, hasCondensed: !!condensed, hasHand: !!hand };
}
