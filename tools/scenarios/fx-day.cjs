// Daylight (CONTRACT 11.1): do the effects read against sunlit walls and against the sky?
//
//   node build.mjs --dev --only=fx,explosives --out=dist/dev-fx.html
//   node tools/shot.cjs dist/dev-fx.html --params "autostart=1&q=low&god=1&nohud=1" --scenario tools/scenarios/fx-day.cjs --timeout 600
//
// FX_PARTS=tracers,impacts,blast10,blast30,emitters picks parts (default: all); FX_TIME=night runs the same
// tour at night. Screenshots: shots/fx/day-*.png (night-*.png).

'use strict';

const { setTime, noErrors } = require('./fx-lib.cjs');

const TIME = process.env.FX_TIME === 'night' ? 'night' : 'day';
const OUT = `shots/fx/${TIME}`;
const PARTS = (process.env.FX_PARTS || 'tracers,impacts,blast10,blast30,emitters').split(',');
const SITE = [33, 0, 19]; // open ground in the lot: a sunlit wall 11 m behind it, sky above

module.exports = async (page, h) => {
  const stats = () => h.eval(() => window.__G.fx.stats());
  const how = await setTime(h, TIME);
  console.error(`${TIME} by ${how}`);
  await h.eval(() => window.__G.enemies.clear());
  await h.skip(20); // the effects sample the scene light twice a second

  // ---- Tracers and muzzle flashes in front of a sunlit wall and across the sky ----------------------
  if (PARTS.includes('tracers')) {
    await h.eval(() => {
      const G = window.__G;
      G.fx.clear();
      window.__setShot({ cam: '40,1.7,20,22,2.6,17', fov: 62 });
      const V = (x, y, z) => new G.THREE.Vector3(x, y, z);
      const { tracerPlayer, tracerEnemy } = G.config.look.palette;
      window.__volley = (n) => {
        // Along the wall, both ways, and one pair up into the sky.
        const a = V(30, 1.5, 27 - n * 0.4);
        const b = V(24 + n * 0.3, 1.3 + n * 0.25, -6);
        G.fx.tracer(a, b, tracerPlayer, 260);
        G.fx.muzzleFlash(a, b.clone().sub(a).normalize(), 1, true);
        const c = V(27, 1.4 + n * 0.2, 9 - n);
        const d = V(26.5 - n * 0.2, 1.2, 33);
        G.fx.tracer(c, d, tracerEnemy, 260);
        G.fx.muzzleFlash(c, d.clone().sub(c).normalize(), 0.8, true);
        G.fx.tracer(V(36, 1.5, 24), V(18 - n * 3, 22, 4 + n * 2), tracerPlayer, 260);
        G.fx.tracer(V(35, 1.5, 12), V(14, 18 + n, 30 - n * 3), tracerEnemy, 260);
      };
    });
    for (let n = 0; n < 3; n++) {
      await h.eval((i) => window.__volley(i), n);
      await h.frames(1);
      await h.shot(`${OUT}-tracers-${n}.png`);
    }
    const s = await stats();
    if (s.tracers < 4) throw new Error(`tracers should still be in flight: ${JSON.stringify(s)}`);
    await h.skip(60);
  }

  // ---- Impacts and bullet holes on the sunlit wall and on the ground ----------------------------------
  if (PARTS.includes('impacts')) {
    await h.eval(() => {
      const G = window.__G;
      G.fx.clear();
      window.__setShot({ cam: '25.6,1.6,18.2,22,1.45,16.4', fov: 55 });
      const V = (x, y, z) => new G.THREE.Vector3(x, y, z);
      const wall = V(1, 0, 0);
      const up = V(0, 1, 0);
      const shot = V(-0.8, -0.1, -0.3).normalize();
      const surfaces = ['brick', 'concrete', 'metal', 'glass', 'wood', 'car'];
      // Old marks first (their dust has settled), then a fresh volley to catch in the air.
      window.__hits = (fresh) => {
        surfaces.forEach((surface, i) => {
          const y = 0.9 + (i % 2) * 0.75 + (fresh ? 0.35 : 0);
          const z = 14.9 + i * 0.55 + (fresh ? 0.2 : 0);
          G.fx.impact(V(22, y, z), wall, surface, shot);
        });
        for (let i = 0; i < 4; i++) G.fx.impact(V(23.2 + i * 0.45, 0, 16.2 + i * 0.5 + (fresh ? 0.3 : 0)), up, i % 2 ? 'asphalt' : 'concrete', V(-0.5, -0.7, -0.2).normalize());
      };
      window.__hits(false);
    });
    await h.skip(70);
    await h.eval(() => window.__hits(true));
    for (const frame of [1, 3, 8]) {
      await h.frames(frame === 1 ? 1 : 1);
      if (frame > 1) await h.skip(frame === 3 ? 1 : 4);
      await h.shot(`${OUT}-impacts-f${frame}.png`);
    }
    await h.skip(70);
    await h.frames(1);
    await h.shot(`${OUT}-decals.png`);
  }

  // ---- A blast at 10 m and at 30 m ------------------------------------------------------------------------
  for (const [part, cam, marks] of [
    ['blast10', `${SITE[0] + 10},1.7,${SITE[2] + 0.8},${SITE[0]},2.2,${SITE[2]}`, [1, 3, 6, 12, 24, 48, 90]],
    ['blast30', `${SITE[0] - 3},1.7,${SITE[2] - 30},${SITE[0]},3.4,${SITE[2]}`, [3, 12, 48]],
  ]) {
    if (!PARTS.includes(part)) continue;
    await h.eval(
      ([cam, site]) => {
        const G = window.__G;
        G.fx.clear();
        window.__setShot({ cam, fov: 62 });
        G.fx.explosion(new G.THREE.Vector3(site[0], site[1] + 0.3, site[2]), 1);
      },
      [cam, SITE],
    );
    let at = 0;
    for (const frame of marks) {
      await h.skip(frame - at - 1);
      await h.frames(1);
      at = frame;
      await h.shot(`${OUT}-${part}-f${String(frame).padStart(2, '0')}.png`);
    }
    await h.skip(260);
  }

  // ---- Fire, a jet, steam and smoke in the open -----------------------------------------------------------
  if (PARTS.includes('emitters')) {
    await h.eval(() => {
      const G = window.__G;
      G.fx.clear();
      window.__setShot({ cam: '39,1.7,20.5,32,1.5,18.5', fov: 58 });
      const V = (x, y, z) => new G.THREE.Vector3(x, y, z);
      window.__emitters = [
        G.fx.addEmitter(V(31, 0.1, 15.5), 'fire', { scale: 1 }),
        G.fx.addEmitter(V(32.5, 0.6, 18), 'jet', { scale: 1, dir: V(0.3, 0.9, 0.2) }),
        G.fx.addEmitter(V(33, 0.05, 20.5), 'steam', { scale: 1 }),
        G.fx.addEmitter(V(31.5, 0.1, 22.5), 'smolder', { scale: 1 }),
      ];
      G.fx.sparks(V(34, 1, 19), null, 14);
    });
    await h.skip(75);
    await h.eval(() => window.__G.fx.sparks(new window.__G.THREE.Vector3(34.5, 1.2, 19.5), null, 16));
    await h.frames(2);
    await h.shot(`${OUT}-emitters.png`);
    await h.eval(() => window.__emitters.forEach((e) => e.stop()));
  }

  console.error(`fx at the end: ${JSON.stringify(await stats())}`);
  await noErrors(h);
};
