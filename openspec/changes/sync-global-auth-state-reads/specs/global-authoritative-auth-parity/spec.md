## ADDED Requirements

### Requirement: Global access authentication remains authoritative per request
Global Backend MUST 对每次受保护请求校验当前令牌和权威会话、用户可用性/active restriction；PostgreSQL 常态 MUST 使用一个连接/SELECT 获取必要状态，不再加载未消费的完整用户/密码/bindings。系统 MUST NOT 增加跨请求正鉴权缓存或新的绑定准入条件，MUST 保留 Global 原错误、最小 schema 兼容和内存 `get_user` 扩展语义。

#### Scenario: Repeated valid requests use consolidated authority
- **WHEN** 有效 Global access token 在 60 秒内多次请求受保护接口
- **THEN** 每次读取权威状态，常态每请求一个 PostgreSQL 连接/SELECT、无活动写行，身份与原响应一致

#### Scenario: Authentication state changes before the next request
- **WHEN** 一次成功后会话被撤销/到期/删除、用户被限制或按原流程凭据变化导致撤销
- **THEN** 下一次请求按当次权威读取和原错误合同处理，没有新增授权宽限

#### Scenario: Invalid tokens and unavailable authority fail closed
- **WHEN** 令牌缺失/坏签名/过期/类型非 access、会话不匹配或权威读取失败
- **THEN** 请求按原安全错误处理且不 touch/执行业务，合法签名但非 access 类型也拒绝，不变更合法 access 的 key/算法/issuer/claims

### Requirement: Global session metadata updates are throttled and race safe
last-used MUST 相隔至少 60 秒后由下一合法请求条件更新，同窗口至多一次实际行写；CAS MUST 只更新活动元数据，不 UPSERT、不延长授权、不覆盖 owner/status/revoked/refresh/issued/expiry。会话到期持久化 MUST 保护旧快照竞争，内存保存与 CAS MUST 共用锁。

#### Scenario: Concurrent due touches race in one interval
- **WHEN** 多个请求同时读到同一到期更新窗口
- **THEN** 允许多次条件尝试但实际行更新至多一次，安全字段和到期时间保持

#### Scenario: Revocation deletion refresh or password reset commits first
- **WHEN** 旧请求读取后，撤销/删除/刷新/改密或重置相关会话变更先提交，再恢复旧 touch 或 expiry 写入
- **THEN** 旧元数据/过期写入不复活、不插入且不覆盖新状态/凭据/有效期，后续请求看到新权威结果

### Requirement: Global account lifecycle and language contracts are preserved
迁移 MUST 保留 Global 邮箱验证/密码注册登录、刷新、改密、重置、退出、多设备、Admin 隔离、默认及会话语言的既有合同，不迁入 CN SMS/错误文案/权益或改动密码策略。

#### Scenario: Global lifecycle executes against the actual source candidate
- **WHEN** 合成账号执行邮箱/密码登录及注册、刷新、当前用户、改密/重置和退出
- **THEN** 正常/失效/他设备撤销和原返回结构保持，默认与面试语言保留，Admin 与 CN 行为不被混入
