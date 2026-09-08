import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

export function publicDownloads(manifest) {
  if (!Array.isArray(manifest.entries)) throw new Error("Invalid Global release manifest");
  const targets = [["windows", "x64"], ["macos", "arm64"], ["macos", "x64"]];
  return targets.flatMap(([platform, architecture]) => {
    const entry = manifest.entries.filter(e => e.platform === platform && e.architecture === architecture
      && e.distributionStatus === "published" && e.signingStatus !== "withdrawn" && e.signingStatus !== "local-development"
      && e.developmentOnly === false && /^[a-f0-9]{64}$/i.test(e.sha256 ?? "")
      && /^OfferSteady-Companion-Global-[A-Za-z0-9.-]+\.(dmg|exe)$/.test(e.fileName ?? "")
      && e.fileName.endsWith(platform === "windows" ? "-Windows-x64.exe" : `-macOS-${architecture}.dmg`)
      && /^\d+(\.\d+)+$/.test(e.version ?? ""))
      .sort((a, b) => b.version.localeCompare(a.version, "en", { numeric: true }))[0];
    return entry ? [{ platform, architecture, version: entry.version, minimumOs: entry.minimumOs,
      signingStatus: entry.signingStatus, href: `/api/v1/web/downloads/desktop/${encodeURIComponent(entry.fileName)}` }] : [];
  });
}

export async function generateHomepageDownloads(root) {
  const manifest = JSON.parse(await readFile(resolve(root, "../backend/app/global_desktop_release_manifest.json"), "utf8"));
  const downloads = publicDownloads(manifest);
  await writeFile(resolve(root, "src/homepage-downloads.generated.json"), JSON.stringify(downloads, null, 2) + "\n");
  const path = resolve(root, "index.html");
  const source = await readFile(path, "utf8");
  const pattern = /<!-- homepage-downloads:start -->[\s\S]*?<!-- homepage-downloads:end -->/;
  if (!pattern.test(source)) throw new Error("Homepage download markers missing");
  const links = downloads.map(e => `<a href="${e.href}">${e.platform === "windows" ? "Download for Windows" : e.architecture === "arm64" ? "macOS Apple Silicon" : "macOS Intel"}</a>`).join(" · ");
  await writeFile(path, source.replace(pattern, `<!-- homepage-downloads:start --><section aria-label="Download Desktop Companion"><p>${links || "Downloads are currently unavailable."}</p></section><!-- homepage-downloads:end -->`));
}
