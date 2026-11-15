// Every sound the game can play, by name, and how to render one variant of it. Pure: runs in node for the
// level tests, and in the browser inside the background render queue.
//
// A definition: {bus, gen(c), n (variants), peak (normalisation target), sr, loop, stereo, + playback
// defaults read by the mixer: vol, jitter, prio, max (polyphony per name), gap (min seconds between plays),
// ref / roll (distance model)}. `gen` returns a Float32Array, or an array of them (channels), and may be a
// generator function that yields between expensive steps.

import { WEAPONS } from './sfx-weapons.js';
import { PLAYER } from './sfx-player.js';
import { WORLD } from './sfx-world.js';
import { ENEMIES } from './sfx-enemies.js';
import { AMBIENCE } from './sfx-ambience.js';
import { MUSIC_SFX } from './music.js';
import { seeded, hashName, fade, measure } from './dsp.js';

export const SOUNDS = { ...WEAPONS, ...PLAYER, ...WORLD, ...ENEMIES, ...AMBIENCE, ...MUSIC_SFX };

export const DEFAULT_SR = 44100;

/**
 * Render order for the background queue: what the first seconds of play need comes first (the guns, the
 * feet, hits), then the enemies, then the calm music layers, the beds, everything else.
 */
const ORDER = [
  /^(chopper|nine)_shot$/, /^dry_fire$/, /_tail_/, /^step_/, /^(hit_|kill_)/, /^imp_/, /^ui_/,
  /^(rifle|pistol)_/, /^(holster|draw|cloth|whoosh|melee_thud|brass_)/, /^(hurt|land|jump|ear_ring)$/,
  /^(smg_shot|goon_|alert_|grunt_|bolt_shot|buzzard_|rotor|whizz|ricochet|pipe_swing|body_fall)/,
  /^stem_(drums|bass|crackle|keys|hats)$/, /^bed_/, /^explosion_/, /^(hiss|reel_|heartbeat|radio_)/,
  /^stem_/, /^sting_/, /^m_/, /^boombox$/,
];

export function renderPriority(name) {
  for (let i = 0; i < ORDER.length; i++) if (ORDER[i].test(name)) return i;
  return ORDER.length;
}

/** Names in render order (stable within a priority). */
export function renderOrder() {
  return Object.keys(SOUNDS)
    .map((name, i) => ({ name, i, p: renderPriority(name) }))
    .sort((a, b) => a.p - b.p || a.i - b.i)
    .map((e) => e.name);
}

const LONG = 65536; // samples: past this the normalisation passes get their own steps

function sum(ch) {
  let m = 0;
  for (let i = 0; i < ch.length; i++) m += ch[i];
  return m;
}

function offset(ch, mean) {
  for (let i = 0; i < ch.length; i++) ch[i] -= mean;
}

function scale(ch, g) {
  for (let i = 0; i < ch.length; i++) ch[i] *= g;
}

/**
 * One variant, as a generator (yields between steps; the return value is the result):
 * {name, variant, sr, channels: Float32Array[]}. Peak-normalised; one-shots get click-free ends.
 */
export function* renderVariant(name, variant = 0) {
  const def = SOUNDS[name];
  if (!def) throw new Error(`no sound named ${name}`);
  const sr = def.sr || DEFAULT_SR;
  const rnd = seeded(hashName(name) + variant * 7919);
  const c = { sr, v: variant, rnd, r: (a, b) => a + (b - a) * rnd(), buf: (secs) => new Float32Array(Math.max(1, Math.round(secs * sr))) };
  let out = def.gen(c);
  if (out && typeof out.next === 'function') {
    let step;
    while (!(step = out.next()).done) yield;
    out = step.value;
  }
  const channels = Array.isArray(out) ? out : [out];
  // One gain for every channel keeps a stereo image; normalise against the loudest. A pass over a long
  // stem is a few hundred thousand samples: the queue gets a step boundary between passes.
  const long = channels[0].length > LONG;
  let top = 0;
  for (const ch of channels) {
    const mean = sum(ch) / (ch.length || 1);
    if (long) yield;
    offset(ch, mean);
    if (long) yield;
    top = Math.max(top, measure(ch).peak);
    if (long) yield;
  }
  for (const ch of channels) {
    const g = top > 1e-9 ? (def.peak || 0.8) / top : 0;
    scale(ch, g);
    if (!def.loop && !def.noFade) fade(ch, sr, 0.0015, Math.min(0.02, ch.length / sr / 4));
    if (long) yield;
  }
  return { name, variant, sr, channels };
}

/** Synchronous render (tests, and short sounds asked for before the queue got to them). */
export function renderNow(name, variant = 0) {
  const it = renderVariant(name, variant);
  let step;
  while (!(step = it.next()).done);
  return step.value;
}

export const variantsOf = (name) => (SOUNDS[name] && SOUNDS[name].n) || 1;
