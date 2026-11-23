# Run inside the MetaHuman scratch editor (py.sh mh_probe.py): what the MetaHuman Creator Python API offers here.
# Reports the presets' asset-registry tags (high-resolution textures), creates /Game/MH/MH_Probe and lists the
# parametric body constraints, the wardrobe slots and whether the character can be assembled.
import unreal

out = []
ar = unreal.AssetRegistryHelpers.get_asset_registry()
presets = ar.get_assets_by_path("/MetaHumanCharacter/Optional/Presets", recursive=True)
for a in presets:
    hr = a.get_tag_value("bHasHighResolutionTextures")
    out.append("preset %s hires=%s" % (a.asset_name, hr))

sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
path = "/Game/MH/MH_Probe"
ch = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
if ch is None:
    ch = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        asset_name="MH_Probe", package_path="/Game/MH", asset_class=unreal.MetaHumanCharacter,
        factory=unreal.new_object(type=unreal.MetaHumanCharacterFactoryNew))
out.append("created %s" % ch.get_path_name())
ok = sub.try_add_object_to_edit(ch)
out.append("edit %s" % ok)
if ok:
    out.append("can_build %s" % sub.can_build_meta_human(ch, True))
    for c in sub.get_body_constraints(ch):
        out.append("body %s active=%s target=%.1f range=%.1f..%.1f" % (
            c.name, c.is_active, c.target_measurement, c.min_measurement, c.max_measurement))
    coll = ch.internal_collection
    out.append("collection %s" % coll)
    try:
        spec = coll.get_pipeline().get_specification()
        out.append("slots %s" % list(spec.slots.keys()))
    except Exception as e:
        out.append("slots ? %s" % e)
"\n".join(out)
