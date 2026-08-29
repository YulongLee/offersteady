import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const productionCaddyConfig = readFileSync(
  resolve(process.cwd(), "../../infra/caddy/Caddyfile.production"),
  "utf8",
);

describe("production Caddy release contract", () => {
  it("flushes realtime transcript SSE without response compression", () => {
    const sseHandle = productionCaddyConfig.match(
      /@realtime_sse path_regexp realtime_sse[^\n]+\n\s*handle @realtime_sse \{[\s\S]*?\n\s*\}/,
    )?.[0] ?? "";

    expect(sseHandle).toContain(
      "^/api/v1/realtime-speech/sessions/[^/]+/stream$",
    );
    expect(sseHandle).toContain('Cache-Control "no-cache, no-transform"');
    expect(sseHandle).toContain("flush_interval -1");
    expect(sseHandle).not.toMatch(/\bencode\b/);
  });

  it("keeps compression enabled for ordinary public traffic", () => {
    expect(productionCaddyConfig).toMatch(
      /handle \{\s*encode gzip\s*reverse_proxy 127\.0\.0\.1:8080\s*\}/,
    );
  });
});
