// Review (enemies): a Goon on the sidewalk, the player just inside the cage fence. Does the pipe reach through?
'use strict';
module.exports = async (page, h) => {
  await h.skip(5);
  await h.eval(() => {
    const G = window.__G;
    const V = G.THREE.Vector3;
    G.enemies.clear();
    G.player.reset({ pos: new V(27, 0, -12.65), yaw: 0 });
    const s = (window.__rv = { hits: [] });
    const damage = G.player.damage.bind(G.player);
    G.player.damage = (amount, from, kind) => {
      s.hits.push([kind, +amount.toFixed(1), +G.player.pos.z.toFixed(2)]);
      return damage(amount, from, kind);
    };
    s.melee = [];
    G.events.on('enemy:melee', (ev) => s.melee.push([ev.phase, +ev.enemy.pos.x.toFixed(2), +ev.enemy.pos.z.toFixed(2)]));
    const e = G.enemies.spawn('goon', new V(27, 0.15, -11.6), { alerted: true, yaw: Math.PI });
    window.__e = e;
  });
  const log = [];
  for (let i = 0; i < 12; i++) {
    await h.skip(15);
    log.push(await h.eval(() => {
      const G = window.__G;
      const e = window.__e;
      G.player.pos.set(27, G.player.pos.y, -12.65); // the player keeps his spot
      return `${e.mode}/${e.sub} goon ${e.pos.x.toFixed(2)},${e.pos.z.toFixed(2)} player z ${G.player.pos.z.toFixed(2)} d=${Math.hypot(e.pos.x - G.player.pos.x, e.pos.z - G.player.pos.z).toFixed(2)}`;
    }));
  }
  const s = await h.eval(() => window.__rv);
  console.log(log.join('\n'));
  console.log('RESULT', JSON.stringify(s));
};
