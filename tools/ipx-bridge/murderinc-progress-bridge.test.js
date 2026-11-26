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
  return { setTimeout: () => 0, addEventListener: (t, f) => l.push(f), removeEventListener: (t, f) => l.splice(l.indexOf(f), 1), fire: (ev) => l.slice().forEach((f) => f(ev)), count: () => l.length };
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

function fakeTimers() {
  const q = [];
  return { setTimeout: (f, ms) => q.push({ f, ms, done: false }), run: (upTo) => q.forEach((t) => { if (!t.done && t.ms <= upTo) { t.done = true; t.f(); } }), q };
}

test('restores on channel open, to the verified origin only, again on a second open', () => {
  const win = fakeWin(), frame = fakeFrame(), st = fakeStore(JSON.stringify(msg())), tm = fakeTimers();
  B.attach(frame, { win, storage: st, setTimeout: tm.setTimeout });
  win.fire({ origin: E, source: frame.contentWindow, data: { type: 'stage1_inqueued' } });
  assert.equal(frame.sent.length, 0);
  win.fire({ origin: E, source: frame.contentWindow, data: { type: 'bidirectionalChannelBetweenUnrealAndIframeReady' } });
  assert.equal(frame.sent.length, 1);
  assert.equal(frame.sent[0][1], E);                       // never '*'
  assert.deepEqual(JSON.parse(frame.sent[0][0]), { cmd: 'sendToUe4', value: msg() });
  win.fire({ origin: E, source: frame.contentWindow, data: { type: 'stream.channelOpen' } });   // reconnect: sent again
  assert.equal(frame.sent.length, 2);
});

test('the playing event also starts the restore (the open event name may never arrive)', () => {
  const win = fakeWin(), frame = fakeFrame(), tm = fakeTimers();
  B.attach(frame, { win, storage: fakeStore(JSON.stringify(msg())), setTimeout: tm.setTimeout });
  win.fire({ origin: E, source: frame.contentWindow, data: { type: 'stage5_playBtnPressed' } });
  assert.equal(frame.sent.length, 1);
});

test('resends until the game answers with a value that holds the stored one; a lower hello is not an answer', () => {
  const win = fakeWin(), frame = fakeFrame(), st = fakeStore(JSON.stringify(msg())), tm = fakeTimers();
  B.attach(frame, { win, storage: st, setTimeout: tm.setTimeout });
  win.fire({ origin: E, source: frame.contentWindow, data: { type: 'stream.channelOpen' } });
  assert.equal(frame.sent.length, 1);
  tm.run(1500);                                            // no answer: resent
  assert.equal(frame.sent.length, 2);
  const lower = { mi: 'progress', v: 1, code: '47YZ-MB30', hold: { block: 0, chinatown: 0, midtown: 0 } };
  win.fire({ origin: E, source: frame.contentWindow, data: lower });
  assert.equal(JSON.parse(st.getItem(B.STORAGE_KEY)).code, '4FMY-N7W6');   // stored value kept
  assert.equal(frame.sent.length, 3);                      // and the game is told again
  win.fire({ origin: E, source: frame.contentWindow, data: msg() });       // answer that holds it: done
  tm.run(99999);
  assert.equal(frame.sent.length, 3);
});

test('warns when no open event arrives', () => {
  const win = fakeWin(), frame = fakeFrame(), tm = fakeTimers(), w = [];
  B.attach(frame, { win, storage: fakeStore(), setTimeout: tm.setTimeout, onWarn: (t) => w.push(t) });
  tm.run(30000);
  assert.equal(w.length, 1);
  const w2 = [], win2 = fakeWin(), tm2 = fakeTimers();
  B.attach(frame, { win: win2, storage: fakeStore(), setTimeout: tm2.setTimeout, onWarn: (t) => w2.push(t) });
  win2.fire({ origin: E, source: frame.contentWindow, data: { type: 'stream.channelOpen' } });
  tm2.run(30000);
  assert.equal(w2.length, 0);
});

test('no frame, or a frame without a window: attach throws / nothing is heard', () => {
  const win = fakeWin();
  assert.throws(() => B.attach(undefined, { win, storage: fakeStore() }));
  const st = fakeStore(), frame = { contentWindow: null };
  B.attach(frame, { win, storage: st });
  win.fire({ origin: E, source: undefined, data: msg() });
  win.fire({ origin: E, source: null, data: msg() });
  assert.equal(st.m.size, 0);
});

test('streamOrigin pins the host, and is itself checked', () => {
  const win = fakeWin(), frame = fakeFrame(), st = fakeStore();
  B.attach(frame, { win, storage: st, streamOrigin: 'https://abc.eagle3dstreaming.com' });
  win.fire({ origin: 'https://other.eagle3dstreaming.com', source: frame.contentWindow, data: msg() });
  assert.equal(st.m.size, 0);
  win.fire({ origin: 'https://abc.eagle3dstreaming.com', source: frame.contentWindow, data: msg() });
  assert.equal(st.m.size, 1);
  assert.throws(() => B.attach(frame, { win, storage: fakeStore(), streamOrigin: 'https://evil.com' }));
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
  win.fire({ origin: E, source: frame.contentWindow, data: msg() });          // an older value never lowers it
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

test('encodeCode round-trips the documented codes', () => {
  for (const c of GOOD) {
    const hi = parseInt(B.checkCode(c) && c.replace('-', '').split('').reduce((a, ch) => a * 32n + BigInt('0123456789ABCDEFGHJKMNPQRSTVWXYZ'.indexOf(ch)), 0n) >> 16n, 10);
    assert.equal(B.encodeCode(Number(BigInt(hi))), c);
  }
});

const P = (code, hold) => ({ mi: 'progress', v: 1, code, hold: Object.assign({ block: 0, chinatown: 0, midtown: 0 }, hold) });

test('mergeProgress: superset of cleared, better rating, larger holds, commutative, idempotent, never lower', () => {
  const a = P('47YZ-MB30', { block: 500 }), b = P('4FMY-N7W6', { block: 100, chinatown: 7 }), c = P('4Y4W-PZ1F', {});
  const ab = B.mergeProgress(a, b);
  assert.deepEqual(ab.hold, { block: 500, chinatown: 7, midtown: 0 });
  assert.deepEqual(B.mergeProgress(b, a), ab);
  assert.deepEqual(B.mergeProgress(ab, ab), ab);
  assert.equal(B.mergeProgress(ab, c).code, '4Y4W-PZ1F');
  assert.equal(B.mergeProgress(c, a).code, '4Y4W-PZ1F');
  assert.equal(B.mergeProgress(a, a).code, '47YZ-MB30');
  assert.equal(B.mergeProgress(P('4FMY-N7W6', {}), P('47YZ-MB30', {})).code, '4FMY-N7W6');
  // every pair of the documented codes merges into a valid code that is at least each of them
  for (const x of GOOD) for (const y of GOOD) {
    const m = B.mergeProgress(P(x, {}), P(y, {}));
    assert.ok(m, x + y);
    assert.equal(B.mergeProgress(m, P(x, {})).code, m.code);
    assert.equal(B.mergeProgress(m, P(y, {})).code, m.code);
  }
});

test('two tabs: a lower code from a stale tab cannot downgrade the stored progress', () => {
  const st = fakeStore(JSON.stringify(P('4FMY-N7W6', { block: 900 })));
  const winB = fakeWin(), frameB = fakeFrame();
  B.attach(frameB, { win: winB, storage: st });
  winB.fire({ origin: E, source: frameB.contentWindow, data: P('47YZ-MB30', { block: 10 }) });
  const now = JSON.parse(st.getItem(B.STORAGE_KEY));
  assert.equal(now.code, '4FMY-N7W6');
  assert.equal(now.hold.block, 900);
});
