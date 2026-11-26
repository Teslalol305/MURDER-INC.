# IPX page bridge: a returning player continues automatically

`murderinc-progress-bridge.js` is the small script the IPX Game OS page adds to the page that embeds the E3DS stream
(design: `docs/unreal/maps/progression.md` 4.3 to 4.5). It keeps the 8-character progress code (`XXXX-XXXX`) and the
Hold the Block bests in the visitor's browser (`localStorage["murderinc.progress.v1"]`), gives them to the game when the
stream's data channel opens, and stores whatever the game sends back. The script itself makes no network calls, sets no
cookies and has no account. See "Privacy and the owner's duties" below: the code does travel to and from the game inside
the E3DS stream.

## Where to paste it

1. Serve the file next to the MURDER INC. page (or paste its content in a `<script>` on that page).
2. Create the iframe in the Play click as `docs/unreal/PREFLIGHT.md` section 3 says, then attach the bridge to it:

```html
<script src="/murderinc-progress-bridge.js"></script>
<script>
  // in the Play click handler, right after you create the iframe (before or after setting src):
  const bridge = MurderIncProgressBridge.attach(frame, { streamOrigin: 'https://YOUR-STREAM-HOST.eagle3dstreaming.com' });
  // when you remove the iframe (Quit, end screen, hidden tab): bridge.detach();
</script>
```

If the game page is itself inside the Game OS page and the Game OS page forwards each E3DS message as
`{source: 'e3ds', data: <message>}` (PREFLIGHT.md section 1), pass the Game OS page's own origin:
`attach(frame, { wrapperOrigin: 'https://your-game-os-origin' })`. Never use `'*'` here. Options also take `onSaved(progress)`
and `onLog(text)` (console only, for testing).

Rules for the call:

- **Once per iframe.** `attach` throws without a frame element. Call `detach()` before attaching to a new iframe; a second
  `attach` without `detach` adds a second listener and sends the value twice.
- **`streamOrigin`** (the origin of `MURDERINC_STREAM_URL`) pins both the messages it hears and the only target it writes
  to. Without it, any `https://*.eagle3dstreaming.com` origin is accepted (still only from this iframe's own window).
- **`wrapperOrigin`** is the Game OS page's origin and must **not** be the page's own origin (any same-origin script could
  then pose as the game).
- **Serve the file from the page's own origin**, not from a CDN you do not control: it runs with full access to the page.

It does not replace your own E3DS message handler: it adds one more `message` listener that ignores everything it does
not need.

## What it does and refuses

- Listens only to messages whose origin is `https://*.eagle3dstreaming.com` (HTTPS, hostname checked after URL parsing:
  `eagle3dstreaming.com.evil.com` fails, or exactly `streamOrigin` when given) and whose source is that iframe's own
  window. A missing or detached frame (`contentWindow` null) hears nothing.
- On every `bidirectionalChannelBetweenUnrealAndIframeReady` / `stream.channelOpen` (and, because that name is not
  proven for every E3DS player, also on `stage5_playBtnPressed` / `stream.playing`) it sends the stored value as
  `JSON.stringify({cmd: 'sendToUe4', value: {mi, v, code, hold}})` to the frame (E3DS passes `value` on to the game as a
  UIInteraction message), with the stream's verified origin as `postMessage` target, never `'*'`. It resends at 1.5, 4
  and 9 s until the game answers with a value that already holds the stored one. A game that answers with less (a fresh
  game's hello that crossed the page's value) is not an acknowledgment and is told again, at most 6 times.
- **It never lowers stored progress.** Every message from the game is merged into what is stored (progression.md 4.5:
  cleared levels are a union, the better rating wins, the album is seen if either saw it, each Hold best is the larger),
  so a second tab, a stale tab or a fresh game's hello cannot downgrade a player.
- With no open event 30 s after `attach` it writes a console warning (`[murderinc] no data-channel open event ...`): the
  restore did not happen; see "Check once".
- It stores a message from the game only when `mi === "progress"`, `v === 1`, the code has the exact format **and the
  right check** (the same CRC and rules as the game: a wrong or invented code is never stored), and each `hold` value is
  an integer from 0 to 99,999,999. Strings above 4,096 characters are not parsed, payloads above 256 characters are
  ignored, unknown fields are dropped.
- Every storage access is in try/catch: in a private window there is simply no bridge, and the game works as before
  (the typed progress code is always the fallback).

## Test it

Unit tests (no browser, no E3DS): `node --test tools/ipx-bridge/murderinc-progress-bridge.test.js` (19 tests: the five
documented codes, every one-character change refused, field and size limits, origins, restore and retries, the merge,
two tabs, the 30 s warning, store, wrapper, throwing storage).

On the site, after the game build with the game-side half (`docs/unreal/patches/maps-progress-bridge/`) is on E3DS:

1. Play with the console open. Add `onLog: console.info` in `attach` to see `progress sent` / `progress saved`.
2. Finish Level 1. The console shows `progress saved 47YZ-MB30`-style lines (a different code is fine) and
   `localStorage["murderinc.progress.v1"]` holds a JSON with the same code.
3. Quit, press Play again: the new session starts with Level 2 open and `progress sent <code>` in the console.
4. In the console, `localStorage.removeItem("murderinc.progress.v1")` and play again: the game starts at Level 1 (a
   code typed into the Progress drawer still works).

## Check once (this is the part not proven yet)

Both E3DS envelopes are unproven: no E3DS session was spent and the docs host was not reachable from the session that
wrote this. Known from E3DS's live player (`docs/unreal/SMOOTH.md` B5): a page command `{cmd: 'sendToUe4', value}`
reaches the game as `emitUIInteraction(value)`. **Not known**: the event E3DS's page sends up when the game answers
with a Pixel Streaming `Response` message. The bridge therefore looks for a valid progress object in the message
itself or in its `value`, `data`, `message`, `payload`, `descriptor` or `response` field, as an object or a JSON string,
and rejects everything else, so a different envelope costs nothing but a missed save. In the first test session:
set `onLog`, play to the end of a level, and in the browser console log every `message` event from E3DS once. If the
game's answer comes under another field name, add that name to the `keys` list in `extractProgress` (one line) and
re-run the tests. If E3DS never relays game responses at all, the page can still restore (page to game works) and the
progress code on the debrief remains the way to save.

Also confirm in that session which open event name arrives (`onLog` prints `channel open event <name>`); if none does,
the warning appears and the restore relies on the playing event.

## Privacy and the owner's duties

- **What is stored and sent.** In the visitor's browser: the 8-character progress code and three Hold the Block bests
  (`localStorage["murderinc.progress.v1"]`), kept until the visitor clears it. The code is a stable per-browser
  identifier. It also travels to the game and back inside the E3DS stream, so E3DS (a third party) carries it. It names
  no one, but say so: **add a line to the site's privacy notice** (progress is saved in your browser and passed to the
  game through the streaming provider; clear it with "Forget my progress").
- **Forgetting.** `bridge.clear()` removes it. Put a "Forget my progress" button on the page that calls it. A private
  window keeps nothing past the window; localStorage is per origin, so `www` versus bare domain, or staging versus
  production, each has its own save (the typed progress code works anywhere).
- **The code is a checksum, not a secret.** The salt and the CRC are in this public file and in the game, so anyone can
  compute a valid code for all levels and the album, and Hold bests are taken at face value. This is accepted
  (progression.md 4.3: single-player convenience; levels are not monetised) and recorded in `docs/unreal/DECISIONS.md`.
  **No leaderboard, prize or ranking may ever read the Hold values, the album bit or the code from this path.**
