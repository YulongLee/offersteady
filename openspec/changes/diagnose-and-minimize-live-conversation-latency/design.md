## Context

当前“实时对话”链路已经具备桌面伴随程序采集、后端接收、实时 ASR、网页订阅和页面显示这些基本部件，但用户体感仍然接近“准离线转写”：说完一句话后要等待很久才出现文字，甚至几十秒后整句一起补出。这个现象说明问题很可能不是单点配置，而是端到端链路中存在多个环节叠加放大延迟，例如：

- 桌面端采集节奏、设备切换和 chunk 发送策略不稳定
- 桌面端到后端之间存在排队、批量提交或重复累计发送
- 后端 ingest、worker、provider gateway 或 transcript publish 之间存在阻塞
- ASR provider 会话初始化、VAD/commit 或 partial/final 消费方式不合理
- 前端订阅和渲染只在 final 到达时刷新，导致“有结果但看起来很晚”

本次变更的重点不是继续猜测“可能是模型慢”，而是建立可以复用的实时链路诊断框架，把真实瓶颈定位到具体阶段，并给每个阶段设定预算与异常信号。约束如下：

- 不改变产品原型、面试主流程和页面风格。
- 不更换当前 ASR 模型，只优化接入方式、流水线和展示链路。
- 不新增原始音频持久化；诊断仅记录时间戳、计数、状态和错误分类。
- 外部语音供应商仍需保持可替换，provider 特定逻辑只能停留在 gateway / adapter 边界。

## Goals / Non-Goals

**Goals:**

- 建立桌面采集到网页显示的端到端延迟分段模型，并能稳定输出瓶颈归因。
- 为实时字幕链路定义明确的延迟预算，包括首字延迟、partial 更新延迟、final 完成延迟和前端渲染延迟。
- 优化实时链路的数据流，使 partial transcript 尽可能接近实时显示，而不是等待整句完成。
- 在页面上显示准确的链路状态，例如“桌面端未送音”“后端已接收但 provider 未返回 partial”“provider 已返回但前端渲染滞后”。
- 保持现有 API 兼容，允许在不改产品原型的前提下渐进替换链路内部实现。

**Non-Goals:**

- 不修改 LLM、Prompt、RAG、截图回答或资料库逻辑。
- 不更换实时 ASR 模型或引入新的语音供应商。
- 不新增用户可见的新页面、后台管理面板或复杂调试 UI。
- 不在本次变更中解决所有桌面音频驱动兼容问题；本次聚焦“链路慢”和“状态不透明”。

## Decisions

### Decision 1: Model the live transcript path as a timestamped staged pipeline

整条链路统一拆为以下阶段，并为每个音频 chunk / transcript event 附带同一条 trace：

1. desktop capture timestamp
2. desktop enqueue timestamp
3. desktop send timestamp
4. backend ingest received timestamp
5. backend worker dequeued timestamp
6. provider append timestamp
7. provider first partial timestamp
8. provider final timestamp
9. backend publish timestamp
10. frontend receive timestamp
11. frontend paint timestamp

只要这些时间点存在，就能稳定算出：

- capture → send
- send → ingest
- ingest → worker
- worker → provider partial
- provider partial → frontend receive
- frontend receive → paint
- capture → first visible partial
- capture → final visible transcript

Alternative considered: 只记录总耗时。缺点是知道“慢”，但不知道慢在哪一段，也无法指导优化顺序。

### Decision 2: Keep one long-lived stream per interview session and source kind

每个 `sessionId + sourceKind`（candidate / interviewer）维护一条独立的持久送音流和 provider 会话，不再允许按句子、按静音段或按 HTTP 请求重建整条实时链路。桌面端只发送增量 PCM chunk，后端 worker 只负责消费增量数据并推给同一条 provider session。

这样可以减少：

- 连接反复建立导致的首字延迟
- 重复上传同一段音频导致的 provider backlog
- 句子级切段引起的整句补刷

Alternative considered: 保持 request/response 风格，由后端或桌面端在检测到静音后再整段提交。缺点是很难实现低延迟 partial。

### Decision 3: Use producer-consumer queues with bounded buffering and drop policies

桌面端采集线程、桌面发送线程、后端 ingest、后端 provider worker 和前端渲染不再互相同步阻塞，而是通过有上限的队列传递数据。每个队列必须暴露：

- 当前长度
- 峰值长度
- 最近一次阻塞时长
- 丢弃次数 / 合并次数

当队列积压超过阈值时，系统优先丢弃过期 partial 或合并音频微块，而不是继续无限堆积，避免“最终都会显示，但已经晚了几十秒”。

Alternative considered: 全链路同步直传。缺点是一旦任一环节抖动，上游全部被拖慢。

### Decision 4: Treat partial transcript as a first-class low-latency product

前端实时对话区优先消费 provider partial transcript，并将 final transcript 视为对最近 partial 的确认与稳定化，而不是两套彼此独立的消息。系统必须支持：

- partial 覆盖最近一条同 source 的未完成字幕
- final 将该条字幕转为稳定记录
- 过期 partial 自动废弃
- 空白 partial / 噪声 partial 可抑制但必须计数

这样可以把体验从“几十秒后整段补出”改成“边说边出，最后再稳定收束”。

Alternative considered: 只在 final 到达时渲染消息。缺点是无法满足实时面试场景。

### Decision 5: Separate transcript transport from answer triggering

实时对话的显示链路和“是否触发快答 / 问题提取”的业务链路解耦。页面显示必须优先反映 partial/final 实时语音结果，而回答触发仍可以只基于 final 或更严格的问题检测条件。这样既能保留问答稳定性，也不牺牲字幕实时性。

Alternative considered: 只有当回答触发条件满足时才展示语音内容。缺点是会让对话区看起来像“没反应”。

### Decision 6: Add explicit latency budgets and anomaly reasons to runtime state

系统对实时链路定义明确预算：

- capture → backend ingest: 目标 ≤ 120ms
- ingest queue wait: 目标 ≤ 80ms
- provider first partial: 目标 ≤ 300ms
- partial publish → frontend receive: 目标 ≤ 120ms
- frontend receive → paint: 目标 ≤ 80ms
- capture → first visible partial: 目标 ≤ 600ms
- capture → final visible transcript: 目标 ≤ 1500ms

当任一预算连续超标时，runtime state 必须输出明确原因分类，例如：

- `desktop_no_audio_frames`
- `desktop_send_backlog`
- `backend_ingest_queue_delayed`
- `provider_partial_timeout`
- `provider_final_timeout`
- `frontend_subscription_stalled`
- `frontend_render_delayed`
- `stale_partial_dropped`

Alternative considered: 页面继续展示统一文案“尚未采集到有效音频”。缺点是用户和开发者都无法判断到底是没收音还是只是链路慢。

### Decision 7: Optimize with instrumentation first, then hot-path reductions

实施顺序必须先补全打点与基线，再做性能改造。原因是当前系统可能同时存在多个瓶颈，如果没有统一指标，任何优化都难以验证收益。打点完成后优先处理热路径：

1. 桌面端 chunk 颗粒度和发送节奏
2. 后端 ingest/worker 队列等待
3. provider session 复用和 partial 首字
4. 前端 partial 渲染和 reconciliation

Alternative considered: 直接先改某一层代码直到“看起来快一点”。缺点是容易局部变快，但整体仍慢。

## Risks / Trade-offs

- [Risk] 增加打点和 runtime counters 会带来额外 CPU / 内存开销 → Mitigation: 默认只保留最近窗口和聚合统计，不持久化原始事件流。
- [Risk] aggressive partial 更新会让前端渲染过于频繁 → Mitigation: 对同 source partial 做节流覆盖，按动画帧或最小时间窗合并更新。
- [Risk] bounded queue 丢弃过期数据可能引发少量字幕缺失 → Mitigation: 优先丢弃已过期 partial，不丢 final，并将丢弃原因纳入诊断。
- [Risk] provider 特定时间点和状态过多会削弱供应商可替换性 → Mitigation: 向上游暴露统一 latency / status schema，provider 特定字段封装在 adapter 里。
- [Risk] 多角色双通道链路下 candidate / interviewer 的节奏不同，可能导致某一路更敏感 → Mitigation: 指标和预算按 source 分开统计，避免两路互相掩盖问题。

## Migration Plan

1. 先补充端到端 tracing、runtime counters 和诊断状态，但不改变现有对外 API。
2. 在桌面端把采集、发送、屏幕捕捉状态统一接入诊断字段，明确当前是否真实送音。
3. 在后端加入分阶段队列指标、provider partial/final 延迟指标和 runtime anomaly 分类。
4. 在前端改为 partial-first 渲染与 final reconciliation，同时保留当前页面结构。
5. 对比优化前后的真实环境基线，确认首字和最终字幕延迟是否显著下降。
6. 若某项优化导致稳定性下降，可按 feature flag 回退到旧的 publish 策略，但保留新诊断指标继续定位。

## Open Questions

- 当前桌面端系统音频链路是否还有平台层采集限制，会不会把“采不到音”误判成“ASR 太慢”？
- 是否需要把诊断模式做成仅开发环境可见，避免将过多内部状态暴露给普通用户？
- 当前前端订阅采用的具体传输方式是否还存在轮询或批量刷新逻辑，需要在后续实现阶段一起核查？
