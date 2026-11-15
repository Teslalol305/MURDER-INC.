// Material gallery: every catalogue material, sign style, poster, tag and decal in one small scene,
// photographed from fixed viewpoints. The gallery stands 200 m south of the block, on its own floor.
//
//   node build.mjs --dev --only=mats --out=dist/dev-mats.html
//   node tools/shot.cjs dist/dev-mats.html --params "autostart=1&q=low&god=1&nohud=1&noaudio=1" \
//        --scenario tools/scenarios/mats-gallery.cjs --timeout 600
//
// Software WebGL is slow and memory-hungry, so a run can be narrowed:
//   MATS_VIEWS=brick,signs1      only these views (see VIEWS below)
//   MATS_PARTS=ground,walls      only these parts of the gallery: ground, walls, spheres, signs, paper,
//                                decals, facades, fence, steel (default: whatever the views need)
//   MATS_OUT=shots/mats          output folder

const OUT = process.env.MATS_OUT || 'shots/mats';

/** Runs in the page: builds the named parts of the gallery and returns what it made. */
function buildGallery(parts) {
  const want = (part) => parts.includes(part);
  const G = window.__G;
  const { THREE, mats, scene } = G;
  const Z0 = 200; // gallery origin on the z axis
  const root = new THREE.Group();
  root.name = 'mats-gallery';
  root.position.set(0, 0, Z0);
  scene.add(root);

  // --- geometry with UVs in metres (what core/geo.js gives the real modules) ---
  const scaleUv = (geo, fn) => {
    const uv = geo.getAttribute('uv');
    for (let i = 0; i < uv.count; i++) {
      const [su, sv] = fn(i);
      uv.setXY(i, uv.getX(i) * su, uv.getY(i) * sv);
    }
    return geo;
  };
  const plane = (w, h) => scaleUv(new THREE.PlaneGeometry(w, h), () => [w, h]);
  const box = (w, h, d) =>
    scaleUv(new THREE.BoxGeometry(w, h, d), (i) => {
      const face = Math.floor(i / 4); // +x −x +y −y +z −z
      return face < 2 ? [d, h] : face < 4 ? [w, d] : [w, h];
    });
  const sphere = (r) => scaleUv(new THREE.SphereGeometry(r, 32, 16), () => [Math.PI * 2 * r, Math.PI * r]);

  const add = (geo, material, x, y, z, rx = 0, ry = 0) => {
    const mesh = new THREE.Mesh(geo, material);
    mesh.position.set(x, y, z);
    mesh.rotation.set(rx, ry, 0);
    mesh.receiveShadow = true;
    root.add(mesh);
    return mesh;
  };
  const floor = (name, x0, x1, z0, z1, lift = 0) => add(plane(x1 - x0, z1 - z0), mats.get(name), (x0 + x1) / 2, lift, (z0 + z1) / 2, -Math.PI / 2);
  /**
   * The quad for a {material, w, h} item (CONTRACT 6.1): UVs 0 … 1 across it, except along a direction
   * in which its texture repeats, which keeps metre UVs (road paint), so w and h may then be anything.
   */
  const quadFor = (item, w = item.w, h = item.h) => {
    const map = item.material.map;
    const metres = (wrap) => wrap === THREE.RepeatWrapping;
    return scaleUv(new THREE.PlaneGeometry(w, h), () => [metres(map.wrapS) ? w : 1, metres(map.wrapT) ? h : 1]);
  };
  /** An item on a wall that faces +z (ry = 0) or −z (ry = π). */
  const onWall = (item, x, y, z, ry = 0) => add(quadFor(item), item.material, x, y, z, 0, ry);
  /** An item lying on the ground, its v axis pointing north. */
  const onGround = (item, x, z, lift = 0.02) => add(quadFor(item), item.material, x, lift, z, -Math.PI / 2);
  const gauge = (w, h, d, x, y, z) => add(new THREE.BoxGeometry(w, h, d), mats.emissive(0xf6c21a, 1.2), x, y, z);

  const WALL_Z = -8;
  const wallFace = WALL_Z + 0.01;
  const panelX = (i) => -32 + 2 + i * 4;

  // --- ground: asphalt, a sidewalk with its kerb, some patches ---
  if (want('ground')) {
    floor('asphalt', -32, 32, -4, 16);
    floor('sidewalk', -32, 32, -8, -4, 0.15);
    add(box(64, 0.15, 0.2), mats.get('curb'), 0, 0.075, -3.9);
    floor('court', 20, 30, 9, 15, 0.01);
    floor('dirt', -30, -20, 9, 15, 0.01);
    floor('concrete_dark', -18, -10, 10, 15, 0.01);
    floor('asphalt_wet', -8, -2, 11, 15, 0.01);
    // scale gauges: a sidewalk flag (1.5 m) and a lane line (0.12 m)
    gauge(1.5, 0.01, 0.02, -0.75, 0.16, -5.5);
    gauge(0.02, 0.01, 0.12, -19.4, 0.03, 6);
  }

  // --- back wall: one 4 m panel per wall material ---
  if (want('walls')) {
    const panels = ['brick_red', 'brick_brown', 'brick_tan', 'brick_painted', 'cinder', 'concrete', 'concrete_dark', 'stucco', 'tile_white', 'roll_gate', 'corrugated', 'plywood', 'wood', 'steel_rust', 'metal_galv', 'cardboard'];
    panels.forEach((name, i) => add(box(4, 4.5, 0.3), mats.get(name), panelX(i), 0.15 + 2.25, WALL_Z - 0.15));
    // scale gauge: one brick (0.2 m × 67 mm) on the first panel
    gauge(0.2, 0.01, 0.01, panelX(0) - 1.2, 1.5, wallFace + 0.02);
    gauge(0.01, 0.0667, 0.01, panelX(0) - 1.32, 1.5, wallFace + 0.02);
  }

  // --- one sphere and one cube per catalogue material ---
  const names = mats.names();
  if (want('spheres')) {
    names.forEach((name, i) => {
      const x = -17.5 + Math.floor(i / 2) * 1.4;
      const z = i % 2 ? 2.2 : 0;
      add(sphere(0.42), mats.get(name), x, 0.42, z);
      add(box(0.5, 0.5, 0.5), mats.get(name), x + 0.62, 0.25, z + 0.35, 0, 0.5);
    });
    // tinted variants
    [0x1d2a4a, 0xf2c21a, 0x14301f, 0xd8d6cf].forEach((color, i) => add(sphere(0.42), mats.get('car_paint', { color }), -17.5 + i * 1.4, 0.42, 4.4));
    [0x1f5a3a, 0x1f4f9a, 0xc9a227].forEach((color, i) => add(sphere(0.42), mats.get('fabric_awning', { color }), -11 + i * 1.4, 0.42, 4.4));
    [0x7a2a8a, 0x2aa0a0].forEach((color, i) => add(sphere(0.42), mats.get('paint_white', { color }), -6 + i * 1.4, 0.42, 4.4));
  }

  // --- signs: every style, in rows across the wall ---
  if (want('signs')) {
    const storefronts = G.config.text.world.storefronts;
    const signs = [
      { text: storefronts[0], w: 7.6, h: 0.9, style: 'neon', fg: 0x35e0ff },
      { text: 'OPEN', sub: '24 HRS', w: 1.6, h: 0.9, style: 'neon', fg: 0xff3030, glow: 0x55ff8a },
      { text: G.config.text.world.shop, w: 7.6, h: 1.1, style: 'box', bg: 0x101113, fg: 0xf6c21a },
      { text: storefronts[5], sub: 'COLD BEER · LOTTO', w: 5.6, h: 1.0, style: 'box' },
      { text: storefronts[2], sub: 'WE BUY · WE LOAN', w: 5.6, h: 0.9, style: 'painted' },
      { text: storefronts[1], w: 5.6, h: 0.8, style: 'painted', bg: 0x1b3565, fg: 0xf2c21a, lit: true },
      { text: storefronts[4], w: 3.8, h: 0.6, style: 'awning' },
      { text: storefronts[6], sub: 'WALK-INS WELCOME', w: 3.8, h: 0.7, style: 'awning', bg: 0x1f6b6b },
      { text: 'Jamaica', sub: 'Av', w: 1.1, h: 0.24, style: 'street' },
      { text: '205', sub: 'St', w: 0.8, h: 0.24, style: 'street' },
      { text: 'NO PARKING', sub: 'LOADING ZONE', w: 2.4, h: 0.9, style: 'stencil', fg: 0xf2c21a },
      { text: 'KEEP CLEAR', w: 2.4, h: 0.5, style: 'stencil' },
      { text: 'Jamaica Av', sub: 'Hollis · Queens', w: 2.6, h: 0.6, style: 'plate', bullet: '1', bulletColor: 0xe2222b },
      { text: 'Downtown & Brooklyn', w: 3.2, h: 0.5, style: 'plate', bullet: 'J', bulletColor: 0x9a6a2a },
      { text: 'IPX', sub: 'IPX.EXCHANGE', w: 2.6, h: 1.0, style: 'plate', lit: false },
      { text: 'IPX', w: 1.6, h: 0.7, style: 'neon', fg: 0xf6c21a },
      { text: 'IPX', w: 1.8, h: 0.6, style: 'box', bg: 0xf6c21a, fg: 0x0d0e11 },
      { text: storefronts[9], w: 3.6, h: 0.7, style: 'neon', fg: 0xff3d9a },
    ];
    let sx = -31.5;
    let row = 0;
    for (const spec of signs) {
      if (sx + spec.w > 31.5) {
        sx = -31.5;
        row++;
      }
      onWall(mats.sign(spec), sx + spec.w / 2, 4.0 - row * 1.25, wallFace + 0.02);
      sx += spec.w + 0.4;
    }
  }

  // --- posters and graffiti along the foot of the wall ---
  if (want('paper')) {
    let px = -31.3;
    for (const kind of ['ipx', 'show', 'wanted', 'ad', 'torn']) {
      for (let v = 0; v < 4; v++) {
        if ((kind === 'wanted' || kind === 'torn') && v > 2) continue;
        const p = mats.poster(kind, v);
        onWall(p, px + p.w / 2, 0.35 + p.h / 2, wallFace + 0.01);
        px += p.w + 0.12;
      }
    }
    const tags = [['RULE', 2], ['VULTURES', 0, 0xe2222b], ['HOLLIS', 1], ['IPX', 1, 0xf6c21a], ['QNS', 2, 0x39d0e0], ['205', 0], ['JA', 1, 0xf4f2ec], ['KINGS', 2, 0xff3d9a], ['INC', 0, 0x55ff8a]];
    let gx = px + 0.4;
    for (const [text, seed, color] of tags) {
      const g = mats.graffiti(text, seed, color);
      onWall(g, gx + g.w / 2, 0.5 + g.h / 2, wallFace + 0.012);
      gx += g.w + 0.15;
    }
  }

  // --- decals on the asphalt ---
  if (want('decals')) {
    const lane = mats.decal('lane');
    add(quadFor(lane, 40, lane.w), lane.material, 0, 0.02, 6, -Math.PI / 2); // one long line: the paint tiles
    const yellow = mats.decal('lane_yellow');
    for (let x = -18; x <= 18; x += 6) add(quadFor(yellow, yellow.h, yellow.w), yellow.material, x, 0.02, 6.4, -Math.PI / 2);
    const cross = mats.decal('crosswalk');
    add(quadFor(cross, 10, cross.h), cross.material, 12, 0.02, 9.5, -Math.PI / 2); // 10 m of crossing from one 4 m painting
    onGround(mats.decal('arrow'), 4, 9.5);
    let dx = -17;
    for (const kind of ['oil', 'crack', 'manhole', 'grime', 'scorch', 'puddle']) {
      for (let v = 0; v < 2; v++) {
        const d = mats.decal(kind, v);
        onGround(d, dx + d.w / 2, 8.2 + (v ? 1.9 : 0), 0.02 + v * 0.001);
        if (v === 1) dx += d.w + 0.3;
      }
    }
    for (let v = 0; v < 3; v++) onWall(mats.decal('bullet', v), panelX(5) - 0.6 + v * 0.5, 2.6, wallFace + 0.01);
  }

  // --- facades, facing north across the street ---
  if (want('facades')) {
    const facades = [
      { base: 'brick_red', floors: 4, bays: 6, floorH: 3.2, lit: 0.35, seed: 3, shopfront: true, x: -19 },
      { base: 'brick_tan', floors: 5, bays: 5, floorH: 3, lit: 0.2, seed: 8, shopfront: false, w: 16, x: 0 },
      { base: 'brick_brown', floors: 3, bays: 5, floorH: 3.4, lit: 0.5, seed: 21, shopfront: true, x: 17 },
      { base: 'brick_painted', floors: 2, bays: 3, floorH: 3.2, lit: 0.34, seed: 5, shopfront: false, x: 30.5 },
    ];
    for (const f of facades) {
      const material = mats.facade(f);
      const { w, h } = material.userData.facade || { w: f.bays * 3, h: f.floors * f.floorH };
      add(plane(w, h + 1.2), material, f.x, (h + 1.2) / 2, 16, 0, Math.PI); // 1.2 m of parapet above the top floor
    }
  }

  // --- chain-link, El steel ---
  if (want('fence')) {
    const fence = mats.get('chainlink');
    for (let i = 0; i < 4; i++) add(plane(3, 2.4), fence, 20 + i * 3, 1.2, 5);
    add(plane(12, 4), fence, 26, 2, -2, 0, -Math.PI / 2);
  }
  if (want('steel')) {
    for (const x of [-12, 12]) add(box(0.6, 6.5, 0.6), mats.get('steel_el'), x, 3.25, 3.6);
    add(box(24.6, 0.7, 0.5), mats.get('steel_el'), 0, 6.15, 3.6);
  }

  // --- lamps: sodium overhead, neon at the shop fronts (pooled lights: adding lights after boot
  //     would recompile every program) ---
  const lamp = (color, intensity, range, x, y, z) => {
    const held = G.render.lights.acquire();
    if (held) {
      held.light.color.set(color);
      held.light.intensity = intensity;
      held.light.distance = range;
      held.light.position.set(x, y, z + Z0);
    }
    add(new THREE.SphereGeometry(0.08, 8, 6), mats.emissive(color, 5), x, y, z);
  };
  lamp(0xffb45e, 90, 22, -6, 5.6, 3);
  lamp(0xffb45e, 90, 22, 14, 5.6, 3);
  lamp(0xff3d9a, 40, 14, 4, 2.6, -6.6);
  lamp(0x35e0ff, 40, 14, -20, 2.6, -6.6);

  return { parts, stats: mats.stats() };
}

/** name → [camera position, look-at (relative to the gallery origin), field of view, parts it needs]. */
const VIEWS = {
  overview: [[0, 11, 17], [0, 1, -3], 62, 'ground walls spheres signs paper decals fence steel'],
  walls1: [[-24, 1.7, 1], [-24, 2.1, -8], 74, 'ground walls'],
  walls2: [[-8, 1.7, 1], [-8, 2.1, -8], 74, 'ground walls'],
  walls3: [[8, 1.7, 1], [8, 2.1, -8], 74, 'ground walls'],
  walls4: [[24, 1.7, 1], [24, 2.1, -8], 74, 'ground walls'],
  brick: [[-31.2, 1.5, -6.9], [-31.2, 1.5, -8], 60, 'walls'],
  sidewalk: [[-0.75, 2.6, -5.2], [-0.75, 0, -6.2], 70, 'ground'],
  asphalt: [[-14, 1.6, 12], [-4, 0.2, 0], 74, 'ground'],
  street: [[-30, 1.7, 2], [20, 0.5, 4], 70, 'ground steel'],
  lane: [[-19.4, 0.7, 6.7], [-19.4, 0, 6], 50, 'ground decals'],
  spheres1: [[-12.5, 2.2, 6.6], [-12.5, 0.4, 1.4], 62, 'ground spheres'],
  spheres2: [[-3.5, 2.2, 6.6], [-3.5, 0.4, 1.4], 62, 'ground spheres'],
  spheres3: [[5.5, 2.2, 6.6], [5.5, 0.4, 1.4], 62, 'ground spheres'],
  spheres4: [[14, 2.2, 6.6], [14, 0.4, 1.4], 62, 'ground spheres'],
  signs1: [[-24, 2.6, -1.5], [-24, 3.1, -8], 70, 'walls signs'],
  signs2: [[-8, 2.6, -1.5], [-8, 3.1, -8], 70, 'walls signs'],
  signs3: [[8, 2.6, -1.5], [8, 3.1, -8], 70, 'walls signs'],
  signs4: [[24, 2.6, -1.5], [24, 3.1, -8], 70, 'walls signs'],
  paper1: [[-28.5, 1.3, -5.2], [-28.5, 1.1, -8], 62, 'ground walls paper'],
  paper2: [[-23, 1.3, -5.2], [-23, 1.1, -8], 62, 'ground walls paper'],
  paper3: [[-16.5, 1.2, -4.8], [-16.5, 1.0, -8], 62, 'ground walls paper'],
  paper4: [[-10, 1.2, -4.8], [-10, 1.0, -8], 62, 'ground walls paper'],
  decals: [[-6, 7.5, 15.5], [-6, 0, 8], 62, 'ground decals'],
  road: [[12, 4.5, 14.5], [10, 0, 8.5], 62, 'ground decals'],
  facade1: [[-12, 1.7, -2], [-12, 7.5, 16], 74, 'ground facades'],
  facade2: [[14, 1.7, -2], [14, 6.5, 16], 74, 'ground facades'],
  facade3: [[-19, 1.6, 12.6], [-21, 1.8, 16], 62, 'ground facades'],
  fence: [[24, 1.6, 9.5], [22, 1.1, 0], 62, 'ground fence spheres'],
  fencefar: [[24, 1.7, 34], [24, 1.2, 5], 40, 'ground fence'],
  steel: [[-11.2, 1.6, 6.2], [-12, 2.2, 3.6], 60, 'ground steel'],
};

const list = (value) => (value || '').split(/[\s,]+/).filter(Boolean);

/** The parts the given views need (or MATS_PARTS when it is set). */
const partsFor = (names) => (list(process.env.MATS_PARTS).length ? list(process.env.MATS_PARTS) : [...new Set(names.flatMap((name) => list(VIEWS[name][3])))]);

module.exports = async (page, h) => {
  const names = list(process.env.MATS_VIEWS).length ? list(process.env.MATS_VIEWS) : Object.keys(VIEWS);
  for (const name of names) if (!VIEWS[name]) throw new Error(`mats-gallery: no view called '${name}'`);
  const parts = partsFor(names);

  const built = await h.eval(buildGallery, parts);
  console.error(`gallery: ${JSON.stringify(built)}`);
  // The first frame compiles programs and uploads textures: give it its own step and say so.
  await h.frames(1);
  console.error('gallery: first frame drawn');
  for (const name of names) {
    const [[x, y, z], [lx, ly, lz], fov] = VIEWS[name];
    await h.eval((shot) => window.__setShot(shot), { cam: [x, y, z + 200, lx, ly, lz + 200].join(','), fov });
    await h.frames(2);
    await h.shot(`${OUT}/gallery-${name}.png`);
    console.error(`gallery: ${name}`);
  }

  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
  const stats = await h.stats();
  console.error(`gallery: ${stats.programs} programs, ${stats.textures} textures, ${stats.calls} draw calls`);
};

// tools/scenarios/mats-view.cjs shows the same gallery in a bare three.js page.
module.exports.buildGallery = buildGallery;
module.exports.VIEWS = VIEWS;
module.exports.partsFor = partsFor;
module.exports.list = list;
