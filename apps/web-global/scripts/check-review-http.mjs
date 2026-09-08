// Read-only, no-JavaScript checks. --baseline reports deployed content without
// asserting it equals this development revision. Never calls payment/auth APIs.
import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
const catalogue = JSON.parse(await readFile(new URL("../src/public-review-pages.json", import.meta.url), "utf8"));
const base = process.argv[2] || "http://127.0.0.1:4273";
const baseline = process.argv.includes("--baseline");
const slugs = ["", "pricing", "terms", "privacy", "refund-policy", "contact", "about", "security", "robots.txt", "sitemap.xml"];
let failed = false;
for (const slug of slugs) {
  try {
    const result = execFileSync("curl", ["-sS", "--max-time", "15", "-w", "\n%{http_code}", `${base}/${slug}`], { encoding: "utf8" });
    const html = result.slice(0, -4), status = Number(result.slice(-3));
    const page = catalogue.pages.find(page => page.slug === slug);
    const expectedH1 = slug ? page?.h1 : catalogue.heroTitle;
    const title = html.match(/<title>(.*?)<\/title>/s)?.[1];
    const h1 = html.match(/<h1[^>]*>(.*?)<\/h1>/s)?.[1];
    const description = html.match(/name="description"\s+content="([^"]+)"/s)?.[1];
    const canonical = html.match(/rel="canonical"\s+href="([^"]+)"/s)?.[1];
    const oldCopyCount = (html.match(/coming soon|checkout is not active|paid checkout/gi) ?? []).length;
    const checks = [status === 200];
    if (expectedH1) {
      checks.push(Boolean(title && h1 && description), canonical === `${catalogue.siteUrl}/${slug}`);
      if (!baseline) checks.push(h1 === expectedH1, html.includes(catalogue.operator), html.includes(catalogue.supportEmail), oldCopyCount === 0);
      if (!baseline && page) checks.push(html.includes(page.sections[0].paragraphs[0]));
      if (!baseline && slug === "pricing") for (const plan of page.plans) checks.push(html.includes(plan.price + plan.term), html.includes(plan.billing), html.includes(plan.accessStarts));
    } else if (slug === "robots.txt") checks.push(html.includes(`Sitemap: ${catalogue.siteUrl}/sitemap.xml`));
    else checks.push(html.includes("<urlset"), ...catalogue.pages.map(page => html.includes(`<loc>${catalogue.siteUrl}/${page.slug}</loc>`)));
    const passed = checks.every(Boolean);
    failed ||= !passed;
    console.log(JSON.stringify({ path: `/${slug}`, status, title, h1, canonical, descriptionPresent: Boolean(description), oldCopyCount, passed, baseline }));
  } catch (error) {
    failed = true;
    console.log(JSON.stringify({ path: `/${slug}`, passed: false, error: error.message.split("\n")[0] }));
  }
}
if (failed) process.exitCode = 1;
