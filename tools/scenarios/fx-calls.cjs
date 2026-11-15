// Explosives on the real block (CONTRACT 11.2): how many draw calls they cost, idle, lit and blown, and
// what a lit tank looks like by day.
//
//   node build.mjs --dev --only=fx,explosives,atmos,level,mats,props --out=dist/dev-fx-day.html
//   node tools/shot.cjs dist/dev-fx-day.html --params "autostart=1&q=low&god=1&nohud=1&noaudio=1" --size 640x360 --scenario tools/scenarios/fx-calls.cjs --timeout 600

'use strict';

const OUT = 'shots/fx';

module.exports = async (page, h) => {
  // Draw calls with and without the explosives (shadow pass included).
  const calls = async (visible) => {
    await h.eval((v) => {
      window.__G.scene.getObjectByName('explosives').visible = v;
    }, visible);
    // Shadows refresh every other frame at `low`: the larger of two frames includes the shadow pass.
    let most = 0;
    for (let i = 0; i < 2; i++) {
      await h.frames(1);
      most = Math.max(most, (await h.stats()).calls);
    }
    return most;
  };
  const info = await h.eval(() => {
    const G = window.__G;
    const root = G.scene.getObjectByName('explosives');
    G.render.post.flash = 0;
    return {
      items: G.explosives.items.length,
      types: G.explosives.items.map((i) => i.type).join(','),
      meshes: root.children.length,
      visible: root.children.filter((m) => m.visible).length,
      instanced: root.children.every((m) => m.isInstancedMesh),
    };
  });
  const keys = Object.keys(await h.stats());
  console.error(`explosives: ${JSON.stringify(info)}; stats keys ${keys.join(',')}`);
  const without = await calls(false);
  const withAll = await calls(true);
  console.error(`draw calls without explosives ${without}, with ${withAll}: ${withAll - without} for ${info.items} items`);
  if (!info.instanced) throw new Error('explosives are not instanced');

  // A lit tank seen from 4 m, then its blast and the wreck it leaves.
  const target = await h.eval(() => {
    const G = window.__G;
    const item = G.explosives.items.find((i) => i.type === 'propane') || G.explosives.items[0];
    const p = item.pos;
    window.__setShot({ cam: `${p.x + 3.2},${p.y + 1.9},${p.z + 2.6},${p.x},${p.y + 0.4},${p.z}`, fov: 60 });
    G.explosives.damage(item, 10, 'player');
    window.__item = item;
    return { type: item.type, pos: [p.x, p.y, p.z], ground: G.physics.groundHeight(p.x, p.z, p.y + 1) };
  });
  console.error(`target ${JSON.stringify(target)}`);
  await h.skip(10);
  await h.frames(1);
  await h.shot(`${OUT}/calls-lit.png`);
  const lit = await h.eval(() => window.__G.scene.getObjectByName('explosives').children.filter((m) => m.visible).length);
  await h.skip(45);
  await h.frames(1);
  await h.shot(`${OUT}/calls-blast.png`);
  await h.skip(120);
  await h.frames(1);
  await h.shot(`${OUT}/calls-wreck.png`);
  const after = await h.eval(() => ({
    state: window.__item.state,
    visible: window.__G.scene.getObjectByName('explosives').children.filter((m) => m.visible).length,
    fx: window.__G.fx.stats(),
  }));
  console.error(`lit meshes visible ${lit}; after ${JSON.stringify(after)}`);
  if (after.state !== 'gone') throw new Error('the tank did not blow');
  await h.eval(() => window.__G.explosives.reset());
  const reset = await h.eval(() => window.__G.explosives.items.every((i) => i.state === 'idle' && i.box));
  if (!reset) throw new Error('reset did not restore the items');
};
