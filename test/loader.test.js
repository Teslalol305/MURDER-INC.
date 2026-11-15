// The artifact's three.js loader (build.mjs cdnLoaderSource), run in a fake page with a manual clock:
// fallback order, slow CDNs that are kept alive, the error line, and an engine that arrives late.

import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { spawnSync } from 'node:child_process';
import { readFileSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('..', import.meta.url));
const OUT = 'dist/dev-test-loader.html';
const FRAGMENT = 'dist/dev-test-loader-fragment.html';
const clean = () => {
  for (const file of [OUT, FRAGMENT]) rmSync(new URL(`../${file}`, import.meta.url), { force: true });
};

let loader = '';
test.before(() => {
  clean();
  const result = spawnSync(process.execPath, ['build.mjs', '--dev', '--stub=audio', `--out=${OUT}`, `--artifact=${FRAGMENT}`], {
    cwd: ROOT,
    encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const html = readFileSync(new URL(`../${FRAGMENT}`, import.meta.url), 'utf8');
  const from = html.lastIndexOf('(function () {\n  var urls = ');
  const to = html.indexOf('attempt(0);\n})();', from);
  assert.ok(from > 0 && to > from, 'the loader was not found in the fragment');
  loader = html.slice(from, to + 'attempt(0);\n})();'.length);
});
test.after(clean);

/** A page with three script slots; `plan[i]` says what CDN i does: {at: ms, ok: boolean} or null (never answers). */
function page(plan) {
  let now = 0;
  let seq = 0;
  const timers = new Map();
  const scripts = [];
  const classes = new Set();
  const line = { textContent: 'Waking up the block' };
  const boot = { classList: { add: (c) => classes.add(c), remove: (c) => classes.delete(c) } };
  const window = { __fatal: undefined, starts: 0, engines: [] };
  window.__MI_START = () => {
    window.starts++;
  };
  const document = {
    getElementById: (id) => (id === 'boot' ? boot : id === 'boot-msg' ? line : null),
    createElement: () => ({ onload: null, onerror: null, src: '' }),
    head: {
      appendChild(script) {
        const i = scripts.length;
        scripts.push(script);
        const what = plan[i];
        if (!what) return;
        timers.set(++seq, {
          at: now + what.at,
          run: () => {
            if (what.ok) {
              window.THREE = { copy: i };
              window.engines.push(i);
              if (script.onload) script.onload();
            } else if (script.onerror) script.onerror();
          },
        });
      },
    },
  };
  const context = {
    window,
    document,
    setTimeout: (fn, ms) => {
      timers.set(++seq, { at: now + ms, run: fn });
      return seq;
    },
    clearTimeout: (id) => timers.delete(id),
  };
  vm.runInNewContext(loader, context);
  return {
    window,
    scripts,
    line,
    fatal: () => classes.has('is-fatal'),
    /** Runs every timer due up to `ms`, in time order. */
    advanceTo(ms) {
      for (;;) {
        let next = null;
        for (const [id, t] of timers) if (t.at <= ms && (!next || t.at < next.t.at)) next = { id, t };
        if (!next) break;
        timers.delete(next.id);
        now = next.t.at;
        next.t.run();
      }
      now = ms;
    },
  };
}

test('loader: the first CDN answers and the game starts once', () => {
  const p = page([{ at: 300, ok: true }, null, null]);
  p.advanceTo(1000);
  assert.equal(p.window.starts, 1);
  assert.equal(p.scripts.length, 1, 'no second request when the first one works');
  assert.equal(p.fatal(), false);
  p.advanceTo(60000);
  assert.equal(p.window.starts, 1);
  assert.equal(p.fatal(), false, 'the overall deadline is cancelled once the game runs');
});

test('loader: failures fall through in order; the error line only shows when every address failed', () => {
  const two = page([{ at: 50, ok: false }, { at: 50, ok: false }, { at: 200, ok: true }]);
  two.advanceTo(1000);
  assert.equal(two.window.starts, 1);
  assert.equal(two.scripts.length, 3);
  assert.equal(two.fatal(), false);

  const all = page([{ at: 50, ok: false }, { at: 50, ok: false }, { at: 50, ok: false }]);
  all.advanceTo(1000);
  assert.equal(all.window.starts, 0);
  assert.equal(all.fatal(), true);
  assert.match(all.line.textContent, /could not be downloaded/);
  assert.ok(all.window.__fatal);
});

test('loader: a slow CDN is kept alive while the next ones are tried, and wins when it delivers', () => {
  // cdnjs needs 20 s; the other two fail outright. Nothing has failed for good until the last script answers.
  const p = page([{ at: 20000, ok: true }, { at: 100, ok: false }, { at: 100, ok: false }]);
  p.advanceTo(19000);
  assert.equal(p.scripts.length, 3, 'the others were started after the per-address timeout');
  assert.equal(p.window.starts, 0);
  assert.equal(p.fatal(), false, 'two failures out of three are not the end');
  p.advanceTo(21000);
  assert.equal(p.window.starts, 1);
  assert.equal(p.fatal(), false);
});

test('loader: after the overall deadline the error shows, and an engine that still arrives clears it and boots', () => {
  const p = page([{ at: 50000, ok: true }, null, null]);
  p.advanceTo(46000);
  assert.equal(p.fatal(), true);
  assert.equal(p.window.starts, 0);
  p.advanceTo(51000);
  assert.equal(p.window.starts, 1);
  assert.equal(p.fatal(), false);
  assert.equal(p.window.__fatal, null);
  assert.equal(p.line.textContent, 'Waking up the block');
});

test('loader: a second copy that lands after the start does not replace the running engine', () => {
  // The first times out at 8 s and delivers at 9 s; the second, started at 8 s, delivers at 8.5 s and wins.
  const p = page([{ at: 9000, ok: true }, { at: 500, ok: true }, null]);
  p.advanceTo(8600);
  assert.equal(p.window.starts, 1);
  assert.equal(p.window.THREE.copy, 1);
  p.advanceTo(10000);
  assert.equal(p.window.starts, 1);
  assert.equal(p.window.THREE.copy, 1, 'the engine the game started on is put back');
});
