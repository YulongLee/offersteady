## Why

支付宝电脑网站支付请求被网关以 `invalid-signature` 拒绝。请求签名错误地复用了通知验签参数过滤规则，未把 `sign_type=RSA2` 纳入待签名字符串。

## What Changes

- 将支付宝出站请求签名与异步通知验签的规范化规则分离。
- 支付下单和主动查单签名包含所有非空业务参数（仅排除 `sign`）。
- 异步通知验签继续排除 `sign` 和 `sign_type`，不改变回调安全行为。
- 增加使用公钥独立验签请求签名的回归测试，避免系统自签自验掩盖协议错误。

## Capabilities

### New Capabilities

- `alipay-request-signing`: 规定支付宝官方网关请求与通知使用各自正确的 RSA2 待签名字符串。

### Modified Capabilities

无。

## Impact

- 后端支付宝支付适配器和专项测试。
- 不改变管理配置、订单数据模型、公开 API 或前端交互。
