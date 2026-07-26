## ADDED Requirements

### Requirement: User explicitly selects the desktop device for each interview
准备页 SHALL 由用户选择连接上次设备或输入新的六位机器码。系统 MUST NOT 因为历史面试曾经绑定设备而自动把该历史 binding 当作本场有效连接。

#### Scenario: User connects the last device
- **WHEN** 当前用户存在最近使用且在线的设备，并点击“一键连接上次设备”
- **THEN** 系统为当前面试创建新的 binding，并显示该设备已经连接到本场

#### Scenario: User enters another machine code
- **WHEN** 用户输入有效的六位机器码并确认连接
- **THEN** 系统校验对应在线设备并为当前面试创建新的 binding

#### Scenario: No reusable device is online
- **WHEN** 当前用户没有在线的最近设备
- **THEN** 系统禁用一键连接并引导用户打开助手后输入机器码

### Requirement: Only one realtime interview is active per user
系统 SHALL 保证一个用户同一时间只有一个 `bound` 实时面试连接。新 binding 创建时 MUST 使该用户其他 session 的 binding 和 publisher 永久失效，但 MUST NOT 删除历史面试业务记录。

#### Scenario: User switches to a new interview
- **WHEN** 用户已在面试 A 使用设备并为面试 B 发起连接
- **THEN** 面试 A 的 binding 变为 stale、publisher 被关闭，面试 B 成为唯一 active binding

#### Scenario: Old publisher reconnects
- **WHEN** 已被替换的 publisher 再次连接或上传音频
- **THEN** 服务端返回永久失效结果，且音频不会进入新面试或旧面试字幕

### Requirement: Desktop follows the latest binding without reusing stale publishers
桌面助手 SHALL 以 binding identity 管理 publisher 生命周期。binding 变化时 MUST 停止旧连接并为新 binding 创建 publisher；永久失效错误 MUST NOT 使用旧 token 重试。

#### Scenario: Binding changes while assistant remains open
- **WHEN** pairing status 返回新的 bindingId、sessionId 或 bindingGeneration
- **THEN** 助手清理旧 publisher、音频队列和重连计时器，并为新 binding 建立通道

#### Scenario: Network disconnect is temporary
- **WHEN** 当前有效 publisher 发生普通网络断开
- **THEN** 助手使用有界指数退避恢复同一 publisher，且不创建并行重连循环

### Requirement: Old web sessions stop consuming realtime updates
网页 SHALL 只订阅当前 session。当前 session 返回身份错误、资源不存在或已被替换时，页面 MUST 终止对应订阅、轮询和重连计时器。

#### Scenario: Another interview replaces the current session
- **WHEN** 旧面试实时订阅收到 `401`、`403`、`404` 或 session-replaced 响应
- **THEN** 页面停止旧订阅并返回面试入口，不再持续请求该 session
