// Scene census: visible meshes, triangles and distinct materials per top-level scene child, the shadow
// casters per material, and the frame cost. The sun's shadow map is redrawn every `shadowEvery` frames,
// so two consecutive frames are measured and the larger one is the frame the budget is judged on.
//
//   node tools/shot.cjs dist/dev-you.html --params "autostart=1&q=low&god=1&noaudio=1" --scenario tools/scenarios/census.cjs
module.exports = async (page, h) => {
  await h.frames(3);
  const out = await h.eval(() => {
    const G = window.__G, rows = [];
    const census = (root, label) => {
      let meshes = 0, tris = 0, inst = 0; const mats = new Set(), tex = new Set();
      root.traverse(o => {
        if (!o.visible) return;
        if (o.isMesh || o.isPoints || o.isLine) {
          meshes++;
          const g = o.geometry; const n = g.index ? g.index.count : (g.attributes.position ? g.attributes.position.count : 0);
          tris += (n / 3) * (o.isInstancedMesh ? o.count : 1); if (o.isInstancedMesh) inst++;
          const ms = Array.isArray(o.material) ? o.material : [o.material];
          for (const m of ms) { if (!m) continue; mats.add(m.uuid); for (const k of ['map','normalMap','roughnessMap','emissiveMap','alphaMap','metalnessMap']) if (m[k]) tex.add(m[k].uuid); }
        }
      });
      rows.push({ label, meshes, tris: Math.round(tris), mats: mats.size, tex: tex.size, inst });
    };
    for (const c of G.scene.children) census(c, (c.name || c.type) + (c.userData && c.userData.owner ? ':' + c.userData.owner : ''));
    if (G.level && G.level.root) for (const c of G.level.root.children) census(c, 'level.root/' + (c.name || c.type));
    rows.sort((a, b) => b.meshes - a.meshes);
    // Shadow casters by mesh name (the level's merged meshes are named by material).
    const casters = new Map();
    let casting = 0;
    G.scene.traverseVisible((o) => {
      if (!(o.isMesh && o.castShadow)) return;
      const g = o.geometry; const n = (g.index ? g.index.count : g.attributes.position.count) / 3 * (o.isInstancedMesh ? o.count : 1);
      casting += n;
      const k = o.name || (o.parent && o.parent.name) || o.type;
      casters.set(k, (casters.get(k) || 0) + n);
    });
    const top = [...casters.entries()].sort((a, b) => b[1] - a[1]).slice(0, 15).map(([k, v]) => [k, Math.round(v)]);
    return { rows: rows.slice(0, 40), sceneChildren: G.scene.children.length, info: G.render.stats(), casting: Math.round(casting), top, sunless: G.level && G.level.stats ? G.level.stats.sunless : undefined };
  });
  for (const r of out.rows) console.log(String(r.meshes).padStart(5), String(r.tris).padStart(8), String(r.mats).padStart(4), String(r.tex).padStart(4), String(r.inst).padStart(3), r.label);
  console.log('scene children', out.sceneChildren, JSON.stringify(out.info).slice(0, 300));
  console.log('shadow casters', out.casting, 'triangles; level props that never see the sun:', out.sunless);
  for (const [k, v] of out.top) console.log(String(v).padStart(8), k);
  // Two consecutive frames: one of them redraws the shadow map.
  const frames = [];
  for (let i = 0; i < 2; i++) {
    await h.frames(1);
    const s = await h.stats();
    frames.push({ calls: s.calls, triangles: s.triangles });
  }
  const worst = { calls: Math.max(...frames.map((f) => f.calls)), triangles: Math.max(...frames.map((f) => f.triangles)) };
  console.log('frames', JSON.stringify(frames), 'worst', JSON.stringify(worst));
};
