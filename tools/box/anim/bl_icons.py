"""White-on-transparent silhouettes of the pack rifles and parts (bpy on the box; the PNGs never leave the box).

    /opt/blpy/bin/python -I tools/box/anim/bl_icons.py <pack FBX root> <out dir>

T_UI_Gun_{Shorty,Stick,Stretch}.png: 512 x 192, the right side of the length's Combined rifle (irons standing) with the
standard magazine, muzzle to the right, one common scale (0.98 m across) and one common receiver position, so the
three lengths read as lengths on the rack. T_UI_Att_<id>.png: 128 x 128 pips, each part alone, fitted.
Workbench renderer, flat lighting, single white colour, transparent film: the alpha is the silhouette.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT, OUT = sys.argv[1:3]
os.makedirs(OUT, exist_ok=True)
GUNS = {"Shorty": "Short", "Stick": "Default", "Stretch": "Extended"}
PARTS = {"irons": ["SM_TFA_AR_ATT_Sight_Rear", "SM_TFA_AR_ATT_Sight_Front"], "scope": ["SM_TFA_AR_ATT_Scope"],
         "silencer": ["SM_TFA_AR_ATT_Silencer"], "grip_vertical": ["SM_TFA_AR_ATT_Grip_Vertical"],
         "grip_angled": ["SM_TFA_AR_ATT_Grip_Angled"], "laser": ["SM_TFA_AR_ATT_Laser"],
         "mag_standard": ["SM_TFA_AR_Magazine_Full"], "mag_clear": ["SM_TFA_AR_Magazine_Transparent_Full"]}
MAG_AT = (0.00007, -0.12265, -0.07021)        # the rifle's Magazine bone, Blender metres (Unreal (x, -y, z) / 100)


def scene(w, h):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "FLAT"
    sc.display.shading.color_type = "SINGLE"
    sc.display.shading.single_color = (1.0, 1.0, 1.0)
    sc.display.render_aa = "32"
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    return sc


def load(name, at=(0, 0, 0)):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(ROOT, "Meshes", name + ".fbx"))
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.parent is None:
            o.location = Vector(at)
    return [o for o in new if o.type == "MESH"]


def bounds(objs):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def camera(sc, centre, ortho):
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ortho
    # on the gun's right (Blender -X), looking +X: screen right is Blender -Y, the muzzle
    cam.location = Vector((centre[0] - 2.0, centre[1], centre[2]))
    cam.rotation_euler = (math.radians(90), 0.0, math.radians(-90))
    sc.camera = cam


def render(sc, path):
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("ICON", path, flush=True)


for ui, L in GUNS.items():
    sc = scene(512, 192)
    objs = load("SK_TFA_AR_%s_Combined" % L) + load("SM_TFA_AR_Magazine_Full", MAG_AT)
    # common frame for the three lengths: Unreal gun y -27.5 .. 64.0, centre 18.2 cm; z centre -3 cm
    camera(sc, (0.0, -0.182 - 0.004, -0.03), 0.98)
    render(sc, os.path.join(OUT, "T_UI_Gun_%s.png" % ui))

for pid, names in PARTS.items():
    sc = scene(128, 128)
    objs = []
    for i, n in enumerate(names):
        objs += load(n, (0.0, -0.06 * i, 0.0))      # the irons: rear and front side by side
    lo, hi = bounds(objs)
    c = (lo + hi) / 2
    size = max(hi[1] - lo[1], hi[2] - lo[2]) * 1.12
    camera(sc, c, size)
    render(sc, os.path.join(OUT, "T_UI_Att_%s.png" % pid))
print("BL-ICONS-DONE")
