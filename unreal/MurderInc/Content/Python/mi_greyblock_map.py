"""Builds /Game/Maps/L_GreyBlock: an empty map with daylight and a player start. The game (AMIGameMode, BlockMaps in
Config/DefaultGame.ini) builds the block from level.json at run time and draws it as grey boxes, because the map
holds no art. Spawn points, objectives, collision and the enemies' navigation all come from data.
Run in the editor: python3 tools/box/mi_mcp.py py unreal/MurderInc/Content/Python/mi_greyblock_map.py"""
import json
import os
import unreal

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
path = '/Game/Maps/L_GreyBlock'
if unreal.EditorAssetLibrary.does_asset_exist(path):
    les.load_level(path)
else:
    les.new_level(path)
for a in eas.get_all_level_actors():
    eas.destroy_actor(a)


def spawn(cls, loc, yaw=0.0, pitch=0.0):
    # unreal.Rotator's positional order is (roll, pitch, yaw): always name the fields.
    return eas.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw))


level = json.load(open(os.path.join(unreal.Paths.project_content_dir(), 'Data', 'level.json')))
start = level['playerStart']['ue']
sun = spawn(unreal.DirectionalLight, (0, 0, 2000), yaw=-35.0, pitch=-40.0)
sun.light_component.set_intensity(10.0)
sun.light_component.set_editor_property('atmosphere_sun_light', True)
spawn(unreal.SkyAtmosphere, (0, 0, 0))
sky = spawn(unreal.SkyLight, (0, 0, 500))
sky.light_component.set_editor_property('real_time_capture', True)
spawn(unreal.ExponentialHeightFog, (0, 0, 0))
spawn(unreal.PostProcessVolume, (0, 0, 0)).set_editor_property('unbound', True)
# The capsule centre stands 92 cm over the feet (the default capsule half height).
spawn(unreal.PlayerStart, (start['pos']['X'], start['pos']['Y'], start['pos']['Z'] + 92.0), yaw=start['yaw'])
unreal.EditorLoadingAndSavingUtils.save_current_level()
'saved ' + path
