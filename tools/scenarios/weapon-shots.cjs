// The viewmodel picture suite: hip, aim, firing, reload, melee, switch and the three weapon positions
// for every gun, played with real input. Checks the rules on the way (rounds spent, ammo moved).
//
//   node build.mjs --dev --only=weapon --out=dist/dev-weapon.html
//   WDAY=1 node tools/shot.cjs dist/dev-weapon.html --params "autostart=1&q=low&god=1&nohud=1&noaudio=1" \
//        --scenario tools/scenarios/weapon-shots.cjs --timeout 900
//
// WDAY=1 pretends it is 4 PM and hangs a daylight card behind the gun (for builds without the real day
// rig); leave it out over the real block. WGUNS=chopper,ar15 (any of the five) limits the run; WPREFIX names the files;
// WPARTS=hip,ads,fire,reload,melee,views,switch picks the pictures (the actions all run regardless).

module.exports = async (page, h) => {
  const day = !!process.env.WDAY;
  const guns = (process.env.WGUNS || 'chopper,nine,ar15,switch9,rocket').split(',');
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

  // The pointer rests on the middle of the view: the harness presses buttons there, and under pointer
  // lock a pointer that had to travel first would turn Rule's head.
  const port = page.viewportSize() || { width: 960, height: 540 };
  await page.mouse.move(port.width / 2, port.height / 2);
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

  const STEP = 1 / 30; // the harness' fixed step
  for (const gun of guns) {
    const now = await state();
    // What the rules say about this gun: its number key, its magazine, how it fires and reloads.
    const def = await h.eval((id) => {
      const W = window.__G.config.weapons;
      const d = W[id];
      return { key: `Digit${W.common.order.indexOf(id) + 1}`, auto: !!d.auto, magSize: d.magSize, flies: !!d.projectile, selfReload: d.reloadAfterShot || 0, reload: d.reload };
    }, gun);
    if (now.current !== gun) {
      await tap(def.key);
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
    if (def.auto) {
      await h.skip(7);
      await snap('fire', `${gun}-burst`);
    }
    await h.key('Mouse0', false);
    // A gun that reaches for its next round by itself is already reloading: its pictures are timed from the shot.
    const waited = def.selfReload ? Math.ceil(def.selfReload / STEP) + 1 : 20;
    await h.skip(waited);
    const after = await state();
    const spent = def.flies ? after.mag < before.mag || after.reserve < before.reserve : after.mag < before.mag && after.shots > before.shots;
    if (!spent) problems.push(`${gun}: firing spent nothing ${JSON.stringify([before, after])}`);

    // The reload: the magazine (or round) on its way out, then on its way in.
    if (!def.selfReload) await tap('KeyR');
    const outAt = Math.round((def.reload.magOut + 0.2) / STEP);
    const inAt = Math.round((def.reload.magInsert - 0.03) / STEP);
    await h.skip(Math.max(1, outAt - 2));
    await snap('reload', `${gun}-reload-out`);
    await h.skip(Math.max(1, inAt - outAt - 1));
    await snap('reload', `${gun}-reload-in`);
    await h.skip(Math.ceil(def.reload.empty / STEP) + 20);
    const reloaded = await state();
    if (reloaded.mag !== def.magSize) problems.push(`${gun}: reload left ${reloaded.mag} in the magazine`);

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
