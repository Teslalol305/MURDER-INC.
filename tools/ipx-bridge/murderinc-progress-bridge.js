/*
 * MURDER INC. progress bridge for the IPX Game OS page.
 *
 * Keeps the 8-character progress code in the browser (localStorage) and passes it to and from the game that E3DS
 * streams into the page's iframe. No network, no cookies, no personal data: the only thing stored is the code
 * (XXXX-XXXX) and the Hold the Block best scores (integers).
 *
 * Use (see README.md):
 *   <script src="murderinc-progress-bridge.js"></script>
 *   const bridge = MurderIncProgressBridge.attach(frame, { streamOrigin: 'https://your-stream-host' });
 *   ... when you remove the iframe: bridge.detach();      // attach once per iframe; detach before attaching again
 *
 * Stored progress only ever goes up: every message from the game, and every restore, is merged into what is stored
 * (progression.md 4.5), never written over it.
 *
 * Pure functions (checkCode, encodeCode, mergeProgress, validateProgress, isE3dsOrigin, extractProgress) are exported
 * for the node tests.
 */
(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) { module.exports = api; }
  else { root.MurderIncProgressBridge = api; }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var STORAGE_KEY = 'murderinc.progress.v1';
  var ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
  var CODE_RE = /^[0-9A-HJKMNP-TV-Z]{4}-?[0-9A-HJKMNP-TV-Z]{4}$/;
  var SALT = 'MURDERINC-PROGRESS-1';
  var MAX_PAYLOAD_CHARS = 256;       // the game's own limit for the progress message
  var MAX_RAW_CHARS = 4096;          // a string from the stream is not even parsed above this
  var MAX_HOLD = 99999999;
  var HOLD_KEYS = ['block', 'chinatown', 'midtown'];
  var E3DS_HOST_RE = /(^|\.)eagle3dstreaming\.com$/;
  var OPEN_EVENTS = ['bidirectionalChannelBetweenUnrealAndIframeReady', 'stream.channelOpen'];
  // The open event's name is not proven for every E3DS player (README, "Check once"): the moment the stream plays also
  // starts the (idempotent, merging) restore, so a wrong open-event name costs a few seconds, not the restore.
  var PLAY_EVENTS = ['stage5_playBtnPressed', 'stream.playing'];
  var RETRY_MS = [1500, 4000, 9000];   // resend until the game's answer shows it has merged the page's value
  var OPEN_WARN_MS = 30000;            // no open event this long after attach: say so on the console

  // ---- progress code (progression.md 4.3, format v1) ----------------------------------------------------------

  function crc16(bytes) {
    var crc = 0xFFFF;
    for (var i = 0; i < bytes.length; i++) {
      crc ^= bytes[i] << 8;
      for (var b = 0; b < 8; b++) {
        crc = (crc & 0x8000) ? ((crc << 1) ^ 0x1021) & 0xFFFF : (crc << 1) & 0xFFFF;
      }
    }
    return crc;
  }

  // Returns the canonical 'XXXX-XXXX' or null. Full check: format, CRC, version, reserved bits and the rules of
  // 4.3 (cleared bits agree with points/difficulty, cleared levels form a prefix, album needs all three).
  function checkCode(input) {
    if (typeof input !== 'string' || input.length > 9 || !CODE_RE.test(input)) { return null; }
    var s = input.replace('-', '');
    var hi = 0, lo = 0;                        // 40 bits as two numbers: top 24 (payload), low 16 (check)
    var bits = 0, acc = 0, vals = [];
    for (var i = 0; i < 8; i++) { vals.push(ALPHABET.indexOf(s[i])); }
    var big = 0;
    for (var j = 0; j < 8; j++) { big = big * 32 + vals[j]; }   // < 2^40, exact in a double
    hi = Math.floor(big / 65536);
    lo = big % 65536;
    var bytes = [];
    for (var k = 0; k < SALT.length; k++) { bytes.push(SALT.charCodeAt(k)); }
    bytes.push((hi >> 16) & 255, (hi >> 8) & 255, hi & 255);
    if (crc16(bytes) !== lo) { return null; }
    if (((hi >> 21) & 7) !== 1 || ((hi >> 19) & 3) !== 0) { return null; }
    var mask = (hi >> 16) & 7;
    var prevCleared = true, all = true;
    for (var L = 0; L < 3; L++) {
      var cleared = ((mask >> L) & 1) === 1;
      var pts = (hi >> (7 + 3 * L)) & 7;
      var diff = (hi >> (1 + 2 * L)) & 3;
      if (pts === 6) { return null; }
      if (cleared !== (pts !== 7) || cleared !== (diff !== 3)) { return null; }
      if (cleared && !prevCleared) { return null; }
      prevCleared = cleared;
      all = all && cleared;
    }
    if ((hi & 1) === 1 && !all) { return null; }
    return s.slice(0, 4) + '-' + s.slice(4);
  }

  // The 24-bit payload of a checked code (null for an invalid one).
  function payloadOf(code) {
    var c = checkCode(code);
    if (!c) { return null; }
    var s = c.replace('-', '');
    var big = 0;
    for (var j = 0; j < 8; j++) { big = big * 32 + ALPHABET.indexOf(s[j]); }
    return Math.floor(big / 65536);
  }

  // A 24-bit payload -> the canonical code (adds the check). Used only by mergeProgress.
  function encodeCode(payload) {
    var bytes = [];
    for (var k = 0; k < SALT.length; k++) { bytes.push(SALT.charCodeAt(k)); }
    bytes.push((payload >> 16) & 255, (payload >> 8) & 255, payload & 255);
    var big = payload * 65536 + crc16(bytes);
    var out = '';
    for (var i = 7; i >= 0; i--) { out += ALPHABET[Math.floor(big / Math.pow(32, i)) % 32]; }
    return out.slice(0, 4) + '-' + out.slice(4);
  }

  // The merge of 4.5, commutative, idempotent and never lower: a level is cleared if either is, its best rating is the
  // higher of (points, difficulty), the album is seen if either saw it, and each Hold best is the larger.
  function mergeProgress(a, b) {
    var pa = payloadOf(a.code), pb = payloadOf(b.code);
    if (pa === null || pb === null) { return null; }
    var mask = (((pa >> 16) & 7) | ((pb >> 16) & 7));
    var pts = 0, diff = 0;
    for (var L = 0; L < 3; L++) {
      var ap = (pa >> (7 + 3 * L)) & 7, bp = (pb >> (7 + 3 * L)) & 7;
      var ad = (pa >> (1 + 2 * L)) & 3, bd = (pb >> (1 + 2 * L)) & 3;
      var aNone = ap === 7, bNone = bp === 7;
      var p, d;
      if (aNone && bNone) { p = 7; d = 3; }
      else if (aNone) { p = bp; d = bd; }
      else if (bNone) { p = ap; d = ad; }
      else if (ap > bp || (ap === bp && ad >= bd)) { p = ap; d = ad; }
      else { p = bp; d = bd; }
      pts |= p << (7 + 3 * L);
      diff |= d << (1 + 2 * L);
    }
    var album = ((pa & 1) | (pb & 1));
    var payload = (1 << 21) | (mask << 16) | pts | diff | album;
    var hold = {};
    for (var i = 0; i < HOLD_KEYS.length; i++) {
      var k = HOLD_KEYS[i];
      hold[k] = Math.max(a.hold[k] || 0, b.hold[k] || 0);
    }
    return validateProgress({ mi: 'progress', v: 1, code: encodeCode(payload), hold: hold });
  }

  function sameProgress(a, b) {
    if (!a || !b || a.code !== b.code) { return false; }
    for (var i = 0; i < HOLD_KEYS.length; i++) { if (a.hold[HOLD_KEYS[i]] !== b.hold[HOLD_KEYS[i]]) { return false; } }
    return true;
  }

  function isHold(v) { return typeof v === 'number' && isFinite(v) && Math.floor(v) === v && v >= 0 && v <= MAX_HOLD; }

  // A progress object {mi:'progress', v:1, code, hold:{block,chinatown,midtown}} -> a clean copy, or null.
  // Unknown fields are dropped; a missing hold is allowed (zeros).
  function validateProgress(obj) {
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) { return null; }
    if (obj.mi !== 'progress' || obj.v !== 1) { return null; }
    var code = checkCode(obj.code);
    if (!code) { return null; }
    var hold = {};
    var src = obj.hold;
    if (src !== undefined && src !== null && (typeof src !== 'object' || Array.isArray(src))) { return null; }
    for (var i = 0; i < HOLD_KEYS.length; i++) {
      var v = src ? src[HOLD_KEYS[i]] : 0;
      if (v === undefined) { v = 0; }
      if (!isHold(v)) { return null; }
      hold[HOLD_KEYS[i]] = v;
    }
    return { mi: 'progress', v: 1, code: code, hold: hold };
  }

  // ---- messages ------------------------------------------------------------------------------------------------

  function isE3dsOrigin(origin) {
    if (typeof origin !== 'string') { return false; }
    var u;
    try { u = new URL(origin); } catch (e) { return false; }
    return u.protocol === 'https:' && E3DS_HOST_RE.test(u.hostname);
  }

  function parseMaybeJson(v, limit) {
    if (typeof v !== 'string') { return v; }
    if (v.length > limit) { return undefined; }
    try { return JSON.parse(v); } catch (e) { return undefined; }
  }

  function eventName(d) {
    if (!d || typeof d !== 'object') { return ''; }
    var n = d.type || d.event || d.cmd || d.name || d.eventName;
    return typeof n === 'string' ? n : '';
  }

  // Finds a valid progress payload in a message from the stream. E3DS's relay envelope for a game response is read
  // from its live player (README, "Check once"): until then the payload is looked for in the usual places of the
  // envelope, and only a payload that passes validateProgress is ever used.
  function extractProgress(data) {
    var d = parseMaybeJson(data, MAX_RAW_CHARS);
    if (d === undefined || d === null) { return null; }
    var direct = validateProgress(d);
    if (direct) { return direct; }
    if (typeof d !== 'object' || Array.isArray(d)) { return null; }
    var keys = ['value', 'data', 'message', 'payload', 'descriptor', 'response'];
    for (var i = 0; i < keys.length; i++) {
      var c = d[keys[i]];
      if (c === undefined) { continue; }
      if (typeof c === 'string' && c.length > MAX_PAYLOAD_CHARS) { continue; }
      c = parseMaybeJson(c, MAX_PAYLOAD_CHARS);
      var p = validateProgress(c);
      if (p) { return p; }
    }
    return null;
  }

  // What goes to the game: E3DS's player passes {cmd:'sendToUe4', value} on as a UIInteraction descriptor.
  function buildOutgoing(progress) {
    return JSON.stringify({ cmd: 'sendToUe4', value: progress });
  }

  // ---- storage -------------------------------------------------------------------------------------------------

  function makeStore(storage) {
    function get() {
      try {
        var raw = storage.getItem(STORAGE_KEY);
        if (typeof raw !== 'string' || raw.length > MAX_PAYLOAD_CHARS) { return null; }
        return validateProgress(JSON.parse(raw));
      } catch (e) { return null; }
    }
    function set(p) {
      try { storage.setItem(STORAGE_KEY, JSON.stringify(p)); return true; } catch (e) { return false; }
    }
    return { get: get, set: set };
  }

  // ---- the bridge ----------------------------------------------------------------------------------------------

  // opts: { win, storage, streamOrigin, wrapperOrigin, onSaved(progress), onLog(text), onWarn(text), setTimeout }
  //   streamOrigin: the exact origin of the stream (e.g. 'https://xxxx.eagle3dstreaming.com', from MURDERINC_STREAM_URL).
  //   Strongly recommended: with it, only that origin is heard and written to; without it, any https *.eagle3dstreaming.com.
  //   wrapperOrigin: only when the game page is itself inside the Game OS page and the Game OS page forwards each E3DS
  //   message as {source:'e3ds', data}: that wrapper is accepted from this origin only (PREFLIGHT.md section 4). Never
  //   the page's own origin (a same-origin script could then pose as the game).
  function attach(frame, opts) {
    opts = opts || {};
    if (!frame || typeof frame !== 'object') { throw new TypeError('MurderIncProgressBridge.attach needs the E3DS iframe element'); }
    var win = opts.win || (typeof window !== 'undefined' ? window : null);
    var storage = opts.storage;
    if (!storage) { try { storage = win.localStorage; } catch (e) { storage = null; } }
    var store = storage ? makeStore(storage) : { get: function () { return null; }, set: function () { return false; } };
    var log = typeof opts.onLog === 'function' ? opts.onLog : function () {};
    var warn = typeof opts.onWarn === 'function' ? opts.onWarn : function (t) { try { console.warn('[murderinc] ' + t); } catch (e) {} };
    var later = typeof opts.setTimeout === 'function' ? opts.setTimeout : function (f, ms) { return win.setTimeout(f, ms); };
    var streamOrigin = isE3dsOrigin(opts.streamOrigin) ? new URL(opts.streamOrigin).origin : null;
    if (opts.streamOrigin && !streamOrigin) { throw new TypeError('streamOrigin must be an https eagle3dstreaming.com origin'); }
    var targetOrigin = null;      // the verified origin of the stream, the only target of a postMessage
    var detached = false;
    var generation = 0;           // a new open event starts a new restore; older retries stop
    var acked = true;
    var openSeen = false;
    var resends = 0;

    function frameOrigin() {
      try { var u = new URL(frame.src); return isE3dsOrigin(u.origin) ? u.origin : null; } catch (e) { return null; }
    }

    function onMessage(ev) {
      if (detached || !ev) { return; }
      var data = ev.data;
      var fromWrapper = false;
      if (opts.wrapperOrigin && ev.origin === opts.wrapperOrigin) {
        if (!data || typeof data !== 'object' || data.source !== 'e3ds') { return; }
        data = data.data;
        fromWrapper = true;
      } else {
        if (!isE3dsOrigin(ev.origin)) { return; }
        if (streamOrigin && ev.origin !== streamOrigin) { return; }
        // The source must be the iframe's own window. A missing or detached frame hears nothing.
        if (!frame.contentWindow || ev.source !== frame.contentWindow) { return; }
      }
      var obj = parseMaybeJson(data, MAX_RAW_CHARS);
      var name = eventName(obj);
      var isOpen = name && OPEN_EVENTS.indexOf(name) >= 0;
      var isPlay = name && PLAY_EVENTS.indexOf(name) >= 0;
      if (isOpen || isPlay) {
        if (!fromWrapper) { targetOrigin = streamOrigin || ev.origin; }
        if (isOpen) { openSeen = true; log('channel open event ' + name); }
        beginRestore();
        return;
      }
      var p = extractProgress(obj);
      if (p) { receive(p); }
    }

    // A message from the game: merged into what is stored (never written over it). The game has acknowledged the
    // page's value only when its answer already holds everything stored; a lower answer (a fresh game's hello that
    // crossed the page's value) is not an acknowledgment and is answered with the merged value.
    function receive(p) {
      var stored = store.get();
      var merged = stored ? mergeProgress(stored, p) : p;
      if (!merged) { return; }
      if (!sameProgress(merged, stored) && store.set(merged)) {
        log('progress saved ' + merged.code);
        if (typeof opts.onSaved === 'function') { try { opts.onSaved(merged); } catch (e) {} }
      }
      if (sameProgress(merged, p)) { acked = true; }
      else if (resends < 6) { resends++; sendStored(); }   // the game is behind the page: tell it again
    }

    function beginRestore() {
      generation++;
      acked = false;
      resends = 0;
      var mine = generation;
      sendStored();
      for (var i = 0; i < RETRY_MS.length; i++) {
        later(function () { if (!detached && mine === generation && !acked) { sendStored(); } }, RETRY_MS[i]);
      }
    }

    function sendStored() {
      var p = store.get();
      if (!p) { acked = true; return false; }   // nothing stored: the game sends its own first value
      var origin = targetOrigin || streamOrigin || frameOrigin();
      if (!origin) { warn('no verified stream origin: progress not sent'); return false; }
      if (!frame.contentWindow) { return false; }
      try { frame.contentWindow.postMessage(buildOutgoing(p), origin); } catch (e) { return false; }
      log('progress sent ' + p.code);
      return true;
    }

    win.addEventListener('message', onMessage);
    later(function () {
      if (!detached && !openSeen) { warn('no data-channel open event 30 s after attach: the saved progress has not been restored (README, Check once)'); }
    }, OPEN_WARN_MS);
    return {
      detach: function () { detached = true; generation++; win.removeEventListener('message', onMessage); },
      current: function () { return store.get(); },
      // "Forget my progress": removes the stored code and bests from this browser.
      clear: function () { try { storage.removeItem(STORAGE_KEY); } catch (e) {} }
    };
  }

  return {
    STORAGE_KEY: STORAGE_KEY,
    attach: attach,
    checkCode: checkCode,
    encodeCode: encodeCode,
    mergeProgress: mergeProgress,
    validateProgress: validateProgress,
    isE3dsOrigin: isE3dsOrigin,
    extractProgress: extractProgress,
    buildOutgoing: buildOutgoing,
    makeStore: makeStore,
    crc16: crc16
  };
});
