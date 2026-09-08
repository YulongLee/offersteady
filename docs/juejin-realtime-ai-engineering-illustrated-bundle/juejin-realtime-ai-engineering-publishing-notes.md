# 掘金发布辅助信息

## 备选标题

1. 《LLM 首字只要 500ms，为什么实时 AI 还是很慢？》
2. 《从 Electron 崩溃到 ASR 重连：我做实时 AI 踩过的坑》
3. 《实时 AI 性能优化实战：别再只盯着模型延迟》

## 摘要

做实时 AI 面试助手后，我发现 LLM 反而不是最难的部分。本文复盘 AudioWorklet 高频分配、ASR 重复建连、Partial 回缩、Endpoint 取舍、音频补发风暴和端到端 Trace 等真实问题，说明为什么单组件指标漂亮，用户仍可能觉得慢。

## 推荐分类

- 人工智能
- 前端

## 推荐标签

- 实时AI
- Electron
- Streaming ASR
- WebSocket
- FastAPI
- RAG
- LLM
- 性能优化

## 三张正文配图

1. `01-latency-iceberg.png`：LLM 首 Token 与用户感知延迟的关系。
2. `02-three-pitfalls.png`：AudioWorklet 分配、ASR 重复建连和 Partial 回缩。
3. `03-trace-before-optimize.png`：端到端 Trace 及真实延迟数据。

## 推荐封面文案

主标题：`实时 AI 最难的不是 LLM`

副标题：`一次 Electron、Streaming ASR 与端到端延迟的踩坑复盘`

## 性能数据与证据

| 文中数据 | 证据路径 | 状态 |
| --- | --- | --- |
| 128 samples 约每 2.67ms 一次；每声道约 375 次/秒 | `docs/releases/release-1.2.14.md` | 历史问题 |
| 5 份 SIGTRAP；约 13万～26.6万 VM regions | `docs/releases/release-1.2.14.md` | 历史问题 |
| 1024 samples；43～47 次/秒；30 分钟传输减少 87.5% | `docs/releases/release-1.2.14.md` | 当前修复 |
| Mic 103 commits / 105 connections；System 90 / 89 | `docs/realtime-t0-t11-performance-baseline-2026-08-25.md` | 历史线上问题 |
| 62 个 utterances 复用预热连接；测试窗口 0 新建、0 重连 | `docs/realtime-system-audio-e2e-validation-2026-08-25.md` | 修复验证 |
| manual 停止说话到 Final 约 797ms；Server VAD 8 秒未完成 | `docs/realtime-t0-t11-performance-baseline-2026-08-25.md`、`docs/companion-answer-performance-report-2026-08-20.md` | 对比样本 |
| 1634 唯一帧触发 1253984 次写入；约 20 分钟 4.95GB | `docs/releases/release-1.2.14.md` | 历史故障 |
| Append → Partial P50/P95 437/447ms | `docs/realtime-t0-t11-performance-baseline-2026-08-25.md` | 12 轮热路径测试 |
| XADD → XREAD P95 1ms；XREAD → SSE P95 2ms | `docs/realtime-t0-t11-performance-baseline-2026-08-25.md` | 12 轮热路径测试 |
| 旧线上 Speech Start → Published Partial：Mic P50/P95 1679/2689ms；System 2005/6352ms | `docs/realtime-t0-t11-performance-baseline-2026-08-25.md` | 历史线上样本，不是当前 SLA |
| Partial 发布额外等待 P50/P95 61/84ms，修复后约 2ms | `docs/realtime-t0-t11-performance-baseline-2026-08-25.md` | 已定位并修复 |

## 关键事实证据

| 技术事实 | 代码或文档路径 |
| --- | --- |
| Electron 双路采集、PCM16、100ms Frame、VAD tail | `apps/desktop/src/renderer/audio/realtime-publisher.ts`、`apps/desktop/src/renderer/audio/pcm-capture.worklet.js` |
| WebSocket 双通道、ACK、Resume、重连 | `apps/desktop/src/renderer/audio/multiplexed-realtime-transport.ts`、`apps/desktop/src/renderer/audio/realtime-reliability.ts` |
| Streaming ASR 持久连接和 Partial receiver | `apps/backend/app/services/dashscope_realtime_asr_gateway.py` |
| Partial / Final / revision / terminal state | `apps/backend/app/services/realtime_speech_service.py`、`apps/web/src/backend-adapter.ts` |
| Redis Event Stream 与 SSE | `apps/backend/app/services/redis_realtime_speech_repository.py`、`apps/backend/app/modules/realtime_speech.py` |
| Resume/JD 固定上下文、Knowledge Retrieval | `docs/material-grounding-behavior.md`、`apps/backend/app/services/chat_service.py` |
| Query Embedding、过滤、Retrieval、Rerank | `apps/backend/app/services/knowledge_retrieval.py` |
| pgvector 目标结构与 JSONB 运行时差距 | `apps/backend/migrations/versions/0003_commercial_material_rag_persistence.sql`、`apps/backend/app/services/postgres_material_persistence.py` |
| Screenshot Answer 与 Vision Model | `apps/backend/app/services/screenshot_answer_service.py`、`docs/realtime-interview-runtime.md` |
| T0–T10 的真实定义与样本边界 | `docs/realtime-t0-t11-performance-baseline-2026-08-25.md` |

## 状态边界

### 当前生产实现

- Electron 区分麦克风和系统音频，输出 16kHz 单声道 PCM16。
- 单条认证 WebSocket 承载两个逻辑通道，并使用有界 ACK、Resume 与补发。
- 每个面试会话、每个来源复用持久 ASR Session。
- 本地 VAD/silence 与 manual commit 收口，前后端按 revision 单调归并。
- Resume/JD 固定上下文，Knowledge 经过 Embedding、Retrieval 与 Rerank。
- 回答通过 SSE 流式发送；截图走独立 Vision 链路。

### 历史问题

- 每个 128 sample 新建 `Float32Array` 导致高频跨线程转移和 Renderer SIGTRAP。
- ASR 连接复用错误绑定 `sourceGeneration`，造成几乎每句话重新建连。
- 更高 revision 的短 Partial 导致字幕回缩。
- sequence gap 触发全队列重放，形成 WebSocket 发送风暴。
- Partial 到达接收线程后等待下一帧 append 才发布。

### 未来优化方向

- 在取得充分实机样本后继续优化语义 Endpoint；当前不能写成已上线。
- 让运行时检索真正使用 pgvector 数据库向量算子。
- 继续补齐前台浏览器端完整 Trace 样本，建立可靠的端到端 P50/P95。
- 优化 Screenshot Answer 的视觉模型耗时与对象写入长尾。
