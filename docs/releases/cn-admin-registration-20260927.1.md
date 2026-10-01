# 国服后台注册时间展示 — 2026-09-27

部署完成：2026-09-27 00:47:28 +0800。只更新国服 Admin 的用户注册时间显示；新增用户统计、积分账本及面试业务不变。

## 基线与范围

基于实际运行的 [用户搜索版](cn-admin-user-search-20260924.1.md) `offersteady-cn-admin:user-search-20260924-1`。从其已发布源码包提取独立候选，确认原 JS/CSS SHA-256 与运行容器完全一致，只替换 `ChinaUsersPanel.tsx`、`china-users.css` 和对应测试。没有从主工作区整体构建或使用业务服务旧源码覆盖后台。

新页面显示“注册时间（北京时间）”，列表及选中用户身份区均使用现有 `created_at_ms`，缺失/非法值显示“—”。没有新增后端接口、请求频率或依赖，没有修改真实用户权益或注册记录。

## 验证

- 独立生产基线 14 个文件、92 项 Admin 测试通过，使用 America/Los_Angeles 时区验证固定北京时间；类型检查和生产构建通过。
- 真实生产候选包在 1440px/390px 合成浏览器检查中通过：时区跨日、身份选择、搜索后清除旧时间、内部表格横向滚动、无页面异常或真实写请求。初次浏览器夹具未覆盖旧 App 初始概览请求，补齐测试拦截后通过；未改动 App 逻辑。
- OpenSpec strict、diff 检查、发布脚本语法、Nginx 配置检查通过。
- HTTPS 首页内容与候选一致；新 JS/CSS 公网 SHA-256 一致；原 JS 仍 200。未登录用户查询仍 401，管理鉴权未绕过。
- 用户首页及健康端点正常，后端 healthy；配置文件及 Admin 环境未变，所有非 Admin 容器 ID/启动时间未变。
- 容器切换后第一次连接重置由有界重试成功恢复，没有触发回滚。Admin 重启计数 0。

## 产物

- 发布目录/`admin-current`：`/opt/offersteady/releases/20260927-cn-admin-registration-1`。
- 新镜像：`offersteady-cn-admin:registration-20260927-1`，ID `sha256:613a0573fe36b0e0bd1a71e1b6737831330ffb2ce0eed0e30de471dbaacab205`。
- JS：`index-Dn4CIr1E.js`，SHA-256 `6a4b060663b1dfd43f6fd06c4c7437e84c9c5030db9abdd16ed4a0472f9375e4`。
- CSS：`index-DD0eN98m.css`，SHA-256 `da62311a83a8236da61d8fa23a712c6acb34bf04c8516cffd21ef155ea353330`。
- 源码包：`source.tar.gz`，SHA-256 `a0d34b8bc953cc6312ccae2cd63bbc11b3e8b95cca3182b917eeb3ac154eee88`。
- Nginx 配置 SHA-256 保持 `6a20351f8d9eb039eb5051a3d2b74d0ffde5310d0edf9193d733972af3a1e8cf`。
- 服务器发布证据：`containers-before.txt`、`containers-after.txt`、`verified-at.txt`、环境哈希、下载比对文件和 `deploy/release-admin.sh`。

## 回滚

旧镜像 `offersteady-cn-admin:user-search-20260924-1`（`sha256:c7a27ee543f75d8e03f7e3ffbeca087a45d20d8d9a43a36ab4e6ad3a95b91921`）保留。只将 Admin 切回该镜像并恢复 `admin-current` 到 `/opt/offersteady/releases/20260924-cn-admin-user-search-1`，不要更新其他服务或恢复数据库。

本次未更新国际服、用户 Web、Backend、桌面助手、数据库或其他容器，未推送 Git。线上验证为短时发布检查，不代表长期监控或真实积分写操作验收。
