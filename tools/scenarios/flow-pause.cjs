// Pause and resume: the pause key (with its 0.35 s debounce), losing the mouse lock, hiding the tab,
// pausing during the intro, and that nothing moves while paused.
//
//   node build.mjs --dev --only=game --out=dist/dev-flow.html
//   node tools/shot.cjs dist/dev-flow.html --params "q=low" --timeout 300 --scenario tools/scenarios/flow-pause.cjs

'use strict';

const { setup } = require('./flow-lib.cjs');

module.exports = async (page, h) => {
  const { check, snap, rec, tap, finish } = await setup(page, h);
  const states = async () => (await rec()).events.filter((e) => e[0] === 'game:state').map((e) => e[1].state);

  // ---- pause during the intro --------------------------------------------------------------------
  await h.eval(() => __G.game.start({}));
  await h.skip(15); // 0.5 s: the location card is up
  let s = await snap();
  check('a full intro is running', s.state === 'intro');
  await tap('KeyP');
  s = await snap();
  let r = await rec();
  check('the pause key during the intro: straight to playing, then paused', (await states()).join(' ') === 'intro playing paused', (await states()).join(' '));
  check('paused: pause card, audio paused, location card down, player not simulated', s.screen === 'paused' && r.calls.paused[r.calls.paused.length - 1] === true && r.calls.locationCard[r.calls.locationCard.length - 1][0] === false && s.post.fade === 0, { screen: s.screen, paused: r.calls.paused.slice(-1) });
  await h.frames(1);
  await h.shot('shots/flow/pause-00-card.png');

  // ---- nothing moves while paused ---------------------------------------------------------------------
  const before = await h.eval(() => ({ t: __G.game.run.time, clock: __G.game.flow.clock, e: __G.enemies.list.map((e) => e.pos.toArray()) }));
  check('update reports the sim as not live', await h.eval(() => __G.game.update(0) === false));
  await tap('KeyP'); // inside the debounce: ignored
  s = await snap();
  check('the pause key is ignored for 0.35 s after pausing', s.state === 'paused');
  await h.skip(60);
  const after = await h.eval(() => ({ t: __G.game.run.time, clock: __G.game.flow.clock, e: __G.enemies.list.map((e) => e.pos.toArray()) }));
  check('run clock and enemies frozen while paused', after.t === before.t && after.clock === before.clock && JSON.stringify(after.e) === JSON.stringify(before.e), { before: before.t, after: after.t });

  // ---- the pause key resumes after the debounce ----------------------------------------------------------
  const locks = (await rec()).calls.requestLock;
  await tap('KeyP');
  s = await snap();
  r = await rec();
  check('the pause key resumes: playing, audio back, mouse re-requested', s.state === 'playing' && r.calls.paused[r.calls.paused.length - 1] === false && r.calls.requestLock > locks && s.screen === 'none', { state: s.state, screen: s.screen });
  await h.skip(30);
  s = await snap();
  check('the run clock runs again', s.run.time > after.t + 0.9, `${s.run.time.toFixed(2)}`);

  // ---- mouse lock lost ----------------------------------------------------------------------------------
  await h.eval(() => __G.events.emit('input:lock', { locked: false, mode: 'drag' }));
  await h.skip(1);
  check('the drag fallback losing nothing does not pause', (await snap()).state === 'playing');
  await h.eval(() => {
    __G.events.emit('input:lock', { locked: true, mode: 'lock' });
    __G.events.emit('input:lock', { locked: false, mode: 'lock' });
  });
  s = await snap();
  check('losing the mouse lock after having it pauses', s.state === 'paused' && s.screen === 'paused', s.state);
  await h.eval(() => __G.game.resume());
  s = await snap();
  check('game.resume() (the Resume button) goes back to playing', s.state === 'playing');

  // ---- tab hidden ------------------------------------------------------------------------------------------
  await h.skip(15);
  await h.eval(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
    document.dispatchEvent(new Event('visibilitychange'));
    delete document.hidden;
  });
  s = await snap();
  check('hiding the tab pauses', s.state === 'paused');
  await h.eval(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
    document.dispatchEvent(new Event('visibilitychange'));
    delete document.hidden;
  });
  s = await snap();
  check('showing it again does not resume by itself', s.state === 'paused');
  await h.eval(() => __G.game.resume());

  // ---- pause outside a run does nothing -------------------------------------------------------------------
  await h.eval(() => __G.game.toTitle());
  await h.eval(() => __G.game.pause());
  await tap('KeyP');
  s = await snap();
  check('pause on the title does nothing', s.state === 'title');
  const seq = (await states()).join(' ');
  check('state sequence', seq === 'intro playing paused playing paused playing paused playing title', seq);
  await finish();
};
