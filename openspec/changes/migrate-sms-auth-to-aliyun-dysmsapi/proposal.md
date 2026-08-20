## Why

生产环境已更换为阿里云短信服务 `Dysmsapi/SendSms` 套餐，而现有认证实现依赖号码认证服务 `Dypnsapi/SendSmsVerifyCode + CheckSmsVerifyCode`。两种 API、模板参数和验证码校验责任不同，直接替换模板编号会导致登录短信不可用。

## What Changes

- 新增 `aliyun-dysmsapi` 短信认证 provider，通过 `SendSms` 使用已审核的短信签名和模板发送验证码。
- 由服务端使用安全随机数生成六位验证码，只持久化带独立 pepper 的 HMAC 摘要，不保存或记录明文。
- 服务端使用常量时间比较校验验证码，并继续执行现有过期、发送频率、每日次数和错误尝试上限。
- 保留现有 `aliyun` Dypnsapi provider 以便回滚，不改变前端登录接口和用户数据归属。
- 增加配置、数据库迁移、单元测试、真实短信显式探测和部署说明。

## Capabilities

### New Capabilities

- `aliyun-dysmsapi-sms-auth`: 定义使用阿里云短信服务发送、摘要保存和服务端校验登录验证码的安全行为。

### Modified Capabilities

- None.

## Impact

- Backend：短信 provider、challenge 记录、认证服务、配置和集成验证。
- Database：`auth_sms_challenges` 新增可空的验证码摘要字段，兼容历史 challenge。
- Deployment：生产模式切换为 `aliyun-dysmsapi`，endpoint、region、签名和模板同步更新；AccessKey 仍只保存在服务端。
- Web/API：接口契约不变，无需修改前端页面。
