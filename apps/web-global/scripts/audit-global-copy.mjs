import fs from "node:fs";
import path from "node:path";

const projectRoot = path.resolve(import.meta.dirname, "..");
const generatedPath = path.join(projectRoot, "src/global-copy.generated.ts");
const generated = fs.readFileSync(generatedPath, "utf8");
if (/:[ \t]*"[^"]*[\u3400-\u9fff]/.test(generated)) {
  throw new Error("Generated Global copy contains a Chinese translation value.");
}
for (const fallback of [
  "Additional product information is available for this step.",
  "Continue the interview workflow and use AI output only as guidance based on your real experience.",
  "Manage the materials selected for this session. Only use information you can verify.",
  "Review the current credit, membership, and pricing information shown by the service.",
]) {
  if (generated.includes(fallback)) throw new Error(`Generated Global copy still contains a generic fallback: ${fallback}`);
}

const catalogue = JSON.parse(fs.readFileSync(path.join(projectRoot, "scripts/global-copy-catalog.json"), "utf8"));
if (Object.values(catalogue).some(value => typeof value !== "string" || !value.trim())) {
  throw new Error("Global copy catalogue contains an empty translation.");
}

const requiredRoutes = [
  "/", "/login", "/terms", "/privacy", "/app", "/app/written-exams",
  "/app/interviews/new", "/app/written-exams/new", "/app/library", "/app/billing",
  "/app/guide", "/app/devices", "/app/settings",
];
const routes = fs.readFileSync(path.join(projectRoot, "src/routes.ts"), "utf8");
for (const route of requiredRoutes) {
  if (!routes.includes(`"${route}"`)) throw new Error(`Missing Global route coverage: ${route}`);
}
for (const dynamicRoute of ["/app/interviews/${id}/prepare", "/app/interviews/${id}/live", "/app/interviews/${id}/review", "/invite/${code}"]) {
  if (!routes.includes(dynamicRoute)) throw new Error(`Missing Global dynamic route coverage: ${dynamicRoute}`);
}

const html = fs.readFileSync(path.join(projectRoot, "index.html"), "utf8");
if (!html.includes('<html lang="en">')) throw new Error("Global HTML language must be English.");
if (html.includes("mianshiwen.cn") || html.includes("baidu-site-verification")) {
  throw new Error("Global HTML must not inherit the Chinese production domain or Baidu verification.");
}

const auditPublicTree = directory => {
  if (!fs.existsSync(directory)) return;
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const filePath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      auditPublicTree(filePath);
      continue;
    }
    if (!entry.isFile() || !/\.(?:html|json|txt|xml|svg|css)$/i.test(entry.name)) continue;
    const value = fs.readFileSync(filePath, "utf8");
    const valueWithoutRequiredLegalName = value.replaceAll("杭州临平知界智能技术工作室（个体工商户）", "");
    if (/[\u3400-\u9fff]/.test(valueWithoutRequiredLegalName) || /mianshiwen\.cn|baidu-site-verification/i.test(value)) {
      throw new Error(`Global public asset inherits domestic content: ${path.relative(projectRoot, filePath)}`);
    }
  }
};
auditPublicTree(path.join(projectRoot, "public"));

const styles = fs.readFileSync(path.join(projectRoot, "src/styles.css"), "utf8");
for (const responsiveRule of [
  "@media (max-width: 1050px)",
  "@media (max-width: 720px)",
  ".global-billing-hero, .global-account-grid { grid-template-columns: 1fr; }",
  ".material-tabs { grid-template-columns: 1fr; }",
]) {
  if (!styles.includes(responsiveRule)) throw new Error(`Missing Global responsive rule: ${responsiveRule}`);
}
console.log("Global copy, route, and public metadata audit passed.");
