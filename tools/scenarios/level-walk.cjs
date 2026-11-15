// Walks Rule around the whole block with the real player and keyboard: start → reel 1 → into the shop
// → up the mezzanine stair → out the side door → down the alley → the cage → under the El to the lot →
// the truck → the rear lane → the vacant lot → up the shed stair onto the deck. The route between
// stops is a nav path; the walker only turns (writes player.yaw) and holds W. Fails if he gets stuck,
// ends up somewhere else, or the page logs an error.
//
//   node build.mjs --dev --out=dist/dev-level-full.html
//   node tools/shot.cjs dist/dev-level-full.html --params "autostart=1&q=test&god=1&noaudio=1" \
//        --scenario tools/scenarios/level-walk.cjs --timeout 900
//
// LEVEL_WALK_SHOTS=1 also takes a first-person picture at every stop (shots/level/walk-*.png).

'use strict';

const path = require('node:path');

// name, target [x, z], expected floor height (null: whatever), optional straight legs walked first (stairs)
const STOPS = [
  ['reel1', [-5.5, 2.6], 0],
  ['shop-door', [-12, -10.5], 0],
  ['reel2', [-10.8, -19.8], 0],
  ['mezz-stair-foot', [-11.7, -25.6], 0],
  ['mezzanine', [-17, -26], 2.8, [[-11.6, -25.65], [-16, -25.65]]],
  ['mezz-down', [-11, -24.5], 0, [[-16, -25.65], [-11.6, -25.65]]],
  ['side-door', [4.6, -22.1], 0],
  ['alley', [8.5, -14], 0],
  ['north-walk', [13, -8.2], 0.15],
  ['cage-gate', [34.5, -11.4], null],
  ['reel3', [33.6, -20.6], 0],
  ['roadblock-walk', [40, 9], 0.15],
  ['lot', [32, 20], 0],
  ['truck', [36.2, 29.4], 0],
  ['rear-lane', [10, 28.5], 0],
  ['vacant', [-10, 20], 0],
  ['vacant-gate', [-10.3, 10], null],
  ['shed-foot', [-3.4, 9.9], 0.15],
  ['shed-deck', [6, 9.3], 2.95, [[-3.4, 9.95], [1.6, 9.95]]],
];

module.exports = async (page, h) => {
  const shots = !!process.env.LEVEL_WALK_SHOTS;
  const report = [];
  await h.skip(10);
  await h.eval(() => {
    window.__G.player.invulnerable = true;
    if (window.__G.enemies && window.__G.enemies.clear) window.__G.enemies.clear();
  });

  for (const [name, [tx, tz], floor, legs] of STOPS) {
    // A nav path from where he stands (the nav grid is the ground); onto a deck, straight legs up its stair.
    const route = legs ? [...legs, [tx, tz]] : await h.eval(([x, z]) => {
      const G = window.__G;
      const p = G.player.pos;
      const goal = new G.THREE.Vector3(x, 0, z);
      const near = G.physics.nav.nearestWalkable(x, z, 3) || goal;
      const path = G.physics.nav.findPath(p.clone(), near);
      const pts = (path || []).map((v) => [v.x, v.z]);
      pts.push([x, z]);
      return pts;
    }, [tx, tz]);

    await h.key('KeyW', true);
    let stuck = null;
    for (const [wx, wz] of route) {
      let best = Infinity;
      let still = 0;
      for (let i = 0; i < 400; i++) {
        const d = await h.eval(([x, z]) => {
          const P = window.__G.player;
          const dx = x - P.pos.x;
          const dz = z - P.pos.z;
          const dist = Math.hypot(dx, dz);
          if (dist > 0.05) P.yaw = Math.atan2(-dx, -dz);
          return dist;
        }, [wx, wz]);
        if (d < 0.45) break;
        if (d < best - 0.05) {
          best = d;
          still = 0;
        } else if (++still > 40) {
          stuck = [wx, wz];
          break;
        }
        await h.skip(3);
      }
      if (stuck) break;
    }
    await h.key('KeyW', false);
    await h.skip(8);

    const at = await h.eval(() => {
      const P = window.__G.player;
      return { x: P.pos.x, y: P.pos.y, z: P.pos.z, zone: window.__G.level.zoneName ? window.__G.level.zoneName(P.pos.x, P.pos.z) : '' };
    });
    const off = Math.hypot(at.x - tx, at.z - tz);
    const ok = !stuck && off < 1.2 && (floor === null || Math.abs(at.y - floor) < 0.2);
    report.push(`${ok ? 'ok  ' : 'FAIL'} ${name.padEnd(16)} at (${at.x.toFixed(1)}, ${at.y.toFixed(2)}, ${at.z.toFixed(1)}) ${at.zone}${stuck ? ` stuck near ${stuck}` : ''}`);
    if (shots) {
      await h.frames(2);
      await h.shot(path.join('shots', 'level', `walk-${name}.png`));
    }
  }

  console.log(report.join('\n'));
  const errors = await h.errors();
  const failed = report.filter((r) => r.startsWith('FAIL'));
  if (failed.length || errors.length) throw new Error(`${failed.length} stop(s) failed, ${errors.length} page error(s) ${errors[0] || ''}`);
};
