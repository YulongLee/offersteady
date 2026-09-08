import fs from "node:fs";
import path from "node:path";

const webWorkspaceUrl = process.env.OFFERSTEADY_GLOBAL_WEB_URL?.trim();
const apiBaseUrl = process.env.OFFERSTEADY_GLOBAL_API_BASE_URL?.trim();
if (!webWorkspaceUrl || !apiBaseUrl) {
  throw new Error("Global packaging requires OFFERSTEADY_GLOBAL_WEB_URL and OFFERSTEADY_GLOBAL_API_BASE_URL.");
}
for (const [name, value] of [["OFFERSTEADY_GLOBAL_WEB_URL", webWorkspaceUrl], ["OFFERSTEADY_GLOBAL_API_BASE_URL", apiBaseUrl]]) {
  const parsed = new URL(value);
  if (parsed.protocol !== "https:") throw new Error(`${name} must use HTTPS.`);
  if (["mianshiwen.cn", "www.mianshiwen.cn", "beta.mianshiwen.cn"].includes(parsed.hostname)) {
    throw new Error(`${name} must not point to the Chinese deployment.`);
  }
  if (name === "OFFERSTEADY_GLOBAL_API_BASE_URL" && parsed.pathname.replace(/\/$/, "") !== "/api/v1") {
    throw new Error("OFFERSTEADY_GLOBAL_API_BASE_URL must point to the versioned /api/v1 API root.");
  }
}
const output = path.resolve(import.meta.dirname, "../build/generated/global-runtime-config.json");
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, `${JSON.stringify({ productEdition: "global", releaseChannel: "global", webWorkspaceUrl, apiBaseUrl }, null, 2)}\n`, { mode: 0o600 });
console.log("Prepared isolated Global companion runtime configuration.");
