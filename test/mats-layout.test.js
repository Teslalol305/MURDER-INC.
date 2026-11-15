// Facade layout (src/mats/layout.js): the window grid of a building wall is pure data from a spec
// and a seed, so the same building is drawn the same way on every machine.

import test from 'node:test';
import assert from 'node:assert/strict';
import { facadeKey, facadeLayout, facadeSpec } from '../src/mats/layout.js';

test('mats facade: a spec is normalised, clamped and sized', () => {
  const s = facadeSpec();
  assert.deepEqual(
    { base: s.base, floors: s.floors, bays: s.bays, floorH: s.floorH, bayW: s.bayW, lit: s.lit, seed: s.seed, shopfront: s.shopfront },
    { base: 'brick_red', floors: 3, bays: 4, floorH: 3.2, bayW: 3, lit: 0.25, seed: 0, shopfront: false },
  );
  assert.equal(s.w, 12);
  assert.ok(Math.abs(s.h - 9.6) < 1e-9);

  // `w` is the wall width: the bays divide it exactly. It wins over bayW.
  const fitted = facadeSpec({ bays: 5, w: 16, bayW: 2 });
  assert.equal(fitted.bayW, 3.2);
  assert.equal(fitted.w, 16);

  const wild = facadeSpec({ floors: 99, bays: 0, floorH: 0.5, lit: 7, seed: 3.9, shopfront: 1, base: 42 });
  assert.equal(wild.floors, 12);
  assert.equal(wild.bays, 1);
  assert.equal(wild.floorH, 2.2);
  assert.equal(wild.lit, 1);
  assert.equal(wild.seed, 3);
  assert.equal(wild.shopfront, true);
  assert.equal(wild.base, 'brick_red');

  assert.equal(facadeKey(facadeSpec({ seed: 4 })), facadeKey(facadeSpec({ seed: 4, floors: 3, bays: 4 })));
  assert.notEqual(facadeKey(facadeSpec({ seed: 4 })), facadeKey(facadeSpec({ seed: 5 })));
  assert.notEqual(facadeKey(facadeSpec({ shopfront: true })), facadeKey(facadeSpec({})));
});

test('mats facade: the same seed gives the same building, another seed another one', () => {
  const s = facadeSpec({ floors: 4, bays: 6, lit: 0.35, seed: 3, shopfront: true });
  assert.deepEqual(facadeLayout(s), facadeLayout(facadeSpec({ floors: 4, bays: 6, lit: 0.35, seed: 3, shopfront: true })));
  const states = (layout) => layout.windows.map((w) => w.state).join('');
  const others = new Set();
  for (let seed = 0; seed < 8; seed++) others.add(states(facadeLayout(facadeSpec({ floors: 4, bays: 6, lit: 0.35, seed }))));
  assert.ok(others.size >= 7, 'seeds barely change which windows are lit');
});

test('mats facade: one opening per bay and floor, every one inside its own bay and storey', () => {
  for (const shopfront of [false, true]) {
    for (let seed = 0; seed < 12; seed++) {
      const s = facadeSpec({ floors: 4, bays: 5, floorH: 3.1, seed, shopfront });
      const layout = facadeLayout(s);
      const perBay = layout.style.paired ? 2 : 1;
      const upper = (s.floors - 1) * s.bays * perBay;
      // Without a shop the ground floor has windows too, one bay of them given up for the street door.
      const expected = shopfront ? upper : upper + (s.bays - 1) * perBay;
      assert.equal(layout.windows.length, expected, `seed ${seed} shop ${shopfront}`);
      assert.equal(layout.doors.length, 1);
      assert.equal(layout.units.length, shopfront ? s.bays : 0);
      assert.equal(!!layout.shop, shopfront);

      for (const w of layout.windows) {
        assert.ok(w.x >= w.bay * s.bayW && w.x + w.w <= (w.bay + 1) * s.bayW, 'window leaves its bay');
        assert.ok(w.y > w.floor * s.floorH && w.y + w.h < (w.floor + 1) * s.floorH - 0.25, 'window leaves its storey (no room for a lintel)');
        assert.ok(['dark', 'warm', 'tv'].includes(w.state));
        assert.ok(w.blind >= 0 && w.blind < 1);
        if (shopfront) assert.ok(w.floor >= 1);
      }
      for (const d of layout.doors) assert.ok(d.x >= 0 && d.x + d.w <= s.w && d.y === 0 && d.h < s.floorH);
      for (const u of layout.units) {
        assert.ok(u.x >= u.bay * s.bayW && u.x + u.w <= (u.bay + 1) * s.bayW + 1e-9, 'shop unit leaves its bay');
        assert.ok(['gate', 'glass', 'lit'].includes(u.kind));
      }
    }
  }
});

test('mats facade: exactly the asked share of windows is lit', () => {
  for (const lit of [0, 0.2, 0.5, 1]) {
    const layout = facadeLayout(facadeSpec({ floors: 5, bays: 6, lit, seed: 9 }));
    const n = layout.windows.length;
    const on = layout.windows.filter((w) => w.state !== 'dark').length;
    assert.equal(on, Math.round(lit * n), `lit ${lit}`);
  }
  // Mostly lamp light, a few televisions.
  const big = facadeLayout(facadeSpec({ floors: 12, bays: 24, lit: 1, seed: 2 }));
  const tv = big.windows.filter((w) => w.state === 'tv').length / big.windows.length;
  assert.ok(tv > 0.1 && tv < 0.35, `tv share ${tv}`);
  // A dark block has no lit shop either.
  const dark = facadeLayout(facadeSpec({ floors: 3, bays: 8, lit: 0, seed: 1, shopfront: true }));
  assert.ok(dark.units.every((u) => u.kind !== 'lit'));
});
