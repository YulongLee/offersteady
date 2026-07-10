## ADDED Requirements

### Requirement: Do not expose an unsupported interview-record retention preference
设置页 MUST NOT 提供“面试记录保存期限”选择器，也 MUST NOT 展示 7 天、30 天或手动删除等尚未由真实保存策略支持的用户偏好。界面只 SHALL 陈述系统实际执行的保存行为。

#### Scenario: User opens settings
- **WHEN** 用户进入设置页的数据与隐私区域
- **THEN** 页面不存在面试记录保存期限下拉框或其他可编辑期限控件

#### Scenario: No retention automation exists
- **WHEN** 产品尚未实现可验证的自动到期删除机制
- **THEN** 系统不得暗示用户选择某个期限后会自动删除记录

### Requirement: Preserve direct deletion and minimum-storage controls
移除期限偏好后，系统 MUST 继续默认不保存原始音频，并 MUST 在复盘页保留删除截图和删除整场面试的操作。删除操作 MUST 以服务端确认结果为准，不得仅隐藏客户端内容。

#### Scenario: User reviews privacy settings
- **WHEN** 用户查看设置页
- **THEN** 系统仍明确显示原始音频默认不保存，并提供通向会话数据管理说明的路径

#### Scenario: User deletes an interview
- **WHEN** 用户在复盘页确认删除整场面试
- **THEN** 系统删除会话专属问题、回答和附件，并明确可复用资料是否保留

#### Scenario: Deletion fails
- **WHEN** 服务端未确认删除完成
- **THEN** 页面保留记录并显示可重试错误，不得宣称已经删除
