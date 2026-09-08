# CSDN 发布辅助信息

## 备选标题

1. 《Electron + Streaming ASR + RAG：实时 AI 面试助手完整工程链路》
2. 《从音频采集到 LLM 首字：实时 AI 系统的端到端延迟优化实战》
3. 《Streaming ASR 实战：长连接、Partial 回缩、VAD 与 Electron 性能踩坑》

## 摘要

一个 AI 面试助手如何从麦克风和系统音频出发，经过 Electron、WebSocket、Streaming ASR、RAG、LLM 与 SSE，把回答实时送到网页？本文结合真实生产实现，复盘 ASR 重复建连、Partial 回缩、句尾判断、音频补发风暴、AudioWorklet 崩溃和端到端 Trace 等工程问题。

## 推荐分类

- 人工智能
- 大模型应用开发

## 推荐标签

- AI面试助手
- Streaming ASR
- Electron
- WebSocket
- FastAPI
- RAG
- LLM
- SSE

## 配图

1. `01-full-architecture.png`：语音、回答和截图三条流程的完整架构。
2. `02-asr-state-machine.png`：持久 ASR 会话、Partial revision 和 Final 收口。
3. `03-electron-recovery.png`：AudioWorklet 与 WebSocket 重放风暴的修复前后。
4. `04-t0-t10-trace.png`：从语音活动到 React Render 的 Trace。

## 官网链接位置

只放在文章最后的产品说明段落。正文技术部分不插入产品链接。

## 性能数据证据

| 数据 | 证据路径 |
| --- | --- |
| 103 commits / 105 connections；90 commits / 89 connections | `docs/realtime-t0-t11-performance-baseline-2026-08-25.md` |
| 12 轮 Qwen append → Partial P50 437ms / P95 447ms | `docs/realtime-t0-t11-performance-baseline-2026-08-25.md` |
| Redis XADD → XREAD P95 1ms；XREAD → SSE P95 2ms | `docs/realtime-t0-t11-performance-baseline-2026-08-25.md` |
| Partial 发布额外等待 P50 61ms / P95 84ms，修复后约 2ms | `docs/realtime-t0-t11-performance-baseline-2026-08-25.md` |
| Server VAD 8 秒未完成；manual 样本停止说话到 Final 约 797ms | `docs/realtime-t0-t11-performance-baseline-2026-08-25.md`、`docs/companion-answer-performance-report-2026-08-20.md` |
| 62 utterances 复用预热连接；115 utterances / 2 System connections | `docs/realtime-system-audio-e2e-validation-2026-08-25.md` |
| 128 samples、375 次/秒、13万～26.6万 VM regions、SIGTRAP | `docs/releases/release-1.2.14.md` |
| 1024 samples、43～47 次/秒、传输减少 87.5% | `docs/releases/release-1.2.14.md` |
| 1634 唯一帧触发 1253984 次写入，约 20 分钟 4.95GB | `docs/releases/release-1.2.14.md` |
| 2.25MB 截图压到约 91.5KB，压缩约 0.14 秒 | `docs/companion-answer-performance-report-2026-08-20.md` |
| 截图正常受控样本：视觉约 13.4～13.6 秒，OSS 约 3 秒 | `docs/companion-answer-performance-report-2026-08-20.md` |
| 最近 24 小时截图 6/6 成功，视觉平均 10.23 秒、P95 12.09 秒 | `docs/companion-answer-performance-report-2026-08-20.md` |

## 关键架构事实证据

| 架构事实 | 代码或文档路径 |
| --- | --- |
| Electron 双路采集、PCM16、100ms 增量和有界缓存 | `apps/desktop/src/renderer/audio/realtime-publisher.ts`、`apps/desktop/src/renderer/audio/pcm-capture.worklet.js`、`docs/realtime-interview-runtime.md` |
| WebSocket v2、双逻辑通道、ACK、Resume 和补发 | `apps/desktop/src/renderer/audio/multiplexed-realtime-transport.ts`、`apps/desktop/src/renderer/audio/realtime-reliability.ts`、`apps/backend/app/modules/realtime_speech.py` |
| Streaming ASR 长连接与 Partial receiver | `apps/backend/app/services/dashscope_realtime_asr_gateway.py` |
| Partial/Final/revision 与稳定文本归并 | `apps/backend/app/services/realtime_speech_service.py`、`apps/web/src/backend-adapter.ts` |
| VAD、silence tail 和 commit | `apps/desktop/src/renderer/audio/realtime-publisher.ts`、`docs/commercial-realtime-finalization-beta.md` |
| Redis Event Stream 与 Session SSE | `apps/backend/app/services/realtime_speech_repository.py`、`apps/backend/app/modules/realtime_speech.py` |
| Resume/JD 固定上下文与 Knowledge RAG | `docs/material-grounding-behavior.md`、`apps/backend/app/services/chat_service.py` |
| Embedding、Retrieval 和 Rerank | `apps/backend/app/services/knowledge_retrieval.py` |
| pgvector 目标表结构与当前 JSONB 运行时差距 | `apps/backend/migrations/versions/0003_commercial_material_rag_persistence.sql`、`apps/backend/app/services/postgres_material_persistence.py` |
| LLM 流式回答与 Answer SSE | `apps/backend/app/services/chat_service.py`、`apps/backend/app/modules/live_answer.py` |
| Screenshot Task、桌面截图、Vision 和 SSE | `apps/backend/app/services/screenshot_answer_service.py`、`apps/desktop/src/main/screenshot-shortcut.ts`、`docs/realtime-interview-runtime.md` |
| T0–T10 字段定义与统计口径 | `docs/realtime-t0-t11-performance-baseline-2026-08-25.md` |
| 面试复盘和导出 | `apps/backend/app/modules/session.py`、`apps/web/src/interview-review-export.ts` |
