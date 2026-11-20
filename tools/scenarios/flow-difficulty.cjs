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

  // The three rows, from the page's own config.
  const D = await h.eval(() => {
    const F = __G.config.flow;
    return { rows: F.difficulty, fallback: F.defaultDifficulty };
  });
  const wave = (name, level) => D.rows[name].levels[level - 1].wave;
  const size = (w) => w.buzzard + w.goon;

  let s = await snap();
  const base = D.rows.hustler;
  check(`default difficulty Hustler: regen ${base.regen.delay} s / ${base.regen.rate} per s, ${base.maxAlive} alive`, s.difficulty === 'hustler' && D.fallback === 'hustler' && s.player.regen.delay === base.regen.delay && s.player.regen.rate === base.regen.rate && s.flow.maxAlive === base.maxAlive, { d: s.difficulty, regen: s.player.regen });

  // ---- Kingpin from the settings panel, mid-run ------------------------------------------------------
  await h.eval(() => __G.settings.set('difficulty', 'kingpin'));
  s = await snap();
  let r = await rec();
  const top = D.rows.kingpin;
  check(`Kingpin at once: enemy table, regen ${top.regen.delay} / ${top.regen.rate}, ${top.maxAlive} alive`, s.difficulty === 'kingpin' && lastDiff(r) === 'kingpin' && s.player.regen.delay === top.regen.delay && s.player.regen.rate === top.regen.rate && s.flow.maxAlive === top.maxAlive, { d: s.difficulty, table: lastDiff(r), regen: s.player.regen, max: s.flow.maxAlive });
  await h.eval(() => window.__fx.killAll());
  await h.eval(() => __G.game.debugGrab());
  s = await snap();
  let w = wave('kingpin', 1);
  check(`the wave of level 1 is Kingpin's: ${w.buzzard} Buzzards + ${w.goon} Goons`, s.flow.lastWave && s.flow.lastWave.order.filter((t) => t === 'buzzard').length === w.buzzard && s.flow.lastWave.order.length === size(w), s.flow.lastWave && s.flow.lastWave.order.join(','));

  // ---- Hustler while that wave is still arriving ---------------------------------------------------------
  await h.skip(60);
  await h.eval(() => __G.settings.set('difficulty', 'hustler'));
  s = await snap();
  r = await rec();
  check(`Hustler at once: regen ${base.regen.delay} / ${base.regen.rate}, ${base.maxAlive} alive, the queued wave keeps its size`, s.difficulty === 'hustler' && lastDiff(r) === 'hustler' && s.player.regen.delay === base.regen.delay && s.player.regen.rate === base.regen.rate && s.flow.maxAlive === base.maxAlive && s.flow.lastWave.order.length === size(w), { regen: s.player.regen, max: s.flow.maxAlive });
  s = await until((x) => x.flow.queue === 0, 900, 10);
  check('the queue still drains under the lower cap', s.flow.queue === 0 && s.alive <= base.maxAlive, `alive ${s.alive}`);
  // Level 1 is seen out, and level 2's wave is the new difficulty's.
  for (let i = 0; i < 40 && (await snap()).flow.phase === 'clear'; i++) {
    await h.skip(10);
    await h.eval(() => window.__fx.killAll());
  }
  s = await until((x) => x.run.level === 2 && x.state === 'playing', 400, 3);
  const patrol = D.rows.hustler.levels[1].patrol;
  check(`level 2's patrol is Hustler's: ${patrol.buzzard} + ${patrol.goon}`, s.run.level === 2 && s.buzzards === patrol.buzzard && s.goons === patrol.goon, { level: s.run.level, b: s.buzzards, g: s.goons });
  await h.eval(() => window.__fx.killAll());
  await h.eval(() => __G.game.debugGrab());
  s = await snap();
  w = wave('hustler', 2);
  check(`…and its wave: ${w.buzzard} Buzzards + ${w.goon} Goons`, s.flow.lastWave.order.length === size(w) && s.flow.lastWave.order.filter((t) => t === 'buzzard').length === w.buzzard, s.flow.lastWave.order.join(','));
  await h.eval(() => __G.game.setDifficulty('nonsense'));
  s = await snap();
  check('an unknown name falls back to the default', s.difficulty === D.fallback && s.flow.maxAlive === D.rows[D.fallback].maxAlive);
  await h.eval(() => __G.game.setDifficulty('boss'));

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
  check(`wave 2 on Boss: ${D.rows.boss.maxAlive} + 1 alive, hp × 1.07`, s.flow.maxAlive === D.rows.boss.maxAlive + 1 && Math.abs(scaleAt2.hp - 1.07) < 1e-9, { max: s.flow.maxAlive, scaleAt2 });
  await h.eval(() => __G.settings.set('difficulty', 'kingpin'));
  s = await snap();
  r = await rec();
  const scaleAfter = r.calls.setScale[r.calls.setScale.length - 1];
  check(`Kingpin mid-wave: ${top.maxAlive} + 1 alive, the same wave 2 multipliers (not compounded)`, s.flow.maxAlive === top.maxAlive + 1 && lastDiff(r) === 'kingpin' && JSON.stringify(scaleAfter) === JSON.stringify(scaleAt2), { max: s.flow.maxAlive, scaleAfter });
  await h.eval(() => __G.settings.set('difficulty', __G.config.flow.defaultDifficulty));
  await finish();
};
