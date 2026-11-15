// Renderer check: every gameplay-driven post effect, the pooled lights and the viewmodel pass.
//
//   node build.mjs --dev --out=dist/dev-foundation.html
//   node tools/shot.cjs dist/dev-foundation.html --params "shot=1&nohud=1" --scenario tools/scenarios/foundation-post.cjs
//
// Writes shots/foundation/post-*.png. Look at them: each should differ from post-0-base.png in the way
// its name says.

const OUT = 'shots/foundation';

module.exports = async (page, h) => {
  await h.frames(5);

  // A stand-in weapon: the stub weapon has no viewmodel. Children of G.vmCamera are in view space.
  await h.eval(() => {
    const { THREE, vmCamera } = window.__G;
    const gun = new THREE.Mesh(
      new THREE.BoxGeometry(0.07, 0.09, 0.5),
      new THREE.MeshStandardMaterial({ color: 0x2a2c30, roughness: 0.4, metalness: 0.8 }),
    );
    gun.name = 'test-viewmodel';
    gun.position.set(0.14, -0.13, -0.42);
    vmCamera.add(gun);
  });

  // While paused nothing else writes to render.post, so the values set below stay put.
  await h.eval(() => window.__G.game.pause());

  const cases = {
    '0-base': {},
    '1-damage': { damage: 1 },
    '2-lowhealth': { lowHealth: 1 },
    '3-ads': { ads: 1 },
    '4-flash': { flash: 0.6 },
    '5-fade': { fade: 0.7 },
    '6-desaturated': { saturation: 0.12 },
  };
  for (const [name, values] of Object.entries(cases)) {
    await h.eval((v) => {
      Object.assign(window.__G.render.post, { damage: 0, lowHealth: 0, ads: 0, flash: 0, fade: 0, saturation: 1 }, v);
    }, values);
    await h.frames(1);
    await h.shot(`${OUT}/post-${name}.png`);
  }
  await h.eval(() => Object.assign(window.__G.render.post, { damage: 0, lowHealth: 0, ads: 0, flash: 0, fade: 0, saturation: 1 }));

  // A pooled light: a long flash just ahead of the camera.
  await h.eval(() => {
    const G = window.__G;
    const p = G.camera.position.clone().add(G.player.forward.clone().multiplyScalar(4));
    p.y = 1;
    G.render.lights.flash(p, 0x40a0ff, 120, 14, 10);
  });
  await h.frames(1);
  await h.shot(`${OUT}/post-7-light.png`);

  // The same frame without bloom: render.look is live, atmos tunes the picture through it.
  await h.eval(() => {
    window.__G.render.look.bloomStrength = 0;
  });
  await h.frames(1);
  await h.shot(`${OUT}/post-8-nobloom.png`);

  const stats = await h.stats();
  if (!stats.post) throw new Error('the post chain is off: the renderer fell back to the forward path');
};
