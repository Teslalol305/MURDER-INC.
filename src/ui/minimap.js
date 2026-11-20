// The minimap (DESIGN 8.2, CONTRACT 11.3): a top-down plan of the block that turns with the player.
//
// The static plan (ground by surface, cover, buildings and walls, the El's two tracks) is painted once to
// an offscreen canvas from data the level already exposes; every frame that plan is blitted, rotated about
// the player, and the live things are drawn over it: the guide line (the dotted route to the objective),
// ammo on the ground, reel bullets and the truck (pinned to the rim when they are off the map), red pips
// for enemies in the fight and for the last few being hunted, the player's arrow in the middle.

import { enemyOnMap, pinToRim, planKind, toMap } from './logic.js';

const VIEW_RADIUS = 30; // metres from the centre to the middle of an edge
const MARGIN = 24; // metres of surrounding city painted around the play bounds
const MAX_DPR = 2;
const PIN_INSET = 11; // css px from the rim to the centre of a pinned bullet
const FIRE_WINDOW = 2; // an enemy shows this long after it fired

// Map inks: the plate tones of the HUD, stepped so the plan reads at a glance.
const INK = {
  city: '#0c0e11', // beyond the bounds: more city, kept dark so the block stands out
  ground: '#2a2f36', // sidewalks, lots, floors
  road: '#191c21', // asphalt
  dirt: '#2b2822',
  court: '#1e2a25',
  wall: '#454c57', // buildings and anything too tall to see over
  wallEdge: '#9aa1ab',
  cover: '#7b828d', // cars, barriers, crates: lighter, so the lanes read
  rail: '#4d5460',
  enemy: '#e2222b',
  ammo: '#3fe07a', // crates and pouches: the green of their marker in the world
};

export function createMinimap(G, canvas) {
  const ctx = canvas.getContext('2d');
  const brand = G.config.brand;
  const point = { x: 0, y: 0 };
  const firedAt = new Map(); // enemy id → G.time.t of its last shot

  let plan = null; // offscreen canvas of the static block
  let planScale = 1; // plan pixels per metre
  let originX = 0; // world x of the plan's left edge
  let originZ = 0; // world z of its top edge
  let size = 0; // css px
  let dpr = 1;
  let markers = [];
  const hunted = new Set(); // Vultures with a marker on them: drawn whether they are fighting or not

  if (ctx) {
    ctx.imageSmoothingEnabled = true;
  }

  G.events.on('enemy:fire', (e) => {
    if (e && e.enemy && e.enemy.id !== undefined) firedAt.set(e.enemy.id, G.time.t);
  });
  G.events.on('game:reset', () => firedAt.clear());

  /** Paints the static block once. Called lazily: every collider is registered by the time the HUD first draws. */
  function buildPlan() {
    const level = G.level;
    const physics = G.physics;
    if (!level || !level.bounds || !physics || !physics.boxes) return false;
    const b = level.bounds;
    planScale = Math.max(3, Math.min(8, Math.round(((size * dpr) / (VIEW_RADIUS * 2)) * 1.25)));
    originX = b.minX - MARGIN;
    originZ = b.minZ - MARGIN;
    const w = Math.ceil((b.maxX - b.minX + MARGIN * 2) * planScale);
    const h = Math.ceil((b.maxZ - b.minZ + MARGIN * 2) * planScale);

    plan = document.createElement('canvas');
    plan.width = w;
    plan.height = h;
    const p = plan.getContext('2d');
    if (!p) return false;
    const X = (x) => (x - originX) * planScale;
    const Z = (z) => (z - originZ) * planScale;

    p.fillStyle = INK.city;
    p.fillRect(0, 0, w, h);

    // Ground, one cell per metre, by what is underfoot.
    const surfaceAt = typeof level.groundSurfaceAt === 'function' ? level.groundSurfaceAt : null;
    p.fillStyle = INK.ground;
    p.fillRect(X(b.minX), Z(b.minZ), (b.maxX - b.minX) * planScale, (b.maxZ - b.minZ) * planScale);
    if (surfaceAt) {
      for (let z = Math.floor(b.minZ); z < b.maxZ; z++) {
        let runStart = 0;
        let runInk = null;
        for (let x = Math.floor(b.minX); x <= b.maxX; x++) {
          let ink = null;
          if (x < b.maxX) {
            let surface = 'concrete';
            try {
              surface = surfaceAt(x + 0.5, z + 0.5);
            } catch {
              /* a level without the lookup: plain ground */
            }
            ink = surface === 'asphalt' ? INK.road : surface === 'dirt' ? INK.dirt : surface === 'rubber' ? INK.court : null;
          }
          if (ink !== runInk) {
            if (runInk) {
              p.fillStyle = runInk;
              p.fillRect(X(runStart), Z(z), (x - runStart) * planScale, planScale + 0.5);
            }
            runInk = ink;
            runStart = x;
          }
        }
      }
    }

    // The El: its two tracks as ladders running the length of the avenue.
    const el = level.el;
    if (el && Number.isFinite(el.minX) && Number.isFinite(el.maxX)) {
      const tracks = Array.isArray(el.tracks) && el.tracks.length ? el.tracks : [(el.minZ + el.maxZ) / 2 - 2.2, (el.minZ + el.maxZ) / 2 + 2.2];
      p.strokeStyle = INK.rail;
      p.lineWidth = Math.max(1, planScale * 0.22);
      for (const tz of tracks) {
        for (const side of [-0.75, 0.75]) {
          p.beginPath();
          p.moveTo(0, Z(tz + side));
          p.lineTo(w, Z(tz + side));
          p.stroke();
        }
        p.beginPath();
        for (let x = Math.ceil(originX / 2) * 2; x < originX + w / planScale; x += 2) {
          p.moveTo(X(x), Z(tz - 0.75));
          p.lineTo(X(x), Z(tz + 0.75));
        }
        p.stroke();
      }
    }

    // Cover first, then everything too tall to see over on top of it.
    const boxes = physics.boxes;
    for (const pass of ['cover', 'wall']) {
      p.fillStyle = pass === 'wall' ? INK.wall : INK.cover;
      for (let i = 0; i < boxes.length; i++) {
        const box = boxes[i];
        if (planKind(box) !== pass) continue;
        const bw = Math.max(1, (box.max.x - box.min.x) * planScale);
        const bh = Math.max(1, (box.max.z - box.min.z) * planScale);
        p.fillRect(X(box.min.x), Z(box.min.z), bw, bh);
      }
    }
    // Building outlines: a hairline round every wall block so neighbouring buildings separate.
    p.strokeStyle = INK.wallEdge;
    p.globalAlpha = 0.55;
    p.lineWidth = 1;
    for (let i = 0; i < boxes.length; i++) {
      const box = boxes[i];
      if (planKind(box) !== 'wall') continue;
      const bw = (box.max.x - box.min.x) * planScale;
      const bh = (box.max.z - box.min.z) * planScale;
      if (bw < 3 || bh < 3) continue;
      p.strokeRect(X(box.min.x) + 0.5, Z(box.min.z) + 0.5, bw - 1, bh - 1);
    }
    p.globalAlpha = 1;

    // The play bounds: a hairline so the edge of the block reads.
    p.strokeStyle = INK.wallEdge;
    p.globalAlpha = 0.5;
    p.lineWidth = 1;
    p.strokeRect(X(b.minX) + 0.5, Z(b.minZ) + 0.5, (b.maxX - b.minX) * planScale - 1, (b.maxZ - b.minZ) * planScale - 1);
    p.globalAlpha = 1;
    return true;
  }

  function resize() {
    const css = Math.round(canvas.clientWidth || 150);
    const ratio = Math.min(MAX_DPR, window.devicePixelRatio || 1);
    if (css === size && ratio === dpr) return;
    size = css;
    dpr = ratio;
    canvas.width = Math.round(size * dpr);
    canvas.height = Math.round(size * dpr);
    plan = null; // repaint at the new density
  }

  function drawBullet(x, y, code, pinned) {
    const wide = code.length > 1;
    const r = 7.5;
    const w = wide ? 13 : r;
    ctx.globalAlpha = pinned ? 0.92 : 1;
    ctx.beginPath();
    if (wide) ctx.roundRect(x - w, y - r, w * 2, r * 2, r);
    else ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = brand.lines[code] || brand.colors.gold;
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = brand.colors.bg;
    ctx.stroke();
    ctx.fillStyle = wide ? brand.colors.bg : brand.colors.ink;
    ctx.font = `${wide ? 'italic 800 9px' : '700 10.5px'} ${brand.fonts.ui}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(code, x, y + 0.5);
    ctx.globalAlpha = 1;
  }

  function draw() {
    if (!ctx) return;
    resize();
    if (size === 0) return;
    if (!plan && !buildPlan()) return;
    const player = G.player;
    if (!player || !player.pos) return;
    const half = size / 2;
    const scale = half / VIEW_RADIUS; // css px per metre
    const yaw = player.yaw || 0;
    const px = player.pos.x;
    const pz = player.pos.z;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, size, size);

    // The plan, turned about the player.
    ctx.save();
    ctx.translate(half, half);
    ctx.rotate(yaw);
    const k = scale / planScale;
    ctx.scale(k, k);
    ctx.drawImage(plan, -(px - originX) * planScale, -(pz - originZ) * planScale);
    ctx.restore();

    // The guide line: the route to the objective, dotted, under everything else that lives.
    const game = G.game;
    const route = game && game.guide && game.guide.route;
    if (route && route.length > 1) {
      ctx.save();
      ctx.beginPath();
      ctx.rect(0, 0, size, size);
      ctx.clip();
      ctx.strokeStyle = game.guide.hunting ? INK.enemy : brand.colors.gold;
      ctx.lineWidth = 2;
      ctx.lineJoin = 'round';
      ctx.setLineDash([3, 4]);
      ctx.globalAlpha = 0.9;
      ctx.beginPath();
      for (let i = 0; i < route.length; i++) {
        toMap(route[i].x - px, route[i].z - pz, yaw, scale, point);
        if (i === 0) ctx.moveTo(half + point.x, half + point.y);
        else ctx.lineTo(half + point.x, half + point.y);
      }
      ctx.stroke();
      ctx.restore();
    }

    // Ammo on the ground: small green squares, only while they are on the map.
    const drops = game && game.pickups && game.pickups.list;
    if (drops) {
      ctx.fillStyle = INK.ammo;
      ctx.strokeStyle = brand.colors.bg;
      ctx.lineWidth = 1;
      for (let i = 0; i < drops.length; i++) {
        const d = drops[i];
        if (!d.live) continue;
        toMap(d.pos.x - px, d.pos.z - pz, yaw, scale, point);
        if (Math.abs(point.x) > half - 4 || Math.abs(point.y) > half - 4) continue;
        const r = d.kind === 'crate' ? 3.2 : 2.2;
        ctx.fillRect(half + point.x - r, half + point.y - r, r * 2, r * 2);
        ctx.strokeRect(half + point.x - r, half + point.y - r, r * 2, r * 2);
      }
    }

    // Enemies in the fight, and the last few of a level wherever they are (the HUD marks those too).
    const enemies = G.enemies && G.enemies.list;
    if (enemies) {
      const now = G.time.t;
      ctx.fillStyle = INK.enemy;
      ctx.strokeStyle = brand.colors.bg;
      ctx.lineWidth = 1;
      for (let i = 0; i < enemies.length; i++) {
        const e = enemies[i];
        if (!enemyOnMap(e, now, firedAt.get(e.id), FIRE_WINDOW) && !(e.alive && hunted.has(e))) continue;
        toMap(e.pos.x - px, e.pos.z - pz, yaw, scale, point);
        const pinned = pinToRim(point, half - 5);
        ctx.globalAlpha = pinned ? 0.6 : 1;
        ctx.beginPath();
        ctx.arc(half + point.x, half + point.y, pinned ? 2.6 : 3.4, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }

    // Objectives: the reel the level is after, or the truck.
    for (let i = 0; i < markers.length; i++) {
      const m = markers[i];
      if (m.kind === 'foe') continue; // a Vulture: it has its pip already
      toMap(m.pos.x - px, m.pos.z - pz, yaw, scale, point);
      const pinned = pinToRim(point, half - PIN_INSET);
      drawBullet(half + point.x, half + point.y, String(m.code), pinned);
    }

    // The player: an arrow that always points up, with a soft view cone.
    ctx.save();
    ctx.translate(half, half);
    ctx.fillStyle = brand.colors.ink;
    ctx.globalAlpha = 0.07;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.arc(0, 0, half * 0.62, -Math.PI / 2 - 0.62, -Math.PI / 2 + 0.62);
    ctx.closePath();
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.beginPath();
    ctx.moveTo(0, -8);
    ctx.lineTo(6, 6.5);
    ctx.lineTo(0, 3.2);
    ctx.lineTo(-6, 6.5);
    ctx.closePath();
    ctx.fillStyle = brand.colors.gold;
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = brand.colors.bg;
    ctx.stroke();
    ctx.restore();
  }

  return {
    draw,
    /** The HUD's markers: the reel or the truck ([{code, pos}]), or the last Vultures of a level (kind 'foe', with `enemy`). */
    setMarkers(list) {
      markers = list || [];
      hunted.clear();
      for (const m of markers) if (m.kind === 'foe' && m.enemy) hunted.add(m.enemy);
    },
    /** Forces the static plan to be repainted (after the level changed). */
    invalidate() {
      plan = null;
    },
  };
}
