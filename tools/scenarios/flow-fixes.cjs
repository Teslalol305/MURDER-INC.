// The fix-pass checks for flow, input and audio, against the full build with real audio:
//   1. "Back to title" from the death card: the title has no low-health look and no death muffle.
//   2. "Back to title" from a debrief reached hurt (25 HP): the same.
//   3. Hold the Block's full intro: its own tagline and radio line, no reels; a Story level says its
//      name, what it asks for and where to go.
//   4. A window blur pauses a live run (drag mode and touch have no pointer lock to lose).
//   5. A real WebGL context loss pauses the run, and the restore leaves the pause card up.
//   6. The pause card made while the lock is still held says how to get the mouse back.
//
//   node build.mjs --dev --out=dist/dev-fix-flow-input-audio.html
//   node tools/shot.cjs dist/dev-fix-flow-input-audio.html --params "q=test&scenes=0" --size 960x540 --timeout 900 \
//     --scenario tools/scenarios/flow-fixes.cjs
// FLOW_NOSHOTS=1 skips the screenshots.

'use strict';

const { setup } = require('./flow-lib.cjs');

const OUT = 'shots/flow-fixes';

module.exports = async (page, h) => {
  const { check, snap, rec, until, finish } = await setup(page, h);
  const shots = !process.env.FLOW_NOSHOTS;
  const shot = async (name) => {
    if (!shots) return;
    await h.frames(2);
    await h.shot(`${OUT}/${name}.png`);
  };
  const look = () =>
    h.eval(() => {
      const G = window.__G;
      const p = G.render.post;
      return {
        state: G.game.state, screen: G.menus.screen, lowHealth: p.lowHealth, damage: p.damage, saturation: p.saturation,
        alive: G.player.alive, health: G.player.health, muffle: G.audio.debug ? G.audio.debug.muffle : null,
      };
    });
  const clickText = async (text) => {
    await page.locator(`button:visible:has-text("${text}")`).first().click();
    await h.skip(2);
  };

  await h.frames(2);
  await h.eval(() => window.__G.audio.unlock());

  // ---- 1. death card → Back to title ----------------------------------------------------------------
  await h.eval(() => window.__G.game.start({ mode: 'mission', skipIntro: true }));
  await h.skip(10);
  await h.eval(() => window.__G.player.damage(1000, null, 'bullet'));
  let s = await until((x) => x.screen === 'dead', 120);
  let L = await look();
  check('death: the card is up, the screen is in the death look and the sound muffled', s.screen === 'dead' && L.lowHealth > 0.5 && (L.muffle === null || L.muffle > 0.5), L);
  await shot('01-death-card');
  await clickText('Back to title');
  await h.skip(90); // three seconds on the title
  L = await look();
  check('Back to title from the death card: title state, player alive and whole', L.state === 'title' && L.screen === 'title' && L.alive && L.health === 100, L);
  check('… no low-health look and no damage flash on the title', L.lowHealth === 0 && L.damage === 0 && L.saturation === 1, L);
  check('… the death muffle is lifting (hold 0)', L.muffle === null || L.muffle < 0.15, `muffle ${L.muffle}`);
  await shot('02-title-after-death');

  // ---- 2. a debrief reached hurt → Back to title ----------------------------------------------------------
  await h.eval(() => {
    const G = window.__G;
    G.game.start({ mode: 'mission', skipIntro: true });
  });
  await h.skip(5);
  await h.eval(() => {
    const G = window.__G;
    G.game.debugLevel(3); // the last level: all three reels in hand, the truck ahead
    G.enemies.clear();
    G.game.flow.queue.length = 0;
    const ex = G.level.extraction;
    G.player.reset({ pos: new G.THREE.Vector3(ex.pos.x, G.physics.groundHeight(ex.pos.x, ex.pos.z, ex.pos.y + 1.5), ex.pos.z), yaw: 0 });
    G.player.damage(75, null, 'bullet');
  });
  s = await until((x) => x.screen === 'complete', 200);
  await h.skip(30);
  L = await look();
  check('debrief at 25 HP: the card is up with the low-health look on', s.screen === 'complete' && L.health === 25 && L.lowHealth > 0.5, L);
  await clickText('Back to title');
  await h.skip(30);
  L = await look();
  check('Back to title from the debrief: no low-health look', L.state === 'title' && L.lowHealth === 0 && L.damage === 0 && L.alive && L.health === 100, L);

  // ---- 3. the full intros -------------------------------------------------------------------------------
  const intro = async (mode) => {
    const r0 = (await rec()).hud.radio.length;
    await h.eval((m) => window.__G.game.start({ mode: m }), mode);
    await h.skip(33); // 1.1 s: card at 0.25 s, radio at 0.9 s
    const card = await h.eval(() => ({
      place: (document.querySelector('.loc-place') || {}).textContent,
      tag: (document.querySelector('.loc-tag') || {}).textContent,
      state: window.__G.game.state,
      mode: window.__G.game.mode,
    }));
    const lines = (await rec()).hud.radio.slice(r0).map((x) => x[1]);
    return { card, lines };
  };
  const text = await h.eval(() => {
    const t = window.__G.config.text;
    const first = t.story.levels[window.__G.config.story.levels[0].id];
    return { holdTag: t.location.taglineHoldout, holdIntro: t.radio.introHoldout.text, place: t.story.stage(1, first.title), brief: first.brief, go: first.go.text };
  });
  let it = await intro('holdout');
  check('Hold the Block intro: its own tagline on the location card', it.card.state === 'intro' && it.card.mode === 'holdout' && it.card.tag === text.holdTag && it.card.tag === 'One block. Endless Vultures.', it.card);
  check('… the place line is still the block and the clock', /Hollis, Queens · Jamaica Ave/.test(it.card.place || ''), it.card.place);
  check('… its own radio line, not the reels briefing', it.lines.length === 1 && it.lines[0] === text.holdIntro && !/reel|master/i.test(it.lines[0]), it.lines);
  await shot('03-holdout-intro');

  // ---- 4. a window blur pauses the run ------------------------------------------------------------------
  await h.skip(45); // the intro is over
  s = await snap();
  check('holdout is live', s.state === 'playing', s.state);
  await h.eval(() => window.dispatchEvent(new Event('blur')));
  await h.skip(2);
  s = await snap();
  check('a window blur pauses the live run', s.state === 'paused' && s.screen === 'paused', s.state);
  const hint = await h.eval(() => window.__G.input.hint());
  check('the pause card hint never says the mouse is locked in', !/locked in/i.test(hint), hint);
  await h.eval(() => window.__G.game.resume());
  await h.skip(5);
  s = await snap();
  check('resume from the card', s.state === 'playing', s.state);

  // ---- 5. a real context loss pauses; the restore leaves the card up ----------------------------------------
  const lost = await h.eval(() => {
    const ext = window.__G.renderer.getContext().getExtension('WEBGL_lose_context');
    if (!ext) return false;
    window.__lose = ext;
    ext.loseContext();
    return true;
  });
  if (lost) {
    await h.wait(300);
    await h.skip(3);
    s = await snap();
    check('context lost mid-run: the run pauses', s.state === 'paused' && s.screen === 'paused', s.state);
    await h.eval(() => window.__lose.restoreContext());
    await h.wait(500);
    await h.skip(10);
    s = await snap();
    check('context restored: still paused until the player resumes', s.state === 'paused', s.state);
    await h.eval(() => window.__G.game.resume());
    await h.skip(5);
    s = await snap();
    check('resume after the restore', s.state === 'playing', s.state);
  } else {
    console.log('note  WEBGL_lose_context is not available: emitting render:lost instead');
    await h.eval(() => window.__G.events.emit('render:lost', {}));
    s = await snap();
    check('render:lost pauses the run', s.state === 'paused', s.state);
    await h.eval(() => window.__G.game.resume());
  }

  // ---- 6. the pause hint while a lock is still held (P while locked: the release comes later) ---------------
  const held = await h.eval(() => {
    const G = window.__G;
    const realLocked = Object.getOwnPropertyDescriptor(G.input, 'locked');
    G.input.locked = true; // the moment between pause() and the browser's pointerlockchange
    G.game.pause();
    const card = document.querySelector('#ui').innerText;
    const out = { state: G.game.state, hint: G.input.hint(), card };
    if (realLocked) Object.defineProperty(G.input, 'locked', realLocked);
    G.input.locked = false;
    return out;
  });
  check('paused with the lock still held: the card says Resume locks the mouse back in', held.state === 'paused' && /Resume locks the mouse/.test(held.hint) && held.card.includes(held.hint), held.hint);
  await shot('04-pause-card');

  // ---- A Story level says where Rule is, what it asks for and where to go --------------------------------
  await h.eval(() => window.__G.game.toTitle());
  await h.skip(5);
  it = await intro('mission');
  check("Story intro: the level's name and brief on the card, the Vault's directions on the radio", it.card.place === text.place && it.card.tag === text.brief && it.lines.length === 1 && it.lines[0] === text.go, it);

  await finish();
};
