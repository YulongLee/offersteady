## ADDED Requirements

### Requirement: Select context for each interview
系统 SHALL 允许用户为每场面试独立选择零或一份简历、零或一份 JD 和零到多份知识材料，并 SHALL 显示资料名称、类型、处理状态、更新时间和选择状态。

#### Scenario: User prepares an interview
- **WHEN** 用户在准备中心打开“本场使用的资料”
- **THEN** 系统按简历、JD 和知识材料分组展示该用户有权访问的资料及当前会话选择

#### Scenario: User selects knowledge materials
- **WHEN** 用户勾选多份已就绪知识材料并保存
- **THEN** 系统只把这些材料加入当前面试的允许来源清单且不影响其他面试

### Requirement: Enforce selection cardinality and readiness
系统 MUST 最多接受一份已就绪简历和一份已就绪 JD，并 SHALL 接受零到多份已就绪知识材料；未就绪、停用或已删除资料 MUST 不可选择。资料完整度只决定个性化程度，已确认的空清单或部分清单仍可用于开始面试。

#### Scenario: Context is empty
- **WHEN** 用户明确确认不使用简历、JD 和知识材料
- **THEN** 系统允许继续并将本场标为“未使用个人资料”，不得宣称回答已经个性化

#### Scenario: Failed material appears in picker
- **WHEN** 资料库中一份知识材料解析失败
- **THEN** 系统显示其失败状态、禁止选择并提供前往资料库处理的入口

### Requirement: Require explicit confirmation
系统 MUST 在开始任何面试前取得用户对本场资料清单的显式确认，包括空清单，并 MUST 不默认选择最近资料或全部知识材料。

#### Scenario: Recent resume is suggested
- **WHEN** 系统向新面试建议最近使用的简历
- **THEN** 界面将其标记为建议且在用户确认前不宣称清单已经授权

#### Scenario: User selects all knowledge materials
- **WHEN** 用户显式执行全选知识材料
- **THEN** 系统显示选中数量和潜在无关内容提示，并允许在保存前取消

### Requirement: Persist isolated session selections
系统 SHALL 以用户和面试会话为作用域保存资料选择，并 SHALL 为每次已确认变更分配递增版本。

#### Scenario: User returns to preparation
- **WHEN** 用户重新打开一场已保存的面试准备页
- **THEN** 系统恢复该面试最后确认的资料清单和选择版本

#### Scenario: Another interview opens
- **WHEN** 用户打开另一场面试
- **THEN** 系统展示另一场面试自己的资料清单，不继承未确认的本地修改

### Requirement: Keep confirmed context fixed during a live interview
系统 MUST 在实时工作台使用开始前最后确认的本场资料清单，并 MUST NOT 在实时页提供更换资料入口。需要改变资料时，用户 SHALL 离开当前实时会话并回到准备流程重新确认。

#### Scenario: Answer is generated during the live session
- **WHEN** 实时面试提交一个新问题
- **THEN** 系统使用开始前最后确认的资料选择版本，并在回答来源中记录该版本

#### Scenario: User wants different materials
- **WHEN** 用户在实时面试中希望更换资料
- **THEN** 实时页不展示调整面板，并要求用户结束或离开当前实时会话后回到准备流程

### Requirement: Enforce selected sources in retrieval
可信服务 MUST 在每次检索前校验资料所有权、会话作用域、选择版本和就绪状态，并 MUST 只把已确认允许的来源 ID 传给检索适配器。

#### Scenario: Client submits an unselected source ID
- **WHEN** 客户端请求包含不在当前会话已确认清单中的资料 ID
- **THEN** 系统拒绝使用该来源、记录不含敏感正文的安全事件并继续使用其他有效来源

#### Scenario: Selected material is irrelevant
- **WHEN** 已选材料没有达到当前问题的相关性要求
- **THEN** 系统不强行把该材料用于回答，也不将其展示为实际回答依据

### Requirement: Record actual answer provenance
每条回答 MUST 记录其使用的选择版本和实际参与检索或生成的具体资料 ID、版本、类型与显示名称，并 SHALL 将实际来源与 AI 推断分开呈现。

#### Scenario: Answer uses two selected materials
- **WHEN** 回答实际使用一份简历和一份知识材料
- **THEN** 实时回答区域展示这两份具体资料名称，而不是展示所有已选资料或笼统的“知识库”

#### Scenario: Answer uses no knowledge material
- **WHEN** 当前问题只使用简历和 JD 生成建议
- **THEN** 系统不把任何未命中的知识材料标记为回答依据

### Requirement: Handle invalidated selected sources
系统 MUST 在已选来源被停用、删除、解析失败或更新版本时使其退出后续检索，并 SHALL 明确提示用户处理失效选择而不静默替换。

#### Scenario: Selected source is deleted
- **WHEN** 用户删除当前会话已选择的一份知识材料
- **THEN** 后续问题立即排除该来源，当前选择显示失效状态，历史回答仅保留最小化来源标识

#### Scenario: Selected source has a new version
- **WHEN** 已选资料产生新的解析版本
- **THEN** 系统要求用户确认是否切换，新问题在确认前不得自动使用新版本

### Requirement: Protect context selection data
系统 MUST 只向获得会话授权的用户和设备展示资料清单，并 MUST 避免在页面标题、通知和客户端日志中暴露资料名称或正文。

#### Scenario: Unauthorized device requests selection
- **WHEN** 未授权设备请求一场面试的资料选择
- **THEN** 系统拒绝请求且不返回资料名称、状态或来源标识
