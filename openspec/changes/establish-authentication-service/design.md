## Context

OfferSteady 当前已经有公开首页、登录入口、微信登录说明、受保护页面语义，以及后续面试、资料、积分、设备和桌面伴随程序这些都需要“知道当前是谁”的产品基础。但正式后端仍缺少统一的 Authentication Service，导致账号、登录、JWT、refresh、多端会话和鉴权中间件还没有独立主线。

这次设计需要先建立一套和业务能力解耦的认证体系，满足：

- first-party 账号注册与密码登录
- JWT access token
- refresh token 与多端会话
- current-user / logout
- token middleware / dependency
- session authentication
- future WeChat login adapter
- future membership / entitlement linkage

同时要遵守这些约束：

- 不把密码、refresh token 或签名密钥暴露到客户端
- 不把认证逻辑耦合进 Chat Service 或 Interview Session Service
- 兼容现有前端原型的登录入口和受保护路由语义
- 微信登录这次只保留扩展位，不实现真实 OAuth
- 会员和支付不纳入本次范围

## Goals / Non-Goals

**Goals:**

- 建立统一 Authentication Service
- 支持注册、登录、JWT access token、refresh token、current user、logout
- 提供 password hash、token middleware 和多端 session 模型
- 让受保护 API 可以统一消费 authenticated identity
- 为后续微信登录和会员体系保留稳定扩展点

**Non-Goals:**

- 不实现支付
- 不实现会员权益计算
- 不实现真实微信 OAuth 回调链路
- 不在本次变更中改写 Chat、Interview Session、Billing 等业务服务内部逻辑
- 不把客户端认证策略限定为单一 Cookie 或单一移动端方式

## Decisions

### 1. Use Authentication Service as an independent identity boundary

Authentication Service 作为独立服务层负责：

1. register account
2. verify password
3. issue access token
4. issue refresh token
5. validate authenticated request
6. revoke one device session
7. return current-user summary

原因：

- OfferSteady 后续会有资料、面试、积分、设备和运营能力，不能让每个模块各自处理登录
- 认证边界越早独立，后面接微信登录和会员体系越稳定
- 有利于测试、安全审查和审计

备选方案：

- 在 Interview Session 或 Web app shell 内部顺手做登录：实现快，但会把账号逻辑和业务服务绑死

### 2. Use JWT access token plus stored refresh-token-backed sessions

短期 access token 采用 JWT，长期续期依赖服务端可撤销的 refresh-token-backed session。模型上区分：

- access token：短时、无状态校验为主
- refresh token：长时、服务端可撤销、按设备会话管理

原因：

- 短 token 更适合高频 API 鉴权
- refresh token 存储后才能支持 logout、多端登录、主动撤销和未来风控
- 与桌面端、Web、多设备场景更匹配

备选方案：

- 只用长期 JWT：实现简单，但撤销、登出和多端会话控制较差
- 只用服务端 session cookie：对未来跨端和 API 客户端兼容性较弱

### 3. Store passwords only as salted password hashes behind a replaceable hashing adapter

密码处理通过可替换 hashing adapter 完成，服务只保存 salted hash 和必要元数据，不保存明文密码或可逆凭据。

原因：

- 这是认证最基本的安全底线
- 适配器边界有利于后续升级算法或参数
- 与未来外部身份 provider 并存也更自然

备选方案：

- 直接在 service 里散写 hashing 逻辑：实现快，但升级和审查成本更高

### 4. Keep auth middleware shared and feature-agnostic

受保护接口不自己解析 JWT，而是统一通过 auth middleware / dependency 获取：

- authenticated user id
- auth session id
- token status

原因：

- 避免不同 API 对“过期、撤销、非法 token”的处理不一致
- 更方便让后续 feature module 复用
- 有利于补统一审计和安全测试

备选方案：

- 每个模块单独写 token 校验：会造成重复代码和安全不一致

### 5. Model multi-device login as separate revocable auth sessions

一次登录对应一条独立 auth session，至少包含：

- session id
- user id
- refresh token fingerprint
- device / client label
- issued / last-used / revoked timestamps

原因：

- 用户可能同时在电脑和手机使用
- 后续设备管理、异常会话查看、微信绑定和桌面伴随程序都需要“会话”概念
- logout 不应默认为踢掉所有设备

备选方案：

- 一个用户只保留一个全局会话：实现简单，但不符合多端登录要求

### 6. Preserve a provider-agnostic identity-provider extension point

核心账号体系与 external identity provider 分开：本次先做 first-party auth，未来微信登录通过 provider adapter 接入，并在需要时与内部账号绑定。

原因：

- 微信登录文档已经要求服务端适配器与一次性 state 校验
- 先把内部账号和会话模型稳定下来，再接 provider 风险更小
- 可以避免让 OAuth 流程污染核心 token 契约

备选方案：

- 直接把微信登录做成唯一账号方式：会拖慢当前基础认证落地，也降低后续灵活性

### 7. Keep auth data and logs minimally exposed

普通日志只记录：

- request id
- auth session id
- user id hash or safe identifier
- outcome
- latency
- error class

不记录：

- plaintext password
- refresh token
- raw password hash
- JWT signing secret
- long-lived provider secret

原因：

- 认证数据天然高敏感
- 日志泄露后果比普通业务日志更严重
- 仍需要足够的排障和安全审计能力

备选方案：

- 在调试日志里输出更多 token / hash 细节：短期方便，但风险过高

## Risks / Trade-offs

- [Risk] JWT + refresh token + multi-session 比单一登录方案更复杂 → Mitigation: 把 access / refresh / session 三层边界明确拆开
- [Risk] 认证过早耦合微信流程会放大接入复杂度 → Mitigation: 本次只保留 provider adapter 扩展点，不提前实现真实 OAuth
- [Risk] 多端登录会提高 session 管理复杂度 → Mitigation: 从一开始把登录建模成独立可撤销 auth session
- [Risk] 不同 feature 未来可能绕过统一鉴权 → Mitigation: 强制受保护 API 通过 shared middleware / dependency 获取用户身份
- [Risk] token、密码或 provider 密钥泄露会带来高安全风险 → Mitigation: server-side secret management、最小化日志和 refresh token revocation

## Migration Plan

1. 在 OpenSpec 中定义 Authentication Service 的能力、令牌模型和扩展边界
2. 在 `apps/backend` 中建立 user model、password hash adapter、JWT issuer / verifier、refresh-session store 和 auth middleware
3. 为现有受保护应用 API 提供统一 authenticated identity 入口
4. 为后续微信登录接入增加 identity-provider adapter 扩展位
5. 后续再通过独立变更接入真实微信 OAuth、会员权益和支付联动

回滚策略：

- 如果 refresh session 模型出现问题，可临时回退到“登录 + 只发 access token”的受限模式，但不应破坏 user model 和 middleware 边界
- 如果 external provider 设计不稳定，可保持 first-party auth 主线不变，仅延后 provider adapter 集成

## Open Questions

- 第一版账号标识是否以 email 为主，还是支持用户名 / 手机号多种登录名？
- refresh token 第一版放在 body 返回、HttpOnly cookie，还是双模式兼容？
- 是否需要第一版就提供“退出所有设备”能力，还是先只做当前会话 logout？
- 当前前端原型的微信登录入口，第一版后端是否要先接成 mock provider session，还是继续只保留页面占位？
