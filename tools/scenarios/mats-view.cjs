#!/usr/bin/env node
// The material gallery (tools/scenarios/mats-gallery.cjs) in a bare three.js page: the real mats module
// and its shader patches, the game's key / ambient / fog numbers and a small environment map, but no
// game, no level and no post chain. It starts in a second or two, so it is the quick way to look at a
// material in 3D; the full harness run remains the reference (bloom, the real light rig).
// A standalone script, not a shot.cjs scenario.
//
//   node tools/scenarios/mats-view.cjs brick asphalt signs1          views by name (default: all)
//   node tools/scenarios/mats-view.cjs --tex 1024 --size 1280x720 facade1
//   MATS_PARTS=ground,walls node tools/scenarios/mats-view.cjs walls1
//
// Output: shots/mats/view-<name>.png. Exits 1 on any console error (a shader that does not compile).

'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { build } = require('esbuild');
const gallery = require('./mats-gallery.cjs');

const ROOT = path.resolve(__dirname, '..', '..');
const OUT = path.join(ROOT, process.env.MATS_OUT || path.join('shots', 'mats'));
const GL_ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];

const ENTRY = `
import * as THREE from 'three';
import * as brand from './src/config/brand.js';
import * as catalog from './src/config/catalog.js';
import * as look from './src/config/look.js';
import * as text from './src/config/text.js';
import { createMats } from './src/mats.js';

window.startViewer = async ({ width, height, tex, shadows, params }) => {
  const canvas = document.createElement('canvas');
  document.body.appendChild(canvas);
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(width, height, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = look.grade.exposure;
  renderer.shadowMap.enabled = shadows;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.debug.onShaderError = (gl, program, vs, fs) => {
    console.error('shader error: ' + [gl.getProgramInfoLog(program), gl.getShaderInfoLog(vs), gl.getShaderInfoLog(fs)].filter(Boolean).join(' | ').slice(0, 600));
  };

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(look.sky.zenith);
  scene.fog = new THREE.FogExp2(look.fog.color, look.fog.density);
  scene.add(new THREE.HemisphereLight(look.ambient.sky, look.ambient.ground, look.ambient.intensity));
  const sun = new THREE.DirectionalLight(look.sun.color, look.sun.intensity);
  const dir = new THREE.Vector3().fromArray(look.sun.direction).normalize();
  sun.target.position.set(0, 0, 204);
  sun.position.copy(sun.target.position).addScaledVector(dir, -60);
  sun.castShadow = shadows;
  sun.shadow.mapSize.set(1024, 1024);
  Object.assign(sun.shadow.camera, { left: -40, right: 40, top: 30, bottom: -30, near: 1, far: 140 });
  sun.shadow.bias = look.sun.shadowBias;
  sun.shadow.normalBias = look.sun.shadowNormalBias;
  scene.add(sun, sun.target);

  // The six pooled point lights of the real renderer.
  const pool = [];
  for (let i = 0; i < 6; i++) {
    const light = new THREE.PointLight(0xffc880, 0, 10, 2);
    scene.add(light);
    pool.push(light);
  }
  let held = 0;

  // The same stand-in environment the stub atmosphere builds: a night gradient with a few lamps.
  {
    const env = new THREE.Scene();
    const dome = new THREE.SphereGeometry(40, 24, 12);
    const top = new THREE.Color(look.sky.zenith).multiplyScalar(2);
    const rim = new THREE.Color(look.sky.glow).multiplyScalar(1.6);
    const floor = new THREE.Color(look.ambient.ground).multiplyScalar(0.35);
    const colors = new Float32Array(dome.attributes.position.count * 3);
    const tint = new THREE.Color();
    for (let i = 0; i < colors.length / 3; i++) {
      const h = dome.attributes.position.getY(i) / 40;
      if (h >= 0) tint.lerpColors(rim, top, Math.min(1, h * 2.5));
      else tint.lerpColors(rim, floor, Math.min(1, -h * 6));
      tint.toArray(colors, i * 3);
    }
    dome.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    env.add(new THREE.Mesh(dome, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide })));
    const lamp = new THREE.MeshBasicMaterial({ color: new THREE.Color(look.palette.sodium).multiplyScalar(18) });
    for (const [x, y, z] of [[14, 22, 6], [-16, 20, -10], [-4, 24, 18], [20, 18, -18]]) {
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(5, 0.5, 5), lamp);
      mesh.position.set(x, y, z);
      env.add(mesh);
    }
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(env, 0.03).texture;
    pmrem.dispose();
  }

  const camera = new THREE.PerspectiveCamera(74, width / height, 0.08, 700);
  const G = {
    THREE,
    params: { tex: String(tex), ...params },
    events: { on() {} },
    time: { t: 0, dt: 0 },
    quality: { name: 'high' },
    config: { brand, catalog, look, text },
    renderer,
    scene,
    camera,
    render: { lights: { acquire: () => (held < 4 ? { light: pool[held++], release() {} } : null) } },
  };
  window.__G = G;
  G.mats = await createMats(G);

  window.viewerShot = (cam, target, fov) => {
    camera.position.fromArray(cam);
    camera.lookAt(target[0], target[1], target[2]);
    camera.fov = fov;
    camera.updateProjectionMatrix();
    G.time.t += 1 / 30;
    G.mats.update(1 / 30);
    renderer.render(scene, camera);
    return canvas.toDataURL('image/png');
  };
  window.viewerStats = () => ({ programs: renderer.info.programs.length, textures: renderer.info.memory.textures, calls: renderer.info.render.calls, triangles: renderer.info.render.triangles, mats: G.mats.stats() });
};
`;

async function main() {
  const args = process.argv.slice(2);
  const opts = { tex: 512, width: 960, height: 540, shadows: true, params: {}, views: [] };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--tex') opts.tex = Number(args[++i]);
    else if (args[i] === '--size') [opts.width, opts.height] = args[++i].split('x').map(Number);
    else if (args[i] === '--no-shadows') opts.shadows = false;
    else if (args[i] === '--params') opts.params = Object.fromEntries(new URLSearchParams(args[++i]));
    else opts.views.push(args[i]);
  }
  const names = opts.views.length ? opts.views : Object.keys(gallery.VIEWS);
  for (const name of names) if (!gallery.VIEWS[name]) throw new Error(`no view called '${name}' (${Object.keys(gallery.VIEWS).join(', ')})`);

  const bundle = await build({ stdin: { contents: ENTRY, resolveDir: ROOT, loader: 'js' }, bundle: true, format: 'iife', write: false, logLevel: 'warning' });
  const { chromium } = require('playwright');
  const browser = await chromium.launch({ args: GL_ARGS });
  const problems = [];
  try {
    const page = await browser.newPage({ viewport: { width: opts.width, height: opts.height } });
    page.on('console', (msg) => {
      if (msg.type() === 'error') problems.push(msg.text());
      if (msg.type() === 'error' || (msg.type() === 'warning' && !/KHR_parallel_shader_compile/.test(msg.text()))) console.error(`[page ${msg.type()}] ${msg.text()}`);
    });
    page.on('pageerror', (err) => problems.push(err.message));
    await page.setContent('<!doctype html><html><body style="margin:0;background:#000"></body></html>');
    await page.addScriptTag({ content: bundle.outputFiles[0].text });
    const t0 = Date.now();
    await page.evaluate((o) => window.startViewer(o), { width: opts.width, height: opts.height, tex: opts.tex, shadows: opts.shadows, params: opts.params });
    const built = await page.evaluate(([fn, parts]) => (0, eval)(`(${fn})`)(parts), [gallery.buildGallery.toString(), gallery.partsFor(names)]);
    console.log(`built ${JSON.stringify(built)} in ${Date.now() - t0} ms`);
    fs.mkdirSync(OUT, { recursive: true });
    for (const name of names) {
      const [[x, y, z], [lx, ly, lz], fov] = gallery.VIEWS[name];
      const url = await page.evaluate(([cam, target, f]) => window.viewerShot(cam, target, f), [[x, y, z + 200], [lx, ly, lz + 200], fov]);
      const file = path.join(OUT, `view-${name}.png`);
      fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
      console.log(path.relative(ROOT, file));
    }
    console.log(JSON.stringify(await page.evaluate(() => window.viewerStats())));
  } finally {
    await browser.close();
  }
  if (problems.length) {
    console.error(`${problems.length} page error(s); first: ${problems[0].slice(0, 400)}`);
    process.exitCode = 1;
  }
}

main().catch((err) => {
  console.error(`mats-view: ${err.stack || err.message}`);
  process.exitCode = 1;
});
