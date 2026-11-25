# Weapons round 4: what the data says, where it differs from the specification, and what nobody has run

For the box engineer, and for whoever packages the next release. The design is `LOADOUT.md` (3.2, 3.3, 6.8); the tests the data
changes are `WEAPONS_R4_TESTS.md`; the owner's decision is `DECISIONS.md`, 2026-11-25. This page is the data engineer's hand-off.

Files (all under `unreal/MurderInc/Content/Data/` unless stated): `guns.json`, `attachments.json`, `presentation.json`,
`frontend_text.json`, and the new `gun_contract.json`; `tools/data/check_guns_data.py` and `tools/data/make_gun_contract.py`.
Nothing under `Source/`, no test, no golden and no `config.json` was touched; every gun's `rules` and `extra` are identical to the
commit before the data (checked by comparing the parsed JSON), the STICK's rules and extra too.

## 1. The assets the import must create

The data names these asset paths; `gun_contract.json` lists every one. If the importer puts a mesh elsewhere, change the data (one
line each) and run the checker: do not change the checker to match. An asset path is `<folder>/<name>.<name>`.

| What | Folder | Names |
|---|---|---|
| The five guns (skeletal) | `/Game/Weapons/<Gun>/` | `SK_Chopper`, `SK_Nine`, `SK_Shorty`, `SK_Stretch`, `SK_Rattler` (the folder is `Chopper`, `Nine`, `Shorty`, `Stretch`, `Rattler`) |
| Their magazines (static, authored in the gun's own space, carried by the `magazine` bone) | `/Game/Weapons/<Gun>/` | `SM_Weapon_<Gun>Magazine` and `SM_Weapon_<Gun>Magazine_TopRound` |
| Brass | `/Game/Weapons/Casings/` | `SM_Weapon_CasingRifle` (CHOPPER, SHORTY, STRETCH), `SM_Weapon_CasingPistol` (RATTLER) |
| The twelve parts (static, origin = mount, with the sockets of `gun_contract.json` written at import) | `/Game/Weapons/Parts/` | `SM_Part_RedDot`, `SM_Part_Scope4x`, `SM_Part_Suppressor`, `SM_Part_SuppressorPistol`, `SM_Part_Compensator`, `SM_Part_ForegripVertical`, `SM_Part_ForegripVerticalWood`, `SM_Part_ForegripAngled`, `SM_Part_LaserModule`, `SM_Part_MagRifleExt`, `SM_Part_MagSmgExt`, `SM_Part_MagPistolExt` (the three magazines also `_TopRound`) |
| Materials the optics need (made by the import, not from the art) | `/Game/Weapons/Parts/` | `M_Part_Lens`, `M_Part_Reticle` (the reticle's axis along +X); their scalar parameters are named as the pack's (`Brightness`, `Opacity`, `Roughness`), the daylight values are in `presentation.json firstPerson.opticMaterials` |
| Icons | `/Game/UI/Icons/` | `T_UI_Gun_Shorty`, `T_UI_Gun_Stretch`, `T_UI_Gun_Rattler` exist in `art/out/ui` today (they replace the box's pack-rendered ones); the CHOPPER's and the NINE's are not rendered. No widget draws an icon, so this blocks nothing. |

Static-mesh sockets cannot be read from a GLB: the part sockets (`SightEye`, `Muzzle`, `SupportHand`, `Beam`) come from
`art/out/weapons_r4.json` (when the art lanes write it) or from `gun_contract.json`, in metres in the part's frame, written as
(x, -y, z) x 100 cm. `MurderInc.Loadout.MountsExist` reads them back.

## 2. Where the data differs from the specification and the plan, and why

| # | Specification or plan said | The data does | Why |
|---|---|---|---|
| 1 | SHORTY, STRETCH and RATTLER: `meshOffset.rot [0, 1.5708, 0]` | `[0, 0, 0]` for all five own guns | `meshOffset` maps the mesh's frame into gun space. The pack rifles face +Y, so a quarter turn puts them on the bore; ours face +X, as `SK_Nine`, whose identity block is proven in play (three review rounds). A quarter turn would point them sideways and send the bolt along the wrong axis (`PoseParts` takes directions through the offset's rotation). The plan (G5) read it the same way; the box probe should show the muzzle at +X. |
| 2 | SHORTY: `meshOffset.pos [0, 0, 0]` and `views[0]` re-anchored | `meshOffset.pos` is web `[-0.001, 0.010, 0.255]`; every `views` entry is the one it was | The SHORTY's origin is its butt, 29.5 cm behind its palm. Every view, the sprint, reload, wall and holster poses and the melee keys are origin-relative and authored for the CHOPPER's gun space (firing palm at web `(0.0155, -0.085, -0.040)`). Moving `views[0]` fixes the hip pose and leaves the other poses and keys 25 cm off. Moving the mesh fixes all of them, puts the hip pose where the modeler's anchor does (to 0.5 mm: checked), and touches no `rules` number. |
| 3 | `mag_ext_pistol` x1.67 (25 rounds) | x1.6 (24 rounds) | `ParseGun` truncates `magSize`. 15 x 1.67 is 25.05, the gun would carry 25 and the `Attachments.<part>.magSize` test, which compares to 1e-12, would fail (the specification said the resolver rounds; it does not). x1.6 is exactly 24. B / W is 2.04, inside the band. The checker refuses a fractional product. |
| 4 | RATTLER: inline `meshOffset` and `animSet` | a `real` block, as the CHOPPER's and the NINE's | The merge happens only when the real mesh is the one drawn, so `mi.Setup.ShowUnready` still draws the template stand-in with its template numbers. With the mesh present it is the same data. |
| 5 | RATTLER: "ready gate met by the procedural roles" | `Idle` moved from `missing` to `template` | `Idle` is a core role and `missing` fails the gate; the RATTLER's idle is the template rifle's, as the CHOPPER's. |
| 6 | SHORTY and STRETCH: clip lists "unchanged" (pack clips `inProgress`) | `Idle` is `template`, the roles that waited for pack clips are `missing`, `ReloadQuick`, `ReloadEmptyRetain` and the `Grip*` roles are `notApplicable`, the `upgrades` block is gone | Nobody is importing pack clips for our guns (they are authored for one M4 on its own skeleton) and the hand-IK way needs none. The statuses are read only by the ready gate and the "named once" check; `Idle`, `Fire`, `ReloadTactical`, `Holster`, `Draw` still pass. |
| 7 | Plan: add 12 parts, `rules` untouched | also `presentation.magazine` on every gun, and on the STICK | The box engineer's assembly reads it to draw the factory magazine on the stage and to override the first-person magazine. The STICK's is the pack's standard magazine on `MagHinge`. Presentation only. |
| 8 | Specification: re-measure `wallPull` | not touched | A rule number; the instruction is that numbers stay unless the specification gives one. Nothing can re-measure it without the game. The bullpup is 0.70 m and the RATTLER 0.465 m folded, so both pull back from a wall a little earlier than they need to. |
| 9 | `grips.json` entries for the new guns | none | They need Blender's grip solve (`_rule_grips.py`), one process at a time under the bake lock. Without an entry the hands use the palm IK alone (the NINE's earlier state). |
| 10 | NINE: new `magHinge` socket | `presentation.json guns.nine.real.sockets.magHinge` stays `magazine` (the bone) | It is the proven first-person path (hand to the magazine bone in a reload). `MagHinge` now exists on `SK_Nine` for the part mount only. Switch it after a picture. |
| 11 | RATTLER `stock_wire_open` | not in the data | It needs a second export; the slot, part and variant are one commit when it lands. |

## 3. What was added beyond the specification (the code ignores it today)

`presentation.<gun>.ejectDir` (the casing's direction in web gun space, from the specification's vectors) on SHORTY, STRETCH and RATTLER;
`attachments.<part>.presentation.socketOffsetsCm` (the parts' sockets in Unreal cm, as the pack parts carry them) and `topRoundMesh` on the
three magazines; `mounts.notes` on each gun (the units of `at`); `presentation.magazine.topRound`.

## 4. Unproven: nobody has run any of it

Everything above was checked against the data's own rules, the art manifest and the source code read, not in the engine. In particular:

- the box has not imported any of the new meshes, so no asset path above has been loaded;
- `MM_Rifle_Fire` (the arms' fire clip of the four new hand-IK sets) is on the plan's list of box assets, nobody here saw it, and
  `FirstPerson.Clips` fails loudly if it is not on the arms' skeleton;
- the first-person values (`shoulders [-6, 0, -24]`, `fireWeight 0.45`, `bobScale 0.6`, `relief`) are starting values: rifles reach 25 to
  45 cm to the support hand and the NINE needed three review rounds;
- whether `HideBoneByName` hides on the first-person gun (a poseable component) and whether the part frame needs the bone's reference-pose
  rotation undone (the plan's G1, G2) are for the box engineer's probe; the data only names the bones;
- the SHORTY's eye (relief 0.12) ends 14 mm ahead of its butt face: the near plane may slice the cheek rise; 0.14 is the fallback in its notes;
- the STRETCH and the RATTLER are exported with draft textures at the time of writing; the data holds for the final bake (same names).

## 5. Re-running and re-checking

    python3 tools/data/check_guns_data.py --art     # the rules, every build, the ready rule, the art contract and its freshness
    python3 tools/data/make_gun_contract.py         # after a new export: rewrites gun_contract.json from art/out
    python3 tools/data/make_gun_contract.py --check # exits 1 when the contract is stale

When the art lanes re-export a gun, run the generator and read the diff of `gun_contract.json`: a changed socket is a changed
`mounts.<slot>.at` or marker, and the checker says which. The hand-off of the art lanes (`docs/unreal/WEAPONS_R4.md`, `art/out/weapons_r4.json`)
had not appeared when this page was written; when it does, its names and numbers are to be compared with `gun_contract.json`
(the generator already stops on a part socket that disagrees with `weapons_r4.json`).
