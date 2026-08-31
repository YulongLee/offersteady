import { describe, expect, it } from "vitest";

import { stabilizeVisibleTranscriptText } from "./speaker";

describe("visible transcript stability", () => {
  it("keeps append-only growth immediate", () => {
    expect(stabilizeVisibleTranscriptText("请介绍项目", "请介绍项目的性能优化", false))
      .toBe("请介绍项目的性能优化");
  });

  it("does not retract already visible text", () => {
    expect(stabilizeVisibleTranscriptText("请介绍项目的性能优化", "请介绍项目", false))
      .toBe("请介绍项目的性能优化");
  });

  it("allows a correction inside the bounded mutable tail", () => {
    const current = "请介绍一下你在上一家公司负责的核心项目上线";
    const incoming = "请介绍一下你在上一家公司负责的核心项目复盘结果";
    expect(stabilizeVisibleTranscriptText(current, incoming, false)).toBe(incoming);
  });

  it("blocks equal and longer revisions that rewrite the stable prefix", () => {
    const current = "这是已经展示给用户的完整面试问题内容";
    const equalRewrite = "那是模型重新生成给用户的完整面试问题内容";
    const longerRewrite = `能否重新改写${current}并继续追加`;
    expect(stabilizeVisibleTranscriptText(current, equalRewrite, false)).toBe(current);
    expect(stabilizeVisibleTranscriptText(current, longerRewrite, false)).toBe(current);
    expect(stabilizeVisibleTranscriptText(current, longerRewrite, true)).toBe(current);
  });

  it("uses Unicode code points so emoji do not split the tail boundary", () => {
    const current = "已稳定的前缀内容支持😀项目旧方案";
    const incoming = "已稳定的前缀内容支持😀项目新方案与复盘";
    expect(stabilizeVisibleTranscriptText(current, incoming, false)).toBe(incoming);
  });
});
