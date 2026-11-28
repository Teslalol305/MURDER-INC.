"""Build L_Midtown (Level 3): import the Midtown art, make the night materials, assemble the map.

Fast build 2026-11-28. Reuses build_block's importers and masters; the art comes from /project/ue/art-in-mt (the
Midtown archive plus the scan sets it names), the map from tools/levels/data/level_midtown.json and the placements
file (art/out/placements/placements_midtown.json). Generated content is not committed.

    import build_midtown; build_midtown.start("all")      # or "textures,materials,meshes,level"; force=True

Progress: <project>/Saved/BuildMidtown/status.txt (last line DONE or FAILED). Units are Unreal's: cm, Z up,
X east, Y south (web (x, y, z) is Unreal (x, z, y) x 100). Every spawned actor carries the tag MIMidtown.
"""
import json
import math
import os
import random
import time
import traceback

import unreal

import build_block as bb

ART = os.environ.get("MI_ART_MT", "/project/ue/art-in-mt")
bb.ART_IN = ART
MAP_PATH = "/Game/Maps/L_Midtown"
TAG = "MIBlock"  # the game finds the art map and switches the art collision off by this tag (presentation.json block.artTag)
MAT, MESH = bb.MAT_DIR, bb.MESH_DIR
SCREEN_MASTER = MAT + "/M_MT_Screen"
WINDOW_MASTER = MAT + "/M_MT_Window"
LIB, ASSETS, ACTORS, LEVELS = bb.LIB, bb.ASSETS, bb.ACTORS, bb.LEVELS

# Night values of the lit slots (linear colour, roughness, metallic, nits): midtown.md 11, 12.3.
NIGHT_SLOTS = {
    "MI_Lamp_Sodium": ((1.0, 0.45, 0.12), 0.2, 0.0, 6000.0),
    "MI_Lamp_LED": ((0.75, 0.85, 1.0), 0.2, 0.0, 9000.0),
    "MI_Lamp_KioskInterior": ((1.0, 0.7, 0.4), 0.3, 0.0, 1500.0),
    "MI_Lamp_Indicator": ((0.1, 1.0, 0.25), 0.3, 0.0, 300.0),
    "MI_Lamp_MarqueeBulb": ((1.0, 0.65, 0.25), 0.2, 0.0, 6000.0),
    "MI_Lamp_Tail": ((1.0, 0.03, 0.02), 0.2, 0.0, 600.0),
    "MI_Stand_RiserGlass": ((1.0, 0.55, 0.15), 0.3, 0.0, 60.0),
    "MI_Neon_Pink": ((1.0, 0.1, 0.45), 0.2, 0.0, 2500.0),
    "MI_Neon_Cyan": ((0.1, 0.8, 1.0), 0.2, 0.0, 2500.0),
}
SCREEN_NITS = {"G1": 160.0, "E1": 160.0, "E3": 160.0, "N1": 160.0}      # the others 100 (the exposure is fixed at EV 3)
GREY = {"brick": "MI_Grey_Brick", "concrete": "MI_Grey_Concrete", "metal": "MI_Grey_Metal", "wood": "MI_Grey_Wood",
        "car": "MI_Grey_Car", "glass": "MI_Grey_Glass", "rubber": "MI_Grey_Metal", "cloth": "MI_Grey_Other"}
MASS_TAGS = {"A", "B", "C", "D", "E", "facade"}      # building masses: pulled in a few cm so the art shows over them


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def level_data():
    return load_json(bb.project_dir("../../tools/levels/data/level_midtown.json"))


def placements():
    return load_json(os.path.join(ART, "placements", "placements_midtown.json"))


# ------------------------------------------------------------------------------------------------ steps 1-2

def texture_units(force):
    return bb.texture_units(force)


def build_screen_master(force):
    if ASSETS.does_asset_exist(SCREEN_MASTER) and not force:
        return "exists"
    if ASSETS.does_asset_exist(SCREEN_MASTER):
        material = unreal.load_asset(SCREEN_MASTER)
        LIB.delete_all_material_expressions(material)
    else:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "M_MT_Screen", MAT, unreal.Material, unreal.MaterialFactoryNew())
    tc = bb.expr(material, unreal.MaterialExpressionTextureCoordinate, -1200, 0)
    names = ("U0", "V0", "U1", "V1")
    params = [bb.expr(material, unreal.MaterialExpressionScalarParameter, -1200, 120 + 100 * i, parameter_name=n,
                      default_value=(1.0 if i >= 2 else 0.0)) for i, n in enumerate(names)]
    node = bb.custom(material, -800, 100, "float u = U0 + UV.x * (U1 - U0);\n"
                     "float v = 1.0 - (V0 + (1.0 - UV.y) * (V1 - V0));\nreturn float2(u, v);",
                     ["UV"] + list(names), unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    LIB.connect_material_expressions(tc, "", node, "UV")
    for n, p in zip(names, params):
        LIB.connect_material_expressions(p, "", node, n)
    atlas = unreal.load_asset(bb.texture_path("MT_Screens_A", "E"))
    tex = bb.expr(material, unreal.MaterialExpressionTextureSampleParameter2D, -450, 0, parameter_name="Atlas",
                  texture=atlas)
    LIB.connect_material_expressions(node, "", tex, "UVs")
    nits = bb.expr(material, unreal.MaterialExpressionScalarParameter, -450, 300, parameter_name="Nits",
                   default_value=300.0)
    glow = bb.expr(material, unreal.MaterialExpressionMultiply, -150, 100)
    LIB.connect_material_expressions(tex, "", glow, "A")
    LIB.connect_material_expressions(nits, "", glow, "B")
    rough = bb.expr(material, unreal.MaterialExpressionConstant, -150, 300, r=0.6)
    LIB.connect_material_property(glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    LIB.recompile_material(material)
    ASSETS.save_asset(SCREEN_MASTER, only_if_is_dirty=False)
    return "created"


WINDOW_HLSL = r"""
// Night windows: each pane cell has its own state from its world position (midtown.md 12.4, art 8):
// about a quarter lit, a long tail of dim ones, tungsten to TV blue, dark reflective glass otherwise.
float3 cell = floor(float3(WP.x * 0.5 + WP.y * 0.5, WP.x * 0.5 - WP.y * 0.5, WP.z) / float3(155.0, 155.0, 160.0));
float h = frac(sin(dot(cell, float3(12.9898, 78.233, 37.719))) * 43758.5453);
float h2 = frac(h * 91.7 + 0.31);
float lit = step(h, Lit);
float bright = lit * (0.12 + 0.88 * h2 * h2);
float3 warm = lerp(float3(1.0, 0.55, 0.22), float3(1.0, 0.85, 0.6), frac(h * 7.3));
float3 tv = float3(0.45, 0.6, 1.0);
float3 col = lerp(warm, tv, step(0.88, frac(h * 13.1)));
Glow = col * bright * Nits;
Rough = 0.28;
return float3(0.012, 0.014, 0.018);
"""


def build_window_master(force):
    if ASSETS.does_asset_exist(WINDOW_MASTER) and not force:
        return "exists"
    if ASSETS.does_asset_exist(WINDOW_MASTER):
        material = unreal.load_asset(WINDOW_MASTER)
        LIB.delete_all_material_expressions(material)
    else:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "M_MT_Window", MAT, unreal.Material, unreal.MaterialFactoryNew())
    wp = bb.world_position(material, -1000, 0)
    lit = bb.expr(material, unreal.MaterialExpressionScalarParameter, -1000, 150, parameter_name="Lit",
                  default_value=0.26)
    nits = bb.expr(material, unreal.MaterialExpressionScalarParameter, -1000, 250, parameter_name="Nits",
                   default_value=180.0)
    node = bb.custom(material, -600, 100, WINDOW_HLSL, ["WP", "Lit", "Nits"],
                     unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                     [("Glow", unreal.CustomMaterialOutputType.CMOT_FLOAT3), "Rough"])
    LIB.connect_material_expressions(wp, "", node, "WP")
    LIB.connect_material_expressions(lit, "", node, "Lit")
    LIB.connect_material_expressions(nits, "", node, "Nits")
    LIB.connect_material_property(node, "", unreal.MaterialProperty.MP_BASE_COLOR)
    LIB.connect_material_property(node, "Glow", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(node, "Rough", unreal.MaterialProperty.MP_ROUGHNESS)
    LIB.recompile_material(material)
    ASSETS.save_asset(WINDOW_MASTER, only_if_is_dirty=False)
    return "created"


BACKDROP_MASTER = MAT + "/M_MT_Backdrop"
BACKDROP_HLSL = r"""
// The far towers: dark walls with small lit panes (a quarter of them), world-aligned on the box faces.
float u = (abs(N.x) > 0.5) ? WP.y : WP.x;
float2 c = float2(u, WP.z) / float2(330.0, 400.0);
float2 id = floor(c);
float2 f = frac(c);
float pane = step(0.22, f.x) * step(f.x, 0.78) * step(0.28, f.y) * step(f.y, 0.72) * step(abs(N.z), 0.5);
float h = frac(sin(dot(float3(id, floor((WP.x + WP.y) * 0.002)), float3(12.9898, 78.233, 37.719))) * 43758.5453);
float h2 = frac(h * 91.7 + 0.31);
float lit = step(h, Lit) * pane;
float3 warm = lerp(float3(1.0, 0.6, 0.28), float3(1.0, 0.85, 0.62), frac(h * 7.3));
float3 col = lerp(warm, float3(0.55, 0.7, 1.0), step(0.85, frac(h * 13.1)));
Glow = col * lit * (0.2 + 0.8 * h2) * Nits;
Rough = 0.5;
return float3(0.018, 0.02, 0.026);
"""


def build_backdrop_master(force):
    if ASSETS.does_asset_exist(BACKDROP_MASTER) and not force:
        return "exists"
    if ASSETS.does_asset_exist(BACKDROP_MASTER):
        material = unreal.load_asset(BACKDROP_MASTER)
        LIB.delete_all_material_expressions(material)
    else:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "M_MT_Backdrop", MAT, unreal.Material, unreal.MaterialFactoryNew())
    wp = bb.world_position(material, -1000, 0)
    normal = bb.expr(material, unreal.MaterialExpressionPixelNormalWS, -1000, 100)
    lit = bb.expr(material, unreal.MaterialExpressionScalarParameter, -1000, 200, parameter_name="Lit", default_value=0.24)
    nits = bb.expr(material, unreal.MaterialExpressionScalarParameter, -1000, 300, parameter_name="Nits", default_value=90.0)
    node = bb.custom(material, -600, 100, BACKDROP_HLSL, ["WP", "N", "Lit", "Nits"],
                     unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                     [("Glow", unreal.CustomMaterialOutputType.CMOT_FLOAT3), "Rough"])
    for name, src in (("WP", wp), ("N", normal), ("Lit", lit), ("Nits", nits)):
        LIB.connect_material_expressions(src, "", node, name)
    LIB.connect_material_property(node, "", unreal.MaterialProperty.MP_BASE_COLOR)
    LIB.connect_material_property(node, "Glow", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(node, "Rough", unreal.MaterialProperty.MP_ROUGHNESS)
    LIB.recompile_material(material)
    ASSETS.save_asset(BACKDROP_MASTER, only_if_is_dirty=False)
    return "created"


def make_simple(name, parent, force, fn):
    path = "%s/%s" % (MAT, name)
    if ASSETS.does_asset_exist(path) and not force:
        return "exists"
    instance = bb.instance_of(name, parent, True)
    fn(instance)
    return bb.finish_instance(instance, name)


def screen_cells():
    """Atlas cell -> (set, u0, v0, u1, v1) from the two atlases' set.json files."""
    cells = {}
    for atlas in ("MT_Screens_A", "MT_Screens_B"):
        info = load_json(os.path.join(ART, "textures", atlas, "set.json"))
        for key, cell in info["cells"].items():
            cells[key] = (atlas,) + tuple(cell["uv"])
    return cells


def screen_instance_name(screen, tile, tiles, cell):
    if tile is None:
        return "MI_MT_Screen_%s" % screen
    return "MI_MT_Screen_%s_%d_%d" % (screen, tile[0], tile[1])


def screen_units(force):
    cells = screen_cells()
    seen = set()
    for item in placements()["instances"]:
        if "screen" not in item or "Edge" in item["mesh"]:
            continue
        screen, tile, tiles = item["screen"], item.get("tile"), item.get("tiles")
        first = item.get("first_slide") or ("G1_Takeover" if screen == "G1" else None)
        if first not in cells and screen == "G1":
            first = next((k for k in cells if k.startswith("G1_")), None)
        if screen == "N1":
            first = next((k for k in cells if k.startswith("N1_")), None)
        if first not in cells:
            first = next((k for k in cells if k.startswith(screen + "_")), None)
        if first is None:
            continue
        name = screen_instance_name(screen, tile, tiles, first)
        if name in seen:
            continue
        seen.add(name)
        atlas, u0, v0, u1, v1 = cells[first]
        if tile is not None and tiles:
            cols, rows = tiles
            du, dv = (u1 - u0) / cols, (v1 - v0) / rows
            u0, u1 = u0 + du * tile[0], u0 + du * (tile[0] + 1)
            v0, v1 = v0 + dv * tile[1], v0 + dv * (tile[1] + 1)

        def setup(instance, atlas=atlas, rect=(u0, v0, u1, v1), nits=SCREEN_NITS.get(screen, 100.0)):
            LIB.set_material_instance_texture_parameter_value(instance, "Atlas",
                                                              unreal.load_asset(bb.texture_path(atlas, "E")))
            for key, value in zip(("U0", "V0", "U1", "V1"), rect):
                LIB.set_material_instance_scalar_parameter_value(instance, key, value)
            LIB.set_material_instance_scalar_parameter_value(instance, "Nits", nits)
        yield "screen " + name, (lambda n=name, s=setup: make_simple(n, SCREEN_MASTER, force, s))


# The canvas scan is blue (mean 0.28, 0.41, 0.61): the manifest's tint made the netting lime under the lamps.
TINT_FIXES = {"MI_Fabric_ScaffoldNet": (0.14, 0.14, 0.15)}


def tint_fixes():
    done = []
    for name, tint in TINT_FIXES.items():
        instance = unreal.load_asset("%s/%s" % (MAT, name))
        if instance is not None:
            LIB.set_material_instance_vector_parameter_value(instance, "Tint", unreal.LinearColor(tint[0], tint[1], tint[2], 1))
            LIB.update_material_instance(instance)
            ASSETS.save_asset("%s/%s" % (MAT, name), only_if_is_dirty=False)
            done.append(name)
    return "tinted " + ",".join(done)


def material_units(force):
    for unit in bb.material_units(force):
        yield unit
    yield "screen master", lambda: build_screen_master(force)
    yield "window master", lambda: build_window_master(force)
    yield "backdrop master", lambda: build_backdrop_master(force)
    yield "backdrop instance", lambda: make_simple("MI_MT_Backdrop", BACKDROP_MASTER, force, lambda i: None)
    for unit in screen_units(force):
        yield unit

    def window(instance):
        LIB.set_material_instance_scalar_parameter_value(instance, "Lit", 0.26)
        LIB.set_material_instance_scalar_parameter_value(instance, "Nits", 180.0)
    yield "window instance", lambda: make_simple("MI_MT_Window", WINDOW_MASTER, force, window)
    yield "sign face", lambda: bb.make_instance("MI_MT_SignFace", "Sign_MT_Atlas1", (1, 1, 1), None, None, None, 0.0,
                                                force, emissive=900.0)
    yield "ticker", lambda: bb.make_instance("MI_MT_Ticker", "MT_Ticker", (1, 1, 1), None, None, None, 0.0, force,
                                             emissive=300.0)
    yield "tint fixes", tint_fixes
    yield "net", lambda: bb.make_flat_instance("MI_MT_Net", ((0.03, 0.045, 0.05), 0.9, 0.0, 0.0), True)
    for name, colour in CANVAS_FLAT.items():
        yield "canvas " + name, (lambda n="MI_MT_" + name[3:], c=colour: bb.make_flat_instance(n, (c, 0.9, 0.0, 0.0), True))
    for name, values in NIGHT_SLOTS.items():
        yield "night " + name, (lambda n="MI_MT_" + name[3:], v=values: bb.make_flat_instance(n, v, True))


# ---------------------------------------------------------------------------------------------------- meshes

def mesh_units(force):
    man = bb.manifest()
    for name, asset in bb.art_assets(man).items():
        if name.endswith("_LOD1"):
            continue                   # Nanite is on for every mesh: the LOD1s are not needed
        yield "mesh " + name, (lambda n=name, a=asset: import_and_fix(n, a, force))


# Every slot on the canvas scan came out lime under the lamps (the scan is blue, the manifest tints assume white):
# flat cloth colours instead (linear colour, roughness).
CANVAS_FLAT = {"MI_Fabric_ScaffoldNet": (0.03, 0.045, 0.05), "MI_Fabric_Scrim": (0.04, 0.04, 0.045),
               "MI_Fabric_UmbrellaNavy": (0.015, 0.025, 0.08), "MI_Fabric_Cushion": (0.12, 0.2, 0.22),
               "MI_Fabric_TentWhite": (0.5, 0.5, 0.48), "MI_Fabric_TentBlack": (0.02, 0.02, 0.022)}
SLOT_OVERRIDE = {"M_MT_WindowGrid": "MI_MT_Window", "M_Sign_MT_Face": "MI_MT_SignFace", "M_MT_Ticker": "MI_MT_Ticker",
                 "MI_Fabric_ScaffoldNet": "MI_MT_Net"}
for _slot in CANVAS_FLAT:
    SLOT_OVERRIDE[_slot] = "MI_MT_" + _slot[3:]
for _slot in NIGHT_SLOTS:
    SLOT_OVERRIDE[_slot] = "MI_MT_" + _slot[3:]


def fix_slots():
    """Re-assign the night overrides on every imported mesh (no import)."""
    changed = 0
    for name in bb.art_assets(bb.manifest()):
        path = "%s/%s" % (MESH, name)
        if not ASSETS.does_asset_exist(path):
            continue
        mesh = unreal.load_asset(path)
        dirty = False
        for index, entry in enumerate(mesh.get_editor_property("static_materials")):
            target = SLOT_OVERRIDE.get(str(entry.get_editor_property("material_slot_name")))
            if target and ASSETS.does_asset_exist("%s/%s" % (MAT, target)):
                mesh.set_material(index, unreal.load_asset("%s/%s" % (MAT, target)))
                dirty = True
        if dirty:
            ASSETS.save_asset(path, only_if_is_dirty=False)
            changed += 1
    return "%d meshes re-slotted" % changed


def import_and_fix(name, asset, force):
    result = bb.import_mesh(name, asset, force)
    path = "%s/%s" % (MESH, name)
    mesh = unreal.load_asset(path)
    changed = 0
    for index, entry in enumerate(mesh.get_editor_property("static_materials")):
        slot = str(entry.get_editor_property("material_slot_name"))
        target = SLOT_OVERRIDE.get(slot)
        if target is None and slot == "M_MI_Screen":
            target = "MI_MT_Screen_G1"
        if target and ASSETS.does_asset_exist("%s/%s" % (MAT, target)):
            mesh.set_material(index, unreal.load_asset("%s/%s" % (MAT, target)))
            changed += 1
    if changed:
        ASSETS.save_asset(path, only_if_is_dirty=False)
    return result + ("; night slots %d" % changed if changed else "")


# ----------------------------------------------------------------------------------------------------- level

def open_map():
    if ASSETS.does_asset_exist(MAP_PATH):
        bb.load_level(MAP_PATH)
        doomed = [a for a in ACTORS.get_all_level_actors() if TAG in [str(t) for t in a.tags]]
        for actor in doomed:
            ACTORS.destroy_actor(actor)
        return "loaded, removed %d old actors" % len(doomed)
    LEVELS.new_level(MAP_PATH)
    return "new level"


def tag(actor, label, folder):
    actor.set_actor_label(label)
    actor.tags = [TAG]
    actor.set_folder_path(folder)
    return actor


def spawn_mesh(path, label, folder, location, yaw=0.0, scale=None, material=None, collide=False):
    mesh = unreal.load_asset(path)
    actor = ACTORS.spawn_actor_from_object(mesh, unreal.Vector(*location), bb.rotator(yaw=yaw))
    if scale:
        actor.set_actor_scale3d(unreal.Vector(*scale))
    if material is not None:
        actor.static_mesh_component.set_material(0, material)
    if not collide:
        actor.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return tag(actor, label, folder)


def box_actor(label, folder, centre, extent, material, hidden):
    actor = bb.spawn_box(label, folder, centre, extent, material)
    tag(actor, label, folder)
    if hidden:
        component = actor.static_mesh_component
        component.set_visibility(False)
        component.set_hidden_in_game(True)
        bb.setp(component, "cast_shadow", False)
        bb.setp(component, "affect_distance_field_lighting", False)
    return actor


def material(name):
    return unreal.load_asset("%s/%s" % (MAT, name))


def ground_chunk(level):
    count = 0
    for k, surface in enumerate(level["ground"]["surfaces"]):
        ue = surface["ue"]
        name = bb.GROUND_SURFACE.get(surface["surface"], bb.GROUND_SURFACE["concrete"])[0]
        centre = ((ue["minX"] + ue["maxX"]) / 2.0, (ue["minY"] + ue["maxY"]) / 2.0, -5.0)
        extent = ((ue["maxX"] - ue["minX"]) / 2.0, (ue["maxY"] - ue["minY"]) / 2.0, 5.0)
        box_actor("Ground_%02d_%s" % (k, surface["surface"]), "Midtown/Ground", centre, extent, material(name), False)
        count += 1
    far = material(bb.GROUND_SURFACE["far"][0])
    box_actor("Ground_Far", "Midtown/Ground", (0, 0, -12.0), (500000, 500000, 10.0), far, False)
    return "%d slabs and the far ground" % (count + 1)


def backdrop_units(level):
    """A ring of dark towers beyond the play area, windows lit by the window master: the city past the avenues."""
    rng = random.Random(1147)
    b = level["bounds"]["ue"]
    wall = material("MI_MT_Backdrop")

    def chunk():
        made = 0
        x0, x1, y0, y1 = b["minX"], b["maxX"], b["minY"], b["maxY"]
        for ring, (gap, count_scale) in enumerate(((1400.0, 1.0), (4200.0, 0.8), (9000.0, 0.7))):
            # walk the perimeter of the (grown) rectangle, one tower per step
            rect = (x0 - gap, x1 + gap, y0 - gap, y1 + gap)
            step = 2600.0
            points = []
            x = rect[0]
            while x < rect[1]:
                points += [(x, rect[2], 0), (x, rect[3], 0)]
                x += step * rng.uniform(0.8, 1.3)
            y = rect[2]
            while y < rect[3]:
                points += [(rect[0], y, 1), (rect[1], y, 1)]
                y += step * rng.uniform(0.8, 1.3)
            for (px, py, along) in points:
                if rng.random() > count_scale:
                    continue
                w = rng.uniform(1800.0, 3200.0)
                h = rng.uniform(5000.0, 12000.0) * (1.0 + ring * 0.9)
                d = rng.uniform(2200.0, 4200.0)
                actor = box_actor("Backdrop_%d_%03d" % (ring, made), "Midtown/Backdrop", (px, py, h / 2.0 - 10.0),
                                  (w / 2.0, d / 2.0, h / 2.0), wall, False)
                actor.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                made += 1
        return "%d towers" % made
    yield "backdrop", chunk


# Colliders whose art is placed by the art lane's own list rather than fitted to a collider index (the stairs, the
# parapets, the scaffold, the gantry and its wall): their boxes stay as invisible collision under the art.
ART_DRAWN_TAGS = {"parapet", "roof-guard", "roof-stair", "stair-rail", "bridge-rail", "bridge", "planks", "pipe-bridge",
                  "gantry", "gantry-guard", "led-wall", "cabinet", "scaffold", "scaffold-guard", "shed-deck",
                  "shed-post", "shed-guard", "billboard"}


def covered_colliders(plan):
    cover = set()
    for item in plan["instances"]:
        fit = item.get("fit")
        if fit:
            cover.update(fit["colliders"])
    return cover


def collider_units(level, plan):
    cover = covered_colliders(plan)
    boxes = [b for b in level["colliders"]["boxes"] if b["blocks"]["movement"] or b["blocks"]["shots"]]
    for start in range(0, len(boxes), 120):
        def chunk(items=boxes[start:start + 120]):
            hidden = 0
            for box in items:
                c, e = dict(box["ue"]["center"]), dict(box["ue"]["extent"])
                tagname = box["tag"]
                name = GREY.get(box["surface"], "MI_Grey_Other")
                mass = tagname in MASS_TAGS
                art = (box["index"] in cover or tagname in ART_DRAWN_TAGS) and not mass
                if mass:
                    e["X"] = max(e["X"] - 32.0, 1.0)
                    e["Y"] = max(e["Y"] - 32.0, 1.0)
                    e["Z"] = max(e["Z"] - 3.0, 1.0)
                    c["Z"] -= 1.5
                if tagname in ("sidewalk", "plaza", "floor", "deck"):
                    name = "MI_Grey_Concrete"
                actor = box_actor("%s_%03d_%s" % ("Collision" if art else "Grey", box["index"], tagname.replace(" ", "_")),
                                  "Midtown/Collision" if art else "Midtown/GreyBox", (c["X"], c["Y"], c["Z"]),
                                  (e["X"], e["Y"], e["Z"]), material(name), art)
                if mass:
                    actor.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                    # the mass keeps its collision as a second, hidden full-size box
                    box_actor("Collision_%03d_%s" % (box["index"], tagname), "Midtown/Collision",
                              (box["ue"]["center"]["X"], box["ue"]["center"]["Y"], box["ue"]["center"]["Z"]),
                              (box["ue"]["extent"]["X"], box["ue"]["extent"]["Y"], box["ue"]["extent"]["Z"]),
                              material(name), True)
                hidden += 1 if art else 0
            return "%d boxes, %d hidden under art" % (len(items), hidden)
        yield "colliders %d of %d" % (start, len(boxes)), chunk


# The art lane put E1, E2a and E2b on x = 33 and S1 on z = 36.4, behind the facade modules of round 3 (front planes at
# x = 30 and z = 36): moved in front of them, 45 cm clear of the cornices' 40 cm, so the screens show.
SCREEN_SHIFT = {"E1": (-345.0, 0.0), "E2a": (-345.0, 0.0), "E2b": (-345.0, 0.0), "S1": (0.0, -55.0)}


def shifted(item):
    location = list(item["location_cm"])
    dx, dy = SCREEN_SHIFT.get(item.get("screen"), (0.0, 0.0))
    return (location[0] + dx, location[1] + dy, location[2])


def art_units(plan):
    groups, singles = {}, []
    for item in plan["instances"]:
        mesh = item["mesh"]
        if not ASSETS.does_asset_exist("%s/%s" % (MESH, mesh)):
            continue
        if "screen" in item and "Edge" not in mesh:
            singles.append(item)
        else:
            groups.setdefault(mesh, []).append(item)

    def xform(item):
        s = item.get("scale") or (1.0, 1.0, 1.0)
        return bb.transform(shifted(item), item["yaw"], tuple(s))

    names = sorted(groups)
    for start in range(0, len(names), 12):
        def chunk(batch=names[start:start + 12]):
            total = 0
            for mesh in batch:
                holder = bb.instance_holder("Art_" + mesh[3:], "Midtown/Art")
                tag(holder, "Art_" + mesh[3:], "Midtown/Art")
                bb.add_instances(holder, "%s/%s" % (MESH, mesh), [xform(i) for i in groups[mesh]])
                total += len(groups[mesh])
            return "%d meshes, %d instances" % (len(batch), total)
        yield "art %d of %d" % (start, len(names)), chunk

    cells = screen_cells()

    def screens():
        made = 0
        for item in singles:
            screen, tile, tiles = item["screen"], item.get("tile"), item.get("tiles")
            first = item.get("first_slide")
            if first not in cells:
                first = next((k for k in cells if k.startswith(screen + "_")), None)
            name = screen_instance_name(screen, tile, tiles, first)
            mi = material(name)
            s = item.get("scale") or (1.0, 1.0, 1.0)
            actor = spawn_mesh("%s/%s" % (MESH, item["mesh"]), "Screen_%s_%d" % (screen, made), "Midtown/Screens",
                               shifted(item), item["yaw"], tuple(s))
            if mi is not None:
                mesh = unreal.load_asset("%s/%s" % (MESH, item["mesh"]))
                for index, entry in enumerate(mesh.get_editor_property("static_materials")):
                    if str(entry.get_editor_property("material_slot_name")) == "M_MI_Screen":
                        actor.static_mesh_component.set_material(index, mi)
            made += 1
        return "%d screen faces" % made
    yield "screens", screens


# ---------------------------------------------------------------------------------------------------- night

def setp(target, name, value):
    bb.setp(target, name, value)


def add_light(cls, label, location, rot=(0, 0, 0), colour=(1, 1, 1), intensity=1000.0, radius=1500.0, shadows=False,
              cone=None, rect=None):
    actor = bb.spawn_class(cls, label, "Midtown/Light", location, rot)
    tag(actor, label, "Midtown/Light")
    component = actor.get_component_by_class(unreal.LightComponent)
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    setp(component, "intensity", intensity)
    setp(component, "light_color", unreal.Color(int(colour[0] * 255), int(colour[1] * 255), int(colour[2] * 255), 255))
    setp(component, "cast_shadows", shadows)
    if hasattr(component, "attenuation_radius") or True:
        setp(component, "attenuation_radius", radius)
    if cone:
        setp(component, "outer_cone_angle", cone)
        setp(component, "inner_cone_angle", cone * 0.6)
    if rect:
        setp(component, "source_width", rect[0])
        setp(component, "source_height", rect[1])
        setp(component, "barn_door_angle", 0.0)
    return actor


def night_rig(level):
    # Moon: a faint cool key from the south-west, shadows from it kept to the two cascades the budget allows.
    sun = bb.spawn_class(unreal.DirectionalLight, "Moon", "Midtown/Light", (0, 0, 5000), (-38, 55, 0))
    tag(sun, "Moon", "Midtown/Light")
    light = sun.get_component_by_class(unreal.DirectionalLightComponent)
    light.set_mobility(unreal.ComponentMobility.MOVABLE)
    setp(light, "intensity", 20.0)
    setp(light, "light_color", unreal.Color(150, 175, 255, 255))
    setp(light, "atmosphere_sun_light", False)
    setp(light, "cast_shadows", True)
    setp(light, "dynamic_shadow_cascades", 2)
    setp(light, "dynamic_shadow_distance_movable_light", 6000.0)

    atm = bb.spawn_class(unreal.SkyAtmosphere, "SkyAtmosphere", "Midtown/Light")
    tag(atm, "SkyAtmosphere", "Midtown/Light")

    sky = bb.spawn_class(unreal.SkyLight, "SkyLight", "Midtown/Light", (0, 0, 1000))
    tag(sky, "SkyLight", "Midtown/Light")
    sk = sky.get_component_by_class(unreal.SkyLightComponent)
    sk.set_mobility(unreal.ComponentMobility.MOVABLE)
    setp(sk, "real_time_capture", True)
    setp(sk, "intensity", 5.0)
    setp(sk, "light_color", unreal.Color(120, 90, 130, 255))
    setp(sk, "lower_hemisphere_is_black", False)
    setp(sk, "lower_hemisphere_color", unreal.LinearColor(0.05, 0.035, 0.04, 1))

    fog = bb.spawn_class(unreal.ExponentialHeightFog, "NightHaze", "Midtown/Light", (0, 0, 0))
    tag(fog, "NightHaze", "Midtown/Light")
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    setp(fc, "fog_density", 0.004)
    setp(fc, "fog_height_falloff", 0.012)
    setp(fc, "fog_inscattering_luminance", unreal.LinearColor(0.06, 0.03, 0.05, 1))
    setp(fc, "enable_volumetric_fog", True)
    setp(fc, "volumetric_fog_extinction_scale", 2.0)

    volume = bb.spawn_class(unreal.PostProcessVolume, "NightPost", "Midtown/Light")
    tag(volume, "NightPost", "Midtown/Light")
    volume.set_editor_property("unbound", True)
    settings = volume.get_editor_property("settings")
    for name, value in (
            ("dynamic_global_illumination_method", unreal.DynamicGlobalIlluminationMethod.LUMEN),
            ("reflection_method", unreal.ReflectionMethod.LUMEN),
            ("auto_exposure_method", unreal.AutoExposureMethod.AEM_HISTOGRAM),
            ("auto_exposure_min_brightness", 3.0), ("auto_exposure_max_brightness", 3.0),
            ("auto_exposure_bias", 0.0), ("auto_exposure_speed_up", 6.0), ("auto_exposure_speed_down", 6.0),
            ("bloom_intensity", 0.5), ("bloom_threshold", -1.0), ("vignette_intensity", 0.25),
            ("lumen_final_gather_quality", 1.0)):
        try:
            settings.set_editor_property("override_" + name, True)
            settings.set_editor_property(name, value)
        except Exception as error:   # noqa: BLE001
            unreal.log_warning("build_midtown: post %s: %s" % (name, error))
    volume.set_editor_property("settings", settings)

    # Placed lights (at most 26): street lamps and plaza poles are spots with shadows, the screens' glow rects.
    count = 0
    plan = placements()["instances"]
    lamp_pos = [tuple(i["location_cm"]) for i in plan if i["mesh"] == "SM_Furn_StreetLamp"]
    for k, (x, y, z) in enumerate(lamp_pos[:8]):
        add_light(unreal.SpotLight, "Lamp_%d" % k, (x, y, z + 560), (-90, 0, 0), (1.0, 0.62, 0.3), 4500.0, 2200.0,
                  True, 70.0)
        count += 1
    work = [tuple(i["location_cm"]) for i in plan if i["mesh"] == "SM_Roof_WorkLight"]
    for k, (x, y, z) in enumerate(work[:9]):
        add_light(unreal.SpotLight, "Work_%d" % k, (x, y, z + 250), (-65, 0, 0), (1.0, 0.7, 0.4), 3500.0, 1800.0,
                  True, 75.0)
        count += 1
    heights = level["layout"]["WALK_LEVELS"]
    for k, door in enumerate(level["checks"]["goonDoors"][:8]):
        y = heights.get(door.get("layer"), 0.0)
        add_light(unreal.PointLight, "Door_%d" % k, (door["x"] * 100.0, door["z"] * 100.0, (y + 3.2) * 100.0),
                  (0, 0, 0), (1.0, 0.72, 0.45), 1800.0, 1600.0, False)
        count += 1
    poles = [i for i in level["propPlacements"]["items"] if i["name"] in ("light_pole",)]
    for k, p in enumerate(poles[:4]):
        pos = p["ue"]["pos"]
        add_light(unreal.SpotLight, "Pole_%d" % k, (pos["X"], pos["Y"], 650.0), (-90, 0, 0), (0.8, 0.9, 1.0),
                  7000.0, 2600.0, True, 80.0)
        count += 1
    for sid, colour, intensity in (("E1", (1.0, 0.5, 0.7), 60000.0), ("E3", (0.5, 0.6, 1.0), 50000.0),
                                   ("G1", (0.9, 0.9, 1.0), 40000.0), ("E2a", (0.6, 1.0, 0.8), 25000.0),
                                   ("N1", (1.0, 0.8, 0.6), 25000.0), ("S1", (0.8, 0.7, 1.0), 20000.0)):
        screen = next((s for s in level["signage"]["placements"] if s["id"] == sid), None)
        if screen is None:
            continue
        p = screen["ue"]["pos"]
        n = screen["web"]["normal"]
        yaw = math.degrees(math.atan2(n["z"], n["x"]))
        add_light(unreal.RectLight, "Screen_" + sid, (p["X"] + n["x"] * 150, p["Y"] + n["z"] * 150, p["Z"]),
                  (0, yaw, 0), colour, intensity, 3500.0, False, None,
                  (screen["ue"]["width"] * 0.8, screen["ue"]["height"] * 0.8))
        count += 1
    return "moon, atmosphere, sky, haze, post, %d placed lights" % count


def start_and_save(level):
    start = level["playerStart"]["ue"]
    bb.spawn_class(unreal.PlayerStart, "PlayerStart", "Midtown", (start["pos"]["X"], start["pos"]["Y"],
                                                                  start["pos"]["Z"] + 92.0), (0, start["yaw"], 0))
    return night_rig(level)


def level_units(force):
    level = level_data()
    plan = placements()
    yield "open map", open_map
    yield "ground", lambda: ground_chunk(level)
    for unit in collider_units(level, plan):
        yield unit
    for unit in backdrop_units(level):
        yield unit
    for unit in art_units(plan):
        yield unit
    yield "player start and night rig", lambda: start_and_save(level)

    def save():
        saved = LEVELS.save_current_level()
        count = len([a for a in ACTORS.get_all_level_actors() if TAG in [str(t) for t in a.tags]])
        return "saved=%s, %d actors" % (saved, count)
    yield "save", save


# ---------------------------------------------------------------------------------------------------- the job

STEPS = {"textures": texture_units, "materials": material_units, "meshes": mesh_units, "level": level_units}
_JOB = {}


def status_path():
    folder = os.path.join(bb.project_dir("Saved"), "BuildMidtown")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "status.txt")


def _write(line):
    with open(status_path(), "a", encoding="utf-8") as handle:
        handle.write("%s %s\n" % (time.strftime("%H:%M:%S"), line))
    unreal.log("build_midtown: " + line)


def _tick(delta_seconds):
    job = _JOB
    if not job or job.get("busy"):
        return
    job["busy"] = True
    try:
        begin = time.time()
        while time.time() - begin < 2.0:
            label, unit = next(job["units"])
            t0 = time.time()
            result = unit()
            job["done"] += 1
            _write("%s: %s (%.1f s)" % (label, result, time.time() - t0))
    except StopIteration:
        _finish("DONE %d units in %.0f s" % (job["done"], time.time() - job["t0"]))
    except Exception:   # noqa: BLE001
        _finish("FAILED " + traceback.format_exc()[-900:].replace("\n", " | "))
    if job:
        job["busy"] = False


def _finish(line):
    _write(line)
    if _JOB.get("handle") is not None:
        unreal.unregister_slate_post_tick_callback(_JOB["handle"])
    _JOB.clear()


def _chain(names, force):
    for name in names:
        for unit in STEPS[name](force):
            yield unit


def start(steps="all", force=False):
    if _JOB:
        return "a build_midtown job is already running"
    names = list(STEPS) if steps == "all" else [s.strip() for s in steps.split(",") if s.strip()]
    with open(status_path(), "w", encoding="utf-8") as handle:
        handle.write("%s START %s force=%s\n" % (time.strftime("%H:%M:%S"), ",".join(names), force))
    _JOB.update(units=_chain(names, force), done=0, t0=time.time())
    _JOB["handle"] = unreal.register_slate_post_tick_callback(_tick)
    return "started %s: poll %s" % (",".join(names), status_path())
