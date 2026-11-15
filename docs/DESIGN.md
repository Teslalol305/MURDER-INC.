# MURDER INC. — game design

An IPX production starring Ja Rule. A browser first-person street shooter set on one block of Queens at 2 AM.
Everything (streets, cars, people, weapons, every sound and the beat) is generated in code at load. No asset files.

This is an original game. Its mechanics and tuning follow the structure mapped in the reference notes
(`$NOTES/00-overview.md` … `07-gaps-resolved.md`, see CONTRACT.md for the path), but the setting, level layout,
art, names, copy, sound and music are all new. Never copy the reference's names, text, layout or look.

Units: metres, seconds, radians. +Y up. North is −Z, east is +X.

---------------------------------------------------------------------------------------------------

## 1. Fiction

- **Where / when**: Hollis, Queens. Jamaica Ave under the elevated train ("the El"). A hot summer night, 02:14 AM.
  The street was hosed down by an open hydrant: wet asphalt, neon in the puddles, steam from the manholes.
- **Who**: the player is **Ja Rule** ("Rule"). First person, never seen from outside. He does not speak.
- **What**: a bootleg crew, **the Vultures**, jacked three **master reels** from the studio and stashed them on the block
  before moving them. Rule takes them back, one at a time, and gets them to the **IPX truck** (an armoured vault truck)
  idling at the far end of the lot.
- **Voice on the line**: one speaker only, label **`IPX VAULT`** (the IPX dispatcher in Rule's earpiece). Dry, calm, brief.
- **Enemies**: the Vultures. Two types:
  - **Goon** — a masked gunman on foot (hoodie or puffer jacket in crew colours: oxblood red on black). Faces are always
    covered (ski mask / bandana). Fires SMG bursts, rushes with a pipe at close range. Weak point: head.
  - **Buzzard** — the crew's armed quadcopter drone. Red eye light, slung gun, fires telegraphed tracer bolts you can dodge.
- No real people other than the player character, no real gangs, no real brands except IPX. All shop names are invented.
  No real lyrics, no real song titles. No gore: hits throw a small dust/cloth puff, bodies fall and fade.

Tone: confident, dry, New York. Short sentences. No slurs, no profanity stronger than "damn".

---------------------------------------------------------------------------------------------------

## 2. Names and copy (single source: `src/config/text.js`)

| Thing | Name |
|---|---|
| Game title / wordmark | `MURDER INC.` |
| Presenter line | `IPX PRESENTS` |
| Star line | `STARRING JA RULE` |
| Location card | `Hollis, Queens · Jamaica Ave · 02:14 AM` / `Three reels. One block. No backup.` |
| Mode: mission | `Story` — "Take back three master reels and reach the IPX truck. About five minutes." |
| Mode: holdout | `Hold the Block` — "Endless waves that keep growing. Resupply between waves. How long can you hold it down?" |
| Difficulty | `Hustler` (standard) · `Boss` (default) · `Kingpin` |
| Weapon 1 | `CHOPPER` — compact automatic carbine, 30 rounds |
| Weapon 2 | `NINE` — 9 mm pistol, 15 rounds, never runs dry |
| Melee | `Pistol whip` / rifle butt (quick strike) |
| Objective item | `Master reel` — reels `1`, `2`, `3`: "Reel 1 — The Avenue", "Reel 2 — Chop Shop", "Reel 3 — The Cage" |
| Extraction | `IPX truck` (marker short code `IPX`) |
| Enemy 1 / 2 | `Goon` / `Buzzard` (kill feed: "Goon down", "Buzzard down", tag "Headshot") |
| Explosives | `Propane tank`, `Welding rack` |

Title screen: eyebrow `IPX PRESENTS · HOLLIS, QUEENS · 02:14 AM`; wordmark `MURDER INC.`; star line `STARRING JA RULE`;
premise "The Vultures jacked three master reels. Take the block back. Get them to the truck.";
note "Every street, sound and beat is generated in your browser. Nothing is downloaded.";
buttons `Hit the block` (start), `Settings`, `Controls`.

Objective lines: "Take back the three master reels" → "Two reels left" → "Last reel" → "Get to the IPX truck".
Holdout: "Vultures inbound" → "Hold the block" → "Catch your breath". Tally: "Stand by" → "Wave N · 12,345".

Interaction prompt: "Hold E — Grab reel 1" (glyph changes per device). Refusal at the truck before all reels:
"Reels still out there — the truck won't roll without all three".

Banners: "Contact — NORTH-EAST" (8-way compass), "Wave N — EAST". Countdown: "Wave N in 3".

Radio (`IPX VAULT`):

| Trigger | Line | Hold s |
|---|---|---|
| Intro (first start only) | "Rule, it's the Vault. Vultures stashed your three masters on this block — the avenue, the chop shop, the cage. Bring them home." | 4.4 |
| First time an enemy engages | "They made you. Goons on foot, Buzzards in the air. Handle it." | 3.2 |
| Reel 1 of 3 secured | "One reel back in your hands. They felt that — more coming." | 3.6 |
| Reel 2 of 3 | "Two reels. They're throwing the whole crew at you now." | 3.6 |
| Reel 3 of 3 | "That's all three. The IPX truck is idling at the south end of the lot. Move." | 4.5 |
| Health first drops under 30 | "You're hit bad. Get behind something solid and breathe." | 3.0 |
| Truck reached | "Masters are in the vault. The block is yours, Rule." | 2.4 |
| Holdout wave N cleared | "Wave N down. Resupply at your feet — 9 seconds." | 3.4 |

Cards: pause — kicker "Hold up", title "Paused", buttons Resume / Settings / Controls / Restart run.
Death — kicker "Rule down", title "Lights out"; stats "Time on the block", "Reels recovered n/3"; holdout stats
"Waves cleared", "Vultures dropped", "Score", "Best"; button "Run it back".
Debrief — kicker "Hollis, Queens · Debrief", title "The block is yours"; "Certification" rating, Time, Accuracy,
Vultures dropped, Retries; button "Run it back".
Rating ladder (0–5 points): `Demo`, `Mixtape`, `Single`, `Gold`, `Platinum`, `Diamond`.

Boot lines (in order): "Waking up the block" (static first line), "Warming up the renderer", "Mixing brick, chrome and neon",
"Parking cars on the avenue", "Raising the El", "Lighting the block", "Loading tracers and smoke", "Racking the Chopper",
"Waking the Vultures", "Waiting on the 2 AM train", "Ready". Fatal: "Murder Inc. could not start: <error>".

---------------------------------------------------------------------------------------------------

## 3. Core loop and modes (same structure as the reference notes, new skin)

1. Start at the west end of the avenue, at the foot of the El stairs. A small Vulture patrol is on the block, unaware.
2. Find a master reel (compass pip + world marker + a boombox leaking a muffled loop), hold Interact 2.4 s to grab it.
3. Each reel immediately queues a reinforcement wave that arrives alerted. Fight from dense waist-high cover (cars, barriers,
   trash, crates) and hard cover (trucks, walls, El columns); use propane tanks and welding racks.
4. Health regenerates after a few seconds out of fire. Enemy accuracy tightens the longer they hold line of sight on you.
5. After the third reel, run to the IPX truck while a finite pursuit keeps spawning. Touch the extraction zone to win.
6. Death or completion shows a card; retry restarts the whole run. No checkpoints.

Modes: **Story** (mission) and **Hold the Block** (holdout: endless growing waves, score, local best, resupply between waves).
State machine: `title → intro → playing ⇄ paused`, `playing → dead`, `playing → complete`.
All flow timings, the reinforcement pump, the spawn scoring, pursuit, the holdout formulas, rating thresholds and the
music-intensity driver follow `$NOTES/04-game-flow.md` unless this document says otherwise.

### 3.1 Tuning deltas from the reference notes

Player and both weapons use the reference numbers unchanged (01, 02), with these additions:

- **Melee works** (the reference bound it but left it unimplemented): 0.55 s strike, hits at 0.16 s, reach 2.3 m in a 50° cone,
  60 damage, 0.75 s between strikes, cancels reload, blocked while switching. Kills by melee count as kills, not shots.
- No sea. Bounds are sealed with player-only walls; falling out of the world is impossible. Drop the water rescue rule.
- Weapon names: slot 1 "CHOPPER" (the auto carbine row), slot 2 "NINE" (the pistol row).

Enemies: the **Buzzard** takes the reference flyer's numbers; the **Goon** takes the reference walker's behaviour with human
numbers, and Goons are the majority type:

| | Hustler | Boss (default) | Kingpin |
|---|---|---|---|
| Buzzard HP / bolt dmg / telegraph / cooldown | 45 / 7 / 0.55 / 1.9–3.3 | 55 / 10 / 0.46 / 1.4–2.5 | 60 / 13 / 0.38 / 1.0–1.9 |
| Buzzard spread far → near (rad) | 0.065 → 0.018 | 0.052 → 0.016 | 0.042 → 0.014 |
| Goon HP | 90 | 110 | 130 |
| Goon shot dmg / burst length / cooldown | 4 / 4 / 1.8–3.0 | 6 / 5 / 1.4–2.4 | 8 / 6 / 1.0–1.9 |
| Goon spread far → near (rad) | 0.12 → 0.045 | 0.095 → 0.038 | 0.08 → 0.032 |
| Goon rush (melee) dmg / run speed | 15 / 4.5 | 22 / 5.0 | 30 / 5.4 |
| Attack tokens (normal / crowd), gap | 2 / 3, 1.25 s | 3 / 4, 0.85 s | 4 / 5, 0.6 s |
| Exposure gain per s | 0.10 | 0.14 | 0.18 |
| Player regen delay / rate | 4 s / 25 per s | 5.5 s / 16 per s | 7 s / 10 per s |
| Starting patrol (Buzzard + Goon) | 1 + 3 | 2 + 4 | 2 + 5 |
| Waves after reel 1 / 2 / 3 (Buzzard + Goon) | 2+3 / 2+4 / 3+5 | 2+5 / 3+6 / 4+7 | 3+6 / 4+7 / 5+8 |
| Alive cap | 9 | 11 | 13 |
| Pursuit interval / budget | 7 s / 5 | 5.5 s / 8 | 4.5 s / 12 |

- Head weak point × 2.2 (Goon only). Goon pool cap 12, Buzzard pool cap 8.
- Pursuit and holdout mixes: 35 % Buzzard / 65 % Goon. Holdout wave n: total `min(5 + 2n, 30)`, Buzzard share
  `max(0.25, 0.45 − 0.02n)`; all other holdout formulas as in the notes.
- Holdout score: Buzzard 100, Goon 150, × (1 + 0.1 (wave − 1)); wave clear + 500 × wave. Resupply: +90 Chopper reserve
  (cap 240), +35 HP, explosives restored after even waves.
- Goons may use cover: they prefer fire positions next to a `level.coverPoints` entry that still has line of sight, and
  crouch between bursts. This is an enhancement over the reference walker; keep the reference behaviour as the fallback.
- A dead Goon drops where he stands (short procedural collapse), stays as a non-colliding body (max 6 kept, oldest fades).
  A dead Buzzard spins down and bursts on impact (r 3, 30 dmg, 15 max to the player).

Explosives (same numbers as the reference's two kinds): **propane tank** (HP 50, fuse 1.6 s with a jet of flame, radius 6.5,
170 / 85) and **welding rack** (HP 70, fuse 1.1 s, radius 7.5, 210 / 105). Chains as in the notes.

---------------------------------------------------------------------------------------------------

## 4. The block (level blueprint)

Play bounds: x −46 … 46, z −34 … 34 (92 × 68 m), flat ground at y 0 (kerbs 0.15 m). The level agent owns the exact
coordinates and may adjust them; the roles, proportions and loop structure below are required.

```
 z=-34 ┌──────────────┬───────────────────────────────┬─────┬───────────┬────────────────────────┐
       │ tenement N1  │   V&R AUTO BODY (chop shop)   │alley│ deli N2   │   THE CAGE             │
       │ (solid)      │   the only interior           │     │ (solid)   │   basketball court     │
       │              │   Reel 2, mezzanine office    │     │           │   Reel 3               │
 z=-11 ├──────────────┴──[roll door]────[door]────────┴─────┴───────────┤   (chain-link, 2 gates)│
       │  north sidewalk                                                 ├────────────────────────┤
 z=-7  │═════════════════════════════════════════════════════════════════════════════════════════│
       │  START →   JAMAICA AVE under the El  ·  parked cars, cabs, box truck  ·  Reel 1    [roadblock]
 z= 7  │═════════════════════════════════════════════════════════════════════════════════════════│
       │  south sidewalk         [scaffold shed = vantage, stairs]               ├────────────────┤
 z= 11 ├──────────────┬──────────┬──────────────┬────────────────────────┬──────┤  PARKING LOT    │
       │ station      │ pawn +   │ vacant lot   │ S3: chicken, liquor,   │      │  cars, booth,   │
       │ house S1     │ records  │ (cut-through)│ nails (solid)          │      │  IPX billboard  │
       │ (solid)      │ S2       │ mural wall   ├────────────────────────┘      │                 │
       │              │ (solid)  │              │   rear service lane →→→→→→→→→→│   IPX TRUCK (EX)│
 z= 34 └──────────────┴──────────┴──────────────┴───────────────────────────────┴─────────────────┘
      x=-46        -30        -16            -4                               22                46
```

- **Jamaica Ave** runs east–west the full length: roadway z −7…7 (two travel lanes + two parking lanes), sidewalks to z ±11.
  **The El** stands over it: riveted steel columns in two rows (z ≈ ±5) every 10 m, cross girders, a track deck with its
  underside at about 6.5 m, ties and rails on top, lamps hung underneath. A train crosses every 40–70 s
  (rumble, window light strobing through the ties, grit falling). The El is the block's signature: get it right.
- **Start** (zone `west`, x −46…−30): foot of the El station stairs on the south sidewalk, near (−40, 0, 8), facing east.
  Rule's black SUV at the kerb. No enemy spawns in this zone. West end sealed by the station stairs + a road-work closure.
- **The avenue** (zone `avenue`, x −30…22): the "maze". Parked sedans, yellow cabs, an SUV, a panel van and a box truck in
  the two parking lanes and double-parked, plus El columns, jersey barriers, a food cart, trash, mailboxes, a bus shelter.
  Three or four parallel east–west lanes with gaps every few car lengths. **Reel 1** sits mid-avenue near (−4, 0, 1),
  ringed by low cover, beside an abandoned Vulture van with its doors open.
  **Vantage**: a construction sidewalk shed (scaffold with a plywood deck at about 2.8 m, sandbags and a parapet on top) on the
  south sidewalk in front of S3, reached by a scaffold stair at its west end.
- **The chop shop** (zone `shop`): "V&R AUTO BODY", a one-storey cinder-block garage on the north side, about x −24…6,
  z −31…−12, eave 6 m. A 6 m roll-up door in the south wall, a second smaller open bay, an east side door into the alley,
  skylights. Inside: two car lifts (one car raised), a stripped car on stands, tool chests, tyre stacks, oil drums, a
  workbench, a welding rack, shelf racks; a **mezzanine office** in the north-west corner (floor about 2.8 m, stairs, glass
  front). 4 real work lights. **Reel 2** on the shop floor near (−9, 0, −21). This is the only interior
  (`level.interiorBoxes[0]`).
- **The alley** (x 6…11, z −34…−11): dumpsters, fire escape, steam, a chain-link gate sealing the north end. Links the
  north sidewalk and the shop's side door.
- **Vacant lot** (x −16…−4, z 11…30): fenced cut-through with an open gate, a burned-out car, tyres, a mattress, shopping
  carts; a big **mural** on the pawn shop's side wall (IPX wordmark + "RULE"). Leads south to the **rear service lane**
  (z 26…31, x −16…22) behind S3: loading dock, dumpsters, garage doors. The lane opens east into the parking lot.
  These give a full flanking loop: avenue ↔ vacant lot ↔ rear lane ↔ lot ↔ avenue.
- **The east side** (zone `lot`, x 22…46): open ground, the "open apron".
  North of the avenue: **The Cage**, a chain-link basketball court (4 m fence, two gates, hoops, bleachers, two flood lights).
  **Reel 3** at centre court near (33, 0, −22).
  South of the avenue: a **parking lot** with rows of parked cars, an attendant booth, light poles and an **IPX billboard**
  on a steel frame. The **IPX truck** waits in the south-east corner near (40, 0, 27): **extraction**, radius 2.5.
  The avenue's east end is sealed by a roadblock (barriers, a jack-knifed box truck) under the El.
- Perimeter: buildings, fences with scrim, roll gates and barricades, each backed by a player-only wall so nothing can be
  hopped. Buildings are 2–5 storeys of brick with fire escapes, lit and dark windows, rooftop water towers, awnings,
  roll-down gates, neon and box signs. Storefront names are invented: "HOLLIS DELI & GROCERY", "KINGS OF QUEENS BARBER",
  "PAWN & GOLD", "TAPES · RECORDS · CDs", "GOLDEN BIRD CHICKEN", "WINES & LIQUORS", "LUCKY NAILS", "24 HR LAUNDROMAT",
  "CHECKS CASHED", "99¢ PIZZA".
- Cover philosophy: dense waist-to-chest cover in every lane (a crouched player at eye 1.05 m is hidden, a standing one
  can shoot over): car bonnets 1.0, sedan roofs 1.45, jersey barriers 0.81, trash-bag piles 0.7, milk-crate stacks 1.0,
  traffic barrels 1.0, newspaper boxes 1.1, mailboxes 1.25, dumpsters 1.35. Vans, trucks, El columns, walls and the food
  cart are hard cover. Each objective sits in a small arena ringed by 4–8 low cover props at 2–5 m.
- About 18–22 explosives placed as part of the cover layout: propane tanks at the food cart, the scaffold and the lot booth;
  welding racks in and outside the shop.
- Spawn points: about 28 ground + 16 air, tagged by zone, hidden behind corners, in doorways, down the alley, in the rear
  lane, behind lot cars; air points over rooftops, beside the El deck and over the court and lot.
- 50+ hand-placed cover points for AI.

Branding in the world: the IPX truck livery, the IPX billboard, the mural, an IPX ad in the bus shelter, IPX tracker tags on
the reel cases. Use the wordmark "IPX" and the address "IPX.EXCHANGE" only. Do not invent a slogan for IPX.

---------------------------------------------------------------------------------------------------

## 5. Look

- **Night, sodium and neon.** Deep blue-black sky with city glow on the horizon; warm sodium street light from above; cool
  moonlit ambient; neon pink, red, cyan and green from the shop fronts; taxi yellow. The avenue under the El is striped with
  light and shadow. Wet asphalt mirrors the signs. Steam rises from manholes. The far skyline is a row of lit silhouettes.
- One steep, warm shadow-casting directional light stands in for "the street lights", plus cool hemisphere ambient, a small
  budget of real point lights at the key lamps (shop work lights, court floods, a few street lamps), additive light pools and
  light cones for the rest, emissive windows and neon that bloom.
- Stylised low-poly realism: clean silhouettes, canvas-painted textures with real-scale detail (brick courses, roll-gate
  ribs, tyre treads, stencilled signs, posters, graffiti). No photo textures, no external files.
- The Goons read at a glance: dark silhouettes with oxblood accents and a pale mask; the Buzzard carries a red eye light.
  Tracers: the player's are warm white-gold, the enemy's are red.

## 6. Interface

- DOM + CSS over the canvas. One deliberate dark look.
- The NYC vernacular is **transit signage**: black enamel plates, white grotesque type, a thin white rule above the text,
  coloured route bullets. The three reels are route bullets `1` `2` `3`; the truck is a bullet `IPX`. The compass is a line strip.
- Accent: taxi / gold-record yellow. Danger: signal red. The palette lives in a brand token block
  (`src/config/brand.js` + CSS custom properties) so the real IPX colours, fonts and logo can be dropped in later.
- The IPX wordmark appears on the boot screen, the title, the pause card, a small HUD corner tag and the debrief.
  Until the real logo is supplied it is typeset: "IPX" in a heavy italic grotesque inside a thin lozenge.
- Type: a tall condensed display face for the wordmark and card titles, a grotesque for UI, tabular figures for numbers.
  Google Fonts only, each with a real fallback stack. The game must look right with fallbacks (fonts may be blocked).

## 7. Sound

- All procedural WebAudio, rendered to buffers at load. No oscillators running per event at runtime if avoidable.
- Weapons with punch and tails (open street vs. inside the shop), reload foley, brass on asphalt, footsteps per surface,
  bullet impacts per surface, car-body hits, glass, ricochets, near-miss whizz, hit confirm (higher on headshots),
  explosions, the reel boombox loop (muffled, 3D), reel grab sting, Buzzard rotor loop / charge-up / shot / death,
  Goon footsteps / burst / rush telegraph / grunt, alert stabs, UI clicks.
- The block: distant traffic wash, a far siren now and then, the El train passing overhead, steam hiss, neon buzz near signs,
  a dog barking far off, wind in the El structure.
- **Music**: an original East-Coast boom-bap beat generated in code, about 92 BPM, minor key: dusty kick and snare, hats,
  sub bass, a dark piano / Rhodes figure, string stabs, a bell hook. Phase-locked stems mixed by an intensity value
  (0.15 calm → 0.6 alert → 1.0 wave or escape), with stings for a reel grab, all reels, death and mission complete.
  It must be an original composition: no real song, no samples.
