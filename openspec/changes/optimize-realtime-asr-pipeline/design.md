## Context

当前 OfferSteady 已经具备桌面伴随助手、后端 Realtime Speech 服务和网页实时对话区，但实时语音链路仍以“功能贯通”为主，而不是以低延迟为主：桌面端存在按段累计发送音频、重复序列化、同步等待识别结果、过度频繁的 interim 修订和静音误触发；后端存在在接收路径上同步调用 ASR、source 级工作单元缺少真正的 Producer-Consumer 解耦、性能指标不足以定位 TTFT 和 Final Transcript 的主要耗时；前端虽然已经改为订阅，但仍主要消费“落库后事件”，而非真正为 partial / final 设计的轻量增量模型。

本次变更的目标不是修补单个参数，而是重新定义整条 Realtime ASR Pipeline。约束条件如下：

- 不修改 ASR 模型、LLM、Prompt、RAG 和当前页面风格。
- 保持现有对外 API 形态不变，内部允许增加兼容字段、流式事件和运行指标。
- 外部语音供应商必须保持可替换，不能把实现强耦合到单一厂商 SDK。
- 不新增原始音频的长期持久化。

主要参与方：

- 桌面伴随助手：负责双 source 音频采集、缓冲、切块和发送。
- FastAPI Realtime Speech：负责 source/session 编排、队列、ASR 客户端、状态与指标。
- Web Live Conversation：负责消费 partial/final 事件并进行最小成本渲染。

## Goals / Non-Goals

**Goals:**

- 将当前同步、重复和阻塞较多的实时语音链路改为低延迟流式 Pipeline。
- 明确当前性能瓶颈，并给出从 Audio Capture 到 Overlay Rendering 的阶段性性能分析框架。
- 通过常驻 ASR 长连接、增量 PCM 发送、Producer-Consumer、RingBuffer/有界队列和增量渲染降低 TTFT、Final Latency、CPU 和 GC 成本。
- 在不变更产品原型和公开 API 的前提下，为当前 session 输出更连续、更可靠的 Partial Transcript 与 Final Transcript。
- 增加性能可观测性与回归验收，使后续优化能量化验证。

**Non-Goals:**

- 不更换 `qwen3-asr-flash-realtime` 或其他供应商模型。
- 不设计新的 LLM、Prompt、RAG、知识库检索或回答策略。
- 不修改网页原型布局、视觉风格或面试业务流程。
- 不在本次变更中引入原始音频历史回放存储。

## Decisions

### Decision 1: Replace request-response transcription with a persistent streaming pipeline

当前问题的根源之一，是后端在接收音频帧的请求路径上同步等待 ASR 返回，导致“采集 → 上传 → 转写 → 推送”成为一条串行长路径。新方案将其拆成：

1. Desktop Capture Producer
2. Source-local RingBuffer / bounded queue
3. FastAPI ingest endpoint or WS ingress
4. Session/source worker
5. Persistent ASR connection
6. Partial / final transcript event bus
7. Web subscriber

其中 ingest 只负责快速入队和返回，ASR worker 负责后台持续推流和消费结果。

Alternative considered: 继续沿用“每帧 HTTP / WS 请求立即做转写”的模式，只调 chunk 参数。缺点是同步等待仍然存在，延迟上限受单次往返和排队影响过大，无法稳定逼近目标 TTFT。

### Decision 2: Use source-scoped persistent ASR sessions

每个 `sessionId + sourceKind` 维护一个长生命周期 ASR 会话，麦克风和系统音频各自独立。source worker 只向各自的持久化连接发送新增 PCM chunk，并读取 partial/final 事件。

这样做的收益：

- 避免重复握手和频繁 `session.update`
- 允许 partial 更早返回
- 更适合把 TTFT 压到 300ms 级
- source 间互不阻塞，便于区分“我 / 面试官”两路延迟

Alternative considered: 按 utterance 或按 interim 片段创建短连接。缺点是连接成本高、抖动大、对厂商侧限流和本地 CPU 更不友好。

### Decision 3: Switch from cumulative segments to incremental PCM transport

桌面端不再反复上传“从 utterance 开始到当前时刻的整段音频”，而是：

- AudioWorklet / native runtime producer 按固定 frame size 产出 PCM
- 进入 source RingBuffer
- ASR sender 只发送尚未提交过的增量 chunk
- partial/final 只是 metadata 状态，而不是重新上传整段语音

Alternative considered: 保留累计片段，只通过服务端去重。缺点是网络、序列化、CPU 和 ASR 端重复计算都会继续存在。

### Decision 4: Prefer AudioWorklet/native producer over ScriptProcessor-style callbacks

桌面端音频采集和分块应尽量从主线程 JS 回调迁移到更稳定的实时音频执行路径：

- 优先 native runtime producer（如果当前桌面端原生采集已可用）
- Web fallback 使用 AudioWorklet
- ScriptProcessor 仅保留兼容后备

原因：

- ScriptProcessor 已经过时，且更容易受主线程调度影响
- AudioWorklet 更适合稳定小块实时采样
- 更少的 UI 主线程抖动意味着更低首字延迟和更少假信号

Alternative considered: 保留 ScriptProcessor，只调 buffer size。缺点是无法根治线程调度抖动和主线程竞争。

### Decision 5: Introduce bounded producer-consumer queues with freshness-first backpressure

每个 source 采用有界队列或 ring buffer，背压策略遵循“新鲜度优先于完整 interim 历史”：

- audio chunk 不允许无限堆积
- partial work item 可覆盖旧 partial
- final work item 不可丢失
- source worker 忙时，丢弃最旧 partial、保留最新 partial 和 final

Alternative considered: 保证所有 partial 都按顺序完全处理。缺点是实时字幕会被旧 partial 拖死，体感变差。

### Decision 6: Distinguish transport events from transcript events

链路上拆分两类事件：

- Transport event：音频帧收到、排队深度、ASR 会话状态、sender backlog
- Transcript event：partial updated、final committed、utterance closed

网页只消费 transcript 事件与少量诊断概览，不直接消费高频 transport 明细；明细进入性能诊断面板和日志。

Alternative considered: 所有状态统一走一个大 runtime payload。缺点是高频抖动会放大前端渲染开销，且难以区分业务字幕和性能诊断。

### Decision 7: Render partial/final via stable utterance identity and incremental reconciliation

前端实时对话区对每一句维护稳定 `utteranceId`：

- partial 到来：更新当前 utterance text
- newer partial 到来：覆盖旧 partial
- final 到来：标记完成并冻结文本
- empty/phantom partial：直接丢弃

渲染层需要最小化 React state churn，优先采用 session-local store + batched updates，而不是每条事件都全量重建 transcript 数组。

Alternative considered: 每次收到 transcript 都把整个列表映射一遍。缺点是会放大 GC、重排和无意义闪动。

### Decision 8: Treat silence detection as a calibrated subsystem, not a single threshold constant

当前“静音也出字”表明静音判定不能只靠单一固定阈值。新方案分三层：

1. Source health threshold：用于设备音量条与“有无声音”
2. Utterance gate threshold：决定是否开始形成实时 utterance
3. Empty transcript suppression：ASR 返回空白时不渲染

并为不同 source 允许独立校准参数，例如系统音频的底噪模型和麦克风不同。

Alternative considered: 只继续调一个全局 RMS 阈值。缺点是不同设备和系统输出场景差异太大，难以稳定兼顾。

## Risks / Trade-offs

- [Risk] 引入 source worker、持久连接和有界队列后，系统状态机会更复杂 → Mitigation: 按 source/session 明确状态图，并增加可重复的单元测试与集成测试。
- [Risk] 过于激进地丢弃 partial 可能影响局部可读性 → Mitigation: 丢弃策略仅针对过期 partial，final 和最新 partial 始终保留。
- [Risk] AudioWorklet / native runtime 切换可能带来平台兼容差异 → Mitigation: 维持分层采集接口，允许 native、AudioWorklet 和 ScriptProcessor 三级回退。
- [Risk] 长连接会话泄漏导致资源累积 → Mitigation: 为 source session 设置 heartbeat、idle timeout 和显式 close 逻辑。
- [Risk] 更多性能指标可能增加日志量 → Mitigation: 只保留摘要计数、采样指标和聚合窗口，不记录高频原始媒体内容。
- [Risk] “保持 API 不变”限制了大规模接口重构 → Mitigation: 在现有 API 之下增加兼容的内部队列、事件模型和诊断字段，对外保持主要入口不变。

## Migration Plan

1. 建立性能基线
   - 记录现有 TTFT、Final Latency、source backlog、CPU、内存、GC 与静音误触发率
   - 为当前链路打点，但不立即替换实现

2. 重构桌面端 Capture/Buffer
   - 引入 source-local 增量 chunk producer
   - 从累计片段发送改为增量 PCM 发送
   - 增加 ring buffer / bounded queue

3. 重构后端 ASR pipeline
   - ingest 快速返回
   - 为 `sessionId + sourceKind` 启动常驻 worker
   - worker 复用持久化 ASR 连接，拆分 partial/final 处理

4. 重构前端字幕消费
   - 基于稳定 utteranceId 做 partial/final reconciliation
   - 引入增量 state 更新和最小渲染策略

5. 打开性能与诊断面板
   - 输出阶段指标
   - 增加回归测试和压测脚本

6. 灰度与回滚
   - 通过 feature flag 保留旧链路回退路径
   - 若 persistent session 出现稳定性问题，可临时回退到兼容 sender，但保留新指标

Rollback:

- 保持现有外部 API 和页面不变，允许通过配置切回旧 sender / old gateway mode。
- 即使回退，也保留性能打点，以继续定位瓶颈。

## Open Questions

- 当前桌面端原生采集 runtime 是否已经具备足够稳定的双 source PCM producer，还是第一阶段仍需以 AudioWorklet 为主？
- DashScope realtime ASR 是否支持我们所需的持续 partial 频率与 source 长会话稳定性上限，是否需要增加 provider capability probing？
- 前端是否需要单独暴露一个“性能诊断模式”，只在内部调试时显示 queue depth、TTFT 和 source backlog？
- 对系统音频 source，是否需要增加独立的回声/底噪门控策略，以减少会议软件空闲时的假触发？
