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
        c.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        c.set_animation(unreal.load_asset(anim_path))
        c.set_position(float(time), False)
        c.set_play_rate(0.0)
        c.play(False)
        c.set_position(float(time), False)
        c.tick_animation(0.0, False)
        c.refresh_bone_transforms()
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


def bone_names(mesh_path):
    m = unreal.load_asset(mesh_path)
    c = unreal.SkeletalMeshEditorSubsystem if False else None  # noqa: F841
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
        rep.append({"anim": anim, "time": t, **bones_match(ra, ta, names)})
    unreal.log_warning("MI: pairs " + json.dumps(rep))
    return rep
