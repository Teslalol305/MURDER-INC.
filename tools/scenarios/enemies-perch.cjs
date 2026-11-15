// A player camping up high (review: enemies #1): on the sidewalk-shed deck, in the shop's mezzanine
// office, or in the open for comparison. Eight Goons come from the level's own ground spawns, everyone is
// re-alerted every 5 s the way Hold the Block does it, and the player (god mode) shoots back: every 2 s
// he puts 45 damage into the nearest Goon he can actually see. Reports the Goons' bullet hits on him and
// how long the "wave" took to die; fails if any Goon was still alive after PERCH_SECONDS, or if Goons hit
// him less than PERCH_MIN_HITS times while there were Goons up.
//
//   node build.mjs --dev --out=dist/dev-enemies.html
//   PERCH=deck node tools/shot.cjs dist/dev-enemies.html --params "autostart=1&q=test&god=1&noaudio=1&nohud=1&eseed=7" \
//        --size 320x180 --scenario tools/scenarios/enemies-perch.cjs --timeout 600
//
// PERCH = deck | office | open (default deck); PERCH_SHOOT=0 keeps the player's gun quiet (hit rate only);
// PERCH_SECONDS (default 90); PERCH_VERBOSE=1 logs the Goons every 6 s.

'use strict';

const SPOTS = { deck: [10, 2.95, 9.3], office: [-21, 2.8, -29], open: [-37.4, 0.15, 8.15] };
const NAME = process.env.PERCH || 'deck';
const POS = SPOTS[NAME];
const SHOOT = process.env.PERCH_SHOOT !== '0';
const SECONDS = +(process.env.PERCH_SECONDS || 90);
const VERBOSE = process.env.PERCH_VERBOSE === '1';
const MIN_HITS = +(process.env.PERCH_MIN_HITS || 0);

module.exports = async (page, h) => {
  await h.skip(5);
  await h.eval((pos) => {
    const G = window.__G;
    const V = G.THREE.Vector3;
    G.game.setDifficulty('boss');
    G.enemies.clear();
    G.player.reset({ pos: new V(pos[0], pos[1], pos[2]), yaw: 0 });
    const s = (window.__pc = { hits: 0, dmg: 0, killed: 0, upHits: 0, upTime: 0, deadAt: -1, under: 0 });
    const damage = G.player.damage.bind(G.player);
    G.player.damage = (amount, from, kind) => {
      if (kind === 'bullet') {
        s.hits++;
        s.dmg += amount;
      }
      return damage(amount, from, kind);
    };
    G.events.on('enemy:killed', () => s.killed++);
    s.fired = 0;
    s.seeing = 0;
    s.engagedSamples = 0;
    G.events.on('enemy:fire', (ev) => ev.type === 'goon' && s.fired++);
    const sp = G.level.enemySpawns.filter((q) => q.type === 'ground').sort((a, b) => a.pos.distanceTo(G.player.pos) - b.pos.distanceTo(G.player.pos));
    for (let i = 0; i < 8; i++) G.enemies.spawn('goon', sp[(i * 2 + 1) % sp.length].pos.clone(), { alerted: true });
  }, POS);
  const lines = [];
  const steps = Math.round(SECONDS * 30);
  for (let done = 0; done < steps; done += 30) {
    await h.skip(30);
    const r = await h.eval(
      ([done, shoot, pos]) => {
        const G = window.__G;
        const P = G.physics;
        const s = window.__pc;
        const t = (done + 30) / 30;
        G.player.pos.set(pos[0], pos[1], pos[2]); // he stays up there
        if ((done / 30) % 5 === 4) G.enemies.alert(G.player.pos, 90);
        const goons = G.enemies.list.filter((e) => e.alive && e.type === 'goon');
        if (goons.length) s.upTime++;
        else if (s.deadAt < 0) s.deadAt = t;
        for (const e of goons) if (e.mode === 'engage') {
          s.engagedSamples++;
          if (e.sees) s.seeing++;
        }
        // Goons parked under the floor he stands on.
        for (const e of goons) if (P.groundHeight(e.pos.x, e.pos.z, pos[1] + 0.3) > e.pos.y + 1.2) s.under++;
        if (shoot && (done / 30) % 2 === 1) {
          const head = new G.THREE.Vector3();
          let best = null;
          let bestD = Infinity;
          for (const e of goons) {
            head.set(e.pos.x, e.pos.y + 1.55, e.pos.z);
            const d = head.distanceTo(G.player.eye);
            if (d < bestD && P.lineOfSight(G.player.eye, head)) {
              best = e;
              bestD = d;
            }
          }
          if (best) G.enemies.damage(best, 45, { point: best.pos.clone(), dir: best.pos.clone().sub(G.player.eye).normalize(), part: 'body', from: 'player', weapon: 'chopper' });
        }
        return `${t}s hits ${s.hits} ` + goons.map((e) => `${e.mode[0]}${e.sees ? '+' : ''}/${e.sub}@${e.pos.x.toFixed(1)},${e.pos.z.toFixed(1)}${e.hasStand ? `>${e.standX.toFixed(1)},${e.standZ.toFixed(1)}` : ''}`).join(' ');
      },
      [done, SHOOT, POS],
    );
    if (VERBOSE && (done / 30) % 6 === 5) lines.push(r);
  }
  const s = await h.eval(() => window.__pc);
  if (VERBOSE) console.log(lines.join('\n'));
  console.log('PERCH', NAME, JSON.stringify({ ...s, hitsPerMin: +((s.hits / Math.max(1, s.upTime)) * 60).toFixed(1) }));
  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
  if (SHOOT && s.deadAt < 0) throw new Error(`${NAME}: Goons still alive after ${SECONDS} s`);
  if (s.hits < MIN_HITS) throw new Error(`${NAME}: only ${s.hits} Goon hits`);
};
