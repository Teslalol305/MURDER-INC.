// What the Vultures look like: every Goon outfit and a Buzzard, posed in the open, photographed from
// 3 m, 12 m and 35 m, under the El (the darkest place on the block) and on the lit sidewalk.
//
//   node build.mjs --dev --only=enemies --out=dist/dev-enemies.html
//   node tools/shot.cjs dist/dev-enemies.html --params "autostart=1&q=test&god=1&noaudio=1&nohud=1" \
//        --scenario tools/scenarios/enemies-look.cjs --timeout 300
//
// Screenshots land in shots/enemies/look-*.png. The units are passive (showcase): they hold a pose.

'use strict';

const OUT = 'shots/enemies/look-';

module.exports = async (page, h) => {
  const place = (where) =>
    h.eval((w) => {
      const G = window.__G;
      const V = G.THREE.Vector3;
      G.enemies.clear();
      G.player.reset({ pos: new V(-44, 0, 20), yaw: 0 }); // out of the way
      const [x, z] = w;
      const south = Math.PI; // facing +Z, toward the camera
      const poses = [
        { variant: 0, dx: -2.4, show: {} },
        { variant: 1, dx: -0.8, show: { aim: 1, lamp: 6 } },
        { variant: 2, dx: 0.8, show: { speed: 5 } },
        { variant: 0, dx: 2.4, show: { aim: 1, crouch: 1 } },
      ];
      for (const p of poses) {
        const e = G.enemies.spawn('goon', new V(x + p.dx, 0, z), { passive: true, yaw: south, show: p.show });
        e.variant = p.variant;
        e.object.geometry = window.__goonGeometry ? window.__goonGeometry[p.variant] : e.object.geometry;
      }
      G.enemies.spawn('buzzard', new V(x, 2.6, z - 1.5), { passive: true, yaw: south });
      return G.enemies.list.length;
    }, where);

  const shoot = async (name, cam, fov = 50) => {
    await h.eval(([c, f]) => window.__setShot({ cam: c, fov: f }), [cam, fov]);
    await h.skip(45); // let the poses blend in
    await h.frames(3);
    await h.shot(`${OUT}${name}.png`);
  };

  // Under the El, mid-avenue.
  let n = await place([-25, 0]);
  if (n !== 5) throw new Error(`expected 5 showcase units, got ${n}`);
  await shoot('el-03m', '-25,1.5,3,-25,1.1,0', 55);
  await shoot('el-03m-side', '-22.6,1.5,2.2,-25,1.1,0', 55);
  await shoot('el-12m', '-25,1.7,12,-25,1.2,0');
  await shoot('el-35m', '-25,1.7,35,-25,1.2,0', 40);

  // On the south sidewalk, in the street light.
  n = await place([-22, 9]);
  await shoot('lit-03m', '-22,1.5,12,-22,1.1,9', 55);
  await shoot('lit-12m', '-22,1.7,21,-22,1.2,9');

  // Close-ups: one Goon, the Buzzard.
  await place([-25, 0]);
  await shoot('goon-close', '-25.6,1.45,1.9,-25.8,1.25,0', 45);
  await shoot('buzzard-close', '-24.2,3.0,0.4,-25,2.6,-1.5', 45);

  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
};
