// Full house: 12 Goons and 8 Buzzards alive and fighting at once. Measures what enemies.update costs per
// step (mean and worst), how many findPath calls a step makes, the garbage per step, and the draw calls.
//
//   node build.mjs --dev --only=enemies --out=dist/dev-enemies.html
//   node tools/shot.cjs dist/dev-enemies.html --params "autostart=1&q=test&god=1&noaudio=1&nohud=1" \
//        --size 640x360 --scenario tools/scenarios/enemies-perf.cjs --timeout 400

'use strict';

module.exports = async (page, h) => {
  // Baseline: the same 300 steps with no enemies at all.
  await h.eval(() => window.__G.enemies.clear());
  await h.skip(30);
  const base0 = await h.heap(true);
  await h.skip(300);
  const base1 = await h.heap(false);
  await h.eval(() => {
    const G = window.__G;
    const V = G.THREE.Vector3;
    G.enemies.clear();
    const p = G.player.pos;
    for (let i = 0; i < 12; i++) G.enemies.spawn('goon', new V(p.x + 14 + (i % 4) * 3, 0, p.z - 4 + Math.floor(i / 4) * 3), { alerted: true });
    for (let i = 0; i < 8; i++) G.enemies.spawn('buzzard', new V(p.x + 18 + (i % 4) * 2, 4 + (i % 2), p.z - 3 + Math.floor(i / 4) * 5), { alerted: true });
    // Time every enemies.update and count path queries.
    const perf = (window.__perf = { n: 0, sum: 0, max: 0, paths: 0, maxPaths: 0, stepPaths: 0, bytes: 0 });
    const update = G.enemies.update;
    G.enemies.update = (dt) => {
      perf.stepPaths = 0;
      const m0 = performance.memory.usedJSHeapSize;
      const t0 = performance.now();
      update(dt);
      const ms = performance.now() - t0;
      const dm = performance.memory.usedJSHeapSize - m0;
      if (dm > 0 && perf.n > 300) perf.bytes += dm; // allocated inside enemies.update (a GC inside hides some)
      perf.n++;
      perf.sum += ms;
      if (perf.n > 30) perf.max = Math.max(perf.max, ms); // after the first second (shader warm-up, first paths)
      perf.maxPaths = Math.max(perf.maxPaths, perf.stepPaths);
    };
    const find = G.physics.nav.findPath;
    G.physics.nav.findPath = (...args) => {
      perf.paths++;
      perf.stepPaths++;
      return find(...args);
    };
  });
  const count = await h.eval(() => [window.__G.enemies.countByType('goon'), window.__G.enemies.countByType('buzzard')]);
  if (count[0] !== 12 || count[1] !== 8) throw new Error(`spawned ${count}`);
  const extra = await h.eval(() => window.__G.enemies.spawn('goon', window.__G.player.pos.clone()));
  if (extra !== null) throw new Error('a 13th Goon was spawned');
  await h.skip(300);
  const heap0 = await h.heap(true);
  await h.skip(300);
  const heap1 = await h.heap(false);
  const p = await h.eval(() => [window.__G.player.pos.x, window.__G.player.pos.z]);
  await h.eval((c) => window.__setShot({ cam: c, fov: 60 }), `${p[0] - 2},5,${p[1] + 9},${p[0] + 16},1,${p[1]}`);
  await h.frames(2);
  await h.shot('shots/enemies/perf-full-house.png');
  const st = await h.stats();
  const perf = await h.eval(() => window.__perf);
  const alive = await h.eval(() => window.__G.enemies.aliveCount());
  const r = {
    steps: perf.n,
    meanMs: +(perf.sum / perf.n).toFixed(3),
    maxMs: +perf.max.toFixed(2),
    pathsPerStep: +(perf.paths / perf.n).toFixed(2),
    maxPathsInStep: perf.maxPaths,
    heapGrowthKBper300: Math.round((heap1 - heap0) / 1024),
    baselineKBper300: Math.round((base1 - base0) / 1024),
    updateBytesPerStep: Math.round(perf.bytes / Math.max(1, perf.n - 300)),
    calls: st.calls,
    triangles: st.triangles,
    alive,
  };
  console.log(JSON.stringify(r));
  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
  if (r.maxPathsInStep > 2) throw new Error(`${r.maxPathsInStep} path queries in one step`);
};
