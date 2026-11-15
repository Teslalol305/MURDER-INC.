// Tiny synchronous pub/sub bus shared by every module as `G.events`.
// Handlers are isolated: one that throws is logged and the rest still run.

export function createEvents() {
  // name → frozen-by-convention array of handlers. Arrays are replaced (never mutated) on subscribe /
  // unsubscribe, so `emit` can iterate without copying and handlers may (un)subscribe while it runs.
  const map = new Map();

  function on(name, fn) {
    if (typeof fn !== 'function') throw new TypeError(`events.on('${name}'): handler must be a function`);
    const list = map.get(name);
    map.set(name, list ? [...list, fn] : [fn]);
    return () => off(name, fn);
  }

  function off(name, fn) {
    const list = map.get(name);
    if (!list) return;
    const i = list.indexOf(fn);
    if (i < 0) return;
    if (list.length === 1) map.delete(name);
    else map.set(name, [...list.slice(0, i), ...list.slice(i + 1)]);
  }

  function emit(name, payload) {
    const list = map.get(name);
    if (!list) return;
    for (let i = 0; i < list.length; i++) {
      try {
        list[i](payload);
      } catch (err) {
        console.error(`[events] handler for '${name}' threw:`, err);
      }
    }
  }

  /** Number of handlers currently subscribed to `name` (debugging aid). */
  function count(name) {
    const list = map.get(name);
    return list ? list.length : 0;
  }

  return { on, off, emit, count };
}
