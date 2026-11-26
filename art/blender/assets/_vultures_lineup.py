"""The two Vulture crews side by side (review F6: do the levels' crews read as different crews at night?).

    venv/bin/python art/blender/assets/_vultures_lineup.py [--samples 32]

Imports the six exported GLBs (art/out/glb/SK_Vulture_*.glb) on their skeletons in the reference pose, puts the
textured set on each (vultures.set_material), the Canal crew on the left and the Roof crew on the right, and
renders four panels into art/previews/characters/maps/vultures_crews.jpg:

1. studio light, front, the six as built;
2. street night (a sodium lamp and a sign light, the preview rig), about 15 m away;
3. silhouettes from the front (black figures on grey: what a player reads at 25 m in the dark);
4. silhouettes in profile (each figure turned 90 degrees: the hoods of the Canal crew against the close caps and
   balaclava of the Roof crew).

It also writes the head outline numbers to art/out/characters/maps/vultures_crews.json: per figure, the depth and
width of the head gear over the top 18 cm and how far it reaches in front of the face, which is what tells a hood
from a cap.
"""
import json
import math
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402

from mi import mat, paths, render  # noqa: E402
from assets import vultures as V  # noqa: E402

ORDER = ["canal_shell", "canal_bomber", "canal_lieutenant", "roof_rigger", "roof_lookout", "roof_lieutenant"]
X = [-3.4, -2.3, -1.2, 1.2, 2.3, 3.4]


def load(cid):
    asset = V.ROSTER[cid][0]
    path = os.path.join(paths.glb, asset + ".glb")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH" and len(o.vertex_groups)]
    drop = [o.name for o in new if o.type == "MESH" and o not in meshes]     # the importer's bone-shape sphere
    keep = [o.name for o in new if o.name not in drop]
    for nm in drop:
        bpy.data.objects.remove(bpy.data.objects[nm], do_unlink=True)
    roots = [bpy.data.objects[nm] for nm in keep if bpy.data.objects[nm].parent is None]
    m = V.set_material("M_" + asset[3:], V._set_name(asset))
    for o in meshes:
        o.data.materials.clear()
        o.data.materials.append(m)
    return roots, meshes


def head_numbers(meshes):
    co = np.vstack([np.array([o.matrix_world @ v.co for v in o.data.vertices]) for o in meshes])
    top = co[:, 2].max()
    h = co[co[:, 2] > top - 0.18]
    face = co[(co[:, 2] > top - 0.30) & (co[:, 2] < top - 0.12)]
    return {"top_m": round(float(top), 3), "head_gear_width_m": round(float(np.ptp(h[:, 0])), 3),
            "head_gear_depth_m": round(float(np.ptp(h[:, 1])), 3),
            "gear_front_of_face_m": round(float(face[:, 1].min() - h[:, 1].min()), 3)}


def main():
    samples = int(sys.argv[sys.argv.index("--samples") + 1]) if "--samples" in sys.argv else 32
    bpy.ops.wm.read_factory_settings(use_empty=True)
    render.setup(samples=samples, threads=3)
    ground = render.backdrop(size=60.0, color=(0.05, 0.05, 0.055), z=0.0)
    figs, nums = [], {}
    for cid, x in zip(ORDER, X):
        roots, meshes = load(cid)
        for r in roots:
            r.location.x += x
        bpy.context.view_layer.update()
        nums[cid] = head_numbers(meshes)
        figs.append((cid, roots, meshes))
    tmp = tempfile.mkdtemp(prefix="vult_crews_")
    shots = []
    render.rig_day(sun_azimuth=215.0, stops=0.4)
    render.cam_look((0.0, -17.0, 1.3), (0.0, 0.0, 0.95), lens=70, name="Cam_Crews")
    p = os.path.join(tmp, "studio.png")
    render.render_png(p, samples, (1280, 400))
    shots.append(p)
    render.rig_night(lamp=(0.0, -4.0, 6.0), lamp_target=(0.0, 0.0, 1.0), lamp_watts=2600.0, sign=(0.0, -5.0, 3.0),
                     sign_color=(0.25, 0.85, 0.55), sign_watts=500.0, sign_target=(0.0, 0.0, 1.0))
    render.cam_look((0.0, -15.0, 1.6), (0.0, 0.0, 0.95), lens=62, name="Cam_Crews")
    p = os.path.join(tmp, "night.png")
    render.render_png(p, samples, (1280, 400))
    shots.append(p)
    # silhouettes: black figures, grey world, no ground
    black = mat.flat("Silhouette", (0.0, 0.0, 0.0), 1.0)
    for _cid, _r, meshes in figs:
        for o in meshes:
            o.data.materials.clear()
            o.data.materials.append(black)
    ground.hide_render = True
    render.rig_day(sun_azimuth=215.0, stops=0.4)
    w = bpy.context.scene.world
    w.use_nodes = True
    nt = w.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.35, 0.35, 0.35, 1.0)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    for o in bpy.data.objects:
        if o.type == "LIGHT":
            o.hide_render = True
    render.cam_look((0.0, -17.0, 1.3), (0.0, 0.0, 0.95), lens=70, name="Cam_Crews")
    p = os.path.join(tmp, "sil_front.png")
    render.render_png(p, 8, (1280, 400))
    shots.append(p)
    for (_cid, roots, _m), x in zip(figs, X):
        for r in roots:                       # the glTF importer's roots rotate by quaternion
            r.rotation_mode = "XYZ"
            r.rotation_euler.z += math.radians(90)
    bpy.context.view_layer.update()
    p = os.path.join(tmp, "sil_side.png")
    render.render_png(p, 8, (1280, 400))
    shots.append(p)
    out = os.path.join(V.PREV, "vultures_crews.jpg")
    render.contact_sheet(shots, out, cols=1, size=(1280, 1612),
                         labels=["studio: Canal crew (left: shell, bomber, lieutenant) | Roof crew (right: rigger, "
                                 "lookout, lieutenant)", "street night, about 15 m", "silhouettes, front",
                                 "silhouettes, profile"])
    with open(os.path.join(V.SRC, "vultures_crews.json"), "w") as f:
        json.dump(nums, f, indent=1)
    print("wrote", out)
    for k, v in nums.items():
        print(k, v)


if __name__ == "__main__":
    main()
