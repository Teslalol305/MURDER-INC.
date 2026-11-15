// Pure UI rules: the numbers behind the HUD and the menus, free of DOM and three.js so they can be unit
// tested (test/ui-logic.test.js). Behaviour and timings follow the reference notes (05, UI part).

export const TAU = Math.PI * 2;

const clamp = (x, min, max) => (x < min ? min : x > max ? max : x);

// ---------------------------------------------------------------------------------------------
// Formatting
// ---------------------------------------------------------------------------------------------

/** 75.4 → "1:15". */
export function clock(seconds) {
  const s = Math.max(0, Math.floor(Number(seconds) || 0));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

/** 12345.6 → "12,346". */
export function score(n) {
  return Math.round(Number(n) || 0).toLocaleString('en-US');
}

/** Accuracy 0…1 → "42 %"; null / undefined (no shots fired) → an em dash. */
export function percent(value) {
  return value === null || value === undefined || !Number.isFinite(value) ? '—' : `${Math.round(clamp(value, 0, 1) * 100)} %`;
}

/** Reserve ammunition: Infinity reads "∞". */
export function reserveText(n) {
  return n === Infinity ? '∞' : String(Math.max(0, Math.round(Number(n) || 0)));
}

/** Whole metres for a marker: 0.4 → "0 m", 41.6 → "42 m". */
export function metres(d) {
  return `${Math.round(Math.max(0, d))} m`;
}

// ---------------------------------------------------------------------------------------------
// Typewriter and timed lines
// ---------------------------------------------------------------------------------------------

/** How many characters of a `length`-character line are out after `t` seconds at `cps` characters a second. */
export function typedCount(length, t, cps) {
  return clamp(Math.floor(Math.max(0, t) * cps), 0, length);
}

/**
 * The radio strip: lines play one at a time, typed out, held for their `secs`, then the next one.
 * A plain queue with a clock, so the HUD only has to draw what `current()` and `shown()` say.
 */
export function createRadioQueue(cps = 58) {
  const queue = [];
  let line = null;
  let t = 0;

  const typeTime = (text) => text.length / cps;

  return {
    push(speaker, text, secs) {
      const entry = { speaker: String(speaker || ''), text: String(text || ''), secs: Number.isFinite(secs) ? secs : 3 };
      if (!entry.text) return;
      if (line) queue.push(entry);
      else {
        line = entry;
        t = 0;
      }
    },
    clear() {
      queue.length = 0;
      line = null;
      t = 0;
    },
    /** Advances the clock; returns true when the line on show changed (a new one started or the strip emptied). */
    update(dt) {
      if (!line) return false;
      t += dt;
      if (t < typeTime(line.text) + line.secs) return false;
      line = queue.shift() || null;
      t = 0;
      return true;
    },
    current: () => line,
    /** Characters of the current line that are typed out so far. */
    shown: () => (line ? typedCount(line.text.length, t, cps) : 0),
    pending: () => queue.length,
  };
}

// ---------------------------------------------------------------------------------------------
// Crosshair, hit marker, banner
// ---------------------------------------------------------------------------------------------

export const DEFAULT_SPREAD = 0.012;

/**
 * Pixels from the screen centre to the inner end of each crosshair tick: the weapon's cone projected
 * onto the screen, plus a fixed 4 px (and 10 more while sprinting), clamped 4…70, in half pixels.
 */
export function crosshairGap(spread, fovDeg, viewportHeight, sprinting = false) {
  const cone = Number.isFinite(spread) && spread >= 0 ? spread : DEFAULT_SPREAD;
  const half = Math.tan(((fovDeg || 74) * Math.PI) / 360);
  const px = (Math.tan(cone) / half) * (viewportHeight / 2) + 4 + (sprinting ? 10 : 0);
  return Math.round(clamp(px, 4, 70) * 2) / 2;
}

/** Hit-marker tiers: how big it pops, how long it lasts. */
export const HIT_TIERS = {
  hit: { scale: 1.15, secs: 0.24 },
  head: { scale: 1.5, secs: 0.24 },
  kill: { scale: 1.5, secs: 0.42 },
};

/** Which tier a `player:hitEnemy` event is. */
export function hitTier(e) {
  if (e && e.killed) return 'kill';
  return e && e.part === 'head' ? 'head' : 'hit';
}

/** Hit marker at `k` = 0…1 of its life: pops at `scale`, settles to 1 by 35 %, then fades at 0.92. */
export function hitMarkerPose(k, scale) {
  if (k >= 1) return { scale: 0.92, opacity: 0 };
  if (k < 0.35) return { scale: scale + (1 - scale) * (k / 0.35), opacity: 1 };
  const u = (k - 0.35) / 0.65;
  return { scale: 1 - 0.08 * u, opacity: 1 - u };
}

/**
 * The contact banner at `k` = 0…1 of its 3.4 s: tracks in and fades up (first 8 %), one flicker dip at
 * 14 %, solid from 20 % to 82 %, then out. `spread` 1 → 0 is how far the letters still stand apart.
 */
export function bannerPose(k) {
  if (k <= 0 || k >= 1) return { opacity: 0, spread: k <= 0 ? 1 : 0 };
  let opacity = 1;
  if (k < 0.08) opacity = k / 0.08;
  else if (k < 0.14) opacity = 1 - 0.65 * ((k - 0.08) / 0.06);
  else if (k < 0.2) opacity = 0.35 + 0.65 * ((k - 0.14) / 0.06);
  else if (k > 0.82) opacity = 1 - (k - 0.82) / 0.18;
  const spread = k < 0.2 ? 1 - k / 0.2 : 0;
  return { opacity, spread: spread * spread };
}

// ---------------------------------------------------------------------------------------------
// Direction: damage arcs, markers, compass words
// ---------------------------------------------------------------------------------------------

/**
 * Screen angle (radians, clockwise from straight up) at which something at (sx, sz) lies for a player at
 * (px, pz) facing `yaw`. North is −Z, yaw 0 looks north and grows turning left.
 */
export function screenBearing(sx, sz, px, pz, yaw) {
  let a = Math.atan2(sx - px, -(sz - pz)) + yaw;
  a %= TAU;
  if (a > Math.PI) a -= TAU;
  if (a <= -Math.PI) a += TAU;
  return a;
}

/** Damage arc opacity for `life` seconds left of its 1.5: solid, then a 0.6 s fade, in steps of 0.05. */
export function arcOpacity(life) {
  return Math.round(clamp(life / 0.6, 0, 1) * 20) / 20;
}

/**
 * Where a world marker goes on screen. Input: its position in normalised device coordinates after
 * projection (x right, y up, both −1…1 on screen) and whether it is behind the camera. On screen it stays
 * where it is; otherwise it is pushed to the border of the ±limX × ±limY rectangle along its direction.
 * @returns {{x: number, y: number, off: boolean}}
 */
export function clampMarker(x, y, behind, limX = 0.9, limY = 0.82, out = { x: 0, y: 0, off: false }) {
  if (behind) {
    // A projection mirrors what is behind the lens: undo it so the direction is right again.
    x = -x;
    y = -y;
  }
  const over = Math.max(Math.abs(x) / limX, Math.abs(y) / limY);
  if (!behind && over <= 1) {
    out.x = x;
    out.y = y;
    out.off = false;
    return out;
  }
  if (over < 1e-6) {
    // Dead behind: park it at the bottom edge.
    out.x = 0;
    out.y = -limY;
  } else {
    out.x = x / over;
    out.y = y / over;
  }
  out.off = true;
  return out;
}

/** True when an on-screen marker sits over the aim point and should dim. */
export function markerOverAim(x, y) {
  return Math.hypot(x, 0.6 * y) < 0.16;
}

// ---------------------------------------------------------------------------------------------
// Minimap
// ---------------------------------------------------------------------------------------------

/**
 * World offset (dx east, dz south) from the player → map pixels (x right, y down) on a map that turns
 * with the player, who faces up. `scale` is pixels per metre.
 */
export function toMap(dx, dz, yaw, scale, out = { x: 0, y: 0 }) {
  const c = Math.cos(yaw);
  const s = Math.sin(yaw);
  out.x = (dx * c - dz * s) * scale;
  out.y = (dx * s + dz * c) * scale;
  return out;
}

/**
 * Keeps a map point inside a square of half-size `half`: points outside are pinned to its rim along
 * their direction. Returns true when the point had to be pinned.
 */
export function pinToRim(p, half) {
  const over = Math.max(Math.abs(p.x), Math.abs(p.y)) / half;
  if (over <= 1) return false;
  p.x /= over;
  p.y /= over;
  return true;
}

/** Enemy states that count as "in the fight" for the minimap. */
const ENGAGED = /engage|attack|chase|rush|fire|combat|strafe|lunge|melee/;

/** An enemy shows on the minimap while it is engaged, or for `window` seconds after it fired. */
export function enemyOnMap(enemy, now, firedAt, window = 2) {
  if (!enemy || !enemy.alive) return false;
  if (typeof enemy.state === 'string' && ENGAGED.test(enemy.state)) return true;
  if (typeof enemy.mode === 'string' && ENGAGED.test(enemy.mode)) return true;
  return firedAt !== undefined && now - firedAt < window;
}

/**
 * Sorts static colliders into what the plan draws. Anything standing on the ground and taller than
 * `tall` is a building or a wall; lower boxes are cover; invisible walls, bullet-only shells, things
 * hanging overhead and paper-thin slabs are left out.
 * @returns {'wall' | 'cover' | null}
 */
export function planKind(box, tall = 2.2) {
  if (!box || !box.min || !box.max || box.playerOnly || box.bulletOnly) return null;
  if (box.tag === 'explosive' || box.owner) return null;
  if (box.min.y > 0.9) return null; // overhead: the El deck, awnings, the scaffold deck
  const top = box.max.y;
  if (top < 0.35) return null; // kerbs, slabs
  return top > tall ? 'wall' : 'cover';
}

/** Zone band text: the level's zone id (and where in it) → the name on the map. */
export function zoneLabel(id, z, names) {
  if (id === 'lot') return z < -9 ? names.cage : names.lot;
  return names[id] || names.avenue;
}

// ---------------------------------------------------------------------------------------------
// Weapon bar and health
// ---------------------------------------------------------------------------------------------

/** "Low" is the last 27 % of a magazine. */
export const lowAmmo = (mag, magSize) => mag <= Math.ceil(magSize * 0.27);

/**
 * The cue line over the weapon bar, from weapon.cue and the device's glyphs.
 * @param {''|'reloading'|'low'|'reload'|'empty'} cue
 * @param {{reload: string, swap: string}} glyph   key caps for the current device ('' when it has none)
 * @param {'kbm'|'pad'|'touch'} device
 * @returns {{text: string, alarm: boolean}}
 */
export function cueLine(cue, glyph, device, copy) {
  const keyed = device !== 'touch';
  switch (cue) {
    case 'reloading':
      return { text: copy.reloading, alarm: false };
    case 'low':
      return { text: copy.low, alarm: false };
    case 'reload':
      return { text: keyed && glyph.reload ? `${glyph.reload} — ${copy.reload}` : copy.reload, alarm: true };
    case 'empty':
      return { text: keyed && glyph.swap ? copy.emptySwap(glyph.swap) : copy.emptyTouch, alarm: true };
    default:
      return { text: '', alarm: false };
  }
}

/** Health → what the bar shows: the number, the filled share, and whether it is critical (30 % or less). */
export function healthView(health, maxHealth, out = { value: 0, fill: 0, critical: false }) {
  const max = maxHealth > 0 ? maxHealth : 100;
  const h = clamp(Number(health) || 0, 0, max);
  out.value = Math.ceil(h);
  out.fill = Math.round((h / max) * 200) / 200;
  out.critical = h > 0 ? Math.ceil((h / max) * 10) <= 3 : true;
  return out;
}

// ---------------------------------------------------------------------------------------------
// Kill feed
// ---------------------------------------------------------------------------------------------

/** Up to `max` lines, newest last; each lives `life` seconds and fades over its last `fade`. */
export function createFeed(max = 4, life = 4.2, fade = 0.6) {
  const lines = [];
  let version = 0;
  return {
    lines,
    push(text, tag = '') {
      lines.push({ text, tag, left: life });
      while (lines.length > max) lines.shift();
      version++;
    },
    clear() {
      if (lines.length) version++;
      lines.length = 0;
    },
    update(dt) {
      for (let i = 0; i < lines.length; i++) lines[i].left -= dt;
      while (lines.length && lines[0].left <= 0) {
        lines.shift();
        version++;
      }
    },
    opacity: (line) => Math.round(clamp(line.left / fade, 0, 1) * 10) / 10,
    /** Changes whenever a line was added or removed (not while lines only fade). */
    version: () => version,
  };
}

// ---------------------------------------------------------------------------------------------
// Menus
// ---------------------------------------------------------------------------------------------

/** Next focus index in a list of `count` items, wrapping. With nothing focused, down goes first, up last. */
export function nextFocus(count, current, dir) {
  if (count <= 0) return -1;
  if (current < 0 || current >= count) return dir > 0 ? 0 : count - 1;
  return (current + (dir > 0 ? 1 : -1) + count) % count;
}

/** One gamepad push on a slider: volume moves by 5, sensitivity by 0.10, field of view by 1. */
export function nudgeSlider(value, dir, { min, max, padStep }) {
  const next = clamp(Number(value) + Math.sign(dir) * padStep, min, max);
  return Math.round(next * 1000) / 1000;
}

/** Debrief certification name for rating points 0…5. */
export function ratingName(points, names) {
  const i = clamp(Math.round(Number(points) || 0), 0, names.length - 1);
  return names[i];
}

/** Stat rows of the death card, by mode. `labels` = config/text.js cards.dead.stats. */
export function deathStats(data, labels) {
  const rows = [[labels.time, clock(data.time)]];
  if (data.mode === 'holdout') {
    rows.push([labels.waves, String(data.wave || 0)]);
    rows.push([labels.kills, String(data.kills || 0)]);
    rows.push([labels.score, score(data.score)]);
    rows.push([labels.best, score(data.best), data.newBest ? 'new' : '']);
  } else {
    rows.push([labels.reels, `${data.reels || 0}/${data.total || 3}`]);
    if (data.kills !== undefined) rows.push([labels.kills, String(data.kills || 0)]);
  }
  return rows;
}

/** Stat rows of the debrief card. `labels` = config/text.js cards.debrief.stats. */
export function debriefStats(data, labels) {
  return [
    [labels.time, clock(data.time)],
    [labels.accuracy, percent(data.accuracy)],
    [labels.kills, String(data.kills || 0)],
    [labels.retries, String(data.retries || 0)],
  ];
}
