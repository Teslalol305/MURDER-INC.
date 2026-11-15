// Scene census: visible meshes, triangles and distinct materials per top-level scene child.
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
    return { rows: rows.slice(0, 40), sceneChildren: G.scene.children.length, info: G.render.stats() };
  });
  for (const r of out.rows) console.log(String(r.meshes).padStart(5), String(r.tris).padStart(8), String(r.mats).padStart(4), String(r.tex).padStart(4), String(r.inst).padStart(3), r.label);
  console.log('scene children', out.sceneChildren, JSON.stringify(out.info).slice(0, 300));
};
