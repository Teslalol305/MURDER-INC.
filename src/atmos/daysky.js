// The day sky: one shader on a box around the camera, drawn at the far plane (like the night sky in
// sky.js, which it replaces while `atmos.time` is 'day'; both are built at boot, one is shown).
//
// A summer afternoon: deep blue overhead paling to a hazy white-blue at the horizon, the sun high in the
// west-south-west with a soft aureole, a few bright cumulus drifting on a flat layer, lit on their sun
// side and grey underneath. Below a few degrees of elevation the sky sinks into the same haze the fog
// uses, so the far city and the ends of the avenue dissolve into it without a seam.

import * as THREE from 'three';

const VERTEX = /* glsl */ `
varying vec3 vDir;
void main() {
	vDir = position;
	vec4 p = projectionMatrix * vec4( mat3( viewMatrix ) * position, 1.0 );
	gl_Position = p.xyww;
}
`;

const FRAGMENT = (hazeGLSL) => /* glsl */ `
uniform float uTime;
uniform vec3 uZenith;
uniform vec3 uHorizon;
uniform float uHorizonPower;
uniform vec3 uSunDir;
uniform vec3 uSunColor;
uniform float uSunCos;
uniform float uSunDisc;          // 0 while the sky is captured into the environment
uniform float uGain;             // the capture may take the sky darker than it is drawn
uniform vec3 uAureole;
uniform vec3 uAureoleTight;
uniform float uCloudAmount;
uniform float uCoverage;
uniform float uSoftness;
uniform float uCloudScale;
uniform vec2 uCloudDrift;
uniform vec3 uCloudLit;
uniform vec3 uCloudShade;
varying vec3 vDir;
${hazeGLSL}

float hash21( vec2 p ) {
	vec3 q = fract( vec3( p.xyx ) * 0.1031 );
	q += dot( q, q.yzx + 33.33 );
	return fract( ( q.x + q.y ) * q.z );
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
	for ( int i = 0; i < 5; i ++ ) {
		s += a * noise( p );
		p = p * 2.07 + vec2( 17.3, 9.1 );
		a *= 0.48;
	}
	return s;
}
// Cumulus: big rounded heaps (low frequencies dominate), cauliflower detail only at the rim.
float heap( vec2 p ) {
	float base = noise( p * 0.5 ) * 0.62 + noise( p * 1.1 + 5.2 ) * 0.38;
	return base + 0.32 * ( fbm( p * 2.3 ) - 0.47 );
}

void main() {
	vec3 d = normalize( vDir );
	float up = clamp( d.y, 0.0, 1.0 );
	float east = d.x / max( length( d.xz ), 1e-4 );

	vec3 col = mix( uHorizon, uZenith, pow( up, uHorizonPower ) );

	// The sun: a hard disc and a soft aureole around it (forward scattering in the haze).
	float mu = dot( d, uSunDir );
	float m = max( mu, 0.0 );
	col += uAureole * pow( m, 6.0 ) * ( 0.6 + 0.4 * ( 1.0 - up ) ) + uAureoleTight * pow( m, 90.0 );
	float disc = smoothstep( uSunCos - 0.00002, uSunCos + 0.00002, mu );

	// Cumulus on a flat layer overhead, drifting.
	float cloud = 0.0;
	vec3 cloudColor = vec3( 0.0 );
	if ( d.y > 0.0 ) {
		vec2 cp = d.xz / ( d.y + 0.1 ) * uCloudScale + uCloudDrift * uTime;
		float n = heap( cp );
		cloud = smoothstep( uCoverage, uCoverage + uSoftness, n ) * uCloudAmount * smoothstep( 0.02, 0.2, d.y );
		// Light from the sun's side of each heap: sample the field a step toward the sun.
		vec2 toSun = normalize( uSunDir.xz + 1e-4 ) * 0.22;
		float lit = clamp( 0.62 + ( n - heap( cp + toSun ) ) * 3.2, 0.0, 1.0 );
		float thick = smoothstep( uCoverage, uCoverage + 0.42, n );
		cloudColor = mix( uCloudShade, uCloudLit, lit * ( 1.0 - 0.45 * thick ) + 0.12 );
		// Silver lining toward the sun.
		cloudColor += uSunColor * 0.012 * pow( m, 5.0 ) * ( 1.0 - thick );
		// Far clouds sink into the blue-white of the horizon.
		cloudColor = mix( cloudColor, uHorizon * 1.15, 1.0 - smoothstep( 0.05, 0.4, d.y ) );
	}
	col = mix( col, cloudColor, cloud );
	col += uSunColor * disc * uSunDisc * ( 1.0 - cloud );

	// Sink into the haze at the horizon (and below it: the dome is also the "ground" beyond the world).
	col = mix( uFogColor * hazeTint( east ), col, smoothstep( - 0.02, 0.09, d.y ) );

	gl_FragColor = vec4( col * uGain, 1.0 );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}
`;

const color = (rgb, gain = 1) => new THREE.Color().setRGB(rgb[0] * gain, rgb[1] * gain, rgb[2] * gain);

/**
 * @param {object} sunDirection  the way the sunlight travels (look.times.day.sun.direction)
 */
export function createDaySky(G, haze, uTime, sunDirection) {
  const cfg = G.config.look.daySky;
  const toSun = new THREE.Vector3().fromArray(sunDirection).normalize().negate();

  const material = new THREE.ShaderMaterial({
    name: 'atmos-day-sky',
    uniforms: {
      uTime,
      ...haze.uniforms,
      uZenith: { value: color(cfg.zenith) },
      uHorizon: { value: color(cfg.horizon) },
      uHorizonPower: { value: cfg.horizonPower },
      uSunDir: { value: toSun },
      uSunColor: { value: color(cfg.sun.radiance) },
      uSunCos: { value: Math.cos(cfg.sun.radius) },
      uSunDisc: { value: 1 },
      uGain: { value: 1 },
      uAureole: { value: color(cfg.sun.aureole) },
      uAureoleTight: { value: color(cfg.sun.aureoleTight) },
      uCloudAmount: { value: cfg.clouds.amount },
      uCoverage: { value: cfg.clouds.coverage },
      uSoftness: { value: cfg.clouds.softness },
      uCloudScale: { value: cfg.clouds.scale },
      uCloudDrift: { value: new THREE.Vector2().fromArray(cfg.clouds.drift) },
      uCloudLit: { value: color(cfg.clouds.lit) },
      uCloudShade: { value: color(cfg.clouds.shade) },
    },
    vertexShader: VERTEX,
    fragmentShader: FRAGMENT(haze.glsl),
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
  });

  const dome = new THREE.Mesh(new THREE.BoxGeometry(2, 2, 2), material);
  dome.name = 'atmos-day-sky';
  dome.frustumCulled = false;
  dome.renderOrder = 1000;
  dome.matrixAutoUpdate = false;

  return {
    dome,
    material,
    sunDir: toSun,
    /** For the environment capture: the disc would only add fireflies to the blurred map. */
    setCapture(on, gain = 1) {
      material.uniforms.uSunDisc.value = on ? 0 : 1;
      material.uniforms.uGain.value = on ? gain : 1;
    },
  };
}
