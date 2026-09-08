import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { HomepageDownloads } from "./HomepageDownloads";
import downloads from "./homepage-downloads.generated.json";

describe("Global homepage downloads", () => {
  it("uses public Global routes with explicit Mac architectures and no account gate", () => {
    render(<HomepageDownloads />);
    expect(screen.getByRole("region", { name: "Download Desktop Companion" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Windows" })).toHaveAttribute("href", downloads.find(e => e.platform === "windows")!.href);
    expect(screen.getByText("macOS").closest("details")).not.toHaveAttribute("open");
    for (const e of downloads) {
      expect(e.href).toMatch(/^\/api\/v1\/web\/downloads\/desktop\/OfferSteady-Companion-Global-/);
      expect(readFileSync("index.html", "utf8")).toContain(e.href);
    }
    expect(screen.queryByText(/Account required to use/)).not.toBeInTheDocument();
    expect(screen.queryByText(/installation notes/)).not.toBeInTheDocument();
    expect(screen.queryByText("Download Desktop Companion")).not.toBeInTheDocument();
  });
  it("filters withdrawn, development, malformed and domestic packages and selects latest", () => {
    const result = execFileSync(process.execPath, ["--input-type=module", "-e", `
      import { publicDownloads } from './scripts/generate-homepage-downloads.mjs';
      const e={platform:'windows',architecture:'x64',version:'1.2.9',distributionStatus:'published',developmentOnly:false,signingStatus:'unsigned',sha256:'a'.repeat(64),fileName:'OfferSteady-Companion-Global-Setup-1.2.9-Windows-x64.exe'};
      const invalid=[{...e,distributionStatus:'withdrawn'},{...e,developmentOnly:true},{...e,sha256:'bad'},{...e,fileName:'OfferSteady-Companion-Setup-1.2.9-Windows-x64.exe'},{...e,signingStatus:'withdrawn'}];
      if(publicDownloads({entries:invalid}).length) throw Error('Unsafe entry accepted');
      const latest=publicDownloads({entries:[e,{...e,version:'1.2.10',fileName:e.fileName.replace('1.2.9','1.2.10')}]});
      if(latest[0].version!=='1.2.10') throw Error('Wrong version');
      console.log('ok');
    `], { encoding: "utf8" });
    expect(result.trim()).toBe("ok");
  });
});
