// Performance sanity of the loop: draw calls and triangles, what one simulation step costs, how much
// garbage a frame leaves behind, and whether the nav grid is left alone. Run it on a production build:
//
//   node build.mjs --out=dist/dev-foundation-perf.html
//   node tools/shot.cjs dist/dev-foundation-perf.html --params "autostart=1&q=low&god=1" \
//        --scenario tools/scenarios/foundation-perf.cjs
//
// It prints a table and fails on the things that must never happen: the nav grid rebuilt during play, or
// a quiet frame that allocates kilobytes. The millisecond figures of DRAWN frames are software-GL numbers
// (SwiftShader) and say nothing about a real GPU; the simulation and allocation figures do carry over.
// Works with any mix of real and stubbed modules; with real modules the numbers are theirs.

'use strict';

const SKIP_BUDGET_MS = 12; // src/main.js: time per animation frame spent on undrawn steps
const QUIET_LIMIT = 4096; // bytes of garbage per simulation step tolerated with nothing going on

/**
 * Runs in the page: advances `n` undrawn steps and resolves with what happened meanwhile.
 * Garbage is read as heap growth since a forced collection, so `n` must be small enough that no
 * collection happens on the way (the caller tries several sizes and keeps the consistent ones).
 */
function measure(n) {
  return new Promise((resolve) => {
    if (typeof window.gc === 'function') window.gc();
    const nav = window.__G.physics.nav;
    const before = { heap: performance.memory.usedJSHeapSize, rebuilds: nav.rebuilds, t: performance.now() };
    let rafs = 0;
    window.__skip = n;
    const poll = () => {
      rafs++;
      if (window.__skip > 0) {
        requestAnimationFrame(poll);
        return;
      }
      resolve({
        steps: n,
        bytes: performance.memory.usedJSHeapSize - before.heap,
        rebuilds: nav.rebuilds - before.rebuilds,
        ms: performance.now() - before.t,
        rafs,
      });
    };
    requestAnimationFrame(poll);
  });
}

module.exports = async (page, h) => {
  const rows = [];
  const row = (what, value) => rows.push([what, value]);
  const problems = [];
  const kb = (n) => `${(n / 1024).toFixed(2)} kB`;

  /** Garbage per step: the median over a few batch sizes, ignoring batches a collection cut into. */
  async function garbage(label, sizes = [200, 400, 800]) {
    const perStep = [];
    let rebuilds = 0;
    for (const n of sizes) {
      const m = await h.eval(measure, n);
      rebuilds += m.rebuilds;
      if (m.bytes >= 0) perStep.push(m.bytes / n);
    }
    perStep.sort((a, b) => a - b);
    const typical = perStep.length ? perStep[Math.floor(perStep.length / 2)] : NaN;
    row(`garbage per step, ${label}`, Number.isFinite(typical) ? `${Math.round(typical)} B` : 'unreadable (collections in every batch)');
    return { typical, rebuilds };
  }

  /** Cost of one undrawn step: the skip loop runs steps for 12 ms per animation frame. */
  async function stepCost(label) {
    const m = await h.eval(measure, 60000);
    // The first and last animation frames are partial: count the full ones only when there are enough.
    const ms = m.rafs > 3 ? ((m.rafs - 1) * SKIP_BUDGET_MS) / m.steps : m.ms / m.steps;
    row(`simulation step, ${label}`, `${(ms * 1000).toFixed(1)} µs  (${Math.round(1 / ms)} steps per ms)`);
    return ms;
  }

  // ---- the picture: what a frame draws ----------------------------------------------------------

  await h.frames(2);
  let s = await h.stats();
  row('build', `${s.stubbed.length ? `${s.stubbed.length} stubbed (${s.stubbed.join(', ')})` : 'no stubs'}, quality ${s.quality}, ${s.width}×${s.height}, msaa ${s.msaa}, shadow map ${s.shadow}`);
  row('first-person view at the start', `${s.calls} draw calls, ${s.triangles} triangles (${s.frameCalls} calls with post)`);
  const overview = await h.eval(() => {
    const b = window.__G.level.bounds;
    return `${(b.minX + b.maxX) / 2},95,${(b.minZ + b.maxZ) / 2 + 40},${(b.minX + b.maxX) / 2},0,${(b.minZ + b.maxZ) / 2}`;
  });
  await h.eval((cam) => window.__setShot({ cam, fov: 60 }), overview);
  await h.frames(2);
  s = await h.stats();
  row('whole block in view (overview camera)', `${s.calls} draw calls, ${s.triangles} triangles`);
  row('GPU objects', `${s.geometries} geometries, ${s.textures} textures, ${s.programs} shader programs`);
  await h.shot('shots/foundation/perf-overview.png');
  await h.eval(() => window.__setShot({ cam: '', fov: '' }));

  // Software GL delivers frames in bursts (some in 20 ms, some in half a second): average over a few dozen.
  const t0 = Date.now();
  await h.frames(30);
  row('drawn frame (software GL, step mode)', `${Math.round((Date.now() - t0) / 30)} ms on average`);

  // ---- the simulation: cost and garbage ---------------------------------------------------------

  const quietCost = await stepCost('patrol out, nobody shooting');
  // From here on the code is warm: what the heap gains now is kept data, not compiled code.
  const heapBefore = await h.heap(true);
  const stepsBefore = await h.eval(() => window.__frames);
  const quiet = await garbage('patrol out, nobody shooting');

  // A firefight: eight alerted enemies in sight of an invulnerable player who never stops firing.
  await h.eval(() => {
    const G = window.__G;
    const p = G.player.pos;
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * Math.PI * 2;
      const type = i % 2 ? 'buzzard' : 'goon';
      G.enemies.spawn(type, new G.THREE.Vector3(p.x + Math.cos(a) * 9, type === 'goon' ? 0 : 5, p.z + Math.sin(a) * 9), { alerted: true });
    }
    G.events.on('weapon:fire', () => {
      if (G.weapon.mag < 5) G.weapon.mag = G.weapon.magSize; // bottomless magazine for the measurement
    });
  });
  const view = page.viewportSize();
  await page.mouse.move(view.width / 2, view.height / 2);
  await h.key('Mouse0', true);
  await h.skip(30);
  const fightCost = await stepCost('firefight');
  const fight = await garbage('firefight (12 rounds a second out, 8 enemies shooting back)', [100, 200, 400]);
  await h.key('Mouse0', false);
  const shots = await h.eval(() => window.__G.combat.stats.shots);
  row('rounds fired meanwhile', String(shots));

  await h.eval(() => {
    window.__G.enemies.clear();
    window.__G.fx.clear();
  });
  await h.skip(200); // bodies gone, tracers faded
  const kept = (await h.heap(true)) - heapBefore;
  const steps = (await h.eval(() => window.__frames)) - stepsBefore;
  row('heap growth', `${kb(kept)} over ${steps} steps (${(kept / steps).toFixed(2)} B per step; a leak is tens of bytes per step or more)`);
  if (kept / steps > 64) problems.push(`the heap grew by ${kb(kept)} in ${steps} steps: something is kept that should not be`);

  // ---- navigation -------------------------------------------------------------------------------

  const nav = await h.eval(() => {
    const G = window.__G;
    const nav = G.physics.nav;
    const from = G.level.playerStart.pos;
    const goals = [...G.level.objectives.map((o) => o.pos), G.level.extraction.pos];
    let t = performance.now();
    let found = 0;
    for (let i = 0; i < 200; i++) if (nav.findPath(from, goals[i % goals.length])) found++;
    const path = (performance.now() - t) / 200;
    const before = nav.rebuilds;
    t = performance.now();
    for (let i = 0; i < 20; i++) nav.rebuild();
    const rebuild = (performance.now() - t) / 20;
    return { path, rebuild, found, cells: nav.cols * nav.rows, boxes: G.physics.boxes.length, total: before };
  });
  row('nav grid', `${nav.cells} cells from ${nav.boxes} colliders; one rebuild ${nav.rebuild.toFixed(2)} ms; findPath ${nav.path.toFixed(3)} ms on average`);
  row('nav rebuilds', `${nav.total} since boot, ${quiet.rebuilds + fight.rebuilds} during the measured play`);

  // ---- verdict ----------------------------------------------------------------------------------

  if (quiet.rebuilds + fight.rebuilds > 0) problems.push('the nav grid was rebuilt during play: something adds or removes colliders every frame');
  if (quiet.typical > QUIET_LIMIT) problems.push(`a quiet simulation step leaves ${kb(quiet.typical)} of garbage (limit ${kb(QUIET_LIMIT)})`);
  if (nav.found !== 200) problems.push('findPath failed between the start and an objective');
  if (!(quietCost < 2 && fightCost < 2)) problems.push('a simulation step takes more than 2 ms');
  const errors = await h.errors();
  if (errors.length) problems.push(`page errors: ${errors[0]}`);

  const width = Math.max(...rows.map(([what]) => what.length));
  console.log(rows.map(([what, value]) => `${what.padEnd(width)}  ${value}`).join('\n'));
  if (problems.length) throw new Error(problems.join('; '));
};
