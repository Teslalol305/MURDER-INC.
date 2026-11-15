// Rule's arms: bare brown forearms, black gloves (stitched panels, a padded knuckle, jointed fingers),
// a gold watch on the left wrist and a gold curb chain on the right. Both arms are one mesh, skinned on the CPU from a small bone list, so they cost a single
// draw call and can bend smoothly at every knuckle.
//
// Hand space (bind pose, right hand): origin at the wrist, fingers along −Z, back of the hand +Y,
// thumb on −X. The forearm runs back along +Z. The left arm is the mirror image.
//
// Per arm the caller sets, in rig (camera) space:
//   arm.pos / arm.quat   the hand (wrist) frame
//   arm.elbow            where the elbow is; the forearm aims at it and rolls with the hand
//   arm.pose             21 joint angles (see POSE below), usually blended from the named poses
// and calls arms.update() once per frame.

import * as THREE from 'three';
import { FINISH, block, loft, rod } from './build.js';

const FINGERS = ['index', 'middle', 'ring', 'pinky'];

/** Right-hand proportions, metres. */
const HAND = {
  knuckle: { index: [-0.0295, 0.002, -0.098], middle: [-0.0085, 0.004, -0.103], ring: [0.0125, 0.002, -0.098], pinky: [0.031, -0.002, -0.088] },
  splay: { index: 0.07, middle: 0.0, ring: -0.06, pinky: -0.15 }, // rest yaw, + toward the thumb
  length: { index: [0.044, 0.026, 0.022], middle: [0.049, 0.03, 0.023], ring: [0.045, 0.028, 0.022], pinky: [0.035, 0.02, 0.019] },
  radius: { index: 0.0093, middle: 0.0097, ring: 0.0091, pinky: 0.008 },
  thumb: {
    base: [-0.027, -0.011, -0.027],
    aim: [-0.6, -0.3, -0.74], // the way the thumb points at rest
    up: [-0.55, 0.8, 0.2], // the way its nail faces
    length: [0.044, 0.034, 0.028],
    radius: 0.0118,
  },
  /** Middle of the palm's inner surface: what "put the palm here" refers to. */
  palm: [0.002, -0.014, -0.062],
};

const BONE = { forearm: 0, hand: 1, finger: 2, thumb: 14, count: 17 };
const FOREARM_LENGTH = 0.31;

/**
 * Pose layout: four fingers × [curl at the knuckle, curl at the middle joint, curl at the tip joint,
 * spread], then the thumb [swing toward the palm, swing down, twist, curl, tip curl]. Radians.
 */
export const POSE = { size: 21, thumb: 16 };

/** Builds a pose from {index, middle, ring, pinky: [c0, c1, c2, spread], thumb: [a, b, c, c1, c2]}. */
export function makePose(spec) {
  const pose = new Float32Array(POSE.size);
  FINGERS.forEach((name, f) => {
    const v = spec[name] || spec.fingers || [0, 0, 0, 0];
    for (let k = 0; k < 4; k++) pose[f * 4 + k] = v[k] || 0;
  });
  const t = spec.thumb || [0, 0, 0, 0, 0];
  for (let k = 0; k < 5; k++) pose[POSE.thumb + k] = t[k] || 0;
  return pose;
}

export function blendPose(out, a, b, t) {
  for (let i = 0; i < POSE.size; i++) out[i] = a[i] + (b[i] - a[i]) * t;
  return out;
}

// ------------------------------------------------------------------------------------------------
// Authoring: a skinned triangle soup in hand space
// ------------------------------------------------------------------------------------------------

const HASH = 1e5;
const _color = new THREE.Color();
const linear = (hex) => {
  _color.set(hex);
  return [_color.r, _color.g, _color.b];
};
const mix = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
const scale = (a, k) => [a[0] * k, a[1] * k, a[2] * k];

/**
 * Collects triangles with per-vertex colour, surface values and a two-bone binding.
 * Geometries carry the attributes `col` (3), `srf` (4: roughness, metalness, glow, finish) and
 * `skin` (3: bone A, bone B, weight of B); a missing attribute falls back to the values given to add().
 */
class SkinSoup {
  constructor() {
    this.pos = [];
    this.nor = [];
    this.col = [];
    this.srf = [];
    this.skin = [];
  }

  add(geo, { m = null, crease = 1.2, col = null, srf = null, skin = null } = {}) {
    if (m) geo.applyMatrix4(m);
    const flat = geo.index ? geo.toNonIndexed() : geo;
    const pos = flat.getAttribute('position').array;
    const count = pos.length / 3;
    const aCol = flat.getAttribute('col');
    const aSrf = flat.getAttribute('srf');
    const aSkin = flat.getAttribute('skin');
    const nor = smoothNormals(pos, crease);
    for (let i = 0; i < count; i++) {
      this.pos.push(pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]);
      this.nor.push(nor[i * 3], nor[i * 3 + 1], nor[i * 3 + 2]);
      if (aCol) this.col.push(aCol.getX(i), aCol.getY(i), aCol.getZ(i));
      else this.col.push(col[0], col[1], col[2]);
      if (aSrf) this.srf.push(aSrf.getX(i), aSrf.getY(i), aSrf.getZ(i), aSrf.getW(i));
      else this.srf.push(srf[0], srf[1], srf[2], srf[3]);
      if (aSkin) this.skin.push(aSkin.getX(i), aSkin.getY(i), aSkin.getZ(i));
      else this.skin.push(skin[0], skin[1], skin[2]);
    }
    geo.dispose();
    if (flat !== geo) flat.dispose();
  }

  /** Mirror image across the YZ plane (right arm → left arm). */
  mirror() {
    for (let i = 0; i < this.pos.length; i += 3) {
      this.pos[i] = -this.pos[i];
      this.nor[i] = -this.nor[i];
    }
    // Swap two corners of every triangle so the faces still point outward.
    const swap = (arr, size, a, b) => {
      for (let k = 0; k < size; k++) {
        const t = arr[a * size + k];
        arr[a * size + k] = arr[b * size + k];
        arr[b * size + k] = t;
      }
    };
    for (let v = 0; v < this.pos.length / 3; v += 3) {
      swap(this.pos, 3, v + 1, v + 2);
      swap(this.nor, 3, v + 1, v + 2);
      swap(this.col, 3, v + 1, v + 2);
      swap(this.srf, 4, v + 1, v + 2);
      swap(this.skin, 3, v + 1, v + 2);
    }
  }
}

/** Per-corner normals averaged over faces within `crease` radians (see build.js for the idea). */
function smoothNormals(pos, crease) {
  const faces = pos.length / 9;
  const faceN = new Float32Array(faces * 3);
  const map = new Map();
  const key = (p) => `${Math.round(pos[p] * HASH)},${Math.round(pos[p + 1] * HASH)},${Math.round(pos[p + 2] * HASH)}`;
  for (let f = 0; f < faces; f++) {
    const o = f * 9;
    const ux = pos[o + 3] - pos[o];
    const uy = pos[o + 4] - pos[o + 1];
    const uz = pos[o + 5] - pos[o + 2];
    const vx = pos[o + 6] - pos[o];
    const vy = pos[o + 7] - pos[o + 1];
    const vz = pos[o + 8] - pos[o + 2];
    faceN[f * 3] = uy * vz - uz * vy;
    faceN[f * 3 + 1] = uz * vx - ux * vz;
    faceN[f * 3 + 2] = ux * vy - uy * vx;
    for (let k = 0; k < 3; k++) {
      const id = key(o + k * 3);
      let list = map.get(id);
      if (!list) map.set(id, (list = []));
      list.push(f);
    }
  }
  const out = new Float32Array(pos.length);
  const cosCrease = Math.cos(crease);
  for (let f = 0; f < faces; f++) {
    const fx = faceN[f * 3];
    const fy = faceN[f * 3 + 1];
    const fz = faceN[f * 3 + 2];
    const fl = Math.hypot(fx, fy, fz) || 1;
    for (let k = 0; k < 3; k++) {
      const p = f * 9 + k * 3;
      const list = map.get(key(p));
      let nx = 0;
      let ny = 0;
      let nz = 0;
      for (let i = 0; i < list.length; i++) {
        const g = list[i] * 3;
        const gl = Math.hypot(faceN[g], faceN[g + 1], faceN[g + 2]) || 1;
        if ((fx * faceN[g] + fy * faceN[g + 1] + fz * faceN[g + 2]) / (fl * gl) >= cosCrease) {
          nx += faceN[g];
          ny += faceN[g + 1];
          nz += faceN[g + 2];
        }
      }
      const len = Math.hypot(nx, ny, nz) || 1;
      out[p] = nx / len;
      out[p + 1] = ny / len;
      out[p + 2] = nz / len;
    }
  }
  return out;
}

/**
 * A loft whose rings also say how they are painted and bound.
 * ring: {…loft ring, bind: [boneA, boneB, weightB], paint(i, n) → [r, g, b, rough]}
 */
function skinLoft(rings, n, caps, finish = FINISH.skin) {
  const geo = loft(rings, n, caps);
  const count = geo.getAttribute('position').count;
  const col = new Float32Array(count * 3);
  const srf = new Float32Array(count * 4);
  const skin = new Float32Array(count * 3);
  const put = (v, ring, i) => {
    const c = ring.paint(i, n);
    col.set([c[0], c[1], c[2]], v * 3);
    srf.set([c[3], 0, 0, finish], v * 4);
    skin.set(ring.bind, v * 3);
  };
  rings.forEach((ring, j) => {
    for (let i = 0; i < n; i++) put(j * n + i, ring, i);
  });
  // Cap centres follow the ring vertices: start cap first, then end cap. −1 = "average of the ring".
  let v = rings.length * n;
  if (caps[0]) put(v++, rings[0], -1);
  if (caps[1]) put(v++, rings[rings.length - 1], -1);
  geo.setAttribute('col', new THREE.BufferAttribute(col, 3));
  geo.setAttribute('srf', new THREE.BufferAttribute(srf, 4));
  geo.setAttribute('skin', new THREE.BufferAttribute(skin, 3));
  return geo;
}

/** Bones of a right arm in bind pose: [{parent, pos, quat}]. */
function authorBones() {
  const bones = [];
  const I = () => new THREE.Quaternion();
  bones[BONE.forearm] = { parent: -1, pos: [0, 0, 0], quat: I() };
  bones[BONE.hand] = { parent: -1, pos: [0, 0, 0], quat: I() };
  FINGERS.forEach((name, f) => {
    const b = BONE.finger + f * 3;
    const [l0, l1] = HAND.length[name];
    bones[b] = { parent: BONE.hand, pos: HAND.knuckle[name], quat: I().setFromAxisAngle(new THREE.Vector3(0, 1, 0), HAND.splay[name]) };
    bones[b + 1] = { parent: b, pos: [0, 0, -l0], quat: I() };
    bones[b + 2] = { parent: b + 1, pos: [0, 0, -l1], quat: I() };
  });
  // The thumb's frame comes from where it points and where its nail faces.
  const t = HAND.thumb;
  const z = new THREE.Vector3().fromArray(t.aim).normalize().negate();
  const y = new THREE.Vector3().fromArray(t.up);
  y.addScaledVector(z, -y.dot(z)).normalize();
  const x = new THREE.Vector3().crossVectors(y, z);
  const rest = I().setFromRotationMatrix(new THREE.Matrix4().makeBasis(x, y, z));
  bones[BONE.thumb] = { parent: BONE.hand, pos: t.base, quat: rest };
  bones[BONE.thumb + 1] = { parent: BONE.thumb, pos: [0, 0, -t.length[0]], quat: I() };
  bones[BONE.thumb + 2] = { parent: BONE.thumb + 1, pos: [0, 0, -t.length[1]], quat: I() };
  return bones;
}

/** World (hand-space) matrices of the bind pose. */
function bindMatrices(bones) {
  const out = [];
  const one = new THREE.Vector3(1, 1, 1);
  bones.forEach((bone, i) => {
    const local = new THREE.Matrix4().compose(new THREE.Vector3().fromArray(bone.pos), bone.quat, one);
    out[i] = bone.parent < 0 ? local : new THREE.Matrix4().multiplyMatrices(out[bone.parent], local);
  });
  return out;
}

/** Forearm and hand cross-sections: [z, width, top, bottom, exponent, x shift, weight of the hand bone]. */
const SECTIONS = [
  [FOREARM_LENGTH + 0.06, 0.1, 0.046, 0.046, 2, 0, 0],
  [0.24, 0.099, 0.044, 0.045, 2, 0, 0],
  [0.16, 0.09, 0.037, 0.04, 2, 0, 0],
  [0.09, 0.072, 0.028, 0.03, 2.1, 0, 0],
  [0.045, 0.061, 0.0225, 0.0235, 2.2, 0, 0],
  [0.02, 0.058, 0.0205, 0.021, 2.3, 0, 0.2],
  [0.004, 0.058, 0.0195, 0.02, 2.4, 0, 0.5],
  [-0.012, 0.062, 0.0185, 0.02, 2.5, -0.001, 0.85],
  [-0.032, 0.074, 0.0165, 0.0205, 2.6, -0.002, 1],
  [-0.06, 0.084, 0.0145, 0.018, 2.7, 0, 1],
  [-0.086, 0.088, 0.013, 0.0145, 2.8, 0.001, 1],
  [-0.1, 0.086, 0.0115, 0.0115, 2.8, 0.001, 1],
  [-0.106, 0.078, 0.008, 0.008, 2.6, 0.001, 1],
];
/** The glove reaches this far up the wrist; the cuff covers the edge. */
const GLOVE_TO = 0.03;

/** The arm's cross-section at z, interpolated: {w, top, bot, exp, x, hand}. */
function sectionAt(z) {
  let i = 0;
  while (i < SECTIONS.length - 2 && SECTIONS[i + 1][0] > z) i++;
  const a = SECTIONS[i];
  const b = SECTIONS[i + 1];
  const t = Math.max(0, Math.min(1, (a[0] - z) / (a[0] - b[0])));
  const at = (k) => a[k] + (b[k] - a[k]) * t;
  return { w: at(1), top: at(2), bot: at(3), exp: at(4), x: at(5), hand: at(6) };
}

/** The whole right arm as a skinned soup in hand space: bare forearm, gloved hand, jewellery. */
function authorArm(bind, tones, { watch = false, bracelet = false } = {}) {
  const soup = new SkinSoup();
  const { skin, glove, palm, seam, pad, gold, goldDark, dial } = tones;
  const SKIN_ROUGH = 0.56;
  const GLOVE_ROUGH = 0.84;
  const gloveSrf = (rough) => [rough, 0, 0, FINISH.glove];
  const handBind = (z) => {
    const w = sectionAt(z).hand;
    return [BONE.forearm, BONE.hand, w];
  };

  // ---- forearm and hand: one skin from the elbow to the knuckles -------------------------------
  const N = 16;
  const armRings = SECTIONS.map(([z, w, top, bot, exp, x, hand]) => ({
    c: [x, 0, z],
    w,
    h: 0,
    top,
    bot,
    exp,
    bind: [BONE.forearm, BONE.hand, hand],
    paint: (i, n) => {
      const a = i < 0 ? -Math.PI / 2 : ((i + 0.5) / n) * Math.PI * 2;
      const under = Math.max(0, -Math.sin(a)); // 1 on the palm side
      if (z < GLOVE_TO) return [...mix(glove, palm, under * 0.85), GLOVE_ROUGH + 0.12 * under];
      return [...mix(skin, scale(skin, 1.12), under * 0.4), SKIN_ROUGH + 0.06 * under];
    },
  }));
  // Gloved and bare parts of the one skin take different finishes: split the loft by ring.
  const handRings = armRings.filter((r) => r.c[2] <= 0.02);
  const bareRings = armRings.filter((r) => r.c[2] >= 0.02); // the shared ring sits under the cuff
  soup.add(skinLoft(bareRings, N, [true, false]), { crease: 1.3 });
  soup.add(skinLoft(handRings, N, [false, true], FINISH.glove), { crease: 1.3 });

  /** A band around the arm at z: `grow` metres proud of the skin. */
  const hoop = (z, grow, extra = {}) => {
    const s = sectionAt(z);
    return { c: [s.x, 0, z], w: s.w + grow * 2, h: 0, top: s.top + grow, bot: s.bot + grow, exp: s.exp, ...extra };
  };

  // ---- glove ------------------------------------------------------------------------------------
  // Cuff: a padded band over the wrist with a rolled edge and a strap across the back.
  const cuff = [hoop(0.042, 0.0018), hoop(0.039, 0.0034), hoop(0.03, 0.0036), hoop(0.012, 0.0032), hoop(0.004, 0.0016)];
  soup.add(skinLoft(cuff.map((r) => ({ ...r, bind: handBind(r.c[2]), paint: (i, n) => [...glove, GLOVE_ROUGH] })), N, [false, false], FINISH.glove), { crease: 0.9 });
  const edge = [hoop(0.0425, 0.0024), hoop(0.0405, 0.0042), hoop(0.0385, 0.0042), hoop(0.0368, 0.0024)];
  soup.add(skinLoft(edge.map((r) => ({ ...r, bind: handBind(r.c[2]), paint: () => [...seam, 0.5] })), N, [false, false], FINISH.plain), { crease: 0.9 });
  {
    const s = sectionAt(0.022);
    const y = s.top + 0.0034;
    const strap = loft(
      [-0.02, -0.012, 0, 0.012, 0.02].map((x, k) => ({ c: [x, y + (k === 0 || k === 4 ? -0.0008 : 0), 0.022], ax: [0, 0, 1], ay: [0, 1, 0], w: 0.024, h: 0, top: 0.0022, bot: 0.0012, exp: 3 })),
      8,
      [true, true],
    );
    soup.add(strap, { col: pad, srf: gloveSrf(0.5), skin: handBind(0.022), crease: 0.8 });
    // Stitching around the strap: a slightly larger, lower plate in the seam colour.
    const rim = loft(
      [-0.0215, 0.0215].map((x) => ({ c: [x, y - 0.0003, 0.022], ax: [0, 0, 1], ay: [0, 1, 0], w: 0.0265, h: 0, top: 0.0019, bot: 0.001, exp: 3 })),
      8,
      [true, true],
    );
    soup.add(rim, { col: seam, srf: [0.6, 0, 0, FINISH.plain], skin: handBind(0.022), crease: 0.8 });
  }

  // Back-of-hand panel: a raised stitched panel from the wrist to the knuckle pad.
  {
    const rings = [];
    const rimRings = [];
    for (const z of [-0.004, -0.018, -0.034, -0.05, -0.064]) {
      const s = sectionAt(z);
      const w = s.w * (z > -0.01 ? 0.52 : 0.66);
      rings.push({ c: [s.x, s.top - 0.0018, z], w, h: 0, top: 0.0042, bot: 0.001, exp: 2.6 });
      rimRings.push({ c: [s.x, s.top - 0.0018, z + 0.0012], w: w + 0.0036, h: 0, top: 0.0034, bot: 0.001, exp: 2.6 });
    }
    soup.add(loft(rings, 12, [true, true]), { col: scale(glove, 1.15), srf: gloveSrf(0.58), skin: [BONE.hand, BONE.hand, 0], crease: 1.0 });
    soup.add(loft(rimRings, 12, [true, true]), { col: seam, srf: [0.6, 0, 0, FINISH.plain], skin: [BONE.hand, BONE.hand, 0], crease: 1.0 });
  }

  // Padded knuckle: a moulded bar across the knuckles with one dome per finger.
  {
    const z = -0.084;
    const s = sectionAt(z);
    const bar = loft(
      [-0.042, -0.032, 0, 0.034, 0.044].map((x, k) => ({ c: [x + s.x, s.top + (k === 0 || k === 4 ? 0.0006 : 0.0024), z], ax: [0, 0, 1], ay: [0, 1, 0], w: k === 0 || k === 4 ? 0.014 : 0.02, h: 0, top: 0.0048, bot: 0.002, exp: 2.6 })),
      10,
      [true, true],
    );
    soup.add(bar, { col: pad, srf: [0.42, 0, 0, FINISH.plain], skin: [BONE.hand, BONE.hand, 0], crease: 1.1 });
  }
  for (const name of FINGERS) {
    const [x, y, z] = HAND.knuckle[name];
    const r = HAND.radius[name] * 1.2;
    const dome = new THREE.SphereGeometry(r, 8, 6);
    dome.deleteAttribute('uv');
    dome.deleteAttribute('normal');
    dome.scale(1, 0.8, 1.2);
    dome.translate(x, y + 0.0042, z + 0.004);
    soup.add(dome, { col: pad, srf: [0.4, 0, 0, FINISH.plain], skin: [BONE.hand, BONE.hand, 0], crease: 1.4 });
  }

  // ---- a finger or the thumb: a tapered tube with three bones -----------------------------------
  const digit = (first, lengths, r0, r1, rootDepth, meta) => {
    const [l0, l1, l2] = lengths;
    const total = l0 + l1 + l2;
    const n = 8;
    const radius = (d) => r0 + (r1 - r0) * Math.max(0, Math.min(1, d / total));
    // [distance from the root joint, radius factor, bone A, bone B, weight of B, joint?]
    const marks = [
      [-rootDepth, meta ? 1.25 : 1.04, first, first, 0],
      [meta ? l0 * 0.45 : 0.012, meta ? 1.12 : 1.04, first, first, 0],
      [l0 - 0.007, 1.03, first, first + 1, 0.12],
      [l0, 1.1, first, first + 1, 0.5, true],
      [l0 + 0.007, 1.03, first, first + 1, 0.88],
      [l0 + l1 - 0.006, 1.02, first + 1, first + 2, 0.12],
      [l0 + l1, 1.09, first + 1, first + 2, 0.5, true],
      [l0 + l1 + 0.006, 1.02, first + 1, first + 2, 0.88],
      [total - 0.008, 1.0, first + 2, first + 2, 0],
      [total - 0.0028, 0.8, first + 2, first + 2, 0],
      [total, 0.34, first + 2, first + 2, 0],
    ];
    const rings = marks.map(([d, k, a, b, w, joint]) => {
      const r = radius(d) * k;
      return {
        c: [0, 0, -d],
        w: r * 2,
        h: 0,
        top: r * 0.92,
        bot: r * 0.96,
        exp: 2.2,
        bind: [a, b, w],
        paint: (i, m) => {
          if (i < 0) return [...palm, GLOVE_ROUGH];
          const ang = ((i + 0.5) / m) * Math.PI * 2;
          const under = Math.max(0, -Math.sin(ang));
          let c = mix(glove, palm, under * 0.85);
          if (joint) c = mix(c, seam, Math.sin(ang) > 0 ? 0.4 : 0.15); // creased fabric over the joint
          return [...c, GLOVE_ROUGH + 0.1 * under];
        },
      };
    });
    soup.add(skinLoft(rings, n, [false, true], FINISH.glove), { m: bind[first], crease: 1.3 });
    // Grip pad on the inside of the last segment.
    const rn = radius(total - 0.012);
    const tip = loft(
      [total - 0.019, total - 0.012, total - 0.005].map((d, k) => ({ c: [0, -rn * 0.62, -d], w: rn * (k === 1 ? 1.5 : 1.2), h: 0, top: rn * 0.2, bot: rn * 0.42, exp: 2.4 })),
      6,
      [true, true],
    );
    soup.add(tip, { m: bind[first], col: pad, srf: [0.7, 0, 0, FINISH.plain], skin: [first + 2, first + 2, 0], crease: 1.0 });
  };

  FINGERS.forEach((name, f) => {
    const r = HAND.radius[name];
    digit(BONE.finger + f * 3, HAND.length[name], r, r * 0.82, 0.01, false);
  });
  digit(BONE.thumb, HAND.thumb.length, HAND.thumb.radius * 1.12, HAND.thumb.radius * 0.82, 0.008, true);

  // ---- jewellery on the bare forearm -------------------------------------------------------------
  const goldSrf = [0.24, 1, 0, FINISH.plain];
  const fixed = { skin: [BONE.forearm, BONE.forearm, 0] };
  if (watch) {
    // Bracelet: a belt around the forearm, then the case on the back of it.
    const at = 0.072;
    const belt = (z, grow) => hoop(z, 0.0012 + grow);
    const band = loft([belt(at - 0.0095, 0), belt(at - 0.009, 0.0022), belt(at + 0.009, 0.0022), belt(at + 0.0095, 0)], 18, [false, false]);
    soup.add(band, { ...fixed, col: gold, srf: [0.3, 1, 0, FINISH.brushed], crease: 0.5 });
    for (const z of [at - 0.0045, at, at + 0.0045]) {
      const groove = loft([belt(z - 0.0004, 0.0024), belt(z + 0.0004, 0.0024)], 18, [false, false]);
      soup.add(groove, { ...fixed, col: goldDark, srf: [0.45, 1, 0, FINISH.plain], crease: 0.5 });
    }
    const y0 = sectionAt(at).top + 0.0012;
    soup.add(rod([0, y0, at], [0, y0 + 0.0085, at], 0.0195, 0.0195, 18), { ...fixed, col: gold, srf: goldSrf, crease: 0.5 });
    soup.add(rod([0, y0 + 0.0075, at], [0, y0 + 0.0105, at], 0.0212, 0.0198, 18), { ...fixed, col: gold, srf: [0.2, 1, 0, FINISH.plain], crease: 0.5 });
    soup.add(rod([0, y0 + 0.0102, at], [0, y0 + 0.0108, at], 0.0172, 0.0172, 18), { ...fixed, col: dial, srf: [0.1, 0, 0, FINISH.plain], crease: 0.5 });
    for (let h = 0; h < 12; h += 3) {
      const m = new THREE.Matrix4().makeRotationY((h / 12) * Math.PI * 2).setPosition(0, 0, at);
      soup.add(block(0.0115, 0.0155, y0 + 0.0108, y0 + 0.0113, -0.0011, 0.0011), { ...fixed, m, col: gold, srf: goldSrf, crease: 0.3 });
    }
    for (const [a, len] of [[0.9, 0.012], [-2.1, 0.009]]) {
      const m = new THREE.Matrix4().makeRotationY(a).setPosition(0, 0, at);
      soup.add(block(-0.002, len, y0 + 0.0109, y0 + 0.0114, -0.0007, 0.0007), { ...fixed, m, col: gold, srf: goldSrf, crease: 0.3 });
    }
    soup.add(rod([0.0195, y0 + 0.0045, at], [0.0235, y0 + 0.0045, at], 0.0028, 0.0028, 8), { ...fixed, col: gold, srf: goldSrf, crease: 0.5 }); // crown
  }
  if (bracelet) {
    // A heavy curb chain hanging loose round the forearm: links tilted alternately along a ring.
    const at = 0.07;
    const s = sectionAt(at);
    const links = 26;
    const rx = s.w / 2 + 0.0036;
    const ry = (s.top + s.bot) / 2 + 0.0036;
    const point = (k, lift) => {
      const a = (k / links) * Math.PI * 2;
      const sag = Math.max(0, -Math.sin(a)) * 0.0028; // it hangs a little under the arm
      return [s.x + Math.cos(a) * (rx + lift), Math.sin(a) * (ry + lift) - sag, at + (k % 2 ? 0.0007 : -0.0007)];
    };
    for (let k = 0; k < links; k++) {
      // Each link overlaps the next, alternately raised: the twist of a curb chain.
      const lift = k % 2 ? 0.0008 : 0;
      soup.add(rod(point(k - 0.1, lift), point(k + 1.1, lift), 0.0028, 0.0028, 6), { ...fixed, col: k % 2 ? gold : scale(gold, 0.78), srf: goldSrf, crease: 0.6 });
    }
  }
  return soup;
}

// ------------------------------------------------------------------------------------------------
// Runtime
// ------------------------------------------------------------------------------------------------

const _m = new THREE.Matrix4();
const _q = new THREE.Quaternion();
const _qa = new THREE.Quaternion();
const _v = new THREE.Vector3();
const _x = new THREE.Vector3();
const _y = new THREE.Vector3();
const _z = new THREE.Vector3();
const ONE = new THREE.Vector3(1, 1, 1);
const AXIS_X = new THREE.Vector3(1, 0, 0);
const AXIS_Y = new THREE.Vector3(0, 1, 0);
const AXIS_Z = new THREE.Vector3(0, 0, 1);

/** One arm: welds the soup, converts it to bone space and keeps the matrices that pose it. */
function createArm(side, tones, options) {
  const bones = authorBones();
  if (side < 0) {
    for (const bone of bones) {
      bone.pos = [-bone.pos[0], bone.pos[1], bone.pos[2]];
      bone.quat.set(bone.quat.x, -bone.quat.y, -bone.quat.z, bone.quat.w);
    }
  }
  // Authored right-handed against right-handed bind matrices, then mirrored as a whole.
  const soup = authorArm(bindMatrices(authorBones()), tones, options);
  if (side < 0) soup.mirror();
  const bind = bindMatrices(bones);
  const inverse = bind.map((m) => m.clone().invert());

  // Weld identical corners so shared vertices are skinned once.
  const lookup = new Map();
  const index = [];
  const keep = [];
  const corners = soup.pos.length / 3;
  for (let i = 0; i < corners; i++) {
    const p = i * 3;
    const key = [
      Math.round(soup.pos[p] * HASH), Math.round(soup.pos[p + 1] * HASH), Math.round(soup.pos[p + 2] * HASH),
      Math.round(soup.nor[p] * 500), Math.round(soup.nor[p + 1] * 500), Math.round(soup.nor[p + 2] * 500),
      Math.round(soup.col[p] * 2000), Math.round(soup.col[p + 1] * 2000), Math.round(soup.col[p + 2] * 2000),
      soup.skin[p], soup.skin[p + 1], Math.round(soup.skin[p + 2] * 100),
    ].join(',');
    let v = lookup.get(key);
    if (v === undefined) {
      v = keep.length;
      keep.push(i);
      lookup.set(key, v);
    }
    index.push(v);
  }

  const count = keep.length;
  const arm = {
    side,
    count,
    index,
    boneA: new Uint8Array(count),
    boneB: new Uint8Array(count),
    weight: new Float32Array(count),
    localA: new Float32Array(count * 3),
    localB: new Float32Array(count * 3),
    normalA: new Float32Array(count * 3),
    normalB: new Float32Array(count * 3),
    color: new Float32Array(count * 3),
    surface: new Float32Array(count * 4),
    rest: new Float32Array(count * 3),
    bones,
    matrices: new Float32Array(BONE.count * 16),
    // Driven by the viewmodel:
    pos: new THREE.Vector3(),
    quat: new THREE.Quaternion(),
    elbow: new THREE.Vector3(side * 0.3, -0.45, 0.1),
    pose: new Float32Array(POSE.size),
    /** The hand bone in rig space, valid after update(). */
    matrix: new THREE.Matrix4(),
  };
  const p = new THREE.Vector3();
  const nrm = new THREE.Vector3();
  const rot = new THREE.Matrix3();
  keep.forEach((corner, v) => {
    const c = corner * 3;
    const a = soup.skin[c];
    const b = soup.skin[c + 1];
    arm.boneA[v] = a;
    arm.boneB[v] = b;
    arm.weight[v] = a === b ? 0 : soup.skin[c + 2];
    for (const [bone, local, normal] of [[a, arm.localA, arm.normalA], [b, arm.localB, arm.normalB]]) {
      p.set(soup.pos[c], soup.pos[c + 1], soup.pos[c + 2]).applyMatrix4(inverse[bone]);
      nrm.set(soup.nor[c], soup.nor[c + 1], soup.nor[c + 2]).applyMatrix3(rot.setFromMatrix4(inverse[bone]));
      p.toArray(local, v * 3);
      nrm.toArray(normal, v * 3);
    }
    arm.color.set([soup.col[c], soup.col[c + 1], soup.col[c + 2]], v * 3);
    arm.surface.set([soup.srf[corner * 4], soup.srf[corner * 4 + 1], soup.srf[corner * 4 + 2], soup.srf[corner * 4 + 3]], v * 4);
    arm.rest.set([soup.pos[c], soup.pos[c + 1], soup.pos[c + 2]], v * 3);
  });
  return arm;
}

/** Bone matrices in rig space from the arm's hand frame, elbow and pose. */
function solve(arm) {
  const { bones, matrices, pose, side } = arm;
  const out = (i) => i * 16;

  // Hand.
  arm.matrix.compose(arm.pos, arm.quat, ONE);
  arm.matrix.toArray(matrices, out(BONE.hand));

  // Forearm: from the wrist toward the elbow, rolled to follow the back of the hand.
  _z.subVectors(arm.elbow, arm.pos).normalize();
  _y.set(0, 1, 0).applyQuaternion(arm.quat);
  _y.addScaledVector(_z, -_y.dot(_z));
  if (_y.lengthSq() < 1e-4) {
    // Hand bent straight back along the forearm: fall back to its sideways axis.
    _y.set(1, 0, 0).applyQuaternion(arm.quat);
    _y.addScaledVector(_z, -_y.dot(_z));
  }
  _y.normalize();
  _x.crossVectors(_y, _z);
  _m.makeBasis(_x, _y, _z).setPosition(arm.pos);
  _m.toArray(matrices, out(BONE.forearm));

  // Fingers and thumb: parent × rest × pose rotation.
  for (let i = BONE.finger; i < BONE.count; i++) {
    const bone = bones[i];
    _q.copy(bone.quat);
    if (i < BONE.thumb) {
      const f = Math.floor((i - BONE.finger) / 3);
      const joint = (i - BONE.finger) % 3;
      if (joint === 0) _q.multiply(_qa.setFromAxisAngle(AXIS_Y, side * pose[f * 4 + 3]));
      _q.multiply(_qa.setFromAxisAngle(AXIS_X, -pose[f * 4 + joint]));
    } else {
      const joint = i - BONE.thumb;
      const t = POSE.thumb;
      if (joint === 0) {
        _q.multiply(_qa.setFromAxisAngle(AXIS_Y, -side * pose[t]));
        _q.multiply(_qa.setFromAxisAngle(AXIS_X, -pose[t + 1]));
        _q.multiply(_qa.setFromAxisAngle(AXIS_Z, side * pose[t + 2]));
      } else {
        _q.multiply(_qa.setFromAxisAngle(AXIS_X, -pose[t + 2 + joint]));
      }
    }
    _m.compose(_v.fromArray(bone.pos), _q, ONE);
    const parent = out(bone.parent);
    const me = out(i);
    // matrices[me] = matrices[parent] × _m (column-major 4×4, affine)
    const a = matrices;
    const b = _m.elements;
    for (let c = 0; c < 4; c++) {
      const b0 = b[c * 4];
      const b1 = b[c * 4 + 1];
      const b2 = b[c * 4 + 2];
      const b3 = b[c * 4 + 3];
      a[me + c * 4] = a[parent] * b0 + a[parent + 4] * b1 + a[parent + 8] * b2 + a[parent + 12] * b3;
      a[me + c * 4 + 1] = a[parent + 1] * b0 + a[parent + 5] * b1 + a[parent + 9] * b2 + a[parent + 13] * b3;
      a[me + c * 4 + 2] = a[parent + 2] * b0 + a[parent + 6] * b1 + a[parent + 10] * b2 + a[parent + 14] * b3;
      a[me + c * 4 + 3] = c === 3 ? 1 : 0;
    }
  }
}

/** Writes the arm's skinned positions and normals into the shared buffers from vertex `base` on. */
function skin(arm, position, normal, base) {
  const { count, boneA, boneB, weight, localA, localB, normalA, normalB, matrices: m } = arm;
  for (let v = 0; v < count; v++) {
    const i = v * 3;
    const a = boneA[v] * 16;
    let x = localA[i];
    let y = localA[i + 1];
    let z = localA[i + 2];
    let px = m[a] * x + m[a + 4] * y + m[a + 8] * z + m[a + 12];
    let py = m[a + 1] * x + m[a + 5] * y + m[a + 9] * z + m[a + 13];
    let pz = m[a + 2] * x + m[a + 6] * y + m[a + 10] * z + m[a + 14];
    x = normalA[i];
    y = normalA[i + 1];
    z = normalA[i + 2];
    let nx = m[a] * x + m[a + 4] * y + m[a + 8] * z;
    let ny = m[a + 1] * x + m[a + 5] * y + m[a + 9] * z;
    let nz = m[a + 2] * x + m[a + 6] * y + m[a + 10] * z;
    const w = weight[v];
    if (w > 0) {
      const b = boneB[v] * 16;
      x = localB[i];
      y = localB[i + 1];
      z = localB[i + 2];
      px += (m[b] * x + m[b + 4] * y + m[b + 8] * z + m[b + 12] - px) * w;
      py += (m[b + 1] * x + m[b + 5] * y + m[b + 9] * z + m[b + 13] - py) * w;
      pz += (m[b + 2] * x + m[b + 6] * y + m[b + 10] * z + m[b + 14] - pz) * w;
      x = normalB[i];
      y = normalB[i + 1];
      z = normalB[i + 2];
      nx += (m[b] * x + m[b + 4] * y + m[b + 8] * z - nx) * w;
      ny += (m[b + 1] * x + m[b + 5] * y + m[b + 9] * z - ny) * w;
      nz += (m[b + 2] * x + m[b + 6] * y + m[b + 10] * z - nz) * w;
    }
    const o = (base + v) * 3;
    position[o] = px;
    position[o + 1] = py;
    position[o + 2] = pz;
    normal[o] = nx;
    normal[o + 1] = ny;
    normal[o + 2] = nz;
  }
}

/**
 * Both arms as one mesh. `skinHex` is the catalogue skin tone, `goldHex` the catalogue gold.
 * Returns {mesh, left, right, triangles, update()}.
 */
export function buildArms(material, skinHex = 0x7a4a2e, goldHex = 0xe7b53a) {
  const tones = {
    skin: scale(mix(linear(skinHex), linear(0x5b3b2b), 0.35), 0.85), // deeper and less orange: it is seen in full sun
    glove: linear(0x151618),
    palm: linear(0x1e1c1a), // synthetic suede
    seam: linear(0x3c3e43), // stitching
    pad: linear(0x111113), // moulded rubber
    gold: linear(goldHex),
    goldDark: scale(linear(goldHex), 0.45),
    dial: linear(0x0a0a0c),
  };
  const right = createArm(1, tones, { bracelet: true });
  const left = createArm(-1, tones, { watch: true });
  const arms = [right, left];

  const total = right.count + left.count;
  const position = new Float32Array(total * 3);
  const normal = new Float32Array(total * 3);
  const color = new Float32Array(total * 3);
  const mre = new Float32Array(total * 4);
  const rest = new Float32Array(total * 3);
  const index = [];
  let base = 0;
  for (const arm of arms) {
    arm.base = base;
    color.set(arm.color, base * 3);
    mre.set(arm.surface, base * 4);
    rest.set(arm.rest, base * 3);
    for (const v of arm.index) index.push(base + v);
    base += arm.count;
  }
  const geometry = new THREE.BufferGeometry();
  const positionAttr = new THREE.BufferAttribute(position, 3).setUsage(THREE.DynamicDrawUsage);
  const normalAttr = new THREE.BufferAttribute(normal, 3).setUsage(THREE.DynamicDrawUsage);
  geometry.setAttribute('position', positionAttr);
  geometry.setAttribute('normal', normalAttr);
  geometry.setAttribute('color', new THREE.BufferAttribute(color, 3));
  geometry.setAttribute('mre', new THREE.BufferAttribute(mre, 4));
  geometry.setAttribute('rest', new THREE.BufferAttribute(rest, 3));
  geometry.setIndex(index);

  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = 'arms';
  mesh.frustumCulled = false; // the vertices move every frame; the arms are always in view

  return {
    mesh,
    left,
    right,
    triangles: index.length / 3,
    update() {
      for (const arm of arms) {
        solve(arm);
        skin(arm, position, normal, arm.base);
      }
      positionAttr.needsUpdate = true;
      normalAttr.needsUpdate = true;
    },
  };
}

/**
 * The hand frame that puts the middle of the palm at `at`, facing along `into` (the direction the
 * palm presses), with the fingers running along `along`. Writes arm.pos / arm.quat.
 */
export function placePalm(arm, at, into, along) {
  _z.copy(along).normalize().negate(); // local +Z runs from the fingers back to the wrist
  _y.copy(into).negate();
  _y.addScaledVector(_z, -_y.dot(_z)).normalize(); // local +Y is the back of the hand
  _x.crossVectors(_y, _z);
  arm.quat.setFromRotationMatrix(_m.makeBasis(_x, _y, _z));
  _v.set(arm.side * HAND.palm[0], HAND.palm[1], HAND.palm[2]).applyQuaternion(arm.quat);
  arm.pos.copy(at).sub(_v);
}
