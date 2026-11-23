// The browser half of stream-test.sh: Epic's Pixel Streaming 2 player page opened by a headless Chromium on the box.
// Writes <out>/results.json and screenshots. Reads the game's cloud log (-MICloudLog=, -MICloudProbe=0.5) for what
// the game saw: the view's yaw, the game state, whether the click card is up.
//   node stream_test.cjs <out> <cloud.log> <launch.txt>      (VW, VH: browser viewport; MATCH: MatchViewportRes)
const { chromium } = require('/project/ue/cloud/pw/node_modules/playwright');
const fs = require('fs');
const [, , OUT, GAMELOG, LAUNCHFILE] = process.argv;
const VW = +(process.env.VW || 1920), VH = +(process.env.VH || 1080), MATCH = process.env.MATCH || 'false';
const R = {};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const note = (k, v) => { R[k] = v; console.log(k, JSON.stringify(v)); fs.writeFileSync(`${OUT}/results.json`, JSON.stringify(R, null, 1)); };
const log = () => { try { return fs.readFileSync(GAMELOG, 'utf8'); } catch (e) { return ''; } };
const probes = () => log().split('\n').filter((l) => l.includes('MICloudProbe')).map((l) => {
  const o = {}; for (const m of l.matchAll(/(\w+)=(-?[\d.]+)/g)) o[m[1]] = +m[2]; return o;
});
const last = () => { const p = probes(); return p[p.length - 1] || {}; };
const count = (s) => log().split(s).length - 1;
async function waitFor(fn, ms, step = 250) { const t = Date.now(); while (Date.now() - t < ms) { const v = await fn(); if (v) return v; await sleep(step); } return null; }
const waitState = (s, ms) => waitFor(() => last().state === s, ms);
const yawAfter = async () => { const n = probes().length; await waitFor(() => probes().length >= n + 2, 5000, 100); return last().yaw; };
const wrap = (d) => ((d + 540) % 360) - 180;

// A fake standard gamepad (the frontend polls navigator.getGamepads) and a log of every peer connection.
function init() {
  const b = () => ({ pressed: false, touched: false, value: 0 });
  window.__pad = { id: 'Xbox Wireless Controller (STANDARD GAMEPAD)', index: 0, connected: true, mapping: 'standard',
    timestamp: performance.now(), axes: [0, 0, 0, 0], buttons: Array.from({ length: 17 }, b) };
  navigator.getGamepads = () => [window.__pad, null, null, null];
  window.GamepadEvent = class extends Event { constructor(t, i) { super(t); this.gamepad = i && i.gamepad; } };
  const PC = window.RTCPeerConnection; window.__pcs = [];
  window.RTCPeerConnection = function (...a) { const pc = new PC(...a); window.__pcs.push(pc); return pc; };
  window.RTCPeerConnection.prototype = PC.prototype;
}
const pad = (page, f) => page.evaluate(f);
async function padButton(page, i) {
  await page.evaluate((i) => { const p = window.__pad; p.buttons[i] = { pressed: true, touched: true, value: 1 }; p.timestamp = performance.now(); }, i);
  await sleep(250);
  await page.evaluate((i) => { const p = window.__pad; p.buttons[i] = { pressed: false, touched: false, value: 0 }; p.timestamp = performance.now(); }, i);
}
// Mouse movement as the browser reports it under pointer lock (movementX in screen pixels / mouse counts).
const moveBy = (page, dx, dy) => page.evaluate(([dx, dy]) => document.dispatchEvent(new MouseEvent('mousemove', { movementX: dx, movementY: dy, bubbles: true })), [dx, dy]);
const shot = (page, n) => page.screenshot({ path: `${OUT}/${n}.png` });

(async () => {
  const launch = +fs.readFileSync(LAUNCHFILE, 'utf8');
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--disable-features=WebRtcHideLocalIpsWithMdns'] });
  const ctx = await browser.newContext({ viewport: { width: VW, height: VH } });
  let page = await ctx.newPage();
  page.on('console', (m) => fs.appendFileSync(`${OUT}/console.log`, m.text() + '\n'));
  await page.addInitScript(init);
  const url = `http://127.0.0.1:8090/?AutoConnect=true&AutoPlayVideo=true&HoveringMouse=false&MatchViewportRes=${MATCH}&StartVideoMuted=false&WaitForStreamer=true&GamepadInput=true&KeyboardInput=true&MouseInput=true`;
  const firstFrame = async () => waitFor(() => page.evaluate(() => {
    const v = document.querySelector('video'); return v && v.readyState >= 2 && v.videoWidth > 0 ? [v.videoWidth, v.videoHeight] : null;
  }), 240000, 250);
  await page.goto(url);
  const size = await firstFrame();
  note('first_frame', { ok: !!size, video: size, seconds_after_game_launch: +((Date.now() / 1000 - launch).toFixed(1)) });
  if (!size) { await shot(page, 'fail'); await browser.close(); return; }
  await sleep(3000);
  note('click_card_up_before_click', last().click === 1);
  await shot(page, '01-click-to-play');

  // The first click: the frontend may take one to start playback (autoplay with sound needs a gesture).
  let clicks = 0;
  while (clicks < 3 && count('Click to play: dismissed') === 0) { await page.mouse.click(VW / 2, VH / 2); clicks++; await sleep(1500); }
  const locked = await page.evaluate(() => !!document.pointerLockElement);
  note('click_to_play', { dismissed: count('Click to play: dismissed') > 0, clicks_needed: clicks, pointer_locked: locked });
  if (!locked) {
    // Headless Chromium may refuse pointer lock: pretend it is locked so the frontend's locked-mouse path runs.
    await page.evaluate(() => { const el = document.querySelector('video').parentElement;
      Object.defineProperty(document, 'pointerLockElement', { get: () => el, configurable: true });
      document.dispatchEvent(new Event('pointerlockchange')); });
  }
  note('audio_before_play', await audio(page));

  // The set-up flow: Enter on Home (keyboard), then Start on the pad through Crew, Loadout, Block, Briefing.
  await page.keyboard.press('Enter'); await sleep(1500); await shot(page, '02-after-enter');
  const states = [];
  for (let i = 0; i < 8 && last().state !== 2; i++) {
    await padButton(page, 9); await sleep(1800); states.push(last().state);
    if (i === 1) await shot(page, '03-setup');
  }
  const playing = await waitState(2, 60000);
  note('setup_flow', { reached_playing: !!playing, states_after_each_start: states, gamepad_start_presses: states.length });
  await sleep(4000);
  await shot(page, '04-playing');

  // Mouse look: counts in, degrees out (local play: 100 counts = 12.03 degrees at sensitivity 1).
  const look = [];
  for (const dx of [200, -200, 400]) {
    const y0 = await yawAfter(); await moveBy(page, dx, 0); const y1 = await yawAfter();
    look.push({ counts: dx, degrees: +wrap(y1 - y0).toFixed(3), deg_per_count: +(wrap(y1 - y0) / dx).toFixed(5) });
  }
  note('mouse_look', { viewport: [VW, VH], match_viewport_res: MATCH, local_deg_per_count: 0.1203, trials: look });

  // Gamepad look: right stick full right for one second.
  { const y0 = await yawAfter();
    await pad(page, () => { window.__pad.axes[2] = 1; window.__pad.timestamp = performance.now(); }); await sleep(1000);
    await pad(page, () => { window.__pad.axes[2] = 0; window.__pad.timestamp = performance.now(); });
    const y1 = await yawAfter(); note('gamepad_look', { degrees: +wrap(y1 - y0).toFixed(2) }); }

  // Keyboard: W walks (not measured), fire makes sound, P pauses and resumes.
  await page.keyboard.down('w'); await sleep(800); await page.keyboard.up('w');
  for (let i = 0; i < 3; i++) { await page.mouse.down(); await sleep(120); await page.mouse.up(); await sleep(300); }
  await sleep(1000);
  note('audio_in_play', await audio(page));
  await page.keyboard.press('p'); const paused = await waitState(3, 4000);
  await sleep(800); await shot(page, '05-paused');
  await sleep(1200); await page.keyboard.press('p'); const resumed = await waitState(2, 4000);
  note('pause_key_p', { paused: !!paused, resumed: !!resumed });

  // Input to picture: a fast turn, timed from the input event to the first video frame that changed.
  const lat = [];
  for (let i = 0; i < 10; i++) { lat.push(await latency(page, i % 2 ? -300 : 300)); await sleep(400); }
  const ms = lat.filter((x) => x && x.ms).map((x) => x.ms).sort((a, b) => a - b);
  note('input_to_picture_ms', { trials: lat, median: ms[Math.floor(ms.length / 2)], min: ms[0], max: ms[ms.length - 1] });
  note('frontend_latency_test', await page.evaluate(() => new Promise((res) => {
    const ps = window.pixelStreaming; if (!ps || !ps.requestLatencyTest) return res(null);
    const t = setTimeout(() => res('timeout'), 8000);
    ps.addEventListener('latencyTestResult', (e) => { clearTimeout(t); const d = e.data.latencyTimings; res({ e2e: d.EndToEndLatency, browserReceiptToComposite: d.BrowserReceiptToComposite, ue: d.UEReceiptToTransmit || d.UECaptureToSend }); });
    ps.requestLatencyTest(); })));
  note('video_stats', await page.evaluate(async () => { const out = {}; for (const pc of window.__pcs) { (await pc.getStats()).forEach((r) => {
    if (r.type === 'inbound-rtp' && r.kind === 'video') Object.assign(out, { fps: r.framesPerSecond, decoded: r.framesDecoded, dropped: r.framesDropped, w: r.frameWidth, h: r.frameHeight, codec: r.codecId, jitterBufferMs: r.jitterBufferEmittedCount ? 1000 * r.jitterBufferDelay / r.jitterBufferEmittedCount : null });
    if (r.type === 'codec' && /video/.test(r.mimeType)) out.mime = r.mimeType; }); } return out; }));

  // Connection lost: the viewer leaves; the game pauses. A new viewer gets the click card again.
  const lost0 = count('Connection lost'), join0 = count('Viewer joined');
  await page.close(); await sleep(4000);
  note('viewer_left', { game_logged_connection_lost: count('Connection lost') > lost0, state: last().state });
  page = await ctx.newPage(); await page.addInitScript(init); await page.goto(url); await firstFrame(); await sleep(3000);
  note('viewer_rejoined', { game_logged_viewer_joined: count('Viewer joined') > join0, click_card_up: last().click === 1 });
  await shot(page, '06-rejoined');
  fs.writeFileSync(`${OUT}/done`, '1');
  await browser.close();
})().catch((e) => { note('error', String(e && e.stack || e)); process.exit(1); });

async function audio(page) {
  return page.evaluate(async () => {
    const media = [...document.querySelectorAll('video,audio')];
    const tracks = media.reduce((n, m) => n + (m.srcObject ? m.srcObject.getAudioTracks().length : 0), 0);
    const out = { audio_tracks: tracks, muted: media.map((m) => m.muted), paused: media.map((m) => m.paused) };
    for (const pc of window.__pcs) (await pc.getStats()).forEach((r) => {
      if (r.type === 'inbound-rtp' && r.kind === 'audio') Object.assign(out, { packets: r.packetsReceived, energy: r.totalAudioEnergy, level: r.audioLevel, samples: r.totalSamplesReceived });
    });
    return out;
  });
}

async function latency(page, dx) {
  return page.evaluate(async (dx) => {
    const v = document.querySelector('video');
    const c = document.createElement('canvas'); c.width = 96; c.height = 54; const g = c.getContext('2d', { willReadFrequently: true });
    const sample = () => { g.drawImage(v, 0, 0, 96, 54); return g.getImageData(0, 0, 96, 54).data; };
    const diff = (a, b) => { let s = 0; for (let i = 0; i < a.length; i += 4) s += Math.abs(a[i] - b[i]) + Math.abs(a[i + 1] - b[i + 1]) + Math.abs(a[i + 2] - b[i + 2]); return s / (a.length / 4); };
    const frame = () => new Promise((r) => v.requestVideoFrameCallback((now) => r(now)));
    await frame(); let prev = sample(); let noise = 0;
    for (let i = 0; i < 12; i++) { await frame(); const s = sample(); noise = Math.max(noise, diff(prev, s)); prev = s; }
    const t0 = performance.now();
    document.dispatchEvent(new MouseEvent('mousemove', { movementX: dx, movementY: 0, bubbles: true }));
    for (let i = 0; i < 90; i++) {
      const now = await frame(); const s = sample(); const d = diff(prev, s); prev = s;
      if (d > Math.max(3 * noise, 6)) return { ms: Math.round(now - t0), noise: +noise.toFixed(1), change: +d.toFixed(1) };
    }
    return { ms: null, noise };
  }, dx);
}
