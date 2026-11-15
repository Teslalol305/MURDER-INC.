#!/usr/bin/env node
// Build script (esbuild JS API). See docs/CONTRACT.md section 2.
//
//   node build.mjs                      production: dist/index.html + dist/artifact.html
//   node build.mjs --dev                unminified, inline source map
//   node build.mjs --dev --only=level,atmos --out=dist/dev-level.html
//                                       the listed modules real, every other optional module stubbed
//                                       (a listed module whose file does not exist yet is stubbed as well)
//   node build.mjs --dev --stub=audio   everything real except the listed modules
//   node build.mjs --artifact           also write the page fragment (implied by the plain production build)
//
// Outputs:
//   <out> (default dist/index.html)  a standalone document: a minimal host-page skeleton followed by the
//                                    page fragment, with three.js bundled in.
//   dist/artifact.html               the page fragment alone (no doctype / html / head / body): three.js is
//                                    not bundled but fetched from a CDN by a small loader, then the game starts.
//
// Stubbing: src/modules.js imports every optional module as `./<name>.js`. That import is redirected to
// `./stubs/<name>.js` when the module is stubbed by the flags or its real file does not exist yet.

import { build, transform } from 'esbuild';
import { existsSync } from 'node:fs';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { gzipSync } from 'node:zlib';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(ROOT, 'src');
const DIST = path.join(ROOT, 'dist');
const MODULES_FILE = path.join(SRC, 'modules.js');

/** Modules that have a stub and can be switched with --only / --stub (boot order). */
const OPTIONAL = [
  'mats', 'props', 'input', 'level', 'atmos', 'fx', 'audio',
  'player', 'explosives', 'weapon', 'enemies', 'hud', 'menus', 'game',
];
/** Foundation modules: always real, no stub. */
const ALWAYS_REAL = ['render', 'physics', 'combat'];

const CSS_FILES = ['base.css', 'ui.css', 'input.css'];

/** Where the artifact build looks for three.js, in order. */
const THREE_CDN = [
  'https://cdnjs.cloudflare.com/ajax/libs/three.js/0.160.0/three.min.js',
  'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js',
  'https://unpkg.com/three@0.160.0/build/three.min.js',
];
const CDN_TIMEOUT_MS = 8000;

/** Host-page stand-in for the standalone build: what an Artifact host wraps around the fragment. */
const SKELETON_OPEN = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>body{margin:0}[hidden]{display:none!important}</style>
</head>
<body>
`;
const SKELETON_CLOSE = `</body>
</html>
`;

class BuildError extends Error {}

// ------------------------------------------------------------------------------------------------
// Arguments
// ------------------------------------------------------------------------------------------------

function parseArgs(argv) {
  const opts = { dev: false, out: null, only: null, stub: [], artifact: null, help: false };
  const list = (value, flag) => {
    if (!value) throw new BuildError(`${flag} needs a comma-separated list of module names`);
    return value.split(',').map((s) => s.trim()).filter(Boolean);
  };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    const eq = arg.indexOf('=');
    const flag = eq < 0 ? arg : arg.slice(0, eq);
    // `--flag=value` or `--flag value`
    const value = () => (eq >= 0 ? arg.slice(eq + 1) : argv[++i]);
    switch (flag) {
      case '--dev': opts.dev = true; break;
      case '--out': opts.out = value(); break;
      case '--only': opts.only = list(value(), '--only'); break;
      case '--stub': opts.stub = list(value(), '--stub'); break;
      case '--artifact': opts.artifact = eq >= 0 ? arg.slice(eq + 1) : true; break;
      case '--help': case '-h': opts.help = true; break;
      default: throw new BuildError(`unknown argument '${arg}' (try --help)`);
    }
  }
  if (opts.out === undefined || opts.out === '') throw new BuildError('--out needs a file name');

  const known = new Set([...OPTIONAL, ...ALWAYS_REAL]);
  for (const name of [...(opts.only ?? []), ...opts.stub]) {
    if (!known.has(name)) throw new BuildError(`unknown module '${name}'. Modules: ${OPTIONAL.join(', ')}`);
  }
  for (const name of opts.stub) {
    if (ALWAYS_REAL.includes(name)) throw new BuildError(`'${name}' is a foundation module and cannot be stubbed`);
  }
  return opts;
}

const HELP = `usage: node build.mjs [--dev] [--out=<file>] [--only=a,b | --stub=a,b] [--artifact[=<file>]]

  --dev            no minification, inline source map
  --out=<file>     standalone HTML output (default dist/index.html)
  --only=a,b       build these optional modules for real and stub all the others
                   (one that has no src/<name>.js yet is stubbed too, with a warning)
  --stub=a,b       stub these optional modules
  --artifact       also write the page fragment that loads three.js from a CDN (default dist/artifact.html;
                   always written by the plain production build)

optional modules: ${OPTIONAL.join(', ')}
always real:      ${ALWAYS_REAL.join(', ')}`;

// ------------------------------------------------------------------------------------------------
// Module plan and esbuild plugins
// ------------------------------------------------------------------------------------------------

/**
 * Decides, for every optional module, whether the real file or the stub goes into the bundle.
 * A module without a real file is always stubbed, also when `--only` asks for it: the documented
 * `--only=level,atmos` must keep working for the level agent while atmos has not been written yet.
 */
function planModules(opts) {
  const plan = {};
  for (const name of OPTIONAL) {
    const flagged = opts.stub.includes(name) || (opts.only !== null && !opts.only.includes(name));
    const missing = !existsSync(path.join(SRC, `${name}.js`));
    if (opts.only?.includes(name) && missing) {
      console.warn(`warning: --only=${name}: src/${name}.js does not exist yet, its stub is used instead`);
    }
    const stub = flagged || missing;
    if (stub && !existsSync(path.join(SRC, 'stubs', `${name}.js`))) {
      throw new BuildError(`module '${name}' needs its stub, but src/stubs/${name}.js does not exist`);
    }
    plan[name] = { stub, reason: flagged ? 'flag' : missing ? 'missing' : null };
  }
  return plan;
}

/** Redirects `./<name>.js` imports made by src/modules.js to the stub when the plan says so. */
function stubPlugin(plan) {
  return {
    name: 'module-stubs',
    setup(b) {
      b.onResolve({ filter: /^\.\/[a-z]+\.js$/ }, (args) => {
        if (path.resolve(args.importer) !== MODULES_FILE) return null;
        const name = args.path.slice(2, -3);
        return plan[name]?.stub ? { path: path.join(SRC, 'stubs', `${name}.js`) } : null;
      });
    },
  };
}

/**
 * Replaces the bare `three` import with the global the CDN build defines. Addons under
 * three/examples/jsm keep being bundled; their own `three` imports resolve to the same global.
 */
function threeGlobalPlugin() {
  return {
    name: 'three-global',
    setup(b) {
      b.onResolve({ filter: /^three$/ }, () => ({ path: 'three', namespace: 'three-global' }));
      b.onLoad({ filter: /.*/, namespace: 'three-global' }, () => ({
        contents: 'module.exports = window.THREE;',
        loader: 'js',
      }));
    },
  };
}

// ------------------------------------------------------------------------------------------------
// Pieces of the page
// ------------------------------------------------------------------------------------------------

/** Evaluates a source module at build time (bundled first, so it may import its neighbours). */
async function loadSourceModule(file) {
  const result = await build({
    entryPoints: [file],
    bundle: true,
    format: 'esm',
    platform: 'neutral',
    write: false,
    logLevel: 'silent',
  });
  const code = Buffer.from(result.outputFiles[0].contents).toString('base64');
  return import(`data:text/javascript;base64,${code}`);
}

async function bundleGame({ dev, plan, artifact }) {
  const meta = {
    dev,
    artifact,
    stubbed: OPTIONAL.filter((name) => plan[name].stub),
  };
  const result = await build({
    entryPoints: [path.join(SRC, 'main.js')],
    outfile: path.join(DIST, artifact ? 'artifact.js' : 'bundle.js'), // names the source-map paths only
    write: false,
    bundle: true,
    format: 'iife',
    platform: 'browser',
    target: 'es2020',
    minify: !dev,
    sourcemap: dev ? 'inline' : false,
    legalComments: 'eof',
    define: { __BUILD__: JSON.stringify(meta) },
    plugins: artifact ? [stubPlugin(plan), threeGlobalPlugin()] : [stubPlugin(plan)],
    // The artifact bundle must not run before three.js has arrived: wrap it in a function.
    banner: artifact ? { js: 'window.__MI_START=function(){' } : undefined,
    footer: artifact ? { js: '};' } : undefined,
    logLevel: 'warning',
  });
  return result.outputFiles[0].text;
}

async function bundleCss(dev) {
  const parts = [];
  for (const name of CSS_FILES) {
    const file = path.join(SRC, name);
    if (!existsSync(file)) continue;
    const css = await readFile(file, 'utf8');
    parts.push(dev ? `/* ---- ${name} ---- */\n${css}` : css);
  }
  const css = parts.join('\n');
  if (dev) return css;
  return (await transform(css, { loader: 'css', minify: true })).code.trim();
}

/** Loader for the artifact: tries each CDN in turn until window.THREE exists, then starts the game. */
function cdnLoaderSource(failText) {
  return `(function () {
  var urls = ${JSON.stringify(THREE_CDN)};
  var started = false;
  function start() {
    if (started) return;
    started = true;
    window.__MI_START();
  }
  function fail() {
    var text = ${JSON.stringify(failText)};
    window.__fatal = text;
    var boot = document.getElementById('boot');
    var line = document.getElementById('boot-msg');
    if (boot) boot.classList.add('is-fatal');
    if (line) line.textContent = text;
  }
  function attempt(i) {
    if (window.THREE) return start();
    if (i >= urls.length) return fail();
    var script = document.createElement('script');
    var settled = false;
    var timer = setTimeout(done, ${CDN_TIMEOUT_MS});
    function done() {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      script.onload = script.onerror = null;
      if (window.THREE) return start();
      script.remove();
      attempt(i + 1);
    }
    script.onload = script.onerror = done;
    script.src = urls[i];
    (document.head || document.documentElement).appendChild(script);
  }
  attempt(0);
})();`;
}

/** Makes script text safe inside an inline <script> element. */
function inlineScript(js) {
  const safe = js.replace(/<\/(script)/gi, '<\\/$1').replace(/<!--/g, '<\\!--');
  return `<script>\n${safe.trimEnd()}\n</script>`;
}

/** Fills the two placeholders of src/page.html. */
function renderPage(template, css, scripts) {
  for (const marker of ['<!--STYLE-->', '<!--SCRIPTS-->']) {
    if (!template.includes(marker)) throw new BuildError(`src/page.html has lost its ${marker} placeholder`);
  }
  if (/<\/style/i.test(css)) throw new BuildError('the stylesheet contains "</style": it cannot be inlined');
  // Function replacers: the bundle is full of `$&`-style sequences that a string replacement would expand.
  return template
    .replace('<!--STYLE-->', () => `<style>\n${css}\n</style>`)
    .replace('<!--SCRIPTS-->', () => scripts);
}

/** Warns when the palette in base.css and config/brand.js no longer agree. */
function checkBrandTokens(css, brand) {
  const kebab = (s) => s.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`);
  const squash = (s) => String(s).replace(/\s+/g, ' ').replace(/"/g, "'").trim().toLowerCase();
  const declared = new Map();
  for (const m of css.matchAll(/(--(?:c|font)-[a-z0-9-]+)\s*:\s*([^;}]+)/g)) {
    if (!declared.has(m[1])) declared.set(m[1], squash(m[2]));
  }
  const expect = [
    ...Object.entries(brand.colors ?? {}).map(([k, v]) => [`--c-${kebab(k)}`, v]),
    ...Object.entries(brand.fonts ?? {}).map(([k, v]) => [`--font-${kebab(k)}`, v]),
  ];
  for (const [name, value] of expect) {
    if (declared.has(name) && declared.get(name) !== squash(value)) {
      console.warn(`warning: brand token drift: ${name} is "${declared.get(name)}" in the CSS but "${value}" in src/config/brand.js`);
    }
  }
}

const kb = (n) => (n >= 1e6 ? `${(n / 1e6).toFixed(2)} MB` : `${(n / 1e3).toFixed(1)} kB`);

async function emit(file, html, note) {
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, html);
  const bytes = Buffer.byteLength(html);
  const name = path.relative(ROOT, file) || file;
  console.log(`  ${name.padEnd(24)} ${kb(bytes).padStart(9)}   gzip ${kb(gzipSync(html).length).padStart(8)}   ${note}`);
}

// ------------------------------------------------------------------------------------------------
// Main
// ------------------------------------------------------------------------------------------------

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    console.log(HELP);
    return;
  }

  const started = Date.now();
  const plan = planModules(opts);
  const outFile = path.resolve(ROOT, opts.out ?? path.join('dist', 'index.html'));
  // The fragment is part of the plain production build and otherwise only made on request.
  const plainProduction = !opts.dev && opts.out === null && opts.only === null && opts.stub.length === 0;
  const artifactFile =
    typeof opts.artifact === 'string' && opts.artifact
      ? path.resolve(ROOT, opts.artifact)
      : opts.artifact || plainProduction
        ? path.join(DIST, 'artifact.html')
        : null;

  const [template, css, text, brand] = await Promise.all([
    readFile(path.join(SRC, 'page.html'), 'utf8'),
    bundleCss(opts.dev),
    loadSourceModule(path.join(SRC, 'config', 'text.js')),
    loadSourceModule(path.join(SRC, 'config', 'brand.js')),
  ]);
  checkBrandTokens(css, brand);

  const real = [...ALWAYS_REAL, ...OPTIONAL.filter((n) => !plan[n].stub)];
  const stubbed = OPTIONAL.filter((n) => plan[n].stub).map((n) => (plan[n].reason === 'missing' ? `${n} (no file yet)` : n));
  console.log(`${opts.dev ? 'dev' : 'production'} build`);
  console.log(`  real: ${real.join(', ')}`);
  console.log(`  stub: ${stubbed.length ? stubbed.join(', ') : 'none'}`);

  const standalone = await bundleGame({ dev: opts.dev, plan, artifact: false });
  await emit(
    outFile,
    SKELETON_OPEN + renderPage(template, css, inlineScript(standalone)) + SKELETON_CLOSE,
    'standalone, three.js bundled',
  );

  if (artifactFile) {
    const game = await bundleGame({ dev: opts.dev, plan, artifact: true });
    const failText = text.boot.fatal('the 3D engine (three.js) could not be downloaded. Check the connection and reload.');
    let loader = cdnLoaderSource(failText);
    if (!opts.dev) loader = (await transform(loader, { minify: true, target: 'es2015' })).code;
    await emit(
      artifactFile,
      renderPage(template, css, `${inlineScript(game)}\n${inlineScript(loader)}`),
      'page fragment, three.js from CDN',
    );
  }

  console.log(`done in ${((Date.now() - started) / 1000).toFixed(1)} s`);
}

main().catch((err) => {
  // esbuild has already printed its own diagnostics for build failures.
  if (err instanceof BuildError) console.error(`build.mjs: ${err.message}`);
  else if (!Array.isArray(err?.errors)) console.error(err);
  else console.error(`build failed with ${err.errors.length} error${err.errors.length === 1 ? '' : 's'}`);
  process.exitCode = 1;
});
