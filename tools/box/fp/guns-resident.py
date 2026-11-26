# Run in the editor (mi_mcp.py py guns-resident.py): the first-person guns' textures never streamed, full size.
# The same as mi_guns_r4.keep_resident, for a clone whose guns are already imported (a fresh import does it itself).
import unreal

A = unreal.EditorAssetLibrary
done = []
for a in A.list_assets("/Game/Weapons", recursive=True, include_folder=False):
    if "/Textures/" not in str(a):
        continue
    t = unreal.load_asset(str(a))
    if isinstance(t, unreal.Texture2D) and not t.get_editor_property("never_stream"):
        t.set_editor_property("never_stream", True)
        t.set_editor_property("lod_bias", 0)
        A.save_loaded_asset(t)
        done.append(t.get_name())
"never_stream set on %d textures" % len(done)
