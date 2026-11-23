# Putting MURDER INC. on the IPX.exchange Game OS page

The game runs on a graphics server at **Eagle 3D Streaming (E3DS)** and streams into the web page as video; the
player's mouse, keyboard and gamepad go back to it. Nobody installs anything. This page is everything you do, in
order. Plan about an hour for the first time, most of it waiting for uploads.

**Before anything else, know the one big risk.** The game is built with **Unreal Engine 5.9, which is still a
preview version**. E3DS lists support up to 5.8 for the original streaming plugin and "5.7 and later" for the new one
(Pixel Streaming 2, which we use), and it does **not** test Linux uploads before you stream them. So the free trial
is the real test: do steps 1 to 6 on the trial before paying for anything.

## What you need

- The game file: **`MurderInc-E3DS.zip`** (about {{ZIP_SIZE}}), in your Higgsfield storage (private links in
  section 9). If it is in several parts, join them first (section 9).
- Google Chrome or Microsoft Edge (Safari cannot lock the mouse and keyboard to the game).
- About 2 GB of upload; a wired connection helps.

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
4. Choose `MurderInc-E3DS.zip` and upload it. The upload is checked only for the streaming plugin's files; if it is
   refused at this point, see section 8.

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
   Linux server warm): expect **{{START_HINT}}**; E3DS gives up after 3 minutes.
2. You see the game's home screen under a card that says **CLICK TO PLAY**. Click once. That click:
   - locks the mouse to the game (mouse look),
   - starts the sound (browsers keep sound off until you click),
   - hides the card. It does not press anything in the menus.
3. Check, in this order: the menus answer the mouse and keyboard; **Gear Up** goes through crew, loadout, block and
   briefing into a run; mouse look turns the view smoothly; W A S D moves; left click fires and you **hear** it;
   **P** pauses and resumes (see the box below); a gamepad plugged into your computer moves and aims.
4. Close the tab. The game pauses by itself when the last viewer leaves.

> **Esc and P.** In a browser, Esc belongs to the browser: it gives the mouse back to you and may never reach the
> game. So **P pauses** (Esc also works when the browser passes it on, and Start on a gamepad). The click card and
> the pause screen say so. To take the mouse again after Esc, click the game.

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
- [ ] The picture stays smooth for 10 minutes (no "Out of video memory" stop): the cloud settings are made for this
      (section 10).
- [ ] Max session time and idle logout are set (section 3), so minutes are not wasted.
- [ ] Read E3DS's terms of service for a violent shooter, and add an age note on the page if you want one.
- [ ] Decide the plan (section 11) and how many players may play at once; extra players wait in E3DS's queue.
- [ ] Mouse feel: if the view turns faster or slower than expected, set the stream's resolution to **match the
      browser window** in E3DS (section 10 explains why).

## 8. If E3DS rejects the build or it never starts

1. **Rejected at upload** ("no Pixel Streaming plugin" or a version message): send E3DS support the zip name and say
   it is an Unreal 5.9 Linux build with Pixel Streaming 2 (the plugin is in
   `Engine/Plugins/Media/PixelStreaming2` inside the zip). Ask whether 5.9 builds are accepted yet.
2. **Uploads but the stream never starts**: check that the configuration's platform is "Linux UE Build for PS" and
   the app name is exactly `MurderInc`, then try once more (first Linux starts are slow). If it still fails, ask E3DS
   support for the app's log.
3. **The fallback: Amazon GameLift Streams.** It runs any Linux program (no streaming plugin needed, so the engine
   version does not matter) on its Ubuntu 22.04 runtime. The costs and the work are different: you need an AWS
   account and a GPU quota increase, it bills for every hour a server is reserved whether anyone plays or not
   (about $0.50 an hour for a T4 server holding two players, in Oregon), and somebody must build a small website
   service that starts sessions; there is no ready-made embed link. Gamepads may not work there. Ask Claude to
   prepare the GameLift package if E3DS does not work out.

## 9. Getting the file

The zip is in your Higgsfield storage, private to your account: {{PACKAGE_LINKS}}

{{JOIN_NOTE}}

Check that the file is complete: on a Mac, open Terminal and run `shasum -a 256 MurderInc-E3DS.zip`; the result must
be `{{SHA256}}`.

The zip contains licensed content (the rifle animation pack, Epic's template content and the main character's
likeness): upload it only to E3DS, do not share the links.

## 10. What the cloud settings change

The game picks a **Cloud** graphics profile by itself when it runs in a stream. E3DS's servers have 8 or 16 GB of
graphics memory (RTX 4080 or 5070 class) and 32 GB of memory; their own advice is to stay near 4 to 6 GB.

{{CLOUD_TABLE}}

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

Claude rebuilds the whole package with one command on the GPU box (`tools/box/cloud/package-cloud.sh all`, about
{{PACKAGE_MIN}} minutes), tests it through a stream on the box (`tools/box/cloud/stream-test.sh`), and puts the new
zip in your Higgsfield storage. You then upload it to E3DS as a new version (section 2) and test the link again.
