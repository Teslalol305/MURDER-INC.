// Narrow and portrait views: the zoom both cameras get (render.js narrowZoom). Run with `node --test test/`.

import test from 'node:test';
import assert from 'node:assert/strict';
import { narrowZoom } from '../src/render.js';

const deg = (r) => (r * 180) / Math.PI;
/** Effective vertical and horizontal field of view (degrees) for a camera fov, aspect and zoom. */
function view(fov, aspect, zoom) {
  const t = Math.tan((fov * Math.PI) / 360) / zoom;
  return { v: 2 * deg(Math.atan(t)), h: 2 * deg(Math.atan(t * aspect)) };
}

test('zoom: landscape views from 4:3 to ultra-wide are untouched', () => {
  for (const aspect of [4 / 3, 16 / 10, 16 / 9, 21 / 9, 844 / 390]) {
    for (const fov of [60, 74, 90]) assert.equal(narrowZoom(aspect, fov), 1);
  }
});

test('zoom: portrait phones and a 400 px pane keep a usable horizontal view, never a fisheye', () => {
  for (const [w, h] of [[390, 844], [400, 760], [768, 1024], [600, 600]]) {
    for (const fov of [60, 74, 90]) {
      const aspect = w / h;
      const zoom = narrowZoom(aspect, fov);
      assert.ok(zoom > 0 && zoom <= 1);
      const unzoomed = view(fov, aspect, 1);
      const zoomed = view(fov, aspect, zoom);
      assert.ok(zoomed.v <= 105 + 1e-6, `${w}x${h} fov ${fov}: vertical ${zoomed.v.toFixed(1)}`);
      assert.ok(zoomed.h >= unzoomed.h - 1e-9);
      if (fov <= 74) assert.ok(zoomed.h >= 62, `${w}x${h} fov ${fov}: horizontal ${zoomed.h.toFixed(1)}`);
    }
  }
  // 400 x 760 at the default 74: about 43 degrees across before, about 70 now.
  const z = narrowZoom(400 / 760, 74);
  assert.ok(Math.abs(view(74, 400 / 760, z).h - 69.3) < 1.5, view(74, 400 / 760, z).h);
});

test('zoom: a square pane reaches the horizontal view of 4:3 exactly', () => {
  const z = narrowZoom(1, 74);
  assert.ok(Math.abs(view(74, 1, z).h - view(74, 4 / 3, 1).h) < 1e-6);
});
