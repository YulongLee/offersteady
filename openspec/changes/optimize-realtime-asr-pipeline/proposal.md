## Why

当前面试实时语音链路已经接入 `qwen3-asr-flash-realtime`，但真实使用中仍存在明显延迟：首字返回慢、Partial Transcript 不连续、Final Transcript 不稳定，且静音或环境噪声会错误触发字幕更新。这说明瓶颈主要不在模型本身，而在 Audio Capture、Buffer、Streaming、ASR Client、后端编排和前端消费这一整条实时链路的架构与实现方式。

现在需要把“能跑通”升级为“可用于真实面试”的低延迟实时系统方案，优先解决首字延迟、流式稳定性、误触发和链路阻塞问题，并在不修改现有产品原型和公开 API 的前提下，重新定义整个 Realtime ASR Pipeline 的目标架构与优化路径。

## What Changes

- 重新设计桌面伴随助手到网页实时对话区之间的低延迟语音处理链路，按“性能优先”原则优化 Audio Capture、Buffer、PCM Streaming、ASR Client、FastAPI 编排和前端字幕消费。
- 引入面向低延迟的 Pipeline 架构，包括常驻长连接、增量音频发送、Producer-Consumer 队列、流式 Partial Transcript 与 Final Transcript 分离处理。
- 将当前可能存在的同步等待、重复序列化、重复内存拷贝、频繁创建 WebSocket / 对象、过大 Chunk 和误触发静音识别等问题纳入统一性能分析与治理范围。
- 增加实时语音链路的性能观测与诊断能力，覆盖 TTFT、Partial/Final Latency、Chunk 排队、ASR 往返耗时、UI 渲染滞后和异常静音触发。
- 优化快答的问题选择：没有手动输入时，按当前轮次自动整理面试官最近的完整问题和最新未定稿片段，再提交既有回答模型。
- 保持现有 Web 产品原型、外部 API 形态、ASR 模型、LLM、Prompt 和 RAG 逻辑不变；快答仅增加确定性的对话问题整理，不改变回答策略。

## Capabilities

### New Capabilities
- `low-latency-realtime-asr-pipeline`: 定义从桌面采集、音频缓冲、实时流式传输、ASR 长连接到网页字幕展示的低延迟实时语音处理能力。
- `realtime-asr-performance-observability`: 定义实时语音链路的性能指标、阶段化诊断、压测方法和回归验收标准。

### Modified Capabilities
- `resizable-live-interview-workspace`: 实时对话区的行为从“按段展示已落库转录”升级为“优先消费流式 Partial Transcript / Final Transcript，并抑制静音误触发与无效字幕刷新”。

## Impact

- Affected desktop areas: `apps/desktop` 的麦克风 / 系统音频采集、Audio Buffer、Chunk 生成、队列调度、ASR 长连接客户端和本地状态监测。
- Affected backend areas: `apps/backend` 的 realtime-speech service、ASR gateway、session 内流式状态机、性能指标采集和前端推送通道。
- Affected web areas: `apps/web` 的实时对话订阅、Partial / Final 字幕合并、增量渲染和 UI 更新节流。
- Affected protocol areas: `packages/protocol` 中实时音频帧、阶段事件、性能指标和流式字幕契约。
- Privacy impact: 不新增原始音频长期保存；新增性能观测必须只记录耗时、状态和统计指标，不记录音频正文或敏感原文。
