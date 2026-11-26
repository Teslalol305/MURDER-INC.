# tools/levels: the layout tool, the level data and its checks (MAPS.md lane D)

Level 2 (Canal Street) and Level 3 (Midtown) as data, before any engine or art work. Python 3 with numpy and Pillow
(both in this container's system Python); no Unreal, no box, no Blender.

```
python3 tools/levels/build_level.py   # layouts/<id>.py -> tools/levels/data/level_<id>.json
python3 tools/levels/check_level.py   # the checks below -> tools/levels/reports/check_<id>.json (exit 1 on a FAIL)
python3 tools/levels/plot_level.py    # top-down plans -> art/previews/maps/plan_<id>.jpg
```

Each takes `--level chinatown|midtown|all` (default all). `build_level.py --el-fallback` adds the degenerate deck of
MAPS.md E2's fallback (see `el` below). The build is deterministic: the same table gives the same bytes.

| File | What |
|---|---|
| `levelkit.py` | The shared layout schema (D1): rectangles (colliders with tag, surface, owner, flags, `part`), walls with openings, edge guards, vehicles sliced as the Block's exporter did, props, points, interiors, doorways, and `Level.to_json()` in level.json's schema and units (web metres plus the `ue` mirror in cm) |
| `layouts/chinatown.py`, `layouts/midtown.py` | The hand-authored tables (D3, D4): every number from chinatown.md and midtown.md revision 2, the deviations marked `DEVIATION` and listed in the file's `meta.deviationsFromDesign` |
| `build_level.py` | Runs a table, derives the cover points and spawn facings, writes the level file |
| `navgrid.py` | The checker's mirror of the engine's rules: FMIBoxWorld::RebuildNav for the street plane, the "boxes" layer rule of midtown.md 17.3 for roofs, A* (8 neighbours, no corner cutting), the box ray cast, and a 0.25 m flood of the player's capsule that follows MoveCapsule and ScanColumn (radius 0.32, footprint 0.7 r, step 0.42, a jump climbs 1.0 + 0.08 m) |
| `check_level.py` | The checks (below) |
| `plot_level.py` | The plan pictures |
| `data/level_<id>.json`, `data/audio_<id>.json` | The level files and their audio zones (D3, D4) |
| `reports/check_<id>.json` | Every check's result and numbers, the guide paths of all six reel orders, the falls found (none) |

## What the files hold

Every section FMILevelData::Load reads, with its field names and types: `bounds`, `zones`, `colliders.boxes`
(tag, surface, owner, flags bulletOnly/playerOnly/noNav, index), `enemySpawns.points`, `coverPoints.points`,
`objectives`, `extraction` with `truck.pos/rotationY`, `playerStart`, `interior.boxes` and `doorways`,
`explosives.items` (each with its own collider), `cinematicPath.points`. Then the sections the designs add, all
optional and absent from the Block's file, so the Block's code path is unchanged:

- `nav`: `layers` (street "plane"; Canal's `roof` at 5.7; Midtown's `r1` 14.0, `r2` 17.6, `r3` 21.2, "boxes"),
  `links` (polylines; Canal's `yardStair`, Midtown's L1 to L6, the scaffold and service stair generated from their
  flights), `spawnReach`, `firingCellRange`, `strandedAfter`. **`grid` is null**: the grids are written by the engine
  bake (`-run=MILevelBake`, MAPS.md D2) with FMIBoxWorld's own code, never by this tool (the designs' rule: no second,
  Python copy of the nav rules in the data). The checker's mirror is for testing only.
- spawn points carry `layer`, `name`, and on Canal's roof `overlooks` and `enabled: false` (off until nav step A);
  objectives carry `layer`; Midtown's `extraction` carries `arrival: "afterAll"` and its truck colliders are owner kind
  `truck`, noNav (E10).
- `guide`: Canal is the single-layer search (`mode: singleLayer`, the design's legs and the two route-tie
  alternatives); Midtown is the route graph (`guide.graph` nodes and edges: links both ways, drops down only, the
  service stair and drops biased +10 m so the scaffold is the drawn way down).
- `drops` (every authored drop with its height), `tuning` (maxAliveAdd, excludePlayerRoom, startPitch, Midtown's
  waveAdd, pursuitBudgetAdd, Buzzard maxAltitude 36, rating), `checks` (inputs for the checker), Midtown's `views`.
- Art side: `ground.surfaces/floors` (rectangles), `buildings` (mass colliders, roofs, facades, shops), `propPlacements`
  (catalogue name, position, rotationY, colliders: the art lanes write props_<id>.json from these and fit the meshes to
  the colliders), `signage` (every sign and screen face: text, kind, position, normal, size, colour, night state),
  `layout` (the named lines), `steam`, `puddles`, `vantage`.
- **`el` is absent** in both. Today's loader requires `el.deck` (MILevelData.cpp line 148), so it cannot read these
  files until E2 makes `el` optional. `--el-fallback` writes MAPS.md E2's fallback, a deck 250 m outside the bounds
  (every deck test is a point-in-rectangle check, so it never applies), for a loader test before E2 lands.

**Signs are English only** (the owner, DECISIONS 2026-11-26 ~02:00): no Chinese characters anywhere in either file
(a check). Canal's `signage` takes every word from the art lane's list (art/blender/assets/_chinatown_names.py, run with
its own English check): each placement names its `face` key, text and carrier there, so a renamed shop is one line in
that list and a rebuild here. Canal Street reads as Chinatown through the market, the produce, the stall boards, the lantern string, the
bakery's pink neon, the arcade and the English shop names of chinatown.md 13.3. Every name is invented and still
needs the C1 search before its face is drawn; IPX is the only real mark.

The files live in `tools/levels/data/`, outside `Content/Data` on purpose: Content/Data is staged as loose files into
every package (Config/DefaultGame.ini) and git-ignores subfolders, and the release in progress (v6) must not change.
The maps branch moves them to `Content/Data/level_<id>.json` when the loader (E1) lands and levels.json joins them
(stage 3); `build_level.py --out` writes anywhere. levels.json is untouched.

## Checks (check_level.py)

| Check | Rule |
|---|---|
| schema.loaderSections, .counts, .reelIds, .zonesTileBounds | every loader section and field present with its type; ue mirror = web x 100; counts = levels.json `provides` (Canal 3 / 38 ground / 18 air / 18 explosives / 14 title keys; Midtown 3 / 30 / 18 / 17 / 14); the zones tile the bounds |
| content.englishOnly, .noRejectedRealNames | no CJK character anywhere in the file; none of the names the designs rejected as real |
| colliders.count, .explosiveIndices, .noThinMovementBoxes | at most 800 / 820, all axis-aligned; each explosive owns its collider; no movement box under 0.05 m |
| explosives.clearOfReelsAndTruck | none within 4 m of a reel or the extraction |
| spawns.groundOnFreeCells, .groundOneComponentPerLayer, .groundNotInsideColliders, .air | ground points on free cells of their own layer, one region per layer, no capsule inside a solid; air points 2.2 to 12 m over the ground below, 1.5 m from any collider, inside the bounds minus 1.2 m |
| spawns.fallbackRingNeverNeeded | chinatown.md 17 check 6: every 2 m on every layer, 3 or more ground points 9 m away, hidden from the eye by the box ray cast, outside the player's room, on an allowed layer (`overlooks` honoured) |
| reach.navCellNearEveryReel, reach.player | a free nav cell within 2.2 m of each reel on its layer; walking only (steps of 0.42 or less) the player reaches every reel and the extraction from playerStart |
| guide.everyReelOrder | a guidance path for all six reel orders, every leg start -> 3 reels -> IPX, over the street layer (Canal) or the route graph (Midtown) |
| guide.intendedLegsVsDesign, guide.routeTie.* | the intended order's legs within 10 % of the design's (WARN: design numbers); Canal's intended legs 3 and 4 at least 10 % shorter than the best route avoiding them |
| guide.linksOnWalkingSurfaces | every link polyline within 0.6 m over a tread, landing or deck every 0.25 m |
| reelRooms.goonPaths, doors.* | every reel has Goon paths from 2 or more ground spawns outside its room, one under 30 s at run speed; the Goon doors are open on the nav; Canal's player-only side door is closed to it |
| edges.noDropOver4m, drops.* | walking and jumping from playerStart the player never drops more than 4.02 m (the 13 m/s fall-damage landing); every authored drop is at most 4.0 m and both its ends are reached |
| slot.booth.* | Midtown: a ray passes the booth's slot; its frame is playerOnly |

Results on the committed files: **Canal Street 28 pass, 1 warn, 0 fail; Midtown 27 pass, 1 warn, 0 fail** (the reports
have every number). The warnings are design questions, below.

## Deviations from the designs (also in each file's meta.deviationsFromDesign)

Canal Street:
- The market's player-only side door moved 0.2 m (z -2.7..-1.3): at the design position one nav column stayed free and
  Goons could use it.
- One air point over the yard moved to z 9.4 (it was 0.75 m from the stair's guard).
- A THE DUB ROOM place region so the HUD names the reel's room.

Midtown:
- **The Stand's tiers 1 to 5 are two wings around a front court at plaza level (x 13..19).** As drawn, tier 5 (top
  2.15 m) stands in front of the booth's slot (1.0 to 2.0 m) and hides it, so nobody outside could fire in. The court
  makes the slot work. The designer should confirm the shape.
- The sidewalk shed by the scaffold runs z 20.1..24.4 (the design's z 20..30 would stand in the W 46 St roadway).
- The shed-hop opening in the tower's south guard is over the west column only.
- Broadway's water barriers at z 17.6..18.2 (south of the parked van); g23 moved to z 18.8 to stay behind them.
- ground.surfaces uses the design's surface words (granite, gravel, bitumen, grating, steel); the audio lane maps them.

## Open

- **Canal leg 4 route tie (WARN).** From Reel 6 the intended way out (partition door, banquet hall, the Square, the
  arcade) measures 60.7 m and the way out the Mott roll-up and up Mott St 60.9 m on the 8-neighbour A* the guidance
  uses: a 0.4 % margin, under the design's 10 %. The drawn path can flip between them. The design's reason (the roll-up
  "south of the reel's partition door") does not hold for its own numbers (roll-up z 24..27, partition door z 26..28,
  reel at z 28.4). Choices for the lead: path hysteresis in the guidance (G2), or a layout change (the reel and the
  racks against the partition, the roll-up moved north, or the hall's tables cleared into a straight aisle); none gives
  10 % alone by my measurements, so hysteresis is the likely answer.
- **Midtown legs vs the design (WARN).** Start -> Reel 7 42.2 m (design 37) and Reel 8 -> Reel 9 128.9 m (design 108):
  the scaffold's eight flights and landings walked as a polyline are about 45 m, longer than the design counted. The
  rating times (330 s / 480 s) should be re-checked in the grey box.
- Nav step A (N1 to N4) and the loader's `el`/`ForLevel` (E1, E2) are C++ for lanes N and E: nothing here replaces
  them. The checks above are design checks; Levels.<Id>.Loads / .Nav / .Reach / .Edges / .ReelRooms in the
  engine stay the authority.
- Collider counts are 336 (Canal) and 422 (Midtown), well under the caps: the designs' planned street clutter (about
  230 small colliders on Canal) is left for the art lanes to add with their placements, inside the caps.
- Cover points: 150 (Canal, design about 112) and 138 (Midtown, design 110, only 2 on W 46 St against 10 planned:
  the street has few solids yet). The bake re-filters them.
- `audio_<id>.json` (zones in audio.json's schema, the beds and one-shots as names for the audio lane) is written next
  to each level file. props_<id>.json and atmos_<id>.json are not: the level files carry `propPlacements` and the
  sign faces, and the night rigs and lights are lane L's.
- The engine bake is a patch, not built: docs/unreal/patches/maps-D (the street grids with FMIBoxWorld's code now; the
  roof grids when nav step A exists).
