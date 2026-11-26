"""Canal Street: the market and vendor goods atlas (chinatown.md 13.5: "the market stall dressing" and "vendor goods
(one atlas)", made as one 2K page) and the remap that puts the small surfaces of the market and vendor props on it.

    venv/bin/python art/blender/assets/_chinatown_matlas.py        # draws art/out/textures/CT_MarketGoods/ (no Blender)

Why: the props were built with flat slots (one colour each, no texture) and up to 7 slots a mesh; in the market (a hero
space on the critical path, worst view 2) the produce read as coloured blobs and every slot is its own draw per ISM on
SM5. Here every such surface is a 256 px cell of one 2048 page (BC sRGB, N OpenGL, ORM), drawn procedurally with PIL and
numpy: orange peel, lemon, apple, leafy greens, stems, dried goods, crate plastics, kraft card, pallet and timber, crushed
ice, whole-fish skin, the vendor fabrics and plastics. After a prop is built, `remap()` moves every face whose slot is in
CELL_OF to the atlas slot M_CT_MarketGoods and maps its UVs into the cell (per face, 1 cell = 0.25 m), so a produce
display is one slot and the rest of the market and vendor props two or three.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))

from mi import paths  # noqa: E402

SET = "CT_MarketGoods"
SLOT = "M_CT_MarketGoods"
RES, CELL = 2048, 256
CELL_M = 0.25            # metres of surface one cell covers (1,024 px/m)
INSET = 6                # px kept clear inside each cell (mips, filtering)

# cell name: (column, row, base sRGB, roughness, metallic, pattern)
CELLS = {
    "orange": (0, 0, (0.80, 0.33, 0.04), 0.45, 0.0, "peel"),
    "lemon": (1, 0, (0.84, 0.70, 0.12), 0.42, 0.0, "peel"),
    "apple": (2, 0, (0.46, 0.06, 0.05), 0.35, 0.0, "streak"),
    "leaf": (3, 0, (0.16, 0.38, 0.09), 0.55, 0.0, "veins"),
    "stem": (4, 0, (0.74, 0.80, 0.62), 0.50, 0.0, "fibre"),
    "dried": (5, 0, (0.50, 0.34, 0.19), 0.85, 0.0, "specks"),
    "ice": (6, 0, (0.80, 0.87, 0.92), 0.12, 0.0, "ice"),
    "fish": (7, 0, (0.52, 0.55, 0.58), 0.28, 0.35, "scales"),
    "plasticBlue": (0, 1, (0.10, 0.28, 0.62), 0.50, 0.0, "plastic"),
    "plasticGreen": (1, 1, (0.12, 0.45, 0.22), 0.50, 0.0, "plastic"),
    "plasticOrange": (2, 1, (0.86, 0.36, 0.06), 0.50, 0.0, "plastic"),
    "plastic": (3, 1, (0.035, 0.035, 0.038), 0.45, 0.0, "plastic"),
    "card": (4, 1, (0.52, 0.38, 0.22), 0.86, 0.0, "fibre"),
    "pallet": (5, 1, (0.55, 0.43, 0.30), 0.80, 0.0, "grain"),
    "timber": (6, 1, (0.30, 0.22, 0.15), 0.78, 0.0, "grain"),
    "styro": (7, 1, (0.86, 0.86, 0.83), 0.80, 0.0, "beads"),
    "cloth": (0, 2, (0.18, 0.19, 0.22), 0.80, 0.0, "weave"),
    "clothLight": (1, 2, (0.70, 0.68, 0.64), 0.80, 0.0, "weave"),
    "fabricRed": (2, 2, (0.55, 0.07, 0.05), 0.80, 0.0, "weave"),
    "fabricBlue": (3, 2, (0.07, 0.20, 0.55), 0.80, 0.0, "weave"),
    "fabricGreen": (4, 2, (0.07, 0.30, 0.17), 0.80, 0.0, "weave"),
    "fabricYellow": (5, 2, (0.85, 0.58, 0.08), 0.80, 0.0, "weave"),
    "fabricPink": (6, 2, (0.85, 0.30, 0.45), 0.80, 0.0, "weave"),
    "fabricWhite": (7, 2, (0.86, 0.85, 0.80), 0.80, 0.0, "weave"),
    "ply": (0, 3, (0.62, 0.45, 0.30), 0.70, 0.0, "grain"),
    "alu": (1, 3, (0.60, 0.60, 0.61), 0.38, 1.0, "brushed"),
    "glasswin": (2, 3, (0.05, 0.06, 0.07), 0.08, 0.0, "plastic"),
}
# the builder slot key -> cell (keys of _chinatown_kit.materials); applied to SM_Prop_CT_* only, never to facades or signs
CELL_OF = {"orange": "orange", "yellow": "lemon", "apple": "apple", "leaf": "leaf", "stem": "stem", "grain": "dried",
           "ice": "ice", "fish": "fish", "plasticBlue": "plasticBlue", "plasticGreen": "plasticGreen",
           "plasticOrange": "plasticOrange", "plastic": "plastic", "card": "card", "pallet": "pallet", "timber": "timber",
           "styro": "styro", "cloth": "cloth", "clothLight": "clothLight", "fabricRed": "fabricRed", "fabricBlue": "fabricBlue",
           "fabricGreen": "fabricGreen", "fabricYellow": "fabricYellow", "fabricPink": "fabricPink", "fabricWhite": "fabricWhite",
           "ply": "ply", "alu": "alu", "glasswin": "glasswin"}


def _noise(rng, n, scale):
    """Smooth value noise in 0..1 at `scale` px."""
    g = max(2, int(n / scale) + 2)
    a = rng.random((g, g)).astype(np.float32)
    im = Image.fromarray((a * 255).astype(np.uint8)).resize((n + 2 * scale, n + 2 * scale), Image.BICUBIC)
    return np.asarray(im, np.float32)[scale:scale + n, scale:scale + n] / 255.0


def _cell(rng, base, pattern):
    """(albedo (n, n, 3) linear-ish 0..1 sRGB values, height (n, n) 0..1) of one cell."""
    n = CELL
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    b = np.array(base, np.float32)
    h = 0.5 * _noise(rng, n, 24) + 0.5 * _noise(rng, n, 6)
    v = 0.9 + 0.2 * _noise(rng, n, 40)
    if pattern == "peel":                       # dimpled citrus skin
        d = _noise(rng, n, 3)
        h = 0.6 * d + 0.4 * _noise(rng, n, 12)
        v = 0.86 + 0.22 * _noise(rng, n, 50) - 0.08 * (d > 0.72)
    elif pattern == "streak":                   # apple: red with paler vertical streaks
        st = _noise(rng, n, 5)[:, :1].repeat(n, 1).T * 0.5 + 0.5 * _noise(rng, n, 30)
        col = b[None, None] * (1 - 0.6 * st[..., None]) + np.array([0.72, 0.22, 0.06])[None, None] * 0.6 * st[..., None]
        return np.clip(col * (0.9 + 0.15 * _noise(rng, n, 40))[..., None], 0, 1), h
    elif pattern == "veins":                    # leaf with a midrib and veins
        mid = np.exp(-((x - 0.5) / 0.018) ** 2)
        vein = np.exp(-((np.mod(y * 6 + np.abs(x - 0.5) * 3, 1.0) - 0.5) / 0.05) ** 2) * (np.abs(x - 0.5) < 0.45)
        v = 0.85 + 0.25 * _noise(rng, n, 30) + 0.35 * mid + 0.18 * vein
        h = 0.5 + 0.3 * mid + 0.2 * vein - 0.2 * _noise(rng, n, 8)
    elif pattern == "fibre":
        v = 0.88 + 0.18 * _noise(rng, n, 2)[:, :] * 0.6 + 0.1 * _noise(rng, n, 30)
    elif pattern == "specks":                   # dried mushrooms, beans, dates: lumps of darker and paler
        k = _noise(rng, n, 10)
        v = 0.6 + 0.6 * k + 0.25 * (_noise(rng, n, 3) > 0.8)
        h = k
    elif pattern == "ice":                      # crushed ice: bright facets and dark gaps
        k = _noise(rng, n, 7)
        v = 0.75 + 0.35 * (k > 0.55) - 0.25 * (k < 0.25)
        h = k
    elif pattern == "scales":                   # whole fish: dark back to silver belly, a scale lattice
        sc = (np.sin(x * n / 5.0 + np.sin(y * n / 9.0)) * np.sin(y * n / 5.0)) * 0.5 + 0.5
        back = np.clip(1.0 - y * 1.6, 0, 1)
        col = b[None, None] * (1 - 0.55 * back[..., None]) + np.array([0.10, 0.13, 0.16])[None, None] * 0.55 * back[..., None]
        col = col * (0.9 + 0.15 * sc)[..., None]
        return np.clip(col, 0, 1), 0.5 + 0.3 * sc
    elif pattern == "plastic":
        v = 0.95 + 0.08 * _noise(rng, n, 40)
        h = 0.5 + 0.1 * _noise(rng, n, 10)
    elif pattern == "grain":                    # wood grain along u
        g = _noise(rng, n, 4)[:1].repeat(n, 0) * 0.6 + 0.4 * _noise(rng, n, 20)
        v = 0.8 + 0.35 * g
        h = g
    elif pattern == "beads":
        v = 0.95 + 0.08 * (_noise(rng, n, 2) > 0.6)
    elif pattern == "weave":                    # cloth: a plain weave and slubs
        w = 0.5 + 0.25 * np.sin(x * n * np.pi / 2.0) * np.sin(y * n * np.pi / 2.0)
        v = 0.86 + 0.14 * w + 0.12 * _noise(rng, n, 30)
        h = w
    elif pattern == "brushed":
        v = 0.92 + 0.1 * _noise(rng, n, 2)[:1].repeat(n, 0)
    return np.clip(b[None, None] * v[..., None], 0, 1), np.clip(h, 0, 1)


def build(seed=7):
    d = paths.ensure(paths.texture_set(SET))
    BC = np.zeros((RES, RES, 3), np.float32) + 0.2
    ORM = np.zeros((RES, RES, 3), np.float32)
    ORM[..., 0], ORM[..., 1] = 1.0, 0.7
    H = np.full((RES, RES), 0.5, np.float32)
    cells = {}
    for name, (c, r, base, rough, metal, pat) in CELLS.items():
        rng = np.random.default_rng(seed + sum(map(ord, name)))
        col, h = _cell(rng, base, pat)
        x0, y0 = c * CELL, r * CELL
        BC[y0:y0 + CELL, x0:x0 + CELL] = col
        H[y0:y0 + CELL, x0:x0 + CELL] = h
        ORM[y0:y0 + CELL, x0:x0 + CELL, 0] = 0.85 + 0.15 * h
        ORM[y0:y0 + CELL, x0:x0 + CELL, 1] = np.clip(rough + 0.08 * (h - 0.5), 0.04, 1)
        ORM[y0:y0 + CELL, x0:x0 + CELL, 2] = metal
        u0, v0 = (x0 + INSET) / RES, 1 - (y0 + CELL - INSET) / RES
        u1, v1 = (x0 + CELL - INSET) / RES, 1 - (y0 + INSET) / RES
        cells[name] = {"px": [x0, y0, CELL, CELL], "uv": [round(u0, 6), round(v0, 6), round(u1, 6), round(v1, 6)],
                       "base": list(base), "roughness": rough, "metallic": metal, "pattern": pat}
    gy, gx = np.gradient(H * 3.0)
    N = np.stack([-gx, gy, np.ones_like(H)], -1)
    N /= np.linalg.norm(N, axis=-1, keepdims=True)
    files = {"BC": "T_%s_BC.png" % SET, "N": "T_%s_N.png" % SET, "ORM": "T_%s_ORM.png" % SET, "H": "T_%s_H.png" % SET}
    Image.fromarray((BC * 255 + 0.5).astype(np.uint8), "RGB").save(os.path.join(d, files["BC"]), optimize=True)
    Image.fromarray(((N * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8), "RGB").save(os.path.join(d, files["N"]), optimize=True)
    Image.fromarray((ORM * 255 + 0.5).astype(np.uint8), "RGB").save(os.path.join(d, files["ORM"]), optimize=True)
    Image.fromarray((H * 65535).astype(np.uint16)).save(os.path.join(d, files["H"]))
    info = {"kind": "atlas", "set": SET, "resolution": [RES, RES], "cell_px": CELL, "cell_m": CELL_M, "files": files,
            "convention": {"BC": "sRGB", "N": "OpenGL (+Y up)", "ORM": "linear AO, roughness, metallic", "H": "16-bit height 0..1"},
            "cells": cells, "albedo_mean": [round(float(v), 4) for v in BC.reshape(-1, 3).mean(0)],
            "roughness_mean": round(float(ORM[..., 1].mean()), 3), "metallic_mean": round(float(ORM[..., 2].mean()), 3),
            "texel_density_px_per_m": CELL / CELL_M,
            "note": "Canal Street market and vendor goods atlas (assets/_chinatown_matlas.py): one 2K page replaces the flat slots of "
                    "the market and vendor props. Each face of a remapped slot has its UVs inside one cell (uv rect, v up)."}
    with open(os.path.join(d, "set.json"), "w") as f:
        json.dump(info, f, indent=1, sort_keys=True)
    return d, cells


def material(ctx):
    """The atlas slot's material (built from the set on disk; drawn first when missing)."""
    from mi import mat
    d = paths.texture_set(SET)
    if not os.path.exists(os.path.join(d, "set.json")) or getattr(ctx.args, "bake", False):
        build()
    m = mat.from_texture_set(d, name=SLOT, tile_m=CELL_M, alpha="splash", dirt_color=(0.06, 0.055, 0.05), macro=0.0)
    if SET not in ctx.sets:
        ctx.sets.append(SET)
    return m


def remap(ob, M, atlas_mat):
    """Move every face whose material is one of CELL_OF's slots onto the atlas slot, its UVs into the slot's cell.
    Per face: the face's own UVs (in metres / tile, from the builder) are shifted to start at 0, scaled so a cell spans
    CELL_M metres (shrunk when the face is larger than a cell) and placed inside the cell's inset rectangle. Returns the
    number of faces moved."""
    with open(os.path.join(paths.texture_set(SET), "set.json")) as f:
        cells = json.load(f)["cells"]
    me = ob.data
    mats = list(me.materials)
    by_name = {m.name: k for k, m in M.items() if m is not None}
    cell_of_mat = {}
    for i, m in enumerate(mats):
        key = by_name.get(m.name) if m is not None else None
        if key in CELL_OF:
            cell_of_mat[i] = cells[CELL_OF[key]]["uv"]
    if not cell_of_mat:
        return 0
    keep = [i for i in range(len(mats)) if i not in cell_of_mat]
    new = [mats[i] for i in keep] + [atlas_mat]
    remap_idx = {i: k for k, i in enumerate(keep)}
    aidx = len(new) - 1
    npoly = len(me.polygons)
    mi = np.empty(npoly, np.int32)
    me.polygons.foreach_get("material_index", mi)
    ls = np.empty(npoly, np.int32)
    me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(npoly, np.int32)
    me.polygons.foreach_get("loop_total", lt)
    uvl = me.uv_layers[0].data
    uv = np.empty(len(me.loops) * 2, np.float32)
    uvl.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    moved = 0
    for p in range(npoly):
        i = int(mi[p])
        if i in cell_of_mat:
            u0, v0, u1, v1 = cell_of_mat[i]
            sl = slice(int(ls[p]), int(ls[p] + lt[p]))
            f = uv[sl] - uv[sl].min(axis=0)
            tm = mats[i].get("mi_tile_m", 2.0) if hasattr(mats[i], "get") else 2.0
            tm = np.atleast_1d(np.asarray(tm, dtype=np.float64))
            f = f * (np.array([tm[0], tm[-1]]) / CELL_M)
            ext = float(f.max()) if f.size else 0.0
            if ext > 0.98:
                f = f * (0.98 / ext)
            uv[sl, 0] = u0 + f[:, 0] * (u1 - u0)
            uv[sl, 1] = v0 + f[:, 1] * (v1 - v0)
            mi[p] = aidx
            moved += 1
        else:
            mi[p] = remap_idx[i]
    uvl.foreach_set("uv", uv.ravel())
    me.materials.clear()
    for m in new:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", mi)
    me.update()
    return moved


if __name__ == "__main__":
    d, cells = build()
    print(d, len(cells), "cells")
