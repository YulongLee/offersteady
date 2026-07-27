## Context

当前桌面程序同时包含三套可能拥有音频资源的实现：renderer WebAudio、Swift ScreenCaptureKit Helper、main process 遗留 HTTP 发布。正式 publisher 会优先启动 Helper，失败后回退 Electron；未进入 live 时本地 monitor 又会单独打开媒体源。无 Developer ID 签名时，Helper 与主应用的 TCC 身份不稳定，真实运行中出现“本地电平有波动，但后端没有 interviewer 音频帧”的分裂状态。

当前版本需要优先保证用户可理解、可授权、可诊断的内测链路。用户接受首次运行时自行授予 macOS 麦克风和屏幕与系统音频录制权限，但暂不申请 Apple 商业签名。

## Goals / Non-Goals

**Goals:**

- Electron renderer 是当前 macOS 版本唯一的音频采集和实时发布所有者。
- 同一面试只创建一个 publisher，其中分别维护 microphone/candidate 与 system/interviewer 两个逻辑通道。
- 本地空闲监视与 live 发布互斥，切换时先释放旧媒体轨道再创建正式发布器。
- 主进程统一选择屏幕源并向 Electron display media 请求提供 loopback 音轨。
- 真实健康状态区分媒体轨道、电平、帧数、后端接收和 ASR 状态。
- 保留现有后端协议和网页消费行为，减少上线范围。

**Non-Goals:**

- 不绕过 macOS TCC，也不承诺无签名应用更新后永久保留授权。
- 不在本变更申请 Developer ID、完成 notarization 或发布 Mac App Store。
- 不修改 ASR 供应商、网页实时对话布局、截图回答链路或面试业务数据。
- 不删除 Swift Helper 源码；它只退出当前正式运行和打包依赖。

## Decisions

### 1. Electron renderer owns both audio channels

`DesktopRealtimePublisher` 直接使用 `MicrophoneAudioAdapter` 和 `SystemAudioAdapter`。启动 live publisher 时不调用 `startNativeAudioStream`，也不订阅 native JSONL frame。两个适配器产生相同的 PCM frame contract，继续复用现有队列、分段、publisher token 和上传逻辑。

Alternative considered: 修复 Helper 的 bundle identity。无稳定签名时每次构建仍可能产生新的 TCC 身份，不能满足当前内测迭代速度。

### 2. Use Electron display media loopback for system output

renderer 请求 display media，main process 的 `setDisplayMediaRequestHandler` 选择当前屏幕源，并在请求音频时返回 `audio: "loopback"`。系统输出适配器只保留音频轨道并立即停止不需要的视频轨道。屏幕预览和截图仍复用同一个主应用权限身份。

Alternative considered: 虚拟声卡。它可以作为未来兼容方案，但增加安装和路由配置成本，不作为当前默认路径。

### 3. Remove production fallback chains

当前包不自动尝试 Helper，也不启用遗留 main-process HTTP audio publisher。失败时返回 Electron 路径的真实错误，不静默切换到第二个所有者。`OFFERSTEADY_ENABLE_LEGACY_MAIN_AUDIO` 不再影响正式包。

Alternative considered: 保留自动 fallback。它会再次造成重复 publisher、难以归因的权限提示和源资源竞争。

### 4. Enforce monitor-to-live handoff

空闲状态允许一个本地 monitor 提供用户可见电平。会话变为 live 后先停止 monitor、等待媒体轨道关闭，再启动 publisher。publisher 生命周期使用稳定的 session/binding identity，React 状态刷新不得重复创建实例。

Alternative considered: monitor 与 publisher 共享一个 MediaStream。共享生命周期会让 UI 状态和正式上传紧耦合，当前阶段实现风险更大。

### 5. Keep server protocol and role mapping unchanged

Electron 采集帧继续按 `microphone` 与 `system` 创建 publisher；后端分别映射 `candidate` 与 `interviewer`。服务端保持单会话、单来源权威 publisher 的替换和恢复规则，网页继续消费有序转写事件。

Alternative considered: 合并为 mixed channel 后做 diarization。它会降低角色准确性并扩大后端改动，不符合本轮修复范围。

### 6. Treat unsigned permission persistence as an explicit beta limitation

安装包使用固定 bundle identifier，首次运行引导用户向主助手授予麦克风与屏幕和系统音频录制权限。诊断与 UI 必须说明拒绝或缺失权限，不把无音轨表述为后端故障。正式商业发布仍需要 Developer ID 和 notarization。

## Risks / Trade-offs

- [Electron loopback 在部分 macOS/Electron 组合下可能拿不到音轨] → 固定受支持版本，增加真实音轨门禁和清晰错误；未来可通过签名原生 runtime 或虚拟声卡变更解决。
- [无签名重建可能导致 TCC 重新授权] → 保持固定 bundle id，减少不必要重建，并在每个测试包明确执行一次授权检查。
- [屏幕与系统音频共用 display media 权限] → 用户明确授权，视频轨道在纯音频路径中立即停止，原始媒体不落盘。
- [monitor 到 publisher 切换存在短暂空窗] → 串行停止和启动，并通过 UI 显示正在建立实时发布通道。
- [保留未使用 Helper 源码可能引起维护混淆] → 打包清单和运行状态明确声明 `electron-display-loopback`，后续签名方案单独提案。

## Migration Plan

1. 更新 Specs 和回归测试，固定单一 Electron 所有权。
2. 删除 publisher 的 native-first 分支，关闭 main process 遗留发布启动。
3. 调整 display media handler、权限请求和健康状态。
4. 构建 macOS arm64 包，执行桌面单测、类型检查和真实媒体诊断。
5. 使用合成音频验证双通道后端发布与角色映射；使用本机播放音频完成真实系统输出验收。
6. 更新下载包与 release manifest，部署后端和网页静态资源。

Rollback: 保留上一个安装包和服务端兼容协议。若 Electron loopback 在目标设备无法建立音轨，可回滚桌面下载包；后端与网页无需回滚。

## Open Questions

- 正式商业版本采用签名后的 Electron loopback，还是重新启用签名 Swift ScreenCaptureKit runtime。
- 是否需要为不支持 loopback 的设备提供可选虚拟音频驱动安装流程。
