import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

describe("production nginx release contract", () => {
  it("normalizes only public www HTML without a host-wide session redirect", () => {
    const nginxConfig = readFileSync(
      resolve(process.cwd(), "../../infra/nginx/default.conf"),
      "utf8",
    );

    expect(nginxConfig).not.toMatch(
      /if \(\$host = www\.mianshiwen\.cn\)[\s\S]*?return 30[18] https:\/\/mianshiwen\.cn/,
    );
    expect(nginxConfig).toContain('map "$request_method:$host:$uri" $redirect_public_www');
    expect(nginxConfig).toContain('if ($redirect_public_www) { return 308 https://mianshiwen.cn$request_uri; }');
    const rule = nginxConfig.match(/~\^\(GET\|HEAD\):[^\n]+/)?.[0] ?? "";
    expect(rule).not.toMatch(/login|api|app|invite/);
  });

  it("serves legal HTML without noindex while preserving private route noindex", () => {
    const config = readFileSync(resolve(process.cwd(), "../../infra/nginx/default.conf"), "utf8");
    const legal = config.match(/location ~ \^\/\(terms\|privacy\)[\s\S]*?\n  \}/)?.[0] ?? "";
    expect(legal).toContain('try_files /$1.html =404;');
    expect(legal).not.toContain('noindex');
    expect(config).toMatch(/location ~ \^\/\(\?:login\|error[\s\S]*?X-Robots-Tag "noindex, follow"/);
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

  it("serves homepage media files directly without falling back to the SPA", () => {
    const nginxConfig = readFileSync(
      resolve(process.cwd(), "../../infra/nginx/default.conf"),
      "utf8",
    );

    expect(nginxConfig).toMatch(
      /location \/media\/ \{[\s\S]*?try_files \$uri =404;/,
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

  it("serves the partner program route through the authenticated SPA", () => {
    const nginxConfig = readFileSync(
      resolve(process.cwd(), "../../infra/nginx/default.conf"),
      "utf8",
    );

    expect(nginxConfig).toContain("/partner-program");
    expect(nginxConfig).toMatch(
      /location ~ \^\/\(\?:login[\s\S]*?try_files \/index\.html =404;/,
    );
  });
});
