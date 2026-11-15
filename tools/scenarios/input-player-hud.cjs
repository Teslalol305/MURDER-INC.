// The v2 touch controls next to the real HUD (full build): layout against the HUD blocks, a tap on a HUD
// weapon slot (input.tap), and two pictures. Any screen size; run it at 844x390 and 390x844.
//
//   node build.mjs --dev --out=dist/dev-input-player-full.html
//   node tools/shot.cjs dist/dev-input-player-full.html --size 844x390 --params "autostart=1&q=low&noaudio=1&god=1" \
//        --scenario tools/scenarios/input-player-hud.cjs --timeout 600
//
// Checks: every visible control inside the viewport and clear of every other control; none over the
// mission badge, the minimap and its buttons, the weapon bar + HP, the kill feed, the radio strip, the
// banner or the prompt; in landscape the bottom-centre 40 % of the width stays free. Prints one line per
// check, fails the run on any failure. Screenshots: shots/input-player/hud-<w>x<h>-*.png.

'use strict';

const HUD_BLOCKS = ['.hud-badge', '.hud-map', '.hud-btn', '.hud-wbar', '.hud-feed-line', '.radio.is-on', '.hud-prompt.is-on', '.hud-banner.is-on'];

module.exports = async (page, h) => {
  const { width: W, height: H } = page.viewportSize();
  const OUT = `shots/input-player/hud-${W}x${H}-`;
  const lines = [];
  let failed = 0;
  const check = (name, ok, detail = '') => {
    lines.push(`${ok ? 'ok  ' : 'FAIL'}  ${name}${detail ? `  (${detail})` : ''}`);
    if (!ok) failed++;
  };

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
  // A touchEnd over CDP releases the points it lists (an empty list releases them all).
  const up = async (id) => {
    const [x, y] = fingers.get(id);
    fingers.delete(id);
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [{ id, x: Math.round(x), y: Math.round(y) }] });
  };
  const centreOf = (selector) =>
    h.eval((sel) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return [r.left + r.width / 2, r.top + r.height / 2, r.width];
    }, selector);

  // Into play, with a finger: the input module takes the touch scheme.
  await down(9, W * 0.62, H * 0.3);
  await up(9);
  for (let i = 0; i < 12; i++) {
    const s = await h.eval(() => window.__G.game.state);
    if (s === 'playing') break;
    await h.skip(30);
  }
  await h.eval(() => window.__G.enemies.clear && window.__G.enemies.clear());
  await h.skip(20);
  await h.frames(2);
  const st = await h.eval(() => ({
    state: window.__G.game.state,
    device: window.__G.input.device,
    touch: document.documentElement.classList.contains('is-touch'),
    shown: !!document.querySelector('.touch') && !document.querySelector('.touch').hidden,
  }));
  check('in play on the touch scheme with the controls showing', st.state === 'playing' && st.device === 'touch' && st.touch && st.shown, JSON.stringify(st));
  await h.shot(`${OUT}1-rest.png`);

  // Layout.
  const layout = await h.eval((blocks) => {
    const vis = (n) => n.offsetParent !== null && getComputedStyle(n).visibility !== 'hidden' && getComputedStyle(n).display !== 'none';
    const rect = (n) => {
      const r = n.getBoundingClientRect();
      return { l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height };
    };
    const hit = (a, b) => Math.min(a.r, b.r) - Math.max(a.l, b.l) > 1 && Math.min(a.b, b.b) - Math.max(a.t, b.t) > 1;
    const controls = [];
    for (const n of document.querySelectorAll('.touch-btn, .touch-stick-ring, .touch-sprint')) {
      if (vis(n)) controls.push([n.className.split(' ').find((c) => /^touch-(?!btn)/.test(c)) || n.className, rect(n)]);
    }
    const hud = [];
    for (const sel of blocks) for (const n of document.querySelectorAll(sel)) if (vis(n) && n.getBoundingClientRect().width) hud.push([sel, rect(n)]);
    const out = { controls: controls.length, hud: hud.map((x) => x[0]), outside: [], each: [], over: [], centre: [], small: [] };
    const W = innerWidth;
    const H = innerHeight;
    for (const [name, r] of controls) {
      if (r.l < 0 || r.t < 0 || r.r > W || r.b > H) out.outside.push(name);
      if (name !== 'touch-sprint' && Math.min(r.w, r.h) < 40) out.small.push(`${name} ${Math.round(r.w)}`);
      for (const [sel, q] of hud) if (hit(r, q)) out.over.push(`${name} × ${sel}`);
      if (W > H && r.r > W * 0.3 && r.l < W * 0.7 && r.b > H * 0.62) out.centre.push(name);
    }
    for (let i = 0; i < controls.length; i++) {
      for (let j = i + 1; j < controls.length; j++) {
        const a = controls[i];
        const b = controls[j];
        // The arrow belongs to the stick: it may sit over the ring's box, not over a button.
        if ((a[0] === 'touch-sprint' && b[0] === 'touch-stick-ring') || (b[0] === 'touch-sprint' && a[0] === 'touch-stick-ring')) continue;
        // Discs: overlap by centre distance, not by box.
        const ax = (a[1].l + a[1].r) / 2, ay = (a[1].t + a[1].b) / 2, bx = (b[1].l + b[1].r) / 2, by = (b[1].t + b[1].b) / 2;
        if (Math.hypot(ax - bx, ay - by) < (a[1].w + b[1].w) / 2 - 1) out.each.push(`${a[0]} × ${b[0]}`);
      }
    }
    // Room taken from the corners (for the contract).
    const right = controls.filter(([n]) => !/stick|sprint|fire2|pause/.test(n)).map((x) => x[1]);
    const left = controls.filter(([n]) => /stick|sprint|fire2/.test(n)).map((x) => x[1]);
    out.roomRight = right.length ? [Math.round(W - Math.min(...right.map((r) => r.l))), Math.round(H - Math.min(...right.map((r) => r.t)))] : null;
    out.roomLeft = left.length ? [Math.round(Math.max(...left.map((r) => r.r))), Math.round(H - Math.min(...left.map((r) => r.t)))] : null;
    return out;
  }, HUD_BLOCKS);
  check('controls built (10 discs + stick)', layout.controls >= 10, `${layout.controls} visible`);
  check('HUD blocks found', layout.hud.length >= 4, layout.hud.join(' '));
  check('every control inside the screen', layout.outside.length === 0, layout.outside.join(', '));
  check('controls do not overlap each other', layout.each.length === 0, layout.each.join(', '));
  check('no control over a HUD block', layout.over.length === 0, layout.over.join(', '));
  check('bottom-centre 40 % stays clear (landscape)', layout.centre.length === 0, layout.centre.join(', '));
  check('thumb-sized (≥ 40 px)', layout.small.length === 0, layout.small.join(', '));
  lines.push(`      room taken: right ${JSON.stringify(layout.roomRight)} left ${JSON.stringify(layout.roomLeft)} (w × h px)`);

  // A tap on the NINE slot of the HUD weapon bar swaps through input.tap.
  const nine = await centreOf('.hud-slot.is-nine');
  if (nine) {
    const before = await h.eval(() => window.__G.weapon.current);
    await down(7, nine[0], nine[1]);
    await up(7);
    await h.skip(40);
    const after = await h.eval(() => ({ current: window.__G.weapon.current, device: window.__G.input.device }));
    check('tapping the NINE slot swaps weapons', before !== 'nine' && after.current === 'nine' && after.device === 'touch', `${before} → ${after.current}, ${after.device}`);
    const chopper = await centreOf('.hud-slot.is-chopper');
    await down(7, chopper[0], chopper[1]);
    await up(7);
    await h.skip(40);
  } else {
    check('HUD weapon bar has a NINE slot', false);
  }

  // Busy: stick up onto the sprint arrow, AIM and CROUCH latched, FIRE held, USE showing.
  const stick = await centreOf('.touch-stick');
  await down(1, stick[0], stick[1]);
  await move(1, stick[0], stick[1] - stick[2] * 0.6);
  await move(1, stick[0], stick[1] - stick[2] * 0.83);
  for (const name of ['ads', 'crouch']) {
    const c = await centreOf(`.touch-${name}`);
    await down(4, c[0], c[1]);
    await up(4);
  }
  // The HUD's own prompt (the input module listens in on hud.prompt and shows USE).
  await h.eval(() => window.__G.hud.prompt({ text: 'Grab the reel', glyph: window.__G.input.glyph('interact') }));
  const fire = await centreOf('.touch-fire');
  await down(2, fire[0], fire[1]);
  await h.skip(6);
  await h.frames(2);
  const busy = await h.eval(() => {
    const G = window.__G;
    return { y: Math.round(G.input.move.y * 100) / 100, sprint: G.input.down('sprint'), fire: G.input.down('fire'), ads: G.input.down('ads'), crouch: G.input.down('crouch') };
  });
  check('stick forward + sprint, FIRE held, AIM and CROUCH latched', busy.y > 0.9 && busy.sprint && busy.fire && busy.ads && busy.crouch, JSON.stringify(busy));
  const useOver = await h.eval((blocks) => {
    const n = document.querySelector('.touch-interact');
    if (!n || getComputedStyle(n).display === 'none') return 'hidden';
    const r = n.getBoundingClientRect();
    const out = [];
    for (const sel of blocks) for (const q of document.querySelectorAll(sel)) {
      const b = q.getBoundingClientRect();
      if (b.width && Math.min(r.right, b.right) - Math.max(r.left, b.left) > 1 && Math.min(r.bottom, b.bottom) - Math.max(r.top, b.top) > 1) out.push(sel);
    }
    return out.join(' ');
  }, HUD_BLOCKS);
  check('USE shows with a prompt, clear of the HUD', useOver === '', useOver);
  const promptOver = await h.eval(() => {
    const p = document.querySelector('.hud-prompt.is-on');
    if (!p) return 'no prompt showing';
    const q = p.getBoundingClientRect();
    const out = [];
    for (const n of document.querySelectorAll('.touch-btn, .touch-stick-ring, .touch-sprint')) {
      if (n.offsetParent === null || getComputedStyle(n).display === 'none') continue;
      const r = n.getBoundingClientRect();
      if (Math.min(r.right, q.right) - Math.max(r.left, q.left) > 1 && Math.min(r.bottom, q.bottom) - Math.max(r.top, q.top) > 1) out.push(n.className.split(' ')[1]);
    }
    return out.join(' ');
  });
  check('the HUD prompt is not covered by a control', promptOver === '', promptOver);
  await h.shot(`${OUT}2-busy.png`);
  await up(2);
  await up(1);
  for (const name of ['ads', 'crouch']) {
    const c = await centreOf(`.touch-${name}`);
    await down(4, c[0], c[1]);
    await up(4);
  }
  await h.eval(() => window.__G.hud.prompt(null));
  await h.skip(4);

  const errors = await h.errors();
  check('no page errors', errors.length === 0, errors.slice(0, 3).join(' | '));
  console.log(lines.join('\n'));
  if (failed) throw new Error(`${failed} check(s) failed`);
};
