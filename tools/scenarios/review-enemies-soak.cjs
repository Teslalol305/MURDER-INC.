// Review (enemies): soak in the real block from a chosen player spot, units from the level's own spawn points.
// env: RV_POS="x,y,z" RV_GOONS RV_BUZZ RV_STEPS RV_DIFF RV_FIGHT=1 (player damages nearest every 2 s) RV_SHOT=name
'use strict';
const POS = (process.env.RV_POS || '').split(',').map(Number);
const GOONS = +(process.env.RV_GOONS || 8);
const BUZZ = +(process.env.RV_BUZZ || 4);
const STEPS = +(process.env.RV_STEPS || 1800);
const DIFF = process.env.RV_DIFF || 'boss';
const FIGHT = process.env.RV_FIGHT === '1';
const SHOT = process.env.RV_SHOT || '';
const CROUCH = process.env.RV_CROUCH === '1';

module.exports = async (page, h) => {
  await h.skip(5);
  await h.eval(
    ([pos, goons, buzz, diff, crouch]) => {
      const G = window.__G;
      const V = G.THREE.Vector3;
      G.game.setDifficulty(diff);
      G.enemies.clear();
      if (pos.length === 3 && pos.every((v) => Number.isFinite(v))) G.player.reset({ pos: new V(pos[0], pos[1], pos[2]), yaw: 0 });
      const s = (window.__rv = { dmg: { bullet: 0, bolt: 0, melee: 0, blast: 0 }, n: { bullet: 0, bolt: 0, melee: 0, blast: 0 }, log: [], fire: 0, tele: 0, alerts: 0, killed: 0, maxAttack: 0 });
      const damage = G.player.damage.bind(G.player);
      G.player.damage = (amount, from, kind) => {
        s.dmg[kind] = (s.dmg[kind] || 0) + amount;
        s.n[kind] = (s.n[kind] || 0) + 1;
        s.log.push([G.enemies.debug().clock, amount, kind]);
        return damage(amount, from, kind);
      };
      if (crouch) {
        Object.defineProperty(G.player, 'crouching', { get: () => true, configurable: true });
      }
      G.events.on('enemy:fire', () => s.fire++);
      G.events.on('enemy:telegraph', () => s.tele++);
      G.events.on('enemy:alert', () => s.alerts++);
      G.events.on('enemy:killed', () => s.killed++);
      const p = G.player.pos;
      const sp = G.level.enemySpawns;
      window.__wave = (ng, nb) => {
        const ground = sp.filter((q) => q.type === 'ground').sort((a, b) => a.pos.distanceTo(p) - b.pos.distanceTo(p));
        const air = sp.filter((q) => q.type === 'air').sort((a, b) => a.pos.distanceTo(p) - b.pos.distanceTo(p));
        for (let i = 0; i < ng; i++) G.enemies.spawn('goon', ground[(i * 2 + 1) % ground.length].pos.clone(), { alerted: true });
        for (let i = 0; i < nb; i++) G.enemies.spawn('buzzard', air[(i * 2) % air.length].pos.clone(), { alerted: true });
      };
      window.__wave(goons, buzz);
      window.__trk = {};
      const perf = (window.__perf = { n: 0, sum: 0, max: 0, over2: 0 });
      const upd = G.enemies.update;
      G.enemies.update = (dt) => {
        const t0 = performance.now();
        upd(dt);
        const ms = performance.now() - t0;
        perf.n++; perf.sum += ms; if (ms > perf.max) { perf.max = ms; perf.maxAt = perf.n; } if (ms > 20) (perf.big = perf.big || []).push([perf.n, +ms.toFixed(1)]); if (ms > 2) perf.over2++;
      };
    },
    [POS, GOONS, BUZZ, DIFF, CROUCH],
  );
  const issues = new Map();
  const note = (k) => issues.set(k, (issues.get(k) || 0) + 1);
  for (let done = 0; done < STEPS; done += 30) {
    await h.skip(30);
    const r = await h.eval(
      ([fight, done, goons, buzz]) => {
        const G = window.__G;
        const P = G.physics;
        const s = window.__rv;
        const now = G.enemies.debug().clock;
        const out = [];
        if (fight && done % 60 === 0) {
          if (G.enemies.aliveCount() < 3) window.__wave(goons, buzz);
          let best = null;
          for (const e of G.enemies.list) if (e.alive && (!best || e.pos.distanceTo(G.player.pos) < best.pos.distanceTo(G.player.pos))) best = e;
          if (best) G.enemies.damage(best, 45, { point: best.pos.clone(), dir: best.pos.clone().sub(G.player.eye).normalize(), part: 'body', from: 'player', weapon: 'chopper' });
        }
        let attacking = 0;
        const el = G.level.el;
        const b = P.bounds;
        for (const e of G.enemies.list) {
          if (!e.alive) continue;
          const id = `${e.type}#${e.id}`;
          if (e.type === 'goon' && (e.sub === 'telegraph' || e.sub === 'burst') && e.mode === 'engage') attacking++;
          if (e.type === 'buzzard' && (e.telegraph > 0 || e.burstLeft > 0)) attacking++;
          if (e.type === 'goon') {
            if (P.overlapsCylinder(e.pos.x, e.pos.z, 0.22, e.pos.y + 0.45, e.pos.y + 1.7)) out.push(`goon in geometry ${e.mode}/${e.sub} ${e.pos.x.toFixed(1)},${e.pos.y.toFixed(2)},${e.pos.z.toFixed(1)}`);
            if (!P.nav.isWalkable(e.pos.x, e.pos.z) && e.pos.y < 0.5) out.push(`goon off nav ${e.pos.x.toFixed(1)},${e.pos.z.toFixed(1)}`);
            const t = (window.__trk[id] = window.__trk[id] || { x: e.pos.x, z: e.pos.z, at: now, want: 0, flips: 0, yaw: e.yaw });
            if (e.moveSpeed > 0.3 || e.wantSpeed > 0) t.want += 1;
            const moved = Math.hypot(e.pos.x - t.x, e.pos.z - t.z);
            if (now - t.at >= 6) {
              if (t.want >= 5 && moved < 1) out.push(`goon stuck ${e.mode}/${e.sub} near ${e.pos.x.toFixed(1)},${e.pos.z.toFixed(1)} goal ${e.goalX.toFixed(1)},${e.goalZ.toFixed(1)} path=${e.hasPath} fails=${e.pathFails}`);
              t.x = e.pos.x; t.z = e.pos.z; t.at = now; t.want = 0;
            }
          } else {
            if (P.overlapsCylinder(e.pos.x, e.pos.z, 0.35, e.pos.y - 0.15, e.pos.y + 0.15)) {
              const bx = P.boxes.find((q) => !q.bulletOnly && q.max.y > e.pos.y - 0.15 && q.min.y < e.pos.y + 0.15 && e.pos.x > q.min.x - 0.35 && e.pos.x < q.max.x + 0.35 && e.pos.z > q.min.z - 0.35 && e.pos.z < q.max.z + 0.35);
              out.push(`buzzard in geometry ${bx && bx.tag} ${bx && bx.playerOnly ? 'PO' : ''} ${e.mode} ${e.pos.x.toFixed(1)},${e.pos.y.toFixed(2)},${e.pos.z.toFixed(1)}`);
            }
            if (el && e.pos.y > el.y - 0.3 && e.pos.y < el.deckTop + 0.3 && Math.abs(e.pos.z) < el.maxZ + 0.4) out.push(`buzzard in deck ${e.pos.x.toFixed(1)},${e.pos.y.toFixed(2)},${e.pos.z.toFixed(1)}`);
            if (e.pos.x < b.minX || e.pos.x > b.maxX || e.pos.z < b.minZ || e.pos.z > b.maxZ || e.pos.y > 16) out.push('buzzard out of bounds');
          }
        }
        s.maxAttack = Math.max(s.maxAttack, attacking);
        return out;
      },
      [FIGHT, done, GOONS, BUZZ],
    );
    for (const k of r) note(k);
    const snap = process.env.RV_SNAP;
    const hit = snap && r.find((k) => k.includes(snap));
    if (hit && !global.__snapped) {
      global.__snapped = true;
      const m = hit.match(/(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)$/);
      const [x, y, z] = [+m[1], +m[2], +m[3]];
      console.log('SNAP at step', done, hit);
      await h.eval((c) => window.__setShot({ cam: c, fov: 50 }), `${x + 2.5},${y + 0.8},${z + 3.2},${x},${y},${z - 0.3}`);
      await h.frames(2);
      await h.shot(`shots/review/snap-${snap.replace(/\W/g, '')}.png`);
      await h.eval(() => window.__setShot({ cam: '' }));
    }
  }
  const s = await h.eval(() => {
    const G = window.__G;
    const s = window.__rv;
    // worst damage windows
    const win = (w) => {
      let best = 0;
      for (let i = 0; i < s.log.length; i++) {
        let sum = 0;
        for (let j = i; j < s.log.length && s.log[j][0] - s.log[i][0] <= w; j++) sum += s.log[j][1];
        best = Math.max(best, sum);
      }
      return +best.toFixed(1);
    };
    const units = G.enemies.list.filter((e) => e.alive).map((e) => `${e.type}:${e.mode}/${e.sub || '-'}@${e.pos.x.toFixed(1)},${e.pos.y.toFixed(1)},${e.pos.z.toFixed(1)} exp${(e.exposure || 0).toFixed(2)}`);
    const pf = window.__perf; return { perf: { mean: +(pf.sum / pf.n).toFixed(3), max: +pf.max.toFixed(2), over2: pf.over2, n: pf.n, maxAt: pf.maxAt, big: pf.big, rebuilds: window.__G.physics.nav.rebuilds }, dmg: s.dmg, n: s.n, w1: win(1), w2: win(2), w4: win(4), fire: s.fire, tele: s.tele, alerts: s.alerts, killed: s.killed, maxAttack: s.maxAttack, units, clock: G.enemies.debug().clock, player: [G.player.pos.x, G.player.pos.y, G.player.pos.z], debug: { ...G.enemies.debug(), tune: undefined } };
  });
  console.log(JSON.stringify(s));
  console.log('ISSUES', JSON.stringify([...issues.entries()].slice(0, 40)));
  if (SHOT) {
    await h.frames(2);
    await h.shot(`shots/review/${SHOT}.png`);
  }
};
