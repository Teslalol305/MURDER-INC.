#!/usr/bin/env python3
"""MURDER INC. art build.

    python art/blender/build.py list
    python art/blender/build.py build <family> [--bake] [--export] [--preview] [--res 2048] [--samples 96]
                                              [--fbx] [--force] [--only NAME[,NAME]] [--seed N]
    python art/blender/build.py sheet [--samples 48]          materials sheet -> art/previews/materials_sheet.jpg
    python art/blender/build.py tile <kind> <TS_Name> [--res 2048] [Param=value ...]   bake one tiling set

Runs with the bpy module (pip install bpy==5.3.0 numpy pillow) or inside Blender:

    blender -b -P art/blender/build.py -- build street --bake --export --preview

A family is a module art/blender/assets/<family>.py with FAMILY = {"name": ..., "description": ...} and
build(ctx) -> list of objects. Optional hooks: on_bake(ctx, objs), on_export(ctx, objs), on_preview(ctx, objs).
Without hooks, --export exports every returned object whose name starts with SM_ using the metadata set by
ctx.asset(...), and --preview renders one three-quarter view per asset into a contact sheet.
"""
import argparse
import importlib
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy  # noqa: E402

from mi import bake, export, geo, mat, paths, render, scene  # noqa: E402


class Ctx:
    """What a family's build(ctx) gets.

    ctx.args        the command line (bake, export, preview, res, samples, fbx, force, seed, only)
    ctx.col         the family's collection: link what you build there (scene.new_object(..., ctx.col))
    ctx.rng(*key)   seeded numpy Generator: same key and --seed, same numbers
    ctx.asset(ob, ...)      declare an exportable asset and its manifest metadata
    ctx.tiling_set(...)     bake (or reuse) a procedural tiling set and get its material
    ctx.scan_set(name)      material on a scanned tiling set from the catalogue (art/scans/sets.json)
    ctx.unique_set(ob)      bake (or reuse) the unique set of a prop and switch it to the baked material
    """

    def __init__(self, family, args):
        self.family = family
        self.args = args
        self.col = scene.collection(family.capitalize())
        self.assets = {}
        self.sets = []
        self.t0 = time.time()

    def rng(self, *key):
        return scene.rng(self.family, self.args.seed, *key)

    def log(self, msg):
        print("[%6.1fs] %s" % (time.time() - self.t0, msg), flush=True)

    def want(self, name):
        return not self.args.only or name in self.args.only

    def asset(self, ob, collision="box", cover_height=None, notes="", pivot=None, expect_size=None, slots=None):
        """Declare ob as an exportable asset. expect_size: (x, y, z) metres from the brief (None = any)."""
        self.assets[ob.name] = dict(ob=ob, collision=collision, cover_height=cover_height, notes=notes, pivot=pivot,
                                    expect_size=expect_size, slots=slots)
        geo.ensure_wear(ob)
        return ob

    def tiling_set(self, set_name, kind, tile_m=2.0, res=None, slot=None, blend=None, alpha=None, procedural=None,
                   mat_kw=None, **params):
        """Material for a tiling slot. With --bake (or when the set already exists) the set is baked and the
        material reads the textures, exactly as Unreal will; otherwise the procedural surface is used directly
        (slow to render, fine for a first look). slot: material name (default MI_<Surface>_<Variant>).
        blend: name of a second set to blend toward with the wear mask (G)."""
        slot = slot or "MI_" + set_name[3:]
        sf = mat.SURFACES[kind]
        alpha = alpha or sf.alpha
        d = paths.texture_set(set_name)
        use_proc = procedural if procedural is not None else False
        if self.args.bake and not use_proc:
            info = bake.bake_tiling_set(set_name, kind, tile_m, res or self.args.res, self.args.tile_samples,
                                        force=self.args.force, **params)
            if set_name not in self.sets:
                self.sets.append(set_name)
        if os.path.exists(os.path.join(d, "set.json")) and not use_proc:
            kw = dict(alpha=alpha, porosity=sf.porosity)
            if blend:
                kw["blend_tile_m"] = mat.scan_tile(blend)      # the partner keeps its own real tile size
            kw.update(mat_kw or {})
            m = mat.from_texture_set(d, name=slot, tile_m=tile_m, blend=paths.texture_set(blend) if blend else None, **kw)
            if set_name not in self.sets:
                self.sets.append(set_name)
        else:
            m = mat.make(slot, kind, tile_m=tile_m, alpha=alpha, **params)
        if blend:
            m["mi_blend_set"] = blend
        m["mi_alpha"] = alpha
        return m

    def scan_set(self, set_name, slot=None, blend=None, **mat_kw):
        """Material for a slot on a catalogued scan (art/scans/sets.json): textures from art/out/textures/<Set>/,
        real tile size from the catalogue (m["mi_tile_m"]). blend: second set name for the G channel.
        Keyword arguments go to mat.from_texture_set (alpha, tint, dirt_color, wear_tint, wear_metal ...)."""
        m = mat.from_scan(set_name, name=slot, blend=blend, **mat_kw)
        for s_ in (set_name, blend):
            if s_ and s_ not in self.sets:
                self.sets.append(s_)
        return m

    def unique_set(self, ob, res=None, ground=False, samples=4, set_name=None, meta=None):
        """Bake the object's procedural materials into its unique set and replace them by one M_<Asset>
        material that reads the baked textures. Without --bake an existing set is reused; if there is none the
        procedural materials stay (and the slot names will not pass export validation)."""
        set_name = set_name or ob.name.replace("SM_", "", 1)
        d = paths.texture_set(set_name)
        js = os.path.join(d, "set.json")
        old = bake.read_set(set_name)
        stale = bool(old) and (old.get("uv_hash") != geo.uv_hash(ob) or old.get("resolution", [0])[0] != (res or self.args.res))
        if self.args.bake and (self.args.force or not old or stale or self.args.rebake_unique):
            bake.bake_object(ob, set_name, res or self.args.res, samples, ground=ground, meta=meta)
            stale = False
        elif stale and old.get("uv_hash") != geo.uv_hash(ob):
            print("  WARNING %s: the mesh was re-unwrapped since its set was baked; run with --bake" % set_name)
        if os.path.exists(js):
            m = mat.from_texture_set(d, name="M_" + set_name, masks=False, macro=0.0, ao_strength=0.0, alpha="none")
            ob.data.materials.clear()
            ob.data.materials.append(m)
            if set_name not in self.sets:
                self.sets.append(set_name)
            return m
        return None


def _families():
    d = os.path.join(HERE, "assets")
    return sorted(f[:-3] for f in os.listdir(d) if f.endswith(".py") and not f.startswith("_"))


def _load(name):
    return importlib.import_module("assets." + name)


def cmd_list(args):
    for f in _families():
        try:
            m = _load(f)
            print("%-14s %s" % (m.FAMILY["name"], m.FAMILY["description"]))
        except Exception as e:  # a broken family must not hide the others
            print("%-14s (import failed: %s)" % (f, e))
    print("\nsurfaces: " + ", ".join(k for k, _d, _p in mat.library()))


def cmd_build(args):
    mod = _load(args.family)
    scene.reset(samples=args.samples)
    ctx = Ctx(mod.FAMILY["name"], args)
    ctx.log("build %s: %s" % (mod.FAMILY["name"], mod.FAMILY["description"]))
    objs = mod.build(ctx) or []
    ctx.log("built %d objects" % len(objs))
    if args.bake and hasattr(mod, "on_bake"):
        mod.on_bake(ctx, objs)
    if args.export:
        paths.ensure(paths.glb)
        if hasattr(mod, "on_export"):
            mod.on_export(ctx, objs)
        else:
            for name, a in ctx.assets.items():
                if ctx.want(name):
                    export.export_asset(a["ob"], ctx.family, a["collision"], a["cover_height"], a["notes"], a["pivot"],
                                        a["expect_size"], fbx=args.fbx, slots=a["slots"])
        export.write_manifest([], ctx.sets)
        ctx.log("manifest: %s" % paths.manifest)
    if args.preview:
        paths.ensure(paths.previews)
        if hasattr(mod, "on_preview"):
            mod.on_preview(ctx, objs)
        else:
            _default_preview(ctx, objs)
    out = os.path.join(paths.blend, mod.FAMILY["name"] + ".blend")
    scene.save_blend(out)
    ctx.log("saved %s" % out)


def _default_preview(ctx, objs):
    import tempfile
    shots, names = [], []
    render.setup(samples=ctx.args.samples, res=(640, 360))
    render.rig_day()
    render.backdrop()
    assets = [a["ob"] for a in ctx.assets.values()] or objs
    for ob in assets:
        for o in assets:
            o.hide_render = o is not ob
        render.cam_hero(ob)
        p = os.path.join(tempfile.gettempdir(), "mi_prev_%s.png" % ob.name)
        render.render_png(p, ctx.args.samples, (640, 360))
        shots.append(p)
        names.append(ob.name)
    for o in assets:
        o.hide_render = False
    out = os.path.join(paths.previews, "%s_sheet.jpg" % ctx.family)
    render.contact_sheet(shots, out, cols=max(1, min(4, len(shots))), labels=names)
    ctx.log("preview: %s" % out)


def cmd_sheet(args):
    """Every library surface on a 2 m plane and a sphere, labelled: art/previews/materials_sheet.jpg."""
    import tempfile
    import numpy as np
    kinds = [k for k, _d, _p in mat.library()]
    if args.only:
        kinds = [k for k in kinds if k in args.only]
    shots, labels = [], []
    cell = (424, 236) if len(kinds) <= 9 else (252, 236)
    cols = 3 if len(kinds) <= 9 else 5
    extra = [("road_paint", "road_paint (white)", {"Paint_Color": (0.62, 0.61, 0.58), "Paint_Wear": 0.5})] if not args.only else []
    todo = [(k, k, dict(mat.SURFACES[k].sample)) for k in kinds] + extra
    for kind, title, params in todo:
        t = time.time()
        scene.reset(samples=args.samples)
        render.setup(samples=args.samples, res=(cell[0] * 2, cell[1] * 2))
        render.rig_day(sun_elevation=42.0, sun_azimuth=215.0)
        render.backdrop(color=(0.07, 0.07, 0.07))
        xs = np.linspace(-1.0, 1.0, 81)
        pl = geo.heightfield(xs, xs, lambda X, Y: X * 0.0, name="Plane", tile_m=2.0)
        sp = geo.sphere(0.36, 96, 48, "Ball")
        geo.transform(sp, loc=(0.38, -0.34, 0.36))
        geo.uv_world_box(sp, 2.0)
        m = mat.make("MI_Sheet_" + kind, kind, tile_m=2.0, **params)
        for ob in (pl, sp):
            ob.data.materials.append(m)
            geo.ensure_wear(ob)
        # masks so the sheet shows the wear interface: plane dirt toward the back, wear to the left,
        # a leak down the ball and splash-back (or wetness) at its foot and at the front of the plane
        geo.paint(pl, "R", lambda x, y, z: np.clip((y - 0.25) * 1.3, 0, 1) * 0.9)
        geo.paint(pl, "G", lambda x, y, z: np.clip((-x - 0.2) * 1.2, 0, 1))
        geo.paint(pl, "B", lambda x, y, z: np.exp(-((x + 0.15) ** 2 + (y + 0.6) ** 2) / 0.02))
        geo.paint(pl, "A", lambda x, y, z: np.clip(1.0 - np.hypot(x - 0.38, y + 0.34) / 0.75, 0, 1) ** 0.6)
        geo.paint(sp, "R", lambda x, y, z: np.clip(0.75 - z * 1.2, 0, 1) * 0.5)
        geo.paint(sp, "G", lambda x, y, z: np.clip((z - 0.45) * 2.5, 0, 1) * 0.8)
        geo.paint(sp, "B", lambda x, y, z: np.exp(-((x - 0.2) ** 2) / 0.002) * np.clip((0.62 - z) * 4, 0, 1) * (y < -0.34))
        geo.paint(sp, "A", lambda x, y, z: np.clip(1.0 - z / 0.22, 0, 1))
        render.cam_look((1.75, -2.3, 1.25), (0.05, -0.1, 0.22), lens=42)
        p = os.path.join(tempfile.gettempdir(), "mi_sheet_%s.png" % title.replace(" ", "_"))
        render.render_png(p, args.samples, (cell[0] * 2, cell[1] * 2))
        shots.append(p)
        labels.append(title.replace("_", " "))
        print("  sheet %-22s %5.1fs" % (title, time.time() - t), flush=True)
    out = os.path.join(paths.previews, "materials_sheet.jpg" if not args.only else "materials_sheet_partial.jpg")
    render.contact_sheet(shots, out, cols=cols, labels=labels, label_size=13)
    print("wrote", out)


def cmd_tile(args):
    scene.reset()
    params = {}
    for kv in args.params:
        k, v = kv.split("=", 1)
        try:
            params[k] = float(v)
        except ValueError:
            params[k] = tuple(float(x) for x in v.strip("()").split(","))
    info = bake.bake_tiling_set(args.set_name, args.kind, args.tile, args.res, args.tile_samples, force=True, **params)
    export.write_manifest([], [args.set_name])
    short = args.set_name.replace("TS_", "").lower()
    bake.tiled_preview(args.set_name, os.path.join(paths.previews, "tiling_%s_2x2.jpg" % short))
    print(info["files"])


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
        if "--" in sys.argv:                       # blender -b -P build.py -- <args>
            argv = sys.argv[sys.argv.index("--") + 1:]
        elif bpy.app.binary_path and os.path.basename(sys.argv[0]).lower().startswith("blender"):
            argv = []
    ap = argparse.ArgumentParser(prog="build.py", description="MURDER INC. Blender art pipeline")
    sub = ap.add_subparsers(dest="cmd")

    def common(p):
        p.add_argument("--res", type=int, default=2048, help="bake resolution (default 2048)")
        p.add_argument("--samples", type=int, default=96, help="render samples (default 96)")
        p.add_argument("--tile-samples", type=int, default=4, help="anti-aliasing samples of tiling bakes")
        p.add_argument("--seed", type=int, default=0)
        p.add_argument("--only", type=lambda s: s.split(","), default=None, help="comma separated names")
        p.add_argument("--force", action="store_true", help="re-bake even when the cache says up to date")

    sub.add_parser("list", help="list families and surfaces")
    b = sub.add_parser("build", help="build a family")
    b.add_argument("family")
    b.add_argument("--bake", action="store_true", help="bake tiling and unique texture sets")
    b.add_argument("--rebake-unique", action="store_true", help="with --bake: re-bake unique sets that exist")
    b.add_argument("--export", action="store_true", help="export GLB files and the manifest")
    b.add_argument("--fbx", action="store_true", help="also export FBX")
    b.add_argument("--preview", action="store_true", help="render previews into art/previews")
    common(b)
    s = sub.add_parser("sheet", help="render the materials sheet")
    common(s)
    t = sub.add_parser("tile", help="bake one tiling set from a library surface")
    t.add_argument("kind")
    t.add_argument("set_name")
    t.add_argument("--tile", type=float, default=2.0, help="tile size in metres")
    t.add_argument("params", nargs="*", help="Param=value pairs, e.g. Cracks=0.5 Paint_Color=0.6,0.6,0.58")
    common(t)
    args = ap.parse_args(argv)
    if args.cmd == "list" or args.cmd is None:
        cmd_list(args)
    elif args.cmd == "build":
        cmd_build(args)
    elif args.cmd == "sheet":
        cmd_sheet(args)
    elif args.cmd == "tile":
        cmd_tile(args)


if __name__ == "__main__":
    main()
