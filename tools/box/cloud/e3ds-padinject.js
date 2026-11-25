// A simulated DualSense in E3DS's own player page, for owner-browser.sh (Firefox under Marionette on the box).
// The script runs in the PAGE's world (a script element), so the stream page's gamepad code sees a standard-mapping pad:
// it reads navigator.getGamepads() every frame and sends what changed to the game, exactly as for a real pad. The page
// must have a stream (see vid.js); then:  ff eval e3ds-padinject.js ; ff eval e3ds-padcon.js ; ff eval e3ds-padseq.js '[...]'
// Buttons by standard index: 0 Cross, 1 Circle, 2 Square, 3 Triangle, 4 L1, 5 R1, 6 L2, 7 R2, 8 Create, 9 Options, 10 L3,
// 11 R3, 12 up, 13 down, 14 left, 15 right. Axes: 0 left X, 1 left Y (up is -1), 2 right X, 3 right Y.
const code = `
if (!window.__pad) {
  const mk = () => ({id: '054c-0ce6-Wireless Controller (STANDARD GAMEPAD Vendor: 054c Product: 0ce6)', index: 0, connected: true, mapping: 'standard',
    timestamp: performance.now(), axes: [0, 0, 0, 0], buttons: Array.from({length: 18}, () => ({pressed: false, touched: false, value: 0})), hapticActuators: []});
  const st = {pad: mk()};
  navigator.getGamepads = () => { st.pad.timestamp = performance.now(); return [st.pad, null, null, null]; };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  window.__pad = {
    st,
    connect() { const e = new Event('gamepadconnected'); e.gamepad = st.pad; window.dispatchEvent(e); return 'connected'; },
    set(i, v) { const b = st.pad.buttons[i]; b.value = v; b.pressed = v > 0.5; b.touched = v > 0; },
    async tap(i, ms) { this.set(i, 1); await sleep(ms || 120); this.set(i, 0); },
    async hold(i, ms, v) { this.set(i, v || 1); await sleep(ms); this.set(i, 0); },
    async stick(ax, ms) { st.pad.axes = ax.slice(); await sleep(ms); st.pad.axes = [0, 0, 0, 0]; },
    async seq(steps) { for (const s of steps) { if (s[0] === 'tap') await this.tap(s[1], s[2]); else if (s[0] === 'hold') await this.hold(s[1], s[2], s[3]); else if (s[0] === 'stick') await this.stick(s[1], s[2]); else if (s[0] === 'wait') await sleep(s[1]); } return 'done'; }
  };
}
`;
const s = document.createElement('script'); s.textContent = code; (document.head || document.documentElement).appendChild(s); s.remove();
return typeof window.wrappedJSObject !== 'undefined' ? ('injected; page sees __pad: ' + (typeof window.wrappedJSObject.__pad)) : 'injected (no wrappedJSObject)';
