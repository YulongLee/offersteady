# 国服核心承接页 SEO/GEO 第一批优化

日期：2026-09-08。开发记录如下；随后已获批准并于01:29:07上线 **cn-core-seo-20260908.1**，详见[生产发布验证](../../releases/cn-core-seo-20260908.md)。本报告不代表收录/排名改善证明。

## 范围与结论

仅优化 `/`、`/pricing`、`/features/realtime-interview`、`/features/ai-interview-assistant` 四个现有承接页。没有新增 Landing Page，没有删除或改 URL，没有改 canonical 策略、robots、真实企业主体、登录、支付、面试、ASR、AI、RAG、Companion 或下载逻辑。代码在此前国服生产基线工作树：

`/private/tmp/offersteady-cn-release-20260907.DTlvCc`

不直接覆盖主工作区或线上目录，避免带入它们已有的其他版本改动。本轮按 SEO Operator、落地页文案与 OpenSpec 流程执行；事实化问答、意图区分和静态价格由此落实，没有添加虚构营销证明或受限 FAQPage markup。

## 修改前：生产 HTTP 原始 HTML

| URL | Primary Keyword | Title | H1 | Description | 主要正文变化 | 内链变化 | Schema |
|---|---|---|---|---|---|---|---|
| / | AI面试助手 | AI面试助手｜实时语音识别、截图解题与个性化回答 - 面试稳 | AI 面试助手，让你的经历更好表达。 | 面试稳是一款 AI 面试助手，可结合简历、目标岗位和知识资料，整理实时面试问题、截图题与技术题的回答思路。 | 产品价值和功能概述，缺少首屏明确的求职者产品定义 | 原有导航到功能、指南、价格等 | Organization + WebSite + SoftwareApplication |
| /pricing | AI面试助手价格 | 积分与会员计费说明｜面试稳 | 先免费体验，再按面试节奏选择 | 了解面试稳AI助手的免费使用、积分按次与按天会员逻辑，以及回答、截图、知识材料和支付到账的计费边界。 | 计费说明，不含公开金额，建议登录看价格 | 原有登录、手册、下载等 | WebPage + BreadcrumbList |
| /features/realtime-interview | 实时面试辅助 | 实时面试辅助：语音识别与回答建议｜面试稳 | 实时面试辅助，从听清问题开始 | 面试稳实时面试辅助说明：区分麦克风与电脑输出音频，持续整理对话，确认面试官问题，并结合本场资料生成回答建议。 | 收音和四步实时流程 | 收音排查、功能、复盘、隐私 | WebPage + BreadcrumbList |
| /features/ai-interview-assistant | 程序员面试助手 | AI面试助手：从资料准备到面试复盘｜面试稳 | AI 面试助手，不只回答一道题 | 了解面试稳 AI 面试助手如何结合简历、岗位 JD 和知识材料，覆盖面试准备、实时问题整理、截图回答与面试复盘。 | 通用面试前中后功能总览 | 实时、截图、复盘、准备与隐私 | WebPage + BreadcrumbList |

## 修改后：本地生产构建 + Nginx HTTP 原始 HTML

| URL | Primary Keyword | Title | H1 | Description | 主要正文变化 | 内链变化 | Schema |
|---|---|---|---|---|---|---|---|
| / | AI面试助手 | AI面试助手｜实时语音识别、截图解题与个性化回答 - 面试稳 | AI 面试助手，让你的经历更好表达。 | 面试稳是一款面向求职者的AI面试助手，结合简历、目标岗位和知识资料，帮助整理实时面试问题、截图题与技术题的回答思路。 | 首屏明确产品定义；补充“是什么/如何工作/适合岗位/如何收费”直接答案，Title/H1不变 | 问答增加实时辅助、技术岗位、公开价格页内链 | Organization + WebSite + SoftwareApplication |
| /pricing | AI面试助手价格 | AI面试助手价格与套餐｜面试稳 | 面试稳价格与套餐 | 查看面试稳AI面试助手价格：按天会员和积分包的人民币金额、有效期、主要权益，以及语音、回答、截图和知识材料的计费说明。 | 构建读取生产目录生成10项金额、有效期、权益、积分费率与限制；手机为卡片，购买仍走已有账户入口 | 增加页内套餐锚点、/app/billing；保留登录、手册和联系支持 | WebPage + BreadcrumbList |
| /features/realtime-interview | 实时面试辅助 | 实时面试辅助：语音识别与回答建议｜面试稳 | 实时面试辅助：从问题到回答建议 | 面试稳实时面试辅助说明：区分麦克风与电脑输出音频，持续整理对话，确认面试官问题，并结合本场资料生成回答建议。 | 明确实时回答建议；六步音频到用户表达流程及直接定义，不宣称延迟或准确率 | 增加准备清单，技术页锚文本改为技术岗位场景 | WebPage + BreadcrumbList |
| /features/ai-interview-assistant | 程序员面试助手 | 程序员面试助手：技术追问与回答思路｜面试稳 | 程序员面试助手，把技术思路讲清楚 | 面试稳程序员面试助手结合简历、JD 和知识资料，为 Java、前端、算法及 LLM 等技术岗位整理项目追问、技术原理、系统设计和截图题的回答思路。 | 改为技术岗位场景：项目追问、原理、系统设计、截图题、上下文和表达；不宣称专属模型或代码已验证 | 增加首页回链、技术指南及LLM/RAG/AI Agent/Java/前端/算法7项专题链接 | WebPage + BreadcrumbList |


## 关键词职责

- 首页唯一主承接通用词：AI面试助手、面试助手、AI面试辅助、面试AI、AI面试工具。不将这些词逐一堆入页面。
- 实时页主承接实时面试辅助，并自然覆盖 AI实时面试助手、AI面试实时回答。
- 技术页承接程序员面试助手、程序员AI面试、技术面试助手意图，以实际场景表述，不虚构岗位专属模式。
- 价格页承接 AI面试助手价格。
- 比较页继续暂缓；没有创建 /guides/ai-interview-assistant-comparison。

## 生产价格来源与边界

来源：既有公开接口 `https://mianshiwen.cn/api/v1/web/state` 的 `data.billing.catalog` 和 `rates`。未使用源码 fallback 价格。确实观察到生产积分包价格与源码默认值不同。

最终构建读取时间：2026-09-08 01:18:17 +08:00（HTML time：2026-09-07T17:18:17.628Z）。
目录费率版本：16；已发布商品10项。目录指纹：
`b4766ec3fab1a60df7ed290ee6900da3501a3f543741b6b695aebd52b7ea1287`

| 当前商品 | 生产价格 CNY | 有效期/权益 |
|---|---:|---|
| 1天会员 | ¥29.90 | 连续24小时；知识索引额度0次 |
| 3天会员 | ¥69.90 | 连续72小时；知识索引额度0次 |
| 7天会员 | ¥129.90 | 连续168小时；知识索引额度0次 |
| 15天会员 | ¥219.90 | 连续360小时；知识索引额度2次 |
| 30天会员 | ¥329.90 | 连续720小时；知识索引额度2次 |
| 1000积分 | ¥39.90 | 积分余额长期保留 |
| 3000积分 | ¥99.90 | 积分余额长期保留 |
| 10000积分 | ¥299.90 | 积分余额长期保留 |
| 30000积分 | ¥699.90 | 积分余额长期保留 |
| 66666积分 | ¥999.90 | 积分余额长期保留 |

这些数值是本次观测记录，不是代码硬编码价格。构建时重新读取生产数据，过滤下架商品，校验整数分、时长、额度、费率与版本，转义文本，只输出公开字段，不保存账户、余额、订单或资料数据。请求失败、空目录或无效价格会停止构建，不回退历史金额。

页面说明：普通回答5积分/次、截图15积分/次、实时面试5积分/分钟；有效会员实时面试、回答和截图不扣积分。**笔试入场30积分/次，会员也扣入场积分**。知识索引最低20积分，每5000 Token 20积分，先使用适用额度，超出额度需确认报价。上面这些数字也由生产 rates 渲染，非写死在页面。会员延长不覆盖剩余时间，积分不因会员到期清除，保留本人使用、并发和安全边界。

代码依据：`billing_service.py` 的 `reserve_usage`、`quote_knowledge_index`；`realtime_speech_service.py` 的 `start_live_session` 和 `_reserve_realtime_minute`。单独 wallet_only 的是笔试入场，不是实时语音。

### 必须知道的同步限制

这是**构建时静态价格快照，不是每次访问时 SSR 查询**。无新增访客 API 请求、后台定时任务或运行时服务。后续管理员改价/上下架，必须同步重新构建并发布 Web，公开页才会更新；checkout 仍按实时目录执行。

发布前执行 `node apps/web/scripts/verify-pricing-live.mjs`。它会核对当前生产目录指纹、完整渲染内容和24小时内的生成时间，不一致/过期即失败。此次未修改部署流程自动触发配置，因此该发布检查必须由实际发布操作者执行，不能把旧 dist 直接上传后假定价格仍最新。

## 初始 HTML 与机器可读性

证据为普通 UA 与模拟 Baiduspider 的直接 HTTP 获取，未依赖浏览器 React Router 跳转。before来自生产，after来自**本地 Nginx + 最终构建**，不混称线上已修复。

| URL | 普通/Baidu本地状态 | 初始正文 | Title/H1 | canonical | robots |
|---|---|---|---|---|---|
| / | 200 / 200 | 有，含产品定义与问答 | 唯一/1个 | https://mianshiwen.cn/ | 无noindex |
| /pricing | 200 / 200 | 有，含10个真实金额 | 唯一/1个 | https://mianshiwen.cn/pricing | 无noindex |
| /features/realtime-interview | 200 / 200 | 有，含六步流程 | 唯一/1个 | https://mianshiwen.cn/features/realtime-interview | 无noindex |
| /features/ai-interview-assistant | 200 / 200 | 有，含技术场景与专题链接 | 唯一/1个 | https://mianshiwen.cn/features/ai-interview-assistant | 无noindex |

- sitemap仍为30个原有URL，仅四页lastmod为2026-09-08，其余保持原日期。
- 30个本地 sitemap URL 均200、自引用canonical且可索引；完整表在 raw-html-evidence.json 的 sitemap 数组。
- 原始正文、内链、JSON-LD均存在；检查了对应CSP精确hash，未放宽script-src。
- Schema保留首页Organization/WebSite/SoftwareApplication，其余WebPage/BreadcrumbList；不加入FAQPage、评价、星级或尚无必要的Offer承诺。
- 没有虚构用户数量、获奖、延迟、准确率、市场排名或竞品数据。
- 当前检查不能保证百度立即收录、实际Baiduspider请求会取得相同网络路径、或关键词排名提升；缺少搜索平台后续数据。
- 本地首页浏览器检查是在API不可达时保留初始正文的状态；SPA首页文案与既有业务交互另由组件测试覆盖，没有在生产创建测试账户、支付或面试。

## 验证结果

| 命令/检查 | 结果 |
|---|---|
| npm run typecheck -w @offersteady/web | 通过 |
| VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=cn-core-seo-20260908.1 npm run build -w @offersteady/web | 通过；价格静态输出约11.65KB |
| npm run test -w @offersteady/web -- --maxWorkers=2 | 53文件、387项通过（包含7项新增SEO/价格测试） |
| npm run test:seo-p0 -w @offersteady/web | 30页源码检查通过 |
| node apps/web/scripts/verify-indexing-build.mjs | 30 sitemap + 2既有法律文档通过 |
| node apps/web/scripts/verify-pricing-live.mjs | 10商品与生产一致，内容及24小时新鲜度通过 |
| node apps/web/scripts/verify-core-seo-http.mjs <evidence-dir> | 四页双UA原始HTML、JSON-LD/CSP、公开内链、30路由通过 |
| Chrome 375px / 1440px | 四页均一H1、无横向页面溢出；价格手机卡片、桌面表格；截图已检查 |
| docker exec cn-core-seo-qa-20260908 nginx -t | 通过；仅本地测试容器 |
| openspec validate optimize-cn-core-search-landing-pages --strict | 通过 |
| git diff --check | 通过 |
| npm run test:seo-build -w @offersteady/web | **未通过：既有JS体积预算问题仍在** |
| lint | 现有Web没有独立lint命令，未声称通过 |

JS总量1,364,681 B（预算1,350,000），入口444,227 B（预算410,000）。前一生产基线总量1,363,159 B，已超标；本轮问答文案等增加1,522 B。未放宽阈值、未在四页文案任务中大规模重构业务bundle，**不能称所有检查全绿**。构建与业务测试通过不等于体积门禁通过，后续发布应知悉此遗留问题。

## 修改文件

以下相对路径均位于上述国服工作树；已有其他未提交改动保留，本清单不代表整个git diff均属于本轮：

- apps/web/index.html：首屏定义、description和静态问答。
- apps/web/src/App.tsx：匹配的首页首屏和问答内容，无业务handler改动。
- apps/web/public/seo/pricing.html：价格意图、生成标记、边界、手机样式。
- apps/web/public/seo/realtime-interview.html：回答建议与六步流程。
- apps/web/public/seo/ai-interview-assistant.html：技术场景与七项专题内链。
- apps/web/pricing-static.mjs、pricing-static.d.mts：公开价格校验、转义、渲染与发布核对。
- apps/web/vite.config.ts：构建时读取生产目录，输出既有pricing.html。
- apps/web/pricing-static.test.ts：7项回归测试（数据错误、网络失败、下架、转义、过期、篡改、意图与链接）。
- apps/web/src/App.product-experience.test.tsx：更新新增问答数量、按原问题定位既有折叠交互。
- apps/web/scripts/verify-pricing-live.mjs、verify-core-seo-http.mjs：发布前价格检查与原始HTTP证据。
- apps/web/scripts/verify-seo-p0.mjs：仅更新四页lastmod断言。
- apps/web/public/sitemap.xml：仅对应lastmod。
- infra/nginx/default.conf：仅替换三个修改JSON-LD的精确hash，无路由/重定向策略改动。
- openspec/changes/optimize-cn-core-search-landing-pages/：本轮proposal、design、spec、tasks。
- SEO-EXECUTION-LOG.md：执行记录。

## 证据与交付

- [完整原始HTML检查数据](raw-html-evidence.json)
- [浏览器检查数据](browser-evidence.json)
- [手机价格卡片](prices-375.png)
- [桌面价格表](prices-1440.png)
- [技术页桌面截图](viewport-1440-_features_ai-interview-assistant.png)
- 同目录包含四页生产before、本地after、普通/Baidu的HTML快照。
- 生产仅做低频公开GET读取，没有SSH登录、重启、上传、部署或配置写入。海外版本不在本轮范围。
