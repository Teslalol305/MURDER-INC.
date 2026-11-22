import unreal
def log(*a): unreal.log_warning("MI: " + " ".join(str(x) for x in a))
log("opts", [p for p in dir(unreal.GLTFExportOptions) if not p.startswith("_")])
log("exporter", [p for p in dir(unreal.GLTFExporter) if not p.startswith("_")])
reg = unreal.AssetRegistryHelpers.get_asset_registry()
for path in ("/Game/Characters/Mannequins/Meshes", "/Game/Weapons/Rifle/Meshes", "/Game/Weapons/Pistol/Meshes",
             "/Game/Characters/Mannequins/Anims/Rifle", "/Game/Characters/Mannequins/Anims/Pistol",
             "/Game/Characters/Mannequins/Anims/Unarmed", "/Game/Characters/Mannequins/Anims/Death"):
    for a in reg.get_assets_by_path(path, recursive=True):
        log("asset", a.package_name, a.asset_class_path.asset_name)
log("MI-DONE")
