// Tell the page a pad was connected (the stream page starts reading pads on this event).
const s = document.createElement('script'); s.textContent = 'window.__padRes = window.__pad ? window.__pad.connect() : "no pad";'; (document.head || document.documentElement).appendChild(s); s.remove();
return 'asked';
