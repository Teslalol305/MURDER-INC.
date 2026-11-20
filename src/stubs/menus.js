// Stub menus (CONTRACT 6.12): four bare cards — title, paused, dead, complete — each wired to G.game.
// No settings or controls panels, no gamepad navigation. Styled inline so it needs nothing from ui.css.
//
// Card data passed by the game (kept by the real flow / UI modules unless they agree on more):
//   dead      {mode, time, reels, total, wave, kills, score, best, newBest}
//   complete  {mode, time, accuracy (0…1, or null with no shots), kills, retries, rating (0…5 points)}

const CARD =
  'position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);box-sizing:border-box;' +
  'width:min(440px,calc(100vw - var(--gutter-left) - var(--gutter-right)));max-height:calc(100vh - 32px);overflow:auto;' +
  'padding:14px 18px 18px;border-top:2px solid var(--c-ink);background:var(--c-plate);color:var(--c-ink);' +
  'font:15px/1.45 var(--font-ui);pointer-events:auto;-webkit-user-select:none;user-select:none;';
const BUTTON =
  'display:block;width:100%;min-height:44px;margin-top:10px;padding:10px 14px;border:1px solid var(--c-plate-edge);' +
  'background:var(--c-bg);color:var(--c-ink);font:600 15px/1.2 var(--font-ui);letter-spacing:.04em;text-align:left;cursor:pointer;';
const PRIMARY = `${BUTTON}border-color:var(--c-gold);background:var(--c-gold);color:var(--c-bg);`;

const clock = (seconds) => {
  const s = Math.max(0, Math.floor(seconds || 0));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
};

export function createMenus(G) {
  const ui = document.getElementById('ui');
  const text = G.config.text;

  const card = document.createElement('div');
  card.className = 'menu-stub';
  card.style.cssText = CARD;
  card.hidden = true;
  const place = document.createElement('div');
  place.style.cssText =
    'position:absolute;left:var(--gutter-left);bottom:calc(24px + var(--safe-bottom));padding:8px 12px;border-top:2px solid var(--c-ink);' +
    'background:var(--c-plate);color:var(--c-ink);font:600 13px/1.5 var(--font-ui);letter-spacing:.04em;';
  place.hidden = true;
  ui.append(card, place);

  // (cutscene(): the stub has no letterbox or title cards; a scene simply plays bare.)
  const menus = { screen: 'none', panelOpen: false, show, locationCard, cutscene() {}, openPanel() {}, update() {} };

  function add(tag, content, style) {
    const el = document.createElement(tag);
    el.textContent = content;
    if (style) el.style.cssText = style;
    card.append(el);
    return el;
  }

  function button(label, onClick, primary = false) {
    const el = add('button', label, primary ? PRIMARY : BUTTON);
    el.type = 'button';
    el.addEventListener('click', () => {
      G.audio.unlock(); // browsers only start sound from a user gesture
      G.events.emit('ui:click', {});
      onClick(el);
    });
    return el;
  }

  function heading(kicker, title) {
    add('div', kicker, 'color:var(--c-ink-dim);font:600 12px/1.4 var(--font-ui);letter-spacing:.18em;text-transform:uppercase;');
    add('div', title, 'margin:4px 0 10px;font:400 44px/1 var(--font-display);text-transform:uppercase;');
  }

  function stat(label, value) {
    add('div', `${label}  ${value}`, 'font:13px/1.7 var(--font-mono);color:var(--c-ink-dim);');
  }

  const SCREENS = {
    title() {
      heading(text.title.eyebrow, text.title.wordmark);
      add('div', text.title.star, 'margin-bottom:8px;color:var(--c-gold);font:600 12px/1.4 var(--font-ui);letter-spacing:.18em;');
      add('div', text.title.premise);
      const start = button(text.title.start, () => G.game.start({ mode: G.settings.get('mode') }), true);
      const modeLabel = () => `Mode: ${text.modes[G.settings.get('mode')].name}`;
      button(modeLabel(), (el) => {
        G.settings.set('mode', G.settings.get('mode') === 'mission' ? 'holdout' : 'mission');
        el.textContent = modeLabel();
      });
      const levelLabel = () => `Difficulty: ${text.difficulties[G.settings.get('difficulty')]}`;
      button(levelLabel(), (el) => {
        const order = G.config.flow.difficulties;
        G.settings.set('difficulty', order[(order.indexOf(G.settings.get('difficulty')) + 1) % order.length]);
        el.textContent = levelLabel();
      });
      add('div', text.title.note, 'margin-top:12px;color:var(--c-ink-faint);font-size:12px;');
      return start;
    },
    paused() {
      const t = text.cards.pause;
      heading(t.kicker, t.title);
      const resume = button(t.resume, () => G.game.resume(), true);
      button(t.restart, () => G.game.restart());
      add('div', G.input.hint(), 'margin-top:12px;color:var(--c-ink-faint);font-size:12px;');
      return resume;
    },
    dead(data) {
      const t = text.cards.dead;
      heading(t.kicker, t.title);
      stat(t.stats.time, clock(data.time));
      if (data.mode === 'holdout') {
        stat(t.stats.waves, data.wave);
        stat(t.stats.kills, data.kills);
        stat(t.stats.score, Math.round(data.score).toLocaleString('en-US'));
        stat(t.stats.best, `${Math.round(data.best).toLocaleString('en-US')}${data.newBest ? '  NEW' : ''}`);
      } else {
        stat(t.stats.reels, `${data.reels}/${data.total}`);
      }
      return button(t.retry, () => G.game.retry(), true);
    },
    complete(data) {
      const t = text.cards.debrief;
      heading(t.kicker, t.title);
      stat(t.stats.rating, text.ratings[data.rating] || text.ratings[0]);
      stat(t.stats.time, clock(data.time));
      stat(t.stats.accuracy, data.accuracy === null || data.accuracy === undefined ? '—' : `${Math.round(data.accuracy * 100)} %`);
      stat(t.stats.kills, data.kills);
      stat(t.stats.retries, data.retries);
      return button(t.again, () => G.game.redeploy(), true);
    },
  };

  function show(screen, data = {}) {
    const build = SCREENS[screen];
    menus.screen = build ? screen : 'none';
    card.replaceChildren();
    card.hidden = !build;
    if (build) build(data).focus({ preventScroll: true });
  }

  function locationCard(on) {
    place.hidden = !on;
    if (on) place.textContent = `${text.location.place}\n${text.location.tagline}`;
    place.style.whiteSpace = 'pre-line';
  }

  // Enter starts from the title even when focus has wandered off the button.
  window.addEventListener('keydown', (e) => {
    if (menus.screen !== 'title' || (e.code !== 'Enter' && e.code !== 'NumpadEnter')) return;
    if (document.activeElement && document.activeElement.tagName === 'BUTTON') return;
    G.audio.unlock();
    G.game.start({ mode: G.settings.get('mode') });
  });

  return menus;
}
