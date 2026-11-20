// Hitscan, melee and explosion resolution plus the run's combat stats (`G.combat`), CONTRACT 5.2.
//
// Combat owns no objects. It asks the world (physics), the enemies, the explosives and the player who
// is in the way, applies the damage through their public methods and announces the result:
//   impact            every shot or strike that lands on the world, an enemy or an explosive
//   player:hitEnemy   player shots and melee strikes that land on an enemy
//   explosion         every blast
// Any of G.enemies / G.explosives / G.player may be missing or a stub; missing methods are skipped.
//
// Conventions other modules can rely on:
//   - enemies.damage(enemy, amount, {point, dir, part, from, weapon}): `from` is 'player', the shooting
//     enemy object, or 'blast' (then `weapon` is 'blast' too, or whatever the blast was credited to:
//     explode({weapon: 'rocket'})); `weapon` is 'melee' for a strike.
//   - explosives.damage(item, amount, from): `from` is 'player', the shooting enemy object, or 'blast'.
//     An enemy round always does the same small fixed damage to an explosive.
//   - player.damage(amount, from, kind): `from` is a fresh Vector3 (the muzzle or the blast centre).
//   - Results and event payloads are fresh objects: safe to keep.

import * as THREE from 'three';

// Shots treat the player as an upright cylinder a little fatter than the collision body.
const PLAYER_RADIUS = 0.38;
const PLAYER_STAND = 1.8;
const PLAYER_CROUCH = 1.15;
// A live explosive is also a collider in the world list, so the world ray stops on the same surface
// the explosives module reports. Within this distance the explosive wins the tie. When the module tests
// a tighter shape than its collider (or nothing at all), the collider decides: see explosiveBehind().
const TIE = 0.03;
const BIG_BLAST_RADIUS = 5; // explosions at least this wide are announced as 'big'
// What a stray enemy round does to a propane tank or welding rack, whatever the round's own damage
// (config/weapons.js `common.explosiveHitFromEnemy` when present).
const ENEMY_ROUND_VS_EXPLOSIVE = 9;

export function createCombat(G) {
  const stats = { shots: 0, hits: 0, kills: 0, headshots: 0, damageTaken: 0 };

  const worldHit = { dist: 0, point: new THREE.Vector3(), normal: new THREE.Vector3(), surface: null, box: null };
  const bodyNormal = new THREE.Vector3(); // written by rayPlayer
  const target = new THREE.Vector3();
  const toTarget = new THREE.Vector3();

  const emit = (name, payload) => {
    if (G.events) G.events.emit(name, payload);
  };
  const has = (obj, method) => !!obj && typeof obj[method] === 'function';

  // Every source of player damage ends in player:hit (enemy bolts and falls never pass through here).
  if (G.events) {
    G.events.on('player:hit', (e) => {
      if (e && e.amount > 0) stats.damageTaken += e.amount;
    });
  }

  function reset() {
    stats.shots = stats.hits = stats.kills = stats.headshots = stats.damageTaken = 0;
  }

  const blankResult = () => ({
    type: 'none',
    point: new THREE.Vector3(),
    normal: new THREE.Vector3(),
    dist: 0,
    surface: null,
    enemy: null,
    part: null,
    killed: false,
    box: null,
    item: null, // the explosive that was hit (type 'explosive')
  });

  const surfaceOf = (enemy) => (enemy.type === 'buzzard' ? 'drone' : 'flesh');

  function enemyRoundDamage() {
    const common = G.config && G.config.weapons && G.config.weapons.common;
    return common && common.explosiveHitFromEnemy > 0 ? common.explosiveHitFromEnemy : ENEMY_ROUND_VS_EXPLOSIVE;
  }

  /**
   * The live explosive a world collider belongs to (`item.box === box`, or `box.owner === item`), or null.
   * A ray that stops on such a collider has hit the explosive, whatever explosives.raycast made of it.
   */
  function explosiveBehind(box) {
    const items = G.explosives && G.explosives.items;
    if (!box || !items) return null;
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item && item.state !== 'gone' && (item.box === box || box.owner === item)) return item;
    }
    return null;
  }

  /** Counts a kill; a kill whose final blow landed on the head is also a headshot. */
  function countKill(part) {
    stats.kills++;
    if (part === 'head') stats.headshots++;
  }

  /**
   * Distance along a unit ray to the player's body cylinder, or Infinity. Writes bodyNormal.
   * A ray that starts inside the cylinder hits at distance 0 (a muzzle pressed against the player).
   */
  function rayPlayer(origin, d, maxDist) {
    const p = G.player;
    if (!p || !p.pos || p.alive === false) return Infinity;
    const height = p.crouching ? PLAYER_CROUCH : PLAYER_STAND;
    const ox = origin.x - p.pos.x;
    const oz = origin.z - p.pos.z;
    const oy = origin.y - p.pos.y;
    const r2 = PLAYER_RADIUS * PLAYER_RADIUS;
    if (ox * ox + oz * oz <= r2 && oy >= 0 && oy <= height) {
      bodyNormal.copy(d).negate();
      return 0;
    }
    let tIn = 0;
    let tOut = maxDist;
    let cap = 0; // 0: entered through the side, ±1: through the bottom / top cap
    const a = d.x * d.x + d.z * d.z;
    if (a > 1e-12) {
      const b = ox * d.x + oz * d.z;
      const disc = b * b - a * (ox * ox + oz * oz - r2);
      if (disc < 0) return Infinity;
      const root = Math.sqrt(disc);
      tIn = Math.max(tIn, (-b - root) / a);
      tOut = Math.min(tOut, (-b + root) / a);
    } else if (ox * ox + oz * oz > r2) {
      return Infinity;
    }
    if (Math.abs(d.y) > 1e-12) {
      const t0 = -oy / d.y;
      const t1 = (height - oy) / d.y;
      const near = Math.min(t0, t1);
      if (near > tIn) {
        tIn = near;
        cap = d.y > 0 ? -1 : 1;
      }
      tOut = Math.min(tOut, Math.max(t0, t1));
    } else if (oy < 0 || oy > height) {
      return Infinity;
    }
    if (tIn > tOut) return Infinity;
    if (cap) bodyNormal.set(0, cap, 0);
    else bodyNormal.set(ox + d.x * tIn, 0, oz + d.z * tIn).normalize();
    return tIn;
  }

  /**
   * One instant shot. `from` is 'player' or the shooting enemy object.
   * Player shots can hit the world, enemies and explosives; enemy shots the world, explosives and the
   * player. The nearest wins, the damage is applied and the hit announced.
   */
  function hitscan({ origin, dir, range = 300, damage = 0, from = 'player', weapon = null, headMult = 1 }) {
    const byPlayer = from === 'player';
    const d = new THREE.Vector3().copy(dir).normalize();
    const res = blankResult();

    const world = G.physics.raycast(origin, d, range, worldHit);
    const limit = world ? world.dist : range;

    // Bodies only count in front of the world hit, so nothing is shot through cover.
    let enemyHit = byPlayer && has(G.enemies, 'raycast') ? G.enemies.raycast(origin, d, limit) : null;
    if (enemyHit && !(enemyHit.dist <= limit)) enemyHit = null;
    let itemHit = has(G.explosives, 'raycast') ? G.explosives.raycast(origin, d, limit + TIE) : null;
    if (itemHit && !(itemHit.dist <= limit + TIE)) itemHit = null;
    const playerDist = byPlayer ? Infinity : rayPlayer(origin, d, limit);

    let dist = limit;
    let item = null;
    if (world) res.type = 'world';
    if (itemHit) {
      res.type = 'explosive';
      item = itemHit.item;
      dist = Math.min(itemHit.dist, limit);
    } else if (world) {
      item = explosiveBehind(world.box);
      if (item) res.type = 'explosive';
    }
    if (enemyHit && enemyHit.dist <= dist) {
      res.type = 'enemy';
      dist = enemyHit.dist;
    }
    if (playerDist <= dist) {
      res.type = 'player';
      dist = playerDist;
    }
    res.dist = dist;
    res.point.copy(origin).addScaledVector(d, dist);
    res.normal.copy(d).negate();

    const side = byPlayer ? 'player' : 'enemy';
    if (res.type === 'enemy') {
      const enemy = enemyHit.enemy;
      const part = enemyHit.part || 'body';
      const dealt = damage * (part === 'head' ? headMult : 1);
      if (enemyHit.point) res.point.copy(enemyHit.point);
      if (enemyHit.normal) res.normal.copy(enemyHit.normal);
      res.enemy = enemy;
      res.part = part;
      res.surface = surfaceOf(enemy);
      const out = has(G.enemies, 'damage')
        ? G.enemies.damage(enemy, dealt, { point: res.point, dir: d, part, from, weapon })
        : null;
      res.killed = !!(out && out.killed);
      stats.hits++;
      if (res.killed) countKill(part);
      emit('impact', { point: res.point, normal: res.normal, surface: res.surface, dir: d, from: side, enemy });
      emit('player:hitEnemy', { enemy, part, killed: res.killed, damage: dealt, weapon });
    } else if (res.type === 'explosive') {
      if (itemHit) {
        if (itemHit.point) res.point.copy(itemHit.point);
        if (itemHit.normal) res.normal.copy(itemHit.normal);
      } else {
        res.normal.copy(world.normal);
      }
      res.item = item;
      res.box = item.box || (world && world.box) || null;
      res.surface = (res.box && res.box.surface) || 'metal';
      if (has(G.explosives, 'damage')) G.explosives.damage(item, byPlayer ? damage : enemyRoundDamage(), from);
      emit('impact', { point: res.point, normal: res.normal, surface: res.surface, dir: d, from: side, enemy: null });
    } else if (res.type === 'player') {
      res.normal.copy(bodyNormal);
      res.surface = 'flesh';
      // No `impact` here: the player's own hit feedback hangs off player:hit.
      if (has(G.player, 'damage')) G.player.damage(damage, origin.clone(), 'bullet');
    } else if (res.type === 'world') {
      res.normal.copy(world.normal);
      res.surface = world.surface;
      res.box = world.box;
      emit('impact', { point: res.point, normal: res.normal, surface: res.surface, dir: d, from: side, enemy: null });
    }
    return res;
  }

  /** Point on an enemy's body nearest to the height of `y` (goons stand on pos, buzzards hover at it). */
  function bodyPoint(enemy, y, out) {
    const p = enemy.pos;
    if (enemy.type === 'buzzard') return out.copy(p);
    const height = enemy.height || PLAYER_STAND;
    return out.set(p.x, THREE.MathUtils.clamp(y, p.y + 0.2, p.y + height - 0.15), p.z);
  }

  /**
   * A strike by the player: the nearest living enemy within `reach` whose body lies inside the cone
   * and in line of sight takes the damage. `cone` is the full apex angle in radians.
   * Melee kills count as kills, but a strike is neither a shot nor a hit for accuracy.
   * With no enemy in the way the result reports the wall within reach, if any (no `impact` event).
   */
  function melee({ origin, dir, reach = 2.3, cone = (50 * Math.PI) / 180, damage = 60 }) {
    const d = new THREE.Vector3().copy(dir).normalize();
    const res = blankResult();
    const list = (G.enemies && G.enemies.list) || [];
    let best = null;
    let bestDist = Infinity;
    for (let i = list.length - 1; i >= 0; i--) {
      const enemy = list[i];
      if (!enemy || !enemy.alive || !enemy.pos) continue;
      bodyPoint(enemy, origin.y, target);
      toTarget.subVectors(target, origin);
      const centreDist = toTarget.length();
      const radius = enemy.radius || 0.35;
      const surfaceDist = Math.max(0, centreDist - radius);
      if (surfaceDist > reach || surfaceDist >= bestDist) continue;
      if (centreDist > radius) {
        // Angle to the nearest edge of the body, not to its axis.
        const angle = Math.acos(THREE.MathUtils.clamp(toTarget.dot(d) / centreDist, -1, 1));
        if (angle - Math.asin(radius / centreDist) > cone / 2) continue;
      }
      if (!G.physics.lineOfSight(origin, target)) continue;
      best = enemy;
      bestDist = surfaceDist;
    }

    if (!best) {
      const world = G.physics.raycast(origin, d, reach, worldHit);
      res.dist = world ? world.dist : reach;
      res.point.copy(origin).addScaledVector(d, res.dist);
      if (world) {
        res.type = 'world';
        res.normal.copy(world.normal);
        res.surface = world.surface;
        res.box = world.box;
      } else {
        res.normal.copy(d).negate();
      }
      return res;
    }

    bodyPoint(best, origin.y, target);
    toTarget.subVectors(target, origin).normalize();
    res.type = 'enemy';
    res.enemy = best;
    res.part = 'body';
    res.dist = bestDist;
    res.surface = surfaceOf(best);
    res.point.copy(origin).addScaledVector(toTarget, bestDist);
    res.normal.copy(toTarget).negate();
    const out = has(G.enemies, 'damage')
      ? G.enemies.damage(best, damage, { point: res.point, dir: d, part: 'body', from: 'player', weapon: 'melee' })
      : null;
    res.killed = !!(out && out.killed);
    if (res.killed) countKill('body');
    emit('impact', { point: res.point, normal: res.normal, surface: res.surface, dir: d, from: 'player', enemy: best });
    emit('player:hitEnemy', { enemy: best, part: 'body', killed: res.killed, damage, weapon: 'melee' });
    return res;
  }

  /** Line of sight from a blast to an explosive: the explosive's own collider does not shield it. */
  function blastReaches(pos, item, point) {
    toTarget.subVectors(point, pos);
    const len = toTarget.length();
    if (len < 0.05) return true;
    const hit = G.physics.raycast(pos, toTarget, len, worldHit);
    return !hit || hit.box === item.box || (!!hit.box && hit.box.owner === item);
  }

  /**
   * A blast at `pos`: damage falls off linearly to zero at `radius` and needs line of sight.
   * Enemies take it in full, the player times `playerScale`, other explosives are damaged too (that is
   * the chain reaction). `source` is whatever blew up (it is skipped) and travels on the `explosion`
   * event; `size` ('small' | 'big') defaults from the radius.
   * Blast kills count as kills; blast damage is not a hit for accuracy. `weapon` is what a kill is
   * credited to on `enemy:killed` (a gun's id for a round that went off; 'blast' otherwise).
   */
  function explode({ pos, radius, damage, playerScale = 0.5, source = null, size, weapon = 'blast' }) {
    const centre = new THREE.Vector3().copy(pos);
    emit('explosion', {
      pos: centre,
      radius,
      size: size || (radius >= BIG_BLAST_RADIUS ? 'big' : 'small'),
      source,
    });
    if (!(radius > 0)) return;

    // Lists are walked backwards so a module that drops an entry while being damaged cannot make us skip one.
    const list = (G.enemies && G.enemies.list) || [];
    const canHurt = has(G.enemies, 'damage');
    for (let i = list.length - 1; canHurt && i >= 0; i--) {
      const enemy = list[i];
      if (!enemy || !enemy.alive || !enemy.pos || enemy === source) continue;
      const p = enemy.pos;
      target.set(p.x, enemy.type === 'buzzard' ? p.y : p.y + (enemy.height || PLAYER_STAND) * 0.5, p.z);
      const dist = target.distanceTo(centre);
      if (dist >= radius || !G.physics.lineOfSight(centre, target)) continue;
      const point = target.clone();
      const dir = dist > 1e-6 ? point.clone().sub(centre).divideScalar(dist) : new THREE.Vector3(0, 1, 0);
      const out = G.enemies.damage(enemy, damage * (1 - dist / radius), {
        point,
        dir,
        part: 'body',
        from: 'blast',
        weapon,
      });
      if (out && out.killed) countKill('body');
    }

    const player = G.player;
    if (player && player.pos && player.alive !== false && has(player, 'damage')) {
      target.copy(player.pos);
      target.y += player.crouching ? 0.6 : 1.0;
      const dist = target.distanceTo(centre);
      if (dist < radius && G.physics.lineOfSight(centre, target)) {
        player.damage(damage * playerScale * (1 - dist / radius), centre.clone(), 'blast');
      }
    }

    const items = (G.explosives && G.explosives.items) || [];
    const canChain = has(G.explosives, 'damage');
    for (let i = items.length - 1; canChain && i >= 0; i--) {
      const item = items[i];
      if (!item || item === source || item.state === 'gone' || !item.pos) continue;
      if (item.box) target.addVectors(item.box.min, item.box.max).multiplyScalar(0.5);
      else target.copy(item.pos).setY(item.pos.y + 0.4);
      const dist = target.distanceTo(centre);
      if (dist >= radius || !blastReaches(centre, item, target)) continue;
      G.explosives.damage(item, damage * (1 - dist / radius), 'blast');
    }
  }

  return { hitscan, melee, explode, stats, reset };
}
