## Why

当前桌面伴随助手仍无法稳定采集麦克风、电脑输出音频和屏幕画面，并且出现“网页未打开却显示已绑定旧 session”的假连接状态。这说明现有 Electron 媒体采集和后端绑定状态模型没有达到产品核心能力，必须升级为可真实采集、可验证、不可显示陈旧绑定的桌面运行时。

## What Changes

- 将 macOS 桌面伴随助手的采集能力从“Electron renderer 尝试 getUserMedia/getDisplayMedia”升级为“可替换的原生 macOS 采集运行时”。
- 对麦克风/耳机输入建立真实采集验收：必须能检测本机说话音量、产生 PCM 帧、发送后端并转写为“我”。
- 对电脑输出音频建立真实采集验收：必须能检测微信、会议软件、浏览器等电脑播放声音，产生 PCM 帧、发送后端并转写为“面试官”。
- 对屏幕捕捉建立真实采集验收：必须能获取所选显示器实时预览帧，并作为后续截图回答来源。
- 修正机器码绑定状态：桌面端不得因为历史 latest binding 显示已绑定；只有当前 Web 会话仍存在、最近有网页端活跃心跳、且 session 状态有效时，才显示已绑定。
- 增加“网页端活跃会话心跳”和“桌面端活跃设备心跳”的双向新鲜度校验，避免陈旧 session 污染当前伴随助手。
- 增加采集能力启动前自检门禁：音频/屏幕任一核心链路不可用时，明确阻止进入“已可用”状态，并输出可复现诊断。
- 保持产品原型页面结构和视觉风格不变；本变更只修正桌面助手采集内核、状态机和 Web/后端连接契约。

## Capabilities

### New Capabilities

- `native-macos-capture-runtime`: macOS 原生或原生辅助进程负责麦克风、电脑输出音频和屏幕帧采集，并向 Electron 壳提供统一帧流。
- `fresh-desktop-session-binding`: 机器码绑定必须与当前活跃 Web 会话和当前活跃桌面设备同时新鲜，不能读取陈旧 latest binding。
- `companion-capture-validation-gate`: 桌面助手进入可用/已连接/正在收音状态前，必须通过真实媒体采集门禁。
- `desktop-web-realtime-bridge`: 桌面采集帧、后端 ASR 和网页实时对话必须形成端到端桥接验收。

### Modified Capabilities

- None. 当前产品原型布局、交互分区和页面风格不在本变更中调整。

## Impact

- Affected desktop areas: `apps/desktop` Electron main/renderer, capture adapters, possible macOS native helper/Swift module, package scripts, local dev artifact.
- Affected backend areas: realtime speech desktop registration, session binding freshness, Web heartbeat, desktop heartbeat, stale binding cleanup and runtime diagnostics.
- Affected web areas: interview preparation binding heartbeat and live session heartbeat; no UI layout changes.
- Affected protocol areas: capture runtime contract, fresh binding state, media validation gate result, native helper event schema.
- Verification impact: requires local physical Mac validation with microphone speech, computer playback audio, screen preview and Web realtime transcript display.
- Privacy impact: native runtime MUST keep raw audio and screen frames transient, MUST NOT save recordings/screenshots by default, and MUST redact media payloads from logs and diagnostics.
