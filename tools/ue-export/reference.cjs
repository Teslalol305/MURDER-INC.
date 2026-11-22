// Reference pictures of the web game as it is: for before / after comparison with the Unreal rebuild
// and for the artists. A scenario for the existing harness:
//
//   node tools/shot.cjs dist/index.html --size 1280x720 --timeout 1200 \
//        --params "q=high&dynres=0&god=1&noaudio=1&seed=1994" --scenario tools/ue-export/reference.cjs
//
// Writes 1280x720 PNGs to docs/unreal/reference/ (REF_OUT overrides the directory, REF_ONLY=a,b runs a
// subset by file name). The page runs in step mode with a fixed seed: the pictures repeat exactly.
// Every camera below is in web space (metres, +Y up, north = -Z): "x,y,z, lookX,lookY,lookZ".
//
// A full-depth screenshot of this renderer weighs 1.3 MB, twenty of them far more than the directory may
// (12 MB). Each picture is therefore rewritten with its colour channels rounded to 40 evenly spaced
// levels (lib/png.cjs): the largest change is 3 parts in 255, the file is half the size.
// REF_LEVELS=256 keeps the frames untouched.
//
//   title                          the title screen, 5 s into its fly-through
//   hud-start                      the HUD in play at the start pose
//   day-*   (6)                    fixed cameras by day: the default look
//   night-* (2)                    two of the same cameras by night
//   enemy-goon, enemy-buzzard      one unit each, posed (passive showcase units), by day
//   viewmodel-chopper, -nine       the first-person view with each gun, HUD hidden
//   viewmodel-*-side               the same guns held up side-on (the game's inspect pose)
//   plan-top-down                  the whole block from 400 m up through a 10.6 degree lens, haze off

'use strict';

const path = require('node:path');
const { reduceLevels } = require('./lib/png.cjs');

const OUT = process.env.REF_OUT || 'docs/unreal/reference';
const ONLY = process.env.REF_ONLY ? process.env.REF_ONLY.split(',') : null;
const LEVELS = Number(process.env.REF_LEVELS || 40);

/** Fixed cameras: [name, camera, field of view]. Eye level is 1.68 m above the ground. */
const VIEWS = [
  ['avenue-east', '-27.5,1.68,0.4, 20,2.3,0.2', 62], // under the El between the column rows, just past the west closure, looking east
  ['chop-shop', '-1.6,1.68,-13.4, -15,2.1,-24.5', 68], // inside V&R AUTO BODY from the small bay: lifts, reel 2, the mezzanine
  ['alley', '8.6,1.68,-9.2, 8.3,2.6,-30', 62], // from the alley mouth to the gate at its north end
  ['vacant-lot-mural', '-5.4,1.68,20.5, -16,3.6,18.5', 66], // across the vacant lot to the mural on the pawn shop
  ['cage', '27.2,1.68,-13.8, 38.5,1.6,-25.5', 66], // The Cage from inside its south-west corner: reel 3 at centre court
  ['parking-lot-ipx-truck', '28.5,1.68,19.5, 41.3,1.7,29.7', 62], // the parking lot with the IPX truck
];
const NIGHT = ['avenue-east', 'parking-lot-ipx-truck'];

module.exports = async (page, h) => {
  const want = (name) => !ONLY || ONLY.includes(name);
  const shot = async (name) => {
    const file = path.resolve(OUT, `${name}.png`);
    await h.shot(file);
    const size = LEVELS >= 2 && LEVELS < 256 ? reduceLevels(file, LEVELS) : null;
    console.error(`[reference] ${name}.png${size ? ` ${Math.round(size.before / 1024)} kB -> ${Math.round(size.after / 1024)} kB` : ''}`);
  };
  const hud = (on) => h.eval((show) => document.documentElement.classList.toggle('nohud', !show), on);
  /** A fixed outside camera (hides the viewmodel); '' gives the player's own view back. */
  const camera = (cam, fov) => h.eval(([c, f]) => window.__setShot({ cam: c, fov: f }), [cam, fov ?? null]);
  /** Lets the lamps hand over, the exposure settle and the shadows redraw, then draws. */
  const settle = async (steps = 75) => {
    await h.skip(steps);
    await h.eval(() => window.__G.atmos.settleLights());
    await h.frames(3);
  };

  // ---------------------------------------------------------------------------------------------
  // Title
  // ---------------------------------------------------------------------------------------------

  await h.eval(() => window.__G.settings.set('time', 'day'));
  if (want('title')) {
    await h.skip(150); // 5 s into the fly-through, past its fade-in
    await h.frames(2);
    await shot('title');
  }

  // ---------------------------------------------------------------------------------------------
  // In play
  // ---------------------------------------------------------------------------------------------

  await h.eval(() => window.__G.game.start({ mode: 'mission', skipIntro: true }));
  await h.skip(20);
  await h.frames(2);
  const state = await h.eval(() => window.__G.game.state);
  if (state !== 'playing') throw new Error(`the run did not start: state ${state}`);

  if (want('hud-start')) {
    // The start pose, a few seconds in: the objective line has typed out, the patrol has not found him.
    await h.skip(110);
    await h.frames(2);
    await shot('hud-start');
  }

  // Scenery: nobody on the block, no interface.
  await h.eval(() => window.__G.enemies.clear());
  await hud(false);

  for (const [name, cam, fov] of VIEWS) {
    if (!want(`day-${name}`)) continue;
    await camera(cam, fov);
    await settle();
    await shot(`day-${name}`);
  }

  // ---------------------------------------------------------------------------------------------
  // The Vultures: passive showcase units (they hold a pose and never act)
  // ---------------------------------------------------------------------------------------------

  // In the sun on the shop's driveway apron, in front of the cinder-block wall between its two doors,
  // facing the avenue (a yaw of π looks at +Z, south). One at a time, seen three-quarter on.
  const pose = (type, y, opts) =>
    h.eval(([t, height, o]) => {
      const G = window.__G;
      G.enemies.clear();
      const e = G.enemies.spawn(t, new G.THREE.Vector3(-8.6, height, -8.8), { passive: true, yaw: Math.PI, ...o });
      return !!e;
    }, [type, y, opts]);
  if (want('enemy-goon')) {
    if (!(await pose('goon', 0, { show: { aim: 1 } }))) throw new Error('the Goon could not be spawned');
    await camera('-10.5,1.4,-6.1, -8.6,1.0,-8.8', 44);
    await settle(60);
    await shot('enemy-goon');
  }
  if (want('enemy-buzzard')) {
    if (!(await pose('buzzard', 2.2, {}))) throw new Error('the Buzzard could not be spawned');
    await camera('-10.2,2.05,-6.4, -8.6,2.2,-8.8', 40);
    await settle(60);
    await shot('enemy-buzzard');
  }
  if (want('enemy-goon') || want('enemy-buzzard')) await h.eval(() => window.__G.enemies.clear());

  // ---------------------------------------------------------------------------------------------
  // The guns: the player's own view at the start pose, then the inspect pose
  // ---------------------------------------------------------------------------------------------

  const guns = [['chopper', 'Digit1'], ['nine', 'Digit2']];
  if (guns.some(([id]) => want(`viewmodel-${id}`) || want(`viewmodel-${id}-side`))) {
    await camera('', null);
    await h.eval(() => {
      const G = window.__G;
      G.player.reset({ pos: G.level.playerStart.pos.clone(), yaw: G.level.playerStart.yaw });
    });
    for (const [id, code] of guns) {
      if (!want(`viewmodel-${id}`) && !want(`viewmodel-${id}-side`)) continue;
      const current = await h.eval(() => window.__G.weapon.current);
      if (current !== id) {
        await h.key(code, true);
        await h.skip(2);
        await h.key(code, false);
        await h.skip(40); // holster and draw
      }
      const now = await h.eval(() => window.__G.weapon.current);
      if (now !== id) throw new Error(`could not switch to the ${id}: holding the ${now}`);
      if (want(`viewmodel-${id}`)) {
        await h.eval(() => window.__G.weapon.inspect(null));
        await settle(30);
        await shot(`viewmodel-${id}`);
      }
      if (want(`viewmodel-${id}-side`)) {
        // Held up in front of the camera, left side on, against the game's plain backdrop.
        await h.eval((gun) => window.__G.weapon.inspect({ dist: gun === 'nine' ? 0.36 : 0.62, yaw: 1.5708, x: gun === 'nine' ? 0.1 : 0.22, y: 0.04, backdrop: true }), id);
        await h.frames(3);
        await shot(`viewmodel-${id}-side`);
        await h.eval(() => window.__G.weapon.inspect(null));
      }
    }
  }

  // ---------------------------------------------------------------------------------------------
  // The plan: straight down from 400 m through a long lens, north up, haze off
  // ---------------------------------------------------------------------------------------------

  if (want('plan-top-down')) {
    await camera('0,400,0.4, 0,0,0', 10.6);
    await h.skip(60);
    const density = await h.eval(() => {
      const fog = window.__G.scene.fog;
      const was = fog.density;
      fog.density = 0; // 400 m of haze would hide the block; nothing else is changed
      return was;
    });
    await h.frames(3);
    await shot('plan-top-down');
    await h.eval((d) => {
      window.__G.scene.fog.density = d;
    }, density);
  }

  // ---------------------------------------------------------------------------------------------
  // Night: the alternate look, from two of the same cameras
  // ---------------------------------------------------------------------------------------------

  if (NIGHT.some((name) => want(`night-${name}`))) {
    await h.eval(() => {
      const G = window.__G;
      G.settings.set('time', 'night');
      G.atmos.setTime('night'); // in a run the rig only changes on a reset: switch it here
    });
    for (const [name, cam, fov] of VIEWS) {
      if (!NIGHT.includes(name) || !want(`night-${name}`)) continue;
      await camera(cam, fov);
      await settle(90);
      await shot(`night-${name}`);
    }
    await h.eval(() => {
      const G = window.__G;
      G.settings.set('time', 'day');
      G.atmos.setTime('day');
    });
  }

  await camera('', null);
  await hud(true);
  const errors = await h.errors();
  if (errors.length) throw new Error(`the page reported errors: ${errors[0]}`);
};
