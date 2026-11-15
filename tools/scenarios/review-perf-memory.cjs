// Review (perf): CPU-side texture memory kept alive after upload (canvases, ImageData, DataTextures) and GPU estimate.
// node tools/shot.cjs dist/dev-all.html --params "autostart=1&q=low&god=1&noaudio=1" --size 640x360 --scenario tools/scenarios/review-perf-memory.cjs
module.exports = async (page, h) => {
  await h.frames(2);
  const out = await h.eval(() => {
    const G = window.__G;
    const texs = new Map();
    const visit = (root) => root.traverse((o) => {
      const ms = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
      for (const m of ms) for (const k in m) { const v = m[k]; if (v && v.isTexture) texs.set(v.uuid, v); }
      if (o.material && o.material.uniforms) for (const k in o.material.uniforms) { const v = o.material.uniforms[k].value; if (v && v.isTexture) texs.set(v.uuid, v); }
    });
    visit(G.scene); visit(G.vmScene);
    if (G.scene.environment) texs.set(G.scene.environment.uuid, G.scene.environment);
    const rows = []; let cpu = 0, gpu = 0;
    const kinds = {};
    for (const t of texs.values()) {
      const img = t.image; let w = 0, hh = 0, kind = 'none', bytes = 0;
      if (img) {
        w = img.width || 0; hh = img.height || 0;
        kind = img instanceof HTMLCanvasElement ? 'canvas' : (typeof OffscreenCanvas !== 'undefined' && img instanceof OffscreenCanvas) ? 'offscreen' : img instanceof ImageData ? 'imagedata' : img.data ? 'data:' + img.data.constructor.name : img.constructor ? img.constructor.name : 'obj';
        bytes = img.data ? img.data.byteLength : w * hh * 4;
        if (t.isDataArrayTexture || t.isData3DTexture) bytes = img.data ? img.data.byteLength : 0;
      }
      if (t.isRenderTargetTexture || t.isCubeTexture) kind += t.isCubeTexture ? ':cube' : ':rt';
      const g = w * hh * 4 * (t.generateMipmaps !== false && t.minFilter !== 1006 && t.minFilter !== 1003 ? 1.33 : 1);
      cpu += bytes; gpu += g;
      kinds[kind] = kinds[kind] || { n: 0, mb: 0 }; kinds[kind].n++; kinds[kind].mb += bytes / 1048576;
      rows.push({ name: t.name || '', w, h: hh, kind, mb: +(bytes / 1048576).toFixed(2) });
    }
    rows.sort((a, b) => b.mb - a.mb);
    // all canvases alive in the document (attached ones) plus a rough count
    const canv = document.querySelectorAll('canvas').length;
    return { n: texs.size, cpuMB: +(cpu / 1048576).toFixed(1), gpuMB: +(gpu / 1048576).toFixed(1), kinds, top: rows.slice(0, 30), canv, heapMB: +(performance.memory.usedJSHeapSize / 1048576).toFixed(1), info: G.renderer.info.memory };
  });
  console.log(JSON.stringify({ n: out.n, cpuMB: out.cpuMB, gpuMB: out.gpuMB, kinds: out.kinds, domCanvases: out.canv, heapMB: out.heapMB, info: out.info }));
  for (const r of out.top) console.log(String(r.mb).padStart(7), `${r.w}x${r.h}`.padStart(10), r.kind.padEnd(16), r.name);
};
