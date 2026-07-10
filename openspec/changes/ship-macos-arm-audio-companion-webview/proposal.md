## Why

当前实时面试页已经具备手动快答和流式回答能力，但真实面试现场主要依赖音频输入。用户需要一个能在当前 Apple Silicon Mac 上实际运行的桌面伴随程序：同时采集本地麦克风/耳机与电脑系统音频，将系统音频识别为“面试官”、本地输入识别为“我”，并把网页工作台直接嵌入软件中，方便一体化使用和调试。

## What Changes

- 将 macOS Apple Silicon 作为本次可交付目标，完成可在当前开发机器运行/下载的桌面伴随程序开发包。
- 桌面端支持双声道音频采集：
  - macOS 本地麦克风或耳机输入固定路由为“我”。
  - 电脑系统音频/会议声音固定路由为“面试官”。
- 实时对话窗口只展示两个角色：“面试官”和“我”，不恢复“角色待确认”或角色修正入口。
- 桌面端提供采集前权限检查、音源可用性检测、音量监控、采集中/暂停/错误/重连状态。
- 将当前 Web 面试工作台嵌入桌面软件窗口中，支持直接打开本地或配置的 Web URL。
- 支持从 Web 设备页/下载页获取当前开发机可用的 macOS arm64 本地开发包，并能看到版本、架构、路径/下载状态和能力说明。
- 接入 Realtime Speech / ASR 处理边界，将双声道转录事件同步到 Web/桌面嵌入工作台。
- 保留用户显式授权、显式开始、持续可见状态和停止入口；默认不保存原始音频。
- 本变更不实现 Windows、不实现正式外部分发签名/公证、不修改资料库、支付、登录、截图回答或回答 Prompt 策略。

## Capabilities

### New Capabilities

- `macos-arm-audio-companion-runtime`: macOS Apple Silicon 桌面伴随程序的权限、麦克风/系统音频采集、音量诊断、状态监控和本地开发包验收。
- `dual-channel-role-audio-routing`: 双声道音频到“面试官/我”的角色路由、降级策略、转录事件和自动问题触发边界。
- `desktop-embedded-web-workspace`: 桌面软件内嵌 Web 面试工作台、URL 配置、连接状态显示和安全边界。

### Modified Capabilities

- `resizable-live-interview-workspace`: 实时对话区必须消费桌面端双声道转录事件，并继续只展示“面试官”和“我”两个角色。

## Impact

- Affected desktop areas: `apps/desktop/src/main`, `apps/desktop/src/renderer`, Electron permissions, audio adapters, packaging scripts and local artifact output.
- Affected backend areas: realtime speech publish/subscribe endpoints, desktop device binding, transcript synchronization, device status aggregation.
- Affected web areas: live conversation state, devices/download page, release manifest or local artifact metadata, embedded Web runtime compatibility.
- Affected protocol areas: `packages/protocol/src/audio.ts`, `packages/protocol/src/speaker.ts`, release manifest capability metadata.
- Affected docs: `docs/desktop-distribution.md`, local run/download instructions, privacy notes for raw audio minimization.
- Privacy impact: raw audio remains transient, local buffers are bounded, logs must not include raw audio bytes, full transcripts, API keys, binding tokens or device credentials.
