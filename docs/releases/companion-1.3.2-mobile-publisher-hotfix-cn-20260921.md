# 国服 Companion 1.3.2 手机面试发布者热修复记录

## 修复范围

- 修复手机面试只启用 Mac 麦克风时，传输发布者仍以 `mixed` 身份创建、被 Backend 手机模式保护规则拒绝，导致麦克风采集无法启动的问题。
- 手机面试现在使用 `microphone` 发布者；电脑面试继续使用原有 `mixed` 双通道发布者，电脑面试链路不变。
- Companion 版本升级至 1.3.2，更新国服 macOS Apple Silicon、macOS Intel 和 Windows x64 安装包及公开发布清单。

## 自测结果

- Desktop 定向回归：17 项通过。
- Desktop 全量回归：36 个测试文件、200 项测试通过。
- Desktop 类型检查和生产构建通过。
- Backend 手机面试路由回归：6 项通过。
- `add-mobile-interview-audio-mode` OpenSpec 严格校验通过。
- macOS 两个安装包均完成 Developer ID 签名、Apple 公证、装订、代码签名和 Gatekeeper 验证。
- Windows x64 安装包结构验证通过。

## 安装包校验

- macOS Apple Silicon：`d27aa1e8ba3a5472f2e2338c09b5bbb94aa47c8df0d0421d40e16d8df1abbc3e`
- macOS Intel：`751e931bdcf0d7301f97aef2670473df03f5b8b1c11039527ccf26e97a361296`
- Windows x64：`571896b63c32763cbae1e566ffc73d9aab4520b074d31d9b670cb18bd599d26b`

## 国服部署与验证

- 切换前数据库中 `live` 面试数为 0。
- 发布目录：`/opt/offersteady/releases/20260921-cn-companion-132-mobile-publisher-hotfix-1`。
- 前一发布目录：`/opt/offersteady/releases/20260921-cn-mobile-interview-131-1`。
- 独立 Backend 回滚镜像：`offersteady-cn-backend:rollback-20260921-before-companion-132`。
- 仅重建国服 Backend 以加载新的发布清单；PostgreSQL、Redis、Web 和后台管理未重启。
- Backend 容器健康状态为 `healthy`，内部与公网健康接口均通过。
- 国服公开发布清单已显示三个平台均为 1.3.2；三个安装包分段下载均返回 HTTP 206。
- 部署后日志未发现 `ERROR`、`CRITICAL`、`Traceback` 或 `Exception`。

## 用户验收提示

已安装 1.3.1 的用户需要完整退出旧版 Companion 并升级到 1.3.2。进入手机面试后，Companion 应只采集 Mac 麦克风；请将手机外放置于 Mac 麦克风附近进行真实音频验收。
