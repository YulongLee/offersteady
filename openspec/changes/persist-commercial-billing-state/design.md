# Design

## Storage model

继续使用现有 `points_redemption_ledger` 作为不可变积分总账，放宽其类型约束以接纳欢迎赠送、购买入账和知识库结算。新增官方订单、会员权益、知识库报价及预留表。订单保存下单时的商品快照，避免后续目录变化影响历史订单。

## Transaction boundaries

- 欢迎积分通过唯一 `reference_id` 幂等写入。
- 创建订单以 `(user_id, idempotency_key)` 唯一约束防止重复下单。
- 支付回调锁定订单；金额不符只更新失败状态，金额正确则在同一事务中更新订单并写入积分或会员权益。
- 知识库预留锁定用户账务键，余额计算扣除未结算预留，防止并发超额消费。
- 结算写入唯一负向流水并更新预留；释放只更新预留状态，不改账本。

## Runtime selection

`billing_service` 在配置数据库且不处于 pytest 默认隔离模式时使用 PostgreSQL 仓储。生产环境必须有数据库且初始化失败直接失败；开发环境可回退内存实现。

## Compatibility

现有 REST 请求和响应结构保持不变。服务层保留内存路径用于单元测试，PostgreSQL 路径返回相同领域记录。

