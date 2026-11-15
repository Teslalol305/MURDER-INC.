// Day and night rigs (CONTRACT 11.1): both are described in src/config/look.js `times` and must carry
// the same fields, so atmos.setTime() can switch between them by changing values only.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as look from '../src/config/look.js';

const keysDeep = (o, prefix = '') =>
  Object.entries(o).flatMap(([k, v]) =>
    v && typeof v === 'object' && !Array.isArray(v) ? keysDeep(v, `${prefix}${k}.`) : [`${prefix}${k}`],
  );

test('day and night describe the same fields', () => {
  const { day, night } = look.times;
  for (const section of ['grade', 'sun', 'ambient', 'fog', 'interior', 'lampGain', 'field', 'city', 'train', 'life']) {
    assert.ok(day[section], `day.${section}`);
    assert.ok(night[section], `night.${section}`);
  }
  for (const section of ['sun', 'ambient', 'fog', 'lampGain', 'field', 'train']) {
    assert.deepEqual(keysDeep(day[section]).sort(), keysDeep(night[section]).sort(), section);
  }
  for (const key of ['exposure', 'ambient', 'ambientSky', 'fog']) {
    assert.ok(key in day.interior && key in night.interior, `interior.${key}`);
  }
});

test('every grade field render.look knows is set by both times', () => {
  for (const name of ['day', 'night']) {
    const grade = look.times[name].grade;
    for (const key of Object.keys(look.grade)) {
      if (key === 'toneMapping') continue; // read once at boot
      assert.equal(typeof grade[key], 'number', `${name}.grade.${key}`);
    }
  }
});

test('lamp gains cover every lamp kind', () => {
  for (const name of ['day', 'night']) {
    for (const kind of Object.keys(look.lamps.kinds)) {
      assert.equal(typeof look.times[name].lampGain[kind], 'number', `${name}.lampGain.${kind}`);
    }
  }
  assert.equal(look.times.day.lampGain.work, 1, 'the shop keeps its work lights by day');
});

test('the day haze is bright and the night haze dark (the fog shader picks its tint by luminance)', () => {
  const lum = (c) => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  assert.ok(lum(look.times.day.fog.haze) > 0.3, 'day haze above the switch');
  assert.ok(lum(look.times.night.fog.haze) < 0.1, 'night haze below the switch');
});

test('the sun is above the horizon and lights the avenue from the west', () => {
  const [x, y, z] = look.times.day.sun.direction;
  const len = Math.hypot(x, y, z);
  const elevation = Math.asin(-y / len) * (180 / Math.PI);
  assert.ok(elevation > 35 && elevation < 70, `elevation ${elevation}`);
  assert.ok(x > 0, 'light travels east (the sun is in the west)');
});
