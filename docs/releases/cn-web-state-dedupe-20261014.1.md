# 国服 Web 状态请求去重 — 2026-10-14

## 当前状态：已撤回

10 月 14 日 22:36（Asia/Shanghai），在空闲门禁通过后只回滚 Web 到切换前的 `pricing-copy-hourly-20261011.1`，镜像 `sha256:df74779852799933e49aee117d1c45aaf3b789d29c8413caa994219ae50ab6a3`。去重候选误用了早于模拟面试发布的 9 月 23 日源码基线，导致新 Web 包缺少模拟面试路由。回滚后入口及能力接口检查通过，Backend/数据库/Redis 未切换。状态去重目前没有部署，须从实际运行 Web 重新准备候选并验证既有功能。下文保留首次发布的历史记录。

## 发布范围

本轮只更新国服 Web。`BackendPreviewInterviewAdapter` 对 `/api/v1/web/state` 增加登录态隔离的并发请求合并、1.5 秒成功缓存和强制刷新边界；失败不缓存，调用方取消不会中止共享请求。登录、退出、删除面试、资料处理轮询和账单同步等需要权威状态的路径使用强制刷新。

没有修改 Backend、数据库、Redis、Admin、Worker、模型、支付配置或桌面助手。

## 版本与切换

- 公网版本：`web-state-dedupe-20261014.1`
- Git 提交：`f21ac11`，标签：`release-20261014.1`
- 发布目录：`/opt/offersteady/releases/20261014-cn-web-state-dedupe-1`
- 前一目录：`/opt/offersteady/releases/20260923-cn-quick-stage-1`
- 新 Web 镜像：`sha256:3cb599b2449f82270f1d5dd977c29c476dd135747ef17d12f4475103aed0711b`
- 回滚镜像：`compose-web:rollback-before-web-state-dedupe-20261014-1`

切换前两次空闲门禁均为：进行中面试 0、有效页面租约 0、近 30 秒音频轨道 0、未完成回答 0。仅重建 `compose-web-1`，其他容器保持不变。

## 上线检查

- Web 生产构建和 TypeScript 检查通过。
- 隔离候选容器冒烟通过，生产构建清单为 `appEnv=production`、`apiBaseUrl=/`。
- 公网首页、登录页、健康接口、`/api/v1/web/state` 和构建清单均返回 HTTP 200。
- Web 容器重启计数为 0；上线后短窗口没有 error、emerg、crit、alert 或 traceback 日志。

这轮发布验证了可用性和请求去重代码已生效；API P95 和请求量的实际改善需要在用户测试窗口继续观察。
