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

#### Scenario: New interview reuses the latest interview details
- **WHEN** 当前账号已有历史面试且用户打开新建面试页
- **THEN** 系统使用最近一场面试的名称、目标岗位和公司作为可编辑默认值

#### Scenario: First interview starts with an empty form
- **WHEN** 当前账号没有任何历史面试且用户打开新建面试页
- **THEN** 面试名称、目标岗位和公司保持为空，并要求用户自行填写必填项

#### Scenario: Preparing interview remains resumable after inactivity
- **WHEN** 用户创建面试后尚未点击开始，并离开准备页超过实时面试空闲超时时间
- **THEN** 会话继续保持 preparing，用户再次进入准备页时仍可选择资料、连接设备并开始面试

#### Scenario: Recover an incorrectly auto-ended unstarted interview
- **WHEN** 历史缺陷曾把 `startedAtMs` 为空的 preparing 会话错误标记为 ended
- **THEN** 系统将该未开始会话恢复为 preparing，且不得把真正开始过或用户已删除的会话恢复

### Requirement: Confirm the material list without a redundant data-purpose checkbox
当用户已确认本场资料并点击“开始面试”时，系统 MUST 先完成后端会话启动，再进入实时面试页。若当前模式为 Web 手动输入模式，开始面试 MUST NOT 再要求额外令牌、发布凭证或等价的前置门槛。

#### Scenario: Start interview in manual mode
- **WHEN** 用户确认资料后点击“开始面试”，且本场依赖手动问题输入而非音频发布
- **THEN** 系统直接调用后端会话启动并在成功后进入实时面试页，不要求额外令牌

#### Scenario: Backend start fails
- **WHEN** 用户点击“开始面试”但后端启动失败
- **THEN** 系统停留在准备页并展示真实失败原因，不得进入无法回答的实时面试页
