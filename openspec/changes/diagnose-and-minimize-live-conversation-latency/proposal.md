## Why

当前面试实时对话体验仍然明显偏慢，用户说一句话后要等待数十秒页面才出现转写结果，这已经超出“实时面试辅助”可接受的范围。现在需要做的不只是继续调参数，而是把桌面采集、上传、后端编排、ASR、前端推送和页面渲染整条链路逐段量化，定位真实瓶颈并把端到端延迟压到接近实时。

## What Changes

- 建立面试实时对话的端到端延迟诊断能力，覆盖桌面采集、音频发送、后端排队、ASR、事件推送和前端渲染。
- 为实时对话链路定义明确的分段延迟预算、瓶颈判定规则和降级策略，避免“有字但很晚”“突然整句补出”“无意义噪声也出字”等问题。
- 增加全链路 profiling、采样日志和本地 / 真实环境对比基线，能够明确回答当前主要延迟来自哪一段。
- 在不改变产品原型和业务流程的前提下，持续优化实时对话链路，使说话与页面显示之间的体感延迟显著下降。

## Capabilities

### New Capabilities
- `end-to-end-live-conversation-latency-diagnostics`: 定义桌面端到网页实时对话区的全链路延迟诊断、分段指标和瓶颈归因能力。
- `latency-budgeted-live-transcript-pipeline`: 定义实时字幕链路的延迟预算、分段目标、超时判定和针对瓶颈的优化策略。

### Modified Capabilities
- `resizable-live-interview-workspace`: 实时对话区的要求调整为优先展示低延迟 partial / final 字幕，并在延迟异常时给出准确的链路状态提示。

## Impact

- Affected desktop areas: `apps/desktop` 的采样节奏、音频缓冲、发送频率、source health 和调试指标上报。
- Affected backend areas: `apps/backend` 的 realtime-speech ingest、worker 队列、ASR gateway、事件推送和链路 profiling。
- Affected web areas: `apps/web` 的 SSE 订阅、partial/final reconciliation、render latency 记录和运行状态提示。
- Affected protocol areas: `packages/protocol` 中实时转写事件、延迟指标、链路状态和诊断契约。
- Privacy impact: 新增的诊断和 profiling 只记录时间戳、计数、状态和错误分类，不记录原始音频正文或敏感对话文本。
