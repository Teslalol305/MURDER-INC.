/*
 * MURDER INC. progress bridge for the IPX Game OS page.
 *
 * Keeps the 8-character progress code in the browser (localStorage) and passes it to and from the game that E3DS
 * streams into the page's iframe. No network, no cookies, no personal data: the only thing stored is the code
 * (XXXX-XXXX) and the Hold the Block best scores (integers).
 *
 * Use (see README.md):
 *   <script src="murderinc-progress-bridge.js"></script>
 *   const bridge = MurderIncProgressBridge.attach(frame);   // frame = the E3DS iframe element, right after you create it
 *   ... when you remove the iframe: bridge.detach();
 *
 * Pure functions (checkCode, validateProgress, isE3dsOrigin, extractProgress) are exported for the node tests.
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

  // opts: { win, storage, wrapperOrigin, onSaved(progress), onLog(text) }
  //   wrapperOrigin: only when the game page is itself inside the Game OS page and the Game OS page forwards each E3DS
  //   message as {source:'e3ds', data}: that wrapper is accepted from this origin only (PREFLIGHT.md section 4).
  function attach(frame, opts) {
    opts = opts || {};
    var win = opts.win || (typeof window !== 'undefined' ? window : null);
    var storage = opts.storage;
    if (!storage) { try { storage = win.localStorage; } catch (e) { storage = null; } }
    var store = storage ? makeStore(storage) : { get: function () { return null; }, set: function () { return false; } };
    var log = typeof opts.onLog === 'function' ? opts.onLog : function () {};
    var sentThisFrame = false;
    var detached = false;

    function onMessage(ev) {
      if (detached || !ev) { return; }
      var data = ev.data;
      if (opts.wrapperOrigin && ev.origin === opts.wrapperOrigin) {
        if (!data || typeof data !== 'object' || data.source !== 'e3ds') { return; }
        data = data.data;
      } else {
        if (!isE3dsOrigin(ev.origin)) { return; }
        if (frame && frame.contentWindow && ev.source !== frame.contentWindow) { return; }
      }
      var obj = parseMaybeJson(data, MAX_RAW_CHARS);
      var name = eventName(obj);
      if (name && OPEN_EVENTS.indexOf(name) >= 0) { sendStored(); return; }
      var p = extractProgress(obj);
      if (p) {
        if (store.set(p)) {
          log('progress saved ' + p.code);
          if (typeof opts.onSaved === 'function') { try { opts.onSaved(p); } catch (e) {} }
        }
      }
    }

    function sendStored() {
      if (sentThisFrame || !frame || !frame.contentWindow) { return false; }
      var p = store.get();
      if (!p) { sentThisFrame = true; return false; }     // nothing stored: the game sends its own first value
      sentThisFrame = true;
      frame.contentWindow.postMessage(buildOutgoing(p), '*');   // E3DS reads a JSON string; the frame's origin is E3DS's
      log('progress sent ' + p.code);
      return true;
    }

    win.addEventListener('message', onMessage);
    return {
      detach: function () { detached = true; win.removeEventListener('message', onMessage); },
      current: function () { return store.get(); },
      clear: function () { try { storage.removeItem(STORAGE_KEY); } catch (e) {} }
    };
  }

  return {
    STORAGE_KEY: STORAGE_KEY,
    attach: attach,
    checkCode: checkCode,
    validateProgress: validateProgress,
    isE3dsOrigin: isE3dsOrigin,
    extractProgress: extractProgress,
    buildOutgoing: buildOutgoing,
    makeStore: makeStore,
    crc16: crc16
  };
});
