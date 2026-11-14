import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";

// Supply an existing Playwright installation; no browser downloads are performed.
const { chromium, webkit } = await import(process.env.PLAYWRIGHT_MODULE ?? "playwright");
const webRoot = fileURLToPath(new URL("..", import.meta.url));
const artifacts = resolve(process.env.OFFERSTEADY_REVIEW_ARTIFACTS ?? join(webRoot, "../../artifacts/mobile-scroll-review"));
await mkdir(artifacts, { recursive: true });
const server = await createServer({
  root: webRoot, configFile: join(webRoot, "vite.config.ts"),
  server: { host: "127.0.0.1", port: 0, strictPort: false },
  plugins: [{ name: "isolated-mobile-scroll-review", configureServer(vite) {
    vite.middlewares.use(async (request, response, next) => {
      if (!request.url?.startsWith("/__mobile-scroll__")) return next();
      const html = await vite.transformIndexHtml(request.url, '<!doctype html><html lang="zh-CN"><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="root"></div><script type="module" src="/scripts/fixtures/mobile-scroll.tsx"></script></body></html>');
      response.setHeader("Content-Type", "text/html"); response.end(html);
    });
  } }],
});
await server.listen();
const origin = `http://127.0.0.1:${server.httpServer.address().port}`;
const results = [];
let browser;
try {
  const engine = process.env.BROWSER_ENGINE ?? "chromium";
  browser = await (engine === "webkit" ? webkit : chromium).launch({ headless: true,
    ...(process.env.BROWSER_PATH ? { executablePath: process.env.BROWSER_PATH } : {}),
  });
  for (const viewport of [{ width: 320, height: 568 }, { width: 390, height: 844 }, { width: 430, height: 932 }, { width: 667, height: 375 }]) {
    const context = await browser.newContext({ viewport, isMobile: true, hasTouch: true });
    // Fail closed even if a future component starts a network request.
    await context.route("**/*", route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    const cdp = engine === "chromium" ? await context.newCDPSession(page) : null;
    const swipe = async (selector, distance, x) => {
      const point = await page.locator(selector).evaluate(el => { const r = el.getBoundingClientRect(); return {
        x: Math.min(innerWidth - 15, Math.max(15, r.x + r.width / 2)),
        y: Math.min(innerHeight - 35, Math.max(75, r.y + Math.min(r.height / 2, innerHeight / 2))),
      }; });
      if (x !== undefined) point.x = x;
      if (cdp) await cdp.send("Input.synthesizeScrollGesture", { ...point, yDistance: distance, speed: 4000, gestureSourceType: "touch" });
      // Mobile WebKit has no supported wheel/swipe injection in this runner.
      // It verifies layout, range and scroll events; Chromium verifies real gestures.
      else if (selector.startsWith(".mobile-live-panel") || selector === ".conversation-list") {
        await page.locator(selector).evaluate((el, delta) => el.scrollBy({ top: delta, behavior: "instant" }), -distance);
      } else await page.evaluate(delta => window.scrollBy({ top: delta, behavior: "instant" }), -distance);
      await page.waitForTimeout(100);
    };
    await page.goto(`${origin}/__mobile-scroll__`);
    await page.locator(".answer-markdown").first().waitFor();
    await swipe(".mobile-live-panel", -250);
    assert(await page.locator(".mobile-live-panel").evaluate(el => el.scrollTop > 30), "long answer did not scroll");
    await swipe(".mobile-live-panel", -20_000);
    assert(await page.locator(".mobile-live-panel").evaluate(el => el.scrollHeight - el.scrollTop - el.clientHeight < 3), "answer bottom unreachable");
    await page.getByRole("tab", { name: "对话" }).click();
    const list = page.locator(".conversation-list");
    await page.waitForTimeout(100);
    const range = await list.evaluate(el => el.scrollHeight - el.clientHeight);
    // ConversationMonitor automatically starts at the latest turn.
    assert(range > 100, "transcript has no bounded scroll range; nested container traps touch gestures");
    await swipe(".conversation-list", 250);
    const beforeAppend = await list.evaluate(el => el.scrollTop);
    assert(beforeAppend < range - 30, "swipe on transcript did not reveal earlier turns");
    await page.locator("#append-turn").click();
    await page.waitForTimeout(100);
    assert(Math.abs(await list.evaluate(el => el.scrollTop) - beforeAppend) < 3, "new transcript interrupted manual review");
    await swipe(".conversation-list", -20_000);
    await page.locator("#append-turn").click();
    await page.waitForTimeout(100);
    assert(await list.evaluate(el => el.scrollHeight - el.scrollTop - el.clientHeight < 3), "latest turn not followed at bottom");
    const controls = await page.locator(".mobile-interview-controls").boundingBox();
    assert(controls.y >= 0 && controls.y + controls.height <= viewport.height + 1, "live controls outside viewport");
    results.push({ engine, scrollInput: cdp ? "touch" : "programmatic", viewport, scenario: "live", answerBottom: true, transcriptRange: range, reviewPreserved: true, followsLatest: true });
    await page.screenshot({ path: join(artifacts, `${engine}-${viewport.width}-live.png`) });

    for (const scenario of ["mock-prepare", "mock-answer", "mock-report"]) {
      await page.goto(`${origin}/__mobile-scroll__?scenario=${scenario}`);
      await page.locator(scenario === "mock-report" ? ".mock-report" : ".mock-end").waitFor();
      const scrollBefore = await page.evaluate(() => scrollY);
      // Start on the portrait/question surface, outside a text input's own scroll area.
      await swipe(".mock-page-heading", -250);
      assert(await page.evaluate(() => scrollY) > scrollBefore + 30, `${scenario} page did not scroll`);
      // Keep the gesture outside the native answer textarea, which scrolls its own text.
      for (let attempt = 0; attempt < 30; attempt++) {
        if (await page.evaluate(() => document.documentElement.scrollHeight - scrollY - innerHeight < 3)) break;
        await swipe(".mock-page", -1200, 5);
      }
      const position = await page.evaluate(() => ({ top: scrollY, height: innerHeight, total: document.documentElement.scrollHeight }));
      assert(position.total - position.top - position.height < 3, `${scenario} ${engine} ${viewport.width}: bottom unreachable ${JSON.stringify(position)}`);
      const bottom = page.locator(scenario === "mock-report" ? ".mock-report > a:last-child" : ".mock-end button");
      assert(await bottom.isVisible(), `${scenario} bottom action absent`);
      const bounds = await bottom.boundingBox();
      assert(bounds.y >= 0 && bounds.y + bounds.height <= viewport.height + 1, `${scenario} bottom action clipped`);
      results.push({ engine, scrollInput: cdp ? "touch" : "programmatic", viewport, scenario, bottomReachable: true });
    }
    assert.deepEqual(errors, [], "browser page errors");
    await context.close();
  }
  await writeFile(join(artifacts, `${process.env.BROWSER_ENGINE ?? "chromium"}-results.json`), JSON.stringify(results, null, 2));
  console.log(JSON.stringify({ status: "passed", cases: results.length, artifacts }));
} finally {
  await browser?.close();
  await server.close();
}
