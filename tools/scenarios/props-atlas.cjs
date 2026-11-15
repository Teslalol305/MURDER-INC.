// Writes the prop atlas and the billboard face (the two sheets the props draw themselves) to PNG files,
// straight from their canvases: no frame is rendered, so this is quick even on a busy machine.
//
//   node build.mjs --dev --only=props --out=dist/dev-props.html
//   node tools/shot.cjs dist/dev-props.html --params "q=medium&noaudio=1" --scenario tools/scenarios/props-atlas.cjs
//
// Output: shots/props/atlas.png (2048 × 1024 at medium quality and up, half that below) and
// shots/props/billboard.png. Look at them: every label, plate and mark the props carry is on these two.

const fs = require('node:fs');
const path = require('node:path');

const OUT = process.env.PROPS_OUT || 'shots/props';

module.exports = async (page, h) => {
  const sheets = await h.eval(() => {
    const G = window.__G;
    const grab = (name, slot) => {
      let canvas = null;
      G.props.build(name).object.traverse((o) => {
        if (o.isMesh && (o.name === slot || (slot === '#own' && o.name.startsWith('#own'))) && o.material.map) canvas = o.material.map.image;
      });
      // Flatten onto mid grey so that white-on-nothing marks can be seen.
      const flat = document.createElement('canvas');
      flat.width = canvas.width;
      flat.height = canvas.height;
      const ctx = flat.getContext('2d');
      ctx.fillStyle = '#4a4d52';
      ctx.fillRect(0, 0, flat.width, flat.height);
      ctx.drawImage(canvas, 0, 0);
      return { w: canvas.width, h: canvas.height, png: flat.toDataURL('image/png') };
    };
    return { atlas: grab('taxi', '@decal'), billboard: grab('billboard', '#own') };
  });
  fs.mkdirSync(OUT, { recursive: true });
  for (const [name, sheet] of Object.entries(sheets)) {
    const file = path.join(OUT, `${name}.png`);
    fs.writeFileSync(file, Buffer.from(sheet.png.split(',')[1], 'base64'));
    console.error(`${file}: ${sheet.w} × ${sheet.h}`);
  }
  const errors = await h.errors();
  if (errors.length) throw new Error(`page errors: ${errors[0]}`);
};
