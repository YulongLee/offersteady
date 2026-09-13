## Why

国服生产环境仍允许开发态微信兼容 Provider 的模拟授权接口，导致未经过微信官方身份校验的合成账号被创建并出现在运营后台。当前国服登录页没有微信登录入口，因此生产环境不应继续暴露这条原型链路。

## What Changes

- 生产环境拒绝创建微信授权会话、模拟扫码、模拟授权和兼容回调。
- 保留 development/test 环境的兼容 Provider 联调能力。
- 不改变手机号、邮箱登录、微信支付或既有用户数据。
- 增加回归测试，确保生产环境不会再通过该接口创建 `wechat` 用户。

## Capabilities

### Modified Capabilities

- `wechat-login-service`: 兼容 Provider 仅允许在非生产环境使用；生产环境必须先完成正式 Provider 接入。

## Impact

- `apps/backend/app/services/authentication_service.py`：增加生产环境边界检查。
- `apps/backend/tests/test_foundation.py`：增加生产环境拒绝测试。
- 不删除历史合成用户，不修改支付和手机号登录流程。
