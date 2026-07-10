# 电脑伴随程序分发与兼容性

计划分发三个独立安装包：macOS Apple Silicon arm64、macOS Intel x64、Windows 10/11 x64。Windows ARM64、Linux 和移动原生伴随程序不在当前范围。

macOS 发布包必须完成 Developer ID 签名、公证和安装验证；Windows 发布包必须完成代码签名和安装/卸载验证。发布清单包含版本、最低系统版本、大小、SHA-256、协议版本、签名状态和实际能力。签名失败、校验值缺失、被撤回或协议不兼容的包不能显示下载按钮。

当前原型中的两个 macOS 条目使用合成清单，Windows 条目明确显示“签名验证中”，不提供真实下载。取得证书并产出安装包后，发布负责人才能把对应条目切换为 verified。

## 本机开发版下载

当前 Apple Silicon Mac 可用本机开发版 zip 进行端到端调试：

```bash
npm run package:mac:arm64 -w @offersteady/desktop
```

该命令会生成：

- `apps/desktop/release/mac-arm64/OfferSteady-Companion-0.1.0-macOS-arm64/面试稳伴随程序.app`
- `apps/desktop/release/mac-arm64/OfferSteady-Companion-0.1.0-macOS-arm64/打开说明.txt`
- `apps/desktop/release/OfferSteady-Companion-0.1.0-macOS-arm64.zip`
- `apps/desktop/release/OfferSteady-Companion-0.1.0-macOS-arm64.json`

后端 `GET /api/v1/web/state` 会读取本地元数据，并在设备下载页展示“macOS Apple Silicon 本机开发版”。下载地址由后端提供，例如：

```text
http://127.0.0.1:8000/api/v1/web/downloads/desktop/OfferSteady-Companion-0.1.0-macOS-arm64.zip
```

本机开发版会进行 ad-hoc 签名，保证包结构和本机启动可用，但它不是 Apple Developer ID 正式签名/公证发行版。若 macOS 提示无法验证开发者，可在“系统设置 → 隐私与安全性”中允许打开，或右键 App 选择“打开”。如果从 Codex/某些终端环境直接启动，需要确保没有设置 `ELECTRON_RUN_AS_NODE=1`；普通双击和页面下载后的打开不应携带该变量。

## 本地联调诊断

桌面伴随助手与网页联调时，先确认 Web 和桌面指向同一个后端地址。桌面默认后端为：

```text
http://127.0.0.1:8000/api/v1
```

如果网页或手机端使用了局域网地址，需要同时设置桌面环境变量 `OFFERSTEADY_API_BASE_URL`，否则会出现“网页绑定了机器码，但助手仍显示未连接”的错位。

可以运行统一实时 E2E 诊断：

```bash
OFFERSTEADY_API_BASE_URL=http://127.0.0.1:8000/api/v1 \
OFFERSTEADY_MANUAL_CODE=123456 \
OFFERSTEADY_DEVICE_ID=your-device-id \
OFFERSTEADY_SESSION_ID=your-session-id \
OFFERSTEADY_USER_ID=admin \
npm run realtime:e2e-diagnose
```

该命令会同时输出：native runtime 权限状态、native 麦克风短时 PCM 探针、native 系统输出探针、后端绑定状态、当前 session runtime、真实桌面帧证据、ASR 合成 PCM 探针（可选）和截图请求阶段（可选）。旧命令仍可使用：

```bash
npm run diagnose:runtime -w @offersteady/desktop
```

诊断报告会写入 `artifacts/desktop-runtime-diagnostics/`，只包含阶段状态、帧计数、错误码和后端返回摘要，不包含原始音频、屏幕图像、截图、API Key 或发布令牌。

如果需要验证后端实时语音入口是否能接收帧并明确返回 ASR 状态，可以额外启用合成 PCM probe。注意：PCM probe 只能证明后端 ingest 与 ASR 适配器可达，不能证明桌面助手真实麦克风/电脑输出已经打通：

```bash
OFFERSTEADY_API_BASE_URL=http://127.0.0.1:8000/api/v1 \
OFFERSTEADY_SESSION_ID=your-session-id \
OFFERSTEADY_USER_ID=admin \
OFFERSTEADY_RUN_PCM_PROBE=1 \
npm run diagnose:runtime -w @offersteady/desktop
```

PCM probe 只在内存中生成短合成音频并记录帧回执、ASR 状态、计数和耗时；报告不保存原始音频。若 `session.backendPcmProbe` 返回 `accepted`，说明后端帧入口和 ASR 状态透出可用。若当前网页仍没有实时对话，应继续检查桌面端真实麦克风/电脑输出是否产生本地电平、`frameCount` 和 `backendFrameCount`。

截图回答排障可以设置 `OFFERSTEADY_SCREENSHOT_REQUEST_ID` 让诊断报告读取某个远程截图请求的阶段。屏幕捕捉排障时先点击伴随助手中的“预览”。预览成功必须看到真实屏幕缩略图；如果缩略图为空或没有屏幕源，伴随助手会显示权限/运行时错误，并且网页发起截图回答时会把失败原因回传给后端。不要仅凭“选择了显示器”判断屏幕捕捉可用。

本地开发包如果显示系统设置里已经授权、但助手仍提示未授权，优先确认当前包是否为 ad-hoc 签名。`codesign -dv --verbose=4 <app>` 若显示 `Signature=adhoc` 或 `TeamIdentifier=not set`，表示每次重新打包后 macOS 都可能把它当成新的代码身份；这时需要运行 `npm run desktop:reset-privacy-open`，在新打开的 App 上重新授权麦克风、录屏与系统音频。不要只在系统设置里看旧开关状态。

当前 macOS 麦克风实时发布优先走 native runtime 的 JSONL PCM 帧流：Electron 主进程启动原生 helper，renderer 只在内存中转发帧到后端 WebSocket，不落盘保存原始音频；若 native bridge 不可用，才回退到 Electron WebAudio。系统输出音频通过 ScreenCaptureKit native stream 输出同样的 JSONL PCM 帧；如果返回 `screen-capture-permission-required`、`system-audio-stream-start-failed` 或没有后端帧回执，表示不能把“权限已打开”当成系统音频可用。若当前 macOS/App 身份无法捕获微信、会议软件或浏览器播放出的电脑输出声音，助手应显示具体失败原因或降级为麦克风单通道，不能用“绿灯”伪装成功；后续商业化版本仍需要固定 bundle id、Developer ID 签名和公证来稳定 TCC 授权。

### 当前 session 实时对话排障顺序

当网页左侧“实时对话”没有出现“面试官 / 我”时，按下面顺序检查：

1. 桌面伴随程序是否已经自动登记到同一个后端
   - 桌面端连接码应稳定显示。
   - 如果网页绑定机器码后助手仍显示“未连接”，优先检查桌面端和网页端是否真的指向同一个 `OFFERSTEADY_API_BASE_URL`。

2. 当前面试 session 是否已经完成机器码绑定并点击“开始面试”
   - 只有当前 session 进入 live 状态后，后端才会把双通道音频视为当前面试的实时对话来源。
   - 未开始面试时，网页应显示“本场面试还未开始”而不是历史转录。

3. 桌面端是否真的采集到了两类来源
   - 麦克风/耳机输入对应“我”。
   - 电脑输出音频对应“面试官”。
   - 如果本地电平条没有波动，问题在采集层，不在 ASR 或网页层。

4. 后端 runtime 是否已经收到当前 session 的帧
   - 查看 `GET /api/v1/realtime-speech/sessions/<sessionId>/runtime?userId=<userId>`。
   - `sourceHealth.frameCount` 或 `backendFrameCount` 为 0，说明采集或上传没有成功。
   - `lastErrorCode=asr-failed` 说明后端收到了音频，但转写阶段失败。

5. 网页是否消费了当前 session 的转录
   - 查看 `GET /api/v1/realtime-speech/sessions/<sessionId>/transcripts?userId=<userId>`。
   - 如果这里已有 `role=interviewer/candidate` 的转录，但页面仍是空态，优先检查网页轮询/消费逻辑，而不是重新绑定机器码。

这条排障链路只允许使用当前 session 的 runtime、events 和 transcripts 作为事实来源，不应再通过其他 session 的历史记录来猜测当前状态。

下载包名称不代表运行能力。客户端连接后仍需报告麦克风、系统音频和协议能力；Windows 系统音频不可用时，网页保留麦克风、手动输入和截图路径。支持的最低 Windows 版本将在物理设备验证后从 Windows 10 22H2 或 Windows 11 中确定。

撤回故障版本时从发布清单移除下载地址并保留审计记录；已安装客户端收到安全升级提示。回滚不得重新开放未签名或已知受损的构建。
