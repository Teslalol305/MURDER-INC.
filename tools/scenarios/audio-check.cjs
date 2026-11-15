// Audio, checked structurally (the sandbox has no sound card): unlock, render everything, fire every event
// and API call, measure every buffer (peak / RMS / punch, nothing clipped, nothing silent, guns loudest),
// render 8 bars of the score at each intensity offline, and check that late stems join phase-locked and
// that the drums sit on the bar grid.
//
//   node build.mjs --dev --only=audio --out=dist/dev-audio.html
//   node tools/shot.cjs dist/dev-audio.html --params "autostart=1&q=test" --scenario tools/scenarios/audio-check.cjs --timeout 240

const OUT = 'shots/audio';

module.exports = async (page, h) => {
  await h.frames(2);
  // Unlock, then let the background queue finish on its own (as in the game), polling.
  await h.eval(() => window.__G.audio.unlock());
  const t0 = Date.now();
  while ((await h.eval(() => window.__G.audio.debug.queued)) > 0 && Date.now() - t0 < 150000) await h.wait(1000);
  const boot = await h.eval(() => {
    const A = window.__G.audio;
    return { state: A.debug.ctx && A.debug.ctx.state, queued: A.debug.queued, mb: +(A.debug.bytes / 1e6).toFixed(1), names: A.debug.names().length };
  });
  boot.secs = Math.round((Date.now() - t0) / 1000);
  console.log('[audio] unlock + render all:', JSON.stringify(boot));
  if (!boot.state) throw new Error('no AudioContext after unlock()');
  if (boot.queued) throw new Error(`queue not empty after flush: ${boot.queued}`);
  if (boot.mb > 40) throw new Error(`decoded buffers over budget: ${boot.mb} MB`);

  // Every API member and every event the module listens to, with plausible payloads.
  const fired = await h.eval(() => {
    const G = window.__G;
    const A = G.audio;
    const V = (x, y, z) => new G.THREE.Vector3(x, y, z);
    const cam = G.camera.position.clone();
    const near = cam.clone().add(V(4, 0, -3));
    const e = { id: 991, type: 'goon', pos: near.clone(), alive: true, vel: V(1, 0, 0) };
    const b = { id: 992, type: 'buzzard', pos: cam.clone().add(V(-6, 4, -8)), alive: true, vel: V(4, 0, 0) };
    const ev = (n, p) => G.events.emit(n, p);
    A.setVolume(0.7);
    A.setInterior(0.5);
    A.setMusicIntensity(0.6);
    for (const w of ['chopper', 'nine']) {
      ev('weapon:fire', { weapon: w, pos: cam, dir: V(0, 0, -1), ads: 0 });
      ev('weapon:dry', { weapon: w });
      for (const phase of ['start', 'magout', 'magin', 'bolt', 'done', 'cancel']) ev('weapon:reload', { weapon: w, phase, empty: true });
      ev('weapon:switch', { from: w, to: w === 'nine' ? 'chopper' : 'nine', phase: 'holster' });
      ev('weapon:switch', { from: w, to: w === 'nine' ? 'chopper' : 'nine', phase: 'draw' });
    }
    ev('weapon:swing', { weapon: 'chopper' });
    ev('weapon:melee', { hit: true });
    for (const s of ['asphalt', 'metal', 'wood']) ev('shell:bounce', { pos: near, surface: s });
    for (const s of ['asphalt', 'concrete', 'metal', 'wood', 'dirt', 'brick', 'glass']) ev('player:step', { pos: cam, surface: s, sprint: s === 'metal' });
    ev('player:jump', {});
    ev('player:land', { speed: 6, surface: 'concrete' });
    ev('player:hit', { amount: 18, from: near, health: 60, kind: 'bullet' });
    ev('player:hitEnemy', { enemy: e, part: 'head', killed: false, damage: 30, weapon: 'chopper' });
    ev('player:hitEnemy', { enemy: e, part: 'body', killed: false, damage: 30, weapon: 'chopper' });
    ev('player:hitEnemy', { enemy: e, part: 'body', killed: true, damage: 30, weapon: 'chopper' });
    for (const s of ['concrete', 'brick', 'metal', 'car', 'glass', 'wood', 'dirt', 'asphalt', 'rubber', 'cloth']) {
      ev('impact', { point: near, normal: V(0, 1, 0), surface: s, dir: V(0, 0, -1), from: 'player', enemy: null });
    }
    ev('impact', { point: near, normal: V(0, 1, 0), surface: 'flesh', dir: V(0, 0, -1), from: 'player', enemy: e });
    ev('enemy:spawn', { enemy: e });
    ev('enemy:spawn', { enemy: b });
    ev('enemy:alert', { enemy: e, pos: e.pos });
    ev('enemy:alert', { enemy: b, pos: b.pos });
    ev('enemy:telegraph', { enemy: e, type: 'goon', duration: 0.5, pos: e.pos });
    ev('enemy:telegraph', { enemy: b, type: 'buzzard', duration: 0.46, pos: b.pos });
    // A burst aimed just past the listener's head: the whizz.
    const muzzle = cam.clone().add(V(0, 0, -20));
    ev('enemy:fire', { enemy: e, type: 'goon', pos: muzzle, dir: cam.clone().add(V(1, 0, 0)).sub(muzzle).normalize() });
    ev('enemy:fire', { enemy: b, type: 'buzzard', pos: b.pos, dir: V(0, 0, 1) });
    ev('enemy:melee', { enemy: e, phase: 'windup', pos: e.pos });
    ev('enemy:melee', { enemy: e, phase: 'strike', pos: e.pos });
    ev('enemy:hit', { enemy: e, part: 'body', damage: 10, point: e.pos });
    ev('enemy:step', { enemy: e, pos: e.pos, surface: 'asphalt' });
    ev('enemy:killed', { enemy: e, type: 'goon', pos: e.pos, part: 'body', byPlayer: true, weapon: 'chopper' });
    ev('explosion', { pos: cam.clone().add(V(12, 0, 0)), radius: 6.5, size: 'big', source: null });
    ev('explosion', { pos: cam.clone().add(V(30, 0, 0)), radius: 3, size: 'small', source: null });
    ev('objective:progress', { id: 'reel1', t: 0.4 });
    ev('radio:line', { speaker: 'Rule', text: 'test', secs: 1 });
    ev('ui:click', {});
    ev('ui:hover', {});
    ev('train:pass', { phase: 'approach', duration: 2, dir: 1 });
    const hiss = A.loop('hiss', { pos: near, volume: 0.25 });
    hiss.setVolume(1);
    hiss.setPos(near.clone().add(V(0, 1, 0)));
    window.__audioHiss = hiss;
    // Every sound by name, once, at the listener: nothing throws, and each gets a voice or a fair refusal.
    let played = 0;
    let refused = 0;
    for (const n of A.debug.names()) {
      const def = n.startsWith('stem_') || n === 'boombox' || n.startsWith('bed_');
      if (def) continue;
      const handle = A.play(n, { pos: near, volume: 0.2 });
      if (handle) played++;
      else refused++;
    }
    for (const s of ['reel', 'all']) A.sting(s);
    return { played, refused, voices: A.debug.voices() };
  });
  console.log('[audio] fired every event, played:', JSON.stringify(fired));
  await h.skip(45);
  const mid = await h.eval(() => {
    const G = window.__G;
    G.events.emit('train:pass', { phase: 'over', duration: 1.5, dir: 1 });
    G.events.emit('objective:done', { id: 'reel1', index: 1, total: 3 });
    G.audio.setPaused(true);
    return { loops: G.audio.debug.loops(), muffle: +G.audio.debug.muffle.toFixed(2), interior: +G.audio.debug.interior.toFixed(2) };
  });
  console.log('[audio] loops mid-run:', JSON.stringify(mid.loops.filter((l) => l.playing).map((l) => l.name)), 'muffle', mid.muffle, 'interior', mid.interior);
  await h.skip(30);
  await h.eval(() => {
    const G = window.__G;
    G.audio.setPaused(false);
    G.events.emit('train:pass', { phase: 'gone', duration: 1, dir: 1 });
    window.__audioHiss.stop();
    G.audio.sting('dead');
    G.audio.sting('complete');
    G.events.emit('game:reset', { mode: 'mission' });
  });
  await h.skip(60);
  await h.frames(2);
  await h.shot(`${OUT}/check-after-events.png`);

  // Every buffer, measured as it leaves its bus at default volume.
  const rows = await h.eval(() => window.__G.audio.debug.measureAll());
  rows.sort((a, b) => b.punch - a.punch);
  const pad = (s, n) => String(s).padEnd(n);
  console.log('[audio] buffers (peak and rms × bus gain × vol; punch = rms of the first 100 ms):');
  console.log(`  ${pad('name', 18)}${pad('bus', 7)}${pad('secs', 7)}${pad('peak', 8)}${pad('rms', 8)}punch`);
  for (const r of rows) console.log(`  ${pad(r.name, 18)}${pad(r.bus, 7)}${pad(r.secs, 7)}${pad(r.peak, 8)}${pad(r.rms, 8)}${r.punch}`);
  const clipped = rows.filter((r) => r.peak > 1.0);
  const silent = rows.filter((r) => r.rms < 2e-4);
  if (clipped.length) throw new Error(`clipped: ${clipped.map((r) => r.name).join(', ')}`);
  if (silent.length) throw new Error(`silent: ${silent.map((r) => r.name).join(', ')}`);
  const gun = Math.min(...rows.filter((r) => r.name === 'chopper_shot' || r.name === 'nine_shot').map((r) => r.punch));
  // Guns over every other effect (blasts may match them; the score is mixed by the conductor, not here).
  const louder = rows.filter((r) => r.punch > gun && !/^(chopper|nine)_shot$/.test(r.name) && !/^explosion_/.test(r.name) && r.bus !== 'music');
  if (louder.length) throw new Error(`louder than the guns: ${louder.map((r) => r.name).join(', ')}`);

  // The score, offline.
  const music = await h.eval(async () => {
    const D = window.__G.audio.debug;
    const out = {};
    for (const I of [0.15, 0.6, 1]) {
      const r = await D.renderMusic(I, 8);
      out[I] = { peak: +r.peak.toFixed(3), rms: +r.rms.toFixed(4) };
    }
    // Phase lock: stems that join late (off the grid) must match the run where they were there from the start.
    const ref = await D.renderMusic(0.6, 4, { keep: true });
    const late = await D.renderMusic(0.6, 4, { keep: true, late: ['drums', 'bass', 'keys'] });
    const from = Math.round((D.BAR * 1.37 + 0.06) * ref.sr);
    let diff = 0;
    let level = 0;
    for (let i = from; i < ref.data.length; i++) {
      diff = Math.max(diff, Math.abs(ref.data[i] - late.data[i]));
      level = Math.max(level, Math.abs(ref.data[i]));
    }
    // Lag: the shift (in samples) that best lines the late run up with the reference; 0 = phase-locked.
    // (A stem rendered at a lower rate than the context differs by interpolation only, never by time.)
    let best = 0;
    let bestLag = 0;
    for (let lag = -30; lag <= 30; lag++) {
      let s = 0;
      for (let i = from; i < from + ref.sr; i++) s += ref.data[i] * late.data[i + lag];
      if (s > best) {
        best = s;
        bestLag = lag;
      }
    }
    out.lateJoin = { maxDiff: +diff.toFixed(5), level: +level.toFixed(3), lag: bestLag };
    // Grid: the drums alone, the first hit after every bar line.
    const drums = await D.renderMusic(0.6, 8, { keep: true, solo: 'drums' });
    let pk = 0;
    for (const v of drums.data) pk = Math.max(pk, Math.abs(v));
    const errs = [];
    for (let bar = 0; bar < 8; bar++) {
      const start = Math.round(bar * D.BAR * drums.sr);
      let i = Math.max(0, start - Math.round(0.01 * drums.sr));
      // Skip whatever rings over from the bar before, then find the kick's attack.
      while (i < drums.data.length && Math.abs(drums.data[i]) > 0.25 * pk && i < start) i++;
      while (i < drums.data.length && Math.abs(drums.data[i]) < 0.4 * pk) i++;
      errs.push(+(((i - start) / drums.sr) * 1000).toFixed(2));
    }
    out.gridMs = errs;
    return out;
  });
  console.log('[audio] music offline (8 bars):', JSON.stringify(music));
  if (!(music[0.15].rms < music[0.6].rms && music[0.6].rms < music[1].rms)) throw new Error('music levels do not rise with intensity');
  for (const I of [0.15, 0.6, 1]) if (music[I].peak > 1 || music[I].rms < 0.005) throw new Error(`music level at ${I}: ${JSON.stringify(music[I])}`);
  if (music.lateJoin.lag !== 0 || music.lateJoin.maxDiff > 0.05 * music.lateJoin.level) throw new Error(`late stems out of phase: ${JSON.stringify(music.lateJoin)}`);
  if (music.gridMs.some((e) => e < -1 || e > 12)) throw new Error(`drums off the grid: ${music.gridMs}`);

  // Another module's unfinished contract is reported, not counted against audio.
  const errs = (await h.errors()).map(String);
  const others = errs.filter((e) => /^\[contract\] G\.(?!audio)/.test(e));
  if (others.length) console.log('[audio] not ours:', JSON.stringify(others));
  const mine = errs.filter((e) => !others.includes(e));
  if (mine.length) throw new Error(`page errors: ${JSON.stringify(mine).slice(0, 400)}`);
};
