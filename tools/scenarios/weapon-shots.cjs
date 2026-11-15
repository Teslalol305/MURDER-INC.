// The viewmodel picture suite: hip, aim, firing, reload, melee, switch and the three weapon positions
// for both guns, played with real input. Checks the rules on the way (rounds spent, ammo moved).
//
//   node build.mjs --dev --only=weapon --out=dist/dev-weapon.html
//   WDAY=1 node tools/shot.cjs dist/dev-weapon.html --params "autostart=1&q=low&god=1&nohud=1&noaudio=1" \
//        --scenario tools/scenarios/weapon-shots.cjs --timeout 900
//
// WDAY=1 pretends it is 4 PM and hangs a daylight card behind the gun (for builds without the real day
// rig); leave it out over the real block. WGUNS=chopper or nine limits the run; WPREFIX names the files;
// WPARTS=hip,ads,fire,reload,melee,views,switch picks the pictures (the actions all run regardless).

module.exports = async (page, h) => {
  const day = !!process.env.WDAY;
  const guns = (process.env.WGUNS || 'chopper,nine').split(',');
  const prefix = process.env.WPREFIX || (day ? 'day' : 'block');
  const parts = new Set((process.env.WPARTS || 'hip,ads,fire,reload,melee,views,switch').split(','));
  /** Draws a frame and saves it when `part` was asked for; otherwise just steps once. */
  const snap = async (part, name) => {
    if (!parts.has(part)) return h.skip(1);
    await h.frames(1);
    await h.shot(`shots/weapon/${prefix}-${name}.png`);
  };
  const tap = async (code, steps = 2) => {
    await h.key(code, true);
    await h.skip(steps);
    await h.key(code, false);
  };
  const state = () => h.eval(() => {
    const w = window.__G.weapon;
    return { current: w.current, state: w.state, mag: w.mag, reserve: w.reserve, shots: window.__G.combat.stats.shots };
  });
  const problems = [];

  await page.mouse.move(480, 270);
  await h.eval((d) => {
    const G = window.__G;
    if (G.enemies && G.enemies.clear) G.enemies.clear();
    if (d && G.atmos) {
      G.atmos.time = 'day';
      const sun = G.atmos.sun;
      if (sun) {
        sun.color.set(0xffe6c6);
        sun.intensity = 5; // as atmos lights the day (config/look.js times.day.sun)
        sun.position.copy(sun.target.position).add(new G.THREE.Vector3(0.45, 1, 0.35).multiplyScalar(80));
      }
    }
    if (d) G.weapon.inspect({ live: true, backdrop: 'day' });
  }, day);

  for (const gun of guns) {
    const now = await state();
    if (now.current !== gun) {
      await tap(gun === 'nine' ? 'Digit2' : 'Digit1');
      await h.skip(30);
    }
    await h.skip(30);
    await snap('hip', `${gun}-hip`);

    // Aim down the sights.
    await h.key('Mouse2', true);
    await h.skip(24);
    await snap('ads', `${gun}-ads`);
    await h.key('Mouse2', false);
    await h.skip(24);

    // Fire: the frame of the shot (flash), then a moment into a burst / a follow-up.
    const before = await state();
    await h.key('Mouse0', true);
    await snap('fire', `${gun}-fire`);
    if (gun === 'chopper') {
      await h.skip(7);
      await snap('fire', `${gun}-burst`);
    }
    await h.key('Mouse0', false);
    await h.skip(20);
    const after = await state();
    if (!(after.mag < before.mag) || !(after.shots > before.shots)) problems.push(`${gun}: firing spent nothing ${JSON.stringify([before, after])}`);

    // Tactical reload: the magazine coming out, then going in.
    await tap('KeyR');
    const timeline = gun === 'chopper' ? [16, 22] : [8, 21];
    await h.skip(timeline[0]);
    await snap('reload', `${gun}-reload-out`);
    await h.skip(timeline[1]);
    await snap('reload', `${gun}-reload-in`);
    await h.skip(60);
    const reloaded = await state();
    if (reloaded.mag !== (gun === 'chopper' ? 30 : 15)) problems.push(`${gun}: reload left ${reloaded.mag} in the magazine`);

    // Melee: just after the blow lands.
    await tap('KeyF');
    await h.skip(5);
    await snap('melee', `${gun}-melee`);
    await h.skip(30);

    // The other two weapon positions.
    for (const view of [2, 3]) {
      await h.eval((v) => window.__G.weapon.setView(v), view);
      await h.skip(10);
      await snap('views', `${gun}-view${view}`);
    }
    await h.eval(() => window.__G.weapon.setView(1));
  }

  // Switching: the frame the new gun comes up.
  await tap('KeyQ');
  await h.skip(12);
  await snap('switch', 'switch');
  await h.skip(30);
  if (day) await h.eval(() => window.__G.weapon.inspect(null));
  const errors = await h.errors();
  if (errors.length) problems.push(`errors: ${errors.join(' | ')}`);
  if (problems.length) throw new Error(problems.join('\n'));
};
