"""Review round 3 of the exported vehicle GLBs: one render per process (memory), sheets and arm's-length close-ups.

Reuses the round-1 loader, materials, ground and measuring (vehicles_review.py); this file adds the IPX door
hinges where the manifest now puts them (x -3.26), close-up anchors measured from the geometry (front wheel,
front-right lamp, right mirror, left driver glass) and a per-view entry point so each Blender process renders once.

    python art/blender/review/vehicles_review_r3.py --measure Sedan          # measure.json + anchors, no render
    python art/blender/review/vehicles_review_r3.py --view Sedan 0           # one sheet cell (0..3) to _tmp
    python art/blender/review/vehicles_review_r3.py --compose Sedan          # 2 x 2 sheet from the four cells
    python art/blender/review/vehicles_review_r3.py --close Sedan wheel      # wheel | lamp | door | interior
    python art/blender/review/vehicles_review_r3.py --close Sedan custom --cam x,y,z --target x,y,z --lens 35

Outputs in art/blender/review/sheets/vehicles_r3/: review_<Name>.jpg (1280 x 720), close_<Name>_<tag>.jpg
(1280 x 720), measure.json.
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import vehicles_review as R  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402

from mi import paths, render, scene as _scene  # noqa: E402

OUT = os.path.join(HERE, "sheets", "vehicles_r3")
TMP = os.path.join(OUT, "_tmp")
MEAS = os.path.join(OUT, "measure.json")
IPX_HINGE_X = -3.26          # manifest notes of SM_Vehicle_IPXTruck_Door(_Left)
VULTURE_HINGE_X = -2.53

_resolve0 = R.resolve


def _resolve(rec, man):
    """The stripped car's primer record carries its colour as 'tint' (no 'paint_default'): honour it, matte."""
    r = _resolve0(rec, man)
    if "tint" in r and "paint_default" not in r:
        r = dict(r, paint_default=list(r["tint"]), matte=True)
    return r


R.resolve = _resolve


def load_vehicle(name, man):
    obs = R.import_glb(os.path.join(paths.glb, "SM_Vehicle_%s.glb" % name), man)
    if name == "IPXTruck":
        for nm, hinge, ang in (("IPXTruck_Door", (IPX_HINGE_X, -0.89, 1.05), 108.9),
                               ("IPXTruck_Door_Left", (IPX_HINGE_X, 0.89, 1.05), -108.9)):
            d = R.import_glb(os.path.join(paths.glb, "SM_Vehicle_%s.glb" % nm), man)
            for o in d:
                o.location = hinge
                o.rotation_mode = "XYZ"
                o.rotation_euler = (0, 0, math.radians(ang))
            obs += d
    bpy.context.view_layer.update()
    return obs


def anchors(ob):
    """Close-up anchor points from the geometry (world space, nose at +X assumed and checked by lamps)."""
    co, tris, pm, ls, lt, lv = R.mesh_arrays(ob)
    lo, hi = co.min(0), co.max(0)
    a = {}
    wp = R.slot_verts(ob, co, pm, ls, lt, lv, lambda n: any(k in n for k in R.WHEEL_SLOTS))
    wh = R.clusters_x(wp)
    if wh:
        w = wh[-1]
        a["wheel"] = [w["x"], float(lo[1]), w["dia_z"] / 2 + w["zmin"]]
        a["wheel_dia"] = w["dia_z"]
    lp = R.slot_verts(ob, co, pm, ls, lt, lv, lambda n: n.endswith("_Lamp"))
    if len(lp):
        f = lp[(lp[:, 0] > hi[0] - 0.6) & (lp[:, 1] < 0)]
        if len(f):
            a["lamp"] = [float(f[:, 0].max()), float(np.median(f[:, 1])), float(np.median(f[:, 2]))]
    gp = R.slot_verts(ob, co, pm, ls, lt, lv, lambda n: "Glass" in n)
    body = co[(co[:, 2] > 0.75)]
    # the mirror: outermost points on the -Y side above the belt in the front half
    fr = body[(body[:, 0] > (lo[0] + hi[0]) / 2 - 0.3) & (body[:, 1] < 0)]
    if len(fr):
        ymin = fr[:, 1].min()
        mm = fr[fr[:, 1] < ymin + 0.03]
        a["mirror"] = [float(np.median(mm[:, 0])), float(ymin), float(np.median(mm[:, 2]))]
    if len(gp):
        g = gp[(gp[:, 1] > 0.3 * hi[1])]
        if len(g):
            xs = g[:, 0]
            xf = xs.max()
            gf = g[g[:, 0] > xf - 0.9]            # driver door glass (front-most side glass on +Y)
            a["driver_glass"] = [float(np.median(gf[:, 0])), float(gf[:, 1].max()), float(np.median(gf[:, 2]))]
    return a


def do_measure(name, man, br):
    _scene.reset(threads=3, samples=8)
    obs = load_vehicle(name, man)
    m = R.measure(name, obs, man, br.get("SM_Vehicle_" + name, {}))
    m["anchors"] = anchors(obs[0])
    m["objects"] = [o.name for o in obs]
    res = {}
    if os.path.exists(MEAS):
        with open(MEAS) as fh:
            res = json.load(fh)
    res[name] = m
    os.makedirs(OUT, exist_ok=True)
    with open(MEAS, "w") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps(m))


def shots_for(name, obs):
    lo, hi = render._bounds(obs)
    c = (lo + hi) / 2
    L = hi[0] - lo[0]
    shots = []
    for tag, d in (("front 3/4", (1.0, -0.9, 0.42)), ("rear 3/4", (-1.0, 0.9, 0.42))):
        shots.append((tag, ("hero", d), R.bearing(d[0], d[1]) + 40))
    dist = max(L, 2.0) * 1.15 / (2 * math.tan(math.atan(18 / 70)))
    shots.append(("side (right flank)", ("look", (c[0], lo[1] - dist, max(0.9, c[2])), (c[0], 0, c[2]), 70), 200.0))
    if name in ("Van_Vulture", "IPXTruck"):
        hx = VULTURE_HINGE_X if name == "Van_Vulture" else IPX_HINGE_X
        shots.append(("eye 1.65 m, 2 m behind tail", ("eye", (hx - 2.0, 0.35), (hx + 2.0, 0.0), 1.2, 22), 290.0))
    else:
        ey = hi[1] + 2.0
        shots.append(("eye 1.65 m, 2 m off left flank",
                      ("eye", (c[0] + 0.25 * L, ey), (c[0] + 0.05 * L, 0.0), 0.7, 22), 20.0))
    return shots


def do_view(name, i, man, samples):
    _scene.reset(threads=3, samples=samples)
    render.setup(samples, res=(640, 360), threads=3)
    obs = load_vehicle(name, man)
    R.ground()
    tag, spec, sb = shots_for(name, obs)[i]
    if spec[0] == "hero":
        cam = render.cam_hero(obs, direction=spec[1], lens=50, margin=0.72)
    elif spec[0] == "look":
        cam = render.cam_look(spec[1], spec[2], lens=spec[3], name="Cam_Side")
    else:
        cam = render.cam_eye(spec[1], spec[2], height=1.65, look_height=spec[3], lens=spec[4])
    os.makedirs(TMP, exist_ok=True)
    p = os.path.join(TMP, "%s_%d.jpg" % (name, i))
    R.view(p, cam, sb % 360, samples)
    print("VIEW", p)


def do_compose(name, man):
    labels = ["%s  front 3/4" % name, "rear 3/4", "side (right flank)",
              "eye 1.65 m, 2 m behind tail" if name in ("Van_Vulture", "IPXTruck") else "eye 1.65 m, 2 m off left flank"]
    imgs = [os.path.join(TMP, "%s_%d.jpg" % (name, i)) for i in range(4)]
    out = os.path.join(OUT, "review_%s.jpg" % name)
    render.contact_sheet(imgs, out, cols=2, labels=labels, size=(1280, 720), max_kb=300)
    print("SHEET", out)


def close_cam(name, tag, a):
    """Arm's-length cameras (0.5 to 1.0 m from the surface) on the anchors."""
    if tag == "wheel":
        x, y, z = a["wheel"]
        d = a.get("wheel_dia", 0.7)
        return (x + 0.55, y - 0.95, z + 0.45), (x - 0.05, y + 0.15, z + 0.05), 30, 230.0
    if tag == "lamp":
        x, y, z = a["lamp"]
        return (x + 0.62, y - 0.42, z + 0.28), (x - 0.02, y * 0.55, z - 0.02), 32, 200.0
    if tag == "door":
        x, y, z = a["mirror"]
        t = (x - 0.30, y + 0.06, z - 0.22)
        return (t[0] + 0.55, t[1] - 0.75, t[2] + 0.30), t, 28, 200.0
    if tag == "interior":
        x, y, z = a["driver_glass"]
        cz = min(z + 0.30, 1.85)
        return (x - 0.15, y + 0.55, cz), (x - 0.05, y - 0.80, z - 0.30), 24, 20.0
    raise ValueError(tag)


# anchors the slot rules cannot find: wrecks have no wheel, lamp or glass slots (rims and hubs measured from the
# ground contacts), the SUV's front-most +Y "glass" is its headlamp lens, the motorbike's front wheel is in Trim
ANCHOR_FIX = {
    "BurnedCar": {"wheel": [1.349, -0.86, 0.30], "lamp": [2.15, -0.58, 0.60], "driver_glass": [0.35, 0.86, 1.02]},
    "StrippedCar": {"wheel": [1.349, -0.86, 0.47], "lamp": [2.15, -0.58, 0.80], "driver_glass": [0.35, 0.86, 1.30]},
    "SUV": {"driver_glass": [0.20, 0.94, 1.45]},
    "Motorbike": {"wheel": [0.69, -0.31, 0.31]},
}


def do_close(name, tag, man, samples, cam=None, target=None, lens=35.0, sun=200.0):
    with open(MEAS) as fh:
        a = json.load(fh)[name]["anchors"]
    a.update(ANCHOR_FIX.get(name, {}))
    if cam is None:
        cam, target, lens, sun = close_cam(name, tag, a)
    _scene.reset(threads=3, samples=samples)
    render.setup(samples, res=(1280, 720), threads=3)
    load_vehicle(name, man)
    R.ground()
    c = render.cam_look(cam, target, lens=lens, name="Cam_Close")
    render.rig_day(sun_azimuth=sun)
    bpy.context.scene.camera = c
    out = os.path.join(OUT, "close_%s_%s.jpg" % (name, tag))
    render.render_jpeg(out, samples, res=(1280, 720), max_kb=300)
    print("CLOSE", out, cam, target, lens)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", default="")
    ap.add_argument("--view", nargs=2, default=None)
    ap.add_argument("--compose", default="")
    ap.add_argument("--close", nargs=2, default=None)
    ap.add_argument("--cam", default="")
    ap.add_argument("--target", default="")
    ap.add_argument("--lens", type=float, default=35.0)
    ap.add_argument("--sun", type=float, default=200.0)
    ap.add_argument("--samples", type=int, default=16)
    a = ap.parse_args(argv)
    man, br = R.manifest(), R.briefs()
    f = lambda s: tuple(float(x) for x in s.split(","))  # noqa: E731
    if a.measure:
        do_measure(a.measure, man, br)
    elif a.view:
        do_view(a.view[0], int(a.view[1]), man, a.samples)
    elif a.compose:
        do_compose(a.compose, man)
    elif a.close:
        if a.cam:
            do_close(a.close[0], a.close[1], man, a.samples, f(a.cam), f(a.target), a.lens, a.sun)
        else:
            do_close(a.close[0], a.close[1], man, a.samples)


if __name__ == "__main__":
    main()
