## MODIFIED Requirements

### Requirement: Publish a server-managed billing catalog
系统 SHALL 从可信服务提供已上架的积分包、1 天、3 天、7 天、15 天和 30 天会员商品，并 MUST 展示人民币价格、权益、有效期、正常使用边界和目录版本；收费说明 SHALL 明确：有效时间会员进入笔试免费，没有有效会员的用户进入笔试按服务端费率扣除 30 积分/次。

#### Scenario: User opens the billing page
- **WHEN** 已授权用户打开收费页面
- **THEN** 系统展示当前已上架商品、普通回答点数、截图回答点数、笔试入场规则、退款说明和客服入口

#### Scenario: Product price changes
- **WHEN** 运营发布新的商品价格版本
- **THEN** 新订单使用新版本且历史订单继续展示购买时的价格和权益快照

### Requirement: Apply entitlement precedence
系统 MUST 优先使用有效会员权益；没有有效会员时才使用积分钱包，并 MUST 在会员期内保留用户原有积分。该优先级 SHALL 同时适用于正常回答、截图回答和笔试入场；笔试入场的积分用户仍按当前 `writtenExamPoints` 费率计费。

#### Scenario: Active member starts a written exam
- **WHEN** 有效时间会员用户启动符合条件的笔试会话
- **THEN** 系统允许进入笔试、记录会员用量且不扣积分

#### Scenario: Active member requests an answer
- **WHEN** 有效会员创建符合正常使用规则的回答或截图任务
- **THEN** 系统允许操作、记录会员用量且不扣积分

#### Scenario: Points user starts a written exam
- **WHEN** 没有有效会员的用户启动笔试会话且可用余额不少于当前笔试入场费
- **THEN** 系统从积分钱包扣除当前 `writtenExamPoints` 费率对应的 30 点并允许进入笔试

#### Scenario: Pass expires
- **WHEN** 用户会员到期后创建新回答或启动新的笔试会话
- **THEN** 系统按当前积分费率检查余额且不清除已有积分
