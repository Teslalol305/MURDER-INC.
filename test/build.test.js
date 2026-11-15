// build.mjs: flags, module stubbing and the two page shapes. Run with `node --test test/`.
// Each case runs the real build into dist/dev-test-* (git-ignored) and removes the files afterwards.

import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('..', import.meta.url));
const OUT = 'dist/dev-test-page.html';
const FRAGMENT = 'dist/dev-test-fragment.html';

function build(...args) {
  const result = spawnSync(process.execPath, ['build.mjs', ...args], { cwd: ROOT, encoding: 'utf8' });
  return { code: result.status, out: result.stdout + result.stderr };
}

const read = (file) => readFileSync(new URL(`../${file}`, import.meta.url), 'utf8');

const clean = () => {
  for (const file of [OUT, FRAGMENT]) rmSync(new URL(`../${file}`, import.meta.url), { force: true });
};
test.before(clean); // leftovers of an interrupted run
test.after(clean);

test('build: a dev build writes a standalone document with three.js inside', () => {
  const { code, out } = build('--dev', '--stub=audio,hud', `--out=${OUT}`);
  assert.equal(code, 0, out);
  assert.match(out, /stub: .*audio/);
  const html = read(OUT);
  assert.ok(html.startsWith('<!doctype html>'));
  assert.ok(html.includes('<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'));
  assert.ok(html.includes('<title>Murder Inc.</title>'));
  assert.ok(html.includes('<canvas id="view" tabindex="0"'));
  assert.ok(html.includes('id="boot-msg"') && html.includes('id="boot-fill"') && html.includes('<div id="ui"></div>'));
  assert.ok(html.includes('sourceMappingURL=data:application/json;base64,'));
  assert.ok(!html.includes('<!--STYLE-->') && !html.includes('<!--SCRIPTS-->'));
  assert.ok(!html.includes('cdnjs.cloudflare.com'), 'the standalone page must not need a CDN');
  assert.ok(!existsSync(new URL(`../${FRAGMENT}`, import.meta.url)), 'no fragment unless asked for');
  // The bundle is the script after the font link; it must never contain a closing script tag of its own.
  const start = html.indexOf('<script>', html.indexOf('<link id="webfonts"')) + 8;
  assert.ok(start > 8);
  const body = html.slice(start, html.lastIndexOf('</script>'));
  assert.ok(body.length > 100000 && !/<\/script/i.test(body));
});

test('build: --artifact writes the page fragment that loads three.js from a CDN', () => {
  const { code, out } = build('--dev', `--out=${OUT}`, `--artifact=${FRAGMENT}`);
  assert.equal(code, 0, out);
  const html = read(FRAGMENT);
  // A fragment: no document skeleton, and it opens with the title, the fit meta and the stylesheet.
  const opening = '<title>Murder Inc.</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n<style>';
  assert.ok(html.startsWith(opening));
  for (const tag of ['<!doctype', '<html', '<head', '<body']) assert.ok(!html.toLowerCase().includes(tag), tag);
  // The boot screen comes before the web-font link so it paints without waiting for it; the script that
  // gives up on a font stylesheet that never arrives must run before the link, the game after it.
  const parts = [
    '<title>',
    '<meta name="claude:viewport-fit-sides"',
    '<style>',
    '<div id="app">',
    '<div id="boot"',
    "getElementById('webfonts')",
    '<link id="webfonts" rel="stylesheet" href="https://fonts.googleapis.com/css2?',
    'window.__MI_START=function(){',
  ];
  const order = parts.map((s) => html.indexOf(s));
  assert.ok(order.every((at, i) => at >= 0 && (i === 0 || at > order[i - 1])), `order ${order}`);
  assert.equal(html.split('<link').length - 1, 1, 'the font stylesheet is the only link');
  // The game waits inside a function; the loader knows the three CDNs, in order.
  assert.ok(html.includes('window.__MI_START=function(){'));
  const urls = [
    'https://cdnjs.cloudflare.com/ajax/libs/three.js/0.160.0/three.min.js',
    'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js',
    'https://unpkg.com/three@0.160.0/build/three.min.js',
  ].map((u) => html.indexOf(u));
  assert.ok(urls[0] > 0 && urls[0] < urls[1] && urls[1] < urls[2]);
  // three.js itself is not in the bundle (its addons are); the standalone page has both.
  const standalone = read(OUT);
  assert.ok(standalone.includes('var WebGLRenderer = class'));
  assert.ok(!html.includes('var WebGLRenderer = class'));
  assert.ok(html.includes('var EffectComposer = class'));
  // The fragment is smaller by about the size of three.js (well over a megabyte unminified).
  assert.ok(standalone.length - html.length > 1e6);
});

test('build: --only for a module that has no real file yet builds with its stub and says so', () => {
  const optional = ['mats', 'props', 'input', 'level', 'atmos', 'fx', 'audio', 'player', 'explosives', 'weapon', 'enemies', 'hud', 'menus', 'game'];
  const missing = optional.filter((name) => !existsSync(new URL(`../src/${name}.js`, import.meta.url)));
  if (missing.length === 0) return; // every module has been written: nothing left to fall back from
  const name = missing[0];
  const { code, out } = build('--dev', `--only=${name}`, `--out=${OUT}`);
  assert.equal(code, 0, out);
  assert.match(out, new RegExp(`warning: --only=${name}: src/${name}\\.js does not exist yet`));
  assert.match(out, new RegExp(`stub: .*\\b${name}\\b`));
  assert.ok(read(OUT).includes('<canvas id="view"'));
});

test('build: bad arguments fail with a message and exit code 1', () => {
  for (const [args, message] of [
    [['--nope'], /unknown argument/],
    [['--stub=render'], /cannot be stubbed/],
    [['--stub=warp'], /unknown module 'warp'/],
    [['--only=nothere'], /unknown module/],
    [['--out'], /--out needs a file name/],
  ]) {
    const { code, out } = build('--dev', ...args);
    assert.equal(code, 1, args.join(' '));
    assert.match(out, message);
  }
});
