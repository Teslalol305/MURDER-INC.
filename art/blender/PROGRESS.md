# Progress (art/blender)

Task: library check + README, scan-backed materials + HDRI day rig, the El kit (assets/el.py), look-dev previews.

## Done (earlier runs, reviewed by the current run where marked)
- mi/mat.py: `from_scan(set_name, ...)` / `ctx.scan_set(...)` build materials from catalogued scans (reviewed: in use).
- mi/steel.py: riveted-steel builder (plates, angles, rivets, leak sources for the wear mask).
- assets/el.py: SM_El_Column, SM_El_Bent, SM_El_GirderSpan_10m, SM_El_Deck_10m, SM_El_Lamp + layout + on_preview.
- art/previews/el_wire.jpg rendered (clay): detail reads well.
- art/out/glb/SM_El_*.glb exist from the earlier run (not yet re-validated by this run).

## In progress (this run)
1. `build.py build el --export` : confirm build + validation end to end.
2. Render el_day_hero / el_day_column / el_day_under (`--preview --only <name>`), then street_day_hero refresh.
3. README.md.

## Exact next step
Run: `python art/blender/build.py build el --export` and read the validation output.

## Update (this run)
- `build el --export` passes validation: column 32156, bent 42900, span 108844, deck 62228, lamp 2220 tris.
- Rendered el_day_hero, el_day_column, el_day_under (64 samples, HDRI day rig). README.md written.
- Review round 1 fixes applied in code (el.py on_preview cameras: hero closer to the kerb and aimed under the
  structure, column camera includes the pedestal; lamps off by day; pale blotches removed from the dressing walls).
- Next: re-render `build el --preview --only el_day_hero,el_day_column --samples 64`, then
  `build street --preview --only street_day_hero --samples 64`, look at each, one more fix round at most.
- Round 1 re-renders done (hero, column: good). street_day_hero refresh rendering.
- Round 2 (last): hero aimed further under the structure (target y +3.0); el_day_under re-render with lamps off.
  Command: `build el --preview --only el_day_hero,el_day_under --samples 64`. After that: final `build el --export`
  and `build street --export` to leave manifest and GLBs current, then report.

## State at hand-off: task complete
- Round 2 renders done and looked at: el_day_hero, el_day_under (lamps off), street_day_hero refreshed.
- Final `build el --export` and `build street --export` passed validation; art/out/manifest.json is current.
- Nothing is pending. Known weaknesses (for a later pass): preview dressing is blank brick massing and a low yard
  wall; guard rails are timber only (no steel inner guard rail); the street's utility patch reads as a flat dark
  rectangle; wear masks are per-vertex at about 0.15 m, so rust edges are soft until Unreal adds detail noise.

---------------------------------------------------------------------------------------------------------------
# Facade kit (assets/facade.py), started after the El hand-off

Task: modular street-front kit (ground floor, upper floors, top, fire escape, roof items), assembly helper, sample
of the south block face (S1 + S2 + S3, seven storefronts) with the street and three El bays, four previews
(facade_day_hero / facade_day_street / facade_storefront / facade_wire), GLB export + manifest + validation, README.

## Status
- [x] assets/facade.py written (modules + `assemble_front` / `assemble_shell` helpers + on_preview)
- [x] `build.py build facade --export` passes validation: 77 modules, no warnings (run 3 fixed the mirrored hoop lugs of the water tank)
- [x] previews round 1 rendered and looked at (wire, hero, storefront, street)
- [x] round 1 fixes in code: glass film/dirt much lighter (store glass read milky), hero +0.5 and storefront +0.9 stops,
      cornice run stops 2 mm inside the end block (coplanar caps rendered as a black patch in clay)
- [x] round 2 (last) rendered and looked at: glass clear with reflections, clay corners clean
- [x] README family row; final `build facade --export`: 77 GLBs, no validation errors or warnings, manifest current

## State at hand-off: task complete
Known weaknesses: sign bands are flat colour placeholders; glass shows only reflections (no interior parallax yet); previews under the El stay dark; the roll-gate bay (Nails, S3) is in no preview; no rear walls or N-side buildings in the sample.
