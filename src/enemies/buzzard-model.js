// The Buzzard: the Vultures' armed quadcopter. About a metre across, a hooked nose, a V tail, four
// rotors on swept arms, and a gimbal under the nose that carries the red eye and the gun.
// One rigid-skinned geometry: the airframe, four rotor bones and the gimbal bone.
//
// Model space: centre of the airframe at the origin, nose toward −Z, +X to its right.

import * as THREE from 'three';
import { damp } from '../core/util.js';
import { createEnemyMaterial, createModelBuilder, m3Euler, P_FADE, P_FLASH, P_LAMP, P_LAMP_R, P_RIM, writeBone } from './rig.js';

export const BZ = { BODY: 1, ROTOR: 2, GIMBAL: 6 }; // rotors: front left, front right, rear left, rear right
export const BZ_SLOTS = 7;

/** Rotor hubs (model space) and the radius of the discs. */
export const ROTORS = [
  [-0.33, 0.075, -0.27],
  [0.33, 0.075, -0.27],
  [-0.35, 0.075, 0.3],
  [0.35, 0.075, 0.3],
];
export const ROTOR_RADIUS = 0.185;

const GIMBAL_PIVOT = [0, -0.085, -0.17];
/** Points on the gimbal, relative to its pivot: the eye lens and the gun muzzle. */
export const EYE = [0, -0.015, -0.085];
export const MUZZLE = [0.062, -0.045, -0.2];
/** Nav strobes (model space): port red, starboard green, tail white. */
export const STROBES = [
  [-0.36, 0.02, -0.33],
  [0.36, 0.02, -0.33],
  [0, 0.09, 0.47],
];

const COLOR = {
  hull: 0x1c1e24,
  hullLight: 0x2b2e36,
  panel: 0x7c151d,
  prop: 0x30333a,
  lens: 0x2a0806,
  gun: 0x17181c,
  skid: 0x22242a,
};

const box = (w, h, d) => new THREE.BoxGeometry(w, h, d);
const tube = (rTop, rBottom, h, sides = 6) => new THREE.CylinderGeometry(rTop, rBottom, h, sides, 1);
const ball = (r, detail = 1) => new THREE.IcosahedronGeometry(r, detail);

export function buildBuzzardGeometry() {
  const m = createModelBuilder();
  const body = BZ.BODY;

  // Fuselage: a flat faceted hull, a raised spine in crew colours, a hooked nose.
  m.add(tube(0.5, 0.42, 0.11, 8), { bone: body, at: [0, 0, 0.02], scale: [0.3, 1, 0.56], color: COLOR.hull });
  m.add(tube(0.3, 0.5, 0.06, 8), { bone: body, at: [0, 0.082, 0.04], scale: [0.26, 1, 0.5], color: COLOR.hullLight });
  m.add(box(0.07, 0.022, 0.34), { bone: body, at: [0, 0.118, 0.05], color: COLOR.panel, glow: 0.3 });
  m.add(tube(0.02, 0.5, 0.24, 4), { bone: body, at: [0, -0.012, -0.36], rot: [-Math.PI / 2 - 0.2, 0, 0], scale: [0.2, 1, 0.1], color: COLOR.hull }); // beak
  m.add(box(0.12, 0.012, 0.1), { bone: body, at: [0, 0.052, -0.3], rot: [0.3, 0, 0], color: COLOR.panel, glow: 0.3 }); // brow
  // Tail boom and V tail.
  m.add(box(0.05, 0.04, 0.26), { bone: body, at: [0, 0.01, 0.4], color: COLOR.hull });
  for (const side of [-1, 1]) {
    m.add(box(0.012, 0.15, 0.11), { bone: body, at: [side * 0.055, 0.075, 0.47], rot: [-0.3, 0, side * -0.6], color: COLOR.panel, glow: 0.3 });
  }
  // Arms, motor pods, landing skids.
  for (let i = 0; i < 4; i++) {
    const [x, y, z] = ROTORS[i];
    const len = Math.hypot(x, z);
    m.add(box(0.045, 0.03, len), { bone: body, at: [x / 2, 0.012, z / 2], rot: [0, Math.atan2(x, z), 0], color: COLOR.hullLight });
    m.add(tube(0.042, 0.05, 0.085, 6), { bone: body, at: [x, y - 0.045, z], color: COLOR.hull });
    // The rotor itself: hub and two blades, on its own bone.
    const rotor = BZ.ROTOR + i;
    m.add(tube(0.018, 0.022, 0.03, 6), { bone: rotor, at: [x, y + 0.008, z], color: COLOR.prop });
    m.add(box(ROTOR_RADIUS * 2, 0.006, 0.034), { bone: rotor, at: [x, y + 0.018, z], rot: [0.12, 0, 0], color: COLOR.prop });
  }
  for (const side of [-1, 1]) {
    m.add(box(0.018, 0.018, 0.4), { bone: body, at: [side * 0.13, -0.16, 0.03], color: COLOR.skid });
    for (const z of [-0.1, 0.16]) m.add(box(0.014, 0.11, 0.014), { bone: body, at: [side * 0.115, -0.105, z], rot: [0, 0, side * 0.27], color: COLOR.skid });
  }

  // Gimbal: the eye in its housing and the slung gun.
  const g = BZ.GIMBAL;
  const [gx, gy, gz] = GIMBAL_PIVOT;
  m.add(ball(0.062, 1), { bone: g, at: [gx, gy - 0.015, gz - 0.02], color: COLOR.gun });
  m.add(tube(0.036, 0.036, 0.012, 8), { bone: g, at: [gx + EYE[0], gy + EYE[1], gz + EYE[2] + 0.004], rot: [Math.PI / 2, 0, 0], color: COLOR.lens, lamp: true });
  m.add(tube(0.045, 0.045, 0.02, 8), { bone: g, at: [gx, gy - 0.015, gz - 0.068], rot: [Math.PI / 2, 0, 0], color: COLOR.hullLight }); // lens ring
  m.add(box(0.03, 0.034, 0.2), { bone: g, at: [gx + MUZZLE[0], gy + MUZZLE[1], gz - 0.09], color: COLOR.gun }); // gun
  m.add(tube(0.01, 0.01, 0.06, 6), { bone: g, at: [gx + MUZZLE[0], gy + MUZZLE[1], gz + MUZZLE[2] + 0.03], rot: [Math.PI / 2, 0, 0], color: COLOR.prop });
  m.add(box(0.05, 0.045, 0.07), { bone: g, at: [gx + 0.055, gy - 0.085, gz - 0.02], color: COLOR.hullLight }); // ammo box
  m.add(tube(0.02, 0.026, 0.04, 6), { bone: body, at: [gx, gy + 0.04, gz], color: COLOR.hull }); // gimbal neck

  return m.build([0, 0, 0], 0.75);
}

export function createBuzzardMaterial() {
  return createEnemyMaterial({ name: 'buzzard', roughness: 0.5, metalness: 0.45, rim: 0xa8bcff, rimStrength: 0.5, rimPower: 2.2 });
}

/** Colour of the eye (linear, multiplied by the lamp brightness). */
export const BUZZARD_LAMP = new THREE.Color(1, 0.09, 0.05);

/** Per-Buzzard animation state. */
export function createBuzzardAnim() {
  return {
    spin: 0.001, // rotor angle
    rotorSpeed: 0.5, // 0…1
    eyeYaw: 0.001,
    eyePitch: 0.001,
    lamp: 0.001,
    flash: 0.001,
    lost: -1, // index of the rotor that came off, -1 = none
    out: new Float64Array(6), // model-space eye and muzzle
  };
}

export const OUT_EYE = 0;
export const OUT_BOLT = 3;

export function resetBuzzardAnim(a, seed) {
  a.spin = seed * 1.7;
  a.rotorSpeed = 1;
  a.eyeYaw = a.eyePitch = 0;
  a.lamp = a.flash = 0;
  a.lost = -1;
}

const R = new Float64Array(9 * 2);
const J = new Float64Array(3);
const ORIGIN = new Float64Array(3);
const BLADE_RATE = 41; // rad/s at full power: slow enough to read as blades under the blur disc

/**
 * Writes the pose: spinning rotors, the gimbal turned toward (eyeYawWant, eyePitchWant) relative to
 * the airframe, shader parameters. The airframe's own attitude is the mesh's rotation.
 * @param e {rotorWant 0…1, eyeYawWant, eyePitchWant, lampWant}
 */
export function poseBuzzard(e, a, dt, M) {
  a.rotorSpeed = damp(a.rotorSpeed, e.rotorWant, e.rotorWant < a.rotorSpeed ? 1.6 : 6, dt);
  a.spin = (a.spin + BLADE_RATE * a.rotorSpeed * dt) % (Math.PI * 2);
  a.eyeYaw = damp(a.eyeYaw, Math.max(-1.5, Math.min(1.5, e.eyeYawWant)), 14, dt);
  a.eyePitch = damp(a.eyePitch, Math.max(-1.35, Math.min(0.5, e.eyePitchWant)), 14, dt);
  a.lamp = damp(a.lamp, e.lampWant, e.lampWant > a.lamp ? 30 : 10, dt);
  a.flash = Math.max(0, a.flash - 7 * dt);

  m3Euler(R, 0, 0, 0, 0);
  writeBone(M, BZ.BODY, R, 0, ORIGIN, 0, 0, 0, 0);
  for (let i = 0; i < 4; i++) {
    const hub = ROTORS[i];
    // Neighbouring rotors turn opposite ways.
    m3Euler(R, 0, 0, (i === 0 || i === 3 ? 1 : -1) * a.spin + i * 0.9, 0);
    J[0] = hub[0];
    J[1] = hub[1];
    J[2] = hub[2];
    writeBone(M, BZ.ROTOR + i, R, 0, J, 0, hub[0], hub[1], hub[2], a.lost === i ? 0.001 : 1);
  }
  m3Euler(R, 9, a.eyePitch, a.eyeYaw, 0);
  J[0] = GIMBAL_PIVOT[0];
  J[1] = GIMBAL_PIVOT[1];
  J[2] = GIMBAL_PIVOT[2];
  writeBone(M, BZ.GIMBAL, R, 9, J, 0, GIMBAL_PIVOT[0], GIMBAL_PIVOT[1], GIMBAL_PIVOT[2]);

  M[P_FLASH] = a.flash;
  M[P_FADE] = 0;
  M[P_LAMP] = a.lamp;
  M[P_RIM] = 1;
  M[P_LAMP_R] = BUZZARD_LAMP.r;
  M[P_LAMP_R + 1] = BUZZARD_LAMP.g;
  M[P_LAMP_R + 2] = BUZZARD_LAMP.b;

  // Eye and muzzle in model space (gimbal pivot + its rotation · offset).
  const out = a.out;
  for (let k = 0; k < 2; k++) {
    const p = k === 0 ? EYE : MUZZLE;
    const o = k * 3;
    out[o] = GIMBAL_PIVOT[0] + R[9] * p[0] + R[10] * p[1] + R[11] * p[2];
    out[o + 1] = GIMBAL_PIVOT[1] + R[12] * p[0] + R[13] * p[1] + R[14] * p[2];
    out[o + 2] = GIMBAL_PIVOT[2] + R[15] * p[0] + R[16] * p[1] + R[17] * p[2];
  }
}
