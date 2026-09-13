# 国服首页加载与测试优化 · 本地验收

版本：`cn-web-loading-20260913.local`。**未部署，未修改海外版本、后端、环境变量、真实价格或支付逻辑。**

使用 OpenSpec propose/apply 技能把用户本轮批准范围限定为首页加载和十项失败测试。变更为 [optimize-cn-web-loading-and-regressions](../../openspec/changes/optimize-cn-web-loading-and-regressions/proposal.md)，7/8 项任务完成；总 JS 预算一项仍未解决，不归档、不视作生产发布通过。

## 修改结果

| 项目 | 修改前 | 修改后 |
| --- | ---: | ---: |
| 首页 main 脚本，未压缩传输大小 | 452,836 B | 400,328 B |
| 首页全部初始 JS，含同步依赖 | 520,634 B | 468,120 B（减少 10.09%） |
| 上述初始 JS 的逐文件 gzip 合计 | 155,177 B | 141,197 B（减少约 9%） |
| 全站所有 JS 文件合计 | 1,373,364 B | 1,374,135 B |
| 前端测试 | 404/414 通过 | 418/418 通过 |

这里的字节减少不等同于页面加载时间、业务 API p95、收音延迟或搜索排名同比改善。未执行真实面试或生产压力测试。

### 加载逻辑

- 从 App 机械抽离 LivePage，首页不再同步加载其会话页面、对话监视等代码。共享账号状态保持单一 Context，品牌/账号菜单通过现有 UI 插槽传入。
- 在准备页挂载时预加载工作区与已有回答渲染模块，只有加载代码，不开始收音、回答、订单或会话。直接访问面试页仍有 Suspense 加载状态。
- 对抽离前后函数进行文本还原比较：除签名与品牌/菜单插槽外，LivePage 全部生命周期逻辑一致。真实 lazy 测试覆盖 Context、手动回答、暂停/恢复、AbortSignal、定时器及唤醒事件清理。
- 没有删 Word 导出、公式显示、登录、购买或截屏能力，没有增加客户端密钥。

### 十项旧失败

九项为旧首页/导航断言，与已批准的 [首页商业化记录](cn-homepage-commercial-development-20260907.md)、[常驻伙伴导航记录](cn-usage-film-partner-navigation-development-20260907.md) 和 [新版排版记录](cn-homepage-refined-preview-20260912.md) 不一致。现改为保护四卡、真实费率/权益、九项可折叠 FAQ、匿名手册、常驻伙伴入口，继续禁止无依据营销数据和自动加入。

一项为删除失败测试没有模拟删除服务，误走请求。现明确模拟网络错误，保留原错误提示和资料不丢失断言，并检查用户/文档/AbortSignal 参数。未改产品删除行为。新增四项测试：暂停伙伴活动不能加入，以及三项真实异步路由测试。

## 文件清单

以下均在隔离候选 `artifacts/cn-homepage-layout.82qdGV/candidate/`，不是根工作区旧版应用：

- `apps/web/src/App.tsx`：引用共享状态与异步 LivePage，准备页预加载；首页设计、登录和其他流程不变。
- `apps/web/src/LivePage.tsx`：原工作区机械迁移。
- `apps/web/src/app-context.ts`：共享 Context 和 hook，避免循环引用及状态副本。
- `apps/web/src/live-route-loader.ts`：单一导入 Promise、按需组件、可失败的可选预加载。
- `apps/web/src/route-components.ts`、`route-components.eager.ts`：生产延迟与原普通测试兼容入口。
- `apps/web/src/App.test.tsx`、`App.product-experience.test.tsx`、`App.partner-program.test.tsx`、`App.material-actions.test.tsx`：修复上述测试约束和隔离。
- `apps/web/src/live-route-loader.test.tsx`：真实异步边界测试，不用 eager 替代真实工作区。
- `apps/web/scripts/verify-route-split.mjs`：检查 HTML 中所有模块脚本、预加载和同步依赖的完整图，防止通过改 chunk 名掩盖首屏体积。
- `apps/web/package.json`：仅增加 `test:route-split` 命令，无依赖调整。

## 实际验证

在候选 `apps/web` 执行：

```sh
npm run typecheck
VITE_API_BASE_URL=http://127.0.0.1:9 npm run test -- --maxWorkers=2 --reporter=json --outputFile=../../candidate-tests-performance-round1.json
VITE_APP_ENV=production VITE_APP_DATA_SOURCE=api VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=cn-web-loading-20260913.local npm run build
npm run test:seo-p0
node scripts/verify-indexing-build.mjs
node scripts/verify-pricing-live.mjs
VITE_APP_ENV=production VITE_APP_DATA_SOURCE=api VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=cn-web-loading-20260913.local npm run test:route-split
npm run test:seo-build
```

- Typecheck、build、418 项测试通过；保留既有 localstorage-file 运行时警告。无独立 lint 命令，因此不声称 lint 通过。
- Source SEO：30 页通过；构建索引检查：30 页及 2 个法律页通过。
- 价格：只读验证公开生产目录 10 个商品与构建一致，快照未超过 24 小时。
- 实际生产模式依赖图：通过，LivePage、ConversationMonitor、AnswerMarkdown、Word 库不在首页初始依赖中。
- **`test:seo-build` 未通过**：总 JS 为 1,374,135 B，仍比 1,350,000 B 预算高 24,135 B。首页 410,000 B 子预算已通过；没有放宽预算。
- 本地隔离 Nginx：5 个核心页 × 普通/Baiduspider 两种 UA，30 个 sitemap URL、58 条内链、10 个初始本地资源、4 个只读业务入口通过；随机不存在 URL 返回 404。所有 15 个 JS 和 1 个 CSS 均为 200 且类型正确。不是生产环境重新验证。
- 本地浏览器：1440×1000 和 390×844，无水平溢出、H1 唯一、保留原设计，控制台检查未发现错误。价格/下载使用明确标注的合成预览数据。
- Spec strict 校验通过；补丁在保存的 before 和候选上分别做正向/反向 `git apply --check --verbose`，13 个文件全部实际检查，没有 skipped。

## 未解决事项

全站总 JS 包含按需的公式与 Word 库。本轮试验了 Oxc 二次压缩、迭代选项、docx 导入方式及临时 Terser；不足以关闭缺口，所以没有把这些实验引入源码或依赖，也没有改动数学/导出业务实现。当前不应宣称所有发布门禁通过。下一轮应独立评估大依赖的功能边界和替换成本，保护现有公式/导出功能。

真实网络断开导致的动态导入失败重试未做浏览器故障注入；预加载使用 allSettled，失败不阻塞准备页。仍需后续真实设备、网络条件及生产监测验证。

## 预览与保存

- [本地首页](http://127.0.0.1:5187/)：保留当前运行预览；未上线。
- [桌面截图](../../design/previews/cn-homepage-layout/performance-round1/desktop-1440.png)、[手机截图](../../design/previews/cn-homepage-layout/performance-round1/mobile-390.png)。
- [字节与资源证据](../../design/previews/cn-homepage-layout/performance-round1/before-after.json)、[真实依赖图](../../design/previews/cn-homepage-layout/performance-round1/bundle-graph.json)、[测试摘要](../../design/previews/cn-homepage-layout/performance-round1/test-summary.json)。
- [13 文件清单与哈希](../../design/previews/cn-homepage-layout/performance-round1/manifest.json)、[增量补丁](../../design/previews/cn-homepage-layout/performance-round1/source.patch)。

补丁基于本地已优化 SEO 候选，并非可直接覆盖当前生产的整包。未来发布需另获授权，对照实际国服版本并处理未完成预算门禁；不要部署根目录未确认改动。
