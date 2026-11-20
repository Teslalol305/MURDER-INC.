// The AR-15. PLACEHOLDER: the Chopper's model and handling until this file gets the rifle's own
// (same interface as chopper.js: see what buildChopper returns).

import { buildChopper } from './chopper.js';

export function buildAr15(material, def) {
  const R = def.reload;
  const gun = buildChopper(material, { ...def, reload: { ...R, pressCheck: R.pressCheck || [R.tactical - 0.34, R.tactical - 0.2] } });
  gun.id = 'ar15';
  gun.root.name = 'ar15';
  return gun;
}
