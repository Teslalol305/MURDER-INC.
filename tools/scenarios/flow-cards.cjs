// Pictures of what the flow puts on screen, for a look in the full build: a wave banner with its radio
// line, the refusal at the truck, the debrief card, the death card and a Hold the Block banner.
//
//   node build.mjs --dev --out=dist/dev-flow-full.html
//   node tools/shot.cjs dist/dev-flow-full.html --params "q=test&noaudio=1&autostart=1" --size 800x450 \
//        --timeout 600 --scenario tools/scenarios/flow-cards.cjs
//
// DIRECTOR: reels are taken with game.debugGrab() and the player is moved with player.reset.

'use strict';

const OUT = 'shots/flow/cards-';

module.exports = async (page, h) => {
  const shot = async (name) => {
    await h.frames(1);
    await h.shot(`${OUT}${name}.png`);
  };
  const standAt = (x, z, yaw) =>
    h.eval(([px, pz, y]) => {
      const G = window.__G;
      G.player.reset({ pos: new G.THREE.Vector3(px, 0, pz), yaw: y });
      G.player.invulnerable = true;
    }, [x, z, yaw]);

  await h.eval(() => (__G.player.invulnerable = true));
  await h.eval(() => __G.game.debugGrab());
  await h.skip(15);
  await shot('00-contact-banner');

  const truck = await h.eval(() => ({ x: __G.level.extraction.pos.x, z: __G.level.extraction.pos.z }));
  await standAt(truck.x - 1, truck.z, Math.PI / 2);
  await h.skip(6);
  await shot('01-refusal');

  await h.eval(() => {
    __G.game.debugGrab();
    __G.game.debugGrab();
  });
  await standAt(truck.x - 0.2, truck.z, Math.PI / 2);
  await h.skip(110);
  await shot('02-debrief');

  await h.eval(() => __G.game.redeploy());
  await h.skip(45);
  await h.eval(() => {
    __G.player.invulnerable = false;
    __G.player.damage(1000, null, 'bullet');
  });
  await h.skip(50);
  await shot('03-dead');

  await h.eval(() => __G.game.start({ mode: 'holdout', skipIntro: true }));
  await h.skip(110);
  await shot('04-holdout-wave');
  const errs = await h.errors();
  if (errs.length) throw new Error(errs.slice(0, 3).join(' | '));
};
