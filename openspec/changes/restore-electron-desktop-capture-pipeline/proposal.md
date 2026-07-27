## Why

当前 macOS 助手同时存在 Electron、Swift Helper 和遗留主进程音频路径，导致界面可以显示电脑输出波动，但正式实时发布通道没有稳定收到音频帧。现阶段产品不使用 Developer ID 签名，独立 Helper 的权限身份无法稳定复用主助手授权，因此需要恢复由 Electron 主助手统一采集和发布的单一链路。

## What Changes

- **BREAKING**：停止使用 Swift Helper 作为正式麦克风和电脑输出采集、发布所有者。
- Electron 主助手统一采集麦克风、电脑输出和屏幕，并通过现有实时语音协议发布双通道音频。
- 同一桌面会话只允许一个采集监督器和一个实时发布器，禁止本地监视器、主进程遗留发布器和正式发布器重复占用音频源。
- 麦克风继续映射为候选人，电脑输出继续映射为面试官；网页只消费后端转写事件，不再次申请音频权限。
- 在助手进入面试前提供真实媒体门禁：必须区分权限缺失、无音轨、静音和服务端未接收，不以 UI 波动代替链路可用性。
- 保留 Swift Helper 源码作为后续签名商业版本的可选实现，但不随当前无证书版本启动或拥有采集资源。
- 保持原始音频短暂内存处理，不默认落盘，不在诊断日志中记录音频或转写正文。

## Capabilities

### New Capabilities

- `electron-desktop-capture-owner`: 定义无 Developer ID 阶段由 Electron 主助手单独拥有麦克风、电脑输出和屏幕采集的行为、权限和互斥要求。
- `desktop-dual-channel-publishing`: 定义单一桌面发布器向实时服务发送候选人和面试官双通道音频并提供真实健康状态的行为。

### Modified Capabilities

<!-- No main-spec requirement is modified; this change supersedes active, unarchived native-capture planning artifacts. -->

## Impact

- 影响 `apps/desktop` 的 Electron 主进程显示媒体处理、renderer 音频适配器、实时发布器、权限状态和打包脚本。
- 保持现有后端实时语音 API、WebSocket/HTTP 兼容协议、ASR 角色映射和网页实时对话消费契约不变。
- 当前 macOS arm64 安装包不再依赖 Swift Helper 完成正式音频采集；未来切换回原生采集必须使用稳定签名并通过新的架构变更。
- 需要更新桌面回归测试、真实媒体诊断和发布包清单，并完成麦克风、电脑输出、双通道发布与网页转写联合验收。
