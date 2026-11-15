// The Vultures in action on the real block, by day: a Goon's telegraph (weapon light) and burst, the rush
// with the pipe, a Buzzard's telegraph (eye) and bolt volley. Each picture waits for the moment, then
// frames it from a camera beside the unit. God mode.
//
//   node build.mjs --dev --out=dist/dev-enemies-full.html
//   node tools/shot.cjs dist/dev-enemies-full.html --params "autostart=1&q=low&god=1&noaudio=1" \
//        --size 800x450 --scenario tools/scenarios/enemies-action.cjs --timeout 800
//
// Also runs on the stub testbed (dist/dev-enemies.html). Screenshots: shots/enemies/action-*.png.

'use strict';

const OUT = 'shots/enemies/action-';

module.exports = async (page, h) => {
  await h.eval(() => {
    const G = window.__G;
    const ui = document.getElementById('ui');
    if (ui) ui.style.display = 'none';
    G.enemies.clear();
    G.player.reset({ pos: new G.THREE.Vector3(-37.4, 0, 5), yaw: -Math.PI / 2 });
  });

  /** Steps until `test(unit)` holds for the unit, at most `max` steps. */
  const waitFor = async (id, test, max) => {
    for (let n = 0; n < max; n += 2) {
      const ok = await h.eval(
        ([i, src]) => {
          const e = window.__G.enemies.list.find((u) => u.id === i);
          return !!e && new Function('e', `return ${src}`)(e);
        },
        [id, test],
      );
      if (ok) return true;
      await h.skip(2);
    }
    return false;
  };

  /** A fixed camera `fwd` m from the unit toward the player, `side` m to one side, `up` m up, looking at it. */
  const frame = async (id, name, fwd, side, up) => {
    await h.eval(
      ([i, f, s, u]) => {
        const G = window.__G;
        const e = G.enemies.list.find((x) => x.id === i);
        const p = G.player.pos;
        const dx = p.x - e.pos.x;
        const dz = p.z - e.pos.z;
        const l = Math.hypot(dx, dz) || 1;
        const fx = dx / l;
        const fz = dz / l;
        const cy = e.type === 'goon' ? e.pos.y + 1.1 : e.pos.y;
        const cam = [e.pos.x + fx * f - fz * s, cy + u, e.pos.z + fz * f + fx * s];
        const look = [e.pos.x, cy, e.pos.z];
        window.__setShot({ cam: [...cam, ...look].map((v) => v.toFixed(2)).join(','), fov: 50 });
      },
      [id, fwd, side, up],
    );
    await h.frames(1);
    await h.shot(`${OUT}${name}.png`);
    await h.eval(() => window.__setShot({ cam: '' }));
  };

  // A Goon 13 m away, alerted: telegraph, then burst.
  const goon = await h.eval(() => {
    const G = window.__G;
    const p = G.player.pos;
    return G.enemies.spawn('goon', new G.THREE.Vector3(p.x + 13, 0, p.z), { alerted: true }).id;
  });
  if (!(await waitFor(goon, "e.sub === 'telegraph' && e.subT > 0.3", 900))) throw new Error('the Goon never telegraphed');
  await frame(goon, 'goon-telegraph', 3, 1.4, 0.3);
  if (!(await waitFor(goon, "e.sub === 'burst'", 60))) throw new Error('no burst after the telegraph');
  await h.skip(2);
  await frame(goon, 'goon-burst', 3.2, -2.4, 1.1);

  // The rush: the player walks up to 2.5 m.
  await h.eval((i) => {
    const G = window.__G;
    const e = G.enemies.list.find((x) => x.id === i);
    G.player.reset({ pos: new G.THREE.Vector3(e.pos.x - 2.4, 0, e.pos.z), yaw: -Math.PI / 2 });
  }, goon);
  if (!(await waitFor(goon, "e.sub === 'windup' || e.sub === 'lunge'", 300))) throw new Error('no rush at 2.4 m');
  await h.skip(4);
  await frame(goon, 'goon-rush', 1.4, 3.4, 1.4);

  // A Buzzard: telegraph (eye) and the volley.
  await h.eval(() => {
    const G = window.__G;
    G.enemies.clear();
    G.player.reset({ pos: new G.THREE.Vector3(-37.4, 0, 5), yaw: -Math.PI / 2 });
  });
  const buzz = await h.eval(() => {
    const G = window.__G;
    const p = G.player.pos;
    return G.enemies.spawn('buzzard', new G.THREE.Vector3(p.x + 12, 4.5, p.z), { alerted: true }).id;
  });
  if (!(await waitFor(buzz, 'e.telegraph > 0.15', 900))) throw new Error('the Buzzard never telegraphed');
  await frame(buzz, 'buzzard-telegraph', 2.6, 1, -0.6);
  if (!(await waitFor(buzz, 'e.telegraph <= 0', 60))) throw new Error('no volley');
  await h.skip(3);
  await frame(buzz, 'buzzard-volley', -1.5, 2.5, 0.6);

  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
};
