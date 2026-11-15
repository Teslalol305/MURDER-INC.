// Prop gallery: every catalogue prop on a grid with its name on the ground, a 1.8 m reference post, and
// (in the collider pass) its colliders as green wireframes. Written to shots/props/.
//
//   node build.mjs --dev --only=props --out=dist/dev-props.html
//   node tools/shot.cjs dist/dev-props.html --params "autostart=1&god=1&q=low&nohud=1&noaudio=1" --timeout 900 \
//        --scenario tools/scenarios/props-gallery.cjs
//
// Environment:
//   PROPS_ONLY=sedan,taxi       only these props (default: the whole catalogue plus the variants below)
//   PROPS_VIEWS=front,eye,back,colliders,top,each   which passes to shoot (default: front,eye,colliders);
//                               `each` = four close-ups of every prop on its own
//   PROPS_OUT=shots/props/x     output directory
//   PROPS_EXPOSURE=1.4          exposure multiplier (the block is lit for 2 AM; raise it to inspect)
//   PROPS_STATE=open            setState() to apply to every stateful prop before shooting
//
// The run fails if any prop fell back to a plain box or left the catalogue box by more than 3 cm
// (door leaves, arms and crowns that are meant to overhang are listed in OVERHANG).

const path = require('node:path');

const OUT = process.env.PROPS_OUT || 'shots/props';
const ONLY = process.env.PROPS_ONLY ? process.env.PROPS_ONLY.split(',').map((s) => s.trim()).filter(Boolean) : null;
const VIEWS = (process.env.PROPS_VIEWS || 'front,eye,colliders').split(',').map((s) => s.trim());
const EXPOSURE = Number(process.env.PROPS_EXPOSURE || 1.25);
const STATE = process.env.PROPS_STATE || '';

// Extra entries beside the plain catalogue names: "label" → [name, opts].
const VARIANTS = {
  'sedan lit': ['sedan', { seed: 1, lit: true, color: 0x8f959c }],
  'van vulture': ['van', { variant: 'vulture' }],
  'car_lift car': ['car_lift', { variant: 'car' }],
  'fence_tall scrim': ['fence_tall', { variant: 'scrim' }],
  'shopping_cart tipped': ['shopping_cart', { variant: 'tipped' }],
  'awning text': ['awning', { text: 'PAWN & GOLD', color: 0x1f5a3a }],
  'fire_escape top': ['fire_escape', { variant: 'top' }],
  'sign_post street': ['sign_post', { variant: 'street', text: 'JAMAICA AV' }],
  'street_lamp off': ['street_lamp', { on: false }],
};

// Props that reach outside their catalogue footprint on purpose.
const OVERHANG = new Set([
  'van vulture', 'street_lamp', 'street_lamp off', 'traffic_light', 'tree', 'court_light', 'hydrant_open', 'master_case',
  'fire_escape', 'fire_escape top', 'shopping_cart tipped',
]);

module.exports = async (page, h) => {
  const info = await h.eval(
    ({ only, variants, state }) => {
      const G = window.__G;
      const { THREE } = G;
      // An empty lot in place of the block: same sky, same key light, nothing in the way.
      G.level.root.visible = false;
      const stubExplosives = G.scene.getObjectByName('explosives-stub');
      if (stubExplosives) stubExplosives.visible = false;
      if (G.enemies.clear) G.enemies.clear();

      const stage = new THREE.Group();
      stage.name = 'props-gallery';
      G.scene.add(stage);
      const ground = new THREE.Mesh(new THREE.PlaneGeometry(96, 72), G.mats.get('sidewalk'));
      ground.rotation.x = -Math.PI / 2;
      ground.receiveShadow = true;
      stage.add(ground);

      const entries = [];
      for (const name of G.props.names()) entries.push([name, name, { seed: 3 }]);
      for (const [label, [name, opts]] of Object.entries(variants)) entries.push([label, name, { seed: 3, ...opts }]);
      const wanted = only ? entries.filter(([label, name]) => only.includes(label) || only.includes(name)) : entries;

      const colliders = new THREE.Group();
      colliders.name = 'gallery-colliders';
      colliders.visible = false;
      stage.add(colliders);
      const wire = new THREE.LineBasicMaterial({ color: 0x40ff70, depthTest: false });
      const posts = new THREE.Group();
      stage.add(posts);
      const postGeo = new THREE.BoxGeometry(0.06, 0.3, 0.06);
      const postMats = [new THREE.MeshBasicMaterial({ color: 0xf4f2ec }), new THREE.MeshBasicMaterial({ color: 0xe2222b })];

      const items = [];
      const live = [];
      const GAP = 1.6;
      const ROW = 40;
      let x = -ROW / 2;
      let z = -30;
      let depth = 0;
      for (const [label, name, opts] of wanted) {
        const prop = G.props.build(name, opts);
        const [L, H, W] = prop.size;
        if (x + L > ROW / 2) {
          x = -ROW / 2;
          z += depth + 3.2;
          depth = 0;
        }
        const cx = x + L / 2;
        const cz = z + Math.max(W, 1.2) / 2;
        prop.object.position.set(cx, 0, cz);
        stage.add(prop.object);
        if (state && prop.setState) prop.setState(state, 0.6);
        if (prop.update) live.push(prop);

        // Name on the ground in front, colliders as wire boxes, a striped 1.8 m post at the left.
        const tag = G.mats.sign({ text: label, w: Math.max(1.5, Math.min(L, 3)), h: 0.36, style: 'plate', lit: true });
        const plateGeo = new THREE.PlaneGeometry(tag.w, tag.h);
        if (tag.uv) {
          // The library hands out a rect on a shared atlas page: map the quad into it.
          const uv = plateGeo.getAttribute('uv');
          const [u0, v0, u1, v1] = tag.uv;
          for (let i = 0; i < uv.count; i++) uv.setXY(i, u0 + uv.getX(i) * (u1 - u0), v0 + uv.getY(i) * (v1 - v0));
        }
        const plate = new THREE.Mesh(plateGeo, tag.material);
        plate.rotation.x = -Math.PI / 2;
        plate.position.set(cx, 0.02, cz + Math.max(W, 1.2) / 2 + 0.45);
        stage.add(plate);
        for (const c of prop.colliders) {
          const size = [c.max[0] - c.min[0], c.max[1] - c.min[1], c.max[2] - c.min[2]];
          const box = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(...size)), wire);
          box.position.set(cx + (c.min[0] + c.max[0]) / 2, (c.min[1] + c.max[1]) / 2, cz + (c.min[2] + c.max[2]) / 2);
          box.renderOrder = 10;
          colliders.add(box);
        }
        for (let i = 0; i < 6; i++) {
          const seg = new THREE.Mesh(postGeo, postMats[i % 2]);
          seg.position.set(cx - L / 2 - 0.35, 0.15 + i * 0.3, cz + Math.max(W, 1.2) / 2);
          posts.add(seg);
        }

        // Measure against the catalogue box.
        prop.object.updateMatrixWorld(true);
        // What is on show only: a hidden flame or wreck is not part of the prop's resting shape.
        const box = new THREE.Box3();
        prop.object.traverseVisible((o) => {
          if (o.isMesh) box.union(new THREE.Box3().setFromObject(o, false));
        });
        let triangles = 0;
        let meshes = 0;
        prop.object.traverse((o) => {
          if (!o.isMesh) return;
          meshes++;
          triangles += (o.geometry.index ? o.geometry.index.count : o.geometry.getAttribute('position').count) / 3;
        });
        items.push({
          label, name, cx, cz, L, H, W, triangles, meshes,
          fallback: !!prop.fallback,
          dynamic: !!prop.dynamic,
          lights: prop.lights ? prop.lights.length : 0,
          colliders: prop.colliders.length,
          over: [
            -L / 2 - (box.min.x - cx), box.max.x - cx - L / 2,
            -box.min.y, box.max.y - H,
            -W / 2 - (box.min.z - cz), box.max.z - cz - W / 2,
          ].map((v) => Math.round(v * 1000) / 1000),
        });
        x += L + GAP;
        depth = Math.max(depth, W, 1.2);
      }

      // Keep the stateful props alive: the level only updates its own.
      const levelUpdate = G.level.update.bind(G.level);
      G.level.update = (dt) => {
        levelUpdate(dt);
        for (const prop of live) prop.update(dt);
      };
      window.__gallery = { colliders, posts };
      return { items, stats: G.props.stats() };
    },
    { only: ONLY, variants: VARIANTS, state: STATE },
  );

  const { items } = info;
  const triangles = items.reduce((sum, it) => sum + it.triangles, 0);
  console.error(`gallery: ${items.length} props, ${triangles} triangles, ${info.stats.shapes} shapes`);
  for (const it of items) {
    const worst = Math.max(...it.over);
    const flag = it.fallback ? ' FALLBACK' : worst > 0.03 && !OVERHANG.has(it.label) ? ` OUTSIDE by ${worst} [${it.over.join(' ')}]` : '';
    console.error(
      `  ${it.label.padEnd(22)} ${String(it.triangles).padStart(5)} tris ${String(it.meshes).padStart(3)} meshes ${it.colliders} col` +
        `${it.lights ? ` ${it.lights} lamp` : ''}${it.dynamic ? ' dyn' : ''}${flag}`,
    );
  }

  // Groups of neighbours that fit one picture.
  const groups = [];
  let group = [];
  for (const it of items) {
    const first = group[0];
    const tooWide = first && it.cx + it.L / 2 - (first.cx - first.L / 2) > 13;
    if (first && (it.cz - it.W / 2 !== first.cz - first.W / 2 && Math.abs(it.cz - first.cz) > 2.2 || tooWide)) {
      groups.push(group);
      group = [];
    }
    group.push(it);
  }
  if (group.length) groups.push(group);

  const shoot = async (name, cam, fov, extra) => {
    await h.eval((view) => {
      window.__gallery.colliders.visible = !!view.colliders;
      window.__gallery.posts.visible = !view.noPosts;
      window.__setShot({ cam: view.cam, fov: view.fov, exposure: view.exposure });
    }, { cam: cam.map((v) => v.toFixed(2)).join(','), fov, exposure: EXPOSURE, ...extra });
    await h.frames(2);
    await h.shot(path.join(OUT, `${name}.png`));
  };

  let n = 0;
  for (const g of groups) {
    const x0 = g[0].cx - g[0].L / 2;
    const x1 = g[g.length - 1].cx + g[g.length - 1].L / 2;
    const zFront = Math.max(...g.map((it) => it.cz + it.W / 2));
    const zBack = Math.min(...g.map((it) => it.cz - it.W / 2));
    const tall = Math.max(...g.map((it) => it.H));
    const mid = (x0 + x1) / 2;
    const zMid = (zFront + zBack) / 2;
    const width = x1 - x0 + 1.5;
    const dist = Math.max(width / 2 / 0.78, tall * 1.25, 3.2);
    const lookY = Math.min(tall / 2, 2.5);
    const id = String(n++).padStart(2, '0');
    const tag = `${id}-${g[0].label.replace(/\W+/g, '_')}`;
    if (VIEWS.includes('front')) await shoot(`front-${tag}`, [mid + dist * 0.45, lookY + dist * 0.42, zFront + dist * 0.9, mid, lookY * 0.8, zMid], 50);
    if (VIEWS.includes('eye')) await shoot(`eye-${tag}`, [mid - dist * 0.25, 1.68, zFront + dist * 0.95, mid, Math.min(1.0, tall / 2), zMid], 55);
    if (VIEWS.includes('back')) await shoot(`back-${tag}`, [mid - dist * 0.45, lookY + dist * 0.35, zBack - dist * 0.9, mid, lookY * 0.8, zMid], 50);
    if (VIEWS.includes('top')) await shoot(`top-${tag}`, [mid, Math.max(dist * 1.3, 7), zMid + 0.5, mid, 0, zMid], 50, { noPosts: true });
    if (VIEWS.includes('colliders')) {
      await shoot(`col-${tag}`, [mid + dist * 0.45, lookY + dist * 0.42, zFront + dist * 0.9, mid, lookY * 0.8, zMid], 50, { colliders: true });
    }
  }

  // Close-ups: each prop on its own from four sides (for working on one model).
  if (VIEWS.includes('each')) {
    for (const it of items) {
      const tag = it.label.replace(/\W+/g, '_');
      const size = Math.max(it.L, it.W, it.H * 1.2);
      const d = Math.max(size * 1.15, 1.6);
      const y = Math.min(it.H / 2, 2.2);
      await shoot(`${tag}-1-front`, [it.cx + d * 0.75, Math.max(1.68, y + d * 0.2), it.cz + d * 0.8, it.cx, y, it.cz], 50);
      await shoot(`${tag}-2-rear`, [it.cx - d * 0.8, y + d * 0.45, it.cz - d * 0.7, it.cx, y, it.cz], 50);
      await shoot(`${tag}-3-side`, [it.cx, y + 0.2, it.cz + d * 2.6, it.cx, y, it.cz], 24);
      await shoot(`${tag}-4-low`, [it.cx - d * 0.9, 1.05, it.cz + d * 0.55, it.cx, y * 0.9, it.cz], 55);
    }
  }

  // Cover: a crouched eye (1.05 m) is hidden behind a sedan's body, a standing one (1.68 m) sees over its bonnet.
  const cover = await h.eval(() => {
    const G = window.__G;
    const V = (x, y, z) => new G.THREE.Vector3(x, y, z);
    const sedan = G.props.build('sedan', { seed: 3 });
    const at = [60, 60]; // out of everybody's way
    const boxes = sedan.colliders.map((c) =>
      G.physics.addBox({ min: [c.min[0] + at[0], c.min[1], c.min[2] + at[1]], max: [c.max[0] + at[0], c.max[1], c.max[2] + at[1]], surface: c.surface, noNav: true }),
    );
    const sees = (x, y0, y1) => G.physics.lineOfSight(V(at[0] + x, y0, at[1] - 1.5), V(at[0] + x, y1, at[1] + 5));
    const result = { crouched: [], standing: sees(1.4, 1.68, 1.2) };
    for (let x = -2.1; x <= 2.1; x += 0.3) result.crouched.push(sees(x, 1.05, 1.05));
    G.physics.removeBoxes(boxes);
    return result;
  });
  if (cover.crouched.some(Boolean)) throw new Error('a crouched eye can be seen across a sedan');
  if (!cover.standing) throw new Error('a standing eye cannot see over a sedan bonnet');
  console.error('cover: crouched eye hidden behind the sedan along its whole length, standing eye sees over the bonnet');

  const fallbacks = items.filter((it) => it.fallback).map((it) => it.label);
  const outside = items.filter((it) => !OVERHANG.has(it.label) && Math.max(...it.over) > 0.03).map((it) => it.label);
  if (fallbacks.length) throw new Error(`props that fell back to a box: ${fallbacks.join(', ')}`);
  if (outside.length) throw new Error(`props outside their catalogue box: ${outside.join(', ')}`);
  if (!ONLY && triangles > 150000) throw new Error(`the catalogue is ${triangles} triangles (budget 150 000)`);
};
