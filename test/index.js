// Entry for `node --test test/`.
//
// Node 21 and later no longer expand a directory argument into its test files: they try to run the
// directory itself, which loads this file. It then pulls in every *.test.js beside it, so the command
// documented in CONTRACT section 2 runs the whole suite.
// Plain `node --test` (and `npm test`) discover the test files on their own and pick this file up as
// one more; in that case it must do nothing, or every test would run twice.

import { readdirSync } from 'node:fs';
import { basename, dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const self = fileURLToPath(import.meta.url);
const here = dirname(self);
const runAsDirectory = basename(process.argv[1] || '') !== basename(self);

if (runAsDirectory) {
  for (const name of readdirSync(here).sort()) {
    if (/\.test\.[cm]?js$/.test(name)) await import(pathToFileURL(join(here, name)).href);
  }
}
