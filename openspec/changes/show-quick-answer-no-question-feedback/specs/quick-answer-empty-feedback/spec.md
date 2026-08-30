## ADDED Requirements

### Requirement: Quick answer explains when no interviewer question is available
实时面试工作区 SHALL 允许用户在没有手动问题且尚未识别到面试官问题时触发快答意图，并 MUST 明确提示“未能识别到面试官的问题”。提示 SHALL 引导用户等待识别或手动输入问题。

#### Scenario: User requests quick answer before any interviewer question is recognized
- **WHEN** 用户未输入问题、系统也没有可用的面试官问题，并点击“快答”
- **THEN** 页面显示“未能识别到面试官的问题”
- **AND** 页面提示用户等待面试官问题识别或手动输入问题

### Requirement: Empty quick answer does not start or charge an answer
缺少可用问题时，系统 MUST NOT 发起回答请求、创建回答任务或产生积分扣费，并 MUST 保留回答处理中防重复提交能力。

#### Scenario: Empty quick answer is handled locally
- **WHEN** 用户在没有可用问题时点击“快答”
- **THEN** 前端不调用回答提交接口
- **AND** 当前回答、任务状态和积分余额保持不变

#### Scenario: Answer generation is already processing
- **WHEN** 快答请求正在生成中
- **THEN** 快答按钮仍保持禁用以防止重复提交
- **AND** 页面不恢复处理中或完成状态文案

### Requirement: Missing-question feedback clears after recovery
当用户开始手动输入问题、系统识别到可用的面试官问题或其他回答操作成功启动时，系统 SHALL 清除缺少问题提示。

#### Scenario: User manually enters a question after the warning
- **WHEN** 页面正在显示缺少面试官问题提示，且用户开始输入手动问题
- **THEN** 缺少问题提示消失
- **AND** 用户可以使用输入的问题触发快答

#### Scenario: Interviewer question arrives after the warning
- **WHEN** 页面正在显示缺少面试官问题提示，且实时链路随后提供可用的面试官问题
- **THEN** 缺少问题提示自动消失
- **AND** 后续快答使用最新的可用问题
