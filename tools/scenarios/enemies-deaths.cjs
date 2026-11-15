// Deaths: Goons collapse away from the killing shot and stay as bodies (at most 6, the oldest fades),
// a Buzzard spins down and bursts where it lands (explosion r 3). Pictures of the collapse, the bodies
// and the Buzzard on its way down.
//
//   node build.mjs --dev --only=enemies --out=dist/dev-enemies.html
//   node tools/shot.cjs dist/dev-enemies.html --params "autostart=1&q=test&god=1&noaudio=1&nohud=1" \
//        --size 800x450 --scenario tools/scenarios/enemies-deaths.cjs --timeout 400

'use strict';

const OUT = 'shots/enemies/death-';

module.exports = async (page, h) => {
  await h.eval(() => {
    const G = window.__G;
    const V = G.THREE.Vector3;
    const s = (window.__dd = { killed: [], explosions: [], hits: 0 });
    G.events.on('enemy:killed', (ev) => s.killed.push(`${ev.type}:${ev.part}:${ev.byPlayer}`));
    G.events.on('enemy:hit', () => s.hits++);
    G.events.on('explosion', (ev) => s.explosions.push({ r: ev.radius, y: +ev.pos.y.toFixed(2), source: ev.source && ev.source.type }));
    G.enemies.clear();
    const p = G.player.pos;
    window.__units = [];
    for (let i = 0; i < 3; i++) window.__units.push(G.enemies.spawn('goon', new V(p.x + 10, 0, p.z - 3 + i * 3), { passive: true, yaw: -Math.PI / 2 }));
    window.__units.push(G.enemies.spawn('buzzard', new V(p.x + 12, 4, p.z), { passive: true }));
    window.__kill = (e, part, dirX) => {
      const dir = new V(dirX, 0, 0);
      G.enemies.damage(e, 999, { point: e.pos.clone().setY(e.pos.y + 1.2), dir, part, from: 'player', weapon: 'chopper' });
    };
  });
  await h.skip(10);
  // Shot from the west (the player): they fall east, away from him. One headshot.
  await h.eval(() => {
    const u = window.__units;
    window.__kill(u[0], 'body', 1);
    window.__kill(u[1], 'head', 1);
    window.__kill(u[3], 'body', 1);
  });
  const p = await h.eval(() => [window.__G.player.pos.x, window.__G.player.pos.z]);
  const cam = `${p[0] + 6},2.4,${p[1] + 7},${p[0] + 11},0.8,${p[1]}`;
  await h.eval((c) => window.__setShot({ cam: c, fov: 60 }), cam);
  await h.skip(8);
  await h.frames(1);
  await h.shot(`${OUT}falling.png`);
  await h.skip(60);
  await h.frames(1);
  await h.shot(`${OUT}bodies.png`);

  // Eight more Goons die one after the other: only six bodies may stay.
  await h.eval(() => {
    const G = window.__G;
    const V = G.THREE.Vector3;
    const q = G.player.pos;
    for (let i = 0; i < 8; i++) {
      const e = G.enemies.spawn('goon', new V(q.x + 6 + i, 0, q.z + 4), { passive: true });
      if (e) window.__kill(e, 'body', i % 2 ? 1 : -1);
    }
  });
  await h.skip(400);
  const s = await h.eval(() => {
    const G = window.__G;
    return { ...window.__dd, debug: { ...G.enemies.debug(), tune: undefined }, alive: G.enemies.aliveCount(), list: G.enemies.list.length };
  });
  console.log(JSON.stringify(s));
  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
  if (s.killed.length !== 11) throw new Error(`expected 11 kills, got ${s.killed.length}`);
  if (!s.explosions.some((x) => x.r === 3)) throw new Error('no Buzzard burst');
  if (s.debug.bodies > 6) throw new Error(`${s.debug.bodies} bodies kept`);
};
