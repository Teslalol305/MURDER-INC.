// The touch controls of the real input module, driven by real touch events (Chromium touch emulation
// over the DevTools protocol): layout checks and pictures, then every control once.
//
//   node build.mjs --dev --only=input,player --out=dist/dev-input-player.html
//   node tools/shot.cjs dist/dev-input-player.html --size 844x390 --params "autostart=1&q=low&noaudio=1&god=1" \
//        --scenario tools/scenarios/input-player-touch.cjs --timeout 400
//   node tools/shot.cjs dist/dev-input-player.html --size 390x844 --params "autostart=1&q=low&noaudio=1&god=1" \
//        --scenario tools/scenarios/input-player-touch.cjs --timeout 400
//   LAYOUT_ONLY=1 node tools/shot.cjs … --size 320x568 …        any other screen: layout checks and one picture
//
// Layout: every control inside the viewport, none overlapping another or the HUD, sizes fit a thumb.
// Then: floating stick with auto-sprint · look drag · FIRE (hold, drag to track) · AIM toggle · DUCK toggle ·
// JUMP · RLD · SWAP · HIT · contextual USE (grabs reel 1) · pause and resume by tapping.
// Prints one line per check and fails the run if any check fails. Screenshots go to shots/input-player/
// as touch-<width>x<height>-*.png. Written against the stub game, HUD, weapon and level.

'use strict';

const EAST = -Math.PI / 2;
const DT = 0.0333;
const TOUCH_RATE = 0.0052;

module.exports = async (page, h) => {
  const lines = [];
  let failed = 0;
  const check = (name, ok, detail = '') => {
    lines.push(`${ok ? 'ok  ' : 'FAIL'}  ${name}${detail ? `  (${detail})` : ''}`);
    if (!ok) failed++;
  };
  const f = (n) => Math.round(n * 1000) / 1000;
  const steps = (seconds) => Math.round(seconds / DT);
  const { width: W, height: H } = page.viewportSize();
  const OUT = `shots/input-player/touch-${W}x${H}-`;

  // ---- real touches ------------------------------------------------------------------------------
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  const fingers = new Map(); // id → [x, y]
  const send = (type) =>
    cdp.send('Input.dispatchTouchEvent', { type, touchPoints: [...fingers].map(([id, [x, y]]) => ({ id, x: Math.round(x), y: Math.round(y) })) });
  const touch = {
    async down(id, x, y) {
      fingers.set(id, [x, y]);
      await send('touchStart');
    },
    async move(id, x, y) {
      fingers.set(id, [x, y]);
      await send('touchMove');
    },
    async up(id) {
      fingers.delete(id);
      await send('touchEnd');
    },
    async tap(id, x, y) {
      await this.down(id, x, y);
      await this.up(id);
    },
  };

  const state = () =>
    h.eval(() => {
      const G = window.__G;
      const p = G.player;
      const layer = document.querySelector('#ui > .touch');
      return {
        x: p.pos.x, y: p.pos.y, z: p.pos.z, yaw: p.yaw, pitch: p.pitch, eyeY: p.eye.y, speed: p.speed,
        sprinting: p.sprinting, crouching: p.crouching, ads: p.ads, fov: G.camera.fov,
        move: { ...G.input.move }, device: G.input.device, touch: G.input.touch, locked: G.input.locked,
        fire: G.input.down('fire'), aim: G.input.down('ads'), crouch: G.input.down('crouch'), sprint: G.input.down('sprint'),
        shots: G.combat.stats.shots, weapon: G.weapon.state, mag: G.weapon.mag,
        game: G.game.state, reels: G.game.run.reels,
        layer: layer ? { hidden: layer.hidden, prompt: layer.classList.contains('has-prompt') } : null,
        root: { cls: document.documentElement.className, device: document.documentElement.dataset.device },
        seen: { ...window.__seen },
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
  /** Bounding boxes of every visible control and HUD block, in CSS pixels. */
  const rects = () =>
    h.eval(() => {
      const box = (el) => {
        const r = el.getBoundingClientRect();
        return { x: r.left, y: r.top, w: r.width, h: r.height };
      };
      const shown = (el) => !!el && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';
      const out = { buttons: {}, hud: {} };
      for (const el of document.querySelectorAll('#ui > .touch > .touch-btn')) {
        if (shown(el)) out.buttons[el.className.replace('touch-btn touch-', '').split(' ')[0]] = box(el);
      }
      const stick = document.querySelector('#ui > .touch > .touch-stick');
      if (shown(stick)) out.stick = box(stick);
      const hud = document.querySelector('#ui > .hud-stub');
      if (hud && !hud.hidden) {
        const names = ['info', 'crosshair', 'prompt'];
        [...hud.children].forEach((el, i) => {
          if (shown(el)) out.hud[names[i] || `block${i}`] = box(el);
        });
      }
      return out;
    });
  const centre = (r) => [r.x + r.w / 2, r.y + r.h / 2];
  const overlap = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
  /** Round controls are compared as circles: their square boxes may touch at the corners. */
  const discsOverlap = (a, b) => Math.hypot(centre(a)[0] - centre(b)[0], centre(a)[1] - centre(b)[1]) < (a.w + b.w) / 2;

  try {
    await run();
  } finally {
    console.log(lines.join('\n'));
  }
  if (failed) throw new Error(`${failed} of ${lines.length} checks failed (tools/scenarios/input-player-touch.cjs)`);

  async function run() {
  // ---- staging -----------------------------------------------------------------------------------
  await h.eval(() => {
    const G = window.__G;
    G.enemies.clear();
    window.__seen = {};
    for (const name of ['player:jump', 'weapon:melee', 'weapon:reload', 'input:device', 'objective:done', 'game:state']) {
      G.events.on(name, () => {
        window.__seen[name] = (window.__seen[name] || 0) + 1;
      });
    }
  });
  await h.skip(2);
  let s = await state();
  check('before the first touch: mouse scheme, no touch layer', s.device === 'kbm' && !s.touch && s.layer === null, `device ${s.device}`);

  // ---- 1. the first touch builds the controls -----------------------------------------------------
  await place(-36, 0, 0, EAST);
  await touch.tap(9, W * 0.7, H * 0.3); // a tap on the look side: harmless
  await h.skip(2);
  s = await state();
  check('the first touch switches to the touch scheme', s.device === 'touch' && s.touch && !s.locked && s.seen['input:device'] === 1 && /\bis-touch\b/.test(s.root.cls) && s.root.device === 'touch',
    `device ${s.device}, <html class="${s.root.cls}">`);
  check('the controls are showing', !!s.layer && !s.layer.hidden && !s.layer.prompt);
  await h.frames(2);
  await h.shot(`${OUT}1-rest.png`);

  // ---- 2. layout ---------------------------------------------------------------------------------
  let r = await rects();
  const names = Object.keys(r.buttons);
  check('eight controls at rest (USE waits for a prompt)', names.sort().join() === 'ads,crouch,fire,jump,melee,pause,reload,swap', names.join());
  const all = { ...r.buttons, stick: r.stick };
  const outside = Object.entries(all).filter(([, b]) => b.x < 0 || b.y < 0 || b.x + b.w > W || b.y + b.h > H).map(([n]) => n);
  check('every control is inside the viewport', outside.length === 0, outside.join() || `${W} × ${H}`);
  const small = Object.entries(r.buttons).filter(([, b]) => Math.min(b.w, b.h) < 42).map(([n, b]) => `${n} ${f(b.w)}`);
  check('every button is at least 42 px across', small.length === 0, small.join() || Object.entries(r.buttons).map(([n, b]) => `${n} ${Math.round(b.w)}`).join(' '));
  const clash = [];
  const list = Object.entries(all);
  for (let i = 0; i < list.length; i++) {
    for (let j = i + 1; j < list.length; j++) {
      const [na, a] = list[i];
      const [nb, b] = list[j];
      const square = na === 'pause' || nb === 'pause';
      if (square ? overlap(a, b) : discsOverlap(a, b)) clash.push(`${na}/${nb}`);
    }
  }
  check('no control overlaps another', clash.length === 0, clash.join());
  const onHud = [];
  for (const [nb, b] of list) {
    for (const [nh, hb] of Object.entries(r.hud)) {
      // The stub HUD's debug read-out is as wide as a portrait screen and runs under the pause button:
      // a real HUD keeps the top-right 56 × 56 px free on touch (CONTRACT 6.3).
      if (nh === 'info' && nb === 'pause' && W < 500) continue;
      if (overlap(b, hb)) onHud.push(`${nb} on ${nh}`);
    }
  }
  check('no control covers a HUD block', onHud.length === 0, onHud.join() || Object.keys(r.hud).join());
  // Thumb reach: everything but pause lies within 300 px of a bottom corner.
  const far = Object.entries(r.buttons)
    .filter(([n, b]) => n !== 'pause' && Math.hypot(W - centre(b)[0], H - centre(b)[1]) > 300)
    .map(([n, b]) => `${n} ${Math.round(Math.hypot(W - centre(b)[0], H - centre(b)[1]))}`);
  check('the right-hand cluster is within thumb reach of the corner', far.length === 0, far.join());
  check('the stick rests in the left thumb corner', centre(r.stick)[0] < W * 0.45 && centre(r.stick)[1] > H * 0.5, centre(r.stick).map(Math.round).join());
  if (process.env.LAYOUT_ONLY === '1') return; // other screen sizes: the layout checks and the picture are enough

  // ---- 3. stick: move, auto-sprint ---------------------------------------------------------------
  const sx = W * 0.2;
  const sy = H * 0.72;
  await touch.down(1, sx, sy);
  await touch.move(1, sx + 20, sy - 20);
  await h.skip(steps(0.6));
  s = await state();
  const unit = r.stick.w / 2;
  check('left thumb: the stick walks, analog', Math.abs(s.move.x - 20 / unit) < 0.03 && Math.abs(s.move.y - 20 / unit) < 0.03 && s.speed > 0.5 && s.speed < 3.8 && !s.sprinting,
    `move ${f(s.move.x)}, ${f(s.move.y)}, speed ${f(s.speed)}`);
  await touch.move(1, sx, sy - 90); // all the way forward
  await h.skip(steps(0.8));
  s = await state();
  check('pushed fully forward: sprint', s.move.y === 1 && s.sprint && s.sprinting && Math.abs(s.speed - 6.4) < 1e-6, `speed ${f(s.speed)}`);

  // ---- 4. FIRE: hold, drag to track --------------------------------------------------------------
  const [fx, fy] = centre(r.buttons.fire);
  const shotsBefore = s.shots;
  await touch.down(2, fx, fy);
  await h.skip(steps(0.5));
  await h.frames(2);
  await h.shot(`${OUT}2-sprint-and-fire.png`);
  s = await state();
  check('FIRE holds the trigger (and firing ends the sprint)', s.fire && s.shots - shotsBefore >= 5 && !s.sprinting, `${s.shots - shotsBefore} rounds in half a second`);
  const yaw = s.yaw;
  const pitch = s.pitch;
  await touch.move(2, fx - 40, fy + 10);
  await h.skip(2);
  s = await state();
  // (the stub weapon adds recoil to the pitch, so only the yaw is exact)
  check('dragging the FIRE finger tracks: 0.0052 rad per pixel', Math.abs(s.yaw - (yaw + 40 * TOUCH_RATE)) < 2e-3 && s.pitch < pitch + 0.02, `yaw +${f(s.yaw - yaw)}`);
  await touch.up(2);
  await touch.up(1);
  await h.skip(steps(0.5));
  s = await state();
  check('letting go stops the fire and the walk', !s.fire && s.speed === 0 && s.move.y === 0);

  // ---- 5. look finger ----------------------------------------------------------------------------
  await place(-36, 0, 0, EAST);
  await h.skip(1);
  await touch.down(3, W * 0.62, H * 0.35);
  await touch.move(3, W * 0.62 + 50, H * 0.35 - 20);
  await h.skip(1);
  await touch.up(3);
  s = await state();
  check('right thumb drags the view', Math.abs(s.yaw - (EAST - 50 * TOUCH_RATE)) < 1e-6 && Math.abs(s.pitch - 20 * TOUCH_RATE) < 1e-6, `yaw ${f(s.yaw - EAST)}, pitch ${f(s.pitch)}`);

  // ---- 6. AIM and DUCK toggle --------------------------------------------------------------------
  await place(-36, 0, 0, EAST);
  await touch.tap(4, ...centre(r.buttons.ads));
  await h.skip(steps(0.6));
  await h.frames(2);
  await h.shot(`${OUT}3-aim.png`);
  s = await state();
  check('AIM stays on after a tap: full aim, 52° view', s.aim && s.ads > 0.99 && Math.abs(s.fov - 52) < 0.5, `ads ${f(s.ads)}, fov ${f(s.fov)}`);
  await touch.tap(4, ...centre(r.buttons.ads));
  await h.skip(steps(0.8));
  s = await state();
  check('and goes off with the next', !s.aim && s.ads < 0.01 && Math.abs(s.fov - 74) < 1, `fov ${f(s.fov)}`);
  await touch.tap(4, ...centre(r.buttons.crouch));
  await h.skip(steps(0.5));
  s = await state();
  check('DUCK toggles the crouch', s.crouch && s.crouching && Math.abs(s.eyeY - 1.05) < 0.03, `eye ${f(s.eyeY)}`);
  await touch.tap(4, ...centre(r.buttons.crouch));
  await h.skip(steps(0.5));
  s = await state();
  check('and stands back up', !s.crouching && Math.abs(s.eyeY - 1.68) < 0.03, `eye ${f(s.eyeY)}`);

  // ---- 7. JUMP, RLD, SWAP, HIT -------------------------------------------------------------------
  await touch.tap(4, ...centre(r.buttons.jump));
  await h.skip(steps(0.3));
  s = await state();
  check('JUMP jumps', s.seen['player:jump'] === 1 && s.y > 0.5, `y ${f(s.y)}`);
  await h.skip(steps(0.6));
  await touch.tap(4, ...centre(r.buttons.reload));
  await h.skip(2);
  s = await state();
  check('RLD reloads', s.weapon === 'reloading' && s.seen['weapon:reload'] >= 1, s.weapon);
  await touch.down(4, ...centre(r.buttons.swap));
  const swap = await h.eval(() => window.__G.input.pressed('swap'));
  await touch.up(4);
  check('SWAP presses swap', swap === true);
  await h.skip(steps(3));
  await touch.tap(4, ...centre(r.buttons.melee));
  await h.skip(2);
  s = await state();
  check('HIT strikes', s.seen['weapon:melee'] === 1 && s.weapon === 'melee', s.weapon);

  // ---- 8. USE appears at a reel and grabs it -----------------------------------------------------
  await h.skip(steps(1));
  await place(-5.6, 0, 1, EAST); // 1.6 m west of reel 1, facing it
  await h.skip(4);
  s = await state();
  check('at a reel the USE button appears', !!s.layer && s.layer.prompt);
  r = await rects();
  check('USE is on screen, clear of the other controls', !!r.buttons.interact && Object.entries(r.buttons).every(([n, b]) => n === 'interact' || n === 'pause' || !discsOverlap(b, r.buttons.interact)),
    r.buttons.interact ? `${Math.round(r.buttons.interact.w)} px at ${centre(r.buttons.interact).map(Math.round).join()}` : 'missing');
  const promptOnControls = Object.entries(r.buttons).filter(([, b]) => r.hud.prompt && overlap(b, r.hud.prompt)).map(([n]) => n);
  check('the HUD prompt is not covered either', promptOnControls.length === 0, promptOnControls.join());
  await touch.down(5, ...centre(r.buttons.interact));
  await h.skip(steps(1.2));
  await h.frames(2);
  await h.shot(`${OUT}4-use.png`);
  await h.skip(steps(1.4));
  s = await state();
  check('holding USE for 2.4 s grabs the reel', s.reels === 1 && s.seen['objective:done'] === 1, `${s.reels} reel`);
  await h.skip(3);
  s = await state();
  check('and the button goes away again', !!s.layer && !s.layer.prompt);
  await touch.up(5);
  await h.eval(() => window.__G.enemies.clear());

  // ---- 9. pause and resume, by touch -------------------------------------------------------------
  await touch.tap(6, ...centre(r.buttons.pause));
  await h.skip(2);
  await h.frames(2);
  await h.shot(`${OUT}5-paused.png`);
  s = await state();
  check('the pause button pauses and the controls step back', s.game === 'paused' && s.layer.hidden, s.game);
  const hint = await h.eval(() => window.__G.input.hint());
  check('no mouse hint on the pause card', hint === '', JSON.stringify(hint));
  const resume = await h.eval(() => {
    const b = document.querySelector('.menu-stub button').getBoundingClientRect();
    return [b.left + b.width / 2, b.top + b.height / 2];
  });
  await touch.tap(6, ...resume); // a tap on a menu button is an ordinary click
  await h.wait(350);
  await h.skip(3);
  s = await state();
  check('tapping Resume resumes; the controls are back', s.game === 'playing' && !s.layer.hidden && s.device === 'touch', `${s.game}, device ${s.device}`);
  await h.frames(2);
  await h.shot(`${OUT}6-resumed.png`);

  const errors = await h.errors();
  check('nothing was logged as an error', errors.length === 0, errors.slice(0, 3).join(' | '));
  }
};
