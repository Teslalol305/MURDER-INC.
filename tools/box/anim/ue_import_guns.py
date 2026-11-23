"""Import the pack's rifles and parts with their own textures and materials, and write the loadout sockets.

Editor Python of a project that holds the pack import (ue_import_pack.py made the rifle skeleton and the magazine
skeleton). Nothing it makes may be committed (Fab licence: use, not publish). See docs/unreal/ANIMATION.md 8.

    import sys; sys.path.insert(0, "<dir of this file>"); import ue_import_guns as G
    G.start()             # asynchronous inside a running editor: one job per editor tick
    G.status()            # {"done": n, "total": m, "failed": [...], "finished": bool}
    G.run_sync()          # synchronous (commandlet: UnrealEditor-Cmd ... -run=pythonscript -script="ue_import_guns.py")
    G.sockets()           # the socket pass alone (re-run after any re-import)

What it makes, under /Game/ThirdParty/InfimaTFA/Weapon:
  SK_TFA_AR_{Short,Default,Extended}_Combined[_Folded]  six rifles on the shared rifle skeleton (_Folded = irons
                                                         folded; the pack has NO folded stock: the stock is the same
                                                         in all six, measured)
  Attachments/SM_TFA_AR_ATT_*, SM_TFA_AR_Magazine_*,      parts, magazines, rounds, handguards
  SM_TFA_AR_Bullet*, SM_TFA_AR_Handguard_*
  SK_TFA_AR_Magazine_Transparent                          the clear magazine on the magazine skeleton (round bones)
  Textures/T_TFA_AR_*                                     the pack's Unreal set, 4K (DirectX normals, ORM = AO,
                                                          roughness, metallic: checked against the Blender maps)
  Materials/M_TFA_AR_Surface + MI_<slot name>             one instance per material slot name of the pack
  Materials/M_TFA_AR_Glass, M_TFA_AR_Reticle              smoked glass; collimated illuminated reticle
Sockets (SOCKETS below) on every rifle variant and on the parts, placed from pack_measure.json (bl_measure.py).
"""
import json
import os
import sys
import time

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = "/project/ue/packs/tactical-rifle/FBX_Files_TacticalAssaultRifle"
DEST = "/Game/ThirdParty/InfimaTFA/Weapon"
ATT = DEST + "/Attachments"
TEX = DEST + "/Textures"
MAT = DEST + "/Materials"
RIFLE_SKELETON = DEST + "/SK_TFA_AR_Default_Combined_Skeleton"
MAG_SKELETON = DEST + "/SK_TFA_AR_Magazine_Skeleton"
ASSETS = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MEL = unreal.MaterialEditingLibrary

LENGTHS = {"shorty": "Short", "stick": "Default", "stretch": "Extended"}
RIFLES = ["SK_TFA_AR_%s_Combined%s" % (L, f) for L in ("Short", "Default", "Extended") for f in ("", "_Folded")]
STATIC = ["SM_TFA_AR_ATT_Scope", "SM_TFA_AR_ATT_Silencer", "SM_TFA_AR_ATT_Grip_Vertical", "SM_TFA_AR_ATT_Grip_Angled",
          "SM_TFA_AR_ATT_Laser", "SM_TFA_AR_ATT_Sight_Front", "SM_TFA_AR_ATT_Sight_Front_Folded",
          "SM_TFA_AR_ATT_Sight_Rear", "SM_TFA_AR_ATT_Sight_Rear_Folded", "SM_TFA_AR_Magazine_Full",
          "SM_TFA_AR_Magazine_Empty", "SM_TFA_AR_Magazine_Transparent_Full", "SM_TFA_AR_Magazine_Transparent_Empty",
          "SM_TFA_AR_Bullet", "SM_TFA_AR_Bullet_Casing", "SM_TFA_AR_Handguard_Short", "SM_TFA_AR_Handguard_Default",
          "SM_TFA_AR_Handguard_Extended"]
TEXTURE_SETS = ["01", "02", "03", "04", "Attachments_01", "Attachments_02", "Attachments_03"]
# material slot name in the pack -> texture set (None: special material)
SLOT_SET = {"MI_TFA_AR_01": "01", "MI_TFA_AR_02": "02", "MI_TFA_AR_03": "03", "MI_TFA_AR_04": "04",
            "MI_TFA_AR_ATT_01": "Attachments_01", "MI_TFA_AR_ATT_02": "Attachments_02",
            "MI_TFA_AR_ATT_03": "Attachments_03", "MI_TFA_AR_Scope_Glass": None, "MI_TFA_AR_Scope_Reticle": None}

_state = {"queue": [], "done": [], "failed": [], "total": 0, "handle": None, "t0": 0.0, "opts": {}}


def _set(obj, **kw):
    for k, v in kw.items():
        obj.set_editor_property(k, v)


# ---------------------------------------------------------------- sockets (gun space, cm, from measured geometry)
def measure(path=None):
    for p in (path, "/project/ue/animpack/facts/pack_measure.json", os.path.join(HERE, "pack_measure.json")):
        if p and os.path.exists(p):
            return json.load(open(p))
    raise RuntimeError("pack_measure.json not found (run bl_measure.py)")


def socket_table(m=None):
    """{length: {socket: (bone, (x, y, z) gun space)}} and {part: {socket: (x, y, z) local}}; rotations identity
    (every socket's +Y is the gun's forward, +Z up, as the pack's own frames)."""
    m = m or measure()
    a = m["author_sockets"]
    out = {}
    for L, v in m["variants"].items():
        bx, bz = v["bore_axis_xz"]
        tip = v["tip_y"]
        ra = v["rear_aperture"]
        out[L] = {
            # the scope's own mount on the receiver rail (the pack's Scope bone): rail tooth tops measured at
            # z 7.09, the mounts clamp from z 6.32 to 7.26 around them
            "Optic": ("Scope", (0.0, m["bones"]["Scope"][1], m["bones"]["Scope"][2])),
            # on the bore axis (muzzle ring centre) at the barrel shoulder behind the thread relief
            "MuzzleMount": ("Handguard", (bx, tip + v["thread_shoulder_from_tip"], bz)),
            "Muzzle": ("Handguard", (bx, tip, bz)),
            # the author's grip frame on the handguard's bottom rail (underside measured at z 0.976)
            "Underbarrel": ("Handguard", tuple(a["Grip"][L])),
            # the author's laser frame on the right side rail (outer face measured at x -1.867)
            "Laser": ("Handguard", tuple(a["Laser"][L])),
            "MagHinge": ("Magazine", tuple(m["bones"]["Magazine"])),
            "Eject": ("Eject_Casing", tuple(m["bones"]["Eject_Casing"])),
            # rear aperture centre (largest gap of the rear sight's centre-line vertices) and front post tip
            "SightRear": ("Sight_Rear", (0.0, ra["y"], ra["centre_z"])),
            "SightFront": ("Handguard", (0.0, v["front_post_y"], v["front_post_tip"][2])),
            "RecoilPivot": ("Grip", (0.0, v["butt"]["y"], v["butt"]["z_mid"])),
            # palms as the pack's own first-person clips hold the rifle (mi_anim.py, ANIMATION.md 1)
            "Palm_R": ("Grip", (-3.5, -4.2, -6.2)),
            "Palm_L": ("Handguard", (3.4, 28.4, 0.6)),
        }
    p = m["parts"]
    sc = p["Scope"]
    gv, ga = p["Grip_Vertical"]["body"], p["Grip_Angled"]["body"]
    parts = {
        # on the author's aim axis (the AimPoint empty's height) at the rear face: the eye looks along +Y
        "SM_TFA_AR_ATT_Scope": {"SightEye": (0.0, sc["rear_face_y"], a["AimPoint_on_scope"][2])},
        "SM_TFA_AR_ATT_Silencer": {"Muzzle": (0.0, p["Silencer"]["end_y"], 0.0)},
        # the palm wraps the vertical grip's body at mid height; on the angled grip it rests on the rear ramp
        "SM_TFA_AR_ATT_Grip_Vertical": {"SupportHand": (0.0, round((gv["min"][1] + gv["max"][1]) / 2, 3),
                                                        round((gv["min"][2] + gv["max"][2]) / 2, 3))},
        "SM_TFA_AR_ATT_Grip_Angled": {"SupportHand": (0.0, round(ga["min"][1] + 1.5, 3),
                                                      round((ga["min"][2] + ga["max"][2]) / 2, 3))},
        "SM_TFA_AR_ATT_Laser": {"Beam": tuple(a["LaserStart_on_laser"])},
    }
    return out, parts


def _bone_cs(mesh):
    sk = mesh.get_editor_property("skeleton")
    pose = unreal.AnimPoseExtensions.get_reference_pose(sk)
    return {str(n): unreal.AnimPoseExtensions.get_ref_bone_pose(pose, n, unreal.AnimPoseSpaces.WORLD)
            for n in unreal.AnimPoseExtensions.get_bone_names(pose)}


def _put_skel_socket(mesh, name, bone, loc_cs, bones):
    s = mesh.find_socket(name)
    if s is None:
        s = unreal.SkeletalMeshSocket(mesh)
        _set(s, socket_name=name)
        mesh.add_socket(s, False)
        s = mesh.find_socket(name)
    rel = bones[bone].inverse_transform_location(unreal.Vector(*loc_cs))
    _set(s, bone_name=bone, relative_location=rel, relative_rotation=unreal.Rotator(0, 0, 0),
         relative_scale=unreal.Vector(1, 1, 1))
    return [round(rel.x, 3), round(rel.y, 3), round(rel.z, 3)]


def _put_static_socket(mesh, name, loc):
    s = mesh.find_socket(name)
    if s is None:
        s = unreal.StaticMeshSocket(mesh)
        _set(s, socket_name=name)
        mesh.add_socket(s)
        s = mesh.find_socket(name)
    _set(s, relative_location=unreal.Vector(*loc), relative_rotation=unreal.Rotator(0, 0, 0),
         relative_scale=unreal.Vector(1, 1, 1))


def sockets():
    table, parts = socket_table()
    rep = {}
    for r in RIFLES:
        path = DEST + "/" + r
        if not ASSETS.does_asset_exist(path):
            rep[r] = "missing"
            continue
        mesh = unreal.load_asset(path)
        L = r.split("_")[3]
        bones = _bone_cs(mesh)
        rep[r] = {n: _put_skel_socket(mesh, n, b, loc, bones) for n, (b, loc) in table[L].items()}
        ASSETS.save_loaded_asset(mesh)
    for part, socks in parts.items():
        path = ATT + "/" + part
        if not ASSETS.does_asset_exist(path):
            rep[part] = "missing"
            continue
        mesh = unreal.load_asset(path)
        for n, loc in socks.items():
            _put_static_socket(mesh, n, loc)
        ASSETS.save_loaded_asset(mesh)
        rep[part] = socks
    _report("sockets", rep)
    return rep


# ---------------------------------------------------------------- textures and materials
def import_textures(force=False):
    tasks = []
    for s in TEXTURE_SETS:
        for suf in ("D", "N", "ORM"):
            name = "T_TFA_AR_%s_%s" % (s, suf)
            if ASSETS.does_asset_exist(TEX + "/" + name) and not force:
                continue
            t = unreal.AssetImportTask()
            _set(t, filename=os.path.join(PACK, "Textures", "Unreal", name + ".png"), destination_path=TEX,
                 automated=True, replace_existing=True, save=False)
            tasks.append(t)
    if not ASSETS.does_asset_exist(TEX + "/T_TFA_AR_Scope_Reticle_D") or force:
        t = unreal.AssetImportTask()
        _set(t, filename=os.path.join(PACK, "Textures", "Unreal", "T_TFA_AR_Scope_Reticle_D.png"), destination_path=TEX,
             automated=True, replace_existing=True, save=False)
        tasks.append(t)
    if tasks:
        TOOLS.import_asset_tasks(tasks)
    made = []
    for s in TEXTURE_SETS:
        for suf in ("D", "N", "ORM"):
            tx = unreal.load_asset("%s/T_TFA_AR_%s_%s" % (TEX, s, suf))
            if tx is None:
                continue
            if suf == "N":   # the pack's Unreal set is DirectX already: no green flip
                _set(tx, srgb=False, compression_settings=unreal.TextureCompressionSettings.TC_NORMALMAP,
                     flip_green_channel=False, lod_group=unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP)
            elif suf == "ORM":
                _set(tx, srgb=False, compression_settings=unreal.TextureCompressionSettings.TC_MASKS)
            else:
                _set(tx, srgb=True, compression_settings=unreal.TextureCompressionSettings.TC_DEFAULT)
            ASSETS.save_loaded_asset(tx)
            made.append(tx.get_name())
    return {"imported": len(tasks), "set": len(made)}


def _param_tex(m, name, tex, x, y, kind):
    n = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, x, y)
    _set(n, parameter_name=name, texture=unreal.load_asset(tex), sampler_type=kind)
    return n


def _scalar(m, name, val, x, y):
    n = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, x, y)
    _set(n, parameter_name=name, default_value=val)
    return n


def _new_material(name):
    path = MAT + "/" + name
    m = unreal.load_asset(path) if ASSETS.does_asset_exist(path) else TOOLS.create_asset(
        name, MAT, unreal.Material, unreal.MaterialFactoryNew())
    MEL.delete_all_material_expressions(m)
    return m


def master_surface():
    """Opaque metal/polymer master: BaseColor (sRGB), Normal (DirectX), ORM (R AO, G roughness, B metallic)."""
    m = _new_material("M_TFA_AR_Surface")
    base = "%s/T_TFA_AR_01_" % TEX
    bc = _param_tex(m, "BaseColor", base + "D", -700, -300, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    orm = _param_tex(m, "ORM", base + "ORM", -700, 0, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    nm = _param_tex(m, "Normal", base + "N", -700, 300, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    rs = _scalar(m, "RoughnessScale", 1.0, -700, 150)
    mul = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -350, 100)
    MEL.connect_material_expressions(orm, "G", mul, "A")
    MEL.connect_material_expressions(rs, "", mul, "B")
    MEL.connect_material_property(bc, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(orm, "B", unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(nm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    _set(m, used_with_skeletal_mesh=True, used_with_static_lighting=False)
    MEL.recompile_material(m)
    ASSETS.save_loaded_asset(m)
    return m


def glass():
    """Smoked optical glass / clear polymer: translucent, surface forward shading (reflections), thin."""
    m = _new_material("M_TFA_AR_Glass")
    _set(m, blend_mode=unreal.BlendMode.BLEND_TRANSLUCENT,
         translucency_lighting_mode=unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING,
         two_sided=True, used_with_skeletal_mesh=True)
    tint = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -500, -200)
    _set(tint, parameter_name="Tint", default_value=unreal.LinearColor(0.035, 0.045, 0.05, 1.0))
    op = _scalar(m, "Opacity", 0.22, -500, 0)
    ro = _scalar(m, "Roughness", 0.04, -500, 100)
    sp = _scalar(m, "Specular", 0.9, -500, 200)
    MEL.connect_material_property(tint, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
    MEL.connect_material_property(ro, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(sp, "", unreal.MaterialProperty.MP_SPECULAR)
    MEL.recompile_material(m)
    ASSETS.save_loaded_asset(m)
    return m


RETICLE_HLSL = """
float3 v = normalize(-Cam);
float3 f = normalize(Fwd);
float a = acos(clamp(dot(v, f), -1.0, 1.0));      // angle off the sight axis, radians
float dotm = 1.0 - smoothstep(DotR * 0.7, DotR, a);
float ring = 1.0 - smoothstep(RingW * 0.5, RingW, abs(a - RingR));
return saturate(dotm + 0.85 * ring);
"""


def reticle():
    """Collimated illuminated reticle on the scope's reticle plane: drawn where the view ray is parallel to the
    scope's axis (mesh +Y), so the dot stays on the point of aim at any eye position (no parallax), like a real
    red-dot / prism sight. A 1.5 mrad dot inside a 16 mrad ring, additive and unlit."""
    m = _new_material("M_TFA_AR_Reticle")
    _set(m, blend_mode=unreal.BlendMode.BLEND_ADDITIVE, shading_model=unreal.MaterialShadingModel.MSM_UNLIT,
         two_sided=True, used_with_skeletal_mesh=True)
    cam = MEL.create_material_expression(m, unreal.MaterialExpressionCameraVectorWS, -900, -100)
    axis = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -1100, 100)
    _set(axis, constant=unreal.LinearColor(0, 1, 0, 0))
    tv = MEL.create_material_expression(m, unreal.MaterialExpressionTransform, -900, 100)
    _set(tv, transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
         transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    MEL.connect_material_expressions(axis, "", tv, "")
    cu = MEL.create_material_expression(m, unreal.MaterialExpressionCustom, -600, 0)
    ins = []
    for nm in ("Cam", "Fwd", "DotR", "RingR", "RingW"):
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", nm)
        ins.append(ci)
    _set(cu, code=RETICLE_HLSL, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT1, inputs=ins,
         description="collimated reticle")
    MEL.connect_material_expressions(cam, "", cu, "Cam")
    MEL.connect_material_expressions(tv, "", cu, "Fwd")
    for i, (nm, val) in enumerate((("DotR", 0.0015), ("RingR", 0.016), ("RingW", 0.0009))):
        MEL.connect_material_expressions(_scalar(m, nm, val, -900, 300 + 90 * i), "", cu, nm)
    col = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -600, 250)
    _set(col, parameter_name="Color", default_value=unreal.LinearColor(1.0, 0.04, 0.02, 1.0))
    br = _scalar(m, "Brightness", 40.0, -600, 400)
    m1 = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -350, 100)
    m2 = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -200, 150)
    MEL.connect_material_expressions(cu, "", m1, "A")
    MEL.connect_material_expressions(col, "", m1, "B")
    MEL.connect_material_expressions(m1, "", m2, "A")
    MEL.connect_material_expressions(br, "", m2, "B")
    MEL.connect_material_property(m2, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m)
    ASSETS.save_loaded_asset(m)
    return m


def materials():
    master = master_surface()
    g = glass()
    r = reticle()
    out = {}
    for slot, s in SLOT_SET.items():
        path = MAT + "/" + slot
        if s is None:
            out[slot] = (g if "Glass" in slot else r).get_path_name()
            continue
        mi = unreal.load_asset(path) if ASSETS.does_asset_exist(path) else TOOLS.create_asset(
            slot, MAT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, master)
        for p, suf in (("BaseColor", "D"), ("Normal", "N"), ("ORM", "ORM")):
            MEL.set_material_instance_texture_parameter_value(mi, p, unreal.load_asset("%s/T_TFA_AR_%s_%s" % (TEX, s, suf)))
        MEL.update_material_instance(mi)
        ASSETS.save_loaded_asset(mi)
        out[slot] = path
    # the clear magazine's polymer: the same glass a little more present
    path = MAT + "/MI_TFA_AR_MagPolymer"
    mi = unreal.load_asset(path) if ASSETS.does_asset_exist(path) else TOOLS.create_asset(
        "MI_TFA_AR_MagPolymer", MAT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, g)
    MEL.set_material_instance_scalar_parameter_value(mi, "Opacity", 0.32)
    MEL.set_material_instance_scalar_parameter_value(mi, "Roughness", 0.18)
    MEL.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(0.06, 0.07, 0.075, 1))
    MEL.update_material_instance(mi)
    ASSETS.save_loaded_asset(mi)
    out["MI_TFA_AR_MagPolymer"] = path
    return out


def _material_for(slot, mesh_name):
    if slot == "MI_TFA_AR_Scope_Glass" and "Magazine" in mesh_name:
        return unreal.load_asset(MAT + "/MI_TFA_AR_MagPolymer")
    if slot == "MI_TFA_AR_Scope_Glass":
        return unreal.load_asset(MAT + "/M_TFA_AR_Glass")
    if slot == "MI_TFA_AR_Scope_Reticle":
        return unreal.load_asset(MAT + "/M_TFA_AR_Reticle")
    if ASSETS.does_asset_exist(MAT + "/" + slot):
        return unreal.load_asset(MAT + "/" + slot)
    return None


def assign(mesh):
    skel = isinstance(mesh, unreal.SkeletalMesh)
    prop = "materials" if skel else "static_materials"
    ms = list(mesh.get_editor_property(prop))
    rep = []
    for i, e in enumerate(ms):
        slot = str(e.get_editor_property("material_slot_name"))
        mat = _material_for(slot, mesh.get_name())
        if mat is not None:
            e.set_editor_property("material_interface", mat)
            ms[i] = e
        rep.append((slot, mat.get_name() if mat else None))
    mesh.set_editor_property(prop, ms)
    ASSETS.save_loaded_asset(mesh)
    return rep


# ---------------------------------------------------------------- meshes
def _pipeline(skeletal, skeleton=None, name=None):
    p = unreal.InterchangeGenericAssetsPipeline()
    _set(p.material_pipeline, import_materials=False)
    _set(p.material_pipeline.texture_pipeline, import_textures=False)
    _set(p.mesh_pipeline, import_static_meshes=not skeletal, import_skeletal_meshes=skeletal,
         create_physics_asset=False)
    if not skeletal:
        _set(p.mesh_pipeline, combine_static_meshes_behavior=unreal.InterchangeCombineStaticMeshesBehavior.ALL)
    common = p.common_skeletal_meshes_and_animations_properties
    if skeleton is not None:
        _set(common, skeleton=skeleton)
    _set(common, import_only_animations=False)
    _set(p.animation_pipeline, import_animations=False)
    if name:
        p.set_editor_property("asset_name", name)
    return p


def import_mesh(name, dest, skeletal, skeleton_path=None):
    src = os.path.join(PACK, "Meshes", name + ".fbx")
    sk = unreal.load_asset(skeleton_path) if skeleton_path else None
    prm = unreal.ImportAssetParameters()
    _set(prm, is_automated=True, replace_existing=True,
         override_pipelines=[unreal.SoftObjectPath(_pipeline(skeletal, sk, name).get_path_name())])
    unreal.InterchangeManager.get_interchange_manager_scripted().import_asset(
        dest, unreal.InterchangeManager.create_source_data(src), prm)
    path = dest + "/" + name
    if not ASSETS.does_asset_exist(path):
        for q in ASSETS.list_assets(dest, recursive=False):
            if name in q.rsplit("/", 1)[1] and not q.endswith("_Skeleton"):
                ASSETS.rename_asset(q.split(".")[0], path)
                break
    mesh = unreal.load_asset(path)
    if mesh is None:
        raise RuntimeError("nothing imported for " + name)
    rep = {"asset": path, "materials": assign(mesh)}
    if skeletal:
        s = mesh.get_editor_property("skeleton")
        rep["skeleton"] = s.get_path_name() if s else None
        b = mesh.get_bounds()
    else:
        b = mesh.get_bounds()
    rep["bounds"] = {"origin": [round(b.origin.x, 3), round(b.origin.y, 3), round(b.origin.z, 3)],
                     "extent": [round(b.box_extent.x, 3), round(b.box_extent.y, 3), round(b.box_extent.z, 3)]}
    ASSETS.save_loaded_asset(mesh)
    return rep


# ---------------------------------------------------------------- job queue
def plan(force_textures=False):
    jobs = [("textures", force_textures), ("materials", None)]
    jobs += [("rifle", r) for r in RIFLES]
    jobs += [("static", s) for s in STATIC]
    jobs += [("mag", "SK_TFA_AR_Magazine_Transparent"), ("mag_assign", "SK_TFA_AR_Magazine"),
             ("rifle_assign", "SK_TFA_AR_Default_Combined"), ("sockets", None)]
    return jobs


def _run_job(job):
    kind, arg = job
    if kind == "textures":
        return import_textures(arg)
    if kind == "materials":
        return materials()
    if kind == "rifle":
        return import_mesh(arg, DEST, True, RIFLE_SKELETON)
    if kind == "static":
        return import_mesh(arg, ATT, False)
    if kind == "mag":
        return import_mesh(arg, DEST, True, MAG_SKELETON)
    if kind in ("mag_assign", "rifle_assign"):
        return assign(unreal.load_asset(DEST + "/" + arg))
    if kind == "sockets":
        return sockets()
    raise RuntimeError(kind)


def _report(name, data):
    d = os.path.join(unreal.Paths.project_saved_dir(), "AnimPack")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name + ".json"), "w") as f:
        json.dump(data, f, indent=1, default=str)
    return data


def _write_status():
    s = {"done": len(_state["done"]), "total": _state["total"], "failed": _state["failed"],
         "finished": not _state["queue"], "seconds": round(time.time() - _state["t0"], 1),
         "last": [d["job"] for d in _state["done"][-3:]]}
    _report("guns_status", s)
    if not _state["queue"]:
        _report("guns", {"done": _state["done"], "failed": _state["failed"]})
    return s


def _tick(_dt):
    if not _state["queue"]:
        if _state["handle"] is not None:
            unreal.unregister_slate_post_tick_callback(_state["handle"])
            _state["handle"] = None
        return
    job = _state["queue"].pop(0)
    try:
        _state["done"].append({"job": "%s %s" % job, "result": _run_job(job)})
    except Exception as ex:  # noqa: BLE001
        _state["failed"].append({"job": "%s %s" % job, "error": str(ex)[:300]})
    _write_status()


def start(only=None, force_textures=False):
    q = plan(force_textures)
    if only:
        q = [j for j in q if j[0] in only or (j[1] and any(o in str(j[1]) for o in only))]
    _state.update(queue=q, done=[], failed=[], t0=time.time(), total=len(q))
    if _state["handle"] is None:
        _state["handle"] = unreal.register_slate_post_tick_callback(_tick)
    return _write_status()


def status():
    try:
        return json.load(open(os.path.join(unreal.Paths.project_saved_dir(), "AnimPack", "guns_status.json")))
    except Exception:  # noqa: BLE001
        return None


def run_sync(only=None, force_textures=False):
    q = plan(force_textures)
    if only:
        q = [j for j in q if j[0] in only or (j[1] and any(o in str(j[1]) for o in only))]
    _state.update(queue=q, done=[], failed=[], t0=time.time(), total=len(q))
    while _state["queue"]:
        _tick(0.0)
    s = _write_status()
    print("MI-GUNS", json.dumps(s))
    return s


if __name__ == "__main__" and "--sync" in sys.argv:
    run_sync()
    print("MI-DONE")
