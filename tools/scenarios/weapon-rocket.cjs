// The ROCKET in play: a round sent down the street at a knot of Vultures. Checks that it flies, goes
// off where it lands, takes them with it and is credited for it; takes the pictures the trail and the
// blast are judged by.
//
//   node tools/shot.cjs dist/dev-all.html --size 960x540 --params "autostart=1&q=medium&god=1&noaudio=1" \
//        --scenario tools/scenarios/weapon-rocket.cjs
//   ROCKET_NOSHOTS=1 skips the pictures (shots/weapon/rocket-*.png).

module.exports = async (page, h) => {
  const problems = [];
  const shot = async (name) => {
    if (process.env.ROCKET_NOSHOTS) return;
    await h.frames(1);
    await h.shot(`shots/weapon/rocket-${name}.png`);
  };
  // The pointer rests on the middle of the view: the harness presses buttons there, and under pointer
  // lock a pointer that had to travel first would turn Rule's head.
  const port = page.viewportSize() || { width: 960, height: 540 };
  await page.mouse.move(port.width / 2, port.height / 2);
  await h.skip(20);
  // Three Vultures standing together in plain view down the street, and nobody else on the block.
  const setup = await h.eval(() => {
    const G = window.__G;
    const V = G.THREE.Vector3;
    G.enemies.clear();
    const p = G.player;
    const f = new V(p.forward.x, 0, p.forward.z).normalize();
    const r = new V(-f.z, 0, f.x);
    const at = (ahead, side) => new V(p.pos.x + f.x * ahead + r.x * side, p.pos.y, p.pos.z + f.z * ahead + r.z * side);
    const eye = p.eye.clone();
    let centre = null;
    for (const ahead of [22, 19, 25, 16]) {
      for (const side of [0, 1.5, -1.5, 3, -3]) {
        const c = at(ahead, side);
        if (!centre && G.physics.nav.isWalkable(c.x, c.z) && G.physics.lineOfSight(eye, new V(c.x, c.y + 1.2, c.z))) centre = { ahead, side };
      }
    }
    if (!centre) return { ok: false };
    const spots = [[0, 0], [1.3, 0.9], [-1.1, 1.2]].map(([a, s]) => at(centre.ahead + a, centre.side + s));
    const list = spots.map((pos) => G.enemies.spawn('goon', pos, { passive: true, yaw: p.yaw + Math.PI }));
    // Look at the middle one's chest.
    const target = new V(spots[0].x, spots[0].y + 1.1, spots[0].z).sub(eye);
    p.yaw = Math.atan2(-target.x, -target.z);
    p.pitch = Math.atan2(target.y, Math.hypot(target.x, target.z));
    window.__kills = [];
    window.__blasts = [];
    G.events.on('enemy:killed', (e) => window.__kills.push(e.weapon));
    G.events.on('explosion', (e) => window.__blasts.push({ radius: e.radius, source: e.source && e.source.type, dist: e.pos.distanceTo(spots[0]) }));
    return { ok: list.every(Boolean), dist: Math.hypot(target.x, target.z) };
  });
  if (!setup.ok) problems.push(`could not stand the targets ${JSON.stringify(setup)}`);

  // Bring the launcher up.
  await h.key('Digit5', true);
  await h.skip(2);
  await h.key('Digit5', false);
  await h.skip(30);
  let w = await h.eval(() => ({ current: window.__G.weapon.current, mag: window.__G.weapon.mag, reserve: window.__G.weapon.reserve, live: window.__G.weapon.rockets.live }));
  if (w.current !== 'rocket' || w.mag !== 1) problems.push(`the launcher is not up and loaded ${JSON.stringify(w)}`);
  await shot('1-ready');

  // Fire.
  await h.key('Mouse0', true);
  await h.skip(1);
  await h.key('Mouse0', false);
  await h.skip(2);
  w = await h.eval(() => ({ mag: window.__G.weapon.mag, live: window.__G.weapon.rockets.live, shots: window.__G.combat.stats.shots }));
  if (w.live !== 1 || w.mag !== 0) problems.push(`no round in the air ${JSON.stringify(w)}`);
  if (w.shots !== 0) problems.push('a rocket was counted as a shot for accuracy');
  await shot('2-away');
  await h.skip(3);
  await shot('3-flight');

  // It lands.
  const flight = Math.ceil((setup.dist / 62) * 30) + 4;
  await h.skip(Math.max(1, flight - 6));
  await shot('4-blast');
  await h.skip(6);
  await shot('5-after');
  const out = await h.eval(() => ({ kills: window.__kills, blasts: window.__blasts, live: window.__G.weapon.rockets.live, alive: window.__G.enemies.aliveCount(), health: window.__G.player.health }));
  if (out.blasts.length !== 1 || out.blasts[0].source !== 'rocket' || out.blasts[0].dist > 2.5) problems.push(`the blast is not where the round was sent ${JSON.stringify(out.blasts)}`);
  if (out.kills.length !== 3 || !out.kills.every((k) => k === 'rocket')) problems.push(`one round should take all three, credited to the launcher: ${JSON.stringify(out.kills)}`);
  if (out.live !== 0) problems.push('the round is still in the air');

  // The kill feed shows the launcher's pictogram; the next round goes in by itself.
  const feed = await h.eval(() => [...document.querySelectorAll('.hud-feed-line')].map((n) => !!n.querySelector('.gl-rocket')));
  if (!feed.length || !feed.every(Boolean)) problems.push(`the kill feed does not show the launcher ${JSON.stringify(feed)}`);
  await h.skip(90);
  w = await h.eval(() => ({ mag: window.__G.weapon.mag, reserve: window.__G.weapon.reserve, state: window.__G.weapon.state }));
  if (w.mag !== 1 || w.reserve !== 2) problems.push(`it did not reload itself ${JSON.stringify(w)}`);

  const errors = await h.errors();
  if (errors.length) problems.push(`errors: ${errors.join(' | ')}`);
  console.error(`[rocket] ${JSON.stringify(out)}`);
  if (problems.length) throw new Error(problems.join('\n'));
};
