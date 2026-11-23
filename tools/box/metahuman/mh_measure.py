# Run inside the MetaHuman scratch editor (py.sh mh_measure.py): triangles per LOD of the exported MetaHuman meshes
# (Geometry Script copy of each LOD), the character's texture sizes (synthesized face maps, body maps) and the
# memory of every MetaHuman asset class from "obj list" (written to the editor log; parsed by mh-measure.sh).
import unreal

name = globals().get("MH_NAME", "MH_Goon")
out = []
au = unreal.GeometryScript_AssetUtils
sms = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
for kind in ("FullBody", "Body", "Head"):
    m = unreal.load_asset("/Game/MH/Export/%s/%s_%s" % (name, name, kind))
    tris = []
    for lod in range(sms.get_lod_count(m)):
        dm = unreal.DynamicMesh()
        opts = unreal.GeometryScriptCopyMeshFromAssetOptions()
        req = unreal.GeometryScriptMeshReadLOD()
        req.lod_index = lod
        try:
            r = au.copy_mesh_from_skeletal_mesh(m, dm, opts, req)
            tris.append(dm.get_triangle_count())
        except Exception as e:
            tris.append("? %s" % str(e)[:60])
    out.append("%s triangles per LOD %s" % (kind, tris))
ch = unreal.load_asset("/Game/MH/" + name)
for label, texmap in (("face", ch.get_editor_property("synthesized_face_textures")),
                      ("body", ch.get_editor_property("body_textures"))):
    for k, t in texmap.items():
        if t:
            out.append("%s texture %s %dx%d %s" % (label, k, t.blueprint_get_size_x(), t.blueprint_get_size_y(),
                                                     t.get_editor_property("compression_settings")))
"\n".join(out)
