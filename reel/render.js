// Renders reel.html frame by frame and pipes PNGs into ffmpeg.
// Usage: node render.js [out.mp4]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');

const FPS = 30;
const out = process.argv[2] || path.join(__dirname, 'reel_silent.mp4');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  await page.addInitScript(() => { window.__RENDERING__ = true; });
  await page.goto('file://' + path.join(__dirname, 'reel.html'));
  await page.evaluate(() => document.fonts.ready);
  const duration = await page.evaluate(() => window.DURATION);
  const frames = Math.round(duration * FPS);

  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', out], { stdio: ['pipe', 'inherit', 'inherit'] });

  for (let i = 0; i < frames; i++) {
    const b64 = await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/png').split(',')[1]; }, i / FPS);
    if (!ff.stdin.write(Buffer.from(b64, 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();
  console.log(`rendered ${frames} frames -> ${out}`);
})();
