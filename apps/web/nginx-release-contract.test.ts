import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

describe("production nginx release contract", () => {
  it("publishes the deployment build manifest without SPA fallback", () => {
    const nginxConfig = readFileSync(
      resolve(process.cwd(), "../../infra/nginx/default.conf"),
      "utf8",
    );

    expect(nginxConfig).toContain("location = /offersteady-build.json");
    expect(nginxConfig).toMatch(
      /location = \/offersteady-build\.json \{[\s\S]*?try_files \$uri =404;/,
    );
    expect(nginxConfig).toMatch(
      /location = \/offersteady-build\.json \{[\s\S]*?Cache-Control "no-store";/,
    );
  });
});
