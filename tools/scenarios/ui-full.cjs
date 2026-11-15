// The UI next to every real module: title → "Hit the block" → intro card → HUD in play → a fight → pause.
// With UI_TOUCH=1 the real input module's touch controls are switched on (Chromium touch emulation) and
// every control is checked against the HUD blocks for overlap.
//
//   node build.mjs --dev --out=dist/dev-ui-full.html
//   node tools/shot.cjs dist/dev-ui-full.html --params "q=low&god=1" --size 1280x720 --scenario tools/scenarios/ui-full.cjs --timeout 600
//   UI_TOUCH=1 node tools/shot.cjs dist/dev-ui-full.html --params "q=low&god=1" --size 844x390 --scenario tools/scenarios/ui-full.cjs --timeout 600

const OUT = process.env.UI_OUT || 'shots/ui';
const HUD_BLOCKS = ['.hud-badge', '.hud-map', '.hud-wbar', '.hud-feed-line', '.radio.is-on', '.hud-prompt.is-on', '.hud-banner'];

module.exports = async (page, h) => {
  const { width, height } = page.viewportSize();
  const touch = !!process.env.UI_TOUCH;
  const tag = `full-${width}x${height}${touch ? '-touch' : ''}`;
  const shot = (name) => h.shot(`${OUT}/${tag}-${name}.png`);
  await page.mouse.move(width / 2, height / 2);

  let tap = null;
  if (touch) {
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
    tap = async (x, y) => {
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ id: 1, x, y }] });
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    };
    // One tap on the street: the input module switches to the touch scheme and builds its controls.
    await tap(Math.round(width * 0.7), Math.round(height * 0.3));
    await h.frames(1);
  }
  /** A press on a menu control: a finger in touch runs (a mouse click would switch the device back). */
  const press = async (selector) => {
    if (!tap) return h.click(selector);
    const r = await h.eval((sel) => {
      const b = document.querySelector(sel).getBoundingClientRect();
      return { x: Math.round(b.left + b.width / 2), y: Math.round(b.top + b.height / 2) };
    }, selector);
    await tap(r.x, r.y);
  };

  await h.frames(2);
  const state0 = await h.eval(() => window.__G.game.state);
  if (state0 !== 'title') throw new Error(`expected the title, got ${state0}`);
  await shot('1-title');

  await press('.title-actions .btn-primary');
  await h.skip(42); // 1.4 s: the location card has wiped in
  await h.frames(1);
  await shot('2-intro');

  await h.skip(120);
  await h.frames(1);
  const s1 = await h.eval(() => ({ state: window.__G.game.state, hud: document.querySelector('.hud').classList.contains('is-on') }));
  if (s1.state !== 'playing' || !s1.hud) throw new Error(`not playing with the HUD up: ${JSON.stringify(s1)}`);
  await shot('3-play');

  // A fight: a reel taken, Vultures on the way, someone shooting back.
  await h.eval(() => {
    const G = window.__G;
    G.game.debugGrab();
    const p = G.player.pos;
    G.enemies.spawn('goon', new G.THREE.Vector3(p.x + 14, 0, p.z - 4), { alerted: true });
    G.enemies.spawn('goon', new G.THREE.Vector3(p.x + 18, 0, p.z + 2), { alerted: true });
  });
  await h.skip(150);
  await h.eval(() => {
    const G = window.__G;
    G.events.emit('player:hitEnemy', { enemy: { id: 0 }, part: 'body', killed: false, damage: 20, weapon: 'chopper' });
    G.events.emit('enemy:killed', { enemy: { id: 0 }, type: 'buzzard', pos: G.player.pos.clone(), part: 'body', byPlayer: true, weapon: 'chopper' });
  });
  await h.frames(2);
  await shot('4-fight');

  if (touch) {
    const overlaps = await h.eval((blocks) => {
      const out = [];
      const rects = [];
      for (const sel of blocks) for (const n of document.querySelectorAll(sel)) {
        const r = n.getBoundingClientRect();
        if (r.width && r.height && getComputedStyle(n).visibility !== 'hidden') rects.push([sel, r]);
      }
      for (const b of document.querySelectorAll('.touch-btn, .touch-stick-zone, .touch-stick')) {
        if (b.offsetParent === null) continue;
        const r = b.getBoundingClientRect();
        if (!r.width) continue;
        for (const [sel, q] of rects) {
          const ix = Math.min(r.right, q.right) - Math.max(r.left, q.left);
          const iy = Math.min(r.bottom, q.bottom) - Math.max(r.top, q.top);
          if (ix > 2 && iy > 2) out.push(`${b.className.baseVal || b.className} × ${sel} (${Math.round(ix)}×${Math.round(iy)})`);
        }
      }
      return { overlaps: out, buttons: document.querySelectorAll('.touch-btn').length, touch: document.documentElement.classList.contains('is-touch') };
    }, HUD_BLOCKS);
    console.error(`touch layout: ${JSON.stringify(overlaps)}`);
  }

  await h.eval(() => window.__G.game.pause());
  await h.frames(2);
  await shot('5-pause');

  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors.join(' | ')}`);
};
