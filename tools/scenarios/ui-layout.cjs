// Layout checks for the HUD and menus at one viewport size (the fix pass for the interface review).
// With UI_TOUCH=1 Chromium's touch emulation is on and the real touch controls are built (one tap).
// UI_TIME=night switches the look first. Shots: shots/ui/layout-<W>x<H>[-touch]-<n>-<name>.png.
// Every stage measures the visible HUD blocks, the location card, the radio strip, the prompt and the
// thumb controls against one another, the aim point and the viewport, and prints LAYOUT <json> lines;
// the run fails on an overlap, a clipped line, a block over the aim point or a "null" on a card.
//
//   node build.mjs --dev --out=dist/dev-fix-ui.html
//   UI_TOUCH=1 node tools/shot.cjs dist/dev-fix-ui.html --size 844x390 --params "q=test&noaudio=1&god=1" \
//     --scenario tools/scenarios/ui-layout.cjs --timeout 600
//   UI_ONLY=cutscene,intro,radio,holdout,markers,pause,pad selects stages; UI_NOSHOTS=1 skips the pictures.

const OUT = process.env.UI_OUT || 'shots/ui';
const ONLY = (process.env.UI_ONLY || '').split(',').filter(Boolean);
const want = (name) => !ONLY.length || ONLY.includes(name);

module.exports = async (page, h) => {
  const { width, height } = page.viewportSize();
  const touch = !!process.env.UI_TOUCH;
  const time = process.env.UI_TIME || 'day';
  const tag = `layout-${width}x${height}${touch ? '-touch' : ''}${time === 'night' ? '-night' : ''}`;
  let n = 0;
  const shot = async (name) => {
    n++;
    if (!process.env.UI_NOSHOTS) await h.shot(`${OUT}/${tag}-${String(n).padStart(2, '0')}-${name}.png`);
  };
  const problems = [];
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

  /** Measures every visible block; `allow` lists pairs ("a|b") that may touch in this stage. */
  const measure = async (label, allow = []) => {
    const m = await h.eval(
      ({ label, allow }) => {
        const vis = (n) => {
          if (!n || n.hidden) return false;
          for (let p = n; p && p !== document.body; p = p.parentElement) {
            if (p.hidden) return false;
            if (p !== n && Number(getComputedStyle(p).opacity) < 0.05) return false;
          }
          const cs = getComputedStyle(n);
          const r = n.getBoundingClientRect();
          return cs.visibility !== 'hidden' && cs.display !== 'none' && r.width > 0 && r.height > 0 && Number(cs.opacity) > 0.05;
        };
        const R = (n) => {
          const r = n.getBoundingClientRect();
          return { l: Math.round(r.left), t: Math.round(r.top), r: Math.round(r.right), b: Math.round(r.bottom) };
        };
        const sels = ['.hud-badge', '.hud-map', '.hud-slots', '.hud-hp', '.hud-cue', '.hud-feed-line', '.radio', '.hud-prompt', '.hud-banner-text', '.hud-msg', '.loc', '.cine-place', '.cine-card', '.cine-skip', '.touch-btn', '.touch-stick', '.touch-sprint', '.hud-mk.is-edge .hud-mk-pin']; // (on-screen markers may pass under a plate)
        const boxes = [];
        const hudOn = document.querySelector('.hud') && document.querySelector('.hud').classList.contains('is-on');
        for (const s of sels)
          for (const n of document.querySelectorAll(s)) {
            if (!vis(n)) continue;
            if (n.closest('.hud') && !hudOn) continue;
            const name = s === '.touch-btn' ? `.${n.classList[1]}` : s;
            boxes.push([name, R(n), n]);
          }
        const over = [];
        for (let i = 0; i < boxes.length; i++)
          for (let j = i + 1; j < boxes.length; j++) {
            const [a, p, na] = boxes[i];
            const [b, q, nb] = boxes[j];
            if (na.contains(nb) || nb.contains(na)) continue;
            if (a.startsWith('.touch') && b.startsWith('.touch')) continue;
            if (a === b) continue;
            if (allow.includes(`${a}|${b}`) || allow.includes(`${b}|${a}`)) continue;
            const ix = Math.min(p.r, q.r) - Math.max(p.l, q.l);
            const iy = Math.min(p.b, q.b) - Math.max(p.t, q.t);
            if (ix > 2 && iy > 2) over.push(`${a} x ${b} (${ix}x${iy})`);
          }
        const off = [];
        for (const [s, r] of boxes) if (r.l < -1 || r.t < -1 || r.r > innerWidth + 1 || r.b > innerHeight + 1) off.push(`${s} ${JSON.stringify(r)}`);
        const clip = [];
        for (const s of ['.loc-place', '.loc-tag', '.hud-zone', '.hud-obj-text', '.hud-obj-label', '.hud-banner-text', '.hud-slot-count', '.hud-badge-tally', '.hud-badge-count', '.hud-feed-line', '.hud-prompt-plate', '.card-title', '.card-hint', '.cine-place', '.cine-kicker', '.cine-title', '.cine-sub'])
          for (const n of document.querySelectorAll(s)) if (vis(n) && n.scrollWidth > n.clientWidth + 1) clip.push(`${s} ${n.scrollWidth}>${n.clientWidth} "${n.textContent}"`);
        // A block running out of its plate (the badge's tally) or under the pause / settings buttons.
        const badge = document.querySelector('.hud-badge');
        const btns = document.querySelector('.hud-btns');
        if (hudOn && vis(badge)) {
          const b = R(badge);
          for (const c of badge.querySelectorAll('.hud-badge-top > *, .hud-obj-text')) {
            if (!vis(c)) continue;
            const r = R(c);
            if (r.r > b.r + 1) clip.push(`${c.className} runs out of the badge (${r.r} > ${b.r})`);
            if (vis(btns)) {
              const q = R(btns);
              if (r.r > q.l && r.b > q.t && r.t < q.b) clip.push(`${c.className} under the map buttons (${r.r} > ${q.l})`);
            }
          }
        }
        const cx = innerWidth / 2;
        const cy = innerHeight / 2;
        const centre = [];
        for (const [s, r] of boxes) if (!s.includes('.hud-mk') && r.l < cx + 24 && r.r > cx - 24 && r.t < cy + 24 && r.b > cy - 24) centre.push(s);
        const out = { label, over, off, clip, centre };
        out.rects = Object.fromEntries(boxes.filter(([s]) => !s.startsWith('.touch')).map(([s, r]) => [s, r]));
        return out;
      },
      { label, allow },
    );
    console.error(`LAYOUT ${tag} ${JSON.stringify(m)}`);
    for (const k of ['over', 'off', 'clip', 'centre']) for (const x of m[k]) problems.push(`${label} ${k}: ${x}`);
    return m;
  };
  const press = async (selector) => {
    if (!tap) return h.click(selector);
    const r = await h.eval((sel) => {
      const b = document.querySelector(sel).getBoundingClientRect();
      return { x: Math.round(b.left + b.width / 2), y: Math.round(b.top + b.height / 2) };
    }, selector);
    await tap(r.x, r.y);
  };

  await h.frames(2);
  if (time === 'night') {
    await h.eval(() => window.__G.settings.set('time', 'night'));
    await h.frames(2);
  }

  // ---- The opening cutscene: letterbox, the place line, a long subtitle, then the title card ---------
  if (want('cutscene') || want('intro') || want('radio')) {
    await press('.title-actions .btn-primary');
    await h.skip(4);
    if ((await h.eval(() => window.__G.game.state)) === 'cutscene') {
      /** The dressing against the two bars: the place line and the card in the picture, the skip in the lower bar. */
      const dressing = async (label) => {
        const d = await h.eval(() => {
          const R = (sel) => {
            const n = document.querySelector(sel);
            if (!n || n.hidden || getComputedStyle(n).display === 'none') return null;
            const r = n.getBoundingClientRect();
            return { l: Math.round(r.left), t: Math.round(r.top), r: Math.round(r.right), b: Math.round(r.bottom) };
          };
          return {
            top: R('.menu-bars .is-top'),
            bottom: R('.menu-bars .is-bottom'),
            place: R('.cine-place'),
            card: R('.cine-card'),
            skip: R('.cine-skip'),
            radio: document.querySelector('.radio').classList.contains('is-on') ? R('.radio') : null,
            hud: document.querySelector('.hud').classList.contains('is-on'),
            touchControls: [...document.querySelectorAll('.touch-btn, .touch-stick')].some((n) => n.offsetParent !== null && getComputedStyle(n).visibility !== 'hidden' && !n.closest('[hidden]')),
            h: innerHeight,
          };
        });
        console.error(`LAYOUT ${tag} ${label} ${JSON.stringify(d)}`);
        if (!d.top || !d.bottom || d.top.b < d.h * 0.08 || d.bottom.t > d.h * 0.92) problems.push(`${label}: the letterbox is not on ${JSON.stringify([d.top, d.bottom])}`);
        if (d.hud) problems.push(`${label}: the HUD is still on`);
        if (d.touchControls) problems.push(`${label}: the thumb controls are still on`);
        for (const key of ['place', 'card', 'radio']) {
          const r = d[key];
          if (!r) continue;
          if (r.t < d.top.b - 1 || r.b > d.bottom.t + 1) problems.push(`${label}: ${key} runs into a bar ${JSON.stringify(r)}`);
        }
        if (!d.skip) problems.push(`${label}: no skip control`);
        else if (d.skip.t < d.bottom.t - 1 || d.skip.b > d.h + 1 || d.skip.b - d.skip.t < 30) problems.push(`${label}: the skip control is not a finger-sized button inside the lower bar ${JSON.stringify(d.skip)}`);
        return d;
      };
      if (want('cutscene')) {
        // The longest line of the story as the subtitle, with the place line typed on.
        await h.skip(24);
        await h.eval(() => {
          const G = window.__G;
          const lines = Object.values(G.config.text.story.scenes).flat();
          const longest = lines.reduce((a, b) => (b.text.length > a.text.length ? b : a));
          G.hud.clearRadio();
          G.hud.radio(G.config.text.story.speakers[longest.who], longest.text, 30);
        });
        await h.skip(80); // typed out
        await h.wait(1500); // the bars, the place wipe and the HUD's fade run on the real clock
        await h.frames(1);
        const d = await dressing('cutscene');
        if (!d.place) problems.push('cutscene: no place line');
        if (!d.radio) problems.push('cutscene: no subtitle');
        await measure('cutscene');
        await shot('cutscene');
        // On to the title card.
        for (let i = 0; i < 60 && !(await h.eval(() => !document.querySelector('.cine-card').hidden)); i++) await h.skip(15);
        await h.eval(() => {
          const G = window.__G;
          G.hud.clearRadio();
          G.hud.radio(G.config.text.story.speakers.rule, 'Then they want me to come get it.', 30);
        });
        await h.skip(30);
        await h.wait(1100);
        await h.frames(1);
        const c = await dressing('cutscene-card');
        if (!c.card) problems.push('cutscene: no title card');
        await measure('cutscene-card');
        await shot('cutscene-card');
      } else {
        await h.skip(30);
      }
      // The skip control ends it: a finger on the button, or the key on its cap (a captured mouse has no
      // pointer to click with).
      if (tap) await press('.cine-skip');
      else {
        const cap = await h.eval(() => document.querySelector('.cine-key').textContent);
        if (cap !== 'ENTER') problems.push(`cutscene: the skip control's key cap reads "${cap}"`);
        await h.key('Enter', true);
        await h.skip(1);
        await h.key('Enter', false);
      }
      await h.skip(2);
      const after = await h.eval(() => ({ state: window.__G.game.state, cine: !document.querySelector('.cine').hidden }));
      if (after.state !== 'intro' || after.cine) problems.push(`cutscene: the skip control did not end it ${JSON.stringify(after)}`);
      await h.eval(() => window.__G.hud.clearRadio());
    }
  }

  // ---- The intro: location card + the long briefing, as a level starts them ---------------------------
  if (want('intro') || want('radio')) {
    await h.skip(8);
    await h.eval(() => {
      const G = window.__G;
      G.hud.clearRadio();
      G.hud.radio(G.config.text.radio.speaker, G.config.text.radio.intro.text, 4.4);
    });
    await h.skip(34); // 1.4 s in: the card has wiped in, the briefing is typing
    await h.frames(1);
    const m = await measure('intro');
    const card = await h.eval(() => {
      const p = document.querySelector('.loc-place');
      const l = document.querySelector('.loc');
      return { text: p.textContent, wipe: p.style.getPropertyValue('--wipe'), shown: !l.hidden, lines: Math.round(p.getBoundingClientRect().height / parseFloat(getComputedStyle(p).lineHeight)) };
    });
    console.error(`LAYOUT ${tag} card ${JSON.stringify(card)}`);
    if (!card.shown) problems.push('intro: the location card is not up');
    await shot('intro');
    if (!m.rects['.loc']) problems.push('intro: no location card measured');
    await h.skip(40); // the wipe has finished
    await h.frames(1);
    const done = await h.eval(() => document.querySelector('.loc-place').style.getPropertyValue('--wipe'));
    if (done !== '100%') problems.push(`intro: the card wipe ended at ${done}`);
  }

  // ---- In play: the briefing still on, a reel prompt with a low-ammo cue under it --------------------
  if (want('radio')) {
    await h.skip(80);
    await h.eval(() => {
      const G = window.__G;
      G.hud.clearRadio();
      G.hud.radio(G.config.text.radio.speaker, G.config.text.radio.intro.text, 6);
      G.hud.prompt({ text: G.config.text.prompts.grab(G.input.glyph('interact'), '2'), glyph: G.input.glyph('interact'), progress: 0.4 });
      G.weapon.mag = 3; // a low magazine: the cue chip shows over the weapon bar
    });
    await h.skip(70); // most of the line typed
    await h.frames(1);
    await measure('radio+prompt');
    await shot('radio-prompt');
    // The same line held over a pause: it must still be there after resuming.
    await h.eval(() => window.__G.game.pause());
    await h.skip(400);
    await h.frames(1);
    const paused = await h.eval(() => ({ text: document.querySelector('.card').textContent, hint: !!document.querySelector('.card-hint') }));
    if (/null|undefined/.test(paused.text)) problems.push(`pause card reads: ${paused.text}`);
    await measure('pause');
    await shot('pause');
    await h.eval(() => window.__G.game.resume());
    await h.skip(2);
    const after = await h.eval(() => ({ on: document.querySelector('.radio').classList.contains('is-on'), text: document.querySelector('.radio-line').textContent.length }));
    if (!after.on || !after.text) problems.push(`radio line lost over the pause: ${JSON.stringify(after)}`);
    await h.eval(() => window.__G.hud.prompt(null));
  }

  // ---- Edge pins: two reels to the side and behind, with the kill feed up -------------------------
  if (want('markers')) {
    const state = await h.eval(() => window.__G.game.state);
    if (state !== 'playing') {
      await h.eval(() => window.__G.game.start({ mode: 'mission', skipIntro: true }));
      await h.skip(30);
    }
    await h.eval(() => {
      const G = window.__G;
      const V = G.THREE.Vector3;
      const cam = G.camera;
      cam.updateMatrixWorld();
      const right = new V(1, 0, 0).applyQuaternion(cam.quaternion);
      const fwd = new V(0, 0, -1).applyQuaternion(cam.quaternion);
      const at = (r, u, f) => cam.position.clone().addScaledVector(right, r).addScaledVector(fwd, f).add(new V(0, u, 0));
      G.hud.clearRadio(); // (with a long radio line up as well, a 667 px phone has no free spot left of centre)
      G.hud.setMarkers([
        { id: 'reel1', code: '1', pos: at(30, 30, 10), kind: 'reel' },
        { id: 'reel2', code: '2', pos: at(-40, -1.9, 8), kind: 'reel' },
        { id: 'reel3', code: '3', pos: at(-10, -1.9, -30), kind: 'reel' },
      ]);
      for (const [id, type, weapon] of [[91, 'goon', 'chopper'], [92, 'buzzard', 'nine'], [93, 'goon', 'melee']])
        G.events.emit('enemy:killed', { enemy: { id }, type, pos: G.player.pos.clone(), part: 'body', byPlayer: true, weapon });
    });
    await h.skip(3);
    await h.wait(400); // the cleared radio strip fades out in real time
    await h.frames(1);
    const mk = await h.eval(() => {
      const out = [];
      for (const n of document.querySelectorAll('.hud-mk')) {
        if (n.hidden) continue;
        const pin = n.querySelector('.hud-mk-pin').getBoundingClientRect();
        const x = pin.left + pin.width / 2;
        const y = pin.top + pin.height / 2;
        // Covered: a plate or control drawn over the pin (the HUD takes no pointer events, so by geometry).
        let covered = null;
        for (const b of document.querySelectorAll('.hud-feed-line, .hud-badge, .hud-map, .hud-slots, .radio.is-on, .touch-btn, .touch-stick')) {
          if (b.offsetParent === null && !b.classList.contains('radio')) continue;
          const q = b.getBoundingClientRect();
          if (!q.width || getComputedStyle(b).visibility === 'hidden') continue;
          if (Math.min(pin.right, q.right) - Math.max(pin.left, q.left) > 2 && Math.min(pin.bottom, q.bottom) - Math.max(pin.top, q.top) > 2) covered = b.className;
        }
        const tag = n.querySelector('.hud-mk-dist').getBoundingClientRect();
        const all = { l: Math.min(pin.left, tag.left), t: Math.min(pin.top, tag.top), r: Math.max(pin.right, tag.right), b: Math.max(pin.bottom, tag.bottom) };
        out.push({ code: n.textContent, x: Math.round(x), y: Math.round(y), covered, all });
      }
      return out;
    });
    console.error(`LAYOUT ${tag} markers ${JSON.stringify(mk)}`);
    for (const m of mk) if (m.covered) problems.push(`markers: pin ${m.code} is covered at ${m.x},${m.y}`);
    for (let i = 0; i < mk.length; i++)
      for (let j = i + 1; j < mk.length; j++) {
        const [p, q] = [mk[i].all, mk[j].all];
        if (Math.min(p.r, q.r) - Math.max(p.l, q.l) > 2 && Math.min(p.b, q.b) - Math.max(p.t, q.t) > 2) problems.push(`markers: pins ${mk[i].code} and ${mk[j].code} overlap`);
      }
    await measure('markers');
    await shot('markers');
    await h.eval(() => window.__G.hud.setMarkers([]));
  }

  // ---- Hold the Block: a long tally, a long banner, the countdown message ------------------------
  if (want('holdout')) {
    await h.eval(() => window.__G.game.start({ mode: 'holdout', skipIntro: true }));
    await h.skip(20);
    await h.eval(() => {
      const G = window.__G;
      const T = G.config.text;
      G.hud.setObjective(T.objectives.holdout.breather);
      G.hud.setTally(T.objectives.tally.wave(14, 187650));
      G.hud.warn(T.banners.wave(14, 'NORTH-WEST'), 3.6);
      G.hud.message(T.banners.countdown(15, 3), 2);
    });
    await h.skip(20);
    await h.frames(1);
    await measure('holdout');
    await shot('holdout');
  }

  // ---- Pad: open the drawer, D-pad right on the selected tab switches to Controls -------------------
  if (want('pad')) {
    await h.eval(() => window.__G.game.pause());
    await h.skip(3);
    const r = await h.eval(async () => {
      const G = window.__G;
      const real = G.input.menuNav;
      let queue = [];
      G.input.menuNav = () => queue.shift() || null;
      const step = (nav) => {
        queue.push({ x: 0, y: 0, accept: false, back: false, start: false, ...nav });
        G.menus.update(0.033);
      };
      G.input.device = 'pad';
      G.menus.openPanel('settings');
      const tab = document.querySelector('.panel-tab[aria-selected="true"]');
      tab.focus();
      step({ x: 1 });
      const afterRight = document.querySelector('.panel-tab[aria-selected="true"]').textContent;
      const first = document.querySelector('.panel-page:not([hidden]) .ctl-title');
      step({ x: -1 });
      const afterLeft = document.querySelector('.panel-tab[aria-selected="true"]').textContent;
      step({ back: true });
      G.input.menuNav = real;
      G.input.device = document.documentElement.classList.contains('is-touch') ? 'touch' : 'kbm';
      return { afterRight, afterLeft, firstTable: first ? first.textContent : null, focus: document.activeElement && document.activeElement.className };
    });
    console.error(`LAYOUT ${tag} pad ${JSON.stringify(r)}`);
    if (r.afterRight !== 'Controls' || r.afterLeft !== 'Settings') problems.push(`pad: tabs did not switch ${JSON.stringify(r)}`);
    if (r.firstTable !== 'Controller') problems.push(`pad: the controller table is not first (${r.firstTable})`);
    // The Controls tab as the active device sees it.
    await h.eval(() => window.__G.menus.openPanel('controls'));
    await h.wait(400);
    await h.frames(1);
    const first = await h.eval(() => {
      const t = document.querySelector('.panel-page:not([hidden]) .ctl-title');
      return { first: t && t.textContent, glyphs: document.querySelectorAll('.cap.is-glyph svg path, .cap.is-glyph svg circle').length };
    });
    console.error(`LAYOUT ${tag} controls ${JSON.stringify(first)}`);
    if (touch && first.first !== 'Touch') problems.push(`controls: touch table not first (${first.first})`);
    if (!first.glyphs) problems.push('controls: no glyphs in the touch key caps');
    await shot('controls');
    await h.eval(() => window.__G.game.resume());
  }

  const errors = await h.errors();
  if (errors.length) problems.push(`page errors: ${errors.join(' | ')}`);
  console.error(`LAYOUT ${tag} problems ${JSON.stringify(problems)}`);
  if (problems.length && !process.env.UI_SOFT) throw new Error(`${problems.length} layout problems:\n${problems.join('\n')}`);
};
