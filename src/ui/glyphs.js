// Every pictogram of the interface, drawn here as small SVG shapes (no icon font, no borrowed artwork).
// All of them paint with `currentColor`, so CSS decides the colour.

import { svg } from './dom.js';

function icon(viewBox, className, children) {
  const node = svg('svg', { viewBox, class: `gl ${className}`, 'aria-hidden': 'true', focusable: 'false' });
  for (const child of children) node.append(child);
  return node;
}

const path = (d, extra) => svg('path', { d, fill: 'currentColor', ...extra });
const rect = (x, y, w, h, rx = 0, extra) => svg('rect', { x, y, width: w, height: h, rx, fill: 'currentColor', ...extra });

/** The CHOPPER: a compact carbine in profile, muzzle to the right. */
export function chopperGlyph() {
  return icon('0 0 104 36', 'gl-chopper', [
    path(
      // stock, receiver, top rail and rear sight
      'M3 13.2 22 11.4h2V21l-12 2.6L3 23ZM24 10h36v9H24ZM27 7.4h31V10H27ZM30 4.8h4.2v2.6H30Z' +
        // grip, trigger guard, magazine
        'M31 19h8l-2.6 11-7-1ZM39.5 19H46v2.2h-6.5ZM47 19h10l4.2 13-9.2 1.6Z' +
        // handguard, foregrip, barrel, muzzle, front sight
        'M60 10.6h24V18H60ZM68 18h5.4l-1 5.2h-3.4ZM84 13h13v2.6H84ZM95.6 11.8h5.6v5h-5.6ZM86 7.2h2.6V13H86Z',
    ),
    // lightening cuts in the handguard
    path('M63 13h4v2.2h-4ZM69.5 13h4v2.2h-4ZM76 13h4v2.2h-4Z', { fill: 'var(--gl-cut, #000)', opacity: '0.55' }),
  ]);
}

/** The NINE: a service pistol in profile, muzzle to the right. */
export function nineGlyph() {
  return icon('0 0 60 36', 'gl-nine', [
    path(
      // slide with sights, beavertail
      'M7 7.6h42.5l2.5 2.2V15H7ZM8 5.6h4.2v2H8ZM45.6 6h3v1.6h-3ZM4.4 11.6 7 12.6v4.6L4 15.2Z' +
        // frame and dust cover
        'M8 15h41v3.4H35.5c-2.6 0-3.4 1.4-3.4 3.4H22V18.4H8Z' +
        // grip, raked back, with its base plate
        'M10 18.4h12.4L18.6 31.4 5.6 30.4ZM5 30.8l13.6 1-.3 2.4L4.8 33.2Z',
    ),
    // trigger guard: a loop
    svg('path', { d: 'M22.6 19.2h10.6v3.6c0 1.6-1 2.6-2.6 2.6h-8', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.7' }),
    path('M13 21.2h6.4l-.5 1.8h-6.4ZM12.2 24.6h6.4l-.5 1.8h-6.4Z', { fill: 'var(--gl-cut, #000)', opacity: '0.5' }),
  ]);
}

/** Melee: a closed fist, knuckles up. */
export function fistGlyph() {
  return icon('0 0 36 36', 'gl-fist', [
    rect(7.2, 6.4, 5.6, 12, 2.8),
    rect(13.6, 5, 5.6, 13, 2.8),
    rect(20, 5.6, 5.6, 13, 2.8),
    rect(26.4, 7.4, 5, 11.4, 2.5),
    rect(7.2, 14.4, 24.2, 13.2, 4.4),
    rect(3.6, 16.2, 16.6, 6.6, 3.3, { transform: 'rotate(-11 12 19.5)', stroke: 'var(--gl-cut, #000)', 'stroke-width': '1.2' }),
    rect(11.4, 26.6, 16.4, 6, 1.4),
  ]);
}

/** Pause: two bars. */
export function pauseGlyph() {
  return icon('0 0 24 24', 'gl-pause', [rect(6.2, 5, 4, 14, 1), rect(13.8, 5, 4, 14, 1)]);
}

/** Settings: an eight-tooth gear. */
export function gearGlyph() {
  const teeth = 8;
  const outer = 9.6;
  const inner = 7.1;
  let d = '';
  for (let i = 0; i < teeth; i++) {
    const a = (i / teeth) * Math.PI * 2;
    const w = (Math.PI * 2) / teeth;
    const pts = [
      [inner, a - w * 0.5],
      [inner, a - w * 0.22],
      [outer, a - w * 0.14],
      [outer, a + w * 0.14],
      [inner, a + w * 0.22],
    ];
    for (const [r, t] of pts) {
      d += `${d ? 'L' : 'M'}${(12 + r * Math.cos(t)).toFixed(2)} ${(12 + r * Math.sin(t)).toFixed(2)}`;
    }
  }
  d += 'ZM12 8.4a3.6 3.6 0 1 0 0 7.2 3.6 3.6 0 0 0 0-7.2Z';
  return icon('0 0 24 24', 'gl-gear', [path(d, { 'fill-rule': 'evenodd' })]);
}

/** A chevron pointing right (buttons, the title's primary action). */
export function arrowGlyph() {
  return icon('0 0 24 24', 'gl-arrow', [
    svg('path', { d: 'M5 12h13M12.5 6l6 6-6 6', fill: 'none', stroke: 'currentColor', 'stroke-width': '2.4', 'stroke-linecap': 'square' }),
  ]);
}

/** Close: a cross. */
export function closeGlyph() {
  return icon('0 0 24 24', 'gl-close', [
    svg('path', { d: 'M6 6l12 12M18 6 6 18', fill: 'none', stroke: 'currentColor', 'stroke-width': '2.2', 'stroke-linecap': 'square' }),
  ]);
}

/** The certification disc on the debrief card: a record with grooves and a label. */
export function recordGlyph() {
  const ring = (r, opacity) => svg('circle', { cx: 32, cy: 32, r, fill: 'none', stroke: 'var(--gl-cut, #000)', 'stroke-width': '0.8', opacity });
  return icon('0 0 64 64', 'gl-record', [
    svg('circle', { cx: 32, cy: 32, r: 30, fill: 'currentColor' }),
    ring(26.5, '0.28'),
    ring(23, '0.28'),
    ring(19.5, '0.28'),
    ring(16, '0.28'),
    // the sheen: two opposite wedges
    path('M32 32 12 6.5A32 32 0 0 1 23 3.2ZM32 32l20 25.5a32 32 0 0 1-11 3.3Z', { fill: '#fff', opacity: '0.22' }),
    svg('circle', { cx: 32, cy: 32, r: 11, fill: 'var(--gl-cut, #000)' }),
    svg('circle', { cx: 32, cy: 32, r: 11, fill: 'none', stroke: 'currentColor', 'stroke-width': '1.2', opacity: '0.7' }),
    svg('circle', { cx: 32, cy: 32, r: 1.8, fill: 'currentColor' }),
  ]);
}

/** One damage-direction arc: a 48° segment near the rim with a chevron pointing outward. Rotated by the HUD. */
export function damageArc() {
  return svg(
    'svg',
    { viewBox: '0 0 200 200', class: 'hud-arc', 'aria-hidden': 'true', focusable: 'false' },
    svg('path', { d: 'M64.2 19.6A88 88 0 0 1 135.8 19.6', fill: 'none', stroke: 'currentColor', 'stroke-width': '4', 'stroke-linecap': 'butt' }),
    svg('path', { d: 'M94 8.6 100 3l6 5.6', fill: 'none', stroke: 'currentColor', 'stroke-width': '2.6', 'stroke-linejoin': 'miter' }),
  );
}

/** The interaction ring: a track and a progress stroke that starts at 12 o'clock and runs clockwise. */
export function promptRing() {
  const C = 2 * Math.PI * 19;
  const track = svg('circle', { cx: 24, cy: 24, r: 19, class: 'hud-ring-track', fill: 'none', 'stroke-width': '3' });
  const fill = svg('circle', {
    cx: 24,
    cy: 24,
    r: 19,
    class: 'hud-ring-fill',
    fill: 'none',
    'stroke-width': '3',
    'stroke-dasharray': C.toFixed(2),
    'stroke-dashoffset': C.toFixed(2),
    transform: 'rotate(-90 24 24)',
  });
  const node = svg('svg', { viewBox: '0 0 48 48', class: 'hud-ring', 'aria-hidden': 'true', focusable: 'false' }, track, fill);
  return { node, fill, circumference: C };
}
