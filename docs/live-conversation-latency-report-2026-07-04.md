# Live Conversation Latency Report

更新时间：2026-07-04

本报告记录「面试稳」实时对话链路的分段模拟测试结果，目标是回答两个问题：

1. 延迟到底出在哪一段？
2. 目前离“接近实时字幕”还差多少？

本次测试不修改产品原型，只分析现有链路：

桌面采集 / 音频分段  
→ 桌面发送到后端  
→ 后端入队与转写工作流  
→ DashScope Realtime ASR  
→ 转录发布  
→ 网页实时对话显示

## 测试方法

本次使用两类测试：

1. 本地模拟链路测试
   - 脚本：`apps/backend/scripts/benchmark_realtime_asr_pipeline.py`
   - 目的：排除本地 HTTP / WS / 队列 / 事件发布是否本身很慢

2. 真实 Provider 链路测试
   - 脚本：`apps/backend/scripts/profile_live_conversation_latency.py`
   - 目的：验证当前 `.env` 配置下，真实 DashScope Realtime ASR 的端到端表现
   - 模式：
     - `manual`
     - `server_vad`

测试输入文本：

`你好，我正在测试面试稳的实时语音识别。`

脚本会把语音按 3200-byte PCM 小块、每 100ms 节奏送入后端，模拟真实连续说话。

## 分段结果

### 1. 本地模拟链路

结果：

- transport roundtrip avg：`0.34ms`
- transport roundtrip p95：`0.43ms`
- queue wait：`0ms`
- publish：`0ms`

结论：

- 本地模拟链路非常快
- 前后端基础传输框架不是 30 秒级延迟的根因
- 也说明“不是 FastAPI 路由本身慢”

### 2. 真实 Realtime ASR - manual 模式

结果：

- 音频时长：`3460ms`
- 首次 partial 可见：`2529ms`
- 最终 final 可见：`5175ms`
- `captureToSendMs`：`1065ms`
- `sendToIngestMs`：`1ms`
- `queueWaitMs`：`0ms`
- `asrTtftMs`：`677ms`
- `finalTranscriptMs`：`707ms`
- `captureToPublishMs`：`1773ms`
- dominant bottleneck：`microphone:desktop_send_backlog`

结论：

- 后端收到包以后并不慢
- provider 首字延迟约 `677ms`，不算极端，但也不够快
- 更大的问题是桌面发送侧已经累计了约 `1s` backlog
- 这会把“用户已经说完的音频”延后送进 provider

### 3. 真实 Realtime ASR - server_vad 模式

结果：

- 音频时长：`3460ms`
- 首次 partial 可见：`2794ms`
- 最终 final 可见：`5499ms`
- `captureToSendMs`：`1081ms`
- `sendToIngestMs`：`1ms`
- `queueWaitMs`：`0ms`
- `backendPushMs`：`980ms`
- `captureToPublishMs`：`2062ms`
- dominant bottleneck：`microphone:desktop_send_backlog`
- anomaly：
  - `microphone:desktop_send_backlog`
  - `microphone:publish_lag`

结论：

- 在当前实现里，`server_vad` 没有比 `manual` 更快
- VAD 模式下首个可见字幕更晚，最终结果也更晚
- 当前代码路径下，VAD 不是主要提速手段

## 当前瓶颈判断

### 结论一：不是前端渲染慢

证据：

- 本次链路里，字幕一旦被 publish，网页可以很快显示
- 当前 runtime 中没有看到前端渲染引起的秒级延迟

### 结论二：不是后端 HTTP 接口慢

证据：

- `sendToIngestMs ≈ 1ms`
- 本地 transport roundtrip `p95 < 1ms`

### 结论三：当前最主要的瓶颈是“发送侧 backlog”

证据：

- `captureToSendMs` 长时间稳定在 `~1s`
- dominant bottleneck 连续被判定为 `microphone:desktop_send_backlog`

这说明：

- 音频在“采集完成”后，没有被足够快地送到后端
- 也就是用户已经说出来的声音，在进入 ASR 前就已经排队了

### 结论四：Provider partial/final 返回仍然偏慢，但不是唯一问题

证据：

- manual 下 `asrTtftMs ≈ 677ms`
- 首次可见 partial 却是 `2529ms`

这说明：

- provider 首字不是完全不可接受
- 但真正“页面看到字”的时间远晚于 provider 首字
- 原因是前面已经被 backlog 拖慢

## 为什么你体感会特别慢

用户体感看到的是：

“我一句话说完后，很久页面才出字”

而从链路上看，它实际是三段时间叠加：

1. 说话后，桌面端没有立刻把增量音频送出去
2. provider 返回 partial/final 不是 100~300ms 级
3. 我们当前还是以“句段级可见”为主，而不是更 aggressive 的 partial 呈现

所以最终体感会明显偏慢。

## 当前能确认的优化收益

本轮已经完成的优化：

1. 去掉累计重发
   - 桌面端与后端都不再重复发送整个累计音频
   - 避免 utterance 越长越慢

2. provider session 改为 source 级复用
   - 不再每段新建连接
   - 降低握手和抖动

3. 增加 trace id 和分段时延指标
   - 可以定位到底卡在 capture / send / ingest / provider / publish 哪一段

4. 降低部分轮询等待
   - 缩短 partial / final drain deadline

这些优化已经把“结构性错误”修掉了，但还没把体感压到真正实时。

## 2026-07-04 传输层改造补充

在本报告基础上，新增了一条桌面伴随程序专用的长连接送音通道：

- 桌面端入口：`apps/desktop/src/renderer/audio/realtime-publisher.ts`
- 后端入口：`/api/v1/realtime-speech/ingest-ws`

新链路行为：

- 每个 source 建立一条持久 WebSocket
- 音频 chunk 直接连续发送
- 后端收到后立即 `ack`
- 转写继续在后台异步执行

本地传输层对比（同一后端进程内测）：

- HTTP frame ingest avg：`1.281ms`
- HTTP frame ingest p95：`1.501ms`
- WebSocket ingest avg：`0.435ms`
- WebSocket ingest p95：`0.631ms`

结论：

- 单次入站开销约下降到原来的三分之一
- 这一步能明显减少桌面端逐帧发包调度造成的 backlog
- 但它还不是最终结论，仍需结合真实桌面伴随程序 + 真实 DashScope ASR 再跑一次端到端基线

## 下一步最值得做的优化

按收益排序：

### P0：把桌面端发包从逐帧 HTTP POST 改成持久化实时流

这是当前最关键的点。

建议：

- 桌面伴随程序到后端改成长连接 websocket
- 按 source 持续 append PCM chunk
- 避免每 100ms 一次 HTTP 序列化、请求调度、事件循环唤醒

预期收益：

- `captureToSendMs` 从 `~1000ms` 压到 `100~250ms`

### P0：前端优先显示 partial，不等整句稳定

建议：

- 实时对话窗口直接显示 partial
- final 到来时再原位替换
- 避免“一整句突然刷出来”

预期收益：

- 用户体感延迟明显下降

### P1：桌面端采集线程与发送线程彻底解耦

建议：

- Producer / Consumer
- ring buffer 或 bounded async queue
- 采集只负责写入
- 发送只负责 flush

预期收益：

- 减少采集受网络抖动影响

### P1：进一步对齐 DashScope 官方最佳实践

建议：

- 更严格地按官方 realtime 会话模式维护 session.update / append / commit
- 优先观察 partial 事件，而不是靠后置拼接推断

预期收益：

- 降低 provider partial 抖动

## 当前结论

这次分段模拟测试后，可以比较明确地说：

1. 问题不在前端页面本身
2. 问题不在 FastAPI 基础路由
3. 当前最大的延迟来自桌面端发送 backlog
4. DashScope realtime 返回速度也还不够理想，但它不是唯一瓶颈
5. 如果不把桌面端到后端改成真正的持续流式传输，很难做到你要的“边说边出字”

## 相关产物

- 原始基线：`artifacts/realtime-asr-benchmarks/baseline.json`
- 本次真实链路诊断：`artifacts/realtime-asr-benchmarks/live-conversation-latency-profile.json`
- 诊断脚本：`apps/backend/scripts/profile_live_conversation_latency.py`
- 历史差距分析：`docs/dashscope-realtime-asr-gap-analysis.md`
