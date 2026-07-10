## Why

当前 OfferSteady 已经进入资料、面试、积分和桌面助手联调阶段，但用户注册/登录仍没有围绕商业化使用建立稳定的手机号身份体系。需要基于阿里云短信验证码服务重建注册与登录能力，让用户身份、积分、资料库、OSS 用户路径和面试会话都绑定到真实用户。

## What Changes

- 新增手机号短信验证码注册/登录主流程：用户输入手机号获取验证码，验证码校验通过后自动创建或登录账号。
- 接入阿里云 `Dypnsapi` 短信验证码能力，发送验证码使用 `SendSmsVerifyCode`，校验验证码使用 `CheckSmsVerifyCode`，服务端负责签名、密钥和接口适配。
- 新增短信验证码限流、安全审计和错误分类，覆盖发送频率、校验失败次数、验证码过期、手机号格式、第三方服务异常和风控拦截。
- 新增后端用户身份、认证会话、JWT access token、refresh token、退出登录和当前用户接口，使资料库、积分、面试会话和桌面绑定都可读取同一用户上下文。
- 更新 Web 登录/注册入口，保留当前原型视觉与交互范式，但真实调用后端 API，不在前端保存服务端密钥。
- 更新环境变量和联调文档，明确阿里云短信、JWT、数据库、日志脱敏和本地/生产配置边界。
- 非目标：本 change 不实现微信登录、第三方 OAuth、实名认证、企业账号、复杂 RBAC 或支付会员逻辑。

## Capabilities

### New Capabilities

- `sms-authentication-service`: 定义手机号短信验证码发送、校验、自动注册/登录、用户身份、令牌会话、安全限流和前端接入能力。

### Modified Capabilities

- None.

## Impact

- Affected backend areas: `apps/backend` 用户模型、认证模块、短信 provider adapter、token/session 服务、鉴权依赖、受保护 API 当前用户解析。
- Affected frontend areas: `apps/web` 登录/注册页面、认证状态存储、受保护路由、资料/面试/积分等页面的用户态加载。
- Affected database: users、phone identity、auth sessions、refresh token、sms challenge 或审计表。
- Affected dependencies: Aliyun OpenAPI SDK or signed HTTP client for `Dypnsapi` 2017-05-25, JWT/signing library, passwordless session storage.
- Affected docs: `docs/environment-variables.md`, backend README/local runbook, authentication integration troubleshooting.
- Security/privacy: 手机号、验证码、token、IP、设备信息必须脱敏记录；短信密钥只能存在后端环境变量或部署密钥系统。
