// An explosion at night seen from 10 m and from 30 m, across several frames.
//
//   node build.mjs --dev --only=fx,explosives --out=dist/dev-fx.html
//   node tools/shot.cjs dist/dev-fx.html --params "autostart=1&q=low&god=1&nohud=1" --scenario tools/scenarios/fx-explosion.cjs --timeout 300
//
// Checks: the blast spawns particles in both pools, debris and a scorch decal, lights a pooled light, and
// everything has burnt out again a few seconds later.

const OUT = 'shots/fx';
const SITE = [-12, 0, 2]; // mid-avenue, open ground

module.exports = async (page, h) => {
  const stats = () => h.eval(() => window.__G.fx.stats());

  for (const [name, cam] of [
    ['10m', `${SITE[0] - 10},1.7,${SITE[2] + 0.5},${SITE[0]},1.6,${SITE[2]}`],
    ['30m', `${SITE[0] - 30},1.7,${SITE[2] + 1.5},${SITE[0]},2.5,${SITE[2]}`],
  ]) {
    await h.eval(
      ([cam, site]) => {
        const G = window.__G;
        G.enemies.clear();
        G.fx.clear();
        window.__setShot({ cam });
        G.fx.explosion(new G.THREE.Vector3(site[0], site[1] + 0.3, site[2]), 1);
      },
      [cam, SITE],
    );
    // 1 frame = 33 ms: flash, fireball, smoke column, embers, aftermath.
    const marks = [1, 3, 6, 12, 24, 48, 90];
    let at = 0;
    for (const frame of marks) {
      await h.skip(frame - at - 1);
      await h.frames(1);
      at = frame;
      await h.shot(`${OUT}/explosion-${name}-f${String(frame).padStart(2, '0')}.png`);
      if (frame === 3) {
        const s = await stats();
        if (s.lit < 5 || s.additive < 15 || s.debris < 3 || s.decals < 1) throw new Error(`thin explosion: ${JSON.stringify(s)}`);
      }
    }
    await h.skip(240);
    const after = await stats();
    if (after.additive > 0 || after.debris > 0) throw new Error(`the blast never burnt out: ${JSON.stringify(after)}`);
  }

  // What it left behind: a scorch mark on the asphalt, seen from above.
  await h.eval((site) => window.__setShot({ cam: `${site[0] - 4.5},4.2,${site[2] + 2.5},${site[0]},0,${site[2]}` }), SITE);
  await h.frames(1);
  await h.shot(`${OUT}/explosion-scorch.png`);
  const left = await stats();
  if (left.decals !== 1) throw new Error(`expected one scorch mark, found ${left.decals} decals`);

  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
};
