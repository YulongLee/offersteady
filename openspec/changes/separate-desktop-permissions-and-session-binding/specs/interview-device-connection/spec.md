## ADDED Requirements

### Requirement: Connect a new interview with a machine code
新建面试的准备页 SHALL 提供机器码输入，并在校验设备在线、机器码正确和账号权限后为本场建立实时 lease。连接成功的设备 SHALL 同时成为当前账号最近使用设备。

#### Scenario: New interview connects successfully
- **WHEN** 用户在新面试准备页输入当前助手的有效机器码
- **THEN** 系统建立本场 lease、显示已连接设备并允许开始实时采集

#### Scenario: Machine code is unavailable
- **WHEN** 机器码无效、设备离线或已被其他账号占用
- **THEN** 系统不建立 lease，并显示设备连接错误而不是系统权限错误

### Requirement: Reconnect a historical interview by choice
用户打开历史面试时 SHALL 能够选择“一键连接上次设备”或“重新输入机器码”。一键连接 MUST 使用当前账号最近成功绑定且在线的设备；失败后 SHALL 保留机器码连接入口。

#### Scenario: Last device is online
- **WHEN** 用户在历史面试中点击“一键连接上次设备”且最近设备在线
- **THEN** 系统无需再次输入机器码即可为该历史面试建立新的实时 lease

#### Scenario: Last device is offline
- **WHEN** 用户点击一键连接但最近设备离线或已解除账号关系
- **THEN** 系统说明最近设备不可用并展示重新输入机器码入口

#### Scenario: User chooses another device
- **WHEN** 用户选择重新输入机器码并连接另一台有效设备
- **THEN** 系统将新设备连接到当前面试并更新账号最近设备

### Requirement: Enforce one active interview connection
系统 SHALL 对每个用户和桌面设备最多保留一个活动面试 lease。建立新 lease 时 MUST 原子撤销冲突的旧 lease，但 MUST NOT 删除长期账号设备关系。

#### Scenario: New interview takes over the device
- **WHEN** 用户已有一场活动面试并为另一场面试连接同一设备
- **THEN** 系统关闭旧 lease、建立新 lease并让旧页面显示已被接管

#### Scenario: Duplicate connect request
- **WHEN** 同一面试对同一设备重复发送连接请求
- **THEN** 系统幂等返回现有 lease，不创建重复采集进程或发布通道

#### Scenario: An old browser tab keeps its realtime page open
- **WHEN** 新面试接管活动 lease 后旧面试页面仍保持打开
- **THEN** 后端向旧实时流发布不可重试的撤销终态，旧页面立即关闭订阅、心跳和轮询且不得再次连接

#### Scenario: An ended session attempts to open a realtime stream
- **WHEN** 已结束或已被接管的 session 请求建立实时订阅
- **THEN** 后端在创建流之前返回不可重试的终态，不加载完整实时快照
