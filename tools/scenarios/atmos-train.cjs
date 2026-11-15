// The El train: sends one over the block and photographs the pass from the street.
//
//   node build.mjs --dev --only=atmos --out=dist/dev-atmos.html
//   node tools/shot.cjs dist/dev-atmos.html --params "shot=1&nohud=1" --scenario tools/scenarios/atmos-train.cjs
//
// Checks: `train:pass` arrives as approach → over → gone with sensible durations, the train is where
// atmos.train says it is, pooled flashes fire while it is overhead, nothing is left behind afterwards.
// Writes shots/atmos/train-*.png (ATMOS_TAG adds a suffix).

const OUT = 'shots/atmos';

module.exports = async (page, h) => {
  const tag = process.env.ATMOS_TAG ? `-${process.env.ATMOS_TAG}` : '';
  await h.eval(() => {
    const G = window.__G;
    window.__train = [];
    G.events.on('train:pass', (e) => window.__train.push({ phase: e.phase, duration: e.duration, dir: e.dir, t: G.time.t }));
    // Count the pooled flashes the train asks for.
    window.__flashes = 0;
    const flash = G.render.lights.flash;
    G.render.lights.flash = (...args) => {
      window.__flashes++;
      return flash(...args);
    };
    G.atmos.passTrain(1, 1.2); // eastbound, 1.2 s before its nose reaches the block
  });

  const state = () => h.eval(() => ({ ...window.__G.atmos.train }));
  const shot = async (name, cam, fov = 74) => {
    await h.eval(([c, f]) => window.__setShot({ cam: c, fov: f }), [cam, fov]);
    await h.frames(2);
    await h.shot(`${OUT}/train-${name}${tag}.png`);
  };

  // 1. Coming in from the west, seen from the south sidewalk.
  await h.skip(110);
  let s = await state();
  if (!s.active || s.phase !== 'over') throw new Error(`the train should be over the block by now: ${JSON.stringify(s)}`);
  await shot('1-arriving', '-20,1.68,9.5,-40,8,2');

  // 2. Overhead: standing under the El looking up the avenue, then along the street at the light on the road.
  await h.skip(90);
  await shot('2-overhead', '-6,1.68,-1,14,5.5,1.5');
  await shot('3-street', '-12,1.68,4.2,10,0.6,-0.5');
  await shot('4-side', '17,1.68,10.4,2,8.4,1', 68);

  // 3. From above, the whole train on the deck.
  await shot('5-above', '2,17,24,0,7,1', 60);

  // 4. Let it leave, then make sure it has gone.
  await h.skip(900);
  s = await state();
  const log = await h.eval(() => ({ events: window.__train, flashes: window.__flashes }));
  console.error(`atmos train: ${JSON.stringify(log)}`);
  const phases = log.events.map((e) => e.phase).join(',');
  if (!phases.startsWith('approach,over,gone')) throw new Error(`train:pass phases were '${phases}'`);
  for (const e of log.events) if (!(e.duration > 0)) throw new Error(`train:pass ${e.phase} has no duration`);
  if (log.flashes < 8) throw new Error(`only ${log.flashes} flashes during a pass`);
  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
};
