"""Scratch-project assets and the picture stage for the animation pack (editor Python, MCP port 8003).

import_chopper(): SK_Chopper (skinned GLB, its own skeleton) with its 4K set, the magazine and its top round, the
Goon SMG; chopper_clip(): an AnimSequence on SK_Chopper's skeleton from part values (bolt travel 0..1, trigger
0..1, magazine bone transform in gun space); stage(): light, floor and backdrop; rig(): a character playing a clip at
a time with the CHOPPER on ik_hand_gun (identity) playing its parts clip, and the magazine on the magazine bone.
"""
import json
import math
import os
import sys

import unreal

sys.path.insert(0, os.path.dirname(__file__))
import mi_adapt as D  # noqa: E402

IN = "/project/ue/animpack/in"
WEP = "/Game/Weapons/Chopper"
ASSETS = unreal.EditorAssetLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MEL = unreal.MaterialEditingLibrary
ARMS = "/Game/Characters/RuleArms/SK_RuleArms"


def _set(obj, **kw):
    for k, v in kw.items():
        obj.set_editor_property(k, v)


def _import(src, dest, name, skeletal):
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
        dest, unreal.InterchangeManager.create_source_data(src), prm)
    return dest + "/" + name


def import_textures(folder, dest):
    tasks = []
    for f in sorted(os.listdir(folder)):
        if f.startswith("T_") and f.endswith(".png"):
            t = unreal.AssetImportTask()
            _set(t, filename=os.path.join(folder, f), destination_path=dest, automated=True, replace_existing=True,
                 save=False)
            tasks.append(t)
    TOOLS.import_asset_tasks(tasks)
    for t in tasks:
        name = os.path.splitext(os.path.basename(t.filename))[0]
        tex = unreal.load_asset(dest + "/" + name)
        if tex is None:
            continue
        if name.endswith("_N"):
            _set(tex, srgb=False, compression_settings=unreal.TextureCompressionSettings.TC_NORMALMAP,
                 flip_green_channel=True)
        elif name.endswith("_ORM"):
            _set(tex, srgb=False, compression_settings=unreal.TextureCompressionSettings.TC_MASKS)
        ASSETS.save_loaded_asset(tex)


def material(name, set_name, tex, dest, emissive=False, skeletal=True):
    path = dest + "/" + name
    m = unreal.load_asset(path) if ASSETS.does_asset_exist(path) else TOOLS.create_asset(
        name, dest, unreal.Material, unreal.MaterialFactoryNew())
    MEL.delete_all_material_expressions(m)

    def node(suffix, x, y, kind):
        n = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSample, x, y)
        n.texture = unreal.load_asset("%s/T_%s_%s" % (tex, set_name, suffix))
        n.sampler_type = kind
        return n
    bc = node("BC", -600, -200, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    orm = node("ORM", -600, 100, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    nm = node("N", -600, 400, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    MEL.connect_material_property(bc, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.connect_material_property(orm, "G", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(orm, "B", unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(nm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    if emissive and ASSETS.does_asset_exist("%s/T_%s_E" % (tex, set_name)):
        e = node("E", -600, 700, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
        MEL.connect_material_property(e, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if skeletal:
        _set(m, used_with_skeletal_mesh=True)
    MEL.recompile_material(m)
    ASSETS.save_loaded_asset(m)
    return path


def _assign(mesh_path, mat_path):
    m = unreal.load_asset(mesh_path)
    if isinstance(m, unreal.SkeletalMesh):
        ms = list(m.get_editor_property("materials"))
        for i, e in enumerate(ms):
            e.set_editor_property("material_interface", unreal.load_asset(mat_path))
            ms[i] = e
        m.set_editor_property("materials", ms)
    else:
        ms = list(m.get_editor_property("static_materials"))
        for i, e in enumerate(ms):
            e.set_editor_property("material_interface", unreal.load_asset(mat_path))
            ms[i] = e
        m.set_editor_property("static_materials", ms)
    ASSETS.save_loaded_asset(m)


def import_chopper(src=IN):
    out = {}
    out["SK_Chopper"] = _import(src + "/glb/SK_Chopper.glb", WEP, "SK_Chopper", True)
    for n in ("SM_Weapon_ChopperMagazine", "SM_Weapon_ChopperMagazine_TopRound"):
        out[n] = _import(src + "/glb/%s.glb" % n, WEP, n, False)
    out["SM_Weapon_GoonSMG"] = _import(src + "/glb/SM_Weapon_GoonSMG.glb", "/Game/Weapons/GoonSMG", "SM_Weapon_GoonSMG",
                                       False)
    for s in ("Chopper", "Weapon_ChopperMagazine", "Weapon_GoonSMG"):
        import_textures(src + "/textures/" + s, WEP + "/Textures" if s != "Weapon_GoonSMG" else "/Game/Weapons/GoonSMG/Textures")
    out["M_Chopper"] = material("M_Chopper", "Chopper", WEP + "/Textures", WEP + "/Materials", emissive=True)
    out["M_Mag"] = material("M_Weapon_ChopperMagazine", "Weapon_ChopperMagazine", WEP + "/Textures", WEP + "/Materials",
                            skeletal=False)
    out["M_SMG"] = material("M_Weapon_GoonSMG", "Weapon_GoonSMG", "/Game/Weapons/GoonSMG/Textures",
                            "/Game/Weapons/GoonSMG/Materials", skeletal=False)
    _assign(out["SK_Chopper"], out["M_Chopper"])
    _assign(out["SM_Weapon_ChopperMagazine"], out["M_Mag"])
    _assign(out["SM_Weapon_ChopperMagazine_TopRound"], out["M_Mag"])
    _assign(out["SM_Weapon_GoonSMG"], out["M_SMG"])
    sk = unreal.load_asset(out["SK_Chopper"]).get_editor_property("skeleton")
    ASSETS.save_loaded_asset(sk)          # the importer leaves the new skeleton unsaved: an editor restart loses it
    out["skeleton"] = sk.get_path_name()
    out["bones"] = chopper_ref()
    return out


def chopper_ref():
    sk = unreal.load_asset(WEP + "/SK_Chopper").get_editor_property("skeleton")
    p = unreal.AnimPoseExtensions.get_reference_pose(sk)
    names = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(p)]
    return {n: {"cs": D.from_ue(unreal.AnimPoseExtensions.get_ref_bone_pose(p, n, D.WS)),
                "ls": D.from_ue(unreal.AnimPoseExtensions.get_ref_bone_pose(p, n, D.LS))} for n in names}


def chopper_frames(parts_list):
    """parts_list: [{bolt, trigger, mag (gun-space transform), selector}] -> per-frame locals of SK_Chopper."""
    ref = chopper_ref()
    names = list(ref.keys())
    parent = {}
    # parents from the reference: every bone but body hangs from body in this rig
    for n in names:
        parent[n] = None if n == names[0] else names[0]
    frames = []
    body_cs = ref[names[0]]["cs"]
    for parts in parts_list:
        loc = {n: ref[n]["ls"] for n in names}
        if "bolt" in ref:
            cs = D.compose(((-CHB * parts.get("bolt", 0.0), 0.0, 0.0), (0, 0, 0, 1)), ref["bolt"]["cs"])
            loc["bolt"] = D.rel(body_cs, cs)
        if "trigger" in ref:
            q = D.pitch(-D.CH["trigger_deg"] * parts.get("trigger", 0.0))
            pv = D.CH["Trigger"]
            tr = (D.vsub(pv, D.qrot(q, pv)), q)
            loc["trigger"] = D.rel(body_cs, D.compose(tr, ref["trigger"]["cs"]))
        if "magazine" in ref:
            loc["magazine"] = D.rel(body_cs, D.compose(parts.get("mag", D.ID), ref["magazine"]["cs"]))
        frames.append(loc)
    return frames


CHB = 9.2


def chopper_clip(name, parts_list, rate=30, dest=WEP + "/Anims", curves=None):
    sk = unreal.load_asset(WEP + "/SK_Chopper").get_editor_property("skeleton")
    frames = chopper_frames(parts_list)
    D.write_clip(dest + "/" + name, frames, rate=rate, skeleton_path=sk.get_path_name(), curves=curves)
    return dest + "/" + name


# ---------------------------------------------------------------- stage
def clear():
    for a in ACTORS.get_all_level_actors():
        if "MIStage" in [str(t) for t in a.tags] or "MIRig" in [str(t) for t in a.tags]:
            ACTORS.destroy_actor(a)


def stage(sun_yaw=210.0, sun_pitch=-35.0, exposure=10.0):
    clear()
    made = []
    floor = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -1))
    floor.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Plane"))
    floor.set_actor_scale3d(unreal.Vector(60, 60, 1))
    made.append(floor)
    wall = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 900, 300))
    wall.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
    wall.set_actor_scale3d(unreal.Vector(30, 0.2, 6))
    made.append(wall)
    sun = ACTORS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 500),
                                        unreal.Rotator(roll=0, pitch=sun_pitch, yaw=sun_yaw))
    sun.light_component.set_editor_property("intensity", 6.0)
    made.append(sun)
    made.append(ACTORS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0)))
    sky = ACTORS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 300))
    sky.light_component.set_editor_property("real_time_capture", True)
    made.append(sky)
    pp = ACTORS.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
    pp.set_editor_property("unbound", True)
    s = pp.get_editor_property("settings")
    _set(s, override_auto_exposure_method=True, auto_exposure_method=unreal.AutoExposureMethod.AEM_MANUAL,
         override_auto_exposure_bias=True, auto_exposure_bias=exposure)
    pp.set_editor_property("settings", s)
    made.append(pp)
    for a in made:
        a.tags = ["MIStage"]
    return len(made)


def _skel_actor(mesh, anim, loc, yaw, t, label):
    a = ACTORS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(*loc), unreal.Rotator(0, 0, yaw))
    a.tags = ["MIRig"]
    a.set_actor_label(label)
    c = a.skeletal_mesh_component
    c.set_skinned_asset_and_update(unreal.load_asset(mesh))
    if anim:
        c.set_update_animation_in_editor(True)
        c.override_animation_data(unreal.load_asset(anim) if isinstance(anim, str) else anim, False, False, float(t), 0.0)
    return a


def rig(char_anim, t, loc=(0, 0, 0), yaw=0.0, label="R", mesh=None, gun_anim=None, gun="chopper", mag=True):
    """A character at loc playing char_anim at t with its gun on ik_hand_gun."""
    mesh = mesh or D.MANNY
    ch = _skel_actor(mesh, char_anim, loc, yaw, t, label)
    if gun == "chopper":
        g = _skel_actor(WEP + "/SK_Chopper", gun_anim, loc, yaw, t, label + "_Chopper")
    else:
        g = _skel_actor(D.PACK + "/Weapon/SK_TFA_AR_Default_Combined", gun_anim, loc, yaw, t, label + "_Rifle")
    g.attach_to_actor(ch, "ik_hand_gun", unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
                      unreal.AttachmentRule.KEEP_WORLD, False)
    out = [ch, g]
    if gun == "chopper" and mag:
        m = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc))
        m.tags = ["MIRig"]
        m.set_actor_label(label + "_Mag")
        m.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        m.static_mesh_component.set_static_mesh(unreal.load_asset(WEP + "/SM_Weapon_ChopperMagazine"))
        m.attach_to_actor(g, "magazine", unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
                          unreal.AttachmentRule.KEEP_WORLD, False)
        out.append(m)
    elif gun != "chopper" and mag:
        for b in ("Magazine",):
            m = _skel_actor(D.PACK + "/Weapon/SK_TFA_AR_Magazine", None, loc, yaw, 0, label + "_PackMag")
            m.attach_to_actor(g, b, unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
                              unreal.AttachmentRule.KEEP_WORLD, False)
            out.append(m)
    return [a.get_actor_label() for a in out]


def eye(loc=(0, 0, 0), yaw=0.0):
    """The first-person camera for a rig at loc / yaw: (x, y, z, pitch, yaw, roll) for mi_mcp.py shot."""
    e = D.EYE_CS
    r = math.radians(yaw)
    x = loc[0] + e[0] * math.cos(r) - e[1] * math.sin(r)
    y = loc[1] + e[0] * math.sin(r) + e[1] * math.cos(r)
    return (round(x, 2), round(y, 2), round(loc[2] + e[2], 2), 0.0, round(90.0 + yaw, 2), 0.0)
