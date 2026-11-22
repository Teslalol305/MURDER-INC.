"""Import the Tactical FPS Animation Pack (Infima Games, Fab) from its FBX files into an Unreal project.

The character clips go ON THE EXISTING UE5 mannequin skeleton (no retargeting: the pack is authored on it, joint for
joint, see docs/unreal/ANIMATION.md); the pack's rifle comes in as a reference skeletal mesh with its own skeleton,
and the weapon clips on that skeleton. Nothing it makes may be committed (Fab licence: use, not publish).

Inside a running editor (asynchronous, one file per editor tick, so an MCP call returns at once):

    import sys; sys.path.insert(0, "<dir of this file>"); import ue_import_pack as P
    P.start(pack="/project/ue/packs/tactical-rifle/FBX_Files_TacticalAssaultRifle", dest="/Game/ThirdParty/InfimaTFA")
    P.status()            # {"done": n, "total": m, "failed": [...], "finished": bool}

As a commandlet (synchronous):

    UnrealEditor-Cmd <Project>.uproject -run=pythonscript -script="ue_import_pack.py --pack <dir> --dest /Game/..."

Options: skeleton (default /Game/Characters/Mannequins/Meshes/SK_Mannequin), only (substring filter on the relative
path), weapon (True: the reference rifle, its skeleton and the weapon clips), textures (True: the Unreal texture set
and one simple material per slot on the rifle), adapted (a folder of adapted clips, FBX or GLB, imported on the
mannequin skeleton into <dest>/Adapted; see tools/box/anim/bl_adapt.py), status file <project>/Saved/AnimPack/status.json.
"""
import glob
import json
import os
import sys
import time

import unreal

SKELETON = "/Game/Characters/Mannequins/Meshes/SK_Mannequin"
ASSETS = unreal.EditorAssetLibrary
RIFLE_FBX = "Meshes/SK_TFA_AR_Default_Combined.fbx"
MAG_FBX = "Meshes/SK_TFA_AR_Magazine.fbx"

_state = {"queue": [], "done": [], "failed": [], "total": 0, "handle": None, "t0": 0.0, "opts": {}}


def _set(obj, **kw):
    for k, v in kw.items():
        obj.set_editor_property(k, v)


def _status_path():
    d = os.path.join(unreal.Paths.project_saved_dir(), "AnimPack")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "status.json")


def _write_status():
    s = {"done": len(_state["done"]), "total": _state["total"], "failed": _state["failed"],
         "finished": not _state["queue"], "seconds": round(time.time() - _state["t0"], 1),
         "last": _state["done"][-3:]}
    with open(_status_path(), "w") as f:
        json.dump(s, f, indent=1)
    return s


def _pipeline(skeleton=None, meshes=False, anims=True, materials=False, name=None):
    p = unreal.InterchangeGenericAssetsPipeline()
    _set(p.material_pipeline, import_materials=materials)
    _set(p.material_pipeline.texture_pipeline, import_textures=materials)
    _set(p.mesh_pipeline, import_static_meshes=False, import_skeletal_meshes=meshes, create_physics_asset=False)
    common = p.common_skeletal_meshes_and_animations_properties
    if skeleton is not None:
        _set(common, skeleton=skeleton)
    _set(common, import_only_animations=bool(anims and not meshes))
    _set(p.animation_pipeline, import_animations=anims)
    if name:
        p.set_editor_property("asset_name", name)
    return p


def _import(src, dest, pipeline):
    prm = unreal.ImportAssetParameters()
    _set(prm, is_automated=True, replace_existing=True,
         override_pipelines=[unreal.SoftObjectPath(pipeline.get_path_name())])
    mgr = unreal.InterchangeManager.get_interchange_manager_scripted()
    return mgr.import_asset(dest, unreal.InterchangeManager.create_source_data(src), prm)


def _after_anim(dest, base, skeleton):
    """Find what the import made in `dest` (the 5.9 importer's return list can be empty), name it after the file."""
    want = dest + "/" + base
    made = [a for a in ASSETS.list_assets(dest, recursive=False, include_folder=False)]
    seqs = []
    for p in made:
        a = unreal.load_asset(p)
        if isinstance(a, unreal.AnimSequence) and a.get_editor_property("skeleton") == skeleton:
            seqs.append(a)
    target = None
    for a in seqs:
        if a.get_path_name().split(".")[0] == want:
            target = a
    if target is None:
        cand = [a for a in seqs if base in a.get_name()]
        if cand:
            src = cand[0].get_path_name().split(".")[0]
            if ASSETS.does_asset_exist(want):
                ASSETS.delete_asset(want)
            ASSETS.rename_asset(src, want)
            target = unreal.load_asset(want)
    if target is not None:
        ASSETS.save_loaded_asset(target)
        return {"asset": want, "length": round(target.get_play_length(), 4),
                "frames": target.get_editor_property("number_of_sampled_frames")
                if hasattr(target, "number_of_sampled_frames") else None}
    return None


def import_clip(fbx, dest, skeleton_path=SKELETON):
    skel = unreal.load_asset(skeleton_path)
    base = os.path.splitext(os.path.basename(fbx))[0]
    _import(fbx, dest, _pipeline(skeleton=skel, meshes=False, anims=True, name=base))
    return _after_anim(dest, base, skel)


def import_rifle(pack, dest, textures=True):
    """The pack's rifle as a reference skeletal mesh with its own skeleton (and the magazine)."""
    out = {}
    for rel, name in ((RIFLE_FBX, "SK_TFA_AR_Default_Combined"), (MAG_FBX, "SK_TFA_AR_Magazine")):
        _import(os.path.join(pack, rel), dest, _pipeline(meshes=True, anims=False, materials=False, name=name))
        p = dest + "/" + name
        m = unreal.load_asset(p) if ASSETS.does_asset_exist(p) else None
        if m is None:
            for q in ASSETS.list_assets(dest, recursive=False):
                a = unreal.load_asset(q)
                if isinstance(a, unreal.SkeletalMesh) and name in a.get_name():
                    m = a
        if m is not None:
            ASSETS.save_loaded_asset(m)
            sk = m.get_editor_property("skeleton")
            out[name] = {"mesh": m.get_path_name(), "skeleton": sk.get_path_name() if sk else None}
            if sk:
                ASSETS.save_loaded_asset(sk)
    if textures:
        try:
            out["materials"] = rifle_materials(pack, dest)
        except Exception as ex:  # noqa: BLE001
            out["materials_error"] = str(ex)
    return out


def rifle_materials(pack, dest):
    """Unreal texture set (_D, _N DirectX, _ORM) and one material per slot named T_TFA_AR_<slot>."""
    tex_dir = os.path.join(pack, "Textures", "Unreal")
    tdest = dest + "/Textures"
    tasks = []
    for f in sorted(glob.glob(os.path.join(tex_dir, "T_TFA_AR_0*_*.png"))):
        t = unreal.AssetImportTask()
        _set(t, filename=f, destination_path=tdest, automated=True, replace_existing=True, save=True)
        tasks.append(t)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    for p in ASSETS.list_assets(tdest, recursive=False):
        tx = unreal.load_asset(p)
        if not isinstance(tx, unreal.Texture2D):
            continue
        n = tx.get_name()
        if n.endswith("_N"):
            _set(tx, srgb=False, compression_settings=unreal.TextureCompressionSettings.TC_NORMALMAP)
        elif n.endswith("_ORM"):
            _set(tx, srgb=False, compression_settings=unreal.TextureCompressionSettings.TC_MASKS)
        ASSETS.save_loaded_asset(tx)
    mesh = unreal.load_asset(dest + "/SK_TFA_AR_Default_Combined")
    if mesh is None:
        return "no mesh"
    mats = mesh.get_editor_property("materials")
    lib = unreal.MaterialEditingLibrary
    report = []
    for i, sm in enumerate(mats):
        slot = str(sm.get_editor_property("material_slot_name"))
        num = "".join(ch for ch in slot if ch.isdigit())[-2:].rjust(2, "0") if any(ch.isdigit() for ch in slot) else "01"
        mp = dest + "/Materials/M_TFA_AR_" + num
        if not ASSETS.does_asset_exist(mp):
            m = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_TFA_AR_" + num, dest + "/Materials",
                                                                         unreal.Material, unreal.MaterialFactoryNew())
            for k, (suffix, prop, typ) in enumerate((("_D", unreal.MaterialProperty.MP_BASE_COLOR, "color"),
                                                     ("_N", unreal.MaterialProperty.MP_NORMAL, "normal"),
                                                     ("_ORM", None, "masks"))):
                tp = tdest + "/T_TFA_AR_" + num + suffix
                if not ASSETS.does_asset_exist(tp):
                    continue
                node = lib.create_material_expression(m, unreal.MaterialExpressionTextureSample, -400, k * 260)
                node.texture = unreal.load_asset(tp)
                if typ == "normal":
                    node.sampler_type = unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
                    lib.connect_material_property(node, "RGB", prop)
                elif typ == "masks":
                    node.sampler_type = unreal.MaterialSamplerType.SAMPLERTYPE_MASKS
                    lib.connect_material_property(node, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
                    lib.connect_material_property(node, "G", unreal.MaterialProperty.MP_ROUGHNESS)
                    lib.connect_material_property(node, "B", unreal.MaterialProperty.MP_METALLIC)
                else:
                    lib.connect_material_property(node, "RGB", prop)
            lib.recompile_material(m)
            ASSETS.save_loaded_asset(m)
        sm.set_editor_property("material_interface", unreal.load_asset(mp))
        mats[i] = sm
        report.append((slot, mp))
    mesh.set_editor_property("materials", mats)
    ASSETS.save_loaded_asset(mesh)
    return report


def plan(pack, dest, only="", weapon=True, adapted=None):
    """The list of (kind, source, destination folder) the import will run."""
    jobs = []
    if weapon:
        jobs.append(("rifle", pack, dest + "/Weapon"))
    for f in sorted(glob.glob(os.path.join(pack, "Animations", "Character", "**", "*.fbx"), recursive=True)):
        rel = os.path.relpath(f, os.path.join(pack, "Animations", "Character"))
        if only in rel:
            jobs.append(("clip", f, dest + "/Character/" + os.path.dirname(rel).replace(os.sep, "/")))
    if weapon:
        for f in sorted(glob.glob(os.path.join(pack, "Animations", "Weapon", "**", "*.fbx"), recursive=True)):
            rel = os.path.relpath(f, os.path.join(pack, "Animations", "Weapon"))
            if only in rel and "Magazine" not in os.path.basename(f):
                jobs.append(("weapon_clip", f, dest + "/Weapon/Anims/" + os.path.dirname(rel).replace(os.sep, "/")))
    if adapted:
        for f in sorted(glob.glob(os.path.join(adapted, "*.fbx")) + glob.glob(os.path.join(adapted, "*.glb"))):
            jobs.append(("clip", f, dest + "/Adapted"))
    return jobs


def _run_job(job, opts):
    kind, src, d = job
    if kind == "rifle":
        r = import_rifle(src, d, textures=opts.get("textures", True))
        opts["weapon_skeleton"] = (r.get("SK_TFA_AR_Default_Combined") or {}).get("skeleton")
        return r
    if kind == "clip":
        return import_clip(src, d, opts.get("skeleton", SKELETON))
    if kind == "weapon_clip":
        sk = opts.get("weapon_skeleton")
        if not sk:
            raise RuntimeError("no weapon skeleton")
        return import_clip(src, d, sk.split(".")[0])
    raise RuntimeError(kind)


def _tick(_dt):
    if not _state["queue"]:
        if _state["handle"] is not None:
            unreal.unregister_slate_post_tick_callback(_state["handle"])
            _state["handle"] = None
        _write_status()
        return
    job = _state["queue"].pop(0)
    try:
        r = _run_job(job, _state["opts"])
        if r is None:
            _state["failed"].append({"job": job[1], "error": "nothing imported"})
        else:
            _state["done"].append({"src": os.path.basename(job[1]), "result": r})
    except Exception as ex:  # noqa: BLE001
        _state["failed"].append({"job": job[1], "error": str(ex)[:300]})
    _write_status()


def start(pack, dest="/Game/ThirdParty/InfimaTFA", skeleton=SKELETON, only="", weapon=True, textures=True,
          adapted=None):
    """Queue the import and process one file per editor tick. Returns the number of jobs."""
    _state.update(queue=plan(pack, dest, only, weapon, adapted), done=[], failed=[], t0=time.time(),
                  opts={"skeleton": skeleton, "textures": textures})
    _state["total"] = len(_state["queue"])
    if weapon is False:
        ws = dest + "/Weapon/SK_TFA_AR_Default_Combined"
        if ASSETS.does_asset_exist(ws):
            sk = unreal.load_asset(ws).get_editor_property("skeleton")
            _state["opts"]["weapon_skeleton"] = sk.get_path_name()
    if _state["handle"] is None:
        _state["handle"] = unreal.register_slate_post_tick_callback(_tick)
    _write_status()
    return _state["total"]


def status():
    try:
        return json.load(open(_status_path()))
    except Exception:  # noqa: BLE001
        return None


def run_sync(pack, dest="/Game/ThirdParty/InfimaTFA", skeleton=SKELETON, only="", weapon=True, textures=True,
             adapted=None):
    _state.update(queue=plan(pack, dest, only, weapon, adapted), done=[], failed=[], t0=time.time(),
                  opts={"skeleton": skeleton, "textures": textures})
    _state["total"] = len(_state["queue"])
    while _state["queue"]:
        _tick(0.0)
    s = _write_status()
    print("MI-ANIMPACK", json.dumps(s))
    print("MI-DONE")
    return s


if __name__ == "__main__" and "--pack" in sys.argv:
    a = sys.argv
    kw = {"pack": a[a.index("--pack") + 1]}
    for flag in ("dest", "skeleton", "only", "adapted"):
        if "--" + flag in a:
            kw[flag] = a[a.index("--" + flag) + 1]
    if "--no-weapon" in a:
        kw["weapon"] = False
    run_sync(**kw)
