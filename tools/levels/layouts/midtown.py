"""Level 3, Midtown (the roofs above a bright square, 11:52 PM, night): the layout table.

Every number comes from docs/unreal/maps/midtown.md revision 2 (sections 2 to 9, 16 and 18) unless a line says
`DEVIATION`; those are listed in meta.deviationsFromDesign with the reason. Every name on a sign or a screen is
invented; IPX is the only real mark. Walk levels: street 0 (slabs 0.15), r1 14.0, r2 17.6, r3 21.2.
"""

from levelkit import Level, rect

ID = "midtown"
R1, R2, R3 = 14.0, 17.6, 21.2
SW = 0.15
PH = 1.1    # parapet height
PT = 0.3    # parapet thickness
GH = 3.0    # edge guard height over the roof
RISE = 13.85 / 40  # the scaffold and service stair: 8 flights of 5 steps


def build():
    L = Level(ID, "Midtown", rect(-50, 31, -38, 37), 4646,
              "Level 3, Midtown: the roofs above a bright square and the square itself, Seventh Av and W 46 St, 11:52 PM, "
              "night. Bounds, zones, every collider, the points the game flow and the AI use, the four nav layers with "
              "their links, the guide's route graph and the art-side placements, written by the shared layout tool.")
    L.notes = [
        "el: absent (midtown.md 7.2, 17.2): the loader must treat a missing `el` as no deck (MAPS.md E2); "
        "`build_level.py --el-fallback` writes a degenerate deck 250 m outside the bounds for today's loader.",
        "nav: four layers (street plane, r1 14.0, r2 17.6, r3 21.2), the six links L1 to L6 as polylines and the spawn "
        "reach are written; the grids are the engine bake's (-run=MILevelBake). The scaffold and service-stair polylines "
        "are generated here from the towers' landings and flights; the bake re-derives them.",
        "No doorways: interior.doorways is empty (the drones that used them are removed, 2026-11-28).",
        "The IPX truck's colliders are owner kind `truck`: out of the box world (shots, sight, movement) until all three reels "
        "are in (extraction.arrival afterAll, MAPS.md E10), but not noNav: the bake blocks its stop spot on the nav from the "
        "start, so the finale's pursuers never path into it.",
    ]
    L.deviations = []

    # ------------------------------------------------------------------ zones and places (9.2, first match wins)
    for zid, name, r in (("high", "HALVORSEN ROOF", rect(-50, -30, -38, -12)), ("gantry", "THE GANTRY", rect(-28, -3, -4, 22)),
                         ("tanks", "THE TANKS", rect(-50, -8, -38, 8)), ("back", "BACK ROOFS", rect(-50, -28, 8, 22)),
                         ("square", "THE SQUARE", rect(-8, 31, -38, 22)), ("w46", "W 46 ST", rect(-50, 31, 22, 37))):
        L.zone(zid, name, r)
    L.region("THE BOOTH", "square", rect(10, 22, -34.3, -29.2))
    L.region("THE TANKS", "tanks", rect(-22, -16, -35, -29))
    for z in L.zones:
        L.region(z["name"], z["id"], z["rect"])

    def slab(tag, x0, x1, z0, z1, top=SW, surface="concrete", part=None):
        return L.box(tag, x0, x1, 0, top, z0, z1, surface=surface, part=part)

    # ------------------------------------------------------------------ the street (2.2)
    slab("sidewalk", -8, -4, -38, 22, part="seventh.sidewalk.west")
    slab("plaza", 8, 22, -38, 22, surface="concrete", part="square.plaza")
    slab("sidewalk", 28, 30, -38, 22, part="broadway.sidewalk.east")
    slab("sidewalk", -50, 31, 22, 24.5, part="w46.sidewalk.north")
    slab("sidewalk", -50, 31, 33.5, 36, part="w46.sidewalk.south")
    slab("floor", -13, -8, 4, 10, part="servicestair.floor")
    L.box("facade", 30, 31, 0, 30, -38, 22, surface="brick", bullet_only=False, part="east.facade")
    L.box("facade", -50, 31, 0, 20, 36, 37, surface="brick", part="w46.south.facade")

    # ------------------------------------------------------------------ the buildings in play (2.1)
    blds = [("A", "HALVORSEN BUILDING", -50, -30, -38, -12, R3, "ground 4.7 + 5 x 3.30", "start roof, water tower WT-A"),
            ("B", "", -50, -30, -12, 8, R2, "ground 4.7 + 4 x 3.225", "flank roof: machine room, WT-B, bulkhead B"),
            ("E", "", -50, -30, 8, 22, R1, "ground 4.7 + 3 x 3.10", "flank roof: the pipe bridge to D"),
            ("C", "CORVIN HALL", -28, -8, -38, -4, R2, "ground 4.7 + 4 x 3.225", "the tank house and WT-C (Reel 7), the roof billboard"),
            ("D", "", -28, -8, -4, 22, R1, "ground 4.7 + 3 x 3.10", "THE LOFTLARK (closed), the service stair, doors to the gantry")]
    for bid, name, x0, x1, z0, z1, top, storeys, role in blds:
        if bid == "D":
            cols = [L.box("D", -28, -13, 0, top, -4, 22, surface="brick", part="D.mass"),
                    L.box("D", -13, -8, 0, top, -4, 4, surface="brick", part="D.mass"),
                    L.box("D", -13, -8, 0, top, 10, 22, surface="brick", part="D.mass")]
        else:
            cols = [L.box(bid, x0, x1, 0, top, z0, z1, surface="brick", part=bid + ".mass")]
        L.buildings.append({"id": bid, "name": name, "colliders": cols, "storeys": storeys, "role": role,
                            "web": {"minX": x0, "maxX": x1, "minZ": z0, "maxZ": z1, "roof": top, "parapetTop": round(top + PH, 2)}})
    court = L.box("light-court", -30, -28, 0, 10.4, -38, 22, surface="concrete", part="lightcourt.fill")
    L.buildings.append({"id": "court", "name": "light court (never walkable)", "colliders": [court],
                        "web": {"minX": -30, "maxX": -28, "minZ": -38, "maxZ": 22, "roof": 10.4}})

    # ------------------------------------------------------------------ parapets (1.10 x 0.30) and edge guards (playerOnly, roof + 3.0)
    def par_x(z0, z1, x0, x1, y, gaps=(), part=None):
        cur = x0
        for a, b in sorted(gaps) + [(x1, x1)]:
            if a > cur:
                L.box("parapet", cur, a, y, y + PH, z0, z1, surface="concrete", part=part)
            cur = max(cur, b)

    def par_z(x0, x1, z0, z1, y, gaps=(), part=None):
        cur = z0
        for a, b in sorted(gaps) + [(z1, z1)]:
            if a > cur:
                L.box("parapet", x0, x1, y, y + PH, cur, a, surface="concrete", part=part)
            cur = max(cur, b)

    # A (R3)
    par_x(-38, -37.7, -50, -30, R3, part="A.parapet.north")
    par_z(-50, -49.7, -37.7, -12, R3, part="A.parapet.west")
    par_z(-30.3, -30, -37.7, -12.3, R3, gaps=[(-22, -20)], part="A.parapet.east")
    par_x(-12.3, -12, -49.7, -30, R3, gaps=[(-44, -42)], part="A.parapet.south")
    L.guard_run("roof-guard", "z", -30, -29.9, -38, -12, R3, R3 + GH, gaps=[(-22, -20)], part="A.guard.court")
    L.guard_run("roof-guard", "x", -12, -11.9, -50, -30, R3, R3 + GH, gaps=[(-44.1, -41.9)], part="A.guard.south")
    # B (R2)
    par_z(-50, -49.7, -12, 8, R2, part="B.parapet.west")
    par_z(-30.3, -30, -12, 7.7, R2, gaps=[(-10, -8)], part="B.parapet.east")
    par_x(7.7, 8, -49.7, -30, R2, gaps=[(-48, -46), (-36, -34)], part="B.parapet.south")
    L.guard_run("roof-guard", "z", -30, -29.9, -12, 8, R2, R2 + GH, gaps=[(-10.1, -7.9)], part="B.guard.court")
    L.guard_run("roof-guard", "x", 8, 8.1, -50, -30, R2, R2 + GH, gaps=[(-48, -46), (-36.1, -33.9)], part="B.guard.south")
    # E (R1)
    par_z(-50, -49.7, 8, 22, R1, part="E.parapet.west")
    par_z(-30.3, -30, 8, 21.7, R1, gaps=[(16, 18)], part="E.parapet.east")
    par_x(21.7, 22, -49.7, -30, R1, part="E.parapet.south")
    L.guard_run("roof-guard", "z", -30, -29.9, 8, 22.1, R1, R1 + GH, gaps=[(15.9, 18.1)], part="E.guard.court")
    L.guard("roof-guard", -50, -29.9, R1, R1 + GH, 22, 22.1, part="E.guard.w46")
    # C (R2)
    par_x(-38, -37.7, -28, -8, R2, part="C.parapet.north")
    par_z(-28, -27.7, -37.7, -4, R2, gaps=[(-22, -20), (-10, -8)], part="C.parapet.west")
    par_z(-8.3, -8, -37.7, -4.3, R2, part="C.parapet.east")
    par_x(-4.3, -4, -27.7, -8.3, R2, gaps=[(-24, -22), (-16, -14)], part="C.parapet.south")
    L.guard_run("roof-guard", "z", -28.1, -28, -38, -4, R2, R2 + GH, gaps=[(-22.1, -19.9), (-10.1, -7.9)], part="C.guard.court")
    L.guard("roof-guard", -8, -7.9, R2, R2 + GH, -38, -3.9, part="C.guard.square")
    L.guard_run("roof-guard", "x", -4, -3.9, -28, -8, R2, R2 + GH, gaps=[(-24, -22), (-16.1, -13.9)], part="C.guard.south")
    # D (R1): east parapet broken by the gantry doors (z 0.5..2.5, 11..13); the bulkhead takes z 4..10
    par_z(-28, -27.7, -4, 22, R1, gaps=[(16, 18)], part="D.parapet.west")
    par_z(-8.3, -8, -4, 21.7, R1, gaps=[(0.5, 2.5), (3.7, 10.3), (11, 13)], part="D.parapet.east")
    par_x(21.7, 22, -27.7, -8.3, R1, part="D.parapet.south")
    L.guard_run("roof-guard", "z", -28.1, -28, -4, 22.1, R1, R1 + GH, gaps=[(15.9, 18.1)], part="D.guard.court")
    L.guard("roof-guard", -8, -7.9, R1, R1 + GH, -4, -2, part="D.guard.street")
    L.guard("roof-guard", -8, -7.9, R1, R1 + GH, 15.5, 22.1, part="D.guard.tower")
    L.guard("roof-guard", -28, -7.9, R1, R1 + GH, 22, 22.1, part="D.guard.w46")

    # ------------------------------------------------------------------ links between walk levels (5.3)
    def roof_stair(name, axis, sign, a0, c0, c1, base, top_y, rails):
        """8 collider steps of 0.40 (tread 0.5) going down from top_y to base along `axis` from a0 in direction sign,
        across c0..c1; each step solid down to the roof below; playerOnly rails both sides to 1.2 m over the treads."""
        for k in range(1, 9):
            a = a0 + sign * 0.5 * (k - 1)
            b = a0 + sign * 0.5 * k
            lo, hi = min(a, b), max(a, b)
            t = round(top_y - 0.4 * k, 4)
            if axis == "x":
                L.box("roof-stair", lo, hi, base, t, c0, c1, surface="metal", part="%s.step%d" % (name, k))
            else:
                L.box("roof-stair", c0, c1, base, t, lo, hi, surface="metal", part="%s.step%d" % (name, k))
        lo = min(a0, a0 + sign * 4.0)
        hi = max(a0, a0 + sign * 4.0)
        for r0, r1 in rails:
            if axis == "x":
                L.guard("stair-rail", lo, hi, base, top_y + 1.2, r0, r1, part=name + ".rail")
            else:
                L.guard("stair-rail", r0, r1, base, top_y + 1.2, lo, hi, part=name + ".rail")

    # L1 STEEL STAIR A -> C: head bridge over the light court, then 8 steps going east standing on C
    L.box("bridge", -30, -27.6, 20.9, R3, -22, -20, surface="metal", part="L1.headbridge")
    roof_stair("L1", "x", 1, -27.6, -22, -20, R2, R3, rails=[(-22.1, -22.0), (-20.0, -19.9)])
    L.guard("stair-rail", -30, -27.6, 20.9, R3 + 1.2, -22.1, -22.0, part="L1.headbridge.rail")
    L.guard("stair-rail", -30, -27.6, 20.9, R3 + 1.2, -20.0, -19.9, part="L1.headbridge.rail")
    # L2 TANK STAIR A -> B, L3 BACK STAIR B -> E, L4 BILLBOARD STAIR C -> D (8 steps going south)
    roof_stair("L2", "z", 1, -12, -44, -42, R2, R3, rails=[(-44.1, -44.0), (-42.0, -41.9)])
    roof_stair("L3", "z", 1, 8, -36, -34, R1, R2, rails=[(-36.1, -36.0), (-34.0, -33.9)])
    roof_stair("L4", "z", 1, -4, -16, -14, R1, R2, rails=[(-16.1, -16.0), (-14.0, -13.9)])
    # PLANKS B <-> C (R2) and the PIPE BRIDGE E <-> D (R1), with rails
    L.box("planks", -30.3, -27.7, R2 - 0.1, R2, -10, -8, surface="wood", part="planks.deck")
    L.guard("bridge-rail", -30.3, -27.7, R2, R2 + 1.2, -10.1, -10.0, part="planks.rail")
    L.guard("bridge-rail", -30.3, -27.7, R2, R2 + 1.2, -8.0, -7.9, part="planks.rail")
    L.box("pipe-bridge", -30.3, -27.7, R1 - 0.1, R1, 16, 18, surface="metal", part="pipebridge.deck")
    L.guard("bridge-rail", -30.3, -27.7, R1, R1 + 1.2, 15.9, 16.0, part="pipebridge.rail")
    L.guard("bridge-rail", -30.3, -27.7, R1, R1 + 1.2, 18.0, 18.1, part="pipebridge.rail")

    # ------------------------------------------------------------------ the gantry and the LED wall (2.1, 4 S2)
    L.box("gantry", -8, -4.5, 13.6, R1, -2, 14, surface="metal", no_nav=False, part="gantry.deck")
    L.box("gantry", -4.6, -4.5, R1, 15.1, -2, 14, surface="metal", part="gantry.rail")
    L.guard("gantry-guard", -4.6, -4.5, 15.1, 16.2, -2, 14, part="gantry.letterbox")
    L.guard("gantry-guard", -8, -4.5, R1, 17.0, -2.1, -2.0, part="gantry.guard.north")
    L.box("led-wall", -4.5, -3.9, 16.2, 25.2, -2, 14, surface="metal", part="G1.ledwall")
    L.box("cabinet", -8, -6.6, R1, 16.2, -2, -1.4, surface="metal", part="G1.cabinet")

    # ------------------------------------------------------------------ L5 the scaffold stair tower and L6 the service stair
    def tower(name, xw, xe, spine, zN, zS, run0, run1, top_at_north, part, surface, spine_top):
        """8 flights of 5 steps (risers 13.85/40) between a north landing (z zN..run0) and a south landing (run1..zS),
        flight k from the top going N->S when k is odd; west column xw, east column xe, solid spine between. Treads
        are 0.3 slabs (solid to the ground near the bottom); landings are 0.3 slabs; levels from 14.0 to 0.15.
        Returns the link polyline from the top landing down to the bottom landing."""
        levels = [round(R1 - RISE * 5 * i, 4) for i in range(9)]  # 14.0 ... 0.15
        tread = (run1 - run0) / 5.0
        poly = []
        for k in range(1, 9):
            hi, lo = levels[k - 1], levels[k]
            col = xw if k % 2 == 1 else xe
            cx = (col[0] + col[1]) / 2
            for j in range(1, 6):
                t = round(hi - RISE * j, 4)
                if k % 2 == 1:   # north -> south
                    z0, z1 = run0 + tread * (j - 1), run0 + tread * j
                else:            # south -> north
                    z0, z1 = run1 - tread * j, run1 - tread * (j - 1)
                y0 = SW if t - 0.3 < 0.5 else t - 0.3
                if t > SW + 0.01:
                    L.box(part, col[0], col[1], y0, t, z0, z1, surface=surface, part="%s.f%d.%d" % (name, k, j))
            if k % 2 == 1:
                poly += [[cx, hi, run0], [cx, lo, run1], [cx, lo, (run1 + zS) / 2]]
            else:
                poly += [[cx, hi, run1], [cx, lo, run0], [cx, lo, (zN + run0) / 2]]
            # the landing this flight arrives on (the bottom one is the ground)
            if lo > SW + 0.01:
                if k % 2 == 1:
                    L.box(part, xw[0], xe[1], lo - 0.3, lo, run1, zS, surface=surface, part="%s.landingS.%d" % (name, k))
                else:
                    L.box(part, xw[0], xe[1], lo - 0.3, lo, zN, run0, surface=surface, part="%s.landingN.%d" % (name, k))
        L.box(part, xw[0], xe[1], R1 - 0.3, R1, zN, run0, surface=surface, part=name + ".landingN.top")
        L.box(part, spine[0], spine[1], SW, spine_top, run0, run1, surface=surface, part=name + ".spine")
        return poly, levels

    # L5: the pipe-scaffold stair tower on the sidewalk, x -8..-3, z 14..20 (odd flights in the west column)
    sc_poly, levels = tower("L5", (-8.0, -5.6), (-5.4, -3.0), (-5.6, -5.4), 14.0, 20.0, 15.5, 18.0, True, "scaffold", "metal", R1 + 3.0)
    L.guard("scaffold-guard", -3.0, -2.9, SW, R1 + 3.0, 14.0, 20.1, part="L5.guard.east")
    L.guard("scaffold-guard", -8.0, -3.0, SW, levels[5], 20.0, 20.1, part="L5.guard.south")
    L.guard("scaffold-guard", -8.0, -3.0, levels[5] + 2.0, R1 + 3.0, 20.0, 20.1, part="L5.guard.south")
    L.guard("scaffold-guard", -5.4, -3.0, levels[5], levels[5] + 2.0, 20.0, 20.1, part="L5.guard.south")
    L.guard("scaffold-guard", -8.0, -3.0, 2.2, 13.6, 13.9, 14.0, part="L5.guard.north")
    L.guard("scaffold-guard", -4.5, -3.0, 13.6, R1 + 3.0, 13.9, 14.0, part="L5.guard.north")
    L.guard("scaffold-guard", -5.4, -3.0, R1, R1 + 3.0, 15.5, 15.6, part="L5.guard.top")
    L.deviations.append("the scaffold's south guard leaves the shed-hop opening (D3) over the west column only (x -8..-5.4, "
                        "5.35 to 7.35 m): the design names the opening, not its width.")
    sc_poly = [[-6.2, R1, 13.0], [-6.8, R1, 14.75]] + sc_poly + [[-4.2, SW, 13.0], [-6.0, SW, 13.0]]
    # the bottom flight ends in the east column: walk out north under the gantry
    sc_poly = [[round(p[0], 3), round(p[1], 3), round(p[2], 3)] for p in sc_poly]

    # L6: the enclosed service stair in D's shaft x -13..-8, z 4..10 (odd flights from the top in the west column)
    ss_poly, _ = tower("L6", (-13.0, -10.6), (-10.4, -8.0), (-10.6, -10.4), 4.0, 10.0, 5.5, 8.5, True, "service-stair", "concrete", 16.8)
    L.wall_z("service-stair", -8.0, -7.7, 3.7, 10.3, SW, R1, openings=[(4.2, 6.2, 2.35)], surface="concrete", part="L6.wall.street")
    L.guard("stair-rail", -10.4, -8.0, R1, 16.8, 5.5, 5.6, part="L6.guard.top")
    # the bulkhead over the shaft (to 16.8) with its 2.0 m roof door on the west face (z 4.2..6.2)
    L.wall_z("bulkhead", -13.3, -13.0, 3.7, 10.3, R1, 16.8, openings=[(4.2, 6.2, 16.2)], surface="brick", part="L6.bulkhead.west")
    L.box("bulkhead", -8.0, -7.7, R1, 16.8, 3.7, 10.3, surface="brick", part="L6.bulkhead.east")
    L.box("bulkhead", -13.0, -8.0, R1, 16.8, 3.7, 4.0, surface="brick", part="L6.bulkhead.north")
    L.box("bulkhead", -13.0, -8.0, R1, 16.8, 10.0, 10.3, surface="brick", part="L6.bulkhead.south")
    L.box("bulkhead", -13.3, -7.7, 16.8, 17.0, 3.7, 10.3, surface="brick", part="L6.bulkhead.roof")
    ss_poly = [[-14.2, R1, 4.8], [-12.2, R1, 4.8]] + ss_poly + [[-9.2, SW, 4.8], [-9.0, SW, 4.8], [-7.0, SW, 4.8]]
    ss_poly = [[round(p[0], 3), round(p[1], 3), round(p[2], 3)] for p in ss_poly]

    # the sidewalk shed beside the tower's south face (deck top 3.0; design 3.2): the shed hop D3. A jump off the deck adds
    # the 1.0 m apex to the fall (MIPlayerRules takes the peak fall speed): 3.2 + 1.0 lands over the 13 m/s damage speed,
    # 3.0 + 1.0 = 4.0 stays under the 4.02 m threshold
    SHED = 3.0
    L.box("shed-deck", -8, -4.2, SHED - 0.2, SHED, 20.1, 24.4, surface="wood", no_nav=True, part="shed.deck")
    for z in (20.6, 24.2):
        L.box("shed-post", -4.4, -4.2, SW, SHED - 0.2, z - 0.1, z + 0.1, surface="metal", part="shed.post")
    L.guard("shed-guard", -8.1, -8.0, SHED, SHED + 3.0, 22.0, 24.5, part="shed.guard.west")
    L.guard("shed-guard", -8.0, -4.2, SHED, SHED + 3.0, 24.4, 24.5, part="shed.guard.south")
    L.deviations.append("the sidewalk shed by the tower runs z 20.1..24.4 over the west sidewalk only (design: z 20..30, which "
                        "would stand in the W 46 St roadway); its south end is guarded, its east edge is the D3 drop (3.2 m).")

    # ------------------------------------------------------------------ roof furniture
    # A: bulkhead A (the room he came up through), WT-A, HVAC, skylights, chimneys, the tar kettle
    L.box("bulkhead", -48, -44, R3, 24.0, -37.0, -36.8, surface="brick", part="bulkheadA.wall")
    L.box("bulkhead", -48, -47.8, R3, 24.0, -36.8, -33.2, surface="brick", part="bulkheadA.wall")
    L.box("bulkhead", -48, -44, R3, 24.0, -33.2, -33.0, surface="brick", part="bulkheadA.wall")
    L.wall_z("bulkhead", -44.2, -44.0, -36.8, -33.2, R3, 24.0, openings=[(-36.0, -34.0, R3 + 2.2)], surface="brick", part="bulkheadA.wall.east")
    L.box("bulkhead", -48, -44, 24.0, 24.2, -37.0, -33.0, surface="brick", part="bulkheadA.roof")
    for x, z in ((-39.2, -27.2), (-34.8, -27.2), (-39.2, -22.8), (-34.8, -22.8)):
        L.box("water-tower", x - 0.225, x + 0.225, R3, 25.2, z - 0.225, z + 0.225, surface="metal", part="WTA.leg")
    L.box("water-tower", -40, -34, 25.2, 30.8, -28, -22, surface="wood", part="WTA.tank")
    L.prop("hvac_rtu", [(-36.5, -34.5, R3, R3 + 1.5, -17, -15, "metal")])
    L.prop("hvac_rtu", [(-46, -43.5, R3, R3 + 1.5, -31, -29, "metal")])
    L.prop("skylight", [(-47, -45, R3, R3 + 0.8, -17, -14, "glass")])
    L.prop("skylight", [(-36, -34, R3, R3 + 0.8, -33, -30, "glass")])
    L.prop("chimney_stack", [(-43, -37, R3, R3 + 1.5, -37.7, -37.0, "brick")])
    L.prop("chimney_stack", [(-34.0, -33.0, R3, R3 + 1.5, -37.7, -37.0, "brick")])
    L.prop("tar_kettle", [(-38.2, -37.2, R3, R3 + 1.0, -18.4, -17.4, "metal")])
    # B: the machine room (I3), WT-B on its short stand, bulkhead B (the wave door), HVAC
    L.box("machine-room", -40, -34, R2, 20.4, -8, -7.8, surface="brick", part="machineroom.wall")
    L.box("machine-room", -40, -39.8, R2, 20.4, -7.8, -2.2, surface="brick", part="machineroom.wall")
    L.box("machine-room", -34.2, -34, R2, 20.4, -7.8, -2.2, surface="brick", part="machineroom.wall")
    L.wall_x("machine-room", -40, -34, -2.2, -2.0, R2, 20.4, openings=[(-38, -36, R2 + 2.0)], surface="brick", part="machineroom.wall.south")
    L.box("machine-room", -40, -34, 20.4, 20.6, -8, -2, surface="brick", part="machineroom.roof")
    for x, z in ((-45.5, -5.5), (-42.5, -5.5), (-45.5, -2.5), (-42.5, -2.5)):
        L.box("water-tower", x - 0.225, x + 0.225, R2, 19.6, z - 0.225, z + 0.225, surface="metal", part="WTB.leg")
    L.box("water-tower", -46, -42, 19.6, 23.6, -6, -2, surface="wood", part="WTB.tank")
    L.box("bulkhead", -48, -44, R2, 20.4, 0, 4, surface="brick", part="bulkheadB")
    L.prop("hvac_rtu", [(-41, -39, R2, R2 + 1.4, 3.5, 5.5, "metal")])
    # E
    L.prop("hvac_rtu", [(-41, -39, R1, R1 + 1.4, 11.5, 13.5, "metal")])
    # E: the old cooling tower's steel dunnage platform, 0.6 m over the roof with a 0.3 step on its open sides: D2 lands
    # on it, so the drop from B is 3.0 m (free even when jumped: 3.0 + the 1.0 m apex < 4.02)
    DECK = R1 + 0.6
    L.box("deck", -49.7, -43.5, R1, DECK, 8.3, 14.5, surface="metal", part="E.dunnage.deck")
    L.box("deck", -43.5, -43.0, R1, R1 + 0.3, 8.3, 15.0, surface="metal", part="E.dunnage.step")
    L.box("deck", -49.7, -43.5, R1, R1 + 0.3, 14.5, 15.0, surface="metal", part="E.dunnage.step")
    L.prop("vent_box", [(-38, -37, R1, R1 + 1.2, 17, 18, "metal")])
    # C: the tank house (I2, Reel 7) with WT-C on it, the roof billboard C1, HVAC row
    L.box("tank-house", -22, -16, R2, 20.4, -35, -34.75, surface="brick", part="tankhouse.wall.north")
    L.box("tank-house", -22, -21.75, R2, 20.4, -34.75, -29.25, surface="brick", part="tankhouse.wall.west")
    L.box("tank-house", -16.25, -16, R2, 20.4, -34.75, -29.25, surface="brick", part="tankhouse.wall.east")
    L.wall_x("tank-house", -22, -16, -29.25, -29.0, R2, 20.4, openings=[(-20, -18, R2 + 2.0)], surface="brick", part="tankhouse.wall.south")
    L.box("tank-house", -22, -16, 20.4, 20.7, -35, -29, surface="concrete", part="tankhouse.roof")
    for x, z in ((-21.5, -34.5), (-16.5, -34.5), (-21.5, -29.5), (-16.5, -29.5)):
        L.box("water-tower", x - 0.225, x + 0.225, 20.7, 22.4, z - 0.225, z + 0.225, surface="metal", part="WTC.leg")
    L.box("water-tower", -21.5, -16.5, 22.4, 27.4, -34.5, -29.5, surface="wood", part="WTC.tank")
    for z in (-35.5, -30.5, -25.5, -20.5):
        L.box("billboard", -10.15, -9.85, R2, 19.6, z - 0.15, z + 0.15, surface="metal", part="C1.leg")
    L.box("billboard", -9.3, -8.9, 19.6, 27.6, -36, -20, surface="metal", part="C1.face")
    L.prop("hvac_rtu", [(-16, -14.5, R2, R2 + 1.4, -14.5, -13, "metal")])
    L.prop("hvac_rtu", [(-12.5, -10, R2, R2 + 1.4, -14.5, -13, "metal")])
    L.prop("hvac_rtu", [(-25, -23, R2, R2 + 1.4, -13, -11, "metal")])
    L.prop("vent_box", [(-20, -19, R2, R2 + 1.2, -25, -24, "metal")])
    # D: THE LOFTLARK (closed rooftop lounge): bar counter, lounger stacks, planters
    # D: THE LOFTLARK's raised timber deck, 0.6 m over the roof with a 0.3 step on its open sides: D1 lands on it, so the
    # drop from C is 3.0 m (free even when jumped)
    L.box("deck", -27.7, -18.5, R1, DECK, -3.7, 3.0, surface="wood", part="D.lounge.deck")
    L.box("deck", -18.5, -18.0, R1, R1 + 0.3, -3.7, 3.5, surface="wood", part="D.lounge.step")
    L.box("deck", -27.7, -18.5, R1, R1 + 0.3, 3.0, 3.5, surface="wood", part="D.lounge.step")
    L.prop("lounge_bar", [(-24, -20, R1, R1 + 1.1, 6, 7, "wood")])
    L.prop("lounger_stack", [(-18, -16.5, R1, R1 + 0.9, 13, 15, "wood")])
    L.prop("lounger_stack", [(-22, -20.5, R1, R1 + 0.9, 16, 17.5, "wood")])
    for x0, x1, z0, z1 in ((-26, -25, 8.5, 10.0), (-13.0, -12.0, -2.5, -0.5), (-12, -11, 13, 15), (-25, -24, 11, 13), (-15.5, -14.5, 8, 10)):
        L.prop("planter_box", [(x0, x1, R1, R1 + 0.9, z0, z1, "wood")])

    # ------------------------------------------------------------------ the Stand and the Booth (2.3)
    # DEVIATION: tiers 1 to 5 stand only in two wings (x 10..13 and 19..22); the middle (x 13..19, z -29.2..-22) is a
    # sunken front court at plaza level. In the design the solid lower tiers stand in front of the booth's window and
    # hide it (tier 5's top is 2.15 m, the slot is 1.0 to 2.0 m), so nobody outside could fire in through it.
    L.deviations.append("the Stand's tiers 1 to 5 are two wings (x 10..13, 19..22) around a front court at plaza level (x 13..19, "
                        "z -29.2..-22): as drawn, tier 5 (top 2.15) stands in front of the booth's slot (1.0 to 2.0 m) and "
                        "would hide it; the court lets Goons and the player see and fire through the slot.")
    for k in range(1, 6):
        z0, z1 = -22 - 1.5 * k, -22 - 1.5 * (k - 1)
        t = round(SW + 0.4 * k, 3)
        L.box("stand", 10, 13, SW, t, z0, z1, surface="metal", part="stand.tier%d.west" % k)
        L.box("stand", 19, 22, SW, t, z0, z1, surface="metal", part="stand.tier%d.east" % k)
    for k in range(6, 9):
        z0, z1 = -22 - 1.5 * k, -22 - 1.5 * (k - 1)
        t = round(SW + 0.4 * k, 3)
        L.box("stand", 10, 22, t - 0.3, t, z0, z1, surface="metal", part="stand.tier%d" % k)
    top = round(SW + 0.4 * 8, 3)
    L.guard("stand-guard", 9.9, 22.1, 2.2, top + 3.0, -34.4, -34.3, part="stand.guard.north")
    L.guard("stand-guard", 9.9, 10.0, 2.2, top + 3.0, -34.3, -32.5, part="stand.guard.west")
    L.guard("stand-guard", 22.0, 22.1, 2.2, top + 3.0, -34.3, -32.5, part="stand.guard.east")
    L.deviations.append("the Stand's top tier (3.35) and the booth's back wall carry playerOnly guards on their north and side "
                        "edges: 3.2 m over the plaza, a jump off them lands over the 13 m/s damage speed.")
    for x0, x1, side in ((10, 10.6, "west"), (21.4, 22, "east")):
        L.box("booth", x0, x1, SW, 3.05, -34, -33, surface="metal", part="booth.wall." + side)
        L.box("booth", x0, x1, 2.15, 3.05, -33, -32.5, surface="metal", part="booth.wall.%s.lintel" % side)
        L.box("booth", x0, x1, 2.15, 2.65, -32.5, -31, surface="metal", part="booth.wall.%s.lintel" % side)
        L.box("booth", x0, x1, SW, 2.25, -31, -29.5, surface="metal", part="booth.wall." + side)
    L.box("booth", 10, 22, SW, 3.35, -34.3, -34, surface="metal", part="booth.wall.back")
    L.box("booth", 10.6, 13, SW, 2.25, -29.5, -29.2, surface="metal", part="booth.wall.front")
    L.box("booth", 19, 21.4, SW, 2.25, -29.5, -29.2, surface="metal", part="booth.wall.front")
    L.box("booth", 13, 19, SW, 1.0, -29.5, -29.2, surface="metal", part="booth.slot.sill")
    slot = L.guard("booth-slot", 13, 19, 1.0, 2.0, -29.5, -29.2, part="booth.slot.frame", surface="metal")
    L.box("booth", 13, 19, 2.0, 2.25, -29.5, -29.2, surface="metal", part="booth.slot.head")
    L.prop("booth_desk", [(14.4, 17.6, SW, 0.95, -34.0, -33.4, "metal")], extra={"what": "the premiere desk, monitors without a brand"})
    L.prop("booth_rack", [(19.8, 21.2, SW, 1.9, -34.0, -33.2, "metal")])

    # ------------------------------------------------------------------ the square: plaza dressing, kiosks, carts, barriers, vehicles
    planters = [(12, 13, -14, -10), (17, 18, -14, -10), (12, 13, -2, 2), (17, 18, -2, 2), (12, 13, 10, 14), (17, 18, 10, 14),
                (9.5, 13.5, 18.5, 19.5), (16.5, 20.5, 18.5, 19.5), (20.5, 21.5, -10, -6), (20.5, 21.5, 0, 4),
                (20.5, 21.5, 10, 14), (8.5, 9.5, -4, 0), (8.5, 9.5, 8, 12), (10, 14, -20.6, -19.6)]
    for x0, x1, z0, z1 in planters:
        L.prop("planter_granite", [(x0, x1, SW, 1.05, z0, z1, "concrete")])
    L.prop("kiosk_souvenir", [(15, 18, SW, 2.6, -19.5, -17.5, "metal")])
    L.prop("kiosk_souvenir", [(15, 18, SW, 2.6, 5, 7, "metal")])
    L.prop("food_cart", [(12.4, 14.2, SW, 1.4, 5.5, 6.5, "metal")])
    L.prop("food_cart", [(18.9, 20.7, SW, 1.4, -12.5, -11.5, "metal")])
    L.prop("generator", [(19.4, 20.6, SW, 1.3, -21.4, -19.8, "metal")])
    for cx, cz in ((14.5, -5.0), (15.6, -3.0), (14.5, -1.0)):
        L.simple("cafe_table", cx, cz, 0.8, 0.8, 0.75, y0=SW, surface="metal")
    for cx, cz in ((15.0, -12.0), (15.0, 12.0), (20.0, 16.0), (10.5, 16.0)):
        L.simple("light_pole", cx, cz, 0.3, 0.3, 8.0, y0=SW)
    for cz in (-26.0, -2.0, 14.0):
        L.simple("street_lamp", 28.33, cz, 0.26, 0.26, 7.3, y0=SW)
    for cz in (-30.0, -18.0, -6.0):
        L.simple("street_lamp", -4.33, cz, 0.26, 0.26, 7.3, y0=SW)
    for cx, cz in ((9.0, -24.0), (21.5, 8.0), (-4.6, 20.0), (29.3, -20.0)):
        L.simple("trash_can", cx, cz, 0.58, 0.58, 0.95, y0=SW)
    # Seventh Av, closed for the premiere: barriers (north), the production truck, 5 parked cars, staggered barriers
    L.prop("jersey_barrier", [(-3.8, -0.2, 0, 0.81, -37.9, -37.4, "concrete")])
    L.prop("jersey_barrier", [(4.0, 7.8, 0, 0.81, -37.9, -37.4, "concrete")])
    L.prop("jersey_barrier", [(22.2, 24.0, 0, 0.81, -37.9, -37.4, "concrete")])
    L.prop("jersey_barrier", [(26.0, 27.8, 0, 0.81, -37.9, -37.4, "concrete")])
    L.vehicle("box_truck", 1, 3.5, -37, -29, forward=-1)
    L.props[-1]["name"] = "production_truck"
    L.props[-1]["what"] = "BRIGHTWIRE EVENTS, VLTR sprayed over it; nose north"
    L.vehicle("sedan", -3.8, -1.9, -27, -22.4, forward=-1)
    L.vehicle("taxi", -3.8, -1.9, -12, -7.4, forward=-1)
    L.vehicle("suv", -3.8, -1.9, 2, 6.9, forward=-1)
    L.vehicle("sedan", 6.1, 7.9, -24, -19.4, forward=-1)
    L.vehicle("taxi", 6.1, 7.9, 9, 13.6, forward=-1)
    for x0, z0 in ((-0.5, -17.3), (3.0, -5.3), (-0.5, 6.7)):
        L.prop("jersey_barrier", [(x0, x0 + 3.0, 0, 0.81, z0, z0 + 0.6, "concrete")])
    # Broadway (southbound): the stalled city bus, 3 parked cars, water barriers at the south end
    L.vehicle("bus", 22.5, 25.3, -6, 6, forward=1)
    L.props[-1]["what"] = "CITY CROSSTOWN, plain blue and white, no real livery; stalled"
    L.vehicle("sedan", 22.3, 24.2, -30, -25.4, forward=1)
    L.vehicle("van", 22.3, 24.4, 12, 17.4, forward=1)
    L.vehicle("taxi", 26.0, 27.9, -36, -31.4, forward=1)
    L.prop("water_barrier", [(22.2, 26.0, 0, 0.9, 16.4 + 1.2, 17.0 + 1.2, "rubber")])
    L.deviations.append("Broadway's water barriers at z 17.6..18.2, south of the parked van (z 12..17.4).")
    # W 46 St: two parked cars on the south lane
    L.vehicle("sedan", -30, -25.4, 31.6, 33.4)
    L.vehicle("van", -12, -6.8, 31.4, 33.4)

    # ------------------------------------------------------------------ explosives (17; section 8)
    E = L.explosive
    E("propane", -36.5, R3, -17.5, note="roofer's torch tank by a tar kettle")
    E("rack", -33.0, R3, -31.0, rotation_y=1.5708, note="welding rack by the chimney repair")
    E("propane", -21.5, R2, -18.0, note="2 m from the foot of the steel stair")
    E("rack", -12.5, R2, -24.0, rotation_y=1.5708, note="under the roof billboard frame (sign crew's kit)")
    E("propane", -33.0, R2, -11.0, note="B, by the planks")
    E("propane", -46.5, R2, 6.0, note="B, by bulkhead B (punishes the wave door)")
    E("propane", -22.0, R1, 10.0, note="THE LOFTLARK's patio heater tank")
    E("rack", -16.0, R1, 19.0, note="D, roof repair")
    E("propane", -40.0, R1, 18.5, note="E")
    E("rack", -3.7, R1, 15.0, rotation_y=1.5708, note="at the scaffold head, in the top landing's east corner (5.5 m from the gantry "
      "door north; design (-6.6, 12.6) was 1.7 m from it)")
    E("propane", 12.0, SW, 6.0, note="food cart (plaza)")
    E("propane", 18.5, SW, -12.0, note="food cart (plaza)")
    E("propane", 21.0, SW, -20.5, note="the premiere's generator by the Stand (8.9 m from x11: no chain)")
    E("rack", 2.2, 0.0, -27.6, note="behind the production truck's tail lift")
    E("propane", 20.0, SW, 34.5, note="W 46 St south sidewalk, restaurant heater")
    E("rack", -2.0, 0.0, 16.5, note="at the scaffold's foot, in the parking lane")
    E("propane", 25.0, 0.0, -8.0, note="off the stalled bus's front")

    # ------------------------------------------------------------------ interiors (9.1; no doorways: the drones are removed)
    L.interior("bulkhead A", -48, R3, -37, -44, 24.0, -33)
    L.interior("tank house", -22, R2, -35, -16, 20.4, -29, reel="reel7")
    L.interior("machine room", -40, R2, -8, -34, 20.6, -2)
    L.interior("service stair", -13, 0, 4, -8, 16.8, 10)
    L.interior("booth", 10.6, SW, -34, 21.4, 2.25, -29.5, reel="reel9")

    # ------------------------------------------------------------------ the player, the reels, the truck
    L.player_start = {"source": "midtown.md 6.1: on A, just up from bulkhead A, looking east along the roof at the skyline and WT-A (turned from the stair so the bulkhead door is not in the first view)",
                      "pos": (-43.2, R3, -35.0), "facing": (0.9848, 0.1736), "layer": "r3"}
    L.objective("reel7", "7", "Reel 7 — The Tank", "THE TANKS", "tanks", (-19.0, R2, -33.0), -1.5708, True, layer="r2",
                note="inside the tank house under WT-C on C (2.0 m door on the south side)")
    L.objective("reel8", "8", "Reel 8 — The Gantry", "THE GANTRY", "gantry", (-6.0, R1, -0.6), -1.5708, False, layer="r1",
                note="north end of the gantry deck at the LED wall's control cabinet; securing it kills G1")
    L.objective("reel9", "9", "Reel 9 — The Booth", "THE BOOTH", "square", (16.0, SW, -32.6), -1.5708, True, layer="street",
                note="the premiere desk in the booth under the Stand (2.0 m doors on both sides, the front a shoot-through slot)")
    tx, tz = 20.0, 29.0
    # noNav false: the bake stamps the stop spot (plain roadway) from the start, so pursuers never path into the truck once it
    # has arrived; the colliders join the box world for shots and movement only on arrival (MAPS.md E10)
    tcols = [L.box("ipx_truck", tx - 3.4, tx + 0.55, 0, 2.86, tz - 1.17, tz + 1.17, surface="car", no_nav=False,
                   owner={"kind": "truck"}, part="truck.cargo"),
             L.box("ipx_truck", tx + 0.55, tx + 3.4, 0, 2.58, tz - 1.17, tz + 1.17, surface="car", no_nav=False,
                   owner={"kind": "truck"}, part="truck.cab")]
    L.extraction = {"source": "midtown.md 6.3: the zone behind the truck's rear doors (truck - 5.4 m x forward); the truck is "
                              "not on the map until the last reel is in, then rolls in along W 46 St over 5 s",
                    "zone": "w46", "place": "W 46 ST", "pos": (14.6, 0.0, 29.0), "radius": 2.5, "layer": "street",
                    "arrival": "afterAll",
                    "arrivalNote": "hidden, colliders out of the box world and the zone inactive until every reel is secured; "
                                   "then the 5 s roll-in from beyond the west bound, the colliders join, the zone goes live, "
                                   "no refusal prompt before (MAPS.md E10)",
                    "truck": {"pos": (tx, 0.0, tz), "rotationY": 0.0, "prop": None, "colliders": tcols}}

    # ------------------------------------------------------------------ enemy spawns (30 ground with layers, no air points: the drones are removed)
    ground = [("g0", "r3", -34.0, -14.0), ("g1", "r3", -47.0, -21.0), ("g2", "r3", -32.5, -36.5), ("g3", "r3", -40.0, -13.5),
              ("g4", "r2", -43.0, 2.0), ("g5", "r2", -37.0, -9.0), ("g6", "r2", -33.0, 6.5), ("g7", "r2", -48.0, -2.0),
              ("g8", "r2", -25.5, -36.5), ("g9", "r2", -13.5, -12.0), ("g10", "r2", -26.0, -6.0), ("g11", "r2", -14.0, -37.0),
              ("g12", "r1", -25.5, 4.8), ("g13", "r1", -20.0, 20.5), ("g14", "r1", -14.2, 4.8), ("g15", "r1", -10.0, 20.5),
              ("g16", "r1", -47.0, 20.5), ("g17", "r1", -34.0, 14.0)]
    ys = {"r1": R1, "r2": R2, "r3": R3}
    for n, ly, x, z in ground:
        L.ground(n, x, ys[ly], z, layer=ly)
    street = [("g18", -6.0, SW, -36.5), ("g19", 5.5, 0.0, -36.0), ("g20", 25.0, 0.0, -36.5), ("g21", 29.2, SW, -14.0),
              ("g22", 29.2, SW, 6.0), ("g23", 25.0, 0.0, 18.8), ("g24", 29.0, 0.0, 30.0), ("g25", 14.0, SW, 35.0),
              ("g26", -46.0, 0.0, 29.0), ("g27", -24.0, SW, 35.0), ("g28", -7.0, SW, 4.8), ("g29", 13.8, SW, -18.5)]
    for n, x, y, z in street:
        L.ground(n, x, y, z, layer="street")
    L.deviations.append("g23 at (25, 0, 18.8) instead of (25, 0, 18): still 'behind the water barriers', which stand at z 17.6..18.2.")
    # 2026-11-28: drones removed by the owner: the level has no air points (the 18 Buzzard points of the first build are gone).

    # ------------------------------------------------------------------ cover (7.6): movement solids 0.9 to 1.6 m tall, one every 3 m
    # along long faces, and the inner faces of the parapets every 4 m
    L.extra["_coverRule"] = {"minHeight": 0.9, "maxHeight": 1.7, "maxSide": 12.0, "out": 0.6, "spacing": 2.2, "every": 4.5,
                             "shortSideMin": 1.8, "parapetTags": ["parapet"], "parapetEvery": 12.0,
                             "tags": ["roof-stair"], "skipTags": ["explosive", "trash_can", "light_pole", "street_lamp", "cafe_table", "sign_pole", "muni_meter", "standpipe", "alarm_pedestal", "bike_rack", "traffic_cone", "traffic_drum", "bollard",
                            "exhaust_fan", "roof_vent", "antenna_mast", "truss_tower", "wayfinding_pylon", "shed_post", "cable_ramp", "hydrant",
                            "fire_hydrant", "milk_crates", "bucket_stack", "vendor_stool", "goods_carton", "cafe_chairs", "pallet_single"]}

    # ------------------------------------------------------------------ nav layers, links, reach; the guide graph; drops; tuning
    links = [
        {"id": "steelStair", "name": "L1 STEEL STAIR", "a": "r3", "b": "r2", "kind": "stair",
         "path": [[-31.0, R3, -21.0], [-30.0, R3, -21.0], [-27.6, R3, -21.0], [-23.6, R2, -21.0], [-23.0, R2, -21.0]]},
        {"id": "tankStair", "name": "L2 TANK STAIR", "a": "r3", "b": "r2", "kind": "stair",
         "path": [[-43.0, R3, -13.0], [-43.0, R3, -12.0], [-43.0, R2, -8.0], [-43.0, R2, -7.0]]},
        {"id": "backStair", "name": "L3 BACK STAIR", "a": "r2", "b": "r1", "kind": "stair",
         "path": [[-35.0, R2, 7.0], [-35.0, R2, 8.0], [-35.0, R1, 12.0], [-35.0, R1, 13.0]]},
        {"id": "billboardStair", "name": "L4 BILLBOARD STAIR", "a": "r2", "b": "r1", "kind": "stair",
         "path": [[-15.0, R2, -5.0], [-15.0, R2, -4.0], [-15.0, R1, 0.0], [-15.0, R1, 1.0]]},
        {"id": "scaffold", "name": "L5 SCAFFOLD", "a": "r1", "b": "street", "kind": "stair", "generated": True, "path": sc_poly},
        {"id": "serviceStair", "name": "L6 SERVICE STAIR", "a": "r1", "b": "street", "kind": "stair", "generated": True, "path": ss_poly},
    ]
    L.nav = {
        "source": "midtown.md 7.2, 16.3: four layers, the links L1 to L6 (read from nav step B), spawn reach, firing cells, the "
                  "stranded rule. The grids are written by the engine bake with FMIBoxWorld's code: `grid` is absent until then.",
        "cell": 0.5, "inflate": 0.5, "bandMin": 0.47, "bandMax": 1.5,
        "layers": [
            {"id": "street", "y": 0.0, "rect": {"minX": -50, "maxX": 31, "minZ": -38, "maxZ": 37}, "floor": "plane", "cols": 162, "rows": 150, "grid": None},
            {"id": "r1", "y": R1, "rect": {"minX": -50, "maxX": -4, "minZ": -4, "maxZ": 22}, "floor": "boxes", "cols": 92, "rows": 52, "grid": None},
            {"id": "r2", "y": R2, "rect": {"minX": -50, "maxX": -8, "minZ": -38, "maxZ": 8}, "floor": "boxes", "cols": 84, "rows": 92, "grid": None},
            {"id": "r3", "y": R3, "rect": {"minX": -50, "maxX": -30, "minZ": -38, "maxZ": -12}, "floor": "boxes", "cols": 40, "rows": 52, "grid": None},
        ],
        "links": links,
        "spawnReach": {"r3": ["r3", "r2"], "r2": ["r2", "r3", "r1"], "r1": ["r1", "r2", "street"], "street": ["street", "r1"]},
        "firingCellRange": 30, "strandedAfter": 10,
    }
    nodes, edges = [], []

    def node(nid, layer, pos):
        nodes.append({"id": nid, "layer": layer, "pos": [round(v, 3) for v in pos]})
        return len(nodes) - 1

    for lk in links:
        a = node(lk["id"] + ".a", lk["a"], lk["path"][0])
        b = node(lk["id"] + ".b", lk["b"], lk["path"][-1])
        edges.append({"from": a, "to": b, "kind": "stair", "link": lk["id"], "path": lk["path"],
                      "bias": 10.0 if lk["id"] == "serviceStair" else 0.0,
                      "step": {"kind": "stair", "link": lk["id"], "height": round(abs(lk["path"][0][1] - lk["path"][-1][1]), 2)}})
    drops = [
        {"id": "D1", "from": [-23.0, R2, -4.6], "to": [-23.0, DECK, -2.8], "height": round(R2 - DECK, 2), "fromLayer": "r2", "toLayer": "r1",
         "walkOff": [[-23.0, DECK, 3.0], [-23.0, R1 + 0.3, 3.25], [-23.0, R1, 4.4]],
         "what": "C's south parapet gap x -24..-22 onto THE LOFTLARK's raised deck (0.6 m) on D: the shortcut from Reel 7 to D, one way"},
        {"id": "D2", "from": [-47.0, R2, 7.4], "to": [-47.0, DECK, 9.0], "height": round(R2 - DECK, 2), "fromLayer": "r2", "toLayer": "r1",
         "walkOff": [[-47.0, DECK, 14.5], [-47.0, R1 + 0.3, 14.75], [-47.0, R1, 15.8]],
         "what": "B's south parapet gap x -48..-46 onto the dunnage platform (0.6 m) on E: the flank, one way"},
        {"id": "D3a", "from": [-6.8, levels[5], 19.2], "to": [-6.8, SHED, 21.5], "height": round(levels[5] - SHED, 2),
         "what": "the scaffold's south landing (5.35) through the opening onto the shed roof"},
        {"id": "D3b", "from": [-5.0, SHED, 22.5], "to": [-3.0, 0.0, 22.5], "height": SHED, "what": "off the shed's east edge to the roadway"},
    ]
    for d in drops[:2]:
        # the bottom node is where the deck's step meets the roof (the deck itself is off the r1 layer's band)
        a = node(d["id"] + ".top", d["fromLayer"], d["from"])
        b = node(d["id"] + ".bottom", d["toLayer"], d["walkOff"][-1])
        edges.append({"from": a, "to": b, "kind": "drop", "drop": d["id"], "oneWay": True, "bias": 10.0,
                      "path": [d["from"], d["to"]] + d["walkOff"], "step": {"kind": "drop", "link": d["id"], "height": d["height"]}})
    L.guide = {"source": "midtown.md 6.4: the route graph the guidance draws over (nearest unsecured reel by route length; to the "
                         "extraction once all are in); within a layer the layer's own path search at run time, across layers "
                         "these edges (stairs both ways, drops down only). The service stair and the drops cost 10 m more, so "
                         "the scaffold is the drawn way down. D3 (the shed hop) is a free player choice, never drawn.",
               "mode": "routeGraph", "graph": {"nodes": nodes, "edges": edges}, "targetHysteresis": 0.15, "markerHeightLabelOver": 3.0,
               "intendedOrder": ["reel7", "reel8", "reel9"],
               "waivers": [{"check": "guide.intendedLegsVsDesign", "legs": ["start -> reel7", "reel8 -> reel9"],
                            "owner": "the designer (midtown.md 6.5), with the grey box of stage 2",
                            "reason": "the design's numbers count the steel stair and the scaffold short: L1's head bridge and "
                                      "eight steps, and the scaffold's eight flights and landings, walked as the polylines "
                                      "the link check proves, are 42 m and 135 m. The routes are the design's; the rating "
                                      "times (330 s, 480 s) are re-timed in the grey box (MAPS.md stage 2)."}],
               "designLegs": [{"from": "start", "to": "reel7", "m": 37}, {"from": "reel7", "to": "reel8", "m": 47},
                              {"from": "reel8", "to": "reel9", "m": 108}, {"from": "reel9", "to": "extraction", "m": 75}]}
    L.drops = drops
    L.extra["_audio"] = {
        "meta": {"file": "audio_midtown.json", "about": "Midtown's audio zones and beds (midtown.md 13), audio.json's zone schema, "
                 "named by levels.json data.audio; no El and no train here (MAPS.md E6).", "generator": "tools/levels/build_level.py"},
        "zones": {
            "about": "web units; each zone has a fade margin; the strongest wins (audio.json zones). There is no roof preset "
                     "yet: the roofs use street with their own bed",
            "street": {"preset": "street", "default": True},
            "roofs": {"preset": "street", "box": [[-50, 12, -38], [-3, 40, 22]], "fade": 3.0, "bed": "bed_roofs_wind"},
            "square": {"preset": "street", "box": [[-8, 0, -38], [31, 12, 22]], "fade": 3.0, "bed": "bed_square_premiere"},
            "w46": {"preset": "street", "box": [[-50, 0, 22], [31, 12, 37]], "fade": 3.0, "bed": "bed_w46_traffic"},
            "bulkheadA": {"preset": "shop", "box": [[-48, 21.2, -37], [-44, 24.0, -33]], "fade": 1.5, "interior": True},
            "tankHouse": {"preset": "shop", "box": [[-22, 17.6, -35], [-16, 20.4, -29]], "fade": 1.5, "interior": True},
            "machineRoom": {"preset": "shop", "box": [[-40, 17.6, -8], [-34, 20.6, -2]], "fade": 1.5, "interior": True},
            "serviceStair": {"preset": "shop", "box": [[-13, 0, 4], [-8, 16.8, 10]], "fade": 1.5, "interior": True},
            "booth": {"preset": "shop", "box": [[10.6, 0.15, -34], [21.4, 2.25, -29.5]], "fade": 1.5, "interior": True},
        },
        "ambience": {"beds": {"night": "bed_night_midtown"}, "train": None,
                     "oneShots": {"about": "midtown.md 13: new sounds for the audio lane (none exist yet)",
                                  "hvac_hum": {"points": [[-35.5, 22.7, -16], [-44.7, 22.7, -30], [-40, 19.0, 4.5], [-43, 15.4, 13], [-15.2, 19.0, -13.7], [-11.2, 19.0, -13.7]], "range": 6.0},
                                  "premiere_loop": {"from": "the screens' speakers", "note": "invented instrumental, no real song"},
                                  "crowd_murmur": {"place": "behind the north barricades"}, "generator_hum": {"pos": [20.0, 0.8, -20.6]},
                                  "truck_arrival": {"on": "all reels secured", "note": "engine and air brakes, then idle"},
                                  "g1_glitch": {"on": "objective:secured reel8"}, "ipx_takeover": {"on": "all reels secured"}}},
    }
    L.tuning = {"source": "midtown.md 7.1, 16.3: the level's adds over config.json (absent for the Block)",
                "difficulty": {"pursuitBudgetAdd": 2},
                "spawn": {"excludePlayerRoom": True}, "rating": {"time": [[330, 2], [480, 1]]}, "startPitch": -4}
    L.vantage = {"source": "the top of the Stand and the gantry letterbox", "web": {"stairsFoot": {"x": -6.0, "y": SW, "z": 13.0}, "deck": {"x": 16.0, "y": 3.35, "z": -33.0}},
                 "ue": {"stairsFoot": {"X": -600, "Y": 1300, "Z": 15}, "deck": {"X": 1600, "Y": -3300, "Z": 335}}}
    L.extra["checks"] = {
        "source": "level-specific inputs for tools/levels/check_level.py",
        "goonDoors": [{"x": x, "z": z, "layer": ly, "what": w} for x, z, ly, w in (
            (-19.0, -29.1, "r2", "tank house door (Reel 7)"), (-37.0, -2.1, "r2", "machine room door"),
            (-13.15, 5.2, "r1", "service stair roof door"), (-7.85, 5.2, "street", "service stair street door"),
            (10.3, -32.0, "street", "booth west door"), (21.7, -32.0, "street", "booth east door"),
            (-44.1, -35.0, "r3", "bulkhead A door"), (-8.15, 1.5, "r1", "gantry door south"), (-8.15, 12.0, "r1", "gantry door north"))],
        "sightlines": {"source": "midtown.md 10 (check_level.py sight.*)", "rules": [
            {"id": "squareUnder45m", "rect": [-8, 31, -38, 22], "max": 45.0, "step": 2.0,
             "why": "breakers keep every open ground line in the square under 45 m, the Goons' sight range"}]},
        "shootThrough": [{"id": "booth", "a": [16.0, 1.5, -26.0], "b": [16.0, 1.5, -31.5], "frame": [slot],
                          "what": "a ray from the front court at 1.5 m through the booth's slot reaches the desk side"}],
    }
    L.extra["views"] = {"source": "midtown.md 15: the shot views (eye, look at)", "list": [
        {"id": "V1", "eye": [-43.2, 22.88, -35.0], "look": [10, 10, -10]}, {"id": "V2", "eye": [-19.3, 19.28, -27.0], "look": [-5, 22, -10]},
        {"id": "V3", "eye": [-6.2, 15.68, 6.0], "look": [20, 3, 6]}, {"id": "V4", "eye": [-5.0, 8.6, 17.0], "look": [15, 3, 0]},
        {"id": "V5", "eye": [16.0, 5.03, -33.0], "look": [10, 2, 20]}, {"id": "V6", "eye": [0.0, 1.68, 26.0], "look": [12, 6, -20]}]}

    # ------------------------------------------------------------------ title camera (18)
    L.cinematic = [((24, 30, 34), (10, 6, -10)), ((18, 24, 24), (6, 6, -18)), ((10, 18, 10), (-6, 20, 6)), ((3, 17, 3), (-6, 21, 6)),
                   ((-2, 22, -6), (-12, 22, -24)), ((-6, 26, -16), (-19, 25, -32)), ((-14, 28, -24), (-38, 28, -26)),
                   ((-24, 30, -30), (-40, 26, -24)), ((-34, 29, -36), (-30, 20, -10)), ((-44, 27, -26), (-20, 16, 0)),
                   ((-40, 24, -8), (-6, 14, 6)), ((-30, 22, 4), (10, 6, -6)), ((-12, 20, 10), (16, 4, -20)), ((8, 26, 30), (10, 6, -10))]
    L.steam = [(-38.0, R3 + 0.05, -30.0), (-20.0, R2 + 0.05, -16.0), (-36.0, R2 + 0.05, 2.0), (-18.0, R1 + 0.05, 0.0)]
    L.puddles = [(-3.2, -20, 1.0), (7.4, -14, 0.8), (-3.2, 10, 0.9), (23.0, 20, 1.2), (5.0, 33.0, 1.4), (-20.0, 25.0, 1.0)]
    for name, r in (("asphalt", rect(-4, 8, -38, 24.5)), ("asphalt", rect(22, 28, -38, 24.5)), ("asphalt", rect(-50, 31, 24.5, 33.5)),
                    ("concrete", rect(-8, -4, -38, 22)), ("concrete", rect(28, 30, -38, 22)), ("concrete", rect(-50, 31, 22, 24.5)),
                    ("concrete", rect(-50, 31, 33.5, 36)), ("concrete", rect(8, 22, -38, 22)), ("asphalt", rect(-50, -30, -38, -12)),
                    ("asphalt", rect(-50, -30, -12, 22)), ("asphalt", rect(-28, -8, -38, -4)), ("asphalt", rect(-28, -8, -4, 22)),
                    ("metal", rect(-8, -4.5, -2, 14)), ("metal", rect(-8, -3, 14, 20)), ("metal", rect(10, 22, -34, -22))):
        L.surfaces.append({"surface": name, "rect": r})
    L.deviations.append("surfaces use audio.json's keys: the design's granite, gravel, bitumen, grating and steel (16.3) are "
                        "concrete, asphalt, asphalt, metal and metal, so footsteps and impacts resolve.")
    for h, r, what in ((0.0, rect(-4, 8, -38, 24.5), "Seventh Av roadway"), (0.0, rect(22, 28, -38, 24.5), "Broadway roadway"),
                       (0.0, rect(-50, 31, 24.5, 33.5), "W 46 St roadway"), (SW, rect(-8, -4, -38, 22), "west sidewalk"),
                       (SW, rect(8, 22, -38, 22), "the plaza"), (SW, rect(28, 30, -38, 22), "east sidewalk"),
                       (SW, rect(-50, 31, 22, 24.5), "W 46 St north sidewalk"), (SW, rect(-50, 31, 33.5, 36), "W 46 St south sidewalk"),
                       (SHED, rect(-8, -4.2, 20.1, 24.4), "sidewalk shed"), (R1, rect(-50, -30, 8, 22), "E roof (r1)"),
                       (R1, rect(-28, -8, -4, 22), "D roof (r1)"), (R1, rect(-8, -4.5, -2, 14), "the gantry deck (r1)"),
                       (R2, rect(-50, -30, -12, 8), "B roof (r2)"), (R2, rect(-28, -8, -38, -4), "C roof (r2)"), (R3, rect(-50, -30, -38, -12), "A roof (r3)")):
        L.floors.append({"h": h, "rect": r, "what": what})
    _signs(L)
    _clutter(L)
    L.layout = {"WALK_LEVELS": {"street": 0.0, "r1": R1, "r2": R2, "r3": R3}, "PARAPET": {"height": PH, "thickness": PT, "guard": GH},
                "SEVENTH": {"westSidewalk": [-8, -4], "roadway": [-4, 8]}, "PLAZA": [8, 22], "BROADWAY": {"roadway": [22, 28], "eastSidewalk": [28, 30]},
                "W46": {"northSidewalk": [22, 24.5], "roadway": [24.5, 33.5], "southSidewalk": [33.5, 36]},
                "STAND": {"rect": [10, 22, -34, -22], "tiers": 8, "tierDepth": 1.5, "tierRise": 0.4, "frontCourt": [13, 19, -29.2, -22]},
                "BOOTH": [10.6, 21.4, -34, -29.5], "GANTRY": [-8, -4.5, -2, 14], "LED_WALL": [-4.5, -3.9, -2, 14, 16.2, 25.2],
                "SCAFFOLD": {"rect": [-8, -3, 14, 20], "levels": levels}, "SERVICE_STAIR": [-13, -8, 4, 10], "LIGHT_COURT": [-30, -28, -38, 22, 10.4]}
    return L


def _signs(L):
    """Screens, storefronts and lettering (midtown.md 12): invented names only; IPX the only real mark; English."""
    S = L.signage

    def add(sid, text, kind, x, y, z, nx, nz, w, h, colour, night="on", note=None, slides=None, lit=True):
        e = {"id": sid, "text": text, "kind": kind, "lit": lit, "night": night, "colour": colour,
             "web": {"pos": {"x": x, "y": y, "z": z}, "normal": {"x": nx, "y": 0, "z": nz}, "width": w, "height": h},
             "ue": {"pos": {"X": round(x * 100, 2), "Y": round(z * 100, 2), "Z": round(y * 100, 2)}, "width": w * 100, "height": h * 100}}
        if note:
            e["note"] = note
        if slides:
            e["slides"] = slides
        S.append(e)

    add("G1", "WORLD PREMIERE · MIDNIGHT", "screen", -3.9, 20.7, 6.0, 1, 0, 16, 9, "white on black, a small oxblood VLTR mark",
        note="playable behind it; countdown from 8:00; dies (0.4 s glitch, NO SIGNAL) when reel8 is secured; IPX PRESENTS when all three are in",
        slides=["WORLD PREMIERE · MIDNIGHT + countdown", "STAND BY", "NO SIGNAL", "IPX PRESENTS"])
    add("E1", "MIRAVESSE · Eau de Nuit", "screen", 30.9, 14.0, -24.0, -1, 0, 24, 18, "cool", note="east tower podium (art, past the bound)",
        slides=["MIRAVESSE · Eau de Nuit", "NORTHBOUND AIRWAYS · Fly the late one", "IPX (6 s after the last reel)"])
    add("E2a", "KESTREL MOBILE · Five bars, five boroughs", "screen", 30.9, 16.0, -6.0, -1, 0, 8, 20, "blue and white", note="east hotel, vertical")
    add("E2b", "BRASS & BUN · Burgers till four", "screen", 30.9, 16.0, 6.0, -1, 0, 8, 20, "warm white", note="east hotel, vertical")
    add("E3", "THE MERIDALE THEATRE presents LAMPLIGHT AVENUE, a new musical", "screen", 30.0, 12.0, 22.0, -1, -1, 20, 12, "cool",
        note="curved corner screen", slides=["THE MERIDALE THEATRE presents LAMPLIGHT AVENUE, a new musical", "VESPERLINE CRUISES", "IPX"])
    add("N1", "HOROVAN watches", "screen", 10.0, 22.0, -39.0, 0, 1, 14, 8, "cool", note="north tower stack beyond the bound (three screens)",
        slides=["HOROVAN watches", "NORTHWEFT fall collection", "FIZZWICK SODA", "IPX"])
    add("S1", "DUSKLINE TOURS · The city after dark", "screen", 5.0, 9.0, 35.95, 0, -1, 12, 6, "cool", note="W 46 St south facade")
    add("ticker", "SQUARE CLOSED TONIGHT FOR A PREMIERE · CROSSTOWN TRAFFIC HEAVY · FORECAST: CLEAR, 41°", "ticker", 29.95, 8.4, -18.0, -1, 0, 24, 0.8,
        "amber LED", note="on the theatre, panned 0.35 m/s")
    add("C1", "MARLOWE & FINCH · The holiday floor is open", "billboard", -8.9, 23.6, -28.0, 1, 0, 16, 8, "lightbox, warm white", note="C's roof billboard, lit face east")
    for i, (t, x, y, z, nx, nz, w, h, col, note, lit) in enumerate((
            ("SEVENTH AV SOUVENIRS", -8.05, 3.6, -30.0, 1, 0, 6, 0.9, "lightbox", "C ground floor", True),
            ("SLICE OF SEVENTH", -8.05, 3.6, -20.0, 1, 0, 5, 0.9, "lightbox", "C ground floor", True),
            ("SHUTTERBOX CAMERA & ELECTRONICS", -8.05, 3.6, -10.0, 1, 0, 7, 0.9, "LED flex", "C ground floor", True),
            ("BELLHAVEN SAVINGS", -8.05, 3.6, 17.0, 1, 0, 5, 0.9, "closed bank lobby, unlit", "D ground floor", False),
            ("THE MERIDALE THEATRE", 29.95, 5.0, -14.0, -1, 0, 10, 2.2, "marquee bulb band, slow chase", "east sidewalk", True),
            ("HOTEL CASTELLANE", 29.95, 4.2, 6.0, -1, 0, 7, 1.0, "canopy letters", "east sidewalk", True),
            ("BRANNIGAN'S CHOP HOUSE", 14.0, 3.6, 35.95, 0, -1, 8, 1.0, "neon", "W 46 St south", True),
            ("ASHBY & CROSS PHARMACY", -24.0, 3.6, 35.95, 0, -1, 6, 1.0, "lightbox", "W 46 St south", True),
            ("HALVORSEN BUILDING", -30.05, 22.0, -26.0, 1, 0, 9, 0.7, "raised letters on A's parapet", "A", False),
            ("CORVIN HALL", -8.05, 16.8, -21.0, 1, 0, 7, 0.7, "on C's cornice", "C", False),
            ("THE LOFTLARK", -8.05, 15.8, 18.0, 1, 0, 4, 0.8, "neon, unlit (the lounge is closed)", "D", False),
            ("KESSLER & ROTH SCAFFOLD", -3.0, 2.6, 17.0, 1, 0, 2.4, 0.6, "contractor's board", "the scaffold tower", False),
            ("BRIGHTWIRE EVENTS", 3.55, 2.0, -32.0, 1, 0, 5, 0.8, "truck livery, VLTR sprayed over it", "the production truck", False),
            ("CITY CROSSTOWN", 25.35, 2.2, 0.0, 1, 0, 6, 0.5, "plain blue and white, no real livery", "the stalled bus", False))):
        add("store.%d" % i, t, "band" if lit else "lettering", x, y, z, nx, nz, w, h, col, note=note, lit=lit)
    for i, (t, x, z, nx, nz) in enumerate((("SEVENTH AV", -4.2, -36.0, 1, 0), ("BROADWAY", 28.2, -36.0, -1, 0), ("W 46 ST", -4.2, 24.6, 0, 1),
                                           ("W 46 ST", 28.2, 24.6, 0, 1))):
        add("street.%d" % i, t, "street", x, 3.0, z, nx, nz, 0.9, 0.2, "plain green blade, no agency mark", lit=False)
    for i, (t, x, y, z, nx, nz, col) in enumerate((("VULTURES", -30.05, 22.4, -16.0, 1, 0, "oxblood"), ("VLTR", 3.55, 1.4, -34.0, 1, 0, "oxblood"),
                                                   ("RULE", -7.95, 1.2, 0.0, 1, 0, "gold"), ("INC.", 13.0, 0.9, -29.15, 0, 1, "gold"))):
        add("graffiti.%d" % i, t, "graffiti", x, y, z, nx, nz, 1.6, 0.6, col, lit=False)


# Planned collider breakdown (midtown.md 15, 760): the groups this table authors as clutter, with the plan. The
# premiere structures and the rest of the street come out of the 167 contingency.
PLAN = {"street": 67, "barriers": 26, "roof": 76, "premiere": 40, "w46": 30, "spare": 60}


def _clutter(L):
    """Street and plaza furniture, barriers, the premiere's structures, W 46 St and the rooftop dressing of midtown.md 15.
    The breakers (the premiere's broadcast van, catering truck, light towers, staging truck, press walls, tents and
    the kiosks) keep every open ground line in the square under 45 m (midtown.md 10, check sight.squareUnder45m)."""
    C = L.clutter
    S = SW
    # ---------------------------------------------------------------- the premiere's vehicles and structures (the breakers)
    for x0, x1, z0, z1, h, name, what in (
            (-3.8, -1.6, -21.0, -14.2, 3.4, "broadcast_van", "a broadcast truck, dish folded, no network mark"),
            (5.7, 7.9, -4.2, 2.6, 3.0, "catering_truck", "a catering truck, hatch shut"),
            (-3.8, -1.6, 7.4, 11.6, 3.2, "generator_truck", "the premiere's generator truck, cables to the Stand"),
            (2.4, 4.6, -26.0, -19.5, 3.4, "broadcast_van", "a second broadcast truck, mast down"),
            (0.8, 3.4, -13.0, -6.0, 3.3, "cable_truck", "the cable and rigging truck"),
            (4.0, 6.1, -13.4, -7.4, 3.0, "production_trailer", "a production office trailer, blinds down"),
            (-1.8, 0.6, -0.2, 6.2, 3.0, "production_trailer", "the talent trailer, steps folded"),
            (2.0, 3.4, 12.8, 15.8, 2.6, "light_tower", "a light tower on its trailer, mast up"),
            (22.1, 24.5, -22.0, -14.0, 3.3, "staging_truck", "a staging truck, ramp up (BRIGHTWIRE EVENTS on the box)"),
            (26.2, 27.7, 7.6, 10.8, 2.6, "light_tower", "a light tower on its trailer, mast up"),
            (9.0, 12.0, -8.6, -5.6, 2.8, "vip_tent", "a white pop-up tent, sides down"),
            (18.8, 20.4, -4.4, -3.2, 2.5, "merch_booth", "a merch booth, shuttered"),
            (15.0, 16.4, -5.6, -4.6, 2.2, "coat_check", "the premiere's coat-check booth"),
            (18.9, 19.5, -0.6, 0.0, 4.2, "truss_tower", "a lighting truss tower"),
            (10.8, 11.4, -0.6, 0.0, 4.2, "truss_tower", "a lighting truss tower"),
            (9.0, 10.4, 1.6, 3.0, 2.6, "security_booth", "a security booth"),
            (19.0, 20.2, 9.4, 10.6, 4.0, "sound_tower", "a sound tower: two speaker stacks on a riser"),
            (8.6, 11.0, 14.4, 15.6, 2.3, "portable_toilets", "a row of portable toilets"),
            (10.0, 13.4, -21.7, -21.4, 2.4, "press_wall", "the press wall (step-and-repeat), blank panels"),
            (20.2, 21.8, -13.6, -12.8, 2.6, "camera_riser", "a camera riser with a jib"),
            (20.0, 21.4, 4.8, 5.6, 2.6, "speaker_stack", "a speaker stack"),
            (10.6, 12.0, 9.6, 11.0, 2.3, "photo_booth", "a photo booth, curtain drawn"),
            (17.2, 17.8, -6.6, -6.0, 4.2, "truss_tower", "a lighting truss tower"),
            (14.6, 15.2, -15.8, -15.2, 4.2, "truss_tower", "a lighting truss tower"),
            (-7.95, -7.6, -20.0, -14.0, 2.4, "hoarding", "a plywood hoarding round a shopfront refit"),
            (-6.7, -6.2, -3.6, -2.4, 2.5, "phone_kiosk", "a sidewalk phone kiosk, no brand"),
            (24.6, 25.6, -12.4, -9.4, 2.6, "light_tower", "a light tower on its trailer"),
            (13.6, 16.4, -12.6, -12.3, 2.4, "press_wall", "the photographers' backdrop"),
            (14.4, 16.8, 11.0, 11.3, 2.4, "press_wall", "a sponsor wall, blank"),
            (28.5, 29.9, -24.0, -22.0, 2.6, "newsstand", "a newsstand on the east sidewalk"),
            (28.5, 29.9, 9.4, 11.4, 2.6, "newsstand", "a closed newsstand"),
            (-6.2, -4.2, -12.0, -8.0, 2.5, "bus_shelter", "a bus shelter, its ad panel dark"),
            (8.2, 8.8, -9.6, -8.6, 2.4, "wayfinding_pylon", "a wayfinding pylon (a map, no logos)"),
            (8.2, 8.8, 7.0, 7.95, 2.4, "wayfinding_pylon", "a wayfinding pylon (a map, no logos)"),
            (11.0, 11.6, -3.6, -3.0, 4.2, "truss_tower", "a lighting truss tower"),
            (18.4, 19.0, -16.6, -16.0, 4.2, "truss_tower", "a lighting truss tower"),
            (-1.6, -0.2, -27.0, -24.0, 2.6, "light_tower", "a light tower on its trailer"),
            (0.4, 1.8, 17.0, 20.0, 2.6, "light_tower", "a light tower on its trailer"),
            (-5.0, -4.6, -33.6, -32.4, 2.5, "phone_kiosk", "a sidewalk phone kiosk, no brand"),
            (25.6, 27.8, -27.0, -20.0, 3.4, "satellite_truck", "a satellite uplink truck, dish stowed"),
            (25.6, 27.0, -2.0, 1.0, 2.6, "light_tower", "a light tower on its trailer"),
            (13.4, 14.6, -0.4, 2.2, 2.4, "info_booth", "the premiere's information booth"),
            (15.0, 19.0, -9.8, -9.2, 4.0, "screen_trailer", "a mobile screen on its trailer, showing the countdown"),
            (20.6, 21.8, -18.8, -16.7, 2.6, "light_tower", "a light tower on its trailer"),
            (-1.0, 0.4, -11.0, -9.0, 1.9, "road_cases", "the crew's road cases, stacked"),
            (3.2, 4.6, 1.2, 2.8, 1.9, "road_cases", "the crew's road cases, stacked"),
            (-7.85, -6.6, -26.0, -24.0, 2.5, "newsstand", "a newsstand on the west sidewalk")):
        C("premiere", name, x0, x1, z0, z1, h, y0=(S if 8 <= x0 < 22 or x0 >= 28 or x1 <= -4 else 0.0), what=what)
    # ---------------------------------------------------------------- crowd-control barriers (1.1 m): the red carpet's edges and the closures
    for x0, z0 in ((8.4, -14.5), (8.4, -11.0), (21.6, -16.0), (21.6, -9.0)):
        C("barriers", "bike_barrier", x0, x0 + 0.5, z0, z0 + 2.4, 1.1, y0=S if x0 < 22 else 0.0, what="a steel crowd barrier")
    for x0, z0 in ((-3.8, -32.0), (4.6, -33.2), (-3.0, 18.6), (4.0, 20.0), (22.4, 20.4), (25.0, 20.4), (12.0, 20.2), (16.4, 20.2)):
        C("barriers", "bike_barrier", x0, x0 + 2.4, z0, z0 + 0.5, 1.1, y0=S if 8 <= x0 < 22 else 0.0, what="a steel crowd barrier")
    for x0 in (-3.6, 0.6, 4.8):
        C("barriers", "jersey_barrier", x0, x0 + 2.8, 23.8, 24.4, 0.81, surface="concrete", what="the Seventh Av closure at W 46 St")
    for z0 in (-34.0, -11.0, 19.0):
        C("barriers", "water_barrier", 26.2, 27.8, z0, z0 + 1.8, 0.9, surface="rubber", what="a water-filled barrier")
    # ---------------------------------------------------------------- plaza and sidewalk furniture
    for x, z in ((9.0, -16.5), (21.4, -5.0), (9.0, 6.6), (21.4, 15.8), (14.4, -20.9), (28.6, -32.0), (28.6, 0.0), (28.6, 18.0),
                 (-7.6, -12.0), (-7.6, 0.4)):
        C("street", "trash_can", x - 0.29, x + 0.29, z - 0.29, z + 0.29, 0.95, y0=S)
    for x, z in ((11.4, 9.0), (18.6, -8.0), (14.2, 17.0), (18.2, 17.0)):
        C("street", "bench", x - 0.9, x + 0.9, z - 0.3, z + 0.3, 0.85, y0=S, what="a plaza bench")
    for x, z in ((13.4, -6.4), (16.4, -7.0)):
        C("street", "cafe_chairs", x - 0.25, x + 0.25, z - 0.25, z + 0.25, 0.9, y0=S, what="cafe chairs, stacked two high")
    for x, z in ((11.0, -12.0), (19.6, -11.0), (19.8, 14.6)):
        C("street", "bollard_planter", x - 0.35, x + 0.35, z - 0.35, z + 0.35, 0.9, y0=S, surface="concrete", what="a round granite bollard-planter")
    for x, z in ((-7.8, -33.0), (-7.8, -20.0), (29.7, -20.0), (29.7, 8.8), (-7.8, 2.0)):
        C("street", "standpipe", x - 0.15, x + 0.15, z - 0.15, z + 0.15, 0.9, y0=S)
    for x, z in ((-4.4, -24.0), (-4.4, -12.0), (-4.4, 0.0), (28.4, -30.0), (28.4, -8.0), (28.4, 4.0)):
        C("street", "hydrant", x - 0.16, x + 0.16, z - 0.16, z + 0.16, 0.74, y0=S)
    for x, z in ((-4.5, -34.0), (-4.5, -28.0), (-4.5, -16.0), (-4.5, -3.0), (28.3, -28.4), (28.3, -17.5), (28.3, -4.0), (28.3, 10.0), (28.3, 16.0)):
        C("street", "sign_pole", x - 0.038, x + 0.038, z - 0.038, z + 0.038, 2.7, y0=S, what="a street-sign pole")
    for x, z in ((-7.6, -29.0), (-7.6, -16.6), (29.6, -24.0), (29.6, -12.0)):
        C("street", "newspaper_box", x - 0.24, x + 0.24, z - 0.21, z + 0.21, 1.08, y0=S)
    for x, z in ((12.0, -16.0), (18.0, -14.6), (12.4, 4.2), (17.6, 8.6), (13.0, 19.8), (20.8, 19.8)):
        C("street", "cable_ramp", x - 0.6, x + 0.6, z - 0.25, z + 0.25, 0.08, y0=S, surface="rubber", what="a cable ramp over the premiere's feeds")
    for x0, x1, z0, z1, h, name, what in ((28.2, 29.8, -36.4, -35.4, 1.1, "valet_stand", "the theatre's valet stand"),
                                         (28.3, 28.9, -22.6, -21.0, 1.2, "queue_rail", "the theatre's queue rail"),
                                         (28.3, 28.9, -15.6, -14.6, 1.2, "queue_rail", "the theatre's queue rail"),
                                         (28.3, 29.8, 3.0, 3.6, 1.2, "luggage_cart", "the hotel's luggage cart"),
                                         (-7.9, -6.6, -6.0, -4.6, 1.0, "crate_stack", "a sidewalk delivery"),
                                         (-7.9, -7.2, -37.6, -36.8, 1.4, "atm_kiosk", "a street-side cash machine, no bank mark")):
        C("street", name, x0, x1, z0, z1, h, y0=S, what=what)
    # ---------------------------------------------------------------- W 46 St
    for x in (-46.0, -38.0, -30.0, -22.0, -14.0, 4.0, 10.0, 26.0):
        C("w46", "planter", x - 0.6, x + 0.6, 35.3, 35.95, 0.95, y0=S, surface="concrete", what="a planter at a restaurant front")
    for x in (-42.0, -34.0, -18.0, 0.0, 7.0, 24.0, 29.6):
        C("w46", "trash_can", x - 0.29, x + 0.29, 33.7, 34.28, 0.95, y0=S)
    for x in (-44.0, -26.0, -2.0, 12.0):
        C("w46", "newspaper_box", x - 0.24, x + 0.24, 33.7, 34.12, 1.08, y0=S)
    for x in (-48.0, -36.0, -20.0, -10.0, 2.0, 18.0, 27.0):
        C("w46", "sign_pole", x - 0.038, x + 0.038, 33.62, 33.7, 2.7, y0=S)
    for x in (-48.0, -40.0, -32.0, -24.0, -16.0, 6.0, 12.0, 26.0):
        C("w46", "sign_pole", x - 0.038, x + 0.038, 24.3, 24.376, 2.7, y0=S)
    for x in (-38.0, -20.0, 8.0, 22.0):
        C("w46", "hydrant", x - 0.16, x + 0.16, 23.8, 24.12, 0.74, y0=S)
    for x0, x1, z0, z1, h, name in ((-28.6, -26.8, 22.05, 22.7, 1.2, "crate_stack"), (-16.6, -15.4, 22.05, 22.65, 0.95, "trash_bags"),
                                    (-45.0, -43.2, 22.05, 22.7, 1.2, "crate_stack"), (-6.8, -5.0, 35.25, 35.95, 1.1, "crate_stack"),
                                    (-34.0, -32.6, 35.3, 35.95, 0.95, "trash_bags"), (8.0, 9.4, 35.3, 35.95, 0.95, "trash_bags")):
        C("w46", name, x0, x1, z0, z1, h, y0=S, surface="cloth" if name == "trash_bags" else "wood")
    # ---------------------------------------------------------------- rooftop dressing (vents, ducts, pipes on sleepers, conduit boxes, dishes)
    roofs = {"A": (R3, [(-48.6, -48.0, -28.0, -27.4, 0.9, "roof_vent"), (-41.0, -40.4, -34.0, -33.4, 0.9, "roof_vent"),
                        (-32.6, -32.0, -24.0, -23.4, 0.9, "roof_vent"), (-46.0, -44.4, -21.0, -19.4, 1.1, "duct_box"),
                        (-33.0, -31.4, -20.6, -19.6, 0.7, "conduit_box"), (-48.8, -48.2, -16.0, -14.0, 1.5, "antenna_mast"),
                        (-42.0, -40.0, -14.4, -13.6, 0.35, "pipe_sleepers"), (-36.4, -35.2, -37.0, -36.4, 1.3, "satellite_dish")]),
             "B": (R2, [(-49.0, -48.4, -10.0, -9.4, 0.9, "roof_vent"), (-44.0, -43.4, -11.0, -10.4, 0.9, "roof_vent"),
                        (-33.6, -32.0, -6.0, -4.4, 1.1, "duct_box"), (-37.0, -35.6, 0.6, 1.4, 0.7, "conduit_box"),
                        (-44.6, -43.0, 6.4, 7.2, 0.35, "pipe_sleepers"), (-32.4, -31.8, 2.0, 2.6, 0.9, "roof_vent"),
                        (-40.6, -39.4, -11.4, -10.6, 1.3, "satellite_dish")]),
             "C": (R2, [(-26.8, -26.2, -36.4, -35.8, 0.9, "roof_vent"), (-13.6, -13.0, -36.0, -35.4, 0.9, "roof_vent"),
                        (-26.8, -25.2, -26.0, -24.4, 1.1, "duct_box"), (-14.0, -12.4, -20.0, -18.4, 1.1, "duct_box"),
                        (-26.4, -26.0, -16.0, -12.0, 0.7, "conduit_run"), (-20.0, -18.4, -8.2, -7.4, 0.35, "pipe_sleepers"),
                        (-11.4, -10.8, -9.0, -8.4, 0.9, "roof_vent"), (-24.0, -23.4, -30.0, -29.4, 0.9, "roof_vent")]),
             "D": (R1, [(-26.8, -26.2, 20.4, 21.0, 0.9, "roof_vent"), (-13.0, -12.4, 18.4, 19.0, 0.9, "roof_vent"),
                        (-17.4, -15.8, 4.6, 6.2, 1.1, "duct_box"), (-11.4, -10.6, 15.2, 16.4, 0.7, "conduit_box"),
                        (-23.0, -21.4, 13.6, 14.4, 0.35, "pipe_sleepers"), (-10.0, -9.4, -2.8, -2.2, 0.9, "roof_vent")]),
             "E": (R1, [(-49.0, -48.4, 18.0, 18.6, 0.9, "roof_vent"), (-36.4, -35.8, 20.4, 21.0, 0.9, "roof_vent"),
                        (-32.6, -31.0, 9.0, 10.6, 1.1, "duct_box"), (-46.0, -44.4, 19.0, 19.8, 0.35, "pipe_sleepers")])}
    for bid, (y, items) in roofs.items():
        for x0, x1, z0, z1, h, name in items:
            C("roof", name, x0, x1, z0, z1, h, y0=y, what="%s's roof" % bid)
    # the deck furniture (THE LOFTLARK's deck, E's platform): loungers, umbrellas folded, an old fan housing
    for x0, x1, z0, z1, h, name in ((-27.0, -25.6, -3.2, -2.2, 0.5, "lounger"), (-27.0, -25.6, -1.4, -0.4, 0.5, "lounger"),
                                    (-21.0, -20.6, 1.6, 2.6, 2.2, "umbrella_folded"), (-25.0, -24.6, 1.6, 2.6, 2.2, "umbrella_folded"),
                                    (-49.2, -47.6, 12.4, 14.0, 1.0, "fan_housing")):
        C("roof", name, x0, x1, z0, z1, h, y0=R1 + 0.6)
    # spare: the booth's dressing and the service stair's foot
    for x0, x1, z0, z1, h, name in ((10.7, 11.5, -33.9, -33.2, 1.6, "equipment_case"), (12.0, 13.2, -33.9, -33.4, 1.0, "monitor_cart"),
                                    (18.4, 19.2, -30.4, -29.6, 0.95, "cable_drum"), (-12.8, -12.0, 9.2, 9.9, 1.0, "mop_bucket")):
        C("spare", name, x0, x1, z0, z1, h, y0=S)

    named = {"planter_granite": "street", "kiosk_souvenir": "street", "food_cart": "street", "cafe_table": "street", "light_pole": "street",
             "street_lamp": "street", "trash_can": "street", "jersey_barrier": "barriers", "water_barrier": "barriers", "generator": "premiere",
             "hvac_rtu": "roof", "skylight": "roof", "chimney_stack": "roof", "tar_kettle": "roof", "vent_box": "roof", "lounge_bar": "roof",
             "lounger_stack": "roof", "planter_box": "roof"}
    groups = {}
    for p in L.props:
        g = p.get("group") or named.get(p["name"])
        if g:
            groups[g] = groups.get(g, 0) + len(p["colliders"])
    L.extra["colliderBudget"] = {"source": "midtown.md 15 (760, cap 820): the clutter groups this table authors, planned against placed "
                                           "(the premiere's structures, W 46 St and spare come out of the 167 contingency)",
                                 "plannedTotal": 760, "cap": 820, "clutterPlanned": PLAN, "clutterPlaced": groups,
                                 "skipped": L.clutter_skipped}
