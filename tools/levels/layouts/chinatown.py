"""Level 2, Canal Street (Chinatown, Manhattan, 7:40 PM, night, wet): the layout table.

Every number comes from docs/unreal/maps/chinatown.md revision 2 (sections 3 to 15 and Appendix A) unless a line says
`DEVIATION`; those are listed in meta.deviationsFromDesign with the reason. Signs are English only (the owner,
DECISIONS 2026-11-26 ~02:00): Chinatown reads through the architecture, the lanterns, the market, the produce, the
awnings, the sign style and the English shop names. Every name is invented; IPX is the only real mark.
"""

from levelkit import Level, rect

ID = "chinatown"
ROOF = 5.7
SW = 0.15  # sidewalk / interior slab height


def build():
    L = Level(ID, "Canal Street", rect(-44, 44, -34, 32), 2112,
              "Level 2, Canal Street: Canal St and Mott St, Chinatown, Manhattan, 7:40 PM, night, the street wet after rain. "
              "Bounds, zones, every collider, the points the game flow and the AI use, the nav layers and the art-side "
              "placements, written by the shared layout tool from the hand-authored table.")
    L.notes = [
        "el: absent. The design has no elevated train here (chinatown.md 8.5); the loader must treat a missing `el` as no "
        "deck (MAPS.md E2). Until E2 lands, `build_level.py --el-fallback` writes a degenerate deck 250 m outside the "
        "bounds so today's loader can read the file (every deck test is a point-in-rectangle check, so it never applies).",
        "nav: the layers, links and spawn reach are written; the grids are not. The engine bake (-run=MILevelBake) writes "
        "`nav.layers[*].grid` with FMIBoxWorld's own code.",
        "Roof spawns rf1 to rf3 carry enabled:false until nav step A exists (chinatown.md 4.4); the release ships with "
        "them on.",
        "Signs and screens: English only, invented names (owner's answer 2026-11-26).",
    ]
    L.deviations = ["air point over the yard at (-13, 8.5, 9.4) instead of (-13, 8.5, 8): at z 8 it was 0.75 m from the yard "
                    "stair's guard between the flights (rule: 1.5 m from any collider)."]

    # ------------------------------------------------------------------ zones and places
    L.zone("canal", "CANAL ST", rect(-44, 44, -34, -14))
    L.zone("alley", "LANTERN ALLEY", rect(-44, -26, -14, 32))
    L.zone("market", "THE MARKET", rect(-26, 8, -14, 32))
    L.zone("mott", "MOTT ST", rect(8, 44, -14, 32))
    L.region("CANAL ST", "canal", rect(-44, 44, -34, -14))
    L.region("LANTERN ALLEY", "alley", rect(-44, -26, -14, 32))
    L.region("LANTERN ALLEY", "market", rect(-26, 8, 10, 14))
    L.region("THE MARKET", "market", rect(-26, 0, -14, 10))
    L.region("THE BAKERY", "market", rect(0, 8, -14, 10))
    L.region("THE BACKS", "market", rect(-26, 8, 14, 32))
    L.region("MOTT ST", "mott", rect(8, 18, -14, 32))
    L.region("THE ARCADE", "mott", rect(18, 44, -14, 2))
    L.region("THE SQUARE", "mott", rect(18, 44, 2, 18))
    L.region("THE DUB ROOM", "mott", rect(18, 26.3, 18, 32))
    L.region("THE BANQUET HALL", "mott", rect(26.3, 44, 18, 32))
    L.deviations.append("places.regions: THE DUB ROOM (x 18..26.3, z 18..32) added before THE BANQUET HALL so the HUD names "
                        "the reel's room as its objective place does (15 lists only THE BANQUET HALL for E2).")

    # ------------------------------------------------------------------ ground slabs (0.15) and raised floors
    def slab(tag, x0, x1, z0, z1, top=SW, surface="concrete", part=None, y0=0.0):
        return L.box(tag, x0, x1, y0, top, z0, z1, surface=surface, part=part)

    slab("sidewalk", -44, 44, -34, -29.8, part="canal.sidewalk.north")
    slab("sidewalk", -44, 10, -19, -14, part="canal.sidewalk.south.west")
    slab("sidewalk", 16, 44, -19, -14, part="canal.sidewalk.south.east")
    slab("sidewalk", 8, 10, -14, 32, part="mott.sidewalk.west")
    slab("sidewalk", 16, 18, -14, 32, part="mott.sidewalk.east")
    slab("square", 18, 44, 2, 18, part="square.paving")
    slab("floor", 0, 8, -14, 10, part="bakery.floor")
    slab("floor", 29.4, 33.6, -14, 2, part="arcade.floor", surface="concrete")
    slab("floor", 34, 37.6, -10, -4, part="workshop.floor", surface="metal")
    slab("floor", 18, 44, 18, 32, part="e2.floor", surface="cloth")
    L.box("stage", 40.8, 43.6, SW, 0.55, 18.8, 26.6, surface="wood", part="banquet.stage")
    L.box("plinth", 27.5, 34.5, SW, 0.45, 6.5, 13.5, surface="concrete", part="square.pavilion.plinth")

    # ------------------------------------------------------------------ north row N1..N6 (alcoves 2.4 x 1.0)
    north = [("N1", -44, -29, 20.2, -35), ("N2", -29, -15, 17.1, -22), ("N3", -15, -1, 17.1, -8),
             ("N4", -1, 13, 20.2, 5), ("N5", 13, 26, 17.1, 20), ("N6", 26, 44, 23.3, 31)]
    for bid, xa, xb, top, ac in north:
        cols = [L.box(bid, xa, xb, 0, top, -36, -34, surface="brick", part=bid + ".mass")]
        cols += [L.box(bid, xa, ac - 1.2, 0, top, -34, -33, surface="brick", part=bid + ".front"),
                 L.box(bid, ac + 1.2, xb, 0, top, -34, -33, surface="brick", part=bid + ".front"),
                 L.box(bid, ac - 1.2, ac + 1.2, 3.0, top, -34, -33, surface="brick", part=bid + ".alcove.lintel")]
        L.buildings.append({"id": bid, "colliders": cols, "web": {"minX": xa, "maxX": xb, "minZ": -36, "maxZ": -33,
                                                                   "roof": round(top - 0.9, 2), "parapetTop": top}})

    # ------------------------------------------------------------------ W1 and the south row
    w1 = L.box("W1", -44, -30, 0, 20.2, -14, 32, surface="brick", part="W1.mass")
    L.buildings.append({"id": "W1", "colliders": [w1], "web": {"minX": -44, "maxX": -30, "minZ": -14, "maxZ": 32, "roof": 19.3, "parapetTop": 20.2}})
    for bid, xa, xb, top in (("S1", -30, -14, 17.1), ("S2", -14, 0, 17.1), ("S3", 0, 8, 20.2)):
        c = L.box(bid, xa, xb, 0, top, 14, 32, surface="brick", part=bid + ".mass")
        L.buildings.append({"id": bid, "colliders": [c], "web": {"minX": xa, "maxX": xb, "minZ": 14, "maxZ": 32, "roof": round(top - 0.9, 2), "parapetTop": top}})

    # ------------------------------------------------------------------ the market hall M and B0
    mcols = []
    mcols += L.wall_x("market", -26, 0, -14, -13.6, 0, 5.4, openings=[(-22, -18, 3.4), (-15, -11, 3.4), (-8, -4, 3.4)],
                      surface="concrete", part="market.wall.north")
    # DEVIATION: side door at z -2.7..-1.3 (design -2.9..-1.5): same 1.4 m, shifted 0.2 m so no nav cell centre falls in
    # the 0.4 m band the 0.5 m inflate leaves; at the design position one cell column stayed free and Goons could use
    # the "player only" door.
    L.deviations.append("market side door at z -2.7..-1.3 instead of -2.9..-1.5 (same 1.4 m): at the design position one nav "
                        "column stayed free (0.5 m cells, 0.5 m inflate), so the player-only door was a Goon door.")
    mcols += L.wall_z("market", -26, -25.6, -13.6, 5.6, 0, 5.4, openings=[(-2.7, -1.3, 2.2)], surface="concrete", part="market.wall.west")
    mcols += L.wall_x("market", -26, 0, 5.6, 6.0, 0, 5.4, openings=[(-7, -3, 3.4)], surface="concrete", part="market.wall.south")
    mcols.append(L.box("market", -0.4, 0.4, 0, 5.4, -14, 6, surface="brick", part="market.wall.party"))
    mcols.append(L.box("market-roof", -26, 0, 5.4, ROOF, -14, 6, surface="asphalt", part="market.roof.slab"))
    b0 = L.box("B0", -26, -16, 0, ROOF, 6, 10, surface="brick", part="B0.mass")
    L.buildings.append({"id": "M", "colliders": mcols, "web": {"minX": -26, "maxX": 0, "minZ": -14, "maxZ": 6, "roof": ROOF, "parapetTop": 6.8}})
    L.buildings.append({"id": "B0", "colliders": [b0], "web": {"minX": -26, "maxX": -16, "minZ": 6, "maxZ": 10, "roof": ROOF, "parapetTop": 6.7}})

    # roof parapets (1.1 on Canal, 1.0 elsewhere), the stair-head gap x -9.8..-8.6
    L.box("parapet", -26, 0, ROOF, 6.8, -14, -13.7, surface="concrete", part="market.parapet.canal")
    L.box("parapet", -26, -25.7, ROOF, 6.7, -13.7, 10, surface="concrete", part="market.parapet.west")
    L.box("parapet", -16, -9.8, ROOF, 6.7, 5.7, 6.0, surface="concrete", part="market.parapet.yard")
    L.box("parapet", -8.6, 0, ROOF, 6.7, 5.7, 6.0, surface="concrete", part="market.parapet.yard")
    L.box("parapet", -25.7, -16, ROOF, 6.7, 9.7, 10, surface="concrete", part="B0.parapet.alley")
    L.box("parapet", -16.3, -16, ROOF, 6.7, 6.0, 9.7, surface="concrete", part="B0.parapet.yard")
    # edge guards: playerOnly on the parapets' outer faces, roof to roof + 3.0 (shots and sight pass)
    G1 = ROOF + 3.0
    L.guard("roof-guard", -26, 0, ROOF, G1, -14.1, -14.0, part="market.guard.canal")
    L.guard("roof-guard", -26.1, -26.0, ROOF, G1, -14.1, 10.1, part="market.guard.alleyA")
    L.guard("roof-guard", -26.1, -16, ROOF, G1, 10.0, 10.1, part="B0.guard.alleyB")
    L.guard("roof-guard", -16.0, -15.9, ROOF, G1, 6.0, 10.1, part="B0.guard.yard")
    L.guard("roof-guard", -15.9, -14.6, ROOF, G1, 6.0, 6.1, part="market.guard.yard")
    L.guard("roof-guard", -8.5, 0, ROOF, G1, 6.0, 6.1, part="market.guard.yard")

    # market interior: stall rows (double counters 1.8 m, 0.95 tall), fish counters, cold room, pallets
    for xa, xb, row in ((-21.6, -19.8, "R1"), (-16.4, -14.6, "R2"), (-11.2, -9.4, "R3"), (-6.0, -4.2, "R4")):
        L.prop("stall_counter", [(xa, xb, 0, 0.95, -11, -5, "wood")], extra={"row": row, "run": "front"})
        L.prop("stall_counter", [(xa, xb, 0, 0.95, -3, -0.5, "wood")], extra={"row": row, "run": "back"})
    L.prop("fish_counter", [(-1.4, -0.4, 0, 0.95, -10, -1, "metal")])
    L.wall_x("cold-room", -25.6, -18.4, 1.5, 1.75, 0, 3.0, openings=[(-21, -19, 2.4)], surface="metal", part="coldroom.wall.north")
    L.box("cold-room", -18.65, -18.4, 0, 3.0, 1.75, 5.6, surface="metal", part="coldroom.wall.east")
    L.box("cold-room", -25.6, -18.4, 3.0, 3.2, 1.5, 5.6, surface="metal", part="coldroom.lid")
    for xa, xb in ((-15, -13.4), (-12.6, -11), (-10.2, -9.4)):
        L.prop("pallet_stack", [(xa, xb, 0, 1.2, 2.4, 5.2, "wood")])

    # roof furniture: skylights 2 x 3 x 0.8, condensers 1.2, the rooftop letters' legs, the B0 bulkhead
    for xa, za in ((-20.5, -10), (-13.5, -10), (-20.5, -2), (-7.5, -2)):
        L.prop("skylight", [(xa, xa + 2, ROOF, ROOF + 0.8, za, za + 3, "glass")])
    for xa, xb, za, zb in ((-23.0, -21.8, -5.8, -4.2), (-4.0, -2.8, -7.0, -5.6), (-15.0, -13.8, 2.5, 3.7)):
        L.prop("condenser", [(xa, xb, ROOF, ROOF + 1.2, za, zb, "metal")])
    for x in (-22, -15, -8.5, -2):
        L.box("rooftop-letters", x - 0.15, x + 0.15, ROOF, 9.0, -13.7, -13.4, surface="metal", part="market.letters.leg")
    L.box("bulkhead", -25.4, -22.4, ROOF, 8.3, 6.6, 9.4, surface="brick", part="B0.bulkhead")

    # ------------------------------------------------------------------ the yard stair (the one climbable fire escape)
    rise, tread = 0.219, 0.26
    for k in range(1, 14):  # flight 1, south lane, foot at x -9.8 going west
        L.box("yard-stair", -9.8 - tread * k, -9.8 - tread * (k - 1), 0, round(rise * k, 4), 7.2, 8.2, surface="metal", part="stair.flight1.%d" % k)
    L.box("yard-stair", -14.6, -9.8 - tread * 13, 0, 2.85, 6.0, 8.2, surface="metal", part="stair.landing.mid")
    x13 = -9.8 - tread * 13
    for k in range(1, 14):  # flight 2, north lane, going east up to the roof
        L.box("yard-stair", x13 + tread * (k - 1), x13 + tread * k, 0, round(2.85 + rise * k, 4), 6.0, 7.2, surface="metal", part="stair.flight2.%d" % k)
    L.box("yard-stair", -9.8, -8.6, 0, ROOF, 6.0, 7.2, surface="metal", part="stair.landing.top")
    L.guard("stair-guard", -14.6, -9.8, 0, 2.85 + 3.0, 8.2, 8.3, part="stair.guard.south")
    L.guard("stair-guard", x13, -8.6, 0, ROOF + 3.0, 7.15, 7.25, part="stair.guard.between")
    L.guard("stair-guard", -14.7, -14.6, 2.85, 2.85 + 3.0, 6.0, 8.3, part="stair.guard.landing")
    L.guard("stair-guard", -8.6, -8.5, ROOF, ROOF + 3.0, 6.0, 7.25, part="stair.guard.head")

    # ------------------------------------------------------------------ W3: the bakery (front shop, kitchen, kitchen roof)
    w3 = [L.box("W3", 0, 8, 3.8, 17.1, -14, -3, surface="brick", part="W3.upper")]
    w3 += L.wall_x("bakery", 0.4, 7.6, -14, -13.6, 0, 3.8, openings=[(2, 4, 2.6)], surface="brick", part="bakery.wall.canal")
    w3.append(L.box("bakery", 7.6, 8, 0, 3.8, -14, -3, surface="brick", part="bakery.wall.mott.front"))
    w3 += L.wall_x("bakery", 0.4, 7.6, -3.2, -3.0, 0, 3.8, openings=[(3, 5, 2.6)], surface="brick", part="bakery.partition")
    w3 += L.wall_z("bakery", 7.6, 8, -3, 10, 0, 5.4, openings=[(2, 4, 2.6)], surface="brick", part="bakery.wall.mott.kitchen")
    w3 += L.wall_x("bakery", 0.4, 7.6, 9.6, 10, 0, 5.4, openings=[(4, 6, 2.6)], surface="brick", part="bakery.wall.alley")
    w3.append(L.box("bakery", 0, 0.4, 0, 5.4, 6, 10, surface="brick", part="bakery.wall.yard"))
    w3.append(L.box("kitchen-roof", 0, 8, 5.4, ROOF, -3, 10, surface="asphalt", part="kitchen.roof.slab"))
    L.buildings.append({"id": "W3", "colliders": w3, "web": {"minX": 0, "maxX": 8, "minZ": -14, "maxZ": 10, "roof": 16.2, "parapetTop": 17.1, "rearRoof": ROOF}})
    L.prop("bakery_counter", [(0.4, 5, SW, 1.15, -8, -7, "wood")])
    L.prop("kitchen_table", [(3.6, 5, SW, 1.05, 4.6, 8.4, "metal")])
    L.prop("bakery_ovens", [(6.4, 7.6, SW, 1.9, -2.4, 0.8, "metal")])
    L.prop("tray_racks", [(0.4, 1.2, SW, 1.9, 0, 3.2, "metal")])
    # kitchen roof: curb to the market roof, parapets with the broken Mott section (z 2..5), guards
    L.box("roof-curb", -0.15, 0.15, ROOF, 6.0, -3, 6, surface="concrete", part="kitchen.curb")
    L.box("parapet", 7.7, 8, ROOF, 6.7, -3, 2, surface="brick", part="kitchen.parapet.mott")
    L.box("parapet", 7.7, 8, ROOF, 6.7, 5, 10, surface="brick", part="kitchen.parapet.mott")
    L.box("parapet", 0, 7.7, ROOF, 6.7, 9.7, 10, surface="brick", part="kitchen.parapet.alley")
    L.box("parapet", 0, 0.3, ROOF, 6.7, 6, 9.7, surface="brick", part="kitchen.parapet.yard")
    L.guard("roof-guard", -0.1, 0, ROOF, G1, 6.0, 10.1, part="kitchen.guard.yard")
    L.guard("roof-guard", 0, 8.1, ROOF, G1, 10.0, 10.1, part="kitchen.guard.alley")
    L.guard("roof-guard", 8.0, 8.1, ROOF, G1, -3, 2, part="kitchen.guard.mott")
    L.guard("roof-guard", 8.0, 8.1, ROOF, G1, 5, 10, part="kitchen.guard.mott")

    # sidewalk shed on the bakery's Mott face: deck top 3.2, posts on the kerb line, plywood parapet with a missing panel
    L.box("shed-deck", 8, 10, 3.0, 3.2, -3, 10, surface="wood", no_nav=True, part="mottshed.deck")
    L.box("shed-parapet", 9.9, 10, 3.2, 4.2, -3, 2, surface="wood", part="mottshed.parapet")
    L.box("shed-parapet", 9.9, 10, 3.2, 4.2, 5, 10, surface="wood", part="mottshed.parapet")
    L.guard("shed-guard", 10, 10.1, 3.2, 6.2, -3.1, 2, part="mottshed.guard")
    L.guard("shed-guard", 10, 10.1, 3.2, 6.2, 5, 10.1, part="mottshed.guard")
    L.guard("shed-guard", 8, 10, 3.2, 6.2, -3.1, -3.0, part="mottshed.guard.north")
    L.guard("shed-guard", 8.1, 10, 3.2, 6.2, 10.0, 10.1, part="mottshed.guard.south")
    for z in (-2.9, 0.1, 5.1, 8.1, 9.85):
        L.box("shed-post", 9.7, 9.9, SW, 3.0, z - 0.1, z + 0.1, surface="metal", part="mottshed.post")

    # ------------------------------------------------------------------ alleys and the yard
    L.prop("dumpster", [(-29.9, -28.3, 0, 1.3, -9, -7.2, "metal")])
    L.prop("crate_stack", [(-27.6, -26.0, 0, 1.0, 4, 5.4, "wood")], extra={"what": "the party-goods wholesaler's cartons on a hand truck"})
    L.prop("dumpster", [(-24, -22.2, 0, 1.3, 12.2, 14, "metal")])
    L.prop("pallet_stack", [(-12, -10.2, 0, 1.2, 10, 11.4, "wood")])
    L.prop("dumpster", [(2, 3.8, 0, 1.3, 12.2, 14, "metal")])
    L.prop("dumpster", [(-1.9, -0.4, 0, 1.3, 6.3, 8.1, "metal")])

    # ------------------------------------------------------------------ Mott St
    L.vehicle("sedan", 10.1, 12.1, -8, -3.5, forward=-1)
    L.vehicle("van", 10.1, 12.2, 3, 8.5, forward=-1)
    L.vehicle("taxi", 10.1, 12.1, 18, 22.5, forward=-1)
    L.vehicle("box_truck", 9.6, 17.6, 27.2, 29.8, forward=1)
    L.prop("ebike", [(9.35, 9.95, SW, 1.0, 6.4, 8.0, "metal")], extra={"what": "two delivery e-bikes chained to a shed post, no brand"})
    L.prop("fruit_crates", [(8.2, 9.1, SW, 0.9, 16.0, 19.0, "wood")], extra={"what": "GOOD WISHES GROCERY's fruit boxes"})
    L.prop("fruit_stand", [(8.2, 9.0, SW, 1.0, 8.6, 9.6, "wood")], extra={"what": "fruit stand under the shed's south end"})

    # ------------------------------------------------------------------ E1a, the arcade, E1b and the neon workshop
    e1a = L.box("E1a", 18, 29.4, 0, 17.1, -14, 2, surface="brick", part="E1a.mass")
    arc = L.box("arcade", 29.4, 33.6, 4.2, 17.1, -14, 2, surface="concrete", part="arcade.ceiling")
    L.buildings.append({"id": "E1a", "colliders": [e1a], "web": {"minX": 18, "maxX": 29.4, "minZ": -14, "maxZ": 2, "roof": 16.2, "parapetTop": 17.1}})
    L.buildings.append({"id": "Arcade", "colliders": [arc], "web": {"minX": 29.4, "maxX": 33.6, "minZ": -14, "maxZ": 2, "ceiling": 4.2}})
    e1b = [L.box("E1b", 33.6, 44, 0, 20.2, -14, -10, surface="brick", part="E1b.mass"),
           L.box("E1b", 33.6, 44, 0, 20.2, -4, 2, surface="brick", part="E1b.mass"),
           L.box("E1b", 37.6, 44, 0, 20.2, -10, -4, surface="brick", part="E1b.mass")]
    e1b += L.wall_z("E1b", 33.6, 34.0, -10, -4, 0, 20.2, openings=[(-8, -6, 2.4)], surface="brick", part="workshop.wall.arcade")
    e1b.append(L.box("E1b", 34.0, 37.6, 3.8, 20.2, -10, -4, surface="brick", part="workshop.ceiling"))
    L.buildings.append({"id": "E1b", "colliders": e1b, "web": {"minX": 33.6, "maxX": 44, "minZ": -14, "maxZ": 2, "roof": 19.3, "parapetTop": 20.2}})
    L.prop("arcade_pillar", [(31.0, 31.6, SW, 4.2, -9.5, -8.9, "concrete")])
    L.prop("kiosk_counter", [(32.6, 33.6, SW, 1.1, -13.4, -12.4, "glass")], extra={"what": "the sign-repair kiosk (NEON SIGNS)"})
    L.prop("tube_bundles", [(34.2, 35.0, SW, 1.0, -9.8, -9.0, "glass")])
    L.prop("bending_bench", [(35.4, 37.4, SW, 0.95, -5.0, -4.2, "metal")])

    # ------------------------------------------------------------------ the Square (a worn neighbourhood park)
    for cx, cz in ((28.2, 7.2), (33.8, 7.2), (28.2, 12.8), (33.8, 12.8)):
        L.box("pavilion", cx - 0.2, cx + 0.2, 0.45, 3.6, cz - 0.2, cz + 0.2, surface="wood", part="pavilion.column")
    L.box("pavilion", 27.5, 34.5, 3.6, 4.4, 6.5, 13.5, surface="wood", part="pavilion.roof")
    for xa, za in ((20, 4), (39, 4), (20, 15), (39, 15)):
        L.prop("raised_bed", [(xa, xa + 3, SW, 1.05, za, za + 1, "concrete")], extra={"what": "concrete bed edged with chain-link"})
    L.prop("park_bench", [(23, 23.8, SW, 0.95, 9, 11, "wood")])
    L.prop("park_bench", [(38, 38.8, SW, 0.95, 9, 11, "wood")])
    L.prop("card_table", [(24.4, 25.4, SW, 0.9, 13.0, 14.0, "wood")], extra={"what": "folding card table and stools"})
    L.prop("card_table", [(36.6, 37.6, SW, 0.9, 3.6, 4.6, "wood")], extra={"what": "folding card table, a xiangqi board"})
    L.prop("hotpot_cart", [(20.6, 21.5, SW, 1.1, 9.4, 10.6, "metal")])
    L.prop("stone_lion", [(29.1, 29.9, SW, 1.25, 16.4, 17.2, "concrete")], extra={"what": "small generic restaurant-door lion"})
    L.prop("stone_lion", [(36.1, 36.9, SW, 1.25, 16.4, 17.2, "concrete")], extra={"what": "small generic restaurant-door lion (mirrored)"})
    L.prop("basketball_hoop", [(40.6, 40.9, SW, 3.5, 16.0, 16.3, "metal")])
    for cx, cz in ((19.0, 2.8), (19.0, 17.3), (43.2, 2.8)):
        L.simple("trash_can", cx, cz, 0.58, 0.58, 0.95, y0=SW)

    # ------------------------------------------------------------------ E2: the banquet hall and the dub room
    e2 = [L.box("E2", 26.3, 44, 5.0, 10.9, 18, 32, surface="concrete", part="E2.upper"),
          L.box("E2", 18, 26.3, 4.2, 10.9, 18, 32, surface="concrete", part="E2.upper")]
    e2 += L.wall_x("E2", 18, 44, 18, 18.4, 0, 5.0, openings=[(31, 35, 3.8)], surface="concrete", part="banquet.wall.square")
    e2 += L.wall_z("E2", 18, 18.4, 18.4, 32, 0, 4.2, openings=[(24, 27, 3.4)], surface="concrete", part="dub.wall.mott")
    e2 += L.wall_z("E2", 26, 26.3, 18.4, 32, 0, 5.0, openings=[(26, 28, 2.4)], surface="concrete", part="e2.partition")
    e2.append(L.box("E2", 43.6, 44, 0, 5.0, 18.4, 32, surface="concrete", part="banquet.wall.east"))
    e2.append(L.box("E2", 18.4, 43.6, 0, 5.0, 31.6, 32, surface="concrete", part="e2.wall.south"))
    e2 += L.wall_x("E2", 36.4, 43.6, 27.0, 27.2, 0, 5.0, openings=[(38, 40, 2.4)], surface="concrete", part="banquet.kitchen.wall")
    e2.append(L.box("E2", 36.2, 36.4, 0, 5.0, 27.0, 31.6, surface="concrete", part="banquet.kitchen.wall"))
    L.buildings.append({"id": "E2", "colliders": e2, "web": {"minX": 18, "maxX": 44, "minZ": 18, "maxZ": 32, "roof": 10.0, "parapetTop": 10.9}})
    for cx, cz in ((29.5, 21.5), (33.5, 21.5), (29.5, 25), (33.5, 25), (37.5, 21.5), (29.5, 28.8), (33.5, 28.8)):
        L.simple("banquet_table", cx, cz, 1.7, 1.7, 0.8, y0=SW, surface="cloth")
    L.prop("kitchen_range", [(37, 40, SW, 1.0, 30.8, 31.6, "metal")])
    L.prop("kitchen_counter", [(42.8, 43.6, SW, 1.0, 27.6, 29.6, "metal")])
    L.prop("tape_racks", [(18.4, 19.4, SW, 2.15, 28, 31.4, "metal")], extra={"what": "reel-to-reel and tape-deck racks"})
    L.prop("cutting_table", [(22.2, 23.8, SW, 1.05, 20.4, 22.4, "wood")])
    L.prop("disc_burners", [(24.6, 25.4, SW, 1.8, 18.6, 19.4, "metal")], extra={"what": "towers of disc burners"})

    # ------------------------------------------------------------------ Canal St: tables, cars, trucks, the ends
    table_x = [-38, -34, -30, -26, -22, -18, -14, -10, -6, 2, 6]
    racks = {-38, -30, -22, -14, -6, 6}
    for x in table_x:
        bx = [(x, x + 1.8, SW, 0.9, -18.8, -17.8, "cloth")]
        if x in racks:
            bx.append((x, x + 1.8, 0.9, 1.45, -18.3, -17.8, "cloth"))
        L.prop("vendor_table", bx, extra={"goods": "rack" if x in racks else "table", "what": "the disc and USB-stick table" if x == -10 else "vendor table"})
    L.vehicle("sedan", -36, -31.5, -29.8, -27.9)
    L.vehicle("taxi", -20, -15.5, -29.8, -27.9)
    L.vehicle("sedan", -4, 0.5, -29.8, -27.9)
    L.vehicle("suv", 34, 38.5, -29.8, -27.9)
    L.vehicle("sedan", -38, -33.5, -21.2, -19.1)
    L.vehicle("van", 20, 25.5, -21.2, -19.1)
    L.vehicle("box_truck", -14, -6, -21.4, -18.9)
    L.vehicle("box_truck", 20, 28, -27.6, -25.0)
    # the IPX truck: the Block's AMITruck collider profile relative to its pos (cargo pos-3.4..pos+0.55, cab ..pos+3.4)
    tx, tz = 37.5, -23.0
    ipx = L.prop("ipx_truck", [(tx - 3.4, tx + 0.55, 0, 2.86, tz - 1.17, tz + 1.17, "car"),
                               (tx + 0.55, tx + 3.4, 0, 2.58, tz - 1.17, tz + 1.17, "car")], pos=(tx, 0, tz))
    L.prop("delivery_truck", [(41.6, 44.0, 0, 3.3, -27.0, -20.0, "car")], extra={"what": "stalled delivery truck across the IPX truck's nose"})
    L.prop("jersey_barrier", [(42.6, 43.4, 0, 0.81, -29.8, -27.1, "concrete")])
    L.prop("jersey_barrier", [(42.6, 43.4, 0, 0.81, -19.9, -19.0, "concrete")])
    L.prop("jersey_barrier", [(-43.6, -42.8, 0, 0.81, -29.8, -19.2, "concrete")], extra={"what": "barriers across the street dig"})
    L.prop("box_truck", [(-47.2, -44.4, 0, 3.3, -27.5, -20.5, "car")], extra={"what": "parked box truck past the dig (outside the bounds, blocks sight)"})
    # street furniture
    for x in (-31.1, -7.1, 18.0, 38.0):
        L.simple("street_lamp", x, -18.82, 0.26, 0.26, 7.3, y0=SW)
    for x in (-18.0, 8.0):
        L.simple("street_lamp", x, -29.92, 0.26, 0.26, 7.3, y0=SW)
    for x, z in ((16.23, -4.0), (9.77, 20.0), (16.23, 10.0)):
        L.simple("street_lamp", x, z, 0.26, 0.26, 7.3, y0=SW)
    for x in (0.2, 3.2, 6.2, 9.2, 11.8):
        L.box("shed-post", x - 0.1, x + 0.1, SW, 3.4, -30.05, -29.85, surface="metal", part="canalshed.post")
    for x, z in ((-26.0, -30.3), (14.5, -30.3), (16.6, 15.0)):
        L.simple("hydrant", x, z, 0.32, 0.32, 0.74, y0=SW)
    for x in (-28.0, -13.0, 11.0, 24.0 + 1.6):
        L.simple("newspaper_box", x, -32.4, 0.48, 0.42, 1.08, y0=SW)
    for x, z in ((-41.0, -14.6), (-24.6, -14.6), (20.0, -14.6), (27.5, -14.6)):
        L.simple("trash_can", x, z, 0.58, 0.58, 0.95, y0=SW)
    for x, z in ((16.9, -10.0), (8.6, 12.6), (-40.0, -30.4)):
        L.simple("trash_bags", x, z, 0.9, 0.6, 0.62, y0=SW if x > 0 or z < -29.8 else 0.0, surface="cloth")
    L.prop("food_cart", [(-34.2, -32.8, SW, 1.4, -15.2, -14.2, "metal")], extra={"what": "dumpling cart"})
    L.prop("food_cart", [(-18.0, -17.0, SW, 1.4, -15.6, -14.2, "metal")], extra={"what": "fried-snack stall"})
    L.prop("food_cart", [(4.8, 6.3, SW, 1.4, -15.1, -14.2, "metal")], extra={"what": "roasted-nut cart"})

    # ------------------------------------------------------------------ explosives (18; section 9, in level order)
    E = L.explosive
    E("propane", -32.6, SW, -14.6, note="dumpling cart outside W1")
    E("propane", -16.6, SW, -14.6, note="fried-snack stall at the market pier, a pair with 2")
    E("propane", -16.6, SW, -15.45, note="as 1")
    E("propane", -3.0, SW, -32.6, note="EIGHT TREASURE BBQ kitchen tanks, a pair with 4")
    E("propane", -2.15, SW, -32.6, note="as 3")
    E("propane", 24.0, SW, -32.6, note="LONG LIFE NOODLE HOUSE")
    E("propane", 6.6, SW, -14.6, note="bakery front, roasted-nut cart")
    E("propane", -13.0, 0, 4.9, note="stockroom, between pallets")
    E("propane", -0.9, 0, -11.2, note="fish-counter boiler, NE corner")
    E("propane", -8.6, 0, 9.3, note="yard gas cage, a pair with 10")
    E("propane", -7.75, 0, 9.3, note="as 9")
    E("propane", -26.5, 0, 8.0, note="alley A, a restaurant's back door at B0")
    E("rack", -17.0, 0, 13.4, note="alley B, a sign hanger's torch rack against S1")
    E("propane", 9.0, SW, -1.0, note="bakery kitchen's Mott door")
    E("rack", 37.0, SW, -8.4, rotation_y=1.5708, note="the neon workshop's torch rack")
    E("rack", 33.0, SW, -12.0, note="arcade, the sign-repair kiosk (the arcade narrows to 3.2 m here)")
    E("propane", 21.8, SW, 10.0, note="the Square, hot-pot cart by the card tables")
    E("propane", 41.8, SW, 30.8, note="banquet kitchen")

    # ------------------------------------------------------------------ interiors and doorways (section 15)
    L.interior("market", -25.6, 0, -13.6, -0.4, 5.4, 5.6, reel="reel5")
    L.interior("bakery front", 0.4, 0, -13.6, 7.6, 3.8, -3.2)
    L.interior("bakery kitchen", 0.4, 0, -3.0, 7.6, 5.4, 9.6)
    L.interior("arcade", 29.4, 0, -14, 33.6, 4.2, 2)
    L.interior("workshop", 34.0, 0, -10, 37.6, 3.8, -4)
    L.interior("banquet", 26.3, 0, 18.4, 43.6, 5.0, 31.6)
    L.interior("dub room", 18.4, 0, 18.4, 26.0, 4.2, 31.6, reel="reel6")
    for x in (-20, -13, -6):
        L.doorway("market gate", (x, 2.6, -16.5), (x, 2.6, -11.8))
    L.doorway("market rear", (-5, 2.6, 8.6), (-5, 2.6, 3.6))
    L.doorway("arcade north", (31.5, 2.6, -16.5), (31.5, 2.6, -11))
    L.doorway("arcade south", (31.5, 2.6, 4.5), (31.5, 2.6, -1))
    L.doorway("banquet doors", (33, 2.5, 15.5), (33, 2.5, 20.0))
    L.doorway("dub room roll-up", (15.5, 2.4, 25.5), (21.0, 2.4, 25.5))

    # ------------------------------------------------------------------ the player, the reels, the truck
    L.player_start = {"source": "chinatown.md 5: in the Canal roadway beside the livery sedan, just inside the west dig, facing east",
                      "pos": (-40.0, 0.0, -24.5), "facing": (1.0, 0.0), "layer": "street"}
    L.objective("reel4", "4", "Reel 4 — The Tables", "THE TABLES", "canal", (-10.0, SW, -16.2), 1.5708, False,
                note="on the sidewalk between the bootleg disc table and the market front, behind the south-lane box truck")
    L.objective("reel5", "5", "Reel 5 — The Market", "THE MARKET", "market", (-22.5, 0.0, 4.4), 1.5708, True,
                note="in the cold room at the back of the market, on a pallet among the fish boxes")
    L.objective("reel6", "6", "Reel 6 — The Dub Room", "THE DUB ROOM", "mott", (21.2, SW, 28.4), 1.5708, True,
                note="in the copying room, by the racks, cabled to a deck mid-transfer")
    L.extraction = {"source": "chinatown.md 6: the zone behind the truck's rear doors (truck - 5.4 m x forward, as on the Block); "
                              "the truck idles boxed in from the start, hazards on until all three reels are in",
                    "zone": "canal", "place": "CANAL ST", "pos": (32.1, 0.0, -23.0), "radius": 2.5,
                    "truck": {"pos": (37.5, 0.0, -23.0), "rotationY": 0.0, "prop": ipx, "colliders": L.props[ipx]["colliders"]}}

    # ------------------------------------------------------------------ enemy spawns (38 ground, 18 air)
    g = L.ground
    for n, x, z in (("c1", -41.5, -27.0), ("c2", -35, -33.3), ("c3", -22, -33.3), ("c4", -8, -33.3), ("c5", 5, -33.3),
                    ("c6", 20, -33.3), ("c7", 31, -33.3), ("c8", 42.0, -31.5)):
        g(n, x, 0.0 if n == "c1" else SW, z)
    g("c9", 42.0, SW, -16.0); g("c10", 24, SW, -15.0); g("c11", -36, SW, -15.0); g("c12", 24.0, 0.0, -28.6)
    for n, x, z in (("a1", -28, -12), ("a2", -28, -4), ("a3", -28, 7), ("a4", -28, 12.5), ("a5", -19, 12)):
        g(n, x, 0.0, z)
    for n, x, y, z in (("m1", -24.2, 0, -12.4), ("m2", -2.6, 0, -12.4), ("m3", -23.6, 0, 0.4), ("m4", -6.5, 0, 4.2),
                       ("m5", -13, 0, 9.2), ("m6", -4.5, 0, 8.6), ("m7", 2.0, SW, 7.0), ("m8", -6, 0, 12), ("m9", 5.5, 0, 12.4)):
        g(n, x, y, z)
    for n, x, y, z in (("t1", 9.0, SW, -6), ("t2", 17.0, SW, -4), ("t3", 13, 0, 30.8), ("t4", 9.0, SW, 22),
                       ("t5", 31.5, SW, -1.0), ("t6", 21.5, SW, 16.6), ("t7", 42.6, SW, 4.0), ("t8", 40.0, SW, 29.5),
                       ("t9", 24.8, SW, 30.4)):
        g(n, x, y, z)
    ov = ["canal", "alley", "market"]
    g("rf1", -21.4, ROOF, 8.0, layer="roof", overlooks=ov, enabled=False, note="at the B0 bulkhead door")
    g("rf2", -4.0, ROOF, -12.4, layer="roof", overlooks=ov, enabled=False, note="behind the rooftop letters' legs")
    g("rf3", -24.0, ROOF, -5.0, layer="roof", overlooks=ov, enabled=False, note="behind the west condenser")
    for x, y, z in ((-36, 9.5, -24.5), (-20, 10, -25), (-4, 10.5, -24.5), (12, 10, -25), (28, 10, -24.5), (40, 9.5, -25.5),
                    (20, 11, -21.5), (-20, 9, -4), (-8, 9.5, 0), (-13, 8.5, 9.4), (4, 9, 3), (13, 10, -6), (13, 10, 8),
                    (13, 9.5, 22), (24, 9, 6), (36, 9.5, 6), (28, 10.5, 13), (40, 9, 13)):
        L.air("air", x, y, z)

    # ------------------------------------------------------------------ cover: props and named solids 0.8 m or taller that block shots
    # (section 10 counts the 0.95 m stall rows and the tables, so the floor is 0.8 m, not 1.0); long sides every 3 m,
    # short sides only when 1.5 m or longer; points 0.6 m out on a walkable cell, 1.2 m apart
    L.extra["_coverRule"] = {"minHeight": 0.8, "maxSide": 10.0, "out": 0.6, "spacing": 1.2, "shortSideMin": 1.8, "every": 5.0,
                            "tags": ["cold-room", "rooftop-letters", "bulkhead"],
                            "skipTags": ["explosive", "street_lamp", "hydrant", "newspaper_box", "trash_can", "trash_bags", "basketball_hoop", "ebike", "box_truck_out"]}

    # ------------------------------------------------------------------ nav layers, links, reach, drops, tuning, guide
    L.nav = {
        "source": "layers, links and spawn reach (chinatown.md 4.4, 8.2, 15). The grids are written by the engine bake "
                  "(-run=MILevelBake) with FMIBoxWorld's code, never by the layout tool: `grid` is absent until then.",
        "cell": 0.5, "inflate": 0.5, "bandMin": 0.47, "bandMax": 1.5,
        "layers": [
            {"id": "street", "y": 0.0, "rect": {"minX": -44, "maxX": 44, "minZ": -34, "maxZ": 32}, "floor": "plane",
             "cols": 176, "rows": 132, "grid": None},
            {"id": "roof", "y": ROOF, "rect": {"minX": -26, "maxX": 8, "minZ": -14, "maxZ": 10}, "floor": "boxes",
             "cols": 68, "rows": 48, "grid": None},
        ],
        "links": [
            {"id": "yardStair", "a": "street", "b": "roof", "kind": "stair", "usedFrom": "nav step B",
             "path": [[-9.4, 0.0, 7.7], [-9.9, 0.11, 7.7], [-13.0, 2.85, 7.7], [-13.9, 2.85, 7.1], [-13.0, 2.95, 6.6],
                      [-9.9, 5.7, 6.6], [-9.2, 5.7, 6.6]]},
        ],
        "spawnReach": {"street": ["street", "roof"], "roof": ["roof", "street"]},
        "firingCellRange": 30, "strandedAfter": 10,
    }
    L.guide = {"source": "chinatown.md 7: the guidance stays the single-layer search on the street layer (the roof is optional); "
                         "hints keyed by objective id live in the text overlay (frontend.story.chinatown.guide.hints)",
               "mode": "singleLayer", "layer": "street", "graph": None, "targetHysteresis": 0.15,
               "intendedOrder": ["reel4", "reel5", "reel6"],
               "designLegs": [{"from": "start", "to": "reel4", "m": 34.5}, {"from": "reel4", "to": "reel5", "m": 27.4},
                              {"from": "reel5", "to": "reel6", "m": 59.6}, {"from": "reel6", "to": "extraction", "m": 60.2}]}
    L.drops = [
        {"id": "R1", "from": [8.0, ROOF, 3.5], "to": [9.0, 3.2, 3.5], "height": 2.5, "what": "kitchen roof parapet gap onto the Mott sidewalk shed"},
        {"id": "R2", "from": [9.5, 3.2, 3.5], "to": [11.0, 0.0, 3.5], "height": 3.2, "what": "the shed's missing panel to Mott St (roadway 0, sidewalk 0.15)"},
        {"id": "landing", "from": [-14.0, 2.85, 7.0], "to": [-15.0, 0.0, 7.0], "height": 2.85, "what": "over the stair's mid-landing rail (guarded anyway)"},
    ]
    L.guide["alternatives"] = [
        {"from": "reel5", "to": "reel6", "block": [17.4, 18.9, 23.5, 27.5], "what": "the dub room's Mott roll-up (leg 3 then runs via the Square and the banquet hall)"},
        {"from": "reel6", "to": "extraction", "block": [25.6, 26.8, 25.5, 28.5], "what": "the partition door (leg 4 then runs out the Mott roll-up and up Mott St)"},
    ]
    L.extra["checks"] = {
        "source": "level-specific inputs for tools/levels/check_level.py",
        "playerOnlyGaps": [{"x": -25.8, "z": -2.0, "what": "the market side door to alley A (1.4 m, player only)"}],
        "goonDoors": [{"x": x, "z": z, "what": w} for x, z, w in (
            (-20, -13.8, "market gate west"), (-13, -13.8, "market gate middle"), (-6, -13.8, "market gate east"),
            (-5, 5.8, "market rear roll-up"), (-20, 1.6, "cold-room door"), (3, -13.8, "bakery Canal door"),
            (4, -3.1, "bakery partition door"), (7.8, 3, "bakery Mott door"), (5, 9.8, "bakery alley door"),
            (33.8, -7, "neon workshop door"), (33, 18.2, "banquet main doors"), (18.2, 25.5, "dub room roll-up"),
            (26.15, 27, "dub room partition door"), (39, 27.1, "banquet kitchen door"))],
    }
    L.tuning = {"source": "chinatown.md 8.1, 15: the level's adds over config.json (absent for the Block)",
                "difficulty": {"maxAliveAdd": 1}, "spawn": {"excludePlayerRoom": True}, "startPitch": 4}
    L.vantage = {"source": "the yard stair's foot and a point on the market roof", "web": {"stairsFoot": {"x": -9.4, "y": 0, "z": 7.7}, "deck": {"x": -12, "y": ROOF, "z": -4}},
                 "ue": {"stairsFoot": {"X": -940, "Y": 770, "Z": 0}, "deck": {"X": -1200, "Y": -400, "Z": 570}}}

    # ------------------------------------------------------------------ title camera (15.1)
    L.cinematic = [((-41.5, 4.6, -24.5), (-12, 2.2, -19)), ((-30, 4.0, -23.5), (-10, 1.4, -16.5)), ((-18, 3.4, -21.0), (-10, 1.2, -16)),
                   ((-13, 2.8, -17.0), (-13, 1.6, -8)), ((-13, 3.0, -9), (-20, 1.2, -2)), ((-17.5, 3.2, -1.5), (-22.5, 0.8, 4.4)),
                   ((-8, 3.2, 1.0), (-5, 2.4, 9)), ((-5, 3.0, 8.5), (8, 2.0, 12)), ((4, 3.4, 12), (16, 2.0, 20)),
                   ((13, 4.0, 14), (18, 1.6, 25.5)), ((16, 5.0, 8), (31, 2.2, 10)), ((26, 4.2, 6), (33, 2.0, 18)),
                   ((31.5, 2.8, 4.0), (31.5, 2.0, -14)), ((31.5, 3.0, -16.5), (37.5, 1.6, -23.0))]

    # ------------------------------------------------------------------ steam, puddles, ground
    L.steam = [(-24, 0.05, -24.5), (6, 0.05, -25), (13, 0.05, 0), (-28, 0.05, 2), (-10, 0.05, 9), (-6, 3.0, 13.8), (42, 3.2, 17.9)]
    L.puddles = [(-38, -29.4, 1.6), (-27, -29.5, 1.2), (-15, -29.4, 2.2), (-3, -29.5, 1.0), (9, -29.4, 1.8), (22, -29.5, 1.4),
                 (31, -29.4, 0.9), (-31, -19.3, 1.4), (-20, -19.3, 2.4), (-1, -19.4, 1.1), (14, -19.4, 1.9), (29, -19.3, 1.3),
                 (10.4, -9, 0.9), (15.6, 1, 1.2), (10.4, 14, 1.6), (-28, 6, 1.0), (-10, 12, 1.4), (-6, 9, 0.8), (19.5, 3.5, 1.2)]
    for name, r in (("asphalt", rect(-44, 44, -29.8, -19)), ("asphalt", rect(10, 16, -19, 32)), ("asphalt", rect(-30, -26, -14, 14)),
                    ("asphalt", rect(-30, 8, 10, 14)), ("concrete", rect(-44, 44, -34, -29.8)), ("concrete", rect(-44, 10, -19, -14)),
                    ("concrete", rect(16, 44, -19, -14)), ("concrete", rect(8, 10, -14, 32)), ("concrete", rect(16, 18, -14, 32)),
                    ("concrete", rect(18, 44, 2, 18)), ("concrete", rect(-16, 0, 6, 10)), ("concrete", rect(-26, 0, -14, 6)),
                    ("concrete", rect(0, 8, -14, 10)), ("concrete", rect(29.4, 33.6, -14, 2)), ("concrete", rect(18.4, 26, 18.4, 31.6)),
                    ("metal", rect(34, 37.6, -10, -4)), ("metal", rect(-14.6, -8.6, 6, 8.2)), ("wood", rect(40.8, 43.6, 18.8, 26.6)),
                    ("cloth", rect(26.3, 43.6, 18.4, 31.6))):
        L.surfaces.append({"surface": name, "rect": r})
    for h, r, what in ((0.0, rect(-44, 44, -29.8, -19), "Canal roadway"), (0.0, rect(10, 16, -19, 32), "Mott roadway"),
                       (0.0, rect(-30, -26, -14, 14), "alley A"), (0.0, rect(-30, 8, 10, 14), "alley B"),
                       (0.0, rect(-25.6, -0.4, -13.6, 5.6), "market floor"), (0.0, rect(-16, 0, 6, 10), "yard"),
                       (SW, rect(-44, 44, -34, -29.8), "north sidewalk"), (SW, rect(-44, 10, -19, -14), "south sidewalk"),
                       (SW, rect(16, 44, -19, -14), "south sidewalk"), (SW, rect(8, 10, -14, 32), "Mott west sidewalk"),
                       (SW, rect(16, 18, -14, 32), "Mott east sidewalk"), (SW, rect(18, 44, 2, 18), "the Square"),
                       (SW, rect(0, 8, -14, 10), "bakery"), (SW, rect(29.4, 33.6, -14, 2), "arcade"), (SW, rect(34, 37.6, -10, -4), "workshop"),
                       (SW, rect(18, 44, 18, 32), "banquet hall and dub room"), (0.45, rect(27.5, 34.5, 6.5, 13.5), "pavilion plinth"),
                       (0.55, rect(40.8, 43.6, 18.8, 26.6), "stage"), (2.85, rect(-14.6, -13.18, 6, 8.2), "stair mid landing"),
                       (3.2, rect(8, 10, -3, 10), "Mott sidewalk shed deck"),
                       (ROOF, rect(-26, 0, -14, 6), "market roof"), (ROOF, rect(-26, -16, 6, 10), "B0 roof"), (ROOF, rect(0, 8, -3, 10), "kitchen roof")):
        L.floors.append({"h": h, "rect": r, "what": what})

    # ------------------------------------------------------------------ art-side: building facts, signs (English only), layout
    facts = {
        "N1": ("painted brick, cream", "Canal", "GOLD HITS RECORDS; 2F JADE TEAPOT DIM SUM (blade)", 6, 1),
        "N2": ("red brick", "Canal", "TWIN CARP JEWELRY; 3F SEA BREEZE TRAVEL (window letters)", 5, 0),
        "N3": ("buff brick", "Canal", "EIGHT TREASURE BBQ (roast-duck window)", 5, 1),
        "N4": ("brown brick, sidewalk shed in front", "Canal", "SPRING PINE HERBS & GINSENG", 6, 0),
        "N5": ("painted green", "Canal", "LONG LIFE NOODLE HOUSE; 2F MAHJONG (window neon)", 5, 0),
        "N6": ("red brick", "Canal", "SUNNY DAY LAUNDROMAT; BRIGHT MOON HOTEL (4-storey blade, the east landmark)", 7, 0),
        "W1": ("red brick", "Canal, alley A", "WEST CITY HARDWARE (gate down)", 6, 3),
        "M": ("painted block and corrugated fascia", "Canal", "GOLDEN TIDE MARKET (walk in)", 1, 0),
        "B0": ("common brick", "alley A", "market storeroom (shut); its roof bulkhead is the roof Goons' door", 1, 0),
        "W3": ("buff brick, sidewalk shed on Mott", "Canal, Mott", "MOON GATE BAKERY (walk through)", 5, 0),
        "S1": ("common brick", "alley B (backs)", "backs", 5, 2), "S2": ("painted brick", "alley B (backs)", "backs", 5, 1),
        "S3": ("brown brick", "Mott", "GOOD WISHES GROCERY; SEVEN STARS COACH; QUICK WIRE PHONES", 6, 1),
        "E1a": ("red brick", "Canal, Mott, Square", "GOLDEN LUCK ELECTRONICS (Canal); LILY CAFE (Mott); CLEVER HANDS TAILOR (Square)", 5, 1),
        "Arcade": ("terrazzo, glass kiosks", "Canal, Square", "PLUM BLOSSOM ARCADE", 0, 0),
        "E1b": ("buff brick", "Canal", "CLEAR VIEW OPTICAL (Canal); BIG LIGHT SIGNS (inside, off the arcade)", 6, 0),
        "E2": ("painted stucco, cream with gold trim", "Square, Mott", "CRANE PAVILION BANQUET HALL; SILVER WAVE VIDEO (the dub room)", 3, 0),
    }
    for b in L.buildings:
        f = facts.get(b["id"])
        if f:
            b.update({"facade": f[0], "front": f[1], "shops": f[2], "storeys": f[3], "fireEscapes": f[4]})
    _signs(L)
    L.layout = {
        "CANAL": {"northFacade": -33, "northKerb": -29.8, "southKerb": -19, "southFacade": -14, "alcoves": [-35, -22, -8, 5, 20, 31],
                  "tables": {"x": table_x, "length": 1.8, "z": [-18.8, -17.8]}},
        "MOTT": {"westFacade": 8, "westKerb": 10, "eastKerb": 16, "eastFacade": 18},
        "ALLEY_A": [-30, -26, -14, 14], "ALLEY_B": [-30, 8, 10, 14], "MARKET": [-26, 0, -14, 6], "YARD": [-16, 0, 6, 10],
        "STAIR": {"flight1": [-13.18, -9.8, 7.2, 8.2], "midLanding": [-14.6, -13.18, 6.0, 8.2], "flight2": [-13.18, -9.8, 6.0, 7.2],
                  "topLanding": [-9.8, -8.6, 6.0, 7.2], "rise": 0.219, "tread": 0.26, "risers": 13},
        "ROOF_Y": ROOF, "BAKERY": [0, 8, -14, 10], "ARCADE": [29.4, 33.6, -14, 2], "WORKSHOP": [34, 37.6, -10, -4],
        "SQUARE": [18, 44, 2, 18], "PAVILION": [27.5, 34.5, 6.5, 13.5], "E2": [18, 44, 18, 32], "DUB": [18.4, 26, 18.4, 31.6],
        "BANQUET": [26.3, 43.6, 18.4, 31.6], "MOTT_SHED": [8, 10, -3, 10, 3.2], "CANAL_SHED": [0, 12, -33, -29.8],
    }
    return L


def _signs(L):
    """Sign faces (art-side), English only. kind: band (lightbox band), blade (projecting), neon (exposed neon),
    letters (rooftop pan letters), board (painted), window (vinyl or neon in a window), arch, kiosk, poster, stencil,
    graffiti, street (street-name blade). normal is the side it shows. Colours follow chinatown.md 11.3 (no red behind a
    fight from the critical path)."""
    S = L.signage

    def add(sid, text, kind, x, y, z, nx, nz, w, h, colour, night="on", building=None, note=None, lit=True):
        e = {"id": sid, "text": text, "kind": kind, "building": building, "lit": lit, "night": night, "colour": colour,
             "web": {"pos": {"x": x, "y": y, "z": z}, "normal": {"x": nx, "y": 0, "z": nz}, "width": w, "height": h},
             "ue": {"pos": {"X": round(x * 100, 2), "Y": round(z * 100, 2), "Z": round(y * 100, 2)}, "width": w * 100, "height": h * 100}}
        if note:
            e["note"] = note
        S.append(e)

    # north row (faces south, z -33)
    add("n1.band", "GOLD HITS RECORDS", "band", -38.5, 3.7, -32.95, 0, 1, 6, 1.0, "warm white", building="N1", note="CDs and VINYL in the window")
    add("n1.blade", "JADE TEAPOT DIM SUM", "blade", -31.5, 8.0, -32.4, 1, 0, 1.0, 6, "jade green and white, red outline", building="N1", note="red only above 4 m on the north row")
    add("n2.band", "TWIN CARP JEWELRY", "band", -25.5, 3.7, -32.95, 0, 1, 6, 1.0, "gold on red", building="N2", note="the one red-ground lightbox, 3.2 to 4.2 m")
    add("n2.window", "SEA BREEZE TRAVEL", "window", -18.0, 10.6, -32.98, 0, 1, 4, 0.8, "white vinyl", building="N2", lit=False)
    add("n3.band", "EIGHT TREASURE BBQ", "band", -11.5, 3.7, -32.95, 0, 1, 6, 1.0, "amber", building="N3", note="roast-duck window below")
    add("n4.band", "SPRING PINE HERBS & GINSENG", "band", 8.5, 3.7, -32.95, 0, 1, 8, 1.0, "cool white on green", building="N4")
    add("n5.band", "LONG LIFE NOODLE HOUSE", "band", 16.5, 3.7, -32.95, 0, 1, 6, 1.0, "amber with a neon bowl outline", building="N5")
    add("n5.window", "MAHJONG", "window", 23.0, 6.0, -32.98, 0, 1, 2.4, 0.8, "green neon", night="flickers", building="N5")
    add("n6.band", "SUNNY DAY LAUNDROMAT", "band", 36.0, 3.7, -32.95, 0, 1, 7, 1.0, "cold white", building="N6")
    add("n6.blade", "BRIGHT MOON HOTEL", "blade", 40.5, 10.0, -32.4, -1, 0, 1.2, 12, "white and blue neon", building="N6", note="the east landmark over the truck")
    # market
    add("m.letters", "GOLDEN TIDE MARKET", "letters", -13.0, 7.8, -13.55, 0, -1, 14, 2.2, "warm white and gold neon", night="one stroke flickers", building="M", note="on the steel frame over the Canal parapet")
    add("m.band", "GOLDEN TIDE MARKET", "band", -13.0, 4.4, -14.05, 0, -1, 10, 0.9, "warm white", building="M")
    add("m.blade.w", "MARKET", "blade", -24.0, 4.8, -14.6, 1, 0, 0.8, 2.4, "warm white", building="M")
    add("m.blade.e", "MARKET", "blade", -2.0, 4.8, -14.6, 1, 0, 0.8, 2.4, "warm white", building="M")
    for i, (t, x) in enumerate((("FRESH FISH", -2.0), ("FRUIT", -20.7), ("VEGETABLES", -15.5), ("DRY GOODS", -10.3), ("TOFU", -5.1), ("ROAST MEAT", -20.7))):
        z = -8.0 if i < 5 else -1.8
        add("m.stall.%d" % i, t, "board", x, 2.6, z, 0, -1, 1.6, 0.4, "painted, lit by bulbs", building="M", lit=False)
    add("m.coldroom", "COLD ROOM", "band", -20.0, 2.55, 1.45, 0, -1, 1.4, 0.35, "cold white", building="M", note="visible down the west aisle")
    add("m.exit", "EXIT", "band", -5.0, 3.6, 5.55, 0, -1, 0.5, 0.2, "green", building="M", note="over the rear roll-up the guide takes")
    # bakery, alleys, Mott
    add("w3.neon", "MOON GATE BAKERY", "neon", 4.0, 4.4, -14.05, 0, -1, 6, 1.2, "pink exposed neon", building="W3")
    add("w1.band", "WEST CITY HARDWARE", "band", -37.0, 3.7, -14.05, 0, -1, 7, 1.0, "lightbox, off", night="off", building="W1", note="shut, gate down")
    add("alley.board", "LANTERN ALLEY", "board", -28.0, 3.4, -14.2, 0, -1, 2.6, 0.6, "painted wood, lit by a bulkhead lamp", building="W1",
        note="the party-goods wholesaler's board over the alley mouth, not a city sign", lit=False)
    add("alley.stencil", "MOTT ST →", "stencil", -26.05, 1.4, 12.0, -1, 0, 1.4, 0.4, "white stencil", building="B0", lit=False, note="at the dog-leg")
    add("e1a.band", "GOLDEN LUCK ELECTRONICS", "band", 23.5, 3.7, -14.05, 0, -1, 9, 1.0, "LED flex outline, cool white", building="E1a")
    add("e1a.lily", "LILY CAFE", "band", 17.95, 3.6, -8.0, -1, 0, 5, 0.9, "warm white", building="E1a", note="its glow lights the kitchen roof gap opposite")
    add("e1a.tailor", "CLEVER HANDS TAILOR", "band", 23.5, 3.2, 2.05, 0, 1, 4, 0.7, "warm white", building="E1a")
    add("arcade.n", "PLUM BLOSSOM ARCADE", "arch", 31.5, 4.6, -14.05, 0, -1, 4.2, 0.8, "jade green and white channel letters", building="Arcade")
    add("arcade.s", "PLUM BLOSSOM ARCADE", "arch", 31.5, 4.6, 2.05, 0, 1, 4.2, 0.8, "jade green and white channel letters", building="Arcade", note="the brightest object on the Square")
    for i, (t, z) in enumerate((("WATCH REPAIR", -6.0), ("KEYS CUT", -3.0), ("PHONES", -11.0), ("NEON SIGNS", -12.9))):
        add("arcade.kiosk.%d" % i, t, "kiosk", 29.45 if i < 3 else 32.55, 2.6, z, 1 if i < 3 else -1, 0, 1.2, 0.3, "cool white", building="Arcade")
    add("e1b.band", "CLEAR VIEW OPTICAL", "band", 39.0, 3.7, -14.05, 0, -1, 6, 1.0, "cool white", building="E1b")
    add("e1b.workshop", "BIG LIGHT SIGNS", "neon", 37.55, 2.2, -7.0, -1, 0, 2.6, 0.9, "blue, half finished", building="E1b", note="on the workshop's back wall")
    add("e2.band", "CRANE PAVILION BANQUET HALL", "band", 33.0, 4.4, 17.95, 0, -1, 12, 1.0, "gold and cream", building="E2", note="red only on the lacquered doors and the one lantern string")
    add("e2.dub", "SILVER WAVE VIDEO", "neon", 17.95, 3.9, 25.5, -1, 0, 4.5, 0.6, "white, half dead", night="flickers", building="E2", note="over the only raised shutter on Mott")
    add("s3.grocery", "GOOD WISHES GROCERY", "band", 8.05, 3.6, 18.0, 1, 0, 5, 0.9, "amber", building="S3", note="fruit boxes on the sidewalk")
    add("s3.coach", "SEVEN STARS COACH", "band", 8.05, 3.6, 24.0, 1, 0, 4, 0.9, "blue and white", building="S3", note="timetable posters with invented towns, no real routes or prices")
    add("s3.wire", "QUICK WIRE PHONES", "band", 8.05, 3.6, 28.5, 1, 0, 3.4, 0.9, "cool white", building="S3", note="window stickers: generic phone shapes, no makes")
    for i, (t, x, z, nx, nz) in enumerate((("CANAL ST", 9.8, -19.3, 0, 1), ("MOTT ST", 16.2, -19.3, 0, 1), ("CANAL ST", 16.2, -13.7, 0, -1))):
        add("street.%d" % i, t, "street", x, 3.0, z, nx, nz, 0.9, 0.2, "plain green blade, no agency mark", lit=False)
    for i, (t, x, z, nx, nz) in enumerate((("CDs $5 · USB $10", -9.1, -18.85, 0, -1), ("BAGS $20", -21.1, -18.85, 0, -1),
                                           ("SUNGLASSES $5", -33.1, -18.85, 0, -1), ("3 FOR $10", 6.9, -18.85, 0, -1))):
        add("placard.%d" % i, t, "board", x, 1.1, z, nx, nz, 0.5, 0.3, "card and marker", lit=False)
    for i, (t, x, z, nx, nz) in enumerate((("FOR LEASE", -20.0, -33.0, 0, 1), ("SHOP FOR RENT", 2.0, 13.95, 0, -1), ("FOR LEASE", 24.0, -32.98, 0, 1))):
        add("vacant.%d" % i, t, "window", x, 7.4, z, nx, nz, 0.6, 0.4, "paper, no numbers", lit=False)
    add("poster.opera", "SPRING SUNSHINE OPERA TROUPE · GALA NIGHT", "poster", -27.95, 1.8, -6.0, 1, 0, 0.8, 1.1, "wheat-paste, no faces", building="M", lit=False)
    for i, (t, x, y, z, nx, nz, col) in enumerate((("VULTURES", -29.95, 1.6, 2.0, 1, 0, "oxblood"), ("VLTR", -18.0, 1.2, 13.95, 0, -1, "oxblood"),
                                                   ("RULE", -5.0, 1.4, 13.95, 0, -1, "gold"), ("INC", 17.95, 1.0, 26.0, -1, 0, "gold"))):
        add("graffiti.%d" % i, t, "graffiti", x, y, z, nx, nz, 1.6, 0.6, col, lit=False)
    add("lanterns", "(no text) one string of 16 red paper lanterns", "lanterns", 33.0, 4.3, 17.6, 0, -1, 6, 0.6, "red, 40 to 80 nits", building="E2",
        note="the level's only lantern string, over the banquet doors")
