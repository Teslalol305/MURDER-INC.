// The El train: five low-poly cars with lit windows that cross the deck every 40–70 seconds.
//
//   - it appears and vanishes deep in the haze outside the bounds, alternating direction and track;
//   - `train:pass` is emitted on approach, when it is over the block, and when it has gone (CONTRACT 4.2);
//   - while it is overhead: window light falls through the ties as moving stripes (one shader-driven patch
//     on the roadway), a pooled light strobes under the deck with the odd blue arc from the third rail,
//     grit comes down (fx.dust, plus a few specks of its own so the stub build shows it too), the lamps
//     under the El stutter, the camera rumbles when the player stands near, loose paper is kicked up.
//
// One mesh for the cars, one for its head and tail lights; nothing is allocated while it runs.

import * as THREE from 'three';
import { clamp01 } from '../core/util.js';
import { createGlowBatch } from './lampfield.js';
import { createTrainSchedule, trainTimeline } from './plan.js';
import { CAR_UV, carSheets, textureSize } from './textures.js';

const OUTPUT = /* glsl */ `
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
`;

/** The whole train as one geometry: nose at x = 0, running back along −x; y = 0 is the rail top. */
function buildTrainGeometry(cfg) {
  const position = [];
  const normal = [];
  const uv = [];
  const index = [];
  const va = new THREE.Vector3();
  const vb = new THREE.Vector3();
  const n = new THREE.Vector3();

  /** Corners a, b (bottom, left to right seen from outside), c, d (top, right to left). */
  function quad(a, b, c, d, [u0, v0, u1, v1]) {
    const base = position.length / 3;
    position.push(...a, ...b, ...c, ...d);
    va.set(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
    vb.set(d[0] - a[0], d[1] - a[1], d[2] - a[2]);
    n.crossVectors(va, vb).normalize();
    for (let i = 0; i < 4; i++) normal.push(n.x, n.y, n.z);
    uv.push(u0, v0, u1, v0, u1, v1, u0, v1);
    index.push(base, base + 1, base + 2, base, base + 2, base + 3);
  }

  function box(x0, x1, y0, y1, z0, z1, region) {
    quad([x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1], region);
    quad([x1, y0, z0], [x0, y0, z0], [x0, y1, z0], [x1, y1, z0], region);
    quad([x1, y0, z1], [x1, y0, z0], [x1, y1, z0], [x1, y1, z1], region);
    quad([x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0], region);
    quad([x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1], region); // underside
  }

  const L = cfg.carLength;
  const hw = cfg.carWidth / 2;
  const floor = 0.42;
  const eave = cfg.carHeight - 0.26; // where the roof starts to curve in
  const top = cfg.carHeight;
  const inset = 0.42;

  for (let i = 0; i < cfg.cars; i++) {
    const x1 = -i * (L + cfg.carGap);
    const x0 = x1 - L;
    // Sides, ends.
    quad([x0, floor, hw], [x1, floor, hw], [x1, eave, hw], [x0, eave, hw], CAR_UV.side);
    quad([x1, floor, -hw], [x0, floor, -hw], [x0, eave, -hw], [x1, eave, -hw], CAR_UV.side);
    quad([x1, floor, hw], [x1, floor, -hw], [x1, eave, -hw], [x1, eave, hw], CAR_UV.end);
    quad([x0, floor, -hw], [x0, floor, hw], [x0, eave, hw], [x0, eave, -hw], CAR_UV.end);
    // Roof: two shoulders and a flat top, and the gables that close the ends.
    quad([x0, eave, hw], [x1, eave, hw], [x1, top, hw - inset], [x0, top, hw - inset], CAR_UV.steel);
    quad([x1, eave, -hw], [x0, eave, -hw], [x0, top, -hw + inset], [x1, top, -hw + inset], CAR_UV.steel);
    quad([x0, top, hw - inset], [x1, top, hw - inset], [x1, top, -hw + inset], [x0, top, -hw + inset], CAR_UV.steel);
    quad([x1, eave, hw], [x1, eave, -hw], [x1, top, -hw + inset], [x1, top, hw - inset], CAR_UV.steel);
    quad([x0, eave, -hw], [x0, eave, hw], [x0, top, hw - inset], [x0, top, -hw + inset], CAR_UV.steel);
    // Floor, underframe and two trucks.
    quad([x0, floor, -hw], [x1, floor, -hw], [x1, floor, hw], [x0, floor, hw], CAR_UV.dark);
    box(x0 + 3.9, x1 - 3.9, 0.14, floor, -0.95, 0.95, CAR_UV.dark);
    for (const cx of [x0 + 2.5, x1 - 2.5]) box(cx - 1.25, cx + 1.25, 0, floor, -1.1, 1.1, CAR_UV.dark);
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(position, 3));
  geo.setAttribute('normal', new THREE.Float32BufferAttribute(normal, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  geo.setIndex(index);
  geo.computeBoundingSphere();
  return geo;
}

export function createTrain(G, { bounds, el, haze, shared, glowMaterial, parent }) {
  const cfg = G.config.look.train;
  const rng = G.rng.fork('atmos-train');
  const length = cfg.cars * cfg.carLength + (cfg.cars - 1) * cfg.carGap;
  // The level may say where its rails are (el.deckTop, el.tracks); otherwise they are placed by proportion.
  const railY = Number.isFinite(el.deckTop) ? el.deckTop : el.y + cfg.railOffset;
  const midZ = (el.minZ + el.maxZ) / 2;
  const halfZ = (el.maxZ - el.minZ) / 2;
  const tracks = Array.isArray(el.tracks) && el.tracks.length >= 2 ? el.tracks : null;
  const trackSouth = tracks ? Math.max(...tracks) : midZ + (el.maxZ - el.minZ) * cfg.trackOffset;
  const trackNorth = tracks ? Math.min(...tracks) : midZ - (el.maxZ - el.minZ) * cfg.trackOffset;

  const timelines = {
    1: trainTimeline({ minX: bounds.minX, maxX: bounds.maxX, dir: 1, speed: cfg.speed, length, runUp: cfg.runUp }),
    '-1': trainTimeline({ minX: bounds.minX, maxX: bounds.maxX, dir: -1, speed: cfg.speed, length, runUp: cfg.runUp }),
  };
  const schedule = createTrainSchedule({ rng, firstPass: cfg.firstPass, every: cfg.every, approach: timelines[1].approach });

  // ---------------------------------------------------------------------------------------------
  // The cars
  // ---------------------------------------------------------------------------------------------

  const sheets = carSheets(textureSize(G), rng.fork('sheet'));
  const material = new THREE.MeshStandardMaterial({
    name: 'atmos-train',
    map: sheets.map,
    emissiveMap: sheets.emissiveMap,
    emissive: new THREE.Color().setRGB(cfg.windowRadiance[0], cfg.windowRadiance[1], cfg.windowRadiance[2]),
    roughness: 0.42,
    metalness: 0.55,
  });
  const group = new THREE.Group();
  group.name = 'atmos-train';
  group.visible = false;
  const cars = new THREE.Mesh(buildTrainGeometry(cfg), material);
  cars.name = 'atmos-train-cars';
  cars.castShadow = true; // it blocks the light that falls through the ties
  group.add(cars);

  {
    const batch = createGlowBatch();
    const white = new THREE.Color().setRGB(1, cfg.headlight[1] / cfg.headlight[0], cfg.headlight[2] / cfg.headlight[0]);
    const red = new THREE.Color().setRGB(1, cfg.tail[1] / cfg.tail[0], cfg.tail[2] / cfg.tail[0]);
    for (const z of [-0.85, 0.85]) {
      batch.add({ pos: { x: 0.15, y: 1.2, z }, color: white, size: 1.7, core: cfg.headlight[0], halo: 1.1, minAngle: 0.0055 });
      batch.add({ pos: { x: -length - 0.15, y: 1.2, z }, color: red, size: 1, core: cfg.tail[0], halo: 0.6, minAngle: 0.004 });
    }
    group.add(batch.mesh(glowMaterial, 'atmos-train-lights'));
  }
  parent.add(group);

  // ---------------------------------------------------------------------------------------------
  // Light through the ties, grit
  // ---------------------------------------------------------------------------------------------

  const uPass = { value: new THREE.Vector4(0, 0, 0, 0) }; // x extent of the train (lo, hi), track z, presence 0…1
  const uHead = { value: 0 };

  const stripes = new THREE.Mesh(
    new THREE.BufferGeometry(),
    new THREE.ShaderMaterial({
      name: 'atmos-train-stripes',
      uniforms: {
        ...haze.uniforms,
        uTime: shared.uTime,
        uPass,
        uHead,
        uCar: { value: cfg.carLength + cfg.carGap },
        uColor: { value: new THREE.Color().setRGB(cfg.windowRadiance[0] * cfg.stripeGain, cfg.windowRadiance[1] * cfg.stripeGain, cfg.windowRadiance[2] * cfg.stripeGain) },
      },
      vertexShader: /* glsl */ `
varying vec2 vXZ;
varying float vDepth;
void main() {
	vec4 mv = modelViewMatrix * vec4( position, 1.0 );
	vXZ = position.xz;
	vDepth = - mv.z;
	gl_Position = projectionMatrix * mv;
}`,
      fragmentShader: /* glsl */ `
uniform float uTime;
uniform vec4 uPass;
uniform float uHead;
uniform float uCar;
uniform vec3 uColor;
varying vec2 vXZ;
varying float vDepth;
${haze.glsl}
void main() {
	float x = vXZ.x;
	float inside = smoothstep( uPass.x - 1.5, uPass.x + 0.5, x ) * ( 1.0 - smoothstep( uPass.y - 0.5, uPass.y + 1.5, x ) ) * uPass.w;
	if ( inside < 0.002 ) discard;
	// Light only gets through between the ties, which stay where they are...
	float ties = x / 0.62;
	float tie = smoothstep( 0.12, 0.36, abs( fract( ties ) - 0.5 ) );
	tie = mix( tie, 0.5, smoothstep( 0.25, 0.7, fwidth( ties ) ) );   // too fine to resolve: its average
	// ...and comes from the windows, which do not: panes between doors, darkness between cars.
	float car = fract( abs( x - uHead ) / uCar );
	float groups = car * 5.0;
	float pane = 0.16 + 0.84 * smoothstep( 0.08, 0.3, abs( fract( groups ) - 0.5 ) );
	pane = mix( pane, 0.65, smoothstep( 0.25, 0.7, fwidth( groups ) ) );
	float ends = smoothstep( 0.0, 0.035, car ) * ( 1.0 - smoothstep( 0.93, 0.965, car ) );
	float across = ( vXZ.y - uPass.z ) / 2.7;
	float flicker = 0.86 + 0.14 * sin( uTime * 31.0 + x * 0.7 );
	vec3 col = uColor * inside * tie * pane * ends * exp( - across * across ) * flicker * hazeT( vDepth, vXZ );
	gl_FragColor = vec4( col, 1.0 );
	${OUTPUT}
}`,
      transparent: true,
      blending: THREE.AdditiveBlending,
      premultipliedAlpha: true,
      depthWrite: false,
      fog: false,
      polygonOffset: true,
      polygonOffsetFactor: -3,
      polygonOffsetUnits: -3,
    }),
  );
  {
    const x0 = bounds.minX - 40;
    const x1 = bounds.maxX + 40;
    const z0 = el.minZ - 2.5;
    const z1 = el.maxZ + 2.5;
    const y = 0.055;
    stripes.geometry.setAttribute('position', new THREE.Float32BufferAttribute([x0, y, z1, x1, y, z1, x1, y, z0, x0, y, z0], 3));
    stripes.geometry.setIndex([0, 1, 2, 0, 2, 3]);
    stripes.geometry.computeBoundingSphere();
  }
  stripes.name = 'atmos-train-stripes';
  stripes.renderOrder = -19;
  stripes.matrixAutoUpdate = false;
  stripes.visible = false;
  parent.add(stripes);

  const GRIT = 150;
  const grit = new THREE.Points(
    new THREE.BufferGeometry(),
    new THREE.ShaderMaterial({
      name: 'atmos-train-grit',
      uniforms: {
        ...haze.uniforms,
        uTime: shared.uTime,
        uPass,
        uDeck: { value: new THREE.Vector3(el.y - 0.25, midZ, halfZ) },
      },
      vertexShader: /* glsl */ `
attribute vec4 aSeed;   // place along the street (0..1), across the deck (-1..1), phase, speed
uniform float uTime;
uniform vec4 uPass;
uniform vec3 uDeck;     // y under the deck, z of its middle, half width
varying float vAlpha;
${haze.glsl}
void main() {
	const float SPAN = 46.0;
	// Each speck has a fixed place on the street, repeated every SPAN metres: use the copy nearest the eye.
	float base = aSeed.x * SPAN;
	float x = base + SPAN * floor( ( cameraPosition.x - base ) / SPAN + 0.5 );
	float t = fract( uTime * ( 0.42 + 0.3 * aSeed.w ) + aSeed.z );
	float y = uDeck.x * ( 1.0 - ( 0.22 * t + 0.78 * t * t ) );
	float z = uDeck.y + aSeed.y * uDeck.z + 0.16 * sin( t * 7.0 + aSeed.z * 40.0 );
	float under = step( uPass.x, x ) * step( x, uPass.y ) * uPass.w;
	vec4 mv = viewMatrix * vec4( x, y, z, 1.0 );
	vAlpha = under * smoothstep( 0.0, 0.06, t ) * ( 1.0 - smoothstep( 0.86, 1.0, t ) ) * hazeT( - mv.z, vec2( x, z ) );
	gl_PointSize = clamp( 30.0 / max( - mv.z, 0.5 ), 1.0, 2.0 );
	gl_Position = under > 0.0 ? projectionMatrix * mv : vec4( 2.0, 2.0, 2.0, 1.0 );
}`,
      fragmentShader: /* glsl */ `
varying float vAlpha;
void main() {
	gl_FragColor = vec4( vec3( 0.085, 0.066, 0.045 ) * vAlpha, 1.0 );
	${OUTPUT}
}`,
      transparent: true,
      blending: THREE.AdditiveBlending,
      premultipliedAlpha: true,
      depthWrite: false,
      fog: false,
    }),
  );
  {
    const seeds = new Float32Array(GRIT * 4);
    for (let i = 0; i < GRIT; i++) {
      seeds[i * 4] = rng.next();
      seeds[i * 4 + 1] = rng.range(-1, 1);
      seeds[i * 4 + 2] = rng.next();
      seeds[i * 4 + 3] = rng.next();
    }
    grit.geometry.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array(GRIT * 3), 3));
    grit.geometry.setAttribute('aSeed', new THREE.Float32BufferAttribute(seeds, 4));
  }
  grit.name = 'atmos-train-grit';
  grit.frustumCulled = false;
  grit.visible = false;
  parent.add(grit);

  // ---------------------------------------------------------------------------------------------
  // The run
  // ---------------------------------------------------------------------------------------------

  /** Live state, also published as `atmos.train`. `x` is the nose, `lo`…`hi` the extent along the street. */
  const state = { active: false, phase: null, dir: 1, x: 0, lo: 0, hi: 0, y: railY, z: midZ, speed: cfg.speed, length, passes: 0 };
  const passEvent = { phase: 'approach', duration: 0, dir: 1 };
  const flashPos = new THREE.Vector3();
  const down = new THREE.Vector3(0, -1, 0);
  const flashColor = new THREE.Color(cfg.flash.color);
  const arcColor = new THREE.Color(cfg.flash.arcColor);
  let timeline = timelines[1];
  let local = 0; // seconds into the current pass
  let flashIn = 0;
  let flashBusy = 0; // our own pooled flash is still fading: do not take a second light
  let gritIn = 0;
  let gritOn = true;

  function emit(phase, duration) {
    passEvent.phase = phase;
    passEvent.duration = duration;
    passEvent.dir = state.dir;
    G.events.emit('train:pass', passEvent);
  }

  function begin(dir, at = 0) {
    timeline = timelines[dir < 0 ? -1 : 1];
    local = at;
    state.active = true;
    state.dir = timeline.dir;
    state.z = timeline.dir > 0 ? trackSouth : trackNorth; // eastbound on the south track
    state.phase = null;
    state.passes++;
    group.position.set(timeline.head(local), railY, state.z);
    group.rotation.y = timeline.dir > 0 ? 0 : Math.PI;
    group.visible = true;
    stripes.visible = true;
    grit.visible = gritOn;
    uPass.value.z = state.z;
    flashIn = 0;
    gritIn = 0;
  }

  function end() {
    state.active = false;
    state.phase = null;
    group.visible = false;
    stripes.visible = false;
    grit.visible = false;
    uPass.value.w = 0;
    shared.uTrain.value.z = 0;
  }

  /** Strobe, arcs, grit, rumble: only what the camera can be near. */
  function effects(dt) {
    const cam = G.camera.position;
    const { lo, hi } = state;
    const outside = Math.max(lo - cam.x, cam.x - hi, 0); // metres of street between the camera and the train
    if (outside > 60) return;

    flashBusy -= dt;
    flashIn -= dt;
    if (flashIn <= 0 && flashBusy <= 0 && hi - lo > 4) {
      const f = cfg.flash;
      const arc = rng.chance(f.arcChance);
      const ttl = arc ? f.ttl[0] : rng.range(f.ttl[0], f.ttl[1]);
      flashPos.set(Math.min(hi - 1, Math.max(lo + 1, cam.x + rng.range(-15, 15))), el.y - 0.45, state.z + rng.range(-1.3, 1.3));
      G.render.lights.flash(flashPos, arc ? arcColor : flashColor, arc ? f.arcIntensity : rng.range(f.intensity[0], f.intensity[1]), f.range, ttl);
      if (arc) G.fx.sparks(flashPos, down, 6);
      flashBusy = ttl;
      flashIn = rng.range(f.every[0], f.every[1]);
    }

    gritIn -= dt;
    if (gritIn <= 0) {
      const g = cfg.grit;
      flashPos.set(Math.min(hi, Math.max(lo, cam.x + rng.range(-g.reach, g.reach))), el.y - 0.3, midZ + rng.range(-halfZ, halfZ));
      G.fx.dust(flashPos, rng.range(g.scale[0], g.scale[1]));
      gritIn = rng.range(g.every[0], g.every[1]);
    }

    // The street shakes under a train: strongest beneath the deck, gone a few metres to either side.
    if (G.game && G.game.state === 'playing') {
      const side = Math.max(Math.abs(cam.z - midZ) - halfZ, 0);
      const amount = clamp01(1 - outside / 14) * clamp01(1 - side / cfg.shakeReach);
      if (amount > 0.02) G.player.addShake(cfg.shake * amount * dt);
    }
  }

  function update(dt, now) {
    if (!state.active) {
      if (now < schedule.nextAt) return;
      begin(schedule.begin(now));
    }
    local += dt;
    const phase = timeline.phase(local);
    if (phase === null) {
      end();
      return;
    }
    if (phase !== state.phase) {
      state.phase = phase;
      emit(phase, timeline[phase]);
    }

    const head = timeline.head(local);
    const tail = head - timeline.dir * length;
    state.x = head;
    state.lo = Math.min(head, tail);
    state.hi = Math.max(head, tail);
    group.position.x = head;

    // How much of the train is on the block: fades the stripes and the lamp stutter in and out.
    const presence = clamp01((Math.min(state.hi, bounds.maxX + 30) - Math.max(state.lo, bounds.minX - 30)) / 12);
    uPass.value.x = state.lo;
    uPass.value.y = state.hi;
    uPass.value.w = presence;
    uHead.value = head;
    shared.uTrain.value.set(state.lo, state.hi, presence);

    if (presence > 0) effects(dt);
  }

  return {
    state,
    schedule,
    timelines,
    update,
    textures: [sheets.map, sheets.emissiveMap],
    /** Starts a pass right now (debug, tests, trailers). `lead` = seconds before it reaches the block. */
    pass(dir = 1, lead = null) {
      const tl = timelines[dir < 0 ? -1 : 1];
      begin(dir, lead === null ? 0 : Math.max(0, tl.approach - lead));
    },
    setDetail(detail) {
      gritOn = detail.grit;
      grit.visible = gritOn && state.active;
    },
  };
}
