// Review probe (read-only): game-rule edge cases across modules.
'use strict';

module.exports = async (page, h) => {
  const out = {};
  const log = (k, v) => {
    out[k] = v;
    console.log(k, JSON.stringify(v));
  };

  // 1. Reachability of reels and the truck zone: free standing spots inside the interaction / extraction radius.
  log('reach', await h.eval(() => {
    const G = window.__G;
    const res = {};
    const sample = (c, R, rad = 0.32) => {
      let free = 0, tot = 0, best = Infinity;
      for (let r = 0.3; r <= R; r += 0.15) {
        for (let a = 0; a < Math.PI * 2; a += Math.PI / 24) {
          const x = c.x + Math.cos(a) * r, z = c.z + Math.sin(a) * r;
          const y = G.physics.groundHeight(x, z, c.y + 0.5);
          tot++;
          if (Math.abs(y - c.y) > 0.5) continue;
          if (G.physics.overlapsCylinder(x, z, rad, y + 0.05, y + 1.8)) continue;
          free++;
          best = Math.min(best, r);
        }
      }
      return { free, tot, nearest: Math.round(best * 100) / 100 };
    };
    for (const o of G.level.objectives) res[o.id] = sample(o.pos, 2.2);
    res.truck = sample(G.level.extraction.pos, 2.5);
    res.truckPos = G.level.extraction.pos.toArray();
    return res;
  }));

  // 2. Death, then "back to title" from the death card: what does the title screen look like?
  await h.eval(() => window.__G.player.damage(1000, null, 'bullet'));
  await h.skip(60);
  log('deadCard', await h.eval(() => ({ state: __G.game.state, screen: __G.menus.screen, low: __G.render.post.lowHealth })));
  await h.eval(() => __G.game.toTitle());
  await h.skip(120);
  log('titleAfterDeath', await h.eval(() => ({ state: __G.game.state, low: __G.render.post.lowHealth, dmg: __G.render.post.damage, alive: __G.player.alive, sat: __G.render.post.saturation })));
  await h.frames(2);
  await h.shot('shots/review/rules-title-after-death.png');

  // 3. Start again from the title: clean?
  await h.eval(() => __G.game.start({ mode: 'mission', skipIntro: true }));
  await h.skip(10);
  log('afterRestart', await h.eval(() => ({ state: __G.game.state, low: __G.render.post.lowHealth, alive: __G.player.alive, health: __G.player.health })));

  // 4. Explosive respawn on top of the player (holdout resupply on even waves).
  log('respawnOnPlayer', await h.eval(() => {
    const G = window.__G;
    const items = G.explosives.items;
    const item = items.find((i) => i.type === 'rack') || items[0];
    // blow it
    G.explosives.damage(item, 1000, 'player');
    return { type: item.type, pos: item.pos.toArray(), state: item.state };
  }));
  await h.skip(10);
  log('respawnMove', await h.eval(() => {
    const G = window.__G;
    const item = G.explosives.items.find((i) => i.type === 'rack') || G.explosives.items[0];
    G.player.invulnerable = true;
    G.player.health = 100;
    const p = item.pos.clone();
    G.player.reset({ pos: new G.THREE.Vector3(p.x, G.physics.groundHeight(p.x, p.z, 2), p.z), yaw: 0 });
    G.player.invulnerable = true;
    const before = item.state;
    G.explosives.reset();
    return { before, after: item.state, player: G.player.pos.toArray() };
  }));
  await h.key('KeyW', true);
  await h.skip(45);
  await h.key('KeyW', false);
  await h.skip(5);
  log('respawnAfterWalk', await h.eval(() => {
    const G = window.__G;
    const item = G.explosives.items.find((i) => i.type === 'rack') || G.explosives.items[0];
    const b = item.box;
    const p = G.player.pos;
    const inside = b && p.x > b.min.x - 0.3 && p.x < b.max.x + 0.3 && p.z > b.min.z - 0.3 && p.z < b.max.z + 0.3;
    return { player: p.toArray().map((v) => Math.round(v * 100) / 100), box: b ? [b.min.toArray(), b.max.toArray()] : null, overlapping: inside, y: p.y };
  }));
  console.log('errors', JSON.stringify(await h.errors()));
};
