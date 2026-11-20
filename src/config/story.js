// The story: four levels on one block, a cutscene before each and one after the last.
//
// A level is a stretch of the block with one thing to do in it: take a reel back and clear out whoever
// comes for it, or (the last one) get all three to the truck. The words are in src/config/text.js
// `story`; how many Vultures a level holds per difficulty is in src/config/flow.js `difficulty.levels`;
// the timings of the flow between levels in `flow.story`.
//
// Points are [x, z] on the level's own floor, air points [x, y, z]. Every ground point is moved to the
// nearest walkable cell when a level is set up (test/story.test.js keeps them within a step of one).

import { CINEMATIC as C, EXTRACTION, REELS, START } from '../level/data.js';

/** A camera composition part-way along the straight leg between two of the title's (all collision-checked). */
const mix = (a, b, k) => a.map((v, i) => v + (b[i] - v) * k);

/**
 * id        the key of its words in text.story.levels
 * goal      'reel' (take `reel` back, then clear the block) | 'truck' (reach the extraction)
 * start     where Rule stands when it begins (he faces along the guide line)
 * time      'night': from here on the block is dark, unless the player already chose night
 * posts     where its Vultures stand before they know: the first N of each list are used
 *           (N per difficulty: flow.difficulty[name].levels[i].patrol). None of them can see the
 *           level's start: Rule gets his bearings before anyone comes at him.
 * crates    ammo crates
 * scene     the cutscene that opens it (`scenes`)
 */
export const levels = [
  {
    id: 'avenue',
    goal: 'reel',
    reel: 'reel1',
    start: { x: START.x, z: START.z },
    posts: {
      goon: [[2.3, -1.7], [-13.2, 1.2], [-6.7, 5.8], [0.2, 4.3], [-3.6, -1.9], [-7.6, -3.6]],
      buzzard: [[-13, 8.8, -8.8], [-3, 9.3, -17]],
    },
    crates: [[-28.5, 6.5], [-16.8, -3.8], [-9, 6], [-1.3, 4.3]],
    scene: 'opening',
  },
  {
    id: 'shop',
    goal: 'reel',
    reel: 'reel2',
    start: { x: -6.9, z: 5.2 }, // where reel 1 stood: the shop is across the avenue
    posts: {
      goon: [[-13.8, -14], [-6, -19.3], [-13.4, -22.2], [-9.9, -26.6], [-16.2, -17.3], [-5, -21]],
      buzzard: [[-3, 9.3, -17], [-17, 9.6, -21]],
    },
    crates: [[-15.5, -8], [-16.2, -17.3], [1.1, -19.6], [-9.9, -26.6]],
    scene: 'shop',
  },
  {
    id: 'cage',
    goal: 'reel',
    reel: 'reel3',
    start: { x: 8.3, z: -15.5 }, // the alley, outside the shop's side door
    time: 'night',
    posts: {
      goon: [[34.1, -18.1], [31.6, -24.6], [36, -27.4], [30.4, -21.7], [38.8, -22.3], [32, -10.3], [41, -30]],
      buzzard: [[30, 9.2, -27], [40, 9.6, -18]],
    },
    crates: [[10.8, -8.3], [16.3, 1.2], [26.5, 2.6], [32, -10.3], [29.6, -30]],
    scene: 'cage',
  },
  {
    id: 'truck',
    goal: 'truck',
    start: { x: 34.1, z: -18.1 }, // the cage, reel 3 in hand
    time: 'night',
    posts: {
      goon: [[39.8, 23.6], [41.6, 24.9], [39.9, 18.4], [43.8, 23.6], [20.6, 28.3]],
      buzzard: [[31, 10, 20], [43, 9.2, 26.5]],
    },
    crates: [[32, -10.3], [36.8, 3.3], [33.2, 18.4]],
    scene: 'truck',
  },
];

/**
 * Cutscenes. `shots` play in order, each a straight move from one composition to another
 * ([x, y, z, lookX, lookY, lookZ]) over `secs`, the view turning evenly from the one's direction to the
 * other's, with a field of view (`fov`, optionally easing to `fovTo`); a cut between two shots is hard.
 * `cues` fire once as the scene clock passes `at`:
 *   say    index of a line in text.story.scenes[name] (speaker + words, shown as a subtitle)
 *   place  the location line (text.location.place, which follows the time of day)
 *   card   the title card: the level's ("LEVEL 2 OF 4 / THE CHOP SHOP / …"), or `end` for the closing one
 *   train  an El train is sent over the block, heading +1 east or −1 west
 */
export const scenes = {
  // The block, the first reel sitting on the avenue.
  opening: {
    shots: [
      { from: C[0], to: mix(C[0], C[1], 0.55), secs: 7, fov: 46 },
      { from: mix(C[2], C[3], 0.1), to: mix(C[2], C[3], 0.85), secs: 6, fov: 44 },
      { from: mix(C[3], C[4], 0.25), to: C[4], secs: 6.5, fov: 42, fovTo: 37 },
    ],
    cues: [
      { at: 0, train: 1 },
      { at: 0.4, place: true },
      { at: 1.6, say: 0 },
      { at: 7.3, say: 1 },
      { at: 13.4, say: 2 },
      { at: 15.2, card: 'level' },
    ],
  },
  // From the reel to the roll door, through it, across the shop floor.
  shop: {
    shots: [
      { from: mix(C[4], C[5], 0.25), to: mix(C[4], C[5], 0.95), secs: 5, fov: 46 },
      { from: mix(C[5], C[6], 0.15), to: mix(C[5], C[6], 0.9), secs: 5, fov: 44 },
      { from: mix(C[6], C[7], 0.3), to: mix(C[6], C[7], 0.95), secs: 4.8, fov: 42 },
    ],
    cues: [
      { at: 0.5, say: 0 },
      { at: 5.3, say: 1 },
      { at: 9.7, say: 2 },
      { at: 11, card: 'level' },
    ],
  },
  // Out of the alley, east under the El, a look through the cage gate.
  cage: {
    shots: [
      { from: C[8], to: mix(C[8], C[9], 0.75), secs: 5.2, fov: 48 },
      { from: mix(C[9], C[10], 0.2), to: mix(C[9], C[10], 0.95), secs: 5.4, fov: 46 },
      { from: C[10], to: C[10], secs: 5.2, fov: 50, fovTo: 39 },
    ],
    cues: [
      { at: 0.3, place: true },
      { at: 0.9, say: 0 },
      { at: 5.5, say: 1 },
      { at: 10.4, say: 2 },
      { at: 12, card: 'level' },
    ],
  },
  // From the cage round to the lot, down to the truck.
  truck: {
    shots: [
      { from: C[10], to: mix(C[10], C[11], 0.85), secs: 4.5, fov: 48 },
      { from: mix(C[11], C[12], 0.15), to: C[12], secs: 4.5, fov: 46 },
      { from: mix(C[12], C[13], 0.35), to: C[13], secs: 4.8, fov: 42 },
    ],
    cues: [
      { at: 0.4, say: 0 },
      { at: 4.8, say: 1 },
      { at: 9.2, say: 2 },
      { at: 10.4, card: 'level' },
    ],
  },
  // The truck's doors, then the whole avenue from under the El as a train goes over.
  ending: {
    shots: [
      { from: C[13], to: mix(C[13], C[12], 0.7), secs: 5.6, fov: 42, fovTo: 48 },
      { from: mix(C[1], C[0], 0.15), to: C[0], secs: 7.4, fov: 44, fovTo: 50 },
    ],
    cues: [
      { at: 0.6, say: 0 },
      { at: 4.2, train: -1 },
      { at: 6.2, say: 1 },
      { at: 8, card: 'end' },
    ],
  },
};

/** The scene after the last level. */
export const endScene = 'ending';

/** Hold the Block: where its ammo crates stand (refilled after every wave). */
export const holdoutCrates = [[-28.5, 6.5], [-9, 6], [16.3, 1.2], [-16.8, -3.8], [26.5, 2.6]];

/** Where each objective is, for anything that needs it without a level (tests, tools). */
export const places = { reels: REELS, truck: EXTRACTION };
