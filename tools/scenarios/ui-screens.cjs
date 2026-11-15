// Every UI screen and HUD state in one run, for one viewport size (shots/ui/<W>x<H>-NN-name.png).
//
//   node build.mjs --dev --only=hud,menus --out=dist/dev-ui.html
//   node tools/shot.cjs dist/dev-ui.html --params "q=test&noaudio=1&god=1" --size 1280x720 --scenario tools/scenarios/ui-screens.cjs --timeout 400
//   (also --size 844x390 and --size 390x844; add &touch=1 … no: emulate touch with UI_TOUCH=1)
//
// Set UI_ONLY=title,hud,… to take a subset. UI_TOUCH=1 puts <html> in the touch scheme (classes the input
// module would set) so the HUD's thumb-clear layout shows.

const OUT = process.env.UI_OUT || 'shots/ui';
const ONLY = (process.env.UI_ONLY || '').split(',').filter(Boolean);
const want = (name) => !ONLY.length || ONLY.includes(name);

module.exports = async (page, h) => {
  const { width, height } = page.viewportSize();
  const tag = `${width}x${height}`;
  let n = 0;
  const shot = async (name) => {
    n++;
    await h.shot(`${OUT}/${tag}-${String(n).padStart(2, '0')}-${name}.png`);
  };
  const check = async (label, fn) => {
    const r = await h.eval(fn);
    if (r !== true) throw new Error(`${label}: ${JSON.stringify(r)}`);
  };
  await page.mouse.move(width / 2, height / 2);
  if (process.env.UI_TOUCH) {
    await h.eval(() => {
      document.documentElement.classList.add('is-touch');
      document.documentElement.dataset.device = 'touch';
      if (window.__G.input) window.__G.input.device = 'touch';
    });
  }

  // Boot screen: put it back up mid-load.
  if (want('boot')) {
    await h.eval(() => {
      const boot = document.getElementById('boot');
      boot.hidden = false;
      boot.classList.remove('done');
      document.getElementById('boot-msg').textContent = 'Raising the El';
      document.getElementById('boot-fill').style.transition = 'none';
      document.getElementById('boot-fill').style.transform = 'scaleX(0.34)';
    });
    await shot('boot');
    await h.eval(() => {
      document.getElementById('boot').hidden = true;
    });
  }

  // Title
  await h.frames(2);
  await check('title is up', () => window.__G.menus.screen === 'title' || window.__G.menus.screen);
  if (want('title')) await shot('title');

  if (want('panel')) {
    await h.click('.title-actions .btn:nth-child(2)');
    await h.frames(1);
    await check('drawer open', () => window.__G.menus.panelOpen === true);
    await h.wait(400); // the drawer slides in over 0.25 s of real time
    await shot('settings');
    await h.click('.panel-tab:nth-child(2)');
    await h.frames(1);
    await shot('controls');
    await h.click('.panel-close');
    await h.frames(2);
    await check('drawer closed', () => window.__G.menus.panelOpen === false);
  }

  // A run
  await h.eval(() => window.__G.game.start({ mode: 'mission', skipIntro: true }));
  await h.frames(2);
  await h.eval(() => {
    const G = window.__G;
    G.hud.show(true);
    G.hud.setObjective(G.config.text.objectives.mission[1]);
    G.hud.setReels(1, 3);
    const objs = G.level.objectives || [];
    const markers = objs
      .filter((o) => o.code !== '1')
      .map((o) => ({ id: o.id, code: o.code, label: o.label, pos: o.pos, kind: 'reel' }));
    G.hud.setMarkers(markers);
  });
  await h.skip(60);
  await h.frames(1);
  if (want('hud')) await shot('hud-idle');

  if (want('fire')) {
    await h.eval(() => {
      const G = window.__G;
      const V = G.THREE.Vector3;
      const p = G.player.pos;
      G.events.emit('enemy:killed', { enemy: { id: 1 }, type: 'goon', pos: p.clone(), part: 'body', byPlayer: true, weapon: 'chopper' });
      G.events.emit('enemy:killed', { enemy: { id: 2 }, type: 'buzzard', pos: p.clone(), part: 'body', byPlayer: true, weapon: 'nine' });
      G.events.emit('enemy:killed', { enemy: { id: 3 }, type: 'goon', pos: p.clone(), part: 'head', byPlayer: true, weapon: 'chopper' });
      G.player.health = 38;
      G.events.emit('player:hit', { amount: 12, from: new V(p.x + 10, 1, p.z - 6), health: 38, kind: 'bullet' });
      G.events.emit('player:hit', { amount: 8, from: new V(p.x - 8, 1, p.z + 9), health: 38, kind: 'bullet' });
      G.hud.warn(G.config.text.banners.contact('NORTH-EAST'), 3.4);
      G.hud.radio(G.config.text.radio.speaker, G.config.text.radio.reel[0].text, 3.6);
      G.hud.prompt({ text: G.config.text.prompts.grab('E', '2'), glyph: 'E', progress: 0.6 });
      G.hud.message('Mouse captured — Esc lets it go', 4);
      G.events.emit('player:hitEnemy', { enemy: { id: 3 }, part: 'head', killed: false, damage: 30, weapon: 'chopper' });
    });
    await h.skip(28); // the banner is solid from 20 %, the radio line types out in ~1 s
    await h.eval(() => window.__G.events.emit('player:hitEnemy', { enemy: { id: 3 }, part: 'head', killed: true, damage: 30, weapon: 'chopper' }));
    await h.frames(2);
    await shot('hud-fire');
    await h.eval(() => window.__G.hud.prompt(null));
  }

  if (want('holdout')) {
    await h.eval(() => {
      const G = window.__G;
      G.hud.setObjective(G.config.text.objectives.holdout.hold);
      G.hud.setTally(G.config.text.objectives.tally.wave(3, 12345));
      G.hud.setMarkers([]);
    });
    await h.skip(60);
    await h.frames(1);
    await shot('hud-holdout');
  }

  if (want('location')) {
    await h.eval(() => window.__G.menus.locationCard(true, window.__G.config.text.location));
    await h.skip(40);
    await h.frames(1);
    await shot('location');
    await h.eval(() => window.__G.menus.locationCard(false));
  }

  if (want('pause')) {
    await h.eval(() => window.__G.game.pause());
    await h.frames(2);
    await check('paused card', () => window.__G.menus.screen === 'paused');
    await shot('pause');
  }

  const deadMission = { mode: 'mission', time: 187.4, reels: 2, total: 3, wave: 0, kills: 14, score: 0, best: 0, newBest: false, accuracy: 0.41, retries: 1, rating: 2 };
  const deadHoldout = { mode: 'holdout', time: 402, reels: 0, total: 3, wave: 6, kills: 41, score: 23580, best: 23580, newBest: true, accuracy: 0.37, retries: 0, rating: 0 };
  const complete = { mode: 'mission', time: 251.2, reels: 3, total: 3, kills: 27, accuracy: 0.52, retries: 0, rating: 5, ratingName: 'Diamond' };
  if (want('dead')) {
    await h.eval((d) => window.__G.menus.show('dead', d), deadMission);
    await h.frames(2);
    await shot('dead-mission');
    await h.eval((d) => window.__G.menus.show('dead', d), deadHoldout);
    await h.frames(2);
    await shot('dead-holdout');
  }
  if (want('complete')) {
    await h.eval((d) => window.__G.menus.show('complete', d), complete);
    await h.frames(2);
    await shot('debrief');
  }
  await h.eval(() => window.__G.menus.show('none'));

  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors.join(' | ')}`);
};
