## ADDED Requirements

### Requirement: Pair a second device
系统 SHALL 允许用户通过同一账号中的进行中会话，或通过短期二维码和 6 位配对码，将第二台已授权设备加入当前面试会话。

#### Scenario: Pairing succeeds
- **WHEN** 已登录用户在配对码有效期内确认加入正确会话
- **THEN** 系统将设备加入会话并向现有设备展示新的在线设备

#### Scenario: Pairing code is invalid
- **WHEN** 用户提交错误、过期或已使用的配对码
- **THEN** 系统拒绝加入且不泄露会话是否存在或会话内容

### Requirement: Synchronize core session state
系统 MUST 在已连接设备之间同步会话状态、当前问题、回答增量、回答完成状态、资料就绪状态、截图任务状态和设备列表。

#### Scenario: Session pauses on one device
- **WHEN** 服务端接受任一有权限设备的暂停命令
- **THEN** 正常网络条件下所有在线设备在 2 秒内显示已暂停状态

#### Scenario: Answer streams to devices
- **WHEN** 服务端产生新的回答增量
- **THEN** 所有在线且有权限的设备按相同顺序追加增量且不重复内容

### Requirement: Maintain an authoritative versioned state
系统 SHALL 由服务端维护权威会话状态，并 MUST 为命令分配唯一标识、为已确认事件分配递增版本。

#### Scenario: Command is delivered twice
- **WHEN** 同一个命令 ID 因重试被服务端接收多次
- **THEN** 服务端只应用一次状态变化并返回相同的确认结果

#### Scenario: Clients issue conflicting commands
- **WHEN** 两台设备基于过期版本提交冲突状态变更
- **THEN** 服务端按当前权威状态处理或拒绝冲突，并向客户端返回最新版本

### Requirement: Control the primary input device
每场进行中的面试会话 MUST 最多只有一个主要输入设备，且所有设备 SHALL 明确展示当前主要输入设备。

#### Scenario: User switches primary input device
- **WHEN** 用户在目标设备确认接管输入
- **THEN** 系统先停止旧设备采集，再激活新设备并同步角色变化

#### Scenario: Secondary device attempts automatic capture
- **WHEN** 非主要输入设备尝试启动自动实时采集
- **THEN** 系统阻止采集并提供申请切换角色的入口

### Requirement: Recover after disconnection
系统 SHALL 在设备重连时根据最后确认版本恢复缺失事件或最新快照，且 MUST 避免重复问题与回答。

#### Scenario: Device reconnects with recent version
- **WHEN** 离线设备携带最后确认版本重新连接
- **THEN** 服务端发送缺失事件并将设备恢复到当前会话状态

#### Scenario: Event history is unavailable
- **WHEN** 服务端无法提供设备缺失的完整事件序列
- **THEN** 服务端发送最新完整快照并要求客户端替换本地共享状态

### Requirement: Remove a paired device
系统 MUST 允许用户查看并移除已配对设备，移除后该设备 SHALL 立即失去后续会话事件访问权限。

#### Scenario: User removes companion device
- **WHEN** 用户确认从会话移除某台伴随设备
- **THEN** 服务端撤销其会话权限、关闭实时连接并同步更新设备列表

### Requirement: Minimize synchronized sensitive data
系统 MUST 只向已授权设备同步渲染当前界面所需的数据，并 MUST 不在跨设备事件中发送服务端密钥、无关原始文档或完整检索索引。

#### Scenario: Mobile requests current answer
- **WHEN** 已配对手机进入现场页面
- **THEN** 系统只返回当前会话所需的问题、回答、来源摘要和控制状态
