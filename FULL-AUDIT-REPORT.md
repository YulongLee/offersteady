# 面试稳 SEO 全站审计

审计日期：2026-08-19

审计对象：`https://mianshiwen.cn/`

业务类型：AI 面试助手 / SaaS
审计范围：公开页面、robots、站点地图、抓取与索引信号、元数据、结构化数据、内容与 E-E-A-T、内部链接、移动端实验室性能、AI 搜索可见性。

## 结论

网站不是“完全没有做 SEO”：HTTPS、robots.txt、sitemap、首页 canonical、中文语言声明、Open Graph、JSON-LD 和安全响应头都已具备，Lighthouse 的 SEO 与可访问性实验室检查均为 100 分。

但当前更像一个完成基础标签的产品首页，而不是已经建立自然搜索获客能力的网站。综合方向性评分为 **58/100（需要改进）**。首要问题是 `/guide` 被放入 sitemap，却在服务端 HTML 中 canonical 到首页；其次是可索引内容和内部链接规模过小，品牌/运营主体信号不完全一致，首页的强营销数据缺少公开证据。

| 维度 | 评分 | 主要判断 |
| --- | ---: | --- |
| 技术 SEO | 58 | 基础完整，但指南页 canonical 冲突会直接影响收录 |
| 内容与 E-E-A-T | 45 | 内容覆盖面薄，运营主体与营销数据可信度不足 |
| 页面 SEO | 62 | 首页标签齐全，标题偏泛化，指南页缺独立元数据 |
| 结构化数据 | 65 | 已有 Organization、WebSite、SoftwareApplication，但主体信息需统一 |
| 性能与 CWV | 76 | TBT、CLS 优秀；移动端实验室 LCP 3.9 秒需优化 |
| 图片 SEO | 55 | 社交分享图存在，但服务端首页没有可索引产品截图 |
| AI 搜索准备度 | 40 | 没有 llms.txt，AI 爬虫策略未明确，实体信号仍弱 |

> 评分用于排优先级，不等同于 Google 排名。当前无法访问 Search Console、百度搜索资源平台与 CrUX 字段数据，因此真实索引量、搜索词、点击率、外链、INP 和真实用户 CWV 仍是未知项。

## 本地修复状态（2026-08-19）

以下高优先级问题已在本地生产构建中修复，尚需部署后复测线上响应：

- `/guide` 已拥有独立服务端 HTML、独立 title/description、self-canonical、H1、WebPage 与 BreadcrumbList JSON-LD。
- 首页搜索标题已补充实时语音、截图解题与个性化回答等核心意图，现有可见 H1、按钮和产品流程保持不变。
- 首页静态 HTML 已增加普通 `/guide` 链接，指南页也可回到首页、登录、隐私政策和用户协议。
- 公开首页与指南页改为 `public, max-age=0, must-revalidate`；登录、邀请、法律文件、错误页和应用内页面继续 `no-store`。
- Vite 生产构建已输出独立 `index.html` 与 `guide.html`，Nginx 路由和 CSP 哈希已同步。
- SEO 发布检查已覆盖 sitemap URL、入口文件映射、独立元数据、self-canonical、H1、内部链接、缓存分层和生产 CSP。
- 修复后的本地生产构建 Lighthouse：主页 Performance 97、SEO 100、LCP 2.1 秒、TBT 0、CLS 0；指南页 Performance 98、SEO 100、LCP 2.1 秒、TBT 0、CLS 0。该结果用于确认没有实验室性能回退，线上仍应以 CrUX p75 为准。

未自动修改的内容：真实运营主体 `legalName` 仍需确认工商登记全称；首页营销数字仍需业务提供统计口径；Search Console、百度和 CrUX 仍需平台权限。未经证据确认前不应自动编造这些信息。

## 关键证据

- 首页 HTTP 200，无跳转；Googlebot 与普通客户端获得相同 HTML 哈希，没有发现按 UA 返回不同内容。
- `robots.txt` 允许全站抓取，并声明 `https://mianshiwen.cn/sitemap.xml`。
- sitemap 有效，但只有首页和 `/guide` 两个 URL，均没有 `lastmod`。
- sitemap 检查确认 `/guide` 返回 200、允许索引，但 canonical 为 `https://mianshiwen.cn/`。
- 原始首页 HTML 具备唯一 H1、4 个 H2、首页 canonical、description、zh-CN、viewport、Open Graph 和 3 组 JSON-LD。
- 抓取到的公开信息架构仅 3 个唯一页面、12 条内部链接；原始首页没有发现指向 `/guide` 的可抓取链接。
- 原始 HTML 内容约 334 个解析词元；中文分词工具存在偏差，但页面可索引主题覆盖仍明显偏薄。
- Lighthouse 移动端实验室结果：Performance 86、Accessibility 100、Best Practices 100、SEO 100；FCP 2.2 秒、LCP 3.9 秒、TBT 10 毫秒、CLS 0。
- PageSpeed Insights API 在本次审计中持续触发限流，未取得 CrUX 字段数据；这属于审计环境限制，不代表网站故障。
- 首页、指南页 HTML 均返回 `Cache-Control: no-store`。
- `llms.txt`、`llms-full.txt` 返回 404。

## 按优先级排列的发现

### 1. `/guide` 的 sitemap 与 canonical 相互冲突

- 严重性：Critical
- 置信度：高
- 证据：`/guide` 位于 sitemap、返回 200 且没有 noindex，但原始 HTML canonical 指向首页；首页与指南页的服务端 title、description、JSON-LD 也完全相同。
- 影响：搜索引擎可能把指南页当成首页副本，不收录指南页，浪费目前仅有的第二个公开落地页。
- 修复：为 `/guide` 输出独立的服务端 HTML 或预渲染结果，设置独立 title、description、self-canonical、H1 和可选 BreadcrumbList；在修复前可暂时将其从 sitemap 移除或 noindex，避免矛盾信号。
- 当前状态：已在本地生产构建修复，等待部署后线上复测。

### 2. 可索引内容与站内主题架构过薄

- 严重性：Warning
- 置信度：高
- 证据：sitemap 仅 2 个 URL；爬虫发现 3 个唯一公开页面；首页服务端 HTML 只提供少量正文和有限内部链接。
- 影响：难以覆盖“AI 面试助手、实时面试、截图解题、模拟面试、技术面试、面试复盘、简历面试准备”等不同搜索意图，也难以积累主题权威。
- 修复：先建立 6–10 个高价值、可长期维护的公开页面，而不是批量生成低质量文章。建议从功能页、使用场景页、真实教程页和问题解决页开始，并让首页、指南页和专题页互相链接。

### 3. 首页标题过于泛化

- 严重性：Warning
- 置信度：高
- 证据：当前 title 仅为“面试稳AI助手”，没有说明实时语音、截图题、个性化资料等核心差异。
- 影响：搜索结果相关性表达和点击吸引力不足。
- 修复：使用自然、可读且不堆词的标题，例如“AI面试助手｜实时语音识别、截图解题与个性化回答 - 面试稳”。description 可继续精炼核心人群、价值和行动点。
- 当前状态：已在本地生产构建修复，等待部署后线上复测。

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

### 6. 移动端 LCP 为 3.9 秒

- 严重性：Warning
- 置信度：中高
- 证据：本地 Lighthouse 移动端实验室 LCP 3.9 秒；TBT 10 毫秒、CLS 0，说明主要不是主线程长阻塞或布局跳动。
- 影响：接近 4 秒的“差”区间，首屏感知偏慢，可能影响跳出与转化。
- 修复：确认 LCP 元素；优先精简首屏 CSS/字体、预加载真正的首屏关键资源、延迟非首屏模块和第三方资源。上线后以 Search Console/CrUX 的 p75 LCP、INP、CLS 为准。

### 7. HTML 使用 `no-store`，重复访问无法有效复用

- 严重性：Warning
- 置信度：高
- 证据：首页与 `/guide` 均返回 `Cache-Control: no-store`。
- 影响：增加重复访问与边缘节点回源成本，也会放大首屏延迟；它不是直接排名惩罚，但会影响体验与抓取效率。
- 修复：对公开 HTML 使用短缓存或 `max-age=0, must-revalidate`/合理 CDN 策略；带内容哈希的 JS/CSS 使用长缓存 immutable。登录态/API 仍应按安全要求禁用敏感缓存。
- 当前状态：公开页已在本地改为强制重新验证缓存；敏感页面继续 `no-store`，等待部署后线上复测。

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
