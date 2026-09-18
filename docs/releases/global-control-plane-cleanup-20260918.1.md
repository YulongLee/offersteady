# 国际服控制面降频与会话资源清理

## 范围

- 将准备页心跳和桌面连接状态建议刷新周期调整为 10 秒，降低空闲轮询请求量。
- 将 Backend 控制面缓存预算调整为 10 秒，并保留绑定变更后的主动失效行为。
- 拒绝已结束会话或已关闭发布者继续上传音频。
- 面试结束时清理 ASR、音频队列、临时音频缓冲、帧回执和发布者短期状态。
- 修复国际服发布包缺少会话回收配置导致实时指标接口返回 500 的问题。

## 验证

- 本地资源清理和控制面回归测试：62 passed。
- Web 轮询回归测试：2 passed；全项目 TypeScript 检查通过。
- 国际服 Backend 和 Global Web 生产镜像构建通过。
- 公网 `/healthz`、`/api/v1/web/state`、`/app` 和构建清单返回成功。
- 实时指标接口恢复成功；部署后活跃 ASR、排队音频帧和活跃会话均为 0。
- 部署后 Backend 日志未出现错误；国服健康检查保持成功。

## 发布与回滚

- Host：`47.84.65.103`
- Release：`global-control-plane-cleanup-20260918.1`
- Release path：`/opt/offersteady-global/releases/20260918-global-control-plane-cleanup-1`
- Current：`/opt/offersteady-global/current`
- Rollback images：`offersteady-global-backend:rollback-before-control-plane-cleanup-20260918`、`offersteady-global-web:rollback-before-control-plane-cleanup-20260918`
- PostgreSQL、Redis、Analytics、Material Worker 和 Admin 未重建或重启。
