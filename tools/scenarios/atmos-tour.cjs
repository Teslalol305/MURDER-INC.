// Atmosphere tour: fixed cameras around the block, one picture each.
//
//   node build.mjs --dev --only=atmos,level,mats,props --out=dist/dev-atmos.html
//   node tools/shot.cjs dist/dev-atmos.html --params "shot=1&nohud=1" --scenario tools/scenarios/atmos-tour.cjs
//
// Views come from the level itself (the player start, the title fly-through, the reels, the truck) plus
// a few fixed ones, so the tour works on the testbed level and on the real block alike.
//
// Environment:
//   ATMOS_VIEWS=start,p3,shop     only these views (default: a representative dozen; `all` for every one)
//   ATMOS_TAG=medium              file name suffix: shots/atmos/tour-<view>-<tag>.png
//   ATMOS_SKIP=600                simulate this many steps first (e.g. to let a train come and go)
//   ATMOS_TIME=night              switch the rig first (atmos.setTime); the default is the user's setting (day)
//   ATMOS_TRAIN=1                 send a train first, overhead when the views are taken (dir +1 / -1)
//
// Add `q=medium`, `bloom=0`, `post=0` … to --params to compare presets. Look at the pictures.

const OUT = 'shots/atmos';

// name → [x, y, z, lookX, lookY, lookZ, fov]
const FIXED = {
  shop: [-12, 1.68, -12.6, -9.5, 1.3, -21.5, 74], // just inside the roll door
  shopback: [-3, 1.68, -27, -16, 2.2, -18, 74], // from the back of the shop toward the door
  cage: [30, 1.68, -13.6, 36, 2, -24, 74], // the court and its floods
  lot: [26, 1.68, 14.5, 42, 3, 31, 74], // the parking lot, out past the fence
  alley: [8.5, 1.68, -12.5, 8.5, 3, -30, 74],
  vacant: [-10, 1.68, 12.5, -10, 2.4, 25, 74],
  lane: [-13, 1.68, 28.5, 20, 2, 28.6, 74],
  east: [38, 1.68, -8.6, 130, 3.5, 0, 74], // past the roadblock, where the avenue runs on
  westend: [-34, 1.68, -8.6, -140, 5, 0, 74], // the same to the west
  moon: [28, 1.68, 14, 80, 22, 40, 60], // up at the sky from the lot
  over: [-10, 17, 28, -4, 1, -3, 60], // the whole block from above
  far: [-14, 40, 70, 10, 0, -10, 55], // higher and further: the city around it
  top: [-4, 52, 14, -4, 0, -1, 62], // straight down onto the avenue: where the sun and the El's shadow fall
  shopdoor: [-9, 1.68, -4, -9, 1.5, -20, 74], // into the shop from the street, through the roll door
  shopout: [-9, 1.68, -24, -9, 1.6, 0, 74], // from inside the shop, out through the roll door
  avwest: [20, 1.68, 2, -60, 3, 1, 74], // mid-avenue looking west (into the sun)
  aveast: [-24, 1.68, -2, 60, 3, -1, 74], // mid-avenue looking east
  skywest: [0, 26, 0, -200, 50, -20, 70], // above the roofs: the glow over the far skyline
  skyeast: [0, 26, 0, 200, 50, 60, 70], // and the moon
};
const DEFAULT = ['start', 'p0', 'p2', 'p4', 'p8', 'p10', 'p12', 'shop', 'cage', 'lot', 'east', 'skywest'];

module.exports = async (page, h) => {
  const views = { ...FIXED, ...(await h.eval(() => {
    const L = window.__G.level;
    const out = {};
    const s = L.playerStart;
    out.start = [s.pos.x, s.pos.y + 1.68, s.pos.z, s.pos.x - Math.sin(s.yaw) * 20, s.pos.y + 1.6, s.pos.z - Math.cos(s.yaw) * 20, 74];
    L.cinematicPath.forEach((p, i) => {
      out[`p${i}`] = [p.pos.x, p.pos.y, p.pos.z, p.look.x, p.look.y, p.look.z, 50];
    });
    L.objectives.forEach((o, i) => {
      out[`reel${i + 1}`] = [o.pos.x - 6, o.pos.y + 1.68, o.pos.z + 5, o.pos.x, o.pos.y + 0.8, o.pos.z, 74];
    });
    const e = L.extraction.pos;
    out.truck = [e.x - 8, e.y + 1.68, e.z - 5, e.x + 3, e.y + 1.4, e.z, 74];
    return out;
  })) };

  const asked = process.env.ATMOS_VIEWS || DEFAULT.join(',');
  const wanted = asked === 'all' ? Object.keys(views) : asked.split(',').map((s) => s.trim()).filter(Boolean);
  const tag = process.env.ATMOS_TAG ? `-${process.env.ATMOS_TAG}` : '';
  const skip = Number(process.env.ATMOS_SKIP || 0);
  if (process.env.ATMOS_TIME) await h.eval((t) => window.__G.atmos.setTime(t), process.env.ATMOS_TIME);
  if (skip > 0) await h.skip(skip);
  if (process.env.ATMOS_TRAIN) await h.eval((d) => window.__G.atmos.passTrain(d, 1), Number(process.env.ATMOS_TRAIN));

  for (const name of wanted) {
    const v = views[name];
    if (!v) throw new Error(`unknown view '${name}' (have: ${Object.keys(views).join(', ')})`);
    await h.eval(([cam, fov]) => window.__setShot({ cam, fov }), [v.slice(0, 6).join(','), v[6]]);
    await h.skip(75); // the interior nudge and the lamp lights follow the camera: let them settle
    await h.eval(() => window.__G.atmos.settleLights && window.__G.atmos.settleLights());
    await h.frames(2); // one for the shadow map, one to look at
    await h.shot(`${OUT}/tour-${name}${tag}.png`);
  }

  const info = await h.eval(() => ({ atmos: window.__G.atmos.stats ? window.__G.atmos.stats() : null, errors: window.__errors.length }));
  console.error(`atmos tour: ${JSON.stringify(info.atmos)}`);
  if (info.errors) throw new Error(`page errors: ${(await h.errors())[0]}`);
};
