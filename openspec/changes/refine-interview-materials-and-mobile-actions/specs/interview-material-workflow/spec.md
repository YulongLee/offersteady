## ADDED Requirements

### Requirement: Organize reusable materials by purpose
系统 SHALL 在资料管理页将用户资料分为“简历”“职位 JD”和“知识库”三个明确分区，并 MUST 为每项资料显示类型、名称、处理状态、更新时间以及适用的添加、替换或删除操作。

#### Scenario: User opens material management
- **WHEN** 用户进入资料管理页
- **THEN** 系统分别展示简历、职位 JD 和知识库入口，而不是把简历或 JD 混入知识库集合

#### Scenario: User manages a job description
- **WHEN** 用户进入职位 JD 分区并添加粘贴文本或支持的文件
- **THEN** 系统将其保存为 JD 类型资料并只提供适用于 JD 的解析、替换和删除操作

### Requirement: Separate material management from interview selection
系统 MUST 将可复用资料管理与单场面试资料选择分开；创建资料不得自动授权任何面试使用，单场选择也不得删除或修改资料库原件。

#### Scenario: User adds a new resume
- **WHEN** 用户在资料管理页成功添加一份简历
- **THEN** 系统将简历加入可选资料列表但不自动加入任何已有或新建面试

#### Scenario: User prepares a specific interview
- **WHEN** 用户进入某场面试的准备页
- **THEN** 系统按简历、职位 JD 和知识材料分组展示该场选择，并与其他面试的选择保持隔离

### Requirement: Allow explicitly empty or partial context
系统 SHALL 允许用户在单场面试中选择零或一份简历、零或一份 JD 和零到多份知识材料，并 MUST 提供明确的“不使用”或“暂不选择”操作。资料为空或仅选择部分资料 MUST NOT 单独阻止用户开始面试。

#### Scenario: User starts with no materials
- **WHEN** 用户明确确认本场不使用简历、JD 和知识材料，且至少一种问题输入方式已就绪
- **THEN** 系统允许开始面试，并提示回答不会结合个人简历、目标岗位或知识库

#### Scenario: User selects only a job description
- **WHEN** 用户只选择一份已就绪 JD 并确认本场清单
- **THEN** 系统允许开始面试，将本场标记为“仅使用 JD”，且不得宣称回答已结合个人经历

### Requirement: Require confirmation without silent inheritance
系统 MUST 在开始面试前记录本场资料清单的显式确认，包括空清单，并 MUST NOT 静默继承上一场面试、最近使用资料或全部知识材料作为已授权选择。

#### Scenario: Recent material is suggested
- **WHEN** 系统在准备页展示最近使用的简历或 JD 建议
- **THEN** 建议项保持未授权状态，直至用户选择并确认本场资料

#### Scenario: User clears all selections
- **WHEN** 用户执行“本场不使用资料”并确认
- **THEN** 系统保存一个已确认的空允许清单和新版本，而不是恢复默认资料

### Requirement: Enforce type limits and source readiness
系统 MUST 限制单场最多选择一份简历和一份 JD，知识材料可多选；未就绪、无权访问、停用或已删除资料 MUST 不可加入本场允许清单。

#### Scenario: Unready resume appears in preparation
- **WHEN** 一份简历仍在解析或解析失败
- **THEN** 系统显示其状态、禁止选择并允许用户继续使用空资料或其他有效资料

#### Scenario: Knowledge base remains empty
- **WHEN** 用户没有任何知识材料或选择数量为零
- **THEN** 系统将知识库显示为可选且不把空知识库视为准备错误

### Requirement: Enforce the confirmed allowlist during answering
可信服务 MUST 只使用本场已确认允许清单中的资料；当清单为空时，检索 MUST 使用空资料范围且不得自动回退到用户的其他简历、JD 或知识材料。

#### Scenario: Answer is generated with empty context
- **WHEN** 当前面试的已确认资料清单为空且用户提交问题
- **THEN** 系统仅基于问题本身生成通用回答建议，显示“未使用个人资料”，并继续遵守不得虚构经历的边界

#### Scenario: Answer uses partial context
- **WHEN** 当前清单只包含 JD 且回答实际使用该 JD
- **THEN** 回答来源仅展示该 JD 的名称和版本，不展示或暗示使用了简历或知识库

### Requirement: Preserve material privacy and deletion boundaries
系统 MUST 对三个资料分区应用相同的用户所有权、访问控制、最小化日志和删除边界，并 MUST 在删除资料后立即阻止其参与后续回答。

#### Scenario: User deletes a selected material
- **WHEN** 用户删除当前面试已选择的一份资料
- **THEN** 系统从后续检索中排除该资料、提示本场选择已变化，并且不在客户端日志中输出资料正文
