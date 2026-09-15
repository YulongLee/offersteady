## Context

结束面试的 API 已调用统一终止流程，流程会关闭发布器、ASR 连接并清理音频队列。但实时服务仍保留多组以 session id 为键的进程内字典，截图适配器也只在正常消费路径释放 bytes。Python 释放对象后 RSS 可能暂时不下降，因此需要同时修复生命周期遗漏并让指标区分当前资源和历史峰值。

## Goals / Non-Goals

**Goals:**

- 结束或自动回收面试后，所有会话级实时对象都从进程内索引移除。
- 对未完成的截图上传意图和 payload 按过期时间回收，不依赖用户再次请求。
- ASR 连接关闭保持幂等，并在关闭失败时记录可诊断状态。
- 用回归测试覆盖显式结束、空闲回收和过期上传。

**Non-Goals:**

- 不改变面试页面布局、用户可见文案或回答模型提示词。
- 不把音频、截图或个人资料改为长期持久化。
- 不引入新的外部依赖或更换 ASR/视觉供应商。

## Decisions

1. **集中清理会话索引。** 在 `_reset_realtime_session` 中统一移除所有以 session id 或 session/source key 保存的短期状态；保留按进程维度的累计计数器。这样结束、超时和替换会话共用同一释放路径，避免遗漏。

2. **截图采用惰性 + 主动双重回收。** 每次发起/确认/上传操作前先清理已过期记录，并增加轻量定时 sweep；释放时同时删除 intent、pending payload 和 uploaded bytes。相比仅依赖请求触发，能处理用户关闭页面或网络中断场景。

3. **ASR 关闭幂等化。** 关闭操作先从索引摘除，再通知 provider 和接收线程；重复关闭视为成功，不重复创建资源。失败只记录诊断计数，不阻塞会话状态落库。

4. **测试优先验证资源可达性。** 测试断言结束后各短期索引为空、ASR active session 为零、过期截图 bytes 被删除；不把 RSS 下降作为唯一断言，因为 Python allocator 可能保留已释放内存。

## Risks / Trade-offs

- [Risk] 定时 sweep 与请求并发可能发生竞态 → 使用现有锁，并让删除操作幂等。
- [Risk] provider 关闭网络失败 → 先移除本地引用并记录失败，后续 stale-session sweep 继续兜底。
- [Risk] 过早删除仍在处理的截图 → 只回收超过 TTL 且未被处理中的 intent/payload，并在任务完成路径显式释放。

## Migration Plan

1. 发布 Backend 代码并观察当前 RSS、ASR active sessions、回收失败计数和截图临时对象数量。
2. 若连接关闭异常增加，回滚 Backend 镜像即可；不会修改数据库结构或用户数据。
3. 低峰期重启一次旧进程以释放历史堆峰值，然后用新版本验证内存曲线是否稳定。

## Open Questions

- 生产容器的 memory limit 由部署平台决定，本变更不擅自调整额度。
- 是否将当前 RSS 与 cgroup current/max 纳入管理员面板，可作为后续独立变更。
