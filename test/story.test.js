// The story (src/config/story.js, src/game/story.js, cutscene.js, guide.js, pickups.js): its levels
// against the real block (every start, post and crate can be stood on, every level has a way to its
// objective), its cutscenes against their words and against the walls, and the pure rules around them.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import * as flow from '../src/config/flow.js';
import * as story from '../src/config/story.js';
import * as text from '../src/config/text.js';
import * as weapons from '../src/config/weapons.js';
import { createCutscene } from '../src/game/cutscene.js';
import { offRoute, resample } from '../src/game/guide.js';
import { pickupLine, shouldDrop } from '../src/game/pickups.js';
import { facing, levelCard, lineSeconds, objectiveLine, patrolOf, sceneProblems, stageOf, timeOf } from '../src/game/story.js';
import { buildLevel } from './level-helpers.js';

const G = await buildLevel();
const { physics, level } = G;
const nav = physics.nav;
const V = (x, y, z) => new THREE.Vector3(x, y, z);
const flat = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);
const near = (a, b, eps = 1e-9, label = '') => assert.ok(Math.abs(a - b) <= eps, `${label} expected ${b} ± ${eps}, got ${a}`);

/** Where a level leads: its reel, or the truck. */
const goalOf = (L) => (L.reel ? level.objectives.find((o) => o.id === L.reel).pos : level.extraction.pos);
/** An authored ground point where the game will put it: the nearest walkable cell. */
const onStreet = (x, z) => nav.nearestWalkable(x, z, 3);
const routeLength = (route) => route.reduce((sum, p, i) => (i ? sum + flat(p, route[i - 1]) : 0), 0);

// ------------------------------------------------------------------------------------------ levels

test('story: four levels, a reel each for the first three, the truck last, a scene for every one', () => {
  assert.deepEqual(story.levels.map((l) => l.id), ['avenue', 'shop', 'cage', 'truck']);
  assert.deepEqual(story.levels.map((l) => l.goal), ['reel', 'reel', 'reel', 'truck']);
  assert.deepEqual(story.levels.map((l) => l.reel), ['reel1', 'reel2', 'reel3', undefined]);
  // The reels are taken in the order of their route bullets.
  assert.deepEqual(level.objectives.map((o) => o.id), ['reel1', 'reel2', 'reel3']);
  for (const L of story.levels) {
    assert.ok(story.scenes[L.scene], `${L.id}: its scene exists`);
    assert.ok(text.story.levels[L.id], `${L.id}: its words exist`);
  }
  assert.ok(story.scenes[story.endScene]);
  // The story begins where the block always began.
  near(story.levels[0].start.x, level.playerStart.pos.x);
  near(story.levels[0].start.z, level.playerStart.pos.z);
  // Night falls for the last two levels and stays.
  assert.deepEqual(story.levels.map((l, i) => timeOf(i, story.levels, 'day')), ['day', 'day', 'night', 'night']);
  assert.deepEqual(story.levels.map((l, i) => timeOf(i, story.levels, 'night')), ['night', 'night', 'night', 'night']);
});

test('story: every level starts on walkable ground with a route to what it wants', () => {
  for (const [i, L] of story.levels.entries()) {
    const start = onStreet(L.start.x, L.start.z);
    assert.ok(start, `${L.id}: a start`);
    assert.ok(flat(start, V(L.start.x, 0, L.start.z)) < 1, `${L.id}: the authored start is (nearly) walkable`);
    const route = nav.findPath(start, goalOf(L), []);
    assert.ok(route && route.length >= 2, `${L.id}: a route to its objective`);
    const length = routeLength(route);
    assert.ok(length > 15 && length < 90, `${L.id}: ${length.toFixed(1)} m is a walk, not a step and not a trek`);
    // Rule starts facing down that route.
    const yaw = facing(route, 99);
    assert.notEqual(yaw, 99);
    const ahead = route[Math.min(route.length - 1, 2)];
    const want = Math.atan2(-(ahead.x - start.x), -(ahead.z - start.z));
    assert.ok(Math.abs(Math.atan2(Math.sin(yaw - want), Math.cos(yaw - want))) < 1.2, `${L.id}: faces the way to go`);
    // A level begins where the one before ended: within a short walk of the last objective.
    if (i > 0) assert.ok(flat(start, goalOf(story.levels[i - 1])) < 22, `${L.id}: starts near where level ${i} ended`);
  }
});

test('story: every post can be stood on (or hovered at) and is enough for the hardest difficulty', () => {
  const most = { goon: 0, buzzard: 0 };
  for (const [i, L] of story.levels.entries()) {
    for (const name of flow.difficulties) {
      const patrol = flow.difficulty[name].levels[i].patrol;
      for (const type of ['goon', 'buzzard']) {
        assert.ok(L.posts[type].length >= patrol[type], `${L.id}: ${patrol[type]} ${type} posts for ${name}`);
        most[type] = Math.max(most[type], patrol[type]);
      }
    }
    const start = onStreet(L.start.x, L.start.z);
    const taken = [];
    for (const [x, z] of L.posts.goon) {
      const at = onStreet(x, z);
      assert.ok(at && flat(at, V(x, 0, z)) < 1, `${L.id}: goon post (${x}, ${z}) is walkable`);
      assert.ok(flat(at, start) > 9, `${L.id}: nobody stands on top of Rule's start`);
      for (const other of taken) assert.ok(flat(at, other) > 1.2, `${L.id}: two posts on one spot`);
      taken.push(at);
      // …and is a place a Goon can walk to Rule from.
      assert.ok(nav.findPath(at, start, []), `${L.id}: a way from the post at (${x}, ${z})`);
    }
    // Nobody who is posted on any difficulty can see Rule where the level puts him down: he gets his
    // bearings (and the Vault's first word) before anyone comes at him.
    const eye = V(start.x, physics.groundHeight(start.x, start.z, 3) + 1.68, start.z);
    const used = Math.max(...flow.difficulties.map((name) => flow.difficulty[name].levels[i].patrol.goon));
    for (const [x, z] of L.posts.goon.slice(0, used)) {
      const at = onStreet(x, z);
      const seen = physics.lineOfSight(eye, V(at.x, 1.6, at.z)) || physics.lineOfSight(eye, V(at.x, 1.0, at.z));
      assert.equal(seen, false, `${L.id}: the Goon posted at (${x}, ${z}) can see the level's start`);
    }
    const air = Math.max(...flow.difficulties.map((name) => flow.difficulty[name].levels[i].patrol.buzzard));
    for (const [x, y, z] of L.posts.buzzard.slice(0, air)) {
      assert.equal(physics.lineOfSight(eye, V(x, y, z)), false, `${L.id}: the Buzzard posted at (${x}, ${y}, ${z}) can see the level's start`);
    }
    for (const [x, y, z] of L.posts.buzzard) {
      assert.ok(y >= 5 && y <= 16, `${L.id}: a Buzzard hovers at a sensible height`);
      assert.equal(physics.overlapsCylinder(x, z, 0.7, y - 0.5, y + 0.5), false, `${L.id}: the air post at (${x}, ${y}, ${z}) is free air`);
      assert.ok(x > level.bounds.minX && x < level.bounds.maxX && z > level.bounds.minZ && z < level.bounds.maxZ);
    }
  }
  assert.ok(most.goon >= 4 && most.buzzard >= 2);
});

test('story: ammo crates lie on the way, on the floor, clear of the start, the reel and anything that blows', () => {
  const lists = [...story.levels.map((L) => [L.id, L.crates, L]), ['holdout', story.holdoutCrates, null]];
  for (const [id, crates, L] of lists) {
    assert.ok(crates.length >= 3 && crates.length <= 10, `${id}: ${crates.length} crates`);
    const placed = [];
    for (const [x, z] of crates) {
      const at = onStreet(x, z);
      assert.ok(at && flat(at, V(x, 0, z)) < 1, `${id}: crate (${x}, ${z}) is on walkable ground`);
      assert.ok(Math.abs(physics.groundHeight(at.x, at.z, 3)) < 0.5, `${id}: on the street, not on a deck`);
      for (const e of level.explosives) assert.ok(flat(at, e.pos) > 1.6, `${id}: crate (${x}, ${z}) sits on an explosive`);
      for (const other of placed) assert.ok(flat(at, other) > 4, `${id}: two crates side by side`);
      placed.push(at);
      if (!L) continue;
      const start = onStreet(L.start.x, L.start.z);
      assert.ok(flat(at, start) > 3.5, `${id}: crate (${x}, ${z}) would be taken on the first step`);
      assert.ok(flat(at, goalOf(L)) > flow.pickups.radius + 0.5, `${id}: crate on the objective`);
      assert.ok(nav.findPath(start, at, []), `${id}: crate (${x}, ${z}) can be walked to`);
    }
    if (!L) continue;
    // At least two of them are no detour: within ten metres of the straight way to the objective.
    const start = onStreet(L.start.x, L.start.z);
    const samples = new Float32Array(900);
    const n = resample(nav.findPath(start, goalOf(L), []), 0.5, 500, samples);
    const close = placed.filter((at) => offRoute(samples, n, at.x, at.z) < 10).length;
    assert.ok(close >= 2, `${id}: ${close} crates near the route`);
  }
  assert.ok(story.holdoutCrates.length >= flow.pickups.holdoutCrates);
});

// --------------------------------------------------------------------------------------- cutscenes

test('cutscenes: every scene has its words, no line talks over another, all of it fits', () => {
  const cps = flow.pacing.radioCharsPerSec;
  for (const [name, scene] of Object.entries(story.scenes)) {
    const lines = text.story.scenes[name];
    assert.ok(Array.isArray(lines) && lines.length > 0, `${name}: lines`);
    assert.deepEqual(sceneProblems(name, scene, lines, cps), []);
    // Every line is said, once, in order.
    const said = scene.cues.filter((c) => c.say !== undefined).map((c) => c.say);
    assert.deepEqual(said, lines.map((_, i) => i), `${name}: the cues say every line in order`);
    for (const line of lines) {
      assert.ok(text.story.speakers[line.who], `${name}: speaker ${line.who}`);
      assert.ok(lineSeconds(line, cps) < 6.5, `${name}: "${line.text.slice(0, 30)}…" is short enough to read`);
    }
    const duration = scene.shots.reduce((sum, shot) => sum + shot.secs, 0);
    assert.ok(duration >= 10 && duration <= 22, `${name}: ${duration} s`);
    // A level's scene ends on its title card; the last scene on the closing one.
    const cards = scene.cues.filter((c) => c.card);
    assert.equal(cards.length, 1, `${name}: one title card`);
    assert.equal(cards[0].card, name === story.endScene ? 'end' : 'level');
    assert.ok(duration - cards[0].at >= 3, `${name}: the card stays up at least three seconds`);
  }
  // Both voices are heard, and Rule has the last word of every scene.
  for (const lines of Object.values(text.story.scenes)) assert.equal(lines.at(-1).who, 'rule');
});

test('cutscenes: the camera never passes through anything and always looks at something', () => {
  const T = { ...flow.story.cutscene, sway: { rate: 0, side: 0, lift: 0, roll: 0 } };
  for (const [name, scene] of Object.entries(story.scenes)) {
    const play = createCutscene(scene, T);
    const hits = [];
    for (let t = 0; t <= play.duration; t += 0.1) {
      const p = play.sample(t, {});
      // The sway adds a few centimetres: a 0.3 m cylinder leaves room for it.
      if (physics.overlapsCylinder(p.x, p.z, 0.3, p.y - 0.25, p.y + 0.25)) hits.push(`${t.toFixed(1)} s (${p.x.toFixed(1)}, ${p.y.toFixed(1)}, ${p.z.toFixed(1)})`);
      assert.ok(Math.hypot(p.lookX - p.x, p.lookY - p.y, p.lookZ - p.z) > 2.5, `${name} at ${t.toFixed(1)} s looks at its own feet`);
      assert.ok(p.y > 1 && p.y < 7 && p.fov >= 30 && p.fov <= 60, `${name} at ${t.toFixed(1)} s: height ${p.y}, fov ${p.fov}`);
    }
    assert.deepEqual(hits.slice(0, 4), [], `${name}: ${hits.length} samples inside something`);
    // The level's objective is in the last picture of its scene, in clear view.
    const L = story.levels.find((l) => l.scene === name);
    if (!L) continue;
    const last = play.sample(play.duration - 0.6, {});
    const goal = goalOf(L);
    assert.ok(flat(last, goal) < 24, `${name}: ends near what the level is after`);
    assert.ok(physics.lineOfSight(V(last.x, last.y, last.z), V(goal.x, goal.y + 1.4, goal.z)), `${name}: and can see it`);
  }
});

test('cutscene director: shots in order, hard cuts with a blink, cues once, black at both ends', () => {
  const scene = {
    shots: [
      { from: [0, 2, 0, 0, 2, -10], to: [10, 2, 0, 10, 2, -10], secs: 4, fov: 50 },
      { from: [100, 3, 0, 100, 3, 10], to: [100, 3, 0, 100, 3, 10], secs: 2, fov: 40, fovTo: 30 },
      { from: [0, 0, 0], to: [1, 1, 1], secs: 9 }, // not a composition: dropped
    ],
    cues: [{ at: 5, say: 1 }, { at: 0.5, say: 0 }, { at: 0, train: 1 }, { at: 5.9, card: 'level' }],
  };
  const T = { fadeIn: 1, fadeOut: 0.5, cut: 0.2, ease: 0, sway: { rate: 0, side: 0, lift: 0, roll: 0 } };
  const fired = [];
  const play = createCutscene(scene, T, (cue) => fired.push(cue.say !== undefined ? `say${cue.say}` : cue.card ? 'card' : 'train'));
  assert.equal(play.duration, 6);
  assert.equal(play.shots.length, 2);
  assert.equal(play.done, false);

  // Opens from black; the first shot moves in a straight line.
  assert.equal(play.sample(0, {}).fade, 1);
  let p = play.sample(2, {});
  assert.deepEqual([p.x, p.y, p.z, p.fov, p.shot], [5, 2, 0, 50, 0]);
  near(p.lookX, 5, 1e-9, 'a move with the view held: the look point travels with the camera');
  near(p.lookZ, -10, 1e-9);
  assert.equal(p.fade, 0);
  // A blink of black across the cut, and the second shot is somewhere else entirely.
  assert.ok(play.sample(3.9, {}).fade > 0.4);
  p = play.sample(4, {});
  assert.deepEqual([p.x, p.shot, p.fade], [100, 1, 1]);
  assert.ok(play.sample(4.1, {}).fade > 0.4);
  assert.equal(play.sample(4.5, {}).fade, 0);
  // The second shot only zooms; the scene closes to black.
  near(play.sample(5, {}).fov, 35, 1e-9);
  assert.equal(play.sample(6, {}).fade, 1);
  assert.ok(play.sample(5.8, {}).fade > 0.5);

  // Cues fire once each, in time order, whatever the frame rate.
  assert.equal(play.update(0.25), false);
  assert.deepEqual(fired, ['train']);
  play.update(0.3);
  assert.deepEqual(fired, ['train', 'say0']);
  for (let i = 0; i < 40; i++) play.update(0.1);
  assert.deepEqual(fired, ['train', 'say0'], '4.55 s in: the next cue is at 5 s');
  assert.equal(play.update(1), false);
  assert.deepEqual(fired, ['train', 'say0', 'say1']);
  assert.equal(play.update(1), true, 'over');
  assert.deepEqual(fired, ['train', 'say0', 'say1', 'card']);
  assert.equal(play.done, true);
  assert.equal(play.time, 6);
  assert.equal(play.update(1), true);
  assert.equal(fired.length, 4);

  // A real camera is put where the scene has it.
  const camera = new THREE.PerspectiveCamera();
  play.sample(2);
  assert.equal(play.apply(camera), 0);
  assert.deepEqual(camera.position.toArray(), [5, 2, 0]);
  assert.equal(camera.fov, 50);
  near(camera.getWorldDirection(V(0, 0, 0)).z, -1, 1e-9);

  // A pan: the view turns evenly between the two directions, and what it looks at never comes near.
  const pan = createCutscene({ shots: [{ from: [0, 2, 0, 0, 2, -10], to: [2, 2, 0, 12, 2, 0], secs: 2, fov: 50 }] }, T);
  for (let t = 0; t <= 2; t += 0.25) {
    const q = pan.sample(t, {});
    near(Math.hypot(q.lookX - q.x, q.lookY - q.y, q.lookZ - q.z), 10, 1e-9, `reach at ${t} s`);
    near(Math.atan2(q.lookX - q.x, -(q.lookZ - q.z)), (Math.PI / 2) * (t / 2), 1e-9, `turned ${t / 2} of the way at ${t} s`);
  }

  // Skipping goes straight to the end and says nothing more.
  const fired2 = [];
  const again = createCutscene(scene, T, (cue) => fired2.push(cue));
  again.update(1);
  assert.equal(fired2.length, 2);
  again.skip();
  assert.equal(again.done, true);
  assert.equal(again.time, again.duration);
  assert.equal(again.pose.fade, 1);
  assert.equal(again.update(1), true);
  assert.equal(fired2.length, 2, 'a skipped line is not said');

  // A scene with nothing to show is over before it starts.
  assert.equal(createCutscene({ shots: [] }, T).done, true);
});

// ------------------------------------------------------------------------------------- bookkeeping

test('story rules: stage, patrol, objective line, title card', () => {
  const s = stageOf(1, story.levels);
  assert.deepEqual([s.index, s.n, s.total, s.id, s.goal, s.reel, s.last, s.scene], [1, 2, 4, 'shop', 'reel', 'reel2', false, 'shop']);
  assert.equal(stageOf(3, story.levels).last, true);
  assert.equal(stageOf(99, story.levels).n, 4, 'clamped');
  assert.equal(stageOf(-5, story.levels).n, 1);

  const L = story.levels[2];
  assert.deepEqual(patrolOf(L, { buzzard: 1, goon: 2 }), [
    { type: 'buzzard', point: L.posts.buzzard[0] },
    { type: 'goon', point: L.posts.goon[0] },
    { type: 'goon', point: L.posts.goon[1] },
  ]);
  assert.deepEqual(patrolOf(L, { buzzard: 0, goon: 0 }), []);
  assert.equal(patrolOf(L, { buzzard: 99, goon: 99 }).length, L.posts.buzzard.length + L.posts.goon.length, 'never more than there are posts');
  assert.deepEqual(patrolOf({}, { goon: 3 }), []);

  const O = text.story.objectives;
  assert.equal(objectiveLine('reach', { code: '2', guided: true }, O), 'Get to reel 2 — follow the gold line');
  assert.equal(objectiveLine('reach', { code: '2', guided: false }, O), 'Get to reel 2');
  assert.equal(objectiveLine('clear', { left: 5 }, O), 'Clear the block — 5 Vultures left');
  assert.equal(objectiveLine('clear', { left: 1 }, O), 'One Vulture left — finish it');
  assert.equal(objectiveLine('clear', { left: 0 }, O), 'One Vulture left — finish it', 'never "0 left": the level is over by then');
  assert.equal(objectiveLine('truck', { guided: true }, O), 'Get to the IPX truck — follow the gold line');
  assert.equal(objectiveLine('done', {}, O), 'Level clear');
  assert.equal(objectiveLine('nonsense', {}, O), '');

  assert.deepEqual(levelCard(stageOf(0, story.levels), text.story), { kicker: 'LEVEL 1 OF 4', title: 'THE AVENUE', sub: 'Take back the first reel' });
  assert.deepEqual(levelCard(stageOf(3, story.levels), text.story), { kicker: 'LEVEL 4 OF 4', title: 'THE TRUCK', sub: 'Get the reels to the IPX truck' });
});

test('story rules: Rule faces down the route, not at its first step', () => {
  // A route that steps 0.8 m south-east round a post, then runs 20 m east.
  const route = [V(0, 0, 0), V(0.6, 0, 0.6), V(20, 0, 0.6)];
  const yaw = facing(route, 0);
  near(yaw, -Math.PI / 2, 0.15, 'east');
  // 0 looks north (−Z), + turns left (west).
  near(facing([V(0, 0, 0), V(0, 0, -9)]), 0);
  near(facing([V(0, 0, 0), V(-9, 0, 0)]), Math.PI / 2);
  near(Math.abs(facing([V(0, 0, 0), V(0, 0, 9)])), Math.PI);
  assert.equal(facing(null, 1.5), 1.5);
  assert.equal(facing([V(1, 0, 1)], 1.5), 1.5);
  assert.equal(facing([V(1, 0, 1), V(1, 0, 1)], 1.5), 1.5, 'a route with no length');
});

// -------------------------------------------------------------------------------------- guide line

test('guide line: a route is sampled at even steps, corners and all', () => {
  const out = new Float32Array(300);
  // 10 m east, then 5 m south.
  const n = resample([V(0, 0, 0), V(10, 0, 0), V(10, 0, 5)], 0.5, 100, out);
  assert.equal(n, 31, 'a sample every half metre, both ends included');
  assert.deepEqual([out[0], out[1], out[2]], [0, 0, 0]);
  near(out[20 * 3], 10);
  near(out[20 * 3 + 2], 10, 1e-9, 'distance along the route');
  near(out[30 * 3], 10);
  near(out[30 * 3 + 1], 5);
  near(out[30 * 3 + 2], 15);
  for (let i = 1; i < n; i++) near(Math.hypot(out[i * 3] - out[(i - 1) * 3], out[i * 3 + 1] - out[(i - 1) * 3 + 1]), 0.5, 1e-6, `step ${i}`);

  // A step that does not divide the legs carries over the corner.
  const m = resample([V(0, 0, 0), V(1, 0, 0), V(1, 0, 1)], 0.75, 100, out);
  assert.equal(m, 3);
  near(out[2 * 3 + 2], 1.5);
  near(out[2 * 3], 1);
  near(out[2 * 3 + 1], 0.5);

  // Stops at the limit, and at the end of the buffer.
  assert.equal(resample([V(0, 0, 0), V(100, 0, 0)], 1, 10, out), 11);
  assert.equal(resample([V(0, 0, 0), V(100, 0, 0)], 1, 1000, new Float32Array(15)), 5);
  assert.equal(resample([], 1, 10, out), 0);
  assert.equal(resample(null, 1, 10, out), 0);

  // How far off the route a point is.
  const k = resample([V(0, 0, 0), V(10, 0, 0)], 0.5, 100, out);
  near(offRoute(out, k, 4, 3), 3);
  near(offRoute(out, k, 14, 0), 4);
  assert.equal(offRoute(out, 0, 1, 1), Infinity);
});

// ----------------------------------------------------------------------------------------- pickups

test('pickups: what a Vulture leaves, and what the HUD says about it', () => {
  const P = flow.pickups;
  // By chance per type; never for something that is not a Vulture.
  assert.equal(shouldDrop('goon', P.dropChance.goon - 0.01, 1, P), true);
  assert.equal(shouldDrop('goon', P.dropChance.goon, 1, P), false);
  assert.equal(shouldDrop('buzzard', P.dropChance.buzzard - 0.01, 1, P), true);
  assert.equal(shouldDrop('buzzard', P.dropChance.buzzard + 0.01, 1, P), false);
  assert.equal(shouldDrop('crate', 0, 1, P), false);
  assert.ok(P.dropChance.goon > P.dropChance.buzzard);
  // Always when the gun in hand is running dry.
  assert.equal(shouldDrop('goon', 0.999, P.dropAlways, P), true);
  assert.equal(shouldDrop('buzzard', 0.999, 0, P), true);
  assert.equal(shouldDrop('goon', 0.999, P.dropAlways + 0.01, P), false);

  const T = text.story.pickup;
  assert.equal(pickupLine('crate', [{ id: 'chopper', name: 'CHOPPER', rounds: 60 }], T), T.crate);
  assert.equal(pickupLine('pouch', [{ id: 'chopper', name: 'CHOPPER', rounds: 30 }, { id: 'ar15', name: 'AR-15', rounds: 30 }], T), T.pouch);
  // Every line the HUD's centre message carries in a fight fits one line between a phone's thumbs.
  const H = text.story.hints;
  for (const line of [T.crate, T.pouch, T.full, H.aim('RMB'), H.aimTouch, H.weaponsTouch, H.crates]) assert.ok(line.length <= 30, `"${line}" is ${line.length} characters`);
  assert.equal(pickupLine('crate', [], T), T.full);
  assert.equal(pickupLine('pouch', null, T), T.full);

  // A crate is worth a drop to every gun that can run dry; a pouch feeds the bullet guns only.
  assert.equal(P.crate, 1);
  assert.ok(P.drop > 0 && P.drop < 1);
  for (const id of weapons.common.order) {
    const def = weapons[id];
    if (!Number.isFinite(def.reserve)) continue;
    assert.ok(def.pickup.rounds * P.crate >= 1, id);
    if (!def.projectile) assert.ok(Math.round(def.pickup.rounds * P.drop) >= def.magSize / 2, `${id}: a pouch is at least half a magazine`);
  }
  assert.ok(P.radius >= 1 && P.radius <= 2.5 && P.dropLife >= 20);
});
