// Walks the gameplay stubs (input, player, weapon, enemies, explosives) through the testbed on the real
// physics and combat modules: wall, slide, jump, crouch, sprint, mouse look, the stair, shooting a dummy,
// reloading, being shot, regeneration, an explosive, and a nav path.
//
//   node build.mjs --dev --stub=input,level,player,explosives,weapon,enemies,game --out=dist/dev-phys.html
//   node tools/shot.cjs dist/dev-phys.html --params "autostart=1&q=low&noaudio=1" \
//        --scenario tools/scenarios/physics-stubs.cjs
//
// Prints one line per check and fails the run if any check fails. Screenshots go to shots/physics/.
// The checks are written against the stubs named in the build line: the stub level's layout (station
// wall at z = 12, stair to the deck at x 2 … 14, a propane tank at the foot of the deck) and the stub
// player, weapon and dummy numbers. Keep those modules stubbed when running it.

'use strict';

const SHOTS = 'shots/physics/';
const EAST = -Math.PI / 2; // yaw that looks toward +X
const MOUSE_RATE = 0.0021; // radians per pixel at sensitivity 1

module.exports = async (page, h) => {
  const lines = [];
  let failed = 0;
  const check = (name, ok, detail = '') => {
    lines.push(`${ok ? 'ok  ' : 'FAIL'}  ${name}${detail ? `  (${detail})` : ''}`);
    if (!ok) failed++;
  };
  const f = (n) => Math.round(n * 1000) / 1000;

  const player = () =>
    h.eval(() => {
      const p = __G.player;
      const { yaw, pitch, health, speed, onGround, crouching, surface } = p;
      return { x: p.pos.x, y: p.pos.y, z: p.pos.z, eyeY: p.eye.y, yaw, pitch, health, speed, onGround, crouching, surface };
    });
  const place = (x, y, z, yaw, pitch = 0) =>
    h.eval(([px, py, pz, pyaw, ppitch]) => {
      const p = __G.player;
      p.pos.set(px, py, pz);
      p.vel.set(0, 0, 0);
      p.yaw = pyaw;
      p.pitch = ppitch;
    }, [x, y, z, yaw, pitch]);
  const spawn = (type, x, y, z, alerted = false) =>
    h.eval(([t, px, py, pz, a]) => !!__G.enemies.spawn(t, new __G.THREE.Vector3(px, py, pz), { alerted: a }), [type, x, y, z, alerted]);
  const events = () => h.eval(() => ({ ...window.__seen }));

  // The starting patrol would wander into the test; count the events the checks care about.
  await h.eval(() => {
    __G.enemies.clear();
    window.__seen = {};
    const watched = [
      'player:step', 'player:jump', 'player:land', 'player:hit', 'weapon:fire', 'enemy:killed', 'enemy:fire',
      'explosive:lit', 'explosive:blast', 'explosion',
    ];
    for (const name of watched) {
      __G.events.on(name, () => {
        window.__seen[name] = (window.__seen[name] || 0) + 1;
      });
    }
  });
  // Park the pointer where h.key('Mouse0') will press, so that move never turns the view later on.
  const viewport = page.viewportSize();
  await page.mouse.move(viewport.width / 2, viewport.height / 2);
  // Mouse look needs the lock, or the fallback once the browser has refused it.
  await page.waitForFunction(() => __G.input.locked || __G.input.mode === 'drag', null, { timeout: 5000 }).catch(() => {});
  await h.skip(1);

  // ---- 1. into a wall, then along it (the station front, z = 12) -------------------------------
  let p = await player();
  const atStart = Math.abs(p.x + 40) < 1e-6 && Math.abs(p.z - 8.6) < 1e-6 && p.y === 0;
  check('starts at the level start', atStart, `${f(p.x)}, ${f(p.y)}, ${f(p.z)}`);
  await place(-40, 0, 8.6, Math.PI); // facing south
  await h.key('KeyW', true);
  await h.skip(20);
  p = await player();
  check('W walks at 3.8 m/s', Math.abs(p.speed - 3.8) < 1e-6, `speed ${f(p.speed)}`);
  await h.skip(70);
  await h.frames(1);
  p = await player();
  check('stopped one radius from the wall', Math.abs(p.z - (12 - 0.32)) < 0.005 && p.speed < 1e-6, `z ${f(p.z)}, speed ${f(p.speed)}`);
  await h.shot(`${SHOTS}1-wall.png`);
  await h.key('KeyD', true); // strafing right while facing south moves west
  await h.skip(30);
  await h.key('KeyD', false);
  await h.key('KeyW', false);
  let q = await player();
  check('slides along the wall', Math.abs(q.z - (12 - 0.32)) < 0.005 && q.x < p.x - 2, `x ${f(p.x)} → ${f(q.x)}, z ${f(q.z)}`);

  // ---- 2. jump, crouch, sprint on the open avenue --------------------------------------------
  await place(-36, 0, 0, EAST);
  await h.skip(2);
  await h.key('Space', true);
  let apex = 0;
  for (let i = 0; i < 12; i++) {
    await h.skip(2);
    apex = Math.max(apex, (await player()).y);
  }
  await h.key('Space', false);
  let seen = await events();
  const oneJump = seen['player:jump'] === 1 && seen['player:land'] === 1;
  check('Space jumps about one metre', apex > 0.9 && apex < 1.05 && oneJump, `apex ${f(apex)}`);
  await h.key('KeyC', true);
  await h.skip(15);
  p = await player();
  check('C crouches', p.crouching && Math.abs(p.eyeY - 1.05) < 0.02, `eye ${f(p.eyeY)}`);
  await h.key('KeyC', false);
  await h.skip(15);
  await h.key('ShiftLeft', true);
  await h.key('KeyW', true);
  await h.skip(30);
  p = await player();
  check('Shift + W sprints at 6.4 m/s', Math.abs(p.speed - 6.4) < 1e-6, `speed ${f(p.speed)}`);
  await h.key('ShiftLeft', false);
  await h.key('KeyW', false);
  await h.skip(10);
  seen = await events();
  check('footsteps were announced', seen['player:step'] >= 5, `${seen['player:step']} steps`);

  // ---- 3. mouse look ---------------------------------------------------------------------------
  await place(-36, 0, 0, EAST);
  await h.skip(1);
  await h.mouse(100, 30);
  await h.skip(1);
  p = await player();
  const look = await h.eval(() => `${__G.input.mode}${__G.input.locked ? ', locked' : ''}`);
  check(
    'mouse right turns right, mouse down looks down',
    Math.abs(p.yaw - (EAST - 100 * MOUSE_RATE)) < 1e-6 && Math.abs(p.pitch + 30 * MOUSE_RATE) < 1e-6,
    `yaw ${f(p.yaw - EAST)}, pitch ${f(p.pitch)}, ${look}`,
  );

  // ---- 4. up the stair onto the deck -----------------------------------------------------------
  await place(-6, 0, 10.7, EAST);
  await h.key('KeyW', true);
  let airborne = 0;
  for (let i = 0; i < 22; i++) {
    await h.skip(5);
    if (!(await player()).onGround) airborne++;
  }
  await h.key('KeyW', false);
  p = await player();
  const onDeck = Math.abs(p.y - 2.8) < 1e-6 && p.x > 2;
  check('walked up the stair onto the deck', onDeck && airborne === 0, `x ${f(p.x)}, y ${f(p.y)}, on ${p.surface}`);
  await h.eval(() => {
    __G.player.yaw = 0.9; // look back down at the avenue
    __G.player.pitch = -0.25;
  });
  await h.frames(2);
  await h.shot(`${SHOTS}2-deck.png`);

  // ---- 5. shoot a dummy, reload ----------------------------------------------------------------
  await place(-36, 0, 0, EAST);
  await spawn('goon', -27, 0, 0);
  await spawn('buzzard', -26, 4, -2);
  await h.frames(2);
  await h.shot(`${SHOTS}3-dummies.png`);
  let s = await h.eval(() => ({ aim: __G.enemies.aimTarget(__G.player.eye, __G.player.forward, 60), alive: __G.enemies.aliveCount() }));
  check('a dummy stands under the crosshair', s.aim && s.alive === 2);
  await h.key('Mouse0', true);
  await h.frames(3);
  await h.shot(`${SHOTS}4-firing.png`);
  await h.skip(12);
  await h.key('Mouse0', false);
  await h.skip(2);
  s = await h.eval(() => ({
    stats: { ...__G.combat.stats },
    goons: __G.enemies.countByType('goon'),
    mag: __G.weapon.mag,
    run: { ...__G.game.run },
  }));
  seen = await events();
  check(
    'left mouse fires 12 rounds a second',
    s.stats.shots === 6 && s.mag === 24 && seen['weapon:fire'] === 6,
    `${s.stats.shots} shots in 0.5 s, magazine ${s.mag}`,
  );
  check(
    'two head hits kill the goon',
    s.goons === 0 && s.stats.hits === 2 && s.stats.kills === 1 && s.stats.headshots === 1 && seen['enemy:killed'] === 1,
    JSON.stringify(s.stats),
  );
  check('the game reads the same numbers', s.run.kills === 1 && s.run.shots === 6 && s.run.hits === 2);
  await h.key('KeyR', true);
  await h.skip(1);
  await h.key('KeyR', false);
  const reloading = await h.eval(() => `${__G.weapon.state} / ${__G.weapon.cue}`);
  await h.skip(75);
  s = await h.eval(() => [__G.weapon.mag, __G.weapon.reserve]);
  const topped = s[0] === 30 && s[1] === 144;
  check('R reloads from the reserve', reloading === 'reloading / reloading' && topped, `${reloading}, then ${s.join(' / ')}`);

  // ---- 6. the buzzard heard that: get shot, then recover ---------------------------------------
  let lowest = 100;
  let flash = 0;
  let pictured = false;
  for (let i = 0; i < 40 && lowest > 75; i++) {
    await h.skip(15);
    const [health, red] = await h.eval(() => [__G.player.health, __G.render.post.damage]);
    lowest = Math.min(lowest, health);
    flash = Math.max(flash, red);
    if (red > 0.3 && !pictured) {
      pictured = true;
      await h.frames(1);
      await h.shot(`${SHOTS}5-hit.png`);
    }
  }
  seen = await events();
  s = await h.eval(() => ({ taken: __G.combat.stats.damageTaken, health: __G.player.health }));
  check(
    'the alerted buzzard shoots back and it hurts',
    lowest < 100 && seen['enemy:fire'] > 0 && seen['player:hit'] > 0 && Math.abs(s.taken - (100 - lowest)) < 1e-6 && flash > 0,
    `lowest health ${f(lowest)}, ${seen['enemy:fire']} shots at us, ${seen['player:hit']} hits`,
  );
  await h.eval(() => __G.enemies.clear());
  await h.skip(30 * 12);
  p = await player();
  check('health regenerates out of fire', p.health === 100, `health ${f(p.health)}`);

  // ---- 7. one round lights the propane tank at the foot of the deck ----------------------------
  await place(-4.6, 0, 7.6, EAST, Math.atan2(0.3 - 1.68, 6));
  await spawn('goon', 2.4, 0, 6.6);
  await h.frames(2);
  await h.shot(`${SHOTS}6-tank.png`);
  const before = await h.eval(() => __G.physics.boxes.length);
  await h.key('Mouse0', true);
  await h.skip(1);
  await h.key('Mouse0', false);
  s = await h.eval(() => __G.explosives.items.map((i) => [i.type, i.state, i.hp]));
  seen = await events();
  check('one round lights the tank', s[1][1] === 'lit' && s[1][2] === 24 && seen['explosive:lit'] === 1, JSON.stringify(s[1]));
  await h.skip(46);
  await h.frames(3);
  await h.shot(`${SHOTS}7-blast.png`);
  await h.skip(10);
  seen = await events();
  s = await h.eval(() => ({
    items: __G.explosives.items.map((i) => i.state),
    boxes: __G.physics.boxes.length,
    goons: __G.enemies.countByType('goon'),
    health: __G.player.health,
    kills: __G.combat.stats.kills,
    hits: __G.combat.stats.hits,
  }));
  check(
    '1.6 s later it blows: collider gone, goon beside it dead, player singed',
    s.items.join() === 'idle,gone,idle,idle' &&
      s.boxes === before - 1 &&
      seen.explosion === 1 &&
      seen['explosive:blast'] === 1 &&
      s.goons === 0 &&
      s.health < 100 &&
      s.health > 80,
    `colliders ${before} → ${s.boxes}, health ${f(s.health)}`,
  );
  check('the blast kill is a kill but not a hit', s.kills === 2 && s.hits === 2, `kills ${s.kills}, hits ${s.hits}`);
  await h.eval(() => __G.explosives.reset());
  s = await h.eval(() => [__G.explosives.items.map((i) => i.state).join(), __G.physics.boxes.length]);
  check('explosives.reset() puts it back', s[0] === 'idle,idle,idle,idle' && s[1] === before, `${s[0]}, ${s[1]} colliders`);

  // ---- 8. nav on the testbed: from the start to reel 2 inside the shop -------------------------
  s = await h.eval(() => {
    const nav = __G.physics.nav;
    const a = __G.level.playerStart.pos;
    const b = __G.level.objectives[1].pos;
    const t0 = performance.now();
    let path = null;
    for (let i = 0; i < 50; i++) path = nav.findPath(a, b);
    const ms = (performance.now() - t0) / 50;
    let clear = !!path;
    for (let i = 1; path && i < path.length; i++) clear = clear && nav.clearLine(path[i - 1], path[i]);
    const round = (n) => Math.round(n * 10) / 10;
    return { points: path && path.map((v) => `${round(v.x)},${round(v.z)}`), ms, expansions: nav.lastExpansions, clear };
  });
  check(
    'nav finds the way from the start into the shop',
    !!s.points && s.points.length >= 3 && s.clear && s.ms < 5,
    s.points ? `${s.points.length} waypoints, ${f(s.ms)} ms, ${s.expansions} expansions: ${s.points.join(' → ')}` : 'no path',
  );

  const errors = await h.errors();
  check('nothing was logged as an error', errors.length === 0, errors.slice(0, 3).join(' | '));

  console.log(lines.join('\n'));
  if (failed) throw new Error(`${failed} of ${lines.length} checks failed (tools/scenarios/physics-stubs.cjs)`);
};
