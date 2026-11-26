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

## 9. The C++ of section 8, built and seen in editor play (2026-11-25, 19:10 to 22:30 UTC, box `603980d9`, clone `repo-guns`)

Code: `Source/MurderInc/Weapons/MIFirstPersonRig.cpp/.h` (and one line in `MIWeaponComponent.cpp`, one warning in
`MIFirstPersonAnim.cpp`), data `presentation.json`, checks `tools/data/check_guns_data.py` and the engine test
`MurderInc.FirstPerson.SupportHand` (`Tests/MIWeaponsR4Tests.cpp`). Commits `7c0bc1a`, `833fae5`, `f816d20`, `2a9d999`,
`1b0cfed`. No fire, recoil, spread, damage or timing number was touched: every key below is under `firstPerson.animSets`.

### 9.1 What the code does now

| Item | Code | Data (anim set) |
|---|---|---|
| 8.1 the support hand holds the magazine | `UpdateHands`: in a reload the solved support grip is no longer let go (`ShapeWeight` stays). Its points go with the palm onto the magazine the rig drops and seats (`HeldMag`: our own magazine, or a fitted magazine part riding the same bone), turned about the palm, narrowed across the gun, blended in and out over `magazine.blend` s. The elbow push is let go meanwhile. `KeepsMagazineInHand()`: the magazine bone is no longer shrunk away at the bottom of its drop while the hand holds it (`MIWeaponComponent::PoseView`, the one line), so the hand holds a magazine all through the swap. | `magazine.palm` (cm in the magazine mesh's frame) or `magazine.height` (that fraction up its front face, the palm bone 2 cm in front) or, with neither, under its base; `magazine.turn` [0, -90, 0] (degrees about the gun's X, Y, Z: the handguard grip stood up round the magazine's body, palm on its front, fingers round its right side, thumb up its left); `magazine.squeeze` 0.55; `magazine.blend` 0.25; `magazine.inHand` 1; `reloadCurl` 0 on the four rifles. The NINE has `inHand` 1 only (its grip goes under the base). |
| 8.2 the support elbow | `Pull`: `IK.PoleShift` from `supportElbowOut` (camera space, cm), blended to `supportElbowOutAim` by the aim; console `mi.FP.ElbowOut "x y z"` forces a value for every gun (tuning). | CHOPPER, STRETCH, RATTLER `[-10, -60, -30]`, SHORTY `[-10, -40, -20]` (tuned, 9.3) |
| 8.3 the aimed solve | `Equip` loads `grip.aimPose` ("aim") beside `grip.pose`; `UpdateHands` lerps each point by smoothstep(aim). Only the hands `grip.aimSides` names ("l" by default): the RATTLER's aimed firing solve has the index finger straight off the trigger (6.4 cm from the hip solve's), so the firing hand keeps the hip solve. | `grip.aimSides` (optional) |
| 5.2 `armsFallback` | `Equip`: when a clip of `arms` is missing, the set's `armsFallback` object is tried (clips and the loaded list reset first) before the template way. | none set (optional) |
| 5.5 the pack-gun crash guard (1f560d7) | Read and built: on every `Equip` the hidden pack gun loses its anim instance and its tick (`SetAnimInstanceClass(nullptr)` clears the instance, the pack branch sets the class and the tick again before `SetVisibility(true)`); every other use of the pack gun's anim instance is behind `Mode == Pack`. It compiles and is right as far as reading goes; the STICK -> RATTLER + `HighResShot` crash of run `h1` was not re-run. | |
| Development logs (Development and editor builds) | `First person: reload hold <gun>: on the magazine 1 (k, points), palm N cm from its place on the magazine, middle finger bent N deg` once a reload; `First person: support arm <gun>: elbow bent N deg, forearm at N deg on the screen (90 = straight up), palm N cm off its target, aim N` every 2 s; `First person: <gun> reload palm on the magazine at ... (the magazine's bounds), squeeze, turn, elbow out` per equip; a warning when a solved grip cannot be laid on a hand (never seen). | |

### 9.2 How the frames were made

The box was shared with three other agents running `lag-test.sh` queues back to back (release 3c gate, the menu audit, the
render audit, weapon switching), so `quiet-editor.sh` never saw its 90 quiet seconds after 19:35. The pictures were taken
under `lag-test.sh`'s own rule instead: a run waits until no process named `MurderInc*` runs (`games()`), so
`/project/ue/logs/repo-guns/r4c/hold.sh` waits for no game **and no `lag-test.sh` run alive** for 20 s, holds a placeholder
process named `MurderInc` (so the others' runs wait), starts this clone's editor, runs `gs.sh` (a copy of
`fp/guns-shots.sh` with `SETTLE`, 15 redraws a frame) or `tune.sh` (the same set-up, then `mi.FP.Shoulders` /
`mi.FP.ElbowOut` combinations read from the support-arm log, no pictures), stops the editor and lets go. Twice a hold ran
past the others' 10-minute wait and their next run started beside this editor (about 21:47 and 21:50; the second one for
about 30 s, the editor was stopped by hand): those runs of theirs may read POLLUTED. The first version of the hold also
took the GPU straight back after its own release; `hold.sh` now leaves it to a run that was waiting. Frames: the editor's
play-in-editor `HighResShot` 1920x1080 with the HUD, frozen 1.2 s into a tactical reload (`MIFreezeOn reload 1.2`).

| Run (folder `/project/ue/logs/repo-guns/r4c/<run>/`) | Code / data | What |
|---|---|---|
| `c1` | `7c0bc1a` | CHOPPER hip, aimed (irons), reload: the reload hand cupping the base pad |
| `d1` | `833fae5` (logs) | CHOPPER reload: the log says palm 0.5 cm from the base pad, middle finger bent 99 degrees, yet the frame reads as an open hand right in front of the eye |
| `e1`, `f1` | `f816d20` (turn, height) | CHOPPER and RATTLER hip, aimed, reload; `f1` the RATTLER with the elbow push off on the box copy of the data (the forearm post stays: 9.3) |
| `t1`, `t2` | `2a9d999` (`mi.FP.ElbowOut`, the arm log) | the tuning table of 9.3 (`t1.log`, `t2.log`, lines `TUNE`) |
| `p1` | `1b0cfed` (final data) | CHOPPER, SHORTY, STRETCH hip, aimed, reload (the RATTLER part was cut short to let a waiting gate run have the GPU) |
| `p2`, `p3`, `p4` | `1b0cfed` | optics aimed (red dot CHOPPER and RATTLER, 4x scope STRETCH and SHORTY); the NINE; the RATTLER hip, aimed, reload and the STRETCH reload (9.4) |

### 9.3 The support elbow, tuned by the arm log (runs `t1`, `t2`; hip / aimed, the forearm's slope on the screen)

90 degrees is the forearm standing straight up from the bottom of the picture (the post of section 8.2); the STICK's
forearm comes in from the lower left at about 45. A larger number than 90 leans the other way (the elbow right of the
hand). "Elbow" is the bend between upper arm and forearm (180 = straight).

| Gun, shoulders | none | `[-5, -25, -10]` | `[-10, -40, -20]` | `[-10, -60, -30]` |
|---|---|---|---|---|
| CHOPPER, data `[-10, -14, -7]` | 98 / 120 (elbow 103 / 114) | | 61 / 70 | **52 / 60** |
| RATTLER, data | 95 / 117 to 119 (elbow 87 / 104 to 133) | 69 / 82 | 61 / 64 to 70 | **52 / 57** |
| STRETCH, data | 96 / 117 (elbow 99 / 125) | 69 / 80 | 61 / 68 | (not run; given the CHOPPER's and RATTLER's value) |
| SHORTY, data `[-6, 0, -24]` | 104 / 121 (elbow 116 / 62) | | **57 / 90** | 51 / 87 |
| RATTLER, shoulders `[-4, -14, -7]` | 98 / 118 | 72 / 79 | 62 / 67 | |
| STRETCH, shoulders `[-4, -14, -7]` | 98 / 114 | 73 / | / 65 | |
| CHOPPER, shoulders `[-10, -22, -10]` | | | 61 / 67 | |

What the numbers say: the push of the pole works and saturates (25 cm takes the post from 95 to 69, 60 cm to 52); moving
the shoulders forward or further left changes the bend but hardly the slope. The data now has `[-10, -60, -30]` on the
CHOPPER, STRETCH and RATTLER and `[-10, -40, -20]` on the SHORTY (whose aimed arm is bent to 62 degrees by its own low
shoulders and barely answers the push). The `palm ... off its target` figure of the log is 4 to 5 cm on every rifle: it
measures the palm bone against the gun's `Palm_L` socket, and the solved grip puts the palm that far from it (the grip
decides, not the socket). In `t2` the RATTLER (slot 3, drawn after the SHORTY) read 20 cm off at the hip and aimed, in
`t1` (slot 1) 4.9: not explained (the frames `p4` were to show whether its support hand reached the strap).

### 9.4 What the frames show (looked at, one by one or in contact sheets; crops in `docs/unreal/shots/hands-r4c-*.jpg`)

| Frame (run folder on the box) | Seen | Verdict against the acceptance of 8.1 to 8.3 |
|---|---|---|
| CHOPPER hip, `p1/r4-fp-chopper-hip-el.jpg` (`hands-r4c-p1-chopper-hip.jpg`) | support hand on the left of the handguard, the forearm in from the lower left on a slant | **better**: no post; the slant is shallower than the STICK's 45 only by the numbers (52) |
| STRETCH hip, `p1/r4-fp-stretch-hip-el.jpg` (`hands-r4c-p1-stretch-hip.jpg`) | the same: hand on the walnut handguard's left, forearm from the lower left | **better** |
| CHOPPER, STRETCH aimed (irons), `p1/...-aim.jpg` | the front sight centred, the support hand only at the lower left edge, no fingers beside the sight | as before (good) |
| SHORTY hip, aimed, reload, `p1/r4-fp-shorty-*.jpg` | the support hand is below the picture at the hip and in the reload; aimed, the carry handle and receiver as in 6.1 | nothing to judge of the hand; no post |
| RATTLER hip before the tuning, `f1/r4-fp-rattler-hip-el.jpg` (`hands-r4c-f1-rattler-reload-and-hip.jpg`, right) | a tattooed forearm standing straight up from the bottom to the receiver: the post of 8.2 (the push off, 95 degrees) | **the fault**, measured 95 / 117; tuned to 52 / 57 (9.3), not yet seen in a frame with the final data |
| CHOPPER reload, base pad (`d1`, `hands-r4c-d1-chopper-reload-basepad.jpg`) | the hand right in front of the eye under the dropped magazine, fingers fanned toward the camera | **not a grasp**: the log said palm 0.5 cm from the pad and the fingers bent 99 degrees, but cupping the base reads as an open hand. Hence the turn and `height` (`f816d20`) |
| RATTLER, CHOPPER reload with the turn (`e1`, `f1`; `hands-r4c-f1-rattler-reload-and-hip.jpg`, left) | the hand stood up at the magazine's front, the back of the hand and the fingers toward the camera, large, and **no magazine in it**: the rig shrinks the magazine bone to nothing between the bottom of its drop and its show mark, which is where a 1.2 s reload frame lands | **not yet**: the hand holds air. Hence `magazine.inHand` (`2a9d999`): the magazine stays drawn in the hand through the swap |
| CHOPPER reload with the final data, `p1/r4-fp-chopper-reload.jpg` (`hands-r4c-p1-chopper-reload.jpg`) | canted gun, the support hand under it at the magazine, fingers up round it; the log: palm 0.1 cm from its place, middle finger bent 99 degrees | **closer**; at this size the fingers still read as spread more than wrapped |

### 9.5 The suite, and what was not seen

**Suite:** `tools/box/test.sh MurderInc` on the clone built at `1b0cfed` (the last code and data commit of this section):
**203 passed, 0 failed** (81 s), golden replays included; the new `MurderInc.FirstPerson.SupportHand` passes. (The first run, at
`7c0bc1a`, had 201 passed and 2 failed, `Cloud.QualityApply` and `Cloud.SessionDecision`: the release engineer's tests, fixed
by their `bbc88fd`, which was in the next pull.) `tools/data/check_guns_data.py`: 0 errors, 0 warnings.

**Not seen in a frame** (the GPU was claimed back to back by other lanes' gate runs from 21:50; the runs `p2`, `p3`, `p4` never
started and nothing was taken in their folders):

- the optic housing fade (8.4) on any aimed optic: the red dot on the CHOPPER and RATTLER and the 4x scope on the STRETCH and
  SHORTY. Whether every aimed optic is still a black ring in this build is **unknown** (read only: `AimFade`, `M_Part_Hardware`,
  7e120ac, a88dcdc; the checker's fade checks pass);
- the NINE (its reload with `inHand`, hip, aimed);
- the RATTLER with the final elbow push (only its numbers, 52 / 57 degrees, `t2`) and its reload with `inHand`; the STRETCH
  reload with the final data;
- any reload with `magazine.inHand` (the magazine kept drawn in the hand): it is in `p1`'s code for the CHOPPER and SHORTY
  frames, but the CHOPPER frame is too small to tell a magazine in the hand from the hand itself (`hands-r4c-p1-chopper-reload.jpg`);
- the pack-gun crash of 5.5 (STICK then RATTLER, aimed, `HighResShot`).

To take them, on the box as root, once the GPU is free (it waits for that itself, and holds it fairly):
`cd /project/ue/logs/repo-guns/r4c && setsid nohup bash hold.sh 'p2|GUNS=chopper shorty stretch rattler|OPTICS=chopper=red_dot rattler=red_dot stretch=scope_4x shorty=scope_4x|ONLY=chopper:aim shorty:aim stretch:aim rattler:aim|SETTLE=15' > hold8.log 2>&1 &`,
then the same with `'p4|GUNS=rattler stretch|ONLY=rattler:hip-el rattler:aim rattler:reload stretch:reload|SETTLE=15'` and
`'p3|GUNS=nine|ONLY=nine:hip-el nine:aim nine:reload|SETTLE=15'` (one hold at a time: each starts and stops this clone's editor).

**Still wrong, as seen:**

1. **The reload grasp is not convincing yet.** The support hand now goes to the magazine and keeps the solved grip (the log:
   palm 0.1 to 0.9 cm from its place, fingers bent 99 to 116 degrees), but in a 1.2 s reload frame of the canted gun the hand
   is large and close to the eye, and its fingers read as spread rather than wrapped (`d1`, `e1`, `f1`, `p1` reload frames).
   The turned handguard grip is an approximation; the real fix is 8.1 step 2: a `reload` solve per gun in `grips.json`, made
   round each magazine's own body by `_rule_grips.py`, loaded beside `grip.pose`. The C++ is ready for it in all but the load
   (the carry, turn and squeeze would then be 0). The reload pose itself (`poses.reload` in `guns.json`) brings the magazine
   close to the eye; it is presentation, but it was not changed here.
2. **The forearm slope** is 52 to 61 degrees at the hip and 57 to 70 aimed after the push (the STICK's is about 45; the post was
   95 / 117 to 121): better, not the STICK's. The push saturates; a further step would need the shoulders lower and further
   left together with it, which brought the upper arm into the reloads before (section 4).
3. **The SHORTY** aimed: its support arm is bent to 62 degrees by its own low shoulders and its forearm stands at 87 to 90
   degrees whatever the push (hidden below the picture in `p1`, so not seen as a post).
4. The RATTLER's 20 cm palm gap in `t2` (slot 3 after the SHORTY) against 4.9 cm in `t1` (slot 1): unexplained.

## 10. Fixer pass: the review of section 9, checked against the code and the frames (2026-11-25, 22:15 UTC on, box `603980d9`, clone `repo-guns`)

### 10.1 The findings, checked

| Finding (review of section 9) | Checked against | Verdict |
|---|---|---|
| Reload: an open, spread hand in front of the eye, no magazine in it (must-fix) | the `c1`, `d1`, `e1`, `f1`, `p1` reload frames as the review lists them, and `UpdateHands` | real. The turned handguard grip (`magazine.turn`, `squeeze`) wraps a 5 to 6 cm cylinder; a magazine is a 2.6 to 3.3 cm plank, so the fingers stood off it |
| The CHOPPER palm target hangs in front of its magazine | `Equip`'s rule `B.Max.X + 2` against the magazine's own cross-sections (read from `SM_Weapon_ChopperMagazine.glb`: the front face runs from X 22.6 at the top to 30.2 near the base, a curved magazine whose bounds reach 31.15) | real: at 35 % up the front face is at about 29.9, the palm was put at 33.15. The log's "0.1 cm from its place" measured the IK against that target, not a touch |
| With a fitted foregrip every reload shows the open V hand (`reloadCurl` 35 to 0) | `UpdateHands`: the shape is built only when `!(bLeftHand && bGrip)` | real (code): with a foregrip no shape was ever carried, and the curl was 0 |
| A reload cut short snaps the hand and elbow in one frame | `MagK` computed from the reload clock alone, and 0 when `bReloadingNow` falls | real (code) |
| The SupportHand test checks JSON only | the test | real |
| The optics, the NINE, the final RATTLER and the STRETCH reload were never photographed; the 5.5 crash case not re-run | the `r4c` folders | real: no such frames existed |
| The HUD hides the firing hand | `guns-shots.sh` had no switch | real |
| Gun finishes read as mirror chrome | see 10.4 | |
| SHORTY reload shows no hand and no magazine | see 10.4 | |
| No suite on the pushed head | the clone was at `1b0cfed` | real; the suite has now run on the clone at this pass's commits (10.3) |

### 10.2 What changed

| Item | Code / data | What it does |
|---|---|---|
| 8.1 step 2: a grip solved round each magazine | `tools/data/reload_grips.py` (new, pure Python), `grips.json` `magazines.<static mesh>.l` | Reads each magazine's GLB (`art/out/glb`, in Unreal's convention, the magazine mesh's own frame: the frame the game reads it in; the CHOPPER bounds match the editor log to 0.01 cm) and cuts it into cross-sections every 0.5 cm. The hand (bone lengths and knuckle arc from the CHOPPER hip solve, the palm laid flat) goes palm-on the magazine's **left face** (palm bones 1.5 cm off it), the knuckle line **along the front edge** (a curved magazine's edge leans: the CHOPPER hand leans 31 degrees with it), the middle knuckle 40 % up from the base (45 % on the pistol magazines). Each finger then closes joint by joint (knuckle, middle, end; at most 90, 105, 80 degrees) until that phalanx (radius 0.8 cm) touches the cross-section at its height: the fingers wrap the front edge and lie on the right face. The thumb lies along the left face, rising 35 degrees toward the front, its tip 2 cm under the magazine's top at most. Solved for all eight magazines a hand-IK gun can hold (the five own, three magazine parts): no point sinks into a magazine (deepest point 0.8 cm outside, the finger radius); the index, middle and ring knuckles bend 68 to 90 degrees and their middle joints 18 to 104 (the pinky, below most magazines, 24 to 50 at the knuckle). `--check` re-solves and compares (0.000 cm) |
| The rig takes it | `MIFirstPersonRig.cpp` `Equip` (loads `magazines.<HeldMag's mesh>.l`), `UpdateHands` | In a reload the support hand's shape moves from the hip/aimed solve to the magazine's solve, carried by the magazine's bone (so it holds the magazine all the way down and back up); the palm target is the solve's palm point, not the bounding-box rule. Without a solve for a magazine the earlier turned handguard grip stays (console `mi.FP.ReloadGrip 0` forces it, for comparison pictures) |
| The foregrip regression | `UpdateHands` | With a fitted foregrip the reload grip now fades in with the hand's way to the magazine (`ShapeWeight = grip.weight x hold`) instead of leaving the clip's open hand; `foregripCurl` lets go as the hand leaves the part |
| A reload cut short | `UpdateHands`, `Update` | The hold is a state moved at most `1 / magazine.blend` a second (`FInterpConstantTo` on the frame time), smoothstepped where used: a switch or sprint mid-reload lets the hand and the elbow push go over 0.25 s, not in one frame |
| The reload log | `UpdateHands` | Now also: palm and finger middle/end joints against the **magazine's own bounding box** in its frame (a finger bone lies about 0.8 cm under the skin; the box is a bound, not the surface), and which grip is used. A warning once when a held magazine rides no bone (the hand would never hold it) |
| Test of the C++ | `Tests/MIReloadHoldTests.cpp`, `MurderInc.FirstPerson.ReloadHold` (new) | The real player in the block with the four rifles, fired and reloaded through the keys (R), the rig read every frame: the hold reaches 1 mid-reload and stays at least 10 frames, the support palm target is the magazine's palm point (within 0.5 cm), the shape laid on it has every joint (25 points), the elbow push is let go there and pushed out again after, the magazine stays drawn while held (`magazine.inHand`), the hold never steps more than 1.5 x frame / 0.25 s, and it is back to 0 a second after the reload. Accessors `GetHandPose`, `GetMagazineHold`, `HasReloadSolve`, `MagazinePalmTarget`, `SupportPalmTarget` |
| Data tests | `MurderInc.FirstPerson.SupportHand`, `check_guns_data.py` | Each rifle set's magazine has a reload grip in `grips.json` with the wrist and every joint (within 25 cm of its wrist); the checker wants one for every own magazine and magazine part |
| `grip.note` of the NINE's set | `presentation.json` | No longer says the support grip lets go in a reload |
| Pictures | `tools/box/fp/guns-shots.sh` | `HUD=0` (console `showhud` once the run plays), `RELOADS="0.5 1.2"` (frames at each time into the tactical reload), `SETTLE` |

No fire, recoil, spread, damage or timing number was touched (`guns.json` and `rules.json` unchanged; every key above is presentation).

### 10.3 The suite

`tools/box/test.sh MurderInc` on `repo-guns` synced to `b9ee527` (this pass's last code commit; the branch's head then, with the other lanes' C++ of 00e4899, 9f21cd3, a3e57b0, 68ce52c, 9c409f7 built in): **207 passed, 0 failed** (76 s), golden replays included, `ReloadHold` among them: its log lines show all four rifles drawn with hand IK, the hold at 1.00, the solve round the magazine (25 points), the palm 0.8 to 1.9 cm from the magazine's box and 6 or 7 of 8 finger joints within 1.5 cm of it. The run before (at `8111ae4`) had 206 passed and 1 failed: this pass's own SupportHand bound (30 cm from the magazine's origin is wrong for the CHOPPER, whose magazine mesh is in the gun's frame), fixed in `b9ee527`. `check_guns_data.py`: 0 errors, 0 warnings.

### 10.4 What was seen, and what was not

**No new frame was taken in this pass.** The picture hold (`/project/ue/logs/repo-guns/r4d/hold.sh`, queue `r4d/queue.txt`: the
runs `q1` hands with the HUD hidden at 0.5 and 1.2 s into the reload on the four rifles, `q2` the optics aimed, `q3` the STICK
with its scope, the NINE and the RATTLER aimed after the STICK (the 5.5 crash case), `q4` the reloads with a foregrip on each
of the three guns that take one) waited from 22:42 for the box's GPU rule (no game, no claim placeholder named `MurderInc`
and no `lag-test.sh` run alive) and never got it: the smooth lane's hitch queues (claims of 2 hours, 22:28 to 23:45), the
stream lane (claims of 3,000 to 3,600 s), the menu-fix lane's lag runs, the death lane's editor and claim (2,400 s, extended
by 3,000 s) and the smooth lane's bug queue (3,600 s) followed each other or overlapped without a free second. An editor of
this lane beside them would have broken the rule the task sets (never beside a measured game, one editor at a time). So:

- **Seen only in the engine, not on screen:** the reload grip is laid on the hand and held (the `ReloadHold` test and its log:
  hold 1.00, 25 points, palm 0.8 to 1.9 cm off the magazine's box, 6 or 7 of 8 finger joints within 1.5 cm of it). Whether it
  now **reads** as a hand round a magazine is unknown until a frame shows it. The solve itself was checked in four views
  drawn from its points over the magazine meshes (`docs/unreal/shots/hands-r4c-reload-solve-views.jpg`: a skeleton drawing,
  not a render; thumb magenta, index red, middle green, ring blue, pinky orange; left side, front, below, and a view from
  behind, above and left like the eye's): the palm flat on the left face, the index, middle and ring fingers round the front
  edge onto the right face, the pinky curled under short magazines, nothing inside a magazine. Seen there too: the thumb
  on the STRETCH and NINE reaches past the magazine's front edge (it is long for those short magazines), and the hand's
  heel sits 3 to 4 cm behind the magazine's rear face; both may read wrong on screen.
- **Read, not seen:** the optic housing fade (8.4: `AimFade` on `M_Part_Hardware`, set only for our own part optics in the
  hand-IK branch; the STICK's pack scope has no fade), the NINE, the RATTLER on the final elbow push, the STRETCH reload, the
  foregrip reloads, the HUD-off firing hands, the 5.5 crash case (STICK, then RATTLER aimed, then `HighResShot`).
- **The chrome finish** (should-fix): not changed. The ORM textures the importer reads have roughness (green) 0.45 to 0.59
  on the gun sets (`art/out/textures/*/T_*_ORM.png`, median of the used texels: STRETCH 0.45, SHORTY 0.59, RATTLER 0.51,
  CHOPPER 0.50) and the importer makes them linear (`TC_MASKS`, sRGB off); a finish that mirrors a street sign is not what
  those numbers give, so the cause is in the engine (the material as built on the box, or reflections on the first-person
  meshes). `r4d/mat.py` (queued first) prints each gun's ORM texture flags and slot materials; it never ran.
- **The SHORTY reload** (should-fix): not changed. Its magazine sits behind the grip (mesh X 17 to 23 cm, the grip's palm
  socket at 29.5) under the eye; whether the new grip brings the hand into view, or `poses.reload` (`guns.json`, presentation)
  must lift and roll the gun further, needs the frame.

**The hold is left waiting** (started 23:19, `r4d/hold.log`): it takes the GPU only under the rule above, yields before each
run to any `lag-test.sh` run that starts waiting, runs `queue.txt` to its `END` and stops this clone's editor. Pictures will
land in `r4d/q1` to `r4d/q4`, the material check in `r4d/py-1.log`. If it has been stopped, start it again on the box as root:
`cd /project/ue/logs/repo-guns/r4d && rm -f done.n && setsid nohup bash hold.sh > hold.log 2>&1 &`.

## 11. Seen at last: the visual pass on the integration clone (2026-11-26, from 16:26 UTC, box `8496fd8c`, clone `/project/ue/int/repo`)

The clone is the integrator's: branch head `0017a21` built (its `unreal/` tree `3fbc520`, unchanged by every later push of the
day), the guns imported fresh. Every picture is play in editor in `L_Block` (`tools/box/fp/guns-shots.sh`, 1920 x 1080
`HighResShot`, the world frozen for each frame, `HUD=0` so the firing hand is not under the weapon bar, `RELOADS="0.5 1.1"`
for the two reload frames of 9.5, `SETTLE=15`). The GPU was taken run by run by `/project/ue/logs/int-repo/vis/queue.sh`
(lag-test.sh's rule: it waits until no game, no claim placeholder and no other drawing editor runs, holds a placeholder
named `MurderInc`, starts this clone's editor, runs one picture script with a hard limit of 13 minutes, stops the editor
and lets go; a watcher notes other games and editors every 2 s). Each run below says whether it shared the GPU. Run
folders: `/project/ue/logs/int-repo/vis/<run>/`; the sheets in `docs/unreal/shots/vis-*.jpg` are made from those frames.

| Run | Guns, build | Pictures | GPU |
|---|---|---|---|
| `h1a` | CHOPPER, RATTLER | none: the editor's first start in this clone was busy for minutes after the map loaded and ignored play in editor; `guns-shots.sh` and `death-shots.sh` now ask again (7e39725) | |
| `h1b` | STRETCH, SHORTY, no parts | hip under the El, aimed (irons), reload at 0.5 and 1.1 s, firing | CLEAN (161 samples) |
| `h2` | CHOPPER and RATTLER red dot, STRETCH and SHORTY 4x scope | aimed | frames CLEAN; one sample after the last frame, while this run's editor was stopping, counted another lane's headless editor |
| `h3` | STICK with the pack scope, NINE, RATTLER | STICK hip and aimed, NINE hip, aimed, reloads, firing, RATTLER aimed after the STICK (the 5.5 crash case) | CLEAN (151) |
| `h4` | CHOPPER walnut vertical grip, SHORTY vertical grip, STRETCH angled grip | CHOPPER hip, the three reloads at 0.5 and 1.1 s | CLEAN (264) |
| `h1c` | CHOPPER (red dot kept from `h2`), RATTLER | hip, aimed, reloads at 0.5 and 1.1 s, firing | frames CLEAN (one sample after the last frame, while this run's editor stopped, saw another editor start) |

### 11.1 What the frames show

| Item (9.5's list) | Seen | Verdict |
|---|---|---|
| Aimed optics: red dot on CHOPPER and RATTLER, 4x scope on STRETCH and SHORTY (`h2`, sheet `shots/vis-optics-aimed.jpg`) | the housing is gone as the sight comes up; the red reticle sits in a clear disc; a faint lens disc (the glass, kept on purpose) darkens a circle about a quarter of the frame wide; the 4x scopes magnify | **pass**: no black ring on any of the four |
| STICK's pack scope (`h3`, `shots/vis-stick-scope-and-aims.jpg`) | a holographic sight's square window with the red ring, the frame of the housing round it, the view through it clear | **pass**: no black ring (the pack scope has no fade; it never had a ring) |
| STICK, then RATTLER aimed, then `HighResShot` (5.5) | the picture was taken, the editor kept running | **pass** (no crash) |
| Reload grip at 0.5 and 1.1 s, no foregrip: STRETCH, SHORTY (`h1b`); NINE (`h3`) | STRETCH: an open left hand fills the lower middle of the frame, fingers fanned toward the eye, **no magazine anywhere in the picture**; at 1.1 s a jagged tear across the back of the hand (two skin surfaces through each other). SHORTY: no hand and no magazine in the frame at either time. NINE: the support hand open beside the pistol, fingers spread, no magazine seen | **fail** (8.1's acceptance not met on any gun seen) |
| Reload grip with a foregrip: CHOPPER, SHORTY, STRETCH (`h4`, `shots/vis-hands-reload-eye.jpg`) | the same open hand close to the eye on the CHOPPER and STRETCH; the SHORTY again shows no hand | **fail** |
| The firing hand, HUD hidden (`h1b`, `h4`, `h3`; `shots/vis-hands-hip-hudoff.jpg`) | never seen before this pass. STRETCH and CHOPPER at the hip and firing: thumb and index finger stand apart in a V below the receiver, large and close to the eye, not closed round the pistol grip. NINE: the right hand round the pistol's grip, the support hand cupping it: reads right | **fail** on the rifles, **pass** on the NINE |
| Support arm at the hip, CHOPPER and STRETCH (`h1b`, `h4`) | the forearm comes in from the lower left onto the handguard; the log has the forearm at 49 to 52 degrees (9.3's 52) | as 9.4 (better, not the STICK's 45) |
| RATTLER hip and aimed with the final elbow push (`h1c`, `shots/vis-hands-rattler.jpg`) | hip: the support forearm comes in from the lower left onto the front of the receiver; no post (8.2's fault is gone); the firing hand's thumb and index finger stand apart in a V as on the other rifles. Aimed with the red dot: a hand on either side of the receiver, the reticle clear. Reloads: the same open, fanned hand close to the eye, no magazine seen | elbow: **pass**; firing hand and reload: **fail** (as above) |
| Finish of the own guns | the STRETCH reads walnut and painted metal in one editor session (`h1b`) and as black mirror reflecting the sky in another (`h4`, the same place and light); the materials are wired as they should be (a headless listing: `M_Stretch`, `M_Shorty`, `M_Rattler`, `M_Chopper`, `M_Chopper_Furniture` take base colour from `_BC`, roughness from `_ORM` G, metallic from `_ORM` B, AO from `_ORM` R, normal from `_N`; the ORM textures are linear `TC_MASKS`) | the mirror is textures that were not resident in that session (a black base colour and ORM give roughness 0), not the material: 10.4's "mirror chrome" is this. It must be checked in a package frame (cooked textures, the stream pool of the release) before anyone changes a texture or the importer |
| SHORTY aimed through its irons (`h1b`) | the rear of the receiver fills the lower half of the frame; with the finish fault above it reads as a white and black box | must be judged again once the finish is right |

The development log of the reload frames (`/project/ue/int/repo/unreal/MurderInc/Saved/Logs/MurderInc-backup-2026.11.26-16.35.45.log`):
`First person: reload hold stretch: on the magazine 1 (k 1.00, the solve round the magazine, 25 support points), palm 0.6 cm
from its place, palm 1.9 cm from the magazine's box, 6 of 8 finger joints within 1.5 cm of it, middle finger bent 176 deg`
(the same for the SHORTY). By the engine's numbers the hand is on the magazine with the fingers round it; on the screen it is
not. Either the magazine is not drawn where the hand holds it, or the hand lies on the magazine's face toward the eye and
covers all of it from there. 11.2 says how the next pass tells the two apart.

### 11.2 Trying to see where the hands really are (`s1`, `s2`, `tools/box/fp/hands-side.sh`)

`hands-side.sh` takes, at the hip and at both reload times, the eye's frame, a frame with everything the player carries
hidden but the arms, and frames from cameras beside the eye. In `s2` (CLEAN) the hiding did not hold (the rig shows its
components again every frame: the "hands alone" frames still show the gun) and the side camera could not be made from
Python in the play world (`GameplayStatics` has no `finish_spawning_actor` in this engine's Python; `death-shots.sh`'s
`cam` falls back to the same call, so its side-camera frames are the player's view too, see PLAY.md). What `s2` did give:
the list of what the player carries and draws at the 0.5 s and 1.1 s reload frames (`nogun 1: CharacterMesh0,
FirstPersonGun, StaticMeshComponent_0, _8, _9, _10, _11`: the gun and five static meshes, the fitted parts and the
magazines; which one is the held magazine is not named), and in this session the STRETCH's walnut and painted finish was
right again (the residency case of 11.1).

The likeliest reading, not yet proven by a picture from the side: the reload hand covers the magazine. The solve lays the
palm on the magazine's left face (`reload_grips.py`), the face the eye looks at in the reload pose, and the hand, about
18 cm long against a magazine of 6 x 11 cm (STRETCH), covers all of it 25 to 35 cm from the eye; the engine's own numbers
(palm 1.9 cm from the magazine's box, 6 of 8 finger joints within 1.5 cm) put the hand on the magazine.

### 11.3 For the owner of `MIFirstPersonRig` (not changed here: C++)

1. **The reload hand must show the magazine.** Lay the solve round the magazine from its far (right) face: palm on the
   right face, fingers round the front edge onto the left face toward the eye, thumb on the right face (`reload_grips.py`:
   mirror `palm_off` and the finger closing across the magazine's Y; the C++ takes the points as they are). Then the eye sees
   the fingertips over the magazine's front edge and its whole left face with the rounds above the hand. Acceptance: the
   0.5 s and 1.1 s frames of `guns-shots.sh RELOADS="0.5 1.1" HUD=0` show the magazine's body between the fingers and the
   magazine well on the CHOPPER, SHORTY, STRETCH, RATTLER and NINE.
2. **The torn back of the hand** (`h1b` STRETCH 1.1 s): a finger closed 176 degrees by the log's measure (the middle
   finger's tip pointing back at the palm) pushes the knuckle skin through the palm's; clamp the summed bend of a finger
   to 150 degrees in `ShapeFingers`, or let the solve stop at 150 in `reload_grips.py` (`MAX_BEND` sums to 275 today).
3. **The firing hand on the rifles** (first seen in this pass, HUD hidden): thumb and index finger apart in a V under the
   receiver, not round the grip. Add to the support-arm development log one line for the firing hand like the reload
   hold's (palm bone against `Palm_R`, index tip against the trigger, middle finger's bend) and check whether the 'r'
   solve's 25 points are laid on the right hand at all (`Shape.Num()` of `HandPose.Hands[1]`); the NINE's firing hand
   reads right, the rifles' do not.
4. **Pictures from beside the player.** A console command on `AMIPlayerController` that sets the view target to a camera
   it spawns at an offset in the eye's frame (and back) would let a picture show the hands from the side; Python cannot
   spawn one in the play world here.
5. **The support hand as a ball (READY.md W2's second half), still there.** In the death pictures (`/project/ue/logs/int-repo/vis/d6/`
   `wall-2` to `wall-5`, `stairs-1`, `-2`, `-5`; `shots/vis-deaths-blast-and-ball.jpg`) the player stands against the hot-dog
   cart or the stair rail looking down about 30 degrees, and the support hand fills a
   third of the frame as a skin-coloured ball (a fist seen from its knuckles, at the eye). In the same runs, posed in the
   open (`d5`), it does not happen. Reproduce with `guns-shots.sh` posed against a wall (`MIPose` beside the cart, pitch
   -30) and check what the support arm's IK is asked to reach there (a guess, not proven: the gun's wall pose near an obstacle
   brings the support palm target toward the eye, and an arm that cannot reach it folds into a fist at the lens); a
   support hand that cannot reach its target in the wall pose should let go (IK weight 0).
### 11.4 The suite

222 passed, 0 failed, 0 skipped on the integration clone at `1b37c7b` (`unreal/` tree `edf7a547`, this pass's last
`unreal/` change), golden replays included; PLAY.md, the visual pass. Nothing under `firstPerson` or `grips.json` was
changed in this pass: every hands item of 11.1 is for the rig's owner (11.3).

## 12. Offline reconstruction: the first-person view rebuilt in Blender from the game's own data (2026-11-26, this container; the box not used)

The box's GPU was busy with the release's checks, so this pass rebuilt the first-person view offline from what the game
reads and computes, and looked at it from the eye and from beside the player. Nothing under `unreal/`, `src/` or the game's
data was changed: every finding below is for the owners of the rig (C++) and of the data.

### 12.1 What was built (`tools/box/fp/offline/`)

| File | What it does |
|---|---|
| `fp_math.py` | Pure Python and numpy. The rig's maths as the C++ has it: the gun in camera space (`MIViewmodel.cpp`: `views[0]`, the aimed pose with the rear sight on the axis `relief` ahead of the eye, `poses.reload` weighted by `min(Ease(t / 0.24), Ease((total - t) / 0.3))`, `WebToUE`, `EulerYXZ`, `MeshOffset * GunTransform`); the magazine bone's drop (`UpdateParts`: `out` / `show` / `in` marks); the arms carried so the shoulders' midpoint sits on the set's `shoulders` (`PoseView`, `GripShoulderTranslation`); the IK targets, the solved grips (hip and aimed by smoothstep(aim) for `grip.aimSides`), the reload hold (the support shape taken from `grips.json magazines.<mesh>.l`, carried by the magazine bone), the elbow push let go in the reload (`UpdateHands`); two-bone IK with the pole `L + (L - (U + E)/2) * 2 + PoleShift`, `ShapeHand` (the hand turned so wrist, middle_01, index_01, pinky_01 match the shape's frame) and `ShapeFingers` (each finger bone swung onto its child's point, the `_03` along its parent segment's reference direction) (`MIFirstPersonAnim.cpp`). The `$ref`s and the `real` block are resolved as `MILoadoutResolver` does. |
| `fp_offline.py` | Blender as a Python module (`/home/user/mi-venv`, bpy 5.3.0): imports `SK_RuleArms.glb`, the gun's `SK_*.glb` and its `SM_Weapon_*Magazine.glb` from `art/out/glb`, poses them by `fp_math`, renders from the eye (the first-person vertical field of view: 54 at the hip, 38 aimed on irons; near plane 1 cm / `firstPerson.scale` 0.6), from the right and from above left, and an ID render of the eye's view (gun blue, magazine red, support arm green, firing arm yellow) from which `report.json` counts what each hand covers and how much of the magazine the hands hide (against a render of the gun and magazine alone). Base colour and ORM (G roughness, B metallic) from `art/out/textures`, wired as `mi_fp_import._surface` wires them. What-if flags change data for the run only: `--shoulders`, `--relief`, `--finish zero`, `--tex-set`. |
| `calibrate.py` | Fits the one thing the repository does not hold (below) to the game's development log; `--reach` bounds the firing arm's reach from the log alone; `--scan` looks for a `shoulders` anchor both arms reach from. |
| `validate.py`, `figures.py`, `sheets.py`, `run-all.sh` | The overlays on the game's frames, the evidence sheets, the per-gun contact sheets; `run-all.sh` reruns everything (about 10 minutes on 4 CPUs, one Blender process at a time, output in `art/out/fp-offline`, git-ignored). |

**What is not the game's: the arms' pre-IK pose.** The rifle sets play the pack's idle (`A_TFA_FP_AR_Idle_Loop_Standing`), which is
not in the repository. It enters the result twice: where the clip puts each shoulder about their midpoint (the code anchors
only the midpoint), and the elbow the IK pole starts from. Both were fitted to the development log of 9.3 (`calibrate.py`): the
clip's left shoulder **25.5 cm ahead of, 3 cm right of and 9 cm below** the midpoint (camera space at the CHOPPER's hip, turned
with the gun as the arms component is), which gives the eight logged support-elbow bends within **4.4 degrees rms** (CHOPPER hip
103.3 / log 103, aimed 115.7 / 114; RATTLER 86.6 / 87, 106.1 / 104 to 133; STRETCH 98.4 / 99, 126.6 / 125; SHORTY 116.8 / 116,
64.5 / 62); the pole fits the sixteen logged forearm slopes within 9.5 degrees rms. A level shoulder line (the rest skeleton
turned in any way) cannot give those bends: the support arm does not reach. The NINE plays another clip (the template
pistol idle) and keeps the rest skeleton's shoulders. Everything else in the frames is the game's data and maths.

### 12.2 Checked against the game's frames

`hands-offline-validation.jpg`: nine frames the game took (sections 9 and 11) with the offline outlines drawn over them. The
gun's outline lies on the game's gun in all nine (CHOPPER, STRETCH, RATTLER hip; STRETCH and RATTLER reloads; SHORTY aimed
and reload; NINE reload), the rear sight and the receiver's end within about 1 % of the frame's width and the muzzle within
about 2 % (the idle's breathing and sway frozen in the game's frame; the offline frame has none). The hands' outlines lie on
the game's hands too, which is how the reload fault was read (12.4). The framing (eye, field of view, gun placement) is
therefore the game's; the hand shapes are the game's solve laid by the game's maths.

### 12.3 Fault (2): the firing hand of the rifles stands in a V under the receiver: **it does not reach the grip**

`PoseView` places the arms so the **midpoint** of `upperarm_l` and `upperarm_r` sits on `shoulders` ([-10, -14, -7] on the
CHOPPER, STRETCH and RATTLER); the IK then reaches each hand from its own shoulder, and the firing arm never stretches
(`IK.Stretch` 1 for the right hand). The clip puts the left shoulder far forward (12.1), so the right one sits far back: offline
at **(-35.5, -17, 2) cm**, 35 cm behind and 17 cm left of the eye. From there the firing arm (27.8 + 27.3 = 55.0 cm to the wrist)
cannot reach the solved wrist on the grip, the IK leaves it straight and short, and the hand keeps its solved shape (fingers
closed round a grip that is not there, thumb along a receiver side that is not there) **8 to 17 cm behind and below the pistol
grip, 21 to 24 cm from the eye**: the V of 11.1.

This does not rest on the fitted clip. `calibrate.py --reach` bounds it from the game's own numbers only: the logged support
bend fixes the left shoulder's distance from the support wrist; the right shoulder is the left one mirrored through the
anchored midpoint; so it can come no nearer to the firing wrist than:

| Gun, state (log of 9.3) | Support shoulder to wrist (from the bend) | Firing shoulder to firing wrist, at least | Firing arm (55.0 cm) |
|---|---|---|---|
| CHOPPER hip (bend 103) | 34.3 cm | 62.0 cm | **short by 7.0 cm or more** |
| STRETCH hip (99) | 35.7 cm | 65.9 cm | **short by 10.9 cm or more** |
| RATTLER hip (87) | 39.9 cm | 67.8 cm | **short by 12.7 cm or more** |
| RATTLER aimed (118) | 28.3 cm | 57.6 cm | **short by 2.6 cm or more** |
| CHOPPER, STRETCH aimed; SHORTY | | | can reach |

With the fitted clip the gaps are (wrist to its target): CHOPPER **10.3 cm** at the hip and **8.3** in the reloads (0 aimed), STRETCH **14.2** and **8.9** (0 aimed), RATTLER **16.7**, **10.9** and 4.4 aimed; the SHORTY 2.8 at the hip, 7.8 aimed, 0.4 in the reloads (its own anchor [-6, 0, -24]). The NINE reaches (0 cm at the hip): its anchor
[-6, 0, -24] and its clip keep the right shoulder under the eye, which is why its firing hand reads right in the game.

The development log never said so: the support-arm line (`UpdateHands`) measures the left arm only, and the tests
(`SupportHand`, `ReloadHold`) check the support hand. **What-if** (`hands-offline-reach.jpg`): with the anchor at
**[2, 0, -16]** (`calibrate.py --scan`: the nearest anchor from which both arms reach on the CHOPPER, STRETCH and RATTLER at
the hip, aimed and at both reload times, the firing elbow bent at least 27 degrees) the firing hand closes round the pistol
grip in every frame, from the eye and from the side. From the eye the magazine shows far more once the firing hand is out of the way (the share of the magazine the gun leaves in sight that the hands do not hide, `report.json`): CHOPPER hip 40 % to 94 %, reload 0.5 s 11 % to 61 %, 1.1 s 12 % to 63 %; RATTLER reload 0.5 s 21 % to 91 %; STRETCH reload 0.5 s 7 % to 13 %, 1.1 s 1 % to 5 % (12.7 item 2).

### 12.4 Fault (1): in the reloads the open hand close to the eye is **the firing hand**, not the support hand

Read in 11.1 to 11.3 as the support hand lying on the magazine's face toward the eye. The overlays settle it: in the
game's STRETCH reload at 0.5 s and the RATTLER's at 0.5 and 1.1 s the open, fanned hand in front of the eye lies inside the
offline **firing** hand's outline (yellow), and the support hand's outline (green) is at the bottom left edge
(`hands-offline-validation.jpg`). In the reload pose (`poses.reload` cants the gun up and to the right) the firing hand that
does not reach the grip (12.3: still 8 to 11 cm short) hangs in front of the magazine well, palm toward the eye, its fingers
fanned round nothing. From the side (`hands-offline-chopper.jpg`, `-stretch`, `-rattler`, the reload rows) the support hand
**does** hold the magazine under the well, as the engine's log said (palm 1.9 cm from the magazine's box, 6 of 8 finger joints
within 1.5 cm): the log was right, the picture was the other hand.

From the eye, with the data as it is: | Frame | Magazine in sight (of what the gun leaves) | Firing hand / support hand, share of the picture |
|---|---|---|
| CHOPPER reload 0.5 s, 1.1 s | 11 %, 12 % | 4.4 % / 1.0 % |
| STRETCH reload 0.5 s, 1.1 s | 7 %, 1 % | 4.5 % / 0.6 % |
| RATTLER reload 0.5 s, 1.1 s (seated again by 1.1 s) | 21 %, 2 % | 5.4 % / 0 to 0.8 % |
| NINE reload 0.5 s (the reference) | 26 % | 2.2 % / 0.9 % |
| SHORTY reload 0.5 s, 1.1 s | outside the picture | 0 / 0 |

**The SHORTY**: no hand and no magazine in either reload frame, offline as in the game. Its reload pose (`poses.reload`
[0.12, -0.15, -0.24, 0.12, 0.22, -0.6]: 7 cm further right and 7 cm lower than the CHOPPER's) and its bullpup layout (the
magazine behind the grip, mesh X 17 to 23 cm, the grip's `Palm_R` at 29.5) put the magazine's centre at **1.8 to 2.0 frame
heights from the top** (the bottom edge is 1.0), the support palm at 2.2 to 2.5 and the gun's own pistol grip at 1.28: the whole
lower half of the gun is below the picture. The CHOPPER's magazine sits at 0.90, the STRETCH's at 0.92. Translation alone
would have to lift the gun 22 cm (its receiver across the middle of the view): its reload needs its own pose, turned (muzzle up,
the well rolled toward the eye), which is presentation data for its owner.

### 12.5 Fault (3): the STRETCH's finish between walnut and black mirror: **not the textures, not the material**

- The STRETCH's and SHORTY's own textures wired as the importer wires them (`mi_fp_import._surface`: base colour from `_BC`,
  AO / roughness / metallic from `_ORM` R / G / B, `TC_MASKS`, linear) give walnut and painted steel (STRETCH) and olive paint
  (SHORTY) offline (`hands-offline-finish.jpg`, first column; every per-gun sheet). The ORM's roughness is 0.45 to 0.59 (10.4).
- **Every texture read as 0** (base colour black, roughness 0, metallic 0) gives the game's look: a black mirror with the sky
  and street in it (second column against the game's third). The game's SHORTY aimed frame (white and black with a "wood"
  band on top) is the same mirror: the top face reflects the rusty underside of the El; the STRETCH's walnut drawn on the
  SHORTY (`--tex-set Stretch`) does not give it.
- **It follows single textures, not sessions**: in `h1b` the STRETCH was right and the SHORTY a mirror in the same editor
  session; in `h4` the STRETCH was a mirror; in `s2` right again. The material is one function for every gun.
- **Residency**: the only first-person textures the importer keeps resident are the arms' (`mi_fp_import.ARMS_TEX`:
  `never_stream`, no LOD bias, about 55 MB, CHARACTERS.md: the streamer had kept them at a few hundred pixels). The guns' sets
  stream in `TEXTUREGROUP_CHARACTER` / `_CHARACTER_SPECULAR` / `_CHARACTER_NORMAL_MAP` like any level texture, 4096 squared
  each, and the editor sessions on the integration clone ran right after a fresh import of the guns (11: "the guns imported
  fresh"), with a pool that is over budget in the opening street even in the package (READY.md R4: 717 to 865 MB wanted
  against 600, now 1000 under `[MICloud]` only; the editor's own pool is the engine's). Which value the engine samples for a
  texture that is not (yet) built or resident cannot be told from here; the look says the three samples read as about 0.

What decides it (on the box, when it is free): `ListTextures` and `stat streaming` in the session that shows the mirror, and
whether the guns' textures were still compiling (the editor log) when the frame was taken; and **a frame from the package**
(cooked textures) before any change. If it is streaming, the cheapest fix is to keep the five guns' first-person sets
resident as the arms' are (`never_stream` in `mi_guns_r4.py` / `mi_fp_import._surface`'s texture import): about 416 MB at
4096 (BC1 base colour and ORM 10.7 MB each with mips, BC5 normals 21.3 MB, emissives 10.7, magazines at 2048), or half the
normals' and emissives' size at 2048. `guns-shots.sh` should also wait for compilation and streaming before a picture
(`FlushRenderingCommands` after the textures report built, `r.Streaming.FullyLoadUsedTextures 1` for the shot).

### 12.6 Fault (4): the SHORTY aimed through its irons shows a box: **the eye is behind the bullpup's butt**

The SHORTY's view (`relief` 0.22 m, `sightRear` 12.1 cm behind its gun origin, `meshOffset` putting the butt face 25.5 cm
behind it) puts the rear sight 22 cm ahead of the eye and the butt face **8.6 cm ahead of the eye** (offline: the gun's rearmost
point at camera X +8.6 cm). The eye floats behind a bullpup and looks at its rear face end-on: the dark rubber butt pad framed
by the olive receiver fills the lower half of the picture (`hands-offline-shorty-aim.jpg`; the game's frame in the same sheet).
The other guns put the eye over the stock (STRETCH: relief 0.12, rearmost point 16.3 cm behind the eye, the comb 0.8 cm
under it) or have no stock behind the receiver (CHOPPER, RATTLER: rear 13 and 16 cm ahead, short receivers seen from above).

The SHORTY's art makes the relief alone a half fix: its sight line (`SightRear` and `SightFront` 6.0 cm over the bore) is only
**0.4 to 0.8 cm over the top of its receiver** behind the rear sight (the receiver's top 5.2 cm at the butt, 5.6 cm 4 to 8 cm
ahead of it). With the eye over the receiver (what-if relief 0.12 m: the butt 1.4 cm behind the eye) the box is gone, the rear
aperture is a large ring with the front post in it, and the receiver's top runs across the lower 40 % of the picture at a
grazing angle (the cheek weld's view, as the STRETCH's comb); nearer (0.10 m) the receiver crosses the near plane. A real
carry-handle bullpup has its sight line 5 to 7 cm over the receiver. So: `relief` about 0.12 m (data) now, and the carry
handle's aperture and the front sight raised 4 to 5 cm (art, `weapons_shorty.py`) for a clean sight picture.

### 12.7 For the owners (nothing here was changed)

1. **The firing hand on the rifles (faults 1 and 2), C++ owner of `MIFirstPersonRig` / `MIWeaponComponent::PoseView`.** Anchor
   the firing shoulder, not the midpoint: `GripShoulderTranslation` should put `upperarm_r` (the arm that holds the grip) on
   a camera-space point (the NINE's and the pack STICK's right shoulder sit under the eye), or choose the translation so that
   both palms are within reach of their shoulders. Add the firing arm to the development log (`palm N cm off Palm_R`, the
   gap of 12.3) and to `ReloadHold` / a new test (the right palm within 1 cm of `Palm_R` at the hip, aimed and at 0.5 / 1.1 s).
   As data alone, today: `shoulders` [2, 0, -16] on `chopper_ik`, `stretch_ik`, `rattler_ik` (offline: both hands reach in
   every state; the supportElbowOut tuning of 9.3 must be redone with it, and the reloads looked at for an upper arm in the
   picture, which the offline eye frames do not show). Acceptance: `guns-shots.sh RELOADS="0.5 1.1" HUD=0` frames with the
   firing hand round the pistol grip and the magazine in sight on the CHOPPER and RATTLER.
2. **The STRETCH reload** after 1: the support hand on the magazine's left face still hides most of it from the eye
   (with the what-if anchor 13 % of the magazine in sight at 0.5 s and 5 % at 1.1 s, the support hand over the rest): 11.3 item 1 stands for the STRETCH (lay `reload_grips.py`'s solve from the far face).
3. **The SHORTY reload**: a reload pose of its own (`guns.json shorty.presentation.poses.reload`) that brings the magazine well
   into the picture (its magazine centre now 1.8 to 2.0 frame heights down).
4. **The finish**: decide on the box as 12.5 says, then keep the guns' sets resident or fix the shot script.
5. **The SHORTY aimed**: `relief` about 0.12 (data) and a taller sight line (art).

### 12.8 Limits

The offline frames have no animation layer: no idle breathing, sway, fire layer or the pack idle's finger and wrist twists
(the solved shape sets every finger's direction, the clip only each bone's roll). The clip's shoulders and pole are a fit (12.1),
not the clip; the reach bound of 12.3 does not use them. Fitted parts (foregrips, optics) were not drawn. Renders are Cycles on
the CPU at 640 x 360, a grey sky and a sun (the finish test under a street HDRI), not the engine's lighting: they show where
things are, not how the engine shades them.

## 13. The fixes, proved offline (2026-11-26, this container; the box not used)

Every change below was chosen and checked in the offline reconstruction of 12 (`tools/box/fp/offline`: `tune.py` chose the numbers, `fp_offline.py` rendered them, `fixsheets.py` made the sheets; `run-all.sh` step 5 reruns it). Before = the data of 12 (commit f861e43); after = this tree. Nothing under `src/` and no C++ in `Source/` changed.

**13.1 What changed (data and import scripts only).**

| Fault | Cause (12) | Fix |
|---|---|---|
| (2) firing-hand V, and the open hand in the rifles' reloads | the right shoulder lands 35 cm behind the eye, the 55 cm arm cannot reach the grip | `presentation.json`: `shoulders` [12, 12, -36] on chopper_ik, stretch_ik, rattler_ik (SHORTY [2, 2, -20]) so both arms reach in every state with no upper arm in the picture; `grips.json`: the firing hand's solve regenerated on the same views (`style base`, thumb rise 70 deg, `index_in` 0.6: the index along the trigger side, the thumb wrapped round the grip) |
| (1) magazine hidden in reloads | the open firing hand and a pose that left the magazine behind the grip | the same shoulders; support hand solved from the magazine's far side (`reload_grips.py` solve, palm under and behind the magazine, fingers on its front); `poses.reload` of CHOPPER, STRETCH, RATTLER retuned |
| (1) SHORTY reload shows nothing | its `poses.reload` was 7 cm right and 7 cm low, the magazine behind the grip | new `poses.reload` [0.115, 0.037, -0.3, 0.12, 0.42, -1.15]: the bullpup rolled about 66 degrees, magazine well toward the eye |
| (4) SHORTY aimed box | `relief` 0.22 puts the eye behind the butt | `guns.json` `relief` 0.12 |
| (3) STRETCH / SHORTY black mirror | textures not built or resident when the frame is taken | `mi_fp_import.finish_textures` after the arms' and every gun set's import and before each material; `pie.sh` waits before `HighResShot` (commit 7a79b51). Not provable offline; confirm on the box. |

**13.2 Numbers (firing-hand gap to its place on the grip, cm; share of the magazine in sight from the eye).**

| State | CHOPPER | STRETCH | RATTLER | SHORTY | NINE |
|---|---|---|---|---|---|
| hip | 10.3 / 40 % -> 0.0 / 94 % | 14.2 / 34 % -> 0.0 / 62 % | 16.7 / 34 % -> 0.0 / 49 % | 2.8 -> 0.0 | 0 / unchanged |
| aimed | 0 -> 0 | 0 -> 0 | 4.4 -> 0.0 | 7.8 -> 0.0 | 0 -> 0 |
| reload 0.5 s | 8.3 / 11 % -> 0.0 / 80 % | 8.9 / 7 % -> 0.0 / 34 % | 10.9 / 21 % -> 0.0 / 71 % | none in sight -> 54 % | 26 % -> 44 % |
| reload 1.1 s | 8.3 / 12 % -> 0.0 / 80 % | 8.9 / 1 % -> 0.0 / 22 % | 10.9 / 2 % -> 0.0 / 44 % | none in sight -> 52 % | 0 % -> 84 % |

**13.3 Pictures** (`docs/unreal/shots/`, each under 300 KB): `hands-offline-fix-{chopper,stretch,rattler,shorty,nine}.jpg` (per state: before and after from the eye, before and after from the right, after from above left) and `hands-offline-fix-grip.jpg` (the firing hand from the gun's left, before and after, hip and reload 0.5 s, every gun). In them: on all three rifles the fingers close round the pistol grip with the index forward on the trigger side and the thumb over, where before the thumb and index stood apart in a V; the open hand in front of the magazine in the reloads is gone; the SHORTY reload now shows both hands and its magazine; the SHORTY aimed picture no longer shows the butt's rear face.

**13.4 Still open.**
- Rig patch (C++, not applied, not compiled): `docs/unreal/patches/hands-offline/` (README inside). It anchors the firing shoulder and guards the reach so a different pack idle cannot bring the V back, and logs the firing hand. The data above reaches without it.
- STRETCH reload: the support hand still covers much of the magazine (34 % in sight at 0.5 s, 22 % at 1.1 s); acceptable, not yet like the CHOPPER. A solve from the magazine's far face is the next step.
- SHORTY aimed: with the eye over the receiver the carry handle's housing fills the lower half of the picture (see the shorty sheet): the sight picture needs the aperture and front sight raised 4 to 5 cm (art), not data.
- Limits as in 12.7: no clip layer, Cycles not the engine's shading; none of this has been seen in an engine frame. Acceptance on the box: build, `MurderInc.FirstPerson.ReloadHold` and the suite, then `guns-shots.sh RELOADS="0.5 1.1" HUD=0` and compare with the sheets above.

### 13.6 Independent review of the offline fix (2026-11-26 ~22:15 UTC)

Verdict: Partly accepted, not shippable on this evidence. The offline reconstruction is credible for gun placement. The firing hand now closes on the pistol grip on every rifle, and the magazine now shows in every reload. Three problems remain: the SHORTY aimed picture is still wrong, the STRETCH reload still buries the magazine, and nothing has been seen in an engine frame. The data stopgap also puts the firing arm in an odd pose, the C++ patch is unapplied, and the STRETCH/SHORTY mirror finish is unfixed and unproved. I looked at the fix sheets (chopper, stretch, rattler, shorty, grip) and the validation sheet. I did not open the nine or finish sheets, or the numeric report.

- **must-fix**: SHORTY aimed picture is still wrong: a big green box fills the lower half. docs/unreal/shots/hands-offline-fix-shorty.jpg, row 'SHORTY aimed (irons), AFTER, eye'. The butt face is gone, but the housing now covers the whole lower half and the carry-handle aperture is a small hole at the top, so there is no usable sight picture. HANDS_R4.md 13.4 admits this and defers it to art. The owner's item (4) is therefore not fixed. Relief 0.12 only trades one box for another. Either raise the aperture and front sight 4 to 5 cm, or pick a relief and sight height that give a clean sight picture, before calling it done.
- **must-fix**: No engine frame confirms any fix. Section 13.4 says nothing has been seen in an engine frame. The idle clip is fitted to the dev log, not read from the repository. The reach bound and the offline gap of 0.0 cm are model outputs. The shoulders [12,12,-36] data is a stopgap that depends on that fitted idle. The C++ guard (docs/unreal/patches/hands-offline/) is unapplied, so a different pack idle can bring the V back. Run ReloadHold and guns-shots.sh RELOADS="0.5 1.1" HUD=0 on the box and compare with the fix sheets before release.
- **should-fix**: STRETCH reload: the support hand still hides the magazine. docs/unreal/shots/hands-offline-fix-stretch.jpg, reload 0.5 s and 1.1 s, 'AFTER, eye': only 34% and 22% of the magazine is in sight. The magazine is a small dark block among fingers, against 80% on the CHOPPER. From the above-left view the hand wraps the magazine's face toward the eye. The owner's complaint was a hand covering the magazine, and here it is reduced but not gone. Do the far-face solve from reload_grips.py before shipping.
- **should-fix**: Firing-arm pose in the 'AFTER' side views looks unnatural. hands-offline-fix-chopper.jpg and -rattler.jpg, 'AFTER, right' rows (hip, aimed, reload 0.5 s). The firing forearm rises almost vertically from the bottom-left to the grip. In the aimed rows a large elbow or upper-arm mass sits in the lower-left corner. A real shooter's firing elbow is bent and tucked beside the body. Check that the elbow and upper arm never enter the eye frame in the real idle: the eye views are clean only because the clip is fitted. The shoulders anchor was chosen to make the reach work, not to match a shooter's posture. Review it once the real clip is in.
- **should-fix**: Firing-hand closure on the grip is good but not perfect. docs/unreal/shots/hands-offline-fix-grip.jpg. In the AFTER columns the fingers wrap the grip on CHOPPER, STRETCH, RATTLER and SHORTY, and the V is gone. That fixes owner item (2). However, the index finger lies along or in front of the guard area rather than clearly on the trigger on some guns (CHOPPER, STRETCH hip). The CHOPPER hip AFTER hand is partly hidden behind the receiver and grip, and the thumb is hard to read. The NINE reference shows the index sitting on the trigger more clearly. An instructor would want trigger-finger discipline (index straight and outside the trigger guard when not firing) to be explicit. Check these in-engine at larger size.
- **should-fix**: SHORTY hip and reload framing. hands-offline-fix-shorty.jpg. At the hip, 'AFTER, eye', the gun sits in the lower right and almost off-frame, and only a sliver of the hand shows. In reload the gun is rolled about 66 degrees and the picture is dominated by a foreshortened forearm and the magazine, so it reads as awkward. It does show both hands and the magazine (54% and 52%), so it is better than 'nothing', but it is not a natural bullpup reload.
- **nit**: Validation is good for guns, weaker for hands. docs/unreal/shots/hands-offline-validation.jpg. Red gun outlines and cyan sight and muzzle marks line up with the game's guns in all nine frames, so the gun placement is faithful. Yellow firing-hand outlines match the game's open hand in the reload frames. The validated hands are the before state; no after frame exists in the game to compare. The green support-arm lines sometimes run along the arm edge only loosely.
- **nit**: STRETCH/SHORTY mirror finish is unfixed and unproved. HANDS_R4.md 13.1 row (3): offline renders cannot reproduce the texture-residency fault. The fix (finish_textures, pie.sh wait) is unverified. Item (3) of the owner's report must be confirmed on a box frame.

For the release fixer (mi-v6-fix): every must-fix above is open and must be closed on the box, in engine frames, before the GO.

## 14. Seen in the engine at last: the release fixer's pass (2026-11-26, from 22:20 UTC, box `8496fd8c`, clone `/project/ue/int/repo`)

Every picture is play in editor in `L_Block`, 1920 x 1080, HUD hidden (`guns-shots.sh HUD=0`), the world frozen per picture, the
data of 13 (`shoulders` [12, 12, -36] on the rifles) and the rig patch of `docs/unreal/patches/hands-offline/` (applied in `16f819d`:
`FiringReachShort`, the `firing hand` log line and the `ReloadHold` check of the firing palm). The suite passed on the build: 222 of 222.

**Log.** `First person: firing hand <gun>: palm N cm from its place on the grip`: CHOPPER 0.3 cm (12 lines, hip and reload), SHORTY 0.3,
RATTLER 0.3, STRETCH 0.3 (0.2 to 2.1 cm for a moment right after the draw, 0.2 to 1.1 cm in the reload). `MurderInc.FirstPerson.ReloadHold`
now fails above 1.5 cm at the hip and through the reload and passes.

| Fault (11, 12) | Engine frame | Verdict |
|---|---|---|
| Firing hand makes a V under the receiver | `shots/v6-hands-chopper.jpg`, `-rattler`, `-stretch`: the fingers close round the pistol grip at the hip, in the sun and under the El, and in the reload | **fixed** on CHOPPER, RATTLER, STRETCH, SHORTY |
| Open fanned hand in front of the eye in the reloads, no magazine | the same sheets, reload 0.5 s and 1.1 s: the support hand holds a visible magazine under the well, the firing hand stays on the grip; no cut upper arm | **fixed** on CHOPPER, RATTLER, STRETCH; SHORTY below |
| Torn back of the hand (finger bend 176 degrees) | not in any of the 40 frames of this pass (hip, aimed, both reload times, four guns) | **not seen**; it was a symptom of the open hand's bend, not separately changed |
| SHORTY reload: nothing in the frame / SHORTY firing forearm | `shots/v6-hands-shorty-before.jpg`: with `shoulders` [2, 2, -20] and the offline reload pose the firing forearm filled the screen (a skin-coloured wall); `shots/v6-hands-shorty-after.jpg`: with [12, 12, -36] both hands and the magazine are in the picture, the firing forearm with its bracelet crosses the lower right | **fixed** (presentation.json; the reload pose of 13 stays) |
| Skin-coloured ball against walls and looking down | `shots/v6-hands-wall.jpg`: CHOPPER, SHORTY, STRETCH against the shop fronts, level and looking down at 35 degrees: no ball; the gun is pulled back as designed and the hands stay on it | **not reproduced** with the new shoulders (the review's frames were taken with the old anchor, whose firing arm stretched to its limit) |
| Black / skin dome at the lower left in `death-shots.sh` frames | it appears only when a run starts with `MIStart mission skip`, which uses the template body's arms (the open upper arm of LOADOUT.md 6.6); every run through the front end (Crew RULE) uses `SK_RuleArms` and shows nothing there | **not a play fault**; the death-shots tool should start through the front end |
| Crew screen: skin-coloured stump beside the gun | the stage poses the pack's idle with no solved grip: the support arm ends in a fist round nothing. `mi.FE.CrewArms` (default 0) now shows the turntable gun there until the stage uses the first-person rig | **fixed** by not showing it (picture in section 15 of READY.md's v6 GO readiness) |
| STRETCH / SHORTY finish (grey or white and black mirror) | SHORTY: olive paint, right, in every frame after `tools/box/fp/guns-resident.py` (every first-person gun texture never streamed). STRETCH: **still wrong** in the same frames (`shots/v6-hands-stretch.jpg`: bright steel receiver, white and black marbling on the stock where the art has walnut) | **SHORTY fixed, STRETCH open** (below) |

**The STRETCH's finish is not a residency fault.** After never-stream was saved on every gun texture and the editor was restarted
(and again after a second restart), the STRETCH still draws its stock marbled. Evidence: the box's `SK_Stretch.glb`, `T_Stretch_BC.png` and
`T_Stretch_ORM.png` have the same md5 as `art/out/` in the repo, so the offline render (walnut and painted steel) and the engine read the
same files; the base colour's walnut islands are where the offline stock is, the engine's stock is where its black rectangles are (the
ORM reads metallic there), a mirror in the sun. Likely a UV set or island mismatch in the engine import (the offline lane renders from the
GLB's own UVs). Needs the importer's UV channel checked (`mi_fp_import._import_mesh`: which `TEXCOORD` the material samples) and one
picture of the material's texture coordinate in the editor; not done here for lack of time.

**Not changed:** the STRETCH's reload (the support hand covers part of the magazine, 13.4): in the engine frame the magazine is in the
support hand and in view; the far-face solve stays an improvement for later.

**SHORTY aimed:** the irons now show the carry handle's ribs across the lower middle of the picture and nothing in front of the target
(`v6-hands-wall.jpg` is not it; see the SHORTY aim frame in `v6-hands-shorty-after.jpg`, top right): the butt's rear face is gone, the
target is clear, there is no aperture ring to look through (art: a taller sight line, 12.6).
