# Run inside the MetaHuman scratch editor (py.sh mh_skel.py): compare the MetaHuman body skeleton
# (metahuman_base_skel, via the exported body mesh) with SK_Mannequin bone for bone: names, parents, extra bones.
import unreal

name = globals().get("MH_NAME", "MH_Goon")
A = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def bones(mesh_path):
    a = A.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, -5000))
    c = a.skeletal_mesh_component
    c.set_skinned_asset_and_update(unreal.load_asset(mesh_path))
    r = {}
    for i in range(c.get_num_bones()):
        n = c.get_bone_name(i)
        r[str(n)] = str(c.get_parent_bone(n))
    A.destroy_actor(a)
    return r


mh = bones("/Game/MH/Export/%s/%s_Body" % (name, name))
mn = bones("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple")
common = [b for b in mn if b in mh]
parent_diff = [b for b in common if mn[b] != mh[b]]
out = ["metahuman body bones %d, mannequin bones %d, common %d" % (len(mh), len(mn), len(common)),
       "mannequin bones missing in metahuman: %s" % [b for b in mn if b not in mh],
       "parent differences: %s" % [(b, mn[b], mh[b]) for b in parent_diff],
       "metahuman extra bones (%d): %s" % (len([b for b in mh if b not in mn]), [b for b in mh if b not in mn][:80])]
"\n".join(out)
