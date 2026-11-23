"""Baked interiors behind the block's glass: a few small rooms are assembled from the art (shop shelving, vending
machine, counters, sofas, beds, boxes), lit by their own lamps, and captured into HDR cube maps
/Game/Art/Interiors/TC_<Room>. M_MI_Glass looks a cube up per window (interior mapping by cube: the eye ray's hit
on the window's room cell, seen from the cell centre), picks one of three per window by a hash of the cell, mirrors
half of them and varies the lamp level, so neighbouring windows differ.

Run as the build_block step "interiors" (it opens /Game/Maps/L_InteriorBake, builds and captures each room, then
reopens /Game/Maps/L_Block). The rooms have the proportions of M_MI_Glass's room cell (BAKE_ROOM): X across the
window, Y into the room (the window wall at -Y), Z up.
"""
import math

import unreal

import build_block as bb

BAKE_MAP = "/Game/Maps/L_InteriorBake"
CUBE_DIR = bb.ROOT + "/Interiors"
BAKE_ROOM = (310.0, 550.0, 310.0)     # cm: M_MI_Glass's Room parameter (across, deep, high)
CUBE_SIZE = 1024
WALL = 10.0
# Box-projected interior surfaces: name -> (texture set, tint, tile metres).
SURFACES = {
    "MI_Int_WallCream": ("TS_Block_ScanPainted", (1.05, 0.98, 0.82), 2.0),
    "MI_Int_WallGreen": ("TS_Block_ScanPainted", (0.62, 0.78, 0.66), 2.0),
    "MI_Int_WallBlue": ("TS_BrickPainted_ScanWhitewash", (0.62, 0.7, 0.86), 2.0),
    "MI_Int_WallWarm": ("TS_BrickPainted_ScanWhitewash", (1.0, 0.84, 0.7), 2.0),
    "MI_Int_Tile": ("TS_Tile_ScanWhite", (1.0, 1.0, 1.0), 1.0),
    "MI_Int_WoodPanel": ("TS_Wood_ScanPlankDark", (1.6, 1.45, 1.3), 2.0),
    "MI_Int_FloorChecker": ("TS_Tile_ScanChecker", (1.0, 1.0, 1.0), 1.2),
    "MI_Int_FloorLino": ("TS_Floor_ScanLino", (1.0, 1.0, 1.0), 2.0),
    "MI_Int_FloorWood": ("TS_Wood_ScanPlankDark", (0.9, 0.8, 0.7), 2.0),
    "MI_Int_FloorConcrete": ("TS_Floor_ScanSealed", (1.0, 1.0, 1.0), 2.0),
    "MI_Int_Ceiling": ("TS_Steel_PaintWhiteClean", (0.95, 0.95, 0.93), 2.0),
    "MI_Int_Fabric": ("TS_Fabric_ScanCanvas", (0.55, 0.32, 0.25), 1.0),
    "MI_Int_FabricBlue": ("TS_Fabric_ScanCanvas", (0.3, 0.38, 0.6), 1.0),
    "MI_Int_Wood": ("TS_Wood_ScanPlankNew", (0.7, 0.5, 0.36), 1.0),
}
FLATS = {"MI_Int_LampPanel": ((1.0, 0.97, 0.9), 0.5, 0.0, 600.0),
         "MI_Int_LampWarm": ((1.0, 0.78, 0.5), 0.5, 0.0, 400.0),
         "MI_Int_Black": ((0.02, 0.02, 0.02), 0.4, 0.0, 0.0),
         "MI_Int_Frame": ((0.04, 0.035, 0.03), 0.5, 0.0, 0.0)}

X0, X1 = -BAKE_ROOM[0] / 2, BAKE_ROOM[0] / 2
Y0, Y1 = -BAKE_ROOM[1] / 2, BAKE_ROOM[1] / 2
H = BAKE_ROOM[2]
BACK, LEFT, RIGHT = 180.0, -90.0, 90.0   # yaw that turns a prop's front (+Y, props.json) into the room from that wall


def M(name):
    return bb.MESH_DIR + "/" + name


# Rooms: (name, shop, wall, floor, lamps [(x, y, candela, warm)], items). Items: ("mesh", path, (x, y, z), yaw,
# scale) or ("box", material, centre, half extent) or ("sign", set of a sign face, centre, half extent).
ROOMS = [
    ("ShopGrocery", True, "MI_Int_WallCream", "MI_Int_FloorChecker",
     [(-60, -80, 1800, False), (60, 60, 1800, False), (0, 200, 1500, False)],
     [("mesh", M("SM_Prop_ShelfRack_Drawers"), (0, Y1 - 40, 0), BACK, 1.0),
      ("mesh", M("SM_Prop_ShelfRack_Single"), (X0 + 30, 60, 0), LEFT, 1.0),
      ("mesh", M("SM_Prop_ShelfRack_Single"), (X0 + 30, -60, 0), LEFT, 1.0),
      ("mesh", M("SM_Prop_VendingMachine"), (X1 - 50, Y1 - 50, 0), BACK, 1.0),
      ("mesh", M("SM_Prop_Workbench"), (X1 - 45, -60, 0), RIGHT, 1.0),
      ("mesh", M("SM_Prop_CardboardBoxes"), (X1 - 50, 120, 0), RIGHT, 1.0),
      ("mesh", M("SM_Furn_MilkCrates_A"), (-30, 160, 0), 20.0, 1.0),
      ("mesh", M("SM_Prop_PlasticChair"), (60, -160, 0), 130.0, 1.0)]),
    ("ShopParlour", True, "MI_Int_Tile", "MI_Int_FloorLino",
     [(0, -100, 1600, False), (0, 120, 1600, False)],
     [("box", "MI_Int_Wood", (0, Y1 - 35, 45), (120, 30, 45)),             # counter
      ("box", "MI_Int_Black", (0, Y1 - 4, 170), (110, 2, 55)),              # mirror / menu board
      ("sign", "Sign_FoodCartMenu", (0, Y1 - 6, 170), (100, 1, 38)),
      ("mesh", M("SM_Prop_PlasticChair"), (X0 + 40, -100, 0), LEFT, 1.0),
      ("mesh", M("SM_Prop_PlasticChair"), (X0 + 40, -20, 0), LEFT, 1.0),
      ("mesh", M("SM_Prop_PlasticChair"), (X0 + 40, 60, 0), LEFT, 1.0),
      ("mesh", M("SM_Furn_NewspaperBox"), (X1 - 35, -120, 0), RIGHT, 1.0),
      ("mesh", M("SM_Street_TrashCan"), (X1 - 40, 40, 0), RIGHT, 1.0),
      ("mesh", M("SM_Prop_VendingMachine"), (X1 - 50, 150, 0), RIGHT, 1.0)]),
    ("ShopStore", True, "MI_Int_WoodPanel", "MI_Int_FloorConcrete",
     [(0, -60, 3200, True), (0, 150, 3200, True)],
     [("mesh", M("SM_Prop_ShelfRack_Drawers"), (0, Y1 - 40, 0), BACK, 1.0),
      ("mesh", M("SM_Prop_ShelfRack_Narrow"), (X0 + 30, 100, 0), LEFT, 1.0),
      ("mesh", M("SM_Prop_ShelfRack_Narrow"), (X1 - 30, 100, 0), RIGHT, 1.0),
      ("mesh", M("SM_Prop_ToolChest"), (X1 - 35, -60, 0), RIGHT, 1.0),
      ("mesh", M("SM_Prop_CrateWood"), (X0 + 60, -100, 0), 10.0, 1.0),
      ("mesh", M("SM_Prop_CardboardBoxes"), (-40, 60, 0), 35.0, 1.0),
      ("box", "MI_Int_Wood", (60, 0, 45), (35, 90, 45))]),
    ("HomeLiving", False, "MI_Int_WallWarm", "MI_Int_FloorWood",
     [(0, 60, 700, True), (X1 - 50, Y1 - 60, 350, True)],
     [("box", "MI_Int_Fabric", (0, Y1 - 50, 22), (100, 40, 22)),            # sofa seat
      ("box", "MI_Int_Fabric", (0, Y1 - 15, 55), (100, 12, 50)),            # sofa back
      ("box", "MI_Int_Fabric", (-95, Y1 - 50, 40), (10, 40, 30)),
      ("box", "MI_Int_Fabric", (95, Y1 - 50, 40), (10, 40, 30)),
      ("box", "MI_Int_Wood", (0, 80, 22), (55, 30, 4)),                     # coffee table
      ("box", "MI_Int_Wood", (X0 + 25, 0, 45), (22, 70, 45)),               # dresser
      ("box", "MI_Int_Frame", (0, Y1 - 4, 175), (55, 2, 38)),
      ("sign", "Sign_FlyPosters", (0, Y1 - 6, 175), (50, 1, 33)),
      ("box", "MI_Int_Black", (X0 + 25, 0, 115), (14, 40, 25)),             # television
      ("box", "MI_Int_LampWarm", (X1 - 50, Y1 - 60, 150), (12, 12, 12))]),
    ("HomeBedroom", False, "MI_Int_WallBlue", "MI_Int_FloorLino",
     [(0, 40, 650, True)],
     [("box", "MI_Int_Wood", (0, Y1 - 100, 20), (75, 100, 20)),             # bed frame
      ("mesh", M("SM_Furn_Mattress"), (0, Y1 - 100, 40), 90.0, 1.0),
      ("box", "MI_Int_FabricBlue", (0, Y1 - 15, 70), (78, 8, 50)),          # headboard
      ("box", "MI_Int_Wood", (X1 - 25, -40, 60), (22, 50, 60)),             # wardrobe
      ("mesh", M("SM_Prop_CardboardBoxes"), (X0 + 40, -120, 0), 15.0, 1.0),
      ("box", "MI_Int_LampWarm", (X0 + 25, Y1 - 30, 70), (10, 10, 10))]),
    ("HomeVacant", False, "MI_Int_WallGreen", "MI_Int_FloorConcrete",
     [(0, 0, 500, False)],
     [("mesh", M("SM_Furn_Mattress"), (-40, Y1 - 90, 0), 80.0, 1.0),
      ("mesh", M("SM_Prop_CardboardBoxes"), (X1 - 50, 80, 0), 200.0, 1.0),
      ("mesh", M("SM_Furn_TrashBags_A"), (X1 - 60, Y1 - 60, 0), 160.0, 1.0),
      ("mesh", M("SM_Prop_PlasticChair"), (X0 + 50, -60, 0), 30.0, 1.0),
      ("mesh", M("SM_Furn_MilkCrates_B"), (X0 + 40, 140, 0), 0.0, 1.0)]),
]
SHOP_CUBES = [r[0] for r in ROOMS if r[1]]
HOME_CUBES = [r[0] for r in ROOMS if not r[1]]
TAG = "MIInterior"


def cube_path(room):
    return "%s/TC_%s" % (CUBE_DIR, room)


def surface_units(force):
    for name, (set_name, tint, tile) in SURFACES.items():
        yield "surface " + name, (lambda n=name, s=set_name, t=tint, m=tile:
                                  bb.make_instance(n, s, t, None, None, m, 0.0, force, None, True, False))
    for name, values in FLATS.items():
        yield "flat " + name, (lambda n=name, v=values: bb.make_flat_instance(n, v, force))
    for room in ROOMS:
        for item in room[5]:
            if item[0] == "sign":
                name = "MI_Int_" + item[1]
                yield "sign " + name, (lambda n=name, s=item[1]: bb.make_instance(
                    n, s, (1, 1, 1), None, None, None, 0.0, force, None, False, False, emissive=0.0))


def open_bake_map():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    current = world.get_path_name().split(".")[0] if world else ""
    if current != BAKE_MAP:
        if bb.ASSETS.does_asset_exist(BAKE_MAP):
            bb.LEVELS.load_level(BAKE_MAP)
        else:
            bb.LEVELS.new_level(BAKE_MAP)
    clear_room()
    return "bake map open"


def clear_room():
    doomed = [a for a in bb.ACTORS.get_all_level_actors() if TAG in [str(t) for t in a.tags]]
    for actor in doomed:
        bb.ACTORS.destroy_actor(actor)
    return len(doomed)


def mark(actor):
    actor.tags = [TAG]
    return actor


def box(material, centre, extent):
    return mark(bb.spawn_box("IntBox", "Interior", centre, extent, unreal.load_asset(bb.MAT_DIR + "/" + material)))


def build_room(room):
    name, shop, wall, floor, lamps, items = room
    clear_room()
    w = unreal.load_asset(bb.MAT_DIR + "/" + wall)
    box(floor, (0, 0, -WALL / 2), (X1 + WALL, Y1 + WALL, WALL / 2))
    box("MI_Int_Ceiling", (0, 0, H + WALL / 2), (X1 + WALL, Y1 + WALL, WALL / 2))
    for centre, extent in (((0, Y1 + WALL / 2, H / 2), (X1 + WALL, WALL / 2, H / 2)),
                           ((0, Y0 - WALL / 2, H / 2), (X1 + WALL, WALL / 2, H / 2)),
                           ((X0 - WALL / 2, 0, H / 2), (WALL / 2, Y1 + WALL, H / 2)),
                           ((X1 + WALL / 2, 0, H / 2), (WALL / 2, Y1 + WALL, H / 2))):
        mark(bb.spawn_box("IntWall", "Interior", centre, extent, w))
    # A skirting line and, in the shops, a dado of the wall colour darkened.
    for x, y, ex, ey in ((0, Y1 - 1, X1, 1), (X0 + 1, 0, 1, Y1), (X1 - 1, 0, 1, Y1)):
        box("MI_Int_Frame", (x, y, 6), (ex, ey, 6))
    for kind, *rest in items:
        if kind == "mesh":
            path, at, yaw, scale = rest
            if bb.ASSETS.does_asset_exist(path):
                mark(bb.spawn_mesh(path, "IntProp", "Interior", at, yaw, (scale, scale, scale)))
        elif kind == "box":
            material, centre, extent = rest
            box(material, centre, extent)
        elif kind == "sign":
            set_name, centre, extent = rest
            box("MI_Int_" + set_name, centre, extent)
    for x, y, candela, warm in lamps:
        box("MI_Int_LampPanel" if not warm else "MI_Int_LampWarm", (x, y, H - 2), (30 if shop else 14, 30 if shop else 14, 2))
        light = mark(bb.spawn_class(unreal.PointLight, "IntLamp", "Interior", (x, y, H - 30)))
        component = light.point_light_component
        component.set_intensity_units(unreal.LightUnits.CANDELAS)
        component.set_intensity(candela)
        component.set_attenuation_radius(1200.0)
        component.set_source_radius(25.0)
        component.set_light_color(unreal.LinearColor(1.0, 0.82, 0.62, 1) if warm else unreal.LinearColor(1.0, 0.97, 0.92, 1))
    # Bounce stand-in (scene captures get no global illumination here): a soft fill without shadows.
    fill = mark(bb.spawn_class(unreal.PointLight, "IntFill", "Interior", (0, 0, H * 0.45)))
    component = fill.point_light_component
    component.set_intensity_units(unreal.LightUnits.CANDELAS)
    component.set_intensity(sum(l[2] for l in lamps) * 0.18)
    component.set_attenuation_radius(1500.0)
    component.set_cast_shadows(False)
    component.set_light_color(unreal.LinearColor(1.0, 0.9, 0.8, 1))
    return "%s: %d items, %d lamps" % (name, len(items), len(lamps))


_TARGET = {}


def capture_room(room):
    target = _TARGET.get("rt")
    if target is None:
        target = unreal.TextureRenderTargetCube()
        target.set_editor_property("size_x", CUBE_SIZE)
        target.set_editor_property("hdr", True)
        _TARGET["rt"] = target
    actor = mark(bb.spawn_class(unreal.SceneCaptureCube, "IntCapture", "Interior", (0, 0, H / 2)))
    component = actor.get_editor_property("capture_component_cube")
    component.set_editor_property("texture_target", target)
    component.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_SCENE_COLOR_HDR)
    component.set_editor_property("capture_every_frame", False)
    component.capture_scene()
    return "captured " + room[0]


def save_cube(room):
    target = _TARGET["rt"]
    path = cube_path(room[0])
    if bb.ASSETS.does_asset_exist(path):
        texture = unreal.load_asset(path)
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.RenderingLibrary.convert_render_target_to_texture_cube_editor_only(world, target, texture)
    else:
        texture = unreal.RenderingLibrary.render_target_create_static_texture_cube_editor_only(
            target, path, unreal.TextureCompressionSettings.TC_HDR, unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
    if texture is None:
        raise RuntimeError("no cube texture for " + room[0])
    bb.ASSETS.save_asset(path, only_if_is_dirty=False)
    return "saved " + path


def interior_units(force):
    for unit in surface_units(force):
        yield unit
    yield "open bake map", open_bake_map
    for room in ROOMS:
        if bb.ASSETS.does_asset_exist(cube_path(room[0])) and not force:
            continue
        yield "room " + room[0], (lambda r=room: build_room(r))
        yield "capture " + room[0], (lambda r=room: capture_room(r))
        yield "wait " + room[0], (lambda: "frame")
        yield "save " + room[0], (lambda r=room: save_cube(r))

    def back():
        clear_room()
        bb.LEVELS.save_current_level()
        bb.LEVELS.load_level(bb.MAP_PATH)
        return "back in " + bb.MAP_PATH
    yield "reopen block", back
