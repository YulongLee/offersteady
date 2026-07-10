## Context

OfferSteady 当前已有三条基础线：Web 实时面试工作台、FastAPI Realtime Speech / Chat 服务、Electron 桌面伴随程序骨架。Web 端已经规定实时对话只展示“面试官”和“我”，协议层也已有 `microphone -> candidate`、`system -> interviewer` 的角色路由基础。缺口是 macOS Apple Silicon 端还没有形成真实可运行闭环：音频采集、设备绑定、状态监控、转录同步、Web 嵌入和本地开发包下载尚未整合成一个可验收产品。

本设计以当前开发机器可验证为优先：先完成 macOS arm64 开发包，再保留 universal / x64 / 正式签名路线。桌面端不得成为第二套业务前端；它承载采集、监控和嵌入 Web 工作台，业务事实仍由后端和 Web 工作台维护。

## Goals / Non-Goals

**Goals:**

- 在 Apple Silicon Mac 上运行桌面伴随程序并完成麦克风/耳机与系统音频双声道采集。
- 将麦克风/耳机声道固定显示为“我”，将系统音频声道固定显示为“面试官”。
- 在桌面端和 Web/嵌入工作台中都能看到权限、音量、采集、暂停、重连、错误和在线状态。
- 桌面软件内嵌当前 Web 面试工作台，支持本地开发 URL 和配置 URL。
- 生成当前开发机器可用的 macOS arm64 开发包/下载产物，并在 Web 下载区域展示可用状态。
- 接入服务端 Realtime Speech 边界，完成转录事件同步和后续自动问题触发的产品契约。
- 默认不写本地录音文件，不在普通日志中记录原始音频、完整敏感转录或凭证。

**Non-Goals:**

- 不实现 Windows 端真实采集。
- 不完成正式 Developer ID 签名、公证和公网分发。
- 不把简历、JD、资料库、支付或登录逻辑搬到桌面端。
- 不提供隐藏录音、绕过系统权限、静默自启动采集或无法停止的模式。
- 不实现离线 ASR、本地大模型或本地回答生成。

## Decisions

### Decision 1: Ship macOS arm64 first, keep universal packaging as follow-up

本次 apply 以 `package:mac:arm64` 或等价本地产物为最低可交付。原因是用户当前只有 Apple Silicon Mac 可测，先打通真实本机闭环比一次性追求 Intel / universal / 公证更有价值。现有 ADR 仍保留 universal 正式路线；本变更只把 arm64 作为本地下载和开发验收目标。

Alternative considered: 直接实现 universal DMG。缺点是 x64 无本机验收，签名、公证和构建体积会拖慢音频闭环。

### Decision 2: Keep Electron, use replaceable audio adapters

继续使用现有 Electron + React/TypeScript 桌面壳。渲染层通过 `navigator.mediaDevices.getUserMedia` 获取本地麦克风/耳机，通过 Electron main 的 `desktopCapturer` / display media handler 获取系统音频。所有平台能力通过 `AudioSourceAdapter` 抽象，不把 macOS 特有代码散落到 UI。

Alternative considered: 用 Swift / ScreenCaptureKit 原生应用。它可能更贴近 macOS 音频能力，但会让当前 React/TypeScript Web 原型复用成本变高；若 Electron 系统音频稳定性不足，再单独做原生适配器。

### Decision 3: Use two fixed source roles instead of speaker guessing

角色判别不依赖声纹或模型猜测：`sourceKind=microphone` 固定为 `role=candidate` / “我”，`sourceKind=system` 固定为 `role=interviewer` / “面试官”。如果来源混合、缺失、断开或客户端不兼容，系统进入 degraded，不自动触发回答。

Alternative considered: 用 ASR diarization 猜角色。风险是误判会在面试现场触发错误回答；双声道产品已经能提供更稳定的角色来源。

### Decision 4: Desktop shell embeds Web workspace but backend remains source of truth

桌面窗口分为“伴随程序状态区”和“Web 工作台区”。Web 工作台 URL 从环境变量、配置文件或默认本地地址读取，例如 `http://127.0.0.1:5173/app`。嵌入方式优先使用 Electron `BrowserView` / `WebContentsView` 或安全 `BrowserWindow` 分区，不在桌面 preload 中暴露服务端密钥。

Alternative considered: 复制一套 React 工作台到桌面 renderer。缺点是 Web 和桌面业务 UI 会分叉，后续原型修改容易再次失控。

### Decision 5: MVP transport uses backend WebSocket with ordered frames

桌面端通过后端 Realtime Speech WebSocket 发布设备状态、音频帧和控制事件。帧保留 `deviceId/sourceId/sourceKind/sequence/capturedAtMs/durationMs/codec`。服务端按设备和来源去重、排序并转给 ASR gateway。后续可以替换为 WebRTC 或原生低延迟通道，但 API 边界不变。

Alternative considered: 桌面直连 ASR。缺点是密钥会进入客户端，且绕过会话绑定、权限、日志和问题触发策略。

### Decision 6: Local download artifact is explicit development distribution

Web 设备页/下载页可以展示“本机开发版 macOS Apple Silicon”，来源为本地构建产物或静态 dev manifest。它必须标明 `development/local` 状态，不伪装为已签名公网发行版。用户点击后打开本地文件路径、下载本地 artifact，或显示运行命令。

Alternative considered: 只让用户从命令行运行 `npm run dev -w @offersteady/desktop`。这不满足用户“支持我现在的开发机器下载”的产品验收。

## Risks / Trade-offs

- [Risk] Electron 系统音频在不同 macOS 权限/版本表现不稳定 → Mitigation: 限定 macOS 14.2+，提供权限诊断、系统音频失败降级和手动输入路径。
- [Risk] 嵌入 Web 后登录态与外部浏览器不一致 → Mitigation: 使用同一后端 API，桌面 Web 分区独立存储；必要时支持重新微信登录或开发 token。
- [Risk] 本地开发包被误认为正式发行版 → Mitigation: release manifest 明确标记 development/local，正式签名前不显示 verified 外部分发。
- [Risk] 双声道回声导致同一句话被识别两次 → Mitigation: 服务端保留 source identity、时间戳、序列和去重窗口，系统音频问题触发优先。
- [Risk] 音频隐私敏感 → Mitigation: 不写本地录音文件，bounded memory buffer，日志脱敏，结束会话清理。
- [Risk] 实时 ASR 延迟影响自动回答 → Mitigation: 先保证转录和状态可见，再启用自动问题触发；低置信度保留手动快答。

## Migration Plan

1. 补齐协议与服务端 Realtime Speech 发布/状态接口，定义双声道 transcript event。
2. 完成 macOS arm64 桌面音频适配器：权限、设备列表、麦克风、系统音频、音量诊断和状态机。
3. 实现桌面到后端的绑定与 WebSocket 发布，先用 synthetic PCM/短帧测试，再接真实音频帧。
4. 将转录事件同步到 Web 状态聚合和实时对话区。
5. 在桌面壳中嵌入 Web 工作台 URL，并提供打开外部浏览器的 fallback。
6. 生成 macOS arm64 本地开发包，更新 release manifest / 下载页显示本机可用 artifact。
7. 跑桌面、协议、后端、Web 和一次本机手动验收。

Rollback: 如果系统音频不可用，保留麦克风/手动输入/截图回答；如果嵌入 Web 不稳定，桌面保留状态监控并提供“在浏览器打开工作台”。

## Open Questions

- 当前本机 macOS 版本是否满足 14.2+ 系统音频路径要求？
- 本地开发包希望输出为 `.app`、`.dmg`，还是先以 `--dir` 目录包验收？
- 嵌入 Web 默认打开本地开发 URL，还是后续部署域名？
- 自动问题触发是否本次必须端到端启用，还是先验收双声道转录与手动快答联动？
