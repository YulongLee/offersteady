## ADDED Requirements

### Requirement: 国服客服账号统一展示

国服运行时客服信息和公开产品页面 MUST 展示 `mianshiwen_01` 作为客服微信账号，并保留现有客服邮箱作为补充渠道。

#### Scenario: 运行时状态返回新账号

- **WHEN** 国服客户端请求 billing 或 web state 数据
- **THEN** 客服微信字段为 `mianshiwen_01`，不得返回 `mianshiwen-cn`

#### Scenario: 公开页面展示新账号

- **WHEN** 用户访问国服首页、联系页、使用说明或法律页面
- **THEN** 页面展示 `mianshiwen_01`，并保留 `contact@oneshowailab.com` 邮箱入口

#### Scenario: 国际服保持独立

- **WHEN** 国际服构建或运行时配置被加载
- **THEN** 本变更不得修改国际服客服账号或页面文案
