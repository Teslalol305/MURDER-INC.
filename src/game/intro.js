// The full intro's copy for a mode: the location card data and the first radio line. Story gets the
// reels briefing; Hold the Block has no reels, no truck and no markers, so it gets its own tagline and
// line. The menus fall back to the reels tagline when the card data has none, which is why the holdout
// tagline is always passed explicitly (never left blank).

/**
 * @param {boolean} story  the run is the Story mission
 * @param {{location: object, radio: object}} text  src/config/text.js
 * @returns {{card: object, line: object | null}}  card data for `menus.locationCard(true, card)`; the radio line
 */
export function introCopy(story, text) {
  const L = text.location;
  if (story) return { card: L, line: text.radio.intro || null };
  return {
    card: L.taglineHoldout ? { ...L, tagline: L.taglineHoldout } : L,
    line: text.radio.introHoldout || null,
  };
}
