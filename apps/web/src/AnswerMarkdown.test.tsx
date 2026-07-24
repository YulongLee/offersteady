import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnswerMarkdown, normalizeMathMarkdown } from "./AnswerMarkdown";

describe("AnswerMarkdown", () => {
  it("renders inline and display formulas with KaTeX", () => {
    const { container } = render(<AnswerMarkdown content={"行内公式 $E=mc^2$\n\n$$\\frac{a}{b}$$"} />);
    expect(container.querySelectorAll(".katex")).toHaveLength(2);
    expect(container.querySelector(".katex-display")).not.toBeNull();
  });

  it("normalizes alternate LaTeX delimiters without changing code fences", () => {
    const value = String.raw`行内 \(x+y\)，块级 \[\frac{1}{n}\]`
      + "\n\n```text\n"
      + String.raw`\(not-math\)`
      + "\n```";
    const normalized = normalizeMathMarkdown(value);
    expect(normalized).toContain("$x+y$");
    expect(normalized).toContain("$$\n\\frac{1}{n}\n$$");
    expect(normalized).toContain(String.raw`\(not-math\)`);
  });

  it("keeps an unfinished streaming formula readable until it closes", () => {
    const normalized = normalizeMathMarkdown("正在生成 $E = mc");
    expect(normalized).toContain("\\$E = mc");
    const { container } = render(<AnswerMarkdown content={"正在生成 $E = mc"} />);
    expect(container.querySelector(".katex")).toBeNull();
    expect(container.textContent).toContain("$E = mc");
  });
});
