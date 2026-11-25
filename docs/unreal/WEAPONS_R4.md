# Weapons round 4: six guns that read apart, and a parts kit (the art hand-off)

For an engineer who has not seen this work. The owner played the build on E3DS and wrote: "all the guns look the same and no
attachments are able to be added to the guns". Both were true. Four of the five guns the rack offered were ONE purchased M4-style
carbine in three handguard lengths, the RATTLER had no first-person mesh (hidden), and the CHOPPER and the NINE had no mounts, so the
Workbench said "No attachments". This round builds the missing art. Every shape is our own design in the manner of a class of firearm;
every marking is invented (no maker, model, serial format or logo of a real firearm).

Companion pages (read them with this one): `WEAPONS_R4_DATA.md` (what the data engineer wrote and where it differs from the
specification), `WEAPONS_R4_TESTS.md` (the tests the data makes false), `LOADOUT.md` 3.2, 3.3, 6.1 to 6.8 (the design),
`DECISIONS.md` 2026-11-25 (the CHOPPER is back on slot 1), `PROGRESS.md` (the dated notes of each lane), and
`art/blender/PROGRESS.md` and `art/blender/README.md` (the Blender side, the commands, the weaknesses of each asset).

**Nothing in this round was run in Unreal.** Everything below is proved in Blender (ray casts, pose proofs on the re-imported files)
and by reading the code and the data. Where this page says "must" or "check", it is for the box.

## 0. The archive and its state

| | |
|---|---|
| File | `art/out/fp-guns-r4.tar` (git-ignored, on the build machine only) |
| Size | 300,011,520 bytes (286.1 MiB) |
| sha256 | `6a521cf3653be7ebc98f976f7ee17a69442f00ae92b3fed191453a7dedbd5741` |
| Members | 133 files: 32 GLBs (5 guns, 10 magazine and top-round pieces, 2 casings, 15 part files), 16 texture sets (BC, N, ORM, E where it exists, `set.json`), 17 icons and pips in `ui/` (5 gun silhouettes, 12 part pips), `manifest.json`, `weapons_r4.json` |
| Layout | the same as `fp-guns.tar`: `glb/`, `textures/<Set>/T_<Set>_{BC,N,ORM[,E]}.png`, `ui/`, `manifest.json`, `weapons_r4.json` (members start with `./`) |
| Made by | `bash tools/box/fp/fp-art.sh packr4` (three tars: guns 230.5 MB, rattler 48.0 MB, parts 21.5 MB) merged into one tar with the duplicate names removed; the three tars stay in `art/out/` and carry the same bytes |

Carrying it. The storage refuses bodies over about 500 MB, and the convention of `send-art.sh` is parts of at most 240 MB. The single
tar is 300 MB, so it should go as one upload (under 500 MB) or, if a limit bites, as the three `fp-weapons-r4-<group>.tar` that are already
under 240 MB each (the guns tar is 230.5 MB: the next addition must go to its own tar). On the box:
`FP_IN=/project/ue/fp-in-guns bash tools/box/fp/fp-art.sh unpack <url> [url ...]`, then `MI_FP_IN=/project/ue/fp-in-guns bash tools/box/fp/import-chars.sh r4`
with the editor stopped.

GLBs in the archive: `SK_Chopper`, `SK_Nine`, `SK_Shorty`, `SK_Stretch`, `SK_Rattler`; the 10 magazine pieces of the five guns (`SM_Weapon_<Gun>Magazine` and
`_TopRound`); `SM_Weapon_CasingRifle` and `_CasingPistol`; the 15 part files (the 12 parts `SM_Part_*` and the 3 top rounds of the extended magazines). Texture sets: `Chopper`, `Chopper_Front`, `Chopper_Furniture`, `Nine`, `Shorty`, `Stretch`, `Rattler`, the five magazine sets,
the two casing sets, `Weapon_Parts`, `Weapon_PartsMags`. `uv_cache.npz` is deliberately not in it.

Clean-state proof (2026-11-25, 15:44 to 15:50 UTC, a fresh process per step): `build.py build weapons_shorty|weapons_stretch|weapons_rattler|weapons_parts --export`
and `_weapons_patch.py --force` re-wrote every gun, magazine and part from the committed code. Byte comparison of the 31 re-exported GLBs against the files that
were there before: all identical. Then the proofs: `_weapons_check.py` (`Chopper: ALL FIXED POINTS KEPT`, `Nine: ALL FIXED POINTS KEPT`),
`_weapons_check_shorty.py`, `_weapons_check_stretch.py`, `_weapons_check_rattler.py` (each `ALL FIXED POINTS KEPT`), `_weapons_check_parts.py`
(`ALL MOUNTS KEPT`, 153 checks, every compatible part on every gun, no crossed triangle) and `_weapons_r4_contract.py` (`CONTRACT KEPT`). A 4K texture
re-bake was not repeated: the sets and their UV caches are the final ones of the review-fix pass, and a re-export reproduces them bit for bit.

## 1. Every asset

Coordinates everywhere: gun space = Blender space, X along the bore (muzzle at +X), Y left, Z up, metres; Unreal centimetres are (x, -y, z) x 100.
Every skinned gun is ONE mesh, every vertex weighted 1.0 to one bone, every joint at rest with the gun's axes (local X = bore); sockets are bones
without vertices (`deform = false`, parent `body`/`frame`). The magazine bone is an attach bone with no vertices: the magazine is a separate static
mesh authored in place in the gun's space, carried by that bone.

### 1.1 The guns

| Gun | Asset | Triangles | Sets (one slot each unless noted) | Deform bones (root first) | Socket bones |
|---|---|---:|---|---|---|
| CHOPPER (pack-free, back on slot 1) | `SK_Chopper` | 150,487 (over the 120k rule, kept: proven) | `Chopper`, `Chopper_Furniture`, `Chopper_Front`, three 4K sets, slots `M_Chopper`, `M_Chopper_Furniture`, `M_Chopper_Front` | body, bolt, trigger, selector, magazine, **Booster**, **FrontSight** (the last two new) | Muzzle, Eject, SightRear, SightFront, RecoilPivot, MagHinge, Palm_R, Palm_L, **Optic**, **MuzzleMount**, **Underbarrel** (new) |
| NINE | `SK_Nine` | 86,033 | `Nine` 4K (`M_Nine`; BC N ORM E A) | frame (root), slide, barrel, trigger, hammer, slide_stop, magazine | Muzzle, Eject, SightRear, SightFront, RecoilPivot, Palm_R, Palm_L, **Laser**, **MuzzleMount**, **MagHinge** (new) |
| SHORTY | `SK_Shorty` | 67,168 | `Shorty` 4K (`M_Shorty`; BC N ORM, E = tritium inserts) | body, bolt, trigger, selector, magazine, MuzzleDevice, IronsFront | Muzzle, Eject, SightRear, SightFront, RecoilPivot, MagHinge, Palm_R, Palm_L, Optic, MuzzleMount, Underbarrel, Laser |
| STRETCH | `SK_Stretch` | 61,792 | `Stretch` 4K (`M_Stretch`; BC N ORM, no E) | body, bolt, trigger, selector, bolt_catch, magazine, bipod, MuzzleDevice, IronsRear, IronsFront | Muzzle, Eject, SightRear, SightFront, RecoilPivot, MagHinge, Palm_R, Palm_L, Optic, MuzzleMount, Underbarrel |
| RATTLER | `SK_Rattler` | 67,964 | `Rattler` 4K (`M_Rattler`; BC N ORM, no E) | body, bolt, trigger, selector, magazine, stock, MuzzleDevice, IronsFront, IronsRear | Muzzle, Eject, SightRear, SightFront, RecoilPivot, MagHinge, Palm_R, Palm_L, Optic, MuzzleMount |

The three new guns are within the budget (at most about 120,000 triangles, one 4K set; 2K sets for parts). The CHOPPER's patch added 72 triangles (the cap that
closes the housing under the `FrontSight` shell) and changed no vertex, UV, normal or colour; `SK_Chopper.patch.json` and `SK_Nine.patch.json` in `art/out/glb/`
are the diff proofs. Texture memory is about 77 MB per 4K gun set (BC7 + BC5 + ORM, mips) and 22 MB per 2K parts set.

Magazines and brass (all static, authored in place on the gun's axes, so spawn them at the gun's origin with no offset and let the `magazine` bone carry them):

| Asset | Triangles | Set (2K) |
|---|---:|---|
| `SM_Weapon_ChopperMagazine` / `_TopRound` | 36,436 / 3,216 | `Weapon_ChopperMagazine` |
| `SM_Weapon_NineMagazine` / `_TopRound` | 19,470 / 2,736 | `Weapon_NineMagazine` |
| `SM_Weapon_ShortyMagazine` / `_TopRound` | 6,292 / 2,804 | `Weapon_ShortyMagazine` |
| `SM_Weapon_StretchMagazine` / `_TopRound` | 4,198 / 2,592 | `Weapon_StretchMagazine` |
| `SM_Weapon_RattlerMagazine` / `_TopRound` | 7,744 / 1,944 | `Weapon_RattlerMagazine` |
| `SM_Weapon_CasingRifle` / `_CasingPistol` | 596 / 548 | `Weapon_CasingRifle` / `Weapon_CasingPistol` (512) |

Socket positions (metres, gun space; the exact values with Unreal cm, bone heads, eject vectors and hide bones are in `art/out/weapons_r4.json` and, checked
into git, `unreal/MurderInc/Content/Data/gun_contract.json`):

| Socket | CHOPPER | NINE | SHORTY | STRETCH | RATTLER |
|---|---|---|---|---|---|
| Muzzle | 0.4975, 0, 0 | 0.201, 0, 0 | 0.700, 0, 0 | 0.790, 0, 0 | 0.465, 0, 0 |
| MuzzleMount | 0.426, 0, 0 | 0.196, 0, 0 | 0.652, 0, 0 | 0.715, 0, 0 | 0.410, 0, 0 |
| Optic | 0.115, 0, 0.042 | none | 0.221, 0, 0.100 | 0.150, 0, 0.052 | 0.172, 0, 0.042 |
| Underbarrel | 0.305, 0, -0.0623 | none | 0.488, 0, -0.052 | 0.300, 0, -0.038 | none |
| Laser | none | 0.156, 0, -0.0236 | 0.536, 0, -0.052 | none | none |
| MagHinge | 0.222, 0, -0.040 | 0.0177, 0, -0.0359 | 0.206, 0, -0.020 | 0.157, 0, -0.024 | 0.166, 0, -0.032 |
| Palm_R | 0.040, -0.0155, -0.085 | 0.014, -0.0146, -0.078 | 0.295, -0.0165, -0.095 | 0.046, -0.0165, -0.085 | 0.062, -0.015, -0.082 |
| Palm_L | 0.315, 0, -0.0615 | 0.030, 0.0146, -0.090 | 0.505, 0, -0.052 | 0.300, 0, -0.038 | 0.315, 0, -0.0275 |
| SightRear / SightFront | 0.0235 / 0.409, Z 0.0555 | 0.0125 / 0.186, Z 0.0185 | 0.134 / 0.575, Z 0.060 | 0.028 / 0.505, Z 0.0645 | 0.012 / 0.412, Z 0.0575 |
| RecoilPivot | -0.020, 0, -0.030 | -0.030, 0, -0.085 | 0.015, 0, -0.012 | -0.245, 0, -0.030 | -0.020, 0, -0.030 |
| Eject (position; casing direction in gun space) | 0.150, -0.019, 0.018; (0, -0.95, 0.30) | 0.105, -0.012, 0.014; (0, -0.95, 0.30) | 0.372, -0.0285, 0.016; (0.55, -0.80, 0.25) | 0.135, -0.0225, 0.020; (-0.15, -0.95, 0.30) | 0.165, -0.0225, 0.008; (0, -0.95, 0.31) |

Origins differ and matter (section 6): CHOPPER on the bore at the rear trunnion; NINE as proven; **SHORTY on the bore at the rear face of the butt pad**
(the palm is 295 mm ahead of the origin); **STRETCH on the bore at the rear of the receiver, the stock at negative X to -0.255**; RATTLER on the bore at the rear
face of the receiver.

Moving parts (all proved through their travel with zero overlaps):

| Gun | Bolt / slide | Trigger | Selector | Other |
|---|---|---|---|---|
| CHOPPER | bolt `bolt` (as before) | 14 / 19.5 deg proof (as before) | as before | `Booster` pose: pushed 20 mm along +X (proof pose) |
| NINE | slide 10 to 44 mm | 17 deg | n/a | barrel tilt, hammer, slide stop (as before) |
| SHORTY | `bolt` 75 mm back along -X (carrier and left charging handle) | `trigger` +17 deg about +Y | 0 / 14 / 28 deg about +Y (AUTO / SEMI / SAFE legends) | magazine drops (0, 0, -0.13) |
| STRETCH | `bolt` 95 mm back (carrier, bolt head, left T-handle); locks back on empty | `trigger` +17 deg | 0 SAFE / +16 SEMI | `bolt_catch` +7 deg; `bipod` rest = folded, rotate (0,1,0) by -100 deg = deployed; magazine drops (0, 0, -0.12) |
| RATTLER | `bolt` 50 mm back (open bolt and the top T-handle, rest = bolt forward); does not lock open | `trigger` +17 deg | 0 / 14 / 28 deg (S / 1 / A) | `stock` rest = FOLDED along the left flank, rotate (0,0,1) by +180 deg about the hinge (0, 0.0285, 0) = deployed; magazine drops (0, 0, -0.14) |

## 2. The roster of six and how each looks

They were checked as side silhouettes at one scale (2.2 mm per pixel, bore lines aligned): `art/previews/weapons_lineup.jpg`. Overall lengths measured on the
meshes: NINE 233 mm, CHOPPER 502, SHORTY 700, RATTLER 713 (stock deployed; 465 folded), STRETCH 1,045. Pairwise silhouette overlap (best-aligned IoU, gun and
magazine) was 0.26 to 0.57 for every pair of the five own guns (the worst, SHORTY against CHOPPER, 0.56), i.e. no two share an outline. The sixth gun, the STICK,
stays the pack M4 (unchanged, never committed).

| Slot | Gun | What the player sees | Colour story |
|---|---|---|---|
| 1 | CHOPPER | Our AK-pattern pistol-length carbine with the stock folded under the receiver, a banana magazine ahead of the grip, round wooden cover. The same mesh the owner approved over three review rounds. | Red-brown laminate wood, grey-blue gunmetal |
| 2 | NINE | Our pistol, stainless slide with a polished gold base pad. Unchanged geometry; gains a laser rail, a muzzle mount and a magazine mount (sockets only). | Stainless, gold, black |
| 3 | SHORTY | Compact bullpup carbine, 700 mm with a 267 mm barrel. A tall rear block with a see-through arched carry handle (the integral rail, a 150 x 24 mm window), the pistol grip hanging from the middle of the gun, a straight magazine BEHIND the grip (no other gun has that), a ventilated forend, a birdcage flash hider, an angled deflector vane at the ejection port. In first person the olive block and the handle arch fill the view in front of the face. | Olive-drab moulded polymer, parkerised dark steel, black rubber pad, green tritium inserts |
| 4 | STICK | The pack M4 carbine (not ours). | Pack finish |
| 5 | STRETCH | Semi-automatic marksman rifle, 1,045 mm: a tall walnut stock with a cheek riser, one long rail from over the stock's front to the handguard's end, a slim slotted handguard with a folding bipod under it, a long free-floating barrel and a ported brake, flip-up irons, a short 10-round box magazine so the gun reads long and low. | Dark oiled walnut, warm graphite steel, black rubber, black anodised bipod |
| 6 | RATTLER | The Goons' gun at first-person grade: a compact stamped-steel box receiver with a top T-handle racing back and forth on the open bolt, a round ventilated shroud with a tan strap wrap, a slotted muzzle device, a long straight stick magazine ahead of the grip, and a wire U-frame stock folded flat along the LEFT side (deployed it makes it 713 mm). | Light grey phosphated sheet, blackened shroud, tan webbing, dull zinc wire |

Pictures to look at (all in `art/previews/`): `weapons_lineup.jpg`; per gun `weapons_<gun>_hero.jpg`, `_fp.jpg` (first-person hip view), `_side.jpg`, `_parts.jpg` (shorty,
stretch, rattler), `_built.jpg` (parts fitted: chopper, nine, shorty, stretch); `weapons_parts_kit.jpg`, `weapons_parts_sights.jpg`; `grips_<gun>_hip.jpg` and
`grips_chopper_aim.jpg`, `grips_rattler_aim.jpg` (the hands). The five rack icons are `art/out/ui/T_UI_Gun_{Chopper,Nine,Shorty,Stretch,Rattler}.png`
(512 x 192, white on transparent, bore line at y = 84, centred; the RATTLER with its stock deployed), in the archive's `ui/`.

## 3. The parts kit

Twelve parts of our own, all STATIC meshes whose origin is the mount (the assembly attaches them with `SnapToTargetIncludingScale` to the gun socket named in the
table, no rotation; sockets carry no rotation, so parts for the canted NINE magazine and the side-mounted grips are modelled in the mount's frame). Two unique 2K
sets: `Weapon_Parts` (slot `M_Part_Hardware`: BC N ORM E) and `Weapon_PartsMags` (slot `M_Part_Mags`: BC N ORM). Lens and reticle are the flat slots `M_Part_Lens`
and `M_Part_Reticle` (no texture set: the glass and the collimated dot are materials made at import, as the pack's `M_TFA_AR_Glass` and `M_TFA_AR_Reticle`).

All rails are the same standard we call MI-R (21.2 mm across the 45 deg flanks, 5.3 mm lugs and slots on a 10.6 mm pitch; the reference plane is the lug tops for a top
rail and the lug undersides for an underside rail). Every clamp was fitted to the measured rails of the CHOPPER, SHORTY, STRETCH and RATTLER.

| Part (`SM_Part_*`) | Triangles | Slot | Mounts on (gun socket) | Fits | Part sockets (part frame, metres) | Hides when fitted |
|---|---:|---|---|---|---|---|
| `RedDot` | 7,734 | optic | Optic | CHOPPER, SHORTY, STRETCH, RATTLER | SightEye (-0.0325, 0, 0.0245), relief 0.14 | CHOPPER FrontSight; SHORTY IronsFront; STRETCH IronsRear + IronsFront; RATTLER IronsFront + IronsRear |
| `Scope4x` | 12,040 | optic | Optic | CHOPPER, SHORTY, STRETCH (not the RATTLER: its rail is too short) | SightEye (-0.067, 0, 0.0275), relief 0.085 | as the red dot |
| `Suppressor` | 5,852 | muzzle | MuzzleMount | CHOPPER, SHORTY, STRETCH, RATTLER | Muzzle (0.210, 0, 0) | CHOPPER Booster; others MuzzleDevice |
| `SuppressorPistol` | 3,684 | muzzle | MuzzleMount | NINE | Muzzle (0.155, 0, 0) | nothing (sits on the frame; the slide cycles past it) |
| `Compensator` | 2,628 | muzzle | MuzzleMount | CHOPPER, SHORTY, RATTLER (not the STRETCH: it has a brake) | Muzzle (0.062, 0, 0) | as the suppressor |
| `ForegripVertical` | 3,544 | underbarrel | Underbarrel | SHORTY, STRETCH | SupportHand (0, 0, -0.052) | nothing |
| `ForegripVerticalWood` | 4,092 | underbarrel | Underbarrel | CHOPPER only (a saddle clamp round the underside of its folded stock plate; the handguard has no rail) | SupportHand (0, 0, -0.048) | nothing |
| `ForegripAngled` | 2,380 | underbarrel | Underbarrel | SHORTY, STRETCH | SupportHand (-0.012, 0, -0.030) | nothing |
| `LaserModule` | 3,096 | laser | Laser | NINE, SHORTY | Beam (0.0235, 0, -0.0125) along +X | nothing |
| `MagRifleExt` + `_TopRound` | 3,712 + 1,968 | magazine | MagHinge | SHORTY, STRETCH (same 24 x 48 mm section as both standard magazines) | none | the standard magazine mesh is replaced by the part |
| `MagSmgExt` + `_TopRound` | 2,992 + 1,680 | magazine | MagHinge | RATTLER | none | as above |
| `MagPistolExt` + `_TopRound` | 5,694 + 1,416 | magazine | MagHinge | NINE (modelled pre-canted along the grip axis in the socket's frame) | none | as above |

Workbench slot counts: CHOPPER 3 (optic, muzzle, underbarrel), NINE 3 (muzzle, laser, magazine), SHORTY 5 (optic, muzzle, underbarrel, laser, magazine), STICK 5 (the
pack's parts, unchanged), STRETCH 4 (optic, muzzle, underbarrel, magazine), RATTLER 3 (optic, muzzle, magazine). Before: none on the CHOPPER and NINE. A bullpup has
no stock slot. `stock_wire_open` (the deployed-stock RATTLER as a second whole-mesh export) was not built; it needs one export of `SK_Rattler` with the `stock` bone
posed +180 deg about +Z, sharing the same set, and one commit that adds the slot, the part and the variant to the data.

## 4. The data (what it says now, and what still has to change)

The data engineer's commits (`19265f1` to `bf98ae4`, the checker `tools/data/check_guns_data.py --art` and the generator `tools/data/make_gun_contract.py`) already
carry the six-gun roster, the 22 attachments (10 pack parts and 12 of ours) and the compatibility table. This page does not repeat them; `WEAPONS_R4_DATA.md` has the
table of every difference from the specification. What matters for the box, field by field:

**guns.json** (all in `unreal/MurderInc/Content/Data/`).
- `roster`: chopper, nine, shorty, stick, stretch, rattler.
- `art.mesh` is `exists` with the asset names `SK_Chopper`, `SK_Nine`, `SK_Shorty`, `SK_Stretch`, `SK_Rattler` (the Blender asset is `SK_Rattler`; the old data said
  `SK_Weapon_Rattler`: renamed). The STICK stays `see variants` (pack).
- `mounts.<slot>.status` is `exists` for every slot of every gun in section 3 (CHOPPER and NINE included: they were `missing`, which is what made the Workbench say "No
  parts"); each carries `socket`, `at` (gun-space metres, from the contract), `hide` (the bones above) and, for magazines, `rideBone: "magazine"`.
- `ready` (the gate of LOADOUT 3.2): a gun is offered when its default mesh `exists`, is not a stand-in, and every core role is `exists`, `template` or `procedural`.
  The RATTLER's `Idle` moved from `missing` to `template` so that the gate passes and the rack shows it (six guns). Without the meshes on the box the new guns fall
  back to the template stand-in and are hidden, as designed.
- `art.icon.status`: `exists` for SHORTY, STRETCH, RATTLER. **Still `missing` for the CHOPPER and the NINE** although `T_UI_Gun_Chopper` and `T_UI_Gun_Nine` are now
  rendered and in the archive: flip both to `exists` once they are imported to `/Game/UI/Icons`. No widget draws an icon today, so it blocks nothing.
- `presentation.<gun>.meshOffset` of the three new guns is the **identity** (`rot [0, 0, 0]`), not the specification's `[0, 1.5708, 0]`: our meshes face +X, as the
  proven `SK_Nine`, whereas the pack rifles face +Y and needed the quarter turn. The SHORTY's `pos` is `[-0.001, 0.010, 0.255]` (web units) so that its `Palm_R` lands
  where the CHOPPER's lands and every authored view, reload and strike pose keeps working. First probe on the box: the muzzle must be at +X; if it is not, the importer's bone turn
  (BOX.md) is the cause, not the data.
- `rules` and `extra` of every gun are unchanged (checked by parsed-JSON comparison); `rules.magSize` is 30 (SHORTY, STRETCH, STICK) and 32 (RATTLER).
  The STRETCH's art magazine shows 10 rounds while the data says 30: the data stays (the extended magazine brings it to 45).
- `animSet`: `chopper_ik`, `shorty_ik`, `stretch_ik`, `rattler_ik`, `pistol` (NINE), `rifle` (STICK, pack clips).

**attachments.json.** New stat `magSize` (`rules.magSize`, clamp 5 to 100, better = higher, a trade). The 12 parts of ours carry `presentation.mesh`
`/Game/Weapons/Parts/SM_Part_<Name>.SM_Part_<Name>`, `socketOffsetsCm` (their sockets in Unreal cm), `art.pip` `T_UI_Att_<id>`, and these effects (all inside the trade band
0.4 to 2.5, computed from the sums of |ln factor|; the pack parts they replace keep their numbers):

| Part | Better | Worse |
|---|---|---|
| `red_dot` | aim time x0.92, moving aimed spread x0.88 | aimed spread x1.08, swap x1.05 |
| `scope_4x` | aimed field of view 30, look x0.6, aimed spread x0.7 | aim time x1.35, moving aimed spread x1.3, sway x1.2 |
| `suppressor`, `suppressor_pistol` | noise x0.4, flash x0.15, kick (pitch) x0.95 | falloff from 25 m to 0.85 at 50 m, aim time x1.08, swap x1.06, length x1.12 (as the pack silencer) |
| `compensator` | camera climb x0.88, sideways x0.90 | noise x1.15, flash x1.3, aim time x1.04 |
| `foregrip_vertical`, `_wood` | kick x0.88, side x0.85 | aim time x1.08, swap x1.05 |
| `foregrip_angled` | aim time x0.9, swap x0.95, kick x0.96 | side x1.12 |
| `laser_module` | hip spread x0.8, moving hip x0.85 | aimed spread x1.1, aim time x1.08, swap x1.04 |
| `mag_ext_rifle`, `mag_ext_smg` | magazine x1.5 | reload x1.12, swap x1.05 / 1.06, aim time x1.04 / 1.05 |
| `mag_ext_pistol` | magazine x1.6 (15 to 24 rounds; the specification said x1.67, but the parser truncates and the test compares to 1e-12) | reload x1.10, swap x1.08, aim time x1.06 |

`compatibility` is the table of section 3 (default `null` = the factory part; `mount` = the gun socket; no stock row on the SHORTY). The pack `laser` row of the NINE was
dropped earlier because the pack laser is 155 mm; our module is 46 mm, so the NINE has a laser row again. Everything under `Source/` and every test: see `WEAPONS_R4_TESTS.md`
(eleven expectations that the data makes false, each with its replacement).

Re-checking, no engine needed: `python3 tools/data/check_guns_data.py --art` and `python3 tools/data/make_gun_contract.py --check` (exits 1 when `gun_contract.json` is
stale against `art/out`).

## 5. Importing it (what the box must do)

Our guns do NOT go through `tools/box/anim/ue_import_guns.py`: that script imports the purchased pack and needs no change (it is not to be touched; the STICK keeps `SM_TFA_AR_*`).
The five guns, the magazines, brass and parts are imported by `tools/box/fp/mi_guns_r4.py` (called by `tools/box/fp/import-chars.sh r4`, tars made by
`tools/box/fp/fp-art.sh packr4`). Order on the box: unpack the archive into a folder of its own (`MI_FP_IN`), editor stopped, run `import-chars.sh r4`, start the editor.

Where things must land (the data names these; `gun_contract.json` lists all 32): skeletal guns `/Game/Weapons/<Gun>/SK_<Gun>`, magazines `/Game/Weapons/<Gun>/SM_Weapon_<Gun>Magazine`
(+ `_TopRound`), brass `/Game/Weapons/Casings/`, parts `/Game/Weapons/Parts/SM_Part_*`, icons and pips `/Game/UI/Icons/`. Slots by name: `M_<Set>` for the guns, `M_Weapon_<Gun>Magazine`, `M_Part_Hardware`,
`M_Part_Mags`; `M_Part_Lens` and `M_Part_Reticle` are made at import as flat/translucent and additive-collimated materials (copy `glass()` and `reticle()` from `ue_import_guns.py`, our own copies, not pack assets).

What the importer and the engine still have to learn or prove (none of it exists in Blender's reach):

1. **Static-mesh sockets.** A GLB cannot carry them. Write the parts' sockets (`SightEye`, `Muzzle`, `SupportHand`, `Beam`) from `weapons_r4.json` (`parts.<id>.sockets_unreal_cm`) or `gun_contract.json`.
   `mi_guns_r4.sockets()` only prints the keys today: make it compare `guns.<id>.sockets[*].unreal_cm` and `bones[*].head_unreal_cm` with the imported skeletons (mind the bone turn the importer leaves, BOX.md)
   and the part sockets with the static meshes, and return the number of differences. **`MurderInc.Loadout.MountsExist`** must then read OUR meshes too (it skips without the pack today): it checks every
   `mounts.<slot>.socket` of the data against the skeleton and every part socket the data names, with `at` within 1 mm of the contract.
2. **The tiling detail is not applied.** `mi_fp_import._surface()` wires BC, N, ORM and E only. Every gun's manifest slot record carries `detail_set` (`TS_GunDetail_Steel`, 20 mm tile; the SHORTY also
   `TS_GunDetail_Polymer`, 12 mm) and `detail_repeat_per_uv`. Add the second UV tile and blend the tiling normal into N: steel where ORM.B = 1, polymer where 0. It is what lifts the 6.2 to 6.6 k px/m unique density at 25 to 60 cm.
3. **Conventions.** Normal maps are OpenGL (flip green as for the CHOPPER and NINE); ORM = R ambient occlusion, G roughness, B metallic (binary); BC sRGB; E sRGB, present only for `Shorty` (the tritium inserts) and `Weapon_Parts` (the laser's emitter) and the NINE and CHOPPER as before. Omit missing maps (`cp_set` already does).
4. **`HideBoneByName`** hides every vertex weighted to the bone and its children; `Booster`, `FrontSight`, `MuzzleDevice`, `IronsFront` and `IronsRear` are closed shells weighted 100 percent (open edges after removal: none; checked), with
   the barrel stub (R 8.5 mm, with its bore) modelled behind a muzzle device. Prove on the FIRST-PERSON gun (a poseable component) that the hide works, and whether the part frame needs the bone's reference-pose rotation undone.
5. **The optic's sight picture (the largest open problem).** The red dot's and the scope's clear cone through the part is about 4 degrees (the specification wanted 9; no tube sight can do it at the data's relief 0.14 and 0.085). At the aimed
   field of view the picture would be a small clear disc in a dark tunnel. The remedy is in the material, not the mesh: while aiming, fade or dither the fitted optic's `M_Part_Hardware` slot (fully gone above about 0.6 aim) and keep `M_Part_Lens` and
   `M_Part_Reticle` (the scope may keep its body: its tunnel is the intended 30 degree look). `presentation.json firstPerson.opticMaterials` carries the daylight values (dot brightness 25000, glass opacity 0.05). This rule is NOT implemented anywhere.
6. **Sight line.** On every gun the sight line is parallel to the bore (SightRear and SightFront have the same Z); `SightEye` of each optic part places the eye. The aimed camera sits at SightEye minus the part's relief along the bore. The SHORTY's eye with the
   red dot ends 14 mm ahead of its butt face and above the cheek rise: check that the near plane does not slice the cheek or the handle (0.14 is the fallback relief).
7. **Re-measure `wallPull`** on the real meshes with ProbeWall (the bullpup is 0.70 m, the RATTLER 0.465 m folded).

## 6. First-person arm notes (palms, support hand, camera recipe, per-gun targets)

The first person is the hand-IK way for all five own guns, not the pack's clips (those are authored for one M4 on its own skeleton): the template rifle's (or the pistol's) idle and fire clips on the arms, both palms put on `Palm_R` and `Palm_L` by
two-bone IK (`presentation.json firstPerson.animSets`: `pistol`, `chopper_ik`, `shorty_ik`, `stretch_ik`, `rattler_ik`, each `ik: {left: Palm_L, right: Palm_R}`). The camera recipe is `docs/unreal/ANIMATION.md` 9 and `presentation.json firstPerson.recipe`
(arms hang from the camera at the eye point; first-person field of view 54, blended to 38 on irons and 32 with any optic; near clip 1 cm).

Rules every gun's sockets follow (the arms depend on them): `Palm_R` sits on the right face of the grip at its upper middle; the trigger face is 70 to 73 mm ahead of it (CHOPPER 73, NINE 90, RATTLER 70 in the specification and 78 as built); `Palm_L` is on a clear underside run
(CHOPPER: under the stock plate's handguard, NINE: left of the dust cover, SHORTY and STRETCH: on the underside rail, RATTLER: the strap wrap's underside, a palm-up cup 253 mm ahead of `Palm_R`).
Grip solves are in `Content/Data/grips.json` (Blender `_rule_grips.py`, checked in Blender only; pictures `art/previews/grips_<gun>_hip.jpg`). Targets and traps per gun:

| Gun | Origin and the trap | Support palm ahead of firing palm | Notes |
|---|---|---|---|
| CHOPPER | rear trunnion; as before | about 275 mm | the owner-approved hold; the foregrip part, when fitted, replaces `Palm_L` by its `SupportHand` |
| NINE | as before | two-hand pistol grip | unchanged; `magHinge` in the presentation stays the bone `magazine` (proven path) until a picture says otherwise |
| SHORTY | the BUTT: its palm is 295 mm out, so the mesh is offset by 0.255 (web) in the data; its forend is 700 mm out and the support wrist is about 77 cm from the CHOPPER's shoulder anchor | 210 mm | its solve wants the shoulders ahead of the eye ([11.5, 1.1, -16.4]); the first-person view must put the butt near the eye; with the optic, the eye is above the cheek rise |
| STRETCH | receiver rear; the stock is behind the origin (to -0.255) and fills the lower right of the frame; its palm is only 46 mm from the origin | 254 mm | a bipod is on the underside rail ahead of `Palm_L` (the legs fold back to X 0.320, an underbarrel grip at X 0.300 must stay within X 0.285..0.315); shoulders [-6.5, 1.1, -12.4] |
| RATTLER | receiver rear; the folded wire stock covers about half of the LEFT flank in the hip view (the strap is NOT covered: wires end at X 256, the strap starts at 290) | 253 mm | the trigger face is at X 140 (spec 132), 4.5 mm from the magazine well: no finger fits in front of it, so the grip solve lays the thumb outside the gun; if the real camera makes the stock too much, fold it to the right, never move the strap; shoulders [-2.5, 1.1, -12.4] |

All four rifle sets carry the NINE's `shoulders [-6, 0, -24]` in the data and the solved values above in the grip entries; the rig only uses the solved shoulder translation once a solved grip exists. Estimated reach (support wrist to shoulder) is
58 to 63 cm against an arm reach of about 55: tune in play with `mi.FP.Shoulders`. The finger solves are Blender-only, the fingers of the rule arms were not re-posed in the engine.

## 7. Animation and sound consequences

Animation. Nothing needs to be authored for the first release: the template rifle's `Idle` and `MM_Rifle_Fire` on the arms (the data says `FirstPerson.Clips` fails loudly if `MM_Rifle_Fire` is not on the arms' skeleton: confirm it on the box) plus the rules-driven procedural viewmodel rig
(FMIViewmodelRig) play every other core role from the guns' rules, bone by bone: `bolt` travel for the fire/charge, `trigger`, `selector`, `magazine` (drop and re-seat by the reload marks), the RATTLER's `bolt` racked on the empty reload, the STRETCH's `bolt_catch` and `bipod`
(the inspect clip and the Workbench pose it), the `stock` bone for the RATTLER icon and the optional deployed variant. Roles that waited for pack clips are `missing` in the data (`ReloadQuick`, `ReloadEmptyRetain`, `Grip*` are `notApplicable`) and their prompts hide. The pack's clips remain the STICK's only. The
CHOPPER's 44 adapted clips (`mi_adapt.py`, ANIMATION.md 3) are available again only if a pack-mode set is ever written for `SK_Chopper`; the hand-IK set does not use them. Per-gun hand IK on `Palm_R` and `Palm_L`, finger poses and reload marks are the animation and characters agents' follow-up; the Eject socket's rotation comes from the direction vectors above.

Sound. Only the CHOPPER and the NINE have sound layers of their own; since version 3b `audio.json weaponSounds` names the gun whose sounds each of the other four fires with (the CHOPPER's, its silenced set, its duck and brass; AUDIO.md, "Guns without sounds of their own"), and `MurderInc.Audio.EveryGunSounds` fails for a gun without a shot or a tail. Suppression is by event: `FMIShotFiredEvent::bSuppressed` (true for a fitted `suppressor` or `suppressor_pistol`)
picks the `<weapon>_shot_silenced` layers and quieter tails. The compensator raises `noise` (x1.15) and `flash` (x1.3) by data only. Brass: `SM_Weapon_CasingRifle` for CHOPPER, SHORTY, STRETCH, `SM_Weapon_CasingPistol` for NINE and RATTLER. No new audio asset is needed for this round; per-gun distinct sound is a sound-lane choice (the paused version 3b).

## 8. What is not done

- Nothing was run in Unreal (sockets, hide bones, materials, lens and reticle, the aimed views, the Workbench, the hands). Section 5 is the checklist.
- The optic sight-picture rule (section 5, item 5) and the importer's tiling detail (item 2) are not written. A task for each was queued.
- `stock_wire_open` (the RATTLER's deployed stock as a part) and `SM_Weapon_GoonSMG` v2 (the Goons carrying the same gun as the player, <= 25k tris, 2K) are not built. The Goon SMG's silhouette no longer matches the RATTLER's shroud and wire stock; acceptable for release.
- The STICK's rack icon (rendered on the box from the pack mesh) is at 1.906 mm per px while the five own icons are at 2.2: re-render it at 2.2 so the six compare by length (`tools/box/anim/bl_icons.py`).
- No LODs, no collision meshes beyond what the importer generates, no impact decals; the new guns are LOD0 only (67k, 62k, 68k triangles; the SHORTY's screws, grip, pad, barrel and hider are the best places to cut a LOD).
- Pack clips for the three new guns (would need `mi_adapt`-style retargeting per gun); finger solves in the engine; `grips.json` entries are Blender-solved only.
- A full-loadout assembly test in the engine (every compatible part on every gun at once, SightEye within 1 mm of the contract, nothing invisible) and the parity check (the default CHOPPER and NINE with no parts are unchanged) are on the box's list.

## 9. Known weaknesses of the art (honest list)

- **Optic clear cone 4 degrees**, not 9 (section 5, item 5). Without the material rule the red dot's aimed view is a porthole.
- **Texel density** is below the 7,000 px/m asked: SHORTY 6,506 on the weight-1 flanks (median 4,268), STRETCH 6,150 on the receiver, rail and grip (3,623 median), RATTLER 6,640 (4,789 median); the CHOPPER and NINE are at 7.7 to 9.3 k. One 4K set per gun is 82 percent covered. The parts sets are 3,266 px/m
  (Weapon_Parts) and 3,866 (Weapon_PartsMags), about half the guns' sharpness at 30 cm; their detail (screws, knurling, flutes, ports) is modelled, not painted. The unapplied tiling detail would offset part of it.
- **Surfaces.** SHORTY polymer is deliberately restrained and still reads clean next to the worn CHOPPER; its parkerised steel reads near-black in studio light. STRETCH wood has more irregular rings after the fix pass but still shows some regular waves near the curved stock edges, and the stock is a heavy wedge because that is the specified comb and toe
  (the walnut and the steel were lifted from the brief's near-black so that they show in daylight, and the steel is warm graphite so that it does not look like the CHOPPER's navy in first person). RATTLER strap and steel albedo drift from the brief (strap #80735b mean against #a58f66, steel warmer and lighter): judge them under the game's sun. The suppressors' heat-tint banding is garish. Receivers and magazines are milled slabs more than curved shells.
- **Triangle overruns:** the CHOPPER stays at 150,487 (proven, kept); the wooden foregrip 4,092 against 4,000 and the scope 12,040 against 12,000.
- **Specification contradictions decided by the geometry** (details in `art/blender/PROGRESS.md`): STRETCH height 211.9 mm (the aperture ring tops at +0.0717; the 198 mm is cheek riser to grip), charging slot X 0.088..0.206, grip lines win over the 40 x 33 mm section; RATTLER deployed length 713 to 715 mm (not 635), height 277, folded width Y -29.8..+42.4,
  rest pose with the bolt forward; SHORTY flank density; the angled grip is about 62 x 30 x 66 mm (92 x 30 x 58 asked), the scope 48 mm wide (54 asked).
- **Unmodelled interiors:** the SHORTY's feed path from the magazine well to the chamber is closed; the STRETCH has no gas piston, ejector or recoil spring inside, only the carrier, bolt head and breech.
- **Parts are proved in pairs** (54 pairs, none cross) and on every gun that has the mount, not as a full loadout; the NINE's barrel tilt of 2.3 deg moves its crown stub about 5 mm inside the suppressor collar during a cycle (estimated, not rendered).
- **Legal comfort.** Markings are invented only (`CARBINE S-5.6`, `SAFE SEMI AUTO`, `MARKSMAN 7.6`, `MOD S1`, `SMG 9`, `R-545`, proof stars, invented serials). The arch-handled bullpup and the wire-stocked open-bolt SMG sit near real families of firearm in layout; the invented parts (deflector vane, six-slot hider, strap wrap, the MI-R rail standard) are what make them ours. If more distance is wanted, change one structural cue on each (the handle arch's profile, the shroud's vent pattern).
- **Preview lighting** is studio and HDRI, not the game's; the first-person pictures use the CHOPPER's viewmodel pose, not the engine's.
- `art/out` is git-ignored: textures and GLBs exist only on the build machine and in the archive; a clean checkout rebuilds the geometry bit for bit from code, and the final bakes are recreated with `build.py build weapons_<gun> --bake --rebake-unique --export --res 4096` (about 11 to 20 minutes each on two threads, one 4K bake at a time under `flock art/out/.bake.lock`; 2K sets about 5 minutes).
  The CHOPPER and NINE must NOT be re-exported from code: a rebuild re-unwraps and would mismatch the cached 4K sets; patch the existing exports with `_weapons_patch.py --force` instead.

## 10. Commands (reproduce, re-prove, re-pack)

    PY=<the Blender-as-a-module python>               # art/blender/README.md
    $PY art/blender/build.py build weapons_shorty --export        # also weapons_stretch, weapons_rattler, weapons_parts
    $PY art/blender/assets/_weapons_patch.py --force              # CHOPPER and NINE mounts, from art/out/glb/_pre_patch
    $PY art/blender/assets/_weapons_check.py                      # Chopper and Nine: ALL FIXED POINTS KEPT
    $PY art/blender/assets/_weapons_check_shorty.py               # SHORTY / _stretch / _rattler: ALL FIXED POINTS KEPT
    $PY art/blender/assets/_weapons_check_parts.py                # ALL MOUNTS KEPT
    $PY art/blender/assets/_weapons_r4_contract.py                # writes art/out/weapons_r4.json: CONTRACT KEPT
    $PY art/blender/assets/_weapons_icons.py chopper nine shorty stretch rattler lineup
    bash tools/box/fp/fp-art.sh packr4                            # the three tars; merge them into art/out/fp-guns-r4.tar (section 0)
    python3 tools/data/check_guns_data.py --art                   # the data against the art contract
