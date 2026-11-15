// The real block (combined build) seen through the material library: fixed views of the avenue, the
// facades, the kerb and the walls, by day and (MATS_TIME=night or both) by night.
//
//   node build.mjs --dev --out=dist/dev-mats-full.html
//   node tools/shot.cjs dist/dev-mats-full.html --params "autostart=1&q=low&nohud=1&noaudio=1&god=1" \
//        --scenario tools/scenarios/mats-block.cjs --timeout 900
//
// MATS_VIEWS=start,kerb limits the run; MATS_TIME=day|night|both (default day); MATS_OUT (shots/mats/block).

const OUT = process.env.MATS_OUT || 'shots/mats/block';

/** name → ["x,y,z,lx,ly,lz", field of view]. The road runs along x (kerbs at z = ±7, fronts at ±11); the run starts at (−37.4, 8.2). */
const VIEWS = {
  start: ['-37.4,1.75,8.2,-20,1.5,5.5', 74], // where the run begins, looking east along the avenue
  north: ['-37,1.75,8,-28,5.5,-11', 74], // across the avenue: the north fronts, signs, facades, windows
  kerb: ['-35,1.25,8.6,-33.6,0.1,6.6', 62], // close on kerb, sidewalk slabs and asphalt
  over: ['-10,17,28,-4,1,-3', 60], // the block from above
};

module.exports = async (page, h) => {
  const wanted = (process.env.MATS_VIEWS || '').split(/[\s,]+/).filter(Boolean);
  const names = wanted.length ? wanted : Object.keys(VIEWS);
  const time = process.env.MATS_TIME || 'day';
  const times = time === 'both' ? ['day', 'night'] : [time];
  await h.skip(20);
  for (const t of times) {
    await h.eval((name) => {
      const G = window.__G;
      if (G.atmos && typeof G.atmos.setTime === 'function') G.atmos.setTime(name);
    }, t);
    await h.skip(3);
    for (const name of names) {
      if (!VIEWS[name]) throw new Error(`mats-block: no view called '${name}'`);
      const [cam, fov] = VIEWS[name];
      await h.eval((shot) => window.__setShot(shot), { cam, fov });
      await h.frames(2);
      await h.shot(`${OUT}/${t}-${name}.png`);
      console.error(`block: ${t} ${name}`);
    }
  }
  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
  const stats = await h.stats();
  const mats = await h.eval(() => window.__G.mats.stats());
  console.error(`block: ${stats.programs} programs, ${stats.textures} textures, ${stats.calls} draw calls, mats ${JSON.stringify(mats)}`);
};
