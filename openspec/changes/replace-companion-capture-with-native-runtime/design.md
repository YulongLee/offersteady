## Context

用户连续实测后确认：当前伴随助手打开后麦克风和电脑输出没有音量波动，屏幕捕捉预览没有生效；同时在网页没有打开时，桌面端仍显示某个历史 session 已绑定。这暴露出两个根问题：

1. 现有 Electron renderer 直接调用 `getUserMedia/getDisplayMedia` 的实现无法保证 macOS 上真实捕获麦克风、电脑输出和屏幕。
2. 后端通过机器码查 latest binding 的策略会把历史 session 当成当前连接，导致假连接状态。

这不是页面文案或按钮位置问题，而是桌面采集内核和连接状态事实源的问题。新的设计必须把“产品能力是否真的成立”作为验收标准，而不是“App 能打开、接口能返回、状态显示已连接”。

## Goals / Non-Goals

**Goals:**

- 在当前 macOS Apple Silicon 开发机上真实采集麦克风/耳机输入。
- 在当前 macOS Apple Silicon 开发机上真实采集电脑输出音频，即用户能听到的会议/微信/浏览器声音。
- 在当前 macOS Apple Silicon 开发机上真实获取所选显示器的屏幕预览帧。
- 通过后端 Realtime Speech 将麦克风转写为“我”、电脑输出转写为“面试官”。
- 网页没有活跃会话时，桌面助手不得显示历史 session 已绑定。
- Web 端绑定机器码后，必须通过后端保存当前 active binding，并用心跳保持连接新鲜。
- 桌面端必须通过媒体自检门禁后才显示“已可用/正在收音/捕捉屏幕”。

**Non-Goals:**

- 不修改网页产品原型布局和桌面助手视觉风格。
- 不在本变更中实现 Windows 原生采集。
- 不引入隐藏录音、静默采集或绕过系统权限的能力。
- 不保存默认原始音频、屏幕录像或截图。
- 不把 ASR/LLM API key 放入桌面客户端或原生 helper。

## Decisions

### Decision 1: Replace browser media capture with a macOS capture runtime boundary

Electron 继续负责 UI、机器码、状态显示和打开网页，但麦克风、电脑输出音频和屏幕捕捉必须由独立 capture runtime 提供。该 runtime 可以优先实现为 macOS native helper（Swift/ScreenCaptureKit/AVFoundation）或 Node native boundary，向 Electron 输出统一事件：

- `source-ready`
- `level`
- `audio-frame`
- `screen-frame`
- `permission-required`
- `capture-error`

Alternative considered: 继续修 Electron `getDisplayMedia`。用户实测已多次失败，且系统输出音频本身不是普通浏览器媒体输入；继续修会浪费时间并继续制造假绿灯。

### Decision 2: Use ScreenCaptureKit for computer output and screen frames on macOS

macOS 13+ 的 ScreenCaptureKit 能提供 display/window capture，并可包含系统输出音频。对 OfferSteady 的“面试官声音 = 用户听到的电脑输出”模型来说，它比浏览器 getDisplayMedia 更贴近产品需求。麦克风输入由 AVFoundation/CoreAudio 获取，电脑输出由 ScreenCaptureKit 获取，屏幕预览也由 ScreenCaptureKit 的 selected display stream 获取。

Alternative considered: 强制用户安装虚拟音频驱动。它可能稳定，但增加安装门槛和权限成本；可以作为 fallback，不作为首选 MVP 路线。

### Decision 3: Stale binding is invalid by default

后端不得仅按 manual code 返回最新历史绑定。新的 active binding 必须同时满足：

- desktop device 最近心跳未过期；
- Web session 最近心跳未过期；
- session 状态为 preparing/live；
- binding 的 `bindingGeneration` 与当前桌面设备登记 generation 匹配；
- 用户或会话上下文仍有效。

Alternative considered: 继续返回 latest binding，桌面自行判断。缺点是桌面无法知道网页是否真的打开，正是当前“网页没打开却已绑定”的根因。

### Decision 4: Capture validation gate blocks false success

桌面助手启动后必须先跑自检：

- 麦克风：权限 granted、track opened、level > threshold、PCM frame emitted。
- 电脑输出：ScreenCaptureKit stream opened、播放测试音/真实电脑声音时 level > threshold、PCM frame emitted。
- 屏幕：selected display stream opened、至少收到一帧 preview。
- 后端：frame receipt 和 ASR accepted 至少能跑通测试段。

未通过时只显示“未就绪/不可用/需授权/需适配器”，不得显示“已连接并等待音频信号”。

Alternative considered: 允许进入 live 后再慢慢发现失败。面试场景不能这样，用户需要面试前就知道可用。

### Decision 5: Web and desktop use explicit heartbeats

Web preparation/live page 每 2-5 秒向后端发送 session heartbeat；桌面助手每 2-5 秒发送 device heartbeat。后端 pairing status 和 runtime status 使用 heartbeat freshness 判断连接，不再从历史记录推断。

Alternative considered: 只靠 API 请求时间或 session status。它不能代表网页仍打开，也不能代表桌面仍在线。

## Risks / Trade-offs

- [Risk] 引入 Swift/ScreenCaptureKit 提高工程复杂度 → Mitigation: 原生层只做采集和权限，不承载业务逻辑；Electron UI 和后端协议不变。
- [Risk] macOS 权限仍可能被系统拒绝 → Mitigation: 自检门禁显示具体缺失权限和恢复路径，不进入假成功。
- [Risk] ScreenCaptureKit 最低系统版本限制 → Mitigation: 检测 macOS 版本，不支持时明确提示并走虚拟音频驱动 fallback proposal。
- [Risk] 原生 helper 打包失败 → Mitigation: 增加本地 package 验收和 helper health check；未带 helper 的包不得标记支持电脑输出/屏幕捕捉。
- [Risk] 真实音频/屏幕隐私敏感 → Mitigation: 原生层只输出实时帧，不写本地文件；诊断只记录计数、状态和错误码。

## Migration Plan

1. 停止把 Electron browser media path 作为 macOS 真实采集验收路径，仅保留为 fallback/diagnostic。
2. 建立 macOS capture runtime 接口和 helper 进程通信协议。
3. 实现麦克风、电脑输出、屏幕预览三类 source 的原生采集自检。
4. 修改后端 binding：加入 Web heartbeat、desktop heartbeat、generation 和 TTL，废弃 latest binding 直接返回策略。
5. 修改桌面 runtime：只有 fresh active binding + capture validation gate 全部通过才显示可用状态。
6. 修改 Web preparation/live：绑定后持续发送 heartbeat，离开页面或结束面试后 binding 失效。
7. 打包 macOS arm64 并在当前机器完成手工 E2E 验收。

Rollback: 若原生 helper 暂时无法打包，桌面助手必须明确显示“采集运行时不可用”，保留手动输入和网页快答，不允许显示假连接或假音频成功。

## Open Questions

- 当前开发机 macOS 版本是否满足 ScreenCaptureKit 系统输出音频采集要求？
- 是否接受在后续 fallback 中引入 BlackHole/虚拟音频驱动作为可选方案？
- 本地调试期间 Web heartbeat 是否需要支持手机局域网访问地址？
