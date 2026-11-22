#!/usr/bin/env python
"""Render the preview pictures of the scan library with Cycles. Needs Blender as a Python module (import bpy).

    <python with bpy> art/scans/render_sheets.py [surfaces] [models] [skies] [--only NAME ...] [--samples N] [--force]

  surfaces  art/previews/scans_sheet_<n>.jpg   every tiling set on a 4 m x 4 m ground or wall panel at the tile size
                                               the catalogue states, with a 1.8 m grey box and a 1 m stick (decimetre
                                               bands, the last decimetre in centimetres); the inset is a straight-on
                                               view 0.4 m across at the centimetre end of the stick
  models    art/previews/scans_models.jpg      every scanned prop at its real size beside the same box and stick;
            art/previews/scans_models_detail_<n>.jpg   the same cells, larger. Red arrow = +X, green = +Y (Blender
                                               axes after glTF import), magenta ball = the model's own origin
  skies     art/previews/scans_skies.jpg       a chrome and an 18 % grey sphere under every sky, each exposed so that
                                               a horizontal grey card reads mid grey (the label gives the shift)

With no word, all three. Every cell is rendered once into art/out/scans/cells/ and reused until the catalogue entry
or its files change. CPU only, two threads, no denoiser (this Blender build has none): the cells are small and use
enough samples instead. Lighting for surfaces and props: the catalogue's first clear-sky HDRI, turned so that the sun
rakes the panel; view transform Standard, exposure set from the sky's measured irradiance so that an 18 % grey card
lying flat renders at 18 %: what looks dark here is dark.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ART = HERE.parent
OUT = ART / "out"
CELLS = OUT / "scans" / "cells"
PREVIEWS = ART / "previews"
CATALOGUE = HERE / "sets.json"
VERSION = 7  # bump to throw every cached cell away

SHEET = (1280, 720)
SURFACE_GRID = (3, 2)
LABEL_H = 22
THREADS = 2


# ------------------------------------------------------------------------------------------------- scene basics

def reset(samples, size):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    s.cycles.samples = samples
    s.cycles.use_denoising = False
    s.cycles.use_adaptive_sampling = False
    s.cycles.max_bounces = 3
    s.cycles.diffuse_bounces = 2
    s.cycles.glossy_bounces = 3
    s.cycles.sample_clamp_indirect = 8.0
    s.cycles.pixel_filter_type = "BLACKMAN_HARRIS"
    s.render.threads_mode = "FIXED"
    s.render.threads = THREADS
    s.render.resolution_x, s.render.resolution_y = size
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGB"
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    s.display_settings.display_device = "sRGB"
    return s


def set_world(scene, hdr_path, sun_u, sun_azimuth_deg, exposure_ev, strength=1.0):
    """Light the scene with a sky, turned about Z so that its sun stands at sun_azimuth_deg (counter-clockwise
    from +X, the direction from the scene towards the sun)."""
    world = bpy.data.worlds.new("Sky")
    world.use_nodes = True
    scene.world = world
    nt = world.node_tree
    nt.nodes.clear()
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    bg = nt.nodes.new("ShaderNodeBackground")
    out = nt.nodes.new("ShaderNodeOutputWorld")
    env.image = bpy.data.images.load(str(hdr_path), check_existing=True)
    # Cycles puts the middle column of an unrotated equirect (u = 0.5) at +X and u = 0.25 at +Y, so column u
    # stands at azimuth 360 * (0.5 - u); the Mapping node turns the lookup direction, so the picture turns the
    # other way: world azimuth = image azimuth - rotation
    image_azimuth = 360.0 * (0.5 - sun_u)
    mapping.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(image_azimuth - sun_azimuth_deg))
    bg.inputs["Strength"].default_value = strength
    nt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    scene.view_settings.exposure = exposure_ev


def flat_material(name, colour, roughness=0.8, metallic=0.0, emission=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*colour, 1.0)
    p.inputs["Roughness"].default_value = roughness
    p.inputs["Metallic"].default_value = metallic
    if emission:
        p.inputs["Emission Color"].default_value = (*emission, 1.0)
        p.inputs["Emission Strength"].default_value = 1.0
    return m


def add_mesh(name, verts, faces, material, uvs=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    if uvs:
        layer = mesh.uv_layers.new(name="UVMap")
        for poly in mesh.polygons:
            for loop, vert in zip(poly.loop_indices, poly.vertices):
                layer.data[loop].uv = uvs[vert]
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def add_box(name, lo, hi, material):
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return add_mesh(name, v, f, material)


def scale_props(box_at, stick_from, stick_axis):
    """The 1.8 m box (18 % grey) and the 1 m stick: decimetre bands, the last decimetre cut into centimetres."""
    grey = flat_material("ScaleGrey", (0.18, 0.18, 0.18))
    white = flat_material("StickWhite", (0.8, 0.8, 0.8), 0.6)
    red = flat_material("StickRed", (0.55, 0.02, 0.02), 0.6)
    black = flat_material("StickBlack", (0.02, 0.02, 0.02), 0.6)
    bx, by = box_at
    add_box("ScaleBox", (bx - 0.225, by - 0.125, 0.0), (bx + 0.225, by + 0.125, 1.8), grey)
    a = Vector(stick_from)
    d = Vector(stick_axis).normalized()
    # two axes across the stick, 3 cm square
    side = Vector((0, 0, 1)).cross(d)
    if side.length < 1e-6:
        side = Vector((1, 0, 0))
    side.normalize()
    up = d.cross(side)
    def piece(t0, t1, mat):
        corners = []
        for t in (t0, t1):
            for su, uu in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                corners.append(tuple(a + d * t + side * 0.015 * su + up * 0.015 * uu))
        faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
        add_mesh("Stick", corners, faces, mat)
    for i in range(9):
        piece(i * 0.1, (i + 1) * 0.1, white if i % 2 == 0 else red)
    for i in range(10):
        piece(0.9 + i * 0.01, 0.9 + (i + 1) * 0.01, black if i % 2 == 0 else white)


def add_camera(name, location, target, lens=50.0, ortho_scale=None):
    cam = bpy.data.cameras.new(name)
    if ortho_scale:
        cam.type = "ORTHO"
        cam.ortho_scale = ortho_scale
    else:
        cam.lens = lens
    cam.clip_start, cam.clip_end = 0.05, 500.0
    obj = bpy.data.objects.new(name, cam)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    direction = Vector(target) - Vector(location)
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return obj


def render(scene, camera, path, size=None, samples=None):
    scene.camera = camera
    if size:
        scene.render.resolution_x, scene.render.resolution_y = size
    if samples:
        scene.cycles.samples = samples
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


# ------------------------------------------------------------------------------------------------ tiling panels

def tiling_material(entry):
    """Base colour, normal and ORM of a set, mapped at its real size on a UV layer that is in metres."""
    tx, ty = entry["tile_m"]
    files = {role: OUT / spec["out"] for role, spec in entry["files"].items()}
    m = bpy.data.materials.new(entry["set"])
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    uv = nt.nodes.new("ShaderNodeUVMap")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1.0 / tx, 1.0 / ty, 1.0)
    nt.links.new(uv.outputs["UV"], mapping.inputs["Vector"])

    def tex(role, colourspace):
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(str(files[role]), check_existing=True)
        node.image.colorspace_settings.name = colourspace
        nt.links.new(mapping.outputs["Vector"], node.inputs["Vector"])
        return node

    bc = tex("BC", "sRGB")
    nt.links.new(bc.outputs["Color"], p.inputs["Base Color"])
    orm = tex("ORM", "Non-Color")
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], p.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], p.inputs["Metallic"])
    nrm = tex("N", "Non-Color")
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(nrm.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
    return m


def surface_cell(entry, sky, path, inset_path, size, samples):
    """One tiling set on a 4 m x 4 m panel, plus the straight-on 0.4 m close-up."""
    scene = reset(samples, size)
    mat = tiling_material(entry)
    ground_grey = flat_material("Apron", (0.18, 0.18, 0.18), 0.9)
    wall = entry.get("preview", "ground") == "wall"
    ev = sky["measured"]["ev_for_grey_card"]
    hdr = OUT / sky["files"]["HDR"]["out"].replace("{res}", sky.get("resolution", "2k"))
    if wall:
        # the wall stands at y = 2 facing -Y; image x runs along world x, image y up the wall
        add_mesh("Panel", [(-2, 2, 0), (2, 2, 0), (2, 2, 4), (-2, 2, 4)], [(0, 1, 2, 3)], mat,
                 uvs=[(0, 0), (4, 0), (4, 4), (0, 4)])
        add_mesh("Apron", [(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [(0, 1, 2, 3)], ground_grey)
        scale_props(box_at=(1.35, 1.45), stick_from=(-1.3, 1.975, 0.0), stick_axis=(0, 0, 1))
        set_world(scene, hdr, sky["measured"]["sun_uv"][0], 215.0, ev)
        cam = add_camera("Main", (0.55, -6.6, 1.65), (0.0, 2.0, 1.95), lens=50)
        macro = add_camera("Macro", (-1.13, 0.5, 0.85), (-1.13, 2.0, 0.85), ortho_scale=0.4)
    else:
        add_mesh("Panel", [(-2, -2, 0), (2, -2, 0), (2, 2, 0), (-2, 2, 0)], [(0, 1, 2, 3)], mat,
                 uvs=[(0, 0), (4, 0), (4, 4), (0, 4)])
        add_mesh("Apron", [(-30, -30, -0.002), (30, -30, -0.002), (30, 30, -0.002), (-30, 30, -0.002)], [(0, 1, 2, 3)],
                 ground_grey)
        scale_props(box_at=(1.3, 1.2), stick_from=(0.2, -1.3, 0.015), stick_axis=(-1, 0, 0))
        set_world(scene, hdr, sky["measured"]["sun_uv"][0], 150.0, ev)
        cam = add_camera("Main", (0.6, -6.3, 4.3), (0.0, 0.05, 0.4), lens=50)
        macro = add_camera("Macro", (-0.63, -1.13, 2.0), (-0.63, -1.13, 0.0), ortho_scale=0.4)
        macro.rotation_euler = (0.0, 0.0, 0.0)  # straight down, image up = world +Y
    render(scene, cam, path)
    render(scene, macro, inset_path, size=(264, 264), samples=max(16, samples // 2))


# ------------------------------------------------------------------------------------------------------- models

def import_gltf(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [o for o in bpy.data.objects if o not in before]


def world_bounds(objects):
    lo, hi = Vector((1e9, 1e9, 1e9)), Vector((-1e9, -1e9, -1e9))
    for o in objects:
        if o.type != "MESH":
            continue
        for corner in o.bound_box:
            w = o.matrix_world @ Vector(corner)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def arrow(name, start, end, colour):
    mat = flat_material(name, colour, 0.5, emission=tuple(c * 0.6 for c in colour))
    a, b = Vector(start), Vector(end)
    d = (b - a).normalized()
    side = Vector((0, 0, 1)).cross(d).normalized() * 0.012
    up = Vector((0, 0, 0.006))
    verts = [tuple(a - side + up), tuple(a + side + up), tuple(b + side + up), tuple(b - side + up),
             tuple(b - side * 4 + up), tuple(b + side * 4 + up), tuple(b + d * 0.09 + up)]
    add_mesh(name, verts, [(0, 1, 2, 3), (4, 5, 6)], mat)


def model_cell(entry, sky, path, size, samples):
    """One prop standing on the ground at its real size. Returns what the camera framed, for the label."""
    scene = reset(samples, size)
    folder = OUT / entry["files"]["GLTF"]["out"]
    gltf = folder / Path(entry["files"]["GLTF"]["src"].replace("{res}", entry.get("resolution", "2k"))).name
    objs = import_gltf(gltf)
    bpy.context.view_layer.update()
    lo, hi = world_bounds(objs)
    fix = entry.get("preview_scale", 1.0)
    roots = [o for o in objs if o.parent is None]
    if fix != 1.0:
        for o in roots:
            o.matrix_world = Matrix.Scale(fix, 4) @ o.matrix_world
        bpy.context.view_layer.update()
        lo, hi = world_bounds(objs)
    # stand it on the ground with the footprint centre at the world origin (preview only)
    shift = Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    for o in roots:
        o.matrix_world = Matrix.Translation(shift) @ o.matrix_world
    bpy.context.view_layer.update()
    size_m = hi - lo
    ground = flat_material("Ground", (0.18, 0.18, 0.18), 0.9)
    add_mesh("Ground", [(-40, -40, 0), (40, -40, 0), (40, 40, 0), (-40, 40, 0)], [(0, 1, 2, 3)], ground)
    half = size_m / 2
    scale_props(box_at=(half.x + 0.45, 0.0), stick_from=(half.x + 0.2, -half.y - 0.12, 0.015), stick_axis=(-1, 0, 0))
    arrow("AxisX", (0, -half.y - 0.3, 0), (0.4, -half.y - 0.3, 0), (0.9, 0.05, 0.05))
    arrow("AxisY", (0, -half.y - 0.3, 0), (0, -half.y + 0.1, 0), (0.05, 0.7, 0.05))
    # the model's own origin
    origin = shift * fix if fix != 1.0 else shift
    marker = flat_material("Origin", (0.9, 0.0, 0.9), 0.4, emission=(0.6, 0.0, 0.6))
    r = max(0.012, min(0.04, max(size_m) * 0.03))
    add_box("Origin", (shift.x - r, shift.y - r, shift.z - r), (shift.x + r, shift.y + r, shift.z + r), marker)
    ev = sky["measured"]["ev_for_grey_card"]
    hdr = OUT / sky["files"]["HDR"]["out"].replace("{res}", sky.get("resolution", "2k"))
    set_world(scene, hdr, sky["measured"]["sun_uv"][0], 200.0, ev)
    # frame the prop and the 1 m stick; small props all get the same frame, so they compare with the whole box
    reach = max(size_m.x / 2 + 0.75, size_m.z * 0.62, size_m.y / 2 + 0.5, 1.05)
    centre = Vector((0.3, 0.0, min(max(size_m.z, 1.8), reach * 1.25) * 0.47))
    az, el = math.radians(-60.0), math.radians(18.0)
    lens = 60.0
    fov_v = 2 * math.atan((36.0 / (size[0] / size[1])) / 2 / lens)
    dist = reach * 1.06 / math.tan(fov_v / 2)
    pos = centre + Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))) * dist
    cam = add_camera("Main", pos, centre, lens=lens)
    render(scene, cam, path)


# -------------------------------------------------------------------------------------------------------- skies

def sky_cell(entry, path, size, samples):
    scene = reset(samples, size)
    m = entry["measured"]
    hdr = OUT / entry["files"]["HDR"]["out"].replace("{res}", entry.get("resolution", "2k"))
    set_world(scene, hdr, m["sun_uv"][0], 215.0, m["ev_for_grey_card"])
    chrome = flat_material("Chrome", (0.95, 0.95, 0.95), 0.02, metallic=1.0)
    grey = flat_material("Grey", (0.18, 0.18, 0.18), 0.6)
    disc = flat_material("Disc", (0.18, 0.18, 0.18), 0.9)
    for x, mat in ((-0.56, chrome), (0.56, grey)):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=0.5, location=(x, 0.0, 0.5))
        ball = bpy.context.object
        bpy.ops.object.shade_smooth()
        ball.data.materials.append(mat)
    bpy.ops.mesh.primitive_circle_add(vertices=64, radius=2.2, fill_type="NGON", location=(0, 0, 0))
    bpy.context.object.data.materials.append(disc)
    cam = add_camera("Main", (0.0, -5.4, 1.05), (0.0, 0.0, 0.52), lens=58)
    render(scene, cam, path)


# ---------------------------------------------------------------------------------------------------- composing

def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def cell_key(entry, extra):
    files = []
    for spec in entry["files"].values():
        f = OUT / spec["out"].replace("{res}", entry.get("resolution", "2k"))
        if f.is_file():
            files.append((f.name, f.stat().st_size, int(f.stat().st_mtime)))
        elif f.is_dir():
            files += [(p.name, p.stat().st_size) for p in sorted(f.rglob("*")) if p.is_file()]
    blob = json.dumps([VERSION, entry.get("tile_m"), entry.get("preview"), entry.get("preview_scale"), files, extra],
                      sort_keys=True)
    return hashlib.sha1(blob.encode()).hexdigest()[:16]


def cached(path, key, force):
    stamp = path.with_suffix(".key")
    if not force and path.is_file() and stamp.is_file() and stamp.read_text() == key:
        return True
    return False


def stamp(path, key):
    path.with_suffix(".key").write_text(key)


def save_jpeg(image, dest, limit=300_000):
    """Write a JPEG no larger than limit bytes, giving up quality step by step."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    for quality in (90, 86, 82, 78, 74, 70, 66, 62, 58, 54, 50):
        image.save(dest, "JPEG", quality=quality, optimize=True, subsampling=1 if quality >= 80 else 2)
        if dest.stat().st_size <= limit:
            return quality
    return quality


def label(draw, xy, text, size=14, fill=(235, 235, 235), width=None):
    f = font(size)
    while width and size > 8 and draw.textlength(text, font=f) > width:
        size -= 1
        f = font(size)
    draw.text(xy, text, fill=fill, font=f)


def do_surfaces(cat, sky, only, samples, force):
    sets = [e for e in cat["sets"] if e["kind"] == "texture"]
    cols, rows = SURFACE_GRID
    cw, ch = SHEET[0] // cols, SHEET[1] // rows
    size = (cw, ch - LABEL_H)
    CELLS.mkdir(parents=True, exist_ok=True)
    for e in sets:
        if only and e["set"] not in only and e["slug"] not in only:
            continue
        main, inset = CELLS / f"{e['set']}.png", CELLS / f"{e['set']}_macro.png"
        key = cell_key(e, [samples, size, sky["set"]])
        if cached(main, key, force) and inset.is_file():
            continue
        surface_cell(e, sky, main, inset, size, samples)
        stamp(main, key)
        print("rendered", e["set"], flush=True)
    per = cols * rows
    names = []
    for n in range(0, len(sets), per):
        sheet = Image.new("RGB", SHEET, (16, 16, 16))
        d = ImageDraw.Draw(sheet)
        for i, e in enumerate(sets[n:n + per]):
            x, y = (i % cols) * cw, (i // cols) * ch
            main, inset = CELLS / f"{e['set']}.png", CELLS / f"{e['set']}_macro.png"
            if not main.is_file():
                continue
            sheet.paste(Image.open(main).convert("RGB").resize(size, Image.LANCZOS), (x, y + LABEL_H))
            s = 132
            mac = Image.open(inset).convert("RGB").resize((s, s), Image.LANCZOS)
            ix, iy = x + cw - s - 4, y + LABEL_H + 4
            d.rectangle((ix - 2, iy - 2, ix + s + 1, iy + s + 1), fill=(255, 255, 255))
            sheet.paste(mac, (ix, iy))
            d.rectangle((ix, iy + s - 15, ix + 70, iy + s), fill=(0, 0, 0))
            label(d, (ix + 3, iy + s - 15), "0.4 m wide", 11)
            t = e["tile_m"]
            label(d, (x + 5, y + 3), f"{e['set']}   {t[0]:.2f} x {t[1]:.2f} m", 14, width=cw - 10)
            d.rectangle((x, y, x + cw - 1, y + ch - 1), outline=(60, 60, 60))
        dest = PREVIEWS / f"scans_sheet_{n // per + 1}.jpg"
        q = save_jpeg(sheet, dest)
        names.append(dest.name)
        print(f"{dest.name}: {dest.stat().st_size / 1000:.0f} kB (quality {q})")
    # sheets left over from a longer catalogue would mislead
    for old in PREVIEWS.glob("scans_sheet_*.jpg"):
        if old.name not in names and not only:
            old.unlink()


def do_models(cat, sky, only, samples, force):
    models = [e for e in cat["sets"] if e["kind"] == "model"]
    size = (256, 180)
    CELLS.mkdir(parents=True, exist_ok=True)
    for e in models:
        if only and e["set"] not in only:
            continue
        cell = CELLS / f"model_{e['set']}.png"
        key = cell_key(e, [samples, size, sky["set"]])
        if cached(cell, key, force):
            continue
        model_cell(e, sky, cell, size, samples)
        stamp(cell, key)
        print("rendered", e["set"], flush=True)

    def dims(e):
        s = e.get("measured", {}).get("size_m")
        k = e.get("preview_scale", 1.0)
        return "{:.2f} x {:.2f} x {:.2f} m".format(*(v * k for v in s)) if s else ""

    # the overview: everything in one picture
    cols = 8
    rows = math.ceil(len(models) / cols)
    cw, ch = SHEET[0] // cols, SHEET[1] // rows
    sheet = Image.new("RGB", SHEET, (16, 16, 16))
    d = ImageDraw.Draw(sheet)
    ih = ch - 28
    iw = min(cw, round(ih * size[0] / size[1]))
    for i, e in enumerate(models):
        x, y = (i % cols) * cw, (i // cols) * ch
        cell = CELLS / f"model_{e['set']}.png"
        if cell.is_file():
            sheet.paste(Image.open(cell).convert("RGB").resize((iw, ih), Image.LANCZOS), (x + (cw - iw) // 2, y + 28))
        label(d, (x + 3, y + 1), e["set"], 12, width=cw - 6)
        label(d, (x + 3, y + 14), dims(e), 11, fill=(255, 220, 0), width=cw - 6)
        d.rectangle((x, y, x + cw - 1, y + ch - 1), outline=(60, 60, 60))
    q = save_jpeg(sheet, PREVIEWS / "scans_models.jpg")
    print(f"scans_models.jpg: {(PREVIEWS / 'scans_models.jpg').stat().st_size / 1000:.0f} kB (quality {q})")
    # the same cells at full size, 20 to a picture
    cols, rows = 5, 4
    cw, ch = SHEET[0] // cols, SHEET[1] // rows
    names = []
    for n in range(0, len(models), cols * rows):
        sheet = Image.new("RGB", SHEET, (16, 16, 16))
        d = ImageDraw.Draw(sheet)
        for i, e in enumerate(models[n:n + cols * rows]):
            x, y = (i % cols) * cw, (i // cols) * ch
            cell = CELLS / f"model_{e['set']}.png"
            if cell.is_file():
                im = Image.open(cell).convert("RGB")
                sheet.paste(im.crop((0, 0, cw, ch)), (x, y))
            d.rectangle((x, y, x + cw - 1, y + 16), fill=(0, 0, 0))
            label(d, (x + 3, y + 1), f"{e['set']}  {dims(e)}", 12, width=cw - 6)
            d.rectangle((x, y, x + cw - 1, y + ch - 1), outline=(60, 60, 60))
        dest = PREVIEWS / f"scans_models_detail_{n // (cols * rows) + 1}.jpg"
        q = save_jpeg(sheet, dest)
        names.append(dest.name)
        print(f"{dest.name}: {dest.stat().st_size / 1000:.0f} kB (quality {q})")
    for old in PREVIEWS.glob("scans_models_detail_*.jpg"):
        if old.name not in names and not only:
            old.unlink()


def do_skies(cat, only, samples, force):
    skies = [e for e in cat["sets"] if e["kind"] == "hdri"]
    cols = 5
    rows = math.ceil(len(skies) / cols)
    cw, ch = SHEET[0] // cols, SHEET[1] // rows
    size = (cw, ch - 30)
    CELLS.mkdir(parents=True, exist_ok=True)
    for e in skies:
        if only and e["set"] not in only:
            continue
        cell = CELLS / f"sky_{e['set']}.png"
        key = cell_key(e, [samples, size, e.get("measured", {}).get("ev_for_grey_card")])
        if cached(cell, key, force):
            continue
        sky_cell(e, cell, size, samples)
        stamp(cell, key)
        print("rendered", e["set"], flush=True)
    sheet = Image.new("RGB", SHEET, (16, 16, 16))
    d = ImageDraw.Draw(sheet)
    for i, e in enumerate(skies):
        x, y = (i % cols) * cw, (i // cols) * ch
        cell = CELLS / f"sky_{e['set']}.png"
        if cell.is_file():
            sheet.paste(Image.open(cell).convert("RGB").resize(size, Image.LANCZOS), (x, y + 30))
        m = e.get("measured", {})
        label(d, (x + 3, y + 1), e["set"], 12, width=cw - 6)
        sun = f"sun {m.get('sun_elevation_deg', 0):.0f} deg, " if m.get("has_sun") else "no sun disc, "
        label(d, (x + 3, y + 15), f"{sun}exposure {m.get('ev_for_grey_card', 0):+.1f} EV", 11, fill=(255, 220, 0), width=cw - 6)
        d.rectangle((x, y, x + cw - 1, y + ch - 1), outline=(60, 60, 60))
    q = save_jpeg(sheet, PREVIEWS / "scans_skies.jpg")
    print(f"scans_skies.jpg: {(PREVIEWS / 'scans_skies.jpg').stat().st_size / 1000:.0f} kB (quality {q})")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("what", nargs="*", choices=["surfaces", "models", "skies", []], help="default: all three")
    ap.add_argument("--only", nargs="+", metavar="NAME", help="render only these sets (the sheets are still composed)")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--force", action="store_true", help="render again even if a cached cell is current")
    args = ap.parse_args(argv)
    what = args.what or ["surfaces", "models", "skies"]
    cat = json.loads(CATALOGUE.read_text())
    sky = next(e for e in cat["sets"] if e["kind"] == "hdri" and e.get("role") == "preview light")
    only = set(args.only or [])
    if "surfaces" in what:
        do_surfaces(cat, sky, only, args.samples, args.force)
    if "models" in what:
        do_models(cat, sky, only, args.samples, args.force)
    if "skies" in what:
        do_skies(cat, only, max(48, args.samples * 2 // 3), args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
