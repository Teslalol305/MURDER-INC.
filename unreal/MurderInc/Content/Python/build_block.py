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
  textures   /Game/Art/Textures/<Set>/T_<Set>_*: BC and E (sign emission) sRGB; N linear normal map with the green
             channel flipped (the sets are OpenGL, +Y up; Unreal wants DirectX); ORM linear masks
  materials  /Game/Art/Materials/M_MI_Surface (master: tiling or unique sets, wear masks, detail layer near the
             eye, macro variation, sign emission), M_MI_Glass (window and shop glass over a world-space interior
             room per window), M_MI_Flat (untextured slots: chrome, aluminium, blinds, lenses, sign stand-ins) and one
             instance per manifest slot (MI_<Surface>_<Variant>, MI_<Asset> for a slot M_<Asset>), the per-shop
             awning cloths, plus the grey-box and ground instances (MI_Grey_*, MI_Ground_*)
  meshes     /Game/Art/Meshes/SM_*: Interchange glTF, Nanite on, no glTF materials; slots assigned by name;
             bounds checked against the manifest (proves the axes and the scale)
  level      /Game/Maps/L_Block: street kit tiled along the avenue, El modules at the data's bents and columns,
             the facade kit on every street-facing building (art-in/placements/buildings.json, instanced static
             meshes), the catalogue props of props.json that have a mesh, every other movement-blocking static
             collider as grey-box massing; the colliders the art replaces stay as invisible blocking boxes (the
             tuned cover does not change); ground slabs, the backdrop (the avenue's continuation and a distant
             skyline), player start, day rig with volumetric clouds

Units are Unreal's: centimetres, Z up, X east, Y south. Every spawned actor carries the tag MIBlock.
"""
import json
import math
import os
import random
import re
import time
import traceback

import unreal

ART_IN = os.environ.get("MI_ART_IN", "/project/ue/art-in")
ROOT = "/Game/Art"
TEX_DIR, MAT_DIR, MESH_DIR = ROOT + "/Textures", ROOT + "/Materials", ROOT + "/Meshes"
MAP_PATH = "/Game/Maps/L_Block"
MASTER = MAT_DIR + "/M_MI_Surface"
MASKED_MASTER = MAT_DIR + "/M_MI_SurfaceMasked"
GLASS_MASTER = MAT_DIR + "/M_MI_Glass"
FLAT_MASTER = MAT_DIR + "/M_MI_Flat"
CARPAINT_MASTER = MAT_DIR + "/M_MI_CarPaint"     # M_MI_Surface with the clear-coat shading model
CATALOGUE_TABLE = "art_catalogue"               # Content/Data/art_catalogue.json: catalogue id -> meshes
GAMEPLAY_OWNERS = {"explosive"}                 # level.json collider owners drawn by gameplay actors
BLACK_TEXTURE = "/Engine/EngineResources/Black.Black"
FLAT_NORMAL = "/Engine/EngineMaterials/FlatNormal.FlatNormal"
TAG = "MIBlock"
CUBE = "/Engine/BasicShapes/Cube.Cube"          # 100 cm, centred on its origin

# Art constants that are not game data (art/blender/README.md, "el" family; ART_BIBLE.md 2.1, 2.3, 2.4;
# docs/unreal/spec/06-look-fx.md 4.5). The day rig's own numbers come from atmos.json.
EL_LAMP_MOUNT_Z = 602.0          # top of the lamp canopy under the deck (README: lamps at (x + 5, +-2.1, 6.02))
LUX_PER_GAME_LUX = 24400.0       # spec 4.5: the web sun (5 game lux x colour luminance 0.819) anchored at 100,000 lx
DAY_EV100 = (12.3, 14.2)         # art bible 2.3: auto exposure clamped; open sun near 14.2, under the El about 13.2,
                                 # the lower clamp is the readability dial (spec 4.5 puts the web's fixed 1.1 at 13.4)
SUN_SOURCE_ANGLE = 0.5357        # art bible 2.4
SUN_SHAFTS = 3.0                 # sun volumetric scattering: visible shafts through the El ties
CONTACT_SHADOW = 0.03            # screen-space contact shadow length of the sun
FOG_VOLUME_EXTINCTION = 5.0      # volumetric fog only: enough medium for the shafts, the far haze stays the fog's
LOCAL_SHADOW_CONTRAST = 0.45     # local exposure lifts the shade under the El without flattening the sun
CLOUD_MATERIAL = "/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst"
CLOUD_LAYER = {"layer_bottom_altitude": 1.6, "layer_height": 6.0}   # km: fair-weather cumulus bases
STREET_EXTENT_CM = 7000          # street kit runs this far east and west of the centre (the bounds end at 4,600)
GREY_SURFACE = {                 # collider surface -> (grey-box instance, texture set, tint)
    "brick": ("MI_Grey_Brick", "TS_Brick_ScanRedCommon", (1.0, 1.0, 1.0)),       # roofs: ROOF_SET
    "concrete": ("MI_Grey_Concrete", "TS_Concrete_ScanWeathered", (1.0, 1.0, 1.0)),
    "metal": ("MI_Grey_Metal", "TS_Concrete_ScanWeathered", (0.42, 0.45, 0.5)),
    "wood": ("MI_Grey_Wood", "TS_Concrete_ScanWeathered", (0.8, 0.58, 0.4)),
    "car": ("MI_Grey_Car", None, ((0.045, 0.05, 0.058), 0.32, 0.6, 0.0)),        # vehicles stay masses: dark paint
    "glass": ("MI_Grey_Glass", None, ((0.01, 0.011, 0.012), 0.05, 0.0, 0.0)),
    "other": ("MI_Grey_Other", "TS_Concrete_ScanWeathered", (0.6, 0.55, 0.5)),
}
ROOF_SET = "TS_Roof_ScanBitumen"         # upward faces of the brick massing and the backdrop: tar roofs
# Colliders the art has no module for keep their box, dressed in the material of what they are (05-level): tag ->
# (instance, texture set world-projected, tint). Sets None: flat values; "glass": the glass with rooms.
TAG_SURFACE = {
    "station": ("MI_Box_ElGreen", "TS_Steel_ScanPaintGreen", (0.84, 1.0, 1.3)),
    "kiosk": ("MI_Box_SteelDark", "TS_Steel_ScanPaintGrey", (0.3, 0.3, 0.32)),
    "hoarding": ("MI_Box_PlywoodGreen", "TS_Plywood_ScanLauan", (0.17, 0.93, 0.83)),
    "dig": ("MI_Box_Plywood", "TS_Plywood_ScanLauan", (1.0, 1.0, 1.0)),
    "produce-stand": ("MI_Box_WoodPainted", "TS_Wood_ScanPlankPainted", (1.0, 1.0, 1.0)),
    "shanty": ("MI_Box_Plywood", "TS_Plywood_ScanLauan", (1.0, 1.0, 1.0)),
    "hoist": ("MI_Box_Plywood", "TS_Plywood_ScanLauan", (1.0, 1.0, 1.0)),
    "backs": ("MI_Box_BrickWindows", "TS_Brick_ScanRedCommon", (1.0, 1.0, 1.0)),
    "seal": ("MI_Box_BrickBrown", "TS_Brick_ScanBrown", (1.0, 1.0, 1.0)),
    "garages": ("MI_Box_BrickPainted", "TS_BrickPainted_ScanWhitewash", (1.0, 1.0, 1.0)),
    "office-glass": ("MI_Box_Glass", "glass", None),
    "shop-wall": ("MI_Box_BlockPainted", "TS_Block_ScanPainted", (0.61, 0.74, 1.06)),
}
for _tag in ("office", "mezzanine", "railing", "shop-stair", "shop-column", "safe", "roadblock", "scaffold",
             "tyre-cage", "alley-gate", "lot-gate", "lot-sign"):
    TAG_SURFACE[_tag] = ("MI_Box_SteelGrey", "TS_Steel_ScanPaintGrey", (1.0, 1.0, 1.0))
BACKDROP_SURFACE = {"brick": ("MI_Backdrop_Brick", "TS_Brick_ScanRedCommon", (0.72, 0.64, 0.6)),
                    "concrete": ("MI_Backdrop_Concrete", "TS_Concrete_ScanWeathered", (0.78, 0.77, 0.75)),
                    "brown": ("MI_Backdrop_BrickBrown", "TS_Brick_ScanBrown", (0.8, 0.75, 0.72)),
                    "buff": ("MI_Backdrop_BrickBuff", "TS_Brick_ScanBuff", (0.85, 0.82, 0.78)),
                    "dark": ("MI_Backdrop_BrickDark", "TS_Brick_ScanRedDark", (0.8, 0.75, 0.72))}
ROOFED = {"MI_Grey_Brick", "MI_Box_BrickWindows", "MI_Box_BrickBrown", "MI_Box_BrickPainted"} | \
    {v[0] for v in BACKDROP_SURFACE.values()}
WINDOWED = {"MI_Box_BrickWindows"} | {v[0] for v in BACKDROP_SURFACE.values()}
BACKDROP_ROOF_PROPS = (("SM_Facade_WaterTank", 0.35), ("SM_Facade_StairBulkhead_Red", 0.45),
                       ("SM_Facade_AirConditioner", 0.6))   # (mesh, chance per roof) within 1.5 km
GROUND_SURFACE = {               # level.json ground surface -> (instance, texture set, tint)
    "asphalt": ("MI_Ground_Asphalt", "TS_Asphalt_ScanWorn", (1.0, 1.0, 1.0)),
    "concrete": ("MI_Ground_Concrete", "TS_Concrete_ScanRough", (1.0, 1.0, 1.0)),
    "dirt": ("MI_Ground_Dirt", "TS_Concrete_ScanRough", (0.62, 0.5, 0.38)),
    "far": ("MI_Ground_Far", "TS_Asphalt_ScanWorn", (0.8, 0.8, 0.8)),
}
SKIP_COLLIDER_TAGS = {"el-column", "el-girder", "el-deck", "sidewalk"}   # drawn by the El and street meshes
DETAIL_SCALE = 4.37              # detail layer: the set again at 4.37 x its repeat (an odd ratio: no visible beat)
SIGN_NITS = 900.0                # sign faces with an emission map: a lit lightbox reads in daylight at about 900 nits
# Untextured manifest slots (workflow "flat"): base colour (linear), roughness, metallic, emissive nits.
FLAT_SLOTS = {
    "MI_Metal_Chrome": ((0.93, 0.93, 0.93), 0.08, 1.0, 0.0),
    "MI_Metal_Aluminium": ((0.86, 0.87, 0.88), 0.34, 1.0, 0.0),
    "MI_Fabric_Blind": ((0.56, 0.52, 0.44), 0.88, 0.0, 0.0),       # parchment roller blind
    "MI_Interior_Dark": ((0.018, 0.017, 0.016), 0.9, 0.0, 0.0),
    "MI_Lamp_Lens": ((0.72, 0.68, 0.6), 0.15, 0.0, 0.0),           # unlit by day
    "MI_Glass_SodiumLens": ((0.6, 0.45, 0.25), 0.12, 0.0, 0.0),
    "MI_Glass_CarTint": ((0.011, 0.012, 0.014), 0.03, 0.0, 0.0),   # tinted car glass: dark, sharp Lumen reflections
    "MI_Glass_Standoff": ((0.03, 0.03, 0.032), 0.05, 0.0, 0.0),
    "MI_Glass_Acrylic": ((0.05, 0.05, 0.052), 0.08, 0.0, 0.0),
    "MI_Glass_StationLit": ((0.06, 0.055, 0.05), 0.05, 0.0, 0.0),  # unlit by day
    "MI_Glass_PlatformLit": ((0.06, 0.06, 0.065), 0.05, 0.0, 0.0),
    "MI_Glass_Wired": ((0.05, 0.052, 0.05), 0.2, 0.0, 0.0),
}
NEON_DAY_NITS = 550.0            # spec 2.8: tubes 400 .. 2,000 nits at night, x 0.55 by day
CLEARCOAT_ROUGHNESS = 0.03       # car paint clear coat (art bible: glossy, Lumen reflections)
SIGN_STAND_IN = ((0.42, 0.42, 0.4), 0.55, 0.0, 0.0)               # neutral sign face until the art arrives
# Glass over a world-space interior room per window (M_MI_Glass): room cell size and offset in cm (Z: storeys of
# 310 above the 380 cm shop floor line; Y: 550 so that both building lines, Y -1100 and +1100, are cell walls),
# interior luminance in nits (rooms behind daylit windows are about a tenth of the facade), shop mode.
GLASS_SLOTS = {
    "MI_Glass_Window": dict(room=(310.0, 550.0, 310.0), offset=(0.0, 0.0, 70.0), nits=110.0, shop=0.0, sill=0.19,
                            cube_scale=1.3),
    "MI_Glass_Store": dict(room=(310.0, 550.0, 310.0), offset=(0.0, 0.0, 70.0), nits=200.0, shop=1.0, sill=0.03,
                           cube_scale=1.8),
}
INTERIOR_CUBES = {"shop": ("ShopGrocery", "ShopParlour", "ShopStore"),       # mi_interiors.ROOMS
                  "home": ("HomeLiving", "HomeBedroom", "HomeVacant")}
BACKDROP_AVENUE_CM = 45000      # the avenue's street walls continue this far east and west of the centre
AWNING_SCAN_MEAN = (0.284, 0.408, 0.613)   # mean linear albedo of TS_Fabric_ScanCanvas BC: tint = cloth / scan

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
            if ext.lower() not in (".jpg", ".jpeg", ".png") or kind not in ("BC", "N", "ORM", "E"):
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
// Octaves 3 and 4 (14 m and 4.3 m) are the macro variation that hides the tile repeat over 10 to 20 m.
float n[5];
float scales[5] = {1.0 / 6.0, 1.0 / 23.0, 1.0, 1.0 / 1400.0, 1.0 / 430.0};
for (int o = 0; o < 5; o++)
{
    float3 P = (o == 2) ? WP * float3(1.0 / 22.0, 1.0 / 22.0, 1.0 / 260.0) : WP * scales[o] + o * 17.31;
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
// Macro variation (Macro.x): value, a slight warm-cool shift and roughness drift over 4 to 14 m.
float macro = 0.6 * n[3] + 0.4 * n[4];
float3 hue = lerp(float3(1.03, 1.0, 0.95), float3(0.96, 1.0, 1.05), n[4]);
bc *= lerp(float3(1.0, 1.0, 1.0), (1.0 + (macro - 0.5) * 0.32) * hue, Macro.x);
rough += (macro - 0.5) * 0.12 * Macro.x;
// Detail layer (Macro.y): the set's own roughness at the detail scale fades in within 3 m of the eye.
float near = saturate((300.0 - Depth) / 150.0) * Macro.y;
rough += (ORMD.g - 0.5) * 0.35 * near;
// Windows (Windows.x): a grid of dark glazed openings on the vertical faces of world-projected masses (the
// backdrop and the neighbours' backs): bay Windows.y, storey Windows.z, from the first floor line (3.8 m) up,
// sill 19 %, head 75 % (vector parameters reach the HLSL as float3: no w).
if (Windows.x > 0.5 && abs(NW.z) < 0.3)
{
    float u = (abs(NW.x) > abs(NW.y)) ? WP.y : WP.x;
    float bay = frac(u / Windows.y);
    float storey = frac((WP.z - 380.0) / Windows.z);
    float inWindow = step(0.3, bay) * step(bay, 0.7) * step(0.19, storey) * step(storey, 0.75) * step(380.0, WP.z);
    float id = frac(sin(dot(floor(float2(u / Windows.y, (WP.z - 380.0) / Windows.z)), float2(12.99, 78.23))) * 43758.5);
    float3 glass = lerp(float3(0.012, 0.014, 0.016), float3(0.05, 0.045, 0.04), step(0.7, id));
    bc = lerp(bc, glass, inWindow);
    rough = lerp(rough, 0.06 + 0.1 * id, inWindow);
    metal = lerp(metal, 0.0, inWindow);
    ao = lerp(ao, 1.0, inWindow);
}
Rough = saturate(rough);
Metal = saturate(metal);
AO = saturate(ao);
Edge = set2;
return bc;
"""

# Detail normal: the set's normal sampled again at the detail scale, whiteout-blended in within 3 m of the eye.
DETAIL_NORMAL_HLSL = r"""
float near = saturate((300.0 - Depth) / 150.0) * Amount;
float3 d = lerp(float3(0.0, 0.0, 1.0), ND, near);
return normalize(float3(NA.xy + d.xy, NA.z * d.z));
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


def build_master(defaults, force, path=None, masked=False, clearcoat=False):
    """M_MI_Surface: tiling texture set (+ optional second set on G), tint, Wear vertex-colour masks."""
    # Rebuilt in place, never deleted: deleting a parent orphans its instances, and every orphan then compiles
    # the default material synchronously on the game thread (minutes).
    path = path or MASTER
    if ASSETS.does_asset_exist(path):
        if not force:
            return "exists"
        material = unreal.load_asset(path)
        LIB.delete_all_material_expressions(material)
    else:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        material = tools.create_asset(path.rsplit("/", 1)[1], MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    if masked:          # alpha-tested cards (chain-link): BC alpha clips at 0.5, both faces drawn
        setp(material, "blend_mode", unreal.BlendMode.BLEND_MASKED)
        setp(material, "two_sided", True)
    if clearcoat:       # car paint: the base layer as M_MI_Surface under a glossy clear coat
        setp(material, "shading_model", unreal.MaterialShadingModel.MSM_CLEAR_COAT)

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
    # The detail layer: the same N and ORM parameters sampled at DetailScale x the surface UVs.
    detail_scale = expr(material, unreal.MaterialExpressionScalarParameter, -1800, 1700, parameter_name="DetailScale",
                        default_value=DETAIL_SCALE)
    detail_uv = expr(material, unreal.MaterialExpressionMultiply, -1650, 1700)
    LIB.connect_material_expressions(uv_switch, "", detail_uv, "A")
    LIB.connect_material_expressions(detail_scale, "", detail_uv, "B")
    for kind, sampler, y in (("N", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, 1700),
                             ("ORM", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, 1950)):
        node = expr(material, unreal.MaterialExpressionTextureSampleParameter2D, -1500, y, parameter_name=kind,
                    sampler_type=sampler, texture=defaults[kind])
        LIB.connect_material_expressions(detail_uv, "", node, "UVs")
        samplers[kind + "D"] = node
    emission = expr(material, unreal.MaterialExpressionTextureSampleParameter2D, -1500, 2200, parameter_name="E",
                    sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
                    texture=unreal.load_asset(BLACK_TEXTURE))
    LIB.connect_material_expressions(uv_switch, "", emission, "UVs")
    depth = expr(material, unreal.MaterialExpressionPixelDepth, -900, 1650)

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
    macro = vector("Macro", (1, 1, 0, 0), -900, 1550)        # x: macro variation, y: detail layer (0 on unique sets)
    windows = expr(material, unreal.MaterialExpressionVectorParameter, -900, 1600, parameter_name="Windows",
                   default_value=unreal.LinearColor(0, 310, 310, 380))
    vertex_colour = expr(material, unreal.MaterialExpressionVertexColor, -900, 1500)
    wear = custom(material, -500, 300, WEAR_HLSL,
                  ["BC", "ORM", "BC2", "ORM2", "VC", "VA", "WP", "Tint", "DirtColor", "LeakColor", "SplashColor",
                   "Modes", "Wetness", "Amount", "NW", "Macro", "ORMD", "Depth", "Windows"],
                  unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["Rough", "Metal", "AO", "Edge"])
    for name, source, output in (("BC", samplers["BC"], "RGB"), ("ORM", samplers["ORM"], "RGB"),
                                 ("BC2", samplers["BC2"], "RGB"), ("ORM2", samplers["ORM2"], "RGB"),
                                 ("VC", vertex_colour, ""), ("VA", vertex_colour, "A"), ("WP", wp, ""),
                                 ("Tint", tint, ""), ("Wetness", modes, "A"),
                                 ("DirtColor", dirt, ""), ("LeakColor", leak, ""), ("SplashColor", splash, ""),
                                 ("Modes", modes, ""), ("Amount", amount, ""), ("NW", normal_ws, ""),
                                 ("Macro", macro, ""), ("ORMD", samplers["ORMD"], "RGB"), ("Depth", depth, ""),
                                 ("Windows", windows, "")):
        if not LIB.connect_material_expressions(source, output, wear, name):
            raise RuntimeError("cannot connect %s output '%s' to the wear node" % (name, output))

    normal_blend = expr(material, unreal.MaterialExpressionLinearInterpolate, -200, 600)
    LIB.connect_material_expressions(samplers["N"], "RGB", normal_blend, "A")
    LIB.connect_material_expressions(samplers["N2"], "RGB", normal_blend, "B")
    LIB.connect_material_expressions(wear, "Edge", normal_blend, "Alpha")

    detail_normal = custom(material, 0, 600, DETAIL_NORMAL_HLSL, ["NA", "ND", "Depth", "Amount"],
                           unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    LIB.connect_material_expressions(normal_blend, "", detail_normal, "NA")
    LIB.connect_material_expressions(samplers["ND"], "RGB", detail_normal, "ND")
    LIB.connect_material_expressions(depth, "", detail_normal, "Depth")
    LIB.connect_material_expressions(macro, "G", detail_normal, "Amount")
    emissive_scale = expr(material, unreal.MaterialExpressionScalarParameter, -900, 2300,
                          parameter_name="EmissiveScale", default_value=0.0)
    emissive = expr(material, unreal.MaterialExpressionMultiply, -600, 2250)
    LIB.connect_material_expressions(emission, "RGB", emissive, "A")
    LIB.connect_material_expressions(emissive_scale, "", emissive, "B")

    LIB.connect_material_property(wear, "", unreal.MaterialProperty.MP_BASE_COLOR)
    LIB.connect_material_property(wear, "Rough", unreal.MaterialProperty.MP_ROUGHNESS)
    LIB.connect_material_property(wear, "Metal", unreal.MaterialProperty.MP_METALLIC)
    LIB.connect_material_property(wear, "AO", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    LIB.connect_material_property(detail_normal, "", unreal.MaterialProperty.MP_NORMAL)
    LIB.connect_material_property(emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if masked:
        LIB.connect_material_property(samplers["BC"], "A", unreal.MaterialProperty.MP_OPACITY_MASK)
    if clearcoat:
        LIB.connect_material_property(expr(material, unreal.MaterialExpressionConstant, -200, 900, r=1.0), "",
                                      unreal.MaterialProperty.MP_CUSTOM_DATA0)
        LIB.connect_material_property(expr(material, unreal.MaterialExpressionConstant, -200, 980,
                                           r=CLEARCOAT_ROUGHNESS), "", unreal.MaterialProperty.MP_CUSTOM_DATA1)
    LIB.recompile_material(material)
    ASSETS.save_asset(path, only_if_is_dirty=False)
    return "created"


# World-space interior mapping: the eye ray enters the room cell behind the pane and the first wall it meets gives
# the colour; every cell hashes its own wall paint, lamp state and furniture band, so no two windows match.
GLASS_HLSL = r"""
float3 V = -normalize(CamV);                        // from the eye into the building
float3 P = WP;
float3 cellP = (WP - N * 40.0 - Offset) / Room;     // the cell behind the pane, whatever the pane's inset
float3 cell = floor(cellP);
float3 far = (cell + step(0.0, V)) * Room + Offset;
float3 safeV = sign(V) * max(abs(V), 1e-4);
float3 t = (far - P) / safeV;
float tm = min(t.x, min(t.y, t.z));
float3 hit = P + V * tm;
float3 f = (hit - Offset) / Room - cell;            // 0..1 inside the cell
float h1 = frac(sin(dot(cell, float3(12.9898, 78.233, 37.719))) * 43758.5453);
float h2 = frac(sin(dot(cell, float3(39.346, 11.135, 83.155))) * 24634.6345);
float h3 = frac(sin(dot(cell, float3(73.156, 52.235, 9.151))) * 35791.4351);
float3 paints[4] = {float3(0.42, 0.38, 0.30), float3(0.30, 0.33, 0.30), float3(0.45, 0.42, 0.38), float3(0.36, 0.27, 0.22)};
float3 wall = paints[(int)(h1 * 3.99)];
float3 colour;
float3 an = abs(t - tm);
if (t.z <= t.x && t.z <= t.y)
    colour = (V.z < 0.0) ? float3(0.16, 0.11, 0.07) : float3(0.55, 0.53, 0.5);   // floor boards : ceiling
else
{
    bool back = (abs(N.x) > abs(N.y)) ? (t.x <= t.y) : (t.y <= t.x);
    colour = wall * (back ? 1.0 : 0.75);
    float fz = f.z;
    if (Shop > 0.5)
    {
        // Shelving on every wall: dark uprights, bands of packed goods in muted packaging colours, a counter.
        colour = float3(0.42, 0.41, 0.38) * (back ? 1.0 : 0.8);
        float band = frac(fz * 6.0);
        float slot = floor((f.x + f.y) * 14.0);
        float pick = frac(sin(slot * 12.31 + h2 * 7.0) * 3758.5);
        float goods = step(0.3, band) * step(fz, 0.8) * step(0.12, fz) * step(0.08, frac((f.x + f.y) * 14.0));
        float3 stock = lerp(float3(0.36, 0.26, 0.2), float3(0.24, 0.27, 0.3), pick) * (0.6 + 0.6 * frac(pick * 7.3));
        colour = lerp(colour, stock, goods);
        colour = lerp(colour, float3(0.08, 0.07, 0.06), step(band, 0.3) * step(fz, 0.8) * step(0.12, fz) * 0.6);
    }
    else
    {
        // A dark furniture band (sofa, dresser) along the back wall in most rooms, a picture in some.
        float w0 = 0.15 + 0.3 * h2, w1 = w0 + 0.3 + 0.3 * h3;
        float side = (abs(N.x) > abs(N.y)) ? f.y : f.x;
        float furn = step(fz, 0.28 + 0.12 * h3) * step(w0, side) * step(side, w1) * (back ? 1.0 : 0.0);
        colour = lerp(colour, float3(0.06, 0.05, 0.05), furn);
    }
}
// Light falls off into the room; a lamp is on in about one room in six.
float depthK = saturate(1.0 - tm / (Room.y * 1.6));
float lit = (0.35 + 0.65 * depthK) * (0.55 + 0.9 * h3) * ((h2 > 0.84) ? 2.2 : 1.0);
float3 room = colour * lit * Nits;
// Grime: a film near the sill and in streaks, plus the mesh's own Wear R.
float3 q = (WP - Offset) / Room;
float sillDist = frac(q.z) - Sill;
float noise = frac(sin(dot(floor(WP * float3(1.0 / 9.0, 1.0 / 9.0, 1.0 / 35.0)), float3(7.1, 3.7, 1.3))) * 9631.71);
Dirt = saturate(saturate(1.0 - sillDist / 0.09) * 0.7 + noise * 0.25 + VC * 0.8);
return room * (1.0 - 0.6 * Dirt);
"""


# Interior by cube map (mi_interiors.py bakes the rooms): the eye ray's hit on the far walls of the window's room cell,
# seen from the cell centre, in the baked room's frame (X across the window, Y into the room, Z up) and size; one of
# three cubes per cell, half of them mirrored, the lamp level varied.
CUBE_HLSL = r"""
float3 V = -normalize(CamV);
float3 cellP = (WP - N * 40.0 - Offset) / Room;
float3 cell = floor(cellP);
float3 far = (cell + step(0.0, V)) * Room + Offset;
float3 safeV = sign(V) * max(abs(V), 1e-4);
float3 t = (far - WP) / safeV;
float tm = min(t.x, min(t.y, t.z));
float3 d = WP + V * tm - ((cell + 0.5) * Room + Offset);
float h1 = frac(sin(dot(cell, float3(12.9898, 78.233, 37.719))) * 43758.5453);
float h2 = frac(sin(dot(cell, float3(39.346, 11.135, 83.155))) * 24634.6345);
float h3 = frac(sin(dot(cell, float3(73.156, 52.235, 9.151))) * 35791.4351);
float3 L;
if (abs(N.y) >= abs(N.x))
    L = float3(d.x / Room.x, -sign(N.y) * d.y / Room.y, d.z / Room.z) * Bake;
else
    L = float3(d.y / Room.y, -sign(N.x) * d.x / Room.x, d.z / Room.z) * Bake;
if (h2 > 0.5) L.x = -L.x;
WA = step(h1, 0.3333);
WB = step(0.3333, h1) * step(h1, 0.6666);
WC = step(0.6666, h1);
Lit = (0.55 + 0.7 * h3) * ((h2 > 0.88) ? 0.25 : 1.0);
return L;
"""


def build_glass_master(force):
    """M_MI_Glass: opaque glazing (Nanite, full Lumen reflections) whose emission is the room behind it."""
    if ASSETS.does_asset_exist(GLASS_MASTER):
        if not force:
            return "exists"
        material = unreal.load_asset(GLASS_MASTER)
        LIB.delete_all_material_expressions(material)
    else:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "M_MI_Glass", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    wp = world_position(material, -1400, 0)
    camera = expr(material, unreal.MaterialExpressionCameraVectorWS, -1400, 150)
    normal_ws = expr(material, unreal.MaterialExpressionVertexNormalWS, -1400, 250)
    vertex_colour = expr(material, unreal.MaterialExpressionVertexColor, -1400, 350)

    def param(cls, name, value, y):
        if cls is unreal.MaterialExpressionVectorParameter:
            return expr(material, cls, -1400, y, parameter_name=name, default_value=unreal.LinearColor(*value))
        return expr(material, cls, -1400, y, parameter_name=name, default_value=value)
    room = param(unreal.MaterialExpressionVectorParameter, "Room", (310, 550, 310, 0), 450)
    offset = param(unreal.MaterialExpressionVectorParameter, "Offset", (0, 0, 70, 0), 550)
    nits = param(unreal.MaterialExpressionScalarParameter, "Nits", 260.0, 650)
    shop = param(unreal.MaterialExpressionScalarParameter, "Shop", 0.0, 750)
    sill = param(unreal.MaterialExpressionScalarParameter, "Sill", 0.19, 850)
    node = custom(material, -900, 300, GLASS_HLSL, ["WP", "CamV", "N", "VC", "Room", "Offset", "Nits", "Shop", "Sill"],
                  unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["Dirt"])
    for name, source, output in (("WP", wp, ""), ("CamV", camera, ""), ("N", normal_ws, ""),
                                 ("VC", vertex_colour, "R"), ("Room", room, ""), ("Offset", offset, ""),
                                 ("Nits", nits, ""), ("Shop", shop, ""), ("Sill", sill, "")):
        if not LIB.connect_material_expressions(source, output, node, name):
            raise RuntimeError("cannot connect %s to the glass node" % name)
    # The baked rooms: three cube parameters, one picked per cell; CubeScale turns the capture into nits.
    bake = param(unreal.MaterialExpressionVectorParameter, "Bake", (310, 550, 310, 0), 950)
    cube_node = custom(material, -900, 900, CUBE_HLSL, ["WP", "CamV", "N", "Room", "Offset", "Bake"],
                       unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["WA", "WB", "WC", "Lit"])
    for name, source in (("WP", wp), ("CamV", camera), ("N", normal_ws), ("Room", room), ("Offset", offset),
                         ("Bake", bake)):
        LIB.connect_material_expressions(source, "", cube_node, name)
    default_cube = unreal.load_asset("/Engine/EngineResources/GrayDarkTextureCube.GrayDarkTextureCube")
    total = None
    for k, (cube_name, weight) in enumerate((("CubeA", "WA"), ("CubeB", "WB"), ("CubeC", "WC"))):
        sample = expr(material, unreal.MaterialExpressionTextureSampleParameterCube, -500, 800 + k * 220,
                      parameter_name=cube_name, texture=default_cube)
        LIB.connect_material_expressions(cube_node, "", sample, "UVs")
        weighted = expr(material, unreal.MaterialExpressionMultiply, -300, 800 + k * 220)
        LIB.connect_material_expressions(sample, "RGB", weighted, "A")
        LIB.connect_material_expressions(cube_node, weight, weighted, "B")
        if total is None:
            total = weighted
        else:
            summed = expr(material, unreal.MaterialExpressionAdd, -150, 800 + k * 220)
            LIB.connect_material_expressions(total, "", summed, "A")
            LIB.connect_material_expressions(weighted, "", summed, "B")
            total = summed
    cube_scale = param(unreal.MaterialExpressionScalarParameter, "CubeScale", 1.0, 1450)
    lit = expr(material, unreal.MaterialExpressionMultiply, 0, 900)
    LIB.connect_material_expressions(cube_node, "Lit", lit, "A")
    LIB.connect_material_expressions(cube_scale, "", lit, "B")
    cube_room = expr(material, unreal.MaterialExpressionMultiply, 150, 850)
    LIB.connect_material_expressions(total, "", cube_room, "A")
    LIB.connect_material_expressions(lit, "", cube_room, "B")
    clean = expr(material, unreal.MaterialExpressionOneMinus, 0, 1000)
    dirt_k = expr(material, unreal.MaterialExpressionMultiply, -150, 1000)
    LIB.connect_material_expressions(node, "Dirt", dirt_k, "A")
    LIB.connect_material_expressions(expr(material, unreal.MaterialExpressionConstant, -300, 1050, r=0.6), "", dirt_k, "B")
    LIB.connect_material_expressions(dirt_k, "", clean, "")
    cube_final = expr(material, unreal.MaterialExpressionMultiply, 300, 900)
    LIB.connect_material_expressions(cube_room, "", cube_final, "A")
    LIB.connect_material_expressions(clean, "", cube_final, "B")
    use_cubes = param(unreal.MaterialExpressionScalarParameter, "UseCubes", 0.0, 1550)
    room_colour = expr(material, unreal.MaterialExpressionLinearInterpolate, 450, 500)
    LIB.connect_material_expressions(node, "", room_colour, "A")
    LIB.connect_material_expressions(cube_final, "", room_colour, "B")
    LIB.connect_material_expressions(use_cubes, "", room_colour, "Alpha")
    # Clean glass: black base, specular 0.5 (F0 0.04), roughness 0.02; grime greys and roughens it.
    base = expr(material, unreal.MaterialExpressionMultiply, -500, 0)
    grime = expr(material, unreal.MaterialExpressionConstant3Vector, -700, -100,
                  constant=unreal.LinearColor(0.09, 0.085, 0.075, 1))
    LIB.connect_material_expressions(grime, "", base, "A")
    LIB.connect_material_expressions(node, "Dirt", base, "B")
    rough = expr(material, unreal.MaterialExpressionLinearInterpolate, -500, 150)
    LIB.connect_material_expressions(expr(material, unreal.MaterialExpressionConstant, -700, 120, r=0.02), "", rough, "A")
    LIB.connect_material_expressions(expr(material, unreal.MaterialExpressionConstant, -700, 200, r=0.45), "", rough, "B")
    LIB.connect_material_expressions(node, "Dirt", rough, "Alpha")
    LIB.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    LIB.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    LIB.connect_material_property(expr(material, unreal.MaterialExpressionConstant, -500, 300, r=0.5), "",
                                  unreal.MaterialProperty.MP_SPECULAR)
    LIB.connect_material_property(room_colour, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.recompile_material(material)
    ASSETS.save_asset(GLASS_MASTER, only_if_is_dirty=False)
    return "created"


FLAT_HLSL = r"""
// Flat slots still get a little life: slow value noise moves value and roughness, Wear R adds grime.
float3 I = floor(WP / 37.0);
float v = frac(sin(dot(I, float3(127.1, 311.7, 74.7))) * 43758.5453);
float dirt = saturate(VC * 0.8);
Rough = saturate(Roughness + (v - 0.5) * 0.08 + dirt * 0.3);
return lerp(Colour * (0.94 + 0.12 * v), float3(0.05, 0.045, 0.04), dirt * 0.6);
"""


def build_flat_master(force):
    """M_MI_Flat: untextured surfaces (chrome, aluminium, blinds, lenses, sign stand-ins)."""
    if ASSETS.does_asset_exist(FLAT_MASTER):
        if not force:
            return "exists"
        material = unreal.load_asset(FLAT_MASTER)
        LIB.delete_all_material_expressions(material)
    else:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "M_MI_Flat", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    wp = world_position(material, -1200, 0)
    vertex_colour = expr(material, unreal.MaterialExpressionVertexColor, -1200, 120)
    colour = expr(material, unreal.MaterialExpressionVectorParameter, -1200, 240, parameter_name="Colour",
                  default_value=unreal.LinearColor(0.5, 0.5, 0.5, 1))
    rough = expr(material, unreal.MaterialExpressionScalarParameter, -1200, 360, parameter_name="Roughness",
                 default_value=0.5)
    metal = expr(material, unreal.MaterialExpressionScalarParameter, -1200, 460, parameter_name="Metallic",
                 default_value=0.0)
    emissive = expr(material, unreal.MaterialExpressionScalarParameter, -1200, 560, parameter_name="EmissiveNits",
                    default_value=0.0)
    node = custom(material, -800, 200, FLAT_HLSL, ["WP", "VC", "Colour", "Roughness"],
                  unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["Rough"])
    LIB.connect_material_expressions(wp, "", node, "WP")
    LIB.connect_material_expressions(vertex_colour, "R", node, "VC")
    LIB.connect_material_expressions(colour, "", node, "Colour")
    LIB.connect_material_expressions(rough, "", node, "Roughness")
    glow = expr(material, unreal.MaterialExpressionMultiply, -500, 500)
    LIB.connect_material_expressions(colour, "", glow, "A")
    LIB.connect_material_expressions(emissive, "", glow, "B")
    LIB.connect_material_property(node, "", unreal.MaterialProperty.MP_BASE_COLOR)
    LIB.connect_material_property(node, "Rough", unreal.MaterialProperty.MP_ROUGHNESS)
    LIB.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
    LIB.connect_material_property(glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.recompile_material(material)
    ASSETS.save_asset(FLAT_MASTER, only_if_is_dirty=False)
    return "created"


DECAL_MASTER = MAT_DIR + "/M_MI_Decal"
DECAL_KINDS = ("Crack", "Patch", "Oil", "Gum", "Rust", "Stain", "Tyre")   # Kind parameter 0..6
# Procedural street storytelling in decal UV space (0..1); the coarse world position varies each placement.
DECAL_HLSL = r"""
float2 uv = UV;
float2 c = uv - 0.5;
float r = length(c) * 2.0;
float3 V = floor(WP / 397.0);
float seed = frac(sin(dot(V, float3(12.9898, 78.233, 37.719))) * 43758.5453);
float2 jitter = float2(seed, frac(seed * 7.13)) * 10.0;
// value noise in uv
float n1 = 0.0, amp = 0.5, freq = 4.0;
for (int o = 0; o < 4; o++)
{
    float2 P = uv * freq + jitter + o * 3.1;
    float2 I = floor(P), F = frac(P);
    F = F * F * (3.0 - 2.0 * F);
    float a = frac(sin(dot(I, float2(127.1, 311.7))) * 43758.5);
    float b = frac(sin(dot(I + float2(1, 0), float2(127.1, 311.7))) * 43758.5);
    float cc = frac(sin(dot(I + float2(0, 1), float2(127.1, 311.7))) * 43758.5);
    float d = frac(sin(dot(I + float2(1, 1), float2(127.1, 311.7))) * 43758.5);
    n1 += amp * lerp(lerp(a, b, F.x), lerp(cc, d, F.x), F.y);
    amp *= 0.5; freq *= 2.0;
}
float3 colour = float3(0.02, 0.02, 0.02);
float rough = 0.9;
float alpha = 0.0;
int k = (int)(Kind + 0.5);
if (k == 0)
{   // crack network: cell edges (F2 - F1) of a jittered grid, fading out from the centre
    float2 P = uv * 5.0 + jitter;
    float2 I = floor(P);
    float f1 = 9.0, f2 = 9.0;
    for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++)
    {
        float2 g = I + float2(x, y);
        float2 o = float2(frac(sin(dot(g, float2(269.5, 183.3))) * 43758.5), frac(sin(dot(g, float2(113.5, 271.9))) * 43758.5));
        float dd = length(g + o - P);
        if (dd < f1) { f2 = f1; f1 = dd; } else if (dd < f2) f2 = dd;
    }
    float edge = 1.0 - smoothstep(0.02, 0.06 + 0.04 * n1, f2 - f1);
    alpha = edge * saturate(1.3 - r * 1.2) * step(0.35, n1);
    colour = float3(0.015, 0.014, 0.013);
}
else if (k == 1)
{   // asphalt patch: a darker, smoother rectangle with a sealed seam
    float2 e = abs(c) * 2.0;
    float inside = step(max(e.x, e.y), 0.92 + 0.05 * n1);
    float seam = inside * smoothstep(0.82, 0.92, max(e.x, e.y));
    colour = lerp(float3(0.05, 0.05, 0.052), float3(0.012, 0.012, 0.012), seam) * (0.8 + 0.4 * n1);
    rough = lerp(0.82, 0.55, seam);
    alpha = inside * 0.92;
}
else if (k == 2)
{   // oil: an irregular blot, darker and slick in the middle
    float blot = saturate((0.75 + (n1 - 0.5) * 0.9 - r) * 4.0);
    colour = float3(0.01, 0.009, 0.008);
    rough = lerp(0.6, 0.18, blot);
    alpha = blot * 0.85;
}
else if (k == 3)
{   // gum and spots: sparse flattened discs on a 14 x 14 grid
    float2 P = uv * 14.0 + jitter;
    float2 I = floor(P);
    float h = frac(sin(dot(I, float2(41.3, 289.1))) * 43758.5);
    float2 o = float2(frac(h * 13.7), frac(h * 71.3)) * 0.6 + 0.2;
    float d = length(frac(P) - o);
    float rad = 0.04 + 0.06 * frac(h * 5.1);
    float spot = step(0.93, h) * (1.0 - smoothstep(rad * 0.7, rad, d));
    colour = (frac(h * 3.3) > 0.7) ? float3(0.12, 0.115, 0.11) : float3(0.03, 0.029, 0.028);
    rough = 0.55;
    alpha = spot;
}
else if (k == 4)
{   // rust streak: runs down from the top edge (decal Z up), narrowing and fading
    float x = abs(c.x) * 2.0;
    float run = saturate(1.0 - uv.y * (0.9 + 0.5 * n1));
    float lanes = smoothstep(0.65, 0.3, x + (n1 - 0.5) * 0.6);
    float streaks = 0.6 + 0.4 * frac(sin(floor(uv.x * 23.0 + jitter.x) * 91.7) * 4375.5);
    colour = lerp(float3(0.16, 0.06, 0.02), float3(0.07, 0.035, 0.02), n1);
    alpha = run * lanes * streaks * 0.75;
}
else if (k == 5)
{   // stain round a casting: a damp dark ring and silt
    float ring = saturate(1.0 - abs(r - 0.62) * 3.0) * (0.6 + 0.6 * n1);
    colour = float3(0.025, 0.024, 0.022);
    rough = 0.7;
    alpha = saturate(ring) * saturate(1.0 - r) * 1.6 * 0.6;
}
else
{   // tyre marks: two dark bands along U, broken up
    float band = smoothstep(0.1, 0.04, abs(abs(c.y) - 0.28));
    colour = float3(0.012, 0.012, 0.012);
    rough = 0.7;
    alpha = band * saturate((n1 - 0.25) * 2.0) * saturate(1.0 - abs(c.x) * 2.0) * 0.7;
}
Rough = rough;
Alpha = saturate(alpha);
return colour;
"""


def build_decal_master(force):
    """M_MI_Decal: deferred (DBuffer) decal with the procedural kinds of DECAL_HLSL."""
    if ASSETS.does_asset_exist(DECAL_MASTER):
        if not force:
            return "exists"
        material = unreal.load_asset(DECAL_MASTER)
        LIB.delete_all_material_expressions(material)
    else:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "M_MI_Decal", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    setp(material, "material_domain", unreal.MaterialDomain.MD_DEFERRED_DECAL)
    setp(material, "blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    uv = expr(material, unreal.MaterialExpressionTextureCoordinate, -1000, 0)
    wp = world_position(material, -1000, 120)
    kind = expr(material, unreal.MaterialExpressionScalarParameter, -1000, 260, parameter_name="Kind", default_value=0.0)
    node = custom(material, -600, 100, DECAL_HLSL, ["UV", "WP", "Kind"], unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                  ["Rough", "Alpha"])
    LIB.connect_material_expressions(uv, "", node, "UV")
    LIB.connect_material_expressions(wp, "", node, "WP")
    LIB.connect_material_expressions(kind, "", node, "Kind")
    LIB.connect_material_property(node, "", unreal.MaterialProperty.MP_BASE_COLOR)
    LIB.connect_material_property(node, "Rough", unreal.MaterialProperty.MP_ROUGHNESS)
    LIB.connect_material_property(node, "Alpha", unreal.MaterialProperty.MP_OPACITY)
    LIB.recompile_material(material)
    ASSETS.save_asset(DECAL_MASTER, only_if_is_dirty=False)
    return "created"


def make_decal_instance(kind, force):
    name = "MI_Decal_" + DECAL_KINDS[kind]
    instance = instance_of(name, DECAL_MASTER, force)
    if instance is None:
        return "exists"
    LIB.set_material_instance_scalar_parameter_value(instance, "Kind", float(kind))
    return finish_instance(instance, name)


def instance_of(name, parent_path, force):
    """Load or create the instance `name` under parent_path; None when it exists and force is off."""
    path = "%s/%s" % (MAT_DIR, name)
    if ASSETS.does_asset_exist(path):
        if not force:
            return None
        instance = unreal.load_asset(path)
    else:
        instance = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, MAT_DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    LIB.set_material_instance_parent(instance, unreal.load_asset(parent_path))
    return instance


def finish_instance(instance, name):
    LIB.update_material_instance(instance)
    ASSETS.save_asset("%s/%s" % (MAT_DIR, name), only_if_is_dirty=False)
    return "created"


def make_flat_instance(name, values, force):
    instance = instance_of(name, FLAT_MASTER, force)
    if instance is None:
        return "exists"
    colour, rough, metal, nits = values
    LIB.set_material_instance_vector_parameter_value(instance, "Colour", unreal.LinearColor(colour[0], colour[1], colour[2], 1))
    LIB.set_material_instance_scalar_parameter_value(instance, "Roughness", rough)
    LIB.set_material_instance_scalar_parameter_value(instance, "Metallic", metal)
    LIB.set_material_instance_scalar_parameter_value(instance, "EmissiveNits", nits)
    return finish_instance(instance, name)


def make_glass_instance(name, values, force):
    instance = instance_of(name, GLASS_MASTER, force)
    if instance is None:
        return "exists"
    LIB.set_material_instance_vector_parameter_value(instance, "Room", unreal.LinearColor(*(values["room"] + (0,))))
    LIB.set_material_instance_vector_parameter_value(instance, "Offset", unreal.LinearColor(*(values["offset"] + (0,))))
    for key, param in (("nits", "Nits"), ("shop", "Shop"), ("sill", "Sill")):
        LIB.set_material_instance_scalar_parameter_value(instance, param, values[key])
    # The baked rooms (mi_interiors.py), shops or homes, when they exist.
    rooms = INTERIOR_CUBES["shop" if values["shop"] > 0.5 else "home"]
    paths = ["%s/Interiors/TC_%s" % (ROOT, r) for r in rooms]
    if all(ASSETS.does_asset_exist(p) for p in paths):
        for cube_name, path in zip(("CubeA", "CubeB", "CubeC"), paths):
            LIB.set_material_instance_texture_parameter_value(instance, cube_name, unreal.load_asset(path))
        LIB.set_material_instance_scalar_parameter_value(instance, "UseCubes", 1.0)
        LIB.set_material_instance_scalar_parameter_value(instance, "CubeScale", values.get("cube_scale", 1.0))
    return finish_instance(instance, name)


def make_instance(name, set_name, tint=(1, 1, 1), blend_set=None, alpha_means=None, world_tile_m=None,
                  wear=1.0, force=False, roof_set=None, macro=None, windows=False, parent=None, emissive=None):
    path = "%s/%s" % (MAT_DIR, name)
    if ASSETS.does_asset_exist(path):
        if not force:
            return "exists"
        instance = unreal.load_asset(path)          # updated in place (meshes keep their references)
    else:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        instance = tools.create_asset(name, MAT_DIR, unreal.MaterialInstanceConstant,
                                      unreal.MaterialInstanceConstantFactoryNew())
    LIB.set_material_instance_parent(instance, unreal.load_asset(parent or MASTER))
    for kind in ("BC", "N", "ORM"):
        texture = unreal.load_asset(texture_path(set_name, kind)) if ASSETS.does_asset_exist(
            texture_path(set_name, kind)) else unreal.load_asset(FLAT_NORMAL if kind == "N" else BLACK_TEXTURE)
        LIB.set_material_instance_texture_parameter_value(instance, kind, texture)
        other = blend_set or roof_set
        second = unreal.load_asset(texture_path(other, kind)) if other and has_set(other) else texture
        LIB.set_material_instance_texture_parameter_value(instance, kind + "2", second)
    # Unique (baked) sets: no macro variation and no detail resample (their UVs are an atlas).
    macro = (wear > 0) if macro is None else macro
    LIB.set_material_instance_vector_parameter_value(instance, "Macro", unreal.LinearColor(
        1.0 if macro else 0.0, 1.0 if macro else 0.0, 0, 0))
    LIB.set_material_instance_vector_parameter_value(instance, "Windows", unreal.LinearColor(
        1.0 if windows else 0.0, 310.0, 310.0, 380.0))
    if ASSETS.does_asset_exist(texture_path(set_name, "E")):
        LIB.set_material_instance_texture_parameter_value(instance, "E", unreal.load_asset(texture_path(set_name, "E")))
        LIB.set_material_instance_scalar_parameter_value(instance, "EmissiveScale",
                                                         SIGN_NITS if emissive is None else emissive)
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
    yield "masked master", lambda: build_master(defaults, force, MASKED_MASTER, True)
    yield "glass master", lambda: build_glass_master(force)
    yield "flat master", lambda: build_flat_master(force)
    yield "car paint master", lambda: build_master(defaults, force, CARPAINT_MASTER, False, True)
    yield "decal master", lambda: build_decal_master(force)
    for kind in range(len(DECAL_KINDS)):
        yield "decal " + DECAL_KINDS[kind], (lambda k=kind: make_decal_instance(k, force))
    seen = set()
    for asset in art_assets(man).values():
        for slot in asset.get("material_slots", []):
            name = slot_instance_name(slot["slot"])
            if name in seen:
                continue
            seen.add(name)
            if name in GLASS_SLOTS or slot.get("workflow") == "glass":
                values = GLASS_SLOTS.get(name, GLASS_SLOTS["MI_Glass_Window"])
                yield "glass " + name, (lambda n=name, v=values: make_glass_instance(n, v, force))
                continue
            if name in FLAT_SLOTS or slot.get("workflow") in ("flat", "emissive", "procedural") or \
                    not has_set(slot["set"]):
                values = FLAT_SLOTS.get(name) or flat_values(slot)
                yield "flat " + name, (lambda n=name, v=values: make_flat_instance(n, v, force))
                continue
            set_name = slot["set"]
            tint = slot.get("tint") or (1, 1, 1)
            wear = 0.0 if slot.get("workflow") in ("unique", "sign", "decal") else 1.0   # unique sets carry wear baked
            parent = slot_parent(slot)
            if parent == CARPAINT_MASTER:
                tint = slot.get("paint_default") or tint
            # Vehicle sets carry the lit lamp colour in E: lamps are off by day.
            glow = 0.0 if set_name.startswith("Vehicle_") else None
            yield "instance " + name, (lambda n=name, s=set_name, t=tint, b=slot.get("blend_set_G"),
                                       a=slot.get("alpha_means"), w=wear, p=parent, g=glow:
                                       make_instance(n, s, t, b, a, None, w, force, parent=p, emissive=g))
    # One clear-coat paint instance per vehicle paint slot and props.json paint colour.
    for slot_name, colour in sorted(vehicle_paints()):
        set_name = paint_slot_set(man, slot_name)
        if set_name and has_set(set_name):
            yield "paint %s %s" % (slot_name, colour), (
                lambda n=paint_instance_name(slot_name, colour), s=set_name, t=tuple(srgb_to_linear(colour)):
                make_instance(n, s, t, None, None, None, 0.0, force, parent=CARPAINT_MASTER, emissive=0.0))
    # One awning cloth per shop colour (placements carry the shop's sRGB colour).
    for shop, tint in sorted(awning_tints().items()):
        yield "awning " + shop, (lambda n="MI_Fabric_ScanCanvas_" + shop, t=tint:
                                 make_instance(n, "TS_Fabric_ScanCanvas", t, None, "splash", None, 1.0, force))
    for name, set_name, tint in list(GREY_SURFACE.values()) + list(GROUND_SURFACE.values()) + \
            [(v[0], v[1], v[2]) for v in TAG_SURFACE.values()] + list(BACKDROP_SURFACE.values()):
        if name in seen:
            continue
        seen.add(name)
        if set_name is None:                       # flat (vehicle paint and glass stand-ins)
            yield "flat " + name, (lambda n=name, v=tint: make_flat_instance(n, v, force))
            continue
        if set_name == "glass":
            yield "glass " + name, (lambda n=name: make_glass_instance(n, GLASS_SLOTS["MI_Glass_Window"], force))
            continue
        roof = ROOF_SET if name in ROOFED else None
        windows = name in WINDOWED
        yield "instance " + name, (lambda n=name, s=set_name, t=tint, r=roof, w=windows:
                                   make_instance(n, s, t, None, None, set_tile_m(man, s), 0.0, force, r, True, w))


def slot_parent(slot):
    """Master of a textured slot: clear-coat paint, alpha-tested (cards, decal sheets, livery) or the surface."""
    name = slot["slot"]
    if (slot.get("shading") or "").startswith("clear-coat"):
        return CARPAINT_MASTER
    if slot.get("alpha") or slot.get("workflow") == "decal" or name.endswith("_Decals") or \
            "decal with alpha" in (slot.get("note") or ""):
        return MASKED_MASTER
    return MASTER


def flat_values(slot):
    """(colour, roughness, metallic, nits) of an untextured slot from its manifest note: the first #rrggbb (or the
    neon tube's emissive colour, greyed toward milky glass by day), 'metallic x', 'roughness x'; metals and lenses
    by their name."""
    name, note = slot["slot"], slot.get("note") or ""
    hexes = re.findall(r"#[0-9a-fA-F]{6}", note)
    colour, rough, metal, nits = SIGN_STAND_IN[0], 0.5, 0.0, 0.0
    if slot.get("emissive"):
        return (tuple(srgb_to_linear(slot["emissive"])), 0.15, 0.0, NEON_DAY_NITS)
    if hexes:
        colour = tuple(srgb_to_linear(hexes[0]))
    match = re.search(r"roughness ([\d.]+)", note)
    if match:
        rough = float(match.group(1))
    match = re.search(r"metallic ([\d.]+)", note)
    if match:
        metal = float(match.group(1))
    if name.startswith("MI_Metal_"):
        metal, rough = 1.0, (rough if match else 0.3)
        if not hexes:
            colour = {"MI_Metal_Brass": (0.78, 0.56, 0.24), "MI_Metal_Gold": (0.8, 0.57, 0.18)}.get(name, (0.85, 0.85, 0.86))
    elif name.startswith("MI_Lamp_") or name.startswith("MI_Glass_"):
        colour = tuple(c * 0.35 for c in colour) if hexes else (0.08, 0.08, 0.08)   # unlit lens by day
        rough = 0.1
    elif name.startswith("MI_Fruit_"):
        colour = {"MI_Fruit_Orange": (0.6, 0.2, 0.02), "MI_Fruit_Red": (0.45, 0.03, 0.02),
                  "MI_Fruit_RedDark": (0.2, 0.02, 0.02), "MI_Fruit_Yellow": (0.65, 0.5, 0.05),
                  "MI_Fruit_Lime": (0.2, 0.4, 0.04), "MI_Fruit_Purple": (0.1, 0.02, 0.08),
                  "MI_Fruit_Stem": (0.1, 0.12, 0.03)}.get(name, colour)
        rough = 0.35
    return (colour, rough, metal, nits)


def catalogue_table():
    return game_data(CATALOGUE_TABLE)["ids"]


def catalogue_entry(prop):
    """The art_catalogue.json entry for a props.json instance (its variant's override applied), or None."""
    entry = catalogue_table().get(prop["name"])
    if not entry or "meshes" not in entry:
        return None
    variant = (entry.get("variants") or {}).get(prop.get("variant") or "")
    return dict(entry, **variant) if variant else entry


def vehicle_paints():
    """{(paint slot, '#rrggbb')} for every props.json instance whose catalogue entry names a paint slot."""
    out = set()
    for prop in game_data("props")["instances"]["list"]:
        entry = catalogue_entry(prop)
        if entry and entry.get("paint") and prop.get("paint"):
            out.add((entry["paint"], prop["paint"].lower()))
    return out


def paint_slot_set(man, slot_name):
    for asset in man["assets"].values():
        for slot in asset.get("material_slots", []):
            if slot["slot"] == slot_name:
                return slot.get("set")
    return None


def paint_instance_name(slot_name, colour):
    return "%s_%s" % (slot_instance_name(slot_name), colour.lstrip("#").upper())


def placements():
    path = os.path.join(ART_IN, "placements", "buildings.json")
    return load_json(path) if os.path.exists(path) else {"instances": []}


def srgb_to_linear(hex_colour):
    out = []
    for k in (1, 3, 5):
        c = int(hex_colour[k:k + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return out


def awning_tints():
    """{shop: tint} for the awnings of the placements: the shop's cloth colour over the canvas scan's mean."""
    tints = {}
    for entry in placements()["instances"]:
        if entry.get("shop") and entry.get("tint"):
            colour = srgb_to_linear(entry["tint"])
            mean = manifest().get("texture_sets", {}).get("TS_Fabric_ScanCanvas", {}).get("albedo_mean") or AWNING_SCAN_MEAN
            tints[entry["shop"]] = tuple(c / m for c, m in zip(colour, mean))
    return tints


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
        spawn_box("Ground_Far", "Block/Ground", (0, 0, -12.0), (500000, 500000, 10.0), far)
        return "%d slabs and the far ground" % count
    yield "ground", ground_chunk

    # The facade kit on the street-facing buildings, the catalogue props that have a mesh.
    facade = placements()
    faced = {b["name"] for b in level["buildings"]["list"] if b["id"] in facade.get("buildings", {})}
    if faced:
        faced.add("bulkhead")            # the stair bulkheads on their roofs are kit modules too
    props = prop_placements(facade)
    placed_props = {entry["prop"] for entry in props}
    structures, structure_boxes = structure_placements(level)
    for building in sorted(facade.get("buildings", {})):
        yield "facade " + building, (lambda b=building: place_facade(facade, b))
    yield "props", lambda: place_props(props)
    yield "structures", lambda: place_structures(structures)
    modelled = structure_art()
    structure_boxes |= {c for entry in modelled for c in entry.get("colliders", [])}
    yield "structures (structures family)", lambda: place_structures(
        [(e["mesh"], tuple(e["location"]), e["yaw"], tuple(e.get("scale", (1.0, 1.0, 1.0)))) for e in modelled],
        "StructureArt")
    yield "gameplay previews", lambda: place_gameplay_previews(gameplay_previews(level))

    # Grey-box massing: every movement-blocking static collider the meshes above do not already draw. The colliders
    # of what the art now draws stay as invisible blocking boxes: the tuned cover and openings do not change.
    gameplay_props = {p["index"] for p in game_data("props")["instances"]["list"]
                      if (catalogue_table().get(p["name"]) or {}).get("gameplay")}
    boxes = [b for b in level["colliders"]["boxes"]
             if b["tag"] not in SKIP_COLLIDER_TAGS and b["blocks"]["movement"] and not b["flags"]["bulletOnly"]
             and b["owner"]["kind"] not in GAMEPLAY_OWNERS and b["owner"].get("prop") not in gameplay_props]

    def drawn_by_art(box):
        owner = box["owner"]
        return (owner["kind"] == "level" and box["tag"] in faced) or \
            (owner["kind"] == "prop" and owner.get("prop") in placed_props) or box["index"] in structure_boxes
    for start in range(0, len(boxes), 120):
        def grey_chunk(items=boxes[start:start + 120]):
            hidden = 0
            for box in items:
                name = GREY_SURFACE.get(box["surface"], GREY_SURFACE["other"])[0]
                if box["owner"]["kind"] == "level" and box["tag"] in TAG_SURFACE:
                    name = TAG_SURFACE[box["tag"]][0]
                material = unreal.load_asset("%s/%s" % (MAT_DIR, name))
                c, e = box["ue"]["center"], box["ue"]["extent"]
                art = drawn_by_art(box)
                actor = spawn_box("%s_%03d_%s" % ("Collision" if art else "Grey", box["index"], box["tag"].replace(" ", "_")),
                                  "Block/Collision" if art else "Block/GreyBox",
                                  (c["X"], c["Y"], c["Z"]), (e["X"], e["Y"], e["Z"]), material)
                if art:
                    component = actor.static_mesh_component
                    component.set_visibility(False)
                    component.set_hidden_in_game(True)
                    setp(component, "cast_shadow", False)
                    setp(component, "affect_distance_field_lighting", False)
                    hidden += 1
            return "%d boxes, %d of them invisible collision under art" % (len(items), hidden)
        yield "grey-box %d of %d" % (start, len(boxes)), grey_chunk

    yield "backdrop", lambda: build_backdrop(level, facade)
    yield "decals", lambda: place_decals(decal_placements(level, facade))

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


# ------------------------------------------------------------------------------------------- instanced art

def transform(location, yaw=0.0, scale=(1.0, 1.0, 1.0)):
    return unreal.Transform(unreal.Vector(*location), rotator(yaw=yaw), unreal.Vector(*scale))


def instance_holder(label, folder):
    """An empty static mesh actor whose root carries the instanced static mesh components."""
    actor = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0), rotator())
    actor.static_mesh_component.set_mobility(unreal.ComponentMobility.STATIC)
    return tag(actor, label, folder)


def add_instances(actor, mesh_path, transforms, material=None, collide=False):
    """One InstancedStaticMeshComponent on `actor` with `transforms` (world space), added the way the details panel
    adds a component (SubobjectDataSubsystem), so it is saved with the level."""
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    root = subsystem.k2_gather_subobject_data_for_instance(actor)[0]
    params = make_struct(unreal.AddNewSubobjectParams, parent_handle=root,
                         new_class=unreal.InstancedStaticMeshComponent)
    handle, reason = subsystem.add_new_subobject(params)
    data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
    component = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(data)
    if component is None:
        raise RuntimeError("cannot add an instanced mesh component: %s" % reason)
    subsystem.rename_subobject(handle, unreal.Text(mesh_path.rsplit("/", 1)[-1]))
    component.set_mobility(unreal.ComponentMobility.STATIC)
    component.set_static_mesh(unreal.load_asset(mesh_path))
    if material is not None:
        for index in range(component.get_num_materials()):
            component.set_material(index, material)
    if not collide:
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    component.add_instances(transforms, False, True)
    return component


def place_facade(facade, building):
    """Every module instance of one building, one instanced component per module (and per awning colour)."""
    groups = {}
    for entry in facade["instances"]:
        if entry["building"] != building:
            continue
        mesh = entry["mesh"]
        if not ASSETS.does_asset_exist("%s/%s" % (MESH_DIR, mesh)):
            groups.setdefault(("missing", mesh), []).append(entry)
            continue
        key = (mesh, entry.get("shop") if entry.get("tint") else None)
        scale = tuple(entry.get("scale", (1.0, 1.0, 1.0)))
        groups.setdefault(key, []).append(transform(entry["location"], entry["yaw"], scale))
    holder = instance_holder("Facade_" + building, "Block/Facades")
    count, missing = 0, []
    for (mesh, shop), items in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")):
        if mesh == "missing":
            missing.append(shop)
            continue
        material = None
        if shop:
            path = "%s/MI_Fabric_ScanCanvas_%s" % (MAT_DIR, shop)
            material = unreal.load_asset(path) if ASSETS.does_asset_exist(path) else None
        add_instances(holder, "%s/%s" % (MESH_DIR, mesh), items, material, collide=False)
        count += len(items)
    return "%d instances of %d modules%s" % (count, len(groups) - len(missing),
                                             (", missing meshes " + ",".join(missing)) if missing else "")


def prop_placements(facade):
    """[{prop, name, mesh, location, yaw, scale, paint, parts}] for the props.json instances whose catalogue id has
    meshes in Content/Data/art_catalogue.json (gameplay ids are the gameplay actors'). The first mesh's footprint
    centre goes where the catalogue shape's footprint centre is (pivots differ: the fire-escape balcony has its pivot
    at its left end on the wall). Props the facade kit already draws (its fire escapes) are skipped."""
    data = game_data("props")
    types = data["catalogue"]["types"]
    man = manifest()["assets"]
    balconies = [e for e in facade["instances"] if e["mesh"] == "SM_Facade_FireEscape_Balcony"]
    out, missing = [], set()
    for prop in data["instances"]["list"]:
        entry = catalogue_entry(prop)
        if entry is None:
            continue
        names = [n for n in entry["meshes"] if ASSETS.does_asset_exist("%s/%s" % (MESH_DIR, n))]
        if not names:
            missing.update(entry["meshes"])
            continue
        mesh = names[prop["seed"] % len(names)]
        ue = prop["ue"]
        yaw = ue["yaw"]
        scale = (ue["scale"]["X"], ue["scale"]["Y"], ue["scale"]["Z"])
        variants = types[prop["name"]]["variants"]
        want = variants[min(prop.get("shapeVariant") or 0, len(variants) - 1)]["bounds"]["ue"]["center"]
        box = man[mesh]["bounds_unreal_cm"]
        have = ((box["min"][0] + box["max"][0]) / 2.0, (box["min"][1] + box["max"][1]) / 2.0)
        dx, dy = (want["X"] - have[0]) * scale[0], (want["Y"] - have[1]) * scale[1]
        c, s_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        location = (ue["pos"]["X"] + c * dx - s_ * dy, ue["pos"]["Y"] + s_ * dx + c * dy, ue["pos"]["Z"])
        if prop["name"] == "fire_escape" and any(
                abs(b["location"][0] + 149.5 * math.cos(math.radians(b["yaw"])) - ue["pos"]["X"]) < 150 and
                abs(b["location"][1] - ue["pos"]["Y"]) < 150 and abs(b["location"][2] - ue["pos"]["Z"]) < 50
                for b in balconies):
            continue
        paint = None
        if entry.get("paint") and prop.get("paint"):
            paint = (entry["paint"], paint_instance_name(entry["paint"], prop["paint"].lower()))
        parts = []
        for part in entry.get("parts", []):
            at = part.get("at", (0, 0, 0))
            parts.append((part["mesh"], (location[0] + c * at[0] - s_ * at[1], location[1] + s_ * at[0] + c * at[1],
                                         location[2] + at[2]), yaw + part.get("yaw", 0.0)))
        out.append(dict(prop=prop["index"], name=prop["name"], mesh=mesh, location=location, yaw=yaw, scale=scale,
                        paint=paint, parts=parts))
    if missing:
        unreal.log_warning("build_block: catalogue meshes not imported: " + ", ".join(sorted(missing)))
    return out


def place_props(props):
    """One instanced component per mesh and paint colour (the paint slot overridden by the colour's instance)."""
    groups = {}
    for entry in props:
        groups.setdefault((entry["mesh"], entry["paint"]), []).append(
            transform(entry["location"], entry["yaw"], entry["scale"]))
        for mesh, location, yaw in entry["parts"]:
            groups.setdefault((mesh, None), []).append(transform(location, yaw, entry["scale"]))
    holder = instance_holder("Props", "Block/Props")
    for (mesh, paint), items in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1] or ("", ""))):
        component = add_instances(holder, "%s/%s" % (MESH_DIR, mesh), items, None, collide=False)
        if paint and ASSETS.does_asset_exist("%s/%s" % (MAT_DIR, paint[1])):
            component.set_material_by_name(paint[0], unreal.load_asset("%s/%s" % (MAT_DIR, paint[1])))
    names = sorted({e["name"] for e in props})
    return "%d props of %d catalogue ids, %d mesh and paint groups: %s" % (len(props), len(names), len(groups),
                                                                          ",".join(names))


GAMEPLAY_PREVIEW_NOTE = "editor preview of a gameplay actor: hidden in game (the actor draws itself at play)"


def gameplay_previews(level):
    """Static stand-ins of what the gameplay actors draw at play (explosives, reel cases, the IPX truck), from
    presentation.json, so that editor pictures of the level show them; hidden in game."""
    look = game_data("presentation")
    out = []

    def mesh_name(path):
        return path.rsplit("/", 1)[-1].split(".")[0] if path and path.startswith(MESH_DIR) else None
    for item in level["explosives"]["items"]:
        kind = look["explosives"].get(item["type"], {})
        name = mesh_name(kind.get("mesh"))
        if name:
            p = item["ue"]["pos"]
            out.append((name, (p["X"], p["Y"], p["Z"]), item["ue"].get("yaw", 0.0), 0.0))
    case = look["objectives"]["case"].get("art")
    if case:
        for k, objective in enumerate(level["objectives"]):
            p, yaw = objective["ue"]["pos"], objective["ue"].get("yaw", 0.0)
            c, s_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
            pieces = [(mesh_name(part["mesh"]), part.get("at", (0, 0, 0)), part.get("rot", (0, 0, 0))[1], 0.0)
                      for part in case["parts"]]
            pieces.append((mesh_name(case["reels"][k % len(case["reels"])]), (0, 0, 0), 0.0, 0.0))
            pieces.append((mesh_name(case["lid"]["mesh"]), case["lid"]["hinge"], 0.0, 0.0))
            for name, at, dyaw, roll in pieces:
                if name:
                    out.append((name, (p["X"] + c * at[0] - s_ * at[1], p["Y"] + s_ * at[0] + c * at[1],
                                       p.get("Z", 0) + at[2]), yaw + dyaw, roll))
    truck = look["objectives"]["truck"].get("art")
    if truck:
        t = level["extraction"]["truck"]["ue"]
        c, s_ = math.cos(math.radians(t["yaw"])), math.sin(math.radians(t["yaw"]))
        out.append((mesh_name(truck["body"]), (t["pos"]["X"], t["pos"]["Y"], t["pos"]["Z"]), t["yaw"], 0.0))
        for door in truck["doors"]:
            h = door["hinge"]
            out.append((mesh_name(door["mesh"]), (t["pos"]["X"] + c * h[0] - s_ * h[1],
                                                  t["pos"]["Y"] + s_ * h[0] + c * h[1], t["pos"]["Z"] + h[2]),
                        t["yaw"], 0.0))
    return [o for o in out if o[0] and ASSETS.does_asset_exist("%s/%s" % (MESH_DIR, o[0]))]


def place_gameplay_previews(items):
    for k, (mesh, location, yaw, roll) in enumerate(items):
        actor = spawn_mesh("%s/%s" % (MESH_DIR, mesh), "Preview_%02d_%s" % (k, mesh), "Block/GameplayPreview",
                           location, yaw)
        actor.set_actor_hidden_in_game(True)
        actor.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return "%d preview meshes (%s)" % (len(items), GAMEPLAY_PREVIEW_NOTE)


# Wall openings of the auto body shop (05-level 2.6.2): opening width x height -> (wall module, pier, door module).
OPENINGS = {(600, 430): ("SM_Furn_BlockWall_Opening_600x430", 20, "SM_Furn_RollUpDoor_600x430_Open"),
            (380, 350): ("SM_Furn_BlockWall_Opening_380x350", 20, "SM_Furn_RollUpDoor_380x350_Open"),
            (200, 250): ("SM_Furn_BlockWall_Door_200x250", 40, None)}


def placed_at_note(mesh):
    """The Unreal location a module's manifest note gives ("place at Blender (x, y, z)")."""
    notes = manifest()["assets"].get(mesh, {}).get("notes") or ""
    match = re.search(r"place at Blender \(([-\d.]+), ([-\d.]+), ([-\d.]+)\)", notes)
    if not match:
        return None
    x, y, z = (float(v) for v in match.groups())
    return (x * 100.0, -y * 100.0, z * 100.0)


def wall_runs(boxes):
    """Thin collider boxes as runs: (axis 'x' or 'y', line coordinate of the outer face, start, end, zmin, zmax,
    index), the outer face being the side away from the centre of all of them."""
    xs = [b["ue"]["center"]["X"] for b in boxes]
    ys = [b["ue"]["center"]["Y"] for b in boxes]
    cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    runs = []
    for b in boxes:
        mn, mx = b["ue"]["min"], b["ue"]["max"]
        if mx["X"] - mn["X"] >= mx["Y"] - mn["Y"]:
            line = mx["Y"] if b["ue"]["center"]["Y"] > cy else mn["Y"]
            runs.append(("x", line, mn["X"], mx["X"], mn["Z"], mx["Z"], b["index"], line > cy))
        else:
            line = mx["X"] if b["ue"]["center"]["X"] > cx else mn["X"]
            runs.append(("y", line, mn["Y"], mx["Y"], mn["Z"], mx["Z"], b["index"], line > cx))
    return runs


def run_transform(axis, line, along, positive_side):
    """Location and yaw of a module whose pivot is the bottom-left of its outer face (+Y local outward, running +X)
    for a run along `axis`; the outer face looks toward +axis' normal when positive_side."""
    if axis == "x":
        # outer face toward +Y: yaw 0 runs +X; toward -Y: yaw 180 runs -X (pivot at the run's far end)
        return ((along, line, 0.0), 0.0) if positive_side else ((along, line, 0.0), 180.0)
    # outer face toward +X: yaw -90 (local +Y -> +X) runs -Y; toward -X: yaw 90 runs +Y
    return ((line, along, 0.0), -90.0) if positive_side else ((line, along, 0.0), 90.0)


def tile(axis, line, start, end, positive_side, mesh, width, z=0.0, scale_z=1.0):
    """Modules of `width` from start to end (the last scaled so the run closes exactly), as (mesh, loc, yaw, scale)."""
    out = []
    length = end - start
    if length < 5:
        return out
    count = max(1, int(math.ceil(length / width - 0.05)))
    k = length / (count * width)
    for i in range(count):
        a, b = start + i * width * k, start + (i + 1) * width * k
        # The pivot is the module's left end seen from outside: start of the run going +, its end going -.
        positive_run = (axis == "x" and positive_side) or (axis == "y" and not positive_side)
        loc, yaw = run_transform(axis, line, a if positive_run else b, positive_side)
        out.append((mesh, (loc[0], loc[1], z), yaw, (k, 1.0, scale_z)))
    return out


def structure_placements(level):
    """Furniture-family modules for the level structures that have them: the sidewalk shed and its stair (at the
    manifest's placement), the auto body shop's block walls with their openings and roll-up doors, the Cage's
    plinths and chain-link. Returns (instances, collider indices they draw)."""
    have = lambda mesh: ASSETS.does_asset_exist("%s/%s" % (MESH_DIR, mesh))
    boxes = level["colliders"]["boxes"]
    out, drawn = [], set()
    # Sidewalk shed over the south sidewalk in front of S3, and its stair.
    for mesh, tags in (("SM_Furn_SidewalkShed", ("shed-deck", "shed-post")), ("SM_Furn_ShedStair", ("shed-stair",))):
        at = placed_at_note(mesh)
        if at and have(mesh):
            out.append((mesh, at, 0.0, (1.0, 1.0, 1.0)))
            drawn |= {b["index"] for b in boxes if b["tag"] in tags}
    # The auto body shop: openings first (a collider that starts above the ground over a gap), then plain wall.
    walls = [b for b in boxes if b["tag"] == "shop-wall" and b["owner"]["kind"] == "level"]
    if walls and have("SM_Furn_BlockWall_200"):
        runs = wall_runs(walls)
        cut = {}
        for axis, line, a, b, z0, z1, index, positive in runs:
            if z0 <= 1:
                continue
            key = min(OPENINGS, key=lambda o: abs(o[0] - (b - a)) + abs(o[1] - z0))
            if abs(key[0] - (b - a)) > 10 or abs(key[1] - z0) > 10 or (axis, line, a) in cut:
                continue
            module, pier, door = OPENINGS[key]
            cut[(axis, line, a)] = (a - pier, b + pier)
            out.extend(tile(axis, line, a - pier, a - pier + manifest_width(module), positive, module,
                            manifest_width(module)))
            if door and have(door):
                out.extend(tile(axis, line, a, a + key[0], positive, door, key[0]))
        for axis, line, a, b, z0, z1, index, positive in runs:
            drawn.add(index)
            if z0 > 1:
                continue
            pieces = [(a, b)]
            for (cut_axis, cut_line, _), (c0, c1) in cut.items():
                if cut_axis != axis or abs(cut_line - line) > 1:
                    continue
                pieces = [p for q in pieces for p in ((q[0], min(q[1], c0)), (max(q[0], c1), q[1])) if p[1] - p[0] > 1]
            for p0, p1 in pieces:
                out.extend(tile(axis, line, p0, p1, positive, "SM_Furn_BlockWall_200", 200.0))
    # Rolling scaffolds: a chain-link enclosure on all four sides of the collider (the tower is fenced off).
    for scaffold in [b for b in boxes if b["tag"] == "scaffold" and b["owner"]["kind"] == "level"]:
        mn, mx = scaffold["ue"]["min"], scaffold["ue"]["max"]
        if not have("SM_Furn_ChainLink_300x400"):
            break
        k = (mx["Z"] - mn["Z"]) / 400.0
        for axis, line, a, b, positive in (("x", mn["Y"], mn["X"], mx["X"], False), ("x", mx["Y"], mn["X"], mx["X"], True),
                                           ("y", mn["X"], mn["Y"], mx["Y"], False), ("y", mx["X"], mn["Y"], mx["Y"], True)):
            out.extend(tile(axis, line, a, b, positive, "SM_Furn_ChainLink_300x400", 300.0, mn["Z"], k))
        drawn.add(scaffold["index"])

    # Fences on the line of a thin collider: the east roadblock and the alley gate (chain-link to the collider's
    # height), the tyre cage (chain-link round it, tyre stacks inside), the lot's low walls (concrete knee wall).
    def run_of(b):
        mn, mx = b["ue"]["min"], b["ue"]["max"]
        along_x = mx["X"] - mn["X"] >= mx["Y"] - mn["Y"]
        line = (mn["Y"] + mx["Y"]) / 2.0 if along_x else (mn["X"] + mx["X"]) / 2.0
        a, e = (mn["X"], mx["X"]) if along_x else (mn["Y"], mx["Y"])
        return ("x" if along_x else "y"), line, a, e, mn["Z"], mx["Z"]
    for b in [b for b in boxes if b["owner"]["kind"] == "level" and b["tag"] in ("roadblock", "alley-gate")]:
        if not have("SM_Furn_ChainLink_250x260"):
            break
        axis, line, a, e, z0, z1 = run_of(b)
        out.extend(tile(axis, line, a, e, True, "SM_Furn_ChainLink_250x260", 250.0, z0, (z1 - z0) / 260.0))
        if b["tag"] == "roadblock" and z0 < 1 and have("SM_Street_JerseyBarrier"):
            # Jersey barriers in front of the fence where it crosses the road (west side).
            for k in range(int((e - a) // 300)):
                out.append(("SM_Street_JerseyBarrier", (line - 45.0, a + 150.0 + k * 300.0 + ((e - a) % 300) / 2.0, 0.0),
                            90.0, (1.0, 1.0, 1.0)))
        drawn.add(b["index"])
    for cage in [b for b in boxes if b["tag"] == "tyre-cage" and b["owner"]["kind"] == "level"]:
        mn, mx = cage["ue"]["min"], cage["ue"]["max"]
        if not have("SM_Furn_ChainLink_240x250"):
            break
        k = (mx["Z"] - mn["Z"]) / 250.0
        for axis, line, a, e, positive in (("x", mn["Y"], mn["X"], mx["X"], False), ("x", mx["Y"], mn["X"], mx["X"], True),
                                           ("y", mn["X"], mn["Y"], mx["Y"], False), ("y", mx["X"], mn["Y"], mx["Y"], True)):
            out.extend(tile(axis, line, a, e, positive, "SM_Furn_ChainLink_240x250", 240.0, mn["Z"], k))
        if have("SM_Prop_TireStack") and have("SM_Prop_TireStack_B"):
            for i, (fx, fy) in enumerate(((0.3, 0.3), (0.7, 0.3), (0.3, 0.7), (0.7, 0.7))):
                out.append(("SM_Prop_TireStack" if i % 2 == 0 else "SM_Prop_TireStack_B",
                            (mn["X"] + fx * (mx["X"] - mn["X"]), mn["Y"] + fy * (mx["Y"] - mn["Y"]), mn["Z"]),
                            i * 37.0, (1.0, 1.0, 1.0)))
        drawn.add(cage["index"])
    for wall in [b for b in boxes if b["tag"] == "lot-wall" and b["owner"]["kind"] == "level"]:
        if not have("SM_Furn_CagePlinth_300"):
            break
        axis, line, a, e, z0, z1 = run_of(wall)
        out.extend(tile(axis, line, a, e, True, "SM_Furn_CagePlinth_300", 300.0, z0, (z1 - z0) / 50.0))
        drawn.add(wall["index"])
    for post in [b for b in boxes if b["tag"] == "lot-gate" and b["owner"]["kind"] == "level"]:
        if have("SM_Furn_Bollard"):
            mn, mx = post["ue"]["min"], post["ue"]["max"]
            out.append(("SM_Furn_Bollard", ((mn["X"] + mx["X"]) / 2.0, (mn["Y"] + mx["Y"]) / 2.0, mn["Z"]), 0.0,
                        ((mx["X"] - mn["X"]) / 20.0, (mx["Y"] - mn["Y"]) / 20.0, (mx["Z"] - mn["Z"]) / 100.0)))
            drawn.add(post["index"])
    # Invisible player blockers (seals, the stair railing's upper part) and the shed's parapet (the shed draws it).
    drawn |= {b["index"] for b in boxes if b["tag"] in ("seal", "railing")}
    drawn |= {534, 535, 536} & {b["index"] for b in boxes if b["tag"] == "hoarding"}
    # The Cage: concrete knee walls, chain-link panels on them, an end post closing each run.
    for plinth in [b for b in boxes if b["tag"] == "cage-plinth"]:
        mn, mx = plinth["ue"]["min"], plinth["ue"]["max"]
        fence = [b for b in boxes if b["tag"] == "cage-fence" and abs(b["ue"]["min"]["X"] - mn["X"]) < 1
                 and abs(b["ue"]["min"]["Y"] - mn["Y"]) < 1]
        along_x = mx["X"] - mn["X"] >= mx["Y"] - mn["Y"]
        axis = "x" if along_x else "y"
        line = (mn["Y"] + mx["Y"]) / 2.0 if along_x else (mn["X"] + mx["X"]) / 2.0
        a, b = (mn["X"], mx["X"]) if along_x else (mn["Y"], mx["Y"])
        top = mx["Z"]
        if have("SM_Furn_CagePlinth_300"):
            out.extend(tile(axis, line, a, b, along_x, "SM_Furn_CagePlinth_300", 300.0, 0.0, top / 50.0))
            drawn.add(plinth["index"])
        if fence and have("SM_Furn_ChainLink_300x350"):
            out.extend(tile(axis, line, a, b, along_x, "SM_Furn_ChainLink_300x350", 300.0, top))
            end_loc, end_yaw = run_transform(axis, line, b, along_x)
            out.append(("SM_Furn_ChainLink_EndPost_350", (end_loc[0], end_loc[1], top), end_yaw + 180.0,
                        (1.0, 1.0, 1.0)))
            drawn |= {f["index"] for f in fence}
    return out, drawn


def manifest_width(mesh):
    box = manifest()["assets"][mesh]["bounds_unreal_cm"]
    return box["max"][0] - max(box["min"][0], 0.0)


def structure_art():
    """The structures family's placements (art-in/placements/structures.json), meshes that were imported."""
    path = os.path.join(ART_IN, "placements", "structures.json")
    items = load_json(path)["instances"] if os.path.exists(path) else []
    return [e for e in items if ASSETS.does_asset_exist("%s/%s" % (MESH_DIR, e["mesh"]))]


def place_structures(items, label="Structures"):
    groups = {}
    for mesh, location, yaw, scale in items:
        groups.setdefault(mesh, []).append(transform(location, yaw, scale))
    holder = instance_holder(label, "Block/Structures")
    for mesh, transforms in sorted(groups.items()):
        add_instances(holder, "%s/%s" % (MESH_DIR, mesh), transforms, None, collide=False)
    return "%d instances: %s" % (len(items), ", ".join("%s x%d" % (m, len(t)) for m, t in sorted(groups.items())))


def decal_placements(level, facade):
    """Street storytelling placed by rule (seeded, so every build is the same): cracks and patches in the road, oil
    and tyre marks in the parking lanes by the kerb, gum on the sidewalks, stains round the manholes, leaks on the
    road under the El's deck edges and rails, rust streaks under a share of the window sills. Returns
    [(kind, location, rotation (pitch, yaw, roll), size (depth, width, height))]."""
    rng = random.Random(4242)
    bounds = level["bounds"]["ue"]
    x0, x1 = bounds["minX"] + 100, bounds["maxX"] - 100
    down = -90.0
    out = []
    for k in range(22):                                   # cracks in the travel lanes
        size = rng.uniform(220, 420)
        out.append((0, (rng.uniform(x0, x1), rng.uniform(-480, 480), 0), (down, rng.uniform(0, 360), 0), (40, size, size)))
    for k in range(7):                                    # patches
        out.append((1, (rng.uniform(x0, x1), rng.uniform(-450, 450), 0), (down, rng.choice((0, 90)), 0),
                    (40, rng.uniform(120, 260), rng.uniform(150, 420))))
    for side in (-1, 1):                                  # parking lanes by the kerb (gutter at 700)
        for k in range(10):
            out.append((2, (rng.uniform(x0, x1), side * rng.uniform(520, 660), 0), (down, rng.uniform(0, 360), 0),
                        (40, rng.uniform(80, 170), rng.uniform(80, 170))))
        for k in range(5):
            out.append((6, (rng.uniform(x0, x1), side * rng.uniform(480, 640), 0), (down, rng.uniform(-8, 8), 0),
                        (40, rng.uniform(300, 600), 160)))
        x = x0                                            # gum on the sidewalk, one patch every 3 to 5 m
        while x < x1:
            out.append((3, (x, side * rng.uniform(780, 1020), 15), (down, rng.uniform(0, 360), 0), (40, 300, 300)))
            x += rng.uniform(300, 500)
    for prop in game_data("props")["instances"]["list"]:  # stains round the castings
        if prop["name"] == "manhole":
            p = prop["ue"]["pos"]
            out.append((5, (p["X"], p["Y"], 0), (down, rng.uniform(0, 360), 0), (40, 230, 230)))
    deck = level["el"]["deck"]["ue"]                      # leaks under the deck edges and the rails
    for y in (deck["minY"] + 20, deck["maxY"] - 20) + tuple(deck["tracksY"]):
        for k in range(6):
            out.append((5 if k % 2 else 2, (rng.uniform(x0, x1), y + rng.uniform(-40, 40), 0),
                        (down, rng.uniform(0, 360), 0), (40, rng.uniform(70, 140), rng.uniform(70, 140))))
    for entry in facade["instances"]:                     # rust streaks under one sill in four
        if not entry["mesh"].startswith("SM_Facade_BayWindow") or rng.random() > 0.25:
            continue
        yaw = entry["yaw"]
        c, s_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        lx, ly = 155.0 + rng.uniform(-30, 30), 0.0
        loc = (entry["location"][0] + c * lx - s_ * ly, entry["location"][1] + s_ * lx + c * ly,
               entry["location"][2] + 60 - 75)
        out.append((4, loc, (0.0, yaw - 90.0, 0.0), (30, rng.uniform(40, 90), 150)))
    return out


def place_decals(items):
    materials = {k: unreal.load_asset("%s/MI_Decal_%s" % (MAT_DIR, DECAL_KINDS[k])) for k in range(len(DECAL_KINDS))}
    for n, (kind, location, rot, size) in enumerate(items):
        actor = ACTORS.spawn_actor_from_class(unreal.DecalActor, unreal.Vector(*location), rotator(*rot))
        component = actor.decal
        component.set_decal_material(materials[kind])
        setp(component, "decal_size", unreal.Vector(*size))
        tag(actor, "Decal_%s_%03d" % (DECAL_KINDS[kind], n), "Block/Decals")
    counts = {}
    for kind, *_ in items:
        counts[DECAL_KINDS[kind]] = counts.get(DECAL_KINDS[kind], 0) + 1
    return "%d decals: %s" % (len(items), ", ".join("%s %d" % kv for kv in sorted(counts.items())))


def build_backdrop(level, facade):
    """What the player sees past the bounds: the avenue's own buildings continuing east and west, the neighbours'
    backs, then a distant skyline in the haze. Deterministic (seeded) masses in five scanned brick and concrete
    finishes (world-projected, window grid, tar roofs), each with a parapet and, near, roof clutter (water tanks,
    stair bulkheads, condensers); no collision: nobody reaches them."""
    rng = random.Random(1937)
    finishes = ("brick", "brown", "buff", "dark", "concrete")
    bounds = level["bounds"]["ue"]
    masses = []          # (finish, centre, half extent)
    # The avenue continues: street walls from the bounds out to 450 m, lots 8 to 30 m wide, 2 to 6 storeys.
    for side in (-1, 1):
        for direction in (-1, 1):
            x = bounds["maxX"] if direction > 0 else bounds["minX"]
            while abs(x) < BACKDROP_AVENUE_CM:
                width = rng.uniform(800, 3000)
                storeys = rng.randint(2, 6)
                height = 380 + 310 * (storeys - 1) + 90
                depth = rng.uniform(1500, 2500)
                x0, x1 = (x, x + width) if direction > 0 else (x - width, x)
                y0 = 1100 * side
                centre = ((x0 + x1) / 2.0, y0 + side * depth / 2.0, height / 2.0)
                masses.append((rng.choice(finishes[:4]), centre, ((x1 - x0) / 2.0 - 10, depth / 2.0, height / 2.0)))
                x = x1 if direction > 0 else x0
    # The blocks behind: rows of 4 to 8 storeys out to 300 m, avenue gap kept clear.
    for k in range(260):
        cx, cy = rng.uniform(-30000, 30000), rng.uniform(-30000, 30000)
        if abs(cy) < 4000 + rng.uniform(0, 1500) or (abs(cx) < 5200 and abs(cy) < 5200):
            continue
        storeys = rng.randint(4, 8) if math.hypot(cx, cy) < 15000 else rng.randint(6, 30)
        height = 310 * storeys + 400
        masses.append((rng.choice(finishes), (cx, cy, height / 2.0),
                       (rng.uniform(800, 2500), rng.uniform(800, 2500), height / 2.0)))
    # A distant skyline to the west and south-west, 2.5 to 4.5 km off: towers 40 to 300 m.
    for k in range(90):
        angle = math.radians(rng.uniform(150, 235))
        distance = rng.uniform(250000, 450000)
        height = rng.uniform(8000, 30000) if rng.random() < 0.35 else rng.uniform(4000, 12000)
        cx, cy = math.cos(angle) * distance, -math.sin(angle) * distance
        masses.append((rng.choice(("concrete", "buff", "concrete")), (cx, cy, height / 2.0),
                       (rng.uniform(1500, 4000), rng.uniform(1500, 4000), height / 2.0)))
    groups = {f: [] for f in finishes}
    props = {}
    for finish, c, e in masses:
        groups[finish].append(transform(c, 0.0, (e[0] / 50.0, e[1] / 50.0, e[2] / 50.0)))
        top = c[2] + e[2]
        if math.hypot(c[0], c[1]) > 150000:
            continue
        # Parapet: a 30 cm wall 90 cm high round the roof edge.
        for px, py, ex, ey in ((c[0], c[1] - e[1] + 15, e[0], 15), (c[0], c[1] + e[1] - 15, e[0], 15),
                               (c[0] - e[0] + 15, c[1], 15, e[1] - 30), (c[0] + e[0] - 15, c[1], 15, e[1] - 30)):
            groups[finish].append(transform((px, py, top + 45), 0.0, (ex / 50.0, ey / 50.0, 0.9)))
        if math.hypot(c[0], c[1]) > 30000 or e[0] < 500 or e[1] < 500:
            continue
        for mesh, chance in BACKDROP_ROOF_PROPS:
            if rng.random() < chance:
                at = (c[0] + rng.uniform(-0.6, 0.6) * (e[0] - 250), c[1] + rng.uniform(-0.6, 0.6) * (e[1] - 250),
                      top + (34 if "Air" in mesh else 0))
                props.setdefault(mesh, []).append(transform(at, rng.choice((0.0, 90.0, 180.0, 270.0))))
    holder = instance_holder("Backdrop", "Block/Backdrop")
    for finish, transforms in groups.items():
        material = unreal.load_asset("%s/%s" % (MAT_DIR, BACKDROP_SURFACE[finish][0]))
        add_instances(holder, CUBE.split(".")[0], transforms, material)
    for mesh, transforms in sorted(props.items()):
        if ASSETS.does_asset_exist("%s/%s" % (MESH_DIR, mesh)):
            add_instances(holder, "%s/%s" % (MESH_DIR, mesh), transforms, None)
    return "%d masses in %d finishes with parapets, roof props %s" % (
        len(masses), len(finishes), ", ".join("%s x%d" % (m, len(t)) for m, t in sorted(props.items())))


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
    setp(light, "volumetric_scattering_intensity", SUN_SHAFTS)      # shafts through the El ties in the haze
    setp(light, "contact_shadow_length", CONTACT_SHADOW)            # bolts, kerbs and sills keep a dark line
    setp(light, "cast_cloud_shadows", True)

    # A clear afternoon with a few cumulus: the engine's volumetric cloud layer at low cover.
    clouds = spawn_class(unreal.VolumetricCloud, "Clouds", "Block/Light")
    cloud_component = clouds.get_component_by_class(unreal.VolumetricCloudComponent)
    cloud_material = unreal.load_asset(CLOUD_MATERIAL)
    if cloud_material is not None:
        setp(cloud_component, "material", cloud_material)
    for name, value in CLOUD_LAYER.items():
        setp(cloud_component, name, value)

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
    setp(fog_component, "volumetric_fog_extinction_scale", FOG_VOLUME_EXTINCTION)

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
        ("local_exposure_shadow_contrast_scale", LOCAL_SHADOW_CONTRAST),
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

def interior_units(force):
    import importlib
    import mi_interiors
    importlib.reload(mi_interiors)
    return mi_interiors.interior_units(force)


STEPS = {"textures": texture_units, "materials": material_units, "meshes": mesh_units, "interiors": interior_units,
         "level": level_units}
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
