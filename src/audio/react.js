// Game events (CONTRACT 4.2) → sounds. Everything the audio module hears on its own: the guns, the feet,
// rounds landing, enemies, objectives, the train, the interface. Also the per-frame trackers: Buzzard rotor
// loops, the low-health heartbeat, the reel-grab loop.

const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);

const STEP_SURFACE = { asphalt: 'asphalt', concrete: 'concrete', metal: 'metal', wood: 'wood', dirt: 'dirt', brick: 'concrete', glass: 'concrete', rubber: 'dirt', cloth: 'dirt', car: 'metal', drone: 'metal', flesh: 'dirt' };
// Impact sound and pitch per surface.
const IMPACT = {
  asphalt: ['imp_concrete', 0.82], concrete: ['imp_concrete', 1], brick: ['imp_brick', 1], metal: ['imp_metal', 1],
  car: ['imp_car', 1], glass: ['imp_glass', 1], wood: ['imp_wood', 1], dirt: ['imp_dirt', 1], rubber: ['imp_wood', 0.7],
  cloth: ['imp_dirt', 1.25], flesh: ['imp_flesh', 1], drone: ['imp_drone', 1],
};
const RICOCHET = { metal: 0.24, car: 0.12, concrete: 0.07, brick: 0.05, asphalt: 0.05 };

export function wireEvents(A) {
  const { G } = A;
  const THREE = G.THREE;
  const on = (name, fn) => G.events && G.events.on(name, fn);
  const tmp = new THREE.Vector3();
  const tmp2 = new THREE.Vector3();

  const weaponOf = (w) => (w === 'nine' || w === 'pistol' ? 'nine' : 'chopper');
  let lastShot = -1e9;
  let lastTail = null;
  let grab = null;
  let grabSeen = 0;
  let heart = null;
  let earLast = -1e9;
  const rotors = new Map(); // enemy → {h, tune}
  let rotorTimer = 0;

  // ---- the player's guns ---------------------------------------------------------------------------

  on('weapon:fire', (p) => {
    if (!A.unlocked) return;
    const w = weaponOf(p && p.weapon);
    const now = A.now();
    A.play(`${w}_shot`, { volume: w === 'nine' ? 0.95 : 1 });
    // Tails: street and shop split by the interior factor (equal power). In a burst each new tail starts
    // low and only the last one is let up to full, so the burst ends on one clean slap off the block.
    const since = now - lastShot;
    lastShot = now;
    const i = A.interior;
    const k = since < 0.45 ? 0.4 + 0.6 * (since / 0.45) : 1;
    if (lastTail) for (const h of lastTail) if (h) h.setVolume(0.25 * k);
    const out = Math.cos((i * Math.PI) / 2);
    const inn = Math.sin((i * Math.PI) / 2);
    lastTail = [
      out > 0.05 ? A.play(`${w}_tail_out`, { volume: out * k }) : null,
      inn > 0.05 ? A.play(`${w}_tail_in`, { volume: inn * k }) : null,
    ];
    if (k < 1) {
      const mine = lastTail;
      setTimeout(() => {
        if (lastTail === mine) mine.forEach((h, j) => h && h.setVolume(j ? inn : out));
      }, 105);
    }
    A.duck(w === 'nine' ? 0.55 : 0.45, 0.085, 0.1);
    A.meter(0, 0.012);
  });

  on('weapon:dry', (p) => A.play('dry_fire', { pitch: weaponOf(p && p.weapon) === 'nine' ? 1.2 : 1 }));

  on('weapon:reload', (p) => {
    if (!p) return;
    const pistol = weaponOf(p.weapon) === 'nine';
    const pre = pistol ? 'pistol' : 'rifle';
    switch (p.phase) {
      case 'start':
        A.play('cloth', { volume: 0.9, pitch: pistol ? 1.12 : 1 });
        break;
      case 'magout':
        A.play(`${pre}_magout`);
        break;
      case 'magin':
        A.play(`${pre}_magin`);
        break;
      case 'bolt':
        A.play(pistol ? 'pistol_slide' : 'rifle_bolt');
        break;
      case 'done':
        A.play('cloth', { volume: 0.5, pitch: pistol ? 1.2 : 1.08 });
        break;
      default:
    }
  });

  on('weapon:switch', (p) => {
    if (!p) return;
    if (p.phase === 'holster') A.play('holster', { volume: weaponOf(p.from) === 'nine' ? 0.75 : 1, pitch: weaponOf(p.from) === 'nine' ? 1.18 : 1 });
    else A.play('draw', { volume: weaponOf(p.to) === 'nine' ? 0.8 : 1, pitch: weaponOf(p.to) === 'nine' ? 1.15 : 1 });
  });

  on('weapon:swing', () => A.play('whoosh', { volume: 0.9, pitch: 1.1 }));
  on('weapon:melee', (p) => {
    if (p && p.hit) A.play('melee_thud');
  });

  on('shell:bounce', (p) => {
    if (!p || !p.pos) return;
    const s = p.surface;
    const metal = s === 'metal' || s === 'car';
    const soft = s === 'dirt' || s === 'wood' || s === 'rubber' || s === 'cloth';
    const nine = G.weapon && G.weapon.current === 'nine';
    A.play(metal ? 'brass_metal' : 'brass_asphalt', { pos: p.pos, volume: soft ? 0.5 : 0.9, pitch: (nine ? 1.22 : 1) * (s === 'wood' ? 0.9 : 1) });
  });

  // ---- the player ----------------------------------------------------------------------------------

  const stepName = (surface, run) => `step_${STEP_SURFACE[surface] || 'concrete'}${run ? '_run' : ''}`;

  on('player:step', (p) => {
    if (!p) return;
    A.play(stepName(p.surface, p.sprint), { volume: p.sprint ? 0.8 : 0.55, pitch: p.sprint ? 1.04 : 1 });
  });
  on('player:jump', () => A.play('jump', { volume: 0.8 }));
  on('player:land', (p) => {
    const v = clamp(0.35 + Math.abs((p && p.speed) || 0) / 10, 0.35, 1);
    A.play('land', { volume: v });
    A.play(stepName(p && p.surface, true), { volume: v * 0.6, pitch: 0.92 });
  });

  on('player:hit', (p) => {
    if (!A.unlocked || !p) return;
    const dmg = Math.max(0, +p.amount || 0);
    A.play('hurt', { volume: clamp(0.5 + dmg / 40, 0.5, 1), pitch: p.kind === 'blast' ? 0.85 : 1 });
    const now = A.now();
    if (dmg >= 8 && now - earLast > 1.8) {
      earLast = now;
      A.play('ear_ring', { volume: clamp(dmg / 28, 0.3, 1) });
    }
    A.muffleTo(clamp(dmg / 40, 0.2, 0.7), 0);
    A.meter(0, 0.15);
  });

  on('player:dead', () => A.muffleTo(1, 0.85));

  on('player:hitEnemy', (p) => {
    if (!p) return;
    if (p.killed) A.play('kill_confirm');
    else A.play(p.part === 'head' ? 'hit_head' : 'hit_confirm');
  });

  // ---- rounds in the world -------------------------------------------------------------------------

  on('impact', (p) => {
    if (!p || !p.point) return;
    const [name, pitch] = IMPACT[p.surface] || IMPACT.concrete;
    const enemyShot = p.from && p.from !== 'player';
    if (p.enemy && p.from === 'player') {
      // The body hit is the confirmation: weak points brighter.
      A.play(name, { pos: p.point, volume: 1, pitch: pitch * (p.part === 'head' ? 1.25 : 1) });
      return;
    }
    A.play(name, { pos: p.point, volume: enemyShot ? 0.8 : 0.9, pitch });
    const chance = RICOCHET[p.surface] || 0;
    if (chance && A.rnd() < chance) A.play('ricochet', { pos: p.point, delay: 0.012, volume: 0.8 });
  });

  /** An enemy round whose line passes within 3.2 m of the listener: a whizz at the closest point. */
  function nearMiss(pos, dir, speed) {
    if (!pos || !dir) return;
    tmp.copy(A.listener).sub(pos);
    const along = tmp.dot(dir);
    if (along < 2) return;
    tmp2.copy(pos).addScaledVector(dir, along);
    const d = tmp2.distanceTo(A.listener);
    if (d > 3.2 || d < 0.25) return; // a round that close hit the player (player:hit is the cue)
    if (G.physics && typeof G.physics.lineOfSight === 'function' && !G.physics.lineOfSight(pos, tmp2)) return;
    A.play('whizz', { pos: tmp2, volume: clamp(1.15 - d / 3.5, 0.3, 1), delay: speed ? Math.min(1.5, along / speed) : 0 });
  }

  const boltSpeed = () => (G.config && G.config.enemies && G.config.enemies.buzzard && G.config.enemies.buzzard.boltSpeed) || 70;

  on('enemy:fire', (p) => {
    if (!p || !p.pos) return;
    if (p.type === 'buzzard') {
      A.play('bolt_shot', { pos: p.pos });
      nearMiss(p.pos, p.dir, boltSpeed());
    } else {
      A.play('smg_shot', { pos: p.pos });
      nearMiss(p.pos, p.dir, 0);
    }
    A.duck(0.85, 0.06, 0.12, false);
    A.meter(0, 0.04);
  });

  on('enemy:telegraph', (p) => {
    if (!p || !p.pos) return;
    const pitch = clamp(0.5 / Math.max(0.15, +p.duration || 0.5), 0.6, 2);
    A.play(p.type === 'buzzard' ? 'buzzard_charge' : 'goon_ready', { pos: p.pos, pitch });
    A.meter(0.6);
  });

  on('enemy:melee', (p) => {
    if (!p || !p.pos) return;
    if (p.phase === 'windup') A.play('goon_rush', { pos: p.pos, pitch: 1, volume: 0.9 });
    else A.play('pipe_swing', { pos: p.pos });
  });

  on('enemy:alert', (p) => {
    if (!p) return;
    const e = p.enemy;
    const pos = p.pos || (e && e.pos);
    if (!pos) return;
    A.play(e && e.type === 'buzzard' ? 'alert_buzzard' : 'alert_goon', { pos });
    A.meter(0.6);
  });

  on('enemy:hit', (p) => {
    const e = p && p.enemy;
    if (!e || e.type === 'buzzard' || e.alive === false) return;
    A.play('grunt_hit', { pos: e.pos, pitch: e.voice || 1 });
  });

  on('enemy:killed', (p) => {
    if (!p || !p.pos) return;
    if (p.type === 'buzzard') {
      A.play('buzzard_death', { pos: p.pos });
      dropRotor(p.enemy);
    } else {
      A.play('grunt_death', { pos: p.pos, pitch: (p.enemy && p.enemy.voice) || 1 });
      A.play('body_fall', { pos: p.pos, delay: 0.42 });
    }
  });

  on('enemy:step', (p) => {
    if (!p || !p.pos) return;
    A.play(stepName(p.surface, true), { pos: p.pos, bus: 'world', volume: 0.75, pitch: 0.88, ref: 3, roll: 1.2, prio: 2 });
  });

  on('enemy:spawn', (p) => {
    const e = p && p.enemy;
    if (e && e.type === 'buzzard') addRotor(e);
  });

  on('explosion', (p) => {
    if (!A.unlocked || !p || !p.pos) return;
    const big = typeof p.size === 'string' ? p.size === 'big' : (+p.radius || 0) >= 6;
    A.play(big ? 'explosion_big' : 'explosion_small', { pos: p.pos, volume: 1, ref: big ? 18 : 12 });
    const d = A.listener.distanceTo(p.pos);
    const near = clamp(1 - (d - 5) / 15, 0, 1);
    if (near > 0) A.muffleTo((big ? 0.8 : 0.56) * near, 0);
    A.duck(big ? 0.4 : 0.6, big ? 0.4 : 0.15, big ? 0.45 : 0.2);
    A.dipMusic(big ? 0.3 : 0.45);
    A.meter(0.6);
  });

  // ---- objectives, flow, radio, the interface ------------------------------------------------------

  on('objective:progress', (p) => {
    if (!A.unlocked || !p) return;
    if (!grab) grab = A.loop('reel_grab', { volume: 0.8 });
    grab.setPitch(0.85 + 0.4 * clamp(+p.t || 0, 0, 1));
    grabSeen = 0;
  });

  on('objective:done', (p) => {
    stopGrab();
    if (!p) return;
    if (p.id !== 'wave') {
      A.play('reel_secure');
      A.ambience.reelTaken(p.id);
    }
  });

  on('radio:line', (p) => {
    A.play('radio_in');
    const secs = clamp(+(p && p.secs) || 2.5, 0.6, 12);
    setTimeout(() => A.play('radio_out'), secs * 1000);
  });

  on('ui:click', () => A.play('ui_click'));
  on('ui:hover', () => A.play('ui_hover'));
  on('train:pass', (p) => A.ambience.onTrain(p));

  on('game:state', (p) => {
    const s = p && p.state;
    if (s === 'title') {
      A.muffleTo(0, 0); // back from the death card: the title music is not heard through the death low-pass
      A.music('title');
      A.setAmbState(0.6);
    } else if (s === 'intro' || s === 'playing') {
      if (!(p.prev === 'paused')) A.muffleTo(0, 0);
      A.music('play');
      A.setAmbState(1);
    } else if (s === 'dead') {
      A.setAmbState(0.7);
    } else if (s === 'complete') {
      A.setAmbState(0.8);
    }
    if (s !== 'playing') stopGrab();
  });

  on('game:reset', () => {
    stopGrab();
    A.muffleTo(0, 0);
    for (const e of [...rotors.keys()]) dropRotor(e);
    A.ambience.startReels();
  });

  function stopGrab() {
    if (grab) grab.stop(0.08);
    grab = null;
  }

  // ---- per-frame trackers --------------------------------------------------------------------------

  function addRotor(e) {
    if (rotors.has(e)) return;
    rotors.set(e, { h: A.loop('rotor', { pos: e.pos, volume: 0 }), tune: 0.96 + A.rnd() * 0.1, on: false });
  }

  function dropRotor(e) {
    const r = rotors.get(e);
    if (!r) return;
    r.h.stop(0.12);
    rotors.delete(e);
  }

  function updateRotors(dt) {
    const list = G.enemies && G.enemies.list;
    if (!Array.isArray(list)) return;
    // Enemies that came without a spawn event (a pool reused, a module that announces nothing).
    for (const e of list) if (e && e.type === 'buzzard' && e.alive && !rotors.has(e)) addRotor(e);
    rotorTimer -= dt;
    const pick = rotorTimer <= 0;
    if (pick) rotorTimer = 0.25;
    // The six nearest within 90 m are heard; the rest are silent.
    let ranked = null;
    if (pick) {
      ranked = [];
      for (const [e] of rotors) ranked.push([e.pos ? e.pos.distanceTo(A.listener) : 1e9, e]);
      ranked.sort((a, b) => a[0] - b[0]);
      ranked.forEach(([d, e], i) => (rotors.get(e).on = i < 6 && d < 90));
    }
    for (const [e, r] of rotors) {
      if (!e.alive || !list.includes(e)) {
        dropRotor(e);
        continue;
      }
      r.h.setPos(e.pos);
      const v = e.vel ? Math.hypot(e.vel.x, e.vel.y, e.vel.z) : 0;
      r.h.setPitch(r.tune * (0.94 + 0.3 * clamp(v / 10, 0, 1)));
      r.h.setVolume(r.on ? 1 : 0);
    }
  }

  function updateHeart() {
    const P = G.player;
    const playing = G.game && G.game.state === 'playing';
    const h = P && P.maxHealth ? P.health / P.maxHealth : 1;
    const want = playing && P.alive && h < 0.35;
    if (want && !heart) heart = A.loop('heartbeat', { volume: 0 });
    if (!heart) return;
    if (!want) {
      heart.stop(0.4);
      heart = null;
      return;
    }
    const k = clamp((0.35 - h) / 0.25, 0, 1);
    heart.setVolume(0.25 + 0.4 * k);
    heart.setPitch(1 + 0.35 * k);
  }

  return {
    update(dt) {
      updateRotors(dt);
      updateHeart();
      if (grab && (grabSeen += dt) > 0.3) stopGrab(); // the player let go
    },
    pause() {
      stopGrab();
    },
  };
}
