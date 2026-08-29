## ADDED Requirements

### Requirement: Keep live answer actions visually quiet
实时面试工作区 MUST 让快答和截屏回答入口保持稳定，并 MUST NOT 在操作入口中展示处理中、成功、完成或取消等任务状态文案。系统 MUST 继续执行防重复提交、任务处理、回答展示和需要用户操作的失败恢复。

#### Scenario: Quick answer is processing or completed
- **WHEN** 用户在实时面试中触发快答且任务进入处理中、成功或取消状态
- **THEN** 快答入口始终显示稳定的“快答”标题，不显示“快答中”“已回答”“快答已完成”或同义状态

#### Scenario: Screenshot answer is processing or completed
- **WHEN** 用户在实时面试中触发截屏回答且任务进入处理中、成功或取消状态
- **THEN** 截屏回答入口不显示任务状态行或完成文案，结果仍在回答区域呈现

#### Scenario: Duplicate action is attempted while processing
- **WHEN** 快答或截屏回答任务尚未结束
- **THEN** 系统仍阻止重复提交，但不以额外状态文案打断用户

#### Scenario: Screenshot answer requires failure recovery
- **WHEN** 截屏回答失败且用户必须选择重试或取消
- **THEN** 系统仍显示可操作的失败恢复界面
