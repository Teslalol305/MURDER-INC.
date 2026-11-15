// Geometry helpers: metre UVs, outward winding, robust merging. Run with `node --test test/`.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { bakeTransform, boxGeo, cylGeo, mergeGeos, mergeStatic, planeGeo, tubeGeo } from '../src/core/geo.js';

const near = (a, b, eps = 1e-5) => assert.ok(Math.abs(a - b) <= eps, `expected ${b}, got ${a}`);

function range(attr, component) {
  let min = Infinity;
  let max = -Infinity;
  for (let i = 0; i < attr.count; i++) {
    const v = attr.getComponent(i, component);
    min = Math.min(min, v);
    max = Math.max(max, v);
  }
  return [min, max];
}

/** Every triangle's geometric normal must point the same way as its vertex normals. */
function assertWinding(geo, label = '') {
  const pos = geo.getAttribute('position');
  const nor = geo.getAttribute('normal');
  const index = geo.index;
  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  const c = new THREE.Vector3();
  const n = new THREE.Vector3();
  const face = new THREE.Vector3();
  const count = index ? index.count : pos.count;
  assert.equal(count % 3, 0);
  for (let i = 0; i < count; i += 3) {
    const [ia, ib, ic] = [0, 1, 2].map((k) => (index ? index.getX(i + k) : i + k));
    a.fromBufferAttribute(pos, ia);
    b.fromBufferAttribute(pos, ib);
    c.fromBufferAttribute(pos, ic);
    face.subVectors(b, a).cross(c.sub(a));
    if (face.lengthSq() < 1e-12) continue; // degenerate
    n.fromBufferAttribute(nor, ia).add(b.fromBufferAttribute(nor, ib)).add(c.fromBufferAttribute(nor, ic));
    assert.ok(face.dot(n) > 0, `${label} triangle ${i / 3} is wound inside out`);
  }
}

test('boxGeo: size, metre UVs, outward faces', () => {
  const geo = boxGeo(4, 2, 1);
  assert.equal(geo.getAttribute('position').count, 24);
  assert.equal(geo.index.count, 36);
  assert.deepEqual(geo.boundingBox.min.toArray(), [-2, -1, -0.5]);
  assert.deepEqual(geo.boundingBox.max.toArray(), [2, 1, 0.5]);
  assertWinding(geo, 'box');

  // The south face (+z, the first quad) is 4 m wide and 2 m tall: its UVs span exactly that.
  const uv = geo.getAttribute('uv');
  assert.deepEqual([uv.getX(0), uv.getY(0)], [0, 0]);
  assert.deepEqual([uv.getX(2), uv.getY(2)], [4, 2]);
  // The east face (+x, third quad) is 1 m wide (the box depth).
  assert.deepEqual([uv.getX(10), uv.getY(10)], [1, 2]);
});

test('boxGeo: options', () => {
  const sitting = boxGeo(2, 3, 2, { bottom: true, at: [10, 0, -5] });
  assert.deepEqual(sitting.boundingBox.min.toArray(), [9, 0, -6]);
  assert.deepEqual(sitting.boundingBox.max.toArray(), [11, 3, -4]);

  const open = boxGeo(1, 1, 1, { noTop: true, noBottom: true });
  assert.equal(open.index.count, 24);

  const scaled = boxGeo(2, 2, 2, { uvScale: [0.5, 2], uvOffset: [1, 0] });
  assert.deepEqual(range(scaled.getAttribute('uv'), 0), [1, 2]);
  assert.deepEqual(range(scaled.getAttribute('uv'), 1), [0, 4]);

  const tinted = boxGeo(1, 1, 1, { color: 0xff0000 });
  const color = tinted.getAttribute('color');
  assert.equal(color.count, 24);
  assert.deepEqual([color.getX(5), color.getY(5), color.getZ(5)], [1, 0, 0]);
});

test('planeGeo: every facing points where it says', () => {
  const expected = { '+y': [0, 1, 0], '-y': [0, -1, 0], '+x': [1, 0, 0], '-x': [-1, 0, 0], '+z': [0, 0, 1], '-z': [0, 0, -1] };
  for (const [facing, normal] of Object.entries(expected)) {
    const geo = planeGeo(3, 2, { facing });
    const n = geo.getAttribute('normal');
    assert.deepEqual([n.getX(0), n.getY(0), n.getZ(0)], normal, facing);
    assertWinding(geo, `plane ${facing}`);
    assert.deepEqual(range(geo.getAttribute('uv'), 0), [0, 3]);
    assert.deepEqual(range(geo.getAttribute('uv'), 1), [0, 2]);
  }
  // Flat by default: 3 m along x, 2 m along z.
  const flat = planeGeo(3, 2);
  assert.deepEqual(flat.boundingBox.min.toArray(), [-1.5, 0, -1]);
  assert.throws(() => planeGeo(1, 1, { facing: 'up' }));
});

test('cylGeo and tubeGeo: UVs in metres', () => {
  const cyl = cylGeo(0.5, 3, 16, { open: true, bottom: true });
  assert.equal(cyl.groups.length, 0);
  near(range(cyl.getAttribute('uv'), 0)[1], Math.PI, 1e-4); // circumference of a 0.5 m radius
  near(range(cyl.getAttribute('uv'), 1)[1], 3);
  near(cyl.boundingBox.min.y, 0);
  near(cyl.boundingBox.max.y, 3);
  assertWinding(cyl, 'cylinder');

  const tube = tubeGeo([[0, 0, 0], [0, 0, -5], [0, 0, -10]], 0.1);
  near(range(tube.getAttribute('uv'), 0)[1], 10, 0.05); // length of the run
  near(range(tube.getAttribute('uv'), 1)[1], Math.PI * 0.2, 1e-4);
  assert.throws(() => tubeGeo([[0, 0, 0]], 0.1));
});

test('mergeGeos: mixed inputs come out as one normalised indexed geometry', () => {
  const indexed = boxGeo(1, 1, 1); // position, normal, uv, indexed
  const bare = new THREE.BufferGeometry(); // position only, non-indexed: one triangle
  bare.setAttribute('position', new THREE.BufferAttribute(new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0]), 3));
  const tinted = boxGeo(1, 1, 1, { color: 0x00ff00 });
  const empty = new THREE.BufferGeometry();

  const merged = mergeGeos([indexed, bare, null, empty, tinted]);
  assert.equal(merged.getAttribute('position').count, 24 + 3 + 24);
  assert.equal(merged.index.count, 36 + 3 + 36);
  for (const name of ['position', 'normal', 'uv', 'color']) assert.ok(merged.getAttribute(name), name);
  assert.deepEqual(Object.keys(merged.attributes).sort(), ['color', 'normal', 'position', 'uv']);
  assertWinding(merged, 'merged');

  // Parts without colours are white; the tinted box keeps its green.
  const color = merged.getAttribute('color');
  assert.deepEqual([color.getX(0), color.getY(0), color.getZ(0)], [1, 1, 1]);
  assert.deepEqual([color.getX(30), color.getY(30), color.getZ(30)], [0, 1, 0]);
  // The bare triangle got a computed normal (+z) and zero UVs.
  const normal = merged.getAttribute('normal');
  assert.deepEqual([normal.getX(24), normal.getY(24), normal.getZ(24)], [0, 0, 1]);
  assert.deepEqual([merged.getAttribute('uv').getX(25), merged.getAttribute('uv').getY(25)], [0, 0]);
  // Inputs are untouched.
  assert.equal(bare.getAttribute('normal'), undefined);

  assert.equal(mergeGeos([indexed]).getAttribute('color'), undefined);
});

test('mergeGeos: transforms, 32-bit indices, interleaved and normalised attributes', () => {
  const moved = mergeGeos([{ geo: boxGeo(1, 1, 1), matrix: new THREE.Matrix4().makeTranslation(5, 0, 0) }]);
  assert.deepEqual(moved.boundingBox.min.toArray(), [4.5, -0.5, -0.5]);

  const many = mergeGeos(Array.from({ length: 2800 }, () => boxGeo(1, 1, 1))); // 67 200 vertices
  assert.ok(many.index.array instanceof Uint32Array);
  assert.ok(mergeGeos([boxGeo(1, 1, 1)]).index.array instanceof Uint16Array);

  // Interleaved position + uv, and a normalised byte colour.
  const data = new THREE.InterleavedBuffer(new Float32Array([0, 0, 0, 0, 0, 2, 0, 0, 1, 0, 0, 2, 0, 0, 1]), 5);
  const odd = new THREE.BufferGeometry();
  odd.setAttribute('position', new THREE.InterleavedBufferAttribute(data, 3, 0));
  odd.setAttribute('uv', new THREE.InterleavedBufferAttribute(data, 2, 3));
  odd.setAttribute('color', new THREE.BufferAttribute(new Uint8Array([255, 0, 0, 255, 0, 255, 0, 255, 0, 0, 255, 255]), 4, true));
  const out = mergeGeos([odd]);
  assert.deepEqual(Array.from(out.getAttribute('position').array), [0, 0, 0, 2, 0, 0, 0, 2, 0]);
  assert.deepEqual(Array.from(out.getAttribute('uv').array), [0, 0, 1, 0, 0, 1]);
  assert.deepEqual(Array.from(out.getAttribute('color').array), [1, 0, 0, 0, 1, 0, 0, 0, 1]);
});

test('bakeTransform: world space copy, mirrored meshes stay right side out', () => {
  const source = boxGeo(2, 2, 2);
  const parent = new THREE.Group();
  parent.position.set(10, 0, 0);
  const mesh = new THREE.Mesh(source, new THREE.MeshBasicMaterial());
  mesh.position.set(0, 5, 0);
  mesh.scale.set(-1, 1, 2); // mirrored on x
  parent.add(mesh);

  const baked = bakeTransform(mesh);
  assert.notEqual(baked, source);
  assert.deepEqual(baked.boundingBox.min.toArray(), [9, 4, -2]);
  assert.deepEqual(baked.boundingBox.max.toArray(), [11, 6, 2]);
  assertWinding(baked, 'mirrored');
  assert.deepEqual(source.boundingBox.max.toArray(), [1, 1, 1]); // the shared source is untouched
});

test('mergeStatic: one mesh per material and shadow flags, dynamic parts carried over', () => {
  const brick = new THREE.MeshStandardMaterial({ name: 'brick' });
  const steel = new THREE.MeshStandardMaterial({ name: 'steel' });
  const root = new THREE.Group();
  root.position.set(100, 0, 0); // the root's own transform is baked too

  const row = new THREE.Group();
  row.position.set(0, 0, 10);
  row.rotation.y = Math.PI / 2;
  root.add(row);
  for (let i = 0; i < 5; i++) {
    const wall = new THREE.Mesh(boxGeo(1, 1, 1), brick);
    wall.position.x = i * 2;
    wall.castShadow = wall.receiveShadow = true;
    row.add(wall);
  }
  const beam = new THREE.Mesh(boxGeo(4, 0.2, 0.2), steel);
  beam.castShadow = true;
  root.add(beam);
  const decal = new THREE.Mesh(planeGeo(1, 1), brick); // same material, no shadow: its own bucket
  root.add(decal);

  // A mesh with two materials: its groups go to their materials' buckets.
  const two = new THREE.Mesh(boxGeo(1, 1, 1), [brick, steel]);
  two.castShadow = two.receiveShadow = true;
  two.geometry.addGroup(0, 18, 0);
  two.geometry.addGroup(18, 18, 1);
  two.position.z = 5; // inside the span of the wall row
  root.add(two);

  const dynamic = new THREE.Group();
  dynamic.userData.noMerge = true;
  dynamic.position.set(1, 2, 3);
  dynamic.add(new THREE.Mesh(boxGeo(1, 1, 1), steel));
  row.add(dynamic);
  const hidden = new THREE.Mesh(boxGeo(1, 1, 1), steel);
  hidden.visible = false;
  root.add(hidden);
  const light = new THREE.PointLight();
  root.add(light);
  const line = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial());
  root.add(line);

  const out = mergeStatic(root);
  const merged = out.children.filter((c) => c.name.startsWith('merged:'));
  // brick+shadows (5 walls + half of `two`), steel cast-only (beam), brick no-shadow (decal), steel+shadows (other half)
  assert.equal(merged.length, 4);
  assert.deepEqual(out.userData.mergeStats, { sourceMeshes: 8, mergedMeshes: 4, kept: 4, vertices: 24 * 5 + 24 + 4 + 24 * 2, triangles: 12 * 5 + 12 + 2 + 12 });

  const walls = merged.find((m) => m.material === brick && m.castShadow);
  assert.equal(walls.geometry.index.count, 36 * 5 + 18);
  assert.equal(walls.receiveShadow, true);
  assert.equal(walls.matrixAutoUpdate, false);
  assertWinding(walls.geometry, 'walls');
  // World transform baked: the row sits at x 100, z 10 and runs toward −z after its quarter turn.
  const box = walls.geometry.boundingBox;
  near(box.min.x, 99.5);
  near(box.max.x, 100.5);
  near(box.min.z, 10 - 8 - 0.5);
  near(box.max.z, 10.5);

  // Everything that must not be merged is carried over with its world transform intact.
  for (const kept of [dynamic, hidden, light, line]) assert.equal(kept.parent, out);
  out.updateMatrixWorld(true);
  const world = new THREE.Vector3().setFromMatrixPosition(dynamic.matrixWorld);
  near(world.x, 100 + 3);
  near(world.y, 2);
  near(world.z, 10 - 1);
  assert.equal(dynamic.children[0].geometry.getAttribute('position').count, 24); // untouched
});
