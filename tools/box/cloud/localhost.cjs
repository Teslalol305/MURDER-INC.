// Preloaded into the signalling server (node --require): every listening socket binds to 127.0.0.1 only, so the
// web page, the player websocket and the streamer websocket are reachable from the box itself and nowhere else
// (the rental forbids extra public servers; stream-test.sh checks the binds with ss).
const net = require('net');
const listen = net.Server.prototype.listen;
net.Server.prototype.listen = function (...a) {
  if (typeof a[0] === 'number' || (typeof a[0] === 'string' && /^\d+$/.test(a[0]))) {
    if (typeof a[1] === 'string') a[1] = '127.0.0.1';
    else a.splice(1, 0, '127.0.0.1');
  } else if (a[0] && typeof a[0] === 'object' && 'port' in a[0]) {
    a[0] = Object.assign({}, a[0], { host: '127.0.0.1' });
  }
  return listen.apply(this, a);
};
