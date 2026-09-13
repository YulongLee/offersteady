# 本轮 SEO 执行记录

日期：2026-09-12 至 2026-09-13，目标：国服本地候选四页内容质量与阅读体验。

使用 SEO 实施流程组织证据、优先级和未知数据；按 OpenSpec 创建 `enhance-cn-core-search-content`，采用真实产品文案与问答结构。没有开展新的完整竞品审计，也没有把旧审核材料当作当前排名数据。

## 修改范围及原因

路径均相对 `artifacts/cn-homepage-layout.82qdGV/candidate`。

| 文件 | 修改原因 |
| --- | --- |
| `apps/web/public/seo/realtime-interview.html` | 资料选择、识别纠错、点击快答流程、合成说明示例与章节导航 |
| `apps/web/public/seo/ai-interview-assistant.html` | 技术岗位区分、项目追问、代码核实、专题内链与章节导航 |
| `apps/web/public/seo/pricing.html` | 公开看价与登录购买、选择依据、费用限制、目录；保留真实价格生成标记 |
| `apps/web/public/seo/download.html` | 下载型 Title/H1；返回首页真实下载入口；区分安装与连接 |
| `apps/web/public/seo/public-search.css` | 四页限定深绿配色、阅读层级、侧栏高度、焦点；全局尊重减少动态效果偏好 |
| `apps/web/public/llms.txt` | 公开看价事实及技术场景锚文本 |
| `apps/web/public/llms-full.txt` | 同步完整工作方式、价格及下载说明，不写永久价格 |
| `apps/web/public/public-facts.json` | 同步动态事实与技术场景，保留 schemaVersion 1.1 和主体边界 |
| `apps/web/public/sitemap.xml` | 只更新本轮四页 lastmod，首页与其他页面不动 |
| `infra/nginx/default.conf` | 替换四页 JSON-LD 的精确 CSP 哈希；其余配置不变 |
| `apps/web/core-search-content.test.ts` | 新增 27 项回归，包括更新时间不能干扰价格快照校验 |
| `apps/web/scripts/verify-seo-p0.mjs` | 精确同步本轮四页的预期修改日期，不放宽任何预算 |

仅预览支持文件：`apps/web/vite.layout-preview.config.ts` 补充已有公开页的本地映射；`apps/web/src/test/layout-preview.tsx` 保留手册路径和章节 hash。两者单独分包，生产构建不用它们。

根目录仅新增本轮 OpenSpec 与此审计目录。根目录原有业务、海外版与未确认改动未纳入补丁。

## 执行与证据

1. 保存 `seo-round1-before` 快照，新增测试对旧快照运行红灯复现。
2. 实施四页内容和 scoped CSS，保留首页/robots/URL/canonical；机器可读文件同步。
3. 发现价格校验取首个 `<time>`，将说明日期放到价格区之后；原价格解析与订单逻辑未改。
4. sitemap 的初次文本补丁因日期行重复误配到首页和手册，被测试捕获；按完整 URL 上下文恢复基线，再仅更新本轮四页。最终30条映射检查通过。
5. 构建首次因未设置生产公共构建变量拒绝，保持保护不变；以 `VITE_APP_ENV=production VITE_APP_DATA_SOURCE=api VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=cn-search-content-20260912.local` 成功构建。
6. 执行 `npm run typecheck`、`npm run build`、全量 `npm run test -- --maxWorkers=2`、`test:seo-p0`、`verify-indexing-build.mjs`、`verify-pricing-live.mjs`、`test:seo-build`。结果和既有失败见 SEO-STATUS。
7. 独立本地 Nginx 在 127.0.0.1:18988 挂载只读构建与配置，backend 映射到容器自身，未连接本地现有或线上后端。运行 `verify-preview.mjs`，得到五页双 UA、30页、58链接、10资产和4入口证据。
8. 浏览器检查 390/1440 宽度、价格卡片、下载返回首页、正文键盘跳转及手册章节。原始手册 hash 缺少 DOM 锚点不是404，属于已有 JS 章节选择；本轮记录限制，不声称纯 HTML 章节导航通过。
9. 生成12文件源码补丁与2文件预览补丁，在独立临时目录重放后逐字节比对通过。

## 可复跑材料

本目录 `verify-preview.mjs` 用于已启动的本地18988站点，只发 GET/HEAD；`package-local-candidate.mjs` 用于生成受限补丁与证据清单。

原始 HTML、JSON、图片和补丁保存在 `artifacts/cn-homepage-layout.82qdGV/seo-round1-validation`。元数据与正文前后对照见 PAGE-CHANGES。

## 延后项与生产动作

延后既有业务 JS 体积整改、10项旧测试、手册一致性、真实排名与转化观测、竞品比较。**生产写操作为0：未部署、未改服务器配置、未创建订单、未发短信、未录音、未下载/安装助手。** 只读请求生产公开商品目录用于价格生成与核验。
