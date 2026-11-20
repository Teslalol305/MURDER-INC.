// Death and the checkpoint: the retries counter, the quick intro, the level set up again with what
// Rule had when it began; then the restart from the pause card, a finished run and the redeploy.
//
//   node build.mjs --dev --only=game --out=dist/dev-flow.html
//   node tools/shot.cjs dist/dev-flow.html --params "q=low&autostart=1" --timeout 400 --scenario tools/scenarios/flow-death.cjs
//
// ?autostart run (no intro, no cutscenes) → level 1 done → in level 2: ammo spent, health down → killed
// → the death sequence (input released, radio cleared, screen to grey, card after 1.5 s with time, level
// and reels) → Retry level (retries 1, 1.1 s intro without card or radio, level 2 as it began: reel 1
// still his, his rack back, its patrol at their posts) → Restart level from the pause card (retries 2)
// → a finished run → Run it back on the debrief (retries 0, level 1, a fresh rack).

'use strict';

const { setup } = require('./flow-lib.cjs');

const OUT = 'shots/flow/death-';

module.exports = async (page, h) => {
  const { check, snap, rec, tap, until, finish } = await setup(page, h);
  const shot = async (name) => {
    await h.frames(1);
    await h.shot(`${OUT}${name}.png`);
  };
  const rack = () => h.eval(() => __G.weapon.slots.map((x) => `${x.id}:${x.mag}/${x.reserve}`).join(' '));
  const T = await h.eval(() => {
    const d = __G.config.flow.difficulty[__G.game.difficulty];
    return { levels: d.levels.map((l) => l.patrol.buzzard + l.patrol.goon), clear: __G.config.flow.story.levelClear };
  });

  let s = await snap();
  let r = await rec();
  check('?autostart skips the title and the intro: level 1, playing', s.state === 'playing' && s.mode === 'mission' && s.post.fade === 0 && s.run.level === 1, s.state);
  const fresh = await rack();

  // ---- level 1 done, level 2 in progress ----------------------------------------------------------
  await h.eval(() => __G.game.debugGrab());
  s = await snap();
  check('debugGrab takes the level\'s reel: the fight for it is on', s.run.reels === 1 && s.flow.phase === 'clear', `${s.run.reels} reels, phase ${s.flow.phase}`);
  // Put them down as they arrive.
  for (let i = 0; i < 40 && (await snap()).flow.phase === 'clear'; i++) {
    await h.skip(20);
    await h.eval(() => window.__fx.killAll());
  }
  s = await until((x) => x.run.level === 2 && x.state === 'playing', 300, 3);
  check('level 1 cleared: level 2 plays (no cutscene in an autostarted run)', s.run.level === 2 && s.state === 'playing' && s.run.reels === 1, { level: s.run.level, state: s.state });
  const atLevel2 = await rack();
  check('level 2 began with a breather for the guns', atLevel2 !== fresh && /chopper:30\/\d+/.test(atLevel2), atLevel2);
  const explosives0 = (await rec()).calls.explosivesReset;
  await h.skip(60);
  await h.eval(() => {
    const G = window.__G;
    // Half a magazine gone, a rocket sent, and a hit taken.
    G.weapon.restore({ ...G.weapon.loadout(), guns: { ...G.weapon.loadout().guns, chopper: { mag: 14, reserve: 12 }, rocket: { mag: 0, reserve: 1 } } });
    G.player.damage(40, null, 'bullet');
  });
  s = await snap();
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
  check('death card after 1.5 s: time on the block, level 2 of 4, reels 1/3', dead && Math.abs(dead[1].time - timeAtDeath) < 0.05 && dead[1].reels === 1 && dead[1].total === 3 && dead[1].mode === 'mission' && dead[1].level === 2 && dead[1].levels === 4 && dead[1].levelTitle === 'THE CHOP SHOP', dead && dead[1]);
  check('music back to calm with the card', r.calls.music === 0.15, `${r.calls.music}`);
  await shot('00-dead');
  check('pause does nothing once dead', await h.eval(() => (__G.game.pause(), __G.game.state === 'dead')));

  // ---- Retry level ------------------------------------------------------------------------------------
  const before = await rec();
  await h.eval(() => __G.game.retry());
  s = await snap();
  r = await rec();
  check('retry: retries 1, quick intro, same mode, the same level', s.run.retries === 1 && s.state === 'intro' && s.mode === 'mission' && s.run.level === 2, `${s.run.retries} ${s.state} level ${s.run.level}`);
  const since = r.events.slice(before.events.length);
  check('a checkpoint, not a new run: no game:reset', !since.some((e) => e[0] === 'game:reset'));
  check('the level as it began: reel 1 still his, reel 2 out there, the clock runs on', s.run.reels === 1 && r.props.reel1 === 'taken' && r.props.reel2 === 'live' && r.props.reel3 === 'live' && Math.abs(s.run.time - timeAtDeath) < 0.05, { reels: s.run.reels, props: r.props, time: s.run.time });
  check('his rack is what it was when the level began; explosives are back', (await rack()) === atLevel2 && r.calls.explosivesReset > explosives0, await rack());
  check('health 100, the level\'s patrol at their posts, HUD 1/3 and the level\'s objective', s.player.health === 100 && s.player.alive && s.alive === T.levels[1] && r.hud.reels[r.hud.reels.length - 1] === '1/3' && r.hud.objective[r.hud.objective.length - 1] === 'Get to reel 2 — follow the gold line', { health: s.player.health, alive: s.alive, objective: r.hud.objective.at(-1) });
  check('screen back to normal colour, black for the fade-in', s.post.saturation === 1 && s.post.fade === 1, s.post);
  await h.skip(20);
  s = await snap();
  check('quick intro still running at 0.67 s', s.state === 'intro');
  await h.skip(16); // 1.2 s
  s = await snap();
  r = await rec();
  check('quick intro ends at 1.1 s', s.state === 'playing', s.state);
  check('no location card and no radio on a retry', !r.calls.locationCard.slice(before.calls.locationCard.length).some((c) => c[0]) && r.hud.radio.length === before.hud.radio.length, r.calls.locationCard.slice(before.calls.locationCard.length));
  check('run clock only counts playing', s.run.time - timeAtDeath < 0.15, (s.run.time - timeAtDeath).toFixed(3));

  // ---- Restart level from the pause card --------------------------------------------------------------
  await h.eval(() => __G.game.debugGrab());
  await tap('KeyP');
  s = await snap();
  check('paused, with reel 2 just taken', s.state === 'paused' && s.run.reels === 2);
  const label = await h.eval(() => [...document.querySelectorAll('.card-actions .btn-label')].map((n) => n.textContent));
  check('the pause card restarts the level, and has a way back to the title', label.includes('Restart level') && label.includes('Back to title') && !label.includes('Restart run'), label);
  await h.eval(() => __G.game.restart());
  await h.skip(40);
  s = await snap();
  r = await rec();
  check('Restart level: retries 2, level 2 from its start, its reel back with the Vultures', s.run.retries === 2 && s.state === 'playing' && s.run.level === 2 && s.run.reels === 1 && s.flow.phase === 'reach' && r.props.reel2 === 'live', `${s.run.retries} ${s.state} reels ${s.run.reels} ${s.flow.phase}`);

  // ---- a finished run, then Run it back on the debrief ----------------------------------------------------
  await h.eval(() => {
    const G = window.__G;
    G.game.debugLevel(3); // straight to the last level, all three reels in hand
    window.__fx.standAt(G.level.extraction.pos.x, G.level.extraction.pos.z, 0.3);
  });
  s = await until((x) => x.state === 'complete', 10, 1);
  check('the last level ends at the truck', s.state === 'complete' && s.run.reels === 3 && s.run.level === 4, { state: s.state, run: s.run });
  await h.skip(105);
  r = await rec();
  const debrief = r.cards.filter((c) => c[0] === 'complete').pop();
  check('the debrief counts the retries of this attempt (2) and rates without the no-retry point', debrief && debrief[1].retries === 2, debrief && debrief[1]);
  const resets = r.events.filter((e) => e[0] === 'game:reset').length;
  await h.eval(() => __G.game.redeploy());
  await h.skip(100);
  s = await snap();
  r = await rec();
  check('Run it back on the debrief: a new story: retries 0, level 1, no reels, a fresh rack, truck shut again', s.run.retries === 0 && s.state === 'playing' && s.run.level === 1 && s.run.reels === 0 && (await rack()) === fresh && r.props.truck === 'idle' && !s.player.invulnerable && s.player.enabled && r.events.filter((e) => e[0] === 'game:reset').length === resets + 1, { run: s.run, truck: r.props.truck, rack: await rack() });

  // ---- back to the title ----------------------------------------------------------------------------------
  await h.eval(() => __G.game.toTitle());
  await h.skip(30);
  s = await snap();
  check('toTitle: the title fly-through again, nobody on the block', s.state === 'title' && s.alive === 0 && !s.player.enabled && s.fov === 50 && s.run.level === 1, `${s.state} alive ${s.alive}`);
  const seq = (await rec()).events.filter((e) => e[0] === 'game:state').map((e) => e[1].state).join(' ');
  check('state sequence', seq === 'intro playing dead intro playing paused intro playing playing complete intro playing title', seq);
  await finish();
};
