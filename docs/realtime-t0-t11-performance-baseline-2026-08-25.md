# 实时面试 T0–T11 性能基线（2026-08-25）

## 范围与结论

本轮保持 Electron 双通道采集、二进制持久 WebSocket、Qwen Realtime ASR、Redis Event Stream、SSE 和浏览器单调归并不变，只补齐端到端诊断并修复有明确证据的 P0 热路径等待。

当前样本显示：本机传输、后端入口队列、Redis 与 SSE 发送不是主要瓶颈。2026-08-25 使用真实 Qwen、真实 Redis、真实 WebSocket 和真实 SSE 执行了 12 轮、100ms 节奏 PCM 热路径测试；Qwen append 到首个 partial 的 P50 为 437ms、P95 为 447ms。Qwen 已返回 partial 后，现有同步 append 调用在下一帧才取出该 partial 并发布，额外形成 P50 61ms、P95 84ms 的等待。这是目前除 Qwen 首字外最明确的应用侧延迟。

本机没有麦克风输入设备，且 macOS 拒绝了正式 Electron 进程的屏幕/系统音频采集；内置浏览器会话也不可用。因此本轮没有伪造 Electron T0/T1 或 Browser T8-T10 数据，完整的 `Speech Start -> Browser First Partial` 分布仍为空。下文明确区分真实已覆盖阶段与尚未取得的端点样本。

## 统一 Trace

每条可交付转录现在可关联以下阶段，且只包含脱敏标识和时间戳：

| 阶段 | 字段 | 位置 |
| --- | --- | --- |
| T0 | `speechStartAtMs` | 语音活动开始 |
| T1 | `desktopWsSendAtMs` | 桌面首帧 WebSocket 发送 |
| T2 | `backendWsReceiveAtMs` | 后端收到首帧 |
| T3 | `qwenAudioAppendAtMs` | Qwen 音频 append 完成 |
| T4 | `qwenPartialReceivedAtMs` | Qwen partial 实际到达接收线程 |
| T5 | `redisEventXaddAtMs` | Redis XADD 完成 |
| T6 | `redisEventXreadAtMs` | Redis XREAD 返回该事件 |
| T7 | `sseEventSendAtMs` | SSE 增量发送 |
| T8 | `browserEventReceiveAtMs` | 浏览器收到事件 |
| T9 | `browserStateUpdateAtMs` | 浏览器本地状态更新 |
| T10 | `browserRenderAtMs` | React commit 后确认 |

关联字段为 `sessionId`、`channel`、`sequence`、`utteranceId`、`eventId` 和 `traceId`。报告和接口不记录原始音频、转录正文、访问令牌或用户资料。

会话级诊断接口：

- `/api/v1/realtime-speech/sessions/{sessionId}/performance-traces`
- `/api/v1/realtime-speech/sessions/{sessionId}/performance-summary`
- `/api/v1/realtime-speech/metrics`

汇总输出提供 count、P50、P95、P99 和 MAX；样本覆盖不足时对应阶段返回空值，不用推测值填充。

## 本轮实测

### 合成本机热路径（5 个最终帧）

| 指标 | 结果 |
| --- | ---: |
| WebSocket ACK 平均 | 0.53ms |
| WebSocket ACK P50 | 0.38ms |
| WebSocket ACK P95 | 1.07ms |
| 队列深度 | 0 |
| 生产帧 / 消费帧 | 5 / 5 |
| 丢弃 partial | 0 |
| 全部转录发布 | 5 / 5 |

### 真实 Qwen Realtime 单次参考样本

| 指标 | 结果 |
| --- | ---: |
| 音频时长 | 2455ms |
| 首个 partial（相对音频开始） | 513ms |
| final（相对音频开始） | 2656ms |
| 语音结束到 final（驱动测量） | 约 201ms |
| 最后一帧 capture-to-send | 7ms |
| 最后一帧后端队列等待 | 0ms |
| 最终帧 Qwen 等待 | 192ms |
| 最终帧 capture-to-publish | 199ms |
| ASR 会话异常 / 队列异常 | 未发现 |

同一音频的 Server VAD 对比探针在 8 秒观察窗口内没有形成 final；生产默认仍保持 `manual`，本轮没有切换 VAD，也没有据此修改业务终结策略。

### 真实 Qwen + Redis + SSE 首个 Partial（12 轮）

本组通过持久 WebSocket 以 100ms 帧节奏发送 macOS `say` 生成的 PCM16 音频。后端、Qwen Realtime、Redis 8.10.1 和 SSE 均为真实进程；未启用 Redis 内存回退。发送器不是 Electron 音频采集器，HTTP 流消费者也不冒充浏览器，所以 T0/T1 与 T8-T10 不进入完整端到端结论。

| 阶段 | P50 | P95 | P99 | MAX |
| --- | ---: | ---: | ---: | ---: |
| Speech Start -> First Frame Send（驱动样本） | 0ms | 0ms | 0ms | 0ms |
| First Frame -> Qwen Append | 2ms | 202ms | 202ms | 202ms |
| Qwen Append -> First Partial | 437ms | 447ms | 447ms | 447ms |
| Qwen Partial -> Redis XADD | 61ms | 84ms | 93ms | 93ms |
| Redis XADD -> XREAD | 1ms | 1ms | 2ms | 2ms |
| XREAD -> SSE Send | 1ms | 2ms | 3ms | 3ms |
| SSE Send -> Browser Receive | 未取样 | 未取样 | 未取样 | 未取样 |
| Browser Receive -> React Render | 未取样 | 未取样 | 未取样 | 未取样 |
| Speech Start -> Browser First Partial | 未取样 | 未取样 | 未取样 | 未取样 |

第一轮包含 Qwen 持久连接创建，First Frame -> Qwen Append 为 202ms；其余 11 轮为 1-2ms。12 轮首个 partial 到 SSE Send 的相对时间分别为 520、515、509、514、530、510、510、515、516、513、508、517ms。

一条真实热路径时间线（第 3 轮）如下：

```text
Speech Start              0ms
Frame Driver Send         0ms
Backend Receive           1ms
Qwen Append               2ms
Qwen First Partial      442ms
Redis XADD              508ms
Redis XREAD             508ms
SSE Send                509ms
Browser Receive       未取样
Browser State Update  未取样
React Render          未取样
```

Redis 直接检查结果：目标 stream 长度 51、consumer group 数 0、pending 不适用且按诊断记为 0。当前读取方式是阻塞 `XREAD`，没有 consumer group；事件级 XADD -> XREAD P95 为 1ms。`XREAD` 调用本身可因空闲 BLOCK 记录约 1 秒，但那不是已有 partial 的 consumer lag。

### 线上真实面试补充样本（2026-08-25）

用户在线面试期间，对正式 Electron、正式 Backend、真实 Redis、Qwen Realtime 和 SSE 进行了只读采样。本次不修改代码、不重启服务，也没有启用 Redis memory fallback。为保护用户数据，报告不记录转写正文、手机号或用户标识。

| 指标 | 麦克风 | 系统音频 |
| --- | ---: | ---: |
| Partial 样本数（最大完整快照） | 31 | 294 |
| Speech Start -> First Published Partial P50 | 1679ms | 2005ms |
| Speech Start -> First Published Partial P95 | 2689ms | 6352ms |
| Speech Start -> First Published Partial P99 | 2689ms | 10489ms |
| Speech Start -> First Published Partial MAX | 2689ms | 10489ms |
| Capture -> Send P50 / P95 / MAX | 0 / 2 / 5ms | 0 / 1 / 3ms |
| Send -> Backend Ingest P50 / P95 / MAX | 153 / 160 / 161ms | 152 / 173 / 1316ms |
| Backend Queue Wait P50 / P95 / MAX | 2 / 14 / 14ms | 2 / 8 / 42ms |
| Capture -> Publish P50 / P95 / P99 / MAX | 169 / 234 / 1332 / 1332ms | 168 / 329 / 1344 / 1656ms |
| 同一段 Partial 更新间隔 P50 / P95 / MAX | 512 / 2161 / 2161ms | 1892 / 3198 / 6027ms |

连续 20 秒队列观察中，大部分时间两声道队列深度为 0；系统声道两次出现 7-10 帧的短时积压，约 2-3 秒后恢复为 0。队列上限为 64，未观察到溢出，但短时积压与 Qwen 连接创建同步占用声道 worker 的代码路径一致。

本场运行时诊断同时显示：

- 麦克风 `commit_count=103`，`connection_recreations=105`。
- 系统音频 `commit_count=90`，`connection_recreations=89`。
- 两声道当时均有 1 个 active provider session，未发现 ASR timeout、session update failure 或 completed missing。

这说明当前所谓的“持久 ASR 会话”只在单个语音段内复用；桌面端每开始一个新语音段都会增加 `sourceGeneration`，而 Qwen gateway 只在 generation 相同时复用连接，因此实际上几乎每段都重建 provider WebSocket。这是本场真实测试新发现的明确热路径问题。

一条真实麦克风 P50 附近时间线（只列出线上旧版观测已能证明的边界）：

```text
Speech/VAD Start             0ms
Desktop Current Frame     1536ms
Desktop Send              1536ms
Backend Receive           1691ms
Backend Queue Leave       1692ms
Backend Publish           1705ms
Redis XADD                1708ms
Redis XREAD / SSE / Browser / React   线上旧版未记录
```

对应的系统音频 P50 样本为 2005ms，P95 样本为 6419ms。P95 样本中，VAD 开始后约 6231ms 才出现本次能产生有效文字的桌面帧；这与系统音频低阈值被背景声过早触发、以及 provider 需要累积到可识别语音后才返回文本的现象一致。这一结论是根据 revision 和时间相关性做出的推断，不应误解为纯网络延迟。

线上事件 stream 已达 1000 条裁剪上限；Redis stream ID 与事件 `created_at_ms` 差值 P50 1ms、P95 3ms、P99 7ms、MAX 14ms。无 consumer group，所以不存在 pending entries list。这些数据继续不支持把 Redis XADD 视为主要瓶颈。

注意：线上旧版的 `sentAtMs` 在本地入队时记录，因此约 150ms 的 `Send -> Backend Ingest` 可能包含桌面端队列驻留，不能直接解读为纯网络 RTT。当前工作树已将 T1 移到真实 `WebSocket.send` 边界，但本次只诊断，该观测改动未部署。

## Top 5 延迟来源（当前证据排序）

1. **客户端话语终结窗口**：系统声道 500ms、麦克风 700ms 静音尾窗是 final 前的确定等待。它用于完整性保护，本轮不改。
2. **Qwen 首个 partial 与每段连接重建**：12 轮单段真实样本中，Qwen append 到首个 partial 为 P50 437ms、P95 447ms；但线上实际几乎每个新语音段都重建 Qwen WebSocket，并会在连接期间造成短时帧积压。因此不能把单段内后续 append 的 1-2ms 误当作跨语音段持久连接的生产现状。
3. **Qwen partial 的应用侧取出等待**：接收线程已在 T4 收到 partial，但 `_latest_available_transcript` 只在下一次音频 append 调用时读取，因此产生 P50 61ms、P95 84ms。正确方向是让 provider partial 的接收回调直接进入字幕事件发布支路；本轮只诊断，没有实施架构改造。
4. **浏览器帧调度**：SSE parser 使用 `requestAnimationFrame` 合并同一帧内更新，理论增加 0-16.7ms；它不会重新请求 transcripts/runtime/candidates，正常更新按 `segmentId + revision` 本地单调归并。尚无真实浏览器 ACK 样本，不能把它列为主要瓶颈。
5. **Redis/SSE**：事件级 Redis XADD -> XREAD P95 1ms，XREAD -> SSE P95 2ms，没有 sleep、固定 batch 等待或慢 consumer 证据，不是当前主要瓶颈。

本机样本中后端队列等待为 0ms、生产等于消费，因此没有证据支持扩大线程池、增加 worker 或重写队列。盲目增加并发反而可能增加 Qwen 会话竞争。

## 当前工作树中已存在的 P0 热路径改动

1. 工作树此前已移除每批 SSE 更新后的固定 `50ms` sleep。该等待不参与背压和游标正确性，删除后不改变事件顺序、游标续传、快答触发条件或转录内容。
2. 工作树此前已将同一转录的两次 Redis `save_transcript` 合并为补齐 timing 后的一次权威写入，减少一次序列化和一次 Redis 写链路；转录 revision、内容和事件顺序保持不变。

## P0/P1 修复候选验证（本地真实 Qwen + 真实 Redis）

根据线上 Trace 已实施三个严格限界的候选修复，未修改 RAG、LLM、Redis 架构、SSE 协议、Server VAD、快答或整体业务逻辑：

1. Qwen provider session 的复用条件不再绑定桌面端逐 utterance 增长的 `sourceGeneration`；一个面试会话内每个声道保持一条连接，只有会话结束、空闲超时、连接异常或不可恢复错误才关闭/重建。
2. System Audio 使用独立 VAD profile，并通过 40ms attack 确认过滤单帧数字底噪；起音仍保留在 pre-speech ring buffer，阈值保持足够低以覆盖低音量开头、英文缩写、数字和短词。
3. Qwen receive pump 收到非空 Partial 后直接创建 `transcript-updated` 事件并写入 Redis；Stable Partial 检测在字幕 XADD 后执行，audio append loop 不再承担 Partial 发布。

本地真实 provider 探针对同一 Interview Session 的 Mic/System 各连续提交 3 个 utterance，结果如下：

| 指标 | Mic | System |
| --- | ---: | ---: |
| Speech Start -> First Provider Partial 样本 | 637 / 435 / 431ms | 2716 / 435 / 481ms |
| P50 | 435ms | 481ms |
| P95 / P99 / MAX | 637ms | 2716ms |
| Qwen connection create | 1 | 1 |
| Qwen reconnect | 0 | 0 |
| utterances / connection | 3.0 | 3.0 |
| frames before first partial（最新） | 5 | 5 |

System 首个 2716ms 样本包含该声道首次建连冷启动；同一连接后两段为 435ms、481ms。该结果证明 commit/final 后连接保持可用，且 `utterance_count` 不再接近 `connection_create_count`。

另一次真实 Backend + Qwen + Redis 探针得到：

| 阶段 | P50 | P95 | P99 | MAX |
| --- | ---: | ---: | ---: | ---: |
| Qwen Partial -> Redis XADD | 2ms | 2ms | 2ms | 2ms |
| Redis XADD -> XREAD | 旧链路复核 1ms | 旧链路复核 1ms | 旧链路复核 2ms | 旧链路复核 2ms |
| XREAD -> SSE Send | 旧链路复核 1ms | 旧链路复核 2ms | 旧链路复核 3ms | 旧链路复核 3ms |

本轮本地环境仍无法取得正式 Electron 音频设备和已登录真实 Browser 的 T0/T1、T8-T10，因此不能虚构 `Speech Start -> Browser First Partial`、`SSE Send -> Browser Receive` 或 `Browser Receive -> React Render` 分布。现有浏览器回归验证了 Partial 按 `utterance_id + revision` 直接单调归并，不会为了每个 Partial 重新请求 transcripts/runtime/candidates。线上当前仍是修复前版本；公开运行指标仍显示 Mic 213 commits / 215 connections、System 111 commits / 109 connections，符合旧问题，不能作为修复后验收数据。

## 下一步验收门槛

- partial：T0→T11，P50 < 500ms，P95 约 1000ms。
- final：speech end→T11，P50 < 1s，P95 < 2s。
- 快答：点击→回答首 token，P50 < 1.5s，P95 < 3s。
- 每个声道 `framesIn - framesOut` 不持续增长，`oldestFrameAgeMs` 不形成长尾。
- Qwen 每个会话每个声道保持一个活动连接；重建率异常时单独告警。

在获得足够真实样本前，不执行 Server VAD 切换、Redis/SSE 替换、事件总线重构、ASR 模型迁移或大规模线程池调整。
