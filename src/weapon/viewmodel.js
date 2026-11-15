// What the player sees of the weapon: both guns, Rule's arms, the muzzle flash, and every motion.
//
// Everything is procedural. Each frame the gun's place in view space is built up in layers:
//   1. a base pose blended between HIP (three selectable views), SPRINT, RELOAD, WALL, AIM and HOLSTER
//   2. a keyed strike when a melee blow is thrown
//   3. small additive motion: breathing, footstep bob, look lag, movement inertia, jump / land
//   4. spring recoil about the gun's pivot
// The gun then says where its parts and the two hands are (chopper.js / nine.js) and the arms are solved
// onto it (arms.js). The rig hangs off G.vmCamera, so all of this is in view space.

import * as THREE from 'three';
import { clamp, clamp01, damp, lerp } from '../core/util.js';
import { blendPose, buildArms } from './arms.js';
import { buildChopper } from './chopper.js';
import { buildEnvironment, createFlashMaterial, createViewMaterial } from './material.js';
import { buildNine } from './nine.js';
import { ease, easeOutBack, softLimit, spring, stepSpring } from './springs.js';

// Feel of the additive layers. Lengths in metres, angles in radians.
const FEEL = {
  breathe: { hz: 0.25, y: 0.0013, pitch: 0.0032, roll: 0.0016 },
  bob: { y: [0.0036, 0.0105], x: [0.0034, 0.0075], roll: [0.008, 0.032], pitch: [0.004, 0.014], adsPos: 0.14, adsRot: 0.05, crouch: 0.72 },
  lag: { gain: 0.5, roll: 0.55, shift: 0.018, ads: 0.22 },
  inertia: { rate: 7.7, strafe: 0.0045, surge: 0.0035, lean: 0.045, fall: 0.0035, fallPitch: 0.012, ads: 0.25 },
  jump: 0.85, // upward kick on take-off, m/s into the land spring
  land: { perSpeed: 0.075, max: 14, roll: 0.5 },
  landSpring: [15, 0.45],
  bumpSpring: [26, 0.5],
  aimArc: { drop: 0.012, roll: 0.07 },
  triggerRate: 38,
};
const LAMP_EVERY = 0.25; // seconds between looks at the street lamps
const ONE = new THREE.Vector3(1, 1, 1);

export function createViewmodel(G) {
  const config = G.config.weapons;
  const common = config.common;
  const strides = (G.config.player && G.config.player.stride) || { walk: 1.55, sprint: 2.1, crouch: 1.05 };

  const materialOf = (name, fallback) => {
    try {
      return G.mats.get(name).color.getHex();
    } catch {
      return fallback;
    }
  };
  const environment = buildEnvironment(G.renderer);
  const material = createViewMaterial(environment);

  // ---------------------------------------------------------------------------------------------
  // Rig
  // ---------------------------------------------------------------------------------------------
  const rig = new THREE.Group();
  rig.name = 'viewmodel';
  rig.visible = false;
  G.vmCamera.add(rig);
  const gunPivot = new THREE.Group();
  rig.add(gunPivot);

  const gold = materialOf('gold', 0xe7b53a);
  const guns = {
    chopper: buildChopper(material, config.chopper),
    nine: buildNine(material, config.nine, config.melee.duration, gold),
  };
  for (const id in guns) gunPivot.add(guns[id].root);
  const arms = buildArms(material, materialOf('skin', 0x7a4a2e), gold);
  rig.add(arms.mesh);

  // Muzzle flash: one star facing back along the bore and two crossed jets ahead of the muzzle.
  const flash = (() => {
    const position = [];
    const uv = [];
    const kind = [];
    // Corners run u0v0, u1v0, u1v1, u0v1; for the jets u is the distance down the bore.
    const quad = (corners, k) => {
      for (const i of [0, 1, 2, 0, 2, 3]) {
        position.push(...corners[i]);
        uv.push(i === 1 || i === 2 ? 1 : 0, i >= 2 ? 1 : 0);
        kind.push(k);
      }
    };
    quad([[-0.5, -0.5, 0], [0.5, -0.5, 0], [0.5, 0.5, 0], [-0.5, 0.5, 0]], 0);
    quad([[0, -0.5, 0.02], [0, -0.5, -1], [0, 0.5, -1], [0, 0.5, 0.02]], 1);
    quad([[-0.5, 0, 0.02], [-0.5, 0, -1], [0.5, 0, -1], [0.5, 0, 0.02]], 1);
    // (near edge, far edge, far edge, near edge: u = 0 at the muzzle, 1 at the tip of the jet)
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(position, 3));
    geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    geometry.setAttribute('kind', new THREE.Float32BufferAttribute(kind, 1));
    const mesh = new THREE.Mesh(geometry, createFlashMaterial());
    mesh.name = 'muzzle-flash';
    mesh.frustumCulled = false;
    mesh.visible = false;
    mesh.renderOrder = 2;
    return mesh;
  })();
  gunPivot.add(flash);

  // Lights. Render owns a world-space key and ambient; these make the gun read at night:
  //   fill   camera space, cool: the faces turned toward the player are never black
  //   rim    world space, coloured by the street lamps around the player
  //   burst  at the muzzle, lit for the length of the flash
  const fill = new THREE.DirectionalLight(0xc8d4ff, 0.4);
  fill.position.set(-0.7, 0.55, 0.9);
  fill.target.position.set(0.1, -0.12, -0.4);
  rig.add(fill, fill.target);
  const rim = new THREE.DirectionalLight(0xffb45e, 0.6);
  rim.position.set(0.3, 1, -0.3);
  G.vmScene.add(rim, rim.target);
  const burst = new THREE.PointLight(0xffb060, 0, 2.5, 2);
  gunPivot.add(burst);

  // Dropped gun: lives in world coordinates in the viewmodel scene.
  const fallen = new THREE.Group();
  fallen.name = 'dropped-weapon';
  fallen.visible = false;
  G.vmScene.add(fallen);

  // ---------------------------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------------------------
  let current = 'chopper';
  let gun = guns[current];
  let def = config[current];
  let viewIndex = 0;
  let clock = 0;
  let shown = false;

  const aim = spring(0);
  let lastAdsLinear = 0;
  let aimTarget = 0;
  const recoil = { back: spring(), pitch: spring(), yaw: spring(), roll: spring(), side: spring(), up: spring() };
  const bump = { pitch: spring(), roll: spring(), y: spring() };
  const sway = { yaw: spring(), pitch: spring() };
  const land = spring();
  let landRoll = 1;
  let bobPhase = 0;
  let bobAmp = 0;
  const inertia = { x: 0, z: 0, lean: 0, fall: 0 };
  const lastVel = { x: 0, z: 0 };
  let reloadWeight = 0;
  let lastReloadT = 0;
  let shotAge = Infinity;
  let trigger = 0;
  let flashLife = 0;
  let flashTotal = 1;
  let flashScale = 1;
  let smokeLeft = 0;
  let smokeTimer = 0;
  let lampTimer = 0;
  const lampColor = new THREE.Color(0xffb45e);
  let lampPower = 0.3;
  const lampDir = new THREE.Vector3(0.3, 1, -0.3).normalize();
  const lampGoal = new THREE.Color(0xffb45e);
  const lampGoalDir = lampDir.clone();
  let lampGoalPower = 0.3;
  const tint = new THREE.Color();
  let inspect = null;
  let backdrop = null;
  const drop = { active: false, t: 0, bounces: 0, vel: new THREE.Vector3(), axis: new THREE.Vector3(1, 0, 0), spin: 0, rest: false };

  // Scratch.
  const pos = new THREE.Vector3();
  const quat = new THREE.Quaternion();
  const v0 = new THREE.Vector3();
  const v1 = new THREE.Vector3();
  const q0 = new THREE.Quaternion();
  const q1 = new THREE.Quaternion();
  const e0 = new THREE.Euler(0, 0, 0, 'YXZ');
  const m0 = new THREE.Matrix4();
  const m1 = new THREE.Matrix4();
  const gunMatrix = new THREE.Matrix4();
  const gunInverse = new THREE.Matrix4();
  const adsPose = { pos: new THREE.Vector3(), quat: new THREE.Quaternion() };
  const strike = [0, 0, 0, 0, 0, 0];
  const ctx = {
    anim: null,
    shotAge: Infinity,
    trigger: 0,
    dt: 0,
    right: { a: null, b: null, t: 0 },
    left: { a: null, b: null, t: 0 },
    magHeld: false,
  };

  // ---------------------------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------------------------

  const blendTo = (pose, t) => {
    if (t <= 0) return;
    pos.lerp(pose.pos, t);
    quat.slerp(pose.quat, t);
  };

  /** Turns the gun by q (view space) about its pivot point. */
  function turnAboutPivot(q) {
    v0.copy(gun.pivot).applyQuaternion(quat).add(pos); // pivot in view space
    pos.sub(v0).applyQuaternion(q).add(v0);
    quat.premultiply(q);
  }

  /** A hand key in view space. */
  function evalKey(key, outPos, outQuat) {
    if (key.space === 'gun') {
      outPos.copy(key.pos).applyMatrix4(gunMatrix);
      outQuat.copy(gunPivot.quaternion).multiply(key.quat);
    } else {
      outPos.copy(key.pos);
      outQuat.copy(key.quat);
    }
  }

  function placeHand(arm, track) {
    evalKey(track.a, arm.pos, arm.quat);
    if (track.t > 0 && track.b !== track.a) {
      evalKey(track.b, v0, q0);
      arm.pos.lerp(v0, track.t);
      arm.quat.slerp(q0, track.t);
      blendPose(arm.pose, track.a.pose, track.b.pose, track.t);
    } else {
      arm.pose.set(track.a.pose);
    }
  }

  /** View-space point → world space, corrected for the viewmodel's own field of view. */
  function toWorld(p, out) {
    const camera = G.camera;
    const k = Math.tan((camera.fov * Math.PI) / 360) / Math.tan((G.vmCamera.fov * Math.PI) / 360);
    return out.set(p.x * k, p.y * k, p.z).applyQuaternion(camera.quaternion).add(camera.position);
  }

  function retune() {
    for (const name in recoil) {
      recoil[name].x = 0;
      recoil[name].v = 0;
    }
  }

  function show(id) {
    current = id;
    gun = guns[id];
    def = config[id];
    for (const other in guns) guns[other].root.visible = guns[other] === gun;
    gun.root.visible = true;
    flash.position.copy(gun.muzzle);
    burst.position.copy(gun.muzzle).add(v0.set(0, 0.01, -0.06));
    flash.material.uniforms.uJet.value = def.auto ? 1 : 0.3;
    // Aimed: the rear sight sits on the view axis, `relief` in front of the eye, the bore parallel to it.
    adsPose.pos.set(-gun.sightRear.x, -gun.sightRear.y, -gun.relief - gun.sightRear.z);
    adsPose.quat.identity();
    retune();
  }

  function attach() {
    if (!drop.active) return;
    drop.active = false;
    fallen.visible = false;
    for (const id in guns) {
      const root = guns[id].root;
      if (root.parent !== gunPivot) gunPivot.add(root);
      root.position.set(0, 0, 0);
      root.quaternion.identity();
    }
    arms.mesh.visible = true;
  }

  // ---------------------------------------------------------------------------------------------
  // Layers
  // ---------------------------------------------------------------------------------------------

  /** The melee strike as offsets from the base pose (x, y, z, pitch, yaw, roll). */
  function sampleStrike(t) {
    const keys = gun.melee;
    let i = 0;
    while (i < keys.length - 2 && t >= keys[i + 1][0]) i++;
    const a = keys[i];
    const b = keys[i + 1];
    const k = ease((t - a[0]) / (b[0] - a[0]));
    for (let c = 0; c < 6; c++) strike[c] = a[c + 1] + (b[c + 1] - a[c + 1]) * k;
  }

  function updateLamps(dt) {
    lampTimer -= dt;
    const lamps = G.level && G.level.lamps;
    if (lampTimer <= 0 && lamps) {
      lampTimer = LAMP_EVERY;
      const eye = G.camera.position;
      let r = 0;
      let g = 0;
      let b = 0;
      let total = 0;
      v1.set(0, 0, 0);
      for (let i = 0; i < lamps.length; i++) {
        const lamp = lamps[i];
        const d = lamp.pos.distanceTo(eye);
        const reach = (lamp.range || 10) * 1.4;
        if (d >= reach) continue;
        const fall = 1 - d / reach;
        const w = (lamp.intensity || 10) * fall * fall;
        tint.set(lamp.color);
        r += tint.r * w;
        g += tint.g * w;
        b += tint.b * w;
        total += w;
        v1.addScaledVector(v0.subVectors(lamp.pos, eye).normalize(), w);
      }
      if (total > 0) {
        lampGoal.setRGB(r / total, g / total, b / total);
        lampGoalPower = clamp01(total / 30);
        if (v1.lengthSq() > 1e-6) lampGoalDir.copy(v1).normalize();
      } else {
        lampGoal.set(0x8fa4cc); // nothing near: moonlit
        lampGoalPower = 0.12;
        lampGoalDir.set(0.2, 1, 0.1).normalize();
      }
    }
    const k = 1 - Math.exp(-4 * dt);
    lampColor.lerp(lampGoal, k);
    lampPower += (lampGoalPower - lampPower) * k;
    lampDir.lerp(lampGoalDir, k).normalize();
    rim.color.copy(lampColor);
    rim.intensity = 0.12 + 1.3 * lampPower;
    rim.position.copy(lampDir);
  }

  function updateFlash(dt, anim) {
    if (flashLife > 0) {
      flashLife -= dt;
      const power = flashLife > 0 ? Math.sqrt(flashLife / flashTotal) : 0;
      flash.visible = power > 0;
      flash.material.uniforms.uPower.value = power;
      burst.intensity = power * (def.auto ? 1.5 : 1.0);
    } else if (flash.visible) {
      flash.visible = false;
      burst.intensity = 0;
    }
    // A hot barrel breathes smoke for a moment after a long burst.
    if (def.muzzleSmoke && G.fx && typeof G.fx.smoke === 'function') {
      if (shotAge < 0.02 && anim.heat > 0.4) smokeLeft = 1.6;
      if (smokeLeft > 0 && shotAge > 0.11) {
        smokeLeft -= dt;
        smokeTimer -= dt;
        if (smokeTimer <= 0) {
          smokeTimer = 0.085;
          v0.copy(gun.muzzle).applyMatrix4(gunMatrix);
          G.fx.smoke(toWorld(v0, v1), 0.22);
        }
      }
    }
  }

  function updateDrop(dt) {
    drop.t += dt;
    if (drop.rest) return;
    drop.vel.y -= 13.5 * dt;
    fallen.position.addScaledVector(drop.vel, dt);
    fallen.quaternion.premultiply(q0.setFromAxisAngle(drop.axis, drop.spin * dt));
    const p = fallen.position;
    const ground = (G.physics ? G.physics.groundHeight(p.x, p.z, p.y + 0.4) : 0) + 0.035;
    if (p.y <= ground && drop.vel.y < 0) {
      p.y = ground;
      if (drop.bounces < 3 && drop.vel.y < -0.6) {
        drop.bounces++;
        drop.vel.y *= -0.3;
        drop.vel.x *= 0.6;
        drop.vel.z *= 0.6;
        drop.spin *= 0.55;
      } else {
        drop.rest = true;
      }
    }
    if (drop.bounces > 0 || drop.rest) {
      // Comes to lie on its side, keeping whatever way it was pointing.
      e0.setFromQuaternion(fallen.quaternion, 'YXZ');
      q1.setFromEuler(e0.set(0, e0.y, e0.z >= 0 ? 1.45 : -1.45, 'YXZ'));
      fallen.quaternion.slerp(q1, 1 - Math.exp(-(drop.rest ? 14 : 5) * dt));
    }
  }

  // ---------------------------------------------------------------------------------------------
  // Frame
  // ---------------------------------------------------------------------------------------------

  function update(dt, anim) {
    const player = G.player;
    const input = G.input;
    if (!player || !(dt > 0)) return;
    clock += dt;
    shotAge += dt;
    if (anim.id !== current && !drop.active) show(anim.id);

    const a = clamp01(anim.ads);
    const calm = 1 - a;

    // Aim: a spring that leaves when the ramp starts and lands when it ends.
    if (anim.adsLinear > lastAdsLinear) aimTarget = 1;
    else if (anim.adsLinear < lastAdsLinear) aimTarget = 0;
    else aimTarget = anim.adsLinear >= 0.5 ? 1 : 0;
    lastAdsLinear = anim.adsLinear;
    stepSpring(aim, aimTarget, def.adsSpring[0], def.adsSpring[1], dt);
    const aimed = clamp01(aim.x);

    // Reload pose weight: in over the first moments, out over the last.
    if (anim.reloading) {
      const total = anim.reloadEmpty ? def.reload.empty : def.reload.tactical;
      const t = anim.reloadT;
      reloadWeight = Math.min(ease(t / 0.24), ease((total - t) / 0.3));
      const R = def.reload;
      const crossed = (mark) => mark !== undefined && lastReloadT < mark && t >= mark;
      if (crossed(R.magInsert)) bump.y.v += 0.12;
      if (crossed(R.tug)) {
        bump.y.v -= 0.2;
        bump.pitch.v -= 0.5;
      }
      if (crossed(R.boltRelease) && anim.reloadEmpty) {
        recoil.back.v -= 0.5;
        bump.pitch.v -= 0.9;
      }
      lastReloadT = t;
    } else {
      reloadWeight = damp(reloadWeight, 0, 16, dt);
      lastReloadT = 0;
    }

    // ---- 1. base pose --------------------------------------------------------------------------
    const hip = gun.poses.hip[viewIndex] || gun.poses.hip[0];
    pos.copy(hip.pos);
    quat.copy(hip.quat);
    if (inspect) {
      pos.set(inspect.x || 0, inspect.y || 0, -(inspect.dist || 0.6));
      quat.setFromEuler(e0.set(inspect.pitch || 0, inspect.yaw || 0, inspect.roll || 0, 'YXZ'));
    } else {
      blendTo(gun.poses.sprint, anim.sprint);
      blendTo(gun.poses.reload, reloadWeight);
      blendTo(gun.poses.wall, anim.wall);
      blendTo(adsPose, aimed);
      // Holster: down and away, the swap happens out of sight, then up with a little overshoot.
      if (anim.switching) {
        blendTo(gun.poses.holster, anim.switching === 'holster' ? ease(anim.switchK) : 1 - easeOutBack(anim.switchK));
      } else if (drop.active) {
        blendTo(gun.poses.holster, ease(drop.t / 0.3));
      }

      // ---- 2. melee strike ---------------------------------------------------------------------
      if (anim.melee) {
        sampleStrike(anim.meleeT);
        pos.x += strike[0];
        pos.y += strike[1];
        pos.z += strike[2];
        turnAboutPivot(q0.setFromEuler(e0.set(strike[3], strike[4], strike[5], 'YXZ')));
      }

      // ---- 3. additive motion ------------------------------------------------------------------
      // Footstep bob, in step with the player's stride.
      const speed = player.speed || 0;
      const stride = player.crouching ? strides.crouch : player.sprinting ? strides.sprint : strides.walk;
      if (player.onGround !== false && speed > 0.3) bobPhase += (speed * dt) / stride;
      const gait = player.onGround === false ? 0 : (speed / 3.8) ** 0.8 * (player.crouching ? FEEL.bob.crouch : 1);
      bobAmp = damp(bobAmp, gait, 9, dt);
      const run = anim.sprint;
      const B = FEEL.bob;
      const posScale = lerp(1, B.adsPos, a) * bobAmp;
      const rotScale = lerp(1, B.adsRot, a) * bobAmp;
      const step = Math.sin(bobPhase * Math.PI); // one swing per two steps
      const bounce = Math.cos(bobPhase * Math.PI * 2); // one dip per step
      let offX = step * lerp(B.x[0], B.x[1], run) * posScale;
      let offY = -bounce * lerp(B.y[0], B.y[1], run) * posScale;
      let offZ = 0;
      let pitch = bounce * lerp(B.pitch[0], B.pitch[1], run) * rotScale;
      let yaw = 0;
      let roll = step * lerp(B.roll[0], B.roll[1], run) * rotScale;

      // Breathing.
      const breath = clock * FEEL.breathe.hz * Math.PI * 2;
      const still = lerp(1, 0.18, a);
      offY += Math.sin(breath) * FEEL.breathe.y * still;
      pitch += Math.sin(breath + 1.1) * FEEL.breathe.pitch * still;
      roll += Math.sin(breath * 0.5 + 0.4) * FEEL.breathe.roll * still;

      // Look lag: the gun trails the view and rolls against the turn.
      const L = FEEL.lag;
      const lagScale = lerp(1, L.ads, a);
      if (input && input.look) {
        sway.yaw.x = softLimit(sway.yaw.x + input.look.dx * L.gain, def.swayMax);
        sway.pitch.x = softLimit(sway.pitch.x + input.look.dy * L.gain, def.swayMax);
      }
      stepSpring(sway.yaw, 0, def.swaySpring[0], def.swaySpring[1], dt);
      stepSpring(sway.pitch, 0, def.swaySpring[0], def.swaySpring[1], dt);
      yaw += sway.yaw.x * lagScale;
      pitch += sway.pitch.x * lagScale;
      roll += sway.yaw.x * L.roll * lagScale;
      offX -= sway.yaw.x * L.shift * lagScale;

      // Movement inertia: starts and stops push the gun the other way, strafes lean it.
      const I = FEEL.inertia;
      const sin = Math.sin(player.yaw || 0);
      const cos = Math.cos(player.yaw || 0);
      const vel = player.vel;
      const vx = vel ? vel.x * cos - vel.z * sin : 0; // to the right
      const vz = vel ? -vel.x * sin - vel.z * cos : 0; // forward
      const ax = (vx - lastVel.x) / dt;
      const az = (vz - lastVel.z) / dt;
      lastVel.x = vx;
      lastVel.z = vz;
      inertia.x = damp(inertia.x, clamp(ax, -40, 40) / 40, I.rate, dt);
      inertia.z = damp(inertia.z, clamp(az, -40, 40) / 40, I.rate, dt);
      inertia.lean = damp(inertia.lean, clamp(vx / 6.4, -1, 1), I.rate, dt);
      inertia.fall = damp(inertia.fall, player.onGround === false && vel ? clamp(vel.y, -12, 8) : 0, I.rate, dt);
      const drift = lerp(1, I.ads, a);
      offX -= inertia.x * I.strafe * drift;
      offZ += inertia.z * I.surge * drift;
      roll -= inertia.lean * I.lean * drift;
      offY -= inertia.fall * I.fall * drift;
      pitch += inertia.fall * I.fallPitch * drift;

      // Jump / land spring, and the generic bump spring (dry click, magazine seating…).
      stepSpring(land, 0, FEEL.landSpring[0], FEEL.landSpring[1], dt);
      offY += land.x * lerp(1, 0.4, a);
      pitch += land.x * 1.6 * lerp(1, 0.3, a);
      roll += land.x * FEEL.land.roll * landRoll * calm;
      for (const name in bump) stepSpring(bump[name], 0, FEEL.bumpSpring[0], FEEL.bumpSpring[1], dt);
      offY += bump.y.x;
      pitch += bump.pitch.x;
      roll += bump.roll.x;

      // Aim arc: the gun dips and cants slightly on its way to the eye.
      const arc = Math.sin(clamp01(aimed) * Math.PI);
      offY -= arc * FEEL.aimArc.drop;
      roll += arc * FEEL.aimArc.roll;

      // ---- 4. recoil ---------------------------------------------------------------------------
      const S = def.kick.springs;
      stepSpring(recoil.back, 0, S.back[0], S.back[1], dt);
      stepSpring(recoil.pitch, 0, S.pitch[0], S.pitch[1], dt);
      stepSpring(recoil.yaw, 0, S.yaw[0], S.yaw[1], dt);
      stepSpring(recoil.roll, 0, S.roll[0], S.roll[1], dt);
      stepSpring(recoil.side, 0, S.pos[0], S.pos[1], dt);
      stepSpring(recoil.up, 0, S.pos[0], S.pos[1], dt);
      pitch += recoil.pitch.x;
      yaw += recoil.yaw.x;
      roll += recoil.roll.x;
      offX += recoil.side.x;
      offY += recoil.up.x;

      turnAboutPivot(q0.setFromEuler(e0.set(pitch, yaw, roll, 'YXZ')));
      pos.x += offX;
      pos.y += offY;
      pos.z += offZ;
      pos.addScaledVector(v0.set(0, 0, 1).applyQuaternion(quat), recoil.back.x); // straight back along the bore
    }

    gunPivot.position.copy(pos);
    gunPivot.quaternion.copy(quat);
    gunMatrix.compose(pos, quat, ONE);

    // ---- parts and hands -------------------------------------------------------------------------
    trigger = damp(trigger, anim.trigger ? 1 : 0, FEEL.triggerRate, dt);
    ctx.anim = anim;
    ctx.dt = dt;
    ctx.shotAge = shotAge;
    ctx.trigger = trigger;
    ctx.magHeld = false;
    gun.animate(ctx);
    placeHand(arms.right, ctx.right);
    placeHand(arms.left, ctx.left);
    if (ctx.magHeld) {
      // The magazine goes where the left hand takes it.
      gunInverse.copy(gunMatrix).invert();
      m0.compose(arms.left.pos, arms.left.quat, ONE).premultiply(gunInverse).multiply(gun.magInHand);
      m0.decompose(gun.meshes.mag.position, gun.meshes.mag.quaternion, v0);
    }
    arms.right.elbow.copy(gun.elbows.right);
    arms.left.elbow.copy(gun.elbows.left);
    if (drop.active) {
      // Empty hands fall away.
      const sink = Math.min(drop.t, 0.4) * 1.6;
      arms.right.pos.y -= sink;
      arms.left.pos.y -= sink;
      if (drop.t > 0.4) arms.mesh.visible = false;
      updateDrop(dt);
    }
    arms.update();

    updateFlash(dt, anim);
    updateLamps(dt);
  }

  // ---------------------------------------------------------------------------------------------
  // Events from the rules
  // ---------------------------------------------------------------------------------------------

  const signed = () => Math.random() * 2 - 1;

  function fire(shot, emptied, ads, crouching) {
    const K = def.kick;
    const first = shot === 1 ? K.firstShot : shot === 2 ? K.secondShot : 1;
    const c = crouching ? K.crouch : 1;
    const vary = () => (1 + signed() * K.random) * c;
    const back = lerp(1, K.ads.back, ads);
    const rot = lerp(1, K.ads.rot, ads);
    const shift = lerp(1, K.ads.pos, ads);
    recoil.back.v += K.back * first * vary() * back;
    recoil.pitch.v += K.rise * first * vary() * rot;
    recoil.yaw.v += signed() * K.yaw * vary() * rot;
    recoil.roll.v += signed() * K.roll * vary() * rot;
    recoil.up.v += K.up * vary() * shift;
    recoil.side.v += signed() * K.side * vary() * shift;

    shotAge = 0;
    const [short, long] = common.flashSeconds;
    flashTotal = flashLife = lerp(short, long, Math.random());
    flashScale = (0.8 + 0.5 * Math.random()) * lerp(1, common.adsFlashScale, ads);
    const { star, jet } = gun.flash;
    flash.scale.set(star * flashScale, star * flashScale, jet * flashScale);
    flash.rotation.z = signed() * 0.6;
    flash.material.uniforms.uSeed.value = Math.random() * 100;
    flash.material.uniforms.uPower.value = 1;
    flash.visible = true;
    burst.intensity = def.auto ? 1.5 : 1.0;
  }

  const view = {
    info: {
      triangles: { chopper: guns.chopper.triangles, nine: guns.nine.triangles, arms: arms.triangles },
    },
    equip: show,
    fire,
    dry() {
      bump.pitch.v += 0.35;
      bump.y.v -= 0.04;
    },
    reloadPhase(phase, empty) {
      if (phase === 'magout') {
        bump.y.v += 0.1;
        bump.roll.v += 0.5;
      } else if (phase === 'magin') {
        bump.y.v += 0.3;
        bump.pitch.v += 0.7;
      } else if (phase === 'bolt') {
        if (def.auto) recoil.back.v += empty ? 0.5 : 0.2;
        else {
          // The Nine's slide slams home.
          recoil.pitch.v += 2.4;
          recoil.back.v -= 0.25;
        }
      }
    },
    switchPhase() {},
    meleeStart() {},
    meleeLand(hit, solid) {
      if (solid) {
        recoil.back.v += hit ? 1.4 : 0.9;
        bump.roll.v += 0.8;
      }
    },
    drop() {
      if (drop.active) return;
      drop.active = true;
      drop.t = 0;
      drop.bounces = 0;
      drop.rest = false;
      // Hand the model over to world space where it is right now.
      const camera = G.camera;
      m0.compose(camera.position, camera.quaternion, ONE).multiply(gunMatrix);
      m0.decompose(fallen.position, fallen.quaternion, v0);
      fallen.add(gun.root);
      fallen.visible = shown;
      v0.set(0.7, 1.1, -1.3).applyQuaternion(camera.quaternion);
      drop.vel.copy(v0);
      if (G.player && G.player.vel) drop.vel.add(G.player.vel);
      drop.axis.set(0.5, 0.3, -1).applyQuaternion(camera.quaternion).normalize();
      drop.spin = 5.5;
    },
    pickUp: attach,
    reset(id) {
      attach();
      show(id);
      aim.x = aim.v = 0;
      lastAdsLinear = 0;
      for (const set of [bump, sway]) for (const name in set) set[name].x = set[name].v = 0;
      land.x = land.v = 0;
      bobAmp = 0;
      bobPhase = 0;
      inertia.x = inertia.z = inertia.lean = inertia.fall = 0;
      reloadWeight = 0;
      shotAge = Infinity;
      trigger = 0;
      flashLife = 0;
      flash.visible = false;
      burst.intensity = 0;
      smokeLeft = 0;
    },
    /** World position of the muzzle as the player sees it. */
    muzzleWorld(out) {
      v0.copy(gun.muzzle).applyMatrix4(gunMatrix);
      toWorld(v0, out);
      return true;
    },
    /** World position of the ejection port and a velocity for the casing. */
    ejectWorld(out, velocity) {
      v0.copy(gun.eject).applyMatrix4(gunMatrix);
      toWorld(v0, out);
      velocity.set(2 + Math.random() * 1.2, 1.2 + Math.random() * 0.8, Math.random() - 0.5).applyQuaternion(G.camera.quaternion);
      if (G.player && G.player.vel) velocity.add(G.player.vel);
      return true;
    },
    setVisible(on) {
      shown = !!on;
      rig.visible = shown;
      // A gun dropped at death stays on the ground until the run is over.
      if (shown) fallen.visible = drop.active;
    },
    setView(n) {
      viewIndex = clamp((n | 0) - 1, 0, 2);
    },
    inspect(spec) {
      inspect = spec || null;
      const want = !!(spec && spec.backdrop);
      if (want && !backdrop) {
        backdrop = new THREE.Mesh(new THREE.PlaneGeometry(8, 5), new THREE.MeshBasicMaterial({ color: 0x3b3f46 }));
        backdrop.position.z = -2.5;
        rig.add(backdrop);
      }
      if (backdrop) backdrop.visible = want;
    },
    update,
  };

  if (G.events) {
    G.events.on('player:step', () => {
      bobPhase = Math.round(bobPhase); // stay in step with the footfalls
    });
    G.events.on('player:jump', () => {
      land.v += FEEL.jump;
    });
    G.events.on('player:land', (e) => {
      land.v -= Math.min((e && e.speed) || 0, FEEL.land.max) * FEEL.land.perSpeed;
      landRoll = -landRoll;
    });
    G.events.on('game:state', (e) => {
      if (e && e.state !== 'dead' && e.state !== 'playing' && e.state !== 'paused') fallen.visible = false;
    });
  }

  show(current);
  return view;
}

