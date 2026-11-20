// Aim assist in play: a Goon and a Buzzard off the crosshair, the aim button held, the sights lock on
// and a burst lands. Checks the lock (weapon.lock) and takes the pictures the HUD brackets are judged by.
//
//   node build.mjs --dev --out=dist/dev-all.html
//   node tools/shot.cjs dist/dev-all.html --size 960x540 --params "autostart=1&q=medium&god=1&noaudio=1" \
//        --scenario tools/scenarios/weapon-assist.cjs

module.exports = async (page, h) => {
  const problems = [];
  const shot = async (name) => {
    if (process.env.ASSIST_NOSHOTS) return;
    await h.frames(1);
    await h.shot(`shots/weapon/assist-${name}.png`);
  };
  // The pointer rests on the middle of the view: the harness presses buttons there, and under pointer
  // lock a pointer that had to travel first would turn Rule's head.
  const port = page.viewportSize() || { width: 960, height: 540 };
  await page.mouse.move(port.width / 2, port.height / 2);
  await h.skip(100); // past the intro
  // Clear the block, then stand two passive Vultures a little off the aim: one on the street, one in the air.
  const setup = await h.eval(() => {
    const G = window.__G;
    const V = G.THREE.Vector3;
    G.enemies.clear();
    const p = G.player;
    const f = new V(p.forward.x, 0, p.forward.z).normalize();
    const r = new V(-f.z, 0, f.x);
    const at = (ahead, side, up) => new V(p.pos.x + f.x * ahead + r.x * side, p.pos.y + up, p.pos.z + f.z * ahead + r.z * side);
    // Wherever the level put Rule down: the first spot ahead that is open ground in plain view, a little
    // off the aim to one side; the Buzzard well off it to the other.
    const eye = p.eye.clone();
    const open = (pos, lift) => G.physics.lineOfSight(eye, new V(pos.x, pos.y + lift, pos.z));
    let ground = null;
    let side = 0;
    for (const ahead of [14, 12, 16, 10, 18]) {
      for (const s of [2.2, -2.2, 1.4, -1.4, 3, -3]) {
        const c = at(ahead, s, 0);
        if (!ground && G.physics.nav.isWalkable(c.x, c.z) && open(c, 1.3) && open(c, 0.4)) {
          ground = c;
          side = s;
        }
      }
    }
    let air = null;
    for (const ahead of [20, 17, 23, 14, 26]) {
      for (const s of side > 0 ? [-5, -7, -3.5, 6, 8] : [5, 7, 3.5, -6, -8]) {
        for (const up of [5.5, 4.5, 3.5, 2.8]) {
          const c = at(ahead, s, up);
          if (!air && open(c, 0) && !G.physics.overlapsCylinder(c.x, c.z, 0.8, c.y - 0.6, c.y + 0.6)) air = c;
        }
      }
    }
    const goon = ground ? G.enemies.spawn('goon', ground, { passive: true, yaw: p.yaw + Math.PI }) : null;
    const buzzard = air ? G.enemies.spawn('buzzard', air, { passive: true }) : null;
    return { goon: !!goon, buzzard: !!buzzard, hp: goon ? goon.hp : 0 };
  });
  if (!setup.goon || !setup.buzzard) problems.push(`could not spawn the targets ${JSON.stringify(setup)}`);
  await h.skip(10);
  await shot('1-before');

  const lock = () => h.eval(() => {
    const G = window.__G;
    const L = G.weapon.lock;
    const p = G.player;
    let off = -1;
    if (L.on) {
      const to = L.point.clone().sub(p.eye).normalize();
      off = Math.acos(Math.min(1, to.dot(p.forward)));
    }
    return { on: L.on, type: L.enemy ? L.enemy.type : '', off, ads: p.ads, alive: G.enemies.aliveCount(), shots: G.combat.stats.shots, hits: G.combat.stats.hits };
  });

  // Aim: the lock is taken at once and the view is on the Goon within a third of a second.
  await h.key('Mouse2', true);
  await h.skip(2);
  let now = await lock();
  if (!now.on || now.type !== 'goon') problems.push(`no lock on the Goon two frames into the aim: ${JSON.stringify(now)}`);
  await h.skip(12);
  now = await lock();
  if (!(now.off >= 0 && now.off < 0.01)) problems.push(`not on target after 0.45 s: ${JSON.stringify(now)}`);
  await shot('2-locked');

  // A held burst: the lock takes the climb out and every round lands until the Goon drops…
  await h.key('Mouse0', true);
  for (let i = 0; i < 90; i++) {
    await h.skip(1);
    now = await lock();
    if (i === 4) await shot('3-burst');
    if (now.alive < 2) break;
  }
  await h.key('Mouse0', false);
  if (now.alive !== 1) problems.push(`the Goon is still standing: ${JSON.stringify(now)}`);
  const accuracy = now.shots > 0 ? now.hits / now.shots : 0;
  if (!(accuracy >= 0.99)) problems.push(`a locked burst should land: ${now.hits} of ${now.shots}`);
  // …then the lock passes to the Buzzard, a good way off the aim, without the button being let go.
  let passed = false;
  for (let i = 0; i < 30 && !passed; i++) {
    await h.skip(1);
    now = await lock();
    passed = now.on && now.type === 'buzzard' && now.off < 0.02;
  }
  if (!passed) problems.push(`the lock never passed to the Buzzard: ${JSON.stringify(now)}`);
  await shot('4-passed');

  // Letting the aim button go ends the lock.
  await h.key('Mouse2', false);
  await h.skip(3);
  now = await lock();
  if (now.on) problems.push('still locked with the aim button up');

  // Switched off in the settings: aiming turns nothing.
  await h.eval(() => window.__G.settings.set('aimAssist', false));
  const before = await h.eval(() => window.__G.player.yaw);
  await h.key('Mouse2', true);
  await h.skip(15);
  now = await lock();
  const after = await h.eval(() => window.__G.player.yaw);
  await h.key('Mouse2', false);
  await h.eval(() => window.__G.settings.set('aimAssist', true));
  if (now.on || Math.abs(after - before) > 1e-6) problems.push('the setting did not switch the lock off');

  const errors = await h.errors();
  if (errors.length) problems.push(`errors: ${errors.join(' | ')}`);
  console.error(`[assist] accuracy ${(accuracy * 100).toFixed(0)} % (${now.hits}/${now.shots})`);
  if (problems.length) throw new Error(problems.join('\n'));
};
