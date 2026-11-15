// Procedural animation of the Goon. No clips: every frame the pose is solved from what the AI wants
// (speed, crouch, aim direction, rush phase, telegraph) and written as bone matrices.
//
//   legs    foot targets from a heel-to-toe gait cycle (or a standing / shooting / kneeling stance),
//           solved with two-bone reach, so crouching and stepping never slide through the ground
//   arms    both hands hold the SMG, which blends between low ready, port arms, shouldered aim and a
//           one-hand carry; during the rush the right hand draws the pipe from his back and swings it
//   body    lean, gait bob and counter-twist, recoil and hit-flinch springs, head tracking
//   death   a short collapse in the direction of the killing shot: knees give, the body topples
//           and twists onto its back or its front, limbs settle, the gun drops beside him
//
// Model space: feet at the origin, facing −Z, +X to his right (the mesh adds position and yaw).

import { clamp, clamp01, damp, lerp, moveToward, smoothstep } from '../core/util.js';
import { B, GOON_LAMP, GUN, HEAD, LIMB, PIVOT, SLOTS } from './goon-model.js';
import { m3Copy, m3Euler, m3Limb, m3Mul, m3Point, P_FADE, P_FLASH, P_LAMP, P_LAMP_R, P_RIM, solveLimb, writeBone } from './rig.js';

const TAU = Math.PI * 2;
const PI = Math.PI;

// Scratch (the pose of one Goon at a time).
const R = new Float64Array(SLOTS * 9); // model-space rotation of every bone
const J = new Float64Array(SLOTS * 3); // model-space position of every bone's joint
const T = new Float64Array(9 * 8); // temporary rotations
const V = new Float64Array(48); // temporary vectors
const F = new Float64Array(6); // foot cycle: z, y, pitch for the left and the right foot
const IK = new Float64Array(9);
const ZERO = new Float64Array(3);

const HIPS9 = B.HIPS * 9;
const SPINE9 = B.SPINE * 9;
const HEAD9 = B.HEAD * 9;
const GUN9 = B.GUN * 9;
const PIPE9 = B.PIPE * 9;
const HIPS3 = B.HIPS * 3;
const SPINE3 = B.SPINE * 3;
const HEAD3 = B.HEAD * 3;
const GUN3 = B.GUN * 3;
const PIPE3 = B.PIPE * 3;

const HIP_Y = PIVOT[HIPS3 + 1];
const CHEST_Y = PIVOT[B.R_UARM * 3 + 1] - PIVOT[SPINE3 + 1]; // shoulder line above the waist joint
const HIP_X = PIVOT[B.R_ULEG * 3];
const HIP_DROP = PIVOT[B.R_ULEG * 3 + 1] - HIP_Y;
const ANKLE = LIMB.ankle;
const HEEL = 0.07; // heel behind the ankle
const BALL = 0.13; // ball of the foot ahead of it

// Stances: ankle targets [x, y, z, pitch] for the left and the right foot, hips [y drop, z], pelvis yaw.
const STANCE_IDLE = { l: [-0.115, ANKLE, -0.03, 0], r: [0.115, ANKLE, 0.03, 0] };
const STANCE_AIM = { l: [-0.13, ANKLE, -0.17, 0], r: [0.14, ANKLE, 0.15, 0] };
const STANCE_KNEEL = { l: [-0.14, ANKLE, -0.2, 0], r: [0.13, 0.13, 0.3, -1.15] };
const KNEEL_DROP = 0.45;
const CROUCH_WALK_DROP = 0.22;
const BLADED = -0.32; // pelvis yaw of the shooting stance: left shoulder leads

// Gun holds: grip position relative to the chest centre, and Euler angles (pitch, yaw, roll).
const HOLD_LOW = { at: [0.1, -0.27, -0.21], rot: [-0.75, 0.55, 0.25] };
const HOLD_PORT = { at: [0.12, -0.2, -0.2], rot: [0.55, 0.75, -0.2] };
const HOLD_CARRY = { at: [-0.04, -0.33, -0.17], rot: [-1.0, 0.9, 0.3] };
const HOLD_AIM = [0.125, -0.042, -0.305]; // in the aim frame: the butt sits in the right shoulder
const WRIST_R = [0, 0.005, 0.065]; // right wrist in the gun's frame…
const WRIST_L = [GUN.fore[0], GUN.fore[1] - 0.03, GUN.fore[2] + 0.05]; // …and the left one
const HAND_R_PITCH = 0.86;
const HAND_L_PITCH = 2.1;

// The pipe: where it rides on his back, and the right hand's path through the swing (chest frame).
const PIPE_BACK = { at: [0.15, 0.06, 0.15], rot: [0.12, 0, 2.62] };
const HAND_BACK = [0.15, 0.06, 0.15];
const HAND_COCKED = [0.3, 0.2, 0.1];
const HAND_STRIKE = [-0.1, -0.22, -0.42];
const PIPE_COCKED = 0.5; // pitch of the pipe: up and back…
const PIPE_STRUCK = -1.9; // …to forward and down
const SWING_TIME = 0.14;
const UNSWING_TIME = 0.25;

const RECOIL = { stiffness: 520, damping: 30, kick: 24 };
const FLINCH = { stiffness: 150, damping: 13, kick: 5.2 };

/** Per-Goon animation state. Everything is a plain number so it is updated in place. */
export function createGoonAnim() {
  return {
    phase: 0.01,
    moveW: 0.001,
    runW: 0.001,
    crouch: 0.001,
    aim: 0.001,
    rush: 0.001,
    gunYaw: 0.001,
    gunPitch: 0.001,
    headYaw: 0.001,
    headPitch: 0.001,
    recoil: 0.001,
    recoilV: 0.001,
    flinchX: 0.001,
    flinchZ: 0.001,
    flinchVX: 0.001,
    flinchVZ: 0.001,
    idle: 0.5,
    lamp: 0.001,
    flash: 0.001,
    fade: 0.001,
    strike: 0.001, // 0…1 through the pipe swing
    carry: 0.001, // pipe in the fist (1) or on the back (0)
    swing: -1, // 0 once the AI has called for the blow, -1 otherwise
    step: 0, // 1 / 2 on the frame the left / right foot lands
    // The pose as last solved, kept for the collapse.
    pelvisX: 0.001,
    pelvisY: 0.001,
    pelvisZ: 0.001,
    spineX: 0.001,
    spineY: 0.001,
    spineZ: 0.001,
    headX: 0.001,
    headY: 0.001,
    // Death.
    dead: false,
    settled: false,
    deathT: 0.001,
    fallYaw: 0.001,
    prone: false,
    flip: 1,
    cap: new Float64Array(72),
    // Model-space points the game reads back (see OUT_*).
    out: new Float64Array(21),
  };
}

export const OUT_HEAD = 0;
export const OUT_MUZZLE = 3;
export const OUT_LAMP = 6;
export const OUT_AIM = 9; // unit vector along the barrel
export const OUT_BODY_LOW = 12;
export const OUT_BODY_HIGH = 15;
export const OUT_CHEST = 18;

export function resetGoonAnim(a, seed) {
  a.phase = (seed * 0.37) % 1;
  a.moveW = a.runW = a.crouch = a.aim = a.rush = 0;
  a.gunYaw = a.gunPitch = a.headYaw = a.headPitch = 0;
  a.recoil = a.recoilV = a.flinchX = a.flinchZ = a.flinchVX = a.flinchVZ = 0;
  a.idle = seed * 7.13;
  a.lamp = a.flash = a.fade = 0;
  a.strike = a.carry = 0;
  a.swing = -1;
  a.step = 0;
  a.dead = a.settled = false;
  a.deathT = 0;
  a.flip = seed % 2 ? 1 : -1;
}

/** A shot was fired: kick the gun. */
export function kickRecoil(a) {
  a.recoilV += RECOIL.kick;
}

/** A hit landed: shove the body along (dx, dz) in model space, `strength` about 0…1.6. */
export function kickFlinch(a, dx, dz, strength) {
  a.flinchVX += dx * strength * FLINCH.kick;
  a.flinchVZ += dz * strength * FLINCH.kick;
  a.flash = Math.min(1, a.flash + 0.55 + 0.25 * strength);
}

/** Position of one foot in the gait cycle: writes ankle z, ankle y and foot pitch to F[o…o+2]. */
function footCycle(p, stance, front, back, lift, roll, o) {
  const strikePitch = 0.32 * roll;
  const offPitch = -0.9 * roll;
  // Ankle when the heel lands in front, and when the toe leaves behind.
  const strikeZ = -front + HEEL + ANKLE * Math.sin(strikePitch) - HEEL * Math.cos(strikePitch);
  const strikeY = ANKLE * Math.cos(strikePitch) + HEEL * Math.sin(strikePitch);
  const offZ = back - BALL + ANKLE * Math.sin(offPitch) + BALL * Math.cos(offPitch);
  const offY = ANKLE * Math.cos(offPitch) - BALL * Math.sin(offPitch);
  if (p < stance) {
    // On the ground, travelling back under the body: roll in over the heel, out over the ball.
    const u = p / stance;
    const contact = -front + (front + back) * u;
    if (u < 0.2) {
      const pitch = strikePitch * (1 - u / 0.2);
      F[o] = contact + HEEL + ANKLE * Math.sin(pitch) - HEEL * Math.cos(pitch);
      F[o + 1] = ANKLE * Math.cos(pitch) + HEEL * Math.sin(pitch);
      F[o + 2] = pitch;
    } else if (u > 0.55) {
      const k = (u - 0.55) / 0.45;
      const pitch = offPitch * k * k;
      F[o] = contact - BALL + ANKLE * Math.sin(pitch) + BALL * Math.cos(pitch);
      F[o + 1] = ANKLE * Math.cos(pitch) - BALL * Math.sin(pitch);
      F[o + 2] = pitch;
    } else {
      F[o] = contact;
      F[o + 1] = ANKLE;
      F[o + 2] = 0;
    }
    return;
  }
  // In the air, swinging forward.
  const v = (p - stance) / (1 - stance);
  const s = v * v * (3 - 2 * v);
  F[o] = offZ + (strikeZ - offZ) * s;
  F[o + 1] = offY + (strikeY - offY) * s + lift * Math.sin(PI * v);
  F[o + 2] = offPitch + (strikePitch - offPitch) * s;
}

/** J[child] = J[parent] + R[parent] · (bind offset between the two joints). */
function placeJoint(child, parent) {
  const c = child * 3;
  const p = parent * 3;
  m3Point(R, parent * 9, PIVOT[c] - PIVOT[p], PIVOT[c + 1] - PIVOT[p + 1], PIVOT[c + 2] - PIVOT[p + 2], J, p, J, c);
}

/**
 * Solves one arm or leg from joint `upper` to the target in V[t…], writes both bone rotations and the
 * joints of `lower` and `end`. `side` is +1 for a limb whose bend points at the pole like a knee (the
 * hinge is reach × pole), −1 for one that bends away from it like an elbow.
 */
function reach(upper, lower, end, t, l1, l2, px, py, pz, side) {
  const u3 = upper * 3;
  solveLimb(J, u3, V[t], V[t + 1], V[t + 2], l1, l2, px, py, pz, IK);
  // Hinge axis from the plane the limb bends in.
  const dx = V[t] - J[u3];
  const dy = V[t + 1] - J[u3 + 1];
  const dz = V[t + 2] - J[u3 + 2];
  const hx = (dy * pz - dz * py) * side;
  const hy = (dz * px - dx * pz) * side;
  const hz = (dx * py - dy * px) * side;
  m3Limb(R, upper * 9, IK[0], IK[1], IK[2], hx, hy, hz);
  m3Limb(R, lower * 9, IK[3], IK[4], IK[5], hx, hy, hz);
  const l3 = lower * 3;
  J[l3] = IK[6];
  J[l3 + 1] = IK[7];
  J[l3 + 2] = IK[8];
  const e3 = end * 3;
  J[e3] = IK[6] + IK[3] * l2;
  J[e3 + 1] = IK[7] + IK[4] * l2;
  J[e3 + 2] = IK[8] + IK[5] * l2;
}

/** Adds weight w of rotation T[t…] (columns X and Y) and of the point p to the blend in V[24…35]. */
function blendHold(w, t, px, py, pz) {
  if (w <= 0) return;
  V[24] += T[t] * w;
  V[25] += T[t + 3] * w;
  V[26] += T[t + 6] * w;
  V[27] += T[t + 1] * w;
  V[28] += T[t + 4] * w;
  V[29] += T[t + 7] * w;
  V[30] += px * w;
  V[31] += py * w;
  V[32] += pz * w;
}

/** Rotation T[t…] = R[SPINE] · Euler(hold.rot) and its grip point relative to the chest, blended in with weight w. */
function addHold(w, hold, t) {
  if (w <= 0) return;
  m3Euler(T, 63, hold.rot[0], hold.rot[1], hold.rot[2]);
  m3Mul(T, t, R, SPINE9, T, 63);
  m3Point(R, SPINE9, hold.at[0], hold.at[1], hold.at[2], V, 21, V, 36);
  blendHold(w, t, V[36], V[37], V[38]);
}

function writeAll(M) {
  for (let b = B.HIPS; b <= B.R_FOOT; b++) writeBone(M, b, R, b * 9, J, b * 3, PIVOT[b * 3], PIVOT[b * 3 + 1], PIVOT[b * 3 + 2]);
  writeBone(M, B.GUN, R, GUN9, J, GUN3, 0, 0, 0);
  writeBone(M, B.PIPE, R, PIPE9, J, PIPE3, 0, 0, 0);
}

function writeParams(a, M) {
  M[P_FLASH] = a.flash;
  M[P_FADE] = a.fade;
  M[P_LAMP] = a.lamp;
  M[P_RIM] = 1;
  M[P_LAMP_R] = GOON_LAMP.r;
  M[P_LAMP_R + 1] = GOON_LAMP.g;
  M[P_LAMP_R + 2] = GOON_LAMP.b;
}

/**
 * Solves and writes the pose of a living Goon.
 *
 * @param e  what the AI wants: {speed, yawRate, wantCrouch, wantAim, aimYawRel, aimPitch, lookYawRel,
 *           lookPitch, rushPhase (0 none, 1 wind-up, 2 dash, 3 recovery), rushK (0…1 through the phase),
 *           lampWant}
 * @param a  createGoonAnim() state
 * @param M  the rig's matrix array
 */
export function poseGoon(e, a, dt, M) {
  const speed = e.speed;
  a.moveW = damp(a.moveW, smoothstep(0.15, 0.9, speed), 12, dt);
  a.runW = damp(a.runW, smoothstep(2.4, 4, speed), 8, dt);
  a.crouch = damp(a.crouch, e.wantCrouch, 8, dt);
  a.aim = damp(a.aim, e.wantAim, 11, dt);
  const moveW = a.moveW;
  const runW = a.runW;
  const crouch = a.crouch;
  const still = 1 - moveW;

  // ---- springs --------------------------------------------------------------------------------
  a.recoilV += (-RECOIL.stiffness * a.recoil - RECOIL.damping * a.recoilV) * dt;
  a.recoil += a.recoilV * dt;
  a.flinchVX += (-FLINCH.stiffness * a.flinchX - FLINCH.damping * a.flinchVX) * dt;
  a.flinchVZ += (-FLINCH.stiffness * a.flinchZ - FLINCH.damping * a.flinchVZ) * dt;
  a.flinchX = clamp(a.flinchX + a.flinchVX * dt, -0.6, 0.6);
  a.flinchZ = clamp(a.flinchZ + a.flinchVZ * dt, -0.6, 0.6);
  a.flash = Math.max(0, a.flash - 7 * dt);
  a.lamp = damp(a.lamp, e.lampWant, e.lampWant > a.lamp ? 30 : 9, dt);
  a.idle += dt;
  const breathe = Math.sin(a.idle * 1.7);
  const sway = Math.sin(a.idle * 0.61);

  // ---- the rush timeline ------------------------------------------------------------------------
  // Wind-up: the right hand leaves the gun for the pipe on his back (reach), draws it and raises it
  // (cock). Dash: the blow, when the AI calls for it. Recovery: the pipe goes back, the hand returns.
  let rushWant = 0;
  let cock = 0;
  let strikeWant = 0;
  let stow = 0;
  let carried = 0;
  if (e.rushPhase === 1) {
    rushWant = smoothstep(0, 0.4, e.rushK);
    cock = smoothstep(0.4, 1, e.rushK);
    carried = cock > 0 ? 1 : 0;
  } else if (e.rushPhase === 2) {
    rushWant = cock = carried = 1;
    strikeWant = a.swing >= 0 ? 1 : 0;
  } else if (e.rushPhase === 3) {
    cock = strikeWant = 1;
    stow = smoothstep(0.25, 0.7, e.rushK);
    rushWant = 1 - smoothstep(0.72, 1, e.rushK);
    carried = stow < 1 ? 1 : 0;
  }
  if (e.rushPhase !== 2) a.swing = -1;
  a.rush = damp(a.rush, rushWant, 20, dt);
  a.strike = moveToward(a.strike, strikeWant, dt / (strikeWant > a.strike ? SWING_TIME : UNSWING_TIME));
  a.carry = damp(a.carry, carried, 30, dt);
  const rw = a.rush; // weight of the rush hand target over the gun grip
  const strike = a.strike * a.strike * (3 - 2 * a.strike);
  const inHand = cock * (1 - stow); // how far the pipe has turned from its strap to the fist
  const aim = a.aim * (1 - rw);

  // ---- gait -------------------------------------------------------------------------------------
  const stride = (0.75 + 0.39 * Math.min(speed, 10)) * (1 - 0.3 * crouch);
  const turnRate = Math.min(Math.abs(e.yawRate), 3);
  const before = a.phase;
  let phase = before + dt * (speed / stride + still * turnRate * 0.22);
  a.step = 0;
  if (phase >= 1) {
    phase -= Math.floor(phase);
    if (moveW > 0.5) a.step = 1;
  } else if (before < 0.5 && phase >= 0.5 && moveW > 0.5) {
    a.step = 2;
  }
  a.phase = phase;

  const stance = lerp(0.62, 0.36, runW);
  const travel = stride * stance * moveW * 0.94;
  const front = Math.min(travel * 0.5, lerp(0.34, 0.3, runW));
  const lift = (0.07 + 0.2 * runW) * moveW + still * Math.min(turnRate, 2) * 0.025;
  const roll = clamp01(travel / 0.6);
  footCycle(phase, stance, front, travel - front, lift, roll, 0);
  footCycle(phase >= 0.5 ? phase - 0.5 : phase + 0.5, stance, front, travel - front, lift, roll, 3);

  // ---- hips -------------------------------------------------------------------------------------
  const kneel = crouch * still;
  const cyc = Math.cos(TAU * phase);
  const syc = Math.sin(TAU * phase);
  const pelvisYaw = -0.15 * cyc * moveW * (1 - 0.3 * runW) + BLADED * Math.max(aim, kneel) * still;
  const pelvisPitch = -0.05 * runW - 0.1 * kneel - 0.12 * strike * rw;
  const pelvisRoll = 0.04 * syc * moveW;
  m3Euler(R, HIPS9, pelvisPitch, pelvisYaw, pelvisRoll);
  J[HIPS3] = -0.016 * syc * moveW * (1 - runW) + a.flinchX * 0.05 + 0.006 * sway * still;
  J[HIPS3 + 1] =
    HIP_Y -
    0.012 -
    0.03 * moveW -
    0.05 * runW -
    0.035 * aim * still -
    crouch * lerp(KNEEL_DROP, CROUCH_WALK_DROP, moveW) -
    0.07 * cock * rw * (1 - strike * 0.5) +
    moveW * ((1 - runW) * -0.02 * Math.cos(2 * TAU * phase) + runW * 0.03 * Math.sin(2 * TAU * phase + 0.8)) +
    0.003 * breathe;
  J[HIPS3 + 2] = 0.04 * kneel + a.flinchZ * 0.05 - 0.03 * runW;

  // ---- spine and head ---------------------------------------------------------------------------
  a.gunYaw = damp(a.gunYaw, clamp(e.aimYawRel, -1.1, 1.1) * e.wantAim, 12, dt);
  a.gunPitch = damp(a.gunPitch, clamp(e.aimPitch, -0.7, 0.7) * e.wantAim, 12, dt);
  const rushTwist = rw * lerp(-0.45 * cock, 0.5, strike);
  const spineYawModel = a.gunYaw * 0.6 - 0.22 * aim * still + 0.5 * 0.15 * cyc * moveW + rushTwist;
  const spineX =
    -(0.03 + 0.05 * moveW + 0.2 * runW + 0.26 * crouch + 0.07 * aim) -
    0.4 * strike * rw +
    0.1 * cock * rw * (1 - strike) +
    0.05 * a.recoil +
    a.flinchZ * 0.55 +
    0.008 * breathe -
    pelvisPitch;
  const spineY = spineYawModel - pelvisYaw;
  const spineZ = -a.flinchX * 0.55 - pelvisRoll * 0.8;
  m3Euler(T, 0, spineX, spineY, spineZ);
  m3Mul(R, SPINE9, R, HIPS9, T, 0);
  placeJoint(B.SPINE, B.HIPS);

  a.headYaw = damp(a.headYaw, clamp(e.lookYawRel, -1.4, 1.4), 7, dt);
  a.headPitch = damp(a.headPitch, clamp(e.lookPitch, -0.6, 0.6), 7, dt);
  const headY = clamp(a.headYaw - spineYawModel, -1.25, 1.25);
  const headX = clamp(a.headPitch - (spineX + pelvisPitch) * 0.8, -0.7, 0.7) - a.flinchZ * 0.5;
  m3Euler(T, 0, headX, headY, -0.1 * aim + a.flinchX * 0.4);
  m3Mul(R, HEAD9, R, SPINE9, T, 0);
  placeJoint(B.HEAD, B.SPINE);
  placeJoint(B.L_UARM, B.SPINE);
  placeJoint(B.R_UARM, B.SPINE);
  // Chest centre: the middle of the shoulder line.
  m3Point(R, SPINE9, 0, CHEST_Y, 0, J, SPINE3, V, 21);

  // ---- the gun: a blend of four holds -------------------------------------------------------------
  for (let i = 24; i < 33; i++) V[i] = 0;
  const wCarry = rw;
  const wAim = aim;
  const wPort = runW * (1 - aim) * (1 - rw);
  const wLow = Math.max(0, 1 - wCarry - wAim - wPort);
  addHold(wLow, HOLD_LOW, 9);
  addHold(wPort, HOLD_PORT, 18);
  addHold(wCarry, HOLD_CARRY, 27);
  if (wAim > 0) {
    m3Euler(T, 36, a.gunPitch + 0.07 * a.recoil, a.gunYaw, 0);
    m3Point(T, 36, HOLD_AIM[0], HOLD_AIM[1], HOLD_AIM[2] + 0.03 * a.recoil, V, 21, V, 36);
    blendHold(wAim, 36, V[36], V[37], V[38]);
  }
  m3Limb(R, GUN9, -V[27], -V[28], -V[29], V[24], V[25], V[26]);
  J[GUN3] = V[30];
  J[GUN3 + 1] = V[31];
  J[GUN3 + 2] = V[32];

  // ---- arms ---------------------------------------------------------------------------------------
  // Right wrist: on the grip, or on the pipe's path through the rush.
  m3Point(R, GUN9, WRIST_R[0], WRIST_R[1], WRIST_R[2], J, GUN3, V, 0);
  if (rw > 0.001) {
    const arc = Math.sin(PI * strike) * (1 - strike * 0.3);
    const lift = Math.sin(PI * stow);
    const hx = lerp(lerp(lerp(HAND_BACK[0], HAND_COCKED[0], cock), HAND_STRIKE[0], strike), HAND_BACK[0], stow);
    const hy = lerp(lerp(lerp(HAND_BACK[1], HAND_COCKED[1], cock), HAND_STRIKE[1], strike) + 0.14 * arc, HAND_BACK[1], stow) + 0.08 * lift;
    const hz = lerp(lerp(lerp(HAND_BACK[2], HAND_COCKED[2], cock), HAND_STRIKE[2], strike) - 0.12 * arc, HAND_BACK[2], stow) + 0.04 * lift;
    m3Point(R, SPINE9, hx, hy, hz, V, 21, V, 3);
    V[0] = lerp(V[0], V[3], rw);
    V[1] = lerp(V[1], V[4], rw);
    V[2] = lerp(V[2], V[5], rw);
  }
  // Elbow poles in the spine's frame: the right one down, out and back, the left one down and out.
  m3Point(R, SPINE9, 0.45, -0.8, 0.45, ZERO, 0, V, 6);
  reach(B.R_UARM, B.R_LARM, B.R_HAND, 0, LIMB.upperArm, LIMB.lowerArm, V[6], V[7], V[8], -1);
  m3Point(R, GUN9, WRIST_L[0], WRIST_L[1], WRIST_L[2], J, GUN3, V, 0);
  m3Point(R, SPINE9, -0.6, -0.8, 0.15, ZERO, 0, V, 6);
  reach(B.L_UARM, B.L_LARM, B.L_HAND, 0, LIMB.upperArm, LIMB.lowerArm, V[6], V[7], V[8], -1);
  // Hands follow the gun; the right one follows the forearm while it holds the pipe.
  m3Euler(T, 0, HAND_L_PITCH, 0, 0);
  m3Mul(R, B.L_HAND * 9, R, GUN9, T, 0);
  if (rw > 0.5) {
    m3Copy(R, B.R_HAND * 9, R, B.R_LARM * 9);
  } else {
    m3Euler(T, 0, HAND_R_PITCH, 0, 0);
    m3Mul(R, B.R_HAND * 9, R, GUN9, T, 0);
  }

  // ---- the pipe -------------------------------------------------------------------------------------
  m3Euler(T, 0, PIPE_BACK.rot[0], PIPE_BACK.rot[1], PIPE_BACK.rot[2]);
  m3Mul(T, 9, R, SPINE9, T, 0);
  m3Point(R, SPINE9, PIPE_BACK.at[0], PIPE_BACK.at[1], PIPE_BACK.at[2], V, 21, V, 9);
  if (inHand > 0.001 || a.carry > 0.001) {
    m3Euler(T, 0, lerp(PIPE_COCKED, PIPE_STRUCK, strike), 0, -0.25);
    m3Mul(T, 18, R, SPINE9, T, 0);
    const k = inHand;
    // Blend the two rotations by their X and Y axes, and the grip from the back to the fist.
    m3Limb(
      R,
      PIPE9,
      -lerp(T[10], T[19], k),
      -lerp(T[13], T[22], k),
      -lerp(T[16], T[25], k),
      lerp(T[9], T[18], k),
      lerp(T[12], T[21], k),
      lerp(T[15], T[24], k),
    );
    const h3 = B.R_HAND * 3;
    J[PIPE3] = lerp(V[9], J[h3], a.carry);
    J[PIPE3 + 1] = lerp(V[10], J[h3 + 1], a.carry);
    J[PIPE3 + 2] = lerp(V[11], J[h3 + 2], a.carry);
  } else {
    m3Copy(R, PIPE9, T, 9);
    J[PIPE3] = V[9];
    J[PIPE3 + 1] = V[10];
    J[PIPE3 + 2] = V[11];
  }

  // ---- legs -----------------------------------------------------------------------------------------
  m3Point(R, HIPS9, -HIP_X, HIP_DROP, 0, J, HIPS3, J, B.L_ULEG * 3);
  m3Point(R, HIPS9, HIP_X, HIP_DROP, 0, J, HIPS3, J, B.R_ULEG * 3);
  const gaitX = 0.11 - 0.035 * runW;
  const kneelW = kneel;
  const aimW = aim * (1 - kneel);
  for (let side = 0; side < 2; side++) {
    const key = side === 0 ? 'l' : 'r';
    const idle = STANCE_IDLE[key];
    const shoot = STANCE_AIM[key];
    const down = STANCE_KNEEL[key];
    const f = side * 3;
    // Standing targets: idle → shooting → kneeling, then the gait takes over with speed.
    let x = lerp(lerp(idle[0], shoot[0], aimW), down[0], kneelW);
    let y = lerp(lerp(idle[1], shoot[1], aimW), down[1], kneelW);
    let z = lerp(lerp(idle[2], shoot[2], aimW), down[2], kneelW);
    let pitch = lerp(0, down[3], kneelW);
    // Stepping on the spot while turning.
    y += F[f + 1] - ANKLE > 0 ? (F[f + 1] - ANKLE) * still : 0;
    x = lerp(x, side === 0 ? -gaitX : gaitX, moveW);
    y = lerp(y, F[f + 1], moveW);
    z = lerp(z, F[f], moveW) + J[HIPS3 + 2] * moveW;
    pitch = lerp(pitch, F[f + 2], moveW);
    V[0] = x;
    V[1] = y;
    V[2] = z;
    // Knees point where the pelvis faces, a little outward.
    m3Point(R, HIPS9, side === 0 ? -0.14 : 0.14, 0.05, -1, ZERO, 0, V, 6);
    const upper = side === 0 ? B.L_ULEG : B.R_ULEG;
    reach(upper, upper + 1, upper + 2, 0, LIMB.upperLeg, LIMB.lowerLeg, V[6], V[7], V[8], 1);
    m3Euler(R, (upper + 2) * 9, pitch, pelvisYaw * 0.6 + (side === 0 ? 0.1 : -0.1), 0);
  }

  writeAll(M);
  writeParams(a, M);

  // ---- what the game reads back -----------------------------------------------------------------------
  const out = a.out;
  m3Point(R, HEAD9, 0, HEAD.centreY, 0, J, HEAD3, out, OUT_HEAD);
  m3Point(R, GUN9, GUN.muzzle[0], GUN.muzzle[1], GUN.muzzle[2], J, GUN3, out, OUT_MUZZLE);
  m3Point(R, GUN9, GUN.lamp[0], GUN.lamp[1], GUN.lamp[2] - 0.02, J, GUN3, out, OUT_LAMP);
  out[OUT_AIM] = -R[GUN9 + 2];
  out[OUT_AIM + 1] = -R[GUN9 + 5];
  out[OUT_AIM + 2] = -R[GUN9 + 8];
  out[OUT_BODY_LOW] = J[HIPS3];
  out[OUT_BODY_LOW + 1] = Math.max(0.27, J[HIPS3 + 1] - 0.62);
  out[OUT_BODY_LOW + 2] = J[HIPS3 + 2];
  m3Point(R, SPINE9, 0, -0.13, 0, J, HEAD3, out, OUT_BODY_HIGH);
  out[OUT_CHEST] = V[21];
  out[OUT_CHEST + 1] = V[22];
  out[OUT_CHEST + 2] = V[23];

  // Remember the pose for a collapse that may start next frame.
  a.pelvisX = pelvisPitch;
  a.pelvisY = pelvisYaw;
  a.pelvisZ = pelvisRoll;
  a.spineX = spineX;
  a.spineY = spineY;
  a.spineZ = spineZ;
  a.headX = headX;
  a.headY = headY;
  captureForCollapse(a);
}

/* ---------------------------------------------------------------------------------- the collapse */

// Layout of `a.cap`, everything in model space at the moment of death:
//   0 hips position (3) · 3 ankles L, R (6) · 11 gun position (3) · 14 gun rotation (9)
//   23 arm rotations relative to the spine: L upper, L lower, R upper, R lower (36)
const CAP_HIPS = 0;
const CAP_ANKLE = 3;
const CAP_GUN = 11;
const CAP_GUN_R = 14;
const CAP_ARMS = 23;
const ARM_BONES = [B.L_UARM, B.L_LARM, B.R_UARM, B.R_LARM];

function captureForCollapse(a) {
  const c = a.cap;
  c[CAP_HIPS] = J[HIPS3];
  c[CAP_HIPS + 1] = J[HIPS3 + 1];
  c[CAP_HIPS + 2] = J[HIPS3 + 2];
  for (let i = 0; i < 3; i++) {
    c[CAP_ANKLE + i] = J[B.L_FOOT * 3 + i];
    c[CAP_ANKLE + 3 + i] = J[B.R_FOOT * 3 + i];
    c[CAP_GUN + i] = J[GUN3 + i];
  }
  for (let i = 0; i < 9; i++) c[CAP_GUN_R + i] = R[GUN9 + i];
  // Arm rotations in the spine's frame: spineᵀ · arm.
  for (let k = 0; k < 4; k++) {
    const b9 = ARM_BONES[k] * 9;
    const o = CAP_ARMS + k * 9;
    for (let r = 0; r < 3; r++) {
      for (let col = 0; col < 3; col++) {
        c[o + r * 3 + col] = R[SPINE9 + r] * R[b9 + col] + R[SPINE9 + 3 + r] * R[b9 + 3 + col] + R[SPINE9 + 6 + r] * R[b9 + 6 + col];
      }
    }
  }
}

// How he ends up, on his back (SUPINE) or on his front (PRONE). Arm bone directions are in the spine's
// frame (the bind arm hangs along −Y; +Z is his back), ankles and knee poles in the pelvis frame.
const SUPINE = {
  hipY: 0.118,
  slide: 0.5,
  spine: [0.05, 0, 0.06],
  head: [0.12, 0.55, 0],
  arms: [
    [-0.82, -0.55, 0.13], // left upper arm: flung out
    [-0.95, 0.25, 0.16], // left forearm
    [0.7, -0.7, 0.13], // right upper arm
    [0.15, -0.97, 0.2], // right forearm: across the hip
  ],
  ankles: [
    [-0.17, -0.8, 0.05],
    [0.2, -0.56, 0.05],
  ],
  poles: [
    [-0.25, 0, -1],
    [0.3, 0, -1],
  ],
  footPitch: [0.25, 0.1],
  footYaw: [0.5, -0.45],
};
const PRONE = {
  hipY: 0.118,
  slide: 0.4,
  spine: [-0.05, 0, 0.05],
  head: [-0.1, 1.15, 0],
  arms: [
    [-0.7, 0.6, -0.14], // left arm thrown up beside the head
    [-0.2, 0.97, -0.14],
    [0.78, -0.6, -0.14],
    [0.5, -0.85, -0.14],
  ],
  ankles: [
    [-0.15, -0.83, -0.045],
    [0.22, -0.79, -0.045],
  ],
  poles: [
    [-1, 0, -0.15],
    [1, 0, -0.15],
  ],
  footPitch: [-1.35, -1.3],
  footYaw: [0.35, -0.5],
};

/**
 * Starts the collapse. (dx, dz) is the horizontal direction of the killing shot in model space
 * (any length; zero means "straight back").
 */
export function startCollapse(a, dx, dz) {
  const len = Math.hypot(dx, dz);
  if (len < 1e-4) {
    dx = 0;
    dz = 1;
  } else {
    dx /= len;
    dz /= len;
  }
  a.dead = true;
  a.settled = false;
  a.deathT = 0;
  // Shot from the front half: over backwards. From behind: onto his face.
  a.prone = dz < -0.25;
  a.fallYaw = a.prone ? Math.atan2(-dx, -dz) : Math.atan2(dx, dz);
  a.lamp = 0;
}

/**
 * Advances and writes the collapse. Returns true once the body has settled (the pose is then final:
 * only writeGoonParams() needs calling to fade it).
 */
export function poseCollapse(a, dt, M, duration) {
  a.deathT += dt;
  a.flash = Math.max(0, a.flash - 7 * dt);
  const c = a.cap;
  const pose = a.prone ? PRONE : SUPINE;
  const flip = a.flip;
  const t = a.deathT;
  const fallTime = duration * 0.78;
  const u = clamp01(t / fallTime);
  const fall = u * u * (1.6 - 0.6 * u); // accelerates like a fall, lands at full speed
  const buckle = smoothstep(0, 0.4, u);
  const settle = t > fallTime ? clamp01((t - fallTime) / (duration - fallTime)) : 0;
  const bounce = Math.sin(PI * settle) * (1 - settle);

  // ---- the body as a whole: knees give, then it topples along the shot and twists onto back or front
  const pitch = (a.prone ? -1 : 1) * ((PI / 2 - 0.03) * fall - 0.07 * bounce);
  const yaw = lerp(a.pelvisY, a.fallYaw, smoothstep(0, 0.85, u));
  m3Euler(R, HIPS9, lerp(a.pelvisX, pitch, smoothstep(0, 0.25, u)), yaw, a.pelvisZ * (1 - u));
  const dirX = Math.sin(a.fallYaw) * (a.prone ? -1 : 1);
  const dirZ = Math.cos(a.fallYaw) * (a.prone ? -1 : 1);
  J[HIPS3] = c[CAP_HIPS] + dirX * pose.slide * fall;
  J[HIPS3 + 1] = lerp(lerp(c[CAP_HIPS + 1], 0.62, buckle), pose.hipY, fall) + 0.045 * bounce;
  J[HIPS3 + 2] = c[CAP_HIPS + 2] + dirZ * pose.slide * fall;

  const limp = smoothstep(0.05, 0.9, u);
  m3Euler(T, 0, lerp(a.spineX, pose.spine[0], limp), lerp(a.spineY, pose.spine[1], limp), lerp(a.spineZ, pose.spine[2] * flip, limp));
  m3Mul(R, SPINE9, R, HIPS9, T, 0);
  placeJoint(B.SPINE, B.HIPS);
  // The head lags, then drops and rolls to the side.
  const nod = Math.sin(PI * u) * (a.prone ? 0.35 : -0.4);
  m3Euler(T, 0, lerp(a.headX, pose.head[0], limp) + nod, lerp(a.headY, pose.head[1] * flip, limp), 0);
  m3Mul(R, HEAD9, R, SPINE9, T, 0);
  placeJoint(B.HEAD, B.SPINE);
  placeJoint(B.L_UARM, B.SPINE);
  placeJoint(B.R_UARM, B.SPINE);

  // ---- arms: from where they were to where they fall, in the spine's frame, trailing a little
  const armW = smoothstep(0.1, 1, u);
  const fling = Math.sin(PI * u) * 0.5;
  for (let k = 0; k < 4; k++) {
    const src = CAP_ARMS + k * 9;
    // A flipped pose is its own mirror image: swap the sides and negate X.
    const mirrored = flip < 0 ? (k + 2) % 4 : k;
    const dst = pose.arms[mirrored];
    const tx = dst[0] * flip;
    const len = Math.hypot(tx, dst[1], dst[2]);
    // Bone direction is −Y of its rotation. Mid-fall the arms are thrown up, away from the ground.
    const dx = lerp(-c[src + 1], tx / len, armW);
    const dy = lerp(-c[src + 4], dst[1] / len, armW) + fling * 0.6;
    const dz = lerp(-c[src + 7], dst[2] / len, armW) + fling * (a.prone ? 0.5 : -0.5);
    const dl = Math.hypot(dx, dy, dz) || 1;
    m3Limb(T, 0, dx / dl, dy / dl, dz / dl, c[src], c[src + 3], c[src + 6]);
    const bone = ARM_BONES[k];
    m3Mul(R, bone * 9, R, SPINE9, T, 0);
    // The next joint down the arm.
    const l = k % 2 === 0 ? LIMB.upperArm : LIMB.lowerArm;
    const b9 = bone * 9;
    J[(bone + 1) * 3] = J[bone * 3] - R[b9 + 1] * l;
    J[(bone + 1) * 3 + 1] = J[bone * 3 + 1] - R[b9 + 4] * l;
    J[(bone + 1) * 3 + 2] = J[bone * 3 + 2] - R[b9 + 7] * l;
  }
  m3Copy(R, B.L_HAND * 9, R, B.L_LARM * 9);
  m3Copy(R, B.R_HAND * 9, R, B.R_LARM * 9);

  // ---- legs: feet stay planted while the knees give, then slide out to where the body lies
  m3Point(R, HIPS9, -HIP_X, HIP_DROP, 0, J, HIPS3, J, B.L_ULEG * 3);
  m3Point(R, HIPS9, HIP_X, HIP_DROP, 0, J, HIPS3, J, B.R_ULEG * 3);
  const legW = smoothstep(0.25, 1, u);
  for (let side = 0; side < 2; side++) {
    const mirrored = flip < 0 ? 1 - side : side;
    const ankle = pose.ankles[mirrored];
    const pole = pose.poles[mirrored];
    m3Point(R, HIPS9, ankle[0] * flip, ankle[1], ankle[2], J, HIPS3, V, 3);
    const src = CAP_ANKLE + side * 3;
    V[0] = lerp(c[src], V[3], legW);
    V[1] = Math.max(0.06, lerp(c[src + 1], V[4], legW));
    V[2] = lerp(c[src + 2], V[5], legW);
    m3Point(R, HIPS9, lerp(side === 0 ? -0.14 : 0.14, pole[0] * flip, legW), 0.05 * (1 - legW), lerp(-1, pole[2], legW), ZERO, 0, V, 6);
    const upper = side === 0 ? B.L_ULEG : B.R_ULEG;
    reach(upper, upper + 1, upper + 2, 0, LIMB.upperLeg, LIMB.lowerLeg, V[6], V[7], V[8], 1);
    m3Euler(T, 0, pose.footPitch[mirrored], pose.footYaw[mirrored] * flip, 0);
    m3Mul(T, 9, R, HIPS9, T, 0);
    // Feet turn from flat on the street to wherever the lying pose leaves them.
    m3Euler(T, 18, 0, a.pelvisY * 0.6, 0);
    const f9 = (upper + 2) * 9;
    m3Limb(
      R,
      f9,
      -lerp(T[19], T[10], legW),
      -lerp(T[22], T[13], legW),
      -lerp(T[25], T[16], legW),
      lerp(T[18], T[9], legW),
      lerp(T[21], T[12], legW),
      lerp(T[24], T[15], legW),
    );
  }

  // ---- the pipe stays strapped to his back; the gun drops, skids and comes to rest on its side
  m3Euler(T, 0, PIPE_BACK.rot[0], PIPE_BACK.rot[1], PIPE_BACK.rot[2]);
  m3Mul(R, PIPE9, R, SPINE9, T, 0);
  m3Point(R, SPINE9, PIPE_BACK.at[0], CHEST_Y + PIPE_BACK.at[1], PIPE_BACK.at[2], J, SPINE3, J, PIPE3);
  const drop = clamp01(t / 0.5);
  const skid = 1 - (1 - drop) * (1 - drop);
  J[GUN3] = c[CAP_GUN] + (dirX * 0.35 + dirZ * 0.3 * flip) * skid;
  J[GUN3 + 1] = Math.max(0.03, c[CAP_GUN + 1] - 4.9 * t * t);
  J[GUN3 + 2] = c[CAP_GUN + 2] + (dirZ * 0.35 - dirX * 0.3 * flip) * skid;
  m3Euler(T, 0, 0, a.fallYaw + 1.1 * flip, PI / 2);
  m3Limb(
    R,
    GUN9,
    -lerp(c[CAP_GUN_R + 1], T[1], skid),
    -lerp(c[CAP_GUN_R + 4], T[4], skid),
    -lerp(c[CAP_GUN_R + 7], T[7], skid),
    lerp(c[CAP_GUN_R], T[0], skid),
    lerp(c[CAP_GUN_R + 3], T[3], skid),
    lerp(c[CAP_GUN_R + 6], T[6], skid),
  );

  writeAll(M);
  writeParams(a, M);
  a.settled = t >= duration;
  return a.settled;
}

/** Shader parameters only (a settled body that is fading). */
export function writeGoonParams(a, M) {
  writeParams(a, M);
}

/** Begins the pipe swing (the AI calls this when the blow lands or the dash is nearly over). */
export function startSwing(a) {
  a.swing = 0;
}
