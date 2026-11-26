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
    "canal_lieutenant": ("SK_Vulture_CanalLieutenant", HOOD, "Level 2 lieutenant: waxed field parka with the hood up, low-profile vest, arm band"),
    "roof_rigger": ("SK_Vulture_RoofRigger", CAP, "Level 3 rank and file: duck work jacket, watch cap, headlamp"),
    "roof_lookout": ("SK_Vulture_RoofLookout", CAP, "Level 3 rank and file (woman): softshell, collar to the nose, glasses"),
    "roof_lieutenant": ("SK_Vulture_RoofLieutenant", 1.0, "Level 3 lieutenant: charcoal wool car coat, balaclava, vest, arm band"),
}

# The generated roughness reads as vinyl on fabric (canal_shell: mean 0.56, glossy joggers and hood in the first
# previews, the earlier generated Goon's fault too): remapped into cloth's range, keeping its pattern (wet sheen,
# seams) as the variation. Metallic only where the map is clearly metal (zips, buckles, eyelets).
ROUGH_REMAP = (0.45, 0.5)       # the first remap (0.45 .. 0.95): still leather or vinyl at 1 m (review F7)
ROUGH_TOP = 0.95
METAL_MIN = 0.5
# Per character (review F7, F1, F8): the roughness floor of the cloth (roughness' = floor + (0.95 - floor) x the
# generated value: denim, wool and canvas 0.6 or more, the nylon shell lowest; wetness is the Unreal material's
# per-level parameter, not the texture), and the eye band: skin and eye whites inside the mask's opening are darkened
# to a dark neutral (eyes in deep shadow, as the Goons' recessed eyes), keeping saturated colour (amber lenses,
# the oxblood cuff) unless 'keep_sat' is None.
STYLE = {
    "canal_shell": {"rough_floor": 0.56, "keep_sat": 0.65},          # nylon rain shell, cotton twill joggers
    "canal_bomber": {"rough_floor": 0.62, "keep_sat": 0.65},         # nylon bomber, fleece, denim
    "canal_lieutenant": {"rough_floor": 0.60, "keep_sat": 0.65},     # waxed cotton (matte wax), fleece, twill
    "roof_rigger": {"rough_floor": 0.68, "keep_sat": 0.65},          # duck canvas, corduroy
    "roof_lookout": {"rough_floor": 0.62, "keep_sat": 0.55},         # softshell; amber lenses kept
    "roof_lieutenant": {"rough_floor": 0.70, "keep_sat": 0.65},      # wool melton, knit
}
# baked highlights: over 1.7 x the level within about 1 cm, over 2.2 x within about 5 cm, or over 0.15 linear
DELIGHT = {"ratio": 1.7, "ratio2": 2.2, "cap": 0.15, "sat": 0.6}
ROUGH_DETAIL = 0.5              # share of the generated roughness' own fine pattern kept (wet droplets, glints)
EYE_L = 0.010                   # linear luminance of the darkened eye band

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
        # the hand chain runs to the middle finger's tip (the hand bone's own tail stops at the knuckles, so a
        # glove's fingers hanging beside the thigh could be nearer the leg chain)
        chains.append([("upperarm_" + sd, "lowerarm_" + sd), ("lowerarm_" + sd, "hand_" + sd),
                       ("hand_" + sd, "middle_03_" + sd + "+")])
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


def connected_labels(ob, arm, co, lab, seed_r=0.12):
    """A limb label must reach its hand (arms) or ankle (legs) over mesh edges between vertices of the same label;
    unreached islands go to the torso. canal_bomber: the hip pouch lies against the hanging forearm and part of it
    was labelled arm, so binding to the mannequin's higher A-pose tore it into flat sheets beside the hip."""
    E = _edges(ob)
    M = arm.matrix_world
    out = lab.copy()
    moved = []
    for k, joint in ((1, "hand_l"), (2, "hand_r"), (3, "foot_l"), (4, "foot_r")):
        mine = lab == k
        if not mine.any():
            moved.append(0)
            continue
        j = np.array(M @ arm.pose.bones[joint].head)
        seen = mine & (np.linalg.norm(co - j, axis=1) < seed_r)
        if not seen.any():
            d = np.where(mine, np.linalg.norm(co - j, axis=1), np.inf)
            seen[int(np.argmin(d))] = True
        e = E[mine[E[:, 0]] & mine[E[:, 1]]]
        while True:                          # grow the reached set along same-label edges until it stops
            grow = (seen[e[:, 0]] & ~seen[e[:, 1]])
            back = (seen[e[:, 1]] & ~seen[e[:, 0]])
            if not grow.any() and not back.any():
                break
            seen[e[grow, 1]] = True
            seen[e[back, 0]] = True
        cut = mine & ~seen
        out[cut] = 0
        moved.append(int(cut.sum()))
    return out, moved


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
ARM_SPINE_R = 0.18     # an arm vertex may keep upper-spine weight only this close to its shoulder joint (m)


def vertex_allowed(arm, co, lab, A, names):
    """Per-vertex allowed bones: the segment's row, with the torso's shoulder and hip allowances limited to the
    joints' neighbourhood (a loose jacket's side panel must not swing with the arm), and the arms' upper-spine
    allowance limited to the shoulder (canal_bomber: forearm vertices by the hip pouch kept 0.4 of spine_03 and
    were left behind by the forearm, 5 to 8 vertices up to 12.5 cm out in the reload, melee, death and swing)."""
    Av = A[lab].copy()
    core = lab == 0
    M = arm.matrix_world
    for k, sd in ((1, "l"), (2, "r")):
        sh = np.array(M @ arm.pose.bones["upperarm_" + sd].head)
        hip = np.array(M @ arm.pose.bones["thigh_" + sd].head)
        dsh = np.linalg.norm(co - sh, axis=1)
        near = dsh < SHOULDER_R
        low = co[:, 2] < hip[2] + HIP_DROP
        arm_far = (lab == k) & (dsh > ARM_SPINE_R)
        for j, n in enumerate(names):
            if n.endswith("_" + sd) and n.startswith("upperarm"):
                Av[core & ~near, j] = False
            if n.endswith("_" + sd) and n.startswith("thigh"):
                Av[core & ~low, j] = False
            if n in ("spine_03", "spine_04", "spine_05"):
                Av[arm_far, j] = False
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


def arm_guess(arm, co, rep, log):
    """goon_generated.mesh_joint looks for the wrist's cross-section near the skeleton's own arm line. When the
    generated arm hangs too far below it, the slice holds fewer than 20 points, the search stops at its start and
    the arm is left unfitted (exactly 0 degrees, length x 1.000; roof_lieutenant's right arm, 20 degrees lower).
    Then the search starts on the line from the shoulder to the mesh's fingertip: the point of that side farthest
    from the shoulder among those 15 cm outside it and below it. Arms the default search fits are left as they are."""
    out = {}
    for up, _lo, end, side in GG.LIMBS[:2]:
        r = rep.get(up)
        if not r or r["angle_deg"] != 0 or r["stretch"] != 1.0:
            continue
        S, W = GG.joint(arm, up), GG.joint(arm, end)
        sel = co[((co[:, 0] * side) > abs(S[0]) + 0.15) & (co[:, 2] < S[2])]
        if len(sel) < 20:
            continue
        P = sel[np.argmax(np.linalg.norm(sel - S, axis=1))]
        out[up] = S + (P - S) / np.linalg.norm(P - S) * np.linalg.norm(W - S)
        log("  %s: no wrist cross-section near the skeleton's arm line; search restarted towards the fingertip at "
            "(%.3f, %.3f, %.3f)" % (up, P[0], P[1], P[2]))
    return out


FINGER_TIPS = ("index_03", "middle_03", "ring_03", "pinky_03")


def fit_hands(arm, co, log=None):
    """Turn and scale each mannequin hand onto the glove (review F3: the fingers used to fold into hand_l / hand_r,
    a rigid paddle round the SMG grip). goon_generated.fit_pose only moves the hand to the mesh's wrist; here the
    hand bone is turned about the wrist so that the mannequin's wrist-to-fingertips line lies on the glove's
    (the glove's fingertips: its points farthest along that line), rolled so that the knuckle line (index to
    pinky) lies on the glove's widest direction across that line, and scaled to the glove's length (x 0.85 to
    1.25). The weights are then transferred from the mannequin's posed hand, finger bones included.
    Returns {hand bone: armature-space matrix} to apply again after a reset (apply_hands)."""
    pbs = arm.pose.bones
    out = {}
    for side, sd in ((1.0, "l"), (-1.0, "r")):
        hand = "hand_" + sd
        if hand not in pbs or ("middle_03_" + sd) not in pbs:
            continue
        W = np.array(pbs[hand].head)
        d = W - np.array(pbs["lowerarm_" + sd].head)
        d /= np.linalg.norm(d)
        rel = co - W
        t = rel @ d
        sel = (t > -0.005) & (np.linalg.norm(rel, axis=1) < 0.26) & (co[:, 0] * side > 0.05)
        if sel.sum() < 200:
            if log:
                log("  hand %s: only %d glove points past the wrist, left as fitted" % (sd, int(sel.sum())))
            continue
        P = co[sel]
        # the glove's axis: wrist to the centroid of its farthest 4 % along the forearm line, twice
        a_m = d.copy()
        for _ in range(2):
            tt = (P - W) @ a_m
            tip = P[tt > np.percentile(tt, 96)].mean(0)
            a_m = (tip - W) / np.linalg.norm(tip - W)
        L_m = float(np.percentile((P - W) @ a_m, 99.5))
        tips = np.array([np.array(pbs[f + "_" + sd].tail) for f in FINGER_TIPS])
        a_k = tips.mean(0) - W
        a_k /= np.linalg.norm(a_k)
        L_k = float(((tips - W) @ a_k).max())
        R1 = Vector(a_k).rotation_difference(Vector(a_m)).to_matrix()
        # roll: the knuckle line (index_01 to pinky_01) onto the glove's widest direction across its axis
        kn = np.array(R1 @ Vector(np.array(pbs["index_01_" + sd].head) - np.array(pbs["pinky_01_" + sd].head)))
        kn -= (kn @ a_m) * a_m
        tt = (P - W) @ a_m
        Q = P[(tt > 0.25 * L_m) & (tt < 0.65 * L_m)]           # the palm and knuckles, not the thumb's tip
        roll = 0.0
        if len(Q) > 60:
            X = Q - Q.mean(0)
            X -= np.outer(X @ a_m, a_m)
            ev, evec = np.linalg.eigh(X.T @ X)
            e1 = evec[:, 2]
            if ev[2] > 1.6 * ev[1] and np.linalg.norm(kn) > 1e-6:
                if e1 @ kn < 0:
                    e1 = -e1
                knn = kn / np.linalg.norm(kn)
                roll = math.atan2(float(np.cross(knn, e1) @ a_m), float(knn @ e1))
        R = (Matrix.Rotation(roll, 3, Vector(a_m)) @ R1).to_4x4()
        k = float(np.clip(L_m / max(L_k, 1e-6), 0.85, 1.25))
        Tw = Matrix.Translation(Vector(W))
        F = Tw @ R @ Matrix.Diagonal((k, k, k, 1.0)) @ Tw.inverted()
        pbs[hand].matrix = F @ pbs[hand].matrix
        bpy.context.view_layer.update()
        out[hand] = pbs[hand].matrix.copy()
        if log:
            log("  hand %s fitted to the glove: turned %.1f deg, rolled %.1f deg, scale x%.2f (glove %.3f m, mannequin "
                "%.3f m, %d points)" % (sd, math.degrees(Vector(a_k).angle(Vector(a_m))), math.degrees(roll), k, L_m,
                                        L_k, len(P)))
    return out


def apply_hands(arm, hands):
    for name, M in (hands or {}).items():
        arm.pose.bones[name].matrix = M
        bpy.context.view_layer.update()


FIN_STRETCH = 1.6      # an edge the reference pose stretches past this (against the generated surface) seeds the band
FIN_R = (0.06, 0.10)   # geodesic radius of the blend band round the seeds, per pass (m)
FIN_FAR = 0.30         # beyond this from the shoulder joint a weak arm share in the band fades out (m)


def fin_band(ob, arm, co, W, names, fits, log):
    """Review F2: the reference A-pose holds the arms about 21 degrees higher than the generated figure, and the
    surface fused between the inner sleeve and the side of the coat was torn into flat sheets ('fins') between an
    arm-weighted and a torso-weighted strip (up to 292 edges over 4x). Here the weights in a band round the stretched
    edges (geodesic radius FIN_R, above the hips) are replaced by the harmonic blend of the weights round the band,
    so the opening spreads over the band instead of one row of edges; then the 4-influence limit. Two passes.
    Lower down (forearm against the hip) the strip is left as before: it closes in every clip."""
    E = _edges(ob)
    L = np.linalg.norm(co[E[:, 0]] - co[E[:, 1]], axis=1) + 1e-9
    hipz = max(float(arm.pose.bones["thigh_" + sd].head[2]) for sd in ("l", "r")) + 0.05
    arm_cols = np.array([n.startswith(("upperarm", "lowerarm", "hand")) or (n.startswith(GG.FINGERS)) for n in names])
    sh = {sd: np.array(arm.pose.bones["upperarm_" + sd].head) for sd in ("l", "r")}
    dsh = np.minimum(np.linalg.norm(co - sh["l"], axis=1), np.linalg.norm(co - sh["r"], axis=1))
    rep = []
    for R in FIN_R:
        rest = GG.unpose(co, names, W, fits)
        rs = np.linalg.norm(rest[E[:, 0]] - rest[E[:, 1]], axis=1) / L
        seeds = np.zeros(len(co), bool)
        seeds[E[rs > FIN_STRETCH].ravel()] = True
        seeds &= co[:, 2] > hipz
        if not seeds.any():
            break
        dist = np.where(seeds, 0.0, np.inf)
        for _ in range(80):
            d_old = dist.copy()
            np.minimum.at(dist, E[:, 1], dist[E[:, 0]] + L)
            np.minimum.at(dist, E[:, 0], dist[E[:, 1]] + L)
            if np.array_equal(d_old, dist):
                break
        band = (dist < R) & (co[:, 2] > hipz)
        # local system: the band and its one-ring
        ring = np.zeros(len(co), bool)
        ring[E[band[E[:, 0]] | band[E[:, 1]]].ravel()] = True
        idx = np.nonzero(ring)[0]
        loc = -np.ones(len(co), np.int64)
        loc[idx] = np.arange(len(idx))
        e = E[ring[E[:, 0]] & ring[E[:, 1]]]
        e0, e1 = loc[e[:, 0]], loc[e[:, 1]]
        cols = np.nonzero(W[idx].max(0) > 1e-4)[0]
        Wl = W[np.ix_(idx, cols)].astype(np.float64)
        free = band[idx]
        deg = np.bincount(e0, minlength=len(idx)) + np.bincount(e1, minlength=len(idx))
        deg = np.maximum(deg, 1).astype(np.float64)
        for _ in range(600):
            acc = np.empty_like(Wl)
            for c in range(Wl.shape[1]):
                acc[:, c] = (np.bincount(e0, weights=Wl[e1, c], minlength=len(idx))
                             + np.bincount(e1, weights=Wl[e0, c], minlength=len(idx)))
            Wl[free] = (acc / deg[:, None])[free]
        Wn = W.copy()
        Wn[np.ix_(idx, cols)] = Wl
        # far from the shoulder (the coat's side by the hip), a small share of the arm only drags the hem after a
        # raised arm (canal_lieutenant: pelvis 0.66 + upper arm 0.25 at hip height, 9 vertices 7.9 cm out with the
        # arms up): there the arm's share fades out between 0.5 and 0.2
        far = band & (dsh > FIN_FAR)
        a = Wn[:, arm_cols].sum(1)
        keep = np.clip((a - 0.2) / 0.3, 0, 1)
        sel = far & (a < 0.5)
        Wn[np.ix_(sel, arm_cols)] *= keep[sel, None]
        W = GG.limit_normalise(Wn.astype(np.float32), 4)
        rest2 = GG.unpose(co, names, W, fits)
        rs2 = np.linalg.norm(rest2[E[:, 0]] - rest2[E[:, 1]], axis=1) / L
        rep.append({"radius_m": R, "seed_vertices": int(seeds.sum()), "band_vertices": int(band.sum()),
                    "edges_over_4x_before": int((rs > 4).sum()), "edges_over_4x_after": int((rs2 > 4).sum()),
                    "p999_after": round(float(np.percentile(rs2, 99.9)), 2)})
        log("  fin band (radius %.2f m): %d seeds, %d vertices blended; edges over 4x %d -> %d, p99.9 x%.2f"
            % (R, rep[-1]["seed_vertices"], rep[-1]["band_vertices"], rep[-1]["edges_over_4x_before"],
               rep[-1]["edges_over_4x_after"], rep[-1]["p999_after"]))
    return W, rep


def bind(ctx, ob, top_factor, log):
    rig_col = scene.collection("Mannequin_" + ob.name)
    arm, body = GG.load_mannequin(char.MANNEQUIN, rig_col)
    bco, btris = GG._evaluated(body)
    top = bco[:, 2].max()
    GG._normalise(ob, top * top_factor)
    co = GG._verts(ob)
    log("  scaled to %.3f m (mannequin %.3f m x %.3f)" % (np.ptp(co[:, 2]), top, top_factor))
    rep = GG.fit_pose(arm, co)
    guess = arm_guess(arm, co, rep, log)
    if guess:
        rep = GG.fit_pose(arm, co, guess)
    for k, v in rep.items():
        log("  fit %-12s %5.1f deg, length x%.3f" % (k, v["angle_deg"], v["stretch"]))
    hands = fit_hands(arm, co, log)
    names, BW = GG.body_weights(body)
    pco, _t = GG._evaluated(body)
    W, dist = GG.transfer_weights(co, pco, btris, BW)
    log("  weights: surface distance median %.3f m, 99th pct %.3f m" % (np.median(dist), np.percentile(dist, 99)))
    # the finger weights are kept (they used to fold into the hand): the mannequin's hand is fitted to the glove
    lab = segment_labels(arm, co)
    lab, moved = connected_labels(ob, arm, co, lab)
    log("  limb islands not connected to their hand or foot, moved to the torso: arms %d / %d, legs %d / %d vertices"
        % tuple(moved))
    A = vertex_allowed(arm, co, lab, allowed(names), names)
    W, n0 = segment_mask(W, lab, A, names)
    W = GG.smooth_weights(ob, W.astype(np.float32))
    W, n1 = segment_mask(W, lab, A, names)
    W = GG.limit_normalise(W, 4)
    W, n2 = segment_mask(W, lab, A, names)
    log("  segments: core %d, arms %d / %d, legs %d / %d vertices; cross-segment weights removed %d, %d after "
        "smoothing, %d after the limit" % tuple([int((lab == k).sum()) for k in range(5)] + [n0, n1, n2]))
    fits = GG.bone_fit_matrices(arm)
    W, fins = fin_band(ob, arm, co, W, names, fits, log)
    rest = GG.unpose(co, names, W, fits)
    # the reference pose is the mannequin's A-pose, the arms higher than the generated ones: what that does to the
    # generated surface (the posed check measures against this rest, so it cannot see it)
    E = _edges(ob)
    rs = np.linalg.norm(rest[E[:, 0]] - rest[E[:, 1]], axis=1) / (np.linalg.norm(co[E[:, 0]] - co[E[:, 1]], axis=1) + 1e-9)
    rest_stretch = {"p999": round(float(np.percentile(rs, 99.9)), 2), "max": round(float(rs.max()), 1),
                    "edges_over_2x": int((rs > 2).sum()), "edges_over_4x": int((rs > 4).sum())}
    log("  reference pose against the generated surface: p99.9 x%.2f, max x%.1f, %d edges over 2x, %d over 4x"
        % (rest_stretch["p999"], rest_stretch["max"], rest_stretch["edges_over_2x"], rest_stretch["edges_over_4x"]))
    GG._set_verts(ob, rest)
    GG.write_groups(ob, names, W)
    char.rest_pose(arm)
    ob.parent = arm
    ob.matrix_parent_inverse = Matrix.Identity(4)
    md = ob.modifiers.new("Armature", "ARMATURE")
    md.object = arm
    body.hide_render = body.hide_viewport = True
    GG.fit_pose(arm, co, guess)
    apply_hands(arm, hands)
    back, _t = GG._evaluated(ob)
    err = np.linalg.norm(back - co, axis=1)
    log("  round trip (fitted pose on the bound mesh): mean %.4f m, max %.4f m" % (err.mean(), err.max()))
    char.rest_pose(arm)
    return arm, body, {"segments": [int((lab == k).sum()) for k in range(5)], "cross_removed": [n0, n1, n2],
                       "round_trip_mean_m": round(float(err.mean()), 5), "round_trip_max_m": round(float(err.max()), 5),
                       "fit": rep, "limb_islands_to_torso": moved, "rest_stretch": rest_stretch, "fin_band": fins,
                       "hands_fitted": sorted(hands),
                       "finger_weighted_vertices": int((W[:, [j for j, n in enumerate(names)
                                                               if n.startswith(GG.FINGERS)]] > 0.05).any(1).sum()),
                       "joints_weighted": int((W.max(0) > 0).sum())}


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


_CHILD = {"upperarm": "lowerarm", "lowerarm": "hand", "thigh": "calf", "calf": "foot"}


def _aim(arm, name, d):
    """Turn a bone about its head so that the limb (its head to the next joint's head: the imported bones' tails
    point along arbitrary axes) lies along the world direction d; its children follow."""
    pbs = arm.pose.bones
    if name not in pbs:
        return
    pb = pbs[name]
    base, sd = name[:-2], name[-2:]
    nxt = pbs.get(_CHILD.get(base, "") + sd)
    cur = ((nxt.head if nxt else pb.tail) - pb.head).normalized()
    R = cur.rotation_difference(Vector(d).normalized()).to_matrix().to_4x4()
    head = pb.head.copy()
    pb.matrix = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ pb.matrix
    bpy.context.view_layer.update()


# Poses no clip reaches but the game does: the physics ragdoll throws bodies into arms-out and arms-up shapes and
# up to six corpses stay (ART_BIBLE, PLAY.md), and the reference pose itself shows in the editor (review F2).
EXTREMES = ("tpose", "arms_up", "ragdoll_spread", "ragdoll_twist")


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
    elif which == "tpose":
        for sd, x in (("l", 1.0), ("r", -1.0)):
            _aim(arm, "upperarm_" + sd, (x, 0, 0))
            _aim(arm, "lowerarm_" + sd, (x, 0, 0))
    elif which == "arms_up":
        for sd, x in (("l", 1.0), ("r", -1.0)):
            _aim(arm, "upperarm_" + sd, (0.3 * x, 0.05, 1))
            _aim(arm, "lowerarm_" + sd, (0.25 * x, 0.1, 1))
    elif which == "ragdoll_spread":       # thrown on the back: arms flung out above the shoulders, legs apart
        _rot(arm, "spine_01", "X", -15)
        _rot(arm, "spine_03", "X", -10)
        _rot(arm, "head", "Y", 25)
        _aim(arm, "upperarm_l", (0.85, 0.15, 0.5))
        _aim(arm, "lowerarm_l", (0.7, -0.3, 0.65))
        _aim(arm, "upperarm_r", (-0.9, 0.3, 0.3))
        _aim(arm, "lowerarm_r", (-0.6, 0.6, 0.5))
        _aim(arm, "thigh_l", (0.45, -0.15, -0.88))
        _aim(arm, "thigh_r", (-0.4, -0.3, -0.87))
        _rot(arm, "calf_r", "X", 35)
    elif which == "ragdoll_twist":        # face down: one arm up past the head, the other trapped under the chest
        _rot(arm, "spine_01", "Z", 25)
        _rot(arm, "spine_03", "Z", 15)
        _rot(arm, "head", "Z", -50)
        _aim(arm, "upperarm_l", (0.35, 0.25, 0.9))
        _aim(arm, "lowerarm_l", (0.2, -0.2, 0.95))
        _aim(arm, "upperarm_r", (-0.25, -0.75, -0.6))
        _aim(arm, "lowerarm_r", (0.6, -0.6, -0.2))
        _aim(arm, "thigh_l", (0.15, -0.75, -0.65))
        _rot(arm, "calf_l", "X", 95)
        _aim(arm, "thigh_r", (-0.2, 0.25, -0.95))


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
            # a clip that cannot be loaded is a failure of the gate, not a pass (review F5)
            rows.append({"pose": clip, "skipped": str(e)[:100], "ok": False})
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
    for nm in ("swing", "kneel", "crouch") + EXTREMES:
        held_pose(arm, nm)
        measure(nm)
    char.rest_pose(arm)
    fails = [r for r in rows if not r.get("ok")]
    stretch = [r for r in rows if "stretch_max" in r]
    skipped = [r["pose"] for r in rows if "skipped" in r]
    rep = {"poses": len(rows), "failed": len(fails), "skipped": skipped, "ok": not fails and not skipped,
           "capsule_out_m": RG.CAPSULE_OUT,
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

def _lum(c):
    return c[..., 0] * 0.2126 + c[..., 1] * 0.7152 + c[..., 2] * 0.0722


def _sat_srgb(c):
    from mi import bake
    e = np.clip(bake.srgb_encode(c), 0, 1)
    mx = e.max(-1)
    return (mx - e.min(-1)) / np.maximum(mx, 1e-4)


def _blur(a, radius_px):
    """Blur of a 2D float map: three box passes (about a Gaussian) on a 1/4 copy, scaled back with PIL."""
    from PIL import Image
    h, w = a.shape
    b = np.asarray(Image.fromarray(a.astype(np.float32), "F").resize((w // 4, h // 4), Image.BILINEAR), np.float64)
    r = max(1, int(round(radius_px / 4.0 / 1.7)))
    for _ in range(3):
        for ax in (0, 1):
            p = np.pad(b, [(r + 1, r) if i == ax else (0, 0) for i in range(2)], mode="edge")
            c = np.cumsum(p, axis=ax)
            b = (np.take(c, np.arange(2 * r + 1, c.shape[ax]), axis=ax)
                 - np.take(c, np.arange(0, c.shape[ax] - 2 * r - 1), axis=ax)) / (2 * r + 1)
    return np.asarray(Image.fromarray(b.astype(np.float32), "F").resize((w, h), Image.BILINEAR), np.float32)


def delight(tex, log):
    """Review F7: Tripo bakes highlights into the albedo (white speckle on canal_shell's hood that reads as frost,
    white crackle on the waxed parka that reads as cracked leather; about 1 % of texels over 0.2 linear against a
    median of 0.025). A texel brighter than DELIGHT['ratio'] x its neighbourhood (a 48 px blur), or than
    DELIGHT['cap'], is brought down to that level, keeping its hue; saturated colour (oxblood, amber) and metal are
    left. The wet look belongs to the Unreal material (a per-level wet parameter)."""
    bc = tex["bc"]
    L = _lum(bc)
    Lb = _blur(L, 48)
    sat = _sat_srgb(bc)
    metal = tex.get("metal", np.zeros_like(L))
    Lb2 = _blur(L, 192)
    target = np.minimum(np.minimum(np.maximum(DELIGHT["ratio"] * Lb, 0.004), np.maximum(DELIGHT["ratio2"] * Lb2, 0.004)),
                        DELIGHT["cap"])
    hit = (L > target) & (sat < DELIGHT["sat"]) & (metal < METAL_MIN)
    over = float((L > 0.2).mean())
    scale = np.where(hit, target / np.maximum(L, 1e-6), 1.0)
    # broad baked sheen (canal_shell's wet hood and shoulders, a patch several cm across, so above its own blur):
    # a soft knee above twice the figure's median, L' = k (L / k)^0.5, on the same texels' kind
    k = 2.0 * float(np.median(L))
    L1 = L * scale
    knee = (L1 > k) & (sat < DELIGHT["sat"]) & (metal < METAL_MIN)
    scale = np.where(knee, scale * (k * np.sqrt(np.maximum(L1, 1e-6) / k)) / np.maximum(L1, 1e-6), scale)
    hit |= knee
    tex["bc"] = (bc * scale[..., None]).astype(np.float32)
    L2 = _lum(tex["bc"])
    rep = {"texels_lowered": round(float(hit.mean()), 4), "over_0.2_before": round(over, 4),
           "over_0.2_after": round(float((L2 > 0.2).mean()), 4), "median": round(float(np.median(L)), 4)}
    log("  de-light: %.2f %% of texels lowered; over 0.2 linear %.2f %% -> %.2f %% (median %.3f)"
        % (100 * rep["texels_lowered"], 100 * over, 100 * rep["over_0.2_after"], rep["median"]))
    return rep


def eye_shadow(ob, arm, tex, keep_sat, log):
    """Reviews F1 and F8: the skin round the eyes (lids, brows, the bridge of the nose) showed through every mask
    opening, photographic and light, and on roof_lieutenant pink lids read as glowing red eyes at 6 m. On the bound
    mesh (the mannequin's reference pose), the faces of the front of the head between 2 and 17 cm above the head
    joint are found, their UV triangles drawn into a mask (grown 4 px for the island padding), and inside it every
    texel brighter than the mask cloth and not strongly saturated is turned to a dark neutral of luminance EYE_L
    (desaturated 70 %): the eyes in deep shadow inside the opening. The relief stays in the normal map."""
    from PIL import Image, ImageDraw, ImageFilter
    me = ob.data
    hb = arm.data.bones["head"]
    H = np.array(hb.head_local)
    co = GG._verts(ob)
    me.calc_loop_triangles()
    nt = len(me.loop_triangles)
    tv = np.empty(nt * 3, np.int64)
    me.loop_triangles.foreach_get("vertices", tv)
    tl = np.empty(nt * 3, np.int64)
    me.loop_triangles.foreach_get("loops", tl)
    tv, tl = tv.reshape(-1, 3), tl.reshape(-1, 3)
    c = co[tv].mean(1)
    n = np.cross(co[tv[:, 1]] - co[tv[:, 0]], co[tv[:, 2]] - co[tv[:, 0]])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    sel = ((c[:, 2] > H[2] + 0.02) & (c[:, 2] < H[2] + 0.17) & (np.abs(c[:, 0] - H[0]) < 0.085)
           & (c[:, 1] < H[1] - 0.02) & (n[:, 1] < -0.15))
    uv = np.empty(len(me.loops) * 2)
    me.uv_layers.active.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    h, w = tex["bc"].shape[:2]
    m = Image.new("L", (w, h), 0)
    dr = ImageDraw.Draw(m)
    for t in tl[sel]:
        pts = [(float(uv[i, 0] * w), float((1.0 - uv[i, 1]) * h)) for i in t]
        dr.polygon(pts, fill=255)
    m = m.filter(ImageFilter.MaxFilter(9))
    mask = np.asarray(m) > 0
    bc = tex["bc"]
    L = _lum(bc)
    sat = _sat_srgb(bc)
    cloth = float(np.percentile(L[mask], 35)) if mask.any() else 0.02
    lo = max(cloth * 1.4, 0.012)
    f = np.clip((L - lo) / 0.02, 0, 1) * mask
    if keep_sat is not None:
        f *= np.clip((keep_sat - sat) / 0.1 + 0.5, 0, 1)
    grey = L[..., None] * np.ones(3)
    tgt = 0.3 * bc + 0.7 * grey
    tgt = tgt * (EYE_L / np.maximum(_lum(tgt), 1e-6))[..., None]
    tex["bc"] = (bc * (1 - f[..., None]) + tgt * f[..., None]).astype(np.float32)
    rep = {"faces": int(sel.sum()), "mask_texels": int(mask.sum()), "darkened_texels": int((f > 0.5).sum()),
           "mask_cloth_luminance": round(cloth, 4),
           "band_luminance_before": round(float(L[f > 0.5].mean()) if (f > 0.5).any() else 0.0, 4)}
    log("  eye band: %d faces, %d texels in the mask (cloth %.3f), %d darkened (mean luminance %.3f -> %.3f)"
        % (rep["faces"], rep["mask_texels"], cloth, rep["darkened_texels"], rep["band_luminance_before"], EYE_L))
    return rep


def write_set(set_name, tex, log, rough_floor=None):
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
    # the wet droplets and glints are in the roughness too: keep half of its fine pattern (the rest from a 1 cm blur)
    rough = (ROUGH_DETAIL * rough + (1 - ROUGH_DETAIL) * _blur(rough, 32)).astype(np.float32)
    if rough_floor is None:
        rough = (ROUGH_REMAP[0] + ROUGH_REMAP[1] * rough).astype(np.float32)
    else:
        rough = (rough_floor + (ROUGH_TOP - rough_floor) * rough).astype(np.float32)
    metal = tex.get("metal", np.zeros((h, w), np.float32))
    metal = np.where(metal > METAL_MIN, metal, 0.0).astype(np.float32)
    ao = tex.get("ao", np.ones((h, w), np.float32))
    orm = np.stack([ao, rough, metal], -1)
    Image.fromarray((np.clip(orm, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(d, "T_%s_ORM.png" % set_name))
    info = {"kind": "generated", "asset": "SK_" + set_name.replace("Vulture", "Vulture_", 1), "resolution": [w, h],
            "albedo_mean": [round(float(v), 4) for v in tex["bc"].reshape(-1, 3).mean(0)],
            "roughness_mean": round(float(rough.mean()), 3), "metallic_mean": round(float(metal.mean()), 3),
            "ao_mean": round(float(ao.mean()), 3),
            "roughness_remap": [rough_floor, ROUGH_TOP] if rough_floor is not None else list(ROUGH_REMAP),
            "metallic_min": METAL_MIN,
            "note": "generated multiview PBR maps rewritten to the project's set: BC sRGB (baked highlights lowered, "
                    "the eye band darkened), N OpenGL, ORM (R = the generated occlusion, G = floor + (0.95 - floor) x "
                    "the generated roughness, B = metallic where over 0.5)"}
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
    arm, body, brep = bind(ctx, ob, top_factor, log)
    rep["bind"] = brep
    style = STYLE.get(cid, {})
    rep["delight"] = delight(tex, log)
    rep["eye_band"] = eye_shadow(ob, arm, tex, style.get("keep_sat", 0.65), log)
    rep["set"] = write_set(sname, tex, log, style.get("rough_floor"))
    old = ob.data.materials[0] if ob.data.materials else None
    if old is not None:
        old.name = slot + "__generated"
    m = set_material(slot, sname)
    ob.data.materials.clear()
    ob.data.materials.append(m)
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
        # the posed gate is part of the verdict (review F5): a failed pose or a skipped clip fails the export check
        chk["export_ok"] = chk["ok"]
        chk["ok"] = bool(chk["export_ok"] and rep["pose_check"]["ok"])
        if not chk["ok"]:
            ctx.log("  GATE FAILED: export checks %s, pose check %s (%d failed, skipped %s)"
                    % (chk["export_ok"], rep["pose_check"]["ok"], rep["pose_check"]["failed"],
                       rep["pose_check"]["skipped"]))
        with open(path + ".check.json", "w") as f:
            json.dump(chk, f, indent=1, default=str)
        lo, hi = scene.bounds(ob)
        entry = {"name": v["asset"], "family": "vultures", "kind": "skeletal", "glb": os.path.relpath(path, paths.art),
                 "skeleton": "SK_Mannequin (all 89 joints)", "triangles": rep["triangles"],
                 "bounds_m": {"min": [round(float(x), 4) for x in lo], "max": [round(float(x), 4) for x in hi]},
                 "material_slots": [{"slot": v["slot"], "workflow": "unique", "set": sname}],
                 "notes": v["notes"] + "; mesh scale 0.98 in the game like the Goons; hit volumes from config.json",
                 "checks": os.path.relpath(path + ".check.json", paths.art), "checks_ok": chk["ok"],
                 "pose_check": {k: rep["pose_check"][k] for k in ("poses", "failed", "skipped", "ok")}}
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
    for cid, v in ctx.vult.items():
        ob, arm = v["ob"], v["arm"]
        base = os.path.join(PREV, "vulture_%s" % cid)
        # a private folder per run and character: two lanes rendering at once used to overwrite v_hero_day.png
        tmp = tempfile.mkdtemp(prefix="vult_%s_" % cid)
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
        if want("hands"):
            # review F3: the gloves on the finger bones, in the aim and the jog (the SMG grip) and at rest
            _key_fill()
            shots, labels = [], []
            for clip, frac, lab, sd in (("rifle_idle_ads", 0.3, "aim, right hand", "r"),
                                        ("rifle_idle_ads", 0.3, "aim, left hand", "l"),
                                        ("rifle_jog_fwd", 0.3, "jog, right hand", "r"),
                                        (None, 0, "reference pose, right hand", "r")):
                if clip:
                    src, _act, rng = char.import_clip(clip)
                    bpy.context.scene.frame_set(int(rng[0] + (rng[1] - rng[0]) * frac))
                    char.pose_from_armature(arm, src)
                    bpy.data.objects.remove(src, do_unlink=True)
                    if "root" in arm.pose.bones:
                        arm.pose.bones["root"].matrix_basis = Matrix.Identity(4)
                bpy.context.view_layer.update()
                pb = arm.pose.bones["hand_" + sd]
                hc = arm.matrix_world @ ((pb.head + arm.pose.bones["middle_02_" + sd].head) * 0.5)
                side = -1.0 if sd == "r" else 1.0
                render.cam_look((hc.x + 0.38 * side, hc.y - 0.30, hc.z + 0.12), tuple(hc), lens=50, name="Cam_Hand")
                pp = os.path.join(tmp, "v_hand_%d.png" % len(shots))
                render.render_png(pp, a.samples, (480, 480))
                shots.append(pp)
                labels.append(lab)
                char.rest_pose(arm)
            render.contact_sheet(shots, base + "_hands.jpg", cols=4, labels=labels)
            ctx.log("preview %s_hands.jpg" % os.path.basename(base))
        if want("extremes"):
            # review F2: the reference pose and the ragdoll's arms-out shapes, from behind (the under-arm fins)
            render.rig_day(sun_azimuth=35.0, stops=0.4)
            shots, labels = [], []
            for nm, lab in ((None, "reference pose, back"), ("tpose", "T-pose, back"), ("arms_up", "arms up, back"),
                            ("ragdoll_spread", "ragdoll, arms flung")):
                if nm:
                    held_pose(arm, nm)
                bpy.context.view_layer.update()
                render.cam_look((1.9, 3.4, 1.5), (0.0, 0.0, 1.15), lens=32, name="Cam_Ext")
                pp = os.path.join(tmp, "v_ext_%d.png" % len(shots))
                render.render_png(pp, a.samples, (480, 560))
                shots.append(pp)
                labels.append(lab)
                char.rest_pose(arm)
            render.contact_sheet(shots, base + "_extremes.jpg", cols=4, labels=labels)
            ctx.log("preview %s_extremes.jpg" % os.path.basename(base))
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
