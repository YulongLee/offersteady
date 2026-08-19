# SEO / GEO 监控清单

## 每次发布

- 运行 `npm run test:seo-p0 -w @offersteady/web`。
- 使用明确生产变量构建 Web，然后运行 `npm run test:seo-build -w @offersteady/web`。
- 请求 sitemap 中全部 17 个 URL，检查 200、self-canonical、title、description、唯一 H1 与结构化数据。
- 检查 `/login` 和 `/app` 仍为 `noindex, follow` 与 `no-store`，未知路径仍为 404。
- 检查 `llms.txt`、`llms-full.txt` 和 `public-facts.json` 不包含动态旧价格、密钥、内部接口或个人数据。

## 每周（接入平台后）

- Google / 百度：有效索引页数、抓取错误、品牌词与非品牌词展示、点击、CTR 和平均排名。
- 重点页：主页、`/guide`、5 个商业决策页、4 个能力页与 6 个维护指南的查询和落地页表现。
- 商业转化：分别跟踪 `/pricing`、`/download`、`/security` 与 `/contact` 到登录、下载和支持动作的转化，不把访问量当作成交。
- 真实体验：移动端 p75 LCP、INP、CLS；目标分别为 ≤2.5 秒、≤200 ms、≤0.1。
- 业务：自然流量登录率、注册率和付费转化；不得将实验室指标当成转化数据。

## 每月

- 检查产品能力、桌面版本、隐私规则、联系信息与 GEO 资料是否一致。
- 复核 Article 的审核团队、发布日期、更新日期和来源说明；发生实质修改时同步 sitemap `lastmod`。
- 复核内容是否仍对应真实产品，不批量生成近义页面。
- 使用真实搜索数据决定下一批主题，不凭空填写搜索量或排名。
- 更新执行记录、页面修改日期和 sitemap `lastmod`。
