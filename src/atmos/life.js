// Small things that move, so the block is never a still picture:
//
//   steam    columns of soft puffs over the manholes at `level.steam` (always there; the fx module's own
//            steam emitters are asked for on top, see hookEmitters)
//   motes    moths around the brightest lamps and dust hanging in their light (medium quality and up)
//   paper    a few sheets that skitter down the avenue on the wind and get kicked up by the train
//   hydrant  the arc of water and the mist from the open hydrant, when the level has one
//
// Steam, motes and spray are animated entirely in their vertex shaders; only the paper is simulated.

import * as THREE from 'three';
import { clamp, damp } from '../core/util.js';
import { paperTexture } from './textures.js';

const OUTPUT = /* glsl */ `
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
`;

// ------------------------------------------------------------------------------------------------
// Steam
// ------------------------------------------------------------------------------------------------

/**
 * Billboard puffs that rise from a point, widen, drift and fade, each on its own phase.
 * columns: [{pos, tint: [r,g,b], height, spread, size: [from, to], rise (m/s), alpha, puffs}]
 */
function buildSteam(G, columns, haze, shared) {
  const position = [];
  const aCorner = [];
  const aPuff = [];
  const aShape = [];
  const aTint = [];
  const index = [];
  const CORNERS = [-1, -1, 1, -1, 1, 1, -1, 1];
  const rng = G.rng.fork('atmos-steam');
  let count = 0;
  for (const col of columns) {
    const life = col.height / col.rise;
    for (let p = 0; p < col.puffs; p++) {
      const phase = (p + rng.next() * 0.6) / col.puffs;
      const angle = rng.range(0, Math.PI * 2);
      const jitter = rng.range(0.75, 1.25);
      const rank = ((p * 0.61803) % 1) * 0.999; // which puffs go first when quality thins the column
      const base = count * 4;
      for (let c = 0; c < 4; c++) {
        position.push(col.pos.x, col.pos.y, col.pos.z);
        aCorner.push(CORNERS[c * 2], CORNERS[c * 2 + 1]);
        aPuff.push(phase, life, angle, col.spread * jitter);
        aShape.push(col.size[0] * jitter, col.size[1] * jitter, col.height, col.alpha);
        aTint.push(col.tint[0], col.tint[1], col.tint[2], rank);
      }
      index.push(base, base + 1, base + 2, base, base + 2, base + 3);
      count++;
    }
  }
  if (!count) return null;

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(position, 3));
  geo.setAttribute('aCorner', new THREE.Float32BufferAttribute(aCorner, 2));
  geo.setAttribute('aPuff', new THREE.Float32BufferAttribute(aPuff, 4));
  geo.setAttribute('aShape', new THREE.Float32BufferAttribute(aShape, 4));
  geo.setAttribute('aTint', new THREE.Float32BufferAttribute(aTint, 4));
  geo.setIndex(index);

  const material = new THREE.ShaderMaterial({
    name: 'atmos-steam',
    uniforms: { ...haze.uniforms, uTime: shared.uTime, uWind: shared.uWind, uShow: { value: 1 }, uDayTint: { value: new THREE.Vector4(1, 1, 1, 0) }, uAlphaScale: { value: 1 } },
    vertexShader: /* glsl */ `
attribute vec2 aCorner;
attribute vec4 aPuff;    // phase, life (s), drift angle, sideways spread (m)
attribute vec4 aShape;   // size at birth, size at the top, column height, opacity
attribute vec4 aTint;    // colour, and a rank 0..1 (puffs above uShow are not drawn)
uniform float uTime;
uniform vec2 uWind;
uniform float uShow;     // fraction of the puffs that are drawn (quality)
uniform vec4 uDayTint;   // by day every column is this colour (w = 1), sunlit, not lamp-lit
uniform float uAlphaScale;
varying vec2 vCorner;
varying vec4 vColor;
varying float vSeed;
${haze.glsl}
void main() {
	float t = fract( uTime / aPuff.y + aPuff.x );
	float rise = 1.0 - ( 1.0 - t ) * ( 1.0 - t );          // quick out of the grate, slowing as it cools
	vec3 centre = position;
	centre.y += aShape.z * rise;
	vec2 drift = vec2( cos( aPuff.z ), sin( aPuff.z ) ) * aPuff.w * t
		+ uWind * aPuff.y * t * t * 0.55
		+ 0.18 * vec2( sin( uTime * 0.9 + aPuff.z * 3.0 ), cos( uTime * 0.7 + aPuff.z * 5.0 ) ) * t;
	centre.xz += drift;
	float size = mix( aShape.x, aShape.y, sqrt( t ) );

	vec4 mv = viewMatrix * vec4( centre, 1.0 );
	float alpha = aShape.w * uAlphaScale * smoothstep( 0.0, 0.1, t ) * ( 1.0 - smoothstep( 0.45, 1.0, t ) );
	alpha *= step( aTint.w, uShow );
	alpha *= smoothstep( 0.6, 2.4, - mv.z );                 // never a wall of white in the face
	float through = hazeT( - mv.z, centre.xz );
	vColor = vec4( mix( hazeColor( centre.xz ), mix( aTint.rgb, uDayTint.rgb, uDayTint.w ), through ), alpha * through );
	vCorner = aCorner;
	vSeed = aPuff.z + floor( uTime / aPuff.y + aPuff.x ) * 7.31;
	mv.xy += aCorner * size;
	gl_Position = projectionMatrix * mv;
}`,
    fragmentShader: /* glsl */ `
varying vec2 vCorner;
varying vec4 vColor;
varying float vSeed;
void main() {
	float r2 = dot( vCorner, vCorner );
	float fall = max( 1.0 - r2, 0.0 );
	// A soft ball with a lumpy edge.
	float lumps = 0.78 + 0.22 * sin( vCorner.x * 5.3 + vSeed ) * sin( vCorner.y * 4.7 - vSeed * 1.7 );
	float a = vColor.a * fall * fall * lumps;
	gl_FragColor = vec4( vColor.rgb * a, a );
	${OUTPUT}
}`,
    transparent: true,
    premultipliedAlpha: true,
    depthWrite: false,
    fog: false,
  });
  const mesh = new THREE.Mesh(geo, material);
  mesh.name = 'atmos-steam';
  mesh.frustumCulled = false;
  mesh.matrixAutoUpdate = false;
  mesh.renderOrder = 5;
  return mesh;
}

// ------------------------------------------------------------------------------------------------
// Moths and dust
// ------------------------------------------------------------------------------------------------

function buildMotes(G, lamps, haze, shared) {
  const cfg = G.config.look.life.motes;
  const rng = G.rng.fork('atmos-motes');
  // The brightest lamps that hang in the open air.
  const chosen = lamps
    .filter((l) => !l.virtual && (l.kind === 'street' || l.kind === 'flood' || l.kind === 'el'))
    .sort((a, b) => b.intensity - a.intensity || a.index - b.index)
    .slice(0, cfg.lamps);
  if (!chosen.length) return null;

  const position = [];
  const aOrbit = [];
  const aColor = [];
  for (const lamp of chosen) {
    for (let i = 0; i < cfg.perLamp; i++) {
      const moth = i < cfg.perLamp * 0.45;
      position.push(lamp.pos.x, lamp.pos.y - (moth ? 0.25 : rng.range(0.6, 3.2)), lamp.pos.z);
      // radius, angular speed (moths dart, dust hangs), phase, bob
      aOrbit.push(moth ? rng.range(0.25, 0.9) : rng.range(0.4, 2.2), (moth ? rng.range(2.2, 5.5) : rng.range(0.08, 0.3)) * rng.sign(), rng.next(), moth ? 0.35 : 0.12);
      const k = cfg.radiance * (moth ? 1 : 0.4);
      aColor.push(lamp.color.r * k, lamp.color.g * k, lamp.color.b * k);
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(position, 3));
  geo.setAttribute('aOrbit', new THREE.Float32BufferAttribute(aOrbit, 4));
  geo.setAttribute('aColor', new THREE.Float32BufferAttribute(aColor, 3));

  const material = new THREE.ShaderMaterial({
    name: 'atmos-motes',
    uniforms: { ...haze.uniforms, uTime: shared.uTime, uSize: { value: cfg.size } },
    vertexShader: /* glsl */ `
attribute vec4 aOrbit;   // radius, angular speed, phase, bob
attribute vec3 aColor;
uniform float uTime;
uniform float uSize;
varying vec3 vColor;
${haze.glsl}
void main() {
	float a = uTime * aOrbit.y + aOrbit.z * 6.2832;
	// An orbit that never quite closes: the radius breathes and the plane wobbles.
	float r = aOrbit.x * ( 0.62 + 0.38 * sin( uTime * 1.9 * abs( aOrbit.y ) + aOrbit.z * 40.0 ) );
	vec3 p = position + vec3( cos( a ) * r, aOrbit.w * sin( a * 1.31 + aOrbit.z * 20.0 ), sin( a ) * r );
	vec4 mv = viewMatrix * vec4( p, 1.0 );
	float dist = max( - mv.z, 0.1 );
	vColor = aColor * hazeT( dist, p.xz ) * ( 1.0 - smoothstep( 30.0, 55.0, dist ) );
	gl_PointSize = clamp( uSize * 22.0 / dist, 1.0, 3.5 );
	gl_Position = projectionMatrix * mv;
}`,
    fragmentShader: /* glsl */ `
varying vec3 vColor;
void main() {
	gl_FragColor = vec4( vColor, 1.0 );
	${OUTPUT}
}`,
    transparent: true,
    blending: THREE.AdditiveBlending,
    premultipliedAlpha: true,
    depthWrite: false,
    fog: false,
  });
  const points = new THREE.Points(geo, material);
  points.name = 'atmos-motes';
  points.frustumCulled = false;
  points.matrixAutoUpdate = false;
  points.renderOrder = 6;
  return points;
}

// ------------------------------------------------------------------------------------------------
// The open hydrant
// ------------------------------------------------------------------------------------------------

function buildSpray(G, origin, dir, haze, shared) {
  const cfg = G.config.look.life.hydrant;
  const rng = G.rng.fork('atmos-hydrant');
  const seeds = new Float32Array(cfg.drops * 4);
  for (let i = 0; i < cfg.drops; i++) {
    seeds[i * 4] = rng.next(); // phase
    seeds[i * 4 + 1] = rng.range(-1, 1); // sideways
    seeds[i * 4 + 2] = rng.range(-1, 1); // up / down
    seeds[i * 4 + 3] = rng.range(0.8, 1.15); // speed
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array(cfg.drops * 3), 3));
  geo.setAttribute('aSeed', new THREE.Float32BufferAttribute(seeds, 4));
  const side = new THREE.Vector3(-dir.z, 0, dir.x);
  const material = new THREE.ShaderMaterial({
    name: 'atmos-spray',
    uniforms: {
      ...haze.uniforms,
      uTime: shared.uTime,
      uOrigin: { value: origin.clone() },
      uDir: { value: dir.clone() },
      uSide: { value: side },
      uJet: { value: new THREE.Vector3(cfg.speed, cfg.lift, cfg.spread) },
      uColor: { value: new THREE.Color().setRGB(cfg.radiance[0], cfg.radiance[1], cfg.radiance[2]) },
    },
    vertexShader: /* glsl */ `
attribute vec4 aSeed;
uniform float uTime;
uniform vec3 uOrigin;
uniform vec3 uDir;
uniform vec3 uSide;
uniform vec3 uJet;     // speed, lift, spread
uniform vec3 uColor;
varying vec3 vColor;
${haze.glsl}
void main() {
	// Flight time of a drop that leaves at this speed and lift and lands back on the street.
	float vy = uJet.y * uJet.x * ( 1.0 + 0.5 * aSeed.z * uJet.z ) ;
	float flight = ( vy + sqrt( vy * vy + 19.6 * uOrigin.y ) ) / 9.8;
	float t = fract( uTime / flight * 0.9 + aSeed.x ) * flight;
	vec3 v = uDir * uJet.x * aSeed.w + uSide * uJet.x * uJet.z * aSeed.y + vec3( 0.0, vy, 0.0 );
	vec3 p = uOrigin + v * t - vec3( 0.0, 4.9 * t * t, 0.0 );
	p.y = max( p.y, 0.03 );
	vec4 mv = viewMatrix * vec4( p, 1.0 );
	float dist = max( - mv.z, 0.1 );
	float k = t / flight;
	vColor = uColor * hazeT( dist, p.xz ) * smoothstep( 0.0, 0.05, k ) * ( 1.0 - 0.6 * k ) * ( 1.0 - smoothstep( 40.0, 70.0, dist ) );
	gl_PointSize = clamp( 16.0 / dist, 1.0, 2.0 );
	gl_Position = projectionMatrix * mv;
}`,
    fragmentShader: /* glsl */ `
varying vec3 vColor;
void main() {
	gl_FragColor = vec4( vColor, 1.0 );
	${OUTPUT}
}`,
    transparent: true,
    blending: THREE.AdditiveBlending,
    premultipliedAlpha: true,
    depthWrite: false,
    fog: false,
  });
  const points = new THREE.Points(geo, material);
  points.name = 'atmos-spray';
  points.frustumCulled = false;
  points.matrixAutoUpdate = false;
  points.renderOrder = 6;
  return points;
}

/** Where the open hydrant stands and which way it sprays, or null when the level has none. */
function findHydrant(G, avenueZ) {
  let found = null;
  if (!G.level.root) return null;
  G.level.root.updateMatrixWorld(true);
  G.level.root.traverse((obj) => {
    if (!found && obj.name === 'hydrant_open') found = obj;
  });
  if (!found) return null;
  const pos = new THREE.Vector3().setFromMatrixPosition(found.matrixWorld);
  // A hint from the prop wins (local-space nozzle direction); otherwise it sprays into the street.
  const hint = found.userData && found.userData.spray;
  let dir;
  if (hint && Number.isFinite(hint.x)) dir = new THREE.Vector3(hint.x, 0, hint.z).transformDirection(found.matrixWorld);
  else if (Math.abs(pos.z - avenueZ) > 3) dir = new THREE.Vector3(0, 0, pos.z > avenueZ ? -1 : 1);
  else dir = new THREE.Vector3(1, 0, 0).transformDirection(found.matrixWorld);
  dir.y = 0;
  dir.normalize();
  return { pos, dir, object: found };
}

// ------------------------------------------------------------------------------------------------
// Paper
// ------------------------------------------------------------------------------------------------

function createPaper(G, bounds, el, parent) {
  const cfg = G.config.look.life.paper;
  const rng = G.rng.fork('atmos-paper');
  const N = cfg.sheets;
  const material = new THREE.MeshStandardMaterial({ name: 'atmos-paper', map: paperTexture(rng), side: THREE.DoubleSide, roughness: 0.92, metalness: 0 });
  const geo = new THREE.PlaneGeometry(0.22, 0.3);
  geo.rotateX(-Math.PI / 2); // lies on the street
  const mesh = new THREE.InstancedMesh(geo, material, N);
  mesh.name = 'atmos-paper';
  mesh.receiveShadow = true;
  mesh.frustumCulled = false;
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  parent.add(mesh);

  const midZ = el ? (el.minZ + el.maxZ) / 2 : 0;

  /** A free spot on the avenue (falls back to the raw point when the nav grid has nothing near). */
  function place(sheet) {
    const x = rng.range(bounds.minX + 6, bounds.maxX - 6);
    const z = midZ + rng.range(-9.5, 9.5);
    const spot = G.physics.nav.nearestWalkable(x, z, 5);
    sheet.x = spot ? spot.x : x;
    sheet.z = spot ? spot.z : z;
    sheet.vx = sheet.vz = 0;
    sheet.stuck = 0;
  }

  const sheets = [];
  for (let i = 0; i < N; i++) {
    sheets.push({
      x: 0,
      z: 0,
      y: 0.02,
      ground: 0,
      vx: 0,
      vz: 0,
      yaw: rng.range(0, 6.28),
      tumble: 0, // rotation about the axis across its path
      air: 0, // 0 lying flat … 1 airborne
      catches: rng.range(0.45, 1), // how much of the wind this sheet takes
      stuck: 0,
    });
    place(sheets[i]);
  }

  const wind = new THREE.Vector2(cfg.wind[0], cfg.wind[1]);
  const gust = new THREE.Vector2();
  let gustLeft = 0;
  let gustIn = rng.range(1.5, 5);
  const dummy = new THREE.Object3D();
  const axis = new THREE.Vector3();
  const qYaw = new THREE.Quaternion();
  const qTumble = new THREE.Quaternion();
  const UP = new THREE.Vector3(0, 1, 0);

  function update(dt, train) {
    gustIn -= dt;
    if (gustIn <= 0) {
      // A gust: mostly down the avenue, either way.
      const a = (rng.chance(0.5) ? 0 : Math.PI) + rng.range(-0.5, 0.5);
      gust.set(Math.cos(a), Math.sin(a)).multiplyScalar(cfg.gust * rng.range(0.6, 1));
      gustLeft = rng.range(1.6, 3.2);
      gustIn = rng.range(cfg.gustEvery[0], cfg.gustEvery[1]);
    }
    gustLeft -= dt;
    const blowing = gustLeft > 0 ? 1 : 0;
    const trainGust = train && train.active ? G.config.look.train.gust : 0;

    for (let i = 0; i < N; i++) {
      const s = sheets[i];
      // Wind on this sheet: the steady draught only moves what is already loose, a gust lifts anything.
      let wx = wind.x * 0.15 + gust.x * blowing;
      let wz = wind.y * 0.15 + gust.y * blowing;
      if (trainGust && s.x > train.lo - 3 && s.x < train.hi + 3 && Math.abs(s.z - train.z) < 8) {
        wx += train.dir * trainGust;
        wz += (s.z > train.z ? 1 : -1) * trainGust * 0.35;
      }
      const drag = s.air > 0.2 ? 1.6 : 4.5; // the street holds on to a sheet that lies flat
      s.vx = damp(s.vx, wx * s.catches, drag, dt);
      s.vz = damp(s.vz, wz * s.catches, drag, dt);
      const speed = Math.hypot(s.vx, s.vz);

      if (speed > 0.02) {
        const nx = s.x + s.vx * dt;
        const nz = s.z + s.vz * dt;
        const inside = nx > bounds.minX + 1 && nx < bounds.maxX - 1 && nz > bounds.minZ + 1 && nz < bounds.maxZ - 1;
        if (inside && G.physics.nav.isWalkable(nx, nz)) {
          s.x = nx;
          s.z = nz;
          s.stuck = 0;
        } else if (inside && G.physics.nav.isWalkable(nx, s.z)) {
          s.x = nx;
          s.vz *= -0.3;
        } else if (inside && G.physics.nav.isWalkable(s.x, nz)) {
          s.z = nz;
          s.vx *= -0.3;
        } else {
          // Pinned against a car or a wall.
          s.vx *= -0.25;
          s.vz *= -0.25;
          s.stuck += dt;
          // Wedged for good: let it turn up somewhere else, as long as nobody is looking at it.
          if (s.stuck > 6 && Math.hypot(s.x - G.camera.position.x, s.z - G.camera.position.z) > 25) place(s);
        }
      }
      // Fast sheets lift and tumble; slow ones settle flat.
      s.air = damp(s.air, clamp((speed - 1.1) / 1.6, 0, 1), s.air < 0.5 ? 3 : 1.4, dt);
      if (s.air > 0.02) {
        s.tumble += speed * 3.4 * dt;
        s.yaw += s.catches * 1.3 * dt;
      } else {
        s.tumble = damp(s.tumble, Math.round(s.tumble / Math.PI) * Math.PI, 8, dt);
        s.yaw += speed * 0.8 * dt;
      }
      s.ground = G.physics.groundHeight(s.x, s.z, 0.5);
      s.y = s.ground + 0.02 + s.air * (0.16 + 0.12 * Math.abs(Math.sin(s.tumble)));

      dummy.position.set(s.x, s.y, s.z);
      qYaw.setFromAxisAngle(UP, s.yaw);
      // Tumble about the horizontal axis square to the direction of travel.
      if (speed > 0.05) axis.set(s.vz / speed, 0, -s.vx / speed);
      else axis.set(1, 0, 0);
      qTumble.setFromAxisAngle(axis, s.tumble);
      dummy.quaternion.copy(qTumble).multiply(qYaw);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
    }
    mesh.instanceMatrix.needsUpdate = true;
  }

  update(0, null);
  return { mesh, update, texture: material.map };
}

// ------------------------------------------------------------------------------------------------

// ------------------------------------------------------------------------------------------------
// Pigeons (day only): a few loose flocks wheeling over the roofs. One draw call, moved in the shader.
// ------------------------------------------------------------------------------------------------

function buildBirds(G, flocks, haze, shared) {
  const cfg = G.config.look.life.birds;
  const rng = G.rng.fork('atmos-birds');
  const position = [];
  const aBird = [];
  const aFlock = [];
  const index = [];
  // A bird is a body diamond and two wings (local x forward, z to the right, metres).
  const S = cfg.size;
  const shape = [
    [0.22, 0, 0], [-0.2, 0, 0], [0, 0.02, 0.05], [0, 0.02, -0.05], // body
    [0.06, 0, -0.04], [-0.08, 0, -0.04], [-0.04, 0, -0.34], // left wing (tip last)
    [0.06, 0, 0.04], [-0.08, 0, 0.04], [-0.04, 0, 0.34], // right wing
  ];
  const tris = [0, 2, 1, 0, 1, 3, 4, 5, 6, 7, 9, 8];
  let base = 0;
  for (const flock of flocks) {
    for (let i = 0; i < flock.count; i++) {
      const bird = [rng.range(flock.radius[0], flock.radius[1]), rng.range(0.16, 0.26) * flock.turn, rng.next(), rng.range(flock.height[0], flock.height[1])];
      for (const v of shape) {
        position.push(v[0] * S, v[1] * S, v[2] * S);
        aBird.push(...bird);
        aFlock.push(flock.x, flock.z, flock.squash);
      }
      for (const t of tris) index.push(base + t);
      base += shape.length;
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(position, 3));
  geo.setAttribute('aBird', new THREE.Float32BufferAttribute(aBird, 4));
  geo.setAttribute('aFlock', new THREE.Float32BufferAttribute(aFlock, 3));
  geo.setIndex(index);
  const material = new THREE.ShaderMaterial({
    name: 'atmos-birds',
    uniforms: { ...haze.uniforms, uTime: shared.uTime, uColor: { value: new THREE.Color().setRGB(cfg.color[0], cfg.color[1], cfg.color[2]) } },
    vertexShader: /* glsl */ `
attribute vec4 aBird;   // orbit radius, angular speed (sign = way round), phase, height
attribute vec3 aFlock;  // centre x, z, how flat the orbit is
uniform float uTime;
uniform vec3 uColor;
varying vec3 vColor;
${haze.glsl}
void main() {
	float a = uTime * aBird.y + aBird.z * 6.2832;
	float r = aBird.x * ( 0.85 + 0.15 * sin( uTime * 0.13 + aBird.z * 17.0 ) );
	vec3 c = vec3( aFlock.x + cos( a ) * r, aBird.w + 1.6 * sin( a * 0.7 + aBird.z * 9.0 ), aFlock.y + sin( a ) * r * aFlock.z );
	vec3 fwd = normalize( vec3( - sin( a ), 0.0, cos( a ) * aFlock.z ) * sign( aBird.y ) );
	vec3 right = normalize( cross( fwd, vec3( 0.0, 1.0, 0.0 ) ) );
	// Flap in bursts, glide in between.
	float burst = smoothstep( 0.25, 0.35, fract( uTime * 0.21 + aBird.z * 3.7 ) );
	float flap = sin( uTime * ( 15.0 + aBird.z * 4.0 ) + aBird.z * 20.0 ) * mix( 0.25, 1.0, burst );
	float tip = abs( position.z ) / ${(0.34 * S).toFixed(4)};
	vec3 p = c + fwd * position.x + right * position.z + vec3( 0.0, position.y + flap * 0.16 * clamp( tip, 0.0, 1.0 ), 0.0 );
	vec4 mv = viewMatrix * vec4( p, 1.0 );
	vColor = mix( hazeColor( p.xz ), uColor, hazeT( - mv.z, p.xz ) );
	gl_Position = projectionMatrix * mv;
}`,
    fragmentShader: /* glsl */ `
varying vec3 vColor;
void main() {
	gl_FragColor = vec4( vColor, 1.0 );
	${OUTPUT}
}`,
    side: THREE.DoubleSide,
    forceSinglePass: true,
    fog: false,
  });
  const mesh = new THREE.Mesh(geo, material);
  mesh.name = 'atmos-birds';
  mesh.frustumCulled = false;
  mesh.matrixAutoUpdate = false;
  return mesh;
}

export function createLife(G, { bounds, el, avenueZ, lamps, haze, shared, parent }) {
  const cfg = G.config.look.life;
  const steamPoints = (G.level.steam || []).filter((p) => p && Number.isFinite(p.x));

  // Steam takes its colour from the light it stands in: the street's own sodium, more of it near a lamp.
  const columns = [];
  const base = cfg.steam.color;
  for (const p of steamPoints) {
    const tint = [base[0], base[1], base[2]];
    for (const lamp of lamps) {
      if (lamp.virtual) continue;
      const d = Math.hypot(lamp.pos.x - p.x, lamp.pos.z - p.z);
      if (d > 14) continue;
      const k = (lamp.intensity / (36 + d * d + lamp.pos.y * lamp.pos.y)) * 0.11;
      tint[0] += lamp.color.r * k;
      tint[1] += lamp.color.g * k;
      tint[2] += lamp.color.b * k;
    }
    columns.push({
      pos: new THREE.Vector3(p.x, p.y + 0.05, p.z),
      tint,
      height: cfg.steam.height,
      spread: cfg.steam.spread,
      size: cfg.steam.size,
      rise: cfg.steam.rise,
      alpha: cfg.steam.alpha,
      puffs: cfg.steam.puffs,
    });
  }

  const hydrant = findHydrant(G, avenueZ);
  let spray = null;
  if (hydrant) {
    const nozzle = hydrant.pos.clone();
    nozzle.y += 0.5;
    nozzle.addScaledVector(hydrant.dir, 0.22);
    spray = buildSpray(G, nozzle, hydrant.dir, haze, shared);
    parent.add(spray);
    // Mist where the jet comes down, and a thinner veil along it.
    const reach = cfg.hydrant.speed * 0.62;
    for (const [along, puffs, alpha] of [[reach, 6, 0.1], [reach * 0.55, 4, 0.06]]) {
      columns.push({
        pos: hydrant.pos.clone().addScaledVector(hydrant.dir, along).setY(hydrant.pos.y + 0.1),
        tint: [base[0] * 1.1, base[1] * 1.15, base[2] * 1.25],
        height: 1.5,
        spread: 1.9,
        size: [0.5, 2.1],
        rise: 0.75,
        alpha,
        puffs,
      });
    }
  }

  const steam = buildSteam(G, columns, haze, shared);
  if (steam) parent.add(steam);
  const motes = buildMotes(G, lamps, haze, shared);
  if (motes) parent.add(motes);
  const paper = createPaper(G, bounds, el, parent);
  let birds = null;
  if (cfg.birds && cfg.birds.flocks > 0) {
    const cx = (bounds.minX + bounds.maxX) / 2;
    const flocks = [
      { x: cx - 8, z: avenueZ, count: cfg.birds.perFlock, radius: [9, 22], height: [15, 24], turn: 1, squash: 0.55 },
      { x: bounds.maxX - 10, z: avenueZ + 20, count: Math.round(cfg.birds.perFlock * 0.7), radius: [6, 14], height: [18, 30], turn: -1, squash: 0.8 },
      { x: bounds.minX - 25, z: avenueZ - 30, count: Math.round(cfg.birds.perFlock * 0.6), radius: [10, 18], height: [24, 34], turn: 1, squash: 0.7 },
    ].slice(0, cfg.birds.flocks);
    birds = buildBirds(G, flocks, haze, shared);
    birds.visible = false; // by day (setTime)
    parent.add(birds);
  }

  // The fx module's steam (real particles, lit and sorted with the rest of its smoke) on top of ours.
  let emitters = [];
  function hookEmitters() {
    for (const e of emitters) {
      try {
        e.stop();
      } catch {
        // an emitter the fx module has already dropped
      }
    }
    emitters = [];
    if (!G.fx || typeof G.fx.addEmitter !== 'function') return;
    for (const p of steamPoints) {
      const handle = G.fx.addEmitter(p, 'steam', { scale: 1 });
      if (handle && typeof handle.stop === 'function') emitters.push(handle);
    }
  }

  let shownDetail = null;
  let motesByTime = true;

  return {
    steam,
    motes,
    spray,
    birds,
    paper,
    hydrant,
    hookEmitters,
    update(dt, train) {
      paper.update(dt, train);
    },
    setDetail(detail) {
      shownDetail = detail;
      if (motes) motes.visible = detail.motes && motesByTime;
      if (steam) steam.material.uniforms.uShow.value = detail.steamPuffs;
    },
    /** Day or night (look.times.<name>.life): steam colour and opacity, the spray, the moths. */
    setTime(t) {
      motesByTime = t.motes;
      if (birds) birds.visible = !!t.birds;
      if (motes) motes.visible = !!(shownDetail && shownDetail.motes) && motesByTime;
      if (steam) {
        const u = steam.material.uniforms;
        if (t.steam) u.uDayTint.value.set(t.steam[0], t.steam[1], t.steam[2], 1);
        else u.uDayTint.value.w = 0;
        u.uAlphaScale.value = t.steamAlpha ?? 1;
      }
      if (spray && t.spray) spray.material.uniforms.uColor.value.setRGB(t.spray[0], t.spray[1], t.spray[2]);
    },
  };
}
