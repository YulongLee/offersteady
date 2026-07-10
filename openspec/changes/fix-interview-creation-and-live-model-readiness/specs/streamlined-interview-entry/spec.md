# Streamlined Interview Entry Specification Delta

## MODIFIED Requirements

### Requirement: Provide one continuation action per active interview
系统在首页或面试入口创建新面试后 MUST 持久化为真实后端会话，并在创建成功后返回可继续的会话记录。创建失败时 MUST 向用户展示真实错误并保持当前页面可重试，不得把失败创建结果伪装成一场可继续的面试。

#### Scenario: New interview is created successfully
- **WHEN** 用户点击“新建面试”且服务端成功创建一场新的 preparing 会话
- **THEN** 系统展示该会话并允许用户进入对应准备页

#### Scenario: New interview creation fails
- **WHEN** 用户点击“新建面试”但服务端创建失败
- **THEN** 系统显示创建失败信息且最近面试列表不出现伪造的新会话

### Requirement: Confirm the material list without a redundant data-purpose checkbox
当用户已确认本场资料并点击“开始面试”时，系统 MUST 先完成后端会话启动，再进入实时面试页。若当前模式为 Web 手动输入模式，开始面试 MUST NOT 再要求额外令牌、发布凭证或等价的前置门槛。

#### Scenario: Start interview in manual mode
- **WHEN** 用户确认资料后点击“开始面试”，且本场依赖手动问题输入而非音频发布
- **THEN** 系统直接调用后端会话启动并在成功后进入实时面试页，不要求额外令牌

#### Scenario: Backend start fails
- **WHEN** 用户点击“开始面试”但后端启动失败
- **THEN** 系统停留在准备页并展示真实失败原因，不得进入无法回答的实时面试页
