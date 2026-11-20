// Pure UI rules (src/ui/logic.js): formatting, timings, crosshair, markers, minimap maths, feed, radio, menus.

import assert from 'node:assert/strict';
import { test } from 'node:test';
import * as copy from '../src/ui/copy.js';
import * as L from '../src/ui/logic.js';
import * as text from '../src/config/text.js';

const near = (a, b, eps = 1e-6) => assert.ok(Math.abs(a - b) < eps, `${a} ≉ ${b}`);

test('formatting: clock, score, percent, reserve, metres', () => {
  assert.equal(L.clock(75.4), '1:15');
  assert.equal(L.clock(-3), '0:00');
  assert.equal(L.clock(3599), '59:59');
  assert.equal(L.score(12345.6), '12,346');
  assert.equal(L.percent(0.416), '42 %');
  assert.equal(L.percent(null), '—');
  assert.equal(L.percent(undefined), '—');
  assert.equal(L.reserveText(Infinity), '∞');
  assert.equal(L.reserveText(120), '120');
  assert.equal(L.metres(41.6), '42 m');
});

test('typewriter count is clamped to the line', () => {
  assert.equal(L.typedCount(10, 0, 46), 0);
  assert.equal(L.typedCount(10, 0.1, 46), 4);
  assert.equal(L.typedCount(10, 5, 46), 10);
});

test('radio queue: one line at a time, typed, held, then the next', () => {
  const q = L.createRadioQueue(10);
  q.push('IPX VAULT', 'abcdefghij', 1); // 1 s to type, 1 s hold
  q.push('IPX VAULT', 'second', 1);
  assert.equal(q.current().text, 'abcdefghij');
  assert.equal(q.pending(), 1);
  q.update(0.5);
  assert.equal(q.shown(), 5);
  assert.equal(q.update(1.4), false);
  assert.equal(q.update(0.2), true);
  assert.equal(q.current().text, 'second');
  assert.equal(q.shown(), 0);
  q.clear();
  assert.equal(q.current(), null);
  q.push('x', '', 1);
  assert.equal(q.current(), null, 'empty lines are dropped');
});

test('crosshair gap follows the spread, sprint adds 10, clamped 4…70 in half pixels', () => {
  const base = L.crosshairGap(0, 74, 720);
  assert.equal(base, 4);
  const g = L.crosshairGap(0.02, 74, 720);
  const expected = (Math.tan(0.02) / Math.tan((74 * Math.PI) / 360)) * 360 + 4;
  near(g, Math.round(expected * 2) / 2);
  assert.equal(L.crosshairGap(0.02, 74, 720, true), Math.round((expected + 10) * 2) / 2);
  assert.equal(L.crosshairGap(0.5, 74, 720), 70);
  assert.equal(L.crosshairGap(undefined, 74, 720), L.crosshairGap(L.DEFAULT_SPREAD, 74, 720));
  assert.equal(L.crosshairGap(0.02, 74, 720) % 0.5, 0);
});

test('hit marker tiers and pose', () => {
  assert.equal(L.hitTier({ killed: true, part: 'head' }), 'kill');
  assert.equal(L.hitTier({ part: 'head' }), 'head');
  assert.equal(L.hitTier({ part: 'body' }), 'hit');
  assert.equal(L.HIT_TIERS.kill.secs, 0.42);
  assert.deepEqual(L.hitMarkerPose(0, 1.5), { scale: 1.5, opacity: 1 });
  near(L.hitMarkerPose(0.35, 1.5).scale, 1);
  assert.equal(L.hitMarkerPose(1, 1.5).opacity, 0);
  assert.ok(L.hitMarkerPose(0.7, 1.15).opacity < 1);
});

test('banner pose: fades in, flickers at 14 %, solid 20–82 %, out', () => {
  assert.equal(L.bannerPose(0).opacity, 0);
  near(L.bannerPose(0.04).opacity, 0.5);
  near(L.bannerPose(0.14).opacity, 0.35);
  assert.equal(L.bannerPose(0.5).opacity, 1);
  assert.equal(L.bannerPose(0.5).spread, 0);
  assert.ok(L.bannerPose(0.05).spread > 0);
  near(L.bannerPose(0.91).opacity, 0.5);
  assert.equal(L.bannerPose(1).opacity, 0);
});

test('screen bearing: ahead is 0, right is +90°, behind is ±180°', () => {
  // Player at origin facing north (yaw 0, forward −Z).
  near(L.screenBearing(0, -10, 0, 0, 0), 0);
  near(L.screenBearing(10, 0, 0, 0, 0), Math.PI / 2);
  near(Math.abs(L.screenBearing(0, 10, 0, 0, 0)), Math.PI);
  // Turned left 90° (yaw +π/2, now facing west): something north is now on the right.
  near(L.screenBearing(0, -10, 0, 0, Math.PI / 2), Math.PI / 2);
});

test('damage arc opacity: solid, then a 0.6 s fade in 0.05 steps', () => {
  assert.equal(L.arcOpacity(1.5), 1);
  assert.equal(L.arcOpacity(0.6), 1);
  assert.equal(L.arcOpacity(0.3), 0.5);
  assert.equal(L.arcOpacity(0), 0);
  assert.equal(L.arcOpacity(0.31) * 20 % 1, 0);
});

test('world markers clamp to the screen rectangle and mirror when behind', () => {
  assert.deepEqual(L.clampMarker(0.2, -0.3, false), { x: 0.2, y: -0.3, off: false });
  const r = L.clampMarker(2, 0, false);
  assert.equal(r.off, true);
  near(r.x, 0.9);
  const b = L.clampMarker(0.3, 0.1, true); // behind and slightly right → mirrored to the left
  assert.equal(b.off, true);
  assert.ok(b.x < 0);
  const dead = L.clampMarker(0, 0, true);
  near(dead.y, -0.82);
  const low = L.clampMarker(0, -2, false, 0.9, 0.82, undefined, 0.5); // below: stops above the weapon bar
  near(low.y, -0.5);
  const high = L.clampMarker(0, 2, false, 0.9, 0.82, undefined, 0.5);
  near(high.y, 0.82);
  assert.equal(L.markerOverAim(0.05, 0.05), true);
  assert.equal(L.markerOverAim(0.5, 0), false);
});

test('minimap: turns with the player, pins to the rim', () => {
  const p = L.toMap(0, -10, 0, 2); // 10 m north, facing north → straight up
  near(p.x, 0);
  near(p.y, -20);
  const q = L.toMap(0, -10, Math.PI / 2, 2); // facing west: north is to the right
  near(q.x, 20);
  near(q.y, 0, 1e-9);
  const pin = { x: 300, y: 0 };
  assert.equal(L.pinToRim(pin, 50), true);
  near(pin.x, 50);
  const inside = { x: 10, y: 10 };
  assert.equal(L.pinToRim(inside, 50), false);
});

test('minimap: enemies show while engaged or for 2 s after firing', () => {
  assert.equal(L.enemyOnMap({ alive: true, state: 'engage' }, 10), true);
  assert.equal(L.enemyOnMap({ alive: true, state: 'patrol' }, 10), false);
  assert.equal(L.enemyOnMap({ alive: true, state: 'patrol' }, 10, 8.5), true);
  assert.equal(L.enemyOnMap({ alive: true, state: 'patrol' }, 10, 7), false);
  assert.equal(L.enemyOnMap({ alive: false, state: 'engage' }, 10), false);
});

test('minimap plan: walls, cover and what is left out', () => {
  const box = (y0, y1, extra) => ({ min: { x: 0, y: y0, z: 0 }, max: { x: 1, y: y1, z: 1 }, ...extra });
  assert.equal(L.planKind(box(0, 6)), 'wall');
  assert.equal(L.planKind(box(0, 1)), 'cover');
  assert.equal(L.planKind(box(0, 0.15)), null);
  assert.equal(L.planKind(box(6, 7)), null);
  assert.equal(L.planKind(box(0, 6, { playerOnly: true })), null);
  assert.equal(L.planKind(box(0, 1, { tag: 'explosive' })), null);
});

test('zone band names', () => {
  assert.equal(L.zoneLabel('lot', -20, copy.hud.zones), copy.hud.zones.cage);
  assert.equal(L.zoneLabel('lot', 20, copy.hud.zones), copy.hud.zones.lot);
  assert.equal(L.zoneLabel('nowhere', 0, copy.hud.zones), copy.hud.zones.avenue);
});

test('ammo: low at 27 %, cue lines per device', () => {
  assert.equal(L.lowAmmo(9, 30), true);
  assert.equal(L.lowAmmo(10, 30), false);
  const g = { reload: 'R', swap: 'Q' };
  assert.deepEqual(L.cueLine('reload', g, 'kbm', copy.hud.cue), { text: 'R — Reload', alarm: true });
  assert.deepEqual(L.cueLine('reload', g, 'touch', copy.hud.cue), { text: 'Reload', alarm: true });
  assert.equal(L.cueLine('empty', g, 'kbm', copy.hud.cue).text, 'Empty — Q for the next gun');
  assert.equal(L.cueLine('empty', g, 'touch', copy.hud.cue).text, copy.hud.cue.emptyTouch);
  assert.equal(L.cueLine('low', g, 'kbm', copy.hud.cue).alarm, false);
  assert.equal(L.cueLine('', g, 'kbm', copy.hud.cue).text, '');
});

test('health view: ceil, share, critical at 3 segments or fewer', () => {
  assert.deepEqual(L.healthView(100, 100), { value: 100, fill: 1, critical: false });
  assert.equal(L.healthView(30.2, 100).critical, false);
  assert.equal(L.healthView(30, 100).critical, true);
  assert.equal(L.healthView(0, 100).critical, true);
  assert.equal(L.healthView(57.3, 100).value, 58);
});

test('kill feed: four lines, newest last, 4.2 s life, fades its last 0.6 s', () => {
  const f = L.createFeed();
  for (let i = 0; i < 6; i++) f.push(`line ${i}`, '', 'chopper');
  assert.equal(f.lines.length, 4);
  assert.equal(f.lines[3].text, 'line 5');
  assert.equal(f.lines[0].weapon, 'chopper');
  const v = f.version();
  f.update(3.9);
  assert.equal(f.version(), v, 'fading is not a change');
  assert.equal(f.opacity(f.lines[0]), 0.5);
  f.update(0.4);
  assert.equal(f.lines.length, 0);
  assert.notEqual(f.version(), v);
});

test('menu focus wraps; sliders step and clamp; ratings', () => {
  assert.equal(L.nextFocus(3, -1, 1), 0);
  assert.equal(L.nextFocus(3, -1, -1), 2);
  assert.equal(L.nextFocus(3, 2, 1), 0);
  assert.equal(L.nextFocus(0, 0, 1), -1);
  assert.equal(L.nudgeSlider(95, 1, { min: 0, max: 100, padStep: 5 }), 100);
  assert.equal(L.nudgeSlider(1, -1, { min: 0.2, max: 3, padStep: 0.1 }), 0.9);
  assert.equal(L.ratingName(5, text.ratings), 'Diamond');
  assert.equal(L.ratingName(9, text.ratings), 'Diamond');
  assert.equal(L.ratingName(-1, text.ratings), 'Demo');
});

test('card stats per mode', () => {
  const labels = text.cards.dead.stats;
  const m = L.deathStats({ mode: 'mission', time: 65, reels: 2, total: 3 }, labels);
  assert.deepEqual(m[0], [labels.time, '1:05']);
  assert.deepEqual(m[1], [labels.reels, '2/3']);
  const h = L.deathStats({ mode: 'holdout', time: 10, wave: 4, kills: 20, score: 12345, best: 12345, newBest: true }, labels);
  assert.equal(h.length, 5);
  assert.deepEqual(h[3], [labels.score, '12,345']);
  assert.equal(h[4][2], 'new');
  const d = L.debriefStats({ time: 250, accuracy: null, kills: 3, retries: 0 }, text.cards.debrief.stats);
  assert.deepEqual(d[1], [text.cards.debrief.stats.accuracy, '—']);
});
