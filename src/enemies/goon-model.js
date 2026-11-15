// The Goon: a stylised low-poly masked gunman, 1.8 m tall, built as one rigid-skinned geometry
// (body, SMG and the pipe on his back) in three outfits. Black with oxblood accents, a pale mask and
// pale sneakers so the head and the feet read at night.
//
// Bind pose: standing at the origin, feet on y = 0, facing −Z, arms hanging straight down, right
// side toward +X. The SMG and the pipe are modelled in their own frames (see GUN and PIPE below) and
// placed by the pose code every frame.

import * as THREE from 'three';
import { createEnemyMaterial, createModelBuilder } from './rig.js';

/** Bone slots. Slot 0 carries shader parameters (rig.js). */
export const B = {
  HIPS: 1,
  SPINE: 2,
  HEAD: 3,
  L_UARM: 4,
  L_LARM: 5,
  L_HAND: 6,
  R_UARM: 7,
  R_LARM: 8,
  R_HAND: 9,
  L_ULEG: 10,
  L_LLEG: 11,
  L_FOOT: 12,
  R_ULEG: 13,
  R_LLEG: 14,
  R_FOOT: 15,
  GUN: 16,
  PIPE: 17,
};
export const SLOTS = 18;

/** Joint positions in the bind pose (model space), per bone slot: x, y, z. */
export const PIVOT = new Float32Array(SLOTS * 3);
const pivot = (bone, x, y, z) => PIVOT.set([x, y, z], bone * 3);
const SHOULDER_X = 0.2;
const HIP_X = 0.095;
pivot(B.HIPS, 0, 0.96, 0);
pivot(B.SPINE, 0, 1.05, 0);
pivot(B.HEAD, 0, 1.5, 0.005);
pivot(B.L_UARM, -SHOULDER_X, 1.42, 0);
pivot(B.L_LARM, -SHOULDER_X, 1.14, 0);
pivot(B.L_HAND, -SHOULDER_X, 0.87, 0);
pivot(B.R_UARM, SHOULDER_X, 1.42, 0);
pivot(B.R_LARM, SHOULDER_X, 1.14, 0);
pivot(B.R_HAND, SHOULDER_X, 0.87, 0);
pivot(B.L_ULEG, -HIP_X, 0.93, 0);
pivot(B.L_LLEG, -HIP_X, 0.5, 0);
pivot(B.L_FOOT, -HIP_X, 0.085, 0);
pivot(B.R_ULEG, HIP_X, 0.93, 0);
pivot(B.R_LLEG, HIP_X, 0.5, 0);
pivot(B.R_FOOT, HIP_X, 0.085, 0);
// The gun and the pipe pivot on their own origins.

/** Limb lengths that follow from the pivots. */
export const LIMB = { upperArm: 0.28, lowerArm: 0.27, upperLeg: 0.43, lowerLeg: 0.415, ankle: 0.085 };

/** Centre of the head above the neck joint, and the radius the hood fills (matches the hit sphere). */
export const HEAD = { centreY: 0.12, radius: 0.15 };

/**
 * The SMG in its own frame: origin where the right hand holds the grip, barrel toward −Z, up +Y.
 * `fore` is where the left hand holds it, `butt` what sits against the shoulder.
 */
export const GUN = {
  muzzle: [0, 0.042, -0.385],
  lamp: [0, -0.002, -0.318],
  fore: [0, -0.012, -0.17],
  butt: [0, 0.03, 0.235],
};

/** The pipe in its own frame: origin in the fist, length along +Y, about 0.7 m. */
export const PIPE = { tip: [0, 0.56, 0] };

const COLOR = {
  black: 0x232328, // black cloth: dark, but with enough albedo that folds read in the sun
  jacket: 0x28282e,
  charcoal: 0x30323b,
  oxblood: 0x7c151d,
  oxbloodDark: 0x4d0d13,
  mask: 0xdcd5c5,
  maskShade: 0xb5ad9c,
  eye: 0x050506,
  glove: 0x0d0d0f,
  sneaker: 0xd6d1c4,
  sole: 0xefece4,
  denim: 0x262a36,
  gun: 0x24262c,
  gunLight: 0x34373f,
  lens: 0x2a1c10,
  pipe: 0x8f949c,
  tape: 0x18181a,
};

// How much of their own colour the readable parts give off (mask, sneakers, crew colours).
const GLOW = { mask: 0.2, accent: 0.3, sneaker: 0.05, pipe: 0.03 };

const box = (w, h, d) => new THREE.BoxGeometry(w, h, d);
/** Frustum along Y with `sides` faces, elliptical when scaled; radii at the top and the bottom. */
const tube = (rTop, rBottom, h, sides = 6) => new THREE.CylinderGeometry(rTop, rBottom, h, sides, 1);
const ball = (r, detail = 1) => new THREE.IcosahedronGeometry(r, detail);

function mirrorX(v) {
  return [-v[0], v[1], v[2]];
}

/**
 * @param {0|1|2} variant  0 hoodie (hood up, full ski mask) · 1 puffer (beanie, bandana) · 2 tracksuit (cap, ski mask)
 */
export function buildGoonGeometry(variant) {
  const m = createModelBuilder();
  const hoodie = variant === 0;
  const puffer = variant === 1;
  const track = variant === 2;
  const cloth = puffer ? COLOR.jacket : COLOR.black;
  const sleeve = cloth;
  const pants = track ? COLOR.black : puffer ? COLOR.charcoal : COLOR.denim;
  const bulk = puffer ? 1.16 : 1;

  /** Adds a part on the left bone and its mirror image on the right bone. */
  const pair = (geometry, left, right, opts) => {
    m.add(geometry, { ...opts, bone: left });
    const scale = typeof opts.scale === 'number' ? [opts.scale, opts.scale, opts.scale] : opts.scale || [1, 1, 1];
    const rot = opts.rot || [0, 0, 0];
    m.add(geometry, { ...opts, bone: right, at: mirrorX(opts.at), rot: [rot[0], -rot[1], -rot[2]], scale: [-scale[0], scale[1], scale[2]] });
  };

  // ---- pelvis and legs -------------------------------------------------------------------------
  m.add(tube(0.5, 0.46, 0.17, 8), { bone: B.HIPS, at: [0, 0.955, 0], scale: [0.36, 1, 0.235], color: pants });
  m.add(box(0.2, 0.035, 0.24), { bone: B.HIPS, at: [0, 1.03, 0], scale: [1.72, 1, 1], color: puffer ? COLOR.oxbloodDark : COLOR.black }); // belt / hem line

  pair(tube(0.086, 0.066, 0.45, 6), B.L_ULEG, B.R_ULEG, { at: [-HIP_X, 0.715, 0], color: pants });
  pair(ball(0.084, 0), B.L_ULEG, B.R_ULEG, { at: [-HIP_X, 0.91, 0], color: pants });
  pair(ball(0.07, 0), B.L_LLEG, B.R_LLEG, { at: [-HIP_X, 0.5, -0.004], color: pants });
  pair(tube(0.066, 0.048, 0.4, 6), B.L_LLEG, B.R_LLEG, { at: [-HIP_X, 0.3, 0], color: pants });
  if (track) {
    // Side stripes: the crew colour all the way down.
    pair(box(0.012, 0.42, 0.03), B.L_ULEG, B.R_ULEG, { at: [-HIP_X - 0.078, 0.715, 0], rot: [0, 0, -0.045], color: COLOR.oxblood, glow: GLOW.accent });
    pair(box(0.012, 0.38, 0.03), B.L_LLEG, B.R_LLEG, { at: [-HIP_X - 0.058, 0.3, 0], rot: [0, 0, -0.045], color: COLOR.oxblood, glow: GLOW.accent });
  }

  // Sneakers: a pale upper on a paler sole, toe toward −Z.
  pair(box(0.098, 0.028, 0.275), B.L_FOOT, B.R_FOOT, { at: [-HIP_X, 0.014, -0.062], color: COLOR.sole, glow: GLOW.sneaker });
  pair(box(0.09, 0.062, 0.15), B.L_FOOT, B.R_FOOT, { at: [-HIP_X, 0.058, 0.005], color: COLOR.sneaker, glow: GLOW.sneaker });
  pair(box(0.09, 0.046, 0.13), B.L_FOOT, B.R_FOOT, { at: [-HIP_X, 0.047, -0.128], rot: [0.12, 0, 0], color: COLOR.sneaker, glow: GLOW.sneaker }); // toe box
  pair(box(0.092, 0.05, 0.012), B.L_FOOT, B.R_FOOT, { at: [-HIP_X, 0.062, 0.082], color: COLOR.oxblood, glow: GLOW.accent }); // heel tab
  pair(tube(0.058, 0.052, 0.05, 6), B.L_FOOT, B.R_FOOT, { at: [-HIP_X, 0.105, 0.006], color: pants }); // trouser cuff over the ankle

  // ---- torso -------------------------------------------------------------------------------------
  if (puffer) {
    // Quilted rings, wider toward the chest, and a tall collar.
    const rings = [
      [1.03, 0.4, 0.27],
      [1.13, 0.43, 0.29],
      [1.23, 0.46, 0.3],
      [1.33, 0.47, 0.3],
    ];
    for (const [y, w, d] of rings) m.add(tube(0.5, 0.5, 0.115, 8), { bone: B.SPINE, at: [0, y + 0.05, 0], scale: [w, 1, d], color: cloth });
    for (const [y, w, d] of rings.slice(1)) m.add(tube(0.5, 0.5, 0.012, 8), { bone: B.SPINE, at: [0, y - 0.006, 0], scale: [w * 0.94, 1, d * 0.94], color: COLOR.black });
    m.add(tube(0.36, 0.5, 0.075, 8), { bone: B.SPINE, at: [0, 1.4725, 0], scale: [0.46, 1, 0.29], color: COLOR.oxblood, glow: GLOW.accent }); // shoulder yoke
    m.add(tube(0.5, 0.56, 0.085, 8), { bone: B.SPINE, at: [0, 1.535, 0.008], scale: [0.2, 1, 0.21], color: cloth }); // collar
    m.add(box(0.016, 0.38, 0.012), { bone: B.SPINE, at: [0, 1.27, -0.151], color: COLOR.oxblood, glow: GLOW.accent }); // zip
  } else {
    m.add(tube(0.5, 0.45, 0.4, 8), { bone: B.SPINE, at: [0, 1.22, 0], scale: [0.42, 1, 0.25], color: cloth });
    m.add(tube(0.45, 0.47, 0.14, 8), { bone: B.SPINE, at: [0, 0.99, 0], scale: [0.4, 1, 0.25], color: cloth }); // hem over the belt
    m.add(tube(0.3, 0.5, 0.075, 8), { bone: B.SPINE, at: [0, 1.4575, 0], scale: [0.42, 1, 0.25], color: cloth }); // shoulders
    if (hoodie) {
      m.add(box(0.24, 0.11, 0.02), { bone: B.SPINE, at: [0, 1.105, -0.122], rot: [0.07, 0, 0], color: 0x0e0e11 }); // pouch pocket
      m.add(box(0.008, 0.13, 0.008), { bone: B.SPINE, at: [-0.04, 1.36, -0.128], rot: [0.05, 0, 0.06], color: COLOR.oxblood, glow: GLOW.accent }); // drawstrings
      m.add(box(0.008, 0.11, 0.008), { bone: B.SPINE, at: [0.04, 1.37, -0.128], rot: [0.05, 0, -0.06], color: COLOR.oxblood, glow: GLOW.accent });
      m.add(tube(0.5, 0.5, 0.05, 8), { bone: B.SPINE, at: [0, 0.94, 0], scale: [0.405, 1, 0.252], color: COLOR.oxbloodDark, glow: GLOW.accent * 0.5 }); // waistband
    } else {
      m.add(box(0.014, 0.4, 0.012), { bone: B.SPINE, at: [0, 1.24, -0.127], color: COLOR.oxblood, glow: GLOW.accent }); // zip
      m.add(tube(0.5, 0.52, 0.06, 8), { bone: B.SPINE, at: [0, 1.52, 0.006], scale: [0.17, 1, 0.18], color: cloth }); // stand-up collar
    }
  }
  // The crew mark on the back: an oxblood V.
  for (const side of [-1, 1]) {
    m.add(box(0.03, 0.2, 0.01), { bone: B.SPINE, at: [side * 0.048, 1.29, puffer ? 0.154 : 0.127], rot: [0, 0, side * 0.42], color: COLOR.oxblood, glow: GLOW.accent });
  }
  m.add(tube(0.052, 0.058, 0.09, 6), { bone: B.SPINE, at: [0, 1.5, 0.005], color: COLOR.black }); // neck

  // ---- arms --------------------------------------------------------------------------------------
  const armR = [0.07 * bulk, 0.058 * bulk, 0.055 * bulk, 0.045];
  pair(ball(0.078 * bulk, 0), B.L_UARM, B.R_UARM, { at: [-SHOULDER_X, 1.42, 0], color: puffer ? COLOR.oxblood : sleeve, glow: puffer ? GLOW.accent : 0 });
  pair(tube(armR[0], armR[1], 0.27, 6), B.L_UARM, B.R_UARM, { at: [-SHOULDER_X, 1.28, 0], color: sleeve });
  pair(ball(0.06 * bulk, 0), B.L_LARM, B.R_LARM, { at: [-SHOULDER_X, 1.14, 0], color: sleeve });
  pair(tube(armR[2], armR[3], 0.25, 6), B.L_LARM, B.R_LARM, { at: [-SHOULDER_X, 1.005, 0], color: sleeve });
  if (puffer) {
    pair(tube(0.062, 0.062, 0.012, 6), B.L_UARM, B.R_UARM, { at: [-SHOULDER_X, 1.28, 0], color: COLOR.black });
    pair(tube(0.058, 0.058, 0.012, 6), B.L_LARM, B.R_LARM, { at: [-SHOULDER_X, 1.02, 0], color: COLOR.black });
  }
  if (track) {
    pair(box(0.012, 0.25, 0.028), B.L_UARM, B.R_UARM, { at: [-SHOULDER_X - 0.064, 1.28, 0], rot: [0, 0, -0.04], color: COLOR.oxblood, glow: GLOW.accent });
    pair(box(0.012, 0.23, 0.026), B.L_LARM, B.R_LARM, { at: [-SHOULDER_X - 0.051, 1.005, 0], rot: [0, 0, -0.04], color: COLOR.oxblood, glow: GLOW.accent });
  }
  pair(tube(0.05, 0.047, 0.04, 6), B.L_LARM, B.R_LARM, { at: [-SHOULDER_X, 0.885, 0], color: hoodie ? COLOR.oxbloodDark : COLOR.black, glow: hoodie ? GLOW.accent * 0.5 : 0 }); // cuff
  pair(box(0.075, 0.105, 0.05), B.L_HAND, B.R_HAND, { at: [-SHOULDER_X, 0.815, -0.004], color: COLOR.glove });
  pair(box(0.03, 0.05, 0.035), B.L_HAND, B.R_HAND, { at: [-SHOULDER_X + 0.045, 0.835, -0.02], color: COLOR.glove }); // thumb

  // ---- head ----------------------------------------------------------------------------------------
  const hy = 1.5 + HEAD.centreY;
  const face = [0.098, 0.122, 0.108]; // the mask: half extents of the head ellipsoid
  m.add(ball(1, 1), { bone: B.HEAD, at: [0, hy, -0.004], scale: face, color: COLOR.mask, glow: GLOW.mask });
  // Eye holes: two narrow, slanted slits.
  for (const side of [-1, 1]) {
    m.add(box(0.046, 0.017, 0.02), { bone: B.HEAD, at: [side * 0.041, hy + 0.022, -0.097], rot: [0, side * -0.32, side * -0.2], color: COLOR.eye });
  }
  if (hoodie) {
    // Hood: a dark shell set back so only the face of the mask shows.
    m.add(ball(1, 1), { bone: B.HEAD, at: [0, hy + 0.012, 0.04], scale: [0.135, 0.15, 0.125], color: COLOR.black });
    m.add(tube(0.5, 0.56, 0.1, 8), { bone: B.HEAD, at: [0, hy - 0.115, 0.03], scale: [0.25, 1, 0.26], color: COLOR.black }); // hood gathered on the shoulders
    m.add(box(0.012, 0.05, 0.02), { bone: B.HEAD, at: [0, hy - 0.058, -0.105], color: COLOR.maskShade, glow: GLOW.mask }); // mouth seam
  } else if (puffer) {
    // Beanie, dark glasses, pale bandana over the lower face.
    m.add(ball(1, 1), { bone: B.HEAD, at: [0, hy + 0.045, 0.006], scale: [0.106, 0.1, 0.116], color: COLOR.black });
    m.add(tube(0.5, 0.5, 0.035, 8), { bone: B.HEAD, at: [0, hy + 0.04, 0.004], scale: [0.218, 1, 0.236], color: COLOR.oxblood, glow: GLOW.accent }); // beanie cuff
    m.add(box(0.19, 0.036, 0.06), { bone: B.HEAD, at: [0, hy + 0.012, -0.09], color: COLOR.eye }); // glasses
    m.add(tube(0.5, 0.02, 0.11, 4), { bone: B.HEAD, at: [0, hy - 0.125, -0.075], rot: [0.3, 0, 0], scale: [0.2, 1, 0.07], color: COLOR.mask, glow: GLOW.mask }); // bandana point
  } else {
    // Fitted cap worn backwards over a full ski mask.
    m.add(ball(1, 1), { bone: B.HEAD, at: [0, hy + 0.05, 0.004], scale: [0.105, 0.085, 0.114], color: COLOR.black });
    m.add(box(0.15, 0.012, 0.09), { bone: B.HEAD, at: [0, hy + 0.058, 0.125], rot: [-0.25, 0, 0], color: COLOR.oxblood, glow: GLOW.accent }); // brim, to the back
    m.add(box(0.012, 0.05, 0.02), { bone: B.HEAD, at: [0, hy - 0.058, -0.105], color: COLOR.maskShade, glow: GLOW.mask });
    m.add(tube(0.5, 0.5, 0.07, 8), { bone: B.HEAD, at: [0, hy - 0.1, 0.004], scale: [0.16, 1, 0.17], color: COLOR.maskShade, glow: GLOW.mask * 0.6 }); // mask tucked into the collar
  }

  // ---- the SMG (own frame) -------------------------------------------------------------------------
  const g = B.GUN;
  m.add(box(0.046, 0.072, 0.27), { bone: g, at: [0, 0.036, -0.055], color: COLOR.gun }); // receiver
  m.add(box(0.036, 0.046, 0.15), { bone: g, at: [0, 0.04, -0.262], color: COLOR.gunLight }); // handguard
  m.add(tube(0.012, 0.012, 0.06, 6), { bone: g, at: [0, 0.042, -0.356], rot: [Math.PI / 2, 0, 0], color: COLOR.gun }); // muzzle
  m.add(box(0.036, 0.1, 0.046), { bone: g, at: [0, -0.046, 0.016], rot: [0.26, 0, 0], color: COLOR.gun }); // grip
  m.add(box(0.03, 0.17, 0.042), { bone: g, at: [0, -0.09, -0.085], rot: [-0.1, 0, 0], color: COLOR.gunLight }); // magazine
  m.add(box(0.03, 0.05, 0.19), { bone: g, at: [0, 0.03, 0.15], color: COLOR.gun }); // stock
  m.add(box(0.034, 0.085, 0.02), { bone: g, at: [0, 0.018, 0.243], color: COLOR.gun }); // butt plate
  m.add(box(0.016, 0.02, 0.07), { bone: g, at: [0, 0.082, -0.05], color: COLOR.gunLight }); // sight rail
  m.add(tube(0.018, 0.018, 0.075, 6), { bone: g, at: [0, -0.002, -0.278], rot: [Math.PI / 2, 0, 0], color: COLOR.gun }); // weapon light
  m.add(tube(0.016, 0.016, 0.006, 6), { bone: g, at: [0, -0.002, -0.3185], rot: [Math.PI / 2, 0, 0], color: COLOR.lens, lamp: true }); // its lens

  // ---- the pipe (own frame) ------------------------------------------------------------------------
  m.add(tube(0.017, 0.017, 0.7, 6), { bone: B.PIPE, at: [0, 0.21, 0], color: COLOR.pipe, glow: GLOW.pipe });
  m.add(tube(0.025, 0.025, 0.05, 6), { bone: B.PIPE, at: [0, 0.545, 0], color: COLOR.pipe, glow: GLOW.pipe }); // coupling at the business end
  m.add(tube(0.02, 0.02, 0.15, 6), { bone: B.PIPE, at: [0, -0.04, 0], color: COLOR.tape }); // taped grip

  // Every pose, including a body lying 1.8 m long next to where he stood.
  return m.build([0, 0.9, 0], 2.4);
}

export function createGoonMaterial() {
  return createEnemyMaterial({ name: 'goon', roughness: 0.78, metalness: 0, rim: 0x9db8ff, rimStrength: 0.55, rimPower: 2.4 });
}

/** Lamp colour of the weapon light (linear, multiplied by the brightness the pose code sets). */
export const GOON_LAMP = new THREE.Color(1, 0.74, 0.42);
