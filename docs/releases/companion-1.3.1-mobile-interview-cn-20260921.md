# 国服 Companion 1.3.1 与手机面试发布记录

## 发布范围

- 国服 Companion 1.3.1：macOS Apple Silicon、macOS Intel、Windows x64。
- macOS 两个安装包均完成 Developer ID 签名、Apple 公证与装订验证。
- 国服 Web 增加电脑面试 / 手机面试选择与手机外放引导。
- 国服 Backend 增加 interviewAudioMode 会话契约、持久化、配对下发、单麦克风路由和问题识别。
- 数据库仅执行向后兼容的 interview_audio_mode 增量字段与约束迁移。

## 发布门禁

- 切换前数据库中 live 面试数为 0。
- 仅重建并切换 Backend 与 Web；PostgreSQL、Redis、后台管理和异步任务容器未重启。
- 发布目录：/opt/offersteady/releases/20260921-cn-mobile-interview-131-1
- 前一发布目录：/opt/offersteady/releases/20260920-cn-polling-version-gate-1
- 回滚资料：/opt/offersteady/rollback/20260921-cn-mobile-interview-131-1
- 独立回滚镜像：
  - offersteady-cn-backend:rollback-20260921-mobile-131
  - offersteady-cn-web:rollback-20260921-mobile-131

## 验证结果

- Desktop：36 个测试文件、199 个测试通过；类型检查通过。
- Backend 手机面试定向回归通过；基于线上基线的发布包额外回归为 5 项通过。
- 国服 Web 类型检查和生产构建通过。
- OpenAPI 已包含 PATCH /api/v1/sessions/{session_id}/audio-mode 与 interviewAudioMode。
- 数据库字段默认值为 computer、非空，并限制为 computer / mobile。
- 三个平台 1.3.1 安装包均返回 HTTP 206 分段下载；两个 macOS 包标记为已公证。
- 线上 Backend 健康检查通过，Web 首页与公开健康检查返回 200。
- 发布后 live 面试数保持为 0，最近日志未发现 ERROR、CRITICAL 或 Traceback。
- 发布后观测：Backend 约 110 MiB，Web 约 3.5 MiB。

## 回滚说明

如需回滚，将 current 原子切回前一发布目录，把独立回滚镜像重新标记为 Compose 的 Backend / Web 镜像后仅重建这两个容器。新增数据库字段对旧版本向后兼容，无需紧急删除；会话表发布前备份保存在回滚资料目录。
