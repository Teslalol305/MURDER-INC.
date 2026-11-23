# Run inside the MetaHuman scratch editor after mh_stage.py (py.sh mh_anim.py): do the mannequin's rifle clips play
# on the exported MetaHuman body? SK_Mannequin is added (in memory, not saved) to metahuman_base_skel's compatible
# skeletons, then the template mannequin and the MetaHuman full body play the same clip at the same time side by side.
# Reports the hand and head positions of both (component space) so the difference is measured, not guessed.
import unreal

name = globals().get("MH_NAME", "MH_Goon")
clips = globals().get("MH_CLIPS", [("/Game/Characters/Mannequins/Anims/Rifle/MM_Rifle_Reload", 1.3),
                                   ("/Game/Characters/Mannequins/Anims/Rifle/MF_Rifle_Idle_ADS", 0.5)])
mesh_kind = globals().get("MH_MESH", "FullBody")
A = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in A.get_all_level_actors():
    if "MIAnim" in [str(t) for t in a.tags]:
        A.destroy_actor(a)
mh_mesh = unreal.load_asset("/Game/MH/Export/%s/%s_%s" % (name, name, mesh_kind))
mann = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SK_Mannequin")
mhs = mh_mesh.skeleton
comp = list(mhs.get_editor_property("compatible_skeletons")) if hasattr(mhs, "get_editor_property") else []
out = []
try:
    if not any(str(s.get_asset_name() if hasattr(s, "get_asset_name") else s).endswith("SK_Mannequin") for s in comp):
        comp.append(mann)
        mhs.set_editor_property("compatible_skeletons", comp)
    out.append("compatible %s" % [str(s) for s in mhs.get_editor_property("compatible_skeletons")])
except Exception as e:
    out.append("compatible_skeletons: %s" % e)
mode = globals().get("MH_RETARGET", None)
if mode is not None:
    out.append("retarget mode request %s" % mode)


def spawn(mesh, anim, t, x, yaw=0.0):
    a = A.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(x, globals().get("MH_Y", 800.0), 0), unreal.Rotator(roll=0, pitch=0, yaw=yaw))
    a.tags = ["MIAnim"]
    c = a.skeletal_mesh_component
    c.set_skinned_asset_and_update(mesh)
    c.set_update_animation_in_editor(True)
    c.override_animation_data(unreal.load_asset(anim), False, False, float(t), 0.0)
    c.tick_animation(0.0, False) if hasattr(c, "tick_animation") else None
    return c


manny = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple")
x = globals().get("MH_X0", -120.0)
for anim, t in clips:
    cm = spawn(manny, anim, t, x)
    cg = spawn(mh_mesh, anim, t, x + 75)
    x += 170
    for b in ("hand_r", "hand_l", "head", "foot_l"):
        pm = cm.get_socket_transform(b, unreal.RelativeTransformSpace.RTS_COMPONENT).translation
        pg = cg.get_socket_transform(b, unreal.RelativeTransformSpace.RTS_COMPONENT).translation
        out.append("%s t=%.2f %s manny (%.1f %.1f %.1f) metahuman (%.1f %.1f %.1f)" % (
            anim.split("/")[-1], t, b, pm.x, pm.y, pm.z, pg.x, pg.y, pg.z))
    out.append("  anim on metahuman: %s" % cg.get_animation_mode())
"\n".join(out)
