// A plain player plays the story: no cover, no strafing, no cleverness. It follows the guide line,
// stops when it sees a Vulture, aims (the lock does the rest), holds the trigger, holds Interact at the
// reel and runs for the truck. What it needs to finish, on each difficulty, is the measure of how
// forgiving the game is: its deaths, the health it was down to, how long each level took.
//
//   node build.mjs --dev --out=dist/dev-all.html
//   node tools/shot.cjs dist/dev-all.html --size 640x360 --params "autostart=1&q=test&noaudio=1&nohud=1" \
//        --scenario tools/scenarios/story-bot.cjs --timeout 900
//   BOT_DIFFICULTY=hustler|boss|kingpin (default hustler); BOT_LIMIT=seconds of play before it gives up
//   (default 900); BOT_MAX_DEATHS: the run fails when the bot needs more retries than this (default: no limit);
//   BOT_SHOTS=n: a picture every n seconds of play (shots/bot/<difficulty>-NN.png; drop &nohud=1 to see the HUD).

module.exports = async (page, h) => {
  const difficulty = process.env.BOT_DIFFICULTY || 'hustler';
  const limit = Number(process.env.BOT_LIMIT) || 900;
  await h.skip(5);
  await h.eval((name) => {
    const G = window.__G;
    G.settings.set('difficulty', name);
    G.game.start({ mode: 'mission', skipIntro: true });

    const V = G.THREE.Vector3;
    const down = new Set();
    const canvas = document.getElementById('view');
    const key = (code, on) => {
      if (on === down.has(code)) return;
      if (on) down.add(code);
      else down.delete(code);
      const m = /^Mouse(\d)$/.exec(code);
      if (m) (on ? canvas : window).dispatchEvent(new MouseEvent(on ? 'mousedown' : 'mouseup', { button: Number(m[1]), bubbles: true, cancelable: true }));
      else window.dispatchEvent(new KeyboardEvent(on ? 'keydown' : 'keyup', { code, bubbles: true, cancelable: true }));
    };
    const releaseAll = () => {
      for (const code of [...down]) key(code, false);
    };
    const log = (window.__bot = { deaths: 0, levels: [], lowest: 100, done: false, stuck: 0, level: 0, t0: 0, deathsAt: 0, lowestAt: 100, died: [] });
    const chest = new V();
    const turnTo = (x, y, z) => {
      const p = G.player;
      const dx = x - p.eye.x;
      const dy = y - p.eye.y;
      const dz = z - p.eye.z;
      p.yaw = Math.atan2(-dx, -dz);
      p.pitch = Math.atan2(dy, Math.hypot(dx, dz));
    };
    let last = new V();
    let still = 0;
    let swapIn = 0;

    function act(dt) {
      const g = G.game;
      const p = G.player;
      const w = G.weapon;
      if (g.state === 'dead') {
        releaseAll();
        if (G.menus.screen === 'dead') {
          log.deaths++;
          log.died.push({ level: g.run.level, phase: g.flow.phase, at: Math.round(g.run.time) });
          g.retry();
        }
        return;
      }
      if (g.state === 'complete') {
        releaseAll();
        if (!log.done) {
          log.levels.push({ level: log.level, secs: Math.round(g.run.time - log.t0), deaths: log.deaths - log.deathsAt, lowest: Math.round(log.lowestAt) });
          log.done = true;
          log.time = Math.round(g.run.time);
          log.kills = G.combat.stats.kills;
          log.accuracy = G.combat.stats.shots ? Math.round((100 * G.combat.stats.hits) / G.combat.stats.shots) : 0;
        }
        return;
      }
      if (g.state !== 'playing') {
        releaseAll();
        return;
      }
      // A new level: close the book on the last one.
      if (g.run.level !== log.level) {
        if (log.level) log.levels.push({ level: log.level, secs: Math.round(g.run.time - log.t0), deaths: log.deaths - log.deathsAt, lowest: Math.round(log.lowestAt) });
        log.level = g.run.level;
        log.t0 = g.run.time;
        log.deathsAt = log.deaths;
        log.lowestAt = 100;
      }
      log.lowest = Math.min(log.lowest, p.health);
      log.lowestAt = Math.min(log.lowestAt, p.health);

      // The nearest Vulture in plain view.
      let target = null;
      let best = 42;
      for (const e of G.enemies.list) {
        if (!e.alive) continue;
        const d = e.pos.distanceTo(p.pos);
        if (d >= best) continue;
        chest.set(e.pos.x, e.pos.y + (e.type === 'buzzard' ? 0 : 1.2), e.pos.z);
        if (!G.physics.lineOfSight(p.eye, chest)) continue;
        best = d;
        target = e;
      }

      if (target) {
        // Stop, look its way, aim: the lock takes over from there. Fire while it holds.
        key('KeyW', false);
        key('ShiftLeft', false);
        key('KeyE', false);
        if (!w.lock.on) turnTo(target.pos.x, target.pos.y + (target.type === 'buzzard' ? 0 : 1.2), target.pos.z);
        key('Mouse2', true);
        key('Mouse0', w.lock.on && w.state !== 'reloading' && w.state !== 'switching');
        // Out of everything for this gun: the next one.
        swapIn -= dt;
        if (w.mag === 0 && !(w.reserve > 0) && swapIn <= 0) {
          swapIn = 1;
          key('KeyQ', true);
          setTimeout(() => key('KeyQ', false), 0);
        }
        still = 0;
        return;
      }
      key('Mouse2', false);
      key('Mouse0', false);

      // Nothing in sight: on to what the level wants.
      const phase = g.flow.phase;
      const reel = phase === 'reach' ? G.level.objectives[g.run.level - 1] : null;
      if (reel && Math.hypot(reel.pos.x - p.pos.x, reel.pos.z - p.pos.z) < 1.5) {
        key('KeyW', false);
        key('ShiftLeft', false);
        turnTo(reel.pos.x, reel.pos.y + 0.6, reel.pos.z);
        key('KeyE', true);
        return;
      }
      key('KeyE', false);
      const route = g.guide.route;
      if (!route || route.length < 2) {
        key('KeyW', false);
        key('ShiftLeft', false);
        return;
      }
      // The first way-point that is still ahead.
      let next = route[route.length - 1];
      for (let i = 1; i < route.length; i++) {
        if (Math.hypot(route[i].x - p.pos.x, route[i].z - p.pos.z) > 0.9) {
          next = route[i];
          break;
        }
      }
      turnTo(next.x, p.eye.y, next.z);
      key('KeyW', true);
      key('ShiftLeft', true);
      // Hung up on a corner: a hop usually frees it.
      still = p.pos.distanceTo(last) < 0.02 ? still + dt : 0;
      last.copy(p.pos);
      if (still > 1) {
        log.stuck++;
        still = 0;
        key('Space', true);
        setTimeout(() => key('Space', false), 0);
      }
    }

    const update = G.game.update;
    G.game.update = function (dt) {
      try {
        act(dt);
      } catch (err) {
        console.error('[bot]', err);
      }
      return update.call(this, dt);
    };
  }, difficulty);

  let out = null;
  const every = Number(process.env.BOT_SHOTS) || 0;
  const chunk = every > 0 ? Math.max(1, Math.round(every * 30)) : 300;
  let n = 0;
  for (let t = 0; t < limit; t += chunk / 30) {
    await h.skip(chunk);
    if (every > 0) {
      await h.frames(1);
      await h.shot(`shots/bot/${difficulty}-${String(++n).padStart(2, '0')}.png`);
    }
    out = await h.eval(() => ({ ...window.__bot, state: window.__G.game.state, level: window.__G.game.run.level, phase: window.__G.game.flow.phase, alive: window.__G.enemies.aliveCount(), health: Math.round(window.__G.player.health) }));
    if (out.done) break;
  }
  console.error(`[bot] ${difficulty}: ${JSON.stringify(out)}`);
  const errors = await h.errors();
  const problems = [];
  if (errors.length) problems.push(`errors: ${errors.slice(0, 3).join(' | ')}`);
  if (!out.done) problems.push(`the bot did not finish the story in ${limit} s of play: level ${out.level}, phase ${out.phase}, ${out.alive} alive`);
  const max = process.env.BOT_MAX_DEATHS;
  if (max !== undefined && out.deaths > Number(max)) problems.push(`the bot went down ${out.deaths} times (at most ${max} allowed on ${difficulty})`);
  if (problems.length) throw new Error(problems.join('\n'));
};
