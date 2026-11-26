'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const B = require('./murderinc-progress-bridge.js');

const GOOD = ['47YZ-MB30', '4FMY-N7W6', '4Y4W-PZ1F', '4FG6-05EW', '4W00-1D88'];

test('documented codes validate', () => {
  for (const c of GOOD) { assert.equal(B.checkCode(c), c); assert.equal(B.checkCode(c.replace('-', '')), c); }
});

test('every single-character change of a valid code is refused', () => {
  const A = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
  for (const c of GOOD) {
    const s = c.replace('-', '');
    for (let i = 0; i < 8; i++) for (const ch of A) {
      if (ch === s[i]) continue;
      const t = s.slice(0, i) + ch + s.slice(i + 1);
      assert.equal(B.checkCode(t), null, t);
    }
  }
});

test('bad formats', () => {
  for (const v of [null, undefined, 5, {}, '', '47YZ', '47YZ-MB3', '47YZ-MB300', 'I7YZ-MB30', '47yz-mb30', '47YZ_MB30', '47YZ-MB30\n', ' 47YZ-MB30', '4FMY--N7W6'])
    assert.equal(B.checkCode(v), null, String(v));
});

const msg = (extra) => Object.assign({ mi: 'progress', v: 1, code: '4FMY-N7W6', hold: { block: 12345, chinatown: 0, midtown: 0 } }, extra);

test('validateProgress', () => {
  assert.deepEqual(B.validateProgress(msg()), msg());
  assert.deepEqual(B.validateProgress(msg({ code: '4FMYN7W6', evil: 'x' })), msg());
  assert.equal(B.validateProgress(msg({ v: 2 })), null);
  assert.equal(B.validateProgress(msg({ mi: 'other' })), null);
  assert.equal(B.validateProgress(msg({ code: '4FMY-N7W7' })), null);
  assert.equal(B.validateProgress(msg({ hold: { block: -1, chinatown: 0, midtown: 0 } })), null);
  assert.equal(B.validateProgress(msg({ hold: { block: 1.5, chinatown: 0, midtown: 0 } })), null);
  assert.equal(B.validateProgress(msg({ hold: { block: 100000000, chinatown: 0, midtown: 0 } })), null);
  assert.equal(B.validateProgress(msg({ hold: { block: '5', chinatown: 0, midtown: 0 } })), null);
  assert.equal(B.validateProgress(msg({ hold: [1, 2, 3] })), null);
  assert.equal(B.validateProgress([]), null);
  assert.equal(B.validateProgress('x'), null);
  assert.deepEqual(B.validateProgress({ mi: 'progress', v: 1, code: '47YZ-MB30' }).hold, { block: 0, chinatown: 0, midtown: 0 });
});

test('origins', () => {
  assert.ok(B.isE3dsOrigin('https://player.eagle3dstreaming.com'));
  assert.ok(B.isE3dsOrigin('https://eagle3dstreaming.com'));
  for (const o of ['http://player.eagle3dstreaming.com', 'https://eagle3dstreaming.com.evil.com', 'https://evileagle3dstreaming.com',
    'https://evil.com/eagle3dstreaming.com', 'null', '', null, undefined, 'https://eagle3dstreaming.com@evil.com'])
    assert.equal(B.isE3dsOrigin(o), false, String(o));
});

test('extractProgress from envelopes, strings, and junk', () => {
  const p = msg();
  assert.deepEqual(B.extractProgress(p), p);
  assert.deepEqual(B.extractProgress(JSON.stringify(p)), p);
  assert.deepEqual(B.extractProgress({ type: 'x', value: p }), p);
  assert.deepEqual(B.extractProgress({ type: 'x', data: JSON.stringify(p) }), p);
  assert.equal(B.extractProgress({ type: 'x', value: 'hello' }), null);
  assert.equal(B.extractProgress('not json'), null);
  assert.equal(B.extractProgress('x'.repeat(5000)), null);
  assert.equal(B.extractProgress({ value: JSON.stringify(msg({ pad: 'x'.repeat(300) })) }), null);
  assert.equal(B.extractProgress(null), null);
  assert.equal(B.extractProgress(42), null);
});

function fakeWin() {
  const l = [];
  return { addEventListener: (t, f) => l.push(f), removeEventListener: (t, f) => l.splice(l.indexOf(f), 1), fire: (ev) => l.slice().forEach((f) => f(ev)), count: () => l.length };
}
function fakeStore(init) {
  const m = new Map(init ? [[B.STORAGE_KEY, init]] : []);
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, v), removeItem: (k) => m.delete(k), m };
}
function fakeFrame() {
  const sent = [];
  const cw = { postMessage: (m, o) => sent.push([m, o]) };
  return { contentWindow: cw, sent };
}
const E = 'https://player.eagle3dstreaming.com';

test('restores on channel open, once, to the frame', () => {
  const win = fakeWin(), frame = fakeFrame(), st = fakeStore(JSON.stringify(msg()));
  B.attach(frame, { win, storage: st });
  win.fire({ origin: E, source: frame.contentWindow, data: { type: 'stage5_playBtnPressed' } });
  assert.equal(frame.sent.length, 0);
  win.fire({ origin: E, source: frame.contentWindow, data: { type: 'bidirectionalChannelBetweenUnrealAndIframeReady' } });
  win.fire({ origin: E, source: frame.contentWindow, data: { type: 'stream.channelOpen' } });
  assert.equal(frame.sent.length, 1);
  assert.deepEqual(JSON.parse(frame.sent[0][0]), { cmd: 'sendToUe4', value: msg() });
});

test('nothing stored: sends nothing; corrupt storage is ignored', () => {
  for (const init of [null, '{bad', JSON.stringify(msg({ code: '4FMY-N7W7' })), 'x'.repeat(1000)]) {
    const win = fakeWin(), frame = fakeFrame();
    B.attach(frame, { win, storage: fakeStore(init) });
    win.fire({ origin: E, source: frame.contentWindow, data: { type: 'stream.channelOpen' } });
    assert.equal(frame.sent.length, 0);
  }
});

test('stores the game message; refuses foreign origin, foreign source, bad data', () => {
  const win = fakeWin(), frame = fakeFrame(), st = fakeStore();
  let saved = 0;
  B.attach(frame, { win, storage: st, onSaved: () => saved++ });
  win.fire({ origin: 'https://evil.com', source: frame.contentWindow, data: msg() });
  win.fire({ origin: E, source: {}, data: msg() });
  win.fire({ origin: E, source: frame.contentWindow, data: msg({ code: 'AAAA-AAAA' }) });
  assert.equal(st.m.size, 0);
  win.fire({ origin: E, source: frame.contentWindow, data: { type: 'response', value: JSON.stringify(msg()) } });
  assert.equal(saved, 1);
  assert.deepEqual(JSON.parse(st.getItem(B.STORAGE_KEY)), msg());
  const newer = msg({ code: '4Y4W-PZ1F' });
  win.fire({ origin: E, source: frame.contentWindow, data: newer });
  assert.equal(JSON.parse(st.getItem(B.STORAGE_KEY)).code, '4Y4W-PZ1F');
});

test('wrapper accepted only from the Game OS origin', () => {
  const win = fakeWin(), frame = fakeFrame(), st = fakeStore();
  B.attach(frame, { win, storage: st, wrapperOrigin: 'https://gameos.example' });
  win.fire({ origin: 'https://other.example', data: { source: 'e3ds', data: msg() } });
  assert.equal(st.m.size, 0);
  win.fire({ origin: 'https://gameos.example', data: msg() });          // unwrapped from the wrapper origin
  assert.equal(st.m.size, 0);
  win.fire({ origin: 'https://gameos.example', data: { source: 'e3ds', data: msg() } });
  assert.equal(st.m.size, 1);
});

test('storage that throws, and detach', () => {
  const win = fakeWin(), frame = fakeFrame();
  const bad = { getItem() { throw new Error('x'); }, setItem() { throw new Error('x'); }, removeItem() { throw new Error('x'); } };
  const b = B.attach(frame, { win, storage: bad });
  win.fire({ origin: E, source: frame.contentWindow, data: msg() });
  win.fire({ origin: E, source: frame.contentWindow, data: { type: 'stream.channelOpen' } });
  assert.equal(frame.sent.length, 0);
  assert.equal(b.current(), null);
  b.detach();
  assert.equal(win.count(), 0);
});
