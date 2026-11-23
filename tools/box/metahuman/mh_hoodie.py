# Run inside the MetaHuman scratch editor after mh_stage.py (py.sh mh_hoodie.py): our cloth-simulated Goon hoodie
# (SK_Goon_Hoodie, on SK_Mannequin) worn by the MetaHuman preview actor. The hoodie follows the MetaHuman body by
# leader pose (the mannequin's 80 deforming bones exist in metahuman_base_skel with the same parents), its mask
# section is hidden with a masked opacity-0 material, and the MetaHuman's own outfit slot is emptied.
import unreal

A = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
mel = unreal.MaterialEditingLibrary
out = []
inv_path = "/Game/MH/M_Invisible"
inv = unreal.load_asset(inv_path) if unreal.EditorAssetLibrary.does_asset_exist(inv_path) else None
if inv is None:
    inv = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_Invisible", "/Game/MH", unreal.Material,
                                                                  unreal.MaterialFactoryNew())
    inv.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    k = mel.create_material_expression(inv, unreal.MaterialExpressionConstant, -300, 0)
    k.set_editor_property("r", 0.0)
    mel.connect_material_property(k, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    mel.recompile_material(inv)
    unreal.EditorAssetLibrary.save_loaded_asset(inv, False)

pa = [a for a in A.get_all_level_actors() if a.get_class().get_name().startswith("MetaHumanDefaultEditorPipelineActor")]
body = None
for a in pa:
    for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
        if c.get_name() == "Body":
            body = c
out.append("preview body %s" % body)
for a in pa:
    a.set_actor_rotation(unreal.Rotator(roll=0, pitch=0, yaw=0), False)
for a in A.get_all_level_actors():
    if "MIHoodie" in [str(t) for t in a.tags]:
        A.destroy_actor(a)
h = A.spawn_actor_from_class(unreal.SkeletalMeshActor, body.get_owner().get_actor_location(),
                             body.get_owner().get_actor_rotation())
h.tags = ["MIHoodie"]
hc = h.skeletal_mesh_component
hc.set_skinned_asset_and_update(unreal.load_asset("/Game/Characters/Goons/SK_Goon_Hoodie"))
hc.set_material_by_name("M_GoonHoodie_Head", inv)
h.attach_to_component(body, "", unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
                      unreal.AttachmentRule.SNAP_TO_TARGET, False)
hc.set_leader_pose_component(body, True)
out.append("hoodie follows %s" % hc.get_editor_property("leader_pose_component"))
# hide the MetaHuman outfit (the engine's default garment, a Chaos cloth component) on the preview actor
for a in pa:
    for c in a.get_components_by_class(unreal.ChaosClothComponent):
        c.set_visibility(not globals().get("MH_HIDE_OUTFIT", True), True)
        out.append("outfit %s visible=%s" % (c.get_name(), c.is_visible()))
"\n".join(out)
