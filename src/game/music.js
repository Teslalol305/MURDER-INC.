// The music-intensity driver: three levels, re-evaluated every frame while a run is on
// (config/flow.js `music`). Pure: the game keeps the clocks and hands them in.

/**
 * @param {object} s
 *   s.allDone     every reel is secured (story: the run for the truck)
 *   s.queued      enemies still waiting to arrive
 *   s.alive       living enemies
 *   s.waveAge     seconds since the last wave was queued (Infinity: none, or its window is over)
 *   s.sinceAlert  seconds since an enemy last went from unaware to engaging
 *   s.sinceHit    seconds since the player was last hit
 *   s.nearest     metres to the closest living enemy (Infinity: none)
 * @param {object} M  config/flow.js `music`
 * @returns {number} M.hot | M.alert | M.calm
 */
export function musicIntensity(s, M) {
  if (s.allDone || s.queued > 0 || (s.waveAge < M.waveHot && s.alive > 0)) return M.hot;
  if (s.sinceAlert < M.alertHold || s.sinceHit < M.hitHold || s.nearest < M.nearDistance) return M.alert;
  return M.calm;
}

/** The "wave is hot" window ends early: the wave has been out a while and nobody is left or on the way. */
export const waveIsOver = (s, M) => s.waveAge >= M.waveMinOut && s.alive === 0 && s.queued === 0;
