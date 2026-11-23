# Run inside the MetaHuman scratch editor (py.sh mh_stage.py): a daylight stage (/Game/MH/L_MH: floor, sun, sky,
# sky light with a ground-coloured lower hemisphere, manual exposure as in tools/box/chars/mi_chars.py) and the
# MetaHuman preview actor of /Game/MH/<MH_NAME> at the origin facing +Y (towards the cameras of mh-shots.sh).
import unreal

A = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LE = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
name = globals().get("MH_NAME", "MH_Goon")
out = []
world = unreal.EditorLevelLibrary.get_editor_world()
if not world.get_path_name().startswith("/Game/MH/L_MH"):
    if unreal.EditorAssetLibrary.does_asset_exist("/Game/MH/L_MH"):
        LE.load_level("/Game/MH/L_MH")
    else:
        LE.new_level("/Game/MH/L_MH")
for a in A.get_all_level_actors():
    if "MIStage" in [str(t) for t in a.tags] or a.get_class().get_name().startswith("MetaHuman"):
        A.destroy_actor(a)


def tag(a):
    a.tags = ["MIStage"]
    return a


floor = tag(A.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -1)))
floor.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Plane"))
floor.set_actor_scale3d(unreal.Vector(40, 40, 1))
mat = unreal.load_asset("/Engine/EngineMaterials/DefaultMaterial")
sun = tag(A.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 500),
                                   unreal.Rotator(roll=0, pitch=-40, yaw=210)))
sun.light_component.set_editor_property("intensity", 6.0)
tag(A.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0)))
sky = tag(A.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 300)))
sky.light_component.set_editor_property("real_time_capture", True)
sky.light_component.set_editor_property("lower_hemisphere_is_black", False)
sky.light_component.set_editor_property("lower_hemisphere_color", unreal.LinearColor(0.28, 0.26, 0.23, 1.0))
pp = tag(A.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0)))
pp.set_editor_property("unbound", True)
s = pp.get_editor_property("settings")
for k, v in dict(override_auto_exposure_method=True, auto_exposure_method=unreal.AutoExposureMethod.AEM_MANUAL,
                 override_auto_exposure_bias=True, auto_exposure_bias=9.0).items():
    s.set_editor_property(k, v)
pp.set_editor_property("settings", s)

ch = unreal.load_asset("/Game/MH/" + name)
if not sub.is_object_added_for_editing(ch):
    out.append("edit %s" % sub.try_add_object_to_edit(ch))
actor = sub.spawn_meta_human_actor(ch, False)
sub.assemble_for_preview(character=ch)  # without it a re-spawned preview has no grooms and no outfit
out.append("actor %s %s" % (actor.get_name() if actor else None, actor.get_class().get_name() if actor else ""))
if actor:
    actor.set_actor_location_and_rotation(unreal.Vector(0, 0, 0), unreal.Rotator(roll=0, pitch=0, yaw=0), False, False)
    comps = actor.get_components_by_class(unreal.SkeletalMeshComponent)
    for c in comps:
        m = c.get_skeletal_mesh_asset()
        out.append("comp %s mesh %s" % (c.get_name(), m.get_path_name() if m else None))
"\n".join(out)
