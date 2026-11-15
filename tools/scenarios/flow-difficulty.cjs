// Switching difficulty mid-run: what changes at once (enemy table, player regen, alive cap), what follows
// from the next spawn on (wave sizes), and that holdout multipliers sit on the new table without compounding.
//
//   node build.mjs --dev --only=game --out=dist/dev-flow.html
//   node tools/shot.cjs dist/dev-flow.html --params "q=low&autostart=1" --timeout 400 --scenario tools/scenarios/flow-difficulty.cjs

'use strict';

const { setup } = require('./flow-lib.cjs');

module.exports = async (page, h) => {
  const { check, snap, rec, until, finish } = await setup(page, h);
  const lastDiff = (r) => r.calls.setDifficulty[r.calls.setDifficulty.length - 1];
  await h.eval(() => {
    window.__god = true;
    __G.player.invulnerable = true;
  });

  let s = await snap();
  check('default difficulty Boss: regen 5.5 s / 16 per s, 11 alive', s.difficulty === 'boss' && s.player.regen.delay === 5.5 && s.player.regen.rate === 16 && s.flow.maxAlive === 11, { d: s.difficulty, regen: s.player.regen });

  // ---- Kingpin from the settings panel, mid-run ------------------------------------------------------
  await h.eval(() => __G.settings.set('difficulty', 'kingpin'));
  s = await snap();
  let r = await rec();
  check('Kingpin at once: enemy table, regen 7 / 10, 13 alive', s.difficulty === 'kingpin' && lastDiff(r) === 'kingpin' && s.player.regen.delay === 7 && s.player.regen.rate === 10 && s.flow.maxAlive === 13, { d: s.difficulty, table: lastDiff(r), regen: s.player.regen, max: s.flow.maxAlive });
  await h.eval(() => window.__fx.killAll());
  await h.eval(() => __G.game.debugGrab());
  s = await snap();
  check('the next wave is Kingpin\'s first: 3 Buzzards + 6 Goons', s.flow.lastWave && s.flow.lastWave.order.filter((t) => t === 'buzzard').length === 3 && s.flow.lastWave.order.length === 9, s.flow.lastWave && s.flow.lastWave.order.join(','));

  // ---- Hustler while that wave is still arriving ---------------------------------------------------------
  await h.skip(60);
  await h.eval(() => __G.settings.set('difficulty', 'hustler'));
  s = await snap();
  r = await rec();
  check('Hustler at once: regen 4 / 25, 9 alive, the queued wave keeps its size', s.difficulty === 'hustler' && lastDiff(r) === 'hustler' && s.player.regen.delay === 4 && s.player.regen.rate === 25 && s.flow.maxAlive === 9 && s.flow.lastWave.order.length === 9, { regen: s.player.regen, max: s.flow.maxAlive });
  s = await until((x) => x.flow.queue === 0, 900, 10);
  check('the queue still drains under the lower cap', s.flow.queue === 0 && s.alive <= 9, `alive ${s.alive}`);
  await h.eval(() => window.__fx.killAll());
  await h.eval(() => __G.game.debugGrab());
  s = await snap();
  check('the next wave is Hustler\'s second: 2 Buzzards + 4 Goons', s.flow.lastWave.order.length === 6 && s.flow.lastWave.order.filter((t) => t === 'buzzard').length === 2, s.flow.lastWave.order.join(','));
  await h.eval(() => __G.game.setDifficulty('nonsense'));
  s = await snap();
  check('an unknown name falls back to Boss', s.difficulty === 'boss' && s.flow.maxAlive === 11);

  // ---- the mode setting waits for the next start --------------------------------------------------------
  await h.eval(() => __G.settings.set('mode', 'holdout'));
  s = await snap();
  check('changing the mode mid-run does not change this run', s.mode === 'mission');

  // ---- holdout: the multipliers ride on whatever table is current -------------------------------------
  await h.eval(() => {
    __G.game.start({ skipIntro: true }); // no mode: the saved one, now Hold the Block
    __G.player.invulnerable = true;
  });
  s = await snap();
  check('a new start takes the saved mode', s.mode === 'holdout' && s.run.retries === 0);
  s = await until((x) => x.run.wave === 1, 200, 5);
  for (let i = 0; i < 100 && (await snap()).holdout.active; i++) {
    await h.skip(6);
    await h.eval(() => window.__fx.killAll());
  }
  s = await until((x) => x.run.wave === 2, 400, 5);
  r = await rec();
  const scaleAt2 = r.calls.setScale[r.calls.setScale.length - 1];
  check('wave 2 on Boss: 11 + 1 alive, hp × 1.07', s.flow.maxAlive === 12 && Math.abs(scaleAt2.hp - 1.07) < 1e-9, { max: s.flow.maxAlive, scaleAt2 });
  await h.eval(() => __G.settings.set('difficulty', 'kingpin'));
  s = await snap();
  r = await rec();
  const scaleAfter = r.calls.setScale[r.calls.setScale.length - 1];
  check('Kingpin mid-wave: 13 + 1 alive, the same wave 2 multipliers (not compounded)', s.flow.maxAlive === 14 && lastDiff(r) === 'kingpin' && JSON.stringify(scaleAfter) === JSON.stringify(scaleAt2), { max: s.flow.maxAlive, scaleAfter });
  await h.eval(() => __G.settings.set('difficulty', 'boss'));
  await finish();
};
