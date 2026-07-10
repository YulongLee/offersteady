## ADDED Requirements

### Requirement: Prepare interview session
系统 SHALL 在用户开始面试前展示简历、JD 和知识库的就绪状态，并说明当前可用的输入方式和数据处理规则。

#### Scenario: Required context is ready
- **WHEN** 简历和 JD 均已解析完成
- **THEN** 系统允许用户开始上下文化面试会话

#### Scenario: Required context is missing
- **WHEN** 简历或 JD 尚未就绪
- **THEN** 系统解释缺失内容，并只在用户明确确认后允许进入受限演示模式

### Requirement: Explicitly control session capture
系统 MUST 只在用户明确开始会话并授权对应输入权限后处理实时输入，并 MUST 在暂停或结束时停止采集。

#### Scenario: User starts interview
- **WHEN** 用户确认数据说明、授予必要权限并点击开始面试
- **THEN** 系统将会话切换为进行中并持续显示当前采集状态

#### Scenario: User pauses interview
- **WHEN** 用户点击暂停
- **THEN** 系统停止处理新的实时输入并将会话状态显示为已暂停

#### Scenario: User ends interview
- **WHEN** 用户确认结束面试
- **THEN** 系统停止采集并不再为该会话自动生成新回答

### Requirement: Accept interview questions
系统 SHALL 接受已授权实时输入产生的问题文本，并 MUST 提供手动输入作为权限拒绝或实时链路失败时的降级方式。

#### Scenario: Question text becomes available
- **WHEN** 系统收到完整或可回答的问题文本
- **THEN** 系统在实时回答区域创建一条问题记录并开始生成建议

#### Scenario: Realtime input fails
- **WHEN** 实时输入不可用或处理中断
- **THEN** 系统显示错误状态并保留手动输入问题的入口

### Requirement: Generate grounded answer suggestions
系统 SHALL 基于当前问题、已确认简历、JD 和相关知识片段生成结构化回答建议，并 MUST 不把推测表述为用户真实经历。

#### Scenario: Sufficient context exists
- **WHEN** 当前问题存在相关简历经历、岗位要求或知识材料
- **THEN** 系统展示包含回答要点、建议结构和上下文来源的回答建议

#### Scenario: Context is insufficient
- **WHEN** 可用资料不足以支持可靠回答
- **THEN** 系统明确提示信息不足，并提供澄清方向而不是虚构事实

### Requirement: Present answer states
实时回答区域 SHALL 清楚展示每条问题的接收、生成、完成和失败状态，并允许用户重新生成失败或不满意的回答。

#### Scenario: Answer generation is in progress
- **WHEN** 系统正在生成回答
- **THEN** 界面立即显示生成状态并保留对应问题文本

#### Scenario: Answer generation fails
- **WHEN** 回答服务返回错误或超时
- **THEN** 界面保留问题、解释失败并提供重试操作
