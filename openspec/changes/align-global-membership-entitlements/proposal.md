## Why

国际服当前已经有独立的 Global Commerce 后端，但前端仍复用国服积分与会员页面，导致订阅剩余时间、截图权益和知识库额度展示不准确。现在国际服已进入正式商业化使用阶段，需要把会员权益、使用量和知识库配额统一为可解释、可审计且不与国服计费混用的模型。

## What Changes

- 为国际服提供独立的会员权益展示：当前套餐、剩余时间、到期/续费时间、自动续费状态和已排队权益。
- 国际服前端不再展示国服积分余额、积分流水、兑换码和国服支付入口；改为展示 Global Commerce 套餐与权益。
- 付费会员的实时回答和截图回答使用会员权益，不扣国服积分；Free 账号保留有限的体验额度。
- 为 Global Commerce 增加知识库 Token 配额及使用量结算：1 天会员不含知识库，7 天/30 天/90 天会员分别提供分级额度。
- 知识库上传按照服务端解析出的可索引 Token 进行预估、预留、结算和释放，失败或取消不得消耗额度。
- 保持历史已购买权益的商品快照不变；新额度仅适用于新发布的套餐版本或续费周期。
- 保留现有 Creem 订单、订阅、验签和支付流程，不模拟支付成功，不修改国服计费规则。

## Capabilities

### New Capabilities

- `global-membership-entitlements`: 定义国际服订阅状态、会员剩余时间、截图/实时回答权益和知识库 Token 配额。

### Modified Capabilities

无。

## Impact

- `apps/backend/app/ports/global_commerce.py`、Global Commerce 服务、PostgreSQL repository 和迁移。
- 国际服前端 billing state 适配与会员页面展示。
- 知识库上传报价、预留、结算和释放流程。
- Global Commerce API 响应、回归测试、构建和国际服部署验证。
- 不影响国服 `/api/v1/billing/*` 计费、订单、支付和现有用户数据。
