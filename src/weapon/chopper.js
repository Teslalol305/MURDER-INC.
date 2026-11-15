// The CHOPPER: a compact wood-and-steel automatic carbine. Stamped receiver with a ribbed top cover,
// laminated-wood handguard and grip, a curved 30-round magazine, a reciprocating charging handle on
// the left where the shooter can see it, a stubby muzzle booster, and an under-folding stock tucked
// along the receiver. Iron sights: a notch at the back of the cover, a hooded post over the gas block.
//
// Gun space: origin on the bore axis at the back of the receiver, −Z down the barrel, +Y up, +X right.
// Profiles are [s, y] with s = distance forward of the origin.

import * as THREE from 'three';
import { FINISH, Soup, block, fillet, lathe, loft, paint, pin, prism, rod, sweep } from './build.js';
import { POSES, gunPose, handKey, sampleCurve, sampleTrack, shiftKey, turnKey } from './handling.js';

export const SIGHT_Y = 0.0555; // height of the sight line over the bore
const REAR_S = 0.0235; // rear notch
const FRONT_S = 0.409; // front post
const MUZZLE_S = 0.4975;
const BOLT_TRAVEL = 0.092;

// The magazine follows an arc: it leaves the receiver leaning forward and keeps curving.
const MAG = { radius: 0.26, from: 0.12, to: 0.92, top: [0.19, -0.026] };
const MAG_CENTRE = [MAG.top[0] + MAG.radius * Math.cos(MAG.from), MAG.top[1] + MAG.radius * Math.sin(MAG.from)];
const magPoint = (a, offset = 0) => [
  MAG_CENTRE[0] - (MAG.radius + offset) * Math.cos(a),
  MAG_CENTRE[1] - (MAG.radius + offset) * Math.sin(a),
];

/** An oval pressed flat against a side of the gun: a slot or a dimple. */
function oval(s, y, rs, ry, x0, x1) {
  return pin(0, 0, 1, x0, x1, 8).scale(1, ry, rs).translate(0, y, -s);
}

export function buildChopper(material, def) {
  const wear = paint(0x8d9299, 0.3, 1);
  const P = {
    steel: paint(0x363a40, 0.48, 0.8, { wear }),
    cover: paint(0x2e3136, 0.52, 0.8, { wear }),
    dark: paint(0x202226, 0.55, 0.8, { wear }),
    bare: paint(0xb1b6bd, 0.26, 1, { finish: FINISH.brushed }),
    wood: paint(0x74401f, 0.38, 0, { finish: FINISH.wood }),
    black: paint(0x050506, 0.92, 0),
    mag: paint(0x23262a, 0.5, 0.88, { wear }),
    brass: paint(0xcaa23d, 0.28, 1),
    copper: paint(0xb5683a, 0.3, 1),
    dot: paint(0xf2f0e4, 0.6, 0, { glow: 0.55 }),
  };

  // ---------------------------------------------------------------------------------------------
  // Body: everything that never moves relative to the receiver
  // ---------------------------------------------------------------------------------------------
  const body = new Soup();

  // Receiver: a stamped steel box.
  body.add(
    prism([[0, -0.04], [0.238, -0.04], [0.256, -0.027], [0.256, 0.012], [-0.004, 0.012], [-0.004, -0.034]], 0.032, { bevel: 0.0012 }),
    P.steel,
  );
  // Rivets and pins through it.
  for (const [s, y] of [[0.012, 0.001], [0.03, -0.03], [0.084, -0.013], [0.112, -0.021], [0.226, -0.006], [0.242, -0.016], [0.228, -0.027]]) {
    body.add(pin(s, y, 0.0022, -0.0166, 0.0166, 6), P.dark);
  }

  // Top cover with its three stamped ribs.
  const coverRing = (s, w, top) => ({ c: [0, 0.012, -s], w, h: 0, top, bot: 0.002, exp: 2.4 });
  body.add(loft([coverRing(0.002, 0.029, 0.011), coverRing(0.012, 0.0325, 0.021), coverRing(0.03, 0.0325, 0.022), coverRing(0.186, 0.0325, 0.022)], 12), P.cover, { crease: 0.9 });
  for (const s of [0.056, 0.102, 0.148]) {
    body.add(loft([coverRing(s - 0.004, 0.0338, 0.0228), coverRing(s + 0.004, 0.0338, 0.0228)], 12), P.cover, { crease: 0.9 });
  }
  // The slot the charging handle runs in (left), and the ejection port (right).
  body.add(block(0.078, 0.192, 0.012, 0.017, -0.0167, -0.0158), P.black);
  body.add(block(0.112, 0.19, 0.0122, 0.0235, 0.0152, 0.0165), P.black);

  // Sight block between the cover and the handguard.
  body.add(prism(fillet([[0.186, 0.012], [0.256, 0.012], [0.256, 0.026], [0.25, 0.032, 0.004], [0.196, 0.032, 0.004], [0.186, 0.026]], 2), 0.03, { bevel: 0.0012 }), P.steel);
  body.add(pin(0.222, 0.022, 0.003, -0.0158, 0.0158, 6), P.dark);

  // Rear sight: a leaf with a square notch at the back of the cover, two dots beside the notch.
  body.add(block(0.01, 0.036, 0.033, 0.0398, -0.008, 0.008, 0.0008), P.dark);
  body.add(block(0.0215, 0.0255, 0.0395, SIGHT_Y - 0.0042, -0.0105, 0.0105, 0.0006), P.dark);
  body.add(block(0.0215, 0.0255, SIGHT_Y - 0.0042, SIGHT_Y, -0.0105, -0.0022, 0.0006), P.dark);
  body.add(block(0.0215, 0.0255, SIGHT_Y - 0.0042, SIGHT_Y, 0.0022, 0.0105, 0.0006), P.dark);
  for (const side of [-1, 1]) {
    body.add(block(0.0211, 0.0216, SIGHT_Y - 0.0034, SIGHT_Y - 0.001, side * 0.0044 - 0.0012, side * 0.0044 + 0.0012), P.dot);
  }

  // Handguard: wooden lower and upper halves with the barrel showing between them.
  const lower = (s, w) => ({ c: [0, -0.02, -s], w, h: 0, top: 0.016, bot: 0.022, exp: 3 });
  body.add(loft([lower(0.25, 0.04), lower(0.258, 0.044), lower(0.32, 0.046), lower(0.375, 0.044), lower(0.385, 0.041)], 14), P.wood, { crease: 0.9 });
  const upper = (s, w, top) => ({ c: [0, 0.016, -s], w, h: 0, top, bot: 0.012, exp: 2.2 });
  body.add(loft([upper(0.262, 0.031, 0.015), upper(0.268, 0.034, 0.017), upper(0.366, 0.034, 0.017), upper(0.372, 0.031, 0.015)], 12), P.wood, { crease: 0.9 });
  // Cooling slots, as dark ovals let into the wood.
  for (const side of [-1, 1]) {
    for (const s of [0.283, 0.318, 0.353]) body.add(oval(s, -0.014, 0.011, 0.0032, side * 0.0224, side * 0.0232), P.black);
    for (const s of [0.295, 0.34]) body.add(pin(s, 0.021, 0.0036, side * 0.0166, side * 0.0172, 8), P.black);
  }
  // Retaining band.
  body.add(block(0.385, 0.3925, -0.0435, 0.034, -0.0225, 0.0225, 0.001), P.steel);

  // Barrel, gas tube, gas block with the front sight.
  body.add(lathe([[0.25, 0.0085], [0.392, 0.0085], [0.3925, 0.0075], [0.432, 0.0075]], 10, { caps: [false, false] }), P.dark, { crease: 0.9 });
  body.add(rod([0, 0.019, -0.255], [0, 0.019, -0.396], 0.0065, 0.0065, 8, [false, false]), P.dark, { crease: 0.9 });
  body.add(prism(fillet([[0.3925, -0.014], [0.426, -0.014], [0.426, 0.012], [0.42, 0.03], [0.398, 0.03], [0.3925, 0.02]], 2), 0.022, { bevel: 0.001 }), P.steel);
  const ear = fillet([[0.398, 0.03], [0.42, 0.03], [0.4185, 0.05], [0.413, 0.063, 0.004], [0.405, 0.063, 0.004], [0.3995, 0.05]], 2);
  for (const side of [-1, 1]) body.add(prism(ear, 0.002, { x: side * 0.0098, bevel: 0.0004 }), P.dark);
  body.add(rod([0, 0.03, -FRONT_S], [0, SIGHT_Y, -FRONT_S], 0.0014, 0.0012, 6), P.dark);
  body.add(block(FRONT_S - 0.0018, FRONT_S - 0.0013, SIGHT_Y - 0.008, SIGHT_Y - 0.0002, -0.0008, 0.0008), P.dot);

  // Muzzle booster: a fat cylinder that opens into a cone.
  body.add(
    lathe(
      [[0.426, 0.0095], [0.432, 0.0095], [0.434, 0.0128], [0.466, 0.0128], [0.468, 0.0112], [0.473, 0.0112], [0.475, 0.0128], [0.48, 0.0128], [MUZZLE_S, 0.0162], [MUZZLE_S + 0.0004, 0.015]],
      14,
      { caps: [true, false] },
    ),
    P.steel,
    { crease: 0.5 },
  );
  body.add(lathe([[MUZZLE_S + 0.0004, 0.015], [0.482, 0.0078], [0.446, 0.007]], 14, { caps: [false, true], inside: true }), P.black, { crease: 0.9, ao: 0 });

  // Pistol grip.
  body.add(
    sweep(
      [[0.07, -0.034], [0.063, -0.055], [0.051, -0.085], [0.037, -0.115], [0.027, -0.139]],
      (t) => ({ w: 0.0275 + 0.003 * Math.sin(t * Math.PI), d: 0.04 + 0.007 * t, exp: 2.8 }),
      12,
      [false, true],
    ),
    P.wood,
    { crease: 0.9 },
  );
  body.add(pin(0.03, -0.139, 0.0028, -0.004, 0.004, 6), P.dark); // grip screw

  // Trigger guard, magazine catch, selector.
  body.add(
    prism([[0.088, -0.04], [0.091, -0.079], [0.152, -0.079], [0.156, -0.04], [0.153, -0.04], [0.1495, -0.0765], [0.0935, -0.0765], [0.0905, -0.04]], 0.014, { bevel: 0.0006 }),
    P.steel,
  );
  body.add(block(0.15, 0.157, -0.063, -0.04, -0.006, 0.006, 0.0008), P.dark);
  body.add(prism([[0.072, -0.018], [0.084, -0.018], [0.11, -0.0255], [0.11, -0.031], [0.084, -0.027], [0.072, -0.027]], 0.0024, { x: -0.0176, bevel: 0.0005 }), P.dark);
  body.add(pin(0.078, -0.0225, 0.0036, -0.0192, -0.016, 8), P.steel);

  // Under-folding stock: two flat arms along the receiver, the butt plate tucked under the handguard.
  const arm = [[0.014, -0.014], [0.03, -0.014], [0.236, -0.0435], [0.236, -0.0555], [0.03, -0.03], [0.014, -0.03]];
  for (const side of [-1, 1]) body.add(prism(arm, 0.003, { x: side * 0.0188, bevel: 0.0007 }), P.steel);
  body.add(pin(0.022, -0.022, 0.0062, -0.0212, 0.0212, 8), P.dark);
  body.add(pin(0.236, -0.0495, 0.0042, -0.0208, 0.0208, 8), P.dark);
  body.add(prism(fillet([[0.234, -0.0525], [0.33, -0.0525], [0.334, -0.046, 0.003], [0.337, -0.046], [0.337, -0.0605, 0.004], [0.234, -0.0605, 0.003]], 2), 0.034, { bevel: 0.002 }), P.steel);

  // ---------------------------------------------------------------------------------------------
  // Moving parts
  // ---------------------------------------------------------------------------------------------

  // Bolt carrier (seen through the port) and the charging handle that rides with it.
  const bolt = new Soup();
  bolt.add(block(0.118, 0.188, 0.0125, 0.0225, 0.0125, 0.0166, 0.0006), P.bare);
  bolt.add(pin(0.18, 0.0145, 0.0042, -0.03, -0.015, 8), P.steel);
  bolt.add(rod([-0.028, 0.0145, -0.18], [-0.042, 0.0145, -0.18], 0.006, 0.0056, 10), P.dark, { crease: 0.5 });
  bolt.add(rod([-0.0318, 0.0145, -0.18], [-0.0335, 0.0145, -0.18], 0.0064, 0.0064, 10, [false, false]), P.steel);
  bolt.add(rod([-0.0368, 0.0145, -0.18], [-0.0385, 0.0145, -0.18], 0.0062, 0.0062, 10, [false, false]), P.steel);

  // Trigger, modelled around its pivot.
  const trigger = new Soup();
  trigger.add(
    prism([[-0.004, 0], [0.004, 0], [0.0035, -0.012], [0.0005, -0.024], [-0.0035, -0.03], [-0.0052, -0.029], [-0.003, -0.02], [-0.0025, -0.01]], 0.006, { bevel: 0.0008 }),
    P.dark,
  );

  // Magazine: a curved steel box with a side rib, a spine and a floor plate.
  const mag = new Soup();
  const arc = [];
  for (let i = 0; i <= 8; i++) arc.push(MAG.from + ((MAG.to - MAG.from) * i) / 8);
  mag.add(sweep(arc.map((a) => magPoint(a)), (t) => ({ w: 0.0255, d: 0.062 - 0.003 * t, exp: 5 }), 12, [true, false]), P.mag, { crease: 0.8 });
  mag.add(sweep(arc.slice(1, 8).map((a) => magPoint(a)), () => ({ w: 0.0268, d: 0.014, exp: 2 }), 8, [true, true]), P.mag, { crease: 0.9 });
  mag.add(sweep(arc.slice(1).map((a) => magPoint(a, -0.0305)), () => ({ w: 0.009, d: 0.003, exp: 2 }), 6, [true, true]), P.mag, { crease: 0.9 });
  mag.add(sweep([magPoint(MAG.to - 0.004), magPoint(MAG.to + 0.012)], () => ({ w: 0.0278, d: 0.0635, exp: 5 }), 12, [true, true]), P.dark, { crease: 0.8 });

  // The round on top of a loaded magazine (hidden inside the receiver when the magazine is in).
  const round = new Soup();
  round.add(lathe([[0.172, 0.0052], [0.173, 0.0056], [0.203, 0.0056], [0.206, 0.0034]], 8, { y: -0.0195, caps: [true, false] }), P.brass, { crease: 0.9 });
  round.add(lathe([[0.206, 0.0034], [0.214, 0.003], [0.222, 0.0008]], 8, { y: -0.0195, caps: [false, true] }), P.copper, { crease: 0.9 });

  // ---------------------------------------------------------------------------------------------
  // Assembly
  // ---------------------------------------------------------------------------------------------
  const root = new THREE.Group();
  root.name = 'chopper';
  const part = (soup, name) => {
    const mesh = new THREE.Mesh(soup.build(), material);
    mesh.name = `chopper-${name}`;
    mesh.frustumCulled = false; // always in view, and close enough to the near plane to be culled wrongly
    return mesh;
  };
  const meshes = {
    body: part(body, 'body'),
    bolt: part(bolt, 'bolt'),
    trigger: part(trigger, 'trigger'),
    mag: part(mag, 'mag'),
    round: part(round, 'round'),
  };
  const triggerPivot = new THREE.Vector3(0, -0.038, -0.108);
  meshes.trigger.position.copy(triggerPivot);
  meshes.mag.add(meshes.round);
  root.add(meshes.body, meshes.bolt, meshes.trigger, meshes.mag);

  // ---------------------------------------------------------------------------------------------
  // Handling: where the hands go and how the reload is played
  // ---------------------------------------------------------------------------------------------
  const R = def.reload;
  const hinge = [0, -0.04, -0.222]; // front lip of the magazine well: the magazine rocks about it

  const grip = handKey(1, 'gun', [0.0145, -0.085, -0.04], [-1, 0, -0.15], [0.08, -0.36, -0.93], POSES.rifleGrip);
  const gripFire = { ...grip, pose: POSES.rifleTrigger };
  const support = handKey(-1, 'gun', [-0.01, -0.0615, -0.315], [0.35, 0.94, 0], [0.82, -0.2, -0.53], POSES.rifleSupport);
  // Around the magazine: palm on its left face, fingers across the front, thumb up toward the catch.
  const magHold = handKey(-1, 'gun', [-0.0135, -0.118, -0.222], [1, 0, 0], [0, 0.479, -0.878], POSES.magHold);
  const magRock = shiftKey(turnKey(magHold, hinge, [1, 0, 0], 0.42), [0, -0.03, -0.012]);
  const magAway = shiftKey(magRock, [-0.04, -0.12, 0.03]);
  const pouch = handKey(-1, 'rig', [-0.2, -0.46, -0.2], [0.4, 0.3, -0.85], [0.35, 0.85, -0.4], POSES.magHold);
  // Two fingers over the charging handle.
  const boltGrab = handKey(-1, 'gun', [-0.052, -0.012, -0.186], [0.85, 0.3, 0.42], [0.25, 0.93, -0.25], POSES.hook);
  const boltCheck = shiftKey(boltGrab, [0, 0, BOLT_TRAVEL * 0.32]);
  const boltBack = shiftKey(boltGrab, [0, 0, BOLT_TRAVEL]);
  const boltOff = shiftKey(boltBack, [-0.03, -0.02, -0.02], POSES.relaxed);

  const [check0, check1] = R.pressCheck;
  const swap = [
    [0, support],
    [0.27, magHold],
    [R.magOut, magHold], // thumb on the catch, magazine comes free
    [R.magOut + 0.13, magRock],
    [R.magOut + 0.28, magAway],
    [R.magShow - 0.06, pouch], // out of sight: the empty one goes, a fresh one comes
    [R.magShow, pouch],
    [R.magInsert - 0.09, magAway],
    [R.magInsert, magRock], // front lip hooked
    [R.magIn, magHold], // rocked home
    [R.tug + 0.06, magHold],
  ];
  const tactical = [...swap, [check0 - 0.01, boltGrab], [check1, boltCheck], [check1 + 0.06, boltGrab], [R.tactical - 0.02, support]];
  const empty = [...swap, [R.boltBack, boltGrab], [R.boltBack + 0.11, boltBack], [R.boltRelease, boltBack], [R.boltRelease + 0.12, boltOff], [R.empty - 0.06, support]];
  const rackTactical = [[check0, 0], [check1, 0.32], [check1 + 0.05, 0]];
  const rackEmpty = [[R.boltBack, 0], [R.boltBack + 0.11, 1], [R.boltRelease, 1], [R.boltRelease + 0.03, 0]];
  const magGone = [R.magOut + 0.3, R.magShow]; // while the hand is out of sight

  // The magazine rides in the left hand between "out" and "in": this is the hand → magazine transform.
  const magInHand = new THREE.Matrix4().compose(magHold.pos, magHold.quat, new THREE.Vector3(1, 1, 1)).invert();

  /** Bolt position (0 forward … 1 back) this long after a shot: back fast, forward a little slower. */
  const cycle = (age) => (age < 0.02 ? age / 0.02 : Math.max(0, 1 - (age - 0.02) / 0.045));

  return {
    id: 'chopper',
    root,
    meshes,
    triangles: body.triangles + bolt.triangles + trigger.triangles + mag.triangles + round.triangles,
    muzzle: new THREE.Vector3(0, 0, -MUZZLE_S),
    eject: new THREE.Vector3(0.019, 0.018, -0.15),
    sightRear: new THREE.Vector3(0, SIGHT_Y, -REAR_S),
    /** Eye to rear sight when aimed. */
    relief: 0.16,
    /** Where recoil rotates the gun about: the back of the receiver, in the firing hand. */
    pivot: new THREE.Vector3(0, -0.03, 0.02),
    flash: { star: 0.2, jet: 0.34 },
    poses: {
      hip: def.views.map((v) => gunPose(...v)),
      sprint: gunPose(0.05, -0.2, -0.27, -0.32, 0.8, -0.3),
      reload: gunPose(0.05, -0.105, -0.31, 0.4, 0.34, -0.55),
      wall: gunPose(0.09, -0.15, -0.14, 0.62, 0.12, -0.1),
      holster: gunPose(0.2, -0.46, -0.2, -0.55, 0.25, -0.45),
    },
    /** Rifle-butt strike: [time, x, y, z, pitch, yaw, roll] offsets from the hip pose. */
    melee: [
      [0, 0, 0, 0, 0, 0, 0],
      [0.08, 0.05, -0.02, 0.07, 0.08, -0.3, 0.15],
      [0.16, -0.13, 0.05, -0.2, -0.18, 1.2, -0.5],
      [0.27, -0.14, 0.03, -0.16, -0.24, 1.3, -0.55],
      [0.55, 0, 0, 0, 0, 0, 0],
    ],
    elbows: { right: new THREE.Vector3(0.3, -0.42, 0.06), left: new THREE.Vector3(-0.22, -0.44, -0.24) },
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

      let boltK = cycle(ctx.shotAge);
      let held = false;
      let visible = true;
      let loaded = anim.mag > 0;
      if (anim.reloading) {
        const t = anim.reloadT;
        sampleTrack(anim.reloadEmpty ? empty : tactical, t, ctx.left);
        boltK = Math.max(boltK, sampleCurve(anim.reloadEmpty ? rackEmpty : rackTactical, t));
        if (t >= R.magOut && t < R.magIn) {
          held = true;
          visible = t < magGone[0] || t >= magGone[1];
          if (t >= magGone[1]) loaded = true;
        }
      } else {
        ctx.left.a = ctx.left.b = support;
        ctx.left.t = 0;
      }
      meshes.bolt.position.z = BOLT_TRAVEL * boltK;
      meshes.mag.visible = visible;
      meshes.round.visible = loaded;
      ctx.magHeld = held;
    },
  };
}
