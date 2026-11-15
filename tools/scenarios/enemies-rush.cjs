// The pipe rush and the Cage's chain-link (review: enemies #2). The fence is see- and shoot-through
// (player-only collider), so a Goon outside it may shoot a player inside, but never club him through it.
// Three cases: the reviewers' (player just inside the south fence, Goon on the sidewalk), the verifier's
// (player 0.3 m inside, Goon 1 m outside, off the midpoint), and the control: open ground, where the rush
// must still land.
//
//   node build.mjs --dev --out=dist/dev-enemies.html
//   node tools/shot.cjs dist/dev-enemies.html --params "autostart=1&q=test&god=1&noaudio=1&nohud=1" \
//        --size 320x180 --scenario tools/scenarios/enemies-rush.cjs --timeout 600

'use strict';

const CASES = [
  { name: 'fence', player: [27, 0, -12.65], goon: [27, 0.15, -11.6], fence: true },
  { name: 'fence-offset', player: [29.5, 0, -12.5], goon: [29.2, 0.15, -11.1], fence: true },
  { name: 'open', player: [-20, 0, -1], goon: [-20.5, 0, 1.1], fence: false }, // the avenue, under the El
];

module.exports = async (page, h) => {
  const out = [];
  for (const c of CASES) {
    await h.eval((c) => {
      const G = window.__G;
      const V = G.THREE.Vector3;
      G.enemies.clear();
      G.player.reset({ pos: new V(c.player[0], c.player[1], c.player[2]), yaw: 0 });
      const s = (window.__rush = { melee: 0, windup: 0, strike: 0, min: Infinity });
      if (!window.__rushHooked) {
        window.__rushHooked = true;
        const damage = G.player.damage.bind(G.player);
        G.player.damage = (amount, from, kind) => {
          if (kind === 'melee') window.__rush.melee++;
          return damage(amount, from, kind);
        };
        G.events.on('enemy:melee', (ev) => window.__rush[ev.phase] = (window.__rush[ev.phase] || 0) + 1);
      }
      window.__e = G.enemies.spawn('goon', new V(c.goon[0], c.goon[1], c.goon[2]), { alerted: true, yaw: Math.PI });
    }, c);
    for (let i = 0; i < 12; i++) {
      await h.skip(15);
      await h.eval((c) => {
        const G = window.__G;
        const e = window.__e;
        G.player.pos.set(c.player[0], G.player.pos.y, c.player[2]); // the player keeps his spot
        window.__rush.min = Math.min(window.__rush.min, Math.hypot(e.pos.x - c.player[0], e.pos.z - c.player[2]));
      }, c);
    }
    const s = await h.eval(() => window.__rush);
    out.push({ name: c.name, ...s, min: +s.min.toFixed(2) });
  }
  console.log('RUSH', JSON.stringify(out));
  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
  for (const r of out) {
    const c = CASES.find((k) => k.name === r.name);
    if (c.fence && r.melee) throw new Error(`${r.name}: the pipe hit through the fence ${JSON.stringify(r)}`);
    if (!c.fence && !r.melee) throw new Error(`${r.name}: the rush never landed in the open ${JSON.stringify(r)}`);
  }
};
