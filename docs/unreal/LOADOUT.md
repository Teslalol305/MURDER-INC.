# Loadout: crew, four guns, attachments, block and style

The design an engineer implements next: from the home screen the player picks a **crew member**, a **loadout of up
to four guns** with **attachments**, a **level** and a **game style** (with difficulty and time of day), reads a
**briefing** and plays. Everything is data. Adding a gun means adding entries, and so does adding an attachment, a
crew member or a level.

| File | What it holds |
|---|---|
| `unreal/MurderInc/Content/Data/guns.json` | The roster: four guns, their rule numbers, presentation, mounts, art and clip status, and the clip roles (3.2, 5, 6.1) |
| `unreal/MurderInc/Content/Data/attachments.json` | Seven slots, the stats an attachment may change, thirteen attachments with their effects, and the per-gun compatibility table (3.3) |
| `unreal/MurderInc/Content/Data/crew.json` | Four crew members as looks on the same arms (3.4) |
| `unreal/MurderInc/Content/Data/levels.json` | Levels with what they provide, and modes with what they need (3.5) |
| `unreal/MurderInc/Content/Data/frontend.json` | Screens, transitions, the 3D stage, new inputs, the weapon wheel, the four-slot bar, the save schema (2, 4, 7) |
| `unreal/MurderInc/Content/Data/frontend_text.json` | Every new string, keyed as it will sit in `text.json` (2.12) |

Read with: `GAMEPLAY.md` (the code as built, whose class names this page uses), spec 02 (weapons), spec 04 (flow),
spec 07 (HUD and menus), `CHARACTERS.md` (the arms), and `ANIMATION.md` (being written: the pack's clips on the
mannequin). No file under `Source/` or any existing `Content/Data` file is changed by this design. Section 4.9 lists
the changes the engineer makes there.

---

## 0. The design on one page

- **The roster has four guns.** The **CHOPPER** and the **NINE** are unchanged. The **STICK** is the pack's carbine
  ("stick" is street for a rifle). Its three handguard lengths and two stock positions are attachments, so the whole
  pack is one gun with every build. The **RATTLER** is the Goon's submachine gun in the player's hands. The player
  carries up to four of them, in an order he chooses, plus melee.
- **Attachments** go in seven slots: optic, muzzle, underbarrel, laser, magazine, handguard, stock. There are
  thirteen parts, all from the pack. They fit the STICK, and also fit our own guns where a mount exists: a scope and
  a silencer on the CHOPPER, a laser on the NINE, a silencer on the RATTLER. Every part has a benefit and a cost, and
  each effect is a single legible number in data (3.3).
- **The crew has four members.** Rule plus three placeholder crew built on Rule's arms (DEUCE, SMOKE, KEYS). They
  are cosmetic. The radio and the death card say the chosen member's name.
- **The flow runs** Home → Crew → Loadout (⇄ Workbench) → Block (with time of day) → Style (with difficulty) →
  Briefing → intro. Back works everywhere. Every choice is saved. **Same set-up** on Home, Enter and gamepad Start
  start a run at once with the remembered set-up, which keeps the one-press start of the web title. **Change set-up**
  on the death and debrief cards opens the Loadout screen.
- **Parity holds.** The default set-up is Rule, the CHOPPER and the NINE with no attachments, on the block, in Story
  or Hold the Block. It resolves to exactly the `FMIWeaponsData` that `config.json` gives today. Every new rule field
  defaults to the web value, no new random draw is added, and every new input does nothing unless pressed. The
  golden tests replay through the new path unchanged (8.1).
- **Four guns in the rules.** `FMIWeaponRules` learns slots 1 to 4, a quick swap to the last gun used, next and
  previous, a wheel, per-gun holster and draw times, per-gun resupply and a semi/auto selector. The host learns damage
  falloff, a noise radius and the aimed field of view per gun (4).

---

## 1. Scope and parity

### 1.1 What is new

| Area | New |
|---|---|
| Front end | Six set-up screens inside the flow's `title` state, a 3D stage with a turntable, a saved set-up |
| Guns | STICK, RATTLER; carrying 1 to 4 guns; fire modes; inspect; magazine check |
| Attachments | 13 parts in 7 slots, a per-gun compatibility table, stat effects resolved before the run |
| Rules | Per-gun holster, draw, aimed field of view, aimed look scale, noise radius, damage falloff, resupply, fire modes; four-gun switching |
| Crew | Four looks on the same arms; radio and card lines with the crew member's name |
| Levels and modes | A data index of levels and modes, with a "needs / provides" check |

### 1.2 The parity set-up

`frontend.json parity`: crew `rule`, guns `[chopper, nine]`, no builds, level `block`, mode, difficulty and time
from the existing settings (defaults `mission`, `boss`, `day`). A first start uses it, and so does any saved set-up
that fails validation (7). With it, the run must be the web game frame for frame:

1. **Same data.** `FMILoadoutResolver` (3.7) returns `FMIWeaponsData` equal field by field to
   `UMIDataSubsystem::GetWeapons()`: the same guns in the same order (`weapons.common.order`), the same numbers, the
   same `Common` and `Melee`. Every new field of `FMIWeaponDef` equals the value the web code uses implicitly:
   - `Holster` and `Draw` = `common.holster` / `common.draw`
   - `AdsFov` = `player.fov.ads`
   - `AdsLook` = 1
   - `NoiseRadius` = `enemies.ai.hear.gunfire`
   - falloff start = end = +∞, min = 1
   - `FireModes` starts in `auto` for the CHOPPER (it may switch to semi, but only when pressed) and is `[semi]`
     for the NINE
   - resupply = `flow.holdout.resupply`
2. **Same arithmetic.** A default value never enters a formula in a way that changes a double. Falloff is skipped
   when the distance is at most the start (+∞), not multiplied by a computed 1. Per-gun holster and draw replace the
   common values in the same expressions.
3. **Same random draws.** No new draw from the `weapon` stream, nor any other. Effects are resolved before the run.
   The selector, inspect and magazine check use no randomness. The alternation of the two melee swings is presentation
   and uses a counter.
4. **Same inputs.** With two guns, the new meanings of Q, the wheel and the D-pad (4.2) pick exactly the gun the web
   game picked. Keys 3 and 4, B, T and View do nothing in the rules unless pressed. Inspect and magazine check never
   write rule state.
5. **Same events.** No new event fires in a parity run. The `weapon:fire` payload gains fields that the golden test
   does not compare (`NoiseRadius`, `bSuppressed`).
6. **Same picture where it matters.** The weapon bar shows two slots and the melee slot, as the web bar does. The
   radio, the cards and the HUD use the original `text.json` lines word for word for Rule.

### 1.3 Where this design departs from the brief

1. **Four slots, two guns in the default.** The brief says the player carries four guns *and* that the default set-up
   is the CHOPPER and the NINE. Both hold if a set-up may carry one to four guns. The default carries two, and the
   Loadout screen offers four slots. This is required for parity: with four guns, Q from the NINE would go to slot 3,
   not back to the CHOPPER. (Open question 2.)
2. **Handguard length trades handling against recoil and *accuracy at range*, not range.** The block is 92 × 68 m and
   every gun reaches 120 m or more, so a `range` change would never be felt. Long and short handguards change aimed
   spread, kick and a damage falloff past 25 m instead.
3. **Time of day sits on the Block screen.** It is a property of the place, and the stage behind the Block screen is
   the block itself, which switches between day and night live. Difficulty stays with the game style, as the brief
   says.
4. **The briefing is skipped by Same set-up.** One press from Home starts the run, as Enter did on the web title.

---

## 2. The flow

### 2.1 State diagram

Every set-up screen is a sub-screen of the flow's existing `title` state (spec 04 3.2). The flow's state machine, its
events and its golden values are untouched. A run still begins with `start()` (T2), and the run reset (spec 04 3.3)
reads the set-up instead of the fixed guns (4.9).

```mermaid
stateDiagram-v2
    state title {
        [*] --> Home
        Home --> Crew: Hit the block
        Crew --> Home: Back
        Crew --> Loadout: Next
        Loadout --> Crew: Back
        Loadout --> Workbench: Attachments (on a gun)
        Workbench --> Loadout: Done / Back
        Loadout --> Block: Next (at least one gun)
        Block --> Loadout: Back
        Block --> Style: Next
        Style --> Block: Back
        Style --> Briefing: Next
        Briefing --> Style: Back
        Briefing --> Crew: Change (crew line)
        Briefing --> Loadout: Change (loadout line)
        Briefing --> Block: Change (block line)
    }
    title --> intro: Hit the block (Briefing) / Same set-up, Enter, Start (Home)
    intro --> playing
    playing --> paused
    paused --> playing: Resume
    paused --> intro: Restart run (same set-up)
    intro --> dead
    playing --> dead
    playing --> complete: Story, at the truck
    dead --> intro: Run it back (same set-up)
    complete --> intro: Run it back (same set-up)
    dead --> title: Back to title (Home) / Change set-up (Loadout)
    complete --> title: Back to title (Home) / Change set-up (Loadout)
```

`Change set-up` first does what `toTitle()` does (spec 04 3.4), then opens the Loadout screen instead of Home. The
set-up is saved on every Next and on every start, so it is remembered whichever way the player leaves (edges with
`remember` in `frontend.json transitions`). The pause card has no way back to the set-up, as in the web game.

### 2.2 The frame every set-up screen shares

| Part | Rule |
|---|---|
| Layout | Letterbox bars and the left-to-right veil of the title (spec 07 4.4). The left 40 % holds the screen's controls; the rest shows the 3D stage (2.11). Safe zone and the HUD's scaling rule (spec 07 4.2) |
| Step strip | Top left: five route bullets (spec 07 2.3) numbered 1 to 5 in the line colours (`line1`, `line2`, `line3`, `lineIpx`, `gold`), labelled `frontend.steps.labels`. Done steps are filled; the current one has the focus ring; a done step can be clicked to jump back |
| Kicker and title | `frontend.<screen>.kicker` (small, `inkDim`, uppercase) over `frontend.<screen>.title` (display font) |
| Bottom bar | `Back` (quiet button, left, with its glyph: Esc / B) and `Next` (primary button, right, with Enter / A or Start). Next is disabled with its reason as a note when the screen is not complete (`frontend.loadout.needOne`) |
| Memory | Every screen opens with the saved choice selected and focused |
| Sound and focus | `ui_hover` and `ui_click` as on the title (spec 07 3.17); gamepad focus ring; the focus never leaves the screen |
| Reduced motion | The turntable does not spin by itself; camera moves cut instead of easing |

### 2.3 Home

**Shows:** The web title as it is (eyebrow, wordmark, star line, premise, `Settings`, `Controls`, the controls glance
strip, the fly-through behind it). The three pickers (Mode, Difficulty, Time) move to the Block and Style screens.
In their place:

- the primary button `Hit the block`, which opens Crew;
- the button `Same set-up`, with the summary line under it (`frontend.home.summary`, for example
  `RULE · CHOPPER / NINE · The Block · Story · Boss`), or `frontend.home.firstTime` before the first run.

**3D:** The title fly-through (spec 04 3.4), unchanged.

| Input | Mouse | Keyboard | Gamepad |
|---|---|---|---|
| Set-up flow | click `Hit the block` | Tab to it, Enter | focus it, A |
| Same set-up | click `Same set-up` | **Enter** with nothing focused (as the web title did) | **Start** (as the web title did), or focus it and A |
| Settings, Controls | click | Tab, Enter | focus, A |

**Texts:** `frontend.home.start`, `.same`, `.summary`, `.firstTime`; the rest are the existing `text.title.*`.

### 2.4 Crew

**Shows:** A row of crew cards in `crew.json order`, each with a portrait (a 2D card of the arms on the bench, never a
face), the name and the tagline. The note `frontend.crew.note` ("Looks only. Everybody shoots the same.") sits under
the row. A crew member whose art is missing still shows, with Rule's arms and its placeholder portrait (6.3).

**3D:** The stage camera `arms` (2.11). The chosen member's arms, in first-person framing, hold the first carried gun
and loop its `Inspect` clip, so the gloves, sleeves and jewellery turn in the light. When the choice changes, the
arms swap behind a 0.15 s dip to black. Dragging orbits the camera up to 35°.

| Input | Mouse | Keyboard | Gamepad |
|---|---|---|---|
| Choose | click a card | Left / Right | D-pad or stick left / right |
| Orbit | drag the stage | none | right stick |
| Next | Next | Enter | A or Start |
| Back | Back, right-click | Esc | B |

**Texts:** `frontend.crew.kicker`, `.title`, `.note`, `.<id>.name`, `.<id>.tagline`.

### 2.5 Loadout (the rack)

**Shows:**

- **Left, the rack:** class tabs (`All`, `Rifles`, `SMGs`, `Pistols`, `New`; `frontend.loadout.filters`). Under
  them is a grid of gun cards, three columns wide, which scrolls when there are more than twelve. Each card shows:
  - the silhouette;
  - the name and the class;
  - six stat bars (Damage, Rate, Control, Handling, Aimed, Hip fire; see the formulas below), computed from the
    gun's *current build*, so a built gun reads truthfully;
  - the magazine (or `∞` reserve) and `SEMI` for a semi-only gun;
  - the number of attachment slots (`frontend.loadout.slots`);
  - a wrench button that opens the Workbench;
  - `NEW` until the player has focused the card once (save `seen`).

  A carried gun shows `Carried · slot n` and stays selectable: selecting it focuses its slot. The tab row is what
  makes a roster of forty usable: each pack adds one rifle, and the class tabs, the scroll and `New` find it.
- **Right, the four slots**, top to bottom, `Slot 1` to `Slot 4`. Each shows the carried gun's silhouette, name,
  attachment pips and key glyph (1 to 4), or `Empty` with `Pick a gun from the rack`. The fixed melee slot
  (`text.weapons.melee.<gun of slot 1>`) sits below them.
- `Carry up to four. Melee comes with you.` above the slots. `All four slots are full: pick a slot to swap out`
  appears when the player picks a gun with every slot full.

**3D:** The turntable (2.11) shows the focused gun (the focused card, else the focused slot) with its build, slowly
spinning. Changing the focus swaps the gun with a 0.2 s scale-out and scale-in on the turntable.

**Rules of the slots** (`frontend.json carry`): from one to four guns; no duplicates; slots always fill 1..n with no
gap (emptying slot 2 of three moves slot 3 up). Next is disabled with `Carry at least one gun` at zero.

| Input | Mouse | Keyboard | Gamepad |
|---|---|---|---|
| Carry a gun | click its card: it goes in the first empty slot; with all four full, in the selected slot | Enter on the card | A on the card |
| Put in a given slot | drag the card onto the slot | 1, 2, 3, 4 on the focused card | select the slot (A), then A on a card |
| Reorder | drag a slot onto another (they swap) | Shift + Up / Down on a slot | LB / RB on a slot |
| Empty a slot | right-click it | Delete | X |
| Attachments | the wrench, or double-click a slot | Space | Y |
| Turn, zoom | drag, wheel | none | right stick, LT / RT |
| Switch panes | none | Tab | D-pad across |
| Next / Back | buttons | Enter on Next / Esc | Start / B |

Stat bars (`frontend.loadout.stats`). Each fills from 0 to 1 and is clamped. The units are those of `config.json`.

| Bar | Fill |
|---|---|
| Damage | damage / 40 |
| Rate | rpm / 900 (a semi-only gun shows `SEMI` and the bar for its rpm) |
| Control | 1 − (recoil.pitch − 0.002) / 0.008 |
| Handling | 1 − (adsTime − 0.10) / 0.25, averaged with 1 − (draw − 0.2) / 0.25 |
| Aimed | 1 − (spread.ads − 0.0005) / 0.0035 |
| Hip fire | 1 − (spread.hip − 0.006) / 0.010 |

**Texts:** `frontend.loadout.*` (kicker, title, carry, slot, empty, emptyHint, carried, needOne, full, attachments,
remove, move, new, filters, classes, stats, slots, noSlots); gun names and blurbs (`text.weapons.*` and
`frontend.weapons.*`).

### 2.6 Workbench (attachments)

Opened from the rack for one gun. It edits the build of a gun whether or not that gun is carried; builds are kept
per gun (7).

**Shows:**

- A title, `Build the {gun}`, with arrows (and a strip of the carried guns) to move to the previous or next carried
  gun without leaving the screen.
- **Slot tabs**, only those the gun has (`attachments.json compatibility.<gun>`), in slot order.
- **The options of the chosen slot:** `Factory` (when the slot is not `required`, with its note "What it came with.
  No change.") and each compatible attachment, with its name and its blurb in the game's voice.
- **For the focused option**, its effect lines, generated from data (`frontend.effects.*`: `+35% aim time`,
  `Heard 18 m out`, `Damage drops past 25 m`). Each line is green when better and red when worse, by the stat's
  `better`. A neutral line (the scope's `Aimed view 30°`) is `ink`. The panel also compares the six stat bars, before
  and after, as ghost and fill.
- `Fitted` on the option in use, and `Reset build` (every slot back to its `default`).

**3D:** The turntable gun with the build. Choosing a slot tab eases the camera to that slot's focus (`frontend.json
stage.cameras.focus`, 0.4 s). Focusing an option previews it on the gun at once, before it is fitted, with a 0.25 s
slide into its socket. Leaving the option without fitting puts the fitted part back. Fitting an underbarrel plays the
hands' `GripChange` clip on the arms when the stage shows them (the Workbench shows the gun alone). The irons fold
down when an optic is fitted.

| Input | Mouse | Keyboard | Gamepad |
|---|---|---|---|
| Slot | click a tab | Left / Right | D-pad left / right |
| Option | hover previews, click fits | Up / Down previews, Enter fits | D-pad up / down previews, A fits |
| Factory part | click `Factory` | Backspace | X |
| Previous / next gun | the arrows, the strip | Q / E | LB / RB |
| Reset build | button | R | Y |
| Turn, zoom | drag, wheel | none | right stick, LT / RT |
| Done | Done or Back | Esc | B |

**Texts:** `frontend.attachments.*` (kicker, title, slots, factory, factoryNote, fit, fitted, reset, done, better,
worse, noChange, items.<id>.name and .blurb); `frontend.effects.*`.

### 2.7 Block (level and time)

**Shows:** One card per level in `levels.json order`, with its name, blurb, place line and the modes it plays
(`Plays Story · Hold the Block`). There is one card today. The row is a carousel built for more and shows only real
levels, with no "coming soon" placeholders. Under the cards is the time picker, `Day` / `Night`, a segmented control
with the notes `text.interface.title.timeNotes`.

**3D:** The title fly-through of the chosen level, if that level is the map that is loaded. The time switches live, as
the web title did (the sky rig switches at once). A level that is not loaded shows its `preview.thumbnail` full screen
behind the veil.

| Input | Mouse | Keyboard | Gamepad |
|---|---|---|---|
| Level | click a card | Left / Right | D-pad left / right |
| Time | click Day / Night | Down to the picker, Left / Right | D-pad down, left / right |
| Next / Back | buttons | Enter / Esc | A or Start / B |

Choosing a level other than the loaded map is remembered. The world travels to that level's map only on Hit the
block: the loading screen (spec 07 4.2 boot) shows, and the new map's flow enters `intro` directly with the saved
set-up.

**Texts:** `frontend.level.kicker`, `.title`, `.time`, `.times`, `.modes`; `frontend.levels.<id>.name`, `.blurb`;
`text.interface.title.timeNotes`.

### 2.8 Style (game style and difficulty)

**Shows:** One card per mode the level provides (3.5), with the name and the note (`text.modes.<id>.name`, `.note`):
Story and Hold the Block. The Hold the Block card shows `Best 12,345` (the saved best score). Under the cards is the
difficulty, `Hustler` / `Boss` / `Kingpin`, with a one-line note per tier (`frontend.mode.difficultyNotes`) and the
existing `text.notes.difficulty`. Both write the existing settings `mode` and `difficulty` at once, as the web pickers
did.

**3D:** The fly-through, which keeps running.

| Input | Mouse | Keyboard | Gamepad |
|---|---|---|---|
| Mode | click a card | Left / Right | D-pad left / right |
| Difficulty | click | Down, Left / Right | D-pad down, left / right |
| Next / Back | buttons | Enter / Esc | A or Start / B |

**Texts:** `frontend.mode.kicker`, `.title`, `.difficulty`, `.best`, `.difficultyNotes`; `text.modes.*`,
`text.difficulties.*`, `text.notes.difficulty`.

### 2.9 Briefing

**Shows:** The IPX Vault's plan as a card (`IPX Vault · The plan`, `Here's how it goes`). It has four lines, each with
a `Change` link:

- **Crew:** the portrait and the name.
- **Carrying:** the guns in slot order with their attachment pips.
- **Block:** the place line for the chosen time (`text.location.byTime`).
- **Style:** the mode, the difficulty and the tagline (`text.location.tagline` / `taglineHoldout`).

Under them is the radio intro of the mode for the chosen crew member (3.4), as a quoted Vault line, and the controls
glance strip with the new rows (`frontend.controls`).

**3D:** The player's own first-person camera at the level's `playerStart`, the chosen arms holding the first carried
gun, which plays its `Equip` clip once. `Hit the block` starts the full intro (spec 04 3.5) from this exact view: the
first frame of play is the last frame of the briefing.

| Input | Mouse | Keyboard | Gamepad |
|---|---|---|---|
| Hit the block | primary button | Enter | A or Start |
| Change a line | `Change` | Up / Down to it, Enter | D-pad to it, A |
| Back | Back | Esc | B |

**Texts:** `frontend.briefing.*`; `frontend.crewLines.*` or `text.radio.intro` / `introHoldout`.

### 2.10 After a run

The death card (`dead`) and the debrief card (`complete`) gain `Change set-up` (`frontend.cards.changeSetup`) between
`Run it back` and `Back to title`. The focus orders become `Run it back`, `Change set-up`, `Back to title`.
`Run it back` and `Restart run` keep the whole set-up. The kicker `Rule down` uses `frontend.crewLines.deadKicker` for
the other crew.

### 2.11 The 3D stage

- **Where.** `AMIShowroom` is an actor spawned at run time at `frontend.json stage.origin` (1 km above the block's
  origin), so the project still needs no binary assets (ARCHITECTURE 1.1 rule 4). Its closed room keeps out the
  block's sun, sky light and fog; at 1 km the height fog is negligible. Its own lights and a fixed-exposure post
  volume bounded by the room light it. Everything is a placeholder for the art pass. A level may later name a place
  inside itself (`levels.json provides.showroom`, for example the chop shop's bench), and the stage then uses it.
- **Who owns the view.** On Crew, Loadout and Workbench the front end puts the view on the stage's camera, as the
  title camera does on Home. On Block and Style the fly-through returns. On the Briefing the player's own camera
  takes over. These are view-target changes with a 0.3 s fade through black, never two renders.
- **The turntable** (`stage.turntable`) spins 18°/s until touched, resumes 3 s after the last touch, turns 0.35° per
  dragged pixel or 120°/s at full right stick, clamps the pitch to −25° … 35° and zooms 0.65 × … 1.6 ×. A fitted part
  slides into its socket in 0.25 s.
- **What you see is what you carry.** The showroom and the first-person gun build the gun with the same
  `UMIGunAssembly` component: the gun mesh, one child mesh per fitted attachment at its mount socket, the hidden parts
  (`mounts.<slot>.hide`), and the marker overrides (4.5). A part with a null mesh shows nothing, and the build still
  resolves.

### 2.12 Text keys

All new strings are in `frontend_text.json`, keyed as `frontend.*`, the way they will sit in `text.json`. They are
kept separate because `text.json` is written by `tools/ue-export` from the web game. The loader reads both; a
`frontend` key never shadows a `text.json` key. Templates use the `{"$template": ...}` form of `text.json`.

| Group | Keys |
|---|---|
| Home | `frontend.home.start`, `.same`, `.summary`, `.firstTime` |
| Frame | `frontend.steps.labels`, `.of`, `.next`, `.back` |
| Crew | `frontend.crew.kicker`, `.title`, `.note`, `.{rule,deuce,smoke,keys}.{name,tagline}` |
| Loadout | `frontend.loadout.*` (2.5) |
| Workbench | `frontend.attachments.*`, `frontend.effects.*` (2.6) |
| Block | `frontend.level.*`, `frontend.levels.block.*` |
| Style | `frontend.mode.*` |
| Briefing | `frontend.briefing.*` |
| Cards | `frontend.cards.changeSetup`; `frontend.crewLines.deadKicker` |
| Radio | `frontend.crewLines.radioIntro`, `.radioIntroHoldout`, `.radioDone` |
| Guns | `frontend.weapons.{stick,rattler}.{name,blurb}`, `frontend.weapons.melee.{stick,rattler}` |
| HUD | `frontend.hud.modes.{auto,semi}`, `.wheel`, `.empty` |
| Glyphs | `frontend.glyphs.{kbm,pad,touch}.{weapon3,weapon4,fireMode,inspect,wheel}` |
| Controls drawer | `frontend.controls.{kbm,pad}` (rows added after "Swap weapon") |

---

## 3. Data

### 3.1 Loading

`UMIDataSubsystem` loads the six new files after `config.json` and `presentation.json`, into a new
`FMILoadoutData` (`Core/Data/MILoadoutData.h`) next to `FMIConfigData`:

1. **Resolve `$ref`.** `{"$ref": "config.json#weapons.chopper"}` is that object of that file. The CHOPPER and the
   NINE therefore have one source of truth.
2. **Build one rule table.** For every roster gun, its `rules` object goes through the *existing* `ParseGun` (it is
   in `config.json`'s schema and units), and its `presentation` goes through `FMIViewmodelData::Parse` (in
   `presentation.json`'s schema). `ParseGun` is called with the gun's object instead of a `weapons.<id>` path; that
   is the only refactor. `extra` is parsed into the new fields, with the defaults of `guns.json extraDefaults`.
3. **Validate** (MurderInc.Loadout.DataLoads, 8.5):
   - every id reference resolves (texts, slots, stats, attachments, mounts, clip roles);
   - every `required` slot's default is among its options;
   - every non-baseline attachment has an effect that is better and one that is worse;
   - every level's `provides` matches its level file;
   - every mode is provided by at least one level.

   On failure the front end offers only the parity set-up, and the log says why (LogMI, Error).

### 3.2 Guns (`guns.json`)

A gun entry has:

- `id`, `class` (a key of `classes`), `text` (name and blurb), `melee` (the HUD's melee label);
- `rules` (config schema, or a `$ref`);
- `extra` (the new per-gun fields, 1.2);
- `presentation` (presentation schema, or a `$ref`; `fallbackMesh` is used when the pack is not installed);
- `mounts` (a socket per attachment slot, parts it hides, art status);
- `art` and `clips` (status, see 6).

`roster` is the display order. Its numbers:

| | CHOPPER | NINE | STICK | RATTLER |
|---|---|---|---|---|
| Class, modes | rifle; auto, semi | pistol; semi | rifle; auto, semi | smg; auto, semi |
| Damage per round (head × 2.2) | 26 | 34 | 22 | 30, falloff to 0.65 × from 15 to 35 m |
| Rate (rpm), damage per s | 720, 312 | 420, 238 | 800, 293 | 545, 272 |
| Magazine / reserve | 30 / 150 | 15 / ∞ | 30 / 150 | 32 / 128 |
| Resupply per wave (cap) | 90 (240) | none | 90 (240) | 96 (256) |
| Range (m) | 300 | 120 | 300 | 120 |
| Aim time (s), holster / draw (s) | 0.18, 0.28 / 0.32 | 0.14, 0.28 / 0.32 | 0.20, 0.28 / 0.32 | 0.14, 0.24 / 0.27 |
| Spread hip / aimed / moving hip (rad) | 0.0125 / 0.0012 / 0.013 | 0.0105 / 0.0017 / 0.0065 | 0.012 / 0.0009 / 0.013 | 0.0094 / 0.003 / 0.0065 |
| Camera kick per round (rad) | 0.0068, climb then weave | 0.0092, snap | 0.0051, climb then weave | 0.0041, fast buzz |
| Reload tactical / empty (s) | 2.24 / 2.72 | 1.50 / 1.90 | 2.13 / 2.45 (bolt catch) | 1.90 / 2.31 (rack) |
| Noise, aimed view | 45 m, 52° | 45 m, 52° | 45 m, 52° | 45 m, 52° |

Rounds and time to drop a Goon with body shots (Goon HP 90 / 110 / 130 by difficulty, `config.json
enemies.difficulty`; time = (rounds − 1) × interval). The table shows that no gun wins everywhere:

| | Hustler 90 | Boss 110 | Kingpin 130 | Its edge |
|---|---|---|---|---|
| CHOPPER | 4 rounds, 0.25 s | 5, 0.33 s | 5, 0.33 s | raw damage; climbs hard |
| NINE | 3, 0.29 s | 4, 0.43 s | 4, 0.43 s | never runs dry, quickest hands |
| STICK | 5, 0.30 s | 5, 0.30 s | 6, 0.38 s | easiest to control, takes every attachment |
| RATTLER | 3, 0.22 s | 4, 0.33 s | 5, 0.44 s | best up close and on the move; weak past 15 m |

#### 3.2.1 How the STICK's numbers come from the CHOPPER's

The STICK is a lighter, faster round in a longer gun with a full stock. Each number is a CHOPPER number times a
stated factor:

| Field | CHOPPER | Factor | STICK |
|---|---|---|---|
| damage, rpm | 26, 720 | × 0.85, × 1.11 | 22, 800 |
| magSize, reserve, range | 30, 150, 300 | same | same, so the resupply rule holds unchanged |
| adsTime | 0.18 | × 1.11 | 0.20 |
| reload tactical, marks to tug | 2.24, 0.40 … 1.565 | × 0.95 | 2.13, 0.38 … 1.49; no press check |
| reload empty | 2.72 (rack) | bolt catch | 2.45, the bolt closes at 1.92 (`slideRelease`) |
| spread hip, ads, moveHip, moveAds | .0125, .0012, .013, .004 | × 0.96, × 0.75, × 1, × 0.9 | .012, .0009, .013, .0036 |
| bloomHip, bloomAds, shot, decay | .0065, .0022, .17, 1.5 | × 0.85, × 0.8, × 0.8, × 1.1 | .0055, .0018, .14, 1.65 |
| recoil pitch, pitchRandom | .0068, [.85, 1.15] | × 0.75, narrower | .0051, [.9, 1.1] |
| yawEarly, weaveAmp, weaveRandom, weaveFrom | .0011, .0042, .001, 4 | × 0.8, × 0.7, × 0.8, + 1 | .0009, .0029, .0008, 5 |
| shake; kick back, rise, yaw, roll, up, side | .12; .82, 1.5, .475, .85, .11, .09 | × 0.75; × 0.8 | .09; .66, 1.2, .38, .68, .09, .07 |
| flash scale, light; wallPull | 1, 45; [1.05, .42] | × 0.9; × 1.05 | .9, 40; [1.1, .44] |
| springs, sway, views, poses, strike keys | | same | provisional until the pack is measured |

#### 3.2.2 How the RATTLER's numbers come from the Goon's gun

The RATTLER is the Goon's gun, so the player hears the same cadence from it that he hears from every Goon. The
enemy's per-round damage (4 on Boss) is tuned against the player's 100 HP for fairness, so it is not used.

| Field | Source | Rule | RATTLER |
|---|---|---|---|
| rpm | `enemies.goon.burstGap` 0.11 s | 60 / 0.11 | 545 |
| damage | the NINE's 34 (the same class of round) | × 0.88; 3 rounds = a Hustler Goon's 90 HP | 30 |
| magSize, reserve | `goon.burst` 4 | 8 bursts; 4 magazines | 32, 128; resupply 3 magazines (96), cap 8 (256) |
| range, falloff | the NINE's 120 m | short barrel | 120 m; full damage to 15 m, 0.65 × from 35 m |
| adsTime, holster, draw | the NINE's 0.14; common 0.28 / 0.32 | × 0.85 | 0.14; 0.24 / 0.27 |
| spread hip, moveHip, ads, moveAds | CHOPPER .0125, .013, .0012, .004 | × 0.75, × 0.5, × 2.5, × 1 | .0094, .0065, .003, .004 |
| bloomHip, bloomAds, air, decay | CHOPPER .0065, .0022; NINE .018; CHOPPER 1.5 | × 0.9, × 1.4, NINE's, × 1.2 | .0058, .0031, .018, 1.8 |
| recoil pitch, shake | CHOPPER .0068, .12 | × 0.6, × 0.67 | .0041, .08 |
| yawEarly, weaveFrom, weaveAmp, weaveFreq, weaveRandom | CHOPPER .0011, 4, .0042, .57, .001 | × 1.45, − 1, × 0.83, × 1.58, × 1.4 | .0016, 3, .0035, .9, .0014: a fast sideways buzz instead of a climb |
| reload, all marks | CHOPPER's | × 0.85 | 1.90 / 2.31 |
| wallPull | CHOPPER [1.05, .42] | × 0.81 | [.85, .34] |

### 3.3 Attachments (`attachments.json`)

**Slots:** optic, muzzle, underbarrel, laser, magazine, handguard, stock, in that order (the order of the Workbench's
tabs and of applying `set`).

**Stats** an effect may change. Each has its targets in the gun's data, a unit, the direction that is `better`, a
clamp and the text of its effect line:

| Stat | Changes | Better |
|---|---|---|
| `adsTime` | `adsTime` | lower |
| `adsFov` | `extra.adsFov` (vertical degrees at full aim) | none (a trade) |
| `adsLook` | `extra.adsLook` (look speed at full aim; follows the view) | none, not shown |
| `spread.hip`, `spread.moveHip`, `spread.ads`, `spread.moveAds` | those spreads | lower |
| `recoil.pitch` | `recoil.pitch`, `recoil.shake`, `kick.rise`, `kick.back` (what the eye sees follows the aim) | lower |
| `recoil.yaw` | `recoil.yaw` or `yawEarly`, `weaveAmp`, `weaveRandom`; `kick.yaw`, `kick.roll` | lower |
| `swapTime` | `extra.holster`, `extra.draw` | lower |
| `reloadTime` | every reload mark and both lengths (the clip plays at 1 / factor) | lower |
| `noise` | `extra.noise`, the hearing radius (m) | lower |
| `flash` | `flash.scale`, `flash.light` | lower |
| `falloff.start`, `falloff.end`, `falloff.min` | `extra.falloff` | higher |
| `length` | both `wallPull` distances | lower |
| `sway` | `swayMax` (presentation) | lower |

**Ops:** for each stat, in this order: every `set` (the later slot wins), the sum of every `add`, the product of every
`mul`, every `min` (the smallest wins), every `max`, then the clamp. Factors from different parts multiply.

**The thirteen parts.** Baseline parts (marked ◦) are the "nothing changed" choice of a required slot and have no
effects.

| Part | Slot | Better | Worse |
|---|---|---|---|
| Folding irons ◦ | optic | | |
| Scope | optic | aimed spread × 0.7 | aim time × 1.35, aimed spread on the move × 1.3, sway × 1.2; aimed view 30° (from 52°), look × 0.6 |
| Silencer | muzzle | heard at 0.4 × (45 → 18 m), flash × 0.15, kick × 0.95 | damage falls from 25 m to 0.85 × at 50 m, aim time × 1.06, swap × 1.06, length × 1.12 |
| Vertical grip | underbarrel | kick × 0.88, side × 0.85 | aim time × 1.08, swap × 1.05 |
| Angled grip | underbarrel | aim time × 0.9, swap × 0.95, kick × 0.96 | side × 1.12 |
| Laser | laser | hip spread × 0.75, moving hip × 0.85 | aim time × 1.05, swap × 1.04 |
| Standard mag ◦ | magazine | | |
| Clear mag | magazine | reload × 0.94 | kick × 1.04 |
| Standard handguard ◦ | handguard | | |
| Short handguard | handguard | aim time × 0.9, swap × 0.92, moving hip × 0.9, length × 0.86 | kick × 1.1, aimed spread × 1.15, flash × 1.3, heard × 1.1, damage falls from 25 m to 0.9 × at 50 m |
| Long handguard | handguard | kick × 0.92, aimed spread × 0.85 | aim time × 1.1, swap × 1.08, length × 1.15, sway × 1.1 |
| Stock open ◦ | stock | | |
| Stock folded | stock | aim time × 0.85, swap × 0.88, hip spread × 0.95 | kick × 1.2, side × 1.2, aimed spread × 1.25, sway × 1.2 |

**Compatibility** (`attachments.json compatibility`; an unlisted slot does not exist on that gun):

| | Optic | Muzzle | Underbarrel | Laser | Magazine | Handguard | Stock |
|---|---|---|---|---|---|---|---|
| CHOPPER | scope (top-cover rail) | silencer (replaces the booster) | | | | | |
| NINE | | | | laser (dust-cover rail) | | | |
| STICK | irons◦ or scope, required | silencer | vertical or angled grip | laser | standard◦ or clear, required | short, standard◦, long, required | open◦ or folded, required |
| RATTLER | (rail too short) | silencer (replaces its device) | | (the light fills the handguard) | | | |

Builds, worked out (STICK; aim time s / kick rad / aimed spread rad / heard m):

| Build | Aim | Kick | Aimed | Heard | Note |
|---|---|---|---|---|---|
| Factory: irons, standard handguard and mag, stock open | 0.20 | 0.0051 | 0.0009 | 45 | |
| Scope | 0.27 | 0.0051 | 0.0006 | 45 | aimed view 30° |
| Close: short, folded, angled, laser, clear mag | 0.145 | 0.0067 | 0.0013 | 49.5 | hip 0.0085, swap 0.26 s; kicks like a CHOPPER |
| Long and quiet: long, scope, vertical, silencer | 0.34 | 0.0039 | 0.0005 | 18 | swap 0.38 s; 0.85 × damage past 50 m |

On the CHOPPER, a scope and a silencer give aim 0.26 s, aimed spread 0.0008, heard at 18 m and 22.1 damage past 50 m.

### 3.4 Crew (`crew.json`)

A crew member is a `look` on Rule's arms:

- `arms`: a mesh on `SK_Mannequin`, by default `SK_RuleArms`;
- `materials`: material instances per slot of the arms mesh;
- `glove`: a glove mesh variant;
- `sleeve`: a sleeve mesh skinned to the arm bones;
- `jewellery`: static meshes on a bone, with an offset as in `CHARACTERS.md`.

It also has a `callName`, a `portrait`, art status, and `perks: []`. Rule's `lines` are `original` (the `text.json`
lines word for word). The others use `template`: `crew.json lines.replaces` maps the four lines that name the player
to `frontend.crewLines.*` with `{name}`.

| Id | Name | Look (placeholder) |
|---|---|---|
| rule | RULE | black leather and suede gloves, steel watch on the left, curb bracelet on the right, bare forearms (exists, in progress) |
| deuce | DEUCE | black fingerless knit gloves, a grey hoodie sleeve pushed up, a thin gold rope bracelet, a different skin tone |
| smoke | SMOKE | bare hands with white tape on the knuckles and wrist, a black bomber cuff, a wooden bead bracelet |
| keys | KEYS | charcoal wool gloves with two fingertips cut off, a denim jacket cuff, a black digital watch |

The crew are cosmetic, for three reasons:

1. A perk would make one member the best pick, which the loadout already avoids.
2. A perk would multiply the parity surface: each crew member would need its own golden tests.
3. The crew is seen only as arms, so a perk could not be read off the character.

`perks` is reserved for open question 4.

### 3.5 Levels and modes (`levels.json`)

A level gives its `map`, its `data` files, its `times`, a `preview` (the title path or a thumbnail) and `provides`:
the counts of what its level file has. A mode gives `needs`; the Style screen offers a mode only where `provides`
covers it.

| Mode | Needs from a level | The block |
|---|---|---|
| Story (`mission`) | a player start; at least 1 objective (each one is a master reel); an extraction zone; at least 1 ground spawn; nav | 3 objectives, truck at the lot, 29 ground and 17 air spawns, nav, 14 title keys |
| Hold the Block (`holdout`) | a player start; at least 1 ground and 1 air spawn (waves mix Goons and Buzzards); nav. Objectives and explosives are optional (closed cases, explosives rebuilt every second wave) | the same |

A new level is a map, its level JSON (exported or authored in the same schema) and one entry here. The flow already
reads everything per level from `level.json` (spec 04 2.15). Story counts its reels from the level's objectives, so a
level with two cases is a two-reel Story; the radio's reel lines are indexed by count.

### 3.6 Front end (`frontend.json`)

`parity` (1.2), `carry` (2.5), `screens` (id, step, back, primary, text group, stage), `transitions` (the edges of
2.1), `stage` (2.11), `input` (4.2 and the per-screen menu inputs of 2.3 to 2.9), `wheel` (4.6), `hud` (4.7) and
`save` (7).

### 3.7 The resolver

`FMILoadoutResolver` (`Weapons/MILoadoutResolver.h/.cpp`) is a rule core with no world and no UObject (ARCHITECTURE
1.1 rule 2). Given `FMILoadoutData`, the set-up and the config, it returns the run's `FMIWeaponsData` and
`FMIViewmodelData`:

1. Validate the set-up (7, validation) against the data.
2. `Guns` = for each carried gun, in slot order: its parsed `FMIWeaponDef`, with `Slot` = its position (1 … 4).
3. For each stat of `attachments.json stats`, collect the effects of the gun's fitted parts and apply the ops (3.3) to
   every target. Set `FMIWeaponDef::Fitted` (slot → part id).
4. Presentation: build each carried gun's view data from its presentation. Apply the marker overrides of the fitted
   parts (4.5) and add the list of attachment meshes for `UMIGunAssembly`.
5. `Common` and `Melee` are config's, unchanged.

It is called once per run, at the run reset, and live on the Workbench to fill the stat bars and the effect lines. It
is pure, so the tests call it directly.

---

## 4. Four guns in the rules

### 4.1 Slots

The resolved `Guns` array holds the carried guns in slot order, so index = slot − 1. `Reset()` already puts index 0
in the hands with full magazines and the start reserve of every gun. The run starts with slot 1 in hand, its fire
mode set to the saved one (or `fireModes[0]`).

### 4.2 Switching

New fields of `FMIWeaponInput`: `bWeapon3Pressed`, `bWeapon4Pressed`, `bNextPressed`, `bPreviousPressed`, `WheelPick`
(the index chosen on the wheel this frame, or `INDEX_NONE`) and `bFireModePressed`. They default to false or
`INDEX_NONE`. `bSwapPressed`, `bWeapon1Pressed` and `bWeapon2Pressed` keep their names, so the golden harness is
unchanged.

| Input (`frontend.json input.game`) | Target |
|---|---|
| Q, Y (`swap`): quick swap | holstering: the gun being put away (`Current`); otherwise `LastUsed` |
| Wheel down, D-pad ↑ (`next`) | (`Aim` + 1) mod N, where `Aim` = `Swap.To` while holstering, else `Current` |
| Wheel up, D-pad ↓ (`previous`) | (`Aim` − 1) mod N |
| 1, 2, 3, 4; D-pad ←, → (slots 1, 2) | that slot, when it holds a gun |
| The wheel (4.6) | the gun chosen |

Precedence within a frame: swap, next, previous, slots 1 to 4, wheel. `LastUsed` is set by `Equip` to the gun put
away. `Reset()` sets it to index 1, or 0 with one gun.

**Why the parity set-up is unchanged.** With N = 2:
- (`Aim` ± 1) mod 2 is the other gun of `Aim`, which is what the web's `OtherOf(Swap.bActive && Swap.bHolster ?
  Swap.To : Current)` gives.
- The quick swap gives the same gun: `Current` while holstering, and otherwise the gun last put away, which is the
  other one.

Golden scenarios `nine_presses`, `switch_reverse` and `spread_stances` exercise this.

`RequestSwitch` gains one case. While holstering toward `To`, a request for a third gun (neither `Current` nor `To`)
**retargets** `Swap.To` and lets the holster run on. A request for `Current` brings the gun back up, as today. With
two guns, any other request is a request for `Current`, so the web behaviour is unchanged.

**Per-gun timing.** `C.Holster` and `C.Draw` become `HolsterOf(Current)` and `DrawOf(Current)`:
- in the reversal arithmetic: `T = Draw(Current) × (1 − T / Holster(Current))`, and the mirror case;
- in `AdvanceSwitch`: the holster ends at `Holster(Current)`; after `Equip`, `T −= Holster(previous)` and the draw
  ends at `Draw(new Current)`;
- in `GetView().ActivityLength`.

They equal the common values in the parity set-up.

### 4.3 Ammunition and resupply

Each gun keeps its own magazine and reserve (the `Ammo` array already does). A new `Resupply()` adds each finite
reserve's `Rounds` up to its `Cap`. The flow's Hold the Block clear (spec 04 3.11) calls it in place of
`AddReserve(90, 240)`, which stays for the tests. The CHOPPER's rounds and cap are 90 and 240, so the result is
unchanged. The low-ammunition cue and `Empty — Q swaps` work per gun as today.

### 4.4 Fire modes

Each gun has `FireModes` (from `extra`) and a per-gun `bSemi` state, set at reset from the saved mode. `bFireModePressed`
on a gun with two modes, while not `Busy()` and not dropped, starts a **Selector** activity of `ModeSwitch` seconds:

- `EMIWeaponActivity::Selector` is new; `Busy()` includes it, so the gun cannot fire, reload or aim meanwhile.
- At its end the rules flip `bSemi` and broadcast a new `WeaponMode {weapon, semi}` event.
- A switch request, a melee strike or death cancels it without flipping.

In `PullTrigger`, `Def.bAuto` becomes `Def.bAuto && !bSemi[Current]`. A semi press on an automatic gun is buffered by
`Def.FireBuffer > 0 ? Def.FireBuffer : Def.SemiFireBuffer` (0.13 s, the NINE's). The interval stays 60 / rpm. The HUD
shows `AUTO` or `SEMI`. The last mode used is saved per gun.

### 4.5 What the attachments do at run time

| Effect | Where it acts | Change |
|---|---|---|
| Aimed field of view, look | `FMIPlayerRules` | `FovTarget = Lerp(base + sprint, AimFov, A)` with `AimFov` from the gun in hand, in place of `T.Fov.Ads`; the aimed look scale is `T.Look.AdsScale × AimLook`. The weapon sets both every frame through the new host call `IMIWeaponHost::SetPlayerAimView(AdsFov, AdsLook)`, whose default does nothing. Defaults: config's values |
| Damage falloff | `UMIWeaponComponent::Hitscan` | `FMIShotRequest` gains `FalloffStart`, `FalloffEnd` (cm) and `FalloffMin`. Damage × 1 while distance ≤ start (the branch is skipped, so exactly the same double), linear to `min` at `end`, `min` beyond; then the head multiplier. Applies to explosives too |
| Noise | the enemies' gunfire listener | `FMIShotFiredEvent` gains `NoiseRadius` (the unit of `Tune.Ai.HearGunfire`) and `bSuppressed`. The listener calls a new `FMIEnemyField::Gunfire(Pos, Radius)`; the existing `Gunfire(Pos)` calls it with `HearGunfire`. The 0.3 s throttle stays, except that a round heard further than the last alert in the window still alerts (never true when every radius is equal) |
| Flash, smoke, sound | `OnRoundFired` / effects / audio | `FlashScale` and the light from the resolved `flash`; `bSuppressed` picks the suppressed sound set |
| Length near walls | `ProbeWall` | the resolved `WallStart` / `WallFull` |
| Sight, muzzle, support hand | `FMIViewmodelRig` markers | a fitted part's socket replaces a marker: the optic's `SightEye` replaces `sightRear` (with the part's `relief`), the muzzle device's `Muzzle` replaces `muzzle` (tracers and flash start there), a grip's `SupportHand` replaces `support` (left-hand IK), a handguard's sockets replace its own |
| Laser | `UMIWeaponComponent` (presentation) | a beam from the `Beam` socket to the point the eye ray hits on the `Bullet` channel (rounds leave the eye: spec 02), so the dot shows where hip fire goes. It fades out above 0.6 aim. Always on |
| Clear magazine | gun material | the scalar `RoundsShown` = magazine / size |

### 4.6 The weapon wheel

Hold Q or Y for 0.25 s (`frontend.json wheel`).

- The press has already started the quick swap, exactly as in the web game. The wheel only redirects it.
- Four sectors, slot 1 at the top, clockwise. Each sector shows the gun's silhouette, name, magazine and reserve, and
  mode. The centre shows `Pick a gun`.
- The mouse travel since the wheel opened selects, with a 60 px radius and a 0.5 dead zone; on the pad, the right
  stick selects. Look and fire are blocked while the wheel is open.
- Release: a selection becomes `WheelPick` and goes through `RequestSwitch`, which reverses, retargets or holsters
  again (4.2). Releasing inside the dead zone keeps the quick swap.
- The game does not slow down (open question 5).
- The wheel is drawn by the HUD and lives in the input layer (`AMIPlayerController`). The rules see only `WheelPick`.

### 4.7 HUD

The weapon bar (spec 07 3.5) shows one slot per carried gun, then melee. The parity set-up shows exactly two slots and
melee.

- Each slot has its silhouette, its own magazine pips and count, its reserve (∞ for the NINE), its glyph
  (`frontend.json hud.weaponBar.glyphs`: 1–4 on a keyboard, ← → for slots 1 and 2 on a pad, where slots 3 and 4 go
  through the wheel and the D-pad cycle), `AUTO` / `SEMI` on two-mode guns, and attachment pips.
- The holstered guns show their ammunition, as the web's holstered slot does.
- Clicking or tapping a slot switches to it, as today.
- The slice-1 `AMIHUD` canvas lists all carried guns' ammunition. The real `WBP_WeaponBar` (spec 07 4.2) is built for
  four from the start.

### 4.8 Presentation-only features from the pack

These never write rule state. Any rule activity, a fire or aim press, sprint or a swap cancels them, with a 0.15 s
blend out:

| Feature | Trigger | Notes |
|---|---|---|
| Inspect | T, or hold View 0.4 s; and by itself after `inspectAfter` s (24) of idle (no input, `Ready`, hip, not sprinting) | `inspectAfter: 24` is in `config.json` today with no animation (spec 02 open question 2): this answers it |
| Magazine check | Reload with a full magazine, or with an empty reserve | the rules refuse that reload as always; `UMIWeaponComponent` sees the press, `Mag == MagSize` (or `Reserve == 0`) and `Ready`, and plays `MagCheck`. With the clear magazine the rounds show |
| Melee with the gun | the existing melee (F, V, RB, R3) | rules unchanged (0.55 s, contact at 0.16 s, spec 02); the strike plays `MeleeA` and `MeleeB` alternately (a counter, not a random draw), `MeleeBash` as the fallback; retimed to 0.55 s with contact on 0.16 s |
| Trigger discipline | always, while not firing | the `TriggerOff` finger pose as an additive layer |

### 4.9 Classes that change (GAMEPLAY.md names)

| Class (file) | Change | Parity guard |
|---|---|---|
| `FMIWeaponDef`, `FMIWeaponsData` (`Core/Data/MIData.h`) | new fields: `Holster`, `Draw`, `AdsFov`, `AdsLook`, `NoiseRadius`, `FalloffStart/End/Min`, `FireModes`, `SemiFireBuffer`, `ModeSwitch`, `ResupplyRounds/Cap`, `InspectAfter`, `Fitted` | defaults = config values (1.2) |
| `UMIDataSubsystem` (`Core/Data`) | loads the six files into `FMILoadoutData`; `ParseGun` takes an object; `$ref` | `MurderInc.Core.DataLoads` unchanged |
| `FMIWeaponRules` (`Weapons/MIWeaponRules`) | 4.2 switching, `LastUsed`, retarget; per-gun holster and draw; `Resupply()`; Selector activity and fire modes; `SetPlayerAimView`; falloff, noise and suppression in `FMIShotRequest` and the fire event | golden weapon scenarios through the resolver (8.1) |
| `IMIWeaponHost` (same file) | `SetPlayerAimView(double, double)` with a default empty body | the golden host needs no change |
| `UMIWeaponComponent` (`Weapons/MIWeaponComponent`) | `Setup` takes the resolved data; builds the guns with `UMIGunAssembly`; falloff in `Hitscan`; laser; inspect and magazine check; forwards the aim view | `Weapons.HitscanDummyBlast` unchanged |
| `FMIViewmodelRig`, `FMIViewmodelData` (`Weapons/MIViewmodel`) | data for any roster gun; marker and relief overrides from the fitted parts | `Weapons.ViewmodelRig` unchanged |
| `FMIPlayerRules` (`Player/MIPlayerRules`) | `AimFov` and `AimLook` per frame | `Golden.PlayerPure`, `.PlayerSim` unchanged |
| `AMIPlayerController` (`Player`) | the actions of `frontend.json input.game` layered over config's (wheel and D-pad ↑ ↓ become next and previous); hold timing for Q, Y and View; the wheel; menu console `MIMenu` | `Core.GameClasses` counts change (8.6) |
| `AMIPlayerCharacter` (`Player`) | passes the run's resolved data to `UMIWeaponComponent::Setup`; spawns the crew's arms look | |
| `FMIGameEvents` (`Core/MIEvents.h`) | `WeaponMode`; `FMIShotFiredEvent.NoiseRadius`, `.bSuppressed` | no new event in parity runs |
| `AMIHUD` (`UI`) | 4-slot ammunition, mode tag, wheel | |
| `AMIGameMode` and the flow director being written (`Flow`) | the title sub-screens; the run reset applies the set-up (resolver → `FMIWeaponRules::Init`, the crew's arms, the crew lines); `Resupply()`; `Change set-up`; level travel | `Golden` flow rules unchanged |
| `FMIEnemyField` (`Enemies/MIEnemies`, the enemy agent's) | `Gunfire(Pos, Radius)` overload | `Golden.Enemies` unchanged |

### 4.10 New classes

| Class | Folder | Kind |
|---|---|---|
| `FMILoadoutData` and its structs (guns, attachments, crew, levels, modes, front end) | `Core/Data/MILoadoutData.h/.cpp` | data |
| `FMIRunSetup` (crew, guns, builds, fire modes, level, mode, difficulty, time) | `Core/Data/MILoadoutData.h` | data |
| `FMILoadoutResolver` | `Weapons/MILoadoutResolver.h/.cpp` | rule core |
| `FMIFrontEndRules` (screen stack, focus, Back and Next, the carry rules, validation; no widgets) | `Flow/MIFrontEndRules.h/.cpp` | rule core |
| `UMIRunSetupSubsystem` (the current set-up across level travel, save and load) | `Flow/MIRunSetupSubsystem.h/.cpp` | game-instance subsystem |
| `UMIGunAssembly` (gun mesh + parts + hidden parts + marker overrides) | `Weapons/MIGunAssembly.h/.cpp` | component |
| `AMIShowroom` (stage, turntable, cameras, arms) | `UI/MIShowroom.h/.cpp` | actor |
| `SMIFrontEnd` and one widget per screen (`SMIScreenHome`, `…Crew`, `…Loadout`, `…Workbench`, `…Level`, `…Style`, `…Briefing`), `SMIWeaponWheel` | `UI/` | Slate (ARCHITECTURE 2.2: the UI is Slate in C++) |

---

## 5. The pack's clips: features and leftovers

`guns.json clipRoles` lists every role, its pack source, whether the rules time it, and its fallback. The asset name
is `A_FP_<Set>_<Role>` (spec 02 5.x); `ANIMATION.md` maps each pack clip to it.

| Pack clips | Use |
|---|---|
| fire semi, auto, aimed, empty | `FireSemi`, `Fire`, `FireAds`, `FireLast` |
| fire-mode switch | `ModeSemi` / `ModeAuto`, a feature (4.4) |
| reload, reload empty | `ReloadTactical`, `ReloadEmpty`, stretched to the rule lengths with notifies on the marks |
| magazine check | `MagCheck`, a feature (4.8) |
| inspect | `Inspect`, a feature (4.8); also the Crew screen (2.4) |
| melee bash, two swings | `MeleeBash`, `MeleeA`, `MeleeB`, a feature (4.8) |
| equip, quick equip, holster | `Equip` (showroom, briefing), `Draw` (0.32 s), `Holster` (0.28 s) |
| aim in and out, crouch transitions, poses, locomotion | `AimIn` / `AimOut` (stretched to the aim time), `CrouchIn` / `Out`, `Idle`, `IdleAds`, `Walk`, `Sprint` |
| trigger discipline poses | `TriggerOff`, an additive pose (4.8) |
| grip change, grip poses | `GripChange` (Workbench), `GripNone`, `GripVertical`, `GripAngled` (left hand per underbarrel) |
| weapon-part clips | the STICK's moving parts during reload, inspect, magazine check and the selector |
| **left out:** jam clearances | no jam rule; a random jam adds a draw to the weapon stream and punishes the player for nothing |
| **left out:** syringe heal | health regenerates; healing needs pickups and an inventory the game does not have |
| **left out:** quick grenade throw | no grenades; the block's explosives are props |
| **left out:** quick and empty-retain reloads, aimed reloads | one tactical and one empty reload per gun; the rules lower the sight during reloads |
| **left out:** third-person clips | the player has no body in the world; kept for a full-body crew preview or a Goon with a STICK |

---

## 6. Art and animation

Status: **exists** (usable now), **in progress** (an agent is on it), **missing** (nobody has started). Socket
coordinates are in the mesh's space (x along the bore, y left, z up; metres), as `art/blender/assets/weapons.py`
writes them.

### 6.1 Guns

| Gun | Mesh | Sockets per slot | Clips (`clipRoles`) | Icon |
|---|---|---|---|---|
| CHOPPER | `SK_Chopper`, in progress (template `SKM_Rifle` stands in) | `Optic` (0.115, 0, 0.0418) on the top-cover rail, **missing**; `MuzzleMount` (0.426, 0, 0) with the booster split off as bone or section `Booster`, **missing**; the existing Muzzle, Eject, SightRear, SightFront, RecoilPivot, MagHinge, Palm_R, Palm_L | in progress (the pack's rifle clips adapted, ANIMATION.md) | `T_UI_Gun_Chopper`, missing |
| NINE | `SK_Nine`, in progress (template `SKM_Pistol`) | `Laser` (0.156, 0, −0.0335) under the dust cover, **missing** | missing beyond the template pistol clips; no inspect, magazine check or swing (rifle clips) | `T_UI_Gun_Nine`, missing |
| STICK | the pack's `SK_TFA_AR_Default_Combined`, exists on the box (import script); `fallbackMesh` the template rifle | `Optic`, `MuzzleMount`, `Underbarrel`, `Laser`, `MagHinge`, `Handguard`, `Stock`: the pack's parts exist, socket names written on import; `MuzzleMount`, `Underbarrel` and `Laser` per handguard length | in progress: the pack's own clips, no adaptation | `T_UI_Gun_Stick`, missing |
| RATTLER | `SK_Weapon_Rattler`, **missing**: a skeletal, first-person-grade `SM_Weapon_GoonSMG` (which exists) with bones bolt, trigger, magazine, knob and `MuzzleDevice`, a 4096 set, origin on the bore at the back of the receiver; template rifle meanwhile | `MuzzleMount` (0.41, 0, 0), **missing**; markers from the Goon SMG's sockets (`guns.json` notes) | missing: the pack's rifle clips adapted to the stick magazine and the left knob | `T_UI_Gun_Rattler`, missing |

### 6.2 Attachments

All thirteen are the pack's parts and **exist**. Their asset paths are filled into `attachments.json
presentation.mesh` from the import listing; null until then, which shows nothing and changes no rule. What each needs
in addition:

| Part | Needs | Status |
|---|---|---|
| Scope | `SightEye` socket on the eye axis at the ocular; a reticle lens material | missing |
| Irons | the folded state when an optic is fitted | exists (pack), state switch missing |
| Silencer | `Muzzle` socket at its end; suppressed gun sounds (`audio.json`) | missing |
| Grips | `SupportHand` socket; the left-hand poses `GripVertical`, `GripAngled` | socket missing, poses exist (pack) |
| Laser | `Beam` socket; a Niagara beam and dot (line-batcher placeholder like the tracers) | missing |
| Clear mag | `RoundsShown` material parameter | missing |
| Handguards | per length: `MuzzleMount`, `Underbarrel`, `Laser`, `Muzzle`, `Palm_L` | names from the import |
| Stock | folded and open states | exists (pack variants) |
| Icons | one small pip icon per part (`T_UI_Att_<id>`) | missing |

### 6.3 Crew

| Member | Arms | Glove | Sleeve | Skin | Jewellery | Portrait |
|---|---|---|---|---|---|---|
| RULE | `SK_RuleArms`, in progress | leather and suede, exists | none | exists | watch and bracelet, in progress (the bracelet's offset is to be copied from `SK_RuleArms.sockets.json`) | missing |
| DEUCE | same | fingerless knit (`SK_Crew_Glove_FingerlessKnit`), missing | hoodie pushed up, missing | `MI_Crew_Skin_Deuce`, missing | gold rope, missing | missing |
| SMOKE | same | knuckle tape over bare hands, missing; needs the hand skin detail the glove hides today | bomber cuff, missing | missing | wooden beads, missing | missing |
| KEYS | same | Rule's glove with two fingertips cut off, wool instances, missing | denim cuff, missing | missing | digital watch on Rule's watch frame, missing | missing |

The variants go through the proven path of `CHARACTERS.md`: SDF surfaces on the mannequin's bones, weights
transferred per region, imported onto the existing `SK_Mannequin`. Never a real person's likeness, no logos, no
maker's marks.

### 6.4 Front end

The stage room, bench and turntable (`frontend.json stage`), the level thumbnail `T_UI_Level_Block`, the gun icons,
the part pips and the crew portraits are missing. Engine shapes and text stand in for all of them. No binary asset is
needed to run the flow.

### 6.5 Licence

The pack (Fab licence) and Epic's mannequin content are used but never committed. A clean checkout has no STICK mesh
and no pack clips. The STICK then uses `fallbackMesh`, its parts show nothing, and every rule and test still works.
Only data, scripts and pictures of our own work are committed.

---

## 7. Save data

One `USaveGame` (`UMISaveGame`, ARCHITECTURE 2.2 `Core/Settings`), slot `MurderInc`, holds the nine existing
settings, the best Hold the Block score and a new `Setup` block (`frontend.json save`):

```
struct FMISetupSave
{
    int32 Version = 1;
    FName Crew;                                  // crew.json id
    TArray<FName> Guns;                          // up to 4, slot order
    TMap<FName, FMIGunBuildSave> Builds;         // gun -> (slot -> part or NAME_None); every gun ever built
    TMap<FName, FName> FireModes;                // gun -> auto | semi, the last used
    FName Level;                                 // levels.json id
    TArray<FName> Seen;                          // ids looked at (NEW badges)
    bool bPlayed = false;                        // Same set-up shows the remembered set-up
};
```

Mode, difficulty and time stay the existing settings keys (`mode`, `difficulty`, `time`) and are not duplicated.

**When it is written:** on every Next, on Done in the Workbench, on Hit the block and on Same set-up.

**When it is read:** at boot, then validated, in this order:
1. Unknown crew → `rule`; unknown level → `block`.
2. Unknown guns are dropped. If none remains → the parity guns.
3. Parts not in the gun's options are dropped. A required slot without a valid choice takes its default.
4. Duplicates and gaps are removed, and the list is cut to four.
5. A mode the level does not provide → the level's first mode.

So a removed pack degrades to a playable set-up and never to a crash. `MISetup dump` (console) prints the set-up as
JSON for bug reports.

---

## 8. Tests

All headless (`tools/box/test.sh`), named `MurderInc.*`.

### 8.1 Parity of the default set-up

| Test | Proves |
|---|---|
| `Loadout.ParityResolve` | the resolver's output for the parity set-up equals `Config.Weapons` field by field, doubles compared exactly, the new fields equal their defaults (1.2), and the view data equals `FMIViewmodelData::Load` |
| `Loadout.ParityGolden` | the 13 weapon golden scenarios (`golden/weapon.json`) replayed with `FMIWeaponRules::Init(resolved parity data)` match every recorded number and event, as `Golden.Weapon` does with the config |
| All existing `Golden.*`, `Weapons.*`, `Core.*` | unchanged and green: no new field reaches them except through its default |

### 8.2 One test per attachment effect

`MurderInc.Attachments.<part>.<stat>` is a complex automation test whose cases come from `attachments.json`, so a new
part gets its tests by being added. Each case resolves the gun with only that part fitted (on the first gun of the
compatibility table that takes it) and measures the stat with its probe. It compares against the same gun without the
part and the same seed: no effect adds a draw, so the ratios are exact.

| Probe (stat) | Measurement |
|---|---|
| `adsTime` | frames at 60 Hz from aim held to `Ads` = 1 = ceil(resolved × 60) |
| `adsFov`, `adsLook` | `FMIPlayerRules` view FOV at full aim (settled) = value ± 0.01°; look delta at full aim for a unit input |
| `spread.*` | settled `Spread` standing (hip, aimed) and at `spreadSpeedRef` (moving), no bloom, = resolved (degrees) |
| `recoil.pitch`, `recoil.yaw` | sum of `KickPitch` / `KickYaw` over 12 rounds ÷ the same without the part = factor (1e-9); the view data's kick rise, back, yaw and roll scaled alike |
| `swapTime` | frames of holster + draw |
| `reloadTime` | time from `start` to `magin` and to `done` = marks × factor |
| `noise` | `WeaponFire.NoiseRadius`; with enemies, a Goon at 30 m is alerted by a bare round and not by a silenced one, and one at 15 m by both |
| `flash` | `OnRoundFired` flash scale and light |
| `falloff.*` | hitscan at a dummy at 20, 37.5 and 60 m: 26, the linear value, 22.1 (CHOPPER + silencer) |
| `length` | the distance the wall probe asks the host for |
| `sway` | `FMIGunViewData::SwayMax` |

The first version has 53 cases (scope 6, silencer 9, vertical grip 4, angled grip 4, laser 4, clear mag 2, short
handguard 11, long handguard 6, folded stock 7). It also has four `…Baseline` cases asserting that irons, the standard
mag, the standard handguard and the open stock change nothing.

### 8.3 Four guns

`Weapons.FourGuns`, a scripted rules run:
- 1–4 select;
- Q goes back to the last gun used;
- the wheel and next/previous cycle and wrap;
- a third gun requested mid-holster retargets;
- the current gun requested mid-holster comes back up, mid-draw holsters again;
- the RATTLER's 0.24 / 0.27 s and the STICK's 0.28 / 0.32 s;
- separate magazines; `Resupply()` 90 / 240 and 96 / 256, the NINE untouched;
- the Selector blocks fire for `ModeSwitch` s and then flips, and is cancelled by a swap;
- semi buffering on the STICK;
- the magazine check never changes rule state;
- a set-up with one gun ignores every switch input.

### 8.4 A scripted walk through the whole flow

`Frontend.Walk` (rules only, `FMIFrontEndRules`), then `Frontend.WalkWorld` (play in editor). Both are driven by the
console `MIMenu <action> [args]`, the menu twin of `MIInput`.

1. Boot: Home. The summary shows the parity set-up; `Same set-up` is labelled `firstTime`.
2. Hit the block → Crew. Pick `deuce` → Next → Loadout. The slots show CHOPPER and NINE.
3. Carry `stick` (slot 3) and `rattler` (slot 4). A fifth carry asks for a slot. Move slot 4 to slot 1. Empty slot 2
   (the rest close up). Carry `nine` again.
4. Workbench on the STICK: fit the scope, the silencer and the short handguard. The effect lines and stat bars equal
   the resolver's. Reset build. Fit them again. Q / E to the RATTLER: one slot (muzzle). Done.
5. Next → Block: pick night (the sky switches). Next → Style: Hold the Block, Kingpin. Next → Briefing: the four
   lines read back the set-up, and the radio line says `Deuce`.
6. Back four times → Crew, every choice still selected. Next three times → Briefing (on the gamepad path, to check the
   focus orders) → Hit the block.
7. The run starts: slot 1 is the RATTLER, the bar has four slots, the STICK's FOV at full aim is 30°, and the radio
   says `Deuce, it's the Vault…`.
8. Die (`MIFlow kill`): the card shows `Deuce down` and `Change set-up`. Change set-up → Loadout with everything
   remembered. Back to Home: `Same set-up` → intro with the identical set-up.
9. Quit and load: the set-up is restored. Corrupt the save (an unknown gun, a part that does not fit): it loads as the
   validated set-up.
10. Picture review: `WalkWorld` writes one screenshot per screen to `docs/unreal/shots/frontend-<screen>.jpg`, to be
    looked at as with the block pictures.

### 8.5 Data and save

`Loadout.DataLoads` checks the rules of 3.1, the `provides` counts (the block: 3, 29 / 17, 21 explosives, 14 title
keys) and that every `frontend.*` key that is used exists. `Save.SetupRoundTrip` writes a set-up and reads it back
equal. `Save.SetupValidation` covers each rule of 7.

### 8.6 Existing tests that change

`Core.GameClasses` counts 38 key mappings today. It becomes 38 plus the actions of `frontend.json input.game` (the
mapping count is not a parity number). No golden file is regenerated.

---

## 9. Build order

Each step is testable alone:

1. `FMILoadoutData`, loading, `Loadout.DataLoads`.
2. The resolver and `Loadout.ParityResolve`.
3. The new `FMIWeaponDef` fields through the rules (per-gun timing, falloff, noise, aim view) and `Loadout.ParityGolden`.
4. Four-gun switching, `Resupply()`, fire modes, `Weapons.FourGuns`.
5. Attachment effects and `Attachments.*`.
6. `UMIGunAssembly` and the marker overrides, with the template meshes.
7. The HUD's four slots and the wheel.
8. `FMIFrontEndRules`, `UMIRunSetupSubsystem`, save, and `Frontend.Walk`.
9. The Slate screens and `AMIShowroom`, then `Frontend.WalkWorld`.
10. Crew looks and lines.
11. The pack's clips (inspect, magazine check, selector, swings) when ANIMATION.md lands.

---

## 10. Open questions for the user

Each has a default; work proceeds on the default until the user answers.

1. **The pack's rifle as one gun or three.** The three handguard lengths could be three roster guns. **Default:** one
   gun, the STICK, with the lengths and the stock as attachments, because they share every clip and rule and the
   player can build each one.
2. **Fewer than four guns.** **Default:** a set-up may carry one to four. The default carries two (the CHOPPER and the
   NINE), which parity needs.
3. **Names.** STICK, RATTLER, DEUCE, SMOKE and KEYS are placeholders. **Default:** keep them until you replace them
   (text and ids live only in data).
4. **Crew perks.** **Default:** cosmetic only. If you want perks, the recommendation is one small,
   presentation-adjacent perk per member (for example 5 % faster swaps), with its own golden tests and never on Rule.
5. **Slow motion while the weapon wheel is open.** **Default:** no; the game runs at full speed.
6. **The scope on the CHOPPER's top-cover rail.** It looks unusual on an AK-pattern gun. **Default:** allowed. The
   RATTLER takes no scope (its rail is too short).
7. **The laser.** **Default:** always on, with no key, and fading while aimed.
8. **The pack's jams, syringe and grenade.** **Default:** left out (section 5). The grenade and the syringe are the
   natural first additions to Hold the Block if you want them later.
9. **Same set-up skips the briefing.** **Default:** yes, one press from Home to the intro.
10. **Time of day on the Block screen rather than with the game style.** **Default:** on the Block screen (1.3).
