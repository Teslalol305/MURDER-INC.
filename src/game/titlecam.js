// Title fly-through: the camera travels level.cinematicPath as one Catmull-Rom curve (positions) while
// it looks along a second one (look targets), at an even pace with a slight ease over the whole loop.
// The loop fades in from black at its start and back out at its end.

import * as THREE from 'three';
import { smoothstep } from '../core/util.js';

/**
 * @param {Array<{pos: Vector3, look: Vector3}>} path   level.cinematicPath
 * @param {object} T   config/flow.js `titleCamera`
 * @returns {{duration: number, length: number, apply(t, camera): number}}
 */
export function createTitleCamera(path, T) {
  const points = Array.isArray(path) ? path.filter((p) => p && p.pos && p.look) : [];
  const usable = points.length >= 2;
  const posCurve = usable ? new THREE.CatmullRomCurve3(points.map((p) => p.pos.clone()), false, 'centripetal') : null;
  const lookCurve = usable ? new THREE.CatmullRomCurve3(points.map((p) => p.look.clone()), false, 'centripetal') : null;
  if (usable) posCurve.arcLengthDivisions = Math.max(200, points.length * 40);
  const length = usable ? posCurve.getLength() : 0;
  const duration = Math.max(T.minLoop, length / T.speed);
  const sway = T.sway || { rate: 0, side: 0, lift: 0, roll: 0 };

  const pos = new THREE.Vector3();
  const look = new THREE.Vector3();
  const side = new THREE.Vector3();

  /** How black the screen is at loop time t: 1 at both ends of the loop, 0 in between. */
  function fadeAt(t) {
    return 1 - smoothstep(0, T.fadeIn, t) + smoothstep(duration - T.fadeOut, duration, t);
  }

  /**
   * Places `camera` for time `seconds` since the title came up and returns the fade (0 clear … 1 black).
   * Without a usable path the camera is left alone and only the fade runs.
   */
  function apply(seconds, camera) {
    const t = ((seconds % duration) + duration) % duration;
    if (usable) {
      const k = t / duration;
      const u = T.ease * smoothstep(0, 1, k) + (1 - T.ease) * k;
      // The same curve parameter for both curves, so each authored composition is met as authored.
      const at = posCurve.getUtoTmapping(u);
      posCurve.getPoint(at, pos);
      lookCurve.getPoint(at, look);

      // A hand-held breath: a few centimetres sideways and up, a trace of roll.
      const w = seconds * sway.rate;
      side.set(look.z - pos.z, 0, pos.x - look.x); // horizontal, at right angles to the view
      const flat = side.length();
      if (flat > 1e-4) pos.addScaledVector(side, (Math.sin(w) * sway.side) / flat);
      pos.y += Math.sin(w * 1.31 + 1.7) * sway.lift;

      camera.position.copy(pos);
      camera.lookAt(look);
      camera.rotateZ(Math.sin(w * 0.77 + 0.6) * sway.roll);
      camera.fov = T.fov; // the renderer refreshes the projection every frame
    }
    return fadeAt(t);
  }

  return { duration, length, usable, apply, fadeAt };
}
