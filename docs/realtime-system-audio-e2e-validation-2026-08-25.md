# System Audio 实时字幕真实端到端验证（2026-08-25）

## 结论摘要

本轮在真实 macOS、正式 Electron Companion 0.1.20、线上 Backend、真实 Qwen Realtime、真实 Redis、真实 SSE 和用户实际 Web 面试页面上执行了 12 分 19 秒连续视频播放测试。测试窗口为 2026-08-25 07:15:05–07:27:24 CST，活动面试为 `session-d4e2394ad39d45399f5d60afb5fc728b`。

共新增 62 个 System utterances，其中 59 个取得首个 Qwen Partial，11 个取得完整 Browser/React ACK。

- Persistent Qwen Connection：本轮 62 个 System utterances 没有新建连接，也没有重连，全部复用测试开始前已经预热的连接。修复真实生效。
- System VAD/首 Partial 长尾：仍然存在。`frames_before_first_partial` P50=7、P95=33、P99/MAX=95。
- Partial Immediate Publish：路径真实生效，但 `Qwen Partial -> Redis XADD` P50=22ms、P95=107ms，未达到 P95 <20ms 的参考目标。
- 浏览器交付：11 条完整样本中，`SSE Send -> Browser Receive` P50=9.157s、P95=19.802s，明显异常；但完整样本覆盖率只有 11/59，而且页面可能在视频播放期间进入后台调度，不能把该分布解释为纯网络延迟或正式验收分布。
- 本轮未满足严格的 Microphone OFF 条件：Mic 仍新增 42 个 utterances、423 次 append。两个声道逻辑隔离，因此 System 数据仍是真实数据，但测试不是纯 System-only 负载。

因此，本轮证明了 Persistent Connection 修复，但没有证明“字幕反应慢”已经整体解决。服务器侧仍有 Qwen/VAD 长尾；浏览器交付链路还出现了更大的真实异常，需要先补齐可靠浏览器样本再判断其根因。

## 测试环境与前置核验

| 项目 | 结果 |
| --- | --- |
| Electron Companion | 0.1.20，正式进程和 Renderer 均存活 |
| Backend commit | `e261732f40840bfefa0cdf34f8d1f486eb14810a` |
| Realtime transport | `websocket-v2` |
| Redis | 真实 Redis，`runtimeStore=redis`，PING=PONG |
| Redis fallback | 未使用 memory fallback |
| Qwen | `qwen3-asr-flash-realtime-2026-02-10`，真实线上 WebSocket API |
| System Audio | 真实 macOS 系统音频；测试期间持续产生 System frames |
| Web | 用户实际面试页面持续订阅 SSE 并回传部分 React ACK |
| 原始音频持久化 | false |

线上代码包含：

1. 按 `session_id + source_kind` 复用 Qwen session；不再按 `sourceGeneration` 为每个 utterance 重建。
2. System 独立 VAD profile。
3. Qwen receive pump 收到 Partial 后直接进入 transcript event/Redis 分支。

## A. Persistent Connection 是否真正生效

### 本测试窗口增量

| 指标 | System |
| --- | ---: |
| utterances | 62 |
| connection create | 0 |
| reconnect | 0 |
| commit | 62 |
| provider append | 5,633 |
| 测试结束时活动连接寿命 | 1,403,386ms（约 23分23秒） |

本轮从一条已经预热的 System 连接开始，所以窗口内 `connection create=0`。该连接连续处理了 62 个新 utterances，commit/final 后没有关闭。Backend 本次启动后的累计 System 计数约为 115 utterances / 2 connections，即累计 57.5 utterances/connection；其中历史第二次连接建立不发生在本测试窗口内。

结论：**Persistent Connection 通过。**

## B. System Speech Start -> Browser First Partial

完整 T0–T11 样本仅 11 条：

| 指标 | Count | P50 | P95 | P99 | MAX |
| --- | ---: | ---: | ---: | ---: | ---: |
| Speech Start -> Browser First Partial | 11 | 12,629ms | 24,989ms | 24,989ms | 24,989ms |

该结果是实际观测值，但**不是有效的正式验收分布**，原因是：

1. 59 个首 Partial 只有 11 个取得完整 Browser/React ACK；
2. `SSE Send -> Browser Receive` 出现 5–20 秒间隔，而服务器 Redis/XREAD/SSE Send 没有对应等待；
3. 播放视频时 Web 页面可能处于后台，浏览器 fetch reader、`requestAnimationFrame` 和 React commit 会受到后台调度影响；
4. 当前 React ACK 只对当前可见/最新 segment 上报，不能保证每个首 Partial 都形成完整 T9–T11 样本。

所以本轮核心问题的严谨回答是：**观测到的完整样本 P50=12.629s，但覆盖率不足且浏览器调度条件不合格，不能据此宣称真实前台字幕 P50 就是 12.629s。当前尚未取得满足验收条件的 50+ 条完整 T0–T11 样本。**

## C. Qwen 本身耗时

以每个 utterance 的第一条 Qwen append 和第一条非空 Partial 计算：

| 指标 | Count | P50 | P95 | P99 | MAX |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen Append -> First Partial | 59 | 195ms | 4,169ms | 12,092ms | 12,092ms |

P50 很快，但 P95/P99 明显不合格。这里的长尾与 `frames_before_first_partial` 同步出现，说明部分 System 语音虽然已经开始 append，但 Qwen 需要更长的有效音频累积才返回非空 Partial。

## D. System VAD/有效 Partial 是否仍有长尾

| 指标 | Count | P50 | P95 | P99 | MAX |
| --- | ---: | ---: | ---: | ---: | ---: |
| VAD trigger -> speech confirmed | 59 | 43ms | 43ms | 44ms | 44ms |
| frames before first partial | 59 | 7 | 33 | 95 | 95 |

VAD attack 本身稳定在约 43ms，问题不是 attack 判断慢，而是从 speech start 到出现可识别 Partial 之间仍有长尾。59 个样本中，P95 需要 33 个 revision/frame，最大 95 个。

已确认的 >3 秒服务器侧异常样本包括：

| Utterance | Frames before Partial | 主要异常 |
| --- | ---: | --- |
| `system-1787613998017-w26zxg` | 48 | Qwen First Partial 6,054ms |
| `system-1787613429244-i0ts7c` | 33 | Qwen First Partial 4,169ms |

Redis stream 末端保留窗口还观测到另外两条 `Speech Start -> Redis XADD` 超过 4 秒的样本，frames 分别为 11 和 33。由于 stream 有 1,000 条裁剪上限，本表不能代替 59 条内存聚合全集。

结论：**System VAD/有效 Partial 长尾仍存在，参考目标未通过。**

## E. Browser 是否存在额外延迟

| 阶段 | Count | P50 | P95 | P99 | MAX |
| --- | ---: | ---: | ---: | ---: | ---: |
| SSE Send -> Browser Receive | 10 | 9,157ms | 19,802ms | 19,802ms | 19,802ms |
| Browser Receive -> State Update | 11 | 725ms | 12,311ms | 12,311ms | 12,311ms |
| State Update -> React Render | 11 | 12ms | 26ms | 26ms | 26ms |

React commit 本身很快，异常主要发生在 T8→T9，以及少量 T9→T10。Nginx 已配置 `proxy_buffering off`，响应也带 `X-Accel-Buffering: no`，因此当前证据不支持简单归因于 Nginx buffering。

T8→T9 的实际含义是“Backend generator 标记发送后，到 Browser JavaScript parser 执行”，它同时覆盖代理传输、浏览器网络读取和浏览器线程调度，不能命名为纯网络 RTT。

结论：**Browser 侧存在真实异常信号，但样本覆盖不足；需要在 Web 页面保持前台可见、Mic 真正关闭的条件下重跑，才能形成正式结论。**

## F. 实际最慢环节排序

### 完整样本 P95 排序

1. SSE Send -> Browser Receive：19,802ms（10 条，覆盖不足）
2. Browser Receive -> State Update：12,311ms（11 条，覆盖不足）
3. Qwen Append -> First Partial：4,169ms（59 条，可靠）
4. ASR Input Age：1,141ms（59 条，可靠）
5. Backend Receive -> Qwen Append：620ms（59 条，可靠）

### 服务器侧可靠样本排序

1. Qwen Append -> First Partial：P95 4,169ms
2. Speech/VAD -> Qwen input：P95 1,141ms
3. Backend Receive -> Qwen append：P95 620ms
4. Qwen Partial -> Redis XADD：P95 107ms
5. Network：P95 65ms

Redis XADD -> XREAD P95=50ms，XREAD -> SSE Send P95=20ms；大多数样本远低于该值，未出现持续队列积压。测试期间 Backend queue depth 始终为 0。

## 分阶段统计

| 阶段 | Count | P50 | P95 | P99 | MAX |
| --- | ---: | ---: | ---: | ---: | ---: |
| VAD Detection | 59 | 43 | 43 | 44 | 44 |
| Desktop Dispatch | 59 | 427 | 429 | 437 | 437 |
| Network | 59 | 55 | 65 | 152 | 152 |
| Backend Dispatch | 59 | 210 | 620 | 702 | 702 |
| Speech/VAD -> Qwen Append | 59 | 736 | 1,141 | 1,321 | 1,321 |
| Qwen First Partial | 59 | 195 | 4,169 | 12,092 | 12,092 |
| Partial Publish | 58 | 22 | 107 | 162 | 162 |
| Redis Consumer | 58 | 8 | 50 | 889 | 889 |
| SSE Dispatch | 58 | 4 | 20 | 198 | 198 |
| SSE -> Browser | 10 | 9,157 | 19,802 | 19,802 | 19,802 |
| Browser State | 11 | 725 | 12,311 | 12,311 | 12,311 |
| React Render | 11 | 15 | 65 | 65 | 65 |

单位均为毫秒。

## 最慢完整 Waterfall（共 11 条，不能虚构为 Top 20）

| Utterance | Total | VAD | Desktop | Network | Backend | Qwen | Publish | Redis | SSE | SSE→Browser | Browser State | React | Frames | 最大阶段 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `system-1787613619017-5119ro` | 24,989 | 43 | 427 | 53 | 78 | 147 | 19 | 8 | 1 | 11,843 | 12,311 | 59 | 5 | Browser State |
| `system-1787613410770-afjom7` | 20,349 | 43 | 43 | 54 | 142 | 238 | 7 | 4 | 6 | 19,802 | 4 | 6 | 3 | SSE→Browser |
| `system-1787613763893-3g978z` | 19,596 | 43 | 427 | 52 | 319 | 194 | 10 | 11 | 2 | 11,813 | 6,660 | 65 | 7 | SSE→Browser |
| `system-1787613998017-w26zxg` | 15,560 | 42 | 43 | 51 | 4 | 6,054 | 11 | 13 | 3 | 7,916 | 1,408 | 15 | 48 | SSE→Browser |
| `system-1787613817600-jx1tsu` | 13,387 | 43 | 427 | 52 | 569 | 324 | 49 | 49 | 2 | 9,157 | 2,694 | 21 | 10 | SSE→Browser |
| `system-1787613429244-i0ts7c` | 12,629 | 42 | 43 | 53 | 38 | 4,169 | 36 | 3 | 5 | 8,235 | 1 | 4 | 33 | SSE→Browser |
| `system-1787613830507-ympaix` | 10,303 | 43 | 43 | 50 | 4 | 253 | 7 | 6 | 9 | 9,875 | 0 | 13 | 2 | SSE→Browser |
| `system-1787613441320-to96kw` | 8,591 | 44 | 427 | 55 | 191 | 139 | 5 | 10 | 13 | 7,659 | 7 | 41 | 6 | SSE→Browser |
| `system-1787613386621-0vsl8d` | 6,826 | 43 | 426 | 55 | 313 | 163 | 29 | 8 | 4 | 5,776 | 0 | 9 | 7 | SSE→Browser |
| `system-1787613374556-xmt4wm` | 3,074 | 42 | 428 | 55 | 261 | 232 | 22 | 17 | 4 | 523 | 1,466 | 24 | 7 | Browser State |
| `system-1787613876608-uowh1k` | 1,817 | 42 | 427 | 58 | 300 | 195 | 49 | 5 | 5 | timestamp skew | 725 | 12 | 7 | Speech→Qwen input |

## 测量缺口

本轮没有修改代码。当前生产埋点仍缺少或无法稳定提供：

- 原始 `desktop_first_non_silent_audio` 与 VAD threshold crossing 的独立时间戳；当前 T0 使用 `systemVadTriggerAtMs`。
- 每条 Trace 的 provider `connection_id`；只能通过会话级连接计数证明复用。
- 每个 utterance 的 `audio_energy`、`noise_floor`、`vad_threshold`、`vad_state` 历史快照；当前仅有桌面运行态最新值。
- 每个首 Partial 的稳定 T9–T11 ACK；当前 React 只对最新可见 segment 回传，且后台页面会影响调度。
- Companion 的声道级关闭开关；进入 live 后当前实现会同时启动 microphone 和 system source，因此本轮 Mic OFF 条件没有真正满足。

这些缺口不能用推测或模拟值补齐。

## 验收判断

| 验收项 | 结果 |
| --- | --- |
| 50+ System utterances | 通过（62） |
| Persistent connection | 通过 |
| reconnect 约 0 | 通过（0） |
| Backend queue 无持续积压 | 通过 |
| Qwen Partial -> Redis XADD P95 <20ms | 未通过（107ms） |
| System VAD/Partial 无 3–10s 长尾 | 未通过 |
| Speech Start -> Browser Partial P50 <1s/P95 <2s | 无法正式验收；11 条异常样本明显超标 |
| Microphone OFF | 未满足 |
| 50+ 完整 T0–T11 | 未满足（11） |

## 最终回答

当视频中的人开始讲话后，本轮服务器侧在正常样本中可以较快产生 Partial，但仍有 Qwen/VAD 长尾：Qwen append 到首 Partial 的 P50=195ms、P95=4.169s、MAX=12.092s。浏览器完整样本观测到 T0→T11 P50=12.629s，但其最大耗时发生在 T8→T9，且仅 11 条、页面前后台状态不受控，不能作为最终商业指标。

当前证据能明确确认的两个主要延迟区间是：

1. **可靠服务器侧长尾：T4 Qwen first append → T5 first Partial。**
2. **需复测的最大异常：T8 SSE send → T9 Browser receive/parser。**

本轮不进行任何架构或代码修改。

## 临时诊断版复测补充（15:30–15:55 CST）

### 测试范围

- 本机临时安装与正式版相同 Bundle ID 的 0.1.20 ARM64 诊断构建，使用 Developer ID 签名并完成 Apple 公证。
- 编译时启用 `VITE_REALTIME_DIAGNOSTIC_AUDIO_CHANNELS=system`，本轮最近 100 条 Trace 全部为 `system`，没有 microphone Trace，System-only 条件真实生效。
- 当前前台 Web 会话为 `session-0e7175a37b884a1dbb0ecd6b9dc0f86c`，Backend、Redis、Qwen 和 SSE 均为线上真实服务。
- 诊断期间未修改服务器代码、Redis/SSE 协议、ASR、RAG、LLM 或回答逻辑。

### 首段有效样本

会话内性能汇总保留 4,096 条 Trace，得到 48 个 Speech Start/首帧样本、46 个 Qwen 首 Partial 样本和 11 个完整 Browser/React 样本。

| 阶段 | Count | P50 | P95 | P99 | MAX |
| --- | ---: | ---: | ---: | ---: | ---: |
| Speech Start → First Frame Send | 48 | 278 | 385 | 11,157 | 11,157 |
| First Frame → Qwen Append | 48 | 167 | 779 | 1,189 | 1,189 |
| Desktop → Backend Network | 4,096 | 80 | 116 | 202 | 413 |
| Backend Preprocess | 4,096 | 2 | 6 | 11 | 38 |
| Backend Queue Wait | 4,096 | 0 | 2 | 61 | 1,086 |
| ASR Input Lag | 4,092 | 1 | 10 | 19 | 134 |
| Qwen Append → First Partial | 46 | 526 | 12,197 | 12,291 | 12,291 |
| Qwen Partial → Redis XADD | 467 | 63 | 123 | 164 | 378 |
| Redis XADD → XREAD | 456 | 3 | 31 | 170 | 222 |
| Redis XREAD → SSE Send | 456 | 8 | 42 | 207 | 304 |
| SSE Send → Browser Receive | 9 | 577 | 24,566 | 24,566 | 24,566 |
| Browser Receive → State Update | 13 | 1 | 11,363 | 11,363 | 11,363 |
| State Update → React Render | 13 | 5 | 33 | 33 | 33 |
| Speech Start → Browser First Partial | 11 | 6,677 | 31,919 | 31,919 | 31,919 |

单位均为毫秒。

这些数据再次确认：Backend 正常帧的网络、预处理、队列和 ASR input lag 不是主要瓶颈；Qwen 首 Partial 和浏览器交付仍有明显长尾。但是，本次还复现了比延迟更高优先级的客户端稳定性故障。

### P0：Renderer 重启后出现“假 capturing”

临时诊断版运行期间多次观察到 Electron Renderer PID 变化，重启前曾出现约 600–775 MB RSS 和 88%–152% CPU。Renderer 自动恢复后：

1. 网页和 pairing-status 仍返回 `sessionStatus=live`、`captureState=capturing`；
2. 设备绑定的 `lastSeenAtMs` 没有继续推进；
3. 连续 135 秒真实观察窗口内，System `append=0`、`utterance=0`、`connection create=0`；
4. 完整重启 Companion 后继续观察约两分钟，System append 仍为 0；
5. Redis 全局事件仍有变化，因此不能用 Redis 活跃误判该桌面正在送音频。

这说明当前存在明确的状态一致性缺陷：**Renderer/Publisher 已停止，但 UI 和后端会话仍显示正在收音。** 用户感知就是字幕停止更新、一直等待或“正在转写”，而不是单纯 ASR 响应慢。

### 本轮根因优先级

1. **P0：Electron Renderer 内存/CPU 异常并重启，Publisher 没有随恢复流程重新建立；捕获实际停止。**
2. **P0：captureState 使用会话期望状态而不是最近音频帧/Publisher lease，产生假 capturing。**
3. **P1：有效音频正常到达时，Qwen Append → First Partial 仍有 12 秒级长尾。**
4. **P1：Partial → Redis XADD P95=123ms，仍高于 20ms 参考目标。**
5. **P1：Browser ACK 覆盖不足，已有样本仍出现 24秒级 SSE→Browser 长尾。**

### 本轮验收判断

本轮不能宣称实时字幕链路通过商业化验收。当前最先需要解决的不是继续微调 Qwen/VAD，而是确保 Renderer/Publisher 不崩溃，并让服务端以最近帧、连接 lease 和 publisher heartbeat 判断真实采集状态。否则任何 ASR 延迟分布都会被“实际没有音频上传”污染。
