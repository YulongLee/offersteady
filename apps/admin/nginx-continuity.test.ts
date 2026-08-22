import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

describe("admin nginx backend continuity contract", () => {
  it("re-resolves the Backend Compose service and preserves the complete request URI", () => {
    const nginxConfig = readFileSync(
      resolve(process.cwd(), "../../infra/nginx/admin.conf"),
      "utf8",
    );

    expect(nginxConfig).toContain("resolver 127.0.0.11 valid=10s ipv6=off;");
    expect(nginxConfig).toContain("set $admin_backend_origin http://backend:8000;");
    expect(nginxConfig).toContain("proxy_pass $admin_backend_origin$request_uri;");
    expect(nginxConfig).not.toContain("proxy_pass http://backend:8000;");
  });
});
