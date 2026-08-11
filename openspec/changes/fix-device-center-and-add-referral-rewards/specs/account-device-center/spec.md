## ADDED Requirements

### Requirement: Device center lists real account devices
设备中心 SHALL 从服务端读取当前登录账号已关联的桌面设备，MUST NOT 使用准备页 fixture 或固定在线文案代替真实数据。每项设备 SHALL 展示安全设备摘要、平台、最近活动和在线状态。

#### Scenario: Account has linked devices
- **WHEN** 用户打开设备中心且账号已关联一台或多台设备
- **THEN** 页面展示服务端返回的设备列表、掩码机器码、平台、最后活动时间以及各自在线或离线状态

#### Scenario: Account has no linked device
- **WHEN** 当前账号从未成功连接桌面助手
- **THEN** 页面展示真实空状态、下载助手和输入机器码的下一步说明，不渲染合成设备

### Requirement: Device states remain independent
系统 MUST 分别表达账号关联、设备在线、助手权限/能力和当前面试连接。客户端 MUST NOT 因为账号已关联就显示设备在线，也 MUST NOT 因为当前没有面试 lease 就显示系统权限失效。

#### Scenario: Linked device is offline
- **WHEN** 账号设备关系仍存在但设备心跳已经过期
- **THEN** 设备中心显示“已关联 · 离线”和最后活动时间，不显示“在线”或“正在收音”

#### Scenario: Device is online without active interview
- **WHEN** 助手在线且权限已授权，但没有活动面试连接
- **THEN** 设备中心显示设备可用和“当前未连接面试”，不把它描述为未授权

#### Scenario: Permission is missing
- **WHEN** 在线助手报告麦克风、系统音频或屏幕权限缺失
- **THEN** 页面逐项显示缺失能力和在桌面助手或系统设置中处理的指引，网页不请求对应浏览器媒体权限

### Requirement: Device center provides truthful refresh and diagnostics
设备中心 SHALL 提供重新读取权威状态的刷新操作和可展开的诊断信息。诊断 SHALL 只展示连接与权限事实、最后心跳及恢复入口，MUST NOT 在没有用户开始面试的情况下远程启动收音。

#### Scenario: User refreshes device status
- **WHEN** 用户点击刷新
- **THEN** 页面重新请求设备列表并显示加载、成功或可重试失败状态

#### Scenario: User opens diagnostics
- **WHEN** 用户点击某台设备的诊断操作
- **THEN** 页面显示最后心跳、权限/能力和当前面试连接摘要，并提供对应使用说明入口

### Requirement: Device list is account isolated
设备列表接口 MUST 使用认证账号作为所有权边界，不接受客户端指定其他 user ID，也不得返回机器码原文、其他账号关系或面试内容。

#### Scenario: Authenticated user requests devices
- **WHEN** 登录用户读取设备中心数据
- **THEN** 服务端只返回该用户的安全设备摘要并掩码连接码

