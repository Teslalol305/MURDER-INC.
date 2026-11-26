# hands-offline: the firing shoulder and the firing hand's reach (C++, for the owner of `MIFirstPersonRig`)

HANDS_R4.md 12.3 found that the rifles' firing hand never reached its pistol grip: `GripShoulderTranslation` puts the
**midpoint** of `upperarm_l` / `upperarm_r` on the anim set's `shoulders`, the pack idle protracts the left shoulder far
forward, so the right one ends up 35 cm behind the eye, 62 to 68 cm from the wrist the solved grip asks for, with an arm
of 55 cm that never stretches. The hand kept its solved shape round nothing: the open V under the receiver (11.1), and in
the reloads the open hand in front of the magazine (12.4). HANDS_R4.md 13 fixes it **in data** (a new `shoulders` anchor
on `chopper_ik`, `stretch_ik`, `rattler_ik`, chosen offline so both arms reach in every state with no upper arm in the
picture). This patch makes the rig itself safe, whatever the data and the clip do. It was written against the tree of
commit `f861e43` and has **not been compiled or run here** (no engine in this container; the box was busy).

    git apply --check docs/unreal/patches/hands-offline/0001-firing-shoulder-and-reach.patch
    git apply docs/unreal/patches/hands-offline/0001-firing-shoulder-and-reach.patch

## What it changes

| File | Change |
|---|---|
| `Weapons/MIFirstPersonRig.h/.cpp` | `GripShoulderTranslation(GunRel, ArmsRel, Out)` (the gun's camera-space transform is passed in). New optional anim-set key `firingShoulder` [x, y, z] (camera cm): when present the arms are carried so that `upperarm_r` sits there instead of the midpoint on `shoulders` (`mi.FP.Shoulders` still overrides with the midpoint). Then, whatever the anchor, the **reach guard**: `FiringReachShort` measures how far the solved grip's firing wrist (`grips.json` `hand_r`, hip and aimed blended by the aim) lies beyond 97 % of the firing arm (upper arm + forearm, from the posed bones), and the arms move toward it by that much (the support arm can stretch to `armStretch`). Console `mi.FP.FiringReach 0` turns the guard off for comparison pictures. |
| `Weapons/MIFirstPersonRig.cpp` `UpdateHands` | A development-log line every 2 s: `First person: firing hand <gun>: palm N cm from its place on the grip (aim A, reload R)`. The support-arm lines never measured the firing hand, which is how the open hand went unseen until the HUD was hidden. |
| `Weapons/MIFirstPersonRig.h/.cpp` | `FiringPalmGap(double&)`: the firing palm bone, as drawn, from where the solved grip puts it. |
| `Weapons/MIWeaponComponent.cpp` `PoseView` | passes `Gun` to `GripShoulderTranslation`. |
| `Tests/MIReloadHoldTests.cpp` | `MurderInc.FirstPerson.ReloadHold` also checks, for every hand-IK rifle, that the firing palm is within 1.5 cm of its place on the pistol grip at the hip and through the whole reload. |

## What the offline reconstruction says it does (`tools/box/fp/offline`, `--patch-reach` / `tune.py --patch-reach`)

- With the **old** anchor [-10, -14, -7] and the guard: both hands reach in every state (firing elbow bent 28 degrees), but
  in the new reload poses a cut upper arm comes 0.33 to 0.40 of a frame into the picture: the guard alone is not enough,
  the anchor of HANDS_R4.md 13 is needed as well.
- With the **new** anchor (the data of 13) the guard does nothing (the firing arm reaches with its elbow bent 34 degrees
  or more); it only steps in if the pack idle differs from the fitted one (13.4: the fitted left shoulder moved 5 cm
  forward leaves the firing hand 0.9 cm short without it).

## Acceptance (on the box)

1. Build, then `MurderInc.FirstPerson.ReloadHold` and the suite.
2. `guns-shots.sh RELOADS="0.5 1.1" HUD=0` with the data of HANDS_R4.md 13: the firing hand closed round the pistol grip
   (index on the trigger) at the hip, aimed and in both reload frames on the CHOPPER, STRETCH and RATTLER; the support
   hand under the magazine with the magazine's rear and left faces in sight; no cut upper arm in any frame.
3. The development log's `firing hand` lines: under 1 cm at the hip and in the reloads.
