import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const sourceHtml = readFileSync(resolve(process.cwd(), "index.html"), "utf8");

describe("Baidu site verification", () => {
  it("publishes the approved marker exactly once inside the document head", () => {
    const marker =
      '<meta name="baidu-site-verification" content="codeva-QBTtniJaXE" />';
    const head = sourceHtml.match(/<head>([\s\S]*?)<\/head>/)?.[1] ?? "";

    expect(head).toContain(marker);
    expect(head).toContain('<meta name="baidu-site-verification" content="codeva-Z0cblvEvbJ" />');
    expect(sourceHtml.match(/codeva-QBTtniJaXE/g)).toHaveLength(1);
    expect(sourceHtml.match(/codeva-Z0cblvEvbJ/g)).toHaveLength(1);
    expect(sourceHtml.match(/name="baidu-site-verification"/g)).toHaveLength(2);
  });
});
