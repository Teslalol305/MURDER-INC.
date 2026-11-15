// Review (perf): which shader programs and textures appear after boot, per first-time event.
// node tools/shot.cjs dist/dev-all.html --params "autostart=1&q=low&god=1&noaudio=1" --size 640x360 --scenario tools/scenarios/review-perf-programs.cjs --timeout 600
module.exports = async (page, h) => {
  const snap = () => h.eval(() => {
    const G = window.__G; const r = G.renderer;
    const hash = (s) => { let x = 0; for (let i = 0; i < s.length; i++) x = (x * 31 + s.charCodeAt(i)) | 0; return (x >>> 0).toString(36); };
    const progs = (r.info.programs || []).map((p) => p.name + '#' + hash(String(p.cacheKey)) + ' ' + String(p.cacheKey).slice(0, 50).replace(/,/g, ' ') + ' … ' + String(p.cacheKey).slice(-40).replace(/,/g, ' '));
    const st = G.render.stats();
    return { progs, textures: r.info.memory.textures, geometries: r.info.memory.geometries, calls: st.calls, tris: st.triangles, frameCalls: st.frameCalls, heap: performance.memory.usedJSHeapSize };
  });
  let prev = null;
  const log = async (label) => {
    const s = await snap();
    const added = prev ? s.progs.filter((p) => !prev.progs.includes(p)) : [];
    console.log(`== ${label}: programs ${s.progs.length} (+${added.length}) textures ${s.textures}${prev ? ` (${s.textures - prev.textures >= 0 ? '+' : ''}${s.textures - prev.textures})` : ''} geometries ${s.geometries} calls ${s.calls} tris ${s.tris} frameCalls ${s.frameCalls} heapMB ${(s.heap / 1048576).toFixed(1)}`);
    for (const a of added) console.log('   + ' + a);
    prev = s;
  };
  await h.frames(3);
  await log('start view');
  // Timed frame: how long a drawn frame takes when programs compile.
  const timed = async (label, fn) => {
    console.log('-- ' + label);
    await h.eval(fn);
    const t0 = Date.now();
    await h.frames(1);
    const ms = Date.now() - t0;
    await h.frames(2);
    await log(`${label} (first frame ${ms} ms)`);
  };
  await timed('baseline frame', () => {});
  await page.mouse.move(320, 180);
  await timed('first player shot', () => { /* fire via key below */ });
  await h.key('Mouse0', true); await h.frames(3); await h.key('Mouse0', false); await h.frames(2);
  await log('after firing chopper');
  await timed('goon in view', () => {
    const G = window.__G; const p = G.player.pos; const f = new G.THREE.Vector3(Math.sin(G.player.yaw) * -6, 0, Math.cos(G.player.yaw) * -6);
    G.enemies.spawn('goon', new G.THREE.Vector3(p.x + f.x, 0, p.z + f.z), { passive: true });
  });
  await timed('buzzard in view', () => {
    const G = window.__G; const p = G.player.pos; const f = new G.THREE.Vector3(Math.sin(G.player.yaw) * -8, 0, Math.cos(G.player.yaw) * -8);
    G.enemies.spawn('buzzard', new G.THREE.Vector3(p.x + f.x + 2, 4, p.z + f.z), { passive: true });
  });
  await timed('goon killed', () => {
    const G = window.__G; for (const e of G.enemies.list) if (e.type === 'goon') G.enemies.damage(e, 999, { from: 'player', part: 'body', dir: new G.THREE.Vector3(0, 0, -1) });
  });
  await h.skip(30);
  await timed('buzzard killed', () => {
    const G = window.__G; for (const e of G.enemies.list) if (e.type === 'buzzard' && e.alive !== false) G.enemies.damage(e, 999, { from: 'player', part: 'body', dir: new G.THREE.Vector3(0, 0, -1) });
  });
  await h.skip(30);
  await timed('explosive lit (nearest)', () => {
    const G = window.__G; const p = G.player.pos; let best = null, bd = 1e9;
    for (const it of G.explosives.items) { const d = it.pos.distanceTo(p); if (d < bd && it.state === 'idle') { bd = d; best = it; } }
    window.__rvItem = best; G.explosives.damage(best, 1, 'player');
  });
  await h.skip(60);
  await timed('explosion (after fuse)', () => {});
  await h.skip(10);
  await timed('combat.explode in view', () => {
    const G = window.__G; const p = G.player.pos; const f = new G.THREE.Vector3(Math.sin(G.player.yaw) * -10, 0.5, Math.cos(G.player.yaw) * -10);
    G.combat.explode({ pos: new G.THREE.Vector3(p.x + f.x, 0.5, p.z + f.z), radius: 6.5, damage: 0, source: null });
  });
  await timed('impacts on several surfaces', () => {
    const G = window.__G; const p = G.player.pos; const n = new G.THREE.Vector3(0, 1, 0);
    for (const s of ['concrete', 'asphalt', 'metal', 'glass', 'wood', 'brick', 'dirt', 'flesh'])
      G.fx.impact(new G.THREE.Vector3(p.x - 2, 0.01, p.z - 3), n, s, new G.THREE.Vector3(0, -1, 0));
  });
  await timed('emitters fire/steam/jet', () => {
    const G = window.__G; const p = G.player.pos;
    for (const k of ['fire', 'steam', 'jet', 'smolder', 'embers', 'drip']) G.fx.addEmitter(new G.THREE.Vector3(p.x - 1, 0.3, p.z - 4), k, { ttl: 3 });
  });
  await timed('swap to nine', () => { window.__G.input.tap && window.__G.input.tap('weapon2'); });
  await h.skip(30); await h.frames(2); await log('nine out');
  await h.key('Mouse0', true); await h.frames(2); await h.key('Mouse0', false); await log('nine fired');
  await timed('melee', () => { window.__G.input.tap && window.__G.input.tap('melee'); });
  await h.skip(20); await h.frames(2); await log('melee done');
  await timed('train sent', () => { window.__G.atmos.passTrain(1, 0.5); });
  await h.skip(30); await timed('train overhead', () => {});
  await h.skip(200); await timed('train later', () => {});
  await timed('night switch', () => { window.__G.atmos.setTime('night'); });
  await h.frames(2); await log('night settled');
  await timed('back to day', () => { window.__G.atmos.setTime('day'); });
  await timed('player hit (post fx)', () => { const G = window.__G; G.player.invulnerable = false; G.player.damage && G.player.damage(1, { from: G.player.pos.clone().add(new G.THREE.Vector3(3, 0, 0)), kind: 'bullet' }); });
  await timed('pause menu', () => { window.__G.game.pause(); });
  await timed('resume', () => { window.__G.game.resume(); });
  const fin = await h.eval(() => ({ fx: window.__G.fx.stats(), en: window.__G.enemies.debug ? window.__G.enemies.debug() : null }));
  console.log(JSON.stringify(fin).slice(0, 1500));
};
