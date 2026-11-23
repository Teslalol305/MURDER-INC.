# Run inside the MetaHuman scratch editor (py.sh mh_export.py): turn the offline character /Game/MH/<MH_NAME> into
# project assets without the cloud: MetaHumanCharacterExportBlueprintLibrary.export_geometry (head, body and full
# body skeletal meshes) needs only the character open for editing (no rig, no downloaded textures), then reports
# skeleton, bones, LODs, triangles and materials of what it wrote.
import unreal

name = globals().get("MH_NAME", "MH_Goon")
dst = "/Game/MH/Export/" + name
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.load_asset("/Game/MH/" + name)
out = []
if not sub.is_object_added_for_editing(ch):
    out.append("edit %s" % sub.try_add_object_to_edit(ch))
p = unreal.MetaHumanGeometryExportParams()
p.project_path = dst
p.head_skeletal_mesh = True
p.body_skeletal_mesh = True
p.full_body_skeletal_mesh = True
p.overwrite_existing_assets = True
unreal.MetaHumanCharacterExportBlueprintLibrary.export_geometry(ch, p)
ar = unreal.AssetRegistryHelpers.get_asset_registry()
ar.scan_paths_synchronous([dst], True)
for a in ar.get_assets_by_path(dst, recursive=True):
    out.append("asset %s %s" % (a.package_name, a.asset_class_path.asset_name))
    if str(a.asset_class_path.asset_name) == "SkeletalMesh":
        m = unreal.load_asset(str(a.package_name))
        sk = m.skeleton
        sms = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
        n = sms.get_lod_count(m)
        out.append("  skeleton %s lods %d verts %s" % (sk.get_path_name() if sk else None, n,
                                                      [sms.get_num_verts(m, i) for i in range(n)]))
        out.append("  materials %s" % [str(x.material_slot_name) for x in m.materials])
"\n".join(out)
