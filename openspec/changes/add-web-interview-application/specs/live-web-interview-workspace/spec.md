## ADDED Requirements

### Requirement: Prioritize current question and answer advice
实时工作台 SHALL 将当前问题与回答建议作为主要视觉区域，并 MUST 明确区分原始问题、资料引用、AI 推断和生成建议。

#### Scenario: Confirmed question receives an answer
- **WHEN** 系统确认一条当前问题并开始生成回答
- **THEN** 页面保留问题原文、流式展示回答建议并标注所使用的资料类型和生成状态

#### Scenario: Evidence is insufficient
- **WHEN** 检索上下文不足以支持具体候选人经历
- **THEN** 系统标记不确定性且不得虚构项目、公司、职责或量化结果

### Requirement: Provide low-distraction desktop layout
系统 SHALL 在不小于 1200 像素的视口将实时对话和回答呈现为可调整宽度的左右两栏，并 SHALL 提供固定可达的会话控制。实时页 MUST NOT 提供资料侧栏或永久历史与设备栏。

#### Scenario: User adjusts the column divider
- **WHEN** 用户通过指针或键盘调整对话与回答之间的分隔条
- **THEN** 两栏在最小宽度限制内改变比例且当前问题、连接状态和暂停操作保持可见

### Requirement: Adapt the live workspace for smaller screens
系统 MUST 在平板和手机按实时对话、回答、紧凑操作的顺序使用单栏布局，并 MUST 移除桌面分隔条。布局变化不得丢失会话状态、流式内容、历史位置或输入草稿。

#### Scenario: Viewport changes during generation
- **WHEN** 回答生成期间视口跨越响应式断点
- **THEN** 系统重新布局且保留当前问题、已生成内容、滚动位置和会话状态

### Requirement: Support explicit question input modes
系统 SHALL 支持桌面音频转录、手动文本和截图作为显式问题输入，并 MUST 对重复命令去重且持续显示当前主要输入设备。

#### Scenario: User submits a screenshot question
- **WHEN** 用户预览并确认提交一张题目截图
- **THEN** 系统在当前会话内显示上传、识别、分类和回答状态且不离开工作台

#### Scenario: User manually enters a question
- **WHEN** 用户在音频不可用时提交文本问题
- **THEN** 系统将其标为手动输入并通过同一回答管线处理

### Requirement: Expose safe session controls and recovery
系统 MUST 提供开始、暂停、恢复和结束操作，并 SHALL 在离线、设备断开、权限拒绝或生成失败时显示可执行的恢复路径。

#### Scenario: Realtime connection is lost
- **WHEN** 浏览器失去实时同步连接
- **THEN** 系统显示离线状态、不继续宣称内容正在同步，并保留安全的重连入口

#### Scenario: User ends the interview
- **WHEN** 用户确认结束正在进行的面试
- **THEN** 系统停止新的采集与问题处理，将会话标为 `ended` 并进入复盘页面

### Requirement: Preserve question history without competing with current answer
系统 SHALL 保存本场已确认的问题列表并允许用户回看旧回答，但 MUST 让历史内容保持次要层级且不得替换当前问题状态。

#### Scenario: User opens a historical answer
- **WHEN** 用户选择一条历史问题
- **THEN** 系统在回答区域内展示历史详情，并提供返回最新回答的直接操作
