## Why

当前产品原型已经把“微信登录 / 注册”作为主入口，但正式后端还没有一条可联调、可替换为正式微信开放平台的登录链路。现在需要先把扫码登录、自动注册、令牌、会话和统一 User ID 绑定能力定义清楚，这样后续资料、面试、截图、语音和历史记录才能真正建立在同一身份体系上。

## What Changes

- 新增 WeChat Login Service 变更，建立与正式微信扫码登录一致的业务流程和接口设计。
- 定义登录页的扫码授权入口、授权会话、授权回调、自动注册、JWT Access Token、Refresh Token、登录态保持、退出登录和当前用户信息接口。
- 增加 provider 解耦边界：开发阶段可接兼容正式接口的认证 Provider 联调，上线前可切换到正式微信开放平台而不改业务层。
- 定义统一 User ID 绑定要求，让 Resume、JD、Knowledge Base、Interview Session、Conversation、Screenshot、Speech 和 History 都通过同一身份体系归属与鉴权。
- 保持当前批准的产品原型交互顺序不变，不新增测试专用页面分支。

## Capabilities

### New Capabilities
- `wechat-login-service`: 覆盖微信扫码登录、授权回调、自动注册、JWT / Refresh Token、登录态保持、登出、当前用户和认证中间件能力
- `authenticated-user-binding`: 覆盖所有核心业务资源统一绑定 User ID、按用户隔离访问和受保护 API 鉴权边界

### Modified Capabilities
- None.

## Impact

- Affected code: `apps/web` 登录页与扫码授权弹层、`apps/backend` 认证接口、provider adapter、token middleware、current-user 和 logout 能力
- APIs: 新增微信授权会话、授权回调、token 刷新、当前用户、登出和认证态查询接口
- Dependencies: WeChat-compatible identity provider adapter、JWT signing / verification、refresh-token session store、provider state validation
- Product behavior: 用户通过微信扫码进入 OfferSteady，首次登录自动创建账号，后续所有资料与面试相关数据统一绑定同一 User ID
