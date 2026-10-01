// Local synthetic report only. Never authenticate to or mutate production.
// Run with the bundled Playwright runtime and the dev preview on port 4291.
const { chromium } = require('playwright');
const { mkdir, readFile } = require('node:fs/promises');
const path = require('node:path');
const JSZip = require('jszip');

(async () => {
  const output = path.resolve(__dirname, '../../../artifacts/mock-interview-word-qa');
  await mkdir(output, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    for (const width of [1440, 390]) {
      const page = await browser.newPage({ viewport: { width, height: 1000 }, acceptDownloads: true });
      const errors = [];
      const requests = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('request', request => requests.push(request.url()));
      await page.goto('http://127.0.0.1:4291/test-previews/mock-interview.html?view=report');
      await page.getByText('部分练习报告', { exact: true }).waitFor();
      await page.evaluate(() => document.fonts.ready);
      const button = page.getByRole('button', { name: '下载 Word', exact: true });
      await button.waitFor();
      if (requests.some(url => /\/docx(?:\.js|\/)/.test(url))) throw new Error('Word dependency loaded before download');
      const requestStart = requests.length;
      const downloadEvent = page.waitForEvent('download');
      await button.click();
      const download = await downloadEvent;
      if (await download.failure()) throw new Error('Browser download failed');
      if (!download.suggestedFilename().endsWith('.docx')) throw new Error('Wrong download extension');
      const file = path.join(output, `report-${width}.docx`);
      await download.saveAs(file);
      const zip = await JSZip.loadAsync(await readFile(file));
      const xml = await zip.file('word/document.xml').async('string');
      for (const text of ['总体评分：78 / 100', '部分练习报告', '回答中的证据', '下一次练习重点']) {
        if (!xml.includes(text)) throw new Error(`Missing report content: ${text}`);
      }
      if (requests.slice(requestStart).some(url => url.includes('/api/'))) throw new Error('Download made an API request');
      if (await button.isDisabled()) throw new Error('Download button did not recover');
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
      if (overflow || errors.length) throw new Error(JSON.stringify({ width, overflow, errors }));
      await page.screenshot({ path: path.join(output, `report-${width}.png`), fullPage: true });
      console.log(`${width}px: editable DOCX downloaded; lazy loading, no API request, no overflow or page errors`);
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
