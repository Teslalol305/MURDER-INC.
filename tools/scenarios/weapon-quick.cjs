// Quick looks at the viewmodel while working on it: one browser, any number of pictures.
//
//   node build.mjs --dev --only=weapon --out=dist/dev-weapon.html
//   WSHOTS='[{"name":"a"},{"name":"b","gun":"nine","ads":true}]' node tools/shot.cjs dist/dev-weapon.html \
//        --params "autostart=1&q=low&god=1&nohud=1" --scenario tools/scenarios/weapon-quick.cjs
//
// Each entry of WSHOTS (JSON): {name, gun: 'chopper' | 'nine', ads, view: 1|2|3, look: [yaw, pitch],
//   inspect: what G.weapon.inspect() takes ({dist, x, y, pitch, yaw, roll} holds the gun in a fixed pose,
//   {live: true} keeps the first-person pose; backdrop: true | 'day' puts a card behind it),
//   day: true (pretend it is 4 PM: sun from the right, daylight box), eval: page code to run first}.
// Default: one hip shot of the Chopper over a daylight card.

const DEFAULT = [{ name: 'quick', day: true, inspect: { live: true, backdrop: 'day' } }];

module.exports = async (page, h) => {
  const shots = process.env.WSHOTS ? JSON.parse(process.env.WSHOTS) : DEFAULT;
  await page.mouse.move(480, 270);
  await h.eval(() => {
    const G = window.__G;
    if (G.enemies && G.enemies.clear) G.enemies.clear();
  });
  let aiming = false;
  for (const shot of shots) {
    if (shot.eval) await h.eval(shot.eval);
    await h.eval((s) => {
      const G = window.__G;
      if (s.look) {
        G.player.yaw = s.look[0];
        G.player.pitch = s.look[1] || 0;
      }
      if (s.view) G.weapon.setView(s.view);
      if (s.day !== undefined && G.atmos) {
        G.atmos.time = s.day ? 'day' : 'night';
        const sun = G.atmos.sun;
        if (s.day && sun) {
          sun.color.set(0xfff0dc);
          sun.intensity = 3;
          sun.position.copy(sun.target.position).add(new G.THREE.Vector3(0.45, 1, 0.35).multiplyScalar(80));
        }
      }
      G.weapon.inspect(s.inspect || null);
    }, shot);
    const gun = shot.gun || 'chopper';
    const current = await h.eval(() => window.__G.weapon.current);
    if (current !== gun) {
      const code = gun === 'nine' ? 'Digit2' : 'Digit1';
      await h.key(code, true);
      await h.skip(2);
      await h.key(code, false);
      await h.skip(40);
    }
    if (!!shot.ads !== aiming) {
      aiming = !!shot.ads;
      await h.key('Mouse2', aiming);
    }
    await h.skip(shot.settle || 40);
    await h.frames(2);
    await h.shot(`shots/weapon/${shot.name}.png`);
  }
  if (aiming) await h.key('Mouse2', false);
  await h.eval(() => window.__G.weapon.inspect(null));
  const info = await h.eval(() => window.__G.weapon.info);
  console.error(`[weapon] ${JSON.stringify(info)}`);
};
