# MURDER INC. — art bible for the Unreal rebuild

The look of the Unreal Engine 5 version, in numbers an artist can build to and an art director can tick off.
Client brief: "much better graphics and textures, realistic next-gen graphics".

**What stays** (the web game is ground truth): the place, the layout, the fiction, every name and line of copy, and
the gameplay silhouettes (what is cover, how high, how wide). **What changes**: the stylised low-poly, canvas-painted
look is replaced by photoreal, physically based rendering (Lumen, Nanite, virtual shadow maps).

Read with:

- `docs/DESIGN.md`: what the game is. Section 8 (daylight) wins over sections 1, 2, 5 and 6.
- `docs/unreal/spec/*.md`: mechanics and exact part dimensions (weapons, arms, enemies). Their sections 5 are the
  asset briefs; this document is the look those assets must share.
- `art/scans/sets.json` (scanned surface library), `art/blender/build.py` (Blender pipeline), `art/out/manifest.json`
  (what has been built).

**Precedence.** Layout, dimensions that affect play, names and copy: the web game wins. Colour, material, light,
construction detail and finish: this document wins. The web game's material colours (`src/config/catalog.js`) were
tuned for a night scene and a low-poly style; do not copy them (its asphalt is 1 % reflective, real asphalt is 10 %).

**Status of the numbers.** *(game)* comes from the web game and is fixed. *(measured)* is physics or a real-world
standard. *(chosen)* is art direction and can be tuned by the art lead. Engine settings are targets: this document
was written without an Unreal Editor or a GPU, so every engine value must be confirmed in the editor against the
calibration checks in 2.12.

Contents: 0 conventions · 1 the target · 2 lighting · 3 materials · 4 modelling · 5 signage and branding ·
6 characters, weapons, vehicles · 7 effects and audio · 8 priorities and definition of done · 9 performance ·
10 open questions · 11 sources.

---------------------------------------------------------------------------------------------------

## 0. Conventions every artist needs (fixed, shared with the pipeline)

| Topic | Rule |
|---|---|
| Units | Blender: metres, Z up, east = +X, north = +Y. Unreal: centimetres, Z up, X = east, Y = south. |
| Conversion | Blender(x, y, z) = (x_web, −z_web, y_web). Unreal(X, Y, Z) = (x_web, z_web, y_web) × 100 = (x_bl, −y_bl, z_bl) × 100. |
| Orientation | Give directions as vectors or as an Unreal yaw: 0° faces +X (east), +90° faces +Y (south). |
| Forward | Props, vehicles, weapons: forward = +X. Characters face −Y in Blender. |
| Pivots | Props: centre of the footprint, on the ground. Wall and facade modules: bottom-left corner of the outer face, running along +X, outer face looking toward −Y (Blender). |
| Meshes | `SM_<Family>_<Name>[_<Variant>]`, skeletal `SK_<Name>`. |
| Tiling sets | `TS_<Surface>_<Variant>`, material slot `MI_<Surface>_<Variant>`. Scanned sets are `TS_<Surface>_Scan<Variant>`. |
| Unique sets | Named after the asset, material slot `M_<Asset>`. |
| Textures | `T_<Set>_BC` (sRGB base colour), `T_<Set>_N` (tangent normal, OpenGL), `T_<Set>_ORM` (R ambient occlusion, G roughness, B metallic, linear), optional `T_<Set>_H` (height), `T_<Set>_E` (emissive). |
| Wear masks | Colour attribute `Wear`, exported as `COLOR_0`, linear (see 3.3). |
| Places | Unreal project `unreal/MurderInc/`, runtime data `unreal/MurderInc/Content/Data/*.json`, Blender pipeline `art/blender/`, generated art `art/out/` (ignored by git), previews `art/previews/`, port documents `docs/unreal/`. |

The block in numbers *(game, `src/level/layout.js`)*: play area 92 × 68 m. Roadway 14 m wide (two travel lanes, two
2.4 m parking lanes), kerbs 0.15 m, sidewalks 4 m, building lines 22 m apart. Storefront storey 3.8 m, upper storeys
3.1 m. Buildings 6.9 m (two storeys) to 16.2 m (five). El: column pairs every 10 m, rows 9.2 m apart, clear height
5.3 m under the cross girders, deck underside 6.5 m, rail top 6.83 m, deck 10.8 m wide.

---------------------------------------------------------------------------------------------------

## 1. The target in one page

### 1.1 One sentence

A frame of the game should pass for a photograph taken on a hot weekday afternoon under an elevated train line in
eastern Queens: full-frame camera, 16 to 35 mm lens, f/8, exposed so the shade under the steel is readable. The place
is invented. Everything in it could be measured with a tape.

### 1.2 What "photoreal" means here: five tests

1. **Measured.** Every size is a real size (section 4), every base colour is inside its measured range (section 3),
   every light is in lux, candela or nits (section 2).
2. **Continuous.** There is detail at 10 m (silhouette), 1 m (construction), 10 cm (fixings, joints, damage),
   1 cm (grain, chips) and 1 mm (pores, scratches). A surface with a scale missing reads as a model.
3. **Caused.** Every stain, chip and streak has a source you can point at: a leaking bracket, a kerb that tyres
   climb, a doorway where people stand.
4. **Imperfect.** Nothing is straight, plumb, flush or identical. Builders, weather and sixty years did this, not
   a modelling tool.
5. **Photographed.** Exposure, tone curve, white balance and lens behave like a camera (section 2). No effect is
   there because it is available.

### 1.3 The place, element by element

| Element | What it is in the real borough | Details that must be there |
|---|---|---|
| **The El** | A steel elevated railway of the 1915–1918 kind (as over Jamaica Avenue in Woodhaven, Roosevelt Avenue, 31st Street, Jerome Avenue). Two-column bents standing in the roadway at the parking-lane line. | Built-up riveted H columns (web plate, four angles, cover plates) on a flared riveted base and a scarred concrete pedestal. A plate-girder cross girder with vertical angle stiffeners every metre and knee braces to the columns. Plate-girder longitudinal spans, a stringer under each rail, a fascia girder on short brackets. Lateral bracing: single angles in a zigzag or X with gusset plates, lacing bars on the built-up struts. Open deck: timber ties straight on the steel with sky between them, running rails, guard timbers, a third rail under a cover board, plank walkways, pipe handrail. Hung on it: lamps, conduit, clamped signals and street signs, pigeon spikes, stencilled column numbers. |
| **Brick tenements, 2 to 5 storeys** | Walk-ups of 1900–1930 on 6 to 7.6 m lots, joined in a row, flat roofs behind parapets. | Street front in face brick, running bond, thin joints. Stone or cast-stone sills and lintels. A pressed sheet-metal cornice on brackets, or the scar where one was removed. Black fire escapes with slatted balconies, drop ladders and a gooseneck to the roof. One-over-one aluminium replacement windows, child guards on the lower half, air conditioners on brackets with drip stains beneath. Side walls in rougher common brick with a header course every sixth course, blind or with a few lot-line windows, carrying painted adverts and the ghost of a demolished neighbour. Roofs: bitumen or silver coating, stair bulkheads, wooden water tanks on steel dunnage, vents, dishes. |
| **Taxpayer strips** | One- or two-storey commercial rows put up cheaply to earn the land tax: a line of shop bays under a continuous sign band and a low parapet. | Aluminium storefront framing, a bulkhead of tile, brick or metal panel, plate glass, a recessed tiled entry, a 0.91 m door with a transom. Roll-down gate in side guides with its hood under the sign band. An awning. Conduit, junction boxes, a through-the-transom air conditioner dripping on the sidewalk, a steel cellar hatch in the sidewalk, a standpipe connection, stickers and handbills. |
| **Cinder-block auto body shop** | A 1950s–70s single-storey block garage, 6 m to the eave. | Painted block in two tones with a dark dado, steel lintels with rust bleeding below them, a 6 m sectional steel door, yellow concrete-filled pipe bollards (chipped, leaning) at the jambs, a steel man-door with wired glass, hand-painted service lists, exhaust fans. Roof of steel joists with wired-glass skylights. An oil-black apron with tyre stacks and drums. |
| **Chain-link ball court** | A city playground court. | 4 m galvanised chain-link (50 mm mesh) on pipe posts every 3 m in a 0.5 m concrete knee wall, top rails bent, mesh bulged and patched. Asphalt under a worn acrylic colour coat. Steel backboards on gooseneck posts, chain nets or none. Aluminium bleachers. Flood lights on 9 m poles. |
| **Attended parking lot** | An asphalt lot behind a low wall. | A prefabricated attendant booth with a sliding window, a rate board and a window air conditioner. Faded stall lines, wheel stops, an oil spot in every bay, weeds in the cracks, light poles, a pole sign, a barrier arm, a billboard on a steel frame over the corner. |
| **The street's working clutter** | What a repair job and a shopping street leave on the sidewalks: the game's hard cover and sightline breaks. | A sidewalk shed of scaffold tube and hunter-green plywood with caged bulbs underneath. Rolling repair scaffolds in orange debris netting, a hoist tower, a plywood site shanty. Shut sheet-steel news kiosks, a tyre cage, a produce stand under a tarp. A utility dig behind barriers with a striped steam stack. Parked cars, cabs, a van, a box truck, a food cart, refuse sacks, mailboxes, a bus shelter. |

### 1.4 Period: present day, in layers

The block is a 2020s photograph of things built at different times. Keep the layers visible.

| Layer | Built | Shows as |
|---|---|---|
| Steel | 1917 | Rivets, many coats of paint, rust jacking between plates. |
| Brick | 1900–1930 | Soot-darkened masonry, repointed patches, cornices lost. |
| Shop fronts and signs | 1950s–1990s | Neon, fluorescent cabinets, hand-painted fascias, old solid roll gates. |
| Street kit | 2010s–2020s | LED street lamps, security cameras, window air conditioners, delivery mopeds, perforated or open-grille roll gates beside the old solid ones, wheeled waste bins beside the bag piles, QR codes on posters (they must not resolve to anything, see 5.7). |

Summer, about 33 °C, no rain for days: dust, dry gutters, heat shimmer. The only water is the open hydrant.

### 1.5 Where reference comes from

Collect real photographs, at least thirty per hero view (2.11), and keep them outside the repository (they are other
people's work). Useful search terms: Jamaica Avenue under the elevated in Woodhaven and Richmond Hill (the closest
real match to the whole block); Roosevelt Avenue in Jackson Heights (signage density); Jerome Avenue in the Bronx
(auto shops under an el); Broadway in Bushwick (older lattice steel); Hollis and Queens Village side streets
(taxpayer rows, garages, vacant lots). Reference is for construction, wear and light. Never reproduce a real shop
name, logo or person from it.

### 1.6 What to avoid

| The tell | Why it reads as a game | Do instead |
|---|---|---|
| Game-clean surfaces | New things are rare on this block. | Every surface carries at least two kinds of history (for example soot and repointing, or chips and overpaint). |
| Uniform noise | Grunge at the same strength everywhere is as false as none. | Wear has a place and a cause (3.5). Leave clean areas: under awnings, behind signs, where rain washes. |
| Pure colours | Paint, plastic and print are never a pure hue. | No base colour channel at 0 or 255. Nothing darker than sRGB 30, nothing brighter than sRGB 240 (3.1). |
| Repetition | The eye finds the second copy at once. | No two identical instances within 10 m without a rotation, a variant or a different wear mask. A tiling set must cross a 20 m wall with no visible repeat (macro variation, 3.2). |
| Perfect geometry | Razor edges and ruler-straight lines. | Bevel everything (4.2). Give long things their sag, lean and dents (4.4). |
| Floating and intersecting | Objects placed, not standing. | Contact shadow, a dirt line at every base, a stain where a thing has stood for years. No mesh passes through another. |
| Dead glass | Flat dark or mirror rectangles. | Reflection with slight waviness, a dirty film, and something behind it: a room, a blind, a display (3.4 glass). |
| Glow without a lamp | Emissive rectangles with no construction. | Every light has a fixture, a wire and a mounting (section 5). |
| The web palette by day | Near-black asphalt and brick kill the bounce light. | Use the ranges in section 3. |
| Over-grading | Heavy vignette, grain, teal-and-orange, crushed blacks. | The grade in 2.4 and 2.8. Day is bright, punchy and natural. |
| Derelict or dystopian dressing | This is a working block on a normal day, emptied by a road closure. | Shops are in business. Litter is a day's worth, not a decade's. |

### 1.7 Ten rules, if you read nothing else

1. Build to the tape measure: the dimensions in 4.1, and the catalogue box and cover height of every prop.
2. Base colour inside the measured range; nothing near black, nothing pure (3.1). The web game's hex values are
   intent, not albedo.
3. Metallic is 0 or 1. Roughness always varies, and for a reason.
4. Patterns are real size: a brick course is 67.7 mm, a sidewalk flag 1.5 m, a rivet head 36 mm.
5. Every edge is bevelled; anything deeper than 5 mm is geometry (4.2, 4.3).
6. Wear has a cause and a place. Paint the `Wear` mask from causes, then tell one specific story (3.3, 3.5).
7. Nothing is straight, level or identical (4.4).
8. Every light is a fixture with a wire; every sign is a built object (2.6, 5.2).
9. No real brand, mark, face or scannable code. IPX is "IPX" and "IPX.EXCHANGE" only (5.7).
10. Judge it in the two lighting rigs, at 0.5 m and at 40 m, beside a 1.8 m figure, against a real photograph.

---------------------------------------------------------------------------------------------------

## 2. Lighting

Two lighting scenarios, chosen between runs by the `time` setting. There is no moving time of day.

- **DAY** (default, gets the polish): a hot, clear summer afternoon, "4:15 PM".
- **NIGHT** (alternate): "02:14 AM", sodium and neon, the street hosed down.

Geometry and materials are shared. Each scenario is a rig (a sub-level or data layer) that owns the lights, sky,
fog and post-process volume and sets three global material values: the signage emissive scale (2.7), the street
wetness (2.9) and whether windows are lit.

### 2.1 DAY, physically

| Quantity | Target | Status |
|---|---|---|
| Sun elevation | 52° | game |
| Sun azimuth | 244° on the game compass (from the west-south-west) | game |
| Light travels toward | web (0.553, −0.788, −0.271) · Blender (0.553, 0.271, −0.788) · Unreal (0.553, −0.271, −0.788) | game |
| Unreal rotation of the sun light | Pitch −52.0°, Yaw −26.1°, Roll 0° | derived |
| Sun disc | 0.53° across: an edge 1 m above a surface casts a soft edge about 12 mm wide (15 mm measured along the ground) | measured |
| Direct sun, facing it | 90,000 lx (accept 80,000 to 98,000) | measured |
| Sun on the road | 71,000 lx | derived |
| Sky on open ground | 15,000 to 20,000 lx, blue | measured |
| Sun to sky ratio on open ground | about 4.5 : 1 | derived |
| Sun colour at street level | 5,300 to 5,600 K (a little warm) | measured |
| Sky colour | 9,000 to 12,000 K overhead, paler and warmer at the horizon | measured |
| Sky luminance | zenith 2,000 to 4,000 nits, horizon 6,000 to 10,000, sunlit cumulus 10,000 to 25,000 | measured |
| Clouds | a few bright cumulus, 15 to 25 % cover, never over the sun | chosen |
| Haze | visibility 5 to 8 km: a 7 to 11 % veil at the far end of the avenue (150 m), 40 to 80 % on a skyline 1 to 2 km away | chosen |

**Why this sun.** It is the web game's sun, and the shadow layout it makes is level design: which fronts are lit,
where the stripes fall, where the deep shade is. It also puts the sun behind the player, who starts in the west and
works east: enemies ahead are front-lit and readable, and looking back west gives the backlit view of the El in
haze. For the record: a real mid-July sun over Queens at 4:15 PM daylight time stands near 45° elevation, azimuth
260°. The game's sun matches a real sun at about 3:20 PM in early August. Nobody can tell from a photograph; do not
"correct" it. (The Blender look-dev rig defaults to 45° / 235°, which is fine for judging a single asset. To judge
a view of the block, call `render.rig_day(sun_elevation=52, sun_azimuth=244)`.)

### 2.2 Who is lit: the shadow map of the block (DAY)

A point at height h throws its shadow 0.78 h away: 0.70 h to the east and 0.34 h to the north.

```
 Section across the avenue, looking east. North is on the left. The sun is behind you, to the right.
 In this section the rays come down at 71 degrees, from the south (right) to the north (left).

  N1 16.2 m                                                              S1/S2 10-13 m
   |                                                                        |
   | lit, raking 74 deg     +---------- deck, 10.8 m wide -----------+      | in shade
   | off the wall normal    |  ties / rails         ties / rails     | 6.5  |
   |                        +----+----------------------------+------+      |
   |                             | column              column |             |
 --+----------+------------------+----------------------------+-------+-----+--
  -11        -7                 -4.6           0             4.6      7     11     z (m)
    sidewalk  |<------- deck shadow, z = -7.6 ... +3.2 ------->| sun  | shade of
    in SUN    |   ladder of light through the tie gaps         | strip| the south
              |                                                | 3.8 m| fronts
```

- **North-side fronts** (deli, alley mouth, V&R Auto Body, the tenement) are sunlit at 74° off the wall normal:
  about 24,000 lx of sun, raking hard across every brick course, plus sky and bounce. This is the texture showcase.
- **North sidewalk** is in full sun (3.4 m of it; the deck shadow starts 0.6 m in from the kerb).
- **Under the deck**: shade over the northern three quarters of the roadway (z −7.6 to +3.2 m). About 38 % of the
  sun passes the open tie zones: two bands of soft-edged bars of light, each band 2.7 m wide, bars about 0.2 m wide
  every 0.56 m, edges about 9 cm soft. Rails, stringers and walkways draw long lines through it.
- **South strip of the roadway** (z +3.2 to +7 m): full sun on the south parking lane.
- **South sidewalk and south fronts**: open shade. A 10 m building shades 3.4 m of sidewalk, a 13 m one all of it.
  The two-storey S3 row would leave its kerb edge in sun, but the sidewalk shed covers it.
- **West-facing walls** (the deli's alley wall, the S3 wall on the vacant lot): sunlit at 56° off the normal, about
  50,000 lx. Both are side walls, so both are common brick (4.8). **East-facing walls** (the mural) are in open
  shade.
- **The alley**: floor in shade (the shop parapet shadows 4.8 m of its 5 m), east wall fully sunlit. A canyon lit
  by bounced, orange-red light.
- **The vacant lot**: western 9 m in the shadow of the pawn building, eastern strip in sun. The mural is lit by
  the sky and by the sunlit brick wall opposite.
- **The Cage and the parking lot**: open, full sun. The hard, simple light of a ball court at 4 PM.

Illuminance and exposure by place (what a meter reads; the card column is an 18 % grey card lying flat):

| Place | Illuminance | Grey card | Relative to the sunlit card |
|---|---|---|---|
| Sunlit road, lot, court | 88,000 lx | 5,000 nits | 0 |
| Sunlit north front (card on the wall) | 37,000 to 44,000 lx | 2,100 to 2,500 nits | −1.1 stops |
| Open shade, south sidewalk | 8,000 to 12,000 lx | 460 to 690 nits | −3 stops |
| Under the El, in shade | 3,000 to 8,000 lx | 170 to 460 nits | −3.5 to −4.9 stops |
| Under the sidewalk shed | 1,000 to 3,000 lx | 60 to 170 nits | −5 to −6.4 stops |
| Shop interior | 1,000 to 5,000 lx (see 2.5) | 60 to 290 nits | −4 to −6.4 stops |

**Bounce.** Fill light under the El is almost all bounce, so it is only right if the albedos are right.

| Sunlit surface | Albedo | Light it gives back | Colour of the fill |
|---|---|---|---|
| Concrete sidewalk | 0.26 to 0.41 | about 30,000 lm/m² | warm white: the main fill for shop fronts and for anyone under the deck facing north |
| Tan brick front, raking sun | 0.26 to 0.42 | 10,000 to 17,000 lm/m² | pale warm: lifts the north sidewalk in front of the deli |
| Common brick, west-facing | 0.11 to 0.21 | 6,500 to 12,500 lm/m² | strong orange-red: the alley glows with it; it fills the mural and the vacant lot |
| Asphalt | 0.07 to 0.13 | about 9,000 lm/m² | weak, neutral |
| Red face-brick front, raking sun | 0.06 to 0.11 | 2,000 to 5,000 lm/m² | faint warm |

The shade under the deck is neutral to slightly warm (bounce) and the open shade of the south sidewalk is blue
(sky). Keep that difference: it is what a camera records.

If the measured shade under the deck is below 3,000 lx, or play-tests as too dark, add a soft unshadowed fill of
up to 2,000 lx under the deck (a cinematographer's bounce board) before opening the exposure any further.

### 2.3 DAY exposure and the tone of the picture

The contrast between sun and the shade under the steel is three and a half to five stops. A single film exposure
would give black shade or burnt sun. The reference is a current camera or phone with moderate local tone mapping: shade
opened, highlights held, colour natural.

| Setting | Target (chosen) |
|---|---|
| Exposure outdoors | Auto exposure clamped to EV100 13.0 to 14.5. In open sun it sits near 14.2 (about half a stop more open than the "sunny 16" rule). Under the El it opens to about 13.2. The lower clamp is the main readability dial: try 12.7 to 13.2. |
| Local exposure | Highlight contrast 0.75 to 0.85, shadow contrast 0.70 to 0.85, detail strength 1.0. Enough to read a black hoodie in the shade, not enough to look like HDR photography. |
| White balance | 6,200 to 6,500 K. Sun reads slightly warm, open shade blue. |
| Tone curve | Unreal's default filmic curve. Contrast 1.03 to 1.05, saturation 1.03 to 1.06. |
| Bloom | Intensity 0.25 to 0.35, no threshold: only the sun, glints on chrome and glass, muzzle flashes. |
| Vignette, grain, aberration | Vignette 0.15 to 0.2, grain 0 to 0.1, chromatic aberration 0. |
| Lens flare | Off, or 0.1 when looking west into the sun. |
| Motion blur | 0.3 at most, per object (train, rotors). An option to switch it off. |
| Depth of field | None in play. Aiming blurs only what is closer than the rear sight. Hero stills: f/5.6 to f/8. |

### 2.4 DAY in Unreal: what to aim for

| Component | Aim |
|---|---|
| Directional light "Sun" | Rotation as in 2.1. Intensity tuned until a card facing the sun reads 90,000 lx at street level (start at 110,000 to 120,000 lux when the sky atmosphere attenuates it; measure, do not trust the number typed). Source angle 0.5357°. White light: let the atmosphere warm it (if it does not, 5,500 K). Atmosphere sun light on. Casts volumetric shadow. |
| Sky atmosphere | Earth defaults with the aerosol (Mie) scattering raised two to three times for humid summer air. Tune aerial perspective until a black object at 150 m shows about 10 % of the horizon colour. |
| Sky light | Real-time capture, intensity scale 1, no tint. The sky must be the one the player sees. |
| Clouds | Volumetric cloud at low cover on High and Epic, a painted dome on Low and Medium. Cloud shadows never cross the block. |
| Height fog | Volumetric fog on (the shafts through the ties and the shop skylights are the point), forward scattering 0.6 to 0.75, density low. No fog colour of its own: the atmosphere supplies it. |
| Global illumination | Lumen. Hardware ray tracing where the card supports it, because distance fields lose thin steel: the tie deck, lattice bracing, fire escapes and fences (see 4.7 for what the meshes must provide). Final gather quality 1 (High) to 2 (Epic): the noisy place is the shade under the El. Lumen scene detail 2 so street props enter the Lumen scene. |
| Reflections | Lumen. Hit lighting on Epic. High-quality translucency reflections on High and above (shop glass, car glass). |
| Shadows | Virtual shadow maps. Every tie, rail, lattice bar and fire-escape slat casts. Contact hardening must be visible: sharp at the foot of a column, 10 cm soft from the deck. |
| Anti-aliasing | TSR. Chain-link, wires and lattice are the test (4.7). |
| Emissive | Signs at their physical luminance (2.7). Windows are not emissive by day. Street lamps off. |

Project switches this look depends on. The project's configuration is authoritative
(`docs/unreal/spec/00-unreal-scout.md` 2.2 lists the full file); these are the ones the art assumes:

```
r.DynamicGlobalIlluminationMethod=1   ; Lumen global illumination
r.ReflectionMethod=1                  ; Lumen reflections
r.Shadow.Virtual.Enable=1             ; virtual shadow maps
r.Nanite.ProjectEnabled=True
r.GenerateMeshDistanceFields=True     ; software Lumen, distance-field occlusion on Low
r.RayTracing=True                     ; lets Lumen use hardware ray tracing
r.Lumen.HardwareRayTracing=True
r.AntiAliasingMethod=4                ; TSR
r.AllowStaticLighting=False           ; nothing is baked: both scenarios are fully dynamic
r.VirtualTextures=True                ; the mural and other very large unique textures
```

### 2.5 The shop interior (both scenarios)

A body shop is a bright workplace, and play goes in and out of its doors, so light it generously.

- **By day**: four skylights throw real sun patches (40,000 lx and more) on the floor with shafts in the dust; the
  roll door admits sky and the bounce of the sunlit apron; rows of LED strips and the four work lights of the
  level data bring the floor to 1,000 to 1,500 lx in the depth of the room. Interior exposure volume: EV100 9.5 to
  11.
- **By night**: the same electric light alone, 500 to 800 lx, work lights warm (3,000 to 3,500 K), strips neutral
  (4,000 K). Interior exposure volume: EV100 6.5 to 8.
- **The doorway test** (gameplay, both ways, both scenarios): standing on the avenue, a Goon 6 m inside the roll
  door must separate from the background by his pale mask, his sneakers and his outline; standing inside, a Goon
  on the sunlit sidewalk must not burn out. Solve it with real light inside, a light-coloured floor, local
  exposure and centre-weighted metering, not by flattening the exposure of the whole game.
- The oil-sealed floor is glossier than the street (roughness 0.35 to 0.6): it mirrors the skylights and the doors.

### 2.6 NIGHT, physically

The El lamps are still high-pressure sodium: that orange is the block's night identity *(chosen; the real borough
is now mostly 3,000 to 4,000 K LED, so the kerb poles are LED)*. The web game's steep "street light" directional
light is not ported: in Unreal the lamps are real lights with real shadows. Lamp positions and kinds come from the
exported level data; this table gives each kind its photometry.

| Kind in the level data | Real fixture | Output | Colour | Unreal light | Intensity toward the ground | Result |
|---|---|---|---|---|---|---|
| `el` | sodium lamp hung under the deck at 5.5 m, one per bay, staggered over the lanes | 8,000 to 9,500 lm | 2,100 K | spot, outer cone 76°, inner 25°, source radius 12 cm | 1,800 cd | 60 lx beneath, 5 to 8 lx between: the pools that make the avenue |
| `street` | LED cobra head on a kerb pole at 7.7 m | 10,000 to 12,000 lm | 3,000 K | spot or a type III IES profile, source 15 × 40 cm | 3,000 cd | about 50 lx at the foot |
| `flood` (court) | two floods on 9 m poles | 40,000 to 60,000 lm each | 4,000 to 5,000 K | spot, outer cone 52°, inner 37° | 12,000 to 15,000 cd each | 100 to 200 lx on the court, hard double shadows |
| `flood` (billboard, lot) | four arm lamps under the billboard face; two poles in the lot | 10,000 lm each; 15,000 lm each | 4,000 K | rect lights on the face; spots on the poles | to give 300 to 500 lx on the face, 10 to 30 lx in the lot | a legible white board; a dim lot |
| `work` (shop) | four caged work lights plus rows of strips | 20,000 lm each plus strips | 3,000 to 3,500 K; strips 4,000 K | spots, outer cone 76°; rect lights for the strips | to give 500 to 800 lx on the floor | the brightest room on the block |
| `neon` | see 2.7 | 250 to 1,000 lm per metre of tube | sign colour | one rect light per sign, the size of the sign | physical | coloured spill on wall, sidewalk and wet road |
| `window` (lit shop) | fluorescent or LED interior | 10,000 to 30,000 lm leaving through the glass | 4,000 to 5,000 K (laundromat, deli), 3,000 K (pizza, chicken) | a rect light inside, facing out | physical | 100 to 300 lx on the sidewalk in front |
| `window` (apartment) | a lit room behind a blind | none worth a light | 2,700 K | emissive only | 20 to 150 nits | warm rectangles |
| Sidewalk shed | caged bulbs strung under the deck every 2 to 3 m *(game)* | 800 to 1,500 lm each | 2,700 to 3,000 K | point lights, source radius 4 cm | physical | 30 to 80 lx along the S3 fronts, a row of small hard shadows |
| IPX truck (idling) | low beams, hazard flashers every 1.1 s, a lamp over the rear doors | 700 to 1,000 lm per beam | 4,300 K; amber `#FF8A1A` | spots; points | 15,000 cd per beam; 300 cd per flasher | the goal is visible from the avenue |

Night ambient: sky light of 0.6 to 1.0 lx, steel blue *(chosen: several times a real clear city night, for
readability)*. Sky dome: zenith about 0.05 nits, deep blue-black; a sodium-pink glow of 1 to 3 nits over the western
skyline; a dozen stars at most. The moon is low in the east-south-east (17° up, bearing 116°), a sky feature only:
no moon shadows, its disc no more than twice real size.

**Readability rule.** Every place an enemy can stand at night receives at least 2 lx from some lamp, sign or lit
window. Where the level data has no lamp (rear lane, alley, vacant lot), add a practical: a wall pack over a door
(3,000 lm, 4,000 K), a bare bulb in a cage, a lit window. This is light placement, not an exposure trick.

### 2.7 Emissive levels (nits)

Unreal treats emissive as luminance in cd/m². Author emitters at their **physical** luminance. Scene white sits
near 2^EV100 nits: 16,000 to 20,000 nits at the day exposure and 16 to 19 nits at the night exposure (the spread
is the engine's lens-attenuation setting; check 3 in 2.12 settles it). A camera cannot hold a saturated hue much
more than five stops over white, and neither can the tone curve, so at NIGHT the lighting rig scales **all
signage by 0.2** (one material parameter; tune it between 0.1 and 0.25 on hero view H8 until red and cyan tubes
hold their hue and pink and green show only a pale core). The paired lights keep their physical output. Lamps,
windows and headlights are not scaled: a clipped white lamp is what a photograph shows.

`T_<Set>_E` stores the emitter's colour and relative intensity (0 to 1). The luminance in nits is a parameter of
the material instance, taken from this table, and the scenario's signage scale multiplies it.

| Emitter | Physical luminance | DAY in engine | NIGHT in engine | Its light is carried by |
|---|---|---|---|---|
| Neon tube, red | 2,000 to 3,000 | physical: a coloured line in shade, nearly invisible in sun | 400 to 600 | rect light, 250 lm per metre of tube |
| Neon tube, blue or cyan | 3,000 to 4,000 | physical | 600 to 800 | 400 lm/m |
| Neon tube, pink, gold or white | 5,000 to 8,000 | physical | 1,000 to 1,600 | 800 lm/m |
| Neon tube, green | 8,000 to 10,000 | physical | 1,600 to 2,000 | 1,000 lm/m |
| LED "neon" flex | 3,000 to 6,000 | physical | 600 to 1,200 | as neon |
| Lightbox face, white areas | 500 to 1,500 | physical: by day the face is read by reflected daylight | 100 to 300 | rect light the size of the face, 1,500 to 4,500 lm per m² of face (π × its luminance); old fluorescent cabinets sit at the low end |
| Channel-letter faces | 1,000 to 2,500 | physical | 200 to 500 | rect light |
| LED window sign | 3,000 to 6,000 | physical | 600 to 1,200 | none |
| Back-lit awning | 100 to 300 | physical | 100 to 300 (not scaled) | none |
| Apartment window | 20 to 150, warm; a television 5 to 30, bluish, flickering | off: reflective glass | 20 to 150 | none |
| Shop seen through glass | surfaces 30 to 150, visible tubes 5,000 to 8,000 | lit by its real lights | lit by its real lights | its real lights |
| Train windows | 150 to 300 | physical | 150 to 300 | rect lights inside each car (the stripes through the ties) |
| Lamp lenses | 50,000 and up | off | capped at 50,000 | the lamp itself |
| Headlamp, low beam | 100,000 and up | capped at 200,000 | capped at 50,000 | spot light |
| Hazard and turn lamps | 20,000 to 50,000 | physical | scaled by 0.2 | point light |
| Tail lamps, taxi roof light | 500 to 2,000 | physical | physical | none |

Gameplay emitters are authored **relative to scene white**, so they read the same in both scenarios:

| Emitter | Level | Colour |
|---|---|---|
| Player tracer | 8 to 16 × white | `#FFE2A8` |
| Enemy tracer, Buzzard bolt | 8 to 16 × white | `#FF3A22` |
| Muzzle flash core | 30 to 60 × white for one frame | `#FFC880` |
| Master reel beacon | 2 to 4 × white, pulsing | `#F6C21A` |
| Buzzard eye | 4 to 8 × white | `#FF2A1A` |
| Explosion fireball | 20 to 50 × white, falling over 0.5 s | black-body orange to yellow |

By day that makes a tracer brighter than anything real. It is the one place where readability is chosen over the
photograph (DESIGN 8.1: tracers must stay visible against bright walls). The reel's 6 m shaft of gold light and
its glow on the ground *(game)* are kept for the same reason: draw them as a faint column of lit haze, strongest
at night; by day the mast and its emissive lens do the work.

Every neon sign has a backing panel whose emissive map carries a blurred copy of its tubes at 10 to 15 % of the
tube luminance. Thin tubes are too small for Lumen's surface cache; the panel is what bounce light and rough
reflections see.

### 2.8 NIGHT in Unreal: what to aim for

| Component | Aim |
|---|---|
| Exposure | Auto exposure clamped to EV100 3.5 to 5.0 outdoors. A grey card under an El lamp reads about 3.4 nits, between lamps about 0.4. |
| Local exposure | Highlight contrast 0.8, shadow contrast 0.7. |
| White balance | 3,800 to 4,200 K: sodium reads golden orange, 4,000 K LED near neutral, the sky light blue. |
| Lamps | All shadow-casting. With MegaLights (production-ready in Unreal 5.8, beta in 5.7) every lamp in the table casts. Without it: at most 24 shadow-casting local lights near the player and no more than 4 to 6 overlapping on any pixel; the rest fade their shadows by distance. |
| Volumetric fog | On, thin: a soft cone under every lamp on a humid night. On Low the cones are cards. |
| Reflections | Lumen with hit lighting where available. Wet asphalt and puddles are the showpiece. |
| Bloom | 0.5 to 0.7. Convolution bloom on Epic only. |
| Vignette, grain, aberration | Vignette 0.3 to 0.35, grain 0.2 to 0.3, chromatic aberration 0.15 at most. |
| Saturation, contrast | 1.05 to 1.08, 1.05. |

### 2.9 Wet street

- **DAY**: dry, except inside the open hydrant's reach (about 4 m) and along the gutter down to the catch basin.
  The wet patch is the one mirror on the avenue: it reflects the deck and the sky slots.
- **NIGHT**: the whole avenue is damp and the low spots hold water.

| State | Base colour | Roughness | Normal |
|---|---|---|---|
| Dry asphalt | as authored | 0.75 to 0.95 | as authored |
| Damp (film broken by the aggregate) | × 0.6 to 0.7 | 0.3 to 0.5 | as authored |
| Standing water | dirty water over the surface, × 0.5 | 0.03 to 0.06 | flat, with slow ripples from drips and from the train |
| Wet steel, paint, glass | unchanged | film at 0.1 to 0.2 with beads | beads and runs |

Porous things darken when wet (asphalt, concrete, brick, timber, cardboard, cloth); sealed things do not. Water
collects where the `Wear` alpha says it does on ground meshes (3.3): gutters, ruts, the dip at a catch basin.
Reflections of neon on damp asphalt are long vertical streaks. Do not fake them; roughness 0.3 to 0.5 makes them.

### 2.10 Mood words

- **DAY**: hot, loud, bright, hard-edged, ordinary, lived-in, sun-bleached, striped, dusty. A busy block holding its
  breath.
- **NIGHT**: humid, sodium, hosed-down, neon, humming, steaming, empty at 2 AM.
- **Never**: apocalyptic, derelict, cyberpunk, desaturated military, noir pastiche, crunchy HDR.

### 2.11 Hero views: eight frames that must look like photographs

Positions are the camera. Web coordinates in metres (x east, y up, z south), then Unreal centimetres. Yaw is
Unreal's (0° east, +90° south). FOV is vertical, at 16:9. Each view has a reference board of real photographs and
is signed off against it. The gameplay camera is wider (74° vertical, a 16 mm lens): every view must also hold at
that width with the weapon in frame. The level spec lists 37 reference cameras of the web game
(`docs/unreal/spec/05-level.md` 5.4): those must be matched for content; these eight must reach photograph quality.

| # | View | Scenario | Camera (web m) | Camera (Unreal cm) | Yaw, pitch | FOV | What must read |
|---|---|---|---|---|---|---|---|
| H1 | Under the El, looking east | DAY | (−38.0, 1.68, 1.5) | (−3800, 150, 168) | −2°, +4° | 50° | Columns receding every 10 m, the ladder of light on the asphalt, rivets, the deck against the sky slots, Rule's black SUV at the kerb, shop fronts both sides, haze at the roadblock. |
| H2 | The north fronts in raking sun | DAY | (20.0, 1.83, −7.6) | (2000, −760, 183) | −168°, +6° | 40° | The deli cabinet sign and green awning, brick relief in grazing light, awning shadows, a cellar hatch, the alley mouth glowing orange-red, V&R's roll door, the painted wall advert, a fire escape. |
| H3 | Inside V&R Auto Body | DAY | (−12.0, 1.68, −12.6) | (−1200, −1260, 168) | −120°, +2° | 55° | Sun shafts from the skylights in dust, a car on the lift, the floor mirroring the skylights, tool chests, tyre stacks, the glass-fronted mezzanine office, work lights on. |
| H4 | The Cage through the fence | DAY | (31.0, 1.83, −10.4) | (3100, −1040, 183) | −78°, 0° | 45° | Galvanised mesh sharp in the foreground, its shadow resolving only at the base, worn court paint, hoops, bleachers, the reel case at centre court, flood poles, brick beyond. |
| H5 | The lot, the billboard, the truck | DAY | (27.0, 1.68, 30.0) | (2700, 3000, 168) | −35°, +5° | 40° | The black IPX truck with its gold band mirroring the sky, the billboard on its steel frame in raking sun, rows of parked cars, the booth, heat shimmer, the El and a train beyond. |
| H6 | The vacant lot and the mural | DAY | (−6.0, 1.68, 19.0) | (−600, 1900, 168) | 180°, +10° | 55° | The mural painted over brick (courses showing through the paint), "RULE" in gold, soft sky light with a warm fill from the wall opposite, the burned car, mattress, carts, weeds, the fence. |
| H7 | A train overhead, from the sidewalk shed | DAY | (3.0, 4.63, 8.6) | (300, 860, 463) | −20°, +10° | 55° | Stainless cars in sun, trucks and wheels through the steel, an arc at the third rail, grit falling, pigeons breaking, the ladder of light on the avenue going dark. |
| H8 | The avenue at night | NIGHT | (−9.0, 1.68, 3.5) | (−900, 350, 168) | −4°, +2° | 50° | Sodium pools under the deck, red, pink and cyan in the wet road, the lit deli, the string of caged bulbs under the shed, steam at a manhole, the yellow cab, warm windows, the reel's gold beacon. |

Plus **the first-person frame**: the CHOPPER at the hip under the El, half in a bar of sun. The gun and gloves fill
40 to 45 % of the frame width (DESIGN 8.2) and are the most looked-at pixels in the game. It must hold as a
close-up photograph of a real firearm and real gloves.

### 2.12 Calibration checks (run before judging any asset in the engine)

1. A white card facing the sun at street level reads 90,000 lx ± 10 %; an 18 % card flat on the sunlit road reads
   about 5,000 nits (Unreal's HDR eye-adaptation view reports luminance and EV100).
2. The same card in the shade under the El reads 170 to 460 nits; in open shade 460 to 690 nits.
3. With exposure fixed at EV100 14, an emissive quad of 16,000 nits renders as a bright white just under clipping
   (scene value about 1); at EV100 4 a quad of 16 nits does the same. If it renders far darker or burns out, the
   emissive units or the exposure calibration are not what this document assumes: fix that before anything else.
4. A grey ball (albedo 0.18, roughness 0.5), a chrome ball and a 24-patch colour chart stand at the start
   position in both scenarios. Screenshots of them are kept in `art/previews/` and compared with the same props in
   the Blender look-dev rig (`art/blender/mi/render.py`, AgX, sunlit card at middle grey).
5. Sun to shade under the El measures three and a half to five stops with a spot meter. On screen, after the
   exposure has adapted and local exposure has done its work, it looks like two and a half to three.

---------------------------------------------------------------------------------------------------

## 3. Material bible

### 3.1 Rules for every material

| Rule | Value |
|---|---|
| Darkest base colour | Measured as luminance: grey level sRGB 30 (linear 0.013) for gloss black car paint only; sRGB 40 (0.021) for everything else: black enamel, tyres, black cloth, black plastic. A saturated colour may have one channel below this, never at 0. |
| Brightest base colour | sRGB 240 (0.87). Typical "white" things are 0.6 to 0.78: white paint, tile, paper, the pale mask. |
| Metallic | 0 or 1, in between only inside a texel where both meet. Paint, rust, dirt, oxide and anodising are non-metal. Metallic is 1 only where bare metal shows. |
| Bare metal base colour | iron and steel `#C5C7C8`, chromium `#C4C5C4`, aluminium `#F5F6F6`, stainless `#C8CACC`, nickel `#D4CDC0`, brass `#F2E6B0`, copper `#FAD1C2`, gold `#FFE39D`. Galvanising is duller than pure zinc: see its row in 3.4. |
| Specular | Leave at the engine default (F0 0.04) for non-metals. Water 0.02. |
| Roughness | No constant roughness. Every roughness map spans at least 0.15 within any square metre, and the variation follows a cause (polish where touched, matte where dusty). |
| Colour variation | At three sizes: within a unit (brick to brick), within a wall (repairs, damp), across the block (sun side faded, north side sooty). |
| Scale | Patterns are real size. A brick course is 67.7 mm everywhere in the game. |
| Dust | A summer block is dusty: horizontal surfaces that nobody touches carry a pale film (`#8A8172`, roughness 0.9), thickest in corners, absent where hands, feet, tyres and rain work. |

Base colours below are sRGB hex with the linear luminance in brackets. A range is the space to vary in.

### 3.2 Texture sets

- **Tiling sets** cover anything larger than 2 m or shared by several assets. 2048 px over 2 m (1024 px per metre).
  A set declares its real tile size (`tile_m`); UVs are in metres and are divided by it. Masonry
  tiles are 2.03 m, not 2.00 m: 10 stretchers by 30 courses of brick, or 5 by 10 blocks (80 inches), so courses
  never stretch.
- **Unique baked sets** cover things smaller than about 2 m whose wear is specific: a polished handle, a dent, a
  stencil. Things between 2 and 8 m (vehicles, the dumpster, the booth, the food cart) are unique sets split into
  several texture sets, or tiling sets with unique decals.
- **Hybrid** for the big hero structures: the El and the buildings use tiling sets, `Wear` masks and decals.
- **Trim sheets** (a tiling set that repeats along one axis only) for cornice profiles, window and storefront
  extrusions, kerbs, steel edges with a rivet row for the far El.
- **Detail sets**: small tiling normal-and-roughness tiles at 4,000 to 8,000 px per metre (paint orange peel, cast
  texture, brushed lines, weave, rubber stipple, leather grain). Unique sets are baked at modest density and get
  their close-up surface from these.
- **Macro variation**: every tiling material multiplies in world-space variation at about 0.5 m, 4 m and 20 m
  (colour ± 8 %, roughness ± 0.08) and may blend to a partner set through the wear mask. The scan catalogue pairs
  sets for this (cracked with worn asphalt, for example).
- **Decal sheets** for cracks, patches, stains, oil, gum, tyre marks, road paint, stencils, posters, graffiti,
  bullet marks and scorch. 1024 px per metre; small type 2048 px per metre.

**Where surfaces come from**, in order of preference:

1. **Scans.** `art/scans/sets.json` already catalogues about 80 Poly Haven sets (CC0) by surface and place. Quixel
   Megascans is reported free again on Fab since 5 November 2026 (over 23,000 scans, Fab Standard Licence, usable
   in any tool): a much larger library with urban surfaces and street props. That is newer than the note in
   `docs/unreal/spec/00-unreal-scout.md` 5.6, it needs the client's Epic account, and `fab.com` is not reachable
   from the build container (open question 2). Where a scan's `use` note names a different brick for a building
   than the table in 4.8, the table decides and the note is an alternative.
2. **Procedural Blender surfaces** (`art/blender/mi/mat.py`) baked to sets, for what scans do not cover: painted
   riveted steel in El green, roll-gate slats, chain-link, awning vinyl, the court coating.
3. **Hand-made**, for signage and unique artwork.

A scan is accepted only if it passes its family's row in 3.4 (albedo, pattern scale, known tile size) **and the
regional filter**: most free brick scans are European or South African formats. Scale a brick scan so that three
courses measure 203 mm; accept it if the stretcher then comes within 10 % of 194 mm, reject it otherwise. Reject
bonds and textures that do not occur here (Flemish garden-wall bonds, tumbled pavers, flint).

### 3.3 The `Wear` mask (vertex colours)

One colour attribute named `Wear`, linear, exported as `COLOR_0`. Zero is factory-clean. A mesh without it reads as
fully wet, so every mesh has one (`geo.ensure_wear`).

| Channel | On props, walls, structure | On ground surfaces | Typical cause |
|---|---|---|---|
| R | cavity dirt and grime | the same | creases and sheltered pockets hold what rain does not wash |
| G | edge wear and chips | traffic wear and fatigue: polish, exposed aggregate, cracking | knocks and rubbing reach exposed, convex edges first |
| B | downward leak and rust streaks | oil and liquid stains | water runs down from fixings, ledges and seams, carrying rust, lime and soot |
| A | ground splash-back | wetness: where water collects | rain throws dirt up the first 0.2 m; water finds the low spots |

How the material answers (the same on every tiling surface, so ten artists' walls age alike):

- **R** blends toward the set's dirt colour (street grime `#3B3632` [0.04], soot `#2A2826` [0.02], dust `#8A8172`
  [0.22]; chosen per material instance), darkens ambient occlusion, moves roughness to 0.9 (dry) or 0.35 (oily, in
  the shop).
- **G** reveals what is underneath, with a hard threshold from the height map so chips have crisp edges (paint is
  there or it is not): primer and rust under paint, bright steel on handled edges, paler rough aggregate in
  concrete, the brighter orange body in a chipped brick, bare wood under painted timber.
- **B** multiplies a world-aligned streak pattern (stretched about 1 : 12 downward) in the set's leak colour: rust
  `#7A4428` to `#A8562A` under steel, white lime `#CFCBC0` under mortar joints and concrete ledges, black wash
  under sills and copings, green-black `#3A4A32` where a wall stays damp in shade, white guano `#D8D6CE` under
  perches.
- **A** on walls and props: a pale, matte mud film when dry, strongest in the first 0.2 m and gone by 0.5 m
  (1 m on faces beside the roadway, from tyre spray). The same zone is the first to go dark and glossy when the
  material's `Wetness` rises. On ground: puddles when wet, a silt stain when dry.

Authoring rules:

- Paint causes, not noise. `geo.wear_from_geometry` derives R from occlusion and concavity, G from convexity and
  exposure, B from leak sources (pass the bolt heads, brackets and ledge ends), A from height above the ground.
  Then add the specific story by hand: the kicked bottom of a gate, the corner a truck clips.
- The mask is low-frequency. The material multiplies it by tiling breakup textures and the height map, so the
  transition is sharp at texel scale.
- Meshes need enough vertices to carry it: no edge longer than 0.25 m on architecture or 0.05 m on props that use
  tiling sets (`geo.densify`).
- Masks are data. A value of 0.5 painted in Blender must arrive as 0.5 in Unreal's vertex colour node. Prove it
  once with a ramp test asset (a strip painted 0, 0.25, 0.5, 0.75 and 1 in each channel) before trusting any wall:
  an importer that applies a gamma curve to vertex colours would shift every mask.

### 3.4 Surface families

T = tiling set, U = unique baked set. Roughness and base colour are ranges for the clean-to-aged span, before the
wear mask adds dirt.

**Ground**

| Family | Set | Base colour | Roughness | Metallic | Real pattern scale | Where it wears, and why |
|---|---|---|---|---|---|---|
| Asphalt, avenue | T | worn `#4E4D4B` to `#666461` [0.07 to 0.13]; fresh patch `#333334` to `#3A3A3B` [0.03 to 0.04] | 0.75 to 0.95; polished wheel paths 0.6 | 0 | Stones of 5 to 12 mm in a dark binder. Utility-cut patches of 0.6 to 1.5 m with tar-sealed edges 50 to 100 mm wide. | Paler and stonier in the wheel paths (binder worn off). A dark oil stripe 0.4 to 0.6 m wide down the middle of every lane, blotched at each parking spot. Alligator cracking where buses stop. Rust-brown dust and paint flakes in two lines under the El's edges and around every column. Concrete collars round manholes. One pothole may show the old granite blocks beneath. |
| Asphalt, parking lot | T | oxidised `#6F6D69` [0.15] | 0.8 to 0.95 | 0 | As above, older. | An oil spot in every bay, weeds in the cracks, faded 100 mm stall lines, tyre arcs at the entry. |
| Road paint (thermoplastic) | decal | white `#D2D0C8` [0.63] clean, to [0.35] dirty; yellow `#E0B21A` [0.48] | 0.5 to 0.65 | 0 | Lines 100 to 150 mm wide, 2 to 3 mm thick (a normal map, not geometry). Crossing bars as in the level data. | Worn through in the wheel paths, cracked across, black tyre scuffs, glass-bead sparkle when new. |
| Concrete sidewalk | T | `#8E8B85` to `#B0ACA3` [0.26 to 0.41]; a new flag `#C2BEB4` [0.52] | 0.7 to 0.9; 0.5 to 0.6 on thresholds polished by feet | 0 | Flags scored at 1.5 m (the real standard is 5 ft, 1.52 m; 1.5 fits the level's 3 m sidewalk modules). Broom finish across the walking direction, with a smooth tooled band 40 to 50 mm wide along every joint. Expansion joints with black filler every 6 m. | Gum: black spots of 20 to 40 mm, thickest at doors, the bus shelter and corners. A grease trail from each food shop door to the kerb. Rust rings under sign posts and hatches. Cracked and lifted flags at tree pits, mismatched replacement flags. Dark drip patches under every air conditioner. |
| Kerb | T (trim) | concrete as sidewalk; steel face rust `#7A4428` [0.08] | concrete 0.8; steel 0.5 to 0.9 | steel 1 where tyres polish it | 150 mm reveal, 150 to 180 mm top, a steel angle on the nose. | Tyre rubber and paint scrapes on the face, chips at driveways, yellow or red paint at hydrants, litter and silt in the gutter line. |
| Shop floor slab | T | sealed concrete `#8E8B85` [0.26] with oil-black patches [0.03 to 0.05] | 0.35 to 0.6; oil 0.15 to 0.3 | 0 | Saw-cut joints at 4 to 6 m, a floor drain, yellow safety lines. | Black under each lift and along the walls, clean tracks where cars roll, absorbent granules on fresh spills, weld spatter by the welding rack. |
| Court coating | T | green `#386148` to `#3F6B52` [0.10 to 0.12]; keys in brick red `#8A3B30` [0.09] *(game: red-brown keys)*; lines `#E4E2DA` [0.76] | 0.7 to 0.85 (sanded acrylic) | 0 | Lines 50 mm. | Worn to asphalt in the keys and under the hoops, black crack sealant, puddle rings, leaves and litter along the fence foot. |
| Dirt (vacant lot) | T | `#54493C` to `#6B5E4E` [0.07 to 0.12] | 0.9 to 1.0 | 0 | Compacted fill with brick rubble, glass and cinders. | A trodden path, tyre ruts, weeds along the fences, a burnt patch under the car. |

**Masonry**

| Family | Set | Base colour | Roughness | Real pattern scale | Where it wears, and why |
|---|---|---|---|---|---|
| Red face brick (tenement fronts) | T | `#6B382E` to `#8F4B3A` [0.06 to 0.11], brick-to-brick variation ± 15 % | 0.8 to 0.95 | 194 × 57 × 92 mm, running bond, joints 6 to 10 mm, often dark. | Soot wash under every sill and cornice end, a clean fan below each window sill where rain runs, grey repointed patches, white efflorescence below the parapet, rust from fire-escape anchors, tags and paint-outs in mismatched reds up to 2.2 m. |
| Common brick (side and rear walls) | T | `#8A4E3A` to `#B46C4C` [0.11 to 0.21], strongly varied, some burnt-dark headers | 0.85 to 0.95 | Same brick, rougher; a header course every sixth course; flush, sloppy joints of 10 to 12 mm. | Patches of new brick and cement, tar lines and plaster ghosts where a neighbour stood, long water stains from failed gutters, peeling painted adverts. |
| Tan and buff brick (deli, S3 row) | T | `#A08766` to `#C2AA86` [0.26 to 0.42], iron-spot speckle | 0.75 to 0.9 | As face brick, with soldier courses over openings and a cast-stone coping. | Grey-black soot streaks show strongly on pale brick, rust bleeds from lintels, splash-back darkening at the base. |
| Brown brick (station house block) | T | `#5C4336` to `#6A4E3E` [0.07 to 0.09] | 0.8 to 0.95 | As face brick. | White lime runs from the joints, pale repointing. |
| Painted brick and block | T | the paint, for example off-white `#C9C4B6` [0.55], dirty `#AAA699` [0.38] | 0.6 to 0.75 | Paint fills the pores and softens the joints; the bond still shows. | Peeling in sheets from damp at the base and below the coping, rectangles of mismatched overpaint where tags were covered, hand-height grime. |
| Concrete block (V&R Auto Body) | T | raw `#979590` to `#A8A59E` [0.30 to 0.38] | 0.9 to 0.95, open-pored | 397 × 194 mm face, 10 mm joints, running bond. | Stair-step cracks from the corners of openings, chipped corners at bumper height, a dark blue-green dado band of paint to 1.2 m (game hue `#27414B`), rust below the steel lintel, exhaust soot above each door. |
| Mortar | in the brick sets | grey-buff `#9A968C` [0.31]; sooty `#6E6A62` [0.15] | 0.9 | Recessed 2 to 6 mm (a normal and height map). | Eroded deeper on weather sides, lighter and harder-edged where repointed. |
| Stucco and cement patch | T | `#B7AE9A` [0.43] | 0.85 to 0.95 | Trowel sweeps of 0.3 to 0.6 m. | Map cracking, damp lines, the scar where a cornice came off. |
| Glazed tile (bulkheads) | T | white `#D9D6CC` [0.67]; grout [0.10] | 0.08 to 0.2, crazed | 75 × 150 mm or 100 mm square. | Cracked and missing tiles at kick height, grime in the grout, splash-back. |
| Cast stone and concrete trim | T | `#9A968C` to `#B7AE9A` [0.31 to 0.43] | 0.8 to 0.9 | Sills 100 to 120 mm deep projecting 40 mm. | Black streaks at the ends of sills, spalled corners with a rusty bar showing. |
| Formed concrete (El pedestals, barriers, knee walls) | T or U | `#979590` [0.30] | 0.75 to 0.9 | Form-board lines, 20 mm chamfers, bug holes of 2 to 10 mm. | On pedestals: car paint in every colour, tyre rubber, hazard stripes worn off, rust wash from the base plate above. |

**Steel, iron and other metals**

| Family | Set | Base colour | Roughness | Metallic | Real pattern scale | Where it wears, and why |
|---|---|---|---|---|---|---|
| El structure paint | T | dark green `#354C40` to `#3F5A4C` [0.06 to 0.09]; chalked tops `#5E7468` [0.16]; sooty undersides `#2C3A33` [0.04] | 0.45 to 0.7; chalked 0.7 to 0.85; repaint patches 0.3 to 0.4 | 0 | Rivet heads 36 mm across and 15 mm high at 75 to 150 mm pitch (geometry). Paint about 1 to 2 mm thick, crazed like alligator skin on old coats. | Rust starts at rivet heads, plate edges and wherever water sits: the top of the bottom flange, gusset pockets, column bases. Pack rust swells between plates and waves their edges (5 to 15 mm, geometry). Orange runs below each connection. Repaint patches in a slightly different green. White guano under every flange a pigeon can stand on. Stickers, tags and paste residue to 2.2 m. Brake dust and oil on the deck underside. |
| Black enamel (fire escapes, railings) | T | `#2B2B2D` [0.02] | 0.25 to 0.45: it mirrors the sky | 0 | Flat bars 38 × 6 mm. Many coats: every edge is rounded by paint. | Rust at every joint and where slats meet stringers, running down the wall beneath each anchor. Bare polished steel on ladder rungs and handrails. |
| Rust | T | old `#4A2E20` [0.04], common `#7A4428` [0.08], fresh runoff `#A8562A` [0.15] | 0.85 to 1.0 | 0 | Scale flakes of 1 to 3 mm. | (A wear layer everywhere steel is; a surface in its own right on the burned car, garage doors, rail webs.) |
| Raw steel with mill scale (road plates, new repair steel) | T | `#6E7175` [0.16]; wheel-polished `#C5C7C8` | 0.45 to 0.6; polished 0.25 to 0.35 | 1 | Plates 1.2 × 2.4 m, 25 mm thick. | Bright in the wheel tracks, orange at the edges, a sprayed owner's mark (invented). |
| Galvanised steel | T | new `#C3C7CA` [0.57]; weathered `#9DA1A4` [0.35] | new 0.35 to 0.5 with spangle crystals of 5 to 20 mm; weathered 0.55 to 0.7 | 1; white-rust patches 0 | Pipe 42 to 73 mm, sheet, wire. | Dull grey with age, white bloom where water sits, red rust at cut ends, welds and scratches. |
| Chain-link | T, alpha | as galvanised | as galvanised | 1 | 50 mm diamond, 3.0 to 3.8 mm wire, knuckled or twisted at the top. | Bulged where people lean and balls hit, curled up at the bottom where people crawl under, wire patches, plastic bags and a litter line at the foot, torn scrim on cable ties. |
| Corrugated and box-profile sheet | T | galvanised or painted | 0.45 to 0.7 | 1 where bare | Corrugation 68 mm pitch, 22 mm deep, or 64 × 13 mm (geometry). | Rust along laps and at every fixing, dents, paint peeling in sheets. |
| Cast iron (hydrants, covers, grates) | U or T | polished high spots `#8A8C8E` [0.26]; recesses hold dirt [0.03 to 0.06] | 0.35 to 0.5 polished; 0.9 in recesses | 1 on polished iron, 0 elsewhere | Cover patterns 3 to 5 mm high (normal map). Covers sit 5 to 20 mm proud or sunk (geometry). | Tyre-polished on the road, rust-brown on sidewalks, asphalt lapped over the frame. Covers carry generic words only: SEWER, WATER, ELECTRIC. |
| Tread plate (cellar hatches, steps) | T | painted or galvanised | 0.4 to 0.6 | 1 where worn | Lugs 25 to 30 mm long, 1.5 to 2 mm high (normal map). | Paint gone and lugs bright down the middle, rust at hinges, a padlock. |
| Aluminium storefront framing | T (trim) | clear anodised `#D6D8DA` [0.69], or dark bronze | 0.3 to 0.45, fine extrusion lines | 1 | Mullions 45 to 50 mm wide. | Scratches and tape residue at hand height, white corrosion at the sill, mastic smears. |
| Stainless steel (train, food cart) | T and U | `#C8CACC` [0.59] | 0.25 to 0.4, brushed along the car | 1 | Panel seams every 1 to 1.5 m; panels are never flat (reflections wobble). | Brake dust on the lower third, water runs from every window corner, scratched tags. |
| Chrome | in unique sets | `#C4C5C4` | 0.02 to 0.08 | 1 | n/a | Pitting and a film of dust. |
| Gold (watch, bracelet, pawn sign, truck band) | in unique sets | `#FFE39D`; 14-carat `#F9E5AD` | 0.15 to 0.3 with fine scratches | 1 | n/a | Brushed and polished faces alternate on the watch band; skin oil in the links. |

**Glass**

| Family | Set | Values | Real scale | Wear |
|---|---|---|---|---|
| Storefront plate glass | T (dirt) | F0 0.04, roughness 0 to 0.05, a faint green tint at the edges | 6 to 10 mm, in panes up to 2.4 m wide. Tempered glass shows a slight roller wave: reflections of the El bend a little. | A dirty film in the bottom 0.4 m (splash-back), handprints at the pull, tape and sticker ghosts, a paper sign taped inside, a security grille or a display behind. |
| Upper-storey windows | T | as above. Opaque glass with a parallax room behind it for upper floors; real shallow rooms at street level | Double-hung, 1.1 × 1.65 m opening *(game)* | Rain-spotted dust, one pane cracked and taped, blinds half down, foil, a fan, a plant. By day they mirror the sky and the facade opposite; you see in only where the reflection is dark. |
| Wired glass (shop doors, skylights) | T | translucent, pebbled, roughness 0.3 to 0.5 | 12 mm square wire mesh | Yellowed, cracked along the wires, paint overspray. |
| Vehicle glass | U | tinted green-grey, darker privacy glass on the SUV | Dotted black border, heater lines, inspection and registration stickers (invented) | Wiper arcs in the dust, bird marks, a parking ticket (invented form). |

**Gates, awnings, plastics, rubber**

| Family | Set | Base colour | Roughness | Metallic | Real pattern scale | Where it wears, and why |
|---|---|---|---|---|---|---|
| Roll-gate slats | T | painted grey, brown, black or forest green, or bare galvanised | 0.4 to 0.6 | 1 only where rubbed bare | Curved slats at 75 mm pitch (geometry), side guides 60 to 75 mm deep, a hood box 0.35 to 0.4 m square, a bottom bar with padlock hasps. Newer gates are perforated or open grille. | Dented in the bottom third (kicks, hand trucks), bright rub tracks in the guides, rust at slat ends and below the hood, layers of tags and paint-out rectangles. |
| Awning vinyl | T | green `#1F5A3A` [0.08], red `#B3261E` [0.11], navy `#1C2F5A` [0.03] *(game colours)* | 0.35 to 0.5; sun-chalked 0.6 to 0.7 | 0 | Laminated fabric on a welded 25 mm square-tube frame. Valance 0.2 to 0.3 m. | Sagging between frame bars with a pooled-water stain, dirt runs from the top edge, faded on the side the sun reaches, guano, a torn corner. One frame on the block has lost its fabric. |
| Canvas | T | natural `#B8AE98` [0.43] or dyed, stripes 100 to 150 mm | 0.85 to 0.95 | 0 | Weave visible only within 0.5 m (detail set). | Mildew spots in the folds, bleached where sunlit, frayed edges. |
| Debris netting, scrim, tarpaulin | T, alpha for netting | netting rust-orange `#C4571A` [0.19] *(game)*; fence scrim and tarps dark green `#2C5A3A` [0.08] | 0.6 to 0.8 | 0 | Knitted mesh with 2 to 4 mm holes and reinforcing tapes every 60 mm; hemmed edges with eyelets every 0.5 m. | It reads as solid from the street because its collision is solid: dense, dusty, doubled where it laps. Torn at corners, sagging between ties, bleached in bands, snagged litter. |
| Moulded plastic (crates, barrels, cones, bins, toilet) | U | traffic orange `#E8641B` [0.26]; bins dark green or grey; crates red, blue, black | 0.4 to 0.6; sun-chalked 0.7 | 0 | Milk crate 330 × 330 × 280 mm. Barrel bands of reflective sheeting 100 to 150 mm. | Scuffed white at edges, chalky and faded on the sun side, tyre rubber on barrels, cracked corners. No dairy names on crates. |
| Black trim plastic (vehicles) | U | `#2B2B2D` [0.02]; faded `#56565A` [0.09] | 0.55 to 0.75, fine grain | 0 | n/a | Greys with sun, wax residue in the grain. |
| Refuse sacks | U | black `#2A2A2C` [0.02]; clear recycling sacks show cans and bottles | 0.2 to 0.4, sharp wrinkles | 0 | 0.5 to 0.7 m sacks, piled at the kerb. | Stretched pale at the knot, a split with something spilling, a wet patch beneath. |
| Rubber (tyres, mats, hoses) | U or T | `#2A2A2B` [0.02]; dusty `#4A4744` [0.06] | sidewall 0.75 to 0.9; tread 0.85 to 0.95 | 0 | Tread grooves 7 to 8 mm deep (geometry). Sidewall text 1 mm (normal map): sizes only, no brands. | Brown brake dust on the wheel and lower sidewall, kerb scuffs, flat-spotted where a car has stood. |

**Timber and roofing**

| Family | Set | Base colour | Roughness | Real pattern scale | Where it wears, and why |
|---|---|---|---|---|---|
| Track ties | T | creosoted `#3E352D` [0.04] to weathered `#5A5148` and `#6E665C` [0.09 to 0.14] | 0.6 to 0.85 | 220 × 180 mm section, 2.7 m long, every 0.56 m *(game)*. Checks (splits along the grain) 2 to 10 mm wide. | Seen from below: rust-orange brake dust, black grease drips, guano, tie plates and spikes bleeding rust. |
| Planks and scaffold boards | T | `#7A6E5E` [0.16]; new boards paler | 0.75 to 0.9 | 235 × 38 mm planks, 2.4 to 4.9 m long, ends cleated or banded. | Grey with weather, concrete splashes, boot-polished centres. |
| Plywood | T | raw `#A98A5C` [0.27]; hunter green paint `#355E3B` [0.09], faded `#4A6B50` [0.13] (the game's hoarding green is `#23463C`: keep that hue, at these values) | 0.7 to 0.9 | 1.22 × 2.44 m sheets, face grain running the long way. | Delaminating at the bottom edge, patches of newer green, "POST NO BILLS" stencil, paste and poster layers. |
| Pallets, crates, cardboard | U or T | wood as planks; cardboard `#9A7B52` [0.22] | 0.85 to 0.95 | Pallet 1.2 × 1.0 × 0.144 m. | Broken boards, strap marks; cardboard dark and slumped where it has been wet. |
| Roofing | T | bitumen `#2F2F31` [0.03]; silver coating `#A9ACAE` [0.41] | bitumen 0.8 to 0.95; silver 0.5 to 0.6 | Rolls 1 m wide with lapped seams, flashing up the parapet. | Ponding rings, patches of fresh tar, blisters, gravel drifted to the drains. Seen from the title camera only. |
| Water-tank staves | T | weathered cedar `#6E665C` [0.14] | 0.8 to 0.9 | Staves 100 to 150 mm, steel hoops closer together toward the bottom. | Dark and green below the overflow, rust lines under every hoop. |

**Signage** (construction in section 5)

| Family | Set | Base colour | Roughness | Notes |
|---|---|---|---|---|
| Acrylic and flex sign faces | U | white `#DEDCD4` [0.72]; translucent film colours as artwork, inside the range of 3.1 | 0.15 to 0.3; dusty 0.4 | Lit from inside at night (2.7). Yellowed, bowed, cracked at a corner, dead insects along the bottom edge, one dim band where a tube has failed. |
| Painted sign (enamel on metal, board or brick) | U or decal | as artwork, clamped to the paint range | 0.3 to 0.5 fresh; 0.6 to 0.8 weathered | Brush edges slightly uneven, an older sign ghosting through, faded most on the sunny side. |
| Cut vinyl lettering | decal | as artwork | 0.3 to 0.45 | Perfect edges, small bubbles, a lifting corner, shrink lines. |
| Neon glass | geometry | clear or coated glass; unlit tubes are milky white or tinted | 0.05 to 0.15 | Black blocking paint between letters, dust on top of every tube. |
| Paper (posters, handbills) | decal on thin mesh | white `#D8D6CE` [0.67] and below | 0.7 to 0.9 | Wheat-paste wrinkles, torn layers showing older posters, sun-faded reds. |

**Vehicles**

| Family | Set | Base colour | Roughness | Metallic | Notes |
|---|---|---|---|---|---|
| Car paint | U | fleet colours *(game, `src/props/vehicles.js`)*: white `#E6E4DC`, silvers `#B9BCC0` and `#8F959C`, graphite `#3A3E45`, black `#1E1E20`, red `#9C2320`, blue `#24508F`, green `#2C5A3E`, champagne `#A89878`, maroon `#6A1C22`, navy `#1E2B48`; taxi yellow `#F2C21A` [0.58] | base 0.3 to 0.5; clear coat 0.03 to 0.1 clean, 0.2 to 0.35 dusty | 0 for solid colours, 1 flake layer for metallics | Clear-coat shading with fine orange peel. At least seven of ten parked cars are white, black, silver or grey. Dust film on bonnet, roof and boot with wiper-clean glass; road grime behind each wheel; kerb rash; a door ding per car; one car per row with a faded, peeling clear coat. |
| IPX truck | U | gloss black `#1E2024` [0.014]; gold band as gold metal | clear coat 0.03 to 0.08: it is kept clean | band 1 | Flat armour plate, visible bolt lines, thick small glass with a green edge. |
| Lamps | U | clear, red and amber lenses over modelled reflectors | 0.05 to 0.15 | reflector 1 | Lens optics as geometry and normal map; hazed, yellowed plastic on the older cars. |
| Wheels | U | painted alloy silver, steel wheels black with caps | 0.3 to 0.5 | 1 where bare | Brake dust browning, kerb rash. |
| Interior | U | grey and black cloth and plastic | 0.6 to 0.95 | 0 | Enough to read through the glass: seats, wheel, dash, a tree-shaped air freshener, a sun shade, coffee cups. No brands. |
| Burned car | U | rust `#7A4428`, soot `#2A2826`, grey ash, blued bare steel | 0.6 to 1.0 | 1 on heat-blued steel | No glass, no tyres (wire beads on the ground), sagged roof, white ash where alloy melted. |

**Clothing and skin** (dimensions in `docs/unreal/spec/02-weapons-combat.md` 5.4 and `03-enemies.md`)

| Family | Set | Base colour | Roughness | Notes |
|---|---|---|---|---|
| Black cotton fleece (hoodie, joggers) | U | `#2E2E33` to `#3A3A40` [0.03 to 0.04]: black, but with enough albedo that folds read in sun | 0.85 to 1.0, cloth shading with a soft sheen | Sun-faded to charcoal on shoulders and hood, pilling, dust on knees, elbows and hems, a drawcord, ribbed cuffs. |
| Nylon puffer | U | black `#2B2B30` [0.03], charcoal `#3A3D47` [0.05] | 0.45 to 0.6 with fine ripstop | Quilted baffles 60 to 80 mm (geometry), stitched seams puckering, scuffs paler. |
| Tracksuit knit | U | black, with oxblood side stripes | 0.6 to 0.75 | Slight sheen along the stripe. |
| Oxblood accents | in the sets | `#6B1218` to `#7C151D` [0.04 to 0.05] | as the cloth | The crew colour: hood lining, yoke, stripes, bandana print, beanie. |
| Pale mask (knit balaclava, bandana) | U | bone `#DCD5C5` [0.67] | 0.85 to 0.95 | Rib knit, stretched over nose and brow, grubby round the mouth and eye holes. It is the brightest thing on the figure: the head must read at 40 m. |
| Sneakers | U | off-white `#D6D1C4` [0.64] leather, white sole | 0.4 to 0.6 | Creased toe box, grey soles, no brand marks of any kind. |
| Denim | U | dark indigo `#2E3442` [0.03] | 0.8 to 0.9 | Twill weave in the detail set, paler at knees and seams. |
| Glove leather and suede (Rule) | U | black synthetic leather `#2A2A2C` [0.02], suede palm slightly warmer | leather 0.55 to 0.7; suede 0.8 to 0.9; rubber knuckle bar 0.4 | Stitched panels, a padded knuckle, creases at each joint, polish on the trigger finger and palm. Original design, no maker's mark. |
| Skin (Rule's forearms) | U | brown `#7A5038` to `#9B6B4C` [0.10 to 0.18] | 0.35 to 0.5 with pores, subsurface profile | Fine hair, tendons that move with the grip, a paler inner arm. Match the star's reference if IPX supplies it (open question 4). |

**Guns** (part dimensions in `docs/unreal/spec/02-weapons-combat.md` 5.2 and 5.3)

| Family | Set | Base colour | Roughness | Metallic | Notes |
|---|---|---|---|---|---|
| Blued steel (CHOPPER receiver, magazine) | U | `#4A4D52` [0.07] | 0.25 to 0.4 | 1 | Blue-black, glossy enough to show the sky and the sun as shapes. Edges and the magazine's rub lines worn to bare steel `#C5C7C8` at roughness 0.25 to 0.35. Fine drag marks along every sliding surface. |
| Phosphate or painted steel | U | grey-black `#3A3B38` [0.04] | 0.6 to 0.75 | 0 | Matte, slightly chalky, oil-darkened where handled. |
| Brushed stainless (NINE slide) | U | `#C5C7C8` | 0.3 to 0.45, brushed along the slide | 1 | Holster wear at the muzzle, carbon at the ejection port. |
| Polymer and checkered grips | U | `#29292B` [0.02] | 0.55 to 0.75 with moulded stipple or checkering 1 mm deep | 0 | Shine on the high points of the checkering. |
| Laminated wood (CHOPPER furniture) | U | red-brown `#55301C` to `#6A3C22` [0.04 to 0.06] under varnish | 0.3 to 0.45 | 0 | Laminate lines every 1.5 to 2 mm following the shape, varnish chipped at edges, dents, hand-darkened grip. |
| Brass and copper (rounds, casings) | U | `#F2E6B0`, `#FAD1C2` | 0.25 to 0.35 | 1 | Fired casings are sooted at the mouth and scratched. |
| Gold accents (NINE trigger, magazine base) | U | `#FFE39D` | 0.2 to 0.3 | 1 | As the watch. |

Guns carry no maker's marks, proof marks or real model names. Selector positions are pictograms. A serial number
is an invented string.

### 3.5 The grammar of wear

| Agent | It gathers | Because |
|---|---|---|
| Dirt and dust | in concave corners, on ledges, behind and under things, in the bottom 0.2 m of every wall | rain and feet clean everything else |
| Rust | at fixings, cut edges, welds, the bottom of anything that holds water, under chipped paint | steel rusts where its coating is broken and water stays |
| Leaks | straight down from brackets, bolt heads, sill ends, coping joints, air conditioners, gutter failures | water carries rust, lime, soot and algae and drops them as it dries |
| Gum | on sidewalks where people wait or step out: doors, the shelter, corners, the kerb edge | it is dropped where people stand |
| Oil | in the centre of each lane, in each parking bay, across the shop apron and floor | engines drip where they sit |
| Soot | above doors and vents, on undersides of the El, on north-facing and sheltered masonry | combustion rises and sticks where rain does not wash |
| Chips | on convex edges at the height of what hits them: bumper (0.4 to 0.6 m), hand truck (0.1 to 0.3 m), shoulder (1.3 to 1.5 m) | impact needs something to do the hitting |
| Polish | on handrails, door pulls, ladder rungs, thresholds, kerb noses, wheel paths | touch and traffic smooth and brighten |
| Sun fade | on south- and west-facing paint, vinyl and plastic | ultraviolet chalks the surface and bleaches reds first |
| Guano | under every perch: flanges, cornices, the billboard catwalk, lamp arms | pigeons sit in the same places every day |
| Paper and tags | from 0.5 to 2.2 m on anything flat and public | that is where an arm reaches |

---------------------------------------------------------------------------------------------------

## 4. Modelling bar

### 4.1 Real dimensions of recurring things

| Thing | Dimension | Status |
|---|---|---|
| Brick | 194 × 57 × 92 mm with joints of about 10 mm, on the 8-inch module: 3 courses = 203 mm, 10 stretchers = 2.03 m | measured |
| Concrete block | 397 × 194 mm face, joints of about 10 mm: 5 blocks = 2.03 m, 10 courses = 2.03 m | measured |
| Kerb | 150 mm reveal, 150 to 180 mm top, steel-faced nose | game, measured |
| Sidewalk flag | 1.5 m square (real 1.52 m, trimmed to fit the 3 m sidewalk modules), score joints 8 mm wide and 10 mm deep | chosen |
| Door leaf | 2.03 × 0.91 m, in a 50 mm frame | measured |
| Shop door opening | 1.25 m wide: one 0.91 m leaf with a fixed sidelight, or a pair of narrow leaves | game |
| Storefront | bulkhead top 0.78 m, glass head 2.84 m, sign band from 2.84 to 3.8 m | game |
| Storefront bay widths | the ten shop fronts measure 5.8 to 11.0 m (table in 5.3); real bays run 4.5 to 7.6 m, so the wide ones are two-bay shops with a centre mullion or pier | game |
| Storey heights | 3.8 m ground, 3.1 m above | game |
| Window opening | 1.1 × 1.65 m, sill 0.95 m above the floor | game |
| Stair riser | 187 mm (station), 233 mm (shop and scaffold stairs) | game |
| Guard rail | 1.07 m | measured |
| Awning | projects 0.9 to 1.5 m, lower edge at least 2.4 m above the sidewalk | measured |
| Fire-escape balcony | 3.0 × 1.1 m per storey, slats 38 × 6 mm with 25 to 30 mm gaps | game, measured |
| El column spacing | 10 m along the avenue, rows 9.2 m apart | game |
| El column | 0.5 m square built-up H, concrete pedestal 1.04 m square, clear height 5.3 m | game |
| El girders | cross girder 1.2 m deep; longitudinal girders 1.0 m deep; deck underside 6.5 m | game |
| Rivet | 22 mm shank, head 36 mm across and 15 mm high, pitch 75 to 150 mm, 38 mm from plate edges | measured |
| Track | gauge 1.435 m, rail 150 mm high with a 70 mm head, rail top 6.83 m | game, measured |
| Tie | 220 × 180 mm, 2.7 m long, every 0.56 m | game |
| Chain-link | 50 mm mesh, 3.0 to 3.8 mm wire, posts 60 to 73 mm every 3.0 m, top rail 42 mm, heights 2.4 m and 4.0 m | measured, game |
| Jersey barrier | 0.81 m high, 0.6 m base, 0.15 m top, 3.0 m long | game |
| Lanes | parking 2.4 m; lane lines 100 to 150 mm | game, measured |
| Basketball | rim 3.05 m, backboard 1.83 × 1.07 m, rim 0.457 m across | measured |
| Scaffold tube | 48.3 mm, couplers at every node, timber sole boards | measured |
| Sidewalk shed | deck 2.8 m above the sidewalk, parapet 1.1 m | game |
| People | Goon 1.80 m; the player's eye at 1.68 m standing, 1.05 m crouched | game |

**The gameplay silhouette contract.** Every prop fills its catalogue box (`src/config/catalog.js`, length × height ×
width) within 5 % (2 cm at least), and its cover top is exact to 2 cm. The code's collider tops are the truth
(`docs/unreal/spec/05b-props.md` 2.3; they differ a little from the round numbers in DESIGN section 4): sedan and
taxi body 1.08 m and cabin 1.45 m, SUV body 1.24 m, jersey barrier 0.81 m, refuse-sack pile 0.62 m, crate stack
0.90 m, traffic barrel 0.98 m, newspaper box 1.08 m, mailbox 1.20 m, dumpster 1.30 m. A crouched eye is at 1.05 m,
a standing one at 1.68 m: those two lines decide what is cover. Collision is the port's simple boxes, never the
render mesh, so the mesh must not be visibly smaller than its box (rounds would stop in air) nor larger (the
player would clip through it). Level modules keep their collision faces, cover heights and openings exactly
(`docs/unreal/spec/05-level.md` 5.1); relief that carries no collision (piers, cornices, awnings, sign boxes) may
stand proud. Where the web game draws mesh or netting over a solid collider, make the thing look as solid as it
plays: scrim, tarp, stacked contents.

### 4.2 Bevels

No visible edge has zero radius. If an edge can be seen from 1 m it is bevelled with at least two segments (three
or more above 8 mm), and flats stay flat (weighted normals).

| Class | Bevel | Examples |
|---|---|---|
| Props | 2 to 10 mm | folded sheet metal 2 to 3 mm; moulded plastic 2 to 4 mm; sawn timber 2 to 5 mm; cast iron 5 to 10 mm |
| Architecture | 5 to 20 mm | block and brick corners 5 mm; cut stone 5 to 10 mm; kerb nose 10 to 20 mm; formed concrete 20 mm chamfers |
| Old painted steel | 3 to 6 mm | paint build-up rounds every edge of the El and the fire escapes |
| First-person weapons | 0.3 to 1.5 mm | real machined chamfers: in the geometry where 0.5 mm or more, in the normal map below that |

### 4.3 Geometry or normal map

Relief deeper than about 5 mm is geometry (Nanite draws it and it casts a shadow). Shallower relief is a normal and
height map.

| Geometry | Normal and height map |
|---|---|
| Rivet and bolt heads, nuts, weld beads over 5 mm | Mortar joints (2 to 6 mm), brick pores and texture |
| Roll-gate slat profile, corrugation, grating bars | Tread-plate lugs, cover patterns, cast texture |
| Sidewalk score joints, kerb chips, potholes, lifted flags | Asphalt aggregate, broom finish, hairline cracks |
| Pack-rust bulges, dents in sheet metal (gates, cars, mailboxes, dumpsters) | Paint chips and crazing, rust scale |
| Window frames, glazing beads, channel letters, raised sign faces | Vinyl lettering, stencils, screen print |
| Panel gaps on vehicles, tyre tread, lamp reflectors | Sidewall lettering, lens prisms, paint orange peel |
| Cloth folds, quilting, laces, zip pulls | Stitches, weave, knit, leather grain |
| Brick at outside corners and around openings (below) | Brick in the field of a wall |

**Brick silhouettes.** A flat plane with a brick normal map fails at its edges. Every outside corner, window and
door reveal, and parapet top within 3 m of any camera gets a strip of modelled bricks (about 0.2 m wide) that
toothes into the flat field, plus a few modelled chipped and missing bricks per wall.

### 4.4 The imperfection budget

| Thing | Deviation |
|---|---|
| Long horizontal lines (sign bands, awning bars, gutters, cornices) | sag or wander 5 to 20 mm over 5 m |
| Posts and poles | lean 0.5 to 1.5° |
| Signs | tilt 0.5 to 2°; no two at the same height |
| Roll gates | slats dented 5 to 30 mm; bottom bar not level by up to 15 mm |
| Chain-link | mesh bulges 30 to 150 mm; top rail bent between posts |
| Sidewalk flags | steps of 5 to 25 mm at some joints; one flag cracked in three |
| Kerb | chips of 20 to 80 mm at driveways and corners |
| Brick walls | a visible bulge or lean on one old wall; lintels sagging 5 to 10 mm |
| Vehicles | parked 0.1 to 0.4 m off the kerb, never parallel; wheels turned on some |
| Repeated modules | every instance differs in at least one of: variant, rotation, `Wear` mask, decal, colour |

### 4.5 Texel density

| Class | Density | Typical sets |
|---|---|---|
| First-person weapons, gloves, watch, bracelet, forearms | 1024 px per metre is the floor. The first-person camera samples the gun at 3,000 to 6,000 px per metre on screen, so surfaces the camera reads (receiver top and left side, sights, slide rear, glove backs, the watch) get 4096 px per metre or more. | One 4096² set per weapon and one for the arms gives 6,000 px per metre and up; the watch and bracelet share a 2048² set. |
| Cover props (everything in the prop catalogue the player can touch) | 512 px per metre unique bake, plus a detail set | 2048² for a barrier or a dumpster; 1024² for small props |
| Hand-sized and hero props (master case, reel, boombox, propane tank, tags) | 1024 px per metre | 1024² to 2048² |
| Vehicles | body 512 to 1024 px per metre | four sets: body 4096², interior 2048², wheels and underbody 2048², glass and lamps 1024² |
| Characters | 1024 px per metre and up | Goon: two 4096² (upper, lower), 2048² (mask, gloves, shoes), 1024² (SMG) |
| Architecture and structure | tiling at 1024 px per metre (2048 px over 2 m) | the tiling library |
| Decals, signs | 1024 px per metre; small type 2048 | atlas sheets |
| Mural (12 × 7.6 m) | about 600 px per metre of colour over the wall's own brick normal | 8192 × 4096 |
| Billboard face (8.9 × 4.0 m) | about 450 px per metre | 4096 × 2048 |
| Beyond the play bounds | 64 to 256 px per metre | shared sets |

### 4.6 Triangles

Static, opaque meshes are Nanite: triangles there are cheap, megabytes and overdraw are not. Model what section
4.3 says is geometry, do not subdivide flats, and keep each exported mesh under 300,000 triangles (the pipeline
warns above that): split larger things into modules.

| Asset | Triangles (source, level of detail 0) |
|---|---|
| El column with base and rivets (one mesh, instanced 20 times) | 100,000 to 200,000 |
| El cross girder and knee braces; a 10 m girder span; a 10 m deck span | 100,000 to 250,000 each |
| Facade bay, one storey (wall, window, sill, lintel, guard) | 20,000 to 60,000 |
| Storefront with gate, awning frame and sign | 100,000 to 300,000, in modules |
| Fire escape, per storey | 60,000 to 120,000 |
| Small props (cone, crate, hydrant, tank) | 5,000 to 30,000 |
| Medium props (barrier, dumpster, mailbox, tool chest) | 20,000 to 80,000 |
| Large props (food cart, booth, bus shelter) | 80,000 to 250,000 |
| Vehicle | 300,000 to 600,000 in parts (body, interior 80,000 to 150,000, four wheels); glass separate, under 5,000 |
| IPX truck | 500,000 to 800,000 in rigid parts (the doors swing) |
| Train car | 200,000 to 400,000 in parts (body, two trucks), one car instanced five times |
| Buzzard | 40,000 to 70,000 in rigid parts |
| Goon (skeletal, not Nanite) | 70,000 to 100,000, with levels of detail at 50 %, 25 % and 10 % |
| CHOPPER; NINE; arms with gloves; watch; bracelet (skeletal, not Nanite) | 120,000 to 200,000; 60,000 to 100,000; 60,000 to 90,000; 20,000 to 40,000; 15,000 to 30,000 |

Not Nanite: skeletal meshes, glass and anything translucent, chain-link cards, decals, effects. Their budget in
view is 1.5 million triangles.

### 4.7 What the engine needs from a mesh

- **Lumen** wants separate, simple, closed pieces: walls, floors and roofs as separate meshes with real thickness
  (20 cm or more), never a whole room as one inside-out shell. The shop interior is built this way.
- **Thin things** (ties, lattice, fire escapes, fences, wires) are lost in distance fields. They keep a Nanite
  fallback mesh that preserves their shape for hardware ray tracing, and they are switched off for distance-field
  lighting. The El deck also ships a solid proxy slab for the software path.
- **Shadows**: everything that stands in the sun casts. Decals, lamp lenses and small clutter on roofs do not.
  Chain-link casts as a uniform 14 % dimming: its diamond shadow is only sharp within 0.4 m of the mesh, because
  the sun's soft edge (about 9 mm per metre) swallows a 3.5 mm wire.
- **Motion**: anything that sways (awning valances, scrim, cables, the tree) moves by vertex offset with a small
  amplitude and a cut-off distance, so shadow caching survives.
- **Chain-link** is an alpha-tested card with a normal map by default, with real posts, rails, ties and gate
  hardware. Whether the reachable panels get real wire is decided by an in-engine test (open question 8).
- **Glass** is its own mesh and material slot on every asset.

### 4.8 Kits

Build modules, not buildings. The block is assembled from: an **El kit** (column, base, bent, girder span, deck
span, bracing bay, lamp, station pieces); a **facade kit** per brick type (wall bay with and without window,
corner strip, parapet, cornice run and end, fire-escape storey and ladders); a **storefront kit** (bulkheads,
glazing bays, door, transom, gate up and down, hood, awning frames, sign carriers); a **block-shop kit** (wall
bays, roll door, man-door, lintel, bollard, skylight, joists); a **fence kit** (panel 2.4 and 4.0 m, post, gate,
scrim, knee wall); a **ground kit** (road strips, kerb straight and dropped, sidewalk flags, hatch, manhole, catch
basin); a **scaffold kit**; a **lot kit** (booth, low wall, wheel stop, pole, billboard). Dimensions and placements
come from the exported level data.

Which brick goes where *(storeys and base brick from the web game; the rest chosen)*. Street fronts are face brick.
Side and rear walls are common brick on every building, whatever the front: it is how these buildings were built
and it is what makes a row read as real.

| Building (layout id) | Storeys, height | Street front | Sides and rear | Ground floor |
|---|---|---|---|---|
| Tenement (`n1`) | 5, 16.2 m | red face brick, sheet-metal cornice, fire escape | common brick; the east party wall carries the painted V&R advert | laundromat, residents' door on a two-step stoop, barber |
| Deli block (`n2`) | 3, 10.0 m | tan iron-spot brick, cast-stone coping | common brick; a fire escape on the alley side | deli |
| Station house block (`s1`) | 3, 10.0 m | brown brick, cornice, fire escape | common brick | cheque casher, pizza |
| Pawn and records (`s2`) | 4, 13.1 m | red face brick | common brick; the east wall carries the mural | pawn shop, gated vestibule, record shop |
| Taxpayer row (`s3`) | 2, 6.9 m | tan brick with soldier courses and a parapet panel | common brick; cement stucco at the rear | chicken, liquor, nails, behind the sidewalk shed |
| Rear-lane garages | 1, 3.8 m | painted brick or block, numbered steel doors (41 and up) | the same | none |
| V&R Auto Body | 1, eave 6.0 m, parapet 6.9 m | painted concrete block, two-tone | raw and painted block | roll door 6.0 × 4.3 m, second bay 3.8 × 3.5 m, side door to the alley |

**Beyond the play bounds**: the next blocks are the same kits at reduced detail out to about 300 m, and the El runs
on 150 m each way. Past that the city is painted cards sunk in the haze: low brick blocks, water tanks, a couple of
distant towers. No recognisable landmark.

**The four gameplay props** are hero objects: the player stands over them and looks at them on purpose.

| Prop (catalogue id) | What it is | Must show |
|---|---|---|
| `master_case` (0.9 × 1.05 × 0.6 m with the lid up) | A touring flight case: black laminate panels in aluminium edge extrusion, steel ball corners, butterfly latches, recessed handles, foam inside. On the foam, a gold 267 mm tape reel with its tape pack. A small display in the lid shows the grab progress. A beacon mast to 1.35 m with a gold lamp, so it shows over waist-high cover. An IPX tracker tag on the handle. | Scuffed laminate, dented extrusion, sticker ghosts, the reel immaculate. Lid shut and lamp off once taken. |
| `boombox` (0.6 × 0.35 × 0.25 m) | A portable stereo of an invented make beside each case. | Moving speaker cones, a level meter, worn buttons. |
| `propane_tank` (0.32 × 0.6 m) | A painted steel cylinder with a collar, a valve and a foot ring. | Chipped paint, rust at the foot ring, generic warning stencils; glows dull red while its fuse burns; a scorched foot remains. |
| `welding_rack` (0.9 × 1.6 × 0.5 m) | Two gas cylinders chained to a hand truck, with regulators, twin hose and a torch. | Cylinders in two colours with worn shoulders, cracked hose, soot. |

---------------------------------------------------------------------------------------------------

## 5. Signage and branding

### 5.1 Rules

- All shop names are the invented ones in `src/config/text.js`. No real brand, logo, product, agency mark or
  person appears anywhere, at any size, including look-alikes.
- IPX is the only real brand: the wordmark "IPX" and the address "IPX.EXCHANGE". No slogan, no invented IPX
  product or claim.
- The only real person connected to the game is the player character, who is never seen. "RULE" and "JA RULE"
  appear as lettering only. No face or likeness of anyone appears on a poster, mural or screen.
- A sign is an object before it is a picture: a carrier, a face, a light source, wiring, fixings. Model those,
  then apply the artwork.

### 5.2 Sign types as built objects

| Type | Construction | Typical size | By day | By night | Wear |
|---|---|---|---|---|---|
| **Lightbox (cabinet)** | Extruded aluminium box 150 to 250 mm deep, a 40 to 50 mm retainer frame, a translucent acrylic or flex face with film graphics, tubes or LED inside, a hinged service edge, a power whip. | 0.6 to 1.2 m tall, the width of the shop | Read by reflected daylight: a slightly glossy, slightly bowed coloured face. | Evenly lit face, 100 to 300 nits in engine. | Yellowed white, a dim band, cracks at a corner, insects along the bottom, rust runs from the fixings, a nest on top. |
| **Channel letters** | Individual aluminium letters 100 to 130 mm deep, acrylic faces in a 20 mm trim cap, LEDs inside, on a raceway box or fixed through the fascia. | Letters 0.3 to 0.6 m tall | Solid coloured letters with real depth and shadow. | Glowing faces, or a halo on the wall behind reverse letters. | One letter dark or flickering, faded faces, a letter askew, drill holes of an older sign. |
| **Open-face neon letters** | Metal pan letters with exposed glass tube inside. | Letters 0.4 to 0.6 m | Dark pan, pale tube. | The classic liquor-store red. | Blackened pan, a dead stroke, a dangling cable. |
| **Exposed neon** | Glass tube of 12 to 15 mm bent to the letterforms, on glass standoffs 30 to 40 mm off a painted metal pan, black blocking paint between letters, electrode boots and cable, a transformer box. Or in the window on a frame. | Tube strokes 0.25 to 0.5 m tall | Milky tubes on a dark pan; lit tubes show only in shade. | 400 to 2,000 nits in engine by colour, with a soft coloured wash on the pan and the wall. | Dust on the tubes, a section out, a faint buzz, flicker on a tired transformer. |
| **LED "neon" flex** | Silicone strip of 8 to 12 mm in a routed clear acrylic backer. | As neon | Flatter and more even than glass. | Very uniform, no dark electrodes. | Yellowing backer, a failed segment. |
| **Painted fascia or wall sign** | Sign-writer's enamel on plywood, sheet metal or straight on the brick or block. Gooseneck lamps above for the lit ones. | Fascia 0.6 to 1.0 m; wall adverts up to 12 × 3.2 m | Brush-edged letters that follow the surface: joints show through paint on brick. | Dark, or pooled light from the goosenecks. | Fading, peeling, an older sign ghosting through, drips, patched boards. |
| **Vinyl awning** | Welded square-tube frame, laminated vinyl skin laced or stapled to it, lettering in cut vinyl or paint on slope and valance. Some back-lit by tubes inside. | 4 m and more wide, 0.9 m drop, 1.3 m out | The shop's biggest colour field; lettering lists the wares. | Back-lit ones glow softly; others catch the sign above. | See 3.4. |
| **Banner** | Printed vinyl with hemmed edges and eyelets, tied with cable ties or rope. | 4.9 × 0.78 m on the sidewalk shed *(game)* | Wrinkles radiating from the eyelets, wind ripple. | Lit by the shed bulbs. | One corner loose, grime along the bottom. |
| **Stencil** | Spray paint through a cut stencil: soft edges, bridges in closed letters, overspray halo. | Letters 80 to 300 mm | "POST NO BILLS", garage numbers, "FLAT FIX". | Unlit. | Several misaligned passes, faded, half painted over. |
| **Enamel plate** | Porcelain enamel on steel, bolted at the corners: the transit plates ("188 ST"). | 4.6 × 0.82 m and smaller *(game)* | Deep gloss black, white grotesque type, a thin white rule above the text. | Lit by a small fixture. | Chips to rusty steel at bolts and edges, stickers. |
| **Street and traffic signs** | Aluminium blades and plates banded to poles and El columns. | Blade 0.58 × 0.15 m | Green blade "JAMAICA AV"; red-on-white parking rules. | Retroreflective glint. | Bent, stickered, faded on the sun side. |
| **Road-work signs** | Orange plates and barricade boards, plastic or plywood. | 1.3 to 3.4 m wide *(game)* | Orange `#E8641B` with black type. | Reflective. | Sun-bleached, tyre-marked, taped. |

### 5.3 The block's signs (names and colours from the web game; construction chosen here)

| Sign | Where | Width | Built as | Colours | Night |
|---|---|---|---|---|---|
| HOLLIS DELI & GROCERY · "OPEN 24 HRS · COLD CUTS · COFFEE · LOTTO" | N2, north side | front 11.0 m, sign 8.4 m | Lightbox with a flex face; green vinyl awning below listing the wares; LED "OPEN" in the window | yellow field `#F2C21A`, dark red letters `#8A1410`; awning `#1F5A3A` | Lit all night, with a bright interior |
| CROWN & FADE BARBER | N1 | 8.2 m | Exposed red glass neon on a black pan; navy canvas awning; a turning barber pole in a glass cylinder with chrome caps | neon `#FF3030`; awning `#1C2F5A` | Neon on, pole lit |
| 24 HR LAUNDROMAT | N1 | 8.8 m | Lightbox; full-height glass showing rows of machines | dark blue field `#0D3550`, off-white letters | Lit, with a cold 5,000 K interior |
| V&R AUTO BODY | the shop, over the roll door | 8.0 × 1.05 m | Lightbox with an opaque black face and translucent gold letters, so only the letters glow | black, gold `#F6C21A` | Letters lit |
| "TIRES · BRAKES · EXHAUST", "INSPECTIONS · 24 HR TOWING" | the shop's fascia: a corrugated steel band 29.4 × 1.3 m across the whole front | 5.4 and 5.6 m | Hand-painted on the corrugated sheet, the brush riding the ribs | cream `#E9E2CF` on the fascia's blue-grey `#1A2B3A` | Unlit |
| "FLAT FIX / NO APPOINTMENT", "USED TIRES" | shop front | 2.6 m, 2.0 m | Stencil | off-white; taxi yellow | Unlit |
| V&R AUTO BODY · "COLLISION · FRAME · PAINT" | tenement's east party wall, above the shop roof | 12 × 3.2 m | Painted straight on common brick, twenty years faded | cream on `#1D2F3F` | Unlit |
| CHECKS CASHED · "MONEY ORDERS · BILLS PAID" | S1 | 7.7 m | Green neon in open-face letters on a raceway; second line in white cut vinyl on the window band | neon `#55FF8A` | Neon on |
| 99¢ PIZZA · "SLICES ALL NIGHT" | S1 | 8.3 m | Lightbox; red vinyl awning; a counter window open to the street; white tile bulkhead | red field `#B3261E`, cream letters `#FFF1D0` | Lit, warm interior |
| PAWN & GOLD · "WE BUY GOLD · LOANS" | S2 | 6.0 m | Gold neon on a black pan; three hanging gold balls; open grille over the display windows of the vestibule | neon `#F6C21A` | Neon on |
| TAPES · RECORDS · CDs | S2 | 5.8 m | Cyan neon over a hand-painted wooden fascia; a window of record sleeves (all artwork invented) | neon `#35E0FF` | Neon on |
| GOLDEN BIRD CHICKEN · "FRIED · WINGS · BISCUITS" | S3, behind the shed | 9.0 m | Lightbox with a raised face | yellow field `#F2C21A`, red letters `#B3261E` | Lit, warm interior |
| WINES & LIQUORS | S3, behind the shed | 8.5 m | Red neon in open-face letters; bottles behind a grille (no real labels) | neon `#FF3030` | Neon on |
| LUCKY NAILS · "MANICURE · PEDICURE" | S3, behind the shed | 8.5 m | Pink LED flex in an acrylic box, above a solid roll gate that is down and tagged | pink `#FF3D9A` | Sign on, shop shut |
| The three S3 names again | on the shed parapet, facing the street | 4.9 × 0.78 m each | Printed vinyl banners tied to the hunter-green boards | chicken: red on yellow; liquor: red on black; nails: pink on dark plum `#2A0F1E` | Lit by the shed bulbs and the street |
| "SIDEWALK SHED · PERMIT 0214 · STORES OPEN DURING WORK", "POST NO BILLS" | shed skirt and hoardings | 5.6 m; 1.5 m | Stencil on green boards | off-white `#E6E4DC` | Unlit |
| PARK · "24 HR · PAY AT BOOTH" | lot | wall sign 5 × 1.6 m; pylon 1.8 m wide and 5.6 m tall with a 1.7 × 1.5 m neon face | Painted board on the wall; a pole-mounted cabinet with cyan neon at the entry | white on blue `#1F4F9A`; neon `#35E0FF` | Neon on |
| 188 ST · "ELEVATED · CLOSED 1 AM – 5 AM", "STATION CLOSED" | station mezzanine and stairs | 4.6 × 0.82 m; 1.5 × 0.42 m | Enamel plates | black, white | Small fixtures; green globes at the stair foot |
| ROAD CLOSED, SIDEWALK CLOSED, EL REPAIRS, DANGER | closures and shed | 1.3 to 3.4 m | Road-work plates and boards | orange `#E8641B`, black; white and red | Reflective |

The S3 signs sit at 2.9 to 3.7 m, level with the shed deck (2.95 m): the parapet hides them from the street, which
is why the banners exist, and a player on the deck stands beside them at knee height. They are close-up assets:
tubes, standoffs, electrode boots, cabinet seams and dust must hold at 0.5 m. The S3 front faces north and is in
shade all day, so its neon reads by day. The barber's neon is in direct sun and reads only at night. That is
correct; do not brighten it.

Secondary copy (posters, graffiti, stencils, plates) is in the web game (`src/mats/paper.js`, `src/level/*.js`) and
in the exported data. Graffiti is spray paint: soft-edged, dripping, layered, in the crew's oxblood `#8A1A22` for
"VULTURES" and "VLTR", gold for "RULE" and "INC".

### 5.4 IPX

- **One master.** Every IPX mark in the world comes from one vector file and one texture built from it. Until IPX
  supplies its real logo it is typeset: "IPX" in a heavy italic grotesque inside a thin lozenge (DESIGN section 6).
  Swapping in the real logo must be one file change (open question 3).
- **Screen colours are not paint.** Brand black `#0F1114` and white `#F4F2EC` are screen values. Printed or
  painted, black is no darker than `#2A2A2C` and white no brighter than `#E6E4DC`. Brand gold `#F6C21A` as paint or
  vinyl stays as it is; as metal it is gold metal (3.4). The same holds for every sign colour quoted from the web
  game in 5.3: the hex is the intent, the paint is clamped to 3.1.

| Placement | Built as | Size | Look |
|---|---|---|---|
| IPX truck livery | Cut vinyl on gloss black armour: the lozenge, a thin gold rule, "IPX.EXCHANGE"; a gold waist band; the lozenge again on the bonnet; yellow and black chevrons on the rear step | flank mark 3.5 × 0.875 m; band 110 mm; bonnet mark 0.8 × 0.33 m *(game)* | Immaculate. The cleanest object on the block. |
| Billboard | Printed vinyl stretched over panel sections on a steel frame with a grating catwalk, a caged ladder and four lamp arms | face 8.9 × 4.0 m, underside at 6.7 m, on two legs *(game)* | Black field, white lozenge, gold rule, the address. Strap wrinkles at the corners, panel seams showing through, an older poster edge at one side. |
| Mural | Masonry paint on the pawn building's common-brick side wall | 12 × 7.6 m *(game)* | See 5.5. |
| Bus-shelter advert | Back-lit poster behind glass in the shelter's advert box, both faces | 1.14 × 1.72 m *(game)* | The game's own one-sheet *(game)*: "IPX PRESENTS", the title in two lines ("MURDER" white, "INC." gold), "STARRING JA RULE", a gold rule, the lozenge, the address. Lettering only, no portrait. |
| Reel-case tracker tags | Moulded white plastic hang tag on a cable tie: lozenge, "TRACKER", a barcode pattern that encodes nothing | 80 × 40 mm | Clean, new. |
| Posters | Wheat-pasted paper | 0.6 × 0.9 m | Wrinkled, overlapped, torn. |

### 5.5 The mural and the billboard as hero pieces

**The mural** *(artwork from the web game)*: a night-blue field falling to maroon; a gold record rising like a sun
behind the El in silhouette, with gold and red rays; the IPX lozenge and "IPX.EXCHANGE" in white at the right; a
gold border; and "RULE" sprayed across it in gold, 6.4 m wide, by a surer hand than the tags around it. Build it
as a paint layer over the wall's tiling brick: the colour replaces the brick's, the brick's normal and height stay
at about 70 % (paint fills the joints a little), roughness 0.6 to 0.8. It must show sun-fade at the top, lime
pushing through in two or three places, peeling at the base, tags and posters across the lowest 2 m, and the
ghost outline of the building that once stood against this wall. By day it is in soft open shade with a warm fill.
At night it is lit by two gooseneck or flood fixtures from above (add them to the lamp data).

**The billboard**: the structure is the picture. Riveted or bolted steel legs with X bracing, a truss behind the
face, a grating catwalk with a pipe rail, lamp arms, a caged ladder, conduit down one leg. By day the face is in
raking sun (74° off its normal), so every wrinkle and seam reads. At night its four lamps light it from below:
brightest along the bottom edge, falling off toward the top.

### 5.6 Type

Use open-licence typefaces only (SIL Open Font Licence or Apache): Anton and Archivo (the game's own), Oswald,
Bebas Neue, League Gothic and Barlow Condensed for cabinets and stencils, Alfa Slab One for a slab, Yellowtail or
Pacifico for script neon. Hand-painted signs are lettered, not typeset: uneven stroke ends, optical spacing, a
slight slope. Shop signs on this block were made by three or four different sign shops over fifty years: vary
the faces and the spacing accordingly.

### 5.7 Hygiene checklist

- No real company, product or team: drinks, beer, cigarettes, lottery, payment cards, phone companies, delivery
  services, tyre and car makers, sneaker marks, gun makers, watch makers.
- No transit authority marks: no real route letter or number in its real colour, no agency logo. The game's own
  bullets (1, 2, 3 and IPX in the game's colours) are the only route bullets.
- No postal eagle, no city or police or fire insignia, no real taxi authority logo. The cab says "NYC TAXI" in a
  plain face with an invented medallion number *(game)*.
- Licence plates *(game)*: a plain pale plate with dark characters, "NEW YORK" in a plain face and a gold band
  along the bottom; the cab's is yellow with a navy band. No state artwork. The five plate strings are the game's
  (`docs/unreal/spec/05b-props.md` 2.4); none reads as a word or a name.
- The names that do appear, by design: the title "MURDER INC.", "JA RULE" and "RULE", "IPX" and "IPX.EXCHANGE", and
  real places ("NEW YORK", "NYC", "QUEENS", "HOLLIS", "JAMAICA AV"). Everything else is invented.
- Phone numbers use (718) 555-01xx. Web addresses other than IPX.EXCHANGE are not shown.
- QR codes and barcodes are patterns that do not scan.
- Paint and print colours stay inside the base-colour range of 3.1.

---------------------------------------------------------------------------------------------------

## 6. Characters, weapons and vehicles

### 6.1 The honest position

The Blender pipeline in this repository is scripted and runs headless. It is strong at architecture, steel,
props, signage and hard-surface objects such as guns and the drone. It is weak at organic form, cloth and the
sculpted surfacing of car bodies, which is where "photoreal" is hardest. Unreal-native sources close most of that
gap for free, but they need the client's Epic account and an editor, neither of which exists in the build
container. So each category below has a recommended source, and a placeholder that keeps the game playable until
it arrives.

### 6.2 The Goon

**Bar.** A 1.80 m masked gunman who reads at a glance in sunlight and at 40 m: a dark figure with oxblood accents,
a pale head and pale feet. Three outfits *(game)*: hoodie (hood up, full ski mask), puffer (beanie, bandana),
tracksuit (cap, ski mask). No skin shows except round the eyes. Real garment construction (seams, ribbing,
drawcords, zips, quilting), cloth that folds where a body bends, materials as in 3.4. He carries a compact SMG
with a weapon light, and a 0.7 m taped steel pipe on his back. The hood or mask fills the head hit sphere (radius
0.15 m): what you see is what you hit. Death is a physics ragdoll; up to six bodies stay.

| Option | You get | Cost | Verdict |
|---|---|---|---|
| A. All in Blender | Full control, no dependencies. | No money. Cloth and anatomy to this bar are weeks of a character artist's time per outfit; a scripted pipeline will not reach it. | Not for the final figure. |
| B. MetaHuman body and Unreal mannequin skeleton, outfits and masks authored in Blender over that body | Correct proportions, a production rig, and every mannequin-compatible animation set (Lyra, the Game Animation Sample). The face, the hardest part, is never seen. | Free under the Unreal licence (MetaHuman has been under the engine licence since 5.6). Needs an editor to create and export the body. Outfits are still real work: three garments, cloth-simulated and baked. Heavier at run time than a plain game character; strip the face and hair. | **Recommended.** |
| C. Mannequin as shipped | Works today with all animations. | Free. It is a robot, not a person. | The day-one placeholder: tint it black and oxblood, add a rigid pale mask and hood. |
| D. Marketplace characters | Finished, rigged figures in days. | Roughly 30 to 150 US dollars a pack. Mixed quality, mismatched style, possible brand look-alikes; must be re-textured to the crew colours and checked against 5.7. | The fallback if nobody can author outfits. |

Animation is the larger cost whatever the mesh: armed locomotion, crouch and cover, burst fire, the pipe rush, hit
reactions. Take locomotion and firing from Lyra, deaths from ragdoll, and buy or adapt one melee set.

### 6.3 The Buzzard

**Bar.** A believable armed quadcopter about 1 m across *(game)*: four rotors of 0.37 m, a hooked nose, a V tail,
a gimbal under the nose with the red eye and a slung gun, navigation strobes (red to port, green to starboard,
white on the tail). Injection-moulded shell with panel lines and screws, carbon arms, brushless motors with visible
windings, wiring and cable ties, oxblood panels and a sprayed crew stencil, dust and oil streaks behind each motor.
Spinning rotors are a blurred disc plus motion blur.

Source: **author it in Blender** (recommended; it is exactly what the pipeline is good at). Rigid Nanite parts on
an actor: body, four rotors, gimbal. No dependency, no licence question. A marketplace drone would cost 20 to 80
US dollars and still need the gun, the eye and the crew colours.

### 6.4 First-person arms and weapons

**Bar.** The most-seen pixels in the game (2.11). Black gloves of an original design (stitched panels, a padded
knuckle), bare brown forearms, a gold watch on the left wrist, a gold curb-link bracelet on the right. The CHOPPER
(a compact wood-and-steel automatic carbine, charging handle on the left) and the NINE (a two-tone 9 mm pistol
with gold on the trigger and the magazine base). Part dimensions are in `docs/unreal/spec/02-weapons-combat.md`;
materials in 3.4; texel density in 4.5. Sights line up for real when aiming. Every moving part moves: bolt,
charging handle, trigger, slide, hammer, magazine, the top round.

| Part | Options | Recommendation |
|---|---|---|
| Weapons | Blender (original designs are required anyway); marketplace guns (50 to 200 US dollars, real-make look-alikes) | **Blender.** |
| Gloves, watch, bracelet | Blender; marketplace first-person arms (20 to 100 US dollars, generic) | **Blender.** The watch has an unbranded dial. |
| Forearm skin | Blender-authored skin (hard to get right); MetaHuman forearms (free, production skin shading) | **MetaHuman forearms** under Blender-made gloves; the mannequin arms from Unreal's first-person template as the placeholder. |
| Animation | The web game poses the arms procedurally | Port those poses (the weapons spec); no motion capture needed. |

**Rule's shadow.** The web game gives the player no body and no shadow. Under a hard sun that stands behind him
for most of the run, a missing shadow is the first thing that reads as fake: his shadow should lie 1.4 m long on
the road ahead. Give the player a hidden body that only casts a shadow (the mannequin skeleton with the armed
locomotion set, in a plain hooded silhouette holding the current weapon). No visible legs, no reflection in shop
glass or car paint (open question 12).

### 6.5 Vehicles

**Bar.** Parked vehicles are the main cover: the player crouches against them for most of the game, so they are
seen from 0.5 m. Present-day shapes, invented makes, no badges. Correct construction: panel gaps, lamp units with
depth, glass with a border and thickness, wheels with brake discs behind them, an interior that reads through the
windows, an underside that reads from a crouch. Wear as in 3.4. They sit on their tyres with weight (tyres bulge),
at slightly different angles to the kerb.

| Option | You get | Cost | Verdict |
|---|---|---|---|
| A. All in Blender | Invented makes by construction, sizes exact. | No money. Car surfacing to this bar is three to six weeks of a vehicle artist's time per car; scripted modelling gives a plausible but simpler body. | Use for the special vehicles and for placeholders. |
| B. City Sample Vehicles (Fab) | Thirteen driveable, unbadged, production-quality vehicles made by Epic, with interiors and damage. | Free. Licensed for Unreal Engine projects only. A multi-gigabyte download through the client's Epic account. Sizes must be matched to the catalogue. The shapes echo real cars: check each against 5.7 and restyle grille, lamps and badge areas where one is too close to a real model. | **Recommended for the ordinary fleet.** |
| C. Marketplace vehicle packs | Variety. | Roughly 50 to 400 US dollars. Real-make look-alikes are common: a trade-dress risk. | Avoid. |

| Vehicle (catalogue id) | Box L × H × W (m) | Collider tops (m) | Source |
|---|---|---|---|
| `sedan` | 4.6 × 1.45 × 1.85 | body 1.08, cabin 1.45 | City Sample, repainted in the fleet colours |
| `taxi` | 4.7 × 1.55 × 1.85 | body 1.08, cabin 1.45; roof light above | City Sample sedan plus a Blender kit: roof light, livery, partition |
| `suv` (Rule's is black) | 4.9 × 1.82 × 2.0 | body 1.24, cabin 1.78 | City Sample |
| `pickup` | 5.3 × 1.8 × 2.0 | body 1.27, cabin 1.78 | City Sample |
| `van`, and the Vultures' van with its doors open | 5.2 × 2.2 × 2.0 | 2.14 | City Sample if its rear doors open; otherwise Blender |
| `box_truck` | 7.4 × 3.3 × 2.45 | cab 2.28, box 3.30 | City Sample or Blender (a box is easy) |
| `burned_car` | 4.5 × 1.3 × 1.8 | body 0.96 | Blender, from a sedan body |
| `ipx_truck` | 6.8 × 3.0 × 2.5 | cab 2.58, vault 2.86; the extraction point | **Blender**: a unique hero, flat armour plate suits the pipeline |
| `motorbike` | 2.0 × 1.1 × 0.7 | 0.95 | Blender (a delivery moped), or a marketplace model checked against 5.7 |
| `food_cart` | 2.4 × 2.25 × 1.4 | 1.25 | Blender |
| The train (five cars, 15.4 × 3.55 × 2.9 m each) | n/a | n/a | Blender: unbranded stainless cars, trucks and shoes modelled, amber destination text of our own |

Whatever the source, each vehicle is scaled to its box within 3 % and its body and cabin are checked against the
collider tops: a sourced sedan whose bonnet is lower than about 0.95 m leaves the player's cover invisible. The
web game's car glass is near-black; the rebuild uses a medium tint, so every car needs its simple interior. Until
the Fab vehicles are in the project, Blender proxies of the same names and sizes stand in.

---------------------------------------------------------------------------------------------------

## 7. Effects, atmosphere and audio

Reference for every effect is slow-motion footage of the real thing. Effects are lit by the scene (sun, shade,
lamps), cast shadows where they are dense, and never glow by default.

| Effect | What it really looks like | Bar |
|---|---|---|
| **Muzzle flash** | One to three milliseconds: a single frame. The CHOPPER's booster throws a ball with side jets; the NINE a small bloom above the slide. | One frame of flash (flipbook variants, random roll), a one-frame light that casts first-person shadows, a wisp of grey gas that drifts with the wind, heat shimmer after a long burst. Never a lingering fireball. Brass ejects as modelled casings that bounce, ring and stay a few seconds. |
| **Tracers** | A thin streak. | Levels and colours as 2.7. A faint heat ripple behind it by day so it shows against a bright wall. |
| **Impacts** | Each surface answers differently. | Brick: orange-red dust and chips, a pale pock. Concrete: grey-white dust, a crater showing aggregate. Asphalt: dark grit, a small divot. Car body: a one-frame spark, a dimpled hole with a bright ring and flaked paint. Car glass: a starred, whitened crater; it does not shatter, because car glass stops rounds in the game. Shop glass: a starred hole. Wood: pale splinters. Dirt: clods. Water: a splash. Chain-link: a spark and a ring of the mesh. Sandbag: a trickle of sand. A Goon: a puff of cloth fibre and dust, no blood (DESIGN section 1). Decals are parallax or mesh-backed holes, not flat stickers. |
| **Explosions** | Propane: a roaring jet for the fuse (1.6 s), then a rolling fireball 4 to 5 m across that lifts and blackens in under a second. Welding rack: sharper and whiter, with a shower of sparks. | Flipbooks rendered from a fluid simulation, lit sparks with collision, tank halves and shrapnel as meshes, a dust ring racing along the ground, a scorch decal, a smoke column for 6 to 10 s leaning with the wind, a flash light that falls over 0.3 s, shop glass rattling in its frames. |
| **Steam** | White when the sun is behind it, grey when lit from the front, the colour of the nearest lamp at night. | Volumetric-lit sprites or a fluid sprite sheet rising about 6 m and shearing in the wind; thin (you see through it). |
| **Dust and grit** | The El sheds rust flakes and dust when a train passes; a car lot is dusty. | Curtains of fine dust in the bars of sun under the deck, heavier flakes falling straight; a puff at the feet on landing; dust kicked by impacts and blasts hangs in the shafts of light. |
| **Heat haze** | Shimmer over sunlit asphalt and car roofs beyond about 30 m, over the idling truck's exhaust, the food cart, the propane jet. | A subtle refraction, by day only, never over the near field. |
| **The train** | Five stainless cars at 16.5 m/s, every 40 to 70 s, alternating direction. | Real meshes casting real shadows: by day the ladder of light on the avenue goes dark as it passes. Blue-white arcs at the third-rail shoe that light the steel for a frame or two. At night its windows strobe light through the ties. Grit falls, lamps under the deck sway, puddles ring, loose paper gusts, pigeons break, the camera trembles. |
| **Open hydrant** | A hard jet arcing about 4 m, breaking to mist. | Lit spray with a faint rainbow when the sun is behind the viewer, a spreading wet patch, a stream along the gutter to the catch basin carrying a cup and leaves. |
| **Pigeons** | Groups on flanges, cornices and the billboard catwalk, by day. | Perched birds that shuffle; flocks that break and wheel on gunfire and trains, then settle. Their guano is already in the textures under every perch. |
| **Litter** | A day's worth. | Loose paper and a plastic bag that tumble in the wind and the train's gust; cups, flattened cans and butts along the gutter (scattered meshes and decals); a bag snagged in the chain-link; broken glass that sparkles at the burned car. |
| **Neon and lamps** | Tired tubes flicker; a sodium lamp cycles off and on. | Two tired lamps and one flickering stroke of neon, no more. |
| **Player feedback** | n/a | Hit flash at the screen edge, low-health desaturation and rim, as the player spec. Kept subtle: the world is the picture. |

Sources: flipbooks rendered from Blender fluid simulations plus Niagara for sparks, debris and lights
(recommended, no dependency), or a purchased simulation-based pack if those fall short. Every effect has a lower
setting (9.3).

**Audio note.** A photoreal picture with synthetic sound reads as fake. The web game's audio is all generated in
code and stays the reference for what plays, when and how loud (`docs/unreal/spec/07-ui-audio.md`). The rebuild needs
recorded-quality sources for the same list: weapon shots with separate tails for the open avenue, under the steel
deck (a hard flutter between deck and street), inside the shop (a big hard room) and in the alley (a slap);
per-surface footsteps and impacts; the train as the loudest thing on the block; neon buzz, transformer hum, air
conditioners, pigeons, a far siren, traffic wash. The music is the game's own boom-bap composition at about 92 BPM
with intensity stems: render or re-record it, never replace it with a real song or samples.

---------------------------------------------------------------------------------------------------

## 8. Priorities and definition of done

### 8.1 Build order

Every module and prop, with its mesh name, size, count and gameplay role, is listed in
`docs/unreal/spec/05-level.md` 5.1 and `docs/unreal/spec/05b-props.md` 5.1 (briefs in `docs/unreal/spec/assets/`).
Where those lists give a priority, the tiers below refine it: Tier 0 comes first whatever else is ready.

**Tier 0: the benchmark photograph.** One bay of the avenue, finished, before anything else is started. It is hero
view H1 and it proves the whole look.

| # | Asset | Why first |
|---|---|---|
| 1 | El kit: column with base and pedestal, bent, girder span, deck span, bracing, lamp | The block's signature and its light pattern. |
| 2 | Ground kit: avenue asphalt with patches and paint, steel-faced kerb, sidewalk flags, manhole, catch basin | Half of every frame. |
| 3 | Red-brick tenement bay kit with a fire escape and cornice | The texture showcase in raking sun. |
| 4 | One storefront complete: HOLLIS DELI & GROCERY (cabinet sign, awning, gate, glass, door, interior depth) | Proves signage by day and night. |
| 5 | One `sedan` and the `taxi` | Proves cover props at 0.5 m and car paint. |
| 6 | DAY and NIGHT rigs with the calibration props | Everything else is judged in them. |
| 7 | CHOPPER and the arms | Always in frame. |

**Tier 1: the playable block.**

| Group | Assets |
|---|---|
| Architecture | Tan-brick taxpayer row (S3), V&R Auto Body shell and interior, deli block, station house block, pawn and records block, rear-lane garages and loading dock, the sealed station and its stairs |
| Street structures (hard cover and sightline breaks) | The sidewalk shed, hoardings, the two rolling repair scaffolds with their debris netting, the hoist tower, the two shut kiosks, the tyre cage, the produce stand, the utility dig with its steam stack, the site shanty |
| Yards | Fence kit (the Cage, vacant lot, alley gate), court surface, hoops, bleachers, flood poles, lot booth, low wall and rail, barrier arm, PARK pylon, light poles, billboard, mural |
| Vehicles | `suv`, `van` (and the Vultures' van), `box_truck`, `pickup`, `burned_car`, `ipx_truck` |
| Cover props | `jersey_barrier`, `dumpster`, `trash_bags`, `milk_crates`, `traffic_barrel`, `newspaper_box`, `mailbox`, `hydrant` and `hydrant_open`, `bus_shelter`, `food_cart`, `pallet_stack`, `crate_wood`, `tire_stack`, `oil_drum`, `sandbags`, `barricade` |
| Gameplay props | `master_case` with the reel and boombox, `propane_tank`, `welding_rack` |
| Characters | Goon (three outfits), Buzzard, NINE |
| Signs | All of 5.3 |
| Effects | Muzzle, tracers, impacts on the six main surfaces, both explosions, the train |

**Tier 2: the finish.** Shop interior props (lifts, tool chests, workbench, hoist, shelf racks, compressor, vending
machine); remaining street furniture (lamps, signals, signs, meters, bench, planter, tree, phone pedestal,
bollards, cones, shopping carts, mattress, generator, flood stands, portable toilet); rooftops (water tanks, air
conditioners, bulkheads, parapets); the next blocks and the El beyond the closures, the far skyline; decal sets
(posters, graffiti, stains, gum, oil, cracks); pigeons, litter, steam, the hydrant; wet-street states; night
polish.

### 8.2 Definition of done

**Every asset**

- [ ] Real size, checked against 4.1 or its brief; fills its catalogue box within 5 %; cover height within 2 cm.
- [ ] Pivot, forward axis and name follow section 0; scale applied; the pipeline's validator passes with no error.
- [ ] Every visible edge bevelled (4.2); relief over 5 mm is geometry (4.3); no flat-shaded or stretched face.
- [ ] Closed, with real thickness; nothing intersects; glass is a separate slot.
- [ ] Base colour inside 3.1 and its family's range; metallic is 0 or 1; roughness varies with a cause.
- [ ] `Wear` attribute present and painted from causes (3.3); at least two kinds of history visible.
- [ ] Deviates from perfect as 4.4 asks; at least two variants or mask sets if it appears more than three times.
- [ ] No real brand, mark, person or scannable code (5.7).
- [ ] Preview renders in `art/previews/`: day rig, night rig, and a close-up at 0.5 m, beside a 1.8 m figure.
- [ ] In engine: correct in both scenarios, no light leak, no shadow artefact, reads at its real viewing distances.
- [ ] Triangle count and texture sets inside 4.5 and 4.6; listed in the manifest.

**Tiling sets, in addition**

- [ ] Declared tile size is right: the pattern measures true (three brick courses = 203 mm).
- [ ] Seamless; no feature that reveals the repeat across a 20 m wall with macro variation on.
- [ ] Height map present; wetness and all four wear channels respond correctly on a test wall.
- [ ] Passes the regional filter (3.2).

**Architecture modules, in addition**

- [ ] Snaps to its neighbours with no gap or overlap; corner and reveal strips carry modelled brick.
- [ ] Windows have depth behind them; by day they reflect, at night a believable share is lit.
- [ ] Leak streaks start at real sources (sills, anchors, copings, air conditioners).
- [ ] Lumen-friendly: separate pieces, 20 cm walls, thin parts flagged (4.7).

**Signs, in addition**

- [ ] Built as its type in 5.2: carrier, face, light source, wiring, fixings.
- [ ] Copy and colours match the web game exactly; type is an open-licence face.
- [ ] Legible at 40 m by day; by night it has its emissive level (2.7), its backing glow and its paired light.

**Vehicles, in addition**

- [ ] Invented make, no badge; plate as 5.7; interior and underside read.
- [ ] Sits with weight; dust, grime and one specific piece of damage; paint from the fleet colours.

**Characters and first-person assets, in addition**

- [ ] Reads at a glance at 40 m in sun and in shade under the El; head and feet are the pale accents.
- [ ] Black cloth holds its folds in full sun (never crushed) and under a sodium lamp.
- [ ] Deforms without collapse at shoulder, elbow, knee and wrist through the full animation set.
- [ ] First-person: holds as a still at the gameplay field of view at 1440p with the gun half in sun.

**Effects, in addition**

- [ ] Lit by the scene in both scenarios; right duration against reference footage; readable in play.
- [ ] Has a lower-cost setting; no more than the overdraw budget at its densest frame (9.2).

**A lighting scenario**

- [ ] The calibration checks of 2.12 pass.
- [ ] All eight hero views are signed off against their reference boards.
- [ ] The doorway test (2.5) passes both ways; at night no playable spot is under 2 lx.
- [ ] Frame time is inside 9.2 on the target card.

---------------------------------------------------------------------------------------------------

## 9. Performance targets and scalability

Nothing here has been measured: there is no editor or GPU in the build container. These are planning budgets to
confirm with `stat unit`, `stat gpu`, the GPU profiler and the Nanite, Lumen and virtual-shadow-map views on the
target machine.

### 9.1 Targets

| Tier | Hardware | Target |
|---|---|---|
| **Target ("High")** | A mid-range current desktop card with 8 to 12 GB (the class of an RTX 4060 or 5060, RX 7600 XT or 9060 XT, Arc B580), a six-core processor, 16 GB of memory, a solid-state drive | 60 frames per second at 1080p output (TSR from about 67 %), or at 1440p output from about 58 % |
| "Epic" | A card with 12 to 16 GB (the class of an RTX 4070 Ti or 5070) | 60 frames per second at 1440p from 75 %, or at 4K from 58 %; hardware ray tracing with hit lighting; all lamps shadowed |
| "Medium" | Older or 6 to 8 GB cards | 60 frames per second at 1080p from 58 %; reduced Lumen, or Lumen Lite on Unreal 5.8 |
| "Low" | Any DirectX 12 card that runs Nanite | 30 to 60 frames per second at 900p to 1080p from 50 %; no Lumen |

The level is one block, 92 × 68 m, with a fixed sun: a small, dense scene is the best case for this technology.
Spend the budget on density and light quality, not on distance.

### 9.2 Budgets at the target tier

| GPU time per frame (16.7 ms available) | Day | Night |
|---|---|---|
| Nanite visibility and base pass | 3.0 ms | 3.0 ms |
| Shadows | 2.0 ms (the sun) | 3.5 ms for shadows and direct lighting together, with MegaLights |
| Direct lighting | 0.8 ms | (included above) |
| Lumen global illumination | 3.5 ms | 3.0 ms |
| Lumen reflections | 1.2 ms | 1.8 ms (wet road) |
| Sky, clouds, volumetric fog | 1.2 ms | 0.8 ms |
| Translucency and effects | 1.0 ms (2.5 ms at an explosion) | 1.0 ms |
| Skinned meshes, glass, decals | 0.8 ms | 0.8 ms |
| TSR and post-processing | 2.0 ms | 2.0 ms |
| **Total** | **15.5 ms** | **15.9 ms** |

Without MegaLights the night scene fits only inside the shadow budget of 2.8 (24 shadowed lamps near the player).

| Content | Budget |
|---|---|
| Video memory in use | 6.5 GB at 1080p, so 8 GB cards do not page |
| Texture streaming pool | 3 GB |
| Tiling sets | about 48 in the shipped level (the scan catalogue has about 80 candidates; choose) |
| Unique Nanite source geometry | 60 million triangles, under 1 GB on disk |
| Non-Nanite triangles in view | 1.5 million |
| Draw calls outside Nanite | 1,500 |
| Local lights at night | 80 in the level; without MegaLights 24 shadowed near the player, 4 to 6 overlapping per pixel |
| Translucent overdraw | four layers at most over any quarter of the screen |
| Enemies | at most 13 alive at once, from pools of 12 Goons and 8 Buzzards *(game)*; six bodies |
| Processor | game thread 6 ms, render thread 6 ms |

### 9.3 What scales, in this order

| Step | Low | Medium | High (target) | Epic |
|---|---|---|---|---|
| Internal resolution (TSR) | 50 % | 58 % | 67 % | 75 % |
| Global illumination | off: sky light, distance-field and screen-space occlusion, and authored fill lights under the El and in the shop | Lumen Lite (5.8) or low-quality software Lumen | Lumen, hardware tracing if supported | Lumen, hardware tracing, higher final gather |
| Reflections | screen-space and captures | as global illumination | Lumen, surface cache | Lumen, hit lighting, two bounces |
| Sun shadows | on, lower resolution | on | on | on, more samples |
| Local-light shadows | 8 | 12 | 24, or MegaLights | all, MegaLights |
| Volumetric fog and clouds | none; painted sky, lamp-cone cards | low fog, painted sky | fog, low clouds | fog, clouds |
| Nanite detail (pixels per edge) | 4 | 2 | 1 | 1 |
| Texture pool | 1.5 GB | 2 GB | 3 GB | 4.5 GB and up |
| Effects | 40 % of the particles, no lights from sparks | 70 % | 100 % | 100 %, denser smoke |
| Clutter (litter, gum, pigeons, decals) | 30 % | 60 % | 100 % | 100 % |
| Character detail | one level lower | one level lower | full | full |
| Glass | opaque with a reflection capture | translucent | translucent, traced reflections | the same |

Because Low has no dynamic bounce, the fill under the El and in the shop is authored for it: a small set of
unshadowed lights tagged for that tier only, matched by eye to the Lumen result.

**Never scaled away**, because they are gameplay or identity: the sun's shadows of the El (the bars of light),
enemy readability (pale mask, tracers, muzzle flashes), sign legibility, cover silhouettes, the train.

### 9.4 Rules that protect the frame rate

- Static, opaque, closed meshes are Nanite. No Nanite on thin lattices of wire or on anything with a translucent
  slot.
- One material per surface family: instances and the `Wear` mask make the variety, not new materials.
- Repeated things are instances of one mesh (ties, rivets inside a column, slats, fence panels, bricks in a
  corner strip).
- Only the train, the truck doors, enemies and effects move. Everything else is static, so shadow caching holds.
- Alpha-tested surfaces are few and large (chain-link, scrim), never stacked.
- Every lamp has a real radius and a sensible range; no light reaches further than it lights.
- Emissive carries appearance; lights carry illumination (2.7).

---------------------------------------------------------------------------------------------------

## 10. Open questions

For the client or the art lead. Each has a default, used until someone decides otherwise.

1. **Platform and minimum card.** The port targets Unreal 5.8 (`docs/unreal/spec/00-unreal-scout.md`), which
   suits the look: MegaLights is production-ready there and the night scene wants it. Which platforms, and what
   is the weakest card that must run it? Default: PC, the tiers of 9.1.
2. **Epic-account content.** May the project depend on City Sample Vehicles, MetaHuman, Lyra and the Game Animation
   Sample (free, Unreal-only licences), and on Megascans (reported free again since 5 November 2026)? Someone with
   the client's Epic account must download them; the build container cannot reach `fab.com`. Default: yes, with
   Blender proxies and the Poly Haven scans until they arrive.
3. **IPX identity.** The real logo as a vector, the brand colours and typeface, and sign-off on the truck livery,
   billboard and mural artwork. Default: the typeset lozenge.
4. **Rule's arms.** Skin-tone reference for the star's forearms; whether tattoos appear (they need his approval
   and the tattoo artists' clearance); the design of the watch and bracelet. Default: no tattoos, an unbranded
   gold watch.
5. **First-person texel density.** The brief fixes 1024 px per metre; the camera needs about four times that on
   the surfaces it reads. Default: 1024 as the floor, one 4096² set per weapon (4.5).
6. **The sun.** Keep the web game's sun (52°, bearing 244°), or move to the true 4:15 PM sun (45°, 260°)? The
   true sun would graze the north fronts even more thinly and halve the sideways shift of the deck's shadow, so
   it changes the play space. The Blender look-dev rig currently defaults to 45° / 235°. Default: keep the game's.
7. **Night colour.** Keep sodium orange under the El although the real borough is now LED? Default: yes.
8. **Chain-link.** Alpha-tested cards everywhere, or real wire on the panels the player can touch? Needs an
   in-engine test of aliasing and cost. Default: cards.
9. **Extra texture channels.** Recolourable props (cars, dumpsters, mailboxes, awnings) need a paint mask and
   decals need opacity. Proposal: the alpha of `T_<Set>_BC` carries it. Default: one base colour per colour
   variant until the pipeline adopts it.
10. **Daylight tracers.** Accept tracers brighter than reality by day for readability (2.7)? Default: yes.
11. **Characters if outfits cannot be authored.** Is there a budget for marketplace or commissioned figures
    (6.2 option D)? Default: placeholders stay until decided.
12. **The player's shadow.** A hidden shadow-casting body for Rule (6.4)? It costs a third-person animation
    set for a figure nobody sees. Default: yes to the shadow, no to visible legs and reflections.
13. **Reference photography.** Who collects the reference boards for the eight hero views, and where are they
    kept? Default: the art lead, outside the repository.

---------------------------------------------------------------------------------------------------

## 11. Sources for the time-sensitive claims

Checked by web search in November 2026. The pages themselves could not be opened from the build container
(`www.unrealengine.com` and `dev.epicgames.com` are outside its allowed network), so confirm each before relying
on it. Everything else in this document is physics, standard dimensions, the web game, or art direction.

| Claim | Where |
|---|---|
| Unreal 5.8 (June 2026): MegaLights production-ready, Lumen Lite in beta, last planned major 5.x release | [Unreal Engine 5.8 is now available](https://www.unrealengine.com/news/unreal-engine-5-8-is-now-available), [5.8 release notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes) |
| Unreal 5.7 (November 2025): MegaLights beta, Substrate production-ready | [Unreal Engine 5.7 is now available](https://www.unrealengine.com/news/unreal-engine-5-7-is-now-available) |
| Low and Medium scalability switch Lumen off by default; High targets 60 frames per second on consoles, Epic 30 | [Lumen performance guide](https://dev.epicgames.com/documentation/unreal-engine/lumen-performance-guide-for-unreal-engine) |
| Emissive is expressed in cd/m², exposure in EV100 | [Using physical lighting units](https://dev.epicgames.com/documentation/unreal-engine/using-physical-lighting-units-in-unreal-engine) |
| MetaHuman is licensed under the Unreal Engine licence from 5.6 | [MetaHuman licence](https://www.metahuman.com/license) |
| City Sample Vehicles: 13 driveable vehicles, licensed for Unreal Engine products only | [Fab listing](https://www.fab.com/listings/2909157b-ddfa-4cef-a925-69dc2467021f) |
| Megascans free again on Fab (announced 5 November 2026; Fab Standard Licence covers any engine or tool) | [CG Channel](https://cgchannel.com/2026/11/epic-has-made-megascans-free-again-for-good-this-time), [Digital Production](https://digitalproduction.com/2026/11/13/quixel-megascans-free-again), [Creative Bloq](https://creativebloq.com/news/the-worlds-biggest-library-of-scanned-assets-for-3d-artists-is-now-free-and-it-seems-that-this-time-its-for-good) |
| New York street lamps: LED, 3,000 K specified now, 4,000 K installed earlier across Queens | [NYC street design manual, lighting](https://www.nycstreetdesign.info/lighting/photometric-standards) |
| Sidewalk sheds: hunter green was the rule until 2025 | [Local Law 47 of 2025](https://www.nyc.gov/assets/buildings/local_laws/ll47of2025.pdf) |
| Old solid roll-down gates remain legal until replaced (deadline repealed June 2026) | [NY1](https://ny1.com/nyc/all-boroughs/news/2026/07/02/city-council-votes-to-repeal-deadline-for-new-roll-down-security-gates) |
