"""Bring the first-person and enemy art into the GAME project (/project/ue/repo-gameplay), headless:

    bash tools/box/fp/import-chars.sh [arms|goons|guns|fx|all]     (the game project's editor stopped)

Inputs: /project/ue/fp-in (tools/box/fp/fp-art.sh pack / put / unpack). Re-runnable: every asset is replaced in place
(same paths), so a re-export by the character agents reaches the game with no data change.

  arms   /Game/Characters/RuleArms/SK_RuleArms on SK_Mannequin (bare tattooed arms), LOD 0 keeps the exported normals,
         T_RuleArms_Skin_{BC,N,ORM}, M_RuleArms_Skin (subsurface profile SP_RuleSkin), M_RuleArms_Nail, the silver
         bracelet SM_Character_RuleBracelet (+ the watch, not worn) with its rest placement printed for presentation.json
  goons  /Game/Characters/Goons/SK_Goon_{Hoodie,Puffer,Tracksuit} with mi_chars.setup_goons (Cloth shading model,
         Recompute Normals off, the fibre detail normal)
  guns   /Game/Weapons/Nine/SK_Nine (own skeleton, saved) + SM_Weapon_NineMagazine(_TopRound), /Game/Weapons/GoonSMG/
         SM_Weapon_GoonSMG(+_Magazine), /Game/Characters/Buzzard/SK_Buzzard, and the CHOPPER's own finish:
         /Game/Weapons/Chopper/M_MI_PackPaint + MI_Chopper_DarkEarth on the pack's 01 / 03 sets (the pack's own
         instances are left alone: SHORTY keeps them)
  fx     /Game/FX: the effect materials the game's UMIEffects spawns (flash, smoke, tracer, decals, brass, debris)
Nothing made here is committed (Epic skeleton, Fab pack): the game falls back to the templates without it.
"""
import json
import os
import sys

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "chars"))
import mi_chars as C  # noqa: E402  (the character agent's helpers, used as they are)

IN = os.environ.get("MI_FP_IN", "/project/ue/fp-in")
ASSETS = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MEL = unreal.MaterialEditingLibrary
REPORT = {}


def _set(o, **kw):
    for k, v in kw.items():
        o.set_editor_property(k, v)


def _material(path):
    d, n = path.rsplit("/", 1)
    if ASSETS.does_asset_exist(path):
        m = unreal.load_asset(path)
        MEL.delete_all_material_expressions(m)      # rebuilt in place: instances keep their parent
        return m
    return TOOLS.create_asset(n, d, unreal.Material, unreal.MaterialFactoryNew())


def _expr(m, cls, x, y, **kw):
    n = MEL.create_material_expression(m, cls, x, y)
    for k, v in kw.items():
        n.set_editor_property(k, v)
    return n


def _scalar(m, name, v, x, y):
    return _expr(m, unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=float(v))


def _vector(m, name, rgb, x, y):
    return _expr(m, unreal.MaterialExpressionVectorParameter, x, y, parameter_name=name,
                 default_value=unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))


def _custom(m, x, y, code, inputs, out=unreal.CustomMaterialOutputType.CMOT_FLOAT1, extra=()):
    n = _expr(m, unreal.MaterialExpressionCustom, x, y, code=code, output_type=out)
    ins = []
    for name in inputs:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", name)
        ins.append(ci)
    n.set_editor_property("inputs", ins)
    if extra:
        outs = []
        for name in extra:
            co = unreal.CustomOutput()
            co.set_editor_property("output_name", name)
            co.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT1)
            outs.append(co)
        n.set_editor_property("additional_outputs", outs)
    return n


def _finish(m, path):
    MEL.recompile_material(m)
    ASSETS.save_asset(path, only_if_is_dirty=False)
    return path


def _tex(m, path, x, y, kind):
    n = _expr(m, unreal.MaterialExpressionTextureSample, x, y)
    n.texture = unreal.load_asset(path)
    n.sampler_type = {"color": unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
                      "normal": unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
                      "masks": unreal.MaterialSamplerType.SAMPLERTYPE_MASKS}[kind]
    return n


def _surface(path, tex, set_name, skeletal=True, emissive=False):
    """BC / ORM / N (OpenGL sets: green flipped on import) [+ E] on the default lit model."""
    m = _material(path)
    bc = _tex(m, "%s/T_%s_BC" % (tex, set_name), -600, -200, "color")
    orm = _tex(m, "%s/T_%s_ORM" % (tex, set_name), -600, 100, "masks")
    nm = _tex(m, "%s/T_%s_N" % (tex, set_name), -600, 400, "normal")
    MEL.connect_material_property(bc, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.connect_material_property(orm, "G", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(orm, "B", unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(nm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    if emissive and ASSETS.does_asset_exist("%s/T_%s_E" % (tex, set_name)):
        e = _tex(m, "%s/T_%s_E" % (tex, set_name), -600, 700, "color")
        MEL.connect_material_property(e, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if skeletal:
        _set(m, used_with_skeletal_mesh=True)
    return _finish(m, path)


def _import_mesh(glb, dest, name, skeletal):
    p = unreal.InterchangeGenericAssetsPipeline()
    _set(p.material_pipeline, import_materials=False)
    _set(p.material_pipeline.texture_pipeline, import_textures=False)
    _set(p.mesh_pipeline, import_static_meshes=not skeletal, import_skeletal_meshes=skeletal, create_physics_asset=False)
    if not skeletal:
        _set(p.mesh_pipeline, combine_static_meshes_behavior=unreal.InterchangeCombineStaticMeshesBehavior.ALL)
    _set(p.animation_pipeline, import_animations=False)
    p.set_editor_property("asset_name", name)
    prm = unreal.ImportAssetParameters()
    _set(prm, is_automated=True, replace_existing=True, override_pipelines=[unreal.SoftObjectPath(p.get_path_name())])
    unreal.InterchangeManager.get_interchange_manager_scripted().import_asset(
        dest, unreal.InterchangeManager.create_source_data(glb), prm)
    path = dest + "/" + name
    if skeletal:
        sk = unreal.load_asset(path)
        if sk is not None and sk.skeleton is not None:
            ASSETS.save_loaded_asset(sk.skeleton)   # the importer leaves a new skeleton unsaved (ANIMATION.md 7)
    return path


def _assign_all(mesh_path, by_slot):
    """Slot name (exact or prefix, the longest match wins) -> material path, on a skeletal or static mesh."""
    m = unreal.load_asset(mesh_path)
    prop = "materials" if isinstance(m, unreal.SkeletalMesh) else "static_materials"
    ms = list(m.get_editor_property(prop))
    done = []
    for i, e in enumerate(ms):
        n = str(e.get_editor_property("material_slot_name"))
        keys = sorted([k for k in by_slot if n == k or n.startswith(k)], key=len, reverse=True)
        if keys:
            e.set_editor_property("material_interface", unreal.load_asset(by_slot[keys[0]]))
            ms[i] = e
            done.append(n)
    m.set_editor_property(prop, ms)
    ASSETS.save_loaded_asset(m)
    return done


# ------------------------------------------------------------------------------------------------------------ arms
ARMS = "/Game/Characters/RuleArms"


def nail_material(path=ARMS + "/Materials/M_RuleArms_Nail"):
    """The nails: the skin set's colour lifted toward a pale keratin pink, glossier, a little clear-coat sheen."""
    m = _material(path)
    bc = _tex(m, ARMS + "/Textures/T_RuleArms_Skin_BC", -800, -200, "color")
    nm = _tex(m, ARMS + "/Textures/T_RuleArms_Skin_N", -800, 300, "normal")
    tint = _vector(m, "NailTint", (0.78, 0.55, 0.48), -800, 0)
    lerp = _expr(m, unreal.MaterialExpressionLinearInterpolate, -450, -100)
    MEL.connect_material_expressions(bc, "RGB", lerp, "A")
    MEL.connect_material_expressions(tint, "", lerp, "B")
    a = _scalar(m, "TintAmount", 0.45, -800, 150)
    MEL.connect_material_expressions(a, "", lerp, "Alpha")
    MEL.connect_material_property(lerp, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(_scalar(m, "Roughness", 0.32, -450, 100), "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(_scalar(m, "Specular", 0.55, -450, 180), "", unreal.MaterialProperty.MP_SPECULAR)
    MEL.connect_material_property(nm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    _set(m, used_with_skeletal_mesh=True)
    return _finish(m, path)


def arms():
    rep = {}
    rep["mesh"] = C.import_on_mannequin(os.path.join(IN, "glb", "SK_RuleArms.glb"), ARMS, "SK_RuleArms")
    rep["build"] = C.keep_exported_normals(ARMS + "/SK_RuleArms")
    rep["textures"] = C.import_textures(os.path.join(IN, "textures", "RuleArms_Skin"), ARMS + "/Textures")
    C.make_material("M_RuleArms_Skin", "RuleArms_Skin", skin=True)
    nail_material()
    rep["slots"] = _assign_all(ARMS + "/SK_RuleArms", {"M_RuleArms_Skin": ARMS + "/Materials/M_RuleArms_Skin",
                                                       "M_RuleArms_Nail": ARMS + "/Materials/M_RuleArms_Nail"})
    silver = C.simple_material("M_RuleSilver", (0.96, 0.95, 0.92), 0.14, 1.0)
    worn = C.simple_material("M_RuleSilverWorn", (0.80, 0.78, 0.74), 0.30, 1.0)
    gold = C.simple_material("M_RuleGold", (1.0, 0.766, 0.336), 0.16, 1.0)
    dial = C.simple_material("M_RuleDial", (0.003, 0.003, 0.0035), 0.07, 0.0)
    glass = C.simple_material("M_RuleGlass", (0.9, 0.9, 0.9), 0.02, 0.0, translucent=True)
    sockets = json.load(open(os.path.join(IN, "glb", "SK_RuleArms.sockets.json")))
    rep["jewels"] = {}
    for name, sk in sockets.items():
        mp = C.import_static(os.path.join(IN, "glb", name + ".glb"), ARMS, name)
        slots = _assign_all(mp, {"M_Character_RuleBracelet_SilverWorn": worn, "M_Character_RuleBracelet_Silver": silver,
                                 "M_Character_RuleWatch_Gold": gold, "M_Character_RuleWatch_Dial": dial,
                                 "M_Character_RuleWatch_Glass": glass})
        rep["jewels"][name] = {"slots": slots, "bone": sk["bone"], "worn": sk.get("worn", True),
                               "blenderWorldRest": sk["blender_world_rest"]}
    return rep


# ----------------------------------------------------------------------------------------------------------- goons
def goons():
    """mi_chars.setup_goons reads <src>/SK_Goon_*.glb, <src>/tex/T_*.png and <src>/goons_ue.json: a link farm."""
    src = os.path.join(IN, "goons-src")
    os.makedirs(os.path.join(src, "tex"), exist_ok=True)
    for f in os.listdir(os.path.join(src, "tex")):
        os.remove(os.path.join(src, "tex", f))

    def link(a, b):
        if os.path.lexists(b):
            os.remove(b)
        os.symlink(a, b)
    for o in C.GOONS:
        link(os.path.join(IN, "glb", "SK_Goon_%s.glb" % o), os.path.join(src, "SK_Goon_%s.glb" % o))
    for d in os.listdir(os.path.join(IN, "textures")):
        if d.startswith("Goon"):
            for f in os.listdir(os.path.join(IN, "textures", d)):
                link(os.path.join(IN, "textures", d, f), os.path.join(src, "tex", f))
    if os.path.exists(os.path.join(IN, "goons_ue.json")):
        link(os.path.join(IN, "goons_ue.json"), os.path.join(src, "goons_ue.json"))
    return C.setup_goons(src)


# ------------------------------------------------------------------------------------------------------------ guns
NINE = "/Game/Weapons/Nine"
SMG = "/Game/Weapons/GoonSMG"
BUZZ = "/Game/Characters/Buzzard"
CHOP = "/Game/Weapons/Chopper"
PACK = "/Game/ThirdParty/InfimaTFA/Weapon"

PAINT_HLSL = r"""
// The pack's black anodised receiver repainted: a worn dark-earth cerakote. The pack's own albedo keeps every
// engraving and scuff as a value change; its brightest texels (edges, wear) stay bare metal.
float lum = dot(BC, float3(0.299, 0.587, 0.114));
float wear = saturate((lum - Edge) * 9.0);
float3 paint = Earth * (0.62 + 6.0 * lum);
Metal = lerp(0.0, M, wear);
Rough = lerp(PaintRough + 0.18 * (1.0 - AO), R, wear);
return lerp(paint, BC, wear);
"""


def paint_master(path=CHOP + "/M_MI_PackPaint"):
    m = _material(path)
    bc = _expr(m, unreal.MaterialExpressionTextureSampleParameter2D, -1200, -200, parameter_name="BaseColor",
               sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    orm = _expr(m, unreal.MaterialExpressionTextureSampleParameter2D, -1200, 150, parameter_name="ORM",
                sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    nm = _expr(m, unreal.MaterialExpressionTextureSampleParameter2D, -1200, 500, parameter_name="Normal",
               sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    for n, t in ((bc, PACK + "/Textures/T_TFA_AR_01_D"), (orm, PACK + "/Textures/T_TFA_AR_01_ORM"),
                 (nm, PACK + "/Textures/T_TFA_AR_01_N")):
        n.set_editor_property("texture", unreal.load_asset(t))
    earth = _vector(m, "Earth", (0.105, 0.072, 0.042), -1200, 820)
    edge = _scalar(m, "Edge", 0.085, -1200, 900)
    pr = _scalar(m, "PaintRough", 0.58, -1200, 980)
    c = _custom(m, -700, 100, PAINT_HLSL, ["BC", "M", "R", "AO", "Earth", "Edge", "PaintRough"],
                unreal.CustomMaterialOutputType.CMOT_FLOAT3, ["Metal", "Rough"])
    MEL.connect_material_expressions(bc, "RGB", c, "BC")
    MEL.connect_material_expressions(orm, "B", c, "M")
    MEL.connect_material_expressions(orm, "G", c, "R")
    MEL.connect_material_expressions(orm, "R", c, "AO")
    MEL.connect_material_expressions(earth, "", c, "Earth")
    MEL.connect_material_expressions(edge, "", c, "Edge")
    MEL.connect_material_expressions(pr, "", c, "PaintRough")
    MEL.connect_material_property(c, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(c, "Metal", unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(c, "Rough", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.connect_material_property(nm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    _set(m, used_with_skeletal_mesh=True)
    return _finish(m, path)


def paint_instance(name, set_name, earth=(0.105, 0.072, 0.042)):
    path = CHOP + "/" + name
    if ASSETS.does_asset_exist(path):
        mi = unreal.load_asset(path)
    else:
        mi = TOOLS.create_asset(name, CHOP, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, unreal.load_asset(CHOP + "/M_MI_PackPaint"))
    for p, s in (("BaseColor", "D"), ("ORM", "ORM"), ("Normal", "N")):
        MEL.set_material_instance_texture_parameter_value(mi, p, unreal.load_asset("%s/Textures/T_TFA_AR_%s_%s" % (PACK, set_name, s)))
    MEL.set_material_instance_vector_parameter_value(mi, "Earth", unreal.LinearColor(earth[0], earth[1], earth[2], 1.0))
    MEL.update_material_instance(mi)
    ASSETS.save_loaded_asset(mi)
    return path


def guns():
    rep = {}
    T = os.path.join(IN, "textures")
    # the NINE
    rep["SK_Nine"] = _import_mesh(os.path.join(IN, "glb", "SK_Nine.glb"), NINE, "SK_Nine", True)
    for n in ("SM_Weapon_NineMagazine", "SM_Weapon_NineMagazine_TopRound"):
        rep[n] = _import_mesh(os.path.join(IN, "glb", n + ".glb"), NINE, n, False)
    C.import_textures(os.path.join(T, "Nine"), NINE + "/Textures")
    C.import_textures(os.path.join(T, "Weapon_NineMagazine"), NINE + "/Textures")
    _surface(NINE + "/M_Nine", NINE + "/Textures", "Nine", emissive=True)
    _surface(NINE + "/M_Weapon_NineMagazine", NINE + "/Textures", "Weapon_NineMagazine", skeletal=False)
    rep["nine_slots"] = _assign_all(rep["SK_Nine"], {"M_Nine": NINE + "/M_Nine"})
    for n in ("SM_Weapon_NineMagazine", "SM_Weapon_NineMagazine_TopRound"):
        _assign_all(rep[n], {"M_": NINE + "/M_Weapon_NineMagazine"})
    # the Goon SMG
    for n in ("SM_Weapon_GoonSMG", "SM_Weapon_GoonSMG_Magazine"):
        rep[n] = _import_mesh(os.path.join(IN, "glb", n + ".glb"), SMG, n, False)
    C.import_textures(os.path.join(T, "Weapon_GoonSMG"), SMG + "/Textures")
    _surface(SMG + "/M_Weapon_GoonSMG", SMG + "/Textures", "Weapon_GoonSMG", skeletal=False)
    lens = C.simple_material("M_Weapon_GoonSMG_Lens", (0.9, 0.85, 0.7), 0.05, 0.0, dest=SMG)
    rep["smg_slots"] = _assign_all(SMG + "/SM_Weapon_GoonSMG", {"M_Weapon_GoonSMG": SMG + "/M_Weapon_GoonSMG",
                                                                "M_Weapon_GoonSMG_Lens": lens})
    _assign_all(SMG + "/SM_Weapon_GoonSMG_Magazine", {"M_Weapon_GoonSMG": SMG + "/M_Weapon_GoonSMG"})
    # the Buzzard (own skeleton)
    rep["SK_Buzzard"] = _import_mesh(os.path.join(IN, "glb", "SK_Buzzard.glb"), BUZZ, "SK_Buzzard", True)
    C.import_textures(os.path.join(T, "Buzzard"), BUZZ + "/Textures")
    _surface(BUZZ + "/M_Buzzard", BUZZ + "/Textures", "Buzzard", emissive=True)
    eye = C.simple_material("M_Buzzard_Eye", (0.02, 0.02, 0.02), 0.05, 0.0, dest=BUZZ)
    strobe = C.simple_material("M_Buzzard_Strobe", (0.8, 0.8, 0.8), 0.2, 0.0, dest=BUZZ)
    rep["buzzard_slots"] = _assign_all(rep["SK_Buzzard"], {"M_Buzzard": BUZZ + "/M_Buzzard", "M_Buzzard_Eye": eye,
                                                           "M_Buzzard_Strobe": strobe})
    # the CHOPPER's own finish on the pack rifle (DECISIONS.md 2026-11-23)
    if ASSETS.does_asset_exist(PACK + "/Textures/T_TFA_AR_01_D"):
        paint_master()
        rep["chopper"] = [paint_instance("MI_Chopper_DarkEarth_01", "01"),
                          paint_instance("MI_Chopper_DarkEarth_03", "03", (0.092, 0.064, 0.038))]
    return rep


# -------------------------------------------------------------------------------------------------------------- fx
FX = "/Game/FX"

FLASH_HLSL = r"""
// Muzzle flash card. Mode 0: seen down the bore (a small white-hot core, four to six short irregular prongs);
// Mode 1: seen from the side (a short tapered jet along +U). Seed varies it per round.
float2 p = UV * 2.0 - 1.0;
float h = frac(sin(Seed * 91.7) * 43758.5);
if (Mode < 0.5) {
  float r = length(p);
  float a = atan2(p.y, p.x) + h * 6.2832;
  float prongs = pow(saturate(0.5 + 0.5 * cos(a * (4.0 + floor(h * 3.0)))), 10.0);
  float jag = 0.65 + 0.35 * frac(sin(floor(a * 7.0) * 12.9898 + Seed) * 43758.5);
  float core = exp(-r * r * 30.0);
  float rays = prongs * jag * saturate(1.0 - r) * exp(-r * 3.0);
  return core * 2.2 + rays * 1.1 + exp(-r * r * 6.0) * 0.12;
}
float u = UV.x; float v = UV.y * 2.0 - 1.0;
float width = 0.18 + 0.55 * u * (1.0 - u) * (0.8 + 0.4 * h);
float body = exp(-(v * v) / (width * width) * 3.0) * pow(saturate(1.0 - u), 1.6) * smoothstep(0.0, 0.08, u);
float flick = 0.7 + 0.3 * frac(sin(floor(u * 9.0) * 78.233 + Seed) * 43758.5);
return body * flick * 1.4;
"""

SMOKE_HLSL = r"""
// Soft volume card: a round puff with three octaves of value noise (Seed shifts it), eroded toward its edge as it ages.
float2 p = UV * 2.0 - 1.0;
float r = length(p);
float2 q = UV * 3.0 + Seed * 17.13;
float n = 0.0, a = 0.5;
for (int i = 0; i < 4; i++) {
  float2 c = floor(q), f = frac(q);
  float2 w = f * f * (3.0 - 2.0 * f);
  float h00 = frac(sin(dot(c, float2(127.1, 311.7))) * 43758.5);
  float h10 = frac(sin(dot(c + float2(1, 0), float2(127.1, 311.7))) * 43758.5);
  float h01 = frac(sin(dot(c + float2(0, 1), float2(127.1, 311.7))) * 43758.5);
  float h11 = frac(sin(dot(c + float2(1, 1), float2(127.1, 311.7))) * 43758.5);
  n += a * lerp(lerp(h00, h10, w.x), lerp(h01, h11, w.x), w.y);
  q *= 2.03; a *= 0.5;
}
float edge = saturate(1.0 - r);
float shape = saturate(edge * edge * (0.55 + n * 1.1) - Erode * (1.0 - n) * 0.8);
return shape;
"""

DECAL_HLSL = r"""
// Kind 0: a bullet strike (dark crater with a lighter chipped ring); 1: a blood spatter (droplets around a stain);
// 2: a blast scorch (soot fading out). Returns the colour; Alpha and Rough as extra outputs.
float2 p = UV * 2.0 - 1.0;
float r = length(p);
float a = atan2(p.y, p.x);
float h = frac(sin(Seed * 37.1) * 43758.5);
float3 col = float3(0.02, 0.02, 0.02);
Alpha = 0.0; Rough = 0.9;
if (Kind < 0.5) {
  float jag = 0.85 + 0.15 * frac(sin(floor(a * 9.0 + h * 9.0) * 12.9898) * 43758.5);
  float hole = 1.0 - smoothstep(0.10, 0.16, r / jag);
  float chip = (1.0 - smoothstep(0.22, 0.55, r / jag)) * (1.0 - hole);
  float dust = (1.0 - smoothstep(0.3, 1.0, r)) * 0.35;
  col = lerp(Tint * 1.25, float3(0.015, 0.013, 0.012), hole);
  Alpha = saturate(hole + chip * 0.85 + dust * (1.0 - chip));
  col = lerp(col, Tint * 0.7, dust * (1.0 - chip) * (1.0 - hole));
} else if (Kind < 1.5) {
  float stain = 1.0 - smoothstep(0.18, 0.42 + 0.1 * sin(a * 5.0 + h * 6.0), r);
  float drops = 0.0;
  for (int i = 0; i < 9; i++) {
    float fi = i + h * 13.0;
    float2 c = float2(cos(fi * 2.4), sin(fi * 2.4)) * (0.35 + 0.55 * frac(sin(fi * 17.3) * 4375.5));
    float s = 0.04 + 0.06 * frac(sin(fi * 7.1) * 4375.5);
    drops = max(drops, 1.0 - smoothstep(s * 0.7, s, length(p - c)));
  }
  col = float3(0.13, 0.008, 0.006);
  Alpha = saturate(stain + drops) * 0.92;
  Rough = 0.35;
} else {
  float soot = (1.0 - smoothstep(0.1, 1.0, r)) * (0.75 + 0.25 * sin(a * 7.0 + h * 5.0));
  col = float3(0.012, 0.011, 0.010);
  Alpha = saturate(soot) * 0.85;
}
return col;
"""


def fx():
    rep = {}
    # muzzle flash: unlit, additive, two-sided
    p = FX + "/M_FX_Flash"
    m = _material(p)
    uv = _expr(m, unreal.MaterialExpressionTextureCoordinate, -900, 0)
    c = _custom(m, -600, 0, FLASH_HLSL, ["UV", "Mode", "Seed"])
    MEL.connect_material_expressions(uv, "", c, "UV")
    MEL.connect_material_expressions(_scalar(m, "Mode", 0, -900, 100), "", c, "Mode")
    MEL.connect_material_expressions(_scalar(m, "Seed", 0, -900, 180), "", c, "Seed")
    col = _vector(m, "Color", (1.0, 0.62, 0.26), -600, 200)
    k = _scalar(m, "Intensity", 60.0, -600, 300)
    e1 = _expr(m, unreal.MaterialExpressionMultiply, -350, 100)
    MEL.connect_material_expressions(c, "", e1, "A")
    MEL.connect_material_expressions(col, "", e1, "B")
    e2 = _expr(m, unreal.MaterialExpressionMultiply, -200, 100)
    MEL.connect_material_expressions(e1, "", e2, "A")
    MEL.connect_material_expressions(k, "", e2, "B")
    MEL.connect_material_property(e2, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    _set(m, blend_mode=unreal.BlendMode.BLEND_ADDITIVE, shading_model=unreal.MaterialShadingModel.MSM_UNLIT, two_sided=True)
    rep["flash"] = _finish(m, p)

    # smoke, dust, mist, fireball: lit translucent puff (volumetric lighting, so the sun shades it), depth-faded
    p = FX + "/M_FX_Smoke"
    m = _material(p)
    uv = _expr(m, unreal.MaterialExpressionTextureCoordinate, -900, 0)
    c = _custom(m, -600, 0, SMOKE_HLSL, ["UV", "Seed", "Erode"])
    MEL.connect_material_expressions(uv, "", c, "UV")
    MEL.connect_material_expressions(_scalar(m, "Seed", 0, -900, 100), "", c, "Seed")
    MEL.connect_material_expressions(_scalar(m, "Erode", 0, -900, 180), "", c, "Erode")
    op = _expr(m, unreal.MaterialExpressionMultiply, -350, 0)
    MEL.connect_material_expressions(c, "", op, "A")
    MEL.connect_material_expressions(_scalar(m, "Opacity", 0.5, -600, 120), "", op, "B")
    df = _expr(m, unreal.MaterialExpressionDepthFade, -200, 0)
    df.set_editor_property("fade_distance_default", 40.0)
    MEL.connect_material_expressions(op, "", df, "Opacity")
    MEL.connect_material_property(df, "", unreal.MaterialProperty.MP_OPACITY)
    MEL.connect_material_property(_vector(m, "Color", (0.42, 0.40, 0.37), -350, 200), "", unreal.MaterialProperty.MP_BASE_COLOR)
    fire = _expr(m, unreal.MaterialExpressionMultiply, -350, 320)
    MEL.connect_material_expressions(_vector(m, "FireColor", (1.0, 0.45, 0.12), -600, 320), "", fire, "A")
    MEL.connect_material_expressions(_scalar(m, "Fire", 0.0, -600, 420), "", fire, "B")
    fire2 = _expr(m, unreal.MaterialExpressionMultiply, -200, 320)
    MEL.connect_material_expressions(fire, "", fire2, "A")
    MEL.connect_material_expressions(c, "", fire2, "B")
    MEL.connect_material_property(fire2, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.connect_material_property(_scalar(m, "Roughness", 1.0, -200, 450), "", unreal.MaterialProperty.MP_ROUGHNESS)
    _set(m, blend_mode=unreal.BlendMode.BLEND_TRANSLUCENT, shading_model=unreal.MaterialShadingModel.MSM_DEFAULT_LIT,
         two_sided=True, translucency_lighting_mode=unreal.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
    rep["smoke"] = _finish(m, p)

    # tracer: a thin hot streak (unlit additive)
    p = FX + "/M_FX_Tracer"
    m = _material(p)
    e = _expr(m, unreal.MaterialExpressionMultiply, -300, 0)
    MEL.connect_material_expressions(_vector(m, "Color", (1.0, 0.55, 0.22), -600, 0), "", e, "A")
    MEL.connect_material_expressions(_scalar(m, "Intensity", 40.0, -600, 120), "", e, "B")
    MEL.connect_material_property(e, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    _set(m, blend_mode=unreal.BlendMode.BLEND_ADDITIVE, shading_model=unreal.MaterialShadingModel.MSM_UNLIT)
    rep["tracer"] = _finish(m, p)

    # decals: bullet strike / blood / scorch
    p = FX + "/MD_FX_Mark"
    m = _material(p)
    _set(m, blend_mode=unreal.BlendMode.BLEND_TRANSLUCENT, material_domain=unreal.MaterialDomain.MD_DEFERRED_DECAL)
    uv = _expr(m, unreal.MaterialExpressionTextureCoordinate, -900, 0)
    c = _custom(m, -600, 0, DECAL_HLSL, ["UV", "Kind", "Seed", "Tint"], unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                ["Alpha", "Rough"])
    MEL.connect_material_expressions(uv, "", c, "UV")
    MEL.connect_material_expressions(_scalar(m, "Kind", 0, -900, 100), "", c, "Kind")
    MEL.connect_material_expressions(_scalar(m, "Seed", 0, -900, 180), "", c, "Seed")
    MEL.connect_material_expressions(_vector(m, "Tint", (0.35, 0.34, 0.32), -900, 260), "", c, "Tint")
    fade = _expr(m, unreal.MaterialExpressionMultiply, -350, 200)
    MEL.connect_material_expressions(c, "Alpha", fade, "A")
    MEL.connect_material_expressions(_scalar(m, "Fade", 1.0, -600, 300), "", fade, "B")
    MEL.connect_material_property(c, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(c, "Rough", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(fade, "", unreal.MaterialProperty.MP_OPACITY)
    rep["decal"] = _finish(m, p)

    # brass and debris (lit)
    rep["brass"] = C.simple_material("M_FX_Brass", (0.86, 0.62, 0.30), 0.28, 1.0, dest=FX)
    p = FX + "/M_FX_Debris"
    m = _material(p)
    MEL.connect_material_property(_vector(m, "Color", (0.18, 0.17, 0.16), -400, 0), "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(_scalar(m, "Roughness", 0.9, -400, 150), "", unreal.MaterialProperty.MP_ROUGHNESS)
    rep["debris"] = _finish(m, p)
    return rep


STEPS = {"arms": arms, "goons": goons, "guns": guns, "fx": fx}

if __name__ == "__main__":
    which = [a for a in sys.argv[1:] if a in STEPS or a == "all"] or ["all"]
    order = ["fx", "guns", "arms", "goons"] if "all" in which else which
    for s in order:
        try:
            REPORT[s] = STEPS[s]()
            print("MI-FP %s ok" % s)
        except Exception as e:   # noqa: BLE001  (one step failing must not hide the others' results)
            import traceback
            traceback.print_exc()
            REPORT[s] = "FAILED: %s" % e
            print("MI-FP %s FAILED %s" % (s, e))
    print("MI-FP-REPORT " + json.dumps(REPORT)[:6000])
    print("MI-DONE")
