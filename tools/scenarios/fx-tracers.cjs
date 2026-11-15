// Tracers across the avenue (player warm white-gold, enemy red), muzzle flashes in the world and on the
// viewmodel, and ejected brass.
//
//   node build.mjs --dev --only=fx,explosives --out=dist/dev-fx.html
//   node tools/shot.cjs dist/dev-fx.html --params "autostart=1&q=low&god=1&nohud=1" --scenario tools/scenarios/fx-tracers.cjs --timeout 300

const OUT = 'shots/fx';

module.exports = async (page, h) => {
  const stats = () => h.eval(() => window.__G.fx.stats());

  // ---- 1. Seen from the south sidewalk: a firefight along the avenue --------------------------------
  await h.eval(() => {
    const G = window.__G;
    G.enemies.clear();
    G.fx.clear();
    window.__setShot({ cam: '-27,2.6,9.2,-6,1.2,-1.5', fov: 62 });
    const V = (x, y, z) => new G.THREE.Vector3(x, y, z);
    // One volley per step for a few steps, so streaks are caught at different points of their flight.
    window.__volley = (n) => {
      const west = V(-24 + n * 0.7, 1.45, 2.2 - n * 0.5);
      const east = V(12 - n, 1.5 + n * 0.1, -3 + n * 0.9);
      G.fx.tracer(west, east, G.config.look.palette.tracerPlayer, 260);
      G.fx.muzzleFlash(west, east.clone().sub(west).normalize(), 1, true);
      const from = V(14 - n * 1.3, 1.4, 3.5 - n);
      const to = V(-20 + n * 2, 1.0 + n * 0.15, -2 + n * 0.4);
      G.fx.tracer(from, to, G.config.look.palette.tracerEnemy, 260);
      G.fx.muzzleFlash(from, to.clone().sub(from).normalize(), 0.8, true);
    };
  });
  for (let n = 0; n < 4; n++) {
    await h.eval((i) => window.__volley(i), n);
    await h.frames(1);
    if (n === 1 || n === 3) await h.shot(`${OUT}/tracers-avenue-${n}.png`);
  }
  const mid = await stats();
  if (mid.tracers < 4) throw new Error(`tracers should still be in flight: ${JSON.stringify(mid)}`);
  await h.skip(40);
  const done = await stats();
  if (done.tracers !== 0) throw new Error(`tracers never arrived: ${done.tracers}`);

  // ---- 2. First person: the stub Chopper firing, flash on the viewmodel, brass out of the port -------
  await h.eval(() => {
    const G = window.__G;
    window.__setShot({ cam: '' });
    G.fx.clear();
    window.__bounces = [];
    G.events.on('shell:bounce', (e) => window.__bounces.push([e.pos.x, e.pos.y, e.pos.z, e.surface]));
    G.events.on('weapon:fire', (e) => {
      G.fx.muzzleFlash(e.pos, e.dir, 1, false);
      const p = G.player;
      const right = new G.THREE.Vector3().crossVectors(p.forward, new G.THREE.Vector3(0, 1, 0)).normalize();
      const port = e.pos.clone().addScaledVector(p.forward, -0.25);
      const vel = right.multiplyScalar(2.4 + Math.random()).add(new G.THREE.Vector3(0, 1.5, 0));
      G.fx.shell(port, vel, 'rifle');
    });
  });
  await page.mouse.move(480, 270);
  await h.key('Mouse0', true);
  await h.frames(3);
  await h.shot(`${OUT}/tracers-firstperson-a.png`);
  await h.frames(4);
  await h.shot(`${OUT}/tracers-firstperson-b.png`);
  await h.key('Mouse0', false);
  const firing = await stats();
  if (firing.shells < 3) throw new Error(`no brass in the air: ${JSON.stringify(firing)}`);

  // ---- 3. The brass a second later, on the pavement ---------------------------------------------------
  await h.skip(60);
  const b = await h.eval(() => ({ bounces: window.__bounces, shots: window.__G.combat.stats.shots, shells: window.__G.fx.stats().shells }));
  if (b.bounces.length < Math.min(b.shots, 3)) throw new Error(`shell:bounce fired ${b.bounces.length} times for ${b.shots} shots`);
  if (b.bounces.some((p) => typeof p[3] !== 'string')) throw new Error('shell:bounce without a surface');
  if (b.shells < b.bounces.length) throw new Error(`brass vanished: ${b.shells} shells for ${b.bounces.length} bounces`);
  // Look at where it came down.
  const cx = b.bounces.reduce((sum, p) => sum + p[0], 0) / b.bounces.length;
  const cz = b.bounces.reduce((sum, p) => sum + p[2], 0) / b.bounces.length;
  await h.eval(([x, z]) => window.__setShot({ cam: `${x - 1.1},0.55,${z - 0.9},${x + 0.2},0,${z + 0.2}`, fov: 45 }), [cx, cz]);
  await h.frames(1);
  await h.shot(`${OUT}/shells-ground.png`);
  console.error(`brass: ${b.shots} shots, ${b.bounces.length} first bounces on ${[...new Set(b.bounces.map((p) => p[3]))].join(', ')}`);

  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
};
