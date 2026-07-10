## ADDED Requirements

### Requirement: Publish a server-managed billing catalog
系统 SHALL 从可信服务提供已上架的积分包、3 天、7 天、15 天和 30 天会员商品，并 MUST 展示人民币价格、权益、有效期、正常使用边界和目录版本。

#### Scenario: User opens the billing page
- **WHEN** 已授权用户打开收费页面
- **THEN** 系统展示当前已上架商品、普通回答点数、截图回答点数、退款说明和客服入口

#### Scenario: Product price changes
- **WHEN** 运营发布新的商品价格版本
- **THEN** 新订单使用新版本且历史订单继续展示购买时的价格和权益快照

### Requirement: Offer fixed-duration passes
系统 SHALL 提供 3 天、7 天、15 天和 30 天会员，并 SHALL 从权益激活时间开始按连续小时计算到期时间。

#### Scenario: User buys a pass without an active pass
- **WHEN** 一笔时长会员订单确认到账
- **THEN** 系统从到账时间开始激活对应天数并展示精确到期时间

#### Scenario: User extends an active pass
- **WHEN** 有效会员用户再次购买时长会员
- **THEN** 新时长从当前会员结束时间顺延且不得覆盖剩余权益

#### Scenario: Long pass knowledge allowance activates
- **WHEN** a 15-day or 30-day entitlement segment reaches its start time
- **THEN** the system activates two knowledge indexing allowances that expire with that segment

### Requirement: Apply entitlement precedence
系统 MUST 优先使用有效会员权益；没有有效会员时才使用积分钱包，并 MUST 在会员期内保留用户原有积分。

#### Scenario: Active member requests an answer
- **WHEN** 有效会员创建符合正常使用规则的回答或截图任务
- **THEN** 系统允许操作、记录会员用量且不扣积分

#### Scenario: Pass expires
- **WHEN** 用户会员到期后创建新回答
- **THEN** 系统按当前积分费率检查余额且不清除已有积分

### Requirement: Explain unlimited-use boundaries
系统 MUST 将会员权益描述为“会员期内回答和截图不扣积分”，并 SHALL 同时展示账号本人使用、并发、安全和防滥用边界，不得宣传无法兑现的绝对无限。

#### Scenario: Member reaches a safety limit
- **WHEN** 会员请求触发公开说明的并发或安全限制
- **THEN** 系统显示具体限制和恢复方式且不悄悄改为扣积分

### Requirement: Show billing state during interviews
系统 SHALL 在准备中心展示当前会员剩余时间或积分余额，并 SHALL 在积分页面展示实时操作适用费率。实时工作台只需提供积分页入口，MUST NOT 在自动回答、手动回答或截图按钮附近展示点数；服务端在创建计费操作前仍 MUST 使用当前费率校验权益。

#### Scenario: Points user opens screenshot input
- **WHEN** 非会员用户准备提交截图问题
- **THEN** 界面提供积分页入口以查看当前截图费率，实时截图确认按钮不重复展示点数，服务端按当前费率校验余额

#### Scenario: Balance is insufficient
- **WHEN** 用户余额低于当前操作费用且没有有效会员
- **THEN** 系统不创建新的 AI 任务，并提供前往收费页的入口而不隐藏历史回答

### Requirement: Protect existing entitlements from catalog changes
系统 MUST 保存订单和权益快照，并 MUST 不因商品下架、调价或毛利告警削减已经确认支付的权益。

#### Scenario: An unprofitable pass is unpublished
- **WHEN** 运营停止销售一项会员商品
- **THEN** 新用户无法购买该商品，但已激活会员继续使用到原到期时间
