// Props in place: a few fixed views of the real block (cars on the avenue, reel 1, the IPX truck) by day.
//
//   node build.mjs --dev --out=dist/dev-props-full.html
//   node tools/shot.cjs dist/dev-props-full.html --params "autostart=1&q=low&god=1&noaudio=1&nohud=1" --timeout 900 \
//        --scenario tools/scenarios/props-street.cjs
//
// PROPS_VIEWS=avenue,reel,truck picks views; PROPS_OUT=shots/props/street is the output directory.

const path = require('node:path');

const OUT = process.env.PROPS_OUT || 'shots/props/street';
const VIEWS = {
  // From the west end at standing eye height, down the parked lanes.
  avenue: () => '-30,1.68,1.5,-12,0.9,-2',
  // Reel 1 from a standing player 7 m away.
  reel: (G) => {
    const o = G.level.objectives[0];
    return o ? `${o.pos.x - 6},1.68,${o.pos.z + 4},${o.pos.x},0.6,${o.pos.z}` : '';
  },
  // The extraction truck from across the lot.
  truck: (G) => {
    const e = G.level.extraction;
    return e ? `${e.pos.x - 9},2.2,${e.pos.z - 6},${e.pos.x},1.2,${e.pos.z}` : '';
  },
};

module.exports = async (page, h) => {
  const wanted = (process.env.PROPS_VIEWS || 'avenue,reel,truck').split(',').map((s) => s.trim());
  await h.eval(() => window.__G.enemies.clear && window.__G.enemies.clear());
  for (const name of wanted) {
    const cam = await h.eval(`(${VIEWS[name].toString()})(window.__G)`);
    if (!cam) continue;
    await h.eval((c) => window.__setShot({ cam: c, fov: 60 }), cam);
    await h.frames(2);
    await h.shot(path.join(OUT, `${name}.png`));
  }
  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors.join(' | ')}`);
};
