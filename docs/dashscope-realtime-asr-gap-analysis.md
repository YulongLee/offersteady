# DashScope Realtime ASR Gap Analysis

更新时间：2026-07-04

本文件记录 `align-realtime-asr-with-dashscope-best-practices` 在实施前对当前实现与阿里百炼官方推荐调用方式之间的主要偏差。

## 当前实现的主要偏差

1. 会话粒度不对

- 旧实现按 `segment_id` 建立 provider session
- 官方推荐更适合按持续 source 会话复用长连接
- 结果：重复握手、连接抖动、TTFT 波动更大

2. provider-ready 判断不严格

- 旧实现虽然会先读第一条事件，但没有把 `session.created` 作为明确的 ready gating
- 结果：`session.update` 发送时点不够明确，provider 初始化异常不易诊断

3. 默认没有 provider-level VAD/Manual 策略

- 旧实现把 `turn_detection` 固定为 `None`
- 结果：系统无法区分“本地静音阈值提交”与“provider VAD 断句”两种模式，也无法记录回退行为

4. 仍保留伪实时 roundtrip 模式

- 旧实现 `process_audio_frame() -> gateway.transcribe() -> 返回`
- 结果：provider 延迟直接阻塞 ingest 路径，无法充分发挥长连接 realtime 模型优势

5. segment final 后立即销毁 provider session

- 旧实现 final 后直接关闭 segment 级 provider session
- 结果：同一路来源无法持续复用会话，不符合官方推荐的实时流式模式

6. provider 事件分类不够细

- 旧实现没有显式诊断 `session.created` 缺失、blank partial、completed 缺失等问题
- 结果：排查“为什么没字 / 为什么乱出字”时缺少足够的 provider-aware 证据

## 本轮修正目标

- 优先使用业务空间专属实时域名
- 等待 `session.created` 后再发送 `session.update`
- provider session 改为 source-scoped 持久连接
- segment 内只 append 增量音频，句末再 commit
- 记录 blank partial、completed missing、session created missing 等 provider 级诊断

## 后续仍待完成

- 将 ingest 从同步转写彻底改为后台 source worker
- 把 provider VAD / Manual 模式显式暴露到 runtime API
- 让桌面端送音完全对齐新的 provider worker 期望
- 让前端实时对话优先消费 partial 状态而不是等待整段稳定结果
