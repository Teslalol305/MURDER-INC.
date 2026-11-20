// A whole Story run by script, from the title screen to the debrief, checked against the flow rules.
// The cutscenes are switched off here (?scenes=0): tools/scenarios/flow-story.cjs plays those. This one
// is about the rules of a level.
//
//   node build.mjs --dev --only=game --out=dist/dev-flow.html
//   node tools/shot.cjs dist/dev-flow.html --params "q=low&scenes=0" --timeout 600 --scenario tools/scenarios/flow-mission.cjs
//
// Title fly-through → Enter → level 1's intro (its name on the location card, the Vault's first word) →
// its patrol at their posts → the facing cone and the range of the reel prompt → a broken hold that
// decays → the reel taken with held Interact and its wave (composition, interleaving, stagger, banner
// direction, radio line, the count on the objective line) → the refusal at the truck → level clear and
// the next level, three times over → the last level's pursuit → extraction → debrief card data.
// FLOW_NOSHOTS=1 in the environment skips the screenshots (checks only).
// DIRECTOR: the player is moved with player.reset and enemies are killed through enemies.damage.

'use strict';

const { setup } = require('./flow-lib.cjs');

const OUT = 'shots/flow/mission-';
const SECTORS = ['NORTH', 'NORTH-EAST', 'EAST', 'SOUTH-EAST', 'SOUTH', 'SOUTH-WEST', 'WEST', 'NORTH-WEST'];
const B = 'buzzard';
const Gn = 'goon';

module.exports = async (page, h) => {
  const { check, snap, rec, tap, until, finish } = await setup(page, h);
  const shot = async (name) => {
    if (process.env.FLOW_NOSHOTS) return; // a memory-starved machine: checks only
    await h.frames(1);
    await h.shot(`${OUT}${name}.png`);
  };
  const info = await h.eval(() => {
    const G = window.__G;
    window.__god = true;
    const d = G.config.flow.difficulty[G.game.difficulty];
    const S = G.config.text.story;
    return {
      reels: G.level.objectives.map((o) => ({ id: o.id, code: o.code, x: o.pos.x, z: o.pos.z })),
      truck: { x: G.level.extraction.pos.x, z: G.level.extraction.pos.z },
      difficulty: G.game.difficulty,
      levels: d.levels,
      budget: d.pursuitBudget,
      every: d.pursuitEvery,
      time: G.settings.get('time'),
      ids: G.config.story.levels.map((l) => l.id),
      starts: G.config.story.levels.map((l) => l.start),
      titles: G.config.story.levels.map((l) => S.levels[l.id].title),
      briefs: G.config.story.levels.map((l) => S.levels[l.id].brief),
      go: G.config.story.levels.map((l) => S.levels[l.id].go.text),
      radio: G.config.text.radio.reel.map((l) => l.text),
      done: G.config.text.radio.done.text,
      refuse: G.config.text.prompts.refuse,
      ratings: G.config.text.ratings,
      clear: G.config.flow.story.levelClear,
      leftover: G.config.flow.story.leftover,
    };
  });
  const count = (x) => (x ? x.buzzard + x.goon : 0);

  // ---- title ------------------------------------------------------------------------------------
  let s = await snap();
  check('boots to the title with the player disabled and a 50° camera', s.state === 'title' && !s.player.enabled && s.fov === 50, `${s.state} fov ${s.fov}`);
  const cam0 = s.cam;
  await h.skip(90);
  s = await snap();
  check('the title camera flies the cinematic path', Math.hypot(s.cam[0] - cam0[0], s.cam[2] - cam0[2]) > 1, `${cam0} → ${s.cam}`);
  check('the title fades in from black at the loop start', s.post.fade < 0.2, `fade ${s.post.fade.toFixed(2)}`);
  await shot('00-title');

  // ---- Enter → level 1's intro ------------------------------------------------------------------
  await h.eval(() => document.activeElement && document.activeElement.blur && document.activeElement.blur());
  await tap('Enter');
  s = await snap();
  check('Enter starts the story at level 1 (cutscenes off: straight to its intro)', s.state === 'intro' && s.mode === 'mission' && s.run.retries === 0 && s.run.level === 1 && s.run.levels === 4, `${s.state} ${s.mode} level ${s.run.level}`);
  await h.skip(10);
  let r = await rec();
  const card = r.calls.locationCard.find((c) => c[0]);
  check('location card at 0.25 s: the level and its name', !!card && card[1] === `LEVEL 1 · ${info.titles[0]}`, card ? card[1] : 'none');
  check('the block is lit as the setting says', (await h.eval(() => window.__G.atmos.time)) === (info.time === 'night' ? 'night' : 'day'));
  await h.skip(25);
  r = await rec();
  check("the Vault's first word at 0.9 s says where to go", r.hud.radio.length === 1 && r.hud.radio[0][1] === info.go[0] && r.hud.radio[0][0] === 'IPX VAULT', r.hud.radio.map((x) => x[1].slice(0, 20)).join('|'));
  await shot('01-intro');
  s = await until((x) => x.state === 'playing', 60, 2);
  r = await rec();
  const states = r.events.filter((e) => e[0] === 'game:state').map((e) => e[1].state);
  check('intro → playing after 2.4 s, card hidden', s.state === 'playing' && r.calls.locationCard[r.calls.locationCard.length - 1][0] === false, states.join(' '));

  // ---- the level's patrol -----------------------------------------------------------------------
  const patrol = async (i) =>
    h.eval((start) => {
      const G = window.__G;
      const list = G.enemies.list.filter((e) => e.alive);
      return {
        n: list.length,
        b: list.filter((e) => e.type === 'buzzard').length,
        unaware: list.every((e) => e.mode === 'patrol'),
        min: Math.min(...list.map((e) => Math.hypot(e.pos.x - start.x, e.pos.z - start.z))),
      };
    }, info.starts[i]);
  let p = await patrol(0);
  let want = info.levels[0].patrol;
  check(`level 1 patrol (${info.difficulty}): ${want.buzzard} Buzzards + ${want.goon} Goons at their posts, unaware, not on top of the start`, p.n === count(want) && p.b === want.buzzard && p.unaware && p.min > 9, p);
  s = await snap();
  r = await rec();
  check('phase "reach": the objective names the reel and the gold line, one marker', s.flow.phase === 'reach' && r.hud.objective.at(-1) === 'Get to reel 1 — follow the gold line' && JSON.stringify(r.calls.markers) === '["reel:1"]', { objective: r.hud.objective.at(-1), markers: r.calls.markers });

  // ---- the prompt: cone and range -----------------------------------------------------------------
  const [r1, r2, r3] = info.reels;
  await h.eval((q) => window.__fx.standAt(q.x, q.z, 1.6, 0.4, true), r1);
  await h.skip(3);
  r = await rec();
  check('no prompt with the back to the reel', r.hud.prompt === null, r.hud.prompt);
  await h.eval((q) => window.__fx.standAt(q.x, q.z, 3.2, 0.4, false), r1);
  await h.skip(3);
  r = await rec();
  check('no prompt out of range (3.2 m)', r.hud.prompt === null, r.hud.prompt);
  await h.eval((q) => window.__fx.standAt(q.x, q.z, 1.6, 0.4, false), r1);
  await h.skip(3);
  r = await rec();
  check('facing it within 2.2 m: "Hold E — Grab reel 1"', r.hud.prompt && r.hud.prompt.text === `Hold ${r.hud.prompt.glyph} — Grab reel 1`, r.hud.prompt);
  check('inside 0.9 m the facing is waived', await (async () => {
    await h.eval((q) => window.__fx.standAt(q.x, q.z, 0.6, 0.4, true), r1);
    await h.skip(3);
    return !!(await rec()).hud.prompt;
  })());
  // The other reels are not this level's business.
  await h.eval((q) => window.__fx.standAt(q.x, q.z, 1.2, 0.4, false), r2);
  await h.skip(3);
  r = await rec();
  check('a reel of a later level offers nothing yet', r.hud.prompt === null, r.hud.prompt);
  await h.eval((q) => window.__fx.standAt(q.x, q.z, 1.6, 0.4, false), r1);
  await h.skip(2);

  // ---- a broken hold decays ------------------------------------------------------------------------
  await h.key('KeyE', true);
  await h.skip(36); // 1.2 s → half
  s = await snap();
  r = await rec();
  check('holding Interact fills the bar linearly over 2.4 s', Math.abs(s.flow.progress - 0.5) < 0.05 && r.props.reel1 === 'grabbing' && r.progress.count > 30, `progress ${s.flow.progress.toFixed(3)} props ${r.props.reel1}`);
  await h.key('KeyE', false);
  await h.skip(6); // 0.2 s at 1.6 / s
  s = await snap();
  r = await rec();
  check('letting go drains it at 1.6 per second, the case goes back to live', Math.abs(s.flow.progress - (0.5 - 0.32)) < 0.06 && r.props.reel1 === 'live', `progress ${s.flow.progress.toFixed(3)}`);

  // ---- a level: its reel, its wave, level clear ---------------------------------------------------
  async function grab(reel, k) {
    await h.eval((q) => window.__fx.standAt(q.x, q.z, 1.4, 1.1, false), reel);
    await h.skip(2);
    const before = (await rec()).events.length;
    await h.key('KeyE', true);
    s = await until((x) => x.run.reels >= k, 120, 3);
    await h.key('KeyE', false);
    r = await rec();
    const done = r.events.slice(before).find((e) => e[0] === 'objective:done');
    check(`reel ${k}: objective:done {id:${reel.id}, index:${k}, total:3}`, !!done && done[1].id === reel.id && done[1].index === k && done[1].total === 3, done);
    check(`reel ${k}: the case is taken, HUD reels ${k}/3`, r.props[reel.id] === 'taken' && r.hud.reels[r.hud.reels.length - 1] === `${k}/3`, r.props[reel.id]);
    return before;
  }

  async function checkWave(k, before, standing) {
    const w = info.levels[k - 1].wave;
    const order = [];
    for (let b = w.buzzard, g = w.goon; b > 0 || g > 0; ) {
      if (b-- > 0) order.push(B);
      if (g-- > 0) order.push(Gn);
    }
    s = await snap();
    const lw = s.flow.lastWave;
    check(`wave ${k}: ${w.buzzard} Buzzards + ${w.goon} Goons, interleaved from a Buzzard`, lw && JSON.stringify(lw.order) === JSON.stringify(order), lw && lw.order.map((t) => t[0]).join(''));
    r = await rec();
    const left = standing + order.length;
    check(`wave ${k}: phase "clear", the objective counts ${left} Vultures left`, s.flow.phase === 'clear' && s.flow.left === left && r.hud.objective.at(-1) === `Clear the block — ${left} Vultures left`, { phase: s.flow.phase, left: s.flow.left, objective: r.hud.objective.at(-1) });
    // The banner direction, recomputed here from the queued spawn points.
    const dir = await h.eval(() => {
      const G = window.__G;
      let x = 0;
      let z = 0;
      for (const q of G.game.flow.queue) {
        x += q.pos.x - G.player.pos.x;
        z += q.pos.z - G.player.pos.z;
      }
      return { x, z };
    });
    const sector = SECTORS[((Math.round(Math.atan2(dir.x, -dir.z) / (Math.PI / 4)) % 8) + 8) % 8];
    const warn = r.hud.warn[r.hud.warn.length - 1];
    check(`wave ${k}: banner "Ambush — ${sector}" for 3.4 s`, warn && warn[0] === `Ambush — ${sector}` && warn[1] === 3.4 && lw.from === sector, warn);
    // Director: the patrol is put down before the wave arrives, so the alive cap holds no arrival back.
    await h.eval(() => window.__fx.killAll());
    await h.skip(2);
    s = await snap();
    r = await rec();
    check(`wave ${k}: the patrol down, the line counts the ${order.length} on their way`, s.flow.left === order.length && r.hud.objective.at(-1) === `Clear the block — ${order.length} Vultures left`, { left: s.flow.left, objective: r.hud.objective.at(-1) });
    // Arrivals: first 1.6 s after the grab, then every 0.85 s.
    s = await until((x) => x.flow.queue === 0, 600, 5);
    r = await rec();
    const spawns = r.events.slice(before).filter((e) => e[0] === 'enemy:spawn');
    const done = r.events.slice(before).find((e) => e[0] === 'objective:done');
    const t0 = done[2];
    const times = spawns.map((e) => e[2] - t0);
    const gaps = times.slice(1).map((t, i) => t - times[i]);
    const types = spawns.map((e) => e[1].enemy);
    check(`wave ${k}: all ${order.length} arrive, alerted, in order`, spawns.length === order.length && JSON.stringify(types) === JSON.stringify(order), types.join(','));
    check(`wave ${k}: first at +1.6 s, then every 0.85 s`, Math.abs(times[0] - 1.6) < 0.1 && gaps.every((g) => Math.abs(g - 0.85) < 0.1), `${times[0].toFixed(2)} / ${gaps.map((g) => g.toFixed(2)).join(' ')}`);
  }

  let arrived = null;
  /** Puts the level's Vultures down a few at a time, down to the last, and sees the level out. */
  async function clearLevel(k) {
    // Down to the last few: each of them gets a marker, and the line counts on.
    const kept = await h.eval((keep) => {
      const G = window.__G;
      const alive = G.enemies.list.filter((e) => e.alive);
      for (const e of alive.slice(keep)) G.enemies.damage(e, 10000, { point: e.pos.clone(), dir: new G.THREE.Vector3(0, 0, -1), part: 'body', from: 'player', weapon: 'chopper' });
      return Math.min(keep, alive.length);
    }, 2);
    await h.skip(3);
    s = await snap();
    r = await rec();
    check(`level ${k}: two left: "Clear the block — 2 Vultures left", a marker on each`, s.flow.left === kept && r.hud.objective.at(-1) === `Clear the block — ${kept} Vultures left` && JSON.stringify(r.calls.markers) === JSON.stringify(Array(kept).fill('foe:!')), { left: s.flow.left, objective: r.hud.objective.at(-1), markers: r.calls.markers });
    await h.eval(() => {
      const G = window.__G;
      const e = G.enemies.list.find((x) => x.alive);
      G.enemies.damage(e, 10000, { point: e.pos.clone(), dir: new G.THREE.Vector3(0, 0, -1), part: 'body', from: 'player', weapon: 'chopper' });
    });
    await h.skip(3);
    r = await rec();
    check(`level ${k}: "One Vulture left — finish it"`, r.hud.objective.at(-1) === 'One Vulture left — finish it', r.hud.objective.at(-1));
    const before = r.events.length;
    await h.eval(() => window.__fx.killAll());
    await h.skip(2);
    s = await snap();
    r = await rec();
    check(`level ${k}: the last one down: "Level clear", Rule safe, the line says so`, s.flow.phase === 'done' && s.player.invulnerable && (r.hud.warn.at(-1) || [])[0] === 'Level clear' && r.hud.objective.at(-1) === 'Level clear' && r.calls.stings.at(-1) === 'all', { phase: s.flow.phase, warn: r.hud.warn.at(-1), stings: r.calls.stings.slice(-2) });
    await h.skip(Math.round((info.clear - 0.8) / (1 / 30)));
    s = await snap();
    check(`level ${k}: still playing ${(info.clear - 0.8).toFixed(1)} s on, the picture not yet dark`, s.state === 'playing' && s.run.level === k && s.post.fade < 0.2, { state: s.state, fade: s.post.fade });
    s = await until((x) => x.run.level === k + 1, 60, 1);
    arrived = s; // the level as it was the moment it came up
    r = await rec();
    check(`level ${k + 1} comes up behind black, in its intro`, s.state === 'intro' && s.run.level === k + 1 && s.post.fade > 0.9 && s.player.alive && !s.player.invulnerable, { state: s.state, level: s.run.level, fade: s.post.fade });
    const next = info.levels[k].patrol;
    p = await patrol(k);
    check(`level ${k + 1}: its patrol at their posts (${next.buzzard} + ${next.goon}), unaware`, p.n === count(next) && p.b === next.buzzard && p.unaware && p.min > 9, p);
    const start = info.starts[k];
    check(`level ${k + 1}: Rule at its start, with full magazines`, Math.hypot(s.player.x - start.x, s.player.z - start.z) < 1.5 && (await h.eval(() => window.__G.weapon.slots.every((x) => x.mag === x.magSize))), { x: s.player.x, z: s.player.z });
    await h.skip(12);
    r = await rec();
    const loc = r.calls.locationCard.filter((c) => c[0]).pop();
    check(`level ${k + 1}: its name on the location card`, loc && loc[1] === `LEVEL ${k + 1} · ${info.titles[k]}`, loc);
    s = await until((x) => x.state === 'playing', 90, 2);
    r = await rec();
    check(`level ${k + 1}: the Vault says where to go`, r.hud.radio.some((x) => x[1] === info.go[k]));
    return before;
  }

  // Level 1.
  let before = await grab(r1, 1);
  await h.skip(20);
  await shot('02-wave1-banner');
  await checkWave(1, before, count(info.levels[0].patrol));
  await shot('03-wave1-arrived');

  // The truck before the last reel: refused, at most once per 8 s.
  await h.eval((q) => window.__fx.standAt(q.x, q.z, 0.4, 0, false), info.truck);
  await h.skip(4);
  r = await rec();
  const refusals = () => r.hud.message.filter((m) => m[0] === info.refuse);
  check('the truck refuses before all three reels: message for 3.5 s', refusals().length === 1 && refusals()[0][1] === 3.5 && (await snap()).state === 'playing', refusals());
  await shot('04-refusal');
  await h.skip(120); // 4 s more, still standing in it
  r = await rec();
  check('…and not again within 8 s', refusals().length === 1, `${refusals().length}`);
  await h.skip(150);
  r = await rec();
  check('…but again after 8 s if he stays', refusals().length === 2, `${refusals().length}`);
  await clearLevel(1);

  // Level 2.
  before = await grab(r2, 2);
  await checkWave(2, before, count(info.levels[1].patrol));
  await clearLevel(2);
  check('level 3 plays after dark', (await h.eval(() => window.__G.atmos.time)) === 'night');

  // Level 3: the last reel.
  before = await grab(r3, 3);
  r = await rec();
  check('the third reel: objective:all', r.events.slice(before).some((e) => e[0] === 'objective:all'));
  await checkWave(3, before, count(info.levels[2].patrol));

  // Radio lines, in order, behind each other (FIFO).
  await h.skip(90);
  r = await rec();
  const lines = r.hud.radio.map((x) => x[1]);
  const at = info.radio.map((t) => lines.indexOf(t));
  check('the three reel radio lines played in order', at.every((i) => i > 0) && at[0] < at[1] && at[1] < at[2], at.join(','));
  await clearLevel(3);

  // ---- level 4: the run to the truck --------------------------------------------------------------
  s = await snap();
  r = await rec();
  check('level 4: phase "truck", the objective and the one marker are the truck', s.flow.phase === 'truck' && r.hud.objective.at(-1) === 'Get to the IPX truck — follow the gold line' && JSON.stringify(r.calls.markers) === '["exit:IPX"]', { phase: s.flow.phase, objective: r.hud.objective.at(-1), markers: r.calls.markers });
  check(`pursuit armed as the level came up: budget ${info.budget}, the first one 3 s in`, arrived.flow.pursuitLeft === info.budget && arrived.flow.pursuitTimer > 2.5 && arrived.flow.pursuitTimer <= 3, `${arrived.flow.pursuitLeft} / ${arrived.flow.pursuitTimer.toFixed(2)}`);

  // Pursuit: nobody left → one extra arrival, then the next `pursuitEvery` later.
  await h.eval(() => window.__fx.killAll());
  await h.skip(2);
  const left0 = (await snap()).flow.pursuitLeft;
  s = await until((x) => x.flow.pursuitLeft < left0, 500, 2);
  check(`pursuit: with fewer than 4 alive, one more is queued (${left0} → ${left0 - 1} to come)`, left0 > 2 && s.flow.pursuitLeft === left0 - 1, `${s.flow.pursuitLeft} at timer ${s.flow.pursuitTimer.toFixed(2)}`);
  s = await until((x) => x.alive > 0, 40, 1);
  check('…and arrives 0.5 s later', s.alive === 1, `${s.alive}`);
  await h.skip(Math.round((info.every + 0.2) / (1 / 30)));
  s = await snap();
  check(`the next one ${info.every} s later (${left0 - 2} to come)`, s.flow.pursuitLeft === left0 - 2, `${s.flow.pursuitLeft}`);
  await shot('05-pursuit');

  // ---- extraction --------------------------------------------------------------------------------
  const evBefore = (await rec()).events.length;
  await h.eval((q) => window.__fx.standAt(q.x, q.z, 0.5, 0, false), info.truck);
  await h.skip(2);
  s = await snap();
  r = await rec();
  check('reaching the truck completes the run', s.state === 'complete' && r.events.slice(evBefore).some((e) => e[0] === 'extraction:reached'), s.state);
  check('player disabled and invulnerable, truck doors open', !s.player.enabled && s.player.invulnerable && r.props.truck === 'open', r.props.truck);
  await h.skip(10);
  r = await rec();
  check('radio cleared, then the done line', r.hud.radio[r.hud.radio.length - 1][1] === info.done, r.hud.radio.slice(-1)[0]);
  await h.skip(40);
  r = await rec();
  check('no debrief card before 3.3 s', !r.cards.some((c) => c[0] === 'complete'));
  await h.skip(60);
  s = await snap();
  r = await rec();
  const debrief = r.cards.filter((c) => c[0] === 'complete').pop();
  const expect = await h.eval(() => {
    const G = window.__G;
    const run = G.game.run;
    return { rating: G.config.flow.ratingPoints(run), kills: G.combat.stats.kills, time: run.time };
  });
  const d = debrief && debrief[1];
  check('debrief card after 3.3 s', !!d, r.cards.map((c) => c[0]).join(','));
  check('debrief data: 3/3 reels, level 4 of 4, retries 0, kills, accuracy, rating', d && d.reels === 3 && d.total === 3 && d.level === 4 && d.levels === 4 && d.retries === 0 && d.kills === expect.kills && d.rating === expect.rating && d.ratingName === info.ratings[expect.rating] && Math.abs(d.time - expect.time) < 0.01, d);
  check('the screen darkens to 0.72 and desaturates', s.post.fade > 0.6 && s.post.saturation < 0.8, s.post);
  await shot('06-debrief');

  // Every state change, in order.
  r = await rec();
  const seq = r.events.filter((e) => e[0] === 'game:state').map((e) => e[1].state).join(' ');
  check('state sequence: four levels, each intro → playing, then complete', seq === 'intro playing intro playing intro playing intro playing complete', seq);
  const resets = r.events.filter((e) => e[0] === 'game:reset');
  check('one game:reset {mode: mission}', resets.length === 1 && resets[0][1].mode === 'mission');
  await finish();
};
