# Hand-off: putting MURDER INC. live on the IPX.exchange Game OS site (for Cursor)

The game itself is **finished and packaged**. Nothing in Unreal needs building to launch. What is left is:

1. Turn the ten downloaded parts into one zip and check it.
2. Upload that zip to Eagle 3D Streaming (E3DS) and make a stream configuration. This gives a share link.
3. Embed that link on a Game OS page in the IPX website and deploy the site.

Steps 1 and 3 are code and terminal work, which Cursor can do in the IPX repository. Step 2 happens in the E3DS
Control Panel, in a browser.

## What Cursor cannot do

- **Rebuild the game.** That needs Unreal Engine 5.9, the GPU box and the licensed packs, which live on the
  Higgsfield GPU box and not in any repository. Any game change (art, gameplay, the "ESC Pause" text) goes back to
  the Claude Code session that built it. That session repackages the game, and you upload the new zip to E3DS as a
  new version.
- **Commit the zip or its links** anywhere public. They hold licensed pack content and the main character's
  likeness.

## Prompt to paste into Cursor (in the IPX website repository)

> We are adding the game MURDER INC. to the IPX.exchange Game OS website. The game is an Unreal Engine build that is
> streamed from Eagle 3D Streaming (E3DS) into the page with an iframe. Its full launch guide is
> `docs/LAUNCH.md` in the GitHub repo `teslalol305/murder-inc.` (branch `claude/tender-albattani-5q78qr`); read
> sections 2 to 7 and 9 first.
>
> 1. **Join the build (in a terminal, outside this repo, e.g. `~/murder-inc-build`)**: I will give you ten download
>    links (or the ten files I already downloaded). Download them, rename each to its part name by sha256 and join
>    them exactly as LAUNCH.md section 9 says. The joined `MurderInc-E3DS.zip` must have the sha256
>    `8378eedde07ce04510a654dee46032c7af6bc87b7fb37852b210d6af4e9e570a`. Do not put the zip, the parts or the links
>    in any git repository.
> 2. **E3DS**: I already have an account. Check E3DS's current documentation for an upload API or CLI. If there is
>    one, use it with credentials I enter myself (never ask me to paste a password into chat). If not, tell me the
>    exact Control Panel steps (LAUNCH.md sections 2 and 3): Platform Linux, app name exactly `MurderInc`, a
>    configuration on the Development tab with Advanced Options > Platform "Linux UE Build for PS", mouse mode
>    locked, 1920x1080, maximum session 30 minutes, idle logout 5 minutes. I will paste the share link back to you.
> 3. **The Game OS page**: in this repository, add a MURDER INC. game entry/page that follows the site's existing
>    Game OS patterns (routing, layout, game list, styling). Embed the stream as in LAUNCH.md section 5:
>    a 16:9 container, an iframe with `allow="autoplay; fullscreen; gamepad; pointer-lock; clipboard-read;
>    clipboard-write"` and `allowfullscreen`, focus on load and on mouse enter. Read the share link from an
>    environment variable or config rather than hard-coding it. Next to the player, add:
>    the controls (W A S D move, mouse aims, left click fires, **P pauses**: Esc gives the mouse back to the browser),
>    "If the picture freezes or says disconnected, reload the page to play again", and an age/violence note.
>    Make sure the site's Content-Security-Policy (`frame-src`) and any iframe sandboxing allow the E3DS domain and
>    pointer lock. Load the iframe only when the player presses a Play button on the page, so streaming minutes are
>    not spent on page views.
> 4. Run the site locally, test the page with the share link in Chrome and Edge (LAUNCH.md section 4 checklist),
>    then deploy through the site's normal deploy process. Report what you changed and the live URL.

## After it is live

- Go through the checklist in `docs/LAUNCH.md` section 7, on the live page.
- The trial has 60 minutes in total and one player at a time. Choose a plan (LAUNCH.md section 11) before you
  announce it.
- If E3DS rejects the upload or the stream never starts, follow LAUNCH.md section 8. Then bring what it said back
  to the Claude Code session.
