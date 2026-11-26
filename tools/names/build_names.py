"""The approved name list for Canal Street (Level 2) and Midtown (Level 3): MAPS.md lane C, item C1.

Writes tools/names/names.json from the tables below. Every invented business, product, show or building name that
appears on a sign, screen, board or poster in the two new levels is listed with the web search that was run for it
(2026-11-26), what the search found, and the verdict. A name that collided with a real business, brand or trademark
in New York (or a well-known national one) is kept here as `retired`, with the invented name that replaces it; the
replacement was searched the same way.

    python3 tools/names/build_names.py      # writes tools/names/names.json
    python3 tools/names/check_names.py      # checks the art lists, the layouts and the designs against it

The method and its limits are in docs/unreal/maps/names.md (a web search is not a trademark clearance).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SEARCHED = "2026-11-26"

# (text on the sign, where, the query as run, what it found, verdict)
# verdict: "approved" (no collision found), "replaces <old>" (a new name, searched), "retired" (collided: do not use)

CANAL = [
    ("GOLD HITS RECORDS", "N1 ground band", '"Gold Hits" records store New York',
     "No store of that name. Nearest: Golden Hits, a short-lived basement record shop in Ridgewood (the New Jersey town, per its Patch page), closed.",
     "approved"),
    ("JADE TEAPOT", "N1 2F blade (with DIM SUM)", '"Jade Teapot" restaurant',
     "No restaurant of that name. Nearest: Jade (Singapore), Jade Teahouse (Portland OR), Teapot Vegetarian House: different names, none in New York.",
     "approved"),
    ("TWIN CARP JEWELRY", "N2 ground band", '"Twin Carp" jewelry',
     "No business; only carp and twin-fish pendant designs sold by various shops.", "approved"),
    ("SEA BREEZE TRAVEL", "N2 3F window", '"Sea Breeze Travel" New York',
     "Real travel agencies of the same name: SeaBreeze Travel (North Conway NH) and Seabreeze Travel Services (Virginia Beach). Not in New York, but the same name in the same trade.",
     "retired"),
    ("FAR SHORE TRAVEL", "N2 3F window", '"Far Shore Travel"',
     "No business. Nearest: Far & Away Adventures (BC, Canada), Shore Travel (New Zealand), Far & Wild Travel (UK).",
     "replaces SEA BREEZE TRAVEL"),
    ("EIGHT TREASURE BBQ", "N3 ground band", '"Eight Treasure" BBQ OR restaurant New York',
     "No restaurant of that name in New York (eight treasure is a dish name).", "approved"),
    ("SPRING PINE HERBS & GINSENG", "N4 ground band", '"Spring Pine" herbs ginseng',
     "No shop of that name. A ginseng product line sold as Pine Brand exists; the shop name shares only the word pine and the band shows no product mark.",
     "approved"),
    ("LONG LIFE NOODLE HOUSE", "N5 ground band", '"Long Life Noodle House"',
     "No business of that name. Nearest: Long Life Noodle Company (San Francisco, Palo Alto), a different name, not in New York.",
     "approved"),
    ("SUNNY DAY LAUNDROMAT", "N6 ground band", '"Sunny Day Laundromat"',
     "No business of that name. Nearest: Sunshine Laundromat (Greenpoint, Brooklyn), My Sunny Laundry (Florida): different names.",
     "approved"),
    ("BRIGHT MOON HOTEL", "N6 four-storey blade", '"Bright Moon Hotel" New York',
     "No hotel of that name, but The Historic Blue Moon Hotel is at 100 Orchard St on the Lower East Side, a few blocks from Canal St: a blade reading BRIGHT MOON HOTEL there is a look-alike.",
     "retired"),
    ("HARBOR STAR HOTEL", "N6 four-storey blade", '"Harbor Star Hotel"',
     "No hotel of that name. Nearest: Harbor Court Hotel (San Francisco). Two earlier candidates were dropped: Nine Bridges (a well-known golf club brand) and East Wind (Eastwind Hotel, Catskills NY).",
     "replaces BRIGHT MOON HOTEL"),
    ("GOLDEN TIDE MARKET", "the market band and rooftop letters", '"Golden Tide Market" OR "Golden Tide" supermarket New York',
     "No store of that name.", "approved"),
    ("LANTERN ALLEY", "alley A painted board", '"Lantern Alley" New York',
     "No place or business of that name (only antique lantern listings).", "approved"),
    ("MOON GATE BAKERY", "W3 band and pink neon", '"Moon Gate Bakery"',
     "No bakery of that name. Nearest: Moon Bakery (Salt Lake City, Calgary), Day Moon Bakery (San Francisco), Golden Gate Bakery (San Francisco).",
     "approved"),
    ("WEST CITY HARDWARE", "W1 band (unlit)", '"West City Hardware"',
     "No store of that name. Nearest: West Hardware Co. (West, Texas), Westlake Ace Hardware.", "approved"),
    ("GOLDEN LUCK ELECTRONICS", "E1a Canal band", '"Golden Luck" electronics New York',
     "No retailer of that name; an importer named Goldenluck Imp Exp appears in shipping records (textiles, not a shop or a consumer mark).",
     "approved"),
    ("LILY CAFE", "E1a Mott band", '"Lily Cafe" New York Manhattan',
     "Cafe Lily is a restaurant at 42 Avenue O, Bensonhurst, Brooklyn; Lily's Restaurant is at 501 Lexington Ave, Midtown East. The same name in the same trade in New York.",
     "retired"),
    ("LITTLE KITE CAFE", "E1a Mott band", '"Little Kite Cafe" OR "Little Kite" cafe New York',
     "No cafe of that name. Nearest: Box Kite (St. Marks Pl, East Village), permanently closed, a different name.",
     "replaces LILY CAFE"),
    ("CLEVER HANDS TAILOR", "E1a Square-side kiosk", '"Clever Hands" tailor',
     "No business of that name.", "approved"),
    ("PLUM BLOSSOM ARCADE", "both arcade arches", '"Plum Blossom Arcade" OR "Plum Blossom" mall Chinatown New York',
     "No arcade or mall of that name. Real Chinatown malls are East Broadway Mall and the like: different names.", "approved"),
    ("CLEAR VIEW OPTICAL", "E1b Canal band", '"Clear View Optical" OR "Clearview Optical" New York',
     "Clear View Optical is a registered optometrist at 707 Burke Ave, the Bronx (NPI registry); Clearview Eye Center is in Astoria; Sterling Optical is also listed as Clearview Optics (Garden City NY).",
     "retired"),
    ("WILLOW BRIDGE OPTICAL", "E1b Canal band", '"Willow Bridge Optical" and "Willow Bridge" optical OR optician OR eyewear New York',
     "No business of that name; the words appear only separately (a frame model named Willow, Bridge Opticians in Staten Island).",
     "replaces CLEAR VIEW OPTICAL"),
    ("CRANE PAVILION BANQUET HALL", "E2 Square band", '"Crane Pavilion" banquet hall OR restaurant',
     "No venue of that name. Nearest: Crane Club (a New York restaurant), Craneway Pavilion (Richmond CA), The Crane (Barbados): different names.",
     "approved"),
    ("GOOD WISHES GROCERY", "S3 Mott band", '"Good Wishes" grocery OR market New York',
     "No store of that name.", "approved"),
    ("SEVEN STARS COACH", "S3 Mott band", '"Seven Stars" bus OR coach Chinatown New York',
     "No operator of that name. The real Chinatown bus lines found (Lucky Star, Fung Wah) have different names.", "approved"),
    ("QUICK WIRE", "S3 Mott band (phones, money transfer)", '"Quick Wire" money transfer',
     "No service of that name.", "approved"),
    ("BIG LIGHT SIGNS", "the neon workshop's board and its half-finished neon", '"Big Light" neon signs shop New York',
     "No shop of that name. Real New York neon shops found: Let There Be Neon, Glo Studio, Mondo Neon.", "approved"),
    ("SILVER WAVE VIDEO", "E2 Mott neon over the dub room", '"Silver Wave" video store OR "Silver Wave Video"',
     "No store of that name. Nearest: Silver Lake Video (Everett WA, closed), Silver Screen Video (WA).", "approved"),
    ("SPRING SUNSHINE TROUPE", "OPERA GALA wheat-paste poster", '"Spring Sunshine" opera troupe',
     "No troupe of that name.", "approved"),
]

MIDTOWN = [
    ("ORBELLE", "E1 screen (perfume)", '"Orbelle" perfume OR fragrance brand',
     "Orebella, a perfume brand launched in 2024 and sold nationally (Ulta, Selfridges): the same trade and nearly the same word.",
     "retired"),
    ("MIRAVESSE", "E1 screen (perfume, Eau de Nuit)", '"Miravesse" perfume OR brand',
     "No brand of that name. Nearest: Miraj, Marylise Mirabelli, Miris: different names.", "replaces ORBELLE"),
    ("NORTHBOUND AIRWAYS", "E1 screen (an airline)", '"Northbound Airways" OR "Northbound Air" airline',
     "No airline of that name. Nearest: Northern Pacific Airways (now New Pacific Airlines): a different name.", "approved"),
    ("KESTREL MOBILE", "E2a screen (a phone carrier)", '"Kestrel Mobile" phone carrier OR company',
     "No carrier of that name.", "approved"),
    ("BRASS & BUN", "E2b screen (a burger bar)", '"Brass & Bun" OR "Brass and Bun" burger',
     "No restaurant of that name. Nearest: Brass Tap, Brass Monkey (Milwaukee), Meat & Bun (UK).", "approved"),
    ("THE ALDERWAY THEATRE", "E3 screen and the east marquee", '"Alderway Theatre" OR "Alderway Theater"',
     "No venue of that name, but Alleyway Theatre (Buffalo, New York) differs by two letters in the same trade, in the same state.",
     "retired"),
    ("THE MERIDALE THEATRE", "E3 screen and the east marquee", '"Meridale Theatre" OR "Meridale Theater"',
     "No venue of that name (Meridale is a hamlet upstate; no theatre or business named for it was found). Nearest: Meridian Theatres (Ottawa), Meadowvale Theatre (Mississauga).",
     "replaces THE ALDERWAY THEATRE"),
    ("NIGHT SHIFT", "E3 screen (the musical's title)", '"Night Shift" musical Broadway OR off-Broadway',
     "No musical of that name found, but Night Shift is a well-known 1982 studio film; a show title that is also a famous film reads as an adaptation.",
     "retired"),
    ("LAMPLIGHT AVENUE", "E3 screen (the musical's title)", '"Lamplight Avenue" musical OR show',
     "No show of that name. Nearest: Lamplight (a play), The Lamplighter (a musical), Lamplighters Music Theatre: different titles.",
     "replaces NIGHT SHIFT"),
    ("VESPERLINE CRUISES", "E3 screen (a cruise line)", '"Vesperline" cruises OR cruise line',
     "No cruise line of that name.", "approved"),
    ("QUILLON", "N1 screen (watches)", '"Quillon" watches brand',
     "No brand of that name, but Aquilon & Co is a French watch brand: one letter apart in the same trade.", "retired"),
    ("HOROVAN", "N1 screen (watches)", '"Horovan" watches OR watch brand',
     "No brand of that name. Nearest: Horon, Horage, Horizon (watch brands): different names.", "replaces QUILLON"),
    ("TAMSIN GRAY", "N1 screen (a fashion label)", '"Tamsin Gray" fashion OR designer',
     "No designer of that name found, but it is a full personal name (real people carry it) and the game allows no real people but the star.",
     "retired"),
    ("NORTHWEFT", "N1 screen (a fashion label, fall collection)", '"Northweft" fashion OR clothing',
     "No label of that name. An earlier candidate, Vantelle, was dropped (Vontelle sells wholesale on Faire).",
     "replaces TAMSIN GRAY"),
    ("HALCYON SODA", "N1 screen (a soft drink)", '"Halcyon Soda" OR "Halcyon" soda drink brand',
     "No soda of that name, but Halcyon, LLC holds trademarks for mineral and aerated waters and soft drinks: the same goods.",
     "retired"),
    ("FIZZWICK SODA", "N1 screen (a soft drink)", '"Fizzwick" soda OR drink',
     "No product of that name (a game's fictional drink is called Fizz; a different word).", "replaces HALCYON SODA"),
    ("DUSKLINE TOURS", "S1 screen (a bus tour)", '"Duskline Tours" OR "Duskline" tour company',
     "No company of that name.", "approved"),
    ("MARLOWE & FINCH", "C's roof billboard (a department store)", '"Marlowe & Finch" OR "Marlowe and Finch"',
     "No business of that spelling. Marlow & Finch (no e) appears only on unfinished template sites as a UK recruitment firm, not a store, not in New York.",
     "approved"),
    ("SEVENTH AV SOUVENIRS", "C ground floor band", '"Seventh Avenue Souvenirs" OR "Seventh Av Souvenirs" OR "7th Avenue Souvenirs" New York',
     "No shop of that name. The real Seventh Avenue shops are Souvenirs and Gifts (730 Seventh Ave) and NYC Mega Mart: different names.",
     "approved"),
    ("MIDTOWN SLICE", "C ground floor band", '"Midtown Slice" pizza New York',
     "Slice Midtown is a real New York pizza listing (the same words reversed, the same trade, the same neighbourhood).",
     "retired"),
    ("SLICE OF SEVENTH", "C ground floor band", '"Slice of Seventh" pizza',
     "No pizzeria of that name. Nearest: 7th Heaven Pizza (Harlem), a different name.", "replaces MIDTOWN SLICE"),
    ("46TH ST CAMERA & ELECTRONICS", "C ground floor band", '"46th Street Camera" OR "46th St Camera" electronics New York',
     "No shop of that name, but 47th Street Photo (famously asked for as 47th Street Camera) was the city's best-known camera store, and H and B Digital is at 29 W 46th St: a look-alike.",
     "retired"),
    ("SHUTTERBOX CAMERA & ELECTRONICS", "C ground floor band", '"Shutterbox" camera store OR electronics',
     "No store of that name. Nearest: The Shutterbug (a camera shop), ShotBox (a photo kit).", "replaces 46TH ST CAMERA & ELECTRONICS"),
    ("LANTERN SAVINGS", "D ground floor, the closed bank lobby", '"Lantern Savings" bank',
     "No bank of that name, but Lantern by SoFi is a national savings-account marketplace: the same field and the same lead word.",
     "retired"),
    ("BELLHAVEN SAVINGS", "D ground floor, the closed bank lobby", '"Bellhaven Savings" bank',
     "No bank of that name. Belhaven (one L) is a town in North Carolina with branches of other banks; Belmont Savings Bank (MA) and Bell Savings Bank (PA) are different names.",
     "replaces LANTERN SAVINGS"),
    ("HOTEL CASTELLANE", "the east hotel canopy", '"Hotel Castellane" OR "Castellane Hotel" New York',
     "No hotel of that name in New York.", "approved"),
    ("BRANNIGAN'S CHOP HOUSE", "W 46 St south band (a steakhouse)", '"Brannigan\'s Chop House" OR "Brannigan\'s" steakhouse New York',
     "No restaurant of that name. Real nearby steakhouses: Gallagher's, Brooklyn Chop House Times Square: different names.", "approved"),
    ("CORNER CHEMISTS", "W 46 St south band (a pharmacy)", '"Corner Chemists" OR "Corner Chemist" pharmacy New York',
     "Corner Chemists Pharmacy LLC is a real retail pharmacy at 11 Henry St, Manhattan (NPI registry).", "retired"),
    ("ASHBY & CROSS PHARMACY", "W 46 St south band (a pharmacy)", '"Ashby & Cross" OR "Ashby and Cross" pharmacy OR chemists',
     "No pharmacy of that name. Nearest: Ashby Pharmacy (two in England), a different name, not in the United States. An earlier candidate, Brightmore, was clear too but repeated Brightwire on the same level.",
     "replaces CORNER CHEMISTS"),
    ("HALVORSEN BUILDING", "A's parapet, incised", '"Halvorsen Building" New York', "No building of that name.", "approved"),
    ("CORVIN HALL", "C's cornice, incised", '"Corvin Hall" New York',
     "No building of that name. Nearest: Corinthian Hall (Rochester, demolished), Carman Hall (Columbia).", "approved"),
    ("KESSLER & ROTH SCAFFOLD", "the scaffold tower's board", '"Kessler & Roth" OR "Kessler and Roth" scaffold OR construction',
     "No firm of that name. Roth Geruste is a Swiss scaffolding firm (a different name, not in the United States).", "approved"),
    ("BRIGHTWIRE EVENTS", "the production truck's side", '"Brightwire Events" OR "Brightwire" event production staging lighting',
     "No firm of that name. Nearest: Bright Event Productions (Nashville), a different name.", "approved"),
    ("CITY CROSSTOWN", "the stalled bus's destination sign", '"City Crosstown" bus OR transit operator',
     "No operator of that name (crosstown is a generic route word).", "approved"),
    ("THE PERCH", "D's closed rooftop lounge, unlit neon", '"The Perch" rooftop bar OR lounge New York Manhattan',
     "The Perch is the 23rd-floor rooftop bar of a Brooklyn hotel (The Livingston): the same name and trade in New York.",
     "retired"),
    ("THE LOFTLARK", "D's closed rooftop lounge, unlit neon", '"Loftlark" bar OR lounge',
     "No venue of that name (only Loft Lounge bars in Perth, Birmingham UK, Atlanta).", "replaces THE PERCH"),
]

# Words that are not names: generic trade words, labels, slogans, real places, the story's own marks.
GENERIC = {
    "chinatown": ["MARKET", "FRESH FISH", "FRUIT", "VEGETABLES", "DRY GOODS", "TOFU", "ROAST MEAT", "COLD ROOM", "WATCH REPAIR",
                  "KEYS CUT", "PHONES", "NEON SIGNS", "MAHJONG", "DIM SUM", "HOTEL", "BAKERY", "VIDEO", "OPERA GALA", "ONE NIGHT ONLY",
                  "FOR RENT", "FOR LEASE", "CDs $5", "USB $10", "BAGS $20", "SUNGLASSES $5", "3 FOR $10",
                  "the sub-lines under each band (CDs · VINYL · KARAOKE, ROAST DUCK · ROAST PORK · SOY CHICKEN, ...)"],
    "midtown": ["WORLD PREMIERE", "MIDNIGHT", "NO SIGNAL", "STAND BY", "PRESENTS", "Eau de Nuit", "Fly the late one",
                "Five bars, five boroughs", "Burgers till four", "a new musical", "watches", "fall collection",
                "The city after dark", "The holiday floor is open", "SIDEWALK SHEDS · SCAFFOLD · HOISTS",
                "STAGING · LIGHTING · SCREENS", "ROOF DOOR / KEEP CLOSED", "MACHINE ROOM / AUTHORIZED ONLY",
                "DANGER / HIGH VOLTAGE", "TANK 2 / DRINKING WATER",
                "SQUARE CLOSED TONIGHT FOR A PREMIERE", "CROSSTOWN TRAFFIC HEAVY", "FORECAST: CLEAR, 41°",
                "HOT DOGS · PRETZELS", "SODA · WATER · COFFEE", "STAGE LEFT", "BROADCAST BOOTH / CREW ONLY"],
}
REAL_PLACES = ["CHINATOWN", "MANHATTAN", "CANAL ST", "MOTT ST", "MIDTOWN", "SEVENTH AV", "W 46 ST", "BROADWAY", "NEW YORK",
               "the bridge east of Canal St (an unnamed silhouette)"]
STORY_MARKS = ["IPX (the owner's real mark, the only one)", "VULTURES", "VLTR", "RULE", "INC"]


def rows(table, level):
    out = []
    for text, where, query, found, verdict in table:
        if verdict == "retired":
            status, replaces = "retired", None
        elif verdict.startswith("replaces "):
            status, replaces = "approved", verdict[len("replaces "):]
        else:
            status, replaces = "approved", None
        out.append(dict(level=level, text=text, where=where, query=query, found=found, status=status,
                        replaces=replaces, searched=SEARCHED))
    for r in out:
        if r["status"] == "retired":
            r["replacedBy"] = next(x["text"] for x in out if x["replaces"] == r["text"])
    return out


def build():
    names = rows(CANAL, "chinatown") + rows(MIDTOWN, "midtown")
    for n in names:
        bad = [c for c in n["text"] if not (32 <= ord(c) < 127)]
        assert not bad, (n["text"], bad)
    data = dict(
        about="Approved invented names for Canal Street and Midtown (MAPS.md lane C, C1). See docs/unreal/maps/names.md.",
        searched=SEARCHED,
        signedOff=None,
        names=names,
        generic=GENERIC, realPlaces=REAL_PLACES, storyMarks=STORY_MARKS)
    path = os.path.join(HERE, "names.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    a = sum(1 for n in names if n["status"] == "approved")
    r = sum(1 for n in names if n["status"] == "retired")
    print("%s: %d approved, %d retired" % (os.path.relpath(path), a, r))


if __name__ == "__main__":
    build()
