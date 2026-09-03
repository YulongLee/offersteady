import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

describe("production nginx release contract", () => {
  it("serves the www host directly so Baidu can verify that exact site property", () => {
    const nginxConfig = readFileSync(
      resolve(process.cwd(), "../../infra/nginx/default.conf"),
      "utf8",
    );

    expect(nginxConfig).not.toMatch(
      /if \(\$host = www\.mianshiwen\.cn\)[\s\S]*?return 30[18] https:\/\/mianshiwen\.cn/,
    );
  });

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

  it("proxies realtime transcript SSE without websocket upgrade or buffering", () => {
    const nginxConfig = readFileSync(
      resolve(process.cwd(), "../../infra/nginx/default.conf"),
      "utf8",
    );
    const sseLocation = nginxConfig.match(
      /location ~ \^\/api\/v1\/realtime-speech\/sessions\/\[\^\/\]\+\/stream\$ \{[\s\S]*?\n  \}/,
    )?.[0] ?? "";

    expect(sseLocation).toContain('proxy_set_header Connection "";');
    expect(sseLocation).toContain("proxy_buffering off;");
    expect(sseLocation).toContain("proxy_cache off;");
    expect(sseLocation).toContain("gzip off;");
    expect(sseLocation).toContain("proxy_read_timeout 3600s;");
    expect(sseLocation).not.toContain("proxy_set_header Upgrade");
  });

  it("serves both written exam workbench routes through the authenticated SPA", () => {
    const nginxConfig = readFileSync(
      resolve(process.cwd(), "../../infra/nginx/default.conf"),
      "utf8",
    );

    expect(nginxConfig).toContain("/written-exams(?:/new)?");
    expect(nginxConfig).toMatch(
      /location ~ \^\/\(\?:login[\s\S]*?try_files \/index\.html =404;/,
    );
  });
});
