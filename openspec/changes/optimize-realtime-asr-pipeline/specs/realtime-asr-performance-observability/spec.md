## ADDED Requirements

### Requirement: Realtime ASR pipeline SHALL expose stage-level latency metrics
系统 MUST 为实时语音链路暴露分阶段性能指标，至少覆盖音频采集、Chunk 入队、后端接收、ASR 首字返回、Final Transcript 完成、前端字幕渲染六个阶段。指标 MUST 支持按 session、source 和阶段聚合，以定位延迟主要来源。

#### Scenario: Engineer inspects a slow realtime session
- **WHEN** 某场面试出现实时字幕明显延迟
- **THEN** 系统能够提供该 session 各阶段耗时指标，以区分是采集、传输、ASR 还是网页渲染导致

#### Scenario: Source-specific latency differs
- **WHEN** 麦克风和系统音频的延迟表现不同
- **THEN** 指标按 source 分开展示，而不是只给出整场面试的单一平均值

### Requirement: Realtime diagnostics SHALL classify blocking and backpressure conditions
系统 MUST 能识别并报告实时链路中的阻塞、排队、背压和连接抖动问题，包括同步等待、Chunk 堆积、队列覆盖、连接重建和前端消费滞后。诊断输出 MUST 使用阶段化错误码或状态，而不是仅显示通用“识别慢”。

#### Scenario: Backend queue becomes saturated
- **WHEN** 后端某 source 的实时队列积压超过设计阈值
- **THEN** 系统输出背压或队列积压诊断，并标记对应阶段而不是继续静默堆积

#### Scenario: ASR connection is recreated too frequently
- **WHEN** 某 source 在短时间内重复创建实时 ASR 连接
- **THEN** 系统输出连接重建异常诊断，帮助定位长连接复用失败

### Requirement: Performance verification SHALL include TTFT and final-latency acceptance tests
系统 MUST 提供可重复执行的性能验证方法，覆盖首字延迟（TTFT）、Partial Transcript 更新间隔、Final Transcript 耗时、CPU 使用、内存分配和 GC 抖动。验收结果 MUST 支持与优化前基线比较。

#### Scenario: Team validates the optimized pipeline before rollout
- **WHEN** 工程团队对优化后的实时语音链路执行验收
- **THEN** 系统输出可比较的 TTFT、Final Latency、CPU、内存和 GC 指标，而不是只依赖主观体验

#### Scenario: Regression appears after a pipeline change
- **WHEN** 某次优化后首字延迟或 Final Transcript 耗时回升
- **THEN** 性能验证流程能够检测出相对基线的退化并阻止静默回归
