# Scanned surfaces, skies and props

A curated library of photo-scanned materials, sky domes and props for the Hollis block: Jamaica Avenue under the El,
brick tenements, shop fronts with roll-down gates, the cinder-block auto body shop, the ball court, the vacant lot and
the parking lot. Every tiling surface carries the real size of one repeat in metres, fixed from the picture itself and
cross-checked against the publisher's own figure, so that a brick course is 67.7 mm wherever a material is used.

Everything comes from Poly Haven and is CC0. Nothing that was downloaded is committed (`art/out/` is git-ignored).
What is committed is this folder: the catalogue, and the scripts that rebuild `art/out/` from it with one command.

| File | What it is |
|---|---|
| `sets.json` | The catalogue. One entry per tiling set, sky and prop: where it goes on the block, the tile size and how it was fixed, the files, colour notes, licence, and a `measured` block of numbers taken from the files. |
| `fetch.py` | Downloads what the catalogue lists, writes the convention files, verifies them, prints a table. |
| `calibrate.py` | Measures the files (repeat counts, seams, relief, albedo, sun position, model bounds) and writes the numbers into the catalogue. |
| `render_sheets.py` | Renders the preview pictures in `art/previews/` with Cycles. |
| `probe.py`, `probes.json` | Existence checks on the download host, and the record of every answer so far. |

## Re-running

```
python3 art/scans/fetch.py                      # everything in the catalogue at 2k: about 1.7 GB down, 3.4 GB on disk
python3 art/scans/fetch.py --res 4k --only TS_Brick_ScanRed TS_Asphalt_ScanCracked
python3 art/scans/fetch.py --offline            # no network: rebuild and verify from the cache
python3 art/scans/calibrate.py                  # re-measure everything and rewrite sets.json (about 3 minutes)
python3 art/scans/calibrate.py --check          # change nothing; fail if catalogue and files disagree
python3 art/scans/calibrate.py --readme         # rewrite the tables below from the catalogue
<python with bpy> art/scans/render_sheets.py    # preview pictures (Blender 5.3 as a Python module; about an hour on 2 threads)
```

`fetch.py` and `calibrate.py` need Python 3 with pillow and numpy, nothing else. `fetch.py` is idempotent: a second run
makes no request and rewrites no file. It exits non-zero if any file is missing, does not open, or is not the size the
catalogue says. With `--res 4k` the convention files are replaced by their 4k versions (same names, same tile sizes in
metres); run it again without the option to go back.

## Licence

All assets are from Poly Haven and are released under CC0 1.0 (public domain dedication): free for any use, commercial
included, no attribution required. Every catalogue entry says so in its `licence` field.

## The direct-download rule

The only network source is Poly Haven's download host, `https://dl.polyhaven.org/file/ph-assets/`, by direct file URL.
The scripts never call the Poly Haven API, never fetch from another site, send `User-Agent: asset-pipeline/1.0`, run at
most 4 requests at a time, and ask for each file once: downloads are kept under `art/out/scans/raw/` (a mirror of the
remote tree), and a path that answered 404 is remembered in `art/out/scans/raw/missing.json` and never asked for again.

Paths on the host, as used here:

| What | Path under `ph-assets/` |
|---|---|
| Texture map | `Textures/<jpg\|png\|exr>/<res>/<slug>/<slug>_<map>_<res>.<ext>`: maps `diff`, `nor_gl`, `nor_dx`, `rough`, `arm`, `ao`, `disp` |
| Texture descriptor | `Textures/gltf/<res>/<slug>/<slug>_<res>.gltf` |
| Sky | `HDRIs/<hdr\|exr>/<res>/<slug>_<res>.<ext>` |
| Model | `Models/gltf/<res>/<slug>/<slug>_<res>.gltf`, with its `.bin` beside it |
| Model texture | `Models/jpg/<res>/<slug>/<file>` |

Three things about the host that are not obvious and cost requests to find out:

- Every texture has a small glTF descriptor. It lists the maps the set really has (a few old sets call the base colour
  `diffuse` or `col_01`, so asking for `<slug>_diff_2k.jpg` misses them), and it holds a preview sphere whose diameter is
  the real-world width the publisher states for the tile (0.1 m for denim, 30 m for the aerial asphalt). That figure is
  recorded for every set as `publisher_stated_m`. `probe.py` asks for this file when it checks a texture slug.
- A model's `.gltf` refers to its textures as `textures/<file>`, but the host does not keep them in the model's folder:
  they are under `Models/jpg/<res>/<slug>/`. The first run of `fetch.py` asked for them beside the `.gltf` and got 154
  answers of 404 before this was corrected; those paths are in `missing.json` and are not asked for again.
- All 83 texture sets chosen here have an `_arm` map, so no ORM had to be packed. `fetch.py` can still pack one from
  `_ao`, `_rough` and `_metal` when a catalogue entry lists them under `"pack"`.

Existence checks so far: PROBE_SUMMARY. The answers, found and missing, are in `probes.json`; `python3 art/scans/probe.py
--status` prints them. Do not probe a slug that is already there.

## What `fetch.py` writes

```
art/out/textures/<Set>/T_<Set>_BC.jpg    sRGB base colour                              source JPEG bytes, untouched
art/out/textures/<Set>/T_<Set>_N.jpg     tangent-space normal, OpenGL (+Y up)          source JPEG bytes, untouched
art/out/textures/<Set>/T_<Set>_ORM.jpg   R ambient occlusion, G roughness, B metallic  the source _arm JPEG, untouched
art/out/textures/<Set>/T_<Set>_H.png     height, one channel, 16 bit                   source PNG bytes, or converted (below)
art/out/textures/<Set>/set.json          tile size, density, height range, albedo      written from the catalogue
art/out/hdri/<slug>_2k.hdr               Radiance HDR, 2048 x 1024
art/out/scans/models/<slug>/             <slug>_2k.gltf, <slug>.bin, textures/*.jpg: as downloaded, in the layout the .gltf expects
art/out/scans/raw/                       the download cache (do not edit)
art/out/scans/cells/                     cached preview renders
```

`<Set>` is the full set name, so the base colour of `TS_Brick_ScanRed` is
`art/out/textures/TS_Brick_ScanRed/T_TS_Brick_ScanRed_BC.jpg`. The exact paths are in each entry's `files`.

Where the bytes are not the publisher's:

- Height maps of 13 sets come as 16-bit grey+alpha or RGB PNGs. Pillow reads those at 8 bits, so `fetch.py` has its own
  PNG reader and rewrites them as single-channel 16-bit PNGs with every sample intact. One set, `TS_Brick_ScanRedEnglish`
  (an old scan), only has an 8-bit height map.
- `TS_Fabric_ScanCanvas` (2048 x 2052) and `TS_Fabric_ScanBurlap` (2048 x 2036) are resampled to 2048 x 2048, because a
  game engine wants powers of two. The picture is squeezed, not cropped, so it still tiles.

## Using a tiling set

- `tile_m` is `[x, y]`: the metres of real surface one repeat covers, x along the image's width and y up its height.
  Map with `UV = (world_x / tile_m[0], world_y / tile_m[1])`. Do not assume the tile is square: many brick and block
  sets are mapped a few per cent away from square pixels so that both the course and the unit length land on the US
  module (the entry's `notes` say by how much; the normal map is used as it is, so its slopes are off by the same few
  per cent along one axis).
- Each set folder also holds a `set.json` with the tile size, texel density, height range in metres, mean albedo and
  seam result, in the format the Blender pipeline (`art/blender/mi`) writes for the sets it bakes: its
  `mat.from_texture_set()` and its export manifest read scanned and baked sets alike.
- `orientation` says which way courses, slats, ribs, boards or cracks run. Walls are stored with y up the wall.
- Height: world height in mm = (H in 0..1 - `measured.height_mid`) x `measured.height_scale_mm`. The scale is the
  amplitude at which the height map's slopes agree with the normal map at the stated tile size; `measured.relief_fit`
  is how well they agree (1 is perfect; below 0.5 use the normal map alone). `measured.relief_mm` is the resulting
  1st-to-99th percentile relief.
- `colour` says what grading the scan needs to pass for New York. Most scans are South African or European: the brick
  is redder or more orange, the soil is orange, and the concrete is darker than a sunlit Queens sidewalk.
  `measured.albedo` gives the mean linear base colour to grade against (fresh asphalt is about 0.05, aged asphalt 0.10
  to 0.18, weathered concrete 0.20 to 0.30, sunlit sidewalk 0.30 to 0.40, red brick 0.15 to 0.30).
- `confidence` is `high`, `medium`, `low` or `stand-in`: see the next section.

## How the sizes were fixed

No tile size in the catalogue is a guess, and none is simply the publisher's figure taken on trust. There are two
recipes, stored per set under `basis` so that `calibrate.py` can recompute `tile_m` and `--check` can catch a mismatch.

**Count x unit.** Where the surface is built of units with a standard size, the units in one tile are counted and
multiplied by the US dimension: brick courses x 67.7 mm and stretchers x 203.2 mm, block courses x 203.2 mm and blocks
x 406.4 mm, roll-shutter slats x 66.7 mm, corrugations x 76.2 mm, boards, pavers, tiles, panels. The count comes from
the image: a regular pattern that wraps must repeat a whole number of times, so the power spectrum of the height map's
row and column profiles peaks at that number; units that are staggered from row to row (bricks in running bond) are
counted from the autocorrelation taken line by line. Every count was then checked by eye against a ruler overlay.

**Stated size, checked.** Where there is no unit to count (asphalt, cast concrete, stucco, rust, soil), the size is the
publisher's stated width, and the picture was checked against it: the size of something whose real size is known was
measured on a 1:1 crop with a millimetre scale (asphalt aggregate, form-tie holes, crushed stone, thread pitch, leaves).
The check is written into `tile_method`.

Why the publisher's figure can be trusted where it can be checked: divided by the counted units it gives real product
sizes, set after set. The corrugated sheet comes out at 75.8 mm pitch (stock: 76.2), the grey shutter at 64.8 mm slats,
the box-profile sheet at 201 mm ribs, the rubber tiles at 504 mm, the framed steel panels at 611 mm, the dark planks at
227 mm, the flags at 600 x 300 mm, and the fifteen brick sets at courses of 68 to 88 mm: European and South African
brick formats. So the counts are right, the publisher's sizes are honest, and the brick sets are deliberately used at a
different size from the scanned wall: the New York module.

Where count and publisher disagree, the count wins and the entry says so: `TS_Brick_ScanRedEnglish` (the stated 0.51 m
would make courses of 36 mm), `TS_Shutter_ScanBrown` (stated size gives 49 mm slats; used 36 % larger to share the US
slat), `TS_Corrugated_ScanWeathered` and `TS_Corrugated_ScanPeeling` (stated sizes give pitches of 97 and 114 mm, which
no stock sheet has), `TS_Wood_ScanTie` (300 mm boards, used 24 % smaller so that one board is one tie).

`confidence`:

| Value | Meaning | Sets |
|---|---|---|
| `high` | Count x standard unit confirmed on the picture, or a stated size confirmed by a feature of known size | CONF_HIGH |
| `medium` | Count is firm but the unit was chosen (or the publisher disagrees); or the confirming feature has a wide natural range | CONF_MEDIUM |
| `low` | Nothing of standard size in the picture: the publisher's figure stands on its record with the other sets | CONF_LOW |
| `stand-in` | Deliberately used at another size than the scanned surface, for want of the real thing | CONF_STANDIN |

## What the checks found

**Seams.** Each base colour and height map is tested across both wraps at three scales: the difference between the
last and the first row (column) is compared with the differences between ordinary neighbours inside the picture.
SEAM_SUMMARY

**Relief.** The height-from-normal fit was validated on the one surface with a known profile: `TS_Corrugated_ScanGalv`
comes out 18.6 mm deep, and the stock sheet is 19 mm. LOWFIT_SENTENCE

**Normal maps.** They are OpenGL style (+Y up), as the convention asks: in every set whose height map is usable, the
green channel rises with the slope up the image (`measured.normal_fit_red_green`). NORMAL_SENTENCE

**Skies.** The sun elevation measured in the two Kloofendal skies is 42.9 and 47.9 degrees, as their names say (43d,
48d), and a rendered shadow of a 1 m pole gave 42.5 degrees and landed at the requested azimuth to 0.1 degree, which
fixes the rotation convention given below.

**Scale by eye.** Every surface was rendered on a 4 m panel beside a 1.8 m box and a 1 m stick and looked at
(`art/previews/scans_sheet_*.jpg`). The brick walls all show the same course height, 1.5 courses to the stick's
decimetre; nothing reads at the wrong size.

<!-- tables:start -->
<!-- tables:end -->

## Skies

- The default look (hot clear afternoon, about 4:15 PM, a few cumulus) is `kloofendal_48d_partly_cloudy_puresky`; the
  cloudless twin is `kloofendal_43d_clear_puresky`. At 4:15 PM daylight time on 15 July the sun over Hollis stands 45
  degrees high at bearing 260 (10 degrees south of due west): it shines down Jamaica Avenue from the west end, and the
  El's ties stripe the roadway across.
- Rotation: in Cycles, column u = 0.5 of an unrotated equirectangular sky faces +X and u = 0.25 faces +Y. With a
  Mapping node in front of the Environment Texture, the key light ends up at world azimuth
  `measured.sun_azimuth_unrotated_deg` minus the node's Z rotation (azimuth counter-clockwise from +X = east). The
  table gives the rotation that puts each sun at the design position (azimuth 190).
- The skies are not on a common absolute scale (the night skies are exposed up by the publisher). `ev_for_grey_card`
  is the exposure shift at which an 18 % grey card lying flat renders at 18 %: use it to normalise, then set absolute
  brightness in the engine.
- The street panoramas contain other cities: use them for reflections and look development, never as a backdrop.

## Props

The models are kept exactly as downloaded; another step re-exports them. What each needs to meet the conventions
(metres, Z up, forward = +X, pivot at the centre of the footprint on the ground) is in its `fix`, and the numbers
behind it are in `measured`: bounding box in Blender axes after glTF import, the offset from the model's origin to its
footprint centre (`pivot_to_footprint_centre_m`), triangle count, textures, and for kits and multi-variant files the
box of every node. All are in metres already except `steel_frame_shelves_01`, whose mesh is ten times too large.

## Preview pictures

| Picture | What it shows |
|---|---|
| `art/previews/scans_sheet_1.jpg` to `scans_sheet_SHEETS.jpg` | Every tiling set on a 4 m x 4 m ground or wall panel at its catalogue size, with a 1.8 m grey box and a 1 m stick (decimetre bands; the last decimetre is in centimetres). Inset: straight-on view 0.4 m wide at the stick's centimetre end. |
| `art/previews/scans_models.jpg` | All 40 props at real size beside the same box and stick. `scans_models_detail_1.jpg` and `_2.jpg` are the same cells, larger. Red arrow +X, green arrow +Y, magenta block at the model's own origin. |
| `art/previews/scans_skies.jpg` | A chrome and an 18 % grey sphere under each sky, each exposed by its `ev_for_grey_card`. |

Lighting for surfaces and props is `kloofendal_43d_clear_puresky`, view transform Standard, exposed so that an 18 % card
lying flat renders at 18 %: a surface that looks dark there is dark.

## What is missing

Probed on the host and not there, or there but not right for New York. These have to be made procedurally, modelled, or
photographed.

GAPS

## Looked at and left out

`sets.json` lists under `not_used` every texture and model that exists on the host and was looked at but not taken,
with the reason (wrong region, duplicate of a set that is in, too few courses per tile to hide the repeat, and so on).
`probes.json` lists every slug that was asked for and is not on the host.
