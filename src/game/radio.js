// The radio queue: one speaker, lines in order. A line types out at `charsPerSec`, holds for its own
// `secs`, then the next one starts after a short gap. The owner supplies what "starting a line" and
// "going quiet" mean (HUD call, event), so the timing can be tested on its own.

/**
 * @param {object} opts
 *   opts.charsPerSec   typing speed of the subtitle
 *   opts.gap           seconds of silence between two lines
 *   opts.onLine(text, secs)   a line starts
 *   opts.onClear()            the queue was cut short while a line was up
 */
export function createRadio({ charsPerSec, gap = 0, onLine, onClear }) {
  const queue = []; // {text, secs}, oldest first
  let busy = 0; // seconds until the current line is over (typing + hold + gap)

  const radio = {
    /** Lines waiting behind the current one. */
    get pending() {
      return queue.length;
    },
    /** True while a line is up or lines are waiting. */
    get active() {
      return busy > 0 || queue.length > 0;
    },

    /** Queues a line; it starts on the next update if nothing is playing. */
    say(text, secs) {
      if (!text) return;
      queue.push({ text: String(text), secs: Number(secs) > 0 ? Number(secs) : 0 });
    },

    /** Drops everything, including the line that is up. */
    clear() {
      const wasUp = busy > 0;
      queue.length = 0;
      busy = 0;
      if (wasUp && onClear) onClear();
    },

    update(dt) {
      if (busy > 0) {
        busy -= dt;
        if (busy > 0) return;
      }
      const line = queue.shift();
      if (!line) {
        busy = 0;
        return;
      }
      busy = line.text.length / charsPerSec + line.secs + gap;
      if (onLine) onLine(line.text, line.secs);
    },
  };
  return radio;
}
