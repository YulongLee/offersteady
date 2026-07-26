# OfferSteady 实时语音延迟测试报告

## 1. 测试结论

本次测试确认，用户感知到的约 1 分钟延迟并不是 ASR 模型单次识别耗时造成的。

当前线上主要故障是实时会话生命周期与鉴权状态不一致：

- 网页仍在订阅已经失效的旧 session。
- 桌面助手仍在使用已被新面试替换的 publisher token。
- 助手收到 `410` 后持续重连旧 token，没有完成“清理旧 token -> 获取当前绑定 -> 创建新 publisher”的恢复流程。
- 当前绑定虽然显示为 `live`，但助手访问 runtime、device-status 和 transcript 接口时持续收到 `401`。
- 结果是麦克风采集正常、服务器网络正常、ASR 独立测试正常，但当前面试没有一条可用的端到端发布通道。

因此，当前一分钟级等待主要是“等待错误通道恢复或等待旧页面轮询碰到可用状态”，不是音频在 ASR 模型中处理了一分钟。

## 2. 测试范围

测试时间：2026-07-26

测试环境：

| 项目 | 环境 |
| --- | --- |
| Web | `https://mianshiwen.cn` |
| Backend | 线上 Docker 服务，版本 `8e77e516` |
| Desktop | macOS arm64，面试稳伴随程序 `0.1.0` |
| ASR | 项目 `.env` 中配置的实时 ASR 服务 |
| 线上日志窗口 | 最近 2 小时 |

测试覆盖：

| 环节 | 测试方式 |
| --- | --- |
| 本机麦克风采集 | macOS native capture runtime，持续 2 秒 |
| 公网基础网络 | `curl` DNS、TCP、TLS、TTFB 分段计时 |
| 当前设备绑定 | 线上 pairing-status |
| 当前 session API | runtime、transcripts、stream |
| publisher 恢复 | 线上容器日志 |
| ASR 独立性能 | 合成语音按 100ms PCM chunk 提交 |
| 后端发布性能 | performance timing 埋点 |
| 异常请求压力 | 线上 2 小时日志聚合 |

## 3. 线上真实观测

### 3.1 当前设备与网络

| 指标 | 结果 | 判断 |
| --- | ---: | --- |
| 助手到线上 HTTPS 连接 | 2 条 established | 网络已连接 |
| 当前设备注册 | registered | 正常 |
| 当前设备绑定 | bound | 正常 |
| 当前 session 状态 | live | 表面正常 |
| 健康接口总耗时 | 97ms | 正常 |
| realtime status 总耗时 | 84ms–141ms | 正常 |

公网基础链路不存在分钟级延迟。

### 3.2 当前 session 与鉴权

| 请求 | 实际结果 |
| --- | --- |
| pairing-status | `200`，返回当前 live binding |
| runtime | `401` |
| transcripts | `401` |
| stream | `401` |
| device-status | 日志中持续出现 `401` |
| 旧 publisher WebSocket | 持续收到 `410` |

这说明“设备绑定成功”和“实时发布通道可用”目前不是同一个原子状态。页面能够显示已绑定，但助手无法为当前 session 建立可用 publisher。

### 3.3 最近两小时异常请求

| 异常 | 次数 |
| --- | ---: |
| 旧 session A 的 stream `404` | 717 |
| 旧 session B 的 stream `404` | 355 |
| runtime `401` | 151 |
| device-status `401` | 151 |
| 旧 publisher token 被替换 `410` | 388 |
| domain error 总数 | 1,523 |

两个失效 session 合计产生 1,072 次 stream `404`。这些请求并不会生成字幕，只会增加 Redis、FastAPI、Nginx 和浏览器重连负担。

### 3.4 线上接口延迟

| 接口 | 样本 | p50 | p95 | 最大值 |
| --- | ---: | ---: | ---: | ---: |
| 旧 session A stream | 718 | 265ms | 472ms | 818ms |
| 旧 session B stream | 356 | 264ms | 485ms | 790ms |
| pairing-status | 158 | 54ms | 177ms | 591ms |
| 当前 session transcripts | 14 | 437ms | 537ms | 588ms |
| 当前 session events | 14 | 447ms | 540ms | 545ms |
| 当前 session question-candidates | 14 | 454ms | 538ms | 587ms |

基础公网请求约 100ms，但 session 聚合接口已经达到约 450ms。大量无效 stream 请求是当前服务负载和事件循环压力的重要来源。

## 4. 各阶段独立性能

### 4.1 本机音频采集

| 指标 | 麦克风 | 电脑输出 |
| --- | ---: | ---: |
| 探测时长 | 2,000ms | 2,000ms |
| PCM frame 数 | 45,600 | 0 |
| buffer 数 | 19 | 0 |
| 权限 | granted | not-granted |
| 结果 | 正常产出 PCM | 屏幕录制权限未授予 |

麦克风采集本身正常，不是当前麦克风字幕一分钟延迟的原因。电脑输出仍有独立权限问题，不能与麦克风链路混为同一个性能问题。

### 4.2 真实 ASR 独立基准

测试音频长度为 3,460ms，按 100ms PCM chunk 提交。

| 阶段 | Manual 结句 | VAD 结句 |
| --- | ---: | ---: |
| 首个 partial，从测试开始计算 | 2,238ms | 2,429ms |
| capture-to-send | 2,660ms | 2,736ms |
| send-to-ingest | 1ms | 2ms |
| 后端 queue wait | 2ms | 2ms |
| ASR TTFT | 514ms | 538ms |
| ASR final | 554ms | 8,038ms |
| backend push | 3ms | 6ms |
| capture-to-publish | 3,220ms | 10,784ms |
| 整段 final，从开始播放计算 | 6,656ms | 14,184ms |

结论：

- ASR 首字耗时约 0.51 秒，模型首字不是一分钟瓶颈。
- 后端排队只有约 2ms，后端 worker 没有明显积压。
- 后端发布只有 3–6ms，不是主要瓶颈。
- Manual 模式明显优于 VAD 模式。
- VAD final 等待约 8 秒，存在 provider final timeout，不能用于追求低延迟的最终字幕。
- 独立基准中的 capture-to-send 达到约 2.7 秒，是正常链路中最明显的可优化项。

注意：该独立基准会在发送 chunk 期间读取 runtime，因此 capture-to-send 数字包含测试驱动开销。它可以证明发送侧会形成积压，但不能直接等同于桌面助手真实 p95；桌面端还需要补充本机队列深度和 frame age 的生产指标。

## 5. 一分钟延迟发生在哪里

当前实际故障链路如下：

```text
麦克风正常产出 PCM
  -> 助手持有旧 publisher token
  -> WebSocket 重连
  -> 后端返回 410：发布通道已被新会话替换
  -> 助手没有清除旧 token，也没有创建当前 session 的新 publisher
  -> 助手 runtime/device-status 请求又因缺少有效鉴权返回 401
  -> 网页同时订阅旧 session，持续收到 404
  -> 当前 live session 没有稳定的音频发布和字幕订阅闭环
  -> 用户等待几十秒到一分钟仍看不到当前讲话
```

所以当前不能把“一句话约一分钟后显示”解释成一个正常的耗时分段。当前请求在通道建立阶段已经失败，后续显示属于异常恢复或跨 session 状态碰撞。

## 6. 根因优先级

### P0：桌面 publisher 恢复状态机不完整

助手收到 `410` 后仍然复用同一个失效 token。正确行为应当是：

1. 立即停止该 token 的重连计时器。
2. 删除内存和本地缓存中的 publisher token。
3. 读取当前 device binding 和 binding generation。
4. 使用当前 binding 创建新 publisher。
5. 新 publisher WebSocket 成功后才恢复音频发送。
6. 恢复过程只允许单实例执行，禁止多个重连循环并发创建连接。

### P0：设备身份和用户鉴权模型混用

pairing-status 是设备可访问接口，但 runtime、device-status 和 publisher 创建依赖用户身份。桌面助手不应该长期复用网页用户态，也不应在没有 Authorization 的情况下无限重试。

商业化方案应为绑定成功的设备签发短期 device session credential。该凭据只能访问绑定 session 的 publisher、heartbeat、device-status 和必要诊断接口，不能访问用户其他业务数据。

### P0：网页旧 session 订阅没有真正停止

同一浏览器至少存在两个旧 session 的重连循环。页面收到 `401/403/404/410` 后应永久终止该 EventSource/订阅实例，取消所有 timer、focus listener 和 fallback poll，并返回当前面试入口。

只修改 React state 不足以解决问题，必须保证旧订阅对象和闭包已经被销毁。

### P1：桌面发送侧仍存在 frame age

在通道修复后，应继续压缩 capture-to-send：

- 记录每个音频 frame 的 `capturedAtMs`、`sentAtMs` 和实际 frame age。
- publisher 未连接时不得无限缓存音频。
- 只保留最新 partial 音频窗口，final 边界不可丢。
- WebSocket 可写时直接发送，避免 UI 状态更新阻塞音频 sender。
- 将健康状态、runtime 轮询与音频发送队列彻底隔离。

### P1：生产环境未显式指定 turn detection mode

线上容器未显式设置 `OFFERSTEADY_REALTIME_ASR_TURN_DETECTION_MODE`。从本次结果看，Manual final 约 0.55 秒，VAD final 约 8.04 秒。生产环境需要显式固定低延迟策略，避免不同构建或默认值变化导致性能漂移。

### P1：无效请求需要熔断和限流

后端应对同一设备、同一失效 session 的高频 `401/404/410` 做短期熔断。客户端必须停止重试，服务端限流只能作为第二道保护。

## 7. 修复后验收指标

| 指标 | 目标 |
| --- | ---: |
| 麦克风 capture-to-send p95 | <= 300ms |
| 公网 send-to-ingest p95 | <= 200ms |
| 后端 queue wait p95 | <= 50ms |
| ASR TTFT p95 | <= 800ms |
| backend push p95 | <= 100ms |
| 首个 partial 端到端 p95 | <= 1,500ms |
| 停止说话到 final p95 | <= 2,000ms |
| 前端 publish-to-render p95 | <= 200ms |
| 失效 token 的重复重连次数 | 0 |
| 失效 session 的持续 stream 请求 | 0 |
| 新面试继承旧 session 字幕 | 0 |

## 8. 最终判断

当前实时语音功能尚未达到可商业化上线标准。

ASR 模型性能基本可用，公网基础网络正常，麦克风 native capture 正常。当前最需要修复的不是继续压缩模型的几百毫秒，而是统一 device binding、publisher token、用户鉴权和网页 session 的生命周期。P0 问题解决后，实际延迟应先从“一分钟或不可用”恢复到数秒级，再针对 capture-to-send 和 final detection 做第二轮性能优化。
