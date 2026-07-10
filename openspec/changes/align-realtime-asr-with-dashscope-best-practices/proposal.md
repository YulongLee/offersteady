## Why

当前项目的实时语音体验仍然不够可用：首字慢、字幕抖动、静音误触发、长时间无结果后又突然整段出字。问题不只是“链路不够快”，还包括 ASR 接入方式没有按阿里百炼实时语音模型的官方推荐模式去使用，导致连接、送音、VAD/Manual 断句、Partial/Final 处理和异常恢复都没有发挥出模型应有的实时性。

现在需要把 Realtime ASR 从“兼容可用”升级为“按 DashScope 最优方式接入”，让面试场景中的语音识别延迟、稳定性和连续性达到真正可联调、可体验、可继续优化的状态。

## What Changes

- 重新定义 OfferSteady 的 DashScope Realtime ASR 调用方式，按阿里百炼官方推荐实践梳理业务空间专属域名、长连接建立、`session.created` / `session.update`、音频 append / commit、VAD / Manual 模式切换、Partial / Final transcript 消费和关闭流程。
- 将当前后端和桌面端中“伪实时”“同步阻塞”“累计片段重复发送”“非最佳连接复用”的部分替换为面向 DashScope Realtime ASR 的推荐集成路径。
- 增加 provider-aware 的实时语音运行策略，包括音频 chunk 粒度、会话保活、错误恢复、静音门控、Partial 频率控制、VAD 参数治理和 source 级连接治理。
- 增加围绕 DashScope Realtime ASR 的链路观测与验收指标，明确 TTFT、Partial 连续性、Final 完成时间、连接重建率和误触发率。
- 保持现有产品原型、面试流程、页面布局和上层问答逻辑不变，只调整实时语音识别集成边界和内部实现。

## Capabilities

### New Capabilities
- `dashscope-realtime-asr-best-practice-integration`: 定义 OfferSteady 如何按照阿里百炼实时语音模型的最佳实践建立、维护和关闭 ASR 会话，并处理 partial / final 识别结果。
- `realtime-asr-provider-observability`: 定义围绕实时语音供应商调用的性能指标、错误分类、连接状态与验收基线。

### Modified Capabilities
- `resizable-live-interview-workspace`: 实时对话区的字幕更新要求调整为优先反映 DashScope partial / final 转写结果，减少长时间空白和突发整段刷新。

## Impact

- Affected desktop areas: `apps/desktop` 的麦克风 / 系统音频采集后发送策略、chunk 组织、会话保活和本地 source 状态反馈。
- Affected backend areas: `apps/backend` 的 realtime-speech service、DashScope ASR gateway、session/source worker、provider error handling 和 runtime telemetry。
- Affected web areas: `apps/web` 的实时对话订阅与 partial / final 字幕刷新逻辑。
- Affected protocol areas: `packages/protocol` 中实时 transcript、provider telemetry 和 runtime diagnostics 字段。
- Privacy impact: 不新增原始音频长期保存；新增 provider 观测只记录延迟、状态、错误码和聚合统计，不记录音频正文或敏感原文。
