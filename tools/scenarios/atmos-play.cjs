// The player's own view (HUD and viewmodel on) a few seconds into a run, by day, then by night.
//   node tools/shot.cjs dist/dev-atmos-full.html --params "autostart=1&q=low&god=1" --scenario tools/scenarios/atmos-play.cjs
module.exports = async (page, h) => {
  await h.skip(90);
  await h.frames(2);
  await h.shot('shots/atmos/play-day.png');
  await h.eval(() => window.__G.atmos.setTime('night'));
  await h.skip(10);
  await h.frames(2);
  await h.shot('shots/atmos/play-night.png');
  const s = await h.eval(() => ({ time: __G.atmos.time, stats: __G.atmos.stats(), calls: __stats().calls, tris: __stats().triangles, errors: __errors }));
  console.error('atmos play: ' + JSON.stringify(s).slice(0, 1500));
  if (s.errors.length) throw new Error(s.errors[0]);
};
