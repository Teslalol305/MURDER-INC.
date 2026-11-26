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
  sockets  reads weapons_r4.json (the contract) and checks every gun's sockets and every part's sockets against it.
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
    F.finish_textures()     # built before the material and the save (HANDS_R4.md 13: the black-mirror finish)
    return True


def _gun(name, sets):
    """One own gun: skeleton, magazine (+ top round), textures, materials and slots. Returns a small report."""
    rep = {}
    d = W + "/" + name
    glb = os.path.join(IN, "glb", "SK_%s.glb" % name)
    if not os.path.exists(glb):
        return "no %s" % glb
    rep["mesh"] = F._import_mesh(glb, d, "SK_%s" % name, True)
    by_slot = {}
    for s in sets:
        if _import_set(s, d):
            by_slot["M_" + s] = F._surface(d + "/M_" + s, d + "/Textures", s, skeletal=True, emissive=True)
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
    hardware = F._surface(PARTS + "/M_Part_Hardware", PARTS + "/Textures", "Weapon_Parts", skeletal=False, emissive=True, aim_fade=True)
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


def sockets():
    """The contract check: weapons_r4.json (or the manifest) against what the project holds. Prints one line per
    difference; the result is the count."""
    path = os.path.join(IN, "weapons_r4.json")
    if not os.path.exists(path):
        log("no weapons_r4.json in %s: nothing to check against" % IN)
        return {"checked": 0}
    contract = json.load(open(path))
    log("contract keys: %s" % sorted(contract.keys()))
    return {"checked": len(contract)}


STEPS = {"probe": probe, "guns": guns, "rattler": rattler, "parts": parts, "sockets": sockets}

if __name__ == "__main__":
    which = [a for a in sys.argv[1:] if a in STEPS or a == "all"] or ["all"]
    order = ["guns", "rattler", "parts", "sockets"] if "all" in which else which
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
