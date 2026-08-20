## Context

现有 `AliyunDypnsSmsVerificationProvider` 由阿里云生成并校验验证码。新套餐属于阿里云短信服务，只有 `SendSms` 发送能力，因此 OfferSteady 必须生成并校验验证码，同时继续满足不保存明文、可限流和可回滚的要求。

## Goals / Non-Goals

**Goals:**

- 支持 `Dysmsapi SendSms` 的签名、模板及 `code` 模板变量。
- 使用密码学安全随机数生成六位验证码，并只持久化 HMAC 摘要。
- 保持现有 Web API、登录会话和用户数据归属不变。
- 保留旧 Dypnsapi provider 作为部署回滚路径。

**Non-Goals:**

- 不修改登录页面、手机号范围或账号合并逻辑。
- 不在后台管理页面展示短信 AccessKey、验证码或摘要。
- 不迁移或重新启用历史验证码 challenge。

## Decisions

### 使用独立 provider mode

新增 `aliyun-dysmsapi`，现有 `aliyun` 继续表示 Dypnsapi。这样部署切换明确，也能通过恢复旧环境变量快速回滚；不根据模板编号隐式猜测 API 类型。

### 只保存带独立 pepper 的 HMAC 摘要

provider 使用 `secrets` 生成六位验证码，并计算 `HMAC-SHA256(pepper, challenge_id + phone + code)`。challenge 只保存摘要，校验使用常量时间比较。独立 pepper 由服务端环境变量提供，不复用浏览器可见配置。

### 扩展现有 challenge 而不另建验证码表

在 `auth_sms_challenges` 增加可空 `code_digest`。旧 Dypnsapi challenge 保持为空并继续委托阿里云校验；新 provider 必须存在摘要才能校验。

### 继续使用阿里云 RPC 签名适配器

`Dysmsapi` 与当前适配器均使用阿里云 RPC HMAC-SHA1 签名，可复用签名逻辑并仅改变 Action、PhoneNumbers 和 TemplateParam。避免新增 SDK 和生产依赖。

## Risks / Trade-offs

- [Risk] 生产 AccessKey 没有短信服务权限 → 部署前运行一次显式真实短信探测，失败则保持旧 provider。
- [Risk] 签名或模板审核状态变化 → 返回脱敏 provider code/request id，不把第三方原始响应暴露给浏览器。
- [Risk] 数据库迁移与后端版本短暂不一致 → 新字段可空，先迁移再切 provider。
- [Risk] 服务端负责验证码校验增加安全责任 → 安全随机生成、HMAC 摘要、过期、限流、尝试上限和常量时间比较共同约束。

## Migration Plan

1. 部署兼容新字段和双 provider 的后端，运行数据库迁移。
2. 配置 Dysmsapi endpoint、region、签名、模板和独立 code pepper。
3. 使用明确授权的测试手机号发送一次验证码并完成校验。
4. 将生产 provider mode 切换为 `aliyun-dysmsapi` 并观察错误率。
5. 回滚时恢复 `aliyun`、原 endpoint、原 region、原签名和原模板，无需回滚数据库。

## Open Questions

- None.
