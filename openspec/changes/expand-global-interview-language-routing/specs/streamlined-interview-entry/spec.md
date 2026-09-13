## MODIFIED Requirements

### Requirement: Confirm the material list without a redundant data-purpose checkbox
系统 MUST 在开始面试前保存用户明确确认的本场资料清单，包括空清单，但 MUST NOT 再要求勾选“我已了解本场数据用途”或同义的通用复选框。准备页 SHALL 同时展示当前会话语言并允许在开始前修改；开始条件 SHALL 由资料清单确认状态、已选语言资源可用性和至少一种可用问题输入方式组成。

#### Scenario: User confirms selected materials and language
- **WHEN** 用户选择资料、选择一个已验证语言并点击确认本场资料
- **THEN** 系统保存会话级资料版本和语言，且在问题输入方式可用时启用“开始面试”

#### Scenario: User selects a language without ready resources
- **WHEN** 用户选择尚未通过资源/评测门禁的语言
- **THEN** 准备页明确显示 Beta 或不可用状态，不允许开始并提供切换到已验证语言的操作

#### Scenario: User confirms an empty list
- **WHEN** 用户明确确认简历、JD 和知识材料均为空
- **THEN** 系统保存空允许清单和当前会话语言并允许继续，不要求额外通用复选框

#### Scenario: Keep the language control compact by default
- **WHEN** 用户进入准备页且当前会话语言为默认英语
- **THEN** 页面以收起状态显示英语和绿色的 Production 标识，用户可通过明确的展开操作查看并切换其他语言；展开或收起不改变现有资料确认和设备准备条件

### Requirement: Keep disclosure and permission specific to the sensitive action
准备页 SHALL 在开始操作附近简洁说明所选语言会影响语音识别、问题检测和 AI 回答，并继续说明已选资料和转录用途、原始音频默认不保存以及记录可删除。麦克风、系统音频、截图上传或其他敏感采集 MUST 在首次执行相应操作时继续取得平台权限或针对性确认。

#### Scenario: User changes language before audio capture
- **WHEN** 用户在准备页从英语切换为日语但尚未启用音频
- **THEN** 系统保存日语选择，不提前请求音频权限或开始采集
