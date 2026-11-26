"""Offline first-person reconstruction in Blender (HANDS_R4.md 12): the game's own data and rig maths (fp_math.py)
applied to the meshes the game draws (art/out/glb: SK_RuleArms, the gun's SK_*, its SM_Weapon_*Magazine), rendered
from the eye (the first-person field of view) and from a camera beside the player.

Run with Blender as a Python module (art/blender/README.md; one heavy job at a time on this container's 4 CPUs):

    /home/user/mi-venv/bin/python tools/box/fp/offline/fp_offline.py [--guns chopper,shorty,stretch,rattler,nine]
        [--states hip,aim,r0.5,r1.1] [--cams eye,side,left] [--res 640] [--samples 16] [--out DIR] [--report-only]
        [--blade DEG] [--pole-l X,Y,Z] [--pole-r X,Y,Z] [--shoulder-l X,Y,Z|rest] [--threads 3]
        [--shoulders X,Y,Z] [--relief M] [--tag -whatif]      (what-if: data changed in this run only)

Writes DIR/<gun>-<state>-<cam>.jpg and DIR/report.json (per frame: the hands against their targets, the support
elbow's bend and forearm slope as the game's development log measures them, distances from the eye, and from a flat
ID render of the eye's view: how much of the magazine and of the pistol grip the hands hide, how much of the picture
each hand covers). --report-only skips the beauty renders (the ID renders still run for the eye).
"""
import argparse
import json
import math
import os
import sys

import warnings

import bpy
import numpy as np

warnings.filterwarnings("ignore", category=DeprecationWarning)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_math as fm  # noqa: E402

TEX = os.path.join(fm.ROOT, "art", "out", "textures")
D = np.diag([1.0, -1.0, 1.0])


# ------------------------------------------------------------------------------------------------ frames: UE cm <-> Blender m
def ue_from_bl_matrix(M):
    M = np.array(M, float)
    out = np.eye(4)
    out[:3, :3] = D @ M[:3, :3] @ D
    out[:3, 3] = D @ M[:3, 3] * 100.0
    return out


def bl_from_ue_matrix(M):
    out = np.eye(4)
    out[:3, :3] = D @ M[:3, :3] @ D
    out[:3, 3] = D @ M[:3, 3] / 100.0
    return out


def bl_point(p):
    return D @ np.asarray(p, float) / 100.0


def to_mat(M):
    from mathutils import Matrix
    return Matrix([list(r) for r in M])


# ------------------------------------------------------------------------------------------------ importing
def import_glb(path, name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    for o in new:
        if o.parent is None:
            o.parent = root
    for o in new:
        if o.type == "MESH" and o.name.lower().startswith("icosphere"):
            o.hide_render = True    # the importer's joint display shape
    return root, new


_tex_cache = {}


def small_texture(folder, key, size=1024):
    """A 1K copy of a 4K texture (art/out/textures/<set>/T_<set>_<key>.png), cached in the output folder's tex/."""
    src = os.path.join(TEX, folder, "T_%s_%s.png" % (folder, key))
    if not os.path.exists(src):
        return None
    dst = os.path.join(OUT_TEX, "%s_%s_%d.png" % (folder, key, size))
    if not os.path.exists(dst):
        from PIL import Image
        im = Image.open(src)
        im = im.convert("RGB") if key in ("BC", "ORM") else im
        im.thumbnail((size, size))
        im.save(dst)
    if dst not in _tex_cache:
        img = bpy.data.images.load(dst)
        if key != "BC":
            img.colorspace_settings.name = "Non-Color"
        _tex_cache[dst] = img
    return _tex_cache[dst]


def textured(mat_name, folder, metal_default=0.0):
    """A principled material from the set's base colour and ORM (G roughness, B metallic), as M_<gun> reads them."""
    m = bpy.data.materials.new(mat_name + "_offline")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bc = small_texture(folder, "BC")
    orm = small_texture(folder, "ORM")
    if bc:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bc
        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    if orm:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = orm
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(t.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    else:
        bsdf.inputs["Metallic"].default_value = metal_default
        bsdf.inputs["Roughness"].default_value = 0.5
    return m


def skin_material():
    m = bpy.data.materials.new("Skin_offline")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bc = small_texture("RuleArms_Skin", "BC")
    if bc:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bc
        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.55
    bsdf.inputs["Metallic"].default_value = 0.0
    return m


def flat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (rgb[0], rgb[1], rgb[2], 1)
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs["Emission"], o.inputs["Surface"])
    return m


def set_material(objs, m_by_name):
    for o in objs:
        if o.type != "MESH":
            continue
        for i, slot in enumerate(o.material_slots):
            nm = slot.material.name if slot.material else ""
            slot.material = m_by_name(nm)


def tex_folder(mat_name):
    base = mat_name.split(".")[0]
    base = base[2:] if base.startswith("M_") else base
    return base if os.path.isdir(os.path.join(TEX, base)) else None


# ------------------------------------------------------------------------------------------------ the scene
class Scene:
    def __init__(self, gun_id, args):
        self.args = args
        self.gun = fm.Gun(gun_id)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        _tex_cache.clear()   # the images of the previous gun's scene are gone
        sc = bpy.context.scene
        sc.render.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.cycles.samples = args.samples
        sc.render.threads_mode = "FIXED"
        sc.render.threads = args.threads
        try:
            sc.cycles.use_denoising = True
        except Exception:
            pass
        sc.render.resolution_x = args.res
        sc.render.resolution_y = int(args.res * 9 / 16)
        sc.render.image_settings.file_format = "JPEG"
        sc.render.image_settings.quality = 85
        sc.view_settings.view_transform = "AgX" if "AgX" in [v.identifier for v in sc.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
        # the arms
        self.arms_root, objs = import_glb(os.path.join(fm.GLB, "SK_RuleArms.glb"), "Arms")
        self.arm = [o for o in objs if o.type == "ARMATURE"][0]
        self.arms_meshes = [o for o in objs if o.type == "MESH" and not o.hide_render]
        bpy.context.view_layer.update()
        names, parents, rest = [], {}, {}
        for b in self.arm.data.bones:
            names.append(b.name)
            parents[b.name] = b.parent.name if b.parent else None
            rest[b.name] = ue_from_bl_matrix(np.array(b.matrix_local))
        self.sk = fm.Skeleton(names, parents, rest)
        # the gun
        self.gun_root, gobjs = import_glb(self.gun.glb, "Gun")
        self.gun_meshes = [o for o in gobjs if o.type == "MESH" and not o.hide_render]
        garm = [o for o in gobjs if o.type == "ARMATURE"]
        self.garm = garm[0] if garm else None
        bpy.context.view_layer.update()
        self.sockets = {}
        if self.garm:
            for b in self.garm.data.bones:
                self.sockets[b.name] = D @ np.array(self.garm.matrix_world @ b.head_local) * 100.0
        # the magazine (UMIFirstPersonRig::Equip OwnMag: the magazine mesh in the gun's own space, riding the bone)
        self.mag_root, mobjs = (None, [])
        if self.gun.mag_glb and os.path.exists(self.gun.mag_glb):
            self.mag_root, mobjs = import_glb(self.gun.mag_glb, "Magazine")
        self.mag_meshes = [o for o in mobjs if o.type == "MESH" and not o.hide_render]
        # materials
        skin = skin_material()
        nail = flat("Nail_offline", (0.0, 0.0, 0.0))
        nail = textured("Nail", "RuleArms_Skin")
        set_material(self.arms_meshes, lambda nm: nail if "Nail" in nm else skin)
        cache = {}

        def gun_mat(nm):
            if nm not in cache:
                f = args.tex_set or tex_folder(nm)
                cache[nm] = textured(nm, f) if f else textured(nm, "", 0.6)
            return cache[nm]
        if args.finish == "zero":
            zero = bpy.data.materials.new("Zero_offline")
            zero.use_nodes = True
            b = zero.node_tree.nodes["Principled BSDF"]
            b.inputs["Base Color"].default_value = (0, 0, 0, 1)
            b.inputs["Roughness"].default_value = 0.0
            b.inputs["Metallic"].default_value = 0.0
            set_material(self.gun_meshes + self.mag_meshes, lambda nm: zero)
        else:
            set_material(self.gun_meshes + self.mag_meshes, gun_mat)
        self.beauty_mats = {o.name: [s.material for s in o.material_slots] for o in self.arms_meshes + self.gun_meshes + self.mag_meshes}
        # light: a sun from above, behind and left of the player, and a grey sky
        w = bpy.data.worlds.new("W")
        w.use_nodes = True
        w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.45, 0.5, 0.58, 1)
        w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
        sc.world = w
        if args.hdri:
            nt = w.node_tree
            env = nt.nodes.new("ShaderNodeTexEnvironment")
            env.image = bpy.data.images.load(args.hdri)
            nt.links.new(env.outputs["Color"], nt.nodes["Background"].inputs["Color"])
            nt.nodes["Background"].inputs["Strength"].default_value = 1.0
        sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
        sun.data.energy = 3.5
        sun.rotation_euler = (math.radians(50), math.radians(20), math.radians(-30))
        sc.collection.objects.link(sun)
        # the eye marker for the side views
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.012, location=(0, 0, 0))
        self.eye_marker = bpy.context.active_object
        self.eye_marker.data.materials.append(flat("EyeMark", (1.0, 0.05, 0.05)))
        # cameras
        self.cam_eye = self._camera("Eye")
        self.cam_side = self._camera("Side")

    def _camera(self, name):
        c = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        bpy.context.scene.collection.objects.link(c)
        c.data.sensor_fit = "VERTICAL"
        c.data.sensor_height = 24.0
        return c

    def place_eye(self, vfov):
        # camera space (UE X forward, Y right, Z up) -> Blender world (x, -y, z): forward +X, right -Y, up +Z
        R = np.column_stack([[0, -1, 0], [0, 0, 1], [-1, 0, 0]])
        M = np.eye(4)
        M[:3, :3] = R
        self.cam_eye.matrix_world = to_mat(M)
        self.cam_eye.data.lens = 12.0 / math.tan(math.radians(vfov) * 0.5)
        # FirstPersonScale 0.6 with the recipe's 1 cm near plane: nothing nearer than 1 / 0.6 cm is drawn
        self.cam_eye.data.clip_start = 0.01 / self.gun.fp.get("scale", 0.6)
        self.cam_eye.data.clip_end = 50.0

    def place_side(self, look_ue, from_ue, vfov=40.0):
        eye = bl_point(from_ue)
        tgt = bl_point(look_ue)
        f = tgt - eye
        f /= np.linalg.norm(f)
        up = np.array([0, 0, 1.0])
        r = np.cross(f, up)
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        M = np.eye(4)
        M[:3, :3] = np.column_stack([r, u, -f])
        M[:3, 3] = eye
        self.cam_side.matrix_world = to_mat(M)
        self.cam_side.data.lens = 12.0 / math.tan(math.radians(vfov) * 0.5)
        self.cam_side.data.clip_start = 0.005

    # -------------------------------------------------------------------------------------------- posing
    def pose(self, state, clip):
        g = self.gun
        F = fm.frame(g, state, self.sk, self.sockets, clip, ref_hip_rot=REF_HIP.get(g.id))
        self.F = F
        self.gun_root.matrix_world = to_mat(bl_from_ue_matrix(F["G"]))
        if self.mag_root is not None:
            self.mag_root.matrix_world = to_mat(bl_from_ue_matrix(F["MagW"]))
        # the gun's magazine bone dropped as PoseParts does (for a magazine skinned into the gun, if any)
        if self.garm and "magazine" in self.garm.pose.bones:
            m, drop = g.magazine_drop(state)
            pb = self.garm.pose.bones["magazine"]
            pb.location = (0, 0, 0)
            bpy.context.view_layer.update()
            arm_space = D @ drop / 100.0
            rest = np.array(pb.bone.matrix_local)
            tgt = rest.copy()
            tgt[:3, 3] += arm_space
            pb.matrix = to_mat(tgt)
        # the arms: the armature object at the eye world's origin; every bone's pose matrix from the computed world
        self.arms_root.matrix_world = to_mat(np.eye(4))
        self.arm.matrix_world = to_mat(np.eye(4))
        W = F["pose"].world()
        P = {n: bl_from_ue_matrix(W[n]) for n in self.sk.names}
        for b in self.arm.data.bones:
            Rb = np.array(b.matrix_local)
            if b.parent:
                Rp = np.array(b.parent.matrix_local)
                basis = np.linalg.inv(np.linalg.inv(Rp) @ Rb) @ np.linalg.inv(P[b.parent.name]) @ P[b.name]
            else:
                basis = np.linalg.inv(Rb) @ P[b.name]
            self.arm.pose.bones[b.name].matrix_basis = to_mat(basis)
        bpy.context.view_layer.update()
        return F

    # -------------------------------------------------------------------------------------------- rendering
    def render(self, cam, path, eye_marker=False):
        sc = bpy.context.scene
        sc.camera = cam
        self.eye_marker.hide_render = not eye_marker
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)

    def id_render(self, path, only=None):
        """A flat emission render of the eye's view: gun blue, magazine red, support arm green, firing arm yellow
        (the arms split by the vertex groups' sides), grip area cyan. Returns the pixel counts."""
        sc = bpy.context.scene
        saved = (sc.cycles.samples, sc.render.image_settings.file_format, sc.view_settings.view_transform, sc.render.filter_size,
                 getattr(sc.cycles, "use_denoising", False))
        sc.cycles.samples = 1
        sc.render.filter_size = 0.01
        sc.cycles.use_denoising = False
        sc.view_settings.view_transform = "Standard"
        sc.render.image_settings.file_format = "PNG"
        ids = {"gun": flat("ID_gun", (0, 0, 1)), "mag": flat("ID_mag", (1, 0, 0)), "l": flat("ID_l", (0, 1, 0)),
               "r": flat("ID_r", (1, 1, 0))}
        hidden = []
        for o in self.gun_meshes:
            for s in o.material_slots:
                s.material = ids["gun"]
        for o in self.mag_meshes:
            for s in o.material_slots:
                s.material = ids["mag"]
        # the arms mesh: split into left / right by a material index per face from the deform weights
        for o in self.arms_meshes:
            self._side_materials(o, ids)
        for o in self.gun_meshes + self.mag_meshes + self.arms_meshes:
            if only is not None and o not in only:
                o.hide_render = True
                hidden.append(o)
        w = sc.world
        sc.world = None
        self.eye_marker.hide_render = True
        sc.camera = self.cam_eye
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        sc.world = w
        for o in hidden:
            o.hide_render = False
        # restore
        for o in self.gun_meshes + self.mag_meshes + self.arms_meshes:
            if o.name in self._split_backup:
                self._restore_side(o)
            for s, m in zip(o.material_slots, self.beauty_mats[o.name]):
                s.material = m
        (sc.cycles.samples, sc.render.image_settings.file_format, sc.view_settings.view_transform, sc.render.filter_size,
         sc.cycles.use_denoising) = saved
        sc.render.image_settings.file_format = "JPEG"
        from PIL import Image
        a = np.asarray(Image.open(path).convert("RGB")).astype(int)
        r, g, b = a[..., 0] > 128, a[..., 1] > 128, a[..., 2] > 128
        return {"gun": int((b & ~r & ~g).sum()), "mag": int((r & ~g & ~b).sum()), "l": int((g & ~r & ~b).sum()),
                "r": int((r & g & ~b).sum()), "px": int(a.shape[0] * a.shape[1]), "mask": a}

    _split_backup = {}

    def _side_materials(self, o, ids):
        """Two slots on the arms mesh: faces whose vertices lean on _l bones -> green, _r -> yellow."""
        me = o.data
        self._split_backup[o.name] = ([s.material for s in o.material_slots], [p.material_index for p in me.polygons])
        while len(o.material_slots) < 2:
            o.data.materials.append(None)
        o.material_slots[0].material = ids["l"]
        o.material_slots[1].material = ids["r"]
        gname = {g.index: g.name for g in o.vertex_groups}
        side = np.zeros(len(me.vertices))
        for v in me.vertices:
            s = 0.0
            for ge in v.groups:
                n = gname.get(ge.group, "")
                if n.endswith("_l"):
                    s -= ge.weight
                elif n.endswith("_r"):
                    s += ge.weight
            side[v.index] = s
        for p in me.polygons:
            p.material_index = 1 if np.mean([side[i] for i in p.vertices]) > 0 else 0

    def _restore_side(self, o):
        mats, idx = self._split_backup.pop(o.name)
        for p, i in zip(o.data.polygons, idx):
            p.material_index = i
        while len(o.data.materials) > len(mats):
            o.data.materials.pop()


REF_HIP = {}
OUT_TEX = ""


def parse_state(s):
    return ("reload", float(s[1:])) if s.startswith("r") else s


def main():
    global OUT_TEX
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--guns", default="chopper,shorty,stretch,rattler,nine")
    ap.add_argument("--states", default="hip,aim,r0.5,r1.1")
    ap.add_argument("--cams", default="eye,side,left")
    ap.add_argument("--res", type=int, default=640)
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--threads", type=int, default=3)
    ap.add_argument("--out", default=os.path.join(fm.ROOT, "art", "out", "fp-offline"))   # art/out is git-ignored
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--no-id", action="store_true")
    ap.add_argument("--blade", type=float, default=CLIP_DEFAULT["blade"])
    ap.add_argument("--pole-l", default=",".join(str(x) for x in CLIP_DEFAULT["pole_l"]))
    ap.add_argument("--pole-r", default=",".join(str(x) for x in CLIP_DEFAULT["pole_r"]))
    ap.add_argument("--shoulder-l", default=",".join(str(x) for x in CLIP_DEFAULT["shoulder_l"]),
                    help="the clip's left shoulder from the midpoint, camera cm at the CHOPPER hip; 'rest' for the rest skeleton")
    ap.add_argument("--shoulders", default=None, help="what-if: the anim set's shoulders (camera cm) for every gun drawn")
    ap.add_argument("--relief", type=float, default=None, help="what-if: the gun's eye relief (m) for every gun drawn")
    ap.add_argument("--patch-reach", action="store_true", help="what-if: the C++ patch's firing reach guard (docs/unreal/patches/hands-offline)")
    ap.add_argument("--elbow-out", default=None, help="what-if: supportElbowOut (camera cm) for every gun drawn")
    ap.add_argument("--elbow-out-aim", default=None, help="what-if: supportElbowOutAim (camera cm) for every gun drawn")
    ap.add_argument("--finish", default="textured", choices=("textured", "zero"),
                    help="what-if: 'zero' samples every gun texture as 0 (base colour black, roughness 0, metallic 0)")
    ap.add_argument("--tex-set", default=None, help="what-if: every gun material samples this texture set (art/out/textures/<set>)")
    ap.add_argument("--hdri", default=None, help="light by an equirectangular HDRI (art/out/hdri/...) instead of the grey sky")
    ap.add_argument("--tag", default="", help="appended to every file name and report key (what-if runs)")
    a = ap.parse_args(argv)
    fm.FIRING_REACH_GUARD = a.patch_reach
    os.makedirs(a.out, exist_ok=True)
    OUT_TEX = os.path.join(a.out, "tex")
    os.makedirs(OUT_TEX, exist_ok=True)
    clip = fm.ClipModel(a.blade, [float(x) for x in a.pole_l.split(",")], [float(x) for x in a.pole_r.split(",")], 0.0,
                        None if a.shoulder_l == "rest" else [float(x) for x in a.shoulder_l.split(",")])
    # the clip's hand is the same in every rifle set (one idle clip): the arms' turn is referred to the CHOPPER's hip
    REF_HIP.update({g: fm.Gun("chopper").gun_matrix("hip")[:3, :3] for g in ("chopper", "shorty", "stretch", "rattler")})
    rifle_clip = clip
    rep_path = os.path.join(a.out, "report.json")
    report = json.load(open(rep_path)) if os.path.exists(rep_path) else {}
    for gid in a.guns.split(","):
        S = Scene(gid, a)
        if a.shoulders:
            S.gun.shoulders = np.array([float(x) for x in a.shoulders.split(",")])
        if a.relief is not None:
            S.gun.relief = a.relief
        if a.elbow_out:
            S.gun.elbow_out = np.array([float(x) for x in a.elbow_out.split(",")])
            S.gun.elbow_out_aim = S.gun.elbow_out.copy()
        if a.elbow_out_aim:
            S.gun.elbow_out_aim = np.array([float(x) for x in a.elbow_out_aim.split(",")])
        # the NINE plays the template pistol idle, not the pack's rifle idle: the rifle fit does not apply to it, so its
        # shoulders are the rest skeleton's (level, 38 cm apart) turned with the gun
        clip = fm.ClipModel(clip.blade_deg, clip.pole_l, clip.pole_r, 0.0, None) if S.gun.set.get("grip", {}).get("gun") == "nine" else rifle_clip
        for st in a.states.split(","):
            state = parse_state(st)
            F = S.pose(state, clip)
            S.place_eye(S.gun.fov_v(state))
            R = F["reports"]
            G = F["G"]
            sockets_cam = {k: fm.xp(G, v).round(2).tolist() for k, v in S.sockets.items() if k in ("Palm_L", "Palm_R", "SightRear", "SightFront", "Muzzle", "magazine")}
            entry = {"state": st, "fov_v": S.gun.fov_v(state), "mag_drop": round(F["mag_drop"], 3), "mag_hold": round(F["mag_k"], 3),
                     "sockets_cam_cm": sockets_cam, "clip": {"blade": clip.blade_deg, "pole_l": clip.pole_l.tolist(), "pole_r": clip.pole_r.tolist(),
                              "shoulder_l": None if clip.shoulder_l is None else clip.shoulder_l.tolist()}}
            for side in ("l", "r"):
                r = R[side]
                pose = F["pose"]
                hand = pose.P("hand_" + side)
                palm = pose.P("middle_metacarpal_" + side)
                tips = {f: pose.P("%s_03_%s" % (f, side)) for f in fm.FINGERS}
                entry[side] = {"reached": r["reached"], "wrist_gap_cm": round(r["gap_cm"], 2), "elbow_bend_deg": round(r["bend_deg"], 1),
                               "shoulder_cam": r["shoulder"].round(1).tolist(), "elbow_cam": r["elbow"].round(1).tolist(),
                               "wrist_cam": hand.round(1).tolist(), "palm_cam": palm.round(1).tolist(),
                               "palm_from_eye_cm": round(float(np.linalg.norm(palm)), 1),
                               "nearest_joint_from_eye_cm": round(float(min(np.linalg.norm(pose.P(n)) for n in pose.sk.names if n.endswith("_" + side) and ("hand" in n or any(f in n for f in fm.FINGERS)))), 1)}
                if side == "l":
                    entry[side]["forearm_slope_deg"] = round(R["l"]["slope_deg"], 1)
                # shape fidelity: the posed joints against the solved points (cm)
                sh = r["shape"]
                errs = [float(np.linalg.norm(pose.P(n) - sh[n])) for n in sh if n in pose.sk.parent]
                entry[side]["shape_err_cm_max"] = round(max(errs), 2) if errs else None
            # the magazine against the eye
            if S.mag_meshes:
                mw = F["MagW"]
                vs = []
                for o in S.mag_meshes:
                    M = np.array(o.matrix_world)
                    co = np.empty(len(o.data.vertices) * 3)
                    o.data.vertices.foreach_get("co", co)
                    co = np.c_[co.reshape(-1, 3), np.ones(len(o.data.vertices))]
                    vs.extend(((M @ co.T).T[:, :3] @ D) * 100.0)
                vs = np.array(vs)
                entry["mag_nearest_from_eye_cm"] = round(float(np.linalg.norm(vs, axis=1).min()), 1)
                entry["mag_centre_cam"] = vs.mean(0).round(1).tolist()
            tag = "%s-%s%s" % (gid, st.replace(".", ""), a.tag)
            # the gun against the eye: its nearest vertex and how far behind the eye its rearmost one lies (camera X)
            gv = []
            for o in S.gun_meshes:
                co = np.empty(len(o.data.vertices) * 3)
                o.data.vertices.foreach_get("co", co)
                co = np.c_[co.reshape(-1, 3), np.ones(len(o.data.vertices))]
                gv.append(((np.array(o.matrix_world) @ co.T).T[:, :3] @ D) * 100.0)
            gv = np.vstack(gv)
            entry["gun_nearest_from_eye_cm"] = round(float(np.linalg.norm(gv, axis=1).min()), 1)
            entry["gun_rear_x_cm"] = round(float(gv[:, 0].min()), 1)
            if a.shoulders or a.relief is not None:
                entry["what_if"] = {"shoulders": a.shoulders, "relief": a.relief}
            if not a.no_id:
                full = S.id_render(os.path.join(a.out, tag + "-id.png"))
                ids = {k: v for k, v in full.items() if k != "mask"}
                if S.mag_meshes:
                    # the magazine with the gun but no arms: what only the hands hide is the difference
                    alone = S.id_render(os.path.join(a.out, tag + "-id-mag.png"), only=S.mag_meshes + S.gun_meshes)
                    ids["mag_alone"] = alone["mag"]
                    ids["mag_visible_frac"] = round(full["mag"] / alone["mag"], 3) if alone["mag"] else None
                ids["l_frac_of_frame"] = round(full["l"] / full["px"], 3)
                ids["r_frac_of_frame"] = round(full["r"] / full["px"], 3)
                entry["id"] = ids
            report["%s-%s%s" % (gid, st, a.tag)] = entry
            print("FRAME", tag, json.dumps({k: entry[k] for k in ("l", "r") if k in entry}))
            if not a.report_only:
                for cam in a.cams.split(","):
                    look = (fm.xp(G, S.sockets.get("Palm_R", np.zeros(3))) + R["l"]["wrist"]) * 0.5
                    if cam == "eye":
                        S.render(S.cam_eye, os.path.join(a.out, tag + "-eye.jpg"))
                    elif cam == "side":
                        # beside the player on the right, level with the hands: the firing hand against the grip
                        S.place_side(look, look + np.array([-5.0, 75.0, 8.0]), 40.0)
                        S.render(S.cam_side, os.path.join(a.out, tag + "-side.jpg"), eye_marker=True)
                    elif cam == "grip":
                        # the firing hand on the pistol grip from the gun's left, level with it: thumb, index, closure
                        pr = fm.xp(G, S.sockets.get("Palm_R", np.zeros(3)))
                        S.place_side(pr, pr + G[:3, :3] @ np.array([4.0, -38.0, 6.0]), 30.0)
                        S.render(S.cam_side, os.path.join(a.out, tag + "-grip.jpg"), eye_marker=False)
                    elif cam in ("gripr", "gripu"):
                        # the same from the gun's right, or from above and behind (the thumb over the web)
                        pr = fm.xp(G, S.sockets.get("Palm_R", np.zeros(3)))
                        off = np.array([4.0, 38.0, 6.0]) if cam == "gripr" else np.array([-22.0, 10.0, 30.0])
                        S.place_side(pr, pr + G[:3, :3] @ off, 30.0)
                        S.render(S.cam_side, os.path.join(a.out, tag + "-" + cam + ".jpg"), eye_marker=False)
                    elif cam == "left":
                        # above and left of the hands, over the support arm: the support hand against the magazine
                        S.place_side(look, look + np.array([5.0, -50.0, 55.0]), 40.0)
                        S.render(S.cam_side, os.path.join(a.out, tag + "-left.jpg"), eye_marker=True)
            json.dump(report, open(rep_path, "w"), indent=1)


# calibrate.py's fit to the development log of HANDS_R4.md 9.3 (eight support-elbow bends: rms 4.4 deg; sixteen forearm
# slopes: rms 9.5 deg). The right elbow's pole has no log to fit: down and out to the right, as the left one.
CLIP_DEFAULT = {"blade": 0.0, "pole_l": (0.0, 1.57, -7.84), "pole_r": (0.0, 3.0, -7.84), "shoulder_l": (25.5, 3.0, -9.0)}

if __name__ == "__main__":
    main()
