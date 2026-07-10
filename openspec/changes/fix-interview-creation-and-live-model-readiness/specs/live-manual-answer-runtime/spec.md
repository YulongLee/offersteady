# Live Manual Answer Runtime Specification

## ADDED Requirements

### Requirement: Route manual answers through the real backend chat runtime
实时面试页的手动问题输入和“快答” MUST 调用当前后端 Live Answer / Chat Service，并 SHALL 使用服务端运行时配置的真实模型供应商。前端 MUST NOT 在生产运行路径中本地拼接占位回答或回退到 mock 回答。

#### Scenario: Manual question is submitted successfully
- **WHEN** 用户在实时面试页输入问题并点击“快答”
- **THEN** 前端调用后端实时回答接口，后端使用当前 `.env` 配置的模型执行回答，并将结果返回到当前回答区与历史记录中

#### Scenario: Backend model is unavailable
- **WHEN** 后端模型配置缺失、无效或供应商调用失败
- **THEN** 系统展示真实失败原因或安全摘要错误，不得显示成功回答、静态样例回答或与实际原因无关的提示

### Requirement: Starting a manual-mode interview must not require an extra user token gate
当用户通过 Web 手动输入模式开始面试时，系统 MUST 允许在无额外发布令牌或前置音频凭证的情况下进入实时面试，并由服务端在会话启动流程中自动完成手动回答所需的内部状态准备。

#### Scenario: User starts a manual-mode interview
- **WHEN** 用户在准备页确认资料后点击“开始面试”，且本场不依赖本地音频发布
- **THEN** 系统成功启动会话并进入实时面试页，不要求用户额外输入、复制或请求令牌

#### Scenario: Session start succeeds before manual answer
- **WHEN** 用户开始面试成功后立即输入问题
- **THEN** 后端将该问题视为属于当前已启动会话并允许生成回答

### Requirement: Surface real session and model startup errors
如果新建面试、开始面试或手动回答所依赖的后端状态未建立成功，系统 MUST 向用户展示真实错误来源，并阻止进入一个看似可用但实际上无法回答的实时界面。

#### Scenario: Interview creation fails
- **WHEN** 用户点击新建面试而服务端未成功创建会话
- **THEN** 页面保留当前状态并展示创建失败信息，不得插入一条不可恢复的假记录

#### Scenario: Session is not started on backend
- **WHEN** 前端尝试开始面试但后端 Session Start 失败
- **THEN** 系统停留在准备页并展示启动失败原因，而不是直接进入实时面试页
