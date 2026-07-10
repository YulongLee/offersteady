## Context

OfferSteady 现在已经接入 DashScope 兼容的实时 ASR，但整体方式仍然偏“先让它能跑起来”：桌面端和后端之间仍有累计片段重复发送、同步阻塞式识别、source 级会话生命周期不稳定、partial/final 消费不统一、静音门控粗糙等问题。结果就是模型本身虽然支持实时返回，产品侧仍会出现首字慢、长时间无字幕、突然整段补出、静音乱出字等体验问题。

这次变更聚焦在“按阿里百炼官方推荐方式使用实时 ASR”，不是简单调几个阈值。我们需要把当前实现对齐到百炼实时接口的正确调用模型：业务空间专属域名、长连接、明确 session 初始化、VAD/Manual 模式配置、增量送音、partial/final 分离处理、连接复用、错误恢复与 provider-aware 观测。约束如下：

- 保持现有产品原型、面试流程和页面结构不变。
- ASR 供应商仍需保持可替换，不能把上层业务逻辑写死在 DashScope SDK 里。
- 不新增原始音频长期保存。
- 真实模型接入必须继续从服务端管理密钥，桌面端只能拿业务侧安全令牌。

## Goals / Non-Goals

**Goals:**

- 将实时语音识别接入方式调整为符合 DashScope Realtime ASR 推荐模式的实现。
- 降低首字延迟、减少 partial 抖动和整段补刷，提高最终字幕的连续性和稳定性。
- 把 provider 调用边界和桌面/后端编排边界拆清楚，便于后续继续做低延迟优化。
- 增加与 DashScope 调用强相关的链路指标和错误分类，让“为什么慢”“为什么没字”可以被准确定位。

**Non-Goals:**

- 不更换当前实时 ASR 供应商。
- 不修改 LLM、Prompt、RAG、截图回答或问答业务流程。
- 不新增用户可见的新页面或新交互。
- 不在这次变更里解决所有桌面音频采集兼容问题；这次主要解决 provider 调用方式与编排问题。

## Decisions

### Decision 1: Use source-scoped persistent DashScope realtime sessions

每个 `sessionId + sourceKind`（麦克风 / 电脑输出）维护一个独立的长生命周期 ASR 会话，而不是把每个 interim / final 都当成一次短请求。连接优先走阿里百炼官方建议的业务空间专属域名，而不是把公共兼容入口当成默认主路径。

这样可以：

- 避免重复握手和反复 `session.update`
- 更早接收 partial transcript
- 更好地贴合百炼 realtime 模型的使用方式
- 把“我 / 面试官”两路音频明确隔离

Alternative considered: 每个片段单独建立一次 ASR 调用。缺点是连接成本大、TTFT 波动明显、partial 体验差。

### Decision 2: Align transport with DashScope realtime event semantics

后端对 DashScope 的调用统一采用：

- 建连后先接收 `session.created`
- 再发送一次 `session.update`
- 音频通过 `input_audio_buffer.append` 增量写入
- utterance 结束时才 `input_audio_buffer.commit`
- partial 与 completed 事件分别处理
- 需要时允许通过 `turn_detection` 显式切换 VAD 与 Manual 模式

系统不得继续通过“把当前整段音频重新上传给同一 segment”来模拟 partial。

Alternative considered: 保留现有 segment 级 request/response 包装，只在网关内部兼容转换。缺点是仍会保留大量重复传输和同步阻塞。

### Decision 3: Treat VAD and Manual commit as provider-level strategies

百炼官方实时接口支持服务端 VAD 和手动 commit 两种模式。OfferSteady 不应把它们混成一个不可诊断的“静音阈值实现”，而是要把它们视为两种明确 provider 策略：

- 面试实时对话默认优先尝试 VAD 模式，以更早拿到 partial/final
- 当某一路 source 噪声复杂、误触发明显或 provider VAD 不稳定时，允许切回 Manual commit
- 模式切换必须体现在 provider runtime diagnostics 中

Alternative considered: 始终只用本地静音阈值控制 commit。缺点是与 provider 官方断句机制脱节，难以判断问题到底来自本地门控还是 provider 侧 VAD。

### Decision 4: Separate ingest, provider streaming, and transcript publishing

后端拆成三层：

1. ingest：快速验签、验 session、入队、立即返回
2. provider worker：负责与 DashScope 长连接交互
3. transcript publisher：负责把 partial/final 变成系统内 transcript 事件并推给前端

这样做可以把 provider 侧抖动从 API 接收路径上拿掉。

Alternative considered: 在 `process_audio_frame()` 里直接转写并保存 transcript。缺点是会把 provider 延迟直接暴露给桌面端推流。

### Decision 5: Treat partial and final as different products

Partial transcript 目标是“尽快显示最新可读内容”，Final transcript 目标是“稳定归档和后续回答触发”。因此：

- partial 允许覆盖旧文本
- final 才写入稳定上下文和问题识别触发链路
- 空白 partial、噪声 partial、已过期 partial 必须可抑制

Alternative considered: partial/final 走同一个持久化与展示路径。缺点是前端会频繁闪烁、后端上下文会被污染。

### Decision 6: Introduce provider-aware observability instead of generic timing only

除了通用延迟指标，还要记录 DashScope 特有的会话状态和错误模式，例如：

- connection recreated
- session.created missing
- session update failed
- append backlog
- commit timeout
- partial received but blank
- completed missing
- vad-to-manual fallback happened

这样才能区分“本地采集没进来”“后端没发出去”“百炼回了空结果”“前端没展示”。

Alternative considered: 只保留 capture-to-render 的总耗时。缺点是定位不到 provider 调用方式本身的问题。

## Risks / Trade-offs

- [Risk] 长连接状态机更复杂，容易出现 session 泄漏或僵死连接 → Mitigation: 增加 idle timeout、heartbeat 和 source worker 自恢复。
- [Risk] partial 更新过于频繁会增加前端和后端压力 → Mitigation: 对 partial 采用 freshness-first 覆盖策略，而不是逐条保序全发。
- [Risk] 过度依赖 DashScope 事件语义会削弱供应商可替换性 → Mitigation: 仅在 gateway / provider worker 层实现 provider-specific 逻辑，对上层暴露统一 transcript 契约。
- [Risk] 更严格的静音抑制可能丢掉极短有效发言 → Mitigation: 将 source health、utterance gate、publish suppression 分层配置，并保留可调参数。

## Migration Plan

1. 明确当前 DashScope 官方最佳实践接入目标
   - 固化推荐事件流、专属域名优先级、长连接模型、VAD/Manual 策略、partial/final 处理方式和失败恢复方式

2. 重构 provider gateway
   - 从 segment 级伪同步模式切换到 source 级持久会话
   - 支持 `session.created → session.update → append / commit` 事件流和 partial / completed 分离

3. 重构 backend realtime orchestration
   - ingest 快速返回
   - provider worker 后台持续推流
   - transcript publisher 将 partial/final 推送到现有前端订阅通道

4. 对齐桌面端送音策略
   - 不再累计整段重传
   - 只发送尚未发送过的 PCM chunk

5. 验证与回滚
   - 通过 feature flag 保留旧网关模式短期回退
   - 若 provider 长连接模式不稳定，可临时退回兼容模式，但保留新观测字段

## Open Questions

- 当前是否要优先走 DashScope 官方推荐的 SDK/事件封装，还是保留现有 websocket client 仅对齐事件模型？
- 系统音频与麦克风两路 source 是否都应使用相同的 partial 节奏，还是允许系统音频更保守、麦克风更积极？
- 是否需要单独增加一个内部诊断页或 debug mode，用来实时观察 provider backlog、TTFT 和空白 partial 抑制次数？
