'use strict';

// Capture hooks for the Unreal data export. `installHooks` is serialised into the page by Playwright
// (page.addInitScript) and runs before any game script.
//
// Most of what the export needs hangs off window.__G once the game has booted. Three things do not:
// the list of placed props lives in the level's building kit (a closure) and the static ones are merged
// away, an oriented collider is sliced into axis-aligned pieces before anyone can see it whole, and a
// sign's text is gone once it has been painted onto an atlas page. So the hooks listen in on the calls
// that carry that knowledge:
//
//   G.props.build(name, opts)                    every prop that is built (and the seed it drew)
//   G.physics.addBox / addOriented               who added each collider; the whole oriented box
//   G.mats.sign / poster / graffiti / decal      what was painted, and the atlas rectangle it landed on
//   G.mats.facade                                the window grids of the facades
//
// Nothing here changes what the game does: every wrapper calls straight through with the same arguments
// and hands back the same result; it only remembers what it saw in window.__ue. The accessors that catch
// the modules as main.js assigns them are turned back into plain properties when the last one is in.

/** Module names in boot order (src/modules.js MODULES). export.cjs checks the page booted in this order. */
const MODULES = [
  'render', 'mats', 'physics', 'props', 'input', 'level', 'atmos', 'fx', 'audio', 'player', 'combat',
  'explosives', 'weapon', 'enemies', 'hud', 'menus', 'game',
];

function installHooks(moduleNames) {
  const rec = {
    order: [], // module names, in the order main.js created them
    builds: [], // {name, opts, prop, by, seed, seedGiven}: every props.build call
    boxes: new Map(), // collider → {by, oriented}
    oriented: [], // {center, size, yaw, boxes, by}: every physics.addOriented call
    paintings: [], // {kind, args, out, by}: every mats.sign / poster / graffiti / decal call
    facades: [], // {spec, material, by}: every mats.facade call
    drawn: null, // the last seed the prop factory drew from its own stream
    h: null, // page helpers, installed later (lib/collect.cjs)
  };
  window.__ue = rec;

  /** The module main.js is creating right now ('run' once the game has booted). */
  const creating = () => moduleNames[rec.order.length] || 'run';

  function hookPhysics(api) {
    const { addBox, addOriented } = api;
    api.addBox = function hookedAddBox(spec) {
      const box = addBox.call(this, spec);
      rec.boxes.set(box, { by: creating(), oriented: null });
      return box;
    };
    api.addOriented = function hookedAddOriented(center, size, yaw = 0, opts = {}) {
      // addOriented makes its pieces with the module's own addBox, not the wrapper above: label them here.
      const out = addOriented.call(this, center, size, yaw, opts);
      const entry = {
        center: Array.isArray(center) ? center.slice() : [center.x, center.y, center.z],
        size: Array.isArray(size) ? size.slice() : [size.x, size.y, size.z],
        yaw,
        boxes: out,
        by: creating(),
      };
      rec.oriented.push(entry);
      for (const box of out) rec.boxes.set(box, { by: entry.by, oriented: entry });
      return out;
    };
  }

  function hookProps(api) {
    const { build } = api;
    api.build = function hookedBuild(name, opts = {}) {
      rec.drawn = null;
      const prop = build.call(this, name, opts);
      // The factory draws a seed from its own stream when the caller gave none (src/props.js build()).
      const given = Number.isFinite(opts.seed);
      rec.builds.push({ name, opts: { ...opts }, prop, by: creating(), seed: given ? Math.abs(Math.floor(opts.seed)) : rec.drawn, seedGiven: given });
      return prop;
    };
  }

  function hookMats(api) {
    for (const kind of ['sign', 'poster', 'graffiti', 'decal']) {
      const paint = api[kind];
      if (typeof paint !== 'function') continue;
      api[kind] = function hookedPaint(...args) {
        const out = paint.apply(this, args);
        rec.paintings.push({ kind, args: args.map((a) => (a && typeof a === 'object' ? { ...a } : a)), out, by: creating() });
        return out;
      };
    }
    const { facade } = api;
    if (typeof facade === 'function') {
      api.facade = function hookedFacade(spec) {
        const material = facade.call(this, spec);
        rec.facades.push({ spec: { ...spec }, material, by: creating() });
        return material;
      };
    }
  }

  const onModule = { physics: hookPhysics, props: hookProps, mats: hookMats };

  /** Catches each module the moment main.js assigns it to G (`G[name] = await createModule(entry)`). */
  function trap(G) {
    const slots = {};
    for (const name of moduleNames) {
      Object.defineProperty(G, name, {
        configurable: true,
        enumerable: true,
        get: () => slots[name],
        set(api) {
          slots[name] = api;
          try {
            if (api && onModule[name]) onModule[name](api);
          } catch (err) {
            console.error(`[ue-export] could not hook ${name}:`, err);
          }
          rec.order.push(name);
          if (name === moduleNames[moduleNames.length - 1]) {
            // The last module is in: give G its plain properties back.
            for (const key of moduleNames) Object.defineProperty(G, key, { configurable: true, enumerable: true, writable: true, value: slots[key] });
          }
        },
      });
    }
    // The prop factory's own random stream: remember the seed it draws for a prop built without one.
    const fork = G.rng && G.rng.fork;
    if (typeof fork === 'function') {
      G.rng.fork = function hookedFork(label) {
        const child = fork.call(this, label);
        if (label === 'props' && child && typeof child.int === 'function') {
          const { int } = child;
          child.int = function hookedInt(a, b) {
            const value = int.call(this, a, b);
            rec.drawn = value;
            return value;
          };
        }
        return child;
      };
    }
  }

  // main.js publishes the shared object as window.__G before it boots anything.
  let shared;
  Object.defineProperty(window, '__G', {
    configurable: true,
    enumerable: true,
    get: () => shared,
    set(G) {
      shared = G;
      if (G && typeof G === 'object') trap(G);
    },
  });
}

module.exports = { installHooks, MODULES };
