// Stub input (CONTRACT 6.3): keyboard and mouse only, no gamepad, no touch.
//
//   WASD move · Space jump · Shift sprint · C / Ctrl crouch · R reload · E interact · Q swap · 1 / 2 weapons
//   F melee · Esc / P pause · left mouse fire · right mouse aim
//
// Look uses pointer lock. When the browser will not grant it the stub falls back to 'drag' mode, where
// plain mouse movement over the page turns the view; a later click on the canvas still retries the lock.
//
// Sign convention shared with the player: look.dx > 0 turns right (yaw decreases), look.dy > 0 looks
// down (pitch decreases) unless invertY is set.

const KEY_ACTIONS = {
  KeyW: 'forward',
  KeyS: 'back',
  KeyA: 'left',
  KeyD: 'right',
  Space: 'jump',
  ShiftLeft: 'sprint',
  ShiftRight: 'sprint',
  KeyC: 'crouch',
  ControlLeft: 'crouch',
  ControlRight: 'crouch',
  KeyR: 'reload',
  KeyE: 'interact',
  KeyQ: 'swap',
  Digit1: 'weapon1',
  Digit2: 'weapon2',
  KeyF: 'melee',
  Escape: 'pause',
  KeyP: 'pause',
};
const BUTTON_ACTIONS = { 0: 'fire', 2: 'ads' };
const GLYPHS = {
  fire: 'LMB',
  ads: 'RMB',
  jump: 'SPACE',
  sprint: 'SHIFT',
  crouch: 'C',
  reload: 'R',
  interact: 'E',
  swap: 'Q',
  weapon1: '1',
  weapon2: '2',
  melee: 'F',
  pause: 'ESC',
};

const MOUSE_RATE = 0.0021; // radians per pixel at sensitivity 1
const MOUSE_GLITCH = 400; // single events larger than this are pointer-lock hiccups
const LOCK_TIMEOUT = 1200; // ms without a grant before giving up on pointer lock

export function createInput(G) {
  const doc = typeof document !== 'undefined' ? document : null;
  const canvas = (G.renderer && G.renderer.domElement) || (doc && doc.getElementById('view')) || null;

  const sources = new Map(); // held key code / mouse button → action
  const held = Object.create(null); // action → number of sources holding it
  const pressedNow = Object.create(null); // edges of the current frame
  const releasedNow = Object.create(null);
  let gameplay = true; // until the game says otherwise, so the stub also works under a stub game
  let pendingX = 0; // mouse pixels since the last update
  let pendingY = 0;
  let everLocked = false;
  let lockTimer = 0;

  const input = {
    move: { x: 0, y: 0 },
    look: { dx: 0, dy: 0 },
    locked: false,
    mode: 'lock',
    device: 'kbm',
    touch: false,
    sensitivity: 1,
    invertY: false,
    aimSlow: 1, // gamepad aim assist; mouse look ignores it
    down: (action) => active(action) && held[action] > 0,
    pressed: (action) => active(action) && pressedNow[action] === true,
    released: (action) => active(action) && releasedNow[action] === true,
    requestLock,
    exitLock,
    setGameplay,
    glyph: (action) => GLYPHS[action] || '',
    hint: () =>
      input.mode === 'drag'
        ? 'Mouse capture is off: move the mouse to look, click to fire.'
        : 'Click the street to grab the mouse. Esc lets it go.',
    rumble() {},
    update,
    endFrame,
  };

  // Outside gameplay only `pause` gets through.
  const active = (action) => gameplay || action === 'pause';
  const announce = () => G.events && G.events.emit('input:lock', { locked: input.locked, mode: input.mode });

  function press(source, action) {
    if (sources.has(source)) return;
    sources.set(source, action);
    held[action] = (held[action] || 0) + 1;
    if (held[action] === 1) pressedNow[action] = true;
  }

  function release(source) {
    const action = sources.get(source);
    if (action === undefined) return;
    sources.delete(source);
    if (--held[action] === 0) releasedNow[action] = true;
  }

  function releaseAll() {
    for (const source of [...sources.keys()]) release(source);
  }

  function useDrag() {
    if (input.mode === 'drag' || everLocked) return;
    input.mode = 'drag';
    announce();
  }

  function requestLock() {
    if (!canvas || input.locked) return;
    if (typeof canvas.requestPointerLock !== 'function') {
      useDrag();
      return;
    }
    try {
      const pending = canvas.requestPointerLock();
      if (pending && typeof pending.catch === 'function') pending.catch(useDrag);
    } catch {
      useDrag();
      return;
    }
    clearTimeout(lockTimer);
    lockTimer = setTimeout(() => {
      if (!input.locked) useDrag();
    }, LOCK_TIMEOUT);
  }

  function exitLock() {
    if (doc && doc.pointerLockElement && typeof doc.exitPointerLock === 'function') doc.exitPointerLock();
  }

  function setGameplay(on) {
    gameplay = !!on;
    if (!gameplay) {
      releaseAll();
      pendingX = pendingY = 0;
    }
  }

  function update() {
    const k = MOUSE_RATE * input.sensitivity;
    input.look.dx = pendingX * k;
    input.look.dy = pendingY * k * (input.invertY ? -1 : 1);
    pendingX = pendingY = 0;

    let x = 0;
    let y = 0;
    if (gameplay) {
      x = (held.right > 0 ? 1 : 0) - (held.left > 0 ? 1 : 0);
      y = (held.forward > 0 ? 1 : 0) - (held.back > 0 ? 1 : 0);
      if (x !== 0 && y !== 0) {
        x *= Math.SQRT1_2;
        y *= Math.SQRT1_2;
      }
    }
    input.move.x = x;
    input.move.y = y;
  }

  function endFrame() {
    for (const action in pressedNow) pressedNow[action] = false;
    for (const action in releasedNow) releasedNow[action] = false;
    input.look.dx = input.look.dy = 0;
  }

  function applySetting(key, value) {
    if (key === 'sens' && value > 0) input.sensitivity = value;
    if (key === 'invertY') input.invertY = !!value;
  }
  if (G.settings) {
    applySetting('sens', G.settings.get('sens'));
    applySetting('invertY', G.settings.get('invertY'));
  }
  if (G.events) G.events.on('settings:change', (e) => applySetting(e.key, e.value));

  if (doc && typeof window !== 'undefined') {
    const typing = (el) => !!el && /^(INPUT|SELECT|TEXTAREA)$/.test(el.tagName);

    window.addEventListener('keydown', (e) => {
      const action = KEY_ACTIONS[e.code];
      if (!action || e.repeat || e.metaKey || e.altKey || typing(e.target)) return;
      // Keep Space from scrolling the page and Ctrl (crouch) + R from reloading it mid-fight.
      if (gameplay && action !== 'pause') e.preventDefault();
      press(e.code, action);
    });
    window.addEventListener('keyup', (e) => release(e.code));
    window.addEventListener('blur', releaseAll);

    doc.addEventListener('mousemove', (e) => {
      if (!gameplay || !(input.locked || input.mode === 'drag')) return;
      const dx = e.movementX || 0;
      const dy = e.movementY || 0;
      if (Math.abs(dx) > MOUSE_GLITCH || Math.abs(dy) > MOUSE_GLITCH) return;
      pendingX += dx;
      pendingY += dy;
    });
    window.addEventListener('mouseup', (e) => release(`mouse${e.button}`));

    if (canvas) {
      canvas.addEventListener('mousedown', (e) => {
        if (!gameplay) return;
        if (!input.locked) requestLock(); // the first click both captures and fires
        const action = BUTTON_ACTIONS[e.button];
        if (action) press(`mouse${e.button}`, action);
      });
      canvas.addEventListener('contextmenu', (e) => e.preventDefault());
    }

    doc.addEventListener('pointerlockchange', () => {
      input.locked = !!canvas && doc.pointerLockElement === canvas;
      clearTimeout(lockTimer);
      if (input.locked) {
        everLocked = true;
        input.mode = 'lock';
      } else {
        // The mouse is free again: buttons held on the canvas would otherwise stick.
        release('mouse0');
        release('mouse2');
      }
      announce();
    });
    doc.addEventListener('pointerlockerror', useDrag);
  }

  return input;
}
