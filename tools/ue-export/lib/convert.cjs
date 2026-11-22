'use strict';

// Web space → Unreal space, rounding and the JSON writer. Shared by export.cjs (which writes the files)
// and verify.cjs (which checks them), so both mean the same thing by "converted".
//
//   web     three.js: metres, +Y up, north = −Z, east = +X, right-handed
//   Unreal  centimetres, +Z up, X = east, Y = south, left-handed
//
//   Unreal (X, Y, Z) = (x_web, z_web, y_web) × 100
//
// Swapping two axes turns the right-handed web frame into Unreal's left-handed one without mirroring
// anything: a prop that reads left to right in the browser reads left to right in the editor.
//
// Angles. Three conventions meet here:
//   object    Object3D.rotation.y of a prop (radians). Local +X (a prop's forward axis) points to
//             (cos θ, 0, −sin θ) in the world.
//   heading   the player's yaw (radians, CONTRACT section 1): 0 looks at −Z, forward = (−sin, 0, −cos).
//   Unreal    FRotator.Yaw in degrees: 0 faces +X (east), +90 faces +Y (south).

const DECIMALS = 4;
const M_TO_CM = 100;
const DEG = 180 / Math.PI;

/** Rounds to `digits` decimals; never −0. */
function round(n, digits = DECIMALS) {
  if (!Number.isFinite(n)) return n;
  const f = 10 ** digits;
  const r = Math.round(n * f) / f;
  return r === 0 ? 0 : r;
}

/** Rounds every number in a JSON-like value (in a copy). */
function roundDeep(value) {
  if (typeof value === 'number') return round(value);
  if (Array.isArray(value)) return value.map(roundDeep);
  if (value && typeof value === 'object') {
    const out = {};
    for (const key of Object.keys(value)) out[key] = roundDeep(value[key]);
    return out;
  }
  return value;
}

/** Degrees in (−180, 180]. */
function wrapDegrees(deg) {
  let d = deg % 360;
  if (d > 180) d -= 360;
  if (d <= -180) d += 360;
  return d === 0 ? 0 : d;
}

// ------------------------------------------------------------------------------------------------
// Web values (rounded once, here: the Unreal twins are computed from the rounded numbers, so a reader
// of the files can reproduce every Unreal value from the web value next to it)
// ------------------------------------------------------------------------------------------------

const webPoint = (p) => ({ x: round(p.x), y: round(p.y), z: round(p.z) });

/** Unit vector (zero stays zero). */
function unit(v) {
  const len = Math.hypot(v.x, v.y, v.z);
  return len > 1e-12 ? { x: v.x / len, y: v.y / len, z: v.z / len } : { x: 0, y: 0, z: 0 };
}

const webDir = (v) => webPoint(unit(v));

/** The world direction of a prop's local +X for Object3D.rotation.y = θ. */
const forwardOfRotationY = (theta) => ({ x: Math.cos(theta), y: 0, z: -Math.sin(theta) });

/** The view direction of a heading (the player's yaw). */
const forwardOfHeading = (yaw) => ({ x: -Math.sin(yaw), y: 0, z: -Math.cos(yaw) });

// ------------------------------------------------------------------------------------------------
// Unreal values
// ------------------------------------------------------------------------------------------------

/** Position: metres → centimetres, y and z swapped. */
const uePoint = (p) => ({ X: round(round(p.x) * M_TO_CM), Y: round(round(p.z) * M_TO_CM), Z: round(round(p.y) * M_TO_CM) });

/** Direction: axes swapped, no scale. */
const ueDir = (v) => {
  const u = unit(v);
  return { X: round(u.x), Y: round(u.z), Z: round(u.y) };
};

/** A length in centimetres. */
const ueLength = (metres) => round(round(metres) * M_TO_CM);

/** Unreal yaw (degrees) of a web direction: atan2(z, x). A vertical direction has yaw 0. */
function ueYawOfDir(v) {
  if (Math.hypot(v.x, v.z) < 1e-9) return 0;
  return round(wrapDegrees(Math.atan2(v.z, v.x) * DEG));
}

/** Unreal yaw of a prop turned by Object3D.rotation.y = θ: the same turn seen in a left-handed frame. */
const ueYawOfRotationY = (theta) => round(wrapDegrees(-theta * DEG));

/** Unreal yaw of a heading (the player's yaw). */
const ueYawOfHeading = (yaw) => ueYawOfDir(forwardOfHeading(yaw));

/** FRotator that points an actor's +X along a web direction (Roll 0). */
function ueRotatorOfDir(v) {
  const u = unit(v);
  return { Pitch: round(Math.asin(Math.max(-1, Math.min(1, u.y))) * DEG), Yaw: ueYawOfDir(u), Roll: 0 };
}

/**
 * FRotator of an actor whose local +X lies along the web direction `right` and whose local +Z lies along
 * `up`. Its local +Y is then the web normal right × up, so a plane mesh modelled in the XZ plane with
 * its visible side toward +Y lands on a face exactly as the web game draws it (a sign reads along +X).
 * Same arithmetic as FMatrix::Rotator().
 */
function ueRotatorOfAxes(right, up) {
  const r = unit(right);
  const u = unit(up);
  const x = { X: r.x, Y: r.z, Z: r.y };
  const z = { X: u.x, Y: u.z, Z: u.y };
  const y = { X: z.Y * x.Z - z.Z * x.Y, Y: z.Z * x.X - z.X * x.Z, Z: z.X * x.Y - z.Y * x.X }; // Z × X
  const flat = Math.hypot(x.X, x.Y);
  const pitch = Math.atan2(x.Z, flat);
  const yaw = flat < 1e-9 ? 0 : Math.atan2(x.Y, x.X);
  const side = { X: -Math.sin(yaw), Y: Math.cos(yaw), Z: 0 }; // the Y axis of FRotator(pitch, yaw, 0)
  const roll = Math.atan2(z.X * side.X + z.Y * side.Y + z.Z * side.Z, y.X * side.X + y.Y * side.Y + y.Z * side.Z);
  return { Pitch: round(pitch * DEG), Yaw: round(wrapDegrees(yaw * DEG)), Roll: round(wrapDegrees(roll * DEG)) };
}

/** The axes an FRotator gives an actor (FRotationMatrix): {x, y, z} as Unreal vectors. */
function ueAxesOfRotator(rot) {
  const p = rot.Pitch / DEG;
  const w = rot.Yaw / DEG;
  const r = rot.Roll / DEG;
  const [sp, cp, sy, cy, sr, cr] = [Math.sin(p), Math.cos(p), Math.sin(w), Math.cos(w), Math.sin(r), Math.cos(r)];
  return {
    x: { X: cp * cy, Y: cp * sy, Z: sp },
    y: { X: sr * sp * cy - cr * sy, Y: sr * sp * sy + cr * cy, Z: -sr * cp },
    z: { X: -(cr * sp * cy + sr * sy), Y: cy * sr - cr * sp * sy, Z: cr * cp },
  };
}

/** Axis-aligned box: stays axis-aligned (no axis is flipped), plus the centre and half size Unreal likes. */
function ueBox(min, max) {
  const a = uePoint(min);
  const b = uePoint(max);
  return {
    min: a,
    max: b,
    center: { X: round((a.X + b.X) / 2), Y: round((a.Y + b.Y) / 2), Z: round((a.Z + b.Z) / 2) },
    extent: { X: round((b.X - a.X) / 2), Y: round((b.Y - a.Y) / 2), Z: round((b.Z - a.Z) / 2) },
  };
}

/** A size given as [x, y, z] extents in web space → Unreal box size (X, Y, Z), centimetres. */
const ueSize = (s) => ({ X: ueLength(s.x), Y: ueLength(s.z), Z: ueLength(s.y) });

/** A rectangle on the ground. */
const webRect = (r) => ({ minX: round(r.minX), maxX: round(r.maxX), minZ: round(r.minZ), maxZ: round(r.maxZ) });
const ueRect = (r) => ({ minX: ueLength(r.minX), maxX: ueLength(r.maxX), minY: ueLength(r.minZ), maxY: ueLength(r.maxZ) });

// ------------------------------------------------------------------------------------------------
// Colour
// ------------------------------------------------------------------------------------------------

/** 0xRRGGBB → "#rrggbb". */
const hexString = (n) => `#${(n >>> 0).toString(16).padStart(6, '0').slice(-6)}`;

/** "#rrggbb" → 0xRRGGBB (or null). */
const hexNumber = (s) => (typeof s === 'string' && /^#[0-9a-f]{6}$/i.test(s) ? parseInt(s.slice(1), 16) : null);

const srgbToLinear = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const linearToSrgb = (c) => (c <= 0.0031308 ? c * 12.92 : 1.055 * c ** (1 / 2.4) - 0.055);

/** An sRGB colour number as {hex, linear}: `linear` is what an FLinearColor takes. */
function colour(n) {
  const r = ((n >> 16) & 255) / 255;
  const g = ((n >> 8) & 255) / 255;
  const b = (n & 255) / 255;
  return { hex: hexString(n), linear: [round(srgbToLinear(r)), round(srgbToLinear(g)), round(srgbToLinear(b))] };
}

/** A linear RGB triple (scene-referred, may exceed 1) as {linear, hex}: `hex` is its clamped sRGB look. */
function colourOfLinear(rgb) {
  const to8 = (c) => Math.max(0, Math.min(255, Math.round(linearToSrgb(Math.max(0, Math.min(1, c))) * 255)));
  return { hex: hexString((to8(rgb[0]) << 16) | (to8(rgb[1]) << 8) | to8(rgb[2])), linear: rgb.map((c) => round(c)) };
}

// ------------------------------------------------------------------------------------------------
// Writing
// ------------------------------------------------------------------------------------------------

const INLINE_WIDTH = 132;

/**
 * Pretty JSON with a stable shape: two-space indentation, keys in the order they were built, numbers
 * rounded to four decimals, and any array or object that fits on one line written on one line (a
 * position is one line, not five). `exact`: numbers are written as they are (golden.mjs uses it to put the
 * tuning numbers back to full precision).
 */
function stringify(value, { exact = false } = {}) {
  const rounded = exact ? value : roundDeep(value);
  const flat = (v) => {
    if (v === null || typeof v !== 'object') return JSON.stringify(v);
    if (Array.isArray(v)) return `[${v.map(flat).join(', ')}]`;
    const keys = Object.keys(v);
    return keys.length ? `{ ${keys.map((k) => `${JSON.stringify(k)}: ${flat(v[k])}`).join(', ')} }` : '{}';
  };
  const write = (v, indent, room) => {
    if (v === null || typeof v !== 'object') return JSON.stringify(v);
    const one = flat(v);
    if (one.length <= room) return one;
    const pad = `${indent}  `;
    if (Array.isArray(v)) {
      return `[\n${v.map((item) => `${pad}${write(item, pad, INLINE_WIDTH - pad.length)}`).join(',\n')}\n${indent}]`;
    }
    const rows = Object.keys(v).map((k) => {
      const head = `${pad}${JSON.stringify(k)}: `;
      return `${head}${write(v[k], pad, INLINE_WIDTH - head.length)}`;
    });
    return `{\n${rows.join(',\n')}\n${indent}}`;
  };
  return `${write(rounded, '', INLINE_WIDTH)}\n`;
}

module.exports = {
  DECIMALS,
  M_TO_CM,
  round,
  roundDeep,
  wrapDegrees,
  unit,
  webPoint,
  webDir,
  webRect,
  forwardOfRotationY,
  forwardOfHeading,
  uePoint,
  ueDir,
  ueLength,
  ueYawOfDir,
  ueYawOfRotationY,
  ueYawOfHeading,
  ueRotatorOfDir,
  ueRotatorOfAxes,
  ueAxesOfRotator,
  ueBox,
  ueSize,
  ueRect,
  hexString,
  hexNumber,
  srgbToLinear,
  colour,
  colourOfLinear,
  stringify,
};
