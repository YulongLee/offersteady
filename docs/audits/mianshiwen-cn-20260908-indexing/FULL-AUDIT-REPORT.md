# 百度零索引第二轮技术排查与修复

日期：2026-09-08（北京时间）。范围：国服 `https://mianshiwen.cn/` 的生产代码、Caddy/Nginx 配置、30 个 sitemap 页面及现有法律、登录、404 路由；非全站内容扩张审计。按 SEO 技能的原始证据与置信度规则执行，OpenSpec 变更 `fix-cn-indexing-readiness`。

## A. 结论

**没有发现这 30 个 sitemap 页面被整体禁止索引的技术证据。** 修复前和修复后均为 30/30 HTTP 200、robots 允许、没有 noindex、自引用 canonical，且初始 HTML 有独立标题、描述、H1、正文与内链。不能把已发现的局部缺陷直接定性为整站索引量 0 的唯一原因，更不能把成功部署等同于已收录。

用户提供的平台数据：索引量 0、基本无自然流量、首页抓取成功、未见明显抓取异常；本次未直接登录平台验证这些数据，也未取得首次提交日期、逐 URL 处理结果或真实爬虫回访历史。

已于 **2026-09-08 00:38:12 +08:00** 发布 `cn-indexing-20260908.1`。经闲置门禁后仅更新 Web 静态文件及 Nginx 配置，平滑重载 Nginx；8 个现有容器 ID 不变，后端仍为 `cn-quick-answer-film-20260907.1`。没有修改登录、面试、支付、ASR、RAG、AI、Companion 或国际服。

前三项修复：公开页启动时正文被清空、旧版 JS/CSS 丢失、Terms/Privacy 返回首页且 noindex。下一阶段优先补齐百度处理状态证据、观察真实回访、单独优化前端包体与动态接口耗时；不批量增页。

## B. 潜在原因与确认的问题

下表基于 [校验后的发现](verified-findings.json)。High/Medium 表示处理优先级；不是百度已经给出相同原因。

|优先级|置信度|问题与证据|对索引/体验的影响|结果|
|---|---|---|---|---|
|Critical|Confirmed（未发现阻断）|30 个 sitemap 页面两种 UA 全部 200、可索引且自引用 canonical|没有已证实的整站 robots/noindex/渲染封锁|不得据此承诺收录|
|High|Confirmed|React 启动后在 state 返回前输出空的 RouteLoadingPage，替换原始静态正文|用户可见空白；执行 JS 的爬虫也可能看到暂时空内容。纯 HTML 爬虫原本仍能读正文|已保留公开 HTML 至真实状态就绪；失败时仍可阅读和重试|
|High|Confirmed|上一版 `/assets/main-DLJpquzR.js`、`main-BHNFoUEv.css` 返回 404|缓存旧 HTML 的用户可能无法启动应用；不意味着无 JS 抓取完全失败|旧文件已恢复；后续标准发布保留旧哈希资源|
|High|Confirmed|`/terms`、`/privacy` 返回首页 H1/canonical，响应头 noindex|直接影响这两个页面，不能解释 sitemap 内 30 页全部未收录|已输出原协议正文、自引用 metadata，法律页移除 noindex；私有路由保留|
|Medium|Confirmed|www 公共页面原先 200，与 non-www 重复|可能分散抓取与规范化信号；原有 canonical 已部分缓解|已公开 GET/HEAD 308 到相同 non-www 路径；不动 API/登录/工作台/短链|
|Medium|Confirmed|首页实质内容近期更新，lastmod 仍 2026-08-19|修改日期信号失真，但不是索引禁令|仅首页改成 2026-09-08，其余 29 页不虚假刷新|
|Medium|Confirmed|JS 总量 1,363,159 B，入口约 442.7 KB，超过现有预算|下载、解析及动态就绪耗时仍有优化空间|未放宽预算；此性能检查仍失败，需独立后续优化|
|Medium|Hypothesis|Pricing 核心文本约 648 字符，没有实际价格金额；部分决策页信息较概括|可能影响页面实用性或百度质量判断，不能仅按字数认定低质量|保留现有真实内容，不补编价格或堆砌词；后续人工评估|

## C. 17 项核对结果

1. **robots**：在线 HTTP 200，`User-agent: * / Allow: /` 覆盖 Baiduspider；30 页均允许。无需为了显式出现 Baiduspider 而重复加规则。
2. **meta robots**：30 页无 noindex；法律页修复后无 noindex；不存在页面有 noindex，符合错误页预期。
3. **X-Robots-Tag**：30 页均无 noindex；法律页修复后也无；`/login` 继续 `noindex, follow`。
4. **canonical**：30/30 与 sitemap URL 完全一致。non-www 是当前正式规范域名，不是错误指向。Terms/Privacy 修复前错误指向首页，已纠正。
5. **协议/主机版本**：HTTP non-www 一跳 HTTPS；HTTPS www 公开页一跳 non-www；HTTP www 两跳（先 HTTPS，再 non-www），无循环或丢失路径。登录/API 等不做跨主机改动，以免影响已有会话。
6. **sitemap 格式**：真实在线，合法 XML `urlset` 与标准命名空间，30 个唯一 URL；robots 中引用正确。
7. **sitemap 状态**：30/30 普通与 Baiduspider GET 最终 200，sitemap 原生 URL 没有跳转。
8. **sitemap 与 canonical**：30/30 逐字相同。
9. **爬虫原始 HTML**：30/30 包含独立 Title/Description/H1/正文/主要内链，普通 UA 与模拟 Baiduspider 的文件 SHA256 全部相同。
10. **JS 依赖**：28 个 SEO 专题/商业文档为独立静态 HTML；首页与 /guide 也有初始静态正文。交互增强使用 React，但原始核心正文无需 JS。已修复 React 等待接口时的清空行为，未重构接口。
11. **旧 JS 失效**：确认存在旧哈希 404，已从保留镜像恢复；原始 HTML 正文可读性不能与客户端启动成败混为一谈。
12. **软 404/重复/空正文**：随机不存在 URL 返回真正 404；30 页正文非空、正文 hash 和 description 均不重复。核心文本约 562–2540 字符，存在公共模板但不是 30 张完全相同的壳；质量判断仍需人工与平台证据。
13. **Privacy/Terms/Pricing**：上线后分别为自身正文；Pricing 原本即独立 HTML，仍无实时金额，不把它误报为首页 shell。法律正文直接提取自既有 LegalPage，没有改写企业主体或协议实质条款。
14. **服务器/CDN/WAF**：A 记录均解析至 101.133.147.212；实际 Caddy → Nginx。已检查配置未见 UA 特殊拦截或限流，实测两种 UA 一致。没有云控制台访问证据，不能排除云 WAF 的历史/地域/IP 策略。
15. **框架/路由**：国内使用 Vite + React，不是 Next.js；公开页由 Nginx 显式静态路由提供，没有全路径 SPA fallback。问题来自法律路由被纳入 noindex SPA 列表与 Provider 的加载分支，而非 Next.js middleware。
16. **lastmod**：首页已修正。其余 29 页保留 2026-08-19，不因本次纯检查更新时间；没有发现未来日期。
17. **内链**：30 页全部能由首页静态 anchor 图在 0–2 次跳转内到达，孤岛数 0。Terms/Privacy 原本已有首页链接，现内容可索引；保持 sitemap 30 条，不借修复增加内容页。

## D. 原始证据与逐页清单

- [30 个页面及两份法律文件逐页结果、完整 robots 与跳转表](PAGE-CHECKS.md)
- [可筛选 CSV：完整 canonical、robots、H1、description、正文长度与深度](PAGE-CHECKS.csv)
- [修复前所有请求记录](before/pages.json)、[修复后所有请求记录](after/pages.json)
- `before/`、`after/` 每个 URL 均保存 `*-ordinary.html/.headers` 与 `*-baidu.html/.headers`，没有执行客户端 JS。
- [sitemap/lastmod/链接深度核对](after/sitemap-summary.json)
- [真实 Chrome：本地接口失败时仍显示正文的 DOM](local-browser-api-failure.html)

最终 sitemap：**https://mianshiwen.cn/sitemap.xml**（仍 30 条）。最终 robots：**https://mianshiwen.cn/robots.txt**，原文见逐页报告，内容未修改。

请求采用串行、每次间隔 0.3 秒、连接超时 5 秒、请求超时 20 秒。伪装 User-Agent 只能检测 UA 差异，不能模拟百度真实出口 IP、地区、抓取预算或索引算法。

24 小时最多 20,000 条 Nginx 日志样本中，带 Baiduspider UA 的请求为 37 条：36 个 200、1 个 404。该样本包含我们的审计请求，未校验反向 DNS，**不能当作真实百度蜘蛛已经回访**。

## E. 修改文件与部署方式

实现以生产基线工作树为准：`/private/tmp/offersteady-cn-release-20260907.DTlvCc`。主工作区有大量未部署的独立改动，本次没有整体覆盖或发布它。

|文件（相对生产基线工作树）|修改|
|---|---|
|apps/web/src/public-startup.ts|捕获受信任公开初始 HTML，仅允许指定公开路径|
|apps/web/src/main.tsx、src/App.tsx|加载/失败时保留公开正文，不生成演示 state、不改认证恢复流程|
|apps/web/index.html|首次渲染的暗色背景，保留两枚百度验证标签|
|apps/web/src/legal-content.ts、src/LegalPage.tsx|既有法律文字无损提取，共享给客户端与构建|
|apps/web/legal-static.ts、vite.config.ts|生成现有 /terms 和 /privacy 独立 HTML 及 metadata|
|apps/web/public/sitemap.xml|仅首页 lastmod 更新|
|infra/nginx/default.conf|公开 www 归一；法律路由独立且不再 noindex；保持 API/私有行为|
|scripts/retain-web-assets.sh、infra/docker/web-retained-assets.Dockerfile|保留旧 JS/CSS，内容冲突拒绝发布、500 MiB 档案上限|
|scripts/deploy-v0.1.sh|标准 Web 构建后、切换前调用保留步骤；本次未运行其全服务部署流程|
|apps/web/src/public-startup.test.tsx、legal-static.test.ts|慢/失败 API、私有边界、成功切换、法律正文回归|
|apps/web/baidu-site-verification.test.ts、nginx-release-contract.test.ts|两枚标签各一次、公共重定向边界、法律与私有索引策略|
|apps/web/scripts/verify-seo-p0.mjs、verify-indexing-build.mjs|日期/路由策略与 30+2 构建文档的索引检查|
|openspec/changes/fix-cn-indexing-readiness/|获准范围、验收与任务记录|

部署文件层基于当前线上镜像，只叠加以上 Web 产物与已保留版本的原始哈希资产；没有重新打包/上传视频。发布时间门禁：0 活跃桌面连接、0 排队帧/worker、0 正在执行或等待的回答/截图、0 最近 30 分钟有活动的 live 面试，陈旧历史状态未修改。保留图片/脚本后先发布 assets，再原子替换入口 HTML，最后 Nginx 检查并平滑重载；没有重建业务容器。

线上源码仍在 `/opt/offersteady/releases/20260907-cn-home-downloads-1`，已按精确源文件清单同步修复。镜像 `compose-web:cn-indexing-20260908.1` / `compose-web:latest` 指向 `sha256:ce7db2a183f2f35327255218d026413f2963d4f1e89cb3510d71dd8347879207`。运行容器保持原 ID，使用已更新文件层；后续重建容器使用新镜像。

回滚证据：服务器 `/tmp/cn-indexing-release-20260908/backup/`、`publish.sh`、`core.before.txt`、`core.after.txt`，保留旧镜像 `compose-web:baidu-verification-20260908`。可恢复原 HTML、配置、源文件和镜像标签，无数据库回滚。临时本地与服务器验收容器已删除，用户业务容器未删除。

## F. 验证结果（不把失败项写成通过）

|检查|结果|
|---|---|
|npm run typecheck -w @offersteady/web|通过|
|VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=cn-indexing-20260908.1 npm run build -w @offersteady/web|通过，产出当前部署版本|
|npm run test -w @offersteady/web -- --maxWorkers=2|52 个文件、380 项通过；此前标签数量旧断言已纠正后重跑|
|npm run test:seo-p0 -w @offersteady/web|30 个公开页面源码检查通过|
|node apps/web/scripts/verify-indexing-build.mjs|30 sitemap + 2 既有法律文档通过|
|npm run test:seo-build -w @offersteady/web|**未通过**：总 JS 1,363,159 B > 1,350,000 B；入口约 442,700 B 也超过 410,000 B。保留已有预算，不掩盖剩余性能问题|
|lint|Web 未配置独立 lint 脚本；不能宣称 lint 已通过。修改文件 git diff --check 通过|
|bash -n scripts/retain-web-assets.sh scripts/deploy-v0.1.sh|通过；历史镜像保留脚本实际执行通过|
|Nginx -t|本地、服务器候选镜像、线上配置均通过；运行时 www 公开重定向、法律 200/无 noindex、登录 noindex、缺失资源 404 检查通过|
|真实 Chrome / 单元慢请求测试|本地 API 故障时正文和重试入口可见；单元测试覆盖 pending / reject / resolve / private route|
|上线后成对 curl|30+2 页全部 200，自引用 canonical、正文完整，两 UA 内容一致；旧 JS 与回答组件 200|
|OpenSpec strict validate|通过|
|PageSpeed/CrUX|API 限流，无有效分数/现场 CWV；不报告 LCP/INP/CLS 改善百分比|

本节点单次首页 HTML TTFB：修复前 0.179 s、修复后 0.165 s；这是两次样本、没有统计显著性，**不是全体用户性能提升结论**。本轮确认修复的是“动态接口等待期间清空正文”，不是底层 API 加速或整体首屏性能全部达标。

## G. 无法从代码确定的零索引原因与下一步

1. 百度平台属性是否正好对应 `https://mianshiwen.cn/`，www 与 non-www 属性、数据统计窗口是否一致；请以截图/导出核对。
2. 首次提交、首次发现、sitemap 接受/解析的时间及结果；抓取诊断成功不代表所有 URL 已进入索引处理。
3. 真实百度蜘蛛是否持续回访；需要排除本次模拟请求，并做官方爬虫身份验证后分析。
4. 百度是否处于等待处理、去重/质量评估阶段，或有平台消息；没有证据就不能认定“惩罚”“沙盒”或固定等待天数。
5. 历史域名使用、站外发现/引用信号、不同地区/IP 下的云防护策略，本次没有完整数据。

建议保持当前 URL 和真实内容稳定，在正确站点属性中检查 sitemap 提交处理状态，并用首页、/features、/pricing、一个深层指南作抓取诊断样本。记录日期、抓取结果、索引量变化，不重复大改站点。如果平台给出具体异常或持续不处理，再以这些证据启动下一轮，不以“再生成更多页面”替代诊断。
