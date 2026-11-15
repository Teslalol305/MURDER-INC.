// Review pass (interface): every screen at one size, real touch when R_TOUCH=1, plus layout measurements.
// R_TIME=night switches the look on the title first. Output: shots/review/<tag>-NN-name.png and a JSON
// report of geometry problems on stderr.
const OUT = process.env.R_OUT || 'shots/review';

module.exports = async (page, h) => {
  const { width, height } = page.viewportSize();
  const touch = !!process.env.R_TOUCH;
  const time = process.env.R_TIME || 'day';
  const tag = `${width}x${height}${touch ? '-touch' : ''}-${time}`;
  let n = 0;
  const shot = async (name) => {
    n++;
    await h.shot(`${OUT}/${tag}-${String(n).padStart(2, '0')}-${name}.png`);
  };
  const report = {};
  await page.mouse.move(width / 2, height / 2);

  let tap = null;
  if (touch) {
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
    tap = async (x, y) => {
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ id: 1, x, y }] });
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    };
    await tap(Math.round(width * 0.7), Math.round(height * 0.3));
    await h.frames(1);
  }
  const press = async (selector) => {
    if (!tap) return h.click(selector);
    const r = await h.eval((sel) => {
      const b = document.querySelector(sel).getBoundingClientRect();
      return { x: Math.round(b.left + b.width / 2), y: Math.round(b.top + b.height / 2) };
    }, selector);
    await tap(r.x, r.y);
  };

  const measure = (label) =>
    h.eval((label) => {
      const vis = (n) => {
        if (!n) return false;
        const cs = getComputedStyle(n);
        const r = n.getBoundingClientRect();
        return cs.visibility !== 'hidden' && cs.display !== 'none' && r.width > 0 && r.height > 0 && Number(cs.opacity) > 0.05;
      };
      const R = (n) => {
        const r = n.getBoundingClientRect();
        return { l: Math.round(r.left), t: Math.round(r.top), r: Math.round(r.right), b: Math.round(r.bottom) };
      };
      const sels = ['.hud-badge', '.hud-map', '.hud-btns', '.hud-wbar', '.hud-feed', '.radio', '.hud-prompt', '.hud-banner', '.hud-msg', '.loc', '.touch-btn', '.touch-stick', '.touch-sprint', '.hud-mk'];
      const boxes = [];
      for (const s of sels) for (const n of document.querySelectorAll(s)) if (vis(n) && !n.hidden) boxes.push([s + (n.classList[1] ? '.' + n.classList[1] : ''), R(n), n]);
      const over = [];
      for (let i = 0; i < boxes.length; i++)
        for (let j = i + 1; j < boxes.length; j++) {
          const [a, p, na] = boxes[i];
          const [b, q, nb] = boxes[j];
          if (na.contains(nb) || nb.contains(na)) continue;
          if (a.startsWith('.touch') && b.startsWith('.touch')) continue;
          const ix = Math.min(p.r, q.r) - Math.max(p.l, q.l);
          const iy = Math.min(p.b, q.b) - Math.max(p.t, q.t);
          if (ix > 2 && iy > 2) over.push(`${a} x ${b} (${ix}x${iy})`);
        }
      const off = [];
      for (const [s, r] of boxes) if (r.l < 0 || r.t < 0 || r.r > innerWidth || r.b > innerHeight) off.push(`${s} ${JSON.stringify(r)}`);
      const clip = [];
      for (const s of ['.loc-place', '.loc-tag', '.hud-zone', '.hud-obj-text', '.hud-banner-text', '.hud-slot-count', '.hud-badge-tally', '.title-mark', '.card-title', '.hud-feed-line']) {
        for (const n of document.querySelectorAll(s)) if (vis(n) && n.scrollWidth > n.clientWidth + 1) clip.push(`${s} ${n.scrollWidth}>${n.clientWidth} "${n.textContent}"`);
      }
      const cx = innerWidth / 2;
      const cy = innerHeight / 2;
      const centre = [];
      for (const [s, r] of boxes) if (r.l < cx + 30 && r.r > cx - 30 && r.t < cy + 30 && r.b > cy - 30) centre.push(s);
      return { label, over, off, clip, centre };
    }, label);

  const log = async (label) => {
    const m = await measure(label);
    report[label] = m;
    console.error(`[${tag}] ${label}: ${JSON.stringify(m)}`);
  };

  await h.frames(2);
  if (time === 'night') {
    await press('.title-picks .pick:nth-child(3) .seg-btn:nth-child(2)');
    await h.frames(2);
  }
  await shot('title');
  report.title = await h.eval(() => {
    const b = document.querySelector('.title-actions .btn-primary').getBoundingClientRect();
    const s = document.querySelector('.scr-title');
    return { startBottom: Math.round(b.bottom), vh: innerHeight, scroll: s.scrollHeight > s.clientHeight, time: window.__G.atmos.time };
  });
  console.error(`[${tag}] title: ${JSON.stringify(report.title)}`);

  if (time === 'day') {
    await press('.title-actions .btn:nth-child(2)');
    await h.frames(1);
    await h.wait(400);
    await shot('settings');
    await press('.panel-tab:nth-child(2)');
    await h.frames(1);
    await shot('controls');
    await press('.panel-close');
    await h.frames(2);
  }

  await press('.title-actions .btn-primary');
  await h.skip(42);
  await h.frames(1);
  await shot('intro');
  await log('intro');
  await h.skip(120);
  await h.frames(1);
  await shot('hud-idle');
  await log('idle');

  // A fight: one reel taken, enemies close, everything at once.
  await h.eval(() => {
    const G = window.__G;
    G.game.debugGrab();
    const p = G.player.pos;
    G.enemies.spawn('goon', new G.THREE.Vector3(p.x + 14, 0, p.z - 4), { alerted: true });
    G.enemies.spawn('buzzard', new G.THREE.Vector3(p.x + 18, 4, p.z + 2), { alerted: true });
  });
  await h.skip(100);
  await h.eval(() => {
    const G = window.__G;
    const V = G.THREE.Vector3;
    const p = G.player.pos;
    G.events.emit('enemy:killed', { enemy: { id: 91 }, type: 'goon', pos: p.clone(), part: 'body', byPlayer: true, weapon: 'chopper' });
    G.events.emit('enemy:killed', { enemy: { id: 92 }, type: 'buzzard', pos: p.clone(), part: 'body', byPlayer: true, weapon: 'nine' });
    G.events.emit('enemy:killed', { enemy: { id: 93 }, type: 'goon', pos: p.clone(), part: 'head', byPlayer: true, weapon: 'melee' });
    G.events.emit('player:hit', { amount: 12, from: new V(p.x + 10, 1, p.z - 6), health: 60, kind: 'bullet' });
    G.events.emit('player:hit', { amount: 8, from: new V(p.x - 8, 1, p.z + 9), health: 60, kind: 'bullet' });
    G.hud.warn(G.config.text.banners.contact('NORTH-EAST'), 3.4);
    G.hud.radio(G.config.text.radio.speaker, G.config.text.radio.reel[2].text, 4.5);
    G.hud.prompt({ text: G.config.text.prompts.grab(G.input.glyph('interact'), '2'), glyph: G.input.glyph('interact'), progress: 0.6 });
    G.events.emit('player:hitEnemy', { enemy: { id: 3 }, part: 'head', killed: false, damage: 30, weapon: 'chopper' });
  });
  await h.skip(40);
  await h.eval(() => window.__G.events.emit('player:hitEnemy', { enemy: { id: 3 }, part: 'head', killed: true, damage: 30, weapon: 'chopper' }));
  await h.frames(2);
  await shot('fight');
  await log('fight');
  await h.eval(() => window.__G.hud.prompt(null));

  await h.eval(() => window.__G.game.pause());
  await h.frames(2);
  await shot('pause');
  await log('pause');

  const deadMission = { mode: 'mission', time: 187.4, reels: 2, total: 3, wave: 0, kills: 14, score: 0, best: 0, newBest: false, accuracy: 0.41, retries: 1, rating: 2 };
  const deadHoldout = { mode: 'holdout', time: 402, reels: 0, total: 3, wave: 6, kills: 41, score: 23580, best: 23580, newBest: true, accuracy: 0.37, retries: 0, rating: 0 };
  const complete = { mode: 'mission', time: 251.2, reels: 3, total: 3, kills: 27, accuracy: 0.52, retries: 0, rating: 5, ratingName: 'Diamond' };
  await h.eval((d) => window.__G.menus.show('dead', d), deadMission);
  await h.frames(2);
  await shot('dead-mission');
  await h.eval((d) => window.__G.menus.show('dead', d), deadHoldout);
  await h.frames(2);
  await shot('dead-holdout');
  await h.eval((d) => window.__G.menus.show('complete', d), complete);
  await h.frames(2);
  await shot('debrief');
  report.cards = await h.eval(() => {
    const c = document.querySelector('.card').getBoundingClientRect();
    const b = document.querySelector('.card .btn-primary').getBoundingClientRect();
    return { cardBottom: Math.round(c.bottom), btnBottom: Math.round(b.bottom), vh: innerHeight };
  });
  console.error(`[${tag}] cards: ${JSON.stringify(report.cards)}`);
  console.error(`REPORT ${tag} ${JSON.stringify(report)}`);
};
