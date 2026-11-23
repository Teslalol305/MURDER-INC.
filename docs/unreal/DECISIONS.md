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
