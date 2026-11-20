// The ROCKET's rounds in flight (src/config/weapons.js `rocket.projectile`).
//
// A round leaves the eye along the aim (what the crosshair covers is what it flies at), runs straight
// at `speed` and goes off on the first thing in its way: the world, a Vulture, an explosive, or within
// `fuse` metres of a Vulture it would otherwise pass. After `life` seconds it goes off where it is.
// The blast is G.combat.explode: the Vultures take it in full, Rule `playerScale` of it.
//
// The flight is rules, so it runs in a unit test with no renderer. With a scene there is a pooled model
// per round, drawn easing from the launcher's muzzle onto the true flight line, a pale smoke trail laid
// down every metre of the way and a light that travels with it.

import * as THREE from 'three';
import { cylGeo, mergeGeos } from '../core/geo.js';

const POOL = 4; // rounds in the air at once: the launcher holds one, a reload takes two seconds
const TIE = 0.03; // an explosive wins a tie with its own collider (see combat.js)
const BACK_OFF = 0.25; // the blast is centred this far short of what was hit, so walls do not shield it
const SETTLE = 0.22; // seconds for the drawn round to ease from the muzzle onto the flight line
const FORWARD = new THREE.Vector3(0, 0, -1);
const SOURCE = Object.freeze({ type: 'rocket', from: 'player' });

const has = (obj, method) => !!obj && typeof obj[method] === 'function';

/** The round: a tube with a pointed nose, four fins and a nozzle, nose toward −Z, origin at its middle. */
function roundGeometry() {
  const lie = (geo, z) => geo.rotateX(-Math.PI / 2).translate(0, 0, z);
  const parts = [
    lie(cylGeo(0.042, 0.46, 10), 0),
    lie(cylGeo(0.042, 0.16, 10, { radiusTop: 0.004 }), -0.31),
    lie(cylGeo(0.03, 0.06, 8, { radiusTop: 0.042 }), 0.26),
  ];
  for (let i = 0; i < 4; i++) {
    const fin = new THREE.BoxGeometry(0.004, 0.11, 0.12).translate(0, 0.07, 0.19).rotateZ((i * Math.PI) / 2);
    parts.push(fin);
  }
  return mergeGeos(parts);
}

export function createRockets(G) {
  const worldHit = { dist: 0, point: new THREE.Vector3(), normal: new THREE.Vector3(), surface: null, box: null };
  const centre = new THREE.Vector3();
  const closest = new THREE.Vector3();
  const tail = new THREE.Vector3();
  const back = new THREE.Vector3();
  const drawn = new THREE.Vector3();

  // Models: only with a scene and a material library to draw them from.
  let group = null;
  let warm = false;
  const canDraw = !!G.scene && has(G.mats, 'get') && has(G.mats, 'emissive');
  let bodyGeo = null;
  let glowGeo = null;
  if (canDraw) {
    try {
      bodyGeo = roundGeometry();
      // The motor's flame: a hot cone out of the nozzle, long enough to read from across the street.
      glowGeo = cylGeo(0.085, 0.62, 8, { radiusTop: 0.012 }).rotateX(Math.PI / 2).translate(0, 0, 0.58);
      group = new THREE.Group();
      group.name = 'rockets';
      G.scene.add(group);
    } catch (err) {
      console.warn('[weapon] rockets fly without a model:', err);
      group = null;
    }
  }

  const rounds = [];
  for (let i = 0; i < POOL; i++) {
    const round = {
      live: false,
      def: null,
      pos: new THREE.Vector3(),
      dir: new THREE.Vector3(0, 0, -1),
      offset: new THREE.Vector3(), // drawn position − true position, eased to nothing
      age: 0,
      trail: 0, // metres flown since the last wisp of smoke
      glow: 0,
      mesh: null,
    };
    if (group) {
      const mesh = new THREE.Group();
      const body = new THREE.Mesh(bodyGeo, G.mats.get('metal_dark'));
      const flame = new THREE.Mesh(glowGeo, G.mats.emissive(0xffb060, 9));
      body.frustumCulled = flame.frustumCulled = false;
      mesh.add(body, flame);
      // Shown once, far under the street, so the boot's shader warm-up compiles what a round needs and
      // the first launch does not wait for it. Hidden again by the first update.
      mesh.position.set(0, -200, 0);
      group.add(mesh);
      round.mesh = mesh;
    }
    rounds.push(round);
  }

  function hideAll() {
    for (const r of rounds) {
      r.live = false;
      if (r.mesh) r.mesh.visible = false;
    }
    warm = true;
  }

  /**
   * Sends a round off. `origin` is the eye, `dir` the aim (unit), `muzzle` where the launcher's mouth
   * is on screen (optional: without it the round is drawn on its flight line from the start).
   * The oldest round in the air goes off early when the pool is full.
   */
  function launch(def, origin, dir, muzzle) {
    let round = rounds.find((r) => !r.live);
    if (!round) {
      round = rounds.reduce((a, b) => (b.age > a.age ? b : a));
      detonate(round, 0);
    }
    round.live = true;
    round.def = def;
    round.pos.copy(origin);
    round.dir.copy(dir).normalize();
    round.age = 0;
    round.trail = 0;
    round.glow = 0;
    if (muzzle) round.offset.subVectors(muzzle, origin);
    else round.offset.set(0, 0, 0);
    if (round.mesh) {
      round.mesh.visible = true;
      round.mesh.quaternion.setFromUnitVectors(FORWARD, round.dir);
      round.mesh.position.copy(origin).add(round.offset);
    }
    return round;
  }

  /** The round goes off `dist` metres further along its line. */
  function detonate(round, dist) {
    const P = round.def.projectile;
    round.live = false;
    if (round.mesh) round.mesh.visible = false;
    centre.copy(round.pos).addScaledVector(round.dir, Math.max(0, dist - BACK_OFF));
    if (has(G.combat, 'explode')) {
      G.combat.explode({ pos: centre, radius: P.radius, damage: round.def.damage, playerScale: P.playerScale, source: SOURCE, weapon: round.def.id });
    }
  }

  /** How far along this step the round passes within `fuse` of a Vulture it can see, or Infinity. */
  function fuseDistance(round, reach, fuse) {
    const list = G.enemies && G.enemies.list;
    if (!list || !(fuse > 0)) return Infinity;
    let best = Infinity;
    for (let i = 0; i < list.length; i++) {
      const e = list[i];
      if (!e || !e.alive || !e.pos) continue;
      const cy = e.type === 'buzzard' ? e.pos.y : e.pos.y + (e.height || 1.8) * 0.55;
      const rx = e.pos.x - round.pos.x;
      const ry = cy - round.pos.y;
      const rz = e.pos.z - round.pos.z;
      const along = Math.min(reach, Math.max(0, rx * round.dir.x + ry * round.dir.y + rz * round.dir.z));
      if (along >= best) continue;
      closest.copy(round.pos).addScaledVector(round.dir, along);
      const dx = e.pos.x - closest.x;
      const dy = cy - closest.y;
      const dz = e.pos.z - closest.z;
      const near = fuse + (e.radius || 0.35);
      if (dx * dx + dy * dy + dz * dz > near * near) continue;
      // Still closing in on it: the fuse waits for the nearest point, which is in a later step.
      if (along >= reach && rx * round.dir.x + ry * round.dir.y + rz * round.dir.z > reach) continue;
      if (has(G.physics, 'lineOfSight') && !G.physics.lineOfSight(closest, centre.set(e.pos.x, cy, e.pos.z))) continue;
      best = along;
    }
    return best;
  }

  function fly(round, dt) {
    const P = round.def.projectile;
    const step = P.speed * dt;
    const world = has(G.physics, 'raycast') ? G.physics.raycast(round.pos, round.dir, step, worldHit) : null;
    let dist = world ? world.dist : step;
    let hit = !!world;
    const enemy = has(G.enemies, 'raycast') ? G.enemies.raycast(round.pos, round.dir, dist) : null;
    if (enemy && enemy.dist <= dist) {
      dist = enemy.dist;
      hit = true;
    }
    const item = has(G.explosives, 'raycast') ? G.explosives.raycast(round.pos, round.dir, dist + TIE) : null;
    if (item && item.dist <= dist + TIE) {
      dist = Math.min(dist, item.dist);
      hit = true;
    }
    const fuse = fuseDistance(round, dist, P.fuse);
    if (fuse <= dist) {
      dist = fuse;
      hit = true;
    }
    if (hit) {
      // The fuse goes off where the round is; anything solid, a little short of it.
      detonate(round, fuse <= dist ? dist + BACK_OFF : dist);
      return;
    }
    round.pos.addScaledVector(round.dir, step);
    round.age += dt;
    if (round.age >= P.life) {
      detonate(round, BACK_OFF);
      return;
    }
    draw(round, dt, step);
  }

  function draw(round, dt, step) {
    const P = round.def.projectile;
    const k = Math.exp(-dt / (SETTLE * 0.35));
    round.offset.multiplyScalar(k);
    drawn.copy(round.pos).add(round.offset);
    if (round.mesh) {
      round.mesh.position.copy(drawn);
      round.mesh.rotateZ(dt * 9); // a slow spin about its own axis
    }
    tail.copy(drawn).addScaledVector(round.dir, -0.34);
    // The trail: a wisp for every `trail` metres flown, laid back along this step so a slow frame
    // leaves no gap in it. (The first metres are the launcher's own smoke.)
    const fx = G.fx;
    round.trail += step;
    while (round.trail >= P.trail) {
      round.trail -= P.trail;
      back.copy(tail).addScaledVector(round.dir, -round.trail);
      // Motor smoke that hangs for a second or two, and a quick pale puff inside it.
      if (has(fx, 'smoke')) fx.smoke(back, 0.5);
      if (has(fx, 'puff')) fx.puff(back, 0xe9e5dc, 1.7);
    }
    if (has(fx, 'sparks')) fx.sparks(tail, back.copy(round.dir).negate(), 1);
    round.glow -= dt;
    if (round.glow <= 0) {
      round.glow = 0.05;
      const lights = G.render && G.render.lights;
      if (has(lights, 'flash')) lights.flash(tail, 0xffa040, 26, 9, 0.09);
    }
  }

  function update(dt) {
    if (!warm) hideAll();
    if (!(dt > 0)) return;
    for (let i = 0; i < rounds.length; i++) if (rounds[i].live) fly(rounds[i], dt);
  }

  /** A new run: whatever is in the air is gone, without a blast. */
  function reset() {
    hideAll();
  }

  return {
    rounds,
    launch,
    update,
    reset,
    get live() {
      let n = 0;
      for (let i = 0; i < rounds.length; i++) if (rounds[i].live) n++;
      return n;
    },
  };
}
