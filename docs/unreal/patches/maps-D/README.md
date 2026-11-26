# maps-D: the engine bake of the new level files (MAPS.md lane D, item D2), unbuilt

`0001-MILevelBake-commandlet.patch` adds `Source/MurderInc/Tools/MILevelBakeCommandlet.{h,cpp}`: two new files, no
existing file touched, nothing the Block's code path reaches. It is **not built and not run** (no Unreal and no box
when it was written; the release in progress, v6, must not change). It lands on the maps branch cut from the v6 commit
(MAPS.md section 5), with E1/E2, and is built and run there.

```
git apply docs/unreal/patches/maps-D/0001-MILevelBake-commandlet.patch     # on the maps branch only
UnrealEditor-Cmd MurderInc.uproject -run=MILevelBake -In=tools/levels/data/level_chinatown.json
UnrealEditor-Cmd MurderInc.uproject -run=MILevelBake -In=tools/levels/data/level_midtown.json
```

What it does, with the runtime's own code and no second copy of the nav rules:

- reads the colliders exactly as FMILevelData::Load does, fills an FMIBoxWorld per "plane" layer and writes its grid
  (FMIBoxWorld::RebuildNav through the public NavCols / NavRows / NavBlocked) into `nav.layers[*].grid` in level.json's
  row format, with cols, rows, free and blocked;
- roof layers ("boxes") are baked only when nav step A's per-layer build exists (MAPS.md N1; the patch calls
  `FMIBoxWorld::ResetLayer(Bounds, Rng, LayerY)` under `MI_WITH_NAV_LAYERS`, the name lane N should give it or rename
  here); until then their `grid` stays null and the report says "pending N1";
- filters cover points onto walkable cells of their baked layer and re-indexes them;
- writes a report to `Saved/LevelBake/bake_<id>.json`: cover dropped, ground spawns off the nav (exit status 1 if
  any), and FindPath from playerStart to each reel and the extraction where both are on the street plane (Canal; on
  Midtown the start is on r3, so reach waits for the links of nav step B, N5).

The Python checker (`tools/levels/check_level.py`) mirrors the same rule for design checks; after the bake, the
engine test `MurderInc.Levels.<Id>.Nav` (progression.md 9.1) compares the baked grid with a rebuild, cell for cell.
Expected on today's data from the mirror: street free cells 10,761 (Canal) and 10,568 (Midtown); no cover dropped,
no spawn off the nav.

To check on the maps branch: it compiles (the commandlet needs only Core, CoreUObject, Engine and Json, already in
MurderInc.Build.cs), the baked Canal street grid equals the mirror's (`tools/levels/navgrid.py layer_grid`), and a
second run is byte-identical.

## 0002: the loader skips disabled spawn points (MAPS.md E8), unbuilt

`0002-MILevelData-skip-disabled-spawns.patch` changes one loop in `FMILevelData::Load`: a spawn point whose JSON carries
`"enabled": false` is not added to `Spawns`. Canal Street's three roof points (rf1 to rf3) carry it until nav step A
exists; without this, any build before N1 (and the loader test with `--el-fallback`) would spawn Goons at y 5.7 on a
street-only nav, and they would walk off the roof edges (the roof guards are playerOnly). The Block's level.json has no
`enabled` field, so its spawn list, indices and goldens are unchanged. Spawns after a skipped point shift down by one in
the loaded list; nothing in the game addresses a spawn by its file index (the spawner draws from the list), but the
maps branch should confirm that with `Levels.Chinatown.Loads` (expected: 35 ground + 18 air loaded while rf1 to rf3
are off). The release turns the three points on (`enabled` true or absent) once N1 lands;
`python3 tools/levels/check_level.py --release` fails while any point is still disabled.

```
git apply docs/unreal/patches/maps-D/0002-MILevelData-skip-disabled-spawns.patch   # on the maps branch only
```
