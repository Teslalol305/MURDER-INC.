// A whole Story run by script, from the title screen to the debrief, checked against the flow rules.
//
//   node build.mjs --dev --only=game --out=dist/dev-flow.html
//   node tools/shot.cjs dist/dev-flow.html --params "q=low" --timeout 600 --scenario tools/scenarios/flow-mission.cjs
//
// Title fly-through → Enter → full intro (location card by time of day, intro radio) → starting patrol →
// the facing cone and the range of the reel prompt → a broken hold that decays → three reels grabbed
// with held Interact, each with its wave (composition, interleaving, stagger, banner direction, radio
// line) → the refusal at the truck before the last reel → pursuit → extraction → debrief card data.
// FLOW_NOSHOTS=1 in the environment skips the screenshots (checks only).
// DIRECTOR: the player is moved with player.reset and enemies are killed through enemies.damage.

'use strict';

const { setup } = require('./flow-lib.cjs');

const OUT = 'shots/flow/mission-';
const DT = 0.0333;
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
    return {
      reels: G.level.objectives.map((o) => ({ id: o.id, code: o.code, x: o.pos.x, z: o.pos.z })),
      truck: { x: G.level.extraction.pos.x, z: G.level.extraction.pos.z },
      start: { x: G.level.playerStart.pos.x, z: G.level.playerStart.pos.z },
      text: G.config.text,
      waves: G.config.flow.difficulty.boss.waves,
      time: G.settings.get('time'),
      byTime: G.config.text.location.byTime,
      radio: G.config.text.radio.reel.map((l) => l.text),
      done: G.config.text.radio.done.text,
      refuse: G.config.text.prompts.refuse,
    };
  });

  // ---- title ------------------------------------------------------------------------------------
  let s = await snap();
  check('boots to the title with the player disabled and a 50° camera', s.state === 'title' && !s.player.enabled && s.fov === 50, `${s.state} fov ${s.fov}`);
  const cam0 = s.cam;
  await h.skip(90);
  s = await snap();
  check('the title camera flies the cinematic path', Math.hypot(s.cam[0] - cam0[0], s.cam[2] - cam0[2]) > 1, `${cam0} → ${s.cam}`);
  check('the title fades in from black at the loop start', s.post.fade < 0.2, `fade ${s.post.fade.toFixed(2)}`);
  await shot('00-title');

  // ---- Enter → intro ----------------------------------------------------------------------------
  await h.eval(() => document.activeElement && document.activeElement.blur && document.activeElement.blur());
  await tap('Enter');
  s = await snap();
  check('Enter starts a Story run with the full intro', s.state === 'intro' && s.mode === 'mission' && s.run.retries === 0, `${s.state} ${s.mode}`);
  await h.skip(10);
  let r = await rec();
  const card = r.calls.locationCard.find((c) => c[0]);
  const wantPlace = info.byTime[info.time === 'night' ? 'night' : 'day'];
  check('location card at 0.25 s, by time of day', !!card && card[1] === wantPlace, card ? card[1] : 'none');
  check('atmos.setTime got the setting on reset', r.calls.setTime.length > 0 && r.calls.setTime[r.calls.setTime.length - 1] === (info.time || 'day'), r.calls.setTime.join(','));
  await h.skip(25);
  r = await rec();
  check('intro radio line at 0.9 s', r.hud.radio.length === 1 && r.hud.radio[0][1] === info.text.radio.intro.text && r.hud.radio[0][0] === 'IPX VAULT', r.hud.radio.map((x) => x[1].slice(0, 20)).join('|'));
  await shot('01-intro');
  s = await until((x) => x.state === 'playing', 60, 2);
  r = await rec();
  const states = r.events.filter((e) => e[0] === 'game:state').map((e) => e[1].state);
  check('intro → playing after 2.4 s, card hidden', s.state === 'playing' && r.calls.locationCard[r.calls.locationCard.length - 1][0] === false, states.join(' '));

  // ---- patrol -----------------------------------------------------------------------------------
  const patrol = await h.eval(() => {
    const G = window.__G;
    const st = G.level.playerStart.pos;
    const list = G.enemies.list.filter((e) => e.alive);
    return { n: list.length, b: list.filter((e) => e.type === 'buzzard').length, min: Math.min(...list.map((e) => Math.hypot(e.pos.x - st.x, e.pos.z - st.z))) };
  });
  check('Boss starting patrol: 2 Buzzards + 4 Goons, 32 m or more from the start', patrol.n === 6 && patrol.b === 2 && patrol.min >= 31.9, patrol);

  // ---- the prompt: cone and range -----------------------------------------------------------------
  const [r1, r2, r3] = info.reels;
  await h.eval((p) => window.__fx.standAt(p.x, p.z, 1.6, 0.4, true), r1);
  await h.skip(3);
  r = await rec();
  check('no prompt with the back to the reel', r.hud.prompt === null, r.hud.prompt);
  await h.eval((p) => window.__fx.standAt(p.x, p.z, 3.2, 0.4, false), r1);
  await h.skip(3);
  r = await rec();
  check('no prompt out of range (3.2 m)', r.hud.prompt === null, r.hud.prompt);
  await h.eval((p) => window.__fx.standAt(p.x, p.z, 1.6, 0.4, false), r1);
  await h.skip(3);
  r = await rec();
  check('facing it within 2.2 m: "Hold E — Grab reel 1"', r.hud.prompt && r.hud.prompt.text === `Hold ${r.hud.prompt.glyph} — Grab reel 1`, r.hud.prompt);
  check('inside 0.9 m the facing is waived', await (async () => {
    await h.eval((p) => window.__fx.standAt(p.x, p.z, 0.6, 0.4, true), r1);
    await h.skip(3);
    return !!(await rec()).hud.prompt;
  })());
  await h.eval((p) => window.__fx.standAt(p.x, p.z, 1.6, 0.4, false), r1);
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

  // ---- three reels and their waves ---------------------------------------------------------------
  const kills0 = (await h.eval(() => window.__fx.killAll()));
  check('director: the patrol is cleared before the first wave', kills0 === 6, `${kills0}`);

  async function grab(reel, k) {
    await h.eval((p) => window.__fx.standAt(p.x, p.z, 1.4, 1.1, false), reel);
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

  async function checkWave(k, before) {
    const w = info.waves[k - 1];
    const want = [];
    for (let b = w.buzzard, g = w.goon; b > 0 || g > 0; ) {
      if (b-- > 0) want.push(B);
      if (g-- > 0) want.push(Gn);
    }
    s = await snap();
    const lw = s.flow.lastWave;
    check(`wave ${k}: ${w.buzzard} Buzzards + ${w.goon} Goons, interleaved from a Buzzard`, lw && JSON.stringify(lw.order) === JSON.stringify(want), lw && lw.order.map((t) => t[0]).join(''));
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
    r = await rec();
    const warn = r.hud.warn[r.hud.warn.length - 1];
    check(`wave ${k}: banner "Contact — ${sector}" for 3.4 s`, warn && warn[0] === `Contact — ${sector}` && warn[1] === 3.4 && lw.from === sector, warn);
    // Arrivals: first 1.6 s after the grab, then every 0.85 s.
    s = await until((x) => x.flow.queue === 0, 600, 5);
    r = await rec();
    const spawns = r.events.slice(before).filter((e) => e[0] === 'enemy:spawn');
    const done = r.events.slice(before).find((e) => e[0] === 'objective:done');
    const t0 = done[2];
    const times = spawns.map((e) => e[2] - t0);
    const gaps = times.slice(1).map((t, i) => t - times[i]);
    const types = spawns.map((e) => e[1].enemy);
    check(`wave ${k}: all ${want.length} arrive, alerted, in order`, spawns.length === want.length && JSON.stringify(types) === JSON.stringify(want), types.join(','));
    check(`wave ${k}: first at +1.6 s, then every 0.85 s`, Math.abs(times[0] - 1.6) < 0.1 && gaps.every((g) => Math.abs(g - 0.85) < 0.1), `${times[0].toFixed(2)} / ${gaps.map((g) => g.toFixed(2)).join(' ')}`);
  }

  let before = await grab(r1, 1);
  r = await rec();
  check('objective → "Two reels left"', r.hud.objective[r.hud.objective.length - 1] === 'Two reels left', r.hud.objective.slice(-1)[0]);
  await h.skip(20);
  await shot('02-wave1-banner');
  await checkWave(1, before);
  await shot('03-wave1-arrived');
  await h.eval(() => window.__fx.killAll());

  // The truck before the last reel: refused, at most once per 8 s.
  await h.eval((p) => window.__fx.standAt(p.x, p.z, 0.4, 0, false), info.truck);
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

  before = await grab(r2, 2);
  r = await rec();
  check('objective → "Last reel"', r.hud.objective[r.hud.objective.length - 1] === 'Last reel');
  await checkWave(2, before);
  await h.eval(() => window.__fx.killAll());

  before = await grab(r3, 3);
  r = await rec();
  const tail = r.events.slice(before);
  check('the third reel: objective:all, "Get to the IPX truck"', tail.some((e) => e[0] === 'objective:all') && r.hud.objective[r.hud.objective.length - 1] === 'Get to the IPX truck');
  s = await snap();
  check('pursuit armed: budget 8, first in 12 s', s.flow.pursuitLeft === 8 && Math.abs(s.flow.pursuitTimer - 12) < 0.3, `${s.flow.pursuitLeft} / ${s.flow.pursuitTimer.toFixed(2)}`);
  await checkWave(3, before);

  // Radio lines, in order, behind each other (FIFO).
  r = await rec();
  const lines = r.hud.radio.map((x) => x[1]);
  const at = info.radio.map((t) => lines.indexOf(t));
  check('the three reel radio lines played in order', at.every((i) => i > 0) && at[0] < at[1] && at[1] < at[2], at.join(','));

  // Pursuit: nobody left → one extra arrival, then the next 5.5 s later.
  await h.eval(() => window.__fx.killAll());
  s = await until((x) => x.flow.pursuitLeft < 8, 400, 3);
  check('pursuit: with fewer than 4 alive, one more is queued (budget 7)', s.flow.pursuitLeft === 7, `${s.flow.pursuitLeft} at timer ${s.flow.pursuitTimer.toFixed(2)}`);
  s = await until((x) => x.alive > 0, 40, 1);
  check('…and arrives 0.5 s later', s.alive === 1, `${s.alive}`);
  await h.skip(170); // 5.7 s
  s = await snap();
  check('the next one 5.5 s later (budget 6)', s.flow.pursuitLeft === 6, `${s.flow.pursuitLeft}`);
  await shot('05-pursuit');

  // ---- extraction --------------------------------------------------------------------------------
  const evBefore = (await rec()).events.length;
  await h.eval((p) => window.__fx.standAt(p.x, p.z, 0.5, 0, false), info.truck);
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
  const want = await h.eval(() => {
    const G = window.__G;
    const run = G.game.run;
    return { rating: G.config.flow.ratingPoints(run), kills: G.combat.stats.kills, time: run.time };
  });
  const d = debrief && debrief[1];
  check('debrief card after 3.3 s', !!d, r.cards.map((c) => c[0]).join(','));
  check('debrief data: 3/3 reels, retries 0, kills, accuracy, rating', d && d.reels === 3 && d.total === 3 && d.retries === 0 && d.kills === want.kills && d.rating === want.rating && d.ratingName === info.text.ratings[want.rating] && Math.abs(d.time - want.time) < 0.01, d);
  check('the screen darkens to 0.72 and desaturates', s.post.fade > 0.6 && s.post.saturation < 0.8, s.post);
  await shot('06-debrief');

  // Every state change, in order.
  r = await rec();
  const seq = r.events.filter((e) => e[0] === 'game:state').map((e) => e[1].state).join(' ');
  check('state sequence intro → playing → complete', seq === 'intro playing complete', seq);
  const resets = r.events.filter((e) => e[0] === 'game:reset');
  check('one game:reset {mode: mission}', resets.length === 1 && resets[0][1].mode === 'mission');
  await finish();
};
