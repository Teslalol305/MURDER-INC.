// Small shader patches on top of MeshStandardMaterial (applied once, when a material is created).
//
// 1. patchWorld: for the ground and masonry of the block, which never move. Adds, in world space:
//      - slow tone variation so a tiled wall or street does not read as tiles,
//      - the wet street: damp areas that darken and shine, and puddles that lie flat and mirror,
//        placed by a 48 m noise texture and fitted to the low spots painted into each ground set,
//      - a band of grime on the first metre and a half of every wall,
//      - (facades) a painted layer of windows and trim laid over the tiling wall.
// 2. patchCutout: chain-link. Close up the mesh is cut out cleanly; once the wires are thinner than a
//    pixel the cut becomes a fixed screen-door pattern that keeps the average coverage, so a fence
//    neither vanishes nor turns solid with distance. Drawn in the opaque pass: it sorts correctly
//    against smoke, tracers and decals.
//
// Every patched material of one kind shares a single program: the patch text is identical and the
// per-material values travel in uniforms.

import { DataTexture, LinearFilter, NoColorSpace, RGBAFormat, RepeatWrapping, UnsignedByteType } from 'three';
import { fbm } from './noise.js';

/** Metres covered by one repeat of the macro texture. */
export const MACRO_TILE = 48;

/**
 * The macro texture: four independent tileable noise layers.
 *   R puddles (blobs a few metres across)   G damp zones (broad)
 *   B tone                                  A grime / streak variation
 */
export function macroTexture(size) {
  const layers = [fbm(size, size, 14, 14, 3, 301), fbm(size, size, 5, 5, 4, 302), fbm(size, size, 4, 4, 4, 303), fbm(size, size, 20, 20, 3, 304)];
  const data = new Uint8Array(size * size * 4);
  for (let i = 0; i < size * size; i++) {
    for (let c = 0; c < 4; c++) data[i * 4 + c] = Math.round(layers[c][i] * 255);
  }
  const texture = new DataTexture(data, size, size, RGBAFormat, UnsignedByteType);
  texture.wrapS = texture.wrapT = RepeatWrapping;
  // No mipmaps: the content is far coarser than a pixel at any distance the fog lets through.
  texture.magFilter = texture.minFilter = LinearFilter;
  texture.generateMipmaps = false;
  texture.colorSpace = NoColorSpace;
  texture.needsUpdate = true;
  return texture;
}

const WORLD_VERTEX_PARS = /* glsl */ `
varying vec3 vMiPos;
`;

const WORLD_VERTEX = /* glsl */ `
{
  vec4 miWorld = vec4( transformed, 1.0 );
  #ifdef USE_BATCHING
    miWorld = batchingMatrix * miWorld;
  #endif
  #ifdef USE_INSTANCING
    miWorld = instanceMatrix * miWorld;
  #endif
  vMiPos = ( modelMatrix * miWorld ).xyz;
}
`;

const WORLD_FRAGMENT_PARS = /* glsl */ `
varying vec3 vMiPos;
uniform sampler2D miMacro;
uniform vec4 miLook;   // x tone variation, y wetness, z wall grime, w 1 / macro tile in metres
#ifdef MI_FACADE
  uniform sampler2D miFacade;   // rgb paint, a coverage: windows, sills, lintels, the shop band
#endif
`;

// After the albedo map: where are we, what does the macro texture say here.
const WORLD_ALBEDO = /* glsl */ `
#ifdef FLAT_SHADED
  vec3 miN = normalize( cross( dFdx( vMiPos ), dFdy( vMiPos ) ) + vec3( 0.0, 1e-9, 0.0 ) );
  float miUp = smoothstep( 0.6, 0.8, abs( miN.y ) );
#else
  vec3 miN = inverseTransformDirection( normalize( vNormal ), viewMatrix );
  float miUp = smoothstep( 0.6, 0.8, miN.y );
#endif
vec2 miWallUv = vec2( abs( miN.x ) > abs( miN.z ) ? vMiPos.z : vMiPos.x, vMiPos.y );
vec4 miM = texture2D( miMacro, ( miUp > 0.5 ? vMiPos.xz : miWallUv ) * miLook.w );
#ifdef MI_FACADE
  vec4 miF = texture2D( miFacade, vEmissiveMapUv );
  miF.a *= step( vEmissiveMapUv.y, 1.0 );   // above the top floor the wall is bare
  diffuseColor.rgb = mix( diffuseColor.rgb, miF.rgb, miF.a );
#endif
diffuseColor.rgb *= 1.0 + miLook.x * ( miM.b - 0.5 ) * 2.0;
float miGrime = miLook.z * ( 1.0 - miUp ) * ( 1.0 - smoothstep( 0.0, 1.7, vMiPos.y ) ) * ( 0.4 + miM.a );
diffuseColor.rgb *= 1.0 - 0.5 * miGrime;
`;

// After the roughness map: the wet street.
const WORLD_ROUGHNESS = /* glsl */ `
#ifdef USE_ROUGHNESSMAP
  float miLow = texelRoughness.r;
#else
  float miLow = 0.5;
#endif
float miWet = miLook.y * miUp;
float miDamp = miWet * smoothstep( 0.26, 0.66, miM.g + ( miLow - 0.5 ) * 0.5 );
float miPuddle = miWet * smoothstep( 0.66, 0.72, miM.r + ( miLow - 0.5 ) * 0.3 );
roughnessFactor = mix( roughnessFactor, roughnessFactor * 0.5, miDamp );
roughnessFactor = mix( roughnessFactor, 0.05, miPuddle );
diffuseColor.rgb *= 1.0 - 0.18 * miDamp - 0.3 * miPuddle;
roughnessFactor = min( 1.0, roughnessFactor + 0.3 * miGrime );
#ifdef MI_FACADE
  // The emissive layer's alpha tells glass (low) from frames and stone (1).
  float miGlass = clamp( ( 1.0 - texture2D( emissiveMap, vEmissiveMapUv ).a ) * 1.3334, 0.0, 1.0 );
  roughnessFactor = mix( roughnessFactor, mix( 0.72, 0.1, miGlass ), miF.a );
#endif
`;

// After the normal map: standing water and painted trim are flat.
const WORLD_NORMAL = /* glsl */ `
normal = normalize( mix( normal, nonPerturbedNormal, miPuddle * 0.94 ) );
#ifdef MI_FACADE
  normal = normalize( mix( normal, nonPerturbedNormal, miF.a ) );
#endif
`;

function inject(source, anchor, code, where = 'after') {
  if (!source.includes(anchor)) throw new Error(`mats: shader anchor '${anchor}' not found (three.js changed?)`);
  return source.replace(anchor, where === 'after' ? `${anchor}\n${code}` : code);
}

/**
 * @param material  a MeshStandardMaterial that has map, normalMap and roughnessMap
 * @param uniforms  {miMacro: {value: Texture}, miLook: {value: Vector4}, miFacade?: {value: Texture}}
 *                  (the objects are shared: change `.value` and every program using them follows)
 */
export function patchWorld(material, uniforms) {
  if (uniforms.miFacade) material.defines = { ...material.defines, MI_FACADE: '' };
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = inject(inject(shader.vertexShader, '#include <common>', WORLD_VERTEX_PARS), '#include <project_vertex>', WORLD_VERTEX);
    let f = shader.fragmentShader;
    f = inject(f, '#include <common>', WORLD_FRAGMENT_PARS);
    f = inject(f, '#include <map_fragment>', WORLD_ALBEDO);
    f = inject(f, '#include <roughnessmap_fragment>', WORLD_ROUGHNESS);
    f = inject(f, '#include <normal_fragment_maps>', WORLD_NORMAL);
    shader.fragmentShader = f;
  };
  material.customProgramCacheKey = () => 'mi-world-1';
  return material;
}

const CUTOUT_PARS = /* glsl */ `
uniform vec3 miWire;   // x texture size in texels, y wire width in texels, z coverage gain far away
`;

const CUTOUT_TEST = /* glsl */ `
#ifdef USE_ALPHATEST
{
  vec2 miFw = fwidth( vMapUv ) * miWire.x;
  float miFar = smoothstep( 0.45, 1.5, max( miFw.x, miFw.y ) / miWire.y );
  // Interleaved gradient noise: a fixed, well spread screen-door threshold.
  float miDither = fract( 52.9829189 * fract( dot( gl_FragCoord.xy, vec2( 0.06711056, 0.00583715 ) ) ) );
  float miCut = mix( alphaTest, 0.02 + 0.96 * miDither, miFar );
  if ( diffuseColor.a * mix( 1.0, miWire.z, miFar ) < miCut ) discard;
  diffuseColor.a = 1.0;
}
#endif
`;

/**
 * @param material  an alpha-tested MeshStandardMaterial whose map carries coverage in alpha
 * @param uniforms  {miWire: {value: Vector3}}
 */
export function patchCutout(material, uniforms) {
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.fragmentShader = inject(inject(shader.fragmentShader, '#include <common>', CUTOUT_PARS), '#include <alphatest_fragment>', CUTOUT_TEST, 'replace');
  };
  material.customProgramCacheKey = () => 'mi-cutout-1';
  return material;
}
