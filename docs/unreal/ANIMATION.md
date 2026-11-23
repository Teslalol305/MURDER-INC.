# Animation: the Tactical FPS Animation Pack on the CHOPPER

The user bought the **Tactical FPS Animation Pack - Assault Rifle** (Infima Games, Fab standard licence). This page
says what the pack is, how it was brought into Unreal 5.9 on SK_Mannequin, how its clips were adapted to our
CHOPPER, and which clip plays for every weapon state and event of the rules (spec 02, `Weapons/MIWeaponRules.h`).

**Licence.** The pack may be used in the game but not published, and this repository is public. No file from the
pack or derived from it (FBX, GLB, .blend, .uasset, baked or adapted copies) is ever committed. They live on the box
under `/project/ue/packs/tactical-rifle/` (the adapted set under `adapted/`) and in the projects' `Content/` folders,
which are not in git. The scripts in `tools/box/anim/` and the JPEG proofs in `docs/unreal/shots/anim-*.jpg` are
ours. The same holds for Epic's mannequin content.

## 1. The pack, measured

Facts from `tools/box/anim/bl_inspect.py` (every FBX parsed with Blender 5.x on the box, compared with the mannequin
export `SKM_Manny_Simple.glb`; raw output `/project/ue/animpack/facts/inspect.json`) and `bl_rig.py` (the Blender
rig; `facts/rig.json`).

| Fact | Value |
|---|---|
| Character skeleton | 88 bones in all 109 character clips, **the UE5 mannequin skeleton bone for bone**: same names, same parents, same rest pose (largest joint offset from SK_Mannequin 0.014 mm). The 89th mannequin bone, `root`, is the FBX armature node itself. No extra bones: the IK bones (`ik_foot_root`, `ik_foot_l/r`, `ik_hand_root`, `ik_hand_gun`, `ik_hand_l/r`), `interaction` and `center_of_mass` are the mannequin's own. No camera bone. |
| First person | The FP clips animate the **whole mannequin body** (legs, spine, head) seen from the head; there is no separate arms rig. The arms-only SK_RuleArms (same skeleton) plays them unchanged. |
| Frame rate, units, axes | 30 fps (FBX time mode 6) for every clip; `A_TFA_WEP_AR_Reference` alone is a 2-frame PAL pose. Unit scale 1.0 (centimetres), Z up, front −Y; FBX 7.3 from FBX SDK 2020.2. Blender source made with Blender 4.5, scene 30 fps. |
| Clips | FP: Combat 23, Interactions 7, Locomotion 17, Poses 10, Transitions 13. TP: Combat 20, Interactions 6, Locomotion 1 (idle only), Poses 7, Transitions 5. Weapon: Common 4, FP 16, TP 11. Props: syringe 2. Lengths in section 6. |
| Weapon rig | Its own 16-bone skeleton under `Root` / `Grip`: `Bolt`, `Bolt_Catch`, `Bullet_Chambered`, `Casing_Jammed`, `Charging_Handle`, `Dust_Cover`, `Eject_Casing`, `Fire_Selector`, `Handguard`, `Magazine`, `Magazine_Release`, `Magazine_Reserve`, `Scope`, `Sight_Rear`, `Trigger`. In Blender every deform bone copies a control bone `CB_*` (plus `LOC_Magazine*` and pivot bones); attachments (grips, laser, sights, silencer, handguards) are separate meshes constrained to `SOCKET_*` empties. The magazine has its own 42-bone rig (30 rounds, follower, springs) for `A_TFA_AR_Magazine_FireDepletion`. |
| The fresh magazine | Is a bone of the rifle, `Magazine_Reserve`: the weapon clips carry it from the chest pouch to the well. The hand does not own it. |
| How the gun is held | The rifle's root hangs from **`ik_hand_gun` with an identity transform** (measured with `mi_anim.py`, and visible in `anim-pack-rifle.jpg`): in the pack's gun space (cm) forward is +Y, left +X, up +Z; right palm at (−3.5, −4.2, −6.2), left palm at (3.4, 28.4, 0.6), magazine (0, 12.3, −7.0), sights at y 1.9 and 39.7, 6.7 cm over the bore. `ik_hand_r` / `ik_hand_l` follow the hands. |

**Skeleton match: identical.** The clips go straight onto `/Game/Characters/Mannequins/Meshes/SK_Mannequin`; no IK
retargeter, nothing lost.

## 2. Import (step 2)

`tools/box/anim/ue_import_pack.py` imports with Interchange: the 109 character clips on the existing SK_Mannequin
into `/Game/ThirdParty/InfimaTFA/Character/{FP,TP}/...`, the rifle `SK_TFA_AR_Default_Combined` and
`SK_TFA_AR_Magazine` with their own skeletons, the Unreal texture set and one material per slot into
`/Game/ThirdParty/InfimaTFA/Weapon`, and the 30 weapon clips on the rifle's skeleton. In the scratch project
`/project/ue/animpack` all 139 imports succeeded (0 failed).

`tools/box/anim/import-animpack.sh <Project.uproject> pack` repeats it headless in any project on the box (editor
stopped); `ONLY=<text>` limits it to matching clips. Tested on a fresh copy of the mannequin project.

Proof, `anim-pack-rifle.jpg`: five SK_Mannequins with the pack's own rifle (and its reserve magazine) on
`ik_hand_gun`: FP aimed idle, FP semi fire, FP quick reload at 1.0 s (old magazine falling, fresh one in the left
hand), FP empty reload at 2.0 s, TP reload at 1.2 s.

## 3. Adaptation to the CHOPPER (step 3)

The pack's M4 and our CHOPPER (`docs/unreal/spec/assets/weapons.json`, `art/blender/assets/weapons.py`,
`SK_Chopper`: origin on the bore at the back of the receiver, +X forward, +Y right, +Z up, cm) differ where the hands
work: our magazine well is 10 cm further forward, the magazine rocks out and in about `MagHinge` (22.2, 0, −4.0) by
24° instead of dropping, the charging handle is on the LEFT at (18.0, −3.8, 1.45) and travels 9.2 cm, there is no
bolt catch, and the sight line sits 5.55 cm over the bore.

Everything is done in Unreal by `tools/box/anim/mi_adapt.py` (transform maths on the clips' component-space poses
read with AnimPose, written back as new AnimSequences on SK_Mannequin), run in batch by `mi_run.py`. Order of
preference, as asked:

1. **Used as is with hand IK onto our gun** (all generic clips, section 6). `ik_hand_gun` becomes the CHOPPER's
   origin, placed so that the pack's right palm lands on our pistol grip at `Palm_R` (4.0, 1.55, −8.5) with the
   palm's flesh 2 cm off the grip face; the right hand is never moved. The left hand is pulled by two-bone IK to
   `Palm_L`'s station (31.5, 0, −6.15), cupping the handguard from below, whenever the pack's left hand is within
   10 cm of its own handguard grip; elsewhere it follows the pack's motion in gun space. Aimed clips get one fixed
   gun-space correction that puts our rear and front sights on the pack's sight line through the eye
   (−5.06, 0.66, 157.55 in component space) with the rules' 16 cm eye relief (spec 02 2.13). SK_Chopper then
   attaches to `ik_hand_gun` with an identity transform. Proof: `anim-grip.jpg` (aimed idle seen square to the
   gun's left side: right hand on the grip, left hand under the handguard), `anim-fp-aimed.jpg` (the same frame from
   the first-person eye: rear sight notch and front post centred).
2. **Adjusted** (the reloads): same performance, new contact points and part timing, retimed piecewise so the rules'
   marks fall on the right frames (spec 02 2.3 and 3.17). The pack has no "old magazine out first" move (its quick
   and empty reloads drop the magazine while the left hand goes to the pouch, the shoulder swinging 33 cm back), so
   0.27–0.68 s plays the pack's own seating motion **backwards** (hand on a seated magazine rocking it out and down),
   cross-faded in and out, then the pack runs forward from its pouch frames. On those frames:
   - 0.067–0.27 the left hand wraps our magazine; 0.40 (`magOut`) it comes free; 0.40–0.53 it rocks 24° forward
     about `MagHinge` and 3 cm down; then it rides in the hand to the pouch, hidden 0.70–0.80;
   - 0.80 (`magShow`) the fresh magazine is in the hand: the pack's hand motion on its `Magazine_Reserve` is mapped
     onto our well; 0.95–1.15 hooked on the front lip at full rock; 1.15–1.44 rocked home about the hinge; 1.44
     (`magIn`) seated; 1.565 tug; 1.625 lets go;
   - tactical: 1.80–2.08 the left hand reaches the LEFT-side charging handle (the pack's hand pose on its bolt catch,
     moved to our knob), press check to 32 % of the travel at 1.93, back by 1.98; return to the handguard by 2.22;
   - empty: 1.70–1.96 to the knob, racked fully back by 2.07, held, let go at 2.155 (the bolt flies home in 0.03 s),
     back on the handguard by 2.66.
   The two-bone IK reaches every target in every frame (largest left-hand error 0.0 cm, FP and TP). Proof:
   `anim-fp-reload.jpg` (first person, 1.10 s: the fresh curved magazine in the left hand at the well),
   `anim-bolt-racked.jpg` (empty reload, 2.08 s, the gun's right side: bolt carrier back, port open, left hand
   over the receiver on the handle), `anim-tp-reload.jpg` (mannequin, TP tactical reload at 0.50 s: magazine rocked
   out in the left hand).
3. **Re-authored**: only the weapon parts, which are ours (next section).

### The CHOPPER's own parts

`SK_Chopper` clips (its skeleton: `body`, `bolt`, `trigger`, `selector`, `magazine` and the socket bones), made by
`mi_stage.chopper_clip` from part values, into `/Game/Weapons/Chopper/Anims`:

| Clip | Length | What moves |
|---|---|---|
| `A_Chopper_Fire` | 0.100 s (play at 1.2 for 720 rpm) | bolt back 92 mm in 0.020 s, home in 0.045 s, trigger held. The compressor resamples bone tracks at 30 fps (the target frame rate cannot be set from Python, and a length that is not a whole number of 30 fps frames trips an engine assertion), so the exact cycle is in the float curves `Chopper_Bolt` (0..1 of the travel) and `Chopper_Trigger`; drive the `bolt` bone from the curve, or from `FMIViewmodelRig::GetParts()` which already has the same numbers (`presentation.json`). |
| `A_Chopper_DryFire` | 0.300 s | trigger in by 0.06, held, out by 0.30 |
| `A_Chopper_Idle` | 1 frame | reference |
| `A_Chopper_ReloadTactical` | 2.233 s | magazine bone rocked, carried, replaced and rocked home in step with the character clip; press check; curves `Chopper_MagVisible`, `Chopper_MagInHand`; markers as below |
| `A_Chopper_ReloadEmpty` | 2.733 s | as above, full rack 1.96–2.155 |

The character reload clips carry the same timing as float curves `Chopper_Bolt`, `Chopper_MagVisible`,
`Chopper_MagInHand`, `Chopper_MagRock` (degrees about `MagHinge`), so the gun can be driven from the arms' clip alone.
The magazine is a separate static mesh: attach it to the `magazine` bone with the inverse of that bone's reference
rotation (the bone carries the glTF axis turn, +90° about X; `mi_stage.rig`), else it sticks out sideways.

### Stored on the box (step 5)

`/project/ue/packs/tactical-rifle/adapted/` (104 MB, never in git):
`manifest.json` (every clip: asset path, source clip, length, aimed correction, markers; engine version; skeleton
paths; licence note), `fbx/` (48 character clips) and `fbx/chopper/` (5 part clips) exported from Unreal,
`uasset/` (the same 53 assets as .uasset, folder for folder under `Content/`).

`import-animpack.sh <Project.uproject> adapted` copies the .uasset set into a project (5.9, and the skeletons at
`/Game/Characters/Mannequins/Meshes/SK_Mannequin` and `/Game/Weapons/Chopper/SK_Chopper_Skeleton`; tested: the
copied reload loads in a fresh project on SK_Mannequin, 2.233 s). `... adapt` rebuilds the adaptation inside the
project from the imported pack instead (needs `pack` first and SK_Chopper at `/Game/Weapons/Chopper/SK_Chopper`).
The FBX exports carry the bone tracks; the sync markers and curves are only guaranteed in the .uasset copies.

## 4. The mapping (step 4)

Clip names are under `/Game/ThirdParty/InfimaTFA/Adapted/` (character, `A_CH_*` generic, `A_FP_/A_TP_Chopper_*`
reloads) and `/Game/Weapons/Chopper/Anims/` (gun). Lengths are the clips' own; "rule" is spec 02. FP is the player
(SK_RuleArms, or the mannequin body). TP is what enemies (Goons) play with the rifle clips and the Goon SMG; the
same clips serve a third-person view of the player.

| State / event (rules) | First person (CHOPPER) | Third person (Goon SMG) | Length vs rule, and how | Notifies / markers |
|---|---|---|---|---|
| Ready, idle (hip) | `FP/Locomotion/A_CH_FP_AR_Idle_Loop_Standing` loop | `TP/Locomotion/A_CH_TP_AR_Idle_Loop` loop | 2.033 / 4.033 s loops, no rule length | — |
| Aimed idle (`Ads` 0..1) | `A_CH_FP_AR_Idle_Loop_Aimed` loop, or pose `FP/Poses/A_CH_FP_AR_Aim_Pose` | `TP/Poses/A_CH_TP_AR_Aim_Pose` | rule aim time 0.18 s (CHOPPER): **blend hip → aimed by `Ads`**; the pack's `Transition_Aim_Start/End` (1.27 / 1.30 s) are far too slow and are not used | — |
| Crouch | `A_CH_FP_AR_Idle_Loop_Crouched`, `Transition_Crouch_Start/End` (1.27 / 1.47 s) | missing (template rifle crouch clips: none) | stance blend at the character's crouch speed; transitions trimmed or skipped | — |
| Walk (8 directions as 4) | `A_CH_FP_AR_Walk_{F,B,Strafe_L,Strafe_R}_Loop_Standing`, `_Aimed` when aimed | **missing in the pack** (TP locomotion is idle only): engine template `Rifle/Walk` and `Rifle/Jog` `MF_Rifle_*` on SK_Mannequin, plus left-hand IK on the SMG | 0.7 s cycles in place; play rate = ground speed / walk speed; blend space by direction. Choose either these or the rules' procedural bob (spec 02 3.16), not both | footsteps come from the rules' `PlayerStep` event, not from notifies |
| Run | `A_CH_FP_AR_Run_F_Loop` | template `MF_Rifle_Jog_*` | 0.7 s cycle, rate by speed | `PlayerStep` |
| Sprint (gun lowered, `SprintBlend`) | `A_CH_FP_AR_Sprint_F_Loop`, weight = `SprintBlend` (17 rad/s spring); `Transition_Run_End` not used | template jog at sprint rate | 0.567 s cycle | `PlayerStep` |
| Jump, fall, land | `A_CH_FP_AR_Jump_Start` (on `PlayerJump`), `Jump_Falling_Loop` while airborne, `Jump_End` (on `PlayerLand`, additive weight by fall speed) | template `Rifle/Jump` | 0.433 / 0.833 loop / 0.933 s; landing scaled by fall speed | — |
| Fire (each `WeaponFire`, 720 rpm) | character: additive `A_CH_FP_AR_Fire_Semi` restarted per round (weight ~0.5; the pack's own motion is under 1 cm), aimed `A_CH_FP_AR_Fire_Aimed`; held trigger may loop `A_CH_FP_AR_Fire_Auto`. The camera kick and the springs stay the rules' (spec 02 2.5, 3.16). Gun: `A_Chopper_Fire` once per round | `A_CH_TP_AR_Fire` additive per round | rule interval 0.0833 s; clips restart per round with 0.03 s blend; gun clip at rate 1.2 | shell eject at 0.020 s (bolt fully back at `Eject`), muzzle flash at 0 — or straight from `WeaponFire` |
| Dry fire (`WeaponDry`) | gun `A_Chopper_DryFire`; the arms keep idle; the rules' dry bump (pitch +0.35 rad/s). The pack's `Fire_Empty` is an M4 last round with the bolt locking back: **not used** (our bolt closes after the last round) | same | 0.3 s; the auto reload follows after 0.32 s by rule | dry click at 0.06 |
| Reload, tactical (magazine not empty) | `FP/A_FP_Chopper_ReloadTactical` + gun `A_Chopper_ReloadTactical` | `TP/A_TP_Chopper_ReloadTactical` + the same gun timing on the SMG (left-hand IK target and magazine bone of the SMG still to set) | **2.233 s vs 2.24**: play rate 0.997 (30 fps quantisation); every stage on its mark: `magOut` 0.40, `magShow` 0.80, `magInsert` 1.15, `magIn` 1.44, `tug` 1.565, `bolt` 1.89 (press check 1.89–1.98), `done` 2.24 | sync markers `MagDetach` 0.40, `MagShow` 0.80, `MagTouch` 1.15, `MagAttach` 1.44, `Tug` 1.565, `BoltPressCheck` 1.89, `Done` 2.24 (track `Chopper`). Ammunition moves on the rules' `magin`, never on a marker |
| Reload, empty | `FP/A_FP_Chopper_ReloadEmpty` + gun `A_Chopper_ReloadEmpty` | `TP/A_TP_Chopper_ReloadEmpty` | **2.733 s vs 2.72**: rate 1.005; marks as above, then `bolt` 1.96 (rack to 2.07), `boltRelease` 2.155, `done` 2.72 | as above with `BoltBack` 1.96, `BoltRelease` 2.155, `Done` 2.72 |
| Reload cancelled (melee, swap, death) | no clip: blend out at the rules' damp rate 16 /s; hand and magazine snap back (spec 02 3.17) | same | — | — |
| Holster (0.28 s) | `FP/Transitions/A_CH_FP_AR_Holster` | `TP/Transitions/A_CH_TP_AR_Holster` | 0.433 s: rate 1.55. The gun must leave the frame by the change-over: the pack only lowers it 18 cm, so the rules' procedural holster offset (spec 02 3.17) stays on top | `holster` sound at start (rules) |
| Draw (0.32 s) | `FP/Transitions/A_CH_FP_AR_Equip_Quick`, range 0–0.53 s (the gun settles by 0.53) | `TP/Transitions/A_CH_TP_AR_Equip_Quick` 0–0.53 | rate 1.66; the rise from out of frame is the rules' `easeOutBack` offset, the clip gives the hands. The full `Equip` (2.37 s, with a charging-handle pull on an M4) is not used | `draw` sound at the change-over (rules) |
| Swap | holster then draw on the other gun | same | 0.28 + 0.32 s | — |
| Melee strike (0.55 s, blow at 0.16) | `FP/Combat/A_CH_FP_AR_Melee_Swing_L` (the flat rifle-butt swing to the left, muzzle left, both hands on: the rule's choreography) | `TP/Combat/A_CH_TP_AR_Melee_Swing_L` | pack contact at 0.27–0.33 s (fastest gun travel), settled by 1.0 s: play range 0–1.0 at rate 1.82 → contact at 0.16, end at 0.55. Alternative thrust `A_CH_*_Melee_Bash_F`: contact 0.333, settled 1.2: range 0–1.2 at rate 2.18 | contact from the rules' `WeaponMelee` (0.16) |
| Inspect | `FP/Interactions/A_CH_FP_AR_Inspect` (5.43 s) | `TP/Interactions/A_CH_TP_AR_Inspect` | the rules have none (`chopper.inspectAfter: 24` is defined and never read, spec 02 2.14): optional idle flourish after 24 s, cancelled by any input. Its left hand is adapted only near the handguard; the M4-specific checks in it are not checked on our gun | — |
| Damage reaction (`PlayerHit`) | none in the pack: the rules' camera shake / punch | engine template `Rifle/HitReact` (8 clips: front light ×4, medium ×2, heavy, back medium) as additive by `PlayerHit.From` | template lengths to read on import | — |
| Death drop (Dropped) | none: the rules drop the gun as a rigid body and the arms leave the view (spec 02 3.15) | engine template `Death` (6: front ×3, back, left, right), gun detached as a rigid body | — | — |

### The NINE (the pack has nothing)

Engine template content `Templates/TemplateResources/High/Characters/Content/Mannequins/Anims/Pistol` on the box,
all on SK_Mannequin and all third person (full body):

| NINE state | Template clip | Covers it? |
|---|---|---|
| Idle, aimed idle | `MF_Pistol_Idle_ADS`, `Aim/MF_Pistol_Idle_ADS1`, aim offset `Aim/AO_Pistol` (+ `_AO_CU/_CD`) | TP yes (aim offset for Goons' pitch); FP no |
| Walk, run | `Walk/MF_Pistol_Walk_*` (8 directions), `Jog/MF_Pistol_Jog_*` (8) | TP yes |
| Jump | `Jump/MM_Pistol_Jump_Start`, `_Fall_Loop`, `_RecoveryAdditive` | TP yes |
| Fire | `MM_Pistol_Fire` (+ `MM_Pistol_Fire_Montage`) | TP yes; FP from the rules' springs |
| Dry fire | `MM_Pistol_DryFire` | TP yes |
| Reload | `MM_Pistol_Reload` (one clip) | TP partly: no tactical / empty split, no slide release; must be retimed to 1.50 / 1.90 s |
| Draw | `MM_Pistol_Equip` | TP yes, retimed to 0.32 s |
| Holster, melee (pistol whip), slide-lock pose, inspect | — | no |

To author or buy for the NINE: all first-person arms clips (aimed and hip idle, fire, dry fire, tactical reload
1.50 s, empty reload 1.90 s with the slide locked back and the thumb on the slide stop at 1.61, holster 0.28, draw
0.32, pistol whip 0.55 with the support hand letting go, slide-lock pose), and in third person the holster, the pistol
whip and the reload split. A handgun pack from the same series, if one is available, would match the rifle clips'
style and could go through the same adaptation (the NINE's sockets are in `weapons.json`); otherwise these are
authored on SK_Mannequin in Blender with the round trip the character agent proved.

## 5. What the game still needs

- Third-person locomotion for the Goons (walk, jog, strafe, crouch, jump, turn in place): the pack's TP set is idle,
  fire, reload, melee, equip and poses only. Engine template rifle locomotion covers it with hand IK onto the SMG.
- The Goon SMG grip: `SM_Weapon_GoonSMG` is a static mesh with no `Palm_R` / `Palm_L` sockets yet; the TP rifle clips
  need a left-hand IK target on it and its own magazine bone or socket for the reloads.
- Hit reactions and deaths: engine template only (TP); first person stays procedural.
- The whole NINE in first person (above).
- A Linked Anim Layer / Anim Blueprint that reads `UMIWeaponComponent::GetView()` and plays this table: not written
  here (the gameplay agent owns the character and the viewmodel).

## 6. Clip list (adapted set, 53 assets)

Character, on SK_Mannequin (`/Game/ThirdParty/InfimaTFA/Adapted/...`), source length = adapted length:

| FP | s | TP | s |
|---|---|---|---|
| Idle_Loop_Standing / Aimed / Crouched | 2.033 | Idle_Loop | 4.033 |
| Walk_{F,B,Strafe_L,Strafe_R}_Loop_Standing / _Aimed (8) | 0.700 | Fire | 1.500 |
| Run_F_Loop | 0.700 | Fire_Empty | 1.167 |
| Sprint_F_Loop | 0.567 | Melee_Bash_F | 2.133 |
| Jump_Start / Falling_Loop / End | 0.433 / 0.833 / 0.933 | Melee_Swing_L | 1.900 |
| Fire_Semi / Auto / Aimed / Empty | 0.833 / 1.500 / 1.500 / 1.167 | Equip_Quick | 0.800 |
| Melee_Bash_F / Swing_L | 2.133 / 1.900 | Holster | 0.433 |
| Equip_Quick / Holster | 1.600 / 0.433 | Transition_Aim_Start / End | 1.000 / 1.033 |
| Transition_Aim_Start / End | 1.267 / 1.300 | Aim_Pose, Idle_Pose | 0.067 |
| Transition_Run_End, Crouch_Start / End | 1.467, 1.267 / 1.467 | Inspect | 5.433 |
| Inspect | 5.433 | A_TP_Chopper_ReloadTactical / Empty | 2.233 / 2.733 |
| Aim_Pose, Idle_Pose_Standing | 0.067 | | |
| A_FP_Chopper_ReloadTactical / Empty | 2.233 / 2.733 | | |

Not adapted (left as imported, usable later): Reload (3.7, retention), Reload_Quick / Empty / Empty_Retain and their
aimed forms (the sources of ours), ClearJam ×3, Grenade throw, GripChange, Heal (syringe), Interact grab / punch /
push, the canted and vertical-grip poses, trigger discipline, Transition_Walk_End. MagCheck, FireModeSwitch,
Melee_Swing_R and the full Equip were added on 2026-11-23 (section 10).

## 7. Scripts and how to run them

| File | What |
|---|---|
| `tools/box/anim/bl_inspect.py`, `bl_rig.py` | facts of the FBX set and the Blender rig (bpy on the box) |
| `tools/box/anim/ue_import_pack.py` | the import (editor, asynchronous, or commandlet) |
| `tools/box/anim/import-animpack.sh` | `pack`, `adapted`, `adapt` for any project on the box |
| `tools/box/anim/mi_anim.py` | reading clips in gun space (measurements of section 1) |
| `tools/box/anim/mi_adapt.py` | the adaptation maths, recipes and clip writer |
| `tools/box/anim/mi_stage.py` | CHOPPER import (with its skeleton saved), part clips, picture stage and rigs |
| `tools/box/anim/mi_run.py` | batch: `adapt_all`, `parts_all`, `export_all`; picture scenes, `gun_cam` |
| `tools/box/anim/editor.sh`, `cmdlet.sh` | the scratch project's editor (MCP port 8003) and commandlets |
| `tools/box/anim/bl_meshes.py`, `bl_measure.py`, `pack_measure.json` | the Meshes/ listing and the rig's sockets; the measured mount points and their committed digest (section 8) |
| `tools/box/anim/ue_import_guns.py` | rifles, parts, magazines, 4K materials, reticle, socket pass, icons (section 8) |
| `tools/box/anim/bl_icons.py` | the white silhouettes and pips (box only) |
| `tools/box/anim/mi_guns.py` | the gun assembly for pictures, the studio, the first-person stage of the camera recipe (section 9) |

Pitfalls met here: a sequence created by `AnimSequenceFactory` has no bone tracks and `set_bone_track_keys` then
returns False without raising (create the track first); a clip whose length is not a whole number of 30 fps frames
crashes the editor when it is compressed (`AnimCompressionTypes.cpp:993`); the Interchange import of a skinned GLB
leaves its new skeleton unsaved, so an editor restart loses it.

## 8. The pack rifles and their parts (LOADOUT.md 6.2)

### 8.1 What `Meshes/` holds

Listed on the box (`FBX_Files_TacticalAssaultRifle/Meshes`, 29 files) and parsed with `tools/box/anim/bl_meshes.py`
(objects, vertex groups, materials, bounding boxes, connected pieces; facts in `/project/ue/animpack/facts/meshes.json`).

| File | What it is | Verts / tris | Material slots |
|---|---|---|---|
| `SK_TFA_AR` | the bare receiver: lower, upper, fixed stock, grip, bolt, charging handle, controls; **no handguard, no irons** | 14,099 / 14,889 | `MI_TFA_AR_01`, `_02` |
| `SK_TFA_AR_{Short,Default,Extended}_Combined` | the whole rifle of one length, **irons standing** | 22,509 / 23,300 / 24,867 verts | `_01`..`_03` (Short), `_01`..`_04` |
| `SK_TFA_AR_{Short,Default,Extended}_Combined_Folded` | the same rifle with **both irons folded flat** (same vertex count) | as above | as above |
| `SK_TFA_AR_Magazine`, `SK_TFA_AR_Magazine_Transparent` | skeletal magazines on the 42-bone magazine rig (follower, 8 spring bones, `Bullet_001..030`; the rounds have no geometry of their own: the rig carries `SM_TFA_AR_Bullet` per bone) | 6,058 / 7,427 | `_02` (+ `MI_TFA_AR_Scope_Glass` on the clear one) |
| `SM_TFA_AR_ATT_Scope` | a prism / holographic-style sight: body, a glass window, a reticle plane | 2,214 | `MI_TFA_AR_ATT_01`, `_Scope_Glass`, `_Scope_Reticle` |
| `SM_TFA_AR_ATT_Silencer` | one piece | 1,408 | `MI_TFA_AR_ATT_01` |
| `SM_TFA_AR_ATT_Grip_Vertical`, `_Grip_Angled` | | 550, 255 | `_ATT_02`, `_ATT_03` |
| `SM_TFA_AR_ATT_Laser` | laser / light unit with its pressure-switch tail | 2,366 | `_ATT_02` |
| `SM_TFA_AR_ATT_Sight_{Front,Rear}[_Folded]` | the folding irons alone, up and down | 579, 781 | `_01` |
| `SM_TFA_AR_Handguard_{Short,Default,Extended}` | the handguards alone (the rig's parts) | 2,504 / 2,824 / 3,462 | `_03` (+ `_04` barrel) |
| `SM_TFA_AR_Magazine_{Full,Empty}`, `_Transparent_{Full,Empty}` | static magazines, rounds baked in or not | 3,010 / 3,842 | `_02` (+ glass) |
| `SM_TFA_AR_Bullet`, `_Bullet_Casing`, `SM_TFA_AR_GunCase`, `_GunCase_Lid` | round, case, transport case | | |

**Per rifle, measured:** the irons and the handguard are **baked into the skinned Combined mesh**, not separate meshes
and not their own sections: the rear sight is skinned to bone `Sight_Rear` (1,631 vertices), the front sight, the
handguard and the barrel to bone `Handguard` (7,568 on the Default); the irons share material slot `_01` with the
receiver. Their folded state is the `_Folded` twin. **The stock is baked into the receiver (bone `Grip`) and is the
same in all six rifles**: the `Grip`-bone vertices of `Combined` and `Combined_Folded` have identical bounds, the
only difference between the twins is the sight height (10.27 cm standing, 8.11 cm folded). **The pack has no folded
stock.** LOADOUT.md's "stock open or folded" reading of `_Folded` is wrong: `_Folded` means folded irons.

Consequences, written into the data: `guns.json variants.open` is the Combined rifle and `variants.open.opticMesh` its
`_Folded` twin, the base mesh whenever an optic is fitted (the standing irons top out at 10.27 cm, above the scope's
10.06 cm sight axis, and would block it; folded they end at 8.11 cm); `variants.folded` (stock) and `stock_folded`
are **missing** (new art), so the stock slot is not offered (`FMIReadiness::OfferedParts` needs two variants).

### 8.2 Import, textures, materials

`tools/box/anim/ue_import_guns.py` (inside a running editor `start()`, as a commandlet `--sync`), after
`ue_import_pack.py` has made the rifle and magazine skeletons:

- the six rifles onto the shared `SK_TFA_AR_Default_Combined_Skeleton` (16 bones, so every weapon clip of the pack
  plays on every length), `SK_TFA_AR_Magazine_Transparent` onto the magazine skeleton, the 18 static parts into
  `Weapon/Attachments`, the magazine's `A_TFA_AR_Magazine_FireDepletion` clip (ue_import_pack leaves magazine clips
  out). Bounds in Unreal equal the Blender measurements to 0.001 cm (gun space: +Y to the muzzle, +X the gun's left,
  +Z up; Unreal = Blender (x, -y, z) for these files; bone `Handguard` at (0, 16.508, 4.41) in both);
- the pack's Unreal texture set at its full **4096 x 4096**: 7 sets (`01`..`04`, `Attachments_01`..`03`) of `_D`
  (sRGB), `_N`, `_ORM`, and `T_TFA_AR_Scope_Reticle_D` (512). **Normal maps: DirectX**, imported without a green flip:
  the Unreal `_N` green channel is exactly 255 minus the Blender (OpenGL) map's (mean difference 0.00002 over the
  image). **ORM packing checked against the Blender folder's single maps**: R = AO, G = roughness, B = metallic, each
  identical to its single map (mean difference 0), so `srgb` off and `TC_MASKS`;
- `Materials/M_TFA_AR_Surface` (BaseColor, Normal, ORM parameters; `RoughnessScale`) and one instance per pack slot
  name (`MI_TFA_AR_01`..`04`, `MI_TFA_AR_ATT_01`..`03`), assigned by slot name; `M_TFA_AR_Glass` (translucent, surface
  per-pixel lighting, smoked 0.22 opacity) on the scope window, `MI_TFA_AR_MagPolymer` (0.32) on the clear magazine;
  `M_TFA_AR_Reticle` on the scope's reticle plane (8.4). The lit close-up of the receiver and the side views
  (`packguns-kit.jpg`, `packguns-lengths.jpg`) were looked at: engraving and knurling read raised and recessed the
  right way round under a raking light, metal and polymer separate in roughness.

### 8.3 Sockets, from measured geometry

`tools/box/anim/bl_measure.py` measures the six rifles and the parts with bpy (facts `facts/pack_sockets.json`, digest
`tools/box/anim/pack_measure.json`, numbers only); the socket pass `ue_import_guns.sockets()` turns the digest into
sockets on both meshes of every length and on the parts, and runs at the end of every import. The pack author's own
attachment frames (the `SOCKET_*` empties of the rig `.blend`, read by `bl_meshes.py`) say where each part's origin
goes; every one was checked against the surface it must sit on. Gun space, cm, identity rotation (+Y is forward on
every socket):

| Socket | Bone | Short | Default | Extended | How it was placed |
|---|---|---|---|---|---|
| `Optic` | `Scope` | (0, 7.936, 6.745) | same | same | the pack's own Scope bone on the receiver rail; rail tooth tops measured at z 7.09, the scope's base clamps from 6.32 to 7.26 around them |
| `MuzzleMount` | `Handguard` | (0, 44.147, 3.54) | (0, 49.655, 3.54) | (0, 58.221, 3.54) | on the bore axis (centre of the muzzle ring, radius 1.018) at the barrel shoulder 5.75 cm behind the muzzle: the radius profile has the 0.842 cm thread relief from 5.0 to 5.75 cm, identical on all three barrels. The author's Short / Extended frames sit there (5.8); his Default frame (48.0) is 1.6 cm further back, so the measurement wins |
| `Muzzle` | `Handguard` | (0, 49.897, 3.54) | (0, 55.405, 3.54) | (0, 63.971, 3.54) | muzzle face, bore axis |
| `Underbarrel` | `Handguard` | (0, 29.689, 0.71) | same | same | the author's grip frame; the bottom rail's underside measured at z 0.976 from y 20 to 34 on every length, the grips' clamps wrap it |
| `Laser` | `Handguard` | (-1.908, 33.874, 3.602) | (-1.908, 38.737, 3.602) | (-1.886, 47.293, 3.602) | the author's laser frame on the right side rail (outer face measured at x -1.867 along the whole rail) |
| `MagHinge` | `Magazine` | (0.007, 12.265, -7.021) | same | same | the Magazine bone (the magazine part's own origin; the well opening measured at y 7.1..15.7, z -5.18); the pack's magazine drops straight, so the "hinge" is the seat |
| `Eject` | `Eject_Casing` | (-0.277, 10.795, 3.875) | same | same | the pack's casing bone in the ejection port (right side) |
| `SightRear` | `Sight_Rear` | (0, 0.844, 9.656) | same | same | centre of the rear aperture (the largest gap, 9.238..10.075, of the rear sight's centre-line vertices) |
| `SightFront` | `Handguard` | (0, 34.489, 9.65) | (0, 39.021, 9.65) | (0, 48.591, 9.65) | front post tip; the sight line is parallel to the bore, 6.11 cm over it |
| `RecoilPivot` | `Grip` | (0, -27.502, 4.019) | same | same | centre of the butt pad |
| `Palm_R`, `Palm_L` | `Grip`, `Handguard` | (-3.5, -4.2, -6.2), (3.4, 28.4, 0.6) | same | same | the palms as the pack's own FP clips hold the rifle (section 1) |

Parts (their own frame, cm): scope `SightEye` (0, -4.322, 3.311) on the author's aim axis (the rig's `AimPoint`
height) at the rear face; silencer `Muzzle` (0, 18.09, 0); vertical grip `SupportHand` (0, -0.092, -4.251) (body
centre); angled grip `SupportHand` (0, -4.542, -2.918) (the rear ramp); laser `Beam` (-1.073, 4.57, 1.606) (the
author's `LaserStart`, 1.5 mm in front of the emitter face).

### 8.4 Every part on every variant, looked at

`tools/box/anim/mi_guns.py` assembles a rifle exactly as `UMIGunAssembly` should: the length's Combined mesh, its
`_Folded` twin when the scope is fitted, every part snapped to its socket with an identity transform, the magazine on
`MagHinge`. All parts were mounted on all three lengths and seen from the side, close up per mount and from the
first-person eye (`packguns-kit.jpg`, `packguns-irons-folded.jpg`, `packguns-fp-scope.jpg`):

- scope on the rail, base clamped round the teeth, irons folded under it, window and reticle on the eye line;
- silencer coaxial by construction (its axis is x 0, z 0 in its frame, the socket on the bore axis: 0.0 cm offset),
  its back cap 0.49 cm behind the shoulder: the barrel enters it, nothing floats;
- grips seated on the bottom rail, laser on the right side rail, clear of the handguard's end on every length;
- the clear magazine shows its rounds: `SK_TFA_AR_Magazine_Transparent` with one `SM_TFA_AR_Bullet` per
  `Bullet_001..030` bone, and `A_TFA_AR_Magazine_FireDepletion` (1 s, one frame per round) held at
  (30 - rounds) / 30 s lifts the follower and scales the spent rounds to zero. That is **RoundsShown**, with no
  material parameter (`attachments.json mag_clear.presentation.fill`);
- **the scope's lens**: `M_TFA_AR_Reticle` is a collimated illuminated reticle, additive and unlit, drawn where the
  view ray (`-CameraVector`) is within 1.5 mrad (dot) or on a 16 mrad ring of the scope's +Y axis, so the dot stays on
  the point of aim from any eye position, as on a real red-dot or prism sight; colour and brightness are parameters.

The pack laser measures **155 mm along the bore** (56 mm without its pressure-switch tail): over the NINE's 50 mm gate,
so the NINE's laser row is dropped (`attachments.json compatibility.nine`) and a compact pistol laser is missing art.

### 8.5 Icons

`tools/box/anim/bl_icons.py` (bpy, Workbench, flat white, transparent film) renders `T_UI_Gun_{Shorty,Stick,Stretch}`
(512 x 192, right side, muzzle right, one scale and one receiver position for the three so the lengths read: alpha
spans x 14..420 / 449 / 494) and pips `T_UI_Att_<id>` (128 x 128) for irons, scope, silencer, both grips, laser and both
magazines; `ue_import_guns.import_icons()` brings them into `/Game/UI/Icons` (UI group, no mips). On the box only
(`/project/ue/animpack/icons`): pictures of the pack's meshes are never committed. `stock_open` / `stock_folded` have
no pip (no stock art of their own).

### 8.6 One command

`tools/box/anim/import-animpack.sh <Project.uproject> guns` (the editor of that project stopped; `all` = `pack` +
`guns`): as root it runs `bl_meshes`, `bl_rig`, `bl_measure` and `bl_icons` with bpy (`/opt/blpy`, made by
`/project/ue/bl/install.sh`; without it the committed `pack_measure.json` and any icons already rendered are used),
then as `ue4` the commandlet `ue_import_guns.py --sync` with `-RenderOffscreen -AllowCommandletRendering` (materials
cannot compile under `-NullRHI`). Tested on a fresh project copy (`/project/ue/animpack-test/GunTest.uproject`, the
mannequin content only, `ONLY=__no_clip__ ... pack` first for the two skeletons): 32 jobs, 0 failed, materials
compiled and assigned, 12 sockets on each rifle, 11 icons, 4 min 45 s including the Blender steps and the first
shader compile.

## 9. The first-person camera recipe

**What the clips say** (measured on the FP clips with `AnimPose`, component space, cm; the mannequin faces +Y):

- the **head joint never moves**: (0, 0.66, 162.58), constant rotation, in every FP clip sampled (idle, aim pose, fire,
  aim transitions, sprint, the reloads, inspect). The pack has no camera bone and no camera curves: the head *is* the camera anchor, the body animates
  around it (the convention of first-person packs on the UE mannequin: a camera on the head, the head kept out of view);
- in `Aim_Pose` and `Fire_Aimed` the M4's **iron sight line passes 0.58 cm under the head joint**, parallel to +Y
  (rear aperture centre at (0, 12.22, 162.0), 11.56 cm ahead). No author documentation of the camera is on the box,
  and the Fab page cannot be reached from here; these two facts fix the camera;
- the hip hold (`Idle_Pose_Standing`, `Idle_Loop_Standing`) is a high ready: rear sight 13.5 cm ahead, 4.6 cm right,
  2.2 cm low. **The `_Aimed` locomotion loops (`Idle_Loop_Aimed`, `Walk_*_Aimed`) hold the gun there too**, not on the
  eye line: only `Aim_Pose` and `Fire_Aimed` are aimed. Aiming is the blend to `Aim_Pose` by `Ads` (section 4);
- the work of reloads and inspect sits 0 to 23° below the eye line (the magazine well at -20 to -23° while the new
  magazine goes in, the left hand lower before it arrives), up to 30° right.

**The recipe** (numbers for `UMIViewmodelRig` / the gameplay agent):

| Item | Value |
|---|---|
| Camera | the eye point `EYE_CS` = component (0, 0.66, 162.0): the head joint lowered 0.58 cm onto the sight line, looking along component +Y, no roll. As a head socket: bone `head`, location (-0.58, 0, 0) in the bone's frame (its X axis points up). The head never moves, so attaching the **arms to the camera** is the same thing: arms mesh relative to the camera **location (-0.66, 0, -162.0), rotation yaw -90** (component +Y onto camera forward) |
| First-person (arms and gun) FOV | **54° vertical = 84.3° horizontal at 16:9** (the game's `player.fov.viewmodel`), with the camera's `bEnableFirstPersonFieldOfView`. Never below **48° vertical** (76.7° h): the magazine work leaves the bottom of the frame. 60° h, tried, shows only the rail and the rear sight; 90° h shows the most hand but makes the gun small |
| World FOV | unchanged: the rules' 74° vertical (106° h), 52° aimed, 30° with the scope (`adsFov`) |
| Near clip | **1 cm** (`r.SetNearClipPlane 1` / Engine settings Near Clip Plane). The default 10 cm cuts the receiver (the charging handle is 8.9 cm from the eye when aimed) and the gloves: one cause of the old proof's fault |
| First-person scale | the game's `presentation.json firstPerson.scale` with `bEnableFirstPersonScale`: keeps the gun out of walls without changing the picture |
| Body | arms only: `SK_RuleArms` (the same skeleton). With a full mannequin on the FP clips, hide `neck_01` (the head sits on the camera) and `thigh_l` / `thigh_r` (`HideBoneByName`, `PBO_None`), and draw the full body as `WorldSpaceRepresentation` / owner-no-see for shadows |
| Aim, irons | blend to `Aim_Pose` by `Ads`: `SightRear` lands on the camera axis (measured 0.001 cm off), eye relief 11.56 cm to the aperture, the front post centred in it (`packguns-fp-irons.jpg`) |
| Aim, scope | base mesh switches to `_Folded` (irons down); the scope's `SightEye` axis is 0.40 cm above the iron line (10.056 against 9.656 over the gun origin), so the aimed pose adds **-0.40 cm along the gun's up axis × Ads** (generally: minus the sight point's offset from `SightRear` across the bore); eye 14.33 cm behind `SightEye` (a collimated sight: relief does not matter) (`packguns-fp-scope.jpg`) |
| Sprint, reload, inspect | the clips as they are; the camera stays on the head (it never moves); camera kick and sway stay the rules' |

**Why the old proof was wrong:** `mi_adapt.EYE_CS` was (-5.06, 0.66, 157.55), the sight-bone line of the hip-ready
`Idle_Loop_Aimed` (bone points 2.9 cm under the real aperture line), so the eye sat 5 cm right and 4.5 cm low, at
the forearm, with the default 10 cm near plane. `EYE_CS` is now the recipe's eye and the CHOPPER's aimed correction
is computed on `Aim_Pose` (`mi_adapt.AIM_CLIP`).

**Proof**, the pack's own rifle (Default length, no IK, `SK_RuleArms`), camera at the recipe's eye, 84.3° h:
`packguns-fp-hip.jpg` (`Idle_Loop_Standing` 0.5 s), `-fp-irons.jpg` (`Aim_Pose`), `-fp-scope.jpg` (`Aim_Pose` + scope,
eye on `SightEye`), `-fp-reload-tactical.jpg` (`Reload` 1.2 s, the new magazine coming up while the old one rides in
the same hand), `-fp-reload-empty-bolt.jpg` (`Reload_Empty` 2.13 s: bolt still back, released between 2.1 and 2.2 s
in `A_TFA_FP_WEP_AR_Reload_Empty`), `-fp-inspect.jpg` (`Inspect` 2.6 s), `-fp-sprint.jpg` (`Sprint_F_Loop` 0.14 s).
Each weapon clip plays at the same time on the rifle; the reserve magazine hangs from `Magazine_Reserve`.
`mi_guns.fp()` builds any of these scenes. The re-adapted CHOPPER was checked the same way (`A_CH_FP_AR_Aim_Pose` from
the recipe's eye, `mi_run.chopper_fp`): rear notch and front post on the screen centre; not committed.

## 10. The CHOPPER's extra roles (LOADOUT.md 6.6)

| Role | Pack clip | State |
|---|---|---|
| Inspect | `FP/Interactions/A_TFA_FP_AR_Inspect` | adapted before (section 6) |
| MeleeA | `FP/Combat/A_TFA_FP_AR_Melee_Swing_L` | adapted before |
| MeleeB | `FP/Combat/A_TFA_FP_AR_Melee_Swing_R` | adapted now (`A_CH_FP_AR_Melee_Swing_R`, 2.0 s) |
| Holster | `FP/Transitions/A_TFA_FP_AR_Holster` | adapted before |
| Draw | `FP/Transitions/A_TFA_FP_AR_Equip_Quick` | adapted before |
| Equip | `FP/Transitions/A_TFA_FP_AR_Equip` | adapted now (`A_CH_FP_AR_Equip`, 2.37 s); its charging-handle pull is the M4's rear handle: the CHOPPER's knob is on the left and is not reached (no reload-style re-authoring); not looked at in a picture |
| MagCheck | `FP/Combat/A_TFA_FP_AR_MagCheck` | adapted now (`A_CH_FP_AR_MagCheck`, 4.6 s), generic: the left hand follows the pack's own motion in gun space away from the handguard, so it works the M4's straight magazine, not our rock-in one; re-authoring it like the reloads (rock-out about `MagHinge`) is still to do; not looked at in a picture |
| ModeSemi, ModeAuto | `FP/Combat/A_TFA_FP_AR_FireModeSwitch` (one clip, played for both) | adapted now (`A_CH_FP_AR_FireModeSwitch`, 0.97 s): the right hand is never moved by the adaptation, so its thumb flicks where the M4's selector sits; the CHOPPER's own lever is on the left (fiction kept from the web game) and is not touched; not looked at in a picture |

The whole adaptation was re-run on 2026-11-23 with this command (3 min: 48 generic clips, 4 reloads with 0.0 cm left-hand error, 5 part clips, 0 failures; export 52 character + 5 gun clips into `adapted/`), so every aimed CHOPPER clip now uses the corrected eye (section 9).

**Re-running everything against a re-exported CHOPPER is one command** (the CHOPPER rebuild is in progress):

    CHOPPER_IN=<folder with glb/SK_Chopper.glb, glb/SM_Weapon_ChopperMagazine*.glb, glb/SM_Weapon_GoonSMG.glb and
      textures/{Chopper,Weapon_ChopperMagazine,Weapon_GoonSMG}> \
      tools/box/anim/import-animpack.sh /project/ue/animpack/AnimPack.uproject chopper

It re-imports SK_Chopper with its 4K set (`mi_stage.import_chopper`, skeleton saved), rebuilds every adapted character
clip and the five part clips (`mi_run.adapt_all`, `parts_all`) and, in the scratch project, exports the .uasset and FBX
copies and the manifest to `/project/ue/packs/tactical-rifle/adapted` (`export_all`), from which `... adapted` copies
them into the game project. The CHOPPER's geometry the adaptation aims at (`mi_adapt.CH`: palms, sights, magazine
hinge, knob, bolt travel) is written in `mi_adapt.py` from `weapons.json`: if the rebuild moves a socket, change `CH`
first.
