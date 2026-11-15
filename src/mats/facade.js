// Facade painter: draws the layout from layout.js as two canvases that the facade material lays over a
// tiling wall (see shader.js).
//
//   overlay   RGBA: everything that is not bare wall (windows, sills, lintels, doors, the shop band,
//             the cornice), transparent elsewhere so the brick underneath stays sharp at any distance
//   emissive  what glows: lit rooms behind blinds and curtains, television blue, a shop still open.
//             Its alpha channel marks glass (0.25) against everything else (1) for the shader.
//
// One canvas spans bays × floors; it repeats along the wall and is clamped at the top.

import { canvas2d, css, mixHex, shade } from './canvas.js';
import { prng } from './noise.js';

const FACADE_PPM = { 256: 22, 512: 40, 1024: 64 };

const WARM = [0xffc070, 0xffd9a0, 0xf4a85a, 0xffcf8a];
const CURTAINS = [0x8a3030, 0x2f506e, 0xd8cfb8, 0x5a6a3a, 0xc9a25a];
const TAGS = [0xe2222b, 0xf6c21a, 0x39d0e0, 0xf4f2ec, 0xff3d9a, 0x101113];
const DOOR = 0x2a1c14;

/**
 * @param s       normalised spec (layout.js facadeSpec)
 * @param layout  facadeLayout(s)
 * @param size    texture tier: 256 | 512 | 1024
 * @returns {{overlay: HTMLCanvasElement, emissive: HTMLCanvasElement}}
 */
export function paintFacade(s, layout, size) {
  const ppm = Math.min(FACADE_PPM[size] || 64, (size * 2) / Math.max(s.w, s.h));
  const W = Math.max(8, Math.round(s.w * ppm));
  const H = Math.max(8, Math.round(s.h * ppm));
  const kx = W / s.w;
  const ky = H / s.h;
  const O = canvas2d(W, H);
  const E = canvas2d(W, H);
  E.fillStyle = '#000';
  E.fillRect(0, 0, W, H);
  const rand = prng(s.seed * 7 + 99);
  const st = layout.style;
  const glassRects = [];

  /** Fills a rectangle given in metres (x from the left, y up from the ground). */
  const box = (ctx, x, y, w, h, style) => {
    ctx.fillStyle = style;
    ctx.fillRect(x * kx, H - (y + h) * ky, w * kx, h * ky);
  };
  const gradient = (ctx, y, h, top, bottom) => {
    const g = ctx.createLinearGradient(0, H - (y + h) * ky, 0, H - y * ky);
    g.addColorStop(0, top);
    g.addColorStop(1, bottom);
    return g;
  };
  /** Runs draw() clipped to a rectangle in metres. */
  const clipped = (ctx, x, y, w, h, draw) => {
    ctx.save();
    ctx.beginPath();
    ctx.rect(x * kx, H - (y + h) * ky, w * kx, h * ky);
    ctx.clip();
    draw();
    ctx.restore();
  };

  /** Unlit glass: night sky in the top of the pane, a slanting streak of reflection. */
  function darkGlass(x, y, w, h) {
    box(O, x, y, w, h, gradient(O, y, h, css(0x1b2632), css(0x070a0e)));
    clipped(O, x, y, w, h, () => {
      O.fillStyle = 'rgba(160,190,220,0.07)';
      O.beginPath();
      O.moveTo((x + w * 0.1) * kx, H - y * ky);
      O.lineTo((x + w * 0.55) * kx, H - (y + h) * ky);
      O.lineTo((x + w * 0.8) * kx, H - (y + h) * ky);
      O.lineTo((x + w * 0.35) * kx, H - y * ky);
      O.fill();
    });
  }

  function drawWindow(win) {
    const { x, y, w, h } = win;
    const stone = st.stone;
    // Head: a stone lintel, a soldier course of brick, or a steel angle.
    if (st.lintel === 'stone') {
      box(O, x - 0.13, y + h, w + 0.26, 0.25, css(stone));
      box(O, x - 0.13, y + h + 0.21, w + 0.26, 0.04, css(shade(stone, 1.15)));
    } else if (st.lintel === 'brick') {
      box(O, x - 0.1, y + h, w + 0.2, 0.22, 'rgba(40,18,12,0.55)');
      for (let jx = x - 0.1; jx < x + w + 0.1; jx += 0.068) box(O, jx, y + h, 0.014, 0.22, 'rgba(20,16,14,0.5)');
    } else {
      box(O, x - 0.1, y + h, w + 0.2, 0.11, css(0x26282b));
      box(O, x - 0.1, y + h + 0.09, w + 0.2, 0.02, 'rgba(255,255,255,0.1)');
    }
    // Sill, with the shadow it throws on the brick below.
    box(O, x - 0.08, y - 0.18, w + 0.16, 0.08, 'rgba(0,0,0,0.38)');
    box(O, x - 0.11, y - 0.1, w + 0.22, 0.1, css(stone));
    box(O, x - 0.11, y - 0.02, w + 0.22, 0.02, css(shade(stone, 1.2)));

    // Sash frame: two panes, one above the other.
    box(O, x, y, w, h, css(st.frame));
    const f = 0.055;
    const rail = 0.05;
    const pw = w - f * 2;
    const ph = (h - f * 2 - rail) / 2;
    const panes = [[x + f, y + f, pw, ph], [x + f, y + f + ph + rail, pw, ph]];
    const lit = win.state !== 'dark';
    const tone = WARM[Math.floor(rand() * WARM.length)];
    const cloth = CURTAINS[Math.floor(rand() * CURTAINS.length)];

    for (let i = 0; i < 2; i++) {
      const [gx, gy, gw, gh] = panes[i];
      glassRects.push(panes[i]);
      if (win.state === 'warm') {
        // A lamp-lit room: brightest where the ceiling light is, behind the upper sash.
        box(O, gx, gy, gw, gh, css(mixHex(tone, 0x000000, 0.5)));
        box(E, gx, gy, gw, gh, i === 1 ? gradient(E, gy, gh, css(tone), css(shade(tone, 0.72))) : gradient(E, gy, gh, css(shade(tone, 0.72)), css(shade(tone, 0.5))));
      } else if (win.state === 'tv') {
        // A dark room with a television going: blue from below.
        box(O, gx, gy, gw, gh, css(0x121c2c));
        box(E, gx, gy, gw, gh, i === 0 ? gradient(E, gy, gh, css(0x35507a), css(0x86b4ff)) : gradient(E, gy, gh, css(0x141e30), css(0x35507a)));
      } else {
        darkGlass(gx, gy, gw, gh);
      }
    }

    // Curtains drawn back to the sides, or blinds let part way down. Both sit behind the glass.
    for (const [gx, gy, gw, gh] of panes) {
      if (win.curtain) {
        const cw = gw * 0.3;
        for (const cx of [gx, gx + gw - cw]) {
          box(O, cx, gy, cw, gh, css(lit ? shade(cloth, 0.55) : shade(cloth, 0.22)));
          if (lit) box(E, cx, gy, cw, gh, css(mixHex(shade(cloth, 0.75), tone, 0.35)));
          for (let k = 1; k < 4; k++) box(O, cx + (cw * k) / 4, gy, 0.012, gh, 'rgba(0,0,0,0.3)');
        }
      }
      if (win.blind > 0) {
        const top = y + h - f;
        const bottom = top - (h - f * 2) * win.blind;
        const from = Math.max(gy, bottom);
        const to = gy + gh;
        if (to > from) {
          clipped(O, gx, from, gw, to - from, () => {
            box(O, gx, from, gw, to - from, css(lit ? 0x9c927c : 0x4c4a44));
            for (let sy = top; sy > bottom; sy -= 0.05) box(O, gx, sy, gw, 0.014, 'rgba(0,0,0,0.5)');
          });
          if (lit) {
            clipped(E, gx, from, gw, to - from, () => {
              box(E, gx, from, gw, to - from, 'rgba(0,0,0,0.5)');
              for (let sy = top; sy > bottom; sy -= 0.05) box(E, gx, sy, gw, 0.02, 'rgba(0,0,0,0.6)');
            });
          }
        }
      }
    }
    // The opening is set back in the wall: shade under its head and down one jamb.
    box(O, x, y + h - 0.08, w, 0.08, 'rgba(0,0,0,0.42)');
    box(O, x, y, 0.035, h, 'rgba(0,0,0,0.28)');

    if (win.bars) {
      for (let bx = x + 0.1; bx < x + w - 0.05; bx += 0.13) box(O, bx, y, 0.022, h * 0.62, css(0x141516));
      box(O, x, y + h * 0.62, w, 0.03, css(0x141516));
    }
    if (win.ac) {
      // A window unit on the sill, its side panels filling the opening, rust weeping beneath.
      const aw = Math.min(0.62, w - 0.1);
      const ax = x + (w - aw) / 2;
      box(O, x + f, y + f, pw, 0.4, css(0xbdb8a8));
      box(O, ax, y - 0.02, aw, 0.42, css(0x8f9290));
      box(O, ax, y - 0.02, aw, 0.05, css(0x5c5f5e));
      for (let gy = y + 0.07; gy < y + 0.36; gy += 0.045) box(O, ax + 0.04, gy, aw - 0.08, 0.016, 'rgba(0,0,0,0.5)');
      box(O, ax + aw * 0.3, y - 0.5, 0.05, 0.4, gradient(O, y - 0.5, 0.4, 'rgba(96,58,34,0.45)', 'rgba(96,58,34,0)'));
      box(E, x + f, y + f - 0.02, pw, 0.44, '#000');
    }
  }

  function drawDoor(d, surround) {
    box(O, d.x - 0.09, d.y, d.w + 0.18, d.h + 0.42, css(surround));
    // Transom: the hall light is always on.
    const transom = [d.x, d.y + d.h + 0.05, d.w, 0.3];
    glassRects.push(transom);
    box(O, ...transom, css(0x6b5230));
    box(E, ...transom, css(0xb98a4a));
    box(O, d.x, d.y, d.w, d.h, css(DOOR));
    for (const [px, py, pw, ph] of [[0.1, 0.12, 0.8, 0.36], [0.1, 0.54, 0.8, 0.38]]) {
      box(O, d.x + d.w * px, d.y + d.h * py, d.w * pw, d.h * ph, 'rgba(0,0,0,0.35)');
      box(O, d.x + d.w * px, d.y + d.h * (py + ph) - 0.015, d.w * pw, 0.015, 'rgba(255,255,255,0.08)');
    }
    box(O, d.x + d.w * 0.84, d.y + d.h * 0.46, 0.035, 0.1, css(0xb89a4a));
    box(O, d.x, d.y + d.h - 0.06, d.w, 0.06, 'rgba(0,0,0,0.45)');
  }

  function drawShop() {
    const sh = layout.shop;
    const pier = shade(st.stone, 0.8);
    box(O, 0, 0, s.w, sh.base, css(0x25262a)); // bulkhead
    for (const u of layout.units) {
      if (u.kind === 'gate') {
        // Roll-down gate: slats, guide rails, a bottom bar, somebody's tag.
        box(O, u.x, 0.04, u.w, sh.top - 0.04, css(0x5d6165));
        for (let gy = 0.04; gy < sh.top; gy += 0.075) {
          box(O, u.x, gy, u.w, 0.02, 'rgba(0,0,0,0.42)');
          box(O, u.x, gy + 0.045, u.w, 0.012, 'rgba(255,255,255,0.07)');
        }
        box(O, u.x, 0.04, u.w, sh.top - 0.04, gradient(O, 0.04, sh.top - 0.04, 'rgba(0,0,0,0.05)', 'rgba(0,0,0,0.4)'));
        box(O, u.x, 0.04, u.w, 0.1, css(0x34373a));
        for (const rx of [u.x, u.x + u.w - 0.07]) box(O, rx, 0.04, 0.07, sh.top - 0.04, css(0x2c2e31));
        O.save();
        O.lineCap = 'round';
        O.lineJoin = 'round';
        const tags = 1 + Math.floor(rand() * 3);
        for (let t = 0; t < tags; t++) {
          O.strokeStyle = css(TAGS[Math.floor(rand() * TAGS.length)], 0.8);
          O.lineWidth = Math.max(1, 0.035 * kx);
          let px = (u.x + 0.2 + rand() * (u.w - 1)) * kx;
          let py = H - (0.7 + rand() * (sh.top - 1.4)) * ky;
          O.beginPath();
          O.moveTo(px, py);
          for (let k = 0; k < 9; k++) {
            px += (0.05 + rand() * 0.12) * kx;
            py += (rand() - 0.5) * 0.5 * ky;
            O.lineTo(px, py);
          }
          O.stroke();
        }
        O.restore();
      } else {
        // Shop window in an aluminium frame; behind it shelves, lit or not.
        const y0 = sh.base;
        const h = sh.top - sh.base;
        box(O, u.x, y0, u.w, h, css(0x2a2c30));
        const panes = u.w > 2.2 ? 2 : 1;
        const pw = (u.w - 0.07 * (panes + 1)) / panes;
        for (let i = 0; i < panes; i++) {
          const gx = u.x + 0.07 + i * (pw + 0.07);
          const pane = [gx, y0 + 0.07, pw, h - 0.14];
          glassRects.push(pane);
          if (u.kind === 'lit') {
            const light = rand() < 0.5 ? 0xe6ecff : 0xffe6b8;
            box(O, ...pane, css(shade(light, 0.42)));
            box(E, ...pane, gradient(E, pane[1], pane[3], css(light), css(shade(light, 0.6))));
            clipped(E, ...pane, () => {
              // Shelving and stock seen against the light.
              for (let sy = pane[1] + 0.35; sy < pane[1] + pane[3] - 0.3; sy += 0.42) {
                box(E, gx, sy, pw, 0.035, 'rgba(0,0,0,0.75)');
                box(O, gx, sy, pw, 0.035, 'rgba(0,0,0,0.6)');
                for (let px = gx + 0.05; px < gx + pw - 0.1; px += 0.1 + rand() * 0.12) {
                  const tint = css(TAGS[Math.floor(rand() * 5)], 0.75);
                  const ih = 0.1 + rand() * 0.2;
                  box(E, px, sy + 0.035, 0.08, ih, tint);
                  box(O, px, sy + 0.035, 0.08, ih, tint);
                }
              }
            });
          } else {
            darkGlass(...pane);
          }
        }
      }
    }
    // Piers between the units, the sign fascia and the cornice that caps the shop floor.
    for (let bay = 0; bay <= s.bays; bay++) box(O, bay * s.bayW - 0.16, 0, 0.32, sh.fascia[0], css(pier));
    box(O, 0, sh.fascia[0] - 0.06, s.w, 0.06, 'rgba(0,0,0,0.45)');
    box(O, 0, sh.fascia[0], s.w, sh.fascia[1] - sh.fascia[0], css(st.fascia));
    box(O, 0, sh.fascia[0], s.w, 0.03, 'rgba(255,255,255,0.08)');
    for (let bay = 0; bay <= s.bays; bay++) box(O, bay * s.bayW - 0.006, sh.fascia[0], 0.012, sh.fascia[1] - sh.fascia[0], 'rgba(0,0,0,0.4)');
    box(O, 0, sh.fascia[1], s.w, s.floorH - sh.fascia[1], css(st.stone));
    box(O, 0, s.floorH - 0.03, s.w, 0.03, css(shade(st.stone, 1.2)));
    box(O, 0, sh.fascia[1], s.w, 0.04, 'rgba(0,0,0,0.3)');
  }

  if (layout.shop) drawShop();
  for (const win of layout.windows) drawWindow(win);
  for (const d of layout.doors) drawDoor(d, layout.shop ? shade(st.stone, 0.8) : st.stone);

  if (st.cornice) {
    // Pressed-metal cornice with a row of dentils, throwing a shadow down the top of the wall.
    const c = 0.44;
    const y = s.h - c;
    const metal = mixHex(st.frame, 0x1c1a18, 0.7);
    box(O, 0, y - 0.14, s.w, 0.14, 'rgba(0,0,0,0.42)');
    box(O, 0, y, s.w, c, css(metal));
    box(O, 0, s.h - 0.07, s.w, 0.07, css(shade(metal, 1.7)));
    box(O, 0, y, s.w, 0.05, css(shade(metal, 0.6)));
    for (let x = 0.07; x < s.w; x += 0.3) {
      box(O, x, y + 0.1, 0.16, 0.16, css(shade(metal, 1.35)));
      box(O, x, y + 0.08, 0.16, 0.03, 'rgba(0,0,0,0.5)');
    }
  }

  // Mark the glass in the emissive layer's alpha.
  E.globalCompositeOperation = 'destination-out';
  E.globalAlpha = 0.75;
  E.fillStyle = '#000';
  for (const [gx, gy, gw, gh] of glassRects) E.fillRect(gx * kx, H - (gy + gh) * ky, gw * kx, gh * ky);

  const half = canvas2d(Math.max(4, Math.round(W / 2)), Math.max(4, Math.round(H / 2)));
  half.drawImage(E.canvas, 0, 0, half.canvas.width, half.canvas.height);
  return { overlay: O.canvas, emissive: half.canvas };
}
