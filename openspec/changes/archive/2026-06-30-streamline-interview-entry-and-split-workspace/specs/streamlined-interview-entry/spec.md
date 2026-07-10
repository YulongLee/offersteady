## ADDED Requirements

### Requirement: Provide one continuation action per active interview
面试首页 SHALL 为每场未结束面试只展示一个名为“继续面试”的主要操作，并 MUST NOT 同时展示“继续准备”和“预览工作台”。系统 MUST 根据服务端会话状态决定目标页面，而不是由用户猜测入口差异。

#### Scenario: Interview is still preparing
- **WHEN** 用户点击一场 `preparing` 面试的“继续面试”
- **THEN** 系统进入该场准备页并恢复已保存的本场资料选择和问题输入状态

#### Scenario: Interview is in progress
- **WHEN** 用户点击一场 `live` 或可恢复面试的“继续面试”
- **THEN** 系统直接进入该场实时工作台且不经过预览页面

#### Scenario: Dashboard is rendered
- **WHEN** 首页展示一场未结束面试
- **THEN** 该面试卡片不存在第二个“预览工作台”或同义的并行入口

### Requirement: Derive interview material choices from the managed library
准备页的“本场使用的资料”选择器 MUST 使用当前账号在资料页可见的同一组简历、职位 JD 和知识库来源，并 MUST 对齐来源 ID、类型、显示名称、版本、处理状态、删除状态和可选性。选择器 MUST NOT 维护无法由资料页解释或管理的第二套资料副本。

#### Scenario: Ready material exists in the library
- **WHEN** 用户在资料页拥有一份已就绪简历、一份已就绪 JD 和两份已就绪知识材料后打开准备页
- **THEN** 选择器在对应三个分组中展示同一来源名称、版本和状态

#### Scenario: Material is still processing
- **WHEN** 资料页中的来源处于处理中或失败状态
- **THEN** 准备页展示相同状态、禁止选用该来源并提供返回资料页处理的入口

#### Scenario: Selected material is deleted
- **WHEN** 用户从资料页删除本场此前选择的来源后重新进入准备页
- **THEN** 系统将该选择标记为失效且要求用户重新确认，不得用同类型的其他来源静默替换

### Requirement: Confirm the material list without a redundant data-purpose checkbox
系统 MUST 在开始面试前保存用户明确确认的本场资料清单，包括空清单，但 MUST NOT 再要求勾选“我已了解本场数据用途”或同义的通用复选框。开始条件 SHALL 由资料清单确认状态和至少一种可用问题输入方式组成。

#### Scenario: User confirms selected materials
- **WHEN** 用户选择资料并点击确认本场资料
- **THEN** 系统保存会话级选择版本，并在问题输入方式可用时启用“开始面试”

#### Scenario: User confirms an empty list
- **WHEN** 用户明确确认简历、JD 和知识材料均为空
- **THEN** 系统保存空允许清单并允许继续，不再要求额外勾选通用数据用途确认

#### Scenario: Material list is not confirmed
- **WHEN** 用户修改了选择但尚未保存确认
- **THEN** 系统不允许开始面试，并说明需要确认本场资料而不是提示数据用途复选框

### Requirement: Keep disclosure and permission specific to the sensitive action
准备页 SHALL 在开始操作附近简洁说明已选资料和转录用于生成回答、原始音频默认不保存以及记录可删除。麦克风、系统音频、截图上传或其他敏感采集 MUST 在首次执行相应操作时继续取得平台权限或针对性确认；移除通用复选框 MUST NOT 被视为这些操作的默认授权。

#### Scenario: User starts in manual mode
- **WHEN** 用户使用手动输入模式进入面试
- **THEN** 系统无需取得音频权限，也不得因为开始面试而默认启用麦克风或系统音频

#### Scenario: User enables audio capture
- **WHEN** 用户首次请求启用麦克风或系统音频
- **THEN** 系统在采集前展示对应用途和保存行为并触发平台权限流程

#### Scenario: User submits a screenshot
- **WHEN** 用户选择截图回答并准备上传图片
- **THEN** 系统在上传前展示预览和提交操作，取消时不把图片加入会话
