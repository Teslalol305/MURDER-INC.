# Unreal rebuild: progress

What is verified on the box, newest first. Every entry says how it was verified. The loop and the pitfalls are in
`docs/unreal/BOX.md`.

## Exact next step

1. Facade kit: when `art/out/glb/SM_Facade_*.glb` is complete, `tools/box/send-art.sh pack 'SM_El_*' 'SM_Street_*'
   'SM_Prop_Hydrant' 'SM_Facade_*'`, transfer (BOX.md section 4), `block.sh start textures,materials,meshes`, then
   replace the brick grey-box of the `facade` colliders in `build_block.py` with facade modules (spec 05-level.md
   facade layout, level.json `buildings`). Their glass, interior and chrome slots need flat (untextured) instances:
   the master has no flat mode yet.
2. Prove the vertex-colour decode with a ramp test asset (art bible 3.3): a strip painted 0, 0.25, 0.5, 0.75, 1 per
   channel, read back in the material (BOX.md section 5).
3. The day sky: volumetric clouds at low cover; the far ground plane is a flat tinted asphalt slab (the web game's
   far city sheet and skyline rings are not built).

## 2026-11-22

- **The block in Unreal, first pictures** (`docs/unreal/shots/block-v0-1.jpg` ... `-4.jpg`, 1920 x 1080, through
  `tools/box/block-shots.sh`): eye level at the player start looking east under the El; a south-row column and its
  pedestal; under the deck looking up at a bent; a high overview of the block. Two review rounds: round 1 fixed
  black shade (scene captures had no sky light and no Lumen: pictures now come from the piloted editor viewport and
  HighResShot), clipped cached lighting (pre-exposure 8), too dark exposure (clamped auto exposure EV100 12.9 to
  14.2) and brick on the roofs of the massing (concrete on upward faces); round 2 moved the column and deck cameras
  out of grey-box clutter.
- **`/Game/Maps/L_Block` assembled from data** by `unreal/MurderInc/Content/Python/build_block.py` (`block.sh start
  level`, 7 s, 920 actors, saved): 7 road pieces and 140 kerb and sidewalk modules along the avenue (X -70 to +70 m,
  gutter lines at Y +-700); the El from `level.json` `el` (18 bents, 17 girder spans and decks, 36 columns, 9 lamps
  at the `atmos.json` El lamp positions; deck underside at Z 650 as the mesh bounds show); 657 grey-box cubes, one per
  movement-blocking static collider of `level.json` (bullet-only colliders and the ones the El and street meshes
  draw are skipped), with world-projected scanned brick or concrete by collider surface; 12 ground slabs from
  `ground.surfaces` off the avenue and a far ground plane; a player start at `playerStart`; the day rig from
  `atmos.json` `rigs.day`: sun at pitch -52.0 yaw -26.1 and 99,956 lx (5 game lux x 24,400 lx x colour
  luminance, spec 06 4.5), source angle 0.5357, atmosphere sun light; sky atmosphere with 2.5 x Mie scattering; real-time
  sky light; height fog for about half of the web haze at 92 m (density 0.0047) with volumetric fog; unbound
  post-process volume with Lumen GI and reflections, clamped auto exposure, bloom 0.25 without threshold, vignette
  0.15, white balance 6,300 K, local exposure, saturation 1.05.
- **Art imported** (`block.sh start textures,materials,meshes`): 60 textures of 20 sets, the master material
  `M_MI_Surface` (base colour, normal, ORM, tint, optional second set on G, the four `Wear` masks with a value-noise
  breakup, world box projection for the grey-box) and 30 instances, 16 meshes with Nanite. Every mesh's bounds equal
  the manifest's Unreal bounds to 0.0 cm: axes and scale right, unmirrored (BOX.md section 5). The lamp lens slot
  (`TS_Glass_SodiumLens`, no texture set yet) uses a warm-tinted concrete stand-in.
- **Art transfer** works: `send-art.sh pack` (163 MB, 16 GLBs, 21 sets), `send-art.sh put` (19 s), `media_confirm`
  type file, box download and unpack to `/project/ue/art-in` (4 s). `receive-art.sh` is the box half.
- **Build and tests green**: `build-status.sh` BUILD OK (127 s game module build), `test.sh` TESTS OK passed=2
  failed=0 (29 s), run again after the last change. Editor stopped at the end.
- `docs/unreal/BOX.md` written: the loop, timings, every pitfall the scripts encode.

## Before 2026-11-22 (the bootstrap)

- The project `unreal/MurderInc` compiles on the box (`-NoUBA`), the headless editor starts with its MCP server, the
  bootstrap map `L_Bootstrap` is built by `mi_bootstrap_map.py`, and a picture of it came back through the transfer
  procedure (`docs/unreal/shots/bootstrap.jpg`; its black shade is the scene-capture limit found later).
