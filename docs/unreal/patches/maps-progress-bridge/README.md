# maps-progress-bridge: the game's half of the IPX page bridge, unbuilt

The page half is `tools/ipx-bridge/` (read its README for the message and the checks). Design:
`docs/unreal/maps/progression.md` 4.3 to 4.5. **Not built and not run** (no Unreal and no GPU box when written; the
release in progress must not change). It lands on the maps branch with the progress store, and is built there.

```
git apply docs/unreal/patches/maps-progress-bridge/000*.patch     # on the maps branch only
```

| Patch | What |
|---|---|
| `0001-MICloud-hooks.patch` | Two lines in `Cloud/MICloud.cpp`: the existing `UIInteraction` handler (the one that reads the away word) first offers the message to `FMIProgressBridge::OnPageMessage`; and a viewer joining schedules the hello (below). Nothing else changes: the plugin's own handler still runs first, the console allowlist is not touched |
| `0002-MIProgressBridge.patch` | New `Cloud/MIProgressBridge.{h,cpp}`: `CheckCode` (format v1: CRC-16/CCITT-FALSE over the salt and payload, version, reserved bits, per-level rules), `ParseDescriptor` / `ParseUIBytes` (strict: at most 256 UTF-16 units, `mi`, `v`, a checked code, `hold` integers 0..99,999,999, a missing level is 0, the page's value tolerated if stringified twice), `BuildJson`, and `SendToPage` (Pixel Streaming `Response` to every viewer through the default streamer) |
| `0003-MIProgressBridge-tests.patch` | `MurderInc.Cloud.ProgressBridge`: the five documented codes, every one-character change refused, bad versions / codes / holds / the away word / over-long messages, the byte round trip. Same vectors as the page's node tests |

The bridge is a pipe, not the store. The maps branch's progress store connects it in three lines:

- `FMIProgressBridge::OnReceived().AddLambda(...)`: merge the message into `FMIProgress` (4.5: merge, never replace; Hold
  bests max) and save. Game thread.
- `FMIProgressBridge::Provider().BindLambda(...)`: fill the current code and Hold bests; used for the hello.
- `FMIProgressBridge::SendCurrent()` after every change of progress (2.4: each debrief, each rating improvement).
  `ScheduleHello()` already sends the current progress 1 s after a viewer joins, so that a page with nothing stored
  gets a value; the page's own message after the channel opens is merged when it arrives.

When the store's own decoder lands, make `CheckCode` call it so the rule exists once (the Python prototype, the page
script and this function are three copies of the same 4.3 rule today, tied by the shared test vectors).

## To check when it is built

- `SendAllPlayersMessage(TEXT("Response"), Json)` is written from memory of Pixel Streaming 2's streamer interface, not
  against the 5.9 headers (none on the machine that wrote it): if the name or signature differs, only `SendToPage`
  changes. Compile it first.
- The `UIInteraction` handler wrapper in `GuardViewerInput` is the one B5 added; this patch applies to the v6 sources
  (`git apply --check` passes there).
- The E3DS relay of the game's `Response` up to the page is unverified: see the last section of
  `tools/ipx-bridge/README.md`. If E3DS does not relay it, nothing here is wasted: page to game still restores.
- No data sent beyond the code and three integers; nothing in the message identifies the player.
