// MURDER INC. — the player (CONTRACT 6.4): Rule's body, his health and the first-person camera.
//
// Movement, jump, crouch, sprint, fall damage, health and every camera layer follow reference notes 01;
// the numbers live in src/config/player.js. The body is a vertical cylinder moved by physics.moveCapsule
// (wall slide, 0.42 m step-up, ground snap); this module decides where it wants to go and what the eye sees.
//
// The view is built in layers, innermost first:
//   aim            yaw / pitch from the look input, plus the permanent share of every weapon kick
//   recoil         the recoverable share of a kick: snaps on, lets go after a short hold (moves the aim too)
//   eye            eye height (stand / crouch), stride bob, the landing spring, stair smoothing
//   roll           strafe lean and the sideways bob
//   shake          trauma² on three axes (camera only: bullets do not follow it)
//   death          the camera drops to the floor and onto its side
//
// Sign conventions shared with the input module: yaw 0 looks at −Z and grows turning left, pitch grows
// looking up; look.dx > 0 turns right, look.dy > 0 looks down.
//
// Beyond the contract the module exposes `player.stridePhase` (footstep phase, a whole number at every
// footfall, wraps at 2), `player.eyeHeight` and `player.trauma` as read-only extras, and exports its
// pure parts (speed rule, acceleration model, recoil, shake, landing spring) for the unit tests.

import * as THREE from 'three';
import * as TUNING from './config/player.js';
import { clamp, clamp01, damp, expDecay, lerp, paramOn, smoothstep, wrapAngle } from './core/util.js';

const TAU = Math.PI * 2;
const SPRING_STEP = 1 / 120; // the landing spring is integrated in steps no longer than this
const ADS_FALLBACK_RATE = 14; // aim amount without a weapon module: damp toward the aim input
const FALL_LIMIT = -30; // feet below this: the world was left somehow, go back to solid ground

/* ------------------------------------------------------------------------------------ pure parts */

/** Take-off speed that peaks `apex` metres up under `gravity`. */
export const jumpSpeed = (gravity, apex) => Math.sqrt(2 * gravity * apex);

/**
 * The ground speed the player is trying to reach: walk, crouch or sprint, capped while aiming, slower
 * backing up. `ads` is the aim amount 0…1, `forward` the forward input −1…1.
 */
export function targetSpeed(speeds, crouching, sprinting, ads, forward) {
  let v = crouching ? speeds.crouch : sprinting ? speeds.sprint : speeds.walk;
  v = lerp(v, Math.min(v, speeds.ads), clamp01(ads));
  if (forward < 0) v *= lerp(1, speeds.backpedal, Math.min(1, -forward));
  return v;
}

/** The sprint rule: held, pushing forward, not strafing hard, standing, not aiming, not firing. */
export function sprintWanted(rules, held, forward, strafe, crouching, ads, firing) {
  return !!held && forward > rules.minForward && Math.abs(strafe) < rules.maxStrafe && !crouching && ads < rules.maxAds && !firing;
}

/**
 * Moves a horizontal velocity straight toward (wishX, wishZ) by at most rate·dt: a move-toward in
 * velocity space, not a friction model. Closer than one step, the velocity snaps to the target when
 * `snap` is set (on the ground, or with input) and is left alone otherwise.
 */
export function approachVelocity(vel, wishX, wishZ, rate, dt, snap = true) {
  const ex = wishX - vel.x;
  const ez = wishZ - vel.z;
  const error = Math.sqrt(ex * ex + ez * ez);
  const step = rate * dt;
  if (error <= step) {
    if (snap) {
      vel.x = wishX;
      vel.z = wishZ;
    }
    return;
  }
  vel.x += (ex / error) * step;
  vel.z += (ez / error) * step;
}

/**
 * Camera recoil. A kick is split in two: `keep` of it belongs to the aim for good (the caller adds that
 * to yaw / pitch), the rest becomes an offset the view snaps onto and, after a short hold, lets go of.
 */
export function createRecoil(tune) {
  const recoil = {
    pitch: 0, // the offset on screen right now
    yaw: 0,
    targetPitch: 0, // what it chases
    targetYaw: 0,
    sinceKick: Infinity,
    /** Adds the recoverable share of a kick (radians; pitch up, yaw left). */
    kick(pitch, yaw) {
      const share = 1 - tune.keep;
      recoil.targetPitch = clamp(recoil.targetPitch + pitch * share, -tune.maxPitch, tune.maxPitch);
      recoil.targetYaw = clamp(recoil.targetYaw + yaw * share, -tune.maxYaw, tune.maxYaw);
      recoil.sinceKick = 0;
    },
    update(dt) {
      recoil.sinceKick += dt;
      // Only the part of this step that lies past the hold recentres: the same curve at any frame rate.
      const past = Math.min(dt, recoil.sinceKick - tune.hold);
      if (past > 0) {
        recoil.targetPitch = expDecay(recoil.targetPitch, tune.recover, past);
        recoil.targetYaw = expDecay(recoil.targetYaw, tune.recover, past);
      }
      recoil.pitch = damp(recoil.pitch, recoil.targetPitch, tune.chase, dt);
      recoil.yaw = damp(recoil.yaw, recoil.targetYaw, tune.chase, dt);
    },
    reset() {
      recoil.pitch = recoil.yaw = recoil.targetPitch = recoil.targetYaw = 0;
      recoil.sinceKick = Infinity;
    },
  };
  return recoil;
}

/**
 * Screen shake: one trauma value 0…1 that decays linearly; the camera turns by trauma² times two
 * sines per axis. Deterministic, no noise.
 *
 * Two kinds of sources feed it. Impulses (a hit, a shot, a landing) add trauma. Trickles — a train
 * overhead adding a sliver every frame — would be eaten by the linear decay before they showed, so
 * anything smaller than `sustain.below` per call is read as a rate instead and holds the shake at
 * rate / decay while it keeps coming.
 */
export function createShake(tune) {
  let trickle = 0; // trauma that arrived in slivers since the last update
  let sustained = 0; // the level those slivers hold
  let impulse = 0;
  const shake = {
    trauma: 0, // what the camera shows: the larger of the two
    time: 0,
    pitch: 0,
    yaw: 0,
    roll: 0,
    add(x) {
      if (!(x > 0)) return;
      if (x < tune.sustain.below) trickle += x;
      else impulse = Math.min(1, impulse + x);
      shake.trauma = Math.max(impulse, sustained);
    },
    /** Raises the trauma to `x` if it is lower (a source that someone else may have added already). */
    atLeast(x) {
      if (x > impulse) impulse = Math.min(1, x);
      shake.trauma = Math.max(impulse, sustained);
    },
    update(dt) {
      shake.time += dt;
      impulse = Math.max(0, impulse - tune.decay * dt);
      const level = dt > 0 ? Math.min(tune.sustain.max, trickle / dt / tune.decay) : 0;
      trickle = 0;
      sustained = damp(sustained, level, tune.sustain.rate, dt);
      if (sustained < 1e-4) sustained = 0;
      shake.trauma = Math.max(impulse, sustained);
      const power = shake.trauma * shake.trauma;
      if (power === 0) {
        shake.pitch = shake.yaw = shake.roll = 0;
        return;
      }
      const t = shake.time;
      const f = tune.freq;
      shake.pitch = tune.pitch * power * (Math.sin(t * f.pitch[0]) + Math.sin(t * f.pitch[1] + 1.3));
      shake.yaw = tune.yaw * power * (Math.sin(t * f.yaw[0] + 2.1) + Math.sin(t * f.yaw[1] + 0.4));
      shake.roll = tune.roll * power * (Math.sin(t * f.roll[0] + 4.2) + Math.sin(t * f.roll[1] + 3.3));
    },
    reset() {
      trickle = sustained = impulse = 0;
      shake.trauma = shake.pitch = shake.yaw = shake.roll = 0;
    },
  };
  return shake;
}

/** The landing dip: a damped spring on a vertical eye offset, held inside [min, max] metres. */
export function createSpring(tune) {
  const spring = {
    offset: 0,
    velocity: 0,
    /** An impulse in m/s (negative = down). */
    kick(v) {
      spring.velocity += v;
    },
    update(dt) {
      let left = dt;
      while (left > 1e-7) {
        const h = Math.min(left, SPRING_STEP);
        left -= h;
        spring.velocity += (-tune.stiffness * spring.offset - tune.damping * spring.velocity) * h;
        spring.offset += spring.velocity * h;
        if (spring.offset < tune.min) {
          spring.offset = tune.min;
          if (spring.velocity < 0) spring.velocity = 0;
        } else if (spring.offset > tune.max) {
          spring.offset = tune.max;
          if (spring.velocity > 0) spring.velocity = 0;
        }
      }
    },
    reset() {
      spring.offset = spring.velocity = 0;
    },
  };
  return spring;
}

/* ---------------------------------------------------------------------------------------- module */

export function createPlayer(G) {
  const override = (G.config && G.config.player) || {};
  const tune = (name) => ({ ...TUNING[name], ...override[name] });
  const body = tune('body');
  const speeds = tune('speed');
  const accel = tune('accel');
  const jump = tune('jump');
  const sprint = tune('sprint');
  const stride = tune('stride');
  const look = tune('look');
  const fov = tune('fov');
  const health = tune('health');
  const fall = tune('fall');
  const bob = tune('bob');
  const recoilTune = tune('recoil');
  const shakeTune = tune('shake');
  const death = tune('death');

  const physics = G.physics;
  const takeOff = jumpSpeed(jump.gravity, jump.apex);
  const sprintSpeed = speeds.walk * sprint.minSpeedFrac; // slower than this, the sprinting flag stays off
  const fixedFov = !!(G.params && G.params.fov); // a debug FOV override wins (main.js applies it)
  const god = !!G.params && paramOn(G.params, 'god');

  const pos = new THREE.Vector3();
  const vel = new THREE.Vector3();
  const eye = new THREE.Vector3();
  const forward = new THREE.Vector3(0, 0, -1);
  const lastSafe = new THREE.Vector3(); // last spot the body stood on
  const moved = { onGround: true, hitWall: false, hitCeil: false, surface: 'asphalt' }; // reused moveCapsule result

  const recoil = createRecoil(recoilTune);
  const shake = createShake(shakeTune);
  const spring = createSpring(bob.spring);
  // The eye's lag behind a body that just popped up or down a step: critically damped, so a flight of
  // stairs reads as a ramp with a faint rhythm instead of a row of jolts.
  const stepFrequency = bob.step.frequency;
  const stepLag = createSpring({
    stiffness: stepFrequency * stepFrequency,
    damping: 2 * stepFrequency,
    min: -bob.step.max,
    max: bob.step.max,
  });

  let eyeHeight = body.eye;
  let coyote = 0; // seconds a jump is still allowed after leaving the ground
  let jumpBuffer = 0; // seconds a jump press is remembered
  let airTime = 0;
  let fallSpeed = 0; // fastest descent of the current fall
  let stridePhase = 0; // distance walked in strides; a footstep at every whole number, wraps at 2
  let bobAmp = 0;
  let strafeRoll = 0;
  let sinceHit = Infinity;
  let hurt = 0; // red flash, feeds render.post.damage
  let blast = 0; // shake owed for explosions since the last update
  let lowHealth = 0;
  let baseFov = fov.base;
  let viewFov = fov.base;
  let deadTime = 0;
  let eyeAtDeath = body.eye;
  let deathSide = 1; // which shoulder the camera falls onto
  // Camera layers on top of the aim, refreshed by update() and applied by placeView().
  let bobX = 0;
  let bobY = 0;
  let viewPitch = 0;
  let viewRoll = 0;

  const player = {
    pos,
    vel,
    yaw: 0,
    pitch: 0,
    eye,
    forward,
    health: health.max,
    maxHealth: health.max,
    alive: true,
    onGround: true,
    sprinting: false,
    crouching: false,
    speed: 0, // horizontal, m/s
    ads: 0, // written by the weapon each frame
    enabled: true,
    invulnerable: false,
    regen: { delay: health.regenDelay, rate: health.regenRate },
    surface: 'asphalt',
    reset,
    damage,
    heal,
    addRecoil,
    turn,
    addShake,
    setFov,
    update,
    // Read-only extras (not part of the contract).
    get stridePhase() {
      return stridePhase;
    },
    get eyeHeight() {
      return eyeHeight;
    },
    get trauma() {
      return shake.trauma;
    },
  };

  const emit = (name, payload) => G.events && G.events.emit(name, payload);
  const down = (action) => !!G.input && G.input.down(action);
  const pressed = (action) => !!G.input && G.input.pressed(action);

  /** Room to stand up from a crouch? */
  function canStand() {
    if (typeof physics.overlapsCylinder !== 'function') return true;
    const from = pos.y + body.crouchHeight - body.standClearance;
    return !physics.overlapsCylinder(pos.x, pos.z, body.radius * body.footprint, from, pos.y + body.height);
  }

  /* ---------------------------------------------------------------------------- public methods */

  function reset(spawn = {}) {
    if (spawn.pos) pos.copy(spawn.pos);
    vel.set(0, 0, 0);
    lastSafe.copy(pos);
    player.yaw = Number.isFinite(spawn.yaw) ? spawn.yaw : 0;
    player.pitch = 0;
    player.health = player.maxHealth;
    player.alive = true;
    player.onGround = true;
    player.sprinting = false;
    player.crouching = false;
    player.speed = 0;
    player.ads = 0;
    player.invulnerable = false;
    eyeHeight = eyeAtDeath = body.eye;
    coyote = jumpBuffer = airTime = fallSpeed = 0;
    stridePhase = bobAmp = strafeRoll = 0;
    bobX = bobY = viewPitch = viewRoll = 0;
    sinceHit = Infinity;
    hurt = blast = lowHealth = deadTime = 0;
    deathSide = 1;
    viewFov = baseFov;
    recoil.reset();
    shake.reset();
    spring.reset();
    stepLag.reset();
    writePost();
    placeView();
  }

  function damage(amount, from = null, kind = 'bullet') {
    if (!player.alive || player.invulnerable || god || !(amount > 0) || !Number.isFinite(amount)) return;
    player.health = Math.max(0, player.health - amount);
    sinceHit = 0;
    const pulse = health.hurtPulse;
    hurt = Math.min(1, hurt + pulse.base + amount * pulse.perDamage);
    shake.add(shakeTune.onHit.base + amount * shakeTune.onHit.perDamage);
    emit('player:hit', { amount, from, health: player.health, kind });
    if (player.health <= 0) die(from);
  }

  function die(from) {
    player.alive = false;
    player.sprinting = false;
    deadTime = 0;
    eyeAtDeath = eyeHeight;
    // Fall away from whatever hit: a shot from the left drops the camera onto its right shoulder
    // (a negative roll), anything else onto the left one.
    deathSide = 1;
    if (from && Number.isFinite(from.x) && Number.isFinite(from.z)) {
      const side = (from.x - pos.x) * Math.cos(player.yaw) - (from.z - pos.z) * Math.sin(player.yaw);
      if (side < 0) deathSide = -1;
    }
    emit('player:dead', { from });
  }

  function heal(n) {
    if (player.alive && n > 0 && Number.isFinite(n)) player.health = Math.min(player.maxHealth, player.health + n);
  }

  /** A weapon kick in radians: pitch up, yaw left. 35 % stays in the aim, the rest springs back. */
  function addRecoil(pitch, yaw = 0) {
    if (!Number.isFinite(pitch) || !Number.isFinite(yaw)) return;
    player.pitch = clamp(player.pitch + pitch * recoilTune.keep, -look.pitchLimit, look.pitchLimit);
    player.yaw = wrapAngle(player.yaw + yaw * recoilTune.keep);
    recoil.kick(pitch, yaw);
    // The weapon runs after the player in a frame: refresh the aim so a second round fired in the same
    // frame, and this frame's picture, already carry the permanent share.
    if (player.alive) placeView();
  }

  /**
   * Turns the aim by these angles in radians (yaw + to the left, pitch + up): the weapon's aim assist.
   * Like a kick, it is already in this frame's aim and picture.
   */
  function turn(yaw, pitch = 0) {
    if (!Number.isFinite(yaw) || !Number.isFinite(pitch)) return;
    player.yaw = wrapAngle(player.yaw + yaw);
    player.pitch = clamp(player.pitch + pitch, -look.pitchLimit, look.pitchLimit);
    if (player.alive) placeView();
  }

  function addShake(trauma) {
    if (Number.isFinite(trauma)) shake.add(trauma);
  }

  function setFov(deg) {
    if (Number.isFinite(deg)) baseFov = clamp(deg, fov.min, fov.max);
  }

  /* -------------------------------------------------------------------------------------- view */

  function writePost() {
    const post = G.render && G.render.post;
    if (!post) return;
    post.damage = hurt;
    post.lowHealth = lowHealth;
  }

  /** Eye, aim vector and (while the player owns it) the camera, from the current pose and view layers. */
  function placeView() {
    const aimYaw = player.yaw + recoil.yaw;
    const aimPitch = clamp(player.pitch + recoil.pitch, -look.viewPitchLimit, look.viewPitchLimit);
    const cp = Math.cos(aimPitch);
    const sinYaw = Math.sin(aimYaw);
    const cosYaw = Math.cos(aimYaw);
    forward.set(-sinYaw * cp, Math.sin(aimPitch), -cosYaw * cp);

    // Bob and the landing spring may lift the eye only as far as the body has headroom for.
    const headroom = (player.crouching ? body.crouchHeight - body.crouchEye : body.height - body.eye) - body.headClearance;
    const lift = eyeHeight + Math.min(bobY + spring.offset, headroom) + stepLag.offset;
    eye.set(pos.x + cosYaw * bobX, pos.y + lift, pos.z - sinYaw * bobX);

    const camera = G.camera;
    if (!camera || !player.enabled) return;
    camera.position.copy(eye);
    camera.rotation.set(aimPitch + viewPitch + shake.pitch, aimYaw + shake.yaw, viewRoll + shake.roll, 'YXZ');
    if (!fixedFov) camera.fov = viewFov; // the renderer refreshes the projection every frame
  }

  /* ------------------------------------------------------------------------------------ update */

  function update(dt) {
    if (!(dt > 0)) return;
    hurt = Math.max(0, hurt - health.hurtPulse.decay * dt);
    if (blast > 0) {
      shake.atLeast(blast);
      blast = 0;
    }

    if (!player.enabled) {
      // The title fly-through and the debrief own the camera. Only the screen feedback keeps settling,
      // so a red flash never freezes on the picture.
      shake.update(dt);
      easeLowHealth(dt);
      writePost();
      return;
    }
    if (!player.alive) {
      updateDead(dt);
      return;
    }

    const input = G.input;
    let mx = input ? input.move.x : 0;
    let my = input ? input.move.y : 0;
    const push = mx * mx + my * my;
    if (!(push <= 1)) {
      // More than a full deflection (or not a number): never faster than the target speed.
      const k = push > 1 ? 1 / Math.sqrt(push) : 0;
      mx *= k;
      my *= k;
    }

    // Look. Aiming slows every device alike.
    if (!Number.isFinite(player.yaw)) player.yaw = 0;
    if (!Number.isFinite(player.pitch)) player.pitch = 0;
    if (input && Number.isFinite(input.look.dx) && Number.isFinite(input.look.dy)) {
      const k = lerp(1, look.adsScale, clamp01(player.ads));
      player.yaw = wrapAngle(player.yaw - input.look.dx * k);
      player.pitch = clamp(player.pitch - input.look.dy * k, -look.pitchLimit, look.pitchLimit);
    }

    // Without a weapon module nothing writes the aim amount: follow the aim input directly.
    if (!G.weapon || typeof G.weapon.update !== 'function') {
      player.ads = damp(player.ads, down('ads') ? 1 : 0, ADS_FALLBACK_RATE, dt);
    }

    // Crouch is a hold; standing back up waits for headroom.
    if (down('crouch')) player.crouching = true;
    else if (player.crouching && canStand()) player.crouching = false;

    // Jump: a press is remembered for a moment, and so is the ground after walking off a ledge.
    const wasGrounded = player.onGround;
    coyote = wasGrounded ? jump.coyote : coyote - dt;
    jumpBuffer = pressed('jump') ? jump.buffer : jumpBuffer - dt;
    let jumped = false;
    if (jumpBuffer > 0 && coyote > 0 && (!player.crouching || canStand())) {
      player.crouching = false; // a jump stands up first
      vel.y = takeOff;
      jumpBuffer = coyote = 0;
      jumped = true;
      emit('player:jump', {});
    }

    // Velocity moves straight toward the wish velocity at a constant rate.
    const wantSprint = sprintWanted(sprint, down('sprint'), my, mx, player.crouching, player.ads, down('fire'));
    const target = targetSpeed(speeds, player.crouching, wantSprint, player.ads, my);
    const sin = Math.sin(player.yaw);
    const cos = Math.cos(player.yaw);
    const hasInput = mx !== 0 || my !== 0;
    const wishX = hasInput ? (cos * mx - sin * my) * target : 0;
    const wishZ = hasInput ? (-sin * mx - cos * my) * target : 0;
    const rate = wasGrounded
      ? hasInput ? accel.ground : accel.groundStop
      : hasInput ? accel.air : accel.airStop;
    approachVelocity(vel, wishX, wishZ, rate, dt, wasGrounded || hasInput);

    // Gravity in two halves around the move; the second half is skipped on frames that end grounded.
    vel.y = Math.max(vel.y - jump.gravity * dt * 0.5, -jump.terminal);
    if (!wasGrounded) fallSpeed = Math.max(fallSpeed, -vel.y);
    const feetBefore = pos.y;
    const height = player.crouching ? body.crouchHeight : body.height;
    physics.moveCapsule(pos, vel, dt, body.radius, height, wasGrounded && !jumped, moved);
    if (!moved.onGround) vel.y = Math.max(vel.y - jump.gravity * dt * 0.5, -jump.terminal);
    keepInWorld();

    const surface = moved.surface || player.surface;
    player.onGround = moved.onGround;
    player.surface = surface;
    player.speed = Math.sqrt(vel.x * vel.x + vel.z * vel.z);
    player.sprinting = wantSprint && (moved.onGround ? player.speed > sprintSpeed : player.sprinting);

    if (moved.onGround) {
      if (!wasGrounded && airTime > fall.landMinAir) land(fallSpeed, surface);
      airTime = 0;
      fallSpeed = 0;
      lastSafe.copy(pos);
    } else {
      airTime += dt;
    }

    // Stairs and kerbs: the body pops by the step, the eye catches up.
    if (stepFrequency > 0) {
      const popped = pos.y - feetBefore;
      if (wasGrounded && moved.onGround && !jumped && popped !== 0) {
        stepLag.offset = clamp(stepLag.offset - popped, -bob.step.max, bob.step.max);
      }
      stepLag.update(dt);
    }

    if (player.alive) updateStride(dt, surface);
    updateHealth(dt);

    eyeHeight = damp(eyeHeight, player.crouching ? body.crouchEye : body.eye, body.eyeRate, dt);
    const ads = clamp01(player.ads);
    const fovTarget = lerp(baseFov + (player.sprinting ? fov.sprintAdd : 0), fov.ads, ads);
    const aiming = ads > fov.adsBand[0] && ads < fov.adsBand[1];
    viewFov = damp(viewFov, fovTarget, aiming ? fov.rateAds : fov.rate, dt);

    recoil.update(dt);
    shake.update(dt);
    spring.update(dt);

    // Lean into strafes; the sideways bob rolls the view a touch as well.
    const lateral = vel.x * cos - vel.z * sin;
    const lean = -(lateral / speeds.sprint) * bob.strafeRoll * lerp(1, bob.strafeRollAds, ads);
    strafeRoll = damp(strafeRoll, lean, bob.strafeRollRate, dt);
    viewPitch = spring.offset * bob.spring.pitch;
    viewRoll = strafeRoll + bobX * bob.rollFromLateral;

    if (player.alive) placeView();
    else updateDead(0); // the fall that killed: hand the camera to the death view on the same frame
  }

  /** The play bounds are walls already; this keeps the eye a little further inside, and catches the impossible. */
  function keepInWorld() {
    const b = physics.bounds;
    if (b) {
      const m = body.boundsMargin;
      if (b.maxX - b.minX > 2 * m) {
        if (pos.x < b.minX + m) {
          pos.x = b.minX + m;
          if (vel.x < 0) vel.x = 0;
        } else if (pos.x > b.maxX - m) {
          pos.x = b.maxX - m;
          if (vel.x > 0) vel.x = 0;
        }
      }
      if (b.maxZ - b.minZ > 2 * m) {
        if (pos.z < b.minZ + m) {
          pos.z = b.minZ + m;
          if (vel.z < 0) vel.z = 0;
        } else if (pos.z > b.maxZ - m) {
          pos.z = b.maxZ - m;
          if (vel.z > 0) vel.z = 0;
        }
      }
    }
    const sane = Number.isFinite(pos.x + pos.y + pos.z + vel.x + vel.y + vel.z);
    if (!sane || pos.y < FALL_LIMIT) {
      pos.copy(lastSafe);
      vel.set(0, 0, 0);
      moved.onGround = true;
    }
  }

  function land(speed, surface) {
    emit('player:land', { speed, surface });
    spring.kick(-Math.min(speed * fall.dipPerSpeed, fall.dipMax));
    if (speed > fall.shakeFrom) shake.add(Math.min(fall.shakeMax, (speed - fall.shakeFrom) * fall.shakePerSpeed));
    // A footstep follows the landing shortly.
    stridePhase = Math.floor(stridePhase) + stride.afterLanding;
    if (speed > fall.damageFrom) damage((speed - fall.damageFrom) * fall.damagePerSpeed, null, 'fall');
  }

  /** Stride phase, footsteps and the bob they drive. */
  function updateStride(dt, surface) {
    const walking = player.onGround && player.speed > speeds.moving;
    if (walking) {
      const length = player.crouching ? stride.crouch : player.sprinting ? stride.sprint : stride.walk;
      const before = Math.floor(stridePhase);
      stridePhase += (player.speed * dt) / length;
      if (Math.floor(stridePhase) > before) {
        emit('player:step', { pos: pos.clone(), surface, sprint: player.sprinting });
      }
    } else if (player.onGround) {
      // Standing still: both feet come to rest on a footfall.
      const rest = Math.round(stridePhase);
      stridePhase = Math.abs(rest - stridePhase) < 0.02 ? rest : damp(stridePhase, rest, stride.settleRate, dt);
    }
    if (stridePhase >= 2) stridePhase -= 2;

    const ads = clamp01(player.ads);
    const amp = player.onGround
      ? clamp01(player.speed / speeds.walk) *
        (player.sprinting ? bob.sprintScale : 1) *
        lerp(1, bob.adsScale, ads) *
        (player.crouching ? bob.crouchScale : 1)
      : 0;
    bobAmp = damp(bobAmp, amp, bob.rate, dt);
    bobY = -Math.cos(TAU * stridePhase) * bob.vertical * bobAmp;
    bobX = Math.sin(Math.PI * stridePhase) * bob.lateral * bobAmp;
  }

  function easeLowHealth(dt) {
    const low = health.lowHealth;
    const target = player.alive ? 1 - smoothstep(low.to, low.from, player.health / player.maxHealth) : 1;
    lowHealth = damp(lowHealth, target, low.rate, dt);
  }

  /** Health comes back after a quiet spell (delay and rate are written by the game per difficulty). */
  function updateHealth(dt) {
    sinceHit += dt;
    if (player.alive && player.health < player.maxHealth && sinceHit >= player.regen.delay) {
      player.health = Math.min(player.maxHealth, player.health + player.regen.rate * dt);
    }
    easeLowHealth(dt);
    writePost();
  }

  /** The body keeps falling and slides to rest while the camera drops to the floor and onto its side. */
  function updateDead(dt) {
    deadTime += dt;
    if (dt > 0) {
      vel.x = expDecay(vel.x, death.slide, dt);
      vel.z = expDecay(vel.z, death.slide, dt);
      vel.y = Math.max(vel.y - jump.gravity * dt, -jump.terminal);
      physics.moveCapsule(pos, vel, dt, body.radius, death.capsuleHeight, player.onGround, moved);
      keepInWorld();
      player.onGround = moved.onGround;
      player.speed = Math.sqrt(vel.x * vel.x + vel.z * vel.z);
      recoil.update(dt);
      shake.update(dt);
      spring.update(dt);
      stepLag.update(dt);
    }
    const s = smoothstep(0, death.collapse, deadTime);
    eyeHeight = damp(eyeHeight, lerp(eyeAtDeath, death.eye, s * s), death.eyeRate, dt);
    bobAmp = damp(bobAmp, 0, bob.rate, dt);
    bobY = -Math.cos(TAU * stridePhase) * bob.vertical * bobAmp;
    bobX = Math.sin(Math.PI * stridePhase) * bob.lateral * bobAmp;
    strafeRoll = damp(strafeRoll, 0, bob.strafeRollRate, dt);
    viewFov = damp(viewFov, baseFov, fov.rate, dt);
    viewPitch = death.pitch * s + death.pitchBounce * Math.sin(Math.PI * s) + spring.offset * bob.spring.pitch;
    viewRoll = deathSide * death.roll * s * s + strafeRoll;
    lowHealth = 1;
    writePost();
    placeView();
  }

  /* ------------------------------------------------------------------------------------ wiring */

  if (G.settings) setFov(G.settings.get('fov'));
  if (G.events) {
    G.events.on('settings:change', (e) => {
      if (e && e.key === 'fov') setFov(e.value);
    });
    // Blasts rock the camera by distance (the damage itself arrives through player.damage). The shake is
    // applied by the next update as "at least this much": the explosives module adds its own for a
    // tank or a rack, and the two must not stack.
    G.events.on('explosion', (e) => {
      if (!e || !e.pos) return;
      const B = shakeTune.onBlast;
      const near = 1 - eye.distanceTo(e.pos) / B.range;
      if (near > 0) blast = Math.max(blast, (B.base + B.scale * near * near) * (e.size === 'small' ? B.small : 1));
    });
  }
  reset((G.level && G.level.playerStart) || {});

  return player;
}
