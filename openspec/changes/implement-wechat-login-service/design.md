## Context

OfferSteady 当前已经把微信登录作为 Web 端主入口：登录页有“微信登录 / 注册”按钮，授权弹层也已经按正式产品体验做了原型占位。但后端现有认证主线仍以通用 Authentication Service 为基础，尚未真正落下一条“扫码授权 → 获取身份 → 自动建号 / 登录 → 发放 Token → 进入产品”的正式业务链路。

这次设计需要解决的不是单纯前端文案，而是整套登录边界：

- Web 端扫码登录入口与状态流转
- 服务端创建短期授权会话与一次性 `state`
- 与正式微信开放平台兼容的 provider adapter
- 当前开发阶段允许接入兼容 provider 联调
- 首次登录自动创建用户，后续统一返回同一 User ID
- 统一 JWT Access Token / Refresh Token / Logout / Current User
- 所有业务资源按 User ID 归属与鉴权

约束：

- 当前产品原型交互顺序保持不变
- 不在客户端保存 `AppSecret`、refresh token 明文或长期 provider 凭据
- 后续切换正式微信开放平台时，不修改业务层服务接口
- 当前开发联调允许使用兼容正式接口的 provider，但不得改变对外认证契约
- 本次不实现微信支付、会员和计费体系

## Goals / Non-Goals

**Goals:**

- 建立统一 WeChat Login Service 方案，与正式扫码登录流程保持一致
- 定义登录页、授权会话、回调、自动注册、JWT、Refresh Token、当前用户、登出和认证中间件
- 让所有核心业务对象统一绑定 User ID，并通过同一鉴权边界访问
- 保持 provider 解耦，使开发态兼容 provider 与正式微信开放平台可平滑切换
- 保持当前产品原型路由结构、登录入口和进入产品的交互顺序不变

**Non-Goals:**

- 不实现微信支付
- 不实现会员权益、积分购买或计费扣费逻辑
- 不扩展新的登录方式（邮箱、手机号、Apple 等）
- 不在本次中引入后台运营系统
- 不改变面试、资料、截图、语音等业务页面结构

## Decisions

### 1. 使用“Provider Adapter + Internal Authentication Service”双层模型

对外的登录方式是微信扫码，但内部仍由 Authentication Service 负责用户、会话、JWT 与 Refresh Token。Provider 只负责：

- 创建授权入口或二维码会话
- 验证授权回调
- 返回稳定的外部身份标识与最小用户资料

Authentication Service 负责：

- 查找或创建内部用户
- 建立用户与 provider identity 的绑定关系
- 发放 Access Token / Refresh Token
- 维护当前登录态与 logout

原因：

- 避免把 OAuth / 开放平台细节渗透到业务层
- 当前可接兼容 provider 联调，后续可切正式微信开放平台
- 业务模块只依赖内部 User ID，不依赖微信身份细节

备选方案：

- 直接把微信返回身份当业务主键：实现快，但后续更换 provider 或增加绑定规则时会污染业务层

### 2. 扫码登录采用“授权会话 + 一次性 state + 回调完成”模型

登录流程统一建模为：

1. 前端请求创建授权会话
2. 服务端生成短期 `auth_request_id`、一次性 `state` 和 provider 授权入口
3. 用户扫码并确认
4. provider 回调服务端
5. 服务端校验 `state`、完成 provider 身份交换
6. 自动注册或绑定已有用户
7. 发放内部 token
8. 前端轮询或消费受控回调结果，进入 OfferSteady

原因：

- 与正式微信扫码登录模式一致
- 可以安全处理二维码过期、重复回调和授权取消
- 开发态兼容 provider 也能复用同一状态机

备选方案：

- 前端直接拿 provider code 再调后端：会扩大前端暴露面，也不利于统一回调幂等

### 3. 内部用户以 OfferSteady User ID 为唯一事实源，provider identity 单独建模

用户表与 provider identity 表分开：

- `users`: `user_id`、昵称、头像、创建时间、最后登录时间
- `user_identities`: `provider`、`provider_subject`、`provider_union_key`（如有）、绑定状态、绑定时间

原因：

- 一个用户未来可能存在多种身份绑定
- 避免把微信身份字段直接塞进用户主表
- 更方便处理首次注册、重复登录和未来账号恢复方式扩展

备选方案：

- 把 provider 字段直接放到用户主表：对单一登录方式够用，但后续演进空间差

### 4. Access Token 短期化，Refresh Token 绑定可撤销登录会话

登录成功后：

- Access Token：短时 JWT，用于 API 鉴权
- Refresh Token：绑定 auth session，由服务端可撤销
- Auth Session：记录 User ID、provider、client label、创建时间、最后使用时间、撤销状态

原因：

- Web、手机、桌面伴随程序需要多端一致会话模型
- 支持 logout、续期、过期和异常会话管理
- 与现有 Authentication Service 基础一致

备选方案：

- 只发长期 JWT：实现简单，但不利于撤销和多端管理

### 5. 登录页保持当前原型交互，开发态兼容 provider 不新增测试专用产品分支

前端仍保留当前：

- 登录页点击微信登录
- 打开授权弹层
- 显示二维码或授权状态
- 成功后进入 OfferSteady

但开发态不再把“模拟成功”视为真实产品能力，而是通过兼容 provider 或受控开发开关返回同契约结果。

原因：

- 用户要求保持产品原型交互一致
- 后续从开发联调切到正式微信时，前端交互不应重做

备选方案：

- 为开发环境单独做另一套登录页面：短期方便，但会导致正式逻辑和原型逻辑分叉

### 6. 所有核心业务资源必须显式绑定 User ID，并经统一认证中间件访问

以下对象统一绑定内部 `user_id`：

- Resume
- JD
- Knowledge Base
- Interview Session
- Conversation
- Screenshot
- Speech
- History

受保护接口统一通过认证中间件或依赖注入读取当前用户，不允许业务接口自行解析 token。

原因：

- 避免资源串用或跨用户访问
- 后续审计、删除、迁移和计费都要依赖统一归属
- 与前端严格真实 API 模式更一致

备选方案：

- 先只在部分模块绑定用户：上线风险高，后续补齐代价更大

## Risks / Trade-offs

- [Risk] 微信开放平台正式配置尚未完成，开发联调与正式接入可能存在细节偏差 → Mitigation: 以 provider adapter 契约为边界，开发 provider 只模拟同等状态机与返回结构，不改变内部业务接口
- [Risk] 扫码授权涉及回调、二维码过期和重复提交，状态处理比普通登录更复杂 → Mitigation: 明确授权会话状态机、一次性 `state`、回调幂等和超时处理
- [Risk] 自动注册若绑定规则不清，可能造成重复账号或错误合并 → Mitigation: provider identity 唯一约束、首次登录自动创建、冲突时禁止静默合并
- [Risk] 当前核心业务模块尚未全部切到真实用户持久化 → Mitigation: 在 specs 中先明确 User ID 绑定与受保护访问契约，后续实现按模块逐步接入
- [Risk] 前端开发态与正式登录体验存在分叉 → Mitigation: 保持同一路由、同一弹层与同一 API 契约，只更换 provider 实现

## Migration Plan

1. 定义 WeChat Login Service 与 User ID 绑定能力 specs
2. 在后端新增 provider adapter、授权会话、回调处理、自动注册 / 绑定、token 发放与 current-user / logout API
3. 在前端登录页与授权弹层接入真实授权会话接口
4. 将受保护 API 统一切到认证中间件读取当前用户
5. 逐步让资料、面试和历史等核心业务对象使用统一 User ID 归属
6. 上线前把开发联调 provider 替换为正式微信开放平台 provider 配置

回滚策略：

- 若正式微信 provider 接入异常，可临时回退到兼容 provider 联调实现，但不回退内部 User ID、session 和 token 契约
- 若扫码回调链路存在问题，可暂时关闭扫码入口并保留授权会话 API，不影响已有认证基础模型

## Open Questions

- Web 端首发正式接入是否只支持微信开放平台网站应用扫码，还是需要同时考虑微信内 OAuth 入口？
- Refresh Token 首版通过 JSON body 返回、HttpOnly Cookie，还是双模式并存？
- 当前开发联调 provider 是否由项目内 mock-compatible adapter 提供，还是接入独立测试身份服务？
- 用户解绑微信前，是否必须先补充另一种恢复方式，还是 MVP 阶段先不开放解绑？
