## ADDED Requirements

### Requirement: Stack membership time across entitlement sources
系统 MUST 将付费会员和后台发放会员视为同一条连续会员时间线；确认新的会员权益时，MUST 从当前时间与该用户所有未结束会员权益的最晚到期时间两者中的较晚者开始顺延。

#### Scenario: Paid pass follows an active admin entitlement
- **WHEN** 用户拥有尚未到期的后台发放会员并支付一笔时间会员订单
- **THEN** 新购买时长从后台会员的到期时间开始且不得与现有权益重叠

#### Scenario: Admin entitlement follows a paid pass
- **WHEN** 用户拥有尚未到期的付费会员且管理员发放新的会员时长
- **THEN** 后台发放时长从付费会员的最晚到期时间开始

#### Scenario: User has no active or queued entitlement
- **WHEN** 用户没有任何未结束的会员权益且支付一笔时间会员订单
- **THEN** 新会员从服务端确认支付时间开始生效

### Requirement: Serialize cross-source membership grants
系统 MUST 对同一用户的付费会员到账和后台会员发放使用共同的事务互斥规则，并 MUST 保持订单权益发放幂等。

#### Scenario: Payment and admin grant arrive concurrently
- **WHEN** 同一用户的支付确认与后台会员发放并发执行
- **THEN** 两段权益按串行顺序衔接且不得产生重叠或丢失时长

#### Scenario: Payment notification is replayed
- **WHEN** 已发放会员权益的支付通知被重复投递
- **THEN** 系统返回原支付结果且不得再次增加会员时间

### Requirement: Present purchased extensions without hiding duration
系统 SHALL 根据服务端会员时间线展示当前有效会员、待生效延长段和累计最终到期时间，且 MUST NOT 因不同权益来源而隐藏已经购买的时长。

#### Scenario: Active member buys an extension
- **WHEN** 用户已有有效会员并成功购买新的时间会员
- **THEN** 顶部权益卡按连续时间线展示累计剩余时间和最终到期时间，并展示新权益待生效时长
