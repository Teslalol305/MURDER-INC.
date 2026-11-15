// The block as numbers: every footprint, height and opening the level is built from (docs/DESIGN.md
// section 4). Pure data and pure functions: the builders, the level's own queries (zoneAt, floorAt,
// groundSurfaceAt) and the unit tests all read the same table.
//
//  z -34 ┌───────────────┬─┬────────────────────────────┬─────┬─────────┬─┬──────────────────┐
//        │ tenement N1   │g│  V&R AUTO BODY (interior)  │alley│ deli N2 │c│ THE CAGE         │
//        │               │a│  mezzanine NW · reel 2     │     │         │u│ reel 3           │
//    -11 ├───────────────┴n┴──[roll door]──[bay]────────┴─────┴─────────┴t┴────[gate]───────┤
//     -7 │═════ north sidewalk (+0.15) ═════ dropped kerbs at the doors and the alley ═══════│
//        │ station · START →   JAMAICA AVE under the El · reel 1                   roadblock │
//      7 │═════ south sidewalk (+0.15) ══ [gateway] ═ [ scaffold shed + stair ] ═ [lot entry] ═│
//     11 ├───────────────┬────────────┬────────────┬──────────────────────────┬─────────────┤
//        │ station house │ pawn +     │ vacant lot │ S3: chicken, liquor,     │ PARKING LOT  │
//        │ S1            │ records S2 │ mural wall │ nails                    │ booth,       │
//     26 │               │            │            ├──────────────────────────┤ billboard    │
//        │               │            │   rear service lane  → → → → → → → →  │ IPX TRUCK    │
//     31 │               │            ├────────────┴── garages ───────────────┤              │
//     34 └───────────────┴────────────┴───────────────────────────────────────┴─────────────┘
//      x -46           -30          -16           -4                          22            46

export const BOUNDS = { minX: -46, maxX: 46, minZ: -34, maxZ: 34 };

export const KERB = 0.15; // sidewalk height above the roadway
export const ROAD_Z = 7; // |z| of the kerb line
export const FRONT_Z = 11; // |z| of the building line
export const GROUND_FLOOR = 3.8; // storefront storey
export const FLOOR = 3.1; // every storey above it

/** The elevated line over the avenue. `y` is the underside of the track deck. */
export const EL = {
  y: 6.5,
  rowZ: 4.6, // |z| of the two column rows
  half: 5.4, // half width of the deck (walkways included)
  spacing: 10,
  bents: [-45, -35, -25, -15, -5, 5, 15, 25, 35, 45], // x of every column pair inside the block
  far: [-85, -75, -65, -55, 55, 65, 75, 85], // the line carries on past both closures (decor)
  columnTop: 5.3,
  tracks: [-2.1, 2.1], // z of the two track centre lines
  gauge: 1.435,
  tieTop: 6.68,
  railTop: 6.83,
};

/** The sealed El station at the west end: a mezzanine under the tracks, one stair to each sidewalk. */
export const STATION = {
  mezz: { x0: -46, x1: -39.4, z0: -4.1, z1: 4.1, y0: 3.9, y1: 6.3 },
  bridgeX: [-45.9, -44.2], // the covered walk from the mezzanine out to each stair head
  stair: { top: -44.2, foot: -38.8, zIn: 7.25, zOut: 9.05, risers: 20 }, // mirrored on the north side
};

export const SHOP = {
  minX: -24,
  maxX: 6,
  minZ: -31,
  maxZ: -11,
  wall: 0.4,
  eave: 6, // underside of the roof
  roof: 0.3,
  parapet: 6.9,
  roll: { x0: -15, x1: -9, h: 4.3 }, // the 6 m roll-up door, south wall
  bay: { x0: -3.2, x1: 0.6, h: 3.5 }, // the second, smaller bay
  side: { z0: -23.1, z1: -21.1, h: 2.5 }, // east door into the alley
  // Mezzanine in the north-west corner: a deck, an office on its back half, a stair down its front.
  mezz: { x0: -23.6, x1: -15.4, z0: -30.6, z1: -25, y: 2.8, officeZ: -27.1, officeX: -17.4, doorX: [-19, -17.4] },
  stair: { x0: -15.4, x1: -12.04, z0: -26.3, z1: -25, risers: 12 }, // 12 × 0.233 m, descending east
  skylights: [
    [-18.5, -19.5],
    [-9, -24.5],
    [-9, -15.5],
    [0.5, -20.5],
  ],
  workLights: [
    [-18.2, -17.2],
    [-9.2, -22.4],
    [-9.2, -14.6],
    [0.6, -21.2],
  ],
};

export const ALLEY = { minX: 6, maxX: 11, minZ: -34, maxZ: -11, gateZ: -31.4 };
export const CUT = { minX: 22, maxX: 25, minZ: -34, maxZ: -11 }; // the passage between the deli and the cage

export const CAGE = {
  minX: 25,
  maxX: 45.4,
  minZ: -33,
  maxZ: -12.2,
  height: 4,
  plinth: 0.5, // concrete knee wall under the mesh: stops walkers, lets bullets through above it
  southGate: [33, 36], // x range, in the south fence
  westGate: [-29.4, -26.4], // z range, in the west fence
  court: { x0: 26.6, x1: 43.9, z0: -29.9, z1: -15.1 },
};

export const VACANT = { minX: -16, maxX: -4, minZ: 11, maxZ: 26, gate: [-11.9, -8.7] };
export const LANE = { minX: -16, maxX: 22, minZ: 26, maxZ: 31 };
export const LOT = {
  minX: 22,
  maxX: 46,
  minZ: 11,
  maxZ: 34,
  entry: [28.6, 35], // dropped kerb and gap in the low wall
};

/** The construction sidewalk shed in front of S3: the vantage. */
export const SHED = {
  x0: 1,
  x1: 19,
  z0: 7.45,
  z1: 10.95,
  deck: KERB + 2.8,
  parapet: 1.1,
  stair: { x0: -2.6, x1: 1, z0: 8.95, z1: 10.95, risers: 12 }, // rises eastward onto the deck
};

/**
 * Solid buildings inside the bounds. `boxes` are their colliders (x0, x1, z0, z1); `floors` counts the
 * storefront storey. Pockets (the gangway beside the tenement, the pawn shop's vestibule) are simply
 * left out of the boxes.
 */
export const BUILDINGS = {
  n1: { name: 'tenement', base: 'brick_red', floors: 5, x0: -46, x1: -24, z0: -34, z1: -11, boxes: [[-46, -26.2, -34, -11], [-26.2, -24, -34, -16]] },
  n2: { name: 'deli', base: 'brick_tan', floors: 3, x0: 11, x1: 22, z0: -34, z1: -11, boxes: [[11, 22, -34, -11]] },
  s1: { name: 'station house', base: 'brick_brown', floors: 3, x0: -46, x1: -30, z0: 11, z1: 34, boxes: [[-46, -30, 11, 34]] },
  s2: { name: 'pawn', base: 'brick_red', floors: 4, x0: -30, x1: -16, z0: 11, z1: 34, boxes: [[-30, -24, 11, 34], [-24, -21.8, 13.4, 34], [-21.8, -16, 11, 34]] },
  s3: { name: 'S3', base: 'brick_tan', floors: 2, x0: -4, x1: 22, z0: 11, z1: 26, boxes: [[-4, 22, 11, 26]] },
  garages: { name: 'garages', base: 'brick_painted', floors: 1, x0: -16, x1: 22, z0: 31, z1: 34, boxes: [[-16, 22, 31, 34]] },
};

export const buildingHeight = (b) => GROUND_FLOOR + (b.floors - 1) * FLOOR;

/** Raised sidewalk slabs (top at KERB). Everything else is at road level. */
export const SIDEWALKS = [
  // north side, broken by the two shop driveways and the alley mouth
  { x0: -46, x1: -16.2, z0: -11, z1: -7 },
  { x0: -7.8, x1: -3.6, z0: -11, z1: -7 },
  { x0: 1, x1: 6, z0: -11, z1: -7 },
  { x0: 11, x1: 25, z0: -11, z1: -7 },
  { x0: 25, x1: 46, z0: -12.2, z1: -7 }, // runs back to the cage fence
  // south side, broken by the vacant lot's gateway and the lot entrance
  { x0: -46, x1: -12.6, z0: 7, z1: 11 },
  { x0: -8, x1: 28.6, z0: 7, z1: 11 },
  { x0: 35, x1: 46, z0: 7, z1: 11 },
];

/** Other floors at sidewalk height: the pawn shop's vestibule. */
export const PADS = [{ x0: -24, x1: -21.8, z0: 11, z1: 13.4 }];

/** Dropped kerbs: [x0, x1, side] with side −1 north, +1 south. */
export const DRIVEWAYS = [
  [-16.2, -7.8, -1],
  [-3.6, 1, -1],
  [6, 11, -1],
  [-12.6, -8, 1],
  [28.6, 35, 1],
];

export const ZONES = [
  { id: 'west', name: 'WEST END', minX: -46, maxX: -30, minZ: -34, maxZ: 34 },
  { id: 'shop', name: 'CHOP SHOP', minX: -30, maxX: 22, minZ: -34, maxZ: -11 },
  { id: 'avenue', name: 'THE AVENUE', minX: -30, maxX: 22, minZ: -11, maxZ: 34 },
  { id: 'lot', name: 'THE LOT', minX: 22, maxX: 46, minZ: -34, maxZ: 34 },
];

/** The east zone is two places: the cage north of the avenue's centre line, the parking lot south of it. */
export const CAGE_NAME = 'THE CAGE';

/** Zone id under a point; points outside every rectangle belong to the nearest one. */
export function zoneAt(x, z) {
  let best = 'avenue';
  let bestD = Infinity;
  for (const zone of ZONES) {
    const dx = Math.max(zone.minX - x, 0, x - zone.maxX);
    const dz = Math.max(zone.minZ - z, 0, z - zone.maxZ);
    const d = dx * dx + dz * dz;
    if (d < bestD) {
      bestD = d;
      best = zone.id;
    }
  }
  return best;
}

const inside = (r, x, z) => x >= r.x0 && x <= r.x1 && z >= r.z0 && z <= r.z1;

/** Height of the walking surface the level itself provides at (x, z): a sidewalk slab or the road. */
export function floorAt(x, z) {
  for (const slab of SIDEWALKS) if (inside(slab, x, z)) return KERB;
  for (const pad of PADS) if (inside(pad, x, z)) return KERB;
  return 0;
}

const inRect = (r, x, z) => x > r.minX && x < r.maxX && z > r.minZ && z < r.maxZ;

/** Surface of the bare ground plane (boxes standing on it report their own). */
export function groundSurfaceAt(x, z) {
  if (inRect(SHOP, x, z)) return 'concrete';
  if (inRect(CAGE, x, z)) return 'concrete';
  if (inRect(VACANT, x, z)) return 'dirt';
  const az = Math.abs(z);
  if (az >= ROAD_Z && az <= FRONT_Z) return 'concrete'; // driveway aprons between the slabs
  return 'asphalt';
}
