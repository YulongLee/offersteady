// Local synthetic visual QA; requires Playwright through NODE_PATH or project deps.
const { chromium } = require('playwright');
const { mkdir } = require('node:fs/promises');
const path = require('node:path');

(async () => {
  const output = path.resolve(__dirname, '../../..', 'artifacts/mock-interview-qa');
  await mkdir(output, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    for (const width of [1440, 390]) {
      for (const view of ['home', 'preparation', 'workbench', 'report']) {
        const page = await browser.newPage({ viewport: { width, height: 1000 } });
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        await page.goto(`http://127.0.0.1:4291/test-previews/mock-interview.html?view=${view}`);
        await page.getByRole('heading', { level: 1 }).waitFor();
        if (view === 'home') await page.getByText('本场免费', { exact: true }).waitFor();
        if (view === 'preparation') await page.getByText('● 助手已就绪', { exact: true }).waitFor();
        if (view === 'workbench') await page.getByRole('textbox', { name: '你的回答' }).waitFor();
        if (view === 'report') await page.getByText('部分练习报告', { exact: true }).waitFor();
        await page.evaluate(async () => {
          await document.fonts.ready;
          await Promise.all([...document.images].map(image => image.decode()));
        });
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
        if (overflow || errors.length) throw new Error(JSON.stringify({ width, view, overflow, errors }));
        await page.screenshot({ path: path.join(output, `${view}-${width}.png`), fullPage: true });
        if (view === 'workbench') {
          const play = page.getByRole('button', { name: '播放声波演示（合成测试音）' });
          await play.click();
          await page.getByText('面试官正在提问', { exact: true }).waitFor();
          await page.waitForFunction(() => [...document.querySelectorAll('.mock-waveform > span')].some(bar => bar.style.transform !== 'scaleY(0.12)'));
          const first = await page.locator('.mock-waveform').innerHTML();
          await page.waitForFunction(previous => document.querySelector('.mock-waveform').innerHTML !== previous, first);
          await page.screenshot({ path: path.join(output, `speaking-${width}.png`), fullPage: true });
          if (width === 1440) {
            await page.getByText('正在聆听你的回答', { exact: true }).waitFor({ timeout: 8000 });
            const idle = await page.locator('.mock-waveform > span').evaluateAll(bars => bars.every(bar => bar.style.transform === 'scaleY(0.12)'));
            if (!idle) throw new Error('Natural completion left the waveform moving');
            await play.click();
            await page.getByText('面试官正在提问', { exact: true }).waitFor();
          }
          await page.getByRole('button', { name: '停止演示', exact: true }).click();
          await page.getByText('语音播放已暂停', { exact: true }).waitFor();
          const stopped = await page.locator('.mock-waveform > span').evaluateAll(bars => bars.every(bar => bar.style.transform === 'scaleY(0.12)'));
          if (!stopped) throw new Error('Stop left the waveform moving');
          await page.emulateMedia({ reducedMotion: 'reduce' });
          await play.click();
          await page.getByText('面试官正在提问', { exact: true }).waitFor();
          const still = await page.locator('.mock-waveform > span').evaluateAll(bars => bars.every(bar => bar.style.transform === 'scaleY(0.12)'));
          if (!still) throw new Error('Reduced motion did not disable moving bars');
          await page.getByRole('button', { name: '停止演示', exact: true }).click();
          if (errors.length) throw new Error(JSON.stringify(errors));
          console.log(`playback ${width}px: actual audio changes bars; stop and reduced motion verified`);
        }
        console.log(`${view} ${width}px: no overflow, no page errors`);
        await page.close();
      }
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
