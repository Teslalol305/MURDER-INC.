// Hold the Block with the player camping up high (review: enemies #1): the real holdout flow, its own
// waves and re-alerts; the player (god mode) never leaves PERCH (deck | office | open) and every second puts
// 45 damage into the nearest enemy he can actually see. At least PERCH_WAVES waves must be cleared within
// PERCH_SECONDS (default 2 in 150 s).
//
//   node build.mjs --dev --out=dist/dev-enemies.html
//   PERCH=deck node tools/shot.cjs dist/dev-enemies.html --params "autostart=1&mode=holdout&q=test&god=1&noaudio=1&nohud=1" \
//        --size 320x180 --scenario tools/scenarios/enemies-perch-holdout.cjs --timeout 900

'use strict';

const SPOTS = { deck: [10, 2.95, 9.3], office: [-21, 2.8, -29], open: [-37.4, 0.15, 8.15] };
const NAME = process.env.PERCH || 'deck';
const POS = SPOTS[NAME];
const SECONDS = +(process.env.PERCH_SECONDS || 150);
const WAVES = +(process.env.PERCH_WAVES || 2);
const VERBOSE = process.env.PERCH_VERBOSE === '1';

module.exports = async (page, h) => {
  await h.skip(10);
  await h.eval((pos) => {
    const G = window.__G;
    const s = (window.__ph = { waves: 0, at: [], hits: 0 });
    G.events.on('objective:done', (ev) => {
      if (ev.id === 'wave') {
        s.waves++;
        s.at.push(+G.enemies.debug().clock.toFixed(1));
      }
    });
    const damage = G.player.damage.bind(G.player);
    G.player.damage = (amount, from, kind) => {
      s.hits++;
      return damage(amount, from, kind);
    };
    G.player.reset({ pos: new G.THREE.Vector3(pos[0], pos[1], pos[2]), yaw: 0 });
  }, POS);
  let last = '';
  for (let i = 0; i < SECONDS; i++) {
    await h.skip(30);
    last = await h.eval((pos) => {
      const G = window.__G;
      const P = G.physics;
      G.player.pos.set(pos[0], pos[1], pos[2]);
      const aim = new G.THREE.Vector3();
      let best = null;
      let bestD = Infinity;
      for (const e of G.enemies.list) {
        if (!e.alive) continue;
        aim.set(e.pos.x, e.pos.y + (e.type === 'goon' ? 1.55 : 0), e.pos.z);
        const d = aim.distanceTo(G.player.eye);
        if (d < bestD && P.lineOfSight(G.player.eye, aim)) {
          best = e;
          bestD = d;
        }
      }
      if (best) G.enemies.damage(best, 45, { point: best.pos.clone(), dir: best.pos.clone().sub(G.player.eye).normalize(), part: 'body', from: 'player', weapon: 'chopper' });
      return `${G.game.state} alive ${G.enemies.aliveCount()} ` + G.enemies.list.filter((e) => e.alive).map((e) => `${e.type[0]}:${e.mode[0]}@${e.pos.x.toFixed(1)},${e.pos.y.toFixed(1)},${e.pos.z.toFixed(1)}`).join(' ');
    }, POS);
    if (VERBOSE && i % 5 === 4) console.log(`${i + 1}s ${last}`);
  }
  const s = await h.eval(() => window.__ph);
  console.log('HOLDOUT', NAME, JSON.stringify(s), '|', last);
  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
  if (s.waves < WAVES) throw new Error(`${NAME}: only ${s.waves} waves cleared in ${SECONDS} s (${last})`);
};
