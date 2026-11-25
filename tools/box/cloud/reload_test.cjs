// A real browser (headless Chromium) joins a streamed game, reloads its page again and again, and leaves: how long a
// reload takes to bring the first picture, and what the game logged meanwhile (release 3c: the session; the 20 seconds
// of MI.Cloud.ExitAfterEmpty have to be longer than a reload takes, docs/LAUNCH.md section 13).
//   node reload_test.cjs <out> <game.log> [reloads=5] [seconds to wait before the browser joins=0]
// Run through stream-test.sh (the signalling server and the game are started there):
//   STREAM_BUILD=<test folder> STREAM_KEEPALIVE=0 bash stream-test.sh start Shipping
//   bash stream-test.sh reload <out> 5 15
// Writes <out>/results.json:
//   join              the first join: seconds from the page's load to its first video frame (the game was idle if the wait
//                     before it was longer than the game's start-up grace and its idle time: see "Nobody is watching")
//   reload_seconds    for every reload (page.reload()): seconds from the call to the first video frame of the new page
//   game_gaps         from the game's own log: for every "Connection lost" the seconds until the next "Viewer joined" (game
//                     time, so the clock is the game's)
//   left              the page is closed: the time (the browser's clock, seconds since the first frame) of the last viewer's
//                     leaving; the game's "Session over" line comes 20 s later (game time in the line)
const { chromium } = require('/project/ue/cloud/pw/node_modules/playwright');
const fs = require('fs');
const [, , OUT, GAMELOG, NRELOADS = '5', WAIT0 = '0'] = process.argv;
const R = {};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const note = (k, v) => { R[k] = v; console.log(k, JSON.stringify(v)); fs.writeFileSync(`${OUT}/results.json`, JSON.stringify(R, null, 1)); };
const log = () => { try { return fs.readFileSync(GAMELOG, 'utf8'); } catch (e) { return ''; } };
async function waitFor(fn, ms, step = 100) { const t = Date.now(); while (Date.now() - t < ms) { const v = await fn(); if (v) return v; await sleep(step); } return null; }

function gameGaps() {
  // "Connection lost ... (game time 70.2 s, ...)" then the next "Viewer joined ... (game time 74.9 s, ...)".
  const lines = log().split('\n');
  const gaps = [];
  let lost = null;
  for (const l of lines) {
    const m = /game time ([\d.]+) s/.exec(l);
    if (!m) continue;
    if (l.includes('Connection lost')) lost = +m[1];
    else if (l.includes('Viewer joined') && lost !== null) { gaps.push(+(+m[1] - lost).toFixed(1)); lost = null; }
  }
  return gaps;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  await sleep(+WAIT0 * 1000);
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--disable-features=WebRtcHideLocalIpsWithMdns'] });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const page = await ctx.newPage();
  page.on('console', (m) => fs.appendFileSync(`${OUT}/console.log`, m.text() + '\n'));
  const url = 'http://127.0.0.1:8090/?AutoConnect=true&AutoPlayVideo=true&HoveringMouse=false&MatchViewportRes=false&StartVideoMuted=true&WaitForStreamer=true';
  const firstFrame = () => waitFor(() => page.evaluate(() => {
    const v = document.querySelector('video'); return v && v.readyState >= 2 && v.videoWidth > 0 ? [v.videoWidth, v.videoHeight] : null;
  }), 120000, 100);
  const t0 = Date.now();
  await page.goto(url);
  const size = await firstFrame();
  note('join', { ok: !!size, video: size, seconds: +((Date.now() - t0) / 1000).toFixed(2), waited_before_joining: +WAIT0 });
  if (!size) { await browser.close(); return; }
  const begin = Date.now();
  await sleep(6000);
  const times = [];
  for (let i = 0; i < +NRELOADS; i++) {
    const t = Date.now();
    await page.reload();
    const s = await firstFrame();
    times.push(s ? +((Date.now() - t) / 1000).toFixed(2) : null);
    await sleep(3000);
  }
  note('reload_seconds', { each: times, max: Math.max(...times.filter((x) => x !== null)), all_ok: times.every((x) => x !== null) });
  await page.close();
  note('left', { seconds_after_first_frame: +((Date.now() - begin) / 1000).toFixed(1) });
  await browser.close();
  // The game's own side, after a moment: the countdown after the last viewer is 20 s, so the log is read again later.
  await sleep(2000);
  note('game_gaps', { seconds: gameGaps(), joins: log().split('Viewer joined').length - 1, lost: log().split('Connection lost').length - 1 });
  fs.writeFileSync(`${OUT}/done`, '1');
})().catch((e) => { note('error', String(e && e.stack || e)); process.exit(1); });
