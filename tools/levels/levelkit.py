"""Core of the shared layout tool (MAPS.md lane D, item D1).

A layout module (tools/levels/layouts/<id>.py) calls the helpers of `Level` to lay down rectangles (colliders), points
(spawns, cover, explosives, objectives), layers, links, drops, the guide graph and tuning. `Level.to_json()` writes the
same schema and units as Content/Data/level.json (web metres, +Y up, x east, z south, plus a `ue` mirror in cm with
Unreal (X, Y, Z) = web (x, z, y) * 100), so FMILevelData reads it with its existing field names.

What this tool never writes: the nav grids. `nav.layers[*].grid` is the engine bake's output (`-run=MILevelBake`,
MAPS.md D2) made with FMIBoxWorld's own code. tools/levels/navgrid.py mirrors the rule only so the checker and the
builder can test the data before that bake exists (cover filtering, spawn facings, reach); its numbers are design
numbers, not the file's nav.
"""

import math

R = lambda v: round(float(v), 4)


def ue_pos(x, y, z):
    return {"X": R(x * 100), "Y": R(z * 100), "Z": R(y * 100)}


def web_pos(x, y, z):
    return {"x": R(x), "y": R(y), "z": R(z)}


def ue_rect(r):
    return {"minX": R(r["minX"] * 100), "maxX": R(r["maxX"] * 100), "minY": R(r["minZ"] * 100), "maxY": R(r["maxZ"] * 100)}


def rect(x0, x1, z0, z1):
    return {"minX": min(x0, x1), "maxX": max(x0, x1), "minZ": min(z0, z1), "maxZ": max(z0, z1)}


def in_rect(r, x, z):
    return r["minX"] <= x <= r["maxX"] and r["minZ"] <= z <= r["maxZ"]


# Physics constants of src/physics.js and config.json (level.json `physics`, config.json player.body / fall).
PHYSICS = {
    "source": "the Block's constants (level.json physics, config.json player.body and player.fall), unchanged",
    "STEP_HEIGHT": 0.42, "AIR_STEP": 0.08, "NAV_CELL": 0.5, "NAV_INFLATE": 0.5, "NAV_BAND_MIN": 0.47,
    "NAV_BAND_MAX": 1.5, "SLICE_THRESHOLD": 0.2, "SLICE_MAX": 10, "SLICE_SHRINK": 0.86,
}
PLAYER = {"radius": 0.32, "height": 1.8, "crouchHeight": 1.15, "eye": 1.68, "step": 0.42, "jumpApex": 1.0,
          "gravity": 21.0, "fallDamageFrom": 13.0, "fallDamagePerSpeed": 7.0, "boundsMargin": 0.4}
SAFE_DROP = PLAYER["fallDamageFrom"] ** 2 / (2 * PLAYER["gravity"])  # 4.024 m: landing at 13 m/s

# Explosive colliders as on the Block (level.json explosives -> colliders): propane 0.32 x 0.6 x 0.32, rack 0.9 x 1.6 x 0.5.
EXPLOSIVE_SIZE = {"propane": (0.32, 0.6, 0.32), "rack": (0.9, 1.6, 0.5)}
EXPLOSIVE_HP = {"propane": 50, "rack": 70}
EXPLOSIVE_PROP = {"propane": "propane_tank", "rack": "welding_rack"}

# Vehicle profiles measured from the Block's colliders (body box + inset glass box; trucks: cargo + cab).
VEHICLES = {
    "sedan": {"body": 1.08, "glass": 1.45, "glassLen": 0.41, "glassInset": 0.075},
    "taxi": {"body": 1.08, "glass": 1.45, "glassLen": 0.41, "glassInset": 0.075},
    "suv": {"body": 1.24, "glass": 1.78, "glassLen": 0.60, "glassInset": 0.13},
    "van": {"body": 2.14},
    "pickup": {"body": 1.27, "glass": 1.78, "glassLen": 0.27, "glassInset": 0.16},
}


def facing_yaw(fx, fz):
    """Web yaw of a facing (0 looks at -Z, positive turns left), as MILevelData::Point computes it."""
    return math.atan2(-fx, -fz)


class Level:
    def __init__(self, level_id, name, bounds, seed, about):
        self.id = level_id
        self.name = name
        self.bounds = bounds
        self.seed = seed
        self.about = about
        self.boxes = []
        self.props = []
        self.zones = []
        self.regions = []
        self.interior_boxes = []
        self.doorways = []
        self.spawns = []
        self.covers = []
        self.cover_sources = []
        self.explosives = []
        self.objectives = []
        self.extraction = None
        self.player_start = None
        self.cinematic = []
        self.steam = []
        self.puddles = []
        self.surfaces = []
        self.floors = []
        self.buildings = []
        self.signage = []
        self.layout = {}
        self.nav = None
        self.guide = None
        self.drops = []
        self.tuning = None
        self.vantage = None
        self.extra = {}
        self.notes = []
        self.deviations = []
        self.clutter_skipped = []

    # ------------------------------------------------------------------ colliders
    def box(self, tag, x0, x1, y0, y1, z0, z1, surface="concrete", owner=None, bullet_only=False, player_only=False,
            no_nav=False, part=None):
        assert x1 > x0 and y1 > y0 and z1 > z0, (tag, x0, x1, y0, y1, z0, z1)
        b = {"tag": tag, "surface": surface, "owner": owner or {"kind": "level"},
             "flags": {"bulletOnly": bool(bullet_only), "playerOnly": bool(player_only), "noNav": bool(no_nav)},
             "min": (x0, y0, z0), "max": (x1, y1, z1)}
        if part:
            b["part"] = part
        self.boxes.append(b)
        return len(self.boxes) - 1

    def guard(self, tag, x0, x1, y0, y1, z0, z1, part=None, surface="metal"):
        """playerOnly edge guard: blocks movement, lets shots, sight and nav through (chinatown.md 4, midtown.md 5.2)."""
        return self.box(tag, x0, x1, y0, y1, z0, z1, surface=surface, player_only=True, part=part)

    def wall_x(self, tag, x0, x1, z0, z1, y0, y1, openings=(), surface="brick", part=None, **kw):
        """A wall running along x (thin in z) from x0 to x1 with openings [(a, b, top)]: solid segments between the
        openings, and a lintel over each opening from `top` to y1."""
        out = []
        cur = x0
        for a, b, top in sorted(openings):
            if a > cur:
                out.append(self.box(tag, cur, a, y0, y1, z0, z1, surface=surface, part=part, **kw))
            if top < y1:
                out.append(self.box(tag, a, b, top, y1, z0, z1, surface=surface, part=(part or tag) + ".lintel", **kw))
            cur = b
        if cur < x1:
            out.append(self.box(tag, cur, x1, y0, y1, z0, z1, surface=surface, part=part, **kw))
        return out

    def wall_z(self, tag, x0, x1, z0, z1, y0, y1, openings=(), surface="brick", part=None, **kw):
        """A wall running along z (thin in x) with openings [(a, b, top)] along z."""
        out = []
        cur = z0
        for a, b, top in sorted(openings):
            if a > cur:
                out.append(self.box(tag, x0, x1, y0, y1, cur, a, surface=surface, part=part, **kw))
            if top < y1:
                out.append(self.box(tag, x0, x1, top, y1, a, b, surface=surface, part=(part or tag) + ".lintel", **kw))
            cur = b
        if cur < z1:
            out.append(self.box(tag, x0, x1, y0, y1, cur, z1, surface=surface, part=part, **kw))
        return out

    def guard_run(self, tag, axis, fixed0, fixed1, a0, a1, y0, y1, gaps=(), part=None):
        """Edge guards along an edge, skipping the gaps [(a, b)] (the authored drops and stair heads)."""
        out = []
        cur = a0
        for a, b in sorted(gaps):
            if a > cur:
                out.append(self._guard_axis(tag, axis, fixed0, fixed1, cur, a, y0, y1, part))
            cur = max(cur, b)
        if cur < a1:
            out.append(self._guard_axis(tag, axis, fixed0, fixed1, cur, a1, y0, y1, part))
        return out

    def _guard_axis(self, tag, axis, f0, f1, a, b, y0, y1, part):
        if axis == "x":
            return self.guard(tag, a, b, y0, y1, f0, f1, part=part)
        return self.guard(tag, f0, f1, y0, y1, a, b, part=part)

    # ------------------------------------------------------------------ props (art-side placements + their colliders)
    def prop(self, name, boxes, pos=None, rotation_y=0.0, surface="metal", tag=None, extra=None, **flags):
        """A placed prop: an entry in `propPlacements` (catalogue name, pos, rotationY; the art lanes turn these into
        props_<id>.json) and its colliders. `boxes` is a list of (x0, x1, y0, y1, z0, z1[, surface])."""
        idx = len(self.props)
        owner = {"kind": "prop", "prop": idx, "name": name}
        cols = []
        for bx in boxes:
            s = bx[6] if len(bx) > 6 else surface
            cols.append(self.box(tag or name, bx[0], bx[1], bx[2], bx[3], bx[4], bx[5], surface=s, owner=owner, **flags))
        if pos is None:
            x0 = min(b[0] for b in boxes); x1 = max(b[1] for b in boxes)
            z0 = min(b[4] for b in boxes); z1 = max(b[5] for b in boxes)
            y0 = min(b[2] for b in boxes)
            pos = ((x0 + x1) / 2, y0, (z0 + z1) / 2)
        p = {"index": idx, "name": name, "pos": pos, "rotationY": rotation_y, "colliders": cols}
        if extra:
            p.update(extra)
        self.props.append(p)
        return idx

    def simple(self, name, cx, cz, sx, sz, h, y0=0.0, surface="metal", rotation_y=0.0, **flags):
        return self.prop(name, [(cx - sx / 2, cx + sx / 2, y0, y0 + h, cz - sz / 2, cz + sz / 2)], pos=(cx, y0, cz),
                         rotation_y=rotation_y, surface=surface, **flags)

    def vehicle(self, kind, x0, x1, z0, z1, y0=0.0, forward=None, **flags):
        """A parked vehicle, axis-aligned (no oriented boxes). The long side picks the axis. Cars get a body box and
        an inset glass box as the Block's exporter sliced them; vans one box; trucks a cargo box and a cab."""
        along_x = (x1 - x0) >= (z1 - z0)
        if forward is None:
            forward = 1 if along_x else -1
        rot = 0.0 if along_x else (1.5708 if forward < 0 else -1.5708)
        if kind in ("box_truck", "ipx_truck", "production_truck", "delivery_truck"):
            cargo_h, cab_h = (3.3, 2.28) if kind != "ipx_truck" else (2.86, 2.58)
            L = (x1 - x0) if along_x else (z1 - z0)
            cab = min(2.85, L * 0.36)
            if along_x:
                if forward > 0:
                    bx = [(x0, x1 - cab, y0, y0 + cargo_h, z0, z1, "car"), (x1 - cab, x1, y0, y0 + cab_h, z0 + 0.1, z1 - 0.1, "car")]
                else:
                    bx = [(x0 + cab, x1, y0, y0 + cargo_h, z0, z1, "car"), (x0, x0 + cab, y0, y0 + cab_h, z0 + 0.1, z1 - 0.1, "car")]
            else:
                if forward > 0:  # nose south (+z)
                    bx = [(x0, x1, y0, y0 + cargo_h, z0, z1 - cab, "car"), (x0 + 0.1, x1 - 0.1, y0, y0 + cab_h, z1 - cab, z1, "car")]
                else:  # nose north (-z)
                    bx = [(x0, x1, y0, y0 + cargo_h, z0 + cab, z1, "car"), (x0 + 0.1, x1 - 0.1, y0, y0 + cab_h, z0, z0 + cab, "car")]
        elif kind in ("bus",):
            bx = [(x0, x1, y0, y0 + 3.1, z0, z1, "car")]
        else:
            p = VEHICLES[kind]
            bx = [(x0, x1, y0, y0 + p["body"], z0, z1, "car")]
            if "glass" in p:
                if along_x:
                    L = x1 - x0; gl = L * p["glassLen"]; c = (x0 + x1) / 2
                    bx.append((c - gl / 2, c + gl / 2, y0 + p["body"], y0 + p["glass"], z0 + p["glassInset"], z1 - p["glassInset"], "glass"))
                else:
                    L = z1 - z0; gl = L * p["glassLen"]; c = (z0 + z1) / 2
                    bx.append((x0 + p["glassInset"], x1 - p["glassInset"], y0 + p["body"], y0 + p["glass"], c - gl / 2, c + gl / 2, "glass"))
        return self.prop(kind, bx, pos=((x0 + x1) / 2, y0, (z0 + z1) / 2), rotation_y=rot, surface="car", **flags)

    # ------------------------------------------------------------------ clutter (the designs' collider breakdown)
    def clutter(self, group, name, x0, x1, z0, z1, h, y0=0.0, surface="metal", what=None, boxes=None, **flags):
        """A dressing prop that the designs count in their collider breakdown (street furniture, alley and yard props,
        vendor goods, map edges, roof dressing): its colliders are authored here, the art lane fits the mesh to them.
        `boxes` (list of (x0, x1, y0, y1, z0, z1[, surface])) replaces the single box when a prop needs more than one.
        The prop is skipped (and listed in `clutterSkipped`) when it would overlap a collider or stand on a point the
        game needs clear: a spawn, a reel, an explosive, the start, the extraction zone, a doorway, a Goon door, a
        player-only gap, a link or an authored drop. Deterministic: the same table gives the same file."""
        bxs = boxes or [(x0, x1, y0, y0 + h, z0, z1, surface)]
        why = self._clutter_conflict(bxs)
        if why:
            self.clutter_skipped.append({"group": group, "name": name, "rect": [x0, x1, z0, z1], "why": why})
            return None
        return self.prop(name, bxs, surface=surface, extra={"group": group, **({"what": what} if what else {})}, **flags)

    def _clutter_conflict(self, bxs):
        def rd(b, x, z):  # 2D distance from a point to a box footprint
            dx = max(b[0] - x, 0.0, x - b[1])
            dz = max(b[4] - z, 0.0, z - b[5])
            return math.hypot(dx, dz)

        for b in bxs:
            for o in self.boxes:
                if o["flags"]["bulletOnly"]:
                    continue
                (ox0, oy0, oz0), (ox1, oy1, oz1) = o["min"], o["max"]
                if b[0] < ox1 - 0.01 and b[1] > ox0 + 0.01 and b[4] < oz1 - 0.01 and b[5] > oz0 + 0.01 \
                        and b[2] < oy1 - 0.01 and b[3] > oy0 + 0.01:
                    return "overlaps %s" % (o.get("part") or o["tag"])

            def near(p, r):
                return rd(b, p[0], p[2]) < r and abs(p[1] - b[2]) < 2.5

            for s in self.spawns:
                if s["type"] == "ground" and near(s["pos"], 1.0):
                    return "spawn " + s["name"]
            for o in self.objectives:
                if near(o["pos"], 2.5):
                    return "reel " + o["id"]
            for e in self.explosives:
                if near(e["pos"], 1.0):
                    return "explosive"
            if self.player_start and near(self.player_start["pos"], 3.0):
                return "player start"
            if self.extraction and near(self.extraction["pos"], self.extraction["radius"] + 1.0):
                return "extraction"
            for d in self.doorways:
                if near(d["outside"], 1.5) or near(d["inside"], 1.5):
                    return "doorway " + d["name"]
            chk = self.extra.get("checks") or {}
            for d in chk.get("goonDoors", []) + chk.get("playerOnlyGaps", []):
                if rd(b, d["x"], d["z"]) < 1.5 and b[2] < 3.0:
                    return "door " + d["what"]
            for lk in (self.nav or {}).get("links", []):
                for p in lk["path"]:
                    if near(p, 1.2):
                        return "link " + lk["id"]
            for d in self.drops:
                if near(d["from"], 1.5) or near(d["to"], 1.5):
                    return "drop " + d["id"]
        return None

    # ------------------------------------------------------------------ zones and places
    def zone(self, zid, name, r):
        self.zones.append({"id": zid, "name": name, "rect": r})

    def region(self, name, zid, r):
        self.regions.append({"name": name, "zone": zid, "rect": r})

    def zone_at(self, x, z):
        for zn in self.zones:
            if in_rect(zn["rect"], x, z):
                return zn
        return None

    def place_at(self, x, z):
        for rg in self.regions:
            if in_rect(rg["rect"], x, z):
                return rg["name"]
        zn = self.zone_at(x, z)
        return zn["name"] if zn else ""

    def interior_at(self, x, y, z):
        for ib in self.interior_boxes:
            mn, mx = ib["min"], ib["max"]
            if mn[0] <= x <= mx[0] and mn[2] <= z <= mx[2] and mn[1] - 0.05 <= y <= mx[1]:
                return True
        return False

    # ------------------------------------------------------------------ interiors
    def interior(self, name, x0, y0, z0, x1, y1, z1, reel=None):
        self.interior_boxes.append({"name": name, "min": (x0, y0, z0), "max": (x1, y1, z1), "reel": reel})

    def doorway(self, name, outside, inside):
        self.doorways.append({"name": name, "outside": outside, "inside": inside})

    # ------------------------------------------------------------------ points
    def ground(self, name, x, y, z, layer="street", overlooks=None, enabled=True, note=None, face=None):
        self.spawns.append({"name": name, "type": "ground", "pos": (x, y, z), "layer": layer, "overlooks": overlooks,
                            "enabled": enabled, "note": note, "face": face})

    def air(self, name, x, y, z, note=None):
        self.spawns.append({"name": name, "type": "air", "pos": (x, y, z), "layer": None, "note": note})

    def cover_source(self, x0, x1, z0, z1, y0, y1, layer, note=None, sides="nesw", every=3.0):
        """A solid a Goon can take cover behind; the builder places points 0.6 m out from its faces."""
        self.cover_sources.append({"r": (x0, x1, z0, z1), "y": (y0, y1), "layer": layer, "note": note, "sides": sides,
                                   "every": every})

    def explosive(self, kind, x, y, z, rotation_y=0.0, note=None):
        i = len(self.explosives)
        sx, sy, sz = EXPLOSIVE_SIZE[kind]
        if abs(math.sin(rotation_y)) > 0.7:
            sx, sz = sz, sx
        col = self.box("explosive", x - sx / 2, x + sx / 2, y, y + sy, z - sz / 2, z + sz / 2, surface="metal",
                       owner={"kind": "explosive", "explosive": i, "type": kind}, part="explosive.%d" % i)
        self.explosives.append({"type": kind, "pos": (x, y, z), "rotationY": rotation_y, "collider": col, "note": note})
        return i

    def objective(self, oid, code, label, place, zone, pos, rotation_y, interior, note=None, layer="street"):
        self.objectives.append({"id": oid, "code": code, "label": label, "place": place, "zone": zone, "pos": pos,
                                "rotationY": rotation_y, "interior": interior, "note": note, "layer": layer})

    # ------------------------------------------------------------------ JSON
    def _box_json(self, i, b):
        (x0, y0, z0), (x1, y1, z1) = b["min"], b["max"]
        f = b["flags"]
        band = (not f["noNav"] and not f["bulletOnly"] and not f["playerOnly"] and y1 >= PHYSICS["NAV_BAND_MIN"]
                and y0 <= PHYSICS["NAV_BAND_MAX"])
        out = {
            "index": i, "tag": b["tag"], "surface": b["surface"], "owner": b["owner"],
            "blocks": {"movement": not f["bulletOnly"], "shots": not f["playerOnly"], "nav": band},
            "flags": f, "orientedBox": None,
            "web": {"min": web_pos(x0, y0, z0), "max": web_pos(x1, y1, z1)},
            "ue": {"min": ue_pos(x0, y0, z0), "max": ue_pos(x1, y1, z1),
                   "center": ue_pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
                   "extent": {"X": R((x1 - x0) * 50), "Y": R((z1 - z0) * 50), "Z": R((y1 - y0) * 50)}},
        }
        if "part" in b:
            out["part"] = b["part"]
        return out

    def _point_common(self, i, x, y, z):
        zn = self.zone_at(x, z)
        return {"index": i, "zone": zn["id"] if zn else "", "place": self.place_at(x, z),
                "interior": self.interior_at(x, y, z)}

    def to_json(self, facings, covers, generator, el_fallback=False):
        b = self.bounds
        boxes = [self._box_json(i, bx) for i, bx in enumerate(self.boxes)]
        by_tag, by_owner, by_surface = {}, {}, {}
        for bx in boxes:
            by_tag[bx["tag"]] = by_tag.get(bx["tag"], 0) + 1
            by_owner[bx["owner"]["kind"]] = by_owner.get(bx["owner"]["kind"], 0) + 1
            by_surface[bx["surface"]] = by_surface.get(bx["surface"], 0) + 1

        spawns = []
        for i, s in enumerate(self.spawns):
            x, y, z = s["pos"]
            p = self._point_common(i, x, y, z)
            fx, fz = facings[i]
            p.update({"type": s["type"], "name": s["name"],
                      "facingSource": ("authored" if s.get("face") else "opening") if s["type"] == "ground" else "centre"})
            if s["type"] == "ground":
                p["layer"] = s["layer"]
                if s.get("overlooks"):
                    p["overlooks"] = s["overlooks"]
                if not s.get("enabled", True):
                    p["enabled"] = False
                    p["enabledWhen"] = "nav step A (MAPS.md lane N): roof-layer spawns are off until per-layer nav exists"
            if s.get("note"):
                p["note"] = s["note"]
            yaw_ue = math.degrees(math.atan2(fz, fx))
            p["web"] = {"pos": web_pos(x, y, z), "facing": {"x": R(fx), "y": 0, "z": R(fz)}}
            p["ue"] = {"pos": ue_pos(x, y, z), "yaw": R(yaw_ue)}
            spawns.append(p)

        cover_pts = []
        for i, c in enumerate(covers):
            x, y, z = c["pos"]
            p = self._point_common(i, x, y, z)
            p.update({"onDeck": False, "layer": c["layer"]})
            p["web"] = {"pos": web_pos(x, y, z)}
            p["ue"] = {"pos": ue_pos(x, y, z)}
            cover_pts.append(p)

        expl = []
        for i, e in enumerate(self.explosives):
            x, y, z = e["pos"]
            p = {"index": i, "type": e["type"], "prop": EXPLOSIVE_PROP[e["type"]], "hp": EXPLOSIVE_HP[e["type"]]}
            p.update({k: v for k, v in self._point_common(i, x, y, z).items() if k != "index"})
            r = e["rotationY"]
            p["collider"] = e["collider"]
            if e.get("note"):
                p["note"] = e["note"]
            p["web"] = {"pos": web_pos(x, y, z), "rotationY": R(r), "forward": {"x": R(math.cos(r)), "y": 0, "z": R(-math.sin(r))}}
            p["ue"] = {"pos": ue_pos(x, y, z), "yaw": R(-math.degrees(r))}
            expl.append(p)

        objs = []
        for i, o in enumerate(self.objectives):
            x, y, z = o["pos"]
            r = o["rotationY"]
            p = {"index": i, "id": o["id"], "code": o["code"], "label": o["label"], "zone": o["zone"], "place": o["place"],
                 "interior": o["interior"], "prop": None, "layer": o["layer"]}
            if o.get("note"):
                p["note"] = o["note"]
            p["web"] = {"pos": web_pos(x, y, z), "rotationY": R(r), "forward": {"x": R(math.cos(r)), "y": 0, "z": R(-math.sin(r))}}
            p["ue"] = {"pos": ue_pos(x, y, z), "yaw": R(-math.degrees(r))}
            objs.append(p)

        ex = self.extraction
        ex_json = {"source": ex["source"], "label": "IPX truck", "code": "IPX", "zone": ex["zone"], "place": ex["place"],
                   "web": {"pos": web_pos(*ex["pos"]), "radius": ex["radius"]},
                   "ue": {"pos": ue_pos(*ex["pos"]), "radius": R(ex["radius"] * 100)}}
        tr = ex["truck"]
        r = tr["rotationY"]
        ex_json["truck"] = {"prop": tr.get("prop"), "colliders": tr.get("colliders", []),
                            "web": {"pos": web_pos(*tr["pos"]), "rotationY": R(r), "forward": {"x": R(math.cos(r)), "y": 0, "z": R(-math.sin(r))}},
                            "ue": {"pos": ue_pos(*tr["pos"]), "yaw": R(-math.degrees(r))}}
        if ex.get("arrival"):
            ex_json["arrival"] = ex["arrival"]
            ex_json["arrivalNote"] = ex.get("arrivalNote")
        if ex.get("layer"):
            ex_json["layer"] = ex["layer"]

        ps = self.player_start
        fx, fz = ps["facing"]
        ps_json = {"source": ps["source"], "zone": self.zone_at(ps["pos"][0], ps["pos"][2])["id"], "layer": ps.get("layer", "street"),
                   "web": {"pos": web_pos(*ps["pos"]), "yaw": R(facing_yaw(fx, fz)), "facing": {"x": R(fx), "y": 0, "z": R(fz)}},
                   "ue": {"pos": ue_pos(*ps["pos"]), "yaw": R(math.degrees(math.atan2(fz, fx)))}}

        def rect_json(r):
            return {"web": {k: R(v) for k, v in r.items()}, "ue": ue_rect(r)}

        zones = [dict({"id": z["id"], "name": z["name"]}, **rect_json(z["rect"])) for z in self.zones]
        regions = [dict({"name": g["name"], "zone": g["zone"]}, **rect_json(g["rect"])) for g in self.regions]

        interior = {"source": "interior boxes (reverb, exposure, the excludePlayerRoom spawn rule) and the doorways "
                              "(none in these levels: the drones that flew through them are removed, 2026-11-28)",
                    "fade": {"web": 1.5, "ue": 150}, "boxes": [], "doorways": []}
        for ib in self.interior_boxes:
            mn, mx = ib["min"], ib["max"]
            e = {"name": ib["name"], "web": {"min": web_pos(*mn), "max": web_pos(*mx)},
                 "ue": {"min": ue_pos(*mn), "max": ue_pos(*mx), "center": ue_pos(*[(a + c) / 2 for a, c in zip(mn, mx)]),
                        "extent": {"X": R((mx[0] - mn[0]) * 50), "Y": R((mx[2] - mn[2]) * 50), "Z": R((mx[1] - mn[1]) * 50)}}}
            if ib.get("reel"):
                e["reel"] = ib["reel"]
            interior["boxes"].append(e)
        for d in self.doorways:
            interior["doorways"].append({"name": d["name"], "web": {"outside": web_pos(*d["outside"]), "inside": web_pos(*d["inside"])},
                                         "ue": {"outside": ue_pos(*d["outside"]), "inside": ue_pos(*d["inside"])}})

        cine = []
        for i, (pos, look) in enumerate(self.cinematic):
            dx, dy, dz = look[0] - pos[0], look[1] - pos[1], look[2] - pos[2]
            pitch = math.degrees(math.atan2(dy, math.hypot(dx, dz)))
            yaw = math.degrees(math.atan2(dz, dx))
            cine.append({"index": i, "web": {"pos": web_pos(*pos), "look": web_pos(*look)},
                         "ue": {"pos": ue_pos(*pos), "look": ue_pos(*look), "rotator": {"Pitch": R(pitch), "Yaw": R(yaw), "Roll": 0}}})

        props = []
        for p in self.props:
            x, y, z = p["pos"]
            e = {k: v for k, v in p.items() if k not in ("pos",)}
            e["web"] = {"pos": web_pos(x, y, z), "rotationY": R(p["rotationY"])}
            e["ue"] = {"pos": ue_pos(x, y, z), "yaw": R(-math.degrees(p["rotationY"]))}
            e.pop("rotationY", None)
            props.append(e)

        counts = {"colliders": len(boxes), "orientedBoxes": 0,
                  "enemySpawns": {"ground": sum(1 for s in self.spawns if s["type"] == "ground"),
                                  "air": sum(1 for s in self.spawns if s["type"] == "air")},
                  "coverPoints": len(cover_pts), "explosives": len(expl), "objectives": len(objs),
                  "interiorBoxes": len(self.interior_boxes), "doorways": len(self.doorways),
                  "titleKeys": len(cine), "propPlacements": len(props), "signage": len(self.signage)}

        doc = {
            "meta": {
                "file": "level_%s.json" % self.id, "about": self.about, "game": "MURDER INC.", "level": self.id,
                "name": self.name, "schema": 1, "generator": generator,
                "spec": "docs/unreal/maps/%s.md (revision 2) and docs/unreal/MAPS.md lane D" % self.id,
                "seed": self.seed,
                "readFrom": "the hand-authored layout table tools/levels/layouts/%s.py, not the web game" % self.id,
                "units": {"web": "metres, seconds, radians; +Y up, north = -Z, east = +X (right-handed)",
                          "ue": "centimetres, degrees; +Z up, X = east, Y = south (left-handed)"},
                "conversion": "ue (X, Y, Z) = web (x, z, y) * 100; ue yaw = atan2(web z, web x) of a direction = -rotationY of a prop, in degrees",
                "numbers": "rounded to 4 decimals",
                "status": "stage-1 data, unbaked: `nav.layers[*].grid` is absent until the engine bake (-run=MILevelBake) writes it; "
                          "the game does not load this file yet (levels.json is unchanged)",
                "counts": counts,
                "notes": self.notes,
                "deviationsFromDesign": self.deviations,
            },
            "bounds": {"source": "the play area and the extent of the street nav grid; the ground is the plane y = 0",
                       "web": {k: R(v) for k, v in b.items()}, "ue": ue_rect(b)},
            "zones": zones,
            "places": {"source": "the zone names the HUD shows (first match wins)", "regions": regions},
            "ground": {"source": "what the bare ground is made of and the walking-surface heights, as rectangles (the Block samples "
                                 "a 0.1 m grid; these rectangles are its source)",
                       "surfaces": [dict({"surface": s["surface"]}, **rect_json(s["rect"])) for s in self.surfaces],
                       "floors": [dict({"height": {"web": R(f["h"]), "ue": R(f["h"] * 100)}, "what": f.get("what", "")}, **rect_json(f["rect"])) for f in self.floors]},
            "playerStart": ps_json,
            "objectives": objs,
            "extraction": ex_json,
            "enemySpawns": {"source": "authored points (docs/unreal/maps/%s.md). `layer` names the nav layer of a ground point; "
                                      "`overlooks` limits a roof point to players in those zones; `facing` is derived (toward the "
                                      "walkable cells it reaches in a straight line within 6 m for ground points, the centre of the "
                                      "level for air points): the game gives a new enemy its own yaw." % self.id, "points": spawns},
            "coverPoints": {"source": "points 0.6 m out from the faces of solids 0.9 m or more tall that block shots, on a walkable "
                                      "cell of their layer, at least 1.2 m apart (the bake re-filters them with FMIBoxWorld)", "points": cover_pts},
            "explosives": {"source": "authored (design section on explosives); each owns one collider (owner kind explosive)", "items": expl},
            "interior": interior,
            "vantage": self.vantage,
            "cinematicPath": {"source": "the title fly-through, a closed loop (timing: config.json flow.titleCamera)", "points": cine},
            "steam": {"source": "vents (design, lighting section)", "vents": [{"web": {"pos": web_pos(*v)}, "ue": {"pos": ue_pos(*v)}} for v in self.steam]},
            "puddles": {"source": "wet decals (night, the street wet after rain)" if self.id == "chinatown" else "standing water",
                        "pools": [{"web": {"x": R(x), "z": R(z), "radius": R(r)}, "ue": {"X": R(x * 100), "Y": R(z * 100), "radius": R(r * 100)}} for x, z, r in self.puddles]},
            "buildings": {"source": "the solid buildings and their roofs (design building tables); colliders list the mass boxes",
                          "storeys": {"web": {"ground": 3.8, "upper": 3.1}, "ue": {"ground": 380, "upper": 310}},
                          "list": self.buildings, "backs": []},
            "physics": PHYSICS,
            "colliders": {"source": "every static collision box (axis-aligned), in the order the layout tool added them. tag: what "
                                    "the layout calls it. owner: the level, a prop placement (index into propPlacements), the "
                                    "explosive (index into explosives.items) or the truck. blocks: movement (bodies), shots (rays: "
                                    "rounds and sight), nav (the street layer's plane rule). `part` names the piece for the art fit.",
                          "byTag": dict(sorted(by_tag.items())), "byOwner": by_owner, "bySurface": dict(sorted(by_surface.items())),
                          "boxes": boxes},
            "orientedBoxes": {"source": "none: everything is parked square to the street", "boxes": []},
            "propPlacements": {"source": "art-side: the props the colliders belong to (catalogue name, position, rotationY); the art "
                                         "lanes write props_%s.json from these and fit the meshes to the colliders" % self.id,
                               "items": props},
            "signage": {"source": "art-side: every sign face, invented names only (IPX is the only real mark); English only (owner, "
                                  "DECISIONS 2026-11-26 ~02:00). Each name is still searched before its face is drawn (MAPS.md C1).",
                        "placements": self.signage},
            "layout": dict({"source": "the layout table's named lines and rectangles (tools/levels/layouts/%s.py)" % self.id}, **self.layout),
        }
        if self.nav:
            doc["nav"] = self.nav
        if self.guide:
            doc["guide"] = self.guide
        if self.drops:
            doc["drops"] = {"source": "the authored drops (every one 4.0 m or less: falls hurt above a 13 m/s landing)", "items": self.drops}
        if self.tuning:
            doc["tuning"] = self.tuning
        for k, v in self.extra.items():
            doc[k] = v
        if el_fallback:
            # MAPS.md E2 fallback only: a degenerate deck 250 m outside the bounds so today's loader (which requires
            # el.deck) can read the file; every deck test in MIEnemies.cpp is a point-in-rectangle check, so it never applies.
            doc["el"] = {"source": "FALLBACK (E2 not landed): a degenerate deck far outside the bounds; delete when `el` is optional",
                         "deck": {"web": {"underside": 6.5, "railTop": 6.83, "minX": b["maxX"] + 250, "maxX": b["maxX"] + 251,
                                          "minZ": 0, "maxZ": 1, "tracksZ": []},
                                  "ue": {"underside": 650, "railTop": 683, "minX": (b["maxX"] + 250) * 100, "maxX": (b["maxX"] + 251) * 100,
                                         "minY": 0, "maxY": 100, "tracksY": []}}}
        return doc
