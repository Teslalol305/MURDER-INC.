"""Modelled car parts shared by the vehicle family: everything a close camera reads on a car, built by script with
per-vehicle parameters, so generated bodies only have to supply the large painted shell.

    from mi import carparts as cp
    parts = cp.wheel("cap", r=0.325, tw=0.21, rim_r=0.22)          # {slot key: [objects]}, axle along Y, outboard +Y
    parts = cp.headlamp(0.34, 0.15)                                 # lens front at x = 0, facing +X
    parts = cp.tail_lamp(0.30, 0.14, (("red", 0.6), ("amber", 0.2), ("clear", 0.2)))
    parts = cp.interior(dict(cowl=0.98, belt=1.02, floor=0.36, roof=1.38, hw=0.70, bpillar=-0.20, ...))
    cp.place(parts, loc=(1.4, 0.8, 0.3), rot=(0, 0, 10))            # move every object of a part dict
    cp.flatten_flank(shell, side=1, ...)                            # generated flank onto a smooth fitted surface
    cp.cut_groove(shell, side=1, p0=(x, z), p1=(x, z), ...)         # a real shut line, 5 mm wide, dark inner face

Every builder returns a dict {slot key: [objects]}; the caller maps the keys to materials. Keys used here:
tyre, steel (painted wheel steel), alloy (wheel alloy / silver plastic), chrome, black (black plastic), brake (cast
iron), reflector (lamp chrome), lens_clear, lens_red, lens_amber, bulb, mirror, cabin (dash and trim plastic),
seat (cloth), carpet, gauge (light print of the dials), glass (window), paint (body colour).
Conventions as the rest of mi: metres, Z up, nose +X; wheels are built around the axle (Y) with the outboard face
at +Y; lamps face +X (turn a tail lamp by 180 degrees); mirrors stick out along +Y.
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from . import geo


# ----------------------------------------------------------------------------------------------------- helpers
def _add(d, key, *obs):
    d.setdefault(key, []).extend(o for o in obs if o is not None)
    return d


def merge(*ds):
    out = {}
    for d in ds:
        for k, v in d.items():
            out.setdefault(k, []).extend(v)
    return out


def objects(d):
    return [o for v in d.values() for o in v]


def place(d, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    """Bake a transform into every object of a part dict (rot XYZ euler in degrees, applied before loc)."""
    for o in objects(d):
        geo.transform(o, rot=rot, scale=scale)
        geo.transform(o, loc=loc)
    return d


def orient(ob, d):
    """Flip the mesh when its faces look away from direction d on average."""
    me = ob.data
    if not len(me.polygons):
        return ob
    n = np.empty(len(me.polygons) * 3)
    me.polygons.foreach_get("normal", n)
    a = np.empty(len(me.polygons))
    me.polygons.foreach_get("area", a)
    if ((n.reshape(-1, 3) @ np.asarray(d, dtype=float)) * a).sum() < 0:
        me.flip_normals()
        me.update()
    return ob


def solid(ob, t, offset=-1.0):
    md = ob.modifiers.new("Solid", "SOLIDIFY")
    md.thickness = t
    md.offset = offset
    md.use_even_offset = True
    geo._apply_modifier(ob, md)
    return ob


def grid(name, us, vs, fn, closed_u=False, smooth=40.0):
    """Quad-grid surface: fn(U, V) -> (X, Y, Z) arrays over meshgrid(us, vs, indexing='ij')."""
    us, vs = np.asarray(us, float), np.asarray(vs, float)
    U, V = np.meshgrid(us, vs, indexing="ij")
    X, Y, Z = fn(U, V)
    verts = np.stack([np.broadcast_to(X, U.shape), np.broadcast_to(Y, U.shape), np.broadcast_to(Z, U.shape)], -1)
    nu, nv = len(us), len(vs)
    i = np.arange(nu if closed_u else nu - 1)[:, None]
    j = np.arange(nv - 1)[None, :]
    i1 = (i + 1) % nu
    f = np.stack([i * nv + j, i1 * nv + j, i1 * nv + j + 1, i * nv + j + 1], -1).reshape(-1, 4)
    return geo.from_arrays(name, verts.reshape(-1, 3), f, smooth=smooth)


def lathe(profile, angles, name="Lathe", smooth=40.0):
    """Revolve a (radius, z) profile around Z at the given angles (radians, a closed ring)."""
    P = np.asarray(profile, float)
    A = np.asarray(angles, float)
    return grid(name, A, np.arange(len(P)), lambda a, j: (P[j.astype(int), 0] * np.cos(a), P[j.astype(int), 0] * np.sin(a),
                                                        P[j.astype(int), 1]), closed_u=True, smooth=smooth)


def loft(name, sections, closed=True, cap=True, smooth=40.0):
    """Skin through cross-sections (each an (m, 3) array of points, same m). closed: each section is a loop."""
    S = np.asarray(sections, float)
    n, m, _ = S.shape
    verts = S.reshape(-1, 3)
    faces = []
    cols = m if closed else m - 1
    for i in range(n - 1):
        for j in range(cols):
            j1 = (j + 1) % m
            faces.append((i * m + j, i * m + j1, (i + 1) * m + j1, (i + 1) * m + j))
    if cap and closed:
        faces.append(tuple(range(m - 1, -1, -1)))
        faces.append(tuple((n - 1) * m + j for j in range(m)))
    ob = geo.from_arrays(name, verts, faces, smooth=smooth)
    geo.recalc_normals(ob)
    return ob


def rbox(size, r=0.01, name="RBox", seg=2):
    """Centred box with rounded edges."""
    return geo.box(size, bevel=r, segments=seg, base=False, name=name)


def rounded_rect(w, h, r, n=4):
    """Closed (y, z) outline of a rounded rectangle, counter-clockwise."""
    r = min(r, 0.49 * w, 0.49 * h)
    pts = []
    for cy, cz, a0 in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cy + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def arc_text(body, radius, size, depth, centre_deg=90.0, inside=False, name="ArcText", res=2):
    """Raised lettering bent round a circle in XY (z from 0 to depth), like geo.text_on_arc but light (no bevel,
    low curve resolution): tyre sidewalls."""
    letters, widths = [], []
    for ch in body:
        if ch == " ":
            letters.append(None)
            widths.append(size * 0.45)
            continue
        o = geo.text(ch, size, depth, 0.0, name="chr", align="CENTER", resolution=res)
        co, _ = geo.arrays(o)
        letters.append(o)
        widths.append(max(float(co[:, 0].max() - co[:, 0].min()), size * 0.25) + size * 0.14)
    total = sum(widths)
    a0 = math.radians(centre_deg) + (total / radius / 2 if not inside else -total / radius / 2)
    out, run = [], 0.0
    for o, w in zip(letters, widths):
        mid = run + w / 2
        run += w
        if o is None:
            continue
        a = a0 - mid / radius if not inside else a0 + mid / radius
        rot = math.degrees(a) - 90 if not inside else math.degrees(a) + 90
        geo.transform(o, loc=(radius * math.cos(a), radius * math.sin(a), 0), rot=(0, 0, rot))
        out.append(o)
    return geo.join(out, name) if out else None


def _to_y(d):
    """Parts built around +Z (outboard +Z) turned so the axle runs along Y, outboard +Y."""
    for o in objects(d):
        geo.transform(o, rot=(-90, 0, 0))
    return d


# ------------------------------------------------------------------------------------------------------- tyres
def tyre(r, tw, rim_r, pitches=30, name="Tyre", text=("QUEENSWAY  RADIAL", "205/65 R15  TUBELESS  STEEL BELTED"),
         grooves=3, lug=0.22, depth=None, side_rings=48):
    """Tyre around +Z (outboard +Z): rounded shoulders, circumferential grooves, lateral shoulder grooves on a
    pitch, sidewall bulge with a rim-protector rib and a fine ring, raised invented lettering on the outboard
    sidewall. Returns the object."""
    h = r - rim_r
    w = tw / 2
    wt = w * 0.80                       # half width of the tread
    d = depth or min(0.009, 0.08 * h)   # groove depth
    gw = 0.11 * wt                      # circumferential groove width
    P = [(rim_r + 0.002, -w * 0.78), (rim_r + 0.012, -w * 0.88), (rim_r + 0.35 * h, -w * 0.98),
         (rim_r + 0.65 * h, -w * 1.0), (r - 0.18 * h, -w * 0.96), (r - 0.06 * h, -w * 0.90), (r - 0.012, -wt * 1.04)]
    gc = [-0.5, 0.0, 0.5] if grooves == 3 else ([-0.35, 0.35] if grooves == 2 else [-0.55, -0.18, 0.18, 0.55])
    P.append((r, -wt))
    for g in gc:
        u = g * wt
        P += [(r, u - gw / 2 - 0.002), (r - d, u - gw / 2 + 0.0015), (r - d, u + gw / 2 - 0.0015), (r, u + gw / 2 + 0.002)]
    P.append((r, wt))
    P += [(r - 0.012, wt * 1.04), (r - 0.06 * h, w * 0.90), (r - 0.18 * h, w * 0.96), (rim_r + 0.65 * h, w * 1.0),
          (rim_r + 0.42 * h, w * 0.985), (rim_r + 0.37 * h, w * 0.995), (rim_r + 0.33 * h, w * 0.995),
          (rim_r + 0.28 * h, w * 0.975), (rim_r + 0.14 * h, w * 0.95), (rim_r + 0.09 * h, w * 0.985),
          (rim_r + 0.05 * h, w * 0.975), (rim_r + 0.012, w * 0.88), (rim_r + 0.002, w * 0.78)]
    # the tread band (from shoulder to shoulder) on the pitch rings: per pitch a lateral groove with steep walls;
    # the sidewalls on 64 plain rings, overlapping the band by a millimetre at the shoulders
    k0 = 5
    k1 = len(P) - 13
    fr = np.array([0.0, 0.035, 0.035 + lug * 0.75, 0.07 + lug * 0.75])
    ang = (np.arange(pitches)[:, None] + fr[None, :]).ravel() * 2 * np.pi / pitches
    band = lathe(P[k0:k1 + 1], ang, name=name, smooth=None)
    co, _ = geo.arrays(band)
    rr = np.hypot(co[:, 0], co[:, 1])
    z = co[:, 2]
    a = np.mod(np.arctan2(co[:, 1], co[:, 0]), 2 * np.pi) / (2 * np.pi / pitches)
    ph = a - np.floor(a + 1e-6)
    in_groove = (ph > 0.02) & (ph < 0.06 + lug * 0.75)
    shoulder = (np.abs(z) > (gc[-1] * wt + gw / 2 + 0.001)) & (rr > r - 0.30 * h)
    sink = np.where(in_groove & shoulder, d * np.clip((rr - (r - 0.30 * h)) / (0.30 * h), 0.0, 1.0) ** 0.5, 0.0)
    s = (rr - sink) / np.maximum(rr, 1e-9)
    co[:, 0] *= s
    co[:, 1] *= s
    geo.set_verts(band, co)
    sa = np.linspace(0, 2 * np.pi, side_rings, endpoint=False)
    Pi = P[:k0 + 1]
    Pi[-1] = (Pi[-1][0] + 0.001, Pi[-1][1])
    Po = P[k1:]
    Po[0] = (Po[0][0] + 0.001, Po[0][1])
    sw_in = lathe(Pi, sa, name=name + "_SwIn", smooth=None)
    sw_out = lathe(Po, sa, name=name + "_SwOut", smooth=None)
    for o, dz in ((band, None), (sw_in, -1.0), (sw_out, 1.0)):
        me = o.data
        n = np.empty(len(me.polygons) * 3)
        me.polygons.foreach_get("normal", n)
        c = np.empty(len(me.polygons) * 3)
        me.polygons.foreach_get("center", c)
        n, c = n.reshape(-1, 3), c.reshape(-1, 3)
        if dz is None:                       # tread faces look away from the axle
            tr = np.hypot(c[:, 0], c[:, 1]) > r - 0.004
            bad = (n[tr, 0] * c[tr, 0] + n[tr, 1] * c[tr, 1]).sum() < 0
        else:                                # sidewalls look outboard / inboard
            bad = (n[:, 2] * dz).sum() < 0
        if bad:
            me.flip_normals()
            me.update()
    ob = geo.join([band, sw_in, sw_out], name)
    geo.smooth_by_angle(ob, 38)
    parts = [ob]
    if text:
        size = min(0.30 * h, 0.034)
        for body, cen, ins, sz, rad, zt in ((text[0], 90.0, False, size, rim_r + 0.62 * h, w * 1.0),
                                            (text[1], 270.0, True, size * 0.40, rim_r + 0.83 * h, w * 0.975)):
            if not body:
                continue
            t = arc_text(body, rad - (sz * 0.5 if not ins else -sz * 0.5), sz, 0.0016, centre_deg=cen, inside=ins,
                         name=name + "_Text")
            if t is not None:
                geo.transform(t, loc=(0, 0, zt - 0.0006))
                parts.append(t)
    return geo.join(parts, name)


# -------------------------------------------------------------------------------------------------- wheel faces
def _barrel(rim_r, w, name):
    """Rim barrel (well, bead seats, flanges), 4 mm wall, around +Z."""
    prof = [(rim_r + 0.016, -w * 0.88), (rim_r + 0.004, -w * 0.84), (rim_r, -w * 0.76), (rim_r, -w * 0.50),
            (rim_r - 0.028, -w * 0.34), (rim_r - 0.028, w * 0.30), (rim_r, w * 0.46), (rim_r, w * 0.76),
            (rim_r + 0.006, w * 0.84), (rim_r + 0.017, w * 0.88), (rim_r + 0.020, w * 0.86)]
    ob = geo.revolve(prof, 40, name=name)
    me = ob.data                              # one-sided, looking at the axle (seen from outside through the face)
    c = np.empty(len(me.polygons) * 3)
    me.polygons.foreach_get("center", c)
    n = np.empty(len(me.polygons) * 3)
    me.polygons.foreach_get("normal", n)
    c, n = c.reshape(-1, 3), n.reshape(-1, 3)
    if (n[:, 0] * c[:, 0] + n[:, 1] * c[:, 1]).sum() > 0:
        me.flip_normals()
        me.update()
    return ob


def _nuts(n, rad, z, size=0.0105, name="Nut", start=0.0):
    out = []
    for i in range(n):
        a = start + 2 * math.pi * i / n
        nut = geo.cylinder(size, 0.016, 6, bevel=0.0018, bevel_segments=1, name=name)
        seat = geo.revolve([(size * 1.25, 0.0), (size * 1.05, 0.004), (0.0, 0.004)], 12, name=name + "_Seat")
        tip = geo.revolve([(size * 0.55, 0.016), (size * 0.45, 0.021), (0.0, 0.023)], 8, name=name + "_Stud")
        o = geo.join([nut, seat, tip])
        geo.transform(o, loc=(rad * math.cos(a), rad * math.sin(a), z))
        out.append(o)
    return geo.join(out, name)


def _valve(rim_r, w, z, a=math.radians(250), name="Valve"):
    stem = geo.cylinder(0.0045, 0.028, 10, bevel=0.001, name=name)
    cap = geo.cylinder(0.0042, 0.011, 10, bevel=0.001, name=name + "_Cap")
    geo.transform(cap, loc=(0, 0, 0.026))
    geo.transform(stem, rot=(0, -25, 0))
    geo.transform(cap, rot=(0, -25, 0))
    for o in (stem, cap):
        geo.transform(o, rot=(0, 0, math.degrees(a)))
        geo.transform(o, loc=(rim_r * 0.93 * math.cos(a), rim_r * 0.93 * math.sin(a), z))
    return stem, cap


def _dark_slot(L, W, t=0.003, name="Slot"):
    s = geo.box((L, W, t), bevel=min(W * 0.48, 0.012), segments=2, base=False, name=name)
    return s


def _follow(ob, zfun, along=0):
    """Bend a flat part so its z follows zfun(radius) (parts laid on a dish)."""
    co, _ = geo.arrays(ob)
    rr = np.hypot(co[:, 0], co[:, 1])
    co[:, 2] += zfun(rr)
    geo.set_verts(ob, co)
    return ob


def _profile_z(prof):
    P = np.asarray(prof, float)
    o = np.argsort(P[:, 0])
    return lambda rr: np.interp(rr, P[o, 0], P[o, 1])


def brake(rim_r, w, kind="disc", name="Brake"):
    """Disc with hat, dust shield and a caliper at the trailing top (cars), or a finned drum (trucks)."""
    out = {}
    if kind == "drum":
        R = rim_r * 0.80
        dr = geo.revolve([(0.0, w * 0.30), (R * 0.55, w * 0.30), (R * 0.60, w * 0.22), (R, w * 0.18), (R, -w * 0.70),
                          (R * 0.9, -w * 0.74)], 48, name=name + "_Drum")
        fins = []
        for i in range(24):
            f = geo.box((0.012, 0.006, w * 0.8), bevel=0.0, base=False, name=name + "_Fin")
            a = 2 * math.pi * i / 24
            geo.transform(f, loc=(R + 0.004, 0, -w * 0.26))
            geo.transform(f, rot=(0, 0, math.degrees(a)))
            fins.append(f)
        hub = geo.revolve([(rim_r * 0.42, w * 0.32), (rim_r * 0.30, w * 0.62), (rim_r * 0.20, w * 0.80), (0.0, w * 0.86)],
                          32, name=name + "_Hub")
        _add(out, "brake", geo.join([dr] + fins, name + "_Drum"))
        _add(out, "steel", hub)
        return out
    R = rim_r * 0.80
    disc = geo.revolve([(0.085, -w * 0.10), (R, -w * 0.10), (R, w * 0.02), (0.085, w * 0.02)], 64, closed=True,
                       name=name + "_Disc")
    hat = geo.revolve([(0.085, w * 0.02), (0.080, w * 0.32), (0.0, w * 0.34)], 40, name=name + "_Hat")
    shield = geo.revolve([(R * 1.04, -w * 0.30), (0.09, -w * 0.32)], 48, name=name + "_Shield")
    # caliper: a block hugging the disc rim at the trailing top
    cal = geo.revolve([(R * 0.62, -w * 0.24), (R * 1.08, -w * 0.24), (R * 1.08, w * 0.16), (R * 0.62, w * 0.16)], 10,
                      closed=True, name=name + "_Caliper", angle=46.0)
    bm = geo.bm_of(cal)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    ends = [e for e in bm.edges if e.is_boundary]
    if ends:
        bmesh.ops.holes_fill(bm, edges=ends, sides=0)
    geo.bm_to(cal, bm)
    geo.recalc_normals(cal)
    geo.transform(cal, rot=(0, 0, 112))
    _add(out, "brake", disc, hat)
    _add(out, "black", shield)
    _add(out, "steel", cal)
    return out


def wheel_face(style, rim_r, w, name="Rim", trim_ring=False):
    """The wheel's face around +Z (outboard +Z) without the tyre. style: 'cap' (steel wheel under a dished
    plastic hubcap with raised spokes), 'steel' (pressed steel disc with vent slots, lug nuts, centre cap),
    'alloy' (five drafted spokes, recessed hub with the lugs on it), 'truck' (deep steel disc with hand holes,
    ten nuts, hub nose)."""
    out = {}
    _add(out, "alloy" if style == "alloy" else "steel", _barrel(rim_r, w, name + "_Barrel"))
    if style in ("steel", "cap"):
        prof = [(rim_r + 0.006, w * 0.82), (rim_r - 0.006, w * 0.76), (rim_r * 0.88, w * 0.64), (rim_r * 0.72, w * 0.42),
                (rim_r * 0.56, w * 0.40), (rim_r * 0.44, w * 0.56), (rim_r * 0.34, w * 0.60), (0.050, w * 0.60),
                (0.044, w * 0.55)]
        disc = orient(geo.revolve(prof, 48, name=name + "_Disc"), (0, 0, 1))
        _add(out, "steel", disc)
        zf = _profile_z(prof)
        if style == "steel":
            for i in range(6):                              # vent slots on the dish slope (dark: through-holes)
                a = 2 * math.pi * i / 6 + math.pi / 6
                rs = rim_r * 0.64
                s = _dark_slot(0.050, 0.026, name=name + "_Vent")
                geo.transform(s, rot=(0, 0, math.degrees(a) + 90))
                geo.transform(s, loc=(rs * math.cos(a), rs * math.sin(a), 0.0))
                _follow(s, lambda rr: zf(rr) + 0.0012)
                _add(out, "black", s)
            _add(out, "chrome", _nuts(5, 0.0572, w * 0.60, name=name + "_Nuts", start=math.pi / 5))
            cc = geo.revolve([(0.046, w * 0.60), (0.044, w * 0.64), (0.034, w * 0.69), (0.0, w * 0.70)], 32,
                             name=name + "_Cap")
            _add(out, "chrome", cc)
            if trim_ring:
                ring = geo.revolve([(rim_r + 0.019, w * 0.90), (rim_r + 0.004, w * 0.93), (rim_r * 0.92, w * 0.86),
                                    (rim_r * 0.84, w * 0.70)], 64, name=name + "_Trim")
                _add(out, "chrome", solid(ring, 0.0015))
            st, vc = _valve(rim_r * 0.97, w, w * 0.70, name=name + "_Valve")
            _add(out, "tyre", st)
            _add(out, "chrome", vc)
        else:  # hubcap
            hp = [(rim_r + 0.015, w * 0.86), (rim_r + 0.010, w * 0.93), (rim_r * 0.995, w * 0.965), (rim_r * 0.93, w * 0.97),
                  (rim_r * 0.88, w * 0.955), (rim_r * 0.84, w * 0.90), (rim_r * 0.68, w * 0.86), (rim_r * 0.52, w * 0.86),
                  (rim_r * 0.44, w * 0.95), (rim_r * 0.36, w * 1.01), (rim_r * 0.27, w * 1.03), (rim_r * 0.24, w * 1.06),
                  (rim_r * 0.16, w * 1.09), (0.0, w * 1.10)]
            cap = orient(geo.revolve(hp, 48, name=name + "_Hubcap"), (0, 0, 1))
            _add(out, "alloy", cap)
            zc = _profile_z(hp)
            n = 10
            for i in range(n):                              # raised spokes, following the dish
                a = 2 * math.pi * i / n
                r0, r1 = rim_r * 0.40, rim_r * 0.86
                ts = np.linspace(0, 1, 9)
                secs = []
                for t in ts:
                    rr = r0 + (r1 - r0) * t
                    hw_ = 0.010 + 0.010 * t
                    ht = 0.0075 * (1 - 0.3 * t)
                    zz = float(zc(rr)) - 0.001
                    sec = [(-hw_ - 0.002, 0.0), (hw_ + 0.002, 0.0), (hw_, ht), (-hw_, ht)]
                    secs.append([(rr, sy, zz + sz) for sy, sz in sec])
                sp = loft(name + "_Spoke", secs, smooth=30)
                geo.transform(sp, rot=(0, 0, math.degrees(a)))
                _add(out, "alloy", sp)
                b = a + math.pi / n                           # slot window between two spokes
                s = _dark_slot(0.055, 0.020 + 0.004, name=name + "_Slot")
                rs = rim_r * 0.66
                geo.transform(s, rot=(0, 0, math.degrees(b)))
                geo.transform(s, loc=(rs * math.cos(b), rs * math.sin(b), 0))
                _follow(s, lambda rr: zc(rr) + 0.0004)
                _add(out, "black", s)
            emb = geo.revolve([(rim_r * 0.15, w * 1.09), (rim_r * 0.14, w * 1.115), (rim_r * 0.10, w * 1.12),
                               (0.0, w * 1.125)], 40, name=name + "_Badge")
            _add(out, "chrome", emb)
            st, vc = _valve(rim_r * 1.02, w, w * 0.92, a=math.radians(250) + math.pi / n, name=name + "_Valve")
            _add(out, "tyre", st)
            _add(out, "chrome", vc)
    elif style == "alloy":
        lip = geo.revolve([(rim_r + 0.020, w * 0.86), (rim_r + 0.008, w * 0.93), (rim_r - 0.006, w * 0.92),
                           (rim_r - 0.012, w * 0.82), (rim_r - 0.020, w * 0.70)], 64, name=name + "_Lip")
        _add(out, "alloy", solid(lip, 0.004))
        hub_p = [(0.118, w * 0.30), (0.118, w * 0.52), (0.108, w * 0.58), (0.072, w * 0.60), (0.058, w * 0.585),
                 (0.044, w * 0.60), (0.036, w * 0.56), (0.0, w * 0.56)]
        hub = geo.revolve(hub_p, 48, name=name + "_Hub")
        _add(out, "alloy", hub)
        r0, r1 = 0.100, rim_r - 0.014
        for i in range(5):
            a = 2 * math.pi * i / 5
            secs = []
            for t in np.linspace(0, 1, 12):
                rr = r0 + (r1 - r0) * t
                fw = 0.034 - 0.012 * t + 0.022 * max(0.0, t - 0.78) / 0.22        # face half width, flaring at the lip
                bw = fw * 0.55                                                      # draft: narrower at the back
                zf_ = w * (0.58 + 0.24 * t - 0.10 * math.sin(math.pi * t))         # concave face
                dp = 0.050 - 0.018 * t
                secs.append([(rr, -bw, zf_ - dp), (rr, bw, zf_ - dp), (rr, fw, zf_ - 0.006), (rr, fw - 0.004, zf_),
                             (rr, 0.0, zf_ + 0.002), (rr, -fw + 0.004, zf_), (rr, -fw, zf_ - 0.006)])
            sp = loft(name + "_Spoke", secs, smooth=35)
            geo.transform(sp, rot=(0, 0, math.degrees(a)))
            _add(out, "alloy", sp)
        _add(out, "chrome", _nuts(5, 0.0572, w * 0.585, name=name + "_Nuts", start=math.pi / 5))
        cc = geo.revolve([(0.034, w * 0.56), (0.033, w * 0.62), (0.026, w * 0.655), (0.0, w * 0.665)], 32,
                         name=name + "_Cap")
        _add(out, "chrome", cc)
        st, vc = _valve(rim_r * 0.97, w, w * 0.78, a=math.radians(234), name=name + "_Valve")
        _add(out, "tyre", st)
        _add(out, "chrome", vc)
    else:  # truck
        prof = [(rim_r + 0.006, w * 0.82), (rim_r - 0.008, w * 0.74), (rim_r * 0.86, w * 0.40), (rim_r * 0.70, w * 0.20),
                (rim_r * 0.60, w * 0.14), (rim_r * 0.52, w * 0.18), (rim_r * 0.46, w * 0.26), (0.095, w * 0.26),
                (0.090, w * 0.22)]
        disc = orient(geo.revolve(prof, 56, name=name + "_Disc"), (0, 0, 1))
        _add(out, "steel", disc)
        zf = _profile_z(prof)
        for i in range(5):
            a = 2 * math.pi * i / 5 + 0.3
            rs = rim_r * 0.74
            s = _dark_slot(0.095, 0.060, name=name + "_HandHole")
            geo.transform(s, rot=(0, 0, math.degrees(a) + 90))
            geo.transform(s, loc=(rs * math.cos(a), rs * math.sin(a), 0))
            _follow(s, lambda rr: zf(rr) + 0.0015)
            _add(out, "black", s)
        _add(out, "chrome", _nuts(10, 0.1425, w * 0.26, size=0.015, name=name + "_Nuts"))
        nose = geo.revolve([(0.092, w * 0.26), (0.090, w * 0.40), (0.080, w * 0.48), (0.060, w * 0.52),
                            (0.0, w * 0.54)], 40, name=name + "_HubNose")
        _add(out, "steel", nose)
        for i in range(6):
            a = 2 * math.pi * i / 6
            b = geo.cylinder(0.0065, 0.006, 6, bevel=0.001, name=name + "_HubBolt")
            geo.transform(b, loc=(0.072 * math.cos(a), 0.072 * math.sin(a), w * 0.495))
            _add(out, "chrome", b)
        st, vc = _valve(rim_r * 0.95, w, w * 0.60, name=name + "_Valve")
        _add(out, "chrome", st, vc)
    return out


def wheel(style, r, tw, rim_r, name="Wheel", twin=False, brake_kind=None, text=None, pitches=None, trim_ring=False):
    """A whole wheel at the origin, axle along Y, outboard +Y: tyre (lettering), face, brake behind. twin: a
    second, inner wheel (dual rears). Returns {slot key: [objects]}."""
    w = tw / 2
    out = {}
    offs = [0.0] if not twin else [0.0, -(tw + 0.025)]
    big = r > 0.45
    txt = text or (("QUEENSWAY  HAUL", "11R22.5  REGROOVABLE") if big else
                   ("QUEENSWAY  RADIAL", "%d/%d R%d  TUBELESS" % (
                       int(round(tw * 1000 / 5) * 5), int(round((r - rim_r) / tw * 100 / 5) * 5),
                       int(round(rim_r * 2 / 0.0254 - 1.0)))))
    for k, dz in enumerate(offs):
        t = tyre(r, tw, rim_r, pitches=pitches or ((18 if k == 0 else 12) if big else 22), name="%s_Tyre%d" % (name, k),
                 text=txt if k == 0 else None, grooves=3, lug=0.18 if big else 0.22, side_rings=40 if big else 48)
        geo.transform(t, loc=(0, 0, dz))
        part = {"tyre": [t]}
        if k == 0:
            part = merge(part, wheel_face(style, rim_r, w, name="%s_Rim%d" % (name, k), trim_ring=trim_ring))
            bk = brake_kind or ("drum" if big else "disc")
            part = merge(part, brake(rim_r, w, bk, name="%s_Brake" % name))
        else:                                  # the inner dual: barrel and disc only (its face is never seen)
            prof = [(rim_r + 0.006, w * 0.82), (rim_r - 0.008, w * 0.74), (rim_r * 0.80, w * 0.30), (0.10, w * 0.26)]
            inner = {"steel": [_barrel(rim_r, w, "%s_Rim%d_Barrel" % (name, k)),
                               orient(geo.revolve(prof, 40, name="%s_Rim%d_Disc" % (name, k)), (0, 0, 1))]}
            for o in objects(inner):
                geo.transform(o, rot=(180, 0, 0))     # the inner dual faces inboard
            place(inner, loc=(0, 0, dz))
            part = merge(part, inner)
        out = merge(out, part)
    return _to_y(out)


# ------------------------------------------------------------------------------------------------------- lamps
def _bowl_surface(name, w, h, depth, cells, ox=0.0):
    """Reflector: paraboloid bowls filling a w x h rectangle (cells along y), rims at x = ox, faces looking +X."""
    ny, nz = 10 * cells + 1, 11
    cw = w / cells

    def f(Y, Z):
        k = np.clip(np.floor((Y + w / 2) / cw), 0, cells - 1)
        yc = -w / 2 + (k + 0.5) * cw
        rho = np.clip(np.hypot((Y - yc) / (cw / 2), Z / (h / 2)), 0.0, 1.0)
        return ox - depth * (1.0 - rho ** 2), Y, Z
    ob = grid(name, np.linspace(-w / 2, w / 2, ny), np.linspace(-h / 2, h / 2, nz), f, smooth=60)
    return orient(ob, (1, 0, 0))


def _lens(name, w, h, bulge, t=0.004, flute=0.0, prism=0.0, pitch=0.012, nyz=(17, 9), shape=None):
    """Lens slab, front face at x = bulge (centre) curving back to 0 at the edges; flutes (vertical ribs) or
    prisms (small pyramids) moulded in the front face; thickness t backwards."""
    ny, nz = nyz
    if flute or prism:
        ny = max(ny, int(w / pitch) * 2 + 1)
        nz = max(nz, int(h / pitch) * 2 + 1 if prism else nz)

    def f(Y, Z):
        x = bulge * (1 - (2 * Y / w) ** 2) * (1 - (2 * Z / h) ** 2)
        if flute:
            x = x + flute * np.abs(np.sin(np.pi * Y / pitch))
        if prism:
            x = x + prism * (1 - np.abs(np.sin(np.pi * Y / pitch))) * (1 - np.abs(np.sin(np.pi * Z / pitch)))
        return x, Y, Z
    ob = grid(name, np.linspace(-w / 2, w / 2, ny), np.linspace(-h / 2, h / 2, nz), f, smooth=30)
    orient(ob, (1, 0, 0))
    return solid(ob, t)


def _bezel(name, w, h, r, width=0.012, depth=0.008, x=0.0):
    """Frame round a w x h opening (rounded corners r) in the YZ plane, face at x."""
    outline = rounded_rect(w + width, h + width, r + width / 2, n=4)
    path = [(x, y, z) for y, z in outline] + [(x, outline[0][0], outline[0][1])]
    prof = [(-width / 2, -depth), (width / 2, -depth), (width / 2, -depth * 0.2), (width * 0.25, 0.0),
            (-width * 0.25, 0.0), (-width / 2, -depth * 0.2)]
    ob = geo.sweep(prof, path, closed_path=False, cap=True, name=name, up=(1, 0, 0))
    return ob


def headlamp(w, h, depth=0.11, cells=None, style="rect", bezel_key="chrome", amber=0.0, flute=0.0012, corner=0.018,
             name="Head"):
    """Headlamp unit facing +X, lens front at about x = 0, centred on y = z = 0: black housing, chrome reflector
    bowls (one per cell), bulbs with anti-glare caps, a clear lens with thickness (fluted like a sealed beam
    or plain), a bezel; amber > 0 adds an amber indicator section of that fraction of the width at -y."""
    out = {}
    wa = w * amber
    wl = w - wa
    yl = wa / 2                          # centre of the headlamp section
    cells = cells or max(1, int(round(wl / max(h, 0.05) / 1.25)))
    hs = rbox((depth + 0.01, w + 0.006, h + 0.006), r=0.008, name=name + "_Housing")
    geo.transform(hs, loc=(-depth / 2 - 0.012, 0, 0))
    _add(out, "black", hs)
    if style == "round":
        R = min(wl / cells, h) / 2 - 0.004
        for k in range(cells):
            yc = yl - wl / 2 + (k + 0.5) * wl / cells
            bw = geo.revolve([(0.0, -depth * 0.8), (R * 0.5, -depth * 0.6), (R * 0.9, -depth * 0.15), (R, -0.004)], 40,
                             name=name + "_Bowl")
            geo.transform(bw, rot=(0, 90, 0))
            geo.transform(bw, loc=(0, yc, 0))
            _add(out, "reflector", orient(bw, (1, 0, 0)))
            ln = geo.revolve([(0.0, 0.010), (R * 0.6, 0.008), (R, 0.0), (R, -0.004)], 40, name=name + "_Lens")
            geo.transform(ln, rot=(0, 90, 0))
            geo.transform(ln, loc=(0, yc, 0))
            _add(out, "lens_clear", solid(orient(ln, (1, 0, 0)), 0.004))
            ring = geo.torus(R + 0.004, 0.0055, 40, 8, name=name + "_Ring")
            geo.transform(ring, rot=(0, 90, 0))
            geo.transform(ring, loc=(0.002, yc, 0))
            _add(out, bezel_key, ring)
            bl = geo.sphere(0.011, 16, 8, name=name + "_Bulb")
            geo.transform(bl, loc=(-depth * 0.55, yc, 0))
            cap = geo.revolve([(0.0, 0.0), (0.012, 0.002), (0.013, 0.008)], 20, name=name + "_GlareCap")
            geo.transform(cap, rot=(0, -90, 0))
            geo.transform(cap, loc=(-depth * 0.42, yc, 0))
            _add(out, "bulb", bl)
            _add(out, "chrome", cap)
    else:
        rf = _bowl_surface(name + "_Reflector", wl - 0.006, h - 0.006, depth * 0.85, cells, ox=-0.006)
        geo.transform(rf, loc=(0, yl, 0))
        _add(out, "reflector", rf)
        cw = (wl - 0.006) / cells
        for k in range(cells):
            yc = yl - (wl - 0.006) / 2 + (k + 0.5) * cw
            bl = geo.sphere(0.010, 16, 8, name=name + "_Bulb")
            geo.transform(bl, loc=(-depth * 0.62, yc, 0))
            sock = geo.cylinder(0.012, depth * 0.25, 16, bevel=0.002, name=name + "_Socket", axis="X")
            geo.transform(sock, loc=(-depth * 0.86, yc, 0))
            cap = geo.revolve([(0.0, 0.0), (0.011, 0.002), (0.0125, 0.007)], 20, name=name + "_GlareCap")
            geo.transform(cap, rot=(0, -90, 0))
            geo.transform(cap, loc=(-depth * 0.48, yc, 0))
            _add(out, "bulb", bl)
            _add(out, "chrome", sock, cap)
            if k < cells - 1:                     # divider between the bowls
                dv = geo.box((depth * 0.7, 0.004, h - 0.01), bevel=0.001, base=False, name=name + "_Divider")
                geo.transform(dv, loc=(-depth * 0.4, yc + cw / 2, 0))
                _add(out, "reflector", dv)
        ln = _lens(name + "_Lens", wl - 0.002, h - 0.002, 0.006)
        geo.transform(ln, loc=(0.0, yl, 0))
        _add(out, "lens_clear", ln)
    if wa > 0:
        ya = -w / 2 + wa / 2
        rf = _bowl_surface(name + "_AmberRefl", wa - 0.008, h - 0.008, depth * 0.5, 1, ox=-0.006)
        geo.transform(rf, loc=(0, ya, 0))
        bl = geo.sphere(0.009, 12, 6, name=name + "_AmberBulb")
        geo.transform(bl, loc=(-depth * 0.3, ya, 0))
        la = _lens(name + "_AmberLens", wa - 0.004, h - 0.002, 0.004)
        geo.transform(la, loc=(0, ya, 0))
        dv = geo.box((0.02, 0.005, h), bevel=0.001, base=False, name=name + "_Split")
        geo.transform(dv, loc=(-0.006, -w / 2 + wa, 0))
        _add(out, "reflector", rf)
        _add(out, "bulb", bl)
        _add(out, "lens_amber", la)
        _add(out, bezel_key, dv)
    _add(out, bezel_key, _bezel(name + "_Bezel", w, h, corner, width=0.012, depth=0.010, x=0.004))
    return out


def tail_lamp(w, h, sections=(("red", 0.62), ("amber", 0.18), ("clear", 0.20)), vertical=False, depth=0.07,
              bezel_key="black", name="Tail"):
    """Rear lamp cluster facing +X (turn it by 180 degrees for the tail), centred: black housing, a white
    reflector cell per section, faceted lens sections (red / amber / clear) with thickness, black dividers,
    a bezel. vertical: the sections stack from bottom to top (upright SUV and van lamps)."""
    out = {}
    hs = rbox((depth, w + 0.006, h + 0.006), r=0.006, name=name + "_Housing")
    geo.transform(hs, loc=(-depth / 2 - 0.010, 0, 0))
    _add(out, "black", hs)
    L = h if vertical else w
    pos = -L / 2
    tot = sum(f for _c, f in sections)
    for i, (col, f) in enumerate(sections):
        ln = L * f / tot
        c = pos + ln / 2
        sw, sh = (w, ln) if vertical else (ln, h)
        sy, sz = (0.0, c) if vertical else (c, 0.0)
        rf = _bowl_surface(name + "_Refl", sw - 0.008, sh - 0.008, depth * 0.45, max(1, int(round(sw / sh))), ox=-0.008)
        geo.transform(rf, loc=(0, sy, sz))
        bl = geo.sphere(0.008, 12, 6, name=name + "_Bulb")
        geo.transform(bl, loc=(-depth * 0.3, sy, sz))
        key = {"red": "lens_red", "amber": "lens_amber", "clear": "lens_clear"}[col]
        lz = _lens(name + "_Lens", sw - 0.004, sh - 0.004, 0.004)
        geo.transform(lz, loc=(0, sy, sz))
        _add(out, "reflector", rf)
        _add(out, "bulb", bl)
        _add(out, key, lz)
        if i > 0:
            dv = geo.box((0.014, 0.005, h) if not vertical else (0.014, w, 0.005), bevel=0.001, base=False,
                         name=name + "_Divider")
            geo.transform(dv, loc=(-0.003, pos if not vertical else 0, 0 if not vertical else pos))
            _add(out, bezel_key, dv)
        pos += ln
    _add(out, bezel_key, _bezel(name + "_Bezel", w, h, 0.010, width=0.010, depth=0.008, x=0.004))
    return out


def marker(w, h, colour="amber", depth=0.03, name="Marker"):
    """Small side marker / indicator lens in a black rim, facing +X."""
    out = {}
    hs = rbox((depth, w + 0.004, h + 0.004), r=min(h, w) * 0.3, name=name + "_Housing")
    geo.transform(hs, loc=(-depth / 2 - 0.002, 0, 0))
    ln = _lens(name + "_Lens", w, h, 0.003, nyz=(9, 5))
    _add(out, "black", hs)
    _add(out, "lens_" + colour, ln)
    return out


# ------------------------------------------------------------------------------------------- mirrors, handles
def mirror(w=0.20, h=0.12, arm=0.10, depth=0.075, house_key="black", name="Mirror"):
    """Door mirror sticking out along +Y from a sail at the origin: sail plate, arm, rounded housing with its
    glass looking back (-X)."""
    out = {}
    sail = rbox((0.13, 0.020, 0.075), r=0.008, name=name + "_Sail")
    geo.transform(sail, loc=(0.02, 0.008, 0))
    arm_ = rbox((0.05, arm, 0.035), r=0.012, name=name + "_Arm")
    geo.transform(arm_, loc=(0.005, arm / 2 + 0.01, 0.005))
    hb = rbox((depth, w, h), r=min(0.03, h * 0.35), name=name + "_Housing", seg=4)
    co, _ = geo.arrays(hb)
    front = co[:, 0] > 0
    co[front, 1] *= 0.94                       # rounded, tapering nose
    co[front, 2] *= 0.92
    co[:, 0] += np.where(front, 0.012 * (1 - (2 * co[:, 1] / w) ** 2), 0.0)
    geo.set_verts(hb, co)
    geo.transform(hb, loc=(0.02, arm + w / 2 - 0.01, 0.02))
    gl = rbox((0.003, w - 0.020, h - 0.020), r=min(0.02, h * 0.3), name=name + "_Glass", seg=3)
    geo.transform(gl, loc=(0.02 - depth / 2 - 0.0005, arm + w / 2 - 0.01, 0.02))
    rim = _bezel(name + "_Rim", w - 0.018, h - 0.018, min(0.02, h * 0.3), width=0.008, depth=0.008)
    geo.transform(rim, rot=(0, 0, 180))
    geo.transform(rim, loc=(0.02 - depth / 2 + 0.002, arm + w / 2 - 0.01, 0.02))
    _add(out, house_key, hb)
    _add(out, "black", sail, arm_, rim)
    _add(out, "mirror", gl)
    return out


def truck_mirror(h=0.40, w=0.19, reach=0.24, name="TMirror"):
    """West Coast mirror: two tube stalks from the door to a tall head (chrome back, flat glass looking back) and
    a round convex spot mirror under it."""
    out = {}
    yh = reach + 0.03
    for z0, z1 in ((0.0, h / 2 - 0.04), (-0.40, -h / 2 + 0.04)):
        p = geo.pipe([(0.0, 0.0, z0), (0.0, reach * 0.6, z0 + (z1 - z0) * 0.3), (0.0, yh, z1)], 0.011, segments=10,
                     bend_radius=0.05, name=name + "_Stalk")
        foot = geo.cylinder(0.022, 0.02, 16, bevel=0.003, name=name + "_Foot", axis="Y")
        geo.transform(foot, loc=(0, 0.0, z0))
        _add(out, "chrome", p)
        _add(out, "black", foot)
    head = rbox((0.06, w, h), r=0.02, name=name + "_Head", seg=3)
    geo.transform(head, loc=(0.01, yh + w / 2 - 0.02, 0))
    gl = rbox((0.003, w - 0.02, h - 0.02), r=0.012, name=name + "_Glass")
    geo.transform(gl, loc=(0.01 - 0.0305, yh + w / 2 - 0.02, 0))
    spot = geo.cylinder(0.075, 0.03, 32, bevel=0.01, name=name + "_Spot", axis="X")
    geo.transform(spot, loc=(0.01, yh + w / 2 - 0.02, -h / 2 - 0.10))
    sg = geo.revolve([(0.0, 0.006), (0.066, 0.0)], 32, name=name + "_SpotGlass")
    geo.transform(sg, rot=(0, -90, 0))
    geo.transform(sg, loc=(0.01 - 0.0155, yh + w / 2 - 0.02, -h / 2 - 0.10))
    sb = geo.pipe([(0.01, yh + w / 2 - 0.02, -h / 2 + 0.01), (0.01, yh + w / 2 - 0.02, -h / 2 - 0.03)], 0.008,
                  segments=8, name=name + "_SpotArm")
    _add(out, "chrome", head, sb)
    _add(out, "black", spot)
    _add(out, "mirror", gl, orient(sg, (-1, 0, 0)))
    return out


def door_handle(w=0.12, key="black", name="Handle"):
    """Pull handle in a dark pocket, flush on a door at y = 0 looking +Y, along X."""
    out = {}
    pocket = rbox((w + 0.02, 0.006, 0.048), r=0.012, name=name + "_Pocket")
    geo.transform(pocket, loc=(0, -0.002, 0))
    bar = rbox((w, 0.018, 0.024), r=0.008, name=name + "_Bar")
    co, _ = geo.arrays(bar)
    co[:, 1] += 0.004 * (1 - (2 * co[:, 0] / w) ** 2)
    geo.set_verts(bar, co)
    geo.transform(bar, loc=(0, 0.010, 0.004))
    lock = geo.cylinder(0.008, 0.006, 16, bevel=0.0015, name=name + "_Lock", axis="Y")
    geo.transform(lock, loc=(-w / 2 - 0.022, 0.0, 0.004))
    _add(out, "black", pocket)
    _add(out, key, bar)
    _add(out, "chrome", lock)
    return out


def plate_frame(w=0.305, h=0.152, key="chrome", name="PlateFrame"):
    """Frame round a US plate (305 x 152 mm) facing +X, with a dark recess behind and four screw heads."""
    out = {}
    fr = _bezel(name, w + 0.004, h + 0.004, 0.012, width=0.016, depth=0.006, x=0.003)
    back = rbox((0.012, w + 0.03, h + 0.03), r=0.01, name=name + "_Recess")
    geo.transform(back, loc=(-0.010, 0, 0))
    screws = []
    for sy in (-0.1, 0.1):
        for sz in (-h / 2 + 0.018, h / 2 - 0.018):
            s = geo.revolve([(0.0045, 0.0), (0.0040, 0.0015), (0.0, 0.0022)], 12, name=name + "_Screw")
            geo.transform(s, rot=(0, 90, 0))
            geo.transform(s, loc=(0.0035, sy, sz))
            screws.append(s)
    _add(out, key, fr, geo.join(screws, name + "_Screws"))
    _add(out, "black", back)
    return out


# ------------------------------------------------------------------------------------------------- the cabin
def _seat(x, y, width, fl, av, name, bench=False):
    """Front bucket (or a bench): cushion with side bolsters and a front roll, back with bolsters, piping
    seams, headrest on two posts. x: back of the cushion."""
    out = {}
    cl = 0.50
    ch = 0.12 * av / 0.95
    zc = fl + 0.20 * av
    n_y, n_x = 13, 9

    def cushion(U, V):                        # U across (y), V along (x from rear 0 to front 1)
        yy = (U - 0.5) * width
        bol = 0.0 if bench else 0.035 * np.clip((np.abs(U - 0.5) - 0.30) / 0.2, 0, 1) ** 0.7
        roll = 0.012 * np.sin(np.pi * np.clip((V - 0.75) / 0.25, 0, 1))
        dip = 0.0 if not bench else 0.010 * np.cos(2 * np.pi * U * 3) * 0.5
        return x + V * cl, y + yy, zc + bol + roll - 0.006 * np.sin(np.pi * V) + dip
    top = grid(name + "_Cushion", np.linspace(0, 1, n_y), np.linspace(0, 1, n_x), cushion, smooth=50)
    orient(top, (0, 0, 1))
    solid(top, ch)
    geo.bevel_edges(top, width=0.012, segments=1, angle=50, harden=False)
    _add(out, "seat", top)
    bh = 0.58 * av
    tilt = math.radians(16)

    def back(U, V):                           # V from the cushion up
        yy = (U - 0.5) * width
        bol = 0.0 if bench else 0.05 * np.clip((np.abs(U - 0.5) - 0.30) / 0.2, 0, 1) ** 0.7
        lumbar = 0.012 * np.sin(np.pi * np.clip(V / 0.5, 0, 1))
        d = bol + lumbar
        s, c = math.sin(tilt), math.cos(tilt)
        return x + 0.02 - V * bh * s + d * c, y + yy, zc + 0.02 + V * bh * c + d * s
    bk = grid(name + "_Back", np.linspace(0, 1, n_y), np.linspace(0, 1, 11), back, smooth=50)
    orient(bk, (1, 0, 0))
    solid(bk, 0.11)
    geo.bevel_edges(bk, width=0.014, segments=1, angle=50, harden=False)
    _add(out, "seat", bk)
    # piping seams where the bolsters meet the centre panels
    if not bench:
        for u in (0.29, 0.71):
            yy = y + (u - 0.5) * width
            p1 = [cushion(np.array(u), np.array(v)) for v in np.linspace(0.05, 0.95, 6)]
            p1 = [(float(a), float(b), float(c) + 0.003) for a, b, c in p1]
            p2 = [back(np.array(u), np.array(v)) for v in np.linspace(0.06, 0.94, 6)]
            p2 = [(float(a) + 0.003, float(b), float(c)) for a, b, c in p2]
            _add(out, "cabin", geo.pipe(p1, 0.0032, segments=6, name=name + "_Pipe"),
                  geo.pipe(p2, 0.0032, segments=6, name=name + "_Pipe"))
        for v in (0.30, 0.62):                # cross seams of the back
            p = [back(np.array(u), np.array(v)) for u in np.linspace(0.30, 0.70, 5)]
            _add(out, "cabin", geo.pipe([(float(a) + 0.002, float(b), float(c)) for a, b, c in p], 0.0026, segments=6,
                                        name=name + "_Seam"))
    tops = [back(np.array(u), np.array(1.0)) for u in ((0.3, 0.7) if not bench else (0.18, 0.82))]
    for k, tp in enumerate(tops):
        if bench and k > 1:
            break
        hx, hy, hz = (float(v) for v in tp)
        hr = rbox((0.10, 0.25 if not bench else 0.23, 0.17), r=0.04, name=name + "_Headrest", seg=3)
        geo.transform(hr, rot=(0, -16, 0))
        geo.transform(hr, loc=(hx - 0.03, y + (0.0 if not bench else (hy - y)), hz + 0.14))
        _add(out, "seat", hr)
        for dy in (-0.075, 0.075):
            post = geo.cylinder(0.0055, 0.10, 10, name=name + "_Post")
            geo.transform(post, rot=(0, -16, 0))
            geo.transform(post, loc=(hx - 0.045, y + (0.0 if not bench else (hy - y)) + dy, hz - 0.01))
            _add(out, "chrome", post)
        if not bench:
            break
    return out


def _gauge(R, name):
    """A dial seen from the driver (+X up the column): chrome ring, light face with tick marks, needle."""
    out = {}
    cup = geo.revolve([(R + 0.006, 0.0), (R + 0.004, -0.010), (R, -0.012), (0.0, -0.013)], 32, name=name + "_Cup")
    ring = geo.torus(R + 0.003, 0.0025, 32, 6, name=name + "_Ring")
    ticks = []
    for i in range(11):
        a = math.radians(225 - 27 * i)
        t = geo.box((0.012 if i % 2 == 0 else 0.007, 0.0022, 0.0012), bevel=0.0, base=False, name=name + "_Tick")
        geo.transform(t, rot=(0, 0, math.degrees(a)))
        geo.transform(t, loc=((R - 0.010) * math.cos(a), (R - 0.010) * math.sin(a), -0.0122))
        ticks.append(t)
    nd = geo.box((R * 0.8, 0.0025, 0.0015), bevel=0.0, base=False, name=name + "_Needle")
    geo.transform(nd, loc=(R * 0.35, 0, -0.011))
    geo.transform(nd, rot=(0, 0, 200))
    _add(out, "black", orient(cup, (0, 0, 1)))
    _add(out, "chrome", ring)
    _add(out, "gauge", geo.join(ticks, name + "_Ticks"))
    _add(out, "lens_red", nd)
    return out


def _vent(w, h, name):
    out = {}
    fr = _bezel(name, w, h, 0.008, width=0.008, depth=0.006)
    back = geo.box((0.01, w, h), bevel=0.0, base=False, name=name + "_Back")
    geo.transform(back, loc=(-0.012, 0, 0))
    sl = []
    for k in range(4):
        s = geo.box((0.016, w - 0.004, 0.003), bevel=0.0, base=False, name=name + "_Slat")
        geo.transform(s, rot=(0, -20, 0))
        geo.transform(s, loc=(-0.004, 0, -h / 2 + (k + 0.5) * h / 4))
        sl.append(s)
    _add(out, "cabin", fr, geo.join(sl, name + "_Slats"))
    _add(out, "black", back)
    return out


def interior(c, name="Cabin"):
    """The cabin behind the glass (driver on +Y). c: cowl (x of the windscreen base), belt (z of the side glass
    base), floor (z), roof (z of the headliner), hw (inner half width), bpillar (x), seat_x (x of the front seat
    backs), rear (x of the cabin's back), rear_seat (bool), bench_x, shelf (sedan parcel shelf: x0, x1, z),
    partition (taxi: x), meter (taxi), doors (list of (x0, x1) door-card spans), dash_depth.
    Returns {slot key: [objects]}: dash with binnacle, dials, vents, centre stack and glovebox; steering wheel,
    column and stalks; seats with bolsters, piping and headrests; door cards with armrest, pull cup, handle,
    speaker and crank; floor with tunnel; parcel shelf; taxi partition and meter."""
    out = {}
    cw, belt, fl, roof, hw = c["cowl"], c["belt"], c["floor"], c["roof"], c["hw"]
    dd = c.get("dash_depth", 0.55)
    dy = c.get("driver_y", 0.37 * hw / 0.70)
    av = roof - fl
    # ---- dashboard: lofted across y, binnacle hump in front of the driver
    secs = []
    ys = np.linspace(-hw + 0.05, hw - 0.05, 25)
    for y in ys:
        hump = 0.040 * max(0.0, 1 - ((y - dy) / 0.22) ** 2)
        side = 1.0 - 0.5 * max(0.0, (abs(y) - (hw - 0.16)) / 0.11)
        top = belt + 0.005 + hump
        prof = [(cw - 0.10, belt - 0.06), (cw - 0.15, belt - 0.005), (cw - 0.30 * side, top),
                (cw - dd * 0.80 * side, top - 0.005), (cw - dd * side - 0.01, top - 0.035), (cw - dd * side, belt - 0.12),
                (cw - dd * 0.88 * side, belt - 0.28), (cw - dd * 0.70 * side, fl + 0.22), (cw - 0.20, fl + 0.12)]
        secs.append([(px, float(y), pz) for px, pz in prof])
    dash = loft(name + "_Dash", np.array(secs), closed=True, cap=True, smooth=35)
    _add(out, "cabin", dash)
    # instrument cluster on the dash face in front of the driver, under a visor; dials
    xf = cw - dd - 0.008
    bz = belt - 0.035
    pnl = geo.box((0.004, 0.33, 0.11), bevel=0.0, base=False, name=name + "_ClusterBack")
    geo.transform(pnl, loc=(xf - 0.002, dy, bz))
    _add(out, "black", pnl)
    visor = rbox((0.10, 0.40, 0.025), r=0.010, name=name + "_Visor")
    geo.transform(visor, rot=(0, 8, 0))
    geo.transform(visor, loc=(xf - 0.035, dy, bz + 0.072))
    cheeks = []
    for sy in (-0.19, 0.19):
        ck = rbox((0.09, 0.022, 0.10), r=0.008, name=name + "_VisorCheek")
        geo.transform(ck, loc=(xf - 0.03, dy + sy, bz + 0.02))
        cheeks.append(ck)
    _add(out, "cabin", visor, *cheeks)
    for gy, R in ((-0.080, 0.043), (0.080, 0.043), (0.0, 0.026)):
        g = _gauge(R, name + "_Dial")
        place(g, rot=(0, -90, 0))
        place(g, loc=(xf - 0.016, dy + gy, bz + (0.0 if R > 0.03 else -0.022)))
        out = merge(out, g)
    # vents: two at the ends, two at the centre; centre stack with a radio and a heater panel
    for vy in (hw - 0.10, -hw + 0.10, 0.09, -0.09):
        v = _vent(0.085 if abs(vy) < 0.2 else 0.07, 0.055, name + "_Vent")
        place(v, rot=(0, 0, 180))
        side = 1.0 - 0.5 * max(0.0, (abs(vy) - (hw - 0.12)) / 0.12)
        place(v, loc=(cw - dd * side - 0.008, vy, belt - 0.045))
        out = merge(out, v)
    stack = rbox((0.03, 0.20, 0.24), r=0.008, name=name + "_Stack")
    geo.transform(stack, loc=(cw - dd - 0.005, 0, belt - 0.21))
    radio = rbox((0.012, 0.18, 0.05), r=0.003, name=name + "_Radio")
    geo.transform(radio, loc=(cw - dd - 0.022, 0, belt - 0.13))
    knobs = []
    for ky, kz in ((-0.065, -0.13), (0.065, -0.13), (-0.055, -0.25), (0.0, -0.25), (0.055, -0.25)):
        k = geo.cylinder(0.011 if kz < -0.2 else 0.008, 0.014, 16, bevel=0.002, name=name + "_Knob", axis="X")
        geo.transform(k, loc=(cw - dd - 0.04, ky, belt + kz))
        knobs.append(k)
    _add(out, "cabin", stack)
    _add(out, "black", radio)
    _add(out, "chrome", geo.join(knobs, name + "_Knobs"))
    gb = geo.box((0.004, 0.36, 0.003), bevel=0.0, base=False, name=name + "_GloveLine")
    geo.transform(gb, loc=(cw - dd * 0.98 - 0.002, -hw * 0.55, belt - 0.13))
    _add(out, "black", gb)
    # ---- steering wheel, column, stalks
    sx, sz = cw - dd - 0.30, belt - 0.02
    rim_ = geo.torus(0.190, 0.0165, 44, 8, name=name + "_WheelRim")
    pad = rbox((0.13, 0.11, 0.05), r=0.02, name=name + "_WheelPad", seg=3)
    geo.transform(pad, loc=(0, 0, 0.012))
    spokes = []
    for a in (0, 180, 270):
        s = rbox((0.15, 0.045, 0.014), r=0.006, name=name + "_WheelSpoke")
        geo.transform(s, loc=(0.11, 0, 0.0))
        geo.transform(s, rot=(0, 0, a))
        spokes.append(s)
    colm = geo.cylinder(0.026, 0.30, 16, name=name + "_Column")
    geo.transform(colm, loc=(0, 0, -0.31))
    shroud = rbox((0.10, 0.12, 0.15), r=0.03, name=name + "_Shroud")
    geo.transform(shroud, loc=(0, 0, -0.16))
    stalk = []
    for sgn in (1, -1):
        st = geo.cylinder(0.006, 0.16, 10, name=name + "_Stalk", axis="Y")
        geo.transform(st, loc=(0.0, sgn * 0.11, -0.13))
        stalk.append(st)
    sw = {"black": [rim_, colm, shroud] + stalk, "cabin": [pad] + spokes}
    place(sw, rot=(0, -64, 0))
    place(sw, loc=(sx, dy, sz))
    out = merge(out, sw)
    # ---- floor with tunnel, carpet
    rear = c.get("rear", c["bpillar"] - 0.9)

    def floor_f(U, V):
        x = rear + (cw - 0.05 - rear) * U
        y = (V - 0.5) * 2 * hw
        tun = 0.13 * np.clip(1 - (y / 0.16) ** 2, 0, 1) ** 0.6
        heel = 0.10 * np.clip((x - (cw - 0.30)) / 0.25, 0, 1)
        return x, y, fl + tun + heel
    floor = grid(name + "_Floor", np.linspace(0, 1, 18), np.linspace(0, 1, 15), floor_f, smooth=50)
    _add(out, "carpet", orient(floor, (0, 0, 1)))
    # ---- seats
    fx = c.get("seat_x", c["bpillar"] - 0.12) - 0.15
    for y in (dy, -dy):
        out = merge(out, _seat(fx, y, 0.52, fl, av, name + "_Seat"))
    console = rbox((0.38, 0.16, 0.18), r=0.03, name=name + "_Console")
    geo.transform(console, loc=(fx + 0.30, 0, fl + 0.17))
    lever = geo.cylinder(0.008, 0.14, 10, name=name + "_Lever")
    geo.transform(lever, rot=(0, -20, 0))
    geo.transform(lever, loc=(fx + 0.48, 0, fl + 0.24))
    _add(out, "cabin", console)
    _add(out, "black", lever)
    if c.get("rear_seat"):
        bx_ = c.get("bench_x", fx - 0.85)
        out = merge(out, _seat(bx_, 0.0, 2 * hw - 0.12, fl, av, name + "_Bench", bench=True))
    # ---- door cards
    for x0, x1 in c.get("doors", [(c["bpillar"] + 0.03, cw - 0.10)]):
        for sd in (1, -1):
            yv = sd * (hw + 0.005)
            card = rbox((x1 - x0, 0.03, belt - fl - 0.10), r=0.012, name=name + "_DoorCard")
            geo.transform(card, loc=((x0 + x1) / 2, yv, (belt + fl + 0.02) / 2))
            arm = rbox((min(0.40, (x1 - x0) * 0.6), 0.07, 0.05), r=0.02, name=name + "_Armrest")
            geo.transform(arm, loc=((x0 + x1) / 2 - 0.05, yv - sd * 0.04, belt - 0.24))
            cup = rbox((0.09, 0.03, 0.035), r=0.012, name=name + "_PullCup")
            geo.transform(cup, loc=((x0 + x1) / 2 + 0.06, yv - sd * 0.07, belt - 0.215))
            spk = geo.cylinder(0.065, 0.006, 24, bevel=0.002, name=name + "_Speaker", axis="Y")
            geo.transform(spk, loc=(x0 + 0.16, yv - sd * 0.018, fl + 0.16))
            hd = rbox((0.10, 0.012, 0.025), r=0.006, name=name + "_InnerHandle")
            geo.transform(hd, loc=(x1 - 0.14, yv - sd * 0.02, belt - 0.11))
            crank = geo.pipe([((x0 + x1) / 2 + 0.10, yv - sd * 0.018, belt - 0.14),
                              ((x0 + x1) / 2 + 0.10, yv - sd * 0.045, belt - 0.14),
                              ((x0 + x1) / 2 + 0.17, yv - sd * 0.045, belt - 0.16)], 0.004, segments=6,
                             name=name + "_Crank")
            sill = rbox((x1 - x0, 0.02, 0.012), r=0.004, name=name + "_Sill")
            geo.transform(sill, loc=((x0 + x1) / 2, yv - sd * 0.015, belt - 0.03))
            _add(out, "cabin", card, arm, sill)
            _add(out, "black", cup, spk)
            _add(out, "chrome", hd, crank)
    # ---- parcel shelf
    if c.get("shelf"):
        s0, s1, sz_ = c["shelf"]
        sh = rbox((s1 - s0, 2 * hw - 0.04, 0.02), r=0.006, name=name + "_Shelf")
        geo.transform(sh, loc=((s0 + s1) / 2, 0, sz_))
        _add(out, "cabin", sh)
        for sy in (hw * 0.55, -hw * 0.55):
            g = rbox((0.12, 0.18, 0.006), r=0.03, name=name + "_ShelfSpeaker")
            geo.transform(g, loc=((s0 + s1) / 2, sy, sz_ + 0.012))
            _add(out, "black", g)
    # ---- headliner: only when the roof span is given (x0, x1, half width, z), it must stay inside the shell
    if c.get("headliner"):
        x0, x1, hh, hz = c["headliner"]
        hl = rbox((x1 - x0, 2 * hh, 0.015), r=0.006, name=name + "_Headliner")
        geo.transform(hl, loc=((x0 + x1) / 2, 0, hz))
        _add(out, "headliner", hl)
    # ---- taxi: partition with a plexiglass upper half and a fare meter on the dash
    if c.get("partition") is not None:
        px = c["partition"]
        low = rbox((0.03, 2 * hw - 0.04, belt - fl - 0.05), r=0.008, name=name + "_PartitionLow")
        geo.transform(low, loc=(px, 0, (belt + fl - 0.05) / 2 + 0.02))
        up = geo.box((0.008, 2 * hw - 0.08, roof - belt - 0.08), bevel=0.002, base=False, name=name + "_PartitionGlass")
        geo.transform(up, loc=(px, 0, (roof + belt) / 2 - 0.02))
        frame = _bezel(name + "_PartitionFrame", 2 * hw - 0.08, roof - belt - 0.08, 0.01, width=0.025, depth=0.03)
        geo.transform(frame, loc=(px + 0.015, 0, (roof + belt) / 2 - 0.02))
        tray = rbox((0.20, 0.24, 0.05), r=0.01, name=name + "_PartitionTray")
        geo.transform(tray, loc=(px, -0.06, belt - 0.02))
        _add(out, "black", low, tray)
        _add(out, "glass", up)
        _add(out, "chrome", frame)
    if c.get("meter"):
        mt = rbox((0.10, 0.20, 0.07), r=0.01, name=name + "_Meter")
        geo.transform(mt, loc=(cw - dd * 0.75, -0.04, belt + 0.085))
        disp = geo.box((0.004, 0.15, 0.028), bevel=0.0, base=False, name=name + "_MeterDisplay")
        geo.transform(disp, loc=(cw - dd * 0.75 - 0.052, -0.04, belt + 0.09))
        mnt = rbox((0.05, 0.05, 0.04), r=0.01, name=name + "_MeterMount")
        geo.transform(mnt, loc=(cw - dd * 0.75, -0.04, belt + 0.04))
        _add(out, "black", mt, mnt)
        _add(out, "lens_red", disp)
    return out


# --------------------------------------------------------------------------------------- generated shell tools
def flatten_flank(ob, side, x0, x1, z0, z1, avoid=(), slot=0, deg=(5, 3), tol=0.022, tol2=0.045, edge=0.08,
                  min_ny=0.45, force=()):
    """Put the generated flank of a body onto a smooth fitted surface y = f(x, z) (a robust polynomial fit), so
    crumpled seams, dents and ripples go while the shape of the side stays. Only vertices whose faces are all
    on material index `slot` (the paint) move, and only where they lie within tol of the fit (handles, rub
    strips and mirrors stay), fading out to tol2 and over `edge` metres at the region border. avoid: circles
    (x, z, r) left alone (wheel arches). Returns the number of moved vertices."""
    me = ob.data
    co, no = geo.arrays(ob)
    nv = len(co)
    mi = np.empty(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("material_index", mi)
    lt = np.empty(len(me.polygons), dtype=np.int64)
    me.polygons.foreach_get("loop_total", lt)
    lv = np.empty(len(me.loops), dtype=np.int64)
    me.loops.foreach_get("vertex_index", lv)
    other = np.zeros(nv, bool)
    np.logical_or.at(other, lv, np.repeat(mi != slot, lt))
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    forced = np.zeros(nv, bool)            # force: boxes (x, z, half x, half z) flattened whatever their normals
    for fx_, fz_, ex, ez in force:
        forced |= (np.abs(x - fx_) < ex) & (np.abs(z - fz_) < ez) & (y * side > 0.5) & ~other
    reg = (y * side > 0.3) & (x > x0) & (x < x1) & (z > z0) & (z < z1) & ((no[:, 1] * side > min_ny) | forced) & ~other
    for ax, az, ar in avoid:
        reg &= np.hypot(x - ax, z - az) > ar
    if reg.sum() < 50:
        return 0
    xm, xs = (x0 + x1) / 2, (x1 - x0) / 2
    zm, zs = (z0 + z1) / 2, (z1 - z0) / 2

    def basis(xx, zz):
        u, v = (xx - xm) / xs, (zz - zm) / zs
        cols = []
        for i in range(deg[0] + 1):
            for j in range(deg[1] + 1):
                cols.append(np.polynomial.legendre.legval(u, [0] * i + [1]) * np.polynomial.legendre.legval(v, [0] * j + [1]))
        return np.stack(cols, 1)
    A = basis(x[reg], z[reg])
    yy = y[reg]
    wgt = np.ones(len(yy))
    for _ in range(4):
        coef = np.linalg.lstsq(A * wgt[:, None], yy * wgt, rcond=None)[0]
        res = yy - A @ coef
        s = max(1.4826 * np.median(np.abs(res)), 0.002)
        wgt = 1.0 / (1.0 + (res / (2.5 * s)) ** 2)
    fit = basis(x[reg], z[reg]) @ coef
    res = y[reg] - fit
    wv = np.clip((tol2 - np.abs(res)) / (tol2 - tol), 0, 1)
    wv = np.where(forced[reg], 1.0, wv)
    d_edge = np.minimum.reduce([x[reg] - x0, x1 - x[reg], z[reg] - z0, z1 - z[reg]])
    for ax, az, ar in avoid:
        d_edge = np.minimum(d_edge, np.hypot(x[reg] - ax, z[reg] - az) - ar)
    wv *= np.clip(d_edge / edge, 0, 1)
    co[reg, 1] = y[reg] - wv * res
    geo.set_verts(ob, co)
    return int((wv > 0.01).sum())


def cut_groove(ob, side, p0, p1, width=0.005, depth=0.005, slot=None, ymin=0.45, region_pad=0.03):
    """A real shut line cut into a shell: the faces on the flank side (sign of y = side) along the straight line
    p0 -> p1 in the XZ plane are bisected on four planes (the groove's lips and floor edges), the floor vertices
    are pushed in along -y by depth (a U groove 'width' wide), and the groove faces take material index slot
    (a dark inner face). Returns the number of groove faces."""
    p0, p1 = np.array(p0, float), np.array(p1, float)
    t = p1 - p0
    L = float(np.linalg.norm(t))
    t /= L
    nrm = np.array([-t[1], t[0]])                 # in-plane normal of the line (x, z)
    pn = Vector((float(nrm[0]), 0.0, float(nrm[1])))
    bm = geo.bm_of(ob)
    bm.verts.ensure_lookup_table()

    def in_region(v):
        q = np.array([v.co.x, v.co.z]) - p0
        s = float(q @ t)
        return v.co.y * side > ymin and -region_pad < s < L + region_pad and abs(float(q @ nrm)) < width + 0.03
    faces = [f for f in bm.faces if all(in_region(v) for v in f.verts)]
    if not faces:
        bm.free()
        return 0
    geom = list({e for f in faces for e in f.edges}) + faces + list({v for f in faces for v in f.verts})
    for off in (-width / 2, -width / 2 + 0.0012, width / 2 - 0.0012, width / 2):
        co = Vector((float(p0[0] + nrm[0] * off), 0.0, float(p0[1] + nrm[1] * off)))
        r = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=pn, dist=1e-6)
        geom = list(set(geom) | set(r["geom"]) | set(r["geom_cut"]))
        geom = [g for g in geom if g.is_valid]
    moved = 0
    for v in {v for g in geom if isinstance(g, bmesh.types.BMFace) for v in g.verts}:
        q = np.array([v.co.x, v.co.z]) - p0
        s = float(q @ t)
        o = float(q @ nrm)
        if 0.0 <= s <= L and abs(o) < width / 2 - 0.0008 and v.co.y * side > ymin:
            v.co.y -= side * depth
            moved += 1
    nf = 0
    for f in [g for g in geom if isinstance(g, bmesh.types.BMFace)]:
        cc = f.calc_center_median()
        q = np.array([cc.x, cc.z]) - p0
        s = float(q @ t)
        if 0.0 <= s <= L and abs(float(q @ nrm)) < width / 2 and slot is not None:
            f.material_index = slot
            nf += 1
    geo.bm_to(ob, bm)
    return nf


# ------------------------------------------------------------------------------- parts fitted to a body surface
def fit_surface(hits, facing=1, deg=(3, 2)):
    """Smooth surface x = f(y, z) through ray hits [(x, y, z)] (robust least squares on a polynomial of degree
    deg in y and z): the crumple of a generated nose or tail is not followed, its shape is. Returns f(Y, Z)."""
    H = np.asarray(hits, float)
    y0, y1 = H[:, 1].min(), H[:, 1].max()
    z0, z1 = H[:, 2].min(), H[:, 2].max()
    ym, ys = (y0 + y1) / 2, max((y1 - y0) / 2, 1e-3)
    zm, zs = (z0 + z1) / 2, max((z1 - z0) / 2, 1e-3)

    def basis(Y, Z):
        u, v = (np.asarray(Y, float) - ym) / ys, (np.asarray(Z, float) - zm) / zs
        return np.stack([u ** i * v ** j for i in range(deg[0] + 1) for j in range(deg[1] + 1)], -1)
    A = basis(H[:, 1], H[:, 2])
    x = H[:, 0]
    wgt = np.ones(len(x))
    for _ in range(4):
        cf = np.linalg.lstsq(A * wgt[:, None], x * wgt, rcond=None)[0]
        r = x - A @ cf
        s = max(1.4826 * np.median(np.abs(r)), 0.001)
        wgt = 1.0 / (1.0 + (r / (2.5 * s)) ** 2)
    lo, hi = x.min() - 0.01, x.max() + 0.01       # never beyond the hits (no wild extrapolation at the corners)
    return lambda Y, Z: np.clip(basis(np.clip(Y, y0, y1), np.clip(Z, z0, z1)) @ cf, lo, hi)


def cut_rect(ob, y0, y1, z0, z1, xa, xb, facing=None, min_nx=0.25):
    """Clean rectangular hole in a shell: the faces near the rectangle (signed y0 < y1, z0 < z1, x in xa..xb) are
    bisected on its four planes, then the faces inside are deleted. facing (+1 nose / -1 tail): only faces that
    look that way (n.x * facing > min_nx) go, so a quarter panel wrapping round a tail lamp stays (close-up
    pass 4: the cut left black gaps on the rear quarters). Returns the number of deleted faces."""
    bm = geo.bm_of(ob)
    pad = 0.05

    def near(f):
        c = f.calc_center_median()
        return xa - pad < c.x < xb + pad and y0 - pad < c.y < y1 + pad and z0 - pad < c.z < z1 + pad
    for ax, v in ((1, y0), (1, y1), (2, z0), (2, z1)):
        fs = [f for f in bm.faces if near(f)]
        if not fs:
            continue
        es = list({e for f in fs for e in f.edges})
        vs = list({x for f in fs for x in f.verts})
        no = (0, 1, 0) if ax == 1 else (0, 0, 1)
        co = (0, v, 0) if ax == 1 else (0, 0, v)
        bmesh.ops.bisect_plane(bm, geom=fs + es + vs, plane_co=co, plane_no=no, dist=1e-6)
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        if xa < c.x < xb and y0 < c.y < y1 and z0 < c.z < z1:
            if facing is not None and f.normal.x * facing <= min_nx:
                continue
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    geo.bm_to(ob, bm)
    return len(kill)


def _outline(fx, y0, y1, z0, z1, r, off, facing, n=3):
    pts = rounded_rect(y1 - y0, z1 - z0, r, n=n)
    yc, zc = (y0 + y1) / 2, (z0 + z1) / 2
    out = []
    for py, pz in pts:
        y, z = yc + py, zc + pz
        out.append((float(fx(np.array(y), np.array(z))) + facing * off, y, z))
    return out


def surface_lamp(fx, y0, y1, z0, z1, sections=(("clear", 1.0),), facing=1, depth=0.10, cells=1, vertical=False,
                 bezel_key="chrome", bezel_r=0.0055, corner=0.015, name="Lamp"):
    """A lamp unit filling the rectangle y0..y1 x z0..z1 (signed y) of a body whose surface there is x = fx(y, z):
    a black housing bucket from the hole's edge back by depth, reflector bowls (cells per section), bulbs,
    lens sections (clear / red / amber, 4 mm thick) lying on the fitted surface, dividers, and a bezel round
    the edge that covers the cut. facing +1: a nose lamp (lens looks +X); -1: a tail lamp."""
    s = facing
    out = {}
    tot = sum(f for _c, f in sections)
    a = z0 if vertical else y0
    span = (z1 - z0) if vertical else (y1 - y0)
    for i, (col, f) in enumerate(sections):
        b = a + span * f / tot
        ya, yb, za, zb = (y0, y1, a, b) if vertical else (a, b, z0, z1)
        nyl = max(6, int((yb - ya) / 0.02) + 2)
        nzl = max(4, int((zb - za) / 0.02) + 2)
        lens = grid(name + "_Lens", np.linspace(ya + 0.001, yb - 0.001, nyl), np.linspace(za + 0.001, zb - 0.001, nzl),
                    lambda Y, Z: (fx(Y, Z) + s * 0.0015, Y, Z), smooth=40)
        orient(lens, (s, 0, 0))
        _add(out, "lens_" + col, solid(lens, 0.004))
        nc = cells if (col == "clear" and not vertical) else max(1, int(round((yb - ya) / max(zb - za, 0.03))))
        bd = depth * (0.55 if col == "clear" else 0.32)
        cw = (yb - ya) / nc
        if col == "clear" and nc >= 1 and not vertical:
            def refl(Y, Z, ya=ya, cw=cw, za=za, zb=zb, nc=nc, bd=bd):
                k = np.clip(np.floor((Y - ya) / cw), 0, nc - 1)
                yc = ya + (k + 0.5) * cw
                rho = np.clip(np.hypot((Y - yc) / (cw / 2), (Z - (za + zb) / 2) / ((zb - za) / 2)), 0, 1)
                return fx(Y, Z) - s * (0.010 + bd * (1 - rho ** 2)), Y, Z
        else:
            def refl(Y, Z, ya=ya, yb=yb, za=za, zb=zb, bd=bd):
                rho = np.clip(np.hypot((Y - (ya + yb) / 2) / ((yb - ya) / 2), (Z - (za + zb) / 2) / ((zb - za) / 2)), 0, 1)
                return fx(Y, Z) - s * (0.008 + bd * (1 - rho ** 1.5)), Y, Z
        rf = grid(name + "_Refl", np.linspace(ya, yb, max(8, 10 * nc + 1)), np.linspace(za, zb, 11), refl, smooth=60)
        _add(out, "reflector", orient(rf, (s, 0, 0)))
        for k in range(nc if (col == "clear" and not vertical) else 1):
            yc = ya + (k + 0.5) * cw if (col == "clear" and not vertical) else (ya + yb) / 2
            zc = (za + zb) / 2
            xc = float(fx(np.array(yc), np.array(zc)))
            bl = geo.sphere(0.010 if col == "clear" else 0.008, 14, 7, name=name + "_Bulb")
            geo.transform(bl, loc=(xc - s * (0.010 + bd * 0.62), yc, zc))
            _add(out, "bulb", bl)
            if col == "clear":
                cap = geo.revolve([(0.0, 0.0), (0.011, 0.002), (0.0125, 0.007)], 18, name=name + "_GlareCap")
                geo.transform(cap, rot=(0, -90 * s, 0))
                geo.transform(cap, loc=(xc - s * (0.010 + bd * 0.48), yc, zc))
                _add(out, "chrome", cap)
        if i > 0:
            if vertical:
                pts = [(float(fx(np.array(y), np.array(a))) + s * 0.002, float(y), a) for y in np.linspace(y0, y1, 8)]
            else:
                pts = [(float(fx(np.array(a), np.array(z))) + s * 0.002, a, float(z)) for z in np.linspace(z0, z1, 6)]
            _add(out, bezel_key, geo.pipe(pts, 0.003, segments=6, name=name + "_Divider"))
        a = b
    o1 = _outline(fx, y0, y1, z0, z1, corner, 0.0, s)
    o2 = [(x - s * depth, y, z) for x, y, z in o1]
    bucket = loft(name + "_Housing", [o1, o2], closed=True, cap=False, smooth=30)
    _add(out, "black", bucket)
    ob = _outline(fx, y0, y1, z0, z1, corner, 0.0015, s)
    _add(out, bezel_key, geo.pipe(ob + [ob[0]], bezel_r, segments=8, name=name + "_Bezel"))
    return out


def surface_grille(fx, y0, y1, z0, z1, facing=1, style="eggcrate", nv=None, nh=None, bar_key="chrome",
                   back_key="black", surround_key="chrome", recess=0.04, bar=0.008, top_ext=0.0, name="Grille"):
    """A moulded grille filling y0..y1 x z0..z1 of a nose x = fx(y, z) (close-up pass 4: bars with depth, not
    wires): a black backing plate `recess` behind the bars, side walls, bars `bar` square with a 2 mm bevel
    ('eggcrate': vertical and horizontal bars crossing; 'bars': horizontal bars), and a surround frame (22 mm
    face, 16 mm deep, rounded) whose top is raised by top_ext to meet the bonnet's shut line."""
    s = facing
    out = {}
    z1f = z1 + top_ext
    back = grid(name + "_Back", np.linspace(y0, y1, 14), np.linspace(z0, z1f, 7),
                lambda Y, Z: (fx(Y, Z) - s * recess, Y, Z), smooth=40)
    _add(out, back_key, orient(back, (s, 0, 0)))
    o1 = _outline(fx, y0, y1, z0, z1f, 0.014, 0.0, s)
    o2 = [(x - s * recess, y, z) for x, y, z in o1]
    _add(out, back_key, loft(name + "_Wall", [o1, o2], closed=True, cap=False, smooth=30))
    nh = nh or max(2, int((z1 - z0) / 0.035))
    nv = nv if nv is not None else (max(3, int((y1 - y0) / 0.045)) if style == "eggcrate" else 0)
    h = bar / 2
    sq = [(-h, -h), (h, -h), (h, h), (-h, h)]
    bars = []
    nseg = nh + 1
    for k in range(1, nseg if style == "eggcrate" else nseg + 1):
        z = z0 + (z1 - z0) * k / (nseg if style == "eggcrate" else nseg + 1)
        pts = [(float(fx(np.array(y), np.array(z))) - s * (h + 0.003), float(y), z)
               for y in np.linspace(y0 + 0.006, y1 - 0.006, 16)]
        if style == "bars":           # flat bright bars, 12 mm tall
            prof = [(-0.006, -h), (0.006, -h), (0.006, h), (-0.006, h)]
            bars.append(geo.sweep(prof, pts, name=name + "_Bar", up=(s, 0, 0), bevel=0.002, bevel_segments=1))
        else:
            bars.append(geo.sweep(sq, pts, name=name + "_Bar", up=(s, 0, 0), bevel=0.002, bevel_segments=1))
    for k in range(1, nv + 1):
        y = y0 + (y1 - y0) * k / (nv + 1)
        pts = [(float(fx(np.array(y), np.array(z))) - s * (h + 0.003), y, float(z))
               for z in np.linspace(z0 + 0.006, z1 - 0.006, 6)]
        bars.append(geo.sweep(sq, pts, name=name + "_Bar", up=(s, 0, 0), bevel=0.002, bevel_segments=1))
    if bars:
        _add(out, bar_key, geo.join(bars, name + "_Bars"))
    ob = _outline(fx, y0, y1, z0, z1f, 0.014, -0.004, s)
    frame = geo.sweep([(-0.011, -0.012), (0.011, -0.012), (0.011, 0.004), (-0.011, 0.004)], ob + [ob[0]],
                      name=name + "_Surround", up=(s, 0, 0), bevel=0.004, bevel_segments=2)
    _add(out, surround_key, frame)
    return out


def _poly_fit(u, v, w, deg, iters=4):
    um, us = u.mean(), max(np.ptp(u) / 2, 1e-3)
    vm, vs = v.mean(), max(np.ptp(v) / 2, 1e-3)

    def basis(a, b):
        a, b = (a - um) / us, (b - vm) / vs
        return np.stack([a ** i * b ** j for i in range(deg[0] + 1) for j in range(deg[1] + 1) if i + j <= max(deg)], -1)
    A = basis(u, v)
    wt = np.ones(len(w))
    for _ in range(iters):
        cf = np.linalg.lstsq(A * wt[:, None], w * wt, rcond=None)[0]
        r = w - A @ cf
        s = max(1.4826 * np.median(np.abs(r)), 0.001)
        wt = 1.0 / (1.0 + (r / (2.5 * s)) ** 2)
    return lambda a, b: basis(a, b) @ cf


def boundary_loops(ob):
    """Ordered vertex-index loops of the open borders of a mesh."""
    me = ob.data
    bm = geo.bm_of(ob)
    bm.verts.ensure_lookup_table()
    nxt = {}
    for e in bm.edges:
        if e.is_boundary:
            a, b = e.verts[0].index, e.verts[1].index
            nxt.setdefault(a, []).append(b)
            nxt.setdefault(b, []).append(a)
    bm.free()
    seen, loops = set(), []
    for s in list(nxt):
        if s in seen or len(nxt[s]) != 2:
            continue
        loop, prev, cur = [s], None, s
        seen.add(s)
        while True:
            cand = [v for v in nxt[cur] if v != prev and len(nxt.get(v, [])) == 2]
            if not cand:
                break
            n_ = cand[0]
            if n_ == s:
                loops.append(loop)
                break
            if n_ in seen:
                break
            loop.append(n_)
            seen.add(n_)
            prev, cur = cur, n_
    return loops


def clean_glass(ob, iters=10, seal_r=0.0055, name="Glass"):
    """Generated glass made into clean panes: the ragged borders smoothed along themselves, every pane put on a
    smooth fitted surface (side glass y = f(x, z) per side, screens x = f(y, z) at the nose and the tail), and a
    rubber seal swept round every border. Returns the seal object (or None)."""
    co, no = geo.arrays(ob)
    loops = boundary_loops(ob)
    for _ in range(iters):                    # borders: Laplacian along the loop
        for lp in loops:
            if len(lp) < 6:
                continue
            idx = np.array(lp)
            p = co[idx]
            co[idx] = 0.5 * p + 0.25 * (np.roll(p, 1, 0) + np.roll(p, -1, 0))
    side = np.abs(no[:, 1]) > 0.55
    for sel, ax, (a1, a2), deg in (((side & (co[:, 1] > 0)), 1, (0, 2), (2, 2)), ((side & (co[:, 1] < 0)), 1, (0, 2), (2, 2)),
                                   ((~side & (co[:, 0] > 0)), 0, (1, 2), (3, 2)), ((~side & (co[:, 0] < 0)), 0, (1, 2), (3, 2))):
        if sel.sum() < 12:
            continue
        f = _poly_fit(co[sel, a1], co[sel, a2], co[sel, ax], deg)
        d = f(co[sel, a1], co[sel, a2]) - co[sel, ax]
        d = np.where(np.abs(d) < 0.025, d, 0.0)      # only the crumple moves; stray parts are left alone
        co[sel, ax] += d
    geo.set_verts(ob, co)
    seals = []
    for lp in loops:
        if len(lp) < 8:
            continue
        pts = [tuple(co[lp[0]])]
        for i in lp[1:]:                     # one ring every 3 cm at most (budget)
            if np.linalg.norm(co[i] - np.array(pts[-1])) >= 0.03:
                pts.append(tuple(co[i]))
        if len(pts) < 4:
            continue
        pts.append(pts[0])
        seals.append(geo.pipe(pts, seal_r, segments=5, name=name + "_Seal"))
    return geo.join(seals, name + "_Seals") if seals else None
