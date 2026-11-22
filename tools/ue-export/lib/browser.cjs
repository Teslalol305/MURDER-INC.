'use strict';

// Boots a built page of the game in headless Chromium for the exporter: the same recipe as
// tools/shot.cjs (software WebGL, a local server, every other request refused, `step=1` so the
// simulation only moves when asked), plus the capture hooks installed before the game's own script.

const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { installHooks, MODULES } = require('./hooks.cjs');

const GL_ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];

/** Serves one directory on a free local port. */
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
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' });
      res.end(data);
    });
  });
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

/**
 * Opens `file` with `params` (an object) and waits until the game has drawn its second frame.
 * @returns {Promise<{page, close: () => Promise<void>, skip: (steps: number) => Promise<void>, bootMs: number}>}
 */
async function openGame(file, params, { timeout = 300, verbose = false, width = 640, height = 360 } = {}) {
  const { chromium } = require('playwright');
  const server = await serve(path.dirname(file));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const query = new URLSearchParams({ step: '1', dt: '0.0333', ...params });
  const url = `${origin}/${encodeURIComponent(path.basename(file))}?${query}`;
  const browser = await chromium.launch({ args: GL_ARGS });
  const close = async () => {
    await browser.close().catch(() => {});
    await new Promise((resolve) => server.close(resolve));
  };
  try {
    const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1 });
    // Offline by construction, like the harness: only the local server answers.
    await context.route('**/*', (route) => (new URL(route.request().url()).origin === origin ? route.continue() : route.abort('blockedbyclient')));
    const page = await context.newPage();
    const pageErrors = [];
    page.on('console', (msg) => {
      if (/net::ERR_(BLOCKED_BY_CLIENT|FAILED)/.test(msg.text())) return;
      if (verbose || msg.type() === 'error') console.error(`[page ${msg.type()}] ${msg.text()}`);
    });
    page.on('pageerror', (err) => pageErrors.push(err.message));
    page.on('crash', () => pageErrors.push('the page crashed'));
    await page.addInitScript(installHooks, MODULES);

    const t0 = Date.now();
    await page.goto(url, { waitUntil: 'load', timeout: timeout * 1000 });
    await page.waitForFunction(() => window.__ready === true || !!window.__fatal, null, { timeout: timeout * 1000 });
    const state = await page.evaluate(() => ({ fatal: window.__fatal || null, errors: (window.__errors || []).slice(), hooked: !!window.__ue && window.__ue.order.length }));
    if (state.fatal) throw new Error(`the game did not start: ${state.fatal}`);
    if (state.errors.length || pageErrors.length) throw new Error(`the page reported errors while booting:\n  ${[...state.errors, ...pageErrors].join('\n  ')}`);
    if (!state.hooked) throw new Error('the capture hooks did not see the game boot (window.__G was not assigned before the modules were created)');

    /** Advances the simulation `steps` fixed steps without drawing. */
    const skip = async (steps) => {
      if (!(steps > 0)) return;
      await page.evaluate((n) => {
        window.__skip = (window.__skip > 0 ? window.__skip : 0) + n;
      }, steps);
      await page.waitForFunction(() => !(window.__skip > 0), null, { timeout: timeout * 1000 });
    };
    return { page, close, skip, bootMs: Date.now() - t0, url, pageErrors };
  } catch (err) {
    await close();
    throw err;
  }
}

module.exports = { openGame };
