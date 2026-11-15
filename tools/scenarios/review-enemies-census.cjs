// Review (enemies): static census of spawns, cover points and nav traps in the real block. No pictures.
'use strict';
module.exports = async (page, h) => {
  await h.skip(5);
  const r = await h.eval(() => {
    const G = window.__G;
    const P = G.physics;
    const nav = P.nav;
    const V = G.THREE.Vector3;
    const out = {};
    const start = G.level.playerStart.pos;
    // 1. boxes that stop a 1.8 m capsule but not the nav grid
    const traps = [];
    const cols = nav.cols, rows = nav.rows, o = nav.origin, grid = nav.grid;
    for (const b of P.boxes) {
      if (b.bulletOnly) continue;
      const navBlocks = !b.noNav && !b.playerOnly && b.max.y >= 0.47 && b.min.y <= 1.5;
      if (navBlocks) continue;
      if (b.min.y >= 1.8 || b.max.y <= 0.42) continue; // walked under or stepped over by a goon
      // free nav cells whose centre is within 0.3 m of the box footprint
      let free = 0;
      const i0 = Math.max(0, Math.floor((b.min.x - 0.3 - o.x) / 0.5)), i1 = Math.min(cols - 1, Math.floor((b.max.x + 0.3 - o.x) / 0.5));
      const j0 = Math.max(0, Math.floor((b.min.z - 0.3 - o.z) / 0.5)), j1 = Math.min(rows - 1, Math.floor((b.max.z + 0.3 - o.z) / 0.5));
      for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
        const cx = o.x + (i + 0.5) * 0.5, cz = o.z + (j + 0.5) * 0.5;
        if (cx < b.min.x - 0.3 || cx > b.max.x + 0.3 || cz < b.min.z - 0.3 || cz > b.max.z + 0.3) continue;
        if (!grid[j * cols + i]) free++;
      }
      if (free) traps.push({ tag: b.tag, po: !!b.playerOnly, nn: !!b.noNav, min: [b.min.x, b.min.y, b.min.z].map((v) => +v.toFixed(2)), max: [b.max.x, b.max.y, b.max.z].map((v) => +v.toFixed(2)), free });
    }
    out.traps = traps;
    // 2. ground spawns
    const reach = (p) => {
      const path = nav.findPath(start, p);
      if (!path) return 'nopath';
      const last = path[path.length - 1];
      return Math.hypot(last.x - p.x, last.z - p.z).toFixed(2);
    };
    out.ground = [];
    out.air = [];
    for (const s of G.level.enemySpawns) {
      const p = s.pos;
      if (s.type === 'ground') {
        out.ground.push({ p: [p.x, p.y, p.z].map((v) => +v.toFixed(2)), walk: nav.isWalkable(p.x, p.z), inside: P.overlapsCylinder(p.x, p.z, 0.3, p.y + 0.43, p.y + 1.8), reach: reach(p), dStart: +Math.hypot(p.x - start.x, p.z - start.z).toFixed(1) });
      } else {
        const up = P.raycast(p, new V(0, 1, 0), 30);
        const dn = P.raycast(p, new V(0, -1, 0), 30);
        out.air.push({ p: [p.x, p.y, p.z].map((v) => +v.toFixed(2)), inside: P.overlapsCylinder(p.x, p.z, 0.6, p.y - 0.4, p.y + 0.4), ceil: up ? +up.dist.toFixed(2) : null, floor: dn ? +dn.dist.toFixed(2) : null, gh: P.groundHeight(p.x, p.z) });
      }
    }
    out.cover = [];
    for (const c of G.level.coverPoints) {
      const p = c.pos;
      const w = nav.isWalkable(p.x, p.z);
      const rr = reach(p);
      if (!w || rr === 'nopath' || +rr > 0.6) out.cover.push({ p: [p.x, p.y, p.z].map((v) => +v.toFixed(2)), walk: w, reach: rr });
    }
    out.coverCount = G.level.coverPoints.length;
    out.el = G.level.el;
    out.vantage = G.level.vantage;
    out.bounds = P.bounds;
    out.explosives = (G.explosives.items || []).map((i) => i.box && { min: [i.box.min.x, i.box.min.z], max: [i.box.max.x, i.box.max.z], nn: !!i.box.noNav });
    return out;
  });
  require('fs').writeFileSync('shots/review/enemies-census.json', JSON.stringify(r, null, 1));
  console.log('traps', r.traps.length, 'ground', r.ground.length, 'air', r.air.length, 'badcover', r.cover.length);
};
