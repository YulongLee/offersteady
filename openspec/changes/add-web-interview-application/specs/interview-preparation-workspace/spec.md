## ADDED Requirements

### Requirement: Create an interview draft
系统 SHALL 允许用户创建包含名称、目标岗位和可选公司信息的面试草稿，并 SHALL 在离开后恢复已确认保存的草稿。

#### Scenario: User creates a draft
- **WHEN** 用户提交有效的岗位和面试名称
- **THEN** 系统创建处于 `preparing` 状态的面试并进入其准备中心

### Requirement: Present a unified preparation checklist
准备中心 SHALL 在同一页面展示本场资料选择和问题输入状态，并 MUST 区分可选项、处理中、失败项和已确认空清单。资料候选项 MUST 来自账号资料页管理的同一来源集合。

#### Scenario: Required documents are processing
- **WHEN** 简历或 JD 已上传但仍在解析
- **THEN** 系统显示对应处理状态且不宣称个性化上下文已就绪

#### Scenario: Optional knowledge base is empty
- **WHEN** 用户没有添加知识库材料
- **THEN** 系统将知识库标为可选并允许完成其他准备步骤

### Requirement: Inspect and correct prepared context
系统 MUST 允许用户查看解析后的简历与 JD 摘要、识别资料来源，并 SHALL 提供替换、重新解析和删除操作。

#### Scenario: Parsed experience is incorrect
- **WHEN** 用户发现简历解析摘要不准确
- **THEN** 系统允许替换资料或重新解析，且旧版本不得继续作为已就绪上下文

### Requirement: Gate personalized interview readiness
系统 MUST 在本场资料清单已明确确认且至少一种问题输入方式可用时允许开始面试；资料是否完整只决定个性化程度。设备不可用时 SHALL 提供手动输入和截图模式。

#### Scenario: Device companion is unavailable
- **WHEN** 资料已就绪但 Mac 伴随程序未连接
- **THEN** 系统说明实时系统音频不可用，并允许用户明确选择手动模式开始

#### Scenario: Required context is missing
- **WHEN** 简历或 JD 缺失
- **THEN** 系统阻止宣称已完成个性化准备，并说明补充资料或进入受限演示模式的影响

### Requirement: Disclose sensitive-data behavior before start
系统 MUST 在开始面试操作附近展示简历、JD、知识材料和转录的用途、原始音频默认不保存及会话删除入口，但 MUST NOT 使用通用数据用途复选框作为启动门槛。麦克风、系统音频和截图上传 SHALL 在对应操作发生时取得针对性权限或确认。

#### Scenario: User starts in manual mode
- **WHEN** 用户已确认本场资料清单并选择手动输入
- **THEN** 系统允许进入面试且不自动启动麦克风或系统音频采集

#### Scenario: User enables sensitive capture
- **WHEN** 用户首次启用麦克风、系统音频或提交截图
- **THEN** 系统在采集或上传前取得该操作对应的权限或确认
