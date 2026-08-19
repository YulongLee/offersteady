# 面试稳 SEO 优化行动计划

审计日期：2026-08-19

## P0：本周处理

1. [x] 修复 `/guide` 的独立 title、description、self-canonical 和服务端可抓取正文；增加首页到指南页的普通链接。
2. [x] 给 SEO 回归测试增加“sitemap 中每个 URL 必须成功、可索引且 canonical 自指”的断言，防止再次发布冲突。
3. [x] 将首页标题改为包含核心价值的自然标题；检查分享标题与搜索标题保持品牌一致。
4. [x] 部署后复测：Lighthouse SEO 100；首页和 `/guide` 均为 200、canonical 自指，公开页缓存与敏感页 noindex/no-store 分层正确。
5. [ ] 统一品牌与真实运营主体：等待提供工商登记全称后，再同步页脚、协议、隐私、Organization JSON-LD、联系邮箱和备案信息。
6. [ ] 核验首页 10W+、98%、1W+、100+ 的统计口径；等待业务提供统计日期、样本和计算方式。

## P1：未来 2–4 周

1. [x] 建立首批 6 个公开高价值页面：AI 面试助手、实时面试辅助、截图回答、面试复盘、面试准备与常见收音排查。
2. [x] 每页使用独立搜索意图、title、description、H1、步骤/事实内容和相关页面链接；避免换词复制和批量低质量 AI 内容。
3. 接入 Search Console 与百度搜索资源平台，提交 sitemap，建立索引/点击/CTR/排名/CWV 周报。
4. [x] 完成首轮图片与布局性能优化：首页品牌图显示资源由约 248 KiB 降至约 12 KiB，补齐图片尺寸并保留非首屏懒加载；本地首页三次 Lighthouse Performance 中位数 97、LCP 2.108 秒。上线后仍需用真实用户 p75 验证。
5. [x] 公开 HTML 使用强制重新验证缓存；登录和应用页面继续 no-store。后续继续核对哈希静态资源的长期 immutable 缓存。
6. 增加真实产品截图及描述性 alt，并提供 WebP/AVIF 与固定尺寸。
7. [x] 新增 `/pricing`、`/download`、`/security`、`/about`、`/contact` 五个无需登录即可抓取的商业决策页；动态价格、支付渠道和下载版本继续以产品内权威状态为准。
8. [x] 新增 macOS 权限、飞书收音、腾讯会议收音与 STAR 回答指南，并将现有两个指南升级为可核验的团队审核、日期、来源与 Article 数据。
9. [x] 将站点地图扩展至 17 个公开 URL，并扩展 robots、GEO 文件、Nginx 明确路由与发布校验。

## P2：未来 1–3 个月

1. 形成“产品页 → 场景页 → 操作指南 → 故障排查”的主题集群与双向内部链接。
2. 发布可验证的真实案例、产品更新记录和方法论内容；明确样本和统计口径，不编造用户、公司与评价。
3. 完善 SoftwareApplication schema 的真实功能、版本和官方价格信息；仅在满足规则时添加 FAQ/Review 等 schema。
4. [x] 增加 `llms.txt`、`llms-full.txt` 和公开事实 JSON，明确官方引用入口、动态信息与产品边界。
5. 持续获取真实行业引用、合作伙伴链接和用户自发提及，避免购买链接或群发外链。

## 验收标准

- sitemap 中全部 URL：HTTP 200、允许索引、canonical 自指、具有独立 title/description。
- 首页和首批专题页均可在禁用 JavaScript 时读取核心正文和导航链接。
- Google/Baidu 搜索平台均验证成功，sitemap 无错误，关键 URL 可被检查工具发现。
- 移动端真实用户 p75：LCP ≤ 2.5 秒、INP ≤ 200 毫秒、CLS ≤ 0.1。
- 所有量化营销主张均有统计日期、口径和内部证据。
- 真实运营主体在页脚、协议、隐私、备案与结构化数据中一致。

## 发布防错建议

在现有 SEO 校验脚本中增加生产构建后的路由级检查：读取 sitemap，逐个请求页面，校验状态码、X-Robots-Tag、canonical、title、description、H1、JSON-LD 和内部链接；任何可索引 URL canonical 指向其他页面时阻止发布。
