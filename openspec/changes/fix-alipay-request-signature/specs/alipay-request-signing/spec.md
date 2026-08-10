## ADDED Requirements

### Requirement: 支付宝出站请求签名
系统 MUST 按支付宝官方网关规则对全部非空请求参数签名，并 MUST 将 `sign_type=RSA2` 纳入下单和主动查单的待签名字符串；只有 `sign` 本身不得参与签名。

#### Scenario: 电脑网站支付请求可被独立验签
- **WHEN** 系统生成支付宝电脑网站支付 URL
- **THEN** 使用应用公钥对 URL 中除 `sign` 外的全部非空参数排序拼接后执行 RSA2 验签 MUST 成功

#### Scenario: 主动查单请求包含签名类型
- **WHEN** 系统调用支付宝主动查单接口
- **THEN** 请求签名 MUST 覆盖 `sign_type=RSA2`

### Requirement: 支付宝通知验签边界
系统 MUST 按支付宝异步通知规则排除 `sign` 和 `sign_type` 后验签，不得因修复出站请求而改变通知验签参数集合。

#### Scenario: 有效通知继续通过验签
- **WHEN** 支付宝通知使用排除 `sign` 与 `sign_type` 的字符串生成有效签名
- **THEN** 系统 MUST 验签成功并继续校验 AppID、卖家身份、金额和交易状态
