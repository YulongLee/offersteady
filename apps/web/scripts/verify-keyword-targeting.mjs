import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(new URL("..", import.meta.url).pathname);
const files = {
  homepage: resolve(root, "index.html"),
  realtime: resolve(root, "public/seo/realtime-interview.html"),
  technical: resolve(root, "public/seo/ai-interview-assistant.html"),
  pricing: resolve(root, "public/seo/pricing.html"),
  features: resolve(root, "public/seo/features.html"),
};
const contents = Object.fromEntries(await Promise.all(Object.entries(files).map(async ([key, file]) => [key, await readFile(file, "utf8")] )));
const checks = [
  ["homepage title", /<title>AI面试助手｜[^<]+面试稳<\/title>/.test(contents.homepage)],
  ["homepage crawl directives", contents.homepage.includes('name="robots" content="index,follow,max-image-preview:large"') && contents.homepage.includes('name="author" content="OneShow AI Lab"')],
  ["homepage direct answer", contents.homepage.includes("面试稳是什么？") && contents.homepage.includes("面向求职者的 AI 面试助手")],
  ["homepage assistant variants", contents.homepage.includes("AI 面试助手与面试辅助工具")],
  ["realtime title", contents.realtime.includes("<title>实时面试辅助与 AI 面试实时回答｜面试稳</title>")],
  ["realtime H1", contents.realtime.includes("<h1>实时面试辅助：AI 面试实时回答建议</h1>")],
  ["realtime flow", contents.realtime.includes("实时语音识别") && contents.realtime.includes("问题理解") && contents.realtime.includes("自行判断和表达")],
  ["technical title", contents.technical.includes("<title>程序员面试助手：技术面试回答思路｜面试稳</title>")],
  ["technical H1", contents.technical.includes("<h1>程序员面试助手：把技术思路讲清楚</h1>")],
  ["technical cluster", ["/guides/technical-interview", "/interview-questions/llm", "/interview-questions/rag", "/interview-questions/ai-agent", "/interview-questions/java-backend", "/interview-questions/frontend", "/interview-questions/algorithms"].every(link => contents.technical.includes(link))],
  ["pricing title", contents.pricing.includes("<title>AI面试助手价格与套餐｜面试稳</title>")],
  ["pricing direct answer", contents.pricing.includes("面试稳如何收费？") && contents.pricing.includes("实时商品目录")],
  ["features neutral title", contents.features.includes("<title>面试稳产品功能：实时辅助、截图回答与复盘</title>")],
  ["no comparison claim", !Object.values(contents).some(content => content.includes("AI面试助手哪个好"))],
  ["no prohibited superiority claim", !Object.values(contents).some(content => /行业第一|全网第一|保证录用/.test(content))],
];
const failed = checks.filter(([, ok]) => !ok);
if (failed.length) {
  console.error(failed.map(([name]) => `FAIL ${name}`).join("\n"));
  process.exit(1);
}
console.log(`keyword targeting checks passed (${checks.length})`);
