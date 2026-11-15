// Level material census: what the merged static block draws, grouped by material name.
//   node tools/shot.cjs dist/dev-level.html --params "autostart=1&q=low&god=1" --scenario tools/scenarios/level-census.cjs
'use strict';
module.exports = async (page, h) => {
  await h.frames(2);
  const out = await h.eval(() => {
    const G = window.__G;
    const rows = new Map();
    let meshes = 0;
    G.level.root.getObjectByName('static').traverse((o) => {
      if (!o.isMesh) return;
      meshes++;
      const m = o.material;
      const k = (m.name || m.type) + (m.userData && m.userData.facade ? ' [facade]' : '');
      const r = rows.get(k) || { n: 0, mats: new Set(), tris: 0, cast: 0 };
      r.n++;
      r.mats.add(m.uuid);
      r.cast += o.castShadow ? 1 : 0;
      r.tris += (o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count) / 3;
      rows.set(k, r);
    });
    const list = [...rows].map(([k, r]) => ({ k, n: r.n, mats: r.mats.size, tris: Math.round(r.tris), cast: r.cast })).sort((a, b) => b.mats - a.mats || b.n - a.n);
    const dyn = {};
    for (const c of G.level.root.getObjectByName('dynamic').children) {
      let n = 0;
      c.traverse((o) => { if (o.isMesh && o.visible) n++; });
      dyn[c.name] = (dyn[c.name] || 0) + n;
    }
    return { meshes, list, dyn, stats: G.level.stats, mats: G.mats.stats ? G.mats.stats() : null };
  });
  console.log('static meshes', out.meshes, JSON.stringify(out.stats));
  for (const r of out.list) console.log(String(r.n).padStart(4), String(r.mats).padStart(4), String(r.tris).padStart(7), String(r.cast).padStart(3), r.k);
  console.log('dynamic', JSON.stringify(out.dyn));
  console.log(JSON.stringify(out.mats).slice(0, 600));
};
