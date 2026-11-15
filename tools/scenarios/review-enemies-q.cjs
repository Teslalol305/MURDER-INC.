'use strict';
module.exports = async (page, h) => {
  await h.skip(3);
  const r = await h.eval((q) => {
    const G = window.__G;
    return G.physics.boxes.filter((b) => b.max.x > q[0] - 1 && b.min.x < q[0] + 1 && b.max.z > q[1] - 1 && b.min.z < q[1] + 1).map((b) => `${b.tag} ${b.playerOnly ? 'PO' : ''}${b.noNav ? 'NN' : ''}${b.bulletOnly ? 'BO' : ''} [${b.min.x.toFixed(2)},${b.min.y.toFixed(2)},${b.min.z.toFixed(2)}]-[${b.max.x.toFixed(2)},${b.max.y.toFixed(2)},${b.max.z.toFixed(2)}]`);
  }, (process.env.RV_Q || '0,0').split(',').map(Number));
  console.log('Q\n' + r.join('\n'));
};
