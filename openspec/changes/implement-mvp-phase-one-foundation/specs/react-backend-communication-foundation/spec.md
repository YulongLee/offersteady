## ADDED Requirements

### Requirement: Add a replaceable API communication layer without changing the approved UI flow
React Web 端 MUST 在现有页面结构与交互保持不变的前提下，引入统一的后端通信层。组件 MUST 通过适配器、服务层或等效抽象访问后端，而 MUST NOT 直接在页面组件中散落请求细节。该通信层 MUST 支持当前原型数据源与后续真实后端实现之间的切换。

#### Scenario: UI is wired to a service abstraction
- **WHEN** 开发者查看首页、资料库、计费页或实时面试页的数据来源
- **THEN** 页面通过统一通信抽象获取数据，而不是在视图组件内部直接拼接请求逻辑

### Requirement: Support environment-based backend configuration and normalized errors
前端通信框架 MUST 支持按环境配置 API 基础地址、请求超时与开发模式开关，并 MUST 将网络错误、服务端占位错误和取消请求错误归一化为前端可消费的统一错误模型。该模型 MUST 允许现有页面延续当前原型的状态展示方式。

#### Scenario: Backend request fails
- **WHEN** 前端调用第一阶段占位接口时遇到网络失败或未实现响应
- **THEN** 页面能够通过统一错误模型处理该结果，而无需为每个页面单独重写错误解析逻辑

### Requirement: Keep current prototype interaction states available during backend transition
在从原型数据源向真实后端通信层过渡期间，前端 MUST 保留现有 pending、success、empty、error 和恢复状态的展示能力，并 MUST 支持在开发环境下使用夹具或本地适配器继续验证交互。引入通信层 MUST NOT 删除现有交互状态覆盖面。

#### Scenario: Developer runs the app without full backend business logic
- **WHEN** 后端只提供基础健康检查和占位接口
- **THEN** 前端仍可通过占位数据源或后端占位响应验证主要页面交互，不因业务未实现而失去页面可演示性
