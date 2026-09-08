# 生产逐页检查 — 2026-09-08

30 个 sitemap 页面 + 2 个现有法律页面；普通爬虫和 Baiduspider 均直接 HTTP GET，不执行 JavaScript。

“允许”仅表示技术上未禁止索引，不等于百度已经收录。正文字符数不包含 head/script/style/nav/footer，不是质量得分。

|URL|普通/Baidu HTTP|Canonical|meta robots / X-Robots-Tag|robots.txt|H1/描述/正文|正文字符|首页深度|两种 UA HTML|
|---|---|---|---|---|---|---:|---:|---|
|https://mianshiwen.cn/|200 / 200|https://mianshiwen.cn/|无 / 无|允许|有 / 有 / 有|825|0|一致|
|https://mianshiwen.cn/guide|200 / 200|https://mianshiwen.cn/guide|无 / 无|允许|有 / 有 / 有|725|1|一致|
|https://mianshiwen.cn/features|200 / 200|https://mianshiwen.cn/features|无 / 无|允许|有 / 有 / 有|833|1|一致|
|https://mianshiwen.cn/interview-questions|200 / 200|https://mianshiwen.cn/interview-questions|无 / 无|允许|有 / 有 / 有|1002|1|一致|
|https://mianshiwen.cn/guides|200 / 200|https://mianshiwen.cn/guides|无 / 无|允许|有 / 有 / 有|858|1|一致|
|https://mianshiwen.cn/pricing|200 / 200|https://mianshiwen.cn/pricing|无 / 无|允许|有 / 有 / 有|648|1|一致|
|https://mianshiwen.cn/download|200 / 200|https://mianshiwen.cn/download|无 / 无|允许|有 / 有 / 有|720|1|一致|
|https://mianshiwen.cn/security|200 / 200|https://mianshiwen.cn/security|无 / 无|允许|有 / 有 / 有|586|1|一致|
|https://mianshiwen.cn/about|200 / 200|https://mianshiwen.cn/about|无 / 无|允许|有 / 有 / 有|617|1|一致|
|https://mianshiwen.cn/contact|200 / 200|https://mianshiwen.cn/contact|无 / 无|允许|有 / 有 / 有|562|1|一致|
|https://mianshiwen.cn/features/ai-interview-assistant|200 / 200|https://mianshiwen.cn/features/ai-interview-assistant|无 / 无|允许|有 / 有 / 有|727|2|一致|
|https://mianshiwen.cn/features/realtime-interview|200 / 200|https://mianshiwen.cn/features/realtime-interview|无 / 无|允许|有 / 有 / 有|642|2|一致|
|https://mianshiwen.cn/features/screenshot-answer|200 / 200|https://mianshiwen.cn/features/screenshot-answer|无 / 无|允许|有 / 有 / 有|595|2|一致|
|https://mianshiwen.cn/features/interview-review|200 / 200|https://mianshiwen.cn/features/interview-review|无 / 无|允许|有 / 有 / 有|615|2|一致|
|https://mianshiwen.cn/guides/audio-troubleshooting|200 / 200|https://mianshiwen.cn/guides/audio-troubleshooting|无 / 无|允许|有 / 有 / 有|966|2|一致|
|https://mianshiwen.cn/guides/interview-preparation|200 / 200|https://mianshiwen.cn/guides/interview-preparation|无 / 无|允许|有 / 有 / 有|934|2|一致|
|https://mianshiwen.cn/guides/macos-permissions|200 / 200|https://mianshiwen.cn/guides/macos-permissions|无 / 无|允许|有 / 有 / 有|763|2|一致|
|https://mianshiwen.cn/guides/feishu-audio-setup|200 / 200|https://mianshiwen.cn/guides/feishu-audio-setup|无 / 无|允许|有 / 有 / 有|764|2|一致|
|https://mianshiwen.cn/guides/tencent-meeting-audio-setup|200 / 200|https://mianshiwen.cn/guides/tencent-meeting-audio-setup|无 / 无|允许|有 / 有 / 有|751|2|一致|
|https://mianshiwen.cn/guides/star-interview-answer|200 / 200|https://mianshiwen.cn/guides/star-interview-answer|无 / 无|允许|有 / 有 / 有|798|2|一致|
|https://mianshiwen.cn/guides/self-introduction|200 / 200|https://mianshiwen.cn/guides/self-introduction|无 / 无|允许|有 / 有 / 有|2024|2|一致|
|https://mianshiwen.cn/guides/project-experience|200 / 200|https://mianshiwen.cn/guides/project-experience|无 / 无|允许|有 / 有 / 有|2098|2|一致|
|https://mianshiwen.cn/guides/technical-interview|200 / 200|https://mianshiwen.cn/guides/technical-interview|无 / 无|允许|有 / 有 / 有|2051|2|一致|
|https://mianshiwen.cn/guides/common-interview-questions|200 / 200|https://mianshiwen.cn/guides/common-interview-questions|无 / 无|允许|有 / 有 / 有|2160|2|一致|
|https://mianshiwen.cn/interview-questions/llm|200 / 200|https://mianshiwen.cn/interview-questions/llm|无 / 无|允许|有 / 有 / 有|2185|2|一致|
|https://mianshiwen.cn/interview-questions/rag|200 / 200|https://mianshiwen.cn/interview-questions/rag|无 / 无|允许|有 / 有 / 有|2292|2|一致|
|https://mianshiwen.cn/interview-questions/ai-agent|200 / 200|https://mianshiwen.cn/interview-questions/ai-agent|无 / 无|允许|有 / 有 / 有|2540|2|一致|
|https://mianshiwen.cn/interview-questions/java-backend|200 / 200|https://mianshiwen.cn/interview-questions/java-backend|无 / 无|允许|有 / 有 / 有|2203|2|一致|
|https://mianshiwen.cn/interview-questions/frontend|200 / 200|https://mianshiwen.cn/interview-questions/frontend|无 / 无|允许|有 / 有 / 有|2437|2|一致|
|https://mianshiwen.cn/interview-questions/algorithms|200 / 200|https://mianshiwen.cn/interview-questions/algorithms|无 / 无|允许|有 / 有 / 有|2144|2|一致|
|https://mianshiwen.cn/terms|200 / 200|https://mianshiwen.cn/terms|无 / 无|允许|有 / 有 / 有|914|1|一致|
|https://mianshiwen.cn/privacy|200 / 200|https://mianshiwen.cn/privacy|无 / 无|允许|有 / 有 / 有|1420|1|一致|

## 私有与异常路由

- /login：200，X-Robots-Tag `noindex, follow`；不在 sitemap。仍用 SPA shell，这是非索引登录入口，不将其计入公开 SEO 页面。
- 合成不存在路径：404，非首页正文；没有软 404。

## Robots 最终原文

```text
User-agent: *
Allow: /

User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

Sitemap: https://mianshiwen.cn/sitemap.xml
```

## 跳转检查

- http://mianshiwen.cn/ → https://mianshiwen.cn/；1 次跳转；最终 HTTP 200。
- http://mianshiwen.cn/pricing → https://mianshiwen.cn/pricing；1 次跳转；最终 HTTP 200。
- http://www.mianshiwen.cn/ → https://mianshiwen.cn/；2 次跳转；最终 HTTP 200。
- http://www.mianshiwen.cn/pricing → https://mianshiwen.cn/pricing；2 次跳转；最终 HTTP 200。
- https://www.mianshiwen.cn/ → https://mianshiwen.cn/；1 次跳转；最终 HTTP 200。
- https://www.mianshiwen.cn/pricing → https://mianshiwen.cn/pricing；1 次跳转；最终 HTTP 200。
