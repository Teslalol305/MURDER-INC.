// Audio next to every real module: unlock, let the queue finish, play for a few seconds (walk, fire, reload,
// an enemy wave), and check the sounds got voices, the loops are up and nothing logged an error.
//
//   node build.mjs --dev --out=dist/dev-audio-full.html
//   node tools/shot.cjs dist/dev-audio-full.html --params "autostart=1&q=test&god=1" --scenario tools/scenarios/audio-full.cjs --timeout 500 --size 640x360

const OUT = 'shots/audio';

module.exports = async (page, h) => {
  await h.frames(2);
  await h.eval(() => window.__G.audio.unlock());
  const t0 = Date.now();
  while ((await h.eval(() => window.__G.audio.debug.queued)) > 0 && Date.now() - t0 < 200000) await h.wait(1000);
  const counts = await h.eval(() => {
    const G = window.__G;
    const c = G.audio.debug.counts();
    c.played = {};
    c.refused = {};
    if (G.game && G.game.debugGrab) G.game.debugGrab();
    return { queued: G.audio.debug.queued, mb: +(G.audio.debug.bytes / 1e6).toFixed(1) };
  });
  console.log('[audio-full] rendered:', JSON.stringify(counts), 'in', Math.round((Date.now() - t0) / 1000), 's');
  await page.mouse.move(320, 180);
  await h.key('KeyW', true);
  await h.skip(40);
  await h.key('Mouse0', true);
  await h.skip(25);
  await h.key('Mouse0', false);
  await h.key('KeyW', false);
  await h.key('KeyR', true);
  await h.skip(2);
  await h.key('KeyR', false);
  await h.skip(120);
  await h.frames(2);
  await h.shot(`${OUT}/full-after-play.png`);
  const r = await h.eval(() => {
    const A = window.__G.audio;
    return { counts: A.debug.counts(), loops: A.debug.loops().filter((l) => l.playing).map((l) => l.name), state: window.__G.game.state };
  });
  console.log('[audio-full] played:', JSON.stringify(r.counts));
  console.log('[audio-full] loops:', JSON.stringify(r.loops), 'state', r.state);
  const errs = (await h.errors()).map(String);
  const ours = errs.filter((e) => /audio/i.test(e));
  if (errs.length) console.log('[audio-full] page errors:', JSON.stringify(errs).slice(0, 600));
  if (ours.length) throw new Error(`audio errors: ${JSON.stringify(ours).slice(0, 400)}`);
  if (!Object.keys(r.counts.played).some((k) => /^(chopper|nine)_shot$/.test(k))) throw new Error('no gunshot was played');
};
