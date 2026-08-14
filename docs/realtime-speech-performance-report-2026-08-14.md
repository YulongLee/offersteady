# 实时语音链路性能优化报告（2026-08-14）

## 结论

本轮不更换 ASR 模型，重点优化桌面采集、WebSocket v2 传输、Manual 断句、provider 观测与网页 partial/final 合并。修正会污染测量结果的旧轮询脚本后，真实 Manual 路径不再出现桌面发送积压，完整识别了测试语句。

## 优化前基线

- 本地旧合成基线：5 帧，transport p95 2.8ms，队列 0，丢帧 0。该结果只覆盖旧测试入口，不代表生产 WebSocket v2。
- 2026-07-26 真实模型基线：capture-to-send 约 2.7s；Manual ASR final 约 0.55s；VAD final 约 8s。
- 线上优化前采样：后端队列 0；麦克风连接重建 2 次、系统音频连接重建 4 次，说明瓶颈不在后端吞吐，而在客户端传输与连接恢复。

## 本轮实现

- WebSocket v2 保存带 sequence 的未确认音频，短暂重连自动重发。
- publisher 凭据被拒绝时只运行一个恢复流程，换取当前绑定的新 token，并转移未确认帧。
- 恢复队列由 64 帧提升到 256 帧，溢出时优先保留 final，并上报明确 sequence gap。
- 每路音频新增未确认队列深度、最老帧龄、丢帧数、ACK 时间、重连次数与原因诊断。
- 麦克风和系统声音分别使用动态噪声基线；Manual 静音收束调整为麦克风 850ms、系统声音 650ms。
- 优先使用 AudioWorklet，旧 Electron 环境自动回退 ScriptProcessor。
- provider runtime 新增 append、commit、completed missing、blank partial、VAD fallback 与活跃 session 指标。
- 网页继续使用相同 segment/revision 原位合并 partial/final，并展示发送积压或音频缺口提示。

## 优化后测量

### 本地 WebSocket v2 合成链路

结果文件：`artifacts/realtime-asr-benchmarks/optimized-2026-08-14.json`

| 指标 | 结果 |
| --- | ---: |
| 样本 | 5 |
| ACK 平均 | 2.41ms |
| ACK p95 | 9.22ms |
| 后端队列 | 0 |
| 丢弃 partial | 0 |
| 字幕完整发布 | 5/5 |

### 真实 DashScope Manual 路径

测试音频 5.414s，按 100ms PCM 增量块通过 WebSocket v2 送入。

| 阶段 | 结果 |
| --- | ---: |
| capture-to-send | 2ms |
| send-to-ingest | 4ms |
| queue wait | 15ms |
| provider final | 736ms |
| backend push | 14ms |
| capture-to-publish | 771ms |
| 停止说话到 final | 约 797ms |
| 最终文本 | 完整 |
| runtime anomaly | 无 |

### VAD 对照

相同音频在 8 秒 final 窗口内没有完成，且只得到不完整 partial。因此生产默认保持 Manual，VAD 只保留为诊断和灰度能力。

## 验收判断

- capture-to-send p95 目标 300ms：通过（本次 2ms；仍需部署后持续采样真实桌面 p95）。
- 后端 queue wait p95 目标 50ms：通过（本次 15ms）。
- 停止说话到 final 目标 2s：通过（约 797ms）。
- 正常链路丢帧：通过（0）。
- partial/final 连续性、迟到 partial 抑制、断线重发与 token 恢复：自动化回归通过。
- 30/60 分钟真实桌面稳定性：部署后观察项；本地自动化不能替代真实会议软件、系统权限和蓝牙设备的持续运行。

## 发布后冒烟验证

- 生产提交：`79e6d07`；后端、Web、管理端、PostgreSQL 与 Redis 容器均正常运行，后端健康检查通过。
- 正式站首页、健康检查、支付状态与实时语音状态接口均返回 HTTP 200；实时语音报告 `websocket-v2` 与 Redis runtime store 正常。
- 使用 Playwright 验证正式站 1280px 桌面端与 390px 手机端：首页完整渲染，无白屏、横向溢出或区块遮挡。
- macOS arm64、macOS x64 与 Windows x64 三个 `0.1.7` 正式下载入口均返回短期签名下载地址，线上 manifest 的版本及 SHA-256 与最终安装包一致。
- 全量回归：JavaScript 404 项、Python 220 项通过（10 项按环境跳过）；所有 workspace typecheck 与 build 通过。

## 隐私

性能报告只记录时延、计数、状态和错误分类，不保存原始音频或用户语音正文。
