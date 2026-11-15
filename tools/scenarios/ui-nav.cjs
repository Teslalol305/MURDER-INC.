// Menu navigation checks: gamepad signals (input.menuNav() replaced by a scripted one), the keyboard's focus
// trap in the drawer, Esc closing the drawer without unpausing, the HUD's pause and settings buttons.
// Prints one line per check; fails on any failed check or page error.
//
//   node build.mjs --dev --only=hud,menus --out=dist/dev-ui.html
//   node tools/shot.cjs dist/dev-ui.html --params "q=test&noaudio=1&god=1" --scenario tools/scenarios/ui-nav.cjs --timeout 300

module.exports = async (page, h) => {
  const lines = [];
  let failed = 0;
  const check = (name, ok, detail = '') => {
    lines.push(`${ok ? 'ok  ' : 'FAIL'}  ${name}${detail ? `  (${detail})` : ''}`);
    if (!ok) failed++;
  };
  // Scripted gamepad: every reader in the next frame sees `signal`, later frames see nothing.
  await h.eval(() => {
    const G = window.__G;
    const idle = { x: 0, y: 0, accept: false, back: false, start: false };
    let next = null;
    window.__pad = (s) => {
      next = { ...idle, ...s };
    };
    // The signal lasts one whole frame, like the real input module's: the game reads menuNav() too (Start on
    // the title), so a read-once signal would be eaten before the menus see it.
    let live = null;
    let liveFrame = -1;
    G.input.menuNav = () => {
      const frame = G.time.frame;
      if (next) {
        live = next;
        next = null;
        liveFrame = frame;
      }
      return live && liveFrame === frame ? live : idle;
    };
  });
  const pad = async (signal) => {
    await h.eval((s) => window.__pad(s), signal);
    await h.frames(1);
  };
  const focus = () => h.eval(() => {
    const a = document.activeElement;
    return a ? `${a.tagName}.${a.className}:${(a.textContent || '').trim().slice(0, 20)}` : '';
  });

  await h.frames(2);
  await h.wait(60);
  check('title focuses its primary button', (await focus()).includes('Hit the block'), await focus());

  await pad({ y: 1 });
  const f1 = await focus();
  await pad({ y: -1 });
  check('pad down / up moves focus and wraps back', f1 !== (await focus()) && (await focus()).includes('Hit the block'), f1);

  await pad({ y: -1 }); // wraps to the last focusable
  check('pad up from the first wraps to the last', !(await focus()).includes('Hit the block'), await focus());

  // A picker: focus Story, step right to Hold the Block, accept.
  await h.eval(() => document.querySelector('.title-picks .seg-btn').focus());
  await pad({ x: 1 });
  check('pad right steps across a picker', (await focus()).includes('Hold the Block'), await focus());
  await pad({ accept: true });
  check('pad A picks', (await h.eval(() => window.__G.settings.get('mode'))) === 'holdout');
  await h.eval(() => window.__G.settings.set('mode', 'mission'));

  // Drawer: open from the title's Settings button, slider nudge, focus trap, Esc.
  await h.click('.title-actions .btn:nth-child(2)');
  await h.frames(1);
  check('drawer opens', await h.eval(() => window.__G.menus.panelOpen === true));
  const vol0 = await h.eval(() => window.__G.settings.get('volume'));
  await h.eval(() => [...document.querySelectorAll('.panel input')][1].focus()); // volume
  await pad({ x: 1 });
  const vol1 = await h.eval(() => window.__G.settings.get('volume'));
  check('pad right nudges the volume by 5', Math.abs(vol1 - Math.min(1, vol0 + 0.05)) < 1e-6, `${vol0} → ${vol1}`);
  await h.eval((v) => window.__G.settings.set('volume', v), vol0);
  let inside = true;
  for (let i = 0; i < 24; i++) {
    await page.keyboard.press('Tab');
    if (!(await h.eval(() => document.querySelector('.panel').contains(document.activeElement)))) inside = false;
  }
  check('Tab stays inside the drawer', inside);
  await page.keyboard.press('Escape');
  await h.frames(2);
  check('Esc closes the drawer', await h.eval(() => window.__G.menus.panelOpen === false));
  check('focus returns to the opener', (await focus()).includes('Settings'), await focus());

  // In a run: the HUD's gear pauses and opens the drawer; Esc closes it and the game stays paused.
  await h.eval(() => window.__G.game.start({ mode: 'mission', skipIntro: true }));
  await h.frames(3);
  await h.eval(() => document.querySelector('.hud-btn[data-action="settings"]').click());
  await h.frames(2);
  const s = await h.eval(() => ({ state: window.__G.game.state, open: window.__G.menus.panelOpen, screen: window.__G.menus.screen }));
  check('HUD gear: paused with the drawer open', s.state === 'paused' && s.open && s.screen === 'paused', JSON.stringify(s));
  await page.keyboard.press('Escape');
  await h.frames(3);
  const s2 = await h.eval(() => ({ state: window.__G.game.state, open: window.__G.menus.panelOpen }));
  check('Esc in the drawer does not unpause', s2.state === 'paused' && !s2.open, JSON.stringify(s2));
  await pad({ back: true });
  await h.frames(2);
  check('pad B on the pause card resumes', (await h.eval(() => window.__G.game.state)) === 'playing');
  await h.eval(() => document.querySelector('.hud-btn[data-action="pause"]').click());
  await h.frames(2);
  check('HUD pause button pauses', (await h.eval(() => window.__G.game.state)) === 'paused');

  // Death card: Start = the primary action.
  await h.eval(() => window.__G.menus.show('dead', { mode: 'mission', time: 30, reels: 1, total: 3, kills: 2 }));
  await h.frames(1);
  await h.eval(() => {
    window.__retried = 0;
    const g = window.__G.game;
    const retry = g.retry;
    g.retry = () => {
      window.__retried++;
      retry();
    };
  });
  await pad({ start: true });
  check('pad Start on the death card runs it back', (await h.eval(() => window.__retried)) === 1);

  console.error(lines.join('\n'));
  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors.join(' | ')}`);
  if (failed) throw new Error(`${failed} check(s) failed`);
};
