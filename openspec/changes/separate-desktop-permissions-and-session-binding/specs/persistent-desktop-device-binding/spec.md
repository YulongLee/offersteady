## ADDED Requirements

### Requirement: Preserve desktop identity and account association
系统 SHALL 为同一桌面安装保持稳定的设备 ID 和机器码，并 SHALL 在用户成功连接设备后持久保存账号与设备关系及最近使用设备。创建、结束或恢复面试 MUST NOT 删除该关系。

#### Scenario: User connects a device for the first time
- **WHEN** 当前账号使用有效机器码成功连接在线桌面助手
- **THEN** 系统保存账号设备关系并将该设备记录为最近使用设备

#### Scenario: Interview ends
- **WHEN** 用户结束当前面试
- **THEN** 系统撤销本场连接但保留账号设备关系、设备 ID、机器码和最近设备记录

### Requirement: Keep operating-system permissions desktop-owned
麦克风、屏幕录制、系统输出和截图权限 MUST 由桌面助手在首次使用相应能力时向 macOS 请求。Web MUST NOT 请求浏览器麦克风或屏幕权限来替代助手权限，也 MUST NOT 把会话未连接描述为系统未授权。

#### Scenario: Permission was previously granted
- **WHEN** 同一代码身份的助手再次启动且 macOS 仍报告权限已授权
- **THEN** 助手直接复用该权限且网页不再展示授权操作

#### Scenario: Local companion is rebuilt during development
- **WHEN** 本地开发版主应用或原生采集 helper 被重新构建
- **THEN** 两者保持稳定 Bundle ID 和指定代码要求，macOS 不因构建产物哈希变化而把同一安装识别为随机新程序

#### Scenario: Companion connection management is displayed
- **WHEN** 用户打开助手并查看固定连接码
- **THEN** 连接码旁直接提供打开或进入当前面试的操作，不再展示重复的设备状态、权限状态、连接详情和音频路由说明面板

#### Scenario: Session is not connected
- **WHEN** 助手权限已授权但当前面试尚未建立连接
- **THEN** Web 展示“尚未连接本场面试”而不是“麦克风未授权”或“截图未授权”

#### Scenario: Permission is denied by macOS
- **WHEN** 助手报告某项系统权限为 denied 或 not-determined
- **THEN** Web 仅展示前往桌面助手或系统设置处理的说明，不在网页发起对应媒体权限请求

### Requirement: Expose independent permission, presence and connection states
桌面端和后端 SHALL 独立提供系统权限、设备在线状态、账号绑定状态和当前面试连接状态，客户端 MUST NOT 使用单一布尔值推断其他层状态。

#### Scenario: Device is ready but idle
- **WHEN** 助手已授权、在线且属于当前账号，但没有活动面试
- **THEN** 系统报告设备可用且当前面试连接为空

#### Scenario: Device disconnects during an interview
- **WHEN** 当前面试 lease 仍有效但设备 presence 过期
- **THEN** 系统报告设备离线和会话等待重连，不改变其系统权限记录或账号设备关系
