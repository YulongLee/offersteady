## ADDED Requirements

### Requirement: Bind the companion to a Web session
系统 SHALL 允许 Web 会话签发短期、一次性的桌面设备绑定凭证，并 MUST 将交换后的设备权限限制在指定用户、会话和音频操作范围内。

#### Scenario: Deep-link binding succeeds
- **WHEN** 用户从 Web 页面使用有效深链唤起桌面程序并确认绑定
- **THEN** 服务端为该桌面设备签发受限凭证并在所有 Web 设备中显示其在线状态

#### Scenario: Binding token is invalid
- **WHEN** 桌面程序提交错误、过期、已使用或会话不匹配的绑定凭证
- **THEN** 服务端拒绝绑定且不返回会话敏感内容

### Requirement: Transmit ordered audio sources securely
桌面程序 MUST 通过加密连接发送带设备、来源、序列号和时间戳的音频帧，并 SHALL 在可用时保持麦克风与系统音频来源独立。

#### Scenario: Audio frames arrive normally
- **WHEN** 服务端收到连续且有效的音频帧
- **THEN** 服务端按设备和来源顺序交给转录管线，并确认已接受的序列位置

#### Scenario: Duplicate frame arrives
- **WHEN** 服务端收到已经接受过的设备、来源和序列号组合
- **THEN** 服务端丢弃重复帧且不产生重复转录内容

### Requirement: Synchronize collection status to Web clients
系统 SHALL 将桌面设备的在线、权限、就绪、采集中、暂停、重连和错误状态同步到当前会话的所有已授权 Web 客户端。

#### Scenario: Desktop capture starts
- **WHEN** 服务端确认桌面程序开始发送音频
- **THEN** 电脑和手机 Web 页面显示该设备、输入来源和采集中状态

#### Scenario: Desktop connection is lost
- **WHEN** 服务端在规定心跳窗口内未收到桌面程序连接状态
- **THEN** Web 页面显示连接中断且不继续宣称正在稳定收音

### Requirement: Recover a transient connection
桌面程序 SHALL 使用有界内存缓冲处理短暂网络中断，并在重连后根据服务端确认位置补发未确认音频，且 MUST 防止无限缓冲。

#### Scenario: Connection recovers within buffer capacity
- **WHEN** 网络在未确认音频仍处于内存缓冲时恢复
- **THEN** 程序按原始序列补发未确认帧并恢复实时发送

#### Scenario: Buffer capacity is exceeded
- **WHEN** 网络中断持续到内存缓冲无法容纳更多音频
- **THEN** 程序丢弃超出策略的音频、停止声称连续采集并向 Web 页面报告音频缺口

### Requirement: Stream transcript events into the interview session
系统 SHALL 将实时转录适配器产生的已确认文本片段发布为当前面试会话事件，并 MUST 保留音频来源与时间范围关联。

#### Scenario: Interviewer question is transcribed
- **WHEN** 系统音频来源产生可识别且已确认的问题文本
- **THEN** 系统将文本作为带来源和时间范围的会话输入交给问题识别流程

#### Scenario: Transcription is uncertain
- **WHEN** 转录结果未达到可回答的置信或完整性要求
- **THEN** 系统显示问题内容不清晰并保留手动提问路径，且不自动触发可靠回答标记或第三角色

### Requirement: Revoke desktop device access
Web 应用 MUST 允许用户立即撤销已绑定桌面设备，撤销后服务端 SHALL 拒绝其后续连接、音频和状态事件。

#### Scenario: User revokes companion
- **WHEN** 用户在任一已授权 Web 设备确认移除桌面伴随程序
- **THEN** 服务端撤销设备凭证、关闭其连接并同步设备已移除状态

### Requirement: Minimize raw audio retention
系统 MUST 默认以流式短暂方式处理原始音频，不在桌面本地写入录音文件，也不在服务端长期保存原始音频。

#### Scenario: Session ends under default policy
- **WHEN** 用户结束面试且没有经过明确产品流程选择允许的其他保存策略
- **THEN** 桌面程序清理内存缓冲，服务端完成短暂处理后删除原始音频数据

### Requirement: Separate adapter-specific data
服务端 SHALL 通过可替换转录适配器处理音频，并 MUST 只向所选第三方发送完成当前转录所需的最小数据。

#### Scenario: Transcription provider is replaced
- **WHEN** 系统配置切换到另一个符合接口的转录适配器
- **THEN** 会话桥接协议和 Web 客户端行为无需改变
