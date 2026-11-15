// A quick look at the touch controls (v2 layout): two pictures per screen size, no gameplay checks.
//
//   node build.mjs --dev --only=input,player --out=dist/dev-input-player.html
//   node tools/shot.cjs dist/dev-input-player.html --size 844x390 --params "autostart=1&q=low&noaudio=1&god=1" \
//        --scenario tools/scenarios/input-player-touch-look.cjs --timeout 300
//
// Writes shots/input-player/look-<width>x<height>-rest.png (everything at rest) and -busy.png (stick pushed
// up onto the sprint-lock arrow, FIRE held, AIM and CROUCH latched, USE showing). Works against any HUD.

'use strict';

module.exports = async (page, h) => {
  const { width: W, height: H } = page.viewportSize();
  const OUT = `shots/input-player/look-${W}x${H}-`;
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  const fingers = new Map();
  const send = (type) =>
    cdp.send('Input.dispatchTouchEvent', { type, touchPoints: [...fingers].map(([id, [x, y]]) => ({ id, x: Math.round(x), y: Math.round(y) })) });
  const down = async (id, x, y) => {
    fingers.set(id, [x, y]);
    await send('touchStart');
  };
  const move = async (id, x, y) => {
    fingers.set(id, [x, y]);
    await send('touchMove');
  };
  const up = async (id) => {
    fingers.delete(id);
    await send('touchEnd');
  };
  const centreOf = (selector) =>
    h.eval((sel) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return [r.left + r.width / 2, r.top + r.height / 2, r.width];
    }, selector);

  await h.eval(() => window.__G.enemies.clear());
  await down(9, W * 0.6, H * 0.3);
  await up(9);
  await h.skip(3);
  await h.frames(2);
  await h.shot(`${OUT}rest.png`);

  const stick = await centreOf('.touch-stick');
  await down(1, stick[0], stick[1]);
  await move(1, stick[0], stick[1] - stick[2] * 0.6);
  await move(1, stick[0], stick[1] - stick[2] * 0.83); // up onto the arrow
  for (const name of ['ads', 'crouch']) {
    const c = await centreOf(`.touch-${name}`);
    await down(4, c[0], c[1]);
    await up(4);
  }
  await h.eval(() => window.__G.input.setPrompt(true));
  const fire = await centreOf('.touch-fire');
  await down(2, fire[0], fire[1]);
  await h.skip(6);
  await h.frames(2);
  await h.shot(`${OUT}busy.png`);
  const state = await h.eval(() => {
    const G = window.__G;
    const stickEl = document.querySelector('.touch-stick');
    return { move: { ...G.input.move }, sprint: G.input.down('sprint'), fire: G.input.down('fire'), ads: G.input.down('ads'), cls: stickEl.className };
  });
  console.log(JSON.stringify(state));
  await up(2);
  await up(1); // let go on the arrow: the run is locked
  await h.skip(4);
  const locked = await h.eval(() => ({ move: { ...window.__G.input.move }, sprint: window.__G.input.down('sprint'), cls: document.querySelector('.touch-stick').className }));
  console.log(JSON.stringify(locked));
  await h.frames(2);
  await h.shot(`${OUT}locked.png`);
  await h.eval(() => window.__G.input.setPrompt(false));
  const errors = await h.errors();
  if (errors.length) throw new Error(errors.slice(0, 3).join(' | '));
};
