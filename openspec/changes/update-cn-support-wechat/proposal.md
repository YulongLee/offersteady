## Why

国服当前仍显示旧客服微信 `mianshiwen-cn`，用户已提供新的客服账号 `mianshiwen_01`。需要统一更新客服配置、公开页面和法律文案，避免用户被引导到已停用的账号。

## What Changes

- 将国服客服微信统一替换为 `mianshiwen_01`。
- 更新后端客服状态接口、国服首页、联系页、使用说明及法律文案。
- 更新开发配置示例和本地测试夹具，确保测试不会回归旧账号。
- 不修改国际服客服信息，不修改支付、登录或面试业务逻辑。

## Capabilities

### New Capabilities

- `cn-support-contact`: 管理和展示国服客服微信账号。

### Modified Capabilities

- 无

## Impact

- 影响 `apps/backend` 的客服配置与 billing 状态响应。
- 影响 `apps/web` 的国服公开页面和法律文案。
- 需要重新构建并发布国服 Web/Backend，使线上页面和接口同时生效。
- 不处理历史审计快照和已归档文档中的旧账号记录。
