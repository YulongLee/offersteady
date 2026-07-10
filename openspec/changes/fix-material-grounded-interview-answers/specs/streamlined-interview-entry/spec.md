## MODIFIED Requirements

### Requirement: Derive interview material choices from the managed library
准备页的“本场使用的资料”选择器 MUST 使用当前账号在资料页可见的同一组简历、职位 JD 和知识库来源，并 MUST 对齐来源 ID、类型、显示名称、版本、处理状态、删除状态、索引状态、后端可选性和资料不可用原因。选择器 MUST NOT 维护无法由资料页解释或管理的第二套资料副本。只有后端资料库中状态为 ready、索引状态为 indexed、未删除、未停用且后端确认 selectable 的文档版本 SHALL 可被确认为本场资料。确认成功后，准备页 MUST 展示本场资料快照摘要，并且实时回答 MUST 使用该快照而不是用户资料库的最新未确认状态。

#### Scenario: Ready material exists in the library
- **WHEN** 用户在资料页拥有一份已就绪且已索引的简历、一份已就绪且已索引的 JD 和两份已就绪且已索引的知识材料后打开准备页
- **THEN** 选择器在对应三个分组中展示同一来源名称、版本、状态、索引可用性和后端可选性

#### Scenario: Material is still processing
- **WHEN** 资料页中的来源处于上传完成、处理中、索引中或失败状态
- **THEN** 准备页展示相同状态、禁止选用该来源并提供返回资料页处理的入口

#### Scenario: Material is ready but backend marks it unselectable
- **WHEN** 资料页中的来源显示为 ready 但后端返回 selectable 为 false 或不可用原因
- **THEN** 准备页禁止选用该来源并展示安全原因，不允许用户把该来源确认为本场资料

#### Scenario: Selected material is deleted
- **WHEN** 用户从资料页删除本场此前选择的来源后重新进入准备页
- **THEN** 系统将该选择标记为失效且要求用户重新确认，不得用同类型的其他来源静默替换

#### Scenario: Material list is confirmed
- **WHEN** 用户确认本场资料清单
- **THEN** 系统保存会话级资料快照，包含来源 ID、文档版本 ID、显示名称、类型、索引状态、后端可选性、选择版本和确认时间

#### Scenario: User starts interview after confirming materials
- **WHEN** 用户确认本场资料清单后开始面试并提出问题
- **THEN** 回答服务使用该确认快照装配资料上下文，并在回答结果中返回安全资料来源摘要
