## ADDED Requirements

### Requirement: Provide one clear billing and membership destination
系统 SHALL 将现有收费页面作为积分和时间会员的统一权益入口，并 MUST 在应用导航中使用能够同时表达两类权益的名称。

#### Scenario: User opens the application navigation
- **WHEN** 已登录用户查看应用导航
- **THEN** 系统显示“积分与会员”入口并继续导航到现有收费页面

### Requirement: Show active membership as the primary entitlement
系统 MUST 在收费页面顶部显著展示当前有效会员的状态、动态剩余时长和精确到期时间，并 SHALL 同时保留积分余额作为会员到期后的备用权益。

#### Scenario: Active member opens the billing page
- **WHEN** 用户拥有当前时间范围内有效的时间会员
- **THEN** 页面将“会员使用中”和剩余天、小时显示为主权益，同时展示精确到期时间及当前积分余额

#### Scenario: Membership crosses a countdown boundary
- **WHEN** 用户停留在收费页面且会员剩余时间跨过小时或到期边界
- **THEN** 页面自动更新剩余时长；到期后不再声称会员有效，并提示后续操作将使用积分

### Requirement: Explain queued and absent membership states
系统 SHALL 清楚区分待生效会员、当前无会员和有效会员，不得把支付订单状态代替权益状态。

#### Scenario: Active member has an extension queued
- **WHEN** 用户已有有效会员且后续购买的会员权益将顺延生效
- **THEN** 页面同时展示当前会员剩余时长、下一段生效时间和累计最终到期时间

#### Scenario: User has no current membership
- **WHEN** 用户没有有效或待生效的时间会员
- **THEN** 页面明确显示“当前未开通会员”，同时正常展示积分余额和会员购买入口

### Requirement: Refresh entitlements after confirmed payment
系统 MUST 在支付订单被服务端确认为已支付后重新获取可信计费状态，不得只更新订单文案而继续显示旧会员权益。

#### Scenario: Time-pass payment is confirmed while polling
- **WHEN** 收费页面轮询到时间会员订单状态变为已支付
- **THEN** 页面重新加载服务端计费状态并显示新激活或待生效的会员时长，无需用户手动刷新

#### Scenario: Billing-state refresh fails after payment
- **WHEN** 订单已确认支付但最新计费状态暂时获取失败
- **THEN** 页面保留已确认订单、提示权益状态正在同步且允许用户安全重试，不得伪造剩余时长

