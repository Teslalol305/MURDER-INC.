# Putting MURDER INC. on the IPX.exchange Game OS page

The game runs on a graphics server at **Eagle 3D Streaming (E3DS)** and streams into the web page as video; the
player's mouse, keyboard and gamepad go back to it. Nobody installs anything. This page is everything you do, in
order. Plan about an hour for the first time, most of it waiting for uploads.

**Before anything else, know the one big risk.** The game is built with **Unreal Engine 5.9, which is still a
preview version**. E3DS lists support up to 5.8 for the original streaming plugin and "5.7 and later" for the new one
(Pixel Streaming 2, which we use), and it does **not** test Linux uploads before you stream them. So the free trial
is the real test: do steps 1 to 6 on the trial before paying for anything.

**The build to upload** is **version 2** of 2026-11-24 (sha256 `ceaf828d...`, nine parts, section 9): the E3DS
crash fix. Version 1 (sha256 `8378eedd...`) passed E3DS's upload check but crashed in every session, with no log; it
is superseded, as is the zip of 2026-11-23 (`4ff06998...`). Upload version 2 as a **new version of the existing
build `MurderInc`** (section 9, step 5). Every start now writes a log on the server (section 13).

## What you need

- The game file: **`MurderInc.zip`** (about 2.3 GB), in your Higgsfield storage in nine parts: join them
  first (section 9).
- Google Chrome or Microsoft Edge (Safari cannot lock the mouse and keyboard to the game).
- About 2.5 GB of upload; a wired connection helps.

## 1. Create the free E3DS trial account (no card)

1. Go to **eagle3dstreaming.com** and choose **Start free trial** (or **Sign up**).
2. Sign up with your email; confirm it from the email they send.
3. The trial gives **60 minutes of streaming in total** (not per month) and **one player at a time**. No credit card
   is asked for. Keep test sessions short.

## 2. Upload the game

1. Open the E3DS **Control Panel** and choose **Upload** (or **Add Application**).
2. **Platform: Linux.** (Not Windows: the game is a Linux build.)
3. **App name: `MurderInc`**, exactly like that: capital M, capital I, no space. E3DS finds the game by this name:
   it must match the launch file `MurderInc.sh` inside the zip.
4. Choose the joined zip (`MurderInc.zip`, section 9) and upload it. The upload is checked only for the
   streaming plugin's files; if it is refused at this point, see section 8. **If the build `MurderInc` already
   exists** (version 1 was uploaded on 2026-11-24), upload the zip as a new version of it instead: section 9, step 5.

## 3. Make the stream configuration

1. In the Control Panel open **Configurations** (or **Stream settings**) for the app, on the **Development** tab.
2. Create a new configuration for `MurderInc`.
3. Open **Advanced Options** and set **Platform** to **"Linux UE Build for PS"**. This is the setting that makes a
   Linux upload stream; without it the stream never starts.
4. Mouse: choose the **locked** mouse mode (the mouse is captured by the game after the first click). Do **not**
   choose "hovering": in a shooter the view would stop turning at the edge of the window.
5. Resolution: **1920 x 1080** (or "match the browser window"; see the note in section 7).
6. Session time: set a maximum session time and an idle (no input) logout, for example 30 minutes and 5 minutes,
   so a forgotten tab does not burn minutes.
7. Save. E3DS gives you a **share link** for this configuration.

## 4. Test the link in Chrome

1. Open the share link in Chrome. The first start of a Linux app takes longer than Windows apps (E3DS keeps no
   Linux server warm): expect **half a minute to a couple of minutes (the game itself is up about 8 seconds after it starts; the rest is E3DS finding and starting a Linux server)**; E3DS gives up after 3 minutes.
2. You see the game's home screen under a card that says **CLICK TO PLAY** (if E3DS shows its own play button
   first, click that, then the game). Click once. That click:
   - locks the mouse to the game (mouse look),
   - starts the sound (browsers keep sound off until you click). If E3DS started the stream muted, the click does
     not bring the sound: click E3DS's **speaker button at the bottom right** of the player (from version 3 the card
     says so),
   - hides the card. It does not press anything in the menus.
3. Check, in this order: the menus answer the mouse and keyboard; **Gear Up** goes through crew, loadout, block and
   briefing into a run; mouse look turns the view smoothly; W A S D moves; left click fires and you **hear** it;
   **P** pauses and resumes (see the box below); a gamepad plugged into your computer moves and aims.
4. Close the tab. The game pauses by itself when the last viewer leaves.

> **Esc and P.** In a browser, Esc belongs to the browser: it gives the mouse back to you and may never reach the
> game. So **P pauses** (Esc also works when the browser passes it on, and Start on a gamepad). The click card, the
> pause screen and, from the build of section 9 on, the home screen's controls row ("P Pause") say so. To take the
> mouse again after Esc, click the game.

## 5. Put it on the Game OS page

Paste this where the game should appear (replace the `src` with your share link):

```html
<div style="position:relative;width:100%;max-width:1280px;aspect-ratio:16/9;background:#000">
  <iframe id="iframe_1"
          src="PASTE-YOUR-E3DS-SHARE-LINK-HERE"
          style="position:absolute;inset:0;width:100%;height:100%;border:0"
          allow="autoplay; fullscreen; gamepad; pointer-lock; clipboard-read; clipboard-write"
          allowfullscreen></iframe>
</div>
<script>
  // E3DS's embed guide: give the game the keyboard as soon as it loads, and again whenever the player clicks it,
  // so W A S D go to the game and not to the page.
  const frame = document.getElementById('iframe_1');
  frame.addEventListener('load', () => frame.focus());
  frame.addEventListener('mouseenter', () => frame.focus());
</script>
```

- `allow="... pointer-lock ..."` is what lets the mouse lock into the game inside the page; `autoplay` lets the
  video start; `gamepad` lets gamepads through; `fullscreen` lets E3DS's full-screen button work.
- Give the frame a real size (the example keeps it 16:9). A small frame still works; the picture is scaled.
- If the Game OS page builder strips `<script>`, the game still works: the player clicks it once (which the CLICK TO
  PLAY card asks for anyway) and the keyboard follows.
- Check E3DS's current "Embed E3DS app with your HTML webpage" page for any newer attributes they recommend.

## 6. When the connection drops

- If the player's network drops or the tab is closed, the game **pauses itself**. E3DS shows its own message in the
  frame. Reloading the page starts a new session: a fresh game on a fresh server, with the click card again.
- Tell players on the page, next to the game: *"If the picture freezes or says disconnected, reload the page to play
  again."*

## 7. Before you make it public

- [ ] Steps 4 and 5 work on the Game OS page itself, in Chrome and Edge, on a normal home connection.
- [ ] A full run plays: Gear Up, a Story run to the IPX truck, and a few waves of Hold the Block.
- [ ] Sound plays after the first click; a gamepad works (Xbox or PlayStation pad, in Chrome).
- [ ] A controller alone (from version 3): plug in an Xbox or PlayStation pad, press a button on it so the browser
      sees it, and go from the CLICK TO PLAY card through the set-up screens into a run and back without touching
      the mouse or keyboard: any button hides the card, the D-pad or left stick moves, A (Cross) accepts, B (Circle)
      goes back, Start (Options) is Next, Hit the block and Pause. The game shows the Xbox names of the buttons until
      the player picks **Controller: PlayStation** on the Settings card (pause, Settings); it cannot tell
      which pad it is through a stream. Sound still needs one click on the page (the browser's rule), or E3DS's
      speaker button.
- [ ] The picture stays smooth for 10 minutes (no "Out of video memory" stop): the cloud settings are made for this
      (section 10).
- [ ] Max session time and idle logout are set (section 3), so minutes are not wasted.
- [ ] Read E3DS's terms of service for a violent shooter, and add an age note on the page if you want one.
- [ ] Decide the plan (section 11) and how many players may play at once; extra players wait in E3DS's queue.
- [ ] Mouse feel (from version 3): the game expects the picture to be shown at the size it is rendered (E3DS's
      Browser Resolution **Dynamic**, or a fixed size shown 1:1). If the view turns too fast or too slow, do not
      rebuild: put **`-MIMouseScale=<number>`** in the configuration's launch options (section 13). 0.5 is the built-in
      value; for a fixed 1920 x 1080 picture shown 1280 wide in the page use 0.333 (the rule: shown width divided by
      twice the rendered width). Players can also change **Sensitivity** on the game's Settings card.
- [ ] Console commands (from version 3): the game runs a console command that arrives through the stream only when
      it reads or sets one of the variables a visitor may tune: the stream's own settings (`PixelStreaming2.` or
      `PixelStreaming.`), the game's pacing (`MI.Cloud.`), the quality groups (`sg.`, 0 to 4), dynamic resolution
      (`r.DynamicRes.`, its smallest and largest picture between 25 and 100), `r.ScreenPercentage` (25 to 100),
      `t.MaxFPS` (0 to 120), `r.Streaming.PoolSize` (200 to 3000), `r.GTSyncType`, `r.OneFrameThreadLag` and
      `r.VolumetricFog.`. Anything else (`quit`, `open`, a debug command, a value out of range) is refused. So E3DS's
      field "Unreal console commands to run at start" takes for example `t.MaxFPS 30` (E3DS's own advice for a
      slow server: the game then holds 30 and says so on the pause card), if E3DS delivers that field to a Linux
      app (not yet seen). The launch option `-MICVars=` does the same without E3DS's field (section 13).
- [ ] The numbers (from version 3): press P in a run and take a screenshot. The small line at the bottom of the pause
      card names the server's graphics card, the frames a second and the frame-rate target, the GPU's time for a
      frame, the size the picture is drawn at and the size it is sent at, the stream as the server sends it (frames a
      second, megabits, QP, round trip) and the build. Send that screenshot with any report of lag: it says whether
      the server's card, the connection or the game is the limit. Both frame rates come with their **lowest value
      of the last half minute of play**, so pause right after a stutter:
      - "60 frames a second (lowest 58, …)" and "stream 57 a second (lowest 9)": the server was fine and the
        **connection** was not. The sender drops frames when the connection cannot carry a moving picture (measured
        on the GPU box: 5 to 7 frames a second received while turning at 1.7 Mbit/s, with the game at a steady 60).
        A nearer region, a wired connection or a lower Video Quality in E3DS's panel helps; the game cannot.
      - "31 frames a second (lowest 12, target 30)": the **server's graphics card** was the limit. Send it.

## 8. If E3DS rejects the build or it never starts

1. **Rejected at upload** ("no Pixel Streaming plugin" or a version message): send E3DS support the zip name and say
   it is an Unreal 5.9 Linux build with Pixel Streaming 2 (built into the game program; the zip carries only the
   plugin's helper scripts, `MurderInc/Samples/PixelStreaming2/WebServers/get_ps_servers.sh` and `.bat`). Ask
   whether 5.9 builds are accepted yet.
2. **Uploads but the stream never starts, or E3DS reports a crash**: check that the configuration's platform is
   "Linux UE Build for PS" and the app name is exactly `MurderInc`, then try once more (first Linux starts are slow).
   If it still fails, get the log: section 13.
3. **The fallback: Amazon GameLift Streams.** It runs any Linux program (no streaming plugin needed, so the engine
   version does not matter) on its Ubuntu 22.04 runtime. The costs and the work are different: you need an AWS
   account and a GPU quota increase, it bills for every hour a server is reserved whether anyone plays or not
   (about $0.50 an hour for a T4 server holding two players, in Oregon), and somebody must build a small website
   service that starts sessions; there is no ready-made embed link. Gamepads may not work there. Ask Claude to
   prepare the GameLift package if E3DS does not work out.

## 9. Getting the file

The zip of **2026-11-24, version 2** (the E3DS crash fix, commit `e989cb8`) is in your Higgsfield storage,
private to your account, in **9 parts** (the storage takes at most about 250 MB per file). They are named
`MurderInc-E3DS-v2b-part1-of-9.zip` to `MurderInc-E3DS-v2b-part9-of-9.zip`; **the parts are not zips on their own**: put them back
together first. The joined file is 2,254,912,173 bytes (about 2.3 GB); unpacked, the game is 2.7 GB.
The ten parts of version 1 (`MurderInc-E3DS-part1-of-10.zip` ..., sha256 `8378eedd…`) are superseded: do not upload
them again. Your storage also holds two earlier uploads of version 2 (`MurderInc-E3DS-v2-part<k>-of-9.zip`, joined
sha256 `a57e2288…` and `82ed886a…`: the same game with older launchers, which did not write E3DS's own log file):
ignore or delete them. Use the links of the release report; the rename step below only accepts the right parts.
The joined file is called `MurderInc.zip` on purpose: E3DS names a build after the file, and a Linux build's name
must be its launcher's name (`MurderInc.sh`).

1. Download the 9 parts into one empty folder (Higgsfield, your files/media library; the direct download links are
   in Claude's release report of 2026-11-24, version 2, or ask Claude for them). They are not written here because
   this page is in a public repository and the zip holds licensed content (see below). **The downloads arrive with
   random names** (like `e588797e-….zip`), not the part names, and Safari may try to open them: turn off "Open safe
   files after downloading" in Safari's settings, or use Chrome.
2. Give each download its part name. On a Mac, open Terminal in that folder and paste this; it reads each file's
   fingerprint (sha256) and renames it to the matching part, so the download order does not matter:

   ```
   for f in *.zip; do
     case "$(shasum -a 256 "$f" | cut -d' ' -f1)" in
       5d4627fc22ab913e8551a99093f2b49b9abc05dede870425c251194a17138da4) mv "$f" MurderInc-E3DS-v2b-part1-of-9.zip ;;
       7310851ba820c53b73eaeebb5bc0cf6524ae516654f9e74fe61b9dbd3cead106) mv "$f" MurderInc-E3DS-v2b-part2-of-9.zip ;;
       f84079f3c16b65d0c0d8325d731990b6aa5a6c1c6815926b3cdf9626bd72f2a4) mv "$f" MurderInc-E3DS-v2b-part3-of-9.zip ;;
       83b64ca6de7c72209d271f534089172523c6fa4d4b1b9b9b9d54649d6fb57f6f) mv "$f" MurderInc-E3DS-v2b-part4-of-9.zip ;;
       5d07e67a5fe4c6f86103ee87cddcdc78a805c1fdc1c7f9f41357588e55a7e304) mv "$f" MurderInc-E3DS-v2b-part5-of-9.zip ;;
       1332ca38d21dd230797ea5207907fbf8b84f37809c90677497b6188c92a3c805) mv "$f" MurderInc-E3DS-v2b-part6-of-9.zip ;;
       6c8c1f3e87c89447797603e5506e2f35ea9d19b43f08c747472dc3338995b152) mv "$f" MurderInc-E3DS-v2b-part7-of-9.zip ;;
       2d650732c1d2167510b55a17f150cd9bce14174a70f4526a4db2a6754444cd64) mv "$f" MurderInc-E3DS-v2b-part8-of-9.zip ;;
       f5289a9c2860aa6bb067488cf315416065196cb2c2d9954c3955343d3c084fdc) mv "$f" MurderInc-E3DS-v2b-part9-of-9.zip ;;
       *) echo "not a part (or incomplete, download again): $f" ;;
     esac
   done
   ls MurderInc-E3DS-v2b-part*
   ```

   It must list 9 parts. On Windows, rename them by hand using the table below (`certutil -hashfile <file> SHA256`
   shows a file's fingerprint; part 9 is the small one, about 242 MB).
3. Join them. On a Mac, in the same Terminal:

   ```
   cat MurderInc-E3DS-v2b-part{1,2,3,4,5,6,7,8,9}-of-9.zip > MurderInc.zip
   shasum -a 256 MurderInc.zip
   ```

   (Type the braces as shown: they keep the parts in the order 1 to 9.) On Windows, in Command Prompt, in that
   folder:

   ```
   copy /b MurderInc-E3DS-v2b-part1-of-9.zip+MurderInc-E3DS-v2b-part2-of-9.zip+MurderInc-E3DS-v2b-part3-of-9.zip+MurderInc-E3DS-v2b-part4-of-9.zip+MurderInc-E3DS-v2b-part5-of-9.zip+MurderInc-E3DS-v2b-part6-of-9.zip+MurderInc-E3DS-v2b-part7-of-9.zip+MurderInc-E3DS-v2b-part8-of-9.zip+MurderInc-E3DS-v2b-part9-of-9.zip MurderInc.zip
   certutil -hashfile MurderInc.zip SHA256
   ```
4. The fingerprint printed must be `ceaf828d10a8b3d7997e8b76ccaa7701e87a8f5dab7f488a1976a3b7944674c5`. If it does not, a
   part is incomplete: compare each part with the list below (`shasum -a 256 MurderInc-E3DS-v2b-part*`), download the
   one that differs again.
5. **Upload it to E3DS as a new version of the existing build `MurderInc`**, not as a new build (E3DS's own
   names, from its documentation): **Your Projects**, open `Project_MurderInc`, tab **Builds**, **Upload a new
   version of MurderInc** (the same button is **New version** on the project list). Choose the joined
   `MurderInc.zip` (not the parts). The window shows the versions the build has and that this upload becomes
   version 2. If it asks: Streams with **Pixel Streaming**, Runs on **Linux**, executable **MurderInc.sh**. When the
   upload is processed the project streams the new version by itself (nothing to choose or save) and the link stays
   the same; "Run a fixed version" must read **Latest**. E3DS does not stream-test Linux uploads, so a green check
   proves nothing: test the link (section 4), best in a fresh Incognito window. Once version 2 streams, delete
   version 1 with the **Delete** button beside it in the version list, **not** by deleting the build.
6. **The log** of every start goes to the file E3DS itself names when it starts the app (`-ABSLOG=`, the file its
   crash-log email is taken from), to the launcher's output, and to `MurderInc/Saved/Logs/MurderInc.log` in the
   app's folder. If it crashes again, section 13 says how to get it.

| Part | Bytes | sha256 |
|---|---|---|
| 1 | 251,658,240 | `5d4627fc22ab913e8551a99093f2b49b9abc05dede870425c251194a17138da4` |
| 2 | 251,658,240 | `7310851ba820c53b73eaeebb5bc0cf6524ae516654f9e74fe61b9dbd3cead106` |
| 3 | 251,658,240 | `f84079f3c16b65d0c0d8325d731990b6aa5a6c1c6815926b3cdf9626bd72f2a4` |
| 4 | 251,658,240 | `83b64ca6de7c72209d271f534089172523c6fa4d4b1b9b9b9d54649d6fb57f6f` |
| 5 | 251,658,240 | `5d07e67a5fe4c6f86103ee87cddcdc78a805c1fdc1c7f9f41357588e55a7e304` |
| 6 | 251,658,240 | `1332ca38d21dd230797ea5207907fbf8b84f37809c90677497b6188c92a3c805` |
| 7 | 251,658,240 | `6c8c1f3e87c89447797603e5506e2f35ea9d19b43f08c747472dc3338995b152` |
| 8 | 251,658,240 | `2d650732c1d2167510b55a17f150cd9bce14174a70f4526a4db2a6754444cd64` |
| 9 | 241,646,253 | `f5289a9c2860aa6bb067488cf315416065196cb2c2d9954c3955343d3c084fdc` |

Checked after the upload: all 9 parts downloaded back from the storage, joined, the sha256 above, and
`unzip -t` reports no errors (64 files; `MurderInc.sh` and `BUILD.txt` at the root).

What is new in version 2 (docs/unreal/PROGRESS.md, "E3DS crash fix"): the launcher `MurderInc.sh` always starts the
game without a window (`-RenderOffScreen`: E3DS's Linux servers have no screen and E3DS does not add that option
itself; on the GPU box version 1 without it ends after 2 seconds with no log, which matches what E3DS reported, though
without E3DS's log it is not proven), writes the log above, also
into E3DS's own log file, and never runs the game as root; the game carries the SM5 shaders too, so a server whose graphics driver fails
Unreal 5.9's SM6 check runs a simpler picture instead of quitting; it needs less graphics memory at start; it reports
a stop by the host as a normal quit; the home screen says "P Pause"; and the Development game rides along for E3DS's
crash-log feature (launch option `-MIDev`, section 13).

The zip contains licensed content (the rifle animation pack, Epic's template content and the main character's
likeness): upload it only to E3DS, do not share the links.

## 10. What the cloud settings change

The game picks a **Cloud** graphics profile by itself when it runs in a stream. E3DS's servers have 8 or 16 GB of
graphics memory (RTX 4080 or 5070 class) and 32 GB of memory; their own advice is to stay near 4 to 6 GB.

Measured on the GPU box at 1920 x 1080 on the **older zip of 2026-11-23** (how in `docs/unreal/PROGRESS.md`, "Cloud build"):

| Run | Graphics memory | Memory (RAM) |
|---|---|---|
| Story run, desktop settings (Epic) | 4.3 GB the game's own; 6.7 GB added on the whole card | 3.2 GB |
| Story run, Cloud settings | 5.5 to 5.7 GB added on the whole card | 3.2 GB |
| Hold the Block, Cloud settings (first waves) | 3.4 GB the game's own; 5.3 GB on the whole card | 3.1 GB |
| Home screen: desktop / Cloud | 3.8 GB / 3.2 GB the game's own | 3.0 GB |

The zip of 2026-11-24 has more art; in its start-up check its memory (RAM) peaked at **3.8 GB** (Shipping) and 4.0 GB
(Development), still far under a server's 32 GB.

**Version 2 (the E3DS crash fix) needs less graphics memory.** Measured with the Vulkan driver's own count
(`r.Vulkan.DumpMemory`, the game's committed memory) on the box, Development game, 1920 x 1080:

| Moment | Version 1 | Version 2 |
|---|---|---|
| Home screen, 6 s after the start | 4.2 GB | 3.6 GB |
| Story run, 30 s in | 4.5 GB | 3.8 GB |

and with the card artificially full (`tools/box/cloud/vram_hog.py`): version 1 crashed 6 s after the start with
5.0 GB free; version 2 starts and holds the home screen at 60 fps with 5.0 GB free, plays a Story run at 60 fps with
6.0 GB free, and runs E3DS-style with 7.6 GB free (an 8 GB card). The card's own counter (`nvidia-smi`) shows more
than the table for the whole process (about 2 GB more for version 1: the driver's share, shader caches).

"The game's own" is what the graphics driver reports for the game alone; "on the whole card" is the rise of the
card's counter while the game ran, which also catches the driver's own share and anything else that grew meanwhile
(other work shared the box's card). Either way the game stays **under 7 GB**, inside an 8 GB server card, with
room to spare on a 16 GB one, and far under the 32 GB of memory.

What the Cloud settings change, and what you might notice:

- **Reflections** are worked out at half resolution, and only on shiny surfaces (wet road, glass, car paint); matte
  surfaces fall back to a simpler reflection. You may notice slightly softer reflections in puddles and windows.
- **Shadows** get a smaller memory pool: in very wide views distant shadows can be a little softer.
- **Fine geometry** streams from a smaller pool: on a fast turn, distant detail can take a moment longer to sharpen.
- **Motion blur is off** (it costs video bandwidth and smears on a stream anyway).
- **Texture pool** 600 MB in version 2 (800 MB in version 1, 1000 MB on the desktop; the first table was measured
  with 1500 MB). On a fast turn a distant texture can take a moment longer to sharpen.
- **Anti-aliasing history** at the stream's resolution (the desktop keeps a 4K history at 1080p): no visible change
  once the video is compressed.
- **The rooms behind shop and home windows** are stored compressed (BC6H), an eighth of the memory, same size.
- The picture is capped at 60 frames a second, the rate the stream sends.

Lighting itself (Lumen with hardware ray tracing), Nanite and the art are unchanged.

**From version 3 the game never runs the graphics card full.** Version 2 lagged on E3DS ("when the player turns it
slows down"): a game that draws without a screen never waits for the graphics card, so on a card slower than 60
frames a second the unfinished frames piled up and the game then froze until the card had caught up (frames of 1 to
8 seconds on the GPU box with a slowed-down card; `docs/unreal/PROGRESS.md`, "Version 3, release A"). Version 3:

- **does not start a frame while the card still owes it more than one** (the pile cannot form, whatever the card);
- **draws a smaller picture when the card is busy** (dynamic resolution: between 50 and 75 % of the size sent, 75 %
  is what version 2 always drew at 1080p; the sent picture stays 1920 x 1080 and is sharpened from it), aiming at 70 %
  use of the card, which is what E3DS asks of an app;
- **lowers its frame-rate target from 60 to 45 and then 30** when the card cannot hold the higher rate even at the
  smallest picture (it decides this within the first seconds of a run, never on a menu), and raises it again only
  while no run is being played. 30 steady frames a second on a slow card instead of 60 that freeze.

What you might notice on a slow server card: a softer picture, and 45 or 30 frames a second. On a fast one: nothing.
The pause card's small line says what the game settled on (section 7).

## 11. Prices (as researched on 2026-11-23: check eagle3dstreaming.com/pricing before you pay)

| Plan | Price | Streaming time | Players at once |
|---|---|---|---|
| Trial | free, no card | 60 minutes in total | 1 |
| Core | $29 a month (or $290 a year) | 300 minutes a month (unused minutes expire) | 10 |
| Extra minutes | $0.10 a minute, bought 100 at a time | | |
| Enterprise | custom, about $0.10 a minute | | up to 1,000, more regions |

One player for one hour uses 60 minutes, so beyond the included minutes it costs about **$6 per player-hour**. E3DS
never bills automatically: when the minutes run out, streaming stops. Servers: US (Texas) and EU on Trial and Core;
players go to the nearer one.

## 12. Making a new build later

Claude rebuilds the whole package with one command on the GPU box (`tools/box/cloud/package-cloud.sh all`: about
10 minutes on a warm cache, 8 on 2026-11-24; on a freshly rented box the first cook of version 2 with its SM5 shaders
took about 20 minutes), runs the crash-cause checks (`tools/box/cloud/e3ds-verify.sh`, about 20 minutes: the box
cannot test an actual stream, that is what the E3DS link in section 4 is for), and puts the new zip, in parts, in
your Higgsfield storage. You then upload it to E3DS as a new version of the build `MurderInc` (section 9, step 5)
and test the link again.

## 13. If it crashes again: the log

The first upload (the zip of 2026-11-24, sha256 `8378eedd…`) crashed on E3DS with "no crashlog was found": that
build wrote no log at all (Shipping builds compile the engine's log out). **The build of section 9 always writes
one.** On the E3DS server, inside the app's folder:

| File | What is in it |
|---|---|
| `MurderInc/Saved/Logs/MurderInc.log` | written by the launcher `MurderInc.sh` for every start: the build's commit (`BUILD.txt`), the user, the GPU, its driver and free graphics memory, other programs holding graphics memory, the Vulkan check Unreal 5.9 needs, the arguments E3DS passed, every line the game prints (its own `[MICloud]` lines: GPU, shader platform, ray tracing, Nanite, Lumen, video memory, viewers joining and leaving), and at the end how the game ended: `quit normally` (with `stop asked by SIGTERM` when the host stopped it), `CRASH: the game was killed by signal 11 (SIGSEGV)` or `ENDED with exit code 1`, followed by the engine's crash report (the call stack) |
| `MurderInc/Saved/Logs/MurderInc-backup-<time>.log` | the run before (the last ten are kept) |
| `MurderInc/Saved/Crashes/crashinfo-MurderInc-pid-<n>-<id>/` | the engine's own crash report (`Diagnostics.txt`, `CrashContext.runtime-xml`); nothing is sent anywhere |

If the app folder cannot be written there, the same files go to `$HOME/MurderInc-cloud/Saved/` (or `/tmp`); the
log's first lines say where.

**Getting it** (E3DS's own options, as their documentation describes them; we could not open their pages from the
build machine, so the menu names may differ slightly):

1. **Browser console.** Keep "Show the Unreal log in the browser console" on. Open Chrome's developer tools
   (**F12**, or **Cmd+Option+J** on a Mac) on the **Console** tab *before* opening the link, then play. If it
   crashes, right-click in the console and choose **Save as...**. E3DS does not say which file it prints; if the
   console shows nothing from the game, use 2 or 3.
2. **The Development game, for E3DS's crash-log email.** E3DS's "Auto Download UE Crash Log" (stream configuration,
   **Advanced Options**, **Developer**) only works with Development builds. The zip carries one beside the normal
   game: put **`-MIDev`** in the configuration's **launch options**, start the link again, and that session writes
   the full engine log, with call stacks, to `MurderInc/Saved/Logs/MurderInc.log`, where Development builds keep
   it. Take `-MIDev` out again afterwards (it keeps the developer console and checks on).
3. **Ask E3DS support** (email or chat) for the files above. Give them: app `MurderInc`, the version, the
   configuration, and the time of the crash in UTC (their crash email gives it in your time zone). Ask them for
   `MurderInc/Saved/Logs/MurderInc.log` and the folder `MurderInc/Saved/Crashes/` from the server that ran the
   session, and while you are at it: the exact command line and user their Linux servers start the app with, that
   server's GPU model, NVIDIA driver version and graphics memory, whether two apps can share one GPU, and how they
   decide an app "crashed" (exit code, or the stream disconnecting).
4. **Send the log to Claude.** Its first lines name the commit; the GPU box keeps that build's debug symbols
   (`/project/ue/cloud/symbols/<commit>/`), which turn the crash report's addresses into function names.

**Reading the end of the log yourself:**

- `Vulkan SM6 check: MISSING ...` or `[MICloud] Fallback: this GPU or driver did not pass Unreal's SM6 check`: the
  server's NVIDIA driver is older than Unreal 5.9 needs for its full renderer. The game still runs on its SM5
  shaders (no Nanite, so simpler distant meshes; Lumen in software), and E3DS support can say whether newer drivers
  exist on other servers. The launch option `-MIForceSM6` makes Unreal skip that check (untested: it may then work
  fully, or crash; try it once, read the log).
- `CRASH: ... SIGSEGV` a few seconds after `[MICloud] Features ... video memory`: look for `Out Of Memory` just
  above: the server's graphics card was full (the GPU line at the top shows how much was free and what else used it).
- `ENDED with exit code 1` within about 10 seconds: a missing shader platform or file; the lines above it say which.
- `CRASH: ... signal 9 (SIGKILL)`: not a fault inside the game. Something outside ended it at once: the host
  stopping the session hard, or the system's out-of-memory killer when the server ran out of memory (the memory line
  at the top shows how much was available). Ask E3DS which one it was.
- `quit normally` (or `stopped by SIGTERM after the host's SIGTERM`): no crash on our side; if E3DS still reported
  one, the log is the evidence to send them.

**Launch options** (stream configuration, launch options; leave empty normally):

| Option | Effect |
|---|---|
| `-MIDev` | run the Development game (full engine log, for E3DS's crash-log feature and support) |
| `-MIMouseScale=<number>` | from version 3: mouse look speed through the stream (0.05 to 4; built-in 0.5). See section 7, "Mouse feel" |
| `-MIFps=60` (or `45`, `30`) | from version 3: fixes the frame-rate target instead of letting the game choose it by the card's time. `-MIFps=30` is the safe setting for a server that turns out to be slow |
| `-MICVars=name=value,name=value` | from version 3: sets console variables at start without a new build, each one printed in the log (`[MICloud] Launch option -MICVars: ...`). Only the variables of section 7's list. Examples: `-MICVars=r.DynamicRes.MinScreenPercentage=40` (allow a smaller picture), `-MICVars=MI.Cloud.GpuFramesInFlight=0` (the lowest delay at the cost of some frame rate on a slow card), `-MICVars=sg.GlobalIlluminationQuality=2,sg.ShadowQuality=2` (cheaper light and shadows) |
| `-MICloudProbe=<seconds>` | how often the game writes its line of numbers into the log (`MICloudProbe fps=... worstMs=... gpuMs=... target=... dr=... owed=...`); from version 3 every 30 s by itself, `0` turns it off |
| `-MIForceSM6` | skip Unreal's Vulkan SM6 check on a driver that fails it |
