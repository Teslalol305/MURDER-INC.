"""Build the block: import the Blender art and assemble /Game/Maps/L_Block from Content/Data/level.json and atmos.json.

Generated content (the imported assets and the map) is not committed: this script regenerates all of it.
Run it inside the running headless editor (tools/box/block.sh does this through the editor's MCP server):

    import build_block; build_block.start("all")            # or "textures,materials,meshes,level", force=True

start() returns at once. The work runs in editor ticks, one small unit per tick, so no MCP call ever waits on it.
Progress goes to <project>/Saved/BuildBlock/status.txt; its last line is "DONE ..." or "FAILED ...".

Inputs
  /project/ue/art-in (env MI_ART_IN): what tools/box/receive-art.sh unpacked: manifest.json, glb/SM_*.glb,
      textures/<Set>/T_<Set>_{BC,N,ORM}.* (art/blender/README.md has the conventions)
  Content/Data/level.json, atmos.json: the web game's block and its day rig

Steps
  textures   /Game/Art/Textures/<Set>/T_<Set>_*: BC sRGB; N linear normal map with the green channel flipped
             (the sets are OpenGL, +Y up; Unreal wants DirectX); ORM linear masks
  materials  /Game/Art/Materials/M_MI_Surface (master) and one instance per manifest slot (MI_<Surface>_<Variant>,
             MI_<Asset> for a slot M_<Asset>), plus the grey-box and ground instances (MI_Grey_*, MI_Ground_*)
  meshes     /Game/Art/Meshes/SM_*: Interchange glTF, Nanite on, no glTF materials; slots assigned by name;
             bounds checked against the manifest (proves the axes and the scale)
  level      /Game/Maps/L_Block: street kit tiled along the avenue, El modules at the data's bents and columns,
             every movement-blocking static collider as grey-box massing, ground slabs, player start, day rig

Units are Unreal's: centimetres, Z up, X east, Y south. Every spawned actor carries the tag MIBlock.
"""
import json
import math
import os
import random
import time
import traceback

import unreal

ART_IN = os.environ.get("MI_ART_IN", "/project/ue/art-in")
ROOT = "/Game/Art"
TEX_DIR, MAT_DIR, MESH_DIR = ROOT + "/Textures", ROOT + "/Materials", ROOT + "/Meshes"
MAP_PATH = "/Game/Maps/L_Block"
MASTER = MAT_DIR + "/M_MI_Surface"
TAG = "MIBlock"
CUBE = "/Engine/BasicShapes/Cube.Cube"          # 100 cm, centred on its origin

# Art constants that are not game data (art/blender/README.md, "el" family; ART_BIBLE.md 2.1, 2.3, 2.4;
# docs/unreal/spec/06-look-fx.md 4.5). The day rig's own numbers come from atmos.json.
EL_LAMP_MOUNT_Z = 602.0          # top of the lamp canopy under the deck (README: lamps at (x + 5, +-2.1, 6.02))
LUX_PER_GAME_LUX = 24400.0       # spec 4.5: the web sun (5 game lux x colour luminance 0.819) anchored at 100,000 lx
DAY_EV100 = (12.9, 14.2)         # art bible 2.3: auto exposure clamped; open sun near 14.2, under the El about 13.2,
                                 # the lower clamp is the readability dial (spec 4.5 puts the web's fixed 1.1 at 13.4)
SUN_SOURCE_ANGLE = 0.5357        # art bible 2.4
STREET_EXTENT_CM = 7000          # street kit runs this far east and west of the centre (the bounds end at 4,600)
GREY_SURFACE = {                 # collider surface -> (grey-box instance, texture set, tint)
    "brick": ("MI_Grey_Brick", "TS_Brick_ScanRedCommon", (1.0, 1.0, 1.0)),       # roofs: ROOF_SET
    "concrete": ("MI_Grey_Concrete", "TS_Concrete_ScanWeathered", (1.0, 1.0, 1.0)),
    "metal": ("MI_Grey_Metal", "TS_Concrete_ScanWeathered", (0.42, 0.45, 0.5)),
    "wood": ("MI_Grey_Wood", "TS_Concrete_ScanWeathered", (0.8, 0.58, 0.4)),
    "car": ("MI_Grey_Car", "TS_Concrete_ScanWeathered", (0.55, 0.55, 0.6)),
    "glass": ("MI_Grey_Glass", "TS_Concrete_ScanWeathered", (0.28, 0.32, 0.36)),
    "other": ("MI_Grey_Other", "TS_Concrete_ScanWeathered", (0.6, 0.55, 0.5)),
}
ROOF_SET = "TS_Concrete_ScanWeathered"   # upward faces of the brick massing
GROUND_SURFACE = {               # level.json ground surface -> (instance, texture set, tint)
    "asphalt": ("MI_Ground_Asphalt", "TS_Asphalt_ScanWorn", (1.0, 1.0, 1.0)),
    "concrete": ("MI_Ground_Concrete", "TS_Concrete_ScanRough", (1.0, 1.0, 1.0)),
    "dirt": ("MI_Ground_Dirt", "TS_Concrete_ScanRough", (0.62, 0.5, 0.38)),
    "far": ("MI_Ground_Far", "TS_Asphalt_ScanWorn", (0.8, 0.8, 0.8)),
}
SKIP_COLLIDER_TAGS = {"el-column", "el-girder", "el-deck", "sidewalk"}   # drawn by the El and street meshes

LIB = unreal.MaterialEditingLibrary
ASSETS = unreal.EditorAssetLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


# --------------------------------------------------------------------------------------------------------- data

def project_dir(sub):
    return os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()), sub)


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def manifest():
    return load_json(os.path.join(ART_IN, "manifest.json"))


def game_data(name):
    return load_json(os.path.join(project_dir("Content"), "Data", name + ".json"))


def art_assets(man):
    """Manifest assets whose GLB arrived."""
    return {name: asset for name, asset in sorted(man["assets"].items())
            if asset.get("glb") and os.path.exists(os.path.join(ART_IN, asset["glb"]))}


def set_tile_m(man, set_name):
    """Real size of one texture repeat in metres (manifest texture_sets, else any slot that uses the set)."""
    info = man.get("texture_sets", {}).get(set_name, {})
    if info.get("tile_m"):
        return float(info["tile_m"][0])
    for asset in man["assets"].values():
        for slot in asset.get("material_slots", []):
            if slot.get("set") == set_name and slot.get("tile_m"):
                return float(slot["tile_m"][0])
    return 2.0


def texture_path(set_name, kind):
    return "%s/%s/T_%s_%s" % (TEX_DIR, set_name, set_name, kind)


def has_set(set_name):
    return ASSETS.does_asset_exist(texture_path(set_name, "BC"))


# ----------------------------------------------------------------------------------------------------- textures

def texture_units(force):
    root = os.path.join(ART_IN, "textures")
    for set_name in sorted(os.listdir(root)):
        for file_name in sorted(os.listdir(os.path.join(root, set_name))):
            stem, ext = os.path.splitext(file_name)
            kind = stem.rsplit("_", 1)[-1]
            if ext.lower() not in (".jpg", ".jpeg", ".png") or kind not in ("BC", "N", "ORM"):
                continue
            yield "texture " + stem, (lambda s=set_name, f=os.path.join(root, set_name, file_name), k=kind:
                                       import_texture(s, f, k, force))


def import_texture(set_name, file_path, kind, force):
    path = texture_path(set_name, kind)
    if ASSETS.does_asset_exist(path) and not force:
        return "exists"
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", file_path)
    task.set_editor_property("destination_path", path.rsplit("/", 1)[0])
    task.set_editor_property("destination_name", path.rsplit("/", 1)[1])
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture = unreal.load_asset(path)
    if texture is None:
        raise RuntimeError("texture import produced nothing: " + file_path)
    if kind == "N":
        texture.set_editor_property("srgb", False)
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        texture.set_editor_property("flip_green_channel", True)          # OpenGL (+Y up) -> Unreal (DirectX)
        texture.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP)
    elif kind == "ORM":
        texture.set_editor_property("srgb", False)
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    else:
        texture.set_editor_property("srgb", True)
    ASSETS.save_asset(path, only_if_is_dirty=False)
    return "imported"


# ---------------------------------------------------------------------------------------------------- materials

# One HLSL node does all the wear-mask work (ART_BIBLE.md 3.3). Inputs arrive as the node's named inputs.
WEAR_HLSL = r"""
// Vector parameters and the vertex colour node give float3 on their main output: alpha and w come separately.
// Vertex colours are stored sRGB-encoded (StaticMeshBuilder: ToFColor(true)) and read back raw: decode RGB.
// Alpha is stored linearly.
float3 m = pow(saturate(VC.rgb), 2.2) * Amount.x;
float  a = saturate(VA) * Amount.x;
// Value noise at two scales breaks up the soft, low-frequency masks into crisp, irregular edges.
float n[3];
float3 scales = float3(1.0 / 6.0, 1.0 / 23.0, 1.0);
for (int o = 0; o < 3; o++)
{
    float3 P = (o < 2) ? WP * scales[o] + o * 17.31 : WP * float3(1.0 / 22.0, 1.0 / 22.0, 1.0 / 260.0);
    float3 I = floor(P);
    float3 F = frac(P);
    F = F * F * (3.0 - 2.0 * F);
    float v[8];
    for (int c = 0; c < 8; c++)
    {
        float3 corner = I + float3(c & 1, (c >> 1) & 1, (c >> 2) & 1);
        v[c] = frac(sin(dot(corner, float3(127.1, 311.7, 74.7))) * 43758.5453);
    }
    n[o] = lerp(lerp(lerp(v[0], v[1], F.x), lerp(v[2], v[3], F.x), F.y),
                lerp(lerp(v[4], v[5], F.x), lerp(v[6], v[7], F.x), F.y), F.z);
}
float breakup = 0.65 * n[0] + 0.35 * n[1];
float breakup2 = 0.65 * (1.0 - n[0]) + 0.35 * n[1];
float dirt  = saturate((m.r + (breakup  - 0.5) * 0.7 - 0.5) * 3.0 + 0.5);
float edge  = saturate((m.g + (breakup2 - 0.5) * 0.7 - 0.5) * 3.0 + 0.5);
float leak  = saturate((m.b * (0.35 + 1.3 * n[2]) - 0.25) * 2.0);
float splash = saturate((a + (breakup - 0.5) * 0.7 - 0.5) * 3.0 + 0.5) * Modes.y;

float3 bc = BC * Tint;
float rough = ORM.g;
float metal = ORM.b;
float ao = ORM.r;
// The second set shows where G wears through (paint to rust, paint to asphalt) and, on grey-box massing with
// Amount.y = 1, on every upward face (a brick block gets a concrete roof).
float set2 = (Modes.x > 0.5) ? edge : 0.0;
set2 = max(set2, Amount.y * step(0.7, NW.z));
bc = lerp(bc, BC2, set2);
rough = lerp(rough, ORM2.g, set2);
metal = lerp(metal, ORM2.b, set2);
ao = lerp(ao, ORM2.r, set2);
if (Modes.x <= 0.5)         // G: paler, smoother worn edges and traffic polish
{
    bc = lerp(bc, saturate(bc * 1.4 + 0.02), edge * 0.7);
    rough = lerp(rough, rough * 0.8, edge);
}
bc = lerp(bc, DirtColor, dirt * 0.8);
rough = lerp(rough, 0.9, dirt * 0.6);
ao *= 1.0 - 0.3 * dirt;
bc = lerp(bc, LeakColor, leak * 0.7);
bc = lerp(bc, SplashColor, splash * 0.55);
rough = lerp(rough, 0.95, splash);
float silt = a * Modes.z;   // ground: a dry silt stain where water collects
bc *= 1.0 - 0.25 * silt;
float wet = saturate(a * Wetness);
bc *= lerp(1.0, 0.55, wet);
rough = lerp(rough, 0.08, wet);
Rough = saturate(rough);
Metal = saturate(metal);
AO = saturate(ao);
Edge = set2;
return bc;
"""

# Box projection in world space for the grey-box cubes and ground slabs: the dominant axis of the normal picks the
# plane, so a texture keeps its real size on any box, whatever its scale.
BOXUV_HLSL = r"""
float3 an = abs(N);
float3 p = WP / TileCm;
float2 uv = (an.z >= an.x && an.z >= an.y) ? p.xy : ((an.x >= an.y) ? p.yz : p.xz);
return float2(uv.x, -uv.y);
"""


def expr(material, cls, x, y, **props):
    node = LIB.create_material_expression(material, cls, x, y)
    for key, value in props.items():
        node.set_editor_property(key, value)
    return node


def world_position(material, x, y):
    """Absolute world position as plain floats (the HLSL nodes do not take large-world-coordinate inputs)."""
    position = expr(material, unreal.MaterialExpressionWorldPosition, x, y)
    if hasattr(unreal, "MaterialExpressionTruncateLWC"):
        truncate = expr(material, unreal.MaterialExpressionTruncateLWC, x + 160, y)
        LIB.connect_material_expressions(position, "", truncate, "")
        return truncate
    return position


def make_struct(cls, **props):
    """Unreal structs take no keyword arguments in their constructor here: set each property."""
    value = cls()
    for key, item in props.items():
        value.set_editor_property(key, item)
    return value


def custom(material, x, y, code, inputs, output_type, extra_outputs=()):
    node = expr(material, unreal.MaterialExpressionCustom, x, y)
    node.set_editor_property("code", code)
    node.set_editor_property("output_type", output_type)
    node.set_editor_property("inputs", [make_struct(unreal.CustomInput, input_name=name) for name in inputs])
    if extra_outputs:
        node.set_editor_property("additional_outputs", [
            make_struct(unreal.CustomOutput, output_name=name,
                        output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT1) for name in extra_outputs])
    return node


def build_master(defaults, force):
    """M_MI_Surface: tiling texture set (+ optional second set on G), tint, Wear vertex-colour masks."""
    # Rebuilt in place, never deleted: deleting a parent orphans its instances, and every orphan then compiles
    # the default material synchronously on the game thread (minutes).
    if ASSETS.does_asset_exist(MASTER):
        if not force:
            return "exists"
        material = unreal.load_asset(MASTER)
        LIB.delete_all_material_expressions(material)
    else:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        material = tools.create_asset("M_MI_Surface", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())

    # UVs: mesh UV0 (already in repeats of the set's tile) x UVScale, or the world box projection.
    uv0 = expr(material, unreal.MaterialExpressionTextureCoordinate, -2200, 0)
    uv_scale = expr(material, unreal.MaterialExpressionScalarParameter, -2200, 120, parameter_name="UVScale",
                    default_value=1.0)
    uv_mul = expr(material, unreal.MaterialExpressionMultiply, -2000, 40)
    LIB.connect_material_expressions(uv0, "", uv_mul, "A")
    LIB.connect_material_expressions(uv_scale, "", uv_mul, "B")
    wp = world_position(material, -2400, 300)
    normal_ws = expr(material, unreal.MaterialExpressionVertexNormalWS, -2200, 420)
    tile_cm = expr(material, unreal.MaterialExpressionScalarParameter, -2200, 520, parameter_name="TileCm",
                   default_value=200.0)
    box_uv = custom(material, -2000, 300, BOXUV_HLSL, ["WP", "N", "TileCm"],
                    unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    LIB.connect_material_expressions(wp, "", box_uv, "WP")
    LIB.connect_material_expressions(normal_ws, "", box_uv, "N")
    LIB.connect_material_expressions(tile_cm, "", box_uv, "TileCm")
    uv_switch = expr(material, unreal.MaterialExpressionStaticSwitchParameter, -1800, 100,
                     parameter_name="WorldBoxUV", default_value=False)
    LIB.connect_material_expressions(box_uv, "", uv_switch, "True")
    LIB.connect_material_expressions(uv_mul, "", uv_switch, "False")

    samplers = {}
    rows = (("BC", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR), ("N", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL),
            ("ORM", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS))
    for column, suffix in enumerate(("", "2")):
        for row, (kind, sampler) in enumerate(rows):
            node = expr(material, unreal.MaterialExpressionTextureSampleParameter2D, -1500 + column * 300,
                        -400 + row * 260 + column * 800, parameter_name=kind + suffix, sampler_type=sampler,
                        texture=defaults[kind])
            LIB.connect_material_expressions(uv_switch, "", node, "UVs")
            samplers[kind + suffix] = node

    def vector(name, value, x, y):
        return expr(material, unreal.MaterialExpressionVectorParameter, x, y, parameter_name=name,
                    default_value=unreal.LinearColor(*value))

    tint = vector("Tint", (1, 1, 1, 1), -900, 900)
    dirt = vector("DirtColor", (0.04, 0.036, 0.032, 1), -900, 1000)      # street grime #3B3632
    leak = vector("LeakColor", (0.2, 0.06, 0.02, 1), -900, 1100)         # rust #7A4428
    splash = vector("SplashColor", (0.22, 0.2, 0.17, 1), -900, 1200)     # dust #8A8172
    modes = vector("Modes", (0, 1, 0, 0), -900, 1300)       # x blend set on G, y splash on A, z silt on A, w wetness
    amount = vector("WearAmount", (1, 0, 0, 0), -900, 1400)  # x: 0 switches the masks off (meshes without Wear);
    #                                                          y: 1 puts the second set on upward faces (roofs)
    vertex_colour = expr(material, unreal.MaterialExpressionVertexColor, -900, 1500)
    wear = custom(material, -500, 300, WEAR_HLSL,
                  ["BC", "ORM", "BC2", "ORM2", "VC", "VA", "WP", "Tint", "DirtColor", "LeakColor", "SplashColor",
                   "Modes", "Wetness", "Amount", "NW"],
                  unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["Rough", "Metal", "AO", "Edge"])
    for name, source, output in (("BC", samplers["BC"], "RGB"), ("ORM", samplers["ORM"], "RGB"),
                                 ("BC2", samplers["BC2"], "RGB"), ("ORM2", samplers["ORM2"], "RGB"),
                                 ("VC", vertex_colour, ""), ("VA", vertex_colour, "A"), ("WP", wp, ""),
                                 ("Tint", tint, ""), ("Wetness", modes, "A"),
                                 ("DirtColor", dirt, ""), ("LeakColor", leak, ""), ("SplashColor", splash, ""),
                                 ("Modes", modes, ""), ("Amount", amount, ""), ("NW", normal_ws, "")):
        if not LIB.connect_material_expressions(source, output, wear, name):
            raise RuntimeError("cannot connect %s output '%s' to the wear node" % (name, output))

    normal_blend = expr(material, unreal.MaterialExpressionLinearInterpolate, -200, 600)
    LIB.connect_material_expressions(samplers["N"], "RGB", normal_blend, "A")
    LIB.connect_material_expressions(samplers["N2"], "RGB", normal_blend, "B")
    LIB.connect_material_expressions(wear, "Edge", normal_blend, "Alpha")

    LIB.connect_material_property(wear, "", unreal.MaterialProperty.MP_BASE_COLOR)
    LIB.connect_material_property(wear, "Rough", unreal.MaterialProperty.MP_ROUGHNESS)
    LIB.connect_material_property(wear, "Metal", unreal.MaterialProperty.MP_METALLIC)
    LIB.connect_material_property(wear, "AO", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    LIB.connect_material_property(normal_blend, "", unreal.MaterialProperty.MP_NORMAL)
    LIB.recompile_material(material)
    ASSETS.save_asset(MASTER, only_if_is_dirty=False)
    return "created"


def make_instance(name, set_name, tint=(1, 1, 1), blend_set=None, alpha_means=None, world_tile_m=None,
                  wear=1.0, force=False, roof_set=None):
    path = "%s/%s" % (MAT_DIR, name)
    if ASSETS.does_asset_exist(path):
        if not force:
            return "exists"
        instance = unreal.load_asset(path)          # updated in place (meshes keep their references)
    else:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        instance = tools.create_asset(name, MAT_DIR, unreal.MaterialInstanceConstant,
                                      unreal.MaterialInstanceConstantFactoryNew())
    LIB.set_material_instance_parent(instance, unreal.load_asset(MASTER))
    for kind in ("BC", "N", "ORM"):
        texture = unreal.load_asset(texture_path(set_name, kind))
        LIB.set_material_instance_texture_parameter_value(instance, kind, texture)
        other = blend_set or roof_set
        second = unreal.load_asset(texture_path(other, kind)) if other and has_set(other) else texture
        LIB.set_material_instance_texture_parameter_value(instance, kind + "2", second)
    LIB.set_material_instance_vector_parameter_value(instance, "Tint", unreal.LinearColor(tint[0], tint[1], tint[2], 1))
    modes = (1.0 if blend_set and has_set(blend_set) else 0.0,
             1.0 if alpha_means == "splash" else 0.0,
             1.0 if alpha_means == "wet" else 0.0,
             0.0)                                    # day: dry street (wetness 0)
    LIB.set_material_instance_vector_parameter_value(instance, "Modes", unreal.LinearColor(*modes))
    LIB.set_material_instance_vector_parameter_value(instance, "WearAmount",
                                                     unreal.LinearColor(wear, 1.0 if roof_set else 0.0, 0, 0))
    if world_tile_m:
        LIB.set_material_instance_static_switch_parameter_value(instance, "WorldBoxUV", True)
        LIB.set_material_instance_scalar_parameter_value(instance, "TileCm", world_tile_m * 100.0)
    LIB.update_material_instance(instance)
    ASSETS.save_asset(path, only_if_is_dirty=False)
    return "created"


def slot_instance_name(slot_name):
    """MI_<Surface>_<Variant> slots keep their name; M_<Asset> (a unique set) becomes MI_<Asset>."""
    return slot_name if slot_name.startswith("MI_") else "MI_" + slot_name[2:] if slot_name.startswith("M_") \
        else "MI_" + slot_name


def material_units(force):
    man = manifest()
    defaults_set = "TS_Concrete_ScanFormed"
    defaults = {kind: unreal.load_asset(texture_path(defaults_set, kind)) for kind in ("BC", "N", "ORM")}
    yield "master material", lambda: build_master(defaults, force)
    seen = set()
    for asset in art_assets(man).values():
        for slot in asset.get("material_slots", []):
            name = slot_instance_name(slot["slot"])
            if name in seen:
                continue
            seen.add(name)
            set_name = slot["set"] if has_set(slot["set"]) else defaults_set    # stand-in for a missing set
            tint = slot.get("tint") or ((1.0, 0.75, 0.45) if set_name != slot["set"] else (1, 1, 1))
            wear = 0.0 if slot.get("workflow") == "unique" else 1.0           # unique sets carry their wear baked
            yield "instance " + name, (lambda n=name, s=set_name, t=tint, b=slot.get("blend_set_G"),
                                       a=slot.get("alpha_means"), w=wear:
                                       make_instance(n, s, t, b, a, None, w, force))
    for name, set_name, tint in list(GREY_SURFACE.values()) + list(GROUND_SURFACE.values()):
        if name in seen:
            continue
        seen.add(name)
        roof = ROOF_SET if name == GREY_SURFACE["brick"][0] else None
        yield "instance " + name, (lambda n=name, s=set_name, t=tint, r=roof:
                                   make_instance(n, s, t, None, None, set_tile_m(man, s), 0.0, force, r))


# ------------------------------------------------------------------------------------------------------- meshes

def mesh_units(force):
    man = manifest()
    for name, asset in art_assets(man).items():
        yield "mesh " + name, (lambda n=name, a=asset: import_mesh(n, a, force))


def import_mesh(name, asset, force):
    path = "%s/%s" % (MESH_DIR, name)
    if not ASSETS.does_asset_exist(path) or force:
        pipeline = unreal.InterchangeGenericAssetsPipeline()
        pipeline.material_pipeline.set_editor_property("import_materials", False)
        pipeline.material_pipeline.texture_pipeline.set_editor_property("import_textures", False)
        pipeline.mesh_pipeline.set_editor_property("build_nanite", True)
        pipeline.mesh_pipeline.set_editor_property("combine_static_meshes_behavior",
                                                   unreal.InterchangeCombineStaticMeshesBehavior.ALL)
        pipeline.mesh_pipeline.set_editor_property("import_skeletal_meshes", False)
        pipeline.set_editor_property("asset_name", name)
        parameters = unreal.ImportAssetParameters()
        parameters.set_editor_property("is_automated", True)
        parameters.set_editor_property("replace_existing", True)
        parameters.set_editor_property("override_pipelines", [unreal.SoftObjectPath(pipeline.get_path_name())])
        manager = unreal.InterchangeManager.get_interchange_manager_scripted()
        source = unreal.InterchangeManager.create_source_data(os.path.join(ART_IN, asset["glb"]))
        result = manager.import_asset(MESH_DIR, source, parameters)
        imported = result[1] if isinstance(result, tuple) else []
        meshes = [o for o in (imported or []) if isinstance(o, unreal.StaticMesh)]
        if not ASSETS.does_asset_exist(path):
            if len(meshes) == 1:
                ASSETS.rename_asset(meshes[0].get_path_name().split(".")[0], path)
            else:
                raise RuntimeError("import of %s made %s" % (asset["glb"], [o.get_path_name() for o in imported or []]))
    mesh = unreal.load_asset(path)
    nanite = mesh.get_editor_property("nanite_settings")
    if not nanite.enabled:
        nanite.enabled = True
        mesh.set_editor_property("nanite_settings", nanite)
    # Material slots by name.
    report = []
    static_materials = mesh.get_editor_property("static_materials")
    for index, entry in enumerate(static_materials):
        slot = str(entry.get_editor_property("material_slot_name"))
        mi_path = "%s/%s" % (MAT_DIR, slot_instance_name(slot))
        if ASSETS.does_asset_exist(mi_path):
            mesh.set_material(index, unreal.load_asset(mi_path))
        else:
            report.append("no instance for slot " + slot)
    ASSETS.save_asset(path, only_if_is_dirty=False)
    # Axes and scale: the imported bounds must equal the manifest's Unreal bounds (Blender (x, -y, z) x 100).
    box = mesh.get_bounding_box()
    want = asset.get("bounds_unreal_cm") or {}
    got_min = (box.min.x, box.min.y, box.min.z)
    got_max = (box.max.x, box.max.y, box.max.z)
    error = 0.0
    if want:
        error = max(abs(a - b) for a, b in zip(got_min + got_max, tuple(want["min"]) + tuple(want["max"])))
    report.append("bounds min (%.1f %.1f %.1f) max (%.1f %.1f %.1f) vs manifest: max error %.1f cm%s" % (
        got_min + got_max + (error, " MISMATCH" if error > 2.0 else "")))
    report.append("slots " + ",".join(str(e.get_editor_property("material_slot_name")) for e in static_materials))
    return "; ".join(report)


# -------------------------------------------------------------------------------------------------------- level

def rotator(pitch=0.0, yaw=0.0, roll=0.0):
    return unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw)


def tag(actor, label, folder):
    actor.set_actor_label(label)
    actor.tags = [TAG]
    actor.set_folder_path(folder)
    return actor


def spawn_mesh(mesh_path, label, folder, location, yaw=0.0, scale=None, material=None):
    mesh = unreal.load_asset(mesh_path)
    actor = ACTORS.spawn_actor_from_object(mesh, unreal.Vector(*location), rotator(yaw=yaw))
    if scale:
        actor.set_actor_scale3d(unreal.Vector(*scale))
    if material:
        actor.static_mesh_component.set_material(0, material)
    return tag(actor, label, folder)


def spawn_box(label, folder, center, extent, material):
    """A grey-box cube from a centre and a half-extent in centimetres."""
    return spawn_mesh(CUBE, label, folder, center, 0.0,
                      (max(extent[0], 0.5) / 50.0, max(extent[1], 0.5) / 50.0, max(extent[2], 0.5) / 50.0), material)


def spawn_class(cls, label, folder, location=(0, 0, 0), rot=(0, 0, 0)):
    actor = ACTORS.spawn_actor_from_class(cls, unreal.Vector(*location), rotator(*rot))
    return tag(actor, label, folder)


def open_block_map():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    current = world.get_path_name().split(".")[0] if world else ""
    if current == MAP_PATH or ASSETS.does_asset_exist(MAP_PATH):
        if current != MAP_PATH:
            LEVELS.load_level(MAP_PATH)
        doomed = [a for a in ACTORS.get_all_level_actors() if TAG in [str(t) for t in a.tags]]
        for actor in doomed:
            ACTORS.destroy_actor(actor)
        return "loaded, removed %d old actors" % len(doomed)
    LEVELS.new_level(MAP_PATH)
    return "new level"


def street_units(level):
    rng = random.Random(1994)
    extent = STREET_EXTENT_CM
    units = []
    for k, x in enumerate(range(-extent, extent, 2000)):
        units.append(("Road_%02d" % k, MESH_DIR + "/SM_Street_Road_20m", (x, 0, 0), 0.0))
    kerb_y = 700.0   # web z +-7: the gutter line of the avenue (art: road y -7..7, sidewalks to +-11)
    for k, x in enumerate(range(-extent, extent, 400)):
        for side, y, yaw, x0 in (("N", -kerb_y, 0.0, x), ("S", kerb_y, 180.0, x + 400)):
            kerb = rng.choice(["SM_Street_Kerb_4m", "SM_Street_Kerb_4m", "SM_Street_Kerb_4m_B"])
            walk = rng.choice(["SM_Street_Sidewalk_4m", "SM_Street_Sidewalk_4m_B", "SM_Street_Sidewalk_4m_C"])
            units.append(("Kerb_%s_%02d" % (side, k), MESH_DIR + "/" + kerb, (x0, y, 0), yaw))
            units.append(("Walk_%s_%02d" % (side, k), MESH_DIR + "/" + walk, (x0, y, 0), yaw))
    return units


def level_units(force):
    level = game_data("level")
    atmos = game_data("atmos")
    yield "open map", open_block_map

    # Street kit along the avenue.
    street = street_units(level)
    for start in range(0, len(street), 60):
        def street_chunk(items=street[start:start + 60]):
            for label, mesh, location, yaw in items:
                spawn_mesh(mesh, label, "Block/Street", location, yaw)
            return "%d pieces" % len(items)
        yield "street %d" % start, street_chunk

    # El: bents at every data bent, girder spans and decks from each bent to the next, columns from the data.
    el = level["el"]

    def el_chunk():
        bents = el["bents"]["ue"]["X"]
        for x in bents:
            spawn_mesh(MESH_DIR + "/SM_El_Bent", "El_Bent_%d" % x, "Block/El", (x, 0, 0))
        for a, b in zip(bents, bents[1:]):
            spawn_mesh(MESH_DIR + "/SM_El_GirderSpan_10m", "El_Span_%d" % a, "Block/El", (a, 0, 0),
                       0.0, ((b - a) / 1000.0, 1, 1))
            spawn_mesh(MESH_DIR + "/SM_El_Deck_10m", "El_Deck_%d" % a, "Block/El", (a, 0, 0),
                       0.0, ((b - a) / 1000.0, 1, 1))
        for column in el["columns"]:
            c = column["ue"]
            spawn_mesh(MESH_DIR + "/SM_El_Column", "El_Column_%d_%s" % (c["X"], column["row"]), "Block/El",
                       (c["X"], c["Y"], 0))
        lamps = [l for l in atmos["lamps"]["list"] if l.get("kind") == "el" and abs(l["ue"]["pos"]["Y"]) < 300]
        for lamp in lamps:
            p = lamp["ue"]["pos"]
            spawn_mesh(MESH_DIR + "/SM_El_Lamp", "El_Lamp_%d" % p["X"], "Block/El", (p["X"], p["Y"], EL_LAMP_MOUNT_Z))
        return "%d bents, %d spans, %d columns, %d lamps" % (len(bents), len(bents) - 1, len(el["columns"]), len(lamps))
    yield "el", el_chunk

    # Ground slabs off the avenue (the avenue and its sidewalks are the street kit), and a far ground plane.
    def ground_chunk():
        count = 0
        for k, surface in enumerate(level["ground"]["surfaces"]):
            web, ue = surface["web"], surface["ue"]
            if web["minZ"] >= -11 and web["maxZ"] <= 11:
                continue
            name = GROUND_SURFACE.get(surface["surface"], GROUND_SURFACE["concrete"])[0]
            material = unreal.load_asset("%s/%s" % (MAT_DIR, name))
            center = ((ue["minX"] + ue["maxX"]) / 2.0, (ue["minY"] + ue["maxY"]) / 2.0, -5.0)
            extent = ((ue["maxX"] - ue["minX"]) / 2.0, (ue["maxY"] - ue["minY"]) / 2.0, 5.0)
            spawn_box("Ground_%02d_%s" % (k, surface["surface"]), "Block/Ground", center, extent, material)
            count += 1
        far = unreal.load_asset("%s/%s" % (MAT_DIR, GROUND_SURFACE["far"][0]))
        spawn_box("Ground_Far", "Block/Ground", (0, 0, -12.0), (30000, 30000, 10.0), far)
        return "%d slabs and the far ground" % count
    yield "ground", ground_chunk

    # Grey-box massing: every movement-blocking static collider the meshes above do not already draw.
    boxes = [b for b in level["colliders"]["boxes"]
             if b["tag"] not in SKIP_COLLIDER_TAGS and b["blocks"]["movement"] and not b["flags"]["bulletOnly"]]
    for start in range(0, len(boxes), 120):
        def grey_chunk(items=boxes[start:start + 120]):
            for box in items:
                name = GREY_SURFACE.get(box["surface"], GREY_SURFACE["other"])[0]
                material = unreal.load_asset("%s/%s" % (MAT_DIR, name))
                c, e = box["ue"]["center"], box["ue"]["extent"]
                spawn_box("Grey_%03d_%s" % (box["index"], box["tag"].replace(" ", "_")), "Block/GreyBox",
                          (c["X"], c["Y"], c["Z"]), (e["X"], e["Y"], e["Z"]), material)
            return "%d boxes" % len(items)
        yield "grey-box %d of %d" % (start, len(boxes)), grey_chunk

    def start_and_rig():
        start = level["playerStart"]["ue"]
        # The PlayerStart's capsule centre stands 92 cm over the feet (the default capsule half height).
        spawn_class(unreal.PlayerStart, "PlayerStart", "Block", (start["pos"]["X"], start["pos"]["Y"],
                                                                start["pos"]["Z"] + 92.0), (0, start["yaw"], 0))
        return build_day_rig(atmos["rigs"]["day"])
    yield "player start and day rig", start_and_rig

    def save():
        saved = LEVELS.save_current_level()
        count = len([a for a in ACTORS.get_all_level_actors() if TAG in [str(t) for t in a.tags]])
        return "saved=%s, %d actors" % (saved, count)
    yield "save", save


def setp(target, name, value):
    """Set a property; a renamed one is logged, not fatal (the rig must still come up)."""
    try:
        target.set_editor_property(name, value)
    except Exception as error:   # noqa: BLE001
        unreal.log_warning("build_block: %s.%s: %s" % (target.get_class().get_name(), name, error))


def build_day_rig(day):
    key = day["key"]
    r = key["ue"]["rotator"]
    colour = key["color"]["linear"]
    luminance = 0.2126 * colour[0] + 0.7152 * colour[1] + 0.0722 * colour[2]
    lux = key["intensity"] * LUX_PER_GAME_LUX * luminance

    sun = spawn_class(unreal.DirectionalLight, "Sun", "Block/Light", (0, 0, 2000), (r["Pitch"], r["Yaw"], r["Roll"]))
    light = sun.get_component_by_class(unreal.DirectionalLightComponent)
    light.set_mobility(unreal.ComponentMobility.MOVABLE)
    setp(light, "intensity", lux)
    setp(light, "light_color", unreal.Color(255, 255, 255, 255))   # the atmosphere warms it
    setp(light, "atmosphere_sun_light", True)
    setp(light, "light_source_angle", SUN_SOURCE_ANGLE)
    setp(light, "cast_shadows", True)
    setp(light, "cast_volumetric_shadow", True)

    atmosphere = spawn_class(unreal.SkyAtmosphere, "SkyAtmosphere", "Block/Light")
    sky_atmosphere = atmosphere.get_component_by_class(unreal.SkyAtmosphereComponent)
    # Humid summer air: aerosol (Mie) scattering about 2.5 x Earth's default (art bible 2.4).
    setp(sky_atmosphere, "mie_scattering_scale",
                                       sky_atmosphere.get_editor_property("mie_scattering_scale") * 2.5)

    sky = spawn_class(unreal.SkyLight, "SkyLight", "Block/Light", (0, 0, 1000))
    sky_light = sky.get_component_by_class(unreal.SkyLightComponent)
    sky_light.set_mobility(unreal.ComponentMobility.MOVABLE)
    setp(sky_light, "real_time_capture", True)
    setp(sky_light, "intensity", 1.0)

    # Haze: the web's day haze reaches 8 % at 92 m (atmos.json fog.opacityAt). Height fog extinction is
    # density x 0.001 per cm here, flat (tiny falloff): 1 - exp(-d * 0.001 * 9200) = 0.083 at d ~ 0.0094.
    # The sky atmosphere's aerial perspective adds its own share, so the fog takes about half.
    target = [p for p in day["fog"]["opacityAt"] if p["ue"] == 9200][0]["opacity"]
    density = -math.log(1.0 - target) / (0.001 * 9200) * 0.5
    fog = spawn_class(unreal.ExponentialHeightFog, "HeightFog", "Block/Light", (0, 0, 0))
    fog_component = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    setp(fog_component, "fog_density", density)
    setp(fog_component, "fog_height_falloff", 0.02)
    setp(fog_component, "fog_inscattering_luminance", unreal.LinearColor(0, 0, 0, 1))
    setp(fog_component, "enable_volumetric_fog", True)
    setp(fog_component, "volumetric_fog_scattering_distribution", 0.7)

    grade = day["grade"]
    volume = spawn_class(unreal.PostProcessVolume, "PostProcess", "Block/Light")
    volume.set_editor_property("unbound", True)
    settings = volume.get_editor_property("settings")
    values = (
        ("dynamic_global_illumination_method", unreal.DynamicGlobalIlluminationMethod.LUMEN),
        ("reflection_method", unreal.ReflectionMethod.LUMEN),
        ("auto_exposure_method", unreal.AutoExposureMethod.AEM_HISTOGRAM),
        ("auto_exposure_min_brightness", DAY_EV100[0]),
        ("auto_exposure_max_brightness", DAY_EV100[1]),
        ("auto_exposure_bias", 0.0),
        ("auto_exposure_speed_up", 6.0),                      # settles within the shot warm-up
        ("auto_exposure_speed_down", 6.0),
        ("bloom_intensity", 0.25),                            # art bible 2.3: restrained, no threshold
        ("bloom_threshold", -1.0),
        ("vignette_intensity", 0.15),
        ("white_temp", 6300.0),
        ("local_exposure_highlight_contrast_scale", 0.8),
        ("local_exposure_shadow_contrast_scale", 0.72),
        ("lumen_final_gather_quality", 1.0),
        ("lumen_scene_detail", 2.0),
    )
    applied = []
    for name, value in values:
        try:
            settings.set_editor_property("override_" + name, True)
            settings.set_editor_property(name, value)
            applied.append(name)
        except Exception as error:   # noqa: BLE001 - a renamed setting must not stop the build
            unreal.log_warning("build_block: post-process setting %s: %s" % (name, error))
    settings.set_editor_property("color_saturation", unreal.Vector4(grade["saturation"], grade["saturation"],
                                                                    grade["saturation"], 1.0))
    settings.set_editor_property("override_color_saturation", True)
    volume.set_editor_property("settings", settings)
    return "sun %.0f lx at pitch %.1f yaw %.1f, fog density %.4f, EV100 %.1f..%.1f, %d post settings" % (
        lux, r["Pitch"], r["Yaw"], density, DAY_EV100[0], DAY_EV100[1], len(applied))


# ------------------------------------------------------------------------------------------------------ the job

STEPS = {"textures": texture_units, "materials": material_units, "meshes": mesh_units, "level": level_units}
_JOB = {}


def status_path():
    folder = os.path.join(project_dir("Saved"), "BuildBlock")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "status.txt")


def _write(line):
    with open(status_path(), "a", encoding="utf-8") as handle:
        handle.write("%s %s\n" % (time.strftime("%H:%M:%S"), line))
    unreal.log("build_block: " + line)


def _tick(delta_seconds):
    job = _JOB
    if not job or job.get("busy"):      # an import can pump Slate ticks while it runs: never re-enter
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
    except Exception:   # noqa: BLE001 - every failure ends the job with its traceback in the status file
        _finish("FAILED " + traceback.format_exc()[-700:].replace("\n", " | "))
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
    """steps: "all" or a comma list of textures, materials, meshes, level. force: rebuild assets that exist."""
    if _JOB:
        return "a build_block job is already running"
    names = list(STEPS) if steps == "all" else [s.strip() for s in steps.split(",") if s.strip()]
    unknown = [n for n in names if n not in STEPS]
    if unknown:
        return "unknown steps %s (use %s)" % (unknown, ", ".join(STEPS))
    with open(status_path(), "w", encoding="utf-8") as handle:
        handle.write("%s START %s force=%s\n" % (time.strftime("%H:%M:%S"), ",".join(names), force))
    _JOB.update(units=_chain(names, force), done=0, t0=time.time())
    _JOB["handle"] = unreal.register_slate_post_tick_callback(_tick)
    return "started %s: poll %s" % (",".join(names), status_path())
