// The ROCKET: a reloadable shoulder launcher. A phosphated steel tube with a reinforcing ring at the
// mouth and a flared blast cone at the back, a varnished wooden heat shield in two halves clamped
// round its middle, a trigger grip and a plain second grip under it, a folding post and a ladder leaf
// standing off its upper left, two sling swivels. The round goes in from the front: its booster hides
// in the tube and the olive warhead stands out of the muzzle on a thin neck.
//
// Gun space: origin on the bore axis over the back of the trigger grip, −Z down the tube, +Y up,
// +X right. Profiles are [s, y] (or [s, radius]) with s = distance forward of the origin.

import * as THREE from 'three';
import { makePose } from './arms.js';
import { FINISH, Soup, block, fillet, lathe, loft, paint, pin, prism, rod, sweep } from './build.js';
import { FINISH_BLUED } from './material.js';
import { POSES, gunPose, handKey, sampleTrack, shiftKey, turnKey } from './handling.js';

const MUZZLE_S = 0.41; // mouth of the tube
const BREECH_S = -0.54; // lip of the blast cone
const BORE = 0.0205; // radii: inside the tube…
const TUBE = 0.0238; // …the forward tube…
const CHAMBER = 0.029; // …the swell under the heat shield…
const THROAT = 0.0245; // …the narrowest point behind it…
const CONE = 0.049; // …and the mouth of the blast cone
const SHIELD = 0.038; // heat shield
const SIGHT_X = -0.04; // the sights stand off to the left of the tube…
const SIGHT_Y = 0.1; // …this high over the bore
const REAR_S = 0.085; // ladder leaf
const FRONT_S = 0.335; // post
const HOUSE_Y = -0.052; // underside of the trigger housing
const TAIL = 0.2; // how far the round reaches into the tube
const N = 20; // sides of the tube and of everything turned on it

const ACROSS = new THREE.Matrix4().makeRotationY(Math.PI / 2);

/** A flat part standing across the bore: the outline [[x, y], …] made `thick` deep at s. */
function plate(pts, s, thick, { bevel = 0, holes = null } = {}) {
  const turn = (list) => list.map(([x, y]) => [-x, y]);
  return prism(turn(pts), thick, { bevel, x: s, holes: holes && holes.map(turn) }).applyMatrix4(ACROSS);
}

/** A rectangle as an outline, for cutting windows. */
const box = (x0, x1, y0, y1) => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];

/** A band round the tube from s0 to s1, standing `lift` proud of radius r, its edges broken. */
const band = (s0, s1, r, lift) =>
  lathe([[s0 - 0.001, r - 0.0004], [s0, r + lift], [s1, r + lift], [s1 + 0.001, r - 0.0004]], N, { caps: [false, false] });

export function buildRocket(material, def) {
  // Phosphated steel: a flat grey-green that takes the light softly; edges rub through to bright metal.
  const wear = paint(0x9aa0a8, 0.3, 1);
  const P = {
    steel: paint(0x666a63, 0.56, 0.7, { wear, finish: FINISH_BLUED }),
    dark: paint(0x393b3d, 0.5, 0.85, { wear }),
    bare: paint(0xb1b6bd, 0.28, 1, { finish: FINISH.brushed }),
    wood: paint(0x6e4021, 0.34, 0, { finish: FINISH.wood }), // varnished: a warm brown with a soft gloss
    black: paint(0x050506, 0.92, 0),
    soot: paint(0x121213, 0.85, 0.2),
    olive: paint(0x556030, 0.56, 0.1), // the warhead's drab paint
    motor: paint(0x3d4136, 0.5, 0.6),
    yellow: paint(0xd0a81e, 0.5, 0),
    tan: paint(0x8b7549, 0.72, 0), // waxed paper round the booster charge
    dot: paint(0xf2f0e4, 0.6, 0, { glow: 0.55 }),
  };

  // ---------------------------------------------------------------------------------------------
  // Body: everything that never moves relative to the tube
  // ---------------------------------------------------------------------------------------------
  const body = new Soup();

  // The tube, mouth to breech: reinforcing ring, forward tube, the chamber's swell (mostly under the
  // heat shield), the throat, the blast cone and its rolled lip.
  body.add(
    lathe(
      [
        [MUZZLE_S + 0.0005, BORE + 0.0012],
        [MUZZLE_S, TUBE + 0.003],
        [MUZZLE_S - 0.004, TUBE + 0.0045],
        [MUZZLE_S - 0.02, TUBE + 0.0045],
        [MUZZLE_S - 0.024, TUBE],
        [-0.004, TUBE],
        [-0.024, CHAMBER],
        [-0.345, CHAMBER],
        [-0.392, THROAT],
        [-0.4, THROAT],
        [BREECH_S + 0.008, CONE],
        [BREECH_S + 0.003, CONE + 0.003],
        [BREECH_S, CONE + 0.003],
        [BREECH_S - 0.0005, CONE + 0.0005],
      ],
      N,
      { caps: [false, false] },
    ),
    P.steel,
    { crease: 0.5 },
  );
  // Both lips are rubbed bright.
  body.add(lathe([[MUZZLE_S + 0.0003, TUBE + 0.0016], [MUZZLE_S + 0.0002, TUBE + 0.0031], [MUZZLE_S - 0.004, TUBE + 0.0047]], N, { caps: [false, false] }), wear, { crease: 0.5 });
  body.add(lathe([[BREECH_S + 0.003, CONE + 0.0032], [BREECH_S - 0.0002, CONE + 0.0032], [BREECH_S - 0.0007, CONE + 0.0005]], N, { caps: [false, false] }), wear, { crease: 0.5 });
  // The bore, and the sooted inside of the cone.
  const hollow = { caps: [false, true], inside: true };
  body.add(lathe([[MUZZLE_S + 0.0005, BORE + 0.0012], [MUZZLE_S - 0.005, BORE], [MUZZLE_S - 0.27, BORE]], N, hollow), P.black, { crease: 0.9, ao: 0 });
  body.add(
    lathe([[BREECH_S - 0.0005, CONE + 0.0005], [BREECH_S + 0.006, CONE - 0.0025], [-0.4, THROAT - 0.003], [-0.36, THROAT - 0.003]], N, hollow),
    P.soot,
    { crease: 0.9, ao: 0 },
  );
  // Collar where the cone is screwed on.
  body.add(lathe([[-0.386, THROAT + 0.0004], [-0.388, THROAT + 0.003], [-0.402, THROAT + 0.003], [-0.404, THROAT + 0.0008]], N, { caps: [false, false] }), P.dark, { crease: 0.5 });

  // Heat shield: an upper and a lower half of wood with a seam along each side…
  const half = (s, r, up) => ({ c: [0, up * 0.0009, -s], w: r * 2, h: 0, top: up > 0 ? r : 0.0001, bot: up > 0 ? 0.0001 : r, exp: 2 });
  for (const up of [1, -1]) {
    body.add(loft([half(-0.02, SHIELD - 0.0035, up), half(-0.026, SHIELD, up), half(-0.334, SHIELD, up), half(-0.34, SHIELD - 0.0035, up)], N, [true, true]), P.wood, { crease: 0.7 });
  }
  for (const side of [-1, 1]) body.add(block(-0.336, -0.024, -0.001, 0.001, side * 0.0328 - 0.004, side * 0.0328 + 0.004), P.black);
  // …held by three steel bands, each drawn up by a bolt through its ears.
  const BANDS = [-0.095, -0.18, -0.265];
  for (const s of BANDS) {
    body.add(band(s - 0.006, s + 0.006, SHIELD, 0.0014), P.steel, { crease: 0.5 });
    if (s === BANDS[0]) continue; // the front one carries the second grip instead
    body.add(block(s - 0.005, s + 0.005, -SHIELD - 0.011, -SHIELD + 0.002, -0.004, 0.004, 0.0008), P.steel);
    body.add(pin(s, -SHIELD - 0.0055, 0.0026, -0.007, 0.007, 6), P.dark);
  }

  // Second grip: a plain turned handle in a ferrule under the front band.
  const G2 = BANDS[0];
  body.add(rod([0, -SHIELD + 0.002, -G2], [0, -SHIELD - 0.014, -G2 + 0.0025], 0.013, 0.0145, 10, [false, true]), P.steel, { crease: 0.5 });
  body.add(
    sweep(
      [[G2 - 0.0025, -SHIELD - 0.012], [G2 - 0.005, -SHIELD - 0.03], [G2 - 0.01, -SHIELD - 0.066], [G2 - 0.015, -SHIELD - 0.098], [G2 - 0.016, -SHIELD - 0.105]],
      (t, i) => ({ w: i === 4 ? 0.025 : 0.029 + 0.006 * Math.sin(t * 2.6), d: i === 4 ? 0.025 : 0.029 + 0.006 * Math.sin(t * 2.6), exp: 2 }),
      10,
      [false, true],
    ),
    P.wood,
    { crease: 0.9 },
  );

  // Trigger housing under the tube, with its pins, the cross-bolt safety and the cocked hammer behind.
  const housing = [[-0.014, -0.018], [0.166, -0.018], [0.166, -0.036, 0.004], [0.152, HOUSE_Y, 0.006], [-0.004, HOUSE_Y, 0.004], [-0.014, -0.042, 0.004]];
  body.add(prism(fillet(housing, 2), 0.03, { bevel: 0.0014 }), P.steel);
  for (const [s, y] of [[0.004, -0.033], [0.108, -0.034], [0.152, -0.031]]) body.add(pin(s, y, 0.0024, -0.0158, 0.0158, 6), P.dark);
  body.add(pin(0.074, -0.04, 0.0042, -0.0185, 0.0185, 8), P.dark);
  body.add(prism(fillet([[0.02, -0.027], [0.14, -0.027], [0.14, -0.046, 0.004], [0.02, -0.046, 0.004]], 2), 0.0012, { x: -0.0154, bevel: 0.0005 }), P.steel);
  body.add(prism([[-0.012, -0.027], [-0.024, -0.026], [-0.034, -0.033], [-0.035, -0.04], [-0.029, -0.04], [-0.023, -0.035], [-0.012, -0.038]], 0.008, { bevel: 0.0008 }), P.dark);
  // A reinforcing band ahead of it, and the dovetail for an optical sight on the left of the tube.
  body.add(band(0.173, 0.185, TUBE, 0.0016), P.steel, { crease: 0.5 });
  body.add(prism(fillet([[-0.008, -0.009], [0.058, -0.009], [0.058, 0.009, 0.003], [-0.008, 0.009, 0.003]], 2), 0.005, { x: -TUBE - 0.0012, bevel: 0.001 }), P.dark);
  for (const s of [0.004, 0.046]) body.add(pin(s, 0, 0.0028, -TUBE - 0.0052, -TUBE - 0.002, 6), P.steel);

  // Trigger grip, wood like the shield, and the guard: one bent strip.
  const DY = HOUSE_Y + 0.04;
  body.add(
    sweep(
      [[0.07, -0.034 + DY], [0.063, -0.055 + DY], [0.051, -0.085 + DY], [0.037, -0.115 + DY], [0.027, -0.139 + DY]],
      (t) => ({ w: 0.028 + 0.003 * Math.sin(t * Math.PI), d: 0.041 + 0.006 * t, exp: 2.6 }),
      12,
      [false, true],
    ),
    P.wood,
    { crease: 0.9 },
  );
  body.add(sweep([[0.0275, -0.138 + DY], [0.0262, -0.1415 + DY]], () => ({ w: 0.0292, d: 0.0485, exp: 2.6 }), 12, [false, true]), P.dark, { crease: 0.9 }); // butt cap
  const guard = [
    [0.088, -0.038], [0.091, -0.079], [0.152, -0.079], [0.156, -0.038], // outside, back to front
    [0.153, -0.038], [0.1495, -0.0765], [0.0935, -0.0765], [0.0905, -0.038], // inside, front to back
  ];
  body.add(prism(guard.map(([s, y]) => [s, y + DY]), 0.014, { bevel: 0.0006 }), P.steel);

  // Sight bases: a band round the tube and a bracket standing off its upper left.
  const bracket = [[SIGHT_X - 0.014, 0.025], [-0.016, 0.025], [-0.006, 0.014], [-0.016, -0.008], [SIGHT_X - 0.014, 0.017]];
  for (const [s, len] of [[REAR_S, 0.02], [FRONT_S, 0.014]]) {
    body.add(band(s - len / 2, s + len / 2, TUBE, 0.0018), P.steel, { crease: 0.5 });
    body.add(plate(bracket, s, len - 0.004, { bevel: 0.0008 }), P.steel);
  }

  // Rear sight: a ladder leaf on its hinge. The window at the top is what the shooter looks through.
  const leaf = fillet([[SIGHT_X - 0.013, 0.025], [SIGHT_X + 0.013, 0.025], [SIGHT_X + 0.013, SIGHT_Y + 0.0135, 0.003], [SIGHT_X - 0.013, SIGHT_Y + 0.0135, 0.003]], 2);
  const x0 = SIGHT_X - 0.011;
  const x1 = SIGHT_X + 0.011;
  const aperture = [
    [x0, SIGHT_Y - 0.011],
    [SIGHT_X - 0.0016, SIGHT_Y - 0.011],
    [SIGHT_X - 0.0016, SIGHT_Y - 0.0135],
    [SIGHT_X + 0.0016, SIGHT_Y - 0.0135],
    [SIGHT_X + 0.0016, SIGHT_Y - 0.011],
    [x1, SIGHT_Y - 0.011],
    [x1, SIGHT_Y + 0.011],
    [x0, SIGHT_Y + 0.011],
  ];
  const rungs = [0, 1, 2, 3].map((k) => box(x0, x1, 0.0335 + k * 0.013, 0.0445 + k * 0.013));
  body.add(plate(leaf, REAR_S, 0.0026, { bevel: 0.0005, holes: [aperture, ...rungs] }), P.dark);
  body.add(pin(REAR_S, 0.0275, 0.0032, SIGHT_X - 0.0155, SIGHT_X + 0.0155, 6), P.steel);

  // Front sight: a folding post, its tip painted white on the shooter's side.
  const post = [[-0.007, 0.025], [0.007, 0.025], [0.007, 0.036], [0.0028, 0.058], [0.0024, SIGHT_Y], [-0.0024, SIGHT_Y], [-0.0028, 0.058], [-0.007, 0.036]];
  body.add(plate(post.map(([x, y]) => [SIGHT_X + x, y]), FRONT_S, 0.003, { bevel: 0.0005 }), P.dark);
  body.add(pin(FRONT_S, 0.0275, 0.003, SIGHT_X - 0.009, SIGHT_X + 0.009, 6), P.steel);
  body.add(block(FRONT_S - 0.002, FRONT_S - 0.0015, SIGHT_Y - 0.009, SIGHT_Y - 0.0006, SIGHT_X - 0.0014, SIGHT_X + 0.0014), P.dot);

  // Sling swivels: a flat ring hanging from a lug on the left, one ahead of the front sight, one on the collar.
  for (const [s, r] of [[FRONT_S + 0.031, TUBE], [-0.395, THROAT + 0.003]]) {
    if (s > 0) body.add(band(s - 0.005, s + 0.005, TUBE, 0.0016), P.steel, { crease: 0.5 });
    body.add(block(s - 0.004, s + 0.004, -0.007, 0.004, -r - 0.006, -r + 0.002, 0.0008), P.steel);
    const ring = fillet([[s - 0.012, -0.001], [s + 0.012, -0.001], [s + 0.012, -0.025, 0.007], [s - 0.012, -0.025, 0.007]], 2);
    const eye = fillet([[s - 0.0085, -0.0045], [s + 0.0085, -0.0045], [s + 0.0085, -0.0215, 0.0045], [s - 0.0085, -0.0215, 0.0045]], 2);
    body.add(prism(ring, 0.0026, { x: -r - 0.0038, holes: [eye] }), P.dark);
  }

  // ---------------------------------------------------------------------------------------------
  // Moving parts
  // ---------------------------------------------------------------------------------------------

  // Trigger, modelled around its pivot.
  const trigger = new Soup();
  trigger.add(
    prism([[-0.004, 0], [0.004, 0], [0.0035, -0.012], [0.0005, -0.024], [-0.0035, -0.03], [-0.0052, -0.029], [-0.003, -0.02], [-0.0025, -0.01]], 0.006, { bevel: 0.0008 }),
    P.dark,
  );

  // The round, as it sits loaded: booster charge and motor tube inside the launcher, then the neck,
  // the double cone of the warhead with its yellow band, and the fuze.
  const round = new Soup();
  const M = MUZZLE_S;
  const turned = (profile, p, caps = [false, false]) => round.add(lathe(profile, 18, { caps }), p, { crease: 0.5 });
  turned([[M - TAIL, 0.012], [M - TAIL + 0.003, 0.0165], [M - 0.115, 0.0165]], P.tan, [true, false]);
  turned([[M - 0.115, 0.0165], [M - 0.112, 0.0195], [M + 0.03, 0.0195], [M + 0.034, 0.0235]], P.motor);
  turned([[M + 0.034, 0.0235], [M + 0.123, 0.042], [M + 0.128, 0.0425]], P.olive);
  turned([[M + 0.128, 0.0425], [M + 0.138, 0.0425]], P.yellow);
  turned([[M + 0.138, 0.0425], [M + 0.143, 0.042], [M + 0.235, 0.0305], [M + 0.325, 0.0145]], P.olive);
  turned([[M + 0.325, 0.0145], [M + 0.327, 0.0125], [M + 0.35, 0.0115]], P.dark);
  turned([[M + 0.35, 0.0115], [M + 0.352, 0.0098], [M + 0.385, 0.0088], [M + 0.405, 0.006], [M + 0.425, 0.0022]], P.bare, [false, true]);

  // ---------------------------------------------------------------------------------------------
  // Assembly
  // ---------------------------------------------------------------------------------------------
  const root = new THREE.Group();
  root.name = 'rocket';
  const part = (soup, name) => {
    const mesh = new THREE.Mesh(soup.build(), material);
    mesh.name = `rocket-${name}`;
    mesh.frustumCulled = false; // always in view, and close enough to the near plane to be culled wrongly
    return mesh;
  };
  const meshes = {
    body: part(body, 'body'),
    trigger: part(trigger, 'trigger'),
    mag: part(round, 'round'), // "the magazine" of this gun is the round itself
  };
  meshes.trigger.position.set(0, -0.038 + DY, -0.108);
  root.add(meshes.body, meshes.trigger, meshes.mag);

  // ---------------------------------------------------------------------------------------------
  // Handling: where the hands go and how the reload is played
  // ---------------------------------------------------------------------------------------------
  const R = def.reload;

  // Support hand cupped under a round tube: the fingers come further round than under a handguard.
  const cup = makePose({ fingers: [1.15, 1.05, 0.55, 0], pinky: [1.2, 1.1, 0.6, -0.05], thumb: [-0.1, 0.25, 0, 0.3, 0.3] });
  // Round the neck of the round, thumb along it toward the nose.
  const clasp = makePose({ fingers: [1.1, 1.15, 0.6, 0], thumb: [0.2, 0.4, 0, 0.3, 0.3] });

  const grip = handKey(1, 'gun', [0.0145, -0.085 + DY, -0.04], [-1, 0, -0.15], [0.08, -0.36, -0.93], POSES.rifleGrip);
  const gripFire = { ...grip, pose: POSES.rifleTrigger };
  const support = handKey(-1, 'gun', [-0.008, -0.043, -0.275], [0.35, 0.94, 0], [0.82, -0.25, -0.5], cup);

  // Reloading, the muzzle swings up and in to meet the left hand.
  const reload = gunPose(0.19, -0.157, -0.066, 0.26, 0.65, -0.15);
  /** A gun-space key as it stands in view space while the launcher is in that pose. */
  const inView = (key) => ({ space: 'rig', pos: key.pos.clone().applyQuaternion(reload.quat).add(reload.pos), quat: reload.quat.clone().multiply(key.quat), pose: key.pose });
  // The round in the hand: cradled from below by its neck, thumb toward the nose.
  const hold = handKey(-1, 'gun', [0.03, -0.02, -(M + 0.065)], [-0.835, 0.551, 0], [0.532, 0.806, -0.259], clasp);
  const seat = turnKey(hold, [0, 0, 0], [0, 0, 1], -0.3);
  const push = turnKey(shiftKey(hold, [0, 0, -0.035]), [0, 0, 0], [0, 0, 1], 0.3);
  const enter = shiftKey(push, [0, 0, -(TAIL - 0.035)]); // tail at the mouth
  const present = shiftKey(enter, [0, 0, -0.07]); // in line with the bore, just clear of it
  const bag = shiftKey(inView(present), [-0.06, -0.52, 0.22]); // the same, below the screen
  const away = shiftKey(bag, [0, 0, 0], POSES.relaxed);

  const load = [
    [0, support],
    [R.magOut, support], // the launcher comes off the shoulder first
    [R.magOut + 0.24, away], // then the hand lets go and drops to the bag
    [R.magShow, bag], // out of sight: a fresh round
    [R.magInsert - 0.14, present],
    [R.magInsert, enter],
    [R.magIn - 0.11, push], // down the tube…
    [R.magIn, seat], // …and turned home
    [R.magIn + 0.1, seat],
    [R.empty - 0.14, support],
  ];

  // The round rides in the left hand from the bag to the tube: this is the hand → round transform.
  const magInHand = new THREE.Matrix4().compose(seat.pos, seat.quat, new THREE.Vector3(1, 1, 1)).invert();

  return {
    id: 'rocket',
    root,
    meshes,
    triangles: body.triangles + trigger.triangles + round.triangles,
    muzzle: new THREE.Vector3(0, 0, -MUZZLE_S),
    /** Nothing is thrown out: the round leaves by the front. */
    eject: new THREE.Vector3(0, 0, -MUZZLE_S),
    sightRear: new THREE.Vector3(SIGHT_X, SIGHT_Y, -REAR_S),
    /** Eye to the ladder leaf when aimed. */
    relief: 0.2,
    /** Recoil and sway turn the tube about the shoulder it lies on. */
    pivot: new THREE.Vector3(0, -0.03, 0.18),
    flash: { star: 0.3, jet: 0.45 },
    poses: {
      hip: def.views.map((v) => gunPose(...v)),
      sprint: gunPose(0.17, -0.15, -0.1, -0.06, 0.78, -0.3),
      reload,
      wall: gunPose(0.27, -0.22, 0, 0.75, 0.25, -0.2),
      holster: gunPose(0.25, -0.5, -0.15, -0.7, 0.3, -0.4),
    },
    /** Tube swing: [time, x, y, z, pitch, yaw, roll] offsets from the hip pose. */
    melee: [
      [0, 0, 0, 0, 0, 0, 0],
      [0.08, 0.05, 0, 0.07, 0.03, -0.22, 0.08], // wound up: back and out to the right
      [0.16, -0.04, 0.03, -0.2, -0.05, 0.42, -0.2], // the muzzle end is thrown forward and across the front
      [0.27, -0.06, 0.02, -0.17, -0.07, 0.5, -0.25],
      [0.55, 0, 0, 0, 0, 0, 0],
    ],
    elbows: { right: new THREE.Vector3(0.36, -0.4, 0.05), left: new THREE.Vector3(-0.3, -0.45, -0.15) },
    magInHand,

    /**
     * Per frame: moves the parts and says where the hands are.
     * ctx: {anim, shotAge, trigger (0…1), left, right (outputs: {a, b, t}), magHeld (output)}
     */
    animate(ctx) {
      const { anim } = ctx;
      meshes.trigger.rotation.x = -0.34 * ctx.trigger;
      ctx.right.a = grip;
      ctx.right.b = gripFire;
      ctx.right.t = ctx.trigger;

      // The round: in the tube while there is one to fire, in the hand on its way there.
      const mesh = meshes.mag;
      mesh.position.set(0, 0, 0);
      mesh.quaternion.identity();
      let held = false;
      let loaded = anim.mag > 0;
      if (anim.reloading) {
        const t = anim.reloadT;
        sampleTrack(load, t, ctx.left);
        if (t >= R.magShow && t < R.magIn) held = loaded = true;
      } else {
        ctx.left.a = ctx.left.b = support;
        ctx.left.t = 0;
      }
      mesh.visible = loaded;
      ctx.magHeld = held;
    },
  };
}
