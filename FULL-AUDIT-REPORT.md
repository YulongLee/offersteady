# 面试稳 SEO 全站审计

审计日期：2026-08-19

审计对象：`https://mianshiwen.cn/`

业务类型：AI 面试助手 / SaaS
审计范围：公开页面、robots、站点地图、抓取与索引信号、元数据、结构化数据、内容与 E-E-A-T、内部链接、移动端实验室性能、AI 搜索可见性。

## 2026-08-19 SEO / GEO 增量优化（本地验收完成）

本轮在不改动登录、面试、实时收音、截图、资料、支付、数据库和电脑伴随程序行为的前提下，完成以下优化：

- 新增 6 个轻量、无 JavaScript 的公开专题页，覆盖 AI 面试助手、实时面试、截图回答、面试复盘、面试准备与收音排查。
- sitemap 从 2 个 URL 扩展为 8 个 URL，并为每项补充 `lastmod`；所有页面使用独立 title、description、H1、self-canonical、Open Graph、WebPage 与 BreadcrumbList 数据。
- 首页与使用手册建立可抓取的主题集群入口；专题页之间双向关联，并保留登录与使用手册的原有转化入口。
- 新增 `llms.txt`、`llms-full.txt` 和 `public-facts.json`，只发布可公开、可核对的产品事实与动态信息边界，不包含内部接口、提示词、密钥或个人数据。
- Nginx 仅增加明确公开路径、GEO 资源类型与缓存规则；登录和应用路径继续 `noindex, follow + no-store`，未知路径继续真实 404。
- 首页显示用品牌图标从 248 KiB 原图切换为约 12 KiB 的同源缩放图，传输体积减少约 95%；同时补充图片尺寸、异步解码和非首屏懒加载约束。
- 自动发布门禁现覆盖 8 个 sitemap 页面、GEO 文件、JSON-LD/CSP 哈希、内部链接、Nginx 映射、缓存分层、图片和构建体积预算。

本地生产构建的三轮 Lighthouse 中位数：

| 页面 | Performance | Accessibility | Best Practices | SEO | LCP | CLS | TBT |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 首页 | 97 | 100 | 96* | 100 | 2.108 秒 | 0 | 0 ms |
| 使用手册 | 98 | 100 | 96* | 100 | 2.105 秒 | 0 | 0 ms |
| 代表性专题页 | 100 | 100 | 100 | 100 | 0.902 秒 | 0 | 0 ms |

\* 本地预览没有启动后端，首页和手册请求 `/api/v1/web/state` 得到 404，因此 Best Practices 扣分；这是本地预览环境缺少 API 的已知限制，不是专题页或生产 Nginx 错误。线上字段数据、Search Console、百度、自然流量和转化仍未知，不应由 Lighthouse 推断。

## 结论

网站不是“完全没有做 SEO”：HTTPS、robots.txt、sitemap、首页 canonical、中文语言声明、Open Graph、JSON-LD 和安全响应头都已具备，Lighthouse 的 SEO 与可访问性实验室检查均为 100 分。

2026-08-19 部署后复测确认，`/guide` canonical 冲突、独立元数据、公开页缓存和首页内部链接均已修复。综合方向性评分由部署前的 **58/100** 提升到 **78/100（良好）**。当前已没有已确认的索引阻断问题；主要扣分转为可索引内容规模偏小、品牌/运营主体信号不完全一致、营销数据缺少公开口径，以及首页移动端 LCP 波动。

| 维度 | 评分 | 主要判断 |
| --- | ---: | --- |
| 技术 SEO | 92 | 两个 sitemap URL 均为 200、可索引且 canonical 自指；缓存与 noindex 分层正确 |
| 内容与 E-E-A-T | 55 | 内容覆盖面仍薄，运营主体与营销数据可信度仍待补强 |
| 页面 SEO | 92 | 首页与指南页均有独立 title、description、H1、canonical 和内部链接 |
| 结构化数据 | 85 | 首页和指南页 JSON-LD 有效，但主体信息仍需统一 |
| 性能与 CWV | 82 | 三次移动 Lighthouse 性能中位数 89；LCP 中位数 3.52 秒，TBT 与 CLS 优秀 |
| 图片 SEO | 70 | 社交分享图完整；运行时图片仍有尺寸、格式与传输优化空间 |
| AI 搜索准备度 | 40 | 没有 llms.txt，AI 爬虫策略未明确，实体信号仍弱 |

> 评分用于排优先级，不等同于 Google 排名。当前无法访问 Search Console、百度搜索资源平台与 CrUX 字段数据，因此真实索引量、搜索词、点击率、外链、INP 和真实用户 CWV 仍是未知项。

## 线上修复状态（2026-08-19）

以下高优先级问题已部署并通过线上复测：

- `/guide` 已拥有独立服务端 HTML、独立 title/description、self-canonical、H1、WebPage 与 BreadcrumbList JSON-LD。
- 首页搜索标题已补充实时语音、截图解题与个性化回答等核心意图，现有可见 H1、按钮和产品流程保持不变。
- 首页静态 HTML 已增加普通 `/guide` 链接，指南页也可回到首页、登录、隐私政策和用户协议。
- 公开首页与指南页改为 `public, max-age=0, must-revalidate`；登录、邀请、法律文件、错误页和应用内页面继续 `no-store`。
- Vite 生产构建已输出独立 `index.html` 与 `guide.html`，Nginx 路由和 CSP 哈希已同步。
- SEO 发布检查已覆盖 sitemap URL、入口文件映射、独立元数据、self-canonical、H1、内部链接、缓存分层和生产 CSP。
- 线上 Lighthouse：主页三次 Performance 为 86/89/100，SEO 均为 100，LCP 中位数 3.52 秒、TBT 0–18 毫秒、CLS 0；指南页 Performance、Accessibility、Best Practices、SEO 均为 100，LCP 1.08 秒。真实用户表现仍应以 CrUX p75 为准。

未自动修改的内容：真实运营主体 `legalName` 仍需确认工商登记全称；首页营销数字仍需业务提供统计口径；Search Console、百度和 CrUX 仍需平台权限。未经证据确认前不应自动编造这些信息。

## 关键证据

- 首页 HTTP 200，无跳转；Googlebot 与普通客户端获得相同 HTML 哈希，没有发现按 UA 返回不同内容。
- `robots.txt` 允许全站抓取，并声明 `https://mianshiwen.cn/sitemap.xml`。
- sitemap 有效，但只有首页和 `/guide` 两个 URL，均没有 `lastmod`。
- sitemap 检查确认首页和 `/guide` 均返回 200、允许索引且 canonical 自指。
- 原始首页 HTML 具备唯一 H1、4 个 H2、首页 canonical、description、zh-CN、viewport、Open Graph 和 3 组 JSON-LD。
- 深度 1 抓取发现 5 个公开/辅助页面、21 条内部链接；首页与 `/guide` 已互相提供可抓取链接，没有孤立候选页。
- 原始 HTML 内容约 334 个解析词元；中文分词工具存在偏差，但页面可索引主题覆盖仍明显偏薄。
- Lighthouse 移动端线上复测：主页 Performance 中位数 89、SEO 100、LCP 中位数 3.52 秒、TBT 0–18 毫秒、CLS 0；指南页 Performance 与 SEO 均为 100。
- PageSpeed Insights API 在本次审计中持续触发限流，未取得 CrUX 字段数据；这属于审计环境限制，不代表网站故障。
- 首页、指南页返回 `Cache-Control: public, max-age=0, must-revalidate`；登录页返回 `no-store` 和 `X-Robots-Tag: noindex, follow`。
- `llms.txt`、`llms-full.txt` 返回 404。

## 按优先级排列的发现

### 1. `/guide` 的 sitemap 与 canonical 相互冲突（已解决）

- 严重性：Pass
- 置信度：高
- 证据：线上 `/guide` 返回 200，canonical 为 `https://mianshiwen.cn/guide`，并具有独立 title、description、H1、WebPage 和 BreadcrumbList JSON-LD。
- 当前状态：已部署并通过线上复测。

### 2. 可索引内容与站内主题架构过薄

- 严重性：Warning
- 置信度：高
- 证据：sitemap 仅 2 个 URL；爬虫发现 3 个唯一公开页面；首页服务端 HTML 只提供少量正文和有限内部链接。
- 影响：难以覆盖“AI 面试助手、实时面试、截图解题、模拟面试、技术面试、面试复盘、简历面试准备”等不同搜索意图，也难以积累主题权威。
- 修复：先建立 6–10 个高价值、可长期维护的公开页面，而不是批量生成低质量文章。建议从功能页、使用场景页、真实教程页和问题解决页开始，并让首页、指南页和专题页互相链接。

### 3. 首页标题过于泛化（已解决）

- 严重性：Pass
- 置信度：高
- 证据：线上 title 已更新为“AI面试助手｜实时语音识别、截图解题与个性化回答 - 面试稳”，description、Open Graph 和 Twitter Card 同步表达核心能力。
- 当前状态：已部署并通过线上复测。

### 4. 品牌、运营主体与结构化数据不完全一致

- 严重性：Warning
- 置信度：高
- 证据：Organization schema 和页脚使用 `OneShow AI Lab`，网站名称为“面试稳AI助手”，备案与实际运营主体需要以真实公司资料为准。
- 影响：对涉及手机号、简历、录音转写、截图和付费的产品，会削弱 E-E-A-T、用户信任和实体识别。
- 修复：在页脚、关于我们、隐私政策、用户协议、联系信息和 Organization JSON-LD 中统一真实运营主体；可保留品牌名，但增加 `legalName`、真实联系邮箱、备案信息和清晰的产品归属关系。

### 5. “10W+、98%、1W+、100+”缺少公开口径

- 严重性：Warning
- 置信度：高
- 证据：首页代码固定展示累计面试、效率提升、题库与岗位数据，但页面没有统计口径、时间范围或第三方/内部研究说明。
- 影响：这不仅是转化可信度问题，也会影响品牌搜索声誉和 E-E-A-T。尤其“效率提升 98%”属于需要解释方法的效果主张。
- 修复：如数据真实，增加统计截止日期、样本量和计算口径；如无法验证，改为可审计的真实数据或定性表达。不要制造评价、客户公司或 aggregateRating。

### 6. 首页移动端 LCP 存在波动

- 严重性：Warning
- 置信度：中高
- 证据：线上 Lighthouse 三次主页 LCP 为 3.85/3.52/1.08 秒，中位数 3.52 秒；TBT 0–18 毫秒、CLS 0。审计还提示约 19 KiB 未使用 CSS、65 KiB 未使用 JavaScript、317 KiB 图片传输优化空间，以及部分图片缺少明确尺寸。
- 影响：接近 4 秒的“差”区间，首屏感知偏慢，可能影响跳出与转化。
- 修复：确认 LCP 元素；优先精简首屏 CSS/字体、预加载真正的首屏关键资源、延迟非首屏模块和第三方资源。上线后以 Search Console/CrUX 的 p75 LCP、INP、CLS 为准。

### 7. 公开页缓存与敏感页缓存分层（已解决）

- 严重性：Pass
- 置信度：高
- 证据：首页与 `/guide` 返回 `public, max-age=0, must-revalidate`；登录页继续返回 `no-store` 和 `noindex, follow`。
- 当前状态：已部署并通过线上复测。

### 8. 服务端 HTML 缺少可索引的产品截图和图像语义

- 严重性：Warning
- 置信度：中
- 证据：原始首页未发现 `<img>` 或 `<svg>`，主要依赖运行时界面；仅存在社交分享图片元数据。
- 影响：失去图片搜索、功能说明和首屏视觉语义机会。
- 修复：增加真实产品截图，使用 `<picture>`、WebP/AVIF、明确尺寸和描述性 alt；不要把关键营销文字只做进图片。

### 9. 搜索可见度目前无法形成数据闭环

- 严重性：Warning
- 置信度：中
- 证据：公开搜索抽样没有稳定观察到 `mianshiwen.cn` 的品牌结果；但本次没有 Search Console 或百度后台权限，不能据此断言未收录。
- 影响：无法知道页面是否被发现、哪些查询产生展示、CTR 是否偏低、是否有手动措施或索引异常。
- 修复：验证 Google Search Console 与百度搜索资源平台，提交 sitemap，检查 URL Inspection/抓取诊断，并建立每周展示、点击、CTR、平均排名、索引页数、CWV 的基线。

### 10. AI 搜索发现文件与策略未建立

- 严重性：Info
- 置信度：高
- 证据：`llms.txt` 与 `llms-full.txt` 均为 404；robots 没有显式区分常见 AI 爬虫。
- 影响：不是 Google 排名必需项，但会降低对 AI 抓取范围、官方事实与引用入口的可控性。
- 修复：先统一品牌实体和高质量公开内容，再提供简洁 `llms.txt`，列出官方介绍、指南、隐私、联系方式和允许引用的核心页面；AI 爬虫是否允许应由业务明确决定。

## 已通过项

- 首页、robots.txt、sitemap.xml 均可访问。
- HTTPS、HSTS、CSP、X-Frame-Options、nosniff、Referrer-Policy 已配置。
- 首页 canonical 自指、lang=zh-CN、charset、viewport 均正确。
- 首页只有一个 H1，标题层级基础正常。
- Open Graph 完整；Twitter 基础卡片完整，仅缺可选的账号字段。
- 首页存在 Organization、WebSite、SoftwareApplication 结构化数据。
- 登录、协议、隐私及应用内页面通过 `X-Robots-Tag: noindex, follow` 避免进入搜索结果，方向正确。
- Lighthouse Accessibility、Best Practices、SEO 均为 100；CLS 为 0、TBT 为 10 毫秒。

## 限制与未验证项

- 未接入 Google Search Console、百度搜索资源平台、GA4 或日志，因此不能验证真实索引、抓取频率、自然流量、转化、查询词和外链。
- PageSpeed API 因限流没有返回字段数据；Lighthouse 是单次实验室结果，不代替真实用户 p75 指标。
- 工信部备案外链在自动检查中返回 521，可能是对自动化请求的限制；应以真实浏览器手动点击结果为准，不能据此认定备案链接失效。
- 中文可读性工具不适配中文分词，未采用其英文可读性评分。

## 建议的商业化 SEO 基线

每周跟踪：品牌词/非品牌词展示与点击、首页和专题页 CTR、有效索引页数、抓取错误、p75 LCP/INP/CLS、自然流量注册率。每月复核：高价值页面覆盖、内容更新、引用与自然外链、品牌主体一致性、付费/隐私信息准确性。
