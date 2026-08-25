## Context

当前 Backend 已在 Qwen Partial、Redis XADD/XREAD、SSE yield、Browser receive/state update 和父级字幕组件 render 处记录部分时间戳，并通过 `performance-ack` 回传无内容指标。但现有 Trace 以首个 Partial 和最新 transcript 为主，不能逐 revision 对账；Web 还会在一个 `requestAnimationFrame` 内合并 SSE 更新，`ProgressiveTranscriptText` 使用独立 32ms 可见文本状态，因此父级 render 并不等同于用户真正看到该 revision。当前配置已经声明 `text/event-stream`、`X-Accel-Buffering: no`，Nginx 也关闭了 buffering，但仍需真实 timestamp 而不是配置推断。

## Goals / Non-Goals

**Goals:**

- 对每个 System Audio Partial revision 建立 R0–R13 的端到端关联和计数。
- 区分 Qwen 是否产生 revision、SSE 是否逐条交付、Browser 是否完整解析、Store 是否合并、React 是否 commit、实际可见文本是否 paint。
- 用前台可见的真实 Web 面试页面和真实 Electron/Qwen/Redis/SSE 链路采集至少 50 个 utterance。
- 生成不含字幕正文的分位数、gap、丢失率、Top 慢样本和一条可脱敏展示的真实 waterfall。

**Non-Goals:**

- 不修复或调整任何已发现的延迟来源。
- 不改变 Qwen、ACK、重传、Ring Buffer、RAG、LLM、快答、Stable Partial、问题预测或业务事件顺序。
- 不把音频、完整字幕或个人资料写入诊断存储。

## Decisions

1. **复用现有有界 performance trace 与 ACK 通道，扩展为 revision 级记录。** Backend 为每个 Partial 生成稳定 `event_id`，并记录 `segment_id/utterance_id/revision/text_length` 与 R0–R8。Browser 复用现有异步 `performance-ack` 回传 R7–R13，不在字幕状态更新前等待请求完成。替代方案是独立遥测服务，但会扩大架构和部署范围。
2. **区分“React 收到新 props”与“用户真正看到文字”。** 父级 transcript render 只记录 R11；`ProgressiveTranscriptText` 在 `useLayoutEffect` 记录 commit，并在下一次 `requestAnimationFrame` 记录 R13，同时记录实际可见 revision/length。诊断不得改变组件现有计时器或显示算法。
3. **用户可见和 Browser 细粒度诊断默认关闭并有界。** Backend 复用项目已经启用的 4096 条有界 performance trace，不增加正文或独立持久化；Web 逐 revision store/commit/paint 记录、Overlay 和远端计数轮询仅在显式 `subtitleDiagnostics=1` 时启用。超限轮换诊断记录，而不是影响产品事件。
4. **用同一事件载荷携带服务端阶段时间戳。** R0–R5 进入 `performance` 元数据并随对应 SSE event 到达 Browser。R6 若 ASGI 层无法可靠取得则明确标记 `unavailable`，不伪造为 R5；可通过有界 ASGI send hook可靠取得时再记录。
5. **跨机器阶段保留原始 wall clock 并标注测量边界。** 同机 Browser 阶段使用同一 wall clock；R5→R7 跨服务器与客户端，正式报告需同时核查 NTP/系统时钟状态，时钟质量不足时只报告范围，不把它冒充为精确单向网络耗时。
6. **Revision 对账以 stage set 为准。** 每个 `event_id + utterance_id + revision` 在 Qwen、Redis、SSE、Browser parse、Store、React commit、paint 分别登记一次；重复登记计数但不改变业务去重逻辑。不可见页面样本带 `visibilityState`，从正式分位数排除。
7. **Overlay 读取诊断旁路 store。** Overlay 只显示计数和 age，不订阅或重写产品 transcript state，避免诊断自身改变渲染路径。

## Risks / Trade-offs

- [逐 revision Trace 增加少量 CPU、Redis 和网络开销] → Browser 细粒度记录默认关闭，Backend 复用已有有界 trace，限制记录数量并禁止正文。
- [浏览器和服务器时钟有偏差] → 记录 RTT/offset，使用最低 RTT 样本校准；质量不足时不输出虚假单向延迟。
- [requestAnimationFrame 只近似 paint] → 将其明确命名为 paint confirmation，不声称等同于 GPU 像素扫描完成。
- [诊断 Overlay 可能影响布局] → 使用 fixed overlay、独立 portal、低频更新并仅在显式诊断模式出现。
- [现有脏工作树包含其他功能改动] → 只编辑直接相关文件，逐文件核对 diff，不覆盖用户已有修改。

## Migration Plan

1. 先增加 Backend/Web 的开关、数据结构和确定性测试，不启用线上诊断。
2. 通过 Backend/Web 测试、类型检查、构建与严格 OpenSpec 校验。
3. 仅在用户授权后部署诊断构建，并只为指定测试 session 开启。
4. 使用可见 Web 页面完成 System-only 50+ utterance 采集并导出报告。
5. 测试结束立即关闭诊断开关；如需回滚，恢复原构建即可，无数据迁移。

## Open Questions

- 当前 ASGI/服务器组合能否可靠提供 R6；实现阶段先验证，不能可靠取得则在报告中标记不可用。
