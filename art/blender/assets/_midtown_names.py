"""Midtown (Level 3) words: every invented name on a screen, billboard, sign or label of the `midtown` family, in one place.

The rules (MAPS.md 5, midtown.md 12.1, the owner's answers of 2026-11-26):
- Invented names only. No real brand, logo, product, show, theatre, operator or trade dress. IPX is the only real mark
  (the owner's), drawn from signs.ipx_master. Real place names are fine (TIMES SQ is not used; SEVENTH AV, W 46 ST,
  MIDTOWN, BROADWAY are).
- English only, plain type: ASCII letters, digits and punctuation, plus the middle dot and the degree sign.
- No phone numbers, no web addresses.
- Every name below is still to be searched against real New York businesses and marks before its art is final
  (MAPS.md lane C, item C1). A name found to be real is replaced here, never kept.

    venv/bin/python art/blender/assets/_midtown_names.py      # prints the list and checks the characters
"""
import re

ALLOWED = re.compile(r"^[A-Za-z0-9 .,:;'&!?/()\-+·°]*$")

# ---------------------------------------------------------------------------------------------- the LED screens
# Slides of the screens of midtown.md 12.2. `screen`: the screens that show it; `size_m`: the screen it is drawn for (a
# slide is drawn at the screen's own aspect and stored squeezed into its atlas cell: the screen's 0..1 UVs map the
# cell back to the right shape). `kind`: ad, takeover, state (NO SIGNAL / STAND BY), ipx.
# Colours: no red field anywhere (readability against the oxblood Goons, midtown.md 11.1); the oxblood mark is small.
SLIDES = {
    "G1_Takeover": dict(screen=["G1"], size_m=(16.0, 9.0), kind="takeover",
                        lines=["WORLD PREMIERE", "MIDNIGHT"], mark="VLTR", clock=True,
                        note="the Vultures' takeover until reel8 is secured: white on black, small oxblood VLTR mark, a "
                             "clock box where the material composites the countdown digits (T_MT_Digits)"),
    "G1_NoSignal": dict(screen=["G1"], size_m=(16.0, 9.0), kind="state", lines=["NO SIGNAL"],
                        note="after reel8 is secured (0.4 s glitch first): black with a dim grey line"),
    "G1_StandBy": dict(screen=["G1"], size_m=(16.0, 9.0), kind="state", lines=["STAND BY"],
                       note="when the countdown reaches 0:00 before reel8 (no gameplay effect)"),
    "IPX_Presents": dict(screen=["G1", "N1"], size_m=(16.0, 9.0), kind="ipx", lines=["PRESENTS"],
                         note="all three reels in: 6 s on every hero screen (the IPX mark + PRESENTS)"),
    "IPX_Presents_E1": dict(screen=["E1"], size_m=(24.0, 18.0), kind="ipx", lines=["PRESENTS"], note="the same for E1's 4:3"),
    "IPX_Presents_E3": dict(screen=["E3"], size_m=(20.0, 12.0), kind="ipx", lines=["PRESENTS"], note="the same for E3's 5:3"),
    "E1_Miravesse": dict(screen=["E1"], size_m=(24.0, 18.0), kind="ad", lines=["MIRAVESSE", "Eau de Nuit"],
                       palette=("#0b0f2a", "#3a2a6e", "#f4ecff", "#c9b8ff"), art="bottle", note="perfume"),
    "E1_Northbound": dict(screen=["E1"], size_m=(24.0, 18.0), kind="ad", font="fjalla", lines=["NORTHBOUND AIRWAYS", "Fly the late one"],
                          palette=("#06142c", "#1d4f8c", "#ffffff", "#9fd0ff"), art="contrail", note="an airline"),
    "E2a_Kestrel": dict(screen=["E2a"], size_m=(8.0, 20.0), kind="ad", font="archivo", lines=["KESTREL", "MOBILE", "Five bars,", "five boroughs"],
                        palette=("#04201c", "#0f6b5a", "#ffffff", "#8ff0d8"), art="bars", note="a phone carrier"),
    "E2b_BrassBun": dict(screen=["E2b"], size_m=(8.0, 20.0), kind="ad", font="slab", lines=["BRASS", "& BUN", "Burgers", "till four"],
                         palette=("#1e1406", "#8a5a12", "#fff3d6", "#ffd27a"), art="bun", note="a burger bar"),
    "E3_Meridale": dict(screen=["E3"], size_m=(20.0, 12.0), kind="ad",
                        lines=["THE MERIDALE THEATRE presents", "LAMPLIGHT AVENUE", "a new musical"],
                        palette=("#0a0a12", "#2b2f5a", "#f6f1e6", "#d8c48a"), art="spot", note="a theatre's show"),
    "E3_Vesperline": dict(screen=["E3"], size_m=(20.0, 12.0), kind="ad", font="anton", lines=["VESPERLINE", "CRUISES"],
                          palette=("#07122a", "#1f5f8f", "#ffffff", "#ffd9a0"), art="horizon", note="a cruise line"),
    "N1_Horovan": dict(screen=["N1"], size_m=(14.0, 8.0), kind="ad", lines=["HOROVAN", "watches"],
                       palette=("#08090c", "#30343c", "#f2f2f2", "#b8c0cc"), art="dial", note="a watchmaker"),
    "N1_Northweft": dict(screen=["N1"], size_m=(14.0, 8.0), kind="ad", lines=["NORTHWEFT", "fall collection"],
                          palette=("#14121a", "#5a5466", "#ffffff", "#d9d2e6"), art="stripes", note="a fashion label"),
    "N1_Fizzwick": dict(screen=["N1"], size_m=(14.0, 8.0), kind="ad", font="passion", lines=["FIZZWICK", "SODA"],
                       palette=("#032a3a", "#0aa0b8", "#ffffff", "#c8fbff"), art="bubbles", note="a soft drink"),
    "S1_Duskline": dict(screen=["S1"], size_m=(12.0, 6.0), kind="ad", font="bebas", lines=["DUSKLINE TOURS", "The city after dark"],
                        palette=("#0c0a1e", "#45306e", "#ffffff", "#ffc48a"), art="skyline", note="a bus tour"),
}

# the ticker band on the theatre (midtown.md 12.2): one strip panned at 0.35 m/s
TICKER = ["SQUARE CLOSED TONIGHT FOR A PREMIERE", "CROSSTOWN TRAFFIC HEAVY", "FORECAST: CLEAR, 41°"]

# the countdown digits (T_MT_Digits, 512 x 64, 16 cells of 32 x 64 px): index = cell
DIGITS = list("0123456789:") + [" ", "-", "", "", ""]

# ------------------------------------------------------------------------------------------------- printed faces
# Sign_MT_Atlas1: lightbox, storefront, plaque and label faces (midtown.md 12.2 C1 and 12.4). kind sets the density:
# billboard 128 px/m, band 256 px/m, plaque and label 512 px/m. lit: a lightbox (emissive at night).
FACES = {
    "C1_MarloweFinch": dict(kind="billboard", w=16.0, h=8.0, lit=True, carrier="SM_Roof_BillboardFrame_16x8",
                            lines=["MARLOWE & FINCH", "The holiday floor is open"], field="#f3efe6", ink="#14213d", sub="#7a5c2e",
                            where="C's roof billboard, facing east (a department store, invented)"),
    "Band_SeventhAvSouvenirs": dict(kind="band", w=8.0, h=0.9, lit=True, carrier="storefront band (facade lane)",
                                    lines=["SEVENTH AV SOUVENIRS"], field="#10233f", ink="#ffd23a", where="C ground floor", font="bebas"),
    "Band_SliceOfSeventh": dict(kind="band", w=6.0, h=0.9, lit=True, carrier="storefront band (facade lane)",
                              lines=["SLICE OF SEVENTH"], field="#f4f0e4", ink="#1f5a2c", where="C ground floor (no red field)", font="passion"),
    "Band_Shutterbox": dict(kind="band", w=10.0, h=0.9, lit=True, carrier="storefront band (facade lane)",
                              lines=["SHUTTERBOX CAMERA & ELECTRONICS"], field="#0c0c0e", ink="#f2f2f2", where="D ground floor", font="archivo"),
    "Band_Bellhaven": dict(kind="band", w=8.0, h=0.9, lit=False, carrier="bank lobby fascia (facade lane)",
                                lines=["BELLHAVEN SAVINGS"], field="#d9d4c8", ink="#2a2a2a", where="D ground floor, closed bank lobby", font="serif"),
    "Band_HotelCastellane": dict(kind="band", w=8.0, h=0.9, lit=True, carrier="canopy fascia (facade lane)",
                                 lines=["HOTEL CASTELLANE"], field="#151515", ink="#e8d39a", font="serif", where="east hotel canopy"),
    "Band_MeridaleTheatre": dict(kind="band", w=12.0, h=1.2, lit=True, carrier="marquee name band (facade lane)",
                                 lines=["THE MERIDALE THEATRE"], field="#141018", ink="#f6e7b8", font="serif", where="east marquee"),
    "Band_BranniganChopHouse": dict(kind="band", w=8.0, h=0.9, lit=True, carrier="storefront band (facade lane)",
                                    lines=["BRANNIGAN'S CHOP HOUSE"], field="#1a2a1e", ink="#efe2c0", font="slab", where="W 46 St south"),
    "Band_AshbyCross": dict(kind="band", w=7.0, h=0.9, lit=True, carrier="storefront band (facade lane)",
                                lines=["ASHBY & CROSS PHARMACY"], field="#f2f6f8", ink="#0b5c8a", where="W 46 St south", font="fjalla"),
    "Plaque_Halvorsen": dict(kind="plaque", w=6.0, h=0.6, lit=False, carrier="SM_Roof_NamePanel_6m",
                             lines=["HALVORSEN BUILDING"], field="#b9ae98", ink="#3a3328", font="serif", carved=True,
                             where="A's parapet, street face (cast stone, incised)"),
    "Plaque_Corvin": dict(kind="plaque", w=6.0, h=0.6, lit=False, carrier="SM_Roof_NamePanel_6m",
                          lines=["CORVIN HALL"], field="#a99d88", ink="#332c22", font="serif", carved=True,
                          where="C's cornice (cast stone, incised)"),
    "Board_KesslerRoth": dict(kind="plaque", w=2.4, h=1.2, lit=False, carrier="SM_Scaf_Sign",
                              lines=["KESSLER & ROTH", "SCAFFOLD", "SIDEWALK SHEDS · SCAFFOLD · HOISTS"],
                              field="#f2c418", ink="#141414", where="the scaffold tower (a contractor, invented; no phone)"),
    "Panel_Brightwire": dict(kind="band", w=7.0, h=1.4, lit=False, carrier="production truck side (vehicles lane)",
                             lines=["BRIGHTWIRE EVENTS", "STAGING · LIGHTING · SCREENS"], field="#1c1c22", ink="#f0f0f0",
                             sub="#7fd0ff", where="the production truck (VLTR is sprayed over it as a decal)"),
    "Panel_CityCrosstown": dict(kind="band", w=3.2, h=0.5, lit=True, carrier="city bus destination sign (vehicles lane)",
                                lines=["CITY CROSSTOWN"], field="#05070a", ink="#ffb020", where="the stalled bus (no real livery)"),
    "Label_RoofDoor": dict(kind="label", w=0.40, h=0.28, lit=False, carrier="SM_Roof_Bulkhead_4x4 door",
                           lines=["ROOF DOOR", "KEEP CLOSED"], field="#f4f4f0", ink="#b01010", where="bulkhead doors"),
    "Label_MachineRoom": dict(kind="label", w=0.40, h=0.28, lit=False, carrier="SM_Roof_MachineRoom_6x6 door",
                              lines=["MACHINE ROOM", "AUTHORIZED ONLY"], field="#f4f4f0", ink="#141414", where="machine room door"),
    "Label_HighVoltage": dict(kind="label", w=0.36, h=0.24, lit=False, carrier="SM_Roof_HVAC_RTU_L panel",
                              lines=["DANGER", "HIGH VOLTAGE"], field="#f2c418", ink="#141414", where="HVAC and gantry cabinets"),
    "Label_TankNumber": dict(kind="label", w=0.50, h=0.30, lit=False, carrier="SM_Roof_WaterTank_* staves",
                             lines=["TANK 2", "DRINKING WATER"], field="#2a2522", ink="#e8e2d6", where="the water tanks (stencil)"),
}

# marks that are not names of a business
MARKS = {"VLTR": "the Vultures' tag (story, invented), oxblood on the takeover slide", "IPX": "the owner's real mark (allowed)"}


def all_strings():
    out = []
    for k, s in SLIDES.items():
        out += s["lines"]
    out += TICKER
    out += [d for d in DIGITS if d]
    for k, f in FACES.items():
        out += f["lines"]
    out += list(MARKS)
    return out


def check_english():
    """Every string is plain English type. Returns the number of strings checked; raises on any other character."""
    bad = [s for s in all_strings() if not ALLOWED.match(s)]
    if bad:
        raise ValueError("non-English characters in Midtown strings: %r" % bad)
    return len(all_strings())


def business_names():
    """The invented names (businesses, products, shows, operators) to be searched (MAPS.md C1)."""
    return sorted({
        "MIRAVESSE", "NORTHBOUND AIRWAYS", "KESTREL MOBILE", "BRASS & BUN", "THE MERIDALE THEATRE", "LAMPLIGHT AVENUE (a musical)",
        "VESPERLINE CRUISES", "HOROVAN", "NORTHWEFT", "FIZZWICK SODA", "DUSKLINE TOURS", "MARLOWE & FINCH",
        "SEVENTH AV SOUVENIRS", "SLICE OF SEVENTH", "SHUTTERBOX CAMERA & ELECTRONICS", "BELLHAVEN SAVINGS", "HOTEL CASTELLANE",
        "BRANNIGAN'S CHOP HOUSE", "ASHBY & CROSS PHARMACY", "HALVORSEN BUILDING", "CORVIN HALL", "KESSLER & ROTH SCAFFOLD",
        "BRIGHTWIRE EVENTS", "CITY CROSSTOWN", "VLTR (the Vultures' tag)",
        "THE LOFTLARK (D's closed roof lounge: unlit neon, built by the square lane, listed here so the search covers it)"})


if __name__ == "__main__":
    n = check_english()
    print("%d strings, English only: OK" % n)
    for b in business_names():
        print("  " + b)
