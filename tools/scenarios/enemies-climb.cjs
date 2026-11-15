// Buzzard reinforcements that must cross buildings to reach the fight (review: enemies #0). Buzzards
// spawn at the rear-lane and alley air points with the player on the avenue; everyone is re-alerted every
// 4.5 s, the way Hold the Block does it, for 60 s. Every one of them must reach the fight (engage), none
// may overlap solid geometry or leave the bounds at any sample, and none may hang still for 6 s while
// not engaged.
//
//   node build.mjs --dev --out=dist/dev-enemies.html
//   node tools/shot.cjs dist/dev-enemies.html --params "autostart=1&q=test&god=1&noaudio=1&nohud=1" \
//        --size 320x180 --scenario tools/scenarios/enemies-climb.cjs --timeout 600
//
// Optional: CLIMB_POS="x,y,z" moves the player, CLIMB_SECONDS the length, CLIMB_VERBOSE=1 logs every sample.

'use strict';

const POS = (process.env.CLIMB_POS || '5,0,-2').split(',').map(Number);
const SECONDS = +(process.env.CLIMB_SECONDS || 60);
const VERBOSE = process.env.CLIMB_VERBOSE === '1';

module.exports = async (page, h) => {
  await h.skip(5);
  await h.eval((pos) => {
    const G = window.__G;
    const V = G.THREE.Vector3;
    G.enemies.clear();
    G.player.reset({ pos: new V(pos[0], pos[1], pos[2]), yaw: 0 });
    const spots = [
      [4, 8.6, 28.5], [2.8, 8.6, 27.6], [5.2, 8.6, 29.4], [-1, 8.6, 28.4], // over the rear lane
      [8.5, 9.6, -24], [7.5, 9.6, -25], [9.5, 9.6, -23], [8.5, 9.6, -26], // over the alley
    ];
    window.__bs = spots.map(([x, y, z]) => G.enemies.spawn('buzzard', new V(x, y, z), { alerted: true }));
    window.__cl = window.__bs.map((e) => ({ engaged: false, at: 0, x: e.pos.x, y: e.pos.y, z: e.pos.z, still: 0, maxStill: 0, inside: 0, out: 0 }));
  }, POS);
  const samples = Math.round(SECONDS / 1.5);
  const lines = [];
  for (let i = 0; i < samples; i++) {
    await h.skip(45);
    lines.push(
      await h.eval((i) => {
        const G = window.__G;
        const P = G.physics;
        const b = P.bounds;
        if (i % 3 === 2) G.enemies.alert(G.player.pos, 90);
        return window.__bs
          .map((e, k) => {
            const c = window.__cl[k];
            if (!e.alive) return 'dead';
            if (e.mode === 'engage' && !c.engaged) {
              c.engaged = true;
              c.at = (i + 1) * 1.5;
            }
            // Solid for a drone: what blocks movement, minus the player-only seals, fence, glass and railings.
            const hitBox = P.boxes.find((q) => !q.bulletOnly && (!q.playerOnly || q.tag === 'hoist') && q.max.y > e.pos.y - 0.15 && q.min.y < e.pos.y + 0.15 &&
              Math.hypot(e.pos.x - Math.max(q.min.x, Math.min(q.max.x, e.pos.x)), e.pos.z - Math.max(q.min.z, Math.min(q.max.z, e.pos.z))) < 0.45);
            if (hitBox) c.inside++;
            if (e.pos.x < b.minX || e.pos.x > b.maxX || e.pos.z < b.minZ || e.pos.z > b.maxZ) c.out++;
            const moved = Math.hypot(e.pos.x - c.x, e.pos.y - c.y, e.pos.z - c.z);
            c.x = e.pos.x; c.y = e.pos.y; c.z = e.pos.z;
            c.still = moved < 0.3 && e.mode !== 'engage' ? c.still + 1.5 : 0;
            c.maxStill = Math.max(c.maxStill, c.still);
            return `${e.mode[0]}${e.pos.x.toFixed(1)},${e.pos.y.toFixed(1)},${e.pos.z.toFixed(1)}${hitBox ? `!${hitBox.tag}` : ''}`;
          })
          .join(' ');
      }, i),
    );
  }
  if (VERBOSE) console.log(lines.map((l, i) => `${((i + 1) * 1.5).toFixed(1)}s ${l}`).join('\n'));
  const r = await h.eval(() => window.__cl.map((c, k) => ({ k, engaged: c.engaged, at: c.at, inside: c.inside, out: c.out, maxStill: c.maxStill })));
  console.log('CLIMB', JSON.stringify(r));
  const bad = r.filter((c) => !c.engaged || c.inside || c.out || c.maxStill >= 6);
  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
  if (bad.length) throw new Error(`${bad.length} Buzzards failed: ${JSON.stringify(bad)}\n${lines.slice(-6).join('\n')}`);
};
