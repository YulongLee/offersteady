## MODIFIED Requirements

### Requirement: Derive interview material choices from the managed library
准备页的“本场使用的资料”选择器 MUST 使用当前账号在资料页可见的同一组简历、职位 JD 和知识库来源，并 MUST 对齐来源 ID、类型、显示名称、版本、处理状态、索引状态、删除状态和可选性。选择器 MUST NOT 维护无法由资料页解释或管理的第二套资料副本。只有后端持久化资料库中已完成索引、未删除、未停用且状态为 ready 的文档版本 SHALL 可被确认为本场资料。

#### Scenario: Ready indexed material exists in the library
- **WHEN** 用户在资料页拥有一份已就绪且已索引的简历、一份已就绪且已索引的 JD 和两份已就绪且已索引的知识材料后打开准备页
- **THEN** 选择器在对应三个分组中展示同一来源名称、版本、状态和索引可用性

#### Scenario: Material is still processing or indexing
- **WHEN** 资料页中的来源处于上传完成、处理中、索引中或失败状态
- **THEN** 准备页展示相同状态、禁止选用该来源并提供返回资料页处理的入口

#### Scenario: Selected material is deleted
- **WHEN** 用户从资料页删除本场此前选择的来源后重新进入准备页
- **THEN** 系统将该选择标记为失效且要求用户重新确认，不得用同类型的其他来源静默替换

#### Scenario: Material list is confirmed
- **WHEN** 用户确认本场资料清单
- **THEN** 系统保存会话级资料快照，包含来源 ID、文档版本 ID、显示名称、类型、索引状态、选择版本和确认时间
