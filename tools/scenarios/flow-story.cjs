// The story from the title to the debrief, played as a director: the opening cutscene, four levels
// (get to the reel along the guide line, hold Interact, clear out the wave; the last one is the run to
// the truck), the cutscenes between them (watched, skipped, paused), a death and its checkpoint, the
// closing scene and the card.
//
//   node build.mjs --dev --out=dist/dev-all.html
//   node tools/shot.cjs dist/dev-all.html --size 960x540 --params "q=test&noaudio=1" \
//        --scenario tools/scenarios/flow-story.cjs --timeout 900
//   FLOW_NOSHOTS=1 skips the pictures (shots/story/*.png).

const { setup } = require('./flow-lib.cjs');

const STEP = 1 / 30;
const steps = (secs) => Math.max(1, Math.round(secs / STEP));

module.exports = async (page, h) => {
  const { check, snap, rec, tap, until, finish } = await setup(page, h);
  const pictures = !process.env.FLOW_NOSHOTS;
  const shot = async (name) => {
    if (!pictures) return;
    await h.frames(1);
    await h.shot(`shots/story/${name}.png`);
  };
  await page.mouse.move(480, 270);

  /** What only the story has: the stage line, the objective, the guide line, the crates, the Vultures. */
  const story = () =>
    h.eval(() => {
      const G = window.__G;
      const g = G.game;
      const text = (sel) => {
        const n = document.querySelector(sel);
        return n ? n.textContent : '';
      };
      const shown = (sel) => {
        const n = document.querySelector(sel);
        return !!n && !n.hidden && getComputedStyle(n).display !== 'none';
      };
      return {
        stage: text('.hud-obj-label'),
        objective: window.__flow.hud.objective.at(-1) || '',
        guide: { shown: g.guide.shown, route: g.guide.route.length, hunting: g.guide.hunting },
        crates: g.pickups.crates,
        drops: g.pickups.list.filter((p) => p.live && p.kind === 'pouch').length,
        time: G.atmos.time,
        blind: G.enemies.list.filter((e) => e.alive).every((e) => e.mode === 'patrol'),
        cine: { on: shown('.cine'), place: text('.cine-place'), card: shown('.cine-card') ? [text('.cine-kicker'), text('.cine-title'), text('.cine-sub')] : null, key: text('.cine-key') },
        radio: text('.radio-speaker') + ': ' + text('.radio-line'),
        loc: shown('.loc') ? [text('.loc-place'), text('.loc-tag')] : null,
        slots: G.weapon.slots.map((x) => `${x.id}:${x.mag}/${x.reserve}`).join(' '),
        yaw: G.player.yaw,
      };
    });
  const T = await h.eval(() => {
    const G = window.__G;
    const d = G.config.flow.difficulty[G.game.difficulty];
    return {
      difficulty: G.game.difficulty,
      levels: d.levels,
      titles: G.config.story.levels.map((l) => G.config.text.story.levels[l.id].title),
      scenes: Object.fromEntries(Object.entries(G.config.story.scenes).map(([k, v]) => [k, v.shots.reduce((a, x) => a + x.secs, 0)])),
      reels: G.level.objectives.map((o) => ({ id: o.id, code: o.code, x: o.pos.x, z: o.pos.z })),
      truck: { x: G.level.extraction.pos.x, z: G.level.extraction.pos.z },
      clear: G.config.flow.story.levelClear,
      hold: G.config.flow.interact.hold,
    };
  });
  const count = (l) => l.buzzard + l.goon;

  // ---------------------------------------------------------------------------------------------
  // The title's button opens the story on a cutscene
  // ---------------------------------------------------------------------------------------------
  let s = await snap();
  check('boots to the title on the easy difficulty', s.state === 'title' && s.difficulty === 'hustler', { state: s.state, d: s.difficulty });
  await h.click('.title-actions .btn-primary');
  await h.skip(2);
  s = await snap();
  let st = await story();
  check('Story starts with the opening cutscene, level 1 dressed behind it', s.state === 'cutscene' && s.flow.scene === 'opening' && s.run.level === 1 && s.run.levels === 4, { state: s.state, scene: s.flow.scene, run: s.run });
  check('the level is set up before its pictures: Vultures at their posts, crates out, by day', s.alive === count(T.levels[0].patrol) && st.crates === 4 && st.time === 'day', { alive: s.alive, crates: st.crates, time: st.time });
  check('the screen is dressed for it: letterbox on, HUD off, no menu screen, Rule safe', st.cine.on && s.screen === 'none' && s.player.invulnerable && !s.player.enabled, { cine: st.cine, screen: s.screen });
  check('the skip control shows the key', st.cine.key === 'ENTER', st.cine.key);

  // A press in the first moment does nothing (the click that started the run may still be down).
  await tap('Enter');
  s = await snap();
  check('a skip press in the first 0.9 s is ignored', s.state === 'cutscene');

  await h.skip(steps(2.2));
  st = await story();
  check('the place line is typed on, the Vault speaks', /HOLLIS, QUEENS/i.test(st.cine.place) && /IPX VAULT: Rule, it's the Vault/.test(st.radio), { place: st.cine.place, radio: st.radio.slice(0, 60) });
  await shot('01-opening-wide');
  await h.skip(steps(7.5));
  await shot('02-opening-avenue');
  st = await story();
  check('nobody on the block has seen Rule while the camera is away', st.blind);

  // Paused mid-scene: the clock stops, and it carries on from where it was.
  const before = (await snap()).flow.sceneTime;
  await tap('Escape');
  s = await snap();
  check('Esc pauses a cutscene', s.state === 'paused' && s.screen === 'paused');
  await h.skip(steps(1));
  await h.click('.card-actions .btn-primary');
  await h.skip(2);
  s = await snap();
  check('Resume goes back into the scene where it stopped', s.state === 'cutscene' && Math.abs(s.flow.sceneTime - before) < 0.2, { state: s.state, t: s.flow.sceneTime, before });

  await h.skip(steps(6.4));
  st = await story();
  check('Rule answers, and the title card names the level', /RULE: Then they want me/.test(st.radio) && st.cine.card && st.cine.card[0] === 'LEVEL 1 OF 4' && st.cine.card[1] === 'THE AVENUE', { radio: st.radio, card: st.cine.card });
  await shot('03-opening-card');

  s = await until((x) => x.state !== 'cutscene', steps(6));
  st = await story();
  check('the scene ends by itself in the intro of level 1', s.state === 'intro' && !st.cine.on && s.player.enabled && !s.player.invulnerable, { state: s.state });
  await h.skip(steps(0.6));
  st = await story();
  check('the location card names the level and what it asks for', st.loc && /LEVEL 1/.test(st.loc[0]) && /first reel/i.test(st.loc[1]), st.loc);
  s = await until((x) => x.state === 'playing', steps(4));
  check('level 1 plays', s.state === 'playing' && s.flow.phase === 'reach');

  // ---------------------------------------------------------------------------------------------
  // Levels 1 to 3: the reel, the wave, level clear, the next cutscene
  // ---------------------------------------------------------------------------------------------
  for (let i = 0; i < 3; i++) {
    const n = i + 1;
    const reel = T.reels[i];
    s = await snap();
    st = await story();
    check(`level ${n}: the HUD says where and what`, st.stage === `LEVEL ${n} · ${T.titles[i]}` && new RegExp(`reel ${reel.code}`).test(st.objective), { stage: st.stage, objective: st.objective });
    check(`level ${n}: one marker, the level's reel`, JSON.stringify((await rec()).calls.markers) === JSON.stringify([`reel:${reel.code}`]), (await rec()).calls.markers);
    await h.skip(steps(0.7)); // the guide line searches a couple of times a second
    st = await story();
    check(`level ${n}: the guide line runs to it`, st.guide.shown >= 6 && st.guide.route >= 2 && !st.guide.hunting, st.guide);
    check(`level ${n}: its crates are out`, st.crates >= 4, st.crates);
    if (i === 0) await shot('04-level1-guide');
    if (i === 2) {
      check('level 3 plays after dark', st.time === 'night', st.time);
      await shot('09-level3-night');
    }

    // Level 2 is where Rule goes down once: back to its start, with what he had.
    if (i === 1) {
      const had = st.slots;
      await h.eval(() => {
        const G = window.__G;
        // Spend some of the rack first, so "what he had when it began" means something.
        G.weapon.restore({ current: 'chopper', guns: { chopper: { mag: 3, reserve: 0 }, nine: { mag: 15, reserve: Infinity }, ar15: { mag: 0, reserve: 0 }, switch9: { mag: 1, reserve: 0 }, rocket: { mag: 0, reserve: 0 } } });
        G.player.damage(1000, G.player.pos.clone().add(new G.THREE.Vector3(3, 1, 0)), 'bullet');
      });
      await h.skip(2);
      s = await snap();
      check('Rule goes down', s.state === 'dead' && !s.player.alive);
      s = await until((x) => x.screen === 'dead', steps(3));
      const card = await h.eval(() => ({
        button: document.querySelector('.card-actions .btn-primary .btn-label').textContent,
        hint: (document.querySelector('.card-hint') || {}).textContent || '',
        stats: [...document.querySelectorAll('.card-stats dt')].map((n) => n.textContent),
      }));
      check('the death card offers the level again and says so', card.button === 'Retry level' && /level 2/.test(card.hint) && card.stats.includes('Level'), card);
      await shot('07-death-card');
      await h.click('.card-actions .btn-primary');
      await h.skip(2);
      s = await snap();
      st = await story();
      check('Retry level: level 2 again, reel 1 still his, no cutscene, one retry on the sheet', s.state === 'intro' && s.run.level === 2 && s.run.reels === 1 && s.run.retries === 1 && s.player.alive, { state: s.state, run: s.run });
      check('with the rack he had when the level began', st.slots === had, { now: st.slots, had });
      check('and its Vultures back at their posts', s.alive === count(T.levels[1].patrol), s.alive);
      s = await until((x) => x.state === 'playing', steps(3));
    }

    // To the reel, and hold Interact.
    await h.eval((r) => window.__fx.standAt(r.x, r.z, 1.4, 0.4), reel);
    await h.skip(3);
    await h.key('KeyE', true);
    s = await until((x) => x.flow.phase !== 'reach', steps(T.hold + 1), 2);
    await h.key('KeyE', false);
    const wave = T.levels[i].wave;
    check(`level ${n}: the reel is his, the ambush is on its way`, s.flow.phase === 'clear' && s.run.reels === n && s.flow.queue === count(wave), { phase: s.flow.phase, reels: s.run.reels, queue: s.flow.queue });
    st = await story();
    const r = await rec();
    check(`level ${n}: "Ambush" banner and the count on the objective line`, /^Ambush — /.test((r.hud.warn.at(-1) || [''])[0]) && /Vultures left/.test(st.objective), { warn: r.hud.warn.at(-1), objective: st.objective });

    // Put them down as they come; the line counts down, the last few are marked, the level clears.
    let lowest = Infinity;
    let marked = false;
    for (let guard = 0; guard < 80; guard++) {
      await h.skip(steps(0.8));
      s = await snap();
      if (s.flow.phase !== 'clear') break;
      const m = (await rec()).calls.markers || [];
      if (m.length && m.every((x) => x === 'foe:!')) marked = true;
      lowest = Math.min(lowest, s.flow.left);
      await h.eval(() => window.__fx.killAll());
    }
    s = await snap();
    check(`level ${n}: the last Vultures were marked on the HUD`, marked);
    check(`level ${n}: cleared`, s.flow.phase === 'done' && s.alive === 0 && s.player.invulnerable, { phase: s.flow.phase, alive: s.alive });
    const r2 = await rec();
    check(`level ${n}: "Level clear"`, (r2.hud.warn.at(-1) || [''])[0] === 'Level clear' && r2.hud.objective.at(-1) === 'Level clear', r2.hud.warn.at(-1));
    if (i === 0) await shot('05-level1-clear');

    // The next level comes up behind black, then its cutscene.
    s = await until((x) => x.state === 'cutscene', steps(T.clear + 1), 2);
    st = await story();
    const next = ['shop', 'cage', 'truck'][i];
    check(`after level ${n}: the "${next}" scene, level ${n + 1} dressed behind it`, s.state === 'cutscene' && s.flow.scene === next && s.run.level === n + 1 && s.alive === count(T.levels[i + 1].patrol), { scene: s.flow.scene, level: s.run.level, alive: s.alive });
    if (i === 0) {
      // Watched to its title card, then left to end.
      await h.skip(steps(11.6));
      st = await story();
      check('the shop scene: its card', st.cine.card && st.cine.card[0] === 'LEVEL 2 OF 4' && st.cine.card[1] === 'THE CHOP SHOP', st.cine.card);
      await shot('06-shop-card');
      s = await until((x) => x.state !== 'cutscene', steps(5));
    } else {
      if (i === 1) {
        await h.skip(steps(1.4));
        st = await story();
        check('the cage scene opens after dark, with the clock on the place line', st.time === 'night' && /02:14/.test(st.cine.place), { time: st.time, place: st.cine.place });
        await shot('08-cage-scene');
      } else {
        await h.skip(steps(1.2));
        await shot('10-truck-scene');
      }
      // Skipped with the key.
      await tap(i === 1 ? 'Enter' : 'Space');
      s = await snap();
    }
    check(`level ${n + 1} begins`, s.state === 'intro' && s.run.level === n + 1, { state: s.state, level: s.run.level });
    st = await story();
    check(`level ${n + 1}: a breather for the guns (full magazines, at least a starting reserve)`, /chopper:30\/(1[5-9]\d|2\d\d) /.test(st.slots) && /rocket:1\/[3-6]$/.test(st.slots), st.slots);
    s = await until((x) => x.state === 'playing', steps(4));
  }

  // ---------------------------------------------------------------------------------------------
  // Level 4: the run to the truck, the closing scene, the debrief
  // ---------------------------------------------------------------------------------------------
  s = await snap();
  st = await story();
  check('level 4: all three reels, the truck is the objective and the marker', s.run.reels === 3 && s.flow.phase === 'truck' && /IPX truck/.test(st.objective) && JSON.stringify((await rec()).calls.markers) === JSON.stringify(['exit:IPX']), { objective: st.objective, markers: (await rec()).calls.markers });
  check('level 4: guards at the truck, a pursuit to come', s.alive === count(T.levels[3].patrol) && s.flow.pursuitLeft > 0, { alive: s.alive, pursuit: s.flow.pursuitLeft });
  await h.skip(steps(0.7));
  st = await story();
  check('level 4: the guide line runs to the truck', st.guide.shown >= 6, st.guide);
  await shot('11-level4-guide');
  await h.eval((t) => window.__fx.standAt(t.x, t.z, 0.5, 0), T.truck);
  await h.skip(3);
  s = await snap();
  st = await story();
  check('at the truck: the closing scene, the block gone quiet', s.state === 'cutscene' && s.flow.scene === 'ending' && s.alive === 0 && (await rec()).props.truck === 'open', { state: s.state, scene: s.flow.scene, alive: s.alive });
  await h.skip(steps(8.6));
  st = await story();
  check('the closing card', st.cine.card && st.cine.card[1] === 'MURDER INC.' && /RULE: It always was/.test(st.radio), { card: st.cine.card, radio: st.radio });
  await shot('12-ending-card');
  s = await until((x) => x.state === 'complete', steps(6));
  check('then the debrief', s.state === 'complete');
  s = await until((x) => x.screen === 'complete', steps(3));
  const card = (await rec()).cards.at(-1);
  check('the debrief card: four levels, one retry', card && card[0] === 'complete' && card[1].level === 4 && card[1].retries === 1 && card[1].reels === 3, card && card[1]);
  await shot('13-debrief');

  // "Run it back" opens the story again from its first scene.
  await h.click('.card-actions .btn-primary');
  await h.skip(2);
  s = await snap();
  check('Run it back: the story from the top', s.state === 'cutscene' && s.flow.scene === 'opening' && s.run.level === 1 && s.run.reels === 0 && s.run.retries === 0, { state: s.state, run: s.run });

  await finish();
};
