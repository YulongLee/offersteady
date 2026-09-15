import { readFile } from "node:fs/promises";
import { assertCurrentPricing, loadProductionPricing } from "../pricing-static.mjs";
const html = await readFile(new URL("../dist/seo/pricing.html", import.meta.url), "utf8");
const pricing = await loadProductionPricing();
assertCurrentPricing(html, pricing);
console.log("PASS: built pricing matches current production catalogue (" + pricing.catalog.length + " products), snapshot < 24h");
