# The hands on the guns of weapons round 4 (hands pass, 2026-11-25)

The owner, on the trial package: "the hands dont look correct ensure the hands holding the weapons are realistic". This page says
what was wrong on each gun, what was changed (data and the grip solve's points only: no C++ was edited), the frames that show it,
and the C++ the lead should apply. Everything below was **seen in play**: the packaged game of the trial zip
(`/project/ue/cloud/v6trial.zip`, game commit `fd8ce12`), unpacked once into `/project/ue/hands/zip`, with this branch's data
files copied over its loose `Content/Data` before every run. Nothing was rebuilt or repackaged.

## 1. How the pictures were made (the loop)

| Step | What |
|---|---|
| Data | `/project/ue/hands/t/try.sh <run> <patch.json> <demo.txt> <secs>`: pulls the box clone `/project/ue/hands/repo`, copies its `Content/Data/*.json` over the zip's, applies the try's dotted-path patch (`mk.py`), then one `lag-test.sh run-fg` (one game on the GPU: it waits for the others). |
| Driving | The **Development** game of the same zip (`game=dev demo=<script>`): the demo director carries four guns through the menus (`MIMenu fe slot`, `bench`, `fit`), starts a Story run with god mode, then per gun `MIInput weapon<n>`, `ads`, `fire`, `reload`, and `mi.FP.Shoulders` for shoulder scans. The script is written by a small generator (`gendemo.py`, in `/project/ue/hands/t`). |
| Frames | `con HighResShot 1920x1080` from the same script at each pose (hip, aimed, aimed while firing, hip while firing, two reload moments): the game's own picture with the HUD, written to the zip's `Saved/Screenshots`, labelled by `label.py`. The streamed viewer ran too (`lag-test.sh` needs it) but its frames were not used: the in-game shot lands exactly on the scripted moment. |
| Logs | The Development log prints `First person: shoulders in camera space ...` every 2 s and `First person: grip <gun>/<pose>, N + N points` per equip. |

Runs (all CLEAN in `lag-test.sh`'s sense unless said): `h1` (crashed, section 5), `h2` and `h3` (clip and shoulder scans), `h4`
(tidied support fingers, red dots on the CHOPPER and RATTLER), `h5` (pack clips and tidied fingers, shoulders `[-10,-14,-7]`, irons),
`h6` (the same with an optic on each rifle), `h7` (the NINE and STICK, and shoulder scans with reloads on the CHOPPER and SHORTY),
`h8` (the committed data, pulled by the box clone, POLLUTED: see section 4). Run folders: `/project/ue/hands/runs/<run>/` (`j/` the labelled frames,
`game.log`, `summary.txt`).

## 2. What was wrong (the trial frames, and the first runs)

1. **The trial package ran without the rifles' solved grips.** Its `grips.json` had only the NINE, and its game (`fd8ce12`) anchored the
   arms' shoulders only when a solved grip exists (`UMIFirstPersonRig::GripShoulderTranslation` returned early: the "since 2026-11-25"
   change of 7e120ac is not in that game). So the four rifles were placed by the older wrist slide: the template rifle clip's body,
   hung on the firing hand, put the left shoulder in front of the eye. That is the cut upper arm and the "brown ball" (the support fist
   seen end-on) of `g-gun1.jpg`, `g-gun3.jpg`, `g-gun4.jpg`, `gb-gun4.jpg` and the arm across a third of the screen in the reloads.
   With this branch's `grips.json` copied over (all four rifles solved), the same game anchors the shoulders and both hands reach the
   gun (run `h1`, `06-rattler-hip`).
2. **The template rifle clips (`MF_Rifle_Idle_ADS`, `MM_Rifle_Fire`, third person) on the rifles.** The arms' rotation comes from the
   clip's right-hand socket (`HandGrip_R`) laid on the gun's grip (`UMIWeaponComponent::PoseView`), so the clip decides where the body,
   the shoulders and the elbows go. With the third-person rifle clip the support forearm stood straight up from the bottom of the
   picture, and the fire clip (an additive, weight 0.45) swung the left upper arm up into the view on every shot: run `h2`,
   `26-rattler-aimfire.jpg` and `27-rattler-hipfire.jpg` show a whole cut upper arm in the middle of the screen. The pistol clips on a
   rifle (tried on the SHORTY, `h2`) hold it like a pistol.
3. **The support fingers stood out to the right of the handguard when aimed** (`h2` `01-chopper-aim`, `h3` `21-stretch-aim`,
   `29-rattler-aim`): four straight fingers beside the gun like an open hand. The solve keeps the knuckles at the forend's lower right
   edge and the first phalanx up its right face, but its last points (`*_03_l` and `*_tip_l`, the tail of the `_03` bone) run 2 cm away
   from the gun (middle finger 03 -> tip (-0.9, +2.1, +0.9) cm on the CHOPPER), and the game aims each finger bone at those points.
4. Not hands, seen on the way: the fitted red dot's housing fills the aimed view as a black ring (`h4` `01-chopper-aim`,
   `19-rattler-aim`); the fade that removes it (7e120ac, `AimFade`) is in the branch but not in the trial game. The SHORTY aimed
   through its carry handle shows the receiver's top across the lower half of the picture (`h3` `11-shorty-aim`): that is the eye 24 mm
   over the mesh (the data checker says so), the bullpup's own sight picture.
5. **The SHORTY's view was not changed.** The grip helper read its hip view as putting the forend 70 cm out; in play, with the arms
   anchored, both hands reach it at the hip, aimed and in the reload (`h7` `24` to `26`) and the gun reads as a bullpup held at the hip
   (where its butt sits against the body is out of the picture and was not measured) (`art/previews/hands_shorty.jpg`). A view change would also move
   its sprint, reload and strike poses, which share the CHOPPER's gun space; nothing in the frames asks for it, so the view and the
   grip solve stay as they were (only the support fingers tidied).

## 3. What was changed

| File | Change | Why |
|---|---|---|
| `presentation.json` `firstPerson.animSets.{chopper,shorty,stretch,rattler}_ik.arms` | `idle` = the pack's first-person rifle idle `A_TFA_FP_AR_Idle_Loop_Standing`, `fire` = the pack's `A_TFA_FP_AR_Fire_Semi` (same skeleton as `SK_RuleArms`: the STICK plays them, `fingerCurl` already used the idle) | a first-person rifle body: support arm from the lower left, no arm swinging into view on a shot (item 2) |
| same, `shoulders` | `[-8, -6, -10]` for the CHOPPER, STRETCH and RATTLER, `[-6, 0, -24]` (unchanged) for the SHORTY (were `[-8.5, 1.1, -12.4]`, `[-6, 0, -24]`, `[-6.5, 1.1, -12.4]`, `[-2.5, 1.1, -12.4]`) | scanned in play (`mi.FP.Shoulders`, runs `h2`, `h3`, `h7`): `[-8.5,1.1,-12.4]`, `[-6,0,-24]`, `[-12,0,-20]`, `[-4,3,-18]`, `[-10,5,-30]`, `[-14,4,-16]`, `[-10,-14,-7]` (the STICK's own: the pack's view logs `shoulders in camera space V(X=-9.9, Y=-14.3, Z=-6.9) (mode 1)`), `[-8,-6,-10]`. The hands reach the gun with every one of them at the hip and aimed. The solves' values leave the support forearm standing straight up from the bottom of the picture (`h3` `28-rattler-hip`); the STICK's brings it in from the lower left (`h3` `34-rattler-sh-10_-14_-7-hip`) but puts the left upper arm and elbow in the picture as a brown mass in every reload (`h5` `16-stretch-reload`, `h7` `17-chopper-sh-10_-14_-7-reload`); `[-8,-6,-10]` keeps the forearm from the lower left at the hip and the reload hand on the magazine with no arm in view (`h7` `06-chopper-hip`, `10-chopper-reload`). The SHORTY's magazine is behind its grip, so its reload brings the support hand back to the body: with `[-8, -6, -10]` the forearm filled the lower left (`h8` `10-shorty-reload`), with its own `[-6, 0, -24]` only the hand shows (`h7` `26-shorty-sh-6_0_-24-reload`) |
| `grips.json` (rifles, hip and aim, support hand) | the middle and end phalanx points of the four support fingers rebuilt along the forend's face (`_rule_grips.py --tidy`: the proximal segment's direction continued, the end one turned 20 degrees toward the gun's centre line; lengths kept; knuckles, proximal joints, wrist, thumb and the firing hand unchanged) | item 3; `h4` `13-stretch-aim` and later show no fingers beside the handguard |
| `art/blender/assets/_rule_grips.py` | `tidy_support`, `tidy_file`, `--tidy` (pure geometry on the points, no Blender) | the change is reproducible after any re-solve: solve, then `--tidy` |

`guns.json` is untouched: no rules number and no view changed (fire, recoil, spread, timings as they were). `tools/data/check_guns_data.py`:
0 errors.

## 4. Per gun (final data)

Final data: the four sets play the pack's first-person rifle idle and fire clips, the support fingers are tidied, the shoulders are
`[-8, -6, -10]` (CHOPPER, STRETCH, RATTLER) and `[-6, 0, -24]` (SHORTY). Proof run `h8` (this commit's data pulled by the box clone,
no patch: CHOPPER and RATTLER with a red dot, SHORTY and STRETCH on irons; POLLUTED in `lag-test.sh`'s sense: two other jobs' games
started in the same second, which slows the frames, not the poses: the shots are taken on game time), with `h7` for the SHORTY's
shoulders and the NINE and STICK, `h5` for the CHOPPER's and RATTLER's irons and `h6` for an optic on every rifle (aimed, the arms are
out of the picture, so those frames do not depend on the shoulders). The sheets: `art/previews/hands_<gun>.jpg`, each cell labelled
with its run.

| Gun | Hip | Aimed | Firing | Reload | Left as it is |
|---|---|---|---|---|---|
| CHOPPER | firing hand on the grip, support hand under the handguard from the left, forearm from the lower left (`h8` `00-chopper-hip`) | irons: the handguard and front sight, no fingers beside them (`h5` `01-chopper-aim`); red dot: the housing ring (section 5, item 1) | the pack's recoil, no arm in view (`h8` `03-chopper-hipfire`) | support hand down to the magazine, the hand alone in the lower left (`h8` `04`, `05`) | the red dot's ring |
| SHORTY | support hand on the forend's front, firing hand on the grip ahead of the magazine (`h7` `24-shorty-sh-6_0_-24-hip`) | irons through the carry handle (the receiver's top fills the lower half: the bullpup's own picture), red dot and 4x scope rings (`h8` `07`, `h7` `25`, `h6` `07`) | `h3` `13-shorty-hipfire` (same clips and shoulders, before the finger tidy) | the hand comes back to the magazine behind the grip, no forearm mass (`h7` `26-shorty-sh-6_0_-24-reload`); with `[-8, -6, -10]` the forearm filled the lower left (`h8` `10-shorty-reload`), hence its own shoulders | no hip-fire frame with the final data |
| STRETCH | support hand under the walnut handguard, firing hand on the grip (`h8` `12-stretch-hip`) | irons: rear aperture and front post, clean (`h8` `13`); 4x scope ring (`h6` `13`) | `h8` `15-stretch-hipfire` | open support hand under the magazine well (`h8` `16`, `17`) | in the reload the support hand is open (the grip lets go and the pack idle's hand shape shows) instead of holding the magazine |
| RATTLER | support hand on the strap round the shroud, fingertips over its right side, firing hand on the grip (`h8` `18-rattler-hip`) | irons (`h5` `19-rattler-aim`), red dot ring (`h8` `19`) | `h8` `21-rattler-hipfire` | support hand under the magazine (`h8` `22`, `23`) | the trigger finger rests about 2 cm off the trigger face (the solve's note: no room in front of the trigger) |
| NINE | unchanged data; `h7` `00-nine-hip` to `05-nine-reload2` hold as the trial did | | | | |
| STICK | unchanged data (pack mode); `h7` `30-stick-hip` to `35-stick-reload2` as in the trial | | | | |

The trial's faults are gone from every frame of `h4` to `h8`: no cut upper arm, no fist end-on, no arm across the screen in a reload, no
fingers through or beside the gun. `docs/unreal/ANIMATION.md` section 11 ("Shoulders now", the template clips) describes the old sets: it
is not in this pass's files; this page is the current state.

## 5. C++ for the lead (not edited here; the box engineer owns `MIFirstPersonRig` and `repo-guns`)

Nothing here is needed for the hands as they now look; these make them robust and finish the job. File and line numbers are
this branch's at `fae8d28`.

1. **Ship the optic fade (already in the branch, 7e120ac).** The trial game `fd8ce12` predates `UMIFirstPersonRig::OpticHardware`
   and the `AimFade` parameter, so every aimed optic is a black ring filling a third of the screen (`h4` `01-chopper-aim`, `h6`
   `07-shorty-aim`, `13-stretch-aim`, `19-rattler-aim`). No data change can do it. A package of the current branch (with the
   importer's masked hardware material, a88dcdc) is the fix; check it with `h6`'s script.
2. **The rifles' clips now need the pack (`/Game/ThirdParty/InfimaTFA`).** `UMIFirstPersonRig::Equip` (`MIFirstPersonRig.cpp`,
   the `LoadRoles(Obj(Set, TEXT("arms")), ...)` call, line 295) gives up on the whole hand-IK set when one clip is missing, and the gun
   falls back to the template mode. The STICK already needs the pack and every package has it, so nothing breaks today; for a build
   without it, add an optional `armsFallback` object to the set (the template rifle clips) and try it when `arms` fails:
   ```cpp
   if (!LoadRoles(Obj(Set, TEXT("arms")), ArmsMesh->GetSkeleton(), Clips.Arms)
       && !LoadRoles(Obj(Set, TEXT("armsFallback")), ArmsMesh->GetSkeleton(), Clips.Arms))
   {
       return Mode;
   }
   ```
   (`LoadRoles` empties nothing on failure: reset `Clips.Arms` before the second try.)
3. **The support elbow for hand-IK guns.** The pack mode drops the support elbow when aimed (`supportElbowDrop`, `BuildPack`, line
   1053); `UpdateHands` (line 1186, the `Pull` lambda) never sets `FMIFPHandIK::PoleShift`, so a hand-IK gun's elbow only follows the
   clip. Reading the set's `supportElbowDrop` there (`IK.PoleShift = SupportElbowDrop` for `hand_l`) would let the data push the
   forearm further to the lower left at the hip; with the pack's clip it is not needed for the pictures above.
4. **The aimed grip solve is unused.** `grips.json` has an `aim` solve for all four rifles; `Equip` reads one pose (`grip.pose`,
   line 369). Blending hip to aim by `W.Ads` in `UpdateHands` (two point maps, `FMath::Lerp` per point) would follow the solves
   exactly; the two differ by under 1 cm on the support hand (`grips.json`), so this is polish.
5. **A crash seen once, with `HighResShot`.** Run `h1` (the Development game, this zip): the STICK drawn first (pack mode), then the
   RATTLER (hand-IK) drawn and aimed, then `HighResShot 1920x1080`: `SIGSEGV: invalid attempt to read memory at address 0x0` with
   `AnimationContext SkeletalMeshComponent='FirstPersonPackGun' SkeletalMesh='SK_TFA_AR_Default_Combined' AnimInstance='MIFPAnimInst...'`
   (`/project/ue/hands/runs/h1/game.log`, line 1904). The pack gun component stays registered with its anim instance after the rig
   leaves the pack mode; the screenshot's extra render ticks it. Not reproduced with the STICK drawn last (`h2`, `h7`), not seen in
   any Shipping run. Suggested: when `Equip` sets a mode other than `Pack`, `PackGun->SetAnimInstanceClass(nullptr)` and
   `PackGun->SetComponentTickEnabled(false)` (and enable them again on the way back).
