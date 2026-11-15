// Every emitter kind side by side on the north sidewalk: steam, smolder, embers, fire, drip, jet.
//
//   node build.mjs --dev --only=fx,explosives --out=dist/dev-fx.html
//   node tools/shot.cjs dist/dev-fx.html --params "autostart=1&q=low&god=1&nohud=1" --scenario tools/scenarios/fx-emitters.cjs --timeout 400

const OUT = 'shots/fx';
const KINDS = ['steam', 'smolder', 'embers', 'fire', 'drip', 'jet'];

module.exports = async (page, h) => {
  const stats = () => h.eval(() => window.__G.fx.stats());

  await h.eval((kinds) => {
    const G = window.__G;
    const V = (x, y, z) => new G.THREE.Vector3(x, y, z);
    G.enemies.clear();
    G.fx.clear();
    window.__handles = kinds.map((kind, i) =>
      G.fx.addEmitter(V(-38 + i * 2, kind === 'drip' ? 3.2 : kind === 'jet' ? 0.5 : 0, -9.3), kind, {
        scale: 1,
        dir: V(0.5, 0.6, 0.2), // only the jet uses it
      }),
    );
    window.__setShot({ cam: '-33,1.7,-3.4,-33,1.5,-9.3', fov: 62 });
  }, KINDS);

  await h.skip(120); // four seconds: columns have risen, the fire has caught
  await h.frames(1);
  await h.shot(`${OUT}/emitters-all-a.png`);
  const running = await stats();
  if (running.emitters !== KINDS.length) throw new Error(`expected ${KINDS.length} emitters, got ${running.emitters}`);
  if (running.lit < 12 || running.additive < 25) throw new Error(`emitters are not producing: ${JSON.stringify(running)}`);

  await h.skip(20);
  await h.frames(1);
  await h.shot(`${OUT}/emitters-all-b.png`);

  // Close-ups.
  for (const [name, cam] of [
    ['steam', '-36.2,1.2,-6.6,-37.6,1.6,-9.3'],
    ['fire', '-32.3,0.9,-6.9,-32,0.8,-9.3'],
    ['jet', '-28.6,0.9,-6.4,-27.6,1.0,-9.2'],
  ]) {
    await h.eval((c) => window.__setShot({ cam: c, fov: 55 }), cam);
    await h.skip(7);
    await h.frames(1);
    await h.shot(`${OUT}/emitters-${name}.png`);
  }

  // The fire moves with setPos and everything stops on request.
  await h.eval(() => {
    const V = (x, y, z) => new window.__G.THREE.Vector3(x, y, z);
    window.__handles[3].setPos(V(-32, 0, -8));
    for (const handle of window.__handles) if (handle !== window.__handles[3]) handle.stop();
  });
  await h.skip(150);
  const one = await stats();
  if (one.emitters !== 1) throw new Error(`stop() left ${one.emitters} emitters`);
  await h.eval(() => window.__handles[3].stop());
  await h.skip(200);
  const none = await stats();
  if (none.emitters !== 0 || none.lit + none.additive !== 0) throw new Error(`still burning: ${JSON.stringify(none)}`);

  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
};
