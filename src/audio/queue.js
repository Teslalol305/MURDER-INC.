// Background render queue: generator jobs worked through in short time slices so synthesis never blocks
// a frame or the boot. Lower `prio` first; `promote(key)` moves a job to the front, `finish(key)` runs it
// to the end right now. Timer and clock are injectable for the tests.
//
// A slice never starts a step it is not expected to finish in time: each job remembers how long its
// last step took, and once a slice has done some work it stops before a step that would overrun it.
// The generators keep their steps short (dsp.js stepped forms), so a slice stays near its budget.

export function createQueue({ slice = 6, interval = 12, now = () => performance.now(), schedule = (fn, ms) => setTimeout(fn, ms) } = {}) {
  const jobs = []; // {key, prio, seq, iter, done(result)}
  const byKey = new Map();
  let seq = 0;
  let timer = false;
  let running = false;

  function add(key, prio, iter, done) {
    if (byKey.has(key)) return;
    const job = { key, prio, seq: seq++, iter, done, last: 0 };
    byKey.set(key, job);
    let i = jobs.length;
    while (i > 0 && (jobs[i - 1].prio > prio)) i--;
    jobs.splice(i, 0, job);
    kick();
  }

  /** Advances one job by one step; true when it finished. */
  function stepJob(job) {
    let r;
    const t0 = now();
    try {
      r = job.iter.next();
      job.last = now() - t0;
    } catch (err) {
      remove(job);
      console.warn(`[audio] rendering ${job.key} failed:`, err);
      return true;
    }
    if (!r.done) return false;
    remove(job);
    job.done(r.value);
    return true;
  }

  function remove(job) {
    byKey.delete(job.key);
    const i = jobs.indexOf(job);
    if (i >= 0) jobs.splice(i, 1);
  }

  /**
   * Works for up to `budget` ms: always one step, then more while the next job's last step still fits
   * in what is left. Returns how many jobs are left.
   */
  function run(budget = slice) {
    const end = now() + budget;
    let first = true;
    while (jobs.length) {
      const t = now();
      if (!first && (t >= end || t + jobs[0].last > end)) break;
      first = false;
      stepJob(jobs[0]);
    }
    return jobs.length;
  }

  function tick() {
    timer = false;
    if (!running) return;
    if (run(slice) > 0) kick();
  }

  function kick() {
    if (timer || !running || !jobs.length) return;
    timer = true;
    schedule(tick, interval);
  }

  return {
    add,
    run,
    start() {
      running = true;
      kick();
    },
    stop() {
      running = false;
    },
    promote(key) {
      const job = byKey.get(key);
      if (!job) return false;
      jobs.splice(jobs.indexOf(job), 1);
      jobs.unshift(job);
      return true;
    },
    finish(key) {
      const job = byKey.get(key);
      if (!job) return false;
      while (!stepJob(job));
      return true;
    },
    has: (key) => byKey.has(key),
    get size() {
      return jobs.length;
    },
  };
}
