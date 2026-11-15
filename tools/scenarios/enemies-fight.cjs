// The Vultures in a fight: Goons and Buzzards spawn alerted down the avenue and engage the player (god
// mode, standing still). Checks that they path, take fire positions, telegraph, fire bursts and bolts,
// hit the player, and that nobody engaged stands idle for 10 s. Pictures from outside along the way.
//
//   node build.mjs --dev --only=enemies --out=dist/dev-enemies.html
//   node tools/shot.cjs dist/dev-enemies.html --params "autostart=1&q=test&god=1&noaudio=1&nohud=1" \
//        --size 800x450 --scenario tools/scenarios/enemies-fight.cjs --timeout 600
//
// Optional: ENEMIES_SOAK=2000 runs that many steps (with a respawn whenever the field thins out) and
// checks the same things; ENEMIES_GOONS / ENEMIES_BUZZARDS set the spawn counts (default 4 + 2).
// ENEMIES_POS="x,y,z" keeps the player there (the scaffold deck is 10,2.95,9.3, the shop's office
// -21,2.8,-29) and brings the waves in from the level's own spawn points instead. A soak also fails on a
// Buzzard whose airframe overlaps anything solid or leaves the bounds, a Buzzard that is not fighting and
// has not moved a metre in 10 s, and a Goon that wants to walk but has not moved a metre in 10 s.

'use strict';

const OUT = 'shots/enemies/fight-';
const SOAK = +(process.env.ENEMIES_SOAK || 0);
const GOONS = +(process.env.ENEMIES_GOONS || 4);
const BUZZ = +(process.env.ENEMIES_BUZZARDS || 2);
const SHOTS = process.env.ENEMIES_SHOTS !== '0';
const POS = (process.env.ENEMIES_POS || '').split(',').filter(Boolean).map(Number);

module.exports = async (page, h) => {
  const setup = await h.eval(
    ([goons, buzz, pos]) => {
      const G = window.__G;
      const V = G.THREE.Vector3;
      const s = (window.__en = { fire: { goon: 0, buzzard: 0 }, tele: 0, melee: 0, hits: 0, bolt: 0, bullet: 0, alert: 0, killed: 0, lastFire: {} });
      G.events.on('enemy:fire', (ev) => {
        s.fire[ev.type]++;
        s.lastFire[ev.enemy.id] = G.enemies.debug().clock;
      });
      G.events.on('enemy:telegraph', () => s.tele++);
      G.events.on('enemy:melee', () => s.melee++);
      G.events.on('enemy:alert', () => s.alert++);
      G.events.on('enemy:killed', () => s.killed++);
      // god=1 swallows player:hit, so count the calls themselves.
      const damage = G.player.damage.bind(G.player);
      G.player.damage = (amount, from, kind) => {
        s.hits++;
        if (kind === 'bolt') s.bolt++;
        if (kind === 'bullet') s.bullet++;
        if (kind === 'melee') s.rush = (s.rush || 0) + 1;
        return damage(amount, from, kind);
      };
      G.enemies.clear();
      if (pos.length === 3) G.player.reset({ pos: new V(pos[0], pos[1], pos[2]), yaw: 0 });
      const p = G.player.pos;
      let wave = 0;
      window.__spawnWave = (ng, nb) => {
        if (pos.length === 3) {
          // From the level's own spawn points, the nearer ones first, a different few every wave.
          const sp = G.level.enemySpawns;
          const ground = sp.filter((q) => q.type === 'ground').sort((a, b) => a.pos.distanceTo(p) - b.pos.distanceTo(p));
          const air = sp.filter((q) => q.type === 'air').sort((a, b) => a.pos.distanceTo(p) - b.pos.distanceTo(p));
          for (let i = 0; i < ng; i++) G.enemies.spawn('goon', ground[(i * 2 + 1 + wave) % ground.length].pos.clone(), { alerted: true });
          for (let i = 0; i < nb; i++) G.enemies.spawn('buzzard', air[(i * 2 + wave) % air.length].pos.clone(), { alerted: true });
          wave++;
          return;
        }
        for (let i = 0; i < ng; i++) G.enemies.spawn('goon', new V(p.x + 22 + (i % 3) * 3, 0, p.z - 3 + i * 1.6), { alerted: true });
        for (let i = 0; i < nb; i++) G.enemies.spawn('buzzard', new V(p.x + 26, 4, p.z - 2 + i * 3), { alerted: true });
      };
      window.__spawnWave(goons, buzz);
      // Every engaged unit records when it last moved or fired.
      window.__track = {};
      window.__checkIdle = () => {
        const now = G.enemies.debug().clock;
        const bad = [];
        for (const e of G.enemies.list) {
          if (!e.alive) continue;
          const t = (window.__track[e.id] = window.__track[e.id] || { x: e.pos.x, z: e.pos.z, at: now });
          const movedFar = Math.hypot(e.pos.x - t.x, e.pos.z - t.z) > 0.5;
          const fired = (s.lastFire[e.id] || -1) > t.at;
          if (movedFar || fired || e.mode !== 'engage') {
            t.x = e.pos.x;
            t.z = e.pos.z;
            t.at = now;
          } else if (now - t.at > 10) bad.push(`${e.type}#${e.id} ${e.sub || ''} at ${e.pos.x.toFixed(1)},${e.pos.z.toFixed(1)}`);
        }
        return bad;
      };
      return { n: G.enemies.list.length, p: [p.x, p.z] };
    },
    [GOONS, BUZZ, POS],
  );
  if (setup.n !== GOONS + BUZZ) throw new Error(`spawned ${setup.n}`);
  const [px, pz] = setup.p;

  const look = async (name, cam) => {
    if (!SHOTS) return;
    await h.eval((c) => window.__setShot({ cam: c, fov: 60 }), cam);
    await h.frames(2);
    await h.shot(`${OUT}${name}.png`);
    await h.eval(() => window.__setShot({ cam: '' }));
  };

  const steps = SOAK || 600;
  const idle = [];
  for (let done = 0; done < steps; done += 60) {
    await h.skip(60);
    const r = await h.eval(
      ([goons, buzz, soak, pos]) => {
        const G = window.__G;
        if (pos.length === 3) G.player.pos.set(pos[0], pos[1], pos[2]); // he stays put
        if (soak && G.enemies.aliveCount() < 3) window.__spawnWave(goons, buzz);
        if (soak) {
          // The player fights back: 45 damage to the nearest unit every two seconds.
          let best = null;
          for (const e of G.enemies.list) if (e.alive && (!best || e.pos.distanceTo(G.player.pos) < best.pos.distanceTo(G.player.pos))) best = e;
          if (best) {
            const dir = best.pos.clone().sub(G.player.eye).normalize();
            G.enemies.damage(best, 45, { point: best.pos.clone(), dir, part: 'body', from: 'player', weapon: 'chopper' });
          }
        }
        // How often Goons are seen at cover, and kneeling there.
        const st = window.__en;
        for (const e of G.enemies.list) {
          if (!e.alive || e.type !== 'goon' || e.mode !== 'engage') continue;
          st.engagedSamples = (st.engagedSamples || 0) + 1;
          if (e.atCover) st.atCover = (st.atCover || 0) + 1;
          if (e.atCover) (st.coverSub = st.coverSub || {})[e.sub + (e.arrived ? '+' : '')] = ((st.coverSub || {})[e.sub + (e.arrived ? '+' : '')] || 0) + 1;
          if (e.atCover && e.anim.crouch > 0.5) st.kneeling = (st.kneeling || 0) + 1;
        }
        // Nobody inside solid geometry (a Buzzard in the El deck, a Goon in a car).
        const clipped = [];
        for (const e of G.enemies.list) {
          if (!e.alive) continue;
          const y = e.type === 'goon' ? e.pos.y + 0.9 : e.pos.y;
          for (const b of G.physics.boxes) {
            if (b.playerOnly || b.bulletOnly) continue;
            if (e.pos.x > b.min.x + 0.05 && e.pos.x < b.max.x - 0.05 && y > b.min.y + 0.05 && y < b.max.y - 0.05 && e.pos.z > b.min.z + 0.05 && e.pos.z < b.max.z - 0.05) {
              clipped.push(`${e.type}#${e.id} inside ${b.tag || b.surface} at ${e.pos.x.toFixed(1)},${e.pos.y.toFixed(1)},${e.pos.z.toFixed(1)}`);
              break;
            }
          }
        }
        if (soak) {
          // Airframes in geometry or out of the block; anyone stuck.
          const P = G.physics;
          const b = P.bounds;
          const now = G.enemies.debug().clock;
          const trk = (window.__stuck = window.__stuck || {});
          for (const e of G.enemies.list) {
            if (!e.alive) continue;
            if (e.type === 'buzzard') {
              const q = P.boxes.find((k) => !k.bulletOnly && (!k.playerOnly || k.tag === 'hoist' || k.tag === 'office-glass') && k.max.y > e.pos.y - 0.15 && k.min.y < e.pos.y + 0.15 &&
                Math.hypot(e.pos.x - Math.max(k.min.x, Math.min(k.max.x, e.pos.x)), e.pos.z - Math.max(k.min.z, Math.min(k.max.z, e.pos.z))) < 0.35);
              if (q) clipped.push(`buzzard#${e.id} airframe in ${q.tag || q.surface} at ${e.pos.x.toFixed(1)},${e.pos.y.toFixed(1)},${e.pos.z.toFixed(1)}`);
              if (e.pos.x < b.minX || e.pos.x > b.maxX || e.pos.z < b.minZ || e.pos.z > b.maxZ || e.pos.y > 16) clipped.push(`buzzard#${e.id} out of bounds at ${e.pos.x.toFixed(1)},${e.pos.y.toFixed(1)},${e.pos.z.toFixed(1)}`);
            }
            const t = (trk[e.id] = trk[e.id] || { x: e.pos.x, y: e.pos.y, z: e.pos.z, at: now, want: 0 });
            if (e.type === 'goon' && e.wantSpeed > 0) t.want++;
            const moved = Math.hypot(e.pos.x - t.x, e.pos.y - t.y, e.pos.z - t.z);
            const span = 10; // a Goon's own give-up on a fire position it cannot reach is 7 s (goon.move.giveUp)
            if (now - t.at >= span) {
              if (moved < 1 && (e.type === 'goon' ? t.want >= 5 : e.mode !== 'engage')) clipped.push(`${e.type}#${e.id} stuck ${e.mode}/${e.sub || '-'} at ${e.pos.x.toFixed(1)},${e.pos.y.toFixed(1)},${e.pos.z.toFixed(1)}${e.type === 'goon' ? ` goal ${e.goalX.toFixed(1)},${e.goalZ.toFixed(1)} path=${e.hasPath} fails=${e.pathFails} speed=${e.wantSpeed.toFixed(1)}/${e.moveSpeed.toFixed(1)}` : ''}`);
              t.x = e.pos.x;
              t.y = e.pos.y;
              t.z = e.pos.z;
              t.at = now;
              t.want = 0;
            }
          }
        }
        return [...window.__checkIdle(), ...clipped];
      },
      [GOONS, BUZZ, SOAK, POS],
    );
    idle.push(...r);
    if (done === 120) await look('approach', `${px - 4},6,${pz + 10},${px + 14},0.8,${pz}`);
    if (done === 300) await look('engaged', `${px + 2},3,${pz + 6},${px + 14},1,${pz}`);
    if (done === 360 && SHOTS) {
      // What the player sees: turn him toward the nearest Goon.
      await h.eval(() => {
        const G = window.__G;
        const p = G.player.pos;
        let best = null;
        for (const e of G.enemies.list) if (e.alive && e.type === 'goon' && (!best || e.pos.distanceTo(p) < best.pos.distanceTo(p))) best = e;
        if (best) G.player.yaw = Math.atan2(-(best.pos.x - p.x), -(best.pos.z - p.z));
        G.player.pitch = 0;
      });
      await h.frames(2);
      await h.shot(`${OUT}player-view.png`);
    }
  }
  const s = await h.eval(() => {
    const G = window.__G;
    const units = G.enemies.list.map((e) => `${e.type}:${e.mode}/${e.sub || '-'}@${e.pos.x.toFixed(1)},${e.pos.y.toFixed(1)},${e.pos.z.toFixed(1)}`);
    return { ...window.__en, units, debug: { ...G.enemies.debug(), tune: undefined } };
  });
  console.log(JSON.stringify(s, null, 1));
  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
  if (idle.length) throw new Error(`idle or clipped units: ${[...new Set(idle)].join('; ')}`);
  if (GOONS && !s.fire.goon) throw new Error('no Goon fired');
  if (BUZZ && !s.fire.buzzard) throw new Error('no Buzzard fired');
  if (!s.tele) throw new Error('no telegraphs');
  if (!s.hits) throw new Error('the player was never hit');
};
