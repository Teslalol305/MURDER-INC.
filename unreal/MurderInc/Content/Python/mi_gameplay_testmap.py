"""Builds /Game/Maps/L_GameplayTest: a floor, a wall 15 m east, daylight, two target dummies, a propane tank and a
player start at the origin looking east. For the gameplay slice's play-in-editor checks (tools/box/pie.sh).
Run in the editor: python3 tools/box/mi_mcp.py py unreal/MurderInc/Content/Python/mi_gameplay_testmap.py"""
import unreal

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
path = '/Game/Maps/L_GameplayTest'
if unreal.EditorAssetLibrary.does_asset_exist(path):
    les.load_level(path)
else:
    les.new_level(path)
for a in eas.get_all_level_actors():
    eas.destroy_actor(a)


def spawn(cls, loc, yaw=0.0, pitch=0.0):
    # unreal.Rotator's positional order is (roll, pitch, yaw): always name the fields.
    return eas.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw))


cube = unreal.load_asset('/Engine/BasicShapes/Cube')
for loc, scale in (((0, 0, -50), (80, 80, 1)), ((1500, 0, 150), (1, 20, 3))):
    block = spawn(unreal.StaticMeshActor, loc)
    block.static_mesh_component.set_static_mesh(cube)
    block.set_actor_scale3d(unreal.Vector(*scale))
sun = spawn(unreal.DirectionalLight, (0, 0, 500), yaw=-30.0, pitch=-45.0)
sun.light_component.set_intensity(10.0)
sun.light_component.set_editor_property('atmosphere_sun_light', True)
spawn(unreal.SkyAtmosphere, (0, 0, 0))
sky = spawn(unreal.SkyLight, (0, 0, 200))
sky.light_component.set_editor_property('real_time_capture', True)
spawn(unreal.ExponentialHeightFog, (0, 0, 0))
spawn(unreal.PostProcessVolume, (0, 0, 0)).set_editor_property('unbound', True)
spawn(unreal.PlayerStart, (0, 0, 100))
dummy = unreal.load_class(None, '/Script/MurderInc.MITargetDummy')
spawn(dummy, (700, 0, 0), yaw=180.0)
spawn(dummy, (900, 150, 0), yaw=180.0)
spawn(unreal.load_class(None, '/Script/MurderInc.MIExplosive'), (800, 400, 0))
unreal.EditorLoadingAndSavingUtils.save_current_level()
'saved ' + path
