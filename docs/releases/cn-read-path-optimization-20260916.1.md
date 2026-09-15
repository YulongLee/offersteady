# 只读链路优化（国服与国际服）

## 内容

- 管理后台请求改为 telemetry 分类，不再抬高用户 API P95。
- 为 `interview_sessions` 的 live/未删除/最近活动查询增加部分索引。
- 保持现有接口响应、权限校验、面试和实时音频流程不变。

## 验证

- 后端相关测试：24 passed，16 subtests passed。
- 管理端测试：54 passed。
- 管理端 typecheck/build 通过。
- OpenSpec strict 校验通过。

## 部署状态

本变更已部署到国服与国际服。国服后端使用 `cn-read-path-20260916-1` 镜像；国际服后端使用 `global-cn-read-path-20260916.1`，管理端同步更新。国际服 Web 保持原有 `global-app-entry-shell-20260915.1` 版本不变。
