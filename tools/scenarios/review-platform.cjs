// Review pass (platform): context loss / restore, hidden tab, resize mid-game, overflow at phone width.
//   node tools/shot.cjs dist/dev-review-platform.html --params "q=test&noaudio=1&god=1" --scenario tools/scenarios/review-platform.cjs --size 960x540 --timeout 600
const OUT = 'shots/review/platform';
const PARTS = (process.env.RP_PARTS || 'ctx,hidden,resize').split(',');

module.exports = async (page, h) => {
  const log = (k, v) => console.error(`[review] ${k}: ${JSON.stringify(v)}`);
  await page.mouse.move(480, 270);
  await h.eval(() => window.__G.game.start({ mode: 'mission', skipIntro: true }));
  await h.skip(30);
  await h.frames(2);
  await h.shot(`${OUT}/01-play.png`);

  if (PARTS.includes('ctx')) {
    const before = await h.eval(() => {
      const G = window.__G;
      const tex = new Set();
      G.scene.traverse((o) => {
        const ms = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
        for (const m of ms) for (const k in m) if (m[k] && m[k].isTexture) tex.add(m[k]);
      });
      let px = 0;
      const big = [];
      for (const t of tex) {
        const img = t.image;
        const w = (img && (img.width || (img.data && img.width))) || 0;
        const hh = (img && img.height) || 0;
        px += w * hh;
        if (w * hh >= 1024 * 1024) big.push(`${t.name || t.constructor.name}:${w}x${hh}`);
      }
      return { textures: tex.size, mpx: Math.round(px / 1e5) / 10, big, stats: G.render.stats() };
    });
    log('textures', before);
    await h.eval(() => {
      window.__lc = window.__G.renderer.getContext().getExtension('WEBGL_lose_context');
      window.__lc.loseContext();
    });
    await h.wait(300);
    await h.skip(60);
    await h.frames(2);
    const during = await h.eval(() => ({ state: window.__G.game.state, t: window.__G.time.t, hp: window.__G.player.health }));
    log('during-loss', during);
    await h.shot(`${OUT}/02-lost.png`);
    await h.eval(() => window.__lc.restoreContext());
    await h.wait(500);
    await h.frames(3);
    await h.shot(`${OUT}/03-restored.png`);
    log('after-restore', { stats: await h.stats(), errors: (await h.errors()).slice(-8) });
  }

  if (PARTS.includes('hidden')) {
    await h.eval(() => {
      Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
      Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    await h.skip(5);
    const hid = await h.eval(() => ({ state: window.__G.game.state }));
    await h.eval(() => {
      Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
      Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    await h.skip(5);
    await h.frames(2);
    await h.shot(`${OUT}/04-after-hidden.png`);
    log('hidden', { hid, back: await h.eval(() => window.__G.game.state) });
    await h.eval(() => window.__G.game.resume && window.__G.game.resume());
    await h.skip(5);
  }

  if (PARTS.includes('resize')) {
    for (const [w, hh] of [[400, 760], [760, 360], [960, 540]]) {
      await page.setViewportSize({ width: w, height: hh });
      await h.wait(200);
      await h.skip(3);
      await h.frames(2);
      await h.shot(`${OUT}/05-resize-${w}x${hh}.png`);
      const m = await h.eval(() => {
        const de = document.documentElement;
        const over = [];
        for (const e of document.querySelectorAll('#ui *')) {
          const r = e.getBoundingClientRect();
          if (r.width && r.height && getComputedStyle(e).visibility !== 'hidden' && (r.right > innerWidth + 1 || r.left < -1)) over.push(`${e.className}:${Math.round(r.left)}-${Math.round(r.right)}`);
        }
        const s = window.__stats();
        return { sw: de.scrollWidth, cw: de.clientWidth, bodySW: document.body.scrollWidth, canvas: [s.canvasWidth, s.canvasHeight], inner: [s.width, s.height], over: over.slice(0, 12), state: window.__G.game.state, aspect: window.__G.camera.aspect };
      });
      log(`resize ${w}x${hh}`, m);
    }
  }
};
