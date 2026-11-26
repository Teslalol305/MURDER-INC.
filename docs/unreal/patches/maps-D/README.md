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
