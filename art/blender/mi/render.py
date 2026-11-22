"""Look-dev rigs, cameras and preview output.

    from mi import render
    render.rig_day()                                   # clear New York summer afternoon, sun 45 deg from the SW
    render.rig_night(lamp=(5, -6, 8.5), sign=(8, -10.5, 3.0), sign_color=(1.0, 0.1, 0.35))
    cam = render.cam_eye((1, -9), (20, -6.5))          # 1.65 m eye level
    cam = render.cam_hero(ob)                          # three-quarter view that frames an object
    cam = render.cam_top(ob)                           # orthographic plan
    render.render_jpeg("art/previews/thing_day.jpg", samples=128)      # 1280x720, denoised, <= 300 kB
    render.contact_sheet(paths, "art/previews/sheet.jpg", cols=4, labels=names)

Compass: +Y is north, +X is east. Angles for the sun are compass bearings (0 = north, 90 = east).
"""
import math
import os
import tempfile

import bpy
import numpy as np
from mathutils import Vector

from . import scene as _scene

# View exposure in stops. DAY puts a sunlit 18 % grey card at middle grey under the physical sky (sunlit grey
# reads 6.2 scene-linear). NIGHT suits the rig_night lamp wattages (about 3 W/m2 on the ground under a lamp).
EXPOSURE = {"DAY": -5.0, "NIGHT": -0.2}
VIEW = "AgX"                      # 5.3 view transforms: Standard, ACES 1.3, ACES 2.0, Khronos PBR Neutral, AgX,
LOOK_DAY = "AgX - Medium High Contrast"   # Filmic, Filmic Log, False Color, Raw. AgX looks are 'AgX - <name>'.
LOOK_NIGHT = "AgX - Medium High Contrast"


def setup(samples=96, res=(1280, 720), denoise=True, threads=None):
    """Cycles on CPU with OpenImageDenoise at the preview resolution."""
    s = bpy.context.scene
    _scene.setup_cycles(s, threads=threads or _scene.THREADS, samples=samples, denoise=denoise)
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = 100
    s.render.film_transparent = False
    return s


def look(view=VIEW, look_name="None", exposure=0.0, gamma=1.0):
    vs = bpy.context.scene.view_settings
    vs.view_transform = view
    try:
        vs.look = look_name
    except TypeError:
        vs.look = "None"
    vs.exposure = exposure
    vs.gamma = gamma
    bpy.context.scene.display_settings.display_device = "sRGB"


def _world():
    s = bpy.context.scene
    w = s.world or bpy.data.worlds.new("World")
    s.world = w
    nt = w.node_tree
    nt.nodes.clear()
    return w, nt


def _clear_rig():
    col = bpy.data.collections.get("Rig")
    if col:
        for o in list(col.objects):
            if o.type == "LIGHT" or o.name.startswith("Sign"):
                bpy.data.objects.remove(o, do_unlink=True)
    return _scene.collection("Rig")


def rig_day(sun_elevation=45.0, sun_azimuth=235.0, exposure=None, haze=1.6, sun_intensity=1.0, sky_strength=1.0,
            clouds=0.0):
    """Physically based sun and sky (Sky Texture, multiple scattering) for a clear summer afternoon in New York
    at about 4:15 PM: sun 45 degrees up, from the south-west (bearing 235). haze = aerosol density (1 = clean air,
    2-3 = humid city summer). The sun disc is part of the sky, so shadows have the right half-degree softness."""
    _clear_rig()
    w, nt = _world()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"        # 5.x names: SINGLE_SCATTERING, MULTIPLE_SCATTERING, PREETHAM, HOSEK_WILKIE
    sky.sun_disc = True
    sky.sun_size = math.radians(0.545)
    sky.sun_intensity = sun_intensity
    sky.sun_elevation = math.radians(sun_elevation)
    sky.sun_rotation = math.radians(sun_azimuth)      # measured: 0 puts the sun in the north (+Y), 90 in the east (+X)
    sky.air_density = 1.0
    sky.aerosol_density = haze
    sky.ozone_density = 1.0
    bg.inputs["Strength"].default_value = sky_strength
    nt.links.new(sky.outputs[0], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    look(VIEW, LOOK_DAY, EXPOSURE["DAY"] if exposure is None else exposure)
    return {"world": w, "sky": sky, "sun_dir": sun_direction(sun_elevation, sun_azimuth)}


def sun_direction(elevation_deg, azimuth_deg):
    """Unit vector pointing from the scene toward the sun."""
    e, a = math.radians(elevation_deg), math.radians(azimuth_deg)
    return Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))


def rig_night(lamp=(0.0, 0.0, 8.5), lamp_target=None, lamp_watts=2600.0, sign=None, sign_color=(1.0, 0.12, 0.38),
              sign_watts=260.0, sign_size=(2.4, 0.7), sign_target=None, exposure=None, sky=1.0, extra_lamps=()):
    """Night: dark blue sky with a warm city glow on the horizon, one sodium-vapour street light (about 2100 K)
    from above, and optionally a coloured sign light (neon pink by default). lamp, sign: world positions.
    extra_lamps: more sodium positions, e.g. the next lamp down the street."""
    col = _clear_rig()
    w, nt = _world()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0.020, 0.016, 0.014, 1.0)      # below the horizon
    els[1].position, els[1].color = 1.0, (0.0035, 0.0055, 0.016, 1.0)    # zenith: deep blue-black
    e = els.new(0.02)
    e.color = (0.075, 0.050, 0.030, 1.0)                                 # city glow on the horizon
    e = els.new(0.22)
    e.color = (0.012, 0.014, 0.030, 1.0)
    nt.links.new(ramp.outputs[0], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = sky
    nt.links.new(bg.outputs[0], out.inputs["Surface"])

    def sodium(pos, name, watts):
        L = bpy.data.lights.new(name, "SPOT")
        L.energy = watts
        L.use_temperature = True          # 5.x lights take a colour temperature directly
        L.temperature = 2100.0
        L.color = (1.0, 1.0, 1.0)
        L.spot_size = math.radians(150.0)
        L.spot_blend = 0.55
        L.shadow_soft_size = 0.18         # a cobra-head luminaire is about 35 cm across
        o = bpy.data.objects.new(name, L)
        o.location = pos
        tgt = Vector(lamp_target) if lamp_target is not None else Vector((pos[0], pos[1], 0.0))
        d = (tgt - Vector(pos))
        o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        col.objects.link(o)
        return o

    lights = [sodium(lamp, "Sodium", lamp_watts)]
    for i, p in enumerate(extra_lamps):
        lights.append(sodium(p, "Sodium.%02d" % (i + 1), lamp_watts))
    if sign is not None:
        L = bpy.data.lights.new("Sign", "AREA")
        L.shape = "RECTANGLE"
        L.size, L.size_y = sign_size
        L.energy = sign_watts
        L.color = sign_color
        o = bpy.data.objects.new("Sign", L)
        o.location = sign
        tgt = Vector(sign_target) if sign_target is not None else Vector((sign[0], 0.0, 0.0))
        o.rotation_euler = (tgt - Vector(sign)).to_track_quat("-Z", "Y").to_euler()
        col.objects.link(o)
        lights.append(o)
    look(VIEW, LOOK_NIGHT, EXPOSURE["NIGHT"] if exposure is None else exposure)
    return {"world": w, "lights": lights}


def mirror_source(camera_pos, ground_point, source_height, ground_z=0.0):
    """Where to hang a light so that its mirror image shows at a point on wet ground, as seen from the camera.
    Returns (x, y, z). Use it for night shots: put a lamp or a sign there and the puddle at ground_point
    reflects it."""
    cx, cy, cz = camera_pos
    px, py = ground_point[0], ground_point[1]
    hc = cz - ground_z
    k = (hc + (source_height - ground_z)) / hc
    return (cx + (px - cx) * k, cy + (py - cy) * k, source_height)


def sign(location, size=(2.4, 0.7), color=(1.0, 0.12, 0.38), watts=300.0, facing=(0.0, -1.0, 0.0), name="Sign",
         strength=8.0):
    """A lit sign: an emissive panel (so reflections have something to show) plus an area light of the same colour
    just in front of it. facing: the direction the sign looks. Returns (panel, light)."""
    import bmesh
    f = Vector(facing).normalized()
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bmesh.ops.scale(bm, vec=(size[0], size[1], 1.0), verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    panel = bpy.data.objects.new(name, me)
    q = f.to_track_quat("Z", "Y")
    panel.rotation_euler = q.to_euler()
    panel.location = Vector(location)
    m = bpy.data.materials.new(name + "_Mat")
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    me.materials.append(m)
    col = _scene.collection("Rig")
    col.objects.link(panel)
    L = bpy.data.lights.new(name + "_Light", "AREA")
    L.shape = "RECTANGLE"
    L.size, L.size_y = size
    L.energy = watts
    L.color = color
    lo = bpy.data.objects.new(name + "_Light", L)
    lo.location = Vector(location) + f * 0.06
    lo.rotation_euler = f.to_track_quat("-Z", "Y").to_euler()
    lo.visible_camera = False
    col.objects.link(lo)
    return panel, lo


# ------------------------------------------------------------------------------------------------------- cameras

def _cam(name, lens=35.0, ortho=None):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
        cd.sensor_width = 36.0
    cd.clip_start, cd.clip_end = 0.02, 2000.0
    ob = bpy.data.objects.new(name, cd)
    _scene.collection("Rig").objects.link(ob)
    bpy.context.scene.camera = ob
    return ob


def cam_look(location, target, lens=35.0, name="Cam", roll=0.0, dof=None):
    """Camera at location looking at target. dof=(focus distance m, f-stop) for a shallow depth of field."""
    ob = _cam(name, lens)
    ob.location = location
    d = Vector(target) - Vector(location)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if dof:
        ob.data.dof.use_dof = True
        ob.data.dof.focus_distance = dof[0]
        ob.data.dof.aperture_fstop = dof[1]
    return ob


def cam_eye(xy, look_at_xy, height=1.65, look_height=None, lens=28.0, name="Cam_Eye", ground_z=0.0):
    """Standing eye level (1.65 m above ground_z) at xy looking toward look_at_xy."""
    lh = height * 0.45 if look_height is None else look_height
    return cam_look((xy[0], xy[1], ground_z + height), (look_at_xy[0], look_at_xy[1], ground_z + lh), lens, name)


def _bounds(objs):
    if not isinstance(objs, (list, tuple)):
        objs = [objs]
    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    for o in objs:
        a, b = _scene.bounds(o, world=True)
        lo, hi = np.minimum(lo, a), np.maximum(hi, b)
    return lo, hi


def cam_hero(objs, direction=(1.0, -1.0, 0.55), lens=50.0, margin=1.25, name="Cam_Hero", aspect=16 / 9):
    """Three-quarter view that frames one or more objects. direction: from the subject toward the camera."""
    lo, hi = _bounds(objs)
    c = (lo + hi) / 2
    r = float(np.linalg.norm(hi - lo)) / 2
    fov_h = 2 * math.atan(18.0 / lens)
    fov_v = 2 * math.atan(18.0 / lens / aspect)
    dist = r * margin / math.sin(min(fov_h, fov_v) / 2)
    d = Vector(direction).normalized()
    return cam_look(Vector(c) + d * dist, c, lens, name)


def cam_top(objs=None, bounds=None, margin=1.04, name="Cam_Top", aspect=16 / 9, height=60.0):
    """Orthographic plan view, north up, fitted to the objects (or to bounds=((x0, y0), (x1, y1)))."""
    if bounds is None:
        lo, hi = _bounds(objs)
    else:
        lo, hi = np.array([*bounds[0], 0.0]), np.array([*bounds[1], 0.0])
    w, h = hi[0] - lo[0], hi[1] - lo[1]
    scale = max(w, h * aspect) * margin
    ob = _cam(name, ortho=scale)
    ob.location = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, max(hi[2], 0.0) + height)
    ob.rotation_euler = (0.0, 0.0, 0.0)
    return ob


# -------------------------------------------------------------------------------------------------------- output

def save_jpeg(image, path, max_kb=300, quality=93):
    """Write a PIL image as JPEG no larger than max_kb (quality steps down until it fits)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    image = image.convert("RGB")
    q = quality
    while True:
        image.save(path, "JPEG", quality=q, optimize=True, progressive=True, subsampling=0 if q >= 88 else 2)
        if os.path.getsize(path) <= max_kb * 1024 or q <= 40:
            break
        q -= 3
    return path, q


def render_png(path, samples=None, res=None):
    """Render the scene camera to an 8-bit PNG (lossless intermediate)."""
    s = bpy.context.scene
    if samples:
        s.cycles.samples = int(samples)
    if res:
        s.render.resolution_x, s.render.resolution_y = res
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGB"
    s.render.image_settings.color_depth = "8"
    s.render.image_settings.compression = 15
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def render_jpeg(path, samples=None, res=(1280, 720), max_kb=300, keep_png=False):
    """Render to a JPEG preview: 1280x720, denoised, at most 300 kB. Returns (path, seconds)."""
    import time
    from PIL import Image
    t = time.time()
    tmp = os.path.join(tempfile.gettempdir(), "mi_render_%d.png" % os.getpid()) if not keep_png else os.path.splitext(path)[0] + ".png"
    render_png(tmp, samples, res)
    img = Image.open(tmp)
    save_jpeg(img, path, max_kb)
    if not keep_png:
        try:
            os.remove(tmp)
        except OSError:
            pass
    return path, time.time() - t


def measure_exposure(target=0.18, samples=12, res=(160, 90), percentile=None):
    """Quick render to scene-linear EXR and return the exposure (stops) that would bring the log-average
    luminance to `target`. Use it to calibrate a new rig, then hard-code the number."""
    s = bpy.context.scene
    keep = (s.render.resolution_x, s.render.resolution_y, s.cycles.samples, s.render.image_settings.file_format,
            s.view_settings.view_transform, s.view_settings.look, s.view_settings.exposure, s.cycles.use_denoising)
    tmp = os.path.join(tempfile.gettempdir(), "mi_expo_%d.exr" % os.getpid())
    s.render.resolution_x, s.render.resolution_y = res
    s.cycles.samples = samples
    s.cycles.use_denoising = False
    s.view_settings.look = "None"
    s.view_settings.view_transform = "Raw"
    s.view_settings.exposure = 0.0
    s.render.image_settings.file_format = "OPEN_EXR"
    s.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(tmp)
    a = np.empty(res[0] * res[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    a = a.reshape(-1, 4)[:, :3]
    lum = a @ np.array([0.2126, 0.7152, 0.0722])
    if percentile is not None:
        v = float(np.percentile(lum, percentile))
    else:
        v = float(np.exp(np.mean(np.log(np.maximum(lum, 1e-6)))))
    (s.render.resolution_x, s.render.resolution_y, s.cycles.samples, s.render.image_settings.file_format,
     s.view_settings.view_transform, s.view_settings.look, s.view_settings.exposure, s.cycles.use_denoising) = keep
    try:
        os.remove(tmp)
    except OSError:
        pass
    return math.log2(target / max(v, 1e-9))


def _font(size):
    from PIL import ImageFont
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def label(image, text, xy=(10, 8), size=18, fill=(255, 255, 255), plate=(0, 0, 0, 170)):
    """Draw a caption on a PIL image: white grotesque on a black plate (the game's transit-sign vernacular)."""
    from PIL import Image, ImageDraw
    img = image.convert("RGBA")
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    f = _font(size)
    box = d.textbbox(xy, text, font=f)
    d.rectangle((box[0] - 6, box[1] - 4, box[2] + 6, box[3] + 4), fill=plate)
    d.text(xy, text, font=f, fill=fill)
    return Image.alpha_composite(img, over).convert("RGB")


def contact_sheet(images, out, cols=4, labels=None, cell=None, size=(1280, 720), gap=4, bg=(16, 16, 16), max_kb=300,
                  label_size=15):
    """Tile images (paths or PIL images) into one labelled JPEG of the given size."""
    from PIL import Image
    ims = [Image.open(p).convert("RGB") if isinstance(p, str) else p.convert("RGB") for p in images]
    n = len(ims)
    rows = int(math.ceil(n / cols))
    cw = (size[0] - gap * (cols + 1)) // cols
    chh = (size[1] - gap * (rows + 1)) // rows
    if cell:
        cw, chh = cell
    sheet = Image.new("RGB", size, bg)
    for i, im in enumerate(ims):
        r, c = divmod(i, cols)
        # cover-fit
        sc = max(cw / im.width, chh / im.height)
        im2 = im.resize((max(1, round(im.width * sc)), max(1, round(im.height * sc))), Image.LANCZOS)
        x0, y0 = (im2.width - cw) // 2, (im2.height - chh) // 2
        im2 = im2.crop((x0, y0, x0 + cw, y0 + chh))
        if labels and i < len(labels) and labels[i]:
            im2 = label(im2, labels[i], size=label_size)
        sheet.paste(im2, (gap + c * (cw + gap), gap + r * (chh + gap)))
    save_jpeg(sheet, out, max_kb)
    return out


def backdrop(size=200.0, color=(0.085, 0.083, 0.08), z=-0.02, name="Backdrop"):
    """Big neutral ground plane so previews do not float in a void (never exported)."""
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2)
    bmesh.ops.translate(bm, vec=(0, 0, z), verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    _scene.collection("Rig").objects.link(ob)
    from . import mat as _mat
    me.materials.append(_mat.flat("M_Backdrop", color, 0.9))
    return ob
