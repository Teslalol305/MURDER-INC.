// A gamepad on the real input module, in the browser: the scenario plugs a standard-mapping pad into
// navigator.getGamepads() and moves its sticks and buttons.
//
//   node build.mjs --dev --only=input,player --out=dist/dev-input-player.html
//   node tools/shot.cjs dist/dev-input-player.html --params "autostart=1&q=low&noaudio=1&god=1" \
//        --scenario tools/scenarios/input-player-pad.cjs --timeout 300
//
// Left stick walks · L3 latches sprint · right stick turns (curve, boost) · LT aims · RT fires with rumble ·
// A jumps · B crouches · X reloads, and grabs a reel when the prompt shows · Y swaps · RB strikes ·
// aim slow-down on a Vulture · a hit rumbles · Start pauses · the menu signals · Start resumes.
// Prints one line per check and fails the run if any check fails. Written against the stub game, weapon,
// enemies and HUD.

'use strict';

const OUT = 'shots/input-player/pad-';
const EAST = -Math.PI / 2;
const DT = 0.0333;
const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));

module.exports = async (page, h) => {
  const lines = [];
  let failed = 0;
  const check = (name, ok, detail = '') => {
    lines.push(`${ok ? 'ok  ' : 'FAIL'}  ${name}${detail ? `  (${detail})` : ''}`);
    if (!ok) failed++;
  };
  const f = (n) => Math.round(n * 1000) / 1000;
  const steps = (seconds) => Math.round(seconds / DT);

  const pad = {
    axes: (values) => h.eval((v) => v.forEach((x, i) => (window.__pad.axes[i] = x)), values),
    press: (index, value = 1) => h.eval(([i, v]) => (window.__pad.buttons[i] = { pressed: v > 0.5, value: v }), [index, value]),
    let: (index) => h.eval((i) => (window.__pad.buttons[i] = { pressed: false, value: 0 }), index),
    async tap(index) {
      await this.press(index);
      await h.skip(2);
      await this.let(index);
      await h.skip(1);
    },
  };
  const state = () =>
    h.eval(() => {
      const G = window.__G;
      const p = G.player;
      const hud = document.querySelector('.hud-stub');
      return {
        x: p.pos.x, y: p.pos.y, yaw: p.yaw, pitch: p.pitch, speed: p.speed, sprinting: p.sprinting, crouching: p.crouching,
        ads: p.ads, fov: G.camera.fov, health: p.health,
        device: G.input.device, root: document.documentElement.dataset.device, aimSlow: G.input.aimSlow, hint: G.input.hint(),
        glyphs: ['fire', 'ads', 'jump', 'reload', 'interact', 'swap', 'melee', 'pause'].map((a) => G.input.glyph(a)).join(' '),
        shots: G.combat.stats.shots, weapon: G.weapon.state, game: G.game.state, reels: G.game.run.reels,
        prompt: hud && !hud.children[2].hidden ? hud.children[2].firstChild.textContent : null,
        rumbles: window.__rumbles.slice(), seen: { ...window.__seen },
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

  try {
    await run();
  } finally {
    console.log(lines.join('\n'));
  }
  if (failed) throw new Error(`${failed} of ${lines.length} checks failed (tools/scenarios/input-player-pad.cjs)`);

  async function run() {
    await h.eval(() => {
      const G = window.__G;
      G.enemies.clear();
      window.__seen = {};
      window.__rumbles = [];
      for (const name of ['player:jump', 'weapon:melee', 'weapon:reload', 'input:device', 'objective:done']) {
        G.events.on(name, () => {
          window.__seen[name] = (window.__seen[name] || 0) + 1;
        });
      }
      window.__pad = {
        index: 0,
        id: 'Scenario pad (STANDARD GAMEPAD)',
        connected: true,
        mapping: 'standard',
        axes: [0, 0, 0, 0],
        buttons: Array.from({ length: 17 }, () => ({ pressed: false, value: 0 })),
        vibrationActuator: {
          playEffect(type, effect) {
            window.__rumbles.push([type, effect.strongMagnitude, effect.weakMagnitude, effect.duration]);
            return Promise.resolve('complete');
          },
        },
      };
      navigator.getGamepads = () => [window.__pad];
      window.dispatchEvent(new Event('gamepadconnected'));
    });
    await page.mouse.move(480, 270);
    await h.skip(3);
    let s = await state();
    check('an idle pad does not take the device', s.device === 'kbm', s.device);

    // ---- move, sprint ----------------------------------------------------------------------------
    await place(-39, 0, 0, EAST);
    await pad.axes([0, -0.57, 0, 0]);
    await h.skip(steps(0.5));
    s = await state();
    check('left stick half-way: half the walk speed; the pad is now the device', Math.abs(s.speed - 1.9) < 0.02 && s.device === 'pad' && s.root === 'pad' && s.seen['input:device'] === 1,
      `speed ${f(s.speed)}, device ${s.device}`);
    check('glyphs follow the device', s.glyphs === 'RT LT A X X Y RB START', s.glyphs);
    check('no mouse hint on a controller', s.hint === '');
    await pad.axes([0, -1, 0, 0]);
    await pad.tap(10); // click the left stick
    await h.skip(steps(0.6));
    s = await state();
    check('L3 latches the sprint', s.sprinting && Math.abs(s.speed - 6.4) < 1e-6, `speed ${f(s.speed)}`);
    await pad.axes([0, -0.5, 0, 0]);
    await h.skip(steps(0.5));
    s = await state();
    check('easing off the stick lets go of it', !s.sprinting && s.speed < 2, `speed ${f(s.speed)}`);
    await pad.axes([0, 0, 0, 0]);
    await h.skip(steps(0.4));

    // ---- look: curve and boost -------------------------------------------------------------------
    await place(-36, 0, 0, EAST);
    await h.skip(1);
    await pad.axes([0, 0, 0.57, 0]); // half deflection
    await h.skip(steps(1));
    s = await state();
    let turned = wrap(EAST - s.yaw);
    check('right stick half-way turns gently (21.9 % of 2.9 rad/s)', Math.abs(turned - 0.21875 * 2.9 * steps(1) * DT) < 0.02, `${f(turned)} rad in a second`);
    await place(-36, 0, 0, EAST);
    await pad.axes([0, 0, 0, 0]);
    await h.skip(steps(0.5));
    await pad.axes([0, 0, 1, 0.5]);
    await h.skip(steps(1));
    s = await state();
    turned = (wrap(EAST - s.yaw) + 2 * Math.PI) % (2 * Math.PI); // more than half a turn
    // Full deflection: 2.9 rad/s, boosted to × 1.75 over the first 0.45 s. The stick is at (1, 0.5), which
    // is (1, 0.419) past the dead zone: 92 % of the rate goes to the yaw, 39 % of it × 0.62 to the pitch.
    const share = 1 / Math.hypot(1, 0.36 / 0.86);
    const boosted = 0.45 * (1 + 1.75) / 2 + (steps(1) * DT - 0.45) * 1.75;
    const expected = share * 2.9 * boosted;
    check('at the rim the turn boost kicks in', Math.abs(turned - expected) < 0.2 && turned > 3.5, `${f(turned)} rad in a second, expected about ${f(expected)}`);
    const down = (0.36 / 0.86) * share * 2.9 * 0.62 * boosted;
    check('pitch is the slower axis', Math.abs(-s.pitch - down) < 0.1, `pitch ${f(s.pitch)}, expected about ${f(-down)}`);
    await pad.axes([0, 0, 0, 0]);
    await h.skip(steps(0.3));

    // ---- triggers --------------------------------------------------------------------------------
    await place(-36, 0, 0, EAST);
    await pad.press(6, 0.8); // LT
    await h.skip(steps(0.6));
    s = await state();
    check('LT aims', s.ads > 0.99 && Math.abs(s.fov - 52) < 0.5, `ads ${f(s.ads)}, fov ${f(s.fov)}`);
    await pad.press(7, 0.3); // RT, not far enough
    await h.skip(4);
    s = await state();
    const before = s.shots;
    await pad.press(7, 0.9);
    await h.skip(steps(0.5));
    await h.frames(2);
    await h.shot(`${OUT}1-aim-and-fire.png`);
    await pad.let(7);
    await pad.let(6);
    await h.skip(steps(0.5));
    s = await state();
    check('RT fires past 35 % of its travel', before === 0 && s.shots >= 5, `${s.shots} rounds`);
    // The real weapon module plays a rumble per round through input.rumble (the stub weapon does not).
    await h.eval(() => window.__G.input.rumble(0.18, 0.5, 55));
    s = await state();
    const fire = s.rumbles.filter((r) => r[3] === 55);
    check('input.rumble reaches the pad motors', fire.length === 1 && fire[0][0] === 'dual-rumble' && fire[0][1] === 0.18 && fire[0][2] === 0.5, JSON.stringify(fire[0]));

    // ---- face buttons ----------------------------------------------------------------------------
    await pad.tap(0);
    await h.skip(steps(0.25));
    s = await state();
    check('A jumps', s.seen['player:jump'] === 1 && s.y > 0.5, `y ${f(s.y)}`);
    await h.skip(steps(0.6));
    await pad.press(1);
    await h.skip(steps(0.4));
    s = await state();
    const crouched = s.crouching;
    await pad.let(1);
    await h.skip(steps(0.4));
    s = await state();
    check('B crouches while held', crouched && !s.crouching);
    await pad.tap(2);
    s = await state();
    check('X reloads when there is nothing to grab', s.weapon === 'reloading' && s.seen['weapon:reload'] >= 1, s.weapon);
    await pad.press(3);
    await h.skip(1);
    const swap = await h.eval(() => window.__G.input.down('swap'));
    await pad.let(3);
    check('Y swaps', swap === true);
    await h.skip(steps(3));
    await pad.tap(5);
    s = await state();
    check('RB strikes', s.seen['weapon:melee'] === 1, s.weapon);

    // ---- X at a reel -----------------------------------------------------------------------------
    await h.skip(steps(1));
    await place(-5.6, 0, 1, EAST);
    await h.skip(4);
    s = await state();
    check('the prompt names the pad button', s.prompt === 'Hold X — Grab reel 1', s.prompt);
    const reloads = s.seen['weapon:reload'];
    await pad.press(2);
    await h.skip(steps(1.2));
    await h.frames(2);
    await h.shot(`${OUT}2-hold-x.png`);
    await h.skip(steps(1.4));
    await pad.let(2);
    await h.skip(2);
    s = await state();
    check('holding X grabs the reel instead of reloading', s.reels === 1 && s.seen['weapon:reload'] === reloads, `${s.reels} reel`);
    await h.eval(() => window.__G.enemies.clear());

    // ---- aim slow-down, hit rumble ---------------------------------------------------------------
    await place(-36, 0, 0, EAST);
    await h.eval(() => window.__G.enemies.spawn('goon', new window.__G.THREE.Vector3(-26, 0, 0), { alerted: false }));
    await h.skip(steps(0.6));
    s = await state();
    check('a Vulture under the crosshair slows the stick to 55 %', Math.abs(s.aimSlow - 0.55) < 0.01, `aimSlow ${f(s.aimSlow)}`);
    await place(-36, 0, 0, EAST, 0.6); // look over his head
    await h.skip(steps(0.6));
    s = await state();
    check('and off him it is back to full', Math.abs(s.aimSlow - 1) < 0.01, `aimSlow ${f(s.aimSlow)}`);
    await h.eval(() => {
      window.__G.enemies.clear();
      window.__rumbles.length = 0;
      window.__G.player.invulnerable = false;
      // (?god=1 keeps the player alive in this scenario: play the hit's event by hand)
      window.__G.events.emit('player:hit', { amount: 12, from: null, health: 88, kind: 'bullet' });
    });
    s = await state();
    check('a hit rumbles harder with the damage', s.rumbles.length === 1 && Math.abs(s.rumbles[0][1] - (0.45 + 12 / 30)) < 1e-9 && s.rumbles[0][2] === 0.3 && s.rumbles[0][3] === 160, JSON.stringify(s.rumbles[0]));

    // ---- Start, the menu signals -----------------------------------------------------------------
    await pad.press(9);
    await h.skip(1);
    await pad.let(9);
    await h.skip(1);
    s = await state();
    check('Start pauses', s.game === 'paused', s.game);
    const nav = async () => h.eval(() => ({ ...window.__G.input.menuNav() }));
    await pad.press(13); // D-pad down
    await h.eval(() => window.__G.input.update(0.0333));
    let n = await nav();
    await h.eval(() => window.__G.input.endFrame());
    await pad.let(13);
    check('in the menu the D-pad moves the selection', n.y === 1 && !n.accept, JSON.stringify(n));
    await pad.press(0);
    await h.eval(() => window.__G.input.update(0.0333));
    n = await nav();
    const jumps = await h.eval(() => window.__G.input.pressed('jump'));
    await h.eval(() => window.__G.input.endFrame());
    await pad.let(0);
    check('A accepts (and does not jump)', n.accept === true && jumps === false, JSON.stringify(n));
    await h.skip(steps(0.5));
    await pad.press(9);
    await h.skip(2);
    await pad.let(9);
    await h.skip(2);
    s = await state();
    check('Start resumes', s.game === 'playing', s.game);

    // ---- unplugged -------------------------------------------------------------------------------
    await pad.axes([0, -1, 0, 0]);
    await h.skip(steps(0.3));
    await h.eval(() => {
      navigator.getGamepads = () => [null];
    });
    await h.skip(steps(0.5));
    s = await state();
    check('unplugging the pad stops the walk and hands the device back', s.speed === 0 && s.device === 'kbm', `speed ${f(s.speed)}, device ${s.device}`);

    const errors = await h.errors();
    check('nothing was logged as an error', errors.length === 0, errors.slice(0, 3).join(' | '));
  }
};
