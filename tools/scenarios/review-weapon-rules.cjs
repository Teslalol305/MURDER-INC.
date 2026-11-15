// Review probe (read-only): ammo / reload / swap / melee accounting through real input.
'use strict';

module.exports = async (page, h) => {
  const W = () => h.eval(() => {
    const G = window.__G;
    const w = G.weapon;
    return { cur: w.current, mag: w.mag, res: w.reserve, other: { ...w.other }, state: w.state, shots: G.combat.stats.shots, hits: G.combat.stats.hits, kills: G.combat.stats.kills, ads: Math.round(G.player.ads * 100) / 100 };
  });
  const log = async (k) => console.log(k, JSON.stringify(await W()));
  await page.mouse.move(480, 270);
  await h.eval(() => {
    const G = window.__G;
    G.enemies.clear();
    G.player.invulnerable = true;
    G.player.pitch = 0.6; // look up at the sky
  });
  await h.skip(5);
  await log('start');
  await h.key('Mouse0', true);
  await h.skip(25); // ~0.83 s → 10 rounds at 720 rpm
  await h.key('Mouse0', false);
  await h.skip(2);
  await log('after-burst');
  // tactical reload, cancelled by a swap before mag-in
  await h.key('KeyR', true); await h.skip(1); await h.key('KeyR', false);
  await h.skip(28); // ~0.95 s
  await log('reload-mid');
  await h.key('KeyQ', true); await h.skip(1); await h.key('KeyQ', false);
  await h.skip(30);
  await log('after-swap');
  await h.key('KeyQ', true); await h.skip(1); await h.key('KeyQ', false);
  await h.skip(30);
  await log('back-to-chopper');
  // reload cancelled by melee before mag-in
  await h.key('KeyR', true); await h.skip(1); await h.key('KeyR', false);
  await h.skip(15);
  await h.key('KeyF', true); await h.skip(1); await h.key('KeyF', false);
  await h.skip(30);
  await log('after-melee-cancel');
  // reload cancelled by melee after mag-in
  await h.key('KeyR', true); await h.skip(1); await h.key('KeyR', false);
  await h.skip(50); // 1.67 s > 1.44
  await h.key('KeyF', true); await h.skip(1); await h.key('KeyF', false);
  await h.skip(30);
  await log('after-melee-late');

  // melee a goon standing in front
  await h.eval(() => {
    const G = window.__G;
    G.player.pitch = 0;
    const p = G.player.pos;
    const f = G.player.forward;
    const at = new G.THREE.Vector3(p.x + f.x * 1.6, p.y, p.z + f.z * 1.6);
    window.__goon = G.enemies.spawn('goon', at, { alerted: false, passive: true });
    window.__goonInfo = { at: at.toArray(), ok: !!window.__goon };
  });
  await h.skip(3);
  console.log('goon', JSON.stringify(await h.eval(() => ({ ...window.__goonInfo, hp: window.__goon && window.__goon.hp, pos: window.__goon && window.__goon.pos.toArray() }))));
  for (let i = 0; i < 3; i++) {
    await h.key('KeyF', true); await h.skip(1); await h.key('KeyF', false);
    await h.skip(25);
  }
  console.log('goon-after', JSON.stringify(await h.eval(() => ({ hp: window.__goon.hp, alive: window.__goon.alive }))));
  await log('after-melee-kill');

  // ADS then sprint: does sprint break ADS / gun lower, speed?
  await h.key('Mouse2', true);
  await h.skip(10);
  await h.key('ShiftLeft', true);
  await h.key('KeyW', true);
  await h.skip(20);
  console.log('ads+sprint', JSON.stringify(await h.eval(() => ({ ads: __G.player.ads, sprinting: __G.player.sprinting, speed: __G.player.speed, wstate: __G.weapon.state }))));
  await h.key('Mouse2', false);
  await h.skip(20);
  console.log('sprint-only', JSON.stringify(await h.eval(() => ({ ads: __G.player.ads, sprinting: __G.player.sprinting, speed: __G.player.speed, wstate: __G.weapon.state }))));
  await h.key('KeyR', true); await h.skip(1); await h.key('KeyR', false);
  await h.skip(10);
  console.log('sprint-reload', JSON.stringify(await h.eval(() => ({ sprinting: __G.player.sprinting, speed: __G.player.speed, wstate: __G.weapon.state }))));
  await h.key('ShiftLeft', false);
  await h.key('KeyW', false);
  await h.skip(60);
  await log('end');
  console.log('errors', JSON.stringify(await h.errors()));
};
