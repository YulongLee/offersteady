## Context

OfferSteady 当前已经有 Web 面试页、FastAPI Realtime Speech 服务和 Electron 桌面伴随助手，但真实联调中仍出现三类断点：

1. 桌面端显示设备存在或绿灯，但麦克风/系统音频没有实际音量波动，也没有稳定发布 PCM 帧。
2. 屏幕捕捉的权限、预览和后续截图来源没有形成同一条可验证链路。
3. 网页端输入机器码后可以进入面试流程，但桌面助手没有可靠感知“已绑定/已开始/可发布”，实时对话也没有展示 ASR 转录。

现有实现里已经有设备登记、机器码、发布者令牌、WebSocket、设备状态、转录列表等基础能力，但缺少一个端到端运行状态契约。结果是某一层成功了，另一层失败了，界面仍可能显示“已连接”或“绿灯”。本设计的核心是把“能不能用”拆成可观测的阶段，并让桌面、后端、网页都以同一个事实源判断状态。

## Goals / Non-Goals

**Goals:**

- 让桌面伴随助手打开后自动登记机器码，并周期性向后端报告设备、媒体源和连接状态。
- 让网页端绑定机器码并开始面试后，后端保存绑定关系和 session live 状态，桌面助手能够自动感知并更新为已连接/可发布。
- 让麦克风/耳机输入源产生可见音量波动、PCM 帧和“我”的 ASR 转录。
- 让电脑输出音频源代表面试官声音；微信、会议软件、浏览器播放的声音能够被真实检测，无法检测时必须给出“不支持/未捕获/静音/权限缺失”的准确原因。
- 让屏幕捕捉使用所选显示器的全屏来源，预览与后续截图回答来源一致。
- 让后端 Realtime Speech 接收桌面发布的音频帧，使用 `.env` 中配置的 ASR 模型生成转录事件，并由网页实时对话区显示“面试官 / 我”两种角色。
- 生成一份本地诊断报告，定位失败发生在桌面媒体、后端 API、WebSocket、ASR、网页消费中的哪一段。

**Non-Goals:**

- 不改变产品原型页面结构、主流程文案、资料库、积分、支付、登录和回答区布局。
- 不把服务端密钥、ASR 密钥或模型密钥放入桌面客户端。
- 不保存默认原始录音、屏幕录制或未脱敏截图。
- 不在本变更中实现 Windows 真实系统音频采集。
- 不实现隐藏录音、静默采集、绕过系统权限或不可停止的监控模式。

## Decisions

### Decision 1: Use backend runtime state as the source of truth

后端维护 `DesktopRuntimeState`，聚合设备登记、机器码绑定、session 状态、publisher 状态、source health、最近帧、最近 ASR 结果和最后错误。桌面助手轮询或订阅这个状态；网页端绑定与开始面试只写后端，不直接假设桌面已连接。

Alternative considered: 桌面端本地判断是否连接成功。缺点是网页和后端不知道真实媒体发布状态，容易继续出现“网页认为已连，助手没有变化”的错位。

### Decision 2: Split media health into capability, permission, stream, signal and publish stages

每个媒体源都使用同一套状态阶段：

- `unsupported`: 当前平台/适配器不支持。
- `permission-required` / `permission-denied`: 权限缺失或被拒绝。
- `stream-opened`: 已拿到 MediaStream。
- `track-live`: track 存在且状态 live。
- `signal-detected`: RMS/peak 超过阈值。
- `frames-produced`: 已生成 PCM 帧。
- `frames-published`: 后端确认接收帧。
- `asr-accepted`: ASR gateway 已接收并返回转录或可解释错误。

绿色状态只能在达到对应真实阶段后显示。比如系统音频只有 `track-live` 但长期没有 `signal-detected` 时，不能显示为“面试官声音已生效”。

Alternative considered: 继续只显示已授权/未授权。缺点是授权成功不等于采集成功，无法解释用户遇到的无波动问题。

### Decision 3: Treat macOS system audio as a dedicated adapter with explicit fallback

电脑输出音频不是普通麦克风输入。Electron `getDisplayMedia({ audio: true, video: false })` 在 macOS 上可能拿不到会议/微信/系统输出。实现时必须将系统音频封装为独立 `SystemOutputAudioController`，优先检测当前 Electron/Chromium loopback 是否真的能产生音频帧；若不可行，必须进入 `unsupported` 或 `adapter-required`，并保留后续切换 ScreenCaptureKit/虚拟音频驱动/原生 helper 的边界。

Alternative considered: 把系统音频当成一个固定下拉设备“电脑输出音频”。缺点是 UI 能选中不代表系统能提供 loopback，正是当前问题根因之一。

### Decision 4: Keep capture orchestration in the desktop shell, keep AI processing in backend

桌面负责设备枚举、权限、音频/屏幕采集、PCM 编码、帧发布和健康状态；后端负责机器码、会话绑定、ASR、转录、问题候选、Chat 触发和网页聚合。桌面不得直连 DashScope 或持有模型密钥。

Alternative considered: 桌面直连 ASR 以减少后端复杂度。缺点是密钥泄露、用户身份和会话上下文无法统一、手机端网页也无法可靠同步。

### Decision 5: Screen preview and screenshot source MUST share the same selected display

屏幕捕捉应由 `ScreenCaptureController` 管理。用户选择“显示器 1”后，预览、权限检测、后续快速截图回答都使用同一个 `screenSourceId` 和 display metadata；预览失败时不能继续宣称屏幕捕捉可用。

Alternative considered: 预览用 thumbnail、截图时重新走一次系统选择。缺点是用户无法确认实际捕获的是哪块屏幕，也无法稳定做快速截图回答。

### Decision 6: E2E verification starts with a local diagnostic matrix

本变更不只依赖肉眼看页面。实现时需要提供本地诊断命令或报告，逐项输出：

- Backend API reachable
- Desktop device registered
- Machine code bound to session
- Session live
- Publisher created
- WebSocket connected
- Microphone stream opened / signal / frames / ASR
- System output stream opened / signal / frames / ASR
- Screen permission / selected display / preview frame
- Web realtime conversation consumed transcript

Alternative considered: 只跑单元测试。缺点是媒体权限和系统输出音频是运行时问题，必须有本机诊断报告覆盖。

## Risks / Trade-offs

- [Risk] macOS/Electron 当前能力无法直接捕获系统输出音频 → Mitigation: 用真实信号检测证明是否支持；不支持时明确进入 `adapter-required`，并把原生 ScreenCaptureKit 或虚拟音频驱动作为后续实现边界。
- [Risk] 桌面与网页连接状态仍可能因轮询间隔延迟 → Mitigation: 后端状态保存 `updatedAt` 与 `lastSeenAt`，桌面和网页均展示最近一次后端确认状态；后续可升级 SSE/WebSocket 状态推送。
- [Risk] ASR 调用延迟导致实时对话慢 → Mitigation: 区分音频帧接收成功和 ASR 转录成功；先显示采集/发布状态，再显示转录结果。
- [Risk] 用户误以为屏幕持续录制 → Mitigation: 只做显式授权的屏幕预览/截图来源，不默认保存屏幕视频；诊断报告不写截图内容。
- [Risk] 本地开发环境 API URL 不一致导致助手连错后端 → Mitigation: 桌面启动时显示并上报实际 `apiBaseUrl`，后端 pairing status 返回登记来源，诊断报告检查网页和桌面是否指向同一后端。

## Migration Plan

1. 梳理当前桌面、后端、网页的机器码、状态、WebSocket 和媒体适配器调用路径，形成断点矩阵。
2. 增加共享 runtime status 协议和后端聚合状态接口，不改变产品原型布局。
3. 重构桌面媒体源为麦克风、系统输出、屏幕三个独立 controller，并按阶段报告健康状态。
4. 修正桌面到后端的 publisher 创建、WebSocket 发布、设备状态上报和失败回传。
5. 修正网页绑定/开始面试后对后端状态的写入与读取，确保助手能看到 `bound/live`。
6. 将 ASR 转录事件稳定落入后端会话，再由网页实时对话区消费。
7. 添加测试和本机诊断报告，重新打包 macOS arm64 伴随助手。

Rollback: 若系统输出音频在当前 macOS/Electron 路径无法稳定采集，保留麦克风、手动快答和截图回答可用，系统输出源显示为不可用/需适配器，不允许继续显示为成功。

## Open Questions

- 当前开发机 macOS 版本和 Electron 版本是否支持 Chromium loopback 系统音频，还是需要切换原生 ScreenCaptureKit 适配器？
- 系统音频后续是否接受引入虚拟音频驱动作为可选依赖？
- 网页与桌面本地联调是否统一使用 `http://127.0.0.1:8000/api/v1`，还是需要支持局域网手机访问地址？
