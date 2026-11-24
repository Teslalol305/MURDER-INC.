# Decisions from the user

Decisions the owner made during the rebuild. Each one wins over any older design text that says otherwise.

## 2026-11-23: the pack rifle stands in for the CHOPPER; the NINE stays

**Asked:** after three rebuild rounds, an independent critic still graded the game's own guns 2.5/5 (CHOPPER) and
2/5 (NINE). The rifle from the purchased Infima pack looked clearly better in the game. The user was offered four ways
forward: buy gun packs, generate source models, keep hand-building, or use the pack rifle.

**Answer:** "Use the pack rifle". The pack's rifle stands in as the main gun, and the NINE stays as it is for now.

**What this means for the build:**

- **The CHOPPER's rules stay the web game's.** Its id, slot 1, its fire rate, damage, magazine, reload stage times,
  recoil and everything else the golden tests replay are unchanged. Only its presentation changes.
- **Its mesh and clips become the pack rifle's.** The CHOPPER is drawn with the pack rifle in the **Short handguard**
  length, the closest to the CHOPPER's compact build. It uses the pack's own first-person and third-person clips
  natively, with no hand IK and no adaptation. The adapted `A_FP_Chopper_*` and `A_TP_Chopper_*` clips and
  `SK_Chopper` are retired from the game (kept on the box and in `art/` for reference).
- **It must still read apart from SHORTY.** SHORTY is the same Short-handguard rifle in the loadout. The CHOPPER gets
  its own material instance: a worn dark-earth or bronze-tinted finish on the receiver and handguard, plus the gold
  accent of the web game's palette where a small part allows it. Its loadout card and HUD keep the name CHOPPER.
- **Reload timing.** The web game's reload stage times stay the rule. The pack's Reload_Quick and Reload_Empty clips
  are played at the rate that lands their magazine-out, magazine-in and bolt marks on the rule's stage times, as
  `ANIMATION.md` describes for the pack rifles.
- **Attachments.** The CHOPPER may now take the pack attachments its Short variant supports. The default set-up still
  carries none, so parity holds.
- **The NINE** keeps `SK_Nine` as it is now (critic 2/5) and the template pistol clips. Better pistol art and
  first-person pistol clips remain an open item: a matching pistol pack is the recommended route.
- **Licence:** unchanged. Nothing from the pack is committed; the stand-in works on the box and falls back to the
  template rifle in a clean checkout.

## 2026-11-23: the game lives on the IPX.exchange Game OS website, streamed

**Owner:** "this game will live on the IPX.exchange Game OS website". Asked how, since Unreal Engine 5 cannot run
inside a web page, the owner chose **"Stream Unreal"**: the full Unreal build runs on cloud GPUs and is streamed into
the IPX.exchange page (Pixel Streaming), playable with keyboard, mouse or gamepad.

**What this means for the build:**

- The delivery target is a **Linux server build with Pixel Streaming 2**, not a desktop package. Everything else
  (art, gameplay, menus) stays as it is.
- The website embeds the Pixel Streaming player (a web component or iframe) in a Game OS page. The site's own code is
  not in this repository; the build provides the player front end, the signalling server and a matchmaker that hands
  each visitor a free game instance, plus the instructions for the site to embed it.
- Each concurrent player needs one GPU game instance (or a share of a large GPU). Hosting cost scales with players:
  measure instances per GPU and cost per player-hour, and write them down.
- Input and UI must work in a browser tab: pointer lock for mouse look, keyboard, gamepad through the browser, a
  click-to-start overlay, audio started on the first click, and graceful handling of a lost connection.
- Latency budget for a shooter: aim for under 80 ms from input to picture on a good connection; measure it.
- The demo playable route (`docs/DEMO.md`) is the first step of this: the same Pixel Streaming set-up, on the box.

## 2026-11-23: hosting the streamed game: a managed Pixel Streaming service

**Asked:** the rented GPU box cannot serve the public (it exposes only its own private desktop page and forbids
tunnels or extra servers), so where should the website version be hosted? **Answer:** "Managed streaming": a
Pixel Streaming service that hosts Unreal games and gives an embed link and auto-scaling (for example Arcware Cloud
or PureWeb). The owner creates the account and uploads the build we package; pricing is per streaming minute.

**Open technical point:** several managed services take only Windows builds, and Unreal cannot package for Windows
from Linux. The next job must check, from each candidate's current documentation, which ones accept a Linux build,
and say plainly if a Windows packaging machine is needed.

**Research result (2026-11-23, `docs/unreal/hosting_research.json`, independently checked):** Eagle 3D Streaming
(E3DS) is the only managed Pixel Streaming host whose own docs accept a Linux Unreal build, so no Windows machine is
needed. Free 60-minute trial with no card; Core $29/month with 300 minutes and 10 concurrent players; extra minutes
$0.10 (about $6 per player-hour); US and EU. Fallback: Amazon GameLift Streams on its Ubuntu runtime (needs an AWS
account and a small session backend; gamepads may not work there). Risks: our engine is Unreal 5.9 Preview 2, which no
host lists; E3DS does not test Linux uploads, so the first upload on the free trial is the real test; budget the cloud
build for 8 GB of video memory; read E3DS's terms for a violent shooter before publishing.

## 2026-11-24: E3DS Core plan

**Owner:** upgraded the E3DS account from the trial to **Core** (dashboard: 300 minutes a month, 10 GB storage
included, 10 players at once). Build `MurderInc` version 1 (the zip of 2026-11-24, sha256 `8378eedd…e570a`, 2.2 GB)
is stored and used by `Project_MurderInc`; 7.8 GB is free, so the fixed build fits beside it as version 2 with no paid
storage. Once version 2 streams, delete version 1 from inside the build (open the build's versions), **not** the
build row's trash icon, which deletes the whole build.

**Still true on Core:** as far as E3DS publishes, Core streams on the same server pool as the trial (RTX 4080 or
RTX 5070 class, 8 or 16 GB of graphics memory), so the game must still fit an 8 GB card with headroom. The owner was
advised to ask E3DS support whether the app can be kept on 16 GB machines.

**Retry on Core (2026-11-24, about 18:55 UTC):** the owner opened the link again on Core, with ten slots, so no
leftover instance could hold the only slot. It **crashed again**. The Chrome console showed only errors from the
owner's crypto-wallet browser extensions (MetaMask, Backpack and others competing for `window.ethereum`), which have
nothing to do with the game, plus E3DS's `SessionIDFound {savedSessionId: …}`. There were no game lines: version 1
writes no log. So the crash is consistent, not caused by one blocked slot. That points to start-up on E3DS's
servers: graphics memory, the driver failing Unreal 5.9's Vulkan SM6 check, or the way E3DS launches the app. Test
version 2 in a fresh **Incognito** window: no extensions and no saved session.
