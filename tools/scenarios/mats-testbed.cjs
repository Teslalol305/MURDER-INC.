// The stub testbed level dressed in the real materials: a handful of fixed views of the block.
//
//   node build.mjs --dev --only=mats --out=dist/dev-mats.html
//   node tools/shot.cjs dist/dev-mats.html --params "shot=1&nohud=1&noaudio=1&god=1" \
//        --scenario tools/scenarios/mats-testbed.cjs --timeout 600
//
// MATS_VIEWS=start,court limits the run; MATS_OUT changes the folder (default shots/mats).

const OUT = process.env.MATS_OUT || 'shots/mats';

/** name → ["x,y,z,lx,ly,lz", field of view] */
const VIEWS = {
  start: ['-40,1.68,8.6,-20,1.4,3', 74], // where the run begins: sidewalk, El columns, the avenue
  avenue: ['-22,1.7,0.5,10,1.2,-1', 74], // down the middle of the street under the El
  shop: ['-8,1.7,-7.5,-12,3.2,-13', 70], // the chop shop front and its sign
  court: ['20,1.7,-9,34,1.5,-22', 70], // through the chain-link into the cage
  lot: ['24,1.8,10,40,1.2,28', 70], // the lot and the truck
  over: ['-10,17,28,-4,1,-3', 60], // the block from above
  kerb: ['-36,0.9,6.2,-33,0.1,7.6', 60], // close on kerb, sidewalk and wet asphalt
  wall: ['-28,1.6,10.2,-26.5,1.5,12', 62], // close on a brick wall
};

module.exports = async (page, h) => {
  const wanted = (process.env.MATS_VIEWS || '').split(/[\s,]+/).filter(Boolean);
  const names = wanted.length ? wanted : Object.keys(VIEWS);
  await h.skip(20);
  for (const name of names) {
    if (!VIEWS[name]) throw new Error(`mats-testbed: no view called '${name}'`);
    const [cam, fov] = VIEWS[name];
    await h.eval((shot) => window.__setShot(shot), { cam, fov });
    await h.frames(2);
    await h.shot(`${OUT}/testbed-${name}.png`);
    console.error(`testbed: ${name}`);
  }
  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
  const stats = await h.stats();
  const mats = await h.eval(() => window.__G.mats.stats());
  console.error(`testbed: ${stats.programs} programs, ${stats.textures} textures, ${stats.calls} draw calls, mats ${JSON.stringify(mats)}`);
};
