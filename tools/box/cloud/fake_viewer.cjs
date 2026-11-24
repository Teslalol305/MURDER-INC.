// A fake Pixel Streaming viewer for e3ds-repro.sh: it joins the signalling server on 127.0.0.1:8090 the way the
// web frontend does (listStreamers, subscribe), answers nothing (no WebRTC), stays <on> seconds, leaves, waits <off>
// seconds, and repeats <cycles> times. Enough to drive the game's "viewer joined" and "all viewers left" paths
// (UMICloudSubsystem::OnViewerJoined / OnAllViewersLeft) without a browser.
//   node fake_viewer.cjs <on>,<off>,<cycles> [startDelaySecs]
const WebSocket = require('/project/ue/cloud/infra/node_modules/ws');
const [on, off, cycles] = (process.argv[2] || '20,10,3').split(',').map(Number);
const delay = Number(process.argv[3] || 30);
const log = (...a) => console.log(new Date().toISOString(), ...a);
const sleep = (s) => new Promise((r) => setTimeout(r, s * 1000));

async function once(i) {
  return new Promise((resolve) => {
    const ws = new WebSocket('ws://127.0.0.1:8090');
    let timer;
    ws.on('open', () => { log(`cycle ${i}: open`); ws.send(JSON.stringify({ type: 'listStreamers' })); });
    ws.on('message', (m) => {
      let msg; try { msg = JSON.parse(m.toString()); } catch { return; }
      log(`cycle ${i}: <- ${msg.type}${msg.ids ? ' ' + JSON.stringify(msg.ids) : ''}`);
      if (msg.type === 'streamerList') {
        if (msg.ids && msg.ids.length) ws.send(JSON.stringify({ type: 'subscribe', streamerId: msg.ids[0] }));
        else log(`cycle ${i}: no streamer`);
        timer = setTimeout(() => { log(`cycle ${i}: leaving`); ws.close(); }, on * 1000);
      }
    });
    ws.on('close', () => { clearTimeout(timer); log(`cycle ${i}: closed`); resolve(); });
    ws.on('error', (e) => { log(`cycle ${i}: error ${e.message}`); });
  });
}

(async () => {
  await sleep(delay);
  for (let i = 1; i <= cycles; i++) { await once(i); await sleep(off); }
  log('done');
})();
