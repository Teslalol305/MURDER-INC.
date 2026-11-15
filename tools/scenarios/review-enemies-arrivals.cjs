// Review (enemies): the real mission flow. The player stands at each reel and grabs it; every arrival is
// checked for being in plain view (line of sight from the player's eye, distance) when it pops in.
'use strict';
const DIFF = process.env.RV_DIFF || 'boss';
module.exports = async (page, h) => {
  await h.skip(5);
  await h.eval((diff) => {
    const G = window.__G;
    G.game.setDifficulty(diff);
    const s = (window.__rv = { arrivals: [], patrol: [] });
    G.events.on('enemy:spawn', (ev) => {
      const e = ev.enemy;
      const eye = G.player.eye;
      const c = e.pos.clone();
      if (e.type === 'goon') c.y += 1.2;
      const los = G.physics.lineOfSight(eye, c);
      const d = Math.hypot(c.x - eye.x, c.z - eye.z);
      // inside a 100 degree horizontal view cone of the player's facing?
      const f = G.player.forward;
      const dot = ((c.x - eye.x) * f.x + (c.z - eye.z) * f.z) / (d * Math.hypot(f.x, f.z) || 1);
      s.arrivals.push({ type: e.type, at: [+e.pos.x.toFixed(1), +e.pos.y.toFixed(1), +e.pos.z.toFixed(1)], los, d: +d.toFixed(1), inView: los && dot > Math.cos((50 * Math.PI) / 180), t: +G.enemies.debug().clock.toFixed(1) });
    });
  }, DIFF);
  const reels = await h.eval(() => window.__G.level.objectives.map((o) => [o.pos.x, o.pos.y, o.pos.z]));
  // The run was started before our listener: record the starting patrol too.
  await h.eval(() => {
    const G = window.__G;
    window.__rv.patrol = G.enemies.list.map((e) => `${e.type}@${e.pos.x.toFixed(1)},${e.pos.z.toFixed(1)}`);
  });
  for (let k = 0; k < reels.length; k++) {
    for (const yawDeg of [0]) {
      await h.eval(
        ([p, yaw]) => {
          const G = window.__G;
          const V = G.THREE.Vector3;
          G.player.reset({ pos: new V(p[0] + 1.2, p[1], p[2] + 1.2), yaw });
          G.game.debugGrab();
        },
        [reels[k], (yawDeg * Math.PI) / 180],
      );
    }
    // Keep the player in place, turning slowly, while the wave lands.
    for (let i = 0; i < 20; i++) {
      await h.skip(30);
      await h.eval(([p, i]) => {
        const G = window.__G;
        G.player.pos.set(p[0] + 1.2, p[1], p[2] + 1.2);
        G.player.yaw = i * 0.6;
      }, [reels[k], i]);
    }
    await h.eval(() => {
      const G = window.__G;
      for (const e of [...G.enemies.list]) if (e.alive) G.enemies.damage(e, 9999, { from: 'player', part: 'body' });
    });
    await h.skip(60);
  }
  const s = await h.eval(() => window.__rv);
  const vis = s.arrivals.filter((a) => a.los);
  console.log('ARRIVALS', s.arrivals.length, 'with LOS', vis.length, 'in view', s.arrivals.filter((a) => a.inView).length);
  console.log(JSON.stringify(vis));
  console.log('PATROL', JSON.stringify(s.patrol));
};
