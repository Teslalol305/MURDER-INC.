// Night haze.
//
// `scene.fog` is a plain FogExp2, but the fog shader three.js compiles into every material is replaced
// (before anything in the world has been compiled) by one that does two more things:
//
//   - the haze thickens outside the play bounds, so the avenue runs out into glow instead of ending;
//   - its colour leans warm toward the city glow in the west and cool toward the moon in the east.
//
// Both are functions of the world position, which the vertex chunk derives from the view-space position
// every fogged material already has: nothing else about a material needs to change. The numbers are
// written into the shader text (they never change), `scene.fog.color` and `.density` stay live uniforms.
//
// The same maths is exported as GLSL for the atmosphere's own additive shaders (`glsl`), and in
// src/atmos/plan.js for the CPU side.

import * as THREE from 'three';
import { endHazeK } from './plan.js';

/** GLSL float literal. */
const f = (n) => {
  const s = Number(n).toFixed(6);
  return s.includes('.') ? s : `${s}.0`;
};
const vec = (list) => `vec${list.length}( ${list.map(f).join(', ')} )`;

export function createFog(G, bounds) {
  const cfg = G.config.look.fog;
  const fog = new THREE.FogExp2(0x000000, cfg.density);
  fog.color.setRGB(cfg.haze[0], cfg.haze[1], cfg.haze[2]); // already linear: no colour-space conversion
  G.scene.fog = fog;

  const centre = [(bounds.minX + bounds.maxX) / 2, (bounds.minZ + bounds.maxZ) / 2];
  const half = [(bounds.maxX - bounds.minX) / 2 + cfg.endClear, (bounds.maxZ - bounds.minZ) / 2 + cfg.endClear];
  const k = endHazeK(cfg.endReach);
  const tintMid = cfg.tintWest.map((w, i) => (w + cfg.tintEast[i]) / 2);
  const tintDelta = cfg.tintWest.map((w, i) => (cfg.tintEast[i] - w) / 2);
  // By day the haze leans only a little (brighter toward the sun). Which set applies is read from the fog
  // colour itself (a bright haze is a day haze), so a day / night switch is a uniform change, not a define.
  const day = G.config.look.dayFogTint || { west: [1, 1, 1], east: [1, 1, 1] };
  const dayMid = day.west.map((w, i) => (w + day.east[i]) / 2);
  const dayDelta = day.west.map((w, i) => (day.east[i] - w) / 2);

  // Extinction outside the bounds, and the tint (−1 looking west … +1 looking east).
  const END = `dot( atmOut, atmOut ) * ${f(k * k)}`;
  const OUT = `max( abs( WORLD_XZ - ${vec(centre)} ) - ${vec(half)}, 0.0 )`;
  const DAYNESS = (c) => `smoothstep( 0.1, 0.3, dot( ${c}, vec3( 0.2126, 0.7152, 0.0722 ) ) )`;
  const TINT_OF = (c) =>
    `mix( ${vec(tintMid)} + ${vec(tintDelta)} * atmWest, ${vec(dayMid)} + ${vec(dayDelta)} * atmWest, ${DAYNESS(c)} )`;
  const TINT = TINT_OF('fogColor');

  if (cfg.endReach > 0) {
    const chunk = THREE.ShaderChunk;
    chunk.fog_pars_vertex = /* glsl */ `
#ifdef USE_FOG
	varying float vFogDepth;
	varying vec2 vFogXZ;
#endif
`;
    // World x/z from the view-space position: the view matrix is rigid, so its transpose undoes the rotation.
    chunk.fog_vertex = /* glsl */ `
#ifdef USE_FOG
	vFogDepth = - mvPosition.z;
	vFogXZ = ( ( mvPosition.xyz - viewMatrix[ 3 ].xyz ) * mat3( viewMatrix ) ).xz;
#endif
`;
    chunk.fog_pars_fragment = /* glsl */ `
#ifdef USE_FOG
	uniform vec3 fogColor;
	varying float vFogDepth;
	varying vec2 vFogXZ;
	#ifdef FOG_EXP2
		uniform float fogDensity;
	#else
		uniform float fogNear;
		uniform float fogFar;
	#endif
#endif
`;
    chunk.fog_fragment = /* glsl */ `
#ifdef USE_FOG
	vec2 atmOut = ${OUT.replace('WORLD_XZ', 'vFogXZ')};
	#ifdef FOG_EXP2
		float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth - ${END} );
	#else
		float fogFactor = 1.0 - ( 1.0 - smoothstep( fogNear, fogFar, vFogDepth ) ) * exp( - ${END} );
	#endif
	vec2 atmDir = vFogXZ - cameraPosition.xz;
	float atmWest = atmDir.x * inversesqrt( dot( atmDir, atmDir ) + 1.0 );
	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor * ${TINT}, fogFactor );
#endif
`;
  }

  // Live uniforms for the atmosphere's own shaders (shared objects: one write reaches every material).
  const uniforms = {
    uFogDensity: { value: fog.density },
    uFogColor: { value: fog.color },
  };

  /**
   * For ShaderMaterials (vertex or fragment stage; `cameraPosition` comes from three.js):
   *   hazeT(viewDepth, worldXZ)  fraction of light that makes it through the haze
   *   hazeColor(worldXZ)         what the haze itself looks like in that direction
   *   hazeTint(west)             the tint alone, for a direction (−1 west … +1 east)
   */
  const glsl = /* glsl */ `
uniform float uFogDensity;
uniform vec3 uFogColor;
float hazeT( float viewDepth, vec2 worldXZ ) {
	vec2 atmOut = ${cfg.endReach > 0 ? OUT.replace('WORLD_XZ', 'worldXZ') : 'vec2( 0.0 )'};
	return exp( - uFogDensity * uFogDensity * viewDepth * viewDepth - ${END} );
}
vec3 hazeTint( float atmWest ) {
	return ${TINT_OF('uFogColor')};
}
vec3 hazeColor( vec2 worldXZ ) {
	vec2 atmDir = worldXZ - cameraPosition.xz;
	return uFogColor * hazeTint( atmDir.x * inversesqrt( dot( atmDir, atmDir ) + 1.0 ) );
}
`;

  let baseDensity = cfg.density;
  let densityScale = 1;

  return {
    fog,
    uniforms,
    glsl,
    k,
    /** Thins or thickens the haze (1 = configured density). */
    setDensityScale(scale) {
      densityScale = scale;
      fog.density = uniforms.uFogDensity.value = baseDensity * scale;
    },
    /** The haze of a time of day: linear colour [r, g, b] and FogExp2 density (before the interior scale). */
    setBase(haze, density) {
      fog.color.setRGB(haze[0], haze[1], haze[2]);
      baseDensity = density;
      fog.density = uniforms.uFogDensity.value = baseDensity * densityScale;
    },
  };
}
