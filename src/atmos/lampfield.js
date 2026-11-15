// The lamp field: what every lamp looks like whether or not it carries a real light.
//
//   pools   additive patches of light on the ground under each lamp (neon: a coloured ellipse on the sidewalk)
//   cones   soft shafts of light under street lamps, El lamps and floods (medium quality and up)
//   glows   camera-facing halos at the fixtures; the same batch draws the blinking aviation lights, the
//           far traffic and the plane, because a glow may blink, drift along a line, or buzz like a tired lamp
//
// Three draw calls for the whole block, all additive, all dimmed by the same haze as the fog. Nothing here
// is updated per frame on the CPU: the shaders animate from uTime and uTrain.

import * as THREE from 'three';
import { clamp } from '../core/util.js';

/** How bright a lamp is right now (1 = steady). Shared by the three shaders. */
const LAMP_ON = /* glsl */ `
uniform float uTime;
uniform vec3 uTrain;   // x extent of the train above the street (min, max) and how present it is (0..1)
float lampOn( float phase, float tired, float underEl, float worldX ) {
	float on = 1.0;
	if ( tired > 0.0 ) {
		// A tired sodium lamp: buzzes, and drops out for a fraction of a second now and then.
		float buzz = sin( uTime * 37.0 + phase * 50.0 ) * sin( uTime * 11.3 + phase * 9.0 );
		float slot = floor( uTime * 6.0 + phase * 13.0 );
		float drop = step( 0.8, fract( sin( slot * 12.9898 ) * 43758.5453 ) );
		on *= 1.0 - tired * ( 0.22 + 0.2 * buzz + 0.55 * drop );
	}
	if ( underEl > 0.5 ) {
		// Lamps hung under the El stutter while a train is on top of them.
		float under = step( uTrain.x, worldX ) * step( worldX, uTrain.y ) * uTrain.z;
		on *= 1.0 - under * ( 0.28 + 0.24 * sin( uTime * 43.0 + worldX * 1.7 ) );
	}
	return on;
}
`;

const OUTPUT = /* glsl */ `
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
`;

const additive = (name, uniforms, vertexShader, fragmentShader, extra = {}) => {
  const material = new THREE.ShaderMaterial({
    name,
    uniforms,
    vertexShader,
    fragmentShader,
    transparent: true,
    blending: THREE.AdditiveBlending,
    premultipliedAlpha: true, // blend ONE, ONE: the shaders output finished radiance
    depthWrite: false,
    fog: false,
    ...extra,
  });
  // three.js draws a transparent double-sided material in two passes and rebuilds its program
  // parameters for each, every frame. Additive light without depth writes is order-free: one pass.
  if (material.side === THREE.DoubleSide) material.forceSinglePass = true;
  return material;
};

// ------------------------------------------------------------------------------------------------
// Pools
// ------------------------------------------------------------------------------------------------

function poolMaterial(shared, shadowFloor) {
  // `lights: true` only to get at the key's shadow map (the same chunks THREE.ShadowMaterial is made of):
  // light on the ground is cut by the shadows of cars, columns and the ties of the El.
  return additive(
    'atmos-pools',
    {
      ...THREE.UniformsUtils.clone(THREE.UniformsLib.lights),
      ...shared.haze.uniforms,
      uTime: shared.uTime,
      uTrain: shared.uTrain,
      uShadowFloor: { value: shadowFloor },
    },
    /* glsl */ `
#include <common>
#include <shadowmap_pars_vertex>
attribute vec4 aPool;    // u, v (-1..1 across the pool), edge hardness, phase
attribute vec4 aLight;   // radiance rgb, flags (1 tired, 2 under the El, 4 open to the sky: takes shadows)
varying vec4 vPool;
varying vec3 vColor;
varying vec2 vWorldXZ;
${shared.haze.glsl}
${LAMP_ON}
void main() {
	vec4 worldPosition = modelMatrix * vec4( position, 1.0 );
	vec4 mvPosition = viewMatrix * worldPosition;
	vec3 transformedNormal = normalMatrix * vec3( 0.0, 1.0, 0.0 );
	#include <shadowmap_vertex>
	float tired = mod( aLight.w, 2.0 );
	float underEl = mod( floor( aLight.w * 0.5 ), 2.0 );
	vColor = aLight.rgb * lampOn( aPool.w, tired, underEl, position.x ) * hazeT( - mvPosition.z, worldPosition.xz );
	vPool = vec4( aPool.xyz, step( 3.5, aLight.w ) );
	vWorldXZ = worldPosition.xz;
	gl_Position = projectionMatrix * mvPosition;
}`,
    /* glsl */ `
#include <common>
#include <packing>
#include <bsdfs>
#include <lights_pars_begin>
#include <shadowmap_pars_fragment>
#include <shadowmask_pars_fragment>
uniform float uShadowFloor;
varying vec4 vPool;
varying vec3 vColor;
varying vec2 vWorldXZ;
float poolHash( vec2 p ) {
	vec3 q = fract( vec3( p.xyx ) * 0.1031 );
	q += dot( q, q.yzx + 33.33 );
	return fract( ( q.x + q.y ) * q.z );
}
float poolNoise( vec2 p ) {
	vec2 i = floor( p );
	vec2 f = fract( p );
	f = f * f * ( 3.0 - 2.0 * f );
	return mix( mix( poolHash( i ), poolHash( i + vec2( 1.0, 0.0 ) ), f.x ),
		mix( poolHash( i + vec2( 0.0, 1.0 ) ), poolHash( i + vec2( 1.0, 1.0 ) ), f.x ), f.y );
}
void main() {
	float r2 = dot( vPool.xy, vPool.xy );
	float soft = max( 1.0 - r2, 0.0 );
	soft *= soft;
	float hard = 1.0 - smoothstep( 0.55, 1.0, r2 );
	float shape = mix( soft, hard, vPool.z );
	if ( shape < 0.003 ) discard;
	// Damp and dry patches: light on a street is never an even disc.
	float patches = 0.62 + 0.38 * poolNoise( vWorldXZ * 0.42 ) + 0.16 * ( poolNoise( vWorldXZ * 2.7 ) - 0.5 );
	float lit = mix( 1.0, mix( uShadowFloor, 1.0, getShadowMask() ), vPool.w );
	gl_FragColor = vec4( vColor * shape * patches * lit, 1.0 );
	${OUTPUT}
}`,
    { lights: true, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 },
  );
}

/**
 * One grid patch per lamp, draped over kerbs and floors (`groundAt(x, z)` gives the height to lie on),
 * plus the "sheen": a faint sheet of street light over the whole block that only shows where the key
 * light reaches, so near-black asphalt still carries the shadows of the El and of whoever stands on it.
 * @returns {THREE.Mesh | null}
 */
function buildPools(G, lamps, shared, cells, groundAt, bounds) {
  const cfg = G.config.look.lamps;
  const position = [];
  const aPool = [];
  const aLight = [];
  const index = [];
  const axisU = new THREE.Vector3();
  const axisV = new THREE.Vector3();
  const centre = new THREE.Vector3();
  const LIFT = 0.045;

  for (const lamp of lamps) {
    const style = lamp.style.pool;
    if (!style) continue;
    const radius = clamp(lamp.range * style.radius, style.min, style.max);
    let ru = radius;
    let rv = radius;
    let reach = 0; // slant distance from the fixture to the middle of its pool
    centre.copy(lamp.pos);
    axisU.set(1, 0, 0);
    axisV.set(0, 0, 1);

    if (lamp.wall) {
      // In front of the wall, stretched along it.
      axisV.copy(lamp.wall);
      axisU.set(-lamp.wall.z, 0, lamp.wall.x);
      ru = radius * (style.stretch ?? 1.3);
      centre.addScaledVector(lamp.wall, rv * 0.72);
    } else if (lamp.dir && lamp.dir.y < -0.05 && Math.hypot(lamp.dir.x, lamp.dir.z) > 0.05) {
      // An aimed lamp: where its axis meets the ground, stretched along the throw.
      const t = Math.min((lamp.pos.y - lamp.floor) / -lamp.dir.y, lamp.range * 0.9);
      centre.addScaledVector(lamp.dir, t);
      axisV.set(lamp.dir.x, 0, lamp.dir.z).normalize();
      axisU.set(-axisV.z, 0, axisV.x);
      rv = radius * clamp(1 / Math.max(-lamp.dir.y, 0.35), 1, 1.9);
      reach = t;
    }

    // A lamp over a raised floor lights that floor (cut off at its edge); every other pool drapes over
    // the street.
    const raised = lamp.floor > 0.6;
    const heightAt = raised
      ? (x, z) => (G.physics.groundHeight(x, z, lamp.floor + 0.3) > lamp.floor - 0.25 ? lamp.floor : -1)
      : groundAt;
    const drop = Math.max(reach || lamp.pos.y - (raised ? lamp.floor : groundAt(centre.x, centre.z)), 2);
    const gain = Math.min(cfg.poolGain * style.gain * (lamp.intensity / (drop * drop)), style.cap ?? 0.4);
    if (gain < 0.002) continue;
    const flags = (lamp.tired ? 1 : 0) + (lamp.kind === 'el' ? 2 : 0) + (style.shadowed ? 4 : 0);
    const phase = (lamp.index * 0.61803) % 1;

    const base = position.length / 3;
    for (let j = 0; j <= cells; j++) {
      for (let i = 0; i <= cells; i++) {
        const u = (i / cells) * 2 - 1;
        const v = (j / cells) * 2 - 1;
        const x = centre.x + axisU.x * u * ru + axisV.x * v * rv;
        const z = centre.z + axisU.z * u * ru + axisV.z * v * rv;
        const y = heightAt(x, z);
        const k = y < 0 ? 0 : gain; // off the edge of its floor: nothing to light
        position.push(x, (y < 0 ? lamp.floor : y) + LIFT, z);
        aPool.push(u, v, style.hard ?? 0, phase);
        aLight.push(lamp.color.r * k, lamp.color.g * k, lamp.color.b * k, flags);
      }
    }
    const row = cells + 1;
    for (let j = 0; j < cells; j++) {
      for (let i = 0; i < cells; i++) {
        const a = base + j * row + i;
        index.push(a, a + row, a + 1, a + 1, a + row, a + row + 1);
      }
    }
  }

  // The sheen: one sheet over the bounds (uv 0 = full strength everywhere), shadowed like the pools.
  const sheen = cfg.sheen;
  if (sheen && sheen.gain > 0) {
    const color = new THREE.Color(sheen.color);
    const nx = Math.max(2, Math.round((bounds.maxX - bounds.minX) / sheen.cell));
    const nz = Math.max(2, Math.round((bounds.maxZ - bounds.minZ) / sheen.cell));
    const base = position.length / 3;
    for (let j = 0; j <= nz; j++) {
      for (let i = 0; i <= nx; i++) {
        const x = bounds.minX + ((bounds.maxX - bounds.minX) * i) / nx;
        const z = bounds.minZ + ((bounds.maxZ - bounds.minZ) * j) / nz;
        position.push(x, groundAt(x, z) + LIFT * 0.8, z);
        aPool.push(0, 0, 0, 0);
        aLight.push(color.r * sheen.gain, color.g * sheen.gain, color.b * sheen.gain, 4);
      }
    }
    const row = nx + 1;
    for (let j = 0; j < nz; j++) {
      for (let i = 0; i < nx; i++) {
        const a = base + j * row + i;
        index.push(a, a + row, a + 1, a + 1, a + row, a + row + 1);
      }
    }
  }
  if (!index.length) return null;

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(position, 3));
  geo.setAttribute('aPool', new THREE.Float32BufferAttribute(aPool, 4));
  geo.setAttribute('aLight', new THREE.Float32BufferAttribute(aLight, 4));
  geo.setIndex(index);
  geo.computeBoundingSphere();
  const mesh = new THREE.Mesh(geo, poolMaterial(shared, cfg.poolShadowFloor));
  mesh.name = 'atmos-pools';
  mesh.receiveShadow = true;
  mesh.renderOrder = -20; // light on the ground goes down before anything else transparent
  mesh.matrixAutoUpdate = false;
  return mesh;
}

// ------------------------------------------------------------------------------------------------
// Cones
// ------------------------------------------------------------------------------------------------

function coneMaterial(shared) {
  return additive(
    'atmos-cones',
    { ...shared.haze.uniforms, uTime: shared.uTime, uTrain: shared.uTrain },
    /* glsl */ `
attribute vec4 aCone;    // t along the axis (0 at the lamp, 1 at the ground), phase, flags, unused
attribute vec3 aLight;
varying vec3 vNormal;
varying vec3 vView;
varying vec3 vColor;
varying float vT;
${shared.haze.glsl}
${LAMP_ON}
void main() {
	vec4 mv = modelViewMatrix * vec4( position, 1.0 );
	float tired = mod( aCone.z, 2.0 );
	float underEl = step( 1.5, aCone.z );
	vColor = aLight * lampOn( aCone.y, tired, underEl, position.x ) * hazeT( - mv.z, position.xz );
	vNormal = normal;
	vView = cameraPosition - position;
	vT = aCone.x;
	gl_Position = projectionMatrix * mv;
}`,
    /* glsl */ `
varying vec3 vNormal;
varying vec3 vView;
varying vec3 vColor;
varying float vT;
void main() {
	float dist = length( vView );
	// Brightest where the shaft is looked through at its thickest, nothing at its silhouette.
	float rim = abs( dot( normalize( vNormal ), vView / dist ) );
	float body = rim * rim * ( 3.0 - 2.0 * rim );
	// Dense at the lamp, thinning out before it reaches the ground.
	float along = 1.0 - vT;
	along = along * along * ( 0.3 + 0.7 * along );
	// No veil over the eyes of someone standing in the light.
	float near = smoothstep( 1.2, 6.5, dist );
	gl_FragColor = vec4( vColor * body * along * near, 1.0 );
	${OUTPUT}
}`,
    { side: THREE.DoubleSide },
  );
}

function buildCones(G, lamps, shared) {
  const SEGMENTS = 14;
  const RINGS = 3;
  const position = [];
  const normal = [];
  const aCone = [];
  const aLight = [];
  const index = [];
  const axis = new THREE.Vector3();
  const side = new THREE.Vector3();
  const other = new THREE.Vector3();
  const radial = new THREE.Vector3();
  const n = new THREE.Vector3();

  for (const lamp of lamps) {
    const style = lamp.style.cone;
    if (!style) continue;
    axis.copy(lamp.dir || { x: 0, y: -1, z: 0 });
    if (axis.y > -0.05) continue; // aimed at the sky: no shaft
    const toGround = (lamp.pos.y - lamp.floor) / -axis.y;
    const length = Math.min(toGround, lamp.range * (style.length ?? 1.2));
    if (length < 1.5) continue;
    const r0 = 0.22;
    const r1 = r0 + length * Math.tan(THREE.MathUtils.degToRad(style.angle));
    const slope = (r1 - r0) / length;
    // Wider, longer shafts hold more haze: keep their brightness per metre in check.
    const gain = style.gain * clamp(lamp.intensity / (lamp.style.ref ?? 60), 0.4, 1.6);
    const flags = (lamp.tired ? 1 : 0) + (lamp.kind === 'el' ? 2 : 0);
    const phase = (lamp.index * 0.61803) % 1;

    side.set(1, 0, 0);
    if (Math.abs(axis.x) > 0.9) side.set(0, 0, 1);
    side.crossVectors(axis, side).normalize();
    other.crossVectors(axis, side);

    const base = position.length / 3;
    for (let r = 0; r < RINGS; r++) {
      const t = r / (RINGS - 1);
      const radius = r0 + (r1 - r0) * t;
      for (let s = 0; s <= SEGMENTS; s++) {
        const a = (s / SEGMENTS) * Math.PI * 2;
        radial.copy(side).multiplyScalar(Math.cos(a)).addScaledVector(other, Math.sin(a));
        position.push(
          lamp.pos.x + axis.x * length * t + radial.x * radius,
          lamp.pos.y + axis.y * length * t + radial.y * radius,
          lamp.pos.z + axis.z * length * t + radial.z * radius,
        );
        n.copy(radial).addScaledVector(axis, -slope).normalize();
        normal.push(n.x, n.y, n.z);
        aCone.push(t, phase, flags, 0);
        aLight.push(lamp.color.r * gain, lamp.color.g * gain, lamp.color.b * gain);
      }
    }
    const row = SEGMENTS + 1;
    for (let r = 0; r < RINGS - 1; r++) {
      for (let s = 0; s < SEGMENTS; s++) {
        const a = base + r * row + s;
        index.push(a, a + row, a + 1, a + 1, a + row, a + row + 1);
      }
    }
  }
  if (!index.length) return null;

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(position, 3));
  geo.setAttribute('normal', new THREE.Float32BufferAttribute(normal, 3));
  geo.setAttribute('aCone', new THREE.Float32BufferAttribute(aCone, 4));
  geo.setAttribute('aLight', new THREE.Float32BufferAttribute(aLight, 3));
  geo.setIndex(index);
  geo.computeBoundingSphere();
  const mesh = new THREE.Mesh(geo, coneMaterial(shared));
  mesh.name = 'atmos-cones';
  mesh.renderOrder = -10;
  mesh.matrixAutoUpdate = false;
  return mesh;
}

// ------------------------------------------------------------------------------------------------
// Glows
// ------------------------------------------------------------------------------------------------

/**
 * Billboard halos. One material serves every batch (the static field, the lights of the train).
 */
export function createGlowMaterial(shared) {
  return additive(
    'atmos-glows',
    { ...shared.haze.uniforms, uTime: shared.uTime, uTrain: shared.uTrain },
    /* glsl */ `
attribute vec2 aCorner;
attribute vec3 aColor;
attribute vec4 aShape;    // size (m), core gain, halo gain, smallest angular size (rad)
attribute vec4 aBlink;    // period (s, 0 = steady), duty, phase, tired
attribute vec4 aMotion;   // velocity (m/s) and loop length (s, 0 = fixed)
attribute vec2 aExtra;    // loop offset (s), 1 = hangs under the El
varying vec2 vCorner;
varying vec3 vCore;
varying vec3 vHalo;
varying float vFar;
${shared.haze.glsl}
${LAMP_ON}
void main() {
	vec3 centre = position;
	float on = lampOn( aBlink.z, aBlink.w, aExtra.y, position.x );
	if ( aMotion.w > 0.0 ) {
		// Travels a straight line again and again, fading in and out at the ends.
		float t = mod( uTime + aExtra.x, aMotion.w );
		centre += aMotion.xyz * t;
		on *= smoothstep( 0.0, 2.0, t ) * ( 1.0 - smoothstep( aMotion.w - 2.0, aMotion.w, t ) );
	}
	if ( aBlink.x > 0.0 ) on *= step( fract( uTime / aBlink.x + aBlink.z ), aBlink.y );

	vec4 world = modelMatrix * vec4( centre, 1.0 );
	vec4 mv = viewMatrix * world;
	float dist = length( mv.xyz );
	float size = max( aShape.x, aShape.w * dist );
	// Held at its smallest size the glow is a point of light: let the hot spot fill it.
	vFar = clamp( aShape.w * dist / max( aShape.x, 1e-3 ) - 1.0, 0.0, 1.0 );
	// A lamp is its own source: haze dims it, but more slowly than it hides a wall.
	on *= mix( hazeT( - mv.z, world.xz ), 1.0, 0.22 );

	mv.xy += aCorner * size;
	// Bring the quad toward the eye (same place on screen) so nearby geometry does not slice the halo.
	float pull = min( size * 0.7, dist * 0.45 );
	mv.xyz *= ( mv.z + pull ) / mv.z;
	gl_Position = projectionMatrix * mv;

	vCorner = aCorner;
	vCore = aColor * aShape.y * on;
	vHalo = aColor * aShape.z * on;
}`,
    /* glsl */ `
varying vec2 vCorner;
varying vec3 vCore;
varying vec3 vHalo;
varying float vFar;
void main() {
	float r2 = dot( vCorner, vCorner );
	float fall = max( 1.0 - r2, 0.0 );
	float halo = fall * fall * exp( - r2 * 2.6 );
	float core = exp( - r2 * mix( 52.0, 5.0, vFar ) ) * fall;
	gl_FragColor = vec4( vCore * core + vHalo * halo, 1.0 );
	${OUTPUT}
}`,
  );
}

/** Collects glow quads; `mesh(material)` turns them into one draw call. */
export function createGlowBatch() {
  const position = [];
  const aCorner = [];
  const aColor = [];
  const aShape = [];
  const aBlink = [];
  const aMotion = [];
  const aExtra = [];
  const index = [];
  const CORNERS = [-1, -1, 1, -1, 1, 1, -1, 1];
  let count = 0;

  return {
    get count() {
      return count;
    },
    /**
     * @param {object} g
     * @param {{x, y, z}} g.pos
     * @param {{r, g, b}} g.color     linear colour; multiplied by `core` in the hot spot and `halo` around it
     * @param {number} g.size         radius in metres
     * @param {number} [g.minAngle]   never smaller than this many radians on screen
     * @param {number[]} [g.blink]    [period s, duty 0..1, phase 0..1]
     * @param {number} [g.tired]      0..1: buzzes and drops out
     * @param {number[]} [g.motion]   [vx, vy, vz, loop seconds, loop offset seconds]
     * @param {boolean} [g.underEl]   stutters under a passing train
     */
    add({ pos, color, size, core = 1, halo = 0.3, minAngle = 0, blink = null, phase = 0, tired = 0, motion = null, underEl = false }) {
      const base = count * 4;
      for (let c = 0; c < 4; c++) {
        position.push(pos.x, pos.y, pos.z);
        aCorner.push(CORNERS[c * 2], CORNERS[c * 2 + 1]);
        aColor.push(color.r, color.g, color.b);
        aShape.push(size, core, halo, minAngle);
        aBlink.push(blink ? blink[0] : 0, blink ? blink[1] : 1, blink ? blink[2] : phase, tired);
        aMotion.push(motion ? motion[0] : 0, motion ? motion[1] : 0, motion ? motion[2] : 0, motion ? motion[3] : 0);
        aExtra.push(motion ? motion[4] || 0 : 0, underEl ? 1 : 0);
      }
      index.push(base, base + 1, base + 2, base, base + 2, base + 3);
      count++;
    },
    mesh(material, name = 'atmos-glows') {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.Float32BufferAttribute(position, 3));
      geo.setAttribute('aCorner', new THREE.Float32BufferAttribute(aCorner, 2));
      geo.setAttribute('aColor', new THREE.Float32BufferAttribute(aColor, 3));
      geo.setAttribute('aShape', new THREE.Float32BufferAttribute(aShape, 4));
      geo.setAttribute('aBlink', new THREE.Float32BufferAttribute(aBlink, 4));
      geo.setAttribute('aMotion', new THREE.Float32BufferAttribute(aMotion, 4));
      geo.setAttribute('aExtra', new THREE.Float32BufferAttribute(aExtra, 2));
      geo.setIndex(index);
      const mesh = new THREE.Mesh(geo, material);
      mesh.name = name;
      mesh.frustumCulled = false; // quads are placed (and moved) in the vertex shader
      mesh.renderOrder = 20; // halos go over smoke and steam
      return mesh;
    },
  };
}

/**
 * Builds pools, cones and the glows of every lamp. Further glows (city, traffic, plane) are added to
 * `glowBatch` by their owners before `finish()` creates the mesh.
 */
export function createLampField(G, lamps, shared, parent, { poolCells = 5, groundAt = () => 0, bounds }) {
  const cfg = G.config.look.lamps;
  const pools = buildPools(G, lamps, shared, poolCells, groundAt, bounds);
  const cones = buildCones(G, lamps, shared);
  if (pools) parent.add(pools);
  if (cones) parent.add(cones);

  const glowBatch = createGlowBatch();
  for (const lamp of lamps) {
    const style = lamp.style.glow;
    if (!style) continue;
    // A wall lamp of 14 cd and a 90 cd street lamp are both "street": the glow follows the brightness.
    const power = clamp(lamp.intensity / (lamp.style.ref ?? lamp.intensity), 0.2, 1.7);
    glowBatch.add({
      pos: lamp.pos,
      color: lamp.color,
      size: style.size * Math.sqrt(power),
      core: style.core * (lamp.virtual ? 0.8 : 1) * Math.min(1, 0.45 + 0.55 * power),
      halo: style.halo,
      minAngle: style.core > 0 ? cfg.glowMinAngle : 0,
      phase: (lamp.index * 0.61803) % 1,
      tired: lamp.tired ? 1 : 0,
      underEl: lamp.kind === 'el',
    });
  }

  const glowMaterial = createGlowMaterial(shared);
  let glows = null;
  return {
    pools,
    cones,
    glowBatch,
    glowMaterial,
    get glows() {
      return glows;
    },
    finish() {
      glows = glowBatch.mesh(glowMaterial);
      glows.matrixAutoUpdate = false;
      parent.add(glows);
      return glows;
    },
  };
}
