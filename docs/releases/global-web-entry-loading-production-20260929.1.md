# 国际服网页加载优化 — 20260929-global-web-entry-1

## 发布结果

2026-09-29 18:53（北京时间）完成国际服 Web-only 部署。已发布基线为 `20260929-global-practice-1`，本次只替换网页容器。

切换前即时检查：进行中面试、近期准备、有效面试页租约、近期音频、未完成回答、运行中材料任务、活跃或近期模拟面试均为 0。Backend、Admin、Material Worker、Analytics、PostgreSQL、Redis 六个容器 ID 与发布前一致，未重启。国服、助手、模型、数据库、支付规则、CDN/DNS 和宿主机 Nginx 均未变更。

对应变更：[optimize-global-web-entry-loading](../../openspec/changes/optimize-global-web-entry-loading/proposal.md)。本地实现说明见[本地验收记录](global-web-entry-loading-local-20260929.md)。

## 已发布优化

- 公共首页、公共页面及登录入口不再等待业务状态；面试工作区按路由延迟加载。
- 保留真实鉴权，登录恢复支持取消与过期结果隔离，避免覆盖新的登录状态。
- 宣传视频封面接近可见区域才加载，视频点击播放后下载；静态 HTML 同样不提前请求媒体。
- 保持首页样式、十种语言、会员支付、模拟面试、联网回答和 Global 1.3.2 三平台助手下载地址。

正式构建首屏必需脚本 gzip 合计由 184,895 字节降至 129,955 字节，减少 29.7%。这不是线上响应时间下降 29.7% 的承诺。

## 实际验证

| 检查 | 结果 |
| --- | --- |
| 本轮重跑前端回归 | 28 文件、181 项通过，无失败/跳过 |
| 生产构建、TypeScript、英文文案及公共页面审核 | 通过；16 个可索引 URL |
| 本地生产构建浏览器检查 | 合成登录/状态、深链接返回、内部导航、退出、媒体播放、390px 布局通过 |
| 服务器发布包 | 217 个源文件/脚本/构建文件逐文件摘要验证通过 |
| 网页镜像与 Nginx 配置 | 构建及配置检查通过；沿用原网页服务配置 |
| 新公开文件 | 58 个通过本机 HTTP 与候选逐字节校验 |
| 旧浏览器兼容 | 原镜像的 56 个 assets 文件摘要保持一致 |
| 健康与入口 | 首页、登录、工作区入口、设置深链接、价格、下载、后台和后端健康检查通过 |
| 支付与模拟面试保护 | 支付目录摘要不变、Creem Live/ready；模拟 capability 开启、无需升级助手；匿名记录访问仍为 401 |
| 公网浏览器 | 首页交互、登录表单、未登录工作区跳转通过；没有公共入口业务状态/工作区脚本/媒体提前请求；没有页面异常或 HTTP 4xx/5xx |
| 发布后后端日志 | 检查时切换以来 Traceback 和 ERROR 均为 0 |
| OpenSpec 与 diff 检查 | 严格校验与 whitespace 检查通过 |

没有使用真实用户账号登录或创建面试，也没有真实支付、麦克风和模型验收。本次不能替代用户完整面试测试。

## 仍存在的限制

本机网络到国际服的一次公网冷加载：FCP 26,228ms，DOMContentLoaded 26,634ms。该样本依然较慢，不能据此宣称端到端速度问题已经解决，也不能外推为所有海外用户体验。代码拆分及按需请求已验证生效，跨区域线路/CDN 需另行定位与授权优化。

服务器磁盘约 85%，发布后剩余约 7.3GB；本轮没有清理用户文件或历史镜像。网页容器切换健康探测曾出现一次短暂连接重置，随后重试成功；当时没有活跃面试。

## 发布物与回退

- 当前目录：`/opt/offersteady-global/releases/20260929-global-web-entry-1`。
- Web 新镜像：`sha256:aa40ed431a67f81c36263b9051621cb63371b982fee55d25bc4769c29142c7c5`。
- Web 原镜像：`sha256:ebc05a4fe5d235dddf22af80b3a7bfe577df15467a2cd4a949644c88884d1683`，另保留 `offersteady-global-web:baseline-entry-20260929` 标签。
- 后端仍为原版 `20260929-global-practice-1`，本次不提高其版本号。
- `deploy-web-entry/compose.release.yml` 和 `compose.rollback.yml` 在服务器保存精确运行环境，权限 0600；未回传或提交密钥。

需要回退时先确认普通/模拟面试空闲，在当前发布目录使用 `infra/compose/docker-compose.global.yml` 加 `deploy-web-entry/compose.rollback.yml`，以项目 `offersteady-global` 执行 `up -d --no-build --no-deps web`，然后将 `current` 恢复至 `20260929-global-practice-1`。不要运行历史全组件部署脚本，不要回滚数据库或删除数据卷。

本地证据：`artifacts/global-web-entry-release-20260929/production-browser.json`、公网截图、候选 `deploy-web-entry/files.json`，以及 `artifacts/global-entry-loading-20260929/verification.json`。
