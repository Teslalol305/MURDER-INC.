// The prop atlas: every small picture the props carry (plates, taxi lettering, street signs, labels,
// the IPX marks, the Vulture stencil …) on one canvas, so they all share one texture and two materials
// (lit by the scene, or glowing). Layout is pure arithmetic and known before anything is drawn, so
// builders (and the node tests) can ask for UV rectangles without a canvas.
//
// Region coordinates are in "base pixels" of a 2048 × 1024 sheet; the canvas itself may be smaller
// (the drawing context is scaled). Each draw function works inside its own clipped w × h box.

export const ATLAS_W = 2048;
export const ATLAS_H = 1024;
const GUTTER = 6;

const INK = '#f4f2ec';
const GOLD = '#f6c21a';
const PLATE = '#0f1114';
const OXBLOOD = '#8a1820';
const NAVY = '#16264f';

const PLATES = ['HLS·2141', 'JRZ·9907', 'KQB·5530', 'DMX·4418'];
export const MEDALLION = '5K83';

// ------------------------------------------------------------------------------------------------
// Drawing helpers
// ------------------------------------------------------------------------------------------------

/** One line of text, shrunk until it fits maxW. o: {font, weight, color, align, italic, maxW, track} */
function label(ctx, t, str, x, y, px, o = {}) {
  const family = o.font === 'display' ? t.fonts.display : o.font === 'mono' ? t.fonts.mono : t.fonts.ui;
  const style = `${o.italic ? 'italic ' : ''}${o.weight ?? 700}`;
  ctx.textAlign = o.align ?? 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = o.color ?? INK;
  if ('letterSpacing' in ctx) ctx.letterSpacing = `${o.track ?? 0}px`;
  let size = px;
  for (let i = 0; i < 24; i++) {
    ctx.font = `${style} ${size}px ${family}`;
    if (!o.maxW || ctx.measureText(str).width <= o.maxW) break;
    size *= 0.94;
  }
  ctx.fillText(str, x, y);
  if ('letterSpacing' in ctx) ctx.letterSpacing = '0px';
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function fillRect(ctx, color, x, y, w, h) {
  ctx.fillStyle = color;
  ctx.fillRect(x, y, w, h);
}

/** Deterministic pseudo-random numbers for speckle and scrawl (no Math.random: the sheet must not change between runs). */
function noise(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let v = Math.imul(s ^ (s >>> 15), 1 | s);
    v = (v + Math.imul(v ^ (v >>> 7), 61 | v)) ^ v;
    return ((v ^ (v >>> 14)) >>> 0) / 4294967296;
  };
}

/** Diagonal warning stripes across the whole box. */
function stripes(ctx, w, h, a, b, pitch) {
  fillRect(ctx, a, 0, 0, w, h);
  ctx.fillStyle = b;
  for (let x = -h; x < w + h; x += pitch * 2) {
    ctx.beginPath();
    ctx.moveTo(x, h);
    ctx.lineTo(x + pitch, h);
    ctx.lineTo(x + pitch + h, 0);
    ctx.lineTo(x + h, 0);
    ctx.closePath();
    ctx.fill();
  }
}

/** Spray-paint roughness: knocks small holes into what has been drawn so far. */
function distress(ctx, w, h, seed, amount = 0.12) {
  const rnd = noise(seed);
  ctx.save();
  ctx.globalCompositeOperation = 'destination-out';
  for (let i = 0; i < w * h * amount * 0.02; i++) {
    ctx.globalAlpha = 0.25 + rnd() * 0.6;
    const r = 0.6 + rnd() * 2.2;
    ctx.beginPath();
    ctx.arc(rnd() * w, rnd() * h, r, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

/** A fast marker scrawl: a few looping strokes, no letters. */
function scrawl(ctx, w, h, seed, color) {
  const rnd = noise(seed);
  ctx.strokeStyle = color;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.lineWidth = h * 0.07;
  let x = w * 0.08;
  const base = h * 0.62;
  ctx.beginPath();
  ctx.moveTo(x, base);
  while (x < w * 0.86) {
    const step = w * (0.08 + rnd() * 0.1);
    const up = h * (0.2 + rnd() * 0.42);
    ctx.bezierCurveTo(x + step * 0.1, base - up, x + step * 0.7, base - up * (0.6 + rnd() * 0.5), x + step * 0.55, base + h * 0.05 * rnd());
    ctx.quadraticCurveTo(x + step * 0.8, base + h * 0.22 * rnd(), x + step, base - h * 0.04);
    x += step;
  }
  ctx.stroke();
  // Underline flick and a dot: every tag has them.
  ctx.lineWidth = h * 0.045;
  ctx.beginPath();
  ctx.moveTo(w * 0.1, h * 0.82);
  ctx.quadraticCurveTo(w * 0.5, h * (0.74 + rnd() * 0.12), w * 0.93, h * 0.8);
  ctx.stroke();
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(w * 0.94, h * 0.3, h * 0.045, 0, Math.PI * 2);
  ctx.fill();
}

/** The Vulture crew mark: a hunched bird on a wire, cut like a spray stencil. */
function vulture(ctx, w, h, color) {
  ctx.save();
  ctx.scale(w / 320, h / 256);
  ctx.fillStyle = color;
  ctx.strokeStyle = color;
  // Body and folded wings: one hunched mass.
  ctx.beginPath();
  ctx.moveTo(86, 214);
  ctx.bezierCurveTo(60, 170, 70, 96, 128, 58);
  ctx.bezierCurveTo(150, 42, 182, 44, 196, 62);
  ctx.bezierCurveTo(214, 86, 212, 132, 196, 168);
  ctx.bezierCurveTo(188, 190, 172, 206, 150, 214);
  ctx.closePath();
  ctx.fill();
  // Tail feathers below the wire.
  ctx.beginPath();
  ctx.moveTo(92, 206);
  ctx.lineTo(70, 250);
  ctx.lineTo(96, 232);
  ctx.lineTo(102, 254);
  ctx.lineTo(122, 230);
  ctx.lineTo(134, 250);
  ctx.lineTo(146, 210);
  ctx.closePath();
  ctx.fill();
  // Neck: stretched forward and down from the shoulders.
  ctx.lineWidth = 17;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(186, 70);
  ctx.quadraticCurveTo(222, 62, 238, 88);
  ctx.stroke();
  // Bald head and hooked beak.
  ctx.beginPath();
  ctx.arc(244, 96, 17, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.moveTo(254, 86);
  ctx.quadraticCurveTo(292, 92, 288, 124);
  ctx.quadraticCurveTo(278, 110, 250, 112);
  ctx.closePath();
  ctx.fill();
  // The wire it sits on.
  ctx.lineWidth = 7;
  ctx.beginPath();
  ctx.moveTo(18, 212);
  ctx.lineTo(302, 212);
  ctx.stroke();
  // Stencil bridges: eye, neck ruff, wing bars.
  ctx.globalCompositeOperation = 'destination-out';
  ctx.beginPath();
  ctx.arc(248, 93, 4.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.lineWidth = 6;
  ctx.beginPath();
  ctx.moveTo(176, 52);
  ctx.quadraticCurveTo(196, 74, 190, 98);
  ctx.stroke();
  ctx.lineWidth = 5;
  for (const [x0, y0, x1, y1] of [[96, 150, 150, 88], [112, 178, 172, 110], [134, 196, 190, 136]]) {
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.quadraticCurveTo((x0 + x1) / 2 - 12, (y0 + y1) / 2 - 6, x1, y1);
    ctx.stroke();
  }
  ctx.restore();
}

function arrow(ctx, x0, y, x1, head, thick, color) {
  const dir = Math.sign(x1 - x0);
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(x0, y - thick / 2);
  ctx.lineTo(x1 - dir * head, y - thick / 2);
  ctx.lineTo(x1 - dir * head, y - head * 0.75);
  ctx.lineTo(x1, y);
  ctx.lineTo(x1 - dir * head, y + head * 0.75);
  ctx.lineTo(x1 - dir * head, y + thick / 2);
  ctx.lineTo(x0, y + thick / 2);
  ctx.closePath();
  ctx.fill();
}

function upArrow(ctx, x, y, s, color) {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(x, y - s);
  ctx.lineTo(x + s * 0.7, y - s * 0.1);
  ctx.lineTo(x + s * 0.28, y - s * 0.1);
  ctx.lineTo(x + s * 0.28, y + s);
  ctx.lineTo(x - s * 0.28, y + s);
  ctx.lineTo(x - s * 0.28, y - s * 0.1);
  ctx.lineTo(x - s * 0.7, y - s * 0.1);
  ctx.closePath();
  ctx.fill();
}

function speaker(ctx, cx, cy, r) {
  ctx.fillStyle = '#b9bcc0';
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#0b0b0d';
  ctx.beginPath();
  ctx.arc(cx, cy, r * 0.9, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = '#2c2d31';
  ctx.lineWidth = r * 0.07;
  for (const k of [0.72, 0.52]) {
    ctx.beginPath();
    ctx.arc(cx, cy, r * k, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.fillStyle = '#3a3b40';
  ctx.beginPath();
  ctx.arc(cx, cy, r * 0.28, 0, Math.PI * 2);
  ctx.fill();
}

function plate(ctx, t, w, h, text, taxi) {
  ctx.fillStyle = taxi ? '#f0c63a' : '#f1efe6';
  roundRect(ctx, 2, 2, w - 4, h - 4, 7);
  ctx.fill();
  ctx.strokeStyle = NAVY;
  ctx.lineWidth = 2.5;
  roundRect(ctx, 5, 5, w - 10, h - 10, 5);
  ctx.stroke();
  fillRect(ctx, taxi ? NAVY : '#d9a21c', 8, h - 15, w - 16, 5);
  label(ctx, t, 'NEW YORK', w / 2, 14, 10, { color: NAVY, weight: 700, track: 1.5 });
  label(ctx, t, text, w / 2, h * 0.56, 30, { color: NAVY, weight: 800, maxW: w - 20, font: 'display', track: 1 });
}

// ------------------------------------------------------------------------------------------------
// Regions: name, base size, draw(ctx, w, h, tools). tools = {drawIPX, fonts, brand}
// ------------------------------------------------------------------------------------------------

const REGIONS = [];
const region = (name, w, h, draw) => REGIONS.push({ name, w, h, draw });

// ---- IPX -------------------------------------------------------------------------------------

region('ipx_side', 1024, 256, (ctx, w, h, t) => {
  const mark = t.drawIPX(ctx, 250, h / 2, 210, INK);
  const x = 250 + mark / 2 + 54;
  fillRect(ctx, GOLD, x, h / 2 - 40, 5, 80);
  label(ctx, t, t.brand.ipx.url, x + 28, h / 2, 54, { align: 'left', weight: 700, track: 8, maxW: w - x - 50 });
});

region('ipx_mark', 384, 160, (ctx, w, h, t) => {
  t.drawIPX(ctx, w / 2, h / 2, 132, INK);
});

region('ipx_url', 384, 48, (ctx, w, h, t) => {
  label(ctx, t, t.brand.ipx.url, w / 2, h / 2, 30, { weight: 700, track: 6, maxW: w - 12 });
});

region('ipx_tag', 160, 80, (ctx, w, h, t) => {
  ctx.fillStyle = '#f1efe6';
  roundRect(ctx, 1, 1, w - 2, h - 2, 6);
  ctx.fill();
  t.drawIPX(ctx, 54, 30, 40, PLATE);
  label(ctx, t, 'TRACKER', 124, 30, 13, { color: PLATE, weight: 800, maxW: 60 });
  // A barcode: nobody will read it, everybody recognises it.
  const rnd = noise(77);
  ctx.fillStyle = PLATE;
  for (let x = 12; x < w - 12; ) {
    const bar = 1 + Math.floor(rnd() * 3);
    ctx.fillRect(x, 54, bar, 16);
    x += bar + 1 + Math.floor(rnd() * 3);
  }
});

region('ipx_ad', 320, 480, (ctx, w, h, t) => {
  const bg = ctx.createLinearGradient(0, 0, 0, h);
  bg.addColorStop(0, '#191b20');
  bg.addColorStop(1, '#0a0b0d');
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, w, h);
  fillRect(ctx, INK, 28, 40, w - 56, 2);
  label(ctx, t, t.brand.presenter, w / 2, 62, 19, { weight: 700, track: 5, maxW: w - 60 });
  const [first, ...rest] = t.brand.title.split(' ');
  label(ctx, t, first, w / 2, 164, 104, { font: 'display', weight: 400, maxW: w - 44 });
  label(ctx, t, rest.join(' '), w / 2, 262, 104, { font: 'display', weight: 400, maxW: w - 44, color: GOLD });
  label(ctx, t, t.brand.starLine, w / 2, 330, 18, { weight: 700, track: 4, maxW: w - 60 });
  fillRect(ctx, GOLD, w / 2 - 24, 356, 48, 3);
  t.drawIPX(ctx, w / 2, 406, 58, INK);
  label(ctx, t, t.brand.ipx.url, w / 2, 452, 14, { weight: 600, track: 4, color: '#a9a7a0' });
});

region('tracker_lcd', 96, 40, (ctx, w, h, t) => {
  fillRect(ctx, '#0a0f0a', 0, 0, w, h);
  label(ctx, t, 'IPX', 24, h / 2 + 1, 20, { color: GOLD, weight: 800, italic: true });
  for (let i = 0; i < 4; i++) fillRect(ctx, GOLD, 50 + i * 10, 28 - i * 6, 6, 6 + i * 6);
});

// ---- the Vultures -----------------------------------------------------------------------------

region('vulture', 320, 256, (ctx, w, h) => {
  vulture(ctx, w, h, '#e9e4d6');
  distress(ctx, w, h, 11, 0.5);
});

region('tag_a', 256, 112, (ctx, w, h) => scrawl(ctx, w, h, 5, '#e9e4d6'));
region('tag_b', 256, 112, (ctx, w, h) => scrawl(ctx, w, h, 23, OXBLOOD));
region('tag_c', 256, 112, (ctx, w, h) => scrawl(ctx, w, h, 61, '#101113'));

// ---- vehicles ---------------------------------------------------------------------------------

PLATES.forEach((text, i) => region(`plate_${i}`, 128, 64, (ctx, w, h, t) => plate(ctx, t, w, h, text, false)));
region('plate_taxi', 128, 64, (ctx, w, h, t) => plate(ctx, t, w, h, `T·${MEDALLION}`, true));

region('taxi_door', 320, 128, (ctx, w, h, t) => {
  label(ctx, t, 'NYC TAXI', w / 2, 40, 62, { color: '#0c0c0d', font: 'display', weight: 400, maxW: w - 16, track: 2 });
  label(ctx, t, MEDALLION, 78, 96, 40, { color: '#0c0c0d', weight: 800 });
  // The fare box: a ruled card.
  ctx.strokeStyle = '#0c0c0d';
  ctx.lineWidth = 2.5;
  ctx.strokeRect(160, 76, 146, 42);
  for (let i = 0; i < 3; i++) fillRect(ctx, '#0c0c0d', 168, 84 + i * 11, 130 - i * 26, 4);
});

region('taxi_roof', 160, 56, (ctx, w, h, t) => {
  const bg = ctx.createLinearGradient(0, 0, 0, h);
  bg.addColorStop(0, '#fff3c4');
  bg.addColorStop(1, '#f5c637');
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, w, h);
  label(ctx, t, MEDALLION, w / 2, h / 2 + 1, 40, { color: '#141414', weight: 800, maxW: w - 16 });
});

region('checker', 256, 32, (ctx, w, h) => {
  const s = h / 2;
  for (let i = 0; i < w / s; i++) {
    fillRect(ctx, i % 2 ? '#0c0c0d' : '#f1efe6', i * s, 0, s, s);
    fillRect(ctx, i % 2 ? '#f1efe6' : '#0c0c0d', i * s, s, s, s);
  }
});

region('stripes_ow', 256, 40, (ctx, w, h) => stripes(ctx, w, h, '#f1efe6', '#e8641b', 26));
region('stripes_yb', 256, 40, (ctx, w, h) => stripes(ctx, w, h, '#f2c21a', '#101113', 22));
region('stripes_rw', 256, 40, (ctx, w, h) => stripes(ctx, w, h, '#f1efe6', '#c2261e', 26));

// ---- street signs -------------------------------------------------------------------------------

region('sign_nopark', 128, 176, (ctx, w, h, t) => {
  fillRect(ctx, '#f1efe6', 0, 0, w, h);
  ctx.strokeStyle = '#c2261e';
  ctx.lineWidth = 5;
  ctx.strokeRect(6, 6, w - 12, h - 12);
  label(ctx, t, 'NO', w / 2, 40, 46, { color: '#c2261e', font: 'display', weight: 400 });
  label(ctx, t, 'PARKING', w / 2, 84, 34, { color: '#c2261e', font: 'display', weight: 400, maxW: w - 24 });
  label(ctx, t, 'ANYTIME', w / 2, 118, 20, { color: '#c2261e', weight: 800, maxW: w - 28 });
  arrow(ctx, w / 2, 146, w - 20, 16, 7, '#c2261e');
  arrow(ctx, w / 2, 146, 20, 16, 7, '#c2261e');
});

region('sign_bus', 128, 176, (ctx, w, h, t) => {
  fillRect(ctx, '#f1efe6', 0, 0, w, h);
  fillRect(ctx, '#1f4f9a', 0, 0, w, 74);
  // A bus, front on.
  ctx.fillStyle = '#f1efe6';
  roundRect(ctx, 38, 12, 52, 48, 8);
  ctx.fill();
  fillRect(ctx, '#1f4f9a', 44, 20, 40, 18);
  fillRect(ctx, '#1f4f9a', 46, 46, 8, 6);
  fillRect(ctx, '#1f4f9a', 74, 46, 8, 6);
  label(ctx, t, 'BUS', w / 2, 100, 34, { color: '#1f4f9a', font: 'display', weight: 400 });
  label(ctx, t, 'STOP', w / 2, 134, 34, { color: '#1f4f9a', font: 'display', weight: 400 });
  label(ctx, t, 'NO STANDING', w / 2, 162, 13, { color: '#c2261e', weight: 800, maxW: w - 16 });
});

region('sign_oneway', 256, 80, (ctx, w, h, t) => {
  fillRect(ctx, '#0c0c0d', 0, 0, w, h);
  ctx.strokeStyle = '#f1efe6';
  ctx.lineWidth = 3;
  ctx.strokeRect(4, 4, w - 8, h - 8);
  arrow(ctx, 20, h / 2, w - 18, 44, 40, '#f1efe6');
  label(ctx, t, 'ONE WAY', w / 2 - 14, h / 2 + 1, 30, { color: '#0c0c0d', weight: 800, maxW: 150 });
});

region('sign_stop', 128, 128, (ctx, w, h, t) => {
  const c = w / 2;
  const r = w / 2 - 3;
  const octagon = (radius) => {
    ctx.beginPath();
    for (let i = 0; i < 8; i++) {
      const a = Math.PI / 8 + (i * Math.PI) / 4;
      ctx.lineTo(c + Math.cos(a) * radius, c + Math.sin(a) * radius);
    }
    ctx.closePath();
  };
  ctx.fillStyle = '#f1efe6';
  octagon(r);
  ctx.fill();
  ctx.fillStyle = '#c2261e';
  octagon(r - 5);
  ctx.fill();
  label(ctx, t, 'STOP', c, c + 2, 44, { color: '#f1efe6', font: 'display', weight: 400, maxW: w - 30 });
});

// ---- street furniture ---------------------------------------------------------------------------

region('news', 128, 160, (ctx, w, h, t) => {
  fillRect(ctx, '#e6e1d2', 0, 0, w, h);
  label(ctx, t, 'QUEENS NIGHT LEDGER', w / 2, 16, 13, { color: '#141414', font: 'display', weight: 400, maxW: w - 12 });
  fillRect(ctx, '#141414', 8, 27, w - 16, 2);
  label(ctx, t, 'THREE REELS', w / 2, 48, 24, { color: '#141414', font: 'display', weight: 400, maxW: w - 14 });
  label(ctx, t, 'GONE', w / 2, 74, 28, { color: '#141414', font: 'display', weight: 400 });
  fillRect(ctx, '#77756c', 8, 94, 60, 56);
  for (let i = 0; i < 7; i++) fillRect(ctx, '#55534c', 74, 96 + i * 8, 46 - (i % 3) * 8, 3);
});

region('mail', 128, 96, (ctx, w, h, t) => {
  fillRect(ctx, '#f1efe6', 0, 0, w, h);
  fillRect(ctx, NAVY, 0, 0, w, 40);
  label(ctx, t, 'MAIL', w / 2, 21, 30, { color: '#f1efe6', font: 'display', weight: 400, track: 4 });
  for (let i = 0; i < 4; i++) fillRect(ctx, '#5a5c63', 12, 50 + i * 10, w - 24 - (i % 2) * 30, 3);
});

region('meter', 64, 96, (ctx, w, h, t) => {
  fillRect(ctx, '#1a1b1e', 0, 0, w, h);
  ctx.fillStyle = '#e6e1d2';
  ctx.beginPath();
  ctx.arc(w / 2, 46, 26, Math.PI, 0);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = '#c2261e';
  ctx.beginPath();
  ctx.moveTo(w / 2, 46);
  ctx.arc(w / 2, 46, 24, Math.PI, Math.PI * 1.34);
  ctx.closePath();
  ctx.fill();
  label(ctx, t, '1 HR', w / 2, 62, 14, { color: '#e6e1d2', weight: 800 });
  label(ctx, t, '25¢', w / 2, 80, 14, { color: GOLD, weight: 800 });
});

region('phone_sign', 192, 48, (ctx, w, h, t) => {
  fillRect(ctx, '#e9f1ff', 0, 0, w, h);
  fillRect(ctx, '#1f4f9a', 0, 0, 48, h);
  // Handset.
  ctx.strokeStyle = '#e9f1ff';
  ctx.lineWidth = 7;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.arc(24, 34, 16, Math.PI * 1.15, Math.PI * 1.85);
  ctx.stroke();
  label(ctx, t, 'PHONE', 118, h / 2 + 1, 32, { color: '#1f4f9a', font: 'display', weight: 400, track: 3 });
});

region('phone_unit', 128, 160, (ctx, w, h, t) => {
  fillRect(ctx, '#17181b', 0, 0, w, h);
  fillRect(ctx, '#d8d4c6', 12, 10, w - 24, 34);
  for (let i = 0; i < 3; i++) fillRect(ctx, '#3a3b40', 18, 17 + i * 9, w - 40 - i * 14, 3);
  for (let r = 0; r < 4; r++) {
    for (let c = 0; c < 3; c++) {
      ctx.fillStyle = '#9a9da3';
      roundRect(ctx, 26 + c * 27, 56 + r * 21, 21, 15, 3);
      ctx.fill();
    }
  }
  fillRect(ctx, '#050506', 54, 144, 20, 5);
  label(ctx, t, '25¢', 100, 146, 12, { color: GOLD, weight: 800 });
});

region('vend', 192, 384, (ctx, w, h, t) => {
  const bg = ctx.createLinearGradient(0, 0, w, h);
  bg.addColorStop(0, '#0d3a8c');
  bg.addColorStop(0.55, '#1877c9');
  bg.addColorStop(1, '#35d0e0');
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, w, h);
  // Fizz.
  const rnd = noise(404);
  ctx.fillStyle = 'rgba(255,255,255,0.35)';
  for (let i = 0; i < 46; i++) {
    ctx.beginPath();
    ctx.arc(rnd() * w, h * 0.3 + rnd() * h * 0.7, 2 + rnd() * 7, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.fillStyle = '#f4f2ec';
  ctx.beginPath();
  ctx.moveTo(0, 150);
  ctx.bezierCurveTo(60, 110, 120, 200, w, 138);
  ctx.lineTo(w, 164);
  ctx.bezierCurveTo(120, 226, 60, 136, 0, 176);
  ctx.closePath();
  ctx.fill();
  label(ctx, t, 'ICE', w / 2, 52, 62, { font: 'display', weight: 400, italic: true });
  label(ctx, t, 'COLD', w / 2, 108, 62, { font: 'display', weight: 400, italic: true });
  label(ctx, t, 'SODA', w / 2, 250, 76, { font: 'display', weight: 400, maxW: w - 20 });
  ctx.fillStyle = '#f6c21a';
  roundRect(ctx, w / 2 - 44, 300, 88, 44, 10);
  ctx.fill();
  label(ctx, t, '$1.00', w / 2, 323, 30, { color: '#141414', weight: 800 });
});

region('ped_stop', 64, 64, (ctx, w, h) => {
  fillRect(ctx, '#050505', 0, 0, w, h);
  ctx.fillStyle = '#ff7a1a';
  roundRect(ctx, 20, 26, 26, 28, 7);
  ctx.fill();
  for (let i = 0; i < 4; i++) {
    roundRect(ctx, 20 + i * 6.6, 10 + (i === 0 || i === 3 ? 4 : 0), 5.4, 22, 2.5);
    ctx.fill();
  }
  roundRect(ctx, 11, 30, 12, 6, 3);
  ctx.fill();
});

region('ped_walk', 64, 64, (ctx, w, h) => {
  fillRect(ctx, '#050505', 0, 0, w, h);
  ctx.fillStyle = '#f4f8ff';
  ctx.strokeStyle = '#f4f8ff';
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.arc(36, 12, 5.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.lineWidth = 6;
  ctx.beginPath();
  ctx.moveTo(34, 21);
  ctx.lineTo(30, 38);
  ctx.moveTo(30, 38);
  ctx.lineTo(40, 56);
  ctx.moveTo(30, 38);
  ctx.lineTo(20, 56);
  ctx.stroke();
  ctx.lineWidth = 4.5;
  ctx.beginPath();
  ctx.moveTo(34, 24);
  ctx.lineTo(46, 34);
  ctx.moveTo(33, 24);
  ctx.lineTo(21, 32);
  ctx.stroke();
});

region('stickers', 96, 128, (ctx, w, h) => {
  const rnd = noise(9);
  const inks = ['#e2222b', '#f6c21a', '#39d0e0', '#f4f2ec', '#55ff8a', '#101113'];
  for (let i = 0; i < 9; i++) {
    ctx.save();
    ctx.translate(12 + rnd() * (w - 34), 10 + rnd() * (h - 34));
    ctx.rotate((rnd() - 0.5) * 0.7);
    const sw = 18 + rnd() * 22;
    const sh = 12 + rnd() * 16;
    fillRect(ctx, '#f4f2ec', -1.5, -1.5, sw + 3, sh + 3);
    fillRect(ctx, inks[i % inks.length], 0, 0, sw, sh);
    fillRect(ctx, 'rgba(0,0,0,0.55)', 3, sh * 0.4, sw - 6, 2.5);
    ctx.restore();
  }
});

// ---- carts, booths, shop --------------------------------------------------------------------------

region('cart_menu', 320, 112, (ctx, w, h, t) => {
  fillRect(ctx, '#c2261e', 0, 0, w, h);
  fillRect(ctx, '#f2c21a', 0, 0, w, 8);
  fillRect(ctx, '#f2c21a', 0, h - 8, w, 8);
  label(ctx, t, 'HOT DOGS', 96, 40, 40, { color: '#f2c21a', font: 'display', weight: 400, maxW: 172 });
  label(ctx, t, 'PRETZELS · COLD SODA', 96, 80, 18, { weight: 800, maxW: 176 });
  fillRect(ctx, '#f4f2ec', 196, 18, 2, h - 36);
  [['HOT DOG', '1.50'], ['SAUSAGE', '2.50'], ['PRETZEL', '1.25'], ['SODA', '1.00']].forEach(([name, price], i) => {
    label(ctx, t, name, 208, 27 + i * 19, 14, { align: 'left', weight: 700 });
    label(ctx, t, price, w - 12, 27 + i * 19, 14, { align: 'right', weight: 800, color: '#f2c21a' });
  });
});

region('booth_sign', 320, 112, (ctx, w, h, t) => {
  fillRect(ctx, '#0c0c0d', 0, 0, w, h);
  ctx.strokeStyle = '#f2c21a';
  ctx.lineWidth = 4;
  ctx.strokeRect(5, 5, w - 10, h - 10);
  label(ctx, t, 'PARK', 122, h / 2 + 3, 92, { color: '#f6c21a', font: 'display', weight: 400, track: 4, maxW: 210 });
  label(ctx, t, '24', 270, 40, 44, { font: 'display', weight: 400 });
  label(ctx, t, 'HOURS', 270, 80, 18, { weight: 800 });
});

region('booth_rates', 160, 208, (ctx, w, h, t) => {
  fillRect(ctx, '#f1efe6', 0, 0, w, h);
  fillRect(ctx, '#141414', 0, 0, w, 44);
  label(ctx, t, 'RATES', w / 2, 23, 30, { font: 'display', weight: 400, track: 4 });
  [['FIRST HOUR', '$6'], ['EACH ADD’L', '$3'], ['ALL NIGHT', '$14'], ['LOST TICKET', '$30']].forEach(([name, price], i) => {
    label(ctx, t, name, 12, 68 + i * 30, 15, { align: 'left', color: '#141414', weight: 700 });
    label(ctx, t, price, w - 12, 68 + i * 30, 17, { align: 'right', color: '#c2261e', weight: 800 });
    fillRect(ctx, '#b9b5a8', 12, 82 + i * 30, w - 24, 1.5);
  });
  label(ctx, t, 'NO IN & OUT', w / 2, 190, 13, { color: '#141414', weight: 800 });
});

region('dumpster', 320, 64, (ctx, w, h, t) => {
  label(ctx, t, 'HOLLIS CARTING', w / 2, 22, 30, { font: 'display', weight: 400, maxW: w - 12, track: 2 });
  label(ctx, t, '718 · 555 · 0144', w / 2, 50, 17, { weight: 800, track: 2 });
  distress(ctx, w, h, 31, 0.6);
});

region('crate_stencil', 192, 128, (ctx, w, h, t) => {
  const ink = '#161310';
  label(ctx, t, 'FRAGILE', 118, 38, 40, { color: ink, font: 'display', weight: 400, maxW: 130, track: 3 });
  label(ctx, t, 'HANDLE WITH CARE', 118, 76, 13, { color: ink, weight: 800, maxW: 132 });
  label(ctx, t, 'LOT 0214 · QNS', 118, 104, 13, { color: ink, weight: 800, font: 'mono', maxW: 132 });
  upArrow(ctx, 22, 64, 26, ink);
  ctx.fillRect(8, 98, 28, 5);
  distress(ctx, w, h, 14, 0.45);
});

region('cardboard', 128, 128, (ctx, w, h, t) => {
  const ink = '#3d2c18';
  upArrow(ctx, 26, 34, 20, ink);
  upArrow(ctx, 62, 34, 20, ink);
  label(ctx, t, 'THIS SIDE UP', 44, 68, 11, { color: ink, weight: 800, maxW: 84 });
  fillRect(ctx, '#ece8dc', 60, 82, 60, 38);
  const rnd = noise(3);
  ctx.fillStyle = '#1a1a1a';
  for (let x = 66; x < 114; ) {
    const bar = 1 + Math.floor(rnd() * 3);
    ctx.fillRect(x, 88, bar, 16);
    x += bar + 1 + Math.floor(rnd() * 2);
  }
  fillRect(ctx, '#1a1a1a', 66, 110, 40, 3);
});

region('drum_label', 128, 80, (ctx, w, h, t) => {
  fillRect(ctx, '#ece8dc', 0, 0, w, h);
  fillRect(ctx, '#141414', 0, 0, w, 22);
  label(ctx, t, 'MOTOR OIL', w / 2, 12, 15, { weight: 800, maxW: w - 10 });
  label(ctx, t, '10W-40', w / 2, 42, 24, { color: '#141414', font: 'display', weight: 400 });
  label(ctx, t, '55 GAL · 208 L', w / 2, 66, 11, { color: '#141414', weight: 700 });
});

region('gauges', 128, 128, (ctx, w, h) => {
  fillRect(ctx, '#1b1c1f', 0, 0, w, h);
  for (const [cx, col] of [[36, '#e6e1d2'], [92, '#e6e1d2']]) {
    ctx.fillStyle = col;
    ctx.beginPath();
    ctx.arc(cx, 40, 24, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#c2261e';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.arc(cx, 40, 19, -0.5, 0.6);
    ctx.stroke();
    ctx.strokeStyle = '#141414';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(cx, 40);
    ctx.lineTo(cx + (cx < 60 ? -10 : 13), 26);
    ctx.stroke();
  }
  for (let i = 0; i < 4; i++) {
    ctx.fillStyle = i === 0 ? '#3ddc6a' : i === 3 ? '#c2261e' : '#8d949a';
    roundRect(ctx, 14 + i * 27, 82, 18, 26, 3);
    ctx.fill();
  }
});

region('gen_label', 192, 80, (ctx, w, h, t) => {
  fillRect(ctx, '#f2c21a', 0, 0, w, h);
  fillRect(ctx, '#141414', 0, 0, w, 30);
  label(ctx, t, 'DANGER', w / 2, 16, 24, { color: '#f2c21a', font: 'display', weight: 400, track: 4 });
  label(ctx, t, 'HIGH VOLTAGE', w / 2, 46, 18, { color: '#141414', weight: 800, maxW: w - 14 });
  label(ctx, t, '60 kW · 480 V', w / 2, 66, 12, { color: '#141414', weight: 700 });
});

region('porta', 128, 96, (ctx, w, h, t) => {
  fillRect(ctx, '#f1efe6', 0, 0, w, h);
  label(ctx, t, 'HOLLIS', w / 2, 24, 26, { color: '#1f4f9a', font: 'display', weight: 400, track: 3 });
  label(ctx, t, 'SITE SERVICES', w / 2, 50, 13, { color: '#1f4f9a', weight: 800, maxW: w - 12 });
  label(ctx, t, 'UNIT 14', w / 2, 76, 16, { color: '#141414', weight: 800, font: 'mono' });
});

region('flame', 96, 96, (ctx, w, h, t) => {
  const c = w / 2;
  ctx.fillStyle = '#f1efe6';
  ctx.beginPath();
  ctx.moveTo(c, 1);
  ctx.lineTo(w - 1, c);
  ctx.lineTo(c, h - 1);
  ctx.lineTo(1, c);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = '#d3281f';
  ctx.beginPath();
  ctx.moveTo(c, 6);
  ctx.lineTo(w - 6, c);
  ctx.lineTo(c, h - 6);
  ctx.lineTo(6, c);
  ctx.closePath();
  ctx.fill();
  // Flame.
  ctx.fillStyle = '#f4f2ec';
  ctx.beginPath();
  ctx.moveTo(c - 2, 22);
  ctx.bezierCurveTo(c + 16, 34, c + 13, 46, c + 5, 54);
  ctx.bezierCurveTo(c + 9, 44, c + 2, 40, c + 1, 36);
  ctx.bezierCurveTo(c - 4, 44, c - 12, 46, c - 9, 56);
  ctx.bezierCurveTo(c - 19, 46, c - 10, 34, c - 2, 22);
  ctx.fill();
  fillRect(ctx, '#f4f2ec', c - 13, 58, 26, 3.5);
  label(ctx, t, '2', c, 76, 16, { weight: 800 });
});

region('gas_placard', 160, 112, (ctx, w, h, t) => {
  fillRect(ctx, '#f1efe6', 0, 0, w, h);
  fillRect(ctx, '#c2261e', 0, 0, w, 36);
  label(ctx, t, 'DANGER', w / 2, 19, 28, { font: 'display', weight: 400, track: 4 });
  label(ctx, t, 'FLAMMABLE GAS', w / 2, 58, 17, { color: '#141414', weight: 800, maxW: w - 14 });
  label(ctx, t, 'NO SMOKING', w / 2, 80, 15, { color: '#c2261e', weight: 800 });
  label(ctx, t, 'NO OPEN FLAME', w / 2, 98, 12, { color: '#141414', weight: 700 });
});

region('backboard', 256, 160, (ctx, w, h) => {
  ctx.strokeStyle = '#e8641b';
  ctx.lineWidth = 9;
  ctx.strokeRect(6, 6, w - 12, h - 12);
  ctx.lineWidth = 7;
  ctx.strokeRect(w / 2 - 42, h - 86, 84, 62);
  distress(ctx, w, h, 8, 0.35);
});

region('ticking', 128, 128, (ctx, w, h) => {
  fillRect(ctx, '#b9b3a2', 0, 0, w, h);
  for (let x = 6; x < w; x += 16) {
    fillRect(ctx, '#4a5f86', x, 0, 3, h);
    fillRect(ctx, '#7c8aa8', x + 6, 0, 1.5, h);
  }
  const rnd = noise(52);
  for (let i = 0; i < 5; i++) {
    const g = ctx.createRadialGradient(0, 0, 2, 0, 0, 18 + rnd() * 22);
    g.addColorStop(0, 'rgba(70,50,25,0.5)');
    g.addColorStop(1, 'rgba(70,50,25,0)');
    ctx.save();
    ctx.translate(rnd() * w, rnd() * h);
    ctx.scale(1.4, 0.8);
    ctx.fillStyle = g;
    ctx.fillRect(-48, -48, 96, 96);
    ctx.restore();
  }
});

// ---- the master reel ---------------------------------------------------------------------------

region('reel_label', 160, 160, (ctx, w, h, t) => {
  fillRect(ctx, '#e6dfc8', 0, 0, w, h);
  fillRect(ctx, PLATE, 0, 0, w, 34);
  label(ctx, t, 'MASTER REEL', w / 2, 18, 22, { font: 'display', weight: 400, track: 3, maxW: w - 12 });
  label(ctx, t, t.brand.title, w / 2, 62, 34, { color: '#141414', font: 'display', weight: 400, maxW: w - 16 });
  fillRect(ctx, '#c2261e', 12, 84, w - 24, 3);
  [['REEL', '__ / 3'], ['SPEED', '30 IPS'], ['TAPE', '2 IN · 24 TRK']].forEach(([k, v], i) => {
    label(ctx, t, k, 12, 102 + i * 16, 11, { align: 'left', color: '#55534c', weight: 800 });
    label(ctx, t, v, w - 12, 102 + i * 16, 11, { align: 'right', color: '#141414', weight: 800, font: 'mono' });
  });
  t.drawIPX(ctx, w - 36, 146, 20, '#141414');
});

region('reel_top', 192, 192, (ctx, w) => {
  const c = w / 2;
  const disc = (r, color) => {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(c, c, r, 0, Math.PI * 2);
    ctx.fill();
  };
  disc(94, '#e7b53a'); // flange: the master is on a gold reel
  disc(88, '#2e1c11'); // tape pack
  disc(86, '#422a18');
  // Flange spokes: three wide arms over the tape.
  ctx.fillStyle = '#f0c75a';
  for (let i = 0; i < 3; i++) {
    ctx.save();
    ctx.translate(c, c);
    ctx.rotate((i * Math.PI * 2) / 3 + 0.3);
    ctx.beginPath();
    ctx.moveTo(-17, 0);
    ctx.lineTo(-26, -92);
    ctx.lineTo(26, -92);
    ctx.lineTo(17, 0);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }
  ctx.strokeStyle = '#f0c75a';
  ctx.lineWidth = 7;
  ctx.beginPath();
  ctx.arc(c, c, 90, 0, Math.PI * 2);
  ctx.stroke();
  disc(34, '#f0c75a');
  disc(27, '#17181b');
  disc(9, '#e7b53a');
  ctx.fillStyle = '#e7b53a';
  for (let i = 0; i < 3; i++) {
    ctx.save();
    ctx.translate(c, c);
    ctx.rotate((i * Math.PI * 2) / 3);
    ctx.fillRect(-3, -24, 6, 12);
    ctx.restore();
  }
  // Round the sheet off: nothing outside the flange.
  ctx.globalCompositeOperation = 'destination-in';
  disc(95, '#000');
});

region('boombox', 320, 128, (ctx, w, h) => {
  fillRect(ctx, '#1b1c1f', 0, 0, w, h);
  fillRect(ctx, '#aeb2b7', 0, 0, w, 26);
  // Tuner scale.
  fillRect(ctx, '#0b0b0d', 96, 5, 128, 16);
  for (let i = 0; i < 16; i++) fillRect(ctx, '#f6c21a', 102 + i * 7.6, 8, 1.5, i % 4 ? 6 : 10);
  fillRect(ctx, '#e2222b', 168, 5, 2, 16);
  speaker(ctx, 52, 76, 44);
  speaker(ctx, w - 52, 76, 44);
  // Cassette door.
  ctx.fillStyle = '#2a2b2f';
  roundRect(ctx, 112, 40, 96, 54, 5);
  ctx.fill();
  fillRect(ctx, '#0a0a0b', 122, 50, 76, 26);
  for (const cx of [142, 178]) {
    ctx.fillStyle = '#d6d9dc';
    ctx.beginPath();
    ctx.arc(cx, 63, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#0a0a0b';
    ctx.beginPath();
    ctx.arc(cx, 63, 3.5, 0, Math.PI * 2);
    ctx.fill();
  }
  for (let i = 0; i < 6; i++) fillRect(ctx, i === 0 ? '#e2222b' : '#9a9da3', 113 + i * 16, 102, 13, 14);
});

// ------------------------------------------------------------------------------------------------
// Layout: skyline packing, tallest regions first
// ------------------------------------------------------------------------------------------------

/** name → {x, y, w, h} in base pixels and uv = [u0, v0, u1, v1] (v0 is the bottom edge). */
export function layoutAtlas() {
  const rects = new Map();
  const order = REGIONS.slice().sort((a, b) => b.h - a.h || b.w - a.w);
  // The skyline: the top edge of everything placed so far, as runs of equal height, left to right.
  let skyline = [{ x: 0, y: 0, w: ATLAS_W }];
  for (const r of order) {
    const w = r.w + GUTTER;
    const h = r.h + GUTTER;
    let best = null;
    for (let i = 0; i < skyline.length; i++) {
      const x = skyline[i].x;
      if (x + w > ATLAS_W) break;
      let y = 0;
      for (let j = i, covered = 0; covered < w; covered += skyline[j].w, j++) y = Math.max(y, skyline[j].y);
      if (y + h <= ATLAS_H && (!best || y < best.y)) best = { x, y };
    }
    if (!best) throw new Error(`prop atlas is full: '${r.name}' does not fit`);
    const x = best.x + GUTTER / 2;
    const y = best.y + GUTTER / 2;
    rects.set(r.name, {
      x, y, w: r.w, h: r.h,
      uv: [(x + 0.5) / ATLAS_W, 1 - (y + r.h - 0.5) / ATLAS_H, (x + r.w - 0.5) / ATLAS_W, 1 - (y + 0.5) / ATLAS_H],
    });
    // Raise the skyline under the new rectangle.
    const next = [];
    const x1 = best.x + w;
    for (const run of skyline) {
      const runEnd = run.x + run.w;
      if (runEnd <= best.x || run.x >= x1) next.push(run);
      else {
        if (run.x < best.x) next.push({ x: run.x, y: run.y, w: best.x - run.x });
        if (runEnd > x1) next.push({ x: x1, y: run.y, w: runEnd - x1 });
      }
    }
    next.push({ x: best.x, y: best.y + h, w });
    skyline = next.sort((a, b) => a.x - b.x);
  }
  return rects;
}

/**
 * Draws the whole sheet. `ctx` is a 2D context of a canvas `scale` × the base size.
 * tools: {drawIPX(ctx, cx, cy, h, color), fonts: {ui, display, mono}, brand: config/brand.js}
 */
export function drawAtlas(ctx, scale, rects, tools) {
  for (const r of REGIONS) {
    const rect = rects.get(r.name);
    ctx.save();
    ctx.setTransform(scale, 0, 0, scale, rect.x * scale, rect.y * scale);
    ctx.beginPath();
    ctx.rect(0, 0, r.w, r.h);
    ctx.clip();
    try {
      r.draw(ctx, r.w, r.h, tools);
    } catch (err) {
      console.warn(`[props] atlas region '${r.name}' failed to draw:`, err);
    }
    ctx.restore();
  }
}

export const atlasRegionNames = () => REGIONS.map((r) => r.name);
