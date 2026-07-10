## ADDED Requirements

### Requirement: Place answer actions in the live main region
实时工作台 SHALL 在主内容中提供可达操作，并 MUST 将低置信度问题的确认放在相关对话条目内，将手动提问和“截图回答”放在回答区下方的紧凑输入栏，而不是放在资料或历史侧栏。

#### Scenario: Transcript content needs confirmation
- **WHEN** 系统音频中的问题因文本或边界置信度不足而等待用户确认
- **THEN** 相关对话条目显示问题文本、“忽略”和“确认问题”，用户无需打开侧栏即可处理

#### Scenario: User needs a screenshot answer
- **WHEN** 用户正在查看当前回答并选择“截图回答”
- **THEN** 系统从主操作区进入截图预览与确认流程且不离开实时工作台

### Requirement: Keep primary actions reachable on phones
系统 MUST 在手机单栏布局中让内容不清晰问题的操作、回答问题和截图回答保持触摸可达，操作不得被会话控制、移动导航或系统安全区遮挡。

#### Scenario: User opens the live page on a phone
- **WHEN** 视口不大于手机断点且没有弹窗打开
- **THEN** 页面在主内容下方或底部安全区上方显示至少 44×44 CSS 像素的确认与截图操作目标

#### Scenario: On-screen keyboard opens
- **WHEN** 用户展开手动提问并唤起手机软键盘
- **THEN** 输入框和提交按钮仍可滚动到可见区域，且不得被固定操作栏永久遮挡

### Requirement: Use one canonical action state across layouts
系统 MUST 让桌面、平板和手机布局共享同一份内容不清晰问题、手动输入草稿和截图任务状态；响应式重排或桌面分栏调整 MUST NOT 创建重复命令或清空未提交内容。

#### Scenario: Viewport changes with a draft question
- **WHEN** 用户输入了尚未提交的手动问题后改变窗口宽度
- **THEN** 重排后的主操作区保留完整草稿且只提供一次提交

#### Scenario: User adjusts the desktop divider
- **WHEN** 用户拖动对话与回答分隔条而截图仍处于预览状态
- **THEN** 截图任务继续保持预览状态，主操作区仍能恢复该流程

### Requirement: Preserve operation status and centralized billing disclosure
实时操作区 SHALL 展示上传、识别、确认、生成、失败和重试状态；失败或取消不得被显示为成功回答。实时按钮和紧凑输入栏 MUST NOT 显示单次点数，适用费率、会员权益和余额明细 SHALL 在积分页面完整展示，服务端仍须在任务创建前校验权益。

#### Scenario: Screenshot recognition fails on mobile
- **WHEN** 用户从手机主操作区提交截图但识别失败
- **THEN** 系统显示失败与重试入口、说明本次不扣点，并保持当前面试与回答可用

#### Scenario: User confirms a detected question
- **WHEN** 用户点击“确认问题”
- **THEN** 系统以幂等命令提交该问题、显示回答生成状态，并按已披露费率只结算一次

### Requirement: Keep secondary panels secondary
实时页 MUST NOT 提供资料面板或现场调整资料能力；历史答案 SHALL 在回答区内翻页。开始前确认的资料选择版本 MUST 继续用于新问题。

#### Scenario: Live workspace opens without a material panel
- **WHEN** 用户在桌面、平板或手机进入实时面试页
- **THEN** 当前问题、主操作区和会话状态直接可见，页面不存在资料面板入口

### Requirement: Provide accessible live actions
主操作区 MUST 支持键盘焦点顺序、可访问名称、状态播报和明确的禁用原因，并 MUST 避免用颜色或图标作为唯一含义。

#### Scenario: Keyboard user confirms unclear question content
- **WHEN** 键盘用户将焦点移动到内容不清晰问题操作区
- **THEN** 系统按问题文本、拒绝操作、确认操作的逻辑顺序提供焦点，并在提交后播报状态变化
