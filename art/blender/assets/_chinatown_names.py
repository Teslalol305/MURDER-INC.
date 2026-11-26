"""Canal Street (Level 2): every invented name and word on a sign, board, poster or placard, in ENGLISH ONLY.

The owner's answer of 2026-11-26 ~02:00 (docs/unreal/DECISIONS.md): Canal Street signs in English only, no Chinese
characters anywhere. Chinatown reads through the architecture, the lanterns, the market, the produce, the awnings, the
sign style (stacked blades, lightbox bands, exposed neon, painted boards) and the English shop names. Every business
name here is invented (docs/unreal/maps/chinatown.md 13.3, translated to English only); IPX is the only real mark in
the game and does not appear on this level's signs. No phone numbers, no web addresses, no prices of real routes.

`FACES` are drawn into the sign atlases (assets/_chinatown_atlas.py) and shown on the generic carriers
(SM_Sign_CT_Band_*, _Blade_*, _Kiosk, _Board, _Arch, _Poster, _Placard, _StreetBlade). `NEON` are built as glass tube
geometry along the letter outlines (no texture). `check_english()` fails on any character outside printable ASCII
plus the few typographic marks listed in ALLOWED, so a CJK character can never slip into a face or a mesh.

Name status: every name is invented and NOT YET SEARCHED against real New York businesses, brands and trade dress
(MAPS.md lane C, item C1). The atlases are redrawn from this table when a name changes.
"""

ALLOWED = set(" !&'(),-./0123456789:?ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz$#+·→")

# kind: band (lightbox band over a shop), blade (vertical lightbox, letters stacked), kiosk (small lightbox),
# board (painted, unlit), poster (paper, unlit), placard (card and marker, unlit), street (green street blade,
# retroreflective), arch (lit arch face). lit: the face has an emissive map (night value at strength 1).
# field / ink / sub ink: sRGB hex. glow: the colour the face throws (for the light rig's sign wash).
# lines: [(text, cap height as a fraction of the face height, vertical centre as a fraction from the top, font)].
# carrier: the mesh the face goes on. where: building and place (chinatown.md 4.10, 13.3).
FACES = {
    # ------------------------------------------------------------------ Canal Street, north row (N1 .. N6)
    "GoldHits": dict(kind="band", w=8.0, h=0.9, field="#101820", ink="#f4c542", lit=True, glow="#ffc84a",
                     lines=[("GOLD HITS RECORDS", 0.40, 0.40, "heavy"), ("CDs  ·  VINYL  ·  KARAOKE", 0.13, 0.80, "bold")],
                     carrier="SM_Sign_CT_Band_8m", where="N1 ground, Canal"),
    "JadeTeapot": dict(kind="blade", w=0.9, h=6.0, field="#0e3b2c", ink="#f2f4ee", rim="#c8322a", lit=True, glow="#7dffb0",
                       lines=[("JADE TEAPOT", 0.0, 0.0, "heavy"), ("DIM SUM", 0.0, 0.0, "heavy")],
                       carrier="SM_Sign_CT_Blade_6m", where="N1 2F blade over Canal (red outline above 4 m)"),
    "TwinCarp": dict(kind="band", w=8.0, h=0.9, field="#9e1b14", ink="#f6cf4a", lit=True, glow="#ffb040",
                     lines=[("TWIN CARP JEWELRY", 0.42, 0.42, "heavy"), ("GOLD  ·  JADE  ·  WATCHES", 0.13, 0.81, "bold")],
                     carrier="SM_Sign_CT_Band_8m", where="N2 ground, Canal: the one red-ground lightbox, 3.2 to 4.2 m"),
    "FarShore": dict(kind="kiosk", w=3.0, h=0.6, field="#e8eef0", ink="#1b5d8a", lit=False, glow=None,
                      lines=[("FAR SHORE TRAVEL", 0.34, 0.40, "heavy"), ("TICKETS  ·  TOURS", 0.15, 0.80, "bold")],
                      carrier="SM_Sign_CT_Kiosk_3m", where="N2 3F window (window vinyl, lit by the room)"),
    "EightTreasure": dict(kind="band", w=8.0, h=0.9, field="#f3e6c4", ink="#7a2410", sub="#2c2a26", lit=True, glow="#ffd9a0",
                          lines=[("EIGHT TREASURE BBQ", 0.40, 0.40, "heavy"),
                                 ("ROAST DUCK  ·  ROAST PORK  ·  SOY CHICKEN", 0.13, 0.80, "bold")],
                          carrier="SM_Sign_CT_Band_8m", where="N3 ground, Canal, over the roast-duck window"),
    "SpringPine": dict(kind="band", w=10.0, h=0.9, field="#1d3b2a", ink="#f0e2b6", lit=True, glow="#d8f0c0",
                       lines=[("SPRING PINE HERBS & GINSENG", 0.38, 0.42, "heavy"), ("DRIED GOODS  ·  TEAS  ·  REMEDIES", 0.13, 0.81, "bold")],
                       carrier="SM_Sign_CT_Band_10m", where="N4 ground, Canal, behind the sidewalk shed"),
    "LongLife": dict(kind="band", w=8.0, h=0.9, field="#f6f1e4", ink="#1a5b44", sub="#a0471c", lit=True, glow="#fff3d8",
                     lines=[("LONG LIFE NOODLE HOUSE", 0.38, 0.40, "heavy"), ("HAND-PULLED NOODLES  ·  WONTON SOUP", 0.13, 0.80, "bold")],
                     carrier="SM_Sign_CT_Band_8m", where="N5 ground, Canal"),
    "SunnyDay": dict(kind="band", w=8.0, h=0.9, field="#0f4c7a", ink="#ffffff", lit=True, glow="#cfe8ff",
                     lines=[("SUNNY DAY LAUNDROMAT", 0.40, 0.40, "heavy"), ("WASH  ·  DRY  ·  FOLD", 0.13, 0.80, "bold")],
                     carrier="SM_Sign_CT_Band_8m", where="N6 ground, Canal"),
    "HarborStar": dict(kind="blade", w=1.1, h=12.0, field="#0b1626", ink="#f4f8ff", rim="#4aa8ff", lit=True, glow="#bcd8ff",
                       lines=[("HARBOR STAR", 0.0, 0.0, "heavy"), ("HOTEL", 0.0, 0.0, "heavy")],
                       carrier="SM_Sign_CT_Blade_12m", where="N6, four-storey blade: the east landmark over the IPX truck"),
    # ------------------------------------------------------------------ the market, the alley, the bakery
    "GoldenTide": dict(kind="band", w=10.0, h=0.9, field="#f2b51e", ink="#2a1a0c", lit=True, glow="#ffd060",
                       lines=[("GOLDEN TIDE MARKET", 0.42, 0.40, "heavy"), ("FISH  ·  PRODUCE  ·  DRY GOODS  ·  OPEN 7 DAYS", 0.13, 0.80, "bold")],
                       carrier="SM_Sign_CT_Band_10m", where="the market's Canal band"),
    "GoldenTideBlade": dict(kind="blade", w=0.8, h=4.0, field="#f2b51e", ink="#2a1a0c", rim="#2a1a0c", lit=True, glow="#ffd060",
                            lines=[("MARKET", 0.0, 0.0, "heavy")], carrier="SM_Sign_CT_Blade_4m", where="the market's two blades"),
    "StallFish": dict(kind="board", w=1.6, h=0.42, field="#1f4e8c", ink="#ffffff", lines=[("FRESH FISH", 0.52, 0.52, "heavy")],
                      carrier="SM_Sign_CT_StallBoard", where="market stall board"),
    "StallFruit": dict(kind="board", w=1.6, h=0.42, field="#e8a81c", ink="#2a1a0c", lines=[("FRUIT", 0.52, 0.52, "heavy")],
                       carrier="SM_Sign_CT_StallBoard", where="market stall board"),
    "StallVeg": dict(kind="board", w=1.6, h=0.42, field="#2f6b33", ink="#ffffff", lines=[("VEGETABLES", 0.50, 0.52, "heavy")],
                     carrier="SM_Sign_CT_StallBoard", where="market stall board"),
    "StallDry": dict(kind="board", w=1.6, h=0.42, field="#6b4a2a", ink="#f4e6c0", lines=[("DRY GOODS", 0.52, 0.52, "heavy")],
                     carrier="SM_Sign_CT_StallBoard", where="market stall board"),
    "StallTofu": dict(kind="board", w=1.6, h=0.42, field="#f1eee2", ink="#1f4e8c", lines=[("TOFU", 0.52, 0.52, "heavy")],
                      carrier="SM_Sign_CT_StallBoard", where="market stall board"),
    "StallRoast": dict(kind="board", w=1.6, h=0.42, field="#7a2a14", ink="#f6d68a", lines=[("ROAST MEAT", 0.52, 0.52, "heavy")],
                       carrier="SM_Sign_CT_StallBoard", where="market stall board (inside the hall: painted, never lit)"),
    "ColdRoom": dict(kind="kiosk", w=1.2, h=0.35, field="#eef6ff", ink="#123a66", lit=True, glow="#e0f0ff",
                     lines=[("COLD ROOM", 0.50, 0.52, "heavy")], carrier="SM_Sign_CT_Kiosk_1m", where="over the cold-room door"),
    "LanternAlley": dict(kind="board", w=2.4, h=0.5, field="#2a3b2c", ink="#e9dcae", lines=[("LANTERN ALLEY", 0.46, 0.52, "serif")],
                         carrier="SM_Sign_CT_Board", where="alley A mouth: the party-goods wholesaler's painted board"),
    "MoonGate": dict(kind="band", w=6.0, h=0.9, field="#2a0f22", ink="#ffd2ea", lit=True, glow="#ff8fc8",
                     lines=[("MOON GATE BAKERY", 0.40, 0.40, "heavy"), ("BUNS  ·  CAKES  ·  EGG TARTS", 0.13, 0.80, "bold")],
                     carrier="SM_Sign_CT_Band_6m", where="W3 Canal band under the pink neon"),
    "WestCity": dict(kind="band", w=8.0, h=0.9, field="#d9d4c6", ink="#1e2a38", lit=False, glow=None,
                     lines=[("WEST CITY HARDWARE", 0.40, 0.40, "heavy"), ("TOOLS  ·  PAINT  ·  KEYS", 0.13, 0.80, "bold")],
                     carrier="SM_Sign_CT_Band_8m", where="W1 Canal (shut, gate down, sign off)"),
    # ------------------------------------------------------------------ Mott Street, the arcade, the Square
    "GoldenLuck": dict(kind="band", w=10.0, h=0.9, field="#0d0d12", ink="#ffe06a", sub="#7fe8ff", lit=True, glow="#ffe090",
                       lines=[("GOLDEN LUCK ELECTRONICS", 0.38, 0.40, "heavy"), ("PHONES  ·  CAMERAS  ·  REPAIRS", 0.13, 0.80, "bold")],
                       carrier="SM_Sign_CT_Band_10m", where="E1a Canal"),
    "LittleKite": dict(kind="band", w=6.0, h=0.9, field="#f7f2e6", ink="#2f6b4a", sub="#b04a6a", lit=True, glow="#fff0d8",
                     lines=[("LITTLE KITE CAFE", 0.40, 0.40, "heavy"), ("MILK TEA  ·  BUNS  ·  NOODLES", 0.13, 0.80, "bold")],
                     carrier="SM_Sign_CT_Band_6m", where="E1a Mott (lights the kitchen-roof gap)"),
    "CleverHands": dict(kind="kiosk", w=3.0, h=0.6, field="#20304a", ink="#f0e6cc", lit=True, glow="#e8e0c8",
                        lines=[("CLEVER HANDS TAILOR", 0.32, 0.40, "heavy"), ("ALTERATIONS  ·  HEMS", 0.15, 0.80, "bold")],
                        carrier="SM_Sign_CT_Kiosk_3m", where="E1a, Square side"),
    "PlumBlossom": dict(kind="arch", w=4.0, h=0.8, field="#0e3b34", ink="#e8fff4", lit=True, glow="#8affd0",
                        lines=[("PLUM BLOSSOM ARCADE", 0.40, 0.48, "heavy")], carrier="SM_Sign_CT_Arch", where="both arcade mouths"),
    "KioskWatch": dict(kind="kiosk", w=1.2, h=0.35, field="#f4f4f0", ink="#1a1a1a", lit=True, glow="#ffffff",
                       lines=[("WATCH REPAIR", 0.46, 0.52, "heavy")], carrier="SM_Sign_CT_Kiosk_1m", where="arcade kiosk"),
    "KioskKeys": dict(kind="kiosk", w=1.2, h=0.35, field="#f2c21a", ink="#1a1a1a", lit=True, glow="#ffe080",
                      lines=[("KEYS CUT", 0.50, 0.52, "heavy")], carrier="SM_Sign_CT_Kiosk_1m", where="arcade kiosk"),
    "KioskPhones": dict(kind="kiosk", w=1.2, h=0.35, field="#123a66", ink="#ffffff", lit=True, glow="#9cc8ff",
                        lines=[("PHONES", 0.50, 0.52, "heavy")], carrier="SM_Sign_CT_Kiosk_1m", where="arcade kiosk"),
    "KioskNeon": dict(kind="kiosk", w=1.2, h=0.35, field="#101018", ink="#7fe8ff", lit=True, glow="#7fe8ff",
                      lines=[("NEON SIGNS", 0.50, 0.52, "heavy")], carrier="SM_Sign_CT_Kiosk_1m", where="arcade kiosk"),
    "WillowBridge": dict(kind="band", w=8.0, h=0.9, field="#f4f6f8", ink="#14365c", lit=True, glow="#e8f2ff",
                      lines=[("WILLOW BRIDGE OPTICAL", 0.40, 0.40, "heavy"), ("EYE EXAMS  ·  FRAMES  ·  CONTACTS", 0.13, 0.80, "bold")],
                      carrier="SM_Sign_CT_Band_8m", where="E1b Canal"),
    "CranePavilion": dict(kind="band", w=10.0, h=0.9, field="#f3e9cf", ink="#8a6a1c", sub="#3a2a14", lit=True, glow="#ffe8b0",
                          lines=[("CRANE PAVILION BANQUET HALL", 0.38, 0.40, "serif"), ("WEDDINGS  ·  BANQUETS  ·  DIM SUM", 0.13, 0.80, "bold")],
                          carrier="SM_Sign_CT_Band_10m", where="E2 Square, over the red doors (gold and cream)"),
    "GoodWishes": dict(kind="band", w=8.0, h=0.9, field="#f6e24a", ink="#1d4a2a", sub="#8a2a14", lit=True, glow="#fff090",
                       lines=[("GOOD WISHES GROCERY", 0.40, 0.40, "heavy"), ("PRODUCE  ·  RICE  ·  SAUCES  ·  SNACKS", 0.13, 0.80, "bold")],
                       carrier="SM_Sign_CT_Band_8m", where="S3 Mott, over the fruit boxes"),
    "SevenStars": dict(kind="band", w=8.0, h=0.9, field="#16233f", ink="#ffffff", sub="#f2c21a", lit=True, glow="#c8d8ff",
                       lines=[("SEVEN STARS COACH", 0.40, 0.40, "heavy"), ("DAILY COACH  ·  TICKETS INSIDE", 0.13, 0.80, "bold")],
                       carrier="SM_Sign_CT_Band_8m", where="S3 Mott: an intercity bus ticket office (no towns, no prices)"),
    "QuickWire": dict(kind="band", w=6.0, h=0.9, field="#e6f0ea", ink="#0f5a3a", sub="#2a2a2a", lit=True, glow="#e0fff0",
                      lines=[("QUICK WIRE  ·  PHONES", 0.40, 0.40, "heavy"), ("MONEY TRANSFER  ·  PREPAID  ·  CASES", 0.13, 0.80, "bold")],
                      carrier="SM_Sign_CT_Band_6m", where="S3 Mott, next to the grocery"),
    "BigLight": dict(kind="board", w=2.4, h=0.5, field="#141418", ink="#7fe8ff", lines=[("BIG LIGHT SIGNS", 0.44, 0.52, "heavy")],
                     carrier="SM_Sign_CT_Board", where="the neon workshop's door board (the half-finished sign is neon geometry)"),
    # ------------------------------------------------------------------ paper, card and the street
    "ForRent": dict(kind="poster", w=0.6, h=0.42, field="#f4f1e8", ink="#b01c14",
                    lines=[("FOR RENT", 0.30, 0.34, "heavy"), ("SHOP  ·  INQUIRE INSIDE", 0.12, 0.72, "bold")],
                    carrier="SM_Sign_CT_Poster_A", where="upper windows (paper, no numbers)"),
    "ForLease": dict(kind="poster", w=0.6, h=0.42, field="#fbe94a", ink="#1a1a1a",
                     lines=[("FOR LEASE", 0.30, 0.40, "heavy"), ("RETAIL SPACE", 0.12, 0.74, "bold")],
                     carrier="SM_Sign_CT_Poster_A", where="vacant shop window (paper, no numbers)"),
    "OperaGala": dict(kind="poster", w=0.6, h=0.9, field="#f0d070", ink="#5a1408",
                      lines=[("OPERA GALA", 0.12, 0.18, "serif"), ("SPRING SUNSHINE", 0.065, 0.42, "heavy"),
                             ("TROUPE", 0.065, 0.52, "heavy"), ("ONE NIGHT ONLY", 0.045, 0.78, "bold")],
                      carrier="SM_Sign_CT_Poster_B", where="wheat-paste on walls (no faces; an invented troupe)"),
    "PlacardCDs": dict(kind="placard", w=0.36, h=0.24, field="#f6f4ee", ink="#151515", lines=[("CDs $5", 0.40, 0.50, "marker")],
                       carrier="SM_Sign_CT_Placard", where="vendor tables"),
    "PlacardUSB": dict(kind="placard", w=0.36, h=0.24, field="#f6f4ee", ink="#151515", lines=[("USB $10", 0.40, 0.50, "marker")],
                       carrier="SM_Sign_CT_Placard", where="vendor tables"),
    "PlacardBags": dict(kind="placard", w=0.36, h=0.24, field="#fff27a", ink="#151515", lines=[("BAGS $20", 0.40, 0.50, "marker")],
                        carrier="SM_Sign_CT_Placard", where="vendor tables"),
    "PlacardShades": dict(kind="placard", w=0.36, h=0.24, field="#f6f4ee", ink="#c01818", lines=[("SUNGLASSES $5", 0.26, 0.50, "marker")],
                          carrier="SM_Sign_CT_Placard", where="vendor tables"),
    "PlacardThree": dict(kind="placard", w=0.36, h=0.24, field="#ff9cc8", ink="#151515", lines=[("3 FOR $10", 0.36, 0.50, "marker")],
                         carrier="SM_Sign_CT_Placard", where="vendor tables"),
    "StreetCanal": dict(kind="street", w=0.9, h=0.2, field="#1b6b3a", ink="#ffffff", lines=[("CANAL ST", 0.56, 0.52, "street")],
                        carrier="SM_Sign_CT_StreetBlade", where="corners (plain green blade, no agency mark)"),
    "StreetMott": dict(kind="street", w=0.9, h=0.2, field="#1b6b3a", ink="#ffffff", lines=[("MOTT ST", 0.56, 0.52, "street")],
                       carrier="SM_Sign_CT_StreetBlade", where="corners (plain green blade, no agency mark)"),
}

# Exposed glass neon built as geometry (tubes along the letter outlines). colour: tube colour (sRGB).
NEON = {
    "MoonGateNeon": dict(text="MOON GATE", sub="BAKERY", w=4.2, h=1.1, colour="#ff3d9a", pan="#1a0c16", mesh="SM_Sign_CT_Neon_MoonGate",
                         where="W3 Canal, over the band: pink exposed neon on a pan"),
    "MahjongNeon": dict(text="MAHJONG", sub=None, w=1.8, h=0.5, colour="#55ff8a", pan=None, mesh="SM_Sign_CT_Neon_Mahjong",
                        where="N5 2F window neon (flickers)"),
    "SilverWaveNeon": dict(text="SILVER WAVE", sub="VIDEO", w=3.6, h=1.0, colour="#35e0ff", pan="#101418", mesh="SM_Sign_CT_Neon_SilverWave",
                           where="E2 Mott, over the dub room's roll-up: half dead (flickers)"),
    "BigLightNeon": dict(text="BIG LIGHT", sub=None, w=2.2, h=0.55, colour="#35e0ff", pan="#202024", mesh="SM_Sign_CT_Neon_BigLight",
                         where="the neon workshop's half-finished sign on the wall"),
}

# Words on painted or moulded geometry that carries no atlas face.
OTHER_TEXT = {
    "RooftopLetters": dict(text="GOLDEN TIDE MARKET", mesh="SM_Sign_CT_RooftopFrame",
                           where="open-face pan letters with warm white and gold neon on a steel frame on the market's north parapet"),
}

# Not drawn by this lane (decals, MAPS.md lane A-CT later or the decal kit): kept here so the list is complete.
DECAL_TEXT = {
    "Graffiti": ["VULTURES", "VLTR", "RULE", "INC"],
    "Stencil": ["MOTT ST →"],
}


def all_strings():
    out = []
    for k, f in FACES.items():
        out += [(k, t[0]) for t in f["lines"]]
    for k, n in NEON.items():
        out += [(k, n["text"])] + ([(k, n["sub"])] if n.get("sub") else [])
    for k, o in OTHER_TEXT.items():
        out.append((k, o["text"]))
    for k, ws in DECAL_TEXT.items():
        out += [(k, w) for w in ws]
    return out


def check_english():
    """Raise on any character outside ALLOWED (no CJK, no other scripts). Returns the number of strings checked."""
    bad = [(k, s, [c for c in s if c not in ALLOWED]) for k, s in all_strings() if any(c not in ALLOWED for c in s)]
    if bad:
        raise ValueError("non-English characters on signs: %s" % bad)
    return len(all_strings())


def business_names():
    """The invented business and place names (for the name searches, MAPS.md C1)."""
    names = {}
    for k, f in FACES.items():
        if f["kind"] in ("band", "blade", "kiosk", "arch") or k in ("LanternAlley", "BigLight", "OperaGala"):
            names[k] = f["lines"][0][0] if f["kind"] != "blade" else " ".join(t[0] for t in f["lines"])
    for k, n in NEON.items():
        names[k] = n["text"] + ((" " + n["sub"]) if n.get("sub") else "")
    return names


if __name__ == "__main__":
    print("strings checked:", check_english())
    for k, v in business_names().items():
        print("%-16s %s" % (k, v))
