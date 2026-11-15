// Quick state checks for the atmosphere (no pictures): day / night switch, train, lights.
//   node tools/shot.cjs dist/dev-atmos.html --params "shot=1&nohud=1" --scenario tools/scenarios/atmos-check.cjs
module.exports = async (page, h) => {
  const out = {};
  out.boot = await h.eval(() => ({ time: __G.atmos.time, fogDensity: __G.scene.fog.density, exposure: __G.render.look.exposure, sun: __G.atmos.sun.intensity }));
  await h.eval(() => __G.atmos.passTrain(1, 1));
  await h.skip(30);
  out.train = await h.eval(() => {
    const t = __G.atmos.train;
    let vis = null;
    __G.scene.traverse((o) => { if (o.name === 'atmos-train') vis = { visible: o.visible, x: o.position.x, y: o.position.y, z: o.position.z, parentVisible: o.parent && o.parent.visible }; });
    return { active: t.active, phase: t.phase, x: t.x, lo: t.lo, hi: t.hi, y: t.y, z: t.z, vis };
  });
  out.programsDay = await h.eval(() => __G.renderer.info.programs.length);
  await h.skip(45);
  await h.eval(() => window.__setShot({ cam: '-26,1.7,9.6,-6,7,1', fov: 70 }));
  await h.frames(2);
  await h.shot('shots/atmos/check-train-day.png');
  await h.eval(() => __G.atmos.setTime('night'));
  await h.skip(5);
  out.night = await h.eval(() => ({ time: __G.atmos.time, fogDensity: __G.scene.fog.density, exposure: __G.render.look.exposure, sun: __G.atmos.sun.intensity, stats: __G.atmos.stats().realKinds }));
  await h.frames(2);
  await h.shot('shots/atmos/check-train-night.png');
  out.programsNight = await h.eval(() => __G.renderer.info.programs.length);
  await h.eval(() => __G.atmos.setTime('day'));
  await h.skip(5);
  out.day = await h.eval(() => ({ time: __G.atmos.time, exposure: __G.render.look.exposure, programs: __G.renderer.info.programs.length }));
  console.error('atmos check: ' + JSON.stringify(out));
  const errs = (await h.errors()).filter((e) => !/menus\.openPanel/.test(e));
  if (errs.length) throw new Error(errs[0]);
};
