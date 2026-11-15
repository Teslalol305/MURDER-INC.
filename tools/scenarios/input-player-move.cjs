// The real input and player modules on the stub testbed, driven the way a player drives them: keys and
// mouse through the browser, with a director's hand only for staging (a few test boxes, teleports,
// scripted hits).
//
//   node build.mjs --dev --only=input,player --out=dist/dev-input-player.html
//   node tools/shot.cjs dist/dev-input-player.html --params "autostart=1&q=low&noaudio=1" \
//        --scenario tools/scenarios/input-player-move.cjs --timeout 400
//
// Walk · sprint · mouse look · key turning · crouch under a beam · step onto 0.4 m · stopped by 0.5 m ·
// jump onto it · the stair · a fall with damage · hits, regeneration · death and the death camera · retry.
// Prints one line per check and fails the run if any check fails. Screenshots go to shots/input-player/.
// Written against the stub level (start at (−40, 0, 8.6), the stair to the deck at x 2 … 14): keep every
// module but input and player stubbed.

'use strict';

const OUT = 'shots/input-player/move-';
const EAST = -Math.PI / 2; // yaw that looks toward +X
const DT = 0.0333;
const MOUSE_RATE = 0.0021;

module.exports = async (page, h) => {
  const lines = [];
  let failed = 0;
  const check = (name, ok, detail = '') => {
    lines.push(`${ok ? 'ok  ' : 'FAIL'}  ${name}${detail ? `  (${detail})` : ''}`);
    if (!ok) failed++;
  };
  const f = (n) => Math.round(n * 1000) / 1000;
  const steps = (seconds) => Math.round(seconds / DT);

  const state = () =>
    h.eval(() => {
      const G = window.__G;
      const p = G.player;
      const c = G.camera;
      return {
        x: p.pos.x, y: p.pos.y, z: p.pos.z, yaw: p.yaw, pitch: p.pitch, eyeY: p.eye.y,
        speed: p.speed, onGround: p.onGround, crouching: p.crouching, sprinting: p.sprinting,
        health: p.health, alive: p.alive, surface: p.surface, trauma: p.trauma,
        camY: c.position.y, camPitch: c.rotation.x, camRoll: c.rotation.z, fov: c.fov,
        post: { ...G.render.post }, game: G.game.state, mode: G.input.mode, locked: G.input.locked,
        seen: { ...window.__seen }, last: { ...window.__last },
      };
    });
  const place = (x, y, z, yaw, pitch = 0) =>
    h.eval(([px, py, pz, pyaw, ppitch]) => {
      const p = window.__G.player;
      p.pos.set(px, py, pz);
      p.vel.set(0, 0, 0);
      p.yaw = pyaw;
      p.pitch = ppitch;
    }, [x, y, z, yaw, pitch]);

  // ---- staging -----------------------------------------------------------------------------------
  await h.eval(() => {
    const G = window.__G;
    const THREE = G.THREE;
    G.enemies.clear(); // the patrol would walk into the test
    window.__seen = {};
    window.__last = {};
    for (const name of ['player:step', 'player:jump', 'player:land', 'player:hit', 'player:dead', 'input:lock', 'input:device']) {
      G.events.on(name, (e) => {
        window.__seen[name] = (window.__seen[name] || 0) + 1;
        const flat = {};
        for (const key in e) flat[key] = e[key] && e[key].isVector3 ? e[key].toArray() : e[key];
        window.__last[name] = flat;
      });
    }
    // Test furniture on the open roadway: a 0.4 m ledge, a 0.5 m ledge and a beam to crouch under.
    const block = (x0, x1, y0, y1, z0, z1, color, surface) => {
      const mesh = new THREE.Mesh(
        new THREE.BoxGeometry(x1 - x0, y1 - y0, z1 - z0),
        new THREE.MeshStandardMaterial({ color, roughness: 0.8 }),
      );
      mesh.position.set((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
      G.scene.add(mesh);
      G.physics.addBox({ min: [x0, y0, z0], max: [x1, y1, z1], surface });
    };
    block(-33, -30.6, 0, 0.4, -3.2, -0.8, 0x8a6a3a, 'wood');
    block(-33, -30.6, 0, 0.5, 0.8, 3.2, 0x55606a, 'metal');
    block(-27.5, -24.5, 1.3, 2.0, -1.6, 1.6, 0xf6c21a, 'metal');
  });
  const viewport = page.viewportSize();
  await page.mouse.move(viewport.width / 2, viewport.height / 2); // park the pointer mid-screen
  await page.waitForFunction(() => window.__G.input.locked || window.__G.input.mode === 'drag', null, { timeout: 5000 }).catch(() => {});
  await h.skip(2);

  // ---- 1. start, walk, sprint ---------------------------------------------------------------------
  let s = await state();
  check('starts at the level start, facing east', Math.abs(s.x + 40) < 1e-6 && Math.abs(s.z - 8.6) < 1e-6 && Math.abs(s.yaw - EAST) < 1e-6, `${f(s.x)}, ${f(s.z)}`);
  // Headless Chromium grants the lock without a click; a real browser refuses and the fallback steps in.
  // Either way the look mode is decided. (input-player-lock.cjs plays both paths on purpose.)
  check('the look mode is decided', s.locked ? s.mode === 'lock' : s.mode === 'drag', `mode ${s.mode}${s.locked ? ', locked' : ''}`);
  const hint = await h.eval(() => window.__G.input.hint());
  check('input.hint() describes it', s.locked ? /Esc/.test(hint) : /edge/.test(hint), hint);

  await place(-39, 0, 0, EAST);
  await h.key('KeyW', true);
  await h.skip(4);
  s = await state();
  check('W reaches walk speed in 0.11 s (4 frames at 30 fps)', Math.abs(s.speed - 3.8) < 1e-6, `speed ${f(s.speed)}`);
  await h.skip(26);
  await h.frames(2);
  await h.shot(`${OUT}1-walk.png`);
  s = await state();
  check('walking: 3.8 m/s, footsteps on asphalt', Math.abs(s.speed - 3.8) < 1e-6 && s.seen['player:step'] >= 2 && s.last['player:step'].surface === 'asphalt', `${s.seen['player:step']} steps`);
  check('walking: field of view stays at the setting', Math.abs(s.fov - 74) < 0.2, `fov ${f(s.fov)}`);

  await place(-39, 0, 0, EAST);
  await h.key('ShiftLeft', true);
  await h.skip(30);
  await h.frames(2);
  await h.shot(`${OUT}2-sprint.png`);
  s = await state();
  check('Shift + W sprints at 6.4 m/s with a wider view', Math.abs(s.speed - 6.4) < 1e-6 && s.sprinting && s.fov > 79 && s.fov < 80.1, `speed ${f(s.speed)}, fov ${f(s.fov)}`);
  check('sprint steps are announced as sprint steps', s.last['player:step'].sprint === true);
  // Firing cancels the sprint.
  await h.key('Mouse0', true);
  await h.skip(8);
  s = await state();
  check('holding fire drops out of the sprint', !s.sprinting && Math.abs(s.speed - 3.8) < 1e-6, `speed ${f(s.speed)}`);
  await h.key('Mouse0', false);
  await h.key('ShiftLeft', false);
  await h.key('KeyW', false);
  await h.skip(10);
  s = await state();
  check('stops within a third of a second', s.speed === 0, `speed ${f(s.speed)}`);

  // ---- 2. looking: mouse, keys --------------------------------------------------------------------
  await place(-36, 0, 0, EAST);
  await h.skip(1);
  await h.mouse(100, 30);
  await h.skip(1);
  s = await state();
  check('mouse right turns right, mouse down looks down, 0.0021 rad per pixel',
    Math.abs(s.yaw - (EAST - 100 * MOUSE_RATE)) < 1e-6 && Math.abs(s.pitch + 30 * MOUSE_RATE) < 1e-6, `yaw ${f(s.yaw - EAST)}, pitch ${f(s.pitch)}`);
  await h.mouse(450, 0); // larger than 400 px in one event: a pointer-lock glitch, dropped
  await h.skip(1);
  let t = await state();
  check('a 450 px jump in one mouse event is discarded', Math.abs(t.yaw - s.yaw) < 1e-9);
  await place(-36, 0, 0, EAST);
  await h.key('ArrowLeft', true);
  await h.key('KeyI', true);
  await h.skip(30);
  await h.key('ArrowLeft', false);
  await h.key('KeyI', false);
  s = await state();
  check('arrow keys and I J K L turn at a fixed rate (2.1 and 1.26 rad/s)',
    Math.abs(s.yaw - (EAST + 2.1 * 30 * DT)) < 1e-3 && Math.abs(s.pitch - 1.26 * 30 * DT) < 1e-3, `yaw +${f(s.yaw - EAST)}, pitch ${f(s.pitch)}`);

  // ---- 3. crouch under the beam -------------------------------------------------------------------
  await place(-29.6, 0, 0, EAST);
  await h.key('KeyW', true);
  await h.skip(steps(1.2));
  s = await state();
  check('standing, the beam (1.3 m clear) is a wall', Math.abs(s.x - (-27.5 - 0.32)) < 0.01 && s.speed < 1e-6, `x ${f(s.x)}`);
  await h.key('KeyC', true);
  await h.skip(steps(0.5));
  s = await state();
  check('C crouches: eye at 1.05 m, 1.9 m/s', s.crouching && Math.abs(s.eyeY - 1.05) < 0.03 && Math.abs(s.speed - 1.9) < 1e-6, `eye ${f(s.eyeY)}, speed ${f(s.speed)}`);
  await h.skip(steps(0.8));
  await h.key('KeyC', false);
  await h.key('KeyW', false);
  await h.skip(steps(0.5));
  await h.frames(2);
  await h.shot(`${OUT}3-under-the-beam.png`);
  s = await state();
  check('under the beam, letting go of C keeps the crouch (no headroom)', s.crouching && s.x > -27.3 && s.x < -24.7, `x ${f(s.x)}, crouching ${s.crouching}`);
  await h.key('Space', true);
  await h.skip(4);
  await h.key('Space', false);
  t = await state();
  check('and a jump is refused there', (t.seen['player:jump'] || 0) === 0 && t.y === 0);
  await h.key('KeyW', true);
  await h.skip(steps(2));
  await h.key('KeyW', false);
  s = await state();
  check('past the beam the player stands up by himself', !s.crouching && s.x > -24 && Math.abs(s.eyeY - 1.68) < 0.05, `x ${f(s.x)}, eye ${f(s.eyeY)}`);

  // ---- 4. ledges ----------------------------------------------------------------------------------
  await place(-35, 0, -2, EAST);
  await h.key('KeyW', true);
  await h.skip(steps(1));
  s = await state();
  check('walks straight onto the 0.4 m ledge (step-up)', Math.abs(s.y - 0.4) < 1e-6 && s.surface === 'wood' && !s.seen['player:land'], `y ${f(s.y)} on ${s.surface}`);
  await place(-35, 0, 2, EAST);
  await h.skip(steps(1));
  await h.frames(2);
  await h.shot(`${OUT}4-ledge-0.5m.png`);
  s = await state();
  check('is stopped by the 0.5 m ledge', s.y === 0 && Math.abs(s.x - (-33 - 0.32)) < 0.01, `x ${f(s.x)}, y ${f(s.y)}`);
  await h.key('Space', true);
  let apex = 0;
  for (let i = 0; i < 8; i++) {
    await h.skip(2);
    apex = Math.max(apex, (await state()).y);
  }
  await h.key('Space', false);
  await h.skip(steps(0.3));
  await h.key('KeyW', false);
  s = await state();
  check('Space jumps about a metre and lands on it', apex > 0.9 && apex < 1.05 && Math.abs(s.y - 0.5) < 1e-6 && s.surface === 'metal' && s.seen['player:jump'] === 1 && s.seen['player:land'] === 1,
    `apex ${f(apex)}, y ${f(s.y)} on ${s.surface}`);

  // ---- 5. the stair to the deck -------------------------------------------------------------------
  await place(-4.5, 0, 10.7, EAST);
  await h.skip(1);
  await h.key('KeyW', true);
  let airborne = 0;
  let worstEye = 0;
  let eye = (await state()).eyeY;
  let pictured = false;
  for (let i = 0; i < 60; i++) {
    await h.skip(1);
    s = await state();
    if (!s.onGround) airborne++;
    worstEye = Math.max(worstEye, Math.abs(s.eyeY - eye));
    eye = s.eyeY;
    if (!pictured && s.y > 1.2) {
      pictured = true;
      await h.frames(1);
      await h.shot(`${OUT}5-on-the-stair.png`);
      eye = (await state()).eyeY;
    }
  }
  await h.key('KeyW', false);
  await h.skip(steps(0.6));
  s = await state();
  check('climbs the 11 risers to the deck without leaving the ground', Math.abs(s.y - 2.8) < 1e-6 && airborne === 0 && s.surface === 'wood', `y ${f(s.y)}, airborne frames ${airborne}`);
  check('the eye glides up the stair (no 0.25 m pops)', worstEye < 0.15, `largest move in one 30 fps frame ${f(worstEye)} m`);
  check('and settles at eye height on the deck', Math.abs(s.eyeY - (2.8 + 1.68)) < 0.01, `eye ${f(s.eyeY)}`);
  await h.eval(() => {
    window.__G.player.yaw = 0.9; // look back down at the avenue
    window.__G.player.pitch = -0.25;
  });
  await h.frames(2);
  await h.shot(`${OUT}6-deck.png`);

  // ---- 6. falling ---------------------------------------------------------------------------------
  // Off the west end of the deck: 2.8 m, a hard landing but no damage.
  const before = (await state()).seen;
  await place(3, 2.8, 9.4, Math.PI / 2);
  await h.key('KeyW', true);
  let dip = 0;
  let rocked = 0;
  for (let i = 0; i < 45; i++) {
    await h.skip(1);
    s = await state();
    if (s.onGround && s.y < 1) dip = Math.max(dip, s.y + 1.68 - s.eyeY);
    rocked = Math.max(rocked, s.trauma);
  }
  await h.key('KeyW', false);
  s = await state();
  check('a 2.8 m drop: lands hard, dips the view, rocks the camera, costs nothing',
    s.y < 0.5 && s.health === 100 && s.seen['player:land'] === (before['player:land'] || 0) + 1 && dip > 0.08 && rocked > 0.1,
    `landing speed ${f(s.last['player:land'].speed)} m/s, dip ${f(dip)} m, trauma ${f(rocked)}`);
  // Nine metres (beside the avenue: the El's track deck hangs over the roadway): (speed − 13) × 7.
  await place(-40, 9, 8.6, EAST);
  let flash = 0;
  pictured = false;
  for (let i = 0; i < 40; i++) {
    await h.skip(1);
    s = await state();
    flash = Math.max(flash, s.post.damage);
    if (!pictured && s.post.damage > 0.5) {
      pictured = true;
      await h.frames(1);
      await h.shot(`${OUT}7-fall-damage.png`);
    }
  }
  const expected = 100 - (Math.sqrt(2 * 21 * 9) - 13) * 7;
  check('a 9 m fall costs (speed − 13) × 7 health and flashes red', Math.abs(s.health - expected) < 4 && s.last['player:hit'].kind === 'fall' && flash > 0.9,
    `health ${f(s.health)}, expected about ${f(expected)}`);

  // ---- 7. hits and regeneration -------------------------------------------------------------------
  await h.eval(() => {
    const G = window.__G;
    G.player.heal(100);
    G.player.damage(25, new G.THREE.Vector3(-20, 1.2, 0), 'bullet');
  });
  await h.frames(1);
  await h.shot(`${OUT}8-hit.png`);
  s = await state();
  check('a 25 point hit: health 75, red pulse, camera shake', s.health === 75 && s.post.damage > 0.8 && s.trauma > 0.4 && Math.abs(s.camRoll) > 1e-4 && s.last['player:hit'].amount === 25,
    `post.damage ${f(s.post.damage)}, trauma ${f(s.trauma)}, roll ${f(s.camRoll)}`);
  await h.eval(() => window.__G.player.damage(60, new window.__G.THREE.Vector3(-20, 1.2, 0), 'bullet'));
  await h.skip(steps(1.2));
  await h.frames(2);
  await h.shot(`${OUT}9-low-health.png`);
  s = await state();
  check('at 15 health the low-health look is nearly full', s.health === 15 && s.post.lowHealth > 0.9, `post.lowHealth ${f(s.post.lowHealth)}`);
  const regen = await h.eval(() => ({ ...window.__G.player.regen }));
  await h.skip(steps(regen.delay - 1.2 - 0.2));
  s = await state();
  check(`nothing comes back for ${regen.delay} s`, s.health === 15, `health ${f(s.health)}`);
  await h.skip(steps(0.2 + 1));
  t = await state();
  check(`then ${regen.rate} a second`, Math.abs(t.health - (15 + regen.rate)) < regen.rate * 0.1, `health ${f(t.health)} one second in`);
  await h.skip(steps(85 / regen.rate));
  s = await state();
  check('back to full health, screen clean', s.health === 100 && s.post.lowHealth < 0.05 && s.post.damage === 0, `health ${f(s.health)}`);

  // ---- 8. death -----------------------------------------------------------------------------------
  await place(-36, 0, 0, EAST);
  await h.skip(2);
  await h.eval(() => window.__G.player.damage(500, new window.__G.THREE.Vector3(-36, 1.2, -20), 'bullet')); // from the left
  await h.skip(steps(0.45));
  await h.frames(1);
  await h.shot(`${OUT}10-dying.png`);
  s = await state();
  check('dead: health 0, the game knows, the camera is on its way down', !s.alive && s.health === 0 && s.game === 'dead' && s.seen['player:dead'] === 1 && s.camY < 1.6 && s.camY > 0.25,
    `camera at ${f(s.camY)} m, roll ${f(s.camRoll)}`);
  await h.skip(steps(1.1));
  await h.frames(2);
  await h.shot(`${OUT}11-dead.png`);
  s = await state();
  check('the camera ends on the floor, on its right side: away from the shot', Math.abs(s.camY - 0.22) < 0.02 && Math.abs(s.camRoll + 1.15) < 0.02, `camera at ${f(s.camY)} m, roll ${f(s.camRoll)}`);
  check('keys do nothing for a dead man', await (async () => {
    await h.key('KeyW', true);
    await h.skip(10);
    await h.key('KeyW', false);
    const d = await state();
    return Math.abs(d.x - s.x) < 0.05;
  })());
  await h.eval(() => window.__G.game.retry());
  await h.skip(steps(1.5));
  await h.frames(2);
  await h.shot(`${OUT}12-retry.png`);
  s = await state();
  check('retry puts Rule back on his feet at the start', s.alive && s.health === 100 && Math.abs(s.x + 40) < 0.01 && Math.abs(s.camY - 1.68) < 0.01 && Math.abs(s.camRoll) < 1e-6 && s.post.lowHealth < 0.05,
    `${f(s.x)}, ${f(s.z)}, camera ${f(s.camY)} m`);

  const errors = await h.errors();
  check('nothing was logged as an error', errors.length === 0, errors.slice(0, 3).join(' | '));

  console.log(lines.join('\n'));
  if (failed) throw new Error(`${failed} of ${lines.length} checks failed (tools/scenarios/input-player-move.cjs)`);
};
