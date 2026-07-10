## ADDED Requirements

### Requirement: Derive the two displayed roles from audio source
在受支持的双声道面试中，系统 MUST 只展示 `我` 和 `面试官` 两种对话角色。选定的本地麦克风或耳机输入 MUST 映射为 `我`，电脑系统音频 MUST 映射为 `面试官`；系统不得根据声纹、语言模型猜测或用户纠正改变该显示映射。

#### Scenario: Local microphone is transcribed
- **WHEN** 选定的 Mac 本地麦克风或耳机输入产生转录片段
- **THEN** 实时对话将该片段显示为“我”且不提供角色修改操作

#### Scenario: System audio is transcribed
- **WHEN** 电脑系统音频产生远端参与者的转录片段
- **THEN** 实时对话将该片段显示为“面试官”且不显示编号或第三种角色

#### Scenario: Multiple remote people speak
- **WHEN** 系统音频中先后出现多个远端说话人
- **THEN** 所有可展示片段均归入“面试官”角色，内部匿名 speaker ID 不作为新的用户角色展示

### Requirement: Remove role-pending interaction from the live workspace
Web 实时页 MUST NOT 显示“角色待确认”、角色置信度、“设为面试官”或“设为我”操作。旧协议中的 `unknown` 角色事件 MUST 进入兼容隔离或输入降级流程，不得直接显示成第三个对话角色。

#### Scenario: A new dual-channel segment arrives
- **WHEN** 新客户端发送带有效 `microphone` 或 `system` 来源的转录事件
- **THEN** Web 直接使用来源映射显示“我”或“面试官”，无需角色确认步骤

#### Scenario: A legacy unknown-role event arrives
- **WHEN** Web 收到缺少可信来源映射的旧版 `unknown` 角色事件
- **THEN** 系统不把该事件显示为“角色待确认”对话轮次、不自动触发回答，并展示可操作的输入降级状态

### Requirement: Trigger automatic answers only from interviewer-source questions
系统 MUST 只允许电脑系统音频中完成边界判断、文本置信度和问题意图检查的片段自动创建回答。来自本地麦克风或耳机输入的候选人陈述、反问、回声和跨声道重复内容 MUST NOT 自动创建回答或计费用量。

#### Scenario: Interviewer asks a complete question
- **WHEN** 系统音频产生一条最终、完整、未重复且可回答的面试官问题
- **THEN** 系统为该问题发布一次确认事件并创建唯一回答任务

#### Scenario: Candidate is answering
- **WHEN** 本地麦克风或耳机输入持续产生候选人陈述或澄清反问
- **THEN** 系统继续显示为“我”但不自动创建回答任务或积分预留

#### Scenario: Candidate voice echoes into system audio
- **WHEN** 本地候选人语音随后以高度相似的回声出现在系统音频
- **THEN** 回声与重复抑制阻止该系统音频副本成为面试官问题

### Requirement: Degrade without inventing a third role
当双声道来源缺失、混合或无法可靠识别时，系统 SHALL 停止基于音频的自动回答，并 MUST 明确显示音频来源异常或仅手动模式。降级状态 MUST NOT 把未分类内容强制标为“我”或“面试官”，也 MUST NOT 恢复“角色待确认”交互。

#### Scenario: Only mixed audio is available
- **WHEN** 当前设备只能提供无法区分本地与系统来源的混合音频
- **THEN** 系统关闭音频自动回答、提示切换受支持的双声道或手动输入，并且不显示第三种角色

#### Scenario: A required audio source disconnects
- **WHEN** 面试进行中本地麦克风或系统音频来源断开
- **THEN** 页面显示对应来源中断，停止依赖该来源的新自动触发且保留现有对话和手动提问能力

### Requirement: Minimize source and speaker data
系统 MUST 仅为本场会话保留完成声道映射、回声去重和问题触发所需的最小来源元数据，不得把耳机、麦克风或匿名 speaker 信息用于现实身份识别或跨会话跟踪。原始音频仍 MUST 默认不长期保存。

#### Scenario: Interview ends
- **WHEN** 用户结束面试
- **THEN** 系统清理临时音频缓冲和回声匹配特征，仅按已说明的数据策略保留必要的来源类型、转录和回答事件
