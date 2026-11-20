// Stub HUD (CONTRACT 6.12): a plain debug read-out with the full API. One text block (state, health,
// ammo, objective, reels or tally, markers with distances, last warning / message / radio line), the
// interaction prompt with its progress, and a centre dot that flashes on hits. Styled inline so it
// needs nothing from ui.css.

const REFRESH = 0.1; // seconds between text rebuilds
const HIT_FLASH = 0.18;

const BLOCK = 'position:absolute;margin:0;padding:8px 10px;background:color-mix(in srgb,var(--c-bg) 70%,transparent);';

export function createHud(G) {
  const ui = document.getElementById('ui');
  const make = (tag, style) => {
    const el = document.createElement(tag);
    el.style.cssText = style;
    return el;
  };

  const root = make('div', 'position:absolute;inset:0;color:var(--c-ink);font:12px/1.5 var(--font-mono);');
  root.className = 'hud-stub';
  const info = make(
    'pre',
    `${BLOCK}left:var(--gutter-left);top:calc(12px + var(--safe-top));max-width:min(60ch,calc(100vw - 32px));font:inherit;white-space:pre-wrap;`,
  );
  const dot = make(
    'div',
    'position:absolute;left:50%;top:50%;width:4px;height:4px;margin:-2px 0 0 -2px;border-radius:50%;background:var(--c-ink);box-shadow:0 0 0 1px var(--c-bg);',
  );
  const promptEl = make('div', `${BLOCK}left:50%;top:62%;transform:translateX(-50%);text-align:center;white-space:nowrap;`);
  const promptText = make('div', '');
  const promptBar = make('div', 'height:3px;margin-top:6px;background:var(--c-plate-edge);');
  const promptFill = make('div', 'height:100%;background:var(--c-gold);transform-origin:0 50%;transform:scaleX(0);');
  promptBar.append(promptFill);
  promptEl.append(promptText, promptBar);
  promptEl.hidden = true;
  root.append(info, dot, promptEl);
  root.hidden = true;
  ui.append(root);

  let objective = '';
  let stage = ''; // the level's name, when the game gives one
  let counter = ''; // "reels 1/3" or the holdout tally
  let markers = [];
  let feed = ''; // last kill
  const lines = {
    warn: { text: '', left: 0 },
    message: { text: '', left: 0 },
    radio: { text: '', left: 0 },
  };
  let refresh = 0;
  let hitLeft = 0;
  let lastPrompt = '';
  let lastText = '';

  function setLine(name, text, secs) {
    lines[name].text = text || '';
    lines[name].left = text ? secs || 3 : 0;
  }

  function rebuild() {
    const out = [];
    const { game, player, weapon } = G;
    out.push(`${game ? `${game.state} · ${game.mode}` : 'boot'}`);
    if (player) out.push(`health     ${Math.ceil(player.health)}${player.crouching ? '  (crouched)' : ''}`);
    if (weapon && weapon.def) {
      const reserve = weapon.reserve === Infinity ? '∞' : weapon.reserve;
      out.push(`${String(weapon.def.name).padEnd(10)} ${weapon.mag} / ${reserve}${weapon.cue ? `  (${weapon.cue})` : ''}`);
    }
    if (stage) out.push(`stage      ${stage}`);
    if (objective) out.push(`objective  ${objective}`);
    if (counter) out.push(counter);
    if (player) {
      for (const m of markers) {
        out.push(`  [${m.code}] ${m.label}  ${Math.round(m.pos.distanceTo(player.pos))} m`);
      }
    }
    if (lines.warn.text) out.push(`warn       ${lines.warn.text}`);
    if (lines.message.text) out.push(`message    ${lines.message.text}`);
    if (lines.radio.text) out.push(lines.radio.text);
    if (feed) out.push(`feed       ${feed}`);
    const text = out.join('\n');
    if (text !== lastText) {
      lastText = text;
      info.textContent = text;
    }
  }

  G.events.on('player:hitEnemy', (e) => {
    hitLeft = HIT_FLASH;
    dot.style.background = e.killed ? 'var(--c-red)' : e.part === 'head' ? 'var(--c-gold)' : 'var(--c-ink)';
    dot.style.transform = 'scale(2.5)';
  });
  G.events.on('enemy:killed', (e) => {
    const names = G.config.text.enemies;
    feed = `${(names[e.type] || names.goon).down}${e.part === 'head' ? ` · ${names.headshot}` : ''}`;
  });

  return {
    show(on) {
      root.hidden = !on;
    },
    reset() {
      objective = stage = counter = feed = '';
      markers = [];
      for (const name in lines) setLine(name, '', 0);
      promptEl.hidden = true;
      lastPrompt = '';
      refresh = 0;
    },
    setStage(text) {
      stage = String(text || '');
    },
    setObjective(text) {
      objective = text || '';
    },
    setReels(done, total) {
      counter = `reels      ${done}/${total}`;
    },
    setTally(text) {
      counter = text || '';
    },
    setMarkers(list) {
      markers = list || [];
    },
    prompt(spec) {
      if (!spec) {
        if (!promptEl.hidden) promptEl.hidden = true;
        return;
      }
      if (promptEl.hidden) promptEl.hidden = false;
      if (spec.text !== lastPrompt) {
        lastPrompt = spec.text;
        promptText.textContent = spec.text;
      }
      promptFill.style.transform = `scaleX(${Math.min(1, Math.max(0, spec.progress || 0)).toFixed(3)})`;
    },
    warn: (text, secs) => setLine('warn', text, secs),
    message: (text, secs) => setLine('message', text, secs),
    radio: (speaker, text, secs) => setLine('radio', `${speaker}: ${text}`, (secs || 3) + text.length / 58),
    clearRadio: () => setLine('radio', '', 0),
    update(dt) {
      if (root.hidden) return;
      for (const name in lines) {
        const line = lines[name];
        if (line.left > 0 && (line.left -= dt) <= 0) line.text = '';
      }
      if (hitLeft > 0 && (hitLeft -= dt) <= 0) {
        dot.style.background = 'var(--c-ink)';
        dot.style.transform = '';
      }
      if ((refresh -= dt) <= 0) {
        refresh = REFRESH;
        rebuild();
      }
    },
  };
}
