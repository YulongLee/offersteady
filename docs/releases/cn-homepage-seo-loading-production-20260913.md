# 国服首页、SEO 和前端加载优化发布

生产版本：`cn-homepage-seo-loading-20260913.1`。地址：[mianshiwen.cn](https://mianshiwen.cn/)。

2026-09-13 01:26–01:29（北京时间）完成静态切换和镜像固化。仅发布用户随后明确授权的国服内容；没有更新海外版、后端、管理平台、数据库、认证、支付逻辑或环境变量。

## 来源和范围

使用 OpenSpec apply 流程记录了从本地验收到明确授权上线的范围变化，未将未完成的体积预算项目标为完成：[变更任务](../../openspec/changes/optimize-cn-web-loading-and-regressions/tasks.md)。

下载当前运行中 Web 所对应生产源码，与原隔离基线确认一致；使用生产快照叠加前三轮累计 32 文件允许清单构建，没有发布根工作区的其他未确认修改。

- 首页：已验收的排版、四项能力展示、演示图、下载入口、真实价格和 FAQ。
- 搜索内容：首页与既有价格、下载、实时辅助、程序员场景内容和内链；没有新增 Landing Page、改 canonical、造价格或评价。
- 加载：面试工作区按需加载，准备页预加载；原收音、回答、积分、登录和购买实现保持不变。
- 配套回归测试、检查脚本和精确 JSON-LD CSP 哈希同步。
- 发布时只额外给四个已修改 SEO HTML 的共享 CSS 链接加版本查询参数，避免老浏览器沿用一天缓存。未改变四页正文或 URL/canonical。
- 没有打包本地预览入口、合成预览账户、开发环境配置或任何密钥。

[32 文件清单及哈希](../../artifacts/cn-release-20260913/allowlist.json)；[打包源与发布脚本](../../artifacts/cn-release-20260913/release-ops.py)。

## 发布保护和基线

- 保存运行中 Web 全部静态文件、Nginx 配置、允许清单内的原源码，以及当前实际容器文件快照镜像。
- 在两个不同采样时间及首页切换紧前确认：近 30 分钟活跃面试、活跃面试页面、在线助手、活跃 ASR 音轨均为 0。紧前 capacity 样本约 16 秒，API P95 52.67ms，5xx 率 0。这只是当时窗口，不是压测或性能承诺。
- 先安装资源，再逐文件原子替换页面，`nginx -t` 后平滑 reload；未运行全栈 compose up，未重建或主动重启任何原有容器。
- 8 个原容器 ID、镜像 ID 均保持一致；除发布前已反复退出的 material-worker 外，启动时间全部一致。
- 75 个新构建文件逐项校验 SHA256；全部 28 个原 assets 文件逐字节保留。
- 写入全部结束后使用不暂停容器的 commit 固化镜像，创建未启动的检查容器，核对镜像内版本、配置、新资源和全部旧资源，然后更新 latest。临时镜像检查容器已删除；本地只读验证容器也已停止并自动删除，不涉及业务数据。
- 32 个源码文件同步到实际 Web compose 的源码目录，保留审计清单。后续 rebuild 必须显式设置对应公开版本号，不能从脏根目录直接部署。

## 实际验证

| 项目 | 结果 |
| --- | --- |
| Typecheck / 正式 build | 通过 |
| 完整前端测试 | 54 文件，418/418 通过 |
| SEO 源码检查 | 30 页通过 |
| 索引构建检查 | 30 sitemap 页面及 2 法律页通过 |
| 发布前实时价格检查 | 10 个商品，与构建逐项一致，快照未超 24 小时；紧前复查通过 |
| 真实首页依赖图 | 通过；LivePage、ConversationMonitor、AnswerMarkdown、Word 库不在首屏同步图 |
| 全站 JS 预算 | **未通过：1,374,155 B，超 1,350,000 B 门槛 24,155 B** |
| 首页入口预算 | 400,338 B，低于 410,000 B |
| 首页实际全部初始 JS | 468,140 B；本地优化前 520,634 B，减少约 10.08% |
| Lint | 项目未配置独立 lint 命令，不声称通过 |
| OpenSpec strict | 通过；总 JS 任务继续未完成 |

上述 JS 数值使用最终生产版本字符串；与本地验收版本的总量差 20 B。没有放宽任何门槛。预算红项按已披露技术债保留，不把此次授权等同于所有门禁变绿。

生产原始 HTML 验证（不执行 JavaScript）：

| 页面 | 普通 UA | Baiduspider | 核对 |
| --- | ---: | ---: | --- |
| `/` | 200 | 200 | 唯一 Title/H1、Description、canonical、完整正文、链接与构建一致 |
| `/pricing` | 200 | 200 | 真实套餐金额、权益、有效期和实时目录一致 |
| `/download` | 200 | 200 | 下载说明、内链、结构化内容和 CSP 一致 |
| `/features/realtime-interview` | 200 | 200 | 实时建议流程、正文、元信息一致 |
| `/features/ai-interview-assistant` | 200 | 200 | 技术岗位场景、正文、内链一致 |
| `/sitemap.xml` | 200 | 200 | 与构建 XML 一致，仍 30 URL |

- 全部 30 sitemap URL × 2 UA = 60 次页面检查通过；另有 Terms/Privacy × 2 = 4 次通过。逐页完整 HTML、meta、H1、canonical、正文、链接和 CSP 精确比较；公开页无 noindex。
- 58 条核心内链通过；`/guide` 动态章节是既有客户端选择器，原始 HTML 不具有对应锚点，作为已知例外记录，未伪称已验证其浏览器章节跳转。
- 所有新增 JS/CSS（包括 LivePage 延迟块）均 200、类型正确、字节与构建一致；文档引用资源正常。
- `/login`、`/app`、`/app/billing`、创建面试、设备、准备和 live 路由只读 HTML 入口正常；不运行真实登录/创建会话/订单/支付操作。
- `/healthz` 正常，后端仍为 `cn-session-reclamation-20260911.1`；公开 billing 状态 200。当前公开可用支付渠道仅 `wechat`，本轮没有启用/关闭任何支付渠道，不声称支付宝真实交易已验证。
- 三个 1.2.15 安装包（macOS arm64/x64、Windows x64）GET Range 0-0 均 206、文件类型及 Content-Range 正常；未全量下载或安装。
- 不存在的公开 URL 返回真正 404。
- 本轮生产浏览器自动检查受工具超时影响，未完成新的桌面/手机生产截图；上一轮本地响应式验收和本轮全部原始 HTML/资源校验有效，但不将其冒称生产浏览器端到端测试。

[最终生产逐项结果和原始 HTML](../../artifacts/cn-release-20260913/final-production-http/production-verification.json)；[首次生产结果](../../artifacts/cn-release-20260913/production-http/production-verification.json)；[下载检查](../../artifacts/cn-release-20260913/downloads.json)；[418 项测试报告](../../artifacts/cn-release-20260913/test-results.json)。

## 发布前就存在的独立故障

**material-worker 持续启动失败：`ModuleNotFoundError: No module named 'argon2'`。** 启动导入链是 worker → deps → authentication_service → Argon2 PasswordHasher。发布前 restartCount 已超过 2,500，前后同一容器/镜像，期间仍自行重试。

这是已有后端依赖/镜像问题，不是本轮静态文件切换引入。它会妨碍该 worker 承担的资料后台处理，应该另行优先修复。本次没有擅自装依赖、重建 worker 或改后端，不能把“主后端 healthz 正常”当作全站所有服务健康。

其他已知限制：总 JS 预算、既有 guide 的无 JS 章节一致性、既有页面版本探测会触发刷新。本轮空闲门禁缩小在用用户被刷新的风险，不保证门禁读取后绝无新用户进入。没有运行真实面试压测，不能据此承诺收音/API p95 或搜索排名改善。

## 镜像、源码与回滚

- 最终镜像：`compose-web:cn-homepage-seo-loading-20260913.1`，同时标记 `compose-web:latest`。
- 镜像 ID：`sha256:ee8b1b39fb3ca6a8645ab44e2ab4df955716ebd066f14b2e750c95db3aef06b2`。
- 回滚基线镜像：`compose-web:before-cn-homepage-seo-loading-20260913.1`，ID `sha256:1e4ccae0dff6df2596590e5953e5fa3dcb9eda77efecbc95b4ad5f27f9a23f9e`。
- 生产发布/备份目录：`/opt/offersteady/web-releases/cn-homepage-seo-loading-20260913.1/`（长期目录，非 `/tmp`）。
- 实际 Web 源码：`/opt/offersteady/releases/20260911-cn-alipay-review-login-1`。后端 current 符号链接未改。
- 回滚操作：在上述发布目录运行 `python3 release-ops.py rollback`；恢复实际旧 HTML、固定 URL 静态文件、Nginx 配置和原源码，校验并平滑 reload，同时恢复 latest。新增 hash 文件和未引用新增源码保留，不删除业务数据。**只改镜像 tag 并不会回滚当前运行文件。**
- 本次未实际触发回滚；备份与镜像已核对，不能声称完成过生产回滚演练。

部署及技术检查不等于百度已经收录，也不保证排名超过竞品。
