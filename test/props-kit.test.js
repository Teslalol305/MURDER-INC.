// The prop construction kit (src/props/kit.js) and the atlas layout: pure geometry and arithmetic.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { ATLAS_H, ATLAS_W, atlasRegionNames, layoutAtlas } from '../src/props/atlas.js';
import { Builder, Soup, arc, blobGeo, glow, insetPolygon, latheGeo, prism, prismGeo, roundBoxGeo, signedArea, triangleCount } from '../src/props/kit.js';

const near = (a, b, eps = 1e-5, label = '') => assert.ok(Math.abs(a - b) <= eps, `${label} expected ${b}, got ${a}`);

/** Triangles whose geometric normal disagrees with their vertex normals. */
function insideOut(geo) {
  const pos = geo.getAttribute('position');
  const nor = geo.getAttribute('normal');
  const idx = geo.index;
  const count = idx ? idx.count : pos.count;
  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  const c = new THREE.Vector3();
  const n = new THREE.Vector3();
  const f = new THREE.Vector3();
  let bad = 0;
  for (let i = 0; i < count; i += 3) {
    const [ia, ib, ic] = [0, 1, 2].map((k) => (idx ? idx.getX(i + k) : i + k));
    a.fromBufferAttribute(pos, ia);
    b.fromBufferAttribute(pos, ib);
    c.fromBufferAttribute(pos, ic);
    f.subVectors(b, a).cross(n.subVectors(c, a));
    if (f.lengthSq() < 1e-14) continue;
    n.fromBufferAttribute(nor, ia).add(b.fromBufferAttribute(nor, ib)).add(c.fromBufferAttribute(nor, ic));
    if (f.dot(n) <= 0) bad++;
  }
  return bad;
}

/** Every triangle of a closed convex shape must face away from the centre. */
function facesOutward(geo, centre = new THREE.Vector3()) {
  const pos = geo.getAttribute('position');
  const idx = geo.index;
  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  const c = new THREE.Vector3();
  const f = new THREE.Vector3();
  for (let i = 0; i < idx.count; i += 3) {
    a.fromBufferAttribute(pos, idx.getX(i));
    b.fromBufferAttribute(pos, idx.getX(i + 1));
    c.fromBufferAttribute(pos, idx.getX(i + 2));
    f.subVectors(b, a).cross(c.clone().sub(a));
    if (f.lengthSq() < 1e-14) continue;
    const mid = a.add(b).add(c).divideScalar(3).sub(centre);
    if (f.dot(mid) <= 0) return false;
  }
  return true;
}

test('kit: Soup shades flat or creased, and welds what it smooths', () => {
  // Two quads meeting at a 20° fold, mapped as one continuous strip.
  const fold = () => {
    const s = new Soup();
    const k = Math.tan((20 * Math.PI) / 180);
    s.quad([0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1, 1]);
    s.quad([1, 0, 0], [2, 0, -k], [2, 1, -k], [1, 1, 0], [1, 0, 2, 1]);
    return s;
  };
  const flat = fold().build(0);
  assert.equal(flat.getAttribute('position').count, 8, 'flat faces keep their own vertices');
  assert.equal(triangleCount(flat), 4);
  near(flat.getAttribute('normal').getZ(0), 1);

  const smooth = fold().build(30);
  assert.equal(smooth.getAttribute('position').count, 6, 'the fold line is shared once the crease allows it');
  const crisp = fold().build(10);
  assert.equal(crisp.getAttribute('position').count, 8, 'a sharper fold than the crease angle stays split');
  assert.equal(insideOut(smooth), 0);
});

test('kit: quadFacing turns a quad toward the hint whatever the corner order', () => {
  const corners = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]];
  for (const hint of [[0, 0, 1], [0, 0, -1]]) {
    for (const order of [corners, corners.slice().reverse()]) {
      const geo = new Soup().quadFacing(hint, ...order).build(0);
      near(geo.getAttribute('normal').getZ(0), hint[2]);
    }
  }
});

test('kit: prism extrudes any outline along any axis with outward faces', () => {
  const square = [[-1, -1], [1, -1], [1, 1], [-1, 1]];
  for (const axis of ['x', 'y', 'z']) {
    for (const outline of [square, square.slice().reverse()]) {
      const geo = prismGeo(outline, -2, 2, { axis });
      assert.equal(triangleCount(geo), 12, `${axis}: a box is twelve triangles`);
      assert.ok(facesOutward(geo), `${axis}: every face looks outward`);
      geo.computeBoundingBox();
      const size = geo.boundingBox.getSize(new THREE.Vector3());
      near(size[axis], 4, 1e-6, axis);
    }
  }
  const bevelled = prismGeo(square, -2, 2, { bevel: 0.2 });
  assert.equal(triangleCount(bevelled), 4 * 6 + 4);
  assert.ok(facesOutward(bevelled));
  bevelled.computeBoundingBox();
  near(bevelled.boundingBox.max.z, 2);
  near(bevelled.boundingBox.max.x, 1);
});

test('kit: prism routes tagged walls to their own soup and cuts the caps along chords', () => {
  // An L-shaped outline (concave), the wall from the tagged point is the floor.
  const outline = [[0, 0, 'floor'], [2, 0], [2, 1], [1, 1], [1, 2], [0, 2]];
  const floor = new Soup();
  const body = prism(outline, 0, 1, { soups: { floor } });
  assert.equal(floor.idx.length / 3, 2, 'one wall went to the tagged soup');
  assert.equal(triangleCount(body.build(0)), 5 * 2 + 4 * 2);
  assert.equal(insideOut(body.build(40)), 0);

  // Given clockwise, a tag still marks the wall that starts at its point in the order given:
  // here the one from [0, 0] to [0, 2].
  const wall = new Soup();
  prism(outline.slice().reverse(), 0, 1, { soups: { floor: wall } });
  assert.equal(wall.idx.length / 3, 2);
  const xs = [];
  for (let i = 0; i < wall.pos.length; i += 3) xs.push(wall.pos[i]);
  assert.ok(xs.every((x) => x === 0), 'the tagged wall of a clockwise outline');

  // A chord between two outline points splits the caps into pieces that are triangulated apart.
  const whole = prism(outline, 0, 1).build(0);
  const cut = prism(outline, 0, 1, { chords: [[3, 0]] }).build(0);
  assert.equal(triangleCount(cut), triangleCount(whole), 'cutting a cap does not change its triangle count');
});

test('kit: latheGeo turns a profile with outward, smooth normals', () => {
  const drum = latheGeo([[0, 0], [0.5, 0], [0.5, 1], [0, 1]], 12);
  assert.equal(triangleCount(drum), 12 + 24 + 12);
  assert.equal(insideOut(drum), 0);
  assert.ok(facesOutward(drum, new THREE.Vector3(0, 0.5, 0)));
  drum.computeBoundingBox();
  near(drum.boundingBox.max.y, 1);
  near(drum.boundingBox.max.x, 0.5);
  // A shallow bend along the profile is smoothed, a right angle is not: the side wall's normals stay level.
  const nor = drum.getAttribute('normal');
  const pos = drum.getAttribute('position');
  for (let i = 0; i < pos.count; i++) {
    if (Math.abs(pos.getY(i) - 0.5) < 0.6 && Math.hypot(pos.getX(i), pos.getZ(i)) > 0.49 && Math.abs(nor.getY(i)) < 0.5) near(nor.getY(i), 0);
  }
  const half = latheGeo([[0.5, 0], [0.5, 1]], 8, { arc: Math.PI });
  half.computeBoundingBox();
  assert.ok(half.boundingBox.min.z > -1e-6, 'an arc of π covers the +z half only');
});

test('kit: blobs and pillows are closed, outward and the size they were asked for', () => {
  const blob = blobGeo(0.5, { seed: 3, rough: 0.2, crease: 60 });
  assert.equal(triangleCount(blob), 80);
  assert.equal(insideOut(blob), 0);
  blob.computeBoundingSphere();
  assert.ok(blob.boundingSphere.radius > 0.4 && blob.boundingSphere.radius < 0.65);
  const bag = roundBoxGeo(0.5, 0.3, 0.6);
  bag.computeBoundingBox();
  near(bag.boundingBox.max.x, 0.25, 3e-3);
  near(bag.boundingBox.max.y, 0.15, 3e-3);
  near(bag.boundingBox.max.z, 0.3, 3e-3);
  assert.ok(bag.boundingBox.max.y <= 0.15 + 1e-9, 'rounding only ever pulls a pillow in');
  assert.equal(insideOut(bag), 0);
});

test('kit: outlines: area sign, inset, arcs', () => {
  const square = [[0, 0], [2, 0], [2, 2], [0, 2]];
  assert.equal(signedArea(square), 4);
  assert.equal(signedArea(square.slice().reverse()), -4);
  const inner = insetPolygon(square, 0.25);
  assert.deepEqual(inner, [[0.25, 0.25], [1.75, 0.25], [1.75, 1.75], [0.25, 1.75]]);
  const quarter = arc(0, 0, 1, 0, Math.PI / 2, 4, 'u');
  assert.equal(quarter.length, 5);
  near(quarter[4][1], 1);
  assert.equal(quarter[2][2], 'u');
});

test('kit: Builder merges per slot, bakes glows into one slot, moves nodes to their pivot', () => {
  const b = new Builder({ name: 't', size: [1, 1, 1], rng: null, atlas: () => [0, 0, 1, 1] });
  b.box('metal_dark', [1, 1, 1], [0, 0.5, 0]);
  b.box('metal_dark', [0.2, 0.2, 0.2], [0, 1.1, 0]);
  b.box(glow(0xff0000, 2), [0.1, 0.1, 0.1], [0.5, 0.5, 0]);
  b.box(glow(0x00ff00, 3), [0.1, 0.1, 0.1], [-0.5, 0.5, 0]);
  b.decal('any', [0, 0.5, 0.5], 0.4, 0.2, '+z');
  b.node('door', [1, 0, 0]);
  b.box('metal_dark', [0.1, 1, 1], [1, 0.5, 0]);
  b.root();
  b.push(new THREE.Matrix4().makeTranslation(0, 5, 0));
  b.box('wood', [1, 1, 1], [0, 0, 0]);
  b.pop();
  b.collide([-0.5, 0, -0.5], [0.5, 1, 0.5], { surface: 'metal' });
  b.lamp([0, 1, 0], { color: 0xffffff, intensity: 1, range: 2, kind: 'work' });
  b.anchor('steam', [0, 1, 0]);
  const proto = b.finish();

  const [root, door] = proto.nodes;
  assert.deepEqual([...root.parts.keys()].sort(), ['@decal', '@glow', 'metal_dark', 'wood']);
  assert.equal(triangleCount(root.parts.get('metal_dark')), 24);
  const glowGeo = root.parts.get('@glow');
  assert.equal(triangleCount(glowGeo), 24);
  const col = glowGeo.getAttribute('color');
  near(col.getX(0), 2, 1e-5, 'red glow keeps its HDR value');
  near(col.getY(col.count - 1), 3, 1e-5, 'green glow keeps its HDR value');
  root.parts.get('wood').computeBoundingBox();
  near(root.parts.get('wood').boundingBox.min.y, 4.5, 1e-6, 'push() moved the box');
  assert.equal(door.name, 'door');
  door.parts.get('metal_dark').computeBoundingBox();
  near(door.parts.get('metal_dark').boundingBox.max.x, 0.05, 1e-6, 'node geometry is relative to its pivot');
  // A decal facing +z is a quad lifted off the surface with the atlas rectangle as UVs.
  const decal = root.parts.get('@decal');
  near(decal.getAttribute('position').getZ(0), 0.506, 1e-6);
  near(decal.getAttribute('normal').getZ(0), 1);
  assert.deepEqual([decal.getAttribute('uv').getX(2), decal.getAttribute('uv').getY(2)], [1, 1]);
  assert.equal(proto.colliders.length, 1);
  assert.equal(proto.lights[0].kind, 'work');
  assert.deepEqual(proto.anchors.steam, { pos: [0, 1, 0], dir: [0, 1, 0] });
  assert.equal(proto.triangles, 24 + 24 + 2 + 12 + 12);
});

test('atlas: every region fits the sheet and none overlap', () => {
  const rects = layoutAtlas();
  const names = atlasRegionNames();
  assert.equal(rects.size, names.length);
  assert.equal(new Set(names).size, names.length, 'region names are unique');
  const list = [...rects.values()];
  for (const r of list) {
    assert.ok(r.x >= 0 && r.y >= 0 && r.x + r.w <= ATLAS_W && r.y + r.h <= ATLAS_H);
    const [u0, v0, u1, v1] = r.uv;
    assert.ok(u0 >= 0 && v0 >= 0 && u1 <= 1 && v1 <= 1 && u0 < u1 && v0 < v1);
  }
  for (let i = 0; i < list.length; i++) {
    for (let j = i + 1; j < list.length; j++) {
      const a = list[i];
      const b = list[j];
      const apart = a.x + a.w <= b.x || b.x + b.w <= a.x || a.y + a.h <= b.y || b.y + b.h <= a.y;
      assert.ok(apart, `${names[i]} and ${names[j]} overlap`);
    }
  }
});
