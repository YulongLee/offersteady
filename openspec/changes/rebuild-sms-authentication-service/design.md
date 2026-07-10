## Context

OfferSteady 现在已经有 FastAPI 后端认证模块、JWT access token、refresh token、微信兼容登录和前端 `auth-client`，但产品主身份仍带有本地 admin 原型兜底，无法支撑商业化资料库、积分、面试会话和 OSS 用户路径的真实归属。用户希望注册和登录统一走阿里云短信验证码服务。

阿里云短信验证码链路按官方 `Dypnsapi` 2017-05-25 API 设计：发送验证码调用 `SendSmsVerifyCode`，验证码校验调用 `CheckSmsVerifyCode`。如果验证码由阿里云托管校验，短信模板参数需要使用阿里云生成的验证码占位（如 `##code##`），服务端不得把 AccessKey、签名或验证码明文暴露给浏览器。

## Goals / Non-Goals

**Goals:**

- 建立手机号短信验证码注册/登录主路径，验证码校验通过后自动创建或登录用户。
- 复用现有 Authentication Service 的 user、auth session、JWT access token、refresh token 和受保护 API 鉴权边界。
- 新增 Aliyun SMS provider adapter，使发送/校验能力可配置、可替换、可测试。
- 让前端登录/注册入口真实调用后端 API，并移除主流程对 `admin` 原型身份的强制兜底。
- 支持商业化用户归属：资料库、积分、面试、桌面绑定都能读取真实 `userId`。
- 建立发送频率、校验失败次数、日志脱敏、错误分类和本地集成验收。

**Non-Goals:**

- 不实现微信登录改造、第三方 OAuth、实名认证、企业组织、复杂 RBAC。
- 不实现支付会员或积分购买逻辑，只保证认证后用户身份可被积分系统引用。
- 不在前端存储阿里云密钥、验证码明文或长期 refresh token 以外的服务端秘密。
- 不把真实手机号或验证码写入测试夹具；测试数据必须合成或脱敏。

## Decisions

### Decision: Use passwordless phone identity as the commercial primary login

注册和登录合并为同一条手机号验证码流程：手机号校验通过后，如果用户不存在则创建用户；如果已存在则创建新的 auth session。

Alternatives considered:

- Keep password registration as primary: 已有框架可用，但用户明确要求短信验证码注册/登录，且面试类产品移动端/桌面联动更适合手机号身份。
- Separate register and login forms: 产品上会增加无意义分支，短信校验本身已经能证明手机号控制权。

### Decision: Keep Aliyun SMS behind a provider port

新增 `SmsVerificationProviderPort`，生产实现调用阿里云 `SendSmsVerifyCode` / `CheckSmsVerifyCode`，本地测试实现使用 deterministic fake provider。Authentication Service 只依赖 port，不直接依赖 Aliyun SDK 细节。

Alternatives considered:

- Directly call Aliyun from route handlers: 实现快，但会把签名、错误映射、重试和测试替身散落在 API 层。
- Self-generate code and send generic SMS: 会让官方 `CheckSmsVerifyCode` 无法承担校验闭环，也增加验证码存储和泄露风险。

### Decision: Store SMS challenge metadata, not code plaintext

后端保存 challenge id、phone hash、send status、request id、expires at、attempt counters、provider biz id 和错误分类。若使用阿里云托管验证码，不保存验证码明文；若本地 fake provider 需要模拟验证码，也只允许在测试内存中保存。

Alternatives considered:

- Store raw phone and code in one table: 调试方便，但不符合敏感信息最小化。
- Store no local challenge state: 无法做业务限流、页面状态恢复、错误审计和第三方故障归因。

### Decision: Token/session contract stays compatible

短信登录成功后返回现有 `AuthenticationResultResponse` 形态：`user`、`tokens`、`authSessionId`。新增 `loginProvider="sms"` 或 `phone"` identity binding，但不破坏 refresh/logout/me/sessions 的现有边界。

Alternatives considered:

- Create separate SMS token format: 会导致受保护 API 和前端 adapter 双轨，后续资料/面试/积分更难统一。

### Decision: Frontend keeps current prototype layout but uses real auth state

Web 端新增发送验证码、倒计时、验证码输入、提交、错误提示和登录态恢复。主流程不得继续把所有用户归一成 `admin`；只有开发显式开关或测试场景可使用原型身份。

Alternatives considered:

- Keep admin fallback for convenience: 会继续造成 OSS/数据库/前端资料不同步，商业化用户隔离无法验证。

## Risks / Trade-offs

- [Risk] 阿里云验证码模板或签名配置错误导致发送失败 -> [Mitigation] 增加启动配置校验、provider probe、错误码映射和后台诊断说明。
- [Risk] 短信接口被刷导致费用或风控风险 -> [Mitigation] 按手机号、IP、设备指纹、会话设置发送频率和每日上限。
- [Risk] 用户换号或多账号合并后资料归属复杂 -> [Mitigation] 本 change 只建立手机号 identity binding，不实现换绑；后续通过账号安全 change 处理。
- [Risk] 前端本地 token 存储有 XSS 暴露面 -> [Mitigation] MVP 先保持现有 localStorage 兼容，生产硬化阶段可迁移到 HttpOnly refresh cookie。
- [Risk] 阿里云官方校验依赖模板 `##code##` 配置 -> [Mitigation] 在文档和 provider probe 中检查配置说明，避免使用自生成验证码误接 `CheckSmsVerifyCode`。

## Migration Plan

1. 增加配置项和 provider port：Aliyun AccessKey、endpoint、region、sign name、template code、TTL、发送/校验限流参数。
2. 增加数据库表或 repository 字段：phone identity、sms challenge metadata、auth session provider 字段。
3. 实现后端 API：`POST /api/v1/auth/sms/send-code`、`POST /api/v1/auth/sms/verify-login`，并复用现有 `/refresh`、`/me`、`/logout`。
4. 改造前端登录入口和 `auth-client`，保存真实短信登录 session，不再主流程强制写入 admin。
5. 逐步把资料、积分、面试、桌面绑定的默认用户上下文从 admin 迁移到认证用户。
6. 增加单元测试、provider fake、集成配置校验和 OpenSpec 校验。
7. 回滚时可保留旧 password/wechat endpoint；短信入口隐藏或回退到兼容登录，不删除 user/session 数据。

## Open Questions

- 阿里云短信签名、模板 Code 和 Dypnsapi endpoint 是否已经在生产控制台创建完成。
- 正式上线时 refresh token 是否继续 localStorage，还是切换 HttpOnly cookie。
- 是否需要在同一个手机号绑定微信身份时做账号合并提示。
