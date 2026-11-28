"""Canal Street (L_Chinatown): the Block's builder (build_block.py) generalised to the second level.

Fast build 2026-11-28. It reuses build_block's importers and master materials, points them at the Canal art folder
(MI_ART_IN, default /project/ue/maps/canal-art-in: art/out's chinatown family and what its placements use) and assembles
/Game/Maps/L_Chinatown from tools/levels/data/level_chinatown.json (Content/Data/level_chinatown.json) and
art/out/placements/placements_chinatown.json:

  steps (comma list, all by default): textures, materials, meshes, paints, canal

  canal = the level: ground and collider massing (hidden behind the art), the art placements as instanced meshes,
          the night lights (at most 48 placed, shadowed ones spots only), the night rig, the player start.

Collision is not made here: the game builds it at run time from the level's own file (MIBlockGeometry), exactly as in
L_Block. Run: python3 mi_mcp.py py - with `import build_canal; build_canal.start("all")`, poll Saved/BuildBlock/status.txt.
"""
import json
import math
import os
import random

import unreal

import build_block as B

ART = os.environ.get("MI_ART_IN", "/project/ue/maps/canal-art-in")
B.ART_IN = ART
B.TAG = "MICanal"
MAP = "/Game/Maps/L_Chinatown"
FOLDER = "Canal"
ACTORS, ASSETS, LEVELS = B.ACTORS, B.ASSETS, B.LEVELS
_FLAT_VALUES = B.flat_values


def flat_values(slot):
    """Canal slots give `emissive` as a linear colour list as well as a hex string."""
    e = slot.get("emissive")
    if isinstance(e, list):
        return (tuple(e), 0.15, 0.0, B.NEON_DAY_NITS)
    return _FLAT_VALUES(slot)


B.flat_values = flat_values
SKIP_MESH = ("_LOD", "_Far_")            # Nanite does the levels of detail; the far proxies are for non-Nanite cards


def level():
    return B.load_json(os.path.join(B.project_dir("Content"), "Data", "level_chinatown.json"))


def placements():
    return B.load_json(os.path.join(ART, "placements", "placements_chinatown.json"))


# ------------------------------------------------------------------------------------------------ import steps

def mesh_units(force):
    man = B.manifest()
    for name, asset in B.art_assets(man).items():
        if any(s in name for s in SKIP_MESH):
            continue
        yield "mesh " + name, (lambda n=name, a=asset: B.import_mesh(n, a, force))


def paint_units(force):
    """One clear-coat instance per vehicle paint colour of the placements."""
    man = B.manifest()
    seen = {}
    for e in placements()["instances"]:
        if e.get("paint"):
            asset = man["assets"].get(e["mesh"], {})
            for slot in asset.get("material_slots", []):
                if (slot.get("shading") or "").startswith("clear-coat"):
                    seen[(slot["slot"], tuple(e["paint"]))] = slot["set"]
    for (slot, colour), set_name in sorted(seen.items()):
        name = paint_name(slot, colour)
        yield "paint " + name, (lambda n=name, s=set_name, c=colour: B.make_instance(
            n, s, c, None, None, None, 0.0, force, parent=B.CARPAINT_MASTER, emissive=0.0))


def paint_name(slot, colour):
    return "%s_%s" % (B.slot_instance_name(slot), "".join("%02X" % int(round(max(0.0, min(1.0, c)) * 255)) for c in colour))


# ------------------------------------------------------------------------------------------------ sign faces

SIGN_MASTER = B.MAT_DIR + "/M_CT_Sign"
SIGN_NITS = 450.0        # night: lit faces about 450 nits (the lightbox range of chinatown.md 11.3 is 100 to 300 at 1x; bloom helps)
SIGN_HLSL = "return UV * Cell.xy + Cell.zw;"


def sign_cells(pl):
    cells = sorted({(e["atlas"], tuple(e["atlas_uv"])) for e in pl["instances"] if e.get("atlas_uv")})
    return {c: "MI_CTSign_%03d" % k for k, c in enumerate(cells)}


def build_sign_master(force):
    if ASSETS.does_asset_exist(SIGN_MASTER) and not force:
        return "exists"
    if ASSETS.does_asset_exist(SIGN_MASTER):
        material = unreal.load_asset(SIGN_MASTER)
        B.LIB.delete_all_material_expressions(material)
    else:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_CT_Sign", B.MAT_DIR, unreal.Material,
                                                                             unreal.MaterialFactoryNew())
    LIB = B.LIB
    tc = B.expr(material, unreal.MaterialExpressionTextureCoordinate, -1200, 0)
    cell = B.expr(material, unreal.MaterialExpressionVectorParameter, -1200, 160, parameter_name="Cell",
                  default_value=unreal.LinearColor(1, 1, 0, 0))
    uv = B.custom(material, -900, 60, SIGN_HLSL, ["UV", "Cell"], unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    LIB.connect_material_expressions(tc, "", uv, "UV")
    LIB.connect_material_expressions(cell, "", uv, "Cell")

    def sample(name, y, masks=False):
        node = B.expr(material, unreal.MaterialExpressionTextureSampleParameter2D, -600, y, parameter_name=name)
        if masks:
            node.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        node.set_editor_property("texture", unreal.load_asset(B.BLACK_TEXTURE))
        LIB.connect_material_expressions(uv, "", node, "UVs")
        return node
    bc, e, orm = sample("BC", -200), sample("E", 100), sample("ORM", 400, True)
    nits = B.expr(material, unreal.MaterialExpressionScalarParameter, -600, 600, parameter_name="EmissiveScale", default_value=SIGN_NITS)
    glow = B.expr(material, unreal.MaterialExpressionMultiply, -300, 100)
    LIB.connect_material_expressions(e, "RGB", glow, "A")
    LIB.connect_material_expressions(nits, "", glow, "B")
    LIB.connect_material_property(bc, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    LIB.connect_material_property(orm, "G", unreal.MaterialProperty.MP_ROUGHNESS)
    LIB.connect_material_property(orm, "B", unreal.MaterialProperty.MP_METALLIC)
    LIB.connect_material_property(orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    LIB.connect_material_property(glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.recompile_material(material)
    ASSETS.save_asset(SIGN_MASTER, only_if_is_dirty=False)
    return "created"


def make_sign_instance(name, atlas, uv, force):
    instance = B.instance_of(name, SIGN_MASTER, force)
    if instance is None:
        return "exists"
    u0, v0, u1, v1 = uv
    B.LIB.set_material_instance_vector_parameter_value(instance, "Cell", unreal.LinearColor(u1 - u0, v1 - v0, u0, 1.0 - v1))
    for kind in ("BC", "E", "ORM"):
        path = B.texture_path(atlas, kind)
        if ASSETS.does_asset_exist(path):
            B.LIB.set_material_instance_texture_parameter_value(instance, kind, unreal.load_asset(path))
    return B.finish_instance(instance, name)


def sign_units(force):
    pl = placements()
    yield "sign master", lambda: build_sign_master(force)
    # A board with no text of its own (a generic lightbox, a stall board) is dark painted steel, not a white stand-in.
    yield "sign stand-in", lambda: B.make_flat_instance("MI_Sign_CT_Face", ((0.035, 0.035, 0.04), 0.55, 0.0, 0.0), True)
    for (atlas, uv), name in sign_cells(pl).items():
        yield "sign " + name, (lambda n=name, a=atlas, u=uv: make_sign_instance(n, a, u, force))


# ------------------------------------------------------------------------------------------------ wet ground

WET = {"MI_Ground_Asphalt": "MI_CT_Asphalt_Wet", "MI_Ground_Concrete": "MI_CT_Concrete_Wet",
       "MI_Grey_Concrete": "MI_CT_Sidewalk_Wet"}
WETNESS = 0.85     # the street after rain: the master's wetness (darker, roughness toward 0.08 where the set's alpha allows)


def wet_units(force):
    for src, name in WET.items():
        def make(s=src, n=name):
            dst = "%s/%s" % (B.MAT_DIR, n)
            if ASSETS.does_asset_exist(dst) and not force:
                return "exists"
            if ASSETS.does_asset_exist(dst):
                ASSETS.delete_asset(dst)
            ASSETS.duplicate_asset("%s/%s" % (B.MAT_DIR, s), dst)
            inst = unreal.load_asset(dst)
            modes = B.LIB.get_material_instance_vector_parameter_value(inst, "Modes")
            B.LIB.set_material_instance_vector_parameter_value(inst, "Modes", unreal.LinearColor(modes.r, modes.g, modes.b, WETNESS))
            B.LIB.update_material_instance(inst)
            ASSETS.save_asset(dst, only_if_is_dirty=False)
            return "created"
        yield "wet " + name, make


# ------------------------------------------------------------------------------------------------ the level

def open_map():
    if ASSETS.does_asset_exist(MAP):
        B.load_level(MAP)
        doomed = [a for a in ACTORS.get_all_level_actors() if B.TAG in [str(t) for t in a.tags]]
        for a in doomed:
            ACTORS.destroy_actor(a)
        return "loaded, removed %d old actors" % len(doomed)
    LEVELS.new_level(MAP)
    return "new level"


def mat(name):
    path = "%s/%s" % (B.MAT_DIR, name)
    return unreal.load_asset(path) if ASSETS.does_asset_exist(path) else None


def ground_units(lv):
    def ground():
        count = 0
        for k, s in enumerate(lv["ground"]["surfaces"]):
            ue = s["ue"]
            gname = B.GROUND_SURFACE.get(s["surface"], B.GROUND_SURFACE["concrete"])[0]
            m = mat(WET.get(gname, gname))
            B.spawn_box("Ground_%02d_%s" % (k, s["surface"]), FOLDER + "/Ground",
                        ((ue["minX"] + ue["maxX"]) / 2, (ue["minY"] + ue["maxY"]) / 2, -5.0),
                        ((ue["maxX"] - ue["minX"]) / 2, (ue["maxY"] - ue["minY"]) / 2, 5.0), m)
            count += 1
        B.spawn_box("Ground_Far", FOLDER + "/Ground", (0, 0, -12.0), (500000, 500000, 10.0), mat(B.GROUND_SURFACE["far"][0]))
        return "%d slabs and the far ground" % count
    yield "ground", ground


UNMAPPED_PROPS = {"ac_unit", "barricade", "tape_shelf", "gas_cage_frame", "newsstand_bundle"}
SOLID_TOPS = {"sidewalk", "floor"}


def mass_units(lv):
    boxes = []
    for b in lv["colliders"]["boxes"]:
        if not b["blocks"]["movement"] or b["flags"]["bulletOnly"] or b["flags"]["playerOnly"]:
            continue
        kind = b["owner"]["kind"]
        if kind == "level" or (kind == "prop" and b["tag"] in UNMAPPED_PROPS):
            boxes.append(b)
    for start in range(0, len(boxes), 120):
        def chunk(items=boxes[start:start + 120]):
            n = 0
            for b in items:
                tag = b["tag"]
                if tag in ("el-column", "el-girder", "el-deck"):
                    continue
                name = B.GREY_SURFACE.get(b["surface"], B.GREY_SURFACE["other"])[0]
                if tag in B.TAG_SURFACE:
                    name = B.TAG_SURFACE[tag][0]
                if tag == "sidewalk":
                    name = WET.get(name, name)
                c, e = b["ue"]["center"], b["ue"]["extent"]
                inset = 0.0 if tag in SOLID_TOPS else 3.0
                ex = max(e["X"] - inset, 0.5)
                ey = max(e["Y"] - inset, 0.5)
                ez = max(e["Z"] - inset * 0.5, 0.5)
                cz = c["Z"] - (inset * 0.25 if inset else 0)
                a = B.spawn_box("Mass_%03d_%s" % (b["index"], tag.replace(" ", "_")), FOLDER + "/Mass",
                                (c["X"], c["Y"], cz), (ex, ey, ez), mat(name))
                a.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                n += 1
            return "%d masses" % n
        yield "masses %d of %d" % (start, len(boxes)), chunk


def art_units(pl):
    cells = sign_cells(pl)
    by_building = {}
    for e in pl["instances"]:
        by_building.setdefault(e["building"], []).append(e)
    for building, items in sorted(by_building.items()):
        def place(bd=building, entries=items):
            groups, missing = {}, set()
            for e in entries:
                path = "%s/%s" % (B.MESH_DIR, e["mesh"])
                if not ASSETS.does_asset_exist(path):
                    missing.add(e["mesh"])
                    continue
                cell = cells.get((e["atlas"], tuple(e["atlas_uv"]))) if e.get("atlas_uv") else None
                key = (e["mesh"], tuple(e["paint"]) if e.get("paint") else None, cell)
                groups.setdefault(key, []).append(B.transform(e["location_cm"], e["yaw"], tuple(e.get("scale", (1, 1, 1)))))
            holder = B.instance_holder("Art_" + bd, FOLDER + "/Art")
            count = 0
            for (mesh, paint, cell), transforms in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1] or (), kv[0][2] or "")):
                comp = B.add_instances(holder, "%s/%s" % (B.MESH_DIR, mesh), transforms, None, collide=False)
                if paint:
                    man_asset = B.manifest()["assets"].get(mesh, {})
                    for slot in man_asset.get("material_slots", []):
                        if (slot.get("shading") or "").startswith("clear-coat"):
                            m = mat(paint_name(slot["slot"], paint))
                            if m:
                                comp.set_material_by_name(slot["slot"], m)
                if cell and mat(cell):
                    comp.set_material_by_name("M_Sign_CT_Face", mat(cell))
                count += len(transforms)
            return "%d instances, %d meshes%s" % (count, len(groups), ("; missing " + ",".join(sorted(missing))) if missing else "")
        yield "art " + building, place


# ------------------------------------------------------------------------------------------------ lights

LIGHT_COUNT = {"n": 0, "shadowed": 0}


def kelvin(k):
    """Approximate colour of a black body (Tanner Helland), as a linear colour."""
    t = k / 100.0
    r = 255 if t <= 66 else max(0, min(255, 329.698727446 * ((t - 60) ** -0.1332047592)))
    g = max(0, min(255, 99.4708025861 * math.log(t) - 161.1195681661)) if t <= 66 else max(0, min(255, 288.1221695283 * ((t - 60) ** -0.0755148492)))
    b = 255 if t >= 66 else (0 if t <= 19 else max(0, min(255, 138.5177312231 * math.log(t - 10) - 305.0447927307)))
    lin = [(c / 255.0) ** 2.2 for c in (r, g, b)]
    peak = max(lin)
    return unreal.LinearColor(lin[0] / peak, lin[1] / peak, lin[2] / peak, 1.0)


def hexcolour(h):
    v = [int(h.lstrip("#")[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [c ** 2.2 for c in v]
    return unreal.LinearColor(lin[0], lin[1], lin[2], 1.0)


def light(kind, label, loc, rot=(0, 0, 0), colour=None, intensity=1000.0, radius=1000.0, shadow=False, cone=60.0,
          size=(100, 100), draw=3500.0, fade=800.0):
    cls = {"spot": unreal.SpotLight, "point": unreal.PointLight, "rect": unreal.RectLight}[kind]
    actor = B.spawn_class(cls, label, FOLDER + "/Light", loc, rot)
    comp = actor.get_component_by_class({"spot": unreal.SpotLightComponent, "point": unreal.PointLightComponent,
                                         "rect": unreal.RectLightComponent}[kind])
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    B.setp(comp, "intensity", intensity)
    B.setp(comp, "light_color", (colour or kelvin(4000)).to_rgbe() if False else unreal.Color(
        int(255 * (colour or kelvin(4000)).r ** (1 / 2.2)), int(255 * (colour or kelvin(4000)).g ** (1 / 2.2)),
        int(255 * (colour or kelvin(4000)).b ** (1 / 2.2)), 255))
    B.setp(comp, "cast_shadows", bool(shadow))
    B.setp(comp, "max_draw_distance", draw if not shadow else min(draw, 2500.0))
    B.setp(comp, "max_distance_fade_range", fade)
    if kind in ("spot", "point"):
        B.setp(comp, "attenuation_radius", radius)
        B.setp(comp, "source_radius", 6.0)
    if kind == "spot":
        B.setp(comp, "outer_cone_angle", cone)
        B.setp(comp, "inner_cone_angle", cone * 0.6)
    if kind == "rect":
        B.setp(comp, "attenuation_radius", radius)
        B.setp(comp, "source_width", size[0])
        B.setp(comp, "source_height", size[1])
        B.setp(comp, "barn_door_angle", 88.0)
    LIGHT_COUNT["n"] += 1
    LIGHT_COUNT["shadowed"] += 1 if shadow else 0
    return actor


DOWN = (-90, 0, 0)


def lights_unit(lv, pl):
    def place():
        # LED street lamps: a spot under each cobra head, the four Canal and two Mott lamps nearest the doc's x/z shadowed.
        lamps = [e for e in pl["instances"] if e["mesh"] == "SM_Furn_StreetLamp"]
        shadowed_x = (-3000, -600, 1800, 3800)
        for k, e in enumerate(lamps):
            x, y, _ = e["location_cm"]
            toward = -1.0 if y > 0 else 1.0                                   # the arm reaches over the roadway (y = 0)
            if abs(y) < 1500 and False:
                toward = 0
            sh = any(abs(x - sx) < 400 for sx in shadowed_x) and abs(y) > 1500 or (abs(x - 1300) < 700 and k % 3 == 0)
            light("spot", "Lamp_%d" % k, (x, y + toward * 220, 760), DOWN, kelvin(4000), 3500.0, 1500.0,
                  shadow=sh and LIGHT_COUNT["shadowed"] < 6, cone=70.0)
        # Sign wash: the largest lit night-on signs, a point light a metre out of the face in the sign's colour.
        signs = [s for s in lv["signage"]["placements"] if s.get("lit") and s.get("night") == "on" and s.get("colour")
                 and s["kind"] in ("band", "blade", "neon", "board", "letters", "arch", "street", "kiosk")]
        signs.sort(key=lambda s: -(s["ue"].get("width", 0) * s["ue"].get("height", 0)))
        used = []
        for s in signs:
            p = s["ue"]["pos"]
            if any(math.hypot(p["X"] - q[0], p["Y"] - q[1]) < 700 for q in used):
                continue
            used.append((p["X"], p["Y"]))
            n = s["web"].get("normal", {"x": 0, "y": 0, "z": 1})
            nx, ny = n["x"], n["z"]
            light("point", "Sign_" + s["id"].replace(".", "_"), (p["X"] + nx * 130, p["Y"] + ny * 130, p["Z"]), (0, 0, 0),
                  hexcolour(s["colour"]), 900.0, 650.0, draw=3000.0, fade=600.0)
            if len(used) >= 13:
                break
        # Interiors and the rest, by place.
        white = kelvin(5000)
        warm = kelvin(3200)
        for k, (x, y) in enumerate(((-2000, -800), (-600, -800), (-2000, 250), (-600, 250))):
            light("rect", "Market_%d" % k, (x, y, 500), DOWN, white, 2200.0, 1200.0, size=(120, 60), draw=3500.0)
        light("spot", "MarketBulb_Cross", (-1300, -400, 505), DOWN, kelvin(2900), 7000.0, 1200.0, shadow=True, cone=85.0)
        light("spot", "MarketBulb_Cold", (-300, 600, 505), DOWN, kelvin(6500), 6000.0, 1200.0, shadow=True, cone=85.0)
        for k, (x, y) in enumerate(((300, -900), (300, 100))):
            light("rect", "Bakery_%d" % k, (x, y, 330), DOWN, warm, 4000.0, 900.0, size=(100, 50))
        for k, x in enumerate((2200, 2900, 3500, 4100)):
            light("rect", "Arcade_%d" % k, (x, -600, 380), DOWN, kelvin(4500), 4500.0, 1000.0, size=(120, 50))
        light("point", "Workshop", (3900, -700, 250), (0, 0, 0), hexcolour("#6fa0ff"), 1500.0, 700.0)
        for k, (x, y) in enumerate(((-3500, 300), (-3500, 1800), (-3500, 2900), (-1000, 2300))):
            light("point", "Bulkhead_%d" % k, (x, y, 330), (0, 0, 0), kelvin(3000), 1500.0, 800.0)
        light("point", "Kitchen_Roof", (200, 1100, 760), (0, 0, 0), kelvin(2800), 1500.0, 700.0)
        light("spot", "Square_Pavilion", (3100, 1000, 620), DOWN, warm, 9000.0, 1000.0, shadow=True, cone=80.0)
        for k, (x, y) in enumerate(((3000, 2500), (3700, 2500), (4200, 2500))):
            light("point", "Banquet_%d" % k, (x, y, 360), (0, 0, 0), warm, 3000.0, 1000.0)
        light("spot", "Banquet_Stage", (3500, 3000, 380), (-70, 90, 0), kelvin(3400), 7000.0, 900.0, shadow=True, cone=70.0)
        for k, (x, y) in enumerate(((2100, 2300), (2300, 2800))):
            light("point", "DubRoom_%d" % k, (x, y, 300), (0, 0, 0), kelvin(3800), 1800.0, 600.0)
        light("rect", "BanquetKitchen", (3500, 2200, 330), DOWN, white, 3000.0, 800.0, size=(100, 50))
        return "%d lights, %d shadowed" % (LIGHT_COUNT["n"], LIGHT_COUNT["shadowed"])
    return place


def rig_unit(lv):
    atmos = B.game_data("atmos")["rigs"]["night"]

    def place():
        start = lv["playerStart"]["ue"]
        B.spawn_class(unreal.PlayerStart, "PlayerStart", FOLDER, (start["pos"]["X"], start["pos"]["Y"], start["pos"]["Z"] + 92.0),
                      (0, start["yaw"], 0))
        # The city glow: one movable directional light, no shadow.
        sun = B.spawn_class(unreal.DirectionalLight, "CityGlow", FOLDER + "/Light", (0, 0, 3000), (-55, -140, 0))
        c = sun.get_component_by_class(unreal.DirectionalLightComponent)
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        B.setp(c, "intensity", 0.15)
        B.setp(c, "light_color", unreal.Color(142, 166, 214, 255))
        B.setp(c, "cast_shadows", False)
        B.setp(c, "atmosphere_sun_light", False)
        sky = B.spawn_class(unreal.SkyLight, "SkyLight", FOLDER + "/Light", (0, 0, 1000))
        s = sky.get_component_by_class(unreal.SkyLightComponent)
        s.set_mobility(unreal.ComponentMobility.MOVABLE)
        B.setp(s, "real_time_capture", False)
        B.setp(s, "intensity", 0.2)
        B.setp(s, "lower_hemisphere_is_black", False)
        B.setp(s, "lower_hemisphere_color", unreal.LinearColor(0.02, 0.016, 0.014, 1.0))
        B.setp(s, "light_color", unreal.Color(120, 130, 170, 255))
        target = [p for p in atmos["fog"]["opacityAt"] if p["ue"] == 9200][0]["opacity"]
        density = -math.log(1.0 - target) / (0.001 * 9200)
        fog = B.spawn_class(unreal.ExponentialHeightFog, "HeightFog", FOLDER + "/Light", (0, 0, 0))
        f = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
        B.setp(f, "fog_density", density)
        B.setp(f, "fog_height_falloff", 0.05)
        B.setp(f, "fog_inscattering_luminance", unreal.LinearColor(0.045, 0.026, 0.02, 1.0))
        B.setp(f, "enable_volumetric_fog", False)
        vol = B.spawn_class(unreal.PostProcessVolume, "PostProcess", FOLDER + "/Light")
        vol.set_editor_property("unbound", True)
        st = vol.get_editor_property("settings")
        values = (
            ("dynamic_global_illumination_method", unreal.DynamicGlobalIlluminationMethod.LUMEN),
            ("reflection_method", unreal.ReflectionMethod.LUMEN),
            ("auto_exposure_method", unreal.AutoExposureMethod.AEM_HISTOGRAM),
            ("auto_exposure_min_brightness", 5.0), ("auto_exposure_max_brightness", 7.5),
            ("auto_exposure_speed_up", 6.0), ("auto_exposure_speed_down", 6.0),
            ("bloom_intensity", 0.35), ("bloom_threshold", -1.0), ("vignette_intensity", 0.15),
            ("white_temp", 5600.0),
            ("local_exposure_highlight_contrast_scale", 0.6), ("local_exposure_shadow_contrast_scale", 0.5),
            ("lumen_final_gather_quality", 1.0), ("lumen_scene_detail", 1.5),
        )
        for name, value in values:
            try:
                st.set_editor_property("override_" + name, True)
                st.set_editor_property(name, value)
            except Exception as error:   # noqa: BLE001
                unreal.log_warning("build_canal: post %s: %s" % (name, error))
        vol.set_editor_property("settings", st)
        return "player start, glow, sky light, fog %.4f, post" % density
    return place


def level_units(force):
    lv, pl = level(), placements()
    yield "open map", open_map
    for u in ground_units(lv):
        yield u
    for u in mass_units(lv):
        yield u
    for u in art_units(pl):
        yield u
    yield "lights", lights_unit(lv, pl)
    yield "rig", rig_unit(lv)

    def save():
        saved = LEVELS.save_current_level()
        return "saved=%s, %d actors" % (saved, len([a for a in ACTORS.get_all_level_actors() if B.TAG in [str(t) for t in a.tags]]))
    yield "save", save


def start(steps="all", force=False):
    B.STEPS = dict(B.STEPS)
    B.STEPS["meshes"] = mesh_units
    B.STEPS["paints"] = paint_units
    B.STEPS["signs"] = sign_units
    B.STEPS["wet"] = wet_units
    B.STEPS["canal"] = level_units
    names = "textures,materials,meshes,paints,signs,wet,canal" if steps == "all" else steps
    return B.start(names, force=force)
