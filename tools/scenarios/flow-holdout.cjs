// Hold the Block through three waves: arrival counts and mixes, banners, the 3-2-1 countdown, the
// resupply, explosives back after even waves, the wave multipliers, the score, then death and the best.
//
//   node build.mjs --dev --only=game --out=dist/dev-flow.html
//   node tools/shot.cjs dist/dev-flow.html --params "q=low&autostart=1&mode=holdout" --timeout 500 \
//        --scenario tools/scenarios/flow-holdout.cjs
//
// DIRECTOR: the player is invulnerable (as with ?god=1, which the stub player ignores) and every Vulture
// is killed through enemies.damage the moment it arrives.

'use strict';

const { setup } = require('./flow-lib.cjs');

const OUT = 'shots/flow/holdout-';

module.exports = async (page, h) => {
  const { check, snap, rec, until, finish } = await setup(page, h);
  const shot = async (name) => {
    await h.frames(1);
    await h.shot(`${OUT}${name}.png`);
  };
  await h.eval(() => {
    window.__god = true;
    __G.player.invulnerable = true;
    try {
      localStorage.removeItem('murderinc.holdout.best');
    } catch (e) {
      /* storage off: best() reads 0 anyway */
    }
  });

  // What the formulas say, from the page's own config.
  const want = await h.eval(() => {
    const H = __G.config.flow.holdout;
    let score = 0;
    const waves = [];
    for (let n = 1; n <= 3; n++) {
      const total = H.total(n);
      const b = Math.round(total * H.buzzardShare(n));
      const kills = Math.round(H.score.buzzard * H.score.killScale(n)) * b + Math.round(H.score.goon * H.score.killScale(n)) * (total - b);
      score += kills + H.score.waveClear(n);
      const cap = __G.config.flow.difficulty[__G.game.difficulty].maxAlive;
      waves.push({ n, total, b, g: total - b, score, scale: { hp: H.hpScale(n), damage: H.damageScale(n), cooldown: H.cooldownScale(n) }, maxAlive: cap + H.extraAlive(n) });
    }
    return waves;
  });

  let s = await snap();
  check('?mode=holdout&autostart: Hold the Block, playing', s.state === 'playing' && s.mode === 'holdout', `${s.state} ${s.mode}`);
  // The autostart reset ran before the recorder was in: start again (the menu button's call) to see it.
  await h.eval(() => {
    __G.game.start({ mode: 'holdout', skipIntro: true });
    __G.player.invulnerable = true;
  });
  s = await snap();
  let r = await rec();
  check('no patrol, no markers, every reel case shut, "Stand by"', s.alive === 0 && ['reel1', 'reel2', 'reel3'].every((id) => r.props[id] === 'taken') && r.hud.tally[r.hud.tally.length - 1] === 'Stand by' && r.hud.objective[r.hud.objective.length - 1] === 'Vultures inbound', { alive: s.alive, props: r.props, tally: r.hud.tally.slice(-1) });

  // The truck is not an exit in this mode.
  await h.eval(() => window.__fx.standAt(__G.level.extraction.pos.x, __G.level.extraction.pos.z, 0.3));
  await h.skip(5);
  s = await snap();
  r = await rec();
  check('the truck does nothing in Hold the Block', s.state === 'playing' && r.hud.message.length === 0, r.hud.message);
  await h.eval(() => window.__fx.standAt(-4, 4, 0.01));

  let explosives = r.calls.explosivesReset;
  let t0 = s.run.time;
  for (const w of want) {
    const ev0 = (await rec()).events.length;
    s = await until((x) => x.run.wave === w.n, 400, 3);
    r = await rec();
    const waveEv = r.events.slice(ev0).find((e) => e[0] === 'holdout:wave');
    if (w.n === 1) check('wave 1 starts 3.5 s in', Math.abs(s.run.time - t0 - 3.5) < 0.15, `${(s.run.time - t0).toFixed(2)} s`);
    else check(`wave ${w.n} starts after the 9 s breather`, Math.abs(s.run.time - t0 - 9) < 0.15, `${(s.run.time - t0).toFixed(2)} s`);
    check(`holdout:wave {wave: ${w.n}, count: ${w.total}}`, waveEv && waveEv[1].wave === w.n && waveEv[1].count === w.total, waveEv);
    const warn = r.hud.warn[r.hud.warn.length - 1];
    check(`banner "Wave ${w.n} — DIR" for 3.6 s`, warn && new RegExp(`^Wave ${w.n} — (NORTH|SOUTH|EAST|WEST|NORTH-EAST|NORTH-WEST|SOUTH-EAST|SOUTH-WEST)$`).test(warn[0]) && warn[1] === 3.6, warn);
    const scale = r.calls.setScale[r.calls.setScale.length - 1];
    const close = (a, b) => Math.abs(a - b) < 1e-9;
    check(`wave ${w.n} multipliers and alive cap`, scale && close(scale.hp, w.scale.hp) && close(scale.damage, w.scale.damage) && close(scale.cooldown, w.scale.cooldown) && s.flow.maxAlive === w.maxAlive, { scale, maxAlive: s.flow.maxAlive });
    check('objective "Hold the block"', r.hud.objective[r.hud.objective.length - 1] === 'Hold the block');
    if (w.n === 1) await shot('00-wave1');

    // Kill everyone the moment they arrive, until the wave is over.
    await h.eval(() => {
      __G.player.health = 50; // regen off until the next wave re-applies the difficulty: the heal shows alone
      __G.player.regen.rate = 0;
    });
    let spawned = 0;
    for (let i = 0; i < 200 && (await snap()).holdout.active; i++) {
      await h.skip(6);
      await h.eval(() => window.__fx.killAll());
    }
    s = await snap();
    r = await rec();
    const tail = r.events.slice(ev0);
    const spawns = tail.filter((e) => e[0] === 'enemy:spawn');
    spawned = spawns.length;
    const b = spawns.filter((e) => e[1].enemy === 'buzzard').length;
    check(`wave ${w.n}: ${w.b} Buzzards + ${w.g} Goons arrived`, spawned === w.total && b === w.b, `${b} + ${spawned - b}`);
    const cleared = tail.find((e) => e[0] === 'objective:done');
    check(`wave ${w.n} cleared: objective:done {id: wave, index: ${w.n}, total: ${w.n}}`, cleared && cleared[1].id === 'wave' && cleared[1].index === w.n && cleared[1].total === w.n, cleared);
    check(`score after wave ${w.n}: ${w.score}`, Math.round(s.run.score) === w.score, `${s.run.score}`);
    check('tally "Wave N · score" with separators', r.hud.tally[r.hud.tally.length - 1] === `Wave ${w.n} · ${w.score.toLocaleString('en-US')}`, r.hud.tally.slice(-1)[0]);
    check('resupply: a drop and a half for every gun, the crates back, and +35 HP', r.calls.resupply[r.calls.resupply.length - 1] === 1.5 && r.calls.heal[r.calls.heal.length - 1] === 35 && s.player.health === 85 && (await h.eval(() => __G.game.pickups.crates)) === 4, { resupply: r.calls.resupply.slice(-1), health: s.player.health });
    const evenWave = w.n % 2 === 0;
    check(`explosives ${evenWave ? 'restored' : 'left as they are'} after wave ${w.n}`, r.calls.explosivesReset === explosives + (evenWave ? 1 : 0), `${r.calls.explosivesReset - explosives}`);
    explosives = r.calls.explosivesReset;
    check('radio "Wave N down…" and "Catch your breath"', r.hud.radio.some((x) => x[1] === `Wave ${w.n} down. Fresh ammo on the block — 9 seconds.`) && r.hud.objective[r.hud.objective.length - 1] === 'Catch your breath');
    t0 = s.run.time;
    if (w.n === 1) {
      // The countdown in the last three seconds of the breather.
      const m0 = r.hud.message.length;
      await h.skip(250); // 8.3 s
      r = await rec();
      const msgs = r.hud.message.slice(m0).map((m) => `${m[0]}/${m[1]}`);
      check('"Wave 2 in 3 / 2 / 1", one a second', msgs.join(' ') === 'Wave 2 in 3/1 Wave 2 in 2/1 Wave 2 in 1/1', msgs.join(' '));
    }
  }
  await shot('01-wave3-cleared');

  // ---- death and the best score ----------------------------------------------------------------------
  const score = want[2].score;
  await h.eval(() => {
    window.__god = false;
    __G.player.invulnerable = false;
    __G.player.damage(1000, null, 'bullet');
  });
  await h.skip(50);
  r = await rec();
  let card = r.cards.filter((c) => c[0] === 'dead').pop();
  check('death card: 3 waves cleared, the score, a new best', card && card[1].mode === 'holdout' && card[1].wave === 3 && card[1].score === score && card[1].best === score && card[1].newBest === true, card && card[1]);
  check('the best is stored', (await h.eval(() => __G.settings.best())) === score);
  await shot('02-dead');

  await h.eval(() => __G.game.retry());
  await h.skip(40);
  s = await snap();
  r = await rec();
  check('retry: Hold the Block again from "Stand by", score 0, retries 1', s.mode === 'holdout' && s.run.score === 0 && s.run.wave === 0 && s.run.retries === 1 && r.hud.tally[r.hud.tally.length - 1] === 'Stand by', s.run);
  await h.eval(() => __G.player.damage(1000, null, 'bullet'));
  await h.skip(50);
  r = await rec();
  card = r.cards.filter((c) => c[0] === 'dead').pop();
  check('a lower score keeps the best and is not a new best', card && card[1].score === 0 && card[1].best === score && card[1].newBest === false, card && card[1]);
  await finish();
};
