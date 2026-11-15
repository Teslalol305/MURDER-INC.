// Example scenario: every harness helper in one short run. Copy it as tools/scenarios/<you>-<what>.cjs.
//
//   node build.mjs --dev --out=dist/dev-foundation.html
//   node tools/shot.cjs dist/dev-foundation.html --params "autostart=1&q=test&god=1" --scenario tools/scenarios/foundation-example.cjs
//
// The page runs with step=1&dt=0.0333: nothing moves between h.frames() / h.skip() calls, so the run is
// the same every time. `page` is the Playwright page for anything the helpers do not cover.

const OUT = 'shots/foundation';

module.exports = async (page, h) => {
  // The run has started (autostart=1). Let two frames pass so the first input is seen.
  await h.frames(2);
  await h.shot(`${OUT}/example-1-start.png`);

  // Walk east for a second and a half: hold W, advance 45 frames, release.
  await h.key('KeyW', true);
  await h.frames(45);
  await h.key('KeyW', false);

  // Look: positive dx turns right, positive dy looks down (pixels of mouse travel).
  await h.mouse(-380, 30);
  await h.frames(2);

  // Fire a burst: hold the left mouse button for 12 frames.
  await h.key('Mouse0', true);
  await h.frames(12);
  await h.shot(`${OUT}/example-2-firing.png`); // taken mid-burst so the tracers are in frame
  await h.key('Mouse0', false);

  // Run code in the page: anything on window.__G is reachable. Return values must be serialisable.
  const ammo = await h.eval(() => ({ mag: window.__G.weapon.mag, shots: window.__G.combat.stats.shots }));
  if (ammo.shots === 0) throw new Error('holding fire did not shoot');

  // Fast-forward ten seconds of simulation without drawing, then look again.
  await h.skip(300);
  await h.frames(1);
  await h.shot(`${OUT}/example-3-later.png`);

  // Debug hooks: a fixed outside camera (releases with cam: '').
  await h.eval(() => window.__setShot({ cam: '-10,17,28,-4,1,-3', fov: 60 }));
  await h.frames(1);
  await h.shot(`${OUT}/example-4-overview.png`);

  // Fail the run on anything the page reported (the harness also does this on its own at the end).
  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
  const stats = await h.stats();
  console.error(`example: ${stats.state}, t = ${stats.t} s, ${stats.calls} draw calls, ${ammo.shots} shots fired`);
};
