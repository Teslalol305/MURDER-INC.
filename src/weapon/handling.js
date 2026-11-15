// Shared vocabulary for how the guns are held: gun poses, hand keys, finger poses and the little
// track sampler the reload and melee choreography is written with.
//
//   gun pose   where the gun sits in view space: {pos, quat}
//   hand key   where a hand is: {space: 'gun' | 'rig', pos, quat, pose}. A key in gun space rides with
//              the gun; one in rig space is fixed to the camera (reaching for a fresh magazine).
//   track      [[time, key], …]: the hand moves from key to key with an eased blend.

import * as THREE from 'three';
import { makePose, placePalm } from './arms.js';
import { ease } from './springs.js';

const V = (a) => new THREE.Vector3(a[0], a[1], a[2]);

/** Gun pose from a position and pitch / yaw / roll (radians; yaw + turns the muzzle left). */
export function gunPose(x, y, z, pitch = 0, yaw = 0, roll = 0) {
  return {
    pos: new THREE.Vector3(x, y, z),
    quat: new THREE.Quaternion().setFromEuler(new THREE.Euler(pitch, yaw, roll, 'YXZ')),
  };
}

/**
 * A hand key from the palm: its middle sits at `at`, presses along `into`, fingers run along `along`.
 * `side` is +1 for the right hand, −1 for the left.
 */
export function handKey(side, space, at, into, along, pose) {
  const frame = { side, pos: new THREE.Vector3(), quat: new THREE.Quaternion() };
  placePalm(frame, V(at), V(into), V(along));
  return { space, pos: frame.pos, quat: frame.quat, pose };
}

/** The same key moved by `offset` (in its own space). */
export function shiftKey(key, offset, pose = key.pose) {
  return { space: key.space, pos: key.pos.clone().add(V(offset)), quat: key.quat, pose };
}

/** The same key turned by `angle` radians about the axis `dir` through the point `pivot` (its own space). */
export function turnKey(key, pivot, dir, angle, pose = key.pose) {
  const q = new THREE.Quaternion().setFromAxisAngle(V(dir).normalize(), angle);
  const p = V(pivot);
  return {
    space: key.space,
    pos: key.pos.clone().sub(p).applyQuaternion(q).add(p),
    quat: q.clone().multiply(key.quat),
    pose,
  };
}

/**
 * Samples a track at time t: writes the two keys around t and the eased blend between them to `out`
 * ({a, b, t}). Before the first key and after the last the hand rests on that key.
 */
export function sampleTrack(track, t, out) {
  const last = track.length - 1;
  if (t <= track[0][0]) {
    out.a = out.b = track[0][1];
    out.t = 0;
    return out;
  }
  for (let i = 0; i < last; i++) {
    if (t < track[i + 1][0]) {
      out.a = track[i][1];
      out.b = track[i + 1][1];
      out.t = ease((t - track[i][0]) / (track[i + 1][0] - track[i][0]));
      return out;
    }
  }
  out.a = out.b = track[last][1];
  out.t = 0;
  return out;
}

/** Piecewise-linear value through [[time, value], …]. */
export function sampleCurve(curve, t) {
  const last = curve.length - 1;
  if (t <= curve[0][0]) return curve[0][1];
  for (let i = 0; i < last; i++) {
    if (t < curve[i + 1][0]) {
      const k = (t - curve[i][0]) / (curve[i + 1][0] - curve[i][0]);
      return curve[i][1] + (curve[i + 1][1] - curve[i][1]) * k;
    }
  }
  return curve[last][1];
}

// Finger poses: [knuckle curl, middle curl, tip curl, spread] per finger, thumb [in, down, twist, curl, tip].
const wrap = [1.3, 1.5, 0.8, 0];
export const POSES = {
  relaxed: makePose({ fingers: [0.35, 0.5, 0.3, 0], thumb: [0.1, 0.1, 0, 0.25, 0.25] }),
  fist: makePose({ fingers: [1.45, 1.6, 0.9, 0], thumb: [0.5, 0.7, 0, 0.6, 0.7] }),
  // Firing hand on a rifle grip: index along the frame, off the trigger.
  rifleGrip: makePose({ index: [0.18, 0.3, 0.2, 0.05], middle: [1.25, 1.45, 0.75, 0.02], ring: wrap, pinky: [1.35, 1.5, 0.8, -0.04], thumb: [0.3, 0.55, 0, 0.45, 0.5] }),
  rifleTrigger: makePose({ index: [0.42, 0.95, 0.5, 0.05], middle: [1.25, 1.45, 0.75, 0.02], ring: wrap, pinky: [1.35, 1.5, 0.8, -0.04], thumb: [0.3, 0.55, 0, 0.45, 0.5] }),
  // Support hand cupping a handguard from below.
  rifleSupport: makePose({ fingers: [1.05, 0.95, 0.5, 0], pinky: [1.1, 1.0, 0.55, -0.05], thumb: [-0.15, 0.1, 0, 0.15, 0.2] }),
  // Around a rifle magazine: fingers across the front, thumb up the back.
  magHold: makePose({ fingers: [0.95, 1.05, 0.55, 0], thumb: [0.15, 0.45, 0, 0.3, 0.35] }),
  // Two fingers hooked over a charging handle.
  hook: makePose({ index: [0.85, 1.1, 0.6, 0], middle: [0.9, 1.15, 0.65, 0], ring: wrap, pinky: wrap, thumb: [0.4, 0.4, 0, 0.4, 0.4] }),
  // Firing hand on a pistol.
  pistolGrip: makePose({ index: [0.12, 0.25, 0.15, 0.04], middle: [1.2, 1.4, 0.7, 0], ring: [1.25, 1.45, 0.75, 0], pinky: [1.3, 1.5, 0.8, -0.03], thumb: [0.2, 0.35, 0, 0.3, 0.25] }),
  pistolTrigger: makePose({ index: [0.38, 0.9, 0.45, 0.04], middle: [1.2, 1.4, 0.7, 0], ring: [1.25, 1.45, 0.75, 0], pinky: [1.3, 1.5, 0.8, -0.03], thumb: [0.2, 0.35, 0, 0.3, 0.25] }),
  // Thumb reaching down for the magazine button / up for the slide stop.
  pistolThumbDown: makePose({ index: [0.12, 0.25, 0.15, 0.04], middle: [1.2, 1.4, 0.7, 0], ring: [1.25, 1.45, 0.75, 0], pinky: [1.3, 1.5, 0.8, -0.03], thumb: [0.45, 0.6, 0, 0.55, 0.6] }),
  // Support hand wrapped over the firing hand.
  pistolSupport: makePose({ fingers: [1.15, 1.2, 0.6, 0], thumb: [0.05, 0.2, 0, 0.15, 0.1] }),
  // A pistol magazine between thumb and fingers, base in the palm.
  magPinch: makePose({ fingers: [0.75, 0.95, 0.5, 0], index: [0.45, 0.6, 0.3, 0.05], thumb: [0.3, 0.5, 0, 0.35, 0.3] }),
  // Open hand, heel forward: the slap that seats a magazine.
  palm: makePose({ fingers: [0.25, 0.3, 0.2, 0.02], thumb: [-0.2, 0, 0, 0.1, 0.1] }),
};
