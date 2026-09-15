## Context

实时服务已有显式结束和部分惰性清理，但异常断开后的 live 会话只有在后续请求到达时才可能被回收。ASR 持久会话模式也会跳过 provider 空闲扫描，因此需要一个低频、幂等、可取消的后台回收器。实现必须不阻塞请求事件循环，不改变正常面试中的连接复用策略。

## Goals / Non-Goals

**Goals:**

- 在应用生命周期内定期回收超过空闲 TTL 的 live 会话。
- 回收路径复用现有 `terminate_session_for_admin`，保证 ASR、计费、发布器、队列和短期索引统一清理。
- 应用关闭时停止回收任务并关闭实时服务持有的 provider/线程池资源。
- 提供可观测的回收次数、最近一次运行时间和失败计数。

**Non-Goals:**

- 不在正常 live 且仍有心跳的面试中主动断开 ASR。
- 不强制 RSS 立即回落；Python allocator 的保留内存不作为回收成功判据。
- 不改变外部 ASR 协议、前端布局或敏感数据持久化策略。

## Decisions

1. **后台任务放在 FastAPI lifespan。** 使用单个 asyncio task，每次通过 `asyncio.to_thread` 调用同步回收，避免数据库扫描阻塞事件循环；退出时取消并等待任务结束。
2. **回收复用统一终止入口。** `reconcile_idle_sessions` 已具备批量和幂等语义，后台只负责调度和记录结果，避免复制清理逻辑。
3. **持久 ASR 仅由会话生命周期关闭。** 不改变“正常安静但仍 live”的连接复用；当后台将会话标记 ended 时调用 `_reset_realtime_session`，从而关闭持久 provider sessions。
4. **增加轻量运行指标。** 只记录计数和时间，不记录音频、截图、转写或用户身份信息。

## Risks / Trade-offs

- [Risk] 回收扫描与用户结束请求并发 → 终止入口保持幂等，单次失败记录后下一轮重试。
- [Risk] 过短 TTL 误结束用户 → 使用现有 20 分钟业务 TTL，并仅处理数据库确认的 idle live 会话。
- [Risk] 任务初始化触发外部 provider 配置错误 → 启动时捕获异常并记录，服务请求路径不受影响。

## Migration Plan

1. 本地启动并运行后台回收测试，确认任务可取消、超时会话被终止且 active provider sessions 为零。
2. 观察回收计数和失败计数，再由用户在低峰期部署。
3. 如需回滚，移除后台任务和新增配置即可，不涉及数据库迁移。

## Open Questions

- 生产环境是否进一步缩短 20 分钟业务空闲 TTL，留待线上观测后决定。
