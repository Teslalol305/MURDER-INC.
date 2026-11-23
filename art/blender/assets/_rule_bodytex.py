"""SK_Rule's body map, review round 1 (used by _rule_body): the generated 4K base colour on its own atlas, per
texel from the baked positions (mi/texel.bake_maps):

  - skin (arms, hands, neck) graded to the shared target (_rule_tex.SKIN_TARGET), so the body, the head and the
    first-person arms are one man's skin
  - the generated thin bands at both wrists painted out (the modelled bracelet is fitted on the right wrist)
  - the chest lettering printed strong enough to read at 2 m (the game's name in a script face, dark ink with a
    worn print), replacing the generated faint marks
The result is art/out/gen/rule/derived/T_Rule_Body_BC.png (git-ignored: it carries the likeness' source pixels).
"""
import os

import bpy
import numpy as np

from mi import gen3d

from . import _rule_head as HD

TEXT = "Murder Inc."


def _base_node(ob):
    m = ob.data.materials[0]
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    node = b.inputs["Base Color"].links[0].from_node if b.inputs["Base Color"].links else None
    seen = 0
    while node is not None and node.type != "TEX_IMAGE" and seen < 6:
        ins = [i for i in node.inputs if i.links]
        node = ins[0].links[0].from_node if ins else None
        seen += 1
    return node


def _lettering(w=2048, h=640):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    font = None
    for f in ("/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"):
        if os.path.exists(f):
            font = ImageFont.truetype(f, int(h * 0.62))
            break
    font = font or ImageFont.load_default()
    tw = d.textlength(TEXT, font=font)
    d.text(((w - tw) / 2, h * 0.12), TEXT, font=font, fill=255)
    img = img.filter(ImageFilter.GaussianBlur(1.2))
    return np.asarray(img, dtype=np.float32) / 255.0


def body_textures(body, btex, log=print, wrists=None):
    from mi import texel as T
    from assets import _rule_tex as RT
    res = 4096
    maps = T.bake_maps(body, res)
    mask = maps["mask"]
    P, N = maps["pos"], maps["normal"]
    bc = HD._load_png(os.path.join(HD.GEN, "body_meshy_bc_4k.png"), res)
    r, g, b = bc[..., 0], bc[..., 1], bc[..., 2]
    lum = HD._lum(bc)
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    red = mask & (r > 0.05) & (r > 2.2 * g) & (r > 2.2 * b)
    hue_skin = (r > g) & (g >= b * 0.9) & (r < 2.6 * g) & (g < 0.95 * r) & (lum > 0.006) & (lum < 0.5)
    skin = mask & hue_skin & ~red & (z > 0.45)
    log("  body texels: skin %.1f %%, shirt %.1f %%" % (100 * skin.sum() / mask.sum(), 100 * red.sum() / mask.sum()))
    out = bc.copy()
    fore = skin & (np.abs(x) > 0.22) & (z > 0.95) & (z < 1.35)
    graded, k = RT.grade_skin(bc[skin], fore[skin])
    out[skin] = graded
    log("  body skin graded: gains %s" % np.round(k, 3).tolist())
    # the neck below the join takes the head's neck colour just above it (no tone step under the jaw)
    neck = skin & (z > 1.44) & (np.abs(x) < 0.10) & (np.abs(y + 0.04) < 0.10)
    below = neck
    if HD.PLANE:
        zp = HD.PLANE[0](y)
        below = neck & (z > zp - 0.015) & (z <= zp + 0.002)   # measured just below the join
    if neck.sum() > 100 and below.sum() > 50:
        gk = np.asarray(HD.NECK_MEDIAN, dtype=np.float32) / np.maximum(np.median(out[below], axis=0), 1e-5)
        wn = HD._smooth(1.44, 1.48, z[neck])[:, None]
        out[neck] = out[neck] * (1 - wn) + out[neck] * gk[None] * wn
        log("  body neck matched to the head's: gains %s" % np.round(gk, 3).tolist())
    # wrist bands: dark or grey outliers on the skin within 8.5 cm of each wrist
    if wrists:
        L = HD.low_pass_3d(P, out, skin, 0.006, 2)
        arm_zone = np.zeros_like(mask)
        for wp in wrists:
            arm_zone |= mask & (np.linalg.norm(P - np.asarray(wp)[None, None], axis=-1) < 0.085)
        sat = (out.max(-1) - out.min(-1)) / np.maximum(out.max(-1), 1e-4)
        band = arm_zone & ~red & ((HD._lum(out) < 0.55 * HD._lum(L)) | (HD._lum(out) > 1.6 * HD._lum(L)) | (sat < 0.25))
        out[band] = L[band] * (0.96 + 0.06 * T.fbm(P[band], 1 / 0.01, 2, seed=401))[:, None]
        log("  wrist bands painted out: %d texels" % band.sum())
    # the shirt a deeper red, as in the photo: its red channel's median to linear 0.30, hue kept
    sg = np.full(3, 0.30 / max(float(np.median(out[red][:, 0])), 1e-5), dtype=np.float32)
    out[red] = out[red] * sg[None]
    log("  shirt graded: gains %s" % np.round(sg, 3).tolist())
    # chest lettering, front of the shirt, over the generated faint print (which is cleaned off first)
    ink = _lettering()
    hh, ww = ink.shape
    cz, wid = 1.325, 0.28
    box = red | (mask & (np.abs(x) < wid / 2 + 0.02) & (np.abs(z - cz) < 0.07) & (N[..., 1] < -0.4) & (y < 0.0)
                 & (r > 1.2 * g))
    old_print = box & (np.abs(x) < wid / 2 + 0.02) & (np.abs(z - cz) < 0.07) & (N[..., 1] < -0.4) & (y < 0.0)
    Lr = HD.low_pass_3d(P, out, red, 0.008, 2)
    dark = old_print & (HD._lum(out) < 0.8 * HD._lum(Lr))
    out[dark] = Lr[dark]
    red = red | dark
    chest = red & (N[..., 1] < -0.45) & (np.abs(x) < wid / 2) & (np.abs(z - cz) < wid * hh / ww / 2) & (y < 0.0)
    u = (x[chest] + wid / 2) / wid
    v = 1 - ((z[chest] - cz) / (wid * hh / ww) + 0.5)
    a = HD._tile_sample(ink[..., None], u * 0.9999, v * 0.9999)[:, 0]
    wear = 0.75 + 0.25 * HD._smooth(-0.5, 0.5, T.fbm(P[chest], 1 / 0.004, 3, seed=402))
    a = a * wear
    out[chest] = out[chest] * (1 - 0.88 * a)[:, None] + np.array([0.016, 0.008, 0.008]) * (0.88 * a)[:, None]
    log("  chest lettering printed on %d texels" % chest.sum())
    out = T.dilate(out, mask, 8)
    p = HD._save_png(out, os.path.join(HD.DERIVED, "T_Rule_Body_BC.png"))
    node = _base_node(body)
    if node is not None:
        img = bpy.data.images.load(p, check_existing=False)
        img.colorspace_settings.name = "sRGB"
        node.image = img
    return p
