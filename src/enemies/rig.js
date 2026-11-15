// Rigid skinning for the enemy models.
//
// A model is ONE geometry whose vertices each follow exactly one bone (weight 1), drawn as ONE
// SkinnedMesh per enemy with a geometry and a material shared by the whole pool. There are no Bone
// objects: the pose code writes the bone matrices (model space, relative to the bind pose) straight
// into the skeleton's float texture, which costs nothing in the scene graph.
//
// Bone slot 0 is not a transform. Its 16 floats are per-instance shader parameters, read by the
// material built in createEnemyMaterial():
//
//   [0] flash   hit flash 0…1                  [4…6] lamp colour (linear RGB)
//   [1] fade    dithered dissolve 0…1          [7]   unused
//   [2] lamp    lamp brightness (HDR scalar)
//   [3] rim     rim-light strength multiplier
//
// Per-vertex extras ride in the `aFx` attribute: x = self-illumination (share of the vertex colour that
// glows: masks, crew colours), y = 1 on lamp lenses (lit by the instance's lamp colour × brightness).

import * as THREE from 'three';

export const PARAM_SLOT = 0;
export const P_FLASH = 0;
export const P_FADE = 1;
export const P_LAMP = 2;
export const P_RIM = 3;
export const P_LAMP_R = 4;

const IDENTITY = new THREE.Matrix4();
const noop = () => {};

const _matrix = new THREE.Matrix4();
const _normalMatrix = new THREE.Matrix3();
const _position = new THREE.Vector3();
const _quaternion = new THREE.Quaternion();
const _scale = new THREE.Vector3();
const _euler = new THREE.Euler();
const _color = new THREE.Color();
const _a = new THREE.Vector3();
const _b = new THREE.Vector3();
const _c = new THREE.Vector3();
const _n = new THREE.Vector3();

/**
 * Collects primitive parts into one skinned geometry.
 *   add(geometry, {at, rot, scale, bone, color, glow, lamp, smooth})
 * `at` / `rot` (Euler XYZ) / `scale` place the part in the bind pose; `bone` is the bone it follows.
 * Parts are flat shaded unless `smooth` is set (then the source normals are kept).
 */
export function createModelBuilder() {
  const position = [];
  const normal = [];
  const color = [];
  const fx = [];
  const bone = [];

  function add(geometry, opts = {}) {
    const source = geometry.index ? geometry.toNonIndexed() : geometry;
    const at = opts.at || [0, 0, 0];
    const rot = opts.rot || [0, 0, 0];
    const s = opts.scale === undefined ? [1, 1, 1] : typeof opts.scale === 'number' ? [opts.scale, opts.scale, opts.scale] : opts.scale;
    _matrix.compose(_position.set(at[0], at[1], at[2]), _quaternion.setFromEuler(_euler.set(rot[0], rot[1], rot[2])), _scale.set(s[0], s[1], s[2]));
    _normalMatrix.getNormalMatrix(_matrix);
    const mirrored = _matrix.determinant() < 0;
    _color.set(opts.color === undefined ? 0x808080 : opts.color);
    const pos = source.getAttribute('position');
    const nor = source.getAttribute('normal');
    for (let i = 0; i < pos.count; i += 3) {
      _a.fromBufferAttribute(pos, i).applyMatrix4(_matrix);
      _b.fromBufferAttribute(pos, i + 1).applyMatrix4(_matrix);
      _c.fromBufferAttribute(pos, i + 2).applyMatrix4(_matrix);
      // A mirroring transform turns the triangle inside out: swap two corners.
      const second = mirrored ? _c : _b;
      const third = mirrored ? _b : _c;
      const order = mirrored ? [i, i + 2, i + 1] : [i, i + 1, i + 2];
      position.push(_a.x, _a.y, _a.z, second.x, second.y, second.z, third.x, third.y, third.z);
      if (opts.smooth && nor) {
        for (const k of order) {
          _n.fromBufferAttribute(nor, k).applyMatrix3(_normalMatrix).normalize();
          normal.push(_n.x, _n.y, _n.z);
        }
      } else {
        _n.subVectors(second, _a).cross(_position.subVectors(third, _a)).normalize();
        normal.push(_n.x, _n.y, _n.z, _n.x, _n.y, _n.z, _n.x, _n.y, _n.z);
      }
      for (let k = 0; k < 3; k++) {
        color.push(_color.r, _color.g, _color.b);
        fx.push(opts.glow || 0, opts.lamp ? 1 : 0);
        bone.push(opts.bone || 0);
      }
    }
    if (source !== geometry) source.dispose();
    return api;
  }

  /** The finished geometry. `radius` / `centre` give the bounding sphere of every pose the model can take. */
  function build(centre = [0, 0, 0], radius = 2) {
    const count = position.length / 3;
    const skinIndex = new Uint16Array(count * 4);
    const skinWeight = new Float32Array(count * 4);
    for (let i = 0; i < count; i++) {
      skinIndex[i * 4] = bone[i];
      skinWeight[i * 4] = 1;
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(position), 3));
    geometry.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(normal), 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(new Float32Array(color), 3));
    geometry.setAttribute('aFx', new THREE.BufferAttribute(new Float32Array(fx), 2));
    geometry.setAttribute('skinIndex', new THREE.BufferAttribute(skinIndex, 4));
    geometry.setAttribute('skinWeight', new THREE.BufferAttribute(skinWeight, 4));
    geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(centre[0], centre[1], centre[2]), radius);
    geometry.boundingBox = new THREE.Box3().setFromCenterAndSize(geometry.boundingSphere.center, _scale.setScalar(radius * 2));
    return geometry;
  }

  const api = {
    add,
    build,
    get triangles() {
      return position.length / 9;
    },
  };
  return api;
}

const VERTEX_PARS = /* glsl */ `
attribute vec2 aFx;
varying vec2 vEnemyFx;
varying vec4 vEnemyInst;
varying vec3 vEnemyLamp;
`;

const VERTEX_MAIN = /* glsl */ `
vEnemyFx = aFx;
#ifdef USE_SKINNING
  vEnemyInst = texelFetch( boneTexture, ivec2( 0, 0 ), 0 );
  vEnemyLamp = texelFetch( boneTexture, ivec2( 1, 0 ), 0 ).rgb;
#else
  vEnemyInst = vec4( 0.0, 0.0, 0.0, 1.0 );
  vEnemyLamp = vec3( 0.0 );
#endif
`;

const FRAGMENT_PARS = /* glsl */ `
varying vec2 vEnemyFx;
varying vec4 vEnemyInst;
varying vec3 vEnemyLamp;
uniform vec4 uEnemyRim;
uniform float uEnemyGlow;
`;

// Dissolve: an interleaved-gradient dither, so a fading body needs neither blending nor sorting.
const FRAGMENT_FADE = /* glsl */ `
if ( vEnemyInst.y > 0.0 ) {
  float enemyDither = fract( 52.9829189 * fract( dot( gl_FragCoord.xy, vec2( 0.06711056, 0.00583715 ) ) ) );
  if ( enemyDither < vEnemyInst.y ) discard;
}
`;

// Self-lit parts, the lamp, the hit flash and a view-dependent rim that lifts the silhouette off a dark street.
// uEnemyGlow and the rim's strength follow the time of day (setEnemyLook): full at night, a trace in sunlight.
const FRAGMENT_GLOW = /* glsl */ `
totalEmissiveRadiance += diffuseColor.rgb * ( vEnemyFx.x * uEnemyGlow );
totalEmissiveRadiance += vEnemyLamp * ( vEnemyFx.y * vEnemyInst.z );
totalEmissiveRadiance += vec3( 1.0, 0.82, 0.62 ) * ( vEnemyInst.x * 0.55 );
{
  float enemyRim = 1.0 - saturate( dot( normalize( vViewPosition ), normal ) );
  totalEmissiveRadiance += uEnemyRim.rgb * ( pow( enemyRim, uEnemyRim.a ) * vEnemyInst.w );
}
`;

function injectEnemyShader(shader) {
  shader.uniforms.uEnemyRim = this.userData.rim;
  shader.uniforms.uEnemyGlow = this.userData.glow;
  shader.vertexShader = shader.vertexShader
    .replace('#include <common>', `#include <common>\n${VERTEX_PARS}`)
    .replace('#include <skinbase_vertex>', `#include <skinbase_vertex>\n${VERTEX_MAIN}`);
  shader.fragmentShader = shader.fragmentShader
    .replace('#include <common>', `#include <common>\n${FRAGMENT_PARS}`)
    .replace('#include <clipping_planes_fragment>', `#include <clipping_planes_fragment>\n${FRAGMENT_FADE}`)
    .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>\n${FRAGMENT_GLOW}`);
}

/**
 * The shared enemy material: vertex-coloured standard shading plus the per-instance extras above.
 * @param {{roughness?:number, metalness?:number, rim?:number, rimPower?:number, rimStrength?:number}} opts
 */
export function createEnemyMaterial(opts = {}) {
  const material = new THREE.MeshStandardMaterial({
    vertexColors: true,
    roughness: opts.roughness ?? 0.8,
    metalness: opts.metalness ?? 0,
  });
  const rim = new THREE.Color(opts.rim ?? 0x8fb2ff).multiplyScalar(opts.rimStrength ?? 0.5);
  material.userData.rim = { value: new THREE.Vector4(rim.r, rim.g, rim.b, opts.rimPower ?? 2.6) };
  material.userData.rimBase = rim.clone();
  material.userData.glow = { value: 1 };
  material.onBeforeCompile = injectEnemyShader;
  // Every enemy material is the same program: the injected code does not depend on the options.
  material.customProgramCacheKey = () => 'enemy-rig-1';
  material.name = opts.name || 'enemy';
  return material;
}

/**
 * Day or night for an enemy material: `glow` scales the self-lit parts, `rim` the rim light (1 = as built).
 * Only uniform values change, never the program.
 */
export function setEnemyLook(material, glow, rim) {
  const base = material.userData.rimBase;
  material.userData.rim.value.set(base.r * rim, base.g * rim, base.b * rim, material.userData.rim.value.w);
  material.userData.glow.value = glow;
}

/**
 * One drawable instance of a rigged model.
 * @returns {{mesh: THREE.SkinnedMesh, matrices: Float32Array, touch(): void}}
 *   `matrices` holds 16 floats per bone slot (column-major); call touch() after writing to it.
 */
export function createRig(geometry, material, slots) {
  const skeleton = new THREE.Skeleton(new Array(slots).fill(null));
  skeleton.computeBoneTexture(); // allocates the final matrix array (padded to the texture size)
  skeleton.update = noop; // the renderer must not overwrite what the pose code wrote
  const matrices = skeleton.boneMatrices;
  for (let i = 0; i < slots; i++) IDENTITY.toArray(matrices, i * 16);
  matrices.fill(0, 0, 16);
  matrices[P_RIM] = 1;

  const mesh = new THREE.SkinnedMesh(geometry, material);
  mesh.bindMode = THREE.DetachedBindMode; // bone matrices are in the mesh's own space
  mesh.bind(skeleton, IDENTITY);
  mesh.boundingSphere = geometry.boundingSphere;
  mesh.boundingBox = geometry.boundingBox;
  mesh.raycast = noop; // hit tests go through enemies.raycast, never through THREE.Raycaster
  mesh.castShadow = true;
  mesh.receiveShadow = false;
  mesh.rotation.order = 'YXZ';

  const texture = skeleton.boneTexture;
  return {
    mesh,
    matrices,
    touch() {
      texture.needsUpdate = true;
    },
  };
}

/* --------------------------------------------------------------------------- 3 × 3 rotations */
//
// Rotations live in flat typed arrays, row-major, nine numbers each, addressed by offset: the pose code
// runs for every enemy every frame and must not allocate.
//
// V8 boxes a double that crosses a call it did not inline (as an argument or a result): 16 bytes of
// garbage each, and the pose code makes hundreds of such calls per enemy per frame. So every helper that
// takes numbers also comes as an `…A` variant that reads them from a Float64Array (a[ao], a[ao + 1], …);
// the hot pose code stages its numbers there. The plain forms are wrappers over the same math.
const ARGS = new Float64Array(12);

/** m[o…] = Ry(y) · Rx(x) · Rz(z): yaw, then pitch, then roll (three.js Euler order 'YXZ'). */
export function m3Euler(m, o, x, y, z) {
  ARGS[0] = x;
  ARGS[1] = y;
  ARGS[2] = z;
  m3EulerA(m, o, ARGS, 0);
}

/** m3Euler with the angles (x, y, z) in a[ao…ao+2]. */
export function m3EulerA(m, o, a, ao) {
  const x = a[ao];
  const y = a[ao + 1];
  const z = a[ao + 2];
  const cx = Math.cos(x);
  const sx = Math.sin(x);
  const cy = Math.cos(y);
  const sy = Math.sin(y);
  const cz = Math.cos(z);
  const sz = Math.sin(z);
  m[o] = cy * cz + sy * sx * sz;
  m[o + 1] = sy * sx * cz - cy * sz;
  m[o + 2] = sy * cx;
  m[o + 3] = cx * sz;
  m[o + 4] = cx * cz;
  m[o + 5] = -sx;
  m[o + 6] = cy * sx * sz - sy * cz;
  m[o + 7] = sy * sz + cy * sx * cz;
  m[o + 8] = cy * cx;
}

/** out[oo…] = a[ao…] · b[bo…]. `out` must not overlap the inputs. */
export function m3Mul(out, oo, a, ao, b, bo) {
  for (let r = 0; r < 3; r++) {
    const a0 = a[ao + r * 3];
    const a1 = a[ao + r * 3 + 1];
    const a2 = a[ao + r * 3 + 2];
    out[oo + r * 3] = a0 * b[bo] + a1 * b[bo + 3] + a2 * b[bo + 6];
    out[oo + r * 3 + 1] = a0 * b[bo + 1] + a1 * b[bo + 4] + a2 * b[bo + 7];
    out[oo + r * 3 + 2] = a0 * b[bo + 2] + a1 * b[bo + 5] + a2 * b[bo + 8];
  }
}

export function m3Copy(out, oo, a, ao) {
  for (let i = 0; i < 9; i++) out[oo + i] = a[ao + i];
}

/** out[oo…oo+2] = base[bo…] + m[o…] · (x, y, z). */
export function m3Point(m, o, x, y, z, base, bo, out, oo) {
  ARGS[0] = x;
  ARGS[1] = y;
  ARGS[2] = z;
  m3PointA(m, o, ARGS, 0, base, bo, out, oo);
}

/** m3Point with (x, y, z) in a[ao…ao+2]. `a` may be `out` (it is read first). */
export function m3PointA(m, o, a, ao, base, bo, out, oo) {
  const x = a[ao];
  const y = a[ao + 1];
  const z = a[ao + 2];
  out[oo] = base[bo] + m[o] * x + m[o + 1] * y + m[o + 2] * z;
  out[oo + 1] = base[bo + 1] + m[o + 3] * x + m[o + 4] * y + m[o + 5] * z;
  out[oo + 2] = base[bo + 2] + m[o + 6] * x + m[o + 7] * y + m[o + 8] * z;
}

/**
 * Rotation that takes the bind-pose limb (hanging along −Y, hinge along +X) to direction (dx, dy, dz)
 * with its hinge as close as possible to (hx, hy, hz). Writes m[o…]. Neither vector needs unit length,
 * which also makes this the way to blend rotations: feed it the weighted sums of their −Y and X axes.
 */
export function m3Limb(m, o, dx, dy, dz, hx, hy, hz) {
  ARGS[0] = dx;
  ARGS[1] = dy;
  ARGS[2] = dz;
  ARGS[3] = hx;
  ARGS[4] = hy;
  ARGS[5] = hz;
  m3LimbA(m, o, ARGS, 0);
}

/** m3Limb with (dx, dy, dz, hx, hy, hz) in a[ao…ao+5]. */
export function m3LimbA(m, o, a, ao) {
  const dx = a[ao];
  const dy = a[ao + 1];
  const dz = a[ao + 2];
  const hx = a[ao + 3];
  const hy = a[ao + 4];
  const hz = a[ao + 5];
  // Y axis: up along the bone. X axis: the hinge, made perpendicular to it. Z = X × Y.
  const dl = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1;
  const yx = -dx / dl;
  const yy = -dy / dl;
  const yz = -dz / dl;
  const d = hx * yx + hy * yy + hz * yz;
  let xx = hx - yx * d;
  let xy = hy - yy * d;
  let xz = hz - yz * d;
  let len = Math.sqrt(xx * xx + xy * xy + xz * xz);
  if (len < 1e-5) {
    // Hinge parallel to the bone: any perpendicular will do.
    if (Math.abs(yy) < 0.9) {
      xx = yz;
      xy = 0;
      xz = -yx;
    } else {
      xx = 1;
      xy = 0;
      xz = 0;
      const e = xx * yx;
      xx -= yx * e;
      xy -= yy * e;
      xz -= yz * e;
    }
    len = Math.sqrt(xx * xx + xy * xy + xz * xz);
  }
  xx /= len;
  xy /= len;
  xz /= len;
  m[o] = xx;
  m[o + 3] = xy;
  m[o + 6] = xz;
  m[o + 1] = yx;
  m[o + 4] = yy;
  m[o + 7] = yz;
  m[o + 2] = xy * yz - xz * yy;
  m[o + 5] = xz * yx - xx * yz;
  m[o + 8] = xx * yy - xy * yx;
}

/**
 * Writes one bone slot: the rigid transform that moves the bind-pose vertices of a bone whose joint
 * sat at (px, py, pz) to rotation r[ro…] about the joint's new position p[po…], scaled uniformly by `s`.
 */
export function writeBone(matrices, slot, r, ro, p, po, px, py, pz, s = 1) {
  ARGS[0] = px;
  ARGS[1] = py;
  ARGS[2] = pz;
  ARGS[3] = s;
  writeBoneA(matrices, slot, r, ro, p, po, ARGS, 0);
}

/** writeBone with the bind joint (px, py, pz) and the scale s in a[ao…ao+3]. */
export function writeBoneA(matrices, slot, r, ro, p, po, a, ao) {
  const px = a[ao];
  const py = a[ao + 1];
  const pz = a[ao + 2];
  const s = a[ao + 3];
  const o = slot * 16;
  const r0 = r[ro] * s;
  const r1 = r[ro + 1] * s;
  const r2 = r[ro + 2] * s;
  const r3 = r[ro + 3] * s;
  const r4 = r[ro + 4] * s;
  const r5 = r[ro + 5] * s;
  const r6 = r[ro + 6] * s;
  const r7 = r[ro + 7] * s;
  const r8 = r[ro + 8] * s;
  matrices[o] = r0;
  matrices[o + 1] = r3;
  matrices[o + 2] = r6;
  matrices[o + 3] = 0;
  matrices[o + 4] = r1;
  matrices[o + 5] = r4;
  matrices[o + 6] = r7;
  matrices[o + 7] = 0;
  matrices[o + 8] = r2;
  matrices[o + 9] = r5;
  matrices[o + 10] = r8;
  matrices[o + 11] = 0;
  matrices[o + 12] = p[po] - (r0 * px + r1 * py + r2 * pz);
  matrices[o + 13] = p[po + 1] - (r3 * px + r4 * py + r5 * pz);
  matrices[o + 14] = p[po + 2] - (r6 * px + r7 * py + r8 * pz);
  matrices[o + 15] = 1;
}

/**
 * Two-bone reach. From the root joint r[ro…] toward target (tx, ty, tz) with bone lengths l1, l2, the
 * middle joint bending toward the pole (kx, ky, kz). Writes the unit directions of both bones to
 * out[0…2] and out[3…5] and the middle joint to out[6…8].
 */
export function solveLimb(r, ro, tx, ty, tz, l1, l2, kx, ky, kz, out) {
  ARGS[0] = tx;
  ARGS[1] = ty;
  ARGS[2] = tz;
  ARGS[3] = l1;
  ARGS[4] = l2;
  ARGS[5] = kx;
  ARGS[6] = ky;
  ARGS[7] = kz;
  solveLimbA(r, ro, ARGS, 0, out);
}

/** solveLimb with (tx, ty, tz, l1, l2, kx, ky, kz) in a[ao…ao+7]. `a` may not be `out`. */
export function solveLimbA(r, ro, a, ao, out) {
  const tx = a[ao];
  const ty = a[ao + 1];
  const tz = a[ao + 2];
  const l1 = a[ao + 3];
  const l2 = a[ao + 4];
  const kx = a[ao + 5];
  const ky = a[ao + 6];
  const kz = a[ao + 7];
  let dx = tx - r[ro];
  let dy = ty - r[ro + 1];
  let dz = tz - r[ro + 2];
  let dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
  if (dist < 1e-5) {
    dx = 0;
    dy = -1;
    dz = 0;
    dist = 1e-5;
  } else {
    dx /= dist;
    dy /= dist;
    dz /= dist;
  }
  const reach = Math.min(Math.max(dist, Math.abs(l1 - l2) + 0.02), l1 + l2 - 0.002);
  const cosA = (l1 * l1 + reach * reach - l2 * l2) / (2 * l1 * reach);
  const sinA = Math.sqrt(Math.max(0, 1 - cosA * cosA));
  // The pole, made perpendicular to the reach direction.
  const d = kx * dx + ky * dy + kz * dz;
  let px = kx - dx * d;
  let py = ky - dy * d;
  let pz = kz - dz * d;
  let len = Math.sqrt(px * px + py * py + pz * pz);
  if (len < 1e-5) {
    px = Math.abs(dy) < 0.9 ? 0 : 1;
    py = Math.abs(dy) < 0.9 ? 1 : 0;
    pz = 0;
    const e = px * dx + py * dy;
    px -= dx * e;
    py -= dy * e;
    pz -= dz * e;
    len = Math.sqrt(px * px + py * py + pz * pz);
  }
  px /= len;
  py /= len;
  pz /= len;
  const ux = dx * cosA + px * sinA;
  const uy = dy * cosA + py * sinA;
  const uz = dz * cosA + pz * sinA;
  const mx = r[ro] + ux * l1;
  const my = r[ro + 1] + uy * l1;
  const mz = r[ro + 2] + uz * l1;
  // Lower bone: from the middle joint to the (clamped) end point.
  let lx = r[ro] + dx * reach - mx;
  let ly = r[ro + 1] + dy * reach - my;
  let lz = r[ro + 2] + dz * reach - mz;
  const ll = Math.sqrt(lx * lx + ly * ly + lz * lz) || 1;
  lx /= ll;
  ly /= ll;
  lz /= ll;
  out[0] = ux;
  out[1] = uy;
  out[2] = uz;
  out[3] = lx;
  out[4] = ly;
  out[5] = lz;
  out[6] = mx;
  out[7] = my;
  out[8] = mz;
}
