## Context

实时页已经具备双声道 ASR、稳定问题候选、单页面租约和流式快答链路。当前只有显式点击快答会创建回答任务。新增自动回答必须复用这条已验证链路，不能把 ASR partial 直接交给模型，也不能改变字幕、计费或 Prompt 语义。

## Goals / Non-Goals

**Goals:**

- 提供默认关闭、可持久化且刷新后状态一致的会话级开关。
- 只消费开启后产生的、高置信度确认的面试官问题。
- 保证一个候选问题最多创建一个自动回答，并保持单个活动回答任务。
- 复用现有流式快答、RAG、语言/编程设置、计费和回答展示。
- 保持关闭状态下的当前链路、性能和界面行为不变。

**Non-Goals:**

- 不修改 ASR、VAD、字幕稳定算法、问题检测阈值或伴随程序。
- 不新增回答模型、Prompt、逐字动画或后台无页面回答。
- 不对低置信度、候选人麦克风、partial 或混合来源自动回答。
- 不取消用户关闭开关前已经开始的回答。

## Decisions

### Persist the switch and activation boundary on the session

会话保存 `auto_answer_enabled` 与 `auto_answer_enabled_at_ms`。每次从关切到开时重置开启时间，浏览器只消费不早于该边界的候选问题，因此开启功能不会补答历史问题，刷新后也不会丢失边界。替代方案是仅用 React 本地状态；它在刷新、多标签和重连后会漂移，因此不采用。

### Browser orchestrates the existing answer stream; backend owns authorization and claims

当前 Live Answer 的正文通过请求级 SSE 直接返回浏览器。页面收到合格的 confirmed candidate 后调用原有流式回答接口，并带 `triggerMode=auto` 和 candidate id。后端在创建任务前重新校验会话开关、开启时间、问题所有权和候选状态，并原子认领 candidate；任务创建后把 task id 回写到 candidate。这样不需要引入第二套服务端推送正文协议，首字性能和现有渲染路径保持不变。

替代方案是由 ASR 服务直接后台启动模型，然后把回答正文转发到会话 SSE。这会耦合 ASR、计费、Chat 生命周期和回答恢复，增加重复推流及部署风险，本轮不采用。

### Reuse the manual quick-answer pipeline with an explicit trigger mode

自动回答只改变触发来源，不改变问题冻结、资料快照、语言/编程设置、Prompt、模型、RAG、答案流、扣费或持久化。任务事件记录 `auto`，手动操作继续记录 `manual`，用于非敏感计数和故障定位。

### Gate on stable interviewer questions and one active answer

只有系统声道生成、状态为 `confirmed`、达到既有高置信度阈值、尚未绑定回答任务且位于开启时间之后的候选问题可触发。页面存在回答任务时暂不提交下一个候选；完成后再处理最新合格候选。页面租约失效、会话不 live、捕获暂停或声道降级时停止触发，但保留手动快答。

### Fail closed without disturbing manual actions

自动认领冲突视为已由其他页面或请求处理，不重复回答。自动请求失败时释放尚未绑定的认领，并在当前页面记住本次尝试，避免紧循环；用户可关闭后重新开启以建立新的边界。手动快答不经过自动门禁，行为保持原样。

## Risks / Trade-offs

- [问题候选在确认后继续修订] → 以 candidate id 作为业务幂等键，认领后不因文字修订再次扣费或生成。
- [多标签同时收到同一事件] → 单页面租约先隔离，后端 candidate 认领作为最终防线。
- [开启后立即收到缓存事件] → 服务端和前端都按 `auto_answer_enabled_at_ms` 拒绝历史候选。
- [自动回答消耗积分超出预期] → 默认关闭、开关状态清晰、沿用现有服务端余额校验与费率，不绕过计费。
- [部署期间新旧实例字段不一致] → 先执行向后兼容的 nullable/default migration，再部署兼容缺省值的 Backend/Web；旧客户端不发送 trigger mode 时按 manual 处理。

## Migration Plan

1. 为 `interview_sessions` 增加带默认值的开关和开启时间列。
2. 部署兼容旧请求的 Backend，再部署 Web；不重启 PostgreSQL、Redis 或桌面伴随程序。
3. 以默认关闭会话回归手动快答，再开启开关验证单题单答、流式显示、扣费和关闭行为。
4. 若异常，回滚应用镜像与 Git 到 `baseline-before-auto-answer-20260901`；新增列保留不影响旧代码。

## Open Questions

无。本轮按用户确认的默认关闭、页面顶部开关和复用当前回答链路实施。
