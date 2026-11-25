# Three levels: progression and systems (design)

Status: design for the three-map release (DECISIONS.md 2026-11-25 ~21:40). Nothing here is built. This file covers how
the story runs across Level 1 → 2 → 3: the story thread and per-level text, unlocks, what carries over and what resets,
the front end (level select, continue, thumbnails), the end of each level, where progress is saved on a streamed game,
Hold mode per map, difficulty, map travel without a long black screen, and the engine, data and test changes, with
files. The level designs are [chinatown.md](chinatown.md) (Level 2) and [midtown.md](midtown.md) (Level 3). Section 12
lists the small changes those two need to match this file.

Two rules apply everywhere. First, **the Block does not change**: level.json, text.json, the rules and every golden replay
stay byte for byte, and anything new that the Block shows (a teaser line, a "Next" button) is drawn outside the flow
rules and their events. Second, **E3DS is the target**: an RTX A4000 with 8 threads, SM5, no Nanite, and a fresh machine
for every session. Max Session Time is 15 minutes today (PREFLIGHT.md section 3), and the game takes about 34 s to start.

Units and conventions are those of level.json (web metres, +Y up, x east, z south).

---

## 0. Decisions in one table

| Question | Decision (recommended) | Why |
|---|---|---|
| How the levels connect | **A campaign of three levels in a fixed order.** Clearing a level's Story opens the next one. The debrief offers **Next: <level>**, which travels there with the same set-up | The owner: "the player needs to progress to 3 levels" |
| Locks | Level 1 is always open. Level 2 opens when Level 1's Story is cleared on any difficulty, and Level 3 when Level 2's is. Hold mode on a map opens with that map | Simple, and the same at every difficulty |
| Run unit | **Each level is its own run**, with its own intro, debrief and rating. Health, ammo and enemies reset at each level. Crew, guns, attachments, mode, difficulty and time carry over (they are the set-up) | The rules reset everything at Begin, and the goldens pin that. A session continued from a code has no carried health anyway |
| Death | Restarts the current level only (the level is the checkpoint). Retries count per level | Today's "no checkpoints" applies within a level |
| Score | A Certification per level (0 to 5 points, as now) and the best one kept per level. After Level 3 the **album card** adds the three bests up (0 to 15) and gives an album certification | Stays a reward and needs no rules change |
| Difficulty | Chosen in Style and can be changed between levels. It does not affect unlocks. The level card shows the best rating and the difficulty it was earned on | No forced restart for a player who finds kingpin too hard |
| Hold mode | On every map, under its own name: Hold the Block, Hold Canal Street, Hold the Square. One best score per map | Each map has ground and air spawns |
| Where progress lives | **Three layers.** (1) The save game on the machine, which lasts for the session. (2) **The IPX Game OS page**, which stores the progress code in the browser through the stream's data channel, automatically. (3) **The progress code** (`XXXX-XXXX`), shown on every debrief and in a Progress drawer and typed in on any machine, so it works with no page support at all | Every E3DS session is a fresh machine, so the save game alone is lost each time |
| Session length | Raise E3DS Max Session Time to **30 minutes** for this release (owner's call). The game warns before the limit and shows the code | First-time play of all three levels takes about 19 minutes, more than 15 |
| Travel | A hard map travel (`OpenLevel`) from game code. The next map is **preloaded while the debrief is open**, a Slate **loading card** is drawn during the load (it is streamed, so the picture never goes black), and a per-map PSO cache is cooked. Target: 10 s or less from Next to the intro on E3DS. Fallback: one persistent map with level instances (section 6.6) | The fastest path that keeps the current code layout. The console's `open` is refused, so travel has to be game code |
| Text | Per-level overlays in frontend_text.json at `frontend.story.<level>.*`, with the **same key paths as text.json** (`radio.intro`, `cards.debrief.kicker`, ...). A key missing from the overlay falls back to text.json. The Block's overlay contains no text.json key | Golden.Directors keeps reading the Block's lines unchanged |
| Reel numbering | One album across the campaign: **Reels 1 to 3 on the Block (unchanged), 4 to 6 on Canal Street, 7 to 9 in Midtown**. The HUD tally still counts the level (0 / 3 to 3 / 3) | The story is nine masters, one album. Nothing in the rules reads the code as a number |

---

## 1. The story across three levels

### 1.1 The thread

The Vultures did not take three reels. They took **the whole album: nine masters**. Level 1 is still exactly the
existing Block story, unchanged ("three master reels", the avenue, the chop shop, the cage). The campaign adds what
Rule learns after it, in lines that sit outside the rules: the briefing, the debrief teaser and the loading card.

Everything happens on one day and night. The Block is at 4:15 PM, Canal Street at 7:40 PM, and Midtown at 11:58 PM,
two minutes before the buyer's midnight premiere. Each level's place line already carries its time, so the clock moves
on with every level.

| Level | Place line | Story beat | The three masters | Extraction |
|---|---|---|---|---|
| 1 · **The Block** | Hollis, Queens · Jamaica Ave · 4:15 PM (day) | The Vultures stashed three masters on the block before moving them (DESIGN.md: "before moving them") | Reel 1 The Avenue, Reel 2 Chop Shop, Reel 3 The Cage | IPX truck, south end of the lot |
| 2 · **Canal Street** | Chinatown, Manhattan · Canal St · 7:40 PM (night) | They ran three more down to Canal Street, where their bootleg operation copies masters in a back-room dub room and sells the copies off the tables | Reel 4 The Tables, Reel 5 The Market, Reel 6 The Dub Room | IPX truck, east end of Canal |
| 3 · **Midtown** | Midtown, Manhattan · Seventh Av · 11:58 PM (night) | The last three went uptown. The Vultures' buyer means to premiere the stolen album on the square's big screens at midnight | Reel 7 The Tank, Reel 8 The Gantry, Reel 9 The Booth | IPX truck on W 46 St, south end of the square |
| **The album** | after Level 3 | Every master is in the vault | | |

The IPX Vault stays the only radio voice (typed lines with squelch). Rule keeps his placeholder barks. The buyer stays
unnamed and unseen, so no new character needs a voice (open question 3).

### 1.2 Where each kind of line is shown

| Line | Shown | Read by the rules? | Block source |
|---|---|---|---|
| Place line, tagline (location card) | Intro, at 0.25 s | No (HUD) | text.json, unchanged |
| Intro radio | Intro, at 0.9 s | Yes (`hud:radio`) | text.json, unchanged |
| Objective lines (4), reel radio (3), done radio, refusal prompt | In play | Yes | text.json, unchanged |
| Debrief kicker and title, dead-card time label | Cards | Yes (`menus:card`) | text.json, unchanged |
| **Briefing plan** (3 short lines) | Briefing screen | No | New, `frontend.story.block.briefing.plan` |
| **Loading card** (kicker, title, place, line, boot ticker) | During travel | No | New, `frontend.story.<to>.loading` |
| **Debrief teaser** (one Vault line under the stats) | Debrief card, only while a next level exists | No (drawn by the menu layer, no event) | New, `frontend.story.block.teaser` |
| **Album card** | After Level 3's debrief | No | New, `frontend.campaign.album` |

### 1.3 The campaign lines in the game voice

The tone is dry, calm and brief, in short street sentences in the second person. `{name}` is the crew member's call
name, and for Rule it resolves to "Rule", so Rule's lines read word for word as written.

**Level 1, The Block** (only lines outside the rules; everything else stays text.json):

- Briefing plan:
  1. "Three masters on this block: the avenue, the chop shop, the cage."
  2. "Every reel you grab brings more of them."
  3. "All three in hand, the IPX truck rolls from the lot."
- Loading card (when travelling back to the Block): kicker "Level 1 of 3", title "The Block", line "Where it started.
  Three masters on one block."
- Debrief teaser: "Three back. The session sheet says nine. Six are still out, and the Vultures are running them to
  Canal Street."

**Level 2, Canal Street** (the radio lines are the Chinatown design's, re-keyed. Durations follow the Block's typing
pace, about characters / 58 + 2.2 s, and are tuned by ear):

| Key | Text | Chars | secs |
|---|---|---|---|
| radio.intro | "{name}, it's the Vault. Vultures moved three more masters to Canal — the tables, the market, the dub room. Bring them home." | 121 | 4.3 |
| radio.introHoldout | "{name}, it's the Vault. Vultures are coming out of every door on Canal. Hold the street." | 86 | 3.7 |
| radio.reel[0] | "That's one. Canal heard it — more coming." | 41 | 2.9 |
| radio.reel[1] | "Two. They're pouring out of the back rooms." | 43 | 2.9 |
| radio.reel[2] | "All three. The IPX truck is idling at the east end of Canal. Cut through the arcade. Move." | 90 | 3.8 |
| radio.done | "Masters are in the vault. Canal's clean, {name}. They're taking what's left uptown." | 81 | 3.6 |

- Briefing plan:
  1. "Three masters on Canal: a bootleg table out front, the market's cold room, the dub room off Mott."
  2. "Close quarters. They come out of doorways, not just the street ends."
  3. "The IPX truck waits at the east end of Canal."
- Loading card: "Level 2 of 3" / "Canal Street" / "Chinatown, Manhattan · Canal St · 7:40 PM" / "They're cutting copies
  in the back rooms. Pull the masters out."
- Debrief teaser: "Six home. The last three went uptown. Their buyer wants your album on the big screens over the square
  at midnight."

**Level 3, Midtown** (the Midtown design's lines, re-keyed, with `{name}`):

| Key | Text | Chars | secs |
|---|---|---|---|
| radio.intro | "{name}, it's the Vault. Last three masters are on these roofs and down in the square. Their buyer wants your album on the big screens at midnight. Not tonight." | 157 | 4.9 |
| radio.introHoldout | "{name}, it's the Vault. The square's full of Vultures. Hold it down as long as you can." | 85 | 3.7 |
| radio.reel[0] | "One back. Every roof heard that. They're coming over the top." | 61 | 3.3 |
| radio.reel[1] | "Two. That screen's dead. Last one's in the booth under the stand. Get down there." | 81 | 3.6 |
| radio.reel[2] | "That's all three. The IPX truck is on Forty-Sixth, south end of the square. Move." | 81 | 3.6 |
| radio.done | "Every master's home. The city's yours, {name}." | 44 | 3.0 |

- Briefing plan:
  1. "Three masters: the tank house up top, the gantry behind the big screen, the booth under the stand."
  2. "Work down the roofs. Stairs and the scaffold get you to the street."
  3. "The IPX truck is on Forty-Sixth, south end of the square."
- Loading card: "Level 3 of 3" / "Midtown" / "Midtown, Manhattan · Seventh Av · 11:58 PM" / "Midnight over the square.
  Last three masters."
- No teaser: Level 3's debrief leads to the album card.

**The album card** (after Level 3): kicker "IPX Vault · The album", title "Every master's home", line "Nine masters.
One night. The album is yours." Below the line come three rows, one per level ("Level 1 · The Block — Gold · Boss"),
then the album certification. Its points are the sum of the three best ratings:

| Album points | 0–3 | 4–6 | 7–9 | 10–12 | 13–14 | 15 |
|---|---|---|---|---|---|---|
| Album certification | Demo | Mixtape | Single | Gold | Platinum | Diamond |

The names are the existing `text.ratings`. The card plays the voice trigger `album.complete` (new) with the existing
`rule_chant` bark (the crowd answers).

---

## 2. Progression rules

### 2.1 Unlocks

- `levels.json campaign.order = ["block", "chinatown", "midtown"]`, with `unlock: "previous"`.
- Level *i* is **open** when *i* = 0 or level *i-1* is **cleared**. Cleared means its Story reached Complete once, on any
  difficulty, retries allowed.
- Hold mode on a level is open when the level is open.
- The album card is offered when all three levels are cleared. `albumSeen` is set the first time it is shown, and the
  Level screen then shows a small "ALBUM · Gold" badge.
- Opening a level never closes one. All progress data only ever goes up (merge = maximum per field, section 4.5).
- A remembered `Setup.Level` that is not open, for example after a fresh session with no code, falls back to the
  **furthest open level**. This is a new rule in frontend.json `save.validation`; the existing rule "unknown → block"
  still applies first.

### 2.2 What carries over and what resets

| Thing | Next level | Same level, Run it back / after death | Note |
|---|---|---|---|
| Crew | carries | carries | set-up (UMIRunSetupSubsystem is a GameInstance subsystem and survives travel) |
| Guns (1 to 4), slot order, every build and attachment | carries | carries | set-up |
| Mode (Story / Hold) | carries | carries | Next is shown only after Story |
| Difficulty | carries | carries | can be changed with Change set-up |
| Time of day | the next level's first `times` entry if the current one is not offered | carries | Block: day. Canal and Midtown: night |
| Health, armour state | reset (full) | reset | rules Reset() |
| Ammo: magazines and the shared bag of rounds | reset (full) | reset | rules Reset() |
| Enemies, explosives, reels | the level's own | reset | |
| Time, kills, accuracy, retries | per level | retries +1 after a death, 0 on Run it back from the debrief | today's rule, per level |
| Certification | best per level, saved | | |
| Hold best score | per map, saved | | the Block keeps the existing `Best` field |
| NEW badges (`Seen`) | global | | levels join the seen list when their card is focused once open |

### 2.3 End of a level

```
Story Complete (rules) ─ 0 s ──── sting, radio.done, the progress record is written (2.4); the next map starts preloading (6.2)
                        3.3 s ─── debrief card (flow.timing.debriefCard, unchanged)
                                   stats: Certification, Time, Accuracy, Vultures dropped, Retries (unchanged)
                                   + teaser line (Levels 1 and 2), + "Progress code 4FMY-N7W6"
                                   items, in this order, the first focused:
                                     Level 1, 2:  Next: <level> · Run it back · Change set-up · Back to title
                                     Level 3:     The album · Run it back · Change set-up · Back to title
Dead (rules)            1.5 s ─── dead card (unchanged): Run it back (this level) · Change set-up · Back to title
Hold mode over                    dead card with Score and Best for this map (the best is per map, 2.5)
```

- `next` and `album` are added by the subsystem's menu patch layer, the same way `changesetup` is today
  (MIGameSubsystem.cpp 466-478), not by FMIMenus' card build. They are added only when a campaign next step exists
  and the boot is not a test or parity boot (`bTestBoot`), so the `menus:card` events of every golden replay stay the
  same. Section 9.3 adds a test that pins this.
- "Back to title" in a new map shows the front end in that map, with that level's title camera path.
- "Run it back" never travels. "Next" always travels.
- "Level select" (on the album card) opens the front end on the Level screen.

### 2.4 What is recorded on Complete

The record is written for Story only, never in parity or test boots:

```
rec = Progress.Levels[levelId]
rec.Clears += 1; rec.bCleared = true
if card.points > rec.BestPoints or (== and difficultyRank > rec.BestDifficultyRank): rec.BestPoints, rec.BestDifficulty = ...
save game written; bridge message sent (4.4); the code on the card is the code after this update
```

For Hold mode, on the dead card: when the score beats the map's best, Levels[id].HoldBest is updated (for the Block,
the existing `Best`), followed by the same save and bridge message.

### 2.5 Hold mode per map

| Map | Mode name | Tagline | Intro radio | Best kept in |
|---|---|---|---|---|
| Block | Hold the Block (text.json, unchanged) | "One block. Endless Vultures." (unchanged) | text.json, unchanged | `UMISaveGame.Best` (unchanged) |
| Canal Street | Hold Canal Street | "One street. Endless Vultures." | `frontend.story.chinatown.radio.introHoldout` | `Progress.Levels.chinatown.HoldBest` |
| Midtown | Hold the Square | "One square. Endless Vultures." | `frontend.story.midtown.radio.introHoldout` | `Progress.Levels.midtown.HoldBest` |

The rules (spec 04 3.11) and the wave growth are the same everywhere. Midtown's Hold uses the street layer only
(midtown.md 7.2).

### 2.6 Difficulty

- The tables in config.json `flow.difficulty` stay global and unchanged: 3 waves, patrol, maxAlive, pursuit.
- A level may override only `tuning.rating.time` (Midtown: [[330, 2], [480, 1]], because its route is longer) and the
  Buzzard ceiling (midtown.md 16.3). Per-level wave tables are not in this release (open question 5).
- Rating time thresholds per level are Block [[270, 2], [400, 1]] (config.json, unchanged), Canal Street
  [[270, 2], [400, 1]] (no override; re-tune after playtests), and Midtown [[330, 2], [480, 1]].

---

## 3. The front end

### 3.1 Flow with three levels

```
Home ── Hit the block / Continue ─────────────────────────────────────────────────► (travel if needed) ► intro
  │
  ├─ Gear up ► 1 Crew ► 2 Loadout (► Workbench) ► 3 Level ► 4 Style ► Briefing ► (travel if needed) ► intro
  │
  └─ Progress (drawer): your code · Enter a code
```

The merged "where" screen splits into **Level** (step 3) and **Style** (step 4), because frontend.json
`screens.where.mergeWhile` ("order has one level") is no longer true. Both screens are already designed (frontend.json
`level`, `style`, `only: "split"`) but not built (FMIFrontEndRules has six fixed screens). Building them belongs to this
release. SMIFrontEnd is in the readiness lane's menu scope for v6, so the work starts after v6 ships.

### 3.2 Home

| State | Primary button | Summary line |
|---|---|---|
| Nothing cleared | **Hit the block** (as now) | `{crew} · {guns} · The Block · {time} · {mode} · {difficulty}` |
| A level open but not cleared, beyond the Block | **Continue · Canal Street** (`frontend.home.continue`, template `Continue · {level}`). Sets Setup.Level to that level, then starts as "Hit the block" does | that level's name |
| All cleared | **Hit the block**, with the remembered level | remembered level |

- First-time play (`played` false) still opens Crew, as now.
- When the bridge (4.4) delivers progress after Home is already showing, the button and the summary update in place,
  with a 0.2 s cross-fade, and focus stays where it was.
- A new secondary link, **Progress**, opens the progress drawer (3.6).

### 3.3 Level screen (step 3): three cards

The layout is three 16:9 cards in a row. Each thumbnail is 400 x 225 px at 1080p, with a 32 px gap (1,264 px wide),
scaling as the other screens do. At 1280 x 720 the cards are 266 x 150. Each card shows:

```
┌──────────────────────────────┐
│ [thumbnail 16:9]             │  locked: desaturated 85 %, brightness 35 %, padlock glyph centred
│                              │
├──────────────────────────────┤
│ LEVEL 2                      │  frontend.level.number "Level {n}"
│ Canal Street                 │  frontend.levels.chinatown.name
│ Chinatown, Manhattan · 7:40 PM│ the level's place line (short form: frontend.levels.<id>.placeShort)
│ Plays Story · Hold Canal St  │  frontend.level.modes, with the per-level Hold name
│ ▸ state line                 │  see below
└──────────────────────────────┘
```

| State | State line | Next button |
|---|---|---|
| Locked | "Locked · Finish The Block to open" (`frontend.level.lockedHint`, `Finish {level} to open`) | disabled. A press shows the hint in the message line |
| Open, never played | "NEW" badge (the existing Seen rule) | enabled |
| Open, played, not cleared | "Not cleared yet" | enabled |
| Cleared | "Cleared · Gold · Boss" (`frontend.level.cleared`, `Cleared · {rating} · {difficulty}`) | enabled |
| Hold best (any open level with a best > 0) | second line: "Hold Canal Street best 12,345" | |

- Locked cards can be focused, so a player can see what comes next. The cards are never "coming soon" placeholders:
  every card is a real level (LOADOUT.md 2.7).
- Thumbnails: `/Game/UI/Levels/T_UI_Level_Block` (title key 3, the avenue under the El), `T_UI_Level_Chinatown` (key 1,
  the tables), and `T_UI_Level_Midtown` (key 2, the gantry LED wall). Each is 768 x 432, BC7 sRGB, no mips, UI texture
  group, never streamed (about 330 KB each). They are made on the box by a committed script, `Content/Python/mi_level_thumbs.py`,
  which opens each art map, places a CineCamera at the title key and captures through SceneCapture with the level's
  rig. They are committed as source PNGs in `art/ui/levels/` and imported by the same script. Packaging adds
  `/Game/UI` to DirectoriesToAlwaysCook, because every map's front end needs all three.
- Until a thumbnail exists, the card shows a flat panel in the level's key colour (Block #c9a36a, Canal #c2323a,
  Midtown #2f6fd6) with the name. The game must never show a missing-texture checkerboard.

### 3.4 Style screen (step 4)

- Mode: Story, or the level's Hold name. Hold is offered when the level provides air and ground spawns (FMIReadiness,
  as now).
- Difficulty: hustler, boss or kingpin, unchanged.
- Time: the level's `times`. With one entry (as on all three levels in this release) the time is shown as fixed text,
  "Night", not as a picker.
- The tagline line uses the level's overlay (`location.tagline` or `location.taglineHoldout`).

### 3.5 Briefing

The kicker and title are unchanged ("IPX Vault · The plan", "Here's how it goes"). New: the level's three
`briefing.plan` lines, between the title and the set-up rows. The "Block" row shows "Level 2 · Canal Street". The go
button stays "Hit the block" on every level, because it is the game's verb.

### 3.6 Progress drawer and code entry

- The drawer shows "Your progress", the code in large monospace (`4FMY-N7W6`), the hint "Write it down. Enter it on any
  machine to pick up where you left off.", and, when the page bridge is connected, "Saved on this page too."
- **Enter a code**: eight boxes with one character each. Keyboard typing goes straight in. On a pad, up and down
  cycle through the 32 characters of the alphabet, left and right move between boxes, and A confirms. Hyphens and spaces
  are ignored, letters are read upper case, and O, I and L are read as 0, 1 and 1.
- A good code shows "Welcome back. Midtown is open." (`frontend.campaign.code.ok`, `{level}` = the furthest open level),
  merges the progress (4.5) and saves it.
- A bad code shows "That code doesn't check out." and changes nothing. There is no limit on attempts: the codes guard
  nothing.

### 3.7 The loading card

- Full screen, drawn by Slate, so it renders while the game thread is loading (section 6.3). It shows the destination's
  kicker ("Level 2 of 3"), title ("Canal Street"), place line, its line, and a **boot ticker** that cycles the
  destination's `boot` lines every 1.2 s, for example "Lighting the signs…".
- The background is the destination thumbnail, blurred and at 40 %, with a thin progress bar that eases to 90 % over
  the expected load time (an estimate, never a lie about completion) and fills when the map is ready.
- Audio is a low radio-static loop (the existing `radio_in` texture, looped at -18 dB).
- The card stays up until all of these hold: (a) the map is loaded, (b) Boot is done, (c) the PSO precompile queue is
  empty or 6 s have passed, and (d) texture streaming has settled or 2 s have passed. Then it fades over 0.3 s into the
  intro.

### 3.8 New text (frontend_text.json, under `frontend`, no text.json key shadowed)

```json
"home": { "continue": {"$template": {"template": "Continue · {level}", "params": ["level"]}}, "progress": "Progress" },
"level": {
  "number": {"$template": {"template": "Level {n}", "params": ["n"]}},
  "locked": "Locked",
  "lockedHint": {"$template": {"template": "Finish {level} to open", "params": ["level"]}},
  "notCleared": "Not cleared yet",
  "cleared": {"$template": {"template": "Cleared · {rating} · {difficulty}", "params": ["rating", "difficulty"]}},
  "holdBest": {"$template": {"template": "{mode} best {score}", "params": ["mode", "score"]}},
  "album": {"$template": {"template": "Album · {rating}", "params": ["rating"]}}
},
"campaign": {
  "next": {"$template": {"template": "Next: {level}", "params": ["level"]}},
  "albumButton": "The album",
  "levelSelect": "Level select",
  "codeLabel": "Progress code",
  "album": { "kicker": "IPX Vault · The album", "title": "Every master's home",
             "line": "Nine masters. One night. The album is yours.",
             "row": {"$template": {"template": "Level {n} · {level} — {rating} · {difficulty}", "params": ["n", "level", "rating", "difficulty"]}},
             "total": "Album certification" },
  "progress": { "title": "Your progress", "hint": "Write it down. Enter it on any machine to pick up where you left off.",
                "page": "Saved on this page too.", "enter": "Enter a code" },
  "code": { "ok": {"$template": {"template": "Welcome back. {level} is open.", "params": ["level"]}},
            "bad": "That code doesn't check out." },
  "session": { "warn": {"$template": {"template": "About {m} minutes left in this session. Your progress code: {code}", "params": ["m", "code"]}},
               "last": {"$template": {"template": "Session ends in 2 minutes. Progress code {code} is on the pause menu.", "params": ["code"]}} },
  "travelFailed": {"$template": {"template": "Couldn't load {level}. Back to the title.", "params": ["level"]}}
},
"levels": {
  "block":     { "name": "The Block", "blurb": "Jamaica Ave under the El. The avenue, the chop shop, the cage, the lot.", "placeShort": "Hollis, Queens · 4:15 PM" },
  "chinatown": { "name": "Canal Street", "blurb": "Chinatown after the rain. The tables, the market, the dub room. Tight corners, lots of neon.", "placeShort": "Chinatown, Manhattan · 7:40 PM" },
  "midtown":   { "name": "Midtown", "blurb": "Over the square. Roofs, water tanks, the big screens. Then the street.", "placeShort": "Midtown, Manhattan · 11:58 PM" }
}
```

The existing `frontend.levels.block` keys keep their values. `placeShort` is added.

---

## 4. Saving progress on a streamed game

### 4.1 The problem

E3DS gives every session a fresh machine: Linux servers copy the whole game for each session (PREFLIGHT.md 4). The
save game (`Saved/SaveGames`) exists only for that session. The visitor's browser is the only thing that lasts, and
the game reaches it only through the Pixel Streaming data channel and the IPX Game OS page that embeds E3DS's player.

| Option | Lasts | Needs | Verdict |
|---|---|---|---|
| Save game only | one session | nothing | **Always on**: it carries progress from level to level within a session |
| The browser, through the page | as long as the browser keeps site data | the IPX page's message bridge (site code, not in this repository) and E3DS's iframe relay | **Recommended main path**: automatic, invisible |
| A progress code | forever, anywhere | the player writes it down | **Always on as the fallback**: works on E3DS's direct link, on another device, and with site data cleared |
| An account or server | forever | a backend, sign-in, privacy work | Not for this release |
| None (each session starts at Level 1) | | | Rejected: with 15 to 30 minute sessions, Level 3 would be out of reach for many players |

### 4.2 Progress data

```
FMIProgress {
  Levels: map level id -> { bCleared, Clears, BestPoints (-1 = none, 0..5), BestDifficulty (hustler | boss | kingpin | None), HoldBest }
  bAlbumSeen
}
```

The progress code carries `bCleared`, `BestPoints`, `BestDifficulty` and `bAlbumSeen` for the three levels. Hold bests
travel only through the page bridge, because the code is kept short.

### 4.3 The progress code (format v1)

- 8 characters from the Crockford base32 alphabet `0123456789ABCDEFGHJKMNPQRSTVWXYZ`, shown as `XXXX-XXXX`. That is 40 bits:
  a 24-bit payload followed by a 16-bit check.
- Payload bits, most significant first:

| Bits | Field | Values |
|---|---|---|
| 23–21 | version | 1 |
| 20–19 | reserved | 0 (a code with any other value is refused) |
| 18–16 | cleared mask | bit 16 block, 17 chinatown, 18 midtown |
| 15–7 | best points, 3 bits per level (block at bits 7–9) | 0..5, 7 = none (6 is refused) |
| 6–1 | best difficulty, 2 bits per level (block at bits 1–2) | 0 hustler, 1 boss, 2 kingpin, 3 none |
| 0 | album seen | 0 / 1 |

- Check: CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection, no final XOR) over the ASCII salt
  `MURDERINC-PROGRESS-1` followed by the 3 payload bytes, big-endian.
- A code is valid only when all of these hold: the check matches, the version is 1, the reserved bits are 0, each
  level's cleared bit agrees with its points ≠ 7 and its difficulty ≠ 3, cleared levels form a prefix (cleared[i]
  needs cleared[i-1]), and the album bit needs all three levels cleared.
- Checked exhaustively in the prototype (Appendix A): 12,007 valid states round-trip, and **no single-character change
  of any valid code is accepted**. All one-symbol errors are 5-bit bursts, which a 16-bit CRC always catches.
- Examples:

| State | Code |
|---|---|
| Block cleared, Gold on boss | `47YZ-MB30` |
| Block and Canal cleared (Gold/boss, Single/boss) | `4FMY-N7W6` |
| All cleared, album seen (Gold/boss, Single/boss, Platinum/kingpin) | `4Y4W-PZ1F` |
| Testing: Levels 1 to 3 open (Block and Canal cleared at Demo on hustler) | `4FG6-05EW` |
| Testing: all cleared at Demo on hustler, album not seen | `4W00-1D88` |

- The code guards nothing. It is a single-player convenience, so anyone can type a code that opens everything. That is
  accepted (it is also how the owner tests Level 3 on E3DS without replaying Levels 1 and 2).
- Growth: when maps are added ("we can add more later"), version 2 lengthens the code to 10 characters. Version 1 codes
  stay valid, and their levels map by id.

### 4.4 The page bridge (spec for the IPX Game OS page, in the style of PREFLIGHT.md section 4)

Game → page (a Pixel Streaming 2 response message to the player, through E3DS's iframe relay):

```json
{"mi": "progress", "v": 1, "code": "4FMY-N7W6", "hold": {"block": 12345, "chinatown": 0, "midtown": 0}}
```

The game sends it (a) once, 1 s after the data channel opens, so that a page with nothing stored gets a value, and
(b) after every change (2.4).

Page → game (sent once, when the frame reports the data channel open: `bidirectionalChannelBetweenUnrealAndIframeReady`
/ `stream.channelOpen`) carries the same JSON, read from `localStorage["murderinc.progress.v1"]`. It arrives in the game
as a UI interaction message.

Page rules:

- Store only a message with `mi === "progress"`, `v === 1`, a `code` matching
  `/^[0-9A-HJKMNP-TV-Z]{4}-?[0-9A-HJKMNP-TV-Z]{4}$/`, and `hold` values that are integers from 0 to 99,999,999.
- Overwrite what is stored with the game's latest message: the game has already merged it.
- Wrap every localStorage access in try/catch. A private window simply has no bridge.

Game rules:

- Accept only the `progress` message type, at most 256 bytes. The code is decoded with the same decoder as typed codes
  (an invalid one is ignored and logged once), and each `hold` value is clamped to 0..99,999,999.
- Merge, never replace (4.5).
- The message handler sits beside the existing command handlers in Cloud/MICloud.cpp, and it does not open the console
  allowlist.

The exact E3DS iframe command that forwards a page message to the game, and the event name under which E3DS passes the
game's responses up to the page, must be read from E3DS's live player code, as PREFLIGHT.md section 4 did for the
session events. That check comes before the page work. Until it is done, the code (4.3) is the only path that lasts
across sessions.

### 4.5 Merge rule

For each level: `bCleared = a || b`, `Clears = max`, best rating = the higher of (points, difficulty rank) compared
lexicographically, and `HoldBest = max`. Then `bAlbumSeen = a || b`. Merging is commutative and idempotent, and it never
lowers progress. The Block's HoldBest merges into `UMISaveGame.Best`.

### 4.6 Session time

- Today Max Session Time is 15 minutes. First-time play of the campaign takes about 19 minutes: front end 1, Block 5,
  travel 0.2, Canal 5, travel 0.2, Midtown 6.5, debriefs 1. Deaths add more.
- **Recommendation: set Max Session Time to 30 for the three-map release.** E3DS's inactivity logout (3 + 1 minutes)
  still ends idle sessions, so the extra cost falls only on sessions that are being played. The owner decides (open
  question 1).
- The game is told the limit through E3DS's launch arguments: `-MISessionMinutes=30`. Without it the game shows no
  warnings. It counts from the first viewer join (the clock MISession.h already keeps).
  - On a debrief with a next level, if the time left is less than the next level's `par` + 1 minute, the debrief shows
    `frontend.campaign.session.warn` under the code.
  - With 2 minutes left in play, `session.last` shows once in the HUD message line.
  - The pause menu always shows the progress code.
- `par` minutes per level in levels.json: Block 5.0, Canal Street 5.0, Midtown 6.5.

---

## 5. How the level runs: data flow

```
levels.json (campaign, levels.<id>.map / data / story / number / par)
      │
      ▼
UMIRunSetupSubsystem (GameInstance; survives travel)
  Setup (crew, guns, builds, level, mode, difficulty, time) + PendingTravel {to, enter} + Progress (FMIProgress)
      │ OpenLevel("/Game/Maps/L_Chinatown?level=chinatown?enter=intro")
      ▼
AMIGameMode::StartPlay: the level id comes from the map (levels.json map → id) or ?level= on a grey map
      ▼
UMIGameSubsystem::Boot(LevelId)
  Level = FMILevelData::ForLevel(id)   (block → the same object as FMILevelData::Get())
  Text  = FMIText(text.json) + overlay frontend.story.<id> (none on block for rules keys)
  times, rig, audio zones, tuning from the level
  ... the existing build steps unchanged ...
  enter=intro: ApplySetup(RunSetup) → StartRun(mode) → intro (location card + radio from the overlay)
      ▼
FMIGameRules (unchanged) ──► Complete ──► record progress, save, bridge, preload the next map ──► debrief (+ next)
```

---

## 6. Travel and loading without a long black screen

### 6.1 Rules

- Travel is game code only (`UGameplayStatics::OpenLevel`). The cloud console refuses `open`, and that stays.
- Every travel goes through **one function**, `UMIGameSubsystem::TravelTo(FName LevelId, EMIEnter Enter)`. Enter is
  `Intro` (start the chosen mode with the set-up) or `Title` (front end).
- It is triggered by: Home's primary button or Briefing's go when `Setup.Level` is not the loaded level, the debrief's
  Next, and Level select → a level → go.
- Before travel the game writes the save, sends the bridge message, and sets `PendingTravel` in the GameInstance
  subsystem.
- URL options: `?level=<id>` (needed only on grey maps, which serve several ids; on art maps the map decides) and
  `?enter=intro|title`. The existing `?autostart` (skip the intro) and `?mode=`/`?difficulty=` are unchanged.

### 6.2 Preload during the debrief

- On Story Complete, when a next level exists and was not already loaded, the game calls
  `LoadPackageAsync("/Game/Maps/L_<Next>")`. The package is held by a strong reference in the GameInstance subsystem
  (`PreloadedMap`). When the debrief appears 3.3 s later, the player usually spends 4 to 10 s more on the stats.
- OpenLevel then finds the world package and most of its dependencies already in memory, so the hitch is mostly world
  initialisation plus Boot.
- Guards:
  - No preload in Hold mode, parity boots or tests.
  - The preload is cancelled (reference released) on Run it back or Back to title.
  - If free physical memory is below 4 GB when Complete fires (`FPlatformMemory::GetStats().AvailablePhysical`;
    E3DS has 20 GB), there is no preload. Travel still works, only slower.
- To measure on the box: peak resident memory with the Block running and Canal preloaded must stay under 14 GB, and
  GPU memory must not grow during the preload (textures stay at their low mips until rendered).

### 6.3 The loading card is streamed

- The card (3.7) is an `SMILoadingCard` widget registered with the engine's MoviePlayer as the loading screen:
  `bAutoCompleteWhenLoadingCompletes = false`, `bMoviesAreSkippable = false`, `MinimumLoadingScreenDisplayTime = 1.0`.
  MoviePlayer ticks Slate on its own thread during LoadMap, so frames keep coming.
- Pixel Streaming 2's back-buffer video producer (MICloud.cpp already sets `CreateVideoProducerBackBuffer`) captures
  Slate's back buffer, so the stream should show the card, not a frozen frame.
- **This must be proven before anything else in section 6**. On the box, with `tools/box/cloud/rtcinput.py`, save a
  frame every 250 ms through a travel. Pass: no all-black frame, and no two consecutive saved frames identical for more
  than 1 s. If it fails, the card is drawn from the game thread between load steps, or section 6.6 is used.
- MICloud's session logic must treat a travel as live: viewers stay connected, the probe line notes `travel=1`, and the
  E3DS-side "no video" watchdog sees frames.

### 6.4 Shader and texture warm-up

- PSO hitches on first view are the main risk on SM5/Vulkan with 8 threads (SMOOTH.md's lane measures stalls today).
- The fix: a bundled PSO cache per map. Recording runs on the box with `-logPSO`, through a scripted fly-through of
  each map's title path and guide legs plus a Story run. The recorded `.upipelinecache` files are expanded into the
  cook's stable shader keys (`ShaderPipelineCache` tooling).
- At boot, `r.ShaderPipelineCache.Enabled=1` with batch mode `Background` in the front end and `Fast` while the loading
  card is up. The card waits for `FShaderPipelineCache::NumPrecompilesRemaining() == 0`, at most 6 s.
- Textures: `IStreamingManager::Get().StreamAllResources(2.0)` behind the card, so the intro does not open on blurry
  mips. The streaming pool question (READY.md R4) applies per map.

### 6.5 Timings to meet (E3DS-faithful box load l20, then on E3DS)

| Step | Target | Worst allowed |
|---|---|---|
| Next pressed → card on screen | ≤ 100 ms | 250 ms |
| Card → map loaded (preloaded) | ≤ 4 s | 7 s |
| Card → map loaded (no preload, cold) | ≤ 8 s | 12 s |
| Boot (level data, colliders, pools, nav) | ≤ 0.8 s | 1.5 s |
| PSO + streaming wait | ≤ 3 s | 6 s + 2 s caps |
| **Next → intro first frame** | **≤ 6 s** | **10 s (preloaded), 15 s (cold)** |
| Frames over 100 ms in the first 10 s of play after travel | 0 | 1 |

Boot cost to check: one UBoxComponent per collider (about 780) plus the nav build. The Block's Boot time today is the
baseline; measure it in the same run.

### 6.6 Fallback design B (only if 6.3 or 6.5 fails)

- One small persistent map, `L_Game`, holds the subsystem's world, the front-end stage and a black backdrop.
- Each level's art map (L_Block, L_Chinatown, L_Midtown, built exactly as now) is added as a
  `ULevelStreamingDynamic::LoadLevelInstance` at the origin and removed afterwards.
- The subsystem gains `Unboot()`, which tears down the geometry, pools, explosives, cases, truck and title camera, and
  `Boot(LevelId)` runs again. The rig, fog and post volume come from each art map, since only one is loaded at a time.
- Gains: the game thread never blocks (the card is just HUD), and the stream never stalls.
- Costs: a teardown path that must leave no stale actor, Lumen and distance-field scene rebuilds on every swap,
  L_Block becomes a sublevel in the package (and is still openable alone for the box tools), and more test work.
- Decide after the 6.3 test on the box.

### 6.7 Failure handling

When a travel fails (a missing map in the package, or a load error), the engine falls back to GameDefaultMap
(L_Block). The game sees `PendingTravel.To != loaded` on boot, shows the front end with
`frontend.campaign.travelFailed`, clears PendingTravel and logs `MITravel: failed to=<id>`. Progress is already saved
by then.

---

## 7. Data changes (files)

### 7.1 `Content/Data/levels.json`

```json
"default": "block",
"order": ["block", "chinatown", "midtown"],
"campaign": {
  "id": "masters",
  "order": ["block", "chinatown", "midtown"],
  "unlock": "previous",
  "text": "frontend.campaign",
  "album": { "ratingByPoints": [[15, 5], [13, 4], [10, 3], [7, 2], [4, 1], [0, 0]], "voice": "album.complete" },
  "notes": "Level i opens when level i-1's Story is cleared (any difficulty). Hold on a level opens with the level. docs/unreal/maps/progression.md"
},
"levels": {
  "block": {
    "...": "every existing field unchanged",
    "number": 1, "par": 5.0, "story": "frontend.story.block", "greyMap": "/Game/Maps/L_GreyBlock",
    "preview": {"camera": "titlePath", "thumbnail": {"asset": "/Game/UI/Levels/T_UI_Level_Block", "titleKey": 3, "status": "missing", "notes": "..."}}
  },
  "chinatown": { "...": "chinatown.md 15.2", "number": 2, "par": 5.0, "story": "frontend.story.chinatown", "greyMap": "/Game/Maps/L_GreyChinatown" },
  "midtown":   { "...": "midtown.md 16.2",  "number": 3, "par": 6.5, "story": "frontend.story.midtown",  "greyMap": "/Game/Maps/L_GreyMidtown" }
}
```

`place` of the new levels points into their overlays: `frontend.story.chinatown.location.byTime.night` and
`frontend.story.midtown.location.byTime.night`. MurderInc.Loadout.DataLoads keeps its Block literals. A per-level
successor checks the other two levels (9.1).

### 7.2 `Content/Data/frontend_text.json`: the overlays

Rules for `frontend.story.<id>`:

- Its key paths mirror text.json's `text.*` exactly: same names, same types, same array lengths
  (`objectives.mission` 4, `radio.reel` 3, `reels.list` 3).
- Radio entries are `{text, secs}`, as in text.json.
- A key that is not in the overlay falls back to text.json.
- Keys that are not in text.json are allowed only from this list: `briefing.plan`, `loading.*`, `teaser`, `guide.hints`.
- **The Block's overlay contains no text.json key path** (enforced by a test, 9.3).

```json
"story": {
  "block": {
    "briefing": { "plan": ["Three masters on this block: the avenue, the chop shop, the cage.", "Every reel you grab brings more of them.", "All three in hand, the IPX truck rolls from the lot."] },
    "loading": { "kicker": "Level 1 of 3", "title": "The Block", "line": "Where it started. Three masters on one block." },
    "teaser": "Three back. The session sheet says nine. Six are still out, and the Vultures are running them to Canal Street."
  },
  "chinatown": {
    "title": { "eyebrow": "IPX PRESENTS · CHINATOWN, MANHATTAN" },
    "location": { "place": "Chinatown, Manhattan · Canal St · 7:40 PM", "byTime": { "night": "Chinatown, Manhattan · Canal St · 7:40 PM" },
                  "tagline": "Three more masters. One market. Tight corners.", "taglineHoldout": "One street. Endless Vultures." },
    "modes": { "mission": { "note": "Take back three more masters and reach the IPX truck. About five minutes." },
               "holdout": { "name": "Hold Canal Street", "note": "Endless waves down Canal and out of every door. How long can you hold it?" } },
    "objectives": { "mission": ["Take back three more masters", "Two masters left", "Last master", "Get to the IPX truck"] },
    "reels": { "list": [ {"id": "reel4", "code": "4", "label": "Reel 4 — The Tables"},
                         {"id": "reel5", "code": "5", "label": "Reel 5 — The Market"},
                         {"id": "reel6", "code": "6", "label": "Reel 6 — The Dub Room"} ] },
    "radio": {
      "intro": { "text": "{name}, it's the Vault. Vultures moved three more masters to Canal — the tables, the market, the dub room. Bring them home.", "secs": 4.3 },
      "introHoldout": { "text": "{name}, it's the Vault. Vultures are coming out of every door on Canal. Hold the street.", "secs": 3.7 },
      "reel": [ { "text": "That's one. Canal heard it — more coming.", "secs": 2.9 },
                { "text": "Two. They're pouring out of the back rooms.", "secs": 2.9 },
                { "text": "All three. The IPX truck is idling at the east end of Canal. Cut through the arcade. Move.", "secs": 3.8 } ],
      "done": { "text": "Masters are in the vault. Canal's clean, {name}. They're taking what's left uptown.", "secs": 3.6 }
    },
    "cards": { "dead": { "stats": { "time": "Time on Canal" } },
               "debrief": { "kicker": "Chinatown, Manhattan · Debrief", "title": "Canal is yours" } },
    "boot": ["Lighting the signs", "Hosing down the market", "Stacking the tables", "Waiting out the rain"],
    "zones": { "canal": "CANAL ST", "alley": "LANTERN ALLEY", "market": "THE MARKET", "mott": "MOTT ST" },
    "briefing": { "plan": ["Three masters on Canal: a bootleg table out front, the market's cold room, the dub room off Mott.", "Close quarters. They come out of doorways, not just the street ends.", "The IPX truck waits at the east end of Canal."] },
    "loading": { "kicker": "Level 2 of 3", "title": "Canal Street", "line": "They're cutting copies in the back rooms. Pull the masters out." },
    "teaser": "Six home. The last three went uptown. Their buyer wants your album on the big screens over the square at midnight.",
    "guide": { "hints": ["Reel 4's on a table outside the market. South side of Canal.", "Back of the market. The cold room, by the west wall.", "Out the market's back door, down the alley to Mott. The dub room's shutter is up.", "The truck's at the east end of Canal. Cut through the arcade off the square."] }
  },
  "midtown": {
    "title": { "eyebrow": "IPX PRESENTS · MIDTOWN, MANHATTAN" },
    "location": { "place": "Midtown, Manhattan · Seventh Av · 11:58 PM", "byTime": { "night": "Midtown, Manhattan · Seventh Av · 11:58 PM" },
                  "tagline": "Last three masters. Up top, then down.", "taglineHoldout": "One square. Endless Vultures." },
    "modes": { "mission": { "note": "The last three masters, roof to street, then the IPX truck. About six minutes." },
               "holdout": { "name": "Hold the Square", "note": "Endless waves over the square. How long can you hold it?" } },
    "objectives": { "mission": ["Take back the last three masters", "Two masters left", "Last master", "Get to the IPX truck"] },
    "reels": { "list": [ {"id": "reel7", "code": "7", "label": "Reel 7 — The Tank"},
                         {"id": "reel8", "code": "8", "label": "Reel 8 — The Gantry"},
                         {"id": "reel9", "code": "9", "label": "Reel 9 — The Booth"} ] },
    "radio": {
      "intro": { "text": "{name}, it's the Vault. Last three masters are on these roofs and down in the square. Their buyer wants your album on the big screens at midnight. Not tonight.", "secs": 4.9 },
      "introHoldout": { "text": "{name}, it's the Vault. The square's full of Vultures. Hold it down as long as you can.", "secs": 3.7 },
      "reel": [ { "text": "One back. Every roof heard that. They're coming over the top.", "secs": 3.3 },
                { "text": "Two. That screen's dead. Last one's in the booth under the stand. Get down there.", "secs": 3.6 },
                { "text": "That's all three. The IPX truck is on Forty-Sixth, south end of the square. Move.", "secs": 3.6 } ],
      "done": { "text": "Every master's home. The city's yours, {name}.", "secs": 3.0 }
    },
    "cards": { "dead": { "stats": { "time": "Time in Midtown" } },
               "debrief": { "kicker": "Midtown, Manhattan · Debrief", "title": "The city is yours" } },
    "boot": ["Lighting up the square", "Filling the water tanks", "Rolling the screens", "Clearing the barricades"],
    "zones": { "high": "HALVORSEN ROOF", "tanks": "THE TANKS", "gantry": "THE GANTRY", "back": "BACK ROOFS", "square": "THE SQUARE", "w46": "W 46 ST" },
    "briefing": { "plan": ["Three masters: the tank house up top, the gantry behind the big screen, the booth under the stand.", "Work down the roofs. Stairs and the scaffold get you to the street.", "The IPX truck is on Forty-Sixth, south end of the square."] },
    "loading": { "kicker": "Level 3 of 3", "title": "Midtown", "line": "Midnight over the square. Last three masters." },
    "guide": { "hints": ["Steel stair on the east side of this roof. The tanks are one roof down.", "The gantry is behind the big screen, one roof down. Stair at the south edge.", "Scaffold stair at the south end of the gantry. The booth is under the stand, north end of the square.", "IPX truck is on 46th, south end of the square."] }
  }
}
```

Reused from text.json on every level (not in any overlay): `radio.contact`, `radio.lowHealth`, `radio.waveClear`,
`prompts.*` (including `refuse`, which names no place), `banners.*`, `extraction.*`, `ratings`, and the dead card's
kicker ("Rule down", with the crew template).

### 7.3 `Content/Data/frontend.json`

- `screens.home.actions`: add `continue` (`text: frontend.home.continue`, `to: intro`, `when: "progress beyond the
  first level and the furthest open level not cleared"`) and `progress` (`to: drawer:progress`).
- `screens`: add the `progress` drawer and the `code` sub-screen. Splitting `where` into `level` and `style` follows
  from `order` having three levels.
- `save.fields`: add `"progress": "FMIProgressSave: levels map id -> {cleared, clears, bestPoints, bestDifficulty,
  holdBest}, albumSeen"`.
- `save.validation`: add "a remembered level that is not open falls back to the furthest open level".

### 7.4 `Content/Data/voice.json`

- Add the trigger `album.complete` → `rule_chant`.
- Add the trigger `level.next` (Next pressed) → none. It is reserved, and characters without lines stay silent.

### 7.5 `Config/DefaultGame.ini`

- `BlockMaps`: add `/Game/Maps/L_Chinatown`, `L_GreyChinatown`, `L_Midtown` and `L_GreyMidtown`. Later the check moves
  to "any levels.json `map` or `greyMap`" (8, item 3).
- `[MICloud]`: `SessionMinutes=0` (default off; the launch argument wins).

### 7.6 `tools/box/cloud/package-cloud.sh`

- `MapsToCook` and `-map=`: add `/Game/Maps/L_Chinatown` and `/Game/Maps/L_Midtown`. The grey maps are not cooked.
- `DirectoriesToAlwaysCook`: add `/Game/UI`.
- The start map stays `/Game/Maps/L_Block`.
- A step to bundle the PSO caches (6.4).
- A size report per map. E3DS storage is 10 GB, so measure before planning how many versions to keep.

---

## 8. Engine changes (C++), with files

None of these change a Block run. Each Block-facing line says why.

| # | Change | Files | The Block |
|---|---|---|---|
| 1 | **Per-level data.** `FMILevelData::ForLevel(FName Id, FString& Err)` loads levels.json `data.level` and caches one object per id (`TMap<FName, TUniquePtr<FMILevelData>>`). `Get()` stays the Block's level.json and returns the same object as `ForLevel("block")`. `Load(FileName)` takes the file. `el` becomes optional (`bHasDeck`), and the optional sections are `tuning`, `nav.layers`/`links`, `guide`, `audio` (midtown.md 17) | World/MILevelData.h/.cpp | the same file and object; goldens call Get() |
| 2 | **levels.json, all of it**: parse `data`, `number`, `par`, `story`, `greyMap`, `campaign`. `Lv.Map` gets used. ValidateData adds: each campaign id is a level, map paths are unique, `story` roots exist, thumbnails are named | Core/Data/MILoadoutData.h/.cpp | an added field read, nothing else |
| 3 | **Boot gate and level id**: StartPlay boots in any map listed as a levels.json `map`/`greyMap` (BlockMaps kept as an override). The level id is the map's id; `?level=` only on grey maps. Parse `?enter=intro|title` | Flow/MIGameMode.cpp/.h | L_Block → block, as now |
| 4 | **Boot(LevelId)**: level-scoped data. Times from the chosen level (today's code reads the default level, MIGameSubsystem.cpp 180-212). Rig, audio zones and `tuning` (startPitch, rating times, Buzzard ceiling) from the level. Then ApplySetup on enter=intro | Flow/MIGameSubsystem.cpp/.h | block: no tuning, the same rig and audio |
| 5 | **Text overlay**: `FMIText::SetOverlay(TSharedPtr<FJsonObject>)`. `Get(Key)` looks in the overlay first, then text.json. `{name}` resolves to the crew call name (Rule → "Rule"). The crew `replaces` table applies to text.json lines only. The HUD location card reads through FMIText, not text.json directly (UI/MIHUD.cpp 344-348) | Flow/MIFlowRules.cpp/.h, UI/MIHUD.cpp | no overlay keys that the rules read: the same strings |
| 6 | **Progress**: the new `FMIProgress` holds records, Merge, Unlocked(id), FurthestOpen, AlbumPoints, `EncodeCode`/`DecodeCode` (4.3). Pure logic | **new** Flow/MIProgress.h/.cpp | not used by the rules |
| 7 | **Save**: `FMILevelRecordSave`, `FMIProgressSave` and `UMISaveGame::Progress` (a new UPROPERTY; old saves load with defaults, so Version stays 1). `Best` stays the Block's Hold best | Flow/MISettings.h/.cpp | same slot, same fields |
| 8 | **Campaign state across travel**: Progress, PendingTravel {To, Enter}, PreloadedMap, the session clock link | Flow/MIRunSetupSubsystem.h/.cpp | |
| 9 | **TravelTo, preload, record on Complete**: TravelTo(LevelId, Enter); preload on Complete (6.2); RecordStory/RecordHold (2.4); the menu patch layer adds `next`/`album`/`levels` (2.3) when `!bTestBoot`; MenuConfirm handles `next`, `album`, `levels`; travel-failed message (6.7) | Flow/MIGameSubsystem.cpp/.h | patch skipped for test and parity boots; the card build in FMIMenus unchanged |
| 10 | **Rating per level**: FMIGameRules::Init takes the rating time table from the level's `tuning` if present, else config (unchanged) | Flow/MIGameRules.cpp/.h | config table, as now |
| 11 | **Front-end rules**: Level and Style screens (the split), card states (locked, open, cleared, hold best), SetLevel refuses a locked level, Continue on Home, the progress drawer and code entry, save validation (furthest open) | Flow/MIFrontEndRules.h/.cpp | with one open level, Home reads as today |
| 12 | **Front-end UI**: three level cards with thumbnails and the lock look, Continue, the drawer, 8-box code entry (keys and pad) | UI/SMIFrontEnd.cpp/.h, UI/MIFrontEnd.cpp | |
| 13 | **Cards**: the album card (`EMIMenuScreen::Album`), the code line and teaser on the debrief, per-level labels via the overlay | UI/MIMenus.cpp/.h | Block debrief stats unchanged |
| 14 | **Loading card**: `SMILoadingCard` and MoviePlayer set-up (PreLoadMap / PostLoadMapWithWorld), with hold conditions (3.7) | **new** UI/SMILoadingCard.h/.cpp, MurderInc.cpp (module start-up), MurderInc.Build.cs (MoviePlayer) | not shown without a travel |
| 15 | **Page bridge and session warning**: a UI interaction handler for `progress`; a response sent on channel open and on change; `-MISessionMinutes=`; warnings (4.6); `travel=1` in the probe line | Cloud/MICloud.cpp/.h, Cloud/MISession.h | no message, no warning |
| 16 | **Audio per level**: zones and train from the level's `audio` block, else global audio.json | Audio/MIAudioData.cpp, Audio/MIAudioDirector.cpp | global, as now |
| 17 | **Voice**: the trigger `album.complete` | Audio/MIVoiceTriggers.cpp | never fired |
| 18 | **Enemies and nav for Midtown** (no deck, nav layers and links, spawn reach, Buzzard ceiling): midtown.md 17.2 to 17.7 | World/MIBoxWorld.*, Enemies/MIEnemies.cpp, Enemies/MIEnemyTune.cpp, Flow/MIGameRules.cpp | Golden.World diff 0 |
| 19 | **Unlock-all for desktop tests**: `-MIUnlockAll`, refused when streamed (MICloud IsStreamed) | Flow/MIRunSetupSubsystem.cpp | |

Pipeline (not C++): build_block.py becomes `build_level.py --level <id>` (midtown.md 17.10, chinatown.md 16), and
`--level block` must reproduce L_Block exactly. mi_greyblock_map.py takes `--level`. `Content/Python/mi_level_thumbs.py`
is new (3.3). The PSO recording uses `tools/box/pso-record.sh` (new).

---

## 9. Tests

### 9.1 Per-level data (headless, no map)

- `MurderInc.Levels.<Id>.Loads`, for chinatown and midtown:
  - every required section is present;
  - the counts equal levels.json `provides` (Canal: 3 objectives, 35 ground and 18 air spawns, 18 explosives, 14 title
    keys; Midtown: 3, 30, 18, 17, 14);
  - the collider count is at most 800 (Canal) or 820 (Midtown).
- `MurderInc.Levels.<Id>.Nav`: the grid built by FMIBoxWorld from the level's colliders equals the `nav` the generator
  wrote, cell for cell. This is an independent check of the generator, as Golden.World is for the Block. For Midtown,
  per layer.
- `MurderInc.Levels.<Id>.Reach`: from playerStart, a path to each objective's approach point and to the extraction.
  Every spawn and cover point is on a walkable cell.
- `MurderInc.Levels.Overlay`:
  - every `frontend.story.<id>` key is a text.json key path of the same type and array length, or is on the allowed
    list (7.2);
  - every radio entry has `secs` between 2.4 and 6.0;
  - every `{name}` line resolves for all four crew members.

### 9.2 Recorded goldens for the new levels

The new levels have no web reference, so their goldens are recorded from the engine:

- `-MIGoldenRecord=<id>` (desktop only) runs the deterministic headless Story run: seed 1994, a scripted bot that walks
  `guide` legs, invulnerable, boss. It writes `Content/Data/golden/levels/<id>/story_complete.json` (the flow event
  stream, the same fields Golden.Directors compares) and `holdout_waves.json` (3 waves, scripted kills).
- `MurderInc.Golden.Level.<Id>.Directors` replays it and requires 0 mismatches.
- A recorded golden is re-recorded only on purpose, and the commit says why. A drift after an unrelated change is a
  bug.
- The Block's goldens (Golden.World, .Enemies, .EnemyLogic, .Blast, .FlowRules, .Directors, PlayerSim,
  Loadout.DataLoads) are unchanged and must pass on every commit of this work.

### 9.3 Campaign and progress (pure logic)

- `MurderInc.Campaign.Code`:
  - every one of the 12,007 valid states round-trips;
  - every single-character change of 1,000 random valid codes is refused;
  - the examples in 4.3 decode to their states;
  - O, I, L, lower case, hyphens and spaces are accepted; U and an over-length code are refused.
- `MurderInc.Campaign.Merge`: commutative, idempotent, never lowers a field. The Block's HoldBest ↔ `Best`.
- `MurderInc.Campaign.Unlocks`: a fresh save opens only the Block. Clearing on hustler opens the next level. Locked
  `Setup.Level` falls back to the furthest open level. Hold opens with its level. The album needs three clears.
- `MurderInc.Campaign.BlockUnchanged`:
  - the Block's overlay has no text.json key;
  - a Block Story run under the Directors' harness gives byte-identical events with the campaign code compiled in;
  - the debrief patch adds nothing in test or parity boots.
- `MurderInc.Campaign.Debrief`: Block → items `next, again, changesetup, totitle` with `next` focused. Chinatown → the
  same. Midtown → `album, ...`. Hold dead card → no `next`.
- `MurderInc.Campaign.Travel` (an injected traveller; no real load): Next on the Block requests
  `/Game/Maps/L_Chinatown?level=chinatown?enter=intro`. Home Continue requests the furthest open level. A locked level
  never travels. A failed travel shows `travelFailed`.

### 9.4 Run tests per level (UWorld::CreateWorld + Boot(LevelId))

- `Run.<Id>.StoryComplete`: the bot completes. The overlay strings appear (intro radio, objective lines, debrief
  kicker), and no Block-only string does ("Hollis", "the block is yours", "south end of the lot").
- `Run.<Id>.StoryDeath`.
- `Run.<Id>.Holdout`: both spawn kinds; the best is written to that level only.
- `Frontend.<Id>.WalkWorld`.

### 9.5 Box and E3DS checks (the release bar)

- Travel stream test (6.3); timings (6.5) under l20 against the Block's Boot in the same run.
- An end-to-end play, fresh save: Home → Block Story → Next → Canal Story → Next → Midtown Story → album → Level select
  → Hold the Square. Every guidance leg works, deaths bleed and fall, guns switch, attachments show. Then a fresh
  session with the code `4FMY-N7W6` → Continue · Midtown.
- On E3DS: the same play through the E3DS page, with per-frame numbers per SMOOTH.md (frames over 25 and 100 ms per
  minute, worst frame, 1 % low) on each map and across both travels.

---

## 10. Build order (after v6 ships)

1. **Logic and data, no GPU**: items 1, 2, 5, 6, 7, 10 and 19, plus the overlays and levels.json entries, with tests
   9.1 (using the generator's first level files), 9.3 and 9.4. Gate: every Block golden unchanged.
2. **Travel proof on the box** (6.3) with two grey maps (L_GreyBlock → L_GreyChinatown), then items 3, 4, 8, 9 and 14
   with the timings of 6.5. If that fails, switch to 6.6 here, before any UI work.
3. **Front end**: items 11, 12 and 13, then screenshots at 1920 x 1080 and 1280 x 720 for every card state.
4. **Persistence**: item 15. Read E3DS's player code for the relay names first, then hand the bridge spec (4.4) to the
   site, then test with a stub page on the box.
5. **Recorded goldens** (9.2) once each level's data is final.
6. **Package, PSO caches, E3DS** (9.5).

---

## 11. Open questions for the owner

1. **Session length**: raise E3DS Max Session Time from 15 to 30 minutes for the three-map release? (Recommended.
   Idle sessions still end after 3 + 1 minutes.)
2. **Locks**: Levels 2 and 3 locked until the one before is cleared (recommended, "progress to 3 levels"), or all three
   open from the start?
3. **The story**: nine masters, one album, one day and night (4:15 PM, 7:40 PM, 11:58 PM), an unnamed buyer who means
   to premiere the album at midnight. Accepted, or a named villain?
4. **The page**: will the IPX Game OS page store the progress code (section 4.4), or should the game rely on the code
   alone?
5. **Per-level waves**: keep the global difficulty tables on all three maps (recommended for this release), or let
   Midtown add Buzzards per wave?

---

## 12. What the two level designs need to match this file

- **chinatown.md 15.3**: move `frontend.levels.chinatown.story.*` to `frontend.story.chinatown.*` with text.json's key
  paths:
  - `cards.debriefKicker` → `cards.debrief.kicker`, `debriefTitle` → `cards.debrief.title`,
    `deadTime` → `cards.dead.stats.time`
  - `holdoutName` → `modes.holdout.name`, `taglineHoldout` → `location.taglineHoldout`, `tagline` → `location.tagline`
  - `objectives` → `objectives.mission`, `hints` → `guide.hints`
  - radio entries become `{text, secs}`
  - `introRule` is dropped (`{name}` resolves to "Rule")
  - `place.night` → `location.byTime.night`, and levels.json `place.night` points there.
  The reel codes 4 to 6 stay.
- **midtown.md 6.2 and 16.4**: reels become **7 to 9** (`reel7`/`7`/"Reel 7 — The Tank", `reel8`/`8`/"Reel 8 — The
  Gantry", `reel9`/`9`/"Reel 9 — The Booth"), in level_midtown.json `objectives[]` and in the overlay. Radio lines take
  `{name}` and `{text, secs}`. `story.midtown.location.place` stays, and `byTime.night` is added. The Hold name and
  tagline move to `modes.holdout.name` and `location.taglineHoldout`. The objective line reads "Take back the last three
  masters".
- Both: levels.json entries gain `number`, `par`, `story` and `greyMap` (7.1).

---

## Appendix A. Progress code reference (Python, the test oracle for MIProgress)

```python
ALPH = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
SALT = b"MURDERINC-PROGRESS-1"

def crc16(data, crc=0xFFFF):                       # CRC-16/CCITT-FALSE
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return crc

def encode(cleared, points, diff, album):          # per level: bool, 0..5 or None, 0..2 or None
    p = 1 << 21                                    # version 1; bits 20-19 reserved 0
    for i in range(3):
        p |= (1 if cleared[i] else 0) << (16 + i)
        p |= (7 if points[i] is None else points[i]) << (7 + 3 * i)
        p |= (3 if diff[i] is None else diff[i]) << (1 + 2 * i)
    p |= 1 if album else 0
    v = (p << 16) | crc16(SALT + p.to_bytes(3, "big"))
    s = "".join(ALPH[(v >> (35 - 5 * k)) & 31] for k in range(8))
    return s[:4] + "-" + s[4:]

def decode(s):
    s = s.upper().replace("-", "").replace(" ", "").replace("O", "0").replace("I", "1").replace("L", "1")
    if len(s) != 8 or any(ch not in ALPH for ch in s):
        return None
    v = 0
    for ch in s:
        v = (v << 5) | ALPH.index(ch)
    p, c = v >> 16, v & 0xFFFF
    if crc16(SALT + p.to_bytes(3, "big")) != c or (p >> 21) != 1 or (p >> 19) & 3:
        return None
    cleared = [bool(p >> (16 + i) & 1) for i in range(3)]
    pts = [p >> (7 + 3 * i) & 7 for i in range(3)]
    dif = [p >> (1 + 2 * i) & 3 for i in range(3)]
    if 6 in pts:
        return None
    for i in range(3):
        if cleared[i] != (pts[i] != 7) or cleared[i] != (dif[i] != 3):
            return None
        if cleared[i] and i > 0 and not cleared[i - 1]:
            return None
    if (p & 1) and not all(cleared):
        return None
    return cleared, pts, dif, bool(p & 1)
```
