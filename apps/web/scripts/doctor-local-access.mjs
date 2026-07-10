import { resolveLocalWebUrl } from "./local-web-access.mjs";

const diagnosis = await resolveLocalWebUrl();

if (diagnosis.selected) {
  process.stdout.write([
    `本地网页原型可访问：${diagnosis.selected}`,
    `来源：${diagnosis.selectedSource === "preview" ? "preview 服务（推荐用于巡检）" : diagnosis.selectedSource === "dev" ? "dev 服务" : "环境变量指定地址"}`,
    "",
    "检测详情：",
    ...diagnosis.results.map(result => `- ${result.url} · ${result.ok ? "可访问" : `不可访问（${result.reason ?? "unknown"}）`}`),
  ].join("\n") + "\n");
  process.exit(0);
}

process.stderr.write([
  "未检测到可访问的本地网页原型。",
  "",
  "检测详情：",
  ...diagnosis.results.map(result => `- ${result.url} · 不可访问（${result.reason ?? "unknown"}）`),
  "",
  "建议顺序：",
  "1. 运行 npm run dev:web 并访问 http://127.0.0.1:5173/",
  "2. 或运行 npm run preview:web 并访问 http://127.0.0.1:4173/",
  "3. 若要执行自动巡检，再运行 npm run review:live -w @offersteady/web",
].join("\n") + "\n");
process.exit(1);
