## Why

桌面伴随助手目前在真实使用中仍出现“输入/系统音频无波动、屏幕捕捉无预览、网页绑定后助手状态不变、实时对话无语音识别”的链路断点。继续零散修按钮会掩盖根因；本变更从前后端架构和运行状态契约出发，把采集、绑定、发布、ASR、网页显示每一环都变成可诊断、可验证的闭环。

## What Changes

- 建立桌面伴随助手运行诊断模型，区分“后端可达、设备已登记、机器码已绑定、面试已开始、媒体源已打开、音频帧已产生、WebSocket 已连接、ASR 已接收、网页已显示”等真实状态。
- 修正麦克风/耳机输入链路，确保所选输入设备能产生音量波动、PCM 帧和“我”的转录事件；失败时显示具体原因，不用绿灯假装可用。
- 修正系统音频链路，将“电脑输出/会议声音/微信声音”作为“面试官”来源进行能力检测、采集和发布；当前平台不支持时必须给出明确降级原因和后续适配边界。
- 修正屏幕捕捉链路，确保所选显示器的全屏预览、权限状态和后续截图回答来源一致。
- 拉通网页端机器码绑定与桌面端连接状态：网页创建/开始面试后，助手必须从后端拿到绑定会话并进入可发布状态。
- 拉通桌面端音频帧到后端 Realtime Speech，再到网页实时对话区的端到端流转。
- 增加桌面、后端、网页三端的诊断报告和回归测试，用真实状态证明链路是否打通。
- 保持当前产品原型页面结构和核心交互不变；本变更只修正助手运行能力、状态同步和架构契约。

## Capabilities

### New Capabilities

- `desktop-companion-runtime-observability`: 桌面伴随助手、后端和网页共享同一套运行状态、故障原因和诊断报告。
- `desktop-audio-capture-reliability`: 麦克风/耳机与电脑输出音频的真实采集、音量检测、帧发布和角色路由可靠性。
- `desktop-screen-capture-reliability`: 所选显示器的权限、预览、全屏捕捉和截图来源一致性。
- `desktop-web-live-session-integration`: 机器码绑定、面试开始、实时语音发布、ASR 转录和网页实时对话的端到端集成。

### Modified Capabilities

- None. 当前已批准产品原型布局和交互不在本变更中调整。

## Impact

- Affected desktop areas: `apps/desktop/src/main`, `apps/desktop/src/renderer`, media source adapters, realtime publisher, machine-code registration, screen preview, local package validation.
- Affected backend areas: `apps/backend/app/modules/realtime_speech.py`, `apps/backend/app/services/realtime_speech_service.py`, realtime repository, publisher/session status, diagnostics endpoints and tests.
- Affected web areas: machine-code binding status, live interview realtime polling/subscription, conversation rendering data source; no approved UI layout change.
- Affected protocol areas: `packages/protocol` runtime status, source health, transcript and diagnostic event contracts.
- Affected verification: desktop unit tests, backend realtime tests, Web integration tests, local manual E2E checklist and generated diagnostic report.
- Privacy impact: raw audio and screen frames remain transient; logs and reports MUST NOT include raw audio bytes, screenshots, full sensitive transcripts, API keys, publisher tokens or device credentials.
