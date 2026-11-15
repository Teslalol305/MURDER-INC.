// Texture census for the material library (CONTRACT 11.2): which textures the visible scene uses,
// grouped by who made them (mats names its textures 'mats:<what>'), with their sizes.
//
//   node build.mjs --dev --out=dist/dev-mats-full.html
//   node tools/shot.cjs dist/dev-mats-full.html --params "autostart=1&q=low&nohud=1&noaudio=1&god=1" \
//        --scenario tools/scenarios/mats-census.cjs --timeout 300
module.exports = async (page, h) => {
  await h.frames(2);
  const out = await h.eval(() => {
    const G = window.__G;
    const seen = new Map(); // uuid -> {name, w, h}
    const SLOTS = ['map', 'normalMap', 'roughnessMap', 'metalnessMap', 'emissiveMap', 'alphaMap', 'aoMap', 'lightMap', 'bumpMap'];
    const note = (t) => {
      if (!t || !t.isTexture || seen.has(t.uuid)) return;
      const img = t.image || {};
      seen.set(t.uuid, { name: t.name || '(unnamed)', w: img.width || 0, h: img.height || 0 });
    };
    const materials = new Set();
    G.scene.traverse((o) => {
      if (!o.material) return;
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
        if (!m || materials.has(m)) continue;
        materials.add(m);
        for (const k of SLOTS) note(m[k]);
        if (m.userData && m.userData.facade) note(m.userData.facade.overlay);
        if (m.uniforms) for (const u of Object.values(m.uniforms)) note(u && u.value);
      }
    });
    const groups = {};
    let mbytes = 0;
    for (const t of seen.values()) {
      const key = t.name.startsWith('mats:') ? t.name.replace(/^mats:/, 'mats ').replace(/:[^:]*$/, (m) => (/(normal|orm|albedo|emissive|overlay)$/.test(m) ? m : '')) : 'other ' + t.name.split(':')[0];
      const g = (groups[key] = groups[key] || { n: 0, px: 0 });
      g.n++;
      g.px += t.w * t.h;
      if (t.name.startsWith('mats:')) mbytes += t.w * t.h * 4 * 1.33;
    }
    const mats = [...seen.values()].filter((t) => t.name.startsWith('mats:')).length;
    return { total: seen.size, mats, matsMB: +(mbytes / 1048576).toFixed(1), materials: materials.size, groups, info: G.renderer.info.memory, stats: G.mats.stats ? G.mats.stats() : null };
  });
  const rows = Object.entries(out.groups).sort((a, b) => b[1].n - a[1].n);
  for (const [k, g] of rows) console.log(String(g.n).padStart(4), String(Math.round(g.px / 1024) + 'k px').padStart(10), k);
  console.log(`scene textures ${out.total} (mats ${out.mats}, ~${out.matsMB} MB with mips), materials ${out.materials}, renderer ${JSON.stringify(out.info)}`);
  console.log(`mats.stats ${JSON.stringify(out.stats)}`);
};
