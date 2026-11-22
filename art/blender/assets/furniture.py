"""Street furniture and yard structures (SM_Furn_*), modelled at real size on tiling scan sets.

Street: dumpster, mailbox, newspaper box, traffic barrel and cone, jersey barrier (3 m), barricade, bus shelter,
trash-bag piles, milk crates, pallet and pallet stack, sandbag wall, oil drums, tyre stacks, shopping cart,
mattress, parking meter, sign post, bollard.
Structures: the sidewalk shed and its stair (spec 05-level 2.9.3), chain-link panels, end posts, gate leaves and
gateways in the level's heights (alpha-tested mesh card TS_ChainLink_Galv on real pipe frames), the cage plinth,
basketball hoop and bleachers, the parking attendant booth, the cobra-head street lamp and the court light mast,
the billboard, roll-up doors and the cinder-block wall modules of the auto body shop with lintels and a steel door.

Sizes and colours: docs/unreal/spec/05b-props.md 2.6 to 2.9 (catalogue ids in each asset's notes) and
05-level.md 2.6 / 2.9 / 2.10. Frames (05b 4.1): props pivot at the footprint centre on the ground, long axis +X,
the front (web +Z) toward -Y. Structures and wall pieces: west end (bottom-left of the outer face), running +X.
Painted graphics (ads, banners, labels, dials) are flat slots M_Sign_<Name> with 0..1 UVs on the face; stencils
and scrawls are left to decals.

    build.py build furniture --bake --export      (--bake only the first time: five small procedural sets)
    build.py build furniture --preview --only furniture_street,furniture_structures
"""
import math
import os

import bpy
import numpy as np

from assets.facade import bar, bx, rod, sub
from assets.street import Waves, sstep
from mi import geo, mat, paths, render, scene, steel

FAMILY = {"name": "furniture", "description": "Street furniture and yard structures: bins, barriers, shelter, shed, fences, court, booth, lamps, billboard, garage walls"}

X, Y, Z = np.eye(3)
GALV, RUBBER = "TS_Galvanised_Aged", "TS_Rubber_Aged"
CL_SET = "TS_ChainLink_Galv"
CL_D = 0.05 * math.sqrt(2.0)             # 2 in (50 mm) mesh: wires 50 mm apart, diamonds 70.7 mm across
CL_TILE = 6 * CL_D                       # 0.424 m: six diamonds, both wire families wrap exactly

SLOT_META = {
    "MI_Steel_DumpsterGreen": {"set": "TS_Steel_ScanPanelTeal", "workflow": "tiling", "tint": [0.07, 0.48, 0.33], "note": "#1f5a3a"},
    "MI_Steel_MailBlue": {"set": "TS_Steel_ScanPaintBlue", "workflow": "tiling", "tint": [0.65, 1.55, 4.2], "note": "#1f4f9a"},
    "MI_Steel_PaintRed": {"set": "TS_Steel_ScanPaintWhite", "workflow": "tiling", "tint": [1.1, 0.066, 0.096], "note": "#b3261e"},
    "MI_Steel_PaintYellow": {"set": "TS_Steel_ScanPaintWhite", "workflow": "tiling", "tint": [2.1, 1.85, 0.075], "note": "#f2c21a"},
    "MI_Steel_PaintBlack": {"set": "TS_Steel_ScanPaintGrey", "workflow": "tiling", "tint": [0.07, 0.07, 0.075]},
    "MI_Steel_IronDark": {"set": "TS_Steel_ScanPaintGrey", "workflow": "tiling", "tint": [0.10, 0.12, 0.22], "note": "#23262a"},
    "MI_Steel_ElGreen": {"set": "TS_Steel_ScanPaintGreen", "workflow": "tiling", "tint": [0.30, 0.32, 0.55], "note": "#1f2a26"},
    "MI_Steel_PaintWhiteClean": {"workflow": "tiling", "note": "clean neutral white enamel #e6e4dc (booth, backboard, barricade)"},
    "MI_Steel_PaintCream": {"set": "TS_Steel_ScanPaintWhite", "workflow": "tiling", "tint": [1.7, 2.3, 3.4], "note": "#e6e4dc"},
    "MI_Steel_PaintOrange": {"set": "TS_Steel_ScanPaintWhite", "workflow": "tiling", "tint": [1.75, 0.25, 0.07], "note": "#d9521a"},
    "MI_Steel_DrumBlue": {"set": "TS_Steel_ScanPaintBlue", "workflow": "tiling", "tint": [0.65, 1.55, 4.2]},
    "MI_Steel_DrumGrey": {"set": "TS_Steel_ScanPaintGrey", "workflow": "tiling", "tint": [0.75, 0.95, 1.6], "note": "#8d949a"},
    "MI_Plywood_HunterGreen": {"set": "TS_Plywood_ScanLauan", "workflow": "tiling", "tint": [0.17, 0.93, 0.83]},
    "MI_Block_PaintedGrey": {"set": "TS_Block_ScanPainted", "workflow": "tiling", "tint": [0.61, 0.74, 1.06],
                             "note": "#8a8880; UVs in metres from the module pivot: use world-aligned UVs so the bond runs through"},
    "MI_Block_DadoTeal": {"set": "TS_Block_ScanPainted", "workflow": "tiling", "tint": [0.05, 0.16, 0.21], "note": "#27414b dado"},
    "MI_Block_DadoYellow": {"set": "TS_Block_ScanPainted", "workflow": "tiling", "tint": [2.1, 1.6, 0.05], "note": "dado stripe"},
    "MI_Fabric_Ticking": {"set": "TS_Fabric_ScanCanvas", "workflow": "tiling", "tint": [1.7, 1.1, 0.59],
                          "note": "beige-grey ticking; the blue stripe and stains belong in a detail layer"},
    "MI_Plastic_CrateBlue": {"set": "TS_Plastic_White", "workflow": "tiling", "tint": [0.03, 0.12, 0.47]},
    "MI_Plastic_CrateRed": {"set": "TS_Plastic_White", "workflow": "tiling", "tint": [0.62, 0.03, 0.02]},
    "MI_Plastic_CrateGreen": {"set": "TS_Plastic_White", "workflow": "tiling", "tint": [0.02, 0.14, 0.06]},
    "MI_Plastic_BagBlack": {"set": "TS_Plastic_Black", "workflow": "tiling", "tint": [0.4, 0.4, 0.42], "note": "refuse sacks: lower the roughness in Unreal"},
    "MI_Plastic_BagGrey": {"set": "TS_Plastic_White", "workflow": "tiling", "tint": [0.81, 0.81, 0.75]},
    "MI_ChainLink_Galv": {"workflow": "tiling", "alpha": "BC alpha is the opacity mask: masked (clip 0.5), two-sided, not Nanite"},
    "MI_Glass_Store": {"workflow": "glass", "note": "translucent, not Nanite"},
    "MI_Metal_Chrome": {"workflow": "flat"},
    "MI_Lamp_Lens": {"workflow": "flat", "note": "lamp lens: emissive in Unreal when lit (colour per the catalogue hint)"},
    "MI_Interior_Dark": {"workflow": "flat"},
}

SIGNS = {   # slot: (flat colour, what the face shows) -- every face is one 0..1 square, u left to right, v up
    "BusShelter": ((0.006, 0.006, 0.008), "the IPX one-sheet (05b 2.11 ipx_ad), 1.14 x 1.72, both faces of the ad box"),
    "BusFlag": ((0.75, 0.75, 0.78), "BUS STOP / NO STANDING flag, 0.26 x 0.36"),
    "Billboard": ((0.006, 0.0065, 0.008), "the IPX billboard face 9.0 x 4.1 (05b 2.11): lozenge, gold rule, IPX.EXCHANGE"),
    "LotBooth": ((0.01, 0.01, 0.01), "PARK / 24 HOURS, gold on black, 1.6 x 0.56"),
    "LotRates": ((0.8, 0.8, 0.78), "RATES tariff board 0.5 x 0.65"),
    "ShedBanner_Chicken": ((0.89, 0.54, 0.01), "GOLDEN BIRD CHICKEN, red on yellow, 4.9 x 0.78"),
    "ShedBanner_Liquor": ((0.006, 0.006, 0.007), "WINES & LIQUORS, red on black, 4.9 x 0.78"),
    "ShedBanner_Nails": ((0.023, 0.005, 0.013), "LUCKY NAILS, pink on dark plum, 4.9 x 0.78"),
    "SignPost": ((0.8, 0.8, 0.8), "NO PARKING ANYTIME (or BUS STOP / ONE WAY), 0.32 x 0.44"),
    "Newspaper": ((0.6, 0.6, 0.58), "QUEENS NIGHT LEDGER front page behind the glass, 0.33 x 0.41"),
    "Mailbox": ((0.008, 0.02, 0.08), "MAIL label, white on navy, 0.36 x 0.27"),
    "MeterDial": ((0.7, 0.7, 0.68), "meter dial: red sector, 1 HR, 25 cents, 0.10 x 0.15, both faces"),
}
for _k, (_c, _d) in SIGNS.items():
    SLOT_META["M_Sign_" + _k] = {"workflow": "sign", "uv": "0..1 over the face", "note": _d}


# ------------------------------------------------------------------------------------------------------ materials

def chainlink_set(res=1024):
    """Write the chain-link tiling set (BC with the opacity in alpha, N, ORM) once: 50 mm diamond mesh of
    3.76 mm (9 gauge) galvanised wire, over/under at every crossing."""
    from PIL import Image
    d = paths.texture_set(CL_SET)
    js = os.path.join(d, "set.json")
    if os.path.exists(js):
        return d
    os.makedirs(d, exist_ok=True)
    n, L, s, r = res, CL_TILE, 0.05, 0.00188
    pix = L / n
    t = (np.arange(n) + 0.5) * pix
    x, y = np.meshgrid(t, t[::-1])                       # row 0 is the top of the image (v = 1)
    a, b = (x + y) / math.sqrt(2), (x - y) / math.sqrt(2)
    ia, ib = np.floor(a / s + 0.5), np.floor(b / s + 0.5)
    pa, pb = np.abs(a - ia * s), np.abs(b - ib * s)      # distance to the nearest wire of each family
    ha = np.sqrt(np.clip(1 - (pa / r) ** 2, 0, 1))
    hb = np.sqrt(np.clip(1 - (pb / r) ** 2, 0, 1))
    over = ((ia + ib) % 2) == 0
    near = np.exp(-(np.minimum(pa, pb) / (2.2 * r)) ** 2) * (np.maximum(pa, pb) < 3 * r)
    za = r * ha + np.where(over, 0.8, -0.8) * r * near * (ha > 0)
    zb = r * hb + np.where(over, -0.8, 0.8) * r * near * (hb > 0)
    h = np.maximum(np.where(ha > 0, za, -9), np.where(hb > 0, zb, -9))
    h = np.where(h < -1, 0.0, h + r)
    cov = np.clip((r - np.minimum(pa, pb)) / pix + 0.5, 0, 1)
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * pix)
    dy = (np.roll(h, 1, 0) - np.roll(h, -1, 0)) / (2 * pix)
    nv = np.stack([-dx, -dy, np.ones_like(h)], -1)
    nv /= np.linalg.norm(nv, axis=-1, keepdims=True)
    rng = np.random.default_rng(7)
    k = np.fft.fftfreq(n)[:, None] ** 2 + np.fft.fftfreq(n)[None, :] ** 2
    noise = np.real(np.fft.ifft2(np.fft.fft2(rng.normal(size=(n, n))) * np.exp(-k * 900)))
    noise = (noise - noise.mean()) / (noise.std() + 1e-9)
    lin = np.stack([0.40, 0.42, 0.43])[None, None, :] * (1 + 0.10 * noise[..., None])
    lin = lin * (0.55 + 0.45 * np.maximum(ha, hb))[..., None]
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.clip(lin, 0, 1) ** (1 / 2.4) - 0.055)
    bc = np.concatenate([srgb, cov[..., None]], -1)
    ao = 0.55 + 0.45 * np.where(near > 0.3, 0.6, 1.0) * np.maximum(ha, hb) ** 0.5
    orm = np.stack([ao, np.clip(0.55 + 0.06 * noise, 0, 1), np.full_like(h, 1.0)], -1)
    u8 = lambda im: Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8))
    files = {"BC": "T_%s_BC.png" % CL_SET, "N": "T_%s_N.png" % CL_SET, "ORM": "T_%s_ORM.png" % CL_SET}
    u8(bc).save(os.path.join(d, files["BC"]))
    u8(nv * 0.5 + 0.5).save(os.path.join(d, files["N"]))
    u8(orm).save(os.path.join(d, files["ORM"]))
    import json
    with open(js, "w") as f:
        json.dump({"set": CL_SET, "kind": "tiling", "surface": "chainlink", "tile_m": [CL_TILE, CL_TILE],
                   "resolution": [n, n], "texel_density_px_per_m": round(n / CL_TILE, 1), "files": files,
                   "seamless": True, "alpha": "BC alpha = opacity (masked, clip 0.5, two-sided)",
                   "albedo_mean": [round(float(v), 4) for v in (lin * cov[..., None]).reshape(-1, 3).sum(0) / cov.sum()],
                   "roughness_mean": round(float(orm[..., 1].mean()), 4), "metallic_mean": 1.0,
                   "params": {"mesh_m": s, "wire_d_m": 2 * r}}, f, indent=1)
    return d


def chainlink_material():
    d = chainlink_set()
    m = mat.from_texture_set(d, name="MI_ChainLink_Galv", tile_m=(CL_TILE, CL_TILE), alpha="splash", macro=0.0,
                             dirt_color=(0.10, 0.08, 0.06), leak_color=(0.22, 0.10, 0.04))
    m["mi_tile_m"] = (CL_TILE, CL_TILE)
    bsdf = mat.principled(m)
    for nd in m.node_tree.nodes:
        if nd.bl_idname == "ShaderNodeTexImage" and nd.image and "_BC" in nd.image.name:
            m.node_tree.links.new(nd.outputs["Alpha"], bsdf.inputs["Alpha"])
            break
    return m


def materials(ctx):
    sc, ts = ctx.scan_set, ctx.tiling_set
    soot = (0.03, 0.028, 0.026)
    rust = dict(blend="TS_Steel_ScanRust", leak_color=(0.24, 0.10, 0.035), leak_rough=0.1, dirt_color=soot, alpha="splash")
    M = {}
    M["green"] = sc("TS_Steel_ScanPanelTeal", slot="MI_Steel_DumpsterGreen", tint=(0.07, 0.48, 0.33), blend_start=0.45, **rust)
    M["blue"] = sc("TS_Steel_ScanPaintBlue", slot="MI_Steel_MailBlue", tint=(0.65, 1.55, 4.2), blend_start=0.5, **rust)
    M["red"] = sc("TS_Steel_ScanPaintWhite", slot="MI_Steel_PaintRed", tint=(1.1, 0.066, 0.096), blend_start=0.5, **rust)
    M["yellow"] = sc("TS_Steel_ScanPaintWhite", slot="MI_Steel_PaintYellow", tint=(2.1, 1.85, 0.075), blend_start=0.5, **rust)
    M["black"] = sc("TS_Steel_ScanPaintGrey", slot="MI_Steel_PaintBlack", tint=(0.07, 0.07, 0.075), blend_start=0.45, **rust)
    M["dark"] = sc("TS_Steel_ScanPaintGrey", slot="MI_Steel_IronDark", tint=(0.10, 0.12, 0.22), blend_start=0.5, **rust)
    M["elgreen"] = sc("TS_Steel_ScanPaintGreen", slot="MI_Steel_ElGreen", tint=(0.30, 0.32, 0.55), blend_start=0.4, **rust)
    # white enamel (booth, hoop backboard, barricade): the clean neutral procedural set from assets/gaps.py when it is
    # baked (build.py build gaps --bake), else the tinted scan, which reads warm and rust-spotted
    if os.path.exists(os.path.join(paths.texture_set("TS_Steel_PaintWhiteClean"), "set.json")):
        M["cream"] = ts("TS_Steel_PaintWhiteClean", "painted_steel", tile_m=1.0, res=1024,
                        **{"Paint Color": (0.74, 0.74, 0.72), "Paint Roughness": 0.40, "Chipping": 0.10, "Rust": 0.03,
                           "Chalking": 0.30, "Old Coat": (0.50, 0.51, 0.51), "Primer Color": (0.42, 0.43, 0.43)})
    else:
        M["cream"] = sc("TS_Steel_ScanPaintWhite", slot="MI_Steel_PaintCream", tint=(1.7, 2.3, 3.4), blend_start=0.8, **rust)
    M["orange"] = sc("TS_Steel_ScanPaintWhite", slot="MI_Steel_PaintOrange", tint=(1.75, 0.25, 0.07), blend_start=0.5, **rust)
    M["drumBlue"] = sc("TS_Steel_ScanPaintBlue", slot="MI_Steel_DrumBlue", tint=(0.65, 1.55, 4.2), blend_start=0.35, **rust)
    M["drumGrey"] = sc("TS_Steel_ScanPaintGrey", slot="MI_Steel_DrumGrey", tint=(0.75, 0.95, 1.6), blend_start=0.35, **rust)
    M["galv"] = ts(GALV, "galvanised", tile_m=2.0, res=1024, Age=0.55, Rust=0.15)
    M["rubber"] = ts(RUBBER, "rubber", tile_m=1.0, res=1024, Age=0.5)
    M["pOrange"] = ts("TS_Plastic_Orange", "plastic", tile_m=1.0, res=1024, Color=(0.80, 0.13, 0.012), Roughness=0.45,
                      **{"Sun Fade": 0.35, "Scratches": 0.5})
    M["pWhite"] = ts("TS_Plastic_White", "plastic", tile_m=1.0, res=1024, Color=(0.72, 0.72, 0.70), Roughness=0.5,
                     **{"Sun Fade": 0.2, "Scratches": 0.45})
    M["pBlack"] = ts("TS_Plastic_Black", "plastic", tile_m=1.0, res=1024, Color=(0.011, 0.011, 0.012), Roughness=0.38,
                     **{"Sun Fade": 0.25, "Scratches": 0.5})
    pw = paths.texture_set("TS_Plastic_White")
    for key, tint in (("crateBlue", (0.03, 0.12, 0.47)), ("crateRed", (0.62, 0.03, 0.02)), ("crateGreen", (0.02, 0.14, 0.06)),
                      ("bagGrey", (0.81, 0.81, 0.75)), ("bagBlack", None)):
        slot = "MI_Plastic_" + key[0].upper() + key[1:]
        if tint is None:
            M[key] = ts("TS_Plastic_Black", "plastic", tile_m=1.0, res=1024, slot=slot, mat_kw=dict(tint=(0.4, 0.4, 0.42)),
                        Color=(0.011, 0.011, 0.012), Roughness=0.38, **{"Sun Fade": 0.25, "Scratches": 0.5})
            M[key]["mi_tint"] = (0.4, 0.4, 0.42)
            continue
        M[key] = ts("TS_Plastic_White", "plastic", tile_m=1.0, res=1024, slot=slot, mat_kw=dict(tint=tint),
                    Color=(0.72, 0.72, 0.70), Roughness=0.5, **{"Sun Fade": 0.2, "Scratches": 0.45}) if os.path.isdir(pw) else M["pWhite"]
        M[key]["mi_tint"] = tint
    M["conc"] = sc("TS_Concrete_ScanRough", alpha="splash", dirt_color=(0.06, 0.055, 0.048), macro=0.12)
    M["ply"] = sc("TS_Plywood_ScanLauan", alpha="splash", dirt_color=soot, macro=0.1)
    M["plyGreen"] = sc("TS_Plywood_ScanLauan", slot="MI_Plywood_HunterGreen", tint=(0.17, 0.93, 0.83), alpha="splash", dirt_color=soot)
    M["plank"] = sc("TS_Wood_ScanPlankNew", alpha="splash", dirt_color=soot, macro=0.12)
    M["pallet"] = sc("TS_Wood_ScanPallet", alpha="splash", dirt_color=soot, macro=0.12)
    M["burlap"] = sc("TS_Fabric_ScanBurlap", alpha="splash", dirt_color=(0.10, 0.08, 0.06), macro=0.15)
    M["ticking"] = sc("TS_Fabric_ScanCanvas", slot="MI_Fabric_Ticking", tint=(1.7, 1.1, 0.59), alpha="splash",
                      dirt_color=(0.16, 0.12, 0.07), leak_color=(0.30, 0.20, 0.08), macro=0.2)
    M["block"] = sc("TS_Block_ScanPainted", slot="MI_Block_PaintedGrey", tint=(0.61, 0.74, 1.06), alpha="splash", dirt_color=soot,
                    leak_color=(0.05, 0.045, 0.04), macro=0.12)
    M["dadoTeal"] = sc("TS_Block_ScanPainted", slot="MI_Block_DadoTeal", tint=(0.05, 0.16, 0.21), alpha="splash", dirt_color=soot)
    M["dadoYellow"] = sc("TS_Block_ScanPainted", slot="MI_Block_DadoYellow", tint=(2.1, 1.6, 0.05), alpha="splash", dirt_color=soot)
    M["shutter"] = sc("TS_Shutter_ScanGrey", alpha="splash", dirt_color=soot, leak_color=(0.22, 0.10, 0.04))
    M["corrugated"] = sc("TS_Corrugated_ScanPeeling", alpha="splash", dirt_color=soot)
    M["chain"] = chainlink_material()
    M["glass"] = mat.make("MI_Glass_Store", "glass", Film=0.10)
    M["chrome"] = mat.flat("MI_Metal_Chrome", (0.77, 0.77, 0.77), 0.10, 1.0)
    M["lens"] = mat.flat("MI_Lamp_Lens", (0.80, 0.78, 0.72), 0.15, 0.0)
    M["interior"] = mat.flat("MI_Interior_Dark", (0.022, 0.021, 0.02), 0.9)
    for k, (c, _d) in SIGNS.items():
        M["sign" + k] = mat.sign_face(k, c, 0.45)                # T_Sign_<Key>_* from signs.py, else flat
    return M


# ------------------------------------------------------------------------------------------------------- helpers

def B(seed=0, step=0.15):
    return steel.Builder(step=step, seed=seed)


def grain(axis):
    """Timber: the scans' grain runs along u; keep it along the board (`axis` 0, 1, 2)."""
    e = np.eye(3)
    return dict(vdir=e[(axis + 1) % 3], fdir=e[(axis + 2) % 3])


def board(b, lo, hi, slot, ch=0.004):
    lo, hi = np.minimum(lo, hi), np.maximum(lo, hi)
    ax = int(np.argmax(np.asarray(hi) - np.asarray(lo)))
    return bx(b, lo, hi, slot, ch=ch, pin=False, axis=ax, **grain(ax))


def box(b, lo, hi, slot, ch=0.004, **kw):
    return bx(b, lo, hi, slot, ch=ch, pin=False, **kw)


def lathe(b, prof, slot, seg=32, loc=(0, 0, 0), rot=(0, 0, 0), closed=False, scale=(1, 1, 1)):
    """Revolve a (radius, z) profile (bottom to top on the outside) and take it into the builder."""
    ob = geo.revolve(prof, seg, closed=closed)
    geo.transform(ob, loc=loc, rot=rot, scale=scale)
    return b.absorb(ob, slot)


def card(b, o, du, dv, slot, step=0.5, sign=False, **kw):
    """Single-sided quad grid from corner o along du and dv; it faces du x dv. sign=True: the face is one
    0..1 square (u along du, v along dv) for a M_Sign_ slot whose mi_tile_m is the face size."""
    o, du, dv = (np.asarray(v, dtype=np.float64) for v in (o, du, dv))
    nu = max(1, int(math.ceil(np.linalg.norm(du) / step)))
    nv = max(1, int(math.ceil(np.linalg.norm(dv) / step)))
    s, t = np.linspace(0, 1, nu + 1), np.linspace(0, 1, nv + 1)
    V = o + s[None, :, None] * du + t[:, None, None] * dv
    idx = lambda r, c: r * (nu + 1) + c
    r_, c_ = np.meshgrid(np.arange(nv), np.arange(nu), indexing="ij")
    q = np.stack([idx(r_, c_), idx(r_, c_ + 1), idx(r_ + 1, c_ + 1), idx(r_ + 1, c_)], -1).reshape(-1, 4)
    kw.setdefault("kind", b.OTHER)
    if sign:
        kw.update(uv_off=(0.0, 0.0), uv_org=o, vdir=dv, fdir=du)
    return b._add(V.reshape(-1, 3), q.ravel(), np.full(len(q), 4), slot, None, **kw)


def sign_slot(M, key, w, h):
    M["sign" + key]["mi_tile_m"] = (float(w), float(h))


def tube_path(b, pts, r, slot, n=10):
    """Straight tube segments through points (mitred by overlap)."""
    for p0, p1 in zip(pts[:-1], pts[1:]):
        rod(b, p0, p1, r, slot, n=n)


def pipe(b, pts, r, slot, bend=0.0, seg=12):
    return b.absorb(geo.pipe([tuple(p) for p in pts], r, seg, bend_radius=bend), slot)


def blob(b, size, loc, slot, seed, rot=0.0, lumps=0.025, flat=0.30, res=(28, 14), tilt=(0.0, 0.0), freq=5.0):
    """Soft lump (refuse sack, sandbag core): a squashed sphere with a flattened base and creases."""
    ob = geo.sphere(0.5, res[0], res[1])
    co, _ = geo.arrays(ob)
    co *= np.asarray(size)
    co[:, 2] = np.maximum(co[:, 2], -flat * size[2])
    co[:, 2] -= co[:, 2].min()
    geo.set_verts(ob, co)
    geo.displace(ob, lumps, freq, seed)
    geo.displace(ob, lumps * 0.3, freq * 3.2, seed + 3)
    geo.transform(ob, loc=loc, rot=(tilt[0], tilt[1], rot))
    return b.absorb(ob, slot)


def pillow(b, size, loc, slot, seed, rot=0.0):
    """Filled sack (sandbag): a box rounded hard, thinning toward its tucked ends, with creases."""
    sx, sy, sz = size
    ob = geo.box(size, bevel=min(size) * 0.42, segments=3)
    geo.densify(ob, 0.035)
    co, _ = geo.arrays(ob)
    u, v = np.clip(2 * co[:, 0] / sx, -1, 1), np.clip(2 * co[:, 1] / sy, -1, 1)
    co[:, 2] = sz / 2 + (co[:, 2] - sz / 2) * (1 - 0.45 * u ** 4) * (1 - 0.25 * v ** 4)
    co[:, 2] -= co[:, 2].min()
    geo.set_verts(ob, co)
    geo.displace(ob, 0.014, 6.0, seed)
    geo.displace(ob, 0.004, 22.0, seed + 5)
    geo.transform(ob, loc=loc, rot=(0, 0, rot))
    return b.absorb(ob, slot)


def fit(b, size):
    """Scale everything built so far to the catalogue box `size`, footprint centre at the origin, base on z = 0."""
    V = np.concatenate([p["v"] for p in b.parts])
    lo, hi = V.min(0), V.max(0)
    s = np.asarray(size, dtype=np.float64) / np.maximum(hi - lo, 1e-9)
    c = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
    for p in b.parts:
        p["v"] = (p["v"] - c) * s
        p["uv_org"] = (p["uv_org"] - c) * s
    b.leaks = [tuple((np.asarray(l) - c) * s) for l in b.leaks]


def clip_rect(poly, x0, x1, z0, z1):
    """Sutherland-Hodgman: a 2D polygon [(x, z)] clipped to a rectangle."""
    def cut(P, keep, inter):
        out = []
        for i in range(len(P)):
            a, c = P[i - 1], P[i]
            if keep(c):
                if not keep(a):
                    out.append(inter(a, c))
                out.append(c)
            elif keep(a):
                out.append(inter(a, c))
        return out
    P = list(poly)
    for k, v, ge in ((0, x0, True), (0, x1, False), (1, z0, True), (1, z1, False)):
        if not P:
            break
        keep = (lambda p, k=k, v=v, ge=ge: p[k] >= v if ge else p[k] <= v)
        def inter(a, c, k=k, v=v):
            t = (v - a[k]) / (c[k] - a[k])
            return (a[0] + t * (c[0] - a[0]), a[1] + t * (c[1] - a[1]))
        P = cut(P, keep, inter)
    return P


def stripes(b, x0, x1, z0, z1, y, slot, width=0.10, pitch=0.20, angle=45.0, face=-1):
    """Diagonal paint stripes on a face at y (face -1: the face looks -Y), as thin plates."""
    t = math.tan(math.radians(angle))
    h = z1 - z0
    k = x0 - h / t - pitch
    while k < x1:
        poly = [(k, z0), (k + width, z0), (k + width + h / t, z1), (k + h / t, z1)]
        P = clip_rect(poly, x0, x1, z0, z1)
        P = [p for i, p in enumerate(P) if math.dist(p, P[i - 1]) > 1e-5] if P else P
        area = 0.5 * sum(P[i - 1][0] * P[i][1] - P[i][0] * P[i - 1][1] for i in range(len(P))) if len(P) >= 3 else 0.0
        if area > 1e-5:
            pts = [(px, y, pz) for px, pz in P]
            if face > 0:
                pts = pts[::-1]
            b.poly_plate(pts, 0.0015, slot)
        k += pitch


def weather(ctx, b, ob, key, ground=True, ao=0.10, dirt=1.0, wear=1.0):
    """Wear mask from the parts: R cavities and grime, G knocked edges, B rust runs from the leak points and
    connections, A splash-back at the foot."""
    W = b.loops(ob, ao=ao, rays=6) if ao else b.loops(ob, ao=None)
    P, N = W.P, W.N
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    rng = ctx.rng("wear", key)
    a = Waves(rng, 0.45).u(x + 0.7 * y, z + 0.3 * x)
    bb = Waves(rng, 1.6).u(x - 0.5 * y, z)
    c = Waves(rng, 0.15).u(x + y, z * 0.15)
    up = np.clip(N[:, 2], 0, 1)
    soft = np.isin(W.slot, [i for i, k in enumerate(W.names) if k.startswith(("glass", "sign", "lens", "chain", "interior"))])
    R = 0.07 + 0.14 * (a - 0.5) + 0.32 * W.concave + 0.55 * W.ao + 0.20 * up * bb
    G = 0.9 * W.convex * sstep(0.30, 0.72, 0.55 * a + 0.45 * c)
    Bk = steel.streaks(P, N, b.leaks, 0.5, 0.03, seed=len(P)) * (0.6 + 0.4 * a) if b.leaks else np.zeros(len(P))
    A = np.zeros(len(P))
    if ground:
        hgt = z - z.min()
        A = np.clip(np.exp(-hgt / 0.20) * (0.5 + 0.5 * c) * (1 - 0.5 * up), 0, 1)
        R = R + 0.20 * sstep(0.8, 0.0, hgt) * (0.3 + 0.7 * bb)
        G = np.maximum(G, 0.6 * sstep(0.35, 0.0, hgt) * sstep(0.4, 0.75, a))
    R, G = R * dirt, G * wear
    R = np.where(soft, 0.05 + 0.10 * a, R)
    G = np.where(soft, 0.0, G)
    Bk = np.where(soft, 0.0, Bk)
    geo.set_wear(ob, np.clip(np.stack([R, G, Bk, A], 1), 0, 1), per="corner")


def done(ctx, b, name, M, notes, size=None, collision="box", cover=None, ground=True, ao=0.10, **wkw):
    ob = b.finish(name, M, ctx.col)
    weather(ctx, b, ob, name, ground=ground, ao=ao, **wkw)
    ctx.asset(ob, collision=collision, cover_height=cover, notes=notes, expect_size=size, slots=SLOT_META)
    ctx.built.append(ob)
    return ob


def ring(n, r, z=0.0, a0=0.0):
    a = a0 + np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([r * np.cos(a), r * np.sin(a), np.full(n, z)], 1)


# ------------------------------------------------------------------------------------------------ street furniture

def dumpster(ctx, M, shut=False):
    b = B(1)
    yb, yf0, yf1, zb, zr, t = 0.50, -0.30, -0.50, 0.14, 1.16, 0.006
    prof = [(yf0, zb), (yb, zb), (yb, zr), (yb - t, zr), (yb - t, zb + t), (yf0 + t, zb + t), (yf1 + t, zr), (yf1, zr)]
    b.prism(prof, (-0.9, 0, 0), Y, Z, (1.8, 0, 0), "green", pstep=0.12)
    trap = [(yf0, zb), (yb, zb), (yb, zr), (yf1, zr)]
    b.poly_plate([(0.9, p, q) for p, q in trap], t, "green")
    b.poly_plate([(-0.9, p, q) for p, q in trap[::-1]], t, "green")
    for xs in (-0.9, 0.9):                                                  # rim tube round the top
        box(b, (xs - 0.02, yf1 - 0.03, zr - 0.05), (xs + 0.02, yb + 0.03, zr), "green", axis="y")
    for yy in (yf1 - 0.03, yb - 0.01):
        box(b, (-0.92, yy, zr - 0.05), (0.92, yy + 0.04, zr), "green", axis="x")
    sl = (yf1 - yf0) / (zr - zb)
    for xr in (-0.45, 0.0, 0.45):                                           # pressed ribs, back and front
        box(b, (xr - 0.03, yb, zb + 0.06), (xr + 0.03, yb + 0.025, zr - 0.07), "green", axis="z")
        za, zc = zb + 0.06, zr - 0.07
        ya, yc = yf0 + sl * (za - zb), yf0 + sl * (zc - zb)
        b.plate_rows([((xr - 0.03, ya - 0.025, za), (xr + 0.03, ya - 0.025, za)),
                      ((xr - 0.03, yc - 0.025, zc), (xr + 0.03, yc - 0.025, zc))], 0.025, "green")
    for s_ in (-1, 1):                                                      # fork pockets on both ends
        x0 = s_ * 0.9
        for zp in (0.42, 0.78):
            box(b, (min(x0, x0 + s_ * 0.05), -0.36, zp), (max(x0, x0 + s_ * 0.05), 0.42, zp + 0.11), "green", axis="y")
    for (cx, cy) in ((-0.75, -0.28), (-0.75, 0.40), (0.75, -0.28), (0.75, 0.40)):
        box(b, (cx - 0.07, cy - 0.07, zb - 0.012), (cx + 0.07, cy + 0.07, zb), "dark")
        box(b, (cx - 0.035, cy - 0.025, 0.06), (cx - 0.028, cy + 0.025, zb - 0.012), "dark")
        box(b, (cx + 0.028, cy - 0.025, 0.06), (cx + 0.035, cy + 0.025, zb - 0.012), "dark")
        lathe(b, [(0.012, -0.02), (0.05, -0.02), (0.058, -0.012), (0.058, 0.012), (0.05, 0.02), (0.012, 0.02)], "rubber", 20,
              loc=(cx, cy, 0.058), rot=(0, 90, 0))
    for i, xs in enumerate((-0.9, 0.0)):                                    # two lids, 0.9 each
        lid = B(10 + i)
        box(lid, (0.005, -0.535, 0.0), (0.895, 0.535, 0.03), "pBlack", ch=0.008)
        box(lid, (0.10, -0.42, 0.03), (0.80, 0.42, 0.075), "pBlack", ch=0.012)
        for xr in (0.25, 0.45, 0.65):
            box(lid, (xr - 0.012, -0.40, 0.075), (xr + 0.012, 0.40, 0.09), "pBlack")
        for xh in (0.15, 0.75):
            rod(lid, (xh, 0.535, 0.012), (xh + 0.06, 0.535, 0.012), 0.016, "pBlack")
        opened = (not shut) and i == 1
        Mx = np.eye(4)
        hinge = np.array([xs, yb + 0.115, zr + 0.012])
        if opened:                                                          # thrown back, hanging behind the hopper
            a_ = math.radians(-270.0)
            R = np.array([[1, 0, 0], [0, math.cos(a_), -math.sin(a_)], [0, math.sin(a_), math.cos(a_)]])
            Mx[:3, :3] = R
            Mx[:3, 3] = hinge - R @ np.array([0, 0.535, 0.012])
            for xh in (0.15, 0.75):                                         # hinge brackets
                box(b, (xs + xh - 0.012, yb, zr - 0.04), (xs + xh + 0.012, yb + 0.12, zr + 0.02), "green")
        else:
            Mx[:3, 3] = (xs, 0.0, zr)
        b.merge(lid, Mx)
    if not shut:
        blob(b, (0.62, 0.50, 0.48), (0.42, 0.02, zr - 0.18), "pBlack", seed=3, rot=20, lumps=0.03)
    size = (1.9, 1.04, 1.25) if shut else (1.9, None, 1.36)
    name = "SM_Furn_Dumpster_Shut" if shut else "SM_Furn_Dumpster"
    return done(ctx, b, name, M, "Catalogue dumpster (05b 2.6): rear-load steel hopper 1.8 x 1.03, rim 1.16, sloping front (-Y), "
                "ribs, fork pockets, four casters, two plastic lids%s. Stencil HOLLIS CARTING / 718 555 0144 is a decal on the front."
                % (" shut" if shut else ", the +X one thrown back with a bag showing"), size, cover=1.30)


def mailbox(ctx, M):
    b = B(2)
    sign_slot(M, "Mailbox", 0.36, 0.27)
    w, d, z0, z1 = 0.52, 0.48, 0.27, 0.95
    r = d / 2
    prof = [(-r, z0), (r, z0), (r, z1)] + [(r * math.cos(a), z1 + r * math.sin(a)) for a in np.linspace(0.18, math.pi - 0.18, 9)] + [(-r, z1)]
    b.prism(prof, (-w / 2, 0, 0), Y, Z, (w, 0, 0), "blue", pstep=0.08)
    for (cx, cy) in ((-0.22, -0.2), (-0.22, 0.2), (0.22, -0.2), (0.22, 0.2)):     # angle legs and feet
        box(b, (cx - 0.025, cy - 0.025, 0.0), (cx + 0.025, cy + 0.025, z0), "blue", ch=0.003)
        box(b, (cx - 0.04, cy - 0.04, 0.0), (cx + 0.04, cy + 0.04, 0.008), "blue")
    box(b, (-w / 2 - 0.004, -r - 0.004, z0), (w / 2 + 0.004, r + 0.004, z0 + 0.05), "blue")          # skirt band
    door = [((-0.21, -(r + 0.008) * math.sin(a), z1 + (r + 0.008) * math.cos(a)),
             (0.21, -(r + 0.008) * math.sin(a), z1 + (r + 0.008) * math.cos(a))) for a in np.linspace(1.75, 0.55, 6)]
    b.plate_rows(door, 0.008, "blue")
    rod(b, (-0.12, -0.262, 1.0), (0.12, -0.262, 1.0), 0.011, "chrome")
    for xh in (-0.12, 0.12):
        rod(b, (xh, -0.232, 1.0), (xh, -0.262, 1.0), 0.008, "chrome")
    card(b, (-0.18, -r - 0.002, 0.50), (0.36, 0, 0), (0, 0, 0.27), "signMailbox", sign=True)
    return done(ctx, b, "SM_Furn_Mailbox", M, "Catalogue mailbox: street collection box, barrel top at 1.19, four legs 0.27, "
                "pull-down chute door with a chrome handle; label MAIL in slot M_Sign_Mailbox (front, 0.36 x 0.27). Scrawl variant: decal.",
                (0.52, 0.51, 1.19), cover=1.20)


def newspaper_box(ctx, M):
    b = B(3)
    sign_slot(M, "Newspaper", 0.33, 0.41)
    z0, z1, w, d = 0.48, 1.08, 0.46, 0.40
    box(b, (-0.17, -0.14, 0.0), (0.17, 0.14, 0.012), "dark")                # base plate and pedestal
    box(b, (-0.04, -0.04, 0.012), (0.04, 0.04, z0), "dark", ch=0.004)
    box(b, (-w / 2, -d / 2, z0), (w / 2, d / 2, z1 - 0.03), "red", ch=0.006)
    box(b, (-w / 2 - 0.01, -d / 2 - 0.02, z1 - 0.035), (w / 2 + 0.01, d / 2 + 0.005, z1), "red", ch=0.006)   # hood
    yf = -d / 2
    for lo, hi in (((-0.21, 0.54), (-0.19, 1.02)), ((0.13, 0.54), (0.15, 1.02)), ((-0.19, 0.54), (0.13, 0.56)), ((-0.19, 0.98), (0.13, 1.02))):
        box(b, (lo[0], yf - 0.02, lo[1]), (hi[0], yf, hi[1]), "red", ch=0.003)          # door frame round the window
    box(b, (-0.19, yf - 0.018, 0.56), (0.13, yf - 0.014, 0.98), "glass", ch=0.0)
    card(b, (-0.185, yf - 0.006, 0.565), (0.32, 0, 0), (0, 0, 0.41), "signNewspaper", sign=True)
    box(b, (0.16, yf - 0.05, 0.86), (0.225, yf, 1.02), "dark", ch=0.006)                                    # coin mechanism
    box(b, (0.175, yf - 0.052, 0.95), (0.21, yf - 0.05, 0.955), "chrome")
    rod(b, (-0.15, yf - 0.045, 0.70), (-0.05, yf - 0.045, 0.70), 0.009, "chrome")
    for xh in (-0.15, -0.05):
        rod(b, (xh, yf - 0.02, 0.70), (xh, yf - 0.045, 0.70), 0.006, "chrome")
    return done(ctx, b, "SM_Furn_NewspaperBox", M, "Catalogue newspaper_box: coin rack 0.46 x 0.40 x 0.60 on a pedestal, glazed door "
                "showing the front page (slot M_Sign_Newspaper 0.33 x 0.41), coin mechanism, chrome pull. Red #b3261e; the other "
                "catalogue colours are material instances of MI_Steel_PaintRed.", (0.48, 0.44, 1.08), cover=1.08)


def banded_lathe(b, prof, bands, seg=36):
    """Lathe a (r, z) profile cut into colour bands [(z0, z1, slot)]."""
    P = np.asarray(prof, dtype=np.float64)
    for z0, z1, slot in bands:
        zz = np.linspace(z0, z1, max(2, int(math.ceil((z1 - z0) / 0.04)) + 1))
        rr = np.interp(zz, P[:, 1], P[:, 0])
        lathe(b, list(zip(rr, zz)), slot, seg)


def traffic_barrel(ctx, M):
    b = B(4)
    lathe(b, [(0.0, 0.0), (0.30, 0.0), (0.30, 0.035), (0.27, 0.075), (0.20, 0.09), (0.0, 0.09)], "rubber", 40)
    prof = [(0.27, 0.08), (0.265, 0.30), (0.25, 0.50), (0.24, 0.68), (0.225, 0.84), (0.205, 0.95)]
    bands = [(0.08, 0.30, "pOrange"), (0.30, 0.50, "pWhite"), (0.50, 0.68, "pOrange"), (0.68, 0.84, "pWhite"), (0.84, 0.95, "pOrange")]
    banded_lathe(b, prof, bands)
    for zr in (0.30, 0.50, 0.68, 0.84):                                     # moulded ridges between the bands
        lathe(b, [(np.interp(zr, [p[1] for p in prof], [p[0] for p in prof]) - 0.002, zr - 0.008), (np.interp(zr, [p[1] for p in prof], [p[0] for p in prof]) + 0.006, zr),
                  (np.interp(zr, [p[1] for p in prof], [p[0] for p in prof]) - 0.002, zr + 0.008)], "pOrange", 36)
    lathe(b, [(0.205, 0.95), (0.19, 0.958), (0.0, 0.958)], "pOrange", 36)
    box(b, (-0.11, -0.022, 0.955), (0.11, 0.022, 1.0), "pOrange", ch=0.012)   # moulded handle
    box(b, (-0.06, -0.023, 0.958), (0.06, 0.023, 0.982), "pBlack", ch=0.0)
    return done(ctx, b, "SM_Furn_TrafficBarrel", M, "Catalogue traffic_barrel: channelizer drum, black rubber base ring r 0.30, body "
                "r 0.27 to 0.205, white bands 0.30-0.50 and 0.68-0.84, moulded handle at 1.0.", (0.6, 0.6, 1.0), collision="convex", cover=0.98)


def traffic_cone(ctx, M):
    b = B(5)
    box(b, (-0.18, -0.18, 0.0), (0.18, 0.18, 0.03), "rubber", ch=0.012)
    prof = [(0.135, 0.03), (0.11, 0.20), (0.085, 0.36), (0.06, 0.52), (0.026, 0.70)]
    banded_lathe(b, prof, [(0.03, 0.30, "pOrange"), (0.30, 0.48, "pWhite"), (0.48, 0.70, "pOrange")], 32)
    lathe(b, [(0.026, 0.70), (0.018, 0.70), (0.018, 0.69)], "pOrange", 32)
    return done(ctx, b, "SM_Furn_TrafficCone", M, "Catalogue traffic_cone: 0.36 square rubber foot, cone to 0.70, white collar "
                "0.30-0.48. No collision in the game.", (0.36, 0.36, 0.70), collision="none")


def jersey_barrier(ctx, M):
    b = B(6, step=0.25)
    c = 0.02
    half = [(0.30, 0.0), (0.30, 0.075 - c), (0.30 - c, 0.075), (0.165, 0.33), (0.085 + c * 0.3, 0.81 - c), (0.085 - c, 0.81)]
    prof = half + [(-p, q) for p, q in half[::-1]]
    prof = [(p, q) for p, q in prof]
    slots = [(-1.5, -0.97, 0.0), (-0.97, -0.63, 0.07), (-0.63, 0.63, 0.0), (0.63, 0.97, 0.07), (0.97, 1.5, 0.0)]
    for x0, x1, zc in slots:
        pr = [(p, max(q, zc)) for p, q in prof]
        pr = [pr[i] for i in range(len(pr)) if i == 0 or (abs(pr[i][0] - pr[i - 1][0]) > 1e-6 or abs(pr[i][1] - pr[i - 1][1]) > 1e-6)]
        if zc > 0:
            pr = [(0.30, zc)] + [p for p in pr if p[1] > zc + 1e-6] + [(-0.30, zc)]
        b.prism(pr, (x0, 0, 0), Y, Z, (x1 - x0, 0, 0), "conc", pstep=0.1)
    for s_ in (-1, 1):                                                      # steel connector loops at the ends
        for zz in (0.22, 0.62):
            rod(b, (s_ * 1.5, -0.04, zz), (s_ * 1.53, -0.04, zz), 0.012, "dark")
            rod(b, (s_ * 1.5, 0.04, zz), (s_ * 1.53, 0.04, zz), 0.012, "dark")
            rod(b, (s_ * 1.53, -0.05, zz), (s_ * 1.53, 0.05, zz), 0.012, "dark")
    fit(b, (3.0, 0.61, 0.81))
    return done(ctx, b, "SM_Furn_JerseyBarrier", M, "Catalogue jersey_barrier (the scanned barriers are 1.55 m): precast safety-shape "
                "barrier 3.0 long, 0.60 foot, 0.33 at 0.33 m, 0.17 top at 0.81, fork-lift slots 0.34 x 0.07 at x +-0.8, 2 cm "
                "chamfers, steel connector loops. Marker scrawl and hazard-stripe variants are decals.", (3.0, 0.61, 0.81), cover=0.81)


def barricade(ctx, M):
    b = B(7)
    for xs in (-1.0, 1.0):                                                  # A-frames
        for s_ in (-1, 1):
            rod(b, (xs, s_ * 0.20, 0.02), (xs, s_ * 0.02, 1.0), 0.018, "cream", n=10)
            box(b, (xs - 0.05, s_ * 0.20 - 0.05, 0.0), (xs + 0.05, s_ * 0.20 + 0.05, 0.02), "cream")
        rod(b, (xs, -0.17, 0.30), (xs, 0.17, 0.30), 0.012, "cream")
        box(b, (xs - 0.03, -0.035, 0.98), (xs + 0.03, 0.035, 1.02), "cream")
    for zc, h in ((0.90, 0.20), (0.50, 0.14)):
        yb = -(0.02 + 0.18 * (1.0 - zc) / 0.98 + 0.018)
        box(b, (-1.2, yb - 0.025, zc - h / 2), (1.2, yb, zc + h / 2), "pWhite", ch=0.005)
        stripes(b, -1.2, 1.2, zc - h / 2, zc + h / 2, yb - 0.0265, "pOrange", width=0.10, pitch=0.20)
        stripes(b, -1.2, 1.2, zc - h / 2, zc + h / 2, yb + 0.0015, "pOrange", width=0.10, pitch=0.20, angle=-45.0, face=1)
    box(b, (0.94, -0.035, 1.0), (1.06, 0.035, 1.03), "pBlack")              # amber flasher
    lathe(b, [(0.0, 0.0), (0.045, 0.0), (0.05, 0.03), (0.045, 0.06), (0.0, 0.062)], "pOrange", 20, loc=(1.0, 0, 1.03))
    return done(ctx, b, "SM_Furn_Barricade", M, "Catalogue barricade: sawhorse with two A-frames, boards 2.4 long (0.20 at 0.9, "
                "0.14 at 0.5) striped orange and white on both faces (modelled paint), amber flasher on the +X end (lens: emissive "
                "#ff8a1a x 1.6 in Unreal).", (2.4, 0.5, 1.1), cover=1.0)


def bus_shelter(ctx, M):
    b = B(8)
    sign_slot(M, "BusShelter", 1.14, 1.72)
    sign_slot(M, "BusFlag", 0.26, 0.36)
    for (px, py) in ((-1.76, -0.71), (-1.76, 0.71), (1.76, -0.71), (1.76, 0.71)):
        box(b, (px - 0.04, py - 0.04, 0.0), (px + 0.04, py + 0.04, 2.38), "dark", ch=0.004)
        box(b, (px - 0.05, py - 0.05, 0.0), (px + 0.05, py + 0.05, 0.012), "dark")
    box(b, (-1.80, -0.75, 2.38), (1.80, 0.75, 2.40), "dark", ch=0.0)       # roof tray
    for yy in (-0.75, 0.71):
        box(b, (-1.80, yy, 2.38), (1.80, yy + 0.04, 2.48), "dark")
    for xx in (-1.80, 1.76):
        box(b, (xx, -0.71, 2.38), (xx + 0.04, 0.71, 2.48), "dark")
    box(b, (-1.76, -0.71, 2.40), (1.76, 0.71, 2.42), "corrugated", ch=0.0)
    box(b, (-1.2, -0.70, 2.35), (1.2, -0.62, 2.38), "dark")                 # light strip
    box(b, (-1.18, -0.70, 2.345), (1.18, -0.63, 2.35), "lens", ch=0.0)
    for x0, x1 in ((-1.72, -0.04), (0.04, 1.72)):                           # back glass, two panes 1.64 x 1.86
        box(b, (x0, 0.69, 0.26), (x1, 0.73, 0.30), "galv")
        box(b, (x0, 0.69, 2.14), (x1, 0.73, 2.18), "galv")
        box(b, (x0 + 0.02, 0.705, 0.30), (x1 - 0.02, 0.715, 2.14), "glass", ch=0.0)
    box(b, (-0.04, 0.69, 0.26), (0.04, 0.73, 2.18), "galv")
    box(b, (1.74, -0.05, 0.26), (1.78, 0.67, 0.30), "galv")                 # half pane at the +X end
    box(b, (1.74, -0.05, 2.14), (1.78, 0.67, 2.18), "galv")
    box(b, (1.74, -0.09, 0.26), (1.78, -0.05, 2.18), "galv")
    box(b, (1.755, -0.05, 0.30), (1.765, 0.67, 2.14), "glass", ch=0.0)
    box(b, (-1.80, -0.62, 0.25), (-1.62, 0.66, 2.20), "dark", ch=0.008)    # lit advertising box closing the -X end
    card(b, (-1.801, 0.59, 0.37), (0, -1.14, 0), (0, 0, 1.72), "signBusShelter", sign=True)
    card(b, (-1.619, -0.55, 0.37), (0, 1.14, 0), (0, 0, 1.72), "signBusShelter", sign=True)
    for xb in (-0.7, 0.7):                                                  # bench, 1.9 long at 0.47
        box(b, (xb - 0.03, 0.40, 0.0), (xb + 0.03, 0.66, 0.44), "dark")
    for k in range(4):
        y0 = 0.36 + k * 0.08
        board(b, (-0.95, y0, 0.44), (0.95, y0 + 0.07, 0.47), "plank")
    box(b, (1.53, -0.754, 1.95), (1.79, -0.751, 2.31), "galv", ch=0.0)       # bus-stop flag on the front +X post
    card(b, (1.53, -0.7545, 1.95), (0.26, 0, 0), (0, 0, 0.36), "signBusFlag", sign=True)
    return done(ctx, b, "SM_Furn_BusShelter", M, "Catalogue bus_shelter: 3.6 x 1.5, four posts, roof tray to 2.48 with a light strip "
                "(MI_Lamp_Lens), glass back in two panes 1.64 x 1.86, half pane at +X, lit ad box closing -X with the IPX one-sheet "
                "on both faces (slot M_Sign_BusShelter, 1.14 x 1.72), timber bench 1.9 at 0.47, flag (M_Sign_BusFlag). Front -Y.",
                (3.6, 1.5, 2.48), cover=2.30)


def trash_bags(ctx, M, variant):
    b = B(9 + variant)
    rng = ctx.rng("bags", variant)
    spots = [(-0.33, -0.22), (0.30, -0.25), (-0.30, 0.24), (0.32, 0.22)] if variant == 0 else [(-0.38, -0.18), (0.22, -0.26), (-0.12, 0.26), (0.40, 0.18)]
    grey = 2 if variant == 0 else 0
    for i, (x, y) in enumerate(spots + [(0.02, 0.0)]):
        top = i == 4
        s = np.array([0.55, 0.48, 0.42]) * rng.uniform(0.88, 1.08, 3)
        z = 0.26 if top else 0.0
        slot = "bagGrey" if i == grey else "bagBlack"
        rot = float(rng.uniform(0, 180))
        blob(b, s * (1, 1, 0.85), (x, y, z), slot, seed=variant * 10 + i, rot=rot, lumps=0.05, freq=3.2, flat=0.36,
             tilt=tuple(rng.uniform(-12, 12, 2)))
        a = math.radians(rot + 90)
        nx, ny = x + 0.22 * math.cos(a), y + 0.22 * math.sin(a)             # tied neck and ears
        nz = z + s[2] * 0.62
        lathe(b, [(0.0, 0.0), (0.05, 0.0), (0.02, 0.05), (0.03, 0.08), (0.0, 0.10)], slot, 10, loc=(nx, ny, nz),
              rot=(0, 60, rot))
    fit(b, (1.28, 0.97, 0.63))
    return done(ctx, b, "SM_Furn_TrashBags_%s" % "AB"[variant], M, "Catalogue trash_bags: pile of five tied refuse sacks about 0.5 "
                "across, the fifth on the others; one pale grey #c9c9c2. Shiny black sacks: give MI_Plastic_Black a lower roughness "
                "instance in Unreal.", (1.28, 0.97, 0.63), collision="convex", cover=0.62)


def crate(b, M, slot):
    """Dairy crate 0.33 x 0.33 x 0.28: solid rims, lattice sides of real bars, grid floor."""
    s, h = 0.165, 0.28
    for (cx, cy) in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        box(b, (cx * s - (0.03 if cx > 0 else 0), cy * s - (0.03 if cy > 0 else 0), 0.0),
            (cx * s + (0.0 if cx > 0 else 0.03), cy * s + (0.0 if cy > 0 else 0.03), h), slot, ch=0.006)
    for z0, z1 in ((0.0, 0.03), (h - 0.045, h)):
        for sgn in (-1, 1):
            box(b, (-s, sgn * s - (0.012 if sgn > 0 else 0), z0), (s, sgn * s + (0 if sgn > 0 else 0.012), z1), slot, ch=0.003)
            box(b, (sgn * s - (0.012 if sgn > 0 else 0), -s, z0), (sgn * s + (0 if sgn > 0 else 0.012), s, z1), slot, ch=0.003)
    for t in np.linspace(-s + 0.055, s - 0.055, 6):
        for sgn in (-1, 1):
            o = sgn * s - (0.009 if sgn > 0 else 0)
            box(b, (t - 0.006, o, 0.03), (t + 0.006, o + 0.009, h - 0.045), slot, ch=0.0, axis="z")
            box(b, (o, t - 0.006, 0.03), (o + 0.009, t + 0.006, h - 0.045), slot, ch=0.0, axis="z")
    for zz in (0.10, 0.17):
        for sgn in (-1, 1):
            o = sgn * s - (0.009 if sgn > 0 else 0)
            box(b, (-s, o, zz), (s, o + 0.009, zz + 0.012), slot, ch=0.0)
            box(b, (o, -s, zz), (o + 0.009, s, zz + 0.012), slot, ch=0.0)
    for t in np.linspace(-s + 0.04, s - 0.04, 7):
        box(b, (t - 0.006, -s, 0.005), (t + 0.006, s, 0.02), slot, ch=0.0)
        box(b, (-s, t - 0.006, 0.005), (s, t + 0.006, 0.02), slot, ch=0.0)


def milk_crates(ctx, M):
    out = []
    b = B(20)
    crate(b, M, "crateBlue")
    out.append(done(ctx, b, "SM_Furn_MilkCrate", M, "One dairy crate 0.33 x 0.33 x 0.28 with lattice sides of real bars (no alpha). "
                    "Tint per instance: #1f4f9a, #b3261e, #202326, #1f5a3a.", (0.33, 0.33, 0.28), collision="box", ao=0.04))
    cols = ["crateBlue", "crateRed", "pBlack", "crateGreen"]
    for v in range(2):
        rng = ctx.rng("crates", v)
        b = B(21 + v)
        lay = [(-0.17, -0.17, 0), (0.17, -0.17, 0), (-0.17, 0.17, 0), (0.17, 0.17, 0),
               (-0.17, -0.15, 1), (0.16, -0.16, 1), (-0.16, 0.17, 1)]
        lay += [(-0.15, -0.14, 2)] if v == 0 else [(-0.16, -0.15, 2), (0.15, -0.14, 2)]
        for i, (x, y, k) in enumerate(lay):
            c = B(100 + i)
            crate(c, M, cols[int(rng.integers(0, 4))])
            sub(b, c, float(rng.uniform(-6, 6)), (x + rng.uniform(-0.008, 0.008), y + rng.uniform(-0.008, 0.008), k * 0.283))
        fit(b, (0.68, 0.68, 0.85))
        out.append(done(ctx, b, "SM_Furn_MilkCrates_%s" % "AB"[v], M, "Catalogue milk_crates: thrown-down stack of dairy crates, four "
                        "on the ground, three on them, %s on top (0.85)." % ("one" if v == 0 else "two"), (0.68, 0.68, 0.85),
                        cover=0.90, ao=0.04))
    return out


def pallet(b, M, wob=None):
    """Timber pallet 1.2 x 1.0 x 0.144: three bottom boards, three bearers, seven top boards (boards along Y)."""
    for xb in (-0.55, 0.0, 0.55):
        board(b, (xb - 0.05, -0.5, 0.0), (xb + 0.05, 0.5, 0.022), "pallet")
    for yb in (-0.45, 0.0, 0.45):
        board(b, (-0.6, yb - 0.05, 0.022), (0.6, yb + 0.05, 0.117), "pallet")
    for k, xt in enumerate(np.linspace(-0.54, 0.54, 7)):
        w = 0.06 if k in (0, 6) else 0.045
        board(b, (xt - w, -0.5, 0.117), (xt + w, 0.5, 0.144), "pallet", ch=0.003)


def pallets(ctx, M):
    out = []
    b = B(30)
    pallet(b, M)
    out.append(done(ctx, b, "SM_Furn_Pallet", M, "Catalogue pallet: 1.2 x 1.0 x 0.144, three bearers, seven top boards, three bottom "
                    "boards. Walk-over: no collision in the level.", (1.2, 1.0, 0.144), collision="none", ao=0.05))
    for v in range(2):
        rng = ctx.rng("pallets", v)
        b = B(31 + v)
        for k in range(8):
            c = B(200 + k)
            pallet(c, M)
            sub(b, c, float(rng.uniform(-2.0, 2.0) * (1 + v)), (rng.uniform(-0.012, 0.012), rng.uniform(-0.012, 0.012), k * 0.144))
        fit(b, (1.23, 1.03, 1.15))
        out.append(done(ctx, b, "SM_Furn_PalletStack_%s" % "AB"[v], M, "Catalogue pallet_stack: eight pallets to 1.15, each a little "
                        "out of line.", (1.23, 1.03, 1.15), cover=1.15, ao=0.05))
    return out


def sandbags(ctx, M):
    b = B(40)
    rng = ctx.rng("sandbags")
    courses = [(4, 0.0), (3, 0.0), (4, 0.0)]
    i = 0
    for k, (n, _o) in enumerate(courses):
        w = 1.95 / 4
        xs = (np.arange(n) - (n - 1) / 2) * w
        for x in xs:
            s = np.array([w * 1.06, 0.56, 0.36]) * rng.uniform(0.95, 1.05, 3)
            pillow(b, s * (1, 1, 0.85), (x + rng.uniform(-0.02, 0.02), rng.uniform(-0.02, 0.02), k * 0.29), "burlap", seed=40 + i,
                   rot=float(rng.uniform(-4, 4)))
            i += 1
    fit(b, (1.95, 0.56, 0.9))
    return done(ctx, b, "SM_Furn_Sandbags", M, "Catalogue sandbags: wall 1.95 long of eleven hessian bags in three courses (4, 3, 4), "
                "0.90 high.", (1.95, 0.56, 0.9), cover=0.90, ao=0.06)


def oil_drum(ctx, M, slot, tag):
    b = B(50)
    R, H = 0.286, 0.90
    side = []
    for zc in (0.30, 0.60):                                                 # rolling hoops
        side += [(R, zc - 0.03), (R + 0.012, zc - 0.012), (R + 0.012, zc + 0.012), (R, zc + 0.03)]
    for zc in (0.18, 0.45, 0.72):                                           # shallow corrugations
        side += [(R, zc - 0.015), (R + 0.003, zc), (R, zc + 0.015)]
    prof = [(0.0, 0.012), (R - 0.014, 0.012), (R - 0.012, 0.0), (R + 0.004, 0.0), (R + 0.006, 0.012), (R, 0.024)]
    prof += sorted(side, key=lambda p: p[1]) + [(R, H - 0.024), (R + 0.006, H - 0.012), (R + 0.004, H), (R - 0.012, H), (R - 0.014, H - 0.012), (0.0, H - 0.012)]
    lathe(b, prof, slot, 48)
    for (bx_, by_, r_) in ((0.17, 0.0, 0.032), (-0.17, 0.0, 0.016)):         # bungs
        lathe(b, [(0.0, 0.0), (r_, 0.0), (r_, 0.008), (r_ * 0.7, 0.012), (0.0, 0.012)], "dark", 16, loc=(bx_, by_, H - 0.012))
    return done(ctx, b, "SM_Furn_OilDrum_%s" % tag, M, "Catalogue oil_drum: 55-gallon drum 0.58 x 0.90, two rolling hoops, rolled "
                "chimes, two bungs. The MOTOR OIL label (variant 0) is a decal.", (0.58, 0.58, 0.90), collision="convex", cover=0.90)


def tyre(b, M, loc=(0, 0, 0), rot=(0, 0, 0)):
    ro, ri, w = 0.385, 0.19, 0.245
    half = w / 2
    prof = [(ri, -half * 0.55), (ri + 0.025, -half * 0.75), (0.30, -half), (0.355, -half * 0.96), (0.375, -half * 0.8)]
    for g in (-0.45, -0.15, 0.15, 0.45):                                     # tread with four grooves
        gz = g * half
        prof += [(ro, gz - 0.018), (ro - 0.008, gz - 0.006), (ro - 0.008, gz + 0.006), (ro, gz + 0.018)]
    prof += [(0.375, half * 0.8), (0.355, half * 0.96), (0.30, half), (ri + 0.025, half * 0.75), (ri, half * 0.55)]
    prof = [(r, z + half) for r, z in prof]
    lathe(b, prof, "rubber", 48, loc=loc, rot=rot, closed=True)


def tyre_stacks(ctx, M):
    out = []
    for v in range(2):
        rng = ctx.rng("tyres", v)
        b = B(60 + v)
        for k in range(4):
            off = rng.uniform(-0.02, 0.02, 2) * (1 + 2 * v)
            tilt = rng.uniform(-1.5, 1.5, 2) * v
            tyre(b, M, (off[0], off[1], k * 0.245), (tilt[0], tilt[1], 0))
        fit(b, (0.77, 0.77, 0.97))
        out.append(done(ctx, b, "SM_Furn_TyreStack_%s" % "AB"[v], M, "Catalogue tire_stack: four car tyres 0.77 across, 0.245 section, "
                        "stacked to 0.97%s." % (" and leaning" if v else ""), (0.77, 0.77, 0.97), collision="convex", cover=0.98))
    return out


def shopping_cart(ctx, M):
    b = B(70)
    wr = 0.0035
    zb, zt = 0.42, 0.93
    def frame(z):                                                           # basket outline at height z: narrow at the front (+X)
        f = (z - zb) / (zt - zb)
        xb, xf = -0.36 - 0.10 * f, 0.30 + 0.12 * f
        hb, hf = 0.20 + 0.06 * f, 0.15 + 0.06 * f
        return xb, xf, hb, hf
    for z in np.linspace(zb, zt, 9):                                        # horizontal wires
        xb, xf, hb, hf = frame(z)
        pts = [(xb, -hb, z), (xf, -hf, z), (xf, hf, z), (xb, hb, z)]
        r_ = 0.006 if z in (zb, zt) else wr
        tube_path(b, pts + [pts[0]], r_, "galv", n=6)
    for t in np.linspace(0, 1, 19):                                         # vertical wires on the sides
        for s_ in (-1, 1):
            p = []
            for z in (zb, zt):
                xb, xf, hb, hf = frame(z)
                p.append((xb + (xf - xb) * t, s_ * (hb + (hf - hb) * t), z))
            rod(b, p[0], p[1], wr, "galv", n=6)
    for t in np.linspace(-1, 1, 11):                                        # front wires and the hinged back gate
        for end in (0, 1):
            p = []
            for z in (zb, zt):
                xb, xf, hb, hf = frame(z)
                p.append(((xf if end else xb), t * (hf if end else hb), z))
            rod(b, p[0], p[1], wr, "galv", n=6)
    for t in np.linspace(-1, 1, 9):                                         # basket floor
        xb, xf, hb, hf = frame(zb)
        rod(b, (xb, t * hb, zb), (xf, t * hf, zb), wr, "galv", n=6)
    for s_ in (-1, 1):                                                      # chassis
        rod(b, (-0.40, s_ * 0.21, 0.12), (0.40, s_ * 0.16, 0.12), 0.011, "galv")
        rod(b, (-0.40, s_ * 0.21, 0.12), (-0.47, s_ * 0.24, 1.0), 0.011, "galv")
        rod(b, (0.30, s_ * 0.155, 0.12), (0.30, s_ * 0.15, zb), 0.008, "galv")
    for t in np.linspace(-1, 1, 7):                                         # bottom tray
        rod(b, (-0.36, t * 0.19, 0.16), (0.32, t * 0.15, 0.16), wr, "galv", n=6)
    rod(b, (-0.36, 0, 0.16), (-0.40, 0, 0.12), 0.006, "galv")
    rod(b, (-0.47, -0.25, 1.0), (-0.47, 0.25, 1.0), 0.018, "red", n=12)      # handle
    for (cx, cy) in ((-0.38, -0.21), (-0.38, 0.21), (0.38, -0.16), (0.38, 0.16)):
        box(b, (cx - 0.02, cy - 0.015, 0.075), (cx + 0.02, cy + 0.015, 0.11), "galv")
        lathe(b, [(0.008, -0.013), (0.045, -0.013), (0.05, -0.006), (0.05, 0.006), (0.045, 0.013), (0.008, 0.013)], "rubber", 16,
              loc=(cx, cy, 0.05), rot=(90, 0, 0))
    fit(b, (0.91, 0.52, 1.02))
    return done(ctx, b, "SM_Furn_ShoppingCart", M, "Catalogue shopping_cart: trolley 0.91 x 0.52, wire basket of real 7 mm wires "
                "flaring to 0.93, lower tray, four castors, red handle at 1.0 (front +X). Tipped variant: lay it on its side.",
                (0.91, 0.52, 1.02), collision="box", cover=0.95, ao=None)


def mattress(ctx, M):
    b = B(80)
    ob = geo.box((1.74, 0.86, 0.20), bevel=0.06, segments=3)
    geo.densify(ob, 0.06)
    geo.displace(ob, 0.012, 3.0, 8)
    co, _ = geo.arrays(ob)
    co[:, 2] -= 0.025 * np.exp(-((co[:, 0] / 0.6) ** 2 + (co[:, 1] / 0.35) ** 2)) * (co[:, 2] > 0.1)      # slept-in hollow
    geo.set_verts(ob, co)
    b.absorb(ob, "ticking")
    for zz in (0.012, 0.188):                                               # piping round both edges
        tube_path(b, [(-0.84, -0.40, zz), (0.84, -0.40, zz), (0.84, 0.40, zz), (-0.84, 0.40, zz), (-0.84, -0.40, zz)], 0.008, "ticking", n=6)
    fit(b, (1.74, 0.86, 0.22))
    return done(ctx, b, "SM_Furn_Mattress", M, "Catalogue mattress: dumped mattress 1.88 x 0.93 x 0.20 (model 1.74 x 0.86) lying flat, "
                "piped edges. Ticking stripes and stains: detail layer or decal. No collision.", (1.74, 0.86, 0.22), collision="none")


def parking_meter(ctx, M):
    b = B(90)
    sign_slot(M, "MeterDial", 0.10, 0.15)
    lathe(b, [(0.0, 0.0), (0.08, 0.0), (0.08, 0.012), (0.035, 0.02), (0.03, 0.03), (0.03, 1.04), (0.0, 1.04)], "galv", 20)
    box(b, (-0.08, -0.06, 1.04), (0.08, 0.06, 1.24), "dark", ch=0.02)
    lathe(b, [(0.0, 0.0), (0.06, 0.0), (0.06, 0.02), (0.045, 0.05), (0.0, 0.06)], "dark", 20, loc=(0, 0, 1.24), scale=(1.33, 1.0, 1.0))
    for s_ in (-1, 1):
        y0 = s_ * 0.0605
        box(b, (-0.06, min(y0, y0 + s_ * 0.004), 1.08), (0.06, max(y0, y0 + s_ * 0.004), 1.235), "chrome", ch=0.0)
        if s_ < 0:
            card(b, (-0.05, y0 - 0.0045, 1.083), (0.10, 0, 0), (0, 0, 0.15), "signMeterDial", sign=True)
        else:
            card(b, (0.05, y0 + 0.0045, 1.083), (-0.10, 0, 0), (0, 0, 0.15), "signMeterDial", sign=True)
    box(b, (0.08, -0.012, 1.15), (0.088, 0.012, 1.17), "chrome")           # coin slot plate and key
    rod(b, (-0.08, 0, 1.12), (-0.10, 0, 1.12), 0.014, "chrome")
    return done(ctx, b, "SM_Furn_ParkingMeter", M, "Catalogue parking_meter: galvanised post to 1.04, single head 0.16 across to 1.30 "
                "with the dial on both faces (slot M_Sign_MeterDial, 0.10 x 0.15).", (0.2, 0.16, 1.30), cover=1.30)


def sign_post(ctx, M):
    b = B(91)
    sign_slot(M, "SignPost", 0.32, 0.44)
    prof = [(-0.025, 0.0), (0.025, 0.0), (0.025, 0.012), (0.018, 0.012), (0.012, 0.022), (-0.012, 0.022), (-0.018, 0.012), (-0.025, 0.012)]
    b.prism(prof, (0, 0.006, 0), X, -Y, (0, 0, 2.8), "galv", pstep=0.02)
    box(b, (-0.16, -0.019, 2.18), (0.16, -0.016, 2.62), "galv", ch=0.0)
    card(b, (-0.16, -0.0195, 2.18), (0.32, 0, 0), (0, 0, 0.44), "signSignPost", sign=True)
    for zz in (2.24, 2.56):
        lathe(b, [(0.0, 0.0), (0.009, 0.0), (0.009, 0.004), (0.0, 0.006)], "galv", 8, loc=(0, -0.0195, zz), rot=(90, 0, 0))
    return done(ctx, b, "SM_Furn_SignPost", M, "Catalogue sign_post: steel channel post 2.8 with one sign 0.32 x 0.44 (slot "
                "M_Sign_SignPost: NO PARKING ANYTIME, BUS STOP or ONE WAY as instances; the street blade is not modelled).",
                (0.32, None, 2.8), collision="box")


def bollard(ctx, M):
    b = B(92)
    lathe(b, [(0.0, 0.0), (0.10, 0.0), (0.10, 0.012), (0.085, 0.016)], "yellow", 32)
    banded_lathe(b, [(0.085, 0.016), (0.085, 0.93)], [(0.016, 0.70, "yellow"), (0.70, 0.80, "black"), (0.80, 0.93, "yellow")], 32)
    lathe(b, [(0.085, 0.93), (0.07, 0.975), (0.04, 0.995), (0.0, 1.0)], "yellow", 32)
    for (bx_, by_) in ((0.075, 0.075), (-0.075, 0.075), (0.075, -0.075), (-0.075, -0.075)):
        lathe(b, [(0.0, 0.0), (0.012, 0.0), (0.012, 0.012), (0.0, 0.014)], "dark", 6, loc=(bx_ * 0.92, by_ * 0.92, 0.012))
    return done(ctx, b, "SM_Furn_Bollard", M, "Catalogue bollard: steel pipe r 0.085, 1.0 tall, domed cap, base flange, yellow with a "
                "black band 0.70-0.80.", (0.2, 0.2, 1.0), collision="convex", cover=1.0)


def street(ctx, M):
    out = [dumpster(ctx, M), dumpster(ctx, M, shut=True), mailbox(ctx, M), newspaper_box(ctx, M), traffic_barrel(ctx, M),
           traffic_cone(ctx, M), jersey_barrier(ctx, M), barricade(ctx, M), bus_shelter(ctx, M)]
    out += [trash_bags(ctx, M, v) for v in range(2)]
    out += milk_crates(ctx, M) + pallets(ctx, M) + [sandbags(ctx, M)]
    out += [oil_drum(ctx, M, "drumBlue", "Blue"), oil_drum(ctx, M, "green", "Green"), oil_drum(ctx, M, "drumGrey", "Grey")]
    out += tyre_stacks(ctx, M) + [shopping_cart(ctx, M), mattress(ctx, M), parking_meter(ctx, M), sign_post(ctx, M), bollard(ctx, M)]
    return out


# ------------------------------------------------------------------------------------------------------ structures

SHED_POSTS = [0.12 + 2.96 * i for i in range(7)]
SHED_BANNERS = (("Chicken", 3.1), ("Liquor", 9.0), ("Nails", 14.9))


def sidewalk_shed(ctx, M):
    """05-level 2.9.3, local frame: x 0 = the deck's west end (web x 1), y 0 = deck centre line (web z 9.2),
    kerb side +Y, z 0 = sidewalk top. Place at Blender (1, -9.2, 0.15)."""
    b = B(300, step=0.3)
    for k, _x in SHED_BANNERS:
        sign_slot(M, "ShedBanner_" + k, 4.9, 0.78)
    top, L = 2.80, 18.0
    for x in SHED_POSTS:
        for yr in (1.6, -1.6):
            board(b, (x - 0.11, yr - 0.15, 0.0), (x + 0.11, yr + 0.15, 0.05), "plank")       # mud sill
            box(b, (x - 0.075, yr - 0.075, 0.05), (x + 0.075, yr + 0.075, 0.058), "galv", ch=0.0)
            rod(b, (x, yr, 0.058), (x, yr, 2.595), 0.045, "galv", n=12)
            for zc in (2.46, 2.56):                                                         # couplers
                box(b, (x - 0.055, yr - 0.055, zc - 0.035), (x + 0.055, yr + 0.055, zc + 0.035), "galv")
            for dx in (-0.75, 0.75):                                                        # knee braces
                if 0.0 <= x + dx <= L:
                    rod(b, (x, yr, 1.90), (x + dx, yr, 2.53), 0.025, "galv", n=8)
        rod(b, (x, -1.68, 2.46), (x, 1.68, 2.46), 0.035, "galv", n=10)                     # cross ledger
    for yr in (1.6, -1.6):
        rod(b, (0.0, yr, 2.56), (L, yr, 2.56), 0.035, "galv", n=10)                         # row ledgers
        board(b, (0.0, yr - 0.05, 2.595), (L, yr + 0.05, 2.64), "plank")                   # timber runner
    for xj in [0.04] + [0.6 + 1.2 * k for k in range(15)] + [L - 0.04]:                      # joists 0.08 x 0.14
        board(b, (xj - 0.04, -1.75, 2.64), (xj + 0.04, 1.75, top - 0.02), "plank")
    for i in range(8):                                                                      # plywood sheets 2.44 x 1.22
        for j in range(3):
            x0, x1 = i * 2.44, min(L, (i + 1) * 2.44)
            y0, y1 = -1.75 + j * 1.22, min(1.75, -1.75 + (j + 1) * 1.22)
            if x1 - x0 > 0.01:
                board(b, (x0 + 0.002, y0 + 0.002, top - 0.02), (x1 - 0.002, y1 - 0.002, top), "ply", ch=0.002)
    yo = 1.75                                                                               # kerb-side skirt and parapet
    for i in range(8):
        x0, x1 = i * 2.44, min(L, (i + 1) * 2.44)
        board(b, (x0 + 0.002, yo - 0.018, 2.30), (x1 - 0.002, yo, top), "plyGreen", ch=0.002)
        board(b, (x0 + 0.002, yo - 0.018, top), (x1 - 0.002, yo, top + 1.10), "plyGreen", ch=0.002)
    for xp in [0.045 + 2.44 * k for k in range(8)] + [L - 0.045]:
        board(b, (xp - 0.045, yo - 0.108, top), (xp + 0.045, yo - 0.018, top + 1.10), "plank")
    board(b, (0.0, yo - 0.14, top + 1.10), (L, yo, top + 1.16), "plank")                    # cap rail
    for xe, (ya, yb_) in ((L - 0.018, (-1.75, yo)), (0.0, (0.25, yo))):                     # east end, west end
        for k in range(3):
            y0, y1 = ya + (yb_ - ya) * k / 3, ya + (yb_ - ya) * (k + 1) / 3
            board(b, (xe, y0 + 0.002, top), (xe + 0.018, y1 - 0.002, top + 1.10), "plyGreen", ch=0.002)
        xi = xe - 0.09 if xe > 1 else xe + 0.018
        for yp in (ya + 0.045, (ya + yb_) / 2):
            board(b, (xi, yp - 0.045, top), (xi + 0.09, yp + 0.045, top + 1.10), "plank")
        board(b, (xe - (0.122 if xe > 1 else 0.0), ya, top + 1.10), (xe + (0.018 if xe > 1 else 0.14), yb_ - 0.14, top + 1.16), "plank")
    for k, xc in SHED_BANNERS:
        box(b, (xc - 2.45, yo, 2.96), (xc + 2.45, yo + 0.002, 3.74), "pWhite", ch=0.0)
        card(b, (xc + 2.45, yo + 0.0025, 2.96), (-4.9, 0, 0), (0, 0, 0.78), "signShedBanner_" + k, sign=True)
    for xb in (1.6, 4.56, 7.52, 10.48, 13.44, 16.4):                                       # caged bulbs
        lathe(b, [(0.0, 2.49), (0.03, 2.50), (0.035, 2.53), (0.03, 2.56), (0.0, 2.565)], "lens", 16, loc=(xb, 0, 0))
        lathe(b, [(0.0, 2.555), (0.022, 2.555), (0.022, 2.64), (0.0, 2.64)], "dark", 12, loc=(xb, 0, 0))
        for a in range(4):
            ca, sa = math.cos(a * math.pi / 2), math.sin(a * math.pi / 2)
            rod(b, (xb + 0.045 * ca, 0.045 * sa, 2.47), (xb + 0.045 * ca, 0.045 * sa, 2.59), 0.003, "dark", n=4)
    rod(b, (0.0, 0.06, 2.632), (L, 0.06, 2.632), 0.006, "rubber", n=6)
    return done(ctx, b, "SM_Furn_SidewalkShed", M, "Sidewalk shed over the south sidewalk in front of S3 (05-level 2.9.3): deck 18 x 3.5, "
                "top 2.80 above the sidewalk (plywood sheets on 15 joists and timber runners), 14 galvanised posts r 0.045 on mud "
                "sills (x 0.12 + 2.96 k, y +-1.6), ledgers and knee braces above head height, hunter-green plywood parapet 1.1 high "
                "on the kerb side (+Y), the east end and the west end to y 0.25 (open where the stair arrives), skirt 0.5 under the "
                "kerb edge (stencil: decal), three banners (M_Sign_ShedBanner_Chicken/_Liquor/_Nails, 4.9 x 0.78), six caged bulbs. "
                "Pivot: west end, deck centre line, sidewalk level; place at Blender (1, -9.2, 0.15).",
                (18.0, 3.5, 3.96), collision="complex", ground=True, ao=None)


def shed_stair(ctx, M):
    b = B(301, step=0.3)
    L, H, n = 3.6, 2.80, 12
    s = np.array([L, 0.0, H - 0.30]) / np.linalg.norm([L, 0.0, H - 0.30])
    out = [(0.0, 0.0), (0.38, 0.0), (L, 2.50), (L, H), (0.0, 0.30)]
    for sy in (-1, 1):
        pts = [(x, sy * 0.975, z) for x, z in out]
        b.poly_plate(pts if sy < 0 else pts[::-1], 0.05, "plank", vdir=(-s[2], 0, s[0]), fdir=(0, 1, 0))
    for k in range(1, n + 1):
        zt = k * H / n
        board(b, ((k - 1) * 0.30, -0.925, zt - 0.04), (min(L, k * 0.30 + 0.025), 0.925, zt), "ply", ch=0.003)
    ys = 0.999
    slope = lambda x: x * H / L
    for xp in (0.12, 1.8, 3.48):
        rod(b, (xp, ys, slope(xp)), (xp, ys, slope(xp) + 1.0), 0.024, "galv", n=10)
    for dz in (0.5, 1.0):
        rod(b, (0.0, ys, dz), (L, ys, H + dz), 0.024, "galv", n=10)
    return done(ctx, b, "SM_Furn_ShedStair", M, "Sidewalk shed stair (05-level 2.9.3): 12 open plywood treads, rise 0.233, going 0.30, "
                "on two timber stringers, 2.0 wide, tube handrail (rails 0.5 and 1.0 above the slope) on the street side (+Y). "
                "Pivot: foot of the stair (west end), centre line, ground; place at Blender (-2.6, -9.95, 0.15).",
                (3.625, 2.0, None), collision="complex", ao=None)


def cl_cap(b, x, z, r, slot="galv"):
    lathe(b, [(0.0, 0.0), (r + 0.006, 0.0), (r + 0.006, 0.02), (r * 0.6, 0.045), (0.0, 0.05)], slot, 16, loc=(x, 0, z))


def chain_panel(ctx, M, L, H, name, base=0.05, extra_post=None, note=""):
    b = B(310, step=0.5)
    posts = [0.0] + ([extra_post] if extra_post else [])
    for xp in posts:
        rod(b, (xp, 0, 0), (xp, 0, H - 0.05), 0.035, "galv", n=12)
        cl_cap(b, xp, H - 0.05, 0.035)
    rails = [base + 0.04, H - 0.07] + ([2.0 if H < 4.2 and H > 3.8 else H / 2] if H > 3.0 else [])
    for zr in rails:
        rod(b, (0.0, 0, zr), (L, 0, zr), 0.022, "galv", n=10)
        for xp in posts:
            box(b, (xp - 0.045, -0.045, zr - 0.03), (xp + 0.045, 0.045, zr + 0.03), "galv")
    card(b, (0.0, -0.042, base), (L, 0, 0), (0, 0, H - base - 0.02), "chain", step=0.6)
    for zt in np.arange(base + 0.25, H - 0.1, 0.35):                                      # wire ties to the posts
        for xp in posts:
            rod(b, (xp - 0.03, -0.04, zt), (xp + 0.03, -0.04, zt), 0.0015, "galv", n=4)
    return done(ctx, b, name, M, "Chain-link panel %.1f m wide, mesh to %.2f (05-level 2.9.2 chain-link construction): line post r 0.035 "
                "at x 0, rails r 0.022 just above the bottom and below the top%s, mesh card on the -Y side (MI_ChainLink_Galv, "
                "alpha-tested, 50 mm diamonds of 3.76 mm wire). Repeat every %.1f m and close a run with the matching end post. %s"
                % (L, H, " and at mid-height" if H > 3.0 else "", L, note), (None, None, H), collision="none", ao=None)


def chain_endpost(ctx, M, H):
    b = B(311, step=0.5)
    rod(b, (0, 0, 0), (0, 0, H + 0.07), 0.05, "galv", n=14)
    cl_cap(b, 0, H + 0.07, 0.05)
    box(b, (0.055, -0.048, 0.05), (0.075, -0.042, H - 0.02), "galv", ch=0.0)               # tension bar
    for zt in np.arange(0.15, H, 0.35):                                                    # tension bands
        box(b, (-0.06, -0.06, zt - 0.012), (0.08, 0.06, zt + 0.012), "galv", ch=0.004)
    return done(ctx, b, "SM_Furn_ChainLink_EndPost_%03d" % round(H * 100), M, "Chain-link end post r 0.05 standing 0.12 above a %.2f m "
                "mesh, tension bar and bands on the +X side (the mesh runs +X)." % H, (None, None, H + 0.12), collision="none", ao=None)


def gate_leaf(ctx, M, W, H=2.2):
    b = B(312, step=0.5)
    x0, x1, z0, z1 = 0.05, W, 0.06, 0.06 + H
    tube_path(b, [(x0, 0, z0), (x1, 0, z0), (x1, 0, z1), (x0, 0, z1), (x0, 0, z0)], 0.021, "galv", n=10)
    rod(b, (x0, 0, (z0 + z1) / 2), (x1, 0, (z0 + z1) / 2), 0.017, "galv", n=8)
    card(b, (x0, -0.026, z0), (x1 - x0, 0, 0), (0, 0, H), "chain", step=0.6)
    for zh in (z0 + 0.25, z1 - 0.25):                                                       # hinges round the post
        lathe(b, [(0.03, -0.03), (0.042, -0.03), (0.042, 0.03), (0.03, 0.03)], "galv", 12, loc=(0, 0, zh), closed=True)
        box(b, (0.0, -0.012, zh - 0.02), (x0, 0.012, zh + 0.02), "galv")
    box(b, (x1 - 0.02, -0.03, 1.0), (x1 + 0.05, 0.03, 1.08), "galv")                        # latch fork
    return done(ctx, b, "SM_Furn_ChainLink_GateLeaf_%03dx%03d" % (round(W * 100), round(H * 100)), M,
                "Chain-link gate leaf %.2f x %.1f: pipe frame r 0.021, mid rail, mesh card, hinges round a post at x 0 (pivot: the "
                "hinge axis on the ground), latch fork." % (W, H), (W + 0.092, None, None), collision="none", ao=None)


def gate_posts(ctx, M, W, H, r, header=None):
    b = B(313, step=0.5)
    for xp in (0.0, W):
        rod(b, (xp, 0, 0), (xp, 0, H - 0.05), r, "galv", n=16)
        cl_cap(b, xp, H - 0.05, r)
    if header:
        rod(b, (0.0, 0, header), (W, 0, header), 0.03, "galv", n=10)
    name = "SM_Furn_ChainLink_GateFrame_%03dx%03d" % (round(W * 100), round(H * 100))
    return done(ctx, b, name, M, "Gateway: two gate posts r %.2f to %.2f, %.1f m apart%s; hang SM_Furn_ChainLink_GateLeaf_* on them."
                % (r, H, W, (", header pipe at %.1f" % header) if header else ""), (W + 2 * r + 0.012, None, H), collision="box", ao=None)


def cage_plinth(ctx, M):
    b = B(314)
    box(b, (0.0, -0.10, 0.0), (3.0, 0.10, 0.50), "conc", ch=0.015)
    return done(ctx, b, "SM_Furn_CagePlinth_300", M, "The Cage's concrete knee wall (05-level 2.10.3): 3.0 x 0.2 x 0.5, solid (tag "
                "cage-plinth); the 3.5 m chain-link panel stands on it.", (3.0, 0.2, 0.5), collision="box", cover=0.5)


def hoop(ctx, M):
    b = B(320, step=0.2)
    box(b, (-0.90, -0.15, 0.0), (-0.66, 0.15, 0.02), "dark", ch=0.003)
    for (bx_, by_) in ((-0.87, -0.12), (-0.87, 0.12), (-0.69, -0.12), (-0.69, 0.12)):
        lathe(b, [(0.0, 0.0), (0.016, 0.0), (0.016, 0.014), (0.0, 0.016)], "dark", 6, loc=(bx_, by_, 0.02))
    pipe(b, [(-0.78, 0, 0.02), (-0.78, 0, 2.75), (-0.50, 0, 3.22), (0.02, 0, 3.30)], 0.057, "dark", bend=0.35, seg=16)
    box(b, (0.02, -0.30, 3.20), (0.08, 0.30, 3.40), "dark")
    for sy in (-1, 1):
        rod(b, (-0.66, 0, 2.95), (0.08, sy * 0.40, 3.02), 0.022, "dark")
        rod(b, (-0.20, 0, 3.27), (0.08, sy * 0.45, 3.80), 0.022, "dark")
    box(b, (0.08, -0.60, 2.925), (0.12, 0.60, 3.975), "dark", ch=0.0)                      # angle frame
    box(b, (0.098, -0.585, 2.94), (0.122, 0.585, 3.96), "cream", ch=0.002)                  # steel board, white
    xf = 0.1235
    for (y0, y1, z0, z1) in ((-0.585, 0.585, 2.94, 2.99), (-0.585, 0.585, 3.91, 3.96), (-0.585, -0.535, 2.99, 3.91), (0.535, 0.585, 2.99, 3.91),
                             (-0.295, 0.295, 3.10, 3.15), (-0.295, 0.295, 3.51, 3.56), (-0.295, -0.245, 3.15, 3.51), (0.245, 0.295, 3.15, 3.51)):
        box(b, (0.122, y0, z0), (xf, y1, z1), "orange", ch=0.0)
    rc = np.array([0.12 + 0.151 + 0.228, 0.0, 3.05])
    t = geo.torus(0.228, 0.009, 40, 8)
    geo.transform(t, loc=tuple(rc))
    b.absorb(t, "orange")
    box(b, (0.124, -0.10, 2.99), (0.14, 0.10, 3.10), "orange")
    box(b, (0.14, -0.03, 3.035), (0.29, 0.03, 3.06), "orange")
    lv = [(0.0, 0.228), (0.13, 0.205), (0.26, 0.175), (0.385, 0.15)]                        # chain net
    P = [[rc + np.array([r * math.cos(2 * math.pi * (j + 0.5 * i) / 12), r * math.sin(2 * math.pi * (j + 0.5 * i) / 12), -dz])
          for j in range(12)] for i, (dz, r) in enumerate(lv)]
    for i in range(len(lv) - 1):
        for j in range(12):
            rod(b, P[i][j], P[i + 1][j], 0.004, "galv", n=5)
            rod(b, P[i][j], P[i + 1][j - 1], 0.004, "galv", n=5)
    return done(ctx, b, "SM_Furn_Hoop", M, "Catalogue hoop: gooseneck steel post at x -0.78 to 3.56 reaching over to a steel backboard "
                "1.2 x 1.05 at x 0.12 (centre z 3.45) facing +X, white with the worn orange border and target modelled as paint, "
                "orange rim r 0.228 at 3.05, chain net 0.385. Pivot: the catalogue origin.", (1.62, 1.2, 3.98), collision="convex")


def bleachers(ctx, M):
    b = B(321, step=0.4)
    seats = [(0.42 + 0.36 * k, -0.73 + 0.47 * k) for k in range(4)]
    for k, (z, yc) in enumerate(seats):
        for y0, y1 in ((yc - 0.13, yc - 0.005), (yc + 0.005, yc + 0.13)):
            box(b, (-2.0, y0, z - 0.045), (2.0, y1, z), "galv", ch=0.006)
        if k:
            box(b, (-2.0, yc - 0.33, z - 0.42 - 0.035), (2.0, yc - 0.14, z - 0.42), "galv", ch=0.005)
    zs = lambda y: 0.05 + (y + 0.93) / 1.88 * 1.40
    for xf in (-1.9, 0.0, 1.9):
        box(b, (xf - 0.025, -0.955, 0.0), (xf + 0.025, -0.905, 0.375), "dark")
        box(b, (xf - 0.025, 0.905, 0.0), (xf + 0.025, 0.955, 1.58), "dark")
        bar(b, (xf, -0.93, 0.05), (xf, 0.93, 1.45), 0.05, 0.05, "dark", up=Z)
        for k, (z, yc) in enumerate(seats):
            bar(b, (xf, yc - 0.15, z - 0.065), (xf, yc + 0.15, z - 0.065), 0.04, 0.04, "dark")
            box(b, (xf - 0.02, yc - 0.02, zs(yc)), (xf + 0.02, yc + 0.02, z - 0.085), "dark")
            if k:
                yf = yc - 0.235
                box(b, (xf - 0.02, yf - 0.02, zs(yf)), (xf + 0.02, yf + 0.02, z - 0.455), "dark")
                bar(b, (xf, yf - 0.1, z - 0.475), (xf, yf + 0.1, z - 0.475), 0.04, 0.04, "dark")
        box(b, (xf - 0.09, -1.0, 0.0), (xf + 0.09, 1.0, 0.012), "dark")
    rod(b, (-2.0, 0.93, 1.58), (2.0, 0.93, 1.58), 0.021, "galv")
    fit(b, (4.0, 1.96, 1.6))
    return done(ctx, b, "SM_Furn_Bleachers", M, "Catalogue bleachers: four-row aluminium bleacher 4.0 x 1.96, plank seats at 0.42, "
                "0.78, 1.14, 1.50 (lowest at the front, -Y), foot boards, three steel frames, back rail at 1.58.", (4.0, 1.96, 1.6),
                collision="complex", ao=None)


def lot_booth(ctx, M):
    b = B(322, step=0.3)
    sign_slot(M, "LotBooth", 1.6, 0.56)
    sign_slot(M, "LotRates", 0.5, 0.65)
    box(b, (-1.1, -0.9, 0.0), (1.1, 0.9, 0.12), "conc", ch=0.01)
    xw, yw, z0, zs_, zh = 1.05, 0.85, 0.12, 1.05, 2.22
    for cx in (-1, 1):
        for cy in (-1, 1):
            box(b, (cx * xw - (0.06 if cx > 0 else 0), cy * yw - (0.06 if cy > 0 else 0), z0),
                (cx * xw + (0 if cx > 0 else 0.06), cy * yw + (0 if cy > 0 else 0.06), zh), "cream", ch=0.004)
    box(b, (-0.99, -yw, z0), (0.99, -yw + 0.03, zs_), "cream")                              # front, steel to the sill
    box(b, (-xw, -0.79, z0), (-xw + 0.03, 0.79, zs_), "cream")                              # -X side
    box(b, (-0.99, yw - 0.03, z0), (0.99, yw, zh), "cream")                                  # blind back
    box(b, (xw - 0.03, 0.30, z0), (xw, 0.79, zs_), "cream")                                  # +X side beside the door
    box(b, (xw - 0.03, -0.79, z0), (xw, -0.75, zh), "cream")
    for (lo, hi) in (((-1.0, -yw - 0.04, zs_), (1.0, -yw + 0.03, zs_ + 0.03)), ((-xw - 0.04, -0.8, zs_), (-xw + 0.03, 0.8, zs_ + 0.03)),
                     ((xw - 0.03, 0.30, zs_), (xw + 0.04, 0.8, zs_ + 0.03))):
        box(b, lo, hi, "cream")                                                              # sills
    for (lo, hi) in (((-0.99, -yw, 2.12), (0.99, -yw + 0.03, zh)), ((-xw, -0.79, 2.12), (-xw + 0.03, 0.79, zh)),
                     ((xw - 0.03, -0.75, 2.12), (xw, 0.79, zh)), ((-0.02, -yw, zs_), (0.02, -yw + 0.03, 2.12))):
        box(b, lo, hi, "cream")                                                              # heads, mullion
    box(b, (-0.99, -yw + 0.01, zs_ + 0.03), (-0.02, -yw + 0.018, 2.12), "glass", ch=0.0)
    box(b, (0.02, -yw + 0.01, zs_ + 0.03), (0.99, -yw + 0.018, 2.12), "glass", ch=0.0)
    box(b, (-xw + 0.01, -0.79, zs_ + 0.03), (-xw + 0.018, 0.79, 2.12), "glass", ch=0.0)
    box(b, (xw - 0.018, 0.30, zs_ + 0.03), (xw - 0.01, 0.79, 2.12), "glass", ch=0.0)
    box(b, (xw - 0.03, 0.25, z0), (xw, 0.30, 2.12), "cream")
    box(b, (xw, -0.74, 0.14), (xw + 0.04, 0.24, 2.10), "cream", ch=0.005)                    # door leaf with a window
    box(b, (xw + 0.039, -0.6, 1.2), (xw + 0.044, 0.1, 1.95), "glass", ch=0.0)
    rod(b, (xw + 0.04, 0.15, 1.0), (xw + 0.07, 0.15, 1.0), 0.008, "chrome")
    rod(b, (xw + 0.07, 0.15, 1.0), (xw + 0.07, 0.03, 1.0), 0.009, "chrome")
    box(b, (-1.1, -0.9, zh), (1.1, 0.9, zh + 0.08), "cream", ch=0.0)                         # roof and lip
    for (lo, hi) in (((-1.1, -0.9, zh), (1.1, -0.87, 2.37)), ((-1.1, 0.87, zh), (1.1, 0.9, 2.37)),
                     ((-1.1, -0.87, zh), (-1.07, 0.87, 2.37)), ((1.07, -0.87, zh), (1.1, 0.87, 2.37))):
        box(b, lo, hi, "cream")
    box(b, (-0.30, 0.05, zh + 0.08), (0.35, 0.60, 2.59), "galv", ch=0.01)                    # roof unit
    box(b, (-0.95, -0.80, 0.97), (0.95, -0.42, 1.0), "plank")                                # counter
    box(b, (-0.25, -0.15, 2.18), (0.25, 0.15, zh), "lens", ch=0.0)
    card(b, (-0.8, -yw - 0.0015, 0.40), (1.6, 0, 0), (0, 0, 0.56), "signLotBooth", sign=True)
    card(b, (xw + 0.0015, 0.30, 0.36), (0, 0.5, 0), (0, 0, 0.65), "signLotRates", sign=True)
    return done(ctx, b, "SM_Furn_LotBooth", M, "Catalogue lot_booth: parking attendant's hut 2.1 x 1.7 on a 2.2 x 1.8 slab, white steel "
                "to a sill at 1.05, glass above on three sides, blind back (+Y), door on +X with a window, flat roof with a lip to "
                "2.37, roof unit to 2.59, counter and ceiling light inside. PARK / 24 HOURS under the front window (M_Sign_LotBooth "
                "1.6 x 0.56), RATES beside the door (M_Sign_LotRates 0.5 x 0.65).", (2.2, 1.8, 2.59), cover=2.37, ao=None)


def street_lamp(ctx, M):
    b = B(330, step=0.3)
    lathe(b, [(0.0, 0.0), (0.24, 0.0), (0.24, 0.04), (0.20, 0.60), (0.0, 0.60)], "galv", 4, rot=(0, 0, 45))
    lathe(b, [(0.13, 0.60), (0.10, 2.5), (0.07, 5.5), (0.06, 7.2), (0.0, 7.2)], "galv", 8, rot=(0, 0, 22.5))
    pipe(b, [(0, 0, 7.0), (0, 0, 7.40), (0, -0.70, 7.76), (0, -1.86, 7.80)], 0.04, "galv", bend=0.35)
    rod(b, (0, -0.02, 6.60), (0, -1.15, 7.70), 0.022, "galv")
    head = geo.sphere(0.5, 24, 12)
    co, _ = geo.arrays(head)
    co *= (0.30, 0.74, 0.16)
    co[:, 2] = np.maximum(co[:, 2], -0.035)
    geo.set_verts(head, co)
    geo.transform(head, loc=(0, -2.16, 7.80))
    b.absorb(head, "galv")
    box(b, (-0.10, -2.42, 7.755), (0.10, -1.98, 7.766), "lens", ch=0.0)
    box(b, (-0.06, 0.205, 0.15), (0.06, 0.212, 0.40), "galv", ch=0.0)                        # base door
    return done(ctx, b, "SM_Furn_StreetLamp", M, "Catalogue street_lamp (and the parking-lot light poles): octagonal tapered steel "
                "pole 7.2 on a transformer base 0.34, davit arm reaching 1.86 toward -Y with a brace, cobra head 0.74 long at "
                "y -2.16, lens at 7.7 (MI_Lamp_Lens; sodium #ffb45e when lit). Galvanised.", (0.34, 2.7, 7.88), collision="box")


def court_light(ctx, M):
    b = B(331, step=0.4)
    lathe(b, [(0.0, 0.0), (0.25, 0.0), (0.25, 0.025), (0.12, 0.03), (0.07, 8.55), (0.0, 8.55)], "galv", 16)
    rod(b, (0, 0, 8.55), (0, 0, 8.72), 0.06, "galv", n=12)
    box(b, (-0.56, -0.04, 8.66), (0.56, 0.04, 8.74), "galv")
    box(b, (-0.04, -0.56, 8.66), (0.04, 0.56, 8.74), "galv")
    for k in range(4):
        h = B(340 + k)
        box(h, (-0.07, -0.21, -0.14), (0.05, 0.21, 0.14), "dark", ch=0.01)
        box(h, (0.05, -0.19, -0.12), (0.056, 0.19, 0.12), "lens", ch=0.0)
        box(h, (-0.11, -0.02, -0.02), (-0.07, 0.02, 0.02), "dark")
        a, t = math.radians(90 * k), math.radians(35)
        Ry = np.array([[math.cos(t), 0, math.sin(t)], [0, 1, 0], [-math.sin(t), 0, math.cos(t)]])
        Rz = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
        Mx = np.eye(4)
        Mx[:3, :3] = Rz @ Ry
        Mx[:3, 3] = Rz @ np.array([0.52, 0, 8.70])
        b.merge(h, Mx)
    return done(ctx, b, "SM_Furn_CourtLight", M, "Catalogue court_light: galvanised mast to 8.55, cross arm at 8.7, four flood heads "
                "0.42 x 0.28 aimed out and 35 deg down (lens #dfe8ff when lit).", (1.3, 1.3, 8.86), collision="box")


def billboard(ctx, M):
    b = B(350, step=0.3)
    sign_slot(M, "Billboard", 9.0, 4.1)
    H, zf = 10.8, 6.7
    for xl in (-2.6, 2.6):                                                                  # riveted box legs 0.34 square
        h = 0.17
        box(b, (xl - h, -h, 0.0), (xl + h, -h + 0.012, H), "elgreen", ch=0.0)
        box(b, (xl - h, h - 0.012, 0.0), (xl + h, h, H), "elgreen", ch=0.0)
        box(b, (xl - h, -h + 0.012, 0.0), (xl - h + 0.012, h - 0.012, H), "elgreen", ch=0.0)
        box(b, (xl + h - 0.012, -h + 0.012, 0.0), (xl + h, h - 0.012, H), "elgreen", ch=0.0)
        zz = np.arange(0.3, H - 0.1, 0.15)
        for sy in (-1, 1):
            for dx in (-0.12, 0.12):
                b.rivets(np.stack([np.full_like(zz, xl + dx), np.full_like(zz, sy * h), zz], 1), (0, sy, 0), "elgreen", d=0.022, h=0.009, leak=0.05)
        for sx in (-1, 1):
            for dy in (-0.12, 0.12):
                b.rivets(np.stack([np.full_like(zz, xl + sx * h), np.full_like(zz, dy), zz], 1), (sx, 0, 0), "elgreen", d=0.022, h=0.009, leak=0.05)
        box(b, (xl - 0.30, -0.17, 0.0), (xl + 0.30, 0.17, 0.03), "elgreen")
    for zr in (0.6, 3.5, 6.3):                                                              # struts and X-bracing
        box(b, (-2.43, -0.05, zr - 0.05), (2.43, 0.05, zr + 0.05), "elgreen")
    for za, zb in ((0.6, 3.5), (3.5, 6.3)):
        bar(b, (-2.43, 0.03, za), (2.43, 0.03, zb), 0.09, 0.012, "elgreen", up=Y)
        bar(b, (-2.43, -0.03, zb), (2.43, -0.03, za), 0.09, 0.012, "elgreen", up=Y)
    for zs_ in (6.85, 7.8, 8.75, 9.7, 10.65):                                                # face stringers
        box(b, (-4.5, -0.35, zs_ - 0.075), (4.5, -0.17, zs_ + 0.075), "elgreen")
    for xu in (-4.42, -1.3, 1.3, 4.42):
        box(b, (xu - 0.04, -0.35, zf), (xu + 0.04, -0.17, H), "elgreen")
    box(b, (-4.5, -0.38, zf), (4.5, -0.35, H), "elgreen", ch=0.0)                           # face sheet
    for (lo, hi) in (((-4.5, -0.42, zf), (4.5, -0.38, zf + 0.08)), ((-4.5, -0.42, H - 0.08), (4.5, -0.38, H)),
                     ((-4.5, -0.42, zf + 0.08), (-4.42, -0.38, H - 0.08)), ((4.42, -0.42, zf + 0.08), (4.5, -0.38, H - 0.08))):
        box(b, lo, hi, "elgreen")
    card(b, (-4.42, -0.3805, zf + 0.08), (8.84, 0, 0), (0, 0, 4.1 - 0.16), "signBillboard", sign=True)
    M["signBillboard"]["mi_tile_m"] = (8.84, 3.94)
    zc = 6.35                                                                               # catwalk grating
    for yg in np.arange(-0.44, -0.97, -0.03):
        box(b, (-4.5, yg - 0.002, zc - 0.03), (4.5, yg + 0.002, zc), "elgreen", ch=0.0)
    for xg in np.arange(-4.45, 4.5, 0.10):
        box(b, (xg - 0.003, -0.98, zc - 0.012), (xg + 0.003, -0.42, zc - 0.006), "elgreen", ch=0.0)
    box(b, (-4.5, -0.98, zc - 0.03), (4.5, -0.97, zc + 0.10), "elgreen", ch=0.0)            # toe board
    for xb in (-4.4, -2.6, 2.6, 4.4):                                                       # brackets
        box(b, (xb - 0.04, -0.98, zc - 0.10), (xb + 0.04, -0.17, zc - 0.03), "elgreen")
        bar(b, (xb, -0.17, zc - 0.9), (xb, -0.95, zc - 0.10), 0.06, 0.06, "elgreen", up=X)
    for xp in np.linspace(-4.45, 4.45, 7):                                                  # railing
        box(b, (xp - 0.025, -0.975, zc), (xp + 0.025, -0.925, zc + 1.07), "elgreen")
    for zr in (zc + 0.55, zc + 1.07):
        rod(b, (-4.5, -0.95, zr), (4.5, -0.95, zr), 0.022, "elgreen")
    for xa in (-3.3, -1.1, 1.1, 3.3):                                                       # lamp arms aimed up the face
        rod(b, (xa, -0.93, zc + 1.07), (xa, -0.70, zc + 1.30), 0.022, "elgreen")
        h = B(360)
        box(h, (-0.17, -0.09, -0.07), (0.17, 0.09, 0.07), "dark", ch=0.01)
        box(h, (-0.15, -0.075, 0.07), (0.15, 0.075, 0.075), "lens", ch=0.0)
        t = math.radians(-40)
        Mx = np.eye(4)
        Mx[:3, :3] = [[1, 0, 0], [0, math.cos(t), -math.sin(t)], [0, math.sin(t), math.cos(t)]]
        Mx[:3, 3] = (xa, -0.68, zc + 1.36)
        b.merge(h, Mx)
    for zl in np.arange(0.6, zc, 0.30):                                                     # ladder on the +X leg
        rod(b, (2.79, -0.13, zl), (2.79, 0.13, zl), 0.011, "elgreen", n=6)
    for yl in (-0.14, 0.14):
        box(b, (2.77, yl - 0.025, 0.5), (2.81, yl + 0.025, zc + 1.0), "elgreen")
    for zl in (1.0, 3.5, 6.0):
        box(b, (2.77, -0.03, zl - 0.02), (2.81, 0.03, zl + 0.02), "elgreen")
    return done(ctx, b, "SM_Furn_Billboard", M, "Catalogue billboard: two riveted box legs 0.34 square at x +-2.6, struts and "
                "X-bracing, face 9.0 x 4.1 from 6.7 to 10.8 facing -Y (M_Sign_Billboard on the 8.84 x 3.94 face inside the frame: "
                "the IPX billboard art), catwalk of bar grating at 6.35 with toe board and railing, four lamp arms aimed up the face, "
                "ladder on the +X leg. El green steel.", (9.0, 1.15, 10.8), collision="complex", ao=None)


def ccw(prof):
    P = np.asarray(prof)
    a = 0.5 * np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1])
    return prof if a > 0 else prof[::-1]


def rollup_door(ctx, M, W, H, closed):
    b = B(370, step=0.5)
    pitch = mat.scan_tile("TS_Shutter_ScanGrey")[1] / 27
    zb = 0.0 if closed else H - 0.55
    zz = np.arange(zb, H + 1e-6, pitch / 4)
    f = np.cos(2 * np.pi * (zz - zb) / pitch)
    yf = 0.43 - 0.006 * f
    prof = ccw([(y, z) for y, z in zip(yf, zz)] + [(y + 0.010, z) for y, z in zip(yf[::-1], zz[::-1])])
    b.prism(prof, (0.0, 0, 0), Y, Z, (W, 0, 0), "shutter", pstep=1.0, uv_off=(0.0, 0.0))
    box(b, (0.0, 0.405, zb), (W, 0.455, zb + 0.05), "dark")                                  # bottom bar
    if closed:
        for xh in (W * 0.25, W * 0.75):
            box(b, (xh - 0.08, 0.40, 0.25), (xh + 0.08, 0.405, 0.30), "dark")
        box(b, (W / 2 - 0.05, 0.395, 0.06), (W / 2 + 0.05, 0.405, 0.16), "chrome")
    for xr in (-0.09, W + 0.01):                                                             # guide rails at the jambs
        box(b, (xr, 0.40, 0.0), (xr + 0.08, 0.47, H + 0.05), "dark")
    box(b, (-0.10, 0.40, H + 0.02), (W + 0.10, 0.82, H + 0.36), "dark", ch=0.01)            # roller housing
    for xe in (-0.10, W + 0.094):
        box(b, (xe, 0.40, H), (xe + 0.006, 0.84, H + 0.40), "dark")
    state = "closed" if closed else "open"
    return done(ctx, b, "SM_Furn_RollUpDoor_%03dx%03d_%s" % (round(W * 100), round(H * 100), state.title()), M,
                "Roll-up garage door for a %.1f x %.1f opening (05-level 2.6.2), %s%s: ribbed slat curtain (TS_Shutter_ScanGrey, "
                "slat pitch matched to the scan) in guide rails at both jambs on the inside face, roller housing %.1f x 0.42 x 0.34 "
                "above the head, bottom bar. Wall-module frame: pivot at the bottom of the left jamb on the wall's outer face "
                "(y 0), the wall 0.40 thick toward +Y." % (W, H, state, ": 0.55 m of slats under the bottom bar" if not closed else
                " with lift handles and a lock", W + 0.2), (W + 0.2, None, H + 0.4), collision="box" if closed else "none", ao=None,
                ground=closed)


WALL_T, WALL_H = 0.40, 6.90


def wall_skin(b, x0, x1, z0, z1):
    """Outer block face and the dado inside (teal to 1.35, yellow stripe to 1.42) on a solid piece of wall."""
    bx(b, (x0, 0.0, z0), (x1, WALL_T, z1), "block", axis="z")
    for za, zc, slot in ((0.0, 1.35, "dadoTeal"), (1.35, 1.42, "dadoYellow")):
        a, c = max(za, z0), min(zc, z1)
        if c > a:
            bx(b, (x0, WALL_T, a), (x1, WALL_T + 0.002, c), slot, axis="x")


def coping(b, W):
    bx(b, (-0.0, -0.025, WALL_H - 0.08), (W, WALL_T + 0.025, WALL_H), "conc", ch=0.01, axis="x")


def block_wall(ctx, M, W):
    b = B(380, step=0.4)
    wall_skin(b, 0.0, W, 0.0, WALL_H - 0.08)
    coping(b, W)
    return done(ctx, b, "SM_Furn_BlockWall_%03d" % round(W * 100), M, "Cinder-block wall module of the auto body shop (05-level 2.6.1): "
                "%.1f m wide, 0.40 thick, ground to 6.82 with an 8 cm concrete coping to 6.90 (parapet top). Painted block outside "
                "(MI_Block_PaintedGrey #8a8880), dark teal dado to 1.35 with a yellow stripe to 1.42 inside. Pivot bottom-left of "
                "the outer face, running +X, outer face -Y." % W, (W, WALL_T + 0.05, WALL_H), collision="box", ao=None)


def block_opening(ctx, M, ow, oh, pier=0.2):
    b = B(381, step=0.4)
    W = ow + 2 * pier
    x0, x1 = pier, pier + ow
    wall_skin(b, 0.0, x0, 0.0, WALL_H - 0.08)
    wall_skin(b, x1, W, 0.0, WALL_H - 0.08)
    wall_skin(b, x0, x1, oh + 0.212, WALL_H - 0.08)
    coping(b, W)
    for y0, s_ in ((0.0, 1), (WALL_T, -1)):                                                 # steel angle lintels, bearing 0.2
        ya, yb_ = (y0 - 0.012, y0) if s_ > 0 else (y0, y0 + 0.012)
        bx(b, (x0 - pier, ya, oh), (x1 + pier, yb_, oh + 0.212), "dark", axis="x")
        yc, yd = (y0, y0 + 0.15) if s_ > 0 else (y0 - 0.15, y0)
        bx(b, (x0 - pier, yc, oh), (x1 + pier, yd, oh + 0.012), "dark", axis="x")
    for xj, s_ in ((x0, -1), (x1, 1)):                                                      # yellow jamb guards
        xa, xc = (xj - 0.10, xj) if s_ < 0 else (xj, xj + 0.10)
        bx(b, (xa, -0.008, 0.0), (xc, 0.0, 1.2), "yellow", axis="z")
        xa, xc = (xj - 0.008, xj) if s_ < 0 else (xj, xj + 0.008)
        bx(b, (xa, 0.0, 0.0), (xc, 0.10, 1.2), "yellow", axis="z")
    return done(ctx, b, "SM_Furn_BlockWall_Opening_%03dx%03d" % (round(ow * 100), round(oh * 100)), M,
                "Cinder-block wall module with a %.1f x %.1f door opening (05-level 2.6.2) between %.1f m piers: steel angle lintels "
                "inside and out bearing 0.2 into the piers, yellow steel jamb guards to 1.2, coping to 6.90. Pair with "
                "SM_Furn_RollUpDoor_%03dx%03d_* at x %.1f. Pivot bottom-left of the outer face, running +X, outer face -Y."
                % (ow, oh, pier, round(ow * 100), round(oh * 100), pier), (W, None, WALL_H), collision="complex", ao=None)


def block_door(ctx, M):
    b = B(382, step=0.4)
    W, x0, x1, oh = 2.8, 0.4, 2.4, 2.5
    wall_skin(b, 0.0, x0, 0.0, WALL_H - 0.08)
    wall_skin(b, x1, W, 0.0, WALL_H - 0.08)
    wall_skin(b, x0, x1, oh + 0.2, WALL_H - 0.08)
    coping(b, W)
    bx(b, (x0 - 0.2, -0.004, oh), (x1 + 0.2, WALL_T + 0.004, oh + 0.2), "conc", ch=0.008, axis="x")   # precast lintel
    for (lo, hi) in (((x0, -0.01, 0.0), (x0 + 0.05, WALL_T, 2.50)), ((x1 - 0.05, -0.01, 0.0), (x1, WALL_T, 2.50)),
                     ((x0, -0.01, 2.42), (x1, WALL_T, 2.50))):
        bx(b, lo, hi, "dark", ch=0.003)                                                     # pressed steel frame
    bx(b, (x0 - 0.02, -0.014, 0.0), (x0 + 0.002, -0.01, 2.52), "dark")
    bx(b, (x1 - 0.002, -0.014, 0.0), (x1 + 0.02, -0.01, 2.52), "dark")
    bx(b, (x0 - 0.02, -0.014, 2.50), (x1 + 0.02, -0.01, 2.52), "dark")
    return done(ctx, b, "SM_Furn_BlockWall_Door_200x250", M, "Cinder-block wall module 2.8 wide with the 2.0 x 2.5 side-door "
                "opening (05-level 2.6.2): precast concrete lintel, pressed steel frame (head 2.42-2.50) for SM_Furn_SteelDoor_190x242 "
                "hinged at x 0.45. Pivot bottom-left of the outer face, outer face -Y.", (W, None, WALL_H), collision="complex", ao=None)


def steel_door(ctx, M):
    b = B(383, step=0.3)
    w, h, t = 1.9, 2.42, 0.045
    box(b, (0.0, -t, 0.0), (w, 0.0, h), "grey", ch=0.003)
    for (lo, hi) in (((0.12, -t - 0.003, 0.12), (w - 0.12, -t, 0.16)), ((0.12, -t - 0.003, h - 0.16), (w - 0.12, -t, h - 0.12)),
                     ((0.12, -t - 0.003, 0.16), (0.16, -t, h - 0.16)), ((w - 0.16, -t - 0.003, 0.16), (w - 0.12, -t, h - 0.16))):
        box(b, lo, hi, "grey", ch=0.001)                                                     # pressed panel border
    box(b, (0.05, -t - 0.0025, 0.02), (w - 0.05, -t, 0.27), "galv", ch=0.0)                  # kick plate
    box(b, (w - 0.20, -t - 0.003, 1.1), (w - 0.10, -t, 1.45), "galv", ch=0.0)                # push plate
    rod(b, (w - 0.15, -t, 1.0), (w - 0.15, -t - 0.06, 1.0), 0.009, "chrome")
    rod(b, (w - 0.15, -t - 0.06, 1.0), (w - 0.30, -t - 0.06, 1.0), 0.010, "chrome")
    lathe(b, [(0.0, 0.0), (0.022, 0.0), (0.022, 0.03), (0.0, 0.035)], "chrome", 12, loc=(w - 0.15, -t, 1.0), rot=(90, 0, 0))
    for zh in (0.25, 1.2, 2.15):
        lathe(b, [(0.0, -0.055), (0.012, -0.055), (0.012, 0.055), (0.0, 0.055)], "grey", 12, loc=(-0.006, -t / 2, zh))
    return done(ctx, b, "SM_Furn_SteelDoor_190x242", M, "Steel side door leaf 1.9 x 2.42 x 0.045 (05-level 2.6.2: swung back flat "
                "against the alley wall): pressed panel border, kick plate, push plate, lever handle, three hinges. Pivot: the hinge "
                "axis at the bottom, outer face -Y.", (1.918, None, 2.42), collision="box", ao=None)


def structures(ctx, M):
    M["grey"] = ctx.scan_set("TS_Steel_ScanPaintGrey", blend="TS_Steel_ScanRust", blend_start=0.40, macro=0.12,
                             leak_color=(0.24, 0.10, 0.035), leak_rough=0.1, dirt_color=(0.03, 0.028, 0.026), alpha="splash")
    sidewalk_shed(ctx, M)
    shed_stair(ctx, M)
    for L, H, extra, note in ((3.0, 2.4, None, "Catalogue fence_panel."), (3.0, 4.0, 1.5, "Catalogue fence_tall (mid rail at 2.0, centre post)."),
                              (2.4, 2.5, None, "The Vultures' roadblock fence (posts every 2.4)."),
                              (2.5, 2.6, None, "The alley gate fence (posts every 2.5)."),
                              (3.0, 3.5, None, "The Cage: stands on SM_Furn_CagePlinth_300 (mesh to 4.0 above the court).")):
        chain_panel(ctx, M, L, H, "SM_Furn_ChainLink_%03dx%03d" % (round(L * 100), round(H * 100)), extra_post=extra, note=note)
    for H in (2.4, 2.5, 2.6, 3.5, 4.0):
        chain_endpost(ctx, M, H)
    gate_leaf(ctx, M, 1.45)
    gate_leaf(ctx, M, 1.58)
    gate_posts(ctx, M, 3.0, 4.5, 0.07, header=4.4)
    gate_posts(ctx, M, 3.2, 2.75, 0.06)
    cage_plinth(ctx, M)
    hoop(ctx, M)
    bleachers(ctx, M)
    lot_booth(ctx, M)
    street_lamp(ctx, M)
    court_light(ctx, M)
    billboard(ctx, M)
    rollup_door(ctx, M, 6.0, 4.3, False)
    rollup_door(ctx, M, 3.8, 3.5, False)
    rollup_door(ctx, M, 6.0, 4.3, True)
    block_wall(ctx, M, 2.0)
    block_opening(ctx, M, 6.0, 4.3)
    block_opening(ctx, M, 3.8, 3.5)
    block_door(ctx, M)
    steel_door(ctx, M)


# ---------------------------------------------------------------------------------------------------------- build

def build(ctx):
    ctx.built = []
    M = materials(ctx)
    street(ctx, M)
    if "structures" in globals():
        structures(ctx, M)
    return ctx.built


# -------------------------------------------------------------------------------------------------------- preview

STREET_LAYOUT = {   # name: (x, y, yaw) -- three rows, fronts toward the camera (-Y)
    "SM_Furn_BusShelter": (-4.9, 4.2, 0), "SM_Furn_PalletStack_A": (-1.9, 4.0, 8), "SM_Furn_Sandbags": (0.4, 4.0, 0),
    "SM_Furn_JerseyBarrier": (3.4, 4.0, 0), "SM_Furn_Barricade": (6.6, 4.0, 0),
    "SM_Furn_Dumpster": (-5.3, 1.6, 0), "SM_Furn_Dumpster_Shut": (-3.0, 1.6, 0), "SM_Furn_TyreStack_A": (-1.2, 1.5, 0),
    "SM_Furn_TyreStack_B": (-0.3, 1.6, 30), "SM_Furn_MilkCrates_A": (0.6, 1.5, 10), "SM_Furn_MilkCrates_B": (1.45, 1.6, -15),
    "SM_Furn_ShoppingCart": (2.6, 1.4, -30), "SM_Furn_TrashBags_A": (4.0, 1.5, 0), "SM_Furn_TrashBags_B": (5.5, 1.6, 20),
    "SM_Furn_Mattress": (7.4, 1.6, 75),
    "SM_Furn_Mailbox": (-5.6, -0.6, 0), "SM_Furn_NewspaperBox": (-4.9, -0.6, 0), "SM_Furn_ParkingMeter": (-4.3, -0.6, 0),
    "SM_Furn_SignPost": (-3.8, -0.5, 0), "SM_Furn_Bollard": (-3.3, -0.6, 0), "SM_Furn_TrafficBarrel": (-2.6, -0.6, 0),
    "SM_Furn_TrafficCone": (-1.9, -0.7, 0), "SM_Furn_OilDrum_Blue": (-1.25, -0.6, 0), "SM_Furn_OilDrum_Green": (-0.6, -0.6, 0),
    "SM_Furn_OilDrum_Grey": (0.05, -0.6, 0), "SM_Furn_MilkCrate": (0.75, -0.7, 20), "SM_Furn_Pallet": (2.0, -0.6, 0),
}
STRUCT_LAYOUT = {
    "SM_Furn_BlockWall_Opening_600x430": (-25.0, 14.0, 0), "SM_Furn_RollUpDoor_600x430_Closed": (-24.8, 14.0, 0),
    "SM_Furn_BlockWall_200": (-18.6, 14.0, 0), "SM_Furn_BlockWall_Door_200x250": (-16.6, 14.0, 0),
    "SM_Furn_SteelDoor_190x242": (-16.15, 13.96, -100), "SM_Furn_BlockWall_Opening_380x350": (-13.8, 14.0, 0),
    "SM_Furn_RollUpDoor_380x350_Open": (-13.6, 14.0, 0),
    "SM_Furn_ShedStair": (-8.6, 13.25, 0), "SM_Furn_SidewalkShed": (-5.0, 14.0, 0), "SM_Furn_Billboard": (18.5, 17.0, 0),
    "SM_Furn_Hoop": (-9.5, -6.0, -90), "SM_Furn_Bleachers": (-16.5, 6.0, 0), "SM_Furn_LotBooth": (-11.5, 6.0, 0),
    "SM_Furn_StreetLamp": (-7.5, 6.5, 0), "SM_Furn_CourtLight": (14.0, 6.0, 0), "SM_Furn_RollUpDoor_600x430_Open": (16.5, 6.5, 0),
    "SM_Furn_CagePlinth_300": (-16.0, 0.0, 0), "SM_Furn_ChainLink_300x350": (-16.0, 0.0, 0), "SM_Furn_ChainLink_EndPost_350": (-13.0, 0.0, 0),
    "SM_Furn_ChainLink_300x240": (-11.5, 0.0, 0), "SM_Furn_ChainLink_EndPost_240": (-8.5, 0.0, 0),
    "SM_Furn_ChainLink_300x400": (3.0, -8.0, 0), "SM_Furn_ChainLink_EndPost_400": (6.0, -8.0, 0),
    "SM_Furn_ChainLink_240x250": (-2.5, 0.0, 0), "SM_Furn_ChainLink_EndPost_250": (-0.1, 0.0, 0),
    "SM_Furn_ChainLink_250x260": (1.4, 0.0, 0), "SM_Furn_ChainLink_EndPost_260": (3.9, 0.0, 0),
    "SM_Furn_ChainLink_GateFrame_300x450": (5.5, 0.0, 0), "SM_Furn_ChainLink_GateLeaf_145x220": (5.5, 0.0, -70),
    "SM_Furn_ChainLink_GateFrame_320x275": (10.0, 0.0, 0), "SM_Furn_ChainLink_GateLeaf_158x220": (13.2, 0.0, -110),
}


def _scale_box(loc):
    b = geo.box((0.4, 0.4, 1.8), bevel=0.01, name="ScaleBox_1m80")
    geo.transform(b, loc=loc)
    b.data.materials.append(mat.flat("M_Preview_Grey", (0.18, 0.18, 0.18), 0.8))
    scene.move_to(b, scene.collection("Rig"))
    return b


def _place(assets, layout, z=None):
    for n, ob in assets.items():
        ob.hide_render = n not in layout
        if n in layout:
            x, y, yaw = layout[n]
            ob.location = (x, y, 0.5 if (z and n in z) else 0.0)
            ob.rotation_euler = (0, 0, math.radians(yaw))
            ob["mi_placed"] = True


def on_preview(ctx, objs):
    a = ctx.args
    only = set(a.only or [])
    assets = {n: v["ob"] for n, v in ctx.assets.items()}
    render.setup(samples=a.samples, res=(1280, 720))
    render.rig_day(sun_azimuth=render.DESIGN_SUN_BEARING)
    render.backdrop(color=(0.16, 0.155, 0.15))
    if not only or "furniture_street" in only:
        _place(assets, STREET_LAYOUT)
        box = _scale_box((-6.9, 1.6, 0))
        render.cam_look((0.6, -8.6, 2.6), (0.7, 1.7, 0.75), lens=21)
        p, sec = render.render_jpeg(os.path.join(paths.previews, "furniture_street.jpg"), a.samples)
        ctx.log("preview %s %.0fs" % (p, sec))
        bpy.data.objects.remove(box, do_unlink=True)
    if not only or "furniture_structures" in only:
        _place(assets, STRUCT_LAYOUT, z={"SM_Furn_ChainLink_300x350"})
        box = _scale_box((-7.0, -6.6, 0))
        render.cam_look((-2.0, -19.0, 5.0), (-1.5, 8.0, 3.4), lens=24)
        p, sec = render.render_jpeg(os.path.join(paths.previews, "furniture_structures.jpg"), a.samples)
        ctx.log("preview %s %.0fs" % (p, sec))
        bpy.data.objects.remove(box, do_unlink=True)
    for ob in assets.values():
        ob.location, ob.rotation_euler, ob.hide_render = (0, 0, 0), (0, 0, 0), False
