// A cutscene (src/config/story.js `scenes`): shots in order, cues as the clock passes them.
//
// A shot is a straight camera move between two compositions with a field of view, the view turning
// evenly from the first one's direction to the second's (a pan, not a slide of the thing looked at: a
// target dragged past the camera would whip the picture round). A cut between two shots is hard, with a
// blink of black over it. The scene opens from black and closes to black.
// Pure: the owner says what a cue does and reads the camera pose out, so a scene runs in a unit test.

import { clamp01, lerp, smoothstep } from '../core/util.js';

const usable = (shot) =>
  !!shot && Array.isArray(shot.from) && shot.from.length === 6 && Array.isArray(shot.to) && shot.to.length === 6 && shot.secs > 0;

/**
 * @param {{shots: object[], cues?: object[]}} scene
 * @param {object} T   config/flow.js `story.cutscene`: fadeIn, fadeOut, cut, ease, sway {rate, side, lift, roll}
 * @param {(cue: object) => void} [onCue]   called once for every cue, in time order
 */
export function createCutscene(scene, T, onCue) {
  const shots = ((scene && scene.shots) || []).filter(usable);
  const starts = [];
  let duration = 0;
  for (const shot of shots) {
    starts.push(duration);
    duration += shot.secs;
  }
  const cues = [...((scene && scene.cues) || [])].filter((cue) => cue && cue.at >= 0).sort((a, b) => a.at - b.at);
  const sway = T.sway || { rate: 0, side: 0, lift: 0, roll: 0 };

  let time = 0;
  let next = 0; // the first cue not fired yet
  let done = shots.length === 0;

  /** The camera right now: where it is, what it looks at, its field of view, a roll, how black the screen is. */
  const pose = { x: 0, y: 0, z: 0, lookX: 0, lookY: 0, lookZ: -1, fov: 50, roll: 0, fade: 1, shot: 0 };

  /** Which shot is up at scene time `t`. */
  function shotAt(t) {
    let i = shots.length - 1;
    while (i > 0 && t < starts[i]) i--;
    return i;
  }

  /** Writes the camera of scene time `t` to `out`. */
  function sample(t, out = pose) {
    if (shots.length === 0) {
      out.fade = 1;
      return out;
    }
    const at = Math.min(Math.max(0, t), duration);
    const i = shotAt(at);
    const shot = shots[i];
    const k = clamp01((at - starts[i]) / shot.secs);
    const u = T.ease * smoothstep(0, 1, k) + (1 - T.ease) * k;
    const a = shot.from;
    const b = shot.to;
    out.x = lerp(a[0], b[0], u);
    out.y = lerp(a[1], b[1], u);
    out.z = lerp(a[2], b[2], u);
    // The view direction turns on the great arc between the two compositions' directions; how far off
    // the thing looked at is eases with it.
    let ax = a[3] - a[0];
    let ay = a[4] - a[1];
    let az = a[5] - a[2];
    let bx = b[3] - b[0];
    let by = b[4] - b[1];
    let bz = b[5] - b[2];
    const al = Math.hypot(ax, ay, az) || 1;
    const bl = Math.hypot(bx, by, bz) || 1;
    ax /= al;
    ay /= al;
    az /= al;
    bx /= bl;
    by /= bl;
    bz /= bl;
    const angle = Math.acos(Math.min(1, Math.max(-1, ax * bx + ay * by + az * bz)));
    let wa = 1 - u;
    let wb = u;
    if (angle > 1e-4 && angle < Math.PI - 1e-3) {
      const s = Math.sin(angle);
      wa = Math.sin((1 - u) * angle) / s;
      wb = Math.sin(u * angle) / s;
    }
    const reach = lerp(al, bl, u);
    out.lookX = out.x + (ax * wa + bx * wb) * reach;
    out.lookY = out.y + (ay * wa + by * wb) * reach;
    out.lookZ = out.z + (az * wa + bz * wb) * reach;
    out.fov = lerp(shot.fov || 50, shot.fovTo || shot.fov || 50, u);
    out.shot = i;

    // A hand-held breath: a few centimetres sideways and up, a trace of roll.
    const w = at * sway.rate;
    const sx = out.lookZ - out.z;
    const sz = out.x - out.lookX;
    const flat = Math.hypot(sx, sz);
    if (flat > 1e-4) {
      const s = (Math.sin(w) * sway.side) / flat;
      out.x += sx * s;
      out.z += sz * s;
    }
    out.y += Math.sin(w * 1.31 + 1.7) * sway.lift;
    out.roll = Math.sin(w * 0.77 + 0.6) * sway.roll;

    // Black at both ends of the scene, and a blink over every cut.
    let fade = Math.max(1 - smoothstep(0, T.fadeIn, at), smoothstep(duration - T.fadeOut, duration, at));
    if (T.cut > 0) {
      if (i > 0) fade = Math.max(fade, 1 - (at - starts[i]) / T.cut);
      if (i < shots.length - 1) fade = Math.max(fade, 1 - (starts[i + 1] - at) / T.cut);
    }
    out.fade = clamp01(fade);
    return out;
  }

  /** Advances the scene; fires the cues it passes. Returns true once it is over. */
  function update(dt) {
    if (done) return true;
    time = Math.min(duration, time + Math.max(0, dt));
    while (next < cues.length && cues[next].at <= time) {
      const cue = cues[next++];
      if (onCue) onCue(cue);
    }
    sample(time);
    if (time >= duration) done = true;
    return done;
  }

  /** Straight to the end. The cues it jumps over are not played: a skipped line is not said. */
  function skip() {
    time = duration;
    next = cues.length;
    done = true;
    sample(time);
  }

  /** Puts a three.js camera where the scene has it (the renderer refreshes the projection every frame). */
  function apply(camera) {
    camera.position.set(pose.x, pose.y, pose.z);
    camera.lookAt(pose.lookX, pose.lookY, pose.lookZ);
    if (pose.roll) camera.rotateZ(pose.roll);
    camera.fov = pose.fov;
    return pose.fade;
  }

  sample(0);
  return {
    duration,
    shots,
    pose,
    sample,
    update,
    skip,
    apply,
    get time() {
      return time;
    },
    get done() {
      return done;
    },
  };
}
