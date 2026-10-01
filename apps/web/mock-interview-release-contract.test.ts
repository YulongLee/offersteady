import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("mock interview production routes", () => {
  const config = readFileSync(resolve(process.cwd(), "../../infra/nginx/default.conf"), "utf8");
  it("serves the mock list and individual session on direct navigation or refresh", () => {
    const route = config.split("\n").find(line => line.includes("location ~") && line.includes("mock-interviews"))!;
    const expression = new RegExp(route.trim().slice("location ~ ".length).replace(/ \{$/, ""));
    expect(expression.test("/app/mock-interviews")).toBe(true);
    expect(expression.test("/app/mock-interviews/mock-example-123")).toBe(true);
    expect(expression.test("/app/mock-interviews/mock-example-123/unknown")).toBe(false);
    expect(expression.test("/app/interviews/session-example/live")).toBe(true);
    const block = config.slice(config.indexOf(route)).split("\n  }")[0];
    expect(block).toContain("try_files /index.html =404;");
    expect(block).toContain('X-Robots-Tag "noindex, follow"');
  });
  it("keeps WebSocket upgrade available for the isolated control endpoint", () => {
    const block = config.slice(config.indexOf("location /api/ {")).split("\n  }")[0];
    expect(block).toContain("proxy_set_header Upgrade $http_upgrade;");
    expect(block).toContain('proxy_set_header Connection "upgrade";');
    expect(block).toContain("proxy_buffering off;");
  });
});
