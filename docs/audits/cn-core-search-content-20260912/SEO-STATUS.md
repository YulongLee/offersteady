# 国服核心内容优化：本地验收

检查完成：2026-09-13（本轮内容核对日期为 2026-09-12）。

版本：`cn-search-content-20260912.local`。**第一批本地优化完成，未部署，不代表排名已经提升或超过竞品。**

## 本轮结果

保留此前新版首页，在四个现有承接页深化真实内容并改善阅读体验。没有新建 Landing Page，没有堆砌关键词，没有添加虚构用户评价、效果数字或竞品结论。

- 实时辅助：补充资料选择、识别纠错与回答思路示例；明确确认问题并点击快答后生成建议。
- 程序员场景：补充岗位差异、项目追问、代码与系统设计核实方法，保留技术指南和六个技术专题链接。
- 价格：明确公开看价、登录购买，解释积分、有效期及知识材料边界；不把“一场面试”等同于积分一定便宜。金额继续由真实生产目录构建生成。
- 下载：原“官方下载”按钮实际通向登录页；现在明确返回首页既有 Windows/macOS 下载入口。解释下载、安装、运行和连接是不同状态。
- 四页：统一深绿配色、标题层级、段落间距、目录、键盘正文跳转；侧栏不再拉伸到整篇高度，手机价格表转为卡片。
- GEO：三份公开说明统一公开看价和登录购买事实，明确技术场景定位；保留公司主体边界，不添加评分、获奖或额外 Schema 承诺。

具体页面前后对照见 [PAGE-CHANGES.md](/Users/liyulong/liyulong/1_projects/offersteady/docs/audits/cn-core-search-content-20260912/PAGE-CHANGES.md)。

## 已执行验证

| 检查 | 结果 |
| --- | --- |
| Typecheck | 通过 |
| 生产构建 | 通过；首次缺少生产构建变量被原有保护拒绝，补齐公共构建变量后重新通过 |
| 生产价格核验 | 10 个商品一致，快照小于 24 小时；未创建订单 |
| 新增内容回归 | 27/27 通过；旧快照 19 失败、8 通过，能复现旧问题 |
| 新增内容 + 原价格测试 | 34/34 通过 |
| 全量前端测试 | 414 项，404 通过、10 失败；失败名称与前一轮完全一致，无新增失败 |
| SEO 源文件检查 | 30 页通过 |
| 初始 HTML 构建检查 | 30 个 sitemap 页面及 2 个既有法律页面通过 |
| 本地 Nginx 配置校验 | 通过；只替换四项 JSON-LD 精确哈希，未放宽 CSP |
| 普通 UA / Baiduspider | 本地首页 + 四页共 10 次检查通过，原始 HTML 完全一致 |
| sitemap | 仍为 30 URL，全部本地 200，Title 唯一、H1 唯一、canonical 自指、无 noindex |
| 主要链接和资源 | 58 个站内链接返回 200；10 个直接引用的本地资产正常；不存在的专题返回真实 404 |
| 只读业务入口 | 登录、套餐账户、创建面试、设备入口 HTML 为 200；未执行登录、短信、订单、收音或真实下载 |
| 桌面/手机 | 四页均检查 1440×1000、390×844，无横向溢出；正文键盘跳转成功 |
| 原有 JS 体积门禁 | **未通过**，未提高预算 |
| 独立 lint | 当前 web package 没有独立 lint 命令，未声称执行 |
| 补丁重放 | 12 个源码/配置文件 + 2 个仅预览文件在独立临时目录重放后逐字节一致 |

这里的 200、双 UA 和入口验证均指本地生产构建，不是线上发布验证。临时 Nginx 未连接任何业务后端。公开价格核验是唯一生产目录请求，不含个人资料。

## 已知问题和未完成事项

**High — 既有业务 JS 预算超标。** 总 JS 1,373,364 字节，预算 1,350,000；主入口约 452.83 KB，预算 410 KB。四个静态内容页不执行新增 JS，本轮不重构业务包。这个结果不能用于证明线上首屏速度已经达标，也不是并发或 API 压测。

**Medium — 原有 10 项测试仍失败。** 涉及旧首页文案/模块断言、合作伙伴导航和一项资料删除失败提示；未修改测试来掩盖它们。完整名称保存在验收目录的 `test-comparison.json`。

**Medium — 使用手册的后续一致性问题。** `/guide` 初始 HTML 仍有“以登录后页面为准”的旧表述，章节 hash 由 JS 选择而非原始 HTML 锚点；API 不可用时保留静态手册，但不会出现完整交互章节。本轮没有扩大为第五页改造。已有三章节在本地合成状态下验证可切换；不能据此称手册无 JS 场景完全一致。

**Unknown — 排名、索引、转化与 AI 引用。** 当前没有百度搜索资源平台的最新查询和页面数据，未取得可用关键词量级、排名难度、点击率、自然注册数据或 AI 引用样本。不能把增加内容、Schema 或 llms 文件等同于收录或引用保证。

**安全提醒。** 会话上下文出现过服务端凭据，建议独立安排轮换和权限核查；本轮未使用这些凭据，也未把它们写入代码、测试或报告。

## 交付与边界

- 本地首页：[预览入口](http://127.0.0.1:5187/)；[价格](http://127.0.0.1:5187/pricing)、[实时辅助](http://127.0.0.1:5187/features/realtime-interview)、[程序员场景](http://127.0.0.1:5187/features/ai-interview-assistant)、[下载](http://127.0.0.1:5187/download)。
- 首页和交互手册采用已有合成预览数据；价格页采用构建时核验的真实商品目录。本地不要用于真实支付或下载测试。
- 代码位于隔离候选 `artifacts/cn-homepage-layout.82qdGV/candidate`，不是根目录旧版本应用。
- 本轮没有修改首页源码、robots、canonical 策略、URL 结构、登录、支付、面试、ASR、桌面程序、海外版本、数据库或生产环境。
- 本轮源码增量 12 文件；预览辅助 2 文件分包。补丁依赖此前 `cn-homepage-refined-20260912.local`，不能直接混入脏工作区部署。
- 源码与预览分包另保存在 `design/previews/cn-homepage-layout/seo-round1`，避免只依赖被忽略的临时构建目录；本轮未提交 Git。
- 如后续批准上线，需重新构建、重新核验生产价格，并按现有国服发布流程部署；不可发布过期价格快照或把预览夹具打包上线。

验收证据：[目录及补丁清单](/Users/liyulong/liyulong/1_projects/offersteady/artifacts/cn-homepage-layout.82qdGV/seo-round1-validation/patch-manifest.json)、[原始 HTML 检查](/Users/liyulong/liyulong/1_projects/offersteady/artifacts/cn-homepage-layout.82qdGV/seo-round1-validation/raw-html-evidence.json)、[测试对照](/Users/liyulong/liyulong/1_projects/offersteady/artifacts/cn-homepage-layout.82qdGV/seo-round1-validation/test-comparison.json)。

下一步见 [SEO-OPERATIONS-PLAN.md](/Users/liyulong/liyulong/1_projects/offersteady/docs/audits/cn-core-search-content-20260912/SEO-OPERATIONS-PLAN.md)。
