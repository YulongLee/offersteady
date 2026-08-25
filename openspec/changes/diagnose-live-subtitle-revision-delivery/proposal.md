## Why

真实面试已经证明持久 Qwen 连接、桌面音频传输、ACK、队列和 Redis 主链路没有持续积压，但用户仍会看到字幕长时间不更新后突然整段出现。当前观测只能定位首个 Partial，无法证明每个 Qwen revision 是否逐级经过 Redis、SSE、Browser State 和 React Paint，因此不能在证据不足时安全修复。

## What Changes

- 为每个真实 `transcript.partial` revision 增加端到端只读 Trace，使用同一 `session_id + utterance_id + segment_id + revision + event_id` 关联 Qwen、事件创建、Redis、SSE、Browser、Store、React commit 和 paint。
- 增加可显式开启的临时 Web Debug Overlay，显示当前 revision、各阶段 age、revision 计数和页面可见性；默认关闭，不进入普通用户体验。
- 增加有界的 revision 统计与诊断报告，比较 Qwen、Redis、SSE、Browser 和 Render 计数，计算各阶段 P50/P95/P99/MAX、连续 revision gap 以及最慢样本。
- 通过真实 Electron System Audio、真实 Qwen、真实 Redis、真实 SSE 和可见 Web 页面采集至少 50 个 utterance；不可见页面样本单独标记且不进入正式分位数。
- 本变更只诊断，不修改 Qwen 生命周期、音频 ACK/重传、Ring Buffer、RAG、LLM、快答、Partial 合并策略、SSE 协议语义或 React 更新策略。

## Capabilities

### New Capabilities

- `live-subtitle-delivery-diagnostics`: 覆盖 revision 级端到端 Trace、可见性标记、临时 Overlay、连续性统计和真实链路诊断验收。

### Modified Capabilities

None.

## Impact

- 影响 Backend 的实时 ASR Partial 发布与 Redis/SSE 观测点、Web 的 SSE 解析/状态合并/字幕组件观测点、诊断配置与测试脚本。
- Trace 只记录标识符、revision、文本长度和时间戳；不新增音频、完整字幕或个人资料持久化。
- 诊断必须显式启用、限量采样并可快速关闭；普通用户路径默认不显示 Overlay，业务事件内容与顺序保持不变。
