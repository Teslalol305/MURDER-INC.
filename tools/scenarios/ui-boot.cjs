// The boot screen put back up mid-load at one size, with whatever fonts the page has (the harness has no
// network, so this is the fallback-face case: the wordmark must stay inside the screen).
//
//   node tools/shot.cjs dist/dev-fix-ui.html --size 400x760 --params "q=test&noaudio=1" --scenario tools/scenarios/ui-boot.cjs
module.exports = async (page, h) => {
  const { width, height } = page.viewportSize();
  await h.eval(() => {
    const boot = document.getElementById('boot');
    boot.hidden = false;
    boot.classList.remove('done');
    document.getElementById('boot-msg').textContent = 'Waiting on the next train';
  });
  await h.wait(300);
  await h.frames(1);
  const m = await h.eval(() => {
    const mark = document.querySelector('.boot-mark');
    const r = mark.getBoundingClientRect();
    const range = document.createRange();
    range.selectNodeContents(mark);
    const t = range.getBoundingClientRect();
    return { right: Math.round(t.right), left: Math.round(t.left), lines: Math.round(r.height / parseFloat(getComputedStyle(mark).lineHeight)), vw: innerWidth, font: getComputedStyle(mark).fontFamily.split(',')[0], anton: document.fonts.check('16px Anton') };
  });
  console.error(`BOOT ${width}x${height} ${JSON.stringify(m)}`);
  await h.shot(`shots/ui/boot-${width}x${height}.png`);
  if (m.right > m.vw - 8 || m.left < 0) throw new Error(`the wordmark runs off the screen: ${JSON.stringify(m)}`);
};
