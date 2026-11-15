// Pointer lock and its fallback, from the title screen, with a real click and a real cursor.
//
//   node build.mjs --dev --only=input,player --out=dist/dev-input-player.html
//   node tools/shot.cjs dist/dev-input-player.html --params "q=low&noaudio=1&god=1" \
//        --scenario tools/scenarios/input-player-lock.cjs --timeout 300              # the browser grants the lock
//   node tools/shot.cjs dist/dev-input-player.html --params "q=low&noaudio=1&god=1&deny=1" \
//        --scenario tools/scenarios/input-player-lock.cjs --timeout 300              # the browser refuses it
//
// Granted: click Start → locked → mouse look and fire → the lock is taken away (what Esc or alt-tab do) →
// the game pauses → Resume takes it back.
// Refused (`deny=1`: the scenario makes requestPointerLock reject, as a sandboxed frame does): drag mode →
// the free cursor turns the view → resting it at a screen edge keeps turning, with the yellow cue →
// arrows turn, Enter fires, a click fires → Esc pauses.
// Prints one line per check and fails the run if any check fails. Written against the stub menus and game.

'use strict';

const OUT = 'shots/input-player/lock-';
const DT = 0.0333;
const MOUSE_RATE = 0.0021;
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
  const deny = new URL(page.url()).searchParams.get('deny') === '1';
  const { width: W, height: H } = page.viewportSize();

  const state = () =>
    h.eval(() => {
      const G = window.__G;
      return {
        game: G.game.state, locked: G.input.locked, mode: G.input.mode, device: G.input.device, hint: G.input.hint(),
        yaw: G.player.yaw, pitch: G.player.pitch, shots: G.combat.stats.shots,
        look: document.documentElement.dataset.look, play: document.documentElement.classList.contains('in-play'),
        events: window.__lock.slice(), requests: window.__requests,
        cue: [...document.querySelectorAll('#ui .look-edge')].map((el) => Number(el.style.opacity || 0)),
      };
    });

  try {
    await run();
  } finally {
    console.log(lines.join('\n'));
  }
  if (failed) throw new Error(`${failed} of ${lines.length} checks failed (tools/scenarios/input-player-lock.cjs)`);

  async function run() {
    await h.eval((refuse) => {
      const G = window.__G;
      window.__lock = [];
      window.__requests = 0;
      G.events.on('input:lock', (e) => window.__lock.push(`${e.locked ? 'locked' : 'free'}/${e.mode}`));
      const canvas = document.getElementById('view');
      const ask = canvas.requestPointerLock.bind(canvas);
      canvas.requestPointerLock = (...args) => {
        window.__requests++;
        return refuse ? Promise.reject(new DOMException('pointer lock is not allowed here', 'NotAllowedError')) : ask(...args);
      };
    }, deny);
    let s = await state();
    check('on the title screen: nothing asked for, lock mode assumed, controls idle', s.game === 'title' && !s.locked && s.mode === 'lock' && !s.play && s.requests === 0, `${s.game}, ${s.mode}`);

    // The player clicks Start (a real click: the user gesture pointer lock wants).
    await h.click('.menu-stub button');
    await page.waitForFunction((refuse) => (refuse ? window.__G.input.mode === 'drag' : window.__G.input.locked), deny, { timeout: 5000 }).catch(() => {});
    await h.skip(steps(3)); // through the intro
    await h.eval(() => window.__G.enemies.clear());
    s = await state();

    if (!deny) {
      check('Start captures the mouse', s.locked && s.mode === 'lock' && s.look === 'lock' && s.play && s.events.join() === 'locked/lock', `${s.events.join()} after ${s.requests} request`);
      check('the game runs', s.game === 'playing', s.game);
      check('hint: how to let go', /Esc/.test(s.hint), s.hint);
      const yaw = s.yaw;
      await h.mouse(100, -20);
      await h.skip(1);
      s = await state();
      check('mouse look while locked', Math.abs(s.yaw - (yaw - 100 * MOUSE_RATE)) < 1e-6 && Math.abs(s.pitch - 20 * MOUSE_RATE) < 1e-6, `yaw ${f(s.yaw - yaw)}`);
      await h.key('Mouse0', true);
      await h.skip(steps(0.5));
      await h.key('Mouse0', false);
      s = await state();
      check('left button fires', s.shots >= 5, `${s.shots} rounds`);

      // Esc, alt-tab: the browser takes the lock away.
      await h.eval(() => document.exitPointerLock());
      await page.waitForFunction(() => !window.__G.input.locked, null, { timeout: 5000 }).catch(() => {});
      await h.skip(3);
      await h.frames(2);
      await h.shot(`${OUT}1-lost-paused.png`);
      s = await state();
      check('losing the lock is announced and pauses the game', !s.locked && s.mode === 'lock' && s.game === 'paused' && s.events.join() === 'locked/lock,free/lock' && !s.play, `${s.game}, ${s.events.join()}`);
      check('the pause card hint: Resume takes the mouse back', /Resume/.test(s.hint), s.hint);
      await h.wait(1300); // a browser will not re-lock for about a second after an exit
      await h.click('.menu-stub button');
      await page.waitForFunction(() => window.__G.input.locked, null, { timeout: 5000 }).catch(() => {});
      await h.skip(3);
      s = await state();
      check('Resume recaptures the mouse', s.locked && s.game === 'playing' && s.mode === 'lock', `${s.game}, ${s.events.join()}`);
    } else {
      check('a refused lock falls back to drag mode, and says so', !s.locked && s.mode === 'drag' && s.look === 'drag' && s.events.join() === 'free/drag', `${s.events.join()} after ${s.requests} request`);
      check('the game runs anyway (no pause)', s.game === 'playing' && s.play, s.game);
      check('hint: how to look without the lock', /edge/.test(s.hint) && /I J K L/.test(s.hint), s.hint);

      // The free cursor turns the view at the normal mouse rate.
      await page.mouse.move(W / 2, H / 2);
      await h.skip(2);
      let { yaw, pitch } = await state();
      await page.mouse.move(W / 2 + 100, H / 2 + 20);
      await h.skip(1);
      s = await state();
      check('moving the free cursor looks around', Math.abs(s.yaw - (yaw - 100 * MOUSE_RATE)) < 1e-6 && Math.abs(s.pitch - (pitch - 20 * MOUSE_RATE)) < 1e-6,
        `yaw ${f(s.yaw - yaw)}, pitch ${f(s.pitch - pitch)}`);
      await h.skip(steps(0.5));
      let t = await state();
      check('mid-screen, a resting cursor does not turn', Math.abs(t.yaw - s.yaw) < 1e-9 && t.cue.every((o) => o === 0));

      // Resting at the right edge keeps turning: 2.4 rad/s at the very edge.
      await page.mouse.move(W - 1, H / 2);
      await h.skip(2);
      yaw = (await state()).yaw;
      await h.skip(steps(1));
      await h.frames(2);
      await h.shot(`${OUT}2-drag-edge-turn.png`);
      s = await state();
      const turned = wrap(yaw - s.yaw);
      check('resting the cursor at the right edge keeps turning right', turned > 2.2 && turned < 2.75, `${f(turned)} rad in ${f((steps(1) + 2) * DT)} s`);
      check('and the edge cue shows it', s.cue.length === 4 && s.cue[1] > 0.9 && s.cue[0] === 0, s.cue.join());
      await page.mouse.move(W / 2, 2); // top edge: look up
      await h.skip(2);
      pitch = (await state()).pitch;
      await h.skip(steps(0.4));
      s = await state();
      check('the top edge pitches up', s.pitch - pitch > 0.35 && s.pitch - pitch < 0.5 && s.cue[2] > 0.5, `pitch +${f(s.pitch - pitch)}`);
      await page.mouse.move(W / 2, H / 2);
      await h.skip(2);

      // Keys only: arrows turn, Enter fires.
      yaw = (await state()).yaw;
      await h.key('ArrowLeft', true);
      await h.key('Enter', true);
      await h.skip(steps(0.5));
      await h.key('ArrowLeft', false);
      await h.key('Enter', false);
      s = await state();
      check('arrow keys turn and Enter fires', Math.abs(wrap(s.yaw - yaw) - 2.1 * 0.5) < 0.08 && s.shots >= 5, `yaw +${f(wrap(s.yaw - yaw))}, ${s.shots} rounds`);
      // A click fires too, and asks for the lock again a few times before giving up.
      const shots = s.shots;
      for (let i = 0; i < 5; i++) {
        await h.key('Mouse0', true);
        await h.skip(4);
        await h.key('Mouse0', false);
        await h.skip(2);
      }
      s = await state();
      check('a click fires', s.shots > shots, `${s.shots - shots} more rounds`);
      check('and only the first three clicks retry the lock', s.requests === 4 && s.mode === 'drag' && s.events.length === 1, `${s.requests} requests`);

      await h.key('Escape', true);
      await h.skip(2);
      await h.key('Escape', false);
      await h.frames(2);
      await h.shot(`${OUT}3-drag-paused.png`);
      s = await state();
      check('Esc pauses in drag mode; the card explains the look mode', s.game === 'paused' && /edge/.test(s.hint), s.game);
      const card = await h.eval(() => document.querySelector('.menu-stub').textContent);
      check('the pause card carries the hint', card.includes(s.hint));
    }

    const errors = await h.errors();
    check('nothing was logged as an error', errors.length === 0, errors.slice(0, 3).join(' | '));
  }
};
