# Level 2: Chinatown / Canal Street (design)

Status: design for the three-map release (DECISIONS.md 2026-11-25 ~21:40). Nothing here is built. This file is the
level designer's brief. It is meant for whoever writes the level data and its generator, the art lane (Blender and
the box), the gameplay/C++ lane and the lead.

Conventions are the ones `level.json` uses. Units are web units: metres, +Y up, x east, z south, so north is -Z.
Unreal (X, Y, Z) cm = web (x, z, y) x 100. A web yaw of 0 looks north (-Z), and a positive yaw turns left, so
facing east is yaw -1.5708. A prop's `rotationY` r gives forward (cos r, 0, -sin r), and its Unreal yaw is -r in
degrees. Heights are measured from the road at y = 0, and sidewalks are at 0.15.

The route lengths, nav counts and spawn checks below come from a throwaway rasteriser of this plan. It used the
game's own nav rule (0.5 m cells, 0.5 m inflate, blocked band 0.47 to 1.5 m, outer ring blocked, 8-neighbour A*).
They are design numbers. The real generator must recompute them from the final collider list (section 17).

---------------------------------------------------------------------------------------------------

## 0. The level in one page

| | Level 1, the Block (built) | Level 2, Canal Street (this design) |
|---|---|---|
| Setting | Jamaica Ave under the El, Hollis, Queens, 4:15 PM, day | Canal St and Mott St, Chinatown, Manhattan, 7:40 PM, night, the street still wet after rain |
| Bounds (web) | x -46..46, z -34..34 (92 x 68 m, 6,256 m²) | **x -44..44, z -34..32 (88 x 66 m, 5,808 m²)** |
| Nav grid | 184 x 136 cells, 9,052 free | 176 x 132 cells, about 11,170 free (prototype) |
| Feel | Open avenue, one big shop, an open lot | Packed and close-quarters: one wide street, a narrow street, two alleys, a covered market, three walk-in interiors, one low roof |
| Objectives | Reel 1 The Avenue, Reel 2 Chop Shop, Reel 3 The Cage | **Reel 4 The Tables, Reel 5 The Market, Reel 6 The Dub Room** |
| Extraction | IPX truck at the south end of the lot | IPX truck idling at the east end of Canal St |
| Critical path (A* on nav) | 39.0 + 25.0 + 65.8 + 63.9 = **193.7 m** | 34.5 + 27.4 + 59.6 + 60.2 = **181.7 m** |
| Spawns | 29 ground, 17 air | 35 ground, 18 air |
| Explosives | 21 (14 propane, 7 rack) | 18 (15 propane, 3 rack) |
| Colliders | 777 | budget at most 800 (planned about 780) |
| Lighting | Day rig (sun, clouds, sky) | Night rig: no sun shadow and no volumetric clouds. About 48 placed local lights, at most 10 of them shadowed. Emissive neon. Wet ground |

**The story beat.** After the Block, the Vultures run three more masters down to Canal Street. One is at a
bootleg table out front. One is in the cold room at the back of a covered market. One sits in the back-room
"dub room" off Mott St where the crew copies the masters. Rule takes all three, and the IPX truck waits at the
east end of Canal. The mission rules do not change: three objectives, three waves, a pursuit, an extraction.

**Why it plays differently.** The Block is mostly open ground. Canal Street is 19 m from facade to facade, with
parked cars, trucks and a row of vendor tables. Off it run narrow alleys (4 m), a narrow street (Mott, 10 m), a
26 x 20 m market hall packed with stall counters, a shop you can walk through (the bakery), a covered arcade, and a
banquet hall that opens into the dub room. Most fights happen at 5 to 15 m, and every wave comes out of doorways
as well as from the street ends. Buzzards have three open air spaces: Canal St, the market roof and yard, and the
Square. Below 15 m they cannot fly over the five- to seven-storey buildings, so drones come down the streets.

---------------------------------------------------------------------------------------------------

## 1. Setting, time and mood

- **Place line:** `Chinatown, Manhattan · Canal St · 7:40 PM`. It is late November and fully dark. Shops are
  still open and the vendors are packing up.
- **Weather:** the rain has stopped and no rain falls. Falling rain is translucent overdraw, and it is the worst
  case for the stream encoder at QP 34. The ground is wet: dark asphalt, puddles in the gutters, drips from awnings
  and fire escapes near the player, and steam from manholes and kitchen vents.
- **Light:** neon, lightboxes and shop interiors carry the street. Cool LED street lamps match the art bible's
  2010s to 2020s street kit. The market hall has hard white light from bare bulbs and fluorescents. The bakery is
  warm pink-white. Red paper lanterns are strung over the Square and the alley. The sky is a low overcast lit
  orange-brown from below by the city.
- **Sound:** wet tyres from beyond the street ends, the buzz of a transformer, Cantonese talk radio from a shop
  (invented content), mahjong tiles from a second-floor window, kitchen fans in the alleys, fish-tank pumps in the
  market, and a distant train rumble across the bridge to the east every 90 to 150 s. That rumble replaces the
  El's train pass.
- **Why night.** The owner asked for "lots of neon", which only reads at night. Day was considered: neon at 550
  nits and signs at 900 would read as signboards, not neon. Night is new work (section 11), but it is also cheap
  on the GPU. There is no sun cascade and no cloud shadow or reconstruction, and that GPU time pays for the local
  lights.

---------------------------------------------------------------------------------------------------

## 2. Footprint

- **Bounds:** x -44..44, z -34..32. The player is clamped to them. Every building collider that lies outside
  them only blocks shots and sight.
- **Nav grid:** origin (-44, -34), cell 0.5, 176 columns x 132 rows. In Unreal the origin is (-4400, -3400) and
  the cell is 50 cm.
- **The front-end stage** stays at (0, 0, 100000) cm. The tallest geometry here is the backdrop towers (at most
  about 120 m) and the bridge silhouette far to the east (about 600 to 900 m away). Both stay well under 1 km and
  outside the stage room's view.
- **Edges.**
  - **West:** a street dig with steel plates, jersey barriers across the roadway at x -43.6..-42.8 and a parked
    box truck. The player arrives here.
  - **East:** barriers at x 42.6..43.4, a stalled delivery truck and traffic barrels, just past the IPX truck.
  - **Mott St south:** a box truck parked across the street (x 9.6..17.6, z 27.2..29.8) under a sidewalk shed.
  - **North:** a continuous row of buildings.
  - **South-west:** the backs of tall tenements.
  - Canal St and Mott St continue beyond the bounds as art and backdrop only.

---------------------------------------------------------------------------------------------------

## 3. Plan

### 3.1 Top-down plan

The plan is 1 character = 1 m east-west and 1 row = 2 m north-south (z labels on the left). North is up.

```
         -40       -30       -20       -10       0         10        20        30        40
         |         |         |         |         |         |         |         |         |
 -34 ########  ###########  ############  ###########  #############  #########  ############
 -32                                                                                         
 -30 ##      ccccc           ccccc           ccccc                                 ccccc   ##
 -28 ##      ccccc           ccccc           ccccc                   bbbbbbbb      ccccc   ##
 -26 ##  S                                                           bbbbbbbb     TTTTTTTTT##
 -24 ##                                                                          XTTTTTTTTT##
 -22 ##    ccccc                   bbbbbbbb                          cccccc       TTTTTTTTT##
 -20 ##    ttcctt  tt  tt  tt  tt  ttbbttbbtt      tt  tt            cccccc                ##
 -18       tt  tt  tt  tt  tt  tt  tt  4t  tt      tt  tt                                    
 -16                                                                                         
 -14 ##############    ####    ###    ###    ######  ####          ############   ###########
 -12 ##############    #   nnn  nnn  nnn   nn   ##      #          ############   ###########
 -10 ##############dd  #   nnn  nnn  nnn   nn  nn#      #          ############ n #  **######
  -8 ##############dd  #   nnn  nnn  nnn   nn  nnnnnnn  #  ccc     ############      **######
  -6 ##############    #   nnn  nnn  nnn   nn  nn#      #  ccc     ############   #   #######
  -4 ##############    #   nnn  nnn  nnn   nn  nn###  ###  ccc     ############   ###########
  -2 ##############    #   nnn  nnn  nnn   nn  nn#      #          ############   ###########
   0 ##############    wwwww  w                 ##      #          ############   ###########
   2 ##############    #      w   pppppp        ##         ccc                               
   4 ##############  nn###5###w###pppppp##    ####  nn  #  ccc       nnn                nnn  
   6 ##############    ##########ZZZZZZZ       dd#  nn  #  ccc               o    o          
   8 ##############    ##########ZZZZZZZ**     dd###nn ##  ccc          n              n     
  10 ##############                  nn                                 n              n     
  12 ##############      dd                        dd                        o    o          
  14 ####################################################            nnn                nnn  
  16 ####################################################                                    
  18 ####################################################  ccc     #############    #####ssss
  20 ####################################################  ccc     #   nn  # nnn nnn nnn ssss
  22 ####################################################  ccc     #   nn  # nnn nnn nnn ssss
  24 ####################################################                  # nnn nnn     ssss
  26 #################################################### bbbbbbbbb#         nnn nnn ##  ssss
  28 #################################################### bbbbbbbbbnn 6    # nnn nnn #      #
  30 ####################################################          nn########################
```

Legend:

- `#`: walls and buildings.
- `n`: counters, tables and other low solids.
- `c`: cars.
- `b`: box trucks.
- `T`: the IPX truck.
- `t`: vendor tables.
- `d`: dumpsters.
- `w`: cold-room walls.
- `p`: pallet stacks.
- `Z`: the climbable stair to the market roof.
- `o`: pavilion columns.
- `s`: the stage.
- `*`: explosives.
- `S`: the player start.
- `4`, `5`, `6`: the reels.
- `X`: the extraction zone.

Blank cells are walkable ground.

Reading the plan:

- **Canal St** fills the top band, z -34..-14.
- **Lantern Alley A** is the 4 m slot at x -30..-26, from Canal down to z 14. **Alley B** runs east along
  z 10..14 to Mott.
- **The market** is the stall grid at x -26..0, z -14..6. Its **yard** (with the stair `Z`) is at x -16..0,
  z 6..10.
- **The bakery** is at x 0..8.
- **Mott St** is at x 8..18.
- **The arcade** is the 4 m slot at x 29.4..33.6, from Canal to **the Square** (x 18..44, z 2..18).
- **The banquet hall** (x 26.3..44) and **the dub room** (x 18..26) take up z 18..32.

### 3.2 How the spaces connect

```mermaid
flowchart LR
  start([Start: west Canal St]) --> canal[Canal St<br/>19 m wide, tables, cars]
  canal -- "3 roll-gate openings, 4 m" --> market[Covered market<br/>stall rows, cold room]
  canal -- "4 m" --> alleyA[Lantern Alley A]
  canal -- "door 2 m" --> bakery[Bakery front + kitchen]
  canal -- "kerb" --> mott[Mott St<br/>10 m wide]
  canal -- "arcade mouth 4 m" --> arcade[Plum Blossom Arcade<br/>+ neon workshop]
  market -- "side door 1.4 m (player only)" --> alleyA
  market -- "rear roll-up 4 m" --> yard[Market yard]
  yard --> alleyB[Lantern Alley B]
  yard -- "switchback stair" --> roof[(Market roof 5.7 m)]
  roof -- "0.3 m curb" --> kroof[(Kitchen roof 5.7 m)]
  kroof -. "drop 5.55 m, no fall damage" .-> mott
  roof -. "drop" .-> canal
  alleyA -- "dog-leg" --> alleyB
  alleyB --> mott
  bakery -- "door 2 m" --> alleyB
  bakery -- "door 2 m" --> mott
  mott --> square[The Square<br/>pavilion, lanterns]
  mott -- "roll-up 3 m" --> dub[Dub room]
  square -- "main doors 4 m" --> banquet[Banquet hall]
  banquet -- "door 2 m" --> dub
  square -- "arcade mouth 4 m" --> arcade
  arcade --> canal
  canal --> truck([IPX truck, east Canal St])
```

---------------------------------------------------------------------------------------------------

## 4. The spaces

Every opening that Goons must use is at least **2.0 m** wide. With the 0.5 m inflate, that leaves at least one
free column of nav cells. Player-only gaps are 1.4 m. Every step the player climbs is at most 0.42 m: risers are
0.219, the stage is 0.40, the plinth 0.30, kerbs 0.15 and the roof curb 0.30.

### 4.1 Canal Street (zone `canal`, x -44..44, z -34..-14)

**Cross-section, north to south:**

- North facade plane at z -33.0, with six shop alcoves 2.4 m wide and 1.0 m deep (to z -34) centred at
  x -35, -22, -8, 5, 20, 31.
- North sidewalk z -33.0..-29.8 (3.2 m) at y 0.15.
- Roadway z -29.8..-19.0 (10.8 m): north parking lane z -29.8..-27.6, two travel lanes, south parking lane
  z -21.2..-19.0.
- South sidewalk z -19.0..-14.0 (5.0 m) at y 0.15.
- Vendor table strip along the south kerb at z -18.8..-17.8: tables 1.8 m long at a 4 m pitch, so the gaps are
  2.2 m and Goons can pass. Tables start at x -38, -34, ..., -6, then x 2 and 6.
- The south facade at z -14.0. The Mott crossing breaks it at x 8..18.

**What is parked there (axis-aligned, so no oriented boxes):**

- North lane: a sedan (x -36..-31.5), a taxi (x -20..-15.5), a sedan (x -4..0.5) and an SUV (x 34..38.5).
- South lane: the livery sedan that dropped Rule off (x -38..-33.5), a box truck (x -14..-6, z -21.4..-18.9;
  cover in front of Reel 4) and a van (x 20..25.5).
- A box truck double-parked in the north travel lane at x 20..28, z -27.6..-25.0. It breaks up the 88 m view
  along the street.
- The IPX truck in the south travel lane at x 33.5..41.5, z -24.3..-21.7.

**Sight lines and cover:**

- The longest sight line in the level is the roadway from the start to the truck, 77 m. Cars, the two box trucks
  and the table row break it up.
- Cover is the cars (1.4 to 1.6 m tall), the box trucks, the tables (0.75 m, with goods racks to 1.3 m), the
  newspaper boxes, the alcoves, the dumpling and chestnut carts, and the hydrants.
- The south sidewalk is the protected lane, with the tables between it and the road. The north sidewalk is the
  exposed flank where enemies come out of the alcoves.

**Above:** projecting blade signs 4 to 12 m up, lightbox bands at 3.2 to 4.2 m, a sidewalk shed in front of N4
(x 0..12; posts block, the deck is art only), fire escapes on N1 and N3 only, and air conditioners.

### 4.2 Lantern Alley (zone `alley`; A: x -30..-26, z -14..14; B: x -30..8, z 10..14)

- **A** is a 4 m slot off Canal between W1 (a six-storey tenement) and the market's west wall. A painted wooden
  board over the mouth reads 燈籠巷 LANTERN ALLEY. This is an in-world nickname, not a city street sign.
- Red lanterns are strung across the alley at 5 to 7 m, as art only.
- Alley A has a dumpster at x -29.9..-28.3, z -9..-7.2 and a stack of crates at x -27.6..-26, z 4..5.4. The market
  side door (1.4 m, player only) is at z -2.9..-1.5 in the market's west wall. Restaurant back doors and three fire
  escapes are on W1's east face, as dressing.
- **The dog-leg** is at x -30..-26, z 10..14. Alley A ends visually in the S1 wall, so alley B opens only when
  you reach the corner. A stencilled arrow "MOTT ST →" and a lit kitchen door mark the turn (section 7.3).
- **B** runs east for 38 m behind the market yard to Mott St. It is a narrow shooting lane with staggered cover:
  dumpsters at x -24..-22.2 (S1 side) and x 2..3.8 (S3 side), and a pallet pile at x -12..-10.2 (yard side).
  There is a fire escape on S1 and one on S2 (dressing), and the bakery's alley door is at x 4..6.

### 4.3 The covered market (zone `market`; shell x -26..0, z -14..6; interior x -25.6..-0.4, z -13.6..5.6)

The market is a former garage turned into a market hall: one tall storey with a clear height of 5.4 m and a roof
slab whose top is the walkable roof at **5.7 m**. The floor is concrete at y 0. 金潮市場 GOLDEN TIDE MARKET.

**Openings:**

- Three Canal entrances with roll gates up, each 4 m wide and 3.4 m tall: x -22..-18, -15..-11 and -8..-4.
- A side door to alley A, 1.4 m (player only).
- A rear roll-up to the yard at x -7..-3 (4 m).
- The east wall (x -0.4..0, a party wall with the bakery) has no door. A door there would give a second route of
  almost equal length to Mott and make the drawn path flip.

**Inside:**

- **Stall rows** are double counters 1.8 m wide and 0.95 m tall: R1 x -21.6..-19.8, R2 x -16.4..-14.6,
  R3 x -11.2..-9.4, R4 x -6.0..-4.2. Each row has a front run (z -11..-5) and a back run (z -3..-0.5). Aisles
  between rows are 3.4 m. The west aisle is 4 m. The front aisle (behind the gates) runs z -13.6..-11, the cross
  aisle z -5..-3 and the back aisle z -0.5..1.5.
- **The fish counters** run along the east wall (x -1.4..-0.4, z -10..-1), with ice trays, styrofoam boxes and
  live tanks (opaque glass, the bubbles in the material).
- **The cold room** is at x -25.6..-18.4, z 1.5..5.6, with walls 0.25 m thick. Its door (2.0 m, a PVC strip
  curtain, art only) is in the north wall at x -21..-19, under a lit sign 冷庫 COLD ROOM. **Reel 5 is here.**
- **The stockroom** is three pallet stacks at x -15..-13.4, -12.6..-11 and -10.2..-9.4, z 2.4..5.2.
- **Overhead:** bare-bulb pendants, hanging stall boards (鮮魚 FRESH FISH, 生果 FRUIT, 蔬菜 VEGETABLES, 乾貨 DRY
  GOODS, 豆腐 TOFU, 燒味 ROAST MEAT), tarps, and skylights in the roof. All of it sits above 2.4 m and is art only,
  so it never blocks sight.
- **Sight lines:** 25 m along each aisle, 25 m across the cross aisle. The counters are chest-high cover. This is
  the close-quarters room of the level.

### 4.4 The yard, the stair and the roofs (rooftop play, player and Buzzards only)

- **The yard** is x -16..0, z 6..10, concrete at y 0, open to alley B along z 10. It holds a dumpster
  (x -1.9..-0.4, z 6.3..8.1) and a cage of gas cylinders (two propane, x -9..-7.2, z 8.8..9.8, next to the rear
  door).
- **The stair** is a steel switchback fixed to the market's south wall. It is the one climbable fire escape in
  the level.
  - Flight 1 runs west in the south lane (z 7.2..8.2), from its foot at x -9.8 (y 0) up to x -13.2 (y 2.85):
    13 risers of 0.219 m on treads of 0.26 m.
  - The mid landing is x -14.6..-13.2, z 6.0..8.2, at y 2.85.
  - Flight 2 runs east in the north lane (z 6.0..7.2), from x -13.2 to x -9.8 (y 5.7).
  - The top landing is x -9.8..-8.6, z 6.0..7.2, at y 5.7, through a gap in the roof parapet.
  - That is 26 step boxes plus 2 landings plus 2 side plates, about 30 colliders. Goons cannot climb it, because
    its boxes block nav, as the Block's shed stair does.
- **The market roof** is x -26..0, z -14..6, plus the back building B0 (x -26..-16, z 6..10), all at y 5.7, as
  tar and gravel. It has:
  - parapets 1.1 m on Canal (north), 1.0 m on alley A (west) and 1.0 m on the yard (south), except at the stair;
  - four skylight boxes 2 x 3 x 0.8 m and three condensers 1.2 m tall, as cover from Buzzards;
  - rooftop letters 金潮市場 on a steel frame standing on the north parapet. They are the landmark you see from
    Canal St, and the frame legs give cover.
- **The kitchen roof** is the bakery's one-storey rear extension (x 0..8, z -3..10) at y 5.7. It joins the market
  roof over a 0.30 m curb at x 0. Its east parapet on Mott (1.0 m) has a broken 3 m section at z 2..5, lit by the
  glow of the LILY CAFE sign opposite.

**What the roof is for:** it is optional.

- From the roof you look over Canal (Reel 4 and the street) and down Mott toward the Square.
- It is a short cut from Reel 5 to Mott St: up the stair, across the roofs and down through the gap. There is no
  fall damage, so the drop costs nothing.
- Goons cannot get up and shoot from the street, so the parapets matter. Buzzards attack freely up here. That
  rule already holds on the Block's scaffold deck.
- Three air spawns sit over the roof and yard, so the roof is never a safe camp.

### 4.5 The bakery (W3: shell x 0..8, z -14..10; walk-through shop)

- 月門餅家 MOON GATE BAKERY, in pink exposed neon.
- **The front shop** is x 0.4..7.6, z -13.6..-3.2. Its floor is at 0.15 and its ceiling at 3.8. It has a display
  counter at x 0.4..5 (the aisle is 2.6 m) and a Canal door at x 2..4.
- **The kitchen** is x 0.4..7.6, z -3..9.6, with a clear height of 5.4. A partition with a 2 m door at x 3..5
  separates it from the front shop. It has a steel table at x 3.6..5, z 4.6..8.4, plus ovens and racks of trays.
  Its doors are the Mott door (x 8, z 2..4) and the alley B door (x 4..6, z 10).
- The bakery links Canal, Mott and alley B for Goons and the player. Buzzards do not enter: the doors are 2.6 m
  tall, too low for minHeight 2.2 plus the 0.5 m body.

### 4.6 Mott Street (zone `mott`, x 8..18, z -14..32)

- West sidewalk x 8..10, one-way roadway x 10..16, east sidewalk x 16..18, kerbs 0.15.
- West-lane parking: a sedan (z -8..-3.5), a van (z 3..8.5) and a taxi (z 18..22.5).
- A box truck across the south end (x 9.6..17.6, z 27.2..29.8).
- 46 m long and narrow, so Goons push up and down it.
- The fronts on Mott: the bakery's kitchen door; S3 如意雜貨 GOOD WISHES GROCERY, with fruit boxes on the
  sidewalk; E1a's 百合茶餐廳 LILY CAFE; and the dub room's roll-up (x 18, z 24..27, 3 m, open) under the dead neon
  of 銀浪影音 SILVER WAVE VIDEO.
- The fire escape on S3's Mott face is dressing.

### 4.7 The arcade and the neon workshop (x 29.4..33.6, z -14..2; workshop x 34..37.6, z -10..-4)

- 梅花商場 PLUM BLOSSOM ARCADE. It is a covered passage 4.2 m wide and 4.2 m tall under E1, with lit arch signs
  at both mouths.
- On either side are kiosks behind glass that you cannot enter: 修錶 WATCH REPAIR, 配匙 KEYS CUT, 手機 PHONES.
- One kiosk pillar stands at x 31..31.6, z -9.5..-8.9.
- **The neon workshop** is 大光招牌 BIG LIGHT SIGNS. It opens off the arcade through a 2 m door at x 33.6,
  z -8..-6. Inside are bundles of glass tube, a bending bench, a half-finished sign glowing on the wall, and the
  torch rack (an explosive of type `rack`, which is the Block's welding rack). It is a dead-end pocket with good
  cover.
- **Role:** the arcade is the short way from the Square to the truck, used on the final run (section 7). It is
  16 m of choke, and Goons spawn in it during the pursuit.

### 4.8 The Square (x 18..44, z 2..18, paved, y 0.15)

- A small public square with a **pavilion** at its centre:
  - a plinth at x 27.5..34.5, z 6.5..13.5, y 0.15..0.45. Its top is under 0.47, so it does not block nav;
  - four columns 0.4 m square at (28.2, 7.2), (33.8, 7.2), (28.2, 12.8) and (33.8, 12.8);
  - a pagoda roof slab at 3.6..4.4. It blocks shots and Buzzards, and it is above the nav band.
- Four planters 3 x 1 x 0.9 m at the corners: (20..23, 4..5), (39..42, 4..5), (20..23, 15..16) and
  (39..42, 15..16).
- Benches and mahjong folding tables at x 23..23.8 and 38..38.8, z 9..11.
- A pair of stone guardian lions at the banquet doors, at (29.5, 16.8) and (36.5, 16.8).
- Lantern strings from the pavilion to the facades at 6 to 8 m, art only.
- This is the Buzzards' arena: 26 x 16 m of open air over three-storey E2, at most 15 m of flight ceiling.
- Exits: the Mott edge (x 18), the arcade mouth (x 29.4..33.6 at z 2) and the banquet hall doors (x 31..35 at
  z 18).

### 4.9 The banquet hall and the dub room (E2, x 18..44, z 18..32)

- **The banquet hall** is 鶴亭酒家 CRANE PAVILION BANQUET HALL, interior x 26.3..43.6, z 18.4..31.6.
  - Floor 0.15, clear height 5.0. The main doors (4 m, red lacquer with 囍 panels) are at x 31..35 on the Square.
  - Seven round tables with cloths and chairs (1.7 m collider boxes) at (29.5, 21.5), (33.5, 21.5), (29.5, 25),
    (33.5, 25), (37.5, 21.5), (29.5, 28.8) and (33.5, 28.8).
  - A stage at x 40.8..43.6, z 18.8..26.6, 0.40 high, with a backdrop panel.
  - A kitchen at x 36.4..43.6, z 27.2..31.6, with a 2 m door at x 38..40.
- **The dub room** is the Vultures' copying room, interior x 18.4..26.0, z 18.4..31.6.
  - Floor 0.15, clear height 4.2. It is reached through the Mott roll-up (3 m) or through a 2 m door in the
    partition at x 26, z 26..28 from the banquet hall.
  - Racks of reel-to-reel and tape decks against the west wall (x 18.4..19.4, z 28..31.4), a cutting table at
    x 22.2..23.8, z 20.4..22.4, towers of disc burners, boxes of blank discs, a monitor with no brand, and
    cables. **Reel 6 is here.**
- Both rooms are Buzzard-enterable interiors with doorways in the data. The doorways are the Mott roll-up and the
  hall's main doors.

### 4.10 Buildings

`ground` is 3.8 m and `upper` 3.1 m, as on the Block. A roof height is 3.8 + 3.1 x (storeys - 1), and the parapet
adds 0.9.

| Id | Footprint (x, z) | Storeys | Roof / parapet top | Front | Facade | Shops (ground; upper) | Fire escapes |
|---|---|---|---|---|---|---|---|
| N1 | -44..-29, -36..-33 | 6 | 19.3 / 20.2 | Canal | painted brick, cream | 金曲唱片 GOLD HITS RECORDS; 2F 玉壺點心 JADE TEAPOT DIM SUM (blade) | 1 (Canal) |
| N2 | -29..-15, -36..-33 | 5 | 16.2 / 17.1 | Canal | red brick | 雙鯉珠寶 TWIN CARP JEWELRY; 3F 海風旅行社 SEA BREEZE TRAVEL (window letters) | 0 |
| N3 | -15..-1, -36..-33 | 5 | 16.2 / 17.1 | Canal | buff brick | 八寶燒臘 EIGHT TREASURE BBQ (roast-duck window) | 1 (Canal) |
| N4 | -1..13, -36..-33 | 6 | 19.3 / 20.2 | Canal | brown brick, sidewalk shed in front | 春松參茸行 SPRING PINE HERBS & GINSENG | 0 |
| N5 | 13..26, -36..-33 | 5 | 16.2 / 17.1 | Canal | painted green | 長壽麵家 LONG LIFE NOODLE HOUSE; 2F 麻將 MAHJONG (window neon) | 0 |
| N6 | 26..44, -36..-33 | 7 | 22.4 / 23.3 | Canal | red brick | 晴天洗衣 SUNNY DAY LAUNDROMAT; 明月旅館 BRIGHT MOON HOTEL (4-storey blade, the east landmark) | 0 |
| W1 | -44..-30, -14..32 | 6 | 19.3 / 20.2 | Canal, alley A | red brick | 西城五金 WEST CITY HARDWARE (gate down) | 3 (alley A) |
| M | -26..0, -14..6 | 1 (hall) | 5.7 / 6.8 (Canal side) | Canal | painted block and corrugated fascia | 金潮市場 GOLDEN TIDE MARKET (walk in) | 0 (the climbable stair is separate) |
| B0 | -26..-16, 6..10 | 1 | 5.7 | alley A | common brick | market storeroom (shut) | 0 |
| W3 | 0..8, -14..-3 (front), -3..10 (one-storey rear) | 5 / 1 | 16.2 / 17.1; rear 5.7 | Canal, Mott | buff brick | 月門餅家 MOON GATE BAKERY (walk through) | 0 |
| S1 | -30..-14, 14..32 | 5 | 16.2 / 17.1 | alley B (backs) | common brick | backs | 2 (alley B) |
| S2 | -14..0, 14..32 | 5 | 16.2 / 17.1 | alley B (backs) | painted brick | backs | 1 (alley B) |
| S3 | 0..8, 14..32 | 6 | 19.3 / 20.2 | Mott | brown brick | 如意雜貨 GOOD WISHES GROCERY | 1 (Mott) |
| E1a | 18..29.4, -14..2 | 5 | 16.2 / 17.1 | Canal, Mott, Square | red brick | 金福電器 GOLDEN LUCK ELECTRONICS (Canal); 百合茶餐廳 LILY CAFE (Mott); 巧手裁縫 CLEVER HANDS TAILOR (Square) | 1 (Mott) |
| Arcade | 29.4..33.6, -14..2 | under E1 | 4.2 (ceiling) | Canal, Square | terrazzo, glass kiosks | 梅花商場 PLUM BLOSSOM ARCADE | 0 |
| E1b | 33.6..44, -14..2 | 6 | 19.3 / 20.2 | Canal | buff brick | 清晰眼鏡 CLEAR VIEW OPTICAL (Canal); 大光招牌 BIG LIGHT SIGNS (inside, off the arcade) | 0 |
| E2 | 18..44, 18..32 | 3 | 10.0 / 10.9 | Square, Mott | painted stucco, red and gold | 鶴亭酒家 CRANE PAVILION BANQUET HALL; 銀浪影音 SILVER WAVE VIDEO (the dub room) | 0 |

In total there are **10 fire-escape stacks** and one climbable stair. Only N1's and N3's escapes are in the
start view (section 13.4, flicker).

---------------------------------------------------------------------------------------------------

## 5. Player start

- **Position:** (-40.0, 0, -24.5), in the Canal roadway beside the livery sedan that dropped Rule off, just inside
  the west dig.
- **Yaw:** -1.5708 (facing east). The Unreal pose is (-4000, -2450, 0) cm, yaw 0.
- **Start pitch:** +4°. The Block uses 7° (presentation.json block.startPitch), so this needs a per-level value.
- **First view:** east down Canal. The table row and the glowing market entrances are on the right, the TWIN
  CARP and JADE TEAPOT signs on the left, and the 明月旅館 blade 77 m away above the IPX truck, so the end of the
  level is in sight from the first second. The Reel 4 marker is 30 m ahead and slightly right.
- **Patrol check:** the starting patrol must spawn at least 32 m away. 27 of the 35 ground points qualify (the
  market, Mott, the Square, east Canal).

---------------------------------------------------------------------------------------------------

## 6. Objectives and extraction

The reels are numbered 4 to 6 so the story reads as one album across the campaign, while the HUD tally counts
this level (0/3 to 3/3). Nothing in the rules reads the code as a number: the case looks up reels[i] by index.
Whether to keep 1 to 3 per level instead is open question 2.

| # | id | code | label | place | zone | interior | web pos | rotationY | Unreal pos (cm) / yaw | What it is |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | `reel4` | `4` | Reel 4 — The Tables | THE TABLES | canal | false | (-10.0, 0.15, -16.2) | 1.5708 (faces north, to the road) | (-1000, -1620, 15) / -90 | On the sidewalk between the bootleg disc table and the market front, behind the south-lane box truck. A boombox on the table plays a muffled loop. |
| 1 | `reel5` | `5` | Reel 5 — The Market | THE MARKET | market | true | (-22.5, 0, 4.4) | 1.5708 (faces its door) | (-2250, 440, 0) / -90 | In the cold room at the back of the market, on a pallet among the fish boxes. |
| 2 | `reel6` | `6` | Reel 6 — The Dub Room | THE DUB ROOM | mott | true | (21.2, 0.15, 28.4) | 1.5708 (faces north) | (2120, 2840, 15) / -90 | In the copying room, by the racks, cabled to a deck that is mid-transfer. |

**Extraction:**

- Code `IPX`, label `IPX truck`, zone `canal`, place `CANAL ST`.
- Zone pos (32.1, 0, -23.0), radius **2.5**, the same as the Block. In Unreal it is (3210, -2300, 0) cm,
  radius 250.
- Truck pos (37.5, 0, -23.0), rotationY 0 (forward east, rear doors west, toward the zone). In Unreal it is
  (3750, -2300, 0), yaw 0.
- The truck and zone are placed exactly as the Block's: zone = truck - 5.4 m x forward.
- The truck and the reel case are reused as they are (AMITruck, AMIReelCase; presentation.json objectives). The
  case's 75 cm lift suits a reel on a table or pallet.
- Before all three reels are in, the refusal prompt plays every 8 s, as on the Block. The Block's line ("Reels
  still out there — the truck won't roll without all three") is not tied to the Block's place, so Canal reuses it.

---------------------------------------------------------------------------------------------------

## 7. Critical path and guidance

### 7.1 The four legs (A* on the prototype nav; the ground path draws these)

| Leg | From → to | Length | Route the path draws | Fight |
|---|---|---|---|---|
| 1 | Start → Reel 4 | 34.5 m | East along the Canal roadway, onto the south sidewalk through a gap in the table row at x -11, then to the reel. | The patrol, from the north alcoves and the market front. |
| 2 | Reel 4 → Reel 5 | 27.4 m | Through the middle market entrance (x -15..-11), down the aisle between R2 and R3, west along the back aisle to the cold-room door. | Wave 1 arrives from both ends of Canal and the north alcoves, which pushes you into the market. |
| 3 | Reel 5 → Reel 6 | 59.6 m | Out of the cold room, east along the back aisle, through the rear roll-up, across the yard into alley B, east to Mott St, south down Mott to the dub room roll-up. | Wave 2 floods the market from the Canal gates and the yard. Alley B is the shooting lane. |
| 4 | Reel 6 → truck | 60.2 m | Through the partition door into the banquet hall, between the tables, out the main doors, across the Square, north through the arcade, across the Canal sidewalk to the truck. | Wave 3, then the pursuit, in the Square and the arcade. |
| | **Total** | **181.7 m** | | The Block's path measured the same way is 193.7 m. |

The rating's time thresholds (270 s and 400 s, flow.rating) can stay as they are at first: the route is 6 %
shorter but the fights are denser. Re-tune after playtests, as a per-level override.

### 7.2 Route ties (path flip)

Legs 3 and 4 each have a second route of similar length:

- Leg 3 via the Square and the banquet hall.
- Leg 4 via the dub room's Mott roll-up and up Mott St.

The layout makes the intended route clearly shorter:

- The market has no east door.
- The roll-up sits at z 24..27, south of the reel's partition door.

The generator must check that each intended leg is **at least 10 % shorter** than the best route that avoids it
(section 17). If the guidance lane adds hysteresis to the path, the margin can be smaller.

### 7.3 Where players get lost, and the fix

| Spot | Why | Fix (data and art, no map-specific code) |
|---|---|---|
| The market grid | Four identical rows; hanging goods cut the long view | Ground path. The cold-room sign 冷庫 is lit cold white and visible down the west aisle. The boombox loop at the case. The objective marker. |
| Three ways out of the market (gates, side door, rear roll-up) | The side door into alley A is the nearest exit from the cold room in a straight line | The path takes the rear roll-up, which is lit by a work lamp and a green exit box. The side door is a narrow dark door for the player only. Alley A loops to alley B anyway, so it is never a dead end. |
| Alley A's dog-leg | The alley seems to end in a wall | Stencilled "MOTT ST →" and a lit kitchen door at the bend (x -28, z 12), and a lantern string turning the corner. |
| The roof | After climbing the stair, the way down may not be obvious | The broken parapet on Mott is lit from the LILY CAFE sign. The stair head has a hazard-yellow handrail. A drop anywhere is safe. |
| Mott St south | The dub room roll-up is on the left among other shopfronts | The only raised shutter on Mott, with a flickering dead neon over it, and light spilling onto wet asphalt. The marker. |
| After Reel 6 | Two exits (the Mott roll-up or the banquet hall) | The path goes through the hall. The radio line names the arcade. The arcade's arch sign is the brightest object on the Square. |
| The arcade | A tunnel; the truck is not visible from the Square | The truck's beacon and the 明月旅館 blade show through the arcade's north mouth. |
| Closed shopfronts | Players try doors that are art only | Rule: open = gate up, interior lit, door gap at least 2 m. Closed = gate down and tagged, or dark glass. Never a lit, open-looking door that is solid. |

### 7.4 Hint lines (shown after no progress; the guidance lane's timing)

- Reel 4: "Reel 4's on a table outside the market. South side of Canal."
- Reel 5: "Back of the market. The cold room, by the west wall."
- Reel 6: "Out the market's back door, down the alley to Mott. The dub room's shutter is up."
- Extraction: "The truck's at the east end of Canal. Cut through the arcade off the square."

---------------------------------------------------------------------------------------------------

## 8. Enemies

### 8.1 Rules that apply unchanged

The rules come from MIGameRules and config.json:

- Pools of 12 Goons and 8 Buzzards.
- Difficulty waves: one wave per reel, three in all.
- maxAlive 9, 11 or 13 by difficulty. The pursuit budget after the last reel is 5, 8 or 12.
- ChoosePosition scores points by distance, hidden from the player's eye, last use and a random term.
- tooClose 9 m (re-pick), waves from at least 18 m, the patrol from at least 32 m, and the 26 m ring as a
  fallback.

Chinatown needs no rule change.

### 8.2 Ground spawns (35)

- y is 0 on asphalt and 0.15 on sidewalks and interior floors.
- Facing is toward the nearest opening or the play space, as the exporter's `facingSource` does.
- In the prototype, every point sits on a free nav cell in the one connected component.

| Area | Points (x, z) | Notes |
|---|---|---|
| Canal (12) | c1 (-41.5, -27.0) behind the west dig. c2 (-35, -33.3), c3 (-22, -33.3), c4 (-8, -33.3), c5 (5, -33.3), c6 (20, -33.3), c7 (31, -33.3): the north alcoves, enemies out of the shops. c8 (42.0, -31.5) east end of the north sidewalk. c9 (42.0, -16.0) east end of the south sidewalk. c10 (24, -15.0) E1a door. c11 (-36, -15.0) W1 door. c12 (24.0, -28.6) behind the double-parked box truck. | The alcoves are hidden from most of the street. |
| Alley (5) | a1 (-28, -12), a2 (-28, -4), a3 (-28, 7), a4 (-28, 12.5), a5 (-19, 12) | a3, a5 and m3 are within 9 m of Reel 5, so the 9 m re-pick drops them for that wave. |
| Market (9) | m1 (-24.2, -12.4) NW inside, m2 (-2.6, -12.4) NE inside, m3 (-23.6, 0.4) back aisle west, m4 (-6.5, 4.2) by the rear door, m5 (-13, 9.2) yard, m6 (-4.5, 8.6) yard, m7 (2.0, 7.0) bakery kitchen, m8 (-6, 12) alley B, m9 (5.5, 12.4) alley B east | `interior` is true for m1 to m4 and m7. |
| Mott and east (9) | t1 (9.0, -6) W3 side, t2 (17.0, -4) E1a door on Mott, t3 (13, 30.8) behind the south box truck, t4 (9.0, 22) S3 door, t5 (31.5, -1.0) arcade (interior), t6 (21.5, 16.6) Square SW behind a planter, t7 (42.6, 4.0) Square NE service gate, t8 (40.0, 29.5) banquet kitchen (interior), t9 (24.8, 30.4) dub room (interior) | |

### 8.3 Air spawns (18)

The Buzzard starts at the point's y. Every point is at least 2.2 m over the ground below, at most 12 m (the
ceiling is 15 m absolute), and at least 1.5 m from any collider.

| Area | Points (x, y, z) |
|---|---|
| Canal (7) | (-36, 9.5, -24.5), (-20, 10, -25), (-4, 10.5, -24.5), (12, 10, -25), (28, 10, -24.5), (40, 9.5, -25.5), (20, 11, -21.5) |
| Market roof and yard (3) | (-20, 9, -4), (-8, 9.5, 0), (-13, 8.5, 8) |
| Kitchen roof (1) | (4, 9, 3) |
| Mott (3) | (13, 10, -6), (13, 10, 8), (13, 9.5, 22) |
| Square (4) | (24, 9, 6), (36, 9.5, 6), (28, 10.5, 13), (40, 9, 13) |

### 8.4 How each wave arrives (from the prototype distances; hiding decided at run time)

- **Patrol** (unaware, at least 32 m from the start). It spreads over the market, the yard, Mott and east Canal.
  The first contact is usually a Goon stepping out of the market's east gate, or a Buzzard over east Canal.
- **Wave 1** (Reel 4 at (-10, -16.2)). The candidates at 18 m or more are the north alcoves c2 to c7, both street
  ends, the market NE corner m2 (which drops out at 6 m), alley A and the yard. The wave comes along Canal from
  east and west and out of the north shops, with Buzzards over the roadway. The market entrances behind you are
  the cover. That is the intended push.
- **Wave 2** (Reel 5, in the cold room). The candidates are the Canal doors, the bakery kitchen, alley B
  (m8, m9), m2 inside the market's NE corner, and Mott. The fight comes into the market from the front gates and
  the yard at once. The player fights out through the rear roll-up into alley B, or climbs to the roof.
- **Wave 3** (Reel 6, in the dub room). The candidates are the arcade (t5), the Square (t6, t7), the banquet
  kitchen (t8), Mott north (t1, t2) and the Canal east end. The pursuit then refills from the same pool while you
  cross the Square and the arcade. Expect contact in the arcade's 16 m tube, so the neon workshop door is the
  side pocket to fall back into.
- **The 26 m fallback ring** can land inside a building in a dense map. With 35 points spread through every
  space, ChoosePosition should never need it. The generator checks this anyway (section 17, check 6).

### 8.5 Buzzards here

- **No El.** The loader requires `el.deck`, and the Buzzards plan around it. Chinatown parks a degenerate deck
  **outside the bounds**: underside 40, rail top 40.33, x 300..301, z 300..301. Every deck test in MIEnemies.cpp
  (lines 1715-1718 and 1949-1970) is a point-in-rectangle check, so a deck 250 m outside the bounds never applies.
  No code change is needed. Making `el` optional would be cleaner, and that is the gameplay lane's choice.
- **Ceiling.** maxAltitude 15 m absolute. Only E2 (10.9 m) and the one-storey roofs can be flown over. Everything
  else is a wall, so Buzzards travel along Canal, Mott, the Square and the market airspace.
- **Orbit in narrow streets.** Orbit radius 14 to 22 m (clamp 13 to 23) is wider than Mott (10 m) and alley B
  (4 m). In those places Buzzards will press against the walls and use their detour logic. On Canal (19 m), the
  Square (26 x 16 m) and above the market roof (26 x 24 m incl. B0 and the yard) they orbit normally.
  - Play the grey box with the Block's tuning first, and count detours and stuck frames.
  - Only if they misbehave, add a per-level override applied when the loaded level is not the Block:
    orbit.radius [10, 16], radiusClamp [9, 17].
  - No air spawn is placed in alley A or B.
- **Interiors.** The market (5.4 m), the arcade (4.2 m), the banquet hall (5.0 m) and the dub room (4.2 m) all
  clear minHeight 2.2 + ceilingClearance 1.3 = 3.5 m. The bakery (3.8 m front, 2.6 m doors) is left out of the
  doorway list on purpose.

### 8.6 Hold mode (holdout) on Canal Street

Holdout is offered on Canal St: it has 35 ground and 18 air spawns, and its explosives come back every second
wave. It needs:

- a per-level mode name, "Hold Canal Street", because "Hold the Block" reads wrong here;
- a tagline, "One street. Endless Vultures.";
- a best score per level, which needs the save to change: today there is one `Best` int.

---------------------------------------------------------------------------------------------------

## 9. Explosives (18)

The hp values are as on the Block: propane 50, rack 70. The `rack` type keeps the Block's welding-rack look,
re-dressed in the fiction as a neon-bender's torch rack. Indices follow the level order, so combat item i is
level explosive i. Each item owns one collider.

| i | type | web pos (x, y, z) | zone | interior | Where and why |
|---|---|---|---|---|---|
| 0 | propane | (-32.6, 0.15, -14.6) | canal | false | dumpling cart outside W1 |
| 1 | propane | (-16.6, 0.15, -14.6) | canal | false | fried-snack stall at the market pier, a pair with 2 |
| 2 | propane | (-16.6, 0.15, -15.45) | canal | false | as 1. It is about 7 m from Reel 4 (the Block's first pair is 9 m from Reel 1). |
| 3 | propane | (-3.0, 0.15, -32.6) | canal | false | EIGHT TREASURE BBQ kitchen tanks, a pair with 4, next to alcove c4 |
| 4 | propane | (-2.15, 0.15, -32.6) | canal | false | as 3 |
| 5 | propane | (24.0, 0.15, -32.6) | canal | false | LONG LIFE NOODLE HOUSE, next to alcove c6 |
| 6 | propane | (6.6, 0.15, -14.6) | canal | false | bakery front, roasted-nut cart |
| 7 | propane | (-13.0, 0, 4.9) | market | true | stockroom, between pallets |
| 8 | propane | (-0.9, 0, -11.2) | market | true | fish-counter boiler, NE corner |
| 9 | propane | (-8.6, 0, 9.3) | market | false | yard gas cage, a pair with 10, next to the rear roll-up |
| 10 | propane | (-7.75, 0, 9.3) | market | false | as 9 |
| 11 | propane | (-26.5, 0, 8.0) | alley | false | alley A, a restaurant's back door at B0 |
| 12 | rack | (-17.0, 0, 13.4) | market | false | alley B, a sign hanger's torch rack against S1 |
| 13 | propane | (9.0, 0.15, -1.0) | mott | false | bakery kitchen's Mott door |
| 14 | rack | (37.0, 0.15, -8.4) | mott | true | the neon workshop |
| 15 | rack | (33.0, 0.15, -12.0) | mott | true | arcade, the sign-repair kiosk (the arcade narrows to 3.2 m here) |
| 16 | propane | (21.8, 0.15, 10.0) | mott | false | Square, hot-pot cart by the mahjong tables |
| 17 | propane | (41.8, 0.15, 30.8) | mott | true | banquet kitchen |

Rule of thumb: every fight space has one pair that can be shot. Nothing explosive sits within 4 m of a reel
case, a doorway centre or the extraction zone.

---------------------------------------------------------------------------------------------------

## 10. Cover points (about 104)

The rule is the exporter's:

- a point 0.6 m out from the side of a solid at least 1.0 m tall that blocks shots;
- on a free nav cell;
- facing away from the solid;
- at least 1.2 m from the next point;
- `onDeck` false everywhere.

| Area | Count | Sources |
|---|---|---|
| Canal | 34 | 9 parked vehicles (2 sides each, 18), the 2 box trucks (6), the table row's goods racks (6), the alcove jambs (4) |
| Market | 22 | the stall row ends and sides (16), fish counters (2), cold-room corners (2), pallets (2) |
| Alleys and yard | 16 | dumpsters (6), crates and pallets (4), the yard cage and stair foot (2), the bakery's alley door (2), the dog-leg corners (2) |
| Bakery | 4 | counter (2), kitchen table (2) |
| Mott | 10 | 3 parked cars (6), the south box truck (2), S3 fruit boxes (2) |
| Arcade and workshop | 4 | kiosk pillar (2), workshop door jambs (2) |
| Square | 8 | planters (4), pavilion columns, too thin to qualify, so none; benches and tables (2); lions (2) |
| Banquet and dub room | 6 | tables (4), cutting table (2) |

---------------------------------------------------------------------------------------------------

## 11. Lighting and atmosphere (night rig, new)

The rig lives in the level's own `atmos_chinatown.json`, `rigs.night`, using the Block's schema. The values below
are the starting point. They are tuned on the box against the l20 load.

### 11.1 The rig

- **Key:** one movable directional light as cool city glow. Colour #8EA6D6, about 0.3 lux, **no shadows**. There
  is no cascade atlas. Direction is high from the south-east, so silhouettes read on the north facades.
- **Sky:**
  - **No VolumetricCloud and no SkyAtmosphere.** Instead an unlit sky dome: a low overcast gradient from #3A2A24
    at the horizon (the city glow under the cloud) to #0B0D14 at the zenith, with a slow-moving cloud texture.
  - The SkyLight captures once, at load. Real-time capture is off.
  - This saves the 0.55 ms cloud shadow plus the 0.40 ms cloud reconstruction and sky capture measured on the
    box. That is about 2.4 ms on the A4000.
- **Fog:** ExponentialHeightFog sized from a `night` opacity table (the web night rig's FogExp2: colour #303035,
  0.26 opacity at 92 m). The inscattering colour is warmed toward #3A2A24. **Volumetric fog is off.** Bloom gives
  the neon halos. Volumetric fog is a quality-ladder step from render scale 0.63 up, with a 16 px grid and 64
  slices, only if the box measures it as affordable.
- **Post:**
  - Histogram auto exposure, EV100 2.0 to 4.5.
  - Local exposure: highlight contrast 0.6, shadow contrast 0.5.
  - Bloom 0.35.
  - Vignette 0.15. White balance 5600 K, so neon stays saturated and the LED lamps read cool.
  - Film grain 0 and chromatic aberration 0, for the encoder.
- **Lumen:** software, global distance field only (r.Lumen.TraceMeshSDFs=0, as the Block). Emissive sign faces and
  shop interiors feed GI through the surface cache. Every sign face of 1 m² or more must be large enough to
  survive surface-cache culling: check this in the Lumen scene view. Reflections use screen traces on, max
  roughness 0.4.

### 11.2 Real lights (at most 48 placed; at most 20 in view; at most 10 shadowed placed, at most 4 in view)

Lights are culled by their own MaxDrawDistance with fade (unshadowed 35 m with an 8 m fade; shadowed 25 m with a
6 m fade). That keeps the count in view down without a light-pool manager. The web game's rig (atmos.json
lamps.rig: the nearest lamps get real lights) is the fallback if the count in view is still too high.

| Kind | Placed | Shadowed | Type and settings |
|---|---|---|---|
| LED street lamps (cobra heads) | 6 Canal + 3 Mott | 4 Canal (x -30, -6, 18, 38) + 2 Mott (z -4, 20) | spot, 4000 K, 60° outer cone, attenuation 14 m, shadow map 512 |
| Sign wash (neon and lightbox spill on the wall and sidewalk) | 16 | 0 | rect or point at the sign colour, attenuation 5 to 7 m, no specular on the small ones |
| Market | 4 rect + 2 spot | 2 (cross aisle, cold-room door) | fluorescent 5000 K rects and bulb spots, attenuation 12 m |
| Bakery | 2 | 0 | warm 3200 K rect, pink sign wash |
| Arcade and workshop | 4 + 1 | 0 | rects along the ceiling, 4500 K; the workshop's half-lit sign |
| Alleys and yard | 3 + 1 | 0 | bulkhead lamps over back doors, 3000 K |
| Kitchen roof | 1 | 0 | the LILY CAFE spill at the broken parapet |
| Square | 1 | 1 (pavilion lantern spot) | warm spot down through the pavilion; the lantern strings are emissive only |
| Banquet hall and dub room | 3 + 2 | 1 (stage) | chandelier points (unshadowed), stage spot (shadowed), dub room work lamp and screen glow |
| Banquet kitchen | 1 | 0 | fluorescent |
| **Total** | **48** | **10** | |

Small clutter does not cast shadows: props under 0.5 m, lanterns, sign tubes, cables and hanging goods.

### 11.3 Emissive

The values follow ART_BIBLE 5.2:

- Exposed neon 400 to 2,000 nits by colour: red about 450, white about 1,200.
- Lightbox faces 100 to 300.
- LED flex 600.
- Window grid (lit flats) 8 to 15, with about 35 % of upper windows lit.
- Shop interiors through glass: the interior cube maps.

At most **3 signs flicker**, all slow dropouts and never a strobe: SILVER WAVE VIDEO (dying), the 麻將 window
neon, and one stroke of the rooftop 金潮市場. Lanterns glow red at 40 to 80 nits.

### 11.4 Wet ground

- A material parameter collection `MPC_Weather` with Wetness 0.65 drives M_MI_Surface.
  - Base colour darkens by 25 % on porous sets.
  - Roughness is clamped down to 0.22 to 0.35 on asphalt and concrete.
  - Normals flatten by 30 %.
- Puddles come from `puddles.pools` as decals (a new M_MI_Decal kind `puddle`) at roughness 0.04 with a
  rain-ripple normal off. The Block keeps Wetness 0, so its look is unchanged.
- Vertex-colour Wear A (splash/wetness) adds wet streaks at the kerbs and wall bases.

### 11.5 Steam and drips

- `steam.vents`: 7 vents, at the manholes (-24, 0.05, -24.5), (6, 0.05, -25) and (13, 0.05, 0); alley A grate
  (-28, 0.05, 2); yard kitchen vent (-10, 0.05, 9); alley B exhaust (-6, 3.0, 13.8); banquet kitchen wall vent
  (42, 3.2, 17.9).
- They use the Block's steam effect, at most 2 overlapping layers near the camera, fading out within 1.5 m of it.
- Drips are 6 small GPU-sprite emitters under awnings and fire escapes along the path. They run only within 15 m
  of the player.
- **No falling rain.**

---------------------------------------------------------------------------------------------------

## 12. Audio (per-level data, new)

audio.json `zones` and `ambience.train` are global today. Unless they move per level, the Block's reverb boxes
(underEl over the avenue, the chop shop box at x -24..6, z -31..-11) would apply in the middle of Canal St. The
level therefore needs `audio_chinatown.json` (or a `zones` block in the level file). Contents:

- **Zones:**

  | Zone | Preset | Box (web) | Fade |
  |---|---|---|---|
  | street | default | | |
  | market | `shop` | (-25.6, 0, -13.6)..(-0.4, 5.4, 5.6) | 1.5, interior |
  | bakery | `shop` | (0.4, 0, -13.6)..(7.6, 5.4, 9.6) | 1.0, interior |
  | arcade | `underEl` (a hard, low tube) | (29.4, 0, -14)..(33.6, 4.2, 2) | 1.5 |
  | banquet | `shop` | (26.3, 0, 18.4)..(43.6, 5.0, 31.6) | 1.5, interior |
  | dub room | `shop` | (18.4, 0, 18.4)..(26, 4.2, 31.6) | 1.0, interior |
  | alley | `underEl` | x -30..-26, z -14..14 and x -30..8, z 10..14, y 0..18 | 2.0 |

  A dedicated `alley` preset (a narrow, tall slot) is optional later.
- **Ambience:** wet traffic beyond the street ends; the train rumble on the bridge to the east every 90 to 150 s,
  as a distant one-shot with no visual train; mahjong tiles from N5's second floor; talk radio from the grocery;
  transformer hum at the signs (3D, 4 m range); kitchen fans (alleys); fish-tank pumps (market).
- **Surfaces:** asphalt (roads, alleys, roofs), concrete (sidewalks, Square, market, bakery, arcade, dub room),
  metal (stair, workshop), wood (stage), cloth (banquet carpet). These are the existing surface keys only.

---------------------------------------------------------------------------------------------------

## 13. Art

### 13.1 Reused from the Block (unchanged meshes and materials)

- **Facade kit:**
  - SM_Facade_BayWindow and BayBlank in Red, Brown, Buff and Painted; Pier, Fill, CornerReturn, Cornice and
    CorniceEnd, Parapet, ParapetFill and PartyWallCap;
  - ResEntry and Vestibule;
  - FireEscape_Balcony, Bracket, Ladder and Stair;
  - AirConditioner, WindowBlind, Awning_750/1026 (re-tinted fabric), StairBulkhead, RoofPanel_4m, WaterTank
    (on the S1 and E1b roofs, unreachable).
- **Furniture:** Dumpster and Dumpster_Shut, TrashBags A and B, MilkCrate(s), Pallet and PalletStack, cardboard
  boxes, ShoppingCart, NewspaperBox, Mailbox, SignPost, Bollard, JerseyBarrier, TrafficBarrel, TrafficCone,
  Barricade, OilDrum, StreetLamp, RollUpDoor_* (all gates), SteelDoor_190x242, SidewalkShed (N4 and Mott south),
  ChainLink (yard edge), BlockWall.
- **Gaps:** traffic light (Canal/Mott corners, 2), food cart (re-dressed as the dumpling and nut carts), vending
  machine, trash can, planter (Square, re-tinted stone).
- **Street kit:** road, kerb, sidewalk, manhole, drain, hydrant.
- **Vehicles:** Taxi, Van, BoxTruck, Sedan, SUV, Motorbike (delivery mopeds, 2), IPXTruck.
- **Gameplay:** master case and reels, boombox, propane_tank, welding_rack (the torch rack); Goons; the Buzzard.
- **Signs:** the signs.py builders (lightbox, exposed neon on a pan, LED flex, open-face pan letters) and the
  MI_Neon_<Colour> materials.
- **Other:** the six interior cube maps (TC_*) for window parallax; the backdrop generator and window-grid
  material (tenements and a few 20- to 30-storey towers; a simplified suspension-bridge silhouette far to the
  east); the 7 decal kinds; the steam effect.

### 13.2 New

The new art is in a family `art/blender/assets/chinatown.py`, plus extensions to signs.py and facade.py that
leave the Block's output byte-identical. Triangle counts are what the SM5 game draws, so they are LOD0 / Nanite
fallback triangles.

| Asset | Count | Tris each (budget) | Notes |
|---|---|---|---|
| SM_Facade_Shopfront_CT_{Wide, Narrow, Restaurant, Jewelry, Grocery} | 5 generic modules | 6-15k | Not one module per shop: the sign is a separate actor from the sign atlas, so 14 shops need 5 meshes. Roll gates are reused. |
| SM_Facade_CT_WindowGrille, CT_StackedSignRail | 2 | 1-3k | Security grilles on low windows; the steel rail that carries the stacked signs |
| Sign carriers: SM_Sign_CT_Blade_4m / 6m / 12m, SM_Sign_CT_Band_{6,8,10}m, SM_Sign_CT_Arch (arcade), SM_Sign_CT_RooftopFrame (market letters) | 9 | 2-12k | Faces in the atlases (13.5). Exposed-neon Chinese characters are tubes generated from font outlines, 6-sided tube profile, at most 12k per sign. |
| Market hall shell: walls, roof slab, parapets, skylights, rooftop gravel | 1 set | 40k total | Fitted to the colliders (structures.py's measuring step) |
| Market stall counter (2 m), fish counter with ice tray, produce crate stack, dry-goods sacks and bins, styrofoam boxes, hanging stall board, tarp, pendant bulb cage, fish tank, hanging scale, hand truck | 11 | 1-6k | Instanced (ISM) |
| Vendor folding table with cloth; goods clusters: unbranded bags, generic watches in a case, sunglasses rack, "NEW YORK" T-shirts, "CANAL ST" caps, phone cases and chargers, the disc and USB-stick table; market umbrella; clothing rail | 9 | 2-6k | No logo, monogram or pattern that resembles any brand |
| Red paper lantern A and B, lantern string | 3 | 0.6k | ISM, at most 120 instances |
| Pavilion (plinth, 4 columns, pagoda roof) | 1 | 40k | Roof tiles as a tiling set, not modelled one by one |
| Guardian lion (stone) | 1 (mirrored) | 15k | Generic cultural form, no copy of a real statue |
| Mahjong folding table and stools, park bench | 3 | 1-3k | |
| Banquet round table with cloth and 8 chairs, stage and backdrop panel (囍), red lacquer double door, chandelier, kitchen range and woks | 5 | 3-10k | Tables and chairs as ISM |
| Dub room: reel-to-reel deck, tape deck rack, disc-burner tower, blank-disc boxes, cutting table, monitor without a brand, cable bundles | 7 | 2-8k | |
| Neon workshop: tube bundles, bending bench, transformer boxes, half-finished sign | 4 | 2-6k | |
| Bakery: display case (opaque glass), trays of buns, counter, ovens, rack trolleys | 5 | 2-6k | |
| Roast-duck window display (N3) | 1 | 6k | |
| SM_Struct_CT_YardStair (the climbable switchback) | 1 | 12k | Fitted to its 30 colliders; chunky 48 mm pipe rails (flicker, 13.4) |
| Rooftop: condenser, skylight, roof hatch | 3 | 2-5k | |
| Decals: `puddle` (new kind), red firecracker paper, gum, painted kerb, stencil "MOTT ST →" | 5 kinds | | M_MI_Decal |

### 13.3 Signs and names (invented; Traditional Chinese, Cantonese usage)

Every name below is made up for the game. Before any face is drawn:

1. **Search each name** as written, in English and in Chinese, against New York, and change any that turns out to
   be a real business, brand or trade dress. Pearl River, Kowloon, Golden Phoenix and an electronics maker's Hong Kong trade
   name (樂聲) were already avoided for that reason.
2. **A reader of Traditional Chinese must check every string** for meaning and register, and sign it off in this
   table before the art is final. No reader has checked them yet (open question 3).
3. **No phone numbers.** Manhattan would be (212), which ART_BIBLE 5.7 does not allow without the owner's approval.
   **No web addresses.**
4. **The new real place names** need the lead to add them to ART_BIBLE 5.7's list of allowed real places:
   CHINATOWN, MANHATTAN, CANAL ST, MOTT ST, and the bridge as an unnamed silhouette.

| Sign | Chinese | Meaning | Where | Built as | Night |
|---|---|---|---|---|---|
| GOLDEN TIDE MARKET | 金潮市場 | golden-tide market | market: rooftop letters + Canal band + 2 blades | rooftop open-face pan letters with red neon; band lightbox | on; one stroke flickers |
| Stall boards: FRESH FISH, FRUIT, VEGETABLES, DRY GOODS, TOFU, ROAST MEAT | 鮮魚, 生果, 蔬菜, 乾貨, 豆腐, 燒味 | generic trade words | market stalls | painted boards | lit by bulbs |
| COLD ROOM | 冷庫 | cold storage | cold-room door | small lightbox, cold white | on |
| MOON GATE BAKERY | 月門餅家 | moon-gate bakery | W3 Canal | pink exposed neon + band | on |
| WEST CITY HARDWARE | 西城五金 | west-city hardware | W1 Canal | lightbox | off (shut, gate down) |
| LANTERN ALLEY | 燈籠巷 | lantern lane | alley A mouth | painted wooden board | lit by lanterns |
| GOLD HITS RECORDS | 金曲唱片 | golden-hits records | N1 ground | lightbox band; "CDs · VINYL" in the window | on |
| JADE TEAPOT DIM SUM | 玉壺點心 | jade-teapot dim sum | N1 2F, 6 m blade | exposed neon red and green | on |
| TWIN CARP JEWELRY | 雙鯉珠寶 | twin-carp jewellery | N2 | gold-on-red lightbox, the brightest band | on |
| SEA BREEZE TRAVEL | 海風旅行社 | sea-breeze travel agency | N2 3F | window vinyl | lit window |
| EIGHT TREASURE BBQ | 八寶燒臘 | eight-treasure roast meats | N3 | lightbox + roast-duck window | on |
| SPRING PINE HERBS & GINSENG | 春松參茸行 | spring-pine ginseng and herb shop | N4 | lightbox band | on |
| LONG LIFE NOODLE HOUSE | 長壽麵家 | long-life noodle house | N5 | lightbox + neon bowl outline | on |
| MAHJONG | 麻將 | mahjong | N5 2F window | green window neon | flickers |
| SUNNY DAY LAUNDROMAT | 晴天洗衣 | sunny-day laundry | N6 ground | lightbox, cold interior | on |
| BRIGHT MOON HOTEL | 明月旅館 | bright-moon hotel | N6, 12 m blade (4 storeys) | white and blue exposed neon | on: the east landmark over the truck |
| GOLDEN LUCK ELECTRONICS | 金福電器 | golden-luck electrical | E1a Canal | LED flex outline + band | on |
| LILY CAFE | 百合茶餐廳 | lily tea restaurant | E1a Mott | lightbox | on (lights the roof gap) |
| CLEVER HANDS TAILOR | 巧手裁縫 | clever-hands tailor | E1a, Square side | small lightbox | on |
| PLUM BLOSSOM ARCADE | 梅花商場 | plum-blossom arcade | both arcade mouths | lit arch, channel letters | on |
| Kiosks: WATCH REPAIR, KEYS CUT, PHONES, NEON SIGNS | 修錶, 配匙, 手機, 光管招牌 | generic trades | arcade | small lightboxes | on |
| BIG LIGHT SIGNS | 大光招牌 | big-light signs | neon workshop | half-finished glowing sign | on |
| CLEAR VIEW OPTICAL | 清晰眼鏡 | clear-view glasses | E1b Canal | lightbox | on |
| CRANE PAVILION BANQUET HALL | 鶴亭酒家 | crane-pavilion restaurant | E2 Square | red and gold band; 囍 (double happiness) on the doors | on |
| SILVER WAVE VIDEO | 銀浪影音 | silver-wave audio-video | E2 Mott, over the dub room | exposed neon, half dead | flickers |
| GOOD WISHES GROCERY | 如意雜貨 | as-you-wish grocery | S3 Mott | lightbox + fruit boxes | on |
| SHOP FOR RENT / FOR LEASE | 吉舖出租, 招租 | vacant shop to let | upper windows | paper signs, no numbers | |
| Opera gala poster | 粵劇 · 春暉劇團 | Cantonese opera, "Spring Sunshine Troupe" | walls | wheat-paste, no faces | |
| Vendor placards | | "CDs $5", "USB $10", "BAGS $20", "SUNGLASSES $5", "3 FOR $10" | tables | card and marker | |
| Street blades | | CANAL ST, MOTT ST | corners | plain green blade, no agency mark | retroreflective |
| Graffiti | | VULTURES, VLTR (oxblood), RULE, INC (gold) | alleys, gates | spray paint | |

### 13.4 Rules for this level's art

- **Fonts.** The art bible allows OFL or Apache type only (ART_BIBLE 5.6). Chinese faces use Noto Serif CJK TC
  and Noto Sans CJK TC (OFL), subset to the glyphs used, so only small files land in art/blender/fonts. The sandbox
  also has WenQuanYi Zen Hei (GPL with a font exception), which is acceptable for baked textures if the lead
  prefers it. Sign painters' brush lettering comes from the serif face with a hand-drawn wobble pass in PIL.
- **Fire escapes and flicker.** Thin steel flickers at render scale 0.50 (READY.md R3). The rules:
  - 10 stacks in all, 2 in the start view;
  - railings at least 40 mm thick;
  - no thin steel on the critical-path sight lines in the market, alley B and the arcade;
  - each new stack is checked with flicker.py rev8 at 0.50 against the Block's avenue in the same run.
- **No real marks.** No Chinatown organisation, association, tong, temple or school is named. No political
  posters. No real songs or artists on discs or posters.
- **Collision.** The art carries no collision (as the Block). Every structure that the player stands on or fights
  around (market hall, stair, pavilion, stage) is fitted to its colliders with structures.py's measure-every-vertex
  step.

### 13.5 Textures (share, atlas, avoid 8K)

- **Tiling sets reused:** bricks (Red, RedDark, Brown, Buff, Painted), stucco, concrete, asphalt, pavers,
  corrugated, steel plates, tiles; TS_Roof_ScanBitumen and TS_Roof_ScanGravel **at 2K, not the 8K versions**.
- **New tiling sets (at most 12, 2K):**
  - TS_Tile_Quarry (market floor), TS_Terrazzo (arcade), TS_Paint_RedLacquer, TS_Wood_Lacquer;
  - TS_Fabric_Awning (tinted in the material), TS_Tarp_Blue, TS_Carpet_Banquet;
  - TS_Metal_DiamondPlate (yard), TS_Styrofoam, TS_Stone_Granite (lions, plinth);
  - TS_Paper_Lantern, TS_Tile_RoofGlazed (pavilion).
- **Unique sets (at most 30, 2K):** the market stall dressing, vendor goods (one atlas), dub room kit, bakery kit,
  roast-duck window, pavilion, lion, banquet set, workshop kit.
- **Sign faces: 3 atlases of 4096 x 4096**, at most about 40 faces, instead of one 4096 x 512 set per shop:
  - BC: BC7.
  - Emissive: a BC4 mask times a per-sign colour parameter.
  - ORM: shared.
  - About 32 MB per atlas with mips, 96 MB in all.
  - Neon tubes need no texture (MI_Neon_<Colour>).

---------------------------------------------------------------------------------------------------

## 14. Budgets on E3DS (RTX A4000, 8 threads, SM5, no Nanite, 1920 x 1080 stream)

The bar is the Block's measured envelope. Every number is checked on the box with the E3DS-faithful load
(`lag-test.sh ... load=1:0.05:0:1024`, l20) at 1080p, with the Block in the same run, and then on E3DS.

| Item | Block (known) | Canal Street budget |
|---|---|---|
| GPU frame, A4000, render scale 0.50 to 0.63 | 10.2 to 13.3 ms (E3DS, Story, no fight); 13.2 ms box l20 at 0.50 | **at most 13.0 ms in the worst view with a 9-enemy fight**; aim for 11.5. At most the Block + 0.5 ms in the same run. |
| Game thread | not profiled on E3DS | at most 6 ms (colliders at most 800 keep ray casts at the Block's cost) |
| Render thread / RHI | 7.7 / 3.3 ms (16-core box) | at most 7.5 / 3.5 ms on E3DS's 8 threads: measure there, not only on the box |
| Colliders (axis-aligned boxes, brute-force rays) | 777 | **at most 800** (planned about 780, 14.1) |
| Oriented boxes sliced into colliders | 322 | at most 40 (everything parked square to the street) |
| Actors | 1,083 | at most 1,100 (facades as one holder per building with ISMs; signs merged per building) |
| ISM instances | 1,350 | at most 2,200 (lanterns, stalls, chairs, goods) |
| Triangles drawn (SM5 fallback), worst view | unmeasured | **at most 1.5 M** (aim 1.1 M); shadow-depth passes at most 0.8 M |
| Draw calls (mesh draw commands), worst view | unmeasured | **at most 1,500** base pass; at most 600 across shadow passes |
| Local lights | none (day) | 48 placed / at most 20 in view / 10 shadowed placed / at most 4 shadowed in view |
| Translucency | steam | at most 2 layers (steam) near the camera; no rain; glass is opaque (M_MI_Glass) |
| Texture streaming want at 1080p, worst view | 717 to 865 MB against a 600 MB pool | **at most 800 MB**, which assumes the 1000 MB pool of READY.md R4. If the pool stays at 600: LOD bias +1 on the sign atlases and dressing sets, and at most 600 MB. |
| New texture sets | 225 in the Block | at most 12 tiling + 30 unique + 3 sign atlases (about 600 MB on disk) |
| Cooked size added by the map | one version is 2.1 to 2.2 GB | at most +0.9 GB (E3DS storage is 10 GB) |
| Card memory through a run | 6.1 to 6.8 GB | at most 7.0 GB |

**Shared risk with the Block: vehicles and the road.** Vehicles are 150k to 179k triangles each, and
SM_Street_Road_20m is 234k. Canal St's worst view holds about 10 vehicles and 5 road pieces. At default Nanite
fallback settings that view alone could pass 1.5 M. Before Canal St art goes in:

- set the Nanite fallback explicitly (fallback_percent_triangles, or a hand LOD) to at most 25k per vehicle and
  at most 20k per road piece;
- measure the Block's SM5 baseline (`stat rhi`, `stat scenerendering`, `stat initviews`), which nobody has done
  yet;
- set the per-asset budgets in 13.2 from that baseline.

**Worst views to measure:**

1. Canal St from the start, looking east.
2. The market cross aisle with wave 2 in it.
3. The Square from Mott with 4 Buzzards.
4. Inside the arcade, looking at the Canal mouth.
5. The market roof, looking north over Canal.

### 14.1 Planned collider breakdown (about 780)

| Group | Boxes |
|---|---|
| Ground: sidewalks, kerbs, raised floors (bakery, arcade, banquet, dub room, Square), stage, plinth | 34 |
| Building shells and the facade alcoves (N row 13, W1, B0, S row, E1a/b, E2 outer) | 70 |
| Market: walls with openings 12, stall rows 8, fish counters 3, cold room 5, pallets 3, skylights and condensers on the roof 7, roof slab and parapets 8 | 46 |
| Bakery: walls 10, counter, table, ovens 5 | 15 |
| Arcade and workshop: walls and kiosks 16, pillar 1 | 17 |
| Banquet and dub room: walls 12, tables 7, stage 1, kitchen 4, racks and cutting table 4 | 28 |
| Climbable stair and landings | 30 |
| Kitchen roof slab and parapets | 6 |
| Vendor tables, goods racks, carts | 34 |
| Vehicles: 12 parked + IPX truck, sliced as the exporter does (about 5 per car, 8 per truck) | 76 |
| Street furniture: hydrants, mailboxes, newspaper boxes, trash cans and bags, crates, cardboard, barrels, cones, bollards, lamp and light posts, shed posts | 230 |
| Alleys and yard: dumpsters, crates, pallets, AC units at ground level, gates | 60 |
| The Square: columns 4, roof 1, planters 4, benches and tables 4, lions 2 | 15 |
| Explosives | 18 |
| Map edges: barriers, dig plates, end trucks | 30 |
| Spare | 71 |
| **Total** | **about 780** |

---------------------------------------------------------------------------------------------------

## 15. Level data (`level_chinatown.json`, the Block's schema)

The C++ reads these sections today (MILevelData.cpp:86-198). Every one marked "loader" is required with no
fallback. The others feed the art builder, the tests or the guidance lane.

| Key | Read by | Chinatown content |
|---|---|---|
| `meta` | reference | file, game, schema 1, generator (the new layout tool, not the web exporter), units, conversion (the Block's strings), counts {colliders, orientedBoxes, enemySpawns {35, 18}, coverPoints, explosives 18, objectives 3, …} |
| `bounds` | loader (play bounds) | web {minX -44, maxX 44, minZ -34, maxZ 32}; ue {-4400, 4400, -3400, 3200} |
| `zones[]` | loader (spawn zones), text | `canal` x -44..44, z -34..-14 "CANAL ST"; `alley` x -44..-26, z -14..32 "LANTERN ALLEY"; `market` x -26..8, z -14..32 "THE MARKET"; `mott` x 8..44, z -14..32 "MOTT ST". Together they tile the bounds. |
| `places.regions` | zone names on the HUD | CANAL ST (canal); LANTERN ALLEY (x -44..-26, z -14..32 and x -26..8, z 10..14); THE MARKET (x -26..0, z -14..10); THE BAKERY (x 0..8, z -14..10); THE BACKS (x -26..8, z 14..32, roofs and backs); MOTT ST (x 8..18, z -14..32); THE ARCADE (x 18..44, z -14..2); THE SQUARE (x 18..44, z 2..18); THE BANQUET HALL (x 18..44, z 18..32) |
| `ground.surfaces` | art, audio | asphalt: Canal roadway, Mott roadway, alleys A and B, roofs; concrete: sidewalks, Square, yard, market, bakery, arcade, dub room; metal: stair, workshop; wood: stage; cloth: banquet floor |
| `ground.floors` | art, tests | 0: roads, alleys, yard, market; 0.15: sidewalks, Square, bakery, arcade, banquet, dub room; 0.45: pavilion plinth; 0.55: stage; 2.85: stair landing; 5.7: market roof, B0, kitchen roof |
| `playerStart` | loader | zone canal, web pos (-40.0, 0, -24.5), yaw -1.5708, facing (1, 0, 0); ue (-4000, -2450, 0), yaw 0 |
| `objectives[]` | loader, rules, HUD | the three rows of section 6 (index, id, code, label, zone, place, interior, prop, web pos/rotationY/forward, ue) |
| `extraction` | loader, rules | section 6; truck.pos and rotationY are required (loader line 128) |
| `enemySpawns.points` | loader, spawning | 35 ground + 18 air (section 8), each with type, zone, place, interior, facing and facingSource |
| `coverPoints.points` | loader, AI | about 104 (section 10), onDeck false |
| `explosives.items` | loader, combat | 18 (section 9), each with its collider index (owner kind explosive) |
| `interior` | loader, AI, audio | fade 1.5. boxes: market (-25.6, 0, -13.6)..(-0.4, 5.4, 5.6); bakery front (0.4, 0, -13.6)..(7.6, 3.8, -3.2); bakery kitchen (0.4, 0, -3.0)..(7.6, 5.4, 9.6); arcade (29.4, 0, -14)..(33.6, 4.2, 2); workshop (34.0, 0, -10)..(37.6, 3.8, -4); banquet (26.3, 0, 18.4)..(43.6, 5.0, 31.6); dub room (18.4, 0, 18.4)..(26.0, 4.2, 31.6). doorways (outside → inside, y): market gates (-20, 2.6, -16.5)→(-20, 2.6, -11.8), (-13, …), (-6, …); market rear (-5, 2.6, 8.6)→(-5, 2.6, 3.6); arcade north (31.5, 2.6, -16.5)→(31.5, 2.6, -11); arcade south (31.5, 2.6, 4.5)→(31.5, 2.6, -1); banquet doors (33, 2.5, 15.5)→(33, 2.5, 20.0); dub room roll-up (15.5, 2.4, 25.5)→(21.0, 2.4, 25.5). That is 8 doorways. |
| `vantage` | reference, tests | stairsFoot (-9.4, 0, 7.7); deck (-12, 5.7, -4) (the market roof) |
| `cinematicPath.points` | loader (title camera) | 14 keys, section 15.1 |
| `steam.vents` | art, FX | 7 (11.5) |
| `puddles.pools` | art (wet decals) | about 18: along both Canal gutters (z -29.6 and -19.2) every 8 to 12 m, radius 0.8 to 2.4; Mott gutters; alley low points (-28, 6) and (-10, 12); the yard drain (-6, 9); the Square's SW corner |
| `buildings` | art, tests | storeys {ground 3.8, upper 3.1}; list = the 4.10 table (id, name, wall, floors, colliders, web rect, roof, parapetTop); backs [] |
| `el` | loader (deck only) | `deck` degenerate outside the bounds (8.5): {underside 40, railTop 40.33, minX 300, maxX 301, minZ 300, maxZ 301, tracksZ []}; `present: false`; bents, columns, girders, station, layout empty. The art builder must skip the El when `present` is false. |
| `train` | not read by C++ | omitted; the train pass is per-level audio (12) |
| `nav` | Golden-style test | generated by the same rule (`physics` constants), cols 176, rows 132, origin (-44, -34); must equal FMIBoxWorld's rebuild cell for cell |
| `physics` | reference | the Block's constants, unchanged: STEP_HEIGHT 0.42, NAV_CELL 0.5, NAV_INFLATE 0.5, band 0.47..1.5, … |
| `colliders.boxes` | loader (collision, sight, nav) | about 780 AABBs with tag, surface, owner, blocks and flags (14.1); byTag, byOwner and bySurface summaries |
| `orientedBoxes` | art, reference | few or none |
| `signage` | art | placements for the about 40 sign faces + about 120 posters, decals, stencils and graffiti; paintings = atlas regions |
| `glazing` | art | shop windows, the bakery case, arcade kiosks, upper windows |
| `facades` | art (window lights) | grids and faces per building face; at night about 35 % of the upper windows lit |
| `layout` | art, reference | CANAL {northFacade -33, northKerb -29.8, southKerb -19, southFacade -14, alcoves [-35, -22, -8, 5, 20, 31]}, MOTT {westFacade 8, westKerb 10, eastKerb 16, eastFacade 18}, ALLEY_A, ALLEY_B, MARKET, YARD, STAIR, ROOF_Y 5.7, BAKERY, ARCADE, WORKSHOP, SQUARE, PAVILION, E2, DUB |

### 15.1 Title camera (cinematicPath, 14 keys; pos → look)

| Key | pos (x, y, z) | look (x, y, z) | Shot |
|---|---|---|---|
| 0 | (-41.5, 4.6, -24.5) | (-12, 2.2, -19) | Canal from the dig |
| 1 | (-30, 4.0, -23.5) | (-10, 1.4, -16.5) | the tables |
| 2 | (-18, 3.4, -21.0) | (-10, 1.2, -16) | Reel 4's table |
| 3 | (-13, 2.8, -17.0) | (-13, 1.6, -8) | into the middle market gate |
| 4 | (-13, 3.0, -9) | (-20, 1.2, -2) | the stall rows |
| 5 | (-17.5, 3.2, -1.5) | (-22.5, 0.8, 4.4) | the cold-room door |
| 6 | (-8, 3.2, 1.0) | (-5, 2.4, 9) | toward the rear roll-up |
| 7 | (-5, 3.0, 8.5) | (8, 2.0, 12) | the yard and alley B |
| 8 | (4, 3.4, 12) | (16, 2.0, 20) | out onto Mott |
| 9 | (13, 4.0, 14) | (18, 1.6, 25.5) | the dub room shutter |
| 10 | (16, 5.0, 8) | (31, 2.2, 10) | the Square and the pavilion |
| 11 | (26, 4.2, 6) | (33, 2.0, 18) | the banquet doors and lions |
| 12 | (31.5, 2.8, 4.0) | (31.5, 2.0, -14) | into the arcade |
| 13 | (31.5, 3.0, -16.5) | (37.5, 1.6, -23.0) | the IPX truck on Canal |

The front-end thumbnail `T_UI_Level_Chinatown` is a 16:9 frame from key 1.

### 15.2 `levels.json` entry

```json
"chinatown": {
  "id": "chinatown",
  "text": "frontend.levels.chinatown",
  "map": "/Game/Maps/L_Chinatown",
  "data": {"level": "level_chinatown.json", "props": "props_chinatown.json", "atmos": "atmos_chinatown.json", "audio": "audio_chinatown.json"},
  "place": {"night": "frontend.levels.chinatown.place.night"},
  "times": ["night"],
  "provides": {
    "playerStart": true, "objectives": 3, "extraction": true,
    "enemySpawns": {"ground": 35, "air": 18},
    "nav": true, "coverPoints": true, "explosives": true, "titlePath": true, "showroom": null
  },
  "preview": {"camera": "titlePath", "thumbnail": {"asset": "T_UI_Level_Chinatown", "status": "missing", "notes": "16:9 frame from title key 1 (the tables)"}},
  "notes": "Level 2. provides is checked against level_chinatown.json by a per-level DataLoads test; 18 explosives, 14 title keys, 3 reels."
}
```

`order` becomes ["block", "chinatown", "midtown"]. `default` stays "block".

### 15.3 Per-level text (frontend_text.json `frontend.levels.chinatown`; never shadows text.json)

Lines that name the player use `{name}` for DEUCE, SMOKE and KEYS. Rule's own line is the same sentence with
"Rule" (crew.json lines.replaces).

```json
"chinatown": {
  "name": "Canal Street",
  "blurb": "Chinatown after the rain. The tables, the market, the dub room. Tight corners, lots of neon.",
  "place": {"night": "Chinatown, Manhattan · Canal St · 7:40 PM"},
  "story": {
    "eyebrow": "IPX PRESENTS · CHINATOWN, MANHATTAN",
    "tagline": "Three more masters. One market. Tight corners.",
    "taglineHoldout": "One street. Endless Vultures.",
    "holdoutName": "Hold Canal Street",
    "objectives": ["Take back three more masters", "Two masters left", "Last master", "Get to the IPX truck"],
    "radio": {
      "intro": "{name}, it's the Vault. Vultures moved three more masters to Canal — the tables, the market, the dub room. Bring them home.",
      "introRule": "Rule, it's the Vault. Vultures moved three more masters to Canal — the tables, the market, the dub room. Bring them home.",
      "reel": ["That's one. Canal heard it — more coming.", "Two. They're pouring out of the back rooms.", "All three. The IPX truck is idling at the east end of Canal. Cut through the arcade. Move."],
      "done": "Masters are in the vault. Canal's clean, {name}. They're taking what's left uptown.",
      "introHoldout": "Vultures are coming out of every door on Canal. Hold the street, {name}."
    },
    "cards": {"debriefKicker": "Chinatown, Manhattan · Debrief", "debriefTitle": "Canal is yours", "deadTime": "Time on Canal"},
    "boot": ["Lighting the signs", "Hosing down the market", "Stacking the tables", "Waiting out the rain"],
    "zones": {"canal": "CANAL ST", "alley": "LANTERN ALLEY", "market": "THE MARKET", "mott": "MOTT ST"},
    "hints": ["Reel 4's on a table outside the market. South side of Canal.", "Back of the market. The cold room, by the west wall.", "Out the market's back door, down the alley to Mott. The dub room's shutter is up.", "The truck's at the east end of Canal. Cut through the arcade off the square."]
  }
}
```

The radio lines are kept within the Block's lengths: the intro runs about 125 characters, as the Block's does
(4.4 s at 58 characters per second). The `prompts.refuse` and `radio.contact` lines are reused from text.json.

---------------------------------------------------------------------------------------------------

## 16. What this level needs from the code and pipeline lanes (none of it changes the Block)

These are shared with Level 3. Owners and order are for the lead (MAPS.md).

1. **Level-aware data.** `FMILevelData::Get(LevelId)` loads levels.json `data.level`. `Get()` stays the Block,
   so every golden and run test is unchanged. `rules`, `text`, `audio` and `atmos` are chosen the same way.
2. **Map travel** on "Hit the block" and on a debrief "Next: Canal Street", with the set-up handed over and the
   intro on arrival. It must come from game code: the cloud console refuses `open`. Add L_Chinatown (and
   L_GreyChinatown) to BlockMaps, or make the check read levels.json maps.
3. **Times per chosen level.** Boot reads the default level's `times` and refuses night. It must read the loaded
   level, and build `rigs.night` from the level's atmos file (11.1).
4. **Per-level audio zones and ambience** (12). Without this the Block's chop shop reverb box lands on Canal St.
5. **Per-level strings** (15.3), falling back to text.json for the Block. That covers the HUD location card,
   objective lines, radio, cards, boot lines, zones, the mode display name and the eyebrow.
6. **Per-level `startPitch`** (4°), and per-level rating thresholds if the playtests ask for them.
7. **Save:** completed levels, plus a best score per level for Hold mode.
8. **Optional:** a per-level Buzzard orbit override (8.5), and `el` made optional instead of the degenerate deck.
9. **Generator and tests:**
   - The layout tool writes `level_chinatown.json` from a rectangle table (Appendix A is the seed).
   - mi_greyblock_map.py takes a level id and makes L_GreyChinatown.
   - New tests: Level.Chinatown.Nav (rebuild equals file), Level.Chinatown.DataLoads (provides vs file), and a
     Run.StoryComplete smoke test on Chinatown.
10. **Art builder.** build_block.py is parameterised by level: map path, data files, street extent, backdrop and
    rig from levels.json and the level's atmos. It must reproduce L_Block exactly.
    - send-art.sh learns the `SM_*_CT_*` patterns.
    - package-cloud.sh cooks /Game/Maps/L_Chinatown, and the start map stays L_Block.

---------------------------------------------------------------------------------------------------

## 17. Checks the level data must pass (generator gates, before any art)

1. **Nav equality.** FMIBoxWorld's grid rebuilt from `colliders` equals `nav` cell for cell.
2. **Connectivity.** One component holds:
   - the start;
   - a cell within 2.2 m of each reel (and 2.5 m vertically);
   - the extraction disc;
   - every ground spawn, or a cell within 4 m of it.
3. **Legs.** Each leg is within ±10 % of section 7.1. The intended routes for legs 3 and 4 are at least 10 %
   shorter than the best alternative.
4. **Gaps and steps.**
   - Every Goon doorway is at least 2.0 m wide.
   - Every walkable step is at most 0.42 m.
   - The stair is walked bottom to top and back by a PlayerSim test.
   - A drop from every roof edge lands on a walkable cell.
5. **Spawns.**
   - Ground points are on free cells.
   - Air points are 2.2 to 12 m over the ground below, at least 1.5 m from any box, and inside the bounds minus
     the Buzzards' margin of 1.2 m.
6. **Fallback ring.** Sample player positions every 2 m on the nav. At each one, count the ground points at least
   9 m away and hidden from the eye (1.6 m) by the box ray cast. If any sample has fewer than 3, add a point near
   it.
7. **Colliders.** At most 800, all axis-aligned. Explosive collider indices match `explosives.items`. Every
   interior doorway's inside point lies in exactly one interior box.
8. **Run smoke.**
   - Story completes on the scripted route.
   - Holdout spawns both kinds.
   - The Block's goldens still pass unchanged.
9. **Performance gates** (14): the five worst views on the box with l20 at 1080p, then on E3DS. Flicker
   (rev8 at 0.50) on the alley A and Mott fire escapes. Texture streaming want and cooked size recorded.
10. **Content.** Every name in 13.3 searched, the Chinese signed off, no brand look-alikes (ART_BIBLE 5.7).

---------------------------------------------------------------------------------------------------

## 18. Build order

1. **Data first.** Write the rectangle table (Appendix A, finished), generate `level_chinatown.json`, pass
   checks 1 to 7, and build L_GreyChinatown. Play the grey box on the box: spawns, Buzzards in the narrow
   streets, the roof, the guidance path. Tune the points and cover. No art yet.
2. **Light prototype in the grey box.** Night rig, the 48 lights on their posts, wet M_MI_Surface on grey boxes,
   emissive placeholder sign quads. Measure the worst views with l20. This decides the light count before any
   sign is drawn.
3. **Blender:**
   - the Chinatown family;
   - signs.py atlases and Chinese tube lettering;
   - facade tables for N1 to N6, W1, W3, S1 to S3, E1a/b and E2 (as data, beside the Block's SHOPS and
     BUILDINGS, not in them);
   - placements;
   - fitting to the colliders.
4. **The box:** import (Interchange, explicit Nanite fallback settings), build L_Chinatown with the parameterised
   builder, then picture rounds (shot.sh / play-shots.sh), the flicker check and the five performance views.
5. **E3DS:** package with the three maps, measure the cooked size and the worst views in the stream, play end to
   end from the front end through the Block into Canal Street.

---------------------------------------------------------------------------------------------------

## 19. Open questions (owner or lead)

1. **Time of day.** This design picks night (7:40 PM, wet). The other option is dusk, about 4:45 PM, sun at 2 to
   4°. Dusk keeps the sun cascade and needs the clouds, losing their quality step. It also reads as "lots of
   neon" only in the shade.
2. **Reel codes** 4 to 6 (one album across the levels, this design) or 1 to 3 per level?
3. **Who checks the Chinese text**, and are the Noto CJK fonts acceptable (or WenQuanYi)?
4. **Hold mode name** "Hold Canal Street" and a best score per level. Accepted?
5. **The roof** is player and Buzzard space only (Goons shoot up from below), as the Block's shed deck. Is that
   acceptable, or should Level 2 wait for multi-layer nav, which Level 3 may need anyway?
6. **A campaign run:** does health or ammo carry over from the Block, or does each level start fresh with its own
   debrief? This level assumes a fresh start, with the set-up handed over.
7. **The bridge silhouette** to the east is a real structure shown far away and unnamed. Is it allowed under
   ART_BIBLE 5.7, or should it be generic towers only?

---------------------------------------------------------------------------------------------------

## Appendix A. Seed rectangle table (footprints, web metres)

The prototype rasterised these footprints to get the numbers in this file. Heights are in the text above.
`x0..x1, z0..z1`.

```
north row          -44..44, -36..-33.0, with alcoves 2.4 x 1.0 at x -35, -22, -8, 5, 20, 31 (back at z -34)
W1                 -44..-30, -14..32
market walls       north z -14..-13.6 with openings x -22..-18, -15..-11, -8..-4
                   west x -26..-25.6 with a 1.4 m side door at z -2.9..-1.5
                   south z 5.6..6 with the rear roll-up x -7..-3; east party wall x -0.4..0.4 (no door)
B0                 -26..-16, 6..10
cold room          walls x -25.6..-18.4, z 1.5..5.6 (0.25 m), door x -21..-19 in the north wall
stall rows         R1 -21.6..-19.8, R2 -16.4..-14.6, R3 -11.2..-9.4, R4 -6.0..-4.2; z -11..-5 and -3..-0.5
fish counters      -1.4..-0.4, -10..-1
pallets            -15..-13.4, -12.6..-11, -10.2..-9.4; z 2.4..5.2
yard stair         -14.6..-8.6, 6.0..8.2 (flights and landings: 4.4; the prototype blocked -16..-9.8)
yard dumpster      -1.9..-0.4, 6.3..8.1;   gas cage -9.0..-7.2, 8.8..9.8
bakery shell       0..8, -14..10; Canal door x 2..4; partition z -3.2..-3 with a door x 3..5
                   Mott door z 2..4; alley door x 4..6; counter 0.4..5, -8..-7; table 3.6..5, 4.6..8.4
alley A props      dumpster -29.9..-28.3, -9..-7.2; crates -27.6..-26, 4..5.4
alley B props      dumpster -24..-22.2, 12.2..14; pallets -12..-10.2, 10..11.4; dumpster 2..3.8, 12.2..14
south row          -30..8, 14..32 (S1 -30..-14, S2 -14..0, S3 0..8)
Mott parked        sedan 10.1..12.1, -8..-3.5; van 10.1..12.2, 3..8.5; taxi 10.1..12.1, 18..22.5
Mott box truck     9.6..17.6, 27.2..29.8
E1a                18..29.4, -14..2
E1b                33.6..44, -14..2 minus the workshop 34.0..37.6, -10..-4 (door z -8..-6 off the arcade)
arcade pillar      31.0..31.6, -9.5..-8.9;  torch racks at (37.0, -8.4) and (33.0, -12.0)
pavilion columns   0.4 m square at (28.2, 7.2), (33.8, 7.2), (28.2, 12.8), (33.8, 12.8)
planters           20..23 and 39..42 at z 4..5 and 15..16;  benches 23..23.8 and 38..38.8, z 9..11
E2 front wall      z 18..18.4, door x 31..35;  west wall x 18..18.4 with the roll-up at z 24..27
E2 partition       x 26..26.3 with a door at z 26..28
banquet kitchen    walls z 27..27.2 (door x 38..40) and x 36.2..36.4, z 27..31.6
banquet tables     1.7 m at (29.5, 21.5) (33.5, 21.5) (29.5, 25) (33.5, 25) (37.5, 21.5) (29.5, 28.8) (33.5, 28.8)
stage              40.8..43.6, 18.8..26.6
dub room           racks 18.4..19.4, 28..31.4; cutting table 22.2..23.8, 20.4..22.4
Canal tables       1.8 m at x -38, -34, ..., -6 and 2, 6; z -18.8..-17.8
Canal cars         north lane: -36..-31.5, -20..-15.5, -4..0.5, 34..38.5 (z -29.8..-27.9)
                   south lane: -38..-33.5, 20..25.5 (z -21.2..-19.1)
Canal trucks       box -14..-6, -21.4..-18.9; box 20..28, -27.6..-25.0; IPX 33.5..41.5, -24.3..-21.7
edges              barriers -43.6..-42.8 and 42.6..43.4, z -30..-19
```
