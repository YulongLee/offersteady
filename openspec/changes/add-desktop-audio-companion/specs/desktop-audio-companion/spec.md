## ADDED Requirements

### Requirement: Discover and download the desktop companion
Web 应用 SHALL 在电脑端提供桌面伴随程序下载入口，并 MUST 展示检测到的平台、支持范围、版本和安装用途。

#### Scenario: Supported platform detected
- **WHEN** 用户在受支持的电脑平台打开下载页面
- **THEN** 系统推荐匹配的签名安装包并提供其他平台的手动选择入口

#### Scenario: Unsupported platform detected
- **WHEN** 用户的平台或系统版本不受支持
- **THEN** 系统不提供错误安装包，并展示浏览器麦克风、手动问题或其他可用替代方式

### Requirement: Request explicit operating-system permissions
桌面伴随程序 MUST 在采集前分别请求所需的麦克风和系统音频权限，并 SHALL 解释每项权限的用途和当前状态。

#### Scenario: Permission granted
- **WHEN** 用户授予所选音频来源所需权限
- **THEN** 程序将该来源标记为可用并允许进行音量测试

#### Scenario: Permission denied
- **WHEN** 用户拒绝或撤销权限
- **THEN** 程序不采集该来源，并提供打开系统设置或选择其他输入方式的指引

### Requirement: Support Intel and Apple Silicon Macs
桌面伴随程序 SHALL 提供一个同时包含 x64 与 arm64 架构的 universal macOS 安装包，并 MUST 在 Intel Mac 与 Apple Silicon Mac 上原生运行。

#### Scenario: Apple Silicon user downloads companion
- **WHEN** Apple Silicon Mac 用户从 Web 页面下载安装 universal 版本
- **THEN** 程序使用 arm64 架构原生启动且无需 Rosetta 2

#### Scenario: Intel user downloads companion
- **WHEN** Intel Mac 用户从 Web 页面下载安装同一 universal 版本
- **THEN** 程序使用 x64 架构原生启动

### Requirement: Select and test audio sources
桌面伴随程序 SHALL 允许用户选择受支持的麦克风、系统音频或组合来源，并在开始面试前展示实时音量诊断。

#### Scenario: Audio source is working
- **WHEN** 用户选择有有效输入信号的来源
- **THEN** 程序展示对应来源名称和持续更新的音量指示，但不在未开始会话时向服务端发送音频

#### Scenario: Audio source is silent or unavailable
- **WHEN** 所选来源无信号、被占用或已断开
- **THEN** 程序显示可操作的错误状态并阻止把该来源标记为已就绪

### Requirement: Provide visible capture controls
桌面伴随程序 MUST 只在用户显式开始后采集，并 MUST 持续显示采集中、暂停、重连或错误状态以及停止入口。

#### Scenario: User starts capture
- **WHEN** 设备已绑定、权限已授予且用户点击“开始面试”
- **THEN** 程序进入采集中状态、显示持续可见指示并开始发送所选来源

#### Scenario: User pauses capture
- **WHEN** 用户点击暂停
- **THEN** 程序停止发送新音频并在本地与 Web 页面显示已暂停

#### Scenario: User stops capture
- **WHEN** 用户点击停止或结束会话
- **THEN** 程序立即停止采集和发送，并清理未发送的临时音频缓冲

### Requirement: Prevent hidden collection
桌面伴随程序 MUST NOT 提供隐藏采集指示、绕过系统权限、静默自动开始或无法由用户停止的模式。

#### Scenario: Application restarts
- **WHEN** 桌面程序在之前的会话期间退出后重新启动
- **THEN** 程序保持非采集状态，直到用户重新确认会话和开始操作

### Requirement: Report capability and version
桌面伴随程序 SHALL 在绑定时报告应用版本、操作系统、可用音频来源能力和权限状态，且 MUST 不上传无关设备信息。

#### Scenario: Companion version is incompatible
- **WHEN** 服务端判定当前程序版本与会话协议不兼容
- **THEN** 程序阻止采集并展示来自可信下载源的升级指引
