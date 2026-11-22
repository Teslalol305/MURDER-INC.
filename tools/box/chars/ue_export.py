"""Export from the character scratch project what Blender needs (docs/unreal/CHARACTERS.md):
the mannequin skeletal mesh with its skeleton, reference animations, the template rifle and pistol.
glTF (the engine's GLTFExporter) and FBX (fallback) side by side into /project/ue/chars/export.
Run: cmdlet.sh /project/ue/chars/scripts/ue_export.py export"""
import os
import unreal

OUT = "/project/ue/chars/export"
M = "/Game/Characters/Mannequins"
MESH = M + "/Meshes/SKM_Manny_Simple"
ANIMS = {
    "rifle_idle_ads": M + "/Anims/Rifle/MF_Rifle_Idle_ADS",
    "pistol_idle_ads": M + "/Anims/Pistol/MF_Pistol_Idle_ADS",
    "rifle_reload": M + "/Anims/Rifle/MM_Rifle_Reload",
    "pistol_reload": M + "/Anims/Pistol/MM_Pistol_Reload",
    "rifle_jog_fwd": None,       # resolved below (first sequence under Rifle/Jog with Fwd in its name)
    "unarmed_attack": None,      # first sequence under Unarmed/Attack
    "death_front": M + "/Anims/Death/MM_Death_Front_01",
}
GUNS = {"rifle": "/Game/Weapons/Rifle/Meshes", "pistol": "/Game/Weapons/Pistol/Meshes"}


def log(*a):
    unreal.log_warning("MI: " + " ".join(str(x) for x in a))


def assets_under(path, cls=None):
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    out = []
    for a in reg.get_assets_by_path(path, recursive=True):
        if cls is None or str(a.asset_class_path.asset_name) == cls:
            out.append(str(a.package_name))
    return sorted(out)


def gltf_options():
    o = unreal.GLTFExportOptions()
    for k, v in (("export_uniform_scale", 0.01), ("export_vertex_skin_weights", True),
                 ("export_animation_sequences", True), ("export_vertex_colors", False),
                 ("bake_material_inputs", unreal.GLTFMaterialBakeMode.DISABLED),
                 ("export_proxy_materials", False), ("export_unlit_materials", False),
                 ("export_clear_coat_materials", False), ("export_level_sequences", False),
                 ("export_morph_targets", True), ("texture_image_format", unreal.GLTFTextureImageFormat.NONE)):
        try:
            o.set_editor_property(k, v)
        except Exception as e:  # noqa: BLE001 - property names move between versions
            log("gltf option", k, "not set:", e)
    return o


def export_gltf(asset_path, fname):
    obj = unreal.load_asset(asset_path)
    if obj is None:
        log("MISSING", asset_path)
        return False
    path = os.path.join(OUT, fname)
    ok = unreal.GLTFExporter.export_to_gltf(obj, path, gltf_options(), set())
    log("gltf", asset_path, "->", path, ok, os.path.getsize(path) if os.path.exists(path) else -1)
    return ok


def export_fbx(asset_path, fname, anim=False):
    obj = unreal.load_asset(asset_path)
    if obj is None:
        log("MISSING", asset_path)
        return False
    t = unreal.AssetExportTask()
    t.object = obj
    t.filename = os.path.join(OUT, fname)
    t.automated = True
    t.prompt = False
    t.replace_identical = True
    t.exporter = unreal.AnimSequenceExporterFBX() if anim else (
        unreal.SkeletalMeshExporterFBX() if isinstance(obj, unreal.SkeletalMesh) else unreal.StaticMeshExporterFBX())
    o = unreal.FbxExportOption()
    for k, v in (("ascii", False), ("collision", False), ("level_of_detail", False), ("vertex_color", False),
                 ("export_morph_targets", True), ("export_preview_mesh", True), ("force_front_x_axis", False),
                 ("map_skeletal_motion_to_root", False), ("export_local_time", True)):
        try:
            o.set_editor_property(k, v)
        except Exception as e:  # noqa: BLE001
            log("fbx option", k, "not set:", e)
    t.options = o
    ok = unreal.Exporter.run_asset_export_task(t)
    log("fbx", asset_path, "->", t.filename, ok, os.path.getsize(t.filename) if os.path.exists(t.filename) else -1)
    return ok


def main():
    os.makedirs(OUT, exist_ok=True)
    jog = [p for p in assets_under(M + "/Anims/Rifle/Jog", "AnimSequence") if "Fwd" in p or "F" == p[-1]]
    att = assets_under(M + "/Anims/Unarmed/Attack", "AnimSequence")
    log("jog candidates", jog, "attack candidates", att)
    ANIMS["rifle_jog_fwd"] = jog[0] if jog else None
    ANIMS["unarmed_attack"] = att[0] if att else None
    export_gltf(MESH, "SKM_Manny_Simple.glb")
    export_fbx(MESH, "SKM_Manny_Simple.fbx")
    for key, p in ANIMS.items():
        if not p:
            log("no asset for", key)
            continue
        export_gltf(p, "A_%s.glb" % key)
        export_fbx(p, "A_%s.fbx" % key, anim=True)
    for key, path in GUNS.items():
        for p in assets_under(path, "StaticMesh"):
            n = p.rsplit("/", 1)[1]
            export_gltf(p, "%s.glb" % n)
            export_fbx(p, "%s.fbx" % n)
    log("files", sorted(os.listdir(OUT)))
    log("MI-DONE")


main()
