// Integration tour: the title, then the player's own view from a dozen spots on the block, then a fight.
//
//   node build.mjs --dev --out=dist/dev-all.html
//   node tools/shot.cjs dist/dev-all.html --params "q=medium&god=1&noaudio=1" --size 1280x720 --scenario tools/scenarios/tour.cjs --timeout 900
//   TOUR_TIME=night TOUR_OUT=shots/tour-night node tools/shot.cjs … (same)
//   TOUR_ONLY=title,start,fight   run a subset (names below)

const OUT = process.env.TOUR_OUT || 'shots/tour';
const TIME = process.env.TOUR_TIME || 'day';
const ONLY = process.env.TOUR_ONLY ? process.env.TOUR_ONLY.split(',') : null;

module.exports = async (page, h) => {
  const want = (name) => !ONLY || ONLY.includes(name);
  const shot = (name) => h.shot(`${OUT}/${name}.png`);

  await h.eval((time) => window.__G.settings.set('time', time), TIME);
  if (want('title')) {
    await h.skip(150); // 5 s into the fly-through, past its fade-in
    await h.frames(2);
    await shot('00-title');
  }

  await h.eval(() => window.__G.game.start({ mode: 'mission', skipIntro: true }));
  await h.skip(20);
  await h.frames(2);

  // Each stop: stand at `at` (snapped to walkable ground) and look at `look`.
  const stops = await h.eval(() => {
    const G = window.__G;
    const L = G.level;
    const o = L.objectives.map((x) => x.pos);
    const ex = L.extraction.pos;
    const v = (p, dx = 0, dy = 0, dz = 0) => [p.x + dx, p.y + dy, p.z + dz];
    const s = L.playerStart.pos;
    return [
      { name: '01-start', at: v(s), yaw: L.playerStart.yaw },
      { name: '02-avenue-east', at: [-24, 0, 0], look: [20, 1.5, 0] },
      { name: '03-avenue-west', at: [16, 0, 2], look: [-30, 3, 0] },
      { name: '04-reel1', at: v(o[0], -6, 0, 3), look: v(o[0], 0, 0.8, 0) },
      { name: '05-shop-front', at: v(o[1], 1, 0, 14), look: v(o[1], 0, 1.5, 0) },
      { name: '06-shop-inside', at: v(o[1], 6, 0, 3), look: v(o[1], -4, 1.2, -2) },
      { name: '07-shop-out', at: v(o[1], 0, 0, -3), look: v(o[1], 0, 1.4, 20) },
      { name: '08-cage', at: v(o[2], -8, 0, 6), look: v(o[2], 0, 1.0, 0) },
      { name: '09-lot-truck', at: v(ex, -12, 0, -8), look: v(ex, 0, 1.5, 0) },
      { name: '10-vantage', at: [L.vantage.deck.x, L.vantage.deck.y, L.vantage.deck.z], look: v(o[0], 0, 0, 0), raw: true },
      { name: '11-vacant-lot', at: [-10, 0, 20], look: [-16, 2.5, 20] },
      { name: '12-rear-lane', at: [-8, 0, 28.5], look: [20, 1.5, 28.5] },
    ];
  });

  for (const stop of stops) {
    if (!want(stop.name.slice(3)) && !want(stop.name)) continue;
    const where = await h.eval((s) => {
      const G = window.__G;
      const p = G.player;
      let x = s.at[0], y = s.at[1], z = s.at[2];
      if (!s.raw) {
        const w = G.physics.nav.nearestWalkable(x, z, 6);
        if (w) { x = w.x; z = w.z; }
        y = G.physics.groundHeight(x, z, 1.0);
      }
      p.pos.set(x, y, z);
      p.vel.set(0, 0, 0);
      if (s.look) {
        const dx = s.look[0] - x, dz = s.look[2] - z, dy = s.look[1] - (y + 1.68);
        p.yaw = Math.atan2(-dx, -dz);
        p.pitch = Math.atan2(dy, Math.hypot(dx, dz));
      } else {
        p.yaw = s.yaw; p.pitch = 0;
      }
      return { x: +x.toFixed(1), y: +y.toFixed(2), z: +z.toFixed(1), zone: G.level.zoneName ? G.level.zoneName(x, z) : G.level.zoneAt(x, z) };
    }, stop);
    await h.skip(12);
    await h.frames(2);
    await shot(stop.name);
    console.log(stop.name, JSON.stringify(where));
  }

  if (want('fight')) {
    // A fight on the avenue: two Goons and a Buzzard ahead, the player firing.
    await h.eval(() => {
      const G = window.__G;
      const p = G.player;
      p.pos.set(-20, G.physics.groundHeight(-20, 1.5, 1), 1.5);
      p.vel.set(0, 0, 0);
      p.yaw = Math.atan2(-1, 0); // facing east (+X)
      p.pitch = 0.02;
      G.enemies.clear();
      const V = G.THREE.Vector3;
      G.enemies.spawn('goon', new V(-8, 0, 0.5), { alerted: true });
      G.enemies.spawn('goon', new V(-5, 0, 3.5), { alerted: true });
      G.enemies.spawn('buzzard', new V(-6, 5, -2), { alerted: true });
    });
    await h.skip(45);
    await h.frames(2);
    await shot('20-fight-contact');
    await h.key('Mouse0', true);
    await h.skip(8);
    await h.frames(2);
    await shot('21-fight-firing');
    await h.skip(20);
    await h.frames(1);
    await shot('22-fight-burst');
    await h.key('Mouse0', false);
    await h.key('Mouse2', true);
    await h.skip(14);
    await h.frames(2);
    await shot('23-ads');
    await h.key('Mouse2', false);
  }

  const stats = await h.stats();
  console.log('stats', JSON.stringify({ calls: stats.calls, frameCalls: stats.frameCalls, tris: stats.triangles, tex: stats.textures, programs: stats.programs, fps: stats.fps, errors: stats.errors }));
};
