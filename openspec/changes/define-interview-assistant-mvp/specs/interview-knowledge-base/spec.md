## ADDED Requirements

### Requirement: Add knowledge material
系统 SHALL 允许用户通过受支持文件或文本添加面试知识材料，并为每份材料记录用户可识别的名称和处理状态。

#### Scenario: Knowledge material added
- **WHEN** 用户提交有效材料
- **THEN** 系统显示材料名称、处理进度和最终可用状态

#### Scenario: Material processing fails
- **WHEN** 系统无法解析或建立材料索引
- **THEN** 系统显示失败原因并允许重试、替换或删除材料

### Requirement: Retrieve relevant knowledge
系统 SHALL 针对当前问题只检索相关的已就绪知识片段，并为回答保留来源关联。

#### Scenario: Relevant material found
- **WHEN** 知识库中存在与当前问题相关的内容
- **THEN** 系统将相关片段提供给回答生成流程并标记使用了知识库上下文

#### Scenario: No relevant material found
- **WHEN** 没有达到相关性要求的知识片段
- **THEN** 系统不强行引用知识库，并继续使用其他可用上下文生成回答

### Requirement: Manage knowledge sources
系统 MUST 允许用户查看、停用和删除每个知识来源。

#### Scenario: Source disabled
- **WHEN** 用户停用某个知识来源
- **THEN** 后续检索立即排除该来源，但保留其可恢复状态

#### Scenario: Source deleted
- **WHEN** 用户确认删除某个知识来源
- **THEN** 系统删除原始内容和派生索引，并不再将其用于回答

### Requirement: Explain knowledge usage
系统 SHALL 让用户识别一条回答是否使用了知识库以及使用了哪些来源。

#### Scenario: Answer uses knowledge base
- **WHEN** 回答生成使用了一个或多个知识片段
- **THEN** 实时回答区域展示可展开的来源名称，而不暴露无关材料内容
