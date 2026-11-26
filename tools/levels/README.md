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
- spawn points carry `layer`, `name`, and on Canal's roof `overlooks` and `enabled: false` (off until nav step A;
  the loader must skip a disabled point, MAPS.md E8, and `check_level.py --release` fails while one is left);
  objectives carry `layer`; Midtown's `extraction` carries `arrival: "afterAll"` and its truck colliders are owner kind
  `truck` and not noNav: the bake blocks the stop spot from the start, the box world takes the colliders on arrival (E10).
- `guide`: both levels carry the route graph (`mode: routeGraph`, `guide.graph` nodes and edges: links both ways, drops
  down only). Canal's graph is the yard stair and the kitchen-roof drop onto the Mott shed and off it, so a player on the
  roof is drawn a walkable way down; on the street its path is the street layer's own search, as on the Block. Midtown's
  biases the service stair and the drops +10 m so the scaffold is the drawn way down. `guide.pathHysteresis` (0.10) is
  MAPS.md G4; `guide.waivers` records every gate a level fails on purpose, with the reason and the owner.
- `colliderBudget`: the design's clutter groups, planned against placed, and every clutter prop the layout tool skipped
  because it would have stood on a spawn, a reel, a door, a link or another collider (`levelkit.Level.clutter`).
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

`python3 tools/levels/check_level.py [--level id] [--quick] [--release]`. A gate that fails is FAIL (exit 1) unless the
level records a waiver for it (`guide.waivers`: the check, the legs it covers, the reason, the owner); it is then
WAIVED and printed with the reason. WARN is used for one advisory check only (`spawns.allEnabledForRelease`, a FAIL with
`--release`).

| Check | Rule |
|---|---|
| schema.loaderSections, .counts, .reelIds, .zonesTileBounds | every loader section and field present with its type; ue mirror = web x 100; counts = levels.json `provides` (Canal 3 / 38 ground / 18 air / 18 explosives / 14 title keys; Midtown 3 / 30 / 18 / 17 / 14); the zones tile the bounds |
| content.englishOnly, .noRejectedRealNames | no CJK character anywhere in the file; none of the names the designs rejected and no real mark the art bible forbids, anywhere |
| content.noRetiredNames, .namesOnApprovedList | tools/names/names.json (lane C): no retired name or id built from one anywhere in the file; every sign face, screen slide and shop list names an approved name, a generic word, a real place or a story mark of the level |
| colliders.count, .explosiveIndices, .noThinMovementBoxes, .surfacesKnown | at most 800 / 820, all axis-aligned; each explosive owns its collider; no movement box under 0.05 m; every surface a key of audio.json surfaces |
| colliders.plannedClutter | the design's clutter groups (chinatown.md 14.1, midtown.md 15) placed at 75 % of the plan or more, under the cap |
| explosives.clearOfReelsAndTruck, .clearOfDoorways | none within 4 m of a reel or the extraction; none within 4 m of a doorway centre or a Goon door (chinatown.md 9; a design exception goes in checks.explosiveDoorExceptions) |
| extraction.lateTruckBlocksNav | Midtown: the arriving truck's footprint is blocked on the street nav from the start; its colliders stay out of rays and movement until it arrives |
| spawns.groundOnFreeCells, .groundOneComponentPerLayer, .groundNotInsideColliders, .air | ground points on free cells of their own layer, one region per layer, no capsule inside a solid; air points 2.2 to 12 m over the ground below, 1.5 m from any collider, inside the bounds minus 1.2 m |
| spawns.allEnabledForRelease | every point enabled (WARN; FAIL with `--release`) |
| spawns.fallbackRingNeverNeeded | chinatown.md 17 check 6, a gate: every 2 m on every layer, 3 or more enabled ground points 9 m away, hidden from the eye by the box ray cast, outside the player's room, on an allowed layer (`overlooks` honoured) |
| reach.navCellNearEveryReel, reach.player | a free nav cell within 2.2 m of each reel on its layer; walking only (steps of 0.42 or less) the player reaches every reel and the extraction from playerStart |
| guide.everyReelOrder, guide.fromEveryLayer | a guidance path for all six reel orders over the route graph; from cells every 4 m on every upper layer, a route to each reel and the extraction |
| guide.intendedLegsVsDesign, guide.routeTie.* | gates: the intended order's legs within 10 % of the design's; Canal's intended legs 3 and 4 at least 10 % shorter than the best route avoiding them |
| guide.linksOnWalkingSurfaces | every link polyline within 0.6 m over a tread, landing or deck every 0.25 m |
| reelRooms.goonPaths, doors.* | every reel has Goon paths from 2 or more ground spawns outside its room, one under 30 s at run speed; the Goon doors are open on the nav; every player-only gap is closed to the nav and 1.0 m wide or less (closed at every grid alignment) |
| edges.noDamagingDrop, drops.authoredFreeWhenJumped, drops.authoredReachable | walking from playerStart no drop over 4.02 m; jumping (the jump flood), no drop over 3.02 m: a jump's 1.0 m apex adds to the fall (MIPlayerRules takes the peak fall speed); every authored drop plus 1.0 m stays under 4.02 m, and both its ends are reached |
| sight.* | eye to eye at 1.6 m, street cells sampled every 1 or 2 m: Canal no open line over 81 m (the 77 m start-to-truck line between nav cells) and none over 45 m along the south sidewalk (the protected lane); Midtown none over 45 m in the square (midtown.md 10) |
| slot.booth.* | Midtown: a ray passes the booth's slot; its frame is playerOnly |

Results on the committed files: **Canal Street 37 pass, 1 warn, 1 waived, 0 fail; Midtown 36 pass, 0 warn, 1 waived,
0 fail** (the reports have every number). The warn is Canal's three roof spawns, still disabled until nav step A. The
waivers: Canal's leg-4 route tie (6 %, the guidance's path hysteresis, MAPS.md G4) and Midtown's two long legs (the
design counted the steel stair and the scaffold short; the rating times are re-timed in the grey box).

## Clutter (chinatown.md 14.1, midtown.md 15)

The layouts author the street furniture, alley and yard props, vendor goods, map edges, the premiere's structures, W 46
St and the roof dressing as colliders (`L.clutter`), so the grey box of stage 2 is built with its cover; the art lanes
fit their meshes to them. Canal: 599 colliders (clutter 337 of the 414 planned in those groups; the rest of the 780 is
the vehicle slicing the design assumed, about 5 boxes a car, where the data keeps the Block's body-and-glass pair).
Midtown: 613 colliders (clutter 248 of 299). The line breakers are named in the tables: Canal's garment rails turned
across the south sidewalk and the tall shop displays (the protected lane), newsstands and steam chimneys; Midtown's
broadcast, cable, catering and staging trucks, trailers, light towers, press walls, tents, booths and truss towers of the
premiere (the 45 m rule). Cover points: Canal 240 (design about 112), Midtown 160 (110; W 46 St 17 of 10), before the
bake's filter.

## Deviations from the designs (also in each file's meta.deviationsFromDesign)

Canal Street:
- The market's player-only side door is 1.0 m (z -2.7..-1.7, centred where the design put its 1.4 m door): a gap of
  1.0 m or less is closed to Goon nav at every grid alignment; the 1.4 m door was closed only by where the cells fell.
- The Mott sidewalk shed's deck is 3.0 m (design 3.2): jumped, 3.2 + 1.0 m lands over the damage speed; R1 is 2.7 m, R2 3.0 m.
- A guard on the yard parapet over the stair's flight 2 (the parapet top stood 3.2 m over the treads).
- Explosives moved 4 m or more off the doorways: propane 1 and 2 with their stall to the market's corner pier, propane 6
  to x 7.2, rack 14 into the workshop's back corner, rack 15 out of the arcade to the Square's east side.
- Reel 6 at x 22.2 (design 21.2): the leg-4 route tie from 0.4 % to 6 %; the rest is G4 (waiver).
- The north-lane SUV by the IPX truck is a step van (2.1 m): with the newsstands it ends the long lines at 81 m.
- Vendor racks hang bags to 1.9 m over the whole table (design 1.3 m): with the chicanes they screen the protected lane.
- One air point over the yard at z 9.4; a THE DUB ROOM place region (unchanged from the first build).

Midtown:
- **The Stand's tiers 1 to 5 are two wings around a front court at plaza level (x 13..19).** As drawn, tier 5 (top
  2.15 m) stands in front of the booth's slot (1.0 to 2.0 m) and hides it. The designer should confirm the shape.
- THE LOFTLARK's raised deck on D and a dunnage platform on E, both 0.6 m with a 0.3 m step: D1 and D2 land on them, so
  each drop is 3.0 m and free even when jumped (design 3.6 m, about 6 damage jumped).
- The scaffold's sidewalk shed deck is 3.0 m (design 3.2), so D3b is 3.0 m.
- Guards on the Stand's top tier and the booth's back wall (north and sides, 3.2 m over the plaza).
- Rack x9 in the scaffold head's east corner (design: 1.7 m from the gantry door north).
- The arriving truck is not noNav (the bake blocks the stop spot from the start).
- The sidewalk shed by the scaffold runs z 20.1..24.4; the shed-hop opening is over the west column only; Broadway's
  water barriers at z 17.6..18.2; g23 at z 18.8; g12 at (-25.5, 4.8) off the deck; surface names are audio.json's keys.

## Open

- **Canal leg 4 (WAIVED):** the guidance's path hysteresis (G4) keeps the drawn route until another is 10 % shorter.
- **Midtown legs (WAIVED):** start to Reel 7 42.5 m (design 37), Reel 8 to Reel 9 135 m (108): re-time the rating in the
  grey box.
- Canal's roof spawns stay disabled until nav step A; the loader must honour `enabled` (E8); `--release` fails until then.
- Nav step A (N1 to N4) and the loader's `el`/`ForLevel` (E1, E2) are C++ for lanes N and E: nothing here replaces
  them. The checks above are design checks; Levels.<Id>.Loads / .Nav / .Reach / .Edges / .ReelRooms in the
  engine stay the authority.
- The engine bake (docs/unreal/patches/maps-D) is unbuilt and runs on the maps branch; `enabled` in the loader is the
  patch docs/unreal/patches/maps-D/0002 (unbuilt). The files move from tools/levels/data to Content/Data with E1.
