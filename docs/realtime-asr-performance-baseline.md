# Realtime ASR Performance Baseline

这个文档记录 `optimize-realtime-asr-pipeline` 变更开始前后的本地可重复基线，方便后续优化对比。

## 基线脚本

在仓库根目录运行：

```bash
PYTHONPATH=apps/backend python apps/backend/scripts/benchmark_realtime_asr_pipeline.py
```

脚本会：

- 使用本地 FastAPI `TestClient`
- 创建一个 synthetic realtime session
- 发送 5 条麦克风音频帧
- 记录 transport roundtrip 与 runtime performance 字段
- 输出到 [artifacts/realtime-asr-benchmarks/baseline.json](/Users/liyulong/liyulong/1_projects/offersteady/artifacts/realtime-asr-benchmarks/baseline.json)

## 2026-07-03 基线结果

- sampleCount: 5
- transport roundtrip avg: 0.32 ms
- transport roundtrip p50: 0.31 ms
- transport roundtrip p95: 0.39 ms
- transport roundtrip max: 0.39 ms
- microphone counters:
  - queueDepth: 0
  - droppedPartialUpdates: 0
  - connectionRecreations: 0
  - emptyResultsSuppressed: 0
  - phantomResultsSuppressed: 0
  - chunksProduced: 5
  - chunksUploaded: 5
  - serializedAudioBytes: 186

## 说明

- 当前基线脚本使用 synthetic ASR 路径，主要用于验证本地 pipeline 架构与埋点是否完整，不代表真实 DashScope 网络延迟。
- 真实线上联调时，应在同样的 runtime 字段上继续采集：
  - `captureToIngestMs`
  - `queueWaitMs`
  - `asrTtftMs`
  - `finalTranscriptMs`
  - `backendPushMs`
  - `frontendRenderMs`
- 后续进入 2.x / 3.x 任务后，这个基线会作为“同步转写旧链路”的对照样本。

## 2026-08-24 商业化终止候选（本地 synthetic）

运行：

```bash
PYTHONPATH=apps/backend OFFERSTEADY_BENCHMARK_LABEL=commercial-finalization-candidate \
  python apps/backend/scripts/benchmark_realtime_asr_pipeline.py
```

- transport acknowledgement avg: 0.77 ms
- transport acknowledgement p95: 1.34 ms
- queue depth: 0
- terminal loss: 0 in this synthetic run
- stop-to-terminal: 0 ms（synthetic adapter 同步返回）
- aggregate snapshot request reduction: 75%
- concurrency 10 aggregate snapshot p95/p99: 15.72 ms / 15.72 ms，0 errors

这个结果只证明本地协议、队列和终态归并没有引入明显控制面开销。它不包含公网、DashScope、设备驱动和浏览器渲染延迟，因此不能单独作为正式商业发布依据。完整门禁和隔离 Beta 步骤见 [commercial-realtime-finalization-beta.md](commercial-realtime-finalization-beta.md)。
