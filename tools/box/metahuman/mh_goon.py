# Run inside the MetaHuman scratch editor (py.sh mh_goon.py): an enemy Goon from MetaHuman Creator, offline.
# 1. copy a stock preset character (face state, skin, eyes) to /Game/MH/MH_Goon
# 2. parametric body: heavy-set adult male (constraints + fat/muscularity)
# 3. grooms (short hair, stubble, eyebrows, eyelashes) and the engine's only outfit (WI_DefaultGarment, a shirt)
# 4. assemble the preview and report what an offline character can and cannot do
import unreal

PRESET = "/MetaHumanCharacter/Optional/Presets/%s.%s"
G = "/MetaHumanCharacter/Optional/Grooms/Bindings/"
out = []
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
eal = unreal.EditorAssetLibrary
name = globals().get("MH_NAME", "MH_Goon")
preset = globals().get("MH_PRESET", "Bruce")
dst = "/Game/MH/" + name
if not eal.does_asset_exist(dst):
    eal.duplicate_asset(PRESET % (preset, preset), dst)
ch = unreal.load_asset(dst)
out.append("character %s from %s" % (ch.get_path_name(), preset))
if not sub.is_object_added_for_editing(ch):
    out.append("edit %s" % sub.try_add_object_to_edit(ch))

body = {str(c.name): c for c in sub.get_body_constraints(ch)}
want = globals().get("MH_BODY", {"Height": 182.0, "Chest": 124.0, "Waist": 118.0, "Hip": 116.0, "High Hip": 114.0,
                                 "Neck": 45.0, "Neck Base": 49.0, "Bicep": 40.0, "Thigh": 70.0, "Across Shoulder": 44.0,
                                 "Fat": 1.6, "Muscularity": 0.4})
for k, v in want.items():
    c = body[k]
    c.is_active = True
    c.target_measurement = max(c.min_measurement, min(c.max_measurement, v))
sub.set_body_constraints(ch, list(body.values()))
sub.commit_body_state(ch)
got = {str(c.name): round(c.target_measurement, 1) for c in sub.get_body_constraints(ch) if str(c.name) in want}
out.append("body %s" % got)

coll = ch.internal_collection
inst = coll.default_instance
items = globals().get("MH_ITEMS", [("Hair", "Hair/WI_Hair_S_BuzzCut"), ("Beard", "Beards/WI_Beard_S_Stubble"),
                                   ("Eyebrows", "Eyebrows/WI_Eyebrows_M_Thick"), ("Eyelashes", "Eyelashes/WI_Eyelashes_S_Thin"),
                                   ("Outfits", None)])
for slot, rel in items:
    path = "/MetaHumanCharacter/Optional/Clothing/WI_DefaultGarment" if rel is None else G + rel
    wi = unreal.load_asset(path)
    if wi is None:
        out.append("missing %s" % path)
        continue
    key = coll.try_add_item_from_wardrobe_item(slot, wi)
    ok = inst.try_add_slot_selection(unreal.MetaHumanPipelineSlotSelection(slot_name=slot, selected_item=key))
    out.append("slot %s <- %s: %s" % (slot, path.split("/")[-1], ok))

sub.assemble_for_preview(character=ch)
out.append("can_build %s" % sub.can_build_meta_human(ch, True))
eal.save_loaded_asset(ch, False)
"\n".join(out)
