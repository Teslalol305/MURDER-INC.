"""The batch of the animation pack's CHOPPER adaptation, its weapon-part clips, the manifest and the export
(editor Python of a project that has run ue_import_pack.py and mi_stage.import_chopper(); see docs/unreal/ANIMATION.md).

    import sys; sys.path.insert(0, "<dir of this file>"); import mi_run as R
    R.adapt_all()          # character clips on SK_Mannequin -> /Game/ThirdParty/InfimaTFA/Adapted/{FP,TP}/...
    R.parts_all()          # SK_Chopper part clips -> /Game/Weapons/Chopper/Anims
    R.export_all(out)      # FBX + .uasset copies + manifest.json into out (never into the repository: Fab licence)

Each step writes its report to <project>/Saved/AnimPack/<step>.json and returns it.
"""
import json
import os
import shutil
import sys
import time

import unreal

sys.path.insert(0, os.path.dirname(__file__))
import mi_adapt as D  # noqa: E402
import mi_stage as S  # noqa: E402

ASSETS = unreal.EditorAssetLibrary

# (pack clip under Character/, aimed correction) for the clips that hold the gun normally: hand IK onto our gun
GENERIC = [
    ("FP/Locomotion/A_TFA_FP_AR_Idle_Loop_Standing", False),
    ("FP/Locomotion/A_TFA_FP_AR_Idle_Loop_Aimed", True),
    ("FP/Locomotion/A_TFA_FP_AR_Idle_Loop_Crouched", False),
    ("FP/Locomotion/A_TFA_FP_AR_Walk_F_Loop_Standing", False),
    ("FP/Locomotion/A_TFA_FP_AR_Walk_B_Loop_Standing", False),
    ("FP/Locomotion/A_TFA_FP_AR_Walk_Strafe_L_Loop_Standing", False),
    ("FP/Locomotion/A_TFA_FP_AR_Walk_Strafe_R_Loop_Standing", False),
    ("FP/Locomotion/A_TFA_FP_AR_Walk_F_Loop_Aimed", True),
    ("FP/Locomotion/A_TFA_FP_AR_Walk_B_Loop_Aimed", True),
    ("FP/Locomotion/A_TFA_FP_AR_Walk_Strafe_L_Loop_Aimed", True),
    ("FP/Locomotion/A_TFA_FP_AR_Walk_Strafe_R_Loop_Aimed", True),
    ("FP/Locomotion/A_TFA_FP_AR_Run_F_Loop", False),
    ("FP/Locomotion/A_TFA_FP_AR_Sprint_F_Loop", False),
    ("FP/Locomotion/A_TFA_FP_AR_Jump_Start", False),
    ("FP/Locomotion/A_TFA_FP_AR_Jump_Falling_Loop", False),
    ("FP/Locomotion/A_TFA_FP_AR_Jump_End", False),
    ("FP/Combat/A_TFA_FP_AR_Fire_Semi", False),
    ("FP/Combat/A_TFA_FP_AR_Fire_Auto", False),
    ("FP/Combat/A_TFA_FP_AR_Fire_Aimed", True),
    ("FP/Combat/A_TFA_FP_AR_Fire_Empty", False),
    ("FP/Combat/A_TFA_FP_AR_Melee_Bash_F", False),
    ("FP/Combat/A_TFA_FP_AR_Melee_Swing_L", False),
    ("FP/Transitions/A_TFA_FP_AR_Equip_Quick", False),
    ("FP/Transitions/A_TFA_FP_AR_Holster", False),
    ("FP/Transitions/A_TFA_FP_AR_Transition_Aim_Start", False),
    ("FP/Transitions/A_TFA_FP_AR_Transition_Aim_End", False),
    ("FP/Transitions/A_TFA_FP_AR_Transition_Run_End", False),
    ("FP/Transitions/A_TFA_FP_AR_Transition_Crouch_Start", False),
    ("FP/Transitions/A_TFA_FP_AR_Transition_Crouch_End", False),
    ("FP/Interactions/A_TFA_FP_AR_Inspect", False),
    ("FP/Poses/A_TFA_FP_AR_Aim_Pose", True),
    ("FP/Poses/A_TFA_FP_AR_Idle_Pose_Standing", False),
    ("TP/Locomotion/A_TFA_TP_AR_Idle_Loop", False),
    ("TP/Combat/A_TFA_TP_AR_Fire", False),
    ("TP/Combat/A_TFA_TP_AR_Fire_Empty", False),
    ("TP/Combat/A_TFA_TP_AR_Melee_Bash_F", False),
    ("TP/Combat/A_TFA_TP_AR_Melee_Swing_L", False),
    ("TP/Transitions/A_TFA_TP_AR_Equip_Quick", False),
    ("TP/Transitions/A_TFA_TP_AR_Holster", False),
    ("TP/Transitions/A_TFA_TP_AR_Transition_Aim_Start", False),
    ("TP/Transitions/A_TFA_TP_AR_Transition_Aim_End", False),
    ("TP/Poses/A_TFA_TP_AR_Aim_Pose", False),
    ("TP/Poses/A_TFA_TP_AR_Idle_Pose", False),
    ("TP/Interactions/A_TFA_TP_AR_Inspect", False),
]

# Named sync markers on the adapted reloads (the rules' marks, spec 02 2.3): sound and effect cues for the
# presentation; the ammunition itself moves on the rules' own `magin` event, never on a marker.
RELOAD_MARKERS = {
    "Tactical": [("MagDetach", 0.40), ("MagShow", 0.80), ("MagTouch", 1.15), ("MagAttach", 1.44), ("Tug", 1.565),
                 ("BoltPressCheck", 1.89), ("Done", 2.24)],
    "Empty": [("MagDetach", 0.40), ("MagShow", 0.80), ("MagTouch", 1.15), ("MagAttach", 1.44), ("Tug", 1.565),
              ("BoltBack", 1.96), ("BoltRelease", 2.155), ("Done", 2.72)],
}
FIRE_INTERVAL = 60.0 / 720.0        # spec 02 2.2: 720 rpm


def _report(name, data):
    d = os.path.join(unreal.Paths.project_saved_dir(), "AnimPack")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name + ".json"), "w") as f:
        json.dump(data, f, indent=1, default=str)
    return data


def _markers(anim, marks, track="Chopper"):
    out = []
    for name, t in marks:
        try:
            unreal.AnimationLibrary.add_animation_sync_marker(anim, name, float(t), track)
            out.append(name)
        except Exception as ex:  # noqa: BLE001
            out.append("%s: %s" % (name, str(ex)[:80]))
    ASSETS.save_loaded_asset(anim)
    return out


def adapt_all(only=""):
    t0 = time.time()
    rep = {"generic": [], "reloads": [], "failed": []}
    for rel, aimed in GENERIC:
        if only not in rel:
            continue
        try:
            rep["generic"].append(dict(D.adapt_generic(rel, aimed=aimed), src=rel))
        except Exception as ex:  # noqa: BLE001
            rep["failed"].append({"src": rel, "error": str(ex)[:300]})
    for view in ("FP", "TP"):
        for kind, rc in (("Tactical", D.RELOAD_TACTICAL), ("Empty", D.RELOAD_EMPTY)):
            if only not in "Reload_%s_%s" % (view, kind):
                continue
            try:
                r = D.adapt_reload(rc, view)
                anim = unreal.load_asset(r["dest"])
                chk = [p.get("_check", {}).get("hand_l_err", 0.0) for _, p in r["parts"]]
                rep["reloads"].append({"dest": r["dest"], "src": rc["src"], "view": view, "length": r["length"],
                                       "frames": r["frames"], "markers": _markers(anim, RELOAD_MARKERS[kind]),
                                       "hand_l_err_max_cm": round(max(chk), 2)})
                if view == "FP":
                    _PARTS[kind] = r["parts"]
            except Exception as ex:  # noqa: BLE001
                rep["failed"].append({"src": rc["src"] + " " + view, "error": str(ex)[:300]})
    rep["seconds"] = round(time.time() - t0, 1)
    return _report("adapt", rep)


_PARTS = {}


def _bolt_cycle(t):
    """bolt travel 0..1 of one round: back in 0.020 s, forward in 0.045 s (spec 02 3.17)."""
    if t <= 0.020:
        return t / 0.020
    if t <= 0.065:
        return 1.0 - (t - 0.020) / 0.045
    return 0.0


def parts_all():
    """SK_Chopper clips: Fire (one round at 720 rpm, 120 fps), DryFire, Idle, ReloadTactical, ReloadEmpty."""
    rep = {"clips": []}
    # The compressor resamples bone tracks at 30 fps (the target frame rate cannot be set from Python), which is
    # too coarse for a 65 ms bolt cycle: the clip is 0.1 s (3 frames) and carries the exact cycle as float curves
    # Chopper_Bolt (0..1 of the 92 mm travel) and Chopper_Trigger, keyed at 0, 0.020, 0.065 s. The game drives the
    # bolt bone from the curve (or from FMIViewmodelRig::GetParts), one cycle per WeaponFire, at play rate 1.2 for
    # the 0.0833 s interval.
    fire = [{"bolt": _bolt_cycle(i / 30.0), "trigger": 1.0} for i in range(4)]
    curves = {"Chopper_Bolt": [(0.0, 0.0), (0.020, 1.0), (0.065, 0.0), (0.1, 0.0)],
              "Chopper_Trigger": [(0.0, 1.0), (0.1, 1.0)]}
    rep["clips"].append({"asset": S.chopper_clip("A_Chopper_Fire", fire, rate=30, curves=curves), "length": 0.1,
                         "note": "one round; play once per WeaponFire at rate 0.1 / 0.0833 = 1.2; bolt from the "
                                 "Chopper_Bolt curve"})
    dry = [{"trigger": D.curve([(0.0, 0.0), (0.06, 1.0), (0.20, 1.0), (0.30, 0.0)], i / 30.0)} for i in range(10)]
    rep["clips"].append({"asset": S.chopper_clip("A_Chopper_DryFire", dry, rate=30), "length": 0.3})
    rep["clips"].append({"asset": S.chopper_clip("A_Chopper_Idle", [{}, {}], rate=30), "length": 1.0 / 30})
    for kind in ("Tactical", "Empty"):
        if kind not in _PARTS:
            rc = D.RELOAD_TACTICAL if kind == "Tactical" else D.RELOAD_EMPTY
            _PARTS[kind] = D.adapt_reload(rc, "FP")["parts"]
        pl = [{"bolt": p["bolt"], "mag": p["mag"], "trigger": 0.0} for _, p in _PARTS[kind]]
        name = "A_Chopper_Reload" + kind
        path = S.chopper_clip(name, pl, rate=30)
        anim = unreal.load_asset(path)
        _markers(anim, RELOAD_MARKERS[kind])
        curves = {"Chopper_MagVisible": [(t, p["mag_visible"]) for t, p in _PARTS[kind]],
                  "Chopper_MagInHand": [(t, p["mag_in_hand"]) for t, p in _PARTS[kind]]}
        for cname, pts in curves.items():
            unreal.AnimationLibrary.add_curve(anim, cname, unreal.RawCurveTrackTypes.RCT_FLOAT, False)
            unreal.AnimationLibrary.add_float_curve_keys(anim, cname, [p[0] for p in pts], [p[1] for p in pts])
        ASSETS.save_loaded_asset(anim)
        rep["clips"].append({"asset": path, "length": round(pl and (len(pl) - 1) / 30.0, 4),
                             "markers": [m for m, _ in RELOAD_MARKERS[kind]]})
    return _report("parts", rep)


def _export_fbx(asset_path, out_file):
    a = unreal.load_asset(asset_path)
    t = unreal.AssetExportTask()
    t.set_editor_property("object", a)
    t.set_editor_property("filename", out_file)
    t.set_editor_property("automated", True)
    t.set_editor_property("prompt", False)
    t.set_editor_property("replace_identical", True)
    t.set_editor_property("exporter", unreal.AnimSequenceExporterFBX())
    try:
        o = unreal.FbxExportOption()
        o.set_editor_property("export_morph_targets", False)
        o.set_editor_property("export_local_time", True)
        t.set_editor_property("options", o)
    except Exception:  # noqa: BLE001
        pass
    ok = unreal.Exporter.run_asset_export_task(t)
    return bool(ok) and os.path.exists(out_file)


def _uasset_file(asset_path):
    rel = asset_path.split(".")[0]
    assert rel.startswith("/Game/")
    return os.path.join(unreal.Paths.project_content_dir(), rel[len("/Game/"):] + ".uasset")


def export_all(out="/project/ue/packs/tactical-rifle/adapted"):
    """FBX of every adapted and part clip, the .uasset copies (same engine version, same skeleton paths), manifest."""
    adapt = json.load(open(os.path.join(unreal.Paths.project_saved_dir(), "AnimPack", "adapt.json")))
    parts = json.load(open(os.path.join(unreal.Paths.project_saved_dir(), "AnimPack", "parts.json")))
    man = {"made": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "engine": unreal.SystemLibrary.get_engine_version(),
           "skeleton": D.SKELETON, "gun_skeleton": "/Game/Weapons/Chopper/SK_Chopper_Skeleton",
           "licence": "derived from the Infima Games Tactical FPS Animation Pack (Fab standard licence): use in the "
                      "game, never publish, never commit", "character": [], "gun": []}
    for sub in ("fbx", "fbx/chopper", "uasset"):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    rows = [(r["dest"], r["src"], r.get("length"), r.get("aimed"), None) for r in adapt["generic"]] + \
           [(r["dest"], r["src"] + " " + r["view"], r["length"], False, r["markers"]) for r in adapt["reloads"]]
    for dest, src, length, aimed, markers in rows:
        name = dest.rsplit("/", 1)[1]
        f = os.path.join(out, "fbx", name + ".fbx")
        ok = _export_fbx(dest, f)
        u = _uasset_file(dest)
        ud = os.path.join(out, "uasset", dest[len("/Game/"):] + ".uasset")
        os.makedirs(os.path.dirname(ud), exist_ok=True)
        shutil.copy2(u, ud)
        man["character"].append({"asset": dest, "source": src, "length": length, "aimed": aimed,
                                 "markers": markers, "fbx": os.path.relpath(f, out) if ok else None,
                                 "uasset": os.path.relpath(ud, out)})
    for c in parts["clips"]:
        dest = c["asset"]
        name = dest.rsplit("/", 1)[1]
        f = os.path.join(out, "fbx", "chopper", name + ".fbx")
        ok = _export_fbx(dest, f)
        u = _uasset_file(dest)
        ud = os.path.join(out, "uasset", dest[len("/Game/"):] + ".uasset")
        os.makedirs(os.path.dirname(ud), exist_ok=True)
        shutil.copy2(u, ud)
        man["gun"].append(dict(c, fbx=os.path.relpath(f, out) if ok else None, uasset=os.path.relpath(ud, out)))
    with open(os.path.join(out, "manifest.json"), "w") as fh:
        json.dump(man, fh, indent=1)
    return _report("export", {"out": out, "character": len(man["character"]), "gun": len(man["gun"]),
                              "fbx_missing": [r["asset"] for r in man["character"] + man["gun"] if not r["fbx"]]})


# ---------------------------------------------------------------- pictures (scenes for mi_mcp.py shot)
def pack_row():
    """Five mannequins with the pack's own rifle: FP aimed idle, FP fire, FP tactical (Quick) reload, FP empty
    reload, TP reload; returns the camera for the row."""
    S.stage()
    rows = [("FP/Locomotion/A_TFA_FP_AR_Idle_Loop_Aimed", 0.0, None),
            ("FP/Combat/A_TFA_FP_AR_Fire_Semi", 0.05, "FP/A_TFA_FP_WEP_AR_Fire"),
            ("FP/Combat/A_TFA_FP_AR_Reload_Quick", 1.0, "FP/A_TFA_FP_WEP_AR_Reload_Quick"),
            ("FP/Combat/A_TFA_FP_AR_Reload_Empty", 2.0, "FP/A_TFA_FP_WEP_AR_Reload_Empty"),
            ("TP/Combat/A_TFA_TP_AR_Reload", 1.2, "TP/A_TFA_TP_WEP_AR_Reload")]
    labels = []
    for i, (clip, t, wep) in enumerate(rows):
        loc = (i * 110.0 - 220.0, 0.0, 0.0)
        g = D.PACK + "/Weapon/Anims/" + wep if wep else None
        labels += S.rig(D.PACK + "/Character/" + clip, t, loc=loc, yaw=-55.0, label="P%d" % i, gun="pack",
                        gun_anim=g, mag=True)
        if wep:
            labels += _reserve_mag("P%d" % i)
    return {"labels": labels, "cam": (0.0, 520.0, 150.0, -8.0, -90.0, 0.0), "fov": 50}


def _reserve_mag(label):
    g = [a for a in S.ACTORS.get_all_level_actors() if a.get_actor_label() == label + "_Rifle"][0]
    m = S._skel_actor(D.PACK + "/Weapon/SK_TFA_AR_Magazine", None, (0, 0, 0), 0.0, 0, label + "_PackMagR")
    m.attach_to_actor(g, "Magazine_Reserve", unreal.AttachmentRule.SNAP_TO_TARGET,
                      unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.KEEP_WORLD, False)
    return [m.get_actor_label()]


def gun_cam(label="C_Chopper", side=-1.0, dist=75.0, fwd=18.0, up=4.0):
    """A camera square to the gun's side (side -1: its left, where the CHOPPER's charging handle is), aimed at the
    receiver: 'x,y,z,pitch,yaw,roll' for mi_mcp.py shot."""
    g = [a for a in S.ACTORS.get_all_level_actors() if a.get_actor_label() == label][0]
    tr = g.get_actor_transform()
    target = tr.transform_location(unreal.Vector(fwd, 0.0, 0.0))
    eye = tr.transform_location(unreal.Vector(fwd, side * dist, up))
    r = unreal.MathLibrary.find_look_at_rotation(eye, target)
    return "%.2f,%.2f,%.2f,%.2f,%.2f,%.2f" % (eye.x, eye.y, eye.z, r.pitch, r.yaw, r.roll)


def chopper_fp(clip, t, gun_clip=None, mesh=None, yaw=0.0):
    """SK_RuleArms (or the mannequin) playing an adapted clip at t with the CHOPPER; returns the eye camera."""
    S.stage()
    mesh = mesh or (S.ARMS if ASSETS.does_asset_exist(S.ARMS) else D.MANNY)
    labels = S.rig(clip, t, loc=(0, 0, 0), yaw=yaw, label="C", mesh=mesh, gun_anim=gun_clip, gun="chopper")
    return {"labels": labels, "cam": S.eye((0, 0, 0), yaw), "mesh": mesh}
