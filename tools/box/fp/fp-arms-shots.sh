#!/bin/bash
# The arms proof (docs/unreal/shots/fp-arms-*.jpg, hands-and-tattoos pass): play in editor in L_Block through the
# player's eyes, the set-up of fp-shots.sh (CHOPPER, NINE, STICK), then
#   fp-arms-hip-sun    CHOPPER at the hip in the sun        fp-arms-hip-el     at the hip under the El
#   fp-arms-irons      aimed through the irons               fp-arms-nine       the NINE at the hip, the hand on the grip
#   fp-arms-forearm-l  fp-arms-forearm-r   a close look at each forearm's tattoos: the world frozen in the CHOPPER's
#                      idle in the sun, the world paused, the arms component turned and moved so that the tattoo faces
#                      the eye 30 cm away (the arms keep their pose, material, lighting and first-person pass)
# and the texture residency of the arms' textures (ListTextures, "MI-ARMS-TEX" lines in the log): the evidence that
# the textures are at full resolution in play.
# Run detached with L_Block open (editor.sh start /Game/Maps/L_Block):  setsid nohup bash fp-arms-shots.sh [out] > log 2>&1 &
# Pictures: <out>/fp-arms-*.jpg (default $MI_LOGS/fp-arms); ends with FP ARMS SHOTS DONE. ONLY="fp-arms-irons ..." limits.
out=${1:-}
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
. ./pie.sh
out=${out:-$MI_LOGS/fp-arms}
mkdir -p "$out"
log=$MI_LOGS/editor.log
mark=$(wc -l < "$log")
settle() { local i; for i in $(seq 1 "${1:-30}"); do pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done; }
fe() { pie_con "MIMenu fe $*" > /dev/null; }
c() { pie_con "$*" > /dev/null; }
run() { c "MIFreezeAfter $1"; sleep "$(python3 -c "print(max(2.0, $1 * 3.0 + 1.5))")"; }
shot() { settle "${2:-30}"; pie_shot "$out/$1.jpg"; }
want() { [ -z "${ONLY:-}" ] || [[ " $ONLY " == *" $1 "* ]]; }
textures() {   # the arms' textures as the renderer holds them (ListTextures: on disk vs in memory)
  local m; m=$(wc -l < "$log"); c "ListTextures"; sleep 3
  tail -n +"$m" "$log" | grep -E "T_RuleArms" | cut -c1-260 | sed "s/^/MI-ARMS-TEX $1: /"
}

pie_start > /dev/null
for i in $(seq 1 40); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "FP ARMS SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4; settle 10
for i in 1 2 3; do c "MIViewSize 1920 1080"; settle 4; done
fe home; fe gearup; fe next
fe slot 1 chopper; fe slot 2 nine; fe slot 3 stick; fe empty 4
fe bench stick; fe benchslot optic; fe fit scope; fe benchslot muzzle; fe fit factory; fe benchslot laser; fe fit factory
fe benchslot underbarrel; fe fit grip_vertical; fe done
fe next; fe time day; fe next; fe mode mission; fe difficulty hustler; fe hit
sleep 10; settle 10
tail -n +"$mark" "$log" | grep -E "Set-up:|First person:" | tail -5 | cut -c1-260
c "MIInput weapon1 1"; run 1.0; c "MIInput weapon1 0"

c "MIPose 170 -380 0 -35 -4"; run 1.2; want fp-arms-hip-sun && shot fp-arms-hip-sun
textures hip-sun
# evidence (not committed: ev-*.jpg): the same frame unlit (the base colour as the arms receive it) and with the
# Subsurface Profile variant of the skin (M_RuleArms_SkinProfile), against the game's Standard Subsurface material
if [ -z "${ONLY:-}" ] || want ev; then
  c "viewmode unlit"; shot ev-unlit 20; c "viewmode lit"
  cat > "$PIE_PY/_skinmat.py" <<'PY'
import unreal
which = open(unreal.Paths.project_saved_dir() + "/mi_skinmat.txt").read().strip()
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
for comp in pawn.get_components_by_class(unreal.SkeletalMeshComponent):
    a = comp.get_skinned_asset()
    if a and a.get_name() == "SK_RuleArms":
        comp.set_material_by_name("M_RuleArms_Skin", unreal.load_asset("/Game/Characters/RuleArms/Materials/" + which))
which
PY
  echo M_RuleArms_SkinProfile > "$MI_PROJECT_DIR/Saved/mi_skinmat.txt"; pie_mcp py "$PIE_PY/_skinmat.py" | tail -1; shot ev-profile 30
  echo M_RuleArms_Skin > "$MI_PROJECT_DIR/Saved/mi_skinmat.txt"; pie_mcp py "$PIE_PY/_skinmat.py" | tail -1
fi
c "MIPose -2900 80 0 0 -3"; run 1.2; want fp-arms-hip-el && shot fp-arms-hip-el
# evidence (not committed): the same frame with the previous pass's skin values (a dynamic instance of the game's
# material: SkinTint 0.92 / 1.0 / 1.12, SubsurfaceTint 0.40 / 0.16 / 0.10, Scatter 0.92), against the current ones
if [ -z "${ONLY:-}" ] || want ev; then
  cat > "$PIE_PY/_skinold.py" <<'PY'
import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
done = []
for comp in pawn.get_components_by_class(unreal.SkeletalMeshComponent):
    a = comp.get_skinned_asset()
    if a and a.get_name() == "SK_RuleArms":
        mid = comp.create_dynamic_material_instance(comp.get_material_index("M_RuleArms_Skin"))
        mid.set_vector_parameter_value("SkinTint", unreal.LinearColor(0.92, 1.0, 1.12, 1))
        mid.set_vector_parameter_value("SubsurfaceTint", unreal.LinearColor(0.40, 0.16, 0.10, 1))
        mid.set_scalar_parameter_value("Scatter", 0.92)
        done.append(comp.get_name())
"old skin values on %s" % done
PY
  pie_mcp py "$PIE_PY/_skinold.py" | tail -1; shot ev-el-oldskin 30
  echo M_RuleArms_Skin > "$MI_PROJECT_DIR/Saved/mi_skinmat.txt"; pie_mcp py "$PIE_PY/_skinmat.py" | tail -1
fi
c "MIInput ads 1"; run 0.8; want fp-arms-irons && shot fp-arms-irons
c "MIInput ads 0"; run 0.6

# a close look at each forearm: the world frozen in the hip idle, a camera off the back of the forearm
cat > "$PIE_PY/_forearm.py" <<'PY'
import unreal
side = open(unreal.Paths.project_saved_dir() + "/mi_forearm_side.txt").read().strip()
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(w, 0)
pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
arms = None
for comp in pawn.get_components_by_class(unreal.SkeletalMeshComponent):
    a = comp.get_skinned_asset()
    if a and a.get_name() == "SK_RuleArms" and comp.is_visible():
        arms = comp
if arms is None:
    raise RuntimeError("no visible SK_RuleArms on the player")
# the world paused (no rig update), the arms component turned and moved so the tattoo faces the eye at 30 cm
unreal.GameplayStatics.set_game_paused(w, True)
sx = "l" if side == "l" else "r"
e = arms.get_socket_location("lowerarm_" + sx)
wr = arms.get_socket_location("hand_" + sx)
# the tattoo's centre, measured on the exported mesh (SK_RuleArms.glb: the vertices inside each tattoo's UV box,
# in the rest pose) and written in the wrist twist bone's frame. Unreal's import of the glTF swaps the bones' local
# Y and Z (thumb_01_l: glTF (1.99, -2.58, -1.36) cm, Unreal (1.99, -1.36, -2.58)), which is why guessing the side
# from the bone axes put the tattoos on the far edge or on the far side. Left: the numerals, 18.3 cm above the wrist;
# right: the word and its script line, 19.4 cm above the wrist; both 4.3-4.4 cm off the forearm's axis.
loc = unreal.Vector(-9.45, 3.50, -1.90) if sx == "l" else unreal.Vector(10.45, -3.41, 1.74)
tw = arms.get_socket_transform("lowerarm_twist_01_" + sx, unreal.RelativeTransformSpace.RTS_WORLD)
M = unreal.MathLibrary
p = M.transform_location(tw, loc)
A = (e - wr).normal()
d = p - wr
n = (d - A * d.dot(A)).normal()            # out of the skin at the tattoo, square to the forearm
cm = pc.player_camera_manager
C = cm.get_camera_location()
cr = cm.get_camera_rotation()
F = cr.get_forward_vector()
# a frame on the tattoo (y the line of sight from the skin to the eye, x along the forearm toward the elbow) mapped onto
# a frame 30 cm in front of the eye (y toward the eye, x up the screen): the lines, which run round the forearm with the
# letters' tops toward the elbow, read upright. The left tattoo is seen square on. The right one faces the inside of the
# bent elbow in the CHOPPER's hold: square on, the right upper arm came straight at the eye and filled the frame (an
# end-on disc with the word at its rim), so it is seen from 35 degrees toward the wrist, past the upper arm
th = 0.0 if sx == "l" else 35.0
v = (n * M.cos(M.degrees_to_radians(th)) - A * M.sin(M.degrees_to_radians(th))).normal()
newp = C + F * 30.0
cur = unreal.Transform(p, M.make_rot_from_yx(v, A), unreal.Vector(1, 1, 1))
tgt = unreal.Transform(newp, M.make_rot_from_yx(F * -1.0, cr.get_up_vector()), unreal.Vector(1, 1, 1))
t = M.compose_transforms(M.compose_transforms(arms.get_world_transform(), M.invert_transform(cur)), tgt)
arms.set_world_transform(t, False, True)
"forearm %s: tattoo point moved to %.0f %.0f %.0f, 30 cm in front of the eye" % (sx, newp.x, newp.y, newp.z)
PY
cat > "$PIE_PY/_unpause.py" <<'PY'
import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
unreal.GameplayStatics.set_game_paused(w, False)
"unpaused"
PY
# in the sun on the north lane, the eye turned so the sun falls on the arms from over the shoulder
# the eye turned four ways (yaw -35, 55, 145, -125: the sun from behind, the side and the front); each forearm is
# shot at each (fp-arms-forearm-<side>-y<yaw>.jpg) and the frame that is sunlit without the player's own shadow is kept
for yw in ${FOREARM_YAWS:--35 55 145 -125}; do
  if want fp-arms-forearm-l || want fp-arms-forearm-r; then c "MIPose 170 -380 0 $yw -4"; run 1.2; fi
  for sd in l r; do
    echo "$sd" > "$MI_PROJECT_DIR/Saved/mi_forearm_side.txt"
    if want fp-arms-forearm-$sd; then pie_mcp py "$PIE_PY/_forearm.py" | tail -3; shot fp-arms-forearm-$sd-y$yw 40; pie_mcp py "$PIE_PY/_unpause.py" > /dev/null; run 0.3; fi
  done
done
textures forearm
# the NINE at the hip: back to the player's own view (a fresh play session resets the flags changed above)
pie_stop > /dev/null; sleep 6
if want fp-arms-nine; then
  mark=$(wc -l < "$log")
  pie_start > /dev/null
  for i in $(seq 1 40); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
  sleep 4; settle 10
  for i in 1 2 3; do c "MIViewSize 1920 1080"; settle 4; done
  fe home; fe gearup; fe next; fe slot 1 chopper; fe slot 2 nine; fe slot 3 stick; fe empty 4; fe done
  fe next; fe time day; fe next; fe mode mission; fe difficulty hustler; fe hit
  sleep 10; settle 10
  c "MIInput weapon2 1"; run 1.0; c "MIInput weapon2 0"; c "MIPose 170 -380 0 -35 -6"; run 1.2; shot fp-arms-nine
fi
pie_stop > /dev/null
echo "FP ARMS SHOTS DONE $out"
