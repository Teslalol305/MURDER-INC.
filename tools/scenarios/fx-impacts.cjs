// Bullet impacts on every surface, the marks they leave, and the decal ring buffer (300 marks into 256 slots).
//
//   node build.mjs --dev --only=fx,explosives --out=dist/dev-fx.html
//   node tools/shot.cjs dist/dev-fx.html --params "autostart=1&q=low&god=1&nohud=1" --scenario tools/scenarios/fx-impacts.cjs --timeout 300
//
// The wall is the south face of the brick tenement (z = -12), the floor the north sidewalk in front of it.

const OUT = 'shots/fx';
const WALL = ['brick', 'concrete', 'metal', 'car', 'glass', 'wood'];
const FLOOR = ['asphalt', 'dirt', 'rubber', 'cloth'];
const BODY = ['flesh', 'drone'];

module.exports = async (page, h) => {
  const stats = () => h.eval(() => window.__G.fx.stats());

  await h.eval(() => {
    const G = window.__G;
    G.enemies.clear();
    G.fx.clear();
    window.__setShot({ cam: '-33,1.7,-5.6,-33,1.25,-12', fov: 62 });
  });
  await h.frames(1);

  // One round into each surface, all in the same step.
  await h.eval(
    ([wall, floor, body]) => {
      const G = window.__G;
      const V = (x, y, z) => new G.THREE.Vector3(x, y, z);
      const eye = V(-33, 1.7, -5.6);
      wall.forEach((surface, i) => {
        const point = V(-37 + i * 1.6, 1.55, -12);
        G.fx.impact(point, V(0, 0, 1), surface, point.clone().sub(eye).normalize());
      });
      floor.forEach((surface, i) => {
        const point = V(-35.4 + i * 1.6, 0, -9.6);
        G.fx.impact(point, V(0, 1, 0), surface, point.clone().sub(eye).normalize());
      });
      // Bodies: through the event, the way combat reports a Goon and a Buzzard being hit.
      body.forEach((surface, i) => {
        const point = V(-34 + i * 2.2, 1.0, -8.6);
        const dir = point.clone().sub(eye).normalize();
        G.events.emit('impact', { point, normal: dir.clone().negate(), surface, dir, from: 'player', enemy: { type: surface === 'drone' ? 'buzzard' : 'goon' } });
      });
    },
    [WALL, FLOOR, BODY],
  );
  const hit = await stats();
  if (hit.decals !== WALL.length + FLOOR.length) throw new Error(`expected ${WALL.length + FLOOR.length} marks (none on bodies), got ${hit.decals}`);
  if (hit.additive < 20 || hit.lit < 8 || hit.debris < 4) throw new Error(`thin impacts: ${JSON.stringify(hit)}`);

  for (const frame of [1, 3, 8]) {
    await h.frames(frame === 1 ? 1 : frame === 3 ? 2 : 5);
    await h.shot(`${OUT}/impacts-f${frame}.png`);
  }

  // The marks, close up, once the dust is gone.
  await h.skip(120);
  const settled = await stats();
  if (settled.additive !== 0 || settled.lit !== 0) throw new Error(`impact particles linger: ${JSON.stringify(settled)}`);
  await h.eval(() => window.__setShot({ cam: '-34.6,1.5,-10.1,-34.6,1.52,-12', fov: 50 }));
  await h.frames(1);
  await h.shot(`${OUT}/decals-wall-left.png`);
  await h.eval(() => window.__setShot({ cam: '-31.4,1.5,-10.1,-31.4,1.52,-12', fov: 50 }));
  await h.frames(1);
  await h.shot(`${OUT}/decals-wall-right.png`);
  await h.eval(() => window.__setShot({ cam: '-33,1.6,-8.2,-33,0,-9.6', fov: 50 }));
  await h.frames(1);
  await h.shot(`${OUT}/decals-floor.png`);

  // 300 marks sprayed over the wall and the pavement: the ring holds the newest 256.
  const ring = await h.eval(() => {
    const G = window.__G;
    const V = (x, y, z) => new G.THREE.Vector3(x, y, z);
    G.fx.clear();
    const kinds = ['brick', 'concrete', 'metal', 'glass', 'wood', 'asphalt'];
    for (let i = 0; i < 300; i++) {
      const u = (i * 0.618034) % 1;
      const v = (i * 0.754877) % 1;
      if (i % 3 === 0) G.fx.decal(V(-38 + u * 10, 0, -11.6 + v * 3.4), V(0, 1, 0), kinds[i % kinds.length]);
      else G.fx.decal(V(-38 + u * 10, 0.3 + v * 2.6, -12), V(0, 0, 1), kinds[i % kinds.length]);
    }
    return G.fx.stats();
  });
  if (ring.decals !== ring.budget.decals || ring.decalsPlaced < 300) throw new Error(`ring buffer: ${JSON.stringify(ring)}`);
  await h.eval(() => window.__setShot({ cam: '-33,2.2,-5.2,-33,1.1,-12', fov: 62 }));
  await h.frames(1);
  await h.shot(`${OUT}/decals-300.png`);

  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
};
