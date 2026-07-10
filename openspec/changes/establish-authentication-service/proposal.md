## Why

当前 OfferSteady 的前端原型已经有登录入口、微信登录文案和受保护页面语义，但正式后端还没有统一 Authentication Service 去承接账号、登录、令牌、鉴权和多端会话管理。现在需要先建立独立认证体系，让后续的面试会话、积分、资料、设备和微信登录都能复用同一套身份与权限基础。

## What Changes

- 新增统一 Authentication Service，负责用户注册、登录、JWT Access Token、Refresh Token、用户信息和退出登录。
- 建立 Password Hash、Token Middleware、Session Authentication 和多端登录会话边界。
- 建立可替换的 Identity Provider 扩展点，为后续微信登录接入保留 provider adapter，而不把 OAuth 细节耦合进核心账号体系。
- 建立面向后续会员体系、计费、资料和面试能力复用的统一用户身份与权限模型。
- 保持 Authentication Service 与 Chat Service、Interview Session 和支付体系解耦。

## Capabilities

### New Capabilities
- `authentication-service`: 定义统一账号注册、登录、JWT / Refresh Token、用户资料、注销、令牌鉴权和多端会话管理能力

### Modified Capabilities
- None.

## Impact

- Affected code: `apps/backend` 的用户、认证、token middleware、受保护 API 鉴权和会话令牌存储边界
- APIs: 新增注册、登录、刷新令牌、当前用户、登出和认证状态接口
- Dependencies: password hashing adapter、JWT signing / verification、refresh-token store、future identity-provider adapter
- Product behavior: 为现有登录入口和受保护应用路由提供正式后端能力，但本 Proposal 不实现支付或会员逻辑
