# Commercial Billing Persistence Specification

## ADDED Requirements

### Requirement: Persist wallet history and balance
系统 MUST 将欢迎积分、兑换积分、购买积分和知识库结算记录为 PostgreSQL 中不可变积分流水，并 MUST 从流水计算余额。

#### Scenario: User returns after a backend restart
- **WHEN** 用户已获得积分且后端进程重启
- **THEN** 用户看到与重启前一致的余额和流水

#### Scenario: Welcome grant is requested concurrently
- **WHEN** 同一用户的多个请求同时初始化钱包
- **THEN** 欢迎积分只写入一次

### Requirement: Persist checkout orders idempotently
系统 MUST 持久化订单商品快照、金额、渠道、支付动作和状态，并 MUST 以用户范围内幂等键避免重复创建订单。

#### Scenario: Checkout creation is retried
- **WHEN** 用户使用相同幂等键重试创建订单
- **THEN** 系统返回原订单且不创建第二笔订单

#### Scenario: User refreshes after creating an order
- **WHEN** 用户刷新页面或后端重启
- **THEN** 订单仍出现在该用户订单列表中

### Requirement: Apply payment callbacks atomically
系统 MUST 在一个事务中校验金额、更新订单并发放积分或会员权益，重复回调 MUST 不重复发放权益。

#### Scenario: Paid callback is delivered twice
- **WHEN** 支付平台重复发送同一订单的成功回调
- **THEN** 订单保持已支付且只产生一次积分入账或一份会员权益

#### Scenario: Callback amount does not match
- **WHEN** 回调金额与订单快照金额不同
- **THEN** 订单标记失败且不发放任何权益

### Requirement: Persist knowledge indexing reservations
系统 MUST 持久化知识库计费报价与预留，并 SHALL 在可用余额中扣除未结算预留，防止并发超额消费。

#### Scenario: Two indexing requests compete for the same balance
- **WHEN** 两个并发预留合计超过用户余额
- **THEN** 仅余额允许的预留成功，其余返回余额不足

#### Scenario: Reserved indexing completes
- **WHEN** 已预留索引任务成功完成
- **THEN** 系统原子写入一次负向结算流水并将预留标记为已结算

### Requirement: Fail closed in production
生产环境 MUST 使用 PostgreSQL 账务仓储，数据库缺失或初始化失败时 MUST 拒绝账务操作，不得回退进程内存。

#### Scenario: Production database is unavailable
- **WHEN** 账务仓储无法连接数据库
- **THEN** 服务启动或依赖初始化失败并报告账务持久化不可用
