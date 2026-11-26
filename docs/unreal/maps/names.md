# Sign and screen names for Canal Street and Midtown (approved list, for the owner's sign-off)

Status: **searched 2026-11-26, waiting for the owner's sign-off.** This is MAPS.md lane C, item C1: every invented name
that appears on a sign, screen, board or poster in Level 2 (Canal Street) and Level 3 (Midtown). Each name was searched
on the web to check that it is not a real business, brand or trademark in New York, or a well-known national one. The
ones that collided are replaced with new invented names, and each replacement was searched the same way. Canal Street
is in English only, as the owner asked (DECISIONS.md 2026-11-26 ~02:00): no Chinese characters anywhere.

The list as data is `tools/names/names.json` (written by `tools/names/build_names.py`, which holds every query and
finding). `python3 tools/names/check_names.py` checks the art lists, the level layouts, the generated level files and
the designs against it (section 7).

---

## 1. For the owner

- **Canal Street: 25 names approved, 4 replaced.** **Midtown: 25 names approved, 11 replaced.** The
  tables in sections 3 and 4 are the whole list; the replaced ones are at the end of each.
- **What you are asked:** approve the list as it stands, or strike any name you do not like (a struck name is replaced
  by a new invented one, searched the same way, before the sign art is final).
- **What this check is and is not.** It is a web search of each name as written, by a person who knows what to look
  for (section 2). It is not a legal trademark clearance. The screen ads in Midtown (a perfume, an airline, a phone
  carrier, a soda, watches, a cruise line, a fashion label) are the most exposed, because they look like national
  advertising; a search of the US trademark register for those seven before release is recommended (section 8).

**Sign-off:** _not yet signed_. When the owner approves, the lead records it in DECISIONS.md and sets `signedOff` in
`tools/names/build_names.py`.

---

## 2. How the names were checked

**The rules** (MAPS.md 5, ART_BIBLE 5.7, chinatown.md 13.3, midtown.md 12.1):

- Every name on a sign or screen is invented. IPX is the only real mark in the game. No real people but the star.
- Canal Street is **English only**: no Chinese characters on any sign, board, poster, lantern, door or screen. It reads
  as Chinatown through its architecture, lanterns, the market and its produce, the awnings, the sign style and the
  English shop names. Midtown is English only as well.
- No phone numbers, no web addresses, no real prices of real routes.
- Real place names are allowed (section 6). The tone of the game holds: no slurs, no stereotypes, nothing a Chinatown
  resident would find mocking (section 5).

**The search.** One web search per name on 2026-11-26, with the name in quotes, its trade, and "New York" where that
helps (the exact query for every name is in section 9). A second search was run when the first found something close.

**What counts as a collision**, and the name is replaced:

1. A real business or mark with the **same name in the same trade**, anywhere in New York, or a national brand.
   *Example:* a real Manhattan pharmacy called Corner Chemists.
2. A **look-alike**: one or two letters apart, or the same words reordered, in the same trade, near where the sign
   stands or nationally. *Example:* QUILLON watches next to Aquilon & Co watches; MIDTOWN SLICE next to a real Slice
   Midtown.
3. The **same name and trade** outside New York, when it is a working business (a sign in the game would show its
   exact name). *Example:* real travel agencies called SeaBreeze Travel.
4. A **real person's full name**, or a famous title (a film or show) used as a title.

**What does not count:** a name that shares one common word with a real business in a different trade (GOLDEN TIDE
MARKET does not collide with every business called Golden-something); a closed business with a different name; a
place name used as a building's name.

---

## 3. Canal Street (Level 2)

### 3.1 Approved names

These are the business and place names the signs carry (chinatown.md 13.3 lists the carrier, the position and whether
each is lit). The words under each name (CDs · VINYL · KARAOKE, ROAST DUCK · ROAST PORK · SOY CHICKEN, and so on) are
ordinary trade words and are not listed one by one.

| Sign text | Where | What the search found |
|---|---|---|
| **GOLD HITS RECORDS** | N1 ground band | No store of that name. Nearest: Golden Hits, a short-lived basement record shop in Ridgewood (the New Jersey town, per its Patch page), closed. |
| **JADE TEAPOT** | N1 2F blade (with DIM SUM) | No restaurant of that name. Nearest: Jade (Singapore), Jade Teahouse (Portland OR), Teapot Vegetarian House: different names, none in New York. |
| **TWIN CARP JEWELRY** | N2 ground band | No business; only carp and twin-fish pendant designs sold by various shops. |
| **FAR SHORE TRAVEL** (new) | N2 3F window | No business. Nearest: Far & Away Adventures (BC, Canada), Shore Travel (New Zealand), Far & Wild Travel (UK). |
| **EIGHT TREASURE BBQ** | N3 ground band | No restaurant of that name in New York (eight treasure is a dish name). |
| **SPRING PINE HERBS & GINSENG** | N4 ground band | No shop of that name. A ginseng product line sold as Pine Brand exists; the shop name shares only the word pine and the band shows no product mark. |
| **LONG LIFE NOODLE HOUSE** | N5 ground band | No business of that name. Nearest: Long Life Noodle Company (San Francisco, Palo Alto), a different name, not in New York. |
| **SUNNY DAY LAUNDROMAT** | N6 ground band | No business of that name. Nearest: Sunshine Laundromat (Greenpoint, Brooklyn), My Sunny Laundry (Florida): different names. |
| **HARBOR STAR HOTEL** (new) | N6 four-storey blade | No hotel of that name. Nearest: Harbor Court Hotel (San Francisco). Two earlier candidates were dropped: Nine Bridges (a well-known golf club brand) and East Wind (Eastwind Hotel, Catskills NY). |
| **GOLDEN TIDE MARKET** | the market band and rooftop letters | No store of that name. |
| **LANTERN ALLEY** | alley A painted board | No place or business of that name (only antique lantern listings). |
| **MOON GATE BAKERY** | W3 band and pink neon | No bakery of that name. Nearest: Moon Bakery (Salt Lake City, Calgary), Day Moon Bakery (San Francisco), Golden Gate Bakery (San Francisco). |
| **WEST CITY HARDWARE** | W1 band (unlit) | No store of that name. Nearest: West Hardware Co. (West, Texas), Westlake Ace Hardware. |
| **GOLDEN LUCK ELECTRONICS** | E1a Canal band | No retailer of that name; an importer named Goldenluck Imp Exp appears in shipping records (textiles, not a shop or a consumer mark). |
| **LITTLE KITE CAFE** (new) | E1a Mott band | No cafe of that name. Nearest: Box Kite (St. Marks Pl, East Village), permanently closed, a different name. |
| **CLEVER HANDS TAILOR** | E1a Square-side kiosk | No business of that name. |
| **PLUM BLOSSOM ARCADE** | both arcade arches | No arcade or mall of that name. Real Chinatown malls are East Broadway Mall and the like: different names. |
| **WILLOW BRIDGE OPTICAL** (new) | E1b Canal band | No business of that name; the words appear only separately (a frame model named Willow, Bridge Opticians in Staten Island). |
| **CRANE PAVILION BANQUET HALL** | E2 Square band | No venue of that name. Nearest: Crane Club (a New York restaurant), Craneway Pavilion (Richmond CA), The Crane (Barbados): different names. |
| **GOOD WISHES GROCERY** | S3 Mott band | No store of that name. |
| **SEVEN STARS COACH** | S3 Mott band | No operator of that name. The real Chinatown bus lines found (Lucky Star, Fung Wah) have different names. |
| **QUICK WIRE** | S3 Mott band (phones, money transfer) | No service of that name. |
| **BIG LIGHT SIGNS** | the neon workshop's board and its half-finished neon | No shop of that name. Real New York neon shops found: Let There Be Neon, Glo Studio, Mondo Neon. |
| **SILVER WAVE VIDEO** | E2 Mott neon over the dub room | No store of that name. Nearest: Silver Lake Video (Everett WA, closed), Silver Screen Video (WA). |
| **SPRING SUNSHINE TROUPE** | OPERA GALA wheat-paste poster | No troupe of that name. |

### 3.2 Replaced names

| Retired | Why (what the search found) | Replaced by | The replacement's search |
|---|---|---|---|
| SEA BREEZE TRAVEL | Real travel agencies of the same name: SeaBreeze Travel (North Conway NH) and Seabreeze Travel Services (Virginia Beach). Not in New York, but the same name in the same trade. | **FAR SHORE TRAVEL** | No business. Nearest: Far & Away Adventures (BC, Canada), Shore Travel (New Zealand), Far & Wild Travel (UK). |
| BRIGHT MOON HOTEL | No hotel of that name, but The Historic Blue Moon Hotel is at 100 Orchard St on the Lower East Side, a few blocks from Canal St: a blade reading BRIGHT MOON HOTEL there is a look-alike. | **HARBOR STAR HOTEL** | No hotel of that name. Nearest: Harbor Court Hotel (San Francisco). Two earlier candidates were dropped: Nine Bridges (a well-known golf club brand) and East Wind (Eastwind Hotel, Catskills NY). |
| LILY CAFE | Cafe Lily is a restaurant at 42 Avenue O, Bensonhurst, Brooklyn; Lily's Restaurant is at 501 Lexington Ave, Midtown East. The same name in the same trade in New York. | **LITTLE KITE CAFE** | No cafe of that name. Nearest: Box Kite (St. Marks Pl, East Village), permanently closed, a different name. |
| CLEAR VIEW OPTICAL | Clear View Optical is a registered optometrist at 707 Burke Ave, the Bronx (NPI registry); Clearview Eye Center is in Astoria; Sterling Optical is also listed as Clearview Optics (Garden City NY). | **WILLOW BRIDGE OPTICAL** | No business of that name; the words appear only separately (a frame model named Willow, Bridge Opticians in Staten Island). |

The four replacements fit the same carriers: HARBOR STAR has the same eleven letters as the blade it replaces; FAR SHORE
TRAVEL and WILLOW BRIDGE OPTICAL fit their bands at the letter heights of the other bands; LITTLE KITE CAFE is longer than
the name it replaces on its 6 m band, so its cap height drops from 0.46 to about 0.40 of the face.

### 3.3 Generic words (not names, nothing to search)

MARKET, FRESH FISH, FRUIT, VEGETABLES, DRY GOODS, TOFU, ROAST MEAT, COLD ROOM, WATCH REPAIR, KEYS CUT, PHONES, NEON SIGNS, MAHJONG, DIM SUM, HOTEL, BAKERY, VIDEO, OPERA GALA, ONE NIGHT ONLY, FOR RENT, FOR LEASE, CDs $5, USB $10, BAGS $20, SUNGLASSES $5, 3 FOR $10, the sub-lines under each band (CDs · VINYL · KARAOKE, ROAST DUCK · ROAST PORK · SOY CHICKEN, ...).

---

## 4. Midtown (Level 3)

### 4.1 Approved names

| Sign text | Where | What the search found |
|---|---|---|
| **MIRAVESSE** (new) | E1 screen (perfume, Eau de Nuit) | No brand of that name. Nearest: Miraj, Marylise Mirabelli, Miris: different names. |
| **NORTHBOUND AIRWAYS** | E1 screen (an airline) | No airline of that name. Nearest: Northern Pacific Airways (now New Pacific Airlines): a different name. |
| **KESTREL MOBILE** | E2a screen (a phone carrier) | No carrier of that name. |
| **BRASS & BUN** | E2b screen (a burger bar) | No restaurant of that name. Nearest: Brass Tap, Brass Monkey (Milwaukee), Meat & Bun (UK). |
| **THE MERIDALE THEATRE** (new) | E3 screen and the east marquee | No venue of that name (Meridale is a hamlet upstate; no theatre or business named for it was found). Nearest: Meridian Theatres (Ottawa), Meadowvale Theatre (Mississauga). |
| **LAMPLIGHT AVENUE** (new) | E3 screen (the musical's title) | No show of that name. Nearest: Lamplight (a play), The Lamplighter (a musical), Lamplighters Music Theatre: different titles. |
| **VESPERLINE CRUISES** | E3 screen (a cruise line) | No cruise line of that name. |
| **HOROVAN** (new) | N1 screen (watches) | No brand of that name. Nearest: Horon, Horage, Horizon (watch brands): different names. |
| **NORTHWEFT** (new) | N1 screen (a fashion label, fall collection) | No label of that name. An earlier candidate, Vantelle, was dropped (Vontelle sells wholesale on Faire). |
| **FIZZWICK SODA** (new) | N1 screen (a soft drink) | No product of that name (a game's fictional drink is called Fizz; a different word). |
| **DUSKLINE TOURS** | S1 screen (a bus tour) | No company of that name. |
| **MARLOWE & FINCH** | C's roof billboard (a department store) | No business of that spelling. Marlow & Finch (no e) appears only on unfinished template sites as a UK recruitment firm, not a store, not in New York. |
| **SEVENTH AV SOUVENIRS** | C ground floor band | No shop of that name. The real Seventh Avenue shops are Souvenirs and Gifts (730 Seventh Ave) and NYC Mega Mart: different names. |
| **SLICE OF SEVENTH** (new) | C ground floor band | No pizzeria of that name. Nearest: 7th Heaven Pizza (Harlem), a different name. |
| **SHUTTERBOX CAMERA & ELECTRONICS** (new) | C ground floor band | No store of that name. Nearest: The Shutterbug (a camera shop), ShotBox (a photo kit). |
| **BELLHAVEN SAVINGS** (new) | D ground floor, the closed bank lobby | No bank of that name. Belhaven (one L) is a town in North Carolina with branches of other banks; Belmont Savings Bank (MA) and Bell Savings Bank (PA) are different names. |
| **HOTEL CASTELLANE** | the east hotel canopy | No hotel of that name in New York. |
| **BRANNIGAN'S CHOP HOUSE** | W 46 St south band (a steakhouse) | No restaurant of that name. Real nearby steakhouses: Gallagher's, Brooklyn Chop House Times Square: different names. |
| **ASHBY & CROSS PHARMACY** (new) | W 46 St south band (a pharmacy) | No pharmacy of that name. Nearest: Ashby Pharmacy (two in England), a different name, not in the United States. An earlier candidate, Brightmore, was clear too but repeated Brightwire on the same level. |
| **HALVORSEN BUILDING** | A's parapet, incised | No building of that name. |
| **CORVIN HALL** | C's cornice, incised | No building of that name. Nearest: Corinthian Hall (Rochester, demolished), Carman Hall (Columbia). |
| **KESSLER & ROTH SCAFFOLD** | the scaffold tower's board | No firm of that name. Roth Geruste is a Swiss scaffolding firm (a different name, not in the United States). |
| **BRIGHTWIRE EVENTS** | the production truck's side | No firm of that name. Nearest: Bright Event Productions (Nashville), a different name. |
| **CITY CROSSTOWN** | the stalled bus's destination sign | No operator of that name (crosstown is a generic route word). |
| **THE LOFTLARK** (new) | D's closed rooftop lounge, unlit neon | No venue of that name (only Loft Lounge bars in Perth, Birmingham UK, Atlanta). |

### 4.2 Replaced names

| Retired | Why (what the search found) | Replaced by | The replacement's search |
|---|---|---|---|
| ORBELLE | Orebella, a perfume brand launched in 2024 and sold nationally (Ulta, Selfridges): the same trade and nearly the same word. | **MIRAVESSE** | No brand of that name. Nearest: Miraj, Marylise Mirabelli, Miris: different names. |
| THE ALDERWAY THEATRE | No venue of that name, but Alleyway Theatre (Buffalo, New York) differs by two letters in the same trade, in the same state. | **THE MERIDALE THEATRE** | No venue of that name (Meridale is a hamlet upstate; no theatre or business named for it was found). Nearest: Meridian Theatres (Ottawa), Meadowvale Theatre (Mississauga). |
| NIGHT SHIFT | No musical of that name found, but Night Shift is a well-known 1982 studio film; a show title that is also a famous film reads as an adaptation. | **LAMPLIGHT AVENUE** | No show of that name. Nearest: Lamplight (a play), The Lamplighter (a musical), Lamplighters Music Theatre: different titles. |
| QUILLON | No brand of that name, but Aquilon & Co is a French watch brand: one letter apart in the same trade. | **HOROVAN** | No brand of that name. Nearest: Horon, Horage, Horizon (watch brands): different names. |
| TAMSIN GRAY | No designer of that name found, but it is a full personal name (real people carry it) and the game allows no real people but the star. | **NORTHWEFT** | No label of that name. An earlier candidate, Vantelle, was dropped (Vontelle sells wholesale on Faire). |
| HALCYON SODA | No soda of that name, but Halcyon, LLC holds trademarks for mineral and aerated waters and soft drinks: the same goods. | **FIZZWICK SODA** | No product of that name (a game's fictional drink is called Fizz; a different word). |
| MIDTOWN SLICE | Slice Midtown is a real New York pizza listing (the same words reversed, the same trade, the same neighbourhood). | **SLICE OF SEVENTH** | No pizzeria of that name. Nearest: 7th Heaven Pizza (Harlem), a different name. |
| 46TH ST CAMERA & ELECTRONICS | No shop of that name, but 47th Street Photo (famously asked for as 47th Street Camera) was the city's best-known camera store, and H and B Digital is at 29 W 46th St: a look-alike. | **SHUTTERBOX CAMERA & ELECTRONICS** | No store of that name. Nearest: The Shutterbug (a camera shop), ShotBox (a photo kit). |
| LANTERN SAVINGS | No bank of that name, but Lantern by SoFi is a national savings-account marketplace: the same field and the same lead word. | **BELLHAVEN SAVINGS** | No bank of that name. Belhaven (one L) is a town in North Carolina with branches of other banks; Belmont Savings Bank (MA) and Bell Savings Bank (PA) are different names. |
| CORNER CHEMISTS | Corner Chemists Pharmacy LLC is a real retail pharmacy at 11 Henry St, Manhattan (NPI registry). | **ASHBY & CROSS PHARMACY** | No pharmacy of that name. Nearest: Ashby Pharmacy (two in England), a different name, not in the United States. An earlier candidate, Brightmore, was clear too but repeated Brightwire on the same level. |
| THE PERCH | The Perch is the 23rd-floor rooftop bar of a Brooklyn hotel (The Livingston): the same name and trade in New York. | **THE LOFTLARK** | No venue of that name (only Loft Lounge bars in Perth, Birmingham UK, Atlanta). |

The E3 screen now reads **THE MERIDALE THEATRE presents LAMPLIGHT AVENUE, a new musical**, and the east marquee **THE
MERIDALE THEATRE**. The N1 stack reads **HOROVAN watches / NORTHWEFT fall collection / FIZZWICK SODA**.

### 4.3 Slogans, labels and the ticker (not names, nothing to search)

WORLD PREMIERE, MIDNIGHT, NO SIGNAL, STAND BY, PRESENTS, Eau de Nuit, Fly the late one, Five bars, five boroughs, Burgers till four, a new musical, watches, fall collection, The city after dark, The holiday floor is open, SIDEWALK SHEDS · SCAFFOLD · HOISTS, STAGING · LIGHTING · SCREENS, ROOF DOOR / KEEP CLOSED, MACHINE ROOM / AUTHORIZED ONLY, DANGER / HIGH VOLTAGE, TANK 2 / DRINKING WATER, SQUARE CLOSED TONIGHT FOR A PREMIERE, CROSSTOWN TRAFFIC HEAVY, FORECAST: CLEAR, 41°. None of the slogans is a known advertising line, and the ticker's headlines name no real event.

---

## 5. Tone (Canal Street)

The list was read for anything a Chinatown resident would find mocking. What was checked, and what the art must keep:

- **The names are in the style of real Chinatown shop names in English**: nature, places and good wishes (jade, pine,
  plum blossom, crane, moon gate, long life, good wishes), plain trade names (WEST CITY HARDWARE, QUICK WIRE), and the
  menu words a real menu uses (DIM SUM, WONTON SOUP, ROAST DUCK, EGG TARTS). No pun on an accent, a name or a food, no
  joke spelling, no "fortune" or "lucky" gag. Kept.
- **No mock-Asian lettering.** The faces use Inter, Old Standard and Carlito only (chinatown.md 13.4): never a
  brush-stroke "chop suey" display face, never Latin letters drawn to look like Chinese ones. Kept.
- **The bootleg table belongs to the Vultures, not to the street.** Reel 4 sits at a bootleg disc table (chinatown.md 0).
  The other vendor tables sell ordinary tourist goods (unbranded bags, "NEW YORK" T-shirts, "CANAL ST" caps, phone
  cases) under plain marker placards, with no fake brand and no word like "replica" or "designer". **Rule for the art
  and the decal lane:** the disc and USB-stick table carries the Vultures' VLTR tag so the copying reads as the gang's
  operation; no shop sign and no resident is tied to it.
- **The enemies are not the neighbourhood.** The Vultures are a mixed New York crew, and nothing in their look refers
  to Chinese people (characters.md). No Goon spawns out of a named shop's front door dressed as its staff.
- **No real organisation, association, temple, school or political poster** (chinatown.md 13.4). The opera poster names
  an invented troupe and shows no face. Kept.
- **"Golden" twice and "Gold" once** (GOLDEN TIDE MARKET, GOLDEN LUCK ELECTRONICS, GOLD HITS RECORDS) is within what a real
  block of Canal Street shows. Acceptable; the owner may vary one.
- **Sound, not signs:** chinatown.md 12 plans "Cantonese talk radio from a shop". It is speech, not lettering, so the
  English-only answer does not cover it. If kept, it must be a real recording by a native speaker (licensed, words the
  audio lane has had translated) or an unintelligible murmur; never made-up syllables that imitate the language. Listed
  as open (section 8).

Midtown's names were read the same way: none mocks a group, and the one real-person risk (a fashion label named after an
invented person, which a real person also carries) is replaced.

---

## 6. Real place names (for the lead to add to ART_BIBLE 5.7)

CHINATOWN, MANHATTAN, CANAL ST, MOTT ST, MIDTOWN, SEVENTH AV, W 46 ST, BROADWAY, NEW YORK, the bridge east of Canal St (an unnamed silhouette). TIMES SQ is allowed by midtown.md 12.1 but used on no sign. The agency marks that usually go with these
(street-sign logos, transit globes, police insignia) stay off every sign.

---

## 7. Hand-off: what the other lanes change

The art lists and the level layout were written before this search, so they still carry the replaced names.
`python3 tools/names/check_names.py` lists every line, file by file, and passes only when none is left; it also fails
on a business name in an art list that is not in `names.json` (search it first) and on any CJK character in the
new levels' files. Today it reports the replaced names in these files (no one else's file was edited by this lane):

| Lane | Files | Change |
|---|---|---|
| A-CT (Canal art) | `art/blender/assets/_chinatown_names.py`, `_chinatown_place.py` | The four faces' text (and their ids, suggested `FarShore`, `HarborStar`, `LittleKite`, `WillowBridge`); re-run the atlas and the north-row previews |
| A-MT (Midtown art) | `art/blender/assets/_midtown_names.py`, `_midtown_atlas.py`, `_midtown_roof.py` (two comments) | The slides and faces of section 4.2 (ids suggested `E1_Miravesse`, `E3_Meridale`, `N1_Horovan`, `N1_Northweft`, `N1_Fizzwick`, `Band_SliceOfSeventh`, `Band_Shutterbox`, `Band_BellhavenSavings`, `Band_MeridaleTheatre`, `Band_AshbyCross`); `business_names()` from the approved list; THE LOFTLARK for the lounge neon |
| D (level data) | `tools/levels/layouts/chinatown.py`, `layouts/midtown.py`, then `build_level.py` | The shop strings, the face ids and the screen slides; the rebuilt `tools/levels/data/level_*.json` follow |
| Lead | `docs/unreal/MAPS.md` 1.4 row 6, `docs/unreal/ART_BIBLE.md` 5.7 | Point decision 6 at this file; add the real places of section 6 |

The designs (chinatown.md 13.3 and 4, midtown.md 12) already carry the new names.

---

## 8. Still open

1. **The owner's sign-off** (section 1).
2. **A trademark-register search before release** for the seven national-style screen brands (MIRAVESSE, NORTHBOUND
   AIRWAYS, KESTREL MOBILE, FIZZWICK SODA, HOROVAN, VESPERLINE CRUISES, NORTHWEFT) and the four that read as chains
   (BRASS & BUN, DUSKLINE TOURS, MARLOWE & FINCH, HOTEL CASTELLANE). A web search finds working businesses; it does not
   find every registered or pending mark.
3. **The other lanes' changes** of section 7, then a clean run of `tools/names/check_names.py`.
4. **The Cantonese radio line** in the Canal sound bed (section 5): a native recording or a murmur, or none.
5. **A look-alike review of the finished art** (MAPS.md C3): a name can be clear and its colours and layout still look
   like a real chain's. Done on the first picture round of each map.

---

## 9. Every query as run (2026-11-26)

### Canal Street

| Name | Query as run |
|---|---|
| GOLD HITS RECORDS | `"Gold Hits" records store New York` |
| JADE TEAPOT | `"Jade Teapot" restaurant` |
| TWIN CARP JEWELRY | `"Twin Carp" jewelry` |
| SEA BREEZE TRAVEL (retired) | `"Sea Breeze Travel" New York` |
| FAR SHORE TRAVEL | `"Far Shore Travel"` |
| EIGHT TREASURE BBQ | `"Eight Treasure" BBQ OR restaurant New York` |
| SPRING PINE HERBS & GINSENG | `"Spring Pine" herbs ginseng` |
| LONG LIFE NOODLE HOUSE | `"Long Life Noodle House"` |
| SUNNY DAY LAUNDROMAT | `"Sunny Day Laundromat"` |
| BRIGHT MOON HOTEL (retired) | `"Bright Moon Hotel" New York` |
| HARBOR STAR HOTEL | `"Harbor Star Hotel"` |
| GOLDEN TIDE MARKET | `"Golden Tide Market" OR "Golden Tide" supermarket New York` |
| LANTERN ALLEY | `"Lantern Alley" New York` |
| MOON GATE BAKERY | `"Moon Gate Bakery"` |
| WEST CITY HARDWARE | `"West City Hardware"` |
| GOLDEN LUCK ELECTRONICS | `"Golden Luck" electronics New York` |
| LILY CAFE (retired) | `"Lily Cafe" New York Manhattan` |
| LITTLE KITE CAFE | `"Little Kite Cafe" OR "Little Kite" cafe New York` |
| CLEVER HANDS TAILOR | `"Clever Hands" tailor` |
| PLUM BLOSSOM ARCADE | `"Plum Blossom Arcade" OR "Plum Blossom" mall Chinatown New York` |
| CLEAR VIEW OPTICAL (retired) | `"Clear View Optical" OR "Clearview Optical" New York` |
| WILLOW BRIDGE OPTICAL | `"Willow Bridge Optical" and "Willow Bridge" optical OR optician OR eyewear New York` |
| CRANE PAVILION BANQUET HALL | `"Crane Pavilion" banquet hall OR restaurant` |
| GOOD WISHES GROCERY | `"Good Wishes" grocery OR market New York` |
| SEVEN STARS COACH | `"Seven Stars" bus OR coach Chinatown New York` |
| QUICK WIRE | `"Quick Wire" money transfer` |
| BIG LIGHT SIGNS | `"Big Light" neon signs shop New York` |
| SILVER WAVE VIDEO | `"Silver Wave" video store OR "Silver Wave Video"` |
| SPRING SUNSHINE TROUPE | `"Spring Sunshine" opera troupe` |

Replacement candidates that were searched and dropped: NINE BRIDGES HOTEL (a well-known golf club brand), EAST WIND HOTEL
(Eastwind Hotel & Bar, Windham NY), PAPER BOAT TRAVEL (a working agency in Winston-Salem NC).

### Midtown

| Name | Query as run |
|---|---|
| ORBELLE (retired) | `"Orbelle" perfume OR fragrance brand` |
| MIRAVESSE | `"Miravesse" perfume OR brand` |
| NORTHBOUND AIRWAYS | `"Northbound Airways" OR "Northbound Air" airline` |
| KESTREL MOBILE | `"Kestrel Mobile" phone carrier OR company` |
| BRASS & BUN | `"Brass & Bun" OR "Brass and Bun" burger` |
| THE ALDERWAY THEATRE (retired) | `"Alderway Theatre" OR "Alderway Theater"` |
| THE MERIDALE THEATRE | `"Meridale Theatre" OR "Meridale Theater"` |
| NIGHT SHIFT (retired) | `"Night Shift" musical Broadway OR off-Broadway` |
| LAMPLIGHT AVENUE | `"Lamplight Avenue" musical OR show` |
| VESPERLINE CRUISES | `"Vesperline" cruises OR cruise line` |
| QUILLON (retired) | `"Quillon" watches brand` |
| HOROVAN | `"Horovan" watches OR watch brand` |
| TAMSIN GRAY (retired) | `"Tamsin Gray" fashion OR designer` |
| NORTHWEFT | `"Northweft" fashion OR clothing` |
| HALCYON SODA (retired) | `"Halcyon Soda" OR "Halcyon" soda drink brand` |
| FIZZWICK SODA | `"Fizzwick" soda OR drink` |
| DUSKLINE TOURS | `"Duskline Tours" OR "Duskline" tour company` |
| MARLOWE & FINCH | `"Marlowe & Finch" OR "Marlowe and Finch"` |
| SEVENTH AV SOUVENIRS | `"Seventh Avenue Souvenirs" OR "Seventh Av Souvenirs" OR "7th Avenue Souvenirs" New York` |
| MIDTOWN SLICE (retired) | `"Midtown Slice" pizza New York` |
| SLICE OF SEVENTH | `"Slice of Seventh" pizza` |
| 46TH ST CAMERA & ELECTRONICS (retired) | `"46th Street Camera" OR "46th St Camera" electronics New York` |
| SHUTTERBOX CAMERA & ELECTRONICS | `"Shutterbox" camera store OR electronics` |
| LANTERN SAVINGS (retired) | `"Lantern Savings" bank` |
| BELLHAVEN SAVINGS | `"Bellhaven Savings" bank` |
| HOTEL CASTELLANE | `"Hotel Castellane" OR "Castellane Hotel" New York` |
| BRANNIGAN'S CHOP HOUSE | `"Brannigan's Chop House" OR "Brannigan's" steakhouse New York` |
| CORNER CHEMISTS (retired) | `"Corner Chemists" OR "Corner Chemist" pharmacy New York` |
| ASHBY & CROSS PHARMACY | `"Ashby & Cross" OR "Ashby and Cross" pharmacy OR chemists` |
| HALVORSEN BUILDING | `"Halvorsen Building" New York` |
| CORVIN HALL | `"Corvin Hall" New York` |
| KESSLER & ROTH SCAFFOLD | `"Kessler & Roth" OR "Kessler and Roth" scaffold OR construction` |
| BRIGHTWIRE EVENTS | `"Brightwire Events" OR "Brightwire" event production staging lighting` |
| CITY CROSSTOWN | `"City Crosstown" bus OR transit operator` |
| THE PERCH (retired) | `"The Perch" rooftop bar OR lounge New York Manhattan` |
| THE LOFTLARK | `"Loftlark" bar OR lounge` |

Replacement candidates that were searched and dropped: VANTELLE (Vontelle, a wholesale brand), MARQUEE PIZZA (Marquee is a
New York nightclub brand), LAMPWICK PHARMACY (clear, but Lampwick is a well-known film character's name), BRIGHTMORE
PHARMACY (clear, but repeats the Bright- of BRIGHTWIRE EVENTS on the same level).
