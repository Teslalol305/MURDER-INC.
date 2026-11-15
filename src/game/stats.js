// What the death and debrief cards are told. Pure.

/** Hits per shot, 0…1; null when no shot was fired (shown as a dash). */
export const accuracy = (run) => (run.shots > 0 ? Math.min(1, run.hits / run.shots) : null);

/**
 * The data object for menus.show('dead' | 'complete', data). One shape for both cards
 * (CONTRACT section 10): each card reads what it needs.
 * @param {object} run       game.run
 * @param {object} info      {mode, difficulty, wavesCleared, best, newBest, headshots}
 * @param {object} flow      config/flow.js (ratingPoints)
 * @param {string[]} ratings config/text.js `ratings`
 */
export function cardData(run, info, flow, ratings) {
  const rating = flow.ratingPoints(run);
  return {
    mode: info.mode,
    difficulty: info.difficulty,
    time: run.time,
    reels: run.reels,
    total: run.total,
    wave: info.wavesCleared || 0,
    kills: run.kills,
    headshots: info.headshots || 0,
    shots: run.shots,
    hits: run.hits,
    score: Math.round(run.score),
    best: info.best || 0,
    newBest: !!info.newBest,
    accuracy: accuracy(run),
    retries: run.retries,
    rating,
    ratingName: ratings[rating] || ratings[0],
  };
}
