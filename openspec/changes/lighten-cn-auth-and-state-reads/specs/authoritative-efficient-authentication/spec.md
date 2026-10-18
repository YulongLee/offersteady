## ADDED Requirements

### Requirement: Every protected request validates authoritative authentication state
系统 MUST 在每次受保护请求读取当前权威会话和现有安全判断所需用户可用性/限制状态，在保留签名、类型、到期和会话校验的前提下，使用请求内合并读取减少 PostgreSQL 独立连接及重复查询。PostgreSQL 鉴权 MUST 不再为未消费的完整用户/密码/身份绑定产生额外读取；内存仓库 MUST 保留 `get_user` 的既有可用性判定扩展语义。系统 MUST 不增加新的绑定准入条件，并保留绑定变更导致的原会话撤销流程。系统 MUST NOT 引入跨请求正鉴权缓存或仅凭未到期 JWT 继续授权。

#### Scenario: A valid request uses the consolidated read
- **WHEN** 当前有效用户使用活跃会话的有效 access token 调用受保护接口
- **THEN** 返回原安全身份及响应合同，合成仓库计数证明常态权威读取使用一个连接和一个 SELECT，且本次读取结果仅在本请求使用；窗口到期的元数据更新可另用一个连接

#### Scenario: Security state changes between requests
- **WHEN** 首次请求成功后会话被退出/撤销/过期，或用户不可用/封禁、绑定变更触发撤销、凭据或 refresh 生命周期按现有规则改变
- **THEN** 下一次请求使用权威状态按原合同拒绝或允许，不因先前成功鉴权结果而产生额外授权宽限

#### Scenario: Invalid or missing authentication input
- **WHEN** 令牌缺失、签名/类型无效、令牌过期，或会话/用户不存在或不满足原可用条件
- **THEN** 按原状态码和错误返回，拒绝请求且不执行活动 touch 或业务副作用

### Requirement: Session usage metadata is throttled without changing authorization
合法鉴权的登录会话 last-used 元数据 MUST 限制为每 60 秒窗口至多一次实际行更新。更新 MUST 不延长授权期限、不改写状态/凭据/令牌/撤销字段，MUST NOT 使用会插入缺失行或覆盖旧快照的 UPSERT/整行保存路径。

#### Scenario: Frequent valid requests within one interval
- **WHEN** 同一活跃会话在不足 60 秒内连续或并发提交多个合法请求
- **THEN** 所有请求保持原授权结果，数据库实际活动行更新至多一次，且每次请求仍读取权威安全状态

#### Scenario: The touch interval elapses
- **WHEN** 活跃会话最后使用时间距当前达到 60 秒且下一个合法请求到达
- **THEN** 只更新允许的使用元数据至当前时间，令牌/会话到期和其他安全字段不变

### Requirement: Touch never revives or overwrites concurrent security changes
touch MUST 使用竞争安全条件，既不能把删除/撤销/过期的会话恢复为活跃，也不能覆盖并发刷新令牌、改密或权限变化。缺失/不匹配的目标 MUST 保持原状态；合并读取失败 MUST NOT 被当成成功授权。

#### Scenario: Expiry observation races with refresh
- **WHEN** 旧请求读到会话到期，另一个事务已刷新有效期或撤销会话后才恢复旧请求的到期持久化
- **THEN** 旧请求使用条件更新，不覆盖已经提交的新会话状态或有效期

#### Scenario: Revocation commits before a delayed touch
- **WHEN** 旧鉴权读取后，另一事务撤销/删除/过期该会话，再恢复旧请求的 touch
- **THEN** touch 不复活会话、不清除撤销、不插入新行，后续鉴权按原合同拒绝

#### Scenario: Refresh or password lifecycle changes concurrently
- **WHEN** 旧鉴权读取后会话 refresh token 轮换，或改密/重置按原规则保留或撤销会话
- **THEN** 旧 touch 不覆盖新凭据/有效期/会话状态，后续 refresh 与 access 判定保持原生命周期语义

#### Scenario: PostgreSQL and in-memory repositories share the contract
- **WHEN** 使用合成用户在内存与隔离 PostgreSQL 仓库运行相同合法、缺失、限制和安全竞争场景
- **THEN** 两者授权结果、允许更新字段和不复活保证一致，且不读取真实用户凭据

### Requirement: Shared authentication preserves regional commercial isolation
共享鉴权优化 MUST 保留 CN 手机/SMS、Global 邮箱/密码与独立 Admin 入口的既有行为，不改变任一区域会员、积分、模拟面试收费或功能开关。

#### Scenario: Global account lifecycle uses the optimized boundary
- **WHEN** Global 合成账号执行登录、刷新、当前用户、改密、重置和退出后的受保护读取
- **THEN** 保留其原响应及安全生命周期，未导入 CN 的收费/权益判断且无跨区域数据访问
