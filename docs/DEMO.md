# Playing the MURDER INC. demo from your Mac

The Unreal game runs on the rented graphics computer (the "box") and you play it in a browser tab: the box sends
you the picture, your keyboard and mouse go back to it. Nothing is installed on your Mac.

## 1. Open it

1. **Ask Claude to start the demo** (for example: "start the game demo"). Claude wakes the box if it is asleep
   (about 5 to 10 minutes from cold, under a minute if it is awake), runs `tools/box/demo/start.sh`, and shows you a
   **Computer** card.
2. Click **Open desktop** on that card. A desktop opens in a new browser tab with the game on it, on its home
   screen. Use **Google Chrome** (or Edge): Safari cannot lock the keyboard, so Esc would throw you out of the game
   view.
3. Press **Control + Shift + X** (Control, not Command). The tab goes full screen and the mouse and keyboard lock
   onto the game: this is "gaming mode". Press **Control + Shift + X** again to get your mouse back.
4. If the game is not on the screen (you quit it, or the picture looks cut off after you resized the window),
   double-click the **MURDER INC.** icon on the desktop: it restarts the game at the current window size in about
   half a minute.

Keep the Open desktop link to yourself: whoever has it controls the whole desktop of the box (see section 6).

## 2. Controls

| Do | Keyboard and mouse |
|---|---|
| Move, sprint, crouch | W A S D, Shift, C |
| Look, fire, aim | Mouse, left button, right button |
| Reload, melee | R, F |
| Weapons | 1 2 3 4, Q for the last gun |
| Grab a reel, use | Hold E |
| Pause, menus | Esc (in gaming mode; otherwise use the on-screen buttons) |

The menus also work with the mouse alone. A **gamepad does not work through the browser stream**: the box's
streaming service has its gamepad input switched off. The game itself supports one.

## 3. What to show (about 10 minutes)

1. **Home screen**: the title over the block, Story or Hold the Block, difficulty, day or night.
2. **Gear Up**: pick a crew member, pick up to four guns, open the workbench and add attachments (scope, grip,
   magazine), pick the block and the style. The set-up is remembered for the next run.
3. **Hit the Block (Story)**: first person with the tattooed arms and the pack rifle. Aim down the sights, reload
   (the magazine drops on an empty reload), switch guns, fight the Goons, blow a propane tank, take back the three
   master reels, and carry them to the IPX truck to extract.
4. **Hold the Block**: survive the waves on the same street.

## 4. How it runs

- Picture: full HD (1920 x 1080) or your browser window's size, at up to 60 frames a second. Measured on the box:
  see `docs/unreal/PROGRESS.md`, section "Demo build".
- Delay between your mouse and the picture: the game's own share is measured in PROGRESS; the trip to the box and
  back adds your internet delay on top (the box is in a data centre, so expect it to feel like a good cloud-gaming
  service, not like a local game).
- **No sound in the browser.** The game plays its sound on the box, but the box's streaming service is set up
  without sound. Show the voice lines and effects from a recorded video, or ask for sound to be turned on in the
  stream (it is a setting of the rental, not of the game).

## 5. How long it stays up, and the cost

- The box costs **about 114 credits an hour** (RTX PRO 6000, 16 cores, 64 GB), billed by the second while it runs.
- It **switches itself off after 10 minutes with nobody using it** (no keyboard or mouse on the desktop and no
  Claude command). Playing keeps it on. Your files and the game build are kept; the next start takes a few minutes.
- To end early, tell Claude "stop the box".
- Other Claude work running on the same box at the same time (an Unreal editor) shares the graphics card and lowers
  the frame rate: say "nothing else on the box during the demo" when you ask for it.

## 6. What is reachable from the internet

Only the box's own desktop page (the Open desktop link). It is private to your Higgsfield account and carries a
secret token, but it is a **whole desktop**: whoever opens it can use the game and also the box's terminal and
files. Do not paste it into a public chat. No other port, game server or tunnel is opened for the demo.

## 7. For Claude: the commands

On the box (through `gpu_rental_exec`, as root):

| What | Command |
|---|---|
| Start the game on the desktop | `bash /project/ue/demo/tools/start.sh` |
| Stop it | `bash /project/ue/demo/tools/stop.sh` |
| Rebuild the package from the gameplay clone | `bash /project/ue/demo/tools/package.sh snapshot`, then `package.sh start`, poll `package.sh status` |

The scripts live in `tools/box/demo/` and are copied to `/project/ue/demo/tools/` from the pushed branch. The
package (`/project/ue/demo/build/Linux`) contains licensed pack and Epic content: it stays on the box, it is never
committed or published.
