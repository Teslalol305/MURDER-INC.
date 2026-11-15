// Review (visual): title fly-through samples and a few outside views. Throwaway.
//   node tools/shot.cjs dist/dev-all.html --params "q=medium&god=1&noaudio=1&nohud=1" --size 960x540 --scenario tools/scenarios/review-visual.cjs --timeout 900
const OUT = process.env.RV_OUT || 'shots/review';
const ONLY = process.env.RV_ONLY ? process.env.RV_ONLY.split(',') : null;
const want = (n) => !ONLY || ONLY.includes(n);

module.exports = async (page, h) => {
  const info = await h.eval(() => {
    const G = window.__G;
    const T = G.THREE;
    const P = G.level.cinematicPath;
    const c = new T.CatmullRomCurve3(P.map((p) => p.pos.clone()), false, 'centripetal');
    c.arcLengthDivisions = 600;
    const len = c.getLength();
    const dur = Math.max(G.config.flow.titleCamera.minLoop, len / G.config.flow.titleCamera.speed);
    return { len, dur, state: G.game.state, time: G.settings.get ? G.settings.get('time') : null };
  });
  console.log('title', JSON.stringify(info));
  if (want('title')) {
    const N = 14;
    let tPrev = 0;
    for (let i = 0; i < N; i++) {
      const t = 3 + (i * (info.dur - 6)) / (N - 1);
      const steps = Math.round((t - tPrev) * 30);
      tPrev += steps / 30;
      await h.skip(steps);
      await h.frames(1);
      const cam = await h.eval(() => {
        const c = window.__G.camera;
        return [c.position.x, c.position.y, c.position.z].map((v) => +v.toFixed(1));
      });
      console.log('title', i, tPrev.toFixed(1), JSON.stringify(cam));
      await h.shot(`${OUT}/title-${String(i).padStart(2, '0')}.png`);
    }
  }
  await h.eval(() => window.__G.game.start({ mode: 'mission', skipIntro: true }));
  await h.skip(20);
  const views = [
    ['truck', '28,2.2,22,35.9,1.4,29.7'],
    ['pizza', '-33,1.7,4,-34,1.8,11'],
    ['endeast', '40,1.7,0,90,3,0'],
    ['endwest', '-36,1.7,0,-90,3,0'],
    ['endeast-high', '30,9,0,90,8,0'],
    ['lane', '4,1.7,28.5,20,1.7,30.5'],
    ['goon', '-14,1.7,3,-8,1.2,0.5'],
  ];
  if (views.some((v) => want(v[0]))) {
    await h.eval(() => {
      const G = window.__G;
      G.enemies.clear();
      G.enemies.spawn('goon', new G.THREE.Vector3(-8, 0, 0.5), { alerted: false });
      G.enemies.spawn('goon', new G.THREE.Vector3(-6, 0, -2.5), { alerted: false });
    });
    await h.skip(10);
  }
  for (const [name, cam] of views) {
    if (!want(name)) continue;
    await h.eval((c) => window.__setShot({ cam: c, fov: 60 }), cam);
    await h.skip(4);
    await h.frames(2);
    await h.shot(`${OUT}/view-${name}.png`);
  }
};
