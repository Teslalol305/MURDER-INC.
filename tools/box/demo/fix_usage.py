"""Standalone game (-game, and any cooked build) cannot add a material usage at run time: a material without the
usage flag of the mesh it is drawn on renders with the engine's default material there ("missing usage flag Nanite!
Default Material will be used in game"). The editor adds the flags on the fly, so PIE never showed it. This sets the
flags the demo capture logged and saves the materials (the game compiles the new permutations when it loads them) (generated content on the box, never committed).
Run: UnrealEditor-Cmd <project> -run=pythonscript -script=<this file> (tools/box/demo/fix-usage.sh)."""
import unreal

NEEDS = {
    '/Game/Characters/RuleArms/Materials/M_RuleSilver': ['used_with_nanite'],
    '/Game/Characters/RuleArms/Materials/M_RuleSilverWorn': ['used_with_nanite'],
    '/Game/FX/M_FX_Tracer': ['used_with_skeletal_mesh'],
    '/Game/ThirdParty/InfimaTFA/Weapon/Materials/MI_TFA_AR_02': ['used_with_nanite'],
    '/Game/ThirdParty/InfimaTFA/Weapon/Materials/MI_TFA_AR_04': ['used_with_nanite'],
    '/Game/ThirdParty/InfimaTFA/Weapon/Materials/MI_TFA_AR_ATT_01': ['used_with_nanite'],
    '/Game/Weapons/GoonSMG/M_Weapon_GoonSMG': ['used_with_nanite'],
    '/Game/Weapons/GoonSMG/M_Weapon_GoonSMG_Lens': ['used_with_nanite'],
    '/Game/Weapons/Nine/M_Weapon_NineMagazine': ['used_with_nanite'],
}
done = set()
# The block-v2 map draws the art's masters on instanced and Nanite meshes (logged by the take with that map: the El
# steel, concrete, plates): every master under /Game/Art/Materials gets both flags.
for path in unreal.EditorAssetLibrary.list_assets('/Game/Art/Materials', recursive=True, include_folder=False):
    a = unreal.load_asset(path)
    if isinstance(a, unreal.Material):
        NEEDS[a.get_path_name().split('.')[0]] = ['used_with_instanced_static_meshes', 'used_with_nanite']
for path, flags in NEEDS.items():
    a = unreal.load_asset(path)
    if a is None:
        unreal.log_warning('fix_usage: missing %s' % path)
        continue
    base = a if isinstance(a, unreal.Material) else a.get_base_material()
    for f in flags:
        base.set_editor_property(f, True)
    key = base.get_path_name()
    if key not in done or flags:
        done.add(key)
        ok = unreal.EditorAssetLibrary.save_loaded_asset(base, False)
        unreal.log('fix_usage: %s %s saved %s' % (key, flags, ok))
