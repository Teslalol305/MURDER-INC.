# The hands on the guns of weapons round 4 (hands passes, 2026-11-25)

Sections 1 to 5 are the first pass; **sections 6 to 8 are the second pass (the review's findings), and where they differ
the second pass is the current state.**

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

## 5. C++ for the lead, first pass (not edited here; the box engineer owns `MIFirstPersonRig` and `repo-guns`)

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

## 6. Second pass: the review's findings, checked in play (2026-11-25, 18:00 to 19:05 UTC)

The review of the first pass looked at the `h7`/`h8` frames and found the hands still unrealistic in five ways. Each was
checked on fresh frames of the same trial game (`fd8ce12`, `/project/ue/hands/zip`) with this branch's data copied over its
loose `Content/Data`. **Box:** the first box (`ec087d85`) had expired at 17:48; this pass ran on the box that was up after it
(`603980d9`, same `/project`). Its `/project` was cold and shared with a 40-minute compile of another clone, so the loop was
changed (section 6.4).

### 6.1 The findings against the frames

| Finding (review) | Verdict on the frames | Fixed by | Seen in |
|---|---|---|---|
| Support forearm rises vertically from the bottom at the hip, missing aimed (CHOPPER, STRETCH, RATTLER, SHORTY) | **Right** (`h8` `00`, `12`, `18`; `i1` `00`: the shoulder scan `[-10,-14,-7]`, `[-6,-14,-14]`, `[-4,-10,-16]` alone does not change it, `i1` `06`, `09`, `12`). The cause is the wrist: the solve put it straight under the forend, so whatever the elbow does the forearm leaves the hand downward. | Data: the whole support hand rolled about the forend's long axis toward its lower left (25 to 45 degrees, `_rule_grips.py` `SUPPORT_ROLL`), then the shoulders `[-10, -14, -7]` (the STICK's own) on the CHOPPER, STRETCH and RATTLER. On the STRETCH and RATTLER the forearm still rises more steeply than the STICK's: the C++ pole (section 8.2) lets data steer the elbow further. | `m4` `00`, `01`, `12`, `13`, `18`, `19` (hip and aimed); first seen on the RATTLER alone in `i1` `27`, `28`, `33`, `34` |
| RATTLER support fingers stand up beside the sight when aimed | **Right** (`h8` `19`, `20`: a column of fingers right of the red dot). Data as the review read: middle tip 5.4 cm over the bore, 1 to 2.6 cm off the strap. | Data: the RATTLER's hand rolled 45 degrees about the bore (exact on its round strap: the palm keeps its contact), the middle and end phalanges laid round the strap (joint centres 3.6 and 3.45 cm from the bore, the strap is 2.75). Tips now 0.8 to 2.5 cm over the bore (middle finger 2.5, the others 1.8 or less) and 2.3 to 3.4 cm to its right, round the strap's right side instead of standing off it. 35 degrees (`m3`) still showed a fingertip right of the front sight base; 45 (`m4`) shows only the tips at the receiver's right edge, below the optic's base. The middle tip is still above the review's +1.5 cm line: a further roll lifts the wrist onto the left of the gun (worked out for 50 and 60 degrees, not tried in play). | `m4` `19`, `20` (red dot, the review's own view), `m3` `19` (irons); before: `h8` `19` |
| CHOPPER trigger finger hooks up through the guard; firing thumbs point straight out (CHOPPER, STRETCH, SHORTY) | Trigger finger: **right in the data** (end phalanx up 1.6 cm into the receiver; SHORTY's straight up 2.6 cm, the STRETCH's up 1.5 cm). Thumbs: **right in the data** (tips 13 to 16 mm from the solve's own target, pointing left). **Not identified in a frame either way:** at the hip the firing hand sits low behind the gun and under the HUD's weapon bar, and neither the old hook nor the new finger can be told apart in `h8` `00` and `m4` `00` crops. The change is a data change read in `grips.json` only. | Data (`FIRING_TIDY`): the index end phalanx turned down onto the trigger face (CHOPPER tip at y -0.39, z -7.16 cm; dz < 0 on all three), the thumb end laid toward the solve's own thumb target along the left of the grip. Lengths kept. | data only (`grips.json`) |
| Reload: rifle stands 60 to 75 degrees muzzle-up mid-screen, firing hand out of view | **Right** (`h8` `04`, `16`, `22`). | Data: `poses.reload` of the CHOPPER and STRETCH `[0.05, -0.08, -0.26, 0.15, 0.34, -0.7]`, the RATTLER `[0.05, -0.075, -0.27, 0.15, 0.33, -0.7]`: canted (roll -0.7) instead of stood up (pitch 0.4 -> 0.15), 2.5 cm higher. The gun now leans about 45 degrees with the muzzle forward-left. The SHORTY (a bullpup: its magazine is behind the grip) has its own, `[0.12, -0.15, -0.24, 0.12, 0.22, -0.6]`: it stays low on the right, near its hip place, canted; with the shared pose its receiver covered the crosshair (`m3` `10`, `11`). | `m4` `04`, `05`, `10`, `11`, `16`, `17`, `22`, `23` |
| Reload: the support hand opens (V of thumb and index) and holds no magazine, on every hand-IK gun and the NINE | **Right**, on all of them (`h8` `04`, `05`, `16`, `22`; `i1` `04`, `25`, `31`; `m2` `13`, `19`, `25`; `m4` `04`, `05`, `16`, `17`, `22`, `23`). The first report had it only on the STRETCH: that was wrong. Tried in data: the support fingers' curl clip (`fingerCurl`) set to the pack's `A_TFA_FP_AR_Reload_Quick` at 1.1 to 1.35 s and `A_TFA_FP_AR_Reload_Empty` at 1.1 s (run `i1`): no visible change, the hand stays open, so it was put back. With the new reload pose the hand does come up to the magazine (`m2` `05`: the new magazine in the hand under the well) but the fingers stay open. | **C++** (section 8.1): carry the solved grip onto the magazine instead of letting it go. The lead's `reloadCurl` (1f560d7, not yet built) only closes the fingers to a loose fist. Not fixable in the trial game's data. | not yet: needs a build |
| Every aimed optic is a black ring | **Right**, and still so: no data reaches it in this game. | C++ already in the branch (7e120ac, a88dcdc): needs a new package (section 8.4). | `h8` `01`, `19`; `m4` `01`, `19` (unchanged) |
| SHORTY: bullpup receiver fills the hip view and covers half the aimed view | **Right** (`h8` `06`, `07`). | Data, presentation only: the SHORTY's hip view 7 cm lower and 0.05 rad more muzzle-up (`guns.json` `shorty.rules.views`, all three rows the same shift) so the butt sits low at the shoulder pocket instead of beside the cheek; its eye relief 0.12 -> 0.22 m (`shorty.presentation.relief`), so aimed the receiver is further from the eye; its own reload pose (row above). The receiver now takes the lower right at the hip, about as the STRETCH's does, and the reload leaves the crosshair clear (`m4` `06`, `10`, `11`). Aimed, the carry handle and the receiver under it still take the lower middle third (`m4` `07`): that is the carry-handle sight's own picture. `meshOffset` was not changed: the aimed view is placed from the markers in gun space (`FMIViewmodelRig::Equip`), so moving the mesh would have moved the sights off the eye. The grip solve needed no change (it is in the gun's own space). | `m4` `06` to `11`; before `h8` `06` to `11` |

### 6.2 What changed (data and grip code only)

| File | Change |
|---|---|
| `art/blender/assets/_rule_grips.py` | `--tidy` now also: `SUPPORT_ROLL` (the support hand turned about the forend's axis; idempotent: the applied roll is kept in the entry's `tidy` object), `wrap_support` (round forends: RATTLER, STRETCH), `face_support` (box forends: CHOPPER, SHORTY: middle and end phalanges up the right face 0.85 / 0.7 cm off it), `FIRING_TIDY` (index end phalanx onto the trigger, thumb end toward `THUMB_AIM`). Pure geometry, no Blender. A re-solve in Blender is followed by `python _rule_grips.py --tidy` as before. |
| `Content/Data/grips.json` | the four rifles' `hip` and `aim` entries re-tidied (the `aim` entries are not read by this game: section 5 item 4). The NINE is untouched. |
| `Content/Data/presentation.json` | `chopper_ik`, `stretch_ik`, `rattler_ik` `shoulders` `[-10, -14, -7]` (were `[-8, -6, -10]`; the SHORTY keeps `[-6, 0, -24]`); `guns.chopper.poses.reload`; the notes. |
| `Content/Data/guns.json` | presentation only: `poses.reload` of the SHORTY, STRETCH and RATTLER; the SHORTY's `views` (hip) and `relief`. No fire, recoil, spread or timing number changed. `tools/data/check_guns_data.py`: 0 errors, 0 warnings. |

### 6.3 Per gun now (run `m4`, this commit's data; sheets `art/previews/hands_<gun>.jpg`: top row `h8`, bottom row `m4`)

| Gun | Hip | Aimed | Reload | Still open |
|---|---|---|---|---|
| CHOPPER | support hand on the left of the handguard, forearm in from the lower left (`00`) | red dot: no hand or finger beside the optic (`01`, `02`); irons (`m3` `01`): the support hand at the lower left of the gun | canted, muzzle forward-left, the hand comes up to the magazine (`04`, `05`) | the support hand is **open** in the reload (8.1); the red dot's black ring (8.4) |
| SHORTY | receiver low on the right, support hand at the forend's front (`06`, `09`) | carry handle: no arm in view; the receiver takes the lower middle third (`07`, `08`) | its own pose: low on the right, crosshair clear (`10`, `11`); the support hand is below the picture | the hand's grasp in the reload (8.1, not seen: off screen) |
| STRETCH | support hand under the walnut handguard, forearm steeper than the CHOPPER's (`12`, `15`) | irons: clean, support hand at the lower left (`13`, `14`) | canted (`16`, `17`) | the support hand is **open** in the reload (8.1); the forearm's angle (8.2) |
| RATTLER | support hand on the strap round the shroud, wrist out to the left, forearm in from the lower left (`18`, `21`) | red dot: only the fingertips at the receiver's right edge below the optic's base, none beside the optic (`19`, `20`) | canted (`22`, `23`) | the support hand is **open** in the reload (8.1); the red dot's ring (8.4); the trigger finger about 2 cm off the trigger face (first pass) |
| NINE, STICK | data unchanged; not re-shot in this pass (`h7` `00` to `05`, `30` to `35`). The NINE's reload has the same open support hand (8.1) | | | |

### 6.4 How the frames were made this time

The first engineer's loop (`try.sh`: a `git pull` of the box clone, then `lag-test.sh`) stalled on the cold box: the pull of 25
commits sat in `git merge` for 12 minutes, and a run's game took more than 3.5 minutes to start, so `lag-test.sh` stopped it
at its time limit before the first frame (`runs/i1-fail*`). Changes: `t/try2.sh` takes the data from a folder (the sandbox's
`Content/Data` uploaded as a tar and fetched on the box: `data/d1` to `data/d3`), runs `lag-test.sh` from a copy of the box
tools (`/project/ue/hands/boxtools`), with `viewer=0` (the frames are the game's own `HighResShot`s, no stream needed) and
`secs=840`; `t/fin2.sh` waits for the script's last screenshot, stops the game, labels the frames and sends them back. Reading
the 2.2 GB `.ucas` once (`cat > /dev/null`) before the game brought its start from minutes to seconds. `i1` still ran at 2.5 to
8 frames a second (the other clone's compile took 10 of 16 CPUs), which stretches the reload against the script's waits:
its reload frames are at other moments than `m2`'s and `m3`'s. `m4` is the proof run of this commit's data (`t/s4.txt`: `s3.txt` with a red dot fitted on the CHOPPER and RATTLER at the Workbench, CLEAN: no other game on the GPU; another clone's editor commandlet ran beside it, which slows frames, not poses: every shot is taken on the script's game time). **Another agent** was working in `/project/ue/hands` at the same
time (`t/try3.sh`, a copy of the zip in `/var/tmp/hz`, its own run also named `i2`); this pass's runs are `i1`, `m2`, `m3`, `m4`
(`t/NOTE-two-agents.txt` says so on the box).

## 7. What was seen and what was only read

- **Seen in play** (frames looked at, this pass): the support forearm and hand at the hip and aimed on all four rifles (`m3`, `m4`); the RATTLER's fingers with irons (`m3`) and with a red dot (`m4`); the canted reloads and the SHORTY's own reload (`m4`); the open support hand in every reload (`m4`); the black optic ring (`m4`).
- **Only read** (data and code, not identifiable in a frame): the firing hand's trigger finger and thumb (`FIRING_TIDY`); why `fingerCurl` cannot close the hand in a reload (the trial game's `UpdateHands`, `fd8ce12`); every line of section 8.
- **Not re-shot:** the NINE and the STICK (their data did not change; `h7` stands).

## 8. C++ for the lead, second pass (not edited here; the box engineer owns `MIFirstPersonRig` and `repo-guns`)

Line numbers are this branch's `Source/MurderInc/Weapons/MIFirstPersonRig.cpp` at `ef77ab7` (last changed by 1f560d7, the lead's
uncompiled review fixes: `armStretch`, `foregripCurl`, `reloadCurl`, the pack gun's tick). Section 5's items 1 (optic fade), 2
(`armsFallback`) and 5 (the crash) still stand; items 3 and 4 are replaced by 8.2 and 8.3 below.

### 8.1 The support hand holds the magazine in a reload (must-fix: both reviewers, every hand-IK gun and the NINE)

**What the frames show.** In every reload the support hand is open, thumb and index finger up in a V, under or beside the
magazine and touching nothing (`h8` `04`, `05`, `16`, `17`, `22`, `23`; `h7` `04-nine-reload`, `26`; this pass `m3` and `m4` `04`,
`05`, `10`, `11`, `16`, `17`, `22`, `23`). **Cause** (`UpdateHands`, lines 1238 to 1248): in a reload the palm target is lerped to
the magazine's base pad and `L.ShapeWeight *= 1 - Smooth(K)` lets the solved grip go within 0.15 s, so the fingers fall back to the
pack idle's own `hand_l`, which is an open hand. **Not fixable in data in the trial game:** pointing the set's `fingerCurl` clip at the
pack's `A_TFA_FP_AR_Reload_Quick` (1.1 to 1.35 s) and `A_TFA_FP_AR_Reload_Empty` (1.1 s) changed nothing visible (run `i1`). The
branch's `reloadCurl` (1f560d7, 35 degrees, not yet built) gives a loose fist; that is better than the open hand but still holds
nothing. The change that makes it hold the magazine:

1. **Carry the support grip onto the magazine instead of letting it go** (lines 1238 to 1248). The solved support hand is a hand
   wrapped round a 5 to 6 cm forend; a rifle magazine body is 2.5 x 7 cm, so the same shape moved with the palm onto it reads as a hand
   cupping the magazine from below, which is what a real reload looks like while the magazine is seated. Replace the block's last
   line:
   ```cpp
   // the support grip goes with the hand: the solved points moved with the palm from the forend (the gun's
   // LeftSocket) to the magazine's base pad, so the fingers stay closed round the magazine instead of falling open.
   // A translation only: the hand keeps the turn it had on the forend (palm up, fingers round the body).
   const FVector Shift = ArmsWorld.InverseTransformVector(Base.GetLocation() - Gun->GetSocketLocation(LeftSocket));
   const float S = static_cast<float>(MIFirstPersonRigPrivate::Smooth(K));
   for (TPair<FName, FVector>& KV : L.Shape)
   {
       KV.Value += Shift * S;
   }
   // L.ShapeWeight is kept (was: L.ShapeWeight *= 1 - Smooth(K))
   ```
   and lengthen the blend from 0.15 s to 0.25 s (`/ 0.25` in `K`): at 0.15 s the hand jumps. With the shape kept, `reloadCurl`
   should drop to 0 for the hand-IK sets (the shape already closes the fingers; a curl on top would sink them into the magazine):
   set `reloadCurl` 0 in `presentation.json` `chopper_ik`, `shorty_ik`, `stretch_ik`, `rattler_ik` when this lands.
2. **Better, as data (when 1 is in):** a `reload` solve per gun in `grips.json`, made by `_rule_grips.py` round the magazine body
   (palm heel on the base pad, index finger along the magazine's front face, the other fingers round its body, thumb on its rear
   face), stored in the magazine bone's space. `Equip` loads it beside `grip.pose` (line 376, a third `GripPoints` map), and the
   block above lerps the support `Shape` from the carried hip solve to the reload solve by `K`.
3. **Acceptance:** reload frames at 0.5 s and 1.1 s (`s4.txt`'s two reload shots) show the support fingers closed round the
   magazine on the four rifles and the NINE.

### 8.2 The support elbow of the hand-IK guns (`supportElbowOut`)

The data changes of this pass (support hand rolled to the forend's lower left, shoulders `[-10, -14, -7]`) already bring the
support forearm in from the lower left at the hip on the CHOPPER and STRETCH (`m3`/`m4` `00`, `12`); on the RATTLER it still rises
nearly vertically (`m4` `18`). `UpdateHands` (line 1194, the `Pull` lambda) never sets `FMIFPHandIK::PoleShift`, so the support
elbow lies in the plane the clip's own elbow gives. Read a camera-space vector next to `supportElbowDrop` in `Equip`:
```cpp
SupportElbowOut = FVector::ZeroVector;   // header: FVector SupportElbowOut;
if (const TSharedPtr<FJsonValue> E = MIJson::Get(Set, TEXT("supportElbowOut")); E.IsValid() && E->Type == EJson::Array && E->AsArray().Num() == 3)
{
    SupportElbowOut = FVector(E->AsArray()[0]->AsNumber(), E->AsArray()[1]->AsNumber(), E->AsArray()[2]->AsNumber());
}
```
and in the `Pull` lambda, after `IK.bRotation = false;` (line 1209):
```cpp
if (bLeftHand && !SupportElbowOut.IsNearlyZero() && Camera)
{
    // camera space (X forward, Y right, Z up), cm: the support elbow pushed out and down from the clip's own pole
    IK.PoleShift = ArmsWorld.InverseTransformVectorNoScale(Camera->GetComponentQuat().RotateVector(SupportElbowOut));
}
```
In the reload block scale it out with the grip (`L.PoleShift *= 1.0 - Smooth(K);`): in a reload the hand goes down to the
magazine, and an elbow pushed out would bring the upper arm into the picture. Data to start from: `"supportElbowOut": [-5, -25, -10]`
on `rattler_ik` (and `[-3, -12, -6]` on `chopper_ik` and `stretch_ik`, which need less); tune against the STICK (`h7` `30-stick-hip`,
`31-stick-aim`: the forearm enters from the lower left at about 45 degrees).

### 8.3 The aimed solve

`grips.json` has a hip and an aimed solve per rifle; `Equip` reads one (`grip.pose`, line 376). Load both and lerp the points by
`W.Ads` in `UpdateHands` (two point maps, `FMath::Lerp` per point). They differ by under 1 cm on the support hand: polish.

### 8.4 The optic housing

Every aimed optic is still a black ring in this game (`h8` `01`, `19`; `m4` `01`, `19` with red dots). The fade (7e120ac) and the
masked hardware material (a88dcdc) are in the branch; only a new package shows them. Re-take `s4.txt`'s aimed frames with it.
