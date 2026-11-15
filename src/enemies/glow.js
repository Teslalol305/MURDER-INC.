// Everything the enemies emit as light, in two instanced draw calls for the whole pool:
//
//   glow    additive sprites that always face the camera: weapon-light and eye flares, nav strobes,
//           and bolt streaks (a sprite stretched along a segment)
//   discs   the translucent blur discs over the Buzzards' rotors
//
// Both are refilled every frame: begin() … flare() / streak() / disc() … end().
// The sprites are turned toward the camera in the vertex shader, so they are right for whatever camera
// renders them (the player's view or a fixed screenshot camera).

import * as THREE from 'three';

const GLOW_VERTEX = /* glsl */ `
// Instance matrix: column 0 = the streak vector in world space (zero for a round flare),
// column 1.y = the sprite's size, column 3 = its centre.
vec4 glowCentre = modelViewMatrix * vec4( instanceMatrix[ 3 ].xyz, 1.0 );
vec3 glowAxis = ( modelViewMatrix * vec4( instanceMatrix[ 0 ].xyz, 0.0 ) ).xyz;
float glowSize = instanceMatrix[ 1 ].y;
float glowLength = length( glowAxis );
vec3 glowDir = vec3( 1.0, 0.0, 0.0 );
vec3 glowSide = vec3( 0.0, 1.0, 0.0 );
if ( glowLength > 1e-4 ) {
  glowDir = glowAxis / glowLength;
  vec3 glowCross = cross( glowDir, glowCentre.xyz );
  float glowCrossLength = length( glowCross );
  glowSide = glowCrossLength > 1e-5 ? glowCross / glowCrossLength : vec3( 0.0, 1.0, 0.0 );
}
vec4 mvPosition = vec4( glowCentre.xyz + glowDir * ( transformed.x * ( glowLength + glowSize ) ) + glowSide * ( transformed.y * glowSize ), 1.0 );
gl_Position = projectionMatrix * mvPosition;
`;

/** A soft round sprite: a hot core inside a wide halo. */
function glowTexture(size = 64) {
  const data = new Uint8Array(size * size * 4);
  const half = (size - 1) / 2;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const r = Math.min(1, Math.hypot(x - half, y - half) / half);
      const v = 0.72 * Math.exp(-r * r * 14) + 0.28 * (1 - r) ** 2.6;
      const o = (y * size + x) * 4;
      data[o] = data[o + 1] = data[o + 2] = data[o + 3] = Math.round(255 * Math.min(1, v));
    }
  }
  return dataTexture(data, size);
}

/** The rotor disc: faint in the middle, a brighter band where the blade tips blur, a soft edge. */
function discTexture(size = 64) {
  const data = new Uint8Array(size * size * 4);
  const half = (size - 1) / 2;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const r = Math.hypot(x - half, y - half) / half;
      const band = Math.exp(-((r - 0.86) ** 2) * 90);
      const v = r >= 1 ? 0 : (0.22 + 0.25 * r + 0.75 * band) * Math.min(1, (1 - r) * 12);
      const o = (y * size + x) * 4;
      data[o] = data[o + 1] = data[o + 2] = Math.round(255 * Math.min(1, v));
      data[o + 3] = 255;
    }
  }
  return dataTexture(data, size);
}

function dataTexture(data, size) {
  const texture = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  texture.colorSpace = THREE.NoColorSpace;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearFilter;
  texture.needsUpdate = true;
  return texture;
}

function instanced(geometry, material, capacity, name) {
  const mesh = new THREE.InstancedMesh(geometry, material, capacity);
  mesh.name = name;
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  mesh.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(capacity * 3), 3);
  mesh.instanceColor.setUsage(THREE.DynamicDrawUsage);
  mesh.frustumCulled = false; // instances are all over the block
  mesh.castShadow = false;
  mesh.receiveShadow = false;
  mesh.raycast = () => {};
  mesh.count = 0;
  mesh.renderOrder = 5; // after the opaque world and other translucent things near the ground
  return mesh;
}

export function createGlow(scene, capacity = 160, discCapacity = 32) {
  const additive = {
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    fog: false,
  };

  // Premultiplied blending: colour adds as before, and the sprite's own alpha (its falloff) × `occlude`
  // takes that much of the background away first. 0 at night (pure additive glow); by day the core
  // replaces a bright wall instead of washing out on it, so a red eye or bolt still reads red.
  const occlude = { value: 0 };
  let flareScale = 1;
  const glowMaterial = new THREE.MeshBasicMaterial({
    ...additive,
    map: glowTexture(),
    blending: THREE.CustomBlending,
    blendEquation: THREE.AddEquation,
    blendSrc: THREE.OneFactor,
    blendDst: THREE.OneMinusSrcAlphaFactor,
  });
  glowMaterial.name = 'enemy-glow';
  glowMaterial.onBeforeCompile = (shader) => {
    shader.uniforms.uGlowOcclude = occlude;
    shader.vertexShader = shader.vertexShader.replace('#include <project_vertex>', GLOW_VERTEX);
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform float uGlowOcclude;')
      .replace('#include <premultiplied_alpha_fragment>', 'gl_FragColor.a = saturate( gl_FragColor.a * uGlowOcclude );\n#include <premultiplied_alpha_fragment>');
  };
  glowMaterial.customProgramCacheKey = () => 'enemy-glow-2';
  const glow = instanced(new THREE.PlaneGeometry(1, 1), glowMaterial, capacity, 'enemy-glow');

  const discMaterial = new THREE.MeshBasicMaterial({ ...additive, map: discTexture(), side: THREE.DoubleSide });
  discMaterial.forceSinglePass = true;
  discMaterial.name = 'enemy-rotor-disc';
  const discGeometry = new THREE.CircleGeometry(1, 20);
  discGeometry.rotateX(-Math.PI / 2); // lies flat, facing up
  const discs = instanced(discGeometry, discMaterial, discCapacity, 'enemy-rotor-discs');

  if (scene) scene.add(glow, discs);

  const gm = glow.instanceMatrix.array;
  const gc = glow.instanceColor.array;
  const dm = discs.instanceMatrix.array;
  const dc = discs.instanceColor.array;
  let n = 0;
  let nd = 0;

  function put(o, ax, ay, az, size, x, y, z) {
    gm[o] = ax;
    gm[o + 1] = ay;
    gm[o + 2] = az;
    gm[o + 3] = 0;
    gm[o + 4] = 0;
    gm[o + 5] = size;
    gm[o + 6] = 0;
    gm[o + 7] = 0;
    gm[o + 8] = 0;
    gm[o + 9] = 0;
    gm[o + 10] = 1;
    gm[o + 11] = 0;
    gm[o + 12] = x;
    gm[o + 13] = y;
    gm[o + 14] = z;
    gm[o + 15] = 1;
  }

  return {
    glow,
    discs,
    begin() {
      n = 0;
      nd = 0;
    },
    /** Day or night: how much a sprite covers what is behind it (0…1), and a size factor for flares. */
    setLook(cover, scale) {
      occlude.value = cover;
      flareScale = scale;
    },
    /** A round sprite `size` metres across at (x, y, z); colour is linear and may exceed 1 (it blooms). */
    flare(x, y, z, size, r, g, b) {
      if (n >= capacity || size <= 0) return;
      put(n * 16, 0, 0, 0, size * flareScale, x, y, z);
      gc[n * 3] = r;
      gc[n * 3 + 1] = g;
      gc[n * 3 + 2] = b;
      n++;
    },
    /** A sprite stretched from (x0, y0, z0) to (x1, y1, z1), `width` metres thick. */
    streak(x0, y0, z0, x1, y1, z1, width, r, g, b) {
      if (n >= capacity) return;
      put(n * 16, x1 - x0, y1 - y0, z1 - z0, width, (x0 + x1) * 0.5, (y0 + y1) * 0.5, (z0 + z1) * 0.5);
      gc[n * 3] = r;
      gc[n * 3 + 1] = g;
      gc[n * 3 + 2] = b;
      n++;
    },
    /**
     * A rotor disc of `radius` at (x, y, z), tilted with the airframe: `m` is a row-major 3 × 3
     * rotation at offset `o`. `level` scales its brightness.
     */
    disc(x, y, z, radius, m, o, level) {
      if (nd >= discCapacity || level <= 0.01) return;
      const k = nd * 16;
      dm[k] = m[o] * radius;
      dm[k + 1] = m[o + 3] * radius;
      dm[k + 2] = m[o + 6] * radius;
      dm[k + 3] = 0;
      dm[k + 4] = m[o + 1] * radius;
      dm[k + 5] = m[o + 4] * radius;
      dm[k + 6] = m[o + 7] * radius;
      dm[k + 7] = 0;
      dm[k + 8] = m[o + 2] * radius;
      dm[k + 9] = m[o + 5] * radius;
      dm[k + 10] = m[o + 8] * radius;
      dm[k + 11] = 0;
      dm[k + 12] = x;
      dm[k + 13] = y;
      dm[k + 14] = z;
      dm[k + 15] = 1;
      dc[nd * 3] = 0.3 * level;
      dc[nd * 3 + 1] = 0.33 * level;
      dc[nd * 3 + 2] = 0.4 * level;
      nd++;
    },
    end() {
      glow.count = n;
      discs.count = nd;
      glow.visible = n > 0;
      discs.visible = nd > 0;
      if (n > 0) {
        glow.instanceMatrix.needsUpdate = true;
        glow.instanceColor.needsUpdate = true;
      }
      if (nd > 0) {
        discs.instanceMatrix.needsUpdate = true;
        discs.instanceColor.needsUpdate = true;
      }
    },
    get count() {
      return n;
    },
  };
}
