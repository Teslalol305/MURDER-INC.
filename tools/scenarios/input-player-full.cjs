// Input and player next to whatever real modules exist (level, weapon, enemies, HUD …): no layout is
// assumed, only that Rule moves, looks, aims, takes a hit and dies the way he should, and that nothing
// logs an error.
//
//   node build.mjs --dev --out=dist/dev-input-player-full.html
//   node tools/shot.cjs dist/dev-input-player-full.html --params "autostart=1&q=low&noaudio=1" \
//        --scenario tools/scenarios/input-player-full.cjs --timeout 600
//
// Screenshots go to shots/input-player/full-*.png.

'use strict';

const OUT = 'shots/input-player/full-';
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
  const state = () =>
    h.eval(() => {
      const G = window.__G;
      const p = G.player;
      return {
        x: p.pos.x, y: p.pos.y, z: p.pos.z, yaw: p.yaw, pitch: p.pitch, eyeY: p.eye.y, speed: p.speed, onGround: p.onGround,
        sprinting: p.sprinting, crouching: p.crouching, ads: p.ads, health: p.health, alive: p.alive, surface: p.surface,
        fov: G.camera.fov, camY: G.camera.position.y, camRoll: G.camera.rotation.z, post: { ...G.render.post },
        game: G.game.state, weapon: G.weapon.state, shots: G.combat.stats.shots, stubbed: window.__stats().stubbed.join(' '),
        mode: G.input.mode, locked: G.input.locked,
      };
    });

  try {
    await run();
  } finally {
    console.log(lines.join('\n'));
  }
  if (failed) throw new Error(`${failed} of ${lines.length} checks failed (tools/scenarios/input-player-full.cjs)`);

  async function run() {
    const { width: W, height: H } = page.viewportSize();
    await page.mouse.move(W / 2, H / 2);
    await h.eval(() => {
      window.__G.enemies.clear(); // nobody shoots while the moves are checked
      window.__seen = {};
      for (const name of ['player:step', 'player:jump', 'player:land', 'player:hit', 'player:dead']) {
        window.__G.events.on(name, (e) => {
          window.__seen[name] = (window.__seen[name] || 0) + 1;
          if (name === 'player:step') window.__surface = e.surface;
        });
      }
    });
    await h.skip(3);
    await h.frames(2);
    await h.shot(`${OUT}1-start.png`);
    let s = await state();
    const start = s;
    check('boots into a run with input and player real', s.game === 'playing' && !/\b(input|player)\b/.test(s.stubbed), `stubbed: ${s.stubbed || 'nothing'}`);
    check('Rule stands at the level start, alive, eye at 1.68 m', s.alive && s.health === 100 && Math.abs(s.eyeY - s.y - 1.68) < 0.05, `${f(s.x)}, ${f(s.y)}, ${f(s.z)}`);

    // Walk, then sprint, along the facing direction.
    await h.key('KeyW', true);
    await h.skip(steps(1.5));
    s = await state();
    const walked = Math.hypot(s.x - start.x, s.z - start.z);
    check('W walks', walked > 2 && walked < 6.5, `${f(walked)} m in 1.5 s, speed ${f(s.speed)}`);
    await h.key('ShiftLeft', true);
    await h.skip(steps(1));
    await h.frames(2);
    await h.shot(`${OUT}2-sprint.png`);
    s = await state();
    const seen = await h.eval(() => ({ ...window.__seen, surface: window.__surface }));
    check('Shift sprints (unless something is in the way)', s.sprinting ? s.fov > 78 : s.speed < 3.9, `speed ${f(s.speed)}, fov ${f(s.fov)}`);
    check('footsteps carry a surface name', seen['player:step'] >= 2 && typeof seen.surface === 'string' && seen.surface.length > 0, `${seen['player:step']} steps on ${seen.surface}`);
    await h.key('ShiftLeft', false);
    await h.key('KeyW', false);
    await h.skip(steps(0.5));

    // Look, jump, crouch.
    const before = await state();
    await h.mouse(-150, 0);
    await h.skip(1);
    s = await state();
    check('the mouse turns the view', Math.abs(wrap(s.yaw - before.yaw) - 150 * 0.0021) < 1e-6, `yaw +${f(wrap(s.yaw - before.yaw))}`);
    await h.key('Space', true);
    await h.skip(2);
    await h.key('Space', false);
    let apex = 0;
    for (let i = 0; i < 12; i++) {
      await h.skip(2);
      apex = Math.max(apex, (await state()).y - before.y);
    }
    await h.skip(steps(0.5));
    check('Space jumps a metre', apex > 0.85 && apex < 1.06, `apex ${f(apex)} m`);
    await h.key('KeyC', true);
    await h.skip(steps(0.5));
    await h.frames(2);
    await h.shot(`${OUT}3-crouch.png`);
    s = await state();
    check('C crouches', s.crouching && Math.abs(s.eyeY - s.y - 1.05) < 0.04, `eye ${f(s.eyeY - s.y)} m`);
    await h.key('KeyC', false);
    await h.skip(steps(0.6));

    // Aim and fire: the weapon writes player.ads, the player zooms and takes the kick.
    await h.key('Mouse2', true);
    await h.skip(steps(0.6));
    await h.frames(2);
    await h.shot(`${OUT}4-aim.png`);
    s = await state();
    check('right mouse aims: the view narrows to 52°', s.ads > 0.95 && Math.abs(s.fov - 52) < 1, `ads ${f(s.ads)}, fov ${f(s.fov)}`);
    await h.key('Mouse2', false);
    await h.skip(steps(0.6));
    const calm = await state();
    await h.key('Mouse0', true);
    await h.skip(steps(0.6));
    await h.frames(1);
    await h.shot(`${OUT}5-fire.png`);
    await h.key('Mouse0', false);
    s = await state();
    check('left mouse fires and the muzzle climbs', s.shots >= 5 && s.pitch > calm.pitch, `${s.shots} rounds, pitch +${f(s.pitch - calm.pitch)}`);
    await h.skip(steps(1));

    // A hit, then the end.
    await h.eval(() => {
      const G = window.__G;
      G.player.invulnerable = false;
      G.player.damage(30, G.player.pos.clone().add(new G.THREE.Vector3(6, 1.2, 3)), 'bullet');
    });
    await h.frames(1);
    await h.shot(`${OUT}6-hit.png`);
    s = await state();
    check('a hit: health down, red pulse', s.health === 70 && s.post.damage > 0.8, `health ${s.health}, post.damage ${f(s.post.damage)}`);
    await h.eval(() => {
      const G = window.__G;
      G.player.damage(500, G.player.pos.clone().add(new G.THREE.Vector3(6, 1.2, 3)), 'bullet');
    });
    await h.skip(steps(0.5));
    await h.frames(1);
    await h.shot(`${OUT}7-dying.png`);
    await h.skip(steps(1.2));
    await h.frames(2);
    await h.shot(`${OUT}8-dead.png`);
    s = await state();
    check('death: the game knows, the camera lies on the floor', !s.alive && s.game === 'dead' && Math.abs(s.camY - s.y - 0.22) < 0.03 && Math.abs(Math.abs(s.camRoll) - 1.15) < 0.03,
      `${s.game}, camera ${f(s.camY - s.y)} m up, roll ${f(s.camRoll)}`);

    const errors = await h.errors();
    check('nothing was logged as an error', errors.length === 0, errors.slice(0, 3).join(' | '));
  }
};
