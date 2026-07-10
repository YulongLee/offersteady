## ADDED Requirements

### Requirement: Start screenshot answering from an instant live capture
实时面试页中的“截屏回答” MUST 直接触发当前屏幕捕获流程，而不是要求用户先上传本地图片文件。系统 MUST 在用户主动点击后立刻进入截屏采集与回答链路，并 SHALL 保持当前会话、对话和答案上下文不跳转到额外页面。

#### Scenario: User triggers screenshot answer during an interview
- **WHEN** 用户在实时面试页点击“截屏回答”
- **THEN** 系统直接发起当前屏幕截取流程，而不是打开文件上传或图片选择器

#### Scenario: Capture completes successfully
- **WHEN** 用户完成一次有效的当前屏幕截取
- **THEN** 系统使用该次截屏作为截图回答输入，留在当前实时页并进入回答生成状态

### Requirement: Keep capture user-initiated and cancellable
截图采集 MUST 由用户显式触发，并 MUST 支持在平台权限、窗口选择或捕获阶段取消。用户取消后，系统 MUST NOT 生成截图回答任务，也 MUST NOT 将未确认的截图静默写入会话记录。

#### Scenario: User cancels screen capture
- **WHEN** 用户在系统权限弹窗、窗口选择器或浏览器捕获流程中取消
- **THEN** 系统返回实时面试页空闲状态，不创建新的截图回答任务，也不修改当前答案页

#### Scenario: Capture permission is denied
- **WHEN** 平台或浏览器拒绝当前屏幕捕获权限
- **THEN** 系统提示截图权限不可用，并提供再次发起截屏回答的恢复入口

### Requirement: Answer from the current screen without upload-specific UI
截图回答流程 MUST NOT 在实时面试页显示“上传并识别”“继续模拟识别”或同义的上传式中间步骤。系统 MAY 显示短暂的“正在截屏”“正在识别”或“正在回答”状态，但这些状态 MUST 服务于即时截屏链路而不是文件上传链路。

#### Scenario: Capture is being processed
- **WHEN** 一次截屏已经成功提交到截图回答服务
- **THEN** 页面显示即时截屏相关的处理中状态，而不是上传预览或文件确认界面

#### Scenario: Existing answer context is open
- **WHEN** 用户正在查看当前回答或历史回答时发起截屏回答
- **THEN** 系统保留当前回答浏览上下文，并在新截图回答开始后按既有回答历史规则切换或提示“有新答案”

### Requirement: Protect sensitive screenshot content in live mode
当前屏幕截取内容属于敏感数据，系统 MUST 只在本次用户触发的截图回答任务中使用该截图，并 MUST 避免把完整截图内容暴露到页面标题、未授权设备或与本场无关的日志中。截图失败重试 MUST 继续要求新的用户触发，而不是后台静默重复截屏。

#### Scenario: Screenshot answer succeeds
- **WHEN** 截图回答成功生成
- **THEN** 系统只在本场授权会话中展示回答结果，并按现有截图回答历史或记录策略保存必要元数据

#### Scenario: Screenshot processing fails
- **WHEN** 截图识别或回答生成失败
- **THEN** 系统显示失败状态和重新发起“截屏回答”的入口，且不会在后台自动再次捕获用户当前屏幕
