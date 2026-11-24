# Hand-off: putting MURDER INC. live on the IPX.exchange Game OS site (for Cursor)

Two jobs, two places:

1. **The game build goes to Eagle 3D Streaming (E3DS). The owner does this by hand** in E3DS's Control Panel:
   join the parts, upload the zip as a new version of the build `MurderInc`, set the project's settings, test the
   link. `docs/LAUNCH.md` sections 2 to 4 and 9 say how. Cursor never touches the build, E3DS's panel or any key.
2. **The website page is Cursor's**, in the IPX website repository: a MURDER INC. page that streams the game in an
   iframe, the site's headers, tests and deployment. The prompt below is everything Cursor needs.

A new version of the game (version 3 and later) is uploaded to E3DS as a new version of the same build: the
project's link stays the same, so nothing on the website changes.

## What Cursor cannot do

- **Rebuild the game.** That needs Unreal Engine 5.9, the GPU box and the licensed packs, which are not in any
  repository. Any game change goes back to the Claude Code session that built it.
- **Commit the zip or its download links** anywhere. They hold licensed pack content and the main character's
  likeness.

## Prompt to paste into Cursor (in the IPX website repository)

The same text is what the owner receives as a file. It was written from E3DS's own documentation by the launch
pre-flight (`docs/unreal/PREFLIGHT.md`, when present, explains each point).

> We are adding the game MURDER INC. to the IPX.exchange Game OS website. The game is an Unreal Engine 5.9 Linux build that runs on Eagle 3D Streaming (E3DS) servers and is streamed into our page in an iframe. Your job is only the website: the MURDER INC. page, its headers, its tests and its deployment. Do not download, join, upload or change the game build. Do not use any E3DS API, API key, login or Control Panel: I do all E3DS work myself, and whatever version I upload, nothing on the page changes. Never ask me for a password or a key.
>
> I will give you three things:
> (a) The Public Stream Link of the E3DS project, copied from the project itself. For this Linux build it starts with https://connector_linux.eagle3dstreaming.com/ or https://stream.eagle3dstreaming.com/.
> (b) The session limit in minutes that I set in E3DS.
> (c) Whether a test password is on.
> Until then, develop against E3DS's public Linux demo link, published on https://docs.eagle3dstreaming.com/wiki/linux-upload-and-stream/. It runs on E3DS's demo account, not on my minutes.
>
> 1. Where it lives
> - Add MURDER INC. to the Game OS game list with its own route. Follow the site's existing patterns for routing, layout, styling and the game list.
> - The E3DS iframe must be in the top-level document of that route. E3DS's Linux player sends every event with window.top.postMessage, so a page that is itself inside an iframe receives none of them. If the Game OS can only show a game inside its own iframe or window frame, do one of two things. Either open MURDER INC. as a full page. Or give that outer frame the same allow and allowfullscreen attributes as below, no sandbox, and pass E3DS's messages on from the top window to the game page.
> - Read these settings from the site's config or environment, never hard-coded. Use public variables, for example NEXT_PUBLIC_... in Next.js.
>   - MURDERINC_STREAM_URL: the stream link.
>   - MURDERINC_SESSION_MINUTES: default 15.
>   - MURDERINC_ENABLED: when false, the page says 'MURDER INC. is offline right now' and shows no Play button.
>   - MURDERINC_GAMEPAD: default false. When true, the controls text also shows the Controller line (aiming with a controller arrives with the next game build; I will tell you when to switch it on).
>   - MURDERINC_LISTED: when false, the page can be reached only by its address, is left out of the game list and carries <meta name="robots" content="noindex">.
> - Accept the stream URL only if it is https and its host ends with .eagle3dstreaming.com. Otherwise show 'not configured' and log why.
> - Tell me how to change each setting.
>
> 2. Headers
> Check every place the site sets headers: framework config (for example next.config headers() or middleware), vercel.json, netlify.toml or _headers, server or CDN rules, and <meta http-equiv="Content-Security-Policy"> tags.
> - Content-Security-Policy: add frame-src https://*.eagle3dstreaming.com and keep the existing sources. Do not list only connector.eagle3dstreaming.com. Do not write the connector_linux host itself: a CSP host may not contain an underscore, so that entry is ignored and the frame is blocked. The wildcard matches both the connector_linux. and the stream. hosts. If the policy has child-src or default-src but no frame-src, add frame-src anyway: frames fall back to child-src, then to default-src.
> - Permissions-Policy, if the site sends one: on this route, fullscreen, autoplay and gamepad must not be () or (self). Use (self "https://*.eagle3dstreaming.com") or leave them out.
> - No Cross-Origin-Embedder-Policy (require-corp or credentialless) on this route. E3DS's pages send no CORP or COEP headers, so the browser would refuse the frame.
> - No sandbox attribute on the iframe. A sandbox blocks the mouse lock and scripts.
>
> 3. The Play button and the iframe
> - Before Play, the 16:9 stage shows a poster and a Play button. The poster is an image I approve, or the title on black.
> - Never render the iframe on page load, on hover, during route prefetch or on the server. Every iframe load starts a session that reserves a server, and once the video runs it spends my minutes.
> - In the Play click handler, do this synchronously:
>   - Create the iframe.
>   - Set id="iframe_1", title="MURDER INC. game stream", allow="autoplay; fullscreen; gamepad" and allowfullscreen before you set src. The browser reads allow when the frame starts loading.
>   - Set border 0 and width and height 100%.
>   - Set src to MURDERINC_STREAM_URL, append the iframe and call frame.focus().
> - Do not add pointer-lock: it is not a real permission, and the mouse lock works in any frame without a sandbox. Do not add clipboard-read, clipboard-write, camera or microphone either.
> - allow="autoplay" together with the Play click should let Chrome, Edge and Firefox start the stream with sound, without another E3DS click. Safari shows E3DS's sound button instead.
> - In React or similar, create the iframe from state set in that click handler and give it a stable key. Make sure no later state change re-creates it: every re-creation is a new paid session. Double-mounting in development must not create two.
> - The stage: aspect-ratio 16/9, width min(100%, 1920px), centred, black. On Play, scroll it fully into view.
> - While a session runs, the page must not scroll: set overflow: hidden on html and body and restore it at the end. That way the mouse wheel (weapon switch) and Space (jump) never move the page.
>
> 4. Messages from the stream (window 'message' events)
> - Use a message only if new URL(event.origin).hostname matches /(^|\.)eagle3dstreaming\.com$/. event.data is usually an object. If it is a string, JSON.parse it inside try/catch. Ignore anything else.
> - What we send to the frame must be a JSON string: frame.contentWindow.postMessage(JSON.stringify({...}), '*').
> - E3DS's Linux player sends the older event names, and the dotted names in E3DS's documentation may never arrive. Handle both. Treat a repeat of the same event within 3 seconds as one event. Each line below reads: moment: old Linux name / documented name.
>   - waiting in line: stage1_inqueued (positionInQueue), QueueNumberUpdated (queuePosition) / session.queued, session.queuePositionChanged (queuePosition)
>   - server found: stage2_deQueued, stage3_slotOccupied / session.hostFound, session.hostReserved
>   - copying the game to the server: stage3_1_AppAcquiringProgress (percent) / build.acquiring (percent)
>   - unpacking: stage3_2_AppPreparationProgress (percent) / build.preparing (percent)
>   - starting: build.started
>   - ready, may wait for a click: stage4_playBtnShowedUp / stream.ready
>   - playing: stage5_playBtnPressed / stream.playing
>   - the game stopped: handleStreamerDisconnected / build.stopped, app.stopped
>   - time limit reached: sessionExpired / session.expired
>   - the video failed: videoStreamFailed / stream.failed
>   - error: Error_Redirect / session.error
>   - ended, always last: redirectingWithMessage and sessionEnding (message) / session.ending (message)
>   - password box: passwordRequested, passwordAccepted
>   - keyboard focus: streamFocusLost, streamFocusGained
>   - if they arrive: notice (show its message as a small note beside the stage), _focus (focus the frame), isIframe (reply JSON.stringify({cmd: 'isIframe', value: true})).
> - Show a status line beside or under the stage, never over it, with aria-live="polite":
>   - 'Waiting for a free game server: you are number N in line'
>   - 'Server found, starting'
>   - 'Copying the game to the server: N %' (Linux servers copy the whole game for every session; 1 to 3 minutes is normal)
>   - 'Unpacking: N %'
>   - 'Ready: click the picture'
>   - nothing while playing.
> - Nothing may cover the iframe while it is on the page. E3DS draws its own password box, queue screen, play button and inactivity countdown inside it, and the player must see and click them. If you want a loading layer over the frame, it needs pointer-events: none. It must go away on stage4_playBtnShowedUp, stage5_playBtnPressed, stream.ready, stream.playing, passwordRequested or session.error, and after 10 seconds in any case.
> - On passwordRequested, focus the frame so that typing goes into E3DS's password box.
> - If the stream becomes ready while the tab is hidden, set document.title to 'Ready: MURDER INC.' until the tab is visible again.
>
> 5. Ending sessions (this is what protects my minutes)
> - A 'Quit game' button beside the stage removes the iframe and shows the end screen. When the frame goes away, E3DS ends the session and frees the server.
> - Remove the iframe, never just hide it, when the visitor leaves the route or the page, or when the Game OS window is closed or minimised. Never keep it mounted with display: none or off-screen: it would keep running, spend minutes and hide the inactivity countdown.
> - If the tab stays hidden for 3 minutes, remove the iframe and show 'We stopped the game while you were away, to free the server. Press Play to start again.' The one exception: the visitor is still waiting in line.
> - On handleStreamerDisconnected, build.stopped or app.stopped, remove the iframe at once and show the 'stopped unexpectedly' text. Otherwise E3DS's player reloads itself after 3 seconds and starts another session.
> - On the ending event, and in all the cases above, remove the iframe and show our own end screen in the stage, with a 'Play again' button. Choose the words from the events you saw, never from the message text. Write E3DS's message only to console.info, never on the page: it can contain the account name or billing words.
>   - A password was asked and the game never played: 'The game did not start (a wrong or cancelled password ends it). Press Play to try again.'
>   - The game never played, for any other reason: 'MURDER INC. could not start right now (all game servers are busy, or the game is being updated). Please try again in a few minutes.'
>   - After sessionExpired or session.expired: 'Your session reached its N-minute limit. Press Play again for a new game.'
>   - After a 'game stopped' event: 'The game stopped unexpectedly. Press Play again to start a new game.'
>   - After videoStreamFailed or stream.failed: 'The video could not reach your browser. A school or office network can block it; try another network, then press Play again.'
>   - Otherwise: 'Your session has ended (for example after a few minutes without input). Press Play again for a new game.'
> - Never start a new session automatically. Do not copy E3DS's demo, which reloads on sessionExpired and stream.failed. 'Play again' creates a new iframe from its own click.
> - Watchdog: if a server was found but the stream is not playing 6 minutes after Play, and the password box is not showing, remove the iframe and show the 'could not start' text.
> - Allow one running game per browser, using BroadcastChannel or a localStorage lock. A second tab says 'MURDER INC. is already running in another tab.'
> - If the site has analytics, record Play clicks and which ending happened, by event name only.
>
> 6. Focus, keys and full screen
> - Focus the frame:
>   - on its load event, with setTimeout(() => frame.focus(), 0)
>   - on mouseenter
>   - when playing starts
>   - on _focus and streamFocusLost
>   - right after any page control is used (full screen, help, quit).
>   Never take focus from an input, select or textarea the visitor is typing in.
> - No page or Game OS shortcut may close, hide or minimise the game on Esc or another single key. In the stream, Esc only gives the mouse back to the browser.
> - Add a 'Full screen' button. In its click handler, call requestFullscreen() (or webkitRequestFullscreen()) on the stage element, then focus the frame. Hide the button where full screen is not available (iPhone).
>
> 7. Text beside the player
> - 'Press Play. Starting takes 1 to 3 minutes. When CLICK TO PLAY shows, click the picture once: that locks the mouse to the game and turns the sound on.'
> - Keyboard and mouse: Move W A S D · Look mouse · Fire left click · Aim right click · Reload R · Swap weapon Q, mouse wheel or 1 to 4 · Weapon wheel hold Q · Grab a reel hold E · Jump Space · Sprint Shift · Crouch C · Melee F · Fire mode B · Inspect T · Pause P. Esc gives the mouse back to the browser; click the game to take it again.
> - Only when MURDERINC_GAMEPAD is true: Controller: move and look with the sticks · Fire RT · Aim LT · Reload X (hold X at a reel to grab it) · Swap Y or D-pad · Jump A · Crouch B or LB · Sprint L3 · Melee RB or R3 · Pause Start. Click the game once first: browsers give a gamepad only to the frame that has focus.
> - 'A session lasts up to N minutes', with N from MURDERINC_SESSION_MINUTES.
> - 'After a few minutes without input a countdown appears in the picture: move the mouse or press a key to stay.'
> - 'If the picture freezes or says disconnected, press Play again (a new game starts).'
> - 'If aiming feels too fast or too slow, change Sensitivity in the game's settings (press P, then Settings; in the game's menus use the arrow keys and Enter).'
> - 'Best in Chrome or Edge on a computer; Safari and Firefox should work. When all game servers are busy you wait in line and see your place.'
> - An age note: 'Mature: strong violence and language. 17+.' I may change the wording.
>
> 8. Phones and tablets
> - If window.matchMedia('(any-pointer: fine)').matches is false (a touch-only device), show 'MURDER INC. needs a computer with a keyboard and mouse, or a gamepad' in place of the Play button, with a small 'Play anyway' link. An iPhone has no mouse lock and no full screen in a frame.
>
> 9. Test, deploy, report
> - Test with the demo link first and check all of these:
>   - The console shows no 'Refused to frame' or Permissions-Policy errors.
>   - The messages arrive and the status follows them. When the page is opened with ?debug=1, log each message with console.debug.
>   - Quit, leaving the route, a 3-minute hidden tab and a second tab behave as described.
>   - Nothing covers the frame.
>   - The page never scrolls during play.
>   - The deployed site sends the right response headers, not only the local one.
> - Then put my link in and make one short test: under 5 minutes, then Quit. Every minute counts against my 300 a month. Mouse lock, sound and gamepad need a person: I test them myself in Chrome, Edge, Safari and Firefox.
> - Deploy with MURDERINC_LISTED=false first. When my tests pass, I will ask you to set it to true.
> - Report the files and headers you changed, the live URL, how I switch the game off (MURDERINC_ENABLED=false) and how I change the link.

## After it is live

- The Core plan has **300 streaming minutes a month and 10 players at once**. Every session counts from the moment
  the video starts. The page's Quit button, the hidden-tab rule and E3DS's own limits (Max Session Time, the
  inactivity log-out) are what protect the minutes. Extra minutes, once bought, are billed every month until
  lowered.
- **Off switch**: `MURDERINC_ENABLED=false` on the site, or in E3DS the project's Streaming status: Disabled.
- Keep `MURDERINC_LISTED=false` and the E3DS password on until the owner has played on the live page in Chrome,
  Edge, Safari and Firefox. Then: password off, listed true.
- If the stream never starts or stops by itself, `docs/LAUNCH.md` section 13 says how to get the log; bring it to
  the Claude Code session.
