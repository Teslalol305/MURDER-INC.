"""Editor helpers of the character scratch project (/project/ue/chars), run through MCP on port 8002:

    MI_MCP_URL=http://127.0.0.1:8002/mcp python3 mi_mcp.py py - <<< 'import sys; sys.path.insert(0, "/project/ue/chars/scripts"); import mi_chars; mi_chars.<fn>(...)'

import_on_mannequin(glb, dest, name): skinned GLB -> SkeletalMesh on the EXISTING SK_Mannequin (Interchange, no new
skeleton, no physics asset, no materials); report(): what the mesh's reference skeleton says against SK_Mannequin;
stage(): a lit floor, sky and the comparison actors; bones_match(): component-space bone transforms of two actors.
"""
import json
import os

import unreal

SKELETON = "/Game/Characters/Mannequins/Meshes/SK_Mannequin"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
ANIM = "/Game/Characters/Mannequins/Anims/"
ASSETS = unreal.EditorAssetLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def _set(obj, **kw):
    for k, v in kw.items():
        obj.set_editor_property(k, v)


def import_on_mannequin(glb, dest="/Game/RoundTrip", name=None, materials=False):
    """Import a skinned GLB as a SkeletalMesh bound to SK_Mannequin. Returns the asset path."""
    name = name or os.path.splitext(os.path.basename(glb))[0]
    skel = unreal.load_asset(SKELETON)
    p = unreal.InterchangeGenericAssetsPipeline()
    _set(p.material_pipeline, import_materials=materials)
    _set(p.material_pipeline.texture_pipeline, import_textures=materials)
    _set(p.mesh_pipeline, import_static_meshes=False, import_skeletal_meshes=True, create_physics_asset=False)
    _set(p.common_skeletal_meshes_and_animations_properties, skeleton=skel, import_only_animations=False)
    _set(p.animation_pipeline, import_animations=False)
    p.set_editor_property("asset_name", name)
    prm = unreal.ImportAssetParameters()
    _set(prm, is_automated=True, replace_existing=True,
         override_pipelines=[unreal.SoftObjectPath(p.get_path_name())])
    mgr = unreal.InterchangeManager.get_interchange_manager_scripted()
    res = mgr.import_asset(dest, unreal.InterchangeManager.create_source_data(glb), prm)
    objs = res[1] if isinstance(res, tuple) else []
    sk = [o for o in (objs or []) if isinstance(o, unreal.SkeletalMesh)]
    out = {"imported": [o.get_path_name() for o in objs or []]}
    if sk:
        m = sk[0]
        out["mesh"] = m.get_path_name()
        out["skeleton"] = m.skeleton.get_path_name() if m.skeleton else None
        out["same_skeleton"] = m.skeleton == skel
        ASSETS.save_loaded_asset(m)
    unreal.log_warning("MI: import " + json.dumps(out))
    return out


def _floor_and_light():
    for a in ACTORS.get_all_level_actors():
        if "MIStage" in [str(t) for t in a.tags]:
            ACTORS.destroy_actor(a)
    made = []
    floor = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -1))
    floor.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Plane"))
    floor.set_actor_scale3d(unreal.Vector(40, 40, 1))
    made.append(floor)
    sun = ACTORS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 500),
                                        unreal.Rotator(roll=0, pitch=-40, yaw=210))
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
         override_auto_exposure_bias=True, auto_exposure_bias=10.0)
    pp.set_editor_property("settings", s)
    made.append(pp)
    for a in made:
        a.tags = ["MIStage"]
    return made


def actor(mesh_path, anim_path, loc, yaw=0.0, time=0.0, label=None, material=None):
    """A SkeletalMeshActor playing `anim_path` frozen at `time` seconds."""
    a = ACTORS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(*loc), unreal.Rotator(0, 0, yaw))
    a.tags = ["MIStage"]
    if label:
        a.set_actor_label(label)
    c = a.skeletal_mesh_component
    c.set_skinned_asset_and_update(unreal.load_asset(mesh_path))
    if material:
        for i in range(c.get_num_materials()):
            c.set_material(i, unreal.load_asset(material))
    if anim_path:
        c.set_update_animation_in_editor(True)
        c.override_animation_data(unreal.load_asset(anim_path), False, False, float(time), 0.0)
    return a


def bones_match(a, b, bones):
    """Max position difference (cm) and rotation difference (deg) of the given bones in component space."""
    ca, cb = a.skeletal_mesh_component, b.skeletal_mesh_component
    dp = dr = 0.0
    worst = None
    for n in bones:
        ta = ca.get_socket_transform(n, unreal.RelativeTransformSpace.RTS_COMPONENT)
        tb = cb.get_socket_transform(n, unreal.RelativeTransformSpace.RTS_COMPONENT)
        d = (ta.translation - tb.translation).length()
        qa, qb = ta.rotation, tb.rotation
        dot = abs(qa.x * qb.x + qa.y * qb.y + qa.z * qb.z + qa.w * qb.w)
        r = 2.0 * __import__("math").degrees(__import__("math").acos(min(1.0, dot)))
        if d > dp:
            dp, worst = d, n
        dr = max(dr, r)
    return {"max_cm": round(dp, 5), "max_deg": round(dr, 4), "worst": worst}


def ref_pose_match(mesh_a, mesh_b):
    """Reference pose of two skeletal meshes bone by bone (local transforms): max cm and degrees apart."""
    import math
    out = {}
    comps = []
    for m in (mesh_a, mesh_b):
        a = ACTORS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, -5000))
        a.skeletal_mesh_component.set_skinned_asset_and_update(unreal.load_asset(m))
        comps.append(a)
    ca, cb = (a.skeletal_mesh_component for a in comps)
    na = [str(ca.get_bone_name(i)) for i in range(ca.get_num_bones())]
    nb = [str(cb.get_bone_name(i)) for i in range(cb.get_num_bones())]
    dp = dr = 0.0
    for i, n in enumerate(na):
        if n not in nb:
            continue
        ta, tb = ca.get_ref_pose_transform(i), cb.get_ref_pose_transform(nb.index(n))
        dp = max(dp, (ta.translation - tb.translation).length())
        qa, qb = ta.rotation, tb.rotation
        dot = min(1.0, abs(qa.x * qb.x + qa.y * qb.y + qa.z * qb.z + qa.w * qb.w))
        dr = max(dr, 2 * math.degrees(math.acos(dot)))
    out = {"bones_a": len(na), "bones_b": len(nb), "same_order": na == nb, "missing_in_b": [n for n in na if n not in nb],
           "max_cm": round(dp, 6), "max_deg": round(dr, 5)}
    for a in comps:
        ACTORS.destroy_actor(a)
    return out


def bone_names(mesh_path):
    m = unreal.load_asset(mesh_path)
    a = ACTORS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, -5000))
    a.skeletal_mesh_component.set_skinned_asset_and_update(m)
    names = [str(a.skeletal_mesh_component.get_bone_name(i)) for i in range(a.skeletal_mesh_component.get_num_bones())]
    ACTORS.destroy_actor(a)
    return names


def stage_pairs(test_mesh, pairs, spacing=110.0, gap=55.0, ref_mesh=MANNY, test_material=None):
    """For each (anim, time): the reference mannequin and the test mesh side by side (test at +X of the
    reference... both face the camera). Returns the bone comparison per pair."""
    _floor_and_light()
    names = bone_names(test_mesh)
    rep = []
    for i, (anim, t) in enumerate(pairs):
        y = (i - (len(pairs) - 1) / 2.0) * spacing * 2
        ra = actor(ref_mesh, anim, (0, y - gap, 0), yaw=0, time=t, label="Ref_%d" % i)
        ta = actor(test_mesh, anim, (0, y + gap, 0), yaw=0, time=t, label="Test_%d" % i, material=test_material)
        rep.append({"anim": anim, "time": t, "ref": ra.get_actor_label(), "test": ta.get_actor_label()})
    unreal.log_warning("MI: pairs " + json.dumps(rep))
    return rep


def compare_staged(bones=None):
    """After the viewport has redrawn (the animations are evaluated): bone transforms of each Ref_i / Test_i pair."""
    acts = {a.get_actor_label(): a for a in ACTORS.get_all_level_actors() if "MIStage" in [str(t) for t in a.tags]}
    out = []
    for k in sorted(acts):
        if k.startswith("Ref_") and ("Test_" + k[4:]) in acts:
            a, b = acts[k], acts["Test_" + k[4:]]
            names = bones or [str(a.skeletal_mesh_component.get_bone_name(i)) for i in range(a.skeletal_mesh_component.get_num_bones())]
            r = bones_match(a, b, names)
            r["pair"] = k[4:]
            # pose is really animated: distance of hand_r from its reference-pose place
            ha = a.skeletal_mesh_component.get_socket_transform("hand_r", unreal.RelativeTransformSpace.RTS_COMPONENT)
            r["hand_r_cm"] = [round(v, 2) for v in (ha.translation.x, ha.translation.y, ha.translation.z)]
            out.append(r)
    return out


# ------------------------------------------------------------------------------------------------ SK_RuleArms

TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MEL = unreal.MaterialEditingLibrary


def import_textures(folder, dest="/Game/Characters/RuleArms/Textures"):
    """T_*_BC (sRGB), _N (OpenGL -> flip green, normal map), _ORM (linear masks) from a folder."""
    tasks = []
    for f in sorted(os.listdir(folder)):
        if not f.startswith("T_") or not f.endswith(".png") or f.endswith("_H.png"):
            continue
        t = unreal.AssetImportTask()
        _set(t, filename=os.path.join(folder, f), destination_path=dest, automated=True, replace_existing=True, save=False)
        tasks.append(t)
    TOOLS.import_asset_tasks(tasks)
    out = []
    for t in tasks:
        name = os.path.splitext(os.path.basename(t.filename))[0]
        tex = unreal.load_asset(dest + "/" + name)
        if tex is None:
            continue
        if name.endswith("_N"):
            _set(tex, srgb=False, compression_settings=unreal.TextureCompressionSettings.TC_NORMALMAP,
                 flip_green_channel=True, lod_group=unreal.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP)
        elif name.endswith("_ORM"):
            _set(tex, srgb=False, compression_settings=unreal.TextureCompressionSettings.TC_MASKS,
                 lod_group=unreal.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR)
        else:
            _set(tex, lod_group=unreal.TextureGroup.TEXTUREGROUP_CHARACTER)
        ASSETS.save_loaded_asset(tex)
        out.append(name)
    return out


def _tex_node(m, path, x, y, kind):
    n = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSample, x, y)
    n.texture = unreal.load_asset(path)
    n.sampler_type = {"color": unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
                      "normal": unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
                      "masks": unreal.MaterialSamplerType.SAMPLERTYPE_MASKS}[kind]
    return n


def make_material(name, set_name, skin=False, dest="/Game/Characters/RuleArms/Materials",
                  tex="/Game/Characters/RuleArms/Textures"):
    """Material on a baked set: BC x AO, ORM, N; skin uses the subsurface profile shading model."""
    path = dest + "/" + name
    m = unreal.load_asset(path) if ASSETS.does_asset_exist(path) else TOOLS.create_asset(name, dest, unreal.Material, unreal.MaterialFactoryNew())
    MEL.delete_all_material_expressions(m)
    bc = _tex_node(m, "%s/T_%s_BC" % (tex, set_name), -600, -200, "color")
    orm = _tex_node(m, "%s/T_%s_ORM" % (tex, set_name), -600, 100, "masks")
    nm = _tex_node(m, "%s/T_%s_N" % (tex, set_name), -600, 400, "normal")
    MEL.connect_material_property(bc, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.connect_material_property(orm, "G", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(orm, "B", unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(nm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    if skin:
        prof_path = dest + "/SP_RuleSkin"
        prof = unreal.load_asset(prof_path) if ASSETS.does_asset_exist(prof_path) else TOOLS.create_asset(
            "SP_RuleSkin", dest, unreal.SubsurfaceProfile, unreal.SubsurfaceProfileFactory())
        st = prof.get_editor_property("settings")
        _set(st, surface_albedo=unreal.LinearColor(0.42, 0.2, 0.11, 1), mean_free_path_color=unreal.LinearColor(1.0, 0.35, 0.18, 1),
             mean_free_path_distance=0.55, world_unit_scale=0.1)
        prof.set_editor_property("settings", st)
        _set(m, shading_model=unreal.MaterialShadingModel.MSM_SUBSURFACE_PROFILE, subsurface_profile=prof)
        sc = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 650)
        sc.r = 1.0
        MEL.connect_material_property(sc, "", unreal.MaterialProperty.MP_OPACITY)
    _set(m, used_with_skeletal_mesh=True)
    MEL.recompile_material(m)
    ASSETS.save_loaded_asset(m)
    return m


def assign_slots(mesh_path, mats):
    """Material slots of a skeletal mesh by slot name -> material path."""
    sk = unreal.load_asset(mesh_path)
    ms = list(sk.get_editor_property("materials"))
    done = []
    for i, e in enumerate(ms):
        n = str(e.get_editor_property("material_slot_name"))
        if n in mats:
            e.set_editor_property("material_interface", unreal.load_asset(mats[n]))
            ms[i] = e
            done.append(n)
    sk.set_editor_property("materials", ms)
    ASSETS.save_loaded_asset(sk)
    return done


def import_static(glb, dest="/Game/Characters/RuleArms", name=None):
    name = name or os.path.splitext(os.path.basename(glb))[0]
    p = unreal.InterchangeGenericAssetsPipeline()
    _set(p.material_pipeline, import_materials=False)
    _set(p.material_pipeline.texture_pipeline, import_textures=False)
    _set(p.mesh_pipeline, import_static_meshes=True, import_skeletal_meshes=False,
         combine_static_meshes_behavior=unreal.InterchangeCombineStaticMeshesBehavior.ALL)
    p.set_editor_property("asset_name", name)
    prm = unreal.ImportAssetParameters()
    _set(prm, is_automated=True, replace_existing=True, override_pipelines=[unreal.SoftObjectPath(p.get_path_name())])
    unreal.InterchangeManager.get_interchange_manager_scripted().import_asset(dest, unreal.InterchangeManager.create_source_data(glb), prm)
    return dest + "/" + name


def ue_from_blender(m16):
    """Blender world matrix (row-major list of 16, metres, Z up, right-handed) -> unreal.Transform (cm),
    through the glTF path: (x, y, z) -> (x, -y, z) x 100."""
    import math
    M = [m16[0:4], m16[4:8], m16[8:12]]
    C = [1, -1, 1]
    R = [[C[i] * M[i][j] * C[j] for j in range(3)] for i in range(3)]
    t = unreal.Vector(M[0][3] * 100, -M[1][3] * 100, M[2][3] * 100)
    # rotation matrix (columns = axes) -> rotator via unreal.Matrix
    um = unreal.Matrix(unreal.Plane(R[0][0], R[1][0], R[2][0], 0), unreal.Plane(R[0][1], R[1][1], R[2][1], 0),
                       unreal.Plane(R[0][2], R[1][2], R[2][2], 0), unreal.Plane(t.x, t.y, t.z, 1))
    return um.transform()


def add_socket(mesh_path, socket, bone, world_m16):
    """Socket on the skeletal mesh at a Blender rest-pose world placement (relative to the bone's reference
    pose in component space)."""
    sk = unreal.load_asset(mesh_path)
    a = ACTORS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0))
    a.skeletal_mesh_component.set_skinned_asset_and_update(sk)
    bone_cs = a.skeletal_mesh_component.get_socket_transform(bone, unreal.RelativeTransformSpace.RTS_COMPONENT)
    ACTORS.destroy_actor(a)
    want = ue_from_blender(world_m16)
    rel = want.make_relative(bone_cs)
    s = sk.find_socket(socket) if hasattr(sk, "find_socket") else None
    if s is None:
        s = unreal.SkeletalMeshSocket(outer=sk)
        sk.add_socket(s, False)
    _set(s, socket_name=socket, bone_name=bone, relative_location=rel.translation,
         relative_rotation=rel.rotation.rotator(), relative_scale=unreal.Vector(1, 1, 1))
    ASSETS.save_loaded_asset(sk)
    return {"socket": socket, "bone": bone, "loc": [round(v, 3) for v in (rel.translation.x, rel.translation.y, rel.translation.z)]}


def arms_actor(mesh_path, anim_path, loc, yaw, time, jewels, label):
    a = actor(mesh_path, anim_path, loc, yaw=yaw, time=time, label=label)
    for mesh, sock in jewels:
        c = unreal.StaticMeshComponent(outer=a, name=sock + "_C")
        c.set_static_mesh(unreal.load_asset(mesh))
        c.attach_to_component(a.skeletal_mesh_component, sock, unreal.AttachmentRule.SNAP_TO_TARGET,
                              unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.KEEP_RELATIVE, False)
        a.add_instance_component(c) if hasattr(a, "add_instance_component") else None
        c.register_component() if hasattr(c, "register_component") else None
    return a
