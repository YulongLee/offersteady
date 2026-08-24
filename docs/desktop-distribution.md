# 电脑伴随程序分发与兼容性

## macOS Developer ID 正式发布

正式的官网 macOS 包使用 Electron Builder、固定 Bundle ID `com.offersteady.companion` 和以下签名身份：

```text
Developer ID Application: Yulong li (8Y5FAR3TF3)
```

正式 Release 不允许回退到 ad-hoc、Apple Development 或本地开发证书。开发调试继续使用下文的 `package:mac:arm64` / `package:mac:x64`，两条流程互不替代。

### 1. 创建公证凭证

推荐在 App Store Connect 中进入“用户和访问（Users and Access）→ 集成（Integrations）→ App Store Connect API → 团队密钥（Team Keys）”，创建具有 App Manager 权限的团队 API Key。保存以下三项：

- Key ID：10 位 Key ID。
- Issuer ID：UUID 格式的发行者 ID。
- `AuthKey_<KeyID>.p8`：只能下载一次，存放在仓库以外的受控目录。

运行时通过环境变量提供，不要写入 `.env`、YAML、脚本或 Git：

```bash
export APPLE_API_KEY=/绝对路径/AuthKey_YOURKEYID.p8
export APPLE_API_KEY_ID=YOURKEYID
export APPLE_API_ISSUER=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

也可以先将凭证安全存入 macOS Keychain：

```bash
xcrun notarytool store-credentials "OfferSteady-Notary" \
  --key /绝对路径/AuthKey_YOURKEYID.p8 \
  --key-id YOURKEYID \
  --issuer xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

export APPLE_KEYCHAIN_PROFILE=OfferSteady-Notary
```

Keychain profile 只保存于当前 Mac 登录钥匙串，不进入仓库。发布脚本也兼容 `APPLE_ID`、`APPLE_APP_SPECIFIC_PASSWORD` 和 `APPLE_TEAM_ID`，但自动化优先使用团队 API Key。

### 2. 正式构建

Apple Silicon：

```bash
npm run package:mac:release:arm64 -w @offersteady/desktop
```

Intel：

```bash
npm run package:mac:release:x64 -w @offersteady/desktop
```

命令会依次执行：Swift runtime 编译、Electron 构建、Developer ID 嵌套签名、Hardened Runtime、App 公证与 staple、DMG 生成、Developer ID 签署最终 DMG、DMG 独立公证与 staple，以及 App/DMG 的 codesign、Gatekeeper、stapler 终检。App 和 DMG 两次公证都必须返回 `Accepted`；任何阶段失败都不会把产物报告为正式发行包。

正式 DMG 路径：

```text
apps/desktop/release/macos-production/OfferSteady-Companion-<version>-macOS-<arch>.dmg
```

每个架构独立清理和生成自己的 App/DMG，构建 Intel x64 时不得删除或覆盖已经验收的 arm64 DMG，反之亦然。发布前还应核对 App 主程序和 `OfferSteadyCaptureRuntime` 的实际 Mach-O 架构与目标一致。

### 3. 没有公证凭证时的签名预检

开发者账号刚开通、API Key 尚未创建时，可先生成 Developer ID 签名的解包 App：

```bash
npm run package:mac:release:prepare:arm64 -w @offersteady/desktop
```

该命令验证 Developer ID、完整嵌套签名、Hardened Runtime和时间戳，但会明确把 Gatekeeper 与 stapler 标为 `PENDING`。它不会生成官网正式 DMG，不得上传分发。

首次使用新导入的 Developer ID 私钥时，macOS 可能提示 `codesign` 访问钥匙串密钥。应在确认进程为 `/usr/bin/codesign` 且证书为上述 Developer ID 后选择“始终允许”，否则签名进程会等待钥匙串授权。不要通过脚本写入登录密码来绕过该确认。

最终 Release 验证等价于：

```bash
codesign --verify --deep --strict --verbose=2 "/path/to/面试稳伴随程序.app"
spctl --assess --type execute --verbose "/path/to/面试稳伴随程序.app"
xcrun stapler validate "/path/to/面试稳伴随程序.app"
spctl --assess --type open --context context:primary-signature --verbose "/path/to/OfferSteady-Companion.dmg"
xcrun stapler validate "/path/to/OfferSteady-Companion.dmg"
```

计划分发三个独立安装包：macOS Apple Silicon arm64、macOS Intel x64、Windows 10/11 x64。Windows ARM64、Linux 和移动原生伴随程序不在当前范围。

发布清单分别记录运营发布状态 `distributionStatus` 与技术签名状态 `signingStatus`。运营负责人确认当前安装包可作为正式产品分发后，将其标为 `published`；网页可以提供下载，但不得把尚未完成的 Developer ID 签名、公证或 Windows 代码签名描述为“已验证”。校验值缺失、内部使用、失败或被撤回的包不能显示下载按钮。

未签名或 ad-hoc 包的技术状态保留为 `local-development`。取得证书并通过真实设备验证后，发布负责人再把签名状态切换为 `verified`；这个过程不需要撤销运营方已经确认的 `published` 分发状态。

## 本机开发版下载

当前 Apple Silicon Mac 可用本机开发版 zip 进行端到端调试：

```bash
npm run package:mac:arm64 -w @offersteady/desktop
```

macOS Intel x64 测试包：

```bash
npm run package:mac:x64 -w @offersteady/desktop
```

Windows 10/11 x64 免安装测试包：

```bash
CSC_IDENTITY_AUTO_DISCOVERY=false npm run package:win:x64 -w @offersteady/desktop
```

面向用户的 Windows NSIS 安装包：

```bash
npm run package:win:installer:x64 -w @offersteady/desktop
```

安装版是单个 `OfferSteady-Companion-Setup-<version>-Windows-x64.exe`，支持安装目录选择、桌面快捷方式、开始菜单和系统卸载入口。Intel 命令会显式编译 x86_64 Swift 采集运行时并下载 x64 Electron，Windows 使用 Electron/Chromium 的 WASAPI loopback 捕获电脑输出。在取得 Windows 代码签名证书前，安装程序仍必须标记为未签名测试版。

该命令会生成：

- `apps/desktop/release/mac-arm64/OfferSteady-Companion-0.1.0-macOS-arm64/面试稳伴随程序.app`
- `apps/desktop/release/mac-arm64/OfferSteady-Companion-0.1.0-macOS-arm64/打开说明.txt`
- `apps/desktop/release/OfferSteady-Companion-0.1.0-macOS-arm64.zip`
- `apps/desktop/release/OfferSteady-Companion-0.1.0-macOS-arm64.json`

后端 `GET /api/v1/web/state` 会读取本地元数据，并在设备下载页展示“macOS Apple Silicon 本机开发版”。下载地址由后端提供，例如：

```text
http://127.0.0.1:8000/api/v1/web/downloads/desktop/OfferSteady-Companion-0.1.0-macOS-arm64.zip
```

发布任意平台包时传入对应元数据文件：

```bash
python3 scripts/publish-desktop-release.py \
  --metadata apps/desktop/release/OfferSteady-Companion-0.1.0-Windows-x64.json
```

OSS 路径统一为 `desktop-releases/{platform}/{architecture}/{version}/{filename}`。发布器只替换相同平台和架构的条目，不会覆盖已经发布的其他系统版本。

本机开发版会进行 ad-hoc 签名，保证包结构和本机启动可用，但它不是 Apple Developer ID 正式签名/公证发行版。若 macOS 提示无法验证开发者，可在“系统设置 → 隐私与安全性”中允许打开，或右键 App 选择“打开”。如果从 Codex/某些终端环境直接启动，需要确保没有设置 `ELECTRON_RUN_AS_NODE=1`；普通双击和页面下载后的打开不应携带该变量。

## 本地联调诊断

桌面伴随助手与网页联调时，先确认 Web 和桌面指向同一个后端地址。桌面默认后端为：

```text
http://127.0.0.1:8000/api/v1
```

打包后的本地助手默认连接线上服务：`https://mianshiwen.cn/app` 和 `https://mianshiwen.cn/api/v1`。开发模式仍默认连接本地：`http://localhost:5173/app` 和 `http://127.0.0.1:8000/api/v1`。

如果网页或手机端使用了局域网地址，或者需要让助手连接本地开发后端，需要同时设置桌面环境变量 `OFFERSTEADY_API_BASE_URL`，否则会出现“网页绑定了机器码，但助手仍显示未连接”的错位。

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

### 空闲轮询与服务端负载

远程截图请求只由 Electron 主进程处理。renderer 负责展示绑定和音频状态，不得并行获取下一笔截图任务。当前助手在设备已登记、绑定有效且 session 为 `live` 时保持一条可取消的 SSE 订阅；快捷键创建成功后会直接处理响应中的请求 ID，不再等待下一轮查询。

`GET /api/v1/screenshot-answer/desktop-devices/<deviceId>/capture-requests/next` 只保留给旧版助手和推送断线恢复。新版助手仅在 SSE 异常后执行一次非重叠回退查询，然后按退避策略重连；健康推送期间不得轮询。未登记、未绑定、绑定失效、非 live 和暂无截图统一返回 HTTP 200 与空 `data`，不应记录为 `desktop-capture-binding` 告警。截图上传、失败回报和快捷键创建等写操作仍必须执行严格设备与绑定校验。

发布后应同时观察设备 SSE 连接数、请求到领取延迟、回退查询次数、`desktop-capture-binding` 告警和 PostgreSQL deadlock。健康连接的回退查询次数应接近零，空闲设备不应保持一秒级请求，绑定/截图查询也不得更新面试业务活动时间。回滚时可继续使用兼容的 `next` 接口，无需回滚数据库结构。

下载包名称不代表运行能力。客户端连接后仍需报告麦克风、系统音频和协议能力；Windows 系统音频不可用时，网页保留麦克风、手动输入和截图路径。支持的最低 Windows 版本将在物理设备验证后从 Windows 10 22H2 或 Windows 11 中确定。

撤回故障版本时从发布清单移除下载地址并保留审计记录；已安装客户端收到安全升级提示。回滚不得重新开放未签名或已知受损的构建。
