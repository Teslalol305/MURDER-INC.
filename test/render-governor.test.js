// The dynamic-resolution governor of the renderer, driven with made-up frame streams.
// Run with `node --test test/`.

import test from 'node:test';
import assert from 'node:assert/strict';
import { dynamicResolution as DR } from '../src/config/quality.js';
import { createGovernor } from '../src/render.js';

const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `expected ${b}, got ${a}`);

/**
 * A governor on a fake clock. `frame` says how long a frame takes at a render scale (ms): a constant
 * for a vsync-capped or CPU-bound frame, or a fill-bound cost that shrinks with the pixel count.
 * `run(seconds)` feeds frames for about that long and logs the scale changes and time below 1.
 */
function rig({ canDrop = false, frame = () => 16.7 } = {}) {
  const log = { changes: [], drops: 0, below: 0 };
  let now = 1000;
  let model = frame;
  const governor = createGovernor(DR, {
    changed: (scale) => log.changes.push(Math.round(scale * 10) / 10),
    canDrop: () => canDrop,
    drop: () => {
      log.drops++;
    },
  });
  governor.sample(now);
  const step = (ms) => {
    if (governor.scale < 1) log.below += ms / 1000;
    governor.sample((now += ms));
  };
  return {
    governor,
    log,
    get now() {
      return now;
    },
    set frame(fn) {
      model = fn;
    },
    /** Frames from the model for `seconds`; `hitch(t)` may return a stall (ms) to put in at time t (s). */
    run(seconds, hitch = null) {
      const end = now + seconds * 1000;
      while (now < end) {
        const extra = hitch ? hitch(now / 1000) : 0;
        step(extra > 0 ? extra : model(governor.scale));
      }
    },
    idle(seconds) {
      now += seconds * 1000;
      governor.sample(now);
    },
  };
}

/** A GPU that spends `ms` on a full-resolution frame, 85 % of it on pixels; never under one vsync. */
const fill = (ms) => (scale) => Math.max(16.7, ms * (0.15 + 0.85 * scale * scale));
const vsync30 = () => 33.34;

test('governor: a steady 60 fps never changes the scale', () => {
  const r = rig();
  r.run(60);
  assert.equal(r.governor.scale, 1);
  assert.deepEqual(r.log.changes, []);
});

test('governor: a steady 30 fps cap (vsync, a throttled iframe) stays at full scale and never drops a preset', () => {
  const r = rig({ canDrop: true, frame: vsync30 });
  r.run(180);
  assert.equal(r.governor.scale, 1);
  assert.equal(r.log.drops, 0);
  // One probe at most (a step, then the floor in case the step was too small to cross a vsync
  // interval): when nothing got faster it is undone and not tried again.
  assert.deepEqual(r.log.changes, [0.8, DR.min, 1]);
  assert.ok(r.log.below < 5, `${r.log.below.toFixed(1)} s below full scale`);
  assert.ok(r.governor.capped);
});

test('governor: a CPU-bound frame (resolution does not matter) is left alone after one probe', () => {
  const r = rig({ canDrop: true, frame: () => 48 });
  r.run(120);
  assert.equal(r.governor.scale, 1);
  assert.equal(r.log.drops, 0);
  assert.ok(r.log.changes.length <= 3, `the scale kept moving: ${r.log.changes}`);
  assert.ok(r.log.below < 5, `${r.log.below.toFixed(1)} s below full scale`);
});

test('governor: a GPU-bound frame held at 30 Hz by vsync finds the scale that gets it back to 60', () => {
  // 30 ms of GPU work shows as 33.3 ms frames; 0.8 still misses the 16.7 ms vsync, the floor makes it.
  const quantised = (scale) => Math.ceil((30 * (0.15 + 0.85 * scale * scale)) / 16.667) * 16.667;
  const r = rig({ frame: quantised });
  r.run(60);
  assert.ok(r.governor.scale < 1, `scale ${r.governor.scale}`);
  assert.equal(r.governor.capped, false);
});

test('governor: a truly slow GPU steps down, stays down, and only then may lose a preset', () => {
  const mild = rig({ frame: fill(25) }); // 25 ms at full scale, 21 ms at 0.9
  mild.run(30);
  assert.equal(mild.governor.scale, 0.9);
  assert.deepEqual(mild.log.changes, [0.9]);

  const heavy = rig({ frame: fill(40) });
  heavy.run(60);
  assert.ok(heavy.governor.scale <= 0.7, `scale ${heavy.governor.scale}`);
  const settled = heavy.governor.scale;
  heavy.run(60);
  near(heavy.governor.scale, settled); // and it stays there
  assert.equal(heavy.log.drops, 0); // not allowed to touch the preset

  const hopeless = rig({ canDrop: true, frame: fill(90) }); // still ~40 ms at the floor
  hopeless.run(2.2);
  near(hopeless.governor.scale, DR.min);
  hopeless.run(6);
  assert.ok(hopeless.log.drops >= 1, 'stuck at the floor and slow: a preset should go');
});

test('governor: isolated 300 ms and 800 ms hitches change nothing', () => {
  for (const stall of [300, 800]) {
    const r = rig({ canDrop: true });
    let next = 5;
    r.run(240, (t) => {
      if (t < next) return 0;
      next += 20;
      return stall;
    });
    assert.equal(r.governor.scale, 1, `${stall} ms`);
    assert.deepEqual(r.log.changes, [], `${stall} ms`);
    assert.equal(r.log.drops, 0);
  }
  // A few hitches in a row inside one window are still not load.
  const b = rig();
  let n = 0;
  b.run(30, (t) => (t > 10 && n < 3 ? (n++, 250) : 0));
  assert.equal(b.governor.scale, 1);
});

test('governor: hitches on a slow device do not drop a preset by themselves', () => {
  const r = rig({ canDrop: true, frame: fill(30) }); // ~17 ms at 0.7: never needs a drop
  let next = 20;
  r.run(200, (t) => {
    if (t < next) return 0;
    next += 7;
    return 600;
  });
  assert.equal(r.log.drops, 0);
});

test('governor: recovers to full scale once the load ends, and the wait decays back', () => {
  const r = rig({ frame: fill(40) });
  r.run(30);
  assert.ok(r.governor.scale < 1);
  r.frame = () => 9; // the explosion is over
  r.run(DR.upWaitMax + 20);
  assert.equal(r.governor.scale, 1);

  // A long session of occasional load: the wait does not ratchet up for good.
  const s = rig({ frame: fill(25) });
  for (let i = 0; i < 6; i++) {
    s.frame = fill(25);
    s.run(5);
    s.frame = () => 10;
    s.run(DR.upWaitDecay + 15);
    assert.equal(s.governor.scale, 1, `round ${i}`);
  }
  // After the decay a fresh step down waits only the base time (doubled once) before trying up.
  s.frame = fill(25);
  s.run(3);
  assert.equal(s.governor.scale, 0.9);
  s.frame = () => 10;
  s.run(DR.upWait * 2 + DR.settleAfterChange + 2);
  assert.equal(s.governor.scale, 1);
});

test('governor: nothing is measured while settling, and a hidden tab is not a frame', () => {
  const r = rig({ frame: fill(60) });
  r.governor.settle(r.now, DR.settle);
  r.run(DR.settle - 0.2); // terrible frames, but inside the settle time
  assert.equal(r.governor.scale, 1);

  const h = rig();
  h.run(0.5);
  h.idle(30); // the tab was hidden for half a minute
  h.run(2);
  assert.equal(h.governor.scale, 1);
});

test('governor: the scale climbs back only after a wait that doubles with every step down', () => {
  const r = rig({ frame: fill(25) });
  r.run(3); // down to 0.9 (and proven); the first wait is twice the base
  assert.equal(r.governor.scale, 0.9);
  r.frame = () => 10;
  r.run(DR.upWait * 2 - 2.5); // fast again, but still inside the wait
  assert.equal(r.governor.scale, 0.9);
  r.run(3);
  assert.equal(r.governor.scale, 1);
  assert.deepEqual(r.log.changes, [0.9, 1]);
});

test('governor: a drop needs two slow windows at the floor and a host that allows it', () => {
  const r = rig({ canDrop: false, frame: fill(90) });
  r.run(20);
  near(r.governor.scale, DR.min);
  assert.equal(r.log.drops, 0);

  const ok = rig({ canDrop: true, frame: fill(45) }); // ~21 ms at the floor: under the drop line
  ok.run(30);
  assert.equal(ok.log.drops, 0);
});

test('governor: reset returns to full resolution', () => {
  const r = rig({ frame: fill(60) });
  r.run(5);
  r.governor.reset(r.now);
  assert.equal(r.governor.scale, 1);
  assert.equal(r.governor.capped, false);
});
