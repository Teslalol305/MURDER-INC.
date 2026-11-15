// Authored gameplay data of the block: where the reels and the truck are, where enemies appear, where
// the AI likes to stand, what blows up, and the title fly-through. Positions are [x, z] on the level's
// own floor (road or sidewalk) unless a height is given.

import { SHED, SHOP } from './layout.js';

export const START = { x: -37.4, z: 8.15, yaw: -Math.PI / 2 + 0.15 }; // foot of the station stair, facing east, a little toward the avenue

/** Reel positions, in route-bullet order: the avenue, the chop shop, the cage. */
export const REELS = [
  { zone: 'avenue', x: -4, z: 1, yaw: 0.35 },
  { zone: 'shop', x: -9.5, z: -21.5, yaw: -0.5 },
  { zone: 'lot', x: 35.25, z: -22.5, yaw: 1.1 },
];

/** The truck stands nose east in the lot's south-east corner; the zone is behind its rear doors. */
export const TRUCK = { x: 41.3, z: 29.7, yaw: 0 };
export const EXTRACTION = { x: 35.9, z: 29.7 };

/**
 * Ground spawn points: out of the main sightlines (pockets, corners, behind vehicles). None in the
 * west zone, so the start stays quiet.
 */
export const GROUND_SPAWNS = [
  // shop zone
  [-25.1, -14.2], // the gangway beside the tenement
  [-21.4, -28.2], // under the mezzanine
  [-22.4, -15.2], // behind the west lift
  [3.6, -26.6], // behind the racks in the north-east corner
  [1.7, -23.8], // behind the car on the east lift
  [8.4, -29.6], // the alley's dead end
  [8.3, -21.8], // the alley, at the side door
  // avenue zone
  [-22.9, 12.3], // the pawn shop's vestibule
  [-21.5, -9.6], // behind the white van, beside the tyre cage
  [-5.7, -9.9], // behind the food cart
  [16.5, -9.9], // between the produce stand and the dig
  [-14.4, 12.7], // vacant lot, behind the hoarding
  [-12.8, 23.6], // vacant lot, behind the burned car
  [-5.2, 21.2], // vacant lot, at S3's side door
  [-12.4, 29.3], // rear lane, behind the van
  [0.4, 28.4], // rear lane, behind the dumpster
  [4.8, 28.6], // rear lane, at the dock steps
  [14.6, 27.4], // rear lane, past the dock
  [20.4, 29.6], // rear lane, at the lot corner
  // lot zone
  [23.5, -31.2], // the far end of the cut
  [26.4, -31.6], // cage, behind the bleachers (west)
  [44.2, -31.6], // cage, behind the bleachers (east)
  [43.6, -9.6], // north sidewalk, at the roadblock
  [43.4, 9.4], // south sidewalk, at the roadblock
  [24.2, 25.5], // lot, behind the pickup
  [36.5, 21], // lot, the empty bay between the van and the sedan
  [27.1, 32.4], // lot, between the cars on the south wall
  [44.5, 16.6], // lot, under the billboard
  [45, 26.4], // lot, between the dumpster and the truck
];

/** Air spawn points [x, y, z]: over rooftops, beside the El deck, over the court and the lot. */
export const AIR_SPAWNS = [
  [-17, 9.6, -21], // shop roof, west
  [-3, 9.3, -17], // shop roof, east
  [8.5, 9.6, -24], // over the alley
  [16.5, 13.6, -21], // deli roof
  [-13, 8.8, -8.8], // beside the El, north
  [10, 9.4, 8.9], // beside the El, south, over the shed
  [-10, 9.6, 20], // over the vacant lot
  [8, 10.8, 18.5], // S3 roof
  [-23, 16.2, 22], // pawn shop roof
  [4, 8.6, 28.5], // over the rear lane
  [30, 9.2, -27], // over the court, north-west
  [40, 9.6, -18], // over the court, south-east
  [35, 9, -8.9], // beside the El at the cage
  [31, 10, 20], // over the lot, west
  [41.5, 12.6, 16], // behind the billboard
  [43, 9.2, 26.5], // over the truck
  [40.5, 9.4, 9], // beside the El at the lot
];

/**
 * Cover points for the AI: standing spots beside something solid. [x, z] on the ground, or
 * [x, z, y] for the two decks. Nudged to walkable cells when the level is finished.
 */
export const COVER_POINTS = [
  // avenue, west of the reel
  [-37.2, -3.8], [-33.1, -0.5], [-31.2, 2.2], [-27.6, 2.2], [-24.1, -2.4], [-19.2, 0.5], [-14.4, -0.7], [-24.6, 8.2], [-19.5, 7.9],
  [-26.3, -8.2], [-21.6, -7.8],
  // the reel 1 arena
  [-13.2, 1.2], [-8.4, -1.4], [-7.6, -3.6], [-4.3, -4], [-3.6, -1.9], [0.9, -1.6], [0.2, 4.3], [-6.9, 5.2], [-3, 8.3],
  // the second curtain
  [6.8, -0.8], [2.2, 2.2], [11.7, 1.4], [16.3, 1.2], [10.6, -3.5], [11.4, -1], [19.9, -2.4], [19.3, 2], [21.5, 2],
  [15.2, 3.7], [4, -8.3], [16.5, -9.6], [22.2, -8.6], [20, 6.2],
  // crossing to roadblock
  [26.5, 2.6], [28.7, 2.6], [29.6, -3], [27.2, -3.1], [33.3, 0.5], [36.9, -0.8], [34.4, -2.6], [36.4, 3.2], [38, 1.4],
  // shop front and interior
  [-17.9, -9.1], [-8.4, -9.9], [3.4, -9.4],
  [-13.8, -14], [-10.5, -14.6], [-6, -19.3], [-5, -21], [-13.4, -22.2], [-9.9, -26.6], [1.1, -19.6], [-16.2, -17.3],
  [-22, -17.3], [3.4, -13.9], [-8, -13.2], [-19.5, -26, SHOP.mezz.y],
  // alley and cut
  [9, -14.4], [7.9, -27.1], [9.3, -24.6], [24, -18],
  // the cage
  [34.1, -18.1], [33.6, -22], [31.6, -24.6], [36, -27.4], [39, -21.6], [30.4, -21.7], [29.6, -30], [41, -30],
  [28.6, -14], [32, -10.3], [37, -10.3],
  // vacant lot
  [-13.5, 17], [-9.2, 20.5], [-7.2, 15.8], [-6.1, 20.3],
  // rear lane
  [-10.6, 27.8], [-0.7, 27.7], [4.5, 29.2], [13.2, 27.9], [16.4, 28.9], [20.6, 28.3],
  // the lot
  [28.3, 15.5], [28.4, 18.1], [28.7, 23.3], [33.2, 15.8], [33.3, 18.4], [39.9, 18.4], [39.8, 23.6],
  [32.2, 26.3], [30.5, 28.6], [32.4, 28.7], [34.6, 31.8], [39.6, 27.5], [41.6, 24.9], [41.7, 27], [43.8, 23.6],
  // the shed deck
  [5.4, 8.9, SHED.deck], [12.8, 8.9, SHED.deck],
];

/**
 * Explosives: part of the cover, solid until they blow. [type, x, z, yaw] or [type, x, z, yaw, y].
 * None within 7 m of the start or 2.2 m of a reel (checked by test/level-layout.test.js).
 */
export const EXPLOSIVES = [
  ['propane', -4.2, -7.85, 0], // two at the food cart
  ['propane', -4.2, -8.7, 0],
  ['rack', -22.6, -10.62, 0], // outside the shop, beside the tyre cage
  ['rack', -20.4, -13.6, Math.PI / 2], // the welding corner inside
  ['rack', 3.4, -17.6, Math.PI / 2], // by the east lift
  ['rack', -14.3, -23.4, 0.3], // at the foot of the mezzanine stair
  ['propane', -3.4, -30.1, 0], // the north bench
  ['rack', 6.55, -19.6, Math.PI / 2], // the alley, beside the shop's side door
  ['propane', 0.35, 7.8, 0], // the foot of the shed
  ['propane', 9.3, 10.35, 0, SHED.deck], // on the shed deck
  ['propane', 17.6, 10.45, 0], // the east end of the shed
  ['propane', 25.9, 12.9, 0], // the lot booth, both sides
  ['propane', 28.8, 13.7, 0],
  ['propane', -12.9, 16.3, 0], // the vacant lot, by the burned car
  ['rack', 5.9, 30.55, 0], // the rear lane, between two garage doors
  ['propane', 18.3, 26.5, 0], // the rear lane, east end
  ['propane', 43.3, -30.5, 0], // the cage, by the bleachers
  ['rack', 32.6, 33.55, 0], // the lot's south wall, short of the truck
  ['propane', 39.6, 20.9, 0], // the lot's east aisle
  ['propane', 39.8, -6.4, 0], // the roadblock
  ['propane', 8.9, -1.5, 0], // the avenue, at the barrier chicane
];

/**
 * Title fly-through, fourteen held compositions: the block from under the El at the station (the opening
 * establishing shot, high between the column rows), a slow push east past the repair scaffold, down the
 * avenue past the Vultures' van to reel 1, into the shop by the roll door, across its floor, out the side
 * door (held on its step: the curve itself threads the doorway) and up the alley, east down the middle of
 * the avenue under the El (well clear of the deli awning and the dig on the north sidewalk), a look
 * between the columns through the cage gate at reel 3, a turn under the El to the lot, and the truck.
 * [x, y, z, lookX, lookY, lookZ]. The straight legs between them and the curve the title camera
 * actually flies through them clear every collider (test/level-layout.test.js walks both).
 */
export const CINEMATIC = [
  [-38.6, 4.4, -1.6, -5, 2, -0.5],
  [-31.5, 4.2, -2.5, -12, 1.8, 0.5],
  [-21, 3.3, 2.6, -9, 1.4, 1.5],
  [-13.4, 2.4, -0.4, -3, 1, -1.5],
  [-6.6, 2.2, -4, -4, 0.8, 1],
  [-12.4, 2.3, -5.6, -11.6, 2, -14],
  [-10.2, 2.1, -13.4, -9.5, 0.9, -21.5],
  [-14.2, 4.2, -22.6, -4, 1.2, -19],
  [6.4, 2, -22.1, 8.8, 2.4, -10],
  [12, 3.6, -1.4, 24, 2, 1],
  [31.5, 3.8, -3, 35.25, 1, -22.5],
  [30.5, 4.6, -1, 40, 2.4, 22],
  [32.2, 3.4, 14.6, 40.5, 1.6, 28.5],
  [34.6, 1.8, 27.8, 42, 1.7, 30.2],
];
