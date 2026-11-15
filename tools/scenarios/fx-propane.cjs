// A lit propane tank: the jet, the blast, and the chain reaction through a cluster of explosives.
//
//   node build.mjs --dev --only=fx,explosives --out=dist/dev-fx.html
//   node tools/shot.cjs dist/dev-fx.html --params "autostart=1&q=low&god=1&nohud=1" --scenario tools/scenarios/fx-propane.cjs --timeout 400
//
// Four explosives are added to the level in a row on the avenue, each within chain range of the next:
// tank, tank, welding rack, tank. One round into the first; the rest follows by itself.

const OUT = 'shots/fx';
const CAM = '-17.5,2.6,6.2,-9,0.9,2.2'; // from the west, a little above head height
const ROW = [
  ['propane', -13, 2.2],
  ['propane', -10.4, 3.1],
  ['rack', -7.6, 1.6],
  ['propane', -4.2, 2.6],
];

module.exports = async (page, h) => {
  const state = () =>
    h.eval(() => {
      const G = window.__G;
      const mine = G.explosives.items.slice(-4);
      return {
        states: mine.map((i) => i.state),
        hp: mine.map((i) => i.hp),
        solid: mine.map((i) => !!i.box && G.physics.boxes.includes(i.box)),
        fx: G.fx.stats(),
        events: window.__log,
      };
    });

  await h.eval(([row, cam]) => {
    const G = window.__G;
    G.enemies.clear();
    G.fx.clear();
    for (const [type, x, z] of row) G.level.explosives.push({ type, pos: new G.THREE.Vector3(x, 0, z), yaw: 0.3 });
    G.explosives.reset();
    window.__log = { lit: 0, blast: 0, explosion: 0, fuses: [] };
    G.events.on('explosive:lit', (e) => {
      window.__log.lit++;
      window.__log.fuses.push(Math.round(e.fuse * 100) / 100);
    });
    G.events.on('explosive:blast', () => window.__log.blast++);
    G.events.on('explosion', () => window.__log.explosion++);
    window.__setShot({ cam, fov: 60 });
  }, [ROW, CAM]);
  await h.frames(2);
  await h.shot(`${OUT}/propane-0-idle.png`);

  // One Chopper round from the south sidewalk into the first tank.
  const hit = await h.eval(() => {
    const G = window.__G;
    const tank = G.explosives.items.slice(-4)[0];
    const origin = new G.THREE.Vector3(tank.pos.x - 0.5, 1.5, tank.pos.z + 6);
    const dir = new G.THREE.Vector3(tank.pos.x, 0.35, tank.pos.z).sub(origin).normalize();
    const res = G.combat.hitscan({ origin, dir, range: 100, damage: 26, from: 'player', weapon: 'chopper' });
    G.fx.tracer(origin, res.point);
    return { type: res.type, isTank: res.item === tank };
  });
  if (hit.type !== 'explosive' || !hit.isTank) throw new Error(`the round missed the tank: ${JSON.stringify(hit)}`);

  let s = await state();
  if (s.states[0] !== 'lit' || s.hp[0] !== 24 || s.events.lit !== 1 || s.events.fuses[0] !== 1.6) throw new Error(`not lit: ${JSON.stringify(s)}`);

  // The jet over its 1.6 s (48 steps), then the blast.
  await h.frames(4);
  await h.shot(`${OUT}/propane-1-jet-early.png`);
  s = await state();
  if (s.fx.emitters < 1 || s.fx.additive < 8) throw new Error(`no jet: ${JSON.stringify(s.fx)}`);
  await h.skip(34);
  await h.frames(2);
  await h.shot(`${OUT}/propane-2-jet-late.png`);
  await h.eval(() => window.__setShot({ cam: '-15.6,1.0,3.2,-12.6,0.7,2.4', fov: 50 })); // side on to the jet
  await h.frames(1);
  await h.shot(`${OUT}/propane-2-jet-close.png`);
  await h.eval((cam) => window.__setShot({ cam, fov: 60 }), CAM);
  s = await state();
  if (s.states[0] !== 'lit') throw new Error(`blew early: ${JSON.stringify(s.states)}`);

  await h.skip(6);
  await h.frames(2); // 49 steps since the hit: it has just gone
  await h.shot(`${OUT}/propane-3-blast.png`);
  s = await state();
  if (s.states[0] !== 'gone' || s.solid[0] || s.events.explosion !== 1) throw new Error(`no blast at 1.6 s: ${JSON.stringify(s)}`);
  if (s.states[1] !== 'lit') throw new Error(`the next tank was not set off: ${JSON.stringify(s.states)}`);

  // The ripple down the row.
  for (const [steps, name] of [[5, '4-chain-a'], [7, '5-chain-b'], [9, '6-chain-c'], [14, '7-chain-d'], [30, '8-smoke']]) {
    await h.skip(steps - 1);
    await h.frames(1);
    await h.shot(`${OUT}/propane-${name}.png`);
  }
  s = await state();
  if (s.states.some((x) => x !== 'gone') || s.solid.some(Boolean)) throw new Error(`the chain stopped: ${JSON.stringify(s.states)}`);
  if (s.events.blast !== 4 || s.events.explosion !== 4 || s.events.lit !== 4) throw new Error(`events: ${JSON.stringify(s.events)}`);
  if (s.events.fuses.slice(1).some((f) => f < 0.14 || f > 0.62)) throw new Error(`chain fuses out of range: ${s.events.fuses}`);
  console.error(`chain fuses: ${s.events.fuses.join(', ')} s; fx at the end: ${JSON.stringify(s.fx)}`);

  // Resupply: everything back, solid, unlit.
  await h.skip(200);
  await h.eval(() => {
    window.__G.fx.clear();
    window.__G.explosives.reset();
  });
  await h.frames(2);
  await h.shot(`${OUT}/propane-9-reset.png`);
  s = await state();
  if (s.states.some((x) => x !== 'idle') || !s.solid.every(Boolean) || s.hp.join() !== '50,50,70,50') throw new Error(`reset: ${JSON.stringify(s)}`);

  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
};
