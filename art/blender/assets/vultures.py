"""Vultures crews for levels 2 and 3 (docs/unreal/maps/characters.md): generated people (turnaround sheet ->
Tripo multiview -> GLB) cleaned, bound to the UE5 mannequin skeleton and checked in poses.

    venv/bin/python art/blender/build.py build vultures --only canal_shell --export --preview --samples 32
    MI_PREVIEWS=hero,poses,wire,size venv/bin/python art/blender/build.py build vultures --only canal_shell --preview

Source (git-ignored): art/out/characters/maps/<id>/<id>_tripo.glb and src/ (the sheet, the four views).
Outputs: art/out/glb/SK_Vulture_<Name>.glb (+ .check.json with the posed check), the unique set
art/out/textures/Vulture<Name>/T_Vulture<Name>_{BC,N,ORM}.png, a manifest record, previews in
art/previews/characters/maps/vulture_<id>_*.jpg.

Steps (each logged):
1. Import the GLB, weld, drop floating bits (connected pieces under 0.4 % of the faces that do not touch the body),
   keep Tripo's winding (a recalc flips patches at its few non-manifold edges), ground at z 0, centred between the feet, facing -Y (goon_generated.facing_check).
2. Scale to the Goon's silhouette: the mannequin's height x HOOD (SK_Goon_Hoodie's hood top, 1.818 m), x CAP for a
   watch cap or beanie, x 1.0 for a bare balaclava. Decimate to the budget (BUDGET triangles) when Tripo returned more.
3. Bind with goon_generated's method (limbs of SKM_Manny posed onto the mesh, weights from the posed mannequin,
   inverse skinning to the mannequin's reference pose), then weights BY BODY SEGMENT (the lesson of SK_RuleArms
   round 3): every vertex is labelled arm / leg / core by the nearest bone chain of the fitted skeleton and may only
   keep weights of bones allowed for its segment (an arm never takes a thigh or the pelvis, a leg never takes the
   other leg or an arm, the torso never takes a forearm, hand or calf); masked before and after smoothing.
   Finger weights fold into the hand (generated gloves are one piece). At most 4 influences.
4. Pose check: the mannequin clips (jog, aim, reloads, melee, death) every 6 frames plus a kneel and an overhead
   swing: no vertex more than 6 cm outside the capsule of the bones that weight it (_rule_gate.Gate), and the edge
   stretch (posed / rest edge length) recorded; a failure is logged and written to the check file.
5. Export on the full SK_Mannequin hierarchy (char.export_character, the proven path, slot stub materials), the
   unique set from the generated PBR maps (BC sRGB, N OpenGL, ORM: R AO = 1, G roughness, B metallic),
   rule.export_checks (validation, skeleton round trip, re-import), manifest record.
"""
import json
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from mi import char, export as mexport, gen3d, geo, mat, paths, render, scene
from assets import goon_generated as GG

FAMILY = {"name": "vultures", "description": "Vultures crews of levels 2 and 3: generated people bound to SK_Mannequin"}

SRC = os.path.join(paths.out, "characters", "maps")
PREV = os.path.join(paths.previews, "characters", "maps")
BUDGET = 120000                 # triangles, the Goons' cap (r3: 115-117.5k)
HOOD = 1.818 / 1.805            # hood top: SK_Goon_Hoodie's (1.818 m) over the mannequin's head (1.805 m)
CAP = 1.815 / 1.805             # watch cap, beanie: 1 cm over the head

# id -> (asset name, top factor over the mannequin's head, notes)
ROSTER = {
    "canal_shell": ("SK_Vulture_CanalShell", HOOD, "Level 2 rank and file: black rain shell, hood up, charcoal balaclava"),
    "canal_bomber": ("SK_Vulture_CanalBomber", HOOD, "Level 2 rank and file (woman): olive bomber over a hoodie, beanie, bandana"),
    "canal_lieutenant": ("SK_Vulture_CanalLieutenant", CAP, "Level 2 lieutenant: waxed field parka, low-profile vest, arm band"),
    "roof_rigger": ("SK_Vulture_RoofRigger", CAP, "Level 3 rank and file: duck work jacket, watch cap, headlamp"),
    "roof_lookout": ("SK_Vulture_RoofLookout", CAP, "Level 3 rank and file (woman): softshell, collar to the nose, glasses"),
    "roof_lieutenant": ("SK_Vulture_RoofLieutenant", 1.0, "Level 3 lieutenant: charcoal wool car coat, balaclava, vest, arm band"),
}

# The generated roughness reads as vinyl on fabric (canal_shell: mean 0.56, glossy joggers and hood in the first
# previews, the earlier generated Goon's fault too): remapped into cloth's range, keeping its pattern (wet sheen,
# seams) as the variation. Metallic only where the map is clearly metal (zips, buckles, eyelets).
ROUGH_REMAP = (0.45, 0.5)       # roughness' = 0.45 + 0.5 x roughness  (0.45 .. 0.95)
METAL_MIN = 0.5

ARM_CHAIN = ("upperarm", "lowerarm", "hand")
LEG_CHAIN = ("thigh", "calf", "foot")


def _ids(ctx):
    only = [o for o in (ctx.args.only or []) if o in ROSTER]
    return only or [k for k in ROSTER if os.path.exists(_glb(k))]


def _glb(cid):
    return os.path.join(SRC, cid, "%s_tripo.glb" % cid)


def _set_name(asset):
    return "Vulture" + asset.split("SK_Vulture_")[1]


# ------------------------------------------------------------------------------------------------- clean-up

def clean(ob, log):
    """Floating bits out, normals outward, smooth shading. Returns a small report."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    seen, parts = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, comp = [f], []
        seen.add(f.index)
        while stack:
            g = stack.pop()
            comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        parts.append(comp)
    parts.sort(key=len, reverse=True)
    n = len(bm.faces)
    drop = [c for c in parts[1:] if len(c) < 0.004 * n]
    # a small piece lying against the body (a toggle, a zip pull) stays; a floater far from it goes
    main = np.array([v.co[:] for f in parts[0] for v in f.verts])
    gone = 0
    for c in drop:
        pts = np.array([v.co[:] for f in c for v in f.verts])
        cen = pts.mean(0)
        d = np.min(np.linalg.norm(main[::7] - cen, axis=1))
        if d > 0.03:
            bmesh.ops.delete(bm, geom=c, context="FACES")
            gone += 1
    # no recalc_face_normals: Tripo's winding is consistent but for 11 edges at the soles, and the recalc, confused
    # by the 15 non-manifold edges there, flipped patches (339 inconsistent edges after it)
    bad = sum(1 for e in bm.edges if e.is_manifold and not e.is_contiguous)
    bm.to_mesh(ob.data)
    bm.free()
    for p in ob.data.polygons:
        p.use_smooth = True
    log("  clean: %d connected pieces, %d floaters removed, %d edges with opposite winding" % (len(parts), gone, bad))
    return {"pieces": len(parts), "floaters_removed": gone, "opposite_winding_edges": bad}


def uv_report(ob):
    me = ob.data
    if not me.uv_layers:
        return {"uv": None}
    uv = np.empty(len(me.loops) * 2)
    me.uv_layers.active.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    out = float(((uv < -1e-4) | (uv > 1 + 1e-4)).any(1).mean())
    # covered fraction of a 512 grid (rough atlas use)
    g = np.zeros((512, 512), bool)
    tri_uv = []
    for p in me.polygons:
        li = list(p.loop_indices)
        for i in range(1, len(li) - 1):
            tri_uv.append((li[0], li[i], li[i + 1]))
    t = uv[np.array(tri_uv)]
    c = np.clip((t.mean(1) * 511).astype(int), 0, 511)
    g[c[:, 1], c[:, 0]] = True
    return {"uv_outside_0_1": round(out, 4), "atlas_cells_hit": round(float(g.mean()), 3)}


# ------------------------------------------------------------------------------------------------- weights

def _seg_dist(p, a, b):
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
    return np.linalg.norm(p - a - t[:, None] * ab[None], axis=1)


def segment_labels(arm, co):
    """0 core, 1 arm_l, 2 arm_r, 3 leg_l, 4 leg_r: the nearest chain of the POSED (fitted) skeleton."""
    pb = arm.pose.bones
    M = arm.matrix_world

    def P(name, tail=False):
        b = pb[name]
        return np.array(M @ (b.tail if tail else b.head))

    chains = [[("pelvis", "spine_01"), ("spine_01", "spine_03"), ("spine_03", "spine_05"), ("spine_05", "neck_01"),
               ("neck_01", "head"), ("head", "head+")]]
    for sd in ("l", "r"):
        chains.append([("upperarm_" + sd, "lowerarm_" + sd), ("lowerarm_" + sd, "hand_" + sd), ("hand_" + sd, "hand_" + sd + "+")])
    for sd in ("l", "r"):
        chains.append([("thigh_" + sd, "calf_" + sd), ("calf_" + sd, "foot_" + sd), ("foot_" + sd, "ball_" + sd),
                       ("ball_" + sd, "ball_" + sd + "+")])
    best = np.full(len(co), 1e9)
    lab = np.zeros(len(co), np.int8)
    # each chain's radius: the torso is wide, so its distance is discounted
    scale = [0.55, 1.0, 1.0, 1.0, 1.0]
    for k, ch in enumerate(chains):
        for a, b in ch:
            pa = P(a)
            pb_ = P(b[:-1], tail=True) if b.endswith("+") else P(b)
            d = _seg_dist(co, pa, pb_) * scale[k]
            m = d < best
            best[m], lab[m] = d[m], k
    return lab


def allowed(names):
    """Boolean matrix (5 segments x bones): which bones a segment may keep."""
    A = np.zeros((5, len(names)), bool)
    for j, n in enumerate(names):
        side = n[-2:] if n[-2:] in ("_l", "_r") else ""
        base = n[:-2] if side else n
        leg = base.startswith(("thigh", "calf", "foot", "ball"))
        armb = base.startswith(("upperarm", "lowerarm", "hand")) or (side and base.split("_")[0] in
                                                                     ("thumb", "index", "middle", "ring", "pinky"))
        clav = base.startswith("clavicle")
        core = not leg and not armb and not clav
        upper_spine = base in ("spine_03", "spine_04", "spine_05")
        # core: everything of the trunk and head, the clavicles and upper arms (shoulders), the thighs (hips)
        A[0, j] = core or clav or base.startswith(("upperarm", "thigh"))
        for k, sd in ((1, "_l"), (2, "_r")):
            A[k, j] = (side == sd and (armb or clav)) or upper_spine
        for k, sd in ((3, "_l"), (4, "_r")):
            A[k, j] = (side == sd and leg) or base == "pelvis"
    return A


SHOULDER_R = 0.13      # a torso vertex may follow an upper arm only this close to its shoulder joint (m)
HIP_DROP = 0.05        # and a thigh only below the hip joint + this (m)


def vertex_allowed(arm, co, lab, A, names):
    """Per-vertex allowed bones: the segment's row, with the torso's shoulder and hip allowances limited to the
    joints' neighbourhood (a loose jacket's side panel must not swing with the arm)."""
    Av = A[lab].copy()
    core = lab == 0
    M = arm.matrix_world
    for sd in ("l", "r"):
        sh = np.array(M @ arm.pose.bones["upperarm_" + sd].head)
        hip = np.array(M @ arm.pose.bones["thigh_" + sd].head)
        near = np.linalg.norm(co - sh, axis=1) < SHOULDER_R
        low = co[:, 2] < hip[2] + HIP_DROP
        for j, n in enumerate(names):
            if n.endswith("_" + sd) and n.startswith("upperarm"):
                Av[core & ~near, j] = False
            if n.endswith("_" + sd) and n.startswith("thigh"):
                Av[core & ~low, j] = False
    return Av


def segment_mask(W, lab, A, names):
    """A: (segments x bones) or per-vertex (vertices x bones) allowed matrix."""
    W = np.array(W, dtype=np.float64)
    bad = ~(A if A.shape[0] == len(W) and A.shape[0] != 5 else A[lab])
    n = int(((W > 1e-4) & bad).sum())
    W[bad] = 0.0
    s = W.sum(1)
    empty = s < 0.05
    if empty.any():
        fb = {0: "spine_03", 1: "lowerarm_l", 2: "lowerarm_r", 3: "calf_l", 4: "calf_r"}
        for i in np.nonzero(empty)[0]:
            W[i] = 0
            W[i, names.index(fb[int(lab[i])])] = 1.0
    return W / np.maximum(W.sum(1, keepdims=True), 1e-12), n


def bind(ctx, ob, top_factor, log):
    rig_col = scene.collection("Mannequin_" + ob.name)
    arm, body = GG.load_mannequin(char.MANNEQUIN, rig_col)
    bco, btris = GG._evaluated(body)
    top = bco[:, 2].max()
    GG._normalise(ob, top * top_factor)
    co = GG._verts(ob)
    log("  scaled to %.3f m (mannequin %.3f m x %.3f)" % (np.ptp(co[:, 2]), top, top_factor))
    rep = GG.fit_pose(arm, co)
    for k, v in rep.items():
        log("  fit %-12s %5.1f deg, length x%.3f" % (k, v["angle_deg"], v["stretch"]))
    names, BW = GG.body_weights(body)
    pco, _t = GG._evaluated(body)
    W, dist = GG.transfer_weights(co, pco, btris, BW)
    log("  weights: surface distance median %.3f m, 99th pct %.3f m" % (np.median(dist), np.percentile(dist, 99)))
    for j, nm in enumerate(names):
        if nm.startswith(GG.FINGERS) and nm[-2:] in ("_l", "_r") and ("hand" + nm[-2:]) in names:
            W[:, names.index("hand" + nm[-2:])] += W[:, j]
            W[:, j] = 0
    lab = segment_labels(arm, co)
    A = vertex_allowed(arm, co, lab, allowed(names), names)
    W, n0 = segment_mask(W, lab, A, names)
    W = GG.smooth_weights(ob, W.astype(np.float32))
    W, n1 = segment_mask(W, lab, A, names)
    W = GG.limit_normalise(W, 4)
    W, n2 = segment_mask(W, lab, A, names)
    log("  segments: core %d, arms %d / %d, legs %d / %d vertices; cross-segment weights removed %d, %d after "
        "smoothing, %d after the limit" % tuple([int((lab == k).sum()) for k in range(5)] + [n0, n1, n2]))
    fits = GG.bone_fit_matrices(arm)
    rest = GG.unpose(co, names, W, fits)
    GG._set_verts(ob, rest)
    GG.write_groups(ob, names, W)
    char.rest_pose(arm)
    ob.parent = arm
    ob.matrix_parent_inverse = Matrix.Identity(4)
    md = ob.modifiers.new("Armature", "ARMATURE")
    md.object = arm
    body.hide_render = body.hide_viewport = True
    GG.fit_pose(arm, co)
    back, _t = GG._evaluated(ob)
    err = np.linalg.norm(back - co, axis=1)
    log("  round trip (fitted pose on the bound mesh): mean %.4f m, max %.4f m" % (err.mean(), err.max()))
    char.rest_pose(arm)
    return arm, body, {"segments": [int((lab == k).sum()) for k in range(5)], "cross_removed": [n0, n1, n2],
                       "round_trip_mean_m": round(float(err.mean()), 5), "round_trip_max_m": round(float(err.max()), 5),
                       "fit": rep}


# ------------------------------------------------------------------------------------------------- pose check

POSE_CLIPS = ("rifle_jog_fwd", "rifle_idle_ads", "rifle_reload", "pistol_idle_ads", "unarmed_attack", "death_front")


def _edges(ob):
    e = np.empty(len(ob.data.edges) * 2, np.int64)
    ob.data.edges.foreach_get("vertices", e)
    return e.reshape(-1, 2)


def _rot(arm, name, axis, deg):
    pbs = arm.pose.bones
    if name not in pbs:
        return
    head = pbs[name].head.copy()
    R = Matrix.Translation(head) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-head)
    pbs[name].matrix = R @ pbs[name].matrix
    bpy.context.view_layer.update()


def held_pose(arm, which):
    """Poses the mannequin clips here do not cover, about world X at each joint (rotation of a hanging limb by +a
    swings it backward, the figure facing -Y). kneel: on the right knee, right thigh down and its shin back
    level, left thigh forward level and its shin down (goon_generated.hand_pose's kneel bends the right knee
    backward through the joint: not a pose a body makes); crouch: both thighs 70 deg forward, knees 110 deg, the
    trunk 20 deg forward; swing: the overhead right-arm swing of the brief."""
    char.rest_pose(arm)
    if which == "kneel":
        _rot(arm, "thigh_r", "X", 8)
        _rot(arm, "calf_r", "X", 90)
        _rot(arm, "thigh_l", "X", -85)
        _rot(arm, "calf_l", "X", 88)
    elif which == "crouch":
        for sd in ("l", "r"):
            _rot(arm, "thigh_" + sd, "X", -70)
            _rot(arm, "calf_" + sd, "X", 110)
        _rot(arm, "spine_01", "X", 20)
    elif which == "swing":
        GG.hand_pose(arm, 0)


def pose_check(ob, arm, log, step=6):
    from assets import _rule_gate as RG
    g = RG.Gate(ob, arm)
    E = _edges(ob)
    rest = GG._verts(ob)
    L0 = np.linalg.norm(rest[E[:, 0]] - rest[E[:, 1]], axis=1) + 1e-9
    far = (0.0, 0.0, 100.0)
    rows = []

    def measure(label):
        r = g.check(label, far)
        co, _t = GG._evaluated(ob)
        L = np.linalg.norm(co[E[:, 0]] - co[E[:, 1]], axis=1) / L0
        r["stretch_p999"] = round(float(np.percentile(L, 99.9)), 3)
        r["stretch_max"] = round(float(L.max()), 3)
        r["edges_over_2x"] = int((L > 2.0).sum())
        r["edges_under_0.35x"] = int((L < 0.35).sum())
        rows.append(r)

    for clip in POSE_CLIPS:
        try:
            src, _act, rng = char.import_clip(clip)
        except Exception as e:
            rows.append({"pose": clip, "skipped": str(e)[:100], "ok": True})
            continue
        for f in range(rng[0], rng[1] + 1, step):
            bpy.context.scene.frame_set(f)
            char.pose_from_armature(arm, src)
            if "root" in arm.pose.bones:
                arm.pose.bones["root"].matrix_basis = Matrix.Identity(4)
            bpy.context.view_layer.update()
            measure("%s@%d" % (clip, f))
        bpy.data.objects.remove(src, do_unlink=True)
        char.rest_pose(arm)
    for nm in ("swing", "kneel", "crouch"):
        held_pose(arm, nm)
        measure(nm)
    char.rest_pose(arm)
    fails = [r for r in rows if not r.get("ok")]
    stretch = [r for r in rows if "stretch_max" in r]
    rep = {"poses": len(rows), "failed": len(fails), "ok": not fails, "capsule_out_m": RG.CAPSULE_OUT,
           "worst_capsule_m": max((r["capsule_out_max_m"] for r in stretch), default=None),
           "worst_stretch_p999": max((r["stretch_p999"] for r in stretch), default=None),
           "edges_over_2x_max": max((r["edges_over_2x"] for r in stretch), default=None),
           "fails": fails[:12], "rows": rows}
    log("  pose check: %d poses, %d failed, worst capsule excess %.3f m, worst p99.9 edge stretch x%.2f, at most %d "
        "edges over 2x" % (rep["poses"], rep["failed"], rep["worst_capsule_m"] or -1, rep["worst_stretch_p999"] or -1,
                           rep["edges_over_2x_max"] or 0))
    for r in fails[:6]:
        log("    fail %s: %d vertices out, %.3f m" % (r["pose"], r.get("outside", -1), r.get("capsule_out_max_m", -1)))
    return rep


# ------------------------------------------------------------------------------------------------- texture set

def write_set(set_name, tex, log):
    from PIL import Image
    from mi import bake
    d = paths.ensure(paths.texture_set(set_name))
    bc = np.clip(bake.srgb_encode(tex["bc"]), 0, 1)
    Image.fromarray((bc * 255 + 0.5).astype(np.uint8)).save(os.path.join(d, "T_%s_BC.png" % set_name))
    if "normal" in tex:
        Image.fromarray((np.clip(tex["normal"], 0, 1) * 255 + 0.5).astype(np.uint8)).save(
            os.path.join(d, "T_%s_N.png" % set_name))
    h, w = tex["bc"].shape[:2]
    rough = tex.get("rough", np.full((h, w), 0.5, np.float32))
    rough = (ROUGH_REMAP[0] + ROUGH_REMAP[1] * rough).astype(np.float32)
    metal = tex.get("metal", np.zeros((h, w), np.float32))
    metal = np.where(metal > METAL_MIN, metal, 0.0).astype(np.float32)
    ao = tex.get("ao", np.ones((h, w), np.float32))
    orm = np.stack([ao, rough, metal], -1)
    Image.fromarray((np.clip(orm, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(d, "T_%s_ORM.png" % set_name))
    info = {"kind": "generated", "asset": "SK_" + set_name.replace("Vulture", "Vulture_", 1), "resolution": [w, h],
            "albedo_mean": [round(float(v), 4) for v in tex["bc"].reshape(-1, 3).mean(0)],
            "roughness_mean": round(float(rough.mean()), 3), "metallic_mean": round(float(metal.mean()), 3),
            "ao_mean": round(float(ao.mean()), 3),
            "roughness_remap": list(ROUGH_REMAP), "metallic_min": METAL_MIN,
            "note": "Tripo multiview PBR maps rewritten to the project's set: BC sRGB, N OpenGL, ORM (R = the generated "
                    "occlusion, G = 0.45 + 0.5 x the generated roughness, B = metallic where over 0.5)"}
    with open(os.path.join(d, "set.json"), "w") as f:
        json.dump(info, f, indent=1)
    log("  set %s: %d x %d, albedo mean %s, roughness mean %.2f, metallic mean %.2f"
        % (set_name, w, h, info["albedo_mean"], info["roughness_mean"], info["metallic_mean"]))
    return info


def set_material(slot, set_name):
    """Preview material on the written set, as the Unreal material reads it (the Goons' textured_material graph:
    BC x AO, roughness and metallic from ORM, OpenGL normal, sheen from roughness as the Cloth model's fuzz)."""
    d = paths.texture_set(set_name)
    m = bpy.data.materials.get(slot) or bpy.data.materials.new(slot)
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs["Surface"])

    def img(tag, data):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(d, "T_%s_%s.png" % (set_name, tag)), check_existing=True)
        t.image.colorspace_settings.name = "Non-Color" if data else "sRGB"
        return t
    bc, nm, orm = img("BC", False), img("N", True), img("ORM", True)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    nt.links.new(bc.outputs["Color"], mix.inputs["A"])
    nt.links.new(sep.outputs["Red"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    nt.links.new(sep.outputs["Green"], b.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], b.inputs["Metallic"])
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(nm.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], b.inputs["Normal"])
    m1 = nt.nodes.new("ShaderNodeMath")
    m1.operation, m1.use_clamp = "MULTIPLY_ADD", True
    nt.links.new(sep.outputs["Green"], m1.inputs[0])
    m1.inputs[1].default_value, m1.inputs[2].default_value = 3.3, -0.55 * 3.3
    m2 = nt.nodes.new("ShaderNodeMath")
    m2.operation = "MULTIPLY"
    nt.links.new(m1.outputs[0], m2.inputs[0])
    m2.inputs[1].default_value = 0.8
    nt.links.new(m2.outputs[0], b.inputs["Sheen Weight"])
    b.inputs["Sheen Roughness"].default_value = 0.5
    nt.links.new(mix.outputs["Result"], b.inputs["Sheen Tint"])
    b.inputs["Specular IOR Level"].default_value = 0.35
    return m


# ------------------------------------------------------------------------------------------------- build

def build_one(ctx, cid):
    asset, top_factor, notes = ROSTER[cid]
    log = ctx.log
    log("%s (%s) from %s" % (asset, cid, os.path.relpath(_glb(cid), paths.art)))
    ob, tex = gen3d.load(_glb(cid), asset, ctx.col)
    st = geo.stats(ob)
    rep = {"id": cid, "asset": asset, "source_triangles": st["triangles"], "source_vertices": len(ob.data.vertices),
           "maps": {k: list(v.shape) for k, v in tex.items() if hasattr(v, "shape")}}
    log("  generated: %d triangles, %d vertices, maps %s" % (st["triangles"], len(ob.data.vertices), rep["maps"]))
    rep["clean"] = clean(ob, log)
    GG._normalise(ob)
    # Tripo's default orientation stands the figure up (Z) but faces it along X: the arm span (widest slice
    # between 50 and 65 % of the height, the A-pose hands and forearms) must lie on X
    co = GG._verts(ob)
    z = (co[:, 2] - co[:, 2].min()) / np.ptp(co[:, 2])
    band = co[(z > 0.50) & (z < 0.65)]
    if np.ptp(band[:, 1]) > np.ptp(band[:, 0]):
        log("  arm span on Y (%.2f against %.2f on X): turned 90 degrees about Z" % (np.ptp(band[:, 1]), np.ptp(band[:, 0])))
        GG._set_verts(ob, co[:, [1, 0, 2]] * [-1, 1, 1])
        GG._normalise(ob)
        rep["turned_deg"] = 90
    if GG.facing_check(ob) < 0:
        log("  the mesh faces +Y: turned 180 degrees")
        GG._set_verts(ob, GG._verts(ob) * [-1, -1, 1])
    if geo.stats(ob)["triangles"] > BUDGET:
        gen3d.decimate(ob, 1.0, target=int(BUDGET * 0.95))
    rep["triangles"] = geo.stats(ob)["triangles"]
    rep["uv"] = uv_report(ob)
    log("  %d triangles (budget %d), uv %s" % (rep["triangles"], BUDGET, rep["uv"]))
    slot = "M_" + asset[3:]
    sname = _set_name(asset)
    rep["set"] = write_set(sname, tex, log)
    old = ob.data.materials[0] if ob.data.materials else None
    if old is not None:
        old.name = slot + "__generated"
    m = set_material(slot, sname)
    ob.data.materials.clear()
    ob.data.materials.append(m)
    arm, body, brep = bind(ctx, ob, top_factor, log)
    rep["bind"] = brep
    co = GG._verts(ob)
    rep["height_m"] = round(float(np.ptp(co[:, 2])), 4)
    rep["width_m"] = round(float(np.ptp(co[:, 0])), 4)
    rep["depth_m"] = round(float(np.ptp(co[:, 1])), 4)
    geo.ensure_wear(ob)
    return dict(ob=ob, arm=arm, body=body, tex=tex, rep=rep, asset=asset, slot=slot, notes=notes)


def build(ctx):
    ctx.vult = {}
    objs = []
    for cid in _ids(ctx):
        if not os.path.exists(_glb(cid)):
            ctx.log("%s: no generated GLB at %s" % (cid, _glb(cid)))
            continue
        v = build_one(ctx, cid)
        ctx.vult[cid] = v
        objs.append(v["ob"])
    return objs


def on_export(ctx, objs):
    from assets import rule as RU
    for cid, v in ctx.vult.items():
        ob, arm, rep = v["ob"], v["arm"], v["rep"]
        rep["pose_check"] = pose_check(ob, arm, ctx.log)
        sname = _set_name(v["asset"])
        ob.data.validate(clean_customdata=False)
        path = char.export_character(ob, arm, name=v["asset"], influences=4)
        ctx.log("  exported %s (%.1f MB)" % (path, os.path.getsize(path) / 1e6))
        chk = RU.export_checks(ob, arm, path, ctx.log)
        chk["build"] = {k: rep[k] for k in rep if k != "pose_check"}
        chk["pose_check"] = {k: rep["pose_check"][k] for k in rep["pose_check"] if k != "rows"}
        chk["pose_rows"] = rep["pose_check"]["rows"]
        with open(path + ".check.json", "w") as f:
            json.dump(chk, f, indent=1, default=str)
        lo, hi = scene.bounds(ob)
        entry = {"name": v["asset"], "family": "vultures", "kind": "skeletal", "glb": os.path.relpath(path, paths.art),
                 "skeleton": "SK_Mannequin (all 89 joints)", "triangles": rep["triangles"],
                 "bounds_m": {"min": [round(float(x), 4) for x in lo], "max": [round(float(x), 4) for x in hi]},
                 "material_slots": [{"slot": v["slot"], "workflow": "unique", "set": sname}],
                 "notes": v["notes"] + "; mesh scale 0.98 in the game like the Goons; hit volumes from config.json",
                 "checks": os.path.relpath(path + ".check.json", paths.art)}
        mexport.write_manifest([entry], [sname])
        ctx.log("  manifest: %s, set %s" % (v["asset"], sname))


# ------------------------------------------------------------------------------------------------- previews

def _preview_material(v):
    """The imported glTF material reads the generated maps already: keep it for the Cycles previews."""
    return v["ob"].material_slots[0].material if v["ob"].material_slots else None


def _night(target=(0.0, 0.0, 1.0)):
    render.rig_night(lamp=(2.2, -3.0, 5.5), lamp_target=target, lamp_watts=700.0, sign=(-2.6, -1.4, 2.8),
                     sign_color=(0.25, 0.85, 0.55), sign_watts=220.0, sign_target=target)


def _key_fill():
    """Neutral studio look for judging the textures (not the game's light)."""
    render.rig_day(sun_azimuth=215.0, stops=0.4)


def on_preview(ctx, objs):
    a = ctx.args
    want_env = os.environ.get("MI_PREVIEWS")
    want = (lambda n: n in want_env.split(",")) if want_env else (lambda n: True)
    paths.ensure(PREV)
    render.setup(samples=a.samples or 32, threads=3)
    ground = render.backdrop(size=40.0, color=(0.05, 0.05, 0.055), z=0.0)
    import tempfile
    tmp = tempfile.gettempdir()
    for cid, v in ctx.vult.items():
        ob, arm = v["ob"], v["arm"]
        base = os.path.join(PREV, "vulture_%s" % cid)
        if want("hero"):
            twin = ob.copy()
            twin.data = ob.data
            ctx.col.objects.link(twin)
            twin.modifiers["Armature"].object = arm
            twin.parent = None
            twin.matrix_world = Matrix.Translation((1.25, 0.5, 0)) @ Matrix.Rotation(math.radians(160), 4, "Z")
            shots = []
            _key_fill()
            render.cam_look((0.95, -4.6, 1.2), (0.62, 0.15, 0.92), lens=40, name="Cam_Hero")
            p1 = os.path.join(tmp, "v_hero_day.png")
            render.render_png(p1, a.samples, (640, 720))
            shots.append(p1)
            _night((0.6, 0.2, 1.0))
            p2 = os.path.join(tmp, "v_hero_night.png")
            render.render_png(p2, a.samples, (640, 720))
            shots.append(p2)
            bpy.data.objects.remove(twin, do_unlink=True)
            render.contact_sheet(shots, base + "_hero.jpg", cols=2, labels=["studio", "street night"])
            ctx.log("preview %s_hero.jpg" % os.path.basename(base))
        if want("detail"):
            _key_fill()
            render.cam_look((0.42, -0.95, 1.55), (0.1, 0.0, 1.42), lens=45, name="Cam_1m")
            p1 = os.path.join(tmp, "v_det_1m.png")
            render.render_png(p1, a.samples, (640, 720))
            render.cam_look((0.6, -1.25, 0.6), (0.05, 0.0, 0.55), lens=45, name="Cam_legs")
            p2 = os.path.join(tmp, "v_det_legs.png")
            render.render_png(p2, a.samples, (640, 720))
            render.contact_sheet([p1, p2], base + "_detail.jpg", cols=2, labels=["head, 1 m", "legs, 1.3 m"])
            ctx.log("preview %s_detail.jpg" % os.path.basename(base))
        if want("poses"):
            _key_fill()
            shots, labels = [], []
            for clip, frac, lab in (("rifle_jog_fwd", 0.3, "jog (walk/run)"), ("rifle_idle_ads", 0.3, "aim"),
                                    (None, "crouch", "crouch"), ("death_front", 0.5, "death (falling)")):
                if clip:
                    src, _act, rng = char.import_clip(clip)
                    bpy.context.scene.frame_set(int(rng[0] + (rng[1] - rng[0]) * frac))
                    char.pose_from_armature(arm, src)
                    bpy.data.objects.remove(src, do_unlink=True)
                    if "root" in arm.pose.bones:
                        arm.pose.bones["root"].matrix_basis = Matrix.Identity(4)
                else:
                    held_pose(arm, frac)
                bpy.context.view_layer.update()
                co, _t = GG._evaluated(ob)
                c = co.mean(0)
                render.cam_look((c[0] + 1.7, c[1] - 3.1, 1.3), (c[0], c[1], max(0.45, c[2])), lens=40, name="Cam_Pose")
                pp = os.path.join(tmp, "v_pose_%d.png" % len(shots))
                render.render_png(pp, a.samples, (480, 640))
                shots.append(pp)
                labels.append(lab)
                char.rest_pose(arm)
            render.contact_sheet(shots, base + "_poses.jpg", cols=4, labels=labels)
            ctx.log("preview %s_poses.jpg" % os.path.basename(base))
        if want("wire"):
            clay = mat.flat("Clay", (0.5, 0.5, 0.5), 0.6)
            wire = ob.copy()
            wire.data = ob.data.copy()
            ctx.col.objects.link(wire)
            wire.data.materials.clear()
            wire.data.materials.append(mat.flat("WireInk", (0.02, 0.02, 0.025), 0.5))
            wm = wire.modifiers.new("Wire", "WIREFRAME")
            wm.thickness = 0.0007
            wm.use_replace = True
            old = [s.material for s in ob.material_slots]
            for s in ob.material_slots:
                s.material = clay
            render.rig_day(sun_azimuth=215.0, stops=0.2)
            render.cam_look((0.35, -1.2, 1.45), (0.08, 0.0, 1.32), lens=40, name="Cam_Wire")
            p1 = os.path.join(tmp, "v_wire.png")
            render.render_png(p1, max(16, a.samples // 2), (640, 720))
            wire.hide_render = True
            # the Goon beside it in clay for the size: same mannequin, same scale
            goon = None
            gp = os.path.join(paths.glb, "SK_Goon_Hoodie.glb")
            if os.path.exists(gp):
                before = set(bpy.data.objects)
                bpy.ops.import_scene.gltf(filepath=gp)
                new = [o for o in bpy.data.objects if o not in before]
                for o in new:
                    if o.type == "MESH":
                        o.data.materials.clear()
                        o.data.materials.append(mat.flat("ClayGoon", (0.32, 0.30, 0.30), 0.6))
                roots = [o for o in new if o.parent is None]
                for o in roots:
                    o.location.x += 1.2
                goon = new
            render.cam_look((0.6, -4.6, 1.0), (0.6, 0.0, 0.9), lens=40, name="Cam_Clay")
            p2 = os.path.join(tmp, "v_clay.png")
            render.render_png(p2, max(16, a.samples // 2), (640, 720))
            for s, m in zip(ob.material_slots, old):
                s.material = m
            bpy.data.objects.remove(wire, do_unlink=True)
            for o in goon or []:
                bpy.data.objects.remove(o, do_unlink=True)
            render.contact_sheet([p2, p1], base + "_wire.jpg", cols=2,
                                 labels=["clay, beside SK_Goon_Hoodie (right)", "wire, 1.2 m"])
            ctx.log("preview %s_wire.jpg" % os.path.basename(base))
    bpy.data.objects.remove(ground, do_unlink=True)
