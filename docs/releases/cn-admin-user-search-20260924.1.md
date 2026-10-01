# 国服管理后台用户搜索 — 2026-09-24

## 范围与结果

已按用户授权完成开发、自测并于北京时间 01:32:46 更新国服 Admin。新增用户名/用户 ID 服务端搜索、分页、结果行权益操作、同名身份确认、重复提交与失败重试保护。未修改或部署 Backend、用户 Web、数据库、国际服及桌面助手，未调整任何真实用户积分。

## 生产基线与发布记录

- 原 Admin 镜像：`sha256:659a338a3df40665fe4bb053c6318d377e1c56e09f9a32e17c87d0b2deb8a7ae`。
- 实际 Admin 源码基线：Git `7fadc14c2b3a75b49d8f8f744bff12bb4afc27c5`。复构建 JS/CSS 与运行容器字节一致；服务器 current 源码及本地 HEAD 均不直接代表旧 Admin 运行版本，因此未整包覆盖。
- 原 JS：`index-CmKwNz3R.js`，SHA-256 `e54e40f4db876810b7e82c93ddc97c4294c85d3c06f5e574622dd8901c07e5f3`。
- 原 CSS：`index-B-FQEBr_.css`，SHA-256 `2b491d07f1072f2db329d87447cd5807847e69f91a651c9f3a0bb0e76687c3ad`。
- 新镜像：`offersteady-cn-admin:user-search-20260924-1`，`sha256:c7a27ee543f75d8e03f7e3ffbeca087a45d20d8d9a43a36ab4e6ad3a95b91921`。
- 回滚镜像：`offersteady-cn-admin:user-search-rollback-20260924-1`。
- 发布源码与产物：`/opt/offersteady/releases/20260924-cn-admin-user-search-1`，独立指针 `/opt/offersteady/admin-current`。
- 业务服务指针 `/opt/offersteady/current` 保持 `/opt/offersteady/releases/20260923-cn-quick-stage-1`，未切换。

后续 Admin 发布必须基于 `admin-current` 或核对实际运行产物后合并，不得从业务服务的旧 `current/apps/admin` 直接重建而丢失本功能。本地仓库保留相同功能的增量修改，未执行 Git 提交/推送。

仅将重建的静态文件叠加到原 Admin 镜像，保留原 Nginx、旧哈希资源及其他页面。生产基线差异仅为 App/API 接入及新增 ChinaUsersPanel 组件、样式与测试。

## 自测

- 本地 Admin 全量：14 文件、77 测试通过，含 23 项新增测试。
- 独立生产基线候选：相同 77 项测试通过。最初打包缺少 Nginx 测试依赖，补齐原配置后重新通过。
- 类型检查、国服构建、国际服构建兼容检查通过；国际服未部署。
- 浏览器使用 65 个合成用户验证模糊搜索、同名结果及选择、扣减确认、余额更新和首屏以外用户搜索。扣减仅产生一次测试命令，目标第二个同名用户从 500 变 480，第一名仍为 500。
- 浏览器控制台无错误，桌面与窄屏布局检查；没有以生产用户进行写操作验收。
- 测试覆盖查询响应竞态、分页保留关键词、查询失败、权限、整数/原因校验、取消确认、重复点击、相同内容重试及操作成功但刷新失败。
- OpenSpec 严格校验与 `git diff --check` 通过。

## 上线验证

首次切换因启动瞬间连接重置，健康检查过早触发自动回滚。检查确认旧版正常后，给同一启动检查增加有界连接重置重试，再次切换成功。没有改动运行应用逻辑以绕过检查。

- 新 Admin 容器启动时间：`2026-09-23T17:32:46.085334172Z`，重启计数 0。
- HTTPS 首页 200，引用 `index-CFJmxyze.js` / `index-DBq9SrIJ.css`。
- 下载 JS SHA-256：`746bb29eb61b43472285fe4415bc63955f1d57e99049c4eddac3ce689b0ae04f`。
- 下载 CSS SHA-256：`77508f26773b452e55f3ba862b8fd2e05a32b5992e0c5e4c96073ab82ce06a39`。
- 新资产与本地通过测试的候选一致；原 JS 仍返回 200。
- 未登录搜索返回 401，鉴权未绕过，代理未返回 502。
- 国服用户首页及 `/healthz` 均返回 200，Backend healthy。
- Nginx 配置哈希保持 `6a20351f8d9eb039eb5051a3d2b74d0ffde5310d0edf9193d733972af3a1e8cf`。
- 对比发布前后所有容器 ID/启动时间，除 Admin 外均未改变；证据保存在发布目录 `containers-before.txt` / `containers-after.txt`。

这属于发布后的短时检查，不代表完成真实账号积分操作或长期监控。

## Admin 独立回滚

只回滚 Admin，不运行 Compose 全服务更新，不切换业务 current，不改数据库或积分账本：

```sh
docker tag offersteady-cn-admin:user-search-rollback-20260924-1 compose-admin:latest
cd /opt/offersteady/current
docker compose -p compose --env-file .env.production -f infra/compose/docker-compose.foundation.yml up -d --no-build --no-deps admin
```

回滚后重新核验 Admin 200、未授权查询 401 和 Backend 健康，并将本记录标记为回滚，避免误把 `admin-current` 当作仍在运行版本。
