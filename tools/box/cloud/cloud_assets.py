"""The cloud package's asset step (tools/box/cloud/package-cloud.sh usage), run in the release copy only:
UnrealEditor-Cmd <release copy>/MurderInc.uproject -run=pythonscript -script=<this file>.

1. The material usage flags the cooked game needs (tools/box/demo/fix_usage.py, run first, unchanged).
2. Graphics memory for the stream (E3DS crash fix, 2026-11-24): the six baked interior cube maps
   (/Game/Art/Interiors/TC_*, the rooms behind the shop and home windows) are stored as uncompressed 16-bit float,
   64 MB each and always resident (rhi.DumpResourceMemory: 384 MB of "Texture Cube Memory"). BC6H (TC_HDR_COMPRESSED)
   keeps their size and HDR range at an eighth of the memory. Generated content on the box, never committed.
"""
import os
import runpy

import unreal

# package-cloud.sh passes the path (the editor's Python may run this file without __file__).
fix_usage = os.environ.get('MI_FIX_USAGE') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'demo', 'fix_usage.py')
runpy.run_path(fix_usage, run_name='__main__')

changed = 0
for path in unreal.EditorAssetLibrary.list_assets('/Game/Art/Interiors', recursive=True, include_folder=False):
    a = unreal.load_asset(path)
    if not isinstance(a, unreal.TextureCube):
        continue
    old = a.get_editor_property('compression_settings')
    if old == unreal.TextureCompressionSettings.TC_HDR_COMPRESSED:
        unreal.log('cloud_assets: %s already BC6H' % a.get_path_name())
        continue
    a.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_HDR_COMPRESSED)
    ok = unreal.EditorAssetLibrary.save_loaded_asset(a, False)
    unreal.log('cloud_assets: cube %s %s -> TC_HDR_COMPRESSED saved %s' % (a.get_path_name(), old, ok))
    changed += 1
unreal.log('cloud_assets: %d interior cube map(s) changed' % changed)
