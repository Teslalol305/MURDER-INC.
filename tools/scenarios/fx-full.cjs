// The effects next to whatever real modules exist: the real block, the real Chopper, real Vultures.
//
//   node build.mjs --dev --out=dist/dev-fx-full.html
//   node tools/shot.cjs dist/dev-fx-full.html --params "autostart=1&q=low&god=1" --scenario tools/scenarios/fx-full.cjs --timeout 600
//
// Fires the weapon from the start position, lights and blows the explosive nearest the player seen from
// a clear spot, and brings a Buzzard down. Works with any mix of real and stubbed modules.

'use strict';

const OUT = process.env.FX_OUT || "shots/fx";

module.exports = async (page, h) => {
  const fx = () => h.eval(() => window.__G.fx.stats());
  const stubbed = (await h.stats()).stubbed;
  console.error(`stubbed: ${stubbed.join(', ') || 'none'}`);

  // ---- 1. First person: a burst from the hip -------------------------------------------------------
  await page.mouse.move(480, 270);
  await h.frames(3);
  await h.shot(`${OUT}/full-0-start.png`);
  await h.key('Mouse0', true);
  for (let i = 0; i < 4; i++) {
    await h.frames(i === 0 ? 2 : 1);
    await h.shot(`${OUT}/full-1-burst-${i}.png`);
  }
  await h.frames(8);
  await h.key('Mouse0', false);
  const burst = await h.eval(() => ({ shots: window.__G.combat.stats.shots, fx: window.__G.fx.stats() }));
  console.error(`burst: ${burst.shots} shots; fx ${JSON.stringify(burst.fx)}`);
  if (burst.shots === 0) throw new Error('the weapon did not fire');
  if (burst.fx.tracers + burst.fx.additive + burst.fx.lit + burst.fx.decals === 0) throw new Error('firing produced no effects at all');
  await h.skip(45);
  await h.frames(1);
  await h.shot(`${OUT}/full-2-after-burst.png`);

  // ---- 2. The nearest explosive, from a spot that can see it ----------------------------------------
  const tank = await h.eval(() => {
    const G = window.__G;
    const V = (x, y, z) => new G.THREE.Vector3(x, y, z);
    G.enemies.clear();
    const items = G.explosives.items.filter((i) => i.state === 'idle');
    if (!items.length) return null;
    const p = G.player.pos;
    items.sort((a, b) => a.pos.distanceTo(p) - b.pos.distanceTo(p));
    const item = items[0];
    const height = item.box.max.y - item.box.min.y;
    const centre = V(item.pos.x, item.pos.y + height * 0.5, item.pos.z);
    // Walk around it until a camera position has a clear line to just in front of it.
    let cam = null;
    for (let i = 0; i < 16 && !cam; i++) {
      const a = (i / 16) * Math.PI * 2;
      const from = V(item.pos.x + Math.cos(a) * 6, item.pos.y + 1.7, item.pos.z + Math.sin(a) * 6);
      const front = centre.clone().add(from.clone().sub(centre).setY(0).normalize().multiplyScalar(0.7));
      const inside = G.physics.raycast(from, V(0, 1, 0), 0.01) || G.physics.groundHeight(from.x, from.z, from.y) > from.y - 1.2;
      if (!inside && G.physics.lineOfSight(from, front)) cam = from;
    }
    if (!cam) return null;
    window.__setShot({ cam: `${cam.x},${cam.y},${cam.z},${centre.x},${centre.y + 0.4},${centre.z}`, fov: 60 });
    window.__tank = { item, cam, centre };
    return { type: item.type, x: item.pos.x, z: item.pos.z, count: G.explosives.items.length };
  });
  if (!tank) {
    console.error('no explosive with a clear view: skipping the blast');
  } else {
    console.error(`explosive: ${tank.type} at ${tank.x.toFixed(1)}, ${tank.z.toFixed(1)} (${tank.count} on the block)`);
    await h.frames(2);
    await h.shot(`${OUT}/full-3-tank.png`);
    const lit = await h.eval(() => {
      const G = window.__G;
      const { item, cam, centre } = window.__tank;
      const dir = centre.clone().sub(cam).normalize();
      const res = G.combat.hitscan({ origin: cam, dir, range: 50, damage: 26, from: 'player', weapon: 'chopper' });
      return { type: res.type, state: item.state };
    });
    if (lit.state !== 'lit') throw new Error(`the round did not light it: ${JSON.stringify(lit)}`);
    await h.skip(20);
    await h.frames(1);
    await h.shot(`${OUT}/full-4-jet.png`);
    const fuse = tank.type === 'rack' ? 1.1 : 1.6;
    await h.skip(Math.round(fuse / 0.0333) - 21 + 1);
    for (const [steps, name] of [[1, 'a'], [3, 'b'], [8, 'c'], [30, 'd']]) {
      await h.skip(steps - 1);
      await h.frames(1);
      await h.shot(`${OUT}/full-5-blast-${name}.png`);
    }
    const gone = await h.eval(() => window.__tank.item.state);
    if (gone !== 'gone') throw new Error(`the explosive is ${gone} after its fuse`);
  }

  // ---- 3. A Buzzard shot down --------------------------------------------------------------------
  const drone = await h.eval(() => {
    const G = window.__G;
    const V = (x, y, z) => new G.THREE.Vector3(x, y, z);
    const p = G.player.pos;
    const at = V(p.x + 9, 5, p.z - 3);
    const enemy = G.enemies.spawn('buzzard', at, { alerted: true });
    if (!enemy) return null;
    window.__setShot({ cam: `${p.x},1.7,${p.z},${at.x},${at.y - 1.5},${at.z}`, fov: 60 });
    window.__drone = enemy;
    return { hp: enemy.hp };
  });
  if (drone) {
    await h.frames(2);
    await h.eval(() => {
      const G = window.__G;
      const e = window.__drone;
      G.events.emit('impact', { point: e.pos.clone(), normal: new G.THREE.Vector3(0, 0, 1), surface: 'drone', dir: new G.THREE.Vector3(0, 0, -1), from: 'player', enemy: e });
      G.enemies.damage(e, 999, { point: e.pos.clone(), dir: new G.THREE.Vector3(1, 0, 0), part: 'body', from: 'player', weapon: 'chopper' });
    });
    for (const [steps, name] of [[2, 'a'], [12, 'b'], [14, 'c'], [10, 'd'], [10, 'e']]) {
      await h.skip(steps - 1);
      await h.frames(1);
      await h.shot(`${OUT}/full-6-buzzard-${name}.png`);
    }
  }

  console.error(`fx at the end: ${JSON.stringify(await fx())}`);
  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors (${errors.length}): ${errors[0]}`);
};
