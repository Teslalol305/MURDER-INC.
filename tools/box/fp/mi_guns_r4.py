"""Weapons round 4 into THIS clone's game project, headless (our own art only; nothing the pack made is touched):

    MI_FP_IN=/project/ue/fp-in-guns bash tools/box/fp/import-chars.sh r4 [probe|guns|rattler|parts|sockets|all]

Inputs: the folder fp-art.sh unpack made (default /project/ue/fp-in-guns, never the shared /project/ue/fp-in): glb/,
textures/<Set>/T_<Set>_{BC,N,ORM[,E]}.png, manifest.json and weapons_r4.json when they exist. Re-runnable: every asset is
replaced in place (the same paths), so a re-export of a gun or a part reaches the game with no data change.

  probe    SK_Shorty and SK_Chopper into /Game/Probe (scratch, removed again): what the importer makes of the exported
           skeleton (bone names, reference poses in component space, the rotation the glTF axes leave on every bone),
           the mesh's bounds and slots. One line each, "MI-PROBE ...". Decides how a part is put on a bone socket.
  guns     /Game/Weapons/<Gun>/SK_<Gun> for Chopper, Nine, Shorty, Stretch (own skeletons), their magazines
           (SM_Weapon_<Gun>Magazine + _TopRound, authored in the gun's space), the texture sets and the materials
           (M_<Set>: BC, N, ORM and E where the set has one), the brass.
  rattler  the same for SK_Rattler (its final bake arrives later than the others: one step of its own).
  parts    /Game/Weapons/Parts/SM_Part_* (static, origin = the mount), their sockets from the .sockets.json (Blender
           metres, X bore, Y left, Z up: Unreal (x, -y, z) x 100), M_Part_Hardware / M_Part_Mags on the two parts sets,
           M_Part_Lens (flat smoked glass) and M_Part_Reticle (the collimated dot along +X: OUR parts look along +X, the
           pack's along +Y).
  sockets  reads weapons_r4.json (the contract) and compares it with the project to 0.01 cm: every gun's bone heads and
           socket bones (the imported skeleton's reference pose, each with the importer's quarter turn about X, BOX.md),
           its eject direction (presentation ejectDir) and hide bones (guns.json mounts), every part's mesh sockets. One
           "MI-R4 DIFF" line per difference; the step's result is their count (0 = the contract is kept).
The guns' materials carry the tiling detail of the manifest's slot records (TS_GunDetail_Steel where ORM.B = 1, and
TS_GunDetail_Polymer where ORM.B = 0 on the slots that name it), on UV 0 x the slot's detail_repeat_per_uv; the sets are
imported once into /Game/Weapons/Detail.
"""
import json
import math
import os
import sys

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "chars"))
sys.path.insert(0, HERE)
import mi_chars as C  # noqa: E402
import mi_fp_import as F  # noqa: E402  (the NINE's importer helpers, used as they are)

IN = os.environ.get("MI_FP_IN", "/project/ue/fp-in-guns")
F.IN = IN
ASSETS = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
W = "/Game/Weapons"
REPORT = {}

# gun -> (folder name, texture sets that skin it, material slot -> set)
GUNS = {
    "Chopper": ("Chopper", ["Chopper", "Chopper_Furniture", "Chopper_Front"]),
    "Nine": ("Nine", ["Nine"]),
    "Shorty": ("Shorty", ["Shorty"]),
    "Stretch": ("Stretch", ["Stretch"]),
    "Rattler": ("Rattler", ["Rattler"]),
}
PARTS = W + "/Parts"
DETAIL = W + "/Detail"      # the guns' shared tiling detail sets (TS_GunDetail_Steel, TS_GunDetail_Polymer)


def log(msg):
    unreal.log_warning("MI-R4 " + msg)


def _q(q):
    return [round(q.x, 5), round(q.y, 5), round(q.z, 5), round(q.w, 5)]


def _v(v):
    return [round(v.x, 3), round(v.y, 3), round(v.z, 3)]


# ----------------------------------------------------------------------------------------------------------- probe
def _bone_table(mesh):
    """name -> (parent name or '', local transform, component-space transform) from the skeleton's reference pose."""
    sk = mesh.get_editor_property("skeleton")
    pose = unreal.AnimPoseExtensions.get_reference_pose(sk)
    names = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(pose)]
    out = {}
    for n in names:
        nm = unreal.Name(n)
        cs = unreal.AnimPoseExtensions.get_ref_bone_pose(pose, nm, unreal.AnimPoseSpaces.WORLD)
        loc = unreal.AnimPoseExtensions.get_ref_bone_pose(pose, nm, unreal.AnimPoseSpaces.LOCAL)
        par = ""
        try:
            par = str(unreal.AnimPoseExtensions.get_bone_parent_name(pose, nm)) if hasattr(unreal.AnimPoseExtensions, "get_bone_parent_name") else ""
        except Exception:  # noqa: BLE001
            par = ""
        out[n] = (par, loc, cs)
    return out


def probe_mesh(path):
    mesh = unreal.load_asset(path)
    if mesh is None:
        print("MI-PROBE %s MISSING" % path)
        return None
    name = path.rsplit("/", 1)[1]
    b = mesh.get_bounds()
    o, e = b.origin, b.box_extent
    print("MI-PROBE %s bounds origin %s extent %s (cm; min %s max %s)" % (
        name, _v(o), _v(e), _v(unreal.Vector(o.x - e.x, o.y - e.y, o.z - e.z)), _v(unreal.Vector(o.x + e.x, o.y + e.y, o.z + e.z))))
    slots = [str(s.get_editor_property("material_slot_name")) for s in mesh.get_editor_property("materials")]
    print("MI-PROBE %s slots %s" % (name, slots))
    tab = _bone_table(mesh)
    for n, (par, loc, cs) in tab.items():
        r = cs.rotation
        rot = cs.rotation.rotator()
        print("MI-PROBE %s bone %-14s parent %-10s cs_loc_cm %s cs_quat %s cs_rot(r,p,y) [%.2f %.2f %.2f] local_loc %s local_quat %s scale %s" % (
            name, n, par, _v(cs.translation), _q(r), rot.roll, rot.pitch, rot.yaw, _v(loc.translation), _q(loc.rotation), _v(cs.scale3d)))
    return tab


def probe():
    rep = {}
    # the NINE that is already in the project (the old export) and the two new ones, imported into a scratch folder
    rep["nine_old"] = bool(probe_mesh(W + "/Nine/SK_Nine.SK_Nine"))
    for g in ("Shorty", "Chopper"):
        glb = os.path.join(IN, "glb", "SK_%s.glb" % g)
        if not os.path.exists(glb):
            print("MI-PROBE no %s" % glb)
            continue
        p = F._import_mesh(glb, "/Game/Probe", "SK_%s" % g, True)
        rep[g] = bool(probe_mesh(p + "." + p.rsplit("/", 1)[1]))
    try:
        ASSETS.delete_directory("/Game/Probe")
    except Exception as e:  # noqa: BLE001
        log("probe folder not removed: %s" % e)
    return rep


# ---------------------------------------------------------------------------------------------------------- guns
def _sets_in():
    d = os.path.join(IN, "textures")
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


def _import_set(set_name, dest):
    folder = os.path.join(IN, "textures", set_name)
    if not os.path.isdir(folder):
        log("no texture set %s" % folder)
        return False
    C.import_textures(folder, dest + "/Textures")
    return True


_MANIFEST = []
_DETAIL_SETS = {}


def _manifest_assets():
    """art/out/manifest.json's assets (it travels in the parts archive), {} when it is not in the input folder."""
    if not _MANIFEST:
        p = os.path.join(IN, "manifest.json")
        _MANIFEST.append(json.load(open(p)).get("assets", {}) if os.path.exists(p) else {})
    return _MANIFEST[0]


def _detail_tex(set_name):
    """A tiling detail set (TS_GunDetail_Steel, TS_GunDetail_Polymer) imported once into /Game/Weapons/Detail: the texture
    path prefix /Game/Weapons/Detail/Textures/T_<Set>, or None when the input folder does not carry it."""
    if set_name not in _DETAIL_SETS:
        ok = _import_set(set_name, DETAIL) and ASSETS.does_asset_exist("%s/Textures/T_%s_N" % (DETAIL, set_name)) \
            and ASSETS.does_asset_exist("%s/Textures/T_%s_ORM" % (DETAIL, set_name))
        _DETAIL_SETS[set_name] = "%s/Textures/T_%s" % (DETAIL, set_name) if ok else None
    return _DETAIL_SETS[set_name]


def _detail_for(asset, slot):
    """The slot's tiling detail from its manifest record (detail_set + detail_repeat_per_uv, and detail_set_polymer +
    detail_polymer_repeat_per_uv where the slot has one): the `detail` argument of F._surface, or (None, why)."""
    rec = next((r for r in (_manifest_assets().get(asset) or {}).get("material_slots", []) if r.get("slot") == slot), None)
    if rec is None:
        return None, "no manifest record of %s %s" % (asset, slot)
    if not rec.get("detail_set"):
        return None, "the manifest gives %s %s no detail" % (asset, slot)
    if not rec.get("detail_repeat_per_uv"):
        return None, "%s %s: no detail_repeat_per_uv (the set has no texel density)" % (asset, slot)
    steel = _detail_tex(rec["detail_set"])
    if steel is None:
        return None, "no texture set %s in %s" % (rec["detail_set"], IN)
    det = {"steel": (steel, rec["detail_repeat_per_uv"]), "polymer": None}
    if rec.get("detail_set_polymer"):
        poly = _detail_tex(rec["detail_set_polymer"])
        if poly is None or not rec.get("detail_polymer_repeat_per_uv"):
            return None, "%s %s: polymer detail %s missing" % (asset, slot, rec["detail_set_polymer"])
        det["polymer"] = (poly, rec["detail_polymer_repeat_per_uv"])
    return det, None


def _gun(name, sets):
    """One own gun: skeleton, magazine (+ top round), textures, materials (with the manifest's tiling detail) and slots.
    Returns a small report."""
    rep = {}
    d = W + "/" + name
    glb = os.path.join(IN, "glb", "SK_%s.glb" % name)
    if not os.path.exists(glb):
        return "no %s" % glb
    rep["mesh"] = F._import_mesh(glb, d, "SK_%s" % name, True)
    by_slot = {}
    rep["detail"] = {}
    for s in sets:
        if _import_set(s, d):
            det, why = _detail_for("SK_" + name, "M_" + s)
            if det is None:
                log("SK_%s M_%s: built WITHOUT the tiling detail: %s" % (name, s, why))
            rep["detail"]["M_" + s] = {k: v[1] for k, v in det.items() if v} if det else "none: " + why
            by_slot["M_" + s] = F._surface(d + "/M_" + s, d + "/Textures", s, skeletal=True, emissive=True, detail=det)
    rep["slots"] = F._assign_all(rep["mesh"], by_slot)
    # the magazine, authored in the gun's own space (origin = the gun's origin), and its top round
    mset = "Weapon_%sMagazine" % name
    mag = os.path.join(IN, "glb", "SM_Weapon_%sMagazine.glb" % name)
    if os.path.exists(mag):
        _import_set(mset, d)
        mat = F._surface(d + "/M_" + mset, d + "/Textures", mset, skeletal=False)
        for n in ("SM_Weapon_%sMagazine" % name, "SM_Weapon_%sMagazine_TopRound" % name):
            g = os.path.join(IN, "glb", n + ".glb")
            if os.path.exists(g):
                p = F._import_mesh(g, d, n, False)
                F._assign_all(p, {"M_": mat})
                rep[n] = p
    return rep


def guns(which=("Chopper", "Nine", "Shorty", "Stretch")):
    rep = {}
    for g in which:
        rep[g] = _gun(g, GUNS[g][1])
    # the brass: ours (a rifle round and a pistol round), one material each
    for n in ("Rifle", "Pistol"):
        g = os.path.join(IN, "glb", "SM_Weapon_Casing%s.glb" % n)
        if os.path.exists(g):
            d = W + "/Casings"
            _import_set("Weapon_Casing%s" % n, d)
            mat = F._surface(d + "/M_Weapon_Casing%s" % n, d + "/Textures", "Weapon_Casing%s" % n, skeletal=False)
            p = F._import_mesh(g, d, "SM_Weapon_Casing%s" % n, False)
            F._assign_all(p, {"M_": mat})
            rep["casing" + n] = p
    return rep


def rattler():
    return {"Rattler": _gun("Rattler", GUNS["Rattler"][1])}


# ---------------------------------------------------------------------------------------------------------- parts
LENS_NAME = "M_Part_Lens"
RETICLE_NAME = "M_Part_Reticle"

# the part's optical axis is +X (our parts are modelled with the bore along +X); the pack's ran along +Y
RETICLE_HLSL = """
float3 v = normalize(-Cam);
float3 f = normalize(Fwd);
float a = acos(clamp(dot(v, f), -1.0, 1.0));      // angle off the sight axis, radians
float dotm = 1.0 - smoothstep(DotR * 0.7, DotR, a);
float ring = 1.0 - smoothstep(RingW * 0.5, RingW, abs(a - RingR));
return saturate(dotm + 0.85 * ring);
"""


def _lens(path):
    """Smoked optical glass: translucent, thin, two-sided (the pack's glass, rebuilt here from our own numbers)."""
    m = F._material(path)
    F._set(m, blend_mode=unreal.BlendMode.BLEND_TRANSLUCENT,
           translucency_lighting_mode=unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING,
           two_sided=True, used_with_skeletal_mesh=True)
    tint = F._vector(m, "Tint", (0.035, 0.045, 0.05), -500, -200)
    MEL.connect_material_property(tint, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(F._scalar(m, "Opacity", 0.22, -500, 0), "", unreal.MaterialProperty.MP_OPACITY)
    MEL.connect_material_property(F._scalar(m, "Roughness", 0.04, -500, 100), "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(F._scalar(m, "Specular", 0.9, -500, 200), "", unreal.MaterialProperty.MP_SPECULAR)
    return F._finish(m, path)


def _reticle(path):
    """Collimated illuminated reticle on the sight's reticle plane: drawn where the view ray is parallel to the sight's
    axis (the part's +X), so the dot stays on the point of aim at any eye position (no parallax)."""
    m = F._material(path)
    F._set(m, blend_mode=unreal.BlendMode.BLEND_ADDITIVE, shading_model=unreal.MaterialShadingModel.MSM_UNLIT,
           two_sided=True, used_with_skeletal_mesh=True)
    cam = F._expr(m, unreal.MaterialExpressionCameraVectorWS, -900, -100)
    axis = F._expr(m, unreal.MaterialExpressionConstant3Vector, -1100, 100)
    axis.set_editor_property("constant", unreal.LinearColor(1, 0, 0, 0))
    tv = F._expr(m, unreal.MaterialExpressionTransform, -900, 100,
                 transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
                 transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    MEL.connect_material_expressions(axis, "", tv, "")
    cu = F._custom(m, -600, 0, RETICLE_HLSL, ["Cam", "Fwd", "DotR", "RingR", "RingW"])
    MEL.connect_material_expressions(cam, "", cu, "Cam")
    MEL.connect_material_expressions(tv, "", cu, "Fwd")
    for i, (nm, val) in enumerate((("DotR", 0.0015), ("RingR", 0.016), ("RingW", 0.0009))):
        MEL.connect_material_expressions(F._scalar(m, nm, val, -900, 300 + 90 * i), "", cu, nm)
    col = F._vector(m, "Color", (1.0, 0.04, 0.02), -600, 250)
    br = F._scalar(m, "Brightness", 40.0, -600, 400)
    m1 = F._expr(m, unreal.MaterialExpressionMultiply, -350, 100)
    m2 = F._expr(m, unreal.MaterialExpressionMultiply, -200, 150)
    MEL.connect_material_expressions(cu, "", m1, "A")
    MEL.connect_material_expressions(col, "", m1, "B")
    MEL.connect_material_expressions(m1, "", m2, "A")
    MEL.connect_material_expressions(br, "", m2, "B")
    MEL.connect_material_property(m2, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return F._finish(m, path)


def _put_static_socket(mesh, name, loc_cm):
    s = mesh.find_socket(name)
    if s is None:
        s = unreal.StaticMeshSocket(mesh)
        F._set(s, socket_name=name)
        mesh.add_socket(s)
        s = mesh.find_socket(name)
    F._set(s, relative_location=unreal.Vector(*loc_cm), relative_rotation=unreal.Rotator(0, 0, 0),
           relative_scale=unreal.Vector(1, 1, 1))


def parts():
    rep = {}
    gd = os.path.join(IN, "glb")
    names = sorted(f[:-4] for f in os.listdir(gd) if f.startswith("SM_Part_") and f.endswith(".glb")) if os.path.isdir(gd) else []
    for s in ("Weapon_Parts", "Weapon_PartsMags"):
        _import_set(s, PARTS)
    hardware = F._surface(PARTS + "/M_Part_Hardware", PARTS + "/Textures", "Weapon_Parts", skeletal=False, emissive=True)
    mags = F._surface(PARTS + "/M_Part_Mags", PARTS + "/Textures", "Weapon_PartsMags", skeletal=False)
    lens = _lens(PARTS + "/" + LENS_NAME)
    ret = _reticle(PARTS + "/" + RETICLE_NAME)
    by_slot = {"M_Part_Hardware": hardware, "M_Part_Mags": mags, "M_Part_Lens": lens, "M_Part_Reticle": ret}
    for n in names:
        p = F._import_mesh(os.path.join(gd, n + ".glb"), PARTS, n, False)
        F._assign_all(p, by_slot)
        sj = os.path.join(gd, n + ".sockets.json")
        socks = {}
        if os.path.exists(sj):
            mesh = unreal.load_asset(p)
            for sn, m in (json.load(open(sj)).get("sockets") or {}).items():
                loc = (m[0] * 100.0, -m[1] * 100.0, m[2] * 100.0)
                _put_static_socket(mesh, sn, loc)
                socks[sn] = [round(c, 3) for c in loc]
            ASSETS.save_loaded_asset(mesh)
        rep[n] = socks
    return rep


# ------------------------------------------------------------------------------------------------- the contract check
TOL_CM = 0.01               # every position: bone heads, socket bones, mesh sockets, part sockets
TOL_DIR = 1e-3              # a unit direction (the eject direction), per component
TOL_TURN_RAD = 1e-3         # a bone's turn: 1 mrad moves a point 10 cm away by 0.01 cm
# Interchange leaves the same quarter turn about X on every bone of our exported skeletons (BOX.md, "Every bone of an
# exported skeleton carries the same turn"): component-space quaternion (x, y, z, w) = (0.707, 0, 0, 0.707); the contract's
# rest orientation is the identity (local X = the bore). UMIGunAssembly undoes the turn, so any other turn is a difference.
BONE_TURN = (math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5))


def _far(a, b, tol):
    """None when the two 3-vectors agree to tol, else the largest component difference."""
    if a is None or b is None or len(a) != 3 or len(b) != 3:
        return float("inf")
    d = max(abs(float(x) - float(y)) for x, y in zip(a, b))
    return d if d > tol else None


def _unit(v):
    n = math.sqrt(sum(float(c) * float(c) for c in v)) or 1.0
    return [float(c) / n for c in v]


def _turn_off(q, ref=BONE_TURN):
    """Angle in radians between quaternion q (x, y, z, w) and ref."""
    d = abs(sum(float(a) * float(b) for a, b in zip(_unit(q), ref)))
    return 2.0 * math.acos(min(1.0, d))


def _r(v, n=3):
    return [round(float(c), n) for c in v]


def compare_gun(gid, g, bones, mesh_sockets, mounts, eject_web, mesh_offset_rot):
    """One gun of weapons_r4.json against the project. Pure (no unreal), so it is testable off the box.
      g              weapons_r4.json guns.<gid>
      bones          the imported skeleton's reference pose: name -> (component-space location cm, quaternion (x, y, z, w)),
                     None when the mesh is not in the project
      mesh_sockets   name -> component-space location cm of a skeletal mesh socket of that name (it would shadow the bone)
      mounts         guns.json guns.<gid>.mounts (slot -> {socket, hide, ...}), None when the gun is not in guns.json
      eject_web      the presentation's ejectDir (web gun space: x right, y up, z to the eye), None when the data has none
      mesh_offset_rot  the presentation's meshOffset.rot ([0, 0, 0] for our guns)
    Returns (differences, notes): lists of strings."""
    diff, notes = [], []
    mesh = g.get("mesh", gid)
    if bones is None:
        return ["%s: %s is not in the project" % (gid, mesh)], notes
    want = [(n, b["head_unreal_cm"], "bone") for n, b in sorted((g.get("bones") or {}).items())]
    want += [(n, s["unreal_cm"], "socket") for n, s in sorted((g.get("sockets") or {}).items())]
    for name, cm, kind in want:
        if name not in bones:
            diff.append("%s: %s %s missing in %s" % (gid, kind, name, mesh))
            continue
        loc, quat = bones[name]
        d = _far(loc, cm, TOL_CM)
        if d is not None:
            diff.append("%s: %s %s at %s cm in the project, contract %s (off %.4f cm)" % (gid, kind, name, _r(loc), cm, d))
        a = _turn_off(tuple(quat))
        if a > TOL_TURN_RAD:
            diff.append("%s: %s %s turned %s (x, y, z, w), not the importer's quarter turn about X (off %.2f deg)" % (
                gid, kind, name, _r(quat, 5), math.degrees(a)))
        if name in mesh_sockets:
            d = _far(mesh_sockets[name], cm, TOL_CM)
            if d is not None:
                diff.append("%s: the mesh socket %s (it shadows the bone) at %s cm, contract %s" % (gid, name, _r(mesh_sockets[name]), cm))
    extra = sorted(set(bones) - {n for n, _c, _k in want} - {"body"})
    if extra:
        notes.append("%s: bones in %s that the contract does not list (not counted): %s" % (gid, mesh, extra))
    # eject direction: the project's ejectDir is in web gun space, read through meshOffset (the identity for our guns)
    if eject_web is None:
        notes.append("%s: the project data has no ejectDir (by design for the CHOPPER and the NINE, WEAPONS_R4_TESTS.md); "
                     "the contract's %s is not compared" % (gid, g.get("eject_dir_unreal")))
    elif any(abs(float(c)) > 1e-9 for c in (mesh_offset_rot or (0, 0, 0))):
        diff.append("%s: meshOffset.rot %s is not the identity: the mesh is turned against gun space" % (gid, mesh_offset_rot))
    else:
        e = eject_web
        got = _unit([-float(e[2]), float(e[0]), float(e[1])])
        exp = _unit(g.get("eject_dir_unreal") or [0, 0, 0])
        if _far(got, exp, TOL_DIR) is not None:
            diff.append("%s: ejectDir %s (web) = %s in Unreal gun space, contract %s" % (gid, e, _r(got, 4), _r(exp, 4)))
    # hide bones: guns.json mounts.<slot>.hide against hide_bones_when_fitted, and every one a bone of the mesh
    hide = g.get("hide_bones_when_fitted") or {}
    if mounts is None:
        diff.append("%s: not in guns.json (no mounts to hold hide bones)" % gid)
        mounts = {}
    slots = sorted(set(hide) | {k for k, v in mounts.items() if isinstance(v, dict) and v.get("hide")})
    for slot in slots:
        have = sorted((mounts.get(slot) or {}).get("hide") or []) if isinstance(mounts.get(slot), dict) else []
        if have != sorted(hide.get(slot) or []):
            diff.append("%s: mounts.%s.hide %s in guns.json, contract %s" % (gid, slot, have, sorted(hide.get(slot) or [])))
        for b in hide.get(slot) or []:
            if b not in bones:
                diff.append("%s: hide bone %s (slot %s) is not a bone of %s" % (gid, b, slot, mesh))
    return diff, notes


def compare_part(pid, rec, mesh_sockets):
    """One part of weapons_r4.json: sockets_unreal_cm against the static mesh's sockets (name -> relative location cm),
    mesh_sockets None when the mesh is not in the project. Returns the differences."""
    if mesh_sockets is None:
        return ["part %s: %s is not in the project" % (pid, rec.get("mesh"))]
    diff = []
    for name, cm in sorted((rec.get("sockets_unreal_cm") or {}).items()):
        if name not in mesh_sockets:
            diff.append("part %s: socket %s missing on %s" % (pid, name, rec.get("mesh")))
            continue
        d = _far(mesh_sockets[name], cm, TOL_CM)
        if d is not None:
            diff.append("part %s: socket %s at %s cm on %s, contract %s (off %.4f cm)" % (pid, name, _r(mesh_sockets[name]), rec.get("mesh"), cm, d))
    return diff


def _project_data():
    """Content/Data/guns.json and presentation.json of this project (the presentation $refs resolved per gun)."""
    data = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()), "Data")
    guns_json = json.load(open(os.path.join(data, "guns.json")))
    pres = json.load(open(os.path.join(data, "presentation.json")))
    out = {}
    for gid, g in (guns_json.get("guns") or {}).items():
        p = g.get("presentation") or {}
        ref = p.get("$ref") if isinstance(p, dict) else None
        if ref:
            node = pres
            for k in ref.split("#", 1)[1].split("."):
                node = (node or {}).get(k)
            p = node or {}
        real = p.get("real") if isinstance(p.get("real"), dict) else {}     # the real mesh's numbers win (MILoadoutResolver)
        mo = real.get("meshOffset", p.get("meshOffset")) or {}
        out[gid] = {"mounts": g.get("mounts"), "eject": real.get("ejectDir", p.get("ejectDir")), "mesh_offset_rot": mo.get("rot")}
    return out


def _skeleton_now(path):
    """(bones, mesh sockets) of a skeletal mesh in the project: see compare_gun. (None, {}) when it is missing."""
    mesh = unreal.load_asset(path) if ASSETS.does_asset_exist(path) else None
    if mesh is None:
        return None, {}
    tab = _bone_table(mesh)
    bones = {n: ([cs.translation.x, cs.translation.y, cs.translation.z],
                 (cs.rotation.x, cs.rotation.y, cs.rotation.z, cs.rotation.w)) for n, (_p, _l, cs) in tab.items()}
    socks = {}
    for n in bones:
        s = mesh.find_socket(n)
        if s is None:
            continue
        bone = str(s.get_editor_property("bone_name"))
        if bone in tab:
            p = tab[bone][2].transform_location(s.get_editor_property("relative_location"))
            socks[n] = [p.x, p.y, p.z]
    return bones, socks


def _static_sockets_now(path):
    mesh = unreal.load_asset(path) if ASSETS.does_asset_exist(path) else None
    if mesh is None:
        return None
    out = {}
    for s in mesh.get_editor_property("sockets") or []:
        v = s.get_editor_property("relative_location")
        out[str(s.get_editor_property("socket_name"))] = [v.x, v.y, v.z]
    return out


def sockets():
    """The contract check: weapons_r4.json against what the project holds. Per gun every bone head and socket bone of the
    imported skeleton (component space, 0.01 cm; each with the importer's quarter turn about X), a skeletal mesh socket
    of the same name, the eject direction (presentation ejectDir) and the hide bones (guns.json mounts); per part the
    static mesh's sockets. Prints one line per difference ("MI-R4 DIFF ...") and returns their count."""
    path = os.path.join(IN, "weapons_r4.json")
    if not os.path.exists(path):
        log("DIFF no weapons_r4.json in %s: nothing to check against" % IN)
        return 1
    contract = json.load(open(path))
    proj = _project_data()
    diff, notes, checked = [], [], 0
    for gid, g in sorted((contract.get("guns") or {}).items()):
        mesh = g.get("mesh", "SK_" + gid.capitalize())
        bones, socks = _skeleton_now("%s/%s/%s.%s" % (W, mesh[3:], mesh, mesh))
        p = proj.get(gid) or {}
        d, n = compare_gun(gid, g, bones, socks, p.get("mounts") if gid in proj else None, p.get("eject"), p.get("mesh_offset_rot"))
        diff += d
        notes += n
        checked += len(g.get("bones") or {}) + len(g.get("sockets") or {})
    for pid, rec in sorted((contract.get("parts") or {}).items()):
        diff += compare_part(pid, rec, _static_sockets_now("%s/%s.%s" % (PARTS, rec["mesh"], rec["mesh"])))
        checked += len(rec.get("sockets_unreal_cm") or {})
    for n in notes:
        log("note " + n)
    for d in diff:
        log("DIFF " + d)
    log("sockets: %d differences (%d guns, %d parts, %d positions checked)" % (
        len(diff), len(contract.get("guns") or {}), len(contract.get("parts") or {}), checked))
    return len(diff)


STEPS = {"probe": probe, "guns": guns, "rattler": rattler, "parts": parts, "sockets": sockets}

if __name__ == "__main__":
    which = [a for a in sys.argv[1:] if a in STEPS or a == "all"] or ["all"]
    order = ["guns", "rattler", "parts", "sockets"] if "all" in which else which
    for s in order:
        try:
            REPORT[s] = STEPS[s]()
            print("MI-FP %s ok" % s if s != "sockets" else "MI-FP sockets %d differences" % REPORT[s])
        except Exception as e:   # noqa: BLE001  (one step failing must not hide the others' results)
            import traceback
            traceback.print_exc()
            REPORT[s] = "FAILED: %s" % e
            print("MI-FP %s FAILED %s" % (s, e))
    print("MI-FP-REPORT " + json.dumps(REPORT)[:6000])
    print("MI-DONE")
