// Small shader patches on top of MeshStandardMaterial (applied once, when a material is created).
//
// 1. patchWorld: for the ground and masonry of the block, which never move. Adds, in world space:
//      - slow tone variation so a tiled wall or street does not read as tiles,
//      - the wet street: damp areas that darken and shine, and puddles that lie flat and mirror,
//        placed by a 48 m noise texture and fitted to the low spots painted into each ground set,
//      - a band of grime on the first metre and a half of every wall,
//      - (facades) a painted layer of windows and trim laid over the tiling wall, read from its rect
//        on a shared facade page.
// 2. patchCutout: chain-link. Close up the mesh is cut out cleanly; once the wires are thinner than a
//    pixel the cut becomes a fixed screen-door pattern that keeps the average coverage, so a fence
//    neither vanishes nor turns solid with distance. Drawn in the opaque pass: it sorts correctly
//    against smoke, tracers and decals.
//
// Every patched material of one kind shares a single program: the patch text is identical and the
// per-material values travel in uniforms.

import { DataTexture, LinearFilter, NoColorSpace, RGBAFormat, RepeatWrapping, UnsignedByteType } from 'three';
import { fbm } from './noise.js';

/** How much of the day sky's blue the diffuse image-based light on the world materials loses (0 … 1). */
export const DAY_IBL_GREY = 0.75;

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
#ifdef MI_FACADE
  varying vec2 vMiUv;
#endif
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
  #ifdef MI_FACADE
    vMiUv = uv;
  #endif
}
`;

const WORLD_FRAGMENT_PARS = /* glsl */ `
varying vec3 vMiPos;
uniform sampler2D miMacro;
uniform vec4 miLook;   // x tone variation, y wetness, z wall grime, w 1 / macro tile in metres
uniform float miDry;   // 0 the night street (soaked), 1 a dry afternoon (wet only where the hydrant reaches)
uniform vec4 miWetLine;   // the open hydrant's reach: a capsule from (x, y) to (z, w) on the ground (x, z)
uniform vec3 miWetSize;   // its radius at either end in metres; z 0 when there is no open hydrant
uniform float miSoak;     // 1 for standing water (asphalt_wet): wet at night, by day inside the reach only
#ifdef MI_FACADE
  varying vec2 vMiUv;           // the geometry's metre UVs
  uniform sampler2D miFacade;   // atlas page: rgb paint, a coverage (windows, sills, lintels, the shop band)
  uniform vec4 miFacadeRect;    // this facade's rect on the page: u0, v0, du, dv
  uniform vec2 miFacadeScale;   // 1 / (width, height) of one repeat in metres
  vec4 miFacadeTexel( sampler2D page, vec2 uv, vec2 dx, vec2 dy ) {
    #if __VERSION__ >= 300
      return textureGrad( page, uv, dx, dy );   // no mip seam where the repeat wraps
    #else
      return texture2D( page, uv );
    #endif
  }
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
  // The window layer repeats along the wall inside its atlas rect; the glow layer (same layout) is
  // read here too: its alpha tells glass from frames below, its rgb is the emissive.
  vec2 miFF = vMiUv * miFacadeScale;
  vec2 miFUv = miFacadeRect.xy + vec2( fract( miFF.x ), clamp( miFF.y, 0.0, 1.0 ) ) * miFacadeRect.zw;
  vec2 miFdx = dFdx( miFF ) * miFacadeRect.zw;
  vec2 miFdy = dFdy( miFF ) * miFacadeRect.zw;
  float miFTop = step( miFF.y, 1.0 );   // above the top floor the wall is bare
  vec4 miF = miFacadeTexel( miFacade, miFUv, miFdx, miFdy );
  vec4 miE = miFacadeTexel( emissiveMap, miFUv, miFdx, miFdy );
  miF.a *= miFTop;
  diffuseColor.rgb = mix( diffuseColor.rgb, miF.rgb, miF.a );
#endif
// The tone variation is gentler on the sunlit ground than in the lamplight.
diffuseColor.rgb *= 1.0 + miLook.x * ( 1.0 - 0.4 * miDry * miUp ) * ( miM.b - 0.5 ) * 2.0;
float miGrime = miLook.z * ( 1.0 - miUp ) * ( 1.0 - smoothstep( 0.0, 1.7, vMiPos.y ) ) * ( 0.4 + miM.a );
diffuseColor.rgb *= 1.0 - 0.5 * miGrime;
`;

// After the roughness map: the wet street.
const WORLD_ROUGHNESS = /* glsl */ `
#if defined( USE_ROUGHNESSMAP ) && defined( MI_PACKED )
  float miLow = texelRoughness.b;
#elif defined( USE_ROUGHNESSMAP )
  float miLow = texelRoughness.r;
#else
  float miLow = 0.5;
#endif
float miWet = miLook.y * miUp;
// By day the street has dried except where the open hydrant reaches (a capsule with a ragged edge).
vec2 miPa = vMiPos.xz - miWetLine.xy;
vec2 miBa = miWetLine.zw - miWetLine.xy;
float miT = clamp( dot( miPa, miBa ) / max( dot( miBa, miBa ), 1e-4 ), 0.0, 1.0 );
float miEdge = length( miPa - miBa * miT ) - mix( miWetSize.x, miWetSize.y, miT ) + 1.2 * ( miM.g - 0.5 );
float miReach = miWetSize.z * ( 1.0 - smoothstep( -0.5, 0.5, miEdge ) );
float miD = miDry * ( 1.0 - miReach );   // 1 where the ground is dry, 0 where it is as wet as at night
// Dried ground: the glossy low spots painted into the roughness map go matte.
roughnessFactor = mix( roughnessFactor, max( roughnessFactor, 0.86 ), miD * max( miWet, miSoak * miUp ) );
float miDamp = miWet * ( 1.0 - miD ) * smoothstep( 0.26, 0.66, miM.g + ( miLow - 0.5 ) * 0.5 );
float miPuddle = miWet * ( 1.0 - miD ) * smoothstep( 0.66, 0.72, miM.r + ( miLow - 0.5 ) * 0.3 );
roughnessFactor = mix( roughnessFactor, roughnessFactor * 0.5, miDamp );
roughnessFactor = mix( roughnessFactor, 0.05, miPuddle );
// Standing water takes the dry street's albedo by day (mats retints it): darken it where it is still wet.
diffuseColor.rgb *= 1.0 - 0.18 * miDamp - 0.3 * miPuddle - 0.6 * miSoak * miDry * miReach;
roughnessFactor = min( 1.0, roughnessFactor + 0.3 * miGrime );
#ifdef MI_FACADE
  // The emissive layer's alpha tells glass (low) from frames and stone (1).
  float miGlass = clamp( ( 1.0 - miE.a ) * 1.3334, 0.0, 1.0 );
  roughnessFactor = mix( roughnessFactor, mix( 0.72, 0.1, miGlass ), miF.a );
#endif
`;

// After the normal map: standing water and painted trim are flat.
// The facade's glow comes from its own rect on the page, not from the emissive map's transform.
const WORLD_EMISSIVE = /* glsl */ `
#ifdef MI_FACADE
  totalEmissiveRadiance *= miE.rgb * miFTop;
#else
  #include <emissivemap_fragment>
#endif
`;

// After the image-based light is gathered: by day the sky's diffuse light reaches the street and the
// walls without its blue cast (the deck of the El and the facades hide most of the blue overhead, which
// the environment, captured in the open, cannot know). Reflections keep the sky's colour.
const WORLD_IBL = /* glsl */ `
#if defined( RE_IndirectDiffuse ) && defined( USE_ENVMAP ) && defined( ENVMAP_TYPE_CUBE_UV )
  iblIrradiance = mix( iblIrradiance, vec3( dot( iblIrradiance, vec3( 0.2126, 0.7152, 0.0722 ) ) ), MI_IBL_GREY * miDry );
#endif
`;

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
 * @param uniforms  {miMacro: {value: Texture}, miLook: {value: Vector4}, miDry: {value: number},
 *                  and for a facade miFacade: {value: Texture}, miFacadeRect: {value: Vector4}, miFacadeScale: {value: Vector2}}
 *                  (the objects are shared: change `.value` and every program using them follows)
 */
export function patchWorld(material, uniforms, packed = false) {
  if (uniforms.miFacade) material.defines = { ...material.defines, MI_FACADE: '' };
  // A packed set (see patchPacked) carries the water level in blue instead of a separate ORM's red.
  if (packed) material.defines = { ...material.defines, MI_PACKED: '' };
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = inject(inject(shader.vertexShader, '#include <common>', WORLD_VERTEX_PARS), '#include <project_vertex>', WORLD_VERTEX);
    let f = shader.fragmentShader;
    f = inject(f, '#include <common>', WORLD_FRAGMENT_PARS);
    f = inject(f, '#include <map_fragment>', WORLD_ALBEDO);
    if (packed) {
      f = inject(f, '#include <roughnessmap_fragment>', PACKED_ROUGHNESS + WORLD_ROUGHNESS, 'replace');
      f = inject(f, '#include <normal_fragment_maps>', PACKED_NORMAL + WORLD_NORMAL, 'replace');
    } else {
      f = inject(f, '#include <roughnessmap_fragment>', WORLD_ROUGHNESS);
      f = inject(f, '#include <normal_fragment_maps>', WORLD_NORMAL);
    }
    f = inject(f, '#include <emissivemap_fragment>', WORLD_EMISSIVE, 'replace');
    f = inject(f, '#include <lights_fragment_maps>', WORLD_IBL.replace('MI_IBL_GREY', DAY_IBL_GREY.toFixed(3)));
    shader.fragmentShader = f;
  };
  material.customProgramCacheKey = () => 'mi-world-3';
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

// 3. patchPacked: surface sets whose normal map and roughness / metalness share one texture
//    (R, G normal x, y; B metalness, or the water level for ground and masonry sets; A roughness): one
//    texture where there were two. The normal's z is rebuilt from x and y. patchWorld(…, packed) does
//    the same for the world materials.
const PACKED_ROUGHNESS = /* glsl */ `
float roughnessFactor = roughness;
#ifdef USE_ROUGHNESSMAP
  vec4 texelRoughness = texture2D( roughnessMap, vRoughnessMapUv );
  roughnessFactor *= texelRoughness.a;
#endif
`;

const PACKED_NORMAL = /* glsl */ `
#ifdef USE_NORMALMAP_TANGENTSPACE
  vec3 mapN = vec3( texture2D( normalMap, vNormalMapUv ).xy * 2.0 - 1.0, 0.0 );
  mapN.z = sqrt( max( 1e-4, 1.0 - dot( mapN.xy, mapN.xy ) ) );
  mapN.xy *= normalScale;
  normal = normalize( tbn * mapN );
#else
  #include <normal_fragment_maps>
#endif
`;

/** @param material  a MeshStandardMaterial whose normalMap, roughnessMap and metalnessMap are one packed texture */
export function patchPacked(material) {
  material.onBeforeCompile = (shader) => {
    let f = shader.fragmentShader;
    f = inject(f, '#include <roughnessmap_fragment>', PACKED_ROUGHNESS, 'replace');
    f = inject(f, '#include <normal_fragment_maps>', PACKED_NORMAL, 'replace');
    shader.fragmentShader = f;
  };
  material.customProgramCacheKey = () => 'mi-packed-1';
  return material;
}
