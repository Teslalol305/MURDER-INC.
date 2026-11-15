// The dynamic-resolution governor of the renderer, driven with made-up frame times.
// Run with `node --test test/`.

import test from 'node:test';
import assert from 'node:assert/strict';
import { dynamicResolution as DR } from '../src/config/quality.js';
import { createGovernor } from '../src/render.js';

const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `expected ${b}, got ${a}`);

/** A governor on a fake clock. `run(ms, seconds)` feeds frames of `ms` for about `seconds`. */
function rig({ canDrop = false } = {}) {
  const log = { changes: [], drops: 0 };
  let now = 1000;
  const governor = createGovernor(DR, {
    changed: (scale) => log.changes.push(Math.round(scale * 10) / 10),
    canDrop: () => canDrop,
    drop: () => {
      log.drops++;
    },
  });
  governor.sample(now);
  return {
    governor,
    log,
    run(ms, seconds) {
      for (let t = 0; t < seconds * 1000; t += ms) governor.sample((now += ms));
    },
    idle(seconds) {
      now += seconds * 1000;
      governor.sample(now);
    },
  };
}

test('governor: a steady 60 fps never changes the scale', () => {
  const r = rig();
  r.run(16.7, 30);
  assert.equal(r.governor.scale, 1);
  assert.deepEqual(r.log.changes, []);
});

test('governor: slow frames step the scale down, slower ones faster, to the floor and no further', () => {
  const mild = rig();
  mild.run(25, 1); // one window just over the "slow" line
  assert.equal(mild.governor.scale, 0.9);

  const heavy = rig();
  heavy.run(35, 1);
  assert.equal(heavy.governor.scale, 0.8); // two steps at once

  const awful = rig();
  awful.run(60, 1);
  assert.equal(awful.governor.scale, DR.min); // straight to the floor
  awful.run(60, 20);
  near(awful.governor.scale, DR.min);
  assert.equal(awful.log.drops, 0); // not allowed to touch the preset
  assert.deepEqual(awful.log.changes, [0.6]);
});

test('governor: nothing is measured while settling, and hitches are ignored', () => {
  const r = rig();
  r.governor.settle(1000, DR.settle);
  r.run(60, DR.settle - 0.2); // terrible frames, but inside the settle time
  assert.equal(r.governor.scale, 1);

  const h = rig();
  h.run(16.7, 0.5);
  h.idle(30); // the tab was hidden for half a minute
  h.run(16.7, 2);
  assert.equal(h.governor.scale, 1);
});

test('governor: the scale climbs back only after a wait that doubles with every drop', () => {
  const r = rig();
  r.run(25, 1); // down to 0.9; the first wait is twice the base
  assert.equal(r.governor.scale, 0.9);
  r.run(10, DR.upWait * 2 - 1.2); // fast again, but still inside the wait
  assert.equal(r.governor.scale, 0.9);
  r.run(10, 2);
  assert.equal(r.governor.scale, 1);
  assert.deepEqual(r.log.changes, [0.9, 1]);
});

test('governor: stuck at the floor twice in a row drops a preset, when the host allows it', () => {
  // A window closes after 45 frames or 900 ms, whichever comes first: at these frame times, 900 ms.
  const r = rig({ canDrop: true });
  r.run(60, 1); // to the floor
  near(r.governor.scale, DR.min);
  r.run(40, DR.settleAfterChange + 1); // first slow window at the floor
  assert.equal(r.log.drops, 0);
  r.run(40, 1); // second one
  assert.equal(r.log.drops, 1);
  near(r.governor.scale, DR.dropScale);

  const ok = rig({ canDrop: true });
  ok.run(60, 1);
  near(ok.governor.scale, DR.min);
  ok.run(22, 20); // at the floor but under the drop line: stays put
  assert.equal(ok.log.drops, 0);
  near(ok.governor.scale, DR.min);
});

test('governor: reset returns to full resolution', () => {
  const r = rig();
  r.run(60, 3);
  r.governor.reset(0);
  assert.equal(r.governor.scale, 1);
});
