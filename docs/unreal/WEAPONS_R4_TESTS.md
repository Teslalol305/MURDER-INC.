# Weapons round 4: the tests the new data changes

For the box engineer, who owns every automation test. The data engineer's commits (`guns.json`, `attachments.json`,
`presentation.json`, `frontend_text.json`, the new `gun_contract.json`) make some existing expectations false. This page
lists each one, with the line it sits on today, and what it must assert instead: the new assertion is as strict as the old
one, nothing is skipped, loosened or re-recorded. No golden file changes (the goldens read `config.json`, and its CHOPPER
and NINE objects are untouched).

**Before you sync and compile**, run the data checker. It needs no engine and takes a second:

    python3 tools/data/check_guns_data.py            # exit 1 on any error; --quiet for errors only
    python3 tools/data/make_gun_contract.py --check  # is gun_contract.json what art/out says now?

It mirrors `ValidateData`, the trade check of LOADOUT.md 3.3, the resolver's arithmetic over every compatible build, the
ready rule in three worlds, and holds every mount, hide bone, part socket, marker and mesh offset to the contract. Where it
says OK the data side of the tests below holds; what is left is code and the box.

## 1. Expectations that are false with the new data

Line numbers are those of the test files as they stood at commit `0e2e653`, just before the data commits; your own edits may have moved them.

| # | Test | Where | Today it asserts | It must assert |
|---|---|---|---|---|
| 1 | `Loadout.DataLoads` | `MILoadoutTests.cpp:84` | `D.Attachments.Num() == 10` | `== 22` (ten pack parts and twelve of our own). When the RATTLER's phase-2 stock variants land: 24. |
| 2 | `FirstPerson.RealArt` | `MIFirstPersonTests.cpp:72` | with art, the CHOPPER's `animSet` is `rifle` | `chopper_ik` (without art: empty, as now) |
| 3 | `FirstPerson.RealArt` | `:74` | `materials` is present exactly when art exists (`IsValid() == bArt`) | `IsValid() == false` in both worlds: `real.materials` (the pack's dark-earth finish) and `real.fingers` (the pack rifle's finger measures) are gone from the CHOPPER's block. Add: `fingers` absent; with art, `meshOffset.rot` is `[0, 0, 0]` and `meshOffset.pos` is `[0, 0, 0]` (SK_Chopper faces +X, as SK_Nine). |
| 4 | `FirstPerson.OpticTwin` | `:90-112`, loop over `shorty`, `stick`, `stretch` with the pack `scope` | with the scope the base mesh is `variants.open.opticMesh`, the animSet is `rifle` | **STICK only** keeps this loop unchanged. For SHORTY and STRETCH, fit `red_dot` and `scope_4x` in turn: the base mesh is `variants.open.mesh` both times (no twin: `variants.open.opticMesh` is absent from the data) and `animSet` is `shorty_ik` / `stretch_ik`. For the RATTLER with `red_dot` the base mesh is `guns.rattler.presentation.realMesh` and the animSet `rattler_ik`. |
| 5 | `FirstPerson.Clips` | `:129` | `Rifle` is `guns.chopper.realMesh`, used as the skeleton that `gun` clips must be on | `Rifle` is the STICK's `variants.open.mesh` (the pack rifle: the only gun that still has `gun` clips). `guns.chopper.realMesh` is now `SK_Chopper`, whose skeleton is another one. The four new sets have `arms.idle` and `arms.fire` only, so the loop covers them with no other change (8 more clips: `MF_Rifle_Idle_ADS` and `MM_Rifle_Fire`, which must be on the arms' skeleton; the plan measured both on the box, nobody here could). |
| 6 | `Frontend.Walk` | `MIFrontEndTests.cpp:86` | `TestFalse("the RATTLER stays hidden", Rack().Contains(rattler))` | The fixture makes every path exist, so the RATTLER (mesh `exists`, Idle `template`) is offered: `TestTrue(...Contains(rattler))`. Then a second readiness whose `AssetExists` is false for any path containing `/Game/Weapons/Rattler/`: the RATTLER is hidden again. |
| 7 | `Frontend.Walk` | `:149` | `TestEqual("CHOPPER: no parts yet", BenchSlots().Num(), 0)` | `BenchSlots() == {optic, muzzle, underbarrel}` (3). The fixture leaves parity guns' mounts as the data says, and the data now says `exists`. Update the comment of the fixture at `:23` ("The CHOPPER's and NINE's mounts stay missing"). |
| 8 | `Frontend.Walk` | `:153` | on the STRETCH, `ChooseBenchSlot(optic); Fit(scope)` | `Fit(scope_4x)`: the pack `scope` is not one of the STRETCH's options any more. `:185` (`STRETCH aimed view 30`) then holds as it is, because `scope_4x` sets `adsFov` to 30. Add: the STRETCH's options are optic `{scope_4x, red_dot}`, muzzle `{suppressor}`, underbarrel `{foregrip_vertical, foregrip_angled}`, magazine `{mag_ext_rifle}`; it has no laser and no stock slot. |
| 9 | `Save.SetupValidation` | `MIFrontEndTests.cpp:255-259` | `S.Guns = {bazooka, rattler}` falls back to the parity guns | With the fixture the RATTLER is offered, so use `{bazooka}` (unknown) and, separately, a readiness whose `AssetExists` is false for the RATTLER's mesh path. Both give the parity guns. |
| 10 | `Save.SetupValidation` | `:262-266` | the NINE carries `{muzzle: silencer, laser: laser}`; both are dropped, the second labelled "a part whose mount is missing" | Both are still dropped, but the second now only because the pack `laser` is not a NINE option. Keep the label honest: set the NINE's `laser` mount `Status = missing` in the test and fit `laser_module`: dropped for its mount. Add: `{muzzle: suppressor_pistol}` is kept (mount exists, mesh exists in the fixture); with `AssetExists` false for `/Game/Weapons/Parts/` it is dropped. |
| 11 | `Attachments.<part>.<stat>` (complex) | `MIAttachmentsTests.cpp:48-82`, `Parsed()` | has no row for `rules.magSize` | Add `{TEXT("rules.magSize"), D.MagSize, 1.0}`. Without it, the three new magazine parts add three `no parsed field for this target` errors. The case list builds itself: 62 new cases (red_dot 4, scope_4x 6, suppressor 9, suppressor_pistol 9, compensator 5, foregrip_vertical 4, foregrip_vertical_wood 4, foregrip_angled 4, laser_module 5, mag_ext_rifle 4, mag_ext_smg 4, mag_ext_pistol 4), 102 in all with the 37 effect cases and 3 baseline cases of today. |

Everything else that mentions the guns keeps passing, checked by reading: `Loadout.ParityResolve` (the CHOPPER's and NINE's top
level in `presentation.json` is untouched; only the `real` block and `realMesh` changed, and the resolver merges `real`
only when the real mesh exists), `Loadout.ParityGolden`, `Loadout.ParityNextPrevious`, `Weapons.ViewmodelRig` (parity guns
only), `Weapons.FourGuns` (resolves the RATTLER with no readiness: the template numbers, as before), `Loadout.BuildPIE`,
`Loadout.PartsScale` (the STICK, skipped without the pack), `Player.ControllerKeys` and `.ControllerPad` (`StartWith` makes
every asset exist: they now equip our STRETCH when its mesh is imported, and a missing mesh only logs), `Audio.EveryGunSounds`,
`FirstPerson.NineMagazine` and every `Golden.*`.

## 2. `Attachments.Builds`: the six cases stay, six are added

The six cases hold (the resolver does not check compatibility; the pack parts are unchanged). Add these, worked out by
`tools/data/check_guns_data.py`'s resolver, which first reproduced the six documented cases to 5e-6. Columns as the test's:
aim time (s), kick (rad), aimed spread (rad), hip spread (rad), heard (m), holster / draw (s), aimed view (deg), damage past the
falloff end where there is one. Tolerance 5e-6 relative, as the existing cases.

| Case | Gun, parts | Aim | Kick | Aimed | Hip | Heard | Holster / draw | View | Far damage |
|---|---|---|---|---|---|---|---|---|---|
| CHOPPER red dot, suppressor | chopper: `optic red_dot`, `muzzle suppressor` | 0.178848 | 0.00646 | 0.001296 | 0.0125 | 18 | 0.31164 / 0.35616 | 52 | 22.1 |
| CHOPPER compensator, wooden grip | chopper: `muzzle compensator`, `underbarrel foregrip_vertical_wood` | 0.202176 | 0.00526592 | 0.0012 | 0.0125 | 51.75 | 0.294 / 0.336 | 52 | none |
| SHORTY carry | shorty: `muzzle compensator`, `underbarrel foregrip_angled`, `laser laser_module`, `magazine mag_ext_rifle` | 0.189237 | 0.00473088 | 0.001144 | 0.0096 | 57.5 | 0.269724 / 0.300846 | 52 | 16.8 |
| STRETCH marksman | stretch: `optic scope_4x`, `underbarrel foregrip_vertical`, `muzzle suppressor`, `magazine mag_ext_rifle` | 0.360278 | 0.0039292 | 0.000539 | 0.012 | 18 | 0.350595 / 0.409028 | 30 | 21.25 |
| RATTLER close | rattler: `optic red_dot`, `muzzle compensator`, `magazine mag_ext_smg` | 0.14065 | 0.003608 | 0.00324 | 0.0094 | 51.75 | 0.26712 / 0.30051 | 52 | 16.25 |
| NINE quiet and long | nine: `muzzle suppressor_pistol`, `laser laser_module`, `magazine mag_ext_pistol` | 0.173094 | 0.00874 | 0.00187 | 0.0084 | 18 | 0.333366 / 0.380989 | 52 | 28.9 |

Add one column for the magazine (`G.Def.MagSize`, an integer, exact) and the reload: SHORTY carry 45 rounds, reload 2.3856,
magOut 0.4256; STRETCH marksman 45, 2.3856, 0.4256; RATTLER close 48, 2.128, 0.3808; NINE quiet and long 24, 1.65, 0.198. The
factory builds of the six guns (a guard that nothing leaks into a bare gun): magSize 30 / 15 / 30 / 30 / 30 / 32 for
CHOPPER / NINE / SHORTY / STICK / STRETCH / RATTLER.

## 3. New tests

| Test | What it asserts | Needs |
|---|---|---|
| `Loadout.TradeBand` | for every non-baseline part, B and W by LOADOUT.md 3.3 (the sum of the absolute logarithms over its better and worse `mul` effects of the stats with `trade` true) are both above zero and B / W is inside `meta.tradeBand`. Assert the table of section 4 to 3 decimals, so a retuned part is a visible edit. A bad fixture (one part with no cost) must be reported, so the test shows it can fail. Also: for every part with a `magSize` effect and every gun that takes it, `base magSize x factor` is a whole number to 1e-9 (the parser truncates). | data |
| `Loadout.DistinctGuns` | with every asset existing, the six guns resolve (no build) to six different `BaseMesh` strings, each own gun's is its `gun_contract.json` asset and the STICK's is the pack's; with none existing, the CHOPPER and the NINE fall back to their template meshes and the other four are not offered. This is the owner's complaint as a regression guard. | data |
| `Loadout.SlotCounts` | with every asset existing: CHOPPER `{optic, muzzle, underbarrel}`, NINE `{muzzle, laser, magazine}`, SHORTY `{optic, muzzle, underbarrel, laser, magazine}`, STICK the same five (its stock slot is hidden: the folded variant has no mesh), STRETCH `{optic, muzzle, underbarrel, magazine}`, RATTLER `{optic, muzzle, magazine}`: 3 / 3 / 5 / 5 / 4 / 3. With no asset existing: only the CHOPPER and the NINE are offered, with no slot. | data |
| `Loadout.SocketContract` | **runs in a clean checkout.** Loads `gun_contract.json` and holds the data to it: every `mounts.<slot>` with status `exists` of the five own guns names a contract socket, its `at` equals the socket to 1e-6, every `hide` is a contract deform bone, a magazine mount's `rideBone` is one; each compatibility `mount` is the gun's mount socket; every own part's mesh is the contract's asset, its `presentation.sockets` values are contract sockets, `socketOffsetsCm` equal the sockets as `(x, -y, z) x 100`, and the guns that list it are exactly the contract's `appliesTo`; every own gun's `meshOffset.rot` is the identity and its six markers equal `(-y, z, -x)` of the exported socket plus `meshOffset.pos` to 1.2 mm; every ik anim set names sockets the gun has. `tools/data/check_guns_data.py` does all of this in Python; this is its engine twin. | data, contract |
| `Loadout.MountsExist` (extended) | on the box with art: also load each own gun's `realMesh` (CHOPPER, NINE, RATTLER; the SHORTY's and STRETCH's `variants.open.mesh` are already covered) and check each mount's socket exists, its position is the contract's within 1 mm (Unreal cm), every `hide` and `rideBone` is a bone of the skeleton; each part mesh: its `SightEye`, `Muzzle`, `SupportHand` and `Beam` static-mesh sockets are the contract's within 1 mm. Today it checks only the variants and the parts, and skips `realMesh`. | box, art |
| `Loadout.PartsOnEveryGun` | on the box with art: for every gun and every part its row offers, assemble that part alone on the gun's mesh (the stage's skeletal component, and the first person gun's poseable one). The part's mesh loads; its mount exists; the part's frame is the gun's (the part's world rotation equals the base's to 0.5 degrees: the check for the bone-frame doubt of the plan); an optic's `SightEye` is within 1 mm of the contract's `Optic + SightEye`; each `hide` bone is really hidden on that component type; the part's bounds are near its socket and not empty; a magazine part follows the `magazine` bone when the bone is moved. | box, art, code |
| `FirstPerson.OwnGunSets` | on the box with art, for `chopper_ik`, `shorty_ik`, `stretch_ik`, `rattler_ik` and `pistol`: every `arms` clip loads on the arms' skeleton; `ik.left` and `ik.right` are sockets of the gun's mesh; `magazine.full` loads as a static mesh and its box sits inside the gun's bounds (1 cm slack) below the bore, as `FirstPerson.NineMagazine` does for the NINE; `magazine.socket` is a bone; `casing` loads (not the NINE's). | box, art |

## 4. The numbers the data now holds

Trade (`B` better, `W` worse, sums of the absolute logarithms; band 0.4 to 2.5). The pack parts are unchanged.

| Part | B | W | B / W | | Part | B | W | B / W |
|---|---|---|---|---|---|---|---|---|
| scope (pack) | 0.3567 | 0.5625 | 0.634 | | scope_4x | 0.3567 | 0.5625 | 0.634 |
| silencer (pack) | 0.9676 | 0.4111 | 2.354 | | suppressor, suppressor_pistol | 0.9676 | 0.4111 | 2.354 |
| grip_vertical (pack) | 0.2904 | 0.1258 | 2.309 | | foregrip_vertical, foregrip_vertical_wood | 0.2904 | 0.1258 | 2.309 |
| grip_angled (pack) | 0.1975 | 0.1133 | 1.743 | | foregrip_angled | 0.1975 | 0.1133 | 1.743 |
| laser (pack) | 0.3857 | 0.2115 | 1.824 | | laser_module | 0.3857 | 0.2115 | 1.824 |
| mag_clear (pack) | 0.0619 | 0.0392 | 1.578 | | red_dot | 0.2112 | 0.1258 | 1.680 |
| stock_folded (pack) | 0.3416 | 0.5878 | 0.581 | | compensator | 0.2332 | 0.1790 | 1.303 |
| | | | | | mag_ext_rifle | 0.4055 | 0.2013 | 2.014 |
| | | | | | mag_ext_smg | 0.4055 | 0.2204 | 1.840 |
| | | | | | mag_ext_pistol | 0.4700 | 0.2305 | 2.039 |

The data's slots on the box after the weapons import, as the checker prints them: CHOPPER 3, NINE 3, SHORTY 5, STICK 5,
STRETCH 4, RATTLER 3. On the box before the import (the pack and the NINE only): the STICK offers 5 slots, the CHOPPER and
the NINE offer none (their parts' meshes do not exist yet), the SHORTY, STRETCH and RATTLER are not offered. In a clean
checkout: the CHOPPER and the NINE, no slot.

## 5. What the data asks of the code (the box engineer's list, for reference)

None of this is in the tests above; each item is a place where the data uses something the code does not read yet.

- `mounts.<slot>.rideBone` (new): `FMIGunMount::RideBone`, copied to `FMIResolvedPart`, so a magazine part follows the
  `magazine` bone in a reload. Parsing it is optional for `DataLoads`; ignoring it leaves the part fixed on `MagHinge`.
- `ValidateData` does not compute the trade check, the clamp check on base values or the build check that LOADOUT.md 3.1
  promises. `Loadout.TradeBand` above is the cheapest place to make them real.
- `presentation.<gun>.ejectDir` (new, own guns but the CHOPPER and NINE; web gun space, unit-ish): the casing's direction
  for the hand-IK path, whose sockets carry no rotation. Nothing reads it yet.
- `firstPerson.opticMaterials` now names `M_Part_Reticle` and `M_Part_Lens` as well; the block is applied only in the Pack
  branch of `UMIFirstPersonRig::Equip` today.
- `attachments.<part>.presentation.topRoundMesh` (new, the three magazines): the hideable top round piece. Nothing reads it yet.
- The first-person sets are cloned from the NINE's: `walkSpeed`, `sprintSpeed` and the grip block are not set; `fireWeight`
  0.45 and `bobScale` 0.6 are first guesses, as are the shoulders `[-6, 0, -24]`.
