# 微信网页登录接入说明

当前原型已经切到“后端统一认证边界”的实现方式。

产品侧流程保持为：

- 访问登录页
- 打开微信登录弹窗
- 服务端创建授权会话
- 前端轮询授权状态
- 授权成功后换取内部 JWT 与 Refresh Token
- 进入 OfferSteady，并把后续资料、会话、截图、语音等资源统一绑定到内部 `User ID`

当前开发阶段默认使用兼容正式接口的 Provider 模式，不直接读取真实微信账号密码，也不会把微信密钥下发到浏览器。

## 当前支持的两种模式

- `compatible`
  - 用于开发联调
  - 后端生成授权会话、二维码文本和一次性 `state`
  - 开发环境可通过兼容 Provider 完成扫码/授权模拟
  - 前端交互、接口结构、状态流转与正式接入保持一致

- `formal`
  - 预留给正式微信开放平台接入
  - 由服务端对接真实微信授权入口、授权码交换和身份信息获取
  - 业务层不需要改动，只替换 Provider 实现

## 必备环境变量

- `OFFERSTEADY_ACCESS_TOKEN_SECRET`
- `OFFERSTEADY_AUTH_WECHAT_PROVIDER_MODE`
- `OFFERSTEADY_AUTH_WECHAT_APP_ID`
- `OFFERSTEADY_AUTH_WECHAT_APP_SECRET`
- `OFFERSTEADY_AUTH_WECHAT_CALLBACK_URL`
- `OFFERSTEADY_AUTH_WECHAT_AUTHORIZATION_TTL_SECONDS`

其中：

- `APP_SECRET` 只能保存在服务端
- `CALLBACK_URL` 必须指向后端 `/api/v1/auth/wechat/callback`
- `AUTHORIZATION_TTL_SECONDS` 控制二维码与 `state` 的有效期

## 安全与状态要求

- 每次授权会话都必须生成一次性 `state`
- `state` 只能成功消费一次，重复回调必须拒绝
- 授权会话过期后状态应变为 `expired`
- 服务端只以内部 `User ID` 作为业务资源归属键
- 微信身份已绑定其他账号时不得静默合并
- 日志不能记录授权码、令牌、`AppSecret` 或完整微信身份标识

## 生产切换建议

从兼容模式切到正式微信开放平台时，只做这几件事：

- 把 `OFFERSTEADY_AUTH_WECHAT_PROVIDER_MODE` 从 `compatible` 改为 `formal`
- 替换 Provider 实现里的授权入口与回调换码逻辑
- 配置正式 `App ID`、`App Secret` 和 HTTPS 回调域名
- 重新做一次回调、过期、回放攻击和多端登录验证

这样可以保证前端页面结构、后端业务归属逻辑、JWT 会话模型都不需要重写。
