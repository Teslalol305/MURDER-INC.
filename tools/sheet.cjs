#!/usr/bin/env node
// Contact sheet: every PNG named on the command line (or every PNG of one folder) on one captioned
// page, saved as a single picture. For looking over a run's screenshots in one go.
//
//   node tools/sheet.cjs shots/story --out shots/story/sheet.png --cols 3 --width 1600
//   node tools/sheet.cjs shots/weapon/a.png shots/weapon/b.png --out shots/weapon/ab.png --cols 2
//
// SHOT_CHROME=/path/to/chrome runs that browser instead of the one Playwright downloaded for itself.

'use strict';

const fs = require('node:fs');
const path = require('node:path');

async function main() {
  const args = process.argv.slice(2);
  const files = [];
  let out = 'shots/sheet.png';
  let cols = 3;
  let width = 1500;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--out') out = args[++i];
    else if (args[i] === '--cols') cols = Number(args[++i]);
    else if (args[i] === '--width') width = Number(args[++i]);
    else files.push(args[i]);
  }
  const list = [];
  for (const f of files) {
    if (fs.statSync(f).isDirectory()) {
      for (const name of fs.readdirSync(f).sort()) if (/\.png$/i.test(name) && path.resolve(f, name) !== path.resolve(out)) list.push(path.join(f, name));
    } else list.push(f);
  }
  if (!list.length) throw new Error('no pictures');
  const cells = list
    .map((f) => `<figure><img src="data:image/png;base64,${fs.readFileSync(f).toString('base64')}"><figcaption>${path.basename(f, '.png')}</figcaption></figure>`)
    .join('');
  const { chromium } = require('playwright');
  const browser = await chromium.launch(process.env.SHOT_CHROME ? { executablePath: process.env.SHOT_CHROME } : {});
  const page = await browser.newPage({ viewport: { width, height: 800 } });
  await page.setContent(
    `<style>body{margin:0;background:#111;display:grid;grid-template-columns:repeat(${cols},1fr);gap:4px;padding:4px}` +
      'figure{margin:0;position:relative}img{width:100%;display:block}' +
      'figcaption{position:absolute;left:0;top:0;background:#000c;color:#ffd84a;font:700 14px/1.4 monospace;padding:1px 7px}</style>' +
      cells,
  );
  fs.mkdirSync(path.dirname(out), { recursive: true });
  // A short sheet is cut to its pictures rather than padded out to the window's height.
  await page.evaluate(() => Promise.all(Array.from(document.images, (img) => img.decode().catch(() => {}))));
  const height = await page.evaluate(() => Math.ceil(Math.max(...Array.from(document.images, (img) => img.getBoundingClientRect().bottom)) + 4));
  if (height > 0 && height < 800) await page.setViewportSize({ width, height });
  await page.screenshot({ path: out, fullPage: true });
  await browser.close();
  console.log(`${out}: ${list.length} pictures`);
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
