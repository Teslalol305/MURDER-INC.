# Run inside the MetaHuman scratch editor after mh_stage.py and mh_anim.py (py.sh mh_pose.py): colour the MetaHuman
# outfit (instance parameters of the preview collection), show or hide our Goon hoodie, and drive the preview actor's
# body with a mannequin clip (SK_Mannequin is a compatible skeleton in memory, mh_anim.py) so face, grooms and cloth
# follow a game pose.
import unreal

A = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
name = globals().get("MH_NAME", "MH_Goon")
clip = globals().get("MH_CLIP", ("/Game/Characters/Mannequins/Anims/Rifle/MF_Rifle_Idle_ADS", 0.5))
colours = globals().get("MH_COLOURS", {"PrimaryColorShirt": (0.035, 0.036, 0.04), "SecondaryColorShirt": (0.02, 0.02, 0.022),
                                        "PrimaryColorShort": (0.03, 0.04, 0.07), "SecondaryColorShort": (0.02, 0.025, 0.04)})
show_hoodie = globals().get("MH_HOODIE", False)
out = []
ch = unreal.load_asset("/Game/MH/" + name)
inst = sub.get_preview_collection(ch).default_instance
for p in inst.get_instance_parameter_item_paths():
    for prm in inst.get_instance_parameters(item_path=p):
        if str(prm.name) in colours:
            prm.set_color(value=unreal.LinearColor(*colours[str(prm.name)], 1.0))
            out.append("colour %s" % prm.name)
for a in A.get_all_level_actors():
    tags = [str(t) for t in a.tags]
    if "MIHoodie" in tags:
        a.set_actor_hidden_in_game(not show_hoodie)
        a.skeletal_mesh_component.set_visibility(show_hoodie, True)
    if a.get_class().get_name().startswith("MetaHumanDefaultEditorPipelineActor"):
        for c in a.get_components_by_class(unreal.ChaosClothComponent):
            c.set_visibility(not show_hoodie, True)
        for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
            if c.get_name() == "Body" and clip:
                c.set_update_animation_in_editor(True)
                c.override_animation_data(unreal.load_asset(clip[0]), False, False, float(clip[1]), 0.0)
                out.append("body plays %s at %.2f: mode %s" % (clip[0].split("/")[-1], clip[1], c.get_animation_mode()))
"\n".join(out)
