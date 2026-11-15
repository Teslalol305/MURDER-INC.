// The NINE: a full-size 9 mm pistol. Brushed steel slide over a black frame, checkered grips, an
// exposed hammer, three-dot sights, and a touch of gold on the trigger and the magazine base.
//
// Gun space: origin on the bore axis at the back of the slide, −Z down the barrel, +Y up, +X right.
// Profiles are [s, y] with s = distance forward of the origin.

import * as THREE from 'three';
import { FINISH, Soup, block, fillet, lathe, paint, pin, prism, rod } from './build.js';
import { POSES, gunPose, handKey, sampleTrack, shiftKey } from './handling.js';
import { ease } from './springs.js';

const SIGHT_Y = 0.0185;
const SLIDE_TRAVEL = 0.044;
const MUZZLE_S = 0.201;
// The magazine slides along the rake of the grip.
const MAG_AXIS = new THREE.Vector3(0, 0.968, -0.25).normalize(); // from base to lips

export function buildNine(material, def, strike = 0.55, goldHex = 0xe7b53a) {
  const P = {
    slide: paint(0xaeb1b6, 0.4, 1, { finish: FINISH.brushed }),
    frame: paint(0x17181b, 0.5, 0.65, { wear: paint(0x5b5f66, 0.35, 0.9) }),
    grip: paint(0x0e0e10, 0.78, 0, { finish: FINISH.checker }),
    dark: paint(0x24262a, 0.45, 0.9, { wear: paint(0x7c8188, 0.3, 1) }),
    barrel: paint(0xbbbec4, 0.22, 1),
    black: paint(0x040405, 0.92, 0),
    gold: paint(goldHex, 0.24, 1),
    steel: paint(0x9da1a7, 0.34, 1, { finish: FINISH.brushed }),
    brass: paint(0xcaa23d, 0.28, 1),
    copper: paint(0xb5683a, 0.3, 1),
    dot: paint(0xf2f0e4, 0.6, 0, { glow: 0.5 }),
  };

  // ---------------------------------------------------------------------------------------------
  // Frame: everything that stays put
  // ---------------------------------------------------------------------------------------------
  const frame = new Soup();
  const outline = fillet(
    [
      [-0.007, -0.0135],
      [0.196, -0.0135],
      [0.196, -0.03, 0.004],
      [0.132, -0.032],
      [0.128, -0.066, 0.008],
      [0.078, -0.0715, 0.006],
      [0.066, -0.06],
      [0.041, -0.128, 0.003],
      [-0.025, -0.128, 0.006],
      [-0.033, -0.118],
      [-0.017, -0.058, 0.01],
      [-0.01, -0.036],
      [-0.018, -0.0245, 0.003],
      [-0.016, -0.0165, 0.003],
    ],
    3,
  );
  const guard = fillet([[0.073, -0.04, 0.003], [0.1235, -0.04, 0.004], [0.1225, -0.061, 0.006], [0.084, -0.066, 0.005], [0.075, -0.057]], 2);
  frame.add(prism(outline, 0.0245, { bevel: 0.0022, holes: [guard], steps: 2 }), P.frame, { crease: 0.5 });
  // Accessory rail under the dust cover.
  for (const s of [0.142, 0.156, 0.17]) frame.add(block(s, s + 0.006, -0.0335, -0.03, -0.0085, 0.0085, 0.0006), P.frame);
  // Recoil spring guide showing under the barrel.
  frame.add(rod([0, -0.0088, -0.12], [0, -0.0088, -0.1985], 0.0036, 0.0036, 8, [false, true]), P.steel, { crease: 0.9 });

  // Grip panels.
  const panel = fillet([[-0.006, -0.04, 0.004], [0.057, -0.045, 0.005], [0.037, -0.122, 0.005], [-0.027, -0.122, 0.006]], 2);
  for (const side of [-1, 1]) frame.add(prism(panel, 0.0034, { x: side * 0.0134, bevel: 0.0012 }), P.grip, { crease: 0.5 });
  for (const side of [-1, 1]) {
    frame.add(pin(0.004, -0.052, 0.0024, side * 0.0146, side * 0.0153, 6), P.dark);
    frame.add(pin(0.012, -0.112, 0.0024, side * 0.0146, side * 0.0153, 6), P.dark);
  }

  // Hammer (cocked), slide stop, safety, magazine button.
  frame.add(prism([[-0.003, -0.012], [-0.003, 0.003], [-0.0105, 0.0105], [-0.0155, 0.0075], [-0.0095, -0.002], [-0.011, -0.012]], 0.0075, { bevel: 0.0008 }), P.dark);
  frame.add(prism([[0.058, -0.0165], [0.098, -0.0165], [0.1, -0.0125], [0.094, -0.0105], [0.058, -0.0115]], 0.0022, { x: -0.0134, bevel: 0.0005 }), P.dark);
  frame.add(prism(fillet([[0.004, -0.0125], [0.026, -0.0125], [0.03, -0.008], [0.022, -0.0045, 0.002], [0.004, -0.006]], 2), 0.003, { x: -0.014, bevel: 0.0006 }), P.dark);
  frame.add(pin(0.0625, -0.0405, 0.0042, -0.0146, -0.012, 8), P.dark);

  // ---------------------------------------------------------------------------------------------
  // Slide (moves back), barrel (tilts as the slide unlocks)
  // ---------------------------------------------------------------------------------------------
  const slide = new Soup();
  slide.add(
    prism(fillet([[0, -0.0135], [0.196, -0.0135], [0.196, 0.0055, 0.003], [0.189, 0.0125, 0.004], [0.004, 0.0125, 0.003], [0, 0.0085]], 2), 0.027, { bevel: 0.0026, steps: 2 }),
    P.slide,
    { crease: 0.5 },
  );
  // Cocking serrations.
  for (let i = 0; i < 7; i++) {
    const s = 0.007 + i * 0.0048;
    for (const side of [-1, 1]) slide.add(block(s, s + 0.002, -0.0105, 0.0075, side * 0.01352, side * 0.01372), P.black);
  }
  // Ejection port with the barrel hood showing in it.
  slide.add(block(0.086, 0.126, 0.0045, 0.01268, 0.0035, 0.01372), P.black);
  slide.add(block(0.089, 0.123, 0.0128, 0.01305, 0.0045, 0.011), P.barrel);
  // Sights: rear notch with two dots, front blade with one.
  slide.add(block(0.007, 0.018, 0.0124, 0.0146, -0.0085, 0.0085, 0.0006), P.dark);
  slide.add(block(0.007, 0.018, 0.0146, SIGHT_Y, -0.0085, -0.0021, 0.0005), P.dark);
  slide.add(block(0.007, 0.018, 0.0146, SIGHT_Y, 0.0021, 0.0085, 0.0005), P.dark);
  for (const side of [-1, 1]) slide.add(block(0.0066, 0.0071, 0.0155, 0.0176, side * 0.0052 - 0.0011, side * 0.0052 + 0.0011), P.dot);
  slide.add(prism([[0.178, 0.0124], [0.19, 0.0124], [0.1885, SIGHT_Y], [0.1835, SIGHT_Y]], 0.0034, { bevel: 0.0004 }), P.dark);
  slide.add(block(0.1832, 0.1836, 0.0152, 0.0178, -0.0011, 0.0011), P.dot);

  const barrel = new Soup();
  barrel.add(lathe([[0.05, 0.0068], [MUZZLE_S, 0.0068], [MUZZLE_S + 0.0004, 0.0058]], 12, { caps: [true, false] }), P.barrel, { crease: 0.6 });
  barrel.add(lathe([[MUZZLE_S + 0.0004, 0.0058], [0.196, 0.0046], [0.17, 0.0044]], 12, { caps: [false, true], inside: true }), P.black, { crease: 0.9, ao: 0 });

  // Trigger, modelled around its pivot.
  const trigger = new Soup();
  trigger.add(
    prism(fillet([[-0.003, 0.002], [0.004, 0.002], [0.005, -0.01], [0.002, -0.022, 0.003], [-0.003, -0.027], [-0.0052, -0.0255], [-0.002, -0.016, 0.004], [-0.004, -0.004]], 2), 0.0068, { bevel: 0.001 }),
    P.gold,
  );

  // Magazine: steel body that lives inside the grip, gold base plate.
  const mag = new Soup();
  mag.add(prism([[0.006, -0.037], [0.04, -0.037], [0.016, -0.1275], [-0.018, -0.1275]], 0.0195, { bevel: 0.0012 }), P.steel);
  for (const y of [-0.06, -0.078, -0.096]) {
    for (const side of [-1, 1]) mag.add(pin(0.012 - (y + 0.06) * 0.26, y, 0.0022, side * 0.0096, side * 0.0099, 6), P.black); // witness holes
  }
  mag.add(prism(fillet([[-0.026, -0.1275], [0.044, -0.1275], [0.046, -0.1345, 0.003], [-0.03, -0.1345, 0.003]], 2), 0.0262, { bevel: 0.0022, steps: 2 }), P.gold, { crease: 0.5 });
  const round = new Soup();
  round.add(lathe([[0.004, 0.0048], [0.022, 0.0048], [0.023, 0.0044]], 8, { y: -0.0335, caps: [true, false] }), P.brass, { crease: 0.9 });
  round.add(lathe([[0.023, 0.0044], [0.03, 0.0036], [0.034, 0.0012]], 8, { y: -0.0335, caps: [false, true] }), P.copper, { crease: 0.9 });

  // ---------------------------------------------------------------------------------------------
  // Assembly
  // ---------------------------------------------------------------------------------------------
  const root = new THREE.Group();
  root.name = 'nine';
  const part = (soup, name) => {
    const mesh = new THREE.Mesh(soup.build(), material);
    mesh.name = `nine-${name}`;
    mesh.frustumCulled = false;
    return mesh;
  };
  const meshes = {
    frame: part(frame, 'frame'),
    slide: part(slide, 'slide'),
    barrel: part(barrel, 'barrel'),
    trigger: part(trigger, 'trigger'),
    mag: part(mag, 'mag'),
    round: part(round, 'round'),
  };
  // The barrel pivots about its lug, the trigger about its pin.
  const lug = new THREE.Vector3(0, -0.008, -0.07);
  meshes.barrel.geometry.translate(-lug.x, -lug.y, -lug.z);
  meshes.barrel.position.copy(lug);
  meshes.trigger.position.set(0, -0.031, -0.091);
  meshes.mag.add(meshes.round);
  root.add(meshes.frame, meshes.slide, meshes.barrel, meshes.trigger, meshes.mag);

  // ---------------------------------------------------------------------------------------------
  // Handling
  // ---------------------------------------------------------------------------------------------
  const R = def.reload;
  const grip = handKey(1, 'gun', [0.0135, -0.078, -0.014], [-1, 0, -0.1], [0.06, -0.25, -0.97], POSES.pistolGrip);
  const gripFire = { ...grip, pose: POSES.pistolTrigger };
  const gripThumb = { ...grip, pose: POSES.pistolThumbDown };
  // Support hand over the firing hand's fingers, thumb forward along the frame.
  const support = handKey(-1, 'gun', [-0.0165, -0.09, -0.024], [1, 0.05, -0.2], [0.05, -0.55, -0.83], POSES.pistolSupport);
  // Under the grip, magazine base in the palm.
  const seat = handKey(-1, 'gun', [0.004, -0.138, -0.012], [MAG_AXIS.x, MAG_AXIS.y, MAG_AXIS.z], [0, -0.25, -0.968], POSES.palm);
  const along = (d) => [MAG_AXIS.x * d, MAG_AXIS.y * d, MAG_AXIS.z * d];
  const start = shiftKey(seat, along(-0.05), POSES.magPinch); // lips entering the well
  const below = shiftKey(seat, [0.0, -0.13, 0.05], POSES.magPinch); // lined up under the grip
  const away = handKey(-1, 'rig', [-0.1, -0.33, -0.3], [0.3, 0.5, -0.8], [0.4, 0.8, -0.4], POSES.relaxed);
  const pouch = handKey(-1, 'rig', [-0.17, -0.52, -0.2], [0.3, 0.5, -0.8], [0.4, 0.8, -0.4], POSES.magPinch);

  const swap = [
    [0, support],
    [0.15, away],
    [R.magShow - 0.1, pouch],
    [R.magShow, pouch], // a fresh magazine in the hand
    [R.magInsert - 0.1, below],
    [R.magInsert, start],
    [R.magIn, seat], // palm drives it home
    [R.magIn + 0.07, seat],
  ];
  const tactical = [...swap, [R.tactical - 0.03, support]];
  const empty = [...swap, [R.magIn + 0.3, away], [R.slideRelease, away], [R.empty - 0.04, support]];
  const magInHand = new THREE.Matrix4().compose(seat.pos, seat.quat, new THREE.Vector3(1, 1, 1)).invert();

  /** Slide position (0 forward … 1 back) this long after a shot. */
  const cycle = (age) => (age < 0.018 ? age / 0.018 : Math.max(0, 1 - (age - 0.018) / 0.042));

  return {
    id: 'nine',
    root,
    meshes,
    triangles: frame.triangles + slide.triangles + barrel.triangles + trigger.triangles + mag.triangles + round.triangles,
    muzzle: new THREE.Vector3(0, 0, -MUZZLE_S),
    eject: new THREE.Vector3(0.012, 0.014, -0.105),
    sightRear: new THREE.Vector3(0, SIGHT_Y, -0.0125),
    relief: 0.37,
    /** Recoil turns the pistol about the wrist. */
    pivot: new THREE.Vector3(0, -0.085, 0.03),
    flash: { star: 0.12, jet: 0.13 },
    poses: {
      hip: def.views.map((v) => gunPose(...v)),
      sprint: gunPose(0.05, -0.2, -0.3, -0.6, 0.6, -0.2),
      reload: gunPose(0.03, -0.085, -0.33, 0.5, 0.32, -0.5),
      wall: gunPose(0.07, -0.13, -0.24, 0.75, 0.1, 0),
      holster: gunPose(0.17, -0.44, -0.24, -0.6, 0.2, -0.4),
    },
    /** Pistol whip: [time, x, y, z, pitch, yaw, roll] offsets from the hip pose. */
    melee: [
      [0, 0, 0, 0, 0, 0, 0],
      [0.08, 0.04, 0.05, 0.06, 0.55, -0.25, 0.35], // wound up: back, up and to the right
      [0.16, -0.1, 0.02, -0.15, 1.05, 0.35, -0.6], // butt first across the front
      [0.27, -0.11, 0.0, -0.13, 1.1, 0.4, -0.65],
      [0.55, 0, 0, 0, 0, 0, 0],
    ],
    elbows: { right: new THREE.Vector3(0.24, -0.38, -0.08), left: new THREE.Vector3(-0.15, -0.4, -0.15) },
    magInHand,

    animate(ctx) {
      const { anim } = ctx;
      meshes.trigger.rotation.x = -0.3 * ctx.trigger;
      ctx.right.a = grip;
      ctx.right.b = gripFire;
      ctx.right.t = ctx.trigger;

      // Slide: cycles with every shot, stays back on an empty magazine until the stop is thumbed.
      let slideK = cycle(ctx.shotAge);
      let held = false;
      let visible = true;
      let loaded = anim.mag > 0;
      const mesh = meshes.mag;
      mesh.position.set(0, 0, 0);
      mesh.quaternion.identity();
      if (anim.reloading) {
        const t = anim.reloadT;
        sampleTrack(anim.reloadEmpty ? empty : tactical, t, ctx.left);
        if (anim.reloadEmpty) slideK = t < R.slideRelease ? 1 : Math.max(0, 1 - (t - R.slideRelease) / 0.03);
        // Thumb: down on the magazine button, later up on the slide stop.
        const press = Math.max(0, 1 - Math.abs(t - R.magOut) / 0.12, anim.reloadEmpty ? 1 - Math.abs(t - R.slideRelease) / 0.1 : 0);
        if (press > 0) {
          ctx.right.b = gripThumb;
          ctx.right.t = press;
        }
        if (t >= R.magOut && t < R.magShow) {
          // The old magazine drops free along the grip.
          const since = t - R.magOut;
          const fall = 4.5 * since * since + 0.25 * since;
          mesh.position.copy(MAG_AXIS).multiplyScalar(-fall);
          mesh.rotation.x = -1.4 * since;
          visible = fall < 0.4;
        } else if (t >= R.magShow && t < R.magIn) {
          held = true;
          loaded = true;
        }
      } else {
        // A pistol whip is thrown one-handed: the support hand lets go for the length of the strike.
        ctx.left.a = support;
        ctx.left.b = away;
        ctx.left.t = anim.melee ? Math.min(ease(anim.meleeT / 0.08), ease((strike - anim.meleeT) / 0.16)) : 0;
        if (anim.mag === 0) slideK = 1;
      }
      meshes.slide.position.z = SLIDE_TRAVEL * slideK;
      meshes.barrel.rotation.x = 0.04 * Math.min(1, slideK * 3);
      mesh.visible = visible;
      meshes.round.visible = loaded;
      ctx.magHeld = held;
    },
  };
}
