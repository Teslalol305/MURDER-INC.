// What the viewer's page receives as sound: the level of the stream's audio track, sampled for N seconds (default 4).
// Run it in the page of a stream session with the browser tool: owner-browser.sh ff eval e3ds-snd.js '[4]'
// Answers "no media element with a stream" (the picture has not started), "stream has no audio track" (the game sends
// no sound: version 4), or a JSON line: rms and peak (0 to 1) and the share of 50 ms windows that were silent.
const vs = [...document.querySelectorAll('video, audio')].filter(v => v.srcObject);
if (!vs.length) return 'no media element with a stream';
const tracks = vs.flatMap(v => v.srcObject.getAudioTracks());
if (!tracks.length) return 'stream has no audio track';
const ctx = new (window.AudioContext || window.webkitAudioContext)();
const an = ctx.createAnalyser(); an.fftSize = 2048;
ctx.createMediaStreamSource(new MediaStream([tracks[0]])).connect(an);
const buf = new Float32Array(an.fftSize);
const secs = (arguments[0] && arguments[0][0]) || 4;
return new Promise(res => {
  const t0 = performance.now(); let n = 0, sumsq = 0, peak = 0, silent = 0;
  const iv = setInterval(() => {
    an.getFloatTimeDomainData(buf); let s = 0, p = 0;
    for (const x of buf) { s += x * x; if (Math.abs(x) > p) p = Math.abs(x); }
    const rms = Math.sqrt(s / buf.length); n++; sumsq += rms * rms; if (p > peak) peak = p; if (rms < 1e-4) silent++;
    if (performance.now() - t0 > secs * 1000) {
      clearInterval(iv); const st = ctx.state; ctx.close();
      res(JSON.stringify({tracks: tracks.length, enabled: tracks[0].enabled, muted: tracks[0].muted, state: tracks[0].readyState,
        rms: +Math.sqrt(sumsq / n).toFixed(5), peak: +peak.toFixed(3), silentFrac: +(silent / n).toFixed(2), samples: n, ctx: st}));
    }
  }, 50);
});
