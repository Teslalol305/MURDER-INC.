#!/usr/bin/env node
// Headless test harness (docs/CONTRACT.md section 2): loads a built page in Chromium with software
// WebGL, drives it frame by frame, takes screenshots and reports what went wrong.
//
//   node tools/shot.cjs dist/dev-level.html --params "autostart=1&q=low" --frames 120 --out shots/level/a.png
//   node tools/shot.cjs dist/dev-level.html --scenario tools/scenarios/level-walk.cjs
//   node tools/shot.cjs dist/artifact.html --artifact-cdn --params "autostart=1"
//
// Options
//   --params "a=1&b=2"   URL parameters for the page
//   --size WxH           viewport in CSS pixels (default 960x540; keep it small, rendering is slow)
//   --frames N           frames to advance before the screenshot (default 60; ignored with --scenario)
//   --skip N             first simulate N frames without drawing (fast: for getting deep into a run)
//   --scenario file.cjs  run a scenario instead of the default "advance, then one screenshot"
//   --out file.png       screenshot path for the default run (default shots/shot.png)
//   --timeout S          give up after S seconds (default 300)
//   --realtime           do not add step=1&dt=0.0333: the page runs on its own clock
//   --artifact-cdn       answer the three.js CDN requests of dist/artifact.html from node_modules
//   --cdn-fail N         with --artifact-cdn: make the first N CDN addresses fail (tests the fallback chain)
//   --verbose            echo the whole page console
//
// Environment
//   SHOT_CHROME=/path/to/chrome   run this browser instead of the one Playwright downloaded for itself
//   SHOT_GPU=1                    leave WebGL to the machine's GPU: many times faster than software GL, and
//                                 the simulation is just as deterministic; only the pictures differ a little
//
// The page is loaded with step=1&dt=0.0333 unless --realtime is given, so the simulation only advances
// when asked and a run is identical on any machine. Every other network request is refused: the game
// must work offline.
//
// A scenario is a CommonJS module: module.exports = async (page, h) => { ... } with
//   h.frames(n)             advance n drawn frames
//   h.skip(n)               advance n frames without drawing (simulation only)
//   h.shot(path)            screenshot (PNG)
//   h.eval(fnOrString, arg) run code in the page, returns its (serialisable) result
//   h.key(code, down)       press / release a key by KeyboardEvent.code ('KeyW', 'Space', 'ShiftLeft'…),
//                           or a mouse button: 'Mouse0' (left), 'Mouse1' (middle), 'Mouse2' (right)
//   h.mouse(dx, dy)         relative mouse look: a `mousemove` with movementX / movementY on the canvas
//   h.click(selector)       real click on a DOM element (menus)
//   h.errors(), h.stats()   window.__errors / window.__stats()
//   h.heap()                bytes of JS heap in use right now; h.heap(true) collects garbage first (needs SHOT_GC=1)
//                           (the browser is started with gc() exposed and precise memory numbers)
//   h.wait(ms)              real-time pause (rarely needed in step mode)
//
// At the end the harness prints window.__errors, window.__fatal and __stats() as JSON and exits with
// code 1 if there was an error, a fatal, or the run itself failed.

'use strict';

const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');
const GL_ARGS = process.env.SHOT_GPU
  ? ['--ignore-gpu-blocklist', '--enable-unsafe-swiftshader']
  : ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
// Unrounded performance.memory for h.heap(). SHOT_GC=1 also exposes window.gc() so h.heap(true) can collect first:
// it is opt-in because with that flag V8 lets dead typed arrays pile up (gigabytes while audio renders its buffers).
// Scenarios that measure allocations (file name contains perf / stress / heap) get it automatically.
const memoryArgs = (scenario) =>
  process.env.SHOT_GC || /perf|stress|heap/.test(path.basename(scenario || ''))
    ? ['--js-flags=--expose-gc', '--enable-precise-memory-info']
    : ['--enable-precise-memory-info'];
const THREE_MIN = path.join(ROOT, 'node_modules', 'three', 'build', 'three.min.js');
// Same order as build.mjs.
const CDN_HOSTS = ['cdnjs.cloudflare.com', 'cdn.jsdelivr.net', 'unpkg.com'];
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.png': 'image/png',
};

const USAGE = 'usage: node tools/shot.cjs <page.html> [--params "a=1&b=2"] [--size WxH] [--frames N] [--skip N]\n' +
  '       [--scenario file.cjs] [--out file.png] [--timeout S] [--realtime] [--artifact-cdn] [--cdn-fail N] [--verbose]';

function parseArgs(argv) {
  const opts = {
    file: null,
    params: '',
    width: 960,
    height: 540,
    frames: 60,
    skip: 0,
    scenario: null,
    out: path.join('shots', 'shot.png'),
    timeout: 300,
    realtime: false,
    artifactCdn: false,
    cdnFail: 0,
    verbose: false,
  };
  const number = (flag, value) => {
    const n = Number(value);
    if (!Number.isFinite(n) || n < 0) throw new Error(`${flag} needs a number`);
    return n;
  };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    const eq = arg.startsWith('--') ? arg.indexOf('=') : -1;
    const flag = eq < 0 ? arg : arg.slice(0, eq);
    const value = () => {
      const v = eq >= 0 ? arg.slice(eq + 1) : argv[++i];
      if (v === undefined) throw new Error(`${flag} needs a value`);
      return v;
    };
    switch (flag) {
      case '--params': opts.params = value().replace(/^\?/, ''); break;
      case '--size': {
        const m = /^(\d+)x(\d+)$/i.exec(value());
        if (!m) throw new Error('--size needs WxH, for example 960x540');
        opts.width = Number(m[1]);
        opts.height = Number(m[2]);
        break;
      }
      case '--frames': opts.frames = number(flag, value()); break;
      case '--skip': opts.skip = number(flag, value()); break;
      case '--scenario': opts.scenario = value(); break;
      case '--out': opts.out = value(); break;
      case '--timeout': opts.timeout = number(flag, value()); break;
      case '--realtime': opts.realtime = true; break;
      case '--artifact-cdn': opts.artifactCdn = true; break;
      case '--cdn-fail': opts.cdnFail = number(flag, value()); break;
      case '--verbose': opts.verbose = true; break;
      case '--help': case '-h': opts.help = true; break;
      default:
        if (arg.startsWith('--')) throw new Error(`unknown option ${arg}`);
        if (opts.file) throw new Error(`unexpected argument ${arg}`);
        opts.file = arg;
    }
  }
  return opts;
}

const firstLine = (err) => (err && err.message ? err.message.split('\n')[0] : String(err));

/**
 * dist/artifact.html is a page fragment: its host supplies the document around it. Served bare it
 * would run in quirks mode, so wrap it in the same minimal skeleton build.mjs uses for the standalone page.
 */
function asDocument(html) {
  if (/^\s*<!doctype/i.test(html)) return html;
  return (
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n' +
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n' +
    '<style>body{margin:0}[hidden]{display:none!important}</style>\n</head>\n<body>\n' +
    html +
    '</body>\n</html>\n'
  );
}

/** Serves the directory of the page on a free local port. */
function serve(dir) {
  const server = http.createServer((req, res) => {
    const name = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    const file = path.join(dir, path.normalize(name));
    if (!file.startsWith(dir)) {
      res.writeHead(403).end();
      return;
    }
    fs.readFile(file, (err, data) => {
      if (err) {
        res.writeHead(404).end('not found');
        return;
      }
      const ext = path.extname(file);
      res.writeHead(200, { 'content-type': MIME[ext] || 'application/octet-stream', 'cache-control': 'no-store' });
      res.end(ext === '.html' ? asDocument(data.toString('utf8')) : data);
    });
  });
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help || !opts.file) {
    console.log(USAGE);
    process.exitCode = opts.help ? 0 : 1;
    return;
  }
  const file = path.resolve(opts.file);
  if (!fs.existsSync(file)) throw new Error(`${opts.file} does not exist (build it first: node build.mjs --dev --out=${opts.file})`);
  const scenario = opts.scenario ? require(path.resolve(opts.scenario)) : null;
  if (opts.scenario && typeof scenario !== 'function') throw new Error(`${opts.scenario} must export an async function (page, h)`);

  const { chromium } = require('playwright');
  const deadline = Date.now() + opts.timeout * 1000;
  const left = () => Math.max(1000, deadline - Date.now());
  const report = { url: '', shots: [], errors: [], fatal: null, stats: null, harness: [] };

  const server = await serve(path.dirname(file));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const query = new URLSearchParams(opts.params);
  if (!opts.realtime) {
    if (!query.has('step')) query.set('step', '1');
    if (!query.has('dt')) query.set('dt', '0.0333');
  }
  report.url = `${origin}/${encodeURIComponent(path.basename(file))}?${query}`;
  const stepping = query.get('step') === '1';

  let browser = null;
  // Never leave a browser behind, whatever happens.
  const watchdog = setTimeout(() => {
    console.error(`shot.cjs: no result after ${opts.timeout} s, giving up`);
    if (browser) browser.close().catch(() => {});
    process.exit(1);
  }, opts.timeout * 1000 + 15000);
  const stop = async () => {
    clearTimeout(watchdog);
    if (browser) await browser.close().catch(() => {});
    await new Promise((resolve) => server.close(resolve));
  };
  for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, () => stop().then(() => process.exit(1)));

  try {
    browser = await chromium.launch({
      args: [...GL_ARGS, ...memoryArgs(opts.scenario)],
      ...(process.env.SHOT_CHROME ? { executablePath: process.env.SHOT_CHROME } : {}),
    });
    const context = await browser.newContext({ viewport: { width: opts.width, height: opts.height }, deviceScaleFactor: 1 });
    const page = await context.newPage();

    // Offline by construction: only the local server answers, plus the CDN stand-in when asked for.
    await context.route('**/*', (route) => {
      const url = new URL(route.request().url());
      if (url.origin === origin) return route.continue();
      const cdn = CDN_HOSTS.indexOf(url.hostname);
      if (opts.artifactCdn && cdn >= 0 && url.pathname.endsWith('/three.min.js')) {
        if (cdn < opts.cdnFail) return route.abort('failed');
        return route.fulfill({ status: 200, contentType: 'text/javascript', body: fs.readFileSync(THREE_MIN) });
      }
      return route.abort('blockedbyclient');
    });

    page.on('console', (msg) => {
      const type = msg.type();
      // Refused requests (fonts, CDN) are expected offline and are not page errors.
      if (/net::ERR_(BLOCKED_BY_CLIENT|FAILED)/.test(msg.text())) return;
      if (opts.verbose || type === 'error' || type === 'warning') console.error(`[page ${type}] ${msg.text()}`);
    });
    page.on('pageerror', (err) => report.harness.push(`uncaught: ${err.message}`));
    page.on('crash', () => report.harness.push('the page crashed'));

    const h = {
      page,
      async frames(n = 1) {
        if (!(n > 0)) return;
        if (stepping) {
          await page.evaluate((count) => {
            window.__step = (window.__step > 0 ? window.__step : 0) + count;
          }, n);
          await page.waitForFunction(() => !(window.__step > 0), null, { timeout: left() });
        } else {
          const target = (await page.evaluate(() => window.__frames)) + n;
          await page.waitForFunction((t) => window.__frames >= t, target, { timeout: left() });
        }
      },
      async skip(n = 1) {
        if (!(n > 0)) return;
        if (!stepping) return h.frames(n);
        await page.evaluate((count) => {
          window.__skip = (window.__skip > 0 ? window.__skip : 0) + count;
        }, n);
        await page.waitForFunction(() => !(window.__skip > 0), null, { timeout: left() });
      },
      async shot(out) {
        const target = path.resolve(out);
        fs.mkdirSync(path.dirname(target), { recursive: true });
        // Two animation frames so the last drawn frame has reached the screen.
        await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
        await page.screenshot({ path: target, timeout: left() });
        report.shots.push(path.relative(process.cwd(), target));
        return target;
      },
      eval: (fnOrString, arg) => page.evaluate(fnOrString, arg),
      async key(code, down = true) {
        const button = { Mouse0: 'left', Mouse1: 'middle', Mouse2: 'right' }[code];
        if (!button) return down ? page.keyboard.down(code) : page.keyboard.up(code);
        await page.mouse.move(opts.width / 2, opts.height / 2);
        return down ? page.mouse.down({ button }) : page.mouse.up({ button });
      },
      mouse: (dx, dy) =>
        page.evaluate(([x, y]) => {
          const target = document.getElementById('view') || document;
          target.dispatchEvent(new MouseEvent('mousemove', { movementX: x, movementY: y, bubbles: true, cancelable: true }));
        }, [dx, dy]),
      click: (selector) => page.click(selector, { timeout: left() }),
      errors: () => page.evaluate(() => window.__errors || []),
      stats: () => page.evaluate(() => (typeof window.__stats === 'function' ? window.__stats() : null)),
      heap: (collect = false) =>
        page.evaluate((gc) => {
          if (gc && typeof window.gc === 'function') window.gc();
          return performance.memory ? performance.memory.usedJSHeapSize : 0;
        }, collect),
      wait: (ms) => page.waitForTimeout(ms),
    };

    await page.goto(report.url, { waitUntil: 'load', timeout: left() });
    await page.waitForFunction(() => window.__ready === true || !!window.__fatal, null, { timeout: left() }).catch(() => {
      report.harness.push('the page never became ready');
    });

    const ready = await page.evaluate(() => window.__ready === true);
    if (ready) {
      // The boot screen fades out in real time: wait until it is really gone.
      await page.waitForFunction(() => (document.getElementById('boot') || { hidden: true }).hidden, null, { timeout: left() });
      // A failing run is reported, but the page's errors and stats are still collected below.
      try {
        if (opts.skip) await h.skip(opts.skip);
        if (scenario) {
          await scenario(page, h);
        } else {
          await h.frames(opts.frames);
          await h.shot(opts.out);
        }
      } catch (err) {
        report.harness.push(firstLine(err));
      }
    }

    report.errors = await h.errors().catch(() => []);
    report.fatal = await page.evaluate(() => window.__fatal || null).catch(() => null);
    report.stats = await h.stats().catch(() => null);
    if (!ready) {
      // The page did not start: keep what the boot screen says, and a picture of it.
      report.bootLine = await page.evaluate(() => (document.getElementById('boot-msg') || {}).textContent || '').catch(() => '');
      await h.shot(scenario ? path.join('shots', 'not-ready.png') : opts.out).catch(() => {});
    }
  } catch (err) {
    report.harness.push(firstLine(err));
  } finally {
    await stop();
  }

  console.log(JSON.stringify(report, null, 2));
  if (report.errors.length || report.fatal || report.harness.length) process.exitCode = 1;
}

main().catch((err) => {
  console.error(`shot.cjs: ${err.message}`);
  process.exitCode = 1;
});
