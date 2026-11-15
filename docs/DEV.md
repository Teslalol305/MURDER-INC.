# MURDER INC. — developer guide

`docs/DESIGN.md` says what the game is, `docs/CONTRACT.md` what every module must expose; this is the practical
side: building, running, testing, extending. Everything here was run against the stubbed foundation.

## Build

```
node build.mjs                    production: dist/index.html (standalone, 0.8 MB) + dist/artifact.html (page fragment)
node build.mjs --dev              unminified, inline source map (5 MB), event payloads checked against the contract
node build.mjs --dev --only=level,atmos --out=dist/dev-level.html     these real, every other optional module stubbed
node build.mjs --dev --stub=audio,fx                                  everything real except these
node --test test/                 unit tests (pure logic; `test/<you>-*.test.js` is picked up automatically)
```

- Optional modules: `mats props input level atmos fx audio player explosives weapon enemies hud menus game`.
  `render`, `physics`, `combat` are always real. Build to your own `--out=dist/dev-<you>.html` (git-ignored).
- The build prints which modules are real and which are stubbed. A module without a `src/<name>.js` is stubbed
  whatever the flags say (`--only=level,atmos` works before atmos exists, with a warning).
- `dist/artifact.html` (`--artifact[=file]` writes it for any build) has no doctype / html / head / body: its host
  wraps it. It loads three.js r160 from cdnjs, then jsDelivr, then unpkg, and shows "Murder Inc. could not start: …"
  if all three fail. CSS is `src/base.css` + `src/ui.css` + `src/input.css`, in that order (missing files are skipped).

## How stubs are swapped

- **Build time**: `src/modules.js` imports every optional module twice, `./<name>.js` and `./stubs/<name>.js`;
  build.mjs redirects the first import to the stub when the module is stubbed. Never edit `modules.js` for this.
- **Boot**: if a real factory throws, rejects, returns nothing or has the wrong export name, the error is logged
  (`[boot] <name> failed, its stub takes over`) and the stub runs instead. A failing `render`, `physics`, `combat`
  or stub is fatal: the message stays on the boot screen and in `__fatal`. `?noaudio=1` forces the audio stub.
- **Run time**: an `update()` that throws is logged once (`[loop] <name>.update threw`) and the loop goes on.
- Which stubs are running: `__stats().stubbed` (build-time stubs plus boot fallbacks) and `G.build.stubbed`.

## Writing a module

1. Create `src/<name>.js` with `export function create<Name>(G) { …; return api }` (may be `async`). It replaces
   `src/stubs/<name>.js` in every build from then on. Read that stub first: it is the smallest correct
   implementation of your API and shows the conventions other modules already rely on.
2. Boot order is the `MODULES` list in `src/modules.js`: use modules above yours while being created, modules
   below yours only inside `update()` or event handlers. Add your own objects to `G.scene` / `#ui` yourself.
3. `src/core/contract.js` is the contract as data. At boot every module is checked against its member list, in
   dev builds every emitted event against its payload keys. A gap is a console error starting with `[contract]`,
   which lands in `__errors` and fails a harness run: expose the whole API first, fill it in later.
4. A new module name (rare) needs `src/stubs/<name>.js`, imports + a `MODULES` entry + an `UPDATE` group in
   `src/modules.js`, `OPTIONAL` in `build.mjs`, a member list in `src/core/contract.js` and a CONTRACT section.

## The harness: tools/shot.cjs

```
node tools/shot.cjs dist/dev-you.html --params "autostart=1&q=low&god=1" --scenario tools/scenarios/you-walk.cjs
node tools/shot.cjs dist/artifact.html --artifact-cdn [--cdn-fail N]      the fragment, three.js served locally
```

Options: `--params`, `--size WxH` (960x540), `--frames N`, `--skip N`, `--scenario file`, `--out file`, `--timeout S`,
`--realtime`, `--verbose`. It prints `__errors`, `__fatal` and `__stats()` as JSON and exits 1 on any page error. The page
runs with `step=1&dt=0.0333`: nothing moves between your calls, so a run repeats exactly. Undrawn steps are nearly
free (over 100 000 a second); a drawn frame costs 0.1 to 0.6 s in software GL, in bursts.

Scenario helpers: `h.frames(n)` drawn frames · `h.skip(n)` undrawn steps · `h.shot(path)` · `h.eval(fn, arg)` ·
`h.key(code, down)` (`'KeyW'`, `'Space'`, `'Mouse0'` …) · `h.mouse(dx, dy)` · `h.click(selector)` · `h.errors()` ·
`h.stats()` · `h.heap(collect)` · `h.wait(ms)` · `h.page` (Playwright). Two patterns cover most needs:

```js
// As a player: keys, mouse, a picture, a check.
module.exports = async (page, h) => {
  await page.mouse.move(480, 270); // park the pointer where 'Mouse0' presses, or that press turns the view
  await h.key('KeyW', true);
  await h.skip(60); // two seconds of walking, not drawn
  await h.key('KeyW', false);
  await h.mouse(-200, 20); // pixels: 200 left, 20 down (single events over 400 px are dropped as glitches)
  await h.key('Mouse0', true);
  await h.frames(3); // drawn frames, only where a picture needs them
  await h.shot('shots/you/firing.png');
  await h.key('Mouse0', false);
  const s = await h.eval(() => ({ shots: __G.combat.stats.shots, x: __G.player.pos.x }));
  if (s.shots === 0 || s.x < -34) throw new Error(`nothing happened: ${JSON.stringify(s)}`);
};
```

```js
// As a director: arrange a situation through window.__G, look at it from outside.
module.exports = async (page, h) => {
  await h.eval(() => {
    const G = window.__G;
    G.enemies.clear();
    G.enemies.spawn('goon', new G.THREE.Vector3(-30, 0, 2), { alerted: true });
    G.game.debugGrab(); // reel 1 is secured: its reinforcement wave is on the way
  });
  await h.skip(240); // eight seconds later
  await h.eval(() => window.__setShot({ cam: '-10,17,28,-4,1,-3', fov: 60 })); // cam: '' gives the view back
  await h.frames(2);
  await h.shot('shots/you/wave.png');
  const s = await h.stats();
  if (s.enemies < 8) throw new Error(`the wave did not arrive: ${s.enemies} enemies`);
};
```

In `tools/scenarios/` (run lines in each header): `foundation-example` (every helper once), `foundation-post` (the
renderer), `physics-stubs` (23 movement and combat checks), `foundation-slice` (a bot plays the whole stubbed game
from the title screen: 59 checks, a minute), `foundation-perf` (draw calls, step cost, garbage per step, nav rebuilds).

## Debug globals and URL parameters

| Global | |
|---|---|
| `__G` | the shared game object: `__G.game.state`, `__G.player.pos`, `__G.combat.stats`, `__G.build` … |
| `__errors`, `__fatal` | every `console.error` and uncaught error (200 at most); the fatal boot message or null |
| `__stats()` | draw calls, triangles, programs, internal size, quality, state, player, enemies, `stubbed`, error count |
| `__setShot({cam, fov, exposure})` | fixed outside camera `"x,y,z,lx,ly,lz"` (hides the viewmodel); `''` releases a key |
| `__ready`, `__frames`, `__step`, `__skip` | true after the 2nd drawn frame; steps so far; with `step=1`, drawn / undrawn steps left to run |

| Parameter | |
|---|---|
| `autostart=1`, `mode=holdout` | skip title and intro; start Hold the Block (only with autostart or shot) |
| `shot=1` | autostart + quality `test` + shadows every frame + no dynamic resolution |
| `q=test\|low\|medium\|high\|ultra` | force a quality preset (and stop automatic drops) |
| `seed`, `eseed` | world RNG seed (default 1994); enemy seed for the real enemies module |
| `god=1`, `noaudio=1`, `nohud=1` | player takes no damage; audio stub; hide the whole `#ui` layer |
| `cam=x,y,z,lx,ly,lz`, `fov`, `exposure` | fixed camera, field of view, exposure multiplier |
| `post=0`, `bloom=0`, `dynres=0`, `step=1`, `dt=0.0333` | forward path; no bloom; no dynamic resolution; advance only on request; fixed timestep |

## Pitfalls (all of these were hit)

- **Step mode timing.** `game.update` runs before `player.update` (it sees a new facing one step later) and the stub
  HUD rebuilds its text every 0.1 s: skip a few steps before reading a result. `fps` / `frameMs` mean nothing in step
  mode; use `--realtime` for frame times.
- **The pointer.** `h.click()` and `h.key('Mouse0')` move the real pointer, and while the mouse is captured that
  turns the view: park it first. Capture is asynchronous: wait for `__G.input.locked` after a click that starts a run.
- **Viewmodel.** `G.vmCamera` is a child of `G.vmScene` and copies the world camera every frame. Parent the weapon
  rig to `G.vmCamera` to work in view space. main.js owns `G.vmScene.visible` (off under `?cam`): hide your own group.
- **`G.time.t` never stops**, not on the title screen and not while paused. Keep your own clock for gameplay.
- **Physics.** Boxes are immutable (remove and re-add). A ray ignores a box that contains its origin: shoot from the
  eye, not from a muzzle that may poke into cover. Changing a nav-blocking box makes the next nav query rebuild the grid
  (0.3 ms; `physics.nav.rebuilds` counts). `raycast`, `moveCapsule`, `nav.findPath` take a result object to reuse as last argument.
- **Combat.** Keep each explosive's collider in `item.box` (or give it `owner: item`): a round that stops on it is a
  hit on the item. Remove the collider before `combat.explode` and pass the item as `source`. `enemies.damage()` must
  return `{killed}`; `from` is `'player'`, the shooting enemy, or `'blast'`. A hit on the player emits `player:hit`, not `impact`.
- **Garbage you cannot see.** V8 boxes a double on the heap when it crosses a non-inlined call (argument or result) or
  is written to a closure variable, and a loop variable seeded from such an argument boxes every value assigned to it: one
  ray cast made 2 kB that way. In hot code use `+x` or a `Float64Array` (`ray` in `src/physics.js`); measure with `foundation-perf`.
- **Materials.** Metallic materials are black without `render.setEnvironment()`. three.js draws a transparent
  `DoubleSide` material twice and rebuilds its program parameters every frame: set `forceSinglePass = true` or use
  an alpha-tested cut-out. Never add lights after boot (`render.lights.flash` / `acquire`: 6 pooled, 4 may be held).
- **Boot waits.** An `async` factory that never resolves leaves the boot screen up for good: bound every wait
  (fonts: 1.5 s) and never wait for a user gesture (`AudioContext.resume()`); start sound from `audio.unlock()`.
- **Stub conventions the real modules inherit.** `objective:done.index` is the number of reels secured so far (waves:
  `{id: 'wave', index: n, total: n}`); the card data for `menus.show('dead' | 'complete', data)` is at the top of
  `src/stubs/menus.js`; `mats.drawIPX` takes the centre of the mark and returns its width; `G.config.<file>` is that
  file's exports (`G.config.catalog.PROPS`). Stack traces point into the built HTML: open a dev build to see sources.

- `window.gc()` is exposed to the page only for scenarios whose file name contains `perf`, `stress` or `heap`, or with
  `SHOT_GC=1`: with that flag on, V8 lets dead typed arrays pile up to gigabytes while audio renders its buffers, and a
  full-build page (about 2.5–3 GB in software GL) gets killed. Run full-build sessions one at a time.
