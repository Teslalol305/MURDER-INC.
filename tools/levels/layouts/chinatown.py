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
    # The player-only side door is 1.0 m wide (z -2.7..-1.7, centred where the design put its 1.4 m door): with 0.5 m
    # cells and the 0.5 m inflate a gap of 1.0 m or less is closed to Goon nav at every grid alignment, and the player's
    # 0.64 m capsule still passes (chinatown.md 4.2, the rule for player-only gaps). A 1.4 m gap was closed only by
    # where the cell centres happened to fall.
    mcols += L.wall_z("market", -26, -25.6, -13.6, 5.6, 0, 5.4, openings=[(-2.7, -1.7, 2.2)], surface="concrete", part="market.wall.west")
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
    # over the stair's flight 2 (x -14.6 .. -9.8) the yard parapet's top (6.7) stands 3.2 m over the treads: jumped, that is a
    # 4.2 m fall; a guard on the parapet's yard face (playerOnly, shots pass) keeps him on the roof side
    L.guard("roof-guard", -14.6, -9.8, ROOF, G1, 6.0, 6.1, part="market.guard.stairhead")

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

    # sidewalk shed on the bakery's Mott face: deck top 3.0 (design 3.2: a jump off the deck adds the 1.0 m apex to the
    # fall, and 3.2 + 1.0 lands above the 13 m/s damage speed; 3.0 + 1.0 = 4.0 stays under the 4.02 m threshold), posts
    # on the kerb line, plywood parapet with a missing panel
    SHED = 3.0
    L.box("shed-deck", 8, 10, SHED - 0.2, SHED, -3, 10, surface="wood", no_nav=True, part="mottshed.deck")
    L.box("shed-parapet", 9.9, 10, SHED, SHED + 1.0, -3, 2, surface="wood", part="mottshed.parapet")
    L.box("shed-parapet", 9.9, 10, SHED, SHED + 1.0, 5, 10, surface="wood", part="mottshed.parapet")
    L.guard("shed-guard", 10, 10.1, SHED, SHED + 3.0, -3.1, 2, part="mottshed.guard")
    L.guard("shed-guard", 10, 10.1, SHED, SHED + 3.0, 5, 10.1, part="mottshed.guard")
    L.guard("shed-guard", 8, 10, SHED, SHED + 3.0, -3.1, -3.0, part="mottshed.guard.north")
    L.guard("shed-guard", 8.1, 10, SHED, SHED + 3.0, 10.0, 10.1, part="mottshed.guard.south")
    for z in (-2.9, 0.1, 5.1, 8.1, 9.85):
        L.box("shed-post", 9.7, 9.9, SW, SHED - 0.2, z - 0.1, z + 0.1, surface="metal", part="mottshed.post")

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
            bx.append((x, x + 1.8, 0.9, 1.9, -18.8, -17.8, "cloth"))
        L.prop("vendor_table", bx, extra={"goods": "rack" if x in racks else "table", "what": "the disc and USB-stick table" if x == -10 else "vendor table"})
    L.vehicle("sedan", -36, -31.5, -29.8, -27.9)
    L.vehicle("taxi", -20, -15.5, -29.8, -27.9)
    L.vehicle("sedan", -4, 0.5, -29.8, -27.9)
    L.vehicle("van", 34, 38.8, -29.8, -27.7)
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
    for x, z in ((-41.0, -14.6), (-29.6, -14.6), (20.0, -14.6), (27.5, -14.6)):
        L.simple("trash_can", x, z, 0.58, 0.58, 0.95, y0=SW)
    for x, z in ((16.9, -10.0), (8.6, 12.6), (-40.0, -30.4)):
        L.simple("trash_bags", x, z, 0.9, 0.6, 0.62, y0=SW if x > 0 or z < -29.8 else 0.0, surface="cloth")
    L.prop("food_cart", [(-34.2, -32.8, SW, 1.4, -15.2, -14.2, "metal")], extra={"what": "dumpling cart"})
    L.prop("food_cart", [(-25.6, -24.7, SW, 1.4, -15.6, -14.2, "metal")], extra={"what": "fried-snack stall at the market's corner pier"})
    L.prop("food_cart", [(4.8, 6.3, SW, 1.4, -15.1, -14.2, "metal")], extra={"what": "roasted-nut cart"})

    # ------------------------------------------------------------------ explosives (18; section 9, in level order)
    E = L.explosive
    E("propane", -32.6, SW, -14.6, note="dumpling cart outside W1")
    E("propane", -24.4, SW, -14.6, note="fried-snack stall at the market's corner pier, a pair with 2 (4.4 m from the west gate)")
    E("propane", -24.4, SW, -15.45, note="as 1")
    E("propane", -3.0, SW, -32.6, note="EIGHT TREASURE BBQ kitchen tanks, a pair with 4")
    E("propane", -2.15, SW, -32.6, note="as 3")
    E("propane", 24.0, SW, -32.6, note="LONG LIFE NOODLE HOUSE")
    E("propane", 7.2, SW, -14.6, note="bakery front, roasted-nut cart (4.3 m from the bakery door)")
    E("propane", -13.0, 0, 4.9, note="stockroom, between pallets")
    E("propane", -0.9, 0, -11.2, note="fish-counter boiler, NE corner")
    E("propane", -8.6, 0, 9.3, note="yard gas cage, a pair with 10")
    E("propane", -7.75, 0, 9.3, note="as 9")
    E("propane", -26.5, 0, 8.0, note="alley A, a restaurant's back door at B0")
    E("rack", -17.0, 0, 13.4, note="alley B, a sign hanger's torch rack against S1")
    E("propane", 9.0, SW, -1.0, note="bakery kitchen's Mott door")
    E("rack", 37.1, SW, -9.4, rotation_y=1.5708, note="the neon workshop's torch rack, in the back corner (4.1 m from the door)")
    E("rack", 42.4, SW, 10.5, note="the Square's east side, a sign hanger's torch rack by the hoop fence (moved out of the arcade: its 7.5 m blast covered the whole 3.2 m exit)")
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
    L.objective("reel6", "6", "Reel 6 — The Dub Room", "THE DUB ROOM", "mott", (22.2, SW, 28.4), 1.5708, True,
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
                            "skipTags": ["explosive", "street_lamp", "hydrant", "newspaper_box", "trash_can", "trash_bags", "basketball_hoop", "ebike", "box_truck_out", "sign_pole", "muni_meter", "standpipe", "alarm_pedestal", "bike_rack", "traffic_cone", "traffic_drum", "bollard",
                            "exhaust_fan", "roof_vent", "antenna_mast", "truss_tower", "wayfinding_pylon", "shed_post", "cable_ramp", "hydrant",
                            "fire_hydrant", "milk_crates", "bucket_stack", "vendor_stool", "goods_carton", "cafe_chairs", "pallet_single"]}

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
    # the route graph (MAPS.md G2): on the street the drawn path is the street layer's own search as on the Block; from
    # the roof (the Reel 5 shortcut, where chinatown.md 7.3 says players get lost) it runs to the yard stair head or the
    # kitchen-roof gap and down the shed (R1 then R2, down only)
    gnodes = [{"id": "yardStair.a", "layer": "street", "pos": [-9.4, 0.0, 7.7]}, {"id": "yardStair.b", "layer": "roof", "pos": [-9.2, ROOF, 6.6]},
              {"id": "shedDrop.top", "layer": "roof", "pos": [7.4, ROOF, 3.5]}, {"id": "shedDrop.bottom", "layer": "street", "pos": [11.0, 0.0, 2.2]}]
    gedges = [{"from": 0, "to": 1, "kind": "stair", "link": "yardStair", "bias": 0.0, "path": L.nav["links"][0]["path"],
               "step": {"kind": "stair", "link": "yardStair", "height": ROOF}},
              {"from": 2, "to": 3, "kind": "drop", "drop": "R1+R2", "oneWay": True, "bias": 10.0,
               "path": [[7.4, ROOF, 3.5], [8.6, 3.0, 3.5], [9.6, 3.0, 2.6], [11.0, 0.0, 2.2]],
               "step": {"kind": "drop", "link": "R1+R2", "height": ROOF}}]
    L.guide = {"source": "chinatown.md 7: on the street the guidance is the street layer's search, as on the Block; the route graph "
                         "(MAPS.md G2) adds the yard stair (both ways) and the kitchen-roof drop onto the shed and off it (down only), "
                         "so a player on the roof is drawn a walkable way down. Hints keyed by objective id live in the text overlay "
                         "(frontend.story.chinatown.guide.hints)",
               "mode": "routeGraph", "layer": "street", "graph": {"nodes": gnodes, "edges": gedges}, "targetHysteresis": 0.15,
               "pathHysteresis": 0.10,
               "intendedOrder": ["reel4", "reel5", "reel6"],
               "designLegs": [{"from": "start", "to": "reel4", "m": 34.5}, {"from": "reel4", "to": "reel5", "m": 27.4},
                              {"from": "reel5", "to": "reel6", "m": 59.6}, {"from": "reel6", "to": "extraction", "m": 60.2}]}
    L.drops = [
        {"id": "R1", "from": [8.0, ROOF, 3.5], "to": [9.0, 3.0, 3.5], "height": 2.7, "what": "kitchen roof parapet gap onto the Mott sidewalk shed"},
        {"id": "R2", "from": [9.5, 3.0, 3.5], "to": [11.0, 0.0, 3.5], "height": 3.0, "what": "the shed's missing panel to Mott St (roadway 0, sidewalk 0.15)"},
        {"id": "landing", "from": [-14.0, 2.85, 7.0], "to": [-15.0, 0.0, 7.0], "height": 2.85, "what": "over the stair's mid-landing rail (guarded anyway)"},
    ]
    L.guide["waivers"] = [
        {"check": "guide.routeTie.reel6-extraction", "owner": "lane G, MAPS.md G4 (path hysteresis)",
         "reason": "the best way out avoiding the partition door is the Mott roll-up then the Square and the arcade, 6 % longer "
                   "(after Reel 6 moved 1 m east); no layout move that keeps leg 3 within 10 % of the design reaches 10 %. The "
                   "guidance keeps the drawn route until another is 10 % shorter (guide.pathHysteresis), so the line cannot flip "
                   "between the two inside the dub room."}]
    L.guide["alternatives"] = [
        {"from": "reel5", "to": "reel6", "block": [17.4, 18.9, 23.5, 27.5], "what": "the dub room's Mott roll-up (leg 3 then runs via the Square and the banquet hall)"},
        {"from": "reel6", "to": "extraction", "block": [25.6, 26.8, 25.5, 28.5], "what": "the partition door (leg 4 then runs out the Mott roll-up and up Mott St)"},
    ]
    L.extra["checks"] = {
        "source": "level-specific inputs for tools/levels/check_level.py",
        "sightlines": {"source": "chinatown.md 4.1 (check_level.py sight.*)", "rules": [
            {"id": "longestOpenLine", "rect": [-44, 44, -34, 32], "max": 81.0, "step": 2.0,
             "why": "the longest open line is the roadway from the start to the truck, 77 m (81 m between nav cells beside them)"},
            {"id": "protectedLane", "rect": [-44, 44, -19, -14], "max": 45.0, "step": 1.0,
             "why": "the south sidewalk is the protected lane: no open line along it longer than the Goons' 45 m sight range"}]},
        "playerOnlyGaps": [{"x": -25.8, "z": -2.2, "width": 1.0, "what": "the market side door to alley A (1.0 m, player only)"}],
        "goonDoors": [{"x": x, "z": z, "what": w} for x, z, w in (
            (-20, -13.8, "market gate west"), (-13, -13.8, "market gate middle"), (-6, -13.8, "market gate east"),
            (-5, 5.8, "market rear roll-up"), (-20, 1.6, "cold-room door"), (3, -13.8, "bakery Canal door"),
            (4, -3.1, "bakery partition door"), (7.8, 3, "bakery Mott door"), (5, 9.8, "bakery alley door"),
            (33.8, -7, "neon workshop door"), (33, 18.2, "banquet main doors"), (18.2, 25.5, "dub room roll-up"),
            (26.15, 27, "dub room partition door"), (39, 27.1, "banquet kitchen door"))],
    }
    L.extra["_audio"] = {
        "meta": {"file": "audio_chinatown.json", "about": "Canal Street's audio zones and beds (chinatown.md 12), audio.json's zone "
                 "schema, named by levels.json data.audio; read only when the loaded level is chinatown (MAPS.md E6). The "
                 "Block's underEl and chop-shop boxes must not apply here.", "generator": "tools/levels/build_level.py"},
        "zones": {
            "about": "web units; each zone has a fade margin; the strongest wins (audio.json zones)",
            "street": {"preset": "street", "default": True},
            "market": {"preset": "shop", "box": [[-25.6, 0, -13.6], [-0.4, 5.4, 5.6]], "fade": 1.5, "interior": True},
            "bakery": {"preset": "shop", "box": [[0.4, 0, -13.6], [7.6, 5.4, 9.6]], "fade": 1.0, "interior": True},
            "arcade": {"preset": "underEl", "box": [[29.4, 0, -14], [33.6, 4.2, 2]], "fade": 1.5},
            "banquet": {"preset": "shop", "box": [[26.3, 0, 18.4], [43.6, 5.0, 31.6]], "fade": 1.5, "interior": True},
            "dubRoom": {"preset": "shop", "box": [[18.4, 0, 18.4], [26.0, 4.2, 31.6]], "fade": 1.0, "interior": True},
            "alleyA": {"preset": "underEl", "box": [[-30, 0, -14], [-26, 18, 14]], "fade": 2.0},
            "alleyB": {"preset": "underEl", "box": [[-30, 0, 10], [8, 18, 14]], "fade": 2.0},
        },
        "ambience": {"beds": {"night": "bed_night_canal"}, "train": None,
                     "oneShots": {"about": "chinatown.md 12: new sounds for the audio lane (none exist yet)",
                                  "bridge_rumble": {"every": [90, 150], "place": "far east"},
                                  "mahjong_tiles": {"pos": [20, 6.0, -33.2], "loop": True},
                                  "talk_radio": {"pos": [8.2, 2.0, 18.0], "loop": True, "note": "invented content, from the grocery"},
                                  "transformer_hum": {"near": "every lit sign", "range": 4.0},
                                  "kitchen_fans": {"near": "alley A and B back doors"}, "fish_tank_pumps": {"pos": [-1.0, 1.0, -6.0]}}},
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
                       (3.0, rect(8, 10, -3, 10), "Mott sidewalk shed deck"),
                       (ROOF, rect(-26, 0, -14, 6), "market roof"), (ROOF, rect(-26, -16, 6, 10), "B0 roof"), (ROOF, rect(0, 8, -3, 10), "kitchen roof")):
        L.floors.append({"h": h, "rect": r, "what": what})

    # ------------------------------------------------------------------ art-side: building facts, signs (English only), layout
    facts = {
        "N1": ("painted brick, cream", "Canal", "GOLD HITS RECORDS; 2F JADE TEAPOT DIM SUM (blade)", 6, 1),
        "N2": ("red brick", "Canal", "TWIN CARP JEWELRY; 3F FAR SHORE TRAVEL (window letters)", 5, 0),
        "N3": ("buff brick", "Canal", "EIGHT TREASURE BBQ (roast-duck window)", 5, 1),
        "N4": ("brown brick, sidewalk shed in front", "Canal", "SPRING PINE HERBS & GINSENG", 6, 0),
        "N5": ("painted green", "Canal", "LONG LIFE NOODLE HOUSE; 2F MAHJONG (window neon)", 5, 0),
        "N6": ("red brick", "Canal", "SUNNY DAY LAUNDROMAT; HARBOR STAR HOTEL (4-storey blade, the east landmark)", 7, 0),
        "W1": ("red brick", "Canal, alley A", "WEST CITY HARDWARE (gate down)", 6, 3),
        "M": ("painted block and corrugated fascia", "Canal", "GOLDEN TIDE MARKET (walk in)", 1, 0),
        "B0": ("common brick", "alley A", "market storeroom (shut); its roof bulkhead is the roof Goons' door", 1, 0),
        "W3": ("buff brick, sidewalk shed on Mott", "Canal, Mott", "MOON GATE BAKERY (walk through)", 5, 0),
        "S1": ("common brick", "alley B (backs)", "backs", 5, 2), "S2": ("painted brick", "alley B (backs)", "backs", 5, 1),
        "S3": ("brown brick", "Mott", "GOOD WISHES GROCERY; SEVEN STARS COACH; QUICK WIRE PHONES", 6, 1),
        "E1a": ("red brick", "Canal, Mott, Square", "GOLDEN LUCK ELECTRONICS (Canal); LITTLE KITE CAFE (Mott); CLEVER HANDS TAILOR (Square)", 5, 1),
        "Arcade": ("terrazzo, glass kiosks", "Canal, Square", "PLUM BLOSSOM ARCADE", 0, 0),
        "E1b": ("buff brick", "Canal", "WILLOW BRIDGE OPTICAL (Canal); BIG LIGHT SIGNS (inside, off the arcade)", 6, 0),
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
        "BANQUET": [26.3, 43.6, 18.4, 31.6], "MOTT_SHED": [8, 10, -3, 10, 3.0], "CANAL_SHED": [0, 12, -33, -29.8],
    }
    _clutter(L)
    return L


def _names():
    """The art lane's name list (art/blender/assets/_chinatown_names.py) is the one source of every word on a Canal
    sign; the placements here only say where each face hangs."""
    import importlib.util
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "art", "blender", "assets", "_chinatown_names.py")
    spec = importlib.util.spec_from_file_location("_chinatown_names", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.check_english()
    return mod


def _signs(L):
    """Sign faces (art-side), English only, one entry per placement: `face` is the key in the art lane's list
    (FACES, NEON, OTHER_TEXT or DECAL_TEXT of art/blender/assets/_chinatown_names.py), `text` its words, `carrier`
    its mesh. normal is the side it shows. Colours follow chinatown.md 11.3 (no red behind a fight from the critical
    path)."""
    N = _names()
    S = L.signage

    def add(sid, face, x, y, z, nx, nz, building=None, note=None, text=None, kind=None, w=None, h=None, colour=None, night=None, lit=None):
        src, f = None, None
        if face in N.FACES:
            src, f = "FACES", N.FACES[face]
            text = text or " / ".join(ln[0] for ln in f["lines"])
            kind = kind or f["kind"]
            w = w or f["w"]
            h = h or f["h"]
            colour = colour or f.get("glow") or f.get("ink")
            lit = f.get("lit", False) if lit is None else lit
            carrier = f.get("carrier")
        elif face in N.NEON:
            src, f = "NEON", N.NEON[face]
            text = text or " / ".join(t for t in (f["text"], f.get("sub")) if t)
            kind, w, h, colour, lit, carrier = "neon", w or f["w"], h or f["h"], colour or f["colour"], True, f.get("mesh")
        elif face in N.OTHER_TEXT:
            src, f = "OTHER_TEXT", N.OTHER_TEXT[face]
            text = text or f["text"]
            kind, lit, carrier = kind or "letters", True, f.get("mesh")
        elif face in N.DECAL_TEXT:
            src = "DECAL_TEXT"
            kind, lit, carrier = kind or "decal", False, None
        else:
            carrier = None
        if night is None:
            night = "on" if lit else "unlit"
        e = {"id": sid, "face": face, "faceList": src, "text": text, "kind": kind, "building": building, "lit": bool(lit),
             "night": night, "colour": colour, "carrier": carrier,
             "web": {"pos": {"x": x, "y": y, "z": z}, "normal": {"x": nx, "y": 0, "z": nz}, "width": w, "height": h},
             "ue": {"pos": {"X": round(x * 100, 2), "Y": round(z * 100, 2), "Z": round(y * 100, 2)},
                    "width": round(w * 100, 2) if w else None, "height": round(h * 100, 2) if h else None}}
        if note:
            e["note"] = note
        S.append(e)

    # north row (faces south, z -33)
    add("n1.band", "GoldHits", -38.5, 3.7, -32.95, 0, 1, "N1")
    add("n1.blade", "JadeTeapot", -31.5, 8.0, -32.4, 1, 0, "N1", note="red outline only above 4 m on the north row")
    add("n2.band", "TwinCarp", -25.5, 3.7, -32.95, 0, 1, "N2", note="the one red-ground lightbox, 3.2 to 4.2 m")
    add("n2.window", "FarShore", -18.0, 10.6, -32.98, 0, 1, "N2")
    add("n3.band", "EightTreasure", -11.5, 3.7, -32.95, 0, 1, "N3", note="roast-duck window below")
    add("n4.band", "SpringPine", 8.5, 3.7, -32.95, 0, 1, "N4")
    add("n5.band", "LongLife", 16.5, 3.7, -32.95, 0, 1, "N5")
    add("n5.window", "MahjongNeon", 23.0, 6.0, -32.98, 0, 1, "N5", night="flickers")
    add("n6.band", "SunnyDay", 36.0, 3.7, -32.95, 0, 1, "N6")
    add("n6.blade", "HarborStar", 40.5, 10.0, -32.4, -1, 0, "N6", note="the east landmark over the truck")
    # the market
    add("m.letters", "RooftopLetters", -13.0, 7.8, -13.55, 0, -1, "M", w=14, h=2.2, colour="warm white and gold neon",
        night="one stroke flickers", note="on the steel frame over the Canal parapet")
    add("m.band", "GoldenTide", -13.0, 4.4, -14.05, 0, -1, "M")
    add("m.blade.w", "GoldenTideBlade", -24.0, 4.8, -14.6, 1, 0, "M")
    add("m.blade.e", "GoldenTideBlade", -2.0, 4.8, -14.6, 1, 0, "M")
    for i, (key, x, z) in enumerate((("StallFish", -2.0, -8.0), ("StallFruit", -20.7, -8.0), ("StallVeg", -15.5, -8.0),
                                     ("StallDry", -10.3, -8.0), ("StallTofu", -5.1, -8.0), ("StallRoast", -20.7, -1.8))):
        add("m.stall.%d" % i, key, x, 2.6, z, 0, -1, "M", note="hung above 2.4 m, art only")
    add("m.coldroom", "ColdRoom", -20.0, 2.55, 1.45, 0, -1, "M", note="visible down the west aisle")
    add("m.exit", None, -5.0, 3.6, 5.55, 0, -1, "M", text="EXIT", kind="exitbox", w=0.5, h=0.2, colour="green", lit=True,
        note="a plain green exit box over the rear roll-up the guide takes (not a shop sign; not in the name list)")
    # bakery, alleys, Mott
    add("w3.band", "MoonGate", 4.0, 3.5, -14.05, 0, -1, "W3")
    add("w3.neon", "MoonGateNeon", 4.0, 4.6, -14.1, 0, -1, "W3")
    add("w1.band", "WestCity", -37.0, 3.7, -14.05, 0, -1, "W1", night="off", note="shut, gate down")
    add("alley.board", "LanternAlley", -28.0, 3.4, -14.2, 0, -1, "W1", note="the party-goods wholesaler's board over the alley mouth, not a city sign")
    add("alley.stencil", "Stencil", -26.05, 1.4, 12.0, -1, 0, "B0", text="MOTT ST \u2192", w=1.4, h=0.4, colour="white stencil", note="at the dog-leg")
    add("e1a.band", "GoldenLuck", 23.5, 3.7, -14.05, 0, -1, "E1a")
    add("e1a.kite", "LittleKite", 17.95, 3.6, -8.0, -1, 0, "E1a", note="its glow lights the kitchen roof gap opposite")
    add("e1a.tailor", "CleverHands", 23.5, 3.2, 2.05, 0, 1, "E1a")
    add("arcade.n", "PlumBlossom", 31.5, 4.6, -14.05, 0, -1, "Arcade")
    add("arcade.s", "PlumBlossom", 31.5, 4.6, 2.05, 0, 1, "Arcade", note="the brightest object on the Square")
    for i, (key, x, z, nx) in enumerate((("KioskWatch", 29.45, -6.0, 1), ("KioskKeys", 29.45, -3.0, 1), ("KioskPhones", 29.45, -11.0, 1),
                                         ("KioskNeon", 32.55, -12.9, -1))):
        add("arcade.kiosk.%d" % i, key, x, 2.6, z, nx, 0, "Arcade")
    add("e1b.band", "WillowBridge", 39.0, 3.7, -14.05, 0, -1, "E1b")
    add("e1b.door", "BigLight", 33.55, 2.6, -7.0, -1, 0, "E1b", note="the workshop's door board off the arcade")
    add("e1b.workshop", "BigLightNeon", 37.55, 2.2, -7.0, -1, 0, "E1b", note="the half-finished sign on the workshop's back wall")
    add("e2.band", "CranePavilion", 33.0, 4.4, 17.95, 0, -1, "E2", note="red only on the lacquered doors and the one lantern string")
    add("e2.dub", "SilverWaveNeon", 17.95, 3.9, 25.5, -1, 0, "E2", night="flickers", note="over the only raised shutter on Mott")
    add("s3.grocery", "GoodWishes", 8.05, 3.6, 18.0, 1, 0, "S3", note="fruit boxes on the sidewalk")
    add("s3.coach", "SevenStars", 8.05, 3.6, 24.0, 1, 0, "S3")
    add("s3.wire", "QuickWire", 8.05, 3.6, 28.5, 1, 0, "S3")
    for i, (key, x, z, nx, nz) in enumerate((("StreetCanal", 9.8, -19.3, 0, 1), ("StreetMott", 16.2, -19.3, 0, 1), ("StreetCanal", 16.2, -13.7, 0, -1))):
        add("street.%d" % i, key, x, 3.0, z, nx, nz)
    for i, (key, x) in enumerate((("PlacardCDs", -9.6), ("PlacardUSB", -8.6), ("PlacardBags", -21.1), ("PlacardShades", -33.1), ("PlacardThree", 6.9))):
        add("placard.%d" % i, key, x, 1.1, -18.85, 0, -1)
    for i, (key, x, z, nx, nz) in enumerate((("ForLease", -20.0, -33.0, 0, 1), ("ForRent", 2.0, 13.95, 0, -1), ("ForRent", 24.0, -32.98, 0, 1))):
        add("vacant.%d" % i, key, x, 7.4, z, nx, nz)
    add("poster.opera", "OperaGala", -27.95, 1.8, -6.0, 1, 0, "M")
    for i, (t, x, y, z, nx, nz, col) in enumerate((("VULTURES", -29.95, 1.6, 2.0, 1, 0, "oxblood"), ("VLTR", -18.0, 1.2, 13.95, 0, -1, "oxblood"),
                                                   ("RULE", -5.0, 1.4, 13.95, 0, -1, "gold"), ("INC", 17.95, 1.0, 26.0, -1, 0, "gold"))):
        add("graffiti.%d" % i, "Graffiti", x, y, z, nx, nz, text=t, kind="graffiti", w=1.6, h=0.6, colour=col)
    add("lanterns", None, 33.0, 4.3, 17.6, 0, -1, "E2", text="", kind="lanterns", w=6, h=0.6, colour="red, 40 to 80 nits", lit=True,
        note="the level's only lantern string (16 red paper lanterns, no characters), over the banquet doors")


# Planned collider breakdown (chinatown.md 14.1, about 780): the groups this table authors as clutter, with the plan.
PLAN = {"street": 230, "alley": 60, "vendor": 34, "edges": 30, "square": 15, "spare": 45}


def _clutter(L):
    """The street clutter, alley and yard props, vendor goods and map edges of chinatown.md 14.1. The art lane fits its
    meshes to these colliders (MAPS.md B: the data decides collision). Heights follow the props they stand for. The
    line breakers (garment rails turned across the sidewalk, tall shop displays, newsstands, steam chimneys, step vans)
    keep the level's longest open ground line at the design's 77 m (start to truck) and the south sidewalk, the
    protected lane, under 45 m (the Goons' sight range): check_level.py sight.* tests both."""
    C = L.clutter
    S = SW
    # ---------------------------------------------------------------- Canal, north sidewalk (z -33 .. -29.8)
    alcoves = (-35, -22, -8, 5, 20, 31)

    def clear_of_alcove(x0, x1):
        return all(x1 < a - 2.0 or x0 > a + 2.0 for a in alcoves)

    # standpipes on the facades, a mailbox and muni-meters on the kerb, sandwich boards and goods at the shop fronts
    for x in (-41.0, -30.5, -17.0, -3.8, 9.5, 24.0, 35.5, 42.6):
        if clear_of_alcove(x - 0.15, x + 0.15):
            C("street", "standpipe", x - 0.15, x + 0.15, -33.0, -32.75, 0.9, y0=S, what="a siamese standpipe on the facade")
    for x in (-38.5, -24.5, -11.0, 2.5, 17.0, 27.5, 39.5):
        C("street", "muni_meter", x - 0.15, x + 0.15, -30.35, -30.05, 1.45, y0=S)
    for x in (-33.0, -6.0, 22.0):
        C("street", "mailbox", x - 0.25, x + 0.25, -30.55, -30.05, 1.25, y0=S, what="a blue street mailbox, no agency mark")
    for x in (-36.6, -26.6, -14.6, -1.0, 12.8, 28.4):
        C("street", "trash_can", x - 0.29, x + 0.29, -30.65, -30.07, 0.95, y0=S)
    for x0, x1 in ((-29.5, -27.5), (14.6, 16.6), (32.6, 34.6)):
        C("street", "bike_rack", x0, x1, -30.95, -30.85, 0.85, y0=S, what="a hoop bike rack with two locked bicycles")
    # shop-front spill: N1 records (CD racks), N3 the roast-meat shop's crates, N4 the herb shop's dried-goods bins
    # under the shed, N5 the noodle house's chairs, N6 the laundromat's carts
    spill = [(-43.0, -42.0, 0.6, 1.5, "cd_rack", "N1 record shop: a rack of CDs"), (-39.4, -38.4, 0.6, 1.5, "cd_rack", "N1 record shop: a rack of CDs"),
             (-31.6, -30.8, 0.6, 1.1, "crate_stack", "N1/N2: cartons waiting for pickup"),
             (-19.6, -18.6, 0.5, 1.2, "crate_stack", "N2: the jeweller's delivery boxes"),
             (-15.6, -14.4, 0.6, 1.0, "crate_stack", "N3: produce boxes for the kitchen"),
             (-12.4, -11.2, 0.6, 1.0, "crate_stack", "N3: produce boxes for the kitchen"),
             (-4.2, -3.4, 0.5, 1.3, "sandwich_board", "N3: a menu board on its stand"),
             (0.6, 2.2, 0.7, 0.95, "drygoods_bins", "N4 herb shop: dried mushrooms and roots in open bins"),
             (2.6, 3.4, 0.6, 1.6, "drygoods_shelf", "N4 herb shop: boxed teas on a shelf"),
             (7.2, 8.8, 0.7, 0.95, "drygoods_bins", "N4 herb shop: dried scallops and shrimp in open bins"),
             (9.2, 10.0, 0.6, 1.6, "drygoods_shelf", "N4 herb shop: ginseng boxes on a shelf"),
             (14.0, 14.8, 0.5, 1.2, "chair_stack", "N5 noodle house: stacked stools"),
             (16.4, 17.4, 0.6, 1.0, "crate_stack", "N5: flour sacks on a hand truck"),
             (23.2, 23.9, 0.5, 1.1, "sandwich_board", "N5: a lunch-special board (pictures, no prices)"),
             (26.0, 26.9, 0.6, 1.05, "laundry_cart", "N6 laundromat: a wire laundry cart"),
             (34.4, 35.3, 0.6, 1.05, "laundry_cart", "N6 laundromat: a wire laundry cart"),
             (37.8, 38.4, 0.5, 0.95, "trash_bags", "N6: bagged laundry for delivery")]
    for x0, x1, d, h, name, what in spill:
        if clear_of_alcove(x0, x1):
            C("street", name, x0, x1, -33.0 + 0.02, -33.0 + 0.02 + d, h, y0=S, what=what)
    # the line breakers at both ends of the north sidewalk: newsstands (the long-line rule, 77 m)
    C("street", "newsstand", -42.8, -40.9, -31.5, -30.1, 2.6, y0=S, what="a closed newsstand, shutters down, magazines behind wire (no titles)")
    C("street", "newsstand", 37.0, 38.9, -31.5, -30.1, 2.6, y0=S, what="a lit newsstand: snacks, lottery-free, no brand")

    # ---------------------------------------------------------------- Canal, south sidewalk (z -19 .. -14): the protected lane
    # chicanes: a garment rail turned across the walk (x a .. a + 0.6, z -17.85 .. -15.3) and a tall shop display 2 to 3 m
    # further on against the facade (z -15.5 .. -14.05); together they close every line along the lane
    chicanes = [(-40.6, -38.2, "W1: the hardware store's shuttered front, a stack of paint cans and ladders"),
                (None, -17.6, "the market's fruit display: oranges, pomelos, persimmons on stepped shelves"),
                (None, -24.0, "the market's corner: crates of melons and pomelos"),
                (0.4, -3.4, "the market's produce boxes: bok choy, gai lan, long beans"),
                (None, 5.0, "MOON GATE BAKERY: a rack of bread trays waiting to go in"),
                (21.6, 25.2, "GOLDEN LUCK: phone cases on a spinner rack"),
                (38.0, 35.4, "WILLOW BRIDGE OPTICAL: a sunglasses tower")]
    for a, f, what in chicanes:
        if a is not None:
            C("vendor", "garment_rail", a, a + 0.6, -17.85, -15.3, 1.85, y0=S, what="a rolling rail of jackets turned across the walk")
        if what:
            C("street", "shop_display", f, f + 1.2, -15.5, -14.05, 1.9, y0=S, what=what)
    # low things along the facade and the kerb
    for x in (-42.6, -35.3, -22.9, -8.4, 1.2, 24.4, 30.8, 42.8):
        C("street", "standpipe", x - 0.15, x + 0.15, -14.25, -14.0, 0.9, y0=S)
    for x in (19.4, 33.6, 40.4):
        C("street", "muni_meter", x - 0.15, x + 0.15, -18.95, -18.65, 1.45, y0=S)
    for x, z in ((-43.2, -16.5), (-31.6, -16.6), (-7.0, -14.6), (17.0, -15.6), (23.0, -14.6), (36.8, -14.6), (43.0, -18.4)):
        C("street", "trash_bags", x - 0.45, x + 0.45, z - 0.3, z + 0.3, 0.62, y0=S, surface="cloth")
    for x, z in ((-23.2, -16.8), (-33.0, -16.6), (-38.6, -16.9), (2.7, -16.8), (8.9, -16.6)):
        C("vendor", "goods_carton", x - 0.4, x + 0.4, z - 0.3, z + 0.3, 0.7, y0=S, surface="cloth", what="the vendors' stock in cartons")
    for x in (-38.0, -30.6, -22.6, -14.6, -6.6, 2.0, 6.0):
        C("vendor", "vendor_stool", x - 0.2, x + 0.2, -17.5, -17.1, 0.5, y0=S, what="a vendor's folding stool")
    C("street", "newspaper_box", 41.5, 42.0, -14.5, -14.05, 1.08, y0=S)
    C("street", "newspaper_box", 18.6, 19.1, -14.5, -14.05, 1.08, y0=S)

    # ---------------------------------------------------------------- Canal roadway and the map edges
    C("street", "steam_chimney", -22.75, -22.25, -27.15, -26.65, 2.5, what="an orange-and-white steam chimney over a manhole")
    C("street", "steam_chimney", 12.55, 13.05, -26.65, -26.15, 2.5, what="an orange-and-white steam chimney over a manhole")
    L.steam += [(-22.5, 2.55, -26.9), (12.8, 2.55, -26.4)]
    for x, z in ((-23.4, -27.6), (-21.6, -27.6), (-23.4, -26.2), (12.0, -25.4), (13.6, -25.4), (13.6, -27.2)):
        C("street", "traffic_cone", x - 0.17, x + 0.17, z - 0.17, z + 0.17, 0.7)
    # west: the dig behind the barriers (plywood fence, plates on edge, a generator, cones)
    C("edges", "dig_fence", -44.0, -43.75, -29.6, -19.4, 2.4, surface="wood", what="the dig's plywood fence")
    for z in (-29.4, -27.0, -24.6, -22.2, -19.8):
        C("edges", "traffic_drum", -42.6, -42.0, z - 0.3, z + 0.3, 1.05, surface="rubber", what="an orange traffic drum")
    C("edges", "road_plates", -43.6, -42.9, -31.6, -30.2, 1.9, y0=S, what="steel road plates stacked on edge against the corner")
    C("edges", "generator", -43.7, -42.5, -17.9, -16.2, 1.3, y0=S, what="the dig's generator")
    # east: around the stalled delivery truck and the IPX truck's nose
    for x, z in ((41.0, -19.6), (43.6, -19.4)):
        C("edges", "traffic_cone", x - 0.17, x + 0.17, z - 0.17, z + 0.17, 0.7)
    C("edges", "jersey_barrier", 42.6, 43.4, -18.9, -17.6, 0.81, y0=S, surface="concrete")
    C("edges", "hand_truck", 41.2, 41.8, -21.0, -20.3, 1.4, what="the delivery driver's hand truck with cartons")

    # ---------------------------------------------------------------- Mott St sidewalks
    for z0, z1, h, name, what in ((-13.2, -12.4, 1.0, "crate_stack", "the bakery's flour sacks"),
                                  (19.2, 20.8, 1.1, "fruit_crates", "GOOD WISHES GROCERY: more fruit boxes"),
                                  (21.4, 21.9, 1.3, "sandwich_board", "SEVEN STARS COACH: a departures board (times only)")):
        C("street", name, 8.02, 8.72, z0, z1, h, y0=S, what=what)
    for z in (-11.0, 14.6):
        C("street", "muni_meter", 9.55, 9.85, z - 0.15, z + 0.15, 1.45, y0=S)
    C("street", "mailbox", 9.4, 9.9, 15.6, 16.1, 1.25, y0=S)
    C("street", "bike_rack", 9.5, 9.6, 24.4, 26.2, 0.85, y0=S)
    for z0, z1, h, name, what in ((-12.6, -11.8, 1.3, "sandwich_board", "LITTLE KITE CAFE: a milk-tea board (pictures)"),
                                  (-6.2, -5.4, 0.9, "crate_stack", "milk crates"),
                                  (-1.0, -0.2, 1.1, "crate_stack", "the cafe's delivery"),
                                  (19.0, 20.0, 1.2, "crate_stack", "the dub room's blank disc cartons"),
                                  (28.4, 29.4, 1.0, "trash_bags", "E2's bags")):
        C("street", name, 17.3, 17.98, z0, z1, h, y0=S, what=what)
    for z in (-12.0, 6.0, 21.0):
        C("street", "muni_meter", 16.15, 16.45, z - 0.15, z + 0.15, 1.45, y0=S)
    C("street", "newspaper_box", 16.1, 16.55, -1.6, -1.1, 1.08, y0=S)
    C("street", "trash_can", 16.1, 16.68, 12.2, 12.78, 0.95, y0=S)

    # ---------------------------------------------------------------- alley A (x -30 .. -26) and alley B (z 10 .. 14), the yard
    alleyA = [(-30.0, -29.4, -13.0, -12.2, 1.1, "cardboard_bale", "a bale of flattened cartons"),
              (-30.0, -29.4, -6.0, -5.2, 0.9, "fish_boxes", "styrofoam fish boxes, stacked"),
              (-30.0, -29.4, -0.6, 0.6, 1.0, "grease_bin", "a restaurant's grease bin"),
              (-30.0, -29.3, 3.2, 4.4, 0.8, "ac_unit", "an air conditioner on the ground, dripping"),
              (-30.0, -29.4, 9.0, 9.8, 0.62, "trash_bags", "kitchen bags"),
              (-26.6, -26.02, -12.4, -11.6, 0.9, "fish_boxes", "the market's empty fish boxes"),
              (-26.6, -26.02, -9.6, -8.8, 1.2, "cardboard_bale", "a bale of flattened produce boxes"),
              (-26.6, -26.02, 1.0, 1.8, 0.62, "trash_bags", "the market's bags"),
              (-26.6, -26.02, 9.8, 10.6, 1.0, "grease_bin", "B0's grease bin")]
    for x0, x1, z0, z1, h, name, what in alleyA:
        C("alley", name, x0, x1, z0, z1, h, surface="cloth" if name in ("trash_bags", "cardboard_bale") else "metal", what=what)
    for x in (-29.95, -26.05):
        for y in (2.4, 2.4):
            pass
    for z in (-10.5, -3.0, 5.5):   # kitchen exhaust boxes on W1's wall above head height (art-side collision only)
        C("alley", "exhaust_fan", -30.0, -29.4, z - 0.4, z + 0.4, 0.8, y0=2.6, what="a kitchen exhaust fan box on the wall")
    alleyB = [(-29.8, -28.8, 13.4, 13.98, 0.9, "fish_boxes"), (-21.0, -20.0, 13.4, 13.98, 1.1, "cardboard_bale"),
              (-16.4, -15.6, 13.4, 13.98, 0.62, "trash_bags"), (-9.0, -8.0, 13.4, 13.98, 1.0, "grease_bin"),
              (-4.0, -3.2, 13.4, 13.98, 0.8, "ac_unit"), (5.6, 6.6, 13.4, 13.98, 0.62, "trash_bags"),
              (-25.6, -24.8, 10.02, 10.6, 0.9, "fish_boxes"), (-14.2, -13.4, 10.02, 10.6, 0.62, "trash_bags"),
              (-2.6, -1.8, 10.02, 10.6, 1.1, "cardboard_bale")]
    for x0, x1, z0, z1, h, name in alleyB:
        C("alley", name, x0, x1, z0, z1, h, surface="cloth" if name in ("trash_bags", "cardboard_bale") else "metal")
    for x in (-24.0, -12.0, 0.5):
        C("alley", "exhaust_fan", x - 0.4, x + 0.4, 13.4, 14.0, 0.8, y0=2.6, what="a kitchen exhaust fan box on the wall")
    yard = [(-7.8, -7.0, 6.05, 6.6, 1.0, "gas_cage_frame", "the empty half of the yard's gas cage"),
            (-3.0, -2.2, 9.4, 9.98, 0.9, "fish_boxes", None), (-1.2, -0.42, 9.2, 9.98, 1.2, "cardboard_bale", None),
            (-3.4, -2.6, 6.05, 6.6, 0.62, "trash_bags", None)]
    for x0, x1, z0, z1, h, name, what in yard:
        C("alley", name, x0, x1, z0, z1, h, what=what)

    # ---------------------------------------------------------------- the market hall (the stalls' spill, aisles kept 2 m or wider)
    for xa, xb, row in ((-21.6, -19.8, "R1"), (-16.4, -14.6, "R2"), (-11.2, -9.4, "R3"), (-6.0, -4.2, "R4")):
        C("spare", "fish_boxes", xa, xa + 0.8, -11.7, -11.1, 0.9, what="styrofoam boxes at the end of stall row " + row)
        C("spare", "produce_crates", xb - 0.8, xb, -0.4, 0.2, 0.8, what="crates at the back of stall row " + row)
    C("spare", "hand_truck", -24.4, -23.8, -8.4, -7.7, 1.3, what="a hand truck of cartons in the west aisle")
    C("spare", "ice_bin", -2.2, -1.5, -11.6, -10.8, 0.9, what="the fish counter's ice bin")
    C("spare", "scale_stand", -25.5, -25.05, -11.0, -10.4, 1.4, what="a hanging-scale stand")

    # ---------------------------------------------------------------- the roofs (y 5.7): vents, pipes on sleepers, the old antenna
    R = ROOF
    roof = [(-24.6, -24.0, -12.8, -12.2, 0.9, "roof_vent"), (-17.0, -16.4, -12.8, -12.2, 0.9, "roof_vent"),
            (-11.0, -10.4, -7.6, -7.0, 0.9, "roof_vent"), (-6.6, -6.0, 3.4, 4.0, 0.9, "roof_vent"),
            (-19.0, -18.0, 2.6, 3.4, 1.2, "roof_ac"), (-3.0, -1.6, 1.6, 2.6, 1.2, "roof_ac"),
            (-25.4, -24.8, -0.8, 0.6, 2.2, "antenna_mast"), (-9.0, -8.4, -12.8, -12.2, 0.9, "roof_vent"),
            (2.2, 2.8, -2.6, -2.0, 0.9, "roof_vent"), (5.0, 6.2, 7.6, 8.8, 1.1, "roof_ac"), (1.0, 1.6, 8.8, 9.4, 1.6, "exhaust_stack"),
            (-22.6, -22.0, 7.0, 7.6, 0.9, "roof_vent"), (-18.4, -17.4, 8.6, 9.4, 1.0, "roof_ac")]
    for x0, x1, z0, z1, h, name in roof:
        C("roof", name, x0, x1, z0, z1, h, y0=R)

    # ---------------------------------------------------------------- the Square and the banquet hall
    for x, z in ((25.0, 2.6), (37.0, 17.4), (43.4, 9.0)):
        C("square", "trash_can", x - 0.29, x + 0.29, z - 0.29, z + 0.29, 0.95, y0=S)
    C("square", "bike_rack", 22.0, 24.0, 17.6, 17.7, 0.85, y0=S)
    C("square", "chess_table", 36.6, 37.4, 13.0, 13.8, 0.75, y0=S, what="a concrete chess table")
    C("square", "chess_table", 22.6, 23.4, 5.4, 6.2, 0.75, y0=S, what="a concrete chess table")
    C("square", "planter", 26.0, 27.0, 15.6, 16.6, 0.9, y0=S, surface="concrete")
    for x, z in ((27.0, 19.0), (28.0, 31.0), (40.0, 19.0), (42.8, 31.0), (35.5, 31.0)):
        C("spare", "chair_stack", x - 0.25, x + 0.25, z - 0.25, z + 0.25, 1.2, y0=S, what="banquet chairs, stacked")
    C("spare", "tape_shelf", 18.45, 19.1, 19.0, 21.4, 2.0, y0=S, what="the dub room's shelf of tapes")
    C("spare", "box_pile", 24.2, 25.4, 30.6, 31.5, 1.0, y0=S, what="cartons of blank discs")

    # ---------------------------------------------------------------- sign poles on every kerb (parking, no standing, one way): thin but
    # 7.6 cm, over the 6 cm flicker floor; the skipper drops the ones that land on a door, a spawn or another prop
    def poles(xs, z0, z1, what="a street-sign pole (parking rules, no words that matter)"):
        for x in xs:
            C("street", "sign_pole", x - 0.038, x + 0.038, z0, z1, 2.7, y0=S, what=what)
    poles([-43.0 + 4.6 * i for i in range(19)], -30.2, -30.124)
    # (none on the south kerb west of Mott: the vendor tables and their gaps are the kerb there)
    poles([18.6 + 4.6 * i for i in range(6)], -18.976, -18.9)
    for z in [-12.0 + 4.5 * i for i in range(10)]:
        if z < 24.0:   # the S3 sidewalk past the box truck (z 25 .. 31) stays clear: it is t3's way out
            C("street", "sign_pole", 9.86, 9.936, z - 0.038, z + 0.038, 2.7, y0=S)
        C("street", "sign_pole", 16.064, 16.14, z + 2.0 - 0.038, z + 2.0 + 0.038, 2.7, y0=S)
    for x in (0.2, 3.2, 6.2, 9.2, 11.8):
        C("street", "shed_post", x - 0.1, x + 0.1, 0.0 - 33.0 + 0.02, -32.78, 3.4, y0=S, what="the Canal sidewalk shed's facade-side post")
    for x, z in ((-34.0, -30.5), (-20.5, -30.5), (-9.5, -30.6), (3.8, -30.6), (19.0, -30.6), (30.0, -30.6)):
        C("street", "fire_hydrant", x - 0.16, x + 0.16, z - 0.16, z + 0.16, 0.74, y0=S) if (x, z) == (-9.5, -30.6) else \
            C("street", "newspaper_box", x - 0.24, x + 0.24, z - 0.21, z + 0.21, 1.08, y0=S)
    for x in (-41.6, -33.8, -27.4, -12.8, -2.4, 6.4):
        C("street", "planter", x - 0.4, x + 0.4, -14.62, -14.02, 0.8, y0=S, surface="concrete", what="a shop's planter box")
    for z in (-9.0, -4.0, 1.0, 13.0, 21.5):
        C("street", "crate_stack", 17.38, 17.98, z - 0.4, z + 0.4, 0.9, y0=S, what="crates along the Mott facade")
    # alleys and the yard, second pass
    for z in (-11.0, -8.0, -2.0, 1.6, 6.0, 11.2):
        C("alley", "milk_crates", -30.0, -29.45, z - 0.3, z + 0.3, 0.75, what="milk crates against W1")
    for z in (-6.2, -4.8, 3.2, 7.0):
        C("alley", "styrofoam_stack", -26.55, -26.0, z - 0.3, z + 0.3, 1.0, what="styrofoam fish boxes")
    for x in (-27.0, -18.0, -11.0, -6.0, -1.0, 4.2):
        C("alley", "bucket_stack", x - 0.3, x + 0.3, 13.45, 13.98, 0.7, what="buckets and a mop wringer")
    for x in (-22.0, -19.6, -7.0, 2.6, 4.6, 7.2):
        C("alley", "cardboard_bale", x - 0.5, x + 0.5, 10.02, 10.55, 1.0, surface="cloth")
    for x, z in ((-7.6, 7.2), (-3.8, 9.5), (-0.9, 7.4)):
        C("alley", "pallet_single", x - 0.6, x + 0.6, z - 0.5, z + 0.5, 0.15 + 0.12, what="a pallet on the ground")
    # edges, second pass
    for x, z in ((-43.2, -18.6), (-43.3, -15.0), (43.2, -16.8), (43.3, -32.4), (-43.3, -32.6)):
        C("edges", "traffic_drum", x - 0.3, x + 0.3, z - 0.3, z + 0.3, 1.05, y0=S, surface="rubber")
    for x in (-43.2, -42.4):
        C("edges", "barricade", x - 0.35, x + 0.35, -29.7, -29.0, 1.0, what="a sawhorse barricade at the dig")
    for x in (21.0, 27.0):
        for z in (-27.9, -24.7):
            C("edges", "traffic_cone", x - 0.17, x + 0.17, z - 0.17, z + 0.17, 0.7, what="hazard cones around the double-parked truck")

    # third pass: what a Canal sidewalk carries at night
    for x0, x1, z0, z1, h, name, what in (
            (-37.6, -37.2, -30.6, -30.2, 1.4, "alarm_pedestal", "a fire-alarm pedestal"),
            (11.0, 11.4, -30.6, -30.2, 1.4, "alarm_pedestal", "a fire-alarm pedestal"),
            (-25.0, -24.6, -31.2, -30.0, 2.5, "phone_kiosk", "a dark sidewalk phone kiosk, no brand"),
            (25.8, 26.2, -31.2, -30.0, 2.5, "phone_kiosk", "a dark sidewalk phone kiosk, no brand"),
            (-41.6, -41.0, -32.9, -31.3, 1.05, "ebike", "a delivery e-bike against the facade"),
            (-27.4, -26.8, -32.9, -31.3, 1.05, "ebike", "a delivery e-bike against the facade"),
            (13.6, 14.2, -32.9, -31.3, 1.05, "ebike", "a delivery e-bike against the facade"),
            (-10.6, -10.0, -32.9, -32.3, 1.4, "hand_truck", "a hand truck of cartons"),
            (28.8, 29.4, -32.9, -32.3, 1.4, "hand_truck", "a hand truck of cartons"),
            (-13.8, -13.2, -32.95, -32.4, 0.75, "milk_crates", "milk crates"),
            (17.8, 18.4, -32.95, -32.4, 0.75, "milk_crates", "milk crates"),
            (38.9, 39.5, -32.95, -32.4, 0.75, "milk_crates", "milk crates"),
            (40.4, 41.2, -32.95, -32.35, 0.8, "planter", "the laundromat's planter"),
            (-6.0, -5.2, -32.95, -32.45, 1.1, "sandwich_board", "N3: a board with photographs of the roast meats"),
            (32.4, 33.0, -15.6, -14.05, 1.2, "crate_stack", "the arcade corner's stacked cartons"),
            (40.8, 41.4, -14.6, -14.05, 0.75, "milk_crates", "milk crates"),
            (29.0, 29.35, -15.0, -14.05, 2.5, "phone_kiosk", "a dark sidewalk phone kiosk, no brand"),
            (16.1, 16.6, 3.0, 3.5, 0.9, "bollard", "a bollard at the Square's corner"),
            (16.1, 16.6, 8.0, 8.5, 0.9, "bollard", "a bollard at the Square's corner"),
            (16.1, 16.6, 16.6, 17.1, 0.9, "bollard", "a bollard at the Square's corner"),
            (17.3, 17.98, 4.6, 5.4, 1.2, "newsstand_bundle", "bundled papers waiting for the morning")):
        C("street", name, x0, x1, z0, z1, h, y0=S, what=what)
    for x0, x1, z0, z1, h, name in ((43.6, 43.98, -29.8, -27.1, 2.4, "dig_fence"), (43.6, 43.98, -19.9, -19.05, 2.4, "dig_fence"),
                                    (14.6, 15.8, 31.2, 31.9, 1.0, "barricade"), (-43.9, -43.6, -33.0, -30.0, 2.4, "dig_fence"),
                                    (-43.9, -43.6, -18.9, -14.2, 2.4, "dig_fence"), (43.6, 43.95, -33.0, -31.9, 2.4, "dig_fence")):
        C("edges", name, x0, x1, z0, z1, h, y0=(S if name == "dig_fence" and (z1 < -29.8 or z0 > -19.0) else 0.0), surface="wood",
          what="the end of the street: plywood and sawhorses")
    for x0, x1, z0, z1, h, name in ((19.2, 19.7, 29.0, 31.4, 2.0, "tape_shelf"), (22.6, 23.2, 18.45, 19.0, 1.2, "box_pile"),
                                    (27.0, 27.5, 31.0, 31.5, 1.2, "chair_stack"), (31.0, 31.5, 31.0, 31.5, 1.2, "chair_stack"),
                                    (38.8, 39.3, 19.0, 19.5, 1.2, "chair_stack"), (42.9, 43.5, 19.0, 19.5, 1.2, "chair_stack"),
                                    (36.6, 37.4, 28.0, 28.6, 1.6, "kitchen_rack"), (40.6, 41.4, 27.4, 27.9, 1.6, "kitchen_rack"),
                                    (0.5, 1.1, -12.6, -12.0, 0.9, "flour_sacks"), (6.6, 7.3, 8.6, 9.4, 0.9, "flour_sacks"),
                                    (35.0, 36.2, -4.6, -4.05, 1.8, "glass_rack"), (-24.6, -24.0, 3.6, 4.2, 0.9, "fish_boxes")):
        C("spare", name, x0, x1, z0, z1, h, y0=S if x0 > -1 else 0.0)

    L.deviations.append("Reel 6 at x 22.2 (design 21.2, still by the racks): the leg-4 route tie's margin goes from 0.4 % to 6 %; "
                        "the rest is the guidance's path hysteresis (MAPS.md G6), see guide.waivers.")

    # ---------------------------------------------------------------- the budget the checker compares with the plan
    named = {"street_lamp": "street", "hydrant": "street", "newspaper_box": "street", "trash_can": "street", "trash_bags": "street",
             "food_cart": "vendor", "vendor_table": "vendor", "ebike": "street", "fruit_crates": "street", "fruit_stand": "street",
             "dumpster": "alley", "crate_stack": "alley", "pallet_stack": "alley", "jersey_barrier": "edges", "delivery_truck": "edges",
             "raised_bed": "square", "park_bench": "square", "card_table": "square", "hotpot_cart": "square", "stone_lion": "square",
             "basketball_hoop": "square"}
    groups = {}
    for p in L.props:
        g = p.get("group") or named.get(p["name"])
        if g:
            groups[g] = groups.get(g, 0) + len(p["colliders"])
    L.extra["colliderBudget"] = {"source": "chinatown.md 14.1 (about 780, cap 800): the clutter groups this table authors, planned "
                                           "against placed; the rest of the plan is the shells, rooms, stairs and vehicles above",
                                 "plannedTotal": 780, "cap": 800, "clutterPlanned": PLAN, "clutterPlaced": groups,
                                 "skipped": L.clutter_skipped}
