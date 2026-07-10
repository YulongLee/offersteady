## MODIFIED Requirements

### Requirement: Confirm the material list without a redundant data-purpose checkbox
系统 MUST 在开始面试前保存用户明确确认的本场资料清单，包括空清单，但 MUST NOT 再要求勾选“我已了解本场数据用途”或同义的通用复选框。开始条件 SHALL 由资料清单确认状态组成；问题输入方式、音频来源、收音权限和问题检测状态 MUST NOT 阻塞 Web 端进入实时面试页。

#### Scenario: User confirms selected materials
- **WHEN** 用户选择资料并点击确认本场资料
- **THEN** 系统保存会话级选择版本，并启用“开始面试”

#### Scenario: User confirms an empty list
- **WHEN** 用户明确确认简历、JD 和知识材料均为空
- **THEN** 系统保存空允许清单并允许开始面试，不再要求额外勾选通用数据用途确认

#### Scenario: Material list is not confirmed
- **WHEN** 用户修改了选择但尚未保存确认
- **THEN** 系统不允许开始面试，并说明需要确认本场资料而不是提示数据用途复选框或问题输入方式

#### Scenario: Input source is not ready
- **WHEN** 用户已确认本场资料但本地端未连接、音频未授权或未选择手动模式
- **THEN** 系统仍允许进入实时面试页，并以非阻塞说明提示音频和问题检测由本地端或实时页操作处理

### Requirement: Keep disclosure and permission specific to the sensitive action
准备页 SHALL 在开始操作附近简洁说明已选资料和转录用于生成回答、原始音频默认不保存以及记录可删除。麦克风、系统音频、截图上传或其他敏感采集 MUST 在首次执行相应操作时继续取得平台权限或针对性确认；移除通用复选框和问题输入 gate MUST NOT 被视为这些操作的默认授权。

#### Scenario: User enters the live workspace without audio readiness
- **WHEN** 用户在本地端未连接、音频未授权或未选择手动模式时点击“开始面试”
- **THEN** 系统进入实时面试页，但不得自动启用麦克风、系统音频或自动问题检测

#### Scenario: User starts in manual mode
- **WHEN** 用户进入实时面试页后使用手动输入
- **THEN** 系统无需取得音频权限，也不得因为进入面试页而默认启用麦克风或系统音频

#### Scenario: User enables audio capture
- **WHEN** 用户首次请求启用麦克风或系统音频
- **THEN** 系统在采集前展示对应用途和保存行为并触发平台权限流程

#### Scenario: User submits a screenshot
- **WHEN** 用户选择截图回答并准备上传图片
- **THEN** 系统在上传前展示预览和提交操作，取消时不把图片加入会话
