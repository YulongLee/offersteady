# Payment Recovery and Reconciliation Specification

## ADDED Requirements

### Requirement: Expire abandoned checkout orders
系统 MUST 持久化订单过期时间，并 SHALL 将超过支付有效期且仍待支付的订单标记为 `expired`。

#### Scenario: User returns after checkout expires
- **WHEN** 用户在支付有效期后刷新积分页面
- **THEN** 原订单显示已过期且不会被误认为仍可支付

#### Scenario: Valid paid callback arrives after expiry
- **WHEN** 已过期订单随后收到验签成功且金额一致的支付成功回调
- **THEN** 系统仍将订单置为已支付并恰好发放一次权益

### Requirement: Audit callbacks without retaining secrets
系统 MUST 持久化支付回调指纹、必要交易元数据和处理结果，并 MUST NOT 保存商户密钥、完整签名或完整请求体。

#### Scenario: Invalid signature callback arrives
- **WHEN** 回调验签失败
- **THEN** 系统记录脱敏拒绝事件、不修改订单或权益并向平台返回失败

#### Scenario: Same callback is delivered repeatedly
- **WHEN** 平台重复发送相同回调
- **THEN** 系统保留单一事件记录且订单权益最多发放一次

### Requirement: Surface reconciliation exceptions
系统 MUST 为未知订单、金额不符和回调处理异常创建持久化对账异常，供服务器运维报告查询。

#### Scenario: Paid callback references an unknown order
- **WHEN** 验签成功的支付回调包含不存在的订单号
- **THEN** 系统返回失败并创建 `unknown_order` 对账异常

#### Scenario: Paid callback amount differs from order
- **WHEN** 回调金额与订单快照金额不同
- **THEN** 系统不发放权益并创建 `amount_mismatch` 对账异常

### Requirement: Provide a secret-safe operations report
系统 SHALL 提供仅服务器侧执行的对账报告，汇总待支付、过期、支付成功、失败回调和未解决异常数量。

#### Scenario: Operator runs reconciliation report
- **WHEN** 授权运维人员在服务器执行报告命令
- **THEN** 命令返回分类计数和安全异常标识，不输出用户资料、支付签名或商户密钥

