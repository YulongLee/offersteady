## Context

OfferSteady 的实时面试核心链路由网页面试页、FastAPI 后端、Realtime Speech/ASR 适配器、桌面伴随程序和截图回答服务组成。当前用户可完成机器码绑定，桌面端也能上报部分权限和设备信息，但进入面试后网页仍显示“等待麦克风或电脑输出出现可识别声音”，截图回答也可能显示 `Failed to fetch`。

最新分段诊断结果：

- 后端 `/api/v1/realtime-speech/status` 可用。
- 当前机器码 `133885` 可以绑定到 admin 用户的 live session。
- 后端能为 session 创建 microphone/system publisher。
- `OFFERSTEADY_RUN_PCM_PROBE=1` 的合成 PCM 探针能进入后端并得到 `lastAsrStatus: accepted`，说明后端 ingest 和 ASR 适配器不是完全未接通。
- 真实桌面端麦克风和系统输出仍没有稳定产生 `frameReceipts`，最新 session 的 `frameReceipts` 和 `transcripts` 为空。
- 电脑输出在 macOS + AirPods/系统音频权限场景下对 Electron `getDisplayMedia` 不稳定，当前上报可能是 `granted` 但实际没有系统音频轨道或没有帧。
- 截图回答链路存在接口和轮询代码，但失败时用户只看到泛化错误，无法判断是网页创建请求、桌面轮询、屏幕捕获、上传、视觉模型还是后端等待阶段失败。

因此本变更把实时能力从“连接状态可见”升级为“真实帧、ASR、网页渲染可验证”。

## Goals / Non-Goals

**Goals:**

- 逐段打通并验证：桌面采集、帧发布、后端 receipt、ASR accepted/transcript、网页实时对话展示。
- 将 macOS 原生采集 runtime 作为实时音频主链路，Electron WebAudio 仅保留为本地检测或兜底。
- 让麦克风和电脑输出分别独立降级：一条通则展示单通道实时对话，两条都不通才显示阻断态。
- 让截图回答具备可观察的阶段状态：request created、desktop claimed、capture success/failure、upload success/failure、vision answer success/failure。
- 提供一条本地端到端自测命令，输出 session、manualCode、frameReceipts、ASR、web runtime、screenshot capture 的结果。

**Non-Goals:**

- 不改变当前面试页面原型布局和机器码绑定流程。
- 不保存原始面试音频、原始截图或个人资料到诊断文件。
- 不在桌面客户端保存 ASR、视觉模型、OSS 或后端服务密钥。
- 不在本变更中完成 Apple Developer ID 签名、公证和正式安装器，但设计必须兼容后续商业化签名。
- 不实现 Windows 系统音频采集主链路。

## Decisions

### Decision 1: Treat backend PCM probe as ASR connectivity proof, but not product success

合成 PCM 探针能够证明后端 ingest、publisher token、ASR gateway 和 runtime receipt 基本可用。但产品成功必须以真实桌面麦克风或系统输出产生 `frameReceipts` 并进入当前 session 为准。

Alternative considered: 只看 ASR 探针 accepted 就认为实时链路成功。Rejected，因为当前故障正是“ASR 可用但真实桌面 0 帧”。

### Decision 2: Native macOS capture runtime becomes the primary capture path

macOS 的麦克风、系统输出和屏幕捕获权限由 TCC、ScreenCaptureKit 和应用签名共同影响。Electron `getUserMedia/getDisplayMedia` 在 AirPods、系统音频、ad-hoc 签名和 Helper 子进程场景下不稳定。桌面端应由原生 runtime 负责采集真实 PCM/屏幕帧，Electron 负责 UI、绑定和状态展示。

Alternative considered: 继续调整 WebAudio 阈值和设备 fallback。Rejected，因为已经多次出现 permissions granted 但 `frameReceipts` 为空，继续调阈值无法解决系统音频轨道不可用和进程授权漂移。

### Decision 3: Keep backend protocol stable and source-kind based

桌面端继续按 `sourceKind=microphone|system` 发布帧。后端统一将 microphone 映射为“我”，system 映射为“面试官”，网页只消费当前 session 的 transcript role。

Alternative considered: 网页端自行根据设备名称判断角色。Rejected，因为会导致历史记录、问题候选和快答逻辑语义漂移。

### Decision 4: Runtime state must be evidence-based

UI 不得仅因为机器码绑定、权限 granted 或 publisher created 就显示实时对话可用。可用状态必须至少满足：当前 session 收到对应 source 的 frame receipt，或正在收到 transcript/question candidate。

Alternative considered: 绑定后一直显示绿色连接。Rejected，因为这正是当前误导用户的主要问题。

### Decision 5: Screenshot answer uses explicit remote stages

网页发起截图回答后，后端创建 capture request；桌面助手 claim request；桌面执行屏幕捕获并上传；后端运行视觉模型和回答模型；网页轮询或订阅结果。每个阶段必须可查询、可展示错误码。

Alternative considered: 保持 120 秒轮询和 `Failed to fetch`。Rejected，因为无法定位链路断点，也不利于商业化支持。

## Risks / Trade-offs

- [Risk] 原生 macOS runtime 增加实现和打包复杂度。→ Mitigation: 保留现有 Electron UI 和后端协议，只替换采集内部实现，并在 release 打包中显式验证 runtime 文件存在。
- [Risk] ad-hoc 签名仍会导致 macOS 权限漂移。→ Mitigation: 本地开发继续提供 reset-and-open 命令；商业化版本必须使用固定 bundle id、Developer ID 签名和 notarization。
- [Risk] ASR accepted 但没有可读 transcript。→ Mitigation: 诊断分别展示 accepted、empty/filler suppressed、partial timeout、final timeout，不把它和采集失败混在一起。
- [Risk] 电脑输出在某些会议软件/耳机路径下不可捕获。→ Mitigation: 独立显示 system source unsupported，并允许 microphone 单通道继续工作。
- [Risk] 截图捕获可能包含敏感屏幕内容。→ Mitigation: 诊断只记录 request id、stage、错误码和尺寸信息；不保存截图内容到诊断文件。

## Migration Plan

1. 固化诊断基线：新增一键 `realtime:e2e-diagnose`，按 session 输出 binding、publisher、real frame receipts、ASR、web runtime、screenshot stages。
2. 将 macOS native runtime 扩展为可输出 microphone/system PCM frame 的主接口，Electron renderer 订阅该接口并发布到现有后端 ingest。
3. 桌面端发布链路改为原生帧优先，Electron WebAudio 仅作为 fallback 和本地波动检测。
4. 后端 runtime 增加阶段化诊断字段，区分 capture-no-frame、publisher-no-connect、asr-accepted-no-text、web-no-consumer、screenshot-stage-failed。
5. 网页面试页改为基于当前 session evidence 展示实时对话和错误原因。
6. 截图回答增加 request stage 查询和桌面端 claim/upload/fail 明细。
7. 打包 macOS release，执行真实麦克风、真实本地播放、截图回答端到端测试。

Rollback:

- 若原生系统输出仍不可用，保留 microphone 单通道可用，并在 UI 明确提示电脑输出 unsupported。
- 若截图回答端到端失败，保留手动截图上传/手动问题输入，不阻塞实时对话主链路。

## Open Questions

- 原生 runtime 需要直接连接后端发布帧，还是把 PCM 通过 IPC 交给 Electron renderer 继续复用现有 publisher？推荐先走 IPC 复用现有 publisher，降低后端协议变化。
- ASR 是否需要针对面试短句启用 partial transcript 流式显示？推荐先完成真实帧闭环，再优化 ASR 延迟和 partial 策略。
