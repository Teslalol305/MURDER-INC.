// The ROCKET. PLACEHOLDER: the Chopper's model and handling until this file gets the launcher's own
// (same interface as chopper.js: see what buildChopper returns).

import { buildChopper } from './chopper.js';

export function buildRocket(material, def) {
  const R = def.reload;
  const reload = {
    ...R,
    tug: R.tug ?? R.magIn + 0.1,
    pressCheck: R.pressCheck || [R.tactical - 0.34, R.tactical - 0.2],
    boltBack: R.boltBack ?? R.empty - 0.34,
    boltRelease: R.boltRelease ?? R.empty - 0.2,
  };
  const gun = buildChopper(material, { ...def, reload });
  gun.id = 'rocket';
  gun.root.name = 'rocket';
  return gun;
}
