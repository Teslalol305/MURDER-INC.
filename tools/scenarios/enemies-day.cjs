// The Vultures on the real block in full sun (needs the real level and atmos): every Goon outfit in a
// pose and a Buzzard, photographed from 3 m, 12 m and 35 m, then one Goon and the Buzzard close up.
//
//   node build.mjs --dev --out=dist/dev-enemies-full.html
//   node tools/shot.cjs dist/dev-enemies-full.html --params "autostart=1&q=low&god=1&noaudio=1&nohud=1" \
//        --size 800x450 --scenario tools/scenarios/enemies-day.cjs --timeout 600
//
// ENEMIES_TIME=night takes the same pictures at night. Screenshots: shots/enemies/day-*.png (night-*.png).

'use strict';

const TIME = process.env.ENEMIES_TIME || 'day';
const OUT = `shots/enemies/${TIME}-`;

module.exports = async (page, h) => {
  const n = await h.eval((time) => {
    const G = window.__G;
    const V = G.THREE.Vector3;
    if (G.atmos && G.atmos.setTime) G.atmos.setTime(time);
    G.enemies.clear();
    const ui = document.getElementById('ui');
    if (ui) ui.style.display = 'none'; // pictures of the street, not of the HUD
    G.player.reset({ pos: new V(-37.4, 0, 8.15), yaw: -Math.PI / 2 });
    const X = -22; // the sunny half of the roadway, clear of cars and El columns
    const Z = 4.5;
    const poses = [
      { variant: 0, dx: -2.4, show: {} },
      { variant: 1, dx: -0.8, show: { aim: 1, lamp: 1 } },
      { variant: 2, dx: 0.8, show: { speed: 5 } },
      { variant: 0, dx: 2.4, show: { aim: 1, crouch: 1 } },
    ];
    for (const p of poses) {
      const e = G.enemies.spawn('goon', new V(X + p.dx, 0, Z), { passive: true, yaw: 0, show: p.show, variant: p.variant });
      if (!e) return -1;
    }
    G.enemies.spawn('buzzard', new V(X, 2.8, Z + 1.5), { passive: true, yaw: 0 });
    return G.enemies.list.length;
  }, TIME);
  if (n !== 5) throw new Error(`expected 5 showcase units, got ${n}`);

  const shoot = async (name, cam, fov = 50) => {
    await h.eval(([c, f]) => window.__setShot({ cam: c, fov: f }), [cam, fov]);
    await h.skip(30);
    await h.frames(2);
    await h.shot(`${OUT}${name}.png`);
  };
  await shoot('03m', '-22,1.5,1.5,-22,1.1,4.5', 55);
  await shoot('12m', '-30,2.2,-4.5,-22,1.2,4.5');
  await shoot('35m', '13,4,5,-22,1.2,4.5', 40);
  await shoot('goon-close', '-22.6,1.5,2.6,-22.8,1.25,4.5', 45);
  await shoot('buzzard-close', '-21.2,3.1,4.1,-22,2.8,6', 45);
  await h.eval(() => window.__setShot({ cam: '' }));

  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
};
