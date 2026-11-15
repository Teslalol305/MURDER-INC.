// The whole stubbed vertical slice, played from the title screen by a small bot that only uses what a
// player has: keys, mouse movement, mouse buttons and clicks on the menu cards. It reads the game state
// through window.__G to decide what to do and to check what happened.
//
//   node build.mjs --dev --out=dist/dev-foundation.html
//   node tools/shot.cjs dist/dev-foundation.html --params "q=low" --timeout 600 \
//        --scenario tools/scenarios/foundation-slice.cjs
//
// Title → start → wall slide → stair, deck, jump off → shoot a Vulture → get hit, recover → die, retry →
// three reels with their waves, the refusal at the truck, extraction, debrief → redeploy → pause and
// resume four ways → Hold the Block: a wave cleared, resupply, death, best score.
//
// Prints one line per check and fails the run if any check fails. Screenshots go to shots/foundation/.
// Written against the STUB modules (testbed level, dummy enemies, stub HUD and menu markup): keep every
// optional module stubbed when running it. The few places where the script acts as a director instead of
// a player (clearing or spawning enemies) are marked DIRECTOR.

'use strict';

const OUT = 'shots/foundation/slice-';
const DT = 0.0333;
const MOUSE_RATE = 0.0021; // radians per pixel at sensitivity 1 (stub input)
const ADS_LOOK = 0.6; // look-rate multiplier at full aim (stub player)
const EAST = -Math.PI / 2;

const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
const f = (n) => Math.round(n * 100) / 100;

/** Runs in the page once: an event recorder and the bot's senses. */
function install() {
  const G = window.__G;
  const V = G.THREE.Vector3;
  const r = (n) => Math.round(n * 1000) / 1000;
  const brief = (v) => {
    if (v && v.isVector3) return [r(v.x), r(v.y), r(v.z)];
    if (v && typeof v === 'object') return v.type ? `${v.type}${v.id ? `#${v.id}` : ''}` : '[object]';
    return typeof v === 'number' ? r(v) : v;
  };

  // Every event that goes over the bus: how often, the last payload, and a running sum of player damage.
  // Also every line the game hands to hud.message(): those time out, the record does not.
  const rec = (window.__rec = { count: {}, last: {}, damage: 0, states: [], messages: [] });
  const message = G.hud.message;
  G.hud.message = (text, secs) => {
    rec.messages.push(text);
    return message(text, secs);
  };
  const emit = G.events.emit;
  G.events.emit = (name, payload) => {
    rec.count[name] = (rec.count[name] || 0) + 1;
    if (name === 'impact' && payload.from === 'player') rec.count['impact (player)'] = (rec.count['impact (player)'] || 0) + 1;
    const flat = {};
    for (const key in payload || {}) flat[key] = brief(payload[key]);
    rec.last[name] = flat;
    if (name === 'player:hit') rec.damage += payload.amount;
    if (name === 'game:state') rec.states.push(payload.state);
    // Ammo and health at the last kill and right after a cleared wave: the resupply is the difference.
    if (name === 'enemy:killed') rec.atKill = { reserve: G.weapon.reserve, health: G.player.health };
    if (name === 'objective:done') rec.atDone = { reserve: G.weapon.reserve, health: G.player.health };
    return emit(name, payload);
  };

  const eye = new V();
  const aim = new V();
  const aimPoint = (e, out, head) => out.set(e.pos.x, e.pos.y + (e.type === 'goon' ? (head ? 1.63 : 0.85) : 0), e.pos.z);
  const living = () => G.enemies.list.filter((e) => e.alive);

  window.__bot = {
    /** Everything the checks look at, in one round trip. */
    snap() {
      const p = G.player;
      const hud = document.querySelector('.hud-stub');
      const card = document.querySelector('.menu-stub');
      const prompt = hud.children[2];
      const place = card.nextElementSibling;
      return {
        state: G.game.state,
        mode: G.game.mode,
        run: { ...G.game.run },
        x: p.pos.x, y: p.pos.y, z: p.pos.z, yaw: p.yaw, pitch: p.pitch,
        health: p.health, alive: p.alive, onGround: p.onGround, speed: p.speed, ads: p.ads,
        enabled: p.enabled, invulnerable: p.invulnerable, surface: p.surface,
        mag: G.weapon.mag, reserve: G.weapon.reserve, weapon: G.weapon.state, cue: G.weapon.cue,
        stats: { ...G.combat.stats },
        alive_: G.enemies.aliveCount(),
        goons: G.enemies.countByType('goon'),
        buzzards: G.enemies.countByType('buzzard'),
        engaged: living().filter((e) => e.state === 'engage').length,
        locked: G.input.locked,
        screen: G.menus.screen,
        post: { ...G.render.post },
        cam: [r(G.camera.position.x), r(G.camera.position.y), r(G.camera.position.z)],
        fov: G.camera.fov,
        hud: hud.hidden ? null : hud.firstChild.textContent,
        prompt: hud.hidden || prompt.hidden ? null : prompt.firstChild.textContent,
        fill: prompt.lastChild.firstChild.style.transform,
        card: card.hidden ? null : card.textContent,
        place: place.hidden ? null : place.textContent,
        count: { ...window.__rec.count },
        damage: window.__rec.damage,
        errors: window.__errors.length,
      };
    },

    /** Nearest living enemy the player can see from where he stands: where to point the gun. */
    target(range) {
      eye.copy(G.player.eye);
      let best = null;
      for (const e of living()) {
        // Heads up close, the bigger body further out.
        const d0 = e.pos.distanceTo(G.player.pos);
        aimPoint(e, aim, d0 < 22);
        const dist = aim.distanceTo(eye);
        if (dist > range || (best && dist >= best.dist) || !G.physics.lineOfSight(eye, aim)) continue;
        const dx = aim.x - eye.x;
        const dy = aim.y - eye.y;
        const dz = aim.z - eye.z;
        best = { id: e.id, type: e.type, dist, yaw: Math.atan2(-dx, -dz), pitch: Math.atan2(dy, Math.hypot(dx, dz)) };
      }
      return best;
    },

    /**
     * A walkable spot with a clear shot at a living enemy no further than `range` from it, as a nav path
     * from where the player stands. Enemies are tried nearest first; null when nobody can be reached.
     */
    hunt(range) {
      const from = G.player.pos;
      const b = G.level.bounds;
      // The bot stops within half a metre of a spot: the shot has to be there from anywhere that close.
      const sees = (x, z) => G.physics.lineOfSight(eye.set(x, 1.68, z), aim);
      const open = (x, z) => sees(x, z) && sees(x - 0.5, z) && sees(x + 0.5, z) && sees(x, z - 0.5) && sees(x, z + 0.5);
      for (const prey of living().sort((p, q) => p.pos.distanceTo(from) - q.pos.distanceTo(from))) {
        aimPoint(prey, aim, false);
        const spots = [];
        for (let x = b.minX + 1; x < b.maxX; x += 1.5) {
          for (let z = b.minZ + 1; z < b.maxZ; z += 1.5) {
            const d = Math.hypot(x - aim.x, 1.68 - aim.y, z - aim.z);
            const near = Math.hypot(x - from.x, z - from.z);
            if (d < 5 || d > range || near < 1 || !G.physics.nav.isWalkable(x, z) || !open(x, z)) continue;
            spots.push({ x, z, near });
          }
        }
        spots.sort((p, q) => p.near - q.near);
        for (const spot of spots.slice(0, 12)) {
          const path = G.physics.nav.findPath(from, spot);
          if (path) return path.map((v) => [v.x, v.z]);
        }
      }
      return null;
    },

    path(x, z) {
      const path = G.physics.nav.findPath(G.player.pos, { x, z });
      return path && path.map((v) => [v.x, v.z]);
    },
  };
}

module.exports = async (page, h) => {
  let checks = 0;
  let failed = 0;
  /** Printed as they happen, so a run that stops half-way still shows how far it got. */
  const check = (name, ok, detail = '') => {
    console.log(`${ok ? 'ok  ' : 'FAIL'}  ${name}${detail ? `  (${detail})` : ''}`);
    checks++;
    if (!ok) failed++;
    return ok;
  };
  const snap = () => h.eval(() => window.__bot.snap());
  const view = page.viewportSize();
  const park = () => page.mouse.move(view.width / 2, view.height / 2);
  const tap = async (code) => {
    await h.key(code, true);
    await h.skip(1);
    await h.key(code, false);
  };
  /** Clicks the n-th button of the menu card, then puts the pointer back where firing expects it. */
  const press = async (n) => {
    await h.click(`.menu-stub button:nth-of-type(${n})`);
    await page.waitForFunction(() => __G.game.state === 'title' || __G.input.locked, null, { timeout: 5000 });
    await park();
    await h.skip(1);
  };
  const shot = async (name) => {
    await h.frames(1);
    await h.shot(`${OUT}${name}.png`);
  };

  // ---- the bot's hands ------------------------------------------------------------------------

  /** Turns the view to (yaw, pitch) with mouse movement, in events small enough to pass the glitch filter. */
  async function look(yaw, pitch = 0) {
    const s = await h.eval(() => ({ yaw: __G.player.yaw, pitch: __G.player.pitch, ads: __G.player.ads, sens: __G.input.sensitivity }));
    const k = MOUSE_RATE * s.sens * (1 + (ADS_LOOK - 1) * s.ads);
    let dx = Math.round(wrap(s.yaw - yaw) / k);
    let dy = Math.round((s.pitch - pitch) / k);
    while (dx !== 0 || dy !== 0) {
      const sx = clamp(dx, -300, 300);
      const sy = clamp(dy, -300, 300);
      await h.mouse(sx, sy);
      dx -= sx;
      dy -= sy;
    }
    await h.skip(1);
  }

  async function reloadIfLow(below = 10) {
    const s = await snap();
    if (s.mag >= below || s.reserve <= 0) return;
    await tap('KeyR');
    await h.skip(Math.ceil(2.8 / DT));
  }

  /** Shoots whatever is in sight, nearest first, until nothing is. Returns the number of bursts fired. */
  async function engage(range = 60, bursts = 60) {
    let fired = 0;
    for (; fired < bursts; fired++) {
      const t = await h.eval((r) => window.__bot.target(r), range);
      if (!t) break;
      await look(t.yaw, t.pitch);
      await h.key('Mouse0', true);
      await h.skip(t.dist < 22 ? 6 : 10);
      await h.key('Mouse0', false);
      await h.skip(1);
      await reloadIfLow();
      if (!(await snap()).alive) throw new Error('the bot was killed in a firefight');
    }
    return fired;
  }

  /** Holds W toward (x, z) until within `tol`, steering every few frames. Stops to fight when `fight` is set. */
  async function walkTo(x, z, { sprint = true, tol = 0.45, fight = false, limit = 900 } = {}) {
    const hold = async (down) => {
      await h.key('KeyW', down);
      if (sprint) await h.key('ShiftLeft', down);
    };
    await hold(true);
    for (let frames = 0; ; ) {
      const s = await h.eval((r) => {
        const p = __G.player;
        return { x: p.pos.x, z: p.pos.z, alive: p.alive, over: __G.game.state === 'complete', threat: r > 0 && !!window.__bot.target(r) };
      }, fight ? 40 : 0);
      if (!s.alive) throw new Error('the bot was killed on the way');
      if (s.over) break; // walked into the extraction zone
      const dx = x - s.x;
      const dz = z - s.z;
      const d = Math.hypot(dx, dz);
      if (d <= tol) break;
      if (frames > limit) throw new Error(`walkTo(${f(x)}, ${f(z)}) is stuck at ${f(s.x)}, ${f(s.z)}`);
      if (s.threat) {
        await hold(false);
        await engage(40);
        await hold(true);
      }
      await look(Math.atan2(-dx, -dz), 0);
      const step = (sprint ? 6.4 : 3.8) * DT;
      const n = clamp(Math.floor((d - tol * 0.5) / step), 1, 8);
      await h.skip(n);
      frames += n + 1;
    }
    await hold(false);
    await h.skip(8); // come to rest
  }

  /** Follows the nav path to (x, z); the path ends on the reachable cell nearest to the goal. */
  async function goTo(x, z, opts = {}) {
    const path = await h.eval(([px, pz]) => window.__bot.path(px, pz), [x, z]);
    if (!path) throw new Error(`no path to ${x}, ${z}`);
    for (let i = 1; i < path.length; i++) {
      await walkTo(path[i][0], path[i][1], { ...opts, tol: i === path.length - 1 ? opts.tol || 0.45 : 0.4 });
    }
  }

  /** Finds and shoots every living enemy: fires at what is in view, else walks to a spot with a shot. */
  async function clearBlock(limit = 40) {
    for (let i = 0; i < limit; i++) {
      await engage();
      if ((await snap()).alive_ === 0) return true;
      const path = await h.eval(() => window.__bot.hunt(55));
      if (!path) return false;
      for (let k = 1; k < path.length; k++) await walkTo(path[k][0], path[k][1], { fight: true, tol: 0.4 });
    }
    return false;
  }

  // ---- 0. title ---------------------------------------------------------------------------------

  await h.eval(install);
  let s = await snap();
  check('boots to the title screen', s.state === 'title' && s.screen === 'title' && s.hud === null && !s.enabled && s.alive_ === 0, s.state);
  check('the title card carries the wordmark and the start button', /MURDER INC\./.test(s.card) && /Hit the block/.test(s.card));
  const cam0 = s.cam;
  await h.frames(20);
  await h.shot(`${OUT}00-title.png`);
  s = await snap();
  check('the camera flies the block behind the title', s.cam.join() !== cam0.join() && s.fov === 50, `${cam0} → ${s.cam}`);

  // ---- 1. start: intro, location card, radio, patrol --------------------------------------------

  await h.click('.menu-stub button:nth-of-type(1)');
  await page.waitForFunction(() => __G.input.locked || __G.input.mode === 'drag', null, { timeout: 5000 }).catch(() => {});
  await h.skip(1);
  s = await snap();
  check(
    'the start button begins a Story run with an intro',
    s.state === 'intro' && s.mode === 'mission' && s.screen === 'none' && s.hud !== null && s.enabled && s.count['game:reset'] === 1 && s.count['ui:click'] === 1,
    `${s.state}, fade ${f(s.post.fade)}`,
  );
  check('the mouse is captured', s.locked);
  check('Rule stands at the start, facing east', Math.abs(s.x + 40) < 1e-6 && Math.abs(s.z - 8.6) < 1e-6 && Math.abs(s.yaw - EAST) < 1e-6, `${f(s.x)}, ${f(s.z)}, yaw ${f(s.yaw)}`);
  check('a patrol of 2 Buzzards and 4 Goons is out, unaware', s.buzzards === 2 && s.goons === 4 && s.engaged === 0 && s.count['enemy:spawn'] === 6, `${s.buzzards} + ${s.goons}, ${s.engaged} engaged`);
  check('the HUD shows the objective and the reel count', /Take back the three master reels/.test(s.hud) && /reels\s+0\/3/.test(s.hud) && /\[1\] Reel 1/.test(s.hud));
  await park();
  await h.skip(14);
  s = await snap();
  check('the location card is up during the intro', /Hollis, Queens/.test(s.place || ''), s.place || 'hidden');
  await h.skip(15);
  await shot('01-intro');
  s = await snap();
  check('the Vault comes on the radio', s.count['radio:line'] === 1 && /IPX VAULT: Rule, it's the Vault/.test(s.hud), JSON.stringify(await h.eval(() => window.__rec.last['radio:line'])));
  check('the screen is fading in', s.post.fade > 0 && s.post.fade < 1, `fade ${f(s.post.fade)}`);
  await h.skip(45);
  s = await snap();
  check('2.4 s later the run is live', s.state === 'playing' && s.place === null && s.post.fade === 0, `${s.state}, fade ${f(s.post.fade)}`);
  await look(EAST, 0);
  await shot('02-start');

  // ---- 2. into a wall at an angle: slide along it ------------------------------------------------

  await look(-Math.PI * 0.75, 0); // south-east, toward the station front at z = 12
  await h.key('KeyW', true);
  await h.skip(75);
  s = await snap();
  await h.key('KeyW', false);
  check(
    'walking into the station wall at 45° slides along it',
    Math.abs(s.z - (12 - 0.32)) < 0.005 && s.x > -36 && Math.abs(s.speed - 3.8 * Math.SQRT1_2) < 0.05,
    `x ${f(s.x)}, z ${f(s.z)}, speed ${f(s.speed)}`,
  );
  await h.skip(10);

  // ---- 3. the stair, the deck, and off it again --------------------------------------------------

  await goTo(-1.9, 10.7, { tol: 0.3 });
  await look(EAST, 0);
  await h.key('KeyW', true);
  let airborne = 0;
  let lastY = 0;
  let wentDown = false;
  for (let i = 0; i < 30; i++) {
    await h.skip(2);
    s = await snap();
    if (!s.onGround) airborne++;
    if (s.y < lastY - 1e-6) wentDown = true;
    lastY = s.y;
  }
  await h.key('KeyW', false);
  await h.skip(8);
  s = await snap();
  check('the stair is walked, not hopped, up to the deck', Math.abs(s.y - 2.8) < 1e-6 && s.x > 2 && airborne === 0 && !wentDown && s.surface === 'wood', `x ${f(s.x)}, y ${f(s.y)}, on ${s.surface}`);
  check('no landing was announced on the way up', !s.count['player:land'] && !s.count['player:jump']);
  await look(1.15, -0.28); // back down the avenue
  await shot('03-deck');

  await walkTo(3.4, 9.2, { sprint: false, tol: 0.3 });
  await look(Math.PI / 2, 0); // west: the open end of the deck
  await h.key('KeyW', true);
  let top = 0;
  let jumped = false;
  for (let i = 0; i < 60; i++) {
    s = await snap();
    top = Math.max(top, s.y);
    if (!jumped && s.x < 2.5) {
      jumped = true;
      await h.key('Space', true);
    }
    if (jumped && s.onGround && s.y === 0) break;
    await h.skip(1);
  }
  await h.key('Space', false);
  await h.key('KeyW', false);
  await h.skip(8);
  s = await snap();
  const land = await h.eval(() => window.__rec.last['player:land']);
  check(
    'a running jump off the deck: one jump, one landing, no fall damage from 3.8 m',
    s.count['player:jump'] === 1 && s.count['player:land'] === 1 && top > 3.6 && top < 3.85 && s.y === 0 && s.health === 100 && land.speed > 11.5 && land.speed < 13,
    `apex ${f(top)}, landed at ${f(land.speed)} m/s on ${land.surface}`,
  );

  // ---- 4. shoot a Vulture until it drops ---------------------------------------------------------

  let before = await snap();
  let path = await h.eval(() => window.__bot.hunt(30));
  for (let k = 1; path && k < path.length; k++) await walkTo(path[k][0], path[k][1], { tol: 0.4 });
  let t = await h.eval(() => window.__bot.target(60));
  if (!check('a Vulture is in sight', !!t, t ? `${t.type} at ${f(t.dist)} m` : 'none')) throw new Error('the bot found nobody to shoot');
  await look(t.yaw, t.pitch);
  await h.key('Mouse0', true);
  await h.frames(3);
  await h.shot(`${OUT}04-firing.png`);
  await h.key('Mouse0', false);
  for (let i = 0; i < 20 && (await snap()).stats.kills === 0; i++) await engage(60, 1);
  await h.skip(4); // the stub HUD rebuilds its text ten times a second
  s = await snap();
  const kill = await h.eval(() => window.__rec.last['enemy:killed']);
  const d = (name) => (s.count[name] || 0) - (before.count[name] || 0);
  check(
    'firing: every round is a weapon:fire and a counted shot',
    s.stats.shots > 0 && s.stats.shots === d('weapon:fire') && s.mag + s.stats.shots === 30 + (150 - s.reserve),
    `${s.stats.shots} shots, magazine ${s.mag}`,
  );
  check(
    'hits: player:hitEnemy, enemy:hit and combat.stats.hits agree; a round makes one impact at most',
    s.stats.hits > 0 && s.stats.hits === d('player:hitEnemy') && d('enemy:hit') === s.stats.hits && d('impact (player)') <= s.stats.shots && d('impact (player)') >= s.stats.hits,
    `${s.stats.hits} hits, ${d('impact (player)')} impacts of ${s.stats.shots} rounds`,
  );
  check(
    'the kill: enemy:killed by the player with the Chopper, counted once',
    s.stats.kills === 1 && d('enemy:killed') === 1 && kill.byPlayer === true && kill.weapon === 'chopper' && s.stats.headshots === (kill.part === 'head' ? 1 : 0) && s.run.kills === 1,
    JSON.stringify(kill),
  );
  check('the block wakes up: an alert and the contact line', d('enemy:alert') >= 1 && /They made you/.test(JSON.stringify(await h.eval(() => window.__rec.last['radio:line']))) && /down/.test(s.hud), `${d('enemy:alert')} alerts`);

  // ---- 5. get shot, then recover out of fire -----------------------------------------------------

  path = await h.eval(() => window.__bot.hunt(13)); // close enough that they do not miss for long
  for (let k = 1; path && k < path.length; k++) await walkTo(path[k][0], path[k][1], { tol: 0.4 });
  s = await snap();
  const hitsBefore = s.count['player:hit'] || 0;
  for (let i = 0; i < 600 && (s.count['player:hit'] || 0) === hitsBefore; i++) {
    await h.skip(2);
    s = await snap();
  }
  await h.skip(1); // the player writes the hit to render.post on its next update
  s = await snap();
  const flash = s.post.damage;
  check(
    'standing in the open gets Rule shot, and the screen edge flashes red',
    s.health < 100 && s.count['player:hit'] > hitsBefore && s.count['enemy:fire'] >= 1 && s.count['enemy:telegraph'] >= 1 && flash > 0.3,
    `health ${f(s.health)}, ${s.count['enemy:fire']} shots at him, red flash ${f(flash)}`,
  );
  await shot('05-hit');
  await h.eval(() => __G.enemies.clear()); // DIRECTOR: silence the block so the regeneration can be timed
  s = await snap();
  const hurt = s.health;
  check('combat.stats.damageTaken is the sum of every player:hit', Math.abs(s.stats.damageTaken - s.damage) < 1e-9 && Math.abs(100 - hurt - s.damage) < 1e-9, `${f(s.damage)} taken`);
  await h.skip(Math.floor(5.0 / DT));
  s = await snap();
  const waited = s.health;
  await h.skip(Math.ceil(0.6 / DT + (100 - hurt) / 16 / DT) + 2);
  s = await snap();
  check('health holds for the 5.5 s delay, then climbs back to 100', waited === hurt && s.health === 100, `${f(hurt)} → ${f(waited)} → ${f(s.health)}`);

  // ---- 6. die, read the card, run it back --------------------------------------------------------

  await h.eval(() => {
    // DIRECTOR: six alerted Goons in a ring around Rule, close enough not to miss.
    const p = __G.player.pos;
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * Math.PI * 2;
      __G.enemies.spawn('goon', new __G.THREE.Vector3(p.x + Math.cos(a) * 2.5, 0, p.z + Math.sin(a) * 2.5), { alerted: true });
    }
  });
  for (let i = 0; i < 300 && s.alive; i++) {
    await h.skip(5);
    s = await snap();
  }
  await page.waitForFunction(() => !__G.input.locked, null, { timeout: 5000 }).catch(() => {});
  s = await snap();
  await h.skip(2); // the weapon lowers on its next update
  s = await snap();
  check(
    'six Goons at arm\'s length kill him: player:dead, state dead, HUD off, gun down, mouse released',
    !s.alive && s.health === 0 && s.count['player:dead'] === 1 && s.state === 'dead' && s.hud === null && s.weapon === 'lowered' && !s.locked,
    `${s.state}, weapon ${s.weapon}`,
  );
  check('no card yet', s.screen === 'none' && s.card === null);
  await h.skip(Math.ceil(1.5 / DT));
  await h.frames(20);
  await h.shot(`${OUT}06-dead.png`);
  s = await snap();
  check(
    'the death card arrives after 1.5 s over a drained, darkened screen',
    s.screen === 'dead' && /Lights out/.test(s.card) && /Reels recovered\s+0\/3/.test(s.card) && /Time on the block\s+\d:\d\d/.test(s.card) && s.post.saturation < 0.3 && s.post.fade > 0.4,
    `saturation ${f(s.post.saturation)}, fade ${f(s.post.fade)}`,
  );
  check('the death camera lies on the ground', s.cam[1] < 0.6, `camera y ${s.cam[1]}`);
  const radioBefore = s.count['radio:line'];
  await press(1);
  s = await snap();
  check(
    '"Run it back" resets the whole run: quick intro, retry counted, full health and ammo, fresh patrol',
    s.state === 'intro' && s.run.retries === 1 && s.run.time === 0 && s.alive && s.health === 100 && s.mag === 30 && s.reserve === 150 &&
      s.stats.shots === 0 && s.stats.kills === 0 && s.stats.damageTaken === 0 && s.alive_ === 6 && s.engaged === 0 && Math.abs(s.x + 40) < 1e-6 && s.locked && s.post.saturation === 1,
    `${s.state}, retries ${s.run.retries}, ${s.alive_} enemies`,
  );
  await h.skip(Math.ceil(1.1 / DT) + 1);
  s = await snap();
  check('the quick intro takes 1.1 s and skips the card and the radio', s.state === 'playing' && s.place === null && s.count['radio:line'] === radioBefore && s.post.fade === 0, s.state);

  // ---- 7. reel 1 and its reinforcement wave ------------------------------------------------------

  const reels = await h.eval(() => __G.level.objectives.map((o) => [o.pos.x, o.pos.z]));
  const truck = await h.eval(() => [__G.level.extraction.pos.x, __G.level.extraction.pos.z]);
  const faceReel = async (i) => {
    const p = await snap();
    await look(Math.atan2(-(reels[i][0] - p.x), -(reels[i][1] - p.z)), -0.5);
  };

  await goTo(reels[0][0], reels[0][1]); // without a fight: the wave should run into the alive cap
  await faceReel(0);
  await h.skip(2);
  s = await snap();
  check('at reel 1 the prompt offers the grab', s.prompt === 'Hold E — Grab reel 1', s.prompt || 'no prompt');
  before = s;
  await h.key('KeyE', true);
  await h.skip(30);
  await h.key('KeyE', false);
  s = await snap();
  const partial = (s.count['objective:progress'] || 0) - (before.count['objective:progress'] || 0);
  const half = await h.eval(() => window.__rec.last['objective:progress']);
  await h.skip(12);
  s = await snap();
  check('letting go early loses the progress', partial === 30 && Math.abs(half.t - 30 * DT / 2.4) < 0.01 && half.id === 'reel1' && /scaleX\(0\)/.test(s.fill) && s.run.reels === 0, `${partial} progress events to ${f(half.t)}, then ${s.fill}`);
  before = s;
  await h.key('KeyE', true);
  await h.skip(40);
  await shot('07-grabbing');
  await h.skip(34);
  await h.key('KeyE', false);
  await h.skip(4);
  s = await snap();
  let done = await h.eval(() => window.__rec.last['objective:done']);
  check(
    'holding E for 2.4 s secures reel 1',
    s.run.reels === 1 && done.id === 'reel1' && done.index === 1 && done.total === 3 && s.prompt === null && /reels\s+1\/3/.test(s.hud) && /Two reels left/.test(s.hud) && !/\[1\] Reel 1/.test(s.hud),
    JSON.stringify(done),
  );
  check('the Vault calls it and a contact banner names a direction', /One reel back in your hands/.test(s.hud) && /warn\s+Contact — [A-Z-]+/.test(s.hud), (s.hud.match(/warn.*/) || [''])[0]);

  // Boss wave 1 is 2 Buzzards + 5 Goons, one every 0.85 s from 1.6 s on, held at the alive cap of 11.
  const spawned0 = s.count['enemy:spawn'];
  const alive0 = s.alive_;
  let most = 0;
  let firstAt = -1;
  for (let i = 0; i < 9 / DT; i += 3) {
    await h.skip(3);
    s = await snap();
    most = Math.max(most, s.alive_);
    if (firstAt < 0 && s.count['enemy:spawn'] > spawned0) firstAt = (i + 3) * DT;
  }
  const expected = Math.min(7, 11 - alive0);
  check(
    'the wave arrives alerted, staggered, and stops at the alive cap',
    firstAt > 1.2 && firstAt < 1.8 && most <= 11 && s.count['enemy:spawn'] - spawned0 === expected && s.engaged >= expected,
    `first after ${f(firstAt)} s, ${s.count['enemy:spawn'] - spawned0} of 7 arrived on top of ${alive0}, at most ${most} alive`,
  );
  await look(EAST, 0.1);
  await shot('08-wave');
  check('the bot clears the block', await clearBlock(), `${(await snap()).alive_} left`);
  await h.skip(Math.ceil(3 / DT));
  check('the rest of the wave arrived once there was room, and was dealt with', (await snap()).count['enemy:spawn'] - spawned0 === 7 && (await clearBlock()));

  // ---- 8. reel 2 in the shop, the refusal at the truck, reel 3 in the cage, extraction -----------

  const grab = async (i) => {
    await goTo(reels[i][0], reels[i][1], { fight: true });
    await engage(45);
    await faceReel(i);
    await h.key('KeyE', true);
    await h.skip(Math.ceil(2.4 / DT) + 2);
    await h.key('KeyE', false);
    await h.skip(4);
  };
  await grab(1);
  s = await snap();
  done = await h.eval(() => window.__rec.last['objective:done']);
  check('reel 2, inside the shop', s.run.reels === 2 && done.id === 'reel2' && done.index === 2 && /Last reel/.test(s.hud) && /Two reels\./.test(s.hud), `at ${f(s.x)}, ${f(s.z)}`);
  await shot('09-shop');
  await h.skip(Math.ceil(10 / DT));
  await clearBlock();

  await goTo(truck[0], truck[1], { fight: true });
  await h.skip(4);
  s = await snap();
  const refusals = await h.eval(() => window.__rec.messages.filter((m) => /Reels still out there/.test(m)));
  check('the truck refuses to roll with a reel still out', s.state === 'playing' && refusals.length >= 1 && !s.count['extraction:reached'], refusals[0] || 'no message');

  await grab(2);
  s = await snap();
  done = await h.eval(() => window.__rec.last['objective:done']);
  check(
    'reel 3, in the cage: all three, the truck is the objective now',
    s.run.reels === 3 && done.index === 3 && s.count['objective:all'] === 1 && /Get to the IPX truck/.test(s.hud) && /\[IPX\] IPX truck/.test(s.hud) && /That's all three/.test(s.hud),
    (s.hud.match(/objective.*/) || [''])[0],
  );
  await goTo(truck[0], truck[1], { fight: true });
  await h.skip(2);
  await page.waitForFunction(() => !__G.input.locked, null, { timeout: 5000 }).catch(() => {});
  s = await snap();
  check(
    'reaching the truck completes the run',
    s.state === 'complete' && s.count['extraction:reached'] === 1 && s.hud === null && !s.enabled && s.invulnerable && !s.locked && s.screen === 'none',
    `${s.state} at ${f(s.x)}, ${f(s.z)}`,
  );
  const points = await h.eval(() => __G.config.flow.ratingPoints(__G.game.run));
  const rating = await h.eval((n) => __G.config.text.ratings[n], points);
  await h.skip(Math.ceil(3.3 / DT));
  await h.frames(2);
  await h.shot(`${OUT}10-debrief.png`);
  s = await snap();
  const accuracy = Math.round((s.run.hits / s.run.shots) * 100);
  check(
    'the debrief card arrives after 3.3 s with the certification and the run\'s numbers',
    s.screen === 'complete' && /The block is yours/.test(s.card) && s.card.includes(`Certification  ${rating}`) && s.card.includes(`Accuracy  ${accuracy} %`) &&
      s.card.includes(`Vultures dropped  ${s.run.kills}`) && s.card.includes('Retries  1') && s.run.kills === s.stats.kills && s.run.kills >= 20,
    `${rating} (${points} points): ${f(s.run.time)} s, ${accuracy} %, ${s.run.kills} dropped`,
  );

  // ---- 9. redeploy, then pause and resume every way there is -------------------------------------

  await press(1);
  s = await snap();
  check('"Run it back" on the debrief redeploys with a clean slate', s.state === 'intro' && s.run.retries === 0 && s.run.reels === 0 && s.alive_ === 6 && !s.invulnerable && s.enabled, `${s.state}, retries ${s.run.retries}`);
  await h.skip(Math.ceil(1.1 / DT) + 5);

  const hover = () => h.eval(() => __G.enemies.list.filter((e) => e.type === 'buzzard').map((e) => e.pos.y).join());
  await tap('Escape');
  await h.skip(1);
  s = await snap();
  const frozen = await hover();
  await h.key('KeyW', true);
  await h.skip(40);
  await h.key('KeyW', false);
  const paused = await snap();
  check(
    'Esc pauses: card up, HUD off, mouse free, nothing moves',
    s.state === 'paused' && s.screen === 'paused' && /Paused/.test(s.card) && s.hud === null && !s.locked && (await hover()) === frozen && paused.x === s.x && paused.run.time === s.run.time,
    s.state,
  );
  await shot('11-paused');
  await tap('KeyP');
  await page.waitForFunction(() => __G.input.locked, null, { timeout: 5000 }).catch(() => {});
  await h.skip(2);
  s = await snap();
  check('P resumes and recaptures the mouse', s.state === 'playing' && s.screen === 'none' && s.locked && (await hover()) !== frozen, s.state);

  await tap('Escape');
  await h.skip(1);
  await press(1);
  s = await snap();
  check('the Resume button does the same', s.state === 'playing' && s.locked && s.run.retries === 0, s.state);

  await h.eval(() => document.exitPointerLock());
  await page.waitForFunction(() => !__G.input.locked, null, { timeout: 5000 }).catch(() => {});
  await h.skip(1);
  s = await snap();
  check('losing the mouse pauses the game', s.state === 'paused', s.state);
  await press(2);
  s = await snap();
  check('"Restart run" starts over and counts a retry', s.state === 'intro' && s.run.retries === 1 && s.run.time === 0, `${s.state}, retries ${s.run.retries}`);

  // ---- 10. Hold the Block ------------------------------------------------------------------------

  await h.eval(() => __G.game.toTitle()); // DIRECTOR: the stub pause card has no way back to the title
  await page.waitForFunction(() => !__G.input.locked, null, { timeout: 5000 }).catch(() => {});
  await h.skip(2);
  s = await snap();
  check('game.toTitle() returns to the title with the block cleared', s.state === 'title' && s.screen === 'title' && s.alive_ === 0 && s.hud === null, s.state);
  await h.click('.menu-stub button:nth-of-type(2)');
  s = await snap();
  const setting = await h.eval(() => [window.__rec.last['settings:change'], __G.settings.get('mode'), localStorage.getItem('murderinc.settings.v1')]);
  check('the mode button stores Hold the Block', /Mode: Hold the Block/.test(s.card) && setting[0].key === 'mode' && setting[0].value === 'holdout' && setting[1] === 'holdout' && /"mode":"holdout"/.test(setting[2]), JSON.stringify(setting[0]));
  await press(1);
  s = await snap();
  check('a holdout run starts empty: no patrol, no reels, standing by', s.mode === 'holdout' && s.state === 'intro' && s.alive_ === 0 && /Vultures inbound/.test(s.hud) && /Stand by/.test(s.hud) && !/\[1\]/.test(s.hud), s.hud.split('\n')[0]);
  await h.skip(Math.ceil(3.5 / DT) + 2);
  s = await snap();
  let wave = await h.eval(() => window.__rec.last['holdout:wave']);
  check('wave 1 is called after 3.5 s: 7 Vultures', s.run.wave === 1 && wave.wave === 1 && wave.count === 7 && /Hold the block/.test(s.hud) && /warn\s+Wave 1 — [A-Z-]+/.test(s.hud), JSON.stringify(wave));
  await h.skip(Math.ceil(8 / DT));
  s = await snap();
  check('3 Buzzards and 4 Goons arrive', s.buzzards === 3 && s.goons === 4, `${s.buzzards} + ${s.goons}`);
  await look(EAST, 0.15);
  await shot('12-holdout');
  await h.key('Mouse0', true); // spend some rounds so the resupply shows
  await h.skip(40);
  await h.key('Mouse0', false);
  await tap('KeyR');
  await h.skip(Math.ceil(2.8 / DT));
  const cleared = await clearBlock();
  await h.skip(4);
  s = await snap();
  done = await h.eval(() => window.__rec.last['objective:done']);
  check(
    'clearing the wave scores it: 3 × 100 + 4 × 150 + 500',
    cleared && done.id === 'wave' && done.index === 1 && s.run.score === 1400 && /Wave 1 · 1,400/.test(s.hud) && /Catch your breath/.test(s.hud) && /Wave 1 down/.test(s.hud),
    `score ${s.run.score}`,
  );
  const supply = await h.eval(() => [window.__rec.atKill, window.__rec.atDone]);
  check(
    'the resupply: 90 rounds for the Chopper (240 at most) and 35 health',
    supply[1].reserve === Math.min(240, supply[0].reserve + 90) && Math.abs(supply[1].health - Math.min(100, supply[0].health + 35)) < 1e-9,
    `reserve ${supply[0].reserve} → ${supply[1].reserve}, health ${f(supply[0].health)} → ${f(supply[1].health)}`,
  );
  let countdown = '';
  for (let i = 0; i < 9 / DT + 4 && s.run.wave === 1; i += 5) {
    await h.skip(5);
    s = await snap();
    const m = /message\s+(Wave 2 in \d)/.exec(s.hud);
    if (m && !countdown.includes(m[1])) countdown += `${m[1]}, `;
  }
  wave = await h.eval(() => window.__rec.last['holdout:wave']);
  check('a 9 s breather with a 3-2-1 countdown, then wave 2 with 9', countdown === 'Wave 2 in 3, Wave 2 in 2, Wave 2 in 1, ' && wave.wave === 2 && wave.count === 9, countdown);

  await h.eval(() => {
    // DIRECTOR: finish the run the hard way.
    const p = __G.player.pos;
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * Math.PI * 2;
      __G.enemies.spawn('goon', new __G.THREE.Vector3(p.x + Math.cos(a) * 2.5, 0, p.z + Math.sin(a) * 2.5), { alerted: true });
    }
  });
  for (let i = 0; i < 400 && s.alive; i++) {
    await h.skip(5);
    s = await snap();
  }
  await h.skip(Math.ceil(1.5 / DT) + 1);
  await h.frames(2);
  await h.shot(`${OUT}13-holdout-dead.png`);
  s = await snap();
  const best = await h.eval(() => [__G.settings.best(), localStorage.getItem('murderinc.holdout.best')]);
  check(
    'the holdout death card: one wave cleared, the score, and a new best that is stored',
    s.state === 'dead' && /Waves cleared\s+1/.test(s.card) && s.card.includes(`Score  ${s.run.score.toLocaleString('en-US')}`) && /NEW/.test(s.card) && best[0] === Math.round(s.run.score) && best[1] === String(Math.round(s.run.score)),
    `score ${s.run.score}, best ${best[0]}`,
  );

  // ---- the books ---------------------------------------------------------------------------------

  const states = await h.eval(() => window.__rec.states.join(' '));
  const expectedStates = 'intro playing dead intro playing complete intro playing paused playing paused playing paused intro title intro playing dead';
  check('every state change was announced, in order', states === expectedStates, states);
  const errors = await h.errors();
  check('nothing was logged as an error', errors.length === 0, errors.slice(0, 3).join(' | '));

  if (failed) throw new Error(`${failed} of ${checks} checks failed (tools/scenarios/foundation-slice.cjs)`);
};
