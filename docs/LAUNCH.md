# Putting MURDER INC. on the IPX.exchange Game OS page

The game runs on a graphics server at **Eagle 3D Streaming (E3DS)** and streams into the web page as video; the
player's mouse, keyboard and gamepad go back to it. Nobody installs anything. This page is everything you do, in
order. Plan about an hour for the first time, most of it waiting for uploads.

**Before anything else, know the one big risk.** The game is built with **Unreal Engine 5.9, which is still a
preview version**. E3DS lists support up to 5.8 for the original streaming plugin and "5.7 and later" for the new one
(Pixel Streaming 2, which we use), and it does **not** test Linux uploads before you stream them. So the free trial
is the real test: do steps 1 to 6 on the trial before paying for anything.

**The build to upload** is **version 3a** of 2026-11-25 (sha256 `de41a708...`, nine parts, section 9): the build
that ends the lag of version 2, sets the mouse speed right, makes a controller work and shows its own numbers on the
pause card. Version 2 (sha256 `ceaf828d...`) streamed on E3DS but lagged ("when the player turns it slows down");
version 1 (`8378eedd...`) crashed in every session. Upload version 3a as a **new version of the existing build
`MurderInc`** (section 9, step 5), with the E3DS settings of section 9.1. Every start writes a log on the server
(section 13).

**Version 3a has no sound. Neither had versions 1 and 2.** The release check of version 3a measured the sound that
arrives through the stream and found silence: the game's sound files were never packed into the build (they exist;
a packing step was left out). The speaker button and the browser's volume change nothing, so do not look for a
mute. Version 3a is still the build to test for the lag, the mouse and the controller; the build after it brings
the sound (`docs/unreal/PREFLIGHT.md`, V3-14), and the game must not go public before that.

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

> For version 3a the settings to use, with E3DS's current names and places, are in **section 9.1**. Where the steps
> below differ (session time, the resolution, the tab names), section 9.1 is right; this section is from before the
> first upload and will be rewritten with the next build.

1. In the Control Panel open **Configurations** (or **Stream settings**) for the app, on the **Development** tab.
2. Create a new configuration for `MurderInc`.
3. Turn **Advanced Options** on and, on the **Developer** tab, set **Platform** to **Linux** (the field offers
   Streaming App, Windows and Linux). This is the setting that makes a Linux upload stream; without it the stream
   never starts.
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
     says so). **Up to and including version 3a there is no sound to start: those builds are silent** (the note at
     the top of this page),
   - hides the card. It does not press anything in the menus.
3. Check, in this order: the menus answer the mouse and keyboard; **Gear Up** goes through crew, loadout, block and
   briefing into a run; mouse look turns the view smoothly; W A S D moves; left click fires (and, from the build after version 3a, you **hear** it);
   **P** pauses and resumes (see the box below); a gamepad plugged into your computer moves and aims.
4. Close the tab. On E3DS that ends the session at once: E3DS stops the game and frees the server (its
   documentation: "A viewer who closes the tab is never waited for"). The game also pauses by itself whenever its
   last viewer leaves, so nothing plays on unseen in between.

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

- If the player's network drops or the tab is closed, the game **pauses itself** (from version 3 also in the two
  seconds before a run goes live) and lets go of everything the player was holding: keys, mouse buttons, sticks and
  triggers. A key that was down when the connection was cut would otherwise still count as down afterwards, and the
  player would walk or fire by himself after a reconnect. E3DS shows its own message in the frame. Reloading the page
  starts a new session: a fresh game on a fresh server, with the click card again. (By E3DS's documentation a broken
  connection ends an Unreal app's session at once; its setting "Keep the app running when a viewer loses
  connection" applies to Omniverse apps only today. So a player never comes back into the same game: the pause
  covers only the moment before E3DS stops it.)
- Tell players on the page, next to the game: *"If the picture freezes or says disconnected, reload the page to play
  again."*

## 7. Before you make it public

- [ ] Steps 4 and 5 work on the Game OS page itself, in Chrome and Edge, on a normal home connection.
- [ ] A full run plays: Gear Up, a Story run to the IPX truck, and a few waves of Hold the Block.
- [ ] Sound plays after the first click (not before the build after version 3a: versions 1 to 3a are silent); a
      gamepad works (Xbox or PlayStation pad, in Chrome).
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
      With Browser Resolution **Dynamic** the page asks the game for the size of the player's frame. From version 3
      the game draws at that size only between 640 x 360 and 1920 x 1080: a larger frame (a 1440p or 4K monitor in
      full screen) gets the largest picture of its shape that fits 1920 x 1080, scaled up by the browser, and the
      mouse keeps its speed (the game works the scale out from the two sizes); a smaller one (a phone held upright)
      is ignored. Until the rest of that work is done (release B: the picture's sharpness and the HUD at small sizes)
      keep Browser Resolution at **Custom 1920 x 1080**.
- [ ] A double click (from version 3): two quick clicks could leave the fire button held (an automatic gun kept
      firing until the next click, and that click fired nothing), because the page sends a "double click" message
      that Unreal takes for a third press, and a page that sends no release after it leaves that press held. On the
      GPU box, with a test viewer that sends it so, version 2's code emptied the magazine after one double click;
      whether E3DS's page sends it so was read from its script in review, not seen on E3DS. Version 3 drops the
      message: a double click is two clicks. Check it once in a run: two quick clicks fire two rounds, and the gun
      stops.
- [ ] Console commands (from version 3): the game runs a console command that arrives through the stream only when
      it reads or sets one of the variables a visitor may tune: the stream's own settings (`PixelStreaming2.` or
      `PixelStreaming.`, but not its two debug dumps, which write files on the server), the game's pacing
      (`MI.Cloud.`), the quality groups (`sg.`, 0 to 3: the levels of the Settings card), dynamic resolution
      (`r.DynamicRes.`, its smallest and largest picture between 25 and 100), `r.ScreenPercentage` (25 to 100),
      `t.MaxFPS` (0 to 120), `r.Streaming.PoolSize` (200 to 3000), `r.GTSyncType`, `r.OneFrameThreadLag`, and the
      fog's two grid sizes (`r.VolumetricFog.GridPixelSize` 8 to 32, `r.VolumetricFog.GridSizeZ` 32 to 128).
      Anything else (`quit`, `open`, a debug command, a value out of range) is refused. So E3DS's
      field "Unreal console commands to run at start" takes for example `t.MaxFPS 30` (E3DS's own advice for a
      slow server: the game then holds 30 and says so on the pause card), if E3DS delivers that field to a Linux
      app (not yet seen). The launch option `-MICVars=` does the same without E3DS's field (section 13).
- [ ] The numbers (from version 3): press P in a run and take a screenshot. The small line at the bottom of the pause
      card names the server's graphics card, the frames a second and the frame-rate target, the GPU's time for a
      frame, the size the picture is drawn at and the size it is sent at, the stream as the server sends it (frames a
      second, megabits, QP, round trip) and the build. Send that screenshot with any report of lag: it says whether
      the server's card, the connection or the game is the limit. Both frame rates come with their **lowest value
      of the last half minute of play**, so pause right after a stutter:
      - "60 frames a second (lowest 58, …)" and "stream 57 a second (lowest 9), 1.9 Mbit/s": the server was fine and
        the **connection** was not: the stream's number fell far below the game's **and the megabits are low**. The
        sender drops frames when the connection cannot carry a moving picture (measured on the GPU box: 5 to 7 frames
        a second received while turning at 1.7 Mbit/s, with the game at a steady 60). A nearer region or a wired
        connection is the cure; a lower Video Quality in E3DS's panel should help too (not measured). The game
        cannot.
      - "60 frames a second …" and "stream 56 a second (lowest 50), 11 Mbit/s": a stream number **a few below the
        game's with plenty of megabits is the server's video encoder**, not the connection. On the GPU box the
        encoder sends 56 to 57 of the game's 60 frames a second on a free card (single seconds at 45 to 50), whatever
        the viewer and the settings: some frames take it longer than the sixtieth of a second it has, and the frame
        behind such a one is dropped. At 45 frames a second it sends 43 to 44, at 30 all 30. If E3DS's servers show a
        larger gap than the box, send the screenshot: `-MIFps=45` (section 13) is then the setting to try.
      - "31 frames a second (lowest 12, target 30)": the **server's graphics card** was the limit. Send it.

## 8. If E3DS rejects the build or it never starts

1. **Rejected at upload** ("no Pixel Streaming plugin" or a version message): send E3DS support the zip name and say
   it is an Unreal 5.9 Linux build with Pixel Streaming 2 (built into the game program; the zip carries only the
   plugin's helper scripts, `MurderInc/Samples/PixelStreaming2/WebServers/get_ps_servers.sh` and `.bat`). Ask
   whether 5.9 builds are accepted yet.
2. **Uploads but the stream never starts, or E3DS reports a crash**: check that **Platform** (Developer tab) is
   **Linux** and the build's name is exactly `MurderInc`, then try once more (first Linux starts are slow).
   If it still fails, get the log: section 13.
3. **The fallback: Amazon GameLift Streams.** It runs any Linux program (no streaming plugin needed, so the engine
   version does not matter) on its Ubuntu 22.04 runtime. The costs and the work are different: you need an AWS
   account and a GPU quota increase, it bills for every hour a server is reserved whether anyone plays or not
   (about $0.50 an hour for a T4 server holding two players, in Oregon), and somebody must build a small website
   service that starts sessions; there is no ready-made embed link. Gamepads may not work there. Ask Claude to
   prepare the GameLift package if E3DS does not work out.

## 9. Getting the file

The zip of **2026-11-25, version 3a** (commit `6c4d810`) is in your Higgsfield storage, private to your account, in
**9 parts** (the storage takes at most about 250 MB per file). They are named `MurderInc-E3DS-v3a-part1-of-9.zip` to
`MurderInc-E3DS-v3a-part9-of-9.zip`; **the parts are not zips on their own**: put them back together first. The
joined file is 2,254,962,151 bytes (about 2.3 GB); unpacked, the game is 2.7 GB.

Everything older in your storage is superseded: ignore or delete the parts of version 2
(`MurderInc-E3DS-v2b-part<k>-of-9.zip` and `MurderInc-E3DS-v2-part<k>-of-9.zip`) and of version 1
(`MurderInc-E3DS-part<k>-of-10.zip`). Use the links of the release report of version 3a; the rename step below only
accepts the right parts. The joined file is called `MurderInc.zip` on purpose: E3DS names a build after the file, and
a Linux build's name must be its launcher's name (`MurderInc.sh`).

1. Download the 9 parts into one empty folder (Higgsfield, your files/media library; the direct download links are
   in Claude's release report of version 3a, or ask Claude for them). They are not written here because this page is
   in a public repository and the zip holds licensed content (see below). **The downloads arrive with random names**
   (like `e588797e-….zip`), not the part names, and Safari may try to open them: turn off "Open safe files after
   downloading" in Safari's settings, or use Chrome.
2. Give each download its part name. On a Mac, open Terminal in that folder and paste this; it reads each file's
   fingerprint (sha256) and renames it to the matching part, so the download order does not matter:

   ```
   for f in *.zip; do
     case "$(shasum -a 256 "$f" | cut -d' ' -f1)" in
       ce4507d81784d274f9a8499c482a2e6e1047bc7e5d1dc6f714eb2ce3a24f6d94) mv "$f" MurderInc-E3DS-v3a-part1-of-9.zip ;;
       d387f5a4065da5f4a913f87a4d08488aee209fdce8f51b846f6c43e3cc26832a) mv "$f" MurderInc-E3DS-v3a-part2-of-9.zip ;;
       070db64bd2f041c2952258c577d30f691977eb39bd5fae4c77f6dfd647dabc83) mv "$f" MurderInc-E3DS-v3a-part3-of-9.zip ;;
       6d3d1f0229bc8b86471fa57d8f88adc7f73aae50a24ce3a2b7e533c63b6c762f) mv "$f" MurderInc-E3DS-v3a-part4-of-9.zip ;;
       2d0a04a975a87a1c397365fcaa94cfca1701398f7a9cc5393d08d35a7d29f571) mv "$f" MurderInc-E3DS-v3a-part5-of-9.zip ;;
       452d9ea0ddac18103186dd0a8a3f18c009e0a962597a8ce10e970806e1ac1624) mv "$f" MurderInc-E3DS-v3a-part6-of-9.zip ;;
       4cc3c4599b8780b27b4eb5080a345bc2e71dee22a2f762588d24f6d367bc354a) mv "$f" MurderInc-E3DS-v3a-part7-of-9.zip ;;
       efaec6ea574ebd3e4e3fe6cf3d4eb304abc1f9060f9afff9225e573d284e4f55) mv "$f" MurderInc-E3DS-v3a-part8-of-9.zip ;;
       d04652438afdc595139a8722d074c60098db769be78f2e01775129e074046fad) mv "$f" MurderInc-E3DS-v3a-part9-of-9.zip ;;
       *) echo "not a part (or incomplete, download again): $f" ;;
     esac
   done
   ls MurderInc-E3DS-v3a-part*
   ```

   It must list 9 parts. On Windows, rename them by hand using the table below (`certutil -hashfile <file> SHA256`
   shows a file's fingerprint; part 9 is the small one, about 242 MB).
3. Join them. On a Mac, in the same Terminal:

   ```
   cat MurderInc-E3DS-v3a-part{1,2,3,4,5,6,7,8,9}-of-9.zip > MurderInc.zip
   shasum -a 256 MurderInc.zip
   ```

   (Type the braces as shown: they keep the parts in the order 1 to 9.) On Windows, in Command Prompt, in that
   folder:

   ```
   copy /b MurderInc-E3DS-v3a-part1-of-9.zip+MurderInc-E3DS-v3a-part2-of-9.zip+MurderInc-E3DS-v3a-part3-of-9.zip+MurderInc-E3DS-v3a-part4-of-9.zip+MurderInc-E3DS-v3a-part5-of-9.zip+MurderInc-E3DS-v3a-part6-of-9.zip+MurderInc-E3DS-v3a-part7-of-9.zip+MurderInc-E3DS-v3a-part8-of-9.zip+MurderInc-E3DS-v3a-part9-of-9.zip MurderInc.zip
   certutil -hashfile MurderInc.zip SHA256
   ```
4. The fingerprint printed must be `de41a7089a3e940c010806753640e1c84b3f357f0e551e067f300b006eef58e4`. If it is
   not, a part is incomplete: compare each part with the list below (`shasum -a 256 MurderInc-E3DS-v3a-part*`) and
   download the one that differs again.
5. **Upload it to E3DS as a new version of the existing build `MurderInc`**, not as a new build (E3DS's own names,
   from its documentation): **Your Projects**, open `Project_MurderInc`, tab **Builds**, **Upload a new version of
   MurderInc** (the same button is **New version** on the project list). Choose the joined `MurderInc.zip` (not the
   parts). The window shows the versions the build has and that this upload becomes the next one (version 3). If it
   asks: Streams with **Pixel Streaming**, Runs on **Linux**, executable **MurderInc.sh**. When the upload is
   processed the project streams the new version by itself (nothing to choose or save) and the link stays the same;
   "Run a fixed version" must read **Latest**. Keep version 2 until version 3 has played well (to go back, choose
   version 2 under "Run a fixed version"); version 1 never worked: remove it with the **Delete** button beside it in
   the version list, **not** with the build's trash icon, which deletes the whole build.
6. Set the E3DS settings of 9.1, press **Save changes**, and open the link in a new Chrome Incognito window. E3DS
   does not stream-test Linux uploads, so a green check proves nothing: the link is the test.

| Part | Bytes | sha256 |
|---|---|---|
| 1 | 251,658,240 | `ce4507d81784d274f9a8499c482a2e6e1047bc7e5d1dc6f714eb2ce3a24f6d94` |
| 2 | 251,658,240 | `d387f5a4065da5f4a913f87a4d08488aee209fdce8f51b846f6c43e3cc26832a` |
| 3 | 251,658,240 | `070db64bd2f041c2952258c577d30f691977eb39bd5fae4c77f6dfd647dabc83` |
| 4 | 251,658,240 | `6d3d1f0229bc8b86471fa57d8f88adc7f73aae50a24ce3a2b7e533c63b6c762f` |
| 5 | 251,658,240 | `2d0a04a975a87a1c397365fcaa94cfca1701398f7a9cc5393d08d35a7d29f571` |
| 6 | 251,658,240 | `452d9ea0ddac18103186dd0a8a3f18c009e0a962597a8ce10e970806e1ac1624` |
| 7 | 251,658,240 | `4cc3c4599b8780b27b4eb5080a345bc2e71dee22a2f762588d24f6d367bc354a` |
| 8 | 251,658,240 | `efaec6ea574ebd3e4e3fe6cf3d4eb304abc1f9060f9afff9225e573d284e4f55` |
| 9 | 241,696,231 | `d04652438afdc595139a8722d074c60098db769be78f2e01775129e074046fad` |

Checked after the upload (2026-11-25, 07:37 UTC): all 9 parts downloaded back from the storage, every fingerprint
as in the table, joined to 2,254,962,151 bytes with the sha256 of step 4, and `unzip -t` reports no errors (65
files; `MurderInc.sh`, `BUILD.txt` and `MIDEV.key` at the top; no `Saved/` folder, no debug symbols, no logs).
`MurderInc.sh` in the zip is byte for byte the repository's, and `BUILD.txt` names commit `6c4d810` for the game and
the launcher.

The zip contains licensed content (the rifle animation pack, Epic's template content and the main character's
likeness): upload it only to E3DS, do not share the links.

### 9.1 The E3DS settings for version 3a

In the Control Panel: **Your Projects**, `Project_MurderInc`, **Settings** (the gear), tab **Viewer Experience**
(its **Search settings** box finds a setting by a word; turn **Advanced Options** on to see the Developer tab).
Nothing is kept until you press **Save changes**, and a change applies to new sessions only.

| Setting | Value | Why |
|---|---|---|
| Browser Resolution (Common) | **Custom**, both boxes filled: **1920** and **1080** | the game then always sends a 1920 x 1080 picture, which is what was tested. Dynamic (E3DS's default) makes the page ask the game for each player's window size; version 3a keeps such a request between 640 x 360 and 1920 x 1080, but small sizes are not finished (the next build) |
| Launch options (Developer) | **leave empty** | version 3a needs none: it chooses its own picture size and frame rate. Take out version 2's `-MICloudProbe=10 -PixelStreamingDecoupleFramerate`: decoupling makes a slow server repeat pictures |
| Unreal console commands to run at start (Developer) | **leave empty** | |
| Video Quality (Developer) | **Medium** | E3DS's default; a higher level can cost smoothness. Try High once play is smooth on an ordinary home connection |
| Codec (Developer) | **H264** | E3DS's default; every server card encodes it |
| Max Session Time (Common) | **15** minutes | a Story run takes about five minutes; a forgotten tab then costs at most 15 of the month's 300 |
| Log Out Automatically After Inactivity (Common) | **On**; countdown starts after **3**; countdown length **1** | both numbers are minutes |
| The mouse mode (search "mouse") | **Locked** | "Hovering" would stop the view turning at the edge of the picture |
| Platform; Select Region (Developer) | **Linux**; **Global** | |
| Print UE log in browser console (Developer) | **On** while you test, **Off** for the public | it shows the game's own lines in Chrome's console (F12) |
| Email To Send Log Upon App Crash (Developer) | **On**, your own address | |
| Password Protect Stream (Common) | **On** until launch | |

**The mouse.** With a fixed 1920 x 1080 picture the mouse speed is exactly the web game's when the picture is shown
1920 pixels wide (a 1080p monitor in full screen, or the Game OS page in a wide window). Shown smaller it turns
faster by the same factor (a third faster in a 1440-wide window). A player sets it with **Sensitivity** on the
game's Settings card (P, Settings); you can set it for everybody with the launch option `-MIMouseScale=` (section 7).

### 9.2 What to check, and what to send back

1. Open the link, click the **CLICK TO PLAY** card, start a Story run (Hit the block, Next three times, Hit the
   block) and play for a few minutes: turn fast, shoot, fight. Two quick clicks must fire two rounds and stop.
   (Expect silence: version 3a has no sound.)
2. Press **P** right after a moment that stuttered, or after a fast turn in a fight if nothing did, and **take a
   screenshot of the pause card**. The small grey line at the bottom of the card is the game's own report, for
   example:

   `NVIDIA GeForce RTX 4080 · 60 frames a second (lowest 58, target 60) · GPU 9.8 ms · drawn 1440 x 810, sent
   1920 x 1080 · stream 57 a second (lowest 50), 11.0 Mbit/s, QP 20, round trip 38 ms · build 6c4d810`

   | In the line | What it means |
   |---|---|
   | `NVIDIA …` | the graphics card of the E3DS server that ran your session |
   | `60 frames a second (lowest 58, target 60)` | pictures the game draws each second now; the lowest in the last half minute of play; the rate the game is aiming for (60, 45 or 30) |
   | `GPU 9.8 ms` | the time the card needs for one picture: 60 a second needs under 16.7 ms, 45 under 22.2, 30 under 33.3 |
   | `drawn 1440 x 810, sent 1920 x 1080` | the size the game draws at (it shrinks when the card is busy) and the size of the video |
   | `stream 57 a second (lowest 50), 11.0 Mbit/s, QP 20, round trip 38 ms` | the video as the server sends it: pictures a second and their lowest, the data rate, the compression (lower QP is sharper), and the time to your computer and back |
   | `build 6c4d810` | the build: version 3a must say `6c4d810` |

   The numbers in brackets ("lowest …") are the lowest of the last half minute of play; the numbers in front of
   them are of the moment the screenshot shows, so on the pause card the stream's number can be the lower one.
3. **Send back that screenshot**, with a sentence on how it felt (smooth or not, the mouse too fast or too slow, the
   answer to your hand late or immediate). One screenshot answers what no log could: the game's number low means
   the server's card is the limit; only the stream's number low with few megabits means the connection; a stream
   number a few below the game's with plenty of megabits is the server's video encoder (section 7 has the three
   cases).
4. With a controller: plug in a PS5 or Xbox pad, press a button on it, and play without touching the mouse or
   keyboard (section 7, "A controller alone"). On the Settings card choose **Controller: PlayStation** for the
   PlayStation names of the buttons.

### 9.3 What the game does on a slow server

Version 2 froze for seconds when the server's graphics card could not keep up. Version 3a never lets the card fall
behind, in three steps, by itself:

1. **It waits for the card.** A new picture is not started while the card still owes the game more than one. This
   alone ends the freezes, whatever the card.
2. **It draws a smaller picture** when the card is busy (down to half the size, sharpened back to 1920 x 1080).
3. **It lowers its rate** from 60 pictures a second to 45, and then to 30, when the card cannot hold the higher rate
   even with the smallest picture. It decides this in the first seconds of a run and goes back up only on a menu or
   the pause card.

So on a slow server you get a softer picture and a steady 45 or 30 pictures a second instead of 60 that freeze, and
the pause card's line says "target 45" or "target 30". On a fast server nothing changes: 60, at version 2's picture.
Measured on the GPU box with the zip of this section, unpacked and started the way E3DS does it
(`docs/unreal/PROGRESS.md`, "Version 3a: packaged, gated and delivered"): with the card free the game holds 60.0
pictures a second (lowest second 59.8). With the card slowed down so that one picture takes it 8, 12, 20 and 34 ms,
the game settles on 60, 60, 45 and 30 and holds them (lowest seconds 59.8, 59.8, 44.8 and 28.9); its longest single
picture in play is 37 ms, where version 2 under the heaviest of these loads froze for 1.7 seconds. The same on a
server with only 6 processor cores (38 ms).

**One pause you will see at the start of every session:** the first time the Crew screen appears (after "Hit the
block" on the home screen) the picture stands still for a little under a second. A server that has never run the
game compiles its graphics programs at that moment, and E3DS starts every session on such a server. It happens once,
on the menu, not in play; making it shorter is for the next build.

If your line says "target 30" (or the game's number is under 30), send it: E3DS support can say whether your
sessions can run on their faster cards, `-MIFps=30` (section 13) makes the rate steady from the first second, and
the next build lowers the lighting quality before it lowers the rate.

### 9.4 What is new in version 3a

- **The lag is gone on the GPU box** at every load tried (9.3). On E3DS it is your test that says so.
- **Mouse look** at the web game's speed, slow movements included (version 2 turned 2 to 3 times too fast and lost
  slow movements); a **double click** no longer leaves the gun firing.
- **A controller** works from the click card into a run and on the pause card: look, move, fire, menus, the
  buttons' names. (Played through the stream on the GPU box up to there; the cards at the end of a run are covered
  by the game's own tests, not yet by a play-through.)
- **The cards** (pause, settings, dead, debrief) take mouse clicks.
- **The pause card shows the game's numbers** (9.2), and the log gets them every 30 seconds.
- **Tuning without a new build**: launch options `-MIFps=`, `-MICVars=`, `-MIMouseScale=` (section 13).
- **Safer**: a visitor's console commands and size requests are limited (section 7), the debug switches are out of
  the normal game, and the Development game in the zip starts only with its key: `-MIDev=<key>`, the word in the
  file `MIDEV.key` at the top of the zip; it comes with the release report (section 13).
- Not yet in this build (the next one, "release B"): **sound** (version 3a is silent, as versions 1 and 2 were:
  the note at the top of this page), lower lighting quality on slow cards, the picture following each player's
  window (Browser Resolution Dynamic), a measured hand-to-picture delay, a smoother first minute after a cold
  start.

**The log** of every start goes to the file E3DS itself names when it starts the app (`-ABSLOG=`, the file its
crash-log email is taken from), to the launcher's output, and to `MurderInc/Saved/Logs/MurderInc.log` in the app's
folder. If it crashes, section 13 says how to get it.

## 10. What the cloud settings change

The game picks a **Cloud** graphics profile by itself when it runs in a stream. E3DS's own machines are RTX 4080 or
RTX 5070 class with 12 to 16 GB of graphics memory and 32 GB of memory (its "System requirements" page); it asks an
app to stay near 4 to 6 GB of graphics memory and 50 to 70 % of the card. Which card a Linux session really gets is
not published: from version 3 the pause card's line names it (section 9.2).

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
(other work shared the box's card). Either way the game stays **under 7 GB**: inside a 12 GB server card with room
to spare (it also ran on the box with only 7.6 GB of the card left free), and far under the 32 GB of memory.
Version 3a, measured again in its release check (one game alone on the box's card, 1920 x 1080): the card's counter
stands at 6.1 to 6.8 GB through a Story run and touched 7.2 GB for about 20 seconds in one run (a controller player
who went through the set-up screens in six seconds). That is a little over E3DS's "4 to 6 GB" advice and no problem
on a 12 or 16 GB card; with less memory free the game takes less (the runs above with 5.0 to 7.6 GB left free).

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
  use of the card, which is what E3DS asks of an app. Measured later on the GPU box, this saves little for this
  game: the smallest picture costs the card only 6 % less time than the largest (most of a frame's work, the
  lighting, the shadows and the geometry, does not depend on the picture's size);
- **lowers its frame-rate target from 60 to 45 and then 30** when the card cannot hold the higher rate even at the
  smallest picture (it decides this within the first seconds of a run, never on a menu), and raises it again only
  while no run is being played (on a card or a set-up screen, after ten seconds in which the card would have a
  fifth of the higher rate's frame time to spare). 30 steady frames a second on a slow card instead of 60 that
  freeze. This is the lever that counts on a slow card.

The pacing was first proven on the GPU box with 16 processor cores. A small cloud server has 8 or fewer, and Unreal
then collects the card's finished work differently: the first form of the pacing froze for a quarter of a second
per frame there. It was found in review, fixed, and the release check now also runs with the game held to 6 cores
(`docs/unreal/PROGRESS.md`, "Version 3, release A: the review's findings").

What you might notice on a slow server card: a softer picture, and 45 or 30 frames a second. On a fast one: nothing.
The pause card's small line says what the game settled on (section 7).

## 11. Prices (as researched on 2026-11-23: check eagle3dstreaming.com/pricing before you pay)

| Plan | Price | Streaming time | Players at once |
|---|---|---|---|
| Trial | free, no card | 60 minutes in total | 1 |
| Core | $29 a month (or $290 a year) | 300 minutes a month (unused minutes expire) | 10 |
| Extra minutes | $0.10 a minute, added in steps of 50 ($5) on the monthly plan (1,000 on the yearly) | | |
| Enterprise | custom, about $0.10 a minute | | up to 1,000, more regions |

One player for one hour uses 60 minutes, so beyond the included minutes it costs about **$6 per player-hour**.
**What is charged by itself and what is not** (E3DS's "Plans and billing" page, read 2026-11-25): the Core plan
renews automatically every month (or year) on the card on file until you cancel it. Going over is never charged:
when the month's minutes run out, streaming stops (a stream that is running is ended) until the next billing month
starts or you add minutes. Extra minutes you add are billed at once **and then again every month** until you lower
them (lowering applies from the next month). Servers: US and EU on Trial and Core; players go to the nearer one.

## 12. Making a new build later

Claude rebuilds the whole package with one command on the GPU box (`tools/box/cloud/package-cloud.sh all`: 5 minutes
on 2026-11-25 with a warm cache and the game already compiled, about 10 otherwise; on a freshly rented box the first
cook of version 2 with its SM5 shaders took about 20 minutes). Then, on the zip unpacked the way a host does it (a
new user, a fresh copy): the release gate (`tools/box/cloud/lag-gate.txt`, 13 runs, about 35 minutes: the game under
a loaded graphics card, on few processor cores, with a viewer that plays), the crash-cause checks
(`tools/box/cloud/e3ds-verify.sh`, about 20 minutes) and a play-through of the stream with mouse and keyboard and
with a controller (`proof-keys.txt`, `proof-pad.txt`). The box receives the stream with its own viewer program and
sends input through it; it cannot run a browser against the game, and it is not E3DS: the E3DS link (section 4) is
the last test. The new zip then goes, in parts, to your Higgsfield storage; you upload it to E3DS as a new version of
the build `MurderInc` (section 9, step 5) and test the link again.

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

1. **Browser console.** Keep **Print UE log in browser console** (Developer tab) on. Open Chrome's developer tools
   (**F12**, or **Cmd+Option+J** on a Mac) on the **Console** tab *before* opening the link, then play. If it
   crashes, right-click in the console and choose **Save as...**. E3DS does not say which file it prints; if the
   console shows nothing from the game, use 2 or 3.
2. **The crash email, and the Development game for a fuller log.** Of E3DS's log options on the **Developer** tab,
   **Email To Send Log Upon App Crash** is the one to use: as far as its documentation tells, it takes the log from
   the file E3DS names when it starts the app (`-ABSLOG=`), and the launcher writes that file for the normal game
   too. (E3DS's own documentation says of **Auto-Download UE Crash Log**: "not working at present".) For the full
   engine log with call stacks the zip carries a Development game beside the normal one: put **`-MIDev=<key>`** in
   the configuration's **launch options**, start the link again, and that session writes the engine's own log to
   `MurderInc/Saved/Logs/MurderInc.log`, where Development builds keep it. Take it out again afterwards (it keeps
   the developer console and checks on). **The key** (from version 3) is a word of 16 letters and digits that is new
   for every zip: it comes with the build's release notes, and it
   is the one line of the file `MIDEV.key` at the top of the zip. E3DS hands the game whatever a visitor writes after
   `?exeLaunchArgs=` on the stream link, and the Development game has the debug switches the normal game was built
   without (a switch that crashes it on purpose, the developer console); with the key no visitor can start it. A
   plain `-MIDev` or a wrong key starts the normal game and says so in the log. Do not put the key on a public page,
   and do not leave `-MIDev=<key>` in the launch options of the public configuration.
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
| `-MIDev=<key>` | run the Development game (full engine log, for E3DS's crash-log feature and support). The key is the word in `MIDEV.key` at the top of the zip (version 2: plain `-MIDev`) |
| `-MIMouseScale=<number>` | from version 3: mouse look speed through the stream (0.05 to 4; built-in 0.5). See section 7, "Mouse feel" |
| `-MIFps=60` (or `45`, `30`) | from version 3: fixes the frame-rate target instead of letting the game choose it by the card's time. `-MIFps=30` is the safe setting for a server that turns out to be slow |
| `-MICVars=name=value,name=value` | from version 3: sets console variables at start without a new build, each one printed in the log (`[MICloud] Launch option -MICVars: ...`). Only the variables of section 7's list. Examples: `-MICVars=r.DynamicRes.MinScreenPercentage=40` (allow a smaller picture), `-MICVars=MI.Cloud.GpuFramesInFlight=0` (the lowest delay at the cost of some frame rate on a slow card), `-MICVars=sg.GlobalIlluminationQuality=2,sg.ShadowQuality=2` (cheaper light and shadows) |
| `-MICloudProbe=<seconds>` | how often the game writes its line of numbers into the log (`MICloudProbe fps=... worstMs=... gpuMs=... target=... dr=... owed=...`); from version 3 every 30 s by itself, `0` turns it off |
| `-MIForceSM6` | skip Unreal's Vulkan SM6 check on a driver that fails it |
| `-MIKeepAlive` | from release 3c: the game does not idle and does not quit by itself when nobody watches (below). For the box's test scripts, which hold a game with no viewer on purpose; **leave it out on E3DS**, or an ended session's game stays on the machine again |
| `-MIIdleFps=<n>` and `-MIIdleAfter=<seconds>` | from release 3c: with nobody watching for 2 s the game draws 2 pictures a second (`-MIIdleFps=0` turns that off; the first viewer's start-up gets 10 s of grace) |
| `-MIExitAfterEmpty=<seconds>` | from release 3c: the game quits this long after the last viewer left (default 20; 0: never; how 20 was chosen: paragraph below) |
| `-MIExitIfNoViewer=<seconds>` | from release 3c: the game quits this long after it started if no viewer ever connected (default 600; 0: never) |
| `-MILauncherPid=<pid>` | from release 3c: given by `MurderInc.sh` itself (its own process id): the game quits 5 s after that process is gone. Not for the stream configuration |
| `-MIQpExact` | from release 3c: the video encoder gets exactly the quality numbers E3DS asks for (Medium QP 34, High QP 16, a constant quantiser), as before |
| `-MIQpBelow=<n>` and `-MIQpAbove=<n>` | from release 3c: how wide the range around E3DS's number is (default 10 below, not under QP 8, and 8 above, not over QP 48: Medium 34 gives 24 to 42, High 16 gives 8 to 24) |

**What the game does when nobody watches (release 3c).** E3DS does not stop the game of a session that has ended: the
next session on that machine found it still drawing and shared the card with it (27 pictures a second for the
second session, 18 for the third). Since release 3c the game looks after that itself, besides the launcher's own
clean-up at the start of the next session:

- With no viewer for 2 s it draws 2 pictures a second at the smallest size (an idle game costs the card almost
  nothing); a viewer who joins wakes it within a few hundredths of a second, and the click card shows as before. A
  game that has just started and has no first viewer yet gets 10 s of grace first.
- 20 s after the last viewer left, the game says so in its log and quits (exit code 0; the log line is
  `Session over: ...`). A viewer present keeps the game for as long as he stays, and a join cancels the countdown.
  **How 20 s was chosen.** Two things have to hold. (1) A page that is reloaded must not lose its game: on a host that
  keeps the game for a reloaded page (the box's test viewers, a signalling server of your own) the new connection is
  there in a few seconds (measured on the box with the test viewer: RELOAD_GAP), so 20 s is several times that. (2)
  A game that nobody will come back to must be gone before the next one is up: E3DS starts a **new** game for a
  reloaded page or a new session (its documentation, section 6 above) and the quickest start seen was 34 s, so the
  old game has to be gone well before that. 20 s sits between the two; `-MIExitAfterEmpty=` moves it (a host whose
  reload is slower can raise it, the cost is a game that stays that much longer), and `-MIKeepAlive` turns it off.
- A game that no viewer ever connected to quits 600 s after it started, and a game whose launcher is gone (E3DS killed
  it) quits 5 s after that.
- The video encoder gets a **range**, not the one quality number E3DS asks for: Medium (QP 34) gives it 24 to 42,
  High (QP 16) gives 8 to 24, so that the sender can pick the quality the connection carries instead of dropping
  frames when it carries less. On a fast connection the picture is as sharp as the range allows (and uses more data:
  up to E3DS's own limit of 20 Mbit/s in fast turns); on a thin one it gets softer instead of freezing.
  `-MIQpExact` gives the old behaviour. The pause card's line shows the range after the QP (`QP 31 of 24 to 42`).
- The pause card's round trip is the median of the last measured values, and absent when none was measured. On E3DS
  it is the time to the other end of the game's video connection, which may be E3DS's own relay on the machine and
  not your computer: E3DS's Info panel has the time to your computer.
