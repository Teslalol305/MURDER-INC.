// Fences and hoardings shared by the yards and the street closures.

import { wallFrame } from './buildings.js';

/** See-through mesh, drawn once from both sides. */
const meshMaterial = (kit) => kit.mats.get('chainlink', { transparent: true, opacity: 0.4, doubleSide: true });

/**
 * A straight run of chain-link along x (z fixed) or along z (x fixed) from height y0 to y1: posts,
 * rails, mesh. No colliders: the caller decides what the run stops.
 * o: spacing (posts), postFrom (where the posts start, default y0).
 */
export function chainlink(kit, x0, z0, x1, z1, y0, y1, o = {}) {
  const alongX = z0 === z1;
  const length = alongX ? x1 - x0 : z1 - z0;
  kit.quad(meshMaterial(kit), alongX ? '+z' : '+x', (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2, length, y1 - y0, { cast: false, receive: false });
  for (const y of [y0 + 0.04, y1 - 0.03, ...(y1 - y0 > 3 ? [(y0 + y1) / 2] : [])]) {
    kit.pipe('metal_galv', [x0, y, z0], [x1, y, z1], 0.022, 5);
  }
  const posts = Math.max(1, Math.round(length / (o.spacing || 3)));
  for (let i = 0; i <= posts; i++) {
    const x = x0 + ((x1 - x0) * i) / posts;
    const z = z0 + ((z1 - z0) * i) / posts;
    const end = i === 0 || i === posts;
    kit.cyl('metal_galv', x, o.postFrom ?? y0, y1 + (end ? 0.12 : 0.04), z, end ? 0.05 : 0.035, 6);
  }
}

/**
 * A plywood hoarding: painted boards on posts, solid to rounds and walkers. It runs from a0 to a1
 * along x when `facing` is ±z (standing at z = at) and along z when it is ±x (standing at x = at).
 * Returns the wall frame of its painted side, for posters and signs.
 */
export function hoarding(kit, a0, a1, at, y0, y1, color, facing) {
  const board = ['plywood', { color }];
  const alongX = facing[1] === 'z';
  const sign = facing[0] === '+' ? 1 : -1;
  const F = wallFrame(kit, facing, at);
  if (alongX) kit.solid(a0, a1, y0, y1, at - 0.04, at + 0.04, { surface: 'wood', tag: 'hoarding' });
  else kit.solid(at - 0.04, at + 0.04, y0, y1, a0, a1, { surface: 'wood', tag: 'hoarding' });
  F.box(board, a0, a1, y0, y1, -0.04, 0.04);
  F.box('wood', a0, a1, y1, y1 + 0.06, -0.07, 0.07);
  for (let u = a0 + 0.1; u <= a1 - 0.05; u += 2.44) F.box('wood', u - 0.045, u + 0.045, y0, y1, -0.13, -0.04, { cast: false });
  return wallFrame(kit, facing, at + sign * 0.04);
}
