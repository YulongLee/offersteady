## Why

当前结算弹窗把微信支付和支付宝渲染成相同颜色、相同层级的连续按钮，用户难以快速确认自己选择的渠道，也容易误触。双渠道同时开启时需要提供清晰、可辨认且在深色和明亮主题下都稳定的选择入口。

## What Changes

- 将微信支付和支付宝显示为两个相互独立的渠道卡片，而不是视觉连续的通用主按钮。
- 为每个渠道展示对应标识、渠道名称和支付方式说明，并使用各自的品牌强调色。
- 保持现有服务端定价、渠道可用性、下单和回调逻辑不变。
- 增加双渠道、单渠道和响应式显示的 Web 回归测试。

## Capabilities

### New Capabilities

- `distinct-checkout-payment-channel-selection`: 规定双渠道结算弹窗必须让微信支付和支付宝在视觉、文案和交互上清晰区分。

### Modified Capabilities

无。

## Impact

- 修改 `apps/web/src/BillingPage.tsx` 的支付渠道选择结构。
- 修改 `apps/web/src/styles.css` 的渠道卡片样式和响应式布局。
- 更新 Web 支付功能测试；不修改后端 API、支付配置或订单数据。
