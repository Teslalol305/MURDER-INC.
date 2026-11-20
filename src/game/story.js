// The story's bookkeeping: pure functions over src/config/story.js, the flow table and the words.
// What the game does with them is in src/game.js; these have no state and run in a unit test.

/**
 * Where level `index` stands in the story.
 * @returns {{index, n, total, id, goal, reel, last, scene}}
 */
export function stageOf(index, levels) {
  const total = levels.length;
  const i = Math.min(total - 1, Math.max(0, index | 0));
  const level = levels[i];
  return { index: i, n: i + 1, total, id: level.id, goal: level.goal, reel: level.reel || null, last: i === total - 1, scene: level.scene || null };
}

/**
 * The Vultures of a level before they know Rule is there: the first `counts[type]` posts of each list.
 * @param {{posts: {goon?: number[][], buzzard?: number[][]}}} level
 * @param {{goon?: number, buzzard?: number}} counts   flow.difficulty[name].levels[i].patrol
 * @returns {{type: string, point: number[]}[]}  Buzzards first: they are the ones seen from afar
 */
export function patrolOf(level, counts) {
  const out = [];
  const posts = (level && level.posts) || {};
  for (const type of ['buzzard', 'goon']) {
    const list = posts[type] || [];
    const n = Math.min(list.length, Math.max(0, Math.floor((counts && counts[type]) || 0)));
    for (let i = 0; i < n; i++) out.push({ type, point: list[i] });
  }
  return out;
}

/**
 * The time of day a level plays in. The player's own choice holds until a level says otherwise, and a
 * player who chose the night keeps it throughout.
 */
export function timeOf(index, levels, setting) {
  const chosen = setting === 'night' ? 'night' : 'day';
  const level = levels[Math.min(levels.length - 1, Math.max(0, index | 0))];
  return level && level.time === 'night' ? 'night' : chosen;
}

/**
 * The objective line.
 * @param {'reach'|'clear'|'truck'|'done'} phase
 * @param {{code?: string, left?: number, guided?: boolean}} info
 * @param {object} T   config/text.js `story.objectives`
 */
export function objectiveLine(phase, info, T) {
  switch (phase) {
    case 'reach':
      return T.reach(info.code, !!info.guided);
    case 'clear':
      return T.clear(Math.max(1, info.left | 0));
    case 'truck':
      return T.truck(!!info.guided);
    case 'done':
      return T.done;
    default:
      return '';
  }
}

/**
 * The yaw that looks down a route from its start (0 looks down −Z, + turns left): toward the point
 * `ahead` metres along it, so a short first step round a corner does not decide it. `fallback` when
 * the route has no length.
 */
export function facing(route, fallback = 0, ahead = 6) {
  if (!route || route.length < 2) return fallback;
  let left = ahead;
  let x = route[0].x;
  let z = route[0].z;
  for (let i = 1; i < route.length && left > 0; i++) {
    const dx = route[i].x - route[i - 1].x;
    const dz = route[i].z - route[i - 1].z;
    const leg = Math.hypot(dx, dz);
    if (leg < 1e-6) continue;
    const k = Math.min(1, left / leg);
    x = route[i - 1].x + dx * k;
    z = route[i - 1].z + dz * k;
    left -= leg;
  }
  const dx = x - route[0].x;
  const dz = z - route[0].z;
  return dx * dx + dz * dz > 1e-6 ? Math.atan2(-dx, -dz) : fallback;
}

/** The words of a level's title card: {kicker, title, sub}. */
export function levelCard(stage, T) {
  const words = T.levels[stage.id] || {};
  return { kicker: T.levelOf(stage.n, stage.total), title: words.title || '', sub: words.brief || '' };
}

/** How long a line stays up: typed out at `cps`, then held for its own seconds. */
export const lineSeconds = (line, cps) => line.text.length / cps + (line.secs || 0);

/**
 * Checks a scene's script against its words: every `say` names a line that exists, lines do not talk
 * over each other, and everything is over before the scene is. Returns a list of problems (empty: fine).
 */
export function sceneProblems(name, scene, lines, cps) {
  const problems = [];
  const duration = scene.shots.reduce((sum, shot) => sum + shot.secs, 0);
  let busyUntil = 0;
  for (const cue of [...scene.cues].sort((a, b) => a.at - b.at)) {
    if (cue.at > duration) problems.push(`${name}: a cue at ${cue.at} s is after the end (${duration} s)`);
    if (cue.say === undefined) continue;
    const line = lines && lines[cue.say];
    if (!line) {
      problems.push(`${name}: no line ${cue.say}`);
      continue;
    }
    if (cue.at < busyUntil - 1e-9) problems.push(`${name}: line ${cue.say} starts at ${cue.at} s while the one before runs to ${busyUntil.toFixed(2)} s`);
    busyUntil = cue.at + lineSeconds(line, cps);
    if (busyUntil > duration + 1e-9) problems.push(`${name}: line ${cue.say} runs to ${busyUntil.toFixed(2)} s, past the end (${duration} s)`);
  }
  return problems;
}
