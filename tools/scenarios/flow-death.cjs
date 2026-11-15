// Death, retry, restart and redeploy: the retries counter, the quick intro and the full run reset.
//
//   node build.mjs --dev --only=game --out=dist/dev-flow.html
//   node tools/shot.cjs dist/dev-flow.html --params "q=low&autostart=1" --timeout 400 --scenario tools/scenarios/flow-death.cjs
//
// ?autostart run (no intro) → a reel taken, ammo spent, health down → killed → the death sequence (input
// released, radio cleared, screen to grey, card after 1.5 s with time and reels) → Run it back (retries 1,
// 1.1 s intro without card or radio, everything back at the start) → Restart run from the pause card
// (retries 2) → a finished run → Run it back on the debrief (retries 0).

'use strict';

const { setup } = require('./flow-lib.cjs');

const OUT = 'shots/flow/death-';

module.exports = async (page, h) => {
  const { check, snap, rec, tap, until, finish } = await setup(page, h);
  const shot = async (name) => {
    await h.frames(1);
    await h.shot(`${OUT}${name}.png`);
  };

  let s = await snap();
  let r = await rec();
  check('?autostart skips the title and the intro', s.state === 'playing' && s.mode === 'mission' && s.post.fade === 0, s.state);
  const full = await h.eval(() => ({ reserve: __G.weapon.reserve, mag: __G.weapon.mag, explosives: __G.explosives.items.length }));

  // ---- a run in progress --------------------------------------------------------------------------
  await h.eval(() => __G.game.debugGrab());
  await h.skip(60);
  await h.eval(() => {
    const G = window.__G;
    G.weapon.reserve = 12;
    G.player.damage(40, null, 'bullet');
  });
  s = await snap();
  check('debugGrab secures the next reel', s.run.reels === 1 && s.run.time > 1.9, `${s.run.reels} reels, ${s.run.time.toFixed(2)} s`);
  const timeAtDeath = s.run.time;
  const ev0 = (await rec()).events.length;

  // ---- death ------------------------------------------------------------------------------------------
  await h.eval(() => __G.player.damage(1000, null, 'bullet'));
  await h.skip(1);
  s = await snap();
  r = await rec();
  const tail = r.events.slice(ev0).map((e) => e[0] + (e[0] === 'game:state' ? `:${e[1].state}` : ''));
  check('player:dead → game:state dead', tail.indexOf('player:dead') >= 0 && tail.indexOf('game:state:dead') > tail.indexOf('player:dead'), tail.join(' '));
  check('death: HUD hidden, radio cleared, mouse released, dead sting', r.calls.hudShown === false && r.calls.clearRadio > 0 && r.calls.exitLock > 0 && r.calls.stings.includes('dead'), r.calls);
  check('the world keeps simulating (death camera): update returns live', await h.eval(() => __G.game.update(0) === true));
  await h.skip(40); // 1.37 s
  s = await snap();
  r = await rec();
  check('no card before 1.5 s, screen greying', !r.cards.some((c) => c[0] === 'dead') && s.post.saturation < 0.3 && s.post.fade > 0.3, s.post);
  await h.skip(6);
  r = await rec();
  const dead = r.cards.filter((c) => c[0] === 'dead').pop();
  check('death card after 1.5 s: time on the block, reels 1/3', dead && Math.abs(dead[1].time - timeAtDeath) < 0.05 && dead[1].reels === 1 && dead[1].total === 3 && dead[1].mode === 'mission', dead && dead[1]);
  check('music back to calm with the card', r.calls.music === 0.15, `${r.calls.music}`);
  await shot('00-dead');
  check('pause does nothing once dead', await h.eval(() => (__G.game.pause(), __G.game.state === 'dead')));

  // ---- Run it back ------------------------------------------------------------------------------------
  const before = await rec();
  await h.eval(() => __G.game.retry());
  s = await snap();
  r = await rec();
  check('retry: retries 1, quick intro, same mode', s.run.retries === 1 && s.state === 'intro' && s.mode === 'mission', `${s.run.retries} ${s.state}`);
  const resetEv = r.events.slice(before.events.length).find((e) => e[0] === 'game:reset');
  check('game:reset {mode: mission}', resetEv && resetEv[1].mode === 'mission');
  check('full reset: reels 0, time 0, weapon full, explosives back, all reels live', s.run.reels === 0 && s.run.time === 0 && s.reserve === full.reserve && r.calls.explosivesReset > before.calls.explosivesReset && ['reel1', 'reel2', 'reel3'].every((id) => r.props[id] === 'live'), { reserve: s.reserve, props: r.props });
  check('full reset: health 100, fresh patrol of 6, HUD 0/3 and the first objective', s.player.health === 100 && s.player.alive && s.alive === 6 && r.hud.reels[r.hud.reels.length - 1] === '0/3' && r.hud.objective[r.hud.objective.length - 1] === 'Take back the three master reels', { health: s.player.health, alive: s.alive });
  check('screen back to normal colour, black for the fade-in', s.post.saturation === 1 && s.post.fade === 1, s.post);
  await h.skip(20);
  s = await snap();
  check('quick intro still running at 0.67 s', s.state === 'intro');
  await h.skip(16); // 1.2 s
  s = await snap();
  r = await rec();
  check('quick intro ends at 1.1 s', s.state === 'playing', s.state);
  check('no location card and no intro radio on a retry', !r.calls.locationCard.slice(before.calls.locationCard.length).some((c) => c[0]) && r.hud.radio.length === before.hud.radio.length, r.calls.locationCard.slice(before.calls.locationCard.length));
  check('run clock only counts playing', s.run.time < 0.15, s.run.time.toFixed(3));

  // ---- Restart run from the pause card ----------------------------------------------------------------
  await tap('KeyP');
  s = await snap();
  check('paused', s.state === 'paused');
  await h.eval(() => __G.game.restart());
  await h.skip(40);
  s = await snap();
  check('Restart run: retries 2, a fresh run after the quick intro', s.run.retries === 2 && s.state === 'playing' && s.run.reels === 0, `${s.run.retries} ${s.state}`);

  // ---- a finished run, then Run it back on the debrief ----------------------------------------------------
  await h.eval(() => {
    const G = window.__G;
    G.game.debugGrab();
    G.game.debugGrab();
    G.game.debugGrab();
    window.__fx.standAt(G.level.extraction.pos.x, G.level.extraction.pos.z, 0.3);
  });
  s = await until((x) => x.state === 'complete', 10, 1);
  await h.skip(105);
  r = await rec();
  const debrief = r.cards.filter((c) => c[0] === 'complete').pop();
  check('the debrief counts the retries of this attempt (2) and rates without the no-retry point', debrief && debrief[1].retries === 2, debrief && debrief[1]);
  await h.eval(() => __G.game.redeploy());
  await h.skip(40);
  s = await snap();
  r = await rec();
  check('Run it back on the debrief: retries 0, playing, truck shut again', s.run.retries === 0 && s.state === 'playing' && r.props.truck === 'idle' && !s.player.invulnerable && s.player.enabled, { retries: s.run.retries, truck: r.props.truck });

  // ---- back to the title ----------------------------------------------------------------------------------
  await h.eval(() => __G.game.toTitle());
  await h.skip(30);
  s = await snap();
  check('toTitle: the title fly-through again, nobody on the block', s.state === 'title' && s.alive === 0 && !s.player.enabled && s.fov === 50, `${s.state} alive ${s.alive}`);
  const seq = (await rec()).events.filter((e) => e[0] === 'game:state').map((e) => e[1].state).join(' ');
  check('state sequence', seq === 'dead intro playing paused intro playing complete intro playing title', seq);
  await finish();
};
