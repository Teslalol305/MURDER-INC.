// Fixed-camera tour of the block: one screenshot per place the level has to get right.
//
//   node build.mjs --dev --only=level --out=dist/dev-level.html
//   node tools/shot.cjs dist/dev-level.html --params "autostart=1&q=test&god=1&nohud=1" \
//        --scenario tools/scenarios/level-tour.cjs --timeout 600
//
//   LEVEL_TOUR=el,shop,cage   only the views whose name contains one of these words
//   LEVEL_TOUR_DIR=shots/level/real   where the pictures go (default shots/level)
//
// It also checks the things a picture cannot show: no page errors, the contract counts, the draw calls.

'use strict';

const path = require('node:path');

// name, camera "x,y,z,lookX,lookY,lookZ", field of view
const VIEWS = [
  ['start', '-37.4,1.83,8.15,-20,1.7,7.2', 74],
  ['start-back', '-33,2.2,5,-44,3.4,2', 70],
  ['avenue-east', '-27.4,1.7,1.5,10,2.6,0.5', 70],
  ['under-el', '-14,1.2,-2.6,6,6.2,0.8', 78],
  ['el-side', '-21,3,-10.3,-2,6.4,3', 70],
  ['reel1', '-10.5,2.4,6.2,-4,0.8,0.6', 68],
  ['reel1-north', '-1,2.6,-7.6,-5,0.8,1.5', 70],
  ['shop-front', '-11,1.75,-3.2,-12,2.4,-14', 74],
  ['shop-in', '-12.5,1.75,-12.6,-6,1.6,-23', 78],
  ['shop-east', '4.6,1.75,-13.4,-12,1.9,-23', 78],
  ['shop-mezz', '-19.5,4.55,-26,-6,1.2,-19', 78],
  ['shop-office', '-16.4,4.4,-28.6,-23,3.9,-29.4', 78],
  ['alley', '8.4,1.75,-12.4,8.6,2.4,-31', 72],
  ['alley-out', '8.5,1.75,-28.5,8.4,2.2,-8', 72],
  ['north-walk', '-26,1.83,-9,10,2.2,-9.4', 70],
  ['south-walk', '-28,1.83,9,10,2.2,9', 70],
  ['shed', '-3.2,1.83,8.6,12,2.6,9.4', 74],
  ['shed-deck', '2.2,4.63,9.4,-8,1.2,-4', 78],
  ['shed-deck-east', '6,4.63,9.6,30,2.4,2', 74],
  ['vacant', '-10,1.75,12.4,-13.5,3.6,20', 78],
  ['mural', '-5.2,1.9,19,-16,4.4,18.2', 74],
  ['lane', '-13,1.75,28.6,20,1.9,28.4', 70],
  ['lane-west', '20.5,1.75,28.5,-12,1.9,28.6', 70],
  ['cage-gate', '34.5,1.83,-8.4,35.2,1.4,-22.5', 74],
  ['cage-in', '27.5,1.75,-15,38,1.2,-25', 78],
  ['cage-reel', '39.5,2.2,-18.2,34.8,0.9,-22.8', 70],
  ['cut', '23.5,1.75,-11.6,23.6,2,-33', 72],
  ['lot-entry', '31.8,1.83,8.6,36,2,26', 74],
  ['lot-truck', '33.8,1.75,26.2,41.5,1.6,30', 70],
  ['lot-north', '43.5,1.75,31.5,30,3.4,12', 78],
  ['roadblock', '30,1.75,1,45,2.2,0.2', 70],
  ['west-end', '-33,1.75,-1,-46,2.6,0.4', 74],
  ['roofline', '6,13,3,-8,5,-22', 62],
  ['overview', '0,104,1.2,0,0,0', 46],
  ['overview-north', '-4,46,26,-4,0,-12', 60],
  ['overview-south', '6,46,-26,6,0,12', 60],
  ['overview-east', '8,38,0,34,0,0', 62],
];

module.exports = async (page, h) => {
  const only = (process.env.LEVEL_TOUR || '').split(',').filter(Boolean);
  const dir = process.env.LEVEL_TOUR_DIR || path.join('shots', 'level');
  await h.frames(2);

  let n = 0;
  for (const [name, cam, fov] of VIEWS) {
    n++;
    if (only.length && !only.some((word) => name.includes(word))) continue;
    await h.eval(([c, f]) => window.__setShot({ cam: c, fov: f }), [cam, fov]);
    await h.frames(2);
    await h.shot(path.join(dir, `tour-${String(n).padStart(2, '0')}-${name}.png`));
  }

  const info = await h.eval(() => {
    const L = window.__G.level;
    const s = window.__stats();
    return {
      calls: s.calls,
      triangles: s.triangles,
      programs: s.programs,
      stats: L.stats,
      spawns: [L.enemySpawns.filter((p) => p.type === 'ground').length, L.enemySpawns.filter((p) => p.type === 'air').length],
      cover: L.coverPoints.length,
      explosives: L.explosives.length,
      lamps: L.lamps.length,
    };
  });
  console.log(`level-tour: ${JSON.stringify(info)}`);
  const errors = await h.errors();
  if (errors.length) throw new Error(`${errors.length} page error(s): ${errors[0]}`);
};
