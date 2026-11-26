# Unbuilt review fixes (deaths, story guidance, blood, demo director)

Written by the end-to-end play fixer on 2026-11-26 after the GPU box ran out of credits (03:33 UTC). They were never compiled or
tested, so they are kept here as patches, not merged into the branch: the suite must pass on everything the branch carries.
Base: 293fd82. They apply cleanly onto the branch head of that time.

To land them once a box is up: in a clone on the box,
`git am docs/unreal/patches/unbuilt-review-fixes/000*.patch`, build, run `tools/box/test.sh MurderInc` (new tests
MurderInc.Guide.Combat and MurderInc.Death.Retired), take the death and guidance pictures (tools/box/fp/death-shots.sh, the guide
verb), then push. First-build risks and what each patch fixes: docs/unreal/PLAY.md, fixer lane section.
