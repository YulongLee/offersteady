## ADDED Requirements

### Requirement: Upload resume
系统 MUST 允许用户上传 PDF、DOCX 或纯文本格式的简历，并在上传前说明文件用途和数据处理方式。

#### Scenario: Supported resume uploaded
- **WHEN** 用户选择受支持且大小符合限制的简历文件
- **THEN** 系统接受文件并显示解析进度

#### Scenario: Unsupported resume rejected
- **WHEN** 用户选择不受支持或超过大小限制的文件
- **THEN** 系统拒绝上传并显示可操作的格式或大小说明

### Requirement: Review parsed resume
系统 SHALL 将简历解析为可阅读、可编辑的结构化内容，并要求用户能够在用于 AI 回答前检查结果。

#### Scenario: Resume parsing succeeds
- **WHEN** 简历解析完成
- **THEN** 系统展示姓名以外的核心经历、技能、项目和教育信息预览以及解析完成状态

#### Scenario: Resume parsing is incomplete
- **WHEN** 系统无法可靠解析部分简历内容
- **THEN** 系统标记不确定区域并允许用户修正或重新上传

### Requirement: Use resume as answer context
系统 SHALL 只使用用户确认的简历内容生成个性化回答建议，并 MUST 不虚构简历中不存在的经历。

#### Scenario: Relevant experience exists
- **WHEN** 当前问题与已确认简历中的经历相关
- **THEN** 系统优先引用该经历并标记回答使用了简历上下文

#### Scenario: Supporting experience is absent
- **WHEN** 简历中没有支持某项回答的经历
- **THEN** 系统说明信息不足并避免生成虚构项目或成果

### Requirement: Delete resume context
系统 MUST 允许用户删除简历及其派生内容。

#### Scenario: User deletes resume
- **WHEN** 用户确认删除当前简历
- **THEN** 系统删除原始文件、解析结果和用于检索的派生数据，并停止在后续回答中使用它
