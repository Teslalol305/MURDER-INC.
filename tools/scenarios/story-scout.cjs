// Scouting pictures for the story's camera work: a list of fixed cameras over the block, one picture
// each, optionally with the Vultures of a level standing where the level puts them.
//
//   SCOUT='[{"name":"a","cam":[x,y,z,lookX,lookY,lookZ],"fov":50}, …]' node tools/shot.cjs dist/dev-all.html \
//        --size 640x360 --params "shot=1&nohud=1&noaudio=1&q=medium" --scenario tools/scenarios/story-scout.cjs
//   SCOUT_TIME=night switches the look; SCOUT_LEVEL=n (1-based) sets that level up first (patrol, reel, crates);
//   SCOUT_OUT names the folder (default shots/scout).

module.exports = async (page, h) => {
  const list = JSON.parse(process.env.SCOUT || '[]');
  const out = process.env.SCOUT_OUT || 'shots/scout';
  if (process.env.SCOUT_TIME) await h.eval((t) => window.__G.atmos.setTime(t), process.env.SCOUT_TIME);
  if (process.env.SCOUT_LEVEL) {
    await h.eval((n) => {
      const game = window.__G.game;
      if (typeof game.debugLevel === 'function') game.debugLevel(n - 1);
    }, Number(process.env.SCOUT_LEVEL));
  }
  await h.skip(20);
  for (const item of list) {
    await h.eval((s) => window.__setShot({ cam: s.cam.join(','), fov: s.fov || 50 }), item);
    if (item.skip) await h.skip(item.skip);
    await h.frames(2);
    await h.shot(`${out}/${item.name}.png`);
  }
  await contactSheet(page, list.map((item) => item.name), out, Number(process.env.SCOUT_COLS) || 3);
};

/** All the pictures on one sheet (shots/scout/sheet.png), captioned: one image to look at instead of twenty. */
async function contactSheet(page, names, out, cols) {
  const fs = require('node:fs');
  const path = require('node:path');
  const root = path.resolve(__dirname, '../..');
  const cells = names
    .map((name) => {
      const data = fs.readFileSync(path.join(root, out, `${name}.png`)).toString('base64');
      return `<figure><img src="data:image/png;base64,${data}"><figcaption>${name}</figcaption></figure>`;
    })
    .join('');
  const sheet = await page.context().newPage();
  const width = Number(process.env.SCOUT_SHEET_W) || 1440;
  await sheet.setViewportSize({ width, height: 800 });
  await sheet.setContent(
    `<style>body{margin:0;background:#111;display:grid;grid-template-columns:repeat(${cols},1fr);gap:4px;padding:4px}` +
      'figure{margin:0;position:relative}img{width:100%;display:block}' +
      'figcaption{position:absolute;left:0;top:0;background:#000c;color:#ffd84a;font:700 15px/1.4 monospace;padding:1px 7px}</style>' +
      cells,
  );
  await sheet.screenshot({ path: path.join(root, out, process.env.SCOUT_SHEET || 'sheet.png'), fullPage: true });
  await sheet.close();
}
