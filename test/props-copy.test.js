// Generated text that a brand partner reads: licence plates and every string the game paints or prints.
// The only real names allowed are the star credit (Ja Rule / Rule), IPX and real places (Hollis, Queens,
// Jamaica Ave). Plates are invented codes.

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { PLATES } from '../src/props/atlas.js';

test('plates: invented three-letter, four-digit codes, no initials of real people', () => {
  assert.ok(PLATES.length >= 4);
  for (const plate of PLATES) {
    assert.match(plate, /^[A-Z]{3}·\d{4}$/, plate);
    assert.ok(!/^(DMX|JRZ|JAR|LLC|RUN|NAS|BIG|PAC|EVE|IRV)/.test(plate), `${plate} reads as someone's name`);
  }
  assert.equal(new Set(PLATES).size, PLATES.length, 'no two alike');
});

// Real artists, labels, crews, gangs and brands that must never be painted or printed in the game.
const DENY = [
  /\bDMX\b/i, /\bRun[- ]?DMC\b/i, /\bLL Cool J\b/i, /\bJam Master\b/i, /\bDef Jam\b/i, /\bRoc[- ]?A[- ]?Fella\b/i,
  /\bRuff Ryders\b/i, /\b50 Cent\b/i, /\bG-Unit\b/i, /\bSupreme Team\b/i, /\bIrv Gotti\b/i, /\bAshanti\b/i,
  /\bBiggie\b/i, /\bTupac\b/i, /\b2Pac\b/i, /\bBloods\b/, /\bCrips\b/, /\bLatin Kings\b/i,
  /\bCoca[- ]?Cola\b/i, /\bPepsi\b/i, /\bNike\b/i, /\bTimberland\b/i, /\bHennessy\b/i, /\bNewport\b/i, /\bMarlboro\b/i,
  /\bMcDonald/i, /\bPopeyes\b/i, /\bGolden Krust\b/i,
];

function sources(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) out.push(...sources(path));
    else if (/\.(js|html|css)$/.test(name)) out.push(path);
  }
  return out;
}

test('copy: no real artists, crews, gangs or brands anywhere in the source', () => {
  const root = fileURLToPath(new URL('../src/', import.meta.url)); // (not .pathname: a folder name with a space in it)
  const hits = [];
  for (const file of sources(root)) {
    const text = readFileSync(file, 'utf8');
    for (const re of DENY) {
      const m = text.match(re);
      if (m) hits.push(`${file.slice(root.length)}: ${m[0]}`);
    }
  }
  assert.deepEqual(hits, []);
});
