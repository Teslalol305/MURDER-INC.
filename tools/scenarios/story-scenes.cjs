// Every cutscene of the story, a picture from each of its shots and one of its title card, for looking
// over the camera work. The levels between them are played by the director (the reel taken at once, the
// Vultures put down as they come).
//
//   node tools/shot.cjs dist/dev-all.html --size 1280x720 --params "q=high&noaudio=1&god=1" \
//        --scenario tools/scenarios/story-scenes.cjs --timeout 900
//   Pictures: shots/scenes/<scene>-<n>.png and shots/scenes/<scene>-card.png (SCENES_OUT names the folder).

const { setup } = require('./flow-lib.cjs');

module.exports = async (page, h) => {
  const { snap, until } = await setup(page, h);
  const out = process.env.SCENES_OUT || 'shots/scenes';
  const scenes = await h.eval(() => {
    const S = window.__G.config.story;
    return Object.fromEntries(Object.entries(S.scenes).map(([name, scene]) => [name, { shots: scene.shots.map((x) => x.secs), card: (scene.cues.find((c) => c.card) || {}).at }]));
  });
  const to = async (name, t) => {
    // Step the scene's clock up to `t` seconds.
    for (let i = 0; i < 2000; i++) {
      const s = await snap();
      if (s.state !== 'cutscene' || s.flow.scene !== name || s.flow.sceneTime >= t) return;
      await h.skip(Math.max(1, Math.min(15, Math.round((t - s.flow.sceneTime) * 30))));
    }
  };
  const picture = async (file) => {
    await h.wait(900); // the bars, the card and the subtitle settle on the real clock
    await h.frames(1);
    await h.shot(`${out}/${file}.png`);
  };

  await page.mouse.move(640, 360);
  await h.click('.title-actions .btn-primary');
  await h.skip(2);
  const problems = [];
  for (const name of ['opening', 'shop', 'cage', 'truck', 'ending']) {
    let s = await until((x) => x.state === 'cutscene' && x.flow.scene === name, 900, 3);
    if (s.state !== 'cutscene' || s.flow.scene !== name) {
      problems.push(`the "${name}" scene never came up (${s.state}, level ${s.run.level}, phase ${s.flow.phase})`);
      break;
    }
    const plan = scenes[name];
    let start = 0;
    for (const [i, secs] of plan.shots.entries()) {
      // A third of the way into the shot, or where its title card has come up.
      const at = plan.card !== undefined && plan.card >= start && plan.card < start + secs ? null : start + secs * 0.45;
      if (at !== null) {
        await to(name, at);
        await picture(`${name}-${i + 1}`);
      }
      start += secs;
    }
    if (plan.card !== undefined) {
      await to(name, plan.card + 1.6);
      await picture(`${name}-card`);
    }
    // On with it.
    await h.key('Enter', true);
    await h.skip(1);
    await h.key('Enter', false);
    await h.skip(2);
    if (name === 'ending') break;
    s = await until((x) => x.state === 'playing', 200, 3);
    if (name === 'truck') {
      await h.eval(() => {
        const G = window.__G;
        window.__fx.standAt(G.level.extraction.pos.x, G.level.extraction.pos.z, 0.4);
      });
      await h.skip(3);
      continue;
    }
    await h.eval(() => window.__G.game.debugGrab());
    for (let i = 0; i < 60 && (await snap()).flow.phase === 'clear'; i++) {
      await h.skip(15);
      await h.eval(() => window.__fx.killAll());
    }
  }
  const errors = await h.errors();
  if (errors.length) problems.push(`errors: ${errors.join(' | ')}`);
  if (problems.length) throw new Error(problems.join('\n'));
};
