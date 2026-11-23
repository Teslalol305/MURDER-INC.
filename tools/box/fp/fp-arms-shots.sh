#!/bin/bash
# The arms proof (docs/unreal/shots/fp-arms-*.jpg, hands-and-tattoos pass): play in editor in L_Block through the
# player's eyes, the set-up of fp-shots.sh (CHOPPER, NINE, STICK), then
#   fp-arms-hip-sun    CHOPPER at the hip in the sun        fp-arms-hip-el     at the hip under the El
#   fp-arms-irons      aimed through the irons               fp-arms-nine       the NINE at the hip, the hand on the grip
#   fp-arms-forearm-l  fp-arms-forearm-r   a close look at each forearm's tattoos: the world frozen in the CHOPPER's
#                      idle, the arms drawn for every view (only-owner-see and the first-person pass off for the picture),
#                      the debug camera (ToggleDebugCamera) 36 cm off the thumb side of the forearm, looking at the tattoo
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
for comp in [arms] + list(arms.get_children_components(True)):
    if isinstance(comp, unreal.PrimitiveComponent):
        comp.set_editor_property("only_owner_see", False)
        try:
            comp.set_first_person_primitive_type(unreal.FirstPersonPrimitiveType.NONE)
        except Exception as e:
            unreal.log_warning("MI forearm: %s" % e)
sx = "l" if side == "l" else "r"
e = arms.get_socket_location("lowerarm_" + sx)
wr = arms.get_socket_location("hand_" + sx)
# the back of the forearm: the lowerarm bones' Z axis on the left arm, -Z on the right (the mannequin's mirrored
# right-arm bones), averaged over the forearm and its wrist twist bone; the thumb (radial) side is their Y axis (-Y on
# the right). The tattoos sit about 38 degrees round from the back toward the thumb side (_rule_tex.tattoo_chart)
z = unreal.Vector(0, 0, 0)
y = unreal.Vector(0, 0, 0)
for b in ("lowerarm_", "lowerarm_twist_01_"):
    q = arms.get_socket_transform(b + sx, unreal.RelativeTransformSpace.RTS_WORLD).rotation
    z = z + q.get_axis_z()
    y = y + q.get_axis_y()
sg = 1.0 if sx == "l" else -1.0
z = (z.normal() * 0.79 + y.normal() * 0.62).normal() * sg
L = (e - wr).length()
p = wr + (e - wr) * ((0.18 if sx == "l" else 0.19) * 100.0 / L)     # the tattoo's height above the wrist
cam_at = p + z * 36.0 + (e - wr).normal() * 6.0
rot = unreal.MathLibrary.find_look_at_rotation(cam_at, p)
# the debug camera (ToggleDebugCamera, started by the shell): its spectator pawn moved to the camera point
dcs = [c for c in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.PlayerController) if "DebugCamera" in c.get_class().get_name()]
if not dcs:
    raise RuntimeError("no debug camera controller (ToggleDebugCamera)")
dc = dcs[0]
sp = dc.get_controlled_pawn()
sp.set_actor_location(cam_at, False, True)
dc.set_control_rotation(rot)
"forearm %s: cam %.0f %.0f %.0f looking at %.0f %.0f %.0f" % (sx, cam_at.x, cam_at.y, cam_at.z, p.x, p.y, p.z)
PY
c "EnableCheats"; sleep 1; c "ToggleDebugCamera"; sleep 2; c "fov 50"
for sd in l r; do
  echo "$sd" > "$MI_PROJECT_DIR/Saved/mi_forearm_side.txt"
  if want fp-arms-forearm-$sd; then pie_mcp py "$PIE_PY/_forearm.py" | tail -3; shot fp-arms-forearm-$sd 40; fi
done
c "ToggleDebugCamera"
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
