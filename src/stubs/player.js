// Stub player (CONTRACT 6.4): a correct but plain first-person controller on physics.moveCapsule.
//
// It has the real movement rules (walk / sprint / crouch / jump / gravity, coyote time and jump buffer,
// fall damage), health with regeneration, death, footstep / jump / land / hit / dead events and the
// camera. It has no view bob, no landing spring, no screen shake, and only the permanent share of a
// recoil kick is applied. Numbers come from src/config/player.js when it is there.

import * as THREE from 'three';
import { clamp, damp, expDecay, lerp, smoothstep, wrapAngle } from '../core/util.js';

const DEFAULTS = {
  body: { radius: 0.32, height: 1.8, crouchHeight: 1.15, eye: 1.68, crouchEye: 1.05, eyeRate: 11 },
  speed: { walk: 3.8, sprint: 6.4, crouch: 1.9, ads: 2.4, backpedal: 0.82 },
  accel: { ground: 34, groundStop: 26, air: 9, airStop: 0.6 },
  jump: { gravity: 21, apex: 1.0, coyote: 0.12, buffer: 0.13, terminal: 40 },
  sprint: { minForward: 0.55, maxStrafe: 0.6, maxAds: 0.35, minSpeedFrac: 0.6 },
  stride: { walk: 1.55, sprint: 2.1, crouch: 1.05 },
  look: { pitchLimit: 1.5, adsScale: 0.6 },
  fov: { base: 74, min: 55, max: 100, sprintAdd: 6, ads: 52, rate: 7, rateAds: 30 },
  health: {
    max: 100,
    regenDelay: 5.5,
    regenRate: 16,
    hurtPulse: { base: 0.35, perDamage: 1 / 40, decay: 1.9 },
    lowHealth: { from: 0.55, to: 0.12, rate: 4 },
  },
  fall: { landMinAir: 0.12, damageFrom: 13, damagePerSpeed: 7 },
  recoil: { keep: 0.35 },
  death: { collapse: 0.85, eye: 0.22, roll: 1.15, capsuleHeight: 0.6 },
};

export function createPlayer(G) {
  const config = (G.config && G.config.player) || {};
  const tune = (name) => ({ ...DEFAULTS[name], ...config[name] });
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
  const recoil = tune('recoil');
  const death = tune('death');
  const jumpSpeed = Math.sqrt(2 * jump.gravity * jump.apex);
  const fixedFov = !!(G.params && G.params.fov); // a debug FOV override wins (main.js applies it)

  const pos = new THREE.Vector3();
  const vel = new THREE.Vector3();
  const eye = new THREE.Vector3();
  const forward = new THREE.Vector3(0, 0, -1);
  const moved = { onGround: true, hitWall: false, hitCeil: false, surface: 'asphalt' }; // reused moveCapsule result

  let eyeHeight = body.eye;
  let coyote = 0;
  let jumpBuffer = 0;
  let airTime = 0;
  let fallSpeed = 0; // fastest descent of the current fall
  let stepDistance = 0;
  let sinceHit = Infinity;
  let hurt = 0; // red flash, feeds render.post.damage
  let lowHealth = 0;
  let deadTime = 0;
  let baseFov = fov.base;
  let viewFov = fov.base;

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
    ads: 0, // written by the weapon
    enabled: true,
    invulnerable: false,
    regen: { delay: health.regenDelay, rate: health.regenRate },
    surface: 'asphalt',
    reset,
    damage,
    heal,
    addRecoil,
    addShake() {}, // no screen shake in the stub
    setFov,
    update,
  };

  const emit = (name, payload) => G.events && G.events.emit(name, payload);
  const down = (action) => !!G.input && G.input.down(action);

  /** Room to stand up from a crouch? */
  const canStand = () =>
    !G.physics.overlapsCylinder(pos.x, pos.z, body.radius * 0.9, pos.y + body.crouchHeight - 0.05, pos.y + body.height);

  function reset(spawn = {}) {
    if (spawn.pos) pos.copy(spawn.pos);
    vel.set(0, 0, 0);
    player.yaw = spawn.yaw || 0;
    player.pitch = 0;
    player.health = player.maxHealth;
    player.alive = true;
    player.onGround = true;
    player.sprinting = false;
    player.crouching = false;
    player.speed = 0;
    player.ads = 0;
    player.invulnerable = false;
    eyeHeight = body.eye;
    coyote = jumpBuffer = airTime = fallSpeed = stepDistance = 0;
    sinceHit = Infinity;
    hurt = lowHealth = deadTime = 0;
    viewFov = baseFov;
    writePost();
    placeView(0, 0);
  }

  function damage(amount, from = null, kind = 'bullet') {
    if (!player.alive || player.invulnerable || !(amount > 0)) return;
    player.health = Math.max(0, player.health - amount);
    sinceHit = 0;
    hurt = Math.min(1, hurt + health.hurtPulse.base + amount * health.hurtPulse.perDamage);
    emit('player:hit', { amount, from, health: player.health, kind });
    if (player.health <= 0) {
      player.alive = false;
      player.sprinting = false;
      deadTime = 0;
      emit('player:dead', { from });
    }
  }

  function heal(n) {
    if (player.alive && n > 0) player.health = Math.min(player.maxHealth, player.health + n);
  }

  /** Stub: only the permanent share of the kick moves the aim; nothing springs back. */
  function addRecoil(pitch, yaw) {
    player.pitch = clamp(player.pitch + pitch * recoil.keep, -look.pitchLimit, look.pitchLimit);
    player.yaw = wrapAngle(player.yaw + yaw * recoil.keep);
  }

  function setFov(deg) {
    if (Number.isFinite(deg)) baseFov = clamp(deg, fov.min, fov.max);
  }

  function writePost() {
    const post = G.render && G.render.post;
    if (!post) return;
    post.damage = hurt;
    post.lowHealth = lowHealth;
  }

  /** Eye, aim vector and camera from the current pose. */
  function placeView(pitchOffset, roll) {
    const pitch = player.pitch + pitchOffset;
    const cp = Math.cos(pitch);
    eye.set(pos.x, pos.y + eyeHeight, pos.z);
    forward.set(-Math.sin(player.yaw) * cp, Math.sin(pitch), -Math.cos(player.yaw) * cp);
    const camera = G.camera;
    if (!camera || !player.enabled) return;
    camera.position.copy(eye);
    camera.rotation.set(pitch, player.yaw, roll, 'YXZ');
    if (!fixedFov) camera.fov = viewFov; // the renderer refreshes the projection every frame
  }

  function update(dt) {
    if (!player.enabled) return;
    hurt = Math.max(0, hurt - health.hurtPulse.decay * dt);
    if (!player.alive) {
      updateDead(dt);
      return;
    }
    const input = G.input;
    const mx = input ? input.move.x : 0;
    const my = input ? input.move.y : 0;

    if (input) {
      const scale = lerp(1, look.adsScale, player.ads);
      player.yaw = wrapAngle(player.yaw - input.look.dx * scale);
      player.pitch = clamp(player.pitch - input.look.dy * scale, -look.pitchLimit, look.pitchLimit);
    }

    // Crouch is a hold; standing back up waits for headroom.
    if (down('crouch')) player.crouching = true;
    else if (player.crouching && canStand()) player.crouching = false;

    // Jump: a press is remembered briefly, and leaving a ledge still counts as grounded for a moment.
    const wasGrounded = player.onGround;
    coyote = wasGrounded ? jump.coyote : coyote - dt;
    jumpBuffer = input && input.pressed('jump') ? jump.buffer : jumpBuffer - dt;
    let jumped = false;
    if (jumpBuffer > 0 && coyote > 0 && (!player.crouching || canStand())) {
      player.crouching = false;
      vel.y = jumpSpeed;
      jumpBuffer = coyote = 0;
      jumped = true;
      emit('player:jump', {});
    }

    // Target speed.
    const wantSprint =
      down('sprint') &&
      my > sprint.minForward &&
      Math.abs(mx) < sprint.maxStrafe &&
      !player.crouching &&
      player.ads < sprint.maxAds &&
      !down('fire');
    let target = player.crouching ? speeds.crouch : wantSprint ? speeds.sprint : speeds.walk;
    target = lerp(target, Math.min(target, speeds.ads), player.ads);
    if (my < 0) target *= lerp(1, speeds.backpedal, -my);
    player.sprinting =
      wantSprint && (wasGrounded ? player.speed > speeds.walk * sprint.minSpeedFrac : player.sprinting);

    // Velocity moves straight toward the wish velocity at a constant rate (no friction model).
    const sin = Math.sin(player.yaw);
    const cos = Math.cos(player.yaw);
    const hasInput = mx !== 0 || my !== 0;
    const wishX = hasInput ? (cos * mx - sin * my) * target : 0;
    const wishZ = hasInput ? (-sin * mx - cos * my) * target : 0;
    const rate = wasGrounded
      ? hasInput ? accel.ground : accel.groundStop
      : hasInput ? accel.air : accel.airStop;
    const ex = wishX - vel.x;
    const ez = wishZ - vel.z;
    const error = Math.hypot(ex, ez);
    if (error <= rate * dt) {
      if (wasGrounded || hasInput) {
        vel.x = wishX;
        vel.z = wishZ;
      }
    } else {
      vel.x += (ex / error) * rate * dt;
      vel.z += (ez / error) * rate * dt;
    }

    // Gravity in two halves around the move; the second half is skipped on the ground.
    vel.y = Math.max(vel.y - jump.gravity * dt * 0.5, -jump.terminal);
    if (!wasGrounded) fallSpeed = Math.max(fallSpeed, -vel.y);
    const height = player.crouching ? body.crouchHeight : body.height;
    G.physics.moveCapsule(pos, vel, dt, body.radius, height, wasGrounded && !jumped, moved);
    if (!moved.onGround) vel.y = Math.max(vel.y - jump.gravity * dt * 0.5, -jump.terminal);

    player.onGround = moved.onGround;
    player.surface = moved.surface;
    player.speed = Math.hypot(vel.x, vel.z);
    if (moved.onGround) {
      if (!wasGrounded && airTime > fall.landMinAir) {
        emit('player:land', { speed: fallSpeed, surface: moved.surface });
        if (fallSpeed > fall.damageFrom) damage((fallSpeed - fall.damageFrom) * fall.damagePerSpeed, null, 'fall');
        stepDistance = 0;
      }
      airTime = 0;
      fallSpeed = 0;
    } else {
      airTime += dt;
    }

    // One footstep per stride travelled on the ground.
    if (moved.onGround && player.speed > 0.3) {
      stepDistance += player.speed * dt;
      const length = player.crouching ? stride.crouch : player.sprinting ? stride.sprint : stride.walk;
      if (stepDistance >= length) {
        stepDistance -= length;
        emit('player:step', { pos: pos.clone(), surface: moved.surface, sprint: player.sprinting });
      }
    }

    // Health comes back after a quiet spell (delay and rate are set per difficulty by the game).
    sinceHit += dt;
    if (player.alive && player.health < player.maxHealth && sinceHit >= player.regen.delay) {
      player.health = Math.min(player.maxHealth, player.health + player.regen.rate * dt);
    }
    const low = health.lowHealth;
    lowHealth = damp(lowHealth, 1 - smoothstep(low.to, low.from, player.health / player.maxHealth), low.rate, dt);
    writePost();

    eyeHeight = damp(eyeHeight, player.crouching ? body.crouchEye : body.eye, body.eyeRate, dt);
    const fovTarget = lerp(baseFov + (player.sprinting ? fov.sprintAdd : 0), fov.ads, player.ads);
    viewFov = damp(viewFov, fovTarget, player.ads > 0.02 && player.ads < 0.98 ? fov.rateAds : fov.rate, dt);
    placeView(0, 0);
  }

  /** The body keeps falling and sliding to rest while the camera drops onto its side. */
  function updateDead(dt) {
    deadTime += dt;
    vel.x = expDecay(vel.x, 5, dt);
    vel.z = expDecay(vel.z, 5, dt);
    vel.y = Math.max(vel.y - jump.gravity * dt, -jump.terminal);
    G.physics.moveCapsule(pos, vel, dt, body.radius, death.capsuleHeight, player.onGround, moved);
    player.onGround = moved.onGround;
    player.speed = Math.hypot(vel.x, vel.z);
    const s = smoothstep(0, death.collapse, deadTime);
    eyeHeight = damp(eyeHeight, lerp(body.eye, death.eye, s * s), 18, dt);
    lowHealth = 1;
    writePost();
    placeView(-0.25 * s + 0.12 * Math.sin(Math.PI * s), death.roll * s * s);
  }

  if (G.settings) setFov(G.settings.get('fov'));
  if (G.events) {
    G.events.on('settings:change', (e) => {
      if (e.key === 'fov') setFov(e.value);
    });
  }
  reset((G.level && G.level.playerStart) || {});

  return player;
}
