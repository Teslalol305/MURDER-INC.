// Shared helpers for the fx scenarios (not a scenario itself).

'use strict';

/**
 * Switches the block to 'day' or 'night'. With an atmosphere that has setTime() (CONTRACT 11.1) that
 * is all it takes; with the stub atmosphere a stand-in rig is dialled in by hand: a high warm sun, a
 * bright sky, pale haze, lower exposure. Returns 'atmos' or 'stand-in'.
 */
exports.setTime = (h, time) =>
  h.eval((time) => {
    const G = window.__G;
    const atmos = G.atmos;
    let how = 'stand-in';
    if (atmos && typeof atmos.setTime === 'function') {
      atmos.setTime(time);
      how = 'atmos';
    } else {
      const day = time === 'day';
      const look = G.config.look;
      window.__nightLook = window.__nightLook || { exposure: G.render.look.exposure, vignette: G.render.look.vignette };
      G.scene.traverse((o) => {
        if (!o.isHemisphereLight) return;
        o.color.set(day ? 0xbcd6ff : look.ambient.sky);
        o.groundColor.set(day ? 0x9c8f7c : look.ambient.ground);
        o.intensity = day ? 1.5 : look.ambient.intensity;
      });
      if (atmos && atmos.sun) {
        atmos.sun.color.set(day ? 0xfff0d6 : look.sun.color);
        atmos.sun.intensity = day ? 4.2 : look.sun.intensity;
      }
      if (G.scene.background && G.scene.background.isColor) G.scene.background.set(day ? 0x6fa8e8 : look.sky.zenith);
      if (G.scene.fog) {
        G.scene.fog.color.set(day ? 0xb4cbe6 : look.fog.color);
        G.scene.fog.density = day ? 0.0035 : look.fog.density;
      }
      G.render.look.exposure = day ? 0.8 : window.__nightLook.exposure;
      G.render.look.vignette = day ? 0.15 : window.__nightLook.vignette;
      atmos.time = time; // what the real module exposes: the effects read it
    }
    return how;
  }, time);

/** Throws when the page logged an error. */
exports.noErrors = async (h) => {
  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
};
