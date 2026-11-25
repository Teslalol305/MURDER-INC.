// Run a sequence on the page's simulated pad (after e3ds-padinject.js and e3ds-padcon.js):
//   owner-browser.sh ff eval e3ds-padseq.js '[["tap",9,150],["wait",800],["stick",[0,0,1,0],1000]]'
// Steps: ["tap",button,ms] ["hold",button,ms,value] ["stick",[lx,ly,rx,ry],ms] ["wait",ms]. It returns at once; the
// sequence runs in the page (window.__padDone becomes true at its end).
const steps = JSON.stringify(arguments[0] || []);
const code = `window.__padDone = false; window.__pad.seq(${steps}).then(() => { window.__padDone = true; });`;
const s = document.createElement('script'); s.textContent = code; (document.head || document.documentElement).appendChild(s); s.remove();
return 'started';
