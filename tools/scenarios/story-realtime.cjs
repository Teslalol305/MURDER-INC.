// The story on the page's own clock (no stepping): the title, the opening cutscene watched for a few
// seconds and then skipped, the first level walked along the guide line, a burst fired down the sights.
// It says how many frames a second each part ran at and fails on any page error, a clock that did not
// move, or a scene that could not be skipped.
//
//   node build.mjs --out=dist/dev-prod.html
//   SHOT_GPU=1 node tools/shot.cjs dist/dev-prod.html --realtime --size 1280x720 --params "god=1" \
//        --scenario tools/scenarios/story-realtime.cjs --timeout 300
//   RT_MIN_FPS=20 (default 0: report only) fails a part that ran slower.

module.exports = async (page, h) => {
  const minFps = Number(process.env.RT_MIN_FPS || 0);
  const problems = [];
  const check = (name, ok, detail) => {
    console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}${detail === undefined ? '' : ' ' + JSON.stringify(detail)}`);
    if (!ok) problems.push(name);
  };
  const snap = () =>
    h.eval(() => {
      const G = window.__G;
      const g = G.game;
      return {
        state: g.state,
        scene: g.flow.scene || null,
        sceneTime: g.flow.sceneTime || 0,
        level: g.run.level,
        time: g.run.time,
        frames: window.__frames,
        pos: [G.player.pos.x, G.player.pos.z],
        guide: g.guide.shown,
        shots: G.combat.stats.shots,
        gun: `${G.weapon.current}:${G.weapon.mag}/${G.weapon.reserve}`,
        locked: document.pointerLockElement ? document.pointerLockElement.id || document.pointerLockElement.tagName : null,
      };
    });
  /** Frames a second over a real-time stretch. */
  const timed = async (ms) => {
    const a = await h.eval(() => window.__frames);
    const t0 = Date.now();
    await h.wait(ms);
    const b = await h.eval(() => window.__frames);
    return Math.round(((b - a) * 1000) / (Date.now() - t0));
  };
  const fpsOk = (name, fps) => check(`${name}: ${fps} frames a second`, fps > 0 && fps >= minFps, { fps, min: minFps });

  await page.mouse.move(640, 360);
  let s = await snap();
  check('the page boots to the title', s.state === 'title', s.state);
  fpsOk('title', await timed(1500));

  await h.click('.title-actions .btn-primary');
  await h.wait(400);
  s = await snap();
  check('Story opens on the opening cutscene', s.state === 'cutscene' && s.scene === 'opening', { state: s.state, scene: s.scene });
  const t0 = s.sceneTime;
  fpsOk('cutscene', await timed(3000));
  s = await snap();
  check('the cutscene runs on the real clock', s.state === 'cutscene' && s.sceneTime - t0 > 2 && s.sceneTime - t0 < 4, { ran: +(s.sceneTime - t0).toFixed(2) });

  await page.keyboard.press('Enter');
  await h.wait(1500);
  s = await snap();
  check('Enter skips it into level 1', (s.state === 'intro' || s.state === 'playing') && s.level === 1, { state: s.state, level: s.level });
  await page.waitForFunction(() => window.__G.game.state === 'playing', null, { timeout: 20000 }).catch(() => {});
  s = await snap();
  check('the level starts by itself', s.state === 'playing', s.state);
  check('skipping did not fire a round', s.shots === 0, s.shots);

  const from = s.pos;
  await page.keyboard.down('KeyW');
  fpsOk('walking', await timed(2500));
  await page.keyboard.up('KeyW');
  s = await snap();
  const moved = Math.hypot(s.pos[0] - from[0], s.pos[1] - from[1]);
  check('Rule walks and the guide line is out', moved > 4 && s.guide, { moved: +moved.toFixed(1), guide: s.guide });

  await page.mouse.down({ button: 'right' });
  await h.wait(350);
  await page.mouse.down({ button: 'left' });
  fpsOk('firing down the sights', await timed(1200));
  // A busy machine can swallow most of a second: the trigger stays down until the rounds are out.
  await page.waitForFunction(() => window.__G.combat.stats.shots > 3, null, { timeout: 8000 }).catch(() => {});
  await page.mouse.up({ button: 'left' });
  await page.mouse.up({ button: 'right' });
  s = await snap();
  check('the trigger works', s.shots > 3, { shots: s.shots, gun: s.gun, pointer: s.locked, state: s.state });
  check('the run clock moved', s.time > 3, +s.time.toFixed(1));

  const errors = await h.errors();
  check('no page errors', errors.length === 0, errors.slice(0, 3));
  await h.shot('shots/story/realtime.png');
  if (problems.length) throw new Error(`story-realtime: ${problems.length} failed: ${problems.join('; ')}`);
};
