// The SWITCH. PLACEHOLDER: the Nine's model and handling until this file gets the pistol's own
// (same interface as nine.js: see what buildNine returns).

import { buildNine } from './nine.js';

export function buildSwitch9(material, def, strike = 0.55, goldHex = 0xe7b53a) {
  const gun = buildNine(material, def, strike, goldHex);
  gun.id = 'switch9';
  gun.root.name = 'switch9';
  return gun;
}
