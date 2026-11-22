"""Build (or rebuild) the bootstrap test map /Game/Maps/L_Bootstrap inside the Unreal Editor.

The map is generated content: it is not committed, this script regenerates it.
Run it in the running headless editor from the box:

    tools/box/mi_mcp.py py unreal/MurderInc/Content/Python/mi_bootstrap_map.py

What it makes: a floor, a few boxes with a sphere and a cylinder, a player start, a directional sun with a sky
atmosphere, a sky light, exponential height fog and an unbound post-process volume with Lumen and a fixed exposure.
Everything it spawns carries the actor tag MIBootstrap, so a rerun replaces its own actors and nothing else.
Units are Unreal's: centimetres, Z up, X east, Y south.
"""
import unreal

MAP_PATH = "/Game/Maps/L_Bootstrap"
ASSET_DIR = "/Game/Maps/Bootstrap"
TAG = "MIBootstrap"
# Fixed exposure (EV100) for the 10 lux sun below: captures must not depend on eye-adaptation history.
EXPOSURE_EV100 = 1.0

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def make_material(name, colour, roughness):
    """A plain opaque material with one colour; made once, reused afterwards."""
    path = "%s/%s" % (ASSET_DIR, name)
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.EditorAssetLibrary.load_asset(path)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    material = tools.create_asset(name, ASSET_DIR, unreal.Material, unreal.MaterialFactoryNew())
    library = unreal.MaterialEditingLibrary
    base = library.create_material_expression(material, unreal.MaterialExpressionConstant3Vector, -350, 0)
    base.set_editor_property("constant", unreal.LinearColor(colour[0], colour[1], colour[2], 1.0))
    library.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = library.create_material_expression(material, unreal.MaterialExpressionConstant, -350, 200)
    rough.set_editor_property("r", roughness)
    library.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    library.recompile_material(material)
    unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
    return material


def spawn(actor_class, label, location=(0, 0, 0), rotation=(0, 0, 0)):
    """rotation is (pitch, yaw, roll) in degrees."""
    actor = actors.spawn_actor_from_class(
        actor_class, unreal.Vector(*location), unreal.Rotator(roll=rotation[2], pitch=rotation[0], yaw=rotation[1]))
    actor.set_actor_label(label)
    actor.tags = [TAG]
    return actor


def spawn_mesh(label, shape, location, scale, material, yaw=0.0):
    actor = spawn(unreal.StaticMeshActor, label, location, (0, yaw, 0))
    component = actor.static_mesh_component
    component.set_static_mesh(unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/%s.%s" % (shape, shape)))
    component.set_material(0, material)
    actor.set_actor_scale3d(unreal.Vector(*scale))
    return actor


def build():
    if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        levels.load_level(MAP_PATH)
        for actor in actors.get_all_level_actors():
            if TAG in [str(tag) for tag in actor.tags]:
                actors.destroy_actor(actor)
    else:
        levels.new_level(MAP_PATH)

    floor = make_material("M_BootstrapFloor", (0.30, 0.30, 0.29), 0.85)
    plaster = make_material("M_BootstrapPlaster", (0.72, 0.66, 0.55), 0.7)
    red = make_material("M_BootstrapRed", (0.55, 0.06, 0.04), 0.45)
    teal = make_material("M_BootstrapTeal", (0.05, 0.33, 0.36), 0.3)

    # The engine's cube, sphere and cylinder are 100 cm across, centred on their origin.
    spawn_mesh("Floor", "Cube", (0, 0, -25), (60, 60, 0.5), floor)
    spawn_mesh("Box_Large", "Cube", (600, -250, 150), (3, 3, 3), plaster, 20)
    spawn_mesh("Box_Red", "Cube", (450, 250, 50), (1, 1, 1), red, -15)
    spawn_mesh("Box_Step", "Cube", (300, 420, 20), (2, 2, 0.4), plaster)       # 40 cm: just under the step height
    spawn_mesh("Box_Wall", "Cube", (1100, 100, 200), (0.4, 12, 4), plaster)
    spawn_mesh("Sphere_Teal", "Sphere", (520, 40, 75), (1.5, 1.5, 1.5), teal)
    spawn_mesh("Cylinder_Red", "Cylinder", (780, 380, 100), (1, 1, 2), red)

    spawn(unreal.PlayerStart, "PlayerStart", (0, 0, 100), (0, 0, 0))

    sun = spawn(unreal.DirectionalLight, "Sun", (0, 0, 800), (-40, 35, 0))   # light travels east-south-east, down
    sun_component = sun.get_component_by_class(unreal.DirectionalLightComponent)
    sun_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun_component.set_editor_property("intensity", 10.0)                # lux
    sun_component.set_editor_property("atmosphere_sun_light", True)

    spawn(unreal.SkyAtmosphere, "SkyAtmosphere")

    sky = spawn(unreal.SkyLight, "SkyLight", (0, 0, 600))
    sky_component = sky.get_component_by_class(unreal.SkyLightComponent)
    sky_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky_component.set_editor_property("real_time_capture", True)

    fog = spawn(unreal.ExponentialHeightFog, "HeightFog", (0, 0, 0))
    fog_component = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fog_component.set_editor_property("fog_density", 0.01)

    volume = spawn(unreal.PostProcessVolume, "PostProcess", (0, 0, 0))
    volume.set_editor_property("unbound", True)
    settings = volume.get_editor_property("settings")
    for name, value in (
            ("dynamic_global_illumination_method", unreal.DynamicGlobalIlluminationMethod.LUMEN),
            ("reflection_method", unreal.ReflectionMethod.LUMEN),
            ("auto_exposure_min_brightness", EXPOSURE_EV100),
            ("auto_exposure_max_brightness", EXPOSURE_EV100)):
        settings.set_editor_property("override_" + name, True)
        settings.set_editor_property(name, value)
    volume.set_editor_property("settings", settings)

    saved = levels.save_current_level()
    count = len([a for a in actors.get_all_level_actors() if TAG in [str(tag) for tag in a.tags]])
    result = "L_Bootstrap: %d actors, saved=%s, world=%s" % (
        count, saved, unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name())
    unreal.log(result)
    return result


RESULT = build()
RESULT
