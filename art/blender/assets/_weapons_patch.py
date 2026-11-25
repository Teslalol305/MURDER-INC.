"""Round 4, lane 2: the mounts of the CHOPPER and the NINE.

The Workbench offers a part only where the gun has the part's mount (guns.json mounts, docs/unreal/LOADOUT.md 6.6), and
the two guns the owner has played carried no mount: the CHOPPER's and the NINE's sockets stop at the palms. This module
adds them to the EXPORTED files, never touching one vertex, one UV, one normal or one colour of the proven meshes (the
4K sets were baked on the exact UV layout: a code rebuild re-unwraps and could mismatch them; specification C5), and it
is re-runnable after any later export of either gun:

    python art/blender/assets/_weapons_patch.py                  # both guns
    python art/blender/assets/_weapons_patch.py chopper|nine     # one gun
    python art/blender/assets/_weapons_patch.py --force          # re-patch from the kept unpatched export

What is added (gun space, metres, bones at rest with the gun's axes: nothing existing moves):

  SK_Chopper  sockets Optic (0.1150, 0, 0.0420)        centre of the 106 mm top-cover rail on the lug tops
                      MuzzleMount (0.4260, 0, 0)        base plane of the booster / the gas block's front face
                      Underbarrel (0.3050, 0, -0.0623)  underside of the lower handguard (saddle clamp, no rail)
              bones   Booster (deform, head (0.4260, 0, 0)): the booster shell, a closed loose shell X 0.4260..0.4975,
                      moves from `body` to `Booster` so a muzzle part can hide it (an 8.5 mm barrel stub with its bore
                      stays behind); FrontSight (deform, head (0.409, 0, 0.031)): the gas-block tower, its two ears, the
                      drum and the post above Z 0.0316, a shell of its own with the housing capped below it, so an optic
                      can hide the iron front sight that would stand in the view.
  SK_Nine     sockets Laser (0.1560, 0, -0.0236)       middle lug of the dust-cover rail, on its underside
                      MuzzleMount (0.1960, 0, 0)        the slide's front face, where a suppressor seats
                      MagHinge (0.0177, 0, -0.0359)     centre of the standard magazine's top face

The output is the exporter's own layout (one primitive per slot, rigid joints, the root joint carries the Z-up to Y-up
turn, every other joint the identity rotation), rewritten with the new joints, the new inverse bind matrices and the
re-weighted vertices; `rig.verify` re-imports it in a fresh process and poses every bone, and the diff report written
next to the file proves that every position, normal, UV, colour and index of the old file is still there.
"""
import json
import math
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BL = os.path.dirname(HERE)
if BL not in sys.path:
    sys.path.insert(0, BL)

import bpy  # noqa: E402,F401  (the bpy module provides bmesh and mathutils)
import numpy as np  # noqa: E402

from mi import export, paths, rig  # noqa: E402

GLB_DIR = paths.glb
KEEP = os.path.join(GLB_DIR, "_pre_patch")           # the unpatched exports, the source of every re-patch

CT = {5126: np.float32, 5123: np.uint16, 5125: np.uint32, 5121: np.uint8, 5122: np.int16, 5120: np.int8}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}

# ---------------------------------------------------------------------------------------------------- the contract
CHOPPER = {
    "name": "SK_Chopper", "root": "body",
    "bones": [("Booster", (0.4260, 0.0, 0.0)), ("FrontSight", (0.4090, 0.0, 0.0310))],            # deform, parent body
    "sockets": [("Optic", (0.1150, 0.0, 0.0420)), ("MuzzleMount", (0.4260, 0.0, 0.0)),
                ("Underbarrel", (0.3050, 0.0, -0.0623))],
    "booster_x": 0.4260,                                  # the booster shell: every vertex of the component from here
    # the specification's box (X 0.4005..0.4175) is narrower than the tower's foot (X 0.3995..0.4185): the whole gas block's
    # length is used, nothing but the sight stands above Z 0.0316 there (housing top Z 0.013, tower from Z 0.0283)
    "front_sight": {"z": 0.0316, "x": (0.3925, 0.4260), "y": 0.0125},
}
NINE = {
    "name": "SK_Nine", "root": "frame", "bones": [],
    "sockets": [("Laser", (0.1560, 0.0, -0.0236)), ("MuzzleMount", (0.1960, 0.0, 0.0)),
                ("MagHinge", (0.0177, 0.0, -0.0359))],
}
GUNS = {"chopper": CHOPPER, "nine": NINE}

CHOPPER_NOTES_ADD = (
    " Round 4 mounts (patched into the exported file, no vertex changed): sockets Optic (0.1150, 0, 0.0420) = centre of the "
    "106 mm top-cover rail on the lug tops (lug tops Z 0.0420 for X 0.064..0.168, slot floors 0.0366), MuzzleMount "
    "(0.4260, 0, 0) = the booster's base plane on the bore, Underbarrel (0.3050, 0, -0.0623) = the lower handguard's "
    "underside; bone Booster (head (0.4260, 0, 0): the muzzle booster, a closed shell X 0.4260..0.4975; hide it for a muzzle "
    "part: the barrel stays behind as an 8.5 mm stub with its bore to X 0.4345); bone FrontSight (head (0.409, 0, 0.031): the "
    "front sight's tower, ears, drum and post above Z 0.0316, a closed shell; hide it when an optic is fitted: the gas "
    "block's housing is capped below it).")
NINE_NOTES_ADD = (
    " Round 4 mounts (patched into the exported file, no vertex changed): sockets Laser (0.1560, 0, -0.0236) = the middle "
    "lug of the dust-cover rail, on its underside (the rail's four 45 deg slots are cut at X 0.135 / 0.149 / 0.163 / 0.177), "
    "MuzzleMount (0.1960, 0, 0) = the slide's front face (the barrel's crown stub, R 6.8 mm, stands 4.5 mm proud of it), "
    "MagHinge (0.0177, 0, -0.0359) = the centre of the standard magazine's top face (the extended magazine's mount, "
    "modelled pre-canted along the grip axis (0.250, 0, 0.968)).")


# --------------------------------------------------------------------------------------------------------- GLB model
class Glb:
    """A GLB as numpy arrays: every accessor read into memory, edited, and written back as one fresh binary chunk
    (one buffer view per accessor, 4-byte aligned, POSITION bounds recomputed)."""

    def __init__(self, path):
        self.path = path
        self.js, binc = rig.read_glb(path)
        self.data, self.target = {}, {}
        for i, a in enumerate(self.js["accessors"]):
            bv = self.js["bufferViews"][a["bufferView"]]
            start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
            n = a["count"] * NC[a["type"]]
            arr = np.frombuffer(binc, dtype=CT[a["componentType"]], count=n, offset=start).copy()
            self.data[i] = arr.reshape(a["count"], NC[a["type"]])
            self.target[i] = bv.get("target")
        self.pos_acc = {p["attributes"]["POSITION"] for m in self.js["meshes"] for p in m["primitives"]}

    # -- skeleton
    def joint_names(self):
        return [self.js["nodes"][j]["name"] for j in self.js["skins"][0]["joints"]]

    def _root_matrix(self):
        from mathutils import Quaternion
        skin = self.js["skins"][0]
        n = self.js["nodes"][skin["joints"][0]]
        x, y, z, w = n.get("rotation", [0, 0, 0, 1])
        M = np.eye(4)
        M[:3, :3] = np.array(Quaternion((w, x, y, z)).to_matrix())
        M[:3, 3] = n.get("translation", [0, 0, 0])
        return M

    def ibm_for(self, asset_pos):
        """Inverse bind matrix (raw column-major row) of a joint at asset position `asset_pos`, child of the root."""
        G = self._root_matrix() @ np.array([[1, 0, 0, asset_pos[0]], [0, 1, 0, asset_pos[1]], [0, 0, 1, asset_pos[2]],
                                            [0, 0, 0, 1.0]])
        return np.linalg.inv(G).T.astype(np.float32).ravel()

    def add_joint(self, name, asset_pos):
        """A joint child of the root at asset_pos (the root sits at the asset origin). Returns its skin index."""
        js = self.js
        skin = js["skins"][0]
        assert name not in self.joint_names(), "joint %s exists" % name
        nodes = js["nodes"]
        nodes.append({"name": name, "translation": [float(np.float32(v)) for v in asset_pos]})
        k = len(nodes) - 1
        nodes[skin["joints"][0]].setdefault("children", []).append(k)
        skin["joints"].append(k)
        acc = skin["inverseBindMatrices"]
        self.data[acc] = np.vstack([self.data[acc], self.ibm_for(asset_pos)[None, :]])
        return len(skin["joints"]) - 1

    def check_ibm(self):
        """Our inverse bind matrices reproduce the file's for every existing joint (proof that the convention is read
        right): max abs difference."""
        skin = self.js["skins"][0]
        worst = 0.0
        for k, j in enumerate(skin["joints"]):
            if k == 0:
                continue
            n = self.js["nodes"][j]
            t = n.get("translation", [0, 0, 0])
            worst = max(worst, float(np.abs(self.ibm_for(t) - self.data[skin["inverseBindMatrices"]][k]).max()))
        return worst

    # -- geometry helpers
    def prims(self):
        return self.js["meshes"][0]["primitives"]

    def prim_arrays(self, pi):
        p = self.prims()[pi]
        a = p["attributes"]
        return {k: a[k] for k in a} | {"indices": p["indices"]}

    def asset_positions(self, pi):
        P = self.data[self.prims()[pi]["attributes"]["POSITION"]].astype(np.float64)
        return np.stack([P[:, 0], -P[:, 2], P[:, 1]], 1)           # glTF (+Y up) -> asset (Blender, Z up)

    def set_joint(self, pi, mask, joint):
        a = self.prims()[pi]["attributes"]
        self.data[a["JOINTS_0"]][mask] = np.array([joint, 0, 0, 0], dtype=self.data[a["JOINTS_0"]].dtype)
        self.data[a["WEIGHTS_0"]][mask] = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)

    def save(self, path):
        js = self.js
        bvs, chunks, off = [], [], 0
        for i, a in enumerate(js["accessors"]):
            arr = np.ascontiguousarray(self.data[i])
            raw = arr.tobytes()
            bv = {"buffer": 0, "byteLength": len(raw), "byteOffset": off}
            if self.target.get(i):
                bv["target"] = self.target[i]
            bvs.append(bv)
            a["bufferView"] = i
            a.pop("byteOffset", None)
            a["count"] = int(len(arr))
            if i in self.pos_acc:
                a["min"] = [float(v) for v in arr.min(axis=0)]
                a["max"] = [float(v) for v in arr.max(axis=0)]
            pad = (-len(raw)) % 4
            chunks.append(raw + b"\0" * pad)
            off += len(raw) + pad
        js["bufferViews"] = bvs
        js["buffers"] = [{"byteLength": off}]
        jb = json.dumps(js, separators=(",", ":")).encode("utf-8")
        jb += b" " * ((-len(jb)) % 4)
        bb = b"".join(chunks)
        with open(path, "wb") as f:
            f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(jb) + 8 + len(bb)))
            f.write(struct.pack("<II", len(jb), 0x4E4F534A))
            f.write(jb)
            f.write(struct.pack("<II", len(bb), 0x004E4942))
            f.write(bb)


def components(P, idx):
    """Connected component id per vertex of a triangle list, vertices welded by position (the exporter splits
    vertices along UV seams and hard edges, so the index buffer alone under-connects)."""
    key = np.round(P * 1e6).astype(np.int64)
    _u, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    parent = np.arange(inv.max() + 1)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for t in idx.reshape(-1, 3):
        ra = find(inv[t[0]])
        for v in t[1:]:
            rb = find(inv[v])
            if rb != ra:
                parent[rb] = ra
    return np.array([find(inv[i]) for i in range(len(P))])


# ---------------------------------------------------------------------------------------------------------- CHOPPER
def booster_vertices(g, pi, x0):
    """The booster: every vertex of the connected components that lie wholly at X >= x0 (a closed loose shell)."""
    P = g.asset_positions(pi)
    idx = g.data[g.prims()[pi]["indices"]].astype(np.int64).ravel()
    comp = components(P, idx)
    sel = np.zeros(len(P), bool)
    for c in np.unique(comp):
        m = comp == c
        if P[m, 0].min() >= x0 - 1e-5:
            sel |= m
    return sel


def front_sight_cut(g, pi, cfg, joint_front, joint_body):
    """Split the front sight off the gas block: the triangles above Z cfg['z'] inside the box become a shell of their own
    on bone FrontSight (every vertex they share with the housing is duplicated, so no vertex is shared: a hidden bone
    must not stretch the housing's triangles toward its head), and the housing's open ring on the cut plane is closed by
    a planar fan on bone body, so hiding the sight leaves a closed stump."""
    p = g.prims()[pi]
    A = p["attributes"]
    pos, nor, uv = g.data[A["POSITION"]], g.data[A["NORMAL"]], g.data[A["TEXCOORD_0"]]
    col, jn, wt = g.data[A["COLOR_0"]], g.data[A["JOINTS_0"]], g.data[A["WEIGHTS_0"]]
    idx = g.data[p["indices"]].astype(np.int64).ravel().reshape(-1, 3)
    P = np.stack([pos[:, 0], -pos[:, 2], pos[:, 1]], 1).astype(np.float64)
    cen = P[idx].mean(axis=1)
    (xa, xb), yh, zc = cfg["x"], cfg["y"], cfg["z"]
    sel = (cen[:, 2] > zc) & (cen[:, 0] > xa) & (cen[:, 0] < xb) & (np.abs(cen[:, 1]) < yh)
    vsel = np.zeros(len(P), bool)
    vsel[idx[sel].ravel()] = True
    vun = np.zeros(len(P), bool)
    vun[idx[~sel].ravel()] = True
    shared = np.nonzero(vsel & vun)[0]                       # vertex entries used by both sides: copy them for the sight
    # the cut ring in space: positions touched by both sides (entries may be split by normals, so weld by position)
    key = np.round(P * 1e6).astype(np.int64)
    _u, pid = np.unique(key, axis=0, return_inverse=True)
    pid = pid.ravel()
    sel_pid = np.zeros(pid.max() + 1, bool)
    sel_pid[pid[vsel]] = True
    un_pid = np.zeros(pid.max() + 1, bool)
    un_pid[pid[vun]] = True
    ring_pid = np.nonzero(sel_pid & un_pid)[0]
    assert len(ring_pid) >= 8, "the front sight's cut ring was not found (%d positions)" % len(ring_pid)
    first = {}
    for v in np.nonzero(vun)[0]:                              # the housing side's entry of every ring position
        if un_pid[pid[v]] and sel_pid[pid[v]] and pid[v] not in first:
            first[pid[v]] = v
    ring = np.array([first[q] for q in ring_pid])
    copies = {int(v): len(P) + k for k, v in enumerate(shared)}
    pos2 = np.vstack([pos, pos[shared]])
    nor2 = np.vstack([nor, nor[shared]])
    uv2 = np.vstack([uv, uv[shared]])
    col2 = np.vstack([col, col[shared]])
    jn2 = np.vstack([jn, jn[shared]])
    wt2 = np.vstack([wt, wt[shared]])
    remap = np.arange(len(P))
    for v, nv in copies.items():
        remap[v] = nv
    idx2 = idx.copy()
    idx2[sel] = remap[idx[sel]]
    used = np.zeros(len(pos2), bool)
    used[idx2[sel].ravel()] = True
    jn2[used] = np.array([joint_front, 0, 0, 0], dtype=jn2.dtype)
    wt2[used] = np.array([1, 0, 0, 0], dtype=np.float32)
    # planar fan over the ring (order by angle: the ring is a convex rounded rectangle)
    Pr = P[ring]
    c = Pr.mean(axis=0)
    ring = ring[np.argsort(np.arctan2(Pr[:, 1] - c[1], Pr[:, 0] - c[0]))]
    Pr = P[ring]
    zcap = float(Pr[:, 2].mean())
    up = np.array([[0.0, 1.0, 0.0]], np.float32)             # asset +Z in glTF
    n = len(ring)
    k0 = len(pos2)
    cpos = np.array([[c[0], zcap, -c[1]]], np.float32)
    pos2 = np.vstack([pos2, cpos, pos[ring]])
    nor2 = np.vstack([nor2, np.tile(up, (n + 1, 1))])
    uv2 = np.vstack([uv2, uv[ring].mean(axis=0, keepdims=True), uv[ring]])
    col2 = np.vstack([col2, col[ring][:1], col[ring]])
    jn2 = np.vstack([jn2, np.tile(np.array([[joint_body, 0, 0, 0]], dtype=jn.dtype), (n + 1, 1))])
    wt2 = np.vstack([wt2, np.tile(np.array([[1, 0, 0, 0]], np.float32), (n + 1, 1))])
    fan = np.array([(k0, k0 + 1 + k, k0 + 1 + (k + 1) % n) for k in range(n)], dtype=np.int64)
    a3 = np.stack([pos2[fan[0, i]] for i in range(3)])
    a3 = np.stack([a3[:, 0], -a3[:, 2], a3[:, 1]], 1).astype(np.float64)
    if np.cross(a3[1] - a3[0], a3[2] - a3[0])[2] < 0:
        fan = fan[:, ::-1]
    idx2 = np.vstack([idx2, fan])
    g.data[A["POSITION"]], g.data[A["NORMAL"]], g.data[A["TEXCOORD_0"]] = pos2, nor2, uv2
    g.data[A["COLOR_0"]], g.data[A["JOINTS_0"]], g.data[A["WEIGHTS_0"]] = col2, jn2, wt2
    big = len(pos2) > 65535
    g.data[p["indices"]] = idx2.ravel().astype(np.uint32 if big else np.uint16)[:, None]
    g.js["accessors"][p["indices"]]["componentType"] = 5125 if big else 5123
    return {"selected_triangles": int(sel.sum()), "copied_vertices": int(len(shared)), "ring_positions": int(n),
            "cap_triangles": int(n), "cap_z": round(zcap, 5), "front_sight_vertices": int(used.sum())}


# --------------------------------------------------------------------------------------------------- patch a gun
def patch(key, force=False, log=print):
    cfg = GUNS[key]
    name = cfg["name"]
    path = os.path.join(GLB_DIR, name + ".glb")
    os.makedirs(KEEP, exist_ok=True)
    src = os.path.join(KEEP, name + ".glb")
    g0 = Glb(path)
    already = "MuzzleMount" in g0.joint_names()
    if not already:
        shutil.copy2(path, src)                                  # a fresh export: it becomes the unpatched source
    elif not os.path.exists(src):
        raise SystemExit("%s is already patched and no unpatched copy is kept in %s" % (name, KEEP))
    elif not force:
        log("%s: already patched (use --force to re-patch from %s)" % (name, os.path.relpath(src, paths.art)))
        return None
    g = Glb(src)
    report = {"gun": name, "source": os.path.relpath(src, paths.art), "ibm_convention_error": g.check_ibm()}
    assert report["ibm_convention_error"] < 1e-6, "inverse bind matrix convention not reproduced"
    joints = {}
    for b, pos in cfg["bones"]:
        joints[b] = g.add_joint(b, pos)
    for s, pos in cfg["sockets"]:
        joints[s] = g.add_joint(s, pos)
    report["joints"] = {k: v for k, v in joints.items()}
    if key == "chopper":
        pi = [m["name"] for m in g.js["materials"]].index("M_Chopper_Front")
        sel = booster_vertices(g, pi, cfg["booster_x"])
        g.set_joint(pi, sel, joints["Booster"])
        P = g.asset_positions(pi)[sel]
        report["booster"] = {"vertices": int(sel.sum()), "bbox_x": [round(float(P[:, 0].min()), 4), round(float(P[:, 0].max()), 4)],
                             "max_radius": round(float(np.hypot(P[:, 1], P[:, 2]).max()), 4)}
        report["front_sight"] = front_sight_cut(g, pi, cfg["front_sight"], joints["FrontSight"], 0)
    tmp = path + ".patching"
    g.save(tmp)
    os.replace(tmp, path)
    report["diff"] = diff(Glb(src), Glb(path))
    return report


def diff(a, b):
    """What changed between two GLBs: per primitive, are the old POSITION / NORMAL / TEXCOORD_0 / COLOR_0 arrays and
    the indices still the prefix of the new ones, and which vertices got another joint."""
    out = {"primitives": []}
    ok = True
    for pi, (pa, pb) in enumerate(zip(a.prims(), b.prims())):
        rec = {"material": a.js["materials"][pa["material"]]["name"]}
        na = len(a.data[pa["attributes"]["POSITION"]])
        for k in ("POSITION", "NORMAL", "TEXCOORD_0", "COLOR_0"):
            old, new = a.data[pa["attributes"][k]], b.data[pb["attributes"][k]]
            same = bool(np.array_equal(old, new[:na]))
            rec[k + "_prefix_identical"] = same
            ok &= same
        ja, jb = a.data[pa["attributes"]["JOINTS_0"]], b.data[pb["attributes"]["JOINTS_0"]]
        wa, wb = a.data[pa["attributes"]["WEIGHTS_0"]], b.data[pb["attributes"]["WEIGHTS_0"]]
        ch = np.nonzero((ja != jb[:na]).any(axis=1) | (wa != wb[:na]).any(axis=1))[0]
        rec["reweighted_vertices"] = int(len(ch))
        rec["joints_after"] = sorted(set(jb[:, 0].tolist()))
        ia = a.data[pa["indices"]].ravel()
        ib = b.data[pb["indices"]].ravel()
        rec["triangles_old_new"] = [int(len(ia) // 3), int(len(ib) // 3)]
        rec["vertices_old_new"] = [na, int(len(b.data[pb["attributes"]["POSITION"]]))]
        if len(ia) == len(ib) and na == rec["vertices_old_new"][1]:
            rec["indices_identical"] = bool(np.array_equal(ia, ib))
            ok &= rec["indices_identical"]
        out["primitives"].append(rec)
    out["ok"] = bool(ok)
    return out


# ---------------------------------------------------------------------------------------------------- proof + manifest
def poses_for(key):
    from assets import weapons as W
    if key == "chopper":
        return W.chopper_poses() + [
            {"name": "booster pushed 20 mm", "bones": {"Booster": {"translate": (0.02, 0, 0)}}},
            {"name": "front sight pushed up 20 mm", "bones": {"FrontSight": {"translate": (0, 0, 0.02)}}}]
    return W.nine_poses()


def verify(key, log=print):
    cfg = GUNS[key]
    path = os.path.join(GLB_DIR, cfg["name"] + ".glb")
    rep = rig.verify(path, poses_for(key))
    ok = rep["ok"] and rep["glb"]["all_axes_are_asset_axes"]
    log("%s: re-import proof %s; poses %s; joint axes = gun axes: %s" % (
        cfg["name"], "OK" if ok else "FAILED", ", ".join("%s %.1e m" % (p["name"], p["max_error_m"]) for p in rep["poses"]),
        rep["glb"]["all_axes_are_asset_axes"]))
    if not ok:
        raise SystemExit(json.dumps(rep)[:3000])
    return rep


def update_manifest(key, rep):
    cfg = GUNS[key]
    name = cfg["name"]
    m = json.load(open(paths.manifest))
    e = m["assets"][name]
    info = rig.inspect_glb(os.path.join(GLB_DIR, name + ".glb"))
    u = lambda v: [round(float(v[0]) * 100, 3), round(-float(v[1]) * 100, 3), round(float(v[2]) * 100, 3)]
    sk = e.setdefault("skeleton", {})
    sock = e.setdefault("sockets", {})
    for b, pos in cfg["bones"]:
        sk[b] = {"parent": cfg["root"], "head_m": [round(v, 5) for v in pos], "head_unreal_cm": u(pos), "deform": True,
                 "rest_orientation": "identity: local X = asset X (bore), Z = up, Y = left"}
    for s, pos in cfg["sockets"]:
        sk[s] = {"parent": cfg["root"], "head_m": [round(v, 5) for v in pos], "head_unreal_cm": u(pos), "deform": False,
                 "rest_orientation": "identity: local X = asset X (bore), Z = up, Y = left"}
        sock[s] = [round(v, 5) for v in pos]
    e["proof"] = {"poses": rep.get("poses"), "ok": rep.get("ok")}
    e["triangles"] = int(sum(m["triangles"] for m in info["meshes"]))             # the FrontSight's cap adds 72 triangles to the CHOPPER
    add = CHOPPER_NOTES_ADD if key == "chopper" else NINE_NOTES_ADD
    if add.strip()[:30] not in e.get("notes", ""):
        e["notes"] = e.get("notes", "") + add
    export.write_manifest([e], [])
    return e


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    force = "--force" in argv
    keys = [a for a in argv if a in GUNS] or list(GUNS)
    for key in keys:
        rep = patch(key, force=force)
        if rep is None:
            continue
        print(json.dumps(rep, indent=1))
        if not rep["diff"]["ok"]:
            raise SystemExit("%s: the patched file differs from the original beyond the joints" % key)
        v = verify(key)
        update_manifest(key, v)
        with open(os.path.join(GLB_DIR, GUNS[key]["name"] + ".patch.json"), "w") as f:
            json.dump(rep, f, indent=1)
    print("patched:", ", ".join(keys))


if __name__ == "__main__":
    main()
