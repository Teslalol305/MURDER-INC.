// Stress: three explosions at once in the middle of sustained fire, twice, while watching fx.stats(),
// the cost of fx.update, draw calls, and the garbage a step of pure effects leaves behind.
//
//   node build.mjs --dev --only=fx,explosives --out=dist/dev-fx.html
//   node tools/shot.cjs dist/dev-fx.html --params "autostart=1&q=low&god=1&nohud=1" --scenario tools/scenarios/fx-stress.cjs --timeout 500
//   (… "q=high" for full budgets)
//
// Fails when a pool overruns its budget, when the update gets slow, when the effects draw more than their
// seven calls, or when a step of effects allocates more than a few boxed numbers.

'use strict';

const OUT = 'shots/fx';
const CAM = '-30,3.4,8.6,-12,1.2,-0.5';
const MAX_UPDATE_MS = 1.5; // mean cost of fx.update over the run, on a core shared with other jobs
const MAX_GARBAGE = 2048; // bytes per step of sustained fire through fx alone (12 rounds a second)

/** Runs in the page: n undrawn steps; returns heap growth per step since a forced collection. */
function measure(n) {
  return new Promise((resolve) => {
    if (typeof window.gc === 'function') window.gc();
    const before = performance.memory.usedJSHeapSize;
    window.__skip = n;
    const poll = () => {
      if (window.__skip > 0) requestAnimationFrame(poll);
      else resolve((performance.memory.usedJSHeapSize - before) / n);
    };
    requestAnimationFrame(poll);
  });
}

module.exports = async (page, h) => {
  // ---- set the stage: a driver that fires every step, wrapped around fx.update -----------------------
  await h.eval((cam) => {
    const G = window.__G;
    const V = (x, y, z) => new G.THREE.Vector3(x, y, z);
    G.enemies.clear();
    G.fx.clear();
    window.__setShot({ cam, fov: 62 });

    const load = (window.__load = {
      mode: 'off', // 'combat': rounds go through G.combat (impact events); 'fx': effects called directly
      peak: { lit: 0, additive: 0, debris: 0, tracers: 0, shells: 0, decals: 0, emitters: 0, ms: 0 },
      sumMs: 0,
      steps: 0,
      over: [],
    });
    const gun = V(-26, 1.45, 3.2);
    const port = V(-26.1, 1.4, 3.3);
    const brass = V(1.6, 1.4, 2.4);
    const aim = V();
    const dir = V();
    const hitPoint = V();
    const up = V(0, 1, 0);
    const goons = [V(4, 1.4, -3), V(8, 1.4, 4.5), V(-2, 1.4, 6)].map((pos) => ({ type: 'goon', pos }));
    const surfaces = ['asphalt', 'metal', 'brick', 'car', 'concrete', 'glass', 'wood'];
    let cool = 0;
    let n = 0;

    function fire(dt) {
      cool -= dt;
      while (cool <= 0) {
        cool += 60 / 720; // the Chopper's rate of fire
        n++;
        // The player sprays the avenue; three Goons answer in turn.
        aim.set(-8 + ((n * 7) % 19), 0.2 + ((n * 3) % 5) * 0.5, -4 + ((n * 5) % 9));
        dir.subVectors(aim, gun).normalize();
        if (load.mode === 'combat') {
          const res = G.combat.hitscan({ origin: gun, dir, range: 120, damage: 26, from: 'player', weapon: 'chopper' });
          G.fx.tracer(gun, res.point);
          const goon = goons[n % 3];
          aim.set(-27 + (n % 4), 0.3 + (n % 3), 1 + (n % 5));
          dir.subVectors(aim, goon.pos).normalize();
          const back = G.combat.hitscan({ origin: goon.pos, dir, range: 120, damage: 6, from: goon, weapon: 'goon' });
          G.fx.tracer(goon.pos, back.point, G.config.look.palette.tracerEnemy);
          G.fx.muzzleFlash(goon.pos, dir, 0.8, true);
        } else {
          hitPoint.copy(gun).addScaledVector(dir, 22);
          G.fx.tracer(gun, hitPoint);
          G.fx.impact(hitPoint, up, surfaces[n % surfaces.length], dir);
        }
        G.fx.muzzleFlash(gun, dir, 1, true);
        G.fx.shell(port, brass, 'rifle');
      }
    }

    const update = G.fx.update;
    G.fx.update = (dt) => {
      if (load.mode !== 'off') fire(dt);
      update(dt);
      if (load.mode !== 'combat') return; // stats() allocates: keep it out of the garbage measurement
      const s = G.fx.stats();
      for (const key of Object.keys(load.peak)) if (s[key] > load.peak[key]) load.peak[key] = s[key];
      for (const key of ['lit', 'additive', 'debris', 'tracers', 'shells', 'decals', 'emitters']) {
        if (s[key] > s.budget[key] && !load.over.includes(key)) load.over.push(key);
      }
      load.sumMs += s.ms;
      load.steps++;
    };
    window.__blasts = (sites) => {
      for (const [x, z, scale] of sites) G.fx.explosion(V(x, 0.3, z), scale);
    };
  }, CAM);

  // ---- quiet baseline -----------------------------------------------------------------------------
  await h.frames(2);
  const t0 = Date.now();
  await h.frames(6);
  const quietFrame = (Date.now() - t0) / 6;
  const quietCalls = (await h.stats()).calls;

  // ---- sustained fire, then three explosions at once, twice ----------------------------------------
  await h.eval(() => (window.__load.mode = 'combat'));
  await h.skip(20);
  await h.frames(1);
  await h.shot(`${OUT}/stress-0-firefight.png`);

  await h.eval(() => window.__blasts([[-14, 1.5, 1], [-9, -2.5, 1.2], [-18, -1, 0.8]]));
  await h.frames(2);
  await h.shot(`${OUT}/stress-1-blasts.png`);
  const t1 = Date.now();
  await h.frames(8);
  const busyFrame = (Date.now() - t1) / 8;
  const busyCalls = (await h.stats()).calls;
  // What the effects themselves draw right now: every visible mesh of theirs is one call.
  const ownCalls = await h.eval(() => {
    const G = window.__G;
    const meshes = [...G.scene.getObjectByName('fx').children, ...G.vmCamera.children.filter((c) => c.name.startsWith('fx-'))];
    return meshes.filter((m) => m.visible).length;
  });
  await h.shot(`${OUT}/stress-2-fireballs.png`);
  await h.skip(40);
  await h.eval(() => window.__blasts([[-12, 3, 1.1], [-6, 0, 1], [-20, 2, 1.3]]));
  await h.skip(12);
  await h.frames(1);
  await h.shot(`${OUT}/stress-3-second-wave.png`);
  await h.skip(60);
  await h.frames(1);
  await h.shot(`${OUT}/stress-4-smoke.png`);

  const load = await h.eval(() => window.__load);
  const fx = await h.eval(() => window.__G.fx.stats());

  // ---- garbage: the same fire through fx alone, measured over undrawn steps ---------------------------
  // The rest of the page (render, physics, stubs) makes garbage of its own: measured without fire first,
  // and only what the effects add on top counts.
  await h.eval(() => (window.__load.mode = 'off'));
  await h.skip(450);
  const quiet = [];
  for (const n of [60, 120, 240]) quiet.push(await h.eval(measure, n));
  const baseline = quiet.filter((b) => b >= 0).sort((a, b) => a - b)[0] || 0;
  await h.eval(() => (window.__load.mode = 'fx'));
  await h.skip(200); // warm: every code path compiled, pools at their working size
  const perStep = [];
  for (const n of [60, 120, 240]) perStep.push(await h.eval(measure, n));
  const busy = perStep.filter((b) => b >= 0).sort((a, b) => a - b)[0];
  const garbage = busy === undefined ? undefined : Math.max(0, busy - baseline);

  // ---- everything stops: the block is clean again ---------------------------------------------------
  await h.eval(() => (window.__load.mode = 'off'));
  await h.skip(450);
  const rest = await h.eval(() => window.__G.fx.stats());

  const rows = [
    ['quality', `${fx.quality} (budgets: lit ${fx.budget.lit}, additive ${fx.budget.additive})`],
    ['peak particles', `lit ${load.peak.lit}, additive ${load.peak.additive}`],
    ['peak others', `debris ${load.peak.debris}, tracers ${load.peak.tracers}, shells ${load.peak.shells}, decals ${load.peak.decals}, emitters ${load.peak.emitters}`],
    ['spawned / recycled / refused', `${fx.spawned} / ${fx.recycled} / ${fx.refused}`],
    ['fx.update', `mean ${(load.sumMs / load.steps).toFixed(3)} ms, worst ${load.peak.ms.toFixed(2)} ms over ${load.steps} steps`],
    ['draw calls', `${ownCalls} by the effects at the peak (scene: ${quietCalls} quiet, ${busyCalls} busy)`],
    ['drawn frame (software GL)', `${quietFrame.toFixed(0)} ms quiet → ${busyFrame.toFixed(0)} ms with three fireballs on screen`],
    ['garbage per step of effects', garbage === undefined ? 'unreadable' : `${Math.round(garbage)} B (page without fire: ${Math.round(baseline)} B)`],
    ['after 15 s of quiet', `lit ${rest.lit}, additive ${rest.additive}, debris ${rest.debris}, emitters ${rest.emitters}`],
  ];
  const width = Math.max(...rows.map((r) => r[0].length));
  console.error(rows.map(([a, b]) => `  ${a.padEnd(width)}  ${b}`).join('\n'));

  const problems = [];
  if (load.over.length) problems.push(`over budget: ${load.over.join(', ')}`);
  if (load.peak.lit < 40 || load.peak.additive < 150) problems.push('the stress case never got busy');
  if (load.sumMs / load.steps > MAX_UPDATE_MS) problems.push(`fx.update takes ${(load.sumMs / load.steps).toFixed(2)} ms on average`);
  if (ownCalls > 7) problems.push(`the effects draw ${ownCalls} calls`);
  if (garbage !== undefined && garbage > MAX_GARBAGE) problems.push(`a step of effects leaves ${Math.round(garbage)} bytes of garbage`);
  if (rest.lit + rest.additive + rest.debris + rest.tracers + rest.emitters !== 0) problems.push(`something never ended: ${JSON.stringify(rest)}`);
  const errors = await h.errors();
  if (errors.length) problems.push(`page errors: ${errors[0]}`);
  if (problems.length) throw new Error(problems.join('; '));
};
