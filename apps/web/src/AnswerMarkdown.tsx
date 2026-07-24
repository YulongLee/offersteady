import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";

interface Props {
  readonly content: string;
}

const normalizeTextSegment = (value: string) => {
  const normalized = value
    .replace(/\$\$([\s\S]*?)\$\$/g, (_, expression: string) => `\n$$\n${expression.trim()}\n$$\n`)
    .replace(/\\\[([\s\S]*?)\\\]/g, (_, expression: string) => `\n$$\n${expression.trim()}\n$$\n`)
    .replace(/\\\(([\s\S]*?)\\\)/g, (_, expression: string) => `$${expression.trim()}$`);

  const displayDelimiters: number[] = [];
  const inlineDelimiters: number[] = [];
  for (let index = 0; index < normalized.length; index += 1) {
    if (normalized[index] !== "$" || normalized[index - 1] === "\\") continue;
    if (normalized[index + 1] === "$") {
      displayDelimiters.push(index);
      index += 1;
    } else {
      inlineDelimiters.push(index);
    }
  }

  let protectedValue = normalized;
  if (inlineDelimiters.length % 2 === 1) {
    const index = inlineDelimiters.at(-1)!;
    protectedValue = `${protectedValue.slice(0, index)}\\$${protectedValue.slice(index + 1)}`;
  }
  if (displayDelimiters.length % 2 === 1) {
    const index = displayDelimiters.at(-1)!;
    protectedValue = `${protectedValue.slice(0, index)}\\$\\$${protectedValue.slice(index + 2)}`;
  }
  return protectedValue;
};

export const normalizeMathMarkdown = (value: string) => {
  const fencedCode = /(```[\s\S]*?(?:```|$)|~~~[\s\S]*?(?:~~~|$))/g;
  return value
    .split(fencedCode)
    .map(part => part.startsWith("```") || part.startsWith("~~~") ? part : normalizeTextSegment(part))
    .join("");
};

export function AnswerMarkdown({ content }: Props) {
  return <div className="answer-markdown">
    <ReactMarkdown
      remarkPlugins={[remarkMath]}
      rehypePlugins={[[rehypeKatex, { strict: "ignore", throwOnError: false }]]}
    >
      {normalizeMathMarkdown(content)}
    </ReactMarkdown>
  </div>;
}
