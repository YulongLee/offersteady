## Why

线上真实日志显示，一个用户切换到新面试后，旧页面仍能持续发送 heartbeat 和实时 stream 请求，15 分钟产生 1,471 次无效订阅和 1,499 次错误。现有系统限制了桌面音频 publisher，却没有限制 Web 页面消费者，导致后台标签页和重复 Effect 持续占用实时资源。

## What Changes

- 为每个用户建立唯一的活跃实时面试页面租约，包含 `sessionId`、`pageInstanceId`、`leaseGeneration` 和过期时间。
- 新页面进入 live 时主动接管租约，后端立即使旧页面租约失效。
- 同一浏览器使用 `BroadcastChannel` 通知其他面试标签页暂停，跨浏览器和跨设备由后端租约强制兜底。
- heartbeat、SSE stream、实时快照和回答操作携带页面租约身份；旧租约返回明确的 `409 session-replaced` 或 SSE `revoked`。
- 旧页面停止 heartbeat、stream、轮询和未完成请求，保留历史内容但进入只读暂停状态。
- `404`、`409 session-replaced`、`410` 和 `session-not-active` 成为终止错误，不进入自动重连。
- 一个用户的新 live 页面接管后，桌面助手只继续向新的活跃 session 发布音频。

## Capabilities

### New Capabilities

- `single-active-interview-page`: 定义用户级唯一活跃实时页面、接管、暂停、过期恢复和跨标签页协调行为。
- `terminal-realtime-subscription-lifecycle`: 定义实时订阅的终止错误、资源清理和有限重连行为。

### Modified Capabilities

<!-- No archived main capability is modified; active realtime changes are superseded where they allow multiple web consumers. -->

## Impact

- 影响 Web LivePage 生命周期、Backend adapter、实时请求类型和跨标签页协调模块。
- 影响 FastAPI heartbeat/stream 路由、RealtimeSpeechService、Repository Port、内存与 Redis Repository。
- 不改变音频格式、ASR 供应商、桌面采集方式、面试历史数据或页面主要视觉原型。
- 页面实例标识仅用于短期租约协调，不包含音频、转写正文或个人资料。
