// G.weapon (CONTRACT 6.5): the CHOPPER and the NINE.
//
//   weapon/logic.js      the rules: ammo, fire control, spread, recoil, aim, reload, switching, melee
//   weapon/viewmodel.js  what the player sees: both guns, Rule's arms, every animation, muzzle flash
//
// The rules run without the viewmodel (unit tests, or a viewmodel that failed to build): the game then
// plays the same, only with empty hands.

import { createLogic } from './weapon/logic.js';
import { createViewmodel } from './weapon/viewmodel.js';

export function createWeapon(G) {
  let view = null;
  if (G.vmCamera && G.renderer && typeof document !== 'undefined') {
    try {
      view = createViewmodel(G);
    } catch (err) {
      console.error('[weapon] the viewmodel could not be built, playing without it:', err);
    }
  }

  const weapon = view ? createLogic(G, view) : createLogic(G);
  const step = weapon.update;

  weapon.update = (dt) => {
    step(dt);
    if (view) view.update(dt, weapon.anim);
  };
  weapon.setVisible = (on) => {
    if (view) view.setVisible(on);
  };
  weapon.setView = (n) => {
    if (view) view.setView(n);
  };
  /** Test hook for the screenshot scenarios: holds the gun in a fixed pose (null releases it). */
  weapon.inspect = (spec) => {
    if (view) view.inspect(spec);
  };
  weapon.info = view ? view.info : null;

  if (G.settings) weapon.setView(G.settings.get('view'));
  if (G.events) {
    G.events.on('settings:change', (e) => {
      if (e.key === 'view') weapon.setView(e.value);
    });
  }
  return weapon;
}
