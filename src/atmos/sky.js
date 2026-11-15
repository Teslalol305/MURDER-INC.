// The night sky: one shader on a box around the camera, drawn at the far plane.
//
// Deep blue-black overhead, the city glowing sodium-orange on the horizon (strongest in the west, toward
// Manhattan), thin cloud wisps that catch that glow from below, a few stars, a low gibbous moon. Below a
// few degrees of elevation the sky sinks into the same haze colour the fog uses, so the far city and the
// ends of the avenue dissolve into it without a seam.
//
// The same material is captured once into a PMREM environment (createEnvironment) together with stand-ins
// for the block: without it metal, glass and wet asphalt have nothing to mirror.

import * as THREE from 'three';

const VERTEX = /* glsl */ `
varying vec3 vDir;
void main() {
	vDir = position;
	// Rotation only: the box stays centred on whichever camera draws it. z = w puts it on the far plane.
	vec4 p = projectionMatrix * vec4( mat3( viewMatrix ) * position, 1.0 );
	gl_Position = p.xyww;
}
`;

const FRAGMENT = (hazeGLSL) => /* glsl */ `
uniform float uTime;
uniform vec3 uZenith;
uniform vec3 uHorizon;
uniform vec3 uGlowWest;
uniform vec3 uGlowEast;
uniform vec2 uGlowHeight;
uniform float uCloudAmount;
uniform float uCloudScale;
uniform vec2 uCloudStretch;
uniform vec2 uCloudDrift;
uniform float uCloudLit;
uniform vec3 uCloudMoon;
uniform float uStarDensity;
uniform float uStarBrightness;
uniform vec3 uMoonDir;
uniform vec3 uMoonRight;
uniform vec3 uMoonUp;
uniform float uMoonRadius;
uniform vec3 uMoonColor;
uniform float uMoonHalo;
varying vec3 vDir;
${hazeGLSL}

float hash21( vec2 p ) {
	vec3 q = fract( vec3( p.xyx ) * 0.1031 );
	q += dot( q, q.yzx + 33.33 );
	return fract( ( q.x + q.y ) * q.z );
}
float hash31( vec3 p ) {
	p = fract( p * 0.1031 );
	p += dot( p, p.zyx + 31.32 );
	return fract( ( p.x + p.y ) * p.z );
}
float noise( vec2 p ) {
	vec2 i = floor( p );
	vec2 f = fract( p );
	f = f * f * ( 3.0 - 2.0 * f );
	return mix( mix( hash21( i ), hash21( i + vec2( 1.0, 0.0 ) ), f.x ),
		mix( hash21( i + vec2( 0.0, 1.0 ) ), hash21( i + vec2( 1.0, 1.0 ) ), f.x ), f.y );
}
float fbm( vec2 p ) {
	float a = 0.5;
	float s = 0.0;
	for ( int i = 0; i < 4; i ++ ) {
		s += a * noise( p );
		p = p * 2.03 + vec2( 17.3, 9.1 );
		a *= 0.5;
	}
	return s;
}

void main() {
	vec3 d = normalize( vDir );
	float up = clamp( d.y, 0.0, 1.0 );
	float east = d.x / max( length( d.xz ), 1e-4 );      // -1 looking west ... +1 looking east
	float west = 0.5 - 0.5 * east;
	float lobe = west * west * ( 3.0 - 2.0 * west );      // how much of the western glow this direction gets

	vec3 col = mix( uHorizon, uZenith, pow( up, 0.42 ) );

	// City glow: hugs the horizon, taller and far stronger toward the west.
	vec3 glowColor = mix( uGlowEast, uGlowWest, lobe );
	float glow = exp( - up / mix( uGlowHeight.x, uGlowHeight.y, lobe ) );
	col += glowColor * glow;

	// The moon: a gibbous disc with a soft halo.
	float cosMoon = dot( d, uMoonDir );
	vec2 q = vec2( dot( d, uMoonRight ), dot( d, uMoonUp ) ) / uMoonRadius;
	float r2 = dot( q, q );
	float moonHalo = 0.0;
	vec3 moon = vec3( 0.0 );
	if ( cosMoon > 0.0 ) {
		float disc = 1.0 - smoothstep( 0.86, 1.0, r2 );
		float limb = sqrt( max( 1.0 - r2, 0.0 ) );
		vec2 qr = vec2( q.x * 0.82 + q.y * 0.57, q.y * 0.82 - q.x * 0.57 );   // tilt the terminator
		float lit = smoothstep( - 0.1, 0.1, qr.x + 0.52 * sqrt( max( 1.0 - qr.y * qr.y, 0.0 ) ) );
		float maria = 1.0 - 0.3 * smoothstep( 0.45, 0.75, noise( q * 2.1 + 11.0 ) );
		moon = uMoonColor * disc * ( 0.06 + 0.94 * lit ) * ( 0.72 + 0.28 * limb ) * maria;
		float ang = sqrt( r2 ) * uMoonRadius;
		moonHalo = uMoonHalo * ( exp( - ang * 26.0 ) + 0.16 * exp( - ang * 5.5 ) );
	}

	// Stars: a few, washed out by the glow.
	vec3 sp = d * 210.0;
	vec3 cell = floor( sp );
	float rnd = hash31( cell );
	float star = step( 1.0 - uStarDensity, rnd ) * smoothstep( 0.4, 0.05, length( fract( sp ) - 0.5 ) );
	float twinkle = 0.7 + 0.3 * sin( uTime * ( 1.3 + rnd * 4.0 ) + rnd * 60.0 );
	float starShow = smoothstep( 0.1, 0.45, d.y ) * ( 1.0 - 0.8 * glow );
	vec3 stars = vec3( 0.85, 0.92, 1.0 ) * star * twinkle * starShow * uStarBrightness * ( 0.25 + 3.0 * fract( rnd * 191.3 ) * fract( rnd * 191.3 ) );

	// Cloud wisps on a flat layer overhead, drifting, lit from below by the city and rimmed by the moon.
	float cloud = 0.0;
	if ( d.y > 0.0 ) {
		vec2 cp = d.xz / ( d.y + 0.2 ) * uCloudStretch * uCloudScale + uCloudDrift * uTime;
		float n = fbm( cp ) + 0.35 * noise( cp * 0.37 - 4.0 );
		cloud = smoothstep( 0.6, 1.02, n ) * uCloudAmount * smoothstep( 0.0, 0.14, d.y );
	}
	vec3 cloudColor = glowColor * uCloudLit * ( 0.06 + exp( - up * 4.5 ) )
		+ uCloudMoon * ( 1.0 + 9.0 * pow( max( cosMoon, 0.0 ), 14.0 ) );

	col += stars * ( 1.0 - cloud );
	col += moon * ( 1.0 - 0.75 * cloud ) + uMoonColor * 0.06 * moonHalo * ( 1.0 + 2.0 * cloud );
	col = mix( col, cloudColor, cloud * 0.8 );

	// Sink into the haze at the horizon (and below it: the dome is also the "ground" beyond the world).
	col = mix( uFogColor * hazeTint( east ), col, smoothstep( - 0.015, 0.1, d.y ) );

	gl_FragColor = vec4( col, 1.0 );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}
`;

const color = (rgb, gain = 1) => new THREE.Color().setRGB(rgb[0] * gain, rgb[1] * gain, rgb[2] * gain);

export function createSky(G, haze, uTime) {
  const cfg = G.config.look.sky;

  const moonDir = new THREE.Vector3().fromArray(cfg.moon.direction).normalize();
  const moonRight = new THREE.Vector3().crossVectors(new THREE.Vector3(0, 1, 0), moonDir).normalize();
  const moonUp = new THREE.Vector3().crossVectors(moonDir, moonRight);

  const material = new THREE.ShaderMaterial({
    name: 'atmos-sky',
    uniforms: {
      uTime,
      ...haze.uniforms,
      uZenith: { value: color(cfg.zenithRadiance) },
      uHorizon: { value: color(cfg.horizonRadiance) },
      uGlowWest: { value: color(cfg.glowWest) },
      uGlowEast: { value: color(cfg.glowEast) },
      uGlowHeight: { value: new THREE.Vector2().fromArray(cfg.glowHeight) },
      uCloudAmount: { value: cfg.clouds.amount },
      uCloudScale: { value: cfg.clouds.scale },
      uCloudStretch: { value: new THREE.Vector2().fromArray(cfg.clouds.stretch) },
      uCloudDrift: { value: new THREE.Vector2().fromArray(cfg.clouds.drift) },
      uCloudLit: { value: cfg.clouds.litByGlow },
      uCloudMoon: { value: color(cfg.clouds.moonlit) },
      uStarDensity: { value: cfg.stars.density },
      uStarBrightness: { value: cfg.stars.brightness },
      uMoonDir: { value: moonDir },
      uMoonRight: { value: moonRight },
      uMoonUp: { value: moonUp },
      uMoonRadius: { value: cfg.moon.radius },
      uMoonColor: { value: color(cfg.moon.radiance) },
      uMoonHalo: { value: cfg.moon.halo },
    },
    vertexShader: VERTEX,
    fragmentShader: FRAGMENT(haze.glsl),
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
  });

  const dome = new THREE.Mesh(new THREE.BoxGeometry(2, 2, 2), material);
  dome.name = 'atmos-sky';
  dome.frustumCulled = false; // the vertex shader moves it: its bounds mean nothing
  dome.renderOrder = 1000; // after the opaque world, so the depth test spares the hidden sky
  dome.matrixAutoUpdate = false;

  return { dome, material, moonDir };
}

/**
 * Captures the image-based light: the sky, a dark band of facades around the probe, the street, and a
 * bright blob in the direction of every lamp (`blobs`: [{dir: Vector3, color: Color (radiance), size}],
 * size in radians). Returns the PMREM render target; its texture goes to render.setEnvironment().
 */
export function createEnvironment(G, sky, blobs) {
  const cfg = G.config.look.env;
  const R = 60; // radius of the stand-in block around the probe
  const env = new THREE.Scene();
  const disposables = [];
  const track = (item) => {
    disposables.push(item);
    return item;
  };

  // The capture has no depth buffer: things are painted in renderOrder, far to near.
  const add = (mesh, order) => {
    mesh.renderOrder = order;
    env.add(mesh);
    return mesh;
  };

  add(new THREE.Mesh(sky.dome.geometry, sky.material), 0).frustumCulled = false;

  // Facades: a ring that rises 30° to the north and south and leaves the avenue open east and west.
  {
    const segments = 64;
    const position = [];
    const index = [];
    for (let i = 0; i <= segments; i++) {
      const a = (i / segments) * Math.PI * 2;
      const x = Math.cos(a) * R;
      const z = Math.sin(a) * R;
      const alongAvenue = Math.abs(Math.cos(a)); // 1 looking east or west
      const rise = THREE.MathUtils.lerp(0.62, 0.05, THREE.MathUtils.smoothstep(alongAvenue, 0.72, 0.985));
      const jag = 0.85 + 0.3 * Math.abs(Math.sin(a * 11.3) * Math.cos(a * 4.7)); // an uneven roof line
      position.push(x, -3, z, x, R * rise * jag, z);
      if (i < segments) index.push(i * 2, i * 2 + 1, i * 2 + 2, i * 2 + 1, i * 2 + 3, i * 2 + 2);
    }
    const geo = track(new THREE.BufferGeometry());
    geo.setAttribute('position', new THREE.Float32BufferAttribute(position, 3));
    geo.setIndex(index);
    const mat = track(new THREE.MeshBasicMaterial({ color: color(cfg.facade, cfg.intensity), side: THREE.DoubleSide, fog: false }));
    add(new THREE.Mesh(geo, mat), 1);
  }

  // The street.
  {
    const geo = track(new THREE.CircleGeometry(R * 1.02, 32));
    const mat = track(new THREE.MeshBasicMaterial({ color: color(cfg.street, cfg.intensity), fog: false }));
    const mesh = new THREE.Mesh(geo, mat);
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.y = -1.4;
    add(mesh, 2);
  }

  // Lamps: soft discs that face the probe (glass mirrors the environment sharply: no hard-edged blobs).
  {
    const disc = track(new THREE.CircleGeometry(1, 16));
    const origin = new THREE.Vector3();
    for (const blob of blobs) {
      const mat = track(
        new THREE.ShaderMaterial({
          uniforms: { uColor: { value: blob.color.clone().multiplyScalar(cfg.intensity) } },
          vertexShader: /* glsl */ `
varying vec2 vP;
void main() {
	vP = position.xy;
	gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
}`,
          fragmentShader: /* glsl */ `
uniform vec3 uColor;
varying vec2 vP;
void main() {
	float r2 = dot( vP, vP );
	float fall = max( 1.0 - r2, 0.0 );
	gl_FragColor = vec4( uColor * fall * fall * exp( - r2 * 3.0 ), 1.0 );
}`,
          transparent: true,
          blending: THREE.AdditiveBlending,
          premultipliedAlpha: true,
          depthTest: false,
          depthWrite: false,
          fog: false,
        }),
      );
      const mesh = new THREE.Mesh(disc, mat);
      mesh.position.copy(blob.dir).multiplyScalar(R * 0.9);
      mesh.scale.setScalar(R * 0.9 * blob.size);
      mesh.lookAt(origin);
      add(mesh, 3);
    }
  }

  const pmrem = new THREE.PMREMGenerator(G.renderer);
  const target = pmrem.fromScene(env, 0, 0.1, R * 4);
  pmrem.dispose();
  for (const item of disposables) item.dispose();
  return target;
}
