// Turntable shots of the viewmodel, for modelling work.
//
//   node build.mjs --dev --only=weapon --out=dist/dev-weapon.html
//   node tools/shot.cjs dist/dev-weapon.html --params "autostart=1&q=low&god=1&nohud=1" \
//        --scenario tools/scenarios/weapon-inspect.cjs
//
// WVIEWS (optional, JSON): [{name, spec, weapon, eval}], where spec is what G.weapon.inspect() takes:
// {dist, x, y, yaw, pitch, roll} holds the gun in front of the camera (yaw 1.57 shows its left side),
// null gives the live first-person pose back. `weapon` switches gun first; `eval` runs page code first.
// WLOOK (optional): "yaw,pitch" in radians to turn the player before shooting.

const DEFAULT_VIEWS = [
  { name: 'inspect-left', spec: { dist: 0.55, yaw: 1.5708, x: 0.25, y: 0.07, backdrop: true } },
  { name: 'inspect-right', spec: { dist: 0.55, yaw: -1.5708, x: -0.25, y: 0.07, backdrop: true } },
  { name: 'inspect-top', spec: { dist: 0.55, yaw: 1.5708, roll: 1.1, x: 0.25, backdrop: true } },
  { name: 'inspect-front', spec: { dist: 0.75, yaw: 2.5, pitch: 0.2, x: 0.12, backdrop: true } },
  { name: 'inspect-rear', spec: { dist: 0.5, yaw: 0.45, pitch: -0.25, x: -0.06, y: 0.02, backdrop: true } },
  { name: 'first-person', spec: null },
];

module.exports = async (page, h) => {
  const views = process.env.WVIEWS ? JSON.parse(process.env.WVIEWS) : DEFAULT_VIEWS;
  await h.eval((look) => {
    const G = window.__G;
    G.enemies.clear();
    if (look) {
      const [yaw, pitch] = look.split(',').map(Number);
      G.player.yaw = yaw;
      G.player.pitch = pitch || 0;
    }
  }, process.env.WLOOK || '');
  for (const view of views) {
    if (view.eval) await h.eval(view.eval);
    if (view.weapon) {
      await h.eval((id) => {
        const G = window.__G;
        if (G.weapon.current !== id) window.dispatchEvent(new KeyboardEvent('keydown', { code: id === 'nine' ? 'Digit2' : 'Digit1' }));
      }, view.weapon);
      await h.skip(2);
      await h.eval(() => {
        for (const code of ['Digit1', 'Digit2']) window.dispatchEvent(new KeyboardEvent('keyup', { code }));
      });
      await h.skip(30);
    }
    await h.eval((spec) => window.__G.weapon.inspect(spec), view.spec || null);
    await h.frames(2);
    await h.shot(`shots/weapon/${view.name}.png`);
  }
  await h.eval(() => window.__G.weapon.inspect(null));
  const info = await h.eval(() => window.__G.weapon.info);
  console.error(`[weapon] ${JSON.stringify(info)}`);
};
