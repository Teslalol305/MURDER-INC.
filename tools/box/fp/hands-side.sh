#!/bin/bash
# The first-person hands seen from beside the player (diagnosis of HANDS_R4.md: does each hand hold the gun, does the support
# hand hold the magazine in a reload): play in editor in L_Block, the guns of GUNS carried, and for each gun, the world's time
# frozen, a picture through the player's eye, then from cameras beside the eye (left and right of the gun, looking at it),
# with the arms and gun made visible to a camera that is not the player's (only-owner-see off for those pictures). The
# first-person scale and field of view are the player camera's: from a side camera the arms and gun are drawn where they
# really are in the world.
# Run detached with L_Block open:  setsid nohup bash hands-side.sh [out] > log 2>&1 &
#   GUNS="stretch chopper"   the carried guns (slot order); HUD=0 hides the HUD; RELOADS="0.5 1.1" the reload frames
#   FITS="chopper=underbarrel:foregrip_vertical_wood" as guns-shots.sh
# Pictures: <out>/<gun>-<state>-<eye|left|right>.jpg (default $MI_LOGS/hands-side); ends with HANDS SIDE DONE.
out=${1:-}
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
. ./pie.sh
out=${out:-$MI_LOGS/hands-side}
mkdir -p "$out"
log=$MI_LOGS/editor.log
guns=${GUNS:-"stretch chopper"}
settle() { local i; for i in $(seq 1 "${1:-12}"); do pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done; }
fe() { pie_con "MIMenu fe $*" > /dev/null; }
c() { pie_con "$*" > /dev/null; }
run() { c "MIFreezeAfter $1"; sleep "$(python3 -c "print(max(2.0, $1 * 3.0 + 1.5))")"; }
pick() { local pair; for pair in $2; do [ "${pair%%=*}" = "$1" ] && echo "${pair#*=}"; done; }
# side <off|left|right>: the view from a camera beside the eye (camera space of the player's eye, cm: forward, right, up)
side() {
  local of=40 or=0 ou=-8
  case "$1" in left) or=-75 ;; right) or=75 ;; esac
  cat > "$PIE_PY/_side.py" <<PY
import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(w, 0)
pawn = pc.get_controlled_pawn()
mode = "$1"
if mode == "off":
    pc.set_view_target_with_blend(pawn, 0.0)
    r = "side off"
else:
    for comp in pawn.get_components_by_class(unreal.PrimitiveComponent):
        try:
            comp.set_only_owner_see(False)
        except Exception:
            pass
    cm = pc.player_camera_manager
    eye = cm.get_camera_location()
    rot = cm.get_camera_rotation()
    f = rot.get_forward_vector(); rt = rot.get_right_vector(); up = rot.get_up_vector()
    at = eye + f * $of + rt * $or + up * $ou
    look = eye + f * 42.0 + rt * 12.0 + up * -20.0
    cams = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.CameraActor) if a.get_name().startswith("SideCam")]
    if cams:
        cam = cams[0]
    else:
        cam = w.spawn_actor(unreal.CameraActor, unreal.Vector(0, 0, 0), unreal.Rotator()) if hasattr(w, "spawn_actor") else unreal.GameplayStatics.finish_spawning_actor(unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(w, unreal.CameraActor, unreal.Transform()), unreal.Transform())
        cam.rename("SideCam")
    cam.set_actor_location_and_rotation(at, unreal.MathLibrary.find_look_at_rotation(at, look), False, True)
    cam.camera_component.set_field_of_view(45.0)
    pc.set_view_target_with_blend(cam, 0.0)
    r = "side %s at %s" % (mode, at)
r
PY
  echo "side $1: $(pie_mcp py "$PIE_PY/_side.py" 2>&1 | tr '\n' ' ' | cut -c1-400)"
}
# nogun <1|0>: everything the player carries hidden but the arms (the hands' own shape, nothing in them), and back
nogun() {
  cat > "$PIE_PY/_nogun.py" <<PY
import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pawn = unreal.GameplayStatics.get_player_controller(w, 0).get_controlled_pawn()
n = []
if $1:
    unreal.mi_hidden = []
    for comp in pawn.get_components_by_class(unreal.PrimitiveComponent):
        if comp.get_name() == "FirstPersonArms" or isinstance(comp, unreal.ShapeComponent) or not comp.is_visible():
            continue
        comp.set_visibility(False, False); unreal.mi_hidden.append(comp); n.append(comp.get_name())
else:
    for comp in getattr(unreal, "mi_hidden", []):
        comp.set_visibility(True, False); n.append(comp.get_name())
    unreal.mi_hidden = []
"nogun $1: " + ",".join(n)
PY
  echo "$(pie_mcp py "$PIE_PY/_nogun.py" 2>&1 | tr '\n' ' ' | cut -c1-400)"
}
shots() {  # <gun> <state>: eye, the hands alone from the eye, left, right
  settle 12; pie_shot "$out/$1-$2-eye.jpg"
  nogun 1; settle 8; pie_shot "$out/$1-$2-hands.jpg"; nogun 0
  side left; settle 10; pie_shot "$out/$1-$2-left.jpg"
  side right; settle 10; pie_shot "$out/$1-$2-right.jpg"
  side off; settle 4
}

for k in 1 2 3 4 5; do
  mark=$(wc -l < "$log")
  pie_start > /dev/null
  for i in $(seq 1 30); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
  tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break
  sleep 10
done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "HANDS SIDE FAILED: play in editor did not start"; exit 1; }
sleep 4; settle 10
for i in 1 2 3; do c "MIViewSize 1920 1080"; settle 4; done
fe home; fe gearup; fe next
n=1
for g in $guns; do fe slot $n $g; n=$((n + 1)); done
while [ $n -le 4 ]; do fe empty $n; n=$((n + 1)); done
for g in $guns; do
  fx=$(pick "$g" "${FITS:-}")
  [ -n "$fx" ] || continue
  fe bench "$g"; fe benchslot "${fx%%:*}"; fe fit "${fx#*:}"; fe done
done
fe next; fe time day; fe next; fe mode mission; fe difficulty hustler; fe hit
sleep 10; settle 10
[ "${HUD:-0}" = 0 ] && c "showhud"
slot=1
for g in $guns; do
  c "MIInput weapon$slot 1"; run 1.0; c "MIInput weapon$slot 0"
  c "MIPose -2900 80 0 0 -3"; run 1.2; shots "$g" hip
  for t in ${RELOADS:-0.5 1.1}; do
    c "MIPose -2900 80 0 0 6"; c "MIInput fire 1"; run 0.3; c "MIInput fire 0"; run 0.3
    c "MIFreezeOn reload $t"; c "MIInput reload 1"; sleep 5; c "MIInput reload 0"; shots "$g" "reload-$t"; c "slomo 1"; run 3.0
  done
  slot=$((slot + 1))
done
pie_stop > /dev/null
echo "HANDS SIDE DONE"
